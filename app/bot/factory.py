from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage, RedisEventIsolation
from aiogram_dialog import setup_dialogs

from app.bot.middlewares.database import DatabaseMiddleware
from app.bot.models import Base
from app.bot.player.mpv_player import player, get_current_track
from app.bot.routers import router
from app.bot.scheduler import Scheduler
from app.database import sessionmaker, engine
from app.redis import redis_connection
from app.settings import settings


async def start_current_ether():
    track = await get_current_track(sessionmaker)
    if track:
        player.play(track)


async def on_startup(bot: Bot) -> None:
    scheduler = Scheduler(bot, sessionmaker)
    scheduler.start()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if (await bot.get_webhook_info()).url != settings.WEBHOOK_URL:
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(f"{settings.WEBHOOK_URL}", secret_token=settings.TELEGRAM_SECRET.get_secret_value())
    await start_current_ether()


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()


def create_dispatcher() -> Dispatcher:
    key_builder = DefaultKeyBuilder(with_destiny=True)
    storage = RedisStorage(redis_connection, key_builder)
    events_isolation = RedisEventIsolation(redis_connection, key_builder)

    dispatcher = Dispatcher(
        storage=storage,
        events_isolation=events_isolation
    )

    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)
    dispatcher.update.middleware(DatabaseMiddleware(sessionmaker))
    setup_dialogs(dispatcher)

    dispatcher.include_router(router)

    return dispatcher


def create_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ))
