import redis
from aiogram.types import ErrorEvent


async def context_not_found(event: ErrorEvent):
    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    redis_client.flushdb()

    if event.update.message:
        await event.update.message.answer("Пропишіть /start")
