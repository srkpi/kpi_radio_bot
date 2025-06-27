import aiohttp
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

stream_router = APIRouter(prefix="/stream", tags=["Stream webhook"])

@stream_router.get("")
async def proxy_icecast_stream(request: Request):
    icecast_url = "http://localhost:8001/stream"
    headers = {"User-Agent": "FastAPI-Proxy"}

    session = aiohttp.ClientSession()
    resp = await session.get(icecast_url, headers=headers)

    if resp.status != 200:
        await session.close()
        return JSONResponse(
            status_code=resp.status, content={"error": "Failed to connect to Icecast"}
        )

    async def stream_generator():
        try:
            async for chunk in resp.content.iter_chunked(32768):
                yield chunk
        finally:
            await resp.release()
            await session.close()

    return StreamingResponse(stream_generator(), media_type="application/ogg")
