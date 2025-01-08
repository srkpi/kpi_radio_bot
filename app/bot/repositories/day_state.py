from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models import DayState
from app.bot.repositories.base import BaseRepository


class DayStateRepository(BaseRepository[DayState]):
    def __init__(self, session: AsyncSession):
        super().__init__(DayState, session)
