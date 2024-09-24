from types import TracebackType
from typing import Self, Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models import Base
from app.bot.repositories.ether import EtherRepository
from app.bot.repositories.order import OrderRepository


class UnitOfWork:
    _session: AsyncSession

    ethers: EtherRepository
    orders: OrderRepository

    def __init__(self, session: AsyncSession):
        self._session = session
        self.ethers = EtherRepository(self._session)
        self.orders = OrderRepository(self._session)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: Type[BaseException], exc_val: BaseException, exc_tb: TracebackType) -> None:
        await self.commit()

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, instance):
        await self._session.refresh(instance)

    async def flush(self) -> None:
        await self._session.flush()

    async def delete(self, model: Base) -> None:
        await self._session.delete(model)

    async def rollback(self) -> None:
        await self._session.rollback()