"""Wizard step definitions and state."""

from __future__ import annotations

from pydantic import BaseModel


class WizardStep(BaseModel):
    """Single wizard step."""

    id: str
    title: str
    description: str
    completed: bool = False
    skipped: bool = False


class WizardState(BaseModel):
    """Wizard execution state."""

    steps: list[WizardStep] = []
    current_step: int = 0
    config: dict[str, object] = {}


def _make_steps() -> list[WizardStep]:
    return [
        WizardStep(id="check_python", title="检查 Python 环境", description=""),
        WizardStep(id="configure_model", title="配置 AI 模型", description=""),
        WizardStep(id="configure_channel", title="配置消息渠道", description=""),
        WizardStep(id="configure_security", title="安全设置", description=""),
        WizardStep(id="configure_evomap", title="EvoMap 设置 (可选)", description=""),
        WizardStep(id="install_daemon", title="安装守护进程 (可选)", description=""),
        WizardStep(id="test_message", title="发送测试消息", description=""),
    ]


DEFAULT_STEPS: list[WizardStep] = _make_steps()
