"""Security subsystem — permissions, pairing, sandbox, audit."""

from whaleclaw.security.audit import AuditEvent, AuditLogger
from whaleclaw.security.pairing import AllowListStore, PairingRequest, PairingService
from whaleclaw.security.permissions import PermissionChecker, SecurityPolicy, ToolPermission
from whaleclaw.security.sandbox import DockerSandbox, SandboxConfig, SandboxMode

__all__ = [
    "AllowListStore",
    "AuditEvent",
    "AuditLogger",
    "DockerSandbox",
    "PairingRequest",
    "PairingService",
    "PermissionChecker",
    "SandboxConfig",
    "SandboxMode",
    "SecurityPolicy",
    "ToolPermission",
]
