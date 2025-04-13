import operator
from datetime import date, datetime, timedelta, time
from urllib.parse import urlparse, parse_qs
from typing import Any
import re

from ytmusicapi import YTMusic

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Start, Select, Column, Back, Group
from aiogram_dialog.widgets.text import Const, Format

from app.bot.banned_user_exception import BannedUserException
from app.bot.consts.ethers import SCHEDULE
from app.bot.consts.other import WEEKDAYS
from app.bot.keyboards.confirm import get_confirm_keyboard
from app.bot.models import Ether, Order
from app.bot.models.banned_user import BannedUser
from app.bot.models.day_state import DayState
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.alert_state import get_alert_state
from app.bot.states.main import MainStates
from app.bot.states.order import OrderStates
from app.bot.services.genius import get_song_language, get_language_flag
from app.bot.services.spotipy import get_track_info
from app.settings import settings

ytmusic = YTMusic()

with open("filtered_words.txt", "r", encoding="utf-8") as f:
    FILTERED_UK_WORDS = set(f.read().splitlines())

with open("whitelist.txt", "r", encoding="utf-8") as f:
    WHITELIST_UK = set(f.read().splitlines())


def detect_language_advanced(title: str) -> str:
    ukrainian_chars = {"є", "і", "ї"}
    russian_chars = {"ы", "ъ", "э"}

    if any(char in title for char in ukrainian_chars):
        return "uk"

    if any(char in title for char in russian_chars):
        return "ru"

    title_words = set(title.lower().split())
    if title_words & FILTERED_UK_WORDS or title_words & WHITELIST_UK:
        return "uk"

    return "ru"


def extract_youtube_video_id(url) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=|music\.youtube\.com/watch\?v=)",  # youtube.com or music.youtube.com
        r"youtu\.be/",  # youtu.be
    ]

    parsed_url = urlparse(url)

    if parsed_url.netloc == "youtu.be":
        return parsed_url.path.strip("/")

    if "youtube.com" in parsed_url.netloc or "music.youtube.com" in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        return query_params.get("v", [None])[0]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def remove_brackets(s: str) -> str:
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\{.*?\}", "", s)
    s = re.sub(r"\s+", " ", s)

    return s.strip()


async def audio_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    await message.answer("Аудіофайли не підтримуються")


async def search_song_by_url(
    url: str, message: Message, apply_restrictions: bool
) -> dict | None:
    url = re.sub(r"&list=[a-zA-Z0-9]+", "", url)
    is_spotify = False

    if "spotify.com" in url:
        is_spotify = True
        track_info = get_track_info(url)
        if track_info:
            spotify_title = track_info["name"]
            artist = track_info["artists"][0]["name"]
            song_full_title = f"{spotify_title} {artist}"

            song_search = ytmusic.search(song_full_title, filter="songs", limit=1)
            if not len(song_search):
                await message.answer(
                    f"Не вдалося знайти трек {song_full_title} на YouTube"
                )
                return

            top_result = song_search[0]
            title = top_result["title"]
            duration = top_result["duration_seconds"]
            video_id = top_result["videoId"]

            if not video_id:
                await message.answer("На жаль, я не можу програти цю пісню :(")
                return

            title_formatted = remove_brackets(title)
        else:
            await message.answer("Не вдалося знайти трек у Spotify")
            return
    elif "youtube.com" in url or "youtu.be" in url or "music.youtube.com" in url:
        split_text = url.split()
        if len(split_text) == 1:
            if "list=" in url:
                await message.answer(
                    "Це посилання на плейлист. Будь ласка, надішліть одне валідне посилання на Spotify, YouTube або YouTube Music."
                )
                return
        else:
            await message.answer(
                "Невірний URL. Будь ласка, надішліть одне валідне посилання на Spotify, YouTube або YouTube Music."
            )
            return

        video_id = extract_youtube_video_id(url)
        if not video_id:
            await message.answer(
                "Невірний URL. Будь ласка, надішліть одне валідне посилання на Spotify, YouTube або YouTube Music."
            )
            return

        get_song_result = ytmusic.get_song(video_id)
        video_details = get_song_result.get("videoDetails")
        if not video_details:
            await message.answer("На жаль, я не можу програти цю пісню :(")
            return

        title = video_details["title"]
        duration = int(video_details["lengthSeconds"])
        author = video_details["author"]
        song_full_title = remove_brackets(f"{title} {author}")
        title_formatted = remove_brackets(title)
    else:
        await message.answer(
            "Невірний URL. Будь ласка, надішліть одне валідне посилання на Spotify, YouTube або YouTube Music."
        )
        return

    if apply_restrictions and duration > 8 * 60:
        await message.answer("Пісня занадто довга!")
        return

    language = get_song_language(song_full_title)

    if language == "ru":
        language = detect_language_advanced(song_full_title)
        # if apply_restrictions and language == "ru":
        #    return await message.answer(
        #        "І цими пальцями ти пишеш мамі що любиш її? Жодних пісень російською!"
        #    )

    return {
        "title": title_formatted,
        "video_id": video_id,
        "spotify_url": url if is_spotify else None,
        "duration": duration,
        "language": language,
    }


