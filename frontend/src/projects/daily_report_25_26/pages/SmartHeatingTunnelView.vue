<template>
  <div class="smart-heating-tunnel-view">
    <AppHeader />
    <main class="tunnel-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <!-- 非 Global_admin 拦截提示卡片 -->
      <section v-if="!isGlobalAdmin" class="card elevated forbidden-card">
        <div class="forbidden-icon">🚫</div>
        <h3 class="forbidden-title">访问权限受限 · 仅限 Global_admin</h3>
        <p class="forbidden-desc">
          智慧供热内网直通通道直连核心生产调度内网系统，严格仅限<strong>系统全局管理员 (Global_admin)</strong> 访问与操作。
        </p>
      </section>

      <!-- 仅 Global_admin 可见的主体控制与操作区 -->
      <template v-else>
        <!-- 顶部控制与状态栏 -->
        <section class="card elevated control-bar">
        <div class="bar-left">
          <div class="portal-badge-icon">🌐</div>
          <div>
            <div class="title-row">
              <h2 class="portal-title">智慧供热平台内网直通</h2>
              <span class="badge-role">反向代理中继</span>
            </div>
            <p class="portal-subtitle">
              办公电脑反向穿透中继 · 免开发直通内网 <code>{{ tunnelConfig.target_base_url || 'http://192.168.1.206:6688' }}</code> 全功能控制台
            </p>
          </div>
        </div>

        <div class="bar-right">
          <!-- 实时连接状态胶囊 -->
          <div class="status-capsule" :class="{ online: isRelayOnline, offline: !isRelayOnline }">
            <span class="dot"></span>
            <span class="status-label">{{ isRelayOnline ? '中继在线 (已连接内网)' : '中继未连接' }}</span>
            <span v-if="isRelayOnline && tunnelStatus.client_ip" class="status-extra">
              IP: {{ tunnelStatus.client_ip }}
            </span>
            <span v-if="tunnelStatus.last_heartbeat" class="status-time">
              ({{ formattedHeartbeat }})
            </span>
          </div>

          <!-- 功能按钮组 -->
          <div class="btn-group">
            <button
              class="btn primary btn-sm btn-download"
              type="button"
              :disabled="downloading"
              title="下载预配置好的 Win7 Python 3.8 中继客户端脚本，双击即跑"
              @click="handleDownloadClient"
            >
              {{ downloading ? '下载中…' : '📥 下载 Win7 中继客户端' }}
            </button>

            <button
              class="btn secondary btn-sm btn-config"
              type="button"
              title="配置内网平台登录账号、密码及中继通信密钥"
              @click="openConfigModal"
            >
              ⚙️ 平台账号与设置
            </button>

            <button
              v-if="isRelayOnline"
              class="btn secondary btn-sm btn-external"
              type="button"
              title="在新浏览器标签页中全屏打开内网平台"
              @click="openInNewTab"
            >
              ↗ 新窗口打开
            </button>

            <button
              class="btn secondary btn-sm btn-refresh"
              type="button"
              :disabled="refreshing"
              title="强制重载内网直通视窗"
              @click="handleReloadFrame"
            >
              {{ refreshing ? '刷新中…' : '⟳ 刷新视图' }}
            </button>
          </div>
        </div>
      </section>

      <!-- 主视窗区域 -->
      <section class="card elevated viewport-card">
        <!-- 场景 1：中继离线时展示连接引导向导 -->
        <div v-if="!isRelayOnline" class="offline-guide">
          <div class="guide-hero-icon">🔌</div>
          <h3 class="guide-title">智慧供热内网直通链路未连接</h3>
          <p class="guide-desc">
            外网通过您的办公电脑作为安全中继器访问内网平台，目前未检测到中继客户端的活跃心跳。
          </p>

          <div class="steps-container">
            <div class="step-card">
              <div class="step-num">1</div>
              <div class="step-content">
                <h4>下载中继客户端</h4>
                <p>点击下方按钮，下载专为 Win7 + Python 3.8 定制的免依赖单文件脚本。</p>
              </div>
            </div>

            <div class="step-card">
              <div class="step-num">2</div>
              <div class="step-content">
                <h4>在办公电脑运行</h4>
                <p>在能访问 <code>192.168.1.206</code> 的办公电脑上双击或运行 <code>python smart_heating_tunnel_win7.py</code>。</p>
              </div>
            </div>

            <div class="step-card">
              <div class="step-num">3</div>
              <div class="step-content">
                <h4>即刻畅通访问</h4>
                <p>中继建立长轮询隧道后，本页面将自动点亮绿灯并无感加载内网控制台。</p>
              </div>
            </div>
          </div>

          <div class="guide-actions">
            <button class="btn primary btn-lg" :disabled="downloading" @click="handleDownloadClient">
              {{ downloading ? '正在打包下载…' : '📥 立即下载中继客户端 (.py)' }}
            </button>
            <button class="btn secondary btn-lg" @click="fetchStatusAndConfig">
              🔄 检查连接状态
            </button>
          </div>
        </div>

        <!-- 场景 2：中继在线时，无缝呈现内网 iframe -->
        <div v-else class="iframe-container">
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

      <!-- 账号与配置弹窗 Modal -->
      <div v-if="showConfigModal" class="modal-backdrop" @click.self="showConfigModal = false">
        <div class="modal-card">
          <div class="modal-header">
            <h3>⚙️ 平台账号与反向中继配置</h3>
            <button class="modal-close" type="button" @click="showConfigModal = false">×</button>
          </div>

          <div class="modal-body">
            <p class="modal-hint">
              此处配置将被中继客户端与网关持久化保存。配置内网平台账号后，系统可在内网会话过期时自动代登，保持外网直通无感。
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
                <label>入口路径 (Portal Path)</label>
                <input
                  v-model.trim="editConfig.portal_path"
                  type="text"
                  placeholder="/vindex/"
                  class="form-control"
                />
              </div>
              <div class="form-group col-half">
                <label>中继通信密钥 (Tunnel Secret)</label>
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
                  placeholder="请输入平台用户名"
                  class="form-control"
                />
              </div>
              <div class="form-group col-half">
                <label>内网平台登录密码</label>
                <input
                  v-model="editConfig.auth_password"
                  type="password"
                  placeholder="未修改请保持为空"
                  class="form-control"
                />
              </div>
            </div>

            <div class="form-group checkbox-group">
              <label class="checkbox-label">
                <input v-model="editConfig.auto_login_enabled" type="checkbox" />
                <span>启用内网账号自动代登与 Session 会话持久保持</span>
              </label>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn secondary btn-sm" type="button" @click="showConfigModal = false">取消</button>
            <button class="btn primary btn-sm" type="button" :disabled="savingConfig" @click="handleSaveConfig">
              {{ savingConfig ? '保存中…' : '💾 保存持久化配置' }}
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
import { useRoute } from 'vue-router'
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
const auth = useAuthStore()
const projectKey = computed(() => route.params.projectKey || 'daily_report_25_26')
const isGlobalAdmin = computed(() => auth.user?.group === 'Global_admin')

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
let pollTimer = null

