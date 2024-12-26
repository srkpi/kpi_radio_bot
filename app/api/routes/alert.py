from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas.alert import RegionAlerts
from app.bot.player.mpv_player import player

from sqlalchemy.orm import selectinload


alert_router = APIRouter(prefix="/alert", tags=["Alert webhook"])


@alert_router.post("")
async def alert_route(
    update: RegionAlerts
) -> JSONResponse:
    print(update)
    if update.region_id == 31:
        if update.status == 'Activate':
            player.stop()
            player.play("music/alert.mp3")
        else:
            player.stop()
            player.play("music/all_clear.mp3")

    return JSONResponse(
        status_code=200,
        content={"ok": True}
    )
