# Phase 5: 插件 + 技能系统

## 目标

构建可扩展的插件架构和技能系统:
1. 插件 SDK — 第三方可开发渠道/工具/钩子插件
2. 插件加载 — 动态发现和加载 Python 插件包
3. 技能系统 — SKILL.md 格式的 Agent 技能
4. 工作区 — Agent 工作目录 + 注入文件
5. 钩子系统 — 消息处理管道中的扩展点
6. 内置高级工具 — 浏览器控制 (Playwright)、代码沙箱

## 前置条件

- Phase 1 ~ 4 全部完成

---

## 1. 插件 SDK

### 1.1 插件 API — `whaleclaw/plugins/sdk.py`

```python
class WhaleclawPluginApi:
    """插件与 WhaleClaw 核心交互的 API"""

    @property
    def runtime(self) -> WhaleclawRuntime:
        """访问运行时 (配置/日志/事件总线)"""

    def register_channel(self, channel: ChannelPlugin) -> None:
        """注册消息渠道"""

    def register_tool(self, tool: Tool) -> None:
        """注册工具"""

    def register_hook(self, hook_name: str, callback: HookCallback) -> None:
        """注册钩子"""

    def register_command(self, command: str, handler: CommandHandler) -> None:
        """注册聊天命令"""

    def get_config(self, key: str, default: Any = None) -> Any:
        """读取插件配置"""

    def get_secret(self, key: str) -> str | None:
        """读取插件凭证"""
```

### 1.2 插件描述文件

每个插件包含一个 `whaleclaw_plugin.json`:

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "description": "A custom plugin for WhaleClaw",
  "version": "1.0.0",
  "author": "Author Name",
  "entry": "main.py",
  "config_schema": {
    "api_key": {"type": "string", "required": true},
    "timeout": {"type": "integer", "default": 30}
  }
}
```

### 1.3 插件基类

```python
class WhaleclawPlugin(ABC):
    """插件基类"""

    @property
    @abstractmethod
    def id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def register(self, api: WhaleclawPluginApi) -> None:
        """注册插件的渠道/工具/钩子"""

    async def on_start(self) -> None:
        """插件启动回调"""

    async def on_stop(self) -> None:
        """插件停止回调"""
```

---

## 2. 插件加载

### 2.1 插件发现 — `whaleclaw/plugins/loader.py`

插件搜索路径 (按优先级):
1. `~/.whaleclaw/plugins/` — 用户安装的插件
2. `./plugins/` — 项目本地插件
3. 通过 pip 安装的 `whaleclaw-plugin-*` 包 (entry_points)

```python
class PluginLoader:
    def discover(self) -> list[PluginMeta]:
        """扫描所有插件搜索路径，返回插件元数据列表"""

    def load(self, plugin_id: str) -> WhaleclawPlugin:
        """加载并实例化指定插件"""

    def load_all(self) -> list[WhaleclawPlugin]:
        """加载所有已发现的插件"""
```

### 2.2 插件注册表 — `whaleclaw/plugins/registry.py`

```python
class PluginRegistry:
    """管理已加载插件的生命周期"""

    async def register(self, plugin: WhaleclawPlugin) -> None: ...
    async def unregister(self, plugin_id: str) -> None: ...
    def get(self, plugin_id: str) -> WhaleclawPlugin | None: ...
    def list_plugins(self) -> list[PluginMeta]: ...
    async def start_all(self) -> None: ...
    async def stop_all(self) -> None: ...
```

### 2.3 pip 安装的插件

支持通过 entry_points 发现:

```toml
# 第三方插件的 pyproject.toml
[project.entry-points."whaleclaw.plugins"]
my_plugin = "my_plugin:plugin"
```

---

## 3. 钩子系统

### 3.1 钩子定义 — `whaleclaw/plugins/hooks.py`

```python
class HookPoint(str, Enum):
    """可用的钩子点"""
    BEFORE_MESSAGE = "before_message"       # 消息进入 Agent 前
    AFTER_MESSAGE = "after_message"         # Agent 回复后
    BEFORE_TOOL_CALL = "before_tool_call"   # 工具调用前
    AFTER_TOOL_CALL = "after_tool_call"     # 工具调用后
    ON_SESSION_CREATE = "on_session_create" # 会话创建时
    ON_SESSION_RESET = "on_session_reset"   # 会话重置时
    ON_ERROR = "on_error"                   # 错误发生时

