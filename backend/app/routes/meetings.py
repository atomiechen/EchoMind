from datetime import datetime
from typing import List, Literal, Optional, Union
from pydantic import TypeAdapter
from typing_extensions import Annotated
from fastapi.responses import FileResponse, StreamingResponse
from fastapi import (
    APIRouter,
    Body,
    HTTPException,
    Header,
    Path,
    Query,
    status,
)

from app.deps import (
    MeetingAgentDep,
    MeetingDepPost,
    SioDep,
    UserDep,
    DependsUser,
    UserManagerDep,
    MeetingManagerDep,
    AttendeeManagerDep,
)
from app.core.asr.models import AsrSentence, TotalData
from app.core.meeting_agent_gamma import MeetingAgentGamma
from app.core.meeting_agent_summary import MeetingAgentSummary
from app.models import (
    AddNodeResponse,
    Code,
    InvalidNodeResponse,
    MeetingItem,
    MeetingJoinResponse,
    MeetingLeaveResponse,
    MeetingListResponse,
    MeetingStart,
    MeetingStartResponse,
    MeetingStopResponse,
    NotMeetingHostResponse,
    SuccessResponse,
    WrongAgentResponse,
)
from app.utils.log import get_logger
from app.core.util import get_max_numbered_parsed_issues


api_router = APIRouter()

logger = get_logger()

Embed_Body_Str = Annotated[str, Body(embed=True)]
Embed_Body_Bool = Annotated[bool, Body(embed=True)]


# 开始会议：base & echo
@api_router.post("/api/meetingStart")
async def start_meeting(
    data: MeetingStart,
    user: UserDep,
    sio: SioDep,
    meeting_manager: MeetingManagerDep,
    attendee_manager: AttendeeManagerDep,
    user_manager: UserManagerDep,
) -> MeetingStartResponse:
    logger.info("start_meeting")
    nickname = data.nickname
    topic = data.topic
    hot_words = data.hotwords
    meeting_resume_hash_id = data.meeting_resume_hash_id
    meeting_language = data.meeting_language  # chinese / english
    ai_type = data.type

    logger.info(f"""
ai_type: {ai_type}
meeting.type: {data.type}
meeting_language: {meeting_language}""")

    # hot_words_str = json.dumps(hot_words, ensure_ascii=False, indent=4)
    assert user.user_id
    # 创建一个新的会议
    if meeting_resume_hash_id and meeting_resume_hash_id != "":
        meeting = meeting_manager.createMeetingResume(
            meeting_resume_hash_id,
            user.user_id,
            ai_type,
            sio,
            attendee_manager,
            hot_words,
            meeting_language,
        )
    else:
        meeting = meeting_manager.createMeeting(
            user.user_id,
            topic,
            ai_type,
            sio,
            attendee_manager,
            hot_words,
            meeting_language,
        )
    assert meeting.meeting_id
    # 创建一个新的参会者
    attendee = attendee_manager.addAttendee(
        meeting.meeting_id, user.user_id, is_master=True, nickname=nickname
    )
    # 加入 socket 会议室
    room = meeting.hash_id
    await user_manager.joinRoom(sio, user.user_id, room)

    # 重启会议
    if meeting_resume_hash_id and meeting_resume_hash_id != "":
        meeting_agent = meeting_manager.meeting_agents.get(str(meeting.meeting_id))
        if isinstance(meeting_agent, MeetingAgentGamma):
            await meeting_agent.gamma_send_issue_map(sio, room)

    # 向前端返回
    return MeetingStartResponse(
        meeting_id=str(meeting.meeting_id),
        meeting_hash_id=meeting.hash_id,
    )


@api_router.post("/api/joinMeeting")
async def join_meeting(
    meeting: MeetingDepPost,
    meeting_agent: MeetingAgentDep,
    nickname: Embed_Body_Str,
    user: UserDep,
    sio: SioDep,
    attendee_manager: AttendeeManagerDep,
    user_manager: UserManagerDep,
) -> MeetingJoinResponse:
    logger.info("join_meeting")
    assert user.user_id

    # 创建一个新的参会者
    attendee = attendee_manager.addAttendee(
        meeting.meeting_id, user.user_id, is_master=False, nickname=nickname
    )
    # 加入 socket 会议室
    await user_manager.joinRoom(sio, user.user_id, meeting.hash_id)

    if isinstance(meeting_agent, MeetingAgentGamma):
        await meeting_agent.gamma_send_issue_map(sio, meeting.hash_id)
    #  TODO meeting_agent_summary 需要发送当前所有的
    return MeetingJoinResponse(
        meeting_id=str(meeting.meeting_id),
        meeting_hash_id=meeting.hash_id,
        topic=meeting.topic,
    )


