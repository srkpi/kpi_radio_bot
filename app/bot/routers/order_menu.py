import html
import operator
from datetime import date, datetime, timedelta, time
from urllib.parse import urlparse, parse_qs
from typing import Any, List
import re

import regex
from ytmusicapi import YTMusic

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, StartMode, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Start, Select, Column, Back, Group
from aiogram_dialog.widgets.text import Const, Format, Jinja

from app.bot.banned_user_exception import BannedUserException
from app.bot.consts.ethers import SCHEDULE
from app.bot.consts.other import AVERAGE_SONG_SWITCH_DELAY, WEEKDAYS
from app.bot.keyboards.confirm import get_confirm_keyboard
from app.bot.models import Ether, Order
from app.bot.models.auto_moderation import AutoModeration
from app.bot.models.banned_user import BannedUser
from app.bot.models.day_state import DayState
from app.bot.player.mpv_player import player, _get_order_play_source
from app.bot.repositories.uow import UnitOfWork
from app.bot.routers.player_menu import get_ethers_info, select_ether_handler
from app.bot.services.song_downloader import (
    add_to_download_queue,
    add_telegram_to_download_queue,
    download_telegram_file,
    get_song_path,
)
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

with open("russian_authors.txt", "r", encoding="utf-8") as f:
    RUSSIAN_AUTHORS = [line.lower() for line in f.read().splitlines()]


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


def compile_block_phrase_pattern(phrases: List[str]):
    escaped_phrases = [regex.escape(a.lower()) for a in phrases if a.strip()]
    escaped_phrases.sort(key=len, reverse=True)
    group = "(?:" + "|".join(escaped_phrases) + ")"
    pattern = rf"\b{group}\b"

    return regex.compile(pattern, flags=regex.IGNORECASE)


RUSSIAN_AUTHORS_PATTERN = compile_block_phrase_pattern(RUSSIAN_AUTHORS)


def extract_youtube_video_id(url: str) -> str | None:
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.lower()
    path = parsed_url.path
    query = parsed_url.query

    # Handle youtu.be/<video_id>
    if "youtu.be" in netloc:
        return path.strip("/")

    # Handle youtube.com/watch?v=<video_id> or music.youtube.com/watch?v=<video_id>
    if "youtube.com" in netloc:
        query_params = parse_qs(query)
        if "v" in query_params:
            return query_params["v"][0]

    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
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
) -> None:
    user_id = message.from_user.id

    if not settings.ADMINS or user_id not in settings.ADMINS:
        await message.answer("Аудіофайли не підтримуються")
        return

    if message.audio:
        file_id = message.audio.file_id
        duration = message.audio.duration or 0
        title = (
            message.audio.title
            or message.audio.file_name
            or "Аудіофайл"
        )
        title = remove_brackets(title)
    elif message.voice:
        file_id = message.voice.file_id
        duration = message.voice.duration or 0
        title = "Голосове повідомлення"
    else:
        await message.answer("Аудіофайли не підтримуються")
        return

    song_info = {
        "title": title,
        "video_id": None,
        "file_id": file_id,
        "spotify_url": None,
        "duration": duration,
        "language": None,
    }

    manager.dialog_data["audio"] = song_info
    await manager.switch_to(OrderStates.day)


