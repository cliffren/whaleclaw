"""Tests for ConversationSummarizer."""

from __future__ import annotations

import pytest

from whaleclaw.memory.summary import ConversationSummarizer


@pytest.mark.asyncio
async def test_summarize() -> None:
    summarizer = ConversationSummarizer()
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你的？"},
        {"role": "user", "content": "介绍一下 Rust"},
        {"role": "assistant", "content": "Rust 是一门系统编程语言..."},
    ]
    result = await summarizer.summarize(messages)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "你好" in result or "Rust" in result


@pytest.mark.asyncio
async def test_extract_facts() -> None:
    summarizer = ConversationSummarizer()
    messages = [
        {"role": "user", "content": "我最喜欢的编程语言是 Rust"},
        {"role": "user", "content": "我 prefer Python 做数据分析"},
        {"role": "user", "content": "name = Alice"},
    ]
    facts = await summarizer.extract_facts(messages)
    assert isinstance(facts, list)
    assert len(facts) >= 1
    fact_strs = " ".join(facts)
    assert "Rust" in fact_strs or "Python" in fact_strs or "Alice" in fact_strs
