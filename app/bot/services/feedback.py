from typing import List, Optional
from aiogram import Bot
from aiogram.types import (
    Message,
    MessageEntity,
    User,
    ReactionTypeEmoji,
    UNSET_PARSE_MODE,
)
from aiogram.exceptions import TelegramBadRequest

from app.bot.models.order import Order
from app.bot.repositories.uow import UnitOfWork
from app.redis import redis_connection
from app.settings import settings


async def store_message_mapping(
    user_id: int,
    user_message_id: int,
    admin_message_id: int,
    info_message_id: Optional[int] = None,
    is_info_message_admin: Optional[bool] = None,
):
    if (info_message_id is not None) != (is_info_message_admin is not None):
        raise ValueError(
            "Both info_message_id and is_info_message_admin must be set together."
        )

    mapping = {
        f"fb:u:{user_id}:{user_message_id}": admin_message_id,
        f"fb:a:{admin_message_id}": f"{user_id}:{user_message_id}",
    }

    if info_message_id:
        if is_info_message_admin:
            mapping[f"fb:a:{info_message_id}"] = f"{user_id}:{user_message_id}"
        else:
            mapping[f"fb:u:{user_id}:{info_message_id}"] = admin_message_id

    await redis_connection.mset(mapping)


async def get_user_message_id(admin_message_id: int):
    data = await redis_connection.get(f"fb:a:{admin_message_id}")
    if data:
        user_id, user_message_id = map(int, data.split(":"))
        return user_id, user_message_id

    return None, None


async def get_admin_message_id(user_id: int, user_message_id: int):
    admin_message_id = await redis_connection.get(f"fb:u:{user_id}:{user_message_id}")
    return int(admin_message_id) if admin_message_id else None


async def send_message_with_reply(
    chat_id: int,
    reply_message_id: int,
    message_text: str,
    bot: Bot,
    thread: Optional[int] = None,
    entities: Optional[List[MessageEntity]] = None,
    parse_mode: str | None = UNSET_PARSE_MODE,
):
    try:
        return await bot.send_message(
            chat_id,
            message_text,
            message_thread_id=thread,
            protect_content=False,
            entities=entities,
            reply_to_message_id=reply_message_id,
        )
    except TelegramBadRequest as e:
        if e.message != "Bad Request: message to be replied not found":
            raise e

        return await bot.send_message(
            chat_id,
            message_text,
            message_thread_id=thread,
            protect_content=False,
            entities=entities,
            parse_mode=parse_mode,
        )


