import asyncio
from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas.alert import RegionAlerts
from app.bot.models.ether import Ether
from app.bot.models.order import Order
from app.bot.player.mpv_player import player

from app.database import sessionmaker
from app.bot.repositories.uow import UnitOfWork


alert_router = APIRouter(prefix="/alert", tags=["Alert webhook"])


async def clear_queue_for_ether(async_session):
    today = datetime.now()
    async with async_session() as session, session.begin():
        async with UnitOfWork(session) as uow:
            ether = await uow.ethers.find_one(
                Ether.date == today.date(),
                Ether.start_time <= today.time(),
                Ether.end_time >= today.time(),
            )

            if not ether:
                return

            orders = await uow.orders.find(
                Order.ether_id == ether.id,
                Order.played == False,
            )

            for order in orders:
                order.played = True


@alert_router.post("")
async def alert_route(
    update: RegionAlerts
) -> JSONResponse:
    print(update)
    if update.region_id == 31:
        if update.status == 'Activate':
            loop = asyncio.new_event_loop()
            loop.run_until_complete(clear_queue_for_ether(sessionmaker))

            player.stop()
            player.play("music/alert.mp3")
        else:
            player.stop()
            player.play("music/all_clear.mp3")

    return JSONResponse(
        status_code=200,
        content={"ok": True}
    )
