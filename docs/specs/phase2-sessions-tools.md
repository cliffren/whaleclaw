# Phase 2: 会话 + 多模型 + 工具系统

## 目标

在 Phase 1 基础上实现:
1. 多轮对话 — 会话持久化，上下文窗口管理
2. 多模型支持 — Anthropic / OpenAI / DeepSeek / 通义千问 / 智谱 / MiniMax / 月之暗面 Kimi / Google Gemini / NVIDIA NIM，运行时切换
3. 工具系统 — Agent 可调用工具 (bash, 文件读写)，支持工具循环
4. 聊天命令 — `/new`, `/reset`, `/status`, `/model`

## 前置条件

- Phase 1 全部完成
- 至少一个 LLM API Key (Anthropic / OpenAI / DeepSeek / 通义千问 / 智谱 / MiniMax / 月之暗面 / Google / NVIDIA)

---

## 1. 会话管理

### 1.1 会话模型 — `whaleclaw/sessions/manager.py`

```python
class Session(BaseModel):
    id: str                          # UUID
    channel: str                     # 来源渠道 ("webchat", "feishu", ...)
    peer_id: str                     # 对话方标识
    messages: list[Message] = []     # 消息历史
    model: str                       # 当前使用的模型
    thinking_level: str = "off"      # 思考深度
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = {}

class SessionManager:
    async def create(self, channel: str, peer_id: str) -> Session: ...
    async def get(self, session_id: str) -> Session | None: ...
    async def get_or_create(self, channel: str, peer_id: str) -> Session: ...
    async def update(self, session: Session) -> None: ...
    async def reset(self, session_id: str) -> Session: ...
    async def list_sessions(self) -> list[Session]: ...
    async def delete(self, session_id: str) -> None: ...
```

### 1.2 会话持久化 — `whaleclaw/sessions/store.py`

SQLite 存储:

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    peer_id TEXT NOT NULL,
    model TEXT NOT NULL,
    thinking_level TEXT DEFAULT 'off',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,          -- system / user / assistant / tool
    content TEXT NOT NULL,
    tool_call_id TEXT,           -- 关联的工具调用 ID
    tool_name TEXT,              -- 工具名称 (role=tool 时)
    timestamp TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE INDEX idx_messages_session ON messages(session_id, timestamp);
```

### 1.3 上下文窗口管理 — `whaleclaw/sessions/context_window.py`

- 按模型的 max_context 限制裁剪历史消息
- **预算分配策略** (避免 system prompt 膨胀吞噬对话空间):

```python
class TokenBudget(BaseModel):
    """上下文窗口 token 预算分配"""
    total: int                           # 模型 max_context
    system_prompt: int                   # system prompt 预算 (total * 0.15)
    tools_schema: int                    # 工具 JSON Schema 预算 (原生参数，部分 Provider 不计入)
    conversation: int                    # 对话历史预算 (total * 0.60)
    reply_reserve: int                   # 回复预留 (total * 0.25)

class ContextWindow:
    def compute_budget(self, model: str) -> TokenBudget:
        """根据模型的 max_context 计算各层预算"""

    def trim(self, messages: list[Message], budget: TokenBudget) -> list[Message]:
        """裁剪消息列表使其不超过 conversation 预算"""

    async def compact(self, messages: list[Message], provider: LLMProvider) -> list[Message]:
        """将历史消息压缩为摘要"""
```

- 保留策略: 始终保留 system prompt (静态层) + 最近 N 条消息
- system prompt 由 PromptAssembler 在 `system_prompt` 预算内组装
- 支持 `/compact` 命令: 将历史压缩为摘要
- Token 计数: 使用 tiktoken (OpenAI) 或近似计算 (其他模型)

---

## 2. 多模型支持

### 2.1 模型注册表

配置 schema 扩展:

```python
class ProviderConfig(BaseModel):
    api_key: str | None = None       # 也可从环境变量读取
    base_url: str | None = None      # 自定义 API 端点
    timeout: int = 120               # 请求超时 (秒)

class ModelsConfig(BaseModel):
    anthropic: ProviderConfig = ProviderConfig()
    openai: ProviderConfig = ProviderConfig()
    deepseek: ProviderConfig = ProviderConfig()
    qwen: ProviderConfig = ProviderConfig()
    zhipu: ProviderConfig = ProviderConfig()
    minimax: ProviderConfig = ProviderConfig()
    moonshot: ProviderConfig = ProviderConfig()
    google: ProviderConfig = ProviderConfig()
    nvidia: ProviderConfig = ProviderConfig()
