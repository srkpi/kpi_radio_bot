from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart, ExceptionTypeFilter
from aiogram_dialog.api.exceptions import UnknownIntent, OutdatedIntent

from app.bot.consts.actions import Actions
from app.bot.routers.confirm import confirm_order, decline_order
from app.bot.routers.errors import context_not_found
from app.bot.routers.help_menu import help_menu
from app.bot.routers.commands import help_command, start, skip, stop
from app.bot.routers.main_menu import main_menu
from app.bot.routers.order_menu import order_menu
from app.bot.routers.player_menu import player_menu
from app.bot.routers.schedule_menu import schedule_menu
from app.bot.schemas.confirm import ConfirmOrder
from app.settings import settings

router = Router()
router.callback_query.register(confirm_order, ConfirmOrder.filter(F.action == Actions.confirm))
router.callback_query.register(decline_order, ConfirmOrder.filter(F.action == Actions.decline))

private_router = Router()
private_router.message.filter(F.chat.type == ChatType.PRIVATE)

private_router.message.register(start, CommandStart())
private_router.message.register(help_command, Command("help"))

private_router.error.register(context_not_found, ExceptionTypeFilter(UnknownIntent))

router.message.register(skip, Command("skip"), F.chat.id == settings.ADMINS_CHAT_ID)
router.message.register(stop, Command("stop"), F.chat.id == settings.ADMINS_CHAT_ID)

private_router.include_router(main_menu)
private_router.include_router(help_menu)
private_router.include_router(order_menu)
private_router.include_router(schedule_menu)
private_router.include_router(player_menu)

router.include_router(private_router)

router.error.register(context_not_found, ExceptionTypeFilter(UnknownIntent))
router.error.register(context_not_found, ExceptionTypeFilter(OutdatedIntent))
