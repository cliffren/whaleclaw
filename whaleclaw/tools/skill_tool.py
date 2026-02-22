"""Skill management tool - install/uninstall/list skills at runtime."""

from __future__ import annotations

import httpx

from whaleclaw.skills.manager import SkillManager
from whaleclaw.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)


class SkillManageTool(Tool):
    """Agent-callable tool for managing skills."""

    def __init__(self, skill_manager: SkillManager) -> None:
        self._mgr = skill_manager

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="skill",
            description=(
                "Manage skills: list installed, search local+GitHub for new skills, "
                "install from GitHub (user/repo/path), or uninstall by id. "
                "Use search to find better skills when current ones aren't good enough."
            ),
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action: list, install, uninstall, search.",
                    enum=["list", "install", "uninstall", "search"],
                ),
                ToolParameter(
                    name="source",
                    type="string",
                    description=(
                        "For install: GitHub shorthand (user/repo/path), "
                        "URL, or local path. "
                        "For uninstall: skill id."
                    ),
                    required=False,
                ),
                ToolParameter(
                    name="query",
                    type="string",
                    description="For search: keyword to match against available skills.",
                    required=False,
                ),
            ],
        )

    async def execute(self, **kwargs: object) -> ToolResult:
        action = str(kwargs.get("action", "")).lower()

        if action == "list":
            return await self._list()
        if action == "install":
            source = str(kwargs.get("source", "")) if kwargs.get("source") else None
            if not source:
                return ToolResult(
                    success=False, output="", error="install 需要 source 参数"
                )
            return await self._install(source)
        if action == "uninstall":
            source = str(kwargs.get("source", "")) if kwargs.get("source") else None
            if not source:
                return ToolResult(
                    success=False, output="", error="uninstall 需要 source (skill_id)"
                )
            return await self._uninstall(source)
        if action == "search":
            query = str(kwargs.get("query", "")) if kwargs.get("query") else None
            return await self._search(query)
        return ToolResult(success=False, output="", error=f"未知操作: {action}")

    async def _list(self) -> ToolResult:
        all_skills = self._mgr.discover()
        installed = self._mgr.list_installed()
        installed_ids = {s.id for s in installed}
        lines: list[str] = []
        for s in all_skills:
            tag = "[已安装]" if s.id in installed_ids else "[内置]"
            triggers = ", ".join(s.triggers[:5]) if s.triggers else "无"
            lines.append(f"- {s.id} {tag}: {s.name} (触发词: {triggers})")
        return ToolResult(
            success=True,
            output="\n".join(lines) if lines else "无可用技能",
        )

    async def _install(self, source: str) -> ToolResult:
        try:
            skill = self._mgr.install(source)
            return ToolResult(
                success=True,
                output=(
                    f"技能已安装: {skill.id} ({skill.name})\n"
                    f"触发词: {', '.join(skill.triggers) or '无'}"
                ),
            )
        except Exception as exc:
            return ToolResult(success=False, output="", error=str(exc))

    async def _uninstall(self, skill_id: str) -> ToolResult:
        removed = self._mgr.uninstall(skill_id)
        if removed:
            return ToolResult(success=True, output=f"已卸载技能: {skill_id}")
        return ToolResult(
            success=False,
            output="",
            error=f"技能未找到: {skill_id}",
        )

    async def _search(self, query: str | None) -> ToolResult:
        all_skills = self._mgr.discover()
        if not query:
            lines = [f"- {s.id}: {s.name}" for s in all_skills]
            return ToolResult(
                success=True, output="\n".join(lines) if lines else "无可用技能"
            )
        q = query.lower()
        matched = [
            s
            for s in all_skills
            if q in s.name.lower()
            or q in s.id.lower()
            or any(q in t.lower() for t in s.triggers)
        ]

        lines: list[str] = []
        if matched:
            lines.append("== 本地已有 ==")
            for s in matched:
                lines.append(f"- {s.id}: {s.name} (触发词: {', '.join(s.triggers[:5])})")

        online = await self._search_github(query)
        if online:
            lines.append("\n== GitHub 在线 Skill（可用 skill install 安装）==")
            lines.extend(online)

        if not lines:
            return ToolResult(
                success=True,
                output=f"未找到匹配 '{query}' 的技能。\n"
                       f"你可以用 browser 工具去 GitHub 搜索更多: "
                       f"https://github.com/search?q=SKILL.md+{query}&type=code",
            )
        return ToolResult(success=True, output="\n".join(lines))

    async def _search_github(self, query: str | None) -> list[str]:
        """Search GitHub for repos containing SKILL.md related to query."""
        if not query:
            return []
        try:
            params = {
                "q": f"agent skill SKILL.md {query}",
                "sort": "stars",
                "per_page": "8",
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params=params,
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                if resp.status_code != 200:
                    log.debug("skill.github_search_http_error", status=resp.status_code)
                    return []
                items = resp.json().get("items", [])
                results: list[str] = []
                for item in items:
                    repo = item.get("full_name", "")
                    stars = item.get("stargazers_count", 0)
                    desc = (item.get("description") or "")[:80]
                    if not repo:
                        continue
                    results.append(
                        f"- {repo} ⭐{stars} — {desc}\n"
                        f"  安装: skill(action=\"install\", source=\"{repo}\")"
                    )
                return results[:5]
        except Exception as exc:
            log.debug("skill.github_search_failed", error=str(exc))
            return []
