from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Const

from app.bot.states.main import MainStates
from app.bot.states.schedule import ScheduleStates

text = Const(
    """
*Будні*
08:00 - 08:30   Ранковий етер
10:05 - 10:25   Перша перерва
12:00 - 12:20   Друга перерва
13:55 - 14:15   Третя перерва
15:50 - 16:10   Четверта перерва
17:45 - 18:05   П'ята перерва
19:40 - 22:00   Вечірній етер

*Неділя та святкові дні*
9:00 - 16:00    Ранковий етер
16:00 - 22:00   Вечірній етер
"""
)

schedule_menu = Dialog(
    Window(
        text,
        Start(
            text=Const("Назад"),
            id="__main__",
            state=MainStates.main,
            mode=StartMode.RESET_STACK,
        ),
        state=ScheduleStates.schedule,
        parse_mode="Markdown",
    )
)
