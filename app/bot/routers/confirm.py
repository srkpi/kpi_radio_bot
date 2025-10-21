import html
import re
import asyncio
from datetime import datetime, timedelta

from aiogram.types import CallbackQuery
from sqlalchemy.orm import selectinload

from app.bot.consts.other import AVERAGE_SONG_SWITCH_DELAY
from app.bot.models import Order
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork
from app.bot.schemas.confirm import ConfirmOrder
from app.bot.services.song_downloader import add_to_download_queue, get_song_path
from app.bot.states.alert_state import get_alert_state

order_count_pattern = r"\((\d+)/(\d+)\)$"
order_locks: dict[int, asyncio.Lock] = {}


async def change_callback_message_text(callback: CallbackQuery, text: str) -> None:
    if callback.message.caption:
        await callback.message.edit_caption(caption=text)
        return

    await callback.message.edit_text(text)


def increment_approved(match: re.Match[str]) -> str:
    first = int(match.group(1))
    second = match.group(2)

    return f"({first + 1}/{second})"


async def confirm_order(
    callback: CallbackQuery, callback_data: ConfirmOrder, uow: UnitOfWork
) -> None:
    order_id = callback_data.order_id

    if order_id not in order_locks:
        order_locks[order_id] = asyncio.Lock()

    async with order_locks[order_id]:
        try:
            order = await uow.orders.find_one(
                Order.id == order_id, options=[selectinload(Order.ether)]
            )

            if order is None:
                text = callback.message.html_text + "\nОрдер не знайдено"
                await change_callback_message_text(callback, text)
                return

            if order.decision_timestamp:
                return

            if order.played:
                text = (
                    callback.message.html_text
                    + "\nОрдер було скасовано (через тривогу, стоп, очистку черги або ще щось)"
                )
                await change_callback_message_text(callback, text)
                return

            order_ether = order.ether

            if order_ether.cancelled:
                text = callback.message.html_text + "\nЕтер більше недоступний"
                await change_callback_message_text(callback, text)
                return

            current_datetime = datetime.now()

            if order_ether.ether_date == current_datetime.date():
                current_time = current_datetime.time()
                if order_ether.end_time < current_time:
                    text = callback.message.html_text + "\nЕтер вже закінчився"
                    await change_callback_message_text(callback, text)
                    return

                song_end_time = (
                    current_datetime + timedelta(seconds=order.duration)
                ).time()
                if order_ether.end_time < song_end_time:
                    text = (
                        callback.message.html_text
                        + f"\nПісня не встигне програти до закінчення етеру\n@Maximax67, 1, ft: {song_end_time.strftime('%H:%M:%S')}"
                    )
                    await change_callback_message_text(callback, text)
                    return

                if order.ether.start_time < current_time and await get_alert_state():
                    text = (
                        callback.message.html_text
                        + "\nНаразі триває повітряна тривога!"
                    )
                    await change_callback_message_text(callback, text)
                    await callback.bot.send_message(
                        callback_data.user_id,
                        f"🚫 Твоє замовлення не зможе програти через тривогу: {order.title}",
                    )
                    return

            text = (
                re.sub(
                    order_count_pattern, increment_approved, callback.message.html_text
                )
                + f"\n✅ Прийнято ({callback.from_user.mention_html()} {current_datetime.strftime('%H:%M:%S')})"
            )
            order.confirmed = True
            order.decision_timestamp = current_datetime
            order.decided_by = callback.from_user.id

            video_id = order.video_id
            download_song = True

            order_title = html.escape(order.title)

            if (
                order_ether.ether_date == current_datetime.date()
                and current_datetime.time() > order_ether.start_time
            ):
                current_playing: Order = await uow.orders.find_one(
                    Order.ether_id == order.ether_id,
                    Order.played == False,
                    Order.confirmed == True,
                    Order.play_start != None,
                    order=[Order.play_start.desc()],
                )

                ether_not_played_orders: list[Order] = await uow.orders.find(
                    Order.ether_id == order.ether_id,
                    Order.played == False,
                    Order.confirmed == True,
                )

                if current_playing or len(ether_not_played_orders):
                    ether_not_played_orders_len = len(ether_not_played_orders)
                    total_duration = sum(o.duration for o in ether_not_played_orders)

                    if current_playing:
                        minus_playing = max(
                            round(
                                (
                                    current_datetime - current_playing.play_start
                                ).total_seconds()
                            ),
                            0,
                        )
                        total_duration -= minus_playing

                    play_delay = AVERAGE_SONG_SWITCH_DELAY * (
                        ether_not_played_orders_len - 1
                    )
                    play_time = datetime.now() + timedelta(
                        seconds=total_duration + play_delay
                    )

                    order_finish_time = (
                        play_time + timedelta(seconds=order.duration)
                    ).time()

                    play_time_str = play_time.strftime("%H:%M")

                    if order_finish_time > order.ether.end_time:
                        text = (
                            callback.message.html_text
                            + f"\nПісня не встигне програти до закінчення етеру\n@Maximax67, 2, ft: {order_finish_time.strftime('%H:%M:%S')}, td: {total_duration}, pd: {play_delay}, eo: {len(ether_not_played_orders)}, cp: {bool(current_playing)}, mp: {minus_playing}"
                        )
                        await change_callback_message_text(callback, text)
                        return

                    order.expected_play_time = play_time

                    await callback.bot.send_message(
                        callback_data.user_id,
                        f"✅ Твоє замовлення прийнято: {order_title}\n"
                        f"🕓 Орієнтовно програє: сьогодні {play_time_str}",
                    )
                else:
                    play_time = datetime.now()
                    order.expected_play_time = play_time
                    order.play_start = play_time

                    download_song = False
                    song_path = get_song_path(video_id)
                    if song_path:
                        player.play(str(song_path))
                    else:
                        player.play(f"https://youtube.com/watch?v={video_id}")

                    play_time_str = play_time.strftime("%H:%M")

                    await callback.bot.send_message(
                        callback_data.user_id,
                        f"✅ Твоє замовлення прийнято: {order_title}\n"
                        f"🕓 Орієнтовно програє: зараз",
                    )
            else:
                ether_orders = await uow.orders.find(
                    Order.ether_id == order.ether_id,
                    Order.played == False,
                    Order.confirmed == True,
                )

                total_duration = sum(
                    o.duration for o in ether_orders if o.id != order.id
                )

                play_delay = AVERAGE_SONG_SWITCH_DELAY * (len(ether_orders) - 1)
                play_time = datetime.combine(
                    order_ether.ether_date, order_ether.start_time
                ) + timedelta(seconds=total_duration + play_delay)

                order_finish_time = (
                    play_time + timedelta(seconds=order.duration)
                ).time()

                play_time_str = play_time.strftime("%H:%M")

                if order_finish_time > order.ether.end_time:
                    text = (
                        callback.message.html_text
                        + f"\nПісня не встигне програти до закінчення етеру\n@Maximax67, 3, ft: {order_finish_time.strftime('%H:%M:%S')}, td: {total_duration}, pd: {play_delay}, eo: {len(ether_orders)}"
                    )
                    await change_callback_message_text(callback, text)
                    return

                order.expected_play_time = play_time

                ether_date = order_ether.ether_date

                if ether_date == current_datetime.date():
                    play_date_str = "сьогодні"
                elif ether_date == (current_datetime + timedelta(days=1)).date():
                    play_date_str = "завтра"
                elif ether_date == (current_datetime + timedelta(days=2)).date():
                    play_date_str = "післязавтра"
                else:
                    play_date_str = order_ether.ether_date.strftime("%d.%m")

                await callback.bot.send_message(
                    callback_data.user_id,
                    f"✅ Твоє замовлення прийнято: {order_title}\n"
                    f"🕓 Орієнтовно програє: {play_date_str} {play_time_str}",
                )

            await uow.flush()

            if video_id and download_song:
                await add_to_download_queue(video_id)
        finally:
            order_locks.pop(order_id, None)

    replaced_time_text = re.sub(r"(🕓)\s(\d{2}:\d{2})", f"\\1 {play_time_str}", text)

    await change_callback_message_text(callback, replaced_time_text)


async def decline_order(
    callback: CallbackQuery, callback_data: ConfirmOrder, uow: UnitOfWork
) -> None:
    order_id = callback_data.order_id

    if order_id not in order_locks:
        order_locks[order_id] = asyncio.Lock()

    async with order_locks[order_id]:
        try:
            order = await uow.orders.find_one(Order.id == order_id)
            if order is None:
                text = callback.message.html_text + "\nОрдер не знайдено"
                await change_callback_message_text(callback, text)
                return

            if order.decision_timestamp:
                return

            current_datetime = datetime.now()
            text = (
                callback.message.html_text
                + f"\n❌ Відхилено ({callback.from_user.mention_html()} {current_datetime.strftime('%H:%M:%S')})"
            )
            order.confirmed = False
            order.decision_timestamp = current_datetime
            order.decided_by = callback.from_user.id

            await uow.flush()
        finally:
            order_locks.pop(order_id, None)

    await callback.bot.send_message(
        callback_data.user_id, f"❌ Твоє замовлення відхилено: {order.title}"
    )

    await change_callback_message_text(callback, text)