async def text_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    song_info = await search_song_by_url(message.text, message, True)
    if song_info is None:
        return

    manager.dialog_data["audio"] = song_info

    await manager.next()


async def on_day_selected(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    selected_item: str,
):
    manager.dialog_data["day"] = int(selected_item)
    await manager.next()


async def on_ether_selected(
    callback: CallbackQuery,
    widget: Any,
    manager: DialogManager,
    ether_id: str,
):
    uow: UnitOfWork = manager.middleware_data["uow"]
    day = manager.dialog_data["day"]
    selected_date = date.today() + timedelta(days=day)
    selected_ether_group = next(
        filter(
            lambda x: x[0] == int(ether_id), await get_grouped_ethers(day, uow, manager)
        ),
        None,
    )

    if selected_ether_group is None:
        await callback.message.answer("Цей етер більше не доступний")
        return

    user_id = callback.from_user.id
    ether_group = selected_ether_group[1]
    for selected_ether in ether_group:
        ether_start_hour, ether_start_minute = map(
            int, selected_ether["start"].split(":")
        )
        ether_start_time = time(ether_start_hour, ether_start_minute)
        ether = await uow.ethers.find_one(
            Ether.ether_date == selected_date,
            Ether.start_time == ether_start_time,
            Ether.cancelled == False,
        )
        duration = manager.dialog_data["audio"]["duration"]
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

            user_ether_orders = await uow.orders.find(
                Order.ether_id == ether.id,
                Order.ordered_by == user_id,
            )

            user_orders = 1
            user_approved_orders = 0

            for user_order in user_ether_orders:
                if user_order.played and not user_order.play_start:
                    continue

                user_orders += 1
                if user_order.confirmed:
                    user_approved_orders += 1

            total_duration = sum(o.duration for o in ether_orders)

            now = datetime.now()
            if now.date() == ether.ether_date and now.time() > ether.start_time:
                if len(ether_orders):
                    current_playing: Order = await uow.orders.find_one(
                        Order.ether_id == ether.id,
                        Order.played == False,
                        Order.confirmed == True,
                        Order.play_start != None,
                        order=[Order.play_start.desc()],
                    )

                    if current_playing:
                        total_duration -= max(
                            round((now - current_playing.play_start).total_seconds()),
                            0,
                        )

                play_time = now + timedelta(seconds=total_duration)
            else:
                play_delay = 5 * len(ether_orders)
                play_time = datetime.combine(
                    ether.ether_date, ether.start_time
                ) + timedelta(seconds=total_duration + play_delay)

            if play_time + timedelta(seconds=duration) > datetime.combine(
                ether.ether_date, ether.end_time
            ):
                continue  # Пісня не влазе в етер

            play_time_str = play_time.strftime("%H:%M")
        else:
            user_orders = 1
            user_approved_orders = 0

            start_hour, start_minute = map(int, selected_ether["start"].split(":"))
            start_time = time(start_hour, start_minute)

            end_hour, end_minute = map(int, selected_ether["end"].split(":"))
            end_time = time(end_hour, end_minute)

            ether = await uow.ethers.create(
                Ether(
                    name=selected_ether["name"],
                    start_time=start_time,
                    end_time=end_time,
                    ether_date=selected_date,
                    cancelled=False,
                )
            )

            current_time = datetime.now().time()
            if day == 0 and current_time > start_time:
                play_time_str = current_time.strftime("%H:%M")
            else:
                play_time_str = start_time.strftime("%H:%M")

        video_id = manager.dialog_data["audio"].get("video_id")
        same_orders = await uow.orders.find(
            Order.video_id == video_id,
            Order.decision_timestamp != None,
        )

        rating = 0
        for order in same_orders:
            if order.confirmed:
                rating += 1
            else:
                rating -= 1

        moderation_flag = ""
        if rating > 2:
            moderation_flag = "🟢 "
        elif rating < -2:
            moderation_flag = "🔴 "

        order = await uow.orders.create(
            Order(
                title=manager.dialog_data["audio"]["title"],
                video_id=video_id,
                duration=duration,
                ether=ether,
                ordered_by=user_id,
            )
        )

        await uow.flush()
        await callback.message.answer("Дякуємо за замовлення, чекай на модерацію!")

        language = manager.dialog_data["audio"]["language"]
        if language:
            language_prefix = get_language_flag(language) + " "
        else:
            language_prefix = ""

        bot: Bot = manager.middleware_data["bot"]

        spotify_url = manager.dialog_data["audio"].get("spotify_url")
        spotify_link = f' [<a href="{spotify_url}">Spotify</a>]' if spotify_url else ""

        if duration and duration > 0:
            minutes = duration // 60
            seconds = duration % 60
            duration_label = f"⏳ {minutes}:{seconds:02}\n"
        else:
            duration_label = ""

        youtube_url = f"https://youtube.com/watch?v={video_id}"
        youtube_music_link = (
            f' [<a href="https://music.youtube.com/watch?v={video_id}">YM</a>]'
        )

        order_message = await bot.send_message(
            settings.ADMINS_CHAT_ID,
            f"{moderation_flag}{language_prefix}{youtube_url}{youtube_music_link}{spotify_link}\n\n"
            "Замовлення:\n"
            f"{WEEKDAYS[ether.ether_date.weekday()]}, {ether.name}\n{duration_label}"
            f"🕓 {play_time_str}\n"
            f"від {callback.from_user.mention_html()} ({user_approved_orders}/{user_orders})\n",
            reply_markup=get_confirm_keyboard(order.id, user_id),
            message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
        )

        order.order_message_id = order_message.message_id

        await uow.flush()
        await manager.done()
        return

    await uow.flush()
    await callback.message.answer("Пісня не встигне програти до закінчення етеру")


