import asyncio
from datetime import datetime
import logging
import random
import string
from typing import Dict, List, Optional, Union
from pydantic import TypeAdapter
from sqlalchemy import Engine
from sqlmodel import Session, func, select
from pathlib import Path

from app.core.sio.sio_server import SioServer
from app.models import Code, Meeting
from app.core.meeting_recorder import MeetingRecorder
from app.core.meeting_agent import MeetingAgent
from app.core.meeting_agent_gamma import MeetingAgentGamma
from app.core.meeting_agent_summary import MeetingAgentSummary
from app.core.asr.models import AsrSentence, SendAsrData
from app.core.attendee_manager import AttendeeManager
from app.core.asr.utils import (
    combine_pcm_to_wav,
)
from app.core.parsed_issues import ParsedIssue
from app.core.util import get_max_numbered_parsed_issues
from app.config import settings
from app.types import AiType, MeetingLanguageType


def get_meeting_hash():
    # 返回一个8位的哈希ID(str，全是数字）
    return "".join(random.choices(string.digits, k=8))


def generate_unique_hash(session: Session) -> str:
    while True:
        hash_id = get_meeting_hash()
        # 检查该 hash_id 是否已存在
        existing_meeting = session.exec(
            select(Meeting).where(Meeting.hash_id == hash_id)
        ).first()
        if not existing_meeting:
            return hash_id


