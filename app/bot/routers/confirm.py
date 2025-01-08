import re

from datetime import datetime, timedelta

from aiogram.types import CallbackQuery
from sqlalchemy.orm import selectinload

from app.bot.models import Order
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork
from app.bot.schemas.confirm import ConfirmOrder


async def confirm_order(callback: CallbackQuery, callback_data: ConfirmOrder, uow: UnitOfWork):
    order = await uow.orders.find_one(Order.id == callback_data.order_id, options=[selectinload(Order.ether)])
    if order is None:
        text = callback.message.html_text + "\nОрдер не знайдено"
    else:
        text = callback.message.html_text + f"\n✅ Прийнято ({callback.from_user.mention_html()})"
        order.confirmed = True

        current_datetime = datetime.now()
        order.decision_timestamp = current_datetime

        if (
            order.ether.date == current_datetime.date()
            and current_datetime.time() > order.ether.start_time
        ):
            current_playing: Order = await uow.orders.find_one(
                Order.ether_id == order.ether_id,
                Order.played == False,
                Order.confirmed == True,
                order=[Order.decision_timestamp.asc()],
            )

            if current_playing:
                ether_not_played_orders: list[Order] = await uow.orders.find(
                    Order.ether_id == order.ether_id,
                    Order.played == False,
                    Order.confirmed == True,
                )
                ether_not_played_orders_len = len(ether_not_played_orders)

                total_duration = sum(o.duration for o in ether_not_played_orders)
                current_play_start = current_playing.play_start

                if current_play_start:
                    total_duration -= max(
                        round((current_datetime - current_play_start).total_seconds()),
                        0,
                    )

                play_delay = 30 * (ether_not_played_orders_len - 1)
                play_time = datetime.now() + timedelta(seconds=total_duration + play_delay)
                play_time_str = play_time.strftime("%H:%M")
                order.expected_play_time = play_time

                await callback.bot.send_message(
                    callback_data.user_id,
                    f"✅ Твоє замовлення прийнято: {order.title}\n"
                    f"🕓 Орієнтовно програє: {play_time_str}",
                )
            else:
                play_time = datetime.now()
                order.expected_play_time = datetime.now()
                play_time_str = play_time.strftime("%H:%M")

                await callback.bot.send_message(
                    callback_data.user_id,
                    f"✅ Твоє замовлення прийнято: {order.title}\n"
                    f"🕓 Орієнтовно програє: зараз",
                )
                player.play(order.url)
        else:
            ether_orders = await uow.orders.find(
                Order.ether_id == order.ether_id,
                Order.played == False,
                Order.confirmed == True,
            )

            total_duration = sum(
                o.duration for o in ether_orders if o.id != order.id
            )

            play_delay = 30 * len(ether_orders)
            play_time = datetime.combine(
                order.ether.date, order.ether.start_time
            ) + timedelta(seconds=total_duration + play_delay)
            play_time_str = play_time.strftime("%H:%M")
            order.expected_play_time = play_time

            await callback.bot.send_message(
                callback_data.user_id,
                f"✅ Твоє замовлення прийнято: {order.title}\n"
                f"🕓 Орієнтовно програє: {play_time_str}",
            )

    await uow.flush()

    replaced_time_text = re.sub(r"(🕓)\s(\d{2}:\d{2})", f"\\1 {play_time_str}", text)

    if callback.message.caption:
        await callback.message.edit_caption(caption=replaced_time_text)
    else:
        await callback.message.edit_text(replaced_time_text)


async def decline_order(callback: CallbackQuery, callback_data: ConfirmOrder, uow: UnitOfWork):
    order = await uow.orders.find_one(Order.id == callback_data.order_id)
    if order is None:
        text = callback.message.html_text + "\nОрдер не знайдено"
    else:
        text = callback.message.html_text + f"\n❌ Відхилено ({callback.from_user.mention_html()})"
        order.confirmed = False
        order.decision_timestamp = datetime.now()

        await callback.bot.send_message(
            callback_data.user_id, f"❌ Твоє замовлення відхилено: {order.title}"
        )

    await uow.flush()

    if callback.message.caption:
        await callback.message.edit_caption(caption=text)
    else:
        await callback.message.edit_text(text)
