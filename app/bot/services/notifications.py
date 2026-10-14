import asyncio
import threading
from typing import Iterable, Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.models.order import Order
from app.settings import settings

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


def notify_orders_cancelled_background(
    orders: Iterable[Order],
    reason: Optional[str] = None,
) -> None:
    """
    Fire-and-forget variant of notify_orders_cancelled.

    For code that has neither a Bot nor a free event loop (mpv callbacks, the
    player picking the next track): messages are sent from a separate thread so
    playback is not held up by Telegram.
    """
    orders = list(orders)
    if not orders:
        return

    async def send() -> None:
        bot = Bot(
            token=settings.TOKEN.get_secret_value(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        try:
            await notify_orders_cancelled(bot, orders, reason)
        finally:
            await bot.session.close()

    threading.Thread(target=lambda: asyncio.run(send()), daemon=True).start()
