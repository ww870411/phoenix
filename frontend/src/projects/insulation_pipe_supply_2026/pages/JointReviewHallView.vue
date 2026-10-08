<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <!-- 标准全局面包屑导航 -->
      <Breadcrumbs :items="breadcrumbItems" />

      <!-- 页面顶栏 -->
      <header class="topbar premium-topbar">
        <div class="topbar-title-block">
          <div class="title-with-badge">
            <span class="title-icon">⚖️</span>
            <h2>多方联合会审大厅 (Joint Review Hall)</h2>
            <span class="live-status-pill">共识会签机制</span>
          </div>
          <p class="topbar-desc">
            全生命周期订单信息协同校核中心。在待到货、待接收、待入库环节，任何正当修正诉求通过圆桌多方会审、全票同意后自动更正生效，共识免责、全程留痕。
          </p>
        </div>
        <div class="topbar-actions">
          <button type="button" class="btn primary btn-initiate-guide" @click="howToInitiateModalVisible = true">
            <span class="btn-icon">➕</span>
            <span>如何提请会审 / 定位订单</span>
          </button>
          <button type="button" class="btn ghost btn-back" @click="goProjectPages">
            ⬅️ 返回功能页
          </button>
          <button type="button" class="btn secondary" @click="loadReviews" :disabled="loading">
            🔄 {{ loading ? '同步中...' : '刷新会审列表' }}
          </button>
        </div>
      </header>

      <!-- 核心统计大盘 KPI -->
      <section class="kpi-banner-grid">
        <div class="kpi-card" :class="{ 'has-action': myPendingCount > 0 }" @click="switchTab('pending_my_vote')">
          <span class="kpi-label">⌛ 待我联审表决</span>
          <span class="kpi-val text-red">
            {{ myPendingCount }} <small>笔</small>
            <span v-if="myPendingCount > 0" class="kpi-alert-pulse">需会签</span>
          </span>
        </div>
        <div class="kpi-card" @click="switchTab('my_initiated')">
          <span class="kpi-label">📋 我发起的会审</span>
          <span class="kpi-val text-blue">{{ myInitiatedCount }} <small>笔</small></span>
        </div>
        <div class="kpi-card" @click="switchTab('history')">
          <span class="kpi-label">✓ 已全票通过更正</span>
          <span class="kpi-val text-emerald">{{ approvedCount }} <small>笔</small></span>
        </div>
        <div class="kpi-card" @click="switchTab('all')">
          <span class="kpi-label">🌐 全网会审总单数</span>
          <span class="kpi-val text-slate">{{ totalCount }} <small>笔</small></span>
        </div>
      </section>

      <!-- 分类 Tab 切换 -->
      <div class="hall-tabs-bar">
        <button
          type="button"
          class="hall-tab-btn"
          :class="{ active: currentTab === 'pending_my_vote' }"
          @click="switchTab('pending_my_vote')"
        >
          <span>🔥 待我联审</span>
          <span v-if="myPendingCount > 0" class="tab-badge-pill">{{ myPendingCount }}</span>
        </button>
        <button
          type="button"
          class="hall-tab-btn"
          :class="{ active: currentTab === 'my_initiated' }"
          @click="switchTab('my_initiated')"
        >
          <span>📋 我发起的会审</span>
        </button>
        <button
          type="button"
          class="hall-tab-btn"
          :class="{ active: currentTab === 'history' }"
          @click="switchTab('history')"
        >
          <span>📚 历史会审档案</span>
        </button>
        <button
          type="button"
          class="hall-tab-btn"
          :class="{ active: currentTab === 'all' }"
          @click="switchTab('all')"
        >
          <span>🌐 全网会审台账</span>
        </button>
      </div>

      <!-- 搜索与筛选工具栏 -->
      <section class="card filter-card">
        <div class="filter-controls-row">
          <div class="filter-field">
            <span>物料类型</span>
            <select v-model="filterCategory" @change="handleFilterChange">
              <option value="">全部物料</option>
              <option value="pipe">🔥 保温直管</option>
              <option value="fitting">🔩 管件与阀门</option>
            </select>
          </div>

          <div class="filter-field" v-if="currentTab === 'all'">
            <span>会审状态</span>
            <select v-model="filterStatus" @change="handleFilterChange">
              <option value="">全部状态</option>
              <option value="voting">🟡 会审中</option>
              <option value="approved">🟢 已全票通过</option>
              <option value="rejected">🔴 存在异议/已驳回</option>
              <option value="cancelled">⚪ 已撤销</option>
            </select>
          </div>

          <div class="filter-field search-field">
            <span>全局搜索</span>
            <input
              type="text"
              v-model="searchKeyword"
              placeholder="搜索会审单号 / 业务订单号 / 事由 / 经办人..."
              @keyup.enter="handleFilterChange"
            />
          </div>

          <button type="button" class="btn primary btn-query" @click="handleFilterChange">
            🔍 筛选
          </button>
          <button type="button" class="btn ghost btn-reset" @click="resetFilters">
            ↺ 重置
          </button>
        </div>
      </section>

      <!-- 会审单据流列表 -->
      <section class="reviews-container">
        <div v-if="loading" class="loading-state">
          <span class="loading-spinner">⌛</span>
          <span>正在检索联合会审档案...</span>
        </div>

        <div v-else-if="reviewItems.length === 0" class="empty-hall-card">
          <span class="empty-icon">📂</span>
          <h3>暂无符合条件的联合会审记录</h3>
          <p>
            {{ currentTab === 'pending_my_vote' ? '太棒了！当前没有任何需要您参与表决的会审订单。' : '在各工作台待办单据中，可针对有错漏争议的单据提请联合会审。' }}
          </p>
        </div>

        <div v-else class="review-cards-list">
          <div
            v-for="rev in reviewItems"
            :key="rev.id"
            class="review-item-card"
            :class="[`status-${rev.review_status}`, { 'needs-me': rev.needs_my_vote }]"
          >
            <!-- 卡片顶栏 -->
            <div class="card-header-row">
              <div class="header-left">
                <span class="cat-pill" :class="rev.order_category">
                  {{ rev.order_category === 'pipe' ? '🔥 保温直管' : '🔩 管件阀门' }}
                </span>
                <span class="review-no font-mono">{{ rev.review_no }}</span>
                <span class="order-ref font-mono">订单号: {{ rev.order_no }}</span>
              </div>
              <div class="header-right">
                <span class="status-badge" :class="`badge-${rev.review_status}`">
                  {{ formatReviewStatus(rev) }}
                </span>
              </div>
            </div>

            <!-- 主体与元数据条 -->
            <div class="meta-strip">
              <span class="meta-item">📍 需求标段：<strong>{{ rev.section_1_name }}</strong></span>
              <span class="meta-item">🏭 供货厂家：<strong>{{ rev.supply_entity_name }}</strong></span>
              <span class="meta-item">👤 提请人：<strong>{{ rev.initiator_name }}</strong> ({{ rev.initiator_role }})</span>
              <span class="meta-item time">🕒 提请时间：{{ rev.created_at }}</span>
            </div>

            <!-- 提请事由说明 -->
            <div class="reason-quote-box">
              <div class="quote-title">📢 提请校核事由：</div>
              <div class="quote-content">{{ rev.review_reason }}</div>
            </div>

            <!-- 拟更正内容对比面板 (Diff Panel) -->
            <div class="diff-block">
              <div class="diff-title">📝 拟更正内容比对：</div>
              <div class="diff-items-grid">
                <template v-for="(val, key) in rev.proposed_patch" :key="key">
                  <!-- 车载订单明细列表 -->
                  <div v-if="key === 'items' && Array.isArray(val)" class="diff-items-full-block">
                    <div class="diff-items-header-bar">
                      <span class="prop-name">📦 车载各订单明细调整 (共 {{ val.length }} 项)：</span>
                    </div>
                    <div class="diff-items-mini-table-wrap">
                      <table class="diff-items-mini-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th>单号</th>
                            <th>拟更正品类</th>
                            <th>拟更正规格型号</th>
                            <th>更正发货量</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(it, itIdx) in val" :key="it.id || itIdx">
                            <td>{{ itIdx + 1 }}</td>
                            <td class="font-mono">{{ it.order_no || '—' }}</td>
                            <td>{{ it.fitting_type || '—' }}</td>
                            <td>{{ it.model_spec || '—' }}</td>
                            <td class="font-mono font-bold" style="color: #ea580c;">
                              {{ it.shipped_qty }} {{ it.unit || '件' }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <!-- 常规单值更正 -->
                  <div v-else class="diff-grid-row">
                    <span class="prop-name">{{ formatPatchKey(key) }}：</span>
                    <span class="prop-old" title="原订单数据">{{ formatSnapshotVal(rev.original_snapshot, key) }}</span>
                    <span class="prop-arrow">➔</span>
                    <span class="prop-new" title="更正目标值">{{ val }}</span>
                  </div>
                </template>
              </div>
            </div>

            <!-- 现场凭据图片预览 -->
            <div v-if="rev.attachments && rev.attachments.length" class="attachments-strip">
              <span class="att-title">📷 现场照片凭据：</span>
              <div class="att-thumbs-row">
                <img
                  v-for="(att, idx) in rev.attachments"
                  :key="idx"
                  :src="att.url"
                  :alt="att.name"
                  class="att-img"
                  @click="openImageViewer(att.url)"
                  title="点击查看高清大图"
                />
              </div>
            </div>

            <!-- 多方会签流转矩阵 (Consensus Pipeline) -->
            <div class="pipeline-section">
              <div class="pipeline-title">
                <span>👥 责任主体联审表决进度 (全票同意即生效)：</span>
                <span class="pipeline-ratio font-mono">
                  已同意 {{ (rev.approved_entities || []).length }} / {{ (rev.required_entities || []).length }} 方
                </span>
              </div>

              <div class="entities-vote-list">
                <div
                  v-for="ent in rev.required_entities"
                  :key="`${ent.entity_type}_${ent.entity_id}`"
                  class="entity-vote-card"
                  :class="getEntityVoteClass(rev, ent)"
                >
                  <div class="ent-info">
                    <span class="ent-role-tag">{{ ent.role_desc || ent.entity_type }}</span>
                    <strong class="ent-name">{{ ent.entity_name }}</strong>
                  </div>
                  <div class="vote-result">
                    <template v-if="hasEntityApproved(rev, ent)">
                      <span class="vote-tag approved">✓ 已同意核准</span>
                    </template>
                    <template v-else-if="hasEntityRejected(rev, ent)">
                      <span class="vote-tag rejected">✕ 提出异议</span>
                      <p class="reject-reason-tip" v-if="getEntityRejectOpinion(rev, ent)">
                        理由: {{ getEntityRejectOpinion(rev, ent) }}
                      </p>
                    </template>
                    <template v-else>
                      <span class="vote-tag pending">⌛ 待表决</span>
                    </template>
                  </div>
                </div>
              </div>
            </div>

            <!-- 决议摘要（若已办结） -->
            <div v-if="rev.resolution_summary" class="resolution-summary-box">
              <span class="res-title">🏁 最终决议记录：</span>
              <span class="res-text">{{ rev.resolution_summary }}</span>
            </div>

            <!-- 操作动作工具栏 -->
            <div class="card-actions-bar">
              <!-- 待我表决操作组 -->
              <div v-if="rev.needs_my_vote" class="action-group my-vote-group">
                <button
                  type="button"
                  class="btn primary btn-approve"
                  @click="handleVoteClick(rev, 'approve')"
                  :disabled="actionLoading"
                >
                  ✓ 同意更正
                </button>
                <button
                  type="button"
                  class="btn danger-outline btn-reject"
                  @click="openRejectModal(rev)"
                  :disabled="actionLoading"
                >
                  ✕ 提出异议
                </button>
              </div>

              <div v-else-if="rev.my_voted" class="my-voted-hint">
                <span class="hint-icon">✓</span>
                <span>您名下主体已表决：<strong>{{ rev.my_vote_decision === 'approve' ? '已同意' : '已提异议' }}</strong></span>
              </div>

              <div class="actions-right">
                <!-- 发起人撤回 -->
                <button
                  v-if="rev.can_cancel"
                  type="button"
                  class="btn ghost btn-cancel-rev"
                  @click="handleCancelClick(rev)"
                  :disabled="actionLoading"
                >
                  撤回会审
                </button>

                <!-- 超级管理员仲裁 -->
                <button
                  v-if="rev.can_arbitrate"
                  type="button"
                  class="btn warning btn-arbitrate"
                  @click="openArbitrateModal(rev)"
                  :disabled="actionLoading"
                >
                  🛡️ 管理员终局裁决
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 分页栏 -->
        <div v-if="totalCount > pageSize" class="pagination-bar">
          <button
            type="button"
            class="btn ghost"
            :disabled="currentPage <= 1 || loading"
            @click="changePage(currentPage - 1)"
          >
            上一页
          </button>
          <span class="page-info">第 {{ currentPage }} 页 / 共 {{ totalPages }} 页</span>
          <button
            type="button"
            class="btn ghost"
            :disabled="currentPage >= totalPages || loading"
            @click="changePage(currentPage + 1)"
          >
            下一页
          </button>
        </div>
      </section>
    </main>

    <!-- 弹窗 1：填写异议理由弹窗 -->
    <div v-if="rejectModalVisible" class="modal-backdrop" @click.self="rejectModalVisible = false">
      <div class="modal-dialog">
        <div class="modal-head">
          <h4>提出不同意异议</h4>
          <button type="button" class="btn-x" @click="rejectModalVisible = false">✕</button>
        </div>
        <div class="modal-content">
          <p class="modal-tip">
            选择不同意时，该会审将保持挂起状态，请详细说明您核对出的事实、不同意的理由或现场实际情况：
          </p>
          <textarea
            v-model="rejectReasonInput"
            rows="4"
            class="modal-textarea"
            placeholder="例：我方经核实出厂磅单与随车GPS记录，发货数量确为 20 根无误，现场吊装卸车可能存在分段堆放未清点齐全，不同意直接扣减发货量，建议双方现场再次复点。"
          ></textarea>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn ghost" @click="rejectModalVisible = false">取消</button>
          <button type="button" class="btn danger" @click="submitRejectVote" :disabled="actionLoading">
            确认提交异议
          </button>
        </div>
      </div>
    </div>

    <!-- 弹窗 2：超级管理员终局裁决弹窗 -->
    <div v-if="arbitrateModalVisible" class="modal-backdrop" @click.self="arbitrateModalVisible = false">
      <div class="modal-dialog">
        <div class="modal-head">
          <h4>🛡️ 管理员终局裁决仲裁 (特权通道)</h4>
          <button type="button" class="btn-x" @click="arbitrateModalVisible = false">✕</button>
        </div>
        <div class="modal-content">
          <p class="modal-tip">
            注意：作为系统超级管理员，您的裁决将具有一锤定音的终局法律效力，直接打破基层死锁：
          </p>
          <div class="arbitrate-choice-row">
            <label class="choice-item">
              <input type="radio" value="force_approve" v-model="arbitrateDecision" />
              <span><strong>强制通过生效</strong> (执行拟更正数据，闭环会审)</span>
            </label>
            <label class="choice-item">
              <input type="radio" value="force_reject" v-model="arbitrateDecision" />
              <span><strong>强制终止驳回</strong> (驳回修正诉求，恢复原单据)</span>
            </label>
          </div>
          <div class="modal-field">
            <label>裁决理由依据说明 *</label>
            <textarea
              v-model="arbitrateReasonInput"
              rows="3"
              class="modal-textarea"
              placeholder="请录入集团最终核实意见或仲裁依据..."
            ></textarea>
          </div>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn ghost" @click="arbitrateModalVisible = false">取消</button>
          <button type="button" class="btn primary" @click="submitArbitration" :disabled="actionLoading">
            执行终局裁决
          </button>
        </div>
      </div>
    </div>

    <!-- 弹窗 3：图片大图浏览器 -->
    <div v-if="previewImageUrl" class="image-viewer-backdrop" @click="previewImageUrl = null">
      <div class="image-viewer-container">
        <img :src="previewImageUrl" alt="凭据大图" class="enlarged-img" />
        <button type="button" class="btn-close-viewer" @click="previewImageUrl = null">✕</button>
      </div>
    </div>

    <!-- 弹窗 4：如何提请会审 / 定位订单指引弹窗 -->
    <div v-if="howToInitiateModalVisible" class="modal-backdrop" @click.self="howToInitiateModalVisible = false">
      <div class="modal-dialog guide-dialog">
        <div class="modal-head">
          <div class="head-title-wrap">
            <span class="guide-icon">⚖️</span>
            <h4>如何提请多方联合会审？</h4>
          </div>
          <button type="button" class="btn-x" @click="howToInitiateModalVisible = false">✕</button>
        </div>
        <div class="modal-content guide-content">
          <p class="guide-intro">
            为保障单据流转的严肃性与责任主体溯源，联合会审由当前<strong>待办节点责任主体</strong>在各自业务工作台中针对具体待办单据提起：
          </p>
          <div class="guide-steps-grid">
            <div class="guide-step-card">
              <div class="step-badge">场景 1 · 待到货环节</div>
              <h5>🚚 现场主管提请</h5>
              <p>供方已发货，现场核对实物或随车小票发现规格、数量或车牌有误。</p>
              <div class="step-action">
                <span>位置：需求侧工作台 ➔ 物流台账 / 管件卡片</span>
                <div class="action-btn-group">
                  <button type="button" class="btn primary btn-xs" @click="goToDemandWorkbench('pipe', 'logistics')">
                    直达直管物流 ➔
                  </button>
                  <button type="button" class="btn ghost btn-xs" @click="goToDemandWorkbench('fitting', 'fitting')">
                    直达管件发货 ➔
                  </button>
                </div>
              </div>
            </div>

            <div class="guide-step-card">
              <div class="step-badge">场景 2 · 待接收环节</div>
              <h5>👷 施工单位提请</h5>
              <p>现场已确认到货，施工承包队领用/进场时发现实物与单据规格不符。</p>
              <div class="step-action">
                <span>位置：需求侧工作台 ➔ 物流台账 / 管件卡片</span>
                <div class="action-btn-group">
                  <button type="button" class="btn primary btn-xs" @click="goToDemandWorkbench('pipe', 'logistics')">
                    直达直管接收 ➔
                  </button>
                  <button type="button" class="btn ghost btn-xs" @click="goToDemandWorkbench('fitting', 'fitting')">
                    直达管件接收 ➔
                  </button>
                </div>
              </div>
            </div>

            <div class="guide-step-card">
              <div class="step-badge">场景 3 · 待入库环节</div>
              <h5>🏢 库管人员提请</h5>
              <p>施工已确认接收，库管员在办结入库手续时发现台账有错漏。</p>
              <div class="step-action">
                <span>位置：库管员工作台 ➔ 库管台账</span>
                <div class="action-btn-group">
                  <button type="button" class="btn primary btn-xs" @click="goToWarehouseWorkbench('pipe')">
                    直达保温管台账 ➔
                  </button>
                  <button type="button" class="btn ghost btn-xs" @click="goToWarehouseWorkbench('fitting', 'pending_warehouse')">
                    直达管件待入库 ➔
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="guide-note-box">
            💡 <strong>操作提示</strong>：在对应工作台中找到该笔待办订单，点击右侧橙黄色的 <strong>【⚖️ 提请会审】</strong> 按钮，录入拟修改的数据（数量/型号/车牌等）、原因并上传现场照片。提请后单据将自动锁定，相关前序主体会收到会签通知并进入大厅表决！
          </div>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn secondary" @click="howToInitiateModalVisible = false">了解并关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import {
  adminArbitrateJointReview,
  cancelJointReview,
  listJointReviews,
  voteJointReview,
} from '../services/jointReviewApi'

