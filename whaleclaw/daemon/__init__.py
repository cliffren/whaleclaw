"""Daemon service management — launchd (macOS) and systemd (Linux)."""

from whaleclaw.daemon.manager import DaemonManager, ServiceStatus

__all__ = ["DaemonManager", "ServiceStatus"]
