"""Agent main loop — message -> LLM -> tool -> reply (multi-turn).

The loop is provider-agnostic.  Tool invocation follows a single code
path regardless of whether the provider supports native ``tools`` API:

* **Native mode** — tool schemas are passed via ``tools=`` parameter;
  the provider returns structured ``ToolCall`` objects in the response.
* **Fallback mode** — tool descriptions are injected into the system
  prompt; the LLM outputs a JSON block which the loop parses.
"""

from __future__ import annotations

import json
import re

from whaleclaw.agent.context import OnToolCall, OnToolResult
from whaleclaw.agent.prompt import PromptAssembler
from whaleclaw.config.schema import WhaleclawConfig
from whaleclaw.providers.base import AgentResponse, ImageContent, Message, ToolCall
from whaleclaw.providers.router import ModelRouter
from whaleclaw.sessions.context_window import ContextWindow
from whaleclaw.sessions.manager import Session
from whaleclaw.tools.base import ToolResult
from whaleclaw.tools.registry import ToolRegistry
from whaleclaw.types import StreamCallback
from whaleclaw.utils.log import get_logger

log = get_logger(__name__)

_assembler = PromptAssembler()
_context_window = ContextWindow()

_MAX_TOOL_ROUNDS = 8

_IMG_MD_RE = re.compile(r"!\[([^\]]*)\]\((/[^)]+)\)")

_TOOL_HINTS: dict[str, str] = {
    "browser": "搜索相关资料",
    "bash": "执行命令",
    "file_write": "生成文件",
    "file_read": "读取文件",
    "file_edit": "编辑文件",
    "skill": "查找技能",
}


def _make_plan_hint(tool_names: list[str], user_msg: str) -> str:
    """Generate a brief plan message when LLM jumps straight to tool calls."""
    steps = []
    seen: set[str] = set()
    for name in tool_names:
        if name in seen:
            continue
        seen.add(name)
        steps.append(_TOOL_HINTS.get(name, f"调用 {name}"))
    plan = "、".join(steps)
    return f"好的，我来处理。正在{plan}…\n\n"


