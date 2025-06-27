import aiohttp
import ngrok
import requests

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommandScopeAllPrivateChats, BotCommandScopeChat
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import AnyUrl

from app.api.routes.alert import alert_router
from app.api.routes.index import index_router
from app.api.routes.stream import stream_router
from app.api.routes.webhook import webhook_router
from app.api.exception_handler import exception_handler
from app.api.stubs import BotStub, DispatcherStub, SecretStub
from app.bot.consts.commands import ADMIN_COMMANDS, USER_COMMANDS
from app.settings import settings


async def update_admins(bot: Bot) -> None:
    admins_ids: list[int] = []
    admins = await bot.get_chat_administrators(chat_id=settings.ADMINS_CHAT_ID)

    for admin in admins:
        admins_ids.append(admin.user.id)

    settings.ADMINS = admins_ids


async def upate_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        commands=USER_COMMANDS, scope=BotCommandScopeAllPrivateChats()
    )
    await bot.set_my_commands(
        commands=ADMIN_COMMANDS,
        scope=BotCommandScopeChat(chat_id=settings.ADMINS_CHAT_ID),
    )


def update_monitor_url() -> None:
    url = f"https://uptime.betterstack.com/api/v2/monitors/{settings.UPTIME_MONITOR_ID.get_secret_value()}"
    headers = {
        "Authorization": f"Bearer {settings.UPTIME_API_TOKEN.get_secret_value()}",
        "Content_Type": "application/json",
    }
    payload = {"url": str(settings.BASE_URL)}

    requests.request("PATCH", url, headers=headers, json=payload)


def create_app(bot: Bot, dispatcher: Dispatcher, webhook_secret: str) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ngrok.set_auth_token(settings.NGROK_AUTHTOKEN.get_secret_value())
        tunnel = await ngrok.connect(8000)
        settings.BASE_URL = AnyUrl(tunnel.url())
        await dispatcher.emit_startup(**workflow_data)

        alarm_token = settings.UKRAINEALARM_TOKEN.get_secret_value()
        if alarm_token:
            async with aiohttp.ClientSession(
                headers={
                    "Authorization": settings.UKRAINEALARM_TOKEN.get_secret_value()
                }
            ) as session:
                await session.post(
                    "https://api.ukrainealarm.com/api/v3/webhook",
                    json={"webHookUrl": f"{settings.BASE_URL}alert"},
                )

        await update_admins(bot)
        await upate_commands(bot)
        update_monitor_url()

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

    app.include_router(index_router)
    app.include_router(webhook_router)
    app.include_router(alert_router)
    app.include_router(stream_router)

    workflow_data = {
        "app": app,
        "dispatcher": dispatcher,
        "bot": bot,
        **dispatcher.workflow_data,
    }

    return app
