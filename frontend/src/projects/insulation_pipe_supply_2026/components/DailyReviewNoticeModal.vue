<template>
  <div v-if="visible" class="notice-modal-backdrop" @click.self="handleClose">
    <div class="notice-modal-card" role="dialog" aria-modal="true">
      <!-- 头部：标题与关闭 -->
      <div class="notice-modal-header">
        <div class="header-left">
          <span class="bell-glow-icon">
            <ScaleBalanceIcon :size="22" color="#f59e0b" />
          </span>
          <div>
            <h3>待办多方联合会审提醒</h3>
            <p class="subtitle">您有名下责任主体待表决签署的订单会审，请及时会签办理</p>
          </div>
        </div>
        <button type="button" class="btn-close" title="稍后处理" @click="handleClose">✕</button>
      </div>

      <!-- 动态提示条：当存在新增提醒打破今日静音时高亮展示 -->
      <div v-if="hasNewlyAdded" class="new-alert-banner">
        <span class="sparkle-icon">✨</span>
        <span>检测到 <strong>{{ newlyAddedCount }}</strong> 笔新提请会审，已连同历史未办一并呈报</span>
      </div>

      <!-- 身体：待办列表 -->
      <div class="notice-modal-body">
        <div class="notice-stat-badge">
          <span>待您代表相关主体会签表决：</span>
          <strong class="count-num">{{ pendingCount }}</strong>
          <span>笔订单</span>
        </div>

        <div class="pending-list-scroll">
          <div
            v-for="item in pendingItems"
            :key="item.review_id"
            class="pending-item-card"
            :class="{ 'is-new-item': isItemNew(item.review_id) }"
            @click="goToReview(item)"
          >
            <div class="item-header">
              <span class="category-tag" :class="item.order_category">
                {{ item.category_label || (item.order_category === 'pipe' ? '保温直管' : '管件/阀门') }}
              </span>
              <span v-if="isItemNew(item.review_id)" class="new-tag">🆕 新提请</span>
              <span class="order-no font-mono">{{ item.order_no }}</span>
              <span class="sec-name">📍 {{ item.section_1_name }}</span>
            </div>
            <div class="item-initiator">
              <span>提请人：<strong>{{ item.initiator_name || '经办人' }}</strong> ({{ item.initiator_role || '责任主体' }})</span>
              <span class="c-time">{{ item.created_at }}</span>
            </div>
            <div class="item-reason">
              <strong>事由：</strong>{{ item.review_reason || '单据数据修正提请' }}
            </div>
            <!-- 提请更正内容卡片：清晰显示提请修改什么内容 -->
            <div class="item-patch-box" v-if="getItemDiffs(item).length > 0">
              <div class="patch-header">
                <span class="patch-title">📝 提请更正内容：</span>
              </div>
              <div class="patch-diff-list">
                <div v-for="(diff, dIdx) in getItemDiffs(item)" :key="dIdx" class="patch-diff-row">
                  <span class="diff-label">【{{ diff.label }}】</span>
                  <span class="diff-before" :title="'原始记录值：' + diff.before">{{ diff.before }}</span>
                  <span class="diff-arrow">➔</span>
                  <span class="diff-after" :title="'提请更正为：' + diff.after">{{ diff.after }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部：今日不再提醒与快捷跳转 -->
      <div class="notice-modal-footer">
        <button
          type="button"
          class="btn ghost btn-suppress"
          title="今天不再弹出（若该主体有新增会审仍将连带唤醒）"
          @click="suppressToday"
        >
          今日不再提醒
        </button>
        <div class="footer-actions-right">
          <button type="button" class="btn ghost btn-later" @click="handleClose">稍后处理</button>
          <button type="button" class="btn primary btn-go-hall" @click="goToHall">
            前往联合会审大厅 ➔
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { getPendingReviewNotifications } from '../services/jointReviewApi'
import ScaleBalanceIcon from './ScaleBalanceIcon.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const visible = ref(false)
const pendingCount = ref(0)
const pendingItems = ref([])
const allPendingIds = ref([])
const hasNewlyAdded = ref(false)
const newlyAddedCount = ref(0)
const newReviewIdSet = ref(new Set())

let pollTimer = null
let isPolling = false

function getTodayString() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function getStorageKey() {
  const username = auth.user?.username || 'common'
  return `phoenix_review_notice_suppress_${username}`
}

function isItemNew(reviewId) {
  return newReviewIdSet.value.has(Number(reviewId))
}

function getItemDiffs(item) {
  if (Array.isArray(item?.diff_list) && item.diff_list.length > 0) {
    return item.diff_list
  }
  const patch = item?.proposed_patch || {}
  const snapshot = item?.original_snapshot || {}
  const list = []
  const fieldLabels = {
    shipped_qty: '发货数量',
    vehicle_plate_no: '送货车牌号',
    pipe_model_id: '规格型号',
    fitting_type: '管件大类',
    model_spec: '规格型号',
    unit: '单位',
    ship_contact_name: '随车联系人',
    ship_contact_phone: '联系电话',
    ship_remark: '发货备注',
  }
  for (const [k, label] of Object.entries(fieldLabels)) {
    if (k in patch) {
      let bVal = snapshot[k] != null ? String(snapshot[k]) : '—'
      let aVal = patch[k] != null ? String(patch[k]) : '—'
      if (k === 'shipped_qty') {
        const u = snapshot.unit || (item.order_category === 'pipe' ? '根/米' : '件')
        bVal = `${bVal} ${u}`.trim()
        aVal = `${aVal} ${u}`.trim()
      }
      list.push({ key: k, label, before: bVal, after: aVal })
    }
  }
  if (Array.isArray(patch.items) && patch.items.length > 0) {
    const total = Array.isArray(snapshot._review_rows)
      ? snapshot._review_rows.length
      : Array.isArray(snapshot.items)
      ? snapshot.items.length
      : 0
    list.push({
      key: 'items',
      label: '车载管件明细',
      before: total > 0 ? `原车次共 ${total} 项` : '原明细记录',
      after: `更正其中 ${patch.items.length} 项规格/数量`,
    })
  }
  return list
}

/**
 * 核心检查函数：
 * 1. 调接口获取当前名下未处理会审；
 * 2. 对比今日已抑制的 ID 集合；
 * 3. 若全已抑制，保持静默；若有任何新增单据，打破静音并新老一并弹出！
 */
async function checkPendingReviews() {
  if (isPolling) return
  // 未登录或当前处于登录页，不弹出
  if (!auth.isLoggedIn && !auth.user && !auth.token) {
    visible.value = false
    return
  }
  if (route && (route.path === '/login' || route.path.startsWith('/login'))) {
    visible.value = false
    return
  }

  isPolling = true
  try {
    const todayStr = getTodayString()
    const res = await getPendingReviewNotifications()
    if (!res || !res.ok || !res.pending_count || res.pending_count <= 0) {
      pendingCount.value = 0
      pendingItems.value = []
      allPendingIds.value = []
      newReviewIdSet.value.clear()
      hasNewlyAdded.value = false
      newlyAddedCount.value = 0
      return
    }

    pendingCount.value = res.pending_count
    pendingItems.value = res.pending_items || []

    const currentIds = (Array.isArray(res.all_pending_review_ids) && res.all_pending_review_ids.length > 0)
      ? res.all_pending_review_ids.map(Number)
      : (res.pending_items || []).map(it => Number(it.review_id))
    allPendingIds.value = currentIds

    // 读取本地存储中的抑制快照
    const rawSuppressed = localStorage.getItem(getStorageKey())
    let suppressedData = null
    if (rawSuppressed) {
      try {
        suppressedData = JSON.parse(rawSuppressed)
      } catch (e) {
        // 兼容旧版纯字符串格式
        suppressedData = { date: rawSuppressed, suppressedReviewIds: [] }
      }
    }

    const isTodaySuppressed = Boolean(suppressedData && suppressedData.date === todayStr)

    if (isTodaySuppressed) {
      const suppressedIds = Array.isArray(suppressedData.suppressedReviewIds)
        ? suppressedData.suppressedReviewIds.map(Number)
        : []

      // 计算当前待办中哪些是新增的（不在已抑制集合中的单据）
      const freshlyAddedIds = currentIds.filter(id => !suppressedIds.includes(id))

      if (freshlyAddedIds.length === 0) {
        // 今日已点不再提醒，且没有新增单据 -> 严格保持静默，不弹出打扰
        return
      }

      // 存在新增单据！打破静音，标记新增 ID 并一并重新弹出
      hasNewlyAdded.value = true
      newlyAddedCount.value = freshlyAddedIds.length
      newReviewIdSet.value = new Set(freshlyAddedIds)
      visible.value = true
    } else {
      // 今日未抑制（或跨天首次进入）-> 正常弹出全量待办
      hasNewlyAdded.value = false
      newlyAddedCount.value = 0
      newReviewIdSet.value.clear()
      visible.value = true
    }
  } catch (err) {
    // 静默兜底，避免影响页面其他操作
  } finally {
    isPolling = false
  }
}

function handleClose() {
  visible.value = false
}

function suppressToday() {
  try {
    const currentIds = (allPendingIds.value && allPendingIds.value.length > 0)
      ? allPendingIds.value
      : pendingItems.value.map(it => Number(it.review_id))

    const payload = {
      date: getTodayString(),
      suppressedReviewIds: currentIds,
    }
    localStorage.setItem(getStorageKey(), JSON.stringify(payload))
  } catch (e) {
    console.warn('缓存会审抑制状态失败:', e)
  }
  visible.value = false
}

function goToHall() {
  visible.value = false
  router.push('/projects/insulation_pipe_supply_2026/pages/joint_review_hall?tab=pending_my_vote')
}

function goToReview(item) {
  visible.value = false
  const targetId = item.review_id || ''
  const searchKw = item.order_no || ''
  if (targetId) {
    router.push(`/projects/insulation_pipe_supply_2026/pages/joint_review_hall?tab=pending_my_vote&review_id=${targetId}&search=${encodeURIComponent(searchKw)}`)
  } else {
    router.push(`/projects/insulation_pipe_supply_2026/pages/joint_review_hall?tab=pending_my_vote&search=${encodeURIComponent(searchKw)}`)
  }
}

// 监听路由切换，若用户在应用内部跳转也及时检查
watch(
  () => route.path,
  () => {
    // 延迟少许，等待页面路由切换完成
    setTimeout(() => {
      checkPendingReviews()
    }, 600)
  }
)

onMounted(() => {
  // 首次挂载延迟 1.5 秒执行，避开主页首屏并发请求
  setTimeout(() => {
    checkPendingReviews()
  }, 1500)

  // 设置 45 秒轻量心跳定时器（全页面常驻轮询）
  pollTimer = setInterval(() => {
    checkPendingReviews()
  }, 45000)

  // 当浏览器窗口重新获得焦点（例如切回标签页）时立即检测一次
  if (typeof window !== 'undefined') {
    window.addEventListener('focus', checkPendingReviews)
  }
})

onBeforeUnmount(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('focus', checkPendingReviews)
  }
})
</script>

