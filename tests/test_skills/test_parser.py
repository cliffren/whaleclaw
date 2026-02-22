"""Tests for SkillParser."""

from __future__ import annotations

from whaleclaw.skills.parser import SkillParser


def test_parse_frontmatter_and_fields(tmp_path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        """---
triggers: ["浏览器", "打开网页", "screenshot"]
max_tokens: 800
---
# 浏览器控制

## 触发条件
用户请求打开网页、截图。

## 指令
使用 browser 工具操作网页。

## 工具
- browser

## 示例
用户: 打开 example.com
Agent: [navigate] -> [screenshot]
""",
        encoding="utf-8",
    )

    parser = SkillParser()
    skill = parser.parse(skill_md)

    assert skill.triggers == ["浏览器", "打开网页", "screenshot"]
    assert skill.max_tokens == 800
    assert skill.name == "浏览器控制"
    assert "browser" in skill.tools
    assert skill.trigger_description
    assert "使用 browser" in skill.instructions
