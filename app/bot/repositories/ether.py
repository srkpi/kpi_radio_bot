from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models import Ether
from app.bot.repositories.base import BaseRepository


class EtherRepository(BaseRepository[Ether]):
    def __init__(self, session: AsyncSession):
        super().__init__(Ether, session)