const route = useRoute()
const router = useRouter()

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '2026年度保温管、管件物流链管理系统', to: '/projects/insulation_pipe_supply_2026/pages' },
  { label: '⚖️ 联合会审大厅', to: null },
])

const currentTab = ref('pending_my_vote')
const filterCategory = ref('')
const filterStatus = ref('')
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const loading = ref(false)
const actionLoading = ref(false)
const reviewItems = ref([])
const totalCount = ref(0)

// 统计值
const myPendingCount = ref(0)
const myInitiatedCount = ref(0)
const approvedCount = ref(0)

// 弹窗状态
const rejectModalVisible = ref(false)
const rejectingReview = ref(null)
const rejectReasonInput = ref('')

const arbitrateModalVisible = ref(false)
const arbitratingReview = ref(null)
const arbitrateDecision = ref('force_approve')
const arbitrateReasonInput = ref('')

const previewImageUrl = ref(null)
const howToInitiateModalVisible = ref(false)

function goToDemandWorkbench(category = 'pipe', tab = 'logistics') {
  howToInitiateModalVisible.value = false
  router.push({
    path: '/projects/insulation_pipe_supply_2026/pages/demand_management',
    query: { category, tab },
  })
}

function goToWarehouseWorkbench(tab = 'pipe', sub = 'all') {
  howToInitiateModalVisible.value = false
  const query = { tab }
  if (sub && sub !== 'all') {
    query.sub = sub
  }
  router.push({
    path: '/projects/insulation_pipe_supply_2026/pages/warehouse_management',
    query,
  })
}

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value) || 1)

