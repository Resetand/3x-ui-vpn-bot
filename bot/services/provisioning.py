from __future__ import annotations

import asyncio
import base64
import logging
import os
import uuid
from dataclasses import dataclass

import httpx

from bot.xui.client import XUIClient

logger = logging.getLogger(__name__)

# Per-user locks to prevent concurrent duplicate creation
_user_locks: dict[int, asyncio.Lock] = {}


def _get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


@dataclass
class ProvisioningResult:
    sub_id: str
    sub_url: str | None  # subscription URL if configured


async def fetch_sub_links(sub_url: str) -> list[str]:
    """Fetch connection links from 3x-ui subscription endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(sub_url)
        resp.raise_for_status()
        decoded = base64.b64decode(resp.text).decode("utf-8")
        return [line for line in decoded.splitlines() if line.strip()]


async def ensure_client_exists(
    xui: XUIClient,
    user_id: int,
    first_name: str,
    username: str | None,
    inbound_ids: list[int],
    host: str,
    sub_url_base: str | None,
    vless_flow: str = "",
) -> ProvisioningResult:
    """Ensure the user has a client in every configured inbound. Idempotent."""
    async with _get_user_lock(user_id):
        return await _provision(xui, user_id, first_name, username, inbound_ids, host, sub_url_base, vless_flow)


async def _provision(
    xui: XUIClient,
    user_id: int,
    first_name: str,
    username: str | None,
    inbound_ids: list[int],
    host: str,
    sub_url_base: str | None,
    vless_flow: str = "",
) -> ProvisioningResult:
    all_inbounds = await xui.get_inbounds()
    inbound_map = {ib["id"]: ib for ib in all_inbounds}

    sub_id = f"{user_id}"
    existing_sub_id: str | None = None

    comment = f"{first_name} (@{username})" if username else first_name

    for iid in inbound_ids:
        inbound = inbound_map.get(iid)
        if inbound is None:
            logger.warning("Inbound %d from allowlist not found in 3x-ui — skipping", iid)
            continue

        email = f"{iid}_{user_id}"
        clients = inbound.get("settings", {}).get("clients", [])

        # Look for existing client
        existing = None
        for c in clients:
            if c.get("email") == email:
                existing = c
                break

        if existing:
            # Reuse subId from existing client if available
            if existing.get("subId") and not existing_sub_id:
                existing_sub_id = existing["subId"]
        else:
            # Create new client — fields depend on inbound protocol
            protocol = inbound.get("protocol", "")
            client_uuid = str(uuid.uuid4())
            final_sub_id = existing_sub_id or sub_id
            client_data = {
                "email": email,
                "limitIp": 0,
                "totalGB": 0,
                "expiryTime": 0,
                "enable": True,
                "tgId": user_id,
                "subId": final_sub_id,
                "comment": comment,
                "reset": 0,
            }
            if protocol == "trojan":
                client_data["password"] = client_uuid
            elif protocol == "shadowsocks":
                method = inbound.get("settings", {}).get("method", "chacha20-ietf-poly1305")
                # Shadowsocks 2022: password must be a base64-encoded key of correct length
                if method.startswith("2022-"):
                    key_len = 32 if "256" in method else 16
                    client_data["password"] = base64.b64encode(os.urandom(key_len)).decode()
                    client_data["method"] = ""
                else:
                    client_data["password"] = client_uuid
                    client_data["method"] = method
            else:
                # vless, vmess
                client_data["id"] = client_uuid
                # flow only works with VLESS + TCP (xtls-rprx-vision for Reality/XTLS)
                network = inbound.get("streamSettings", {}).get("network", "tcp")
                if protocol == "vless" and network == "tcp" and vless_flow:
                    client_data["flow"] = vless_flow
                else:
                    client_data["flow"] = ""
            created = await xui.add_client(iid, client_data)
            if created:
                logger.info("Created client %s in inbound %d", email, iid)
            else:
                logger.info("Client %s already existed in inbound %d (duplicate)", email, iid)
            if not existing_sub_id:
                existing_sub_id = final_sub_id

    final_sub_id_value = existing_sub_id or sub_id
    sub_url = f"{sub_url_base}/{final_sub_id_value}" if sub_url_base else None

    return ProvisioningResult(sub_id=final_sub_id_value, sub_url=sub_url)
