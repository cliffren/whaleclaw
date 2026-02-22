"""SSH reverse tunnel management."""

from __future__ import annotations

import asyncio
from typing import Any

from whaleclaw.utils.log import get_logger

logger = get_logger(__name__)


class SSHTunnel:
    """Start/stop SSH reverse tunnel (-R remote_port:localhost:local_port)."""

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process[Any] | None = None

    async def start(self, remote_host: str, remote_port: int, local_port: int) -> None:
        """Start ssh -R {remote_port}:localhost:{local_port} {remote_host} as subprocess."""
        cmd = [
            "ssh",
            "-N",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "ServerAliveInterval=60",
            "-R",
            f"{remote_port}:localhost:{local_port}",
            remote_host,
        ]
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        logger.info("ssh_tunnel_started", remote_host=remote_host, remote_port=remote_port)

    async def stop(self) -> None:
        """Terminate process if running."""
        if self._process is not None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                self._process.kill()
            self._process = None

    def is_running(self) -> bool:
        """Return True if tunnel process is alive."""
        if self._process is None:
            return False
        return self._process.returncode is None
