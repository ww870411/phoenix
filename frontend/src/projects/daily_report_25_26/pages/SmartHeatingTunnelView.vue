<template>
  <div class="smart-heating-tunnel-view" :class="{ 'fullscreen-mode': isFullscreen }">
    <!-- 常规模式下展示全局顶部导航 -->
    <AppHeader v-if="!isFullscreen" />

    <!-- 全屏模式顶部极简浮动工具条 -->
    <header v-if="isFullscreen" class="fullscreen-topbar">
      <div class="topbar-left">
        <button class="topbar-btn back-btn" type="button" @click="handleExitFullscreen" title="返回常规页面">
          ← 返回常规页面
        </button>
        <span class="topbar-divider"></span>
        <div class="topbar-brand">
          <span class="portal-mini-icon">🌐</span>
          <span class="topbar-title">智慧供热调度平台</span>
        </div>
      </div>

      <div class="topbar-right">
        <!-- 实时在线状态胶囊 -->
        <div class="status-capsule" :class="{ online: isRelayOnline, offline: !isRelayOnline }">
          <span class="dot"></span>
          <span class="status-label">{{ isRelayOnline ? '中继在线' : '中继未连接' }}</span>
          <span v-if="isRelayOnline && tunnelStatus.client_ip" class="status-extra">
            {{ tunnelStatus.client_ip }}
          </span>
          <span v-if="tunnelStatus.last_heartbeat" class="status-time">
            {{ formattedHeartbeat }}
          </span>
        </div>

        <button
          class="topbar-btn"
          type="button"
          :disabled="refreshing"
          @click="handleReloadFrame"
          title="重新加载内网视窗"
        >
          {{ refreshing ? '刷新中…' : '⟳ 刷新' }}
        </button>
        <button
          class="topbar-btn"
          type="button"
          @click="openConfigModal"
          title="配置内网账号与中继密钥"
        >
          ⚙️ 平台设置
        </button>
        <button
          class="topbar-btn accent"
          type="button"
          :disabled="downloading"
          @click="handleDownloadClient"
          title="下载 Win7 客户端脚本"
        >
          📥 客户端
        </button>
      </div>
    </header>

    <!-- 主工作区 -->
    <main class="tunnel-main" :class="{ 'fullscreen-main': isFullscreen }">
      <!-- 常规模式展示面包屑 -->
      <Breadcrumbs v-if="!isFullscreen" :items="breadcrumbItems" class="compact-breadcrumbs" />

      <!-- 非 Global_admin 拦截卡片 -->
      <section v-if="!isAllowed" class="forbidden-card">
        <div class="forbidden-icon">🚫</div>
        <h3 class="forbidden-title">访问权限受限 · 仅限 Global_admin</h3>
        <p class="forbidden-desc">
          智慧供热内网直通通道直连核心调度生产内网系统，严格仅限<strong>超级管理员本人 (Global_admin)</strong> 访问与操作。
        </p>
        <div class="forbidden-actions">
          <button class="btn secondary" type="button" @click="$router.push(`/projects/${projectKey}/pages/select`)">
            ⬅️ 返回生产监控大厅
          </button>
        </div>
      </section>

      <!-- 系统管理员操作视窗 -->
      <template v-else>
        <!-- 常规模式下的紧凑现代控制栏 -->
        <section v-if="!isFullscreen" class="control-toolbar">
          <div class="toolbar-left">
            <div class="portal-badge-icon">🌐</div>
            <h2 class="portal-title">智慧供热平台内网直通</h2>
          </div>

          <div class="toolbar-right">
            <!-- 实时连接状态胶囊 -->
            <div class="status-capsule" :class="{ online: isRelayOnline, offline: !isRelayOnline }">
              <span class="dot"></span>
              <span class="status-label">{{ isRelayOnline ? '中继在线' : '中继未连接' }}</span>
              <span v-if="isRelayOnline && tunnelStatus.client_ip" class="status-extra">
                IP: {{ tunnelStatus.client_ip }}
              </span>
              <span v-if="tunnelStatus.last_heartbeat" class="status-time">
                {{ formattedHeartbeat }}
              </span>
            </div>

            <!-- 操作按钮组 -->
            <div class="toolbar-actions">
              <button
                class="btn primary btn-sm btn-download"
                type="button"
                :disabled="downloading"
                title="下载专为 Win7 + Python 3.8 定制的免安装单文件客户端脚本"
                @click="handleDownloadClient"
              >
                {{ downloading ? '下载中…' : '📥 下载客户端' }}
              </button>

              <button
                class="btn secondary btn-sm"
                type="button"
                title="配置内网平台登录账号密码及中继密钥"
                @click="openConfigModal"
              >
                ⚙️ 平台设置
              </button>

              <button
                class="btn secondary btn-sm"
                type="button"
                title="以独立全屏工作台新窗口打开内网平台"
                @click="openInNewTab"
              >
                ↗ 新窗口打开
              </button>

              <button
                class="btn secondary btn-sm"
                type="button"
                :disabled="refreshing"
                title="刷新直通内网视窗"
                @click="handleReloadFrame"
              >
                {{ refreshing ? '刷新中…' : '⟳ 刷新' }}
              </button>
            </div>
          </div>
        </section>

        <p v-if="statusError" class="connection-message" role="alert">
          {{ statusError }}
          <button class="btn secondary btn-sm" @click="fetchStatusAndConfig(true)">重试连接</button>
        </p>
        <!-- 主视窗容器：充满剩余高度，无双滚动条 -->
        <section class="viewport-card" :class="{ 'fullscreen-viewport': isFullscreen }">
          <div v-if="initializing" class="offline-guide-panel">正在读取中继状态与平台入口…</div>
          <!-- 场景 1：中继离线引导与状态诊断向导 -->
          <div v-else-if="!isRelayOnline" class="offline-guide-panel">
            <div class="guide-header">
              <div class="guide-hero-icon">🔌</div>
              <h3 class="guide-title">智慧供热内网未连接</h3>
              <p class="guide-desc">
                当前未检测到办公电脑中继客户端连接，启动后将自动加载内网平台。
              </p>
            </div>

            <!-- 拓扑示意图 -->
            <div class="topology-strip">
              <div class="topo-node active">
                <span class="topo-icon">☁️</span>
                <span class="topo-name">Phoenix 外网平台</span>
                <span class="topo-status">就绪</span>
              </div>
              <div class="topo-line offline">
                <span class="topo-arrow">◄── 长轮询隧道 ──►</span>
              </div>
              <div class="topo-node offline">
                <span class="topo-icon">💻</span>
                <span class="topo-name">办公电脑中继</span>
                <span class="topo-status">等待启动</span>
              </div>
              <div class="topo-line">
                <span class="topo-arrow">── 局域网 ──►</span>
              </div>
              <div class="topo-node ready">
                <span class="topo-icon">🏢</span>
                <span class="topo-name">内网智慧供热平台</span>
                <span class="topo-status">内网服务</span>
              </div>
            </div>

            <!-- 简明快速上手步骤 -->
            <div class="steps-grid">
              <div class="step-card">
                <div class="step-badge">1</div>
                <div class="step-body">
                  <h4>下载客户端</h4>
                  <p>点击下方按钮下载免安装中继脚本（适用于 Win7 + Python 3.8）。</p>
                </div>
              </div>

              <div class="step-card">
                <div class="step-badge">2</div>
                <div class="step-body">
                  <h4>办公电脑运行</h4>
                  <p>在可访问内网的办公电脑运行：<code>python smart_heating_tunnel_win7.py</code></p>
                </div>
              </div>

              <div class="step-card">
                <div class="step-badge">3</div>
                <div class="step-body">
                  <h4>自动加载平台</h4>
                  <p>连接建立后本页面将自动点亮在线状态并加载内网控制台。</p>
                </div>
              </div>
            </div>

            <div class="guide-actions">
              <button class="btn primary btn-lg" :disabled="downloading" @click="handleDownloadClient">
                {{ downloading ? '正在打包下载…' : '📥 立即下载中继客户端' }}
              </button>
              <button class="btn secondary btn-lg" @click="fetchStatusAndConfig">
                🔄 刷新连接状态
              </button>
              <button class="btn outline btn-lg" @click="openConfigModal">
                ⚙️ 平台设置
              </button>
            </div>
          </div>

          <!-- 场景 2：中继在线时，高清晰满屏无缝嵌入内网 iframe -->
          <div v-else class="iframe-container">
            <div v-if="refreshing" class="frame-loading" role="status">页面加载中…</div>
            <iframe
              ref="portalIframe"
              :src="gatewayUrl"
              class="portal-frame"
              frameborder="0"
              allowfullscreen
              @load="onIframeLoad"
            ></iframe>
          </div>
        </section>

        <!-- 账号与持久化配置弹窗 Modal -->
        <div v-if="showConfigModal" class="modal-backdrop" @click.self="showConfigModal = false">
          <div class="modal-card">
            <div class="modal-header">
              <div class="modal-title-wrap">
                <span class="modal-icon">⚙️</span>
                <h3>平台账号与反向中继持久化配置</h3>
              </div>
              <button class="modal-close" type="button" @click="showConfigModal = false">×</button>
            </div>

            <div class="modal-body">
              <p class="modal-hint">
                配置保存在 Phoenix 数据卷中。修改目标地址或密钥后，请重新下载并替换办公电脑脚本；已有本地 JSON 配置优先。内网登录仍由平台登录页完成。
              </p>

              <div class="form-group">
                <label>内网目标平台地址 (Base URL)</label>
                <input
                  v-model.trim="editConfig.target_base_url"
                  type="text"
                  placeholder="http://192.168.1.206:6688"
                  class="form-control"
                />
              </div>

              <div class="form-row">
                <div class="form-group col-half">
                  <label>平台入口路径 (Portal Path)</label>
                  <input
                    v-model.trim="editConfig.portal_path"
                    type="text"
                    placeholder="/vindex/"
                    class="form-control"
                  />
                </div>
                <div class="form-group col-half">
                  <label>中继安全通信密钥 (Secret)</label>
                  <input
                    v-model.trim="editConfig.tunnel_secret"
                    type="text"
                    placeholder="phoenix_tunnel_secret_2026"
                    class="form-control"
                  />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group col-half">
                  <label>内网平台登录用户名</label>
                  <input
                    v-model.trim="editConfig.auth_username"
                    type="text"
                    placeholder="请输入内网平台账号"
                    class="form-control"
                  />
                </div>
                <div class="form-group col-half">
                  <label>内网平台登录密码</label>
                  <input
                    v-model="editConfig.auth_password"
                    type="password"
                    placeholder="若不修改密码请留空"
                    class="form-control"
                  />
                </div>
              </div>

              <div class="form-group checkbox-group">
                <label class="checkbox-label">
                  <input v-model="editConfig.auto_login_enabled" type="checkbox" disabled />
                  <span>自动代登暂未实现，请在内网页面登录</span>
                </label>
              </div>

              <!-- 原生网关直链调试入口 -->
              <div class="form-group gateway-debug-box">
                <div class="gateway-debug-label">原生直通网关地址 (带身份令牌)：</div>
                <div class="gateway-debug-url">
                  <code>{{ gatewayUrl }}</code>
                </div>
                <button class="btn text-btn btn-sm" type="button" @click="openRawGatewayInTab">
                  ↗ 在独立标签直接打开此原生网关链接
                </button>
              </div>
            </div>

            <div class="modal-footer">
              <button class="btn secondary btn-sm" type="button" @click="showConfigModal = false">取消</button>
              <button class="btn primary btn-sm" type="button" :disabled="savingConfig" @click="handleSaveConfig">
                {{ savingConfig ? '正在保存…' : '💾 保存持久化配置' }}
              </button>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { useAuthStore } from '../store/auth'