# 结束会议：base & echo
@api_router.post("/api/meetingEnd")
async def end_meeting(
    meeting: MeetingDepPost,
    user: UserDep,
    sio: SioDep,
    meeting_manager: MeetingManagerDep,
    attendee_manager: AttendeeManagerDep,
) -> Union[MeetingStopResponse, NotMeetingHostResponse]:
    logger.info("end_meeting")
    if meeting.master_id != user.user_id:
        return NotMeetingHostResponse()

    # 结束会议
    code = await meeting_manager.endMeeting(
        str(meeting.meeting_id), sio, attendee_manager
    )
    return MeetingStopResponse(
        code=code,
    )


# 离开会议：base & echo
@api_router.post("/api/leaveMeeting")
async def leave_meeting(
    meeting: MeetingDepPost,
    user: UserDep,
    sio: SioDep,
    meeting_manager: MeetingManagerDep,
    attendee_manager: AttendeeManagerDep,
    user_manager: UserManagerDep,
) -> MeetingLeaveResponse:
    logger.info("leave_meeting")
    assert user.user_id

    # 离开会议
    attendee_manager.leaveMeeting(meeting.meeting_id, user.user_id)
    await user_manager.leaveRoom(sio, user.user_id, meeting.hash_id)

    attendees = attendee_manager.get_active_attendees(
        meeting.meeting_id
    )  # 获取所有在会议中的参会者
    # 如果没有参会者了，结束会议
    if len(attendees) == 0:
        code = await meeting_manager.endMeeting(
            str(meeting.meeting_id), sio, attendee_manager
        )
        return MeetingLeaveResponse(
            code=code,
        )
    # 如果是主持人离开，重新选举主持人
    if meeting.master_id == user.user_id:
        new_master = attendees[0]
        assert new_master.user_id is not None
        meeting_manager.updateMasterId(str(meeting.meeting_id), new_master.user_id)
        # 通知新主持人
        await user_manager.sendIdentification(sio, new_master.user_id, "host")
    return MeetingLeaveResponse(
        code=Code.SUCCESS,
    )


# 在进入会议的时候请求所有的数据：base & echo
@api_router.post("/api/requestTotal")
async def request_total(
    meeting: MeetingDepPost,
    meeting_agent: MeetingAgentDep,
    user: UserDep,
    sio: SioDep,
    meeting_manager: MeetingManagerDep,
    attendee_manager: AttendeeManagerDep,
    user_manager: UserManagerDep,
) -> TotalData:
    assert user.user_id
    meeting_id = str(meeting.meeting_id)

    # 向前端返回截至目前的全部asr转写结果
    result = await meeting_manager.getTotalAsrResult(meeting_id)
    if result is None:  # 注意这里允许空列表，但不允许None
        raise Exception(f"Unknown error: no total asr result {meeting_id=}")

    role = "host" if meeting.master_id == user.user_id else "participant"

    if meeting.ai_type == "document":
        speaker = attendee_manager.get_speaker_map(meeting_id)
        return TotalData(
            speaker=speaker,
            sentences=result,
            issue_map=[],
            meeting_id=meeting_id,
            meeting_hash_id=meeting.hash_id,
            topic=str(meeting.topic),
            role=role,
            ai_type=meeting.ai_type,
        )
    else:
        assert isinstance(meeting_agent, MeetingAgentGamma)
        issue_map = meeting_agent.parsed_issues_new.issue_map_list_without_delete
        speaker = attendee_manager.get_speaker_map(meeting_id)

        # 通知身份（可能有同一账号多端登录的问题，但按理来说不应该在这里通知）
        await user_manager.sendIdentification(sio, user.user_id, role)

        return TotalData(
            speaker=speaker,
            sentences=result,
            issue_map=issue_map,
            meeting_id=meeting_id,
            meeting_hash_id=meeting.hash_id,
            topic=str(meeting.topic),
            role=role,
            ai_type=meeting.ai_type,
        )


