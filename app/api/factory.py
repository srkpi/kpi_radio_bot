from contextlib import asynccontextmanager

import aiohttp
from fastapi.responses import JSONResponse
import ngrok
from aiogram import Bot, Dispatcher
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AnyUrl

from app.api.routes.alert import alert_router
from app.api.routes.webhook import webhook_router
from app.api.exception_handler import exception_handler
from app.api.stubs import BotStub, DispatcherStub, SecretStub
from app.settings import settings


def create_app(bot: Bot, dispatcher: Dispatcher, webhook_secret: str) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ngrok.set_auth_token(settings.NGROK_AUTHTOKEN.get_secret_value())
        tunnel = await ngrok.connect(8000)
        settings.BASE_URL = AnyUrl(tunnel.url())
        await dispatcher.emit_startup(**workflow_data)

        alarm_token = settings.UKRAINEALARM_TOKEN.get_secret_value()
        if alarm_token:
            async with aiohttp.ClientSession(headers={"Authorization": settings.UKRAINEALARM_TOKEN.get_secret_value()}) as session:
                await session.post("https://api.ukrainealarm.com/api/v3/webhook", json={"webHookUrl": f"{settings.BASE_URL}alert"})

        yield
        await dispatcher.emit_shutdown(**workflow_data)
        ngrok.disconnect()

    app = FastAPI(lifespan=lifespan)

    app.dependency_overrides.update(
        {
            BotStub: lambda: bot,
            DispatcherStub: lambda: dispatcher,
            SecretStub: lambda: webhook_secret,
        }
    )

    async def async_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return await exception_handler(request, exc, bot)

    app.add_exception_handler(Exception, async_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(webhook_router)
    app.include_router(alert_router)

    workflow_data = {
        "app": app,
        "dispatcher": dispatcher,
        "bot": bot,
        **dispatcher.workflow_data,
    }

    return app
