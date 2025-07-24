from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models import AutoModeration
from app.bot.repositories.base import BaseRepository


class AutoModerationRepository(BaseRepository[AutoModeration]):
    def __init__(self, session: AsyncSession):
        super().__init__(AutoModeration, session)
