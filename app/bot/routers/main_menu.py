from aiogram.enums import ContentType
from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Start, Row
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory
from aiogram_dialog.widgets.text import Const

from app.bot.repositories.uow import UnitOfWork
from app.bot.routers.feedback_menu import ban_check
from app.bot.routers.order_menu import search_song_by_url
from app.bot.states.feedback import FeedbackStates
from app.bot.states.help import HelpStates
from app.bot.states.main import MainStates
from app.bot.states.order import OrderStates
from app.bot.states.player import PlayerStates
from app.bot.states.schedule import ScheduleStates
from app.settings import settings

async def forward_to_order(
    message: Message, message_input: MessageInput, manager: DialogManager
) -> None:
    await ban_check(manager)

    uow: UnitOfWork = manager.middleware_data["uow"]
    apply_restrictions = not settings.ADMINS or message.from_user.id not in settings.ADMINS
    song_info = await search_song_by_url(message.text, message, uow, apply_restrictions)
    if song_info is None:
        return

    await manager.start(OrderStates.day, data={"audio": song_info})


main_menu = Dialog(
    Window(
        Const(
            "Ти можеш:\n"
            "📝 Замовити пісню\n"
            "🖌 Поставити будь-яке запитання, що-небудь запропонувати, запропонувати свою кандидатуру до наших лав\n"
            "🎧 Дізнатися, що грає зараз, грало чи гратиме\n"
            "⏱ Дізнатися, коли в улюбленому КПІ перерви\n\n"
            "🚫 ВІДЕО ВЕРСІЇ ВІДХИЛЯЮТЬСЯ В 70% ВИПАДКІВ\n"
            "⁉️ Радимо насамперед прочитати інструкцію та правила (/help)"
        ),
        Row(
            Start(
                text=Const("🎧 Що грає?"), id="queue", state=PlayerStates.now_playing
            ),
            Start(text=Const("📝 Замовити пісню"), id="order", state=OrderStates.input),
        ),
        Row(
            Start(
                text=Const("🖌 Зворотний звʼязок"),
                id="support",
                state=FeedbackStates.feedback,
            ),
            Start(text=Const("⁉️ Допомога"), id="help", state=HelpStates.select),
            Start(
                text=Const("⏱ Розклад етерів"),
                id="schedule",
                state=ScheduleStates.schedule,
            ),
        ),
        MessageInput(forward_to_order, content_types=[ContentType.TEXT]),
        markup_factory=ReplyKeyboardFactory(
            resize_keyboard=True,
        ),
        state=MainStates.main,
    )
)
