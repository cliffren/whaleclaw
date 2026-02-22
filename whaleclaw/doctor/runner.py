"""Doctor runner — runs all health checks and formats report."""

from __future__ import annotations

from whaleclaw.doctor.checks import (
    CheckResult,
    ConfigFileCheck,
    DatabaseCheck,
    DiskSpaceCheck,
    HealthCheck,
    PortCheck,
    PythonVersionCheck,
)


class Doctor:
    """Health check runner."""

    DEFAULT_CHECKS: tuple[HealthCheck, ...] = (
        PythonVersionCheck(),
        ConfigFileCheck(),
        PortCheck(),
        DatabaseCheck(),
        DiskSpaceCheck(),
    )

    def __init__(self, checks: list[HealthCheck] | None = None) -> None:
        self._checks = list(checks) if checks is not None else list(self.DEFAULT_CHECKS)

    async def run_all(self) -> list[CheckResult]:
        """Run all checks and collect results."""
        results: list[CheckResult] = []
        for check in self._checks:
            result = await check.check()
            results.append(result)
        return results

    def format_report(self, results: list[CheckResult]) -> str:
        """Format check results as a readable report."""
        ok = sum(1 for r in results if r.status == "ok")
        warning = sum(1 for r in results if r.status == "warning")
        error = sum(1 for r in results if r.status == "error")

        icons = {"ok": "✅", "warning": "⚠️", "error": "❌"}
        lines = ["WhaleClaw Doctor", "━" * 35, ""]
        for r in results:
            lines.append(f"{icons[r.status]} {r.name}: {r.message}")
        lines.append("")
        lines.append("━" * 35)
        counts = []
        if ok:
            counts.append(f"✅ {ok} 通过")
        if warning:
            counts.append(f"⚠️ {warning} 警告")
        if error:
            counts.append(f"❌ {error} 错误")
        lines.append("  ".join(counts))
        return "\n".join(lines)
