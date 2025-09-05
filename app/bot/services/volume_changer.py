from datetime import datetime, time
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork


class VolumeChanger:
    volume_points: Dict[time, int] = {}

    @classmethod
    async def load_volume_points(cls, uow: UnitOfWork) -> None:
        points = await uow.volume_change_points.find()
        cls.volume_points = {point.time: point.volume for point in points}
        cls.check_and_set_volume()

    @classmethod
    async def load_volume_points_by_session(
        cls, async_session: async_sessionmaker[AsyncSession]
    ) -> None:
        async with async_session() as session, session.begin():
            async with UnitOfWork(session) as uow:
                await cls.load_volume_points(uow)

    @classmethod
    def check_and_set_volume(cls) -> None:
        now = datetime.now().time().replace(second=0, microsecond=0)

        volume_point = cls.volume_points.get(now)
        if volume_point is not None:
            player.set_volume(volume_point)

    @classmethod
    def check_and_set_nearest_volume(cls) -> None:
        now = datetime.now().time().replace(second=0, microsecond=0)
        sorted_points = sorted(cls.volume_points.keys())

        nearest_point: Optional[time] = None

        for point in sorted_points:
            if point <= now:
                nearest_point = point
            else:
                break

        if nearest_point is not None:
            volume = cls.volume_points[nearest_point]
            player.set_volume(volume)

        elif sorted_points:
            nearest_point = sorted_points[-1]
            volume = cls.volume_points[nearest_point]
            player.set_volume(volume)
