import asyncio
import threading
from datetime import datetime
from time import sleep

import mpv

from app.bot.models import Ether, Order
from app.bot.repositories.uow import UnitOfWork
from app.database import sessionmaker
from app.settings import settings


def mpv_log(loglevel, component, message):
    print("[{}] ({}) {}".format(loglevel, component, message))

class MPVPlayer(mpv.MPV):
    def slow_volume(self):
        for i in range(0, 110, 10):
            self.volume = i
            sleep(0.5)

    def play(self, filename):
        threading.Thread(target=self.slow_volume, args=(self,))
        super().play(filename)

player = MPVPlayer(ytdl=True, log_handler=mpv_log, input_default_bindings=True, input_vo_keyboard=True, video=False)
player['vo'] = 'null'

async def get_current_track(async_session):
    today = datetime.now()
    async with async_session() as session, session.begin():
        async with UnitOfWork(session) as uow:
            ether = await uow.ethers.find_one(Ether.date == today.date(), Ether.start_time <= today.time(),
                                              Ether.end_time >= today.time(), Ether.cancelled == False)
            print("ETHER:", ether)
            if not ether:
                return

            order = await uow.orders.find_one(Order.ether_id == ether.id, Order.played == False,
                                              Order.confirmed == True, order=[Order.decision_timestamp.asc()])
            if not order:
                return

            order.play_start = datetime.now()

            return f"{order.url}"


async def set_latest_track_played(async_session):
    async with async_session() as session, session.begin():
        async with UnitOfWork(session) as uow:
            order = await uow.orders.find_one(Order.played == False, Order.confirmed == True, order=[Order.play_start.desc()])
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
