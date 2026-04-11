from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import Settings, load_settings
from bot.handlers.start import router as start_router
from bot.handlers.create import router as create_router
from bot.xui.client import XUIClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    xui = XUIClient(
        host=settings.xui_host,
        port=settings.xui_port,
        webbasepath=settings.xui_webbasepath,
        username=settings.xui_username,
        password=settings.xui_password,
    )

    # Register handlers
    dp.include_router(start_router)
    dp.include_router(create_router)

    # Inject dependencies into handler kwargs
    dp["settings"] = settings
    dp["xui"] = xui

    logger.info("Bot started, polling for updates...")
    try:
        await dp.start_polling(bot)
    finally:
        await xui.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
