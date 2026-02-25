"""Feishu Open Platform API client."""

from __future__ import annotations

import time
from typing import Any

import httpx

from whaleclaw.utils.log import get_logger

log = get_logger(__name__)

_BASE = "https://open.feishu.cn/open-apis"


class FeishuClient:
    """Async HTTP client for the Feishu Open Platform."""

    def __init__(self, app_id: str, app_secret: str, *, timeout: int = 30) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._timeout = timeout
        self._tenant_access_token: str | None = None
        self._token_expires_at: float = 0

    async def _ensure_token(self) -> str:
        if self._tenant_access_token and time.time() < self._token_expires_at:
            return self._tenant_access_token
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{_BASE}/auth/v3/tenant_access_token/internal",
                json={"app_id": self._app_id, "app_secret": self._app_secret},
            )
            data = resp.json()
        if data.get("code") != 0:
            msg = f"获取 tenant_access_token 失败: {data}"
            raise RuntimeError(msg)
        self._tenant_access_token = data["tenant_access_token"]
        self._token_expires_at = time.time() + data.get("expire", 7200) - 60
        return self._tenant_access_token

    async def request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make an authenticated API request."""
        token = await self._ensure_token()
        headers = {
            "Authorization": f"Bearer {token}",
            **(kwargs.pop("headers", None) or {}),
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.request(method, f"{_BASE}{path}", headers=headers, **kwargs)
        data: dict[str, Any] = resp.json()
        if data.get("code", 0) != 0:
            log.warning("feishu.api_error", path=path, code=data.get("code"), msg=data.get("msg"))
        return data

    # ── Message API ─────────────────────────────────────────

    async def send_message(
        self,
        receive_id: str,
        msg_type: str,
        content: str,
        receive_id_type: str = "open_id",
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"/im/v1/messages?receive_id_type={receive_id_type}",
            json={"receive_id": receive_id, "msg_type": msg_type, "content": content},
        )

    async def reply_message(
        self, message_id: str, msg_type: str, content: str
    ) -> dict[str, Any]:
        return await self.request(
            "POST",
            f"/im/v1/messages/{message_id}/reply",
            json={"msg_type": msg_type, "content": content},
        )

    async def update_message(
        self, message_id: str, content: str
    ) -> dict[str, Any]:
        return await self.request(
            "PATCH",
            f"/im/v1/messages/{message_id}",
            json={"content": content},
        )

    async def get_message(self, message_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/im/v1/messages/{message_id}")

    # ── Media API ───────────────────────────────────────────

    async def upload_image(
        self, image: bytes, image_type: str = "message"
    ) -> str:
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{_BASE}/im/v1/images",
                headers={"Authorization": f"Bearer {token}"},
                data={"image_type": image_type},
                files={"image": ("image.png", image, "image/png")},
            )
        data = resp.json()
        return data.get("data", {}).get("image_key", "")

    async def upload_file(
        self, file: bytes, filename: str, file_type: str
    ) -> str:
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{_BASE}/im/v1/files",
                headers={"Authorization": f"Bearer {token}"},
                data={"file_type": file_type, "file_name": filename},
                files={"file": (filename, file, "application/octet-stream")},
            )
        data = resp.json()
        return data.get("data", {}).get("file_key", "")

    async def download_resource(
        self, message_id: str, file_key: str, *, resource_type: str = "file"
    ) -> bytes:
        token = await self._ensure_token()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                f"{_BASE}/im/v1/messages/{message_id}/resources/{file_key}",
                headers={"Authorization": f"Bearer {token}"},
                params={"type": resource_type},
            )
        return resp.content

    # ── User API ────────────────────────────────────────────

    async def get_user_info(
        self, user_id: str, user_id_type: str = "open_id"
    ) -> dict[str, Any]:
        return await self.request(
            "GET",
            f"/contact/v3/users/{user_id}?user_id_type={user_id_type}",
        )