<style scoped>
.notice-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 2500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.notice-modal-card {
  background: #ffffff;
  border-radius: 14px;
  width: 100%;
  max-width: 600px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.45);
  overflow: hidden;
  animation: modalIn 0.24s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(12px);
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.65));
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
  border-radius: 6px;
  padding: 4px 8px;
  transition: all 0.15s ease;
}
.btn-close:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
}

.new-alert-banner {
  background: linear-gradient(90deg, #dbeafe 0%, #eff6ff 100%);
  border-bottom: 1px solid #bfdbfe;
  color: #1e40af;
  padding: 8px 20px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}
.new-alert-banner strong {
  color: #2563eb;
  font-weight: 700;
}
.sparkle-icon {
  font-size: 14px;
}

.notice-modal-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 58vh;
  overflow-y: auto;
}

.notice-stat-badge {
  background: #fefce8;
  border: 1px solid #fef08a;
  color: #854d0e;
  padding: 8px 12px;
  border-radius: 8px;
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
  border-radius: 10px;
  padding: 12px 14px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.18s ease;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}
.pending-item-card:hover {
  border-color: #3b82f6;
  background: #eff6ff;
  box-shadow: 0 4px 10px -2px rgba(59, 130, 246, 0.12);
  transform: translateY(-1px);
}
.pending-item-card.is-new-item {
  border-color: #93c5fd;
  background: #f0f7ff;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-tag {
  font-size: 11px;
  padding: 2px 7px;
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

.new-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: #fecaca;
  color: #dc2626;
  border-radius: 4px;
  font-weight: 700;
  animation: pulse 1.6s infinite ease-in-out;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
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
  line-height: 1.45;
  background: #ffffff;
  padding: 7px 10px;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
  word-break: break-all;
}

