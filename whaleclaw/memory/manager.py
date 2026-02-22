"""Memory manager — recall, memorize, compact with token budget."""

from __future__ import annotations

from whaleclaw.memory.base import MemoryEntry, MemoryStore
from whaleclaw.memory.summary import ConversationSummarizer


def _est_tokens(text: str) -> int:
    return max(0, len(text) // 3)


class MemoryManager:
    """Orchestrates recall and storage with token budget."""

    def __init__(self, store: MemoryStore) -> None:
        self._store = store
        self._summarizer = ConversationSummarizer()

    async def recall(self, query: str, max_tokens: int = 500, limit: int = 10) -> str:
        results = await self._store.search(query, limit=limit, min_score=0.3)
        if not results:
            return ""
        parts: list[str] = []
        used = 0
        for r in results:
            txt = f"- {r.entry.content}"
            need = _est_tokens(txt)
            if used + need > max_tokens:
                break
            parts.append(txt)
            used += need
        return "\n".join(parts) if parts else ""

    async def memorize(
        self, content: str, source: str, tags: list[str] | None = None
    ) -> MemoryEntry:
        return await self._store.add(content, source, tags or [])

    async def compact(self, messages: list[dict[str, str]], source: str) -> str:
        summary = await self._summarizer.summarize(messages)
        facts = await self._summarizer.extract_facts(messages)
        for fact in facts:
            await self._store.add(fact, source, tags=["compact"])
        return summary