```

环境变量映射:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `DASHSCOPE_API_KEY` (通义千问)
- `ZHIPU_API_KEY` (智谱)
- `MINIMAX_API_KEY` (MiniMax 海螺)
- `MINIMAX_GROUP_ID` (MiniMax Group ID)
- `MOONSHOT_API_KEY` (月之暗面 Kimi)
- `GOOGLE_API_KEY` (Google Gemini，从 ai.google.dev 获取)
- `NVIDIA_API_KEY` (NVIDIA NIM，从 build.nvidia.com 获取)

### 2.2 新增 Provider

#### OpenAI — `whaleclaw/providers/openai.py`
- 调用 OpenAI Chat Completions API
- 支持 GPT-4o / GPT-4.1 / o3 等模型
- 流式响应

#### DeepSeek — `whaleclaw/providers/deepseek.py`
- 调用 DeepSeek API (兼容 OpenAI 格式)
- `base_url = "https://api.deepseek.com/v1"`
- 支持 deepseek-chat / deepseek-reasoner

#### 通义千问 — `whaleclaw/providers/qwen.py`
- 调用 DashScope API
- 支持 qwen-max / qwen-plus / qwen-turbo
- 流式响应

#### 智谱 — `whaleclaw/providers/zhipu.py`
- 调用智谱开放平台 API (兼容 OpenAI 格式)
- `base_url = "https://open.bigmodel.cn/api/paas/v4"`
- 支持 glm-5 (MoE 架构，~745B 参数，200K 上下文) / glm-4.7 (200K 上下文，128K 输出)
- 轻量版: glm-4.7-flash (30B 级，免费)
- 流式响应
- 支持 web_search 等内置工具

#### MiniMax (海螺 AI) — `whaleclaw/providers/minimax.py`
- 调用 MiniMax API (兼容 Anthropic/OpenAI 格式)
- `base_url = "https://api.minimax.chat/v1"`
- 支持 MiniMax-M2.5 / MiniMax-M2.5-highspeed / MiniMax-M2.1 / MiniMax-M2.1-highspeed / MiniMax-M2 / M2-her
- 流式响应

#### 月之暗面 Kimi — `whaleclaw/providers/moonshot.py`
- 调用 Moonshot API (兼容 OpenAI 格式)
- `base_url = "https://api.moonshot.cn/v1"`
- 支持 kimi-k2.5 (多模态，256K 上下文) / kimi-k2-thinking / kimi-k2-thinking-turbo / kimi-k2-turbo-preview
- 流式响应
- 支持 thinking 模式 (`{"type": "enabled"}` / `{"type": "disabled"}`)
- 支持图片/视频理解 (原生多模态)
- 定价: 输入 $0.60/M tokens (缓存命中 $0.10)，输出 $3.00/M tokens

#### Google Gemini — `whaleclaw/providers/google.py`
- 调用 Google Generative AI API
- `base_url = "https://generativelanguage.googleapis.com/v1beta"`
- 支持 gemini-3.1-pro-preview (旗舰推理) / gemini-3-pro-preview / gemini-3-flash-preview (高性价比)
- 多模态: 原生支持图片、视频、音频、PDF 输入
- 200K+ 上下文窗口
- 支持 thinking_level 参数控制推理深度 (high / low)
- 支持 Context Caching 降低重复输入成本
- 流式响应
- 免费层: 有限速率免费使用；付费层按 token 计费
- 定价 (gemini-3-pro-preview): 输入 $2.00/M tokens，输出 $12.00/M tokens

#### NVIDIA NIM (免费) — `whaleclaw/providers/nvidia.py`
- 调用 NVIDIA NIM API (兼容 OpenAI 格式)
- `base_url = "https://integrate.api.nvidia.com/v1"`
- 免费模型: meta/llama-3.1-8b-instruct / deepseek-ai/deepseek-r1 / google/gemma-2-9b-it 等
- API Key 从 build.nvidia.com 免费获取
- 流式响应
- 适合原型开发和测试，生产环境需 NVIDIA AI Enterprise 许可

### 2.3 模型路由 — `whaleclaw/providers/router.py`

```python
class ModelRouter:
    def resolve(self, model_id: str) -> tuple[LLMProvider, str]:
        """
        解析 model_id (如 "anthropic/claude-sonnet-4-20250514") 为 (provider, model_name)
        格式: "<provider>/<model>" 或 "<model>" (使用默认 provider)
        """

    async def chat(self, model_id: str, messages, on_stream=None) -> str:
        """路由到对应 provider 并调用"""

    async def chat_with_failover(self, model_ids: list[str], messages, on_stream=None) -> str:
        """按优先级尝试多个模型，失败时自动切换"""
