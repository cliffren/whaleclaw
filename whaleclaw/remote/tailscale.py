"""Tailscale serve/funnel management."""

from __future__ import annotations

import asyncio

from whaleclaw.utils.log import get_logger

logger = get_logger(__name__)


class TailscaleManager:
    """Manage Tailscale serve/funnel for remote access."""

    async def setup_serve(self, port: int) -> str:
        """Run `tailscale serve --bg https+insecure://localhost:{port}` via subprocess."""
        cmd = ["tailscale", "serve", "--bg", f"https+insecure://localhost:{port}"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode(errors="replace").strip()
            err = stderr.decode(errors="replace").strip()
            if proc.returncode != 0:
                return err or out or f"tailscale serve 失败 (exit={proc.returncode})"
            return out or f"已启动 serve，端口 {port}"
        except FileNotFoundError:
            return "Tailscale 未安装"
        except OSError as exc:
            return str(exc)

    async def setup_funnel(self, port: int) -> str:
        """Run `tailscale funnel --bg {port}` via subprocess."""
        cmd = ["tailscale", "funnel", "--bg", str(port)]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode(errors="replace").strip()
            err = stderr.decode(errors="replace").strip()
            if proc.returncode != 0:
                return err or out or f"tailscale funnel 失败 (exit={proc.returncode})"
            return out or f"已启动 funnel，端口 {port}"
        except FileNotFoundError:
            return "Tailscale 未安装"
        except OSError as exc:
            return str(exc)

    async def teardown(self) -> None:
        """Run `tailscale serve --https=443 off`."""
        cmd = ["tailscale", "serve", "--https=443", "off"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except (FileNotFoundError, OSError) as exc:
            logger.warning("tailscale teardown failed", exc_info=exc)

    async def status(self) -> str:
        """Run `tailscale status --json`, return output or error message."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "tailscale",
                "status",
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            out = stdout.decode(errors="replace")
            err = stderr.decode(errors="replace")
            if proc.returncode != 0:
                return err or out or f"tailscale status 失败 (exit={proc.returncode})"
            return out
        except FileNotFoundError:
            return "Tailscale 未安装"
        except OSError as exc:
            return str(exc)
