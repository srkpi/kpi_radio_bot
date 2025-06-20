from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart, ExceptionTypeFilter
from aiogram_dialog.api.exceptions import UnknownIntent, OutdatedIntent

from app.bot.banned_user_exception import BannedUserException
from app.bot.consts.actions import Actions
from app.bot.routers.confirm import confirm_order, decline_order
from app.bot.routers.errors import context_not_found, user_is_banned
from app.bot.routers.feedback_menu import feedback_menu
from app.bot.routers.help_menu import help_menu
from app.bot.routers.commands import (
    alert,
    ban,
    ban_list,
    cancel,
    help_command,
    restart,
    send_database,
    send_orders,
    set_temp_volume,
    set_volume,
    start,
    skip,
    stop,
    holiday,
    close,
    open,
    stop_alert,
    stop_all,
    stop_today,
    traktor,
    unban,
    unholiday,
    force_play,
)
from app.bot.routers.main_menu import main_menu
from app.bot.routers.order_menu import order_menu
from app.bot.routers.player_menu import player_menu
from app.bot.routers.schedule_menu import schedule_menu
from app.bot.schemas.confirm import ConfirmOrder
from app.bot.services.feedback import (
    admin_feedback_reply_handler,
    send_reply,
    user_feedback_reply_handler,
)
from app.settings import settings

router = Router()
router.callback_query.register(
    confirm_order, ConfirmOrder.filter(F.action == Actions.confirm)
)
router.callback_query.register(
    decline_order, ConfirmOrder.filter(F.action == Actions.decline)
)

private_router = Router()
private_router.message.filter(F.chat.type == ChatType.PRIVATE)

private_router.message.register(start, CommandStart())
private_router.message.register(help_command, Command("help"))
private_router.message.register(traktor, Command("traktor"))
private_router.message.register(user_feedback_reply_handler, F.reply_to_message)

private_router.error.register(context_not_found, ExceptionTypeFilter(UnknownIntent))

router.message.register(skip, Command("skip"), F.chat.id == settings.ADMINS_CHAT_ID)
router.message.register(cancel, Command("cancel"), F.chat.id == settings.ADMINS_CHAT_ID)
router.message.register(stop, Command("stop"), F.chat.id == settings.ADMINS_CHAT_ID)
router.message.register(
    stop_today, Command("stop_today"), F.chat.id == settings.ADMINS_CHAT_ID
)
router.message.register(
    stop_all, Command("stop_all"), F.chat.id == settings.ADMINS_CHAT_ID
)
router.message.register(
    holiday, Command("holiday"), F.chat.id == settings.ADMINS_CHAT_ID
)
router.message.register(
    unholiday, Command("unholiday"), F.chat.id == settings.ADMINS_CHAT_ID
)

router.message.register(close, Command("close"), F.chat.id == settings.ADMINS_CHAT_ID)
router.message.register(open, Command("open"), F.chat.id == settings.ADMINS_CHAT_ID)

router.message.register(
    set_volume, Command("volume"), F.chat.id == settings.ADMINS_CHAT_ID
)
router.message.register(
    set_temp_volume, Command("temp_volume"), F.chat.id == settings.ADMINS_CHAT_ID
)

router.message.register(alert, Command("alert"), F.chat.id == settings.ADMINS_CHAT_ID)
router.message.register(
    stop_alert, Command("stop_alert"), F.chat.id == settings.ADMINS_CHAT_ID
)

router.message.register(
    send_reply,
    Command("reply"),
    F.chat.id == settings.ADMINS_CHAT_ID,
    F.message_thread_id == settings.ADMINS_MODERATION_THREAD_ID,
    F.text,
)
router.message.register(
    ban,
    Command("ban"),
    F.chat.id == settings.ADMINS_CHAT_ID,
    F.text,
)
router.message.register(
    unban,
    Command("unban"),
    F.chat.id == settings.ADMINS_CHAT_ID,
)
router.message.register(
    ban_list,
    Command("ban_list"),
    F.chat.id == settings.ADMINS_CHAT_ID,
)
router.message.register(
    send_orders,
    Command("send_orders"),
    F.chat.id == settings.ADMINS_CHAT_ID,
)
router.message.register(
    send_database,
    Command("send_database"),
    F.chat.id == settings.ADMINS_CHAT_ID,
)
router.message.register(
    traktor,
    Command("traktor"),
    F.chat.id == settings.ADMINS_CHAT_ID,
)
router.message.register(
    restart,
    Command("restart"),
    F.chat.id == settings.ADMINS_CHAT_ID,
)
router.message.register(
    force_play,
    Command("force_play"),
    F.chat.id == settings.ADMINS_CHAT_ID,
)
router.message.register(
    admin_feedback_reply_handler,
    F.chat.id == settings.ADMINS_CHAT_ID,
    F.reply_to_message,
)

private_router.include_router(main_menu)
private_router.include_router(help_menu)
private_router.include_router(order_menu)
private_router.include_router(schedule_menu)
private_router.include_router(player_menu)
private_router.include_router(feedback_menu)

router.include_router(private_router)

router.error.register(context_not_found, ExceptionTypeFilter(UnknownIntent))
router.error.register(context_not_found, ExceptionTypeFilter(OutdatedIntent))
router.error.register(user_is_banned, ExceptionTypeFilter(BannedUserException))