```

模型 ID 格式:
- `anthropic/claude-sonnet-4-20250514`
- `openai/gpt-4o`
- `deepseek/deepseek-chat`
- `qwen/qwen-max`
- `zhipu/glm-5`
- `zhipu/glm-4.7`
- `minimax/MiniMax-M2.5`
- `moonshot/kimi-k2.5`
- `google/gemini-3.1-pro-preview`
- `google/gemini-3-flash-preview`
- `nvidia/meta/llama-3.1-8b-instruct`

---

## 3. 工具系统

### 3.1 工具基类 — `whaleclaw/tools/base.py`

```python
class ToolParameter(BaseModel):
    name: str
    type: str                        # "string", "integer", "boolean", "object", "array"
    description: str
    required: bool = True
    enum: list[str] | None = None

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter]

class ToolResult(BaseModel):
    success: bool
    output: str
    error: str | None = None

class Tool(ABC):
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition: ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult: ...
```

### 3.2 工具注册表 — `whaleclaw/tools/registry.py`

```python
class ToolRegistry:
    def register(self, tool: Tool) -> None: ...
    def get(self, name: str) -> Tool | None: ...
    def list_tools(self) -> list[ToolDefinition]: ...
    def to_llm_schemas(self) -> list[ToolSchema]: ...
    def to_prompt_fallback(self) -> str: ...
```

**工具描述传递策略** (token 优化核心):

工具的 JSON Schema 通过 LLM API 原生 `tools` 参数传递，**不注入 system prompt**:
- `to_llm_schemas()` 生成 `ToolSchema` 列表，传给 `LLMProvider.chat(tools=...)`
- 所有主流 Provider (Anthropic/OpenAI/DeepSeek/Gemini/智谱/Kimi/MiniMax) 均支持
- Anthropic 对 tools 参数有 prompt caching，多轮对话只计费一次
- `to_prompt_fallback()` 仅用于不支持原生 tools 的 Provider (如部分 NVIDIA NIM 免费模型)，此时将工具描述文本注入 system prompt 作为降级方案

这与 OpenClaw 的做法不同 — OpenClaw 将 TOOLS.md 全文塞入 system prompt，每轮浪费约 1500 tokens。

### 3.3 内置工具

#### Bash — `whaleclaw/tools/bash.py`
```python
class BashTool(Tool):
    """执行 bash 命令，返回 stdout/stderr/exit_code"""
    # 参数: command (str), timeout (int, 默认 30s)
    # 安全: 不允许 rm -rf /、不允许修改系统文件
```

#### 文件读取 — `whaleclaw/tools/file_read.py`
```python
class FileReadTool(Tool):
    """读取文件内容，支持行号范围"""
    # 参数: path (str), offset (int, 可选), limit (int, 可选)
```

#### 文件写入 — `whaleclaw/tools/file_write.py`
```python
class FileWriteTool(Tool):
    """写入文件内容 (覆盖)"""
    # 参数: path (str), content (str)
```

#### 文件编辑 — `whaleclaw/tools/file_edit.py`
```python
class FileEditTool(Tool):
    """精确字符串替换"""
    # 参数: path (str), old_string (str), new_string (str)
```

### 3.4 Agent 工具循环

更新 `whaleclaw/agent/loop.py`:

```python
async def run_agent(message, session, config, on_stream, on_tool_call) -> str:
    """
    带工具的 Agent 循环:
    1. ContextWindow.compute_budget() 计算各层 token 预算
    2. PromptAssembler.build() 在预算内组装 system prompt
    3. ToolRegistry.to_llm_schemas() 生成工具 Schema
    4. 调用 LLM (messages + tools 原生参数)
    5. 如果 LLM 返回 tool_use:
       a. 执行工具
       b. 将工具结果追加到消息列表
       c. 回到步骤 4 (最多 N 轮)
    6. 如果 LLM 返回文本: 结束循环，返回回复
    """
```

工具循环上限: 默认 25 轮，防止无限循环。

---

## 4. 流式响应增强

### 4.1 WebSocket 流式协议扩展

新增消息类型:

```python
class MessageType(str, Enum):
    # ... Phase 1 的类型
    TOOL_CALL = "tool_call"       # Agent 发起工具调用
    TOOL_RESULT = "tool_result"   # 工具执行结果
    THINKING = "thinking"         # Agent 思考过程
    STATUS = "status"             # 状态更新 (如 "正在调用工具...")
