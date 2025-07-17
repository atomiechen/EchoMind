import asyncio
import os
import json
from pathlib import Path
from typing import List, Optional
from handyllm.types import PathType
from tenacity import RetryCallState, retry, stop_after_attempt

from app.core.sio.sio_server import SioServer
from app.core.meeting_agent import MeetingAgent
from app.core.asr.models import AsrSentence
from app.core.agent.models import Sentence
from app.core.attendee_manager import AttendeeManager
from app.core.utils_echo import parse_sentences_to_dialog
from app.core.agent.parser import parse_summary
from app.core.sio.models import AllSummaries, SummaryData
from app.types import MeetingLanguageType


class MeetingAgentSummary(MeetingAgent):
    def __init__(self, root_dir: PathType, meeting_language: MeetingLanguageType):
        super().__init__(root_dir, meeting_language)

        # 字数阈值
        if self.meeting_language == "Chinese":
            self.SUMMARY_THRESHOLD = 200
        else:
            self.SUMMARY_THRESHOLD = 70

        self.sentence_queue: asyncio.Queue[Sentence] = asyncio.Queue()

        # 累计字符：目前尚未被AI分析所积累的字符数
        self.acc_char_num = 0
        self.new_sentence = []

        # 存储最新的summary和历史所有的summary（历史的summary不会包括最新的summary）
        self.summary_total: List = []
        self.summary_new: List[SummaryData] = []

        # agent 文件计数
        self.summary_cnt = 0
        self.edit_history_cnt = 0

        # 是否自动生成summary
        self.auto_generate = False

    async def proc_asr_results(
        self, asr_results: List[AsrSentence], sio: SioServer, room: str, manual=False
    ):
        for item in asr_results:
            sentence = Sentence(
                spk=item.speaker_id,
                sentence_id=len(self.sentences),
                content=item.content,
            )
            self.sentences.append(sentence)
            self.logger.info(f"[sentence] {sentence=}")

            # 非阻塞放入队列，保证这些数据一次性放入
            self.sentence_queue.put_nowait(sentence)

    async def loop_generate_summary(
        self,
        meeting_id: int,
        sio: SioServer,
        room: str,
        attendee_manager: AttendeeManager,
        meeting_manager,
    ):
        print("in loop_generate_summary")
        while meeting_manager.isRunning(str(meeting_id)):
            # 取出队列中所有未处理的数据
            while not self.sentence_queue.empty():
                sentence = self.sentence_queue.get_nowait()
                if self.meeting_language == "Chinese":
                    self.acc_char_num += len(sentence.content)
                else:
                    self.acc_char_num += len(sentence.content.split())
                self.new_sentence.append(sentence)

            # 如果字数超过阈值
            if self.acc_char_num > self.SUMMARY_THRESHOLD or self.auto_generate:
                if self.summary_cnt == 0:
                    await asyncio.sleep(15)
                else:
                    if not self.auto_generate:
                        await asyncio.sleep(2)
                        continue
                self.acc_char_num = 0
                self.auto_generate = False
                self.agent.is_running = True
                await sio.statusAI(room, True)
                speaker = attendee_manager.get_speaker_map(meeting_id)
                new_dialog = parse_sentences_to_dialog(self.new_sentence, speaker)
                try:
                    # 生成summary
                    new_summary_points = await self.generate_summary(new_dialog)
                    # 保存并发送summary
                    await self.save_and_send_summary(new_summary_points, sio, room)
                except Exception as e:
                    self.logger.warning(
                        f"[text_to_summary_error]: {str(e)}", exc_info=True
                    )
                    self.agent.is_running = False
                    await sio.statusAI(room, False)
                    await asyncio.sleep(1)
                    continue
            else:
                await asyncio.sleep(1)

    @retry(stop=stop_after_attempt(3))
    async def generate_summary(
        self,
        dialog: str,
        retry_state: Optional[RetryCallState] = None,
    ):
        print("in generate_summary")

        base_filename = Path(
            self.cm.base_dir, f"summary/sum_{self.summary_cnt}.txt"
        ).resolve()
        # 获取当前的重试次数
        # retry_count = retry_state.attempt_number if retry_state else 1
        retry_count = 1
        # 构造带有重试次数后缀的文件名
        full_filename = base_filename
        file_suffix = ""
        if os.path.exists(base_filename):
            full_filename = f"{base_filename}_retry_{retry_count}"
            file_suffix = f"_retry_{retry_count}"
            while os.path.exists(
                full_filename
            ):  # 如果带有后缀的文件已经存在，递增后缀数字
                retry_count += 1
                full_filename = f"{base_filename}_retry_{retry_count}"
                file_suffix = f"_retry_{retry_count}"

        # 调用文转 summary API
        new_summary_points = await self.cm.cache(
            self.agent.summary_points,
            f"summary/sum_{self.summary_cnt}{file_suffix}.txt",
        )(
            dialog=dialog,
            cnt=self.summary_cnt,
            logger=self.logger,
            file_suffix=file_suffix,
            meeting_language=self.meeting_language,
        )
        self.logger.info(f"[summary_points] {new_summary_points=}")
        return new_summary_points

    async def save_and_send_summary(
        self, new_summary_points: str, sio: SioServer, room: str
    ):
        parsed_summary_list = parse_summary(new_summary_points)
        self.logger.info(f"[parsed_summary_list] {parsed_summary_list=}")
        for summary in parsed_summary_list:
            summary_data = SummaryData(
                id=len(self.summary_new) + len(self.summary_total),
                summary=summary,
            )
            self.summary_new.append(summary_data)
        await sio.sendSummaryNew(room, AllSummaries(summaries=self.summary_new))

        # 重置变量
        self.summary_total.extend(self.summary_new)
        self.summary_new = []
        self.new_sentence = []
        # self.start_summary_index = len(self.sentences)
        self.agent.is_running = False
        self.summary_cnt += 1
        await sio.statusAI(room, False)
        await asyncio.sleep(1)

    async def save_history(self, history_list: List):
        # 保存历史记录
        history = {
            "id": self.edit_history_cnt,
            "history": history_list,
        }
        history_filename = Path(
            self.cm.base_dir, f"history/history_{self.edit_history_cnt}.json"
        ).resolve()
        with open(history_filename, "w") as f:
            json.dump(history, f)

        self.edit_history_cnt += 1
