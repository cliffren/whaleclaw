# Phase 4: 飞书渠道

## 目标

接入飞书 (Feishu/Lark) 机器人，实现:
1. 单聊 + 群聊消息收发
2. 富文本和卡片消息 (Interactive Card)
3. 流式卡片更新 (模拟打字效果)
4. 飞书工具集 (文档/知识库/云盘/多维表格/权限)
5. 媒体处理 (图片/文件上传下载)
6. Webhook 安全验证 + DM 配对

对标 OpenClaw 的 `extensions/feishu/` 扩展。

## 前置条件

- Phase 1 + 2 + 3 全部完成
- 飞书开放平台应用 (App ID + App Secret)
- 飞书机器人已配置事件订阅

---

## 1. 飞书 API 客户端

### 1.1 客户端 — `whaleclaw/channels/feishu/client.py`

```python
class FeishuClient:
    """飞书开放平台 API 客户端"""

    def __init__(self, app_id: str, app_secret: str):
        self._app_id = app_id
        self._app_secret = app_secret
        self._tenant_access_token: str | None = None
        self._token_expires_at: float = 0

    async def _ensure_token(self) -> str:
        """获取/刷新 tenant_access_token"""

    async def request(self, method: str, path: str, **kwargs) -> dict:
        """通用 API 请求，自动处理 token 刷新和错误"""

    # 消息 API
    async def send_message(self, receive_id: str, msg_type: str, content: str, receive_id_type: str = "open_id") -> dict: ...
    async def reply_message(self, message_id: str, msg_type: str, content: str) -> dict: ...
    async def update_message(self, message_id: str, content: str) -> dict: ...
    async def get_message(self, message_id: str) -> dict: ...

    # 媒体 API
    async def upload_image(self, image: bytes, image_type: str = "message") -> str: ...
    async def upload_file(self, file: bytes, filename: str, file_type: str) -> str: ...
    async def download_resource(self, message_id: str, file_key: str) -> bytes: ...

    # 用户 API
    async def get_user_info(self, user_id: str, user_id_type: str = "open_id") -> dict: ...
```

### 1.2 配置 Schema

```python
class FeishuConfig(BaseModel):
    app_id: str
    app_secret: str
    verification_token: str | None = None    # 事件订阅验证 token
    encrypt_key: str | None = None           # 事件加密 key
    allow_from: list[str] = []               # 允许的用户 open_id 列表
    groups: dict[str, GroupConfig] = {}       # 群组配置
    dm_policy: Literal["pairing", "open", "closed"] = "pairing"
    webhook_path: str = "/webhook/feishu"

class GroupConfig(BaseModel):
    require_mention: bool = True             # 群聊需要 @机器人
    activation: Literal["mention", "always"] = "mention"
```

环境变量:
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_VERIFICATION_TOKEN`
- `FEISHU_ENCRYPT_KEY`

---

## 2. 事件处理

### 2.1 Webhook 端点 — `whaleclaw/channels/feishu/webhook.py`

```python
@router.post("/webhook/feishu")
async def feishu_webhook(request: Request) -> Response:
    """
    飞书事件订阅 Webhook:
    1. URL 验证 (challenge 响应)
    2. 签名验证 (encrypt_key)
    3. 事件分发
    """
```

事件类型处理:
- `im.message.receive_v1` — 收到消息
- `im.message.reaction.created_v1` — 消息被表情回复
- `im.chat.member.bot.added_v1` — 机器人被加入群聊
- `im.chat.member.bot.deleted_v1` — 机器人被移出群聊

### 2.2 签名验证

```python
def verify_signature(timestamp: str, nonce: str, encrypt_key: str, body: bytes, signature: str) -> bool:
    """验证飞书 Webhook 签名"""
    # sha256(timestamp + nonce + encrypt_key + body)
```

### 2.3 事件解密

```python
def decrypt_event(encrypt_key: str, encrypted: str) -> dict:
    """AES-256-CBC 解密飞书事件"""
