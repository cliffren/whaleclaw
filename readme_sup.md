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

## 持久化运行与多实例部署

WhaleClaw 现在内置了一个脚本，可以一键将其安装为 macOS 的后台进程（通过 `launchctl`），开机自启动并在崩溃时自动重启。

**正常后台启动（唯一实例）**：
```bash
./安装后台服务.command
```
- 服务名称默认是 `com.whaleclaw.gateway`。
- 日志文件将保存在 `~/.whaleclaw/logs/` 下。

---

如果希望在同一台机器上运行多个**完全独立**的 WhaleClaw 实例（比如扮演不同角色，绑定不同 Telegram/Feishu 机器人）：

可以通过 `WHALECLAW_HOME` 环境变量指定独立的配置和数据目录。各个实例的配置 / 会话 / 记忆 / 凭证 会完全隔离。

**多实例后台独立部署示例：**

假设我们要创建第二个独立实例（使用当前相同的代码目录）：

```bash
# 1. 为新实例配置独立的 API 和端口 (例如修改为 18667)
WHALECLAW_HOME=~/.whaleclaw-instance2 ./修改配置.command

# 2. 将新实例安装为独立的后台服务，指定独一无二的服务名
WHALECLAW_HOME=~/.whaleclaw-instance2 ./安装后台服务.command com.whaleclaw.instance2
```

**管理后台服务**
部署后，你可以通过 macOS 标准命令进行管理：
```bash
# 查看实例日志
tail -f ~/.whaleclaw/logs/com.whaleclaw.gateway.out.log
tail -f ~/.whaleclaw-instance2/logs/com.whaleclaw.instance2.out.log

# 停止或启动服务
launchctl unload ~/Library/LaunchAgents/com.whaleclaw.instance2.plist
launchctl load ~/Library/LaunchAgents/com.whaleclaw.instance2.plist
```
