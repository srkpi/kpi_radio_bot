import asyncio
import logging

from aiohttp import ClientSession, ClientTimeout
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi import Request, APIRouter
from app.bot.player.streamer import ffmpeg_streamer

MAX_STREAM_RETRIES = 5
ICECAST_URL = "http://localhost:8001/stream"
HEADERS = {"User-Agent": "FastAPI-Proxy"}

logger = logging.getLogger(__name__)
stream_router = APIRouter(prefix="/stream", tags=["Stream webhook"])


@stream_router.get("")
async def proxy_icecast_stream(request: Request):
    try:
        async with ClientSession(timeout=ClientTimeout(total=None)) as session:
            resp = await session.get(ICECAST_URL, headers=HEADERS)
            if resp.status != 200:
                await ffmpeg_streamer.start()
                await asyncio.sleep(3)

                resp = await session.get(ICECAST_URL, headers=HEADERS)
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
                            async for chunk in resp.content.iter_any():
                                yield chunk
                                retries = 0
                        except Exception:
                            retries += 1
                            logger.warning(
                                f"Exception while reading stream. Retry {retries}/{MAX_STREAM_RETRIES}"
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
