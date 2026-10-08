<template>
  <div class="top-inbox-wrap" ref="inboxWrapRef">
    <!-- 顶栏收件箱入口胶囊按钮 -->
    <button
      type="button"
      class="top-inbox-btn"
      :class="{ 'has-unread': unreadCount > 0, 'is-active': dropdownOpen }"
      @click.stop="toggleDropdown"
      title="点击打开个人消息收件箱"
    >
      <span class="inbox-icon">📥</span>
      <span class="inbox-label">收件箱</span>
      <span v-if="unreadCount > 0" class="inbox-badge-pill">
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- 移动端蒙层 -->
    <div v-if="dropdownOpen" class="inbox-backdrop" @click="dropdownOpen = false"></div>

    <!-- 消息中心下拉气泡卡片 (Glassmorphism) -->
    <div v-if="dropdownOpen" class="inbox-dropdown-card" @click.stop>
      <div class="inbox-dropdown-header">
        <div class="header-title-box">
          <span class="header-icon">📥</span>
          <div>
            <div class="header-main-title">
              <span>个人收件箱</span>
              <span v-if="unreadCount > 0" class="unread-tag">{{ unreadCount }} 未读</span>
            </div>
            <p class="header-sub-title">系统通知、联合会审会签及站内消息</p>
          </div>
        </div>
        <div class="header-actions">
          <button
            v-if="unreadCount > 0"
            type="button"
            class="btn-text-action"
            @click="handleMarkAllRead"
            :disabled="actionLoading"
            title="一键标记所有消息为已读"
          >
            ✓ 全部已读
          </button>
          <button
            type="button"
            class="btn-icon-refresh"
            @click="fetchMessages"
            :disabled="loading"
            title="刷新消息"
          >
            🔄
          </button>
        </div>
      </div>

      <!-- 分类 Tab -->
      <div class="inbox-tab-bar">
        <button
          type="button"
          class="inbox-tab-btn"
          :class="{ active: activeCategory === 'all' }"
          @click="switchCategory('all')"
        >
          全部
        </button>
        <button
          type="button"
          class="inbox-tab-btn"
          :class="{ active: activeCategory === 'joint_review' }"
          @click="switchCategory('joint_review')"
        >
          ⚖️ 会审会签
        </button>
        <button
          type="button"
          class="inbox-tab-btn"
          :class="{ active: activeCategory === 'broadcast' }"
          @click="switchCategory('broadcast')"
        >
          📢 系统广播
        </button>
        <button
          type="button"
          class="inbox-tab-btn"
          :class="{ active: activeCategory === 'direct_chat' }"
          @click="switchCategory('direct_chat')"
        >
          💬 站内互动
        </button>
      </div>

      <!-- 消息列表 -->
      <div class="inbox-dropdown-body">
        <div v-if="loading && !messages.length" class="state-hint">
          <span class="loading-spinner">⌛</span>
          <span>正在同步消息...</span>
        </div>
        <div v-else-if="filteredMessages.length === 0" class="state-hint empty">
          <span class="empty-icon">✓</span>
          <span>收件箱空空如也，暂无相关消息</span>
        </div>
        <div v-else class="message-list-scroll">
          <div
            v-for="msg in filteredMessages"
            :key="msg.id"
            class="message-item-row"
            :class="{ 'is-unread': !msg.is_read }"
            @click="handleMessageClick(msg)"
          >
            <div class="msg-dot-col">
              <span v-if="!msg.is_read" class="unread-dot"></span>
              <span v-else class="read-dot"></span>
            </div>
            <div class="msg-content-col">
              <div class="msg-head-line">
                <span class="msg-type-pill" :class="msg.msg_type">
                  {{ getTypeLabel(msg.msg_type) }}
                </span>
                <span class="msg-title">{{ msg.title }}</span>
                <span class="msg-time">{{ msg.created_at }}</span>
              </div>
              <div class="msg-body-text">
                {{ msg.content }}
              </div>
              <div class="msg-footer-line">
                <span class="msg-sender">来自：<strong>{{ msg.sender_name }}</strong> ({{ msg.sender_role }})</span>
                <span v-if="msg.action_url" class="msg-jump-hint">点击直达办理 ➔</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getMyInboxMessages,
  getMyUnreadCount,
  markAllMessagesRead,
  markMessageRead,
} from '../services/systemMessageApi'

const router = useRouter()
const inboxWrapRef = ref(null)
const dropdownOpen = ref(false)

const loading = ref(false)
const actionLoading = ref(false)
const unreadCount = ref(0)
const messages = ref([])
const activeCategory = ref('all')

let pollTimer = null

async function fetchUnreadCount() {
  try {
    const res = await getMyUnreadCount()
    if (res && res.ok) {
      unreadCount.value = Number(res.unread_count) || 0
    }
  } catch (e) {
    // 静默
  }
}