```

---

## 3. 消息处理

### 3.1 Bot 处理器 — `whaleclaw/channels/feishu/bot.py`

```python
class FeishuBot:
    """飞书消息处理核心"""

    async def handle_message(self, event: dict) -> None:
        """
        处理收到的消息:
        1. 提取消息内容 (文本/图片/文件)
        2. 检查 DM 策略 (pairing/allowFrom)
        3. 群聊: 检查是否 @机器人
        4. 路由到 Agent
        5. 发送回复 (卡片消息)
        """

    def extract_text(self, message: dict) -> str:
        """从飞书消息结构中提取纯文本"""

    def is_bot_mentioned(self, message: dict, bot_open_id: str) -> bool:
        """检查消息是否 @了机器人"""

    def strip_bot_mention(self, text: str, bot_name: str) -> str:
        """移除消息中的 @机器人 标记"""
```

### 3.2 消息去重 — `whaleclaw/channels/feishu/dedup.py`

飞书可能重复推送事件，需要去重:

```python
class MessageDedup:
    """基于 message_id 的消息去重，TTL 5 分钟"""

    def is_duplicate(self, message_id: str) -> bool: ...
    def mark(self, message_id: str) -> None: ...
```

### 3.3 @提及处理 — `whaleclaw/channels/feishu/mention.py`

```python
def extract_mention_targets(message: dict) -> list[MentionTarget]:
    """提取消息中的 @提及目标"""

def format_mention_for_text(user_id: str, name: str) -> str:
    """格式化 @提及 (文本消息)"""

def format_mention_for_card(user_id: str, name: str) -> dict:
    """格式化 @提及 (卡片消息)"""
```

---

## 4. 卡片消息

### 4.1 卡片构建 — `whaleclaw/channels/feishu/card.py`

```python
class FeishuCard:
    """飞书交互卡片构建器"""

    @staticmethod
    def text_card(content: str, title: str | None = None) -> dict:
        """纯文本卡片 (支持 Markdown)"""

    @staticmethod
    def streaming_card(initial_text: str = "") -> dict:
        """流式更新卡片 (初始状态)"""

    @staticmethod
    def error_card(error: str) -> dict:
        """错误提示卡片"""

    @staticmethod
    def tool_call_card(tool_name: str, arguments: dict, result: str | None = None) -> dict:
        """工具调用卡片"""
```

### 4.2 流式卡片更新 — `whaleclaw/channels/feishu/streaming_card.py`

模拟 Agent 打字效果:

```python
class StreamingCard:
    """
    流式更新飞书卡片:
    1. 先发送一条空卡片 (显示 "思考中...")
    2. 每收到一段 stream 文本，更新卡片内容
    3. 工具调用时追加工具卡片段
    4. 完成后更新为最终卡片
    """

    def __init__(self, client: FeishuClient, message_id: str): ...

    async def update(self, content: str) -> None:
        """更新卡片内容 (节流: 最快 500ms 更新一次)"""

    async def append_tool_call(self, tool_name: str, result: str) -> None:
        """追加工具调用结果"""

    async def finalize(self, content: str) -> None:
        """最终更新"""
```

节流策略: 最少间隔 500ms 更新一次，避免触发飞书 API 限流。

---

## 5. 飞书渠道插件

### 5.1 渠道注册 — `whaleclaw/channels/feishu/__init__.py`

```python
class FeishuChannel(ChannelPlugin):
    name = "feishu"

    async def start(self) -> None:
        """初始化飞书客户端，注册 Webhook 路由"""

    async def stop(self) -> None:
        """清理资源"""

    async def send(self, peer_id: str, content: str, **kwargs) -> None:
        """发送消息 (自动选择文本/卡片)"""

    async def send_stream(self, peer_id: str, stream) -> None:
        """流式发送 (通过卡片更新)"""
```

---

## 6. 飞书工具集

对标 OpenClaw feishu 扩展中的工具:

### 6.1 文档工具 — `whaleclaw/channels/feishu/tools/docx.py`

```python
class FeishuDocxTool(Tool):
    """飞书文档操作"""
    # 功能: 创建文档、读取文档内容、更新文档、获取文档列表
```

### 6.2 知识库工具 — `whaleclaw/channels/feishu/tools/wiki.py`

```python
class FeishuWikiTool(Tool):
    """飞书知识库操作"""
    # 功能: 搜索知识库、获取节点内容、创建节点
```

### 6.3 云盘工具 — `whaleclaw/channels/feishu/tools/drive.py`

```python
class FeishuDriveTool(Tool):
    """飞书云盘操作"""
    # 功能: 列出文件、上传文件、下载文件、创建文件夹
