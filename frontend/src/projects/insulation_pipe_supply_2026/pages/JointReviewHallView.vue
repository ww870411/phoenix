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
            <ScaleBalanceIcon :size="26" class="title-header-icon" />
            <h2>多方联合会审大厅 (Joint Review Hall)</h2>
            <span class="live-status-pill">共识会签机制</span>
          </div>
          <p class="topbar-desc">
            在待到货、待接收、待入库环节，任何正当修正诉求通过圆桌多方会审、全票同意后自动更正生效，共识免责、全程留痕。
          </p>
        </div>
        <div class="topbar-actions">
          <button type="button" class="btn primary btn-initiate-guide" @click="howToInitiateModalVisible = true">
            <span class="btn-icon">➕</span>
            <span>提请会审流程说明</span>
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
          <span class="kpi-label">✓ 已通过更正</span>
          <span class="kpi-val text-emerald">{{ approvedCount }} <small>笔</small></span>
        </div>
        <div class="kpi-card" @click="switchTab('all')">
          <span class="kpi-label">🌐 全网会审总单数</span>
          <span class="kpi-val text-slate">{{ allReviewCount ?? '—' }} <small>笔</small></span>
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
          <span>📚 已完结会审档案</span>
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
              <option value="pipe">🔥 保温管</option>
              <option value="fitting">🔩 管件与阀门</option>
            </select>
          </div>

          <div class="filter-field" v-if="currentTab === 'all'">
            <span>会审状态</span>
            <select v-model="filterStatus" @change="handleFilterChange">
              <option value="">全部状态</option>
              <option value="voting">🟡 会审中 (含推进中与挂起中)</option>
              <option value="suspended">🟠 挂起中 (存在异议协商中)</option>
              <option value="voting_normal">🟡 会审推进中 (尚无异议)</option>
              <option value="approved">🟢 已通过（含裁决）</option>
              <option value="rejected">🔴 终局裁决驳回</option>
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

        <template v-else>
          <!-- 列表折叠与批量控制栏 -->
          <div class="list-control-bar">
            <div class="control-left">
              <span class="total-text">共找到 <strong>{{ totalCount }}</strong> 笔会审提案</span>
              <span class="fold-hint-text">{{ focusedReviewId ? '（已定位通知关联议案）' : '（默认已折叠，点击卡片或按钮可展开查看明细）' }}</span>
            </div>
            <div class="control-right">
              <button v-if="focusedReviewId" type="button" class="btn ghost btn-xs" @click="showReviewList">返回当前列表</button>
              <button type="button" class="btn ghost btn-xs btn-ctrl-fold" @click="expandAll">
                展开全部 ▾
              </button>
              <button type="button" class="btn ghost btn-xs btn-ctrl-fold" @click="collapseAll">
                收起全部 ▴
              </button>
            </div>
          </div>

          <div class="review-cards-list">
            <div
              v-for="rev in reviewItems"
              :key="rev.id"
              class="review-item-card"
              :class="[
                `status-${rev.review_status}`,
                {
                  'needs-me': rev.needs_my_vote,
                  'is-card-collapsed': !isExpanded(rev.id),
                  'is-suspended': rev.review_status === 'voting' && (rev.rejected_entities || []).length > 0
                }
              ]"
              @click="handleCardClick($event, rev.id)"
            >
              <!-- 卡片顶栏（整行支持点击展开/折叠） -->
              <div
                class="card-header-row clickable-head"
                @click.stop="handleHeaderClick(rev.id)"
                :title="isExpanded(rev.id) ? '点击收起提案详情' : '点击展开提案详情'"
              >
                <div class="header-left">
                  <span class="fold-arrow" :class="{ 'is-open': isExpanded(rev.id) }">
                    {{ isExpanded(rev.id) ? '▼' : '▶' }}
                  </span>
                  <span class="cat-pill" :class="rev.order_category">
                    {{ rev.order_category === 'pipe' ? '🔥 保温管' : '🔩 管件阀门' }}
                  </span>
                  <span class="review-no font-mono">{{ rev.review_no }}</span>
                  <span class="order-ref font-mono">订单号: {{ rev.order_no }}</span>
                </div>
                <div class="header-right">
                  <!-- 待我表决高亮红标 -->
                  <span v-if="rev.needs_my_vote" class="needs-vote-badge">
                    ⚡ 待我表决
                  </span>
                  <!-- 状态徽章 -->
                  <span class="status-badge" :class="getStatusBadgeClass(rev)">
                    {{ formatReviewStatus(rev) }}
                  </span>
                  <!-- 折叠/展开独立按钮 -->
                  <button
                    type="button"
                    class="btn ghost btn-xs btn-fold-toggle"
                    @click.stop="isExpanded(rev.id) ? collapseCard(rev.id) : expandCard(rev.id)"
                  >
                    {{ isExpanded(rev.id) ? '收起 ▴' : '展开 ▾' }}
                  </button>
                </div>
              </div>

              <!-- 折叠态紧凑摘要条 (默认展示，点击任意位置一键顺畅展开) -->
              <div v-if="!isExpanded(rev.id)" class="folded-summary-strip" @click.stop="expandCard(rev.id)">
                <div class="summary-left">
                  <span class="sum-tag">👤 提请人：<strong>{{ rev.initiator_name }}</strong> ({{ rev.initiator_role }})</span>
                  <span class="sum-tag">📍 {{ rev.section_1_name }}</span>
                  <span class="sum-tag">🏭 {{ rev.supply_entity_name }}</span>
                  <span class="sum-patch-preview">
                    📝 拟更正：<strong>{{ formatPatchSummary(rev.proposed_patch) }}</strong>
                  </span>
                  <span v-if="rev.review_status === 'approved'" class="sum-tag tag-success font-mono">
                    ✅ 办结生效: {{ rev.finalized_at || rev.updated_at }}
                  </span>
                  <span v-else-if="rev.review_status === 'rejected'" class="sum-tag tag-reject font-mono">
                    🛑 终局驳回: {{ rev.finalized_at || rev.updated_at }}
                  </span>
                  <span v-else-if="rev.review_status === 'cancelled'" class="sum-tag tag-cancel font-mono">
                    ⚪ 已撤回: {{ rev.finalized_at || rev.updated_at }}
                  </span>
                  <span v-else-if="(rev.rejected_entities || []).length > 0" class="sum-tag tag-suspended font-mono">
                    🟠 挂起中: 存在异议待协商/裁决
                  </span>
                  <span v-else class="sum-tag tag-voting font-mono">
                    🟡 会审中: 待全员达成共识
                  </span>
                </div>
                <div class="summary-right">
                  <span class="sum-reason-text" :title="rev.review_reason">事由: {{ rev.review_reason }}</span>
                </div>
              </div>

              <!-- 展开态完整详情区 (展开后展示，阻止内部冒泡) -->
              <div v-if="isExpanded(rev.id)" class="expanded-details-body" @click.stop>
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
                                <th>原始记录（品类 / 规格 / 数量）</th>
                                <th>拟更正品类</th>
                                <th>拟更正规格型号</th>
                                <th>更正发货量</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="(it, itIdx) in val" :key="it.id || itIdx">
                                <td>{{ itIdx + 1 }}</td>
                                <td class="font-mono">{{ it.order_no || '—' }}</td>
                                <td>{{ formatOriginalItem(rev, it) }}</td>
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
                      已同意 {{ getApprovedVoteCount(rev) }} / {{ getTotalVoteCount(rev) }} 方
                    </span>
                  </div>

                  <div class="entities-vote-list">
                    <!-- 发起人专属卡片（发起人主动提请，默认计入法定赞成票） -->
                    <div class="entity-vote-card is-approved initiator-entity-card">
                      <div class="card-ent-top">
                        <div class="ent-info">
                          <span class="ent-role-tag initiator-pill">{{ rev.initiator_role || '现场负责人' }} · 提请人</span>
                          <strong class="ent-name">{{ rev.initiator_name || '提请主体' }}</strong>
                        </div>
                        <span class="vote-tag approved">✓ 发起并同意 (默认1票)</span>
                      </div>
                      <div class="card-vote-audit">
                        <div class="audit-row">
                          <span class="audit-signer">✍️ 提请经办: <strong>{{ rev.initiator_name }}</strong></span>
                          <span class="audit-time">🕒 {{ rev.created_at }}</span>
                        </div>
                        <div class="audit-opinion" :title="rev.review_reason">
                          💬 提请附言: {{ rev.review_reason }}
                        </div>
                      </div>
                    </div>

                    <!-- 协同表决主体卡片 -->
                    <div
                      v-for="ent in rev.required_entities"
                      :key="`${ent.entity_type}_${ent.entity_id}`"
                      class="entity-vote-card"
                      :class="getEntityVoteClass(rev, ent)"
                    >
                      <div class="card-ent-top">
                        <div class="ent-info">
                          <span class="ent-role-tag">{{ ent.role_desc || ent.entity_type }}</span>
                          <strong class="ent-name">{{ ent.entity_name }}</strong>
                        </div>
                        <template v-if="hasEntityApproved(rev, ent)">
                          <span class="vote-tag approved">✓ 已同意核准</span>
                        </template>
                        <template v-else-if="hasEntityRejected(rev, ent)">
                          <span class="vote-tag rejected">✕ 提出异议</span>
                        </template>
                        <template v-else>
                          <span class="vote-tag pending">⌛ 待表决</span>
                        </template>
                      </div>

                      <!-- 审计详情：经办人、时间、签署意见 -->
                      <div v-if="getEntityVote(rev, ent)" class="card-vote-audit" :class="{ 'is-reject': hasEntityRejected(rev, ent) }">
                        <div class="audit-row">
                          <span class="audit-signer">✍️ 经办签署: <strong>{{ getEntityVote(rev, ent).voter_name || getEntityVote(rev, ent).voter_username }}</strong></span>
                          <span class="audit-time">🕒 {{ getEntityVote(rev, ent).voted_at }}</span>
                        </div>
                        <div class="audit-opinion" :class="{ 'text-danger': hasEntityRejected(rev, ent) }">
                          💬 {{ hasEntityApproved(rev, ent) ? '核准意见' : '异议说明' }}：{{ getEntityVote(rev, ent).vote_opinion || (hasEntityApproved(rev, ent) ? '经核验事实无误，同意更正' : '未填写具体理由') }}
                        </div>
                      </div>
                      <div v-else-if="hasEntityRejected(rev, ent) && getEntityRejectOpinion(rev, ent)" class="card-vote-audit is-reject">
                        <div class="audit-opinion text-danger">
                          💬 异议说明：{{ getEntityRejectOpinion(rev, ent) }}
                        </div>
                      </div>
                      <div v-else class="card-vote-audit is-pending">
                        <span class="audit-wait-text">⌛ 待该主体经办人会签表决</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 最终决议记录（若已办结） -->
                <div v-if="rev.resolution_summary" class="resolution-summary-box">
                  <span class="res-title">🏁 最终决议记录：</span>
                  <span class="res-text">{{ rev.resolution_summary }}</span>
                </div>

                <!-- 操作动作工具栏 -->
                <div class="card-actions-bar">
                  <!-- 待我表决操作组 / 管理员代签入口 -->
                  <div v-if="rev.review_status === 'voting' && (rev.can_i_vote || rev.needs_my_vote || isAdminUser)" class="action-group my-vote-group">
                    <span v-if="isAdminUser" class="admin-sign-badge" title="系统超级管理员可指定代表任意主体进行表决或覆盖签署">
                      👑 管理员代签
                    </span>
                    <button
                      type="button"
                      class="btn primary btn-approve"
                      @click="openApproveModal(rev)"
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
                      @click="openCancelModal(rev)"
                      :disabled="actionLoading"
                    >
                      撤回会审
                    </button>

                    <!-- 终局裁决仲裁（超级管理员及特许裁决员特权通道） -->
                    <button
                      v-if="rev.can_arbitrate"
                      type="button"
                      class="btn warning btn-arbitrate"
                      @click="openArbitrateModal(rev)"
                      :disabled="actionLoading"
                      title="作为特许裁决员或超级管理员行使终局裁决权，打破死锁直接通过或驳回会审"
                    >
                      ⚖️ 终局裁决
                    </button>

                    <!-- 快捷收起按钮 -->
                    <button
                      type="button"
                      class="btn ghost btn-xs btn-collapse-bottom"
                      @click.stop="collapseCard(rev.id)"
                      title="收起此提案详情"
                    >
                      收起 ▴
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

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

    <!-- 弹窗 1：提出异议弹窗 -->
    <div v-if="rejectModalVisible" class="modal-backdrop" @click.self="rejectModalVisible = false">
      <div class="modal-dialog">
        <div class="modal-head">
          <h4>提出异议</h4>
          <button type="button" class="btn-x" @click="rejectModalVisible = false">✕</button>
        </div>
        <div class="modal-content">
          <p class="modal-tip">
            选择提出异议时，该会审将变更为【挂起中】状态，请详细说明您核对出的事实、不同意的理由或现场实际情况：
          </p>

          <!-- 管理员代为表决主体身份选择器 -->
          <div v-if="isAdminUser" class="modal-field admin-identity-picker">
            <label>👑 管理员表决身份主体：</label>
            <select v-model="adminSelectedEntityKey" class="modal-select">
              <option v-for="ent in getSelectableEntities(rejectingReview)" :key="ent.key" :value="ent.key">
                {{ ent.role_desc }} - {{ ent.entity_name }} {{ ent.statusText }}
              </option>
            </select>
            <small class="field-hint">作为超级管理员，请指定您本次发表异议代表的具体主体</small>
          </div>

          <textarea
            v-model="rejectReasonInput"
            rows="4"
            class="modal-textarea"
            placeholder="请详细说明您核对出的事实、不同意的理由或现场实际情况..."
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

    <!-- 弹窗：同意更正确认弹窗 -->
    <div v-if="approveModalVisible" class="modal-backdrop" @click.self="approveModalVisible = false">
      <div class="modal-dialog">
        <div class="modal-head">
          <h4>✓ 同意更正确认</h4>
          <button type="button" class="btn-x" @click="approveModalVisible = false">✕</button>
        </div>
        <div class="modal-content">
          <p class="modal-tip">
            您即将对会审单据 <strong>[{{ approvingReview?.review_no }}]</strong>（订单号：{{ approvingReview?.order_no }}）签署【同意更正】意见。
          </p>

          <!-- 管理员代为表决主体身份选择器 -->
          <div v-if="isAdminUser" class="modal-field admin-identity-picker">
            <label>👑 管理员表决身份主体：</label>
            <select v-model="adminSelectedEntityKey" class="modal-select">
              <option v-for="ent in getSelectableEntities(approvingReview)" :key="ent.key" :value="ent.key">
                {{ ent.role_desc }} - {{ ent.entity_name }} {{ ent.statusText }}
              </option>
            </select>
            <small class="field-hint">作为超级管理员，请指定您本次签署同意代表的具体主体</small>
          </div>

          <div class="modal-field">
            <label style="font-size: 12.5px; font-weight: 600; color: #475569; margin-bottom: 4px; display: block;">签署核准意见（可选）</label>
            <textarea
              v-model="approveOpinionInput"
              rows="3"
              class="modal-textarea"
              placeholder="请输入核准意见..."
            ></textarea>
          </div>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn ghost" @click="approveModalVisible = false">取消</button>
          <button type="button" class="btn primary" @click="submitApproveVote" :disabled="actionLoading">
            确认同意更正
          </button>
        </div>
      </div>
    </div>

    <!-- 弹窗：撤回会审确认弹窗 -->
    <div v-if="cancelModalVisible" class="modal-backdrop" @click.self="cancelModalVisible = false">
      <div class="modal-dialog">
        <div class="modal-head">
          <h4>↩ 撤回联合会审</h4>
          <button type="button" class="btn-x" @click="cancelModalVisible = false">✕</button>
        </div>
        <div class="modal-content">
          <p class="modal-tip">
            确定撤回对单据 <strong>[{{ cancelingReview?.review_no }}]</strong> 发起的联合会审吗？撤回后单据将自动解锁并恢复常规流转。
          </p>
          <div class="modal-field">
            <label style="font-size: 12.5px; font-weight: 600; color: #475569; margin-bottom: 4px; display: block;">撤回原因说明（可选）</label>
            <textarea
              v-model="cancelReasonInput"
              rows="3"
              class="modal-textarea"
              placeholder="请输入撤回理由..."
            ></textarea>
          </div>
        </div>
        <div class="modal-foot">
          <button type="button" class="btn ghost" @click="cancelModalVisible = false">取消</button>
          <button type="button" class="btn danger" @click="submitCancelReview" :disabled="actionLoading">
            确认撤回会审
          </button>
        </div>
      </div>
    </div>

    <!-- 弹窗 2：超级管理员终局裁决弹窗 -->
    <div v-if="arbitrateModalVisible" class="modal-backdrop" @click.self="arbitrateModalVisible = false">
      <div class="modal-dialog">
        <div class="modal-head">
          <h4>⚖️ 终局裁决仲裁 (特许通道)</h4>
          <button type="button" class="btn-x" @click="arbitrateModalVisible = false">✕</button>
        </div>
        <div class="modal-content">
          <p class="modal-tip">
            注意：作为特许终局裁决员或超级管理员，您的裁决将具有一锤定音的终局效力，直接打破流转僵局或协商争议：
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
            <div>
              <h4>如何提请多方联合会审？</h4>
              <p class="guide-subtitle">业务节点原位发起 · 全流程协同会签 · 实时纠错生效</p>
            </div>
          </div>
          <button type="button" class="btn-x" @click="howToInitiateModalVisible = false">✕</button>
        </div>
        <div class="modal-content guide-content">
          <!-- 导语 Banner -->
          <div class="guide-banner">
            <span class="banner-badge">📌 设立宗旨</span>
            <p class="guide-intro">
              为保障物流信息流转的准确性与及时性，降低沟通成本，故设立本功能。联合会审由当前<strong>待办节点责任主体</strong>在各自业务工作台中针对具体待办订单提起：
            </p>
          </div>

          <!-- 三大业务场景卡片 -->
          <div class="guide-steps-grid">
            <!-- 场景 1 -->
            <div class="guide-step-card">
              <div class="card-top-row">
                <div class="badge-and-title">
                  <span class="step-num-badge">场景 1</span>
                  <span class="step-title-text">已发货，待现场负责人确认到货环节</span>
                </div>
                <span class="role-pill">🚚 现场负责人提请。</span>
              </div>
              <div class="card-detail-body">
                <div class="detail-item">
                  <span class="detail-label"><span class="label-dot red"></span>异常情形：</span>
                  <span class="detail-text">供货商已发货，现场核对实物及随车单据中发现规格、数量或车牌号有误。</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label"><span class="label-dot blue"></span>所在位置：</span>
                  <span class="detail-text path-tag">需求侧工作台 ➔ 保温管物流台账 / 管件（阀门）物流台账</span>
                </div>
              </div>
              <div class="card-action-bar">
                <span class="action-label">⚡ 快捷直达：</span>
                <div class="action-btn-group">
                  <button type="button" class="btn ghost btn-xs btn-jump" @click="goToDemandWorkbench('pipe', 'logistics')">
                    直达保温管物流台账 ➔
                  </button>
                  <button type="button" class="btn ghost btn-xs btn-jump" @click="goToDemandWorkbench('fitting', 'fitting')">
                    直达管件/阀门物流台账 ➔
                  </button>
                </div>
              </div>
            </div>

            <!-- 场景 2 -->
            <div class="guide-step-card">
              <div class="card-top-row">
                <div class="badge-and-title">
                  <span class="step-num-badge">场景 2</span>
                  <span class="step-title-text">现场已确认到货，待施工单位接收环节</span>
                </div>
                <span class="role-pill">👷 施工单位提请</span>
              </div>
              <div class="card-detail-body">
                <div class="detail-item">
                  <span class="detail-label"><span class="label-dot red"></span>异常情形：</span>
                  <span class="detail-text">现场已确认到货，施工单位领用时发现实物与系统内订单规格或数量不符。</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label"><span class="label-dot blue"></span>所在位置：</span>
                  <span class="detail-text path-tag">需求侧工作台 ➔ 保温管物流台账 / 管件（阀门）物流台账</span>
                </div>
              </div>
              <div class="card-action-bar">
                <span class="action-label">⚡ 快捷直达：</span>
                <div class="action-btn-group">
                  <button type="button" class="btn ghost btn-xs btn-jump" @click="goToDemandWorkbench('pipe', 'logistics')">
                    直达保温管物流台账 ➔
                  </button>
                  <button type="button" class="btn ghost btn-xs btn-jump" @click="goToDemandWorkbench('fitting', 'fitting')">
                    直达管件/阀门物流台账 ➔
                  </button>
                </div>
              </div>
            </div>

            <!-- 场景 3 -->
            <div class="guide-step-card">
              <div class="card-top-row">
                <div class="badge-and-title">
                  <span class="step-num-badge">场景 3</span>
                  <span class="step-title-text">待库管确认环节</span>
                </div>
                <span class="role-pill">🏢 库管人员提请</span>
              </div>
              <div class="card-detail-body">
                <div class="detail-item">
                  <span class="detail-label"><span class="label-dot red"></span>异常情形：</span>
                  <span class="detail-text">施工单位已确认接收，库管人员在办结入库手续时发现台账与单据的规格型号、数量货车牌号等信息存在不一致。</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label"><span class="label-dot blue"></span>所在位置：</span>
                  <span class="detail-text path-tag">库管员工作台 ➔ 库管台账</span>
                </div>
              </div>
              <div class="card-action-bar">
                <span class="action-label">⚡ 快捷直达：</span>
                <div class="action-btn-group">
                  <button type="button" class="btn ghost btn-xs btn-jump" @click="goToWarehouseWorkbench('pipe')">
                    直达保温管台账 ➔
                  </button>
                  <button type="button" class="btn ghost btn-xs btn-jump" @click="goToWarehouseWorkbench('fitting', 'pending_warehouse')">
                    直达管件待入库 ➔
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 四步流转闭环流程可视化卡片 -->
          <div class="guide-workflow-strip">
            <div class="workflow-title">
              <span class="strip-icon">🧭</span>
              <span>业务操作闭环（四步指引）</span>
            </div>
            <div class="workflow-steps">
              <div class="wf-step">
                <div class="wf-step-idx">1</div>
                <div class="wf-step-content">
                  <div class="wf-step-name">定位待办订单</div>
                  <div class="wf-step-desc">进入对应工作台列表</div>
                </div>
              </div>
              <div class="wf-arrow">➔</div>
              <div class="wf-step">
                <div class="wf-step-idx">2</div>
                <div class="wf-step-content">
                  <div class="wf-step-name">点击【⚖️ 提请会审】</div>
                  <div class="wf-step-desc">右侧橙黄色专属按钮</div>
                </div>
              </div>
              <div class="wf-arrow">➔</div>
              <div class="wf-step">
                <div class="wf-step-idx">3</div>
                <div class="wf-step-content">
                  <div class="wf-step-name">录入更正与凭证</div>
                  <div class="wf-step-desc">修改数据/原因/上传照片</div>
                </div>
              </div>
              <div class="wf-arrow">➔</div>
              <div class="wf-step highlight">
                <div class="wf-step-idx success">✓</div>
                <div class="wf-step-content">
                  <div class="wf-step-name">全票同意·即刻生效</div>
                  <div class="wf-step-desc">单据变更并保留纪要</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 操作提示卡片 -->
          <div class="guide-note-box">
            <span class="note-icon">💡</span>
            <div class="note-content">
              <strong>操作提示</strong>：在对应工作台中找到该笔待办订单，点击右侧橙黄色的 <strong>【⚖️ 提请会审】</strong> 按钮，录入拟修改的数据（数量/型号/车牌等）、原因并上传现场照片。提请后单据将自动锁定，相关前序主体会收到会签通知并进入大厅表决！取得一致同意后，订单信息立即变更，并保留会议纪要
            </div>
          </div>
        </div>
        <div class="modal-foot guide-modal-foot">
          <button type="button" class="btn primary btn-know" @click="howToInitiateModalVisible = false">了解并关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import ScaleBalanceIcon from '../components/ScaleBalanceIcon.vue'