```

流式推送顺序:
1. `thinking` — Agent 思考内容 (如果模型支持)
2. `tool_call` — 工具调用信息 `{name, arguments}`
3. `tool_result` — 工具执行结果 `{name, output, success}`
4. `stream` — 文本片段 (可能多轮)
5. `message` — 最终完整回复

---

## 5. 聊天命令

### 5.1 命令解析 — `whaleclaw/agent/commands.py`

```python
class ChatCommand:
    """解析和执行聊天命令 (以 / 开头的消息)"""

    async def handle(self, text: str, session: Session) -> str | None:
        """如果是命令返回响应文本，否则返回 None"""
```

支持的命令:

| 命令 | 说明 | 示例 |
|------|------|------|
| `/new` 或 `/reset` | 重置当前会话 | `/new` |
| `/status` | 显示会话状态 (模型/token 用量) | `/status` |
| `/model <id>` | 切换模型 | `/model openai/gpt-4o` |
| `/compact` | 压缩会话上下文 | `/compact` |
| `/think <level>` | 设置思考深度 | `/think high` |
| `/help` | 显示可用命令 | `/help` |

---

## 6. 配置扩展

`whaleclaw/config/schema.py` 新增:

```python
class AgentConfig(BaseModel):
    model: str = "anthropic/claude-sonnet-4-20250514"
    max_tool_rounds: int = 25
    workspace: str = str(WORKSPACE_DIR)
    thinking_level: str = "off"      # off / low / medium / high

class WhaleclawConfig(BaseModel):
    gateway: GatewayConfig
    agent: AgentConfig
    models: ModelsConfig             # 新增
```

---

## 验收标准

### AC-1: 多轮对话
```
用户: 我叫小明
Agent: 你好小明！
用户: 我叫什么？
Agent: 你叫小明。
```
Agent 能记住上下文。

### AC-2: 模型切换
```
用户: /model openai/gpt-4o
Agent: 已切换到 openai/gpt-4o
用户: 你好
Agent: (由 GPT-4o 回复)
```

### AC-3: 工具调用
```
用户: 列出当前目录的文件
Agent: [调用 bash 工具: ls -la]
Agent: 当前目录包含以下文件: ...
```

### AC-4: 会话重置
```
用户: /new
Agent: 会话已重置。
用户: 我叫什么？
Agent: 我不知道你的名字，你还没有告诉我。
```

### AC-5: 会话持久化
1. 发送几条消息
2. 重启 Gateway
3. 重新连接，历史消息仍在

### AC-6: 流式工具调用
WebSocket 客户端应依次收到:
`tool_call` -> `tool_result` -> `stream` -> `message`

---

## 文件清单

```
whaleclaw/sessions/__init__.py
whaleclaw/sessions/manager.py
whaleclaw/sessions/store.py
whaleclaw/sessions/context_window.py
whaleclaw/providers/openai.py
whaleclaw/providers/deepseek.py
whaleclaw/providers/qwen.py
whaleclaw/providers/zhipu.py
whaleclaw/providers/minimax.py
whaleclaw/providers/moonshot.py
whaleclaw/providers/google.py
whaleclaw/providers/nvidia.py
whaleclaw/providers/router.py
whaleclaw/tools/__init__.py
whaleclaw/tools/base.py
whaleclaw/tools/registry.py
whaleclaw/tools/bash.py
whaleclaw/tools/file_read.py
whaleclaw/tools/file_write.py
whaleclaw/tools/file_edit.py
whaleclaw/agent/commands.py
tests/test_sessions/test_manager.py
tests/test_sessions/test_store.py
tests/test_sessions/test_context_window.py
tests/test_providers/test_openai.py
tests/test_providers/test_deepseek.py
tests/test_providers/test_qwen.py
tests/test_providers/test_zhipu.py
tests/test_providers/test_minimax.py
tests/test_providers/test_moonshot.py
tests/test_providers/test_google.py
tests/test_providers/test_nvidia.py
tests/test_providers/test_router.py
tests/test_tools/test_bash.py
tests/test_tools/test_file_read.py
tests/test_tools/test_file_write.py
tests/test_tools/test_file_edit.py
tests/test_tools/test_registry.py
tests/test_agent/test_commands.py
```
