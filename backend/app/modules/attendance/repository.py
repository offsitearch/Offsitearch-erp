from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.models import Attendance


class AttendanceRepository:
    async def get_by_user_date(
        self, db: AsyncSession, user_id: int, date_: date
    ) -> Attendance | None:
        result = await db.execute(
            select(Attendance).where(Attendance.user_id == user_id, Attendance.date == date_)
        )
        return result.scalar_one_or_none()

    async def get(self, db: AsyncSession, record_id: int) -> Attendance | None:
        return await db.get(Attendance, record_id)

    async def list_by_user_month(
        self, db: AsyncSession, user_id: int, year: int, month: int
    ) -> list[Attendance]:
        result = await db.execute(
            select(Attendance)
            .where(
                Attendance.user_id == user_id,
                Attendance.date >= date(year, month, 1),
                Attendance.date < date(year + 1, 1, 1)
                if month == 12
                else Attendance.date < date(year, month + 1, 1),
            )
            .order_by(Attendance.date)
        )
        return list(result.scalars().all())

    async def add(self, db: AsyncSession, attendance: Attendance) -> Attendance:
        db.add(attendance)
        await db.commit()
        await db.refresh(attendance)
        return attendance


attendance_repository = AttendanceRepository()