HookCallback = Callable[[HookContext], Awaitable[HookResult]]

class HookContext(BaseModel):
    """钩子上下文"""
    hook: HookPoint
    session: Session
    data: dict[str, Any]                    # 钩子特定数据

class HookResult(BaseModel):
    """钩子返回值"""
    proceed: bool = True                    # False 则中断后续处理
    data: dict[str, Any] = {}               # 修改后的数据
```

### 3.2 钩子管理器

```python
class HookManager:
    def register(self, hook: HookPoint, callback: HookCallback, priority: int = 0) -> None: ...
    async def run(self, hook: HookPoint, context: HookContext) -> HookResult: ...
```

钩子按 priority 升序执行，任一钩子返回 `proceed=False` 则中断。

---

## 4. 技能系统

### 4.1 SKILL.md 格式

```markdown
---
triggers: ["浏览器", "打开网页", "截图", "browser", "screenshot", "webpage"]
max_tokens: 800
---
# 技能名称

## 触发条件
描述何时应使用此技能。

## 指令
Agent 应遵循的具体指令。

## 工具
此技能需要的工具列表。

## 示例
使用示例。
```

**与 OpenClaw 的关键区别**: SKILL.md 新增 YAML frontmatter:
- `triggers`: 关键词列表，用于 SkillRouter 快速匹配 (不需要调用 LLM)
- `max_tokens`: 该技能注入时的 token 上限 (超出则截断指令部分)

### 4.2 技能路由 — `whaleclaw/skills/router.py` (新增)

**这是 token 优化的核心组件。** OpenClaw 将所有激活技能全量注入 system prompt；WhaleClaw 通过 SkillRouter 按需选择 0~2 个最相关的技能。

```python
class SkillRouter:
    """轻量级技能路由 — 基于关键词匹配，不调用 LLM"""

    def route(
        self,
        user_message: str,
        available_skills: list[Skill],
        max_skills: int = 2,
    ) -> list[Skill]:
        """
        根据用户消息选择最相关的技能:
        1. 精确命令: /use <skill_id> -> 直接激活
        2. 关键词匹配: 用户消息包含技能 triggers 中的关键词
        3. 无匹配 -> 返回空列表 (不注入任何技能指令)
        最多返回 max_skills 个，按匹配度排序。
        """

    def _score(self, message: str, skill: Skill) -> float:
        """计算消息与技能的匹配分数 (关键词命中数 / 总关键词数)"""
```

匹配规则:
- 用户消息 "帮我打开百度截个图" -> 命中 triggers ["打开网页", "截图"] -> 注入浏览器技能
- 用户消息 "今天天气怎么样" -> 无命中 -> 不注入任何技能 (节省 ~1000 tokens)
- 用户消息 "/use browser-control" -> 显式激活 -> 注入浏览器技能

### 4.3 技能管理 — `whaleclaw/skills/manager.py`

```python
class SkillManager:
    """技能发现、加载和管理"""

    def discover(self) -> list[SkillMeta]:
        """扫描技能目录"""

    def load(self, skill_id: str) -> Skill:
        """加载技能 (解析 SKILL.md)"""

    def get_routed_skills(self, user_message: str, session: Session) -> list[Skill]:
        """通过 SkillRouter 获取当前消息匹配的技能 (替代原来的 get_active_skills)"""

    def format_for_prompt(self, skills: list[Skill], budget: int) -> str:
        """
        将路由命中的技能格式化为提示词片段，在 budget 内:
        - 如果 1 个技能: 注入完整指令
        - 如果 2 个技能: 各分一半预算，超出则截断示例部分
        - 如果 0 个技能: 返回空字符串 (不占 token)
        """

    async def install(self, source: str) -> SkillMeta:
        """从 URL/路径安装技能"""

    async def uninstall(self, skill_id: str) -> None:
        """卸载技能"""