class MeetingManager:
    def __init__(self, db_engine: Engine) -> None:
        self.db_engine = db_engine
        self.meeting_recorders: Dict[str, MeetingRecorder] = {}
        self.meeting_agents: Dict[str, MeetingAgent] = {}

    def newMeetingRecorder(
        self,
        meeting_id: Union[int, str],
        meeting_language: MeetingLanguageType,
        create_time: datetime,
        meeting_root_path: Path,
    ):
        meeting_id = str(meeting_id)
        obj = MeetingRecorder(
            meeting_id, meeting_language, create_time, meeting_root_path
        )
        self.meeting_recorders[meeting_id] = obj
        return obj

    def newMeetingAgent(
        self,
        meeting_id: Union[int, str],
        ai_type: AiType,
        meeting_language: MeetingLanguageType,
    ):
        meeting_id = str(meeting_id)
        if ai_type == "graph":
            obj = MeetingAgentGamma(
                self.getMeetingRootPath(meeting_id), meeting_language
            )
        elif ai_type == "document":
            obj = MeetingAgentSummary(
                self.getMeetingRootPath(meeting_id), meeting_language
            )
        else:
            raise ValueError("Unsupported agent type")
        self.meeting_agents[meeting_id] = obj
        return obj

    def createMeeting(
        self,
        create_by: int,
        topic: str,
        ai_type: AiType,
        sio: SioServer,
        attendee_manager: AttendeeManager,
        hot_words: Optional[List[str]],
        meeting_language: MeetingLanguageType,
    ) -> Meeting:
        with Session(self.db_engine) as session:
            hash_id = generate_unique_hash(session)
            meeting = Meeting(
                create_by=create_by,
                master_id=create_by,
                topic=topic,
                hot_words=hot_words,
                hash_id=hash_id,
                ai_type=ai_type,
                meeting_language=meeting_language,
            )
            session.add(meeting)
            session.commit()
            session.refresh(meeting)
        assert meeting.meeting_id
        # 创建会议根目录路径
        root_path = self.getMeetingRootPath(str(meeting.meeting_id))
        root_path.mkdir(parents=True, exist_ok=True)
        self.newMeetingRecorder(
            meeting.meeting_id, meeting_language, meeting.create_time, root_path
        )
        room = meeting.hash_id
        meeting_agent = self.newMeetingAgent(
            meeting.meeting_id, ai_type, meeting_language
        )
        if isinstance(meeting_agent, MeetingAgentGamma):
            print("meeting agent is gamma")
            meeting_agent.set_first_issue(topic=topic)
            asyncio.create_task(
                meeting_agent.gamma_generate_issue_map(
                    meeting.meeting_id,
                    sio,
                    room,
                    attendee_manager,
                    self,
                )
            )
        elif isinstance(meeting_agent, MeetingAgentSummary):
            print("meeting agent is summary")
            asyncio.create_task(
                meeting_agent.loop_generate_summary(
                    meeting.meeting_id, sio, room, attendee_manager, self
                )
            )
        else:
            print("meeting agent is base")
        # 开启后端循环计时异步任务
        asyncio.create_task(
            self.cycle_request_data(
                str(meeting.meeting_id), sio, room, attendee_manager
            )
        )
        return meeting

    def createMeetingResume(
        self,
        meeting_resume_hash_id: str,
        create_by: int,
        ai_type: AiType,
        sio: SioServer,
        attendee_manager: AttendeeManager,
        hot_words: Optional[List[str]],
        meeting_language: MeetingLanguageType,
    ) -> Meeting:
        # get meeting from db by hash id
        meeting = self.getMeetingByHashId(meeting_resume_hash_id)
        assert meeting
        assert meeting.meeting_id

        # get old issue map and topic
        old_parsed_issue = []
        root_path = self.getMeetingRootPath(str(meeting.meeting_id))
        latest_issue_map_path = root_path / "online" / "issue_map"
        old_parsed_issue, old_topic = get_max_numbered_parsed_issues(
            latest_issue_map_path
        )

        # create new agent
        with Session(self.db_engine) as session:
            hash_id = generate_unique_hash(session)
            meeting = Meeting(
                create_by=create_by,
                master_id=create_by,
                topic=old_topic,
                hot_words=hot_words,
                hash_id=hash_id,
                ai_type=ai_type,
                meeting_language=meeting_language,
            )
            session.add(meeting)
            session.commit()
            session.refresh(meeting)
        assert meeting.meeting_id
        # 创建会议根目录路径
        root_path = self.getMeetingRootPath(str(meeting.meeting_id))
        root_path.mkdir(parents=True, exist_ok=True)
        self.newMeetingRecorder(
            meeting.meeting_id, meeting_language, meeting.create_time, root_path
        )
        room = meeting.hash_id
        meeting_agent = self.newMeetingAgent(
            meeting.meeting_id, ai_type, meeting_language
        )
        if isinstance(meeting_agent, MeetingAgentGamma):
            print("meeting agent is gamma")
            meeting_agent.logger.info("[restart_success] meeting agent is gamma")
            meeting_agent.set_first_issue(topic=old_topic)
            meeting_agent.parsed_issues_new = ParsedIssue(parsed_issue=old_parsed_issue)
            meeting_agent.update_and_save_issue_map()
            asyncio.create_task(
                meeting_agent.gamma_generate_issue_map(
                    meeting.meeting_id,
                    sio,
                    room,
                    attendee_manager,
                    self,
                )
            )
        else:
            print("meeting agent is base")
        # 开启后端循环计时异步任务
        asyncio.create_task(
            self.cycle_request_data(
                str(meeting.meeting_id), sio, room, attendee_manager
            )
        )
        return meeting

    def getMeetingRootPath(self, meeting_id: str):
        return settings.meeting_data_root / meeting_id

    def getMeetingByHashId(self, hash_id: str):
        with Session(self.db_engine) as session:
            statement = select(Meeting).where(Meeting.hash_id == hash_id)
            meeting = session.exec(statement).one_or_none()
            return meeting

    def updateHotWords(self, meeting_id: str, hot_words: List[str]) -> None:
        with Session(self.db_engine) as session:
            statement = select(Meeting).where(Meeting.meeting_id == meeting_id)
            meeting = session.exec(statement).one_or_none()
            if meeting:
                meeting.hot_words = hot_words
                session.commit()

    def getMeetingById(self, meeting_id: str):
        with Session(self.db_engine) as session:
            statement = select(Meeting).where(Meeting.meeting_id == meeting_id)
            meeting = session.exec(statement).one_or_none()
            return meeting

    def updateMasterId(self, meeting_id: str, master_id: int) -> None:
        with Session(self.db_engine) as session:
            statement = select(Meeting).where(Meeting.meeting_id == meeting_id)
            meeting = session.exec(statement).one_or_none()
            if meeting:
                meeting.master_id = master_id
                session.commit()

    def updateTopic(self, meeting_id: str, topic: str) -> None:
        with Session(self.db_engine) as session:
            statement = select(Meeting).where(Meeting.meeting_id == meeting_id)
            meeting = session.exec(statement).one_or_none()
            if meeting:
                meeting.topic = topic
                session.commit()

    async def endMeeting(
        self, meeting_id: str, sio: SioServer, attendee_manager: AttendeeManager
    ):
        if settings.save_pcm:
            pcm_dir = Path(settings.meeting_data_root) / meeting_id / "pcm"
            wav_path = (
                Path(settings.meeting_data_root) / meeting_id / f"{meeting_id}.wav"
            ).resolve()
            if pcm_dir.exists():
                await asyncio.to_thread(combine_pcm_to_wav, pcm_dir, wav_path)
                print(f"音频合并成功: {wav_path}")
            else:
                print("音频合并失败: pcm文件夹不存在")

        with Session(self.db_engine) as session:
            statement = select(Meeting).where(Meeting.meeting_id == meeting_id)
            meeting = session.exec(statement).one_or_none()
            if meeting:
                meeting.status = "finished"
                room = meeting.hash_id
                session.commit()
            else:
                return Code.FAILED
        attendees = attendee_manager.get_active_attendees(
            meeting_id
        )  # 获取所有在会议中的参会者
        # 所有参会者离开会议
        for attendee in attendees:
            attendee_manager.leaveMeeting(meeting_id, attendee.user_id)

        # 通知所有还在会议中的参会者
        await sio.sendMeetingEnd(room)
        # 关闭会议房间
        await sio.close_room(room)
        # 释放 meeting_agent
        meeting_agent = self.meeting_agents.pop(meeting_id, None)
        if meeting_agent:
            meeting_agent.close()
            del meeting_agent
        # 释放 meeting_recorder
        meeting_recorder = self.meeting_recorders.pop(meeting_id, None)
        if meeting_recorder:
            del meeting_recorder

        return Code.SUCCESS

    async def getTotalAsrResult(self, meeting_id: str):
        meeting_recorder = self.meeting_recorders.get(meeting_id)
        if meeting_recorder:
            return await meeting_recorder.get_total_asr()

    def isRunning(self, meeting_id: str):
        meeting = self.getMeetingById(meeting_id)
        return meeting and meeting.status == "processing"

    def init_logger(self, meeting_id):
        logger = logging.getLogger(f"mid-{meeting_id}-asr")
        file_handler = logging.FileHandler(
            self.getMeetingRootPath(meeting_id) / "meeting_asr.log"
        )
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def close_logger(self, logger: logging.Logger):
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)

    async def cycle_request_data(
        self,
        meeting_id: str,
        sio: SioServer,
        room: str,
        attendee_manager: AttendeeManager,
    ):
        logger_mid = self.init_logger(meeting_id)
        # 获取会议录音器和会议agent
        meeting_recorder = self.meeting_recorders[meeting_id]
        meeting_agent = self.meeting_agents[meeting_id]
        meeting = self.getMeetingById(meeting_id)
        assert meeting is not None
        logger_mid.info("[loop.enter] cycle_request_data")
        # DONE 检查所有的循环都会在会议结束的时候停止
        while self.isRunning(meeting_id):
            try:
                # 等待通知
                await asyncio.wait_for(
                    meeting_recorder.trigger_event.wait(), timeout=1.0
                )
            except asyncio.TimeoutError:
                # 没有新数据，继续轮询
                continue

            # 清除事件，进行后续处理
            meeting_recorder.trigger_event.clear()

            # 获取当前排序后的的asr结果
            result = await meeting_recorder.get_current()
            # 输出内容与对应的开始时间
            # logger_mid.info(f"[asr] {result=}")
            speaker = attendee_manager.get_speaker_map(meeting_id)
            data = SendAsrData(speaker=speaker, sentences=result)
            await sio.sendCurrent(room, data)  # 向所有room内客户端广播
            await meeting_recorder.step()  # 将current_asr加入total_asr
            await meeting_agent.proc_asr_results(data.sentences, sio, room)
        logger_mid.info("[loop.exit] cycle_request_data")
        # 关闭 funasr clients（会等待剩余asr结果）
        await meeting_recorder.close_funasr_clients()
        await meeting_recorder.step()  # 将current_asr加入total_asr

        # 记录所有的asr结果到文件
        total_asr_path = self.getMeetingRootPath(meeting_id) / "total_asr.json"
        total_asr_path.write_bytes(
            TypeAdapter(List[AsrSentence]).dump_json(
                meeting_recorder.total_asr, indent=2
            )
        )
        logger_mid.info(f"[asr_path] {total_asr_path=}")

        self.close_logger(logger_mid)

    async def get_all_meetings(
        self,
        limit: int,
        offset: int,
        hash_id: Optional[str] = None,
        title: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        with Session(self.db_engine) as session:  # 使用同步上下文管理
            stmt = select(Meeting)
            # 动态过滤条件
            if hash_id:
                stmt = stmt.where(Meeting.hash_id == hash_id)
            if title:
                stmt = stmt.where(Meeting.topic.contains(title))  # type: ignore
            if start_time:
                stmt = stmt.where(Meeting.create_time >= start_time)
            if end_time:
                stmt = stmt.where(Meeting.create_time <= end_time)

            # 获取总数（过滤后）
            total = session.exec(
                select(func.count()).select_from(stmt.subquery())
            ).one()

            # 按照 meeting_id 降序排列；添加排序、分页
            result_meetings = session.exec(
                stmt.order_by(Meeting.meeting_id.desc())  # type: ignore
                .offset(offset)
                .limit(limit)
            ).all()
            return result_meetings, total

    async def get_ongoing_meetings(
        self,
        limit: int,
    ):
        with Session(self.db_engine) as session:  # 使用同步上下文管理
            stmt = select(Meeting).where(Meeting.status == "processing")

            # 获取总数（过滤后）
            total = session.exec(
                select(func.count()).select_from(stmt.subquery())
            ).one()

            # 按照 meeting_id 降序排列；添加排序、分页
            result_meetings = session.exec(
                stmt.order_by(Meeting.meeting_id.desc()).limit(limit)  # type: ignore
            ).all()
            return result_meetings, total

    async def send_audio_chunk(self, meeting_id: str, speaker_id: str, chunk: bytes):
        meeting_recorder = self.meeting_recorders.get(meeting_id)
        if meeting_recorder:
            await meeting_recorder.send_audio_chunk(speaker_id, chunk)

    async def toggle_mic(
        self, meeting_id: str, speaker_id: str, enable: bool, receive_time: datetime
    ):
        meeting_recorder = self.meeting_recorders.get(meeting_id)
        if meeting_recorder:
            await meeting_recorder.toggle_mic(speaker_id, enable, receive_time)

    async def write_pcm(
        self, meeting_id: str, data: bytes, user_id: str, receive_time: datetime
    ):
        meeting_recorder = self.meeting_recorders.get(meeting_id)
        if meeting_recorder:
            await asyncio.to_thread(
                meeting_recorder.write_pcm, data, user_id, receive_time
            )
