<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      
      <!-- 高级工作台头部 -->
      <header class="topbar premium-topbar">
        <div>
          <h2>现场管理工作台 (需求侧)</h2>
          <p class="sub">
            面向项目现场负责人与管理人员。提供 Tabs 标签化分类，支持未来三日滚动计划的高效填报、昨日实际用量核对、物理到货确认与施工接收登记。
          </p>
        </div>
        <div class="topbar-actions">
          <button type="button" class="btn ghost btn-back" @click="goProjectPages">
            返回功能页
          </button>
          <button
            type="button"
            class="btn primary submit-status-button"
            :disabled="!selectedSection1Id || !canSubmitCurrentProject || submitStatusLoading"
            @click="handleSection1SubmitClick"
          >
            {{ submitStatusLoading ? '提交中...' : '提交本站填报状态' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>

      <!-- 全局筛选与工作台 Meta 卡片 -->
      <section class="card elevated filter-card">
        <div class="panel-title-row">
          <h2>工作台全局筛选</h2>
          <p v-if="actionMessage" :class="['action-message', actionMessage.type]">
            {{ actionMessage.text }}
          </p>
        </div>

        <div v-if="optionsError" class="error-box">
          {{ optionsError }}
        </div>

        <div class="filter-grid compact-filter-grid">
          <label class="field">
            <span>当前管理的需求主体</span>
            <select v-model="selectedSection1Id" :disabled="optionsLoading || !section1Options.length">
              <option value="" disabled>请选择要操作的需求主体</option>
              <option v-for="section1 in section1Options" :key="section1.section_1_id" :value="section1.section_1_id">
                {{ section1.section_1_name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>消耗采集日期</span>
            <input v-model="usageDate" type="date" :disabled="!isGlobalAdmin" @change="handleUsageDateChange" />
          </label>
        </div>

        <!-- 磨砂玻璃态微数据看板 (Quick Dashboard) -->
        <div class="meta-dashboard">
          <div class="meta-card">
            <span class="meta-label">授权范围</span>
            <strong class="meta-value">{{ section1Options.length }} 个主体</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">保温管型号</span>
            <strong class="meta-value">{{ currentPipeModelOptions.length }} 种</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">当前角色</span>
            <strong class="meta-value">{{ currentGroupLabel }}</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">计划起始日期</span>
            <strong class="meta-value">{{ anchorDate || '未设置' }}</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">消耗采集日期</span>
            <strong class="meta-value">{{ usageDate || '未设置' }}</strong>
          </div>
        </div>
      </section>

      <!-- 一级大类胶囊分段切换栏 (Segmented Category Bar) -->
      <div class="category-segment-wrapper" v-if="selectedSection1Id">
        <div class="category-segment-bar">
          <button 
            type="button" 
            class="category-segment-btn" 
            :class="{ active: activeCategory === 'pipe' }" 
            @click="handleCategoryClick('pipe')"
          >
            <span class="cat-icon">🔹</span>
            <span class="cat-label">保温管业务</span>
            <span class="cat-count">4 项功能</span>
          </button>
          <button 
            type="button" 
            class="category-segment-btn" 
            :class="{ active: activeCategory === 'fitting' }" 
            @click="handleCategoryClick('fitting')"
          >
            <span class="cat-icon">🔩</span>
            <span class="cat-label">管件业务</span>
            <span class="cat-count">2 项功能</span>
          </button>
        </div>
      </div>

      <!-- 二级选项卡导航 (Responsive Sub-Tabs Header) -->
      <div class="tube-tabs-header-wrap" v-if="selectedSection1Id">
        <!-- 保温管子标签 -->
        <div class="tube-tabs-header" v-if="activeCategory === 'pipe'">
          <button 
            type="button" 
            :class="{ active: activeTab === 'usage' }" 
            @click="handleTabClick('usage')"
          >
            📊 每日使用消耗填报
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'plan' }" 
            @click="handleTabClick('plan')"
          >
            🕒 三日滚动计划填报
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'logistics' }" 
            @click="handleTabClick('logistics')"
          >
            🚚 现场到货与接收确认
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'baseline' }" 
            @click="handleTabClick('baseline')"
          >
            📋 设计量与采购量
          </button>
        </div>

        <!-- 管件子标签 -->
        <div class="tube-tabs-header" v-else-if="activeCategory === 'fitting'">
          <button 
            type="button" 
            :class="{ active: activeTab === 'fitting' }" 
            @click="handleTabClick('fitting')"
          >
            🔧 管件发货与到货记录
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'fitting_baseline' }" 
            @click="handleTabClick('fitting_baseline')"
          >
            📋 设计量与采购量
          </button>
        </div>
      </div>

      <!-- Tab内容区域 -->
      <div class="tube-tab-content-wrap" v-if="selectedSection1Id">
        
        <!-- Tab 1: 三日计划填报 -->
        <div v-if="activeTab === 'plan'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>未来三日滚动计划</h2>
                <span class="panel-hint">按起始日期连续生成三天滚动计划。建议从右侧快捷区进行批量填报。计量单位：米。</span>
              </div>
              <button
                type="button"
                class="primary-button"
                :disabled="planLoading || savePlanLoading || !selectedSection1Id || !canSubmitCurrentProject || planEditableDays <= 0"
                @click="savePlanMatrix"
              >
                {{ savePlanLoading ? '提交中...' : '提交三日计划量' }}
              </button>
            </div>

            <!-- 严格顺序填报流程锁拦截横幅 -->
            <div v-if="strictPlanningFlowControl && !isUsageSubmitted" class="flow-gateway-banner animate-slide-down">
              <span class="gateway-icon">🔒</span>
              <div class="gateway-desc">
                <strong>首二日流程管控锁已激活</strong>
                <span>由于当前{{ modeLabels.section_1 }}前日实际消耗尚未结清上报，为保证盈缺预测100%可靠，滚动第三日填报已被自动锁定。</span>
              </div>
              <button type="button" class="gateway-link-btn" @click="handleTabClick('usage')">
                👉 一键去上报前日消耗
              </button>
            </div>

            <!-- 批量粘贴解析利器 -->
            <div 
              class="paste-zone" 
              tabindex="0" 
              title="点击激活后直接按 Ctrl+V 粘贴"
              @paste="handleClipboardPaste"
            >
              <div class="paste-icon">📋</div>
              <div class="paste-desc">
                <strong>智能 Excel 批量粘贴录入区</strong>
                <span>在一线线下 Excel 中选中 [型号, 计划量] 数据块复制后，点击此虚线框内直接按 <b>Ctrl + V</b>，系统将智能提取并匹配填充下方表格</span>
              </div>
            </div>

            <div v-if="planLoading" class="loading-text">正在加载三日计划...</div>
            <div v-else-if="planError" class="error-box">{{ planError }}</div>
            <div v-else-if="!planRows.length" class="empty-box">当前暂无可填报型号。</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>型号</th>
                    <th
                      v-for="(date, index) in planDates"
                      :key="date"
                      :class="{ 'editable-plan-date': isPlanDateEditable(index) }"
                    >
                      {{ date }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in planRows" :key="row.pipeModelId">
                    <td class="cell-text cell-model-name" :title="row.pipeModelName">
                      <div class="model-name-text">{{ row.pipeModelName }}</div>
                      <div class="model-badge-row">
                        <span
                          class="sandbox-trigger-badge"
                          :class="getSandboxTriggerClass(row)"
                          @mouseenter="showSandboxPopover($event, row)"
                          @mouseleave="hideSandboxPopover"
                        >
                          {{ getSandboxTriggerLabel(row) }}
                        </span>
                      </div>
                    </td>
                    <td
                      v-for="(date, index) in planDates"
                      :key="`${row.pipeModelId}-${date}`"
                      :class="{ 'editable-plan-date-cell': isPlanDateEditable(index) }"
                    >
                      <div class="cell-editor" :class="{ 'editable-plan-date-cell': isPlanDateEditable(index) }">
                        <input
                          v-model.number="row.values[date].plannedQty"
                          type="number"
                          min="0"
                          step="1"
                          placeholder="数量"
                          :disabled="!isPlanDateEditable(index) || !canSubmitCurrentProject || (index === 2 && strictPlanningFlowControl && !isUsageSubmitted)"
                        />
                        <input
                          v-model.trim="row.values[date].remarks"
                          type="text"
                          maxlength="120"
                          placeholder="备注"
                          :disabled="!isPlanDateEditable(index) || !canSubmitCurrentProject || (index === 2 && strictPlanningFlowControl && !isUsageSubmitted)"
                        />
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 2: 实际使用消耗填报 -->
        <div v-if="activeTab === 'usage'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>实际消耗与损耗上报</h2>
                <span class="panel-hint">登记采集日（{{ usageDate || '今日' }}）各保温管型号的实际施工消耗与现场损耗。计量单位：米。</span>
              </div>
              <button
                type="button"
                class="primary-button"
                :disabled="usageLoading || saveUsageLoading || !selectedSection1Id || !canSubmitCurrentProject"
                @click="saveUsageSheet"
              >
                {{ saveUsageLoading ? '提交中...' : '提交消耗与损耗数据' }}
              </button>
            </div>

            <!-- 批量粘贴解析利器 -->
            <div 
              class="paste-zone" 
              tabindex="0" 
              title="点击激活后直接按 Ctrl+V 粘贴"
              @paste="handleUsageClipboardPaste"
            >
              <div class="paste-icon">📋</div>
              <div class="paste-desc">
                <strong>智能 Excel 批量粘贴录入区</strong>
                <span>在 Excel 中选中 [型号, 使用量, 损耗量(可选), 备注(可选)] 数据块复制后，点击此虚线框内直接按 <b>Ctrl + V</b>，系统将智能提取并匹配填充下方表格</span>
              </div>
            </div>

            <div v-if="usageLoading" class="loading-text">正在加载实际使用数据...</div>
            <div v-else-if="usageError" class="error-box">{{ usageError }}</div>
            <div v-else-if="!usageRows.length" class="empty-box">当前暂无可填报型号。</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>型号</th>
                    <th>实际使用量（米）</th>
                    <th>实际损耗量（米）</th>
                    <th>备注</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in usageRows" :key="row.pipeModelId">
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td>
                      <input
                        v-model.number="row.usedQty"
                        class="number-input"
                        type="number"
                        min="0"
                        step="1"
                        :disabled="usageActionLoading || !canSubmitCurrentProject"
                      />
                    </td>
                    <td>
                      <input
                        v-model.number="row.lossQty"
                        class="number-input"
                        type="number"
                        min="0"
                        step="1"
                        :disabled="usageActionLoading || !canSubmitCurrentProject"
                      />
                    </td>
                    <td>
                      <input
                        v-model.trim="row.remarks"
                        type="text"
                        maxlength="120"
                        placeholder="备注"
                        :disabled="usageActionLoading || !canSubmitCurrentProject"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 3: 基准量台账 -->
        <div v-if="activeTab === 'baseline'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>{{ modeLabels.section_1 }}设计与采购基准量</h2>
                <span class="panel-hint">展示当前{{ modeLabels.section_1 }}的设计总量与全局计划采购总量，供日常对照。计量单位：米。</span>
              </div>
            </div>

            <div v-if="baselineLoading" class="loading-text">正在加载基准量...</div>
            <div v-else-if="baselineError" class="error-box">{{ baselineError }}</div>
            <div v-else-if="!baselineRows.length" class="empty-box">当前{{ modeLabels.section_1 }}暂无基准量记录。</div>
            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>型号</th>
                    <th>设计总量（米）</th>
                    <th>计划采购总量（米）</th>
                    <th>备注</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in baselineRows" :key="row.pipeModelId">
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td class="cell-number">{{ formatNumber(row.designQuantity) }}</td>
                    <td class="cell-number">{{ formatNumber(row.purchaseQuantity) }}</td>
                    <td class="cell-text" :title="row.remarks || '—'">{{ row.remarks || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 4: 物流到货与施工确认 -->
        <div v-if="activeTab === 'logistics'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>到货与施工接收记录</h2>
                <span class="panel-hint">确认运输车次的安全到站，并录入施工单位的真实物理接收量。计量单位：米。</span>
              </div>
              <div class="toolbar-actions" style="display: flex; gap: 8px;">
                <button type="button" class="btn ghost" :disabled="pendingLoading" @click="resetPendingFilters">重置筛选</button>
                <button type="button" class="primary-button" :disabled="pendingLoading || !selectedSection1Id" @click="applyPendingFilters">
                  {{ pendingLoading ? '查询中...' : '筛选记录' }}
                </button>
                <button v-if="pendingRows.length > 0" type="button" class="btn primary" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #fff !important; border: none !important; font-weight: 600;" @click="showExportModal = true">📥 导出 Excel</button>
              </div>
            </div>

            <!-- 筛选排版 -->
            <div class="filter-grid compact-filter-grid">
              <label class="field field-compact">
                <span>订单号</span>
                <input v-model.trim="pendingFilters.orderNo" type="text" placeholder="输入订单号" />
              </label>
              <label class="field field-compact">
                <span>运输车次号</span>
                <input v-model.trim="pendingFilters.shipmentNo" type="text" placeholder="输入运输车次号" />
              </label>
              <label class="field field-compact">
                <span>过滤型号</span>
                <select v-model="pendingFilters.pipeModelId">
                  <option value="">全部型号</option>
                  <option v-for="model in currentPipeModelOptions" :key="model.pipe_model_id" :value="model.pipe_model_id">
                    {{ model.pipe_model_name || model.pipe_model_id }}
                  </option>
                </select>
              </label>
              <label class="field field-compact">
                <span>发货日期</span>
                <input v-model="pendingFilters.shippedDate" type="date" />
              </label>
              <label class="field field-compact">
                <span>确认到货日期</span>
                <input v-model="pendingFilters.arrivedDate" type="date" />
              </label>
            </div>

            <div v-if="pendingLoading" class="loading-text">正在加载物流确认记录...</div>
            <div v-else-if="pendingError" class="error-box">{{ pendingError }}</div>
            <div v-else-if="!pendingRows.length" class="empty-box">当前没有待物流确认记录。</div>
            <div v-else class="table-wrap logistics-table-wrap">
              <table class="data-table logistics-table">
                <thead>
                  <tr>
                    <th class="cell-status">状态</th>
                    <th>订单号</th>
                    <th>运输车次号</th>
                    <th>车牌号</th>
                    <th>供给主体</th>
                    <th>型号</th>
                    <th>发货量（米）</th>
                    <th>发货时间</th>
                    <th>确认到货时间</th>
                    <th>在途时长</th>
                    <th>确认量（米）</th>
                    <th>确认操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="row in pendingRows" 
                    :key="row.deliveryId" 
                    class="logistics-table-row" 
                    title="点击整行可查看单据全生命周期凭证与发货备注"
                    @click="handleLogisticsRowClick($event, row)"
                  >
                    <td class="cell-status col-status">
                      <div class="status-pill-group">
                        <span 
                          class="status-pill clickable-pill" 
                          :class="row.status === 'pending_diff_approve' ? 'pending_receive' : (row.isTimeoutReceive ? 'pending_warehouse' : row.status)"
                        >
                          {{ row.statusLabel }}
                        </span>
                        <span v-if="row.abnormalFlag" class="status-pill abnormal">
                          {{ getAbnormalLabel(row) }}
                        </span>
                      </div>
                    </td>
                    <td class="cell-code col-code-order"><span class="val-text">{{ row.deliveryCode || row.deliveryId }}</span></td>
                    <td class="cell-code col-code-shipment"><span class="val-text">{{ row.shipmentNo || '—' }}</span></td>
                    <td class="cell-text col-text-plate" :title="row.vehiclePlateNo || '—'"><span class="plate-badge">{{ row.vehiclePlateNo || '—' }}</span></td>
                    <td class="cell-text col-text-supply" :title="row.supplyEntityName"><span class="val-text">🏭 {{ row.supplyEntityName }}</span></td>
                    <td class="cell-text col-text-model" :title="row.pipeModelName"><strong class="val-text" style="color: #1e293b; font-size: 13.5px;">{{ row.pipeModelName }}</strong></td>
                    <td class="cell-number col-shipped-qty"><strong style="color: #2563eb;">{{ formatNumber(row.shippedQty) }} 米</strong></td>
                    <td class="cell-datetime col-shipped-time"><span>{{ formatDateTimeDisplay(row.shippedAt) || '—' }}</span></td>
                    <td class="cell-datetime col-arrived-time"><span>{{ formatDateTimeDisplay(row.arrivedConfirmAt) || '—' }}</span></td>
                    <td class="cell-elapsed col-elapsed"><span>⏱️ {{ formatDeliveryElapsedDisplay(row) }}</span></td>
                    <td class="col-confirm-qty">
                      <div v-if="row.status === 'pending_arrival'" class="stack-controls" style="display: inline-flex; align-items: center; gap: 4px;">
                        <input
                          v-model.number="row.arrivalConfirmQty"
                          type="number"
                          min="0"
                          :max="row.shippedQty"
                          step="1"
                          style="width: 70px; padding: 2px 4px; border: 1px solid #059669; border-radius: 4px; text-align: right; font-weight: bold; color: #047857;"
                        />
                        <span style="font-size: 11px; color: #64748b;">米</span>
                      </div>
                      <div v-else-if="row.status === 'pending_receive'" class="stack-controls" style="display: inline-flex; align-items: center; gap: 4px;">
                        <input
                          v-model.number="row.receiptConfirmQty"
                          type="number"
                          min="0"
                          :max="row.arrivedQty"
                          step="1"
                          style="width: 70px; padding: 2px 4px; border: 1px solid #7c3aed; border-radius: 4px; text-align: right; font-weight: bold; color: #6b21a8;"
                        />
                        <span style="font-size: 11px; color: #64748b;">米</span>
                      </div>
                      <span v-else-if="row.status === 'pending_diff_approve'" class="cell-number" style="color: #f97316; font-weight: bold;">
                        {{ formatNumber(row.receivedQty) }} 米 (待审批)
                      </span>
                      <span v-else class="cell-number" style="color: #059669; font-weight: bold;">{{ formatNumber(row.receivedQty || row.arrivedQty) }} 米</span>
                    </td>
                    <td class="col-action-btns">
                      <div v-if="row.status === 'pending_arrival' || row.status === 'pending_receive'" class="action-stack action-inline">
                        <button
                          type="button"
                          class="primary-button action-button arrival-button"
                          :class="{ 'is-active': canClickArrival(row) }"
                          :disabled="deliveryActionLoadingKey === `arrival-${row.deliveryId}` || !canClickArrival(row)"
                          @click="confirmArrival(row)"
                        >
                          {{
                            deliveryActionLoadingKey === `arrival-${row.deliveryId}`
                              ? '确认中...'
                              : row.status === 'pending_arrival'
                                ? '确认到货'
                                : '到货已确认'
                          }}
                        </button>
                        <button
                          type="button"
                          class="primary-button action-button receipt-button"
                          :class="{ 'is-active': canClickReceipt(row) }"
                          :disabled="deliveryActionLoadingKey === `receipt-${row.deliveryId}` || !canClickReceipt(row)"
                          @click="confirmReceipt(row)"
                        >
                          {{
                            deliveryActionLoadingKey === `receipt-${row.deliveryId}`
                              ? '确认中...'
                              : row.status === 'pending_receive'
                                ? '施工接收'
                                : '等待到货'
                          }}
                        </button>
                      </div>
                      <div v-else-if="row.status === 'pending_diff_approve' && isSiteManager" class="action-stack action-inline">
                        <button
                          type="button"
                          class="primary-button action-button arrival-button is-active"
                          :disabled="deliveryActionLoadingKey === `approve-${row.deliveryId}` || deliveryActionLoadingKey === `reject-${row.deliveryId}`"
                          @click="handleDiffApprove(row, true)"
                        >
                          {{ deliveryActionLoadingKey === `approve-${row.deliveryId}` ? '处理中...' : '同意差异' }}
                        </button>
                        <button
                          type="button"
                          class="primary-button action-button receipt-button"
                          style="border-color: #ef4444; color: #ef4444;"
                          :disabled="deliveryActionLoadingKey === `approve-${row.deliveryId}` || deliveryActionLoadingKey === `reject-${row.deliveryId}`"
                          @click="handleDiffApprove(row, false)"
                        >
                          {{ deliveryActionLoadingKey === `reject-${row.deliveryId}` ? '处理中...' : '驳回并更正' }}
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 5: 本标段管件发货到货记录 -->
        <div v-if="activeTab === 'fitting'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>🔧 管件发货记录</h2>
                <span class="panel-hint">本标段（需求主体）收到的全量管件（弯头、三通、大小头等）发货明细台账。由供给侧调度发货自动联动上报，需求方无需进行任何手工填报。</span>
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button
                  type="button"
                  class="btn ghost"
                  style="height: 34px; padding: 0 12px; font-size: 12.5px; display: flex; align-items: center; gap: 4px; border-color: #cbd5e1; background: #fff; cursor: pointer;"
                  @click="toggleAllDemandFittingGroups(true)"
                >
                  📖 展开全车次
                </button>
                <button
                  type="button"
                  class="btn ghost"
                  style="height: 34px; padding: 0 12px; font-size: 12.5px; display: flex; align-items: center; gap: 4px; border-color: #cbd5e1; background: #fff; cursor: pointer;"
                  @click="toggleAllDemandFittingGroups(false)"
                >
                  📕 折叠全车次
                </button>
                <button
                  type="button"
                  class="btn ghost"
                  style="height: 34px; padding: 0 14px; font-size: 13px; display: flex; align-items: center; gap: 4px; border-color: #cbd5e1; background: #fff; cursor: pointer;"
                  @click="handleFittingQuery"
                >
                  🔄 刷新
                </button>
                <button
                  type="button"
                  class="btn ghost"
                  :disabled="fittingExportLoading || !fittingRows.length"
                  style="height: 34px; padding: 0 14px; font-size: 13px; display: flex; align-items: center; gap: 4px; border-color: #cbd5e1; background: #fff; cursor: pointer;"
                  @click="handleDemandFittingExport"
                >
                  📥 导出本标段台账 (.xlsx)
                </button>
              </div>
            </div>

            <!-- 快捷搜索过滤条 -->
            <div style="display: flex; gap: 12px; margin-bottom: 16px; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 16px; border-radius: 8px; flex-wrap: wrap;">
              <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; max-width: 100%;">
                <span style="font-size: 12px; color: #64748b; font-weight: 500; flex-shrink: 0;">发货日期：</span>
                <input v-model="fittingFilter.startDate" type="date" class="input" style="height: 32px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
                <span style="color: #94a3b8;">至</span>
                <input v-model="fittingFilter.endDate" type="date" class="input" style="height: 32px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
              </div>

              <div style="display: flex; align-items: center; gap: 6px; flex: 1; min-width: 180px;">
                <span style="font-size: 12px; color: #64748b; font-weight: 500; flex-shrink: 0;">关键字：</span>
                <input v-model="fittingFilter.searchKeyword" type="text" placeholder="搜索车牌号/单号/类型/型号/备注..." class="input" style="height: 32px; background: #fff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 10px; font-size: 13px; width: 100%;" @keyup.enter="handleFittingQuery" />
              </div>

              <button type="button" class="btn primary" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 4px; cursor: pointer; flex-shrink: 0;" @click="handleFittingQuery">
                🔍 检索
              </button>
            </div>

            <!-- 数据展示 (按车次卡片折叠) -->
            <div v-if="fittingLoading" class="loading-text">正在读取本标段管件到货记录...</div>
            <div v-else-if="!groupedDemandFittingRows.length" class="empty-box">本标段暂无管件发货历史记录。</div>
            <div v-else style="display: flex; flex-direction: column; gap: 12px;">
              <div 
                v-for="group in groupedDemandFittingRows" 
                :key="group.groupKey"
                style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.02); transition: all 0.2s ease;"
              >
                <!-- 车次汇总卡片表头 (支持点击展开/折叠) -->
                <div 
                  class="fitting-card-header"
                  style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #f8fafc; cursor: pointer; user-select: none; border-bottom: 1px solid #e2e8f0;"
                  @click="toggleDemandFittingGroup(group.groupKey)"
                >
                  <div class="header-left-meta" style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span style="font-size: 14px; color: #4f46e5; transition: transform 0.2s ease; font-weight: bold;" :style="{ transform: isDemandFittingGroupExpanded(group.groupKey) ? 'rotate(90deg)' : 'rotate(0deg)' }">
                      ▶
                    </span>
                    <div style="display: flex; align-items: center; gap: 6px;">
                      <span style="font-size: 11px; color: #64748b; font-weight: 600;">车次:</span>
                      <strong style="color: #4f46e5; font-family: monospace; font-size: 14px;">{{ group.shipmentNo }}</strong>
                    </div>
                    <span class="plate-badge" style="margin-left: 2px; flex-shrink: 0;">{{ group.vehiclePlateNo }}</span>
                    <div style="font-size: 12.5px; color: #334155; display: flex; align-items: center; gap: 4px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="`供给主体: ${group.supplyEntityName}`">
                      <span style="color: #94a3b8; flex-shrink: 0;">🏭 供给方:</span>
                      <strong style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ group.supplyEntityName }}</strong>
                    </div>
                    <span style="font-size: 11.5px; color: #64748b; font-family: monospace; flex-shrink: 0;">{{ formatDateTimeDisplay(group.shippedAt) }}</span>
                  </div>

                  <div class="header-right-meta" style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <!-- 状态 Badge -->
                    <span v-if="group.status === 'shipped' || group.status === 'pending_arrival' || !group.status" class="tag-badge primary" style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-size: 11.5px;">🚚 待到货确认</span>
                    <span v-else-if="group.status === 'arrived' || group.status === 'pending_receive'" class="tag-badge success" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 11.5px;">✅ 待施工接收</span>
                    <span v-else-if="group.status === 'construction_confirmed' || group.status === 'pending_warehouse' || group.status === 'received'" class="tag-badge warning" style="background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; font-size: 11.5px;">👷 待库管归档</span>
                    <span v-else-if="group.status === 'warehouse_confirmed' || group.status === 'completed'" class="tag-badge success" style="background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; font-size: 11.5px;">🏢 库管已归档</span>
                    <span v-else-if="group.status === 'cancelled'" class="tag-badge" style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; font-size: 11.5px;">❌ 已撤销</span>
                    <span v-if="group.hasCancelled && group.status !== 'cancelled'" class="tag-badge" style="background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; font-size: 11.5px;">⚠️ 含已撤销明细</span>

                    <div style="text-align: right; margin-left: 4px;">
                      <span style="font-size: 12px; color: #64748b; margin-right: 6px;">共 {{ group.items.length }} 种管件</span>
                      <strong style="font-size: 13.5px; color: #2563eb;">发货 {{ group.totalShippedQty }} {{ getGroupUnitLabel(group) }} / 已确认到货 {{ group.totalArrivedQty }} {{ getGroupUnitLabel(group) }}</strong>
                    </div>

                    <!-- 流转凭证按钮 -->
                    <button 
                      type="button" 
                      class="btn ghost btn-sm" 
                      style="padding: 4px 10px; font-size: 12px; color: #4f46e5; border-color: #c7d2fe; background: #eef2ff; cursor: pointer; flex-shrink: 0;"
                      @click.stop="showDeliveryDetail(group)"
                    >
                      📜 流转凭证
                    </button>
                  </div>
                </div>

                <!-- 明细展开区 -->
                <div v-show="isDemandFittingGroupExpanded(group.groupKey)" style="padding: 12px 16px; background: #ffffff;">
                  <div v-if="group.shipRemark" style="font-size: 12px; color: #475569; background: #f1f5f9; padding: 6px 12px; border-radius: 6px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px;">
                    <span>📝 整车发货备注：</span>
                    <span style="color: #0f172a;">{{ group.shipRemark }}</span>
                  </div>

                  <!-- 视口横向滚动防护与手机卡片保护层 (Mobile Responsive Wrapper) -->
                  <div class="table-responsive-wrapper" style="overflow-x: auto; width: 100%; -webkit-overflow-scrolling: touch; margin-bottom: 4px;">
                    <table class="data-table demand-fitting-table" style="margin: 0; min-width: 760px; width: 100%; table-layout: fixed; border: 1px solid #edf2f7; border-radius: 6px; font-size: 12.5px;">
                      <thead style="background: #f8fafc;">
                        <tr>
                          <th style="width: 38px; text-align: center;">#</th>
                          <th style="width: 110px;">管件类型</th>
                          <th style="min-width: 200px;">型号 / 规格描述</th>
                          <th style="width: 95px; text-align: right;">发货件数</th>
                          <th style="width: 115px; text-align: right;">到货确认数</th>
                          <th style="width: 125px; text-align: center;">履约状态</th>
                          <th style="width: 135px; text-align: center;">单项确认操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(item, idx) in group.items" :key="item.id" style="vertical-align: middle;">
                          <td class="col-index" style="text-align: center; color: #94a3b8;">{{ idx + 1 }}</td>
                          
                          <td class="col-type">
                            <span v-if="isStandardFittingType(item.fitting_type)" class="tag-badge primary" style="font-size: 11.5px;">{{ item.fitting_type }}</span>
                            <span v-else class="tag-badge warning" style="background: #fff7ed; color: #c2410c; border: 1px solid #ffedd5; font-size: 11.5px;">⚠️ {{ item.fitting_type }}</span>
                          </td>
                          
                          <td class="col-model">
                            <strong style="color: #1e293b;">{{ item.model_spec }}</strong>
                            <div style="font-family: monospace; font-size: 11px; color: #94a3b8;">单号: {{ item.order_no }}</div>
                          </td>
                          
                          <td class="col-shipped" style="text-align: right; font-weight: bold; color: #2563eb;">
                            <span class="mobile-lbl" style="display: none;">发货件数: </span>
                            <span>{{ item.shipped_qty }} {{ item.unit || '个' }}</span>
                          </td>
                          
                          <!-- 到货确认数量设定（默认等于发货数量，允许单条直接微调） -->
                          <td class="col-arrived" style="text-align: right;">
                            <span class="mobile-lbl" style="display: none;">到货确认: </span>
                            <div v-if="item.status === 'shipped' || item.status === 'pending_arrival' || !item.status" style="display: inline-flex; align-items: center; gap: 4px;">
                              <input 
                                type="number" 
                                v-model.number="item.tempArrivedQty"
                                min="1"
                                :max="item.shipped_qty"
                                step="1"
                                :disabled="!canConfirmArrival"
                                style="width: 60px; padding: 2px 4px; border: 1px solid #059669; border-radius: 4px; text-align: right; font-weight: bold; color: #047857; font-size: 12px;"
                              />
                              <span style="font-size: 11px; color: #64748b;">{{ item.unit || '个' }}</span>
                            </div>
                            <span v-else style="font-weight: bold; color: #059669;">
                              {{ item.arrived_qty !== undefined && item.arrived_qty !== null ? item.arrived_qty : item.shipped_qty }} {{ item.unit || '个' }}
                            </span>
                          </td>

                          <!-- 明细单项状态 Badge -->
                          <td class="col-status" style="text-align: center;">
                            <span v-if="item.status === 'shipped' || item.status === 'pending_arrival' || !item.status" class="tag-badge primary" style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-size: 11px; padding: 1px 6px;">🚚 待到货确认</span>
                            <span v-else-if="item.status === 'arrived' || item.status === 'pending_receive'" class="tag-badge success" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 11px; padding: 1px 6px;">✅ 待施工接收</span>
                            <span v-else-if="item.status === 'construction_confirmed' || item.status === 'pending_warehouse' || item.status === 'received'" class="tag-badge warning" style="background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; font-size: 11px; padding: 1px 6px;">👷 待库管归档</span>
                            <span v-else-if="item.status === 'warehouse_confirmed' || item.status === 'completed'" class="tag-badge success" style="background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; font-size: 11px; padding: 1px 6px;">🏢 库管已归档</span>
                            <span v-else-if="item.status === 'cancelled'" class="tag-badge" style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; font-size: 11px; padding: 1px 6px;">❌ 已撤销</span>
                          </td>

                          <!-- 明细项独立确认操作列 -->
                          <td class="col-action" style="text-align: center;">
                            <!-- 1. 待到货状态下的确认到货按钮 -->
                            <div v-if="item.status === 'shipped' || item.status === 'pending_arrival' || !item.status" style="display: flex; justify-content: center; gap: 4px;">
                              <button 
                                type="button" 
                                class="btn primary btn-sm" 
                                style="padding: 2px 8px; font-size: 11.5px; background: #059669; border-color: #059669; color: #fff; cursor: pointer;"
                                :disabled="item.submitting || !canConfirmArrival"
                                :title="canConfirmArrival ? '确认现场到货' : '仅现场负责人可确认到货'"
                                @click.stop="handleConfirmSingleItemArrival(item)"
                              >
                                {{ item.submitting ? '提交中...' : '🚚 确认到货' }}
                              </button>
                              <button 
                                type="button" 
                                class="btn ghost btn-sm" 
                                style="padding: 2px 6px; font-size: 11.5px; color: #059669; border-color: #a7f3d0;"
                                @click.stop="openFittingArrivalModalForSingle(item, group)"
                                :disabled="!canConfirmArrival"
                                title="补充到货备注"
                              >
                                💬 备注
                              </button>
                            </div>

                            <!-- 2. 到货状态下的施工接收按钮 -->
                            <div v-else-if="item.status === 'arrived' || item.status === 'pending_receive'" style="display: flex; justify-content: center; gap: 4px;">
                              <button 
                                type="button" 
                                class="btn primary btn-sm" 
                                style="padding: 2px 8px; font-size: 11.5px; background: #7c3aed; border-color: #7c3aed; color: #fff; cursor: pointer;"
                                :disabled="item.submitting || !canConfirmReceipt"
                                :title="canConfirmReceipt ? '确认施工接收' : '仅施工单位可确认接收'"
                                @click.stop="handleConfirmSingleItemConstruction(item)"
                              >
                                {{ item.submitting ? '提交中...' : '👷 施工接收' }}
                              </button>
                              <button 
                                type="button" 
                                class="btn ghost btn-sm" 
                                style="padding: 2px 6px; font-size: 11.5px; color: #7c3aed; border-color: #ddd6fe;"
                                @click.stop="openFittingConstructionModalForSingle(item, group)"
                                :disabled="!canConfirmReceipt"
                                title="补充领用备注"
                              >
                                💬 备注
                              </button>
                            </div>

                            <!-- 3. 已完全流转状态 -->
                            <span v-else style="font-size: 11px; color: #16a34a; font-weight: 600;">✓ 节点流程完成</span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            <!-- 管件情况决策透视卡片 -->
            <div v-if="fittingRows.length > 0" style="margin-top: 15px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px 18px; border-radius: 8px; font-size: 13px; color: #334155; line-height: 1.8;">
              <div style="font-weight: 700; color: #0f172a; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                <span>💡 本标段管件物资统计：</span>
              </div>
              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px 14px;">
                <div style="background: #fff; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                  <span>🚚 累计发货车次</span>
                  <strong style="color: #0f172a;">{{ demandFittingBatches }} 车/批</strong>
                </div>
                <div style="background: #fff; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                  <span>📦 收到管件总量</span>
                  <strong style="color: #2563eb;">{{ demandFittingTotalQty }} 个</strong>
                </div>
                <div style="background: #fff; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                  <span>🟢 常用标准管件</span>
                  <strong style="color: #16a34a;">{{ demandFittingStandardQty }} 个</strong>
                </div>
                <div style="background: #fff; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                  <span>🟧 非常用/异形管件</span>
                  <strong style="color: #ea580c;">{{ demandFittingNonStandardQty }} 个</strong>
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- Tab 6: 需求主体管件基准设计量与计划采购量台账 -->
        <div v-if="activeTab === 'fitting_baseline'" class="tab-pane">
          <section class="card elevated tab-card">
            <div class="panel-title-row">
              <div>
                <h2>🔩 {{ currentSection1Name }}管件设计量与计划采购量</h2>
                <span class="panel-hint">展示当前{{ modeLabels.section_1 }}在基准数据库（tube.tube_fitting_baseline）中的全量标准化管件与物料基准明细，供施工核对与物资计划追踪。</span>
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button
                  type="button"
                  class="btn ghost"
                  style="height: 34px; padding: 0 14px; font-size: 13px; display: flex; align-items: center; gap: 4px; border-color: #cbd5e1; background: #fff; cursor: pointer;"
                  @click="loadFittingBaseline"
                >
                  🔄 刷新数据
                </button>
                <button
                  type="button"
                  class="btn ghost"
                  :disabled="!fittingBaselineRows.length"
                  style="height: 34px; padding: 0 14px; font-size: 13px; display: flex; align-items: center; gap: 4px; border-color: #cbd5e1; background: #fff; cursor: pointer;"
                  @click="exportDemandFittingBaseline"
                >
                  📥 导出 Excel
                </button>
              </div>
            </div>

            <!-- 数据统计微看板 -->
            <div class="summary-row baseline-summary" style="margin-top: 12px; margin-bottom: 12px;">
              <span class="summary-chip">📍 当前主体：<strong>{{ currentSection1Name }}</strong></span>
              <span class="summary-chip">
                🔍 命中种类：<strong>{{ filteredFittingBaselineRows.length }}</strong> / {{ fittingBaselineRows.length }} 种
              </span>
              <span class="summary-chip">
                📐 命中设计量：<strong>{{ formatNumber(fittingBaselineStats.filteredDesignQty) }}</strong>
                <small v-if="filteredFittingBaselineRows.length !== fittingBaselineRows.length" style="color: #64748b; font-weight: normal; margin-left: 4px;">(总: {{ formatNumber(fittingBaselineStats.totalDesignQty) }})</small>
              </span>
              <span class="summary-chip">
                📦 命中采购量：<strong>{{ formatNumber(fittingBaselineStats.filteredPurchaseQty) }}</strong>
                <small v-if="filteredFittingBaselineRows.length !== fittingBaselineRows.length" style="color: #64748b; font-weight: normal; margin-left: 4px;">(总: {{ formatNumber(fittingBaselineStats.totalPurchaseQty) }})</small>
              </span>
            </div>

            <!-- 🔩 多维多选下拉筛选工具栏 (Clean Multi-Select Dropdown Toolbar) -->
            <div class="fitting-filter-toolbar" @click.stop>
              <!-- 1. 系统类型下拉框 -->
              <div class="ms-dropdown-container" v-if="availableFittingFacets.systemTypes.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.systemTypes.length > 0, 'is-open': activeDropdown === 'systemTypes' }"
                  @click="toggleFittingDropdown('systemTypes', $event)"
                >
                  <span class="ms-label-icon">💧</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('systemTypes', '系统类型') }}</span>
                  <span v-if="fittingFilters.systemTypes.length > 1" class="ms-badge">{{ fittingFilters.systemTypes.length }}</span>
                  <span v-if="fittingFilters.systemTypes.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('systemTypes')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'systemTypes'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择系统类型</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('systemTypes', availableFittingFacets.systemTypes)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('systemTypes')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.systemTypes"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('systemTypes', item.value) }"
                      @click.stop="toggleFittingFilterItem('systemTypes', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('systemTypes', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('systemTypes', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 2. 物理类别下拉框 -->
              <div class="ms-dropdown-container" v-if="availableFittingFacets.categories.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.categories.length > 0, 'is-open': activeDropdown === 'categories' }"
                  @click="toggleFittingDropdown('categories', $event)"
                >
                  <span class="ms-label-icon">🔩</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('categories', '物理类别') }}</span>
                  <span v-if="fittingFilters.categories.length > 1" class="ms-badge">{{ fittingFilters.categories.length }}</span>
                  <span v-if="fittingFilters.categories.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('categories')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'categories'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择物理类别</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('categories', availableFittingFacets.categories)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('categories')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.categories"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('categories', item.value) }"
                      @click.stop="toggleFittingFilterItem('categories', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('categories', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('categories', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 3. 主径DN下拉框 -->
              <div class="ms-dropdown-container" v-if="availableFittingFacets.mainDns.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.mainDns.length > 0, 'is-open': activeDropdown === 'mainDns' }"
                  @click="toggleFittingDropdown('mainDns', $event)"
                >
                  <span class="ms-label-icon">📏</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('mainDns', '主径DN', 'DN') }}</span>
                  <span v-if="fittingFilters.mainDns.length > 1" class="ms-badge">{{ fittingFilters.mainDns.length }}</span>
                  <span v-if="fittingFilters.mainDns.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('mainDns')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'mainDns'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择主径口径</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('mainDns', availableFittingFacets.mainDns)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('mainDns')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.mainDns"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('mainDns', item.value) }"
                      @click.stop="toggleFittingFilterItem('mainDns', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('mainDns', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('mainDns', item.value)"
                      />
                      <span class="ms-item-name">DN{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 4. 角度下拉框 (弯头) -->
              <div class="ms-dropdown-container" v-if="shouldShowAngleAndBending && availableFittingFacets.angles.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.angles.length > 0, 'is-open': activeDropdown === 'angles' }"
                  @click="toggleFittingDropdown('angles', $event)"
                >
                  <span class="ms-label-icon">📐</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('angles', '角度', '', '°') }}</span>
                  <span v-if="fittingFilters.angles.length > 1" class="ms-badge">{{ fittingFilters.angles.length }}</span>
                  <span v-if="fittingFilters.angles.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('angles')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'angles'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择弯头角度</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('angles', availableFittingFacets.angles)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('angles')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.angles"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('angles', item.value) }"
                      @click.stop="toggleFittingFilterItem('angles', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('angles', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('angles', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}°</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 5. 弯曲半径倍数下拉框 (弯头) -->
              <div class="ms-dropdown-container" v-if="shouldShowAngleAndBending && availableFittingFacets.bendingRatios.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.bendingRatios.length > 0, 'is-open': activeDropdown === 'bendingRatios' }"
                  @click="toggleFittingDropdown('bendingRatios', $event)"
                >
                  <span class="ms-label-icon">🔄</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('bendingRatios', '弯曲半径', '', 'DN') }}</span>
                  <span v-if="fittingFilters.bendingRatios.length > 1" class="ms-badge">{{ fittingFilters.bendingRatios.length }}</span>
                  <span v-if="fittingFilters.bendingRatios.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('bendingRatios')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'bendingRatios'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择弯曲半径倍数</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('bendingRatios', availableFittingFacets.bendingRatios)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('bendingRatios')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.bendingRatios"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('bendingRatios', item.value) }"
                      @click.stop="toggleFittingFilterItem('bendingRatios', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('bendingRatios', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('bendingRatios', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}DN</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 6. 次径/支管DN下拉框 (三通/变径) -->
              <div class="ms-dropdown-container" v-if="shouldShowSubDn && availableFittingFacets.subDns.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.subDns.length > 0, 'is-open': activeDropdown === 'subDns' }"
                  @click="toggleFittingDropdown('subDns', $event)"
                >
                  <span class="ms-label-icon">🔀</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('subDns', '次径DN', 'DN') }}</span>
                  <span v-if="fittingFilters.subDns.length > 1" class="ms-badge">{{ fittingFilters.subDns.length }}</span>
                  <span v-if="fittingFilters.subDns.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('subDns')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'subDns'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择次径/支管口径</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('subDns', availableFittingFacets.subDns)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('subDns')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.subDns"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('subDns', item.value) }"
                      @click.stop="toggleFittingFilterItem('subDns', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('subDns', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('subDns', item.value)"
                      />
                      <span class="ms-item-name">DN{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 7. 公称压力下拉框 (阀门/承压) -->
              <div class="ms-dropdown-container" v-if="shouldShowPressure && availableFittingFacets.pressures.length > 0">
                <button
                  type="button"
                  class="ms-dropdown-trigger"
                  :class="{ 'has-value': fittingFilters.pressures.length > 0, 'is-open': activeDropdown === 'pressures' }"
                  @click="toggleFittingDropdown('pressures', $event)"
                >
                  <span class="ms-label-icon">🛡️</span>
                  <span class="ms-label-text">{{ getFittingFilterSummary('pressures', '公称压力') }}</span>
                  <span v-if="fittingFilters.pressures.length > 1" class="ms-badge">{{ fittingFilters.pressures.length }}</span>
                  <span v-if="fittingFilters.pressures.length > 0" class="ms-clear-btn" title="清空" @click.stop="clearFittingFilterDimension('pressures')">✕</span>
                  <span class="ms-arrow">▾</span>
                </button>
                <div v-if="activeDropdown === 'pressures'" class="ms-dropdown-menu">
                  <div class="ms-menu-header">
                    <span class="ms-menu-title">选择公称压力</span>
                    <div class="ms-menu-actions">
                      <a href="javascript:void(0)" @click.stop="selectAllFittingFilterDimension('pressures', availableFittingFacets.pressures)">全选</a>
                      <span class="sep">|</span>
                      <a href="javascript:void(0)" @click.stop="clearFittingFilterDimension('pressures')">清空</a>
                    </div>
                  </div>
                  <div class="ms-menu-list">
                    <label
                      v-for="item in availableFittingFacets.pressures"
                      :key="item.value"
                      class="ms-menu-item"
                      :class="{ checked: isFittingFilterSelected('pressures', item.value) }"
                      @click.stop="toggleFittingFilterItem('pressures', item.value)"
                    >
                      <input
                        type="checkbox"
                        :checked="isFittingFilterSelected('pressures', item.value)"
                        @click.stop
                        @change="toggleFittingFilterItem('pressures', item.value)"
                      />
                      <span class="ms-item-name">{{ item.value }}</span>
                      <span class="ms-item-count">({{ item.count }})</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- 8. 关键词搜索框 -->
              <div class="ms-search-box">
                <input
                  v-model="fittingFilters.searchKeyword"
                  type="text"
                  class="input"
                  placeholder="搜索标准名称 / 规格型号 / 备注..."
                  style="height: 34px; padding: 0 10px; font-size: 13px; border-radius: 8px;"
                />
              </div>

              <!-- 9. 重置按钮 -->
              <button
                v-if="activeFittingFilterTags.length > 0"
                type="button"
                class="btn ghost compact-btn reset-filter-btn"
                title="重置全部筛选条件"
                @click="clearAllFittingFilters"
              >
                🔄 重置
              </button>
            </div>

            <div v-if="fittingBaselineLoading" class="loading-text">正在从数据库加载管件基准量...</div>
            <div v-else-if="fittingBaselineError" class="error-box">{{ fittingBaselineError }}</div>
            <div v-else-if="!filteredFittingBaselineRows.length" class="empty-box">
              {{ fittingBaselineRows.length ? '未找到符合筛选条件的管件记录。' : `当前${modeLabels.section_1}暂无管件基准量记录。` }}
            </div>
            <div v-else class="table-wrap" style="overflow-x: auto;">
              <table class="data-table">
                <thead>
                  <tr>
                    <th style="width: 50px; text-align: center;">序号</th>
                    <th style="width: 80px; text-align: center;">系统类型</th>
                    <th style="width: 90px;">物理类别</th>
                    <th style="min-width: 150px;">标准名称</th>
                    <th style="min-width: 160px;">型号规格</th>
                    <th style="min-width: 120px;">细分规格/子型号</th>
                    <th style="width: 75px; text-align: right;">主径DN</th>
                    <th style="width: 75px; text-align: right;">次径DN</th>
                    <th style="width: 75px; text-align: right;">角度(°)</th>
                    <th style="width: 80px; text-align: right;">弯曲倍数</th>
                    <th style="width: 110px;">阀门/公称压力</th>
                    <th style="min-width: 130px;">原型号规格</th>
                    <th style="min-width: 130px;">原名称</th>
                    <th style="width: 60px; text-align: center;">单位</th>
                    <th style="width: 105px; text-align: right; color: #1d4ed8;">设计使用量</th>
                    <th style="width: 115px; text-align: right; color: #059669;">计划采购总量</th>
                    <th style="min-width: 140px;">说明备注</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in filteredFittingBaselineRows" :key="row.id || idx">
                    <td class="cell-text" style="text-align: center; color: #94a3b8;">{{ idx + 1 }}</td>
                    <td class="cell-text" style="text-align: center;">
                      <span :style="{
                        fontSize: '11.5px',
                        padding: '2px 7px',
                        borderRadius: '6px',
                        background: row.system_type === '高温水' ? '#eff6ff' : '#ecfdf5',
                        color: row.system_type === '高温水' ? '#2563eb' : '#059669',
                        fontWeight: '600'
                      }">
                        {{ row.system_type || '高温水' }}
                      </span>
                    </td>
                    <td class="cell-text" style="font-weight: 600;">{{ row.category || row.fitting_type || '管件' }}</td>
                    <td class="cell-text" :title="row.standard_name">{{ row.standard_name || '—' }}</td>
                    <td class="cell-text font-mono" style="font-weight: 500;" :title="row.model_spec">{{ row.model_spec }}</td>
                    <td class="cell-text font-mono" :title="row.sub_model_spec">{{ row.sub_model_spec || '—' }}</td>
                    <td class="cell-number">{{ row.main_dn != null ? row.main_dn : '—' }}</td>
                    <td class="cell-number">{{ row.sub_dn != null ? row.sub_dn : '—' }}</td>
                    <td class="cell-number">{{ row.angle != null ? row.angle : '—' }}</td>
                    <td class="cell-number">{{ row.bending_radius_ratio != null ? row.bending_radius_ratio : '—' }}</td>
                    <td class="cell-text" style="font-size: 12px;" :title="`${row.valve_model || ''} ${row.pressure_rating || ''}`">
                      {{ [row.valve_model, row.pressure_rating].filter(Boolean).join(' / ') || '—' }}
                    </td>
                    <td class="cell-text font-mono" :title="row.raw_model_spec">{{ row.raw_model_spec || '—' }}</td>
                    <td class="cell-text" :title="row.raw_name">{{ row.raw_name || '—' }}</td>
                    <td class="cell-text" style="text-align: center;">{{ row.unit || '个' }}</td>
                    <td class="cell-number" style="font-weight: 700; color: #1d4ed8;">{{ formatNumber(row.design_qty) }}</td>
                    <td class="cell-number" style="font-weight: 700; color: #059669;">{{ formatNumber(row.purchase_plan_qty) }}</td>
                    <td class="cell-text" :title="row.remark">{{ row.remark || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

      </div>

      <!-- 初始未选择提示卡 -->
      <section v-else class="card elevated select-hint-card">
        <div class="hint-content">
          <div class="hint-icon">📂</div>
          <h3>请首先选择要操作的{{ modeLabels.section_1 }}</h3>
          <p>在上方“工作台全局筛选”下拉框中选择具体的{{ modeLabels.section_1 }}后，系统将为您正式解锁三日滚动计划、使用量填报及到货到货确认等多标签管理模块。</p>
        </div>
      </section>

    </main>
    <!-- 导出配置与 XLSX 导出组件 -->
    <ExportSettingsModal
      :show="showExportModal"
      :columns="exportColumns"
      :data="exportAllPendingRows"
      :filtered-data="exportPendingRows"
      default-filename="保温管到货与接收确认记录"
      @close="showExportModal = false"
    />

    <!-- 全局操作反馈 Toast 弹窗 (SaaS Premium Floating Toast) -->
    <div v-if="toastVisible" :class="['global-toast', toastType]">
      <span class="toast-icon">{{ toastType === 'success' ? '✅' : '❌' }}</span>
      <span class="toast-text">{{ toastText }}</span>
    </div>

    <!-- 负库存硬性拦截磨砂玻璃警告弹窗 (Premium Glassmorphism Usage Block Modal) -->
    <Transition name="fade">
      <div v-if="blockModalVisible && blockModalData" class="block-modal-overlay">
        <div class="block-modal-container">
          <!-- 头部警告区 -->
          <div class="block-modal-header">
            <span class="block-warning-icon">🚨</span>
            <h3>实际使用量填报硬性拦截</h3>
            <p class="block-warning-desc">现场实际库存量不允许填报至负数，您的保存申请已被系统安全拦截！</p>
          </div>
          
          <!-- 参数对照表格卡片 -->
          <div class="block-modal-metrics">
            <div class="metric-block-card">
              <span class="lbl">被拦截规格</span>
              <span class="val model-val">{{ blockModalData.pipeModelId }}</span>
            </div>
            <div class="metric-block-card">
              <span class="lbl">现场累计已到货</span>
              <span class="val green-val">{{ formatNumber(blockModalData.totalArrived) }} <small>米</small></span>
            </div>
            <div class="metric-block-card">
              <span class="lbl">拟上报消耗总量</span>
              <span class="val red-val">{{ formatNumber(blockModalData.expectedTotalUsage) }} <small>米</small></span>
              <span v-if="blockModalData.expectedLossOnly > 0" class="sub-lbl-detail">
                (使用: {{ formatNumber(blockModalData.expectedUsageOnly) }} | 损耗: {{ formatNumber(blockModalData.expectedLossOnly) }})
              </span>
            </div>
            <div class="metric-block-card warning">
              <span class="lbl">超前账面亏空</span>
              <span class="val orange-val">{{ formatNumber(blockModalData.shortage) }} <small>米</small></span>
            </div>
          </div>

          <!-- 物流在途提示 -->
          <div class="block-logistics-card" :class="{ 'has-transit': blockModalData.pendingArrival > 0 }">
            <div v-if="blockModalData.pendingArrival > 0" class="logistics-info">
              <span class="logistics-icon">🚚</span>
              <div class="logistics-detail">
                <h4>运输链好消息：正有在途物资！</h4>
                <p>检测到目前正有 <strong>{{ formatNumber(blockModalData.pendingArrival) }} 米</strong> 保温管已从工厂发货，正处于<strong>“已发货待到货确认”</strong>在途状态！</p>
                <p class="action-guide">业务纠偏指引：请先前往“到货与施工接收记录”标签下，对这批物资执行<strong>【到货确认】</strong>操作，补充账面现场库存，再返回提交实际使用量。</p>
              </div>
            </div>
            <div v-else class="logistics-info no-transit">
              <span class="logistics-icon">⚠️</span>
              <div class="logistics-detail">
                <h4>物流警告：暂无在途物资！</h4>
                <p>检测到目前针对该规格<strong>暂无在途运输车次</strong>，无法通过到货确认进行现场库存的自主补充。</p>
                <p class="action-guide danger">业务纠偏指引：请先联系发货工厂或主管库管员安排紧急物资发货，待车次录入后再执行到货确认。</p>
              </div>
            </div>
          </div>

          <!-- 底部按钮区 -->
          <div class="block-modal-actions">
            <button 
              v-if="blockModalData.pendingArrival > 0" 
              type="button" 
              class="btn primary handle-btn" 
              @click="handleGotoLogistics"
            >
              去处理在途物资 (到货确认)
            </button>
            <button 
              type="button" 
              class="btn ghost cancel-btn" 
              @click="blockModalVisible = false"
            >
              {{ blockModalData.pendingArrival > 0 ? '稍后处理' : '我知道了' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 施工少接收备注输入弹窗 -->
    <Transition name="fade">
      <div v-if="receiptRemarkModalVisible && receiptRemarkModalData.row" class="block-modal-overlay">
        <div class="block-modal-container" style="max-width: 500px;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;">
            <span class="block-warning-icon">📝</span>
            <h3 style="margin-top: 5px; color: #fff;">少到货/少接收备注确认</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">检测到您的实收量小于到货确认量，系统强制需要填写差异备注原因（不少于 10 个字符）</p>
          </div>
          
          <div class="block-modal-metrics" style="grid-template-columns: repeat(2, 1fr); padding: 15px; gap: 10px;">
            <div class="metric-block-card" style="grid-column: span 2;">
              <span class="lbl">保温管规格</span>
              <span class="val model-val" style="font-size: 13px;">{{ receiptRemarkModalData.row.pipeModelName }}</span>
            </div>
            <div class="metric-block-card">
              <span class="lbl">确认到货量</span>
              <span class="val green-val" style="font-size: 18px;">{{ formatNumber(receiptRemarkModalData.limitQty) }} <small>米</small></span>
            </div>
            <div class="metric-block-card">
              <span class="lbl">施工拟收量</span>
              <span class="val red-val" style="font-size: 18px; color: #f97316;">{{ formatNumber(receiptRemarkModalData.receivedQty) }} <small>米</small></span>
            </div>
          </div>

          <div style="padding: 0 20px 15px 20px; text-align: left;">
            <label style="display: block; font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px;">
              ⚠️ 请输入具体的差异原因（不得少于10个字）：
            </label>
            <textarea
              v-model="receiptRemarkModalData.remark"
              placeholder="例如：运输途中破损2米；现场测量短缺1米，管厂发货短少... （字数不少于10字）"
              rows="3"
              style="width: 100%; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; font-size: 12px; resize: none; box-sizing: border-box; outline: none;"
            ></textarea>
            <div style="font-size: 11px; color: #94a3b8; text-align: right; margin-top: 4px;">
              当前字数：<strong :style="{ color: receiptRemarkModalData.remark.trim().length >= 10 ? '#10b981' : '#ef4444' }">
                {{ receiptRemarkModalData.remark.trim().length }}
              </strong> / 最少 10 字
            </div>
          </div>

          <div class="block-modal-actions" style="margin-top: 5px;">
            <button 
              type="button" 
              class="btn primary" 
              style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important; width: 100%; color: #fff !important; font-weight: 600;"
              :disabled="receiptRemarkModalData.remark.trim().length < 10"
              @click="submitReceiptWithRemark"
            >
              提交接收并挂起差异审批
            </button>
            <button 
              type="button" 
              class="btn ghost" 
              style="width: 100%; margin-top: 5px;"
              @click="receiptRemarkModalVisible = false"
            >
              取消
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 订单流转备注及全生命周期详情弹窗 -->
    <Transition name="fade">
      <div v-if="deliveryDetailModalVisible && deliveryDetailModalData" class="block-modal-overlay" @click.self="deliveryDetailModalVisible = false">
        <div class="block-modal-container" style="max-width: 600px; max-height: 85vh; overflow-y: auto;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #4f46e5 0%, #312e81 100%) !important;">
            <span class="block-warning-icon">🚚</span>
            <h3 style="margin-top: 5px; color: #fff;">订单全生命周期流转凭证</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">单号：{{ deliveryDetailModalData.deliveryCode || deliveryDetailModalData.deliveryId }}</p>
          </div>
          
          <!-- 信息概述 -->
          <div class="block-modal-metrics" style="grid-template-columns: repeat(3, 1fr); padding: 15px; gap: 8px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
            <div class="metric-block-card">
              <span class="lbl">车牌号</span>
              <span class="val" style="font-size: 13px; font-weight: bold; color: #1e293b;">{{ deliveryDetailModalData.vehiclePlateNo || '—' }}</span>
            </div>
            <div class="metric-block-card" style="grid-column: span 2;">
              <span class="lbl">规格型号</span>
              <span class="val model-val" style="font-size: 11px; line-height: 1.3;" :title="deliveryDetailModalData.pipeModelName">{{ deliveryDetailModalData.pipeModelName }}</span>
            </div>
            <div v-if="deliveryDetailModalData.shipRemark" class="metric-block-card" style="grid-column: span 3; background: #eff6ff; border: 1px solid #bfdbfe; text-align: left; padding: 8px 12px; border-radius: 6px;">
              <span class="lbl" style="color: #1d4ed8; font-weight: 600; font-size: 11px; display: flex; align-items: center; gap: 4px;">📝 供给侧发货备注</span>
              <span class="val" style="font-size: 12px; color: #1e3a8a; font-weight: 500; white-space: pre-wrap; word-break: break-all; margin-top: 2px;">{{ deliveryDetailModalData.shipRemark }}</span>
            </div>
          </div>

          <!-- 本车装载物品明细清单（区分管件模式与直管模式） -->
          <div v-if="deliveryDetailModalData.itemsList && deliveryDetailModalData.itemsList.length" style="padding: 14px 15px; background: #ffffff; border-bottom: 1px solid #e2e8f0; width: 100%; box-sizing: border-box; flex-shrink: 0 !important; min-height: 120px !important; overflow-x: auto;">
            <div style="font-size: 12.5px; font-weight: bold; color: #1e293b; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
              <span>{{ isFittingDeliveryModal ? '📦 本车次搭载管件清单及履约明细' : '📦 本车次保温管发货及履约明细' }}</span>
              <span style="font-size: 11px; color: #4f46e5; background: #eef2ff; padding: 3px 10px; border-radius: 99px; border: 1px solid #c7d2fe; font-weight: 600;">
                {{ isFittingDeliveryModal ? `共 ${deliveryDetailModalData.totalTypesCount} 种规格 / 合计 ${formatNumber(deliveryDetailModalData.shippedQty)} ${getModalUnitLabel(deliveryDetailModalData)}` : `装载总长度 ${formatNumber(deliveryDetailModalData.shippedQty)} 米` }}
              </span>
            </div>
            <table style="margin: 0; width: 100%; min-width: 480px; min-height: 70px; table-layout: fixed; border-collapse: collapse; border: 1px solid #edf2f7; border-radius: 6px; font-size: 11.5px; box-sizing: border-box;">
              <thead>
                <tr style="background: #f1f5f9; color: #475569;">
                  <th style="padding: 6px 4px; text-align: center; width: 28px;">#</th>
                  <th style="padding: 6px 6px; text-align: left; width: 110px;">{{ isFittingDeliveryModal ? '管件类型' : '物资类别' }}</th>
                  <th style="padding: 6px 6px; text-align: left; width: 140px;">{{ isFittingDeliveryModal ? '规格型号' : '保温管规格描述' }}</th>
                  <th style="padding: 6px 6px; text-align: right; width: 65px;">{{ isFittingDeliveryModal ? '发货件数' : '发货长度' }}</th>
                  <th style="padding: 6px 6px; text-align: right; width: 65px;">{{ isFittingDeliveryModal ? '实到件数' : '实到长度' }}</th>
                  <th style="padding: 6px 6px; text-align: left;">备注</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(it, idx) in deliveryDetailModalData.itemsList" :key="it.id || idx" style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 6px 4px; text-align: center; color: #94a3b8;">{{ idx + 1 }}</td>
                  <td style="padding: 6px 6px; font-weight: 600; color: #0f172a; word-break: break-word;">{{ isFittingDeliveryModal ? (it.fitting_type || it.fittingType || '管件') : '保温管' }}</td>
                  <td style="padding: 6px 6px; color: #334155; font-family: monospace; word-break: break-word;">{{ isFittingDeliveryModal ? (it.model_spec || it.modelSpec || '—') : (it.pipe_model_id || it.pipeModelName || deliveryDetailModalData.pipeModelName || '未填') }}</td>
                  <td style="padding: 6px 6px; text-align: right; font-weight: bold; color: #2563eb; white-space: nowrap;">{{ formatNumber(it.shipped_qty || it.shippedQty) }} {{ it.unit || (isFittingDeliveryModal ? '个' : '米') }}</td>
                  <td style="padding: 6px 6px; text-align: right; font-weight: bold; white-space: nowrap;">
                    <span v-if="Boolean(deliveryDetailModalData.arrivedConfirmAt || (it.status && it.status !== 'shipped' && it.status !== 'pending_arrival') || (deliveryDetailModalData.status && deliveryDetailModalData.status !== 'shipped' && deliveryDetailModalData.status !== 'pending_arrival'))" style="color: #059669;">
                      {{ formatNumber(it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : (it.arrivedQty !== undefined && it.arrivedQty !== null ? it.arrivedQty : 0)) }} {{ it.unit || (isFittingDeliveryModal ? '个' : '米') }}
                    </span>
                    <span v-else style="color: #94a3b8; font-weight: normal;">—</span>
                  </td>
                  <td style="padding: 6px 6px; color: #64748b; font-style: italic; word-break: break-word;">{{ it.ship_remark || it.shipRemark || it.arrival_remark || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 时光轴内容 Timeline -->
          <div style="padding: 25px 25px 15px 35px; text-align: left; position: relative; width: 100%; box-sizing: border-box;">
            <!-- 时光轴中轴线 -->
            <div style="position: absolute; left: 17px; top: 30px; bottom: 30px; width: 2px; border-left: 2px dashed #cbd5e1;"></div>

            <!-- 1. 发货阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; background: #4f46e5; border: 2px solid #fff; box-shadow: 0 0 0 2px #4f46e5; display: inline-block;"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold; color: #1e293b;">🏭 供给侧装车发货</span>
                  <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.shippedAt) }}</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>发货数量：<strong>{{ formatNumber(deliveryDetailModalData.shippedQty) }} {{ deliveryDetailModalData.unit || '米' }}</strong></div>
                  <div>操作账号：<span>{{ deliveryDetailModalData.createdBy || '供给端系统' }}</span></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.shipContactName || '—' }}</span></div>
                  <div style="grid-column: span 2;">联系电话：<span>{{ deliveryDetailModalData.shipContactPhone || '—' }}</span></div>
                  <div style="grid-column: span 2;">供给主体：<span>{{ deliveryDetailModalData.supplyEntityName || '—' }} ({{ deliveryDetailModalData.supplyEntityId || '—' }})</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.shipRemark">发货备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.shipRemark }}”</span></div>
                </div>
              </div>
            </div>

            <!-- 2. 到货确认阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.arrivedConfirmAt ? '#10b981' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.arrivedConfirmAt ? '#10b981' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.arrivedConfirmAt ? '#1e293b' : '#94a3b8' }">🚚 物流卸车到货确认</span>
                  <span v-if="deliveryDetailModalData.arrivedConfirmAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.arrivedConfirmAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待卸车到货...</span>
                </div>
                <div v-if="deliveryDetailModalData.arrivedConfirmAt" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>到货确认：<strong>{{ formatNumber(deliveryDetailModalData.arrivedQty) }} {{ deliveryDetailModalData.unit || '米' }}</strong></div>
                  <div>操作账号：<span>{{ deliveryDetailModalData.arrivedConfirmBy || '—' }}</span></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.arrivedConfirmName || '—' }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.arrivedConfirmPhone">联系电话：<span>{{ deliveryDetailModalData.arrivedConfirmPhone }}</span></div>
                  <div style="grid-column: span 2;">需求主体：<span>{{ deliveryDetailModalData.section_1_name || deliveryDetailModalData.section1Name || '—' }} ({{ deliveryDetailModalData.section_1_id || deliveryDetailModalData.section1Id || '—' }})</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.arrivedRemark">到货备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.arrivedRemark }}”</span></div>
                </div>
              </div>
            </div>

            <!-- 3. 施工接收阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.receivedConfirmAt || deliveryDetailModalData.status === 'pending_diff_approve' ? '#8b5cf6' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.receivedConfirmAt || deliveryDetailModalData.status === 'pending_diff_approve' ? '#8b5cf6' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.receivedConfirmAt || deliveryDetailModalData.status === 'pending_diff_approve' ? '#1e293b' : '#94a3b8' }">👷 施工单位确认领用</span>
                  <span v-if="deliveryDetailModalData.receivedConfirmAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.receivedConfirmAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待施工接收...</span>
                </div>
                <div v-if="deliveryDetailModalData.receivedConfirmAt || deliveryDetailModalData.status === 'pending_diff_approve'" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>实收数量：<strong>{{ formatNumber(deliveryDetailModalData.receivedQty) }} {{ deliveryDetailModalData.unit || '米' }}</strong></div>
                  <div>操作账号：<span>{{ deliveryDetailModalData.receivedConfirmBy || '—' }}</span></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.receivedConfirmName || '—' }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.receivedConfirmPhone">联系电话：<span>{{ deliveryDetailModalData.receivedConfirmPhone }}</span></div>
                  <div style="grid-column: span 2;">需求主体：<span>{{ deliveryDetailModalData.section_1_name || deliveryDetailModalData.section1Name || '—' }} ({{ deliveryDetailModalData.section_1_id || deliveryDetailModalData.section1Id || '—' }})</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.receivedRemark">接收备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.receivedRemark }}”</span></div>
                  <div style="grid-column: span 2; color: #f97316; font-weight: 500;" v-if="deliveryDetailModalData.isTimeoutReceive">
                    🕒 提示：该订单由系统触发 [12小时超时强制自动确认接收]。
                  </div>
                </div>
              </div>
            </div>

            <!-- 4. 差异审批阶段 -->
            <div v-if="deliveryDetailModalData.diffApproveBy || deliveryDetailModalData.status === 'pending_diff_approve'" style="position: relative; margin-bottom: 20px;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.diffApproveBy ? '#f97316' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.diffApproveBy ? '#f97316' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.diffApproveBy ? '#1e293b' : '#94a3b8' }">🛡️ 现场负责人差异审批</span>
                  <span v-if="deliveryDetailModalData.diffApproveAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.diffApproveAt) }}</span>
                  <span v-else style="font-size: 11px; color: #f97316; font-weight: bold; font-style: italic;">⚠️ 挂起待审批...</span>
                </div>
                <div v-if="deliveryDetailModalData.diffApproveBy" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>审批人：<strong>{{ deliveryDetailModalData.diffApproveBy }}</strong></div>
                  <div>审批时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.diffApproveAt) }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.diffApproveRemark">审批意见：<span style="color: #ea580c; font-weight: 500;">{{ deliveryDetailModalData.diffApproveRemark }}</span></div>
                </div>
              </div>
            </div>

            <!-- 5. 库管入库阶段 -->
            <div style="position: relative;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.warehouseConfirmAt ? '#059669' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.warehouseConfirmAt ? '#059669' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.warehouseConfirmAt ? '#1e293b' : '#94a3b8' }">🏢 库管员确认物资归档入库</span>
                  <span v-if="deliveryDetailModalData.warehouseConfirmAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.warehouseConfirmAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待库管确认...</span>
                </div>
                <div v-if="deliveryDetailModalData.warehouseConfirmAt" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>入库日期：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.warehouseConfirmAt) }}</span></div>
                  <div>操作账号：<strong>{{ deliveryDetailModalData.warehouseConfirmBy || '—' }}</strong></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.warehouseConfirmName || '—' }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.warehouseConfirmPhone">联系电话：<span>{{ deliveryDetailModalData.warehouseConfirmPhone }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.warehouseRemark">入库备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.warehouseRemark }}”</span></div>
                </div>
              </div>
            </div>
            
            <!-- 6. 管理员编辑覆盖节点 -->
            <div v-if="deliveryDetailModalData.shipRemark && (deliveryDetailModalData.shipRemark.includes('[超级修正智能补齐]') || deliveryDetailModalData.shipRemark.includes(' | 状态强改至'))" style="position: relative; margin-top: 20px;">
              <span style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; background: #64748b; border: 2px solid #fff; box-shadow: 0 0 0 2px #64748b"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold; color: #1e293b;">🛠️ 超级管理员覆盖修正</span>
                  <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.updatedAt || deliveryDetailModalData.shippedAt) }}</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #f1f5f9; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>修正人：<strong>{{ deliveryDetailModalData.updatedBy || '超级管理员' }}</strong></div>
                  <div>修改时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.updatedAt) }}</span></div>
                  <div style="grid-column: span 2; word-break: break-all;">修正轨迹及批注：
                    <span style="color: #475569; font-style: italic; font-weight: 500;">
                      {{ 
                        deliveryDetailModalData.shipRemark.includes('[超级修正智能补齐]') 
                          ? deliveryDetailModalData.shipRemark.substring(deliveryDetailModalData.shipRemark.indexOf('[超级修正智能补齐]')).replace('[超级修正智能补齐] ', '') 
                          : deliveryDetailModalData.shipRemark.substring(deliveryDetailModalData.shipRemark.indexOf(' | 状态强改至') + 3) 
                      }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 底部按钮区 -->
          <div class="block-modal-actions" style="margin-top: 5px;">
            <button 
              type="button" 
              class="btn primary cancel-btn" 
              style="width: 100%; background: #4f46e5 !important; color: #fff !important; font-weight: 600;"
              @click="deliveryDetailModalVisible = false"
            >
              已阅并关闭
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 🚚 1. 现场卸车到货确认 Modal -->
    <Transition name="fade">
      <div v-if="fittingArrivalModalVisible" class="block-modal-overlay" @click.self="fittingArrivalModalVisible = false">
        <div class="block-modal-container" style="max-width: 580px;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;">
            <span class="block-warning-icon">🚚</span>
            <h3 style="margin-top: 5px; color: #fff;">管件现场到货清点确认</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">车次单号：{{ fittingArrivalForm.shipmentNo }} (车牌：{{ fittingArrivalForm.vehiclePlateNo }})</p>
          </div>

          <div style="padding: 15px 20px; font-size: 13px; color: #334155;">
            <div style="margin-bottom: 12px; background: #ecfdf5; border: 1px solid #a7f3d0; padding: 10px 12px; border-radius: 6px; color: #065f46; font-size: 12px;">
              💡 提示：请现场负责人清点到货实际数量，如有损耗拆包不符可微调“到货确认数”，提交后将更新物资归属！
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 12px; border: 1px solid #e2e8f0; table-layout: fixed;">
              <thead>
                <tr style="background: #f8fafc; color: #475569;">
                  <th style="padding: 6px 8px; text-align: left;">管件规格</th>
                  <th style="padding: 6px 8px; text-align: right; width: 80px;">出厂发货数</th>
                  <th style="padding: 6px 8px; text-align: right; width: 100px;">实际到货数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in fittingArrivalForm.items" :key="it.id" style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 6px 8px;">
                    <strong>{{ it.fitting_type }}</strong>
                    <span style="color: #64748b; font-family: monospace; font-size: 11.5px; display: block;">{{ it.model_spec }}</span>
                  </td>
                  <td style="padding: 6px 8px; text-align: right; font-weight: bold; color: #2563eb;">{{ it.shipped_qty }} {{ it.unit }}</td>
                  <td style="padding: 6px 8px; text-align: right;">
                    <input 
                      type="number" 
                      v-model.number="it.arrived_qty"
                      min="0"
                      style="width: 70px; padding: 4px 6px; border: 1px solid #059669; border-radius: 4px; text-align: right; font-weight: bold; color: #047857;" 
                    />
                  </td>
                </tr>
              </tbody>
            </table>

            <div style="margin-bottom: 10px;">
              <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">到货备注 / 现场验收说明：</label>
              <input 
                type="text" 
                v-model="fittingArrivalForm.arrivalRemark" 
                placeholder="例如：卸车验收完毕，随车合格证齐全；现场无损耗" 
                style="width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; box-sizing: border-box;"
              />
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 12px; color: #64748b;">操作经办人：<strong>{{ fittingArrivalForm.operatorName }}</strong></span>
            </div>
          </div>

          <div class="block-modal-actions" style="display: flex; gap: 10px; padding: 12px 20px; background: #f8fafc; border-top: 1px solid #e2e8f0;">
            <button type="button" class="btn ghost" style="flex: 1;" @click="fittingArrivalModalVisible = false">取消</button>
            <button type="button" class="btn primary" style="flex: 2; background: #059669; border-color: #059669;" :disabled="fittingArrivalSubmitting" @click="handleFittingArrivalSubmit">
              {{ fittingArrivalSubmitting ? '确认处理中...' : '✅ 确认物理卸车到货' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 👷 2. 施工单位确认接收领用 Modal -->
    <Transition name="fade">
      <div v-if="fittingConstructionModalVisible" class="block-modal-overlay" @click.self="fittingConstructionModalVisible = false">
        <div class="block-modal-container" style="max-width: 550px;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%) !important;">
            <span class="block-warning-icon">👷</span>
            <h3 style="margin-top: 5px; color: #fff;">施工单位管件领用接收确认</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">车次单号：{{ fittingConstructionForm.shipmentNo }} (车牌：{{ fittingConstructionForm.vehiclePlateNo }})</p>
          </div>

          <div style="padding: 15px 20px; font-size: 13px; color: #334155;">
            <div style="margin-bottom: 12px; background: #f3e8ff; border: 1px solid #d8b4fe; padding: 10px 12px; border-radius: 6px; color: #581c87; font-size: 12px;">
              💡 提示：由施工现场接收人员确认管件到场领用入库。确认后将进入“库管待归档”流转阶段。
            </div>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 12px; border: 1px solid #e2e8f0; table-layout: fixed;">
              <thead>
                <tr style="background: #f8fafc; color: #475569;">
                  <th style="padding: 6px 8px; text-align: left;">管件规格</th>
                  <th style="padding: 6px 8px; text-align: right; width: 90px;">确认到货数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in fittingConstructionForm.items" :key="it.id" style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 6px 8px;">
                    <strong>{{ it.fitting_type }}</strong>
                    <span style="color: #64748b; font-family: monospace; font-size: 11.5px; display: block;">{{ it.model_spec }}</span>
                  </td>
                  <td style="padding: 6px 8px; text-align: right; font-weight: bold; color: #7c3aed;">{{ it.arrived_qty }} {{ it.unit }}</td>
                </tr>
              </tbody>
            </table>

            <div style="margin-bottom: 10px;">
              <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">施工领用接收说明 / 差异说明：</label>
              <input 
                type="text" 
                v-model="fittingConstructionForm.constructionRemark" 
                placeholder="例如：施工队一班已核对领用无误，存入管网施工堆场" 
                style="width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; box-sizing: border-box;"
              />
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-size: 12px; color: #64748b;">接收领用经办人：<strong>{{ fittingConstructionForm.operatorName }}</strong></span>
            </div>
          </div>

          <div class="block-modal-actions" style="display: flex; gap: 10px; padding: 12px 20px; background: #f8fafc; border-top: 1px solid #e2e8f0;">
            <button type="button" class="btn ghost" style="flex: 1;" @click="fittingConstructionModalVisible = false">取消</button>
            <button type="button" class="btn primary" style="flex: 2; background: #7c3aed; border-color: #7c3aed;" :disabled="fittingConstructionSubmitting" @click="handleFittingConstructionSubmit">
              {{ fittingConstructionSubmitting ? '确认处理中...' : '👷 确认施工无误接收' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 🔮 首二日填报决策沙盘 Hover 悬浮气泡 (Popover) -->
    <div
      v-if="activeSandboxRow"
      :style="sandboxPopoverStyle"
      class="sandbox-popover-card"
    >
      <div class="popover-arrow"></div>
      <div class="popover-header">
        <span class="popover-title">🔮 第三天开工前库存推演</span>
        <span class="popover-badge-label" :class="getPredictionStatusClass(activeSandboxRow)">
          {{ getPredictionStatusLabel(activeSandboxRow) }}
        </span>
      </div>
      <div class="popover-body">
        <div class="popover-metrics-grid">
          <div class="metric-row">
            <span class="metric-label">现场可用在库：</span>
            <span class="metric-val text-bold">
              {{ strictPlanningFlowControl && !isUsageSubmitted ? '待结算' : `${activeSandboxRow.section1InventoryQty} 米` }}
            </span>
          </div>
          <div class="metric-row">
            <span class="metric-label">发货在途总量：</span>
            <span class="metric-val text-bold">{{ activeSandboxRow.inboundPipelineQty }} 米</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">前两日计划用量：</span>
            <span class="metric-val text-bold text-danger">- {{ getPrevTwoDaysPlanSum(activeSandboxRow) }} 米</span>
          </div>
        </div>
        <div class="popover-divider"></div>
        <div class="popover-suggestion-box">
          <span class="suggestion-icon">💡</span>
          <div class="suggestion-text">
            {{ getSandboxSuggestion(activeSandboxRow) }}
            <span
              v-if="strictPlanningFlowControl && !isUsageSubmitted"
              class="popover-jump-hint"
              @click="jumpToUsageTab"
            >
              去上报昨日消耗 ➜
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as XLSX from 'xlsx'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell, getDeliveryStatus } from './shared'
import ExportSettingsModal from './ExportSettingsModal.vue'
import {
  confirmTubeDemandManagementDeliveryArrival,
  confirmTubeDemandManagementDeliveryReceipt,
  approveTubeDemandManagementDeliveryDifference,
  getTubeDemandManagementBaseline,
  getTubeDemandManagementFittingBaseline,
  getTubeDemandManagementLogisticsRecords,
  getTubeDemandManagementOptions,
  getTubeDemandManagementPlanMatrix,
  getTubeDemandManagementUsageSheet,
  saveTubeDemandManagementPlanMatrix,
  saveTubeDemandManagementUsageSheet,
  saveTubeGlobalManagementConfigSection,
  submitTubeDemandManagementSection1Status,
  getFittingDeliveriesList,
  confirmFittingDeliveryArrival,
  confirmFittingDeliveryConstruction
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'

const auth = useAuthStore()
const {
  errorMessage,
  breadcrumbItems,
  goProjectPages,
  managementMode,
  modeLabels
} = useTubePageShell('需求侧管理入口')

const optionsLoading = ref(false)
const optionsError = ref('')
const section1Options = ref([])
const pipeModelOptions = ref([])
const currentGroup = ref('')

const selectedSection1Id = ref('')
const activeCategory = ref('pipe') // 'pipe' | 'fitting'
const lastPipeTab = ref('usage') // 记忆直管最后选中的子标签
const lastFittingTab = ref('fitting') // 记忆管件最后选中的子标签
const activeTab = ref('usage')
const showExportModal = ref(false)
const blockModalVisible = ref(false)
const blockModalData = ref(null)
const allPendingRows = ref([])

// 新增差异备注弹窗与订单流转时光轴详情弹窗状态
const receiptRemarkModalVisible = ref(false)
const receiptRemarkModalData = ref({
  row: null,
  receivedQty: 0,
  limitQty: 0,
  remark: ''
})

function getGroupUnitLabel(group) {
  if (!group || !group.items || !group.items.length) return '个'
  const units = Array.from(new Set(group.items.map(it => String(it.unit || '个').trim()).filter(Boolean)))
  if (units.length === 1) return units[0]
  return '件'
}

function getModalUnitLabel(modalData) {
  if (!modalData) return '个'
  const items = modalData.itemsList || []
  if (!items.length) return modalData.unit || '个'
  const units = Array.from(new Set(items.map(it => String(it.unit || '个').trim()).filter(Boolean)))
  if (units.length === 1) return units[0]
  return '件'
}

const deliveryDetailModalVisible = ref(false)
const deliveryDetailModalData = ref(null)

const isFittingDeliveryModal = computed(() => {
  if (!deliveryDetailModalData.value) return false
  const data = deliveryDetailModalData.value
  if (data.fitting_type || data.fittingType || data.isFittingDelivery) return true
  if (data.pipe_model_id || data.pipe_model_name || data.pipeModelId || data.pipeModelName || data.isStraightPipe) return false
  if (data.itemsList && data.itemsList.length && (data.itemsList[0].fitting_type || data.itemsList[0].fittingType)) return true
  return false
})

function showDeliveryDetail(input) {
  if (!input) return
  const isGroup = Boolean(input.items && Array.isArray(input.items))
  const itemsList = isGroup ? input.items : [input]
  const mainRow = itemsList[0] || input

  const shipmentNo = input.shipmentNo || input.shipment_no || mainRow.shipment_no || mainRow.shipmentNo || mainRow.order_no || mainRow.orderNo || String(mainRow.id || '')
  const vehiclePlateNo = input.vehiclePlateNo || input.vehicle_plate_no || mainRow.vehicle_plate_no || mainRow.vehiclePlateNo || '—'
  const shippedAt = input.shippedAt || input.shipped_at || mainRow.shipped_at || mainRow.shippedAt || ''
  const supplyEntityId = input.supplyEntityId || input.supply_entity_id || mainRow.supply_entity_id || mainRow.supplyEntityId || ''
  const supplyEntityName = input.supplyEntityName || input.supply_entity_name || mainRow.supply_entity_name || mainRow.supplyEntityName || supplyEntityId
  const section1Id = input.section1Id || input.section_1_id || mainRow.section_1_id || mainRow.section1Id || ''
  const section1Name = input.section1Name || input.section_1_name || mainRow.section_1_name || mainRow.section1Name || section1Id

  const shipContactName = mainRow.ship_contact_name || mainRow.shipContactName || input.shipContactName || mainRow.created_by || '发货负责人'
  const shipContactPhone = mainRow.ship_contact_phone || mainRow.shipContactPhone || input.shipContactPhone || '—'
  const createdBy = mainRow.created_by || mainRow.createdBy || mainRow.operator || input.createdBy || '发货操作员'
  const shipRemark = input.shipRemark || mainRow.ship_remark || mainRow.shipRemark || ''

  const arrivedConfirmAt = mainRow.arrived_at || mainRow.arrivedConfirmAt || ''
  const arrivedConfirmBy = mainRow.arrived_by || mainRow.arrivedConfirmBy || (arrivedConfirmAt ? '现场到货负责人' : '')
  const arrivedRemark = mainRow.arrival_remark || mainRow.arrivedRemark || ''

  const constructionConfirmedAt = mainRow.construction_confirmed_at || mainRow.receivedConfirmAt || ''
  const constructionConfirmedBy = mainRow.construction_confirmed_by || mainRow.receivedConfirmBy || (constructionConfirmedAt ? '施工接收负责人' : '')
  const constructionRemark = mainRow.construction_remark || mainRow.receivedRemark || ''

  const warehouseConfirmedAt = mainRow.warehouse_confirmed_at || mainRow.warehouseConfirmAt || ''
  const warehouseConfirmedBy = mainRow.warehouse_confirmed_by || mainRow.warehouseConfirmBy || (warehouseConfirmedAt ? '库管员' : '')
  const warehouseRemark = mainRow.warehouse_remark || mainRow.warehouseRemark || ''

  const totalShippedQty = itemsList.reduce((sum, it) => sum + (Number(it.shipped_qty !== undefined ? it.shipped_qty : it.shippedQty) || 0), 0)
  const totalArrivedQty = itemsList.reduce((sum, it) => {
    const val = (it.arrived_qty !== undefined && it.arrived_qty !== null) ? it.arrived_qty : (it.arrivedQty !== undefined && it.arrivedQty !== null ? it.arrivedQty : null)
    return sum + (val !== null ? Number(val) : 0)
  }, 0)

  deliveryDetailModalData.value = {
    ...mainRow,
    ...input,
    itemsList,
    totalTypesCount: itemsList.length,
    deliveryCode: shipmentNo,
    vehiclePlateNo,
    shippedAt,
    shippedQty: totalShippedQty,
    arrivedQty: totalArrivedQty,
    receivedQty: totalArrivedQty,
    unit: mainRow.unit || input.unit || ((mainRow.pipe_model_id || mainRow.pipe_model_name || mainRow.pipeModelId || mainRow.pipeModelName || input.pipeModelName || input.pipe_model_id) ? '米' : (mainRow.fitting_type ? '个' : '米')),
    pipeModelName: itemsList.length === 1 
      ? (mainRow.pipe_model_name || mainRow.pipeModelName || `${mainRow.fitting_type || '管件'} (${mainRow.model_spec || '未填'})`)
      : `组合装车共包含 ${itemsList.length} 种规格管件`,
    createdBy,
    shipContactName,
    shipContactPhone,
    shipRemark,
    supplyEntityName,
    supplyEntityId,
    section_1_name: section1Name,
    section_1_id: section1Id,
    section1Name,
    section1Id,
    arrivedConfirmAt,
    arrivedConfirmBy,
    arrivedRemark,
    receivedConfirmAt: constructionConfirmedAt,
    receivedConfirmBy: constructionConfirmedBy,
    receivedRemark: constructionRemark,
    warehouseConfirmAt: warehouseConfirmedAt,
    warehouseConfirmBy: warehouseConfirmedBy,
    warehouseRemark,
  }
  deliveryDetailModalVisible.value = true
}

// ----------------------------------------------------
// 需求侧：管件现场卸车到货确认与施工接收领用 Modal 控件与接口
// ----------------------------------------------------
const fittingArrivalModalVisible = ref(false)
const fittingArrivalSubmitting = ref(false)
const fittingArrivalForm = ref({
  groupKey: '',
  shipmentNo: '',
  vehiclePlateNo: '',
  operatorName: '',
  arrivalRemark: '',
  items: []
})

function openFittingArrivalModal(group) {
  if (!group || !group.items || !group.items.length) return
  const currentUsername = (auth.user && auth.user.username) ? auth.user.username : '需求侧现场负责人'
  fittingArrivalForm.value = {
    groupKey: group.groupKey,
    shipmentNo: group.shipmentNo || group.items[0]?.shipment_no || '',
    vehiclePlateNo: group.vehiclePlateNo || group.items[0]?.vehicle_plate_no || '—',
    operatorName: currentUsername,
    arrivalRemark: '',
    items: group.items.map(it => ({
      id: it.id,
      fitting_type: it.fitting_type || '管件',
      model_spec: it.model_spec || '未填',
      shipped_qty: Number(it.shipped_qty || 0),
      arrived_qty: Number(it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : it.shipped_qty || 0),
      unit: it.unit || '个'
    }))
  }
  fittingArrivalModalVisible.value = true
}

async function handleFittingArrivalSubmit() {
  if (!fittingArrivalForm.value.items.length) return
  if (!canConfirmArrival.value) {
    alert('当前账号无管件到货确认权限。')
    return
  }
  fittingArrivalSubmitting.value = true
  try {
    const ids = fittingArrivalForm.value.items.map(item => item.id)
    const arrivedQtyMap = Object.fromEntries(
      fittingArrivalForm.value.items.map(item => [String(item.id), Number(item.arrived_qty)])
    )
    await confirmFittingDeliveryArrival(PROJECT_KEY, {
      ids,
      arrived_qty_map: arrivedQtyMap,
      remark: fittingArrivalForm.value.arrivalRemark
    })
    alert('✅ 现场卸车到货确认成功！数据已更新。')
    fittingArrivalModalVisible.value = false
    await handleFittingQuery()
  } catch (err) {
    console.error('到货确认失败:', err)
    alert(`到货确认失败: ${err.message || '系统开小差了'}`)
  } finally {
    fittingArrivalSubmitting.value = false
  }
}

const fittingConstructionModalVisible = ref(false)
const fittingConstructionSubmitting = ref(false)
const fittingConstructionForm = ref({
  groupKey: '',
  shipmentNo: '',
  vehiclePlateNo: '',
  operatorName: '',
  constructionRemark: '',
  items: []
})

function openFittingConstructionModal(group) {
  if (!group || !group.items || !group.items.length) return
  const currentUsername = (auth.user && auth.user.username) ? auth.user.username : '施工现场负责人'
  fittingConstructionForm.value = {
    groupKey: group.groupKey,
    shipmentNo: group.shipmentNo || group.items[0]?.shipment_no || '',
    vehiclePlateNo: group.vehiclePlateNo || group.items[0]?.vehicle_plate_no || '—',
    operatorName: currentUsername,
    constructionRemark: '',
    items: group.items.map(it => ({
      id: it.id,
      fitting_type: it.fitting_type || '管件',
      model_spec: it.model_spec || '未填',
      shipped_qty: Number(it.shipped_qty || 0),
      arrived_qty: Number(it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : it.shipped_qty || 0),
      unit: it.unit || '个'
    }))
  }
  fittingConstructionModalVisible.value = true
}

async function handleFittingConstructionSubmit() {
  if (!fittingConstructionForm.value.items.length) return
  if (!canConfirmReceipt.value) {
    alert('当前账号无管件施工接收确认权限。')
    return
  }
  fittingConstructionSubmitting.value = true
  try {
    await confirmFittingDeliveryConstruction(PROJECT_KEY, {
      ids: fittingConstructionForm.value.items.map(item => item.id),
      remark: fittingConstructionForm.value.constructionRemark
    })
    alert('✅ 施工单位领用接收确认成功！数据已更新。')
    fittingConstructionModalVisible.value = false
    await handleFittingQuery()
  } catch (err) {
    console.error('施工接收确认失败:', err)
    alert(`施工接收确认失败: ${err.message || '系统开小差了'}`)
  } finally {
    fittingConstructionSubmitting.value = false
  }
}

function handleLogisticsRowClick(event, row) {
  const target = event.target
  if (!target) return
  if (
    target.tagName === 'INPUT' ||
    target.tagName === 'BUTTON' ||
    target.tagName === 'SELECT' ||
    target.closest('button') ||
    target.closest('.stack-controls') ||
    target.closest('.action-stack')
  ) {
    return
  }
  showDeliveryDetail(row)
}


function tryParseBlockError(message) {
  if (!message || typeof message !== 'string') return null
  if (!message.includes('现场可用账面库存不足')) return null
  
  try {
    const modelMatch = message.match(/规格【(.*?)】/)
    const arrivedMatch = message.match(/累计到货仅为\s*([\d.]+)\s*米/)
    const expectedMatch = message.match(/累计消耗将达到\s*([\d.]+)\s*米/)
    const useMatch = message.match(/其中实际使用\s*([\d.]+)\s*米/)
    const lossMatch = message.match(/实际损耗\s*([\d.]+)\s*米/)
    const shortageMatch = message.match(/账面超前亏空\s*([\d.]+)\s*米/)
    const pendingMatch = message.match(/当前正有\s*([\d.]+)\s*米\s*在途物资/)
    
    if (modelMatch && arrivedMatch && expectedMatch && shortageMatch && pendingMatch) {
      return {
        pipeModelId: modelMatch[1],
        totalArrived: Number(arrivedMatch[1]),
        expectedTotalUsage: Number(expectedMatch[1]),
        expectedUsageOnly: useMatch ? Number(useMatch[1]) : Number(expectedMatch[1]),
        expectedLossOnly: lossMatch ? Number(lossMatch[1]) : 0,
        shortage: Number(shortageMatch[1]),
        pendingArrival: Number(pendingMatch[1]),
        rawMessage: message
      }
    }
  } catch (e) {
    // ignore
  }
  return null
}

// 5. 本标段管件发货到货对账台账 Ref 变量
const fittingRows = ref([])
const fittingLoading = ref(false)
const fittingExportLoading = ref(false)

const getPastDateStr = (days) => {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().split('T')[0]
}
const getTodayStr = () => {
  return new Date().toISOString().split('T')[0]
}

const fittingFilter = ref({
  startDate: getPastDateStr(30),
  endDate: getTodayStr(),
  searchKeyword: '',
})

const expandedDemandFittingGroupKeys = ref(new Set())

const toggleDemandFittingGroup = (groupKey) => {
  const next = new Set(expandedDemandFittingGroupKeys.value)
  if (next.has(groupKey)) {
    next.delete(groupKey)
  } else {
    next.add(groupKey)
  }
  expandedDemandFittingGroupKeys.value = next
}

const isDemandFittingGroupExpanded = (groupKey) => {
  return expandedDemandFittingGroupKeys.value.has(groupKey)
}

const toggleAllDemandFittingGroups = (expandAll = true) => {
  if (expandAll) {
    expandedDemandFittingGroupKeys.value = new Set(groupedDemandFittingRows.value.map(g => g.groupKey))
  } else {
    expandedDemandFittingGroupKeys.value = new Set()
  }
}

const groupedDemandFittingRows = computed(() => {
  const map = new Map()
  for (const item of fittingRows.value) {
    const groupKey = item.shipment_key || item.shipment_no || item.order_no || `${item.vehicle_plate_no}_${item.shipped_at}_${item.id}`
    if (!map.has(groupKey)) {
      map.set(groupKey, {
        groupKey,
        shipmentNo: item.shipment_no || item.order_no || '—',
        orderNo: item.order_no || '—',
        vehiclePlateNo: item.vehicle_plate_no || '—',
        shippedAt: item.shipped_at,
        supplyEntityId: item.supply_entity_id,
        supplyEntityName: item.supply_entity_name || item.supply_entity_id || '—',
        section1Id: item.section_1_id,
        section1Name: item.section_1_name || item.section_1_id || '—',
        shipRemark: item.ship_remark || '',
        status: item.status || 'shipped',
        totalShippedQty: 0,
        totalArrivedQty: 0,
        items: []
      })
    }
    const group = map.get(groupKey)
    group.items.push(item)
    group.totalShippedQty += (Number(item.shipped_qty) || 0)
    if (['arrived', 'construction_confirmed', 'received', 'warehouse_confirmed'].includes(item.status) && item.arrived_qty !== null && item.arrived_qty !== undefined) {
      group.totalArrivedQty += (Number(item.arrived_qty) || 0)
    }
  }

  // 短板状态判定原则：若多条明细中有任何一条状态落后于其它条目，外层 group.status 展现该落后状态
  const statusRankMap = {
    'shipped': 0,
    'arrived': 1,
    'construction_confirmed': 2,
    'received': 2,
    'warehouse_confirmed': 3
  }

  const result = Array.from(map.values())
  for (const group of result) {
    const activeItems = group.items.filter(item => (item.status || 'shipped') !== 'cancelled')
    group.hasCancelled = activeItems.length !== group.items.length
    if (!activeItems.length) {
      group.status = 'cancelled'
      continue
    }
    let minRank = 999
    let minStatus = 'shipped'
    for (const item of activeItems) {
      const st = item.status || 'shipped'
      const r = statusRankMap[st] !== undefined ? statusRankMap[st] : 0
      if (r < minRank) {
        minRank = r
        minStatus = st
      }
    }
    group.status = minStatus
  }

  return result
})

const standardFittingTypes = ref(['弯头', '三通', '大小头', '封头', '直缝弯管', '补偿器', '固定节'])
function isStandardFittingType(typeStr) {
  if (!typeStr) return true
  return (standardFittingTypes.value || []).includes(String(typeStr).trim())
}

const currentSection1Name = computed(() => {
  const match = section1Options.value.find(s => s.section_1_id === selectedSection1Id.value)
  return match ? match.section_1_name : selectedSection1Id.value
})

const handleFittingQuery = async () => {
  expandedDemandFittingGroupKeys.value = new Set()
  if (!selectedSection1Id.value) return
  fittingLoading.value = true
  try {
    const res = await getFittingDeliveriesList(PROJECT_KEY, {
      section1Id: selectedSection1Id.value,
      startDate: fittingFilter.value.startDate,
      endDate: fittingFilter.value.endDate,
      searchKeyword: fittingFilter.value.searchKeyword,
      limit: 300,
    })
    if (res && res.ok) {
      fittingRows.value = (res.items || []).map(it => ({
        ...it,
        tempArrivedQty: Number(it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : it.shipped_qty || 0),
        submitting: false
      }))
    }
  } catch (err) {
    console.error('读取本标段管件到货记录失败:', err)
  } finally {
    fittingLoading.value = false
  }
}

async function handleConfirmSingleItemArrival(item) {
  if (!item || !item.id) return
  if (!canConfirmArrival.value) {
    alert('当前账号无管件到货确认权限。')
    return
  }
  const qtyToConfirm = Number(item.tempArrivedQty !== undefined ? item.tempArrivedQty : item.shipped_qty)
  const shippedQty = Number(item.shipped_qty || 0)
  if (!Number.isInteger(qtyToConfirm) || qtyToConfirm <= 0 || qtyToConfirm > shippedQty) {
    alert(`到货确认数量必须是 1 至 ${shippedQty} 的正整数！`)
    return
  }
  item.submitting = true
  try {
    await confirmFittingDeliveryArrival(PROJECT_KEY, {
      ids: [item.id],
      arrived_qty_map: { [String(item.id)]: qtyToConfirm },
      remark: item.ship_remark ? `现场核对签收 (发货备注: ${item.ship_remark})` : '现场清点签收到货'
    })
    alert(`✅ 单项管件【${item.fitting_type || '管件'} (${item.model_spec || ''})】到货确认成功！确认到货数: ${qtyToConfirm}`)
    await handleFittingQuery()
  } catch (err) {
    console.error('单项到货确认失败:', err)
    alert(`确认到货失败: ${err.message || '系统开小差了'}`)
  } finally {
    item.submitting = false
  }
}

function openFittingArrivalModalForSingle(item, group) {
  const currentUsername = (auth.user && auth.user.username) ? auth.user.username : '需求侧现场负责人'
  fittingArrivalForm.value = {
    groupKey: group ? group.groupKey : '',
    shipmentNo: group ? group.shipmentNo : item.shipment_no,
    vehiclePlateNo: group ? group.vehiclePlateNo : item.vehicle_plate_no,
    operatorName: currentUsername,
    arrivalRemark: '',
    items: [{
      id: item.id,
      fitting_type: item.fitting_type || '管件',
      model_spec: item.model_spec || '未填',
      shipped_qty: Number(item.shipped_qty || 0),
      arrived_qty: Number(item.tempArrivedQty !== undefined ? item.tempArrivedQty : (item.arrived_qty !== undefined ? item.arrived_qty : item.shipped_qty)),
      unit: item.unit || '个'
    }]
  }
  fittingArrivalModalVisible.value = true
}

async function handleConfirmSingleItemConstruction(item) {
  if (!item || !item.id) return
  if (!canConfirmReceipt.value) {
    alert('当前账号无管件施工接收确认权限。')
    return
  }
  item.submitting = true
  try {
    await confirmFittingDeliveryConstruction(PROJECT_KEY, {
      ids: [item.id],
      remark: '施工班组核对领用接收'
    })
    alert(`✅ 单项管件【${item.fitting_type || '管件'} (${item.model_spec || ''})】施工接收领用成功！`)
    await handleFittingQuery()
  } catch (err) {
    console.error('单项施工接收失败:', err)
    alert(`施工接收失败: ${err.message || '系统开小差了'}`)
  } finally {
    item.submitting = false
  }
}

function openFittingConstructionModalForSingle(item, group) {
  const currentUsername = (auth.user && auth.user.username) ? auth.user.username : '施工现场负责人'
  fittingConstructionForm.value = {
    groupKey: group ? group.groupKey : '',
    shipmentNo: group ? group.shipmentNo : item.shipment_no,
    vehiclePlateNo: group ? group.vehiclePlateNo : item.vehicle_plate_no,
    operatorName: currentUsername,
    constructionRemark: '',
    items: [{
      id: item.id,
      fitting_type: item.fitting_type || '管件',
      model_spec: item.model_spec || '未填',
      shipped_qty: Number(item.shipped_qty || 0),
      arrived_qty: Number(item.arrived_qty !== undefined ? item.arrived_qty : item.shipped_qty),
      unit: item.unit || '个'
    }]
  }
  fittingConstructionModalVisible.value = true
}

function handleDemandFittingExport() {
  if (!fittingRows.value.length) {
    alert('当前标段暂无管件到货记录可导出')
    return
  }
  fittingExportLoading.value = true
  try {
    const exportData = fittingRows.value.map(r => ({
      '发货时间': formatDateTimeDisplay(r.shipped_at),
      '发货单号': r.shipment_no || '—',
      '运输车牌号': r.vehicle_plate_no || '—',
      '供给主体': r.supply_entity_name || r.supply_entity_id || '—',
      '接收标段': r.section_1_name || r.section_1_id || '—',
      '管件类型': r.fitting_type || '—',
      '型号/规格': r.model_spec || '—',
      '发货数量': r.shipped_qty ?? '—',
      '单位': r.unit || '个',
      '整车备注': r.ship_remark || '—',
    }))

    const worksheet = XLSX.utils.json_to_sheet(exportData)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, `${currentSection1Name.value}_管件到货台账`)

    const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14)
    XLSX.writeFile(workbook, `demand_fitting_${selectedSection1Id.value}_${timestamp}.xlsx`)
  } catch (error) {
    console.error('导出管件到货台账失败:', error)
    alert('导出管件到货台账失败')
  } finally {
    fittingExportLoading.value = false
  }
}

const demandFittingTotalQty = computed(() => {
  return fittingRows.value.reduce((sum, r) => sum + (Number(r.shipped_qty) || 0), 0)
})

const demandFittingBatches = computed(() => {
  const set = new Set(fittingRows.value.map(r => r.shipment_no || r.id))
  return set.size
})

const demandFittingStandardQty = computed(() => {
  return fittingRows.value
    .filter(r => isStandardFittingType(r.fitting_type))
    .reduce((sum, r) => sum + (Number(r.shipped_qty) || 0), 0)
})

const demandFittingNonStandardQty = computed(() => {
  return Math.max(0, demandFittingTotalQty.value - demandFittingStandardQty.value)
})

function handleGotoLogistics() {
  blockModalVisible.value = false
  activeTab.value = 'logistics'
  setTimeout(() => {
    const el = document.querySelector('.tab-card')
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, 100)
}
const exportColumns = [
  { key: 'deliveryCode', label: '订单号' },
  { key: 'shipmentNo', label: '运输车次号' },
  { key: 'vehiclePlateNo', label: '车牌号' },
  { key: 'supplyEntityName', label: '供给主体' },
  { key: 'pipeModelName', label: '规格型号' },
  { key: 'shippedQty', label: '发货量（米）' },
  { key: 'shippedAtDisplay', label: '发货时间' },
  { key: 'arrivedConfirmAtDisplay', label: '确认到货时间' },
  { key: 'statusLabel', label: '状态' },
  { key: 'receivedQty', label: '物理接收量（米）' },
  { key: 'shipRemark', label: '备注' }
]
const exportPendingRows = computed(() => {
  return pendingRows.value.map(row => ({
    ...row,
    shippedAtDisplay: formatDateTimeDisplay(row.shippedAt),
    arrivedConfirmAtDisplay: formatDateTimeDisplay(row.arrivedConfirmAt),
    shipRemark: row.remarks || ''
  }))
})
const exportAllPendingRows = computed(() => {
  return allPendingRows.value.map(row => ({
    ...row,
    shippedAtDisplay: formatDateTimeDisplay(row.shippedAt),
    arrivedConfirmAtDisplay: formatDateTimeDisplay(row.arrivedConfirmAt),
    shipRemark: row.remarks || ''
  }))
})

// 智能 Excel 一键粘贴解析函数
function handleClipboardPaste(event) {
  if (!selectedSection1Id.value || activeTab.value !== 'plan') {
    return
  }
  const clipboardData = event.clipboardData || window.clipboardData
  const pastedText = clipboardData.getData('text')
  if (!pastedText) return

  // 按换行符切分行
  const lines = pastedText.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  if (!lines.length) return

  let successCount = 0
  lines.forEach(line => {
    // 按 Tab 键切分列
    const parts = line.split(/\t/).map(p => p.trim())
    if (parts.length < 2) return

    const pipeModelInput = parts[0].toUpperCase()
    const qtyValue = Number(parts[1])
    if (isNaN(qtyValue) || qtyValue < 0) return

    // 匹配前台 planRows 里的保温管型号名称或 ID
    const targetRow = planRows.value.find(row => 
      row.pipeModelName.toUpperCase() === pipeModelInput || 
      row.pipeModelId.toUpperCase() === pipeModelInput
    )

    if (targetRow) {
      planDates.value.forEach((date, dateIdx) => {
        // 如果 pasted 数据里有多列，依次按列填入
        const colValIdx = dateIdx + 1
        if (parts[colValIdx] !== undefined) {
          const partVal = Number(parts[colValIdx])
          if (!isNaN(partVal) && partVal >= 0 && isPlanDateEditable(dateIdx)) {
            targetRow.values[date].plannedQty = partVal
            successCount++
          }
        } else if (dateIdx === 0 && isPlanDateEditable(0)) {
          // 若只有两列，默认填入第一天可编辑日期
          targetRow.values[date].plannedQty = qtyValue
          successCount++
        }
      })
    }
  })

  if (successCount > 0) {
    setActionMessage('success', `智能粘贴解析成功！已为您智能匹配并自动填报 ${successCount} 个计划量单元格。`)
  } else {
    setActionMessage('error', '未在剪贴板中匹配出有效的保温管型号，请确认从 Excel 中整行复制了 [型号, 计划量] 等数据。')
  }
}

function handleUsageClipboardPaste(event) {
  if (!selectedSection1Id.value || activeTab.value !== 'usage') {
    return
  }
  const clipboardData = event.clipboardData || window.clipboardData
  const pastedText = clipboardData.getData('text')
  if (!pastedText) return

  // 按换行符切分行
  const lines = pastedText.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  if (!lines.length) return

  let successCount = 0
  lines.forEach(line => {
    // 按 Tab 键切分列
    const parts = line.split(/\t/).map(p => p.trim())
    if (parts.length < 2) return

    const pipeModelInput = parts[0].toUpperCase()

    // 匹配前台 usageRows 里的保温管型号名称或 ID
    const targetRow = usageRows.value.find(row => 
      row.pipeModelName.toUpperCase() === pipeModelInput || 
      row.pipeModelId.toUpperCase() === pipeModelInput
    )

    if (targetRow) {
      // 第一列是型号，第二列是使用量
      const usedQtyVal = Number(parts[1])
      if (!isNaN(usedQtyVal) && usedQtyVal >= 0) {
        targetRow.usedQty = usedQtyVal
        successCount++
      }

      // 第三列是损耗量（如果有的话）
      if (parts[2] !== undefined && parts[2] !== '') {
        const lossQtyVal = Number(parts[2])
        if (!isNaN(lossQtyVal) && lossQtyVal >= 0) {
          targetRow.lossQty = lossQtyVal
          successCount++
        }
      }

      // 第四列是备注（如果有的话）
      if (parts[3] !== undefined && parts[3] !== '') {
        targetRow.remarks = parts[3]
      }
    }
  })

  if (successCount > 0) {
    setActionMessage('success', `智能粘贴解析成功！已为您智能匹配并自动填报 ${successCount} 个消耗/损耗单元格。`)
  } else {
    setActionMessage('error', '未在剪贴板中匹配出有效的保温管型号，请确认从 Excel 中复制了 [型号, 实际使用量, (可选)实际损耗量, (可选)备注] 等数据。')
  }
}

const showDate = ref('')
const anchorDate = ref('')
const usageDate = ref('')
const planEditableDays = ref(3)
const strictPlanningFlowControl = ref(true)
const isUsageSubmitted = ref(false)

const baselineLoading = ref(false)
const baselineError = ref('')
const baselineRows = ref([])

const fittingBaselineLoading = ref(false)
const fittingBaselineError = ref('')
const fittingBaselineRows = ref([])

// 多维多选分面筛选响应式状态
const fittingFilters = reactive({
  systemTypes: [],      // 系统类型多选
  categories: [],       // 物理类别多选
  mainDns: [],          // 主径DN多选
  subDns: [],           // 次径DN多选
  angles: [],           // 角度多选
  bendingRatios: [],    // 弯曲倍数多选
  pressures: [],        // 公称压力多选
  searchKeyword: '',    // 全局关键词检索
})

// 动态提取当前标段各维度的可选值列表及对应记录数
const availableFittingFacets = computed(() => {
  const rows = fittingBaselineRows.value || []
  
  const systemTypeMap = new Map()
  const categoryMap = new Map()
  const mainDnMap = new Map()
  const subDnMap = new Map()
  const angleMap = new Map()
  const bendingRatioMap = new Map()
  const pressureMap = new Map()

  rows.forEach((r) => {
    // 1. 系统类型
    const st = String(r.system_type || '').trim()
    if (st) systemTypeMap.set(st, (systemTypeMap.get(st) || 0) + 1)

    // 2. 物理类别
    const cat = String(r.category || r.fitting_type || '').trim()
    if (cat) categoryMap.set(cat, (categoryMap.get(cat) || 0) + 1)

    // 3. 主径DN
    if (r.main_dn != null && !isNaN(Number(r.main_dn))) {
      const dn = Number(r.main_dn)
      mainDnMap.set(dn, (mainDnMap.get(dn) || 0) + 1)
    }

    // 4. 次径DN
    if (r.sub_dn != null && !isNaN(Number(r.sub_dn))) {
      const sdn = Number(r.sub_dn)
      subDnMap.set(sdn, (subDnMap.get(sdn) || 0) + 1)
    }

    // 5. 角度
    if (r.angle != null && !isNaN(Number(r.angle))) {
      const ang = Number(r.angle)
      angleMap.set(ang, (angleMap.get(ang) || 0) + 1)
    }

    // 6. 弯曲倍数
    if (r.bending_radius_ratio != null && !isNaN(Number(r.bending_radius_ratio))) {
      const br = Number(r.bending_radius_ratio)
      bendingRatioMap.set(br, (bendingRatioMap.get(br) || 0) + 1)
    }

    // 7. 压力
    const pr = String(r.pressure_rating || '').trim()
    if (pr) pressureMap.set(pr, (pressureMap.get(pr) || 0) + 1)
  })

  return {
    systemTypes: Array.from(systemTypeMap.entries()).map(([value, count]) => ({ value, count })),
    categories: Array.from(categoryMap.entries()).map(([value, count]) => ({ value, count })),
    mainDns: Array.from(mainDnMap.entries()).map(([value, count]) => ({ value, count })).sort((a, b) => b.value - a.value),
    subDns: Array.from(subDnMap.entries()).map(([value, count]) => ({ value, count })).sort((a, b) => b.value - a.value),
    angles: Array.from(angleMap.entries()).map(([value, count]) => ({ value, count })).sort((a, b) => b.value - a.value),
    bendingRatios: Array.from(bendingRatioMap.entries()).map(([value, count]) => ({ value, count })).sort((a, b) => b.value - a.value),
    pressures: Array.from(pressureMap.entries()).map(([value, count]) => ({ value, count })),
  }
})

// 判断特定专属明细维度是否应该展示（级联感知）
const shouldShowAngleAndBending = computed(() => {
  if (fittingFilters.categories.length > 0) {
    return fittingFilters.categories.some(c => c.includes('弯头') || c.includes('弯管'))
  }
  return (availableFittingFacets.value.angles.length > 0 || availableFittingFacets.value.bendingRatios.length > 0)
})

const shouldShowSubDn = computed(() => {
  if (fittingFilters.categories.length > 0) {
    return fittingFilters.categories.some(c => c.includes('三通') || c.includes('异径') || c.includes('变径') || c.includes('大小头'))
  }
  return availableFittingFacets.value.subDns.length > 0
})

const shouldShowPressure = computed(() => {
  if (fittingFilters.categories.length > 0) {
    return fittingFilters.categories.some(c => c.includes('阀') || c.includes('补偿') || c.includes('波纹'))
  }
  return availableFittingFacets.value.pressures.length > 0
})

// 下拉浮层展开状态控制
const activeDropdown = ref('')

function toggleFittingDropdown(name, event) {
  if (event) event.stopPropagation()
  if (activeDropdown.value === name) {
    activeDropdown.value = ''
  } else {
    activeDropdown.value = name
  }
}

function closeFittingDropdown() {
  activeDropdown.value = ''
}

function getFittingFilterSummary(dimension, defaultLabel, prefix = '', suffix = '') {
  const selected = fittingFilters[dimension] || []
  if (selected.length === 0) {
    return defaultLabel
  }
  if (selected.length === 1) {
    return `${prefix}${selected[0]}${suffix}`
  }
  return `已选 ${selected.length} 项`
}

function selectAllFittingFilterDimension(dimension, options) {
  if (!options || !options.length) return
  fittingFilters[dimension] = options.map(opt => opt.value)
}

function toggleFittingFilterItem(dimension, value) {
  const arr = fittingFilters[dimension]
  if (!arr) return
  const index = arr.indexOf(value)
  if (index > -1) {
    arr.splice(index, 1)
  } else {
    arr.push(value)
  }
}

function isFittingFilterSelected(dimension, value) {
  return fittingFilters[dimension]?.includes(value) ?? false
}

function clearFittingFilterDimension(dimension) {
  if (fittingFilters[dimension]) {
    fittingFilters[dimension] = []
  }
}

function clearAllFittingFilters() {
  fittingFilters.systemTypes = []
  fittingFilters.categories = []
  fittingFilters.mainDns = []
  fittingFilters.subDns = []
  fittingFilters.angles = []
  fittingFilters.bendingRatios = []
  fittingFilters.pressures = []
  fittingFilters.searchKeyword = ''
}

// 活跃筛选条件标签列表 (用于可一键移除的小胶囊)
const activeFittingFilterTags = computed(() => {
  const tags = []
  fittingFilters.systemTypes.forEach(v => tags.push({ dim: 'systemTypes', label: `系统: ${v}`, value: v }))
  fittingFilters.categories.forEach(v => tags.push({ dim: 'categories', label: `类别: ${v}`, value: v }))
  fittingFilters.mainDns.forEach(v => tags.push({ dim: 'mainDns', label: `主径: DN${v}`, value: v }))
  fittingFilters.subDns.forEach(v => tags.push({ dim: 'subDns', label: `次径: DN${v}`, value: v }))
  fittingFilters.angles.forEach(v => tags.push({ dim: 'angles', label: `角度: ${v}°`, value: v }))
  fittingFilters.bendingRatios.forEach(v => tags.push({ dim: 'bendingRatios', label: `弯曲: ${v}DN`, value: v }))
  fittingFilters.pressures.forEach(v => tags.push({ dim: 'pressures', label: `压力: ${v}`, value: v }))
  if (fittingFilters.searchKeyword.trim()) {
    tags.push({ dim: 'searchKeyword', label: `搜索: "${fittingFilters.searchKeyword.trim()}"`, value: fittingFilters.searchKeyword })
  }
  return tags
})

// 多维多选综合过滤
const filteredFittingBaselineRows = computed(() => {
  let list = fittingBaselineRows.value || []

  // 1. 系统类型多选 (OR)
  if (fittingFilters.systemTypes.length > 0) {
    list = list.filter(r => fittingFilters.systemTypes.includes(String(r.system_type || '').trim()))
  }

  // 2. 物理类别多选 (OR)
  if (fittingFilters.categories.length > 0) {
    list = list.filter(r => fittingFilters.categories.includes(String(r.category || r.fitting_type || '').trim()))
  }

  // 3. 主径DN多选 (OR)
  if (fittingFilters.mainDns.length > 0) {
    list = list.filter(r => r.main_dn != null && fittingFilters.mainDns.includes(Number(r.main_dn)))
  }

  // 4. 次径DN多选 (OR)
  if (fittingFilters.subDns.length > 0) {
    list = list.filter(r => r.sub_dn != null && fittingFilters.subDns.includes(Number(r.sub_dn)))
  }

  // 5. 角度多选 (OR)
  if (fittingFilters.angles.length > 0) {
    list = list.filter(r => r.angle != null && fittingFilters.angles.includes(Number(r.angle)))
  }

  // 6. 弯曲倍数多选 (OR)
  if (fittingFilters.bendingRatios.length > 0) {
    list = list.filter(r => r.bending_radius_ratio != null && fittingFilters.bendingRatios.includes(Number(r.bending_radius_ratio)))
  }

  // 7. 公称压力多选 (OR)
  if (fittingFilters.pressures.length > 0) {
    list = list.filter(r => fittingFilters.pressures.includes(String(r.pressure_rating || '').trim()))
  }

  // 8. 关键词全局模糊搜索
  if (fittingFilters.searchKeyword.trim()) {
    const kw = fittingFilters.searchKeyword.trim().toLowerCase()
    list = list.filter((r) => {
      const matchName = String(r.standard_name || '').toLowerCase().includes(kw)
      const matchSpec = String(r.model_spec || '').toLowerCase().includes(kw)
      const matchSub = String(r.sub_model_spec || '').toLowerCase().includes(kw)
      const matchRawSpec = String(r.raw_model_spec || '').toLowerCase().includes(kw)
      const matchRawName = String(r.raw_name || '').toLowerCase().includes(kw)
      const matchDn = String(r.main_dn || '').includes(kw) || String(r.sub_dn || '').includes(kw)
      const matchValve = String(r.valve_model || '').toLowerCase().includes(kw)
      const matchPressure = String(r.pressure_rating || '').toLowerCase().includes(kw)
      const matchRemark = String(r.remark || '').toLowerCase().includes(kw)
      return matchName || matchSpec || matchSub || matchRawSpec || matchRawName || matchDn || matchValve || matchPressure || matchRemark
    })
  }

  return list
})

// 实时统计计算
const fittingBaselineStats = computed(() => {
  let totalDesignQty = 0
  let totalPurchaseQty = 0
  let filteredDesignQty = 0
  let filteredPurchaseQty = 0

  fittingBaselineRows.value.forEach((r) => {
    totalDesignQty += Number(r.design_qty || 0)
    totalPurchaseQty += Number(r.purchase_plan_qty || 0)
  })

  filteredFittingBaselineRows.value.forEach((r) => {
    filteredDesignQty += Number(r.design_qty || 0)
    filteredPurchaseQty += Number(r.purchase_plan_qty || 0)
  })

  return {
    totalDesignQty,
    totalPurchaseQty,
    filteredDesignQty,
    filteredPurchaseQty,
  }
})

const planLoading = ref(false)
const planError = ref('')
const planDates = ref([])
const planRows = ref([])
const savePlanLoading = ref(false)

const usageLoading = ref(false)
const usageError = ref('')
const usageRows = ref([])
const saveUsageLoading = ref(false)

const originalPlanRowsJson = ref('')
function backupPlanRows() {
  originalPlanRowsJson.value = JSON.stringify(planRows.value)
}
const isPlanDirty = computed(() => {
  if (!planRows.value.length) return false
  return originalPlanRowsJson.value !== JSON.stringify(planRows.value)
})

const originalUsageRowsJson = ref('')
function backupUsageRows() {
  originalUsageRowsJson.value = JSON.stringify(usageRows.value)
}
const isUsageDirty = computed(() => {
  if (!usageRows.value.length) return false
  return originalUsageRowsJson.value !== JSON.stringify(usageRows.value)
})
const submitStatusLoading = ref(false)

const pendingLoading = ref(false)
const pendingError = ref('')
const pendingRows = ref([])
const pendingFilters = reactive({
  orderNo: '',
  shipmentNo: '',
  pipeModelId: '',
  shippedDate: '',
  arrivedDate: '',
})
const nowTick = ref(Date.now())
let nowTimer = null

const actionMessage = ref(null)
const canSubmitCurrentProject = computed(() => auth.canSubmitFor(PROJECT_KEY))
const normalizedGroupKey = computed(() => String(currentGroup.value || '').trim())
const isGlobalAdmin = computed(() => {
  const group = normalizedGroupKey.value.toLowerCase()
  return group === 'global_admin' || group === 'globaladmin' || group === '系统管理员' || group === '管理员'
})
const canConfirmArrival = computed(() => isGlobalAdmin.value || normalizedGroupKey.value === 'tube_site_manager')
const canConfirmReceipt = computed(() => isGlobalAdmin.value || normalizedGroupKey.value === 'tube_construction_unit')
const isSiteManager = computed(() => isGlobalAdmin.value || normalizedGroupKey.value === 'tube_site_manager')
const deliveryActionLoadingKey = ref('')

const currentGroupLabel = computed(() => {
  const group = normalizedGroupKey.value
  if (!group) {
    return '未识别'
  }
  if (isGlobalAdmin.value) {
    return '全局管理员'
  }
  return group
})

function isPlanDateEditable(index) {
  const editableDays = Number(planEditableDays.value ?? 0)
  if (editableDays <= 0) {
    return false
  }
  return index >= planDates.value.length - editableDays
}

function canClickArrival(row) {
  return Boolean(canConfirmArrival.value && (row?.status === 'pending_arrival' || row?.status === 'shipped' || !row?.status))
}

function canClickReceipt(row) {
  return Boolean(canConfirmReceipt.value && (row?.status === 'pending_receive' || row?.status === 'arrived'))
}

function getTodayString(offsetDays = 0) {
  const today = new Date()
  today.setDate(today.getDate() + offsetDays)
  return today.toISOString().slice(0, 10)
}

const toastVisible = ref(false)
const toastType = ref('success')
const toastText = ref('')
let toastTimer = null

function setActionMessage(type, text) {
  actionMessage.value = { type, text }
  
  // 激活浮动 Toast
  toastType.value = type
  toastText.value = text
  toastVisible.value = true
  
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => {
    toastVisible.value = false
  }, 3000)
}

function clearActionMessage() {
  actionMessage.value = null
  toastVisible.value = false
  if (toastTimer) clearTimeout(toastTimer)
}

function getErrorMessage(error, defaultMsg = '操作失败') {
  if (!error) return defaultMsg
  const msg = error.message || String(error)
  try {
    if (msg.trim().startsWith('{')) {
      const parsed = JSON.parse(msg)
      if (parsed.detail) {
        if (typeof parsed.detail === 'string') {
          return parsed.detail
        } else if (Array.isArray(parsed.detail)) {
          return parsed.detail.map(d => d.msg).join('; ')
        }
      }
    }
  } catch (e) {
    // ignore
  }
  return msg
}

function formatNumber(value) {
  const numericValue = Number(value || 0)
  return Number.isFinite(numericValue) ? numericValue.toLocaleString('zh-CN') : '0'
}

function parsePipeModelDiameters(modelCode) {
  if (!modelCode) return { main: 0, outer: 0 }
  const str = String(modelCode).trim()
  const parts = str.split('/')
  const leftStr = parts[0] || ''
  const rightStr = parts[1] || ''
  const leftMatch = leftStr.match(/(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)/i)
  const rightMatch = rightStr.match(/(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)/i)
  const main = leftMatch ? parseFloat(leftMatch[1]) || 0 : 0
  const outer = rightMatch ? parseFloat(rightMatch[1]) || 0 : 0
  return { main, outer }
}

function sortPipeModelsByDiameterDesc(modelList) {
  return [...modelList].sort((a, b) => {
    const codeA = a.pipe_model_id || a.pipeModelId || a.pipe_model_name || a.pipeModelName
    const codeB = b.pipe_model_id || b.pipeModelId || b.pipe_model_name || b.pipeModelName
    const dA = parsePipeModelDiameters(codeA)
    const dB = parsePipeModelDiameters(codeB)
    if (dB.main !== dA.main) {
      return dB.main - dA.main
    }
    if (dB.outer !== dA.outer) {
      return dB.outer - dA.outer
    }
    return String(codeA || '').localeCompare(String(codeB || ''))
  })
}

function normalizeBaselineRows(rows) {
  const list = (rows || []).map((row) => ({
    pipeModelId: row.pipe_model_id || row.pipeModelId,
    pipeModelName: row.pipe_model_name || row.pipeModelName || row.model_name || '未命名型号',
    designQuantity: row.design_total_qty || row.designQuantity || row.design_qty || 0,
    purchaseQuantity: row.purchase_total_qty || row.purchaseQuantity || row.purchase_qty || row.purchase_plan_qty || 0,
    remarks: row.remarks || row.remark || ''
  }))
  return sortPipeModelsByDiameterDesc(list)
}

function normalizePlanRows(rows, dates) {
  const list = (rows || []).map((row) => {
    const valueMap = {}
    const sourceMap = row.values || row.plan_values || {}
    const remarksMap = row.remarks || row.remark_map || {}
    dates.forEach((date) => {
      const sourceValue = sourceMap[date]
      valueMap[date] = {
        plannedQty: Number(
          typeof sourceValue === 'number'
            ? sourceValue
            : sourceValue?.plan_qty ?? sourceValue?.planned_qty ?? sourceValue?.plannedQty ?? 0,
        ),
        remarks:
          remarksMap[date] ||
          sourceValue?.remark ||
          sourceValue?.remarks ||
          ''
      }
    })
    return {
      pipeModelId: row.pipe_model_id || row.pipeModelId,
      pipeModelName: row.pipe_model_name || row.pipeModelName || row.model_name || '未命名型号',
      section1InventoryQty: Number(row.section_1_inventory_qty ?? row.section1InventoryQty ?? 0),
      inboundPipelineQty: Number(row.inbound_pipeline_qty ?? row.inboundPipelineQty ?? 0),
      values: valueMap
    }
  })
  return sortPipeModelsByDiameterDesc(list)
}

function normalizeUsageRows(rows) {
  const list = (rows || []).map((row) => ({
    pipeModelId: row.pipe_model_id || row.pipeModelId,
    pipeModelName: row.pipe_model_name || row.pipeModelName || row.model_name || '未命名型号',
    usedQty: Number(row.usage_qty ?? row.used_qty ?? row.usedQty ?? 0),
    lossQty: Number(row.loss_qty ?? row.lossQty ?? 0),
    remarks: row.remark || row.remarks || ''
  }))
  return sortPipeModelsByDiameterDesc(list)
}

const currentPipeModelOptions = computed(() => {
  if (baselineRows.value && baselineRows.value.length > 0) {
    const list = baselineRows.value.map((b) => ({
      pipe_model_id: b.pipeModelId,
      pipe_model_name: b.pipeModelName || b.pipeModelId,
    }))
    return sortPipeModelsByDiameterDesc(list)
  }
  const list = pipeModelOptions.value.map((m) => ({
    pipe_model_id: m.pipe_model_id,
    pipe_model_name: m.pipe_model_name || m.pipe_model_id,
  }))
  return sortPipeModelsByDiameterDesc(list)
})

function normalizePendingRows(rows) {
  return (rows || []).map((row) => ({
    deliveryId: row.delivery_id || row.deliveryId || row.id,
    deliveryCode: row.delivery_code || row.deliveryCode || '',
    shipmentNo: row.shipment_no || row.shipmentNo || '',
    vehiclePlateNo: row.vehicle_plate_no || row.vehiclePlateNo || '',
    supplyEntityName: row.supply_entity_name || row.supplyEntityName || row.supply_entity_id || row.supplyEntityId || '—',
    pipeModelName: row.pipe_model_name || row.pipeModelName || '未命名型号',
    section_1_id: row.section_1_id || row.section1Id || '',
    section_1_name: row.section_1_name || row.section1Name || '',
    status: row.status || '',
    isTimeoutReceive: Boolean(row.is_timeout_receive || row.isTimeoutReceive),
    statusLabel: getDeliveryStatusLabel(row.status, Boolean(row.is_timeout_receive || row.isTimeoutReceive)),
    abnormalFlag: Boolean(row.abnormal_flag || row.abnormalFlag),
    shippedQty: Number(row.shipped_qty || row.shippedQty || 0),
    arrivedQty: Number(row.arrived_qty || row.arrivedQty || row.shipped_qty || row.shippedQty || 0),
    receivedQty: Number(row.received_qty || row.receivedQty || row.arrived_qty || row.arrivedQty || row.shipped_qty || row.shippedQty || 0),
    shippedAt: row.shipped_at || row.shippedAt || '',
    arrivedConfirmAt: row.arrived_confirm_at || row.arrivedConfirmAt || '',
    deliveryElapsedLabel: row.delivery_elapsed_label || row.deliveryElapsedLabel || '',
    remarks: row.remarks || row.ship_remark || '',
    arrivalConfirmQty: Number(row.arrived_qty || row.arrivedQty || row.shipped_qty || row.shippedQty || 0),
    receiptConfirmQty: Number(row.received_qty || row.receivedQty || row.arrived_qty || row.arrivedQty || row.shipped_qty || row.shippedQty || 0),
    arrivalRemark: row.arrived_remark || row.arrivedRemark || '',
    receiptRemark: row.received_remark || row.receivedRemark || '',
    createdBy: row.created_by || row.createdBy || '',
    shipRemark: row.ship_remark || row.shipRemark || '',
    shipContactName: row.ship_contact_name || row.shipContactName || '',
    shipContactPhone: row.ship_contact_phone || row.shipContactPhone || '',
    supplyEntityId: row.supply_entity_id || row.supplyEntityId || '',
    arrivedConfirmBy: row.arrived_confirm_by || row.arrivedConfirmBy || '',
    arrivedConfirmName: row.arrived_confirm_name || row.arrivedConfirmName || '',
    arrivedConfirmPhone: row.arrived_confirm_phone || row.arrivedConfirmPhone || '',
    arrivedRemark: row.arrived_remark || row.arrivedRemark || '',
    receivedConfirmBy: row.received_confirm_by || row.receivedConfirmBy || '',
    receivedConfirmName: row.received_confirm_name || row.receivedConfirmName || '',
    receivedConfirmPhone: row.received_confirm_phone || row.receivedConfirmPhone || '',
    receivedConfirmAt: row.received_confirm_at || row.receivedConfirmAt || '',
    receivedRemark: row.received_remark || row.receivedRemark || '',
    receivedConfirmBy: row.received_confirm_by || row.receivedConfirmBy || '',
    receivedConfirmAt: row.received_confirm_at || row.receivedConfirmAt || '',
    receivedRemark: row.received_remark || row.receivedRemark || '',
    diffApproveBy: row.diff_approve_by || row.diffApproveBy || '',
    diffApproveAt: row.diff_approve_at || row.diffApproveAt || '',
    diffApproveRemark: row.diff_approve_remark || row.diffApproveRemark || '',
    warehouseConfirmBy: row.warehouse_confirm_by || row.warehouseConfirmBy || '',
    warehouseConfirmName: row.warehouse_confirm_name || row.warehouseConfirmName || '',
    warehouseConfirmPhone: row.warehouse_confirm_phone || row.warehouseConfirmPhone || '',
    warehouseConfirmAt: row.warehouse_confirm_at || row.warehouseConfirmAt || '',
    warehouseRemark: row.warehouse_remark || row.warehouseRemark || '',
    updatedBy: row.updated_by || row.updatedBy || '',
    updatedAt: row.updated_at || row.updatedAt || ''
  }))

}

function getAbnormalLabel(row) {
  if (!row?.abnormalFlag) return ''
  if (row.receivedQty != null && row.arrivedQty != null && Number(row.receivedQty) < Number(row.arrivedQty)) {
    return '少接收'
  }
  if (row.arrivedQty != null && Number(row.arrivedQty) < Number(row.shippedQty || 0)) {
    return '少到货'
  }
  return '异常'
}

function formatElapsedLabel(shippedAt) {
  if (!shippedAt) return ''
  const start = new Date(shippedAt)
  if (Number.isNaN(start.getTime())) return ''
  const diffMs = Math.max(nowTick.value - start.getTime(), 0)
  const totalSeconds = Math.floor(diffMs / 1000)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  if (days > 0) return `${days}天${hours}小时${minutes}分`
  if (hours > 0) return `${hours}小时${minutes}分`
  if (minutes > 0) return `${minutes}分`
  return `${totalSeconds}秒`
}

function formatDeliveryElapsedDisplay(row) {
  if (!row || row.status === 'cancelled') return '—'
  return row.deliveryElapsedLabel || formatElapsedLabel(row.shippedAt) || '—'
}

function formatDateTimeDisplay(value) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return String(value).replace('T', ' ').slice(0, 16)
  }
  const pad = (part) => String(part).padStart(2, '0')
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`
}

function getDeliveryStatusLabel(status, isTimeout = false) {
  return getDeliveryStatus(status, isTimeout).label
}

function normalizeOptionsPayload(response) {
  return {
    section1Options: response.section_1s || [],
    pipeModelOptions: response.pipe_model_options || response.pipe_models || [],
    currentGroup: response.current_group || response.user?.group || '',
    showDate: response.show_date || response.biz_date || '',
    planStartDate: response.plan_start_date || '',
    planEditableDays: Number(response.plan_editable_days ?? 3),
    defaultAnchorDate: response.default_anchor_date || response.default_plan_anchor_date || '',
    usageCollectionDate: response.usage_collection_date || '',
    defaultUsageDate: response.default_usage_date || response.default_usage_sheet_date || ''
  }
}

async function loadOptions() {
  optionsLoading.value = true
  optionsError.value = ''
  try {
    const response = await getTubeDemandManagementOptions(PROJECT_KEY)
    const normalized = normalizeOptionsPayload(response)
    section1Options.value = normalized.section1Options
    pipeModelOptions.value = normalized.pipeModelOptions
    currentGroup.value = normalized.currentGroup
    showDate.value = normalized.showDate || getTodayString(-1)
    planEditableDays.value = Number.isFinite(normalized.planEditableDays) ? normalized.planEditableDays : 3
    if (response && response.fitting_config && Array.isArray(response.fitting_config.standard_types) && response.fitting_config.standard_types.length) {
      standardFittingTypes.value = response.fitting_config.standard_types
    }
    const section1IdSet = new Set(section1Options.value.map((item) => String(item.section_1_id || '')))
    if (!selectedSection1Id.value || !section1IdSet.has(selectedSection1Id.value)) {
      selectedSection1Id.value = section1Options.value[0]?.section_1_id || ''
    }
    anchorDate.value = normalized.planStartDate || normalized.defaultAnchorDate || getTodayString()
    usageDate.value = normalized.usageCollectionDate || normalized.defaultUsageDate || getTodayString(-1)
  } catch (error) {
    optionsError.value = error?.message || '加载需求侧配置失败'
  } finally {
    optionsLoading.value = false
  }
}

async function loadBaseline() {
  if (!selectedSection1Id.value) {
    baselineRows.value = []
    return
  }
  baselineLoading.value = true
  baselineError.value = ''
  try {
    const response = await getTubeDemandManagementBaseline(PROJECT_KEY, selectedSection1Id.value)
    baselineRows.value = normalizeBaselineRows(response.rows)
  } catch (error) {
    baselineError.value = error?.message || '加载基准量失败'
    baselineRows.value = []
  } finally {
    baselineLoading.value = false
  }
}

async function loadFittingBaseline() {
  if (!selectedSection1Id.value) {
    fittingBaselineRows.value = []
    return
  }
  fittingBaselineLoading.value = true
  fittingBaselineError.value = ''
  try {
    const response = await getTubeDemandManagementFittingBaseline(PROJECT_KEY, selectedSection1Id.value)
    fittingBaselineRows.value = response.rows || []
  } catch (error) {
    fittingBaselineError.value = error?.message || '加载管件基准量失败'
    fittingBaselineRows.value = []
  } finally {
    fittingBaselineLoading.value = false
  }
}

function exportDemandFittingBaseline() {
  const rows = filteredFittingBaselineRows.value
  if (!rows.length) return

  const headers = [
    '序号', '系统类型', '物理类别', '标准名称', '型号规格', '细分规格/子型号',
    '主径DN', '次径DN', '角度(°)', '弯曲倍数', '阀门型号', '公称压力',
    '单位', '设计使用量', '计划采购总量', '原型号规格', '原名称', '说明备注'
  ]

  const dataRows = rows.map((r, idx) => [
    idx + 1,
    r.system_type || '高温水',
    r.category || r.fitting_type || '管件',
    r.standard_name || '',
    r.model_spec || '',
    r.sub_model_spec || '',
    r.main_dn,
    r.sub_dn,
    r.angle,
    r.bending_radius_ratio,
    r.valve_model || '',
    r.pressure_rating || '',
    r.unit || '个',
    r.design_qty != null ? r.design_qty : 0,
    r.purchase_plan_qty != null ? r.purchase_plan_qty : 0,
    r.raw_model_spec || '',
    r.raw_name || '',
    r.remark || '',
  ])

  const ws = XLSX.utils.aoa_to_sheet([headers, ...dataRows])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '管件设计与采购量')
  XLSX.writeFile(wb, `${currentSection1Name.value}_管件设计量与计划采购量.xlsx`)
}

async function loadPlanMatrix() {
  if (!selectedSection1Id.value || !anchorDate.value) {
    planDates.value = []
    planRows.value = []
    return
  }
  planLoading.value = true
  planError.value = ''
  try {
    const response = await getTubeDemandManagementPlanMatrix(PROJECT_KEY, selectedSection1Id.value, anchorDate.value)
    const dates = response.plan_dates || []
    planDates.value = dates
    planRows.value = normalizePlanRows(response.rows, dates)
    backupPlanRows()
    strictPlanningFlowControl.value = response.strict_planning_flow_control ?? true
    isUsageSubmitted.value = response.is_usage_submitted ?? false
  } catch (error) {
    planError.value = error?.message || '加载三日计划失败'
    planDates.value = []
    planRows.value = []
  } finally {
    planLoading.value = false
  }
}

async function loadUsageSheet() {
  if (!selectedSection1Id.value || !usageDate.value) {
    usageRows.value = []
    return
  }
  usageLoading.value = true
  usageError.value = ''
  try {
    const response = await getTubeDemandManagementUsageSheet(PROJECT_KEY, selectedSection1Id.value, usageDate.value)
    usageRows.value = normalizeUsageRows(response.rows)
    backupUsageRows()
  } catch (error) {
    usageError.value = error?.message || '加载实际使用数据失败'
    usageRows.value = []
  } finally {
    usageLoading.value = false
  }
}

async function loadAllPendingLogistics() {
  if (!selectedSection1Id.value) {
    allPendingRows.value = []
    return
  }
  try {
    const response = await getTubeDemandManagementLogisticsRecords(PROJECT_KEY, selectedSection1Id.value, {})
    allPendingRows.value = normalizePendingRows(response.rows)
  } catch (error) {
    console.error('Failed to load all pending logistics for export:', error)
  }
}

async function loadLogisticsRecords() {
  if (!selectedSection1Id.value) {
    pendingRows.value = []
    pendingError.value = ''
    pendingLoading.value = false
    return
  }
  pendingLoading.value = true
  pendingError.value = ''
  try {
    const response = await getTubeDemandManagementLogisticsRecords(PROJECT_KEY, selectedSection1Id.value, {
      orderNo: pendingFilters.orderNo || '',
      shipmentNo: pendingFilters.shipmentNo || '',
      pipeModelId: pendingFilters.pipeModelId || '',
      shippedDate: pendingFilters.shippedDate || '',
      arrivedDate: pendingFilters.arrivedDate || '',
    })
    pendingRows.value = normalizePendingRows(response.rows)
  } catch (error) {
    pendingError.value = error?.message || '加载物流确认记录失败'
    pendingRows.value = []
  } finally {
    pendingLoading.value = false
  }
}

function applyPendingFilters() {
  loadLogisticsRecords()
}

async function resetPendingFilters() {
  pendingFilters.orderNo = ''
  pendingFilters.shipmentNo = ''
  pendingFilters.pipeModelId = ''
  pendingFilters.shippedDate = ''
  pendingFilters.arrivedDate = ''
  await Promise.all([
    loadLogisticsRecords(),
    loadAllPendingLogistics()
  ])
}

async function confirmArrival(row) {
  if (!row?.deliveryId || !canClickArrival(row)) {
    return
  }
  const normalizedArrivedQty = Number(row.arrivalConfirmQty ?? row.shippedQty ?? 0)
  if (normalizedArrivedQty > Number(row.shippedQty || 0)) {
    setActionMessage('error', '确认到货量不能大于该订单的发货量。')
    return
  }
  deliveryActionLoadingKey.value = `arrival-${row.deliveryId}`
  clearActionMessage()
  try {
    await confirmTubeDemandManagementDeliveryArrival(PROJECT_KEY, row.deliveryId, {
      arrived_qty: normalizedArrivedQty,
      remark: row.arrivalRemark || ''
    })
    setActionMessage('success', `发货单 ${row.deliveryCode || row.deliveryId} 到货已确认。`)
    await Promise.all([
      loadLogisticsRecords(),
      loadAllPendingLogistics()
    ])
  } catch (error) {
    setActionMessage('error', getErrorMessage(error, '确认到货失败'))
  } finally {
    deliveryActionLoadingKey.value = ''
  }
}

async function confirmReceipt(row) {
  if (!row?.deliveryId || !canClickReceipt(row)) {
    return
  }
  const limitQty = Number(row.arrivedQty ?? row.shippedQty ?? 0)
  const receivedQty = Number(row.receiptConfirmQty ?? row.arrivedQty ?? row.shippedQty ?? 0)
  if (receivedQty > limitQty) {
    setActionMessage('error', `确认施工接收量不能大于已到货量 ${limitQty} 米`)
    return
  }
  if (receivedQty < 0) {
    setActionMessage('error', `确认施工接收量不能为负数`)
    return
  }
  if (receivedQty < limitQty) {
    // 弹窗让用户填写备注，而不是直接阻断
    receiptRemarkModalData.value = {
      row: row,
      receivedQty: receivedQty,
      limitQty: limitQty,
      remark: (row.receiptRemark || '').trim()
    }
    receiptRemarkModalVisible.value = true
    return
  }
  
  // 正常全额到货签收，无需备注，直接执行提交
  await submitReceiptExecution(row, receivedQty, '')
}

async function submitReceiptExecution(row, receivedQty, remark) {
  deliveryActionLoadingKey.value = `receipt-${row.deliveryId}`
  clearActionMessage()
  try {
    await confirmTubeDemandManagementDeliveryReceipt(PROJECT_KEY, row.deliveryId, {
      received_qty: receivedQty,
      remark: remark
    })
    setActionMessage('success', `发货单 ${row.deliveryCode || row.deliveryId} 施工接收已确认。`)
    // 回写数据，以便回显
    row.receivedQty = receivedQty
    row.receiptRemark = remark
    await Promise.all([
      loadLogisticsRecords(),
      loadAllPendingLogistics()
    ])
  } catch (error) {
    setActionMessage('error', getErrorMessage(error, '确认施工接收失败'))
  } finally {
    deliveryActionLoadingKey.value = ''
  }
}

async function submitReceiptWithRemark() {
  const remark = receiptRemarkModalData.value.remark.trim()
  if (remark.length < 10) {
    alert('⚠️ 备注理由字数必须不少于 10 个字符！')
    return
  }
  receiptRemarkModalVisible.value = false
  const row = receiptRemarkModalData.value.row
  const receivedQty = receiptRemarkModalData.value.receivedQty
  await submitReceiptExecution(row, receivedQty, remark)
}


async function handleDiffApprove(row, approved) {
  if (!row?.deliveryId) {
    return
  }
  const actionName = approved ? '同意差异' : '驳回差异'
  const confirmText = approved
    ? `您确定同意发货单 ${row.deliveryCode || row.deliveryId} 的少接收确认吗？\n确认后，实收数量将按施工上报的 ${row.receivedQty} 米进行结账。`
    : `您确定驳回发货单 ${row.deliveryCode || row.deliveryId} 的少接收确认吗？\n驳回后，实收数量将强制更正并等于到货数量 ${row.arrivedQty} 米。`
  
  if (!confirm(confirmText)) {
    return
  }
  
  const approveRemark = prompt('请输入审批意见 (选填):') || ''
  
  deliveryActionLoadingKey.value = approved ? `approve-${row.deliveryId}` : `reject-${row.deliveryId}`
  clearActionMessage()
  try {
    await approveTubeDemandManagementDeliveryDifference(PROJECT_KEY, row.deliveryId, {
      approved: approved,
      remark: approveRemark
    })
    setActionMessage('success', `发货单 ${row.deliveryCode || row.deliveryId} 差异审批已完成 (${actionName})。`)
    await Promise.all([
      loadLogisticsRecords(),
      loadAllPendingLogistics()
    ])
  } catch (error) {
    setActionMessage('error', getErrorMessage(error, `${actionName}失败`))
  } finally {
    deliveryActionLoadingKey.value = ''
  }
}

async function reloadSection1Data() {
  if (
    receiptRemarkModalVisible.value ||
    deliveryDetailModalVisible.value ||
    showExportModal.value ||
    blockModalVisible.value
  ) {
    return
  }
  clearActionMessage()
  await Promise.all([
    loadBaseline(),
    loadFittingBaseline(),
    loadPlanMatrix(),
    loadUsageSheet(),
    loadLogisticsRecords(),
    loadAllPendingLogistics(),
    handleFittingQuery()
  ])
}

async function refreshRealtimeConfig() {
  if (
    receiptRemarkModalVisible.value ||
    deliveryDetailModalVisible.value ||
    showExportModal.value ||
    blockModalVisible.value
  ) {
    return
  }
  await loadOptions()
  await reloadSection1Data()
}


async function savePlanMatrix() {
  if (!selectedSection1Id.value || !planDates.value.length || planEditableDays.value <= 0) {
    return
  }
  savePlanLoading.value = true
  clearActionMessage()
  try {
    const records = []
    planRows.value.forEach((row) => {
      planDates.value.forEach((date, index) => {
        if (!isPlanDateEditable(index)) {
          return
        }
        const cell = row.values[date]
        records.push({
          plan_date: date,
          pipe_model_id: row.pipeModelId,
          plan_qty: Number(cell.plannedQty || 0),
          remark: cell.remarks || ''
        })
      })
    })
    await saveTubeDemandManagementPlanMatrix(PROJECT_KEY, {
      section_1_id: selectedSection1Id.value,
      anchor_date: anchorDate.value,
      records
    })
    setActionMessage('success', '三日计划量已提交。')
    await loadPlanMatrix()
  } catch (error) {
    setActionMessage('error', getErrorMessage(error, '提交三日计划量失败'))
  } finally {
    savePlanLoading.value = false
  }
}

async function saveUsageSheet() {
  if (!selectedSection1Id.value || !usageDate.value) {
    return
  }
  saveUsageLoading.value = true
  clearActionMessage()
  try {
    const records = usageRows.value.map((row) => ({
      pipe_model_id: row.pipeModelId,
      usage_qty: Number(row.usedQty || 0),
      loss_qty: Number(row.lossQty || 0),
      remark: row.remarks || ''
    }))
    await saveTubeDemandManagementUsageSheet(PROJECT_KEY, {
      section_1_id: selectedSection1Id.value,
      usage_date: usageDate.value,
      records
    })
    setActionMessage('success', '实际消耗量及损耗数据已成功上报提交！')
    await loadUsageSheet()
  } catch (error) {
    const errorText = getErrorMessage(error, '提交实际使用量失败')
    const parsed = tryParseBlockError(errorText)
    if (parsed) {
      blockModalData.value = parsed
      blockModalVisible.value = true
    } else {
      setActionMessage('error', errorText)
    }
  } finally {
    saveUsageLoading.value = false
  }
}

async function handleSection1SubmitClick() {
  if (!selectedSection1Id.value || !canSubmitCurrentProject.value) {
    return
  }
  submitStatusLoading.value = true
  clearActionMessage()
  try {
    const response = await submitTubeDemandManagementSection1Status(PROJECT_KEY, {
      section_1_id: selectedSection1Id.value,
      remark: ''
    })
    const submittedDate = response?.submission?.data_submit_date || anchorDate.value || '未设置'
    setActionMessage('success', `需求主体 ${selectedSection1Id.value} 已标记为提交完成，提交日期为 ${submittedDate}.`)
  } catch (error) {
    setActionMessage('error', getErrorMessage(error, '提交需求主体填报状态失败'))
  } finally {
    submitStatusLoading.value = false
  }
}

watch(selectedSection1Id, () => {
  reloadSection1Data()
})

async function handleUsageDateChange() {
  if (!usageDate.value || !isGlobalAdmin.value) return
  try {
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'usage_collection_date',
      data: usageDate.value,
    })
    setActionMessage('success', `消耗采集日期已保存更新为 ${usageDate.value}`)
    await loadUsageSheet()
  } catch (err) {
    setActionMessage('error', err?.message || '保存消耗采集日期失败')
  }
}

watch(usageDate, (value, oldValue) => {
  if (!selectedSection1Id.value || !value || value === oldValue) {
    return
  }
  loadUsageSheet()
})

onMounted(async () => {
  nowTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
  document.addEventListener('click', closeFittingDropdown)
  await refreshRealtimeConfig()
})

function handleCategoryClick(category) {
  if (activeCategory.value === category) {
    return
  }

  if (activeTab.value === 'plan' && isPlanDirty.value) {
    const confirmDiscard = confirm('您在“三日滚动计划填报”中有未保存的修改，确定要离开并丢弃修改吗？')
    if (!confirmDiscard) {
      return
    }
  }

  if (activeTab.value === 'usage' && isUsageDirty.value) {
    const confirmDiscard = confirm('您在“每日使用消耗填报”中有未保存的修改，确定要离开并丢弃修改吗？')
    if (!confirmDiscard) {
      return
    }
  }

  activeCategory.value = category
  if (category === 'pipe') {
    activeTab.value = lastPipeTab.value || 'usage'
  } else if (category === 'fitting') {
    activeTab.value = lastFittingTab.value || 'fitting'
  }
  refreshCurrentTabData(activeTab.value)
}

function handleTabClick(targetTab) {
  if (['usage', 'plan', 'logistics', 'baseline'].includes(targetTab)) {
    activeCategory.value = 'pipe'
    lastPipeTab.value = targetTab
  } else if (['fitting', 'fitting_baseline'].includes(targetTab)) {
    activeCategory.value = 'fitting'
    lastFittingTab.value = targetTab
  }

  if (activeTab.value === targetTab) {
    refreshCurrentTabData(targetTab)
    return
  }

  if (activeTab.value === 'plan' && isPlanDirty.value) {
    const confirmDiscard = confirm('您在“三日滚动计划填报”中有未保存的修改，确定要离开并丢弃修改吗？')
    if (!confirmDiscard) {
      return
    }
  }

  if (activeTab.value === 'usage' && isUsageDirty.value) {
    const confirmDiscard = confirm('您在“每日使用消耗填报”中有未保存的修改，确定要离开并丢弃修改吗？')
    if (!confirmDiscard) {
      return
    }
  }

  activeTab.value = targetTab
  refreshCurrentTabData(targetTab)
}

function refreshCurrentTabData(tab) {
  if (tab === 'plan') {
    loadPlanMatrix()
  } else if (tab === 'usage') {
    loadUsageSheet()
  } else if (tab === 'baseline') {
    loadBaseline()
  } else if (tab === 'logistics') {
    loadLogisticsRecords()
  } else if (tab === 'fitting') {
    handleFittingQuery()
  } else if (tab === 'fitting_baseline') {
    loadFittingBaseline()
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('click', closeFittingDropdown)
  if (nowTimer) {
    clearInterval(nowTimer)
    nowTimer = null
  }
})

// 计算前两日计划需求总量
function getPrevTwoDaysPlanSum(row) {
  if (!planDates.value || planDates.value.length < 2) return 0
  const date1 = planDates.value[0]
  const date2 = planDates.value[1]
  const q1 = Number(row.values[date1]?.plannedQty || 0)
  const q2 = Number(row.values[date2]?.plannedQty || 0)
  return q1 + q2
}

// 预测尾部一日开工时的可用库存量 = 现场在库 + 在途总量 - 前两日计划需求之和
function getTailDayPrediction(row) {
  const stock = Number(row.section1InventoryQty || 0)
  const transit = Number(row.inboundPipelineQty || 0)
  const prevDemand = getPrevTwoDaysPlanSum(row)
  return stock + transit - prevDemand
}

// 预测状态样式类
function getPredictionStatusClass(row) {
  if (strictPlanningFlowControl.value && !isUsageSubmitted.value) {
    return 'locked-grey'
  }
  const prediction = getTailDayPrediction(row)
  return prediction >= 0 ? 'safe-green' : 'danger-red'
}

// 状态标签文本
function getPredictionStatusLabel(row) {
  if (strictPlanningFlowControl.value && !isUsageSubmitted.value) {
    return '⌛ 待上报前日消耗'
  }
  const prediction = getTailDayPrediction(row)
  if (prediction > 0) return `盈余 +${prediction} 米`
  if (prediction === 0) return `平衡 0 米`
  return `缺口 -${Math.abs(prediction)} 米`
}

// 智能决策建议提示
function getSandboxSuggestion(row) {
  if (strictPlanningFlowControl.value && !isUsageSubmitted.value) {
    return '昨日实际使用消耗尚未上报结清！为了避免提供虚假的盈缺预测，请先提交昨日消耗以解锁首二日盈缺推演。'
  }
  const prediction = getTailDayPrediction(row)
  if (prediction > 0) {
    return `首二日后可用富余 ${prediction} 米，第三天建议≤${prediction}米填报，防止爆仓积压。`
  }
  if (prediction === 0) {
    return `前两天计划恰好耗光全部可用库存。第三天填报量建议等于第3天的真实施工需求量。`
  }
  const absoluteGap = Math.abs(prediction)
  return `前两天计划将消耗光全部可用库存！首二日后将面临断料缺口 ${absoluteGap} 米，第三天填报量建议≥${absoluteGap}米。`
}

// 🔮 首二日填报决策沙盘 Hover Popover 相关状态与方法
const activeSandboxRow = ref(null)
const sandboxPopoverStyle = ref({ top: '0px', left: '0px' })

function showSandboxPopover(event, row) {
  activeSandboxRow.value = row
  const rect = event.currentTarget.getBoundingClientRect()
  // 气泡定位在触发Badge的上方居中 (利用 position: fixed)
  sandboxPopoverStyle.value = {
    top: `${rect.top - 8}px`,
    left: `${rect.left + rect.width / 2}px`,
    transform: 'translate(-50%, -100%)',
  }
}

function hideSandboxPopover() {
  activeSandboxRow.value = null
}

function getSandboxTriggerClass(row) {
  if (strictPlanningFlowControl.value && !isUsageSubmitted.value) {
    return 'trigger-locked'
  }
  const prediction = getTailDayPrediction(row)
  return prediction >= 0 ? 'trigger-safe' : 'trigger-danger'
}

function getSandboxTriggerLabel(row) {
  if (strictPlanningFlowControl.value && !isUsageSubmitted.value) {
    return '🔒 待上报'
  }
  const prediction = getTailDayPrediction(row)
  if (prediction > 0) return `盈 +${prediction}m`
  if (prediction === 0) return `平 0m`
  return `缺 -${Math.abs(prediction)}m`
}

function jumpToUsageTab() {
  activeSandboxRow.value = null
  activeTab.value = 'usage'
  // 滚动到顶部以看到填报卡片
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<style scoped>
/* Premium Usage Block Modal */
.block-modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background: rgba(15, 23, 42, 0.75) !important;
  backdrop-filter: blur(4px) !important;
  z-index: 99999 !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  padding: 16px !important;
  box-sizing: border-box !important;
}

.block-modal-container {
  width: 90% !important;
  max-width: 620px !important;
  max-height: 85vh !important;
  background: #ffffff !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  border-radius: 16px !important;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35) !important;
  overflow-y: auto !important;
  display: flex !important;
  flex-direction: column !important;
  position: relative !important;
  margin: auto !important;
}

.block-modal-header {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.block-warning-icon {
  font-size: 40px;
  animation: pulse-ring 2s infinite ease-in-out;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.08); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.block-modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #e11d48;
}

.block-warning-desc {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
  line-height: 1.5;
}

.block-modal-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.metric-block-card {
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.metric-block-card.warning {
  background: #fff5f5;
  border-color: #fee2e2;
}

.metric-block-card .lbl {
  font-size: 11px;
  color: #64748b;
  text-align: center;
}

.metric-block-card .sub-lbl-detail {
  font-size: 10px;
  color: #94a3b8;
  transform: scale(0.9);
  margin-top: 1px;
  text-align: center;
  white-space: nowrap;
}

.metric-block-card .val {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.metric-block-card .val.model-val {
  font-size: 12px;
  color: #3b82f6;
  word-break: break-all;
  text-align: center;
}

.metric-block-card .val.green-val {
  color: #10b981;
}

.metric-block-card .val.red-val {
  color: #ef4444;
}

.metric-block-card .val.orange-val {
  color: #f97316;
}

.metric-block-card .val small {
  font-size: 10px;
  font-weight: normal;
  color: #94a3b8;
}

.block-logistics-card {
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 12px;
  padding: 16px;
}

/* 浮动 Toast 弹窗 */
.global-toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(10px);
  border: 1px solid #e2e8f0;
  padding: 12px 28px;
  border-radius: 30px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 99999;
  font-weight: 600;
  font-size: 14px;
  animation: toast-in-out 3s ease forwards;
  pointer-events: none;
}
.global-toast.success {
  border-color: #bbf7d0;
  color: #15803d;
  background: rgba(240, 253, 250, 0.96);
}
.global-toast.error {
  border-color: #fecaca;
  color: #b91c1c;
  background: rgba(254, 242, 242, 0.96);
}
@keyframes toast-in-out {
  0% { top: -60px; opacity: 0; }
  8% { top: 24px; opacity: 1; }
  92% { top: 24px; opacity: 1; }
  100% { top: -60px; opacity: 0; }
}

.block-logistics-card.has-transit {
  background: #ecfdf5;
  border-color: #d1fae5;
}

.logistics-info {
  display: flex;
  gap: 12px;
}

.logistics-icon {
  font-size: 28px;
}

.logistics-detail {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.logistics-detail h4 {
  margin: 0;
  font-size: 14.5px;
  font-weight: 600;
  color: #065f46;
}

.no-transit .logistics-detail h4 {
  color: #92400e;
}

.logistics-detail p {
  margin: 0;
  font-size: 12.5px;
  color: #374151;
  line-height: 1.5;
}

.logistics-detail p strong {
  color: #047857;
  font-size: 13.5px;
}

.no-transit .logistics-detail p strong {
  color: #b45309;
}

.action-guide {
  margin-top: 4px !important;
  font-size: 12px !important;
  color: #6b7280 !important;
  background: rgba(255, 255, 255, 0.5);
  border-left: 3px solid #10b981;
  padding: 6px 8px;
  border-radius: 0 4px 4px 0;
}

.no-transit .action-guide {
  border-left-color: #f97316;
}

.block-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.block-modal-actions .btn {
  padding: 10px 20px;
  font-size: 13.5px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.block-modal-actions .btn.primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: #fff;
  border: none;
  box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
}

.block-modal-actions .btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 8px -1px rgba(37, 99, 235, 0.3);
}

.block-modal-actions .btn.ghost {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
}

.block-modal-actions .btn.ghost:hover {
  background: #e2e8f0;
}

/* Transition Animations */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.submit-status-button {
  white-space: nowrap;
}
.page-error { margin: 0; color: var(--danger); }

.panel-title-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
}

.panel-title-row h2 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.panel-hint {
  color: #64748b;
  font-size: 13px;
}

.compact-filter-grid {
  margin-bottom: 16px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  align-items: end;
}

.field-compact span {
  font-size: 12px;
  color: #64748b;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}


.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: #334155;
  font-size: 14px;
}

.field select,
.field input,
.cell-editor input,
.number-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  color: #0f172a;
  background: #fff;
  box-sizing: border-box;
}

.field select:focus,
.field input:focus,
.cell-editor input:focus,
.number-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.meta-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef2ff;
  color: #334155;
  font-size: 13px;
}

.table-wrap {
  overflow-x: auto;
}

.logistics-table-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  background: #ffffff;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 780px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 14px 16px !important;
  text-align: left;
  vertical-align: middle !important;
}

.data-table th {
  color: #334155;
  background: #f8fafc;
  font-weight: 600;
}

.cell-editor {
  display: grid;
  gap: 8px;
  min-width: 180px;
}

.logistics-table {
  min-width: 1460px;
}

.logistics-table-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.logistics-table-row:hover {
  background-color: #f1f5f9 !important;
}

.logistics-table th {
  white-space: nowrap;
}

.logistics-table td {
  white-space: normal;
}

.cell-code {
  min-width: 140px;
  font-family: "Consolas", "Courier New", monospace;
  font-size: 14px;
  color: #0f172a;
  word-break: break-all;
}

.cell-text {
  min-width: 160px;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.cell-number {
  min-width: 90px;
  white-space: nowrap;
}

.cell-datetime {
  min-width: 132px;
  white-space: nowrap;
  color: #334155;
}

.cell-elapsed {
  min-width: 96px;
  white-space: nowrap;
}

.cell-status {
  min-width: 118px;
  white-space: nowrap;
}

.stack-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 120px;
}

.action-inline {
  flex-direction: row;
  flex-wrap: nowrap;
  min-width: 232px;
}

.action-button {
  min-width: 118px;
}

.action-placeholder {
  color: #64748b;
  font-size: 13px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.2;
  background: #eef2ff;
  color: #334155;
  white-space: nowrap;
}

.clickable-pill {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.clickable-pill:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  filter: brightness(0.95);
}


.status-pill-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.status-pill.pending_arrival {
  background: #eff6ff;
  color: #1d4ed8;
}

.status-pill.pending_receive {
  background: #fff7ed;
  color: #c2410c;
}

.status-pill.pending_warehouse {
  background: #f0fdf4;
  color: #15803d;
}

.status-pill.completed {
  background: #ecfdf5;
  color: #047857;
}

.status-pill.cancelled {
  background: #fef2f2;
  color: #b91c1c;
}

.status-pill.abnormal {
  background: #fff1f2;
  color: #be123c;
}

.primary-button.arrival-button {
  border-color: #e5e7eb;
  background: #ffffff;
  color: #cbd5e1;
}

.primary-button.arrival-button.is-active {
  border-color: #1d4ed8;
  background: #1d4ed8;
  color: #fff;
}

.primary-button.receipt-button {
  border-color: #e5e7eb;
  background: #ffffff;
  color: #cbd5e1;
}

.primary-button.receipt-button.is-active {
  border-color: #c2410c;
  background: #c2410c;
  color: #fff;
}

.editable-plan-date {
  background: #dbeafe;
  color: #1d4ed8;
}

.editable-plan-date-cell {
  background: #eff6ff;
}

.editable-plan-date-cell input {
  background: #f8fbff;
}

.btn, .primary-button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  box-sizing: border-box !important;
}

.primary-button {
  border-radius: 10px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.primary-button {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
}

.primary-button:disabled,
.btn:disabled {
  opacity: 1;
  cursor: not-allowed;
}

.loading-text,
.empty-box,
.error-box {
  padding: 14px 16px;
  border-radius: 10px;
  font-size: 14px;
}

.loading-text,
.empty-box {
  background: #f8fafc;
  color: #475569;
}

.error-box {
  background: #fff1f2;
  color: #be123c;
}

.action-message {
  margin: 0;
  font-size: 14px;
}

.action-message.success {
  color: #15803d;
}

.action-message.error {
  color: #be123c;
}

@media (max-width: 720px) {
  .tube-page-main {
    padding-bottom: 16px;
  }

  .topbar,
  .panel-title-row {
    flex-direction: column;
    align-items: stretch;
    gap: 10px !important;
  }

  .fitting-card-header {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
    padding: 10px 12px !important;
  }

  .fitting-card-header .header-left-meta {
    width: 100% !important;
  }

  .fitting-card-header .header-right-meta {
    width: 100% !important;
    justify-content: space-between !important;
    border-top: 1px dashed #e2e8f0 !important;
    padding-top: 8px !important;
  }

  .block-modal-metrics {
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 8px !important;
  }

  .table-responsive-wrapper {
    margin-left: -4px;
    margin-right: -4px;
    overflow-x: visible !important;
  }

  /* 移动端 (<=720px) 明细表格自适应卡片化重构，彻底解决死硬表格列被严重挤压、文字叠字、高度拉高的问题 */
  .demand-fitting-table {
    min-width: 0 !important;
    border: none !important;
    table-layout: auto !important;
    background: transparent !important;
  }

  .demand-fitting-table thead {
    display: none !important;
  }

  .demand-fitting-table tbody {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
  }

  .demand-fitting-table tbody tr {
    display: flex !important;
    flex-direction: column !important;
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    padding: 10px 12px !important;
    gap: 6px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
  }

  .demand-fitting-table tbody td {
    border: none !important;
    padding: 0 !important;
    text-align: left !important;
    width: 100% !important;
  }

  /* 隐去无意义纯数字序号列 */
  .demand-fitting-table tbody td.col-index {
    display: none !important;
  }

  /* 卡片第 1 区域：类型 Badge 与型号规格吸纳整行全宽，绝不折叠压缩 */
  .demand-fitting-table tbody td.col-type {
    display: inline-block !important;
    margin-bottom: 2px !important;
  }

  .demand-fitting-table tbody td.col-model {
    width: 100% !important;
  }

  .demand-fitting-table tbody td.col-model strong {
    font-size: 13.5px !important;
    color: #0f172a !important;
    word-break: break-word !important;
  }

  /* 卡片第 2 区域：发货件数与到货确认数 (浅色包围流式 Grid 双栏) */
  .demand-fitting-table tbody td.col-shipped,
  .demand-fitting-table tbody td.col-arrived {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
    padding: 6px 10px !important;
    font-size: 12px !important;
    box-sizing: border-box !important;
  }

  .demand-fitting-table tbody td.col-shipped .mobile-lbl,
  .demand-fitting-table tbody td.col-arrived .mobile-lbl {
    display: inline-block !important;
    color: #64748b !important;
    font-weight: 500 !important;
  }

  /* 卡片第 3 区域：状态 Badge 与单项确认操作按钮 (底部并排布局) */
  .demand-fitting-table tbody td.col-status {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-top: 4px !important;
    padding-top: 6px !important;
    border-top: 1px dashed #e2e8f0 !important;
  }

  .demand-fitting-table tbody td.col-action {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
  }

  /* 移动端 (<=720px) 到货与施工接收记录表格 (logistics-table) 响应式卡片化精细重构 */
  .logistics-table {
    min-width: 0 !important;
    border: none !important;
    table-layout: auto !important;
    background: transparent !important;
  }

  .logistics-table thead {
    display: none !important;
  }

  .logistics-table tbody {
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
  }

  .logistics-table tbody tr.logistics-table-row {
    display: flex !important;
    flex-direction: column !important;
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    padding: 12px 14px !important;
    gap: 6px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    box-sizing: border-box !important;
  }

  .logistics-table tbody td {
    border: none !important;
    padding: 0 !important;
    text-align: left !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }

  /* 状态与车牌 */
  .logistics-table tbody td.col-status {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    margin-bottom: 2px !important;
  }

  .logistics-table tbody td.col-code-order::before { content: "单号: "; color: #94a3b8; font-size: 11.5px; }
  .logistics-table tbody td.col-code-shipment::before { content: "车次: "; color: #94a3b8; font-size: 11.5px; }
  .logistics-table tbody td.col-shipped-time::before { content: "发货时间: "; color: #94a3b8; font-size: 11.5px; }
  .logistics-table tbody td.col-arrived-time::before { content: "确认时间: "; color: #94a3b8; font-size: 11.5px; }
  
  .logistics-table tbody td.col-shipped-qty,
  .logistics-table tbody td.col-confirm-qty {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 6px !important;
    padding: 6px 10px !important;
    font-size: 12px !important;
  }

  .logistics-table tbody td.col-shipped-qty::before { content: "工厂发货量"; color: #64748b; font-weight: 500; }
  .logistics-table tbody td.col-confirm-qty::before { content: "到货/接收确认量"; color: #047857; font-weight: 500; }

  .logistics-table tbody td.col-text-model strong {
    font-size: 14px !important;
    color: #0f172a !important;
  }

  /* 确认量与操作按钮行 */
  .logistics-table tbody td.col-action-btns {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
    margin-top: 4px !important;
    padding-top: 6px !important;
    border-top: 1px dashed #e2e8f0 !important;
  }
}

/* 磨砂玻璃态微数据看板 (Quick Dashboard) */
.meta-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.meta-card {
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(226, 232, 240, 0.8) !important;
  border-radius: 14px !important;
  padding: 16px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative !important;
  overflow: hidden !important;
  box-sizing: border-box;
}

.meta-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: linear-gradient(180deg, #6366f1 0%, #3b82f6 100%);
}

.meta-card.highlight::before {
  background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);
}

.meta-card:hover {
  transform: translateY(-4px) !important;
  background: rgba(255, 255, 255, 0.85) !important;
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.08), 0 4px 6px -2px rgba(59, 130, 246, 0.04) !important;
  border-color: rgba(147, 197, 253, 0.5) !important;
}

.meta-label {
  font-size: 12px !important;
  color: #64748b !important;
  font-weight: 500 !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-value {
  font-size: 20px !important;
  color: #1e293b !important;
  font-weight: 700 !important;
  font-family: "Inter", "Outfit", -apple-system, sans-serif !important;
}

/* 呼吸灯特效 - Excel粘贴激活区 */
.paste-zone {
  display: flex !important;
  align-items: center !important;
  gap: 16px !important;
  border: 2px dashed #cbd5e1 !important;
  border-radius: 14px !important;
  padding: 16px 20px !important;
  background: #f8fafc !important;
  cursor: pointer !important;
  margin-bottom: 20px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-sizing: border-box;
}

.paste-zone:hover, .paste-zone:focus {
  outline: none !important;
  border-color: #3b82f6 !important;
  background: #eff6ff !important;
  transform: scale(1.005) !important;
  animation: pulse-glow-indigo 2s infinite !important;
}

.paste-icon {
  font-size: 28px !important;
  background: #dbeafe !important;
  padding: 10px !important;
  border-radius: 12px !important;
  color: #2563eb !important;
  transition: all 0.3s ease !important;
  display: flex;
  align-items: center;
  justify-content: center;
}

.paste-zone:hover .paste-icon, .paste-zone:focus .paste-icon {
  background: #3b82f6 !important;
  color: #ffffff !important;
}

.paste-desc {
  display: flex !important;
  flex-direction: column !important;
  gap: 4px !important;
  text-align: left !important;
}

.paste-desc strong {
  font-size: 15px !important;
  color: #1e293b !important;
}

.paste-desc span {
  font-size: 13px !important;
  color: #64748b !important;
}

.paste-zone:hover .paste-desc span {
  color: #2563eb !important;
}

@keyframes pulse-glow-indigo {
  0% {
    box-shadow: 0 0 0 0px rgba(59, 130, 246, 0.25);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
  }
  100% {
    box-shadow: 0 0 0 0px rgba(59, 130, 246, 0);
  }
}

/* 升级表格 Hover 行高亮 */
.data-table tbody tr {
  transition: background-color 0.2s ease;
}

.data-table tbody tr:hover {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.03) 0%, rgba(255, 255, 255, 0) 100%) !important;
}

/* 🔹 一级物料大类分段控制器 (Segmented Category Bar) */
.category-segment-wrapper {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
  border-radius: 14px !important;
  padding: 4px !important;
  margin-bottom: 6px !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.02) !important;
  box-sizing: border-box;
}

.category-segment-bar {
  display: flex !important;
  gap: 6px !important;
  width: 100% !important;
}

.category-segment-btn {
  flex: 1 !important;
  border: 1px solid transparent !important;
  background: transparent !important;
  padding: 8px 16px !important;
  border-radius: 10px !important;
  font-size: 14.5px !important;
  font-weight: 600 !important;
  color: #64748b !important;
  cursor: pointer !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
}

.category-segment-btn:hover {
  color: #1e293b !important;
  background: rgba(255, 255, 255, 0.7) !important;
}

.category-segment-btn.active {
  color: #1e40af !important;
  background: #ffffff !important;
  border-color: #dbeafe !important;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1), 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}

.category-segment-btn .cat-icon {
  font-size: 15px;
  line-height: 1;
}

.category-segment-btn .cat-label {
  font-size: 14px;
  letter-spacing: 0.2px;
}

.category-segment-btn .cat-count {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 7px;
  border-radius: 20px;
  background: #e2e8f0;
  color: #64748b;
  transition: all 0.25s ease;
}

.category-segment-btn.active .cat-count {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

/* Vue Tabs 高端样式切换 */
.tube-tabs-header-wrap {
  background: rgba(241, 245, 249, 0.8) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  margin-bottom: 14px !important;
  border: 1px solid #e2e8f0 !important;
  box-sizing: border-box;
}

.tube-tabs-header {
  display: flex !important;
  gap: 4px !important;
  width: 100% !important;
}

.tube-tabs-header button {
  flex: 1 !important;
  border: none !important;
  background: transparent !important;
  padding: 12px 16px !important;
  border-radius: 10px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #475569 !important;
  cursor: pointer !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
}

.tube-tabs-header button:hover {
  color: #1e293b !important;
  background: rgba(255, 255, 255, 0.5) !important;
}

.tube-tabs-header button.active {
  color: #2563eb !important;
  background: #ffffff !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
}

/* 🔮 首二日填报决策沙盘 Hover 悬浮气泡极致优化样式 */
.cell-model-name {
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
  justify-content: center !important;
  gap: 6px !important;
  min-width: 180px !important;
}

.model-name-text {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}

.model-badge-row {
  display: flex;
  align-items: center;
  width: 100%;
}

.sandbox-trigger-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
  cursor: help;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  border: 1px solid transparent;
}

/* 触发器徽章颜色状态 */
.sandbox-trigger-badge.trigger-safe {
  background: #dcfce7 !important;
  color: #15803d !important;
  border-color: rgba(187, 247, 208, 0.6) !important;
}

.sandbox-trigger-badge.trigger-safe:hover {
  background: #bbf7d0 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(34, 197, 94, 0.15);
}

.sandbox-trigger-badge.trigger-danger {
  background: #fee2e2 !important;
  color: #be123c !important;
  border-color: rgba(254, 226, 226, 0.6) !important;
  animation: badge-pulse-danger 2s infinite ease-in-out;
}

.sandbox-trigger-badge.trigger-danger:hover {
  background: #fca5a5 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(239, 68, 68, 0.15);
}

.sandbox-trigger-badge.trigger-locked {
  background: #f1f5f9 !important;
  color: #64748b !important;
  border-color: rgba(226, 232, 240, 0.8) !important;
  border-style: dashed !important;
}

.sandbox-trigger-badge.trigger-locked:hover {
  background: #e2e8f0 !important;
  transform: translateY(-1px);
}

@keyframes badge-pulse-danger {
  0%, 100% { border-color: rgba(254, 226, 226, 0.6); }
  50% { border-color: rgba(239, 68, 68, 0.4); }
}

/* 🔮 Hover Popover 容器 (SaaS Glassmorphism) */
.sandbox-popover-card {
  position: fixed;
  z-index: 9995;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(10px);
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 
    0 10px 25px -5px rgba(15, 23, 42, 0.1), 
    0 8px 10px -6px rgba(15, 23, 42, 0.05),
    0 0 1px 1px rgba(0, 0, 0, 0.02);
  max-width: 320px;
  min-width: 250px;
  pointer-events: auto;
  animation: popover-fade-in 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.popover-arrow {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 12px;
  height: 12px;
  background: #ffffff;
  border-right: 1px solid #cbd5e1;
  border-bottom: 1px solid #cbd5e1;
  z-index: -1;
}

@keyframes popover-fade-in {
  from { opacity: 0; transform: translate(-50%, -95%) scale(0.95); }
  to { opacity: 1; transform: translate(-50%, -100%) scale(1); }
}

/* 气泡头部 */
.popover-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.popover-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.popover-badge-label {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 999px;
  white-space: nowrap;
}

.popover-badge-label.safe-green {
  background: #dcfce7;
  color: #15803d;
}

.popover-badge-label.danger-red {
  background: #fee2e2;
  color: #be123c;
}

.popover-badge-label.locked-grey {
  background: #f1f5f9;
  color: #475569;
}

/* 指标表格网格 */
.popover-metrics-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #64748b;
}

.metric-val.text-bold {
  font-weight: 600;
  color: #1e293b;
}

.metric-val.text-danger {
  color: #ef4444;
}

.popover-divider {
  height: 1px;
  background: #f1f5f9;
  margin: 8px 0;
}

/* 气泡建议框 */
.popover-suggestion-box {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  background: #f8fafc;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.suggestion-icon {
  font-size: 13px;
  margin-top: 1px;
}

.suggestion-text {
  font-size: 11px;
  color: #475569;
  line-height: 1.45;
  text-align: left;
}

.popover-jump-hint {
  display: block;
  margin-top: 6px;
  color: #2563eb;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s;
}

.popover-jump-hint:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

/* 🔒 首二日顺序填报控制锁引导横幅 */
.flow-gateway-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: linear-gradient(135deg, rgba(254, 243, 199, 0.9) 0%, rgba(253, 230, 138, 0.8) 100%);
  border: 1px solid rgba(245, 158, 11, 0.5);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
  box-shadow: 0 4px 10px rgba(245, 158, 11, 0.08);
  box-sizing: border-box;
}

.gateway-icon {
  font-size: 20px;
  background: #f59e0b;
  color: #ffffff;
  padding: 6px;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gateway-desc {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  text-align: left;
}

.gateway-desc strong {
  font-size: 14px;
  color: #78350f;
}

.gateway-desc span {
  font-size: 12px;
  color: #92400e;
}

.gateway-link-btn {
  background: #2563eb !important;
  color: #ffffff !important;
  border: none !important;
  padding: 8px 16px !important;
  border-radius: 8px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 2px 4px rgba(37, 99, 235, 0.15) !important;
  animation: link-pulse-glow 2s infinite !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  white-space: nowrap !important;
}

.gateway-link-btn:hover {
  background: #1d4ed8 !important;
  transform: translateY(-1px) !important;
}



@keyframes link-pulse-glow {
  0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(37, 99, 235, 0); }
  100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
}

@keyframes slide-down-fade {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-slide-down {
  animation: slide-down-fade 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 🔩 多维多选下拉筛选工具栏 (Clean Multi-Select Dropdown Toolbar) */
.fitting-filter-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 8px 12px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

.ms-dropdown-container {
  position: relative;
  display: inline-block;
}

.ms-dropdown-trigger {
  height: 34px;
  padding: 0 10px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  color: #334155;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  user-select: none;
  white-space: nowrap;
}

.ms-dropdown-trigger:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}

.ms-dropdown-trigger.has-value {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
  font-weight: 600;
}

.ms-dropdown-trigger.is-open {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.ms-label-icon {
  font-size: 13px;
}

.ms-label-text {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ms-badge {
  background: #2563eb;
  color: #ffffff;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
  font-weight: 700;
}

.ms-clear-btn {
  font-size: 11px;
  color: #94a3b8;
  padding: 0 2px;
  border-radius: 50%;
  cursor: pointer;
}

.ms-clear-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.ms-arrow {
  font-size: 10px;
  color: #64748b;
  margin-left: 2px;
}

/* 下拉浮层菜单 */
.ms-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 60;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  min-width: 180px;
  max-width: 260px;
  padding: 6px 0;
  animation: slide-down-fade 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

.ms-menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px 6px 10px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 11.5px;
  color: #64748b;
}

.ms-menu-title {
  font-weight: 600;
  color: #475569;
}

.ms-menu-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ms-menu-actions a {
  color: #2563eb;
  text-decoration: none;
  font-size: 11px;
}

.ms-menu-actions a:hover {
  text-decoration: underline;
}

.ms-menu-actions .sep {
  color: #cbd5e1;
  font-size: 10px;
}

.ms-menu-list {
  max-height: 220px;
  overflow-y: auto;
  padding: 4px 0;
}

.ms-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  font-size: 12.5px;
  color: #334155;
  cursor: pointer;
  transition: background 0.15s ease;
  user-select: none;
}

.ms-menu-item:hover {
  background: #f8fafc;
  color: #0f172a;
}

.ms-menu-item.checked {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 500;
}

.ms-menu-item input[type="checkbox"] {
  cursor: pointer;
  accent-color: #2563eb;
  width: 14px;
  height: 14px;
}

.ms-item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ms-item-count {
  font-size: 11px;
  color: #94a3b8;
}

/* 搜索框与重置按钮 */
.ms-search-box {
  flex: 1;
  min-width: 180px;
}

.reset-filter-btn {
  height: 34px !important;
  font-size: 12px !important;
  color: #ef4444 !important;
  border-color: #fecaca !important;
  background: #fff5f5 !important;
  padding: 0 10px !important;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.reset-filter-btn:hover {
  background: #fee2e2 !important;
  border-color: #fca5a5 !important;
}
</style>
