import io
import os
import sqlite3
import subprocess
import re
from datetime import date, datetime, timedelta
from typing import Tuple, List, Optional

from openpyxl import Workbook

from aiogram import Bot
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy.orm import joinedload, selectinload

from aiogram.types import BufferedInputFile

from app.api.routes.alert import clear_queue_alert
from app.bot.models import Ether, Order
from app.bot.models.banned_user import BannedUser
from app.bot.models.day_state import DayState
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork
from app.bot.routers.order_menu import search_song_by_url
from app.bot.services.feedback import get_user_message_id
from app.bot.services.song_downloader import delete_song, get_song_path, is_downloading
from app.bot.states.alert_state import get_alert_state, set_alert_state
from app.bot.states.help import HelpStates
from app.bot.states.main import MainStates
from app.settings import settings


def get_text_after_command(message: Message) -> str | None:
    full_text = message.text
    if not full_text:
        return None

    command_end_index = full_text.find(" ")
    if command_end_index == -1:
        return None

    return full_text[command_end_index + 1 :]


def parse_dates_from_command(arg: str | None) -> list[date] | None:
    """
    Parses a single date (21.06), or a range (21.06-30.06), returns list of date objects.
    If arg is None, returns [today].
    Returns None if invalid.
    """
    if not arg or not arg.strip():
        return [datetime.now().date()]

    arg = arg.strip()
    date_pattern = r"^(\d{2})\.(\d{2})$"
    range_pattern = r"^(\d{2})\.(\d{2})-(\d{2})\.(\d{2})$"

    if re.match(date_pattern, arg):
        day, month = map(int, arg.split("."))
        try:
            d = date(datetime.now().year, month, day)
            return [d]
        except ValueError:
            return None

    m = re.match(range_pattern, arg)
    if m:
        day1, month1, day2, month2 = map(int, m.groups())
        try:
            start = date(datetime.now().year, month1, day1)
            end = date(datetime.now().year, month2, day2)
            if end < start:
                return None
            days = []
            cur = start
            while cur <= end:
                days.append(cur)
                cur += timedelta(days=1)
            return days
        except ValueError:
            return None

    return None


def parse_dates_and_reason(arg: str | None) -> Tuple[Optional[List[date]], Optional[str]]:
    """
    Parses a single date (21.06), a range (21.06-30.06), or just a reason.
    Returns (list of dates, reason). If no date is given, uses today.
    Returns (None, None) if invalid.
    """
    today = datetime.now().date()
    if not arg or not arg.strip():
        return [today], None

    arg = arg.strip()
    # Match: 21.06-23.06 reason
    m = re.match(r"^(\d{2})\.(\d{2})-(\d{2})\.(\d{2})(?:\s+(.*))?$", arg)
    if m:
        day1, month1, day2, month2, reason = m.groups()
        try:
            start = date(today.year, int(month1), int(day1))
            end = date(today.year, int(month2), int(day2))
            if end < start:
                return None, None
            days = []
            cur = start
            while cur <= end:
                days.append(cur)
                cur += timedelta(days=1)
            return days, reason.strip() if reason else None
        except ValueError:
            return None, None

    # Match: 21.06 reason
    m = re.match(r"^(\d{2})\.(\d{2})(?:\s+(.*))?$", arg)
    if m:
        day, month, reason = m.groups()
        try:
            d = date(today.year, int(month), int(day))
            return [d], reason.strip() if reason else None
        except ValueError:
            return None, None

    # If not a date, treat as reason for today
    return [today], arg.strip()


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

    player.stop_current()

    if next_order:
        next_order.play_start = datetime.now()
        video_id = next_order.video_id

        song_path = get_song_path(video_id)
        if song_path:
            player.play(str(song_path))
        else:
            player.play(f"https://youtube.com/watch?v={video_id}")

    await uow.flush()
    await message.answer("Трек скіпнуто")