import {
  downloadTunnelClientScript,
  fetchTunnelConfig,
  fetchTunnelStatus,
  getTunnelGatewayUrl,
  updateTunnelConfig,
} from '../services/api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// 路由与模式判断
const projectKey = computed(() => route.params.projectKey || 'daily_report_25_26')
const isFullscreen = computed(() => route.query.fullscreen === 'true')

// 严格仅限 Global_admin (超级管理员本人 ww870411) 访问
const isAllowed = computed(() => {
  return (
    auth.isGlobalAdmin ||
    auth.user?.group === 'Global_admin' ||
    auth.user?.username === 'ww870411'
  )
})

const breadcrumbItems = computed(() => [
  { label: '首页', to: `/projects/${projectKey.value}` },
  { label: '生产监控与看板', to: `/projects/${projectKey.value}/pages/select` },
  { label: '智慧供热内网直通' },
])

// 状态与数据
const isRelayOnline = ref(false)
const tunnelStatus = ref({
  online: false,
  last_heartbeat: '',
  client_ip: '',
  active_workers: 0,
})

const tunnelConfig = ref({
  target_base_url: 'http://192.168.1.206:6688',
  portal_path: '/vindex/',
  auth_username: '',
  has_password: false,
})

const editConfig = ref({
  target_base_url: '',
  portal_path: '/vindex/',
  login_path: '/vindex/login',
  auth_username: '',
  auth_password: '',
  tunnel_secret: '',
  auto_login_enabled: true,
})