def adjust_entities_and_message_text(
    prefix: str,
    text: str,
    entities: Optional[List[MessageEntity]],
    user: Optional[User] = None,
):
    full_name = user.full_name if user else ""
    full_name_length = len(full_name.encode("utf-16-le")) // 2

    new_entities = []

    if user:
        new_entities.append(
            MessageEntity(
                type="code",
                offset=len(prefix.encode("utf-16-le")) // 2,
                length=full_name_length,
            )
        )

        prefix += full_name

        username = user.username
        if username:
            new_entities.append(
                MessageEntity(
                    type="url",
                    offset=(len(prefix.encode("utf-16-le")) // 2) + 2,
                    length=len(username) + 1,
                    url=f"https://t.me/{username}",
                )
            )

            prefix += f" (@{username})"

    prefix += ":\n\n"
    entity_offset = len(prefix.encode("utf-16-le")) // 2

    if entities:
        for entity in entities:
            adjusted_entity = entity.model_copy()
            adjusted_entity.offset += entity_offset
            new_entities.append(adjusted_entity)

    return prefix + text, new_entities


async def send_reply(message: Message, bot: Bot, uow: UnitOfWork):
    message_text = message.text
    if not message_text.startswith("/reply"):
        await message.reply("Команда /reply бути на початку повідомлення")
        return

    reply_message = message.reply_to_message
    if reply_message is None:
        await message.reply(
            "Команда /reply має бути реплаєм на повідомлення із замовленням"
        )
        return

    order_message_id = reply_message.message_id
    order = await uow.orders.find_one(Order.order_message_id == order_message_id)
    if order is None:
        await message.reply(
            "Команда /reply має бути реплаєм на повідомлення із замовленням"
        )
        return

    message_text = message.text
    stripped_text = message_text.split(maxsplit=1)[-1] if " " in message_text else ""
    if not stripped_text:
        await message.reply("Додайте текст відповіді після команди /reply")
        return

    prefix = "📩 Нове повідомлення від модераторів:\n\n"
    offset = (
        (len(prefix.encode("utf-16-le")) // 2)
        - (len(message_text.encode("utf-16-le")) // 2)
        + (len(stripped_text.encode("utf-16-le")) // 2)
    )

    new_entities = []
    entities = message.entities
    if entities:
        for entity in entities:
            if not (entity.offset == 0 and entity.type == "bot_command"):
                adjusted_entity = entity.model_copy()
                adjusted_entity.offset += offset
                new_entities.append(adjusted_entity)

    user_id = order.ordered_by
    reply_text = prefix + stripped_text

    forwarded_message = await bot.send_message(
        user_id, reply_text, parse_mode=None, entities=new_entities
    )

    await store_message_mapping(
        user_id, forwarded_message.message_id, message.message_id
    )

    await bot.set_message_reaction(
        message.chat.id,
        message.message_id,
        [ReactionTypeEmoji(emoji="❤")],
    )


async def send_feedback(message: Message, bot: Bot):
    user_id = message.from_user.id
    message_id = message.message_id

    if message.text:
        user = message.from_user
        prefix = "📩 Нове повідомлення від "
        info_text, entities = adjust_entities_and_message_text(
            prefix,
            message.text,
            message.entities,
            user,
        )

        forwarded_message = await bot.send_message(
            settings.ADMINS_CHAT_ID,
            info_text,
            message_thread_id=settings.ADMINS_FEEDBACK_THREAD_ID,
            protect_content=False,
            entities=entities,
            parse_mode=None,
        )
        await store_message_mapping(user_id, message_id, forwarded_message.message_id)
        return

    full_name = message.from_user.full_name
    username = message.from_user.username
    username_label = (
        f' (<a href="https://t.me/{username}">@{username}</a>)' if username else ""
    )

    info_message = await bot.send_message(
        settings.ADMINS_CHAT_ID,
        f"📩 Нове повідомлення від <code>{full_name}</code>{username_label}:",
        message_thread_id=settings.ADMINS_FEEDBACK_THREAD_ID,
        parse_mode="HTML",
    )

    forwarded_message = await message.forward(
        settings.ADMINS_CHAT_ID,
        settings.ADMINS_FEEDBACK_THREAD_ID,
        protect_content=False,
    )

    await store_message_mapping(
        user_id, message_id, forwarded_message.message_id, info_message.message_id, True
    )


async def user_feedback_reply_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    reply_message_id = message.reply_to_message.message_id
    admin_message_id = await get_admin_message_id(user_id, reply_message_id)

    if not admin_message_id:
        return

    if message.text:
        user = message.from_user
        prefix = "📨 Відповідь від "
        info_text, entities = adjust_entities_and_message_text(
            prefix,
            message.text,
            message.entities,
            user,
        )
        forwarded_message = await send_message_with_reply(
            settings.ADMINS_CHAT_ID,
            admin_message_id,
            info_text,
            bot,
            thread=settings.ADMINS_FEEDBACK_THREAD_ID,
            entities=entities,
        )
        await store_message_mapping(
            user_id,
            message.message_id,
            forwarded_message.message_id,
        )
        return

    full_name = message.from_user.full_name
    username = message.from_user.username
    username_label = (
        f' (<a href="https://t.me/{username}">@{username}</a>)' if username else ""
    )

    info_message = await send_message_with_reply(
        settings.ADMINS_CHAT_ID,
        admin_message_id,
        f"📨 Відповідь від <code>{full_name}</code>{username_label}:",
        bot,
        settings.ADMINS_FEEDBACK_THREAD_ID,
        parse_mode="HTML",
    )

    forwarded_actual = await message.forward(
        settings.ADMINS_CHAT_ID,
        settings.ADMINS_FEEDBACK_THREAD_ID,
        protect_content=False,
    )

    await store_message_mapping(
        user_id,
        message.message_id,
        forwarded_actual.message_id,
        info_message.message_id,
        True,
    )


async def admin_feedback_reply_handler(message: Message, bot: Bot):
    user_id, user_message_id = await get_user_message_id(
        message.reply_to_message.message_id
    )

    if not user_id or not user_message_id:
        return

    await bot.set_message_reaction(
        message.chat.id,
        message.message_id,
        [ReactionTypeEmoji(emoji="❤")],
    )

    if message.text:
        info_text, entities = adjust_entities_and_message_text(
            "📨 Відповідь від модераторів",
            message.text,
            message.entities,
        )
        forwarded_message = await send_message_with_reply(
            user_id, user_message_id, info_text, bot, entities=entities
        )
        await store_message_mapping(
            user_id,
            forwarded_message.message_id,
            message.message_id,
        )
        return

    info_message = await send_message_with_reply(
        user_id, user_message_id, "📨 Відповідь від модераторів:", bot
    )
    forwarded_message = await bot.copy_message(
        user_id,
        message.chat.id,
        message.message_id,
        protect_content=False,
    )

    await store_message_mapping(
        user_id,
        forwarded_message.message_id,
        message.message_id,
        info_message.message_id,
        False,
    )