async def search_song_by_url(
    url: str, message: Message, uow: UnitOfWork, apply_restrictions: bool
) -> dict | None:
    url = re.sub(r"&list=[a-zA-Z0-9]+", "", url)
    is_spotify = False

    if "spotify.com" in url:
        is_spotify = True
        track_info = get_track_info(url)
        if track_info:
            spotify_title = track_info["name"]
            artist = track_info["artists"][0]["name"]
            song_original_full_title = f"{spotify_title} {artist}"
            song_full_title = song_original_full_title

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
        song_original_full_title = f"{title} {author}"
        song_full_title = remove_brackets(song_original_full_title)
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

    if apply_restrictions:
        full_title = song_original_full_title.lower()
        matched = RUSSIAN_AUTHORS_PATTERN.search(full_title)
        is_russian = matched is not None

        if not matched:
            phrases = await uow.block_phrases.find()
            if phrases:
                block_phrases = compile_block_phrase_pattern(
                    [phrase.phrase for phrase in phrases if phrase.phrase in full_title]
                )
                matched = block_phrases.search(full_title)

        if matched:
            matched_str = matched.group(0).strip()
            if matched_str:
                escaped_match = html.escape(matched_str)
                reason = "Російський автор:" if is_russian else "Назва містить:"
                await message.answer(
                    f"🚫 Я не буду програвати цю пісню! {reason} {escaped_match}"
                )
                spotify_link = f' [<a href="{url}">Spotify</a>]' if is_spotify else ""

                if duration and duration > 0:
                    minutes = duration // 60
                    seconds = duration % 60
                    duration_label = f"⏳ {minutes}:{seconds:02}\n"
                else:
                    duration_label = ""

                if language:
                    language_prefix = get_language_flag(language) + " "
                else:
                    language_prefix = ""

                youtube_url = (
                    f'[<a href="https://youtube.com/watch?v={video_id}">YouTube</a>]'
                )
                youtube_music_link = (
                    f' [<a href="https://music.youtube.com/watch?v={video_id}">YM</a>]'
                )

                await message.bot.send_message(
                    settings.ADMINS_CHAT_ID,
                    f"🚫 {language_prefix}{youtube_url}{youtube_music_link}{spotify_link}\n\n"
                    f"{duration_label}"
                    f"від {message.from_user.mention_html()}\n"
                    f"Я відмовився програвати цю пісню! {reason} {escaped_match}",
                    message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
                )
                return

    return {
        "title": title_formatted,
        "video_id": video_id,
        "file_id": None,
        "spotify_url": url if is_spotify else None,
        "duration": duration,
        "language": language,
    }


