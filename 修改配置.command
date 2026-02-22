#!/bin/bash
# ═══════════════════════════════════════════════
#  WhaleClaw — 修改配置
# ═══════════════════════════════════════════════
cd "$(dirname "$0")"

CONFIG_DIR="$HOME/.whaleclaw"
CONFIG_FILE="$CONFIG_DIR/whaleclaw.json"
PYTHON="./python/bin/python3.12"

# 自动检测本地代理（用于访问海外 API）
if [ -z "$https_proxy" ]; then
    for port in 7897 7890 1087 8080; do
        if nc -z 127.0.0.1 $port 2>/dev/null; then
            export https_proxy="http://127.0.0.1:$port"
            export http_proxy="http://127.0.0.1:$port"
            break
        fi
    done
fi

mkdir -p "$CONFIG_DIR"

# 如果配置文件不存在，创建默认配置
if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" << 'DEFAULTCFG'
{
  "gateway": {
    "port": 18789,
    "bind": "127.0.0.1",
    "verbose": false,
    "auth": { "mode": "none", "password": null }
  },
  "agent": {
    "model": "deepseek/deepseek-chat",
    "max_tool_rounds": 25,
    "thinking_level": "off"
  },
  "models": {
    "anthropic": { "api_key": null, "base_url": null },
    "openai":    { "api_key": null, "base_url": null },
    "deepseek":  { "api_key": null, "base_url": null },
    "qwen":      { "api_key": null, "base_url": null },
    "zhipu":     { "api_key": null, "base_url": null },
    "minimax":   { "api_key": null, "base_url": null },
    "moonshot":  { "api_key": null, "base_url": null },
    "google":    { "api_key": null, "base_url": null },
    "nvidia":    { "api_key": null, "base_url": null }
  },
  "security": {
    "sandbox_mode": "non-main",
    "dm_policy": "pairing",
    "audit": true
  }
}
DEFAULTCFG
    echo ""
    echo "  ✅ 已创建默认配置文件: $CONFIG_FILE"
fi

# ── 用 Python 读取当前状态 ──
read_status() {
    "$PYTHON" << 'PYEOF'
import json, pathlib, os

p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
gw = cfg.get('gateway', {})
ag = cfg.get('agent', {})
au = gw.get('auth', {})
models = cfg.get('models', {})

port = gw.get('port', 18789)
bind = gw.get('bind', '127.0.0.1')
auth_mode = au.get('mode', 'none')
model = ag.get('model', '未设置')
thinking = ag.get('thinking_level', 'off')

# 找出已配置的提供商和模型
configured = []
for name, conf in models.items():
    key = conf.get('api_key')
    if not key:
        continue
    cm = conf.get('configured_models', [])
    verified = [m for m in cm if m.get('verified')]
    total = len(cm)
    key_preview = key[:8] + '...' + key[-4:] if len(str(key)) > 16 else str(key)
    if verified:
        names = ', '.join(m.get('name') or m['id'] for m in verified[:3])
        extra = f' +{len(verified)-3}' if len(verified) > 3 else ''
        configured.append(f'{name} | {len(verified)}/{total} 模型 | {names}{extra}')
    else:
        configured.append(f'{name} | Key: {key_preview} (未配置模型)')

print(f'PORT={port}')
print(f'BIND={bind}')
print(f'AUTH_MODE={auth_mode}')
print(f'MODEL={model}')
print(f'THINKING={thinking}')
print(f'NUM_KEYS={len(configured)}')
for i, c in enumerate(configured):
    print(f'KEY_{i}={c}')
PYEOF
}

eval "$(read_status)"

