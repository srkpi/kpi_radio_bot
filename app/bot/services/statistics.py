import asyncio
import json
import tempfile
import requests

from datetime import date, datetime, time
from pathlib import Path
from enum import Enum
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from typing import Any, Optional, TypeAlias, Union
from time import perf_counter
from urllib.parse import urljoin

from app.bot.consts.ethers import SCHEDULE
from app.bot.models.banned_user import BannedUser
from app.bot.repositories.uow import UnitOfWork
from app.settings import settings

STATS_FILE = Path("statistics.json")

bot_launch_time = datetime.now()
_update_statistics_lock = asyncio.Lock()


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return int(obj.timestamp())

        if isinstance(obj, date):
            return int(obj.toordinal())

        if isinstance(obj, time):
            return obj.hour * 3600 + obj.minute * 60 + obj.second

        if isinstance(obj, Enum):
            return obj.value

        return super().default(obj)


class OrderStates(Enum):
    PLAYED = 1
    QUEUED = 2
    UNDECIDED = 3
    REJECTED = 4
    SKIPPED = 5
    ERROR = 6


class DayStates(Enum):
    CLOSED = 1
    HOLIDAY = 2


async def _fetch_banned_users(uow: UnitOfWork) -> list[datetime]:
    banned_users = await uow.banned_users.find(BannedUser.is_deleted == False)

    banned_timestamps = []
    for user in banned_users:
        banned_timestamps.append(user.timestamp)

    return banned_timestamps


async def _fetch_date_states(
    uow: UnitOfWork,
) -> list[tuple[DayStates, date, Optional[str]]]:
    day_states_formatted = []
    day_states = await uow.day_state.find()

    for day_state in day_states:
        if day_state.is_closed:
            state = DayStates.CLOSED
        elif day_state.is_holiday:
            state = DayStates.HOLIDAY
        else:
            continue

        day_states_formatted.append((state, day_state.state_date, day_state.reason))

    return day_states_formatted


OrderRow: TypeAlias = Union[
    list[int, int, OrderStates],
    list[int, int, OrderStates, Optional[datetime]],
    list[int, int, OrderStates, Optional[datetime], Optional[datetime]],
    list[
        int,
        int,
        OrderStates,
        Optional[datetime],
        Optional[datetime],
        Optional[datetime],
    ],
]


async def _fetch_songs_with_orders(
    uow: UnitOfWork,
) -> tuple[
    list[tuple[str, int, str]],
    list[OrderRow],
]:
    song_mapper: dict[str, int] = {}
    songs_formatted: list[tuple[str, int, str]] = []
    orders_formatted: list[OrderRow] = []

    orders = await uow.orders.find()

    for order in orders:
        video_id = order.video_id
        if video_id is None:
            continue

        order_state = OrderStates.ERROR

        if order.confirmed is None:
            order_state = OrderStates.UNDECIDED
        elif not order.confirmed:
            order_state = OrderStates.REJECTED
        elif order.played:
            if order.play_start:
                order_state = OrderStates.PLAYED
            else:
                order_state = OrderStates.SKIPPED
        elif order.expected_play_time:
            order_state = OrderStates.QUEUED

        song_id = song_mapper.get(video_id)
        if song_id is None:
            song_id = len(songs_formatted)
            song_mapper[video_id] = song_id
            songs_formatted.append((order.title, order.duration, video_id))
        else:
            songs_formatted[song_id] = (order.title, order.duration, video_id)

        song_data = [
            song_id,
            order.ether_id,
            order_state,
        ]

        if order.decision_timestamp:
            song_data.append(order.decision_timestamp)

            if order.expected_play_time:
                song_data.append(order.expected_play_time)

                if order.play_start:
                    song_data.append(order.play_start)

        orders_formatted.append(song_data)

    return songs_formatted, orders_formatted


async def _fetch_ethers(
    uow: UnitOfWork,
) -> list[dict[str, Union[list[time, time, date], list[time, time, date, 1]]]]:
    ethers_formatted = {}
    ethers = await uow.ethers.find()

    for ether in ethers:
        data = [
            ether.start_time,
            ether.end_time,
            ether.ether_date,
        ]

        if ether.cancelled:
            data.append(1)

        ethers_formatted[str(ether.id)] = data

    return ethers_formatted


async def _collect_statistics(uow: UnitOfWork) -> dict:
    start_time = perf_counter()

    banned_users = await _fetch_banned_users(uow)
    day_states = await _fetch_date_states(uow)
    songs, orders = await _fetch_songs_with_orders(uow)
    ethers = await _fetch_ethers(uow)

    end_time = perf_counter()
    duration = end_time - start_time

    return {
        "banned_users": banned_users,
        "day_states": day_states,
        "songs": songs,
        "orders": orders,
        "ethers": ethers,
        "schedule": SCHEDULE,
        "fetch_duration": round(duration, 3),
        "timestamp": datetime.now(),
        "bot_launch_time": bot_launch_time,
    }


def get_statistics() -> dict[str, Any]:
    if not STATS_FILE.exists():
        return {}

    with STATS_FILE.open() as f:
        return json.load(f)


async def save_statistics_to_file(data: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False, dir=".") as tmp:
        json.dump(data, tmp)
        tmp.flush()

    Path(tmp.name).replace(STATS_FILE)


async def update_statistics(async_session: async_sessionmaker[AsyncSession]) -> None:
    if _update_statistics_lock.locked():
        return

    print("Collecting statistics")
    async with _update_statistics_lock:
        try:
            async with async_session() as session, session.begin():
                async with UnitOfWork(session) as uow:
                    statistics = await _collect_statistics(uow)

            await save_statistics_to_file(statistics)
            print("Statistics collected")
            requests.request("GET", str(settings.STATISTICS_HEARTBEAT_URL))
        except Exception as e:
            print(e)
            requests.request(
                "GET", urljoin(str(settings.STATISTICS_HEARTBEAT_URL), "fail")
            )
