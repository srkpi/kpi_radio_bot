import operator
from datetime import date, datetime, timedelta
from typing import Any
import re
import logging

from youtubesearchpython import VideosSearch

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
from app.bot.models.day_state import DayState
from app.bot.repositories.uow import UnitOfWork
from app.settings import settings
from app.bot.states.main import MainStates
from app.bot.states.order import OrderStates
from app.bot.services.genius import get_song_language
from app.bot.services.spotipy import get_track_info


async def audio_input(message: Message, message_input: MessageInput, manager: DialogManager):
    await message.answer("Аудіофайли не підтримуються")


async def text_input(message: Message, message_input: MessageInput, manager: DialogManager):
    url = re.sub(r'&list=[a-zA-Z0-9]+', '', message.text)
    url = re.sub(r'\?si=[a-zA-Z0-9]+', '', url)
    song_name = None
    is_spotify = False

    if "spotify.com" in url:
        is_spotify = True
        track_info = get_track_info(url)
        if track_info:
            title = track_info["name"]
            artist = track_info["artists"][0]["name"]
            song_name = f"{title} {artist}"

            video_search = VideosSearch(song_name, limit=1)
            video_result = video_search.result()
            if not video_result["result"]:
                return await message.answer(
                    f"Не вдалося знайти трек {song_name} на YouTube"
                )

            youtube_url = (
                "https://www.youtube.com/watch?v=" + video_result["result"][0]["id"]
            )
        else:
            return await message.answer("Не вдалося знайти трек у Spotify")
    elif "youtube.com" in url or "youtu.be" in url or "music.youtube.com" in url:
        split_text = url.split()
        if len(split_text) == 1:
            if "list=" not in url:
                youtube_url = url
            else:
                return await message.answer(
                    "Це посилання на плейлист. Будь ласка, надішліть одне валідне посилання на Spotify, YouTube або YouTube Music."
                )
        else:
            return await message.answer(
                "Невірний URL. Будь ласка, надішліть одне валідне посилання на Spotify, YouTube або YouTube Music."
            )
    else:
        return await message.answer(
            "Невірний URL. Будь ласка, надішліть одне валідне посилання на Spotify, YouTube або YouTube Music."
        )

    try:
        with YoutubeDL() as ydl:
            info = ydl.extract_info(youtube_url, download=False, process=False)
    except DownloadError:
        return await message.answer("Спробуйте ще раз")

    title = song_name if song_name else info.get("title")
    language = await get_song_language(title)

    logging.info(f"Song Language: {language}")

    if language == "ru":
        return await message.answer(
            "Російські пісні замовляти не можна"
        )

    manager.dialog_data["audio"] = {
        "title": title,
        "url": youtube_url if is_spotify else url,
        "spotify_url": url if is_spotify else None,
        "duration": info.get("duration"),
        "language": language,
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
    selected_ether = next(filter(lambda x: x['id'] == int(ether_id), await get_ethers_by_day(day, uow)), None)
    ether = await uow.ethers.find_one(Ether.date == selected_date, Ether.start_time == selected_ether["start"], Ether.cancelled == False)
    duration = manager.dialog_data['audio']['duration']
    if ether:
        ether_orders_1 = await uow.orders.find(
            Order.ether_id == ether.id,
            Order.played == False,
            Order.confirmed == True,
        )

        ether_orders_2 = await uow.orders.find(
            Order.ether_id == ether.id,
            Order.played == False,
            Order.decision_timestamp == None,
        )

        ether_orders = ether_orders_1 + ether_orders_2

        total_duration = sum(o.duration for o in ether_orders)

        now = datetime.now()
        if now.date() == ether.date and now.time() > ether.start_time:
            play_delay = 30 * max((len(ether_orders) - 1), 0)
            if len(ether_orders):
                current_playing: Order = await uow.orders.find_one(
                    Order.ether_id == ether.id,
                    Order.played == False,
                    Order.confirmed == True,
                    order=[Order.decision_timestamp.asc()],
                )
                current_play_start = current_playing.play_start

                if current_play_start:
                    total_duration -= max(
                        round((now - current_play_start).total_seconds()),
                        0,
                    )

            play_time = now + timedelta(seconds=total_duration)
        else:
            play_delay = 30 * len(ether_orders)
            play_time = datetime.combine(ether.date, ether.start_time) + timedelta(
                seconds=total_duration + play_delay
            )

        if play_time + timedelta(seconds=duration) > datetime.combine(ether.date, ether.end_time):
            return await callback.message.answer("Пісня не встигне програти до закінчення етеру")

        play_time_str = play_time.strftime("%H:%M")
    else:
        start_time = selected_ether["start"]
        ether = await uow.ethers.create(
            Ether(
                name=selected_ether["name"],
                start_time=start_time,
                end_time=selected_ether["end"],
                date=selected_date,
                cancelled=False,
            )
        )

        current_time = datetime.now().time()
        if day == 0 and current_time > start_time:
            play_time_str = current_time.strftime("%H:%M")
        else:
            play_time_str = start_time.strftime("%H:%M")

    order = await uow.orders.create(Order(
        title=manager.dialog_data['audio']['title'],
        url=manager.dialog_data['audio'].get('url'),
        duration=duration,
        ether=ether
    ))
    await uow.flush()
    await callback.message.answer("Дякуємо за замовлення, чекай на модерацію!")

    language = manager.dialog_data["audio"]["language"]

    bot: Bot = manager.middleware_data['bot']

    spotify_url = manager.dialog_data['audio'].get('spotify_url')
    spotify_link = f' [<a href="{spotify_url}">Spotify</a>]' if spotify_url else ''
    language_label = f' [{language}]' if language else ''

    if duration and duration > 0:
        minutes = duration // 60
        seconds = duration % 60
        duration_label = f"⏳ {minutes}:{seconds:02}\n"
    else:
        duration_label = ""

    await bot.send_message(
        settings.ADMINS_CHAT_ID,
        f"{manager.dialog_data['audio'].get('url')}{spotify_link}{language_label}\n\n"
        "Замовлення:\n"
        f"{WEEKDAYS[ether.date.weekday()]}, {ether.name}\n{duration_label}"
        f"🕓 {play_time_str}\n"
        f"від {callback.from_user.mention_html()}\n",
        reply_markup=get_confirm_keyboard(order.id, callback.from_user.id),
        message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
    )

    await manager.done()


async def get_ethers_by_day(day: int, uow: UnitOfWork):
    selected_date = date.today() + timedelta(days=day)
    day_state = await uow.day_state.find_one(DayState.date == selected_date)
    if day_state:
        if day_state.is_closed:
            return []

        is_weekday = not day_state.is_holiday and selected_date.weekday() < 6
    else:
        is_weekday = selected_date.weekday() < 6

    ethers = WEEKDAY_ETHERS if is_weekday else WEEKEND_ETHERS

    if day == 0:
        now = datetime.now().time()
        return list(filter(lambda x: x["end"] > now, ethers))

    return ethers


async def get_data(dialog_manager: DialogManager, **kwargs):
    uow = dialog_manager.middleware_data["uow"]
    audio = MediaAttachment(
        ContentType.AUDIO,
        url=dialog_manager.dialog_data["audio"].get("url")
    )
    days = []

    if len(await get_ethers_by_day(0, uow)) > 0:
        days.append(("Сьогодні", "0"))

    if len(await get_ethers_by_day(1, uow)) > 0:
        days.append(("Завтра", "1"))

    if len(await get_ethers_by_day(2, uow)) > 0:
        days.append(("Післязавтра", "2"))

    if len(await get_ethers_by_day(3, uow)) > 0:
        days.append(("Післяпіслязавтра", "3"))

    return {
        'audio': audio,
        'days': days
    }


async def get_ethers(dialog_manager: DialogManager, **kwargs):
    day = dialog_manager.dialog_data['day']
    uow = dialog_manager.middleware_data["uow"]
    ethers = await get_ethers_by_day(day, uow)

    return {"ethers": ethers}

order_menu = Dialog(
    Window(
        Const(
            "Що ти хочеш почути?\n"
            "Скинь посилання на трек із music.youtube.com або Spotify\n"
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
