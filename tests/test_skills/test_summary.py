"""Tests for AgentsSummaryBuilder."""

from __future__ import annotations

from whaleclaw.skills.summary import AgentsSummaryBuilder


def test_build_summary_shorter_than_original(tmp_path) -> None:
    agents_md = tmp_path / "AGENTS.md"
    long_content = """# WhaleClaw 项目指南

这是非常长的介绍段落，包含许多冗余的说明文字。我们需要确保
摘要生成器能够正确提取核心内容并生成更短的版本。这里继续
添加更多文字以达到足够的长度。

## 核心规则

第一段核心规则描述。

第二段更多的规则说明，用于测试多段落处理。

## 安全约束

安全相关的详细描述。包括不应提交真实凭证、默认 DM 策略等。

## 代码示例

```python
# 这里是一大段代码示例
def example():
    pass
```
"""
    agents_md.write_text(long_content, encoding="utf-8")

    builder = AgentsSummaryBuilder()
    summary = builder.build(agents_md)

    assert len(summary) < len(long_content)
    assert "# WhaleClaw" in summary or "WhaleClaw" in summary


def test_build_empty_for_missing_file(tmp_path) -> None:
    builder = AgentsSummaryBuilder()
    result = builder.build(tmp_path / "nonexistent.md")
    assert result == ""
