<template>
  <header class="app-header">
    <div class="app-header__inner">
      <div class="brand" @click="goHome">
        <span class="brand-mark"></span>
        <div class="brand-text">
          <span class="brand-name">大连洁净能源集团</span>
          <span class="brand-sub">数据智算平台</span>
        </div>
      </div>
      <nav class="nav">
        <!-- 全局在线用户人数发光胶囊微件 -->
        <div class="presence-container" ref="presenceWrapRef">
          <button 
            type="button" 
            class="presence-capsule" 
            :class="{ 'active': showPresenceDropdown }"
            @click.stop="togglePresenceDropdown"
            title="点击查看当前系统在线人员列表"
          >
            <span class="online-pulse-dot"></span>
            <span class="presence-label">在线 <strong>{{ onlineCount }}</strong> 人</span>
          </button>

          <!-- 移动端半透明背景遮罩蒙层 -->
          <div v-if="showPresenceDropdown" class="presence-backdrop" @click="showPresenceDropdown = false"></div>

          <!-- Glassmorphism 在线人员展示卡片 -->
          <div v-if="showPresenceDropdown" class="presence-dropdown" @click.stop>
            <div class="presence-dropdown-header">
              <div class="dropdown-title">
                <span class="online-pulse-dot static"></span>
                <span>平台实时在线人员 ({{ onlineCount }})</span>
              </div>
              <span class="refresh-hint">30s 自动同步</span>
            </div>
            
            <div v-if="loadingPresence && !onlineUsers.length" class="presence-loading">正在读取在线列表...</div>
            <div v-else-if="!onlineUsers.length" class="presence-empty">当前无活跃人员</div>
            <div v-else class="presence-user-list">
              <div v-for="u in onlineUsers" :key="u.username" class="presence-user-item" :class="{ 'is-me': u.username === auth.user?.username }">
                <div class="user-avatar" :class="{ 'avatar-me': u.username === auth.user?.username }">
                  {{ getAvatarText(u.display_name || u.username) }}
                </div>
                <div class="user-details">
                  <div class="user-name-row">
                    <span class="user-display-name">
                      {{ u.username || u.display_name }}
                      <span v-if="u.username === auth.user?.username" class="me-badge">我</span>
                    </span>
                    <span class="user-group-tag">{{ getGroupLabel(u.group) }}</span>
                  </div>
                  <div class="user-status-row">
                    <span class="user-page-badge">📍 当前位置：<strong>{{ u.current_page || '在线' }}</strong></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <button
          v-if="auth.canAccessAdminConsole"
          class="btn btn-admin"
          @click="goAdminConsole"
        >
          进入后台
        </button>
        <span v-if="userLabel" class="user-info">{{ userLabel }}</span>
        <button class="btn" @click="logout">退出</button>
      </nav>
    </div>
  </header>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../store/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// 在线用户 Presence 响应式状态（持久化最近已知在线人数，消除进入新页面时从 1 突然跳变的视觉闪烁）
const PRESENCE_COUNT_STORAGE_KEY = 'phoenix_last_online_count'

function getInitialOnlineCount() {
  if (typeof window === 'undefined') return 1
  try {
    const cached = parseInt(localStorage.getItem(PRESENCE_COUNT_STORAGE_KEY), 10)
    if (!isNaN(cached) && cached > 0) return cached
  } catch (e) {}
  return 1
}

function updateOnlineCount(count) {
  const num = Math.max(1, parseInt(count, 10) || 1)
  onlineCount.value = num
  try {
    localStorage.setItem(PRESENCE_COUNT_STORAGE_KEY, String(num))
  } catch (e) {}
}

const presenceWrapRef = ref(null)
const showPresenceDropdown = ref(false)
const onlineCount = ref(getInitialOnlineCount())
const onlineUsers = ref([])
const loadingPresence = ref(false)
let heartbeatTimer = null

function goHome() {
  router.push('/projects')
}

function goAdminConsole() {
  const currentPath = route.fullPath || route.path
  if (currentPath && !currentPath.startsWith('/admin-console') && currentPath !== '/login') {
    router.push({ path: '/admin-console', query: { from: currentPath } })
  } else {
    router.push('/admin-console')
  }
}

