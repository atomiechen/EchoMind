import logging
from pathlib import Path
from typing import List
from handyllm import OpenAIClient, CacheManager
from handyllm.types import PathType

from app.core.agent.agent_realtime import AgentRealtime
from app.config import settings
from app.core.asr.models import AsrSentence
from app.core.sio.sio_server import SioServer
from app.utils import get_logger
from app.types import MeetingLanguageType


class MeetingAgent:
    def __init__(self, root_dir: PathType, meeting_language: MeetingLanguageType):
        self.meeting_language: MeetingLanguageType = meeting_language
        self.client = OpenAIClient(
            "async", endpoints=[model.model_dump() for model in settings.endpoints]
        )
        # 初始化agent，后续用于API调用
        print(f"meeting {root_dir=}")
        # 定义cache文件夹
        self.cm = CacheManager(
            base_dir=Path(root_dir, "online"),
            only_dump=True,
        )
        self.agent = AgentRealtime(
            client=self.client, base_dir=Path(root_dir, "online")
        )

        # 初始化数据
        self.sentences = []  # 本次会议中的所有句子
        self.logger = get_logger()
        self.file_handler = logging.FileHandler(Path(root_dir, "meeting_agent.log"))
        self.file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        self.file_handler.setFormatter(formatter)
        self.logger.addHandler(self.file_handler)

    def close(self):
        # 将log全部flush到文件，并关闭
        self.file_handler.close()
        # 关闭 api client
        self.client.close()

    async def proc_asr_results(
        self, asr_results: List[AsrSentence], sio: SioServer, room: str, manual=False
    ):
        raise NotImplementedError("This method should be overridden by subclasses.")
