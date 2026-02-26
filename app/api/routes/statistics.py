from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.bot.services.statistics import statistics

statistics_router = APIRouter(prefix="/statistics", tags=["Statistics"])


@statistics_router.get("")
async def webhook_route() -> JSONResponse:
    if statistics:
        return JSONResponse(status_code=200, content=statistics)

    return JSONResponse(status_code=404, content={"error": "No statistics available"})
