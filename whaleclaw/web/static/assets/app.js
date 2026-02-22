/* WhaleClaw WebChat SPA — Vue 3 Composition API */

const { createApp, ref, reactive, computed, watch, nextTick, onMounted } = Vue;

/* ── markdown-it + highlight.js setup ── */
const md = window.markdownit({
  html: true,
  breaks: true,
  linkify: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const html = hljs.highlight(str, { language: lang }).value;
        return `<pre class="hljs"><code>${html}</code><button class="copy-btn" onclick="copyCode(this)">复制</button></pre>`;
      } catch (_) { /* ignore */ }
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code><button class="copy-btn" onclick="copyCode(this)">复制</button></pre>`;
  },
});

/* Rewrite local file paths in markdown image tokens to /api/local-file?path= */
const _defaultImageRender = md.renderer.rules.image ||
  function (tokens, idx, options, env, self) { return self.renderToken(tokens, idx, options); };

md.renderer.rules.image = function (tokens, idx, options, env, self) {
  const token = tokens[idx];
  const srcIdx = token.attrIndex('src');
  if (srcIdx >= 0) {
    let src = token.attrs[srcIdx][1];
    if (src && /^(\/|~\/|\.\/|\.\.\/)/.test(src) && !src.startsWith('/api/')) {
      token.attrs[srcIdx][1] = `/api/local-file?path=${encodeURIComponent(src)}`;
    } else if (src && src.includes('/api/local-file?path=')) {
      /* LLM already included the proxy prefix — ensure path portion is encoded */
      const parts = src.split('path=');
      if (parts.length === 2 && !parts[1].includes('%')) {
        token.attrs[srcIdx][1] = `${parts[0]}path=${encodeURIComponent(decodeURIComponent(parts[1]))}`;
      }
    }
  }
  return _defaultImageRender(tokens, idx, options, env, self);
};

window.copyCode = function (btn) {
  const code = btn.previousElementSibling.textContent;
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = '已复制';
    setTimeout(() => (btn.textContent = '复制'), 1500);
  });
};

/* ── App ── */
createApp({
  setup() {
    const theme = ref(
      localStorage.getItem('wc-theme') ||
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    );
    watch(theme, (v) => {
      document.documentElement.setAttribute('data-theme', v);
      localStorage.setItem('wc-theme', v);
    }, { immediate: true });

    const token = ref(localStorage.getItem('wc-token') || '');
    const needLogin = ref(false);
    const loginPassword = ref('');
    const loginError = ref('');

    const sessions = ref([]);
    const activeSessionId = ref('');
    const messages = ref([]);
    const inputText = ref('');
    const isStreaming = ref(false);
    const showSettings = ref(false);
    const showSidebar = ref(false);
    const pendingImages = ref([]);

    const currentModel = ref('');
    const thinkingLevel = ref('off');
    const availableModels = ref([]);
    const defaultModel = ref('');

    const activeSession = computed(() =>
      sessions.value.find((s) => s.id === activeSessionId.value)
    );

    const _PROVIDER_LABELS = {
      anthropic: 'Anthropic', openai: 'OpenAI', deepseek: 'DeepSeek',
      qwen: '通义千问', zhipu: '智谱 GLM', minimax: 'MiniMax',
      moonshot: '月之暗面', google: 'Google', nvidia: 'NVIDIA NIM',
    };

    const groupedModels = computed(() => {
      const groups = {};
      for (const m of availableModels.value) {
        const p = m.provider || 'other';
        if (!groups[p]) groups[p] = [];
        groups[p].push(m);
      }
      return Object.entries(groups).map(([provider, models]) => ({
        provider,
        label: _PROVIDER_LABELS[provider] || provider,
        models,
      }));
    });

    let ws = null;
    let streamingMessage = null;

    /* ── API helpers ── */
    const apiBase = window.location.origin;

    async function apiFetch(path, opts = {}) {
      const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
      if (token.value) headers['Authorization'] = `Bearer ${token.value}`;
      const res = await fetch(`${apiBase}${path}`, { ...opts, headers });
      if (res.status === 401) {
        needLogin.value = true;
        throw new Error('auth');
      }
      return res.json();
    }

    /* ── Auth ── */
    async function checkAuth() {
      try {
        await apiFetch('/api/auth/verify');
        needLogin.value = false;
      } catch {
        /* needLogin already set by apiFetch */
      }
    }

    async function doLogin() {
      loginError.value = '';
      try {
        const res = await fetch(`${apiBase}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: loginPassword.value }),
        });
        const data = await res.json();
        if (data.token) {
          token.value = data.token;
          localStorage.setItem('wc-token', data.token);
          needLogin.value = false;
          await init();
        } else {
          loginError.value = data.error || '登录失败';
        }
      } catch (e) {
        loginError.value = '网络错误';
      }
    }

    /* ── Models ── */
    async function loadModels() {
      try {
        const data = await apiFetch('/api/models');
        availableModels.value = data.models || [];
        defaultModel.value = data.default || '';
        if (!currentModel.value && defaultModel.value) {
          currentModel.value = defaultModel.value;
        }
        if (data.thinking_level) {
          thinkingLevel.value = data.thinking_level;
        }
      } catch { /* ignore */ }
    }

    /* ── Sessions ── */
    async function loadSessions() {
      try {
        sessions.value = await apiFetch('/api/sessions');
      } catch { /* ignore auth redirect */ }
    }

    async function createSession() {
      const data = await apiFetch('/api/sessions', { method: 'POST' });
      await loadSessions();
      await switchSession(data.id);
    }

    async function deleteSession(id) {
      await apiFetch(`/api/sessions/${id}`, { method: 'DELETE' });
      if (activeSessionId.value === id) {
        activeSessionId.value = '';
        messages.value = [];
      }
      await loadSessions();
    }

    async function switchSession(id) {
      activeSessionId.value = id;
      try {
        const data = await apiFetch(`/api/sessions/${id}`);
        messages.value = (data.messages || []).map((m, i) => ({
          id: `hist-${i}`,
          role: m.role,
          content: m.content,
          rendered: renderMarkdown(m.content),
          toolCalls: [],
        }));
        currentModel.value = data.model || '';
        thinkingLevel.value = data.thinking_level || 'off';
      } catch { /* ignore */ }
      connectWS(id);
      await nextTick();
      scrollToBottom();
    }

    /* ── WebSocket ── */
    function connectWS(sessionId) {
      if (ws) { ws.close(); ws = null; }
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      let url = `${protocol}//${location.host}/ws`;
      if (token.value) url += `?token=${encodeURIComponent(token.value)}`;
      ws = new WebSocket(url);

      ws.onopen = () => {
        /* ping to keep alive */
        ws._ping = setInterval(() => {
          if (ws.readyState === 1) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 25000);
      };

      ws.onmessage = (evt) => {
        let msg;
        try { msg = JSON.parse(evt.data); } catch { return; }

        if (msg.type === 'stream') {
          if (!streamingMessage) {
            streamingMessage = {
              id: `msg-${Date.now()}`,
              role: 'assistant',
              content: '',
              rendered: '',
              toolCalls: [],
            };
            messages.value.push(streamingMessage);
          }
          streamingMessage.content += msg.payload.content || '';
          streamingMessage.rendered = renderMarkdown(streamingMessage.content);
          scrollToBottom();
        } else if (msg.type === 'message') {
          isStreaming.value = false;
          if (streamingMessage) {
            streamingMessage.content = msg.payload.content || streamingMessage.content;
            streamingMessage.rendered = renderMarkdown(streamingMessage.content);
            streamingMessage = null;
          } else {
            messages.value.push({
              id: `msg-${Date.now()}`,
              role: 'assistant',
              content: msg.payload.content,
              rendered: renderMarkdown(msg.payload.content),
              toolCalls: [],
            });
          }
          scrollToBottom();
        } else if (msg.type === 'tool_call') {
          if (!streamingMessage) {
            streamingMessage = {
              id: `msg-${Date.now()}`,
              role: 'assistant',
              content: '',
              rendered: '',
              toolCalls: [],
            };
            messages.value.push(streamingMessage);
            isStreaming.value = true;
          }
          const tc = {
            name: msg.payload.name,
            args: JSON.stringify(msg.payload.arguments, null, 2),
            result: null,
            loading: true,
            collapsed: false,
          };
          streamingMessage.toolCalls.push(tc);
          scrollToBottom();
        } else if (msg.type === 'tool_result') {
          if (streamingMessage) {
            const tc = streamingMessage.toolCalls.find(
              (t) => t.name === msg.payload.name && t.loading
            );
            if (tc) {
              tc.result = msg.payload.output;
              tc.loading = false;
              tc.collapsed = true;
            }
            scrollToBottom();
          }
        } else if (msg.type === 'error') {
          isStreaming.value = false;
          streamingMessage = null;
          messages.value.push({
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: `**Error:** ${msg.payload.error}`,
            rendered: renderMarkdown(`**Error:** ${msg.payload.error}`),
            toolCalls: [],
          });
          scrollToBottom();
        }
      };

      ws.onclose = () => {
        clearInterval(ws?._ping);
        /* auto-reconnect with backoff */
        setTimeout(() => {
          if (activeSessionId.value === sessionId) connectWS(sessionId);
        }, 2000);
      };
    }

    /* ── Send message ── */
    function sendMessage() {
      const text = inputText.value.trim();
      const imgs = pendingImages.value;
      if ((!text && !imgs.length) || !ws || ws.readyState !== 1) return;

      let displayHtml = renderMarkdown(text);
      if (imgs.length) {
        const imgHtml = imgs.map((img) => `<img src="${img.dataUrl}" style="max-width:200px;max-height:160px;border-radius:6px;margin:4px 2px">`).join('');
        displayHtml = imgHtml + (displayHtml ? '<br>' + displayHtml : '');
      }

      messages.value.push({
        id: `user-${Date.now()}`,
        role: 'user',
        content: text,
        rendered: displayHtml,
        toolCalls: [],
      });

      const payload = { content: text || '(用户发送了图片)' };
      if (imgs.length) {
        payload.images = imgs.map((img) => ({
          data: img.dataUrl.split(',')[1],
          mime: img.mime,
          name: img.name,
        }));
      }

      ws.send(JSON.stringify({
        type: 'message',
        session_id: activeSessionId.value,
        payload,
      }));

      inputText.value = '';
      pendingImages.value = [];
      isStreaming.value = true;
      streamingMessage = null;
      nextTick(scrollToBottom);
    }

    function handleKeydown(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    }

    /* ── Image handling ── */
    function addImageFiles(files) {
      for (const file of files) {
        if (!file.type.startsWith('image/')) continue;
        if (pendingImages.value.length >= 4) break;
        const reader = new FileReader();
        reader.onload = (e) => {
          pendingImages.value.push({
            dataUrl: e.target.result,
            mime: file.type,
            name: file.name || 'image.png',
          });
        };
        reader.readAsDataURL(file);
      }
    }

    function removeImage(idx) {
      pendingImages.value.splice(idx, 1);
    }

    function onPaste(e) {
      const items = e.clipboardData?.items;
      if (!items) return;
      const imageFiles = [];
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          const f = item.getAsFile();
          if (f) imageFiles.push(f);
        }
      }
      if (imageFiles.length) {
        e.preventDefault();
        addImageFiles(imageFiles);
      }
    }

    function onDrop(e) {
      e.preventDefault();
      if (e.dataTransfer?.files) addImageFiles(e.dataTransfer.files);
    }

    function onDragOver(e) { e.preventDefault(); }

    function triggerFileInput() {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.multiple = true;
      input.onchange = (e) => { if (e.target.files) addImageFiles(e.target.files); };
      input.click();
    }

    /* ── Settings ── */
    async function switchModel(model) {
      if (model === currentModel.value) return;
      currentModel.value = model;
      const modelInfo = availableModels.value.find((m) => m.id === model);
      if (modelInfo && modelInfo.thinking) {
        thinkingLevel.value = modelInfo.thinking;
      }
      if (ws && ws.readyState === 1) {
        ws.send(JSON.stringify({
          type: 'message',
          session_id: activeSessionId.value,
          payload: { content: `/model ${model}` },
        }));
        if (modelInfo && modelInfo.thinking && modelInfo.thinking !== 'off') {
          ws.send(JSON.stringify({
            type: 'message',
            session_id: activeSessionId.value,
            payload: { content: `/thinking ${modelInfo.thinking}` },
          }));
        }
      }
    }

    /* ── Utils ── */
    const _FILE_ICONS = {
      pptx: '📊', ppt: '📊',
      xlsx: '📗', xls: '📗', csv: '📗',
      docx: '📝', doc: '📝',
      pdf: '📕',
      zip: '📦', rar: '📦', '7z': '📦', tar: '📦', gz: '📦',
      mp3: '🎵', wav: '🎵', flac: '🎵',
      mp4: '🎬', mov: '🎬', avi: '🎬',
      py: '🐍', js: '📜', ts: '📜', json: '📜',
      txt: '📄', md: '📄', log: '📄',
    };
    const _IMAGE_EXTS = new Set(['jpg','jpeg','png','gif','webp','bmp','svg','ico']);

    function _fileCard(filePath) {
      const name = filePath.split('/').pop();
      const ext = (name.split('.').pop() || '').toLowerCase();
      const icon = _FILE_ICONS[ext] || '📎';
      const encPath = encodeURIComponent(filePath);
      const downloadUrl = `/api/local-file?path=${encPath}&download=true`;
      const openUrl = `/api/local-file?path=${encPath}`;
      return `<div class="file-card" onclick="window.open('${openUrl}','_blank')">` +
        `<div class="file-card-icon">${icon}</div>` +
        `<div class="file-card-info">` +
          `<div class="file-card-name">${name}</div>` +
          `<div class="file-card-meta" data-path="${encPath}">加载中...</div>` +
        `</div>` +
        `<a class="file-card-dl" href="${downloadUrl}" onclick="event.stopPropagation()" title="下载">⬇</a>` +
      `</div>`;
    }

    let _metaTimer = null;
    function _loadFileCardMeta() {
      clearTimeout(_metaTimer);
      _metaTimer = setTimeout(() => {
        document.querySelectorAll('.file-card-meta[data-path]').forEach(async (el) => {
          const p = el.dataset.path;
          if (!p || el.dataset.loaded) return;
          el.dataset.loaded = '1';
          try {
            const resp = await fetch(`/api/file-info?path=${p}`);
            if (resp.ok) {
              const info = await resp.json();
              el.textContent = `${info.ext.toUpperCase()} 文件 · ${info.size_human}`;
            } else {
              el.textContent = '文件不可用';
            }
          } catch { el.textContent = ''; }
        });
      }, 300);
    }

    function renderMarkdown(text) {
      if (!text) return '';
      let html = md.render(text);

      /* Rewrite <img src="/local/path"> to use /api/local-file proxy */
      html = html.replace(
        /(<img\s[^>]*src=["'])(\/(tmp|home|Users|var|opt|etc)[^"']+)(["'][^>]*>)/gi,
        (m, pre, src, _d, post) => {
          if (m.includes('/api/local-file')) return m;
          return `${pre}/api/local-file?path=${encodeURIComponent(src)}${post}`;
        }
      );

      /* Convert file paths to file cards (non-image files only) */
      html = html.replace(
        /(\/(?:tmp|home|Users|var|opt|etc)\/[^\s<"']*\.(\w{2,5}))(?=[\s<"']|$)/gi,
        (m, filePath, ext) => {
          if (_IMAGE_EXTS.has(ext.toLowerCase())) return m;
          if (m.includes('file-card')) return m;
          return _fileCard(filePath);
        }
      );

      nextTick(_loadFileCardMeta);
      return html;
    }

    const messagesEl = ref(null);
    function scrollToBottom() {
      nextTick(() => {
        if (messagesEl.value) {
          messagesEl.value.scrollTop = messagesEl.value.scrollHeight;
        }
      });
    }

    function toggleTheme() {
      theme.value = theme.value === 'dark' ? 'light' : 'dark';
    }

    function formatTime(iso) {
      if (!iso) return '';
      const d = new Date(iso);
      return d.toLocaleDateString();
    }

    /* ── Init ── */
    async function init() {
      await loadModels();
      await loadSessions();
      if (sessions.value.length > 0) {
        await switchSession(sessions.value[0].id);
      } else {
        await createSession();
      }
    }

    onMounted(async () => {
      try {
        const status = await fetch(`${apiBase}/api/status`).then((r) => r.json());
        if (status.status === 'ok') {
          await checkAuth();
          if (!needLogin.value) await init();
        }
      } catch {
        needLogin.value = false;
        await init();
      }
    });

    return {
      theme, token, needLogin, loginPassword, loginError, doLogin,
      sessions, activeSessionId, activeSession, messages,
      inputText, isStreaming, showSettings, showSidebar, pendingImages,
      currentModel, thinkingLevel, availableModels, defaultModel, groupedModels, messagesEl,
      createSession, deleteSession, switchSession,
      sendMessage, handleKeydown, switchModel, loadModels,
      toggleTheme, formatTime, renderMarkdown,
      addImageFiles, removeImage, onPaste, onDrop, onDragOver, triggerFileInput,
    };
  },

  template: `
    <!-- Login Overlay -->
    <div v-if="needLogin" class="login-overlay">
      <div class="login-card">
        <h2>WhaleClaw</h2>
        <p v-if="loginError" class="login-error">{{ loginError }}</p>
        <input
          v-model="loginPassword"
          type="password"
          placeholder="输入密码"
          @keydown.enter="doLogin"
        />
        <button class="btn-send" @click="doLogin">登录</button>
      </div>
    </div>

    <!-- Main App -->
    <template v-else>
      <!-- Sidebar -->
      <aside class="sidebar" :class="{ open: showSidebar }">
        <div class="sidebar-header">
          <h1>WhaleClaw</h1>
          <div class="sidebar-actions">
            <button class="btn-icon" @click="createSession" title="新建会话">+</button>
            <button class="btn-icon" @click="toggleTheme" title="切换主题">
              {{ theme === 'dark' ? '☀' : '🌙' }}
            </button>
            <button class="btn-icon" @click="showSettings = !showSettings" title="设置">⚙</button>
          </div>
        </div>
        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.id"
            class="session-item"
            :class="{ active: s.id === activeSessionId }"
            @click="switchSession(s.id); showSidebar = false"
          >
            <div class="session-info">
              <div class="session-title">{{ s.model || '会话' }}</div>
              <div class="session-meta">{{ formatTime(s.created_at) }} · {{ s.message_count || 0 }} 条</div>
            </div>
            <button class="session-delete" @click.stop="deleteSession(s.id)">✕</button>
          </div>
        </div>
      </aside>

      <!-- Main Area -->
      <div class="main">
        <div class="chat-header">
          <div style="display:flex;align-items:center;gap:8px">
            <button class="btn-icon mobile-menu" @click="showSidebar = !showSidebar">☰</button>
            <select
              class="model-selector"
              :value="currentModel"
              @change="switchModel($event.target.value)"
            >
              <template v-if="groupedModels.length">
                <optgroup v-for="g in groupedModels" :key="g.provider" :label="g.label">
                  <option
                    v-for="m in g.models"
                    :key="m.id"
                    :value="m.id"
                  >{{ m.name }}{{ m.thinking && m.thinking !== 'off' ? ' 💭' : '' }}{{ m.tools ? '' : ' ⚠无工具' }}</option>
                </optgroup>
              </template>
              <template v-else>
                <option :value="currentModel">{{ currentModel || '未配置模型' }}</option>
              </template>
            </select>
            <span v-if="thinkingLevel !== 'off'" class="thinking-badge">💭 {{ thinkingLevel }}</span>
          </div>
          <span class="chat-header-info" v-if="activeSession">
            {{ activeSession.message_count || messages.length }} 条消息
          </span>
        </div>

        <div class="messages" ref="messagesEl">
          <div
            v-for="msg in messages"
            :key="msg.id"
            class="message-row"
            :class="msg.role"
          >
            <div class="bubble" :class="msg.role">
              <div v-if="msg.rendered" v-html="msg.rendered"></div>
              <div v-if="msg.toolCalls && msg.toolCalls.length" class="tool-calls">
                <div v-for="(tc, ti) in msg.toolCalls" :key="ti" class="tool-card" :class="{ loading: tc.loading }">
                  <div class="tool-card-header" @click="tc.collapsed = !tc.collapsed">
                    <span class="tool-card-icon">{{ tc.loading ? '⏳' : '✅' }}</span>
                    <span class="tool-card-name">{{ tc.name }}</span>
                    <span class="tool-card-status">{{ tc.loading ? '执行中...' : '完成' }}</span>
                    <span class="tool-card-toggle">{{ tc.collapsed ? '▸' : '▾' }}</span>
                  </div>
                  <div v-if="!tc.collapsed" class="tool-card-body">
                    <pre class="tool-card-args">{{ tc.args }}</pre>
                    <pre v-if="tc.result" class="tool-card-result">{{ tc.result.length > 500 ? tc.result.slice(0, 500) + '...' : tc.result }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="isStreaming && !messages.length" class="message-row assistant">
            <div class="bubble assistant">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </div>
          </div>
        </div>

        <div class="input-area" @drop="onDrop" @dragover="onDragOver">
          <div v-if="pendingImages.length" class="image-preview-strip">
            <div v-for="(img, idx) in pendingImages" :key="idx" class="image-preview-item">
              <img :src="img.dataUrl" />
              <button class="image-remove-btn" @click="removeImage(idx)">✕</button>
            </div>
          </div>
          <div class="input-wrapper">
            <button class="btn-attach" @click="triggerFileInput" title="添加图片">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            </button>
            <textarea
              v-model="inputText"
              placeholder="输入消息... (Enter 发送, Shift+Enter 换行, 可粘贴/拖拽图片)"
              @keydown="handleKeydown"
              @paste="onPaste"
              rows="1"
            ></textarea>
            <button class="btn-send" :disabled="isStreaming || (!inputText.trim() && !pendingImages.length)" @click="sendMessage">
              发送
            </button>
          </div>
        </div>
      </div>

      <!-- Settings Panel -->
      <div class="settings-panel" :class="{ open: showSettings }">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
          <h3>设置</h3>
          <button class="btn-icon" @click="showSettings = false">✕</button>
        </div>
        <div class="setting-group">
          <label>当前模型</label>
          <select :value="currentModel" @change="switchModel($event.target.value)">
            <template v-if="groupedModels.length">
              <optgroup v-for="g in groupedModels" :key="g.provider" :label="g.label">
                <option v-for="m in g.models" :key="m.id" :value="m.id">
                  {{ m.name }}{{ m.tools ? '' : ' ⚠无工具' }}
                </option>
              </optgroup>
            </template>
            <template v-else>
              <option :value="currentModel">{{ currentModel || '未配置' }}</option>
            </template>
          </select>
          <p style="font-size:12px;color:var(--text-secondary);margin-top:4px">
            在「修改配置.command」中添加更多 API Key 后刷新页面
          </p>
        </div>
        <div class="setting-group">
          <label>主题</label>
          <select :value="theme" @change="theme = $event.target.value">
            <option value="light">亮色</option>
            <option value="dark">暗色</option>
          </select>
        </div>
      </div>
    </template>
  `,
}).mount('#app');