const portalIframe = ref(null)
const downloading = ref(false)
const refreshing = ref(false)
const showConfigModal = ref(false)
const savingConfig = ref(false)
const initializing = ref(true)
const statusError = ref('')
let pollTimer = null
let disposed = false

// 计算网关 URL (自动附加管理员的会话 token，支持新窗口与跨域嵌入)
const gatewayUrl = computed(() => {
  const pPath = (tunnelConfig.value.portal_path || 'vindex/').replace(/^\/+/, '')
  const base = getTunnelGatewayUrl(projectKey.value, pPath)
  const token = auth.token || ''
  return token ? `${base}?phoenix_token=${encodeURIComponent(token)}` : base
})

// 心跳时间友好展示
const formattedHeartbeat = computed(() => {
  if (!tunnelStatus.value.last_heartbeat) return ''
  return `更新于 ${tunnelStatus.value.last_heartbeat.slice(11, 19)}`
})

// 获取中继状态与持久化配置
async function fetchStatusAndConfig(refreshConfig = true) {
  if (!isAllowed.value) return
  try {
    const [statusData, cfgData] = await Promise.all([
      fetchTunnelStatus(projectKey.value),
      refreshConfig ? fetchTunnelConfig(projectKey.value) : Promise.resolve(null),
    ])
    if (disposed) return
    if (cfgData) tunnelConfig.value = cfgData
    tunnelStatus.value = statusData
    if (!isRelayOnline.value && statusData.online) refreshing.value = true
    isRelayOnline.value = Boolean(statusData.online)
    statusError.value = ''
  } catch (err) {
    statusError.value = `中继状态读取失败：${err.message}`
  } finally {
    initializing.value = false
  }
}