show_menu() {
    clear
    echo ""
    echo "  ═══════════════════════════════════════════════════"
    echo "  🐋 WhaleClaw 配置管理"
    echo "  ═══════════════════════════════════════════════════"
    echo ""
    echo "  📁 配置文件: $CONFIG_FILE"
    echo ""
    echo "  ┌─────────────── 当前状态 ───────────────┐"
    echo "  │  端口:     ${PORT}"
    echo "  │  地址:     http://${BIND}:${PORT}"
    echo "  │  认证:     ${AUTH_MODE}"
    echo "  │  默认模型: ${MODEL}"
    echo "  │  思考深度: ${THINKING}"
    echo "  │  已配置:   ${NUM_KEYS} 个提供商"

    i=0
    while [ $i -lt ${NUM_KEYS:-0} ]; do
        eval "info=\$KEY_$i"
        echo "  │    → $info"
        i=$((i+1))
    done

    echo "  └────────────────────────────────────────┘"
    echo ""
    echo "  ─── 操作菜单 ────────────────────────────"
    echo ""
    echo "  1) 配置 AI 模型"
    echo "  2) 修改 Gateway 端口"
    echo "  3) 设置登录密码"
    echo "  4) 编辑配置文件 (系统编辑器)"
    echo "  5) 运行诊断 (doctor)"
    echo "  6) 查看完整配置"
    echo "  0) 退出"
    echo ""
}

# ══════════════════════════════════════════════
#  通用 API 验证函数
#  参数: provider model api_key base_url
#  返回: 0=成功, 1=失败
# ══════════════════════════════════════════════
verify_api() {
    local v_provider="$1" v_model="$2" v_apikey="$3" v_base_url="$4"

    "$PYTHON" << PYEOF
import httpx, json, socket, sys, os

api_key = '''$v_apikey'''
base_url = '''$v_base_url'''
provider = '''$v_provider'''
model = '''$v_model'''

def find_proxy():
    for port in (7897, 7890, 1087, 8080):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect(('127.0.0.1', port))
            s.close()
            return f'http://127.0.0.1:{port}'
        except Exception:
            pass
    return None

NEEDS_PROXY = {'anthropic', 'openai', 'google'}

headers = {}
url = ''
body = {}

if provider == 'anthropic':
    url = f'{base_url}/v1/messages'
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'Content-Type': 'application/json',
    }
    body = {'model': model, 'max_tokens': 5, 'messages': [{'role': 'user', 'content': 'hi'}]}
elif provider == 'google':
    url = f'{base_url}/models/{model}:generateContent?key={api_key}'
    headers = {'Content-Type': 'application/json'}
    body = {'contents': [{'parts': [{'text': 'hi'}]}], 'generationConfig': {'maxOutputTokens': 5}}
else:
    url = f'{base_url}/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    body = {'model': model, 'max_tokens': 5, 'messages': [{'role': 'user', 'content': 'hi'}]}

def try_request(proxy_url=None):
    kwargs = {'timeout': 15}
    if proxy_url:
        kwargs['proxy'] = proxy_url
    with httpx.Client(**kwargs) as client:
        return client.post(url, json=body, headers=headers)

resp = None

if provider in NEEDS_PROXY:
    proxy = os.environ.get('https_proxy') or os.environ.get('HTTP_PROXY') or find_proxy()
    if proxy:
        print(f'  📡 代理: {proxy}')
    try:
        resp = try_request(proxy)
    except (httpx.ConnectError, httpx.TimeoutException):
        if proxy:
            print('  ⚠️  代理失败，尝试直连...')
            try:
                resp = try_request(None)
            except Exception:
                print(f'  ❌ 无法连接 {base_url}')
                sys.exit(1)
        else:
            print(f'  ❌ 无法连接 {base_url}')
            sys.exit(1)
else:
    print('  📡 直连')
    try:
        resp = try_request(None)
    except (httpx.ConnectError, httpx.TimeoutException):
        proxy = os.environ.get('https_proxy') or os.environ.get('HTTP_PROXY') or find_proxy()
        if proxy:
            print(f'  ⚠️  直连失败，尝试代理 {proxy} ...')
            try:
                resp = try_request(proxy)
            except Exception:
                print(f'  ❌ 代理也失败')
                sys.exit(1)
        else:
            print(f'  ❌ 无法连接 {base_url}')
            sys.exit(1)

