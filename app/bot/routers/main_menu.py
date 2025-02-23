from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Start, Row
from aiogram_dialog.widgets.markup.reply_keyboard import ReplyKeyboardFactory
from aiogram_dialog.widgets.text import Const

from app.bot.states.feedback import FeedbackStates
from app.bot.states.help import HelpStates
from app.bot.states.main import MainStates
from app.bot.states.order import OrderStates
from app.bot.states.player import PlayerStates
from app.bot.states.schedule import ScheduleStates

main_menu = Dialog(
    Window(
        Const(
            "Привіт, це бот Радіо КПІ.\n"
            "Ти можеш:\n"
            "📝 Замовити пісню\n"
            "🖌 Поставити будь-яке запитання, що-небудь запропонувати, запропонувати свою кандидатуру до наших лав\n"
            "🎧 Дізнатися, що грає зараз, грало чи гратиме\n"
            "⏱ Дізнатися, коли в улюбленому КПІ перерви\n\n"
            "⁉️ Радимо насамперед прочитати інструкцію (/help)"
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
        markup_factory=ReplyKeyboardFactory(
            resize_keyboard=True,
        ),
        state=MainStates.main,
    )
)