def has_time_passed(cur_time: time, time_str: str | None) -> bool:
    if time_str is None:
        return False

    hour, minute = map(int, time_str.split(":"))
    check_time = time(hour, minute)

    return cur_time >= check_time


async def get_ethers_by_day(day: int, uow: UnitOfWork, dialog_manager: DialogManager):
    selected_date = date.today() + timedelta(days=day)
    day_state = await uow.day_state.find_one(DayState.state_date == selected_date)
    if day_state:
        if day_state.is_closed:
            await dialog_manager.middleware_data["bot"].send_message(
                chat_id=dialog_manager.event.from_user.id,
                text=f"На {selected_date.strftime('%d.%m')} замовляти пісні не можна: {day_state.reason}",
            )

            return []

        weekday = 6 if day_state.is_holiday else selected_date.weekday()
    else:
        weekday = selected_date.weekday()

    day_schedule = SCHEDULE.get(str(weekday))
    if day_schedule is None:
        await dialog_manager.middleware_data["bot"].send_message(
            chat_id=dialog_manager.event.from_user.id,
            text=f"Не можна замовити на цей день :(",
        )

        return []

    user_id = dialog_manager.event.from_user.id
    now = datetime.now().time()
    ether_list = []
    for ether in day_schedule:
        if ether["is_locked"]:
            if (settings.ADMINS and user_id in settings.ADMINS) or (
                day == 0 and has_time_passed(now, ether.get("unlock_time"))
            ):
                if day != 0 or (
                    day == 0 and not has_time_passed(now, ether.get("end"))
                ):
                    ether_list.append(ether)

            continue

        if day != 0:
            ether_list.append(ether)
            continue

        end_hour, end_minute = map(int, ether.get("end").split(":"))
        end_time = time(end_hour, end_minute)
        if now < end_time:
            ether_list.append(ether)

    if len(ether_list) == 0:
        return []

    if day == 0 and await get_alert_state():
        return ether_list[1:]

    return ether_list