async def cancel(message: Message, bot: Bot, uow: UnitOfWork):
    reply_message = message.reply_to_message
    if reply_message is None:
        await message.reply(
            "Команда /cancel має бути реплаєм на повідомлення із замовленням"
        )
        return

    reply_message_id = reply_message.message_id
    order = await uow.orders.find_one(Order.order_message_id == reply_message_id)
    if order is None:
        await message.reply(
            "Команда /cancel має бути реплаєм на повідомлення із замовленням"
        )
        return

    if order.played:
        await message.reply("Трек вже програв або вже пропущений")
        return

    order.played = True

    if order.play_start:
        next_order = await uow.orders.find_one(
            Order.ether_id == order.ether_id,
            Order.played == False,
            Order.confirmed == True,
            Order.play_start == None,
            order=[Order.decision_timestamp.asc()],
        )
        order.played = True

        player.stop_current()

        if next_order:
            next_order.play_start = datetime.now()
            video_id = next_order.video_id

            song_path = get_song_path(video_id)
            if song_path:
                player.play(str(song_path))
            else:
                player.play(f"https://youtube.com/watch?v={video_id}")

    video_id = order.video_id
    is_same_song_orders_exists = await uow.orders.check_exists(
        Order.video_id == video_id,
        Order.played == False,
        Order.confirmed == True,
        Order.expected_play_time >= order.expected_play_time - timedelta(hours=1),
    )

    if not is_same_song_orders_exists and not is_downloading(video_id):
        delete_song(video_id)

    await uow.flush()
    await message.answer("Трек скасовано")

    reason = get_text_after_command(message)
    cancel_text = f"🚫 Трек було скасовано: {order.title}"
    if reason:
        cancel_text += "\nПричина: " + reason

    await bot.send_message(order.ordered_by, cancel_text)


async def stop(message: Message, uow: UnitOfWork):
    today = datetime.now()
    ether = await uow.ethers.find_one(
        Ether.ether_date == today.date(),
        Ether.start_time <= today.time(),
        Ether.cancelled == False,
        Ether.end_time >= today.time(),
        options=[selectinload(Ether.orders)],
    )

    if ether is not None:
        for order in ether.orders:
            order.played = True

        await uow.flush()

    if ether is not None and ether.ether_date == today.date():
        player.stop()

    if ether is None:
        await message.answer("Етер не знайдено!")
        return

    await message.answer("Чергу зупинено")


async def stop_today(message: Message, uow: UnitOfWork):
    today = datetime.now()
    ethers = await uow.ethers.find(
        Ether.ether_date == today.date(),
        Ether.end_time >= today.time(),
        Ether.cancelled == False,
        options=[selectinload(Ether.orders)],
    )

    for ether in ethers:
        for order in ether.orders:
            order.played = True

    await uow.flush()

    player.stop()
    await message.answer("Чергу зупинено. Всі замовлення на сьогодні видалено!")


async def stop_all(message: Message, uow: UnitOfWork):
    today = datetime.now()
    today_ethers = await uow.ethers.find(
        Ether.ether_date == today.date(),
        Ether.end_time >= today.time(),
        Ether.cancelled == False,
        options=[selectinload(Ether.orders)],
    )

    for ether in today_ethers:
        for order in ether.orders:
            order.played = True

    next_days_ethers = await uow.ethers.find(
        Ether.ether_date > today.date(),
        Ether.cancelled == False,
        options=[selectinload(Ether.orders)],
    )

    for ether in next_days_ethers:
        for order in ether.orders:
            order.played = True

    await uow.flush()

    player.stop()
    await message.answer("Чергу зупинено. Всі замовлення видалено!")


async def traktor(message: Message, uow: UnitOfWork):
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

    if order:
        order.played = True
        await uow.flush()

    player.play("music/traktor.mp3")

    await message.answer("Трактор їде митися!")