```

技能搜索路径:
1. `~/.whaleclaw/workspace/skills/` — 用户技能
2. `whaleclaw/skills/bundled/` — 内置技能

### 4.4 技能解析 — `whaleclaw/skills/parser.py`

```python
class SkillParser:
    def parse(self, path: Path) -> Skill:
        """解析 SKILL.md 文件为 Skill 对象 (含 YAML frontmatter)"""

class Skill(BaseModel):
    id: str
    name: str
    triggers: list[str] = []        # 关键词列表 (用于 SkillRouter 快速匹配)
    trigger_description: str = ""   # 触发条件描述 (人类可读)
    instructions: str               # 指令内容
    tools: list[str] = []           # 需要的工具
    examples: list[str] = []        # 使用示例
    max_tokens: int = 800           # 注入时的 token 上限
    source_path: Path
```

---

## 5. 工作区

### 5.1 工作区结构

```
~/.whaleclaw/workspace/
  AGENTS.md                         # Agent 行为指南 (完整版，供人类阅读)
  AGENTS.summary.md                 # Agent 行为指南精简版 (~500 tokens，自动生成)
  skills/                           # 技能目录
    browser-control/
      SKILL.md
    code-sandbox/
      SKILL.md
  data/                             # Agent 工作数据
```

**注意**: 不再有 `TOOLS.md`。工具描述通过 LLM 原生 `tools` 参数传递 (Phase 2)，不需要单独的文本文件。

### 5.2 AGENTS.md 摘要化

```python
class AgentsSummaryBuilder:
    """从 AGENTS.md 生成精简摘要版"""

    def build(self, agents_md_path: Path) -> str:
        """
        读取完整 AGENTS.md，提取核心规则生成 AGENTS.summary.md:
        - 保留: 核心行为规则、安全约束、关键约定
        - 移除: 代码示例、详细说明、冗余描述
        - 目标: ~500 tokens
        """

    def rebuild_if_stale(self, agents_md_path: Path, summary_path: Path) -> bool:
        """如果 AGENTS.md 比 summary 新，则重新生成"""
```

CLI 命令: `whaleclaw config build-summary` 手动触发重新生成。

### 5.3 提示词注入策略 (PromptAssembler 动态层 + 延迟层)

**与 OpenClaw 的关键区别**: OpenClaw 在每轮对话都注入 AGENTS.md + TOOLS.md + 全部 SKILL.md (约 8000+ tokens)。WhaleClaw 的注入策略:

| 内容 | 注入时机 | 预算 | OpenClaw 做法 |
|------|---------|------|--------------|
| 身份 + 核心规则 | 每轮 (静态层) | ~200 tokens | 每轮 ~200 tokens |
| 工具描述 | 每轮 (tools 参数) | 不占 prompt | 每轮 ~1500 tokens |
| AGENTS.md | 仅首轮 (延迟层) | ~500 tokens | 每轮 ~2000 tokens |
| 技能指令 | 按需路由 (动态层) | 0~800 tokens | 全部 ~3000 tokens |
| 记忆 | 按需检索 (动态层) | ~500 tokens | 无限制 ~1000+ |
| **每轮总计** | | **~700-2000** | **~8000+** |

注入流程 (PromptAssembler.build 的完整实现):
1. **静态层** (必选): 身份 + 核心行为规则 (~200 tokens)
2. **动态层** (按需): SkillRouter 匹配的技能指令 (0~800 tokens) + MemoryManager 检索的记忆 (~500 tokens)
3. **延迟层** (条件触发):
   - 首轮对话: 注入 AGENTS.summary.md (~500 tokens)
   - 后续轮次: 不注入 (已在首轮建立上下文)
   - `/reload` 命令: 重新注入 AGENTS.summary.md
   - 遇到错误: 注入 EvoMap 相关方案 (如果有)

---

## 6. 内置高级工具

### 6.1 浏览器控制 — `whaleclaw/tools/browser.py`

基于 Playwright:

```python
class BrowserTool(Tool):
    """浏览器控制工具"""

    # 子命令:
    # - navigate: 打开 URL
    # - screenshot: 截图
    # - click: 点击元素
    # - type: 输入文本
    # - get_text: 获取页面文本
    # - evaluate: 执行 JavaScript