import {
  adminArbitrateJointReview,
  cancelJointReview,
  listJointReviews,
  getJointReviewDetail,
  voteJointReview,
} from '../services/jointReviewApi'

const route = useRoute()
const router = useRouter()
// 展开详情和代签弹窗需要读取当前登录身份。
const auth = useAuthStore()

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '2026年度保温管、管件物流链管理系统', to: '/projects/insulation_pipe_supply_2026/pages' },
  { label: '联合会审大厅', to: null },
])

const currentTab = ref('pending_my_vote')
const filterCategory = ref('')
const filterStatus = ref('')
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

// 只允许最新请求更新列表和统计，旧响应不能覆盖用户当前操作。
let listRequestVersion = 0
let statsRequestVersion = 0
const focusedReviewId = ref(null)
const loading = ref(false)
const actionLoading = ref(false)
const reviewItems = ref([])
const totalCount = ref(0)
// 全网统计独立于当前列表的标签、筛选和分页；尚未取到统计时显示横线。
const allReviewCount = ref(null)

// 折叠/展开提案状态控制（响应式字典，确保精确触发 Vue 3 重新渲染）
const expandedMap = ref({})

function isExpanded(revId) {
  if (revId == null) return false
  return !!expandedMap.value[String(revId)]
}

// 展开卡片（幂等赋值 true，无论调用多少次均确保为展开态）
function expandCard(revId) {
  if (revId == null) return
  expandedMap.value = {
    ...expandedMap.value,
    [String(revId)]: true,
  }
}