async def holiday(message: Message, uow: UnitOfWork):
    arg = get_text_after_command(message)
    dates, _ = parse_dates_and_reason(arg)
    if not dates:
        await message.reply(
            "Невірний формат дати! Використовуйте /holiday або /holiday 21.06 або /holiday 21.06-30.06"
        )
        return

    for d in dates:
        if d.weekday() == 6:
            await message.answer(f"{d.strftime('%d.%m')} — неділя завжди вихідний день")
            continue

        current_state = await uow.day_state.find_one(DayState.state_date == d)
        if current_state:
            current_state.is_holiday = True
        else:
            await uow.day_state.create(DayState(state_date=d, is_holiday=True))

        ethers = await uow.ethers.find(
            Ether.ether_date == d,
            Ether.cancelled == False,
            options=[selectinload(Ether.orders)],
        )

        for ether in ethers:
            ether.cancelled = True
            for order in ether.orders:
                order.played = True

    await uow.flush()
    if datetime.now().date() in dates:
        player.stop()
    if len(dates) == 1:
        await message.answer(
            f"День {dates[0].strftime('%d.%m')} тепер вихідний! Минула черга на цей день очищена!"
        )
    else:
        await message.answer(
            f"Дні {dates[0].strftime('%d.%m')} — {dates[-1].strftime('%d.%m')} тепер вихідні! Минула черга на ці дні очищена!"
        )


async def unholiday(message: Message, uow: UnitOfWork):
    arg = get_text_after_command(message)
    dates, _ = parse_dates_and_reason(arg)
    if not dates:
        await message.reply(
            "Невірний формат дати! Використовуйте /unholiday або /unholiday 21.06 або /unholiday 21.06-30.06"
        )
        return

    for d in dates:
        current_state = await uow.day_state.find_one(DayState.state_date == d)
        if current_state is None or not current_state.is_holiday:
            await message.answer(f"{d.strftime('%d.%m')} не був позначений як вихідний")
            continue

        current_state.is_holiday = False

        ethers = await uow.ethers.find(
            Ether.ether_date == d,
            Ether.cancelled == False,
            options=[selectinload(Ether.orders)],
        )

        for ether in ethers:
            ether.cancelled = True
            for order in ether.orders:
                order.played = True

    await uow.flush()
    if datetime.now().date() in dates:
        player.stop()
    if len(dates) == 1:
        await message.answer(
            f"День {dates[0].strftime('%d.%m')} тепер не вихідний! Минула черга на цей день очищена!"
        )
    else:
        await message.answer(
            f"Дні {dates[0].strftime('%d.%m')} — {dates[-1].strftime('%d.%m')} тепер не вихідні! Минула черга на ці дні очищена!"
        )


async def close(message: Message, uow: UnitOfWork):
    arg = get_text_after_command(message)
    dates, reason = parse_dates_and_reason(arg)
    if not dates:
        await message.reply(
            "Невірний формат дати! Використовуйте /close, /close 21.06, /close 21.06-23.06 або /close 21.06 причина"
        )
        return

    for d in dates:
        current_state = await uow.day_state.find_one(DayState.state_date == d)
        if current_state:
            current_state.is_closed = True
            current_state.reason = reason
        else:
            await uow.day_state.create(
                DayState(state_date=d, is_closed=True, reason=reason)
            )

        ethers = await uow.ethers.find(
            Ether.ether_date == d,
            Ether.cancelled == False,
            options=[selectinload(Ether.orders)],
        )

        for ether in ethers:
            for order in ether.orders:
                order.played = True

    await uow.flush()
    if datetime.now().date() in dates:
        player.stop()

    if len(dates) == 1:
        await message.answer(
            f"День {dates[0].strftime('%d.%m')} закритий для замовлень! Минула черга на цей день видалена"
        )
    else:
        await message.answer(
            f"Дні {dates[0].strftime('%d.%m')} — {dates[-1].strftime('%d.%m')} закриті для замовлень! Минула черга на ці дні видалена"
        )


