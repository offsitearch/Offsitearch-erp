"""Meeting scheduling service.

Meeting CRUD, RSVP tracking, and attendee notifications.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.modules.meetings.models import Meeting, MeetingAttendee
from app.modules.meetings.schemas import MeetingCreate, MeetingUpdate
from app.modules.notifications.service import notify
from app.utils.enums import RsvpStatus
from app.utils.errors import MeetingError


async def _profile(db: AsyncSession, meeting: Meeting, current_user_id: int | None = None) -> dict:
    attendee_rows = (
        await db.execute(
            select(MeetingAttendee, User.name, User.email)
            .join(User, User.id == MeetingAttendee.user_id)
            .where(MeetingAttendee.meeting_id == meeting.id)
            .order_by(MeetingAttendee.id)
        )
    ).all()
    organizer = None
    if meeting.organizer_id is not None:
        organizer_row = await db.get(User, meeting.organizer_id)
        organizer = organizer_row.name if organizer_row else None
    my_rsvp = None
    if current_user_id is not None:
        mine = await db.execute(
            select(MeetingAttendee).where(
                MeetingAttendee.meeting_id == meeting.id,
                MeetingAttendee.user_id == current_user_id,
            )
        )
        mine_row = mine.scalar_one_or_none()
        if mine_row is not None:
            my_rsvp = mine_row.rsvp_status.value
    return {
        "id": meeting.id,
        "title": meeting.title,
        "description": meeting.description,
        "meeting_type": meeting.meeting_type.value,
        "scheduled_at": meeting.scheduled_at,
        "duration_minutes": meeting.duration_minutes,
        "location": meeting.location,
        "meeting_link": meeting.meeting_link,
        "status": meeting.status.value,
        "organizer_id": meeting.organizer_id,
        "organizer_name": organizer,
        "attendees": [
            {
                "user_id": attendee.user_id,
                "name": name,
                "email": email,
                "rsvp_status": attendee.rsvp_status.value,
            }
            for attendee, name, email in attendee_rows
        ],
        "my_rsvp": my_rsvp,
    }


async def list_meetings(
    db: AsyncSession,
    user: User,
    include_all: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    stmt = select(Meeting).order_by(Meeting.scheduled_at.desc())
    if not include_all:
        attendee_sub = select(MeetingAttendee.meeting_id).where(MeetingAttendee.user_id == user.id)
        stmt = stmt.where((Meeting.organizer_id == user.id) | (Meeting.id.in_(attendee_sub)))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    meetings = (
        (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    )
    if not meetings:
        return [], total
    meeting_ids = [meeting.id for meeting in meetings]
    attendee_rows = (
        await db.execute(
            select(MeetingAttendee, User.name, User.email)
            .join(User, User.id == MeetingAttendee.user_id)
            .where(MeetingAttendee.meeting_id.in_(meeting_ids))
            .order_by(MeetingAttendee.id)
        )
    ).all()
    attendees_by_meeting: dict[int, list] = {}
    for attendee, name, email in attendee_rows:
        attendees_by_meeting.setdefault(attendee.meeting_id, []).append((attendee, name, email))

    organizer_ids = {m.organizer_id for m in meetings if m.organizer_id is not None}
    organizer_names: dict[int, str] = {}
    if organizer_ids:
        org_rows = await db.execute(select(User.id, User.name).where(User.id.in_(organizer_ids)))
        organizer_names = {user_id: name for user_id, name in org_rows.all()}

    my_rsvp_by_meeting: dict[int, str] = {}
    if not include_all:
        mine = await db.execute(
            select(MeetingAttendee.meeting_id, MeetingAttendee.rsvp_status).where(
                MeetingAttendee.meeting_id.in_(meeting_ids),
                MeetingAttendee.user_id == user.id,
            )
        )
        my_rsvp_by_meeting = {
            meeting_id: rsvp_status.value for meeting_id, rsvp_status in mine.all()
        }

    items = [
        {
            "id": meeting.id,
            "title": meeting.title,
            "description": meeting.description,
            "meeting_type": meeting.meeting_type.value,
            "scheduled_at": meeting.scheduled_at,
            "duration_minutes": meeting.duration_minutes,
            "location": meeting.location,
            "meeting_link": meeting.meeting_link,
            "status": meeting.status.value,
            "organizer_id": meeting.organizer_id,
            "organizer_name": organizer_names.get(meeting.organizer_id)
            if meeting.organizer_id
            else None,
            "attendees": [
                {
                    "user_id": attendee.user_id,
                    "name": name,
                    "email": email,
                    "rsvp_status": attendee.rsvp_status.value,
                }
                for attendee, name, email in attendees_by_meeting.get(meeting.id, [])
            ],
            "my_rsvp": my_rsvp_by_meeting.get(meeting.id),
        }
        for meeting in meetings
    ]
    return items, total


async def _sync_attendees(db: AsyncSession, meeting: Meeting, attendee_ids: list[int]) -> None:
    if attendee_ids is None:
        return
    existing = (
        (await db.execute(select(MeetingAttendee).where(MeetingAttendee.meeting_id == meeting.id)))
        .scalars()
        .all()
    )
    for link in existing:
        if link.user_id not in attendee_ids:
            await db.delete(link)
    seen: set[int] = set()
    new_attendees: list[int] = []
    for user_id in attendee_ids:
        if user_id in seen:
            continue
        seen.add(user_id)
        if not any(link.user_id == user_id for link in existing):
            user = await db.get(User, user_id)
            if user is None:
                raise MeetingError(f"User {user_id} not found", 404)
            db.add(MeetingAttendee(meeting_id=meeting.id, user_id=user_id))
            new_attendees.append(user_id)
    await db.flush()
    for user_id in new_attendees:
        await notify(
            db,
            user_id,
            "Meeting invitation",
            f"You are invited to '{meeting.title}'",
            "meeting",
            f"/meetings/{meeting.id}",
        )


async def create_meeting(db: AsyncSession, payload: MeetingCreate, user: User) -> dict:
    meeting = Meeting(
        title=payload.title,
        description=payload.description,
        meeting_type=payload.meeting_type,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        location=payload.location,
        meeting_link=payload.meeting_link,
        organizer_id=user.id,
    )
    db.add(meeting)
    await db.flush()
    await _sync_attendees(db, meeting, payload.attendee_ids)
    await db.commit()
    await db.refresh(meeting)
    return await _profile(db, meeting, user.id)


async def update_meeting(
    db: AsyncSession, meeting: Meeting, payload: MeetingUpdate, user: User
) -> dict:
    if payload.title is not None:
        meeting.title = payload.title
    if payload.description is not None:
        meeting.description = payload.description
    if payload.meeting_type is not None:
        meeting.meeting_type = payload.meeting_type
    if payload.scheduled_at is not None:
        meeting.scheduled_at = payload.scheduled_at
    if payload.duration_minutes is not None:
        meeting.duration_minutes = payload.duration_minutes
    if payload.location is not None:
        meeting.location = payload.location
    if payload.meeting_link is not None:
        meeting.meeting_link = payload.meeting_link
    if payload.status is not None:
        from app.utils.state_machines import assert_transition

        assert_transition(meeting.status, payload.status, "meeting")
        meeting.status = payload.status
    await _sync_attendees(db, meeting, payload.attendee_ids)
    await db.commit()
    await db.refresh(meeting)
    return await _profile(db, meeting, user.id)


async def delete_meeting(db: AsyncSession, meeting: Meeting) -> None:
    await db.delete(meeting)
    await db.commit()


async def rsvp(db: AsyncSession, meeting: Meeting, user: User, status: RsvpStatus) -> dict:
    result = await db.execute(
        select(MeetingAttendee).where(
            MeetingAttendee.meeting_id == meeting.id, MeetingAttendee.user_id == user.id
        )
    )
    attendee = result.scalar_one_or_none()
    if attendee is None:
        if user.id == meeting.organizer_id:
            raise MeetingError("Organizers confirm via the meeting page", 409)
        raise MeetingError("You are not an attendee of this meeting", 404)
    attendee.rsvp_status = status
    await db.commit()
    return await _profile(db, meeting, user.id)
