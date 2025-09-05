from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.models.volume_change_point import VolumeChangePoint
from app.bot.repositories.base import BaseRepository


class VolumeChangePointRepository(BaseRepository[VolumeChangePoint]):
    def __init__(self, session: AsyncSession):
        super().__init__(VolumeChangePoint, session)
