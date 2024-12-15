from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Jinja, Const

from app.bot.models import Order
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.main import MainStates
from app.bot.states.player import PlayerStates


async def get_data(dialog_manager: DialogManager, **kwargs):
    uow: UnitOfWork = dialog_manager.middleware_data['uow']

    previous_order = await uow.orders.find_one(
        Order.played == True, order=[Order.id.desc()]
    )

    if previous_order:
        current_order = await uow.orders.find_one(
            Order.id > previous_order.id,
            Order.played == False,
            Order.confirmed == True,
        )

        if current_order:
            next_order = await uow.orders.find_one(
                Order.id > current_order.id,
                Order.confirmed == True,
            )
        else:
            next_order = None
    else:
        current_order = None
        next_order = None

    return {
        "previous": previous_order.title if previous_order else "відсутній",
        "current": current_order.title if current_order else "нічого",
        "next": next_order.title if next_order else "відсутній",
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
