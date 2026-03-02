#!/bin/bash
# ═══════════════════════════════════════════════
#  WhaleClaw — 安装为后台守护进程 (launchd)
# ═══════════════════════════════════════════════
cd "$(dirname "$0")"
PROJECT_DIR="$(pwd)"
STARTUP_SCRIPT="$PROJECT_DIR/启动 WhaleClaw.command"

# 服务名称（可传参，用于多实例）
SERVICE_NAME="${1:-com.whaleclaw.gateway}"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"

# 隔离的日志目录
LOG_DIR="$HOME/.whaleclaw/logs"
mkdir -p "$LOG_DIR"

# 对应的 WHALECLAW_HOME，如果没有传入环境变量，使用默认的
DATA_DIR="${WHALECLAW_HOME:-$HOME/.whaleclaw}"

echo "  ═══ 配置 WhaleClaw 后台服务 ═══"
echo "  服务名称: $SERVICE_NAME"
echo "  项目路径: $PROJECT_DIR"
echo "  数据目录: $DATA_DIR"
echo ""

# 生成 plist 文件内容
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$SERVICE_NAME</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$STARTUP_SCRIPT</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>WHALECLAW_NO_BROWSER</key>
        <string>1</string>
        <key>WHALECLAW_HOME</key>
        <string>$DATA_DIR</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$LOG_DIR/${SERVICE_NAME}.out.log</string>

    <key>StandardErrorPath</key>
    <string>$LOG_DIR/${SERVICE_NAME}.err.log</string>
</dict>
</plist>
EOF

# 加载服务
echo "  正在加载服务..."
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo ""
echo "  ✅ 服务已部署并启动，系统开机会自动运行，崩溃会自动重启！"
echo ""
echo "  查看日志: tail -f $LOG_DIR/${SERVICE_NAME}.out.log"
echo "  停止服务: launchctl unload $PLIST_PATH"
echo "  启动服务: launchctl load $PLIST_PATH"
echo "  ──────────────────────────────────────────"
echo "  如果你想部署 dev 分支的多实例，可以带参数运行："
echo "  WHALECLAW_HOME=~/.whaleclaw-dev ./安装后台服务.command com.whaleclaw.dev"
echo ""
