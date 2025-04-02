import mpv
import asyncio
from datetime import datetime, timedelta

from app.bot.models import Ether, Order
from app.bot.repositories.uow import UnitOfWork
from app.bot.services.song_downloader import delete_song, get_song_path, is_downloading
from app.database import sessionmaker


def mpv_log(loglevel, component, message):
    print("[{}] ({}) {}".format(loglevel, component, message))


class MPVPlayer(mpv.MPV):
    def __init__(
        self,
        *extra_mpv_flags,
        log_handler=None,
        start_event_thread=True,
        loglevel=None,
        **extra_mpv_opts,
    ):
        super().__init__(
            *extra_mpv_flags,
            log_handler=log_handler,
            start_event_thread=start_event_thread,
            loglevel=loglevel,
            **extra_mpv_opts,
        )
        self.constant_volume = 100
        self.volume = 100

    def set_volume(self, volume: int):
        assert 0 <= volume <= 100
        self.volume = volume
        self.constant_volume = volume

    def set_temp_volume(self, volume: int):
        assert 0 <= volume <= 100
        self.volume = volume

    def play(self, filename):
        self.volume = self.constant_volume
        super().play(filename)


player = MPVPlayer(
    ytdl=True,
    log_handler=mpv_log,
    input_default_bindings=True,
    video=False,
    cache=False,
)


async def get_current_track(async_session):
    today = datetime.now()
    async with async_session() as session, session.begin():
        async with UnitOfWork(session) as uow:
            ether = await uow.ethers.find_one(
                Ether.ether_date == today.date(),
                Ether.start_time <= today.time(),
                Ether.end_time >= today.time(),
                Ether.cancelled == False,
            )

            if not ether:
                return

            order = await uow.orders.find_one(
                Order.ether_id == ether.id,
                Order.played == False,
                Order.confirmed == True,
                order=[Order.decision_timestamp.asc()],
            )

            if not order:
                return

            order.play_start = datetime.now()
            video_id = order.video_id

            song_path = get_song_path(video_id)
            if song_path:
                return str(song_path)

            return f"https://youtube.com/watch?v={video_id}"


async def set_latest_track_played(async_session):
    async with async_session() as session, session.begin():
        async with UnitOfWork(session) as uow:
            order = await uow.orders.find_one(
                Order.played == False,
                Order.confirmed == True,
                order=[Order.play_start.desc()],
            )
            if not order:
                return

            order.played = True
            video_id = order.video_id

            is_same_song_orders_exists = await uow.orders.check_exists(
                Order.video_id == video_id,
                Order.played == False,
                Order.confirmed == True,
                Order.expected_play_time
                >= order.expected_play_time - timedelta(hours=1),
            )

            if not is_same_song_orders_exists and not is_downloading(video_id):
                delete_song(video_id)


@player.event_callback("end-file")
def on_end_file(event):
    print(event)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(set_latest_track_played(sessionmaker))
    track = loop.run_until_complete(get_current_track(sessionmaker))
    if track:
        player.play(track)
