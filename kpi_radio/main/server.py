from itertools import islice
from pathlib import Path

from aiohttp import web

from kpi_radio.music import search_text

ROUTES = web.RouteTableDef()


@ROUTES.get("/gettext/{name}")
async def gettext(request):
    if not (name := request.match_info.get('name')):
        return web.Response(text="Использование: /gettext/имя_песни")
    if not (res := await search_text(name)):
        return web.Response(text="Ошибка поиска")
    title, text = res
    return web.Response(text=f"{title} \n\n{text}")


@ROUTES.get("/history")
async def history_get(request):
    from kpi_radio.player import Broadcast
    history = await Broadcast.player.get_history()
    history = [
        {
            'performer': item.performer,
            'title': item.title,
            'start_time': str(item.start_time)
        }
        for item in islice(history, 5)
    ]
    return web.json_response(history)


@ROUTES.post("/alert")
async def history_get(request):
    from kpi_radio.player import Broadcast, PlaylistItem
    data = await request.json()
    active_alerts = data.get("activeAlerts", [])

    if any(item.get("regionId", -1) == 31 for item in active_alerts):
        Broadcast.player.add_track(PlaylistItem.from_path(Path('alert.mp3')), at_position=0)

    return web.json_response({"status": "ok"})