// 读取 URL 参数以自适应定位
onMounted(() => {
  if (typeof document !== 'undefined') {
    document.title = '⚖️ 联合会审大厅 - 保温管物流链管理系统'
  }
  if (route.query.tab) {
    currentTab.value = String(route.query.tab)
  }
  if (route.query.search) {
    searchKeyword.value = String(route.query.search)
  }
  loadReviews()
  loadStats()
})

watch(
  () => route.query,
  (newQ) => {
    if (newQ.tab && newQ.tab !== currentTab.value) {
      currentTab.value = String(newQ.tab)
      loadReviews()
    }
  }
)

async function loadStats() {
  try {
    // 异步拉取各 Tab 的统计概况
    const [pRes, mRes, aRes] = await Promise.all([
      listJointReviews({ tab: 'pending_my_vote', limit: 1 }),
      listJointReviews({ tab: 'my_initiated', limit: 1 }),
      listJointReviews({ review_status: 'approved', limit: 1 }),
    ])
    if (pRes && pRes.ok) myPendingCount.value = pRes.total || 0
    if (mRes && mRes.ok) myInitiatedCount.value = mRes.total || 0
    if (aRes && aRes.ok) approvedCount.value = aRes.total || 0
  } catch (e) {}
}

async function loadReviews() {
  loading.value = true
  try {
    const res = await listJointReviews({
      tab: currentTab.value,
      order_category: filterCategory.value || undefined,
      review_status: filterStatus.value || undefined,
      search: searchKeyword.value ? searchKeyword.value.trim() : undefined,
      page: currentPage.value,
      limit: pageSize.value,
    })
    if (res && res.ok) {
      reviewItems.value = res.items || []
      totalCount.value = res.total || 0
      if (currentTab.value === 'pending_my_vote') {
        myPendingCount.value = res.total || 0
      }
    }
  } catch (err) {
    alert(err.message || '加载联合会审列表失败')
  } finally {
    loading.value = false
  }
}

