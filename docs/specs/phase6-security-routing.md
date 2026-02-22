# Phase 6: 安全 + 多 Agent 路由

## 目标

实现生产级安全机制和多 Agent 会话隔离:
1. 消息路由 — 按渠道/账号/群组路由到不同 Agent 实例
2. 沙箱执行 — Docker 沙箱模式，非主会话工具隔离
3. DM 配对 — 跨渠道的统一配对码验证流程
4. 权限模型 — 工具白名单/黑名单，per-session 权限控制
5. Agent 间通信 — 跨会话消息传递
6. 审计日志 — 完整的操作记录

## 前置条件

- Phase 1 ~ 5 全部完成
- Docker (沙箱功能需要)

---

## 1. 消息路由

### 1.1 路由引擎 — `whaleclaw/routing/router.py`

```python
class MessageRouter:
    """
    消息路由引擎:
    根据渠道/发送者/群组将消息路由到对应的 Agent 实例
    """

    async def route(self, message: ChannelMessage) -> RoutingResult:
        """
        路由决策:
        1. 匹配路由规则
        2. 确定目标 Agent (workspace + 配置)
        3. 确定会话 (新建或复用)
        4. 应用安全策略
        """

class RoutingResult(BaseModel):
    agent_id: str                    # 目标 Agent 标识
    session_id: str                  # 目标会话 ID
    workspace: str                   # Agent 工作区路径
    security_policy: SecurityPolicy  # 安全策略
    allowed: bool                    # 是否允许处理
    deny_reason: str | None = None   # 拒绝原因
```

### 1.2 路由规则 — `whaleclaw/routing/rules.py`

```python
class RoutingRule(BaseModel):
    """路由规则"""
    name: str
    priority: int = 0
    match: RoutingMatch
    target: RoutingTarget

class RoutingMatch(BaseModel):
    """匹配条件"""
    channel: str | None = None       # 渠道名 ("feishu", "webchat")
    peer_id: str | list[str] | None = None
    group_id: str | list[str] | None = None
    pattern: str | None = None       # 消息内容正则匹配

class RoutingTarget(BaseModel):
    """路由目标"""
    agent_id: str = "default"
    workspace: str | None = None
    model: str | None = None         # 覆盖默认模型
    tools: list[str] | None = None   # 覆盖工具列表
    sandbox: bool = False            # 是否启用沙箱
```

配置示例:
```json
{
  "routing": {
    "rules": [
      {
        "name": "feishu-group-sandbox",
        "priority": 10,
        "match": {"channel": "feishu", "group_id": "*"},
        "target": {"sandbox": true, "tools": ["bash", "file_read"]}
      },
      {
        "name": "webchat-main",
        "match": {"channel": "webchat"},
        "target": {"agent_id": "main"}
      }
    ]
  }
}
```

### 1.3 多 Agent 实例

```python
class AgentInstance:
    """独立的 Agent 实例，拥有自己的工作区和配置"""

    id: str
    workspace: Path
    config: AgentConfig
    tool_registry: ToolRegistry
    session_manager: SessionManager

class AgentPool:
    """Agent 实例池"""

    async def get_or_create(self, agent_id: str) -> AgentInstance: ...
    async def destroy(self, agent_id: str) -> None: ...
    def list_agents(self) -> list[str]: ...
```

---

## 2. 沙箱执行

### 2.1 沙箱管理 — `whaleclaw/security/sandbox.py`

```python
class SandboxMode(str, Enum):
    NONE = "none"                    # 不使用沙箱
    NON_MAIN = "non-main"           # 非主会话使用沙箱
    ALL = "all"                      # 所有会话使用沙箱

class DockerSandbox:
    """Docker 沙箱环境"""

    async def create(self, session_id: str, config: SandboxConfig) -> SandboxInstance:
        """创建沙箱容器"""

    async def execute(self, instance: SandboxInstance, command: str, timeout: int = 30) -> SandboxResult:
        """在沙箱中执行命令"""

    async def destroy(self, instance: SandboxInstance) -> None:
        """销毁沙箱容器"""

class SandboxConfig(BaseModel):
    image: str = "python:3.12-slim"
    memory_limit: str = "256m"
    cpu_limit: float = 1.0
    network: bool = False            # 默认禁止网络
    timeout: int = 60                # 容器最大存活时间 (秒)
    volumes: dict[str, str] = {}     # 挂载卷
```

