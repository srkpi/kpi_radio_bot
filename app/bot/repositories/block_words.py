from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models import BlockPhrase
from app.bot.repositories.base import BaseRepository


class BlockPhraseRepository(BaseRepository[BlockPhrase]):
    def __init__(self, session: AsyncSession):
        super().__init__(BlockPhrase, session)