// 计算网关 URL (自动附加 Global_admin 的会话 token)
const gatewayUrl = computed(() => {
  const pPath = (tunnelConfig.value.portal_path || 'vindex/').replace(/^\/+/, '')
  const base = getTunnelGatewayUrl(projectKey.value, pPath)
  const token = auth.token || ''
  return token ? `${base}?phoenix_token=${encodeURIComponent(token)}` : base
})

// 心跳时间友好展示
const formattedHeartbeat = computed(() => {
  if (!tunnelStatus.value.last_heartbeat) return ''
  return `更新于: ${tunnelStatus.value.last_heartbeat.slice(11, 19)}`
})

// 获取状态与配置
async function fetchStatusAndConfig() {
  if (!isGlobalAdmin.value) return
  try {
    const statusData = await fetchTunnelStatus(projectKey.value)
    tunnelStatus.value = statusData
    isRelayOnline.value = Boolean(statusData.online)

    const cfgData = await fetchTunnelConfig(projectKey.value)
    tunnelConfig.value = cfgData
  } catch (err) {
    console.warn('获取中继状态失败:', err)
  }
}

// 打开配置弹窗
function openConfigModal() {
  editConfig.value = {
    target_base_url: tunnelConfig.value.target_base_url || 'http://192.168.1.206:6688',
    portal_path: tunnelConfig.value.portal_path || '/vindex/',
    login_path: tunnelConfig.value.login_path || '/vindex/login',
    auth_username: tunnelConfig.value.auth_username || '',
    auth_password: '', // 留空表示不改动
    tunnel_secret: tunnelConfig.value.tunnel_secret || 'phoenix_tunnel_secret_2026',
    auto_login_enabled: tunnelConfig.value.auto_login_enabled ?? true,
  }
  showConfigModal.value = true
}