if resp.status_code in (200, 201):
    print('  \033[32m✅ 验证成功\033[0m')
elif resp.status_code == 401:
    print('  \033[31m❌ API Key 无效 (401)\033[0m')
    sys.exit(1)
elif resp.status_code == 403:
    print('  \033[31m❌ 权限不足 (403)\033[0m')
    sys.exit(1)
elif resp.status_code == 404:
    print(f'  \033[31m❌ 模型不存在: {model} (404)\033[0m')
    sys.exit(1)
elif resp.status_code == 429:
    print('  \033[33m⚠️  速率限制 (429)，Key 有效\033[0m')
else:
    print(f'  \033[33m⚠️  返回 {resp.status_code}\033[0m')
    try:
        err = resp.json()
        if 'error' in err:
            msg = err['error'].get('message', '') if isinstance(err['error'], dict) else str(err['error'])
            print(f'  ⚠️  {msg[:120]}')
    except Exception:
        pass
PYEOF
}

# ══════════════════════════════════════════════
#  通用：保存模型到 configured_models
#  参数: provider model_id display_name base_url verified(0/1) thinking
# ══════════════════════════════════════════════
_save_model_entry() {
    local s_provider="$1" s_mid="$2" s_name="$3" s_url="$4" s_verified="$5" s_thinking="$6"

    "$PYTHON" << PYEOF
import json, pathlib, os

p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
prov = cfg.setdefault('models', {}).setdefault('$s_provider', {})
models = prov.setdefault('configured_models', [])

entry = {
    'id': '$s_mid',
    'name': '$s_name',
    'verified': $s_verified == 0,
    'thinking': '$s_thinking',
}
provider_base = prov.get('base_url', '')
if '$s_url' and '$s_url' != provider_base:
    entry['base_url'] = '$s_url'

existing = [i for i, m in enumerate(models) if m.get('id') == '$s_mid']
if existing:
    models[existing[0]] = entry
else:
    models.append(entry)

p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))

v = entry['verified']
c = '\033[32m' if v else '\033[31m'
r = '\033[0m'
tag = '✅' if v else '❌'
tk = f' [thinking={entry["thinking"]}]' if entry['thinking'] != 'off' else ''
print(f'  {c}{tag} {entry["id"]} — {entry["name"]}{tk}{r}')
PYEOF
}

# ══════════════════════════════════════════════
#  每个提供商的推荐模型列表
#  格式: "model_id|display_name|thinking_default"
#  thinking_default: off / low / medium / high
# ══════════════════════════════════════════════

_MODELS_anthropic=(
    "claude-sonnet-4-20250514|Claude Sonnet 4|off"
    "claude-opus-4-20250514|Claude Opus 4|off"
    "claude-sonnet-4-20250514|Claude Sonnet 4 (思考)|medium"
    "claude-opus-4-20250514|Claude Opus 4 (思考)|high"
)
_URL_anthropic="https://api.anthropic.com"

_MODELS_openai=(
    "gpt-4o|GPT-4o|off"
    "gpt-4.1|GPT-4.1|off"
    "o3|o3 (思考)|medium"
    "o4-mini|o4-mini (思考)|medium"
)
_URL_openai="https://api.openai.com/v1"

_MODELS_deepseek=(
    "deepseek-chat|DeepSeek Chat|off"
    "deepseek-reasoner|DeepSeek Reasoner (思考)|high"
)
_URL_deepseek="https://api.deepseek.com"

_MODELS_qwen=(
    "qwen-max|Qwen Max|off"
    "qwen-plus|Qwen Plus|off"
    "qwq-plus|QwQ Plus (思考)|medium"
)
_URL_qwen="https://dashscope.aliyuncs.com/compatible-mode/v1"

_MODELS_zhipu=(
    "glm-4.7-flash|GLM-4.7 Flash (免费)|off"
    "glm-4.7|GLM-4.7|off"
    "glm-5|GLM-5|off"
)
_URL_zhipu="https://open.bigmodel.cn/api/paas/v4"