### 2.2 沙箱化工具执行

当会话启用沙箱时，`BashTool` 和 `CodeSandboxTool` 自动切换到沙箱执行:

```python
class SandboxedBashTool(BashTool):
    """沙箱版 Bash 工具"""

    async def execute(self, command: str, timeout: int = 30) -> ToolResult:
        """在 Docker 容器中执行命令"""
```

---

## 3. DM 配对 (跨渠道)

### 3.1 统一配对服务 — `whaleclaw/security/pairing.py`

```python
class PairingService:
    """跨渠道的 DM 配对服务"""

    async def generate_code(self, channel: str, peer_id: str) -> str:
        """生成 6 位配对码 (有效期 5 分钟)"""

    async def verify(self, code: str) -> PairingRequest | None:
        """验证配对码"""

    async def approve(self, code: str) -> bool:
        """批准配对请求"""

    async def reject(self, code: str) -> bool:
        """拒绝配对请求"""

    async def list_pending(self) -> list[PairingRequest]:
        """列出待处理的配对请求"""

class PairingRequest(BaseModel):
    code: str
    channel: str
    peer_id: str
    peer_name: str | None = None
    created_at: datetime
    expires_at: datetime
    status: Literal["pending", "approved", "rejected", "expired"]
```

### 3.2 CLI 配对命令

```
whaleclaw pairing
  list                              # 列出待处理配对
  approve <code>                    # 批准配对
  reject <code>                     # 拒绝配对
```

### 3.3 全局白名单

```python
class AllowListStore:
    """跨渠道白名单存储"""

    async def is_allowed(self, channel: str, peer_id: str) -> bool: ...
    async def add(self, channel: str, peer_id: str, approved_by: str) -> None: ...
    async def remove(self, channel: str, peer_id: str) -> None: ...
    async def list_all(self, channel: str | None = None) -> list[AllowListEntry]: ...
```

存储: `~/.whaleclaw/credentials/allowlist.db` (SQLite)

---

## 4. 权限模型

### 4.1 工具权限 — `whaleclaw/security/permissions.py`

```python
class ToolPermission(BaseModel):
    """工具权限配置"""
    allow: list[str] = ["*"]         # 允许的工具 ("*" = 全部)
    deny: list[str] = []             # 禁止的工具

class SecurityPolicy(BaseModel):
    """会话安全策略"""
    sandbox: bool = False
    tools: ToolPermission = ToolPermission()
    max_tool_rounds: int = 25
    allow_file_write: bool = True
    allow_network: bool = True
    allowed_paths: list[str] = []    # 允许访问的文件路径 (空 = 不限)
    denied_paths: list[str] = [      # 禁止访问的路径
        "/etc/", "/var/", "/usr/", "/sys/", "/proc/",
        "~/.ssh/", "~/.gnupg/",
    ]
```

### 4.2 权限检查

```python
class PermissionChecker:
    """工具调用前的权限检查"""

    def check_tool(self, tool_name: str, policy: SecurityPolicy) -> bool:
        """检查工具是否被允许"""

    def check_path(self, path: str, policy: SecurityPolicy, write: bool = False) -> bool:
        """检查文件路径是否被允许"""

    def check_command(self, command: str, policy: SecurityPolicy) -> bool:
        """检查 bash 命令是否被允许 (危险命令拦截)"""
```

危险命令黑名单:
- `rm -rf /`
- `mkfs`
- `dd if=/dev/zero`
- `:(){ :|:& };:` (fork bomb)
- 修改系统关键文件

---

## 5. Agent 间通信

### 5.1 会话工具 — `whaleclaw/tools/sessions.py`

