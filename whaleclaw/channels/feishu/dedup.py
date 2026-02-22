"""Message deduplication for Feishu event callbacks."""

from __future__ import annotations

import time


class MessageDedup:
    """In-memory dedup based on message_id with a 5-minute TTL."""

    def __init__(self, ttl: float = 300.0) -> None:
        self._seen: dict[str, float] = {}
        self._ttl = ttl

    def _evict(self) -> None:
        now = time.monotonic()
        expired = [k for k, t in self._seen.items() if now - t > self._ttl]
        for k in expired:
            del self._seen[k]

    def is_duplicate(self, message_id: str) -> bool:
        self._evict()
        return message_id in self._seen

    def mark(self, message_id: str) -> None:
        self._seen[message_id] = time.monotonic()
