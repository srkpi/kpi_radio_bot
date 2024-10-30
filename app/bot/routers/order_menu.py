import operator
from datetime import date, datetime, timedelta
from typing import Any
import re

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Start, Select, Column, Back, Group
from aiogram_dialog.widgets.text import Const, Format
from yt_dlp import YoutubeDL, DownloadError

from app.bot.consts.ethers import WEEKDAY_ETHERS, WEEKEND_ETHERS
from app.bot.consts.other import WEEKDAYS
from app.bot.keyboards.confirm import get_confirm_keyboard
from app.bot.models import Ether, Order
from app.bot.repositories.uow import UnitOfWork
from app.settings import settings
from app.bot.states.main import MainStates
from app.bot.states.order import OrderStates


async def audio_input(message: Message, message_input: MessageInput, manager: DialogManager):
    await message.answer("Аудіофайли не підтримуються")


async def text_input(message: Message, message_input: MessageInput, manager: DialogManager):
    url = re.sub(r'&list=.*', '', message.text)
    try:
        with YoutubeDL() as ydl:
            info = ydl.extract_info(message.text, download=False)
    except DownloadError:
        return await message.answer("Спробуйте ще раз")

    manager.dialog_data["audio"] = {
        "title": info["title"],
        "url": url,
        "duration": info["duration"]
    }

    await manager.next()


async def on_day_selected(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    selected_item: str,
):
    manager.dialog_data['day'] = int(selected_item)
    await manager.next()


async def on_ether_selected(
        callback: CallbackQuery,
        widget: Any,
        manager: DialogManager,
        ether_id: str,
):
    uow: UnitOfWork = manager.middleware_data['uow']
    day = manager.dialog_data['day']
    selected_date = date.today() + timedelta(days=day)
    selected_ether = next(filter(lambda x: x['id'] == int(ether_id), get_ethers_by_day(day)), None)
    ether = await uow.ethers.find_one(Ether.date == selected_date, Ether.start_time == selected_ether["start"])
    if not ether:
        ether = await uow.ethers.create(Ether(
            name=selected_ether["name"],
            start_time=selected_ether["start"],
            end_time=selected_ether["end"],
            date=selected_date
        ))
    order = await uow.orders.create(Order(
        title=manager.dialog_data['audio']['title'],
        url=manager.dialog_data['audio'].get('url'),
        duration=manager.dialog_data['audio']['duration'],
        ether=ether
    ))
    await uow.flush()
    await callback.message.answer("Дякуємо за замовлення, чекай на модерацію!")

    bot: Bot = manager.middleware_data['bot']
    await bot.send_message(
        settings.ADMINS_CHAT_ID,
        f"{manager.dialog_data['audio'].get('url')}\n\n"
        "Замовлення:\n"
        f"{WEEKDAYS[ether.date.weekday()]}, {ether.name}\n"
        f"від {callback.from_user.mention_html()}\n",
        reply_markup=get_confirm_keyboard(order.id)
    )

    await manager.done()


def get_ethers_by_day(day: int):
    selected_date = date.today() + timedelta(days=day)
    is_weekday = selected_date.weekday() < 6
    ethers = WEEKDAY_ETHERS if is_weekday else WEEKEND_ETHERS
    if day == 0:
        now = datetime.now().time()
        return list(filter(lambda x: x["end"] > now, ethers))

    return ethers


async def get_data(dialog_manager: DialogManager, **kwargs):
    audio = MediaAttachment(
        ContentType.AUDIO,
        url=dialog_manager.dialog_data["audio"]["url"] if dialog_manager.dialog_data["audio"].get("url") else None
    )
    days = [
        ("Завтра", "1"),
        ("Післязавтра", "2"),
        ("Післяпіслязавтра", "3"),
    ]
    if len(get_ethers_by_day(0)) > 0:
        days.insert(0, ("Сьогодні", "0"))
    return {
        'audio': audio,
        'days': days
    }


async def get_ethers(dialog_manager: DialogManager, **kwargs):
    day = dialog_manager.dialog_data['day']
    return {
        'ethers': get_ethers_by_day(day)
    }

order_menu = Dialog(
    Window(
        Const(
            "Що ти хочеш почути?\n"
            "Скинь посилання на трек із music.youtube.com\n"
        ),
        MessageInput(
            audio_input,
            content_types=[ContentType.AUDIO]
        ),
        MessageInput(
            text_input,
            content_types=[ContentType.TEXT]
        ),
        Start(
            text=Const("Відміна"),
            id="__main__",
            state=MainStates.main
        ),
        state=OrderStates.input
    ),
    Window(
        Const("Вибери день"),
        Column(
            Select(
                text=Format("{item[0]}"),
                id="day",
                items="days",
                item_id_getter=operator.itemgetter(1),
                on_click=on_day_selected
            )
        ),
        Start(
            text=Const("Відміна"),
            id="__main__",
            state=MainStates.main
        ),
        state=OrderStates.day,
        getter=get_data,
    ),
    Window(
        Const("Тепер вибери час"),
        Group(
            Select(
                text=Format("{item[name]}"),
                id="ether",
                items="ethers",
                item_id_getter=lambda x: str(x['id']),
                on_click=on_ether_selected
            ),
            width=2
        ),
        Back(
            text=Const("Назад")
        ),
        state=OrderStates.ether,
        getter=get_ethers,
    ),
)