async def get_data(dialog_manager: DialogManager, **kwargs):
    uow = dialog_manager.middleware_data["uow"]
    audio = dialog_manager.dialog_data["audio"]
    days = []

    def format_day_offset(offset: int) -> str:
        date = datetime.now().date() + timedelta(days=offset)
        weekday_ukrainian = {
            0: "Пн",
            1: "Вт",
            2: "Ср",
            3: "Чт",
            4: "Пт",
            5: "Сб",
            6: "Нд",
        }
        weekday_name = weekday_ukrainian[date.weekday()]

        return f"{weekday_name} {date.strftime('%d.%m')}"

    if len(await get_ethers_by_day(0, uow, dialog_manager)) > 0:
        days.append(("Сьогодні", "0"))

    if len(await get_ethers_by_day(1, uow, dialog_manager)) > 0:
        days.append(("Завтра", "1"))

    if len(await get_ethers_by_day(2, uow, dialog_manager)) > 0:
        days.append((format_day_offset(2), "2"))

    if len(await get_ethers_by_day(3, uow, dialog_manager)) > 0:
        days.append((format_day_offset(3), "3"))

    return {"audio": audio, "days": days}


async def ban_check(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    is_banned = await uow.banned_users.check_exists(
        BannedUser.user_id == user_id, BannedUser.is_deleted == False
    )

    if is_banned:
        raise BannedUserException()

    return {}


async def get_grouped_ethers(
    day: int, uow: UnitOfWork, dialog_manager: DialogManager
) -> list[tuple[int, list[object]]]:
    ethers = await get_ethers_by_day(day, uow, dialog_manager)
    grouped_ethers = {}

    now = datetime.now().time()

    for ether in ethers:
        ether_name = ether.get("name")
        if ether.get("is_locked"):
            if day == 0 and has_time_passed(now, ether.get("unlock_time")):
                group_name = ether.get("unlock_name", ether_name)
            else:
                group_name = ether_name
        else:
            group_name = ether_name

        if group_name not in grouped_ethers:
            grouped_ethers[group_name] = []

        grouped_ethers[group_name].append(ether)

    indexed_groups = [(i, group) for i, group in enumerate(grouped_ethers.values())]

    return indexed_groups


async def get_ethers(dialog_manager: DialogManager, **kwargs):
    day = dialog_manager.dialog_data["day"]
    uow = dialog_manager.middleware_data["uow"]
    ethers = await get_grouped_ethers(day, uow, dialog_manager)

    if day == 0 and await get_alert_state():
        await dialog_manager.middleware_data["bot"].send_message(
            chat_id=dialog_manager.event.from_user.id,
            text=f"Наразі лунає тривога. Замовлення на поточний етер не приймаються, однак Ви можете замовити на інші!",
        )

    return {"ethers": ethers}


order_menu = Dialog(
    Window(
        Const(
            "Чим хочеш порадувати кампус?\n"
            "Скинь посилання на трек з Youtube Music або Spotify!\n\n"
            "Пам’ятай — під час повітряної тривоги мовлення не здійснюється."
        ),
        MessageInput(audio_input, content_types=[ContentType.AUDIO]),
        MessageInput(text_input, content_types=[ContentType.TEXT]),
        Start(text=Const("Відміна"), id="__main__", state=MainStates.main),
        state=OrderStates.input,
        getter=ban_check,
    ),
    Window(
        Const("Вибери день"),
        Column(
            Select(
                text=Format("{item[0]}"),
                id="day",
                items="days",
                item_id_getter=operator.itemgetter(1),
                on_click=on_day_selected,
            )
        ),
        Start(text=Const("Відміна"), id="__main__", state=MainStates.main),
        state=OrderStates.day,
        getter=get_data,
    ),
    Window(
        Const("Тепер вибери час"),
        Group(
            Select(
                text=Format("{item[1][0][name]}"),
                id="ether",
                items="ethers",
                item_id_getter=lambda x: str(x[0]),
                on_click=on_ether_selected,
            ),
            width=2,
        ),
        Back(text=Const("Назад")),
        state=OrderStates.ether,
        getter=get_ethers,
    ),
)