function switchTab(tabKey) {
  if (currentTab.value === tabKey) return
  currentTab.value = tabKey
  currentPage.value = 1
  router.replace({
    path: route.path,
    query: { ...route.query, tab: tabKey },
  })
  loadReviews()
}

function handleFilterChange() {
  currentPage.value = 1
  loadReviews()
}

function resetFilters() {
  filterCategory.value = ''
  filterStatus.value = ''
  searchKeyword.value = ''
  currentPage.value = 1
  loadReviews()
}

function changePage(page) {
  currentPage.value = page
  loadReviews()
}

function formatReviewStatus(rev) {
  const st = rev.review_status
  if (st === 'voting') {
    const appCount = (rev.approved_entities || []).length
    const reqCount = (rev.required_entities || []).length
    const rejCount = (rev.rejected_entities || []).length
    if (rejCount > 0) return `🔴 存在异议挂起 (${appCount}/${reqCount})`
    return `🟡 会审中 (${appCount}/${reqCount} 已同意)`
  }
  if (st === 'approved') return '🟢 全票通过已生效'
  if (st === 'rejected') return '🔴 终局驳回'
  if (st === 'cancelled') return '⚪ 已撤销'
  return st
}

function formatPatchKey(key) {
  const map = {
    shipped_qty: '发货数量',
    pipe_model_id: '保温管规格型号',
    fitting_type: '管件大类',
    model_spec: '管件规格',
    unit: '单位',
    vehicle_plate_no: '送货车牌号',
    items: '车载订单明细更正',
    ship_contact_name: '随车联系人',
    ship_contact_phone: '联系电话',
    ship_remark: '发货备注',
  }
  return map[key] || key
}

