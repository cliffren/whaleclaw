"""Feishu channel — bot integration via Webhook."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from typing import Any

from whaleclaw.channels.base import ChannelMessage, ChannelPlugin
from whaleclaw.channels.feishu.bot import FeishuBot
from whaleclaw.channels.feishu.client import FeishuClient
from whaleclaw.channels.feishu.config import FeishuConfig
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)


class FeishuChannel(ChannelPlugin):
    """Feishu channel plugin — manages client, bot, and webhook."""

    name = "feishu"

    def __init__(self, config: FeishuConfig | None = None) -> None:
        self._config = config or FeishuConfig(
            app_id=os.environ.get("FEISHU_APP_ID", ""),
            app_secret=os.environ.get("FEISHU_APP_SECRET", ""),
            verification_token=os.environ.get("FEISHU_VERIFICATION_TOKEN"),
            encrypt_key=os.environ.get("FEISHU_ENCRYPT_KEY"),
        )
        self._client: FeishuClient | None = None
        self._bot: FeishuBot | None = None
        self._callback: Callable[
            [ChannelMessage], Awaitable[None]
        ] | None = None

    @property
    def client(self) -> FeishuClient | None:
        return self._client

    @property
    def bot(self) -> FeishuBot | None:
        return self._bot

    async def start(self) -> None:
        if not self._config.app_id or not self._config.app_secret:
            log.warning("feishu.not_configured")
            return
        self._client = FeishuClient(
            self._config.app_id, self._config.app_secret
        )
        self._bot = FeishuBot(self._client, self._config)
        log.info("feishu.started")

    async def stop(self) -> None:
        log.info("feishu.stopped")

    async def send(
        self, peer_id: str, content: str, **kwargs: Any
    ) -> None:
        if self._client:
            import json

            msg_content = json.dumps({"text": content})
            await self._client.send_message(peer_id, "text", msg_content)

    async def on_message(
        self,
        callback: Callable[[ChannelMessage], Awaitable[None]],
    ) -> None:
        self._callback = callback
