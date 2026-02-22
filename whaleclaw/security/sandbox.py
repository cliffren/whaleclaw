"""Docker sandbox for tool execution isolation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SandboxMode(StrEnum):
    """When to apply sandbox: never, non-main sessions only, or all."""

    NONE = "none"
    NON_MAIN = "non-main"
    ALL = "all"


class SandboxConfig(BaseModel):
    """Docker sandbox configuration."""

    image: str = "python:3.12-slim"
    memory_limit: str = "256m"
    cpu_limit: float = 1.0
    network: bool = False
    timeout: int = 60
    volumes: dict[str, str] = Field(default_factory=dict)


class SandboxInstance(BaseModel):
    """Running sandbox container reference."""

    container_id: str
    session_id: str


class SandboxResult(BaseModel):
    """Result of a command execution in sandbox."""

    exit_code: int
    stdout: str
    stderr: str


class DockerSandbox:
    """Docker-based sandbox for isolated command execution (stub)."""

    async def create(self, session_id: str, config: SandboxConfig) -> SandboxInstance:
        """Create a sandbox container for the session (stub)."""
        return SandboxInstance(
            container_id=f"stub-{session_id}",
            session_id=session_id,
        )

    async def execute(
        self,
        instance: SandboxInstance,
        command: str,
        timeout: int = 30,
    ) -> SandboxResult:
        """Execute command in sandbox (stub)."""
        _ = instance
        _ = command
        _ = timeout
        return SandboxResult(
            exit_code=-1,
            stdout="",
            stderr="Docker 沙箱未安装",
        )

    async def destroy(self, instance: SandboxInstance) -> None:
        """Destroy sandbox container (stub)."""
        _ = instance