.item-patch-box {
  background: #fffbeb;
  border: 1px solid #fef08a;
  border-left: 3px solid #eab308;
  border-radius: 6px;
  padding: 7px 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.patch-header {
  display: flex;
  align-items: center;
}

.patch-title {
  font-size: 11.5px;
  font-weight: 700;
  color: #854d0e;
}

.patch-diff-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.patch-diff-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  line-height: 1.4;
}

.diff-label {
  font-weight: 600;
  color: #713f12;
  white-space: nowrap;
}

.diff-before {
  color: #b91c1c;
  background: #fee2e2;
  padding: 1px 6px;
  border-radius: 4px;
  text-decoration: line-through;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11.5px;
  white-space: nowrap;
}

.diff-arrow {
  color: #d97706;
  font-weight: 800;
  font-size: 12px;
}

.diff-after {
  color: #15803d;
  background: #dcfce7;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11.5px;
  white-space: nowrap;
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
  background: transparent;
  border: 1px solid #cbd5e1;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-suppress:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.footer-actions-right {
  display: flex;
  gap: 10px;
}

.btn-later {
  font-size: 13px;
  color: #475569;
  background: transparent;
  border: 1px solid #cbd5e1;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-later:hover {
  background: #f1f5f9;
}

.btn-go-hall {
  background: #2563eb;
  color: #fff;
  font-weight: 600;
  border: none;
  padding: 7px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
  transition: all 0.15s ease;
}
.btn-go-hall:hover {
  background: #1d4ed8;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.35);
}
</style>
