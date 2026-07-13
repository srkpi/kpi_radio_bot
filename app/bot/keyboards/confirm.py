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


def get_moderation_keyboard(order_id: int, user_id: int):
    """3-button keyboard (no text, emoji only) shown for songs that are
    not yet present in any auto-moderation list (whitelist/blacklist/manual).

    🟢 - approve the order and whitelist the video
    🟡 - move the video to the manual list and switch to the confirm/decline keyboard
    🔴 - reject the order and blacklist the video
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🟢",
        callback_data=ConfirmOrder(
            action=Actions.whitelist, order_id=order_id, user_id=user_id
        ),
    )
    builder.button(
        text="🟡",
        callback_data=ConfirmOrder(
            action=Actions.manual, order_id=order_id, user_id=user_id
        ),
    )
    builder.button(
        text="🔴",
        callback_data=ConfirmOrder(
            action=Actions.blacklist, order_id=order_id, user_id=user_id
        ),
    )
    builder.adjust(3)

    return builder.as_markup()