// 折叠卡片（幂等赋值 false）
function collapseCard(revId) {
  if (revId == null) return
  expandedMap.value = {
    ...expandedMap.value,
    [String(revId)]: false,
  }
}

// 卡片容器点击：折叠态下点击卡片任意空白区域或文字，均 100% 顺畅展开
function handleCardClick(event, revId) {
  if (revId == null) return
  if (!isExpanded(revId)) {
    expandCard(revId)
  }
}

// 顶栏点击：根据当前状态明确执行收起或展开
function handleHeaderClick(revId) {
  if (revId == null) return
  if (isExpanded(revId)) {
    collapseCard(revId)
  } else {
    expandCard(revId)
  }
}

function toggleExpand(revId) {
  if (revId == null) return
  const k = String(revId)
  expandedMap.value = {
    ...expandedMap.value,
    [k]: !expandedMap.value[k],
  }
}

function expandAll() {
  const next = {}
  for (const r of reviewItems.value) {
    if (r && r.id != null) {
      next[String(r.id)] = true
    }
  }
  expandedMap.value = next
}

function collapseAll() {
  expandedMap.value = {}
}

// 统计总表决方数：发起人 1 票 + 被邀协同主体 N 票
function getTotalVoteCount(rev) {
  if (!rev) return 1
  return 1 + ((rev.required_entities || []).length)
}