function formatSnapshotVal(snapshot, key) {
  if (!snapshot) return '—'
  const v = snapshot[key]
  return v !== undefined && v !== null && v !== '' ? v : '无'
}

function hasEntityApproved(rev, ent) {
  const list = rev.approved_entities || []
  return list.some((e) => e.entity_type === ent.entity_type && e.entity_id === ent.entity_id)
}

function hasEntityRejected(rev, ent) {
  const list = rev.rejected_entities || []
  return list.some((e) => e.entity_type === ent.entity_type && e.entity_id === ent.entity_id)
}

function getEntityRejectOpinion(rev, ent) {
  const list = rev.rejected_entities || []
  const item = list.find((e) => e.entity_type === ent.entity_type && e.entity_id === ent.entity_id)
  return item ? item.opinion : ''
}

function getEntityVoteClass(rev, ent) {
  if (hasEntityApproved(rev, ent)) return 'is-approved'
  if (hasEntityRejected(rev, ent)) return 'is-rejected'
  return 'is-pending'
}

async function handleVoteClick(rev, decision) {
  if (!confirm(`确定代表您名下责任主体对单据 [${rev.order_no}] 签署【同意更正】意见吗？`)) {
    return
  }
  actionLoading.value = true
  try {
    const res = await voteJointReview(rev.id, {
      vote_decision: decision,
      vote_opinion: '经核验事实无误，同意更正',
    })
    alert(res.message || '表决已提交')
    loadReviews()
    loadStats()
  } catch (err) {
    alert(err.message || '表决提交失败')
  } finally {
    actionLoading.value = false
  }
}

