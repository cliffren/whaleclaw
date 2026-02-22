"""Skill routing by keyword matching."""

from __future__ import annotations

from whaleclaw.skills.parser import Skill


class SkillRouter:
    """Route user messages to skills by keyword matching."""

    def route(
        self,
        user_message: str,
        available_skills: list[Skill],
        max_skills: int = 2,
    ) -> list[Skill]:
        """Select top skills by /use command or keyword score."""
        msg = user_message.strip()
        if msg.startswith("/use "):
            skill_id = msg[5:].strip().lower()
            for s in available_skills:
                if s.id.lower() == skill_id:
                    return [s]

        scored = [(self._score(msg, s), s) for s in available_skills]
        scored = [(score, s) for score, s in scored if score > 0]
        scored.sort(key=lambda x: (-x[0], x[1].id))
        return [s for _, s in scored[:max_skills]]

    def _score(self, message: str, skill: Skill) -> float:
        """Return hit_count / total_triggers, 0 if no triggers."""
        if not skill.triggers:
            return 0.0
        lower = message.lower()
        hits = sum(1 for t in skill.triggers if t.lower() in lower)
        return hits / len(skill.triggers)
