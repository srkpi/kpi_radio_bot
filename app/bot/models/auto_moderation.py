from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from app.bot.models.base import Base


class AutoModeration(Base):
    __tablename__ = "auto_moderation"

    video_id: Mapped[str]
    confirm: Mapped[Optional[bool]]
    set_by: Mapped[int]
    timestamp: Mapped[datetime]
    is_deleted: Mapped[bool] = mapped_column(default=False)
