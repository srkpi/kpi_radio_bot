from datetime import datetime
from aiogram import Bot
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.schemas.alert import RegionAlerts
from app.api.stubs import BotStub
from app.bot.models.ether import Ether
from app.bot.models.order import Order
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork
from app.bot.states.alert_state import get_alert_state, set_alert_state
from app.bot.services.notifications import notify_orders_cancelled

from app.database import sessionmaker
from app.settings import settings


alert_router = APIRouter(prefix="/alert", tags=["Alert webhook"])


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

                player.play("music/alert.mp3")
                player.set_temp_volume(100)

                await bot.send_message(
                    text="Повітряна тривога!",
                    chat_id=settings.ADMINS_CHAT_ID,
                    message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
                )
        elif is_alert:
            await set_alert_state(False)

            player.play("music/all_clear.mp3")
            player.set_temp_volume(100)

            await bot.send_message(
                text="Відбій повітряної тривоги!",
                chat_id=settings.ADMINS_CHAT_ID,
                message_thread_id=settings.ADMINS_MODERATION_THREAD_ID,
            )

    return JSONResponse(status_code=200, content={"ok": True})
