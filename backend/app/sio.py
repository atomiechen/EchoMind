from datetime import datetime

from app.deps import get_user_manager, get_meeting_manager, get_attendee_manager
from app.core.sio.models import AudioChunkMeta, ToggleMicrophone
from app.core.sio.sio_server import SioServer
from app.utils import get_logger
from app.config import settings


logger = get_logger()

sio = SioServer()


@sio.on("*")
async def any_event(event: str, sid: str, *args, **kwargs):
    logger.info(f"{event=} {sid=} {args=} {kwargs=}")


@sio.event
async def connect(sid: str, environ, auth):
    logger.info(f"connect {sid} {auth}")
    # 从连接中获取cookie，或者检查auth中的cookie
    cookie = environ.get("HTTP_COOKIE", None) or (
        auth.get("cookie", None) if auth else None
    )
    user = None
    print(f"cookie={cookie}")
    try:
        token = cookie.split("mytoken=")[1].split(";")[0] if cookie else None
        user = get_user_manager().setSid(token, sid) if token else None
    except Exception:
        pass
    if not user:
        # 断开连接
        logger.error(f"authentication failed: sid={sid} auth={auth}")
        raise ConnectionRefusedError("Socket.IO authentication failed")
    print(f"setSid sid={sid} userId={user.user_id} username={user.username}")

    # 将同一个userid的sid都加入到同一个room中，方便debug查看
    await sio.enter_room(sid, f"user-{user.username}")

    # TODO: 如果断开重连，要重新加入到room中
    meeting_id = get_attendee_manager().getMeetingIn(user)
    if meeting_id:
        meeting = get_meeting_manager().getMeetingById(str(meeting_id))
        if meeting and meeting.hash_id:
            print(f"sid={sid} userId={user.user_id} rejoin room {meeting.hash_id}")
            await sio.enter_room(sid, meeting.hash_id)


@sio.event
async def disconnect(sid):
    logger.info(f"disconnect {sid}")
    userId = get_user_manager().removeSid(sid)
    logger.info(f"removeSid sid={sid} userId={userId}")


@sio.on("audioChunk")
async def audio_chunk(sid, data: bytes, meta: AudioChunkMeta):
    receive_time = datetime.now()
    # 判断是否为合法用户，不合法则直接返回
    user = get_user_manager().findUser(sid)
    if not user:
        return
    # print(f"audioChunk {len(data)=} {meta.begin=} {meta.end=} {meta.encodingType=}")
    await get_meeting_manager().send_audio_chunk(
        meeting_id=meta.meeting_id,
        speaker_id=str(user.user_id),
        chunk=data,
    )
    if settings.save_pcm:
        # 保存pcm文件
        await get_meeting_manager().write_pcm(
            meta.meeting_id, data, str(user.user_id), receive_time
        )


@sio.on("toggleMic")
async def toggle_mic(sid, data: ToggleMicrophone):
    receive_time = datetime.now()
    # 判断是否为合法用户，不合法则直接返回
    user = get_user_manager().findUser(sid)
    if not user:
        return
    print(f"toggleMic {user.user_id=} {user.username=} {data.enable=}")
    await get_meeting_manager().toggle_mic(
        meeting_id=data.meeting_id,
        speaker_id=str(user.user_id),
        enable=data.enable,
        receive_time=receive_time,
    )
