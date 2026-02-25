"""Bridge helpers between hook data and agent memory injection."""

from __future__ import annotations

from typing import Any


def build_memory_hint_from_hook_data(
    data: dict[str, Any],
    *,
    max_items: int = 4,
    max_chars: int = 6000,
) -> str:
    """Convert EvoMap hook suggestions into a compact memory hint block."""
    assets = data.get("evomap_suggestions")
    if not isinstance(assets, list) or not assets:
        return ""

    lines: list[str] = []
    for asset in assets[: max(1, max_items)]:
        if not isinstance(asset, dict):
            continue
        summary = str(asset.get("summary", "")).strip()
        title = str(asset.get("title", "")).strip()
        aid = str(asset.get("asset_id") or asset.get("assetId") or "").strip()
        if summary:
            line = f"- {summary}"
        elif title:
            line = f"- {title}"
        elif aid:
            line = f"- 参考资产 {aid}"
        else:
            continue
        lines.append(line)
    if not lines:
        return ""

    block = "【EvoMap 协作经验候选】\n" + "\n".join(lines)
    return block[:max_chars]