async def open(message: Message, uow: UnitOfWork):
    arg = get_text_after_command(message)
    dates, _ = parse_dates_and_reason(arg)
    if not dates:
        await message.reply(
            "Невірний формат дати! Використовуйте /open, /open 21.06 або /open 21.06-23.06"
        )
        return

    for d in dates:
        current_state = await uow.day_state.find_one(DayState.state_date == d)
        if current_state:
            current_state.is_closed = False
            current_state.reason = None
        else:
            await uow.day_state.create(
                DayState(state_date=d, is_closed=False, reason=None)
            )

    await uow.flush()

    if len(dates) == 1:
        await message.answer(
            f"День {dates[0].strftime('%d.%m')} відкритий до замовлень!"
        )
    else:
        await message.answer(
            f"Дні {dates[0].strftime('%d.%m')} — {dates[-1].strftime('%d.%m')} відкриті до замовлень!"
        )


async def alert(message: Message, bot: Bot, uow: UnitOfWork):
    is_alert = await get_alert_state()
    if is_alert:
        await message.reply("Наразі вже триває тривога!")
        return

    await set_alert_state(True)
    await clear_queue_alert(uow, bot)

    player.play("music/alert.mp3")

    await message.reply("Повітряна тривога увімкненна!")


async def stop_alert(message: Message, uow: UnitOfWork):
    is_alert = await get_alert_state()
    if not is_alert:
        await message.reply("Тривоги наразі немає!")
        return

    await set_alert_state(False)

    player.play("music/all_clear.mp3")

    await message.reply("Повітряна тривога вимкнена!")