const userLabel = computed(() => {
  if (!auth?.user) return ''
  const unit = auth.user.unit ? `｜${auth.user.unit}` : ''
  return `${auth.user.username}${unit}`
})

function getAvatarText(name) {
  const str = String(name || '').trim()
  if (!str) return 'U'
  return str[0].toUpperCase()
}

function getGroupLabel(group) {
  const map = {
    Global_admin: '全局管理员',
    Supply_entity: '供给侧厂家',
    Demand_entity: '需求侧施工',
    Warehouse_manager: '仓库管理组',
    tube_global_viewer: '全局观察员',
  }
  return map[group] || group || '普通用户'
}

function getCurrentPageName() {
  if (route.meta?.title) return route.meta.title

  const path = route.path || ''
  const pageKey = route.params?.pageKey

  // 1. 特殊固定业务页面与工具页判定
  if (path.includes('/spring-dashboard')) return '春节专刊大盘'
  if (path.includes('/import-workspace')) return '月度数据导入'
  if (path.includes('/query-tool')) return '月度数据查询'
  if (path.includes('/page_showcase')) return '案例组件展示'
  if (path.includes('/admin-console')) return '后台管理控制台'
  if (path.includes('/admin-file-editor')) return '系统文件编辑器'
  if (path.includes('/debug/runtime-eval')) return '调测诊断工作台'

  // 2. 业务页面功能动作优先匹配
  if (path.includes('/data-analysis')) return '数据分析看板'
  if (path.includes('/display')) return '动态展示看板'
  if (path.includes('/approval')) return '数据审核页'
  if (path.includes('/sheets/')) return '数据填报工作区'
  if (path.includes('/dashboard')) return '数据看板'
  if (path.includes('/pages') && !pageKey && path.endsWith('/pages')) return '页面选择列表'

  // 3. 动态 pageKey 词表映射
  if (pageKey) {
    const pageMap = {
      dashboard: '数据看板',
      demand_management: '需求管理',
      supply_management: '供给管理',
      warehouse_management: '仓库到货管理',
      global_management: '全局大盘配置',
      gis_map: 'GIS地图看板',
      comprehensive_query: '综合数据查询中心',
      history_query: '综合数据查询中心',
      analysis: '数据分析看板',
      approval: '数据审核',
    }
    if (pageMap[pageKey]) return pageMap[pageKey]
    return pageKey
  }

  // 4. 仅当路径正好为项目大口径/首页时才判定为项目入口或选择页
  if (path === '/projects' || path === '/projects/') return '项目选择页'
  if (route.params?.projectKey) {
    const projectMap = {
      daily_report_25_26: '25-26采暖季日报',
      daily_report_spring_festval_2026: '2026春节保供专刊',
      monthly_data_pull: '月度数据拉取',
      monthly_data_show: '月度数据展示',
      insulation_pipe_supply_2026: '2026保温管供给大盘',
      page_showcase: '页面展示中心'
    }
    const name = projectMap[route.params.projectKey]
    return name ? `${name}入口` : '项目入口'
  }

  return document.title || '工作区'
}

// 物理发送心跳 (Presence Heartbeat)
async function sendHeartbeat() {
  if (!auth?.user) return
  const projectKey = route.params?.projectKey || 'insulation_pipe_supply_2026'
  const currentPage = getCurrentPageName()
  
  try {
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(projectKey)}/presence/heartbeat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': auth.token ? `Bearer ${auth.token}` : '',
      },
      body: JSON.stringify({
        username: auth.user.username,
        display_name: auth.user.username,
        unit: auth.user.unit || '',
        group: auth.user.group || '',
        current_page: currentPage,
      }),
    })
    if (response.ok) {
      const data = await response.json()
      if (data.online_count) {
        updateOnlineCount(data.online_count)
      }
    }
  } catch (e) {
    console.debug('Presence heartbeat error:', e)
  }
}

