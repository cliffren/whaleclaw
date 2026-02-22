"""Tests for OnboardWizard."""

from __future__ import annotations

import pytest

from whaleclaw.wizard.onboard import OnboardWizard


@pytest.mark.asyncio
async def test_wizard_run() -> None:
    """Create wizard, run, verify all steps processed."""
    wizard = OnboardWizard()
    state = await wizard.run()
    assert len(state.steps) == 7
    completed = [s for s in state.steps if s.completed]
    skipped = [s for s in state.steps if s.skipped]
    assert len(completed) + len(skipped) == 7
    step_ids = [s.id for s in state.steps]
    assert step_ids == [
        "check_python",
        "configure_model",
        "configure_channel",
        "configure_security",
        "configure_evomap",
        "install_daemon",
        "test_message",
    ]


@pytest.mark.asyncio
async def test_wizard_progress() -> None:
    """Verify progress tuple (completed_count, total_count)."""
    wizard = OnboardWizard()
    before = wizard.progress()
    assert before == (0, 7)
    await wizard.run()
    after = wizard.progress()
    assert after[0] + sum(1 for s in wizard.state.steps if s.skipped) == 7
    assert after[1] == 7


@pytest.mark.asyncio
async def test_check_python_passes() -> None:
    """Verify _check_python returns True on Python 3.12+."""
    wizard = OnboardWizard()
    result = await wizard._check_python()
    assert result is True
