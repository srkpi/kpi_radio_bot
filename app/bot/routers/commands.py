from datetime import datetime

from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy.orm import joinedload, selectinload

from app.bot.models import Ether, Order
from app.bot.models.day_state import DayState
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.help import HelpStates
from app.bot.states.main import MainStates


def get_text_after_command(message: Message):
    full_text = message.text
    command_end_index = full_text.find(" ")
    if command_end_index == -1:
        return ""

    return full_text[command_end_index + 1 :]


async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MainStates.main, mode=StartMode.RESET_STACK)


async def help_command(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(HelpStates.select, mode=StartMode.RESET_STACK)


async def skip(message: Message, uow: UnitOfWork):
    today = datetime.now()
    order = await uow.orders.find_one(Ether.date == today.date(), Ether.start_time <= today.time(), Ether.cancelled == False, Order.played == False, Order.confirmed == True, options=[joinedload(Order.ether)], order=[Order.decision_timestamp.asc()])

    if not order:
        return await message.answer("Зараз нічого не грає")

    next_order = await uow.orders.find_one(
        Order.ether_id == order.ether_id,
        Order.played == False,
        Order.confirmed == True,
        order=[Order.decision_timestamp.asc()],
        offset=1,
    )
    order.played = True

    await uow.flush()

    if next_order:
        player.play(f"{next_order.url}")

    await message.answer("Трек скіпнуто")


async def stop(message: Message, uow: UnitOfWork):
    today = datetime.now()
    ether = await uow.ethers.find_one(Ether.date == today.date(), Ether.start_time <= today.time(), Ether.cancelled == False, Ether.end_time >= today.time(), options=[selectinload(Ether.orders)])
    for order in ether.orders:
        order.played = True

    await uow.flush()

    player.stop()
    await message.answer("Чергу зупинено")


async def holiday(message: Message, uow: UnitOfWork):
    today = datetime.now().date()
    current_state = await uow.day_state.find_one(DayState.date == today)
    if current_state:
        current_state.is_holiday = True
    else:
        await uow.day_state.create(DayState(date=today, is_holiday=True))

    ethers = await uow.ethers.find(
        Ether.date == today,
        Ether.cancelled == False,
        options=[selectinload(Ether.orders)],
    )

    for ether in ethers:
        ether.cancelled = True
        for order in ether.orders:
            order.played = True

    await uow.flush()
    player.stop()

    await message.answer("День тепер вихідний! Минула черга на цей день видалена")


async def close(message: Message, uow: UnitOfWork):
    today = datetime.now().date()

    current_state = await uow.day_state.find_one(DayState.date == today)
    if current_state:
        current_state.is_closed = True
        current_state.reason = get_text_after_command(message)
    else:
        await uow.day_state.create(
            DayState(date=today, is_closed=True, reason=get_text_after_command(message))
        )

    ethers = await uow.ethers.find(
        Ether.date == today,
        Ether.cancelled == False,
        options=[selectinload(Ether.orders)],
    )

    for ether in ethers:
        for order in ether.orders:
            order.played = True

    await uow.flush()
    player.stop()

    await message.answer("День закритий для замовлень! Минула черга на цей день видалена")


async def open(message: Message, uow: UnitOfWork):
    today = datetime.now().date()

    current_state = await uow.day_state.find_one(DayState.date == today)
    if current_state:
        current_state.is_closed = False
        current_state.reason = None
    else:
        await uow.day_state.create(
            DayState(
                date=today, is_closed=False, reason=None
            )
        )

    await uow.flush()
    await message.answer("День відкритий до замовлень!")
