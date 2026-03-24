from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class XUIAuthError(Exception):
    pass


class XUIClient:
    def __init__(self, host: str, port: int, webbasepath: str, username: str, password: str) -> None:
        self._base_url = f"http://{host}:{port}{webbasepath}"
        self._username = username
        self._password = password
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0, follow_redirects=True)
        self._logged_in = False

    async def close(self) -> None:
        await self._client.aclose()

    async def login(self) -> None:
        resp = await self._client.post(
            "/login/",
            data={"username": self._username, "password": self._password},
        )
        body = resp.json()
        if not body.get("success"):
            raise XUIAuthError(f"Login failed: {body.get('msg', 'unknown error')}")
        self._logged_in = True
        logger.info("Logged in to 3x-ui panel")

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        if not self._logged_in:
            await self.login()

        resp = await self._client.request(method, path, **kwargs)

        # Auto re-login on session expiry (3x-ui returns 404 or 401 when the session cookie is stale)
        if resp.status_code in (401, 404) or (resp.is_redirect and "/login" in str(resp.headers.get("location", ""))):
            logger.info("Session expired (HTTP %d), re-logging in", resp.status_code)
            await self.login()
            resp = await self._client.request(method, path, **kwargs)

        resp.raise_for_status()
        return resp.json()

    async def get_inbounds(self) -> list[dict]:
        """Retrieve all inbounds. Parses settings and streamSettings JSON strings into dicts."""
        data = await self._request("GET", "/panel/api/inbounds/list")
        if not data.get("success"):
            raise RuntimeError(f"Failed to get inbounds: {data.get('msg')}")

        inbounds = data.get("obj") or []
        for inbound in inbounds:
            for field in ("settings", "streamSettings", "sniffing"):
                raw = inbound.get(field)
                if isinstance(raw, str):
                    try:
                        inbound[field] = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse %s JSON for inbound %s", field, inbound.get("id"))
        return inbounds

    async def add_client(self, inbound_id: int, client_data: dict) -> bool:
        """Add a client to an inbound. Returns True on success, False on duplicate email."""
        settings_json = json.dumps({"clients": [client_data]})
        data = await self._request(
            "POST",
            "/panel/api/inbounds/addClient",
            data={"id": str(inbound_id), "settings": settings_json},
        )
        if data.get("success"):
            return True
        msg = data.get("msg", "")
        if "Duplicate email" in msg:
            logger.info("Client with email %s already exists in inbound %d", client_data.get("email"), inbound_id)
            return False
        raise RuntimeError(f"Failed to add client to inbound {inbound_id}: {msg}")