// 统计已赞成方数：发起人提请即代表同意（默认 1 票） + 各已同意主体
function getApprovedVoteCount(rev) {
  if (!rev) return 0
  if (rev.review_status === 'cancelled') return 0
  return 1 + ((rev.approved_entities || []).length)
}

function getVoteProgressClass(rev) {
  if (rev.review_status === 'approved') return 'progress-all-approved'
  if ((rev.rejected_entities || []).length > 0) return 'progress-has-reject'
  const total = getTotalVoteCount(rev)
  const approved = getApprovedVoteCount(rev)
  if (approved === total) return 'progress-all-approved'
  return 'progress-partial'
}

function formatPatchSummary(patch) {
  if (!patch || typeof patch !== 'object') return '无变更数据'
  const keys = Object.keys(patch)
  if (keys.length === 0) return '现场事实认定 / 澄清会签'
  const parts = []
  for (const k of keys) {
    if (k === 'items' && Array.isArray(patch[k])) {
      parts.push(`明细更正(${patch[k].length}项)`)
    } else {
      const label = formatPatchKey(k)
      parts.push(`${label}: ${patch[k]}`)
    }
  }
  return parts.slice(0, 3).join('；') + (parts.length > 3 ? ' 等' : '')
}

// 统计值
const myPendingCount = ref(0)
const myInitiatedCount = ref(0)
const approvedCount = ref(0)
const suspendedCount = ref(0)

