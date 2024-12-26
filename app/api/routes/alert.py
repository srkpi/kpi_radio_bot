from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas.alert import RegionAlerts
from app.bot.models.ether import Ether
from app.bot.player.mpv_player import player
from app.bot.repositories.uow import UnitOfWork

from sqlalchemy.orm import selectinload


alert_router = APIRouter(prefix="/alert", tags=["Alert webhook"])


@alert_router.post("")
async def alert_route(update: RegionAlerts, uow: UnitOfWork) -> JSONResponse:
    print(update)
    if update.region_id == 31:
        if update.status == 'Activate':
            today = datetime.now()
            ether = await uow.ethers.find_one(Ether.date == today.date(), Ether.start_time <= today.time(), Ether.end_time >= today.time(), options=[selectinload(Ether.orders)])
            for order in ether.orders:
                order.played = True

            await uow.flush()

            player.stop()
            player.play("music/alert.mp3")
        else:
            player.stop()
            player.play("music/all_clear.mp3")

    return JSONResponse(
        status_code=200,
        content={"ok": True}
    )
