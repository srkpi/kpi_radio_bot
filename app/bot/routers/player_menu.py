import html
from datetime import datetime, timedelta

from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Start, Button, Group, Row
from aiogram_dialog.widgets.text import Jinja, Const

from app.bot.models import Order
from app.bot.models.ether import Ether
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.main import MainStates
from app.bot.states.player import PlayerStates

from aiogram.types import CallbackQuery

from sqlalchemy.orm import selectinload


async def next_day_handler(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    selected_date = dialog_manager.dialog_data.get("selected_date")
    if selected_date:
        selected_date = datetime.fromisoformat(selected_date).date()
    else:
        selected_date = datetime.now().date()

    dialog_manager.dialog_data["selected_date"] = (
        selected_date + timedelta(days=1)
    ).isoformat()

    await dialog_manager.update(dialog_manager.dialog_data)


async def prev_day_handler(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    selected_date = dialog_manager.dialog_data.get("selected_date")
    if selected_date:
        selected_date = datetime.fromisoformat(selected_date).date()
    else:
        selected_date = datetime.now().date()

    dialog_manager.dialog_data["selected_date"] = (
        selected_date - timedelta(days=1)
    ).isoformat()

    await dialog_manager.update(dialog_manager.dialog_data)


async def today_handler(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    await dialog_manager.update({"selected_date": datetime.now().date().isoformat()})


async def select_ether_handler(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    idx = int(button.widget_id.split("_")[-1])
    dialog_manager.dialog_data["selected_ether_idx"] = idx
    await dialog_manager.update(dialog_manager.dialog_data)


async def get_data(dialog_manager: DialogManager, **kwargs):
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]

    today = datetime.now().date()
    selected_date = dialog_manager.dialog_data.get("selected_date")
    if selected_date:
        selected_date = datetime.fromisoformat(selected_date).date()
    else:
        selected_date = today

    previous_order = current_order = next_order = None

    if today == selected_date:
        previous_order = await uow.orders.find_one(
            Order.played == True,
            Order.play_start != None,
            order=[Order.play_start.desc()],
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

    ethers = await uow.ethers.find(
        Ether.ether_date == selected_date,
        Ether.cancelled == False,
        options=[selectinload(Ether.orders)],
        order=[Ether.start_time.asc()],
    )

    ether_buttons = None
    selected_ether_idx = dialog_manager.dialog_data.get("selected_ether_idx", 0)
    if (
        len(ethers) == 2
        and ethers[0].name == "Ранково-денний етер"
        and ethers[1].name == "Вечірній етер"
    ):
        ethers_to_show = [ethers[selected_ether_idx]]
        ether_buttons = []
        for i in range(2):
            label = f"[ {i+1} ]" if i == selected_ether_idx else f"{i+1}"
            ether_buttons.append({"label": label, "id": f"ether_{i}"})
    else:
        ethers_to_show = ethers
        dialog_manager.dialog_data.pop("selected_ether_idx", None)

    ethers_info = ""
    for ether in ethers_to_show:
        orders_string = ""
        orders = [
            order for order in ether.orders if order.expected_play_time is not None
        ]
        orders.sort(key=lambda x: x.expected_play_time)
        for order in orders:
            if order.confirmed and (not order.played or order.play_start):
                safe_title = html.escape(order.title)
                if order.video_id:
                    title_link = f'<a href="https://youtube.com/watch?v={order.video_id}">{safe_title}</a>'
                else:
                    title_link = safe_title
                orders_string += f"{'>' if current_order and order.id == current_order.id else '•'} {order.expected_play_time.strftime('%H:%M')} - {title_link}\n"

        if orders_string:
            ethers_info += f"\n{ether.name} ({ether.start_time.strftime('%H:%M')}-{ether.end_time.strftime('%H:%M')}):\n{orders_string}"

    if not ethers_info:
        ethers_info = "\nЧерга порожня!"

    if selected_date != today:
        formatted_date = selected_date.strftime("%d.%m")
        header = "Історія треків за " + formatted_date
    else:
        previous_track = (
            f'<a href="https://youtube.com/watch?v={previous_order.video_id}">{html.escape(previous_order.title)}</a>'
            if previous_order
            else "відсутній"
        )
        current_track = (
            f'<a href="https://youtube.com/watch?v={current_order.video_id}">{html.escape(current_order.title)}</a>'
            if current_order
            else "нічого"
        )
        next_track = (
            f'<a href="https://youtube.com/watch?v={next_order.video_id}">{html.escape(next_order.title)}</a>'
            if next_order
            else "відсутній"
        )
        header = (
            f"⏮ Попередній трек: {previous_track}\n"
            f"▶️ Зараз грає: {current_track}\n"
            f"⏭ Наступний трек: {next_track}"
        )

    return {
        "header": header,
        "ethers": ethers_info,
        "selected_date": selected_date.isoformat(),
        "today": today.isoformat(),
        "ether_buttons": ether_buttons,
    }


player_menu = Dialog(
    Window(
        Jinja("{{ header|safe }}\n{{ ethers|safe }}"),
        Row(
            *[
                Button(
                    Jinja("{{ ether_buttons[0]['label'] if ether_buttons else '' }}"),
                    id="ether_0",
                    when=lambda data, widget, manager: data.get("ether_buttons"),
                    on_click=select_ether_handler,
                ),
                Button(
                    Jinja("{{ ether_buttons[1]['label'] if ether_buttons else '' }}"),
                    id="ether_1",
                    when=lambda data, widget, manager: data.get("ether_buttons"),
                    on_click=select_ether_handler,
                ),
            ]
        ),
        Group(
            Button(
                Const("<----"),
                id="prev_day",
                when=lambda data, widget, manager: data["today"] is None
                or datetime.fromisoformat(data["selected_date"]).date()
                > datetime.fromisoformat(data["today"]).date() - timedelta(days=4),
                on_click=prev_day_handler,
            ),
            Button(
                Const("----->"),
                id="next_day",
                when=lambda data, widget, manager: data["today"] is None
                or datetime.fromisoformat(data["selected_date"]).date()
                < datetime.fromisoformat(data["today"]).date() + timedelta(days=4),
                on_click=next_day_handler,
            ),
            width=2,
        ),
        Button(
            Const("Сьогодні"),
            id="today",
            when=lambda data, widget, manager: data["selected_date"] != data["today"],
            on_click=today_handler,
        ),
        Start(Const("Назад"), id="__main__", state=MainStates.main),
        getter=get_data,
        state=PlayerStates.now_playing,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
)
