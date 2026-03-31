from typing import TYPE_CHECKING, Optional
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.bot.models.base import Base

if TYPE_CHECKING:
    from app.bot.models.ether import Ether


class Order(Base):
    __tablename__ = "orders"

    title: Mapped[Optional[str]]

    video_id: Mapped[Optional[str]] = mapped_column(index=True)
    file_id: Mapped[Optional[str]]
    duration: Mapped[int]

    confirmed: Mapped[bool] = mapped_column(default=False)
    decided_by: Mapped[Optional[int]]
    decision_timestamp: Mapped[Optional[datetime]]

    played: Mapped[bool] = mapped_column(default=False)
    play_start: Mapped[Optional[datetime]]
    expected_play_time: Mapped[Optional[datetime]]

    ordered_by: Mapped[int]
    order_message_id: Mapped[Optional[int]] = mapped_column(unique=True, index=True)

    ether_id: Mapped[int] = mapped_column(ForeignKey("ethers.id"), index=True)
    ether: Mapped["Ether"] = relationship(back_populates="orders")
