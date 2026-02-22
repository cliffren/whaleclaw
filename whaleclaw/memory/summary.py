"""Conversation summarization and fact extraction."""

from __future__ import annotations

import re

FACT_PATTERNS = [
    re.compile(r".*[是]\s*[^，。！？\s]+.*"),
    re.compile(r".*=\s*[^，。！？\s]+.*"),
    re.compile(r".*喜欢\s+[^，。！？\s]+.*"),
    re.compile(r".*\bprefer\s+\w+.*", re.IGNORECASE),
    re.compile(r".*\bis\s+\w+.*", re.IGNORECASE),
    re.compile(r".*\b(?:like|love|hate)\s+\w+.*", re.IGNORECASE),
]


class ConversationSummarizer:
    """Extractive summarization without LLM."""

    async def summarize(self, messages: list[dict[str, str]]) -> str:
        if not messages:
            return ""
        n = 2
        first = messages[:n]
        last = messages[-n:] if len(messages) > n else []
        parts: list[str] = []
        for m in first:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            if content.strip():
                parts.append(f"[{role}] {content[:200]}")
        if last and last != first:
            parts.append("...")
            for m in last:
                role = m.get("role", "unknown")
                content = m.get("content", "")
                if content.strip():
                    parts.append(f"[{role}] {content[:200]}")
        return "\n".join(parts)

    async def extract_facts(self, messages: list[dict[str, str]]) -> list[str]:
        facts: list[str] = []
        seen: set[str] = set()
        for m in messages:
            content = m.get("content", "")
            for line in content.split("\n"):
                line = line.strip()
                if len(line) < 5:
                    continue
                for pat in FACT_PATTERNS:
                    if pat.match(line) and line not in seen:
                        seen.add(line)
                        facts.append(line)
                        break
        return facts
