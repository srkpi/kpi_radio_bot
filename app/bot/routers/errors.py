from aiogram.types import ErrorEvent


async def context_not_found(event: ErrorEvent):
    if event.update.message:
        await event.update.message.answer(
            "Лишенько, не впізнав тебе! Пропиши, будь ласка, /start"
        )
