from pydantic_socketio import FastAPISocketIO

from app.core.sio.models import (
    AllSummaries,
    Identification,
    ProcessStatus,
    RequestData,
    UpdateIssueData,
    SendAsrData,
)
from app.types import RoleType


class SioServer(FastAPISocketIO):
    """Custom Socket.IO server with additional functionality."""

    async def sendIdentification(self, sid: str, role: RoleType):
        await self.emit("identification", Identification(role=role), to=sid)

    async def sendMeetingEnd(self, sid: str):
        await self.emit("meetingEnd", to=sid)

    async def requestData(self, sid: str, cnt: int):
        await self.emit("requestData", RequestData(cnt=cnt), to=sid)

    async def sendCurrent(self, sid: str, data: SendAsrData):
        await self.emit("sendCurrent", data, to=sid)

    async def updateIssue(self, sid: str, data: UpdateIssueData):
        await self.emit("updateIssue", data, to=sid)

    async def statusAI(self, sid: str, running: bool):
        await self.emit("statusAI", ProcessStatus(running=running), to=sid)

    async def sendSummaryNew(self, sid: str, data: AllSummaries):
        await self.emit("sendSummaryNew", data, to=sid)