```

配置:
```json
{
  "tools": {
    "browser": {
      "enabled": true,
      "headless": true,
      "timeout": 30
    }
  }
}
```

### 6.2 代码沙箱 — `whaleclaw/tools/code_sandbox.py`

```python
class CodeSandboxTool(Tool):
    """安全的代码执行沙箱"""

    # 支持语言: Python
    # 执行方式: subprocess + 资源限制
    # 限制: 内存 256MB, CPU 30s, 无网络
    # 输出: stdout + stderr + 返回值
```

---

## 7. EvoMap 内置插件

### 7.1 概述

EvoMap 是一个 AI Agent 协作进化市场 (`https://evomap.ai`)。WhaleClaw 内置 EvoMap 插件，使 Agent 能够:
- 将验证过的解决方案 (修复/优化/创新) 发布到 EvoMap 网络
- 从网络获取其他 Agent 已验证的解决方案，避免重复劳动
- 认领赏金任务并赚取积分
- 参与 Swarm 多 Agent 协作分解大型任务

协议: GEP-A2A v1.0.0，传输: HTTPS

### 7.2 节点身份 — `whaleclaw/plugins/evomap/identity.py`

```python
class EvoMapIdentity:
    """管理 WhaleClaw 在 EvoMap 网络中的节点身份"""

    IDENTITY_PATH = Path("~/.whaleclaw/evomap/identity.json")

    def get_or_create_sender_id(self) -> str:
        """
        首次运行时生成 sender_id ("node_" + random_hex(8))，
        持久化到 identity.json，后续复用。
        注意: 绝不使用 Hub 返回的 sender_id (hub_ 前缀)。
        """

    def get_claim_code(self) -> str | None:
        """获取当前 claim code (用于绑定用户账户)"""

    def save_claim_code(self, code: str, url: str) -> None:
        """保存 hello 返回的 claim code"""
```

身份文件结构:
```json
{
  "sender_id": "node_a1b2c3d4e5f6a7b8",
  "created_at": "2026-02-22T12:00:00Z",
  "claim_code": "REEF-4X7K",
  "claim_url": "https://evomap.ai/claim/REEF-4X7K",
  "reputation": 0
}
```

### 7.3 A2A 协议客户端 — `whaleclaw/plugins/evomap/client.py`

```python
class A2AClient:
    """GEP-A2A 协议 HTTP 客户端"""

    HUB_URL = "https://evomap.ai"

    def _build_envelope(self, message_type: str, payload: dict) -> dict:
        """
        构建完整协议信封 (7 个必填字段):
        protocol, protocol_version, message_type,
        message_id, sender_id, timestamp, payload
        """

    async def hello(self, capabilities: dict | None = None) -> HelloResponse:
        """POST /a2a/hello — 注册/刷新节点"""

    async def publish(self, assets: list[Asset]) -> PublishResponse:
        """POST /a2a/publish — 发布 Gene+Capsule+EvolutionEvent 捆绑包"""

    async def fetch(
        self,
        asset_type: str = "Capsule",
        include_tasks: bool = False,
    ) -> FetchResponse:
        """POST /a2a/fetch — 拉取已推广资产和可用任务"""

    async def report(self, target_asset_id: str, report: ValidationReport) -> None:
        """POST /a2a/report — 提交验证报告"""
```

### 7.4 资产哈希 — `whaleclaw/plugins/evomap/hasher.py`

```python
class AssetHasher:
    @staticmethod
    def compute_asset_id(asset: dict) -> str:
        """
        计算 content-addressable ID:
        1. 移除 asset_id 字段
        2. canonical JSON (sorted keys)
        3. SHA256 哈希
        返回 "sha256:<hex>"
        """
```

### 7.5 资产发布 — `whaleclaw/plugins/evomap/publisher.py`

