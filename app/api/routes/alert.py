import asyncio
from datetime import datetime
from aiogram import Bot
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.settings import settings
from app.api.schemas.alert import RegionAlerts
from app.api.stubs import BotStub
from app.bot.models.ether import Ether
from app.bot.models.order import Order
from app.bot.player.mpv_player import player

from app.database import sessionmaker
from app.bot.repositories.uow import UnitOfWork


alert_router = APIRouter(prefix="/alert", tags=["Alert webhook"])
alert_state = {"is_active": False}
alert_state_lock = asyncio.Lock()


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
    )

    to_notify: list[tuple[str, int, datetime]] = []
    for order in orders:
        to_notify.append((order.title, order.ordered_by))
        order.played = True

    await uow.flush()

    for title, user_id in to_notify:
        await bot.send_message(user_id, f"Замовлення скасоване через тривогу: {title}")


async def set_alert_state(is_active: bool):
    async with alert_state_lock:
        alert_state["is_active"] = is_active


async def get_alert_state() -> bool:
    async with alert_state_lock:
        return alert_state["is_active"]


@alert_router.post("")
async def alert_route(
    update: RegionAlerts,
    bot: Bot = Depends(BotStub),
) -> JSONResponse:
    print(update)
    if update.region_id == 31:
        is_alert = await get_alert_state()

        if update.status == "Activate":
            if not is_alert:
                await set_alert_state(True)

                async with sessionmaker() as session, session.begin():
                    async with UnitOfWork(session) as uow:
                        await clear_queue_alert(uow, bot)

                player.stop()
                player.play("music/alert.mp3")

                await bot.send_message(
                    text="Повітряна тривога!",
                    chat_id=settings.ADMINS_CHAT_ID,
                    message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
                )
        elif is_alert:
            await set_alert_state(False)

            player.stop()
            player.play("music/all_clear.mp3")

            await bot.send_message(
                text="Відбій повітряної тривоги!",
                chat_id=settings.ADMINS_CHAT_ID,
                message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
            )

    return JSONResponse(status_code=200, content={"ok": True})
