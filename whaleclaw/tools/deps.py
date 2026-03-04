"""Auto-install tool dependencies at runtime."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

from whaleclaw.utils.log import get_logger

log = get_logger(__name__)

_PROJECT_PYTHON = Path(__file__).resolve().parents[2] / "python" / "bin" / "python3.12"
_CONDA_ENV_PYTHON = Path.home() / "miniconda3" / "envs" / "whaleclaw" / "bin" / "python"


def _get_pip() -> list[str]:
    conda_prefix = os.environ.get("CONDA_PREFIX", "").strip()
    if conda_prefix:
        conda_python = Path(conda_prefix) / "bin" / "python"
        if conda_python.is_file():
            return [str(conda_python), "-m", "pip"]
    if _CONDA_ENV_PYTHON.is_file():
        return [str(_CONDA_ENV_PYTHON), "-m", "pip"]
    if _PROJECT_PYTHON.is_file():
        return [str(_PROJECT_PYTHON), "-m", "pip"]
    return [sys.executable, "-m", "pip"]


def ensure_package(
    import_name: str,
    pip_name: str | None = None,
    post_install_hook: str | None = None,
) -> bool:
    """Ensure a Python package is importable; install if missing.

    Args:
        import_name: Module name to try importing (e.g. ``playwright``).
        pip_name: Package name for pip (defaults to import_name).
        post_install_hook: Optional shell command to run after install
            (e.g. ``playwright install chromium``).

    Returns:
        True if package is ready (was already installed or just installed).
        False if installation failed.
    """
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        pass

    pkg = pip_name or import_name
    log.info("deps.installing", package=pkg)

    pip_cmd = _get_pip()
    try:
        result = subprocess.run(
            [*pip_cmd, "install", pkg],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            log.warning(
                "deps.install_failed",
                package=pkg,
                stderr=result.stderr[:500],
            )
            return False
        log.info("deps.installed", package=pkg)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        log.warning("deps.install_error", package=pkg, error=str(exc))
        return False

    if post_install_hook:
        try:
            python = pip_cmd[0]
            subprocess.run(
                [python, "-m", *post_install_hook.split()],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except Exception as exc:
            log.warning(
                "deps.post_hook_failed",
                hook=post_install_hook,
                error=str(exc),
            )

    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


TOOL_DEPS: dict[str, dict[str, str | None]] = {
    "playwright": {
        "import_name": "playwright",
        "pip_name": "playwright",
        "post_install_hook": "playwright install chromium",
    },
    "chromadb": {
        "import_name": "chromadb",
        "pip_name": "chromadb",
        "post_install_hook": None,
    },
    "docx": {
        "import_name": "docx",
        "pip_name": "python-docx",
        "post_install_hook": None,
    },
    "openpyxl": {
        "import_name": "openpyxl",
        "pip_name": "openpyxl",
        "post_install_hook": None,
    },
    "reportlab": {
        "import_name": "reportlab",
        "pip_name": "reportlab",
        "post_install_hook": None,
    },
    "pptx": {
        "import_name": "pptx",
        "pip_name": "python-pptx",
        "post_install_hook": None,
    },
}


def ensure_tool_dep(dep_key: str) -> bool:
    """Ensure a known tool dependency is available.

    Args:
        dep_key: Key from ``TOOL_DEPS`` table.

    Returns:
        True if dependency is available.
    """
    entry = TOOL_DEPS.get(dep_key)
    if not entry:
        return ensure_package(dep_key)
    return ensure_package(
        import_name=str(entry["import_name"]),
        pip_name=entry.get("pip_name"),
        post_install_hook=entry.get("post_install_hook"),
    )
