from datetime import datetime
from typing import Optional

from app.bot.models.auto_moderation import AutoModeration
from app.bot.repositories.uow import UnitOfWork


async def set_auto_moderation(
    uow: UnitOfWork, video_id: str, confirm: Optional[bool], set_by: int
) -> AutoModeration:
    """Put a video into one of the auto-moderation lists.

    confirm=True  -> whitelist
    confirm=False -> blacklist
    confirm=None  -> manual list

    Mirrors the behaviour of the /whitelist, /blacklist and /manual_list
    commands: if the video already has an active record with the same
    value, it is left untouched; if it has a record with a different
    value, that record is superseded (marked as deleted) and a new one
    is created.
    """
    record = await uow.auto_moderation.find_one(
        AutoModeration.video_id == video_id, AutoModeration.is_deleted == False
    )

    if record and record.confirm == confirm:
        return record

    if record:
        record.is_deleted = True

    return await uow.auto_moderation.create(
        AutoModeration(
            video_id=video_id,
            confirm=confirm,
            set_by=set_by,
            timestamp=datetime.now(),
        )
    )