_MODELS_minimax=(
    "MiniMax-M2.5|MiniMax M2.5|off"
    "MiniMax-M2.1|MiniMax M2.1|off"
)
_URL_minimax="https://api.minimax.chat/v1"

_MODELS_moonshot=(
    "kimi-k2.5|Kimi K2.5|off"
)
_URL_moonshot="https://api.moonshot.cn/v1"

_MODELS_google=(
    "gemini-3-flash-preview|Gemini 3 Flash|off"
    "gemini-3.1-pro-preview|Gemini 3.1 Pro|off"
    "gemini-3-flash-thinking|Gemini 3 Flash (思考)|medium"
)
_URL_google="https://generativelanguage.googleapis.com/v1beta"

_MODELS_nvidia=(
    "qwen/qwen3.5-397b-a17b|Qwen 3.5 397B 🔧|off"
    "z-ai/glm5|GLM-5 🔧|off"
    "z-ai/glm4.7|GLM-4.7 🔧|off"
    "minimaxai/minimax-m2.1|MiniMax M2.1|off"
    "moonshotai/kimi-k2.5|Kimi K2.5 🔧|off"
    "meta/llama-3.1-405b-instruct|Llama 3.1 405B 🔧|off"
)
_URL_nvidia="https://integrate.api.nvidia.com/v1"

# ══════════════════════════════════════════════
#  通用提供商配置流程
#  参数: provider_name display_label
# ══════════════════════════════════════════════
configure_provider() {
    local pname="$1"
    local plabel="$2"

    echo ""
    echo "  ═══ 配置 $plabel ═══"
    echo ""

    # 获取该 provider 的推荐模型数组和默认 URL (bash 3.2 兼容)
    eval "local default_url=\"\$_URL_${pname}\""

    # ── Step 1: API Key (复用已保存的) ──
    local saved_key
    saved_key=$("$PYTHON" -c "
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
print(cfg.get('models', {}).get('$pname', {}).get('api_key', '') or '')
" 2>/dev/null)

    if [ -n "$saved_key" ]; then
        local preview="${saved_key:0:12}...${saved_key: -4}"
        echo "  已保存的 API Key: $preview"
        read -p "  回车复用，或输入新 Key: " new_key
        if [ -n "$new_key" ]; then
            saved_key="$new_key"
        fi
    else
        read -p "  请输入 $plabel API Key: " saved_key
        if [ -z "$saved_key" ]; then
            echo "  ⚠️  API Key 为空，跳过"
            return
        fi
    fi

    local apikey="$saved_key"

    # ── Step 2: Base URL ──
    echo ""
    echo "  默认 Base URL: $default_url"
    read -p "  如需修改请输入，回车保持默认: " custom_url
    local base_url="${custom_url:-$default_url}"

    # 保存 API Key + Base URL
    "$PYTHON" << PYEOF
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
prov = cfg.setdefault('models', {}).setdefault('$pname', {})
prov['api_key'] = '''$apikey'''
prov['base_url'] = '$base_url'
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print('  ✅ API Key 和 Base URL 已保存')
PYEOF

    # ── Step 3: 显示已配置的模型 ──
    echo ""
    echo "  ─── 已配置的模型 ────────────────"
    "$PYTHON" << PYEOF
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
models = cfg.get('models', {}).get('$pname', {}).get('configured_models', [])
if models:
    for m in models:
        v = m.get('verified', False)
        c = '\033[32m' if v else '\033[31m'
        r = '\033[0m'
        tag = '✅' if v else '❌'
        tk = f' [thinking={m.get("thinking","off")}]' if m.get('thinking','off') != 'off' else ''
        burl = m.get('base_url', '')
        url_info = f'  (URL: {burl})' if burl else ''
        print(f'  {c}{tag} {m["id"]} — {m.get("name","")}{tk}{url_info}{r}')
else:
    print('  (暂无已配置模型)')
PYEOF

    # ── Step 4: 选择要配置的模型 ──
    _provider_model_menu "$pname" "$plabel" "$apikey" "$base_url"
}

# ══════════════════════════════════════════════
#  显示模型菜单并处理选择
# ══════════════════════════════════════════════
_provider_model_menu() {
    local pname="$1" plabel="$2" apikey="$3" base_url="$4"

    # bash 3.2: 用 eval 间接获取数组
    local arr_name="_MODELS_${pname}"
    eval "local count=\${#${arr_name}[@]}"

    echo ""
    echo "  ─── 可选模型 ─────────────────────"
    echo ""

    local i=0
    while [ $i -lt $count ]; do
        eval "local entry=\"\${${arr_name}[$i]}\""
        local mid=$(echo "$entry" | cut -d'|' -f1)
        local mname=$(echo "$entry" | cut -d'|' -f2)
        local mthink=$(echo "$entry" | cut -d'|' -f3)
        local think_label=""
        if [ "$mthink" != "off" ]; then
            think_label=" 💭"
        fi
        echo "    $((i+1))) ${mname}${think_label}"
        i=$((i+1))
    done
    echo "    c) 自定义输入"
    echo "    a) 批量验证以上全部"
    echo "    0) 返回"
    echo ""
    read -p "  选择 [1-${count}/c/a/0]: " mchoice

    case $mchoice in
        0) return ;;
        a|A) _batch_verify_provider "$pname" "$apikey" "$base_url"; return ;;
        c|C)
            read -p "  输入模型 ID: " custom_mid
            read -p "  显示名称: " custom_name
            [ -z "$custom_mid" ] && return
            _configure_single_model "$pname" "$custom_mid" "$custom_name" "$apikey" "$base_url" "off"
            return
            ;;
    esac

    # 数字选择
    if [ "$mchoice" -ge 1 ] 2>/dev/null && [ "$mchoice" -le $count ] 2>/dev/null; then
        local idx=$((mchoice - 1))
        eval "local entry=\"\${${arr_name}[$idx]}\""
        local mid=$(echo "$entry" | cut -d'|' -f1)
        local mname=$(echo "$entry" | cut -d'|' -f2)
        local mthink=$(echo "$entry" | cut -d'|' -f3)
        _configure_single_model "$pname" "$mid" "$mname" "$apikey" "$base_url" "$mthink"
    else
        echo "  ❌ 无效选择"
    fi
}

