"""In-memory store with keyword matching, optional embedding and JSON persistence."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from whaleclaw.memory.base import MemoryEntry, MemorySearchResult, MemoryStore
from whaleclaw.utils.log import get_logger

if TYPE_CHECKING:
    from fastembed import TextEmbedding

log = get_logger(__name__)


def _serialize_entry(entry: MemoryEntry) -> dict:
    d = entry.model_dump(mode="json")
    d["created_at"] = entry.created_at.isoformat()
    d["last_accessed"] = entry.last_accessed.isoformat()
    return d


def _deserialize_entry(d: dict) -> MemoryEntry:
    d = dict(d)
    d["created_at"] = datetime.fromisoformat(d["created_at"])
    d["last_accessed"] = datetime.fromisoformat(d["last_accessed"])
    return MemoryEntry.model_validate(d)


class SimpleMemoryStore(MemoryStore):
    """In-memory store with keyword matching, optional embedding, and JSON persistence.

    Args:
        persist_dir: Directory for JSON persistence. ``None`` disables persistence.
        use_embedding: When ``True``, compute embeddings on ``add`` and use
            cosine-similarity + keyword hybrid scoring in ``search``.
            When ``False`` (the default), behaviour is identical to the
            legacy keyword-only implementation.
        embedding_model: Model name for *fastembed*. Only used when
            ``use_embedding=True``.
    """

    def __init__(
        self,
        persist_dir: Path | None = None,
        *,
        use_embedding: bool = False,
        embedding_model: str = "BAAI/bge-small-zh-v1.5",
    ) -> None:
        self._entries: dict[str, MemoryEntry] = {}
        self._persist_dir = persist_dir
        self._use_embedding = use_embedding
        self._embedding_model = embedding_model
        self._embedder: TextEmbedding | None = None
        if persist_dir:
            self._load()

    # ------------------------------------------------------------------
    # Embedding helpers
    # ------------------------------------------------------------------

    def _get_embedder(self) -> TextEmbedding:
        """Lazily initialise the embedding model (first call ~1-2 s)."""
        if self._embedder is None:
            try:
                from fastembed import TextEmbedding as _TE
            except ImportError as exc:
                raise ImportError(
                    "fastembed is required for embedding support. "
                    'Install it with: pip install "whaleclaw[embedding]"'
                ) from exc
            self._embedder = _TE(self._embedding_model)
            log.info(
                "memory.embedding_model_loaded",
                model=self._embedding_model,
            )
        return self._embedder

    def _embed(self, text: str) -> list[float]:
        """Return the embedding vector for *text*."""
        return list(next(self._get_embedder().embed([text])))

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        path = self._persist_dir / "memory.json"  # type: ignore[union-attr]
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for d in data.get("entries", []):
                entry = _deserialize_entry(d)
                self._entries[entry.id] = entry
        except (OSError, json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        if not self._persist_dir:
            return
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        path = self._persist_dir / "memory.json"
        data = {"entries": [_serialize_entry(e) for e in self._entries.values()]}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Keyword scoring (legacy, always available)
    # ------------------------------------------------------------------

    def _keyword_score(self, query: str, content: str) -> float:
        words = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 0]
        if not words:
            return 0.0
        content_lower = content.lower()
        found = sum(1 for w in words if w in content_lower)
        return found / len(words)

    # ------------------------------------------------------------------
    # MemoryStore interface
    # ------------------------------------------------------------------

    async def add(
        self,
        content: str,
        source: str,
        tags: list[str] | None = None,
        *,
        importance: float = 0.5,
    ) -> MemoryEntry:
        now = datetime.now(UTC)
        embedding: list[float] | None = None
        if self._use_embedding:
            embedding = self._embed(content)
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            source=source,
            tags=tags or [],
            importance=importance,
            embedding=embedding,
            created_at=now,
            last_accessed=now,
        )
        self._entries[entry.id] = entry
        self._save()
        return entry

    async def search(
        self, query: str, limit: int = 5, min_score: float = 0.5
    ) -> list[MemorySearchResult]:
        if self._use_embedding:
            return self._hybrid_search(query, limit, min_score)
        return self._keyword_search(query, limit, min_score)

    async def get(self, memory_id: str) -> MemoryEntry | None:
        return self._entries.get(memory_id)

    async def delete(self, memory_id: str) -> bool:
        if memory_id in self._entries:
            del self._entries[memory_id]
            self._save()
            return True
        return False

    async def list_recent(self, limit: int = 20) -> list[MemoryEntry]:
        entries = sorted(self._entries.values(), key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    # ------------------------------------------------------------------
    # Search implementations
    # ------------------------------------------------------------------

    def _keyword_search(
        self, query: str, limit: int, min_score: float
    ) -> list[MemorySearchResult]:
        """Legacy keyword-only search (use_embedding=False)."""
        results: list[MemorySearchResult] = []
        for entry in self._entries.values():
            score = self._keyword_score(query, entry.content)
            if score >= min_score:
                results.append(MemorySearchResult(entry=entry, score=score))
        results.sort(key=lambda r: (-r.score, -r.entry.created_at.timestamp()))
        return results[:limit]

    def _hybrid_search(
        self, query: str, limit: int, min_score: float
    ) -> list[MemorySearchResult]:
        """Hybrid search: 70 % cosine similarity + 30 % keyword match."""
        query_vec = self._embed(query)
        threshold = max(0.05, min_score * 0.7)
        results: list[MemorySearchResult] = []
        for entry in self._entries.values():
            vec_score = (
                self._cosine_sim(query_vec, entry.embedding) if entry.embedding else 0.0
            )
            kw_score = self._keyword_score(query, entry.content)
            score = 0.7 * vec_score + 0.3 * kw_score
            if score >= threshold:
                results.append(MemorySearchResult(entry=entry, score=score))
        results.sort(key=lambda r: (-r.score, -r.entry.created_at.timestamp()))
        return results[:limit]
