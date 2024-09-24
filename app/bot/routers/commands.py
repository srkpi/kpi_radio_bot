from datetime import datetime

from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy.orm import joinedload, selectinload

from app.bot.models import Ether, Order
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.help import HelpStates
from app.bot.states.main import MainStates


async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MainStates.main, mode=StartMode.RESET_STACK)


async def help_command(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(HelpStates.select, mode=StartMode.RESET_STACK)


async def skip(message: Message, uow: UnitOfWork):
    today = datetime.now()
    order = await uow.orders.find_one(Ether.date == today.date(), Ether.start_time <= today.time(), Ether.end_time >= today.time(), Order.played == False, Order.confirmed == True, options=[joinedload(Order.ether)])
    next_order = await uow.orders.find_one(order.ether_id == order.ether_id, Order.played == False, offset=1)
    order.played = True

    if next_order.file_id:
        player.play(f"telegram://{next_order.file_id}")
    else:
        player.play(f"{next_order.url}")

    await message.answer("Трек скіпнуто")


async def stop(message: Message, uow: UnitOfWork):
    today = datetime.now()
    ether = await uow.ethers.find_one(Ether.date == today.date(), Ether.start_time <= today.time(), Ether.end_time >= today.time(), options=[selectinload(Ether.orders)])
    for order in ether.orders:
        order.played = True
    player.stop()
    await message.answer("Чергу зупинено")