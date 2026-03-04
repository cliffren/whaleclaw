# WhaleClaw — Agent Coding Guide

**Project**: WhaleClaw — Personal AI Assistant
**Runtime**: Python 3.12 (`miniconda` env: `whaleclaw`)
**Package Manager**: pip + pyproject.toml
**Framework**: FastAPI + uvicorn (async HTTP + WebSocket)

---

## Build/Lint/Test Commands

CRITICAL: Always run Python commands in the `whaleclaw` conda env, never system Python.

```bash
# Install dependencies
conda run -n whaleclaw python -m pip install -e ".[dev]"

# Run tests (all)
conda run -n whaleclaw python -m pytest

# Run single test file
conda run -n whaleclaw python -m pytest tests/test_config/test_schema.py

# Run single test function
conda run -n whaleclaw python -m pytest tests/test_config/test_schema.py::TestGatewayConfig::test_defaults

# Run single test class
conda run -n whaleclaw python -m pytest tests/test_config/test_schema.py::TestGatewayConfig

# Run tests with coverage
conda run -n whaleclaw python -m pytest --cov=whaleclaw --cov-report=term-missing

# Lint (Ruff)
conda run -n whaleclaw python -m ruff check .

# Format (Ruff)
conda run -n whaleclaw python -m ruff format .

# Type check (pyright strict mode)
conda run -n whaleclaw python -m pyright

# Run gateway server
conda run -n whaleclaw python -m whaleclaw gateway run --port 18666 --verbose
```

---

## Code Style

### Imports

```python
# Standard library first
import asyncio
import json
from typing import TYPE_CHECKING

# Third-party next
from pydantic import BaseModel, Field
import pytest

# Local imports last (absolute)
from whaleclaw.config.schema import AgentConfig
from whaleclaw.tools.base import ToolResult
from whaleclaw.utils.log import get_logger

# TYPE_CHECKING for circular import avoidance
if TYPE_CHECKING:
    from whaleclaw.memory.manager import MemoryManager
```

### Formatting

- **Line length**: 100 characters (Ruff)
- **Quotes**: Double quotes for strings
- **Trailing comma**: In multi-line collections
- **Type annotations**: Required on all function signatures

### Types

- **ALWAYS** use type annotations on function parameters and return types
- **NEVER** use `Any` — fix the root cause instead
- **NEVER** use `# type: ignore` without documented justification
- Use `|` for union types: `str | None` (not `Optional[str]`)
- Use modern type syntax: `list[str]` (not `List[str]`)

### Naming

| Element | Convention | Example |
|---------|------------|---------|
| Files | `snake_case.py` | `session_manager.py` |
| Classes | `PascalCase` | `SessionManager` |
| Functions | `snake_case` | `get_session()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES` |
| Private | `_leading_underscore` | `_internal_cache` |
| Product name | **WhaleClaw** (docs/UI), `whaleclaw` (CLI/package) |

---

## Error Handling

- Custom exceptions MUST inherit from `WhaleclawError` (defined in `whaleclaw/types.py`)
- NEVER catch bare `Exception` — catch specific types
- User-facing messages: Chinese (中文); Internal logs: English
- Tool failures: Return `ToolResult(success=False, error="...")`, don't raise

---

## Async Guidelines

- ALL I/O operations use `async/await`
- NEVER use blocking calls in async context (no `time.sleep`, use `asyncio.sleep`)
- Async tests use `@pytest.mark.asyncio` decorator

---

## Testing

- **Framework**: pytest + pytest-asyncio
- **Location**: `tests/` mirror `whaleclaw/` structure
- **Naming**: `test_<module>.py` with `test_<function>()` or `TestClassName`
- **Fixtures**: Defined in `tests/conftest.py` or per-module
- **No real API keys** unless marked `@pytest.mark.live`
- **E2E tests**: Suffix `_e2e`

---

## File Organization

- **Max 500 lines per file** — split if larger
- Each package has `__init__.py` with `__all__` for public API
- Tests mirror source structure: `whaleclaw/config/` → `tests/test_config/`

---

## Comments & Docstrings

- Comments ONLY for non-obvious logic
- NO narrative comments ("import module", "define function")
- Public APIs MUST have Google-style docstrings
- Complex algorithms/trade-offs MUST be commented

---

## Commit Convention

Format: `<scope>: <description>`

Scopes: `gateway`, `agent`, `config`, `cli`, `channels`, `tools`, `sessions`, `plugins`, `skills`, `memory`, `media`, `security`, `evomap`, `docs`, `tests`, `deps`, `ci`

---

## Security

- NEVER commit real credentials (API keys, tokens, phone numbers)
- Use obvious fake data in tests/docs: `sk-test-xxx`, `13800138000`
- Feishu Webhook: MUST verify signature
- WebChat: MUST enable auth (token or password)

---

## Project Structure Overview

```
whaleclaw/
├── config/          # Pydantic v2 config models
├── gateway/         # FastAPI + WebSocket control plane
├── agent/           # Agent loop (message → LLM → tool → reply)
├── providers/       # LLM adapters (Anthropic, OpenAI, DeepSeek, etc.)
├── channels/        # Message channels (WebChat, Feishu)
├── sessions/        # Session management (SQLite persistence)
├── tools/           # Built-in tools (bash, file_*, browser)
├── plugins/         # Plugin system + EvoMap
├── skills/          # Skill discovery & routing
├── memory/          # Memory system (JSON + keyword search)
├── media/           # Media processing (transcribe, vision)
├── security/        # Auth, pairing, sandbox
├── cli/             # Typer CLI commands
└── utils/           # Logging, async helpers, types
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Run gateway | `conda run -n whaleclaw python -m whaleclaw gateway run` |
| Run all tests | `conda run -n whaleclaw python -m pytest` |
| Run single test | `conda run -n whaleclaw python -m pytest tests/test_xxx/test_file.py::test_name` |
| Lint | `conda run -n whaleclaw python -m ruff check .` |
| Format | `conda run -n whaleclaw python -m ruff format .` |
| Type check | `conda run -n whaleclaw python -m pyright` |
| Install deps | `conda run -n whaleclaw python -m pip install -e ".[dev]"` |