// 上一轮完成后再安排下一轮，慢请求不会叠加；定期只读状态。
async function pollStatus() {
  await fetchStatusAndConfig(false)
  if (!disposed) pollTimer = setTimeout(pollStatus, 8000)
}

// 打开配置弹窗
function openConfigModal() {
  editConfig.value = {
    target_base_url: tunnelConfig.value.target_base_url || 'http://192.168.1.206:6688',
    portal_path: tunnelConfig.value.portal_path || '/vindex/',
    login_path: tunnelConfig.value.login_path || '/vindex/login',
    auth_username: tunnelConfig.value.auth_username || '',
    auth_password: '', // 留空表示不修改
    tunnel_secret: tunnelConfig.value.tunnel_secret || 'phoenix_tunnel_secret_2026',
    auto_login_enabled: tunnelConfig.value.auto_login_enabled ?? true,
  }
  showConfigModal.value = true
}

// 保存持久化配置
async function handleSaveConfig() {
  savingConfig.value = true
  try {
    await updateTunnelConfig(editConfig.value, projectKey.value)
    showConfigModal.value = false
    await fetchStatusAndConfig()
    alert('配置已保存。修改地址或密钥后，请更新办公电脑脚本及其本地 JSON 配置并重启中继。')
  } catch (err) {
    alert(`保存配置失败: ${err.message || err}`)
  } finally {
    savingConfig.value = false
  }
}

