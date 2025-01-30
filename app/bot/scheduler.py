from datetime import time

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.bot.consts.ethers import WEEKDAY_ETHERS, WEEKEND_ETHERS
from app.bot.player.mpv_player import player, get_current_track


class Scheduler:
    def __init__(self, bot: Bot, async_session: async_sessionmaker[AsyncSession]):
        self._bot = bot
        self._async_sessionmaker = async_session
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        for ether in WEEKDAY_ETHERS:
            self._scheduler.add_job(
                self.start_ether,
                "cron",
                day_of_week="mon-sat",
                hour=ether["start"].hour,
                minute=ether["start"].minute,
                args=(self._bot, self._async_sessionmaker, ether["start"]),
            )
            self._scheduler.add_job(
                self.start_ether,
                "cron",
                day_of_week="sun",
                hour=ether["end"].hour,
                minute=ether["end"].minute,
                args=(self._bot, self._async_sessionmaker, ether["end"]),
            )

        for ether in WEEKEND_ETHERS:
            self._scheduler.add_job(
                self.start_ether,
                "cron",
                day_of_week="sat-sat",
                hour=ether["start"].hour,
                minute=ether["start"].minute,
                args=(self._bot, self._async_sessionmaker, ether["start"]),
            )
            self._scheduler.add_job(
                self.start_ether,
                "cron",
                day_of_week="sun",
                hour=ether["end"].hour,
                minute=ether["end"].minute,
                args=(self._bot, self._async_sessionmaker, ether["end"]),
            )

        self._scheduler.add_job(self.minute, "cron", hour=9)
        self._scheduler.start()

    @staticmethod
    async def minute():
        player.play('music/minute.mp3')

    @staticmethod
    async def start_ether(bot: Bot, async_session: async_sessionmaker[AsyncSession], start_time: time):
        track = await get_current_track(async_session)
        if track:
            player.play(track)

    @staticmethod
    async def end_ether(bot: Bot, async_session: async_sessionmaker[AsyncSession], end_time: time):
        ...
