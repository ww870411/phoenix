<template>
  <div class="notif-bell-wrap" ref="bellWrapRef">
    <button
      type="button"
      class="notif-bell-btn"
      :class="{ 'has-badge': pendingCount > 0, 'is-active': dropdownOpen }"
      @click.stop="toggleDropdown"
      title="多方联合会审待办通知"
    >
      <span class="bell-icon">🔔</span>
      <span v-if="pendingCount > 0" class="notif-badge-pill">
        {{ pendingCount > 99 ? '99+' : pendingCount }}
      </span>
    </button>

    <!-- 下拉气泡卡片 -->
    <div v-if="dropdownOpen" class="notif-dropdown-card" @click.stop>
      <div class="dropdown-header">
        <div class="header-title">
          <span>待办会签通知</span>
          <span v-if="pendingCount > 0" class="badge-count">({{ pendingCount }})</span>
        </div>
        <button type="button" class="btn-refresh" @click="fetchNotifications" title="刷新">🔄</button>
      </div>

      <div class="dropdown-body">
        <div v-if="loading" class="empty-state">正在同步待办会审...</div>
        <div v-else-if="pendingCount === 0" class="empty-state">
          <span class="empty-icon">✓</span>
          <span>当前无待您会签的会审订单</span>
        </div>
        <div v-else class="notif-items-list">
          <div
            v-for="item in pendingItems"
            :key="item.review_id"
            class="notif-row"
            @click="goToItem(item)"
          >
            <div class="row-top">
              <span class="tag-cat" :class="item.order_category">{{ item.category_label }}</span>
              <span class="order-no font-mono">{{ item.order_no }}</span>
            </div>
            <div class="row-middle">
              <span class="sec-text">📍 {{ item.section_1_name }}</span>
              <span class="time-text">{{ item.created_at }}</span>
            </div>
            <div class="row-desc text-truncate">
              事由：{{ item.review_reason }}
            </div>
          </div>
        </div>
      </div>

      <div class="dropdown-footer">
        <button type="button" class="btn-go-all" @click="goToHall">
          进入联合会审大厅 ➔
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPendingReviewNotifications } from '../services/jointReviewApi'

const router = useRouter()
const dropdownOpen = ref(false)
const pendingCount = ref(0)
const pendingItems = ref([])
const loading = ref(false)
const bellWrapRef = ref(null)

let pollTimer = null

async function fetchNotifications() {
  try {
    loading.value = true
    const res = await getPendingReviewNotifications()
    if (res && res.ok) {
      pendingCount.value = res.pending_count || 0
      pendingItems.value = res.pending_items || []
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
    fetchNotifications()
  }
}

function handleClickOutside(e) {
  if (bellWrapRef.value && !bellWrapRef.value.contains(e.target)) {
    dropdownOpen.value = false
  }
}

onMounted(() => {
  fetchNotifications()
  pollTimer = setInterval(fetchNotifications, 45000) // 45 秒轮询一次
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  document.removeEventListener('click', handleClickOutside)
})

function goToHall() {
  dropdownOpen.value = false
  router.push('/projects/insulation_pipe_supply_2026/pages/joint_review_hall')
}

function goToItem(item) {
  dropdownOpen.value = false
  router.push(`/projects/insulation_pipe_supply_2026/pages/joint_review_hall?tab=pending_my_vote&search=${encodeURIComponent(item.order_no)}`)
}
</script>

<style scoped>
.notif-bell-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.notif-bell-btn {
  position: relative;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  color: #f8fafc;
}

.notif-bell-btn:hover,
.notif-bell-btn.is-active {
  background: rgba(255, 255, 255, 0.18);
  border-color: rgba(255, 255, 255, 0.35);
}

.bell-icon {
  font-size: 17px;
}

.notif-badge-pill {
  position: absolute;
  top: -4px;
  right: -5px;
  background: #ef4444;
  color: #ffffff;
  font-size: 10px;
  font-weight: 800;
  line-height: 1;
  padding: 2px 5px;
  border-radius: 10px;
  border: 2px solid #0f172a;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.8);
  animation: pulseBadge 2s infinite ease-in-out;
}

@keyframes pulseBadge {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.notif-dropdown-card {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 340px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  z-index: 1100;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: dropIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes dropIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-header {
  padding: 12px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge-count {
  color: #dc2626;
  font-weight: 800;
}

.btn-refresh {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  padding: 2px 4px;
  border-radius: 4px;
}
.btn-refresh:hover {
  background: #e2e8f0;
}

.dropdown-body {
  max-height: 320px;
  overflow-y: auto;
  padding: 6px;
}

.empty-state {
  padding: 28px 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.empty-icon {
  font-size: 24px;
  color: #10b981;
}

.notif-items-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.notif-row {
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.notif-row:hover {
  border-color: #3b82f6;
  background: #eff6ff;
}

.row-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tag-cat {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  font-weight: 600;
}
.tag-cat.pipe {
  background: #ffedd5;
  color: #ea580c;
}
.tag-cat.fitting {
  background: #e0e7ff;
  color: #4f46e5;
}

.order-no {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}

.row-middle {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
}

.row-desc {
  font-size: 11px;
  color: #475569;
  line-height: 1.3;
}

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-footer {
  padding: 8px 12px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  text-align: center;
}

.btn-go-all {
  width: 100%;
  background: none;
  border: none;
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 0;
  cursor: pointer;
  border-radius: 6px;
}
.btn-go-all:hover {
  background: #eff6ff;
}
</style>
