import asyncio
import os
import subprocess

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.bot.consts.ethers import SCHEDULE
from app.bot.player.mpv_player import player, announcement_file_path, get_current_track
from app.bot.repositories.uow import UnitOfWork
from app.bot.services.statistic import update_statistic
from app.bot.services.volume_changer import VolumeChanger
from app.settings import settings


day_mapping = {
    "0": "mon",
    "1": "tue",
    "2": "wed",
    "3": "thu",
    "4": "fri",
    "5": "sat",
    "6": "sun",
}

_play_current_lock = asyncio.Lock()


class Scheduler:
    def __init__(self, bot: Bot, async_session: async_sessionmaker[AsyncSession]):
        self._bot = bot
        self._async_sessionmaker = async_session
        self._scheduler = AsyncIOScheduler()

    async def start(self) -> None:
        for day, ethers in SCHEDULE.items():
            day_of_week = day_mapping.get(day)
            if not day_of_week:
                continue

            for ether in ethers:
                start_hour, start_minute = map(int, ether["start"].split(":"))

                self._scheduler.add_job(
                    self.play_current_song,
                    "cron",
                    day_of_week=day_of_week,
                    hour=start_hour,
                    minute=start_minute,
                    args=(self._async_sessionmaker,),
                )

        self._scheduler.add_job(self.minute, "cron", hour=9)
        self._scheduler.add_job(
            update_statistic,
            "interval",
            hours=3,
            args=(self._async_sessionmaker,),
        )
        self._scheduler.add_job(
            self.scheduled_restart,
            "cron",
            hour=22,
            minute=5,
            args=(self._async_sessionmaker, self._bot),
        )
        self._scheduler.add_job(
            VolumeChanger.check_and_set_volume,
            "cron",
            minute="*",
        )
        self._scheduler.add_job(
            self.auto_recovery,
            "interval",
            minutes=1,
            args=(self._async_sessionmaker, self._bot),
        )
        self._scheduler.start()

    @staticmethod
    def minute() -> None:
        player.play("music/minute.mp3")
        player.set_temp_volume(100)

    @staticmethod
    async def scheduled_restart(
        async_session: async_sessionmaker[AsyncSession], bot: Bot
    ) -> None:
        async with async_session() as session, session.begin():
            async with UnitOfWork(session) as uow:
                await uow.flush()

        script_path = os.path.abspath("./restart_bot.sh")
        subprocess.Popen(
            ["nohup", "bash", script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        await bot.send_message(
            settings.ADMINS_CHAT_ID,
            "🔄 Автоматичний перезапуск",
            message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
        )

    @staticmethod
    async def play_current_song(
        async_session: async_sessionmaker[AsyncSession],
    ) -> None:
        async with _play_current_lock:
            if not player.is_playing:
                track = await get_current_track(async_session)
                if track and not player.is_playing:
                    player.play(track)

                    return track != announcement_file_path

        return False

    @staticmethod
    async def auto_recovery(
        async_session: async_sessionmaker[AsyncSession], bot: Bot
    ) -> None:
        if await Scheduler.play_current_song(async_session):
            return

            #await bot.send_message(
            #    settings.ADMINS_CHAT_ID,
            #    "💥🔄✅ Автоматично відновлено програвання",
            #    message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
            #)
