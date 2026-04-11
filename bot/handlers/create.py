from __future__ import annotations

import html
import logging
import uuid

from aiogram import Bot, Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile

from bot.config import Settings
from bot.handlers.start import _build_instructions, _load_clients
from bot.services.provisioning import ensure_client_exists
from bot.utils.qr import generate_qr_png
from bot.xui.client import XUIClient

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("issue"))
async def handle_issue(message: types.Message, settings: Settings, xui: XUIClient, bot: Bot) -> None:
    user = message.from_user
    if not user:
        return

    # Only respond in private chats
    if message.chat.type != "private":
        return

    # Admin check
    if settings.admin_telegram_id is None or user.id != settings.admin_telegram_id:
        logger.info("Access denied for /issue: user %d is not admin", user.id)
        await message.answer("⛔ Доступ запрещён.")
        return

    # Parse comment from command arguments
    raw_args = message.text or ""
    parts = raw_args.split(maxsplit=1)
    comment = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "manual"

    slug = uuid.uuid4().hex[:8]

    await message.answer("⏳ Создаю VPN-клиента...")

    try:
        result = await ensure_client_exists(
            xui=xui,
            user_id=user.id,
            first_name=user.first_name or "Admin",
            username=user.username,
            inbound_ids=settings.xui_inbound_ids,
            host=settings.xui_host,
            sub_url_base=settings.sub_url_base,
            vless_flow=settings.vless_flow,
            slug=slug,
            comment=comment,
        )
    except Exception:
        logger.exception("Provisioning failed for /issue by admin %d", user.id)
        await message.answer("❌ Произошла ошибка при создании клиента. Попробуйте позже.")
        return

    if not result.sub_url:
        await message.answer("⚠️ Не удалось создать подключения. Попробуйте позже.")
        return

    # QR + copyable subscription link
    qr_buf = generate_qr_png(result.sub_url)
    await message.answer_photo(
        BufferedInputFile(qr_buf.read(), filename="subscription_qr.png"),
        caption=f"🔑 Ключ-ссылка:\n\n<code>{html.escape(result.sub_url)}</code>",
        parse_mode="HTML",
    )

    # Setup instructions
    clients = _load_clients()
    await message.answer(
        _build_instructions(clients),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