async def ban(message: Message, bot: Bot, uow: UnitOfWork):
    reply_message = message.reply_to_message
    if reply_message is None:
        await message.reply(
            "Команда /ban має бути реплаєм на повідомлення із замовленням або на повідомлення фідбеку"
        )
        return

    reply_message_id = reply_message.message_id
    user_id, _ = await get_user_message_id(reply_message_id)
    if user_id is None:
        order = await uow.orders.find_one(Order.order_message_id == reply_message_id)
        if order is None:
            await message.reply(
                "Команда /ban має бути реплаєм на повідомлення із замовленням або на повідомлення фідбеку"
            )
            return

        user_id = order.ordered_by

    is_banned = await uow.banned_users.check_exists(
        BannedUser.user_id == user_id, BannedUser.is_deleted == False
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

    block_reason = f" Причина блокування: {reason}" if reason else ""
    additional_info = "Ти більше не можеш замовляти пісні. За потреби напиши модераторам, скориставшись функцією зворотнього зв'язку."
    try:
        await bot.send_message(
            user_id, f"🚫 Тебе забанили!{block_reason}\n\n{additional_info}"
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
    await message.reply(
        f"Користувач з id <code>{user_id}</code> розблокований!", parse_mode="HTML"
    )

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

    for i, user in enumerate(banned_users, 1):
        ban_message_url = f"https://t.me/c/{chat_id_formatted}/{user.ban_message_id}"
        ban_list_message += f'\n{i}) <code>{user.user_id}</code> - <a href="{ban_message_url}">{user.timestamp.strftime("%d.%m.%Y %H:%M")}</a>'

    await message.reply(ban_list_message, parse_mode="HTML")


async def set_volume(message: Message):
    volume = get_text_after_command(message)

    if not volume:
        await message.reply("Невірний формат команди! /volume гучність_цілим_числом")
        return

    try:
        volume = int(volume)
    except ValueError:
        await message.reply("Невірний формат команди! /volume гучність_цілим_числом")
        return

    if not 0 <= volume <= 100:
        await message.reply("Гучність має бути в межах 0-100")
        return

    if player.volume == volume:
        await message.reply("Наразі вже встановлена така гучність")
        return

    player.set_volume(volume)

    await message.reply(f"Гучність успішно встановлена на {volume}%")


async def set_temp_volume(message: Message):
    volume = get_text_after_command(message)

    if not volume:
        await message.reply(
            "Невірний формат команди! /temp_volume гучність_цілим_числом"
        )
        return

    try:
        volume = int(volume)
    except ValueError:
        await message.reply(
            "Невірний формат команди! /temp_volume гучність_цілим_числом"
        )
        return

    if not 0 <= volume <= 100:
        await message.reply("Гучність має бути в межах 0-100")
        return

    if player.volume == volume:
        await message.reply("Наразі вже встановлена така гучність")
        return

    player.set_temp_volume(volume)

    await message.reply(f"Гучність для поточної пісні успішно встановлена на {volume}%")


async def send_orders(message: Message, uow: UnitOfWork):
    await uow.flush()

    conn = sqlite3.connect("radio.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100;")
    orders_columns = [desc[0] for desc in cursor.description]
    orders_rows = cursor.fetchall()

    cursor.execute("SELECT * FROM ethers ORDER BY id DESC LIMIT 100;")
    ethers_columns = [desc[0] for desc in cursor.description]
    ethers_rows = cursor.fetchall()

    conn.close()

    buffer = io.BytesIO()
    wb = Workbook()
    wb.remove(wb.active)

    orders_ws = wb.create_sheet(title="orders")
    orders_ws.append(orders_columns)
    for row in orders_rows:
        orders_ws.append(row)

    orders_ws.freeze_panes = "A2"

    for col_idx, column in enumerate(orders_columns, 1):
        col_values = [
            str(row[col_idx - 1]) for row in orders_rows if row[col_idx - 1] is not None
        ]
        max_length = max([len(str(column))] + [len(val) for val in col_values])
        orders_ws.column_dimensions[
            orders_ws.cell(row=1, column=col_idx).column_letter
        ].width = (max_length + 2)

    ethers_ws = wb.create_sheet(title="ethers")
    ethers_ws.append(ethers_columns)
    for row in ethers_rows:
        ethers_ws.append(row)

    ethers_ws.freeze_panes = "A2"

    for col_idx, column in enumerate(ethers_columns, 1):
        col_values = [
            str(row[col_idx - 1]) for row in ethers_rows if row[col_idx - 1] is not None
        ]
        max_length = max([len(str(column))] + [len(val) for val in col_values])
        ethers_ws.column_dimensions[
            ethers_ws.cell(row=1, column=col_idx).column_letter
        ].width = (max_length + 2)

    wb.save(buffer)
    buffer.seek(0)

    await message.reply_document(
        document=BufferedInputFile(file=buffer.getvalue(), filename="orders.xlsx")
    )


async def send_database(message: Message, uow: UnitOfWork):
    await uow.flush()

    conn = sqlite3.connect("radio.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    buffer = io.BytesIO()
    wb = Workbook()
    wb.remove(wb.active)

    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        ws = wb.create_sheet(title=table)
        ws.append(columns)

        for row in rows:
            ws.append(row)

        ws.freeze_panes = "A2"

        for col_idx, column in enumerate(columns, 1):
            col_values = [
                str(row[col_idx - 1]) for row in rows if row[col_idx - 1] is not None
            ]
            max_length = max([len(str(column))] + [len(val) for val in col_values])
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = (
                max_length + 2
            )

    conn.close()

    wb.save(buffer)
    buffer.seek(0)

    await message.reply_document(
        document=BufferedInputFile(file=buffer.getvalue(), filename="database.xlsx")
    )


async def restart(message: Message, uow: UnitOfWork):
    try:
        await uow.flush()
    except Exception:
        pass

    script_path = os.path.abspath("./restart_bot.sh")
    subprocess.Popen(
        ["nohup", "bash", script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("Bot restart script triggered. Exiting current instance.")
    await message.reply("🔄 Бот зараз перезапуститься!")


async def force_play(message: Message, uow: UnitOfWork):
    url = get_text_after_command(message)
    if not url:
        await message.reply("Невірний формат команди! /force_play {url}")
        return

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

    if order:
        order.played = True
        await uow.flush()

    video_info = await search_song_by_url(url, message, False)
    if video_info is None:
        return

    video_id = video_info["video_id"]

    song_path = get_song_path(video_id)
    if song_path:
        player.play(str(song_path))
    else:
        player.play(f"https://youtube.com/watch?v={video_id}")

    await message.reply(f"⏯️ Примусово програється: {video_info['title']}")