def _fix_image_paths(text: str, known_paths: list[str] | None = None) -> str:
    """Validate image paths in markdown; fix fabricated paths using known real ones."""
    from pathlib import Path

    unused_real = list(known_paths or [])

    def _replace(m: re.Match[str]) -> str:
        alt, raw_path = m.group(1), m.group(2)
        fp = Path(raw_path)
        if fp.is_file():
            return m.group(0)

        # Priority 1: match from tool-returned real paths (by hash or order)
        for i, real in enumerate(unused_real):
            rp = Path(real)
            if rp.is_file():
                unused_real.pop(i)
                log.info("fix_image_path.known", original=raw_path, found=real)
                return f"![{alt}]({real})"

        # Priority 2: fuzzy match by hash suffix
        stem = fp.stem
        hash_m = re.search(r"_([0-9a-f]{6,8})$", stem)
        if hash_m and fp.parent.is_dir():
            suffix = hash_m.group(0) + fp.suffix
            for candidate in fp.parent.iterdir():
                if candidate.name.endswith(suffix) and candidate.is_file():
                    log.info("fix_image_path.fuzzy", original=raw_path, found=str(candidate))
                    return f"![{alt}]({candidate})"

        # Priority 3: most recent file in same directory
        if fp.parent.is_dir():
            files = sorted(
                (f for f in fp.parent.iterdir() if f.is_file() and f.suffix == fp.suffix),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if files:
                best = files[0]
                log.info("fix_image_path.recent", original=raw_path, found=str(best))
                return f"![{alt}]({best})"

        log.warning("fix_image_path.removed", path=raw_path)
        return f"[图片未找到: {alt}]"

    return _IMG_MD_RE.sub(_replace, text)


def create_default_registry(
    session_manager: object | None = None,
    cron_scheduler: object | None = None,
) -> ToolRegistry:
    """Create a ToolRegistry with all built-in tools registered.

    Args:
        session_manager: Optional SessionManager for session tools.
        cron_scheduler: Optional CronScheduler for cron/reminder tools.
    """
    from whaleclaw.tools.bash import BashTool
    from whaleclaw.tools.browser import BrowserTool
    from whaleclaw.tools.file_edit import FileEditTool
    from whaleclaw.tools.file_read import FileReadTool
    from whaleclaw.tools.file_write import FileWriteTool

    registry = ToolRegistry()
    registry.register(BashTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileEditTool())
    registry.register(BrowserTool())

    if session_manager is not None:
        from whaleclaw.tools.sessions import (
            SessionsHistoryTool,
            SessionsListTool,
            SessionsSendTool,
        )

        registry.register(SessionsListTool(session_manager))
        registry.register(SessionsHistoryTool(session_manager))
        registry.register(SessionsSendTool(session_manager))

    if cron_scheduler is not None:
        from whaleclaw.tools.cron_tool import CronManageTool
        from whaleclaw.tools.reminder import ReminderTool

        registry.register(CronManageTool(cron_scheduler))
        registry.register(ReminderTool(cron_scheduler))

    from whaleclaw.skills.manager import SkillManager
    from whaleclaw.tools.skill_tool import SkillManageTool

    registry.register(SkillManageTool(SkillManager()))

    return registry


def _parse_fallback_tool_calls(text: str) -> list[ToolCall]:
    """Extract tool calls from LLM text output (fallback mode).

    Looks for JSON objects with ``"tool"`` key, either fenced or bare.
    """
    calls: list[ToolCall] = []

    fenced = re.findall(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    candidates: list[str] = list(fenced)

    if not candidates:
        for match in re.finditer(r"\{[^{}]*\"tool\"[^{}]*\{[^}]*\}[^}]*\}", text):
            candidates.append(match.group(0))
        for match in re.finditer(r"\{[^{}]*\"tool\"[^{}]*\}", text):
            candidates.append(match.group(0))

    for raw in candidates:
        raw = raw.strip()
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        name = obj.get("tool", "")
        args = obj.get("arguments", {})
        if name and isinstance(args, dict):
            calls.append(ToolCall(
                id=f"fallback_{len(calls)}",
                name=name,
                arguments=args,
            ))

    return calls


def _strip_tool_json(text: str) -> str:
    """Remove tool-call JSON blocks from text for clean display."""
    cleaned = re.sub(
        r'```(?:json)?\s*\n?\s*\{[^`]*"tool"\s*:[^`]*\}\s*\n?\s*```',
        "",
        text,
        flags=re.DOTALL,
    )
    cleaned = re.sub(
        r'\{\s*"tool"\s*:\s*"[^"]*"[^}]*\}',
        "",
        cleaned,
    )
    return cleaned.strip()


async def _execute_tool(
    registry: ToolRegistry,
    tc: ToolCall,
    on_tool_call: OnToolCall | None,
    on_tool_result: OnToolResult | None,
) -> tuple[str, ToolResult]:
    """Execute a single tool call and return (tool_call_id, result)."""
    if on_tool_call:
        await on_tool_call(tc.name, tc.arguments)

    tool = registry.get(tc.name)
    if tool is None:
        result = ToolResult(
            success=False,
            output="",
            error=f"未知工具: {tc.name}",
        )
    else:
        try:
            result = await tool.execute(**tc.arguments)
        except Exception as exc:
            result = ToolResult(success=False, output="", error=str(exc))

    if on_tool_result:
        await on_tool_result(tc.name, result)

    return tc.id, result


def _format_tool_output(result: ToolResult) -> str:
    """Format ToolResult into a string for LLM consumption."""
    if result.success:
        return result.output or "(empty output)"
    return f"[ERROR] {result.error or 'unknown error'}\n{result.output}".strip()


async def run_agent(
    message: str,
    session_id: str,
    config: WhaleclawConfig,
    on_stream: StreamCallback | None = None,
    *,
    session: Session | None = None,
    router: ModelRouter | None = None,
    registry: ToolRegistry | None = None,
    on_tool_call: OnToolCall | None = None,
    on_tool_result: OnToolResult | None = None,
    images: list[ImageContent] | None = None,
) -> str:
    """Run the Agent loop with tool support and multi-turn context.

    The loop is provider-agnostic:
    1. Check if provider supports native tools API
    2. If yes  -> pass schemas via ``tools=``; parse structured tool_calls
    3. If no   -> inject tool descriptions into system prompt; parse JSON text
    4. Execute tools, append results, loop (max _MAX_TOOL_ROUNDS)
    5. Return final text reply
    """
    model_id = session.model if session else config.agent.model
    if router is None:
        router = ModelRouter(config.models)
    if registry is None:
        registry = create_default_registry()

    native_tools = router.supports_native_tools(model_id)

    tool_schemas = registry.to_llm_schemas() if native_tools else None
    fallback_text = "" if native_tools else registry.to_prompt_fallback()

    system_messages = _assembler.build(
        config, message, tool_fallback_text=fallback_text
    )

    conversation: list[Message] = []
    if session:
        conversation = list(session.messages)
    conversation.append(Message(role="user", content=message, images=images))

    budget = _context_window.compute_budget(
        model_id.split("/", 1)[-1] if "/" in model_id else model_id
    )

    log.info(
        "agent.run",
        model=model_id,
        session_id=session_id,
        native_tools=native_tools,
    )

    final_text_parts: list[str] = []
    real_image_paths: list[str] = []
    total_input = 0
    total_output = 0
    announced_plan = False

    for round_idx in range(_MAX_TOOL_ROUNDS):
        all_messages = _context_window.trim(
            [*system_messages, *conversation], budget
        )

        response: AgentResponse = await router.chat(
            model_id,
            all_messages,
            tools=tool_schemas or None,
            on_stream=on_stream,
        )

        total_input += response.input_tokens
        total_output += response.output_tokens

        tool_calls = response.tool_calls
        if not tool_calls and not native_tools and response.content:
            tool_calls = _parse_fallback_tool_calls(response.content)

        content = response.content or ""
        if content:
            if tool_calls and not native_tools:
                clean = _strip_tool_json(content)
                if clean:
                    final_text_parts.append(clean)
            else:
                final_text_parts.append(content)

        if not tool_calls:
            break

        if not announced_plan and on_stream:
            announced_plan = True
            has_text = content.strip() if content else ""
            if not has_text:
                tool_names = [tc.name for tc in tool_calls]
                plan = _make_plan_hint(tool_names, message)
                await on_stream(plan)

        log.info(
            "agent.tool_calls",
            round=round_idx,
            count=len(tool_calls),
            tools=[tc.name for tc in tool_calls],
        )

        assistant_msg = Message(
            role="assistant",
            content=response.content or "",
            tool_calls=tool_calls if native_tools else None,
        )
        conversation.append(assistant_msg)

        for tc in tool_calls:
            tc_id, result = await _execute_tool(
                registry, tc, on_tool_call, on_tool_result
            )

            if result.success and result.output:
                for path_match in re.finditer(
                    r"(/[^\s]+\.(?:jpg|jpeg|png|gif|webp))", result.output
                ):
                    real_image_paths.append(path_match.group(1))

            if native_tools:
                tool_msg = Message(
                    role="tool",
                    content=_format_tool_output(result),
                    tool_call_id=tc_id,
                )
            else:
                tool_msg = Message(
                    role="user",
                    content=(
                        f"[工具 {tc.name} 执行结果]\n"
                        f"{_format_tool_output(result)}"
                    ),
                )
            conversation.append(tool_msg)
            log.debug(
                "agent.tool_result",
                tool=tc.name,
                success=result.success,
                output_len=len(result.output),
            )

        final_text_parts.clear()
    else:
        log.warning(
            "agent.max_tool_rounds",
            session_id=session_id,
            rounds=_MAX_TOOL_ROUNDS,
        )

    final_text = "".join(final_text_parts)
    final_text = _fix_image_paths(final_text, real_image_paths)

    log.info(
        "agent.done",
        model=model_id,
        input_tokens=total_input,
        output_tokens=total_output,
        session_id=session_id,
    )

    return final_text
