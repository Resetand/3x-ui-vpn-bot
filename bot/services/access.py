from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus

logger = logging.getLogger(__name__)

_ALLOWED_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


async def is_user_allowed(bot: Bot, user_id: int, allowed_chat_id: int | None) -> bool:
    """Check whether *user_id* is a member of the required Telegram group.

    Returns ``True`` when:
    - *allowed_chat_id* is ``None`` (check disabled, everyone allowed)
    - user has status member / administrator / creator in the group
    """
    if allowed_chat_id is None:
        return True

    try:
        member = await bot.get_chat_member(chat_id=allowed_chat_id, user_id=user_id)
    except Exception:
        logger.exception("Failed to check membership for user %d in chat %d", user_id, allowed_chat_id)
        return False

    if member.status in _ALLOWED_STATUSES:
        return True

    logger.info(
        "Access denied for user %d: status=%s in chat %d",
        user_id,
        member.status,
        allowed_chat_id,
    )
    return False