// 下载客户端脚本
async function handleDownloadClient() {
  downloading.value = true
  try {
    await downloadTunnelClientScript(projectKey.value)
  } catch (err) {
    alert(`下载中继客户端失败: ${err.message || err}`)
  } finally {
    downloading.value = false
  }
}

// 刷新 iframe 视窗
function handleReloadFrame() {
  refreshing.value = true
  fetchStatusAndConfig(false)
  if (portalIframe.value) {
    const glue = gatewayUrl.value.includes('?') ? '&' : '?'
    portalIframe.value.src = `${gatewayUrl.value}${glue}_t=${Date.now()}`
  } else {
    refreshing.value = false
  }
}

// 退出全屏工作台
function handleExitFullscreen() {
  if (window.opener && window.history.length <= 1) {
    window.close()
  } else {
    router.replace({ path: route.path, query: {} })
  }
}

// 在独立全屏新窗口打开
function openInNewTab() {
  const url = `${window.location.origin}/projects/${projectKey.value}/pages/smart_heating_tunnel?fullscreen=true`
  window.open(url, '_blank')
}

// 直接在独立标签打开原生后端直通网关
function openRawGatewayInTab() {
  window.open(gatewayUrl.value, '_blank')
}

function onIframeLoad() {
  refreshing.value = false
}

onMounted(async () => {
  await fetchStatusAndConfig(true)
  if (!disposed) pollTimer = setTimeout(pollStatus, 8000)
})

