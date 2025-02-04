from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models import BannedUser
from app.bot.repositories.base import BaseRepository


class BannedUserRepository(BaseRepository[BannedUser]):
    def __init__(self, session: AsyncSession):
        super().__init__(BannedUser, session)
