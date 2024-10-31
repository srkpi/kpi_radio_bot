from contextlib import asynccontextmanager
import logging

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import InputFile, BufferedInputFile, FSInputFile
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AnyUrl

from app.api.routes.alert import alert_router
from app.api.routes.webhook import webhook_router
from app.api.stubs import BotStub, DispatcherStub, SecretStub
from app.settings import settings


def create_app(bot: Bot, dispatcher: Dispatcher, webhook_secret: str) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await dispatcher.emit_startup(**workflow_data)
        async with aiohttp.ClientSession(headers={"Authorization": settings.UKRAINEALARM_TOKEN.get_secret_value()}) as session:
            r = await session.post("https://api.ukrainealarm.com/api/v3/webhook", json={"webHookUrl": f"{settings.BASE_URL}alert"})
            print(r.text)
        yield
        await dispatcher.emit_shutdown(**workflow_data)

    app = FastAPI(lifespan=lifespan)

    app.dependency_overrides.update(
        {
            BotStub: lambda: bot,
            DispatcherStub: lambda: dispatcher,
            SecretStub: lambda: webhook_secret,
        }
    )

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
