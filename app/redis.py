from redis.asyncio import Redis
from typing import Any


redis_connection: "Redis[Any]" = Redis(
    host="localhost", port=6379, decode_responses=True
)
