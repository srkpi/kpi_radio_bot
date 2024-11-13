from datetime import datetime

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
        text = callback.message.html_text + f"\n✅Прийнято ({callback.from_user.mention_html()})"
        order.confirmed = True

        await callback.bot.send_message(
            callback_data.user_id, f"Ваше замовлення прийнято: {order.title}"
        )
    today = datetime.now()
    if order.ether.date == today.date() and order.ether.end_time > today.time() > order.ether.start_time:
        current = await uow.orders.find_one(Order.ether_id == order.ether_id, Order.played == False, Order.confirmed == True)
        if not current:
            player.play(order.url)
    if callback.message.caption:
        await callback.message.edit_caption(caption=text)
    else:
        await callback.message.edit_text(text)


async def decline_order(callback: CallbackQuery, callback_data: ConfirmOrder, uow: UnitOfWork):
    order = await uow.orders.find_one(Order.id == callback_data.order_id)
    if order is None:
        text = callback.message.html_text + "\nОрдер не знайдено"
    else:
        text = callback.message.html_text + f"\n❌Відхилено ({callback.from_user.mention_html()})"
        order.confirmed = False

        await callback.bot.send_message(
            callback_data.user_id, f"Ваше замовлення відхилено: {order.title}"
        )

    if callback.message.caption:
        await callback.message.edit_caption(caption=text)
    else:
        await callback.message.edit_text(text)
