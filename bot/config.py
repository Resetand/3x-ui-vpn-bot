from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    xui_host: str
    xui_port: int
    xui_webbasepath: str
    xui_username: str
    xui_password: str
    xui_inbound_ids: list[int]
    allowed_telegram_ids: set[int] | None  # None means wildcard (*)
    allowed_chat_id: int | None  # Telegram group/supergroup ID for membership check
    sub_url_base: str | None
    vless_flow: str
    admin_telegram_id: int | None


def load_settings() -> Settings:
    load_dotenv()

    def _require(name: str) -> str:
        val = os.environ.get(name)
        if not val:
            print(f"ERROR: Required environment variable {name} is not set", file=sys.stderr)
            sys.exit(1)
        return val

    telegram_bot_token = _require("TELEGRAM_BOT_TOKEN")
    xui_host = _require("XUI_HOST")
    xui_port = int(os.environ.get("XUI_PORT", "2053"))
    xui_webbasepath = os.environ.get("XUI_WEBBASEPATH", "/").rstrip("/")
    xui_username = _require("XUI_USERNAME")
    xui_password = _require("XUI_PASSWORD")

    raw_ids = os.environ.get("XUI_INBOUND_IDS", "")
    if not raw_ids.strip():
        print("ERROR: XUI_INBOUND_IDS must contain at least one inbound ID", file=sys.stderr)
        sys.exit(1)
    xui_inbound_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip()]

    raw_allowed = os.environ.get("ALLOWED_TELEGRAM_IDS", "").strip()
    if raw_allowed == "*":
        allowed_telegram_ids = None
    elif raw_allowed:
        allowed_telegram_ids = {int(x.strip()) for x in raw_allowed.split(",") if x.strip()}
    else:
        allowed_telegram_ids = set()  # empty = deny all

    raw_chat_id = os.environ.get("ALLOWED_CHAT_ID", "").strip()
    allowed_chat_id = int(raw_chat_id) if raw_chat_id else None

    sub_url_base = os.environ.get("SUB_URL_BASE", "").strip() or None
    vless_flow = os.environ.get("VLESS_FLOW", "").strip()

    raw_admin_id = os.environ.get("ADMIN_TELEGRAM_ID", "").strip()
    admin_telegram_id = int(raw_admin_id) if raw_admin_id else None

    return Settings(
        telegram_bot_token=telegram_bot_token,
        xui_host=xui_host,
        xui_port=xui_port,
        xui_webbasepath=xui_webbasepath,
        xui_username=xui_username,
        xui_password=xui_password,
        xui_inbound_ids=xui_inbound_ids,
        allowed_telegram_ids=allowed_telegram_ids,
        allowed_chat_id=allowed_chat_id,
        sub_url_base=sub_url_base,
        vless_flow=vless_flow,
        admin_telegram_id=admin_telegram_id,
    )
