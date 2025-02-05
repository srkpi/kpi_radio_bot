from aiogram import Bot
from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Const

from app.bot.services.feedback import send_feedback
from app.bot.states.main import MainStates
from app.bot.states.feedback import FeedbackStates


async def handle_feedback_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    bot: Bot = manager.middleware_data["bot"]
    await send_feedback(message, bot)
    await manager.switch_to(FeedbackStates.message_sent)


feedback_menu = Dialog(
    Window(
        Const(
            "🖌 *Зворотний звʼязок:*\n\n"
            "📩 Надішли сюди будь-яке повідомлення, і ми його отримаємо.\n"
            '❌ Якщо передумав, натисни "Назад".'
        ),
        MessageInput(handle_feedback_input),
        Start(text=Const("Назад"), id="__main__", state=MainStates.main),
        state=FeedbackStates.feedback,
        parse_mode="Markdown",
    ),
    Window(
        Const(
            'Ваше повідомленя надіслано! За потреби надішліть ще одне, або натисність "Назад".'
        ),
        MessageInput(handle_feedback_input),
        Start(text=Const("Назад"), id="__main__", state=MainStates.main),
        state=FeedbackStates.message_sent,
    ),
)
