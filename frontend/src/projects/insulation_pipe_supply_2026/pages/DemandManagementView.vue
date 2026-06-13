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
            :disabled="!selectedStationId || !canSubmitCurrentProject || submitStatusLoading"
            @click="handleStationSubmitClick"
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
            <span>当前管理的换热站</span>
            <select v-model="selectedStationId" :disabled="optionsLoading || !stationOptions.length">
              <option value="" disabled>请选择要操作的换热站</option>
              <option v-for="station in stationOptions" :key="station.station_id" :value="station.station_id">
                {{ station.station_name }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>展示截止日期</span>
            <input v-model="showDate" type="date" :disabled="!isGlobalAdmin" />
          </label>
        </div>

        <!-- 磨砂玻璃态微数据看板 (Quick Dashboard) -->
        <div class="meta-dashboard">
          <div class="meta-card">
            <span class="meta-label">授权范围</span>
            <strong class="meta-value">{{ stationOptions.length }} 个站</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">保温管型号</span>
            <strong class="meta-value">{{ pipeModelOptions.length }} 种</strong>
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

      <!-- 选项卡导航 (Responsive Tabs Header) -->
      <div class="tube-tabs-header-wrap" v-if="selectedStationId">
        <div class="tube-tabs-header">
          <button 
            type="button" 
            :class="{ active: activeTab === 'usage' }" 
            @click="activeTab = 'usage'"
          >
            📊 每日使用消耗填报
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'plan' }" 
            @click="activeTab = 'plan'"
          >
            🕒 三日滚动计划填报
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'logistics' }" 
            @click="activeTab = 'logistics'"
          >
            🚚 现场到货与接收确认
          </button>
          <button 
            type="button" 
            :class="{ active: activeTab === 'baseline' }" 
            @click="activeTab = 'baseline'"
          >
            📋 基准设计量台账
          </button>
        </div>
      </div>

      <!-- Tab内容区域 -->
      <div class="tube-tab-content-wrap" v-if="selectedStationId">
        
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
                :disabled="planLoading || savePlanLoading || !selectedStationId || !canSubmitCurrentProject || planEditableDays <= 0"
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
                <span>由于当前换热站前日实际消耗尚未结清上报，为保证盈缺预测100%可靠，滚动第三日填报已被自动锁定。</span>
              </div>
              <button type="button" class="gateway-link-btn" @click="activeTab = 'usage'">
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
                    <th class="sandbox-th">🔮 首二日填报决策沙盘 (决策辅助)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in planRows" :key="row.pipeModelId">
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
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
                    <td class="cell-sandbox">
                      <div class="sandbox-badge" :class="getSandboxStatusClass(row)">
                        <div class="sandbox-header-row">
                          <span class="sandbox-title">🔮 首二日后盈缺</span>
                          <span class="result-chip" :class="getPredictionStatusClass(row)">
                            {{ getPredictionStatusLabel(row) }}
                          </span>
                        </div>
                        <div class="sandbox-metrics">
                          <span class="metric-item" title="当前现场已确认接收在库总量">在库: <strong>{{ strictPlanningFlowControl && !isUsageSubmitted ? '待结算' : `${row.stationInventoryQty} 米` }}</strong></span>
                          <span class="metric-item" title="当前所有已发货在途及到站待确认的总量">在途: <strong>{{ row.inboundPipelineQty }} 米</strong></span>
                          <span class="metric-item" title="未来三日计划中前两日计划量之和">前两日需: <strong>{{ getPrevTwoDaysPlanSum(row) }} 米</strong></span>
                        </div>
                        <div class="sandbox-suggestion">
                          💡 {{ getSandboxSuggestion(row) }}
                        </div>
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
                <span class="panel-hint">登记昨日（{{ usageDate || '今日' }}）各保温管型号的实际施工消耗与现场损耗。计量单位：米。</span>
              </div>
              <button
                type="button"
                class="primary-button"
                :disabled="usageLoading || saveUsageLoading || !selectedStationId || !canSubmitCurrentProject"
                @click="saveUsageSheet"
              >
                {{ saveUsageLoading ? '提交中...' : '提交消耗与损耗数据' }}
              </button>
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
                <h2>换热站设计与采购基准量</h2>
                <span class="panel-hint">展示当前换热站的设计总量与全局计划采购总量，供日常对照。计量单位：米。</span>
              </div>
            </div>

            <div v-if="baselineLoading" class="loading-text">正在加载基准量...</div>
            <div v-else-if="baselineError" class="error-box">{{ baselineError }}</div>
            <div v-else-if="!baselineRows.length" class="empty-box">当前换热站暂无基准量记录。</div>
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
                <button type="button" class="primary-button" :disabled="pendingLoading || !selectedStationId" @click="applyPendingFilters">
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
                  <option v-for="model in pipeModelOptions" :key="model.pipe_model_id" :value="model.pipe_model_id">
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
                    <th>订单号</th>
                    <th>运输车次号</th>
                    <th>车牌号</th>
                    <th>供给主体</th>
                    <th>型号</th>
                    <th>发货量（米）</th>
                    <th>发货时间</th>
                    <th>确认到货时间</th>
                    <th>在途时长</th>
                    <th class="cell-status">状态</th>
                    <th>确认量（米）</th>
                    <th>确认操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in pendingRows" :key="row.deliveryId">
                    <td class="cell-code">{{ row.deliveryCode || row.deliveryId }}</td>
                    <td class="cell-code">{{ row.shipmentNo || '—' }}</td>
                    <td class="cell-text" :title="row.vehiclePlateNo || '—'">{{ row.vehiclePlateNo || '—' }}</td>
                    <td class="cell-text" :title="row.supplyEntityName">{{ row.supplyEntityName }}</td>
                    <td class="cell-text" :title="row.pipeModelName">{{ row.pipeModelName }}</td>
                    <td class="cell-number">{{ formatNumber(row.shippedQty) }}</td>
                    <td class="cell-datetime">{{ formatDateTimeDisplay(row.shippedAt) || '—' }}</td>
                    <td class="cell-datetime">{{ formatDateTimeDisplay(row.arrivedConfirmAt) || '—' }}</td>
                    <td class="cell-elapsed">{{ formatDeliveryElapsedDisplay(row) }}</td>
                    <td class="cell-status">
                      <div class="status-pill-group">
                        <span class="status-pill" :class="row.status">
                          {{ row.statusLabel }}
                        </span>
                        <span v-if="row.abnormalFlag" class="status-pill abnormal">
                          {{ getAbnormalLabel(row) }}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div v-if="row.status === 'pending_arrival'" class="stack-controls">
                        <input
                          v-model.number="row.arrivalConfirmQty"
                          type="number"
                          min="0"
                          :max="row.shippedQty"
                          step="1"
                        />
                      </div>
                      <div v-else-if="row.status === 'pending_receive'" class="stack-controls">
                        <input
                          v-model.number="row.receiptConfirmQty"
                          type="number"
                          min="0"
                          :max="row.arrivedQty"
                          step="1"
                        />
                      </div>
                      <span v-else class="cell-number">{{ formatNumber(row.receivedQty || row.arrivedQty) }}</span>
                    </td>
                    <td>
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
                      <span v-else class="action-placeholder">{{ getDeliveryStatusLabel(row.status) }}</span>
                    </td>
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
          <h3>请首先选择要操作的换热站</h3>
          <p>在上方“工作台全局筛选”下拉框中选择具体的换热站后，系统将为您正式解锁三日滚动计划、使用量填报及到货到货确认等多标签管理模块。</p>
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
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh, getDeliveryStatus } from './shared'
import ExportSettingsModal from './ExportSettingsModal.vue'
import {
  confirmTubeDemandManagementDeliveryArrival,
  confirmTubeDemandManagementDeliveryReceipt,
  getTubeDemandManagementBaseline,
  getTubeDemandManagementLogisticsRecords,
  getTubeDemandManagementOptions,
  getTubeDemandManagementPlanMatrix,
  getTubeDemandManagementUsageSheet,
  saveTubeDemandManagementPlanMatrix,
  saveTubeDemandManagementUsageSheet,
  submitTubeDemandManagementStationStatus
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'

const auth = useAuthStore()
const {
  errorMessage,
  breadcrumbItems,
  goProjectPages
} = useTubePageShell('需求侧管理入口')

const optionsLoading = ref(false)
const optionsError = ref('')
const stationOptions = ref([])
const pipeModelOptions = ref([])
const currentGroup = ref('')

const selectedStationId = ref('')
const activeTab = ref('usage')
const showExportModal = ref(false)
const blockModalVisible = ref(false)
const blockModalData = ref(null)
const allPendingRows = ref([])

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
  if (!selectedStationId.value || activeTab.value !== 'plan') {
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

const showDate = ref('')
const anchorDate = ref('')
const usageDate = ref('')
const planEditableDays = ref(3)
const strictPlanningFlowControl = ref(true)
const isUsageSubmitted = ref(false)

const baselineLoading = ref(false)
const baselineError = ref('')
const baselineRows = ref([])

const planLoading = ref(false)
const planError = ref('')
const planDates = ref([])
const planRows = ref([])
const savePlanLoading = ref(false)

const usageLoading = ref(false)
const usageError = ref('')
const usageRows = ref([])
const saveUsageLoading = ref(false)
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
  return Boolean(canConfirmArrival.value && row?.status === 'pending_arrival')
}

function canClickReceipt(row) {
  return Boolean(canConfirmReceipt.value && row?.status === 'pending_receive')
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

function normalizeBaselineRows(rows) {
  return (rows || []).map((row) => ({
    pipeModelId: row.pipe_model_id || row.pipeModelId,
    pipeModelName: row.pipe_model_name || row.pipeModelName || row.model_name || '未命名型号',
    designQuantity: row.design_total_qty || row.designQuantity || row.design_qty || 0,
    purchaseQuantity: row.purchase_total_qty || row.purchaseQuantity || row.purchase_qty || row.purchase_plan_qty || 0,
    remarks: row.remarks || row.remark || ''
  }))
}

function normalizePlanRows(rows, dates) {
  return (rows || []).map((row) => {
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
      stationInventoryQty: Number(row.station_inventory_qty ?? row.stationInventoryQty ?? 0),
      inboundPipelineQty: Number(row.inbound_pipeline_qty ?? row.inboundPipelineQty ?? 0),
      values: valueMap
    }
  })
}

function normalizeUsageRows(rows) {
  return (rows || []).map((row) => ({
    pipeModelId: row.pipe_model_id || row.pipeModelId,
    pipeModelName: row.pipe_model_name || row.pipeModelName || row.model_name || '未命名型号',
    usedQty: Number(row.usage_qty ?? row.used_qty ?? row.usedQty ?? 0),
    lossQty: Number(row.loss_qty ?? row.lossQty ?? 0),
    remarks: row.remark || row.remarks || ''
  }))
}

function normalizePendingRows(rows) {
  return (rows || []).map((row) => ({
    deliveryId: row.delivery_id || row.deliveryId || row.id,
    deliveryCode: row.delivery_code || row.deliveryCode || '',
    shipmentNo: row.shipment_no || row.shipmentNo || '',
    vehiclePlateNo: row.vehicle_plate_no || row.vehiclePlateNo || '',
    supplyEntityName: row.supply_entity_name || row.supplyEntityName || row.supply_entity_id || row.supplyEntityId || '—',
    pipeModelName: row.pipe_model_name || row.pipeModelName || '未命名型号',
    status: row.status || '',
    statusLabel: getDeliveryStatusLabel(row.status),
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
    arrivalRemark: '',
    receiptRemark: ''
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

function getDeliveryStatusLabel(status) {
  return getDeliveryStatus(status).label
}

function normalizeOptionsPayload(response) {
  return {
    stationOptions: response.station_options || response.stations || [],
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
    stationOptions.value = normalized.stationOptions
    pipeModelOptions.value = normalized.pipeModelOptions
    currentGroup.value = normalized.currentGroup
    showDate.value = normalized.showDate || getTodayString(-1)
    planEditableDays.value = Number.isFinite(normalized.planEditableDays) ? normalized.planEditableDays : 3
    const stationIdSet = new Set(stationOptions.value.map((item) => String(item.station_id || '')))
    if (!selectedStationId.value || !stationIdSet.has(selectedStationId.value)) {
      selectedStationId.value = stationOptions.value[0]?.station_id || ''
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
  if (!selectedStationId.value) {
    baselineRows.value = []
    return
  }
  baselineLoading.value = true
  baselineError.value = ''
  try {
    const response = await getTubeDemandManagementBaseline(PROJECT_KEY, selectedStationId.value)
    baselineRows.value = normalizeBaselineRows(response.rows)
  } catch (error) {
    baselineError.value = error?.message || '加载基准量失败'
    baselineRows.value = []
  } finally {
    baselineLoading.value = false
  }
}

async function loadPlanMatrix() {
  if (!selectedStationId.value || !anchorDate.value) {
    planDates.value = []
    planRows.value = []
    return
  }
  planLoading.value = true
  planError.value = ''
  try {
    const response = await getTubeDemandManagementPlanMatrix(PROJECT_KEY, selectedStationId.value, anchorDate.value)
    const dates = response.plan_dates || []
    planDates.value = dates
    planRows.value = normalizePlanRows(response.rows, dates)
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
  if (!selectedStationId.value || !usageDate.value) {
    usageRows.value = []
    return
  }
  usageLoading.value = true
  usageError.value = ''
  try {
    const response = await getTubeDemandManagementUsageSheet(PROJECT_KEY, selectedStationId.value, usageDate.value)
    usageRows.value = normalizeUsageRows(response.rows)
  } catch (error) {
    usageError.value = error?.message || '加载实际使用数据失败'
    usageRows.value = []
  } finally {
    usageLoading.value = false
  }
}

async function loadAllPendingLogistics() {
  if (!selectedStationId.value) {
    allPendingRows.value = []
    return
  }
  try {
    const response = await getTubeDemandManagementLogisticsRecords(PROJECT_KEY, selectedStationId.value, {})
    allPendingRows.value = normalizePendingRows(response.rows)
  } catch (error) {
    console.error('Failed to load all pending logistics for export:', error)
  }
}

async function loadLogisticsRecords() {
  if (!selectedStationId.value) {
    pendingRows.value = []
    pendingError.value = ''
    pendingLoading.value = false
    return
  }
  pendingLoading.value = true
  pendingError.value = ''
  try {
    const response = await getTubeDemandManagementLogisticsRecords(PROJECT_KEY, selectedStationId.value, {
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
  deliveryActionLoadingKey.value = `receipt-${row.deliveryId}`
  clearActionMessage()
  try {
    await confirmTubeDemandManagementDeliveryReceipt(PROJECT_KEY, row.deliveryId, {
      received_qty: receivedQty,
      remark: row.receiptRemark || ''
    })
    setActionMessage('success', `发货单 ${row.deliveryCode || row.deliveryId} 施工接收已确认。`)
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

async function reloadStationData() {
  clearActionMessage()
  await Promise.all([
    loadBaseline(),
    loadPlanMatrix(),
    loadUsageSheet(),
    loadLogisticsRecords(),
    loadAllPendingLogistics()
  ])
}

async function refreshRealtimeConfig() {
  await loadOptions()
  await reloadStationData()
}

async function savePlanMatrix() {
  if (!selectedStationId.value || !planDates.value.length || planEditableDays.value <= 0) {
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
      station_id: selectedStationId.value,
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
  if (!selectedStationId.value || !usageDate.value) {
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
      station_id: selectedStationId.value,
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

async function handleStationSubmitClick() {
  if (!selectedStationId.value || !canSubmitCurrentProject.value) {
    return
  }
  submitStatusLoading.value = true
  clearActionMessage()
  try {
    const response = await submitTubeDemandManagementStationStatus(PROJECT_KEY, {
      station_id: selectedStationId.value,
      remark: ''
    })
    const submittedDate = response?.submission?.data_submit_date || anchorDate.value || '未设置'
    setActionMessage('success', `换热站 ${selectedStationId.value} 已标记为提交完成，提交日期为 ${submittedDate}。`)
  } catch (error) {
    setActionMessage('error', getErrorMessage(error, '提交换热站填报状态失败'))
  } finally {
    submitStatusLoading.value = false
  }
}

watch(selectedStationId, () => {
  reloadStationData()
})

watch(usageDate, (value, oldValue) => {
  if (!selectedStationId.value || !value || value === oldValue) {
    return
  }
  loadUsageSheet()
})

onMounted(async () => {
  nowTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
  await refreshRealtimeConfig()
})

useTubeRealtimeRefresh(refreshRealtimeConfig)

onBeforeUnmount(() => {
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
  const stock = Number(row.stationInventoryQty || 0)
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

// 决策沙盘的外层状态样式类
function getSandboxStatusClass(row) {
  if (strictPlanningFlowControl.value && !isUsageSubmitted.value) {
    return 'status-locked'
  }
  const prediction = getTailDayPrediction(row)
  return prediction >= 0 ? 'status-safe' : 'status-alert'
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
    return '前日(昨日)实际使用消耗尚未上报结清！为了避免给您的三日计划提供虚假的盈缺预测，请先前往‘每日使用消耗填报’中提交昨日消耗，系统将即时为您解锁首二日后库存盈缺推演与第三日计划填报。'
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
</script>

<style scoped>
/* Premium Usage Block Modal */
.block-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(12px);
  z-index: 2000;
  display: flex;
  justify-content: center;
  align-items: center;
}

.block-modal-container {
  width: 90%;
  max-width: 620px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 16px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
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

/* Vue Tabs 高端样式切换 */
.tube-tabs-header-wrap {
  background: rgba(241, 245, 249, 0.8) !important;
  border-radius: 14px !important;
  padding: 6px !important;
  margin-bottom: 16px !important;
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

/* 🔮 首二日填报决策沙盘殿堂级 UI 样式 */
.sandbox-th {
  min-width: 330px !important;
  max-width: 360px !important;
}

.cell-sandbox {
  padding: 8px 10px !important;
}

.sandbox-badge {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-radius: 12px;
  padding: 10px 12px;
  box-sizing: border-box;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
}

.sandbox-badge::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
}

/* 安全盈余卡片 */
.sandbox-badge.status-safe {
  background: rgba(240, 253, 244, 0.6) !important;
  border: 1px solid rgba(187, 247, 208, 0.7) !important;
}

.sandbox-badge.status-safe::before {
  background: linear-gradient(180deg, #10b981 0%, #059669 100%);
}

.sandbox-badge.status-safe:hover {
  background: rgba(240, 253, 244, 0.95) !important;
  border-color: rgba(34, 197, 94, 0.4) !important;
  box-shadow: 0 4px 10px rgba(16, 185, 129, 0.08);
}

/* 缺口警报卡片 */
.sandbox-badge.status-alert {
  background: rgba(254, 242, 242, 0.6) !important;
  border: 1px solid rgba(254, 226, 226, 0.7) !important;
  animation: border-glow-alert 3s infinite ease-in-out;
}

.sandbox-badge.status-alert::before {
  background: linear-gradient(180deg, #ef4444 0%, #be123c 100%);
}

.sandbox-badge.status-alert:hover {
  background: rgba(254, 242, 242, 0.95) !important;
  border-color: rgba(239, 68, 68, 0.4) !important;
  box-shadow: 0 4px 10px rgba(239, 68, 68, 0.08);
}

.sandbox-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.sandbox-title {
  font-size: 12px;
  font-weight: 700;
  color: #334155;
  letter-spacing: 0.02em;
}

.result-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.result-chip.safe-green {
  background: #dcfce7;
  color: #15803d;
}

.result-chip.danger-red {
  background: #fee2e2;
  color: #be123c;
  animation: pulse-danger-text 2s infinite ease-in-out;
}

.sandbox-metrics {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
  border-bottom: 1px dashed rgba(226, 232, 240, 0.8);
  padding-bottom: 6px;
}

.metric-item {
  font-size: 11px;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}

.metric-item strong {
  color: #1e293b;
}

.sandbox-suggestion {
  font-size: 11px;
  color: #475569;
  line-height: 1.45;
  text-align: left;
  background: rgba(255, 255, 255, 0.4);
  padding: 6px 8px;
  border-radius: 6px;
  word-break: break-all;
}

.status-alert .sandbox-suggestion {
  background: rgba(255, 255, 255, 0.7);
  color: #991b1b;
}

.status-safe .sandbox-suggestion {
  background: rgba(255, 255, 255, 0.7);
  color: #166534;
}

@keyframes pulse-danger-text {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.75; }
}

@keyframes border-glow-alert {
  0%, 100% {
    border-color: rgba(254, 226, 226, 0.7);
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
  }
  50% {
    border-color: rgba(248, 113, 113, 0.35);
    box-shadow: 0 2px 8px 0 rgba(239, 68, 68, 0.04);
  }
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

/* 锁定灰卡片样式 */
.sandbox-badge.status-locked {
  background: rgba(241, 245, 249, 0.6) !important;
  border: 1px dashed rgba(148, 163, 184, 0.6) !important;
  box-shadow: none !important;
}

.sandbox-badge.status-locked::before {
  background: linear-gradient(180deg, #94a3b8 0%, #64748b 100%);
}

.result-chip.locked-grey {
  background: #e2e8f0;
  color: #475569;
}

.status-locked .sandbox-suggestion {
  background: rgba(255, 255, 255, 0.8);
  color: #475569;
  border-left: 2px solid #94a3b8;
}

.status-locked .metric-item strong {
  color: #94a3b8;
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
</style>
