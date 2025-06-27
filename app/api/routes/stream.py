from aiohttp import ClientSession, ClientTimeout
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import Request, APIRouter
from app.bot.player.streamer import ffmpeg_streamer

import asyncio
import logging

MAX_STREAM_RETRIES = 5

logger = logging.getLogger(__name__)
stream_router = APIRouter(prefix="/stream", tags=["Stream webhook"])


@stream_router.get("")
async def proxy_icecast_stream(request: Request):
    icecast_url = "http://localhost:8001/stream"
    headers = {"User-Agent": "FastAPI-Proxy"}

    try:
        async with ClientSession(timeout=ClientTimeout(total=None)) as session:
            resp = await session.get(icecast_url, headers=headers)
            if resp.status != 200:
                await ffmpeg_streamer.start()
                await asyncio.sleep(3)

                resp = await session.get(icecast_url, headers=headers)
                if resp.status != 200:
                    return JSONResponse(
                        status_code=resp.status,
                        content={"error": "Failed to connect to Icecast"},
                    )

            async def stream_generator():
                retries = 0
                try:
                    while True:
                        try:
                            chunk = await asyncio.wait_for(
                                resp.content.readany(), timeout=15
                            )
                            if not chunk:
                                logger.info("No more data from Icecast, ending stream.")
                                break
                            yield chunk
                            retries = 0
                        except asyncio.TimeoutError:
                            retries += 1
                            logger.warning(
                                f"Timeout while reading stream. Retry {retries}/{MAX_STREAM_RETRIES}"
                            )
                            if retries >= MAX_STREAM_RETRIES:
                                logger.error("Max retries reached. Ending stream.")
                                break
                            await asyncio.sleep(1)
                except Exception as e:
                    logger.exception(f"Unhandled error in stream: {e}")
                finally:
                    await resp.release()

            return StreamingResponse(stream_generator(), media_type="application/ogg")

    except Exception as e:
        logger.exception(f"Failed to establish connection to Icecast: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Stream connection error"}
        )
