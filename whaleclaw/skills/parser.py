"""Parse SKILL.md files with YAML frontmatter."""

from __future__ import annotations

import contextlib
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class Skill(BaseModel):
    """Skill parsed from SKILL.md."""

    id: str
    name: str
    triggers: list[str] = Field(default_factory=list)
    trigger_description: str = ""
    instructions: str
    tools: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    max_tokens: int = 800
    source_path: Path


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)


def _extract_section(content: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*$\s*\n(.*?)(?=^##\s|\Z)"
    m = re.search(pattern, content, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else ""


def _first_paragraph(text: str) -> str:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paras[0] if paras else ""


class SkillParser:
    """Parse SKILL.md files with YAML frontmatter."""

    def parse(self, path: Path) -> Skill:
        """Parse SKILL.md file into Skill model."""
        raw = path.read_text(encoding="utf-8")
        body = raw
        frontmatter: dict[str, object] = {}

        fm_match = _FRONTMATTER_RE.match(raw)
        if fm_match:
            with contextlib.suppress(yaml.YAMLError):
                frontmatter = yaml.safe_load(fm_match.group(1)) or {}
            body = raw[fm_match.end() :]

        triggers = list(frontmatter.get("triggers") or [])
        if isinstance(triggers, str):
            triggers = [triggers]
        max_tokens = int(frontmatter.get("max_tokens", 800))

        heading_match = re.search(r"^#\s+(.+?)\s*$", body, re.MULTILINE)
        name = heading_match.group(1).strip() if heading_match else path.stem

        trigger_desc = _extract_section(body, "触发条件")
        trigger_description = _first_paragraph(trigger_desc)

        instructions = _extract_section(body, "指令")
        if not instructions:
            heading_end = heading_match.end() if heading_match else 0
            instructions = body[heading_end:].strip()

        tools_text = _extract_section(body, "工具")
        tools = [t.strip().lstrip("-* ").strip() for t in tools_text.splitlines() if t.strip()]

        examples_text = _extract_section(body, "示例")
        examples = [e.strip() for e in examples_text.splitlines() if e.strip()]

        skill_id = path.parent.name

        return Skill(
            id=skill_id,
            name=name,
            triggers=triggers,
            trigger_description=trigger_description,
            instructions=instructions,
            tools=tools,
            examples=examples,
            max_tokens=max_tokens,
            source_path=path,
        )
