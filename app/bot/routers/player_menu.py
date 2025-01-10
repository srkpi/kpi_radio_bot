from datetime import datetime, timedelta

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Start
from aiogram_dialog.widgets.text import Jinja, Const

from app.bot.models import Order
from app.bot.models.ether import Ether
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.main import MainStates
from app.bot.states.player import PlayerStates

from sqlalchemy.orm import selectinload


async def get_data(dialog_manager: DialogManager, **kwargs):
    uow: UnitOfWork = dialog_manager.middleware_data['uow']

    previous_order = await uow.orders.find_one(
        Order.played == True,
        Order.play_start != None,
        order=[Order.play_start.desc()]
    )

    current_order = await uow.orders.find_one(
        Order.played == False,
        Order.play_start != None,
        order=[Order.play_start.desc()],
    )

    next_order = await uow.orders.find_one(
        Order.played == False,
        Order.play_start == None,
        Order.expected_play_time > datetime.now() - timedelta(hours=1),
        order=[Order.expected_play_time.asc()],
    )

    today = datetime.now().date()
    ethers = await uow.ethers.find(
        Ether.date == today,
        Ether.cancelled == False,
        options=[selectinload(Ether.orders)],
    )

    ethers_info = ""
    for ether in ethers:
        orders_string = ""
        orders = [order for order in ether.orders if order.expected_play_time is not None]
        orders.sort(key=lambda x: x.expected_play_time)
        for order in orders:
            if order.confirmed and (not order.played or order.play_start):
                orders_string += f"{'>' if current_order and order.id == current_order.id else '•'} {order.expected_play_time.strftime('%H:%M')} - {order.title}\n"

        if orders_string:
            ethers_info += f"\n{ether.name} ({ether.start_time.strftime('%H:%M')}-{ether.end_time.strftime('%H:%M')}):\n{orders_string}"

    if not ethers_info:
        ethers_info = "\nЧерга на сьогодні порожня!"

    return {
        "previous": previous_order.title if previous_order else "відсутній",
        "current": current_order.title if current_order else "нічого",
        "next": next_order.title if next_order else "відсутній",
        "ethers": ethers_info
    }


player_menu = Dialog(
    Window(
        Jinja(
            "⏮ Попередній трек: {{ previous }}\n"
            "▶️ Зараз грає: {{ current }}\n"
            "⏭ Наступний трек: {{ next }}\n"
            "{{ ethers }}"
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
