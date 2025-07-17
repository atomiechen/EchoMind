from datetime import datetime
from enum import IntEnum
from typing import Generic, List, Literal, Optional, TypeVar
from pydantic import ConfigDict
from sqlmodel import JSON, Column, Field, SQLModel, String

from app.types import AiType, MeetingLanguageType, StatusType


# enable generation of description based on attribute docstring (for OpenAPI)
class AnnotatedModel(SQLModel):
    model_config = ConfigDict(use_attribute_docstrings=True)  # type: ignore


class RegisterRequest(AnnotatedModel):
    username: str
    password: str


class Token(AnnotatedModel):
    access_token: str
    token_type: str


class MeetingStart(AnnotatedModel):
    topic: str
    nickname: str

    hotwords: Optional[List[str]] = None

    meeting_resume_hash_id: str
    type: AiType

    meeting_language: MeetingLanguageType


class Code(IntEnum):
    SUCCESS = 0
    FAILED = 1
    NOT_MEETING_HOST = 2
    MEETING_NOT_FOUND = 3
    AGENT_NOT_FOUND = 4
    WRONG_AGENT = 5
    INVALID_NODE = 6
    ANALYSIS_GENERATING = 7
    USER_NOT_FOUND = 8
    WRONG_PASSWORD = 9
    USER_EXISTED = 10
    INVALID_PASSWORD = 11


T = TypeVar("T", bound=Code)


class BaseResponse(AnnotatedModel, Generic[T]):
    code: T


class SuccessResponse(BaseResponse):
    code: Literal[Code.SUCCESS] = Code.SUCCESS


class RegisterResponse(BaseResponse):
    code: Literal[Code.SUCCESS, Code.USER_EXISTED, Code.INVALID_PASSWORD]


class LoginResponse(BaseResponse):
    code: Literal[Code.SUCCESS, Code.WRONG_PASSWORD, Code.USER_NOT_FOUND]


class UserResponse(SuccessResponse):
    username: str


class MeetingNotFoundResponse(BaseResponse):
    code: Literal[Code.MEETING_NOT_FOUND] = Code.MEETING_NOT_FOUND


class NotMeetingHostResponse(BaseResponse):
    code: Literal[Code.NOT_MEETING_HOST] = Code.NOT_MEETING_HOST


class AgentNotFoundResponse(BaseResponse):
    code: Literal[Code.AGENT_NOT_FOUND] = Code.AGENT_NOT_FOUND


class WrongAgentResponse(BaseResponse):
    code: Literal[Code.WRONG_AGENT] = Code.WRONG_AGENT


class MeetingStartResponse(SuccessResponse):
    meeting_id: str
    meeting_hash_id: str


class MeetingJoinResponse(SuccessResponse):
    meeting_id: str
    meeting_hash_id: str
    topic: str


class MeetingLeaveResponse(BaseResponse):
    code: Literal[Code.SUCCESS, Code.FAILED]


class MeetingStopResponse(BaseResponse):
    code: Literal[Code.SUCCESS, Code.FAILED]


class AddNodeResponse(SuccessResponse):
    full_id: str


class InvalidNodeResponse(BaseResponse):
    code: Literal[Code.INVALID_NODE] = Code.INVALID_NODE


class EvaluationItem(AnnotatedModel):
    name: str
    active: int
    contribution: int
    comment: str


class MeetingListRequest(AnnotatedModel):
    hash_id: Optional[str] = None
    title: Optional[str] = None
    start_time: Optional[datetime] = None


class MeetingItem(AnnotatedModel):
    id: str
    hash_id: str
    topic: str
    create_time: str
    create_by: str
    hotwords: Optional[List[str]]
    status: StatusType
    master: str
    meeting_language: MeetingLanguageType


class MeetingListResponse(BaseResponse):
    meetings: List[MeetingItem]
    total: int


# Blow are database models


class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)  # 用户ID，自增主键
    username: str = Field(unique=True)  # 用户名
    password: str  # 密码
    created_at: datetime = Field(default_factory=datetime.now)  # 用户创建时间


# 实时研讨系统 Meeting 类
class Meeting(SQLModel, table=True):
    meeting_id: Optional[int] = Field(
        default=None, primary_key=True
    )  # 会议ID，自增主键
    # hash_id 传入前做唯一性检查判断
    hash_id: str = Field(index=True, unique=True)  # 会议哈希ID
    # hash_id: str = Field(default_factory=get_meeting_hash)
    create_time: datetime = Field(default_factory=datetime.now)  # 会议创建时间
    create_by: Optional[int] = Field(
        default=None, foreign_key="user.user_id"
    )  # 会议创建者ID

    # ref: https://github.com/fastapi/sqlmodel/issues/57#issuecomment-2416155216
    status: StatusType = Field(sa_type=String, default="processing")

    master_id: Optional[int] = Field(
        default=None, foreign_key="user.user_id"
    )  # 会议主持人ID
    topic: str  # 会议主题

    # ref: https://github.com/fastapi/sqlmodel/issues/178#issuecomment-989908481
    hot_words: Optional[List[str]] = Field(sa_column=Column(JSON), default=None)  # 热词

    analysis_status: Literal["Not Started", "In Progress", "Completed", "Failed"] = (
        Field(sa_type=String, default="Not Started")
    )

    ai_type: AiType = Field(sa_type=String)
    meeting_language: MeetingLanguageType = Field(sa_type=String)


class Attendee(SQLModel, table=True):
    attendee_id: Optional[int] = Field(
        default=None, primary_key=True
    )  # 参会者ID，自增主键
    meeting_id: Optional[int] = Field(
        default=None, foreign_key="meeting.meeting_id"
    )  # 会议ID
    user_id: Optional[int] = Field(default=None, foreign_key="user.user_id")  # 用户ID
    is_master: Optional[bool] = False  # 是否为主持人
    nickname: Optional[str] = None  # 昵称
    is_in_meeting: Optional[bool] = True  # 是否在会议中