```python
class AssetPublisher:
    """将 Agent 的解决方案打包为 Gene+Capsule+EvolutionEvent 发布"""

    async def publish_fix(
        self,
        category: Literal["repair", "optimize", "innovate"],
        signals: list[str],
        gene_summary: str,
        capsule_summary: str,
        confidence: float,
        blast_radius: BlastRadius,
        outcome: Outcome,
        mutations_tried: int = 1,
        total_cycles: int = 1,
    ) -> PublishResult:
        """
        构建完整捆绑包:
        1. 创建 Gene (策略模板)
        2. 创建 Capsule (验证过的修复)
        3. 创建 EvolutionEvent (进化过程记录)
        4. 计算每个资产的 asset_id
        5. 调用 A2AClient.publish()
        """
```

### 7.6 资产拉取 — `whaleclaw/plugins/evomap/fetcher.py`

```python
class AssetFetcher:
    """从 EvoMap 拉取已推广的资产并缓存到本地"""

    CACHE_DIR = Path("~/.whaleclaw/evomap/assets/")

    async def fetch_promoted(self, asset_type: str = "Capsule") -> list[Asset]:
        """拉取最新推广资产"""

    async def search_by_signals(self, signals: list[str]) -> list[Asset]:
        """按信号搜索相关资产 (用于 Agent 遇到问题时自动查找已有方案)"""

    def get_cached(self, asset_id: str) -> Asset | None:
        """从本地缓存获取资产"""
```

### 7.7 赏金任务 — `whaleclaw/plugins/evomap/bounty.py`

```python
class BountyManager:
    """管理 EvoMap 赏金任务"""

    async def list_tasks(self, min_reputation: int = 0) -> list[Task]:
        """获取可用任务列表"""

    async def claim_task(self, task_id: str) -> ClaimResult:
        """认领任务"""

    async def complete_task(self, task_id: str, asset_id: str) -> CompleteResult:
        """提交任务完成"""

    async def my_tasks(self) -> list[Task]:
        """查看已认领的任务"""
```

### 7.8 数据模型 — `whaleclaw/plugins/evomap/models.py`

```python
class Gene(BaseModel):
    type: Literal["Gene"] = "Gene"
    schema_version: str = "1.5.0"
    category: Literal["repair", "optimize", "innovate"]
    signals_match: list[str]
    summary: str                         # min 10 chars
    validation: list[str] = []
    asset_id: str = ""                   # sha256:<hex>

class Capsule(BaseModel):
    type: Literal["Capsule"] = "Capsule"
    schema_version: str = "1.5.0"
    trigger: list[str]
    gene: str                            # Gene 的 asset_id
    summary: str                         # min 20 chars
    confidence: float                    # 0-1
    blast_radius: BlastRadius
    outcome: Outcome
    env_fingerprint: EnvFingerprint
    success_streak: int = 0
    asset_id: str = ""

class EvolutionEvent(BaseModel):
    type: Literal["EvolutionEvent"] = "EvolutionEvent"
    intent: Literal["repair", "optimize", "innovate"]
    capsule_id: str = ""
    genes_used: list[str] = []
    outcome: Outcome
    mutations_tried: int = 1
    total_cycles: int = 1
    asset_id: str = ""

class BlastRadius(BaseModel):
    files: int                           # 必须 > 0
    lines: int                           # 必须 > 0

class Outcome(BaseModel):
    status: Literal["success", "failure"]
    score: float                         # 0-1

class EnvFingerprint(BaseModel):
    platform: str                        # "darwin", "linux", "win32"
    arch: str                            # "arm64", "x64"

class Task(BaseModel):
    task_id: str
    title: str
    signals: str
    bounty_id: str | None = None
    min_reputation: int = 0
    status: Literal["open", "claimed", "completed"]
    expires_at: datetime | None = None
    swarm_role: str | None = None
    parent_task_id: str | None = None
```

### 7.9 EvoMap 插件主入口 — `whaleclaw/plugins/evomap/plugin.py`

