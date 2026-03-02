# WhaleClaw — 更新补充说明

本文档记录对原版 WhaleClaw 新增的功能与配置方法。

---

## 新增功能

### 1. 向量记忆管理（Embedding Memory）

长期记忆默认启用向量存储，支持语义召回。

**存储位置**
```
~/.whaleclaw/
├── whaleclaw.db     # 会话 & 消息历史
└── memory/
    └── memory.db    # 长期记忆（文本 + embedding 向量）
```

**向量模型**：`BAAI/bge-small-zh-v1.5`（通过 fastembed 本地运行，无需额外 API）

**安装向量依赖**（首次运行启动脚本会自动安装）：
```bash
pip install "whaleclaw[embedding]"
```

未安装时自动降级为关键词匹配，记忆仍正常保存。

---

### 2. Telegram 渠道

支持通过 Telegram 私聊或群组 @Bot 与 Agent 交互。

**配置步骤**
1. 在 Telegram 搜索 **@BotFather** → `/newbot` → 获取 Token
2. 运行 `修改配置.command` → 选 `7) 配置 Telegram 渠道`
3. 输入 Token（脚本自动验证连通性）
4. 重启 Gateway 生效

**Bot 命令菜单**（启动时自动注册）

| 命令 | 说明 |
|------|------|
| `/new` `/reset` | 重置当前会话 |
| `/status` | 显示会话状态（ID、模型、思考深度、消息数） |
| `/models` | 列出可切换模型 |
| `/model <name>` | 切换模型，如 `/model bailian/qwen3.5-plus` |
| `/think <level>` | 设置思考深度：`off` / `low` / `medium` / `high` |
| `/compact` | 压缩会话上下文（生成 L0/L1 摘要） |

**安全配置（用户白名单）**

在配置菜单 → `3) 管理允许用户 ID` 添加 Telegram User ID 后，DM 策略自动切为 `closed`（仅白名单用户可用）。

> 不知道自己的 User ID？在 Telegram 搜索 **@userinfobot** 发任意消息即可。

---

### 3. 阿里百炼（Bailian）模型接入

使用阿里云百炼平台的 OpenAI 兼容接口，一个 API Key 可用多个模型。

**配置步骤**
1. 前往 [百炼控制台](https://bailian.console.aliyun.com/) 获取 API Key
2. 运行 `修改配置.command` → `1) 配置 AI 模型` → `9) 阿里百炼`
3. 输入 API Key，选择模型验证

**预置模型**

| 模型 ID | 说明 |
|---------|------|
| `bailian/qwen3.5-plus` | 通义千问 3.5 Plus，支持视觉 |
| `bailian/qwen3-max-2026-01-23` | 通义千问 3 Max |
| `bailian/qwen3-coder-next` | 千问代码模型 Next |
| `bailian/qwen3-coder-plus` | 千问代码模型 Plus，支持视觉 |
| `bailian/kimi-k2.5` | 月之暗面 Kimi K2.5，支持视觉 |
| `bailian/MiniMax-M2.5` | MiniMax M2.5 |
| `bailian/glm-5` | 智谱 GLM-5 |
| `bailian/glm-4.7` | 智谱 GLM-4.7 |

**API Endpoint**：`https://dashscope.aliyuncs.com/v1`

---

## 多实例部署

通过 `WHALECLAW_HOME` 环境变量可在同一台机器上运行多个完全独立的 WhaleClaw 实例。

**各实例数据完全隔离：** 配置 / 会话 / 记忆 / 工作目录 / 凭证 / 日志

**正常启动**（使用默认 `~/.whaleclaw`）：
```bash
./启动\ WhaleClaw.command
```

**启动第二个实例：**
```bash
# 1. 先配置第二个实例（会读写 ~/.whaleclaw-bob/）
WHALECLAW_HOME=~/.whaleclaw-bob ./修改配置.command

# 2. 在配置里设置一个不同的端口（默认 18666，改为 18667）

# 3. 启动
WHALECLAW_HOME=~/.whaleclaw-bob ./启动\ WhaleClaw.command
```

**注意事项：**
- 每个实例需配置不同的 **Gateway 端口**（`修改配置.command` → `3) 修改 Gateway 端口`）
- 每个 Telegram 实例需要一个独立的 **Bot Token**（一个 Token 只支持一个 polling 连接）
- `WHALECLAW_HOME` 支持绝对路径和 `~` 前缀路径