onBeforeUnmount(() => {
  disposed = true
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.connection-message { margin: 0 16px 8px; color: #fbbf24; }
.frame-loading { position: absolute; top: 8px; left: 50%; transform: translateX(-50%); z-index: 2; padding: 8px 16px; background: #1e293b; color: #fff; border-radius: 6px; }
/* 全局页面容器：锁定视口高度，杜绝双滚动条 */
.smart-heating-tunnel-view {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #090e17;
  color: #f1f5f9;
}

.smart-heating-tunnel-view.fullscreen-mode {
  background: #000000;
}

/* 全屏模式下的微型浮动顶部导航条 (38px) */
.fullscreen-topbar {
  height: 38px;
  background: #111827;
  border-bottom: 1px solid #1f2937;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  user-select: none;
  z-index: 50;
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-btn {
  background: #1f2937;
  border: 1px solid #374151;
  color: #cbd5e1;
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
}

.topbar-btn:hover:not(:disabled) {
  background: #374151;
  color: #ffffff;
}

.topbar-btn.back-btn {
  background: #0284c7;
  border-color: #0284c7;
  color: #ffffff;
}

.topbar-btn.back-btn:hover {
  background: #0369a1;
}

.topbar-btn.accent {
  background: #059669;
  border-color: #059669;
  color: #ffffff;
}

.topbar-btn.accent:hover:not(:disabled) {
  background: #047857;
}

.topbar-divider {
  width: 1px;
  height: 16px;
  background: #374151;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.portal-mini-icon {
  font-size: 1rem;
}

.topbar-title {
  font-size: 0.86rem;
  font-weight: 600;
  color: #f3f4f6;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 主工作区布局：充满垂直空间 */
.tunnel-main {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0.5rem 1.25rem 0.75rem;
  gap: 0.5rem;
  overflow: hidden;
}

.tunnel-main.fullscreen-main {
  padding: 0;
  gap: 0;
}

.compact-breadcrumbs {
  margin-bottom: 0;
  font-size: 0.82rem;
  flex-shrink: 0;
}

/* 常规模式现代工具栏 (52px) */
.control-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 52px;
  padding: 0 1rem;
  background: #111827;
  border: 1px solid #1f2937;
  border-radius: 8px;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.portal-badge-icon {
  font-size: 1.5rem;
  width: 36px;
  height: 36px;
  background: rgba(14, 165, 233, 0.15);
  border: 1px solid rgba(14, 165, 233, 0.3);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.portal-title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #f8fafc;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 状态胶囊 */
.status-capsule {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  user-select: none;
}

.status-capsule.online {
  background: rgba(34, 197, 94, 0.12);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.status-capsule.offline {
  background: rgba(239, 68, 68, 0.12);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.status-capsule .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-capsule.online .dot {
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}

.status-capsule.offline .dot {
  background: #ef4444;
}

.status-extra {
  color: #cbd5e1;
  font-size: 0.74rem;
  font-weight: normal;
}

.status-time {
  color: #64748b;
  font-size: 0.72rem;
  font-weight: normal;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 主视窗卡片 */
.viewport-card {
  flex: 1;
  min-height: 0;
  height: 100%;
  background: #0f172a;
  border: 1px solid #1f2937;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

.viewport-card.fullscreen-viewport {
  border-radius: 0;
  border: none;
}

/* iframe 容器：绝对充满、零滚动条 */
.iframe-container {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.portal-frame {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
  background: #ffffff;
}

/* 中继离线诊断与连接引导面板 */
.offline-guide-panel {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  text-align: center;
}

.guide-header {
  margin-bottom: 1.5rem;
}

.guide-hero-icon {
  font-size: 3.5rem;
  margin-bottom: 0.5rem;
}

.guide-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: #f8fafc;
  margin: 0 0 0.4rem;
}

.guide-desc {
  font-size: 0.88rem;
  color: #94a3b8;
  max-width: 640px;
  line-height: 1.5;
  margin: 0 auto;
}

/* 网络拓扑条 */
.topology-strip {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0b1120;
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 0.85rem 1.5rem;
  margin-bottom: 1.75rem;
  max-width: 820px;
  width: 100%;
}

.topo-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 6px 12px;
  border-radius: 6px;
  background: #1e293b;
  min-width: 130px;
}

.topo-node.active {
  border: 1px solid rgba(34, 197, 94, 0.4);
}

.topo-node.offline {
  border: 1px solid rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.08);
}

.topo-node.ready {
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.topo-icon {
  font-size: 1.4rem;
}

.topo-name {
  font-size: 0.78rem;
  font-weight: 600;
  color: #f1f5f9;
}

.topo-status {
  font-size: 0.7rem;
  color: #94a3b8;
}

.topo-node.offline .topo-status {
  color: #f87171;
  font-weight: 600;
}

.topo-line {
  flex: 1;
  text-align: center;
  padding: 0 8px;
}

.topo-arrow {
  font-size: 0.72rem;
  color: #64748b;
  font-family: ui-monospace, monospace;
}

.topo-line.offline .topo-arrow {
  color: #ef4444;
}

/* 三步指引网格 */
.steps-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  max-width: 840px;
  width: 100%;
  margin-bottom: 2rem;
}

.step-card {
  background: #111827;
  border: 1px solid #1f2937;
  border-radius: 8px;
  padding: 1.25rem 1rem;
  text-align: left;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.step-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #0284c7;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  flex-shrink: 0;
}

.step-body h4 {
  margin: 0 0 0.25rem;
  font-size: 0.92rem;
  color: #f1f5f9;
}

.step-body p {
  margin: 0;
  font-size: 0.78rem;
  color: #94a3b8;
  line-height: 1.45;
}

.step-body code {
  color: #38bdf8;
  background: #090e17;
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 0.75rem;
}

.guide-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

/* 按钮通用组件 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0.45rem 0.9rem;
  font-size: 0.82rem;
  font-weight: 600;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn.primary {
  background: #0284c7;
  color: #ffffff;
}

.btn.primary:hover:not(:disabled) {
  background: #0369a1;
}

.btn.secondary {
  background: #1f2937;
  border: 1px solid #374151;
  color: #f1f5f9;
}

.btn.secondary:hover:not(:disabled) {
  background: #374151;
}

.btn.outline {
  background: transparent;
  border: 1px solid #475569;
  color: #cbd5e1;
}

.btn.outline:hover:not(:disabled) {
  border-color: #94a3b8;
  color: #ffffff;
}

.btn.btn-sm {
  padding: 0.32rem 0.68rem;
  font-size: 0.78rem;
}

.btn.btn-lg {
  padding: 0.65rem 1.25rem;
  font-size: 0.9rem;
}

.btn.text-btn {
  background: transparent;
  border: none;
  color: #38bdf8;
  padding: 0;
  font-weight: 500;
  cursor: pointer;
  text-decoration: underline;
}

.btn.text-btn:hover {
  color: #7dd3fc;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 权限受限卡片 */
.forbidden-card {
  margin: 4rem auto;
  max-width: 540px;
  padding: 2.5rem;
  background: #111827;
  border: 1px solid #ef4444;
  border-radius: 12px;
  text-align: center;
}

.forbidden-icon {
  font-size: 3rem;
  margin-bottom: 0.75rem;
}

.forbidden-title {
  font-size: 1.25rem;
  color: #f87171;
  margin: 0 0 0.5rem;
}

.forbidden-desc {
  font-size: 0.88rem;
  color: #94a3b8;
  line-height: 1.6;
  margin: 0 0 1.5rem;
}

/* 弹窗设计 */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-card {
  background: #111827;
  border: 1px solid #374151;
  border-radius: 10px;
  width: 95%;
  max-width: 580px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #1f2937;
  background: #161f30;
}

.modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-icon {
  font-size: 1.15rem;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: #f8fafc;
}

.modal-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 1.4rem;
  cursor: pointer;
  line-height: 1;
}

.modal-close:hover {
  color: #ffffff;
}

.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.modal-hint {
  font-size: 0.8rem;
  color: #94a3b8;
  margin: 0;
  line-height: 1.5;
  background: rgba(14, 165, 233, 0.08);
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
  border-left: 3px solid #0284c7;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-row {
  display: flex;
  gap: 12px;
}

.col-half {
  flex: 1;
}

.form-group label {
  font-size: 0.8rem;
  color: #cbd5e1;
  font-weight: 500;
}

.form-control {
  background: #090e17;
  border: 1px solid #374151;
  border-radius: 6px;
  padding: 0.55rem 0.75rem;
  color: #f8fafc;
  font-size: 0.86rem;
}

.form-control:focus {
  outline: none;
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.25);
}

.checkbox-group {
  margin-top: 0.25rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  color: #cbd5e1;
  cursor: pointer;
}

.gateway-debug-box {
  background: #090e17;
  border: 1px solid #1f2937;
  border-radius: 6px;
  padding: 0.65rem 0.8rem;
  margin-top: 0.5rem;
}

.gateway-debug-label {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 4px;
}

.gateway-debug-url {
  word-break: break-all;
  font-size: 0.72rem;
  color: #38bdf8;
  font-family: ui-monospace, monospace;
  margin-bottom: 6px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0.85rem 1.25rem;
  border-top: 1px solid #1f2937;
  background: #0b1120;
}

@media (max-width: 900px) {
  .control-toolbar {
    height: auto;
    padding: 0.75rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  .toolbar-right {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
  }
  .steps-grid {
    grid-template-columns: 1fr;
  }
  .topology-strip {
    flex-direction: column;
    gap: 8px;
  }
  .topo-arrow {
    transform: rotate(90deg);
    display: inline-block;
  }
}
</style>
