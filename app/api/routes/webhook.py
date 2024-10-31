from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import SecretStr
from starlette import status
from aiogram.types import FSInputFile

from app.api.stubs import BotStub, DispatcherStub, SecretStub
from app.settings import settings

webhook_router = APIRouter(prefix="/webhook", tags=["Telegram Webhook"])


@webhook_router.get("/test")
async def test(bot: Bot = Depends(BotStub)):
    await bot.set_webhook(
            f"{settings.WEBHOOK_URL}", 
            secret_token=settings.TELEGRAM_SECRET.get_secret_value(),
            certificate=FSInputFile('certificate.pem'),
        )
    return {}


@webhook_router.post("")
async def webhook_route(
        update: Update,
        secret: SecretStr = Header(alias="X-Telegram-Bot-Api-Secret-Token"),
        expected_secret: str = Depends(SecretStub),
        bot: Bot = Depends(BotStub),
        dispatcher: Dispatcher = Depends(DispatcherStub),
) -> JSONResponse:
    if secret.get_secret_value() != expected_secret:
        raise HTTPException(detail="Invalid secret", status_code=status.HTTP_401_UNAUTHORIZED)

    await dispatcher.feed_update(bot, update=update)
    return JSONResponse(
        status_code=200,
        content={"ok": True}
    )
