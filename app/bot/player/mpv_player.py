import asyncio
import threading
from datetime import datetime
from time import sleep

import mpv
from aiogram import Bot

from app.bot.models import Ether, Order
from app.bot.repositories.uow import UnitOfWork
from app.database import sessionmaker
from app.settings import settings


def mpv_log(loglevel, component, message):
    print("[{}] ({}) {}".format(loglevel, component, message))

class MPVPlayer(mpv.MPV):
    def slow_volume(self):
        for i in range(0, 100, 10):
            self.volume = i
            sleep(0.5)

    def play(self, filename):
        threading.Thread(target=self.slow_volume, args=(self,))
        super().play(filename)

player = MPVPlayer(ytdl=True, log_handler=mpv_log, input_default_bindings=True, input_vo_keyboard=True)
player['vo'] = 'gpu'
player['ao'] = 'alsa'


async def get_music(file_id: str):
    bot = Bot(token=settings.TOKEN.get_secret_value())
    try:
        file = await bot.get_file(file_id)
        file_path = file.file_path
        result = await bot.download_file(file_path)
    except Exception as err:
        print(err)
        raise ValueError()
    print(result)
    return result


async def get_current_track(async_session):
    today = datetime.now()
    async with async_session() as session, session.begin():
        async with UnitOfWork(session) as uow:
            ether = await uow.ethers.find_one(Ether.date == today.date(), Ether.start_time <= today.time(),
                                              Ether.end_time >= today.time())
            print("ETHER:", ether)
            if not ether:
                return

            order = await uow.orders.find_one(Order.ether_id == ether.id, Order.played == False,
                                              Order.confirmed == True)
            if not order:
                return
            if order.file_id:
                return f"telegram://{order.file_id}"
            else:
                return f"{order.url}"


async def set_latest_track_played(async_session):
    today = datetime.now()
    async with async_session() as session, session.begin():
        async with UnitOfWork(session) as uow:
            ether = await uow.ethers.find_one(Ether.date == today.date(), Ether.start_time <= today.time(),
                                              Ether.end_time >= today.time())
            if not ether:
                return
            order = await uow.orders.find_one(Order.ether_id == ether.id, Order.played == False,
                                              Order.confirmed == True)
            if not order:
                return
            order.played = True


@player.event_callback("end-file")
def on_end_file(event):
    print(event)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(set_latest_track_played(sessionmaker))
    track = loop.run_until_complete(get_current_track(sessionmaker))
    if track:
        player.play(track)


class ReturnableThread(threading.Thread):
    def __init__(self, uri):
        threading.Thread.__init__(self)
        self.uri = uri
        self.result = None

    def run(self) -> None:
        self.result = asyncio.run(get_music(self.uri))


@player.register_stream_protocol('telegram')
def open_fn(uri):
    print(uri)
    _thread = ReturnableThread(uri.strip('telegram://'))
    _thread.start()
    _thread.join()
    return _thread.result