async function fetchMessages() {
  try {
    loading.value = true
    const res = await getMyInboxMessages({ page: 1, page_size: 50 })
    if (res && res.ok) {
      unreadCount.value = Number(res.unread_count) || 0
      messages.value = res.items || []
    }
  } catch (e) {
    // 静默
  } finally {
    loading.value = false
  }
}

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value
  if (dropdownOpen.value) {
    fetchMessages()
  }
}

function switchCategory(cat) {
  activeCategory.value = cat
}

const filteredMessages = computed(() => {
  if (activeCategory.value === 'all') {
    return messages.value
  }
  return messages.value.filter((m) => m.msg_type === activeCategory.value)
})

function getTypeLabel(type) {
  const map = {
    joint_review: '会审',
    broadcast: '广播',
    direct_chat: '私信',
    system_alert: '警报',
  }
  return map[type] || '通知'
}

async function handleMessageClick(msg) {
  if (!msg.is_read) {
    msg.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    markMessageRead(msg.id).catch(() => {})
  }

  if (msg.action_url) {
    dropdownOpen.value = false
    router.push(msg.action_url)
  }
}

async function handleMarkAllRead() {
  try {
    actionLoading.value = true
    const res = await markAllMessagesRead()
    if (res && res.ok) {
      messages.value.forEach((m) => {
        m.is_read = true
      })
      unreadCount.value = 0
    }
  } catch (e) {
    // 静默
  } finally {
    actionLoading.value = false
  }
}

function handleClickOutside(e) {
  if (inboxWrapRef.value && !inboxWrapRef.value.contains(e.target)) {
    dropdownOpen.value = false
  }
}

onMounted(() => {
  fetchUnreadCount()
  document.addEventListener('click', handleClickOutside)
  // 30 秒轮询一次未读数
  pollTimer = setInterval(() => {
    fetchUnreadCount()
  }, 30000)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.top-inbox-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}

/* 顶栏收件箱入口按钮 */
.top-inbox-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(226, 232, 240, 0.9);
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.top-inbox-btn:hover {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #0f172a;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.top-inbox-btn.is-active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.top-inbox-btn.has-unread {
  border-color: #fca5a5;
  background: #fff5f5;
  color: #b91c1c;
}

.inbox-icon {
  font-size: 14px;
}

.inbox-label {
  letter-spacing: 0.3px;
}

.inbox-badge-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #ef4444;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  box-shadow: 0 1px 4px rgba(239, 68, 68, 0.4);
  animation: pulse-badge 2.4s infinite;
}

@keyframes pulse-badge {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

/* 蒙层 */
.inbox-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1050;
  background: rgba(15, 23, 42, 0.15);
}

/* 下拉窗 */
.inbox-dropdown-card {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 380px;
  max-width: 90vw;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 16px 36px -6px rgba(15, 23, 42, 0.18), 0 0 0 1px rgba(0, 0, 0, 0.02);
  z-index: 1100;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 头部 */
.inbox-dropdown-header {
  padding: 14px 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title-box {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  font-size: 22px;
}

.header-main-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.unread-tag {
  font-size: 11px;
  font-weight: 600;
  background: #fee2e2;
  color: #dc2626;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid #fca5a5;
}

.header-sub-title {
  margin: 2px 0 0;
  font-size: 11.5px;
  color: #64748b;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-text-action {
  background: transparent;
  border: none;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
}

.btn-text-action:hover {
  background: #e0e7ff;
}

.btn-icon-refresh {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 4px 6px;
  border-radius: 4px;
}

.btn-icon-refresh:hover {
  background: #e2e8f0;
}

/* 分类 Tab */
.inbox-tab-bar {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  background: #ffffff;
  border-bottom: 1px solid #f1f5f9;
}

.inbox-tab-btn {
  flex: 1;
  padding: 6px 0;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  text-align: center;
}

.inbox-tab-btn:hover {
  color: #1e293b;
  background: #f1f5f9;
}

.inbox-tab-btn.active {
  color: #2563eb;
  background: #eff6ff;
  font-weight: 700;
}

/* 列表主体 */
.inbox-dropdown-body {
  max-height: 380px;
  overflow-y: auto;
  background: #ffffff;
}

.state-hint {
  padding: 40px 20px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.empty-icon {
  font-size: 24px;
  color: #10b981;
}

.message-list-scroll {
  display: flex;
  flex-direction: column;
}

.message-item-row {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
  transition: background 0.15s ease;
}

.message-item-row:hover {
  background: #f8fafc;
}

.message-item-row.is-unread {
  background: #fafafa;
}

.msg-dot-col {
  padding-top: 4px;
}

.unread-dot {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
}

.read-dot {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e1;
}

.msg-content-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.msg-head-line {
  display: flex;
  align-items: center;
  gap: 6px;
}

.msg-type-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
}

.msg-type-pill.joint_review {
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fed7aa;
}

.msg-type-pill.broadcast {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.msg-type-pill.direct_chat {
  background: #f3e8ff;
  color: #7e22ce;
  border: 1px solid #e9d5ff;
}

.msg-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.msg-time {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
}

.msg-body-text {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.msg-footer-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.msg-jump-hint {
  color: #2563eb;
  font-weight: 600;
}
</style>