// 管理员代签主体身份
const adminSelectedEntityKey = ref('')

const isAdminUser = computed(() => {
  const grp = auth.user?.group
  return grp === 'Global_admin' || grp === 'dev_admin'
})

function getSelectableEntities(rev) {
  if (!rev || !rev.required_entities) return []
  const req = rev.required_entities || []
  const votes = rev.votes || []
  const voteMap = {}
  for (const v of votes) {
    voteMap[`${v.entity_type}::${v.entity_id}`] = v
  }

  return req.map((ent) => {
    const key = `${ent.entity_type}::${ent.entity_id}`
    const v = voteMap[key]
    let statusText = '【待签署】'
    if (v) {
      statusText = v.vote_decision === 'approve' ? '【已同意】' : '【已提异议】'
    }
    return {
      key,
      entity_type: ent.entity_type,
      entity_id: ent.entity_id,
      entity_name: ent.entity_name || ent.entity_id,
      role_desc: ent.role_desc || '必审主体',
      hasVoted: !!v,
      votedDecision: v ? v.vote_decision : null,
      statusText,
    }
  })
}

// 弹窗状态
const rejectModalVisible = ref(false)
const rejectingReview = ref(null)
const rejectReasonInput = ref('')

const approveModalVisible = ref(false)
const approvingReview = ref(null)
const approveOpinionInput = ref('经核验事实无误，同意更正')

const cancelModalVisible = ref(false)
const cancelingReview = ref(null)
const cancelReasonInput = ref('经核实现场无误，自愿撤回')

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

// 通知按ID直接打开，不受首屏分页或已表决后待办筛选影响。
function applyRouteQuery(query) {
  const tab = String(query.tab || 'pending_my_vote')
  currentTab.value = ['pending_my_vote', 'my_initiated', 'history', 'all'].includes(tab) ? tab : 'all'
  searchKeyword.value = String(query.search || '')
  const id = Number(query.review_id)
  focusedReviewId.value = Number.isSafeInteger(id) && id > 0 ? id : null
  currentPage.value = 1
}
onMounted(() => {
  applyRouteQuery(route.query)
  loadReviews()
  loadStats()
})
watch(() => route.query, (query, previous) => {
  const id = Number(query.review_id)
  const nextId = Number.isSafeInteger(id) && id > 0 ? id : null
  let changed = false
  if (query.tab !== previous.tab) {
    const tab = String(query.tab || 'pending_my_vote')
    const normalized = ['pending_my_vote', 'my_initiated', 'history', 'all'].includes(tab) ? tab : 'all'
    if (currentTab.value !== normalized) {
      currentTab.value = normalized
      changed = true
    }
  }
  if (nextId !== focusedReviewId.value) {
    focusedReviewId.value = nextId
    changed = true
  }
  if (query.search !== previous.search && String(query.search || '') !== searchKeyword.value) {
    searchKeyword.value = String(query.search || '')
    changed = true
  }
  if (changed) {
    currentPage.value = 1
    loadReviews()
  }
})

function clearFocusedReview() {
  focusedReviewId.value = null
  if (route.query.review_id) {
    const { review_id, ...query } = route.query
    router.replace({ path: route.path, query })
  }
}

function showReviewList() {
  clearFocusedReview()
  currentPage.value = 1
  loadReviews()
}

