from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models import Order
from app.bot.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)
