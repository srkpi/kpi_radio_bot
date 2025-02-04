from datetime import date
from typing import Optional
from sqlalchemy.orm import Mapped
from app.bot.models.base import Base


class DayState(Base):
    __tablename__ = "day_states"

    state_date: Mapped[date]
    is_holiday: Mapped[Optional[bool]]
    is_closed: Mapped[Optional[bool]]
    reason: Mapped[Optional[str]]