// 拉取实时在线人员详情列表
async function fetchOnlineUsers() {
  if (!auth?.user) return
  const projectKey = route.params?.projectKey || 'insulation_pipe_supply_2026'
  loadingPresence.value = true
  try {
    const response = await fetch(`/api/v1/projects/${encodeURIComponent(projectKey)}/presence/online-users`, {
      headers: {
        'Authorization': auth.token ? `Bearer ${auth.token}` : '',
      },
    })
    if (response.ok) {
      const data = await response.json()
      let list = Array.isArray(data.users) ? [...data.users] : []
      const myUsername = auth.user?.username

      // 强校验：保障当前登录的【我自己】100% 呈现在列表中
      if (myUsername) {
        const hasMe = list.some(u => u.username === myUsername)
        if (!hasMe) {
          list.unshift({
            username: myUsername,
            display_name: auth.user.username,
            unit: auth.user.unit || '当前账号',
            group: auth.user.group || '',
            current_page: getCurrentPageName(),
            last_seen_seconds_ago: 0
          })
        }
      }

      // 将【我自己】排序至最首位，方便第一眼识别
      list.sort((a, b) => {
        if (a.username === myUsername) return -1
        if (b.username === myUsername) return 1
        return (a.last_seen_seconds_ago || 0) - (b.last_seen_seconds_ago || 0)
      })

      onlineUsers.value = list
      updateOnlineCount(Math.max(data.online_count || 0, list.length))
    }
  } catch (e) {
    console.error('Fetch online users error:', e)
  } finally {
    loadingPresence.value = false
  }
}

function togglePresenceDropdown() {
  showPresenceDropdown.value = !showPresenceDropdown.value
  if (showPresenceDropdown.value) {
    fetchOnlineUsers()
  }
}

function handleGlobalClick(e) {
  if (presenceWrapRef.value && !presenceWrapRef.value.contains(e.target)) {
    showPresenceDropdown.value = false
  }
}

async function logout() {
  try {
    const projectKey = route.params?.projectKey || 'insulation_pipe_supply_2026'
    if (auth?.user && navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify({ username: auth.user.username })], { type: 'application/json' })
      navigator.sendBeacon(`/api/v1/projects/${encodeURIComponent(projectKey)}/presence/logout`, blob)
    }
  } catch (e) {
    // 静默降级
  }
  await auth.logout()
  router.replace('/login')
}

function handleVisibilityChange() {
  if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
    // 监听用户从后台切回标签页，立即主动唤醒补发心跳并拉取最新在线人数
    sendHeartbeat()
    if (showPresenceDropdown.value) {
      fetchOnlineUsers()
    }
  }
}

onMounted(() => {
  window.addEventListener('click', handleGlobalClick)
  document.addEventListener('visibilitychange', handleVisibilityChange)
  // 初次启动并设置 30 秒轮询心跳
  sendHeartbeat()
  fetchOnlineUsers()
  heartbeatTimer = setInterval(() => {
    sendHeartbeat()
    if (showPresenceDropdown.value) {
      fetchOnlineUsers()
    }
  }, 30000)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', handleGlobalClick)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer)
    heartbeatTimer = null
  }
})
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: linear-gradient(90deg, #0b3b86 0%, #0e4cba 60%, #2563eb 100%);
  color: #fff;
  box-shadow: 0 6px 16px rgba(0,0,0,.12);
}
.app-header__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; min-width: 0; }
.brand-mark { width: 10px; height: 10px; border-radius: 50%; background: #93c5fd; box-shadow: 0 0 0 3px rgba(147,197,253,.25); }
.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.brand-name { font-weight: 800; letter-spacing: .5px; white-space: nowrap; word-break: keep-all; line-height: 1.15; }
.brand-sub { opacity: .9; font-size: 12px; white-space: nowrap; word-break: keep-all; line-height: 1.1; }
.nav { display: flex; gap: 10px; flex-wrap: nowrap; align-items: center; }
.user-info {
  font-size: 13px;
  opacity: .9;
  align-self: center;
  white-space: nowrap;
}
.btn {
  height: 30px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,.35);
  background: rgba(255,255,255,.08);
  color: #fff;
  cursor: pointer;
  backdrop-filter: blur(4px);
  white-space: nowrap;
  word-break: keep-all;
  writing-mode: horizontal-tb;
}
.btn:hover { background: rgba(255,255,255,.16); }
.btn-admin {
  border-color: rgba(251, 191, 36, 0.75);
  background: rgba(251, 191, 36, 0.16);
  color: #fde68a;
}
.btn-admin:hover {
  background: rgba(251, 191, 36, 0.28);
}