function openRejectModal(rev) {
  rejectingReview.value = rev
  rejectReasonInput.value = ''
  rejectModalVisible.value = true
}

async function submitRejectVote() {
  if (!rejectReasonInput.value || rejectReasonInput.value.trim().length < 2) {
    alert('提出不同意时，必须填写具体理由说明')
    return
  }
  actionLoading.value = true
  try {
    const res = await voteJointReview(rejectingReview.value.id, {
      vote_decision: 'reject',
      vote_opinion: rejectReasonInput.value.trim(),
    })
    alert(res.message || '异议已登记')
    rejectModalVisible.value = false
    loadReviews()
    loadStats()
  } catch (err) {
    alert(err.message || '提交异议失败')
  } finally {
    actionLoading.value = false
  }
}

async function handleCancelClick(rev) {
  const reason = prompt('请输入撤回本次联合会审的理由（可选）：', '经核实现场无误，自愿撤回')
  if (reason === null) return
  actionLoading.value = true
  try {
    const res = await cancelJointReview(rev.id, { cancel_reason: reason })
    alert(res.message || '会审已撤销')
    loadReviews()
    loadStats()
  } catch (err) {
    alert(err.message || '撤销失败')
  } finally {
    actionLoading.value = false
  }
}

function openArbitrateModal(rev) {
  arbitratingReview.value = rev
  arbitrateDecision.value = 'force_approve'
  arbitrateReasonInput.value = ''
  arbitrateModalVisible.value = true
}

async function submitArbitration() {
  if (!arbitrateReasonInput.value || arbitrateReasonInput.value.trim().length < 2) {
    alert('终局裁决必须填写详细理由')
    return
  }
  if (!confirm(`确定以管理员身份对会审 [${arbitratingReview.value.review_no}] 执行终局裁决吗？`)) {
    return
  }
  actionLoading.value = true
  try {
    const res = await adminArbitrateJointReview(arbitratingReview.value.id, {
      arbitration_decision: arbitrateDecision.value,
      arbitration_reason: arbitrateReasonInput.value.trim(),
    })
    alert(res.message || '管理员裁决已执行')
    arbitrateModalVisible.value = false
    loadReviews()
    loadStats()
  } catch (err) {
    alert(err.message || '裁决失败')
  } finally {
    actionLoading.value = false
  }
}

function openImageViewer(url) {
  previewImageUrl.value = url
}

function goToProjectSelect() {
  router.push('/projects')
}

function goProjectPages() {
  router.push('/projects/insulation_pipe_supply_2026/pages')
}
</script>

<style scoped>
.tube-page-root {
  min-height: 100vh;
  background-color: #f8fafc;
  color: #0f172a;
}

.tube-page-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 16px 20px 60px;
}

.breadcrumbs-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 12px;
  color: #64748b;
}

.crumb-link {
  background: none;
  border: none;
  padding: 0;
  font-size: 13px;
  color: #3b82f6;
  cursor: pointer;
}
.crumb-link:hover {
  text-decoration: underline;
}

