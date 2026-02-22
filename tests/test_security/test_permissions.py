"""Tests for whaleclaw.security.permissions."""

from __future__ import annotations

from whaleclaw.security.permissions import (
    PermissionChecker,
    SecurityPolicy,
    ToolPermission,
)


class TestPermissionChecker:
    def test_check_tool_allowed_all(self) -> None:
        policy = SecurityPolicy(tools=ToolPermission(allow=["*"], deny=[]))
        assert PermissionChecker.check_tool("file_read", policy) is True
        assert PermissionChecker.check_tool("bash", policy) is True

    def test_check_tool_denied(self) -> None:
        policy = SecurityPolicy(tools=ToolPermission(allow=["*"], deny=["bash"]))
        assert PermissionChecker.check_tool("file_read", policy) is True
        assert PermissionChecker.check_tool("bash", policy) is False

    def test_check_tool_explicit_allow(self) -> None:
        policy = SecurityPolicy(
            tools=ToolPermission(allow=["file_read", "file_write"], deny=[]),
        )
        assert PermissionChecker.check_tool("file_read", policy) is True
        assert PermissionChecker.check_tool("file_write", policy) is True
        assert PermissionChecker.check_tool("bash", policy) is False

    def test_check_path_denied(self) -> None:
        policy = SecurityPolicy()
        assert PermissionChecker.check_path("/etc/passwd", policy) is False
        assert PermissionChecker.check_path("/var/log/syslog", policy) is False
        assert PermissionChecker.check_path("~/.ssh/id_rsa", policy) is False

    def test_check_command_dangerous(self) -> None:
        policy = SecurityPolicy()
        assert PermissionChecker.check_command("rm -rf /", policy) is False
        assert PermissionChecker.check_command("mkfs.ext4 /dev/sda", policy) is False
        assert PermissionChecker.check_command("dd if=/dev/zero of=/dev/sda", policy) is False

    def test_check_command_safe(self) -> None:
        policy = SecurityPolicy()
        assert PermissionChecker.check_command("ls -la", policy) is True
        assert PermissionChecker.check_command("python --version", policy) is True
        assert PermissionChecker.check_command("echo hello", policy) is True
