from fastapi import Request, Response
from fastapi.responses import JSONResponse
from aiogram import Bot
import traceback

from app.settings import settings


async def exception_handler(request: Request, exc: Exception, bot: Bot) -> JSONResponse:
    if str(exc) == "Telegram server says - Bad Request: MESSAGE_ID_INVALID":
        return Response(status_code=200)

    tb = traceback.extract_tb(exc.__traceback__)
    filtered_tb = [line for line in tb if "app" in line.filename]
    formatted_tb = "".join(traceback.format_list(filtered_tb))

    try:
        await bot.send_message(
            chat_id=settings.ADMINS_CHAT_ID,
            message_thread_id=settings.ADMINS_BUGS_THREAD_ID,
            text=f"🚨 <b>Error Alert</b> 🚨\n\n{exc}\n\n<pre>Short Traceback:\n{formatted_tb if formatted_tb else 'Exception is somewhere in python modules. Please check detailed logs!'}</pre>",
            parse_mode="HTML",
        )
    except Exception as bot_error:
        print("Failed to send error message to Telegram:", bot_error)

    return Response(status_code=200)
