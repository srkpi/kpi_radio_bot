import asyncio
from typing import Optional


alert_state: dict[str, Optional[str]] = {"level": None}
alert_state_lock = asyncio.Lock()


async def set_alert_level(level: Optional[str]) -> None:
    async with alert_state_lock:
        alert_state["level"] = level


async def get_alert_level() -> Optional[str]:
    async with alert_state_lock:
        return alert_state["level"]


async def set_alert_state(is_active: bool) -> None:
    await set_alert_level("Red" if is_active else None)


async def get_alert_state() -> bool:
    return await get_alert_level() is not None
