"""Global type definitions for WhaleClaw."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

StreamCallback = Callable[[str], Awaitable[None]]


class WhaleclawError(Exception):
    """Base exception for all WhaleClaw errors."""


class ConfigError(WhaleclawError):
    """Configuration loading or validation error."""


class ProviderError(WhaleclawError):
    """LLM provider communication error."""


class ProviderAuthError(ProviderError):
    """Missing or invalid API key."""


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded."""


class GatewayError(WhaleclawError):
    """Gateway runtime error."""


class AuthError(WhaleclawError):
    """Authentication or authorization error."""