对标 OpenClaw 的 `sessions_*` 工具:

```python
class SessionsListTool(Tool):
    """列出活跃会话"""
    # 返回: 会话 ID、渠道、对话方、最后活动时间

class SessionsHistoryTool(Tool):
    """获取指定会话的消息历史"""
    # 参数: session_id, limit

class SessionsSendTool(Tool):
    """向指定会话发送消息"""
    # 参数: session_id, message
    # 可选: reply_back (等待对方回复)
```

---

## 6. 审计日志

### 6.1 审计记录 — `whaleclaw/security/audit.py`

```python
class AuditEvent(BaseModel):
    timestamp: datetime
    event_type: str                  # "tool_call", "message", "auth", "config_change"
    session_id: str | None
    channel: str | None
    peer_id: str | None
    details: dict[str, Any]

class AuditLogger:
    """审计日志记录器"""

    async def log(self, event: AuditEvent) -> None:
        """记录审计事件"""

    async def query(
        self,
        event_type: str | None = None,
        session_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """查询审计日志"""
```

存储: `~/.whaleclaw/logs/audit.db` (SQLite)

记录的事件:
- 工具调用 (工具名、参数、结果、耗时)
- 消息收发 (渠道、发送者、内容摘要)
- 认证事件 (登录、配对)
- 配置变更
- 插件加载/卸载
- 安全拦截 (权限拒绝、危险命令)

---

## 7. 配置扩展

```python
class SecurityConfig(BaseModel):
    sandbox_mode: SandboxMode = SandboxMode.NON_MAIN
    dm_policy: Literal["pairing", "open", "closed"] = "pairing"
    audit: bool = True

class RoutingConfig(BaseModel):
    rules: list[RoutingRule] = []

class WhaleclawConfig(BaseModel):
    # ... 已有字段
    security: SecurityConfig = SecurityConfig()
    routing: RoutingConfig = RoutingConfig()
```

---

## 验收标准

### AC-1: 路由规则
配置飞书群聊走沙箱，WebChat 走主 Agent:
- 飞书群聊消息在沙箱中执行工具
- WebChat 消息在主机上执行工具

### AC-2: Docker 沙箱
在沙箱会话中执行 `bash: rm -rf /tmp/test`:
- 命令在 Docker 容器中执行
- 主机文件系统不受影响

### AC-3: DM 配对
1. 未知飞书用户发消息 -> 收到配对码
2. `whaleclaw pairing list` 显示待处理请求
3. `whaleclaw pairing approve <code>` 后用户可正常对话

### AC-4: 权限拦截
在受限会话中:
- 尝试调用被禁止的工具 -> 返回权限错误
- 尝试读取 `~/.ssh/id_rsa` -> 返回路径禁止
- 尝试执行 `rm -rf /` -> 返回危险命令拦截

### AC-5: Agent 间通信
```
用户 (会话A): 帮我查看会话B的最近消息
Agent: [调用 sessions_history 工具]
Agent: 会话B的最近消息是: ...
```

### AC-6: 审计日志
```bash
# 查看最近的工具调用审计
whaleclaw audit --type tool_call --limit 10
```

---

## 文件清单

```
whaleclaw/routing/__init__.py
whaleclaw/routing/router.py
whaleclaw/routing/rules.py
whaleclaw/security/__init__.py
whaleclaw/security/sandbox.py
whaleclaw/security/pairing.py
whaleclaw/security/permissions.py
whaleclaw/security/auth.py               (更新: 扩展认证)
whaleclaw/security/audit.py
whaleclaw/agent/pool.py                  (AgentPool)
whaleclaw/tools/sessions.py
whaleclaw/cli/pairing_cmd.py
whaleclaw/cli/audit_cmd.py
tests/test_routing/test_router.py
tests/test_routing/test_rules.py
tests/test_security/test_sandbox.py
tests/test_security/test_pairing.py
tests/test_security/test_permissions.py
tests/test_security/test_audit.py
tests/test_tools/test_sessions.py
```
