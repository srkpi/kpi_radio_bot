from fastapi import APIRouter
from fastapi.responses import JSONResponse

index_router = APIRouter(prefix="", tags=["Index"])


@index_router.post("/")
async def webhook_route() -> JSONResponse:
    return JSONResponse(status_code=200, content={"ok": True})
