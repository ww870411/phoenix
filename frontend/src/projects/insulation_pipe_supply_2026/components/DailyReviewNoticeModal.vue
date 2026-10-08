<template>
  <div v-if="visible" class="notice-modal-backdrop" @click.self="handleClose">
    <div class="notice-modal-card">
      <div class="notice-modal-header">
        <div class="header-left">
          <span class="bell-glow-icon">⚖️</span>
          <div>
            <h3>待办多方联合会审提醒</h3>
            <p class="subtitle">您有名下责任主体待表决签署的订单会审，请及时会签办理</p>
          </div>
        </div>
        <button type="button" class="btn-close" @click="handleClose">✕</button>
      </div>

      <div class="notice-modal-body">
        <div class="notice-stat-badge">
          <span>待您表决会签：</span>
          <strong class="count-num">{{ pendingCount }}</strong>
          <span>笔订单</span>
        </div>

        <div class="pending-list-scroll">
          <div v-for="item in pendingItems" :key="item.review_id" class="pending-item-card" @click="goToReview(item)">
            <div class="item-header">
              <span class="category-tag" :class="item.order_category">
                {{ item.category_label }}
              </span>
              <span class="order-no font-mono">{{ item.order_no }}</span>
              <span class="sec-name">📍 {{ item.section_1_name }}</span>
            </div>
            <div class="item-initiator">
              <span>提请人：<strong>{{ item.initiator_name }}</strong> ({{ item.initiator_role }})</span>
              <span class="c-time">{{ item.created_at }}</span>
            </div>
            <div class="item-reason">
              事由：{{ item.review_reason }}
            </div>
          </div>
        </div>
      </div>

      <div class="notice-modal-footer">
        <button type="button" class="btn ghost btn-suppress" @click="suppressToday">
          今日不再弹出
        </button>
        <div class="footer-actions-right">
          <button type="button" class="btn ghost" @click="handleClose">稍后处理</button>
          <button type="button" class="btn primary btn-go-hall" @click="goToHall">
            前往联合会审大厅 ➔
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getPendingReviewNotifications } from '../services/jointReviewApi'

const router = useRouter()
const visible = ref(false)
const pendingCount = ref(0)
const pendingItems = ref([])

const STORAGE_KEY = 'phoenix_review_notice_suppressed_date'

function getTodayString() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function checkPendingReviews() {
  try {
    const todayStr = getTodayString()
    const suppressed = localStorage.getItem(STORAGE_KEY)
    if (suppressed === todayStr) {
      return
    }

    const res = await getPendingReviewNotifications()
    if (res && res.ok && res.pending_count > 0) {
      pendingCount.value = res.pending_count
      pendingItems.value = res.pending_items || []
      visible.value = true
    }
  } catch (e) {
    // 静默失败，不打扰主页面
  }
}

onMounted(() => {
  // 延迟 1.2 秒检测，避开主页面初始渲染
  setTimeout(() => {
    checkPendingReviews()
  }, 1200)
})

function handleClose() {
  visible.value = false
}

function suppressToday() {
  localStorage.setItem(STORAGE_KEY, getTodayString())
  visible.value = false
}

function goToHall() {
  visible.value = false
  router.push('/projects/insulation_pipe_supply_2026/pages/joint_review_hall?tab=pending_my_vote')
}

function goToReview(item) {
  visible.value = false
  router.push(`/projects/insulation_pipe_supply_2026/pages/joint_review_hall?tab=pending_my_vote&search=${encodeURIComponent(item.order_no)}`)
}
</script>

<style scoped>
.notice-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.notice-modal-card {
  background: #ffffff;
  border-radius: 12px;
  width: 100%;
  max-width: 580px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
  overflow: hidden;
  animation: modalIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.94) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.notice-modal-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bell-glow-icon {
  font-size: 26px;
  filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.6));
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #f8fafc;
}

.header-left .subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #94a3b8;
}

.btn-close {
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 18px;
  cursor: pointer;
  border-radius: 4px;
  padding: 4px;
}
.btn-close:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.notice-modal-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 55vh;
  overflow-y: auto;
}

.notice-stat-badge {
  background: #fefce8;
  border: 1px solid #fef08a;
  color: #854d0e;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.count-num {
  font-size: 16px;
  color: #dc2626;
  font-weight: 800;
}

.pending-list-scroll {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pending-item-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pending-item-card:hover {
  border-color: #3b82f6;
  background: #eff6ff;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.category-tag.pipe {
  background: #ffedd5;
  color: #ea580c;
}
.category-tag.fitting {
  background: #e0e7ff;
  color: #4f46e5;
}

.order-no {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.sec-name {
  font-size: 12px;
  color: #64748b;
  margin-left: auto;
}

.item-initiator {
  font-size: 12px;
  color: #475569;
  display: flex;
  justify-content: space-between;
}

.c-time {
  font-size: 11px;
  color: #94a3b8;
}

.item-reason {
  font-size: 12px;
  color: #334155;
  line-height: 1.4;
  background: #ffffff;
  padding: 6px 10px;
  border-radius: 4px;
  border-left: 3px solid #3b82f6;
}

.notice-modal-footer {
  padding: 14px 20px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.btn-suppress {
  font-size: 12px;
  color: #64748b;
}

.footer-actions-right {
  display: flex;
  gap: 10px;
}

.btn-go-hall {
  background: #2563eb;
  color: #fff;
  font-weight: 600;
}
.btn-go-hall:hover {
  background: #1d4ed8;
}
</style>
