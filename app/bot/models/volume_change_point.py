from datetime import time
from sqlalchemy.orm import Mapped
from app.bot.models.base import Base


class VolumeChangePoint(Base):
    __tablename__ = "volume_change_points"

    time: Mapped[time]
    volume: Mapped[int]