# ══════════════════════════════════════════════
#  配置单个模型 (验证 + 思考设置 + 保存)
# ══════════════════════════════════════════════
_configure_single_model() {
    local pname="$1" mid="$2" mname="$3" apikey="$4" base_url="$5" default_think="$6"

    echo ""
    echo "  模型: $mid ($mname)"
    echo "  Base URL: $base_url"
    read -p "  此模型使用不同的 Base URL? 回车保持默认: " model_url
    local use_url="${model_url:-$base_url}"

    # 思考模式设置
    local thinking="$default_think"
    if [ "$default_think" != "off" ]; then
        echo ""
        echo "  此模型支持深度思考 (当前: $default_think)"
        echo "    0) off — 关闭"
        echo "    1) low — 轻度"
        echo "    2) medium — 中度"
        echo "    3) high — 深度"
        read -p "  选择思考深度 [0-3, 默认 $default_think]: " tchoice
        case $tchoice in
            0) thinking="off" ;;
            1) thinking="low" ;;
            2) thinking="medium" ;;
            3) thinking="high" ;;
        esac
    else
        echo ""
        echo "  是否启用深度思考? (适用于复杂推理任务)"
        echo "    0) off — 关闭 (默认)"
        echo "    1) low — 轻度"
        echo "    2) medium — 中度"
        echo "    3) high — 深度"
        read -p "  选择 [0-3, 默认 off]: " tchoice
        case $tchoice in
            1) thinking="low" ;;
            2) thinking="medium" ;;
            3) thinking="high" ;;
        esac
    fi

    echo ""
    echo "  ⏳ 验证 $mid ..."
    verify_api "$pname" "$mid" "$apikey" "$use_url"
    local vresult=$?

    _save_model_entry "$pname" "$mid" "$mname" "$use_url" "$vresult" "$thinking"

    if [ "$vresult" -eq 0 ]; then
        echo ""
        read -p "  是否设为默认模型? [y/N]: " set_default
        if echo "$set_default" | grep -qi '^y'; then
            "$PYTHON" -c "
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
cfg.setdefault('agent', {})['model'] = '$pname/$mid'
cfg['agent']['thinking_level'] = '$thinking'
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print('  ✅ 默认模型: $pname/$mid (thinking=$thinking)')
"
        fi
    fi

    echo ""
    read -p "  继续配置其他 $pname 模型? [Y/n]: " cont
    if ! echo "$cont" | grep -qi '^n'; then
        _provider_model_menu "$pname" "" "$apikey" "$base_url"
    fi
}