```python
class EvoMapPlugin(WhaleclawPlugin):
    """EvoMap 协作进化市场插件"""

    @property
    def id(self) -> str:
        return "evomap"

    @property
    def name(self) -> str:
        return "EvoMap"

    def register(self, api: WhaleclawPluginApi) -> None:
        api.register_tool(EvoMapPublishTool(self.publisher))
        api.register_tool(EvoMapFetchTool(self.fetcher))
        api.register_tool(EvoMapBountyTool(self.bounty_mgr))
        api.register_hook(HookPoint.ON_ERROR, self._on_error_search)
        api.register_hook(HookPoint.AFTER_TOOL_CALL, self._on_tool_success_publish)
        api.register_command("/evomap", self._evomap_command)

    async def on_start(self) -> None:
        """启动时: hello 注册节点 + 拉取最新资产"""
        await self.client.hello()
        await self.fetcher.fetch_promoted()

    async def _on_error_search(self, ctx: HookContext) -> HookResult:
        """Agent 遇到错误时，自动搜索 EvoMap 是否有已验证的修复方案"""

    async def _on_tool_success_publish(self, ctx: HookContext) -> HookResult:
        """工具调用成功后，评估是否值得发布到 EvoMap"""
```

### 7.10 EvoMap 工具集

```python
class EvoMapPublishTool(Tool):
    """发布解决方案到 EvoMap 网络"""
    # Agent 可调用: 将当前修复打包为 Gene+Capsule 发布

class EvoMapFetchTool(Tool):
    """从 EvoMap 搜索已验证的解决方案"""
    # Agent 可调用: 按信号搜索相关 Capsule

class EvoMapBountyTool(Tool):
    """查看和认领 EvoMap 赏金任务"""
    # Agent 可调用: 列出任务 / 认领 / 完成
```

### 7.11 EvoMap 配置

```json
{
  "plugins": {
    "evomap": {
      "enabled": true,
      "hub_url": "https://evomap.ai",
      "auto_fetch": true,
      "auto_publish": false,
      "sync_interval_hours": 4,
      "webhook_url": null,
      "min_confidence_to_publish": 0.7,
      "auto_search_on_error": true
    }
  }
}
```

### 7.12 CLI 扩展

```
whaleclaw evomap
  status                              # 节点状态 (sender_id/reputation/积分)
  hello                               # 手动注册/刷新节点
  fetch                               # 手动拉取最新资产
  publish                             # 手动发布 (交互式)
  tasks                               # 查看可用赏金任务
  claim <task_id>                     # 认领任务
  my-tasks                            # 查看已认领任务
  sync                                # 完整同步 (hello + fetch + publish)
  claim-code                          # 显示 claim code (绑定用户账户)
```

### 7.13 持续同步

EvoMap 插件支持后台持续同步 (类似 Evolver 的 loop 模式):

```python
class EvoMapSyncLoop:
    """后台定时同步任务"""

    async def run(self, interval_hours: float = 4.0) -> None:
        """
        每 N 小时执行:
        1. hello — 刷新节点注册
        2. fetch — 拉取新推广资产和可用任务
        3. publish — 上传待发布的本地资产
        4. claim — 自动认领匹配的高价值任务
        """
```

与 Phase 7 的 Cron 系统集成，作为内置定时任务运行。

---

## 8. CLI 扩展

新增命令:

```
whaleclaw plugins
  list                              # 列出已安装插件
  install <source>                  # 安装插件
  uninstall <plugin_id>             # 卸载插件
  enable <plugin_id>                # 启用插件
  disable <plugin_id>               # 禁用插件

whaleclaw skills
  list                              # 列出已安装技能
  install <source>                  # 安装技能
  uninstall <skill_id>              # 卸载技能

whaleclaw evomap
  status                            # EvoMap 节点状态
  hello                             # 注册/刷新节点
  fetch                             # 拉取最新资产
  tasks                             # 查看赏金任务
  claim <task_id>                   # 认领任务
  my-tasks                          # 已认领任务
  sync                              # 完整同步
  claim-code                        # 显示绑定码
```

---

## 验收标准

### AC-1: 插件加载
创建一个简单的测试插件 (注册一个自定义工具)，放入 `~/.whaleclaw/plugins/`，重启 Gateway 后工具可用。

