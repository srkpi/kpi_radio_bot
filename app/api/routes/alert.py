from datetime import datetime, timezone
from aiogram import Bot
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.schemas.alert import RegionAlerts
from app.api.stubs import BotStub
from app.bot.models.ether import Ether
from app.bot.models.order import Order
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.alert_state import get_alert_level, set_alert_level
from app.bot.services.notifications import notify_orders_cancelled

from app.database import sessionmaker
from app.settings import settings


alert_router = APIRouter(prefix="/alert", tags=["Alert webhook"])

RED = "Red"
YELLOW = "Yellow"

SOUND_RED_START = "music/alert_red.mp3"
SOUND_YELLOW_START = "music/alert_yellow.mp3"
SOUND_RED_TO_YELLOW = "music/alert_red_to_yellow.mp3"
SOUND_YELLOW_TO_RED = "music/alert_yellow_to_red.mp3"
SOUND_ALL_CLEAR = "music/all_clear.mp3"

START_SOUND = {RED: SOUND_RED_START, YELLOW: SOUND_YELLOW_START}
CHANGE_SOUND = {
    (RED, YELLOW): SOUND_RED_TO_YELLOW,
    (YELLOW, RED): SOUND_YELLOW_TO_RED,
}

LEVEL_EMOJI = {RED: "🔴", YELLOW: "🟡"}
LEVEL_LABEL = {RED: "червоний", YELLOW: "жовтий"}


async def clear_queue_alert(uow: UnitOfWork, bot: Bot):
    today = datetime.now()

    ether = await uow.ethers.find_one(
        Ether.ether_date == today.date(),
        Ether.start_time <= today.time(),
        Ether.end_time >= today.time(),
    )

    if not ether:
        return

    orders = await uow.orders.find(
        Order.ether_id == ether.id,
        Order.played == False,
        Order.confirmed == True,
    )

    cancelled_orders = list(orders)
    for order in orders:
        order.played = True

    await uow.flush()
    await notify_orders_cancelled(bot, cancelled_orders, "повітряна тривога")


def resolve_alert_level(update: RegionAlerts) -> str:
    if update.alert_level in (RED, YELLOW):
        return update.alert_level

    if update.active_alert_levels:
        latest = max(
            update.active_alert_levels,
            key=lambda entry: entry.created_at or datetime.min.replace(tzinfo=timezone.utc),
        )
        if latest.alert_level in (RED, YELLOW):
            return latest.alert_level

    return RED


@alert_router.post("")
async def alert_route(
    update: RegionAlerts,
    bot: Bot = Depends(BotStub),
) -> JSONResponse:
    print(update)
    if update.region_id == 31:
        previous_level = await get_alert_level()

        if update.status == "Activate":
            new_level = resolve_alert_level(update)

            if new_level != previous_level:
                await set_alert_level(new_level)

                if previous_level is None:
                    async with sessionmaker() as session, session.begin():
                        async with UnitOfWork(session) as uow:
                            await clear_queue_alert(uow, bot)

                    sound = START_SOUND[new_level]
                    text = (
                        f"{LEVEL_EMOJI[new_level]} Повітряна тривога! "
                        f"Рівень: {LEVEL_LABEL[new_level]}."
                    )
                else:
                    sound = CHANGE_SOUND[(previous_level, new_level)]
                    text = (
                        f"{LEVEL_EMOJI[previous_level]}➡️{LEVEL_EMOJI[new_level]} "
                        f"Рівень тривоги змінився: {LEVEL_LABEL[previous_level]} → "
                        f"{LEVEL_LABEL[new_level]}."
                    )

                player.play(sound)
                player.set_temp_volume(100)

                await bot.send_message(
                    text=text,
                    chat_id=settings.ADMINS_CHAT_ID,
                    message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
                )
        elif previous_level is not None:
            await set_alert_level(None)

            player.play(SOUND_ALL_CLEAR)
            player.set_temp_volume(100)

            await bot.send_message(
                text="✅ Відбій повітряної тривоги!",
                chat_id=settings.ADMINS_CHAT_ID,
                message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
            )

    return JSONResponse(status_code=200, content={"ok": True})