# ══════════════════════════════════════════════
#  批量验证某 provider 的全部推荐模型
# ══════════════════════════════════════════════
_batch_verify_provider() {
    local pname="$1" apikey="$2" base_url="$3"

    local arr_name="_MODELS_${pname}"
    eval "local count=\${#${arr_name}[@]}"

    echo ""
    echo "  ═══ 批量验证 $count 个模型 ═══"
    echo ""

    local i=0
    local pass_count=0
    while [ $i -lt $count ]; do
        eval "local entry=\"\${${arr_name}[$i]}\""
        local mid=$(echo "$entry" | cut -d'|' -f1)
        local mname=$(echo "$entry" | cut -d'|' -f2)
        local mthink=$(echo "$entry" | cut -d'|' -f3)

        echo "  [$((i+1))/$count] $mid ..."
        verify_api "$pname" "$mid" "$apikey" "$base_url" 2>/dev/null
        local vresult=$?

        _save_model_entry "$pname" "$mid" "$mname" "$base_url" "$vresult" "$mthink"

        if [ $vresult -eq 0 ]; then
            pass_count=$((pass_count + 1))
        fi
        i=$((i + 1))
        echo ""
    done

    echo "  ─────────────────────────────────"
    echo "  验证完成: $pass_count / $count 个模型可用"
    echo ""

    if [ $pass_count -gt 0 ]; then
        read -p "  将第一个可用模型设为默认? [y/N]: " set_def
        if echo "$set_def" | grep -qi '^y'; then
            "$PYTHON" << PYEOF
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
models = cfg.get('models', {}).get('$pname', {}).get('configured_models', [])
for m in models:
    if m.get('verified'):
        cfg.setdefault('agent', {})['model'] = f'$pname/{m["id"]}'
        cfg['agent']['thinking_level'] = m.get('thinking', 'off')
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
        tk = m.get('thinking', 'off')
        print(f'  ✅ 默认模型: $pname/{m["id"]} (thinking={tk})')
        break
PYEOF
        fi
    fi
}

# ══════════════════════════════════════════════
#  配置 AI 模型 — 选择提供商
# ══════════════════════════════════════════════
configure_model() {
    echo ""
    echo "  ═══ 配置 AI 模型 ═══"
    echo ""
    echo "  选择提供商:"
    echo "  ─────────────────────────────────────────────────"
    echo "  a) Anthropic  — Claude Sonnet 4 / Opus 4"
    echo "  b) OpenAI     — GPT-4o / GPT-4.1 / o3 / o4-mini"
    echo "  c) DeepSeek   — deepseek-chat / deepseek-reasoner"
    echo "  d) 通义千问   — qwen-max / qwen-plus / qwq-plus"
    echo "  e) 智谱 GLM   — glm-5 / glm-4.7 / glm-4.7-flash"
    echo "  f) MiniMax    — MiniMax-M2.5 / M2.1"
    echo "  g) 月之暗面   — kimi-k2.5"
    echo "  h) Google     — Gemini 3 Flash / 3.1 Pro"
    echo "  i) NVIDIA NIM — Qwen 3.5 / GLM / Kimi / Llama"
    echo ""
    read -p "  选择提供商 [a-i]: " provider_choice

    case $provider_choice in
        a) configure_provider "anthropic" "Anthropic" ;;
        b) configure_provider "openai" "OpenAI" ;;
        c) configure_provider "deepseek" "DeepSeek" ;;
        d) configure_provider "qwen" "通义千问" ;;
        e) configure_provider "zhipu" "智谱 GLM" ;;
        f) configure_provider "minimax" "MiniMax" ;;
        g) configure_provider "moonshot" "月之暗面" ;;
        h) configure_provider "google" "Google" ;;
        i) configure_provider "nvidia" "NVIDIA NIM" ;;
        *) echo "  ❌ 无效选择" ;;
    esac
}

