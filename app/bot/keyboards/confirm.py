from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.consts.actions import Actions
from app.bot.schemas.confirm import ConfirmOrder


def get_confirm_keyboard(order_id: int, user_id: int):
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✅ Прийняти",
        callback_data=ConfirmOrder(
            action=Actions.confirm, order_id=order_id, user_id=user_id
        ),
    )
    builder.button(
        text="❌ Відхилити",
        callback_data=ConfirmOrder(
            action=Actions.decline, order_id=order_id, user_id=user_id
        ),
    )
    builder.adjust(2)

    return builder.as_markup()
