from typing import List, Optional

from pydantic import BaseModel

from app.core.agent.models import Issue
from app.core.asr.models import SendAsrData as SendAsrData
from app.types import RoleType


class AudioChunk(BaseModel):
    meeting_id: str
    file_id: Optional[int]
    begin: int
    end: int
    base64: str
    encodingType: str


class AudioChunkMeta(BaseModel):
    meeting_id: str
    encodingType: str
    begin: int
    end: int


class ToggleMicrophone(BaseModel):
    meeting_id: str
    enable: bool
    timestamp: int


class Identification(BaseModel):
    role: RoleType


class RequestData(BaseModel):
    cnt: int


class ProcessStatus(BaseModel):
    running: bool


class UpdateIssueData(BaseModel):
    issue_map: List[Issue]
    chosen_id: str


class SummaryData(BaseModel):
    id: int
    summary: str


class AllSummaries(BaseModel):
    summaries: List[SummaryData]
