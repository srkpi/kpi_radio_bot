import logging

import aiohttp
from aiogram import Dispatcher
from aiogram.dispatcher.webhook import WebhookRequestHandler, DEFAULT_WEB_PATH, DEFAULT_ROUTE_NAME, BOT_DISPATCHER_KEY
from aiogram.utils import executor
from aiohttp import web

from kpi_radio.bot.bot_utils import bind_filters
from kpi_radio.consts.config import BOT
from .handlers import register_handlers

DP = Dispatcher(BOT)
bind_filters(DP)
register_handlers(DP)


async def set_webhook(url):
    if (await BOT.get_webhook_info()).url != url:
        await BOT.set_webhook(url)


async def set_alert_webhook(url, api_key):
    headers = {"Authorization": api_key}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(
            "https://api.ukrainealarm.com/api/v3/webhook",
            json={
                "webHookUrl": url
            }
        ) as response:
            logging.info(await response.json())


def start_longpoll(**kwargs):
    executor.start_polling(DP, skip_updates=True, **kwargs)


# ignore errors
class MyHandler(WebhookRequestHandler):
    async def process_update(self, update):
        try:
            return await super().process_update(update)
        except:
            logging.exception("WEBHOOK Exception")


def get_aiohttp_app():
    app = web.Application()
    app.router.add_route('*', DEFAULT_WEB_PATH, MyHandler, name=DEFAULT_ROUTE_NAME)
    app[BOT_DISPATCHER_KEY] = DP
    return app