.crumb-current {
  color: #0f172a;
  font-weight: 600;
}

.topbar.premium-topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: #ffffff;
  padding: 20px 24px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin-bottom: 16px;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-icon {
  font-size: 28px;
}

.topbar-title-block h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}

.live-status-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: #dbeafe;
  color: #1e40af;
  font-weight: 600;
}

.topbar-desc {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  max-width: 800px;
}

.topbar-actions {
  display: flex;
  gap: 10px;
}

.kpi-banner-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  cursor: pointer;
  transition: all 0.15s ease;
}
.kpi-card:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);
}
.kpi-card.has-action {
  border-color: #f87171;
  background: linear-gradient(180deg, #fff5f5 0%, #ffffff 100%);
}

.kpi-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.kpi-val {
  font-size: 26px;
  font-weight: 800;
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.kpi-val small {
  font-size: 13px;
  color: #94a3b8;
  font-weight: normal;
}

.text-red {
  color: #dc2626;
}
.text-blue {
  color: #2563eb;
}
.text-emerald {
  color: #059669;
}
.text-slate {
  color: #475569;
}

.kpi-alert-pulse {
  font-size: 11px;
  background: #ef4444;
  color: #fff;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: bold;
  animation: pulseBadge 1.5s infinite;
  margin-left: 8px;
}

.hall-tabs-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 2px;
}

.hall-tab-btn {
  background: none;
  border: none;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
  position: relative;
}
.hall-tab-btn:hover {
  color: #0f172a;
  background: #e2e8f0;
}
.hall-tab-btn.active {
  color: #2563eb;
  background: #ffffff;
  border-bottom: 2px solid #2563eb;
  margin-bottom: -4px;
}

.tab-badge-pill {
  background: #ef4444;
  color: #ffffff;
  font-size: 11px;
  font-weight: 800;
  padding: 1px 6px;
  border-radius: 10px;
}

.filter-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 20px;
  margin-bottom: 20px;
}

.filter-controls-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-field {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #475569;
}

.filter-field select,
.filter-field input {
  height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 10px;
  font-size: 13px;
  color: #0f172a;
  outline: none;
}
.filter-field select:focus,
.filter-field input:focus {
  border-color: #3b82f6;
}

.search-field input {
  width: 320px;
}

.reviews-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loading-state,
.empty-hall-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  color: #64748b;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  display: inline-block;
}

.empty-hall-card h3 {
  margin: 0 0 8px;
  color: #1e293b;
  font-size: 16px;
}

.review-cards-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.review-item-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.15s ease;
}
.review-item-card:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
}
.review-item-card.needs-me {
  border: 2px solid #ef4444;
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.15);
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cat-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}
.cat-pill.pipe {
  background: #ffedd5;
  color: #c2410c;
}
.cat-pill.fitting {
  background: #e0e7ff;
  color: #4338ca;
}

.review-no {
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
}

.order-ref {
  font-size: 13px;
  color: #475569;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
}

.status-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
}
.badge-voting {
  background: #fef3c7;
  color: #92400e;
}
.badge-approved {
  background: #d1fae5;
  color: #065f46;
}
.badge-rejected {
  background: #fee2e2;
  color: #991b1b;
}
.badge-cancelled {
  background: #f1f5f9;
  color: #64748b;
}

.meta-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
  color: #475569;
  background: #f8fafc;
  padding: 8px 14px;
  border-radius: 8px;
}

.meta-strip .time {
  margin-left: auto;
  color: #94a3b8;
  font-size: 12px;
}

.reason-quote-box {
  background: #fdf4ff;
  border-left: 4px solid #c026d3;
  padding: 10px 14px;
  border-radius: 0 8px 8px 0;
  font-size: 13px;
}

.quote-title {
  font-weight: 700;
  color: #86198f;
  margin-bottom: 4px;
}

.quote-content {
  color: #4a044e;
  line-height: 1.5;
}

.diff-block {
  background: #fefce8;
  border: 1px dashed #ca8a04;
  border-radius: 8px;
  padding: 12px 14px;
}

.diff-title {
  font-size: 12px;
  font-weight: 700;
  color: #854d0e;
  margin-bottom: 8px;
}

.diff-items-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.diff-grid-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.prop-name {
  color: #713f12;
  font-weight: 600;
}

.prop-old {
  color: #dc2626;
  text-decoration: line-through;
  background: rgba(220, 38, 38, 0.08);
  padding: 1px 4px;
  border-radius: 3px;
}

.prop-arrow {
  color: #854d0e;
}

.prop-new {
  color: #16a34a;
  font-weight: 700;
  background: rgba(22, 163, 74, 0.1);
  padding: 1px 6px;
  border-radius: 3px;
}

.diff-items-full-block {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #ffffff;
  border: 1px solid #fed7aa;
  border-radius: 6px;
  padding: 8px 10px;
}

.diff-items-header-bar {
  font-size: 12px;
}

