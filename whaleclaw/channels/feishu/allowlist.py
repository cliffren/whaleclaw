"""Feishu user allowlist — persisted to disk."""

from __future__ import annotations

import json
from pathlib import Path

from whaleclaw.config.paths import CREDENTIALS_DIR

_FILE = CREDENTIALS_DIR / "feishu_allowlist.json"


class FeishuAllowList:
    """Manage the user allowlist for Feishu DM access."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _FILE
        self._ids: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self._path.is_file():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._ids = set(data) if isinstance(data, list) else set()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(sorted(self._ids), ensure_ascii=False),
            encoding="utf-8",
        )

    def is_allowed(self, open_id: str) -> bool:
        return open_id in self._ids

    def add(self, open_id: str) -> None:
        self._ids.add(open_id)
        self._save()

    def remove(self, open_id: str) -> None:
        self._ids.discard(open_id)
        self._save()

    def list_all(self) -> list[str]:
        return sorted(self._ids)
