from typing import Dict
from sqlalchemy import Engine
from sqlmodel import Session, select, true

from app.models import Attendee


class AttendeeManager:
    def __init__(self, db_engine: Engine) -> None:
        self.db_engine = db_engine

    def addAttendee(self, meeting_id, user_id, is_master, nickname):
        with Session(self.db_engine) as session:
            new_attendee = Attendee(
                meeting_id=meeting_id,
                user_id=user_id,
                is_master=is_master,
                nickname=nickname,
            )
            session.add(new_attendee)
            session.commit()
            session.refresh(new_attendee)
        return new_attendee

    def leaveMeeting(self, meeting_id, user_id):
        with Session(self.db_engine) as session:
            statement = (
                select(Attendee)
                .where(Attendee.meeting_id == meeting_id)
                .where(Attendee.user_id == user_id)
            )
            # attendee = session.exec(statement).one_or_none()
            # 如果有多个，找到最后一个
            attendees = session.exec(statement).all()
            if attendees:
                attendee = attendees[-1]
                attendee.is_in_meeting = False
                attendee.is_master = False
                session.commit()

    def get_active_attendees(self, meeting_id):
        with Session(self.db_engine) as session:
            # statement = select(Attendee).where(Attendee.meeting_id == meeting_id).where(Attendee.is_in_meeting == True)
            statement = select(Attendee).where(Attendee.meeting_id == meeting_id)
            attendees = session.exec(statement).all()
            return attendees  # 返回所有在会议中的参会者，数据类型为list[Attendee]

    def change_master(self, meeting_id, user_id):
        with Session(self.db_engine) as session:
            statement = (
                select(Attendee)
                .where(Attendee.meeting_id == meeting_id)
                .where(Attendee.user_id == user_id)
            )
            attendee = session.exec(statement).one_or_none()
            if attendee:
                attendee.is_master = True
                session.commit()

    def get_speaker_map(self, meeting_id):
        attendees = self.get_active_attendees(meeting_id)
        # print(f"{attendees=}")
        speaker: Dict[str, str] = {}
        for person in attendees:
            assert person.nickname is not None
            assert person.user_id is not None
            speaker[str(person.user_id)] = person.nickname
        # print(f"{speaker=}")
        return speaker

    def getMeetingIn(self, user):
        with Session(self.db_engine) as session:
            # 找到满足条件的最后一个 attendee
            statement = (
                select(Attendee)
                .where(Attendee.user_id == user.user_id)
                .where(Attendee.is_in_meeting == true())
            )
            attendees = session.exec(statement).all()
            if attendees:
                attendee = attendees[-1]
                return attendee.meeting_id
            else:
                return None
