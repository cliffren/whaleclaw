"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
import re
import sys
from typing import Protocol

import structlog

_SENSITIVE_QUERY_RE = re.compile(
    r"(?P<key>token|access_token|access_key|ticket)=(?P<value>[^&\s\"']+)",
    re.IGNORECASE,
)


class Logger(Protocol):
    """Minimal logger protocol for basedpyright compatibility.

    structlog.stdlib.BoundLogger methods return Any, which basedpyright
    treats as Unknown.  This protocol gives callers a concrete type.
    """

    def debug(self, event: str | None = None, **kw: object) -> None: ...
    def info(self, event: str | None = None, **kw: object) -> None: ...
    def warning(self, event: str | None = None, **kw: object) -> None: ...
    def error(self, event: str | None = None, **kw: object) -> None: ...
    def critical(self, event: str | None = None, **kw: object) -> None: ...
    def exception(self, event: str | None = None, **kw: object) -> None: ...


def setup_logging(*, verbose: bool = False) -> None:
    """Configure structlog for the application.

    Args:
        verbose: When *True*, set log level to DEBUG; otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
        force=True,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        ],
    )

    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(formatter)

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.addFilter(_SensitiveAccessLogFilter())
    lark_logger = logging.getLogger("Lark")
    lark_logger.addFilter(_SensitiveAccessLogFilter())
    for handler in lark_logger.handlers:
        handler.addFilter(_SensitiveAccessLogFilter())

    if not verbose:
        # Reduce noisy transport logs in normal mode.
        uvicorn_access_logger.setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("websockets").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Logger:
    """Return a bound structlog logger."""
    return structlog.stdlib.get_logger(name)  # type: ignore[return-value]


def _mask_sensitive_query_values(text: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = match.group("key")
        value = match.group("value")
        masked = "***" if len(value) <= 8 else f"{value[:4]}***{value[-4:]}"
        return f"{key}={masked}"

    return _SENSITIVE_QUERY_RE.sub(_replace, text)


class _SensitiveAccessLogFilter(logging.Filter):
    """Mask sensitive query values in uvicorn access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        masked = _mask_sensitive_query_values(msg)
        if masked != msg:
            record.msg = masked
            record.args = ()
        return True
