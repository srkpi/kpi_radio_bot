import asyncio
import mpv
import threading

from aiogram import Bot
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from typing import Optional

from app.bot.models import Ether, Order
from app.bot.repositories.uow import UnitOfWork
from app.bot.services.song_downloader import delete_song, get_song_path, is_downloading
from app.bot.states.alert_state import get_alert_state
from app.database import sessionmaker
from app.settings import settings

ytdl_opts = "" # "extractor-args=youtube:player_client=android"

#if settings.COOKIES_PATH:
#    ytdl_opts += f"cookies={settings.COOKIES_PATH}"


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

    def play(self, filename):
        super().play(filename)

    def stop_current(self):
        self.command("playlist-remove", 0)


class DoubleMPVPlayer:
    def __init__(self, physical_player: MPVPlayer, streaming_player: MPVPlayer):
        self.last_play = datetime.now()
        self.is_playing = False
        self.physical_player = physical_player
        self.streaming_player = streaming_player

        self.constant_volume = 100
        self.volume = 100

    def play(self, filename):
        self.is_playing = True
        self.last_play = datetime.now()

        physical_player.volume = self.constant_volume
        streaming_player.volume = self.constant_volume

        self.physical_player.play(filename)
        self.streaming_player.play(filename)

    def stop(self):
        self.is_playing = False
        self.physical_player.stop()
        self.streaming_player.stop()

    def stop_current(self):
        self.is_playing = False
        self.physical_player.stop_current()
        self.streaming_player.stop_current()

    def set_volume(self, volume: int):
        assert 0 <= volume <= 100
        self.volume = volume
        self.constant_volume = volume
        physical_player.volume = volume
        streaming_player.volume = volume

    def set_temp_volume(self, volume: int):
        assert 0 <= volume <= 100
        physical_player.volume = volume
        streaming_player.volume = volume


async def mpv_log_error(component: str, message: str) -> None:
    bot = Bot(token=settings.TOKEN.get_secret_value())
    try:
        await bot.send_message(
            chat_id=settings.ADMINS_CHAT_ID,
            message_thread_id=settings.ADMINS_BUGS_THREAD_ID,
            text=f"🚨 <b>Player Error</b> 🚨\n\n<code>({component}) {message}</code>",
            parse_mode="HTML",
        )
    finally:
        await bot.session.close()


def mpv_log(loglevel: str, component: str, message: str) -> None:
    print("[{}] ({}) {}".format(loglevel, component, message))

    if loglevel == "error" and component != "ffmpeg":

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(mpv_log_error(component, message))
            loop.close()

        threading.Thread(target=run).start()


physical_player = MPVPlayer(
    ytdl=True,
    audio_device="alsa/hw:3,0",
    log_handler=mpv_log,
    input_default_bindings=True,
    video=False,
    cache=False,
    audio_channels="stereo",
    ytdl_raw_options=ytdl_opts,
)

streaming_player = MPVPlayer(
    ytdl=True,
    audio_device="alsa/plughw:CARD=Loopback,DEV=0",
    log_handler=mpv_log,
    input_default_bindings=True,
    video=False,
    cache=False,
    audio_channels="stereo",
    ytdl_raw_options=ytdl_opts,
)

player = DoubleMPVPlayer(physical_player, streaming_player)

announcement_file_path = "music/announcement.mp3"
_last_announcement_played: set[tuple[date, int]] = set()


def _is_announcement_time(
    now: datetime, margin: timedelta = timedelta(minutes=5)
) -> bool:
    # Announcements are currently disabled
    return False

    hour = now.hour

    if not (9 <= hour <= 21):
        return False

    target = now.replace(minute=30, second=0, microsecond=0)

    if target - margin <= now <= target + margin:
        return True

    return False


async def get_current_track(
    async_session: async_sessionmaker[AsyncSession],
) -> Optional[str]:
    if await get_alert_state():
        return

    now = datetime.now()
    today = now.date()

    if _is_announcement_time(now):
        key = (today, now.hour)

        if key not in _last_announcement_played:
            _last_announcement_played.add(key)

            return announcement_file_path

    async with async_session() as session, session.begin():
        async with UnitOfWork(session) as uow:
            ether = await uow.ethers.find_one(
                Ether.ether_date == now.date(),
                Ether.start_time <= now.time(),
                Ether.end_time >= now.time(),
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

            await uow.flush()

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
                Order.play_start != None,
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


@physical_player.event_callback("end-file")
def on_end_file(event):
    print("Physical player:", event)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(set_latest_track_played(sessionmaker))

    if event.data.reason == 2:  # If stopped
        if datetime.now() > player.last_play + timedelta(seconds=10):
            player.is_playing = False

        return

    player.is_playing = False

    track = loop.run_until_complete(get_current_track(sessionmaker))
    if track:
        player.play(track)


@streaming_player.event_callback("end-file")
def on_end_file_streaming(event):
    print("Streaming player:", event)
