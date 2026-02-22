"""Pydantic v2 configuration schema for WhaleClaw."""

from __future__ import annotations

from pydantic import BaseModel, Field

from whaleclaw.config.paths import WORKSPACE_DIR


class AuthConfig(BaseModel):
    """Authentication configuration for the Gateway."""

    mode: str = "none"
    password: str | None = None
    token: str | None = None
    jwt_secret: str = "whaleclaw-default-secret"
    jwt_expire_hours: int = 24


class GatewayConfig(BaseModel):
    """Gateway server configuration."""

    port: int = Field(default=18789, ge=1, le=65535)
    bind: str = "127.0.0.1"
    verbose: bool = False
    auth: AuthConfig = Field(default_factory=AuthConfig)


class ProviderModelEntry(BaseModel):
    """A single validated model under a provider (e.g. one NVIDIA NIM model)."""

    id: str
    name: str = ""
    base_url: str | None = None
    verified: bool = False
    thinking: str = "off"


class ProviderConfig(BaseModel):
    """Per-provider configuration."""

    api_key: str | None = None
    base_url: str | None = None
    timeout: int = 120
    configured_models: list[ProviderModelEntry] = Field(default_factory=list)


class ModelsConfig(BaseModel):
    """Configuration for all LLM providers."""

    anthropic: ProviderConfig = Field(default_factory=ProviderConfig)
    openai: ProviderConfig = Field(default_factory=ProviderConfig)
    deepseek: ProviderConfig = Field(default_factory=ProviderConfig)
    qwen: ProviderConfig = Field(default_factory=ProviderConfig)
    zhipu: ProviderConfig = Field(default_factory=ProviderConfig)
    minimax: ProviderConfig = Field(default_factory=ProviderConfig)
    moonshot: ProviderConfig = Field(default_factory=ProviderConfig)
    google: ProviderConfig = Field(default_factory=ProviderConfig)
    nvidia: ProviderConfig = Field(default_factory=ProviderConfig)


class AgentConfig(BaseModel):
    """Agent runtime configuration."""

    model: str = "anthropic/claude-sonnet-4-20250514"
    max_tool_rounds: int = 25
    workspace: str = str(WORKSPACE_DIR)
    thinking_level: str = "off"


class SecurityConfig(BaseModel):
    """Security configuration."""

    sandbox_mode: str = "non-main"
    dm_policy: str = "pairing"
    audit: bool = True


class RoutingRuleConfig(BaseModel):
    """Single routing rule in config."""

    name: str
    priority: int = 0
    match: dict[str, object] = Field(default_factory=dict)
    target: dict[str, object] = Field(default_factory=dict)


class RoutingConfig(BaseModel):
    """Routing configuration."""

    rules: list[RoutingRuleConfig] = Field(default_factory=list)


class WhaleclawConfig(BaseModel):
    """Root configuration model."""

    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    routing: RoutingConfig = Field(default_factory=RoutingConfig)
