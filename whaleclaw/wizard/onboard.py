"""Onboard wizard for first-time setup."""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable

from whaleclaw.wizard.steps import DEFAULT_STEPS, WizardState, WizardStep


class OnboardWizard:
    """Interactive setup wizard."""

    def __init__(self) -> None:
        self.state = WizardState(steps=[s.model_copy() for s in DEFAULT_STEPS])

    async def run(self) -> WizardState:
        """Run all steps and return final state."""
        for i, step in enumerate(self.state.steps):
            self.state.current_step = i
            completed = await self._run_step(step)
            if completed:
                step.completed = True
            else:
                step.skipped = True
        return self.state

    async def _run_step(self, step: WizardStep) -> bool:
        """Dispatch to step handler. Returns True if completed, False if skipped."""
        handlers: dict[str, Callable[[], Awaitable[bool]]] = {
            "check_python": self._check_python,
            "configure_model": self._configure_model,
            "configure_channel": self._configure_channel,
            "configure_security": self._configure_security,
            "configure_evomap": self._configure_evomap,
            "install_daemon": self._install_daemon,
            "test_message": self._test_message,
        }
        handler = handlers.get(step.id)
        if handler:
            return await handler()
        return False

    async def _check_python(self) -> bool:
        return sys.version_info >= (3, 12)

    async def _configure_model(self) -> bool:
        return True

    async def _configure_channel(self) -> bool:
        return True

    async def _configure_security(self) -> bool:
        return True

    async def _configure_evomap(self) -> bool:
        return False

    async def _install_daemon(self) -> bool:
        return False

    async def _test_message(self) -> bool:
        return True

    def progress(self) -> tuple[int, int]:
        """Return (completed_count, total_count)."""
        total = len(self.state.steps)
        completed = sum(1 for s in self.state.steps if s.completed)
        return completed, total
