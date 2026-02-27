from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.bot.services.statistics import get_statistics

statistics_router = APIRouter(prefix="/statistics", tags=["Statistics"])


@statistics_router.get("")
async def get_statistics_route() -> JSONResponse:
    statistics = get_statistics()
    if statistics:
        return JSONResponse(status_code=200, content=statistics)

    return JSONResponse(status_code=404, content={"error": "No statistics available"})