# 用户更改会议标题：base & echo
@api_router.post("/api/changeTitle")
async def change_title(
    meeting: MeetingDepPost,
    title: Embed_Body_Str,
    user: UserDep,
    meeting_manager: MeetingManagerDep,
) -> Union[SuccessResponse, NotMeetingHostResponse]:
    assert user.user_id
    if meeting.master_id != user.user_id:
        return NotMeetingHostResponse()
    meeting_manager.updateTopic(str(meeting.meeting_id), topic=title)
    return SuccessResponse()


# 用户更新热词：base & echo
@api_router.post("/api/updateHotWords")
async def update_hot_words(
    meeting: MeetingDepPost,
    hot_words: Annotated[List[str], Body(embed=True)],
    user: UserDep,
    meeting_manager: MeetingManagerDep,
) -> Union[SuccessResponse, NotMeetingHostResponse]:
    assert user.user_id
    if meeting.master_id != user.user_id:
        return NotMeetingHostResponse()
    meeting_manager.updateHotWords(str(meeting.meeting_id), hot_words)
    return SuccessResponse()


# 用户主动触发更新
@api_router.post("/api/manualUpdate")
async def manual_update(
    meeting_agent: MeetingAgentDep,
    user: UserDep,
) -> Union[SuccessResponse, WrongAgentResponse]:
    logger.info("generate graph")
    assert user.user_id
    # print("meeting hash id: ", meeting_hash_id)
    # meeting_id = meeting.meeting_id
    # print("meeting_id: ", meeting_id)
    if isinstance(meeting_agent, MeetingAgentGamma):
        meeting_agent.auto_generate = True
        meeting_agent.logger.info("[manual_generate]")
    elif isinstance(meeting_agent, MeetingAgentSummary):
        meeting_agent.auto_generate = True
        # meeting_agent.stop_summary = False
        meeting_agent.logger.info("[manual_generate]")
    else:
        return WrongAgentResponse()
    return SuccessResponse()


# 用户选择节点：注意需要判断选择的节点和当前的节点是否是一样的
# TODO 对于dialog何时清空的定义
@api_router.post("/api/chooseNode")
async def choose_node(
    meeting: MeetingDepPost,
    meeting_agent: MeetingAgentDep,
    chosenNodeId: Embed_Body_Str,
    sio: SioDep,
) -> Union[SuccessResponse, WrongAgentResponse]:
    """
    {
        "chosenNodeId": "full id"
        "meeting_hash_id": "hash id",
    }
    """
    # get meeting agent
    if isinstance(meeting_agent, MeetingAgentGamma):
        await meeting_agent.set_chosen_node(chosenNodeId, sio, room=meeting.hash_id)
        return SuccessResponse()
    else:
        return WrongAgentResponse()


# 用户修改某个节点的content
@api_router.post("/api/modifyNode")
async def modify_node(
    meeting: MeetingDepPost,
    meeting_agent: MeetingAgentDep,
    full_id: Embed_Body_Str,
    content: Embed_Body_Str,
    sio: SioDep,
) -> Union[SuccessResponse, WrongAgentResponse]:
    """
    前端->后端：
    {
        "meeting_hash_id": str,
        "full_id": str,
        "content": str
    }
    """
    # get data
    logger.info("user modify node")

    # run agent
    if isinstance(meeting_agent, MeetingAgentGamma):
        room = meeting.hash_id
        await meeting_agent.gamma_op_node(
            op="modify", sio=sio, room=room, full_id=str(full_id), content=content
        )
        meeting_agent.logger.info(f"修改节点：{full_id}，内容：{content}")
        return SuccessResponse()
    else:
        return WrongAgentResponse()