# ══════════════════════════════════════════════
#  主循环
# ══════════════════════════════════════════════
while true; do
    eval "$(read_status)"
    show_menu
    read -p "  请输入选项 [0-6]: " choice

    case $choice in
        1)
            configure_model
            echo ""
            read -p "  按回车键继续..."
            ;;
        2)
            echo ""
            echo "  当前端口: ${PORT}"
            read -p "  请输入新端口号: " port
            if [ -n "$port" ]; then
                "$PYTHON" -c "
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
cfg.setdefault('gateway', {})['port'] = $port
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print('  ✅ Gateway 端口已设置为 $port')
print('  ⚠️  需要重启 Gateway 生效')
"
            fi
            echo ""
            read -p "  按回车键继续..."
            ;;
        3)
            echo ""
            echo "  当前认证模式: ${AUTH_MODE}"
            echo ""
            echo "  a) 无需认证 (none)"
            echo "  b) 密码认证 (password)"
            echo "  c) Token 认证 (token)"
            echo ""
            read -p "  选择模式 [a-c]: " authmode

            case $authmode in
                a)
                    "$PYTHON" -c "
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
cfg.setdefault('gateway', {}).setdefault('auth', {})['mode'] = 'none'
cfg['gateway']['auth']['password'] = None
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print('  ✅ 已关闭认证')
"
                    ;;
                b)
                    read -p "  请设置登录密码: " pw
                    "$PYTHON" -c "
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
auth = cfg.setdefault('gateway', {}).setdefault('auth', {})
auth['mode'] = 'password'
auth['password'] = '$pw'
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print('  ✅ 密码认证已启用')
"
                    ;;
                c)
                    read -p "  请设置 Token: " tk
                    "$PYTHON" -c "
import json, pathlib, os
p = pathlib.Path(os.path.expanduser('~/.whaleclaw/whaleclaw.json'))
cfg = json.loads(p.read_text())
auth = cfg.setdefault('gateway', {}).setdefault('auth', {})
auth['mode'] = 'token'
auth['token'] = '$tk'
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
print('  ✅ Token 认证已启用')
"
                    ;;
                *) echo "  ❌ 无效选择" ;;
            esac
            echo ""
            read -p "  按回车键继续..."
            ;;
        4)
            open -t "$CONFIG_FILE"
            echo "  📝 已用系统编辑器打开配置文件"
            echo ""
            read -p "  按回车键继续..."
            ;;
        5)
            echo ""
            "$PYTHON" -c "
import asyncio
from whaleclaw.doctor.runner import Doctor

async def main():
    d = Doctor()
    results = await d.run_all()
    print(d.format_report(results))

asyncio.run(main())
"
            echo ""
            read -p "  按回车键继续..."
            ;;
        6)
            echo ""
            echo "  完整配置内容:"
            echo "  ─────────────────────────────────"
            "$PYTHON" -m json.tool "$CONFIG_FILE" 2>/dev/null || cat "$CONFIG_FILE"
            echo ""
            read -p "  按回车键继续..."
            ;;
        0)
            echo "  👋 再见"
            exit 0
            ;;
        *)
            echo "  ❌ 无效选择"
            sleep 1
            ;;
    esac
done