// 保存配置
async function handleSaveConfig() {
  savingConfig.value = true
  try {
    await updateTunnelConfig(editConfig.value, projectKey.value)
    showConfigModal.value = false
    await fetchStatusAndConfig()
    alert('持久化配置已成功保存！若更新了账号密码或密钥，请重新下载并启动中继脚本。')
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
    alert(`下载失败: ${err.message || err}`)
  } finally {
    downloading.value = false
  }
}

// 刷新视窗
function handleReloadFrame() {
  refreshing.value = true
  fetchStatusAndConfig()
  if (portalIframe.value) {
    try {
      portalIframe.value.src = gatewayUrl.value + '?_t=' + Date.now()
    } catch {
      // 忽略跨域重载错误
    }
  }
  setTimeout(() => {
    refreshing.value = false
  }, 800)
}

// 在新标签页打开
function openInNewTab() {
  window.open(gatewayUrl.value, '_blank')
}

function onIframeLoad() {
  // iframe 加载完成
}

onMounted(() => {
  fetchStatusAndConfig()
  // 每 8 秒自动轮询心跳状态
  pollTimer = setInterval(fetchStatusAndConfig, 8000)
})

onBeforeUnmount(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.smart-heating-tunnel-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary, #0f172a);
  color: var(--text-primary, #f8fafc);
}

.tunnel-main {
  flex: 1;
  padding: 1.25rem 2rem 2rem;
  max-width: 1720px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* 顶部控制栏 */
.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--bg-card, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 12px;
  flex-wrap: wrap;
  gap: 1rem;
}

.bar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.portal-badge-icon {
  font-size: 2.2rem;
  background: rgba(56, 189, 248, 0.15);
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.portal-title {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 700;
  color: #f1f5f9;
}

.badge-role {
  font-size: 0.75rem;
  padding: 2px 8px;
  background: rgba(14, 165, 233, 0.2);
  color: #38bdf8;
  border: 1px solid rgba(14, 165, 233, 0.4);
  border-radius: 999px;
  font-weight: 600;
}

.portal-subtitle {
  margin: 0.25rem 0 0;
  font-size: 0.88rem;
  color: #94a3b8;
}

.portal-subtitle code {
  color: #38bdf8;
  background: rgba(15, 23, 42, 0.6);
  padding: 2px 6px;
  border-radius: 4px;
}

.bar-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

/* 状态指示胶囊 */
.status-capsule {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-capsule.online {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.status-capsule.offline {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.status-capsule .dot {
  width: 8px;
  height: 8px;
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
  color: #94a3b8;
  font-size: 0.8rem;
  font-weight: normal;
}

.status-time {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: normal;
}

.btn-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* 主视窗卡片 */
.viewport-card {
  flex: 1;
  min-height: 780px;
  background: var(--bg-card, #1e293b);
  border: 1px solid var(--border-color, #334155);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.iframe-container {
  flex: 1;
  width: 100%;
  height: 100%;
  position: relative;
  min-height: 800px;
}

.portal-frame {
  width: 100%;
  height: 100%;
  min-height: 800px;
  border: none;
  display: block;
  background: #ffffff;
}

/* 离线引导 */
.offline-guide {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
}

.guide-hero-icon {
  font-size: 4.5rem;
  margin-bottom: 1rem;
}

.guide-title {
  font-size: 1.6rem;
  color: #f8fafc;
  margin: 0 0 0.5rem;
}

.guide-desc {
  font-size: 0.95rem;
  color: #94a3b8;
  max-width: 600px;
  line-height: 1.6;
  margin: 0 0 2.5rem;
}

.steps-container {
  display: flex;
  gap: 1.5rem;
  max-width: 900px;
  width: 100%;
  margin-bottom: 2.5rem;
}

.step-card {
  flex: 1;
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 1.5rem;
  text-align: left;
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.step-num {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #0284c7;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}

.step-content h4 {
  margin: 0 0 0.4rem;
  font-size: 1.05rem;
  color: #e2e8f0;
}

.step-content p {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.5;
}

.step-content code {
  color: #38bdf8;
  background: rgba(30, 41, 59, 0.8);
  padding: 1px 4px;
  border-radius: 4px;
}

.guide-actions {
  display: flex;
  gap: 1rem;
}

/* 弹窗样式 */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  width: 100%;
  max-width: 600px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #334155;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #f1f5f9;
}

.modal-close {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 1.5rem;
  cursor: pointer;
  line-height: 1;
}

.modal-close:hover {
  color: #f8fafc;
}

.modal-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modal-hint {
  font-size: 0.85rem;
  color: #94a3b8;
  margin: 0 0 0.5rem;
  line-height: 1.5;
  background: rgba(14, 165, 233, 0.1);
  padding: 0.75rem;
  border-radius: 6px;
  border-left: 3px solid #0284c7;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-row {
  display: flex;
  gap: 1rem;
}

.col-half {
  flex: 1;
}

.form-group label {
  font-size: 0.85rem;
  color: #cbd5e1;
  font-weight: 500;
}

.form-control {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 6px;
  padding: 0.6rem 0.8rem;
  color: #f8fafc;
  font-size: 0.9rem;
}

.form-control:focus {
  outline: none;
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.2);
}

.checkbox-group {
  margin-top: 0.5rem;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.88rem;
  color: #cbd5e1;
  cursor: pointer;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #334155;
  background: #182234;
}

/* 按钮通用 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  font-size: 0.88rem;
  font-weight: 600;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn.primary {
  background: #0284c7;
  color: #ffffff;
}

.btn.primary:hover:not(:disabled) {
  background: #0369a1;
}

.btn.secondary {
  background: #334155;
  color: #f1f5f9;
}

.btn.secondary:hover:not(:disabled) {
  background: #475569;
}

.btn.btn-sm {
  padding: 0.38rem 0.75rem;
  font-size: 0.82rem;
}

.btn.btn-lg {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.forbidden-card {
  padding: 4rem 2rem;
  text-align: center;
  background: #1e293b;
  border: 1px solid #ef4444;
  border-radius: 12px;
  max-width: 600px;
  margin: 3rem auto;
}

.forbidden-icon {
  font-size: 3.5rem;
  margin-bottom: 1rem;
}

.forbidden-title {
  color: #f87171;
  font-size: 1.4rem;
  margin: 0 0 0.75rem;
}

.forbidden-desc {
  color: #94a3b8;
  line-height: 1.6;
  margin: 0;
}

@media (max-width: 860px) {
  .control-bar {
    flex-direction: column;
    align-items: flex-start;
  }
  .bar-right {
    width: 100%;
    justify-content: space-between;
  }
  .steps-container {
    flex-direction: column;
  }
}
</style>