# 用户新增一个节点
@api_router.post("/api/addNode")
async def add_node(
    meeting: MeetingDepPost,
    meeting_agent: MeetingAgentDep,
    # using both `alias` and `validation_alias` due to [BUG](https://github.com/fastapi/fastapi/issues/10286)
    node_type: Annotated[
        Literal["ISSUE", "POSITION"],
        Body(embed=True, alias="type", validation_alias="type"),
    ],
    father_id: Embed_Body_Str,
    content: Embed_Body_Str,
    sio: SioDep,
) -> Union[
    AddNodeResponse,
    InvalidNodeResponse,
    WrongAgentResponse,
]:
    # TODO 这里加了一个 suggestion_id，后端需要做对应修改
    """
    前端
    {
        "type": "ISSUE" / "POSITION",
        "father_id": "父节点的full id",
        "content": "",
        "meeting_hash_id": "",
        "suggestion_id": ""
    }
    后端
    {
        "code": 0,
        "full_id": "这个节点的full id"
    }
    """
    logger.info("user add node")
    # get data
    # TODO 把suggestion_id传给agent

    # judge meeting agent type
    if isinstance(meeting_agent, MeetingAgentGamma):
        room = meeting.hash_id
        full_id_dict = await meeting_agent.gamma_op_node(
            op="add",
            sio=sio,
            room=room,
            node_type=node_type,
            father_id=father_id,
            content=content,
        )
        full_id = full_id_dict["full_id"]
        if full_id == "0":
            return InvalidNodeResponse()
        return AddNodeResponse(full_id=full_id)
    else:
        return WrongAgentResponse()


# 用户删除某个节点
@api_router.post("/api/deleteNode")
async def delete_node(
    meeting: MeetingDepPost,
    meeting_agent: MeetingAgentDep,
    full_id: Embed_Body_Str,
    sio: SioDep,
) -> Union[SuccessResponse, WrongAgentResponse]:
    """
    前端
    {
        "full_id": "",  # issue/position的full id
        "meeting_hash_id": ""
    }
    """
    # get data
    logger.info(f"user delete node {full_id} ")

    # judge meeting agent type
    if isinstance(meeting_agent, MeetingAgentGamma):
        room = meeting.hash_id
        await meeting_agent.gamma_op_node(
            op="delete", sio=sio, room=room, full_id=full_id
        )
        return SuccessResponse()
    else:
        return WrongAgentResponse()


# 保存前端发来的信息
@api_router.post("/api/sendUserSummary")
async def send_user_summary(
    meeting_agent: MeetingAgentDep,
    edit_history: List,
) -> Union[SuccessResponse, WrongAgentResponse]:
    """
    {
        "meeting_hash_id": "hash id",
        "edit_history": "list"
    }
    """
    if isinstance(meeting_agent, MeetingAgentSummary):
        await meeting_agent.save_history(edit_history)
        return SuccessResponse()
    else:
        return WrongAgentResponse()


# 获取所有的会议
@api_router.get("/api/getAllMeetings")
async def get_all_meetings(
    meeting_manager: MeetingManagerDep,
    attendee_manager: AttendeeManagerDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1)] = 50,
    hash_id: Optional[str] = None,
    title: Optional[str] = None,
    start_time: Optional[datetime] = None,
) -> MeetingListResponse:
    """
    输入
    {
      hash_id: hash_id,
      title: title,
      start_time: startTime,
    }
    输出
    type MeetingItem = {
        id: number;
        hash_id: number;
        topic: string;
        created_by: string;
        created_time: string;
        status: string;
        master: string;
        hot_words: string;
        anlysisStatus: string;
    };
    """
    # get all meetings
    # hash_id = data.hash_id
    # title = data.title
    # start_time = data.start_time
    meetings, total = await meeting_manager.get_all_meetings(
        hash_id=hash_id, title=title, start_time=start_time, offset=offset, limit=limit
    )
    res: List[MeetingItem] = []
    for meeting in meetings:
        speaker = attendee_manager.get_speaker_map(meeting.meeting_id)
        # print(f"{speaker=}")
        res.append(
            MeetingItem(
                id=str(meeting.meeting_id),
                hash_id=meeting.hash_id,
                topic=meeting.topic,
                create_by=speaker[str(meeting.create_by)]
                if str(meeting.create_by) in speaker
                else "",
                create_time=meeting.create_time.isoformat(),
                status=meeting.status,
                master=speaker[str(meeting.master_id)]
                if str(meeting.master_id) in speaker
                else "",
                hotwords=meeting.hot_words,
                meeting_language=meeting.meeting_language,
            )
        )

    # return {"code": 0, "meetings": res}
    return MeetingListResponse(
        code=Code.SUCCESS,
        meetings=res,
        total=total,
    )


