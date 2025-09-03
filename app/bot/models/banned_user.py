from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from app.bot.models.base import Base


class BannedUser(Base):
    __tablename__ = "banned_users"

    user_id: Mapped[int] = mapped_column(index=True)
    ban_message_id: Mapped[int]
    banned_by: Mapped[int]
    banned_feedback: Mapped[Optional[bool]] = mapped_column(default=False)
    timestamp: Mapped[datetime]
    reason: Mapped[Optional[str]]
    is_deleted: Mapped[bool] = mapped_column(default=False)