```

### 6.4 多维表格工具 — `whaleclaw/channels/feishu/tools/bitable.py`

```python
class FeishuBitableTool(Tool):
    """飞书多维表格操作"""
    # 功能: 读取表格数据、写入记录、创建表格、查询记录
```

### 6.5 权限工具 — `whaleclaw/channels/feishu/tools/perm.py`

```python
class FeishuPermTool(Tool):
    """飞书权限管理"""
    # 功能: 查看文档权限、设置协作者、转移所有者
```

---

## 7. 媒体处理

### 7.1 媒体收发 — `whaleclaw/channels/feishu/media.py`

```python
async def handle_image_message(client: FeishuClient, message: dict) -> str:
    """处理图片消息: 下载图片 -> 存储 -> 返回本地路径"""

async def handle_file_message(client: FeishuClient, message: dict) -> str:
    """处理文件消息: 下载文件 -> 存储 -> 返回本地路径"""

async def send_image(client: FeishuClient, peer_id: str, image_path: str) -> None:
    """发送图片: 上传 -> 发送图片消息"""

async def send_file(client: FeishuClient, peer_id: str, file_path: str) -> None:
    """发送文件: 上传 -> 发送文件消息"""
```

---

## 8. DM 安全

### 8.1 配对机制

当 `dm_policy = "pairing"` 时:

1. 未知用户发消息 -> 生成 6 位配对码 -> 回复配对码
2. 管理员通过 CLI 确认: `whaleclaw pairing approve feishu <code>`
3. 确认后用户加入 allowFrom 白名单
4. 后续消息正常处理

### 8.2 白名单

```python
class FeishuAllowList:
    """飞书用户白名单管理"""

    async def is_allowed(self, open_id: str) -> bool: ...
    async def add(self, open_id: str) -> None: ...
    async def remove(self, open_id: str) -> None: ...
    async def list_all(self) -> list[str]: ...
```

白名单持久化到 `~/.whaleclaw/credentials/feishu_allowlist.json`。

---

## 验收标准

### AC-1: 单聊消息
飞书单聊发送 "你好"，机器人回复卡片消息。

### AC-2: 群聊 @提及
群聊中 @机器人 + 问题，机器人回复。
不 @机器人时不回复。

### AC-3: 流式卡片
发送需要较长回复的问题:
- 先显示 "思考中..." 卡片
- 卡片内容逐步更新
- 最终显示完整回复

### AC-4: 工具调用
发送 "帮我查看知识库中关于 XX 的文档":
- 卡片中显示工具调用过程
- 最终回复包含文档内容

### AC-5: 图片处理
发送一张图片给机器人:
- 机器人能识别图片内容 (通过多模态模型)
- 回复描述图片内容

### AC-6: Webhook 安全
- 无效签名的请求被拒绝 (HTTP 403)
- 重复事件被去重

### AC-7: DM 配对
- 未知用户发消息收到配对码
- CLI 确认后用户可正常对话

---

## 文件清单

```
whaleclaw/channels/feishu/__init__.py
whaleclaw/channels/feishu/client.py
whaleclaw/channels/feishu/bot.py
whaleclaw/channels/feishu/card.py
whaleclaw/channels/feishu/streaming_card.py
whaleclaw/channels/feishu/webhook.py
whaleclaw/channels/feishu/media.py
whaleclaw/channels/feishu/mention.py
whaleclaw/channels/feishu/dedup.py
whaleclaw/channels/feishu/config.py
whaleclaw/channels/feishu/allowlist.py
whaleclaw/channels/feishu/tools/__init__.py
whaleclaw/channels/feishu/tools/docx.py
whaleclaw/channels/feishu/tools/wiki.py
whaleclaw/channels/feishu/tools/drive.py
whaleclaw/channels/feishu/tools/bitable.py
whaleclaw/channels/feishu/tools/perm.py
whaleclaw/channels/manager.py              (更新)
tests/test_channels/test_feishu/__init__.py
tests/test_channels/test_feishu/test_client.py
tests/test_channels/test_feishu/test_bot.py
tests/test_channels/test_feishu/test_card.py
tests/test_channels/test_feishu/test_webhook.py
tests/test_channels/test_feishu/test_dedup.py
tests/test_channels/test_feishu/test_mention.py
tests/test_channels/test_feishu/test_streaming_card.py
tests/test_channels/test_feishu/test_media.py
```