async def text_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    uow: UnitOfWork = manager.middleware_data["uow"]
    song_info = await search_song_by_url(message.text, message, uow, True)
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

    audio_data = manager.dialog_data.get("audio") or manager.start_data.get("audio", {})
    video_id = audio_data.get("video_id")
    file_id = audio_data.get("file_id")
    is_file_order = bool(file_id) and video_id is None

    not_confimred_orders_duration = 0

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

            confirmed_orders_duration = sum(o.duration for o in ether_orders_1)
            not_confimred_orders_duration = sum(o.duration for o in ether_orders_2)
            total_duration = confirmed_orders_duration + not_confimred_orders_duration

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

                    if current_playing and current_playing.play_start:
                        total_duration -= max(
                            round((now - current_playing.play_start).total_seconds()),
                            0,
                        )

                play_time = now + timedelta(seconds=total_duration)
            else:
                play_delay = AVERAGE_SONG_SWITCH_DELAY * len(ether_orders)
                not_confimred_orders_duration += AVERAGE_SONG_SWITCH_DELAY * len(
                    ether_orders_2
                )

                play_time = datetime.combine(
                    ether.ether_date, ether.start_time
                ) + timedelta(seconds=total_duration + play_delay)

            if play_time + timedelta(seconds=duration) > datetime.combine(
                ether.ether_date, ether.end_time
            ):
                continue  # Song doesn't fit

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
                play_time = datetime.now()
                play_time_str = current_time.strftime("%H:%M")
            else:
                play_time = datetime.combine(datetime.today().date(), start_time)
                play_time_str = start_time.strftime("%H:%M")

                if play_time + timedelta(seconds=duration) > datetime.combine(
                    ether.ether_date, ether.end_time
                ):
                    continue  # Song doesn't fit

        today = datetime.today().date()
        start_dt = datetime.combine(today, ether.start_time)
        end_dt = datetime.combine(today, ether.end_time)

        is_long_ether = ether.name == "Вечірній етер" or end_dt - start_dt > timedelta(
            hours=2
        )

        order_title = html.escape(manager.dialog_data["audio"]["title"])

        if is_file_order:
            confirmation_status = True
            decision_label = "✅ Файл адміна"
            moderation_flag = "📁 "
            cancel_text = ""
        else:
            same_orders = await uow.orders.find(Order.video_id == video_id)

            recent_ordered = False
            will_play_soon = False
            recently_played = False

            rating = 0
            same_ether_orders: list[Order] = []
            for order in same_orders:
                if order.ether_id == ether.id:
                    if order.expected_play_time:
                        same_ether_orders.append(order)
                        now = datetime.now()

                        if (
                            order.played == False
                            and (
                                now.date() == ether.ether_date
                                and now < order.expected_play_time
                                and now + timedelta(minutes=30) > order.expected_play_time
                            )
                            or play_time - timedelta(minutes=30) < order.expected_play_time
                        ):
                            will_play_soon = True

                        if (
                            order.play_start
                            and order.played == True
                            and now
                            < order.play_start
                            + timedelta(
                                seconds=order.duration,
                                minutes=30,
                            )
                        ):
                            recently_played = True

                    elif order.decided_by is None and not order.played:
                        recent_ordered = True

                if order.confirmed:
                    rating += 1
                elif order.decision_timestamp and order.decided_by != 0:
                    rating -= 1

            confirmation_status = None
            auto_moderation_choice = await uow.auto_moderation.find_one(
                AutoModeration.video_id == video_id, AutoModeration.is_deleted == False
            )

            moderation_flag = ""

            if auto_moderation_choice and auto_moderation_choice.confirm is None:
                moderation_flag = "🟨 "
            elif auto_moderation_choice and auto_moderation_choice.confirm == False:
                moderation_flag = "🟥 "
                cancel_reason = "у блеклісті"
                if not settings.ADMINS or user_id not in settings.ADMINS:
                    confirmation_status = False
                    cancel_text = "🚫 Замовлення автоматично відхилено. Рекомендуємо ознайомитися з правилами або написати адміністраторам через функцію зворотного зв'язку!"
                    decision_label = f"🚫 Відхлилено автоматично ({cancel_reason})"
            elif rating < -2:
                moderation_flag = "🔴 "
                cancel_reason = "часто відхиляють"

                if not settings.ADMINS or user_id not in settings.ADMINS:
                    confirmation_status = False
                    cancel_text = "🚫 Замовлення автоматично відхилено. Рекомендуємо ознайомитися з правилами або написати адміністраторам через функцію зворотного зв'язку!"
                    decision_label = f"🚫 Відхлилено автоматично ({cancel_reason})"
            elif rating > 2 or (auto_moderation_choice and auto_moderation_choice.confirm):
                moderation_flag = (
                    "🟩 "
                    if auto_moderation_choice and auto_moderation_choice.confirm == True
                    else "🟢 "
                )

                if user_orders <= 2:
                    confirmation_status = True
                elif is_long_ether and user_orders <= 5:
                    confirmation_status = True

            if same_ether_orders and not is_long_ether:
                same_ether_orders.sort(key=lambda x: x.expected_play_time, reverse=True)

                cancel_text = "🚫 Замовлення автоматично відхилено, адже така пісня вже була замовлена. "
                scheduled_order = same_ether_orders[0]

                if scheduled_order.play_start:
                    alredy_play_start_str = scheduled_order.play_start.strftime("%H:%M")

                    if scheduled_order.played:
                        cancel_text += f"Вже програла о {alredy_play_start_str}"
                    else:
                        cancel_text += f"Грає з {alredy_play_start_str}"
                else:
                    scheduled_play_time_str = scheduled_order.expected_play_time.strftime(
                        "%H:%M"
                    )
                    cancel_text += f"Почне грати о {scheduled_play_time_str}"

                decision_label = "🚫 Відхлилено автоматично (вже замовлено, НЕ вечірній етер, НЕ вихідний)"
                confirmation_status = False

            elif recent_ordered:
                cancel_text = "🚫 Замовлення автоматично відхилено, адже така пісня вже замовлена та чекає модерації."
                decision_label = (
                    "🚫 Відхлилено автоматично (вже замовлено, чекає апруву на цей етер)"
                )
                confirmation_status = False

            elif will_play_soon:
                cancel_text = (
                    "🚫 Замовлення автоматично відхилено, має програти на цьому етері."
                )
                decision_label = (
                    "🚫 Відхлилено автоматично (вже замовлено, має програти на цьому етері)"
                )
                confirmation_status = False

            elif recently_played:
                cancel_text = (
                    "🚫 Замовлення автоматично відхилено, ця пісня нещодавно програла."
                )
                decision_label = (
                    "🚫 Відхлилено автоматично (вже замовлено, нещодавно програла)"
                )
                confirmation_status = False

        play_now = False
        if confirmation_status is None:
            await callback.message.answer("Дякуємо за замовлення, чекай на модерацію!")
            decision_label = ""
        elif confirmation_status == False:
            await callback.message.answer(cancel_text)
        else:
            user_approved_orders += 1
            if not is_file_order:
                decision_label = "✅ Прийнято автоматично"

            play_time -= timedelta(seconds=not_confimred_orders_duration)
            play_time_str = play_time.strftime("%H:%M")

            current_datetime = datetime.now()
            cur_date = current_datetime.date()
            cur_time = current_datetime.time()

            ether_date = ether.ether_date

            if ether_date == cur_date:
                play_date_str = "сьогодні"
            elif ether_date == (current_datetime + timedelta(days=1)).date():
                play_date_str = "завтра"
            elif ether_date == (current_datetime + timedelta(days=2)).date():
                play_date_str = "післязавтра"
            else:
                play_date_str = ether.ether_date.strftime("%d.%m")

            if (
                ether.ether_date == cur_date
                and ether.start_time < cur_time
                and ether.end_time > cur_time
            ):
                current_playing_order: Order = await uow.orders.find_one(
                    Order.ether_id == ether.id,
                    Order.played == False,
                    Order.confirmed == True,
                    Order.play_start != None,
                    order=[Order.play_start.desc()],
                )

                ether_not_played_orders: list[Order] = await uow.orders.find(
                    Order.ether_id == ether.id,
                    Order.played == False,
                    Order.confirmed == True,
                )

                if current_playing_order or len(ether_not_played_orders):
                    await callback.message.answer(
                        f"✅ Твоє замовлення прийнято: {order_title}\n"
                        f"🕓 Орієнтовно програє: {play_date_str} {play_time_str}",
                    )
                else:
                    play_now = True
                    await callback.message.answer(
                        f"✅ Твоє замовлення прийнято: {order_title}\n"
                        f"🕓 Орієнтовно програє: зараз",
                    )
            else:
                await callback.message.answer(
                    f"✅ Твоє замовлення прийнято: {order_title}\n"
                    f"🕓 Орієнтовно програє: {play_date_str} {play_time_str}",
                )

        order = await uow.orders.create(
            Order(
                title=manager.dialog_data["audio"]["title"],
                video_id=video_id,
                file_id=file_id,
                duration=duration,
                ether=ether,
                ordered_by=user_id,
                decided_by=None if confirmation_status is None else 0,
                decision_timestamp=(
                    None if confirmation_status is None else datetime.now()
                ),
                confirmed=True if confirmation_status else False,
                expected_play_time=play_time if confirmation_status else None,
            )
        )

        await uow.flush()

        bot: Bot = manager.middleware_data["bot"]

        if duration and duration > 0:
            minutes = duration // 60
            seconds = duration % 60
            duration_label = f"⏳ {minutes}:{seconds:02}\n"
        else:
            duration_label = ""

        if is_file_order:
            # File orders: show a simple header without YouTube links
            header_line = f"📁 {html.escape(manager.dialog_data['audio']['title'])}"
        else:
            language = manager.dialog_data["audio"]["language"]
            language_prefix = get_language_flag(language) + " " if language else ""

            spotify_url = manager.dialog_data["audio"].get("spotify_url")
            spotify_link = (
                f' [<a href="{spotify_url}">Spotify</a>]' if spotify_url else ""
            )

            youtube_url = (
                f'[<a href="https://youtube.com/watch?v={video_id}">YouTube</a>]'
            )
            youtube_music_link = (
                f' [<a href="https://music.youtube.com/watch?v={video_id}">YM</a>]'
            )

            header_line = (
                f"{moderation_flag}{language_prefix}"
                f"{youtube_url}{youtube_music_link}{spotify_link}"
            )

        if decision_label:
            decision_label += " " + datetime.now().strftime("%H:%M:%S")

        order_message = await bot.send_message(
            settings.ADMINS_CHAT_ID,
            f"{header_line}\n\n"
            f"{WEEKDAYS[ether.ether_date.weekday()]}, {ether.name}\n{duration_label}"
            f"🕓 {play_time_str}\n"
            f"від {callback.from_user.mention_html()} ({user_approved_orders}/{user_orders})\n"
            + decision_label,
            reply_markup=(
                get_confirm_keyboard(order.id, user_id)
                if confirmation_status is None
                else None
            ),
            message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
        )

        order.order_message_id = order_message.message_id

        await uow.flush()
        await manager.done()

        if not confirmation_status:
            return

        # ── Queue download or play immediately ────────────────────────────
        if not play_now or await get_alert_state():
            if is_file_order:
                await add_telegram_to_download_queue(file_id)
            elif video_id:
                await add_to_download_queue(video_id)
            return

        # Play right now
        order.play_start = datetime.now()

        if is_file_order:
            # Download from Telegram and play (file is usually small, fast)
            downloaded = await download_telegram_file(file_id)
            if downloaded:
                player.play(str(downloaded))
        else:
            song_path = get_song_path(video_id)
            if song_path:
                player.play(str(song_path))
            else:
                player.play(f"https://youtube.com/watch?v={video_id}")

        await uow.flush()

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
    audio = dialog_manager.dialog_data.get("audio")
    if audio is None:
        audio = dialog_manager.start_data.get("audio")
        dialog_manager.dialog_data["audio"] = audio

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
    day: int = dialog_manager.dialog_data["day"]
    uow: UnitOfWork = dialog_manager.middleware_data["uow"]
    ethers = await get_grouped_ethers(day, uow, dialog_manager)

    if day == 0 and await get_alert_state():
        await dialog_manager.middleware_data["bot"].send_message(
            chat_id=dialog_manager.event.from_user.id,
            text=f"Наразі лунає тривога. Замовлення на поточний етер не приймаються, однак Ви можете замовити на інші!",
        )

    if day == 0:
        current_order = await uow.orders.find_one(
            Order.played == False,
            Order.play_start != None,
            order=[Order.play_start.desc()],
        )
    else:
        current_order = None

    now = datetime.now()
    selected_date = now.date() + timedelta(days=day)
    selected_ether_idx = dialog_manager.dialog_data.get("selected_ether_idx")
    if selected_ether_idx is None:
        selected_ether_idx = 1 if now.time() > time(hour=16) else 0

    end_after = now.time() if day == 0 else None
    ethers_info, ether_buttons = await get_ethers_info(
        uow, current_order, selected_date, selected_ether_idx, end_after
    )
    if not ether_buttons:
        dialog_manager.dialog_data.pop("selected_ether_idx", None)

    return {
        "ethers": ethers,
        "ethers_info": ethers_info,
        "ether_buttons": ether_buttons,
    }


order_menu = Dialog(
    Window(
        Const(
            "Чим хочеш порадувати кампус?\n"
            "Скинь посилання на трек з Youtube Music або Spotify!\n\n"
            "Пам'ятай — під час повітряної тривоги мовлення не здійснюється."
        ),
        MessageInput(audio_input, content_types=[ContentType.AUDIO, ContentType.VOICE]),
        MessageInput(text_input, content_types=[ContentType.TEXT]),
        Start(
            text=Const("Відміна"),
            id="__main__",
            state=MainStates.main,
            mode=StartMode.RESET_STACK,
        ),
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
        Start(
            text=Const("Відміна"),
            id="__main__",
            state=MainStates.main,
            mode=StartMode.RESET_STACK,
        ),
        state=OrderStates.day,
        getter=get_data,
    ),
    Window(
        Jinja("{{ ethers_info|safe }}\n\nТепер вибери час"),
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
        disable_web_page_preview=True,
    ),
)
