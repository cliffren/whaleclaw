"""WhaleClaw skills system: discovery, routing, prompt formatting."""

from __future__ import annotations

from whaleclaw.skills.manager import SkillManager
from whaleclaw.skills.parser import Skill, SkillParser
from whaleclaw.skills.router import SkillRouter

__all__ = ["Skill", "SkillManager", "SkillParser", "SkillRouter"]