### AC-2: 钩子执行
注册 `before_message` 钩子，在消息前自动添加前缀。验证消息被修改。

### AC-3: 技能注入
创建一个 `SKILL.md`，放入 `~/.whaleclaw/workspace/skills/`，Agent 回复时遵循技能指令。

### AC-4: 浏览器工具
```
用户: 打开 https://example.com 并截图
Agent: [调用 browser 工具: navigate + screenshot]
Agent: 这是 example.com 的截图: [图片]
```

### AC-5: 代码沙箱
```
用户: 用 Python 计算斐波那契数列前 10 项
Agent: [调用 code_sandbox 工具]
Agent: 结果: [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
```

### AC-6: 插件 CLI
```bash
whaleclaw plugins list
# 输出: 已安装插件列表

whaleclaw skills list
# 输出: 已安装技能列表
```

### AC-7: pip 插件发现
安装一个 `whaleclaw-plugin-example` 包后，`whaleclaw plugins list` 能发现它。

### AC-8: EvoMap 节点注册
```bash
whaleclaw evomap hello
# 输出: 节点已注册，sender_id: node_xxx，claim code: XXXX-XXXX
# identity.json 已持久化
```

### AC-9: EvoMap 资产发布
Agent 成功修复一个 bug 后，通过 EvoMap 工具将解决方案打包为 Gene+Capsule+EvolutionEvent 发布到网络。

### AC-10: EvoMap 资产搜索
Agent 遇到 `TimeoutError` 时，自动搜索 EvoMap 网络中已有的修复方案并应用。

### AC-11: EvoMap 赏金任务
```bash
whaleclaw evomap tasks
# 输出: 可用赏金任务列表
whaleclaw evomap claim <task_id>
# 输出: 任务已认领
```

### AC-12: EvoMap 持续同步
启用 `auto_fetch` 后，EvoMap 插件每 4 小时自动同步一次 (hello + fetch)。

---

## 文件清单

```
whaleclaw/plugins/__init__.py
whaleclaw/plugins/sdk.py
whaleclaw/plugins/loader.py
whaleclaw/plugins/registry.py
whaleclaw/plugins/hooks.py
whaleclaw/skills/__init__.py
whaleclaw/skills/manager.py
whaleclaw/skills/parser.py
whaleclaw/skills/router.py                  (技能路由器 — token 优化核心)
whaleclaw/skills/summary.py                 (AGENTS.md 摘要生成器)
whaleclaw/skills/bundled/                   (内置技能目录)
whaleclaw/skills/bundled/browser-control/SKILL.md
whaleclaw/skills/bundled/code-sandbox/SKILL.md
whaleclaw/tools/browser.py
whaleclaw/tools/code_sandbox.py
whaleclaw/plugins/evomap/__init__.py
whaleclaw/plugins/evomap/plugin.py
whaleclaw/plugins/evomap/client.py
whaleclaw/plugins/evomap/identity.py
whaleclaw/plugins/evomap/publisher.py
whaleclaw/plugins/evomap/fetcher.py
whaleclaw/plugins/evomap/bounty.py
whaleclaw/plugins/evomap/hasher.py
whaleclaw/plugins/evomap/models.py
whaleclaw/plugins/evomap/config.py
whaleclaw/cli/plugins_cmd.py
whaleclaw/cli/skills_cmd.py
whaleclaw/cli/evomap_cmd.py
tests/test_plugins/test_sdk.py
tests/test_plugins/test_loader.py
tests/test_plugins/test_registry.py
tests/test_plugins/test_hooks.py
tests/test_plugins/test_evomap/test_client.py
tests/test_plugins/test_evomap/test_identity.py
tests/test_plugins/test_evomap/test_publisher.py
tests/test_plugins/test_evomap/test_fetcher.py
tests/test_plugins/test_evomap/test_bounty.py
tests/test_plugins/test_evomap/test_hasher.py
tests/test_skills/test_manager.py
tests/test_skills/test_parser.py
tests/test_skills/test_router.py
tests/test_skills/test_summary.py
tests/test_tools/test_browser.py
tests/test_tools/test_code_sandbox.py
```
