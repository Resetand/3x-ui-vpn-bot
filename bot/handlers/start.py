from __future__ import annotations

import html
import json
import logging
from pathlib import Path

from aiogram import Bot, Router, types
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile

from bot.config import Settings
from bot.services.access import is_user_allowed
from bot.services.provisioning import ensure_client_exists
from bot.utils.qr import generate_qr_png
from bot.xui.client import XUIClient

logger = logging.getLogger(__name__)
router = Router()

_CLIENTS_FILE = Path(__file__).resolve().parent.parent.parent / "clients_recommended.json"
_PLATFORM_ORDER = ["ios", "android", "windows", "macos"]


def _load_clients() -> dict:
    with open(_CLIENTS_FILE, encoding="utf-8") as f:
        return json.load(f)


@router.message(CommandStart())
async def handle_start(message: types.Message, settings: Settings, xui: XUIClient, bot: Bot) -> None:
    user = message.from_user
    if not user:
        return

    # Only respond in private chats
    if message.chat.type != "private":
        await message.answer("📩 Напишите мне в личные сообщения, чтобы получить VPN-ключ.")
        return

    # Access control: allowed Telegram IDs (static list)
    if settings.allowed_telegram_ids is not None and user.id not in settings.allowed_telegram_ids:
        logger.info("Access denied for user %d: not in allowed_telegram_ids", user.id)
        await message.answer("⛔ Доступ запрещён. Обратитесь к администратору.")
        return

    # Access control: group membership
    if not await is_user_allowed(bot, user.id, settings.allowed_chat_id):
        await message.answer("⛔ Доступ запрещён. Обратитесь к администратору.")
        return

    await message.answer("⏳ Настраиваю VPN-доступ, подождите...")

    try:
        result = await ensure_client_exists(
            xui=xui,
            user_id=user.id,
            first_name=user.first_name or "User",
            username=user.username,
            inbound_ids=settings.xui_inbound_ids,
            host=settings.xui_host,
            sub_url_base=settings.sub_url_base,
            vless_flow=settings.vless_flow,
        )
    except Exception:
        logger.exception("Provisioning failed for user %d", user.id)
        await message.answer("❌ Произошла ошибка при настройке VPN. Попробуйте позже или обратитесь к администратору.")
        return

    if not result.sub_url:
        await message.answer("⚠️ Не удалось создать подключения. Обратитесь к администратору.")
        return

    # 1. QR + copyable subscription link
    qr_buf = generate_qr_png(result.sub_url)
    await message.answer_photo(
        BufferedInputFile(qr_buf.read(), filename="subscription_qr.png"),
        caption=f"\n\n🔑 Ваш ключ-ссылка: <b><code>{html.escape(result.sub_url)}</code></b>\n\n",
        parse_mode="HTML",
    )

    # 2. Setup instructions
    clients = _load_clients()
    await message.answer(
        _build_instructions(clients),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


def _build_instructions(clients: dict) -> str:
    parts: list[str] = [
        "🟢 <b>VPN настроен!</b>",
        "Теперь нужно подключиться — это займёт 1–2 минуты 👇\n",
        "📱 <b>Шаг 1. Установите приложение-клиент</b>\n",
        "Ниже перечислены рекомендуемые приложения для разных платформ.\n"
        "Подробнее о том что такое клиенты <a href=\"https://github.com/Resetand/3x-ui-vpn-bot/wiki/%D0%9F%D1%80%D0%B8%D0%BB%D0%BE%D0%B6%D0%B5%D0%BD%D0%B8%D1%8F-%D0%BA%D0%BB%D0%B8%D0%B5%D0%BD%D1%82%D1%8B\">небольшой статье</a>.\n",
    ]

    for key in _PLATFORM_ORDER:
        platform = clients.get(key)
        if not platform:
            continue

        if recommended_client := next((c for c in platform["clients"] if c.get("recommended")), None):
            name = html.escape(recommended_client["name"])
            parts.append(f'<b>{html.escape(platform["name"])}</b>: <a href="{recommended_client["url"]}">{name}</a>')
    
    
    parts.append("")

    parts.append("🔗 <b>Шаг 2. Добавьте VPN</b>\n")
    parts.append("1. Скопируйте ключ-ссылку (из сообщения выше 🔼)")
    parts.append("2. Откройте приложение-клиент")
    parts.append("3. Импортируйте конфигурацию — отсканируйте QR или вставьте ссылку\n")

    parts.append("▶️ <b>Шаг 3. Подключитесь</b>\n")
    parts.append("1. Выберите сервер (рекомендуем Germany, vless ⭐)")
    parts.append("2. Нажмите «Подключиться» и разрешите добавление VPN-конфигурации\n")

    parts.append("✅ <b>Готово!</b> Теперь интернет работает через VPN.")

    return "\n".join(parts)
