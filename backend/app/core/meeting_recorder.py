from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List
import asyncio
import copy

from funasr_client import AsyncFunASRClient, FunASRMessageDecoded, async_funasr_client

from app.core.asr.models import AsrSentence
from app.config import settings
from app.types import MeetingLanguageType


# NOTE participant不包括host
# NOTE total_asr 不包括 current_asr
# NOTE total_pcm 不包括 current_pcm
class MeetingRecorder:
    def __init__(
        self,
        meeting_id: str,
        meeting_language: MeetingLanguageType,
        create_time: datetime,
        meeting_root_path: Path,
    ):
        self.meeting_id = meeting_id
        self.meeting_language: MeetingLanguageType = meeting_language
        self.create_time = create_time
        self.trigger_event = asyncio.Event()
        self.pcm_root_path = meeting_root_path / "pcm"

        self.current_asr: List[AsrSentence] = []  # 待发送给前端的asr
        self.current_asr_lock = asyncio.Lock()

        self.total_asr: List[AsrSentence] = []
        self.total_asr_lock = asyncio.Lock()

        self.funasr_client_dict: Dict[str, AsyncFunASRClient] = {}

        # 如果 funasr_client 还没建立好连接，但数据已经来了，就先buffer住
        self.buffer_dict: Dict[str, Deque[bytes]] = {}
        self.lock_dict: Dict[str, asyncio.Lock] = {}

    async def get_total_asr(self) -> List[AsrSentence]:
        async with self.total_asr_lock:
            total_asr = copy.deepcopy(self.total_asr)
        return total_asr

    async def get_current(self) -> List[AsrSentence]:
        async with self.current_asr_lock:
            current_asr = copy.deepcopy(self.current_asr)
        return current_asr

    async def step(self):
        # 将current_asr加入total_asr
        async with self.total_asr_lock:
            async with self.current_asr_lock:
                self.total_asr.extend(self.current_asr)
                self.current_asr.clear()
                # 按照起始时间排序
                self.total_asr.sort(key=lambda x: x.time_range[0])

    async def send_buffer(self, speaker_id: str):
        """发送buffered的数据"""
        client = self.funasr_client_dict[speaker_id]
        buffer_queue = self.buffer_dict[speaker_id]
        try:
            while buffer_queue:
                buffered_chunk = buffer_queue[0]
                await client.send(buffered_chunk)
                buffer_queue.popleft()
            return True
        except Exception:
            # 只要有异常就不发了
            print(
                f"send_buffer failed for speaker {speaker_id}, buffer size: {len(buffer_queue)}"
            )
            return False

    async def send_audio_chunk(self, speaker_id: str, chunk: bytes):
        async with self.lock_dict[speaker_id]:  # 防止多协程冲突
            self.buffer_dict[speaker_id].append(chunk)
            # 把buffered发出去
            await self.send_buffer(speaker_id)

    async def close_funasr_clients(self):
        for client in self.funasr_client_dict.values():
            await client.close()
        self.funasr_client_dict.clear()

    async def toggle_mic(self, speaker_id: str, enable: bool, receive_time: datetime):
        self.lock_dict.setdefault(speaker_id, asyncio.Lock())  # 创建lock如果不存在

        async with self.lock_dict[speaker_id]:
            self.buffer_dict.setdefault(speaker_id, deque())  # 创建buffer如果不存在

            # 创建 funasr client 如果不存在
            if speaker_id not in self.funasr_client_dict:

                async def on_asr_result(msg: FunASRMessageDecoded):
                    # print(f"{speaker_id=} FunASRMessageDecoded: {msg}")
                    # NOTE: funasr runtime服务bug：text为空字符串时mode键不存在
                    if not msg["text"] or msg["mode"] != "2pass-offline":
                        return
                    assert "real_timestamp" in msg
                    if self.meeting_language == "Chinese":
                        content = msg["text"]
                    else:
                        content = msg["text"].replace("，", ",").replace("。", ".")
                    self.current_asr.append(
                        AsrSentence(
                            content=content,
                            time_range=[
                                msg["real_timestamp"][0][0],
                                msg["real_timestamp"][-1][1],
                            ],
                            speaker_id=speaker_id,
                        )
                    )
                    self.current_asr.sort(key=lambda x: x.time_range[0])
                    self.trigger_event.set()  # 通知更新前端

                new_client = async_funasr_client(
                    uri=settings.funasr_uri,
                    mode="offline",
                    callback=on_asr_result,
                )
                self.funasr_client_dict[speaker_id] = new_client

            # 无论开启关闭，都需要把旧的client关掉、移除
            if speaker_id in self.funasr_client_dict:
                await self.send_buffer(speaker_id)
                old_client = self.funasr_client_dict[speaker_id]
                await old_client.close()

            # 开启麦克风
            if enable:
                # 计算服务端接收时间相对于会议开始时间的偏移量
                start_offset = int(
                    (receive_time - self.create_time).total_seconds() * 1000
                )
                cur_client = self.funasr_client_dict[speaker_id]
                # reset variables
                cur_client.start_time = start_offset
                await cur_client.connect()

    def write_pcm(self, data: bytes, user_id: str, receive_time: datetime):
        # 计算服务端接收时间相对于会议开始时间的偏移量
        start_offset = int((receive_time - self.create_time).total_seconds() * 1000)
        pcm_path = self.pcm_root_path / f"{user_id}_{start_offset}.pcm"
        pcm_path.parent.mkdir(parents=True, exist_ok=True)
        pcm_path.write_bytes(data)
