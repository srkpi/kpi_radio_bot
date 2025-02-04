from datetime import datetime

from aiogram import Bot
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy.orm import joinedload, selectinload

from app.bot.models import Ether, Order
from app.bot.models.banned_user import BannedUser
from app.bot.models.day_state import DayState
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.help import HelpStates
from app.bot.states.main import MainStates
from app.settings import settings


def get_text_after_command(message: Message):
    full_text = message.text
    command_end_index = full_text.find(" ")
    if command_end_index == -1:
        return None

    return full_text[command_end_index + 1 :]


async def start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(MainStates.main, mode=StartMode.RESET_STACK)


async def help_command(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(HelpStates.select, mode=StartMode.RESET_STACK)


async def skip(message: Message, uow: UnitOfWork):
    today = datetime.now()
    order = await uow.orders.find_one(
        Ether.ether_date == today.date(),
        Ether.start_time <= today.time(),
        Ether.cancelled == False,
        Order.played == False,
        Order.confirmed == True,
        Order.play_start != None,
        options=[joinedload(Order.ether)],
        order=[Order.play_start.desc()],
    )

    if not order:
        return await message.answer("Зараз нічого не грає")

    next_order = await uow.orders.find_one(
        Order.ether_id == order.ether_id,
        Order.played == False,
        Order.confirmed == True,
        Order.play_start == None,
        order=[Order.decision_timestamp.asc()],
    )
    order.played = True

    if next_order:
        next_order.play_start = datetime.now()
        player.play(f"https://youtube.com/watch?v={next_order.video_id}")

    await uow.flush()
    await message.answer("Трек скіпнуто")


async def stop(message: Message, uow: UnitOfWork):
    today = datetime.now()
    ether = await uow.ethers.find_one(
        Ether.ether_date == today.date(),
        Ether.start_time <= today.time(),
        Ether.cancelled == False,
        Ether.end_time >= today.time(),
        options=[selectinload(Ether.orders)],
    )
    for order in ether.orders:
        order.played = True

    await uow.flush()

    player.stop()
    await message.answer("Чергу зупинено")


async def holiday(message: Message, uow: UnitOfWork):
    today = datetime.now().date()
    current_state = await uow.day_state.find_one(DayState.state_date == today)
    if current_state:
        current_state.is_holiday = True
    else:
        await uow.day_state.create(DayState(state_date=today, is_holiday=True))

    ethers = await uow.ethers.find(
        Ether.ether_date == today,
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

    current_state = await uow.day_state.find_one(DayState.state_date == today)
    if current_state:
        current_state.is_closed = True
        current_state.reason = get_text_after_command(message)
    else:
        await uow.day_state.create(
            DayState(
                state_date=today, is_closed=True, reason=get_text_after_command(message)
            )
        )

    ethers = await uow.ethers.find(
        Ether.ether_date == today,
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

    current_state = await uow.day_state.find_one(DayState.state_date == today)
    if current_state:
        current_state.is_closed = False
        current_state.reason = None
    else:
        await uow.day_state.create(
            DayState(state_date=today, is_closed=False, reason=None)
        )

    await uow.flush()
    await message.answer("День відкритий до замовлень!")


async def ban(message: Message, bot: Bot, uow: UnitOfWork):
    reply_message = message.reply_to_message
    if reply_message is None:
        await message.reply(
            "Команда /ban має бути реплаєм на повідомлення із замовленням"
        )
        return

    order_message_id = reply_message.message_id
    order = await uow.orders.find_one(Order.order_message_id == order_message_id)
    if order is None:
        await message.reply(
            "Команда /ban має бути реплаєм на повідомлення із замовленням"
        )
        return

    user_id = order.ordered_by

    is_banned = await uow.banned_users.check_exists(
        BannedUser.user_id == user_id,
        BannedUser.is_deleted == False
    )

    if is_banned:
        await message.reply("Користувач вже заблокований!")
        return

    reason = get_text_after_command(message)
    await uow.banned_users.create(
        BannedUser(
            user_id=user_id,
            ban_message_id=message.message_id,
            banned_by=message.from_user.id,
            timestamp=datetime.now(),
            reason=reason,
        )
    )
    await uow.flush()
    await message.reply(
        f"Користувач з id <code>{user_id}</code> заблокований!", parse_mode="HTML"
    )

    additional_info = "Ти більше не можеш замовляти пісні. За потреби напиши модераторам, скориставшись функцією зворотнього зв'язку."

    try:
        await bot.send_message(
            user_id,
            (
                f"🚫 Тебе забанили! Причина блокування: {reason}\n\n{additional_info}"
                if reason
                else f"🚫 Тебе забанили!\n\n{additional_info}"
            ),
        )
    except Exception:
        pass


async def unban(message: Message, bot: Bot, uow: UnitOfWork):
    user_id = get_text_after_command(message)

    if not user_id:
        await message.reply("Невірний формат команди! /unban user_id")
        return

    try:
        user_id = int(user_id)
    except ValueError:
        await message.reply("Невірний формат команди! /unban user_id")
        return

    banned_user = await uow.banned_users.find_one(
        BannedUser.user_id == user_id, BannedUser.is_deleted == False
    )

    if not banned_user:
        await message.reply("Цей користувач не заблокований!")
        return

    banned_user.is_deleted = True
    await uow.flush()
    await message.reply(f"Користувач з id <code>{user_id}</code> розблокований!", parse_mode="HTML")

    try:
        await bot.send_message(
            user_id, "🎉 Тебе розблокували! Тепер знову можеш замовляти пісні!"
        )
    except Exception:
        pass


async def ban_list(message: Message, uow: UnitOfWork):
    banned_users = await uow.banned_users.find(BannedUser.is_deleted == False)

    if not banned_users:
        await message.reply("Список заблокованих користувачів порожній")
        return

    ban_list_message = f"<b>== Заблоковані користувачі ({len(banned_users)}) ==</b>\n"

    chat_id = settings.ADMINS_CHAT_ID
    chat_id_formatted = str(chat_id)[4:] if chat_id < 0 else str(chat_id)
    thread_id = settings.ADMINS_MODERATION_THREAD_ID

    for i, user in enumerate(banned_users, 1):
        ban_message_url = (
            f"https://t.me/c/{chat_id_formatted}/{thread_id}/{user.ban_message_id}"
        )
        ban_list_message += f'\n{i}) <code>{user.user_id}</code> - <a href="{ban_message_url}">{user.timestamp.strftime("%m-%d-%Y %H:%M")}</a>'

    await message.reply(ban_list_message, parse_mode="HTML")