@api_router.get("/api/ongoingMeetings")
async def get_ongoing_meetings(
    meeting_manager: MeetingManagerDep,
    attendee_manager: AttendeeManagerDep,
    limit: Annotated[int, Query(ge=1)],
) -> MeetingListResponse:
    """获取所有正在进行中的会议"""
    ongoing_meetings, total = await meeting_manager.get_ongoing_meetings(limit=limit)
    res: List[MeetingItem] = []
    for meeting in ongoing_meetings:
        speaker = attendee_manager.get_speaker_map(meeting.meeting_id)
        res.append(
            MeetingItem(
                id=str(meeting.meeting_id),
                hash_id=meeting.hash_id,
                topic=meeting.topic,
                create_by=speaker[str(meeting.create_by)]
                if str(meeting.create_by) in speaker
                else "",
                create_time=meeting.create_time.isoformat(),
                status=meeting.status,
                master=speaker[str(meeting.master_id)]
                if str(meeting.master_id) in speaker
                else "",
                hotwords=meeting.hot_words,
                meeting_language=meeting.meeting_language,
            )
        )
    return MeetingListResponse(
        code=Code.SUCCESS,
        meetings=res,
        total=total,
    )


@api_router.post("/api/requestRecord")
async def request_record(
    meeting: MeetingDepPost,
    attendee_manager: AttendeeManagerDep,
    meeting_manager: MeetingManagerDep,
    user: UserDep,
) -> TotalData:
    speaker = attendee_manager.get_speaker_map(meeting.meeting_id)

    root_path = meeting_manager.getMeetingRootPath(str(meeting.meeting_id))
    latest_issue_map_path = root_path / "online" / "issue_map"
    asr_path = root_path / "total_asr.json"

    old_parsed_issue, old_topic = get_max_numbered_parsed_issues(latest_issue_map_path)
    sentences = TypeAdapter(List[AsrSentence]).validate_json(
        (asr_path).read_text(encoding="utf-8")
    )

    return TotalData(
        speaker=speaker,
        sentences=sentences,
        issue_map=old_parsed_issue,
        meeting_id=str(meeting.meeting_id),
        meeting_hash_id=meeting.hash_id,
        topic=str(meeting.topic),
        role="host" if meeting.master_id == user.user_id else "participant",
        ai_type=meeting.ai_type,
    )


@api_router.get("/api/downloadAudio/{meeting_id}", dependencies=[DependsUser])
async def download_audio(
    meeting_id: Annotated[str, Path()],
    meeting_manager: MeetingManagerDep,
) -> FileResponse:
    meeting = meeting_manager.getMeetingById(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found"
        )
    file_path = (
        meeting_manager.getMeetingRootPath(str(meeting.meeting_id))
        / f"{meeting.meeting_id}.wav"
    )
    filename = f"{meeting.meeting_id}.wav"  # 给前端的文件名，可以写死
    try:
        # 提供filename参数以设置Content-Disposition，让浏览器知道下载文件的名称
        return FileResponse(file_path, filename=filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"File not found: {e}"
        )


def gen_chunk_stream(file_path, start: int, end: int, chunk_size: int):
    # `start` and `end` parameters are inclusive due to specification
    with open(file_path, mode="rb") as file:
        file.seek(start)
        pos = file.tell()
        while pos <= end:
            bytes_to_read = min(chunk_size, end + 1 - pos)
            yield file.read(bytes_to_read)
            pos = file.tell()


CHUNK_SIZE = 10000  # 10 KB


@api_router.get("/audio/{meeting_id}")
async def get_audio(
    meeting_id: str,
    meeting_manager: MeetingManagerDep,
    range: Optional[str] = Header(None),
) -> StreamingResponse:
    meeting = meeting_manager.getMeetingById(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found"
        )
    logger.info(f"get_audio range: {range}, meeting_id: {meeting.meeting_id}")
    # 该方法特殊，因为前端需要使用路径参数指定mid，所以不能使用Body参数
    wav_path = (
        meeting_manager.getMeetingRootPath(str(meeting.meeting_id))
        / f"{meeting.meeting_id}.wav"
    )
    audio_type = "wav"
    filesize = wav_path.stat().st_size
    # `start` and `end` parameters are inclusive due to specification
    if range:
        start, end = range.replace("bytes=", "").split("-")
        start = int(start) if start else 0
        end = int(end) if end else filesize - 1
    else:
        start, end = 0, filesize - 1
    headers = {
        "Content-Range": f"bytes {str(start)}-{str(end)}/{filesize}",
        "Accept-Ranges": "bytes",
    }
    return StreamingResponse(
        gen_chunk_stream(wav_path, start, end, CHUNK_SIZE),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
        media_type=f"audio/{audio_type}",
    )
