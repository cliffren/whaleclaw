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

**使用体验增强 (Real-time UX)**
Telegram 渠道内置了“单消息动态刷新”机制以避免刷屏：
- **思考动画**：Agent 分析时会显示动态的 `💭 思考中...`
- **动作预览**：调用工具（比如执行 bash 命令）时，会折叠显示参数预览（如 `[运行] bash (ls -la)`）
- **网络重试预警**：当大模型接口波动触发重试时，会亮起 `⚠️ 网络重试中` 提示
- **速率流控**：严格处理了 Telegram 的 1秒/消息 发送频率限制，保障长交互不被封禁

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

### 4. 异步挂起后台任务 (Async Background Tasks)

专门解决大模型执行长时间阻塞脚本（如：跑测试、模型训练、复杂编译、数据抓取）导致的 Token 严重浪费和 Agent 超时假死问题。

**使用体验**
只需在聊天时自然语言要求：*“在后台跑一下这个命令”* 或 *“帮我用挂起的方式执行训练脚本”*。

**核心机制**
1. **瞬间脱离 (`bash_background` 工具)**:
   Agent 会将命令挂起到 OS 后台（通过新建进程组独立执行），并立即回到你面前汇报“任务已提交，PID=xxx”，当前对话轮次**瞬间结束**，Token 消费到此停止。
2. **零开销轮询 (`TaskMonitor` 引擎)**:
   Gateway 会在内存中起一个 `asyncio` 线程，每隔 10 秒调用底层的 `os.kill(pid, 0)` 确认进程生死。此过程**0 CPU 占用，0 Token 挂载**。
3. **事件唤醒 (Session Wakeup)**:
   一旦进程死亡出块（任务成功或报错结束），系统会自动抓取日志（位于 `WHALECLAW_HOME/bg_tasks/<task_id>.log`）的最后输出片段。
   直接以 **[系统通知]** 的名义将结果以新消息的形式，直接推送到你的原对话流中（无论你身在 WebChat 还是 Telegram）。Agent 会像看到你发消息一样，被**重新唤醒**，根据最新的结果接续工作。

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

**多实例独立部署示例：**

假设我们要创建第二个独立实例（使用当前相同的代码目录）：

```bash
# 1. 为新实例配置独立的 API 和端口 (例如修改为 18667)
WHALECLAW_HOME=~/.whaleclaw-instance2 ./修改配置.command

# 2. 将新实例安装为独立的后台服务，指定独一无二的服务名
WHALECLAW_HOME=~/.whaleclaw-instance2 ./安装后台服务.command com.whaleclaw.instance2
```

**工作区 (Workspace) 隔离机制**
为了防止多个实例的 Agent 操作系统文件时发生冲突（例如两个实例同时去写同一个文件），启动脚本默认会把每个实例的当前运行目录 (`cwd`) 强制切换到它自己的配置目录下：
- 实例 1 的 Bash / Python Agent 会在 `~/.whaleclaw/workspace` 内干活。
- 实例 2 的 Agent 会在 `~/.whaleclaw-instance2/workspace` 内干活。

这保证了无论多少个 bot 并发运行，它们生成的文件、爬取的数据在物理层都是完全隔离和安全的。

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
