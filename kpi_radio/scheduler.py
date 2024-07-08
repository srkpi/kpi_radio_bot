import logging
from pathlib import Path

from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class Scheduler:
    def __init__(self):
        self._scheduler = AsyncIOScheduler()

    @staticmethod
    def error_handling(event) -> None:  # type: ignore
        if event.exception:
            logging.exception(event.exception)

    def start(self) -> None:
        self._scheduler.add_listener(self.error_handling, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self._scheduler.add_job(self.schedule, 'cron', hour="9")
        self._scheduler.start()

    @staticmethod
    async def schedule() -> None:
        from kpi_radio.player import Broadcast, PlaylistItem

        Broadcast.player.add_track(PlaylistItem.from_path(Path('minute.mp3')), at_position=0)

