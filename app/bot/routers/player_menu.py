from datetime import datetime

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Jinja, Const
from sqlalchemy.orm import joinedload

from app.bot.models import Order, Ether
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.main import MainStates
from app.bot.states.player import PlayerStates


async def get_data(dialog_manager: DialogManager, **kwargs):
    uow: UnitOfWork = dialog_manager.middleware_data['uow']
    today = datetime.now()
    order = await uow.orders.find_one(Ether.date == today.date(), Ether.start_time <= today.time(), Ether.end_time >= today.time(), Order.played == False,
                                      Order.confirmed == True, options=[joinedload(Order.ether)])
    previous_order = await uow.orders.find_one(Order.played == True, order=[Order.id.desc()])
    next_order = await uow.orders.find_one(Order.played == False, offset=1)
    return {
        "previous": previous_order.title if previous_order else '',
        "current": order.title if order else '',
        'next': next_order.title if next_order else ''
    }


player_menu = Dialog(
    Window(
        Jinja(
            "⏮ Попередній трек: {{ previous }}\n"
            "▶️ Зараз грає:  {{ current }}\n"
            "⏭ Наступний трек:  {{ next }}\n"
        ),
        Start(
            text=Const("Назад"),
            id="__main__",
            state=MainStates.main
        ),
        getter=get_data,
        state=PlayerStates.now_playing
    )
)
