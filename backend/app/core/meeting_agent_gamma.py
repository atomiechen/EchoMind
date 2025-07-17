import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple
from handyllm.types import PathType
import asyncio
import copy
from tenacity import retry, stop_after_attempt, RetryCallState

from app.core.agent.models import Issue, Sentence
from app.core.agent.parser import (
    issue_map_to_str,
    gamma_parse_new_position,
    gamma_parse_new_issue,
)
from app.core.asr.models import AsrSentence
from app.core.utils_echo import (
    judge_node_type_by_full_id,
    parse_sentences_to_dialog,
)
from app.core.meeting_agent import MeetingAgent
from app.core.attendee_manager import AttendeeManager
from app.core.parsed_issues import ParsedIssue
from app.core.sio.sio_server import SioServer
from app.core.sio.models import UpdateIssueData
from app.types import MeetingLanguageType


class MeetingAgentGamma(MeetingAgent):
    def __init__(self, root_dir: PathType, meeting_language: MeetingLanguageType):
        super().__init__(root_dir, meeting_language)

        # 字数阈值
        if self.meeting_language == "Chinese":
            self.TEXT_TO_POSITION_THRESHOLD = 50
        else:
            self.TEXT_TO_POSITION_THRESHOLD = 100

        # 初始化数据
        self.issue_map = ""
        self.context = ""
        self.parsed_issues_new = ParsedIssue(parsed_issue=[])

        # self.sentences = [] # 本次会议中的所有句子
        self.context_queue = asyncio.Queue()  # 生成context的新对话

        self.issue_map_queue: asyncio.Queue[Sentence] = asyncio.Queue()
        self.start_issue_index = 0  # 文转issue agent的对话的起始index(实际开始的id)
        self.start_position_index = (
            0  # 文转position agent的对话的起始index(实际开始的id)
        )
        self.processed_issue_index = 0  # 记录上一次调用文转issue agent的index
        self.processed_position_index = 0  # 记录上一次调用文转position agent的index
        self.split_flag = False  # 是否需要截断对话

        # self.new_dialogs: List[Sentence] = [] # 存储选择当前节点之后的累计对话

        # 累计字符：目前尚未被AI分析所积累的字符数
        self.acc_char_num_issue_map = 0
        self.acc_char_num_context = 0

        # 文件计数
        self.issue_and_position_cnt = 0
        self.issue_map_cnt = 0
        self.ctx_cnt = 0
        self.dialog_cnt = 0

        # agent 文件计数
        self.text_to_position_cnt = 0
        self.text_to_issue_cnt = 0
        self.suggest_position_cnt = 0
        self.suggest_issue_cnt = 0

        # 用户选择的节点, 默认没有选中
        self.chosen_node: int = -1

        # 静音触发
        self.is_mute = False  # 用户没有说话
        self.mute_generate = False  # 用户没有说话已经触发了生成issue map

        self.auto_generate = False
        self.last_issue = None

        # 用新的asr结果更新meeting agent

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
            self.issue_map_queue.put_nowait(sentence)

    async def gamma_op_node(
        self,
        op: Literal["modify", "add", "delete"],
        sio: SioServer,
        room: str,
        full_id: Optional[str] = None,
        node_type: Optional[Literal["ISSUE", "POSITION"]] = None,
        content: Optional[str] = None,
        father_id: Optional[str] = None,
    ) -> Dict:
        # operate on parsed_issues_new
        data = {}
        self.logger.info(f"user {op} node {full_id} {node_type}")
        if self.agent.is_running:
            self.agent.edit_node = True
        if op == "modify":
            self.logger.info(f"[modify] {full_id=} {content=}")
            self.parsed_issues_new.user_modify_node(
                full_id=str(full_id), new_content=str(content)
            )
        elif op == "add":
            new_node_full_id = self.parsed_issues_new.user_add_node(
                node_type=node_type, father_id=str(father_id), content=str(content)
            )
            data["full_id"] = new_node_full_id
            self.logger.info(
                f"[add] {new_node_full_id=} {node_type=} {father_id=} {content=}"
            )
        elif op == "delete":
            self.logger.info(f"[delete] {full_id=}")
            print("delete full_id: ", full_id)
            self.split_flag = False
            if str(self.chosen_node) == str(full_id):
                self.split_flag = True
                self.chosen_node = -1
            if judge_node_type_by_full_id(str(full_id)) == "position":
                if str(full_id).split(".")[0] == str(self.chosen_node):
                    self.split_flag = True
                    self.start_position_index = self.processed_position_index
            # 删除issue
            if judge_node_type_by_full_id(str(full_id)) == "issue":
                deleted_issue = self.parsed_issues_new.parsed_issue[
                    int(str(full_id).split(".")[0]) - 1
                ]
                print("deleted_issue", deleted_issue)
                if (
                    deleted_issue.source is not None
                    and deleted_issue.source.target_id.split(".")[0]
                    == str(self.chosen_node)
                ):
                    self.split_flag = True
                    self.start_issue_index = self.processed_issue_index
            self.acc_char_num_issue_map = 0
            self.log_check_point("delete_node_check")
            self.parsed_issues_new.user_delete_node(full_id=str(full_id))
        # update issue map
        self.update_and_save_issue_map()
        await self.gamma_send_issue_map(sio, room)
        return data

    async def gamma_generate_issue_map(
        self,
        meeting_id: int,
        sio: SioServer,
        room: str,
        attendee_manager: AttendeeManager,
        meeting_manager,
    ):
        print("in gamma_generate_issue_map")
        if self.meeting_language == "English":
            self.TEXT_TO_POSITION_THRESHOLD = 100
        while meeting_manager.isRunning(str(meeting_id)):
            # 取出队列中所有未处理的数据
            while not self.issue_map_queue.empty():
                sentence = self.issue_map_queue.get_nowait()
                if self.meeting_language == "Chinese":
                    self.acc_char_num_issue_map += len(sentence.content)
                else:
                    self.acc_char_num_issue_map += len(sentence.content.split())

            # 如果字数超过阈值，且用户选择了节点
            if (
                self.acc_char_num_issue_map > self.TEXT_TO_POSITION_THRESHOLD
                or self.auto_generate
            ) and self.chosen_node > 0:
                """
                新position -> new issue -> suggest issue 
                           -> suggest position
                """
                # 是否用户主动生成
                if self.auto_generate:
                    self.auto_generate = False
                self.agent.is_running = True
                await sio.statusAI(room, True)

                self.last_issue = copy.deepcopy(self.chosen_node)
                speaker = attendee_manager.get_speaker_map(meeting_id)
                last_index = len(self.sentences)

                if self.start_position_index >= last_index:
                    await sio.statusAI(room, False)
                    self.acc_char_num_issue_map = 0
                    self.is_running = False
                    self.logger.info(
                        f"[invalid_position_index] {self.start_position_index=} {last_index=}"
                    )
                    continue

                # 文转position
                try:
                    is_edited = await self.text_to_position(
                        parse_sentences_to_dialog(
                            self.sentences[self.start_position_index : last_index],
                            speaker,
                        )
                    )
                    if is_edited:
                        await sio.statusAI(room, False)
                        self.is_running = False
                        self.logger.info("[interrupt_position]")
                        continue
                except Exception as e:
                    self.logger.warning(
                        f"[text_to_position_error]: {str(e)}", exc_info=True
                    )
                    self.agent.is_running = False
                    await sio.statusAI(room, False)
                    await asyncio.sleep(1)
                    continue

                # 如果用户对思维导图进行了操作，就直接返回

                # 保存并往前端发送issue map
                self.update_and_save_issue_map()
                await self.gamma_send_issue_map(sio, room)
                self.processed_position_index = last_index
                self.log_check_point("text_to_position_check")

                # 新建一个平行的任务，建议position
                # is_edited = asyncio.create_task(self.suggest_position(dialog))
                # if is_edited:
                #     continue

                # 文转issue
                if self.start_issue_index >= last_index:
                    await sio.statusAI(room, False)
                    self.acc_char_num_issue_map = 0
                    self.is_running = False
                    self.logger.info(
                        f"[invalid_issue_index] {self.start_issue_index=} {last_index=}"
                    )
                    continue

                try:
                    issue_added, is_edited = await self.text_to_issue(
                        dialog=parse_sentences_to_dialog(
                            self.sentences[self.start_issue_index : last_index], speaker
                        )
                    )
                    if is_edited:
                        await sio.statusAI(room, False)
                        self.is_running = False
                        self.logger.info("[interrupt_issue]")
                        continue
                except Exception as e:
                    self.logger.warning(
                        f"[text_to_issue_error]: {str(e)}", exc_info=True
                    )
                    self.agent.is_running = False
                    await sio.statusAI(room, False)
                    await asyncio.sleep(1)
                    continue

                # 保存并往前端发送issue map
                self.update_and_save_issue_map()
                await self.gamma_send_issue_map(sio, room)
                self.processed_issue_index = last_index
                self.log_check_point("text_to_issue_check")

                # 字数置零
                self.acc_char_num_issue_map = 0
                self.agent.is_running = False
                await sio.statusAI(room, False)

                # DONE： 用 processed_index 记录截止到调用上一次 agent 的对话 id (注意：这是总id，不是当前对话的id)

            else:
                await asyncio.sleep(1)

        print(f"现在用户是否静音：{self.is_mute}")
        print(f"现在用户是否已经触发生成issue map：{self.mute_generate}")
        print("现在选择的节点是：", self.chosen_node)
        print(f"issue map累计的字符数：{self.acc_char_num_issue_map}")
        print("end gamma_generate_issue_map")
        self.logger.info("--- end gamma_generate_issue_map ---")

    def check_manual_edits(
        self,
        node_type: Literal["issue", "position"],
        old_dict: Dict,
        last_issue: str,
        last_chosen_id: int,
    ) -> bool:
        """
        检查 focus 节点有没有被修改（内容，id）
        检查agent的原始输入节点有没有被修改（内容，type）
        返回：true-有修改，false-无修改
        """
        # TODO 如果换了节点，还是把原来的内容放进去
        # DONE 换了节点也不能长
        if (
            self.parsed_issues_new.parsed_issue[int(self.chosen_node) - 1].content
            != last_issue
            or self.parsed_issues_new.parsed_issue[int(self.chosen_node) - 1].type
            == "deleted"
        ):
            return True
        if node_type == "position":
            current_positions, input_positions = (
                self.parsed_issues_new.i2p_current_positions(self.chosen_node)
            )
            # TODO 编辑距离小于3，就判定为没有修改
            if (
                old_dict["current_positions"] != current_positions
                or old_dict["input_positions"] != input_positions
            ):
                return True
        if node_type == "issue":
            p2i_positions = self.parsed_issues_new.p2i_parse_positions(self.chosen_node)
            if old_dict["p2i_positions"] != p2i_positions:
                return True
        return False

    @retry(stop=stop_after_attempt(3))
    async def text_to_position(
        self, dialog: str, retry_state: Optional[RetryCallState] = None
    ) -> bool:
        """
        文转position
        返回需要调用文转 issue agent 的 position 的 full_id 列表
        """
        # get input data
        current_positions, input_positions = (
            self.parsed_issues_new.i2p_current_positions(self.chosen_node)
        )
        last_issue_id = self.chosen_node
        last_issue_content = self.parsed_issues_new.parsed_issue[
            int(last_issue_id) - 1
        ].content
        base_filename = Path(
            self.cm.base_dir, f"text_to_position/i2p_{self.text_to_position_cnt}.txt"
        ).resolve()
        base_filename.parent.mkdir(parents=True, exist_ok=True)
        # 获取当前的重试次数
        retry_count = retry_state.attempt_number if retry_state else 1

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

        # 创建并打开文件，'w' 模式表示如果文件不存在则创建，存在则覆写
        with open(full_filename, "w") as file:
            file.write("")  # 可以写入初始内容或留空

        # 根据当前的position数量，限制新增position的数量
        current_positions_number = len(input_positions)
        if current_positions_number <= 2:
            position_number_limitation = "You can only add at most 1 new position, unless the dialog explicitly mentions multiple structured aspects."
        else:
            position_number_limitation = "Make sure the total number of positions is less than 5; typically within 3."

        # # 获取当前的重试次数
        # retry_count = retry_state.attempt_number if retry_state is not None else 0
        # file_suffix = f'_retry_{retry_count}' if retry_count > 0 else ''
        # print("file_suffix: ", file_suffix)

        # 调用文转 position API
        new_positions = await self.cm.cache(
            self.agent.gamma_text_to_position,
            f"text_to_position/i2p_{self.text_to_position_cnt}{file_suffix}.txt",
        )(
            dialog=dialog,
            context=self.context,
            issue_chain=self.parsed_issues_new.issue_chain(last_issue_id),
            current_positions=current_positions,
            cnt=self.text_to_position_cnt,
            logger=self.logger,
            position_number_limitation=position_number_limitation,
            file_suffix=file_suffix,
            meeting_language=self.meeting_language,
        )
        # 判断调用 agent 的时候用户是否对于思维导图进行了操作
        is_edited = self.check_manual_edits(
            node_type="position",
            old_dict={
                "current_positions": current_positions,
                "input_positions": input_positions,
            },
            last_issue=last_issue_content,
            last_chosen_id=last_issue_id,
        )
        p2i_postions = []
        if not is_edited:
            parsed_new_positions = gamma_parse_new_position(new_positions)
            self.logger.info(f"[parsed_new_positions] {parsed_new_positions=}")
            self.text_to_position_cnt += 1
            if len(parsed_new_positions) > 0:
                p2i_postions = self.parsed_issues_new.add_new_positions(
                    parsed_new_positions,
                    chosen_id=last_issue_id,
                    input_positions=input_positions,
                )
        return is_edited

    @retry(stop=stop_after_attempt(3))
    async def text_to_issue(
        self, dialog: str, retry_state: Optional[RetryCallState] = None
    ) -> Tuple[int, bool]:
        """
        文转issue
        """
        # 保存元数据
        last_issue_id = self.chosen_node
        last_issue_content = self.parsed_issues_new.parsed_issue[
            int(last_issue_id) - 1
        ].content

        # 获取当前没有生成过的 position 的 list
        p2i_positions = self.parsed_issues_new.p2i_parse_positions(last_issue_id)
        if p2i_positions == "":
            return 0, False

        # 获取当前的重试次数
        retry_count = retry_state.attempt_number if retry_state else 1
        base_filename = Path(
            self.cm.base_dir, f"text_to_issue/p2i_{self.text_to_issue_cnt}.txt"
        ).resolve()
        base_filename.parent.mkdir(parents=True, exist_ok=True)
        # 构造带有重试次数后缀的文件名
        full_filename = base_filename
        file_suffix = ""
        if os.path.exists(base_filename):
            full_filename = f"{base_filename}_retry_{retry_count}"
            file_suffix = f"_retry_{retry_count}"
            while os.path.exists(full_filename):
                retry_count += 1
                full_filename = f"{base_filename}_retry_{retry_count}"
                file_suffix = f"_retry_{retry_count}"

        # 调用文转 issue agent
        new_issues = await self.cm.cache(
            self.agent.gamma_text_to_issue,
            f"text_to_issue/p2i_{self.text_to_issue_cnt}{file_suffix}.txt",
        )(
            context=self.context,
            issue_chain=self.parsed_issues_new.issue_chain(last_issue_id),
            positions_list=p2i_positions,
            dialog=dialog,
            cnt=self.text_to_issue_cnt,
            logger=self.logger,
            file_suffix=file_suffix,
            meeting_language=self.meeting_language,
        )

        # 检查用户是否对思维导图进行了操作
        res = self.check_manual_edits(
            node_type="issue",
            old_dict={"p2i_positions": p2i_positions},
            last_issue=last_issue_content,
            last_chosen_id=last_issue_id,
        )

        if not res:
            # 检查是否生成了新的 issue
            if (
                new_issues == "无"
                or new_issues is None
                or "none" in new_issues.lower()
                or len(new_issues) < 5
            ):
                return 0, res
            # 解析 agent 的输出
            # TODO 修改prompt中的输入, 改成这里的解析的方法: position内容和编号都不能改
            parsed_new_issues = gamma_parse_new_issue(new_issues)
            self.logger.info(f"[parsed_new_issues] {parsed_new_issues=}")
            # 用 agent 的输出更新 issue map
            self.parsed_issues_new.add_new_issues(
                new_issues=parsed_new_issues, chosen_id=last_issue_id
            )
            self.text_to_issue_cnt += 1
        return 1, res

    def update_and_save_issue_map(self):
        """
        更新issue map并保存
        """
        self.issue_map = issue_map_to_str(self.parsed_issues_new.parsed_issue)
        output_path = Path(
            self.cm.base_dir, f"issue_map/issue_map-{self.issue_map_cnt}.json"
        ).resolve()
        issue_map_dict = self.cm.cache(
            self.parsed_issues_new.get_issue_map_dict, output_path
        )()
        self.logger.info(f"[issue_map] {output_path=}")
        self.issue_map_cnt += 1

    async def gamma_send_issue_map(self, sio: SioServer, room: str):
        """
        发送issue map
        {
            "issue_map": [...],
            "issue_map_html":[]
            "chosen_id": ""
        }
        """
        tmp = self.parsed_issues_new.issue_map_list_without_delete
        await sio.updateIssue(
            room,
            UpdateIssueData(
                issue_map=tmp,
                chosen_id=str(self.chosen_node),
            ),
        )
        print("send issue map: \n", tmp)

    def set_first_issue(self, topic: str):
        """
        设置第一个issue
        """
        issue = Issue(full_id="1", content=topic, issue_id=1, positions=[], source=None)
        self.parsed_issues_new.parsed_issue.append(issue)
        self.update_and_save_issue_map()

    async def set_chosen_node(self, full_id_str: str, sio: SioServer, room: str):
        """
        设置用户选择的节点, 如果当前没有选择的节点就置为-1
        """
        full_id = int(str(full_id_str).strip())
        self.logger.info(f"[choose_node] {full_id=}")
        if full_id == -1:
            self.chosen_node = -1
            print("现在没有选择的节点")
        elif int(full_id) != self.chosen_node:
            self.chosen_node = int(full_id)
            # TODO: 检查，用户选择节点后，哪些变量要重置
            # self.new_dialogs = []
            self.start_issue_index = len(self.sentences)
            self.start_position_index = len(self.sentences)
            self.acc_char_num_issue_map = 0
            self.parsed_issues_new.confirm_node_fathers(str(full_id))
        self.log_check_point("choose_node_check")
        self.update_and_save_issue_map()
        await self.gamma_send_issue_map(sio, room)

    def log_check_point(self, tag: str):
        """
        打印当前的检查点
        """
        self.logger.info(
            f"[{tag}] {self.acc_char_num_issue_map=} {self.start_issue_index=} {self.start_position_index=} {self.processed_issue_index=} {self.processed_position_index=} {self.split_flag=} {len(self.sentences)=}"
        )