async function loadStats() {
  const version = ++statsRequestVersion
  // 各项统计独立取数，个别请求失败不会丢弃其余成功结果。
  const counts = [myPendingCount, myInitiatedCount, approvedCount, suspendedCount, allReviewCount]
  const results = await Promise.allSettled([
    listJointReviews({ tab: 'pending_my_vote', limit: 1 }),
    listJointReviews({ tab: 'my_initiated', limit: 1 }),
    listJointReviews({ tab: 'all', review_status: 'approved', limit: 1 }),
    listJointReviews({ tab: 'all', review_status: 'suspended', limit: 1 }),
    listJointReviews({ tab: 'all', limit: 1 }),
  ])
  if (version !== statsRequestVersion) return
  results.forEach((result, index) => {
    if (result.status === 'fulfilled' && result.value?.ok) {
      counts[index].value = result.value.total ?? 0
    } else {
      if (counts[index] === allReviewCount) allReviewCount.value = null
      console.warn('加载联合会审统计失败', result.status === 'rejected' ? result.reason : result.value)
    }
  })
}

async function loadReviews() {
  const version = ++listRequestVersion
  const focusId = focusedReviewId.value
  loading.value = true
  try {
    const res = focusId ? await getJointReviewDetail(focusId) : await listJointReviews({
      tab: currentTab.value,
      order_category: filterCategory.value || undefined,
      review_status: currentTab.value === 'all' ? (filterStatus.value || undefined) : undefined,
      search: searchKeyword.value ? searchKeyword.value.trim() : undefined,
      page: currentPage.value,
      limit: pageSize.value,
    })
    if (version !== listRequestVersion) return
    if (res && res.ok) {
      reviewItems.value = focusId ? [res.data] : (res.items || [])
      totalCount.value = focusId ? 1 : (res.total || 0)
      expandedMap.value = focusId ? { [String(focusId)]: true } : {}
    }
  } catch (err) {
    if (version === listRequestVersion) alert(err.message || '加载联合会审列表失败')
  } finally {
    if (version === listRequestVersion) loading.value = false
  }
}

function switchTab(tabKey) {
  if (currentTab.value === tabKey) return
  focusedReviewId.value = null
  currentTab.value = tabKey
  currentPage.value = 1
  router.replace({
    path: route.path,
    query: { ...route.query, tab: tabKey, review_id: undefined },
  })
  loadReviews()
}

function handleFilterChange() {
  clearFocusedReview()
  currentPage.value = 1
  loadReviews()
}

function resetFilters() {
  clearFocusedReview()
  filterCategory.value = ''
  filterStatus.value = ''
  searchKeyword.value = ''
  currentPage.value = 1
  loadReviews()
}

function changePage(page) {
  clearFocusedReview()
  currentPage.value = page
  loadReviews()
}

function formatReviewStatus(rev) {
  const st = rev.review_status
  const totalVotes = getTotalVoteCount(rev)
  const appVotes = getApprovedVoteCount(rev)
  if (st === 'voting') {
    const rejCount = (rev.rejected_entities || []).length
    if (rejCount > 0) return `🟠 挂起中 (${rejCount}方异议·${appVotes}/${totalVotes}同意)`
    return `🟡 会审中 (${appVotes}/${totalVotes} 已同意)`
  }
  if (st === 'approved') return isArbitrationApproval(rev)
    ? `🟢 终局裁决通过已生效 (${appVotes}/${totalVotes} 同意)`
    : `🟢 全票通过已生效 (${appVotes}/${totalVotes})`
  if (st === 'rejected') return '🔴 终局裁决驳回'
  if (st === 'cancelled') return '⚪ 已撤销'
  return st
}

function getStatusBadgeClass(rev) {
  if (rev.review_status === 'voting' && (rev.rejected_entities || []).length > 0) {
    return 'badge-suspended'
  }
  return `badge-${rev.review_status}`
}

function isArbitrationApproval(rev) {
  return rev.approval_type === 'arbitration' ||
    (rev.finalized_by && rev.finalized_by !== 'SYSTEM_CONSENSUS')
}

