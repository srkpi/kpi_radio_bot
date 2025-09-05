from types import TracebackType
from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models import Base
from app.bot.repositories.auto_moderation import AutoModerationRepository
from app.bot.repositories.banned_user import BannedUserRepository
from app.bot.repositories.day_state import DayStateRepository
from app.bot.repositories.ether import EtherRepository
from app.bot.repositories.order import OrderRepository
from app.bot.repositories.volume_change_point import VolumeChangePointRepository


class UnitOfWork:
    _session: AsyncSession

    ethers: EtherRepository
    orders: OrderRepository
    day_state: DayStateRepository
    banned_users: BannedUserRepository
    auto_moderation: AutoModerationRepository
    volume_change_points: VolumeChangePointRepository

    def __init__(self, session: AsyncSession):
        self._session = session
        self.ethers = EtherRepository(self._session)
        self.orders = OrderRepository(self._session)
        self.day_state = DayStateRepository(self._session)
        self.banned_users = BannedUserRepository(self._session)
        self.auto_moderation = AutoModerationRepository(self._session)
        self.volume_change_points = VolumeChangePointRepository(self._session)

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        await self.commit()

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, instance) -> None:
        await self._session.refresh(instance)

    async def flush(self) -> None:
        await self._session.flush()

    async def delete(self, model: Base) -> None:
        await self._session.delete(model)

    async def rollback(self) -> None:
        await self._session.rollback()