/* ==================== 在线人员 Presence 胶囊与下拉卡片样式 ==================== */
.presence-container {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.presence-capsule {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: 20px;
  border: 1px solid rgba(52, 211, 153, 0.45);
  background: rgba(16, 185, 129, 0.15);
  color: #ecfdf5;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  backdrop-filter: blur(8px);
}

.presence-capsule:hover, .presence-capsule.active {
  background: rgba(16, 185, 129, 0.3);
  border-color: #34d399;
  box-shadow: 0 0 12px rgba(52, 211, 153, 0.35);
}

.online-pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #10b981;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  animation: pulseDot 2s infinite;
}

.online-pulse-dot.static {
  animation: none;
  box-shadow: 0 0 8px #10b981;
}

@keyframes pulseDot {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.presence-dropdown {
  position: absolute;
  top: 38px;
  right: 0;
  width: 310px;
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  padding: 12px;
  z-index: 1050;
  color: #f8fafc;
  animation: fadeInDown 0.2s ease-out;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.presence-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 8px;
}

.dropdown-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #34d399;
}

.refresh-hint {
  font-size: 10px;
  color: #94a3b8;
}

.presence-loading, .presence-empty {
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
  padding: 16px 0;
}

.presence-user-list {
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.presence-user-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: background 0.15s ease;
}

.presence-user-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
  color: #ffffff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4);
  flex-shrink: 0;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.user-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.user-display-name {
  font-size: 12px;
  font-weight: 600;
  color: #f1f5f9;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-unit-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.3);
  white-space: nowrap;
}

.user-status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10px;
  color: #94a3b8;
}

.user-group-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(14, 165, 233, 0.2);
  color: #38bdf8;
  border: 1px solid rgba(14, 165, 233, 0.35);
  white-space: nowrap;
}

/* 我自己 (Current User) 高亮展示 */
.presence-user-item.is-me {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(52, 211, 153, 0.35);
}

.avatar-me {
  background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.4) !important;
}

.me-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 0 5px;
  border-radius: 4px;
  background: #10b981;
  color: #ffffff;
  margin-left: 4px;
  vertical-align: middle;
}

/* 移动端遮罩蒙层 */
.presence-backdrop {
  display: none;
}

@media (max-width: 768px) {
  .app-header__inner {
    padding: 6px 10px;
    gap: 6px;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    min-height: 44px;
    box-sizing: border-box;
    overflow: visible; /* 移除 hidden 约束，防止裁剪下拉面板 */
  }
  .brand {
    gap: 6px;
    min-width: 0;
    flex: 1;
  }
  .brand-name {
    font-size: 13px;
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .brand-sub {
    display: none;
  }
  .brand-text {
    gap: 0;
    min-width: 0;
  }
  .nav {
    gap: 5px;
    flex-shrink: 0;
    align-items: center;
  }
  .user-info {
    display: none;
  }
  .btn {
    height: 26px;
    padding: 0 8px;
    font-size: 11px;
    border-radius: 6px;
  }
  .presence-capsule {
    height: 26px;
    padding: 0 8px;
    font-size: 11px;
  }

  /* 移动端半透明全屏蒙层 */
  .presence-backdrop {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(4px);
    z-index: 1999;
  }

  /* 移动端置顶玻璃弹窗卡片 */
  .presence-dropdown {
    position: fixed;
    top: 52px;
    left: 12px;
    right: 12px;
    width: auto;
    max-width: calc(100vw - 24px);
    z-index: 2000;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.2);
  }
}
</style>

