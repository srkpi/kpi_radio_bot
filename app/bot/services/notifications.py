import asyncio
from typing import Iterable, Optional

from aiogram import Bot

from app.bot.models.order import Order

NOTIFY_DELAY_SECONDS = 0.1


async def notify_orders_cancelled(
    bot: Bot,
    orders: Iterable[Order],
    reason: Optional[str] = None,
) -> None:
    reason_line = f"\nПричина: {reason}" if reason else ""

    for order in orders:
        if not order.ordered_by:
            continue

        if order.confirmed == False and order.decision_timestamp:
            continue  # Already cancelled manually

        text = "🚫 Замовлення скасоване"
        if order.title:
            text += f": {order.title}"

        text += reason_line

        try:
            await bot.send_message(order.ordered_by, text)
        except Exception as e:
            print(f"Eror sending cancel notification to {order.ordered_by}: {e}")

        await asyncio.sleep(NOTIFY_DELAY_SECONDS)
