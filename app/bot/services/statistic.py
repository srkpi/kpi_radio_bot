import json
import requests

from datetime import date, datetime, time
from enum import Enum
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional
from time import perf_counter
from urllib.parse import urljoin

from app.bot.consts.ethers import SCHEDULE
from app.bot.models.banned_user import BannedUser
from app.bot.models.ether import Ether
from app.bot.repositories.uow import UnitOfWork
from app.settings import settings

bot_launch_time = datetime.now()


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
    ERROR = "e"
    UNDECIDED = "u"
    REJECTED = "r"
    SKIPPED = "s"
    PLAYED = "p"
    QUEUED = "q"


class DayStates(Enum):
    CLOSED = "c"
    HOLIDAY = "h"


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


async def _fetch_songs_with_orders(
    uow: UnitOfWork,
) -> tuple[
    dict[str, tuple[str, int]],
    list[
        tuple[
            str,
            int,
            OrderStates,
            Optional[datetime],
            Optional[datetime],
            Optional[datetime],
        ]
    ],
]:
    songs_formatted = {}
    orders_formatted = []
    orders = await uow.orders.find()

    for order in orders:
        if order.video_id is None:
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

        songs_formatted[order.video_id] = (order.title, order.duration)
        orders_formatted.append(
            (
                order.video_id,
                order.ether_id,
                order_state,
                order.decision_timestamp,
                order.expected_play_time,
                order.play_start,
            )
        )

    return songs_formatted, orders_formatted


async def _fetch_ethers(
    uow: UnitOfWork,
) -> list[dict[str, tuple[time, time, date, bool]]]:
    ethers_formatted = {}
    ethers = await uow.ethers.find(
        options=[selectinload(Ether.orders)],
    )

    for ether in ethers:
        ethers_formatted[str(ether.id)] = (
            ether.start_time,
            ether.end_time,
            ether.ether_date,
            ether.cancelled,
        )

    return ethers_formatted


async def _get_statistic(uow: UnitOfWork) -> dict:
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


def _upload_to_json_silo(data: object) -> None:
    url = f"https://api.jsonsilo.com/api/v1/manage/{settings.JSON_SILO_UUID.get_secret_value()}"
    headers = {
        "X-MAN-API": settings.JSON_SILO_KEY.get_secret_value(),
        "Content-Type": "application/json",
    }
    payload = {
        "filename": "radio_kpi",
        "file_data": data,
        "is_public": True,
    }
    payload_json = json.dumps(
        payload,
        cls=CustomEncoder,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    response = requests.request("PATCH", url, data=payload_json, headers=headers)
    response.raise_for_status()


async def update_statistic(async_session: async_sessionmaker[AsyncSession]) -> None:
    try:
        async with async_session() as session, session.begin():
            async with UnitOfWork(session) as uow:
                statistic = await _get_statistic(uow)

        _upload_to_json_silo(statistic)
        requests.request("GET", settings.STATISTIC_HEARTBEAT_URL)
    except Exception as e:
        print(e)
        requests.request("GET", urljoin(str(settings.STATISTIC_HEARTBEAT_URL), "fail"))
