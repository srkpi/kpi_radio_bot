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

        today = datetime.now()
        if order.ether.date == today.date() and order.ether.end_time > today.time() > order.ether.start_time:
            current = await uow.orders.find_one(Order.ether_id == order.ether_id, Order.played == False, Order.confirmed == True)
            if current:
                ether_orders = await uow.orders.find(
                    Order.id < current.id,
                    Order.ether_id == order.ether_id,
                    Order.played == False,
                )

                total_duration = sum(o.duration for o in ether_orders)

                play_delay = 5 * len(ether_orders)
                play_time = datetime.now() + timedelta(seconds=total_duration + play_delay)
                play_time_str = play_time.strftime("%H:%M")

                await callback.bot.send_message(
                    callback_data.user_id,
                    f"✅ Твоє замовлення прийнято: {order.title}\n"
                    f"🕓 Орієнтовно програє: {play_time_str}",
                )
            else:
                await callback.bot.send_message(
                    callback_data.user_id,
                    f"✅ Твоє замовлення прийнято: {order.title}\n"
                    f"🕓 Орієнтовно програє: зараз",
                )
                player.play(order.url)
        else:
            ether_orders = await uow.orders.find(
                Order.ether_id == order.ether_id,
                Order.played == False
            )

            total_duration = sum(
                o.duration for o in ether_orders if o.id != order.id
            )

            play_delay = 5 * len(ether_orders)
            play_time = datetime.combine(
                order.ether.date, order.ether.start_time
            ) + timedelta(seconds=total_duration + play_delay)
            play_time_str = play_time.strftime("%H:%M")

            await callback.bot.send_message(
                callback_data.user_id,
                f"✅ Твоє замовлення прийнято: {order.title}\n"
                f"🕓 Орієнтовно програє: {play_time_str}",
            )

    await uow.flush()

    if callback.message.caption:
        await callback.message.edit_caption(caption=text)
    else:
        await callback.message.edit_text(text)


async def decline_order(callback: CallbackQuery, callback_data: ConfirmOrder, uow: UnitOfWork):
    order = await uow.orders.find_one(Order.id == callback_data.order_id)
    if order is None:
        text = callback.message.html_text + "\nОрдер не знайдено"
    else:
        text = callback.message.html_text + f"\n❌ Відхилено ({callback.from_user.mention_html()})"
        order.confirmed = False

        await callback.bot.send_message(
            callback_data.user_id, f"❌ Твоє замовлення відхилено: {order.title}"
        )

    await uow.flush()

    if callback.message.caption:
        await callback.message.edit_caption(caption=text)
    else:
        await callback.message.edit_text(text)