function formatOriginalItem(rev, item) {
  const rows = rev.original_snapshot?.items || rev.original_snapshot?._review_rows || []
  const before = rows.find(row => String(row.id) === String(item.id))
  return before ? `${before.fitting_type || '—'} / ${before.model_spec || '—'} / ${before.shipped_qty ?? '—'} ${before.unit || '件'}` : '历史议案未留存该项原值'
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

function getEntityVote(rev, ent) {
  if (!rev || !rev.votes || !ent) return null
  return rev.votes.find(
    (v) =>
      v.entity_type === ent.entity_type &&
      String(v.entity_id).toLowerCase() === String(ent.entity_id).toLowerCase()
  ) || null
}

function getPendingEntities(rev) {
  if (!rev || !rev.required_entities) return []
  const votes = rev.votes || []
  return rev.required_entities.filter(
    (ent) =>
      !votes.some(
        (v) =>
          v.entity_type === ent.entity_type &&
          String(v.entity_id).toLowerCase() === String(ent.entity_id).toLowerCase()
      )
  )
}

function formatPreStatus(status) {
  const map = {
    pending_arrival: '待到货确认',
    pending_receive: '待施工接收',
    pending_diff_approve: '差异待审核',
    pending_warehouse: '待库管确认',
    completed: '已入库办结',
    under_review: '会审挂起中',
  }
  return map[status] || status || '待办流转中'
}

function formatTimelineStatus(rev) {
  if (!rev) return ''
  if (rev.review_status === 'voting') {
    if ((rev.rejected_entities || []).length > 0) {
      return '🟠 挂起中·存在异议待协商或裁决'
    }
    return '🟡 会审中·协同签署中'
  }
  const map = {
    approved: isArbitrationApproval(rev) ? '🟢 终局裁决通过·已办结生效' : '🟢 全票通过·已办结生效',
    rejected: '🔴 终局裁决驳回终止',
    cancelled: '⚪ 已主动撤销',
  }
  return map[rev.review_status] || rev.review_status
}

function getFinalStepBadge(rev) {
  if (!rev) return ''
  if (rev.review_status === 'approved') return isArbitrationApproval(rev) ? '终局裁决·通过生效' : '全票共识·自动生效'
  if (rev.review_status === 'rejected') return '终局驳回·维持原单'
  if (rev.review_status === 'cancelled') return '已主动撤销'
  if (rev.review_status === 'voting' && (rev.rejected_entities || []).length > 0) return '存在异议·挂起协商中'
  return '等待全员达成共识'
}

function getFinalStepOperator(rev) {
  if (!rev) return ''
  if (rev.review_status === 'approved') {
    if (rev.finalized_by === 'SYSTEM_CONSENSUS') return '🤖 系统共识自动闭环'
    return `👤 ${rev.finalized_by || '系统自动处理'}`
  }
  if (rev.review_status === 'rejected') {
    return `👤 ${rev.finalized_by || '会审异议/管理员裁决'}`
  }
  if (rev.review_status === 'cancelled') {
    return `👤 提请人: ${rev.initiator_name}`
  }
  return '系统自动化监测中'
}

function openApproveModal(rev) {
  approvingReview.value = rev
  approveOpinionInput.value = '经核验事实无误，同意更正'
  if (isAdminUser.value) {
    const ents = getSelectableEntities(rev)
    const unvoted = ents.find((e) => !e.hasVoted)
    adminSelectedEntityKey.value = unvoted ? unvoted.key : (ents[0]?.key || '')
  } else {
    adminSelectedEntityKey.value = ''
  }
  approveModalVisible.value = true
}

async function submitApproveVote() {
  if (!approvingReview.value) return
  actionLoading.value = true
  try {
    const payload = {
      vote_decision: 'approve',
      vote_opinion: approveOpinionInput.value.trim() || '经核验事实无误，同意更正',
    }
    if (isAdminUser.value && adminSelectedEntityKey.value) {
      const [etype, eid] = adminSelectedEntityKey.value.split('::')
      payload.target_entity_type = etype
      payload.target_entity_id = eid
    }
    const res = await voteJointReview(approvingReview.value.id, payload)
    alert(res.message || '表决已提交')
    approveModalVisible.value = false
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
  if (isAdminUser.value) {
    const ents = getSelectableEntities(rev)
    const unvoted = ents.find((e) => !e.hasVoted)
    adminSelectedEntityKey.value = unvoted ? unvoted.key : (ents[0]?.key || '')
  } else {
    adminSelectedEntityKey.value = ''
  }
  rejectModalVisible.value = true
}

async function submitRejectVote() {
  if (!rejectReasonInput.value || rejectReasonInput.value.trim().length < 2) {
    alert('提出异议时，必须填写具体理由说明')
    return
  }
  actionLoading.value = true
  try {
    const payload = {
      vote_decision: 'reject',
      vote_opinion: rejectReasonInput.value.trim(),
    }
    if (isAdminUser.value && adminSelectedEntityKey.value) {
      const [etype, eid] = adminSelectedEntityKey.value.split('::')
      payload.target_entity_type = etype
      payload.target_entity_id = eid
    }
    const res = await voteJointReview(rejectingReview.value.id, payload)
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

function openCancelModal(rev) {
  cancelingReview.value = rev
  cancelReasonInput.value = '经核实现场无误，自愿撤回'
  cancelModalVisible.value = true
}

async function submitCancelReview() {
  if (!cancelingReview.value) return
  actionLoading.value = true
  try {
    const res = await cancelJointReview(cancelingReview.value.id, {
      cancel_reason: cancelReasonInput.value.trim() || '经核实现场无误，自愿撤回',
    })
    alert(res.message || '会审已撤销')
    cancelModalVisible.value = false
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
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 18px;
  padding-bottom: 60px;
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
  align-items: center;
  gap: 20px;
  background: #ffffff;
  padding: 18px 24px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  margin-bottom: 16px;
}

.topbar-title-block {
  flex: 1 1 auto;
  min-width: 0;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.title-header-icon {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  filter: drop-shadow(0 1px 2px rgba(217, 119, 6, 0.18));
}

.topbar-title-block h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap;
}

.live-status-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: #dbeafe;
  color: #1e40af;
  font-weight: 600;
  white-space: nowrap;
}

.topbar-desc {
  margin: 6px 0 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  white-space: nowrap;
}

.topbar-actions .btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
  box-sizing: border-box;
  transition: all 0.15s ease;
}

.topbar-actions .btn-refresh {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #334155;
}

.topbar-actions .btn-refresh:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}

@media (max-width: 860px) {
  .topbar.premium-topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 20px;
  }

  .topbar-actions {
    width: 100%;
    flex-wrap: wrap;
  }
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

.list-control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background: #f1f5f9;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  font-size: 13px;
  margin-bottom: -4px;
}

.total-text {
  color: #334155;
}
.total-text strong {
  color: #2563eb;
}
.fold-hint-text {
  color: #64748b;
  font-size: 12px;
  margin-left: 6px;
}

.control-right {
  display: flex;
  gap: 8px;
}

.btn-ctrl-fold {
  background: #ffffff !important;
  border: 1px solid #cbd5e1 !important;
  color: #334155 !important;
  font-size: 11.5px !important;
  padding: 3px 10px !important;
  border-radius: 5px !important;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-ctrl-fold:hover {
  background: #f8fafc !important;
  border-color: #3b82f6 !important;
  color: #2563eb !important;
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
.review-item-card.is-card-collapsed {
  padding: 12px 18px;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.review-item-card.is-card-collapsed:hover {
  border-color: #93c5fd;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
  background: #fbfdff;
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

.card-header-row.clickable-head {
  cursor: pointer;
  user-select: none;
  transition: background 0.15s ease;
}
.card-header-row.clickable-head:hover .review-no {
  color: #2563eb;
}

.fold-arrow {
  font-size: 11px;
  color: #64748b;
  width: 14px;
  display: inline-block;
  transition: transform 0.2s ease;
}
.fold-arrow.is-open {
  color: #2563eb;
}

.needs-vote-badge {
  background: #ef4444;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  animation: pulseBadge 1.5s infinite;
}

.vote-progress-pill {
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #475569;
}
.vote-progress-pill.progress-all-approved {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #047857;
}
.vote-progress-pill.progress-partial {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}
.vote-progress-pill.progress-has-reject {
  background: #fef2f2;
  border-color: #fecaca;
  color: #b91c1c;
}

.btn-fold-toggle {
  background: #ffffff !important;
  border: 1px solid #cbd5e1 !important;
  color: #475569 !important;
  font-size: 11px !important;
  padding: 2px 8px !important;
  border-radius: 4px !important;
  cursor: pointer;
  margin-left: 4px;
}
.btn-fold-toggle:hover {
  border-color: #3b82f6 !important;
  color: #2563eb !important;
  background: #f8fafc !important;
}

.btn-collapse-bottom {
  border: 1px solid #cbd5e1 !important;
  color: #64748b !important;
  font-size: 11.5px !important;
  padding: 3px 8px !important;
  border-radius: 4px !important;
  cursor: pointer;
}
.btn-collapse-bottom:hover {
  border-color: #94a3b8 !important;
  color: #1e293b !important;
  background: #f1f5f9 !important;
}

.folded-summary-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12.5px;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
  gap: 12px;
}
.folded-summary-strip:hover {
  background: #eff6ff;
  border-color: #60a5fa;
}

.summary-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.sum-tag {
  color: #475569;
  font-size: 12px;
}

.sum-patch-preview {
  color: #0369a1;
  background: #e0f2fe;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.summary-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.sum-reason-text {
  color: #64748b;
  font-size: 12px;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.click-unfold-tip {
  color: #2563eb;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}

.expanded-details-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.initiator-entity-card {
  background: #f0fdf4 !important;
  border-color: #86efac !important;
  box-shadow: 0 1px 3px rgba(16, 185, 129, 0.1);
}

.initiator-pill {
  color: #065f46 !important;
  font-weight: 700;
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
.badge-suspended {
  background: #ffedd5;
  color: #c2410c;
  border: 1px solid #fed7aa;
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
  padding: 12px 14px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.15s ease;
}
.entity-vote-card.is-approved {
  border-color: #86efac;
  background: #f0fdf4;
}
.entity-vote-card.is-rejected {
  border-color: #fca5a5;
  background: #fef2f2;
}

.card-ent-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.card-vote-audit {
  margin-top: 2px;
  padding-top: 8px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}
.card-vote-audit.is-reject {
  border-top-color: #fca5a5;
}
.card-vote-audit.is-pending {
  border-top-color: #e2e8f0;
}

.audit-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.audit-signer {
  color: #334155;
  font-size: 11.5px;
}
.audit-time {
  color: #64748b;
  font-family: monospace;
  font-size: 11px;
}

.audit-opinion {
  color: #0f172a;
  background: rgba(0, 0, 0, 0.03);
  padding: 5px 8px;
  border-radius: 4px;
  line-height: 1.4;
  word-break: break-all;
  font-size: 12px;
}
.audit-wait-text {
  color: #94a3b8;
  font-size: 11.5px;
  font-style: italic;
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
.sum-tag.tag-success {
  background: #dcfce7;
  color: #15803d;
}
.sum-tag.tag-reject {
  background: #fee2e2;
  color: #991b1b;
}
.sum-tag.tag-cancel {
  background: #f1f5f9;
  color: #64748b;
}
.sum-tag.tag-suspended {
  background: #ffedd5;
  color: #9a3412;
  border: 1px solid #fdba74;
}
.sum-tag.tag-voting {
  background: #fef3c7;
  color: #92400e;
}

.admin-sign-badge {
  font-size: 11px;
  font-weight: 700;
  color: #7c2d12;
  background: #ffedd5;
  border: 1px solid #fed7aa;
  padding: 3px 8px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
}

.admin-identity-picker {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 12px;
}
.admin-identity-picker label {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 6px;
  display: block;
}
.admin-identity-picker .modal-select {
  width: 100%;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid #94a3b8;
  font-size: 13px;
  background: #ffffff;
  color: #0f172a;
}
.admin-identity-picker .field-hint {
  display: block;
  font-size: 11.5px;
  color: #64748b;
  margin-top: 4px;
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
  max-width: 880px;
  max-height: 90vh;
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 40px -15px rgba(15, 23, 42, 0.35);
}

.modal-head {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.head-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.guide-icon {
  font-size: 26px;
  line-height: 1;
}

.modal-head h4 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
}

.guide-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: #64748b;
  font-weight: 400;
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

.guide-content {
  padding: 20px 24px;
  overflow-y: auto;
  gap: 16px;
  background: #fcfdfe;
}

/* 顶部导语 Banner */
.guide-banner {
  background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 12px 16px;
  position: relative;
}

.banner-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  color: #1e40af;
  background: #dbeafe;
  border: 1px solid #93c5fd;
  border-radius: 4px;
  padding: 1px 6px;
  margin-bottom: 6px;
}

.guide-intro {
  font-size: 13.5px;
  color: #1e293b;
  margin: 0;
  line-height: 1.6;
}

/* 业务场景卡片列表 */
.guide-steps-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.guide-step-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.guide-step-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.card-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.badge-and-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.step-num-badge {
  font-size: 11.5px;
  font-weight: 700;
  color: #3b82f6;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 2px 8px;
  border-radius: 6px;
  letter-spacing: 0.2px;
}

.step-title-text {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.role-pill {
  font-size: 12px;
  font-weight: 600;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

.card-detail-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  line-height: 1.55;
}

.detail-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.detail-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  color: #475569;
  min-width: 76px;
  font-size: 12px;
}

.label-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.label-dot.red { background: #ef4444; }
.label-dot.blue { background: #3b82f6; }

.detail-text {
  color: #334155;
  font-size: 12.5px;
}

.path-tag {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: inherit;
  color: #1e293b;
  font-weight: 500;
}

.card-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
}

.action-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.action-btn-group {
  display: inline-flex;
  gap: 8px;
}

.btn-jump {
  background: #ffffff !important;
  border: 1px solid #cbd5e1 !important;
  color: #1e293b !important;
  font-size: 12px !important;
  font-weight: 600;
  padding: 5px 12px !important;
  border-radius: 6px !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: all 0.15s ease;
  cursor: pointer;
}

.btn-jump:hover {
  background: #f8fafc !important;
  border-color: #3b82f6 !important;
  color: #2563eb !important;
  box-shadow: 0 2px 5px rgba(37, 99, 235, 0.15);
  transform: translateY(-1px);
}

/* 4 步流转闭环条 */
.guide-workflow-strip {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.workflow-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 700;
  color: #334155;
}

.workflow-steps {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.wf-step {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 6px 10px;
  flex: 1;
}

.wf-step.highlight {
  background: #f0fdf4;
  border-color: #86efac;
}

.wf-step-idx {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #3b82f6;
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.wf-step-idx.success {
  background: #16a34a;
}

.wf-step-content {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}

.wf-step-name {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
}

.wf-step-desc {
  font-size: 10.5px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wf-arrow {
  color: #94a3b8;
  font-size: 12px;
  font-weight: bold;
}

/* 操作提示框 */
.guide-note-box {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.note-icon {
  font-size: 18px;
  line-height: 1.4;
  flex-shrink: 0;
}

.note-content {
  font-size: 12.5px;
  color: #92400e;
  line-height: 1.6;
}

.guide-modal-foot {
  padding: 12px 24px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
  display: flex;
  justify-content: flex-end;
}

.btn-know {
  padding: 6px 20px;
  font-size: 13px;
  font-weight: 600;
}
</style>
