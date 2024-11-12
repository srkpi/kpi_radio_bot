from aiogram.filters.callback_data import CallbackData

from app.bot.consts.actions import Actions


class ConfirmOrder(CallbackData, prefix="c_order"):
    action: Actions
    order_id: int
    user_id: int