.diff-items-mini-table-wrap {
  overflow-x: auto;
}

.diff-items-mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.diff-items-mini-table th {
  background: #fff7ed;
  color: #9a3412;
  font-weight: 600;
  padding: 4px 8px;
  text-align: left;
  border-bottom: 1px solid #fed7aa;
  white-space: nowrap;
}

.diff-items-mini-table td {
  padding: 5px 8px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  white-space: nowrap;
}

.diff-items-mini-table tr:last-child td {
  border-bottom: none;
}

.attachments-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.att-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.att-thumbs-row {
  display: flex;
  gap: 8px;
}

.att-img {
  width: 44px;
  height: 44px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  cursor: pointer;
  transition: transform 0.15s ease;
}
.att-img:hover {
  transform: scale(1.08);
}

.pipeline-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f8fafc;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.pipeline-title {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.pipeline-ratio {
  color: #2563eb;
}

.entities-vote-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
}

.entity-vote-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  background: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.entity-vote-card.is-approved {
  border-color: #86efac;
  background: #f0fdf4;
}
.entity-vote-card.is-rejected {
  border-color: #fca5a5;
  background: #fef2f2;
}

.ent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ent-role-tag {
  font-size: 11px;
  color: #64748b;
}

.ent-name {
  font-size: 13px;
  color: #0f172a;
}

.vote-tag {
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
}
.vote-tag.approved {
  background: #dcfce7;
  color: #15803d;
}
.vote-tag.rejected {
  background: #fee2e2;
  color: #b91c1c;
}
.vote-tag.pending {
  background: #f1f5f9;
  color: #94a3b8;
}

.reject-reason-tip {
  margin: 4px 0 0;
  font-size: 11px;
  color: #dc2626;
  max-width: 200px;
}

.resolution-summary-box {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  color: #065f46;
}

.res-title {
  font-weight: 700;
}

.card-actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid #f1f5f9;
  padding-top: 14px;
}

.my-vote-group {
  display: flex;
  gap: 10px;
}

.btn-approve {
  background: #16a34a;
  color: #fff;
  font-weight: 700;
  padding: 8px 18px;
}
.btn-approve:hover {
  background: #15803d;
}

.btn-reject {
  color: #dc2626;
  border: 1px solid #fca5a5;
  background: #fff;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
}
.btn-reject:hover {
  background: #fef2f2;
}

.my-voted-hint {
  font-size: 13px;
  color: #059669;
  background: #ecfdf5;
  padding: 4px 10px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.actions-right {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

.btn-cancel-rev {
  font-size: 13px;
  color: #64748b;
}

.btn-arbitrate {
  background: #f59e0b;
  color: #fff;
  font-weight: 600;
  font-size: 13px;
}
.btn-arbitrate:hover {
  background: #d97706;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
}

.page-info {
  font-size: 13px;
  color: #64748b;
}

/* 模态弹窗样式 */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 1400;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-dialog {
  background: #ffffff;
  border-radius: 12px;
  width: 100%;
  max-width: 500px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-head {
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-head h4 {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
}

.btn-x {
  background: none;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
}

.modal-content {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-tip {
  margin: 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.5;
}

.modal-textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}
.modal-textarea:focus {
  border-color: #3b82f6;
}

.arbitrate-choice-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
}

.choice-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #1e293b;
  cursor: pointer;
}

.modal-foot {
  padding: 12px 20px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 图片查看器 */
.image-viewer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 1500;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
}

.image-viewer-container {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}

.enlarged-img {
  max-width: 100%;
  max-height: 90vh;
  border-radius: 8px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
}

.btn-close-viewer {
  position: absolute;
  top: -16px;
  right: -16px;
  background: #ffffff;
  color: #0f172a;
  border: none;
  font-size: 18px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

/* 提请指引弹窗样式 */
.guide-dialog {
  max-width: 680px;
}

.head-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.guide-icon {
  font-size: 20px;
}

.btn-initiate-guide {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
  color: #ffffff !important;
  border: 1px solid #d97706 !important;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(217, 119, 6, 0.25);
}

.btn-initiate-guide:hover {
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%) !important;
}

.guide-intro {
  font-size: 13.5px;
  color: #334155;
  margin-bottom: 16px;
  line-height: 1.6;
}

.guide-steps-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.guide-step-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step-badge {
  align-self: flex-start;
  font-size: 11px;
  font-weight: 600;
  color: #4f46e5;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  padding: 1px 6px;
  border-radius: 4px;
}

.guide-step-card h5 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.guide-step-card p {
  margin: 0;
  font-size: 12.5px;
  color: #64748b;
  line-height: 1.5;
}

.step-action {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
  font-size: 12px;
  color: #475569;
}

.action-btn-group {
  display: inline-flex;
  gap: 6px;
}

.btn-xs {
  font-size: 11.5px;
  padding: 4px 10px;
  border-radius: 5px;
}

.guide-note-box {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 12.5px;
  color: #92400e;
  line-height: 1.6;
}
</style>
