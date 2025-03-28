from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.bot.consts.ethers import SCHEDULE
from app.bot.player.mpv_player import player, get_current_track


day_mapping = {
    "0": "mon",
    "1": "tue",
    "2": "wed",
    "3": "thu",
    "4": "fri",
    "5": "sat",
    "6": "sun",
}


class Scheduler:
    def __init__(self, bot: Bot, async_session: async_sessionmaker[AsyncSession]):
        self._bot = bot
        self._async_sessionmaker = async_session
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        for day, ethers in SCHEDULE.items():
            day_of_week = day_mapping.get(day)
            if not day_of_week:
                continue

            for ether in ethers:
                start_hour, start_minute = map(int, ether["start"].split(":"))

                self._scheduler.add_job(
                    self.start_ether,
                    "cron",
                    day_of_week=day_of_week,
                    hour=start_hour,
                    minute=start_minute,
                    args=(self._async_sessionmaker,),
                )

        self._scheduler.add_job(self.minute, "cron", hour=9)
        self._scheduler.start()
        self.start_ether()

    @staticmethod
    async def minute():
        player.play("music/minute.mp3")

    @staticmethod
    async def start_ether(async_session: async_sessionmaker[AsyncSession]):
        track = await get_current_track(async_session)
        if track:
            player.play(track)
