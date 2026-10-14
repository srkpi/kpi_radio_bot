import asyncio
import html
import logging
from datetime import datetime
from typing import Iterable, Optional

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.consts.other import ALARM_MAX_DELAY, LONG_ETHER_MIN_DURATION
from app.bot.models import Ether, Order
from app.bot.repositories.uow import UnitOfWork
from app.bot.services.notifications import (
    NOTIFY_DELAY_SECONDS,
    notify_orders_cancelled_background,
)

logger = logging.getLogger(__name__)

OVERDUE_REASON = (
    f"програвання затрималось більше ніж на "
    f"{int(ALARM_MAX_DELAY.total_seconds() // 60)} хв"
)
ETHER_ENDED_REASON = "етер закінчився, а замовлення не встигло програти"


def is_long_ether(ether: Ether) -> bool:
    start = datetime.combine(ether.ether_date, ether.start_time)
    end = datetime.combine(ether.ether_date, ether.end_time)

    return end - start >= LONG_ETHER_MIN_DURATION


def get_order_deadline(order: Order) -> Optional[datetime]:
    """Latest moment the order may start playing (None if it has no expected time)."""
    if order.expected_play_time is None:
        return None

    return order.expected_play_time + ALARM_MAX_DELAY


def is_order_overdue(order: Order, now: datetime) -> bool:
    deadline = get_order_deadline(order)

    return deadline is not None and now > deadline


async def notify_orders_delayed(
    bot: Bot, orders: Iterable[Order], ether: Ether
) -> None:
    ether_end = datetime.combine(ether.ether_date, ether.end_time)

    for order in orders:
        if not order.ordered_by:
            continue

        text = "⏸ Замовлення відкладено через повітряну тривогу"
        if order.title:
            text += f": {html.escape(order.title)}"

        text += "\nВоно програє після відбою тривоги."

        deadline = get_order_deadline(order)
        cancel_after = min(deadline, ether_end) if deadline else ether_end
        text += (
            f"\nЯкщо тривога триватиме довше ніж до "
            f"{cancel_after.strftime('%H:%M')}, замовлення буде скасоване."
        )

        try:
            await bot.send_message(order.ordered_by, text)
        except Exception as e:
            print(f"Error sending delay notification to {order.ordered_by}: {e}")

        await asyncio.sleep(NOTIFY_DELAY_SECONDS)


async def cancel_stale_orders(
    uow: UnitOfWork, now: datetime
) -> tuple[list[Order], list[Order]]:
    """
    Cancel queued (not started yet) orders of today's ethers that can't be played.

    An order is stale when it would start more than ALARM_MAX_DELAY after its
    expected play time, or when its ether is already over.

    Returns (overdue, ether_ended) lists of the cancelled orders.
    """
    ethers = await uow.ethers.find(
        Ether.ether_date == now.date(),
        Ether.cancelled == False,
    )
    if not ethers:
        return [], []

    ethers_by_id = {ether.id: ether for ether in ethers}
    orders = await uow.orders.find(
        Order.ether_id.in_(list(ethers_by_id)),
        Order.played == False,
        Order.confirmed == True,
        Order.play_start == None,
        order=[Order.decision_timestamp.asc()],
    )

    overdue: list[Order] = []
    ether_ended: list[Order] = []

    for order in orders:
        if is_order_overdue(order, now):
            overdue.append(order)
        elif now.time() > ethers_by_id[order.ether_id].end_time:
            ether_ended.append(order)
        else:
            continue

        order.played = True

    if overdue or ether_ended:
        await uow.flush()

    return overdue, ether_ended


async def cleanup_stale_orders(
    async_session: async_sessionmaker[AsyncSession],
) -> None:
    """Cancel stale queued orders and tell their authors. Never raises."""
    try:
        async with async_session() as session, session.begin():
            async with UnitOfWork(session) as uow:
                overdue, ether_ended = await cancel_stale_orders(uow, datetime.now())
    except Exception as e:
        logger.exception(e)
        return

    notify_orders_cancelled_background(overdue, OVERDUE_REASON)
    notify_orders_cancelled_background(ether_ended, ETHER_ENDED_REASON)
