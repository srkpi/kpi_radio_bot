import asyncio
import logging

import aiohttp
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import Request, APIRouter
from app.bot.player.streamer import ffmpeg_streamer

ICECAST_URL = "http://localhost:8001/stream"
HEADERS = {"User-Agent": "FastAPI-Proxy"}

logger = logging.getLogger(__name__)
stream_router = APIRouter(prefix="/stream", tags=["Stream webhook"])


@stream_router.get("")
async def proxy_icecast_stream(request: Request):
    session = aiohttp.ClientSession()
    resp = await session.get(ICECAST_URL, headers=HEADERS)

    try:
        if resp.status != 200:
            await ffmpeg_streamer.start()
            await asyncio.sleep(5)

            resp = await session.get(ICECAST_URL, headers=HEADERS)

            if resp.status != 200:
                await session.close()

                return JSONResponse(
                    status_code=resp.status,
                    content={"error": "Failed to connect to Icecast"},
                )

        async def stream_generator():
            try:
                async for chunk in resp.content.iter_any():
                    yield chunk
            finally:
                await resp.release()
                await session.close()

        return StreamingResponse(stream_generator(), media_type="application/ogg")
    except:
        await session.close()
