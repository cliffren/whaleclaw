"""Feishu bot — core message handling logic."""

from __future__ import annotations

import json
from typing import Any

from whaleclaw.channels.feishu.allowlist import FeishuAllowList
from whaleclaw.channels.feishu.card import FeishuCard
from whaleclaw.channels.feishu.client import FeishuClient
from whaleclaw.channels.feishu.config import FeishuConfig
from whaleclaw.channels.feishu.dedup import MessageDedup
from whaleclaw.channels.feishu.mention import is_bot_mentioned, strip_bot_mention
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)


class FeishuBot:
    """Process incoming Feishu messages and route to the Agent."""

    def __init__(
        self,
        client: FeishuClient,
        config: FeishuConfig,
        allowlist: FeishuAllowList | None = None,
    ) -> None:
        self._client = client
        self._config = config
        self._dedup = MessageDedup()
        self._allowlist = allowlist or FeishuAllowList()
        self._pairing_codes: dict[str, str] = {}
        self._bot_open_id = ""

    def set_bot_open_id(self, bot_open_id: str) -> None:
        self._bot_open_id = bot_open_id

    async def handle_event(
        self, event_type: str, body: dict[str, Any]
    ) -> None:
        """Dispatch an event to the appropriate handler."""
        if event_type == "im.message.receive_v1":
            event = body.get("event", {})
            await self.handle_message(event)

    async def handle_message(self, event: dict[str, Any]) -> None:
        """Process a received message event."""
        message = event.get("message", {})
        msg_id = message.get("message_id", "")
        chat_type = message.get("chat_type", "")
        sender = event.get("sender", {}).get("sender_id", {})
        open_id = sender.get("open_id", "")

        if self._dedup.is_duplicate(msg_id):
            return
        self._dedup.mark(msg_id)

        text = self.extract_text(message)
        if not text:
            return

        if chat_type == "group":
            group_cfg = self._config.groups.get(
                message.get("chat_id", "")
            )
            need_mention = (
                group_cfg.require_mention if group_cfg else True
            )
            if need_mention and not is_bot_mentioned(message, self._bot_open_id):
                return
            text = strip_bot_mention(text, "")

        not_allowed = (
            chat_type == "p2p"
            and self._config.dm_policy != "open"
            and not self._allowlist.is_allowed(open_id)
        )
        if not_allowed:
            if self._config.dm_policy == "closed":
                return
            await self._send_pairing_prompt(open_id, msg_id)
            return

        log.info(
            "feishu.message",
            chat_type=chat_type,
            open_id=open_id,
            text_len=len(text),
        )

        card = FeishuCard.streaming_card()
        resp = await self._client.reply_message(msg_id, "interactive", card)
        reply_msg_id = (
            resp.get("data", {}).get("message_id", "")
        )

        if not reply_msg_id:
            content = json.dumps({"text": "处理中..."})
            await self._client.reply_message(msg_id, "text", content)

    @staticmethod
    def extract_text(message: dict[str, Any]) -> str:
        """Extract plain text from a Feishu message."""
        msg_type = message.get("message_type", "text")
        content_str = message.get("content", "{}")
        try:
            content = json.loads(content_str)
        except (json.JSONDecodeError, TypeError):
            return ""

        if msg_type == "text":
            return content.get("text", "")
        if msg_type == "post":
            parts: list[str] = []
            blocks = content.get("content") or [[]]
            for line in blocks:
                for elem in line:
                    if elem.get("tag") == "text":
                        parts.append(elem.get("text", ""))
            return " ".join(parts)
        return ""

    async def _send_pairing_prompt(
        self, open_id: str, msg_id: str
    ) -> None:
        import random
        import string

        code = "".join(random.choices(string.digits, k=6))  # noqa: S311
        self._pairing_codes[code] = open_id
        card = FeishuCard.text_card(
            f"请将此配对码发送给管理员进行验证:\n\n**{code}**",
            title="配对验证",
        )
        await self._client.reply_message(msg_id, "interactive", card)

    def approve_pairing(self, code: str) -> str | None:
        """Approve a pairing code and add the user to the allowlist."""
        open_id = self._pairing_codes.pop(code, None)
        if open_id:
            self._allowlist.add(open_id)
        return open_id
