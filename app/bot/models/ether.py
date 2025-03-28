from datetime import date, time
from typing import List, TYPE_CHECKING

from sqlalchemy.orm import Mapped, relationship, mapped_column

from app.bot.models.base import Base

if TYPE_CHECKING:
    from app.bot.models.order import Order


class Ether(Base):
    __tablename__ = "ethers"

    name: Mapped[str]
    start_time: Mapped[time]
    end_time: Mapped[time]
    ether_date: Mapped[date] = mapped_column(index=True)
    cancelled: Mapped[bool]

    orders: Mapped[List["Order"]] = relationship(back_populates="ether")
