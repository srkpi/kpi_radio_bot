import asyncio


alert_state = {"is_active": False}
alert_state_lock = asyncio.Lock()


async def set_alert_state(is_active: bool):
    async with alert_state_lock:
        alert_state["is_active"] = is_active


async def get_alert_state() -> bool:
    async with alert_state_lock:
        return alert_state["is_active"]
