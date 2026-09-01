<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      
      <!-- 高级工作台头部 -->
      <header class="topbar premium-topbar">
        <div>
          <h2>现场管理工作台 (需求侧)</h2>
        </div>
        <div class="topbar-actions">
          <button
            type="button"
            class="btn pending-summary-topbar-btn"
            @click="openPendingSummaryModal('governance')"
            title="根据当前账号管辖的标段范围，查看各标段填报履约进度与在途发货督办"
          >
            <span class="btn-icon">📋</span>
            <span>全标段现场综合督办中心</span>
            <span v-if="governanceSummary.pending_sections_count > 0 || pendingSummaryTotalCount > 0" class="badge-count-pill">
              {{ governanceSummary.pending_sections_count > 0 ? `${governanceSummary.pending_sections_count} 标段待办` : `${pendingSummaryTotalCount} 笔发货` }}
            </span>
          </button>
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

      <!-- 一体化双层复合导航区 (Unified Compound Navigation Group) -->
      <div class="nav-composite-group" v-if="selectedSection1Id">
        <!-- 一级大类胶囊分段切换栏 (Segmented Category Bar) -->
        <div class="category-segment-wrapper">
          <div class="category-segment-bar">
            <button 
              type="button" 
              class="category-segment-btn" 
              :class="{ active: activeCategory === 'pipe' }" 
              @click="handleCategoryClick('pipe')"
            >
              <span class="cat-icon">🔹</span>
              <span class="cat-label">保温管业务</span>
            </button>
            <button 
              type="button" 
              class="category-segment-btn" 
              :class="{ active: activeCategory === 'fitting' }" 
              @click="handleCategoryClick('fitting')"
            >
              <span class="cat-icon">🔩</span>
              <span class="cat-label">管件业务</span>
            </button>
            <button 
              type="button" 
              class="category-segment-btn" 
              :class="{ active: activeCategory === 'tools' }" 
              @click="handleCategoryClick('tools')"
            >
              <span class="cat-icon">🛠️</span>
              <span class="cat-label">实用工具</span>
            </button>
          </div>
        </div>

        <!-- 二级选项卡导航 (Responsive Sub-Tabs Header) -->
        <div class="tube-tabs-header-wrap">
          <!-- 保温管子标签 -->
          <div class="tube-tabs-header" v-if="activeCategory === 'pipe'">
            <button 
              type="button" 
              :class="{ active: activeTab === 'overview' }" 
              @click="handleTabClick('overview')"
            >
              📈 需求与库存信息统计
            </button>
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
              🚚 到货确认与明细记录
            </button>
            <button 
              type="button" 
              :class="{ active: activeTab === 'fitting_usage' }" 
              @click="handleTabClick('fitting_usage')"
            >
              🔨 库存与管件使用量填报
            </button>
            <button 
              type="button" 
              :class="{ active: activeTab === 'fitting_baseline' }" 
              @click="handleTabClick('fitting_baseline')"
            >
              📋 设计量与采购量
            </button>
          </div>

          <!-- 实用工具子标签 -->
          <div class="tube-tabs-header" v-else-if="activeCategory === 'tools'">
            <button 
              type="button" 
              :class="{ active: activeTab === 'ocr_tool' }" 
              @click="handleTabClick('ocr_tool')"
            >
              📷 业务单据智能识别
            </button>
          </div>
        </div>
      </div>

      <!-- Tab内容区域 -->
      <div class="tube-tab-content-wrap" v-if="selectedSection1Id">
        
        <!-- Tab 0: 需求与库存信息统计 (图 + 表) -->
        <div v-if="activeTab === 'overview'" class="tab-pane">
          <section class="card elevated tab-card demand-overview-pane">
            <div class="panel-title-row" style="flex-wrap: wrap; gap: 12px;">
              <div>
                <h2>📈 保温管需求与库存信息统计</h2>
                <span class="panel-hint">
                  统计当前标段各型号保温管的“三日需求计划量、发货量、施工量、库存量、库存+在途、三日净缺口”，提供多维供需图表与精准缺口预警。
                </span>
              </div>
              <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                <button
                  type="button"
                  class="btn ghost compact-btn"
                  :disabled="overviewLoading"
                  @click="loadDemandInventoryOverview"
                  title="重新同步最新库存与缺口数据"
                >
                  🔄 刷新数据
                </button>
                <button
                  v-if="canExtractXlsx"
                  type="button"
                  class="btn primary compact-btn"
                  :disabled="overviewLoading || !overviewRows.length"
                  @click="exportOverviewToExcel"
                >
                  📥 导出统计报表
                </button>
              </div>
            </div>

            <!-- 1. 顶部 4 张关键态势概览指标卡片 (Quick KPI Cards) -->
            <div class="overview-kpi-grid">
              <div class="overview-kpi-card kpi-purple">
                <div class="kpi-card-header">
                  <span class="kpi-icon">🕒</span>
                  <span class="kpi-title">三日需求计划总量</span>
                </div>
                <div class="kpi-main-val">
                  <strong class="kpi-number">{{ formatNumber(overviewStats.totalPlan) }}</strong>
                  <span class="kpi-unit">米</span>
                </div>
                <div class="kpi-footer-note">覆盖 {{ overviewStats.planModelsCount }} 种需用规格型号</div>
              </div>

              <div class="overview-kpi-card kpi-green">
                <div class="kpi-card-header">
                  <span class="kpi-icon">📦</span>
                  <span class="kpi-title">现场可用实物库存</span>
                </div>
                <div class="kpi-main-val">
                  <strong class="kpi-number">{{ formatNumber(overviewStats.totalInventory) }}</strong>
                  <span class="kpi-unit">米</span>
                </div>
                <div class="kpi-footer-note">累计到货 {{ formatNumber(overviewStats.totalArrived) }}m · 消耗 {{ formatNumber(overviewStats.totalUsage) }}m</div>
              </div>

              <div class="overview-kpi-card kpi-blue">
                <div class="kpi-card-header">
                  <span class="kpi-icon">🚚</span>
                  <span class="kpi-title">运输在途保供总量</span>
                </div>
                <div class="kpi-main-val">
                  <strong class="kpi-number">{{ formatNumber(overviewStats.totalTransit) }}</strong>
                  <span class="kpi-unit">米</span>
                </div>
                <div class="kpi-footer-note">现存+在途合计 {{ formatNumber(overviewStats.totalInventoryPlusTransit) }} 米</div>
              </div>

              <div class="overview-kpi-card" :class="overviewStats.totalNetGap > 0 ? 'kpi-red is-alert-pulse' : 'kpi-safe'">
                <div class="kpi-card-header">
                  <span class="kpi-icon">{{ overviewStats.totalNetGap > 0 ? '🚨' : '🛡️' }}</span>
                  <span class="kpi-title">三日净缺口报警量</span>
                </div>
                <div class="kpi-main-val">
                  <strong class="kpi-number">{{ formatNumber(overviewStats.totalNetGap) }}</strong>
                  <span class="kpi-unit">米</span>
                </div>
                <div class="kpi-footer-note" :style="{ color: overviewStats.totalNetGap > 0 ? '#b91c1c' : '#15803d', fontWeight: '600' }">
                  {{ overviewStats.totalNetGap > 0 ? `⚠️ ${overviewStats.gapModelsCount} 个型号存在断料停工风险` : '✅ 各型号现存+在途均满足' }}
                </div>
              </div>
            </div>

            <!-- 2. 可视化图表区 (ECharts) -->
            <div class="overview-chart-box">
              <div class="overview-chart-header">
                <span class="chart-box-title">📊 各型号保温管供需对照图</span>
                <div class="chart-legend-hint">
                  <span class="dot purple"></span> 三日需求计划
                  <span class="dot green"></span> 现场库存
                  <span class="dot blue"></span> 运输在途
                  <span class="dot red"></span> 三日净缺口
                </div>
              </div>
              <div class="overview-chart-stage">
                <div v-if="overviewLoading" class="chart-loading-placeholder">
                  <div class="loading-spinner"></div>
                  <span>正在聚合各型号供需与库存数据...</span>
                </div>
                <div v-else-if="!overviewRows.length" class="chart-empty-placeholder">
                  当前需求主体暂无保温管型号数据
                </div>
                <div ref="overviewChartRef" class="overview-echarts-dom"></div>
              </div>
            </div>

            <!-- 3. 数据明细表格区 (带过滤与搜索) -->
            <div class="overview-table-section">
              <div class="overview-table-toolbar">
                <div class="toolbar-left">
                  <span class="toolbar-heading">📋 各型号供需全要素穿透台账</span>
                  <span class="toolbar-count-tag">共 {{ filteredOverviewRows.length }} 种型号规格</span>
                </div>
                <div class="toolbar-right">
                  <label class="gap-filter-checkbox" title="勾选后仅展示存在三日净缺口（断料风险）的型号">
                    <input type="checkbox" v-model="overviewOnlyShowGap" />
                    <span>⚠️ 仅看存在净缺口型号 ({{ overviewStats.gapModelsCount }})</span>
                  </label>
                  <input
                    v-model.trim="overviewSearchKeyword"
                    type="text"
                    class="overview-search-input"
                    placeholder="🔍 搜索管径型号规格..."
                  />
                </div>
              </div>

              <div v-if="overviewLoading" class="loading-text">正在加载各型号需求与库存统计...</div>
              <div v-else-if="overviewError" class="error-box">{{ overviewError }}</div>
              <div v-else-if="!filteredOverviewRows.length" class="empty-box">未找到符合筛选条件的型号记录。</div>
              <div v-else class="table-wrap custom-scroll-list" style="max-height: 480px; overflow-y: auto;">
                <table class="data-table overview-data-table">
                  <thead>
                    <tr>
                      <th style="width: 42px; text-align: center;">#</th>
                      <th style="min-width: 170px; text-align: left;">保温管规格型号</th>
                      <th style="min-width: 105px; text-align: right; color: #6d28d9;">三日需求计划(m)</th>
                      <th style="min-width: 95px; text-align: right;">累计发货(m)</th>
                      <th style="min-width: 95px; text-align: right;">累计施工(m)</th>
                      <th style="min-width: 105px; text-align: right; color: #047857; background: #f0fdf4;">现场库存(m)</th>
                      <th style="min-width: 100px; text-align: right; color: #0369a1; background: #f0f9ff;">运输在途(m)</th>
                      <th style="min-width: 110px; text-align: right; color: #0f766e;">库存+在途(m)</th>
                      <th style="min-width: 115px; text-align: right; color: #b91c1c; background: #fef2f2;">三日净缺口(m)</th>
                      <th style="min-width: 110px; text-align: center;">保供态势判定</th>
                      <th style="min-width: 120px; text-align: center;">快捷联动</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="(row, idx) in filteredOverviewRows" 
                      :key="row.pipeModelId"
                      :class="{ 'highlight-gap-row': row.netGapQty > 0 }"
                    >
                      <td style="text-align: center; color: #94a3b8;">{{ idx + 1 }}</td>
                      <td class="cell-text font-bold" :title="row.pipeModelName">
                        {{ row.pipeModelName }}
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #6d28d9;">
                        {{ formatQtyDisplay(row.futurePlanQty) }}
                      </td>
                      <td style="text-align: right; color: #334155;">
                        {{ formatQtyDisplay(row.totalShippedQty) }}
                      </td>
                      <td style="text-align: right; color: #334155;">
                        {{ formatQtyDisplay(row.totalUsageQty) }}
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #047857; background: #f0fdf4;">
                        {{ formatQtyDisplay(row.inventoryQty) }}
                      </td>
                      <td style="text-align: right; font-weight: 600; color: #0369a1; background: #f0f9ff;">
                        {{ formatQtyDisplay(row.pendingArrivalQty) }}
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #0f766e;">
                        {{ formatQtyDisplay(row.inventoryPlusPipeline) }}
                      </td>
                      <td 
                        style="text-align: right; font-weight: 700; background: #fef2f2;" 
                        :style="{ color: row.netGapQty > 0 ? '#b91c1c' : '#94a3b8' }"
                      >
                        <span v-if="row.netGapQty > 0" class="gap-warning-pill">
                          ⚠️ {{ formatQtyDisplay(row.netGapQty) }}
                        </span>
                        <span v-else>0.00</span>
                      </td>
                      <td style="text-align: center;">
                        <span :class="['status-pill', row.statusPillClass]">
                          {{ row.statusText }}
                        </span>
                      </td>
                      <td style="text-align: center;">
                        <div class="row-actions-group">
                          <button
                            type="button"
                            class="btn ghost btn-xs"
                            title="去该型号三日计划填报"
                            @click="handleTabClick('plan')"
                          >
                            🕒 计划
                          </button>
                          <button
                            type="button"
                            class="btn ghost btn-xs"
                            title="去该型号施工消耗填报"
                            @click="handleTabClick('usage')"
                          >
                            📊 消耗
                          </button>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                  <!-- 表尾合计行 -->
                  <tfoot>
                    <tr class="summary-total-row">
                      <td colspan="2" style="text-align: center; font-weight: 700; color: #1e293b;">
                        合计 ({{ filteredOverviewRows.length }} 种型号)
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #6d28d9;">
                        {{ formatQtyDisplay(filteredOverviewTotals.futurePlanQty) }}
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #334155;">
                        {{ formatQtyDisplay(filteredOverviewTotals.totalShippedQty) }}
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #334155;">
                        {{ formatQtyDisplay(filteredOverviewTotals.totalUsageQty) }}
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #047857; background: #e6f9ed;">
                        {{ formatQtyDisplay(filteredOverviewTotals.inventoryQty) }}
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #0369a1; background: #e0f2fe;">
                        {{ formatQtyDisplay(filteredOverviewTotals.pendingArrivalQty) }}
                      </td>
                      <td style="text-align: right; font-weight: 700; color: #0f766e;">
                        {{ formatQtyDisplay(filteredOverviewTotals.inventoryPlusPipeline) }}
                      </td>
                      <td 
                        style="text-align: right; font-weight: 700; background: #fee2e2;" 
                        :style="{ color: filteredOverviewTotals.netGapQty > 0 ? '#b91c1c' : '#15803d' }"
                      >
                        {{ formatQtyDisplay(filteredOverviewTotals.netGapQty) }}
                      </td>
                      <td colspan="2" style="text-align: center; font-size: 12px; color: #64748b;">
                        {{ filteredOverviewTotals.netGapQty > 0 ? `共 ${overviewStats.gapModelsCount} 种型号缺料` : '全型号供需平衡' }}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </section>
        </div>

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

            <!-- 下半区：保温管施工使用与损耗历史台账 -->
            <div style="margin-top: 28px; border-top: 2px dashed #e2e8f0; padding-top: 20px;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div>
                  <h3 style="margin: 0; font-size: 16px; color: #1e293b; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                    <span>📋 保温管施工使用与损耗历史台账</span>
                  </h3>
                  <span style="font-size: 12px; color: #64748b;">
                    支持按采集日期追溯该标段所有历史保温管实际施工消耗与现场损耗填报明细。
                  </span>
                </div>
                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                  <button
                    v-if="groupedPipeUsageHistory.length"
                    type="button"
                    class="btn ghost"
                    style="height: 30px; font-size: 12px; padding: 0 10px;"
                    @click="expandAllPipeUsageDates"
                  >
                    全部展开
                  </button>
                  <button
                    v-if="groupedPipeUsageHistory.length"
                    type="button"
                    class="btn ghost"
                    style="height: 30px; font-size: 12px; padding: 0 10px;"
                    @click="collapseAllPipeUsageDates"
                  >
                    全部折叠
                  </button>
                  <button
                    v-if="canExtractXlsx"
                    type="button"
                    class="btn secondary"
                    style="height: 30px; font-size: 12px; padding: 0 12px; display: inline-flex; align-items: center; gap: 4px;"
                    @click="exportPipeUsageHistory"
                  >
                    📊 导出使用台账
                  </button>
                  <button
                    type="button"
                    class="btn ghost"
                    style="height: 30px; font-size: 12px; padding: 0 10px;"
                    @click="loadPipeUsageHistory"
                  >
                    🔄 刷新台账
                  </button>
                </div>
              </div>

              <!-- 历史台账表格 -->
              <div v-if="pipeUsageHistoryLoading" class="loading-text" style="padding: 16px; text-align: center; color: #64748b;">
                正在加载保温管使用历史台账...
              </div>
              <div v-else-if="!groupedPipeUsageHistory.length" class="empty-box" style="padding: 20px; text-align: center; color: #94a3b8;">
                当前标段尚无保温管使用与损耗填报历史记录。
              </div>
              <div v-else class="table-wrap fitting-baseline-table-wrap" style="max-height: 520px;">
                <table class="data-table grouped-history-table" style="width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed;">
                  <thead>
                    <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                      <th style="width: 38px; padding: 6px 2px; text-align: center; white-space: nowrap;">序号</th>
                      <th style="width: 110px; text-align: left; padding: 6px 8px; white-space: nowrap;">消耗采集日期</th>
                      <th style="width: 90px; text-align: center; padding: 6px 4px; white-space: nowrap;">填报规模</th>
                      <th style="width: 95px; text-align: right; padding: 6px 8px; color: #2563eb; white-space: nowrap;">施工消耗(m)</th>
                      <th style="width: 85px; text-align: right; padding: 6px 8px; color: #ea580c; white-space: nowrap;">现场损耗(m)</th>
                      <th style="width: 95px; text-align: right; padding: 6px 8px; color: #047857; white-space: nowrap;">合计总米数</th>
                      <th style="width: 85px; text-align: center; padding: 6px 4px; white-space: nowrap;">填报人</th>
                      <th style="width: 100px; text-align: center; padding: 6px 4px; white-space: nowrap;">填报时间</th>
                      <th style="width: 70px; text-align: center; padding: 6px 2px; white-space: nowrap;">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <template v-for="(group, gIdx) in groupedPipeUsageHistory" :key="group.usage_date">
                      <!-- 📅 日期聚合主行 -->
                      <tr 
                        class="history-group-header-row"
                        :class="{ 'is-expanded': isPipeUsageDateExpanded(group.usage_date) }"
                        @click="togglePipeUsageDateExpand(group.usage_date)"
                      >
                        <td class="cell-text" style="width: 38px; padding: 6px 2px; text-align: center; color: #94a3b8; font-size: 11px;">
                          {{ gIdx + 1 }}
                        </td>
                        <td class="cell-text font-mono" style="padding: 6px 8px; font-weight: 700; color: #1e293b; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="`消耗采集日期: ${group.usage_date}`">
                          <span class="group-expand-caret">{{ isPipeUsageDateExpanded(group.usage_date) ? '▼' : '▶' }}</span>
                          <span>{{ group.usage_date }}</span>
                        </td>
                        <td class="cell-text" style="text-align: center; padding: 6px 4px; white-space: nowrap;">
                          <span class="pill-badge-subtle" style="font-size: 11px; padding: 1px 6px;">共 {{ group.total_types }} 种</span>
                        </td>
                        <td class="cell-text font-mono" style="text-align: right; padding: 6px 8px; font-weight: 700; color: #2563eb; white-space: nowrap;">
                          {{ formatNumber(group.total_usage_qty) }} m
                        </td>
                        <td class="cell-text font-mono" style="text-align: right; padding: 6px 8px; font-weight: 600; color: #ea580c; white-space: nowrap;">
                          {{ formatNumber(group.total_loss_qty) }} m
                        </td>
                        <td class="cell-text font-mono" style="text-align: right; padding: 6px 8px; font-weight: 700; color: #047857; white-space: nowrap;">
                          {{ formatNumber(group.total_sum_qty) }} m
                        </td>
                        <td class="cell-text" style="text-align: center; padding: 6px 4px; font-size: 11.5px; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="group.filled_by_str">
                          {{ group.filled_by_str }}
                        </td>
                        <td class="cell-text font-mono" style="text-align: center; padding: 6px 4px; font-size: 11px; color: #64748b; white-space: nowrap;">
                          {{ formatUsageTime(group.latest_filled_at) }}
                        </td>
                        <td class="cell-text" style="text-align: center; padding: 6px 2px; white-space: nowrap;">
                          <button 
                            type="button" 
                            class="btn-toggle-expand"
                            style="padding: 1px 6px; font-size: 10.5px;"
                            @click.stop="togglePipeUsageDateExpand(group.usage_date)"
                          >
                            {{ isPipeUsageDateExpanded(group.usage_date) ? '收起▴' : '明细▾' }}
                          </button>
                        </td>
                      </tr>

                      <!-- 展开的型号明细行 -->
                      <template v-if="isPipeUsageDateExpanded(group.usage_date)">
                        <tr
                          v-for="sub in group.items"
                          :key="sub.id || sub.pipe_model_id"
                          class="history-group-sub-row"
                          :style="(sub.usage_qty > 0 || sub.loss_qty > 0) ? 'background-color: #f0fdf4;' : ''"
                        >
                          <td style="text-align: center; color: #cbd5e1; font-size: 11px;">↳</td>
                          <td colspan="2" class="cell-text font-bold" style="padding-left: 20px; color: #334155;" :title="sub.pipe_model_name">
                            <span>{{ sub.pipe_model_name }}</span>
                            <span v-if="sub.usage_qty > 0 || sub.loss_qty > 0" class="pill-badge-subtle" style="margin-left: 6px; font-size: 10px; padding: 0 4px; background: #dcfce7; color: #15803d;">当日施工</span>
                          </td>
                          <td class="cell-text font-mono" style="text-align: right;" :style="sub.usage_qty > 0 ? 'color: #2563eb; font-weight: 700;' : 'color: #94a3b8;'">
                            {{ formatNumber(sub.usage_qty) }} m
                          </td>
                          <td class="cell-text font-mono" style="text-align: right;" :style="sub.loss_qty > 0 ? 'color: #ea580c; font-weight: 700;' : 'color: #94a3b8;'">
                            {{ formatNumber(sub.loss_qty) }} m
                          </td>
                          <td class="cell-text font-mono" style="text-align: right;" :style="sub.total_qty > 0 ? 'color: #047857; font-weight: 700;' : 'color: #94a3b8;'">
                            {{ formatNumber(sub.total_qty) }} m
                          </td>
                          <td class="cell-text" style="text-align: center; font-size: 11px; color: #64748b;" :title="sub.filled_by">
                            {{ sub.filled_by }}
                          </td>
                          <td colspan="2" class="cell-text" style="font-size: 11px; color: #64748b;" :title="sub.remark || '无备注'">
                            {{ sub.remark || '—' }}
                          </td>
                        </tr>
                      </template>
                    </template>
                  </tbody>
                </table>
              </div>
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
                <button 
                  type="button" 
                  class="btn ghost" 
                  style="color: #ea580c; border-color: #fdba74; font-weight: 600;" 
                  @click="openPendingSummaryModal"
                  title="查看管辖的所有标段中待到货与待接收的发货单汇总"
                >
                  🚚 全标段在途汇总 ({{ pendingSummaryTotalCount }})
                </button>
                <button type="button" class="btn ghost" :disabled="pendingLoading" @click="resetPendingFilters">重置筛选</button>
                <button type="button" class="primary-button" :disabled="pendingLoading || !selectedSection1Id" @click="applyPendingFilters">
                  {{ pendingLoading ? '查询中...' : '筛选记录' }}
                </button>
                <button v-if="canExtractXlsx && pendingRows.length > 0" type="button" class="btn primary" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: #fff !important; border: none !important; font-weight: 600;" @click="showExportModal = true">📥 导出 Excel</button>
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
                  style="height: 34px; padding: 0 12px; font-size: 12.5px; display: flex; align-items: center; gap: 4px; border-color: #fdba74; color: #ea580c; background: #fff; font-weight: 600; cursor: pointer;" 
                  @click="openPendingSummaryModal"
                  title="查看管辖的所有标段中待到货与待接收的发货单汇总"
                >
                  🚚 全标段在途汇总 ({{ pendingSummaryTotalCount }})
                </button>
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
                  v-if="canExtractXlsx"
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
                style="border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.03); transition: all 0.2s ease;"
              >
                <!-- 车次汇总卡片表头 (超紧凑清爽流式，0滚动条) -->
                <div 
                  class="fitting-card-header"
                  @click="toggleDemandFittingGroup(group.groupKey)"
                >
                  <!-- 左侧：箭头 + 车次 + 车牌 + 供给主体 + 发货时间 -->
                  <div class="card-left-stream">
                    <span 
                      class="expand-caret-icon" 
                      :style="{ transform: isDemandFittingGroupExpanded(group.groupKey) ? 'rotate(90deg)' : 'rotate(0deg)' }"
                    >▶</span>
                    <span class="shipment-code-badge">{{ group.shipmentNo }}</span>
                    <span class="plate-badge">{{ group.vehiclePlateNo }}</span>
                    <span class="entity-pill-badge" :title="`供给主体: ${group.supplyEntityName}`">
                      <span style="opacity: 0.8; font-size: 11px;">🏭</span>
                      <span class="entity-name-text">{{ group.supplyEntityName }}</span>
                    </span>
                    <span class="shipped-time-text">{{ formatShortDateTime(group.shippedAt) }}</span>
                  </div>

                  <!-- 右侧：发到数量微芯片 + 状态 Badge + 操作按钮组 -->
                  <div class="card-right-stream">
                    <!-- 发到数量微芯片 -->
                    <div class="qty-summary-chip">
                      <span class="qty-types-lbl">{{ group.items.length }} 种</span>
                      <span class="qty-divider">·</span>
                      <span class="qty-stat-item text-blue">发 <strong>{{ group.totalShippedQty }}</strong></span>
                      <span class="qty-divider">/</span>
                      <span class="qty-stat-item text-emerald">到 <strong>{{ group.totalArrivedQty }}</strong></span>
                      <span class="qty-unit-lbl">{{ getGroupUnitLabel(group) }}</span>
                    </div>

                    <!-- 履约状态 Badge -->
                    <div class="status-badge-container">
                      <span v-if="group.status === 'shipped' || group.status === 'pending_arrival' || !group.status" class="tag-badge primary" style="font-size: 11px; padding: 1px 6px; white-space: nowrap;">🚚 待到货确认</span>
                      <span v-else-if="group.status === 'arrived' || group.status === 'pending_receive'" class="tag-badge success" style="font-size: 11px; padding: 1px 6px; white-space: nowrap;">✅ 待施工接收</span>
                      <span v-else-if="group.status === 'construction_confirmed' || group.status === 'pending_warehouse' || group.status === 'received'" class="tag-badge warning" style="font-size: 11px; padding: 1px 6px; white-space: nowrap;">👷 待库管确认</span>
                      <span v-else-if="group.status === 'warehouse_confirmed' || group.status === 'completed'" class="tag-badge success" style="font-size: 11px; padding: 1px 6px; white-space: nowrap;">🏢 库管已确认</span>
                      <span v-else-if="group.status === 'cancelled'" class="tag-badge" style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; font-size: 11px; padding: 1px 6px; white-space: nowrap;">❌ 已撤销</span>
                      <span v-if="group.hasCancelled && group.status !== 'cancelled'" class="tag-badge" style="background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; font-size: 10.5px; padding: 1px 5px; margin-left: 2px; white-space: nowrap;">⚠️ 撤销</span>
                    </div>

                    <!-- 操作按钮组 -->
                    <div class="action-btn-container" @click.stop>
                      <button 
                        v-if="(group.status === 'shipped' || group.status === 'pending_arrival' || !group.status || group.items.some(i => i.status === 'shipped' || i.status === 'pending_arrival' || !i.status)) && canConfirmArrival"
                        type="button" 
                        class="btn primary btn-sm" 
                        style="height: 26px; padding: 0 8px; font-size: 11.5px; background: #059669; border-color: #059669; color: #fff; cursor: pointer; font-weight: 600; border-radius: 5px; white-space: nowrap; display: inline-flex; align-items: center; gap: 2px;"
                        @click.stop="openFittingArrivalModal(group)"
                      >
                        🚚 到货确认
                      </button>

                      <button 
                        v-else-if="(group.status === 'arrived' || group.status === 'pending_receive' || group.items.some(i => i.status === 'arrived' || i.status === 'pending_receive')) && canConfirmReceipt"
                        type="button" 
                        class="btn primary btn-sm" 
                        style="height: 26px; padding: 0 8px; font-size: 11.5px; background: #7c3aed; border-color: #7c3aed; color: #fff; cursor: pointer; font-weight: 600; border-radius: 5px; white-space: nowrap; display: inline-flex; align-items: center; gap: 2px;"
                        @click.stop="openFittingConstructionModal(group)"
                      >
                        👷 施工接收
                      </button>

                      <button 
                        type="button" 
                        class="btn ghost btn-sm" 
                        style="height: 26px; padding: 0 9px; font-size: 11.5px; color: #4f46e5; border: 1px solid #c7d2fe; background: #eef2ff; cursor: pointer; border-radius: 5px; white-space: nowrap; display: inline-flex; align-items: center; gap: 3px;"
                        @click.stop="showDeliveryDetail(group)"
                      >
                        📜 流转凭证
                      </button>
                    </div>
                  </div>
                </div>

                <!-- 明细展开区 (纯净货物清单展示，100% 自适应，无滚动条) -->
                <div v-show="isDemandFittingGroupExpanded(group.groupKey)" style="padding: 10px 14px 14px 14px; background: #ffffff;">
                  <div v-if="group.shipRemark" style="font-size: 11.5px; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; padding: 4px 10px; border-radius: 6px; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                    <span style="font-weight: 600;">📝 发货备注：</span>
                    <span style="color: #1e293b;">{{ group.shipRemark }}</span>
                  </div>

                  <div style="border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;">
                    <table class="data-table demand-fitting-table" style="margin: 0; width: 100%; font-size: 12px; border-collapse: collapse;">
                      <thead>
                        <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                          <th style="width: 42px; padding: 6px 2px; text-align: center; white-space: nowrap;">序号</th>
                          <th style="width: 90px; text-align: center; white-space: nowrap;">名称</th>
                          <th style="text-align: left; white-space: nowrap;">型号规格</th>
                          <th style="width: 140px; text-align: center; white-space: nowrap;">订单编号</th>
                          <th style="width: 75px; text-align: right; white-space: nowrap; color: #2563eb;">发货数量</th>
                          <th style="width: 75px; text-align: right; white-space: nowrap; color: #059669;">到货确认数</th>
                          <th style="width: 115px; text-align: center; white-space: nowrap;">履约状态</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr 
                          v-for="(item, idx) in group.items" 
                          :key="item.id" 
                          style="border-bottom: 1px solid #f1f5f9; height: 36px; vertical-align: middle;"
                        >
                          <td style="width: 32px; padding: 6px 2px; text-align: center; color: #94a3b8; font-size: 11px;">
                            {{ idx + 1 }}
                          </td>
                          <td style="text-align: center; white-space: nowrap;">
                            <span class="fitting-type-badge" style="font-size: 11px; padding: 1px 6px;">{{ item.fitting_type }}</span>
                          </td>
                          <td class="font-mono" style="font-weight: 600; color: #1e293b;">
                            {{ item.model_spec }}
                          </td>
                          <td class="font-mono" style="text-align: center; color: #64748b; font-size: 11px;">
                            {{ item.order_no || '-' }}
                          </td>
                          <td class="font-mono" style="text-align: right; font-weight: 700; color: #2563eb; white-space: nowrap;">
                            <span v-if="item.status === 'cancelled'" style="color: #94a3b8; text-decoration: line-through;">{{ item.shipped_qty }}</span>
                            <span v-else>{{ item.shipped_qty }} {{ item.unit || '件' }}</span>
                          </td>
                          <td class="font-mono" style="text-align: right; font-weight: 700; color: #059669; white-space: nowrap;">
                            <span v-if="isItemArrived(item)">{{ getItemArrivedQty(item) }} {{ item.unit || '件' }}</span>
                            <span v-else-if="item.status === 'cancelled'" style="color: #94a3b8; font-size: 11px; font-weight: normal;">-</span>
                            <span v-else style="color: #94a3b8; font-size: 11px; font-weight: normal;">待到货 (0)</span>
                          </td>
                          <td style="text-align: center; white-space: nowrap;">
                            <span v-if="item.status === 'shipped' || item.status === 'pending_arrival' || !item.status" class="tag-badge primary" style="background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-size: 10.5px; padding: 1px 6px;">🚚 待到货确认</span>
                            <span v-else-if="item.status === 'arrived' || item.status === 'pending_receive'" class="tag-badge success" style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 10.5px; padding: 1px 6px;">✅ 待施工接收</span>
                            <span v-else-if="item.status === 'construction_confirmed' || item.status === 'pending_warehouse' || item.status === 'received'" class="tag-badge warning" style="background: #f3e8ff; color: #6b21a8; border: 1px solid #d8b4fe; font-size: 10.5px; padding: 1px 6px;">👷 待库管确认</span>
                            <span v-else-if="item.status === 'warehouse_confirmed' || item.status === 'completed'" class="tag-badge success" style="background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; font-size: 10.5px; padding: 1px 6px;">🏢 库管已确认</span>
                            <span v-else-if="item.status === 'cancelled'" class="tag-badge" style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; font-size: 10.5px; padding: 1px 6px;">❌ 已撤销</span>
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
                  <strong style="color: #2563eb;">{{ demandFittingTotalQty }} 件</strong>
                </div>
                <div style="background: #fff; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                  <span>🟢 常用标准管件</span>
                  <strong style="color: #16a34a;">{{ demandFittingStandardQty }} 件</strong>
                </div>
                <div style="background: #fff; border: 1px solid #cbd5e1; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                  <span>🟧 非常用/异形管件</span>
                  <strong style="color: #ea580c;">{{ demandFittingNonStandardQty }} 件</strong>
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- Tab 7: 标段库存与管件使用量填报 -->
        <div v-if="activeTab === 'fitting_usage'" class="tab-pane">
          <section class="card elevated tab-card">
            <!-- 标题与操作栏 -->
            <div class="panel-title-row">
              <div>
                <h2>📦 {{ currentSection1Name }}库存与管件使用量填报</h2>
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
                <div class="section-select-group" style="background: #f8fafc; padding: 4px 12px; border-radius: 8px; border: 1px solid #cbd5e1; display: inline-flex; align-items: center; gap: 6px;">
                  <span class="section-select-label" style="font-size: 13px; color: #475569; font-weight: 500;">📅 消耗采集日期:</span>
                  <strong style="font-size: 13.5px; color: #1e293b; font-family: monospace;">{{ usageDate || '未设置' }}</strong>
                </div>
                <button
                  type="button"
                  class="btn ghost"
                  style="height: 34px; padding: 0 14px; font-size: 13px; display: inline-flex; align-items: center; gap: 4px; border-color: #cbd5e1; background: #fff; cursor: pointer; border-radius: 8px;"
                  @click="refreshFittingUsageData"
                >
                  🔄 刷新库存
                </button>
              </div>
            </div>

            <!-- 库存与消耗微看板 (Premium Metrics Grid) -->
            <div class="fitting-usage-summary-grid">
              <div class="summary-metric-card card-blue">
                <div class="metric-header-row">
                  <span class="metric-icon">📦</span>
                  <span class="metric-label">到货物料种类</span>
                </div>
                <div class="metric-body-row">
                  <strong class="metric-val text-blue">{{ fittingInventorySummary.total_types || 0 }}</strong>
                  <span class="metric-unit">种</span>
                </div>
              </div>

              <div class="summary-metric-card card-indigo">
                <div class="metric-header-row">
                  <span class="metric-icon">🚚</span>
                  <span class="metric-label">累计到货总数</span>
                </div>
                <div class="metric-body-row">
                  <strong class="metric-val text-indigo">{{ fittingInventorySummary.arrived_sum || 0 }}</strong>
                  <span class="metric-unit">件</span>
                </div>
              </div>

              <div class="summary-metric-card card-emerald">
                <div class="metric-header-row">
                  <span class="metric-icon">🔨</span>
                  <span class="metric-label">累计安装总数</span>
                </div>
                <div class="metric-body-row">
                  <strong class="metric-val text-emerald">{{ fittingInventorySummary.used_sum || 0 }}</strong>
                  <span class="metric-unit">件</span>
                </div>
              </div>

              <div class="summary-metric-card card-amber">
                <div class="metric-header-row">
                  <span class="metric-icon">🏷️</span>
                  <span class="metric-label">现场实时可用库存</span>
                </div>
                <div class="metric-body-row">
                  <strong class="metric-val text-amber">{{ fittingInventorySummary.stock_sum || 0 }}</strong>
                  <span class="metric-unit">件</span>
                </div>
              </div>

              <div class="summary-metric-card card-purple">
                <div class="metric-header-row">
                  <span class="metric-icon">📈</span>
                  <span class="metric-label">整体安装消耗率</span>
                </div>
                <div class="metric-body-row">
                  <strong class="metric-val text-purple">{{ fittingInventorySummary.overall_rate_pct || 0 }}%</strong>
                </div>
                <div class="micro-progress-bar">
                  <div class="micro-progress-fill" :style="{ width: `${Math.min(fittingInventorySummary.overall_rate_pct || 0, 100)}%` }"></div>
                </div>
              </div>
            </div>

            <!-- 加载与空数据提示 -->
            <div v-if="fittingInventoryLoading" class="loading-text" style="padding: 24px; text-align: center; color: #64748b;">
              ⏳ 正在计算当前标段现场实时库存...
            </div>
            <div v-else-if="fittingInventoryError" class="error-box">{{ fittingInventoryError }}</div>
            <div v-else-if="!filteredFittingInventoryItems.length" class="empty-box" style="padding: 30px; text-align: center; color: #94a3b8;">
              当前{{ modeLabels.section_1 }}暂无可用的到货管件记录。
            </div>

            <!-- 单日已提交锁定提示条 -->
            <div v-if="hasSubmittedFittingUsageToday" class="submitted-warning-banner" style="margin-top: 14px; padding: 12px 16px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; color: #92400e; font-size: 13px; display: flex; align-items: center; justify-content: space-between; gap: 8px; box-sizing: border-box; word-break: break-word; line-height: 1.5;">
              <span>⚠️ <strong>单日填报已锁定</strong>：当前标段在【{{ usageDate }}】已完成管件安装使用量填报（已记账）。单日仅允许提交一次，如需重新填报，请在下方【管件现场安装使用历史台账】中点击【撤回】后重新填报。</span>
            </div>

            <!-- 动态库存与可视化填报表 (电脑端表格 + 移动端卡片自适应) -->
            <div v-else class="fitting-usage-content-body" style="margin-top: 14px;">
              <!-- 🖥️ 电脑端高密度表格视图 (大屏幕显示，手机端隐藏) -->
              <div class="table-wrap fitting-baseline-table-wrap desktop-fitting-table-view" style="max-height: 580px;">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; white-space: nowrap;">序号</th>
                      <th style="min-width: 100px; text-align: center; white-space: nowrap;">名称</th>
                      <th style="min-width: 180px; white-space: nowrap;">到货型号规格</th>
                      <th style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; white-space: nowrap;">单位</th>
                      <th style="min-width: 140px; white-space: nowrap;">库存量</th>
                      <th style="min-width: 180px; white-space: nowrap;">本日使用量</th>
                      <th style="min-width: 140px; white-space: nowrap;">备注</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="(item, idx) in filteredFittingInventoryItems" 
                      :key="getItemKey(item)"
                      :class="{ 'row-has-input': (fittingUsageForm[getItemKey(item)]?.qty || 0) > 0 }"
                    >
                      <td class="cell-text" style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; color: #94a3b8; font-size: 11.5px;">
                        {{ idx + 1 }}
                      </td>
                      <td class="cell-text" style="text-align: center;">
                        <span class="fitting-type-badge">{{ item.fitting_type }}</span>
                      </td>
                      <td class="cell-text font-mono" style="font-weight: 600; color: #1e293b;">
                        {{ item.model_spec }}
                      </td>
                      <td class="cell-text" style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; color: #64748b; font-size: 12px;">
                        {{ item.unit }}
                      </td>
                      <td class="cell-text">
                        <div class="stock-progress-cell">
                          <div class="stock-stat-text">
                            <span>已用: <strong style="color: #059669;">{{ item.used_qty }}</strong></span>
                            <span>库存剩余: <strong :style="{ color: item.stock_qty > 0 ? '#2563eb' : '#dc2626' }">{{ item.stock_qty }}</strong> {{ item.unit }}</span>
                          </div>
                          <div class="stock-progress-bar-bg">
                            <div class="stock-progress-bar-used" :style="{ width: `${item.usage_rate_pct}%` }"></div>
                          </div>
                        </div>
                      </td>
                      <td class="cell-text">
                        <div v-if="item.stock_qty > 0" class="usage-input-control-group">
                          <div class="stepper-wrap">
                            <button 
                              type="button" 
                              class="step-btn" 
                              :disabled="hasSubmittedFittingUsageToday || (fittingUsageForm[getItemKey(item)]?.qty || 0) <= 0"
                              @click="adjustFittingUsageQty(item, -1)"
                            >-</button>
                            <input 
                              type="number" 
                              min="0" 
                              :max="item.stock_qty" 
                              v-model.number="getFormItem(item).qty" 
                              class="qty-input"
                              :disabled="hasSubmittedFittingUsageToday"
                              @blur="validateFittingUsageQty(item)"
                            />
                            <button 
                              type="button" 
                              class="step-btn" 
                              :disabled="hasSubmittedFittingUsageToday || (fittingUsageForm[getItemKey(item)]?.qty || 0) >= item.stock_qty"
                              @click="adjustFittingUsageQty(item, 1)"
                            >+</button>
                          </div>
                          <input 
                            type="range" 
                            min="0" 
                            :max="item.stock_qty" 
                            v-model.number="getFormItem(item).qty" 
                            class="usage-slider"
                            :disabled="hasSubmittedFittingUsageToday"
                          />
                          <button 
                            v-if="!hasSubmittedFittingUsageToday && (fittingUsageForm[getItemKey(item)]?.qty || 0) > 0"
                            type="button" 
                            class="quick-clear-btn"
                            @click="clearFittingUsageItem(item)"
                            title="清零"
                          >✕</button>
                        </div>
                        <div v-else style="color: #ef4444; font-size: 12px; font-weight: 500;">
                          ⚠️ 现场已无结存库存
                        </div>
                      </td>
                      <td class="cell-text">
                        <input 
                          type="text" 
                          v-model="getFormItem(item).remark"
                          placeholder="备注" 
                          class="text-input-compact"
                          :disabled="hasSubmittedFittingUsageToday || item.stock_qty <= 0"
                        />
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- 📱 手机端触控卡片流视图 (手机屏幕展示，电脑端隐藏) -->
              <div class="mobile-fitting-cards-view">
                <div 
                  v-for="(item, idx) in filteredFittingInventoryItems" 
                  :key="getItemKey(item)"
                  class="fitting-mobile-card"
                  :class="{ 
                    'card-has-input': (fittingUsageForm[getItemKey(item)]?.qty || 0) > 0,
                    'card-out-of-stock': item.stock_qty <= 0 
                  }"
                >
                  <!-- 顶部信息行：序号、类型、规格、单位与已填徽章 -->
                  <div class="fmc-header">
                    <div class="fmc-title-left">
                      <span class="fmc-idx">#{{ idx + 1 }}</span>
                      <span class="fitting-type-badge">{{ item.fitting_type }}</span>
                      <span class="fmc-spec font-mono">{{ item.model_spec }}</span>
                    </div>
                    <div class="fmc-header-right">
                      <span v-if="(fittingUsageForm[getItemKey(item)]?.qty || 0) > 0" class="fmc-filled-badge">
                        已填 {{ fittingUsageForm[getItemKey(item)]?.qty }} {{ item.unit }}
                      </span>
                      <span class="fmc-unit-chip">{{ item.unit }}</span>
                    </div>
                  </div>

                  <!-- 中部：现场库存与进度指示 -->
                  <div class="fmc-stock-panel">
                    <div class="fmc-stock-grid">
                      <div class="fmc-stock-box">
                        <span class="fmc-stock-lbl">累计已安装</span>
                        <div class="fmc-stock-val text-emerald">
                          <strong>{{ item.used_qty }}</strong> <span class="unit">{{ item.unit }}</span>
                        </div>
                      </div>
                      <div class="fmc-stock-box highlight-box" :class="item.stock_qty > 0 ? 'box-blue' : 'box-danger'">
                        <span class="fmc-stock-lbl">现场可用库存</span>
                        <div class="fmc-stock-val" :class="item.stock_qty > 0 ? 'text-blue' : 'text-danger'">
                          <strong>{{ item.stock_qty }}</strong> <span class="unit">{{ item.unit }}</span>
                        </div>
                      </div>
                    </div>
                    <div class="stock-progress-bar-bg" style="margin-top: 6px;">
                      <div class="stock-progress-bar-used" :style="{ width: `${item.usage_rate_pct}%` }"></div>
                    </div>
                  </div>

                  <!-- 下部：触控填报控件区 -->
                  <div class="fmc-action-panel">
                    <div v-if="item.stock_qty > 0" class="fmc-control-wrapper">
                      <!-- 填报量头部与一键填满/清零操作 -->
                      <div class="fmc-action-top-row">
                        <span class="fmc-action-heading">
                          本日使用量: 
                          <strong style="color: #2563eb; font-size: 15px;">{{ getFormItem(item).qty || 0 }}</strong> {{ item.unit }}
                        </span>
                        <div class="fmc-quick-btn-group">
                          <button 
                            type="button" 
                            class="fmc-btn-quick max"
                            :disabled="hasSubmittedFittingUsageToday"
                            @click="setFittingUsageMax(item)"
                          >
                            全部用完 ({{ item.stock_qty }})
                          </button>
                          <button 
                            v-if="!hasSubmittedFittingUsageToday && (fittingUsageForm[getItemKey(item)]?.qty || 0) > 0"
                            type="button" 
                            class="fmc-btn-quick clear"
                            @click="clearFittingUsageItem(item)"
                          >
                            清零
                          </button>
                        </div>
                      </div>

                      <!-- 大触控步进器 + 手指滑块 -->
                      <div class="fmc-stepper-control-row">
                        <div class="fmc-touch-stepper">
                          <button 
                            type="button" 
                            class="fmc-touch-btn minus" 
                            :disabled="hasSubmittedFittingUsageToday || (fittingUsageForm[getItemKey(item)]?.qty || 0) <= 0"
                            @click="adjustFittingUsageQty(item, -1)"
                          >−</button>
                          <input 
                            type="number" 
                            inputmode="numeric"
                            min="0" 
                            :max="item.stock_qty" 
                            v-model.number="getFormItem(item).qty" 
                            class="fmc-touch-input"
                            :disabled="hasSubmittedFittingUsageToday"
                            @blur="validateFittingUsageQty(item)"
                          />
                          <button 
                            type="button" 
                            class="fmc-touch-btn plus" 
                            :disabled="hasSubmittedFittingUsageToday || (fittingUsageForm[getItemKey(item)]?.qty || 0) >= item.stock_qty"
                            @click="adjustFittingUsageQty(item, 1)"
                          >+</button>
                        </div>
                        <div class="fmc-touch-slider-wrap">
                          <input 
                            type="range" 
                            min="0" 
                            :max="item.stock_qty" 
                            v-model.number="getFormItem(item).qty" 
                            class="fmc-touch-slider"
                            :disabled="hasSubmittedFittingUsageToday"
                          />
                        </div>
                      </div>

                      <!-- 选填备注 -->
                      <div class="fmc-remark-row">
                        <input 
                          type="text" 
                          v-model="getFormItem(item).remark"
                          placeholder="选填备注（如安装部位、班组等）" 
                          class="fmc-touch-remark"
                          :disabled="hasSubmittedFittingUsageToday"
                        />
                      </div>
                    </div>

                    <div v-else class="fmc-no-stock-tip">
                      <span>⚠️ 现场已无结存库存，无法登记安装量</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 底部提交条 -->
            <div class="usage-submit-action-bar" style="margin-top: 14px; padding: 12px 18px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
              <div class="usage-submit-info" style="font-size: 13.5px; color: #1e3a8a;">
                <span v-if="hasSubmittedFittingUsageToday" style="color: #92400e; font-weight: 600;">
                  🔒 当前标段在【{{ usageDate }}】已记账提交，单日仅限提交一次。
                </span>
                <template v-else>
                  <span>已选填报 <strong>{{ totalFilledItemsCount }}</strong> 种管件规格，</span>
                  <span>本次拟安装消耗合计：<strong style="color: #2563eb; font-size: 16px;">{{ totalFilledQtySum }}</strong> 件</span>
                  <span v-if="totalFilledQtySum > 0" style="margin-left: 8px; color: #059669; font-size: 12px;">(消耗采集日期: {{ usageDate }})</span>
                </template>
              </div>
              <div class="usage-submit-btns" :class="{ 'is-submitted-single': hasSubmittedFittingUsageToday }" style="display: flex; gap: 10px; align-items: center;">
                <button
                  v-if="!hasSubmittedFittingUsageToday"
                  type="button"
                  class="btn ghost"
                  style="height: 36px; padding: 0 14px; font-size: 13px;"
                  :disabled="hasSubmittedFittingUsageToday || totalFilledQtySum <= 0"
                  @click="resetFittingUsageForm"
                >
                  清空填写
                </button>
                <button
                  type="button"
                  class="btn primary"
                  :style="{ opacity: hasSubmittedFittingUsageToday ? 0.6 : 1, cursor: hasSubmittedFittingUsageToday ? 'not-allowed' : 'pointer' }"
                  style="height: 36px; padding: 0 18px; font-size: 14px; font-weight: 600; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; gap: 6px;"
                  :disabled="hasSubmittedFittingUsageToday || totalFilledQtySum <= 0 || fittingUsageSubmitting"
                  @click="handleFittingUsageSubmit"
                >
                  <span v-if="hasSubmittedFittingUsageToday">🔒 本日已提交</span>
                  <span v-else-if="fittingUsageSubmitting">正在提交入库...</span>
                  <span v-else>🚀 提交管件安装记录</span>
                </button>
              </div>
            </div>

            <!-- 下半区：管件安装使用历史台账 -->
            <div style="margin-top: 28px; border-top: 2px dashed #e2e8f0; padding-top: 20px;">
              <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div>
                  <h3 style="margin: 0; font-size: 16px; color: #1e293b; font-weight: 700; display: flex; align-items: center; gap: 6px;">
                    <span>📋 管件现场安装使用历史台账</span>
                  </h3>
                  <span style="font-size: 12px; color: #64748b;">支持查看与追溯所有历史安装流水；填报人 24 小时内或超级管理员可撤回误填记录并自动恢复现场库存。</span>
                </div>
                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                  <button
                    v-if="groupedFittingUsageHistory.length"
                    type="button"
                    class="btn ghost"
                    style="height: 30px; font-size: 12px; padding: 0 10px;"
                    @click="expandAllUsageDates"
                  >
                    全部展开
                  </button>
                  <button
                    v-if="groupedFittingUsageHistory.length"
                    type="button"
                    class="btn ghost"
                    style="height: 30px; font-size: 12px; padding: 0 10px;"
                    @click="collapseAllUsageDates"
                  >
                    全部折叠
                  </button>
                  <button
                    v-if="canExtractXlsx"
                    type="button"
                    class="btn secondary"
                    style="height: 30px; font-size: 12px; padding: 0 12px; display: inline-flex; align-items: center; gap: 4px;"
                    @click="exportFittingUsageHistory"
                  >
                    📊 导出使用台账
                  </button>
                  <button
                    type="button"
                    class="btn ghost"
                    style="height: 30px; font-size: 12px; padding: 0 10px;"
                    @click="loadFittingUsageHistory"
                  >
                    🔄 刷新台账
                  </button>
                </div>
              </div>

              <!-- 历史台账表格 -->
              <div v-if="fittingUsageHistoryLoading" class="loading-text" style="padding: 16px; text-align: center; color: #64748b;">
                正在加载安装流水台账...
              </div>
              <div v-else-if="!groupedFittingUsageHistory.length" class="empty-box" style="padding: 20px; text-align: center; color: #94a3b8;">
                当前标段尚无管件安装使用流水记录。
              </div>
              <div v-else class="table-wrap fitting-baseline-table-wrap" style="max-height: 520px;">
                <table class="data-table grouped-history-table" style="width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed;">
                  <thead>
                    <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                      <th style="width: 38px; padding: 6px 2px; text-align: center; white-space: nowrap;">序号</th>
                      <th style="width: 110px; text-align: left; padding: 6px 8px; white-space: nowrap;">消耗采集日期</th>
                      <th style="width: 90px; text-align: center; padding: 6px 4px; white-space: nowrap;">填报规模</th>
                      <th style="width: 85px; text-align: right; padding: 6px 8px; color: #2563eb; white-space: nowrap;">有效安装总量</th>
                      <th style="width: 75px; text-align: center; padding: 6px 4px; white-space: nowrap;">填报人</th>
                      <th style="width: 95px; text-align: center; padding: 6px 4px; white-space: nowrap;">填报时间</th>
                      <th style="width: 60px; text-align: center; padding: 6px 2px; white-space: nowrap;">状态</th>
                      <th style="width: 120px; text-align: center; padding: 6px 2px; white-space: nowrap;">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <template v-for="(group, gIdx) in groupedFittingUsageHistory" :key="group.usage_date">
                      <!-- 📅 日期聚合主行 -->
                      <tr 
                        class="history-group-header-row"
                        :class="{ 'is-expanded': isUsageDateExpanded(group.usage_date) }"
                        @click="toggleUsageDateExpand(group.usage_date)"
                      >
                        <td class="cell-text" style="width: 38px; padding: 6px 2px; text-align: center; color: #94a3b8; font-size: 11px;">
                          {{ gIdx + 1 }}
                        </td>
                        <td class="cell-text font-mono" style="padding: 6px 8px; font-weight: 700; color: #1e293b; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="`消耗采集日期: ${group.usage_date}`">
                          <span class="group-expand-caret">{{ isUsageDateExpanded(group.usage_date) ? '▼' : '▶' }}</span>
                          <span>{{ group.usage_date }}</span>
                        </td>
                        <td class="cell-text" style="text-align: center; padding: 6px 4px; white-space: nowrap;">
                          <span class="pill-badge-subtle" style="font-size: 11px; padding: 1px 6px;">共 {{ group.total_types }} 种</span>
                        </td>
                        <td class="cell-text font-mono" style="text-align: right; padding: 6px 8px; font-weight: 700; color: #2563eb; white-space: nowrap;">
                          {{ group.total_active_qty }} 件
                        </td>
                        <td class="cell-text" style="text-align: center; padding: 6px 4px; font-size: 11.5px; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" :title="group.filled_by_str">
                          {{ group.filled_by_str }}
                        </td>
                        <td class="cell-text font-mono" style="text-align: center; padding: 6px 4px; font-size: 11px; color: #64748b; white-space: nowrap;">
                          {{ formatUsageTime(group.latest_filled_at) }}
                        </td>
                        <td class="cell-text" style="text-align: center; padding: 6px 2px; white-space: nowrap;">
                          <span v-if="!group.has_cancelled" style="font-size: 10.5px; padding: 1px 5px; border-radius: 4px; background: #ecfdf5; color: #059669; font-weight: 600;">已记账</span>
                          <span v-else-if="group.has_active && group.has_cancelled" style="font-size: 10.5px; padding: 1px 5px; border-radius: 4px; background: #fff7ed; color: #ea580c; font-weight: 600;">含作废</span>
                          <span v-else style="font-size: 10.5px; padding: 1px 5px; border-radius: 4px; background: #fef2f2; color: #ef4444; font-weight: 600;">全作废</span>
                        </td>
                        <td class="cell-text" style="text-align: center; padding: 6px 2px; white-space: nowrap;">
                          <div style="display: inline-flex; align-items: center; justify-content: center; gap: 3px;">
                            <button
                              v-if="isGlobalAdmin"
                              type="button"
                              class="btn-toggle-expand"
                              style="padding: 1px 5px; font-size: 10.5px; color: #4f46e5; border-color: #c7d2fe; background: #eef2ff;"
                              @click.stop="openEditUsageBatchModal(group)"
                              title="管理员批量编辑整日安装批次 (支持修改日期、填报人与各项物料)"
                            >
                              ✏️ 编辑
                            </button>
                            <button
                              v-if="isGlobalAdmin && group.has_active"
                              type="button"
                              class="btn-cancel-usage"
                              style="padding: 1px 5px; font-size: 10.5px; color: #b91c1c; border-color: #fecaca; background: #fef2f2;"
                              @click.stop="openCancelUsageGroupModal(group)"
                              title="管理员作废当日整批记录 (退回库存并解锁填报)"
                            >
                              ↩️ 作废
                            </button>
                            <button 
                              type="button" 
                              class="btn-toggle-expand"
                              style="padding: 1px 5px; font-size: 10.5px;"
                              @click.stop="toggleUsageDateExpand(group.usage_date)"
                            >
                              {{ isUsageDateExpanded(group.usage_date) ? '收起▴' : '明细▾' }}
                            </button>
                          </div>
                        </td>
                      </tr>

                      <!-- 🔍 日期明细展开子表格 -->
                      <tr v-if="isUsageDateExpanded(group.usage_date)" class="history-detail-container-row">
                        <td colspan="8" style="padding: 0; background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
                          <div style="padding: 8px 12px 12px 16px;">
                            <div style="font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between;">
                              <span>📋 【消耗采集日期: {{ group.usage_date }}】安装物料明细 (共 {{ group.items.length }} 笔)</span>
                              <span v-if="isGlobalAdmin" style="font-size: 11px; color: #2563eb; font-weight: 500;">⚡ 管理员可对单项或整批进行编辑微调与作废</span>
                              <span v-else style="font-size: 11px; color: #64748b;">台账已归档记账，如需修正请联系系统管理员</span>
                            </div>
                            <table class="detail-nested-table" style="width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; font-size: 12px; table-layout: fixed;">
                              <thead>
                                <tr style="background: #f1f5f9; color: #475569;">
                                  <th style="width: 36px; padding: 6px 2px; text-align: center; white-space: nowrap;">序号</th>
                                  <th style="width: 70px; text-align: center; padding: 6px 4px; white-space: nowrap;">名称</th>
                                  <th style="text-align: left; padding: 6px 8px; white-space: nowrap;">型号规格</th>
                                  <th style="width: 70px; text-align: right; padding: 6px 8px; color: #2563eb; white-space: nowrap;">安装量</th>
                                  <th style="width: 36px; padding: 6px 2px; text-align: center; white-space: nowrap;">单位</th>
                                  <th style="width: 120px; text-align: left; padding: 6px 8px; white-space: nowrap;">备注</th>
                                  <th style="width: 60px; text-align: center; padding: 6px 2px; white-space: nowrap;">状态</th>
                                  <th style="width: 95px; text-align: center; padding: 6px 4px; white-space: nowrap;">填报人/时间</th>
                                  <th style="width: 80px; text-align: center; padding: 6px 2px; white-space: nowrap;">操作</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr 
                                  v-for="(row, rIdx) in group.items" 
                                  :key="row.id || rIdx"
                                  :style="{ opacity: row.status === 'cancelled' ? 0.55 : 1, background: row.status === 'cancelled' ? '#fff5f5' : '#ffffff' }"
                                  style="border-bottom: 1px solid #f1f5f9;"
                                >
                                  <td style="width: 36px; padding: 6px 2px; text-align: center; color: #94a3b8; font-size: 11px;">
                                    {{ rIdx + 1 }}
                                  </td>
                                  <td style="text-align: center; padding: 6px 4px; white-space: nowrap;">
                                    <span class="fitting-type-badge" style="font-size: 10.5px; padding: 1px 5px;">{{ row.fitting_type }}</span>
                                  </td>
                                  <td class="font-mono" style="font-weight: 600; color: #1e293b; padding: 6px 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="row.model_spec">
                                    {{ row.model_spec }}
                                  </td>
                                  <td class="font-mono" style="text-align: right; font-weight: 700; color: #2563eb; padding: 6px 8px; white-space: nowrap;">
                                    {{ row.usage_qty }}
                                  </td>
                                  <td style="width: 36px; padding: 6px 2px; text-align: center; color: #64748b; white-space: nowrap;">
                                    {{ row.unit || '件' }}
                                  </td>
                                  <td style="padding: 6px 8px; color: #475569; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="row.remark || ''">
                                    {{ row.remark || '-' }}
                                  </td>
                                  <td style="text-align: center; padding: 6px 2px; white-space: nowrap;">
                                    <span v-if="row.status === 'active'" style="font-size: 10px; padding: 1px 4px; border-radius: 3px; background: #ecfdf5; color: #059669; font-weight: 600;">已记账</span>
                                    <span v-else style="font-size: 10px; padding: 1px 4px; border-radius: 3px; background: #fef2f2; color: #ef4444; font-weight: 600;" :title="`作废原因: ${row.cancel_reason}`">已作废</span>
                                  </td>
                                  <td style="text-align: center; font-size: 11px; color: #64748b; padding: 6px 4px; white-space: nowrap;">
                                    <div>{{ row.filled_by }}</div>
                                    <div style="font-size: 10px; color: #94a3b8; font-family: monospace;">{{ formatUsageTime(row.filled_at) }}</div>
                                  </td>
                                  <td style="text-align: center; padding: 6px 2px; white-space: nowrap;">
                                    <div v-if="isGlobalAdmin" style="display: inline-flex; align-items: center; justify-content: center; gap: 3px;">
                                      <button
                                        type="button"
                                        class="btn-toggle-expand"
                                        style="padding: 1px 4px; font-size: 10px; color: #2563eb; border-color: #bfdbfe; background: #eff6ff;"
                                        @click="openEditUsageItemModal(row)"
                                        title="管理员编辑此笔安装记录"
                                      >
                                        ✏️
                                      </button>
                                      <button
                                        v-if="row.status === 'active'"
                                        type="button"
                                        class="btn-cancel-usage"
                                        style="padding: 1px 4px; font-size: 10px;"
                                        @click="openCancelUsageModal(row)"
                                        title="管理员作废当笔记录"
                                      >
                                        ↩️
                                      </button>
                                    </div>
                                    <span v-else style="font-size: 11px; color: #94a3b8;">-</span>
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    </template>
                  </tbody>
                </table>
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
                  v-if="canExtractXlsx"
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
            <!-- 限制20行数据高度并带固定表头与垂直滚动条 -->
            <div v-else class="table-wrap fitting-baseline-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; white-space: nowrap;">序号</th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'system_type' }" style="min-width: 95px; text-align: center; white-space: nowrap;" @click="handleFittingSort('system_type')">
                      系统类型
                      <span class="sort-icon">{{ fittingSortState.key === 'system_type' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'category' }" style="min-width: 105px; white-space: nowrap;" @click="handleFittingSort('category')">
                      物理类别
                      <span class="sort-icon">{{ fittingSortState.key === 'category' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'standard_name' }" style="min-width: 160px; white-space: nowrap;" @click="handleFittingSort('standard_name')">
                      标准名称
                      <span class="sort-icon">{{ fittingSortState.key === 'standard_name' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'model_spec' }" style="min-width: 170px; white-space: nowrap;" @click="handleFittingSort('model_spec')">
                      型号规格
                      <span class="sort-icon">{{ fittingSortState.key === 'model_spec' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'sub_model_spec' }" style="min-width: 110px; white-space: nowrap;" @click="handleFittingSort('sub_model_spec')">
                      细分规格
                      <span class="sort-icon">{{ fittingSortState.key === 'sub_model_spec' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'main_dn' }" style="min-width: 90px; text-align: right; white-space: nowrap;" @click="handleFittingSort('main_dn')">
                      主径DN
                      <span class="sort-icon">{{ fittingSortState.key === 'main_dn' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'sub_dn' }" style="min-width: 90px; text-align: right; white-space: nowrap;" @click="handleFittingSort('sub_dn')">
                      次径DN
                      <span class="sort-icon">{{ fittingSortState.key === 'sub_dn' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'angle' }" style="min-width: 85px; text-align: right; white-space: nowrap;" @click="handleFittingSort('angle')">
                      角度(°)
                      <span class="sort-icon">{{ fittingSortState.key === 'angle' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'bending_radius_ratio' }" style="min-width: 95px; text-align: right; white-space: nowrap;" @click="handleFittingSort('bending_radius_ratio')">
                      弯曲倍数
                      <span class="sort-icon">{{ fittingSortState.key === 'bending_radius_ratio' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th style="min-width: 130px; white-space: nowrap;">阀门/公称压力</th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'raw_model_spec' }" style="min-width: 140px; white-space: nowrap;" @click="handleFittingSort('raw_model_spec')">
                      原型号规格
                      <span class="sort-icon">{{ fittingSortState.key === 'raw_model_spec' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'raw_name' }" style="min-width: 140px; white-space: nowrap;" @click="handleFittingSort('raw_name')">
                      原名称
                      <span class="sort-icon">{{ fittingSortState.key === 'raw_name' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th style="width: 50px; min-width: 50px; max-width: 50px; padding: 8px 4px; text-align: center; white-space: nowrap;">单位</th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'design_qty' }" style="min-width: 125px; text-align: right; color: #1d4ed8; white-space: nowrap;" @click="handleFittingSort('design_qty')">
                      设计使用量
                      <span class="sort-icon">{{ fittingSortState.key === 'design_qty' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th class="sortable-th" :class="{ sorted: fittingSortState.key === 'purchase_plan_qty' }" style="min-width: 135px; text-align: right; color: #059669; white-space: nowrap;" @click="handleFittingSort('purchase_plan_qty')">
                      计划采购总量
                      <span class="sort-icon">{{ fittingSortState.key === 'purchase_plan_qty' ? (fittingSortState.order === 'asc' ? '▲' : '▼') : '⇅' }}</span>
                    </th>
                    <th style="min-width: 140px; white-space: nowrap;">说明备注</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in sortedFittingBaselineRows" :key="row.id || idx">
                    <td class="cell-text" style="width: 36px; min-width: 36px; max-width: 36px; padding: 6px 2px; text-align: center; color: #94a3b8; font-size: 11.5px;">{{ idx + 1 }}</td>
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
                    <td class="cell-text" style="width: 50px; min-width: 50px; max-width: 50px; padding: 6px 4px; text-align: center;">{{ row.unit || '个' }}</td>
                    <td class="cell-number" style="font-weight: 700; color: #1d4ed8;">{{ formatNumber(row.design_qty) }}</td>
                    <td class="cell-number" style="font-weight: 700; color: #059669;">{{ formatNumber(row.purchase_plan_qty) }}</td>
                    <td class="cell-text" :title="row.remark">{{ row.remark || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <!-- Tab 8: 实用工具 - 业务单据智能识别 -->
        <div v-if="activeTab === 'ocr_tool'" class="tab-pane">
          <section class="card elevated tab-card">
            <DeliveryBillOcrTool
              :project-key="PROJECT_KEY"
              :selected-section1-id="selectedSection1Id"
              :section1-options="section1Options"
              :is-global-admin="isGlobalAdmin"
              @navigate-tab="handleTabClick"
            />
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
                <tr v-for="(it, idx) in deliveryDetailModalData.itemsList" :key="it.id || idx" style="border-bottom: 1px solid #f1f5f9;" :style="it.status === 'cancelled' ? { background: '#fef2f2', opacity: '0.8' } : {}">
                  <td style="padding: 6px 4px; text-align: center; color: #94a3b8;">{{ idx + 1 }}</td>
                  <td style="padding: 6px 6px; font-weight: 600; color: #0f172a; word-break: break-word;">
                    {{ isFittingDeliveryModal ? (it.fitting_type || it.fittingType || '管件') : '保温管' }}
                    <span v-if="it.status === 'cancelled'" class="tag-badge" style="background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; font-size: 10px; margin-left: 4px;">已撤销</span>
                  </td>
                  <td style="padding: 6px 6px; color: #334155; font-family: monospace; word-break: break-word;">{{ isFittingDeliveryModal ? (it.model_spec || it.modelSpec || '—') : (it.pipe_model_id || it.pipeModelName || deliveryDetailModalData.pipeModelName || '未填') }}</td>
                  <td style="padding: 6px 6px; text-align: right; font-weight: bold;" :style="{ color: it.status === 'cancelled' ? '#94a3b8' : '#2563eb', textDecoration: it.status === 'cancelled' ? 'line-through' : 'none', whiteSpace: 'nowrap' }">{{ formatNumber(it.shipped_qty || it.shippedQty) }} {{ it.unit || (isFittingDeliveryModal ? '个' : '米') }}</td>
                  <td style="padding: 6px 6px; text-align: right; font-weight: bold; white-space: nowrap;">
                    <span v-if="it.status === 'cancelled'" style="color: #ef4444; font-size: 11px;">已撤销</span>
                    <span v-else-if="Boolean(deliveryDetailModalData.arrivedConfirmAt || (it.status && it.status !== 'shipped' && it.status !== 'pending_arrival') || (deliveryDetailModalData.status && deliveryDetailModalData.status !== 'shipped' && deliveryDetailModalData.status !== 'pending_arrival'))" style="color: #059669;">
                      {{ formatNumber(it.arrived_qty !== undefined && it.arrived_qty !== null ? it.arrived_qty : (it.arrivedQty !== undefined && it.arrivedQty !== null ? it.arrivedQty : 0)) }} {{ it.unit || (isFittingDeliveryModal ? '个' : '米') }}
                    </span>
                    <span v-else style="color: #94a3b8; font-weight: normal;">—</span>
                  </td>
                  <td style="padding: 6px 6px; color: #64748b; font-style: italic; word-break: break-word;">
                    {{ it.cancel_reason ? `[撤销原因: ${it.cancel_reason}]` : (it.ship_remark || it.shipRemark || it.arrival_remark || '—') }}
                  </td>
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
                  <div>操作账号：<span class="user-matrix-link" @click="handleGoToUserDirectory(deliveryDetailModalData.createdBy)" title="点击在责任主体矩阵中定位">{{ deliveryDetailModalData.createdBy || '供给端系统' }}</span></div>
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
                  <div>操作账号：<span class="user-matrix-link" @click="handleGoToUserDirectory(deliveryDetailModalData.arrivedConfirmBy)" title="点击在责任主体矩阵中定位">{{ deliveryDetailModalData.arrivedConfirmBy || '—' }}</span></div>
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
                  <div>操作账号：<span class="user-matrix-link" @click="handleGoToUserDirectory(deliveryDetailModalData.receivedConfirmBy)" title="点击在责任主体矩阵中定位">{{ deliveryDetailModalData.receivedConfirmBy || '—' }}</span></div>
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
                  <div>审批人：<strong class="user-matrix-link" @click="handleGoToUserDirectory(deliveryDetailModalData.diffApproveBy)" title="点击在责任主体矩阵中定位">{{ deliveryDetailModalData.diffApproveBy }}</strong></div>
                  <div>审批时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.diffApproveAt) }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.diffApproveRemark">审批意见：<span style="color: #ea580c; font-weight: 500;">{{ deliveryDetailModalData.diffApproveRemark }}</span></div>
                </div>
              </div>
            </div>

            <!-- 5. 库管确认阶段 -->
            <div style="position: relative;">
              <span :style="{
                position: 'absolute', left: '-24px', top: '2px', width: '12px', height: '12px', borderRadius: '99px',
                background: deliveryDetailModalData.warehouseConfirmAt ? '#059669' : '#cbd5e1',
                border: '2px solid #fff',
                boxShadow: '0 0 0 2px ' + (deliveryDetailModalData.warehouseConfirmAt ? '#059669' : '#cbd5e1')
              }"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span :style="{ fontSize: '13px', fontWeight: 'bold', color: deliveryDetailModalData.warehouseConfirmAt ? '#1e293b' : '#94a3b8' }">🏢 库管已确认</span>
                  <span v-if="deliveryDetailModalData.warehouseConfirmAt" style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.warehouseConfirmAt) }}</span>
                  <span v-else style="font-size: 11px; color: #94a3b8; font-style: italic;">等待库管确认...</span>
                </div>
                <div v-if="deliveryDetailModalData.warehouseConfirmAt" style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>确认时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.warehouseConfirmAt) }}</span></div>
                  <div>操作账号：<strong class="user-matrix-link" @click="handleGoToUserDirectory(deliveryDetailModalData.warehouseConfirmBy)" title="点击在责任主体矩阵中定位">{{ deliveryDetailModalData.warehouseConfirmBy || '—' }}</strong></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.warehouseConfirmName || '—' }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.warehouseConfirmPhone">联系电话：<span>{{ deliveryDetailModalData.warehouseConfirmPhone }}</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.warehouseRemark">确认备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.warehouseRemark }}”</span></div>
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
                  <div>修正人：<strong class="user-matrix-link" @click="handleGoToUserDirectory(deliveryDetailModalData.updatedBy)" title="点击在责任主体矩阵中定位">{{ deliveryDetailModalData.updatedBy || '超级管理员' }}</strong></div>
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

            <!-- 7. 撤销/异常废弃阶段 (当单据状态为 cancelled 或存在撤销记录时展示) -->
            <div v-if="deliveryDetailModalData.status === 'cancelled' || deliveryDetailModalData.cancelledAt || deliveryDetailModalData.cancelAt || deliveryDetailModalData.cancelReason || deliveryDetailModalData.cancel_reason" style="position: relative; margin-top: 20px;">
              <span style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; background: #ef4444; border: 2px solid #fff; box-shadow: 0 0 0 2px #ef4444; display: inline-block;"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold; color: #b91c1c;">🚫 供给侧撤销发货</span>
                  <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.cancelledAt || deliveryDetailModalData.cancelAt || deliveryDetailModalData.updatedAt) }}</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #fef2f2; padding: 6px 10px; border-radius: 6px; border: 1px solid #fecaca; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>撤销操作人：<strong class="user-matrix-link" style="color: #b91c1c;" @click="handleGoToUserDirectory(deliveryDetailModalData.cancelBy || deliveryDetailModalData.cancel_by)" title="点击在责任主体矩阵中定位">{{ deliveryDetailModalData.cancelBy || deliveryDetailModalData.cancel_by || '供给端操作员' }}</strong></div>
                  <div>撤销时间：<span>{{ formatDateTimeDisplay(deliveryDetailModalData.cancelledAt || deliveryDetailModalData.cancelAt || deliveryDetailModalData.updatedAt) }}</span></div>
                  <div style="grid-column: span 2; word-break: break-all;">撤销原因：
                    <strong style="color: #b91c1c; font-weight: 600;">{{ deliveryDetailModalData.cancelReason || deliveryDetailModalData.cancel_reason || '供给侧主动撤销发货' }}</strong>
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
              💡 提示：由施工现场接收人员确认管件到场领用接收。确认后将进入“待库管确认”流转阶段。
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

    <!-- ↩️ 管件使用量记录撤回作废 Modal -->
    <Transition name="fade">
      <div v-if="showFittingUsageCancelModal" class="block-modal-overlay" @click.self="showFittingUsageCancelModal = false">
        <div class="block-modal-container" style="max-width: 500px;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%) !important;">
            <span class="block-warning-icon">↩️</span>
            <h3 style="margin-top: 5px; color: #fff;">{{ selectedCancelUsageGroup ? '撤回整日管件安装使用记录' : '撤回管件安装使用记录' }}</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">
              <span v-if="selectedCancelUsageGroup">
                消耗采集日期：<strong>{{ selectedCancelUsageGroup.usage_date }}</strong> (共 {{ selectedCancelUsageGroup.items.filter(i => i.status === 'active').length }} 笔有效物料，合计 {{ selectedCancelUsageGroup.total_active_qty }} 件)
              </span>
              <span v-else>
                管件：{{ selectedCancelUsageRow?.fitting_type }} {{ selectedCancelUsageRow?.model_spec }} ({{ selectedCancelUsageRow?.usage_qty }} {{ selectedCancelUsageRow?.unit || '件' }})
              </span>
            </p>
          </div>

          <div style="padding: 16px 20px; font-size: 13px; color: #334155;">
            <div style="margin-bottom: 12px; background: #fff5f5; border: 1px solid #fed7d7; padding: 10px 12px; border-radius: 6px; color: #c53030; font-size: 12px;">
              <span v-if="selectedCancelUsageGroup">
                ⚠️ 撤回作废后，该日所有有效安装物料（共 <strong>{{ selectedCancelUsageGroup.total_active_qty }} 件</strong>）将立即全额退回当前标段的现场可用库存，<strong>单日填报通道将自动重新解锁</strong>！
              </span>
              <span v-else>
                ⚠️ 撤回作废后，该笔安装使用的 <strong>{{ selectedCancelUsageRow?.usage_qty }} {{ selectedCancelUsageRow?.unit || '件' }}</strong> 将立即退回至当前标段的现场可用库存！
              </span>
            </div>

            <div style="margin-bottom: 14px;">
              <label style="display: block; font-weight: 600; margin-bottom: 6px; color: #1e293b;">
                请填写撤回/作废原因 <span style="color: #ef4444;">*</span>:
              </label>
              <textarea
                v-model="cancelUsageReason"
                rows="3"
                placeholder="例如：现场桩号或数量录入有误，需重新核实填报..."
                style="width: 100%; padding: 8px 10px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; outline: none;"
              ></textarea>
            </div>
          </div>

          <div class="block-modal-actions" style="margin-top: 5px; display: flex; gap: 10px;">
            <button
              type="button"
              class="btn ghost"
              style="flex: 1;"
              @click="showFittingUsageCancelModal = false"
            >
              取消
            </button>
            <button
              type="button"
              class="btn primary"
              style="flex: 1; background: #ef4444 !important; border-color: #ef4444 !important; color: #fff !important; font-weight: 600;"
              :disabled="!cancelUsageReason.trim() || cancelUsageSubmitting"
              @click="handleConfirmCancelUsage"
            >
              {{ cancelUsageSubmitting ? '正在撤回...' : '确认撤回并恢复库存' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ✏️ 管理员编辑单项安装记录 Modal -->
    <Transition name="fade">
      <div v-if="showFittingUsageItemEditModal" class="block-modal-overlay" @click.self="showFittingUsageItemEditModal = false">
        <div class="block-modal-container" style="max-width: 520px;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;">
            <span class="block-warning-icon">✏️</span>
            <h3 style="margin-top: 5px; color: #fff;">管理员编辑安装记录</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">
              物料：{{ selectedEditUsageItem?.fitting_type }} {{ selectedEditUsageItem?.model_spec }} ({{ selectedEditUsageItem?.unit || '件' }})
            </p>
          </div>

          <div style="padding: 16px 20px; font-size: 13px; color: #334155;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
              <div>
                <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">消耗采集日期 <span style="color: #ef4444;">*</span></label>
                <input v-model="editItemForm.usage_date" type="date" style="width: 100%; padding: 6px 8px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box;" />
              </div>
              <div>
                <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">填报人</label>
                <input v-model="editItemForm.filled_by" type="text" style="width: 100%; padding: 6px 8px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box;" />
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
              <div>
                <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">安装数量 ({{ selectedEditUsageItem?.unit || '件' }}) <span style="color: #ef4444;">*</span></label>
                <input v-model.number="editItemForm.usage_qty" type="number" min="1" style="width: 100%; padding: 6px 8px; font-size: 13px; font-weight: 700; color: #2563eb; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box;" />
              </div>
              <div>
                <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">记录状态</label>
                <select v-model="editItemForm.status" style="width: 100%; padding: 6px 8px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box;">
                  <option value="active">🟢 已记账 (生效并占用库存)</option>
                  <option value="cancelled">🔴 已作废 (退回可用库存)</option>
                </select>
              </div>
            </div>

            <div style="margin-bottom: 12px;">
              <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">施工备注</label>
              <input v-model="editItemForm.remark" type="text" placeholder="填写施工部位、核验说明等备注信息" style="width: 100%; padding: 6px 8px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box;" />
            </div>

            <div v-if="editItemForm.status === 'cancelled'" style="margin-bottom: 12px; background: #fff5f5; border: 1px solid #fed7d7; padding: 10px; border-radius: 6px;">
              <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #c53030;">作废原因说明 <span style="color: #ef4444;">*</span></label>
              <input v-model="editItemForm.cancel_reason" type="text" placeholder="必填：请输入作废原因说明" style="width: 100%; padding: 6px 8px; font-size: 13px; border: 1px solid #feb2b2; border-radius: 6px; box-sizing: border-box;" />
            </div>
          </div>

          <div class="block-modal-actions" style="margin-top: 5px; display: flex; gap: 10px;">
            <button type="button" class="btn ghost" style="flex: 1;" @click="showFittingUsageItemEditModal = false">取消</button>
            <button type="button" class="btn primary" style="flex: 1; background: #2563eb !important; border-color: #2563eb !important; color: #fff !important; font-weight: 600;" :disabled="editItemSubmitting || (editItemForm.status === 'active' && editItemForm.usage_qty <= 0) || (editItemForm.status === 'cancelled' && !editItemForm.cancel_reason.trim())" @click="handleConfirmUpdateUsageItem">
              {{ editItemSubmitting ? '保存中...' : '💾 保存修改' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 📋 管理员批量编辑整日安装批次 Modal -->
    <Transition name="fade">
      <div v-if="showFittingUsageBatchEditModal" class="block-modal-overlay" @click.self="showFittingUsageBatchEditModal = false">
        <div class="block-modal-container" style="max-width: 650px;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;">
            <span class="block-warning-icon">📋</span>
            <h3 style="margin-top: 5px; color: #fff;">管理员批量编辑整日安装批次</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">
              当前标段在【{{ selectedEditUsageGroup?.usage_date }}】的管件安装批次 (共 {{ editBatchForm.items.length }} 笔物料)
            </p>
          </div>

          <div style="padding: 16px 20px; font-size: 13px; color: #334155; max-height: 60vh; overflow-y: auto;">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; background: #f8fafc; padding: 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <div>
                <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">整批迁移至新消耗采集日期</label>
                <input v-model="editBatchForm.new_usage_date" type="date" style="width: 100%; padding: 6px 8px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box;" />
              </div>
              <div>
                <label style="display: block; font-weight: 600; margin-bottom: 4px; color: #1e293b;">批量更新填报人</label>
                <input v-model="editBatchForm.filled_by" type="text" placeholder="留空则保持各项原填报人" style="width: 100%; padding: 6px 8px; font-size: 13px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box;" />
              </div>
            </div>

            <div style="font-weight: 600; margin-bottom: 8px; color: #0f172a;">📦 当日各物料使用量微调：</div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;">
              <thead>
                <tr style="background: #f1f5f9; color: #475569;">
                  <th style="padding: 6px 4px; text-align: center; width: 65px;">类型</th>
                  <th style="padding: 6px 6px; text-align: left;">型号规格</th>
                  <th style="padding: 6px 6px; text-align: right; width: 85px;">安装数量</th>
                  <th style="padding: 6px 6px; text-align: left; width: 150px;">施工备注</th>
                  <th style="padding: 6px 4px; text-align: center; width: 75px;">状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="it in editBatchForm.items" :key="it.id" style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 6px 4px; text-align: center;">
                    <span class="fitting-type-badge" style="font-size: 10.5px;">{{ it.fitting_type }}</span>
                  </td>
                  <td class="font-mono" style="padding: 6px 6px; font-weight: 600; font-size: 11.5px;">
                    {{ it.model_spec }}
                  </td>
                  <td style="padding: 6px 6px; text-align: right;">
                    <input v-model.number="it.usage_qty" type="number" min="0" style="width: 65px; padding: 3px 4px; font-size: 12px; font-weight: 700; color: #2563eb; text-align: right; border: 1px solid #cbd5e1; border-radius: 4px;" />
                  </td>
                  <td style="padding: 6px 6px;">
                    <input v-model="it.remark" type="text" placeholder="施工部位/说明等备注" style="width: 100%; padding: 4px 6px; font-size: 11.5px; border: 1px solid #cbd5e1; border-radius: 4px; box-sizing: border-box;" />
                  </td>
                  <td style="padding: 6px 4px; text-align: center;">
                    <select v-model="it.status" style="padding: 2px 4px; font-size: 11px; border: 1px solid #cbd5e1; border-radius: 4px;">
                      <option value="active">🟢 生效</option>
                      <option value="cancelled">🔴 作废</option>
                    </select>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="block-modal-actions" style="margin-top: 5px; display: flex; gap: 10px;">
            <button type="button" class="btn ghost" style="flex: 1;" @click="showFittingUsageBatchEditModal = false">取消</button>
            <button type="button" class="btn primary" style="flex: 1; background: #4f46e5 !important; border-color: #4f46e5 !important; color: #fff !important; font-weight: 600;" :disabled="editBatchSubmitting" @click="handleConfirmUpdateUsageBatch">
              {{ editBatchSubmitting ? '正在批量保存...' : '💾 批量保存并重算库存' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 🚚 全标段现场综合督办中心 Modal (双Tab: 标段填报履约督办 + 在途发货单据督办) -->
    <Transition name="fade">
      <div v-if="pendingSummaryModalVisible" class="block-modal-overlay pending-super-overlay" @click.self="pendingSummaryModalVisible = false">
        <div class="block-modal-container pending-clean-modal-container">
          <!-- 1. 清爽单行 Header -->
          <div class="pending-clean-header">
            <div class="header-left-info">
              <span class="header-icon">{{ supervisionActiveTab === 'governance' ? '📋' : '🚚' }}</span>
              <h3 class="header-title">{{ supervisionActiveTab === 'governance' ? '全标段现场综合督办中心' : '全标段发货督办清单' }}</h3>
              <span class="header-count-pill">
                {{ supervisionActiveTab === 'governance' ? `${governanceSummary.pending_sections_count || 0} 标段待催办` : `${pendingSummaryTotalCount} 笔待办` }}
              </span>
            </div>
            
            <div class="header-right-tools">
              <button
                type="button"
                class="btn-clean-ghost"
                :disabled="supervisionActiveTab === 'governance' ? governanceLoading : pendingSummaryLoading"
                @click="supervisionActiveTab === 'governance' ? loadGovernanceOverview(true) : loadPendingDeliveriesSummary(true)"
                title="重新拉取最新数据"
              >
                <span class="btn-ic" :class="{ 'spin-anim': governanceLoading || pendingSummaryLoading }">🔄</span>
                <span>刷新</span>
              </button>
              <button
                v-if="canExtractXlsx"
                type="button"
                class="btn-clean-export"
                :disabled="supervisionActiveTab === 'governance' ? (governanceLoading || !filteredGovernanceSections.length) : (pendingSummaryLoading || !sortedPendingSummaryRows.length)"
                @click="supervisionActiveTab === 'governance' ? exportGovernanceExcel() : exportPendingSummaryExcel()"
                :title="supervisionActiveTab === 'governance' ? '导出当前筛选的标段填报履约 Excel 督办清单' : '导出当前筛选的发货单 Excel 督办清单'"
              >
                <span class="btn-ic">📥</span>
                <span>导出 EXCEL 表</span>
              </button>
              <button type="button" class="btn-clean-close" @click="pendingSummaryModalVisible = false" title="关闭弹窗 (Esc)">
                ✕
              </button>
            </div>
          </div>

          <!-- 2. 专属双 Tab 切换导航条 (单行通透，绝不挤压顶栏) -->
          <div class="pending-modal-nav-bar">
            <button
              type="button"
              class="modal-nav-item"
              :class="{ active: supervisionActiveTab === 'governance' }"
              @click="supervisionActiveTab = 'governance'"
            >
              <span class="nav-ic">📋</span>
              <span class="nav-txt">各标段填报履约督办</span>
              <span v-if="governanceSummary.pending_sections_count > 0" class="nav-badge warning">
                {{ governanceSummary.pending_sections_count }} 标段待办
              </span>
              <span v-else class="nav-badge success">✓ 全部完成</span>
            </button>
            <button
              type="button"
              class="modal-nav-item"
              :class="{ active: supervisionActiveTab === 'logistics' }"
              @click="supervisionActiveTab = 'logistics'"
            >
              <span class="nav-ic">🚚</span>
              <span class="nav-txt">全标段发货单据督办</span>
              <span v-if="pendingSummaryTotalCount > 0" class="nav-badge info">
                {{ pendingSummaryTotalCount }} 笔在途
              </span>
              <span v-else class="nav-badge gray">0 笔在途</span>
            </button>
          </div>

          <!-- ==================== 标签页 1: 📋 各标段填报履约督办 ==================== -->
          <div v-if="supervisionActiveTab === 'governance'" class="supervision-tab-content">
            <!-- 4 大 KPI 汇总横栏 -->
            <div class="gov-kpi-bar">
              <div class="gov-kpi-card">
                <div class="gov-kpi-ic">🏛️</div>
                <div class="gov-kpi-info">
                  <span class="gov-kpi-lbl">管辖标段总数</span>
                  <div class="gov-kpi-val">
                    <strong>{{ governanceSummary.total_sections || 0 }}</strong>
                    <span class="unit">个标段</span>
                  </div>
                  <span class="gov-kpi-sub">已全部闭环 {{ governanceSummary.all_completed_count || 0 }} 个</span>
                </div>
              </div>

              <div class="gov-kpi-card">
                <div class="gov-kpi-ic">📅</div>
                <div class="gov-kpi-info">
                  <span class="gov-kpi-lbl">三日计划报送进度</span>
                  <div class="gov-kpi-val text-blue">
                    <strong>{{ governanceSummary.plan_submitted_count || 0 }}</strong>
                    <span class="unit">/ {{ governanceSummary.total_sections || 0 }} 标段</span>
                  </div>
                  <span class="gov-kpi-sub">计划起始日: {{ governanceDates.plan_start_date || '—' }}</span>
                </div>
              </div>

              <div class="gov-kpi-card">
                <div class="gov-kpi-ic">📏</div>
                <div class="gov-kpi-info">
                  <span class="gov-kpi-lbl">直管消耗填报进度</span>
                  <div class="gov-kpi-val text-emerald">
                    <strong>{{ governanceSummary.pipe_usage_submitted_count || 0 }}</strong>
                    <span class="unit">/ {{ governanceSummary.total_sections || 0 }} 标段</span>
                  </div>
                  <span class="gov-kpi-sub">消耗采集日: {{ governanceDates.usage_collection_date || '—' }}</span>
                </div>
              </div>

              <div class="gov-kpi-card">
                <div class="gov-kpi-ic">🔩</div>
                <div class="gov-kpi-info">
                  <span class="gov-kpi-lbl">管件用量填报进度</span>
                  <div class="gov-kpi-val text-purple">
                    <strong>{{ governanceSummary.fitting_usage_submitted_count || 0 }}</strong>
                    <span class="unit">/ {{ governanceSummary.total_sections || 0 }} 标段</span>
                  </div>
                  <span class="gov-kpi-sub">消耗采集日: {{ governanceDates.usage_collection_date || '—' }}</span>
                </div>
              </div>
            </div>

            <!-- 标段督办过滤工具栏 -->
            <div class="pending-clean-toolbar">
              <div class="capsule-group">
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: governanceFilter.status === 'all' }"
                  @click="governanceFilter.status = 'all'"
                >
                  全部标段 ({{ governanceSections.length }})
                </button>
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: governanceFilter.status === 'pending' }"
                  @click="governanceFilter.status = 'pending'"
                >
                  🔴 待催办标段 ({{ governanceSummary.pending_sections_count || 0 }})
                </button>
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: governanceFilter.status === 'completed' }"
                  @click="governanceFilter.status = 'completed'"
                >
                  🟢 全部完成 ({{ governanceSummary.all_completed_count || 0 }})
                </button>
              </div>

              <!-- 搜索框 -->
              <div class="clean-search-wrap" style="flex: 1; max-width: 380px;">
                <span class="search-ic">🔍</span>
                <input
                  v-model.trim="governanceFilter.searchKeyword"
                  type="text"
                  placeholder="搜索标段名称 / 供暖辖区..."
                  class="clean-search-input"
                />
                <button
                  v-if="governanceFilter.searchKeyword"
                  type="button"
                  class="clean-search-clear"
                  @click="governanceFilter.searchKeyword = ''"
                  title="清空搜索"
                >
                  ✕
                </button>
              </div>
            </div>

            <!-- 标段填报履约主体内容 -->
            <div class="pending-clean-body">
              <div v-if="governanceLoading" class="clean-empty-state">
                <div class="clean-spinner"></div>
                <p>正在读取各标段每日填报履约与上次提交时间...</p>
              </div>

              <div v-else-if="governanceError" class="clean-error-state">
                <span>⚠️ {{ governanceError }}</span>
                <button type="button" class="btn-clean-ghost small" @click="loadGovernanceOverview(true)">重试</button>
              </div>

              <div v-else-if="!filteredGovernanceSections.length" class="clean-empty-state">
                <span class="empty-emoji">🎉</span>
                <h4>太好了！当前筛选条件下没有需要催办的标段</h4>
                <p>管辖标段内各项计划与施工消耗均已正常完成填报。</p>
              </div>

              <div v-else class="pending-content-wrapper">
                <!-- PC 端大横表 (清爽无折行) -->
                <div class="clean-table-scroll-wrap pc-only-table">
                  <table class="clean-wide-table">
                    <thead>
                      <tr>
                        <th style="width: 50px; text-align: center;">#</th>
                        <th style="min-width: 170px; width: 190px;">需求标段</th>
                        <th style="min-width: 220px;">📅 三日需求计划</th>
                        <th style="min-width: 230px;">📏 直管施工消耗</th>
                        <th style="min-width: 200px;">🔩 管件施工使用</th>
                        <th style="min-width: 200px;">🚚 待办在途发货</th>
                        <th style="width: 150px; text-align: center;">现场督办操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(sec, idx) in filteredGovernanceSections"
                        :key="sec.section_1_id"
                        class="clean-table-tr"
                        :class="{
                          'tr-severe': sec.overall_status === 'severe_pending',
                          'tr-warning': sec.overall_status === 'partially_pending'
                        }"
                      >
                        <!-- 序号 -->
                        <td style="text-align: center; color: #94a3b8; font-size: 12.5px;" class="font-mono">
                          {{ idx + 1 }}
                        </td>

                        <!-- 需求标段 -->
                        <td>
                          <div class="sec-name-box">
                            <span class="sec-name-txt">📍 {{ sec.section_1_name }}</span>
                            <span class="sec-region-badge">{{ sec.region }}</span>
                          </div>
                        </td>

                        <!-- 1. 三日需求计划 -->
                        <td>
                          <div class="gov-cell-block">
                            <div class="gov-pill-line">
                              <span v-if="sec.plan.is_submitted" class="gov-status-pill success">✓ 今日已报送</span>
                              <span v-else class="gov-status-pill warning">⌛ 今日未报送</span>
                            </div>
                            <div class="gov-meta-line">
                              <template v-if="sec.plan.is_submitted">
                                <span class="gov-meta-label">报送量:</span>
                                <strong class="gov-meta-val text-blue font-mono">{{ sec.plan.total_qty }} 米</strong>
                                <span v-if="sec.plan.submitted_at" class="gov-time-sub">{{ sec.plan.submitted_at.slice(11) }}</span>
                              </template>
                              <template v-else>
                                <span v-if="sec.plan.last_submitted_date" class="gov-history-txt">
                                  上次报送: <strong class="font-mono text-amber">{{ sec.plan.last_submitted_date }}</strong>
                                </span>
                                <span v-else class="gov-history-none">从未报送</span>
                              </template>
                            </div>
                          </div>
                        </td>

                        <!-- 2. 直管施工消耗 -->
                        <td>
                          <div class="gov-cell-block">
                            <div class="gov-pill-line">
                              <span v-if="sec.pipe_usage.is_submitted" class="gov-status-pill success">✓ 今日已填报</span>
                              <span v-else class="gov-status-pill warning">⌛ 今日未填报</span>
                            </div>
                            <div class="gov-meta-line">
                              <template v-if="sec.pipe_usage.is_submitted">
                                <span class="gov-meta-label">消耗:</span>
                                <strong class="gov-meta-val text-emerald font-mono">{{ sec.pipe_usage.total_usage_qty }} 米</strong>
                                <span v-if="sec.pipe_usage.total_loss_qty > 0" class="gov-loss-sub font-mono">(损耗 {{ sec.pipe_usage.total_loss_qty }}米)</span>
                              </template>
                              <template v-else>
                                <span v-if="sec.pipe_usage.last_submitted_date" class="gov-history-txt">
                                  上次填报: <strong class="font-mono text-amber">{{ sec.pipe_usage.last_submitted_date }}</strong>
                                </span>
                                <span v-else class="gov-history-none">从未填报</span>
                              </template>
                            </div>
                          </div>
                        </td>

                        <!-- 3. 管件施工使用 -->
                        <td>
                          <div class="gov-cell-block">
                            <div class="gov-pill-line">
                              <span v-if="sec.fitting_usage.is_submitted" class="gov-status-pill success">✓ 今日已填报</span>
                              <span v-else class="gov-status-pill warning">⌛ 今日未填报</span>
                            </div>
                            <div class="gov-meta-line">
                              <template v-if="sec.fitting_usage.is_submitted">
                                <span class="gov-meta-label">使用量:</span>
                                <strong class="gov-meta-val text-purple font-mono">{{ sec.fitting_usage.total_qty }} 件</strong>
                              </template>
                              <template v-else>
                                <span v-if="sec.fitting_usage.last_submitted_date" class="gov-history-txt">
                                  上次填报: <strong class="font-mono text-amber">{{ sec.fitting_usage.last_submitted_date }}</strong>
                                </span>
                                <span v-else class="gov-history-none">从未填报</span>
                              </template>
                            </div>
                          </div>
                        </td>

                        <!-- 4. 待办在途发货 -->
                        <td>
                          <div class="gov-cell-block">
                            <div class="gov-pill-line">
                              <span v-if="sec.deliveries.total === 0" class="gov-status-pill gray">✓ 无在途发货</span>
                              <span v-else class="gov-status-pill info" :class="{ severe: sec.deliveries.severe_delay > 0 }">
                                🚚 在途 {{ sec.deliveries.total }} 笔
                              </span>
                            </div>
                            <div class="gov-meta-line">
                              <template v-if="sec.deliveries.total > 0">
                                <span class="gov-del-breakdown">
                                  待到货 {{ sec.deliveries.pending_arrival }} / 待接收 {{ sec.deliveries.pending_receive }}
                                </span>
                                <span v-if="sec.deliveries.severe_delay > 0" class="gov-severe-pill">
                                  🔴 滞留 {{ sec.deliveries.severe_delay }} 笔
                                </span>
                              </template>
                              <template v-else>
                                <span class="gov-history-none">所有物资已闭环</span>
                              </template>
                            </div>
                          </div>
                        </td>

                        <!-- 现场督办操作 -->
                        <td style="text-align: center;">
                          <button
                            type="button"
                            class="btn-gov-action"
                            @click="handleSelectSectionFromGovernance(sec.section_1_id)"
                            title="一键切换主工作台至该标段"
                          >
                            🚀 切到该标段 ➔
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 手机端小卡片 -->
                <div class="mobile-only-cards-grid">
                  <div
                    v-for="sec in filteredGovernanceSections"
                    :key="sec.section_1_id"
                    class="mobile-ticket-card"
                    :class="{
                      'card-severe': sec.overall_status === 'severe_pending',
                      'card-warning': sec.overall_status === 'partially_pending'
                    }"
                  >
                    <div class="m-card-header">
                      <div class="m-tags-row">
                        <span class="clean-section-tag">📍 {{ sec.section_1_name }}</span>
                        <span class="sec-region-badge mini">{{ sec.region }}</span>
                      </div>
                    </div>

                    <div class="m-card-body">
                      <div class="m-grid-kv">
                        <div class="m-kv-item">
                          <span class="m-k">三日计划:</span>
                          <span v-if="sec.plan.is_submitted" class="m-v font-bold text-blue">✓ 已报 ({{ sec.plan.total_qty }}米)</span>
                          <span v-else class="m-v text-amber font-bold">⌛ 未报 ({{ sec.plan.last_submitted_date ? `上次:${sec.plan.last_submitted_date}` : '从未报送' }})</span>
                        </div>
                        <div class="m-kv-item">
                          <span class="m-k">直管消耗:</span>
                          <span v-if="sec.pipe_usage.is_submitted" class="m-v font-bold text-emerald">✓ 已填 ({{ sec.pipe_usage.total_usage_qty }}米)</span>
                          <span v-else class="m-v text-amber font-bold">⌛ 未填 ({{ sec.pipe_usage.last_submitted_date ? `上次:${sec.pipe_usage.last_submitted_date}` : '从未填报' }})</span>
                        </div>
                        <div class="m-kv-item">
                          <span class="m-k">管件使用:</span>
                          <span v-if="sec.fitting_usage.is_submitted" class="m-v font-bold text-purple">✓ 已填 ({{ sec.fitting_usage.total_qty }}件)</span>
                          <span v-else class="m-v text-amber font-bold">⌛ 未填 ({{ sec.fitting_usage.last_submitted_date ? `上次:${sec.fitting_usage.last_submitted_date}` : '从未填报' }})</span>
                        </div>
                        <div class="m-kv-item">
                          <span class="m-k">在途发货:</span>
                          <span v-if="sec.deliveries.total === 0" class="m-v text-muted">✓ 无在途</span>
                          <span v-else class="m-v font-bold" :class="{ 'text-red': sec.deliveries.severe_delay > 0 }">在途 {{ sec.deliveries.total }} 笔</span>
                        </div>
                      </div>
                    </div>

                    <div class="m-card-footer">
                      <button
                        type="button"
                        class="m-btn-jump full-w"
                        @click="handleSelectSectionFromGovernance(sec.section_1_id)"
                      >
                        🚀 切换至该标段工作台 ➔
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ==================== 标签页 2: 🚚 全标段发货单据督办 (100% 原始精美排版) ==================== -->
          <div v-else class="supervision-tab-content">
            <!-- 2. 清爽通透的筛选栏 (单行流，按钮文字绝对不串行) -->
            <div class="pending-clean-toolbar">
              <!-- 品类胶囊切换 -->
              <div class="capsule-group">
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: pendingSummaryFilter.category === 'all' }"
                  @click="setPendingSummaryCategory('all')"
                >
                  全部品类
                </button>
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: pendingSummaryFilter.category === 'pipe' }"
                  @click="setPendingSummaryCategory('pipe')"
                >
                  🔥 直管 ({{ pendingSummaryStats.pipe_count || 0 }})
                </button>
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: pendingSummaryFilter.category === 'fitting' }"
                  @click="setPendingSummaryCategory('fitting')"
                >
                  🔩 管件 ({{ pendingSummaryStats.fitting_count || 0 }})
                </button>
              </div>

              <!-- 待办状态切换 -->
              <div class="capsule-group status-capsules">
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: pendingSummaryFilter.status === '' }"
                  @click="setPendingSummaryStatusFilter('')"
                >
                  全部状态
                </button>
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: pendingSummaryFilter.status === 'pending_arrival' }"
                  @click="setPendingSummaryStatusFilter('pending_arrival')"
                >
                  🚚 待到货确认 ({{ pendingSummaryStats.pending_arrival_count || 0 }})
                </button>
                <button
                  type="button"
                  class="capsule-item"
                  :class="{ active: pendingSummaryFilter.status === 'pending_receive' }"
                  @click="setPendingSummaryStatusFilter('pending_receive')"
                >
                  🏗️ 待施工接收 ({{ pendingSummaryStats.pending_receive_count || 0 }})
                </button>
              </div>

              <!-- 标段筛选下拉 -->
              <select v-model="pendingSummaryFilter.section1Id" class="clean-select" @change="loadPendingDeliveriesSummary(true)">
                <option value="">全部管辖标段 ({{ pendingSummaryAccessibleSections.length }}个)</option>
                <option v-for="sec in pendingSummaryAccessibleSections" :key="sec.section_1_id" :value="sec.section_1_id">
                  📍 {{ sec.section_1_name }}
                </option>
              </select>

              <!-- 🚛 按车次合并开关 (默认合并，可手动切换) -->
              <button
                type="button"
                class="btn-group-toggle"
                :class="{ 'is-active': groupByShipment }"
                @click="groupByShipment = !groupByShipment"
                :title="groupByShipment ? '当前：按车次号合并记录（点击切换为按单据逐笔明细）' : '当前：按单据逐笔明细展示（点击切换为按车次号合并）'"
              >
                <span class="toggle-ic">{{ groupByShipment ? '🚛' : '📄' }}</span>
                <span class="toggle-txt">{{ groupByShipment ? '按车次合并' : '单据明细' }}</span>
                <span class="toggle-indicator" :class="{ active: groupByShipment }"></span>
              </button>

              <!-- 搜索框 -->
              <div class="clean-search-wrap">
                <span class="search-ic">🔍</span>
                <input
                  v-model.trim="pendingSummaryFilter.searchKeyword"
                  type="text"
                  placeholder="搜索单号/车牌/厂家/规格..."
                  class="clean-search-input"
                  @input="loadPendingDeliveriesSummary(false)"
                />
                <button
                  v-if="pendingSummaryFilter.searchKeyword"
                  type="button"
                  class="clean-search-clear"
                  @click="clearPendingSummarySearch"
                  title="清空搜索"
                >
                  ✕
                </button>
              </div>
            </div>

            <!-- 3. 主体内容区：PC 端大横表 + 手机端小卡片 -->
            <div class="pending-clean-body">
              <!-- 加载状态 -->
              <div v-if="pendingSummaryLoading" class="clean-empty-state">
                <div class="clean-spinner"></div>
                <p>正在读取全标段在途单据与在途时长...</p>
              </div>

              <!-- 错误提示 -->
              <div v-else-if="pendingSummaryError" class="clean-error-state">
                <span>⚠️ {{ pendingSummaryError }}</span>
                <button type="button" class="btn-clean-ghost small" @click="loadPendingDeliveriesSummary(true)">重试</button>
              </div>

              <!-- 空状态 -->
              <div v-else-if="!sortedPendingSummaryRows.length" class="clean-empty-state">
                <span class="empty-emoji">🎉</span>
                <h4>太好了！当前没有未确认或在途滞留的发货单</h4>
                <p>管辖标段内所有物资均已正常完成到站与接收。</p>
              </div>

              <!-- 数据呈现区 -->
              <div v-else class="pending-content-wrapper">
                <!-- A. 桌面端：通透大气的大横表 (PC Table) -->
                <div class="clean-table-scroll-wrap pc-only-table">
                  <table class="clean-wide-table">
                    <thead>
                      <tr>
                        <th style="width: 48px; text-align: center;">#</th>
                        <th style="width: 88px; text-align: center;">物料品类</th>
                        <th style="width: 110px; text-align: center;">当前状态</th>
                        <th style="width: 130px;">需求标段</th>
                        <th style="width: 160px;">订单号 / 运输车次</th>
                        <th style="width: 100px;">车牌号</th>
                        <th style="width: 140px;">供给厂家</th>
                        <th style="min-width: 180px;">规格型号 / 物料名称</th>
                        <th style="width: 110px; text-align: right;">发货数量</th>
                        <th style="width: 120px;">发货时间</th>
                        <th
                          style="width: 125px; cursor: pointer; user-select: none;"
                          class="clean-sort-th"
                          @click="togglePendingSummarySort"
                          title="点击按在途时长升降序排列（次级按操作等待时长排序）"
                        >
                          <span>在途时长</span>
                          <span class="sort-icon-tag">{{ pendingSummaryFilter.sortOrder === 'desc' ? '▼ 降序' : '▲ 升序' }}</span>
                        </th>
                        <th style="width: 125px;" title="待到货确认单据为在途时长；待施工接收单据为自确认到货以来的时长">
                          <span>操作等待时长</span>
                        </th>
                        <th style="width: 170px; text-align: center;">现场督办操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(row, idx) in sortedPendingSummaryRows"
                        :key="`${row.category}_${row.id}`"
                        class="clean-table-tr"
                        :class="{ 'tr-severe': row.is_severe_delay, 'tr-warning': row.is_warning_delay && !row.is_severe_delay }"
                      >
                        <td style="text-align: center; color: #94a3b8; font-size: 12px;">{{ idx + 1 }}</td>
                        <td style="text-align: center;">
                          <span class="clean-cat-badge" :class="row.category">
                            {{ row.category === 'pipe' ? '🔥 直管' : '🔩 管件' }}
                          </span>
                        </td>
                        <td style="text-align: center;">
                          <span
                            class="clean-status-badge"
                            :class="row.status === 'pending_arrival' ? 'st-arriving' : (row.status === 'pending_receive' ? 'st-receiving' : 'st-diff')"
                          >
                            {{ row.status_label }}
                          </span>
                        </td>
                        <td>
                          <span class="clean-section-tag">📍 {{ row.section_1_name }}</span>
                        </td>
                        <td>
                          <div class="order-code-main font-mono">
                            {{ row.order_no }}
                            <span v-if="row.is_grouped && row.sub_count > 1" class="sub-count-tag" :title="`该车次合并了 ${row.sub_count} 笔发货单`">
                              共{{ row.sub_count }}单
                            </span>
                          </div>
                          <div v-if="row.shipment_no && row.shipment_no !== '—'" class="shipment-code-sub font-mono">
                            车次: {{ row.shipment_no }}
                          </div>
                        </td>
                        <td>
                          <span class="clean-plate-pill">{{ row.vehicle_plate_no || '未填' }}</span>
                        </td>
                        <td>
                          <div class="supply-entity-cell text-ellipsis" :title="row.supply_entity_name">
                            🏭 {{ row.supply_entity_name }}
                          </div>
                        </td>
                        <td>
                          <div class="material-name-cell">
                            <strong>{{ row.material_name }}</strong>
                          </div>
                        </td>
                        <td style="text-align: right;">
                          <span class="qty-highlight">{{ row.quantity_display }}</span>
                        </td>
                        <td>
                          <span class="time-cell-text">{{ formatShortDateTime(row.shipped_at) }}</span>
                        </td>
                        <td>
                          <div
                            class="clean-elapsed-pill"
                            :class="{ 'is-severe': row.is_severe_delay, 'is-warning': row.is_warning_delay && !row.is_severe_delay }"
                          >
                            ⏱️ {{ row.elapsed_display }}
                          </div>
                        </td>
                        <td>
                          <div
                            class="clean-elapsed-pill unconfirmed"
                            :class="{
                              'is-severe': row.is_unconfirmed_severe,
                              'is-warning': row.is_unconfirmed_warning && !row.is_unconfirmed_severe
                            }"
                          >
                            ⏳ {{ row.unconfirmed_elapsed_display || row.elapsed_display }}
                          </div>
                        </td>
                        <td style="text-align: center;">
                          <div class="clean-op-btn-group">
                            <button
                              type="button"
                              class="op-btn-jump"
                              @click="handleJumpToSectionDelivery(row)"
                              title="切换至该标段并前往现场到货/施工接收确认"
                            >
                              📍 定位处理
                            </button>
                            <button
                              type="button"
                              class="op-btn-detail"
                              @click="showDeliveryDetail(row)"
                              title="查看单据完整时光轴与凭证"
                            >
                              👁️ 详情
                            </button>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- B. 手机端 / 窄屏：自动展示精致小卡片 (Mobile Cards) -->
                <div class="mobile-only-cards-grid">
                  <div
                    v-for="row in sortedPendingSummaryRows"
                    :key="`m_${row.category}_${row.id}`"
                    class="mobile-ticket-card"
                    :class="{ 'card-severe': row.is_severe_delay, 'card-warning': row.is_warning_delay && !row.is_severe_delay }"
                  >
                    <!-- 手机卡片顶栏 -->
                    <div class="m-card-header">
                      <div class="m-tags-row">
                        <span class="clean-section-tag">📍 {{ row.section_1_name }}</span>
                        <span class="clean-cat-badge" :class="row.category">
                          {{ row.category === 'pipe' ? '🔥 直管' : '🔩 管件' }}
                        </span>
                        <span
                          class="clean-status-badge"
                          :class="row.status === 'pending_arrival' ? 'st-arriving' : (row.status === 'pending_receive' ? 'st-receiving' : 'st-diff')"
                        >
                          {{ row.status_label }}
                        </span>
                      </div>
                      <div class="m-elapsed-box">
                        <div
                          class="clean-elapsed-pill mini"
                          :class="{ 'is-severe': row.is_severe_delay, 'is-warning': row.is_warning_delay && !row.is_severe_delay }"
                          title="在途时长"
                        >
                          ⏱️ 在途: {{ row.elapsed_display }}
                        </div>
                        <div
                          class="clean-elapsed-pill mini unconfirmed"
                          :class="{
                            'is-severe': row.is_unconfirmed_severe,
                            'is-warning': row.is_unconfirmed_warning && !row.is_unconfirmed_severe
                          }"
                          title="操作等待时长"
                        >
                          ⏳ 等待: {{ row.unconfirmed_elapsed_display || row.elapsed_display }}
                        </div>
                      </div>
                    </div>

                    <!-- 手机卡片主体 -->
                    <div class="m-card-body">
                      <div class="m-material-title">
                        <strong>{{ row.material_name }}</strong>
                      </div>
                      <div class="m-grid-kv">
                        <div class="m-kv-item">
                          <span class="m-k">订单编号:</span>
                          <span class="m-v font-mono">{{ row.order_no }}</span>
                        </div>
                        <div class="m-kv-item">
                          <span class="m-k">发货数量:</span>
                          <span class="m-v qty">{{ row.quantity_display }}</span>
                        </div>
                        <div class="m-kv-item">
                          <span class="m-k">运输车牌:</span>
                          <span class="m-v">{{ row.vehicle_plate_no || '未填' }}</span>
                        </div>
                        <div class="m-kv-item">
                          <span class="m-k">发货厂家:</span>
                          <span class="m-v text-ellipsis">{{ row.supply_entity_name }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- 手机卡片底栏 -->
                    <div class="m-card-footer">
                      <button
                        type="button"
                        class="m-btn-detail"
                        @click="showDeliveryDetail(row)"
                      >
                        👁️ 流转详情
                      </button>
                      <button
                        type="button"
                        class="m-btn-jump"
                        @click="handleJumpToSectionDelivery(row)"
                      >
                        📍 前往现场确认 ➔
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 4. 弹窗底栏 Footer -->
          <div class="pending-clean-footer">
            <div v-if="supervisionActiveTab === 'governance'" class="footer-stats-left">
              <span class="f-stat-item">
                管辖标段：<strong>{{ governanceSections.length }}</strong> 个
              </span>
              <span class="f-divider">/</span>
              <span class="f-stat-item">
                全部闭环：<strong class="text-emerald">{{ governanceSummary.all_completed_count || 0 }} 标段</strong>
              </span>
              <span class="f-divider">/</span>
              <span class="f-stat-item">
                待催办：<strong class="text-amber">{{ governanceSummary.pending_sections_count || 0 }} 标段</strong>
              </span>
            </div>

            <div v-else class="footer-stats-left">
              <span class="f-stat-item">
                待办单据：<strong>{{ sortedPendingSummaryRows.length }}</strong> 笔
              </span>
              <span class="f-divider">/</span>
              <span class="f-stat-item">
                在途直管：<strong class="text-blue">{{ summaryAggregates.totalPipeMeters }} 米</strong>
              </span>
              <span class="f-divider">/</span>
              <span class="f-stat-item">
                在途管件：<strong class="text-purple">{{ summaryAggregates.totalFittingCount }} 件</strong>
              </span>
            </div>

            <div class="footer-btn-right">
              <button type="button" class="btn-clean-close-foot" @click="pendingSummaryModalVisible = false">
                关闭
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as XLSX from 'xlsx-js-style'
import * as echarts from 'echarts'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import { AppHeader, Breadcrumbs, useTubePageShell, getDeliveryStatus, navigateToUserInDirectory } from './shared'
import ExportSettingsModal from './ExportSettingsModal.vue'
import DeliveryBillOcrTool from './DeliveryBillOcrTool.vue'
import {
  confirmTubeDemandManagementDeliveryArrival,
  confirmTubeDemandManagementDeliveryReceipt,
  approveTubeDemandManagementDeliveryDifference,
  getTubeDemandManagementBaseline,
  getTubeDemandManagementFittingBaseline,
  getTubeDemandManagementLogisticsRecords,
  getTubeDemandManagementPendingDeliveriesSummary,
  getTubeDemandManagementGovernanceOverview,
  getTubeDemandManagementOptions,
  getTubeDemandManagementPlanMatrix,
  getTubeDemandManagementUsageSheet,
  saveTubeDemandManagementPlanMatrix,
  saveTubeDemandManagementUsageSheet,
  saveTubeGlobalManagementConfigSection,
  submitTubeDemandManagementSection1Status,
  getFittingDeliveriesList,
  confirmFittingDeliveryArrival,
  confirmFittingDeliveryConstruction,
  getTubeFittingInventorySummary,
  submitTubeFittingUsage,
  listTubeFittingUsageHistory,
  listTubePipeUsageHistory,
  cancelTubeFittingUsage,
  updateTubeFittingUsageItem,
  updateTubeFittingUsageBatch,
  getTubeSupplyManagementDemandSummary
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'

const auth = useAuthStore()
const canExtractXlsx = computed(() => auth.canExtractXlsxFor(PROJECT_KEY))
const route = useRoute()
const router = useRouter()

const VALID_TABS = ['overview', 'usage', 'plan', 'logistics', 'baseline', 'fitting', 'fitting_usage', 'fitting_baseline', 'ocr_tool']
const VALID_CATEGORIES = ['pipe', 'fitting', 'tools']

// 清理历史残留的 localStorage 缓存，避免跨入口污染
try {
  localStorage.removeItem('phoenix_demand_management_active_category')
  localStorage.removeItem('phoenix_demand_management_active_tab')
  localStorage.removeItem('phoenix_demand_management_section1_id')
} catch (e) {}

const getInitialCategoryAndTab = () => {
  // 纯粹依据当前 URL Query 参数（刷新页面时 URL 自带参数，从主菜单进入时 URL 干净则展示默认页）
  const queryTab = String(route?.query?.tab || '').trim()
  const queryCategory = String(route?.query?.category || '').trim()

  if (VALID_TABS.includes(queryTab)) {
    let inferredCategory = 'pipe'
    if (['fitting', 'fitting_usage', 'fitting_baseline'].includes(queryTab)) {
      inferredCategory = 'fitting'
    } else if (['ocr_tool'].includes(queryTab)) {
      inferredCategory = 'tools'
    }
    return {
      category: VALID_CATEGORIES.includes(queryCategory) ? queryCategory : inferredCategory,
      tab: queryTab,
    }
  }

  // 无 Query 时严格返回默认首页
  return { category: 'pipe', tab: 'usage' }
}

const syncTabStateToUrl = (category, tab) => {
  if (route?.query?.tab !== tab || route?.query?.category !== category) {
    router.replace({
      query: {
        ...(route?.query || {}),
        category,
        tab,
      },
    }).catch(() => {})
  }
}

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

const initialSelection = getInitialCategoryAndTab()
const selectedSection1Id = ref('')
const activeCategory = ref(initialSelection.category) // 'pipe' | 'fitting'
const lastPipeTab = ref(initialSelection.category === 'pipe' ? initialSelection.tab : 'usage') // 记忆直管最后选中的子标签
const lastFittingTab = ref(initialSelection.category === 'fitting' ? initialSelection.tab : 'fitting') // 记忆管件最后选中的子标签
const activeTab = ref(initialSelection.tab)
const showExportModal = ref(false)
const blockModalVisible = ref(false)
const blockModalData = ref(null)
const allPendingRows = ref([])

// 🚚 全标段现场综合督办中心状态
const pendingSummaryModalVisible = ref(false)

// --- 📈 保温管“需求与库存信息统计”核心状态与方法 ---
const overviewLoading = ref(false)
const overviewError = ref('')
const overviewRows = ref([])
const overviewSearchKeyword = ref('')
const overviewOnlyShowGap = ref(false)
const overviewChartRef = ref(null)
let overviewChartInstance = null

function formatQtyDisplay(val) {
  const num = Number(val || 0)
  if (!Number.isFinite(num)) return '0.00'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const overviewStats = computed(() => {
  let totalPlan = 0
  let totalShipped = 0
  let totalArrived = 0
  let totalUsage = 0
  let totalInventory = 0
  let totalTransit = 0
  let totalInventoryPlusTransit = 0
  let totalNetGap = 0
  let planModelsCount = 0
  let gapModelsCount = 0

  overviewRows.value.forEach(r => {
    totalPlan += r.futurePlanQty || 0
    totalShipped += r.totalShippedQty || 0
    totalArrived += r.totalArrivedQty || 0
    totalUsage += r.totalUsageQty || 0
    totalInventory += r.inventoryQty || 0
    totalTransit += r.pendingArrivalQty || 0
    totalInventoryPlusTransit += r.inventoryPlusPipeline || 0
    totalNetGap += r.netGapQty || 0

    if ((r.futurePlanQty || 0) > 0) {
      planModelsCount += 1
    }
    if ((r.netGapQty || 0) > 0) {
      gapModelsCount += 1
    }
  })

  return {
    totalPlan: Math.round(totalPlan * 100) / 100,
    totalShipped: Math.round(totalShipped * 100) / 100,
    totalArrived: Math.round(totalArrived * 100) / 100,
    totalUsage: Math.round(totalUsage * 100) / 100,
    totalInventory: Math.round(totalInventory * 100) / 100,
    totalTransit: Math.round(totalTransit * 100) / 100,
    totalInventoryPlusTransit: Math.round(totalInventoryPlusTransit * 100) / 100,
    totalNetGap: Math.round(totalNetGap * 100) / 100,
    planModelsCount,
    gapModelsCount,
  }
})

const filteredOverviewRows = computed(() => {
  let list = overviewRows.value

  if (overviewOnlyShowGap.value) {
    list = list.filter(r => (r.netGapQty || 0) > 0)
  }

  if (overviewSearchKeyword.value) {
    const kw = overviewSearchKeyword.value.toLowerCase().trim()
    list = list.filter(r => 
      String(r.pipeModelName || '').toLowerCase().includes(kw) || 
      String(r.pipeModelId || '').toLowerCase().includes(kw)
    )
  }

  return sortPipeModelsByDiameterDesc(list)
})

const filteredOverviewTotals = computed(() => {
  let futurePlanQty = 0
  let totalShippedQty = 0
  let totalUsageQty = 0
  let inventoryQty = 0
  let pendingArrivalQty = 0
  let inventoryPlusPipeline = 0
  let netGapQty = 0

  filteredOverviewRows.value.forEach(r => {
    futurePlanQty += r.futurePlanQty || 0
    totalShippedQty += r.totalShippedQty || 0
    totalUsageQty += r.totalUsageQty || 0
    inventoryQty += r.inventoryQty || 0
    pendingArrivalQty += r.pendingArrivalQty || 0
    inventoryPlusPipeline += r.inventoryPlusPipeline || 0
    netGapQty += r.netGapQty || 0
  })

  return {
    futurePlanQty: Math.round(futurePlanQty * 100) / 100,
    totalShippedQty: Math.round(totalShippedQty * 100) / 100,
    totalUsageQty: Math.round(totalUsageQty * 100) / 100,
    inventoryQty: Math.round(inventoryQty * 100) / 100,
    pendingArrivalQty: Math.round(pendingArrivalQty * 100) / 100,
    inventoryPlusPipeline: Math.round(inventoryPlusPipeline * 100) / 100,
    netGapQty: Math.round(netGapQty * 100) / 100,
  }
})

async function loadDemandInventoryOverview() {
  if (!selectedSection1Id.value) return
  overviewLoading.value = true
  overviewError.value = ''

  try {
    const showDate = usageDate.value || undefined
    const res = await getTubeSupplyManagementDemandSummary(PROJECT_KEY, { show_date: showDate })
    const allRows = Array.isArray(res?.rows) ? res.rows : []
    
    // 过滤当前需求主体
    const targetSectionId = String(selectedSection1Id.value).trim().toUpperCase()
    const secRows = allRows.filter(r => String(r.section_1_id || '').trim().toUpperCase() === targetSectionId)

    const mappedRows = secRows.map(r => {
      const futurePlanQty = Number(r.future_plan_qty) || 0
      const totalShippedQty = Number(r.total_shipped_qty) || 0
      const totalArrivedQty = Number(r.total_arrived_qty) || 0
      const totalUsageQty = Number(r.total_usage_qty) || 0
      const inventoryQty = Number(r.section_1_inventory_qty) || 0
      const pendingArrivalQty = Number(r.pending_arrival_qty) || 0
      const inventoryPlusPipeline = Math.round((inventoryQty + pendingArrivalQty) * 100) / 100
      const netGapQty = Number(r.net_gap_qty) || 0
      const hardGapQty = Number(r.hard_gap_qty) || 0

      // 保供态势判定
      let statusText = '⚪ 现存安全'
      let statusPillClass = 'pill-neutral'
      if (netGapQty > 0) {
        statusText = '🚨 紧缺待调拨'
        statusPillClass = 'pill-danger'
      } else if (futurePlanQty > inventoryQty && futurePlanQty <= inventoryPlusPipeline) {
        statusText = '🚚 在途可满足'
        statusPillClass = 'pill-info'
      } else if (futurePlanQty > 0 && inventoryQty >= futurePlanQty) {
        statusText = '✅ 现存充足'
        statusPillClass = 'pill-success'
      } else if (futurePlanQty === 0 && inventoryQty > 0) {
        statusText = '📦 现存富余'
        statusPillClass = 'pill-neutral'
      }

      return {
        pipeModelId: r.pipe_model_id,
        pipeModelName: r.pipe_model_name || r.pipe_model_id,
        futurePlanQty,
        totalShippedQty,
        totalArrivedQty,
        totalUsageQty,
        inventoryQty,
        pendingArrivalQty,
        inventoryPlusPipeline,
        netGapQty,
        hardGapQty,
        statusText,
        statusPillClass,
      }
    })

    overviewRows.value = sortPipeModelsByDiameterDesc(mappedRows)

    await nextTick()
    renderOverviewChart()
  } catch (err) {
    console.error('加载需求与库存信息统计失败:', err)
    overviewError.value = err?.message || '读取需求与库存统计失败'
  } finally {
    overviewLoading.value = false
    await nextTick()
    renderOverviewChart()
    setTimeout(() => {
      handleResizeOverviewChart()
    }, 80)
    setTimeout(() => {
      handleResizeOverviewChart()
    }, 300)
  }
}

function renderOverviewChart() {
  if (!overviewChartRef.value) return
  if (!overviewChartInstance) {
    overviewChartInstance = echarts.init(overviewChartRef.value)
    if (window.ResizeObserver) {
      try {
        const ro = new ResizeObserver(() => {
          handleResizeOverviewChart()
        })
        ro.observe(overviewChartRef.value)
      } catch (e) {}
    }
  }

  const dataList = overviewRows.value
  if (!dataList || dataList.length === 0) {
    overviewChartInstance.clear()
    return
  }

  const modelNames = dataList.map(item => item.pipeModelName)
  const planData = dataList.map(item => item.futurePlanQty)
  const invData = dataList.map(item => item.inventoryQty)
  const transitData = dataList.map(item => item.pendingArrivalQty)
  const netGapData = dataList.map(item => item.netGapQty)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: function (params) {
        if (!params || !params.length) return ''
        const modelName = params[0].name
        const targetRow = dataList.find(d => d.pipeModelName === modelName) || {}
        let html = `<div style="font-weight: 700; margin-bottom: 6px; color: #0f172a; font-size: 13px;">📏 ${modelName}</div>`
        html += `<div style="display: grid; grid-template-columns: auto auto; gap: 4px 12px; font-size: 12px;">`
        html += `<span style="color: #6d28d9;">🟣 三日需求计划:</span><strong style="text-align: right;">${formatQtyDisplay(targetRow.futurePlanQty)} m</strong>`
        html += `<span style="color: #047857;">🟢 现场实物库存:</span><strong style="text-align: right;">${formatQtyDisplay(targetRow.inventoryQty)} m</strong>`
        html += `<span style="color: #0284c7;">🔵 运输在途保供:</span><strong style="text-align: right;">${formatQtyDisplay(targetRow.pendingArrivalQty)} m</strong>`
        html += `<span style="color: #0f766e;">🌐 现存+在途合计:</span><strong style="text-align: right;">${formatQtyDisplay(targetRow.inventoryPlusPipeline)} m</strong>`
        html += `<span style="color: #475569;">🚚 累计发货总量:</span><strong style="text-align: right;">${formatQtyDisplay(targetRow.totalShippedQty)} m</strong>`
        html += `<span style="color: #475569;">🔨 累计施工消耗:</span><strong style="text-align: right;">${formatQtyDisplay(targetRow.totalUsageQty)} m</strong>`
        const gapColor = (targetRow.netGapQty || 0) > 0 ? '#b91c1c' : '#15803d'
        const gapText = (targetRow.netGapQty || 0) > 0 ? `⚠️ ${formatQtyDisplay(targetRow.netGapQty)} m` : `0.00 m (安全)`
        html += `<span style="color: ${gapColor}; font-weight: bold;">🔴 三日净缺口:</span><strong style="text-align: right; color: ${gapColor};">${gapText}</strong>`
        html += `</div>`
        return html
      }
    },
    legend: {
      top: 6,
      right: 12,
      data: ['三日需求计划', '现场库存', '运输在途', '三日净缺口'],
      textStyle: { color: '#475569', fontSize: 12 }
    },
    grid: {
      left: '2%',
      right: '2%',
      bottom: '14%',
      top: '18%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: modelNames,
      axisLabel: {
        interval: 0,
        rotate: modelNames.length > 5 ? 25 : 0,
        fontSize: 11,
        color: '#475569'
      },
      axisLine: { lineStyle: { color: '#cbd5e1' } }
    },
    yAxis: {
      type: 'value',
      name: '米 (m)',
      nameTextStyle: { color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
    },
    series: [
      {
        name: '三日需求计划',
        type: 'bar',
        barMaxWidth: 22,
        data: planData,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#a78bfa' },
            { offset: 1, color: '#7c3aed' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '现场库存',
        type: 'bar',
        barMaxWidth: 22,
        data: invData,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#34d399' },
            { offset: 1, color: '#059669' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '运输在途',
        type: 'bar',
        barMaxWidth: 22,
        data: transitData,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#38bdf8' },
            { offset: 1, color: '#0284c7' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      },
      {
        name: '三日净缺口',
        type: 'bar',
        barMaxWidth: 22,
        data: netGapData,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#f87171' },
            { offset: 1, color: '#dc2626' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      }
    ]
  }

  overviewChartInstance.setOption(option, true)
  overviewChartInstance.resize()
}

function handleResizeOverviewChart() {
  if (overviewChartInstance && activeTab.value === 'overview') {
    overviewChartInstance.resize()
  }
}

function exportOverviewToExcel() {
  if (!overviewRows.value.length) return
  const currentSecName = section1Options.value.find(s => s.section_1_id === selectedSection1Id.value)?.section_1_name || selectedSection1Id.value

  const header = [
    '序号', '保温管规格型号', '未来三日计划(米)', '累计发货量(米)', '累计施工量(米)', 
    '现场库存量(米)', '运输在途量(米)', '库存+在途(米)', '三日净缺口(米)', '保供态势判定'
  ]
  const rows = filteredOverviewRows.value.map((r, idx) => [
    idx + 1,
    r.pipeModelName,
    r.futurePlanQty,
    r.totalShippedQty,
    r.totalUsageQty,
    r.inventoryQty,
    r.pendingArrivalQty,
    r.inventoryPlusPipeline,
    r.netGapQty,
    r.statusText
  ])

  rows.push([
    '合计',
    `共 ${filteredOverviewRows.value.length} 种型号`,
    filteredOverviewTotals.value.futurePlanQty,
    filteredOverviewTotals.value.totalShippedQty,
    filteredOverviewTotals.value.totalUsageQty,
    filteredOverviewTotals.value.inventoryQty,
    filteredOverviewTotals.value.pendingArrivalQty,
    filteredOverviewTotals.value.inventoryPlusPipeline,
    filteredOverviewTotals.value.netGapQty,
    filteredOverviewTotals.value.netGapQty > 0 ? `存在 ${overviewStats.value.gapModelsCount} 种缺料` : '全型号充足'
  ])

  const ws = XLSX.utils.aoa_to_sheet([header, ...rows])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '需求与库存统计')
  XLSX.writeFile(wb, `${currentSecName}_保温管需求与库存统计_${usageDate.value || '最新'}.xlsx`)
}
const supervisionActiveTab = ref('governance') // 'governance' (标段填报履约督办) | 'logistics' (在途发货单据督办)

// 标段填报履约大盘状态
const governanceLoading = ref(false)
const governanceError = ref('')
const governanceDates = ref({
  show_date: '',
  usage_collection_date: '',
  plan_start_date: ''
})
const governanceSummary = ref({
  total_sections: 0,
  plan_submitted_count: 0,
  pipe_usage_submitted_count: 0,
  fitting_usage_submitted_count: 0,
  all_completed_count: 0,
  pending_sections_count: 0,
  total_pending_deliveries: 0,
  severe_delay_deliveries: 0
})
const governanceSections = ref([])
const governanceFilter = reactive({
  status: 'all', // 'all' | 'pending' | 'completed'
  searchKeyword: ''
})

const filteredGovernanceSections = computed(() => {
  let list = governanceSections.value || []
  if (governanceFilter.status === 'pending') {
    list = list.filter(s => s.overall_status !== 'all_completed')
  } else if (governanceFilter.status === 'completed') {
    list = list.filter(s => s.overall_status === 'all_completed')
  }
  if (governanceFilter.searchKeyword) {
    const kw = governanceFilter.searchKeyword.trim().toLowerCase()
    list = list.filter(s =>
      (s.section_1_name || '').toLowerCase().includes(kw) ||
      (s.section_1_id || '').toLowerCase().includes(kw) ||
      (s.construction_unit_name || '').toLowerCase().includes(kw) ||
      (s.contact_name || '').toLowerCase().includes(kw) ||
      (s.contact_phone || '').includes(kw) ||
      (s.region || '').toLowerCase().includes(kw)
    )
  }
  return list
})

// 在途发货单据督办状态
const pendingSummaryLoading = ref(false)
const pendingSummaryError = ref('')
const pendingSummaryViewMode = ref('card') // 'card' | 'table'
const pendingSummaryRows = ref([])
const pendingSummaryStats = ref({
  total_count: 0,
  pending_arrival_count: 0,
  pending_receive_count: 0,
  severe_delay_count: 0,
  pipe_count: 0,
  fitting_count: 0
})
const pendingSummaryTotalCount = ref(0)
const pendingSummaryAccessibleSections = ref([])
const groupByShipment = ref(true) // 默认开启按车次合并，可手动切换

const pendingSummaryFilter = reactive({
  category: 'all',
  status: '',
  section1Id: '',
  searchKeyword: '',
  sortOrder: 'desc'
})

function setPendingSummaryCategory(cat) {
  pendingSummaryFilter.category = cat
  loadPendingDeliveriesSummary(true)
}

function setPendingSummaryStatusFilter(status) {
  if (pendingSummaryFilter.status === status) {
    pendingSummaryFilter.status = ''
  } else {
    pendingSummaryFilter.status = status
  }
  loadPendingDeliveriesSummary(true)
}

function clearPendingSummarySearch() {
  pendingSummaryFilter.searchKeyword = ''
  loadPendingDeliveriesSummary(true)
}

function togglePendingSummarySort() {
  pendingSummaryFilter.sortOrder = pendingSummaryFilter.sortOrder === 'desc' ? 'asc' : 'desc'
}

const processedPendingSummaryRows = computed(() => {
  const rawRows = pendingSummaryRows.value || []
  if (!groupByShipment.value) {
    return rawRows.map(r => ({
      ...r,
      is_grouped: false,
      sub_count: 1,
      sub_rows: [r],
      is_unconfirmed_severe: Boolean(r.is_unconfirmed_severe) || Number(r.unconfirmed_elapsed_seconds || 0) >= 172800,
      is_unconfirmed_warning: Boolean(r.is_unconfirmed_warning) || Number(r.unconfirmed_elapsed_seconds || 0) >= 86400,
    }))
  }

  const groupMap = new Map()

  rawRows.forEach((r) => {
    // 分组 Key：相同标段、相同品类、相同有效车次号
    const hasShipment = r.shipment_no && r.shipment_no !== '—' && String(r.shipment_no).trim() !== ''
    const groupKey = hasShipment
      ? `${r.section_1_id}_${r.category}_${r.shipment_no.trim()}_${r.vehicle_plate_no || ''}`
      : `${r.section_1_id}_${r.category}_INDIVIDUAL_${r.id}`

    if (!groupMap.has(groupKey)) {
      groupMap.set(groupKey, {
        ...r,
        group_key: groupKey,
        is_grouped: false,
        sub_count: 1,
        sub_rows: [r],
        shipped_qty: Number(r.shipped_qty || 0),
        elapsed_seconds: Number(r.elapsed_seconds || 0),
        unconfirmed_elapsed_seconds: Number(r.unconfirmed_elapsed_seconds || 0),
        is_severe_delay: Boolean(r.is_severe_delay) || Number(r.elapsed_seconds || 0) >= 172800,
        is_warning_delay: Boolean(r.is_warning_delay) || Number(r.elapsed_seconds || 0) >= 86400,
        is_unconfirmed_severe: Boolean(r.is_unconfirmed_severe) || Number(r.unconfirmed_elapsed_seconds || 0) >= 172800,
        is_unconfirmed_warning: Boolean(r.is_unconfirmed_warning) || Number(r.unconfirmed_elapsed_seconds || 0) >= 86400,
      })
    } else {
      const g = groupMap.get(groupKey)
      g.is_grouped = true
      g.sub_count += 1
      g.sub_rows.push(r)
      g.shipped_qty += Number(r.shipped_qty || 0)

      // 物料聚合
      const uniqueMats = [...new Set(g.sub_rows.map(item => item.material_name || item.pipe_model_name || ''))].filter(Boolean)
      if (uniqueMats.length === 1) {
        g.material_name = uniqueMats[0]
      } else {
        g.material_name = `${uniqueMats[0]} 等共 ${uniqueMats.length} 种物料`
      }

      // 单号聚合
      const allOrders = g.sub_rows.map(item => item.order_no || item.delivery_code).filter(Boolean)
      g.order_no = `${allOrders[0]} 等(共${g.sub_count}单)`

      // 时长取最大延误
      if (Number(r.elapsed_seconds || 0) > g.elapsed_seconds) {
        g.elapsed_seconds = Number(r.elapsed_seconds || 0)
        g.elapsed_display = r.elapsed_display
        g.shipped_at = r.shipped_at
      }
      if (Number(r.unconfirmed_elapsed_seconds || 0) > g.unconfirmed_elapsed_seconds) {
        g.unconfirmed_elapsed_seconds = Number(r.unconfirmed_elapsed_seconds || 0)
        g.unconfirmed_elapsed_display = r.unconfirmed_elapsed_display
      }

      // 预警合并
      if (r.is_severe_delay || Number(r.elapsed_seconds || 0) >= 172800) g.is_severe_delay = true
      if (r.is_warning_delay || Number(r.elapsed_seconds || 0) >= 86400) g.is_warning_delay = true
      if (r.is_unconfirmed_severe || Number(r.unconfirmed_elapsed_seconds || 0) >= 172800) g.is_unconfirmed_severe = true
      if (r.is_unconfirmed_warning || Number(r.unconfirmed_elapsed_seconds || 0) >= 86400) g.is_unconfirmed_warning = true

      // 联系方式补齐
      if (!g.ship_contact_phone && r.ship_contact_phone) {
        g.ship_contact_phone = r.ship_contact_phone
        g.ship_contact_name = r.ship_contact_name
      }
    }
  })

  // 格式化合并后的数量显示
  return Array.from(groupMap.values()).map(g => {
    if (g.category === 'pipe') {
      g.quantity_display = `${g.shipped_qty.toFixed(1)} 米`
    } else {
      g.quantity_display = `${Math.round(g.shipped_qty)} ${g.unit || '个'}`
    }
    return g
  })
})

const sortedPendingSummaryRows = computed(() => {
  const rows = [...processedPendingSummaryRows.value]
  const isDesc = pendingSummaryFilter.sortOrder === 'desc'
  return rows.sort((a, b) => {
    const timeA = Number(a.elapsed_seconds || 0)
    const timeB = Number(b.elapsed_seconds || 0)
    if (timeA !== timeB) {
      return isDesc ? timeB - timeA : timeA - timeB
    }
    const unconfA = Number(a.unconfirmed_elapsed_seconds || 0)
    const unconfB = Number(b.unconfirmed_elapsed_seconds || 0)
    return isDesc ? unconfB - unconfA : unconfA - unconfB
  })
})

const summaryAggregates = computed(() => {
  let totalPipeMeters = 0
  let totalFittingCount = 0
  ;(pendingSummaryRows.value || []).forEach((r) => {
    if (r.category === 'pipe') {
      totalPipeMeters += Number(r.shipped_qty || 0)
    } else {
      totalFittingCount += Number(r.shipped_qty || 0)
    }
  })
  return {
    totalPipeMeters: totalPipeMeters.toFixed(2),
    totalFittingCount: Math.round(totalFittingCount),
  }
})

async function copyContactPhone(phone, name) {
  if (!phone) return
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(phone)
      setActionMessage('success', `已复制【${name || '联系人'}】电话：${phone}`)
    } else {
      prompt('联系人电话（请按 Ctrl+C 复制）：', phone)
    }
  } catch (e) {
    prompt('联系人电话（请按 Ctrl+C 复制）：', phone)
  }
}

async function loadGovernanceOverview(showLoading = true) {
  if (showLoading) {
    governanceLoading.value = true
    governanceError.value = ''
  }
  try {
    const res = await getTubeDemandManagementGovernanceOverview(PROJECT_KEY)
    if (res && res.ok) {
      governanceSections.value = res.sections || []
      governanceSummary.value = res.summary || {}
      governanceDates.value = res.dates || {}
    }
  } catch (err) {
    if (showLoading) {
      governanceError.value = err?.message || '加载全标段填报履约大盘失败'
    }
  } finally {
    if (showLoading) {
      governanceLoading.value = false
    }
  }
}

async function loadPendingDeliveriesSummary(showLoading = true) {
  if (showLoading) {
    pendingSummaryLoading.value = true
    pendingSummaryError.value = ''
  }
  try {
    const res = await getTubeDemandManagementPendingDeliveriesSummary(PROJECT_KEY, {
      section_1_id: pendingSummaryFilter.section1Id || '',
      category: pendingSummaryFilter.category || 'all',
      status: pendingSummaryFilter.status || '',
      search: pendingSummaryFilter.searchKeyword || ''
    })
    if (res && res.ok) {
      pendingSummaryRows.value = res.rows || []
      pendingSummaryStats.value = res.summary || {}
      pendingSummaryTotalCount.value = res.summary?.total_count || 0
      pendingSummaryAccessibleSections.value = res.accessible_sections || []
    }
  } catch (err) {
    if (showLoading) {
      pendingSummaryError.value = err?.message || '加载全标段在途与待接收单据失败'
    }
  } finally {
    if (showLoading) {
      pendingSummaryLoading.value = false
    }
  }
}

function openPendingSummaryModal(defaultTab = 'governance') {
  supervisionActiveTab.value = defaultTab
  pendingSummaryModalVisible.value = true
  loadGovernanceOverview(true)
  loadPendingDeliveriesSummary(true)
}

function handleSelectSectionFromGovernance(sectionId, targetDimension = '') {
  if (!sectionId) return
  selectedSection1Id.value = sectionId
  if (targetDimension === 'fitting') {
    activeCategory.value = 'fitting'
    activeTab.value = 'fitting'
  } else if (targetDimension === 'plan') {
    activeCategory.value = 'pipe'
    activeTab.value = 'plan'
  } else {
    activeCategory.value = 'pipe'
    activeTab.value = 'usage'
  }
  syncTabStateToUrl(activeCategory.value, activeTab.value)
  pendingSummaryModalVisible.value = false
  const secName = governanceSections.value.find(s => s.section_1_id === sectionId)?.section_1_name || sectionId
  setActionMessage('success', `已为您切换至标段【${secName}】工作台。`)
}

function handleJumpToSectionDelivery(row) {
  if (!row || !row.section_1_id) return
  selectedSection1Id.value = row.section_1_id
  if (row.category === 'fitting') {
    activeCategory.value = 'fitting'
    activeTab.value = 'fitting'
  } else {
    activeCategory.value = 'pipe'
    activeTab.value = 'logistics'
  }
  syncTabStateToUrl(activeCategory.value, activeTab.value)
  pendingSummaryModalVisible.value = false
  setActionMessage('success', `已为您切换至标段【${row.section_1_name}】并定位至到货与施工接收记录。`)
}

function exportPendingSummaryExcel() {
  const rows = sortedPendingSummaryRows.value
  if (!rows.length) {
    alert('当前没有待处理的发货单数据可导出。')
    return
  }

  const exportTime = new Date().toLocaleString()
  const todayStr = getTodayString()
  const modeText = groupByShipment.value
    ? `按车次合并模式 (共 ${rows.length} 车次 / 汇总 ${pendingSummaryRows.value.length} 笔单据)`
    : `单据明细模式 (共 ${rows.length} 笔单据)`

  // 1. 构建数据行（含大标题行、摘要行、表头行）
  const titleRow = ['全标段发货督办清单', ...Array(22).fill('')]
  const metaRow = [
    `导出时间：${exportTime}  |  导出模式：${modeText}  |  待办单据：${rows.length} 笔  |  在途直管：${summaryAggregates.value.totalPipeMeters} 米  |  在途管件：${summaryAggregates.value.totalFittingCount} 件`,
    ...Array(22).fill('')
  ]
  const headers = [
    '序号', '物料品类', '当前状态', '需求标段', '订单号', '运输车次号', '车牌号',
    '供给厂家', '规格型号 / 物料描述', '发货数量', '单位', '发货时间', '在途时长', '操作等待时长',
    '发货负责人', '联系电话', '发货备注', '现场到货时间', '到货确认人', '到货备注说明',
    '施工接收时间', '施工接收人', '施工接收备注'
  ]

  const dataRows = rows.map((r, idx) => [
    idx + 1,
    r.category_label || (r.category === 'pipe' ? '保温直管' : '管件'),
    r.status_label || r.status,
    r.section_1_name || r.section_1_id,
    r.order_no || r.delivery_code || '',
    r.shipment_no || '—',
    r.vehicle_plate_no || '—',
    r.supply_entity_name || r.supply_entity_id,
    r.material_name || r.pipe_model_name || '',
    r.shipped_qty != null ? r.shipped_qty : '',
    r.unit || '',
    r.shipped_at ? formatDateTimeDisplay(r.shipped_at) : '',
    r.elapsed_display || '',
    r.unconfirmed_elapsed_display || r.elapsed_display || '',
    r.ship_contact_name || '',
    r.ship_contact_phone || '',
    r.ship_remark || '',
    r.arrived_confirm_at ? formatDateTimeDisplay(r.arrived_confirm_at) : '',
    r.arrived_confirm_by || '',
    r.arrived_remark || '',
    r.received_confirm_at ? formatDateTimeDisplay(r.received_confirm_at) : '',
    r.received_confirm_by || '',
    r.received_remark || ''
  ])

  const wsData = [titleRow, metaRow, headers, ...dataRows]
  const ws = XLSX.utils.aoa_to_sheet(wsData)

  // 2. 合并大标题与摘要栏
  ws['!merges'] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: 22 } },
    { s: { r: 1, c: 0 }, e: { r: 1, c: 22 } }
  ]

  // 3. 列宽自适应
  ws['!cols'] = [
    { wch: 6 },  // 序号
    { wch: 10 }, // 物料品类
    { wch: 12 }, // 当前状态
    { wch: 16 }, // 需求标段
    { wch: 18 }, // 订单号
    { wch: 14 }, // 运输车次号
    { wch: 12 }, // 车牌号
    { wch: 20 }, // 供给厂家
    { wch: 28 }, // 规格型号 / 物料描述
    { wch: 12 }, // 发货数量
    { wch: 6 },  // 单位
    { wch: 18 }, // 发货时间
    { wch: 14 }, // 在途时长
    { wch: 14 }, // 操作等待时长
    { wch: 10 }, // 发货负责人
    { wch: 14 }, // 联系电话
    { wch: 18 }, // 发货备注
    { wch: 18 }, // 现场到货时间
    { wch: 10 }, // 到货确认人
    { wch: 18 }, // 到货备注说明
    { wch: 18 }, // 施工接收时间
    { wch: 10 }, // 施工接收人
    { wch: 18 }  // 施工接收备注
  ]

  // 4. 行高
  ws['!rows'] = [
    { hpx: 36 }, // 大标题
    { hpx: 24 }, // 摘要栏
    { hpx: 28 }, // 表头
  ]

  // 5. 边框统一样式
  const thinBorder = {
    top: { style: 'thin', color: { rgb: 'CBD5E1' } },
    bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
    left: { style: 'thin', color: { rgb: 'CBD5E1' } },
    right: { style: 'thin', color: { rgb: 'CBD5E1' } }
  }

  // 6. 遍历单元格赋予专业排版与延误标色
  const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:W4')
  for (let R = range.s.r; R <= range.e.r; ++R) {
    for (let C = range.s.c; C <= range.e.c; ++C) {
      const cellRef = XLSX.utils.encode_cell({ r: R, c: C })
      if (!ws[cellRef]) ws[cellRef] = { v: '', t: 's' }

      if (R === 0) {
        // 大标题行
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 15, bold: true, color: { rgb: '0F172A' } },
          fill: { fgColor: { rgb: 'F1F5F9' } },
          alignment: { horizontal: 'center', vertical: 'center' },
          border: thinBorder
        }
      } else if (R === 1) {
        // 摘要统计行
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 9.5, color: { rgb: '475569' } },
          fill: { fgColor: { rgb: 'F8FAFC' } },
          alignment: { horizontal: 'center', vertical: 'center' },
          border: thinBorder
        }
      } else if (R === 2) {
        // 深蓝表头行
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 10.5, bold: true, color: { rgb: 'FFFFFF' } },
          fill: { fgColor: { rgb: '2563EB' } },
          alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
          border: thinBorder
        }
      } else {
        // 数据行 (R >= 3, 对应 rows[R - 3])
        const dataIndex = R - 3
        const rData = rows[dataIndex] || {}
        const isZebra = dataIndex % 2 === 1
        const bgRgb = isZebra ? 'F8FAFC' : 'FFFFFF'

        // 默认数据单元格样式
        const cellStyle = {
          font: { name: 'Microsoft YaHei', sz: 10, color: { rgb: '334155' } },
          fill: { fgColor: { rgb: bgRgb } },
          alignment: { vertical: 'center' },
          border: thinBorder
        }

        // 按列细化对齐与强调
        if (C === 0 || C === 1 || C === 2 || C === 10) {
          // 序号, 品类, 状态, 单位
          cellStyle.alignment.horizontal = 'center'
        } else if (C === 3 || C === 8) {
          // 标段, 物料描述 (加粗)
          cellStyle.alignment.horizontal = 'left'
          cellStyle.font.bold = true
        } else if (C === 4 || C === 5 || C === 6 || C === 11 || C === 14 || C === 15 || C === 17 || C === 18 || C === 20 || C === 21) {
          // 单号, 车次, 车牌, 时间, 人员, 电话
          cellStyle.alignment.horizontal = 'center'
          if (C === 6) cellStyle.font.bold = true
        } else if (C === 9) {
          // 发货数量 (居右加粗深蓝)
          cellStyle.alignment.horizontal = 'right'
          cellStyle.font.bold = true
          cellStyle.font.color = { rgb: '1D4ED8' }
        } else if (C === 12) {
          // 在途时长延误标色
          cellStyle.alignment.horizontal = 'center'
          if (rData.is_severe_delay) {
            cellStyle.fill = { fgColor: { rgb: 'FEE2E2' } }
            cellStyle.font.color = { rgb: '991B1B' }
            cellStyle.font.bold = true
          } else if (rData.is_warning_delay) {
            cellStyle.fill = { fgColor: { rgb: 'FEF3C7' } }
            cellStyle.font.color = { rgb: '92400E' }
            cellStyle.font.bold = true
          }
        } else if (C === 13) {
          // 操作等待时长延误标色
          cellStyle.alignment.horizontal = 'center'
          if (rData.is_unconfirmed_severe) {
            cellStyle.fill = { fgColor: { rgb: 'FEE2E2' } }
            cellStyle.font.color = { rgb: '991B1B' }
            cellStyle.font.bold = true
          } else if (rData.is_unconfirmed_warning) {
            cellStyle.fill = { fgColor: { rgb: 'FEF3C7' } }
            cellStyle.font.color = { rgb: '92400E' }
            cellStyle.font.bold = true
          }
        } else {
          cellStyle.alignment.horizontal = 'left'
        }

        ws[cellRef].s = cellStyle
      }
    }
  }

  // 7. 输出标准 .xlsx 文件
  try {
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '全标段发货督办清单')
    XLSX.writeFile(wb, `全标段发货督办清单_${todayStr}.xlsx`)
    setActionMessage('success', '已成功导出全标段发货督办清单 Excel 表格（.xlsx 原生格式）！')
  } catch (error) {
    console.error('导出 Excel 失败:', error)
    setActionMessage('error', `导出 Excel 失败: ${error?.message || '未知错误'}`)
  }
}

function exportGovernanceExcel() {
  const rows = filteredGovernanceSections.value || []
  if (!rows.length) {
    alert('当前筛选条件下暂无标段履约督办数据可导出。')
    return
  }

  const exportTime = new Date().toLocaleString()
  const todayStr = getTodayString()

  // 1. 构建数据行（含大标题行、摘要行、表头行）
  const titleRow = ['各标段填报履约督办清单', ...Array(15).fill('')]
  const metaRow = [
    `导出时间：${exportTime}  |  管辖标段总数：${governanceSections.value.length} 个  |  全部闭环：${governanceSummary.value.all_completed_count || 0} 标段  |  待催办：${governanceSummary.value.pending_sections_count || 0} 标段  |  计划起始日：${governanceDates.value.plan_start_date || '—'}  |  消耗采集日：${governanceDates.value.usage_collection_date || '—'}`,
    ...Array(15).fill('')
  ]
  const headers = [
    '序号', '需求标段', '供暖辖区',
    '三日计划-报送状态', '三日计划-报送量(米)', '三日计划-填报时间/上次报送',
    '直管消耗-填报状态', '直管消耗-消耗量(米)', '直管消耗-损耗量(米)', '直管消耗-上次填报日',
    '管件使用-填报状态', '管件使用-使用量(件)', '管件使用-上次填报日',
    '在途物资-待到货(笔)', '在途物资-待接收(笔)', '在途物资-严重滞留(笔)'
  ]

  const dataRows = rows.map((sec, idx) => {
    // 计划
    const planStatus = sec.plan?.is_submitted ? '已报送' : '未报送'
    const planQty = sec.plan?.is_submitted ? sec.plan.total_qty : 0
    const planTimeOrLast = sec.plan?.is_submitted
      ? (sec.plan.submitted_at ? sec.plan.submitted_at.slice(11) : '今日已提交')
      : (sec.plan?.last_submitted_date ? `上次: ${sec.plan.last_submitted_date}` : '从未报送')

    // 直管消耗
    const pipeUsageStatus = sec.pipe_usage?.is_submitted ? '已填报' : '未填报'
    const pipeUsageQty = sec.pipe_usage?.is_submitted ? sec.pipe_usage.total_usage_qty : 0
    const pipeLossQty = sec.pipe_usage?.is_submitted ? sec.pipe_usage.total_loss_qty : 0
    const pipeLastDate = sec.pipe_usage?.is_submitted
      ? '今日已填'
      : (sec.pipe_usage?.last_submitted_date ? `上次: ${sec.pipe_usage.last_submitted_date}` : '从未填报')

    // 管件使用
    const fitUsageStatus = sec.fitting_usage?.is_submitted ? '已填报' : '未填报'
    const fitUsageQty = sec.fitting_usage?.is_submitted ? sec.fitting_usage.total_qty : 0
    const fitLastDate = sec.fitting_usage?.is_submitted
      ? '今日已填'
      : (sec.fitting_usage?.last_submitted_date ? `上次: ${sec.fitting_usage.last_submitted_date}` : '从未填报')

    // 在途物资
    const pendingArrival = sec.deliveries?.pending_arrival || 0
    const pendingReceive = sec.deliveries?.pending_receive || 0
    const severeDelay = sec.deliveries?.severe_delay || 0

    return [
      idx + 1,
      sec.section_1_name || sec.section_1_id,
      sec.region || '—',
      planStatus,
      planQty,
      planTimeOrLast,
      pipeUsageStatus,
      pipeUsageQty,
      pipeLossQty,
      pipeLastDate,
      fitUsageStatus,
      fitUsageQty,
      fitLastDate,
      pendingArrival,
      pendingReceive,
      severeDelay
    ]
  })

  const wsData = [titleRow, metaRow, headers, ...dataRows]
  const ws = XLSX.utils.aoa_to_sheet(wsData)

  // 2. 合并大标题与摘要栏
  ws['!merges'] = [
    { s: { r: 0, c: 0 }, e: { r: 0, c: 15 } },
    { s: { r: 1, c: 0 }, e: { r: 1, c: 15 } }
  ]

  // 3. 列宽自适应
  ws['!cols'] = [
    { wch: 6 },  // 序号
    { wch: 20 }, // 需求标段
    { wch: 14 }, // 供暖辖区
    { wch: 14 }, // 三日计划-报送状态
    { wch: 14 }, // 三日计划-报送量
    { wch: 20 }, // 三日计划-填报时间/上次报送
    { wch: 14 }, // 直管消耗-填报状态
    { wch: 14 }, // 直管消耗-消耗量
    { wch: 14 }, // 直管消耗-损耗量
    { wch: 18 }, // 直管消耗-上次填报日
    { wch: 14 }, // 管件使用-填报状态
    { wch: 14 }, // 管件使用-使用量
    { wch: 18 }, // 管件使用-上次填报日
    { wch: 14 }, // 在途物资-待到货
    { wch: 14 }, // 在途物资-待接收
    { wch: 16 }  // 在途物资-严重滞留
  ]

  // 4. 行高
  ws['!rows'] = [
    { hpx: 36 }, // 大标题
    { hpx: 24 }, // 摘要栏
    { hpx: 28 }, // 表头
  ]

  // 5. 边框统一样式
  const thinBorder = {
    top: { style: 'thin', color: { rgb: 'CBD5E1' } },
    bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
    left: { style: 'thin', color: { rgb: 'CBD5E1' } },
    right: { style: 'thin', color: { rgb: 'CBD5E1' } }
  }

  // 6. 遍历单元格赋予专业排版与延误标色
  const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:P4')
  for (let R = range.s.r; R <= range.e.r; ++R) {
    for (let C = range.s.c; C <= range.e.c; ++C) {
      const cellRef = XLSX.utils.encode_cell({ r: R, c: C })
      if (!ws[cellRef]) ws[cellRef] = { v: '', t: 's' }

      if (R === 0) {
        // 大标题行
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 15, bold: true, color: { rgb: '0F172A' } },
          fill: { fgColor: { rgb: 'F1F5F9' } },
          alignment: { horizontal: 'center', vertical: 'center' },
          border: thinBorder
        }
      } else if (R === 1) {
        // 摘要统计行
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 9.5, color: { rgb: '475569' } },
          fill: { fgColor: { rgb: 'F8FAFC' } },
          alignment: { horizontal: 'center', vertical: 'center' },
          border: thinBorder
        }
      } else if (R === 2) {
        // 深蓝表头行
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 10.5, bold: true, color: { rgb: 'FFFFFF' } },
          fill: { fgColor: { rgb: '2563EB' } },
          alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
          border: thinBorder
        }
      } else {
        // 数据行 (R >= 3, 对应 rows[R - 3])
        const dataIndex = R - 3
        const sec = rows[dataIndex] || {}
        const isZebra = dataIndex % 2 === 1
        const bgRgb = isZebra ? 'F8FAFC' : 'FFFFFF'

        const cellStyle = {
          font: { name: 'Microsoft YaHei', sz: 10, color: { rgb: '334155' } },
          fill: { fgColor: { rgb: bgRgb } },
          alignment: { vertical: 'center' },
          border: thinBorder
        }

        // 序号, 辖区, 时间等居中
        if (C === 0 || C === 2 || C === 5 || C === 9 || C === 12) {
          cellStyle.alignment.horizontal = 'center'
        } else if (C === 1) {
          // 需求标段 (居左加粗)
          cellStyle.alignment.horizontal = 'left'
          cellStyle.font.bold = true
        } else if (C === 3) {
          // 三日计划状态
          cellStyle.alignment.horizontal = 'center'
          if (sec.plan?.is_submitted) {
            cellStyle.fill = { fgColor: { rgb: 'ECFDF5' } }
            cellStyle.font.color = { rgb: '047857' }
            cellStyle.font.bold = true
          } else {
            cellStyle.fill = { fgColor: { rgb: 'FEF3C7' } }
            cellStyle.font.color = { rgb: '92400E' }
            cellStyle.font.bold = true
          }
        } else if (C === 4) {
          // 三日计划报送量 (居右深蓝)
          cellStyle.alignment.horizontal = 'right'
          cellStyle.font.bold = true
          cellStyle.font.color = { rgb: '1D4ED8' }
        } else if (C === 6) {
          // 直管消耗状态
          cellStyle.alignment.horizontal = 'center'
          if (sec.pipe_usage?.is_submitted) {
            cellStyle.fill = { fgColor: { rgb: 'ECFDF5' } }
            cellStyle.font.color = { rgb: '047857' }
            cellStyle.font.bold = true
          } else {
            cellStyle.fill = { fgColor: { rgb: 'FEF3C7' } }
            cellStyle.font.color = { rgb: '92400E' }
            cellStyle.font.bold = true
          }
        } else if (C === 7) {
          // 直管消耗量 (居右绿色)
          cellStyle.alignment.horizontal = 'right'
          cellStyle.font.bold = true
          cellStyle.font.color = { rgb: '059669' }
        } else if (C === 8) {
          // 直管损耗量 (居右橙色)
          cellStyle.alignment.horizontal = 'right'
          if (sec.pipe_usage?.total_loss_qty > 0) {
            cellStyle.font.color = { rgb: 'D97706' }
            cellStyle.font.bold = true
          }
        } else if (C === 10) {
          // 管件使用状态
          cellStyle.alignment.horizontal = 'center'
          if (sec.fitting_usage?.is_submitted) {
            cellStyle.fill = { fgColor: { rgb: 'ECFDF5' } }
            cellStyle.font.color = { rgb: '047857' }
            cellStyle.font.bold = true
          } else {
            cellStyle.fill = { fgColor: { rgb: 'FEF3C7' } }
            cellStyle.font.color = { rgb: '92400E' }
            cellStyle.font.bold = true
          }
        } else if (C === 11) {
          // 管件使用量 (居右紫色)
          cellStyle.alignment.horizontal = 'right'
          cellStyle.font.bold = true
          cellStyle.font.color = { rgb: '7C3AED' }
        } else if (C === 13 || C === 14) {
          // 待到货 / 待接收
          cellStyle.alignment.horizontal = 'center'
        } else if (C === 15) {
          // 严重滞留笔数
          cellStyle.alignment.horizontal = 'center'
          if (sec.deliveries?.severe_delay > 0) {
            cellStyle.fill = { fgColor: { rgb: 'FEE2E2' } }
            cellStyle.font.color = { rgb: '991B1B' }
            cellStyle.font.bold = true
          }
        }

        ws[cellRef].s = cellStyle
      }
    }
  }

  // 7. 输出标准 .xlsx 文件
  try {
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '各标段填报履约督办清单')
    XLSX.writeFile(wb, `各标段填报履约督办清单_${todayStr}.xlsx`)
    setActionMessage('success', '已成功导出各标段填报履约督办清单 Excel 表格（.xlsx 原生格式）！')
  } catch (error) {
    console.error('导出标段履约 Excel 失败:', error)
    setActionMessage('error', `导出 Excel 失败: ${error?.message || '未知错误'}`)
  }
}

// 新增差异备注弹窗与订单流转时光轴详情弹窗状态
const receiptRemarkModalVisible = ref(false)
const receiptRemarkModalData = ref({
  row: null,
  receivedQty: 0,
  limitQty: 0,
  remark: ''
})

function getGroupUnitLabel(group) {
  if (!group || !group.items || !group.items.length) return '件'
  return '件'
}

function getModalUnitLabel(modalData) {
  if (!modalData) return '件'
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
    cancelledAt: mainRow.cancelled_at || mainRow.cancel_at || mainRow.cancelledAt || input.cancel_at || input.cancelled_at || input.cancelAt || '',
    cancelReason: mainRow.cancel_reason || mainRow.cancelReason || input.cancel_reason || input.cancelReason || '',
    cancelBy: mainRow.cancelled_by || mainRow.cancel_by || mainRow.cancelBy || input.cancel_by || input.cancelled_by || input.cancelBy || '',
  }
  deliveryDetailModalVisible.value = true
}

function handleGoToUserDirectory(target) {
  if (!target || target === '—' || target === '供给端系统') return
  deliveryDetailModalVisible.value = false
  navigateToUserInDirectory(router, target, PROJECT_KEY)
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

function isItemArrived(item) {
  if (!item || item.status === 'cancelled') return false
  if (['arrived', 'pending_receive', 'construction_confirmed', 'received', 'pending_warehouse', 'warehouse_confirmed', 'completed'].includes(item.status)) {
    return true
  }
  if (item.arrived_confirm_at || item.arrived_at) {
    return true
  }
  return false
}

function getItemArrivedQty(item) {
  if (!isItemArrived(item)) return 0
  if (item.arrived_qty !== null && item.arrived_qty !== undefined && !isNaN(Number(item.arrived_qty))) {
    return Number(item.arrived_qty)
  }
  return Number(item.shipped_qty) || 0
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

    // 仅累加未作废的有效发运与到货数据
    if (item.status !== 'cancelled') {
      group.totalShippedQty += (Number(item.shipped_qty) || 0)
      if (isItemArrived(item)) {
        group.totalArrivedQty += getItemArrivedQty(item)
      }
    }
  }

  // 短板状态判定原则：若多条明细中有任何一条状态落后于其它条目，外层 group.status 展现该落后状态
  const statusRankMap = {
    'shipped': 0,
    'pending_arrival': 0,
    'arrived': 1,
    'pending_receive': 1,
    'construction_confirmed': 2,
    'received': 2,
    'pending_warehouse': 2,
    'warehouse_confirmed': 3,
    'completed': 3
  }

  const result = Array.from(map.values())
  const validGroups = []
  for (const group of result) {
    const activeItems = group.items.filter(item => (item.status || 'shipped') !== 'cancelled')
    if (!activeItems.length) {
      continue
    }
    group.items = activeItems
    group.hasCancelled = false
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
    validGroups.push(group)
  }

  return validGroups
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
      exclude_cancelled: true,
      limit: 300,
    })
    if (res && res.ok) {
      fittingRows.value = (res.items || [])
        .filter(it => it.status !== 'cancelled')
        .map(it => ({
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
  return fittingRows.value
    .filter(r => (r.status || 'shipped') !== 'cancelled')
    .reduce((sum, r) => sum + (Number(r.shipped_qty) || 0), 0)
})

const demandFittingBatches = computed(() => {
  const set = new Set(
    fittingRows.value
      .filter(r => (r.status || 'shipped') !== 'cancelled')
      .map(r => r.shipment_no || r.id)
  )
  return set.size
})

const demandFittingStandardQty = computed(() => {
  return fittingRows.value
    .filter(r => (r.status || 'shipped') !== 'cancelled' && isStandardFittingType(r.fitting_type))
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

// 表头排序状态 (点击升序 -> 点击降序 -> 点击重置)
const fittingSortState = reactive({
  key: '',
  order: 'asc', // 'asc' | 'desc'
})

function handleFittingSort(key) {
  if (fittingSortState.key === key) {
    if (fittingSortState.order === 'asc') {
      fittingSortState.order = 'desc'
    } else if (fittingSortState.order === 'desc') {
      fittingSortState.key = ''
      fittingSortState.order = 'asc'
    }
  } else {
    fittingSortState.key = key
    fittingSortState.order = 'asc'
  }
}

const sortedFittingBaselineRows = computed(() => {
  const list = [...filteredFittingBaselineRows.value]
  if (!fittingSortState.key) {
    return list
  }
  const { key, order } = fittingSortState
  const multiplier = order === 'asc' ? 1 : -1

  return list.sort((a, b) => {
    let valA = a[key]
    let valB = b[key]

    const isNullA = valA === null || valA === undefined || valA === ''
    const isNullB = valB === null || valB === undefined || valB === ''

    if (isNullA && isNullB) return 0
    if (isNullA) return 1
    if (isNullB) return -1

    if (typeof valA === 'number' && typeof valB === 'number') {
      return (valA - valB) * multiplier
    }

    const numA = Number(valA)
    const numB = Number(valB)
    if (!isNaN(numA) && !isNaN(numB) && typeof valA !== 'boolean' && typeof valB !== 'boolean') {
      return (numA - numB) * multiplier
    }

    return String(valA).localeCompare(String(valB), 'zh-CN', { numeric: true }) * multiplier
  })
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

function formatShortDateTime(value) {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return String(value).replace('T', ' ').slice(5, 16)
  }
  const pad = (part) => String(part).padStart(2, '0')
  return `${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`
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
  const rows = sortedFittingBaselineRows.value
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

// ----------------------------------------------------------------------
// 📦 管件现场动态库存与安装使用量填报响应式状态与业务逻辑
// ----------------------------------------------------------------------
const fittingUsageDate = ref(getTodayString())
const fittingInventorySummary = ref({
  total_types: 0,
  arrived_sum: 0,
  used_sum: 0,
  stock_sum: 0,
  overall_rate_pct: 0
})
const fittingInventoryItems = ref([])
const fittingInventoryLoading = ref(false)
const fittingInventoryError = ref('')

const fittingUsageCategoryFilter = ref('')
const fittingUsageKeyword = ref('')
const fittingUsageOnlyInStock = ref(true)

const fittingUsageForm = reactive({}) // { [key]: { qty: 0, remark: '' } }
const fittingUsageSubmitting = ref(false)

// 历史台账
const fittingUsageHistoryRows = ref([])
const fittingUsageHistoryLoading = ref(false)
const expandedUsageDates = ref(new Set())

function toggleUsageDateExpand(dateStr) {
  const nextSet = new Set(expandedUsageDates.value)
  if (nextSet.has(dateStr)) {
    nextSet.delete(dateStr)
  } else {
    nextSet.add(dateStr)
  }
  expandedUsageDates.value = nextSet
}

function isUsageDateExpanded(dateStr) {
  return expandedUsageDates.value.has(dateStr)
}

function expandAllUsageDates() {
  const nextSet = new Set()
  groupedFittingUsageHistory.value.forEach(g => nextSet.add(g.usage_date))
  expandedUsageDates.value = nextSet
}

function collapseAllUsageDates() {
  expandedUsageDates.value = new Set()
}

const groupedFittingUsageHistory = computed(() => {
  const groupsMap = {}
  const dateOrder = []
  
  fittingUsageHistoryRows.value.forEach(row => {
    const d = row.usage_date || '未知日期'
    if (!groupsMap[d]) {
      groupsMap[d] = {
        usage_date: d,
        items: [],
        total_types: 0,
        total_active_qty: 0,
        total_cancelled_qty: 0,
        filled_by_list: new Set(),
        latest_filled_at: '',
        has_cancelled: false,
        has_active: false
      }
      dateOrder.push(d)
    }
    const g = groupsMap[d]
    g.items.push(row)
    if (row.status === 'active') {
      g.total_active_qty += Number(row.usage_qty || 0)
      g.has_active = true
    } else {
      g.total_cancelled_qty += Number(row.usage_qty || 0)
      g.has_cancelled = true
    }
    if (row.filled_by) g.filled_by_list.add(row.filled_by)
    if (!g.latest_filled_at || (row.filled_at && row.filled_at > g.latest_filled_at)) {
      g.latest_filled_at = row.filled_at
    }
  })
  
  return dateOrder.map(d => {
    const g = groupsMap[d]
    g.total_types = g.items.length
    g.filled_by_str = Array.from(g.filled_by_list).join(', ') || '-'
    return g
  })
})

// --- 📋 保温管施工使用与损耗历史台账状态与操作 ---
const pipeUsageHistoryRows = ref([])
const pipeUsageHistoryLoading = ref(false)
const expandedPipeUsageDates = ref(new Set())

function togglePipeUsageDateExpand(dateStr) {
  const nextSet = new Set(expandedPipeUsageDates.value)
  if (nextSet.has(dateStr)) {
    nextSet.delete(dateStr)
  } else {
    nextSet.add(dateStr)
  }
  expandedPipeUsageDates.value = nextSet
}

function isPipeUsageDateExpanded(dateStr) {
  return expandedPipeUsageDates.value.has(dateStr)
}

function expandAllPipeUsageDates() {
  const nextSet = new Set()
  groupedPipeUsageHistory.value.forEach(g => nextSet.add(g.usage_date))
  expandedPipeUsageDates.value = nextSet
}

function collapseAllPipeUsageDates() {
  expandedPipeUsageDates.value = new Set()
}

const groupedPipeUsageHistory = computed(() => {
  const groupsMap = {}
  const dateOrder = []

  pipeUsageHistoryRows.value.forEach(row => {
    const d = row.usage_date || '未知日期'
    if (!groupsMap[d]) {
      groupsMap[d] = {
        usage_date: d,
        items: [],
        total_types: 0,
        total_usage_qty: 0,
        total_loss_qty: 0,
        total_sum_qty: 0,
        filled_by_list: new Set(),
        latest_filled_at: '',
      }
      dateOrder.push(d)
    }
    const g = groupsMap[d]
    g.items.push(row)
    g.total_usage_qty += Number(row.usage_qty || 0)
    g.total_loss_qty += Number(row.loss_qty || 0)
    g.total_sum_qty += Number(row.total_qty || (Number(row.usage_qty || 0) + Number(row.loss_qty || 0)))
    if (row.filled_by) g.filled_by_list.add(row.filled_by)
    if (!g.latest_filled_at || (row.filled_at && row.filled_at > g.latest_filled_at)) {
      g.latest_filled_at = row.filled_at
    }
  })

  return dateOrder.map(d => {
    const g = groupsMap[d]
    return {
      usage_date: g.usage_date,
      items: g.items,
      total_types: g.items.length,
      total_usage_qty: Math.round(g.total_usage_qty * 100) / 100,
      total_loss_qty: Math.round(g.total_loss_qty * 100) / 100,
      total_sum_qty: Math.round(g.total_sum_qty * 100) / 100,
      filled_by_str: Array.from(g.filled_by_list).join(', ') || '施工现场',
      latest_filled_at: g.latest_filled_at
    }
  })
})

async function loadPipeUsageHistory() {
  if (!selectedSection1Id.value) return
  pipeUsageHistoryLoading.value = true
  try {
    const res = await listTubePipeUsageHistory(PROJECT_KEY, { section_1_id: selectedSection1Id.value })
    if (res.ok) {
      pipeUsageHistoryRows.value = res.rows || []
    }
  } catch (err) {
    console.error('加载保温管使用台账失败', err)
  } finally {
    pipeUsageHistoryLoading.value = false
  }
}

function exportPipeUsageHistory() {
  const rows = pipeUsageHistoryRows.value
  if (!rows || !rows.length) return
  const currentSecName = section1Options.value.find(s => s.section_1_id === selectedSection1Id.value)?.section_1_name || selectedSection1Id.value

  const header = ['序号', '消耗采集日期', '标段名称', '保温管型号', '实际施工消耗(米)', '实际现场损耗(米)', '合计总米数(米)', '填报人', '填报时间', '备注']
  const dataRows = rows.map((r, idx) => [
    idx + 1,
    r.usage_date,
    currentSecName,
    r.pipe_model_name,
    r.usage_qty,
    r.loss_qty,
    r.total_qty,
    r.filled_by || '施工现场',
    r.filled_at || '',
    r.remark || ''
  ])

  const ws = XLSX.utils.aoa_to_sheet([header, ...dataRows])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '保温管使用台账')
  XLSX.writeFile(wb, `${currentSecName}_保温管施工消耗历史台账.xlsx`)
}

const hasSubmittedFittingUsageToday = computed(() => {
  if (!usageDate.value || !fittingUsageHistoryRows.value.length) return false
  return fittingUsageHistoryRows.value.some(
    row => row.usage_date === usageDate.value && row.status === 'active'
  )
})

// 撤回 Modal (仅限 Global_admin)
const showFittingUsageCancelModal = ref(false)
const selectedCancelUsageRow = ref(null)
const selectedCancelUsageGroup = ref(null)
const cancelUsageReason = ref('')
const cancelUsageSubmitting = ref(false)

// ✏️ 管理员单项编辑 Modal
const showFittingUsageItemEditModal = ref(false)
const selectedEditUsageItem = ref(null)
const editItemForm = reactive({
  usage_qty: 0,
  remark: '',
  status: 'active',
  cancel_reason: '',
  filled_by: '',
  usage_date: ''
})
const editItemSubmitting = ref(false)

// 📋 管理员整批编辑 Modal
const showFittingUsageBatchEditModal = ref(false)
const selectedEditUsageGroup = ref(null)
const editBatchForm = reactive({
  new_usage_date: '',
  filled_by: '',
  cancel_reason: '',
  items: []
})
const editBatchSubmitting = ref(false)

function getItemKey(item) {
  return `${item.fitting_type}__${item.model_spec}__${item.unit}`
}

function getFormItem(item) {
  const key = getItemKey(item)
  if (!fittingUsageForm[key]) {
    fittingUsageForm[key] = {
      qty: 0,
      remark: ''
    }
  }
  return fittingUsageForm[key]
}

const fittingInventoryCategories = computed(() => {
  const map = {}
  fittingInventoryItems.value.forEach(it => {
    const cat = it.fitting_type || '其他'
    map[cat] = (map[cat] || 0) + 1
  })
  return Object.keys(map).map(name => ({ name, count: map[name] }))
})

const filteredFittingInventoryItems = computed(() => {
  return fittingInventoryItems.value
})

const totalFilledItemsCount = computed(() => {
  return Object.values(fittingUsageForm).filter(v => Number(v?.qty || 0) > 0).length
})

const totalFilledQtySum = computed(() => {
  return Object.values(fittingUsageForm).reduce((sum, v) => sum + (Number(v?.qty || 0) > 0 ? Number(v.qty) : 0), 0)
})

function adjustFittingUsageQty(item, delta) {
  const formItem = getFormItem(item)
  let val = (formItem.qty || 0) + delta
  if (val < 0) val = 0
  if (val > item.stock_qty) val = item.stock_qty
  formItem.qty = val
}

function setFittingUsageMax(item) {
  const formItem = getFormItem(item)
  formItem.qty = item.stock_qty
}

function clearFittingUsageItem(item) {
  const formItem = getFormItem(item)
  formItem.qty = 0
}

function validateFittingUsageQty(item) {
  const formItem = getFormItem(item)
  if (formItem.qty < 0 || isNaN(formItem.qty)) {
    formItem.qty = 0
  } else if (formItem.qty > item.stock_qty) {
    formItem.qty = item.stock_qty
  } else {
    formItem.qty = Math.floor(formItem.qty)
  }
}

function resetFittingUsageForm() {
  Object.keys(fittingUsageForm).forEach(k => delete fittingUsageForm[k])
}

async function loadFittingInventorySummary() {
  if (!selectedSection1Id.value) return
  fittingInventoryLoading.value = true
  fittingInventoryError.value = ''
  try {
    const res = await getTubeFittingInventorySummary(PROJECT_KEY, selectedSection1Id.value)
    if (res.ok) {
      fittingInventorySummary.value = res.summary || {}
      fittingInventoryItems.value = res.items || []
    }
  } catch (err) {
    fittingInventoryError.value = err?.message || '加载管件现场库存失败'
  } finally {
    fittingInventoryLoading.value = false
  }
}

async function loadFittingUsageHistory() {
  if (!selectedSection1Id.value) return
  fittingUsageHistoryLoading.value = true
  try {
    const res = await listTubeFittingUsageHistory(PROJECT_KEY, { section_1_id: selectedSection1Id.value })
    if (res.ok) {
      fittingUsageHistoryRows.value = res.rows || []
      // 默认全部折叠，不自动加入任何展开项
    }
  } catch (err) {
    console.error('加载管件使用台账失败', err)
  } finally {
    fittingUsageHistoryLoading.value = false
  }
}

function refreshFittingUsageData() {
  loadFittingInventorySummary()
  loadFittingUsageHistory()
}

async function handleFittingUsageSubmit() {
  const itemsToSubmit = []
  for (const item of fittingInventoryItems.value) {
    const key = getItemKey(item)
    const formVal = fittingUsageForm[key]
    const qty = Number(formVal?.qty || 0)
    if (qty > 0) {
      itemsToSubmit.push({
        fitting_type: item.fitting_type,
        model_spec: item.model_spec,
        unit: item.unit || '个',
        usage_qty: qty,
        remark: formVal?.remark || ''
      })
    }
  }

  if (!itemsToSubmit.length) {
    alert('未填报任何大于 0 的管件安装数量')
    return
  }

  const confirmMsg = `确定在【${usageDate.value}】为标段【${currentSection1Name.value}】提交 ${itemsToSubmit.length} 种管件共计 ${totalFilledQtySum.value} 件安装使用记录吗？`
  if (!confirm(confirmMsg)) return

  fittingUsageSubmitting.value = true
  try {
    const payload = {
      section_1_id: selectedSection1Id.value,
      usage_date: usageDate.value,
      items: itemsToSubmit
    }
    const res = await submitTubeFittingUsage(PROJECT_KEY, payload)
    if (res.ok) {
      setActionMessage('success', res.message || '提交管件安装记录成功')
      resetFittingUsageForm()
      refreshFittingUsageData()
    }
  } catch (err) {
    alert(err?.message || '提交失败')
  } finally {
    fittingUsageSubmitting.value = false
  }
}

function canCancelUsage(row) {
  if (!row) return false
  // 严格仅保留 Global_admin 的记录编辑/作废权限，普通填报用户不可撤回
  return isGlobalAdmin.value
}

function canCancelUsageGroup(group) {
  if (!group || !group.has_active) return false
  return isGlobalAdmin.value
}

function openCancelUsageModal(row) {
  selectedCancelUsageRow.value = row
  selectedCancelUsageGroup.value = null
  cancelUsageReason.value = ''
  showFittingUsageCancelModal.value = true
}

function openCancelUsageGroupModal(group) {
  selectedCancelUsageGroup.value = group
  selectedCancelUsageRow.value = null
  cancelUsageReason.value = ''
  showFittingUsageCancelModal.value = true
}

async function handleConfirmCancelUsage() {
  if (!cancelUsageReason.value.trim()) return
  cancelUsageSubmitting.value = true
  try {
    if (selectedCancelUsageRow.value) {
      const res = await cancelTubeFittingUsage(PROJECT_KEY, {
        usage_id: selectedCancelUsageRow.value.id,
        cancel_reason: cancelUsageReason.value.trim()
      })
      if (res.ok) {
        setActionMessage('success', res.message || '管理员作废成功，库存已恢复')
      }
    } else if (selectedCancelUsageGroup.value) {
      const activeItems = (selectedCancelUsageGroup.value.items || []).filter(it => it.status === 'active')
      let successCount = 0
      for (const item of activeItems) {
        await cancelTubeFittingUsage(PROJECT_KEY, {
          usage_id: item.id,
          cancel_reason: cancelUsageReason.value.trim()
        })
        successCount++
      }
      setActionMessage('success', `管理员已成功作废【${selectedCancelUsageGroup.value.usage_date}】共 ${successCount} 笔安装记录，库存已全部退回，填报通道已重新解锁！`)
    }
    showFittingUsageCancelModal.value = false
    selectedCancelUsageRow.value = null
    selectedCancelUsageGroup.value = null
    refreshFittingUsageData()
  } catch (err) {
    alert(err?.message || '作废操作失败')
  } finally {
    cancelUsageSubmitting.value = false
  }
}

// ✏️ 管理员单项编辑处理
function openEditUsageItemModal(row) {
  if (!row) return
  selectedEditUsageItem.value = row
  editItemForm.usage_qty = Number(row.usage_qty || 0)
  editItemForm.remark = String(row.remark || '')
  editItemForm.status = String(row.status || 'active')
  editItemForm.cancel_reason = String(row.cancel_reason || '')
  editItemForm.filled_by = String(row.filled_by || '')
  editItemForm.usage_date = String(row.usage_date || usageDate.value || '')
  showFittingUsageItemEditModal.value = true
}

async function handleConfirmUpdateUsageItem() {
  if (!selectedEditUsageItem.value) return
  if (editItemForm.status === 'active' && editItemForm.usage_qty <= 0) {
    alert('有效记录的安装数量必须大于 0')
    return
  }
  if (editItemForm.status === 'cancelled' && !editItemForm.cancel_reason.trim()) {
    alert('作废记录必须填写作废原因说明')
    return
  }

  editItemSubmitting.value = true
  try {
    const res = await updateTubeFittingUsageItem(PROJECT_KEY, {
      usage_id: selectedEditUsageItem.value.id,
      usage_qty: editItemForm.usage_qty,
      remark: editItemForm.remark,
      status: editItemForm.status,
      cancel_reason: editItemForm.cancel_reason,
      filled_by: editItemForm.filled_by,
      usage_date: editItemForm.usage_date
    })
    if (res.ok) {
      setActionMessage('success', res.message || '管理员成功更新安装记录')
      showFittingUsageItemEditModal.value = false
      selectedEditUsageItem.value = null
      refreshFittingUsageData()
    }
  } catch (err) {
    alert(err?.message || '更新记录失败')
  } finally {
    editItemSubmitting.value = false
  }
}

// 📋 管理员批量整日编辑处理
function openEditUsageBatchModal(group) {
  if (!group) return
  selectedEditUsageGroup.value = group
  editBatchForm.new_usage_date = group.usage_date || ''
  editBatchForm.filled_by = ''
  editBatchForm.cancel_reason = ''
  editBatchForm.items = (group.items || []).map(it => ({
    id: it.id,
    fitting_type: it.fitting_type,
    model_spec: it.model_spec,
    unit: it.unit || '件',
    usage_qty: Number(it.usage_qty || 0),
    remark: String(it.remark || ''),
    status: String(it.status || 'active'),
    cancel_reason: String(it.cancel_reason || '')
  }))
  showFittingUsageBatchEditModal.value = true
}

async function handleConfirmUpdateUsageBatch() {
  if (!selectedEditUsageGroup.value || !selectedSection1Id.value) return
  editBatchSubmitting.value = true
  try {
    const res = await updateTubeFittingUsageBatch(PROJECT_KEY, {
      section_1_id: selectedSection1Id.value,
      usage_date: selectedEditUsageGroup.value.usage_date,
      new_usage_date: editBatchForm.new_usage_date || selectedEditUsageGroup.value.usage_date,
      filled_by: editBatchForm.filled_by || undefined,
      items: editBatchForm.items.map(it => ({
        id: it.id,
        usage_qty: Number(it.usage_qty || 0),
        remark: it.remark,
        status: it.status,
        cancel_reason: it.cancel_reason
      })),
      cancel_reason: editBatchForm.cancel_reason
    })
    if (res.ok) {
      setActionMessage('success', res.message || '管理员成功批量更新整日安装批次')
      showFittingUsageBatchEditModal.value = false
      selectedEditUsageGroup.value = null
      refreshFittingUsageData()
    }
  } catch (err) {
    alert(err?.message || '批量更新失败')
  } finally {
    editBatchSubmitting.value = false
  }
}

function formatUsageTime(isoStr) {
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    if (Number.isNaN(d.getTime())) {
      const s = String(isoStr).replace('T', ' ')
      return s.slice(5, 16) || s
    }
    // 使用东八区（Asia/Shanghai）标准时区格式化
    const formatter = new Intl.DateTimeFormat('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
    const parts = formatter.formatToParts(d)
    const getPart = (type) => parts.find(p => p.type === type)?.value || '00'
    return `${getPart('month')}-${getPart('day')} ${getPart('hour')}:${getPart('minute')}`
  } catch {
    return String(isoStr).replace('T', ' ').slice(5, 16)
  }
}

function exportFittingUsageHistory() {
  const rows = fittingUsageHistoryRows.value
  const groups = groupedFittingUsageHistory.value
  if (!rows.length) {
    alert('暂无管件使用台账数据可导出')
    return
  }

  const wb = XLSX.utils.book_new()

  // Sheet 1: 每日安装汇总
  const summaryHeaders = ['序号', '施工日期', '填报物料种数', '有效安装总量(件)', '填报人', '最新填报时间', '状态']
  const summaryData = groups.map((g, idx) => [
    idx + 1,
    g.usage_date,
    g.total_types,
    g.total_active_qty,
    g.filled_by_str,
    g.latest_filled_at,
    !g.has_cancelled ? '已记账' : (g.has_active ? '含作废' : '全作废')
  ])
  const wsSummary = XLSX.utils.aoa_to_sheet([summaryHeaders, ...summaryData])
  XLSX.utils.book_append_sheet(wb, wsSummary, '每日安装汇总')

  // Sheet 2: 全量安装流水明细
  const detailHeaders = ['序号', '施工日期', '名称', '型号规格', '安装数量', '计量单位', '备注', '记录状态', '填报人', '填报时间', '撤回人', '撤回原因']
  const detailData = rows.map((r, idx) => [
    idx + 1,
    r.usage_date,
    r.fitting_type,
    r.model_spec,
    r.usage_qty,
    r.unit,
    r.remark || '',
    r.status === 'active' ? '已记账' : '已作废',
    r.filled_by,
    r.filled_at,
    r.cancelled_by || '',
    r.cancel_reason || ''
  ])
  const wsDetail = XLSX.utils.aoa_to_sheet([detailHeaders, ...detailData])
  XLSX.utils.book_append_sheet(wb, wsDetail, '安装流水明细')

  XLSX.writeFile(wb, `${currentSection1Name.value}_管件安装使用台账_${getTodayString()}.xlsx`)
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
  resetFittingUsageForm()
  await Promise.all([
    loadDemandInventoryOverview(),
    loadBaseline(),
    loadFittingBaseline(),
    loadPlanMatrix(),
    loadUsageSheet(),
    loadPipeUsageHistory(),
    loadLogisticsRecords(),
    loadAllPendingLogistics(),
    loadPendingDeliveriesSummary(false),
    handleFittingQuery(),
    refreshFittingUsageData()
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
    await Promise.all([loadUsageSheet(), loadDemandInventoryOverview(), loadPipeUsageHistory()])
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
    await Promise.all([loadUsageSheet(), loadPipeUsageHistory()])
  } catch (err) {
    setActionMessage('error', err?.message || '保存消耗采集日期失败')
  }
}

watch(usageDate, (value, oldValue) => {
  if (!selectedSection1Id.value || !value || value === oldValue) {
    return
  }
  Promise.all([loadUsageSheet(), loadDemandInventoryOverview(), loadPipeUsageHistory()])
})

onMounted(async () => {
  nowTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, 60000)
  document.addEventListener('click', closeFittingDropdown)
  window.addEventListener('resize', handleResizeOverviewChart)
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
    activeTab.value = lastPipeTab.value || 'overview'
  } else if (category === 'fitting') {
    activeTab.value = lastFittingTab.value || 'fitting'
  } else if (category === 'tools') {
    activeTab.value = 'ocr_tool'
  }
  syncTabStateToUrl(activeCategory.value, activeTab.value)
  refreshCurrentTabData(activeTab.value)
}

function handleTabClick(targetTab) {
  if (['overview', 'usage', 'plan', 'logistics', 'baseline'].includes(targetTab)) {
    activeCategory.value = 'pipe'
    lastPipeTab.value = targetTab
  } else if (['fitting', 'fitting_usage', 'fitting_baseline'].includes(targetTab)) {
    activeCategory.value = 'fitting'
    lastFittingTab.value = targetTab
  } else if (['ocr_tool'].includes(targetTab)) {
    activeCategory.value = 'tools'
  }

  if (activeTab.value === targetTab) {
    syncTabStateToUrl(activeCategory.value, targetTab)
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
  syncTabStateToUrl(activeCategory.value, targetTab)
  refreshCurrentTabData(targetTab)
}

function refreshCurrentTabData(tab) {
  if (tab === 'overview') {
    loadDemandInventoryOverview()
  } else if (tab === 'plan') {
    loadPlanMatrix()
  } else if (tab === 'usage') {
    loadUsageSheet()
    loadPipeUsageHistory()
  } else if (tab === 'baseline') {
    loadBaseline()
  } else if (tab === 'logistics') {
    loadLogisticsRecords()
  } else if (tab === 'fitting') {
    handleFittingQuery()
  } else if (tab === 'fitting_usage') {
    refreshFittingUsageData()
  } else if (tab === 'fitting_baseline') {
    loadFittingBaseline()
  }
}

onBeforeUnmount(() => {
  document.removeEventListener('click', closeFittingDropdown)
  window.removeEventListener('resize', handleResizeOverviewChart)
  if (overviewChartInstance) {
    overviewChartInstance.dispose()
    overviewChartInstance = null
  }
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

  /* 📱 移动端一级与二级导航栏排版优化 */
  .category-segment-wrapper {
    padding: 3px !important;
    border-radius: 10px !important;
  }

  .category-segment-bar {
    gap: 4px !important;
  }

  .category-segment-btn {
    padding: 7px 4px !important;
    font-size: 13px !important;
    gap: 4px !important;
  }

  .category-segment-btn .cat-label {
    font-size: 12.5px !important;
    font-weight: 600 !important;
  }

  .tube-tabs-header-wrap {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch !important;
    padding: 3px !important;
    border-radius: 10px !important;
  }

  .tube-tabs-header {
    display: flex !important;
    flex-wrap: nowrap !important;
    width: max-content !important;
    min-width: 100% !important;
    gap: 4px !important;
  }

  .tube-tabs-header button {
    flex: 0 0 auto !important;
    white-space: nowrap !important;
    padding: 8px 12px !important;
    font-size: 12.5px !important;
    gap: 4px !important;
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

/* 🧭 一体化复合双层导航容器 (Unified Compound Navigation Group) */
.nav-composite-group {
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  width: 100% !important;
  margin-bottom: 2px !important;
}

/* 🔹 一级物料大类分段控制器 (Segmented Category Bar) */
.category-segment-wrapper {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  margin: 0 !important;
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
  border-radius: 8px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #64748b !important;
  cursor: pointer !important;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
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
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.12), 0 1px 2px rgba(0, 0, 0, 0.04) !important;
}

.category-segment-btn .cat-icon {
  font-size: 14.5px;
  line-height: 1;
}

.category-segment-btn .cat-label {
  font-size: 13.5px;
  letter-spacing: 0.2px;
}

.category-segment-btn .cat-count {
  font-size: 11px;
  font-weight: 500;
  padding: 1.5px 6px;
  border-radius: 20px;
  background: #e2e8f0;
  color: #64748b;
  transition: all 0.22s ease;
}

.category-segment-btn.active .cat-count {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

/* 🏷️ 二级选项卡导航 (Responsive Sub-Tabs Header) */
.tube-tabs-header-wrap {
  background: rgba(241, 245, 249, 0.8) !important;
  border-radius: 12px !important;
  padding: 4px !important;
  margin: 0 !important;
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
  padding: 11px 16px !important;
  border-radius: 8px !important;
  font-size: 13.5px !important;
  font-weight: 600 !important;
  color: #475569 !important;
  cursor: pointer !important;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
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
  box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.06), 0 1px 3px -1px rgba(0, 0, 0, 0.04) !important;
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

/* 📊 表格可点击排序表头样式 (Click-to-Sort Headers) */
.sortable-th {
  cursor: pointer !important;
  user-select: none !important;
  transition: all 0.18s ease !important;
  position: relative;
  white-space: nowrap !important;
}

.sortable-th:hover {
  background: #f1f5f9 !important;
  color: #1d4ed8 !important;
}

.sortable-th.sorted {
  background: #eff6ff !important;
  color: #1d4ed8 !important;
  font-weight: 700 !important;
  border-bottom: 2px solid #2563eb !important;
}

.sort-icon {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  color: #94a3b8;
  vertical-align: middle;
  transition: color 0.15s ease;
}

.sortable-th.sorted .sort-icon {
  color: #2563eb;
  font-weight: bold;
}

.sortable-th:hover .sort-icon {
  color: #3b82f6;
}

/* 📜 限制约20行高度并带粘性吸顶表头与独立滚动条的表格容器 */
.fitting-baseline-table-wrap {
  max-height: 680px !important;
  overflow-y: auto !important;
  overflow-x: auto !important;
  position: relative !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 10px !important;
  background: #ffffff !important;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.02) !important;
}

.fitting-baseline-table-wrap table {
  margin: 0 !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  width: 100% !important;
}

.fitting-baseline-table-wrap thead th {
  position: sticky !important;
  top: 0 !important;
  z-index: 12 !important;
  background: #f8fafc !important;
  border-bottom: 2px solid #cbd5e1 !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}

/* 📦 管件现场库存微看板与滑块填报控件样式 */
.fitting-usage-summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

@media (max-width: 1180px) {
  .fitting-usage-summary-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .fitting-usage-summary-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  .fitting-usage-summary-grid .summary-metric-card:nth-child(5) {
    grid-column: span 2;
  }
}

.summary-metric-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
  position: relative;
  overflow: hidden;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
}

.summary-metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.summary-metric-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3.5px;
}

.summary-metric-card.card-blue {
  background: linear-gradient(145deg, #f0f9ff 0%, #ffffff 100%);
  border-color: #e0f2fe;
}
.summary-metric-card.card-blue::before {
  background: #0284c7;
}

.summary-metric-card.card-indigo {
  background: linear-gradient(145deg, #eef2ff 0%, #ffffff 100%);
  border-color: #e0e7ff;
}
.summary-metric-card.card-indigo::before {
  background: #4f46e5;
}

.summary-metric-card.card-emerald {
  background: linear-gradient(145deg, #ecfdf5 0%, #ffffff 100%);
  border-color: #d1fae5;
}
.summary-metric-card.card-emerald::before {
  background: #059669;
}

.summary-metric-card.card-amber {
  background: linear-gradient(145deg, #fffbeb 0%, #ffffff 100%);
  border-color: #fef3c7;
}
.summary-metric-card.card-amber::before {
  background: #d97706;
}

.summary-metric-card.card-purple {
  background: linear-gradient(145deg, #faf5ff 0%, #ffffff 100%);
  border-color: #f3e8ff;
}
.summary-metric-card.card-purple::before {
  background: #7c3aed;
}

.metric-header-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.metric-icon {
  font-size: 14px;
}

.summary-metric-card .metric-label {
  font-size: 12px;
  color: #475569;
  font-weight: 600;
}

.metric-body-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.summary-metric-card .metric-val {
  font-size: 20px;
  font-weight: 700;
  line-height: 1.1;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}

.metric-unit {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.text-blue { color: #0284c7; }
.text-indigo { color: #4f46e5; }
.text-emerald { color: #059669; }
.text-amber { color: #d97706; }
.text-purple { color: #7c3aed; }

.micro-progress-bar {
  width: 100%;
  height: 5px;
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
  margin-top: 2px;
}

.micro-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #7c3aed 0%, #a855f7 100%);
  border-radius: 99px;
  transition: width 0.3s ease;
}

.pill-filter-btn {
  height: 28px;
  padding: 0 10px;
  font-size: 12px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  border-radius: 99px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.pill-filter-btn:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.pill-filter-btn.active {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
  font-weight: 600;
}

.fitting-type-badge {
  display: inline-block;
  font-size: 11.5px;
  padding: 2px 7px;
  border-radius: 6px;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
}

.stock-progress-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.stock-stat-text {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  color: #475569;
}

.stock-progress-bar-bg {
  width: 100%;
  height: 6px;
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.stock-progress-bar-used {
  height: 100%;
  background: linear-gradient(90deg, #10b981 0%, #059669 100%);
  border-radius: 99px;
  transition: width 0.2s ease;
}

.usage-input-control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stepper-wrap {
  display: inline-flex;
  align-items: center;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.step-btn {
  width: 26px;
  height: 28px;
  border: none;
  background: #f8fafc;
  color: #334155;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.15s ease;
}

.step-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #0f172a;
}

.step-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.qty-input {
  width: 44px;
  height: 28px;
  border: none;
  text-align: center;
  font-weight: 700;
  color: #2563eb;
  font-size: 13px;
  outline: none;
}

.usage-slider {
  width: 80px;
  height: 5px;
  cursor: pointer;
  accent-color: #2563eb;
}

.quick-max-btn {
  font-size: 11px;
  padding: 2px 6px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
}

.quick-max-btn:hover {
  background: #dbeafe;
}

.quick-clear-btn {
  font-size: 11px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fee2e2;
  border: none;
  color: #dc2626;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.text-input-compact {
  width: 100%;
  height: 28px;
  padding: 0 6px;
  font-size: 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  outline: none;
  box-sizing: border-box;
}

.row-has-input {
  background: #f0fdf4 !important;
}

.btn-cancel-usage {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #fecaca;
  background: #fff5f5;
  color: #ef4444;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-cancel-usage:hover {
  background: #fee2e2;
  border-color: #f87171;
}

/* 📅 历史台账按日期折叠展开样式 */
.history-group-header-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
  user-select: none;
}

.history-group-header-row:hover {
  background-color: #f1f5f9 !important;
}

.history-group-header-row.is-expanded {
  background-color: #eff6ff !important;
  border-bottom: 1px solid #bfdbfe !important;
}

.group-expand-caret {
  display: inline-block;
  width: 16px;
  font-size: 10px;
  color: #64748b;
  margin-right: 4px;
  transition: transform 0.15s ease;
}

.pill-badge-subtle {
  display: inline-block;
  font-size: 11.5px;
  padding: 1px 8px;
  border-radius: 99px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-weight: 500;
}

.btn-toggle-expand {
  font-size: 11.5px;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #2563eb;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s ease;
}

.btn-toggle-expand:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

.detail-nested-table {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.detail-nested-table th {
  font-weight: 600;
  font-size: 11.5px;
  border-bottom: 1px solid #e2e8f0;
}

.detail-nested-table td {
  border-bottom: 1px solid #f1f5f9;
}

/* 🔧 管件发货记录卡片与表头超紧凑清爽流式排版（0滚动条，自适应） */
.fitting-card-header {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  padding: 8px 12px !important;
  background: #f8fafc !important;
  cursor: pointer !important;
  user-select: none !important;
  border-bottom: 1px solid #e2e8f0 !important;
  flex-wrap: nowrap !important;
  gap: 10px !important;
  transition: background-color 0.15s ease !important;
  overflow: hidden !important;
}

.fitting-card-header:hover {
  background: #f1f5f9 !important;
}

.card-left-stream {
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  flex: 1 !important;
  min-width: 0 !important;
  white-space: nowrap !important;
}

.expand-caret-icon {
  display: inline-block;
  width: 14px;
  font-size: 11px;
  color: #6366f1;
  font-weight: bold;
  text-align: center;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.shipment-code-badge {
  font-family: monospace;
  font-size: 12px;
  font-weight: 700;
  color: #4338ca;
  background: #e0e7ff;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid #c7d2fe;
  flex-shrink: 0;
}

.plate-badge {
  flex-shrink: 0;
  padding: 1px 6px !important;
  font-size: 11.5px !important;
}

.entity-pill-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11.5px;
  color: #334155;
  max-width: 140px;
  flex-shrink: 1;
  overflow: hidden;
  box-sizing: border-box;
}

.entity-pill-badge .entity-name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.shipped-time-text {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
  flex-shrink: 0;
}

.card-right-stream {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  flex-shrink: 0 !important;
  white-space: nowrap !important;
}

.qty-summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 1px 8px;
  border-radius: 99px;
  font-size: 11.5px;
}

.qty-types-lbl {
  color: #64748b;
  font-size: 11px;
}

.qty-divider {
  color: #cbd5e1;
  font-size: 10px;
  margin: 0 1px;
}

.qty-stat-item {
  font-size: 11.5px;
}

.qty-stat-item strong {
  font-size: 12px;
}

.qty-unit-lbl {
  color: #64748b;
  font-size: 11px;
}

.status-badge-container {
  display: flex;
  align-items: center;
}

.action-btn-container {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ==========================================================================
   📱 移动端管件库存与使用量专属卡片流样式 (Mobile Touch Cards View)
   ========================================================================== */
.desktop-fitting-table-view {
  display: block !important;
}

.mobile-fitting-cards-view {
  display: none !important;
}

@media (max-width: 768px) {
  .desktop-fitting-table-view {
    display: none !important;
  }

  .mobile-fitting-cards-view {
    display: flex !important;
    flex-direction: column !important;
    gap: 12px !important;
    margin-top: 10px !important;
  }

  /* 📦 移动端型号填报单卡片 */
  .fitting-mobile-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 14px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    display: flex;
    flex-direction: column;
    gap: 10px;
    position: relative;
    overflow: hidden;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
    box-sizing: border-box;
  }

  .fitting-mobile-card::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: #cbd5e1;
    transition: background 0.2s ease;
  }

  /* 🟢 已填写数量的高亮活跃卡片 */
  .fitting-mobile-card.card-has-input {
    background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
    border-color: #86efac;
    box-shadow: 0 4px 14px rgba(34, 197, 94, 0.12);
  }

  .fitting-mobile-card.card-has-input::before {
    background: #16a34a;
  }

  /* 🔴 缺货/无库存卡片 */
  .fitting-mobile-card.card-out-of-stock {
    background: #f8fafc;
    border-color: #e2e8f0;
    opacity: 0.88;
  }

  .fitting-mobile-card.card-out-of-stock::before {
    background: #ef4444;
  }

  /* 卡片头部 */
  .fmc-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
  }

  .fmc-title-left {
    display: flex;
    align-items: center;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .fmc-idx {
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    background: #f1f5f9;
    padding: 1px 6px;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .fmc-spec {
    font-size: 14.5px;
    font-weight: 700;
    color: #0f172a;
    word-break: break-all;
    line-height: 1.35;
  }

  .fmc-header-right {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .fmc-filled-badge {
    font-size: 11.5px;
    font-weight: 700;
    color: #15803d;
    background: #dcfce7;
    border: 1px solid #bbf7d0;
    padding: 2px 7px;
    border-radius: 6px;
    box-shadow: 0 1px 2px rgba(22, 163, 74, 0.08);
  }

  .fmc-unit-chip {
    font-size: 11px;
    color: #64748b;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    padding: 2px 7px;
    border-radius: 6px;
    font-weight: 600;
  }

  /* 库存指示区 */
  .fmc-stock-panel {
    background: #f8fafc;
    border: 1px solid #edf2f7;
    border-radius: 10px;
    padding: 8px 10px;
  }

  .fmc-stock-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .fmc-stock-box {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .fmc-stock-box.highlight-box {
    border-left: 2px solid #e2e8f0;
    padding-left: 10px;
  }

  .fmc-stock-box.highlight-box.box-blue {
    border-left-color: #3b82f6;
  }

  .fmc-stock-box.highlight-box.box-danger {
    border-left-color: #ef4444;
  }

  .fmc-stock-lbl {
    font-size: 11px;
    color: #64748b;
    font-weight: 500;
  }

  .fmc-stock-val {
    font-size: 15px;
    font-family: monospace;
    font-weight: 700;
    display: flex;
    align-items: baseline;
    gap: 3px;
  }

  .fmc-stock-val .unit {
    font-size: 11px;
    color: #94a3b8;
    font-weight: normal;
  }

  .fmc-stock-val.text-danger {
    color: #dc2626;
  }

  /* 填报控制区 */
  .fmc-action-panel {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .fmc-control-wrapper {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .fmc-action-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .fmc-action-heading {
    font-size: 12.5px;
    font-weight: 600;
    color: #334155;
  }

  .fmc-quick-btn-group {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .fmc-btn-quick {
    font-size: 11.5px;
    padding: 3px 9px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.15s ease;
  }

  .fmc-btn-quick.max {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1d4ed8;
  }

  .fmc-btn-quick.max:active {
    background: #dbeafe;
  }

  .fmc-btn-quick.clear {
    background: #fee2e2;
    border: 1px solid #fecaca;
    color: #dc2626;
  }

  .fmc-btn-quick:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* 大触控步进器与滑块行 */
  .fmc-stepper-control-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .fmc-touch-stepper {
    display: inline-flex;
    align-items: center;
    border: 1.5px solid #cbd5e1;
    border-radius: 8px;
    overflow: hidden;
    background: #ffffff;
    flex-shrink: 0;
  }

  .fmc-touch-btn {
    width: 42px;
    height: 40px;
    border: none;
    background: #f8fafc;
    color: #1e293b;
    font-size: 20px;
    font-weight: bold;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    touch-action: manipulation;
    user-select: none;
    transition: background 0.15s ease;
  }

  .fmc-touch-btn:hover:not(:disabled) {
    background: #e2e8f0;
  }

  .fmc-touch-btn:active:not(:disabled) {
    background: #cbd5e1;
  }

  .fmc-touch-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .fmc-touch-input {
    width: 56px;
    height: 40px;
    border: none;
    border-left: 1px solid #e2e8f0;
    border-right: 1px solid #e2e8f0;
    text-align: center;
    font-size: 16px;
    font-weight: 700;
    color: #2563eb;
    outline: none;
    background: #ffffff;
    box-sizing: border-box;
  }

  .fmc-touch-slider-wrap {
    flex: 1;
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .fmc-touch-slider {
    width: 100%;
    height: 8px;
    cursor: pointer;
    accent-color: #2563eb;
    border-radius: 99px;
  }

  /* 备注输入框 */
  .fmc-remark-row {
    width: 100%;
  }

  .fmc-touch-remark {
    width: 100%;
    height: 38px;
    padding: 0 12px;
    font-size: 13px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    outline: none;
    box-sizing: border-box;
    background: #ffffff;
    transition: border-color 0.15s ease;
  }

  .fmc-touch-remark:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
  }

  .fmc-no-stock-tip {
    background: #fef2f2;
    border: 1px solid #fee2e2;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ef4444;
    font-size: 12px;
    font-weight: 500;
    text-align: center;
  }

  /* 移动端底部提交栏优化 */
  .usage-submit-action-bar {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
    padding: 12px 14px !important;
    box-sizing: border-box !important;
    max-width: 100% !important;
    overflow: hidden !important;
  }

  .usage-submit-action-bar .usage-submit-info {
    font-size: 13px !important;
    line-height: 1.5 !important;
    word-break: break-word !important;
  }

  .usage-submit-action-bar .usage-submit-btns {
    display: grid !important;
    grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) !important;
    gap: 8px !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }

  .usage-submit-action-bar .usage-submit-btns.is-submitted-single {
    grid-template-columns: minmax(0, 1fr) !important;
  }

  .usage-submit-action-bar .btn {
    height: 40px !important;
    font-size: 13.5px !important;
    padding: 0 10px !important;
    justify-content: center !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
  }
}

/* 🚚 全标段在途发货单汇总督办 - 清爽大气现代样式 (PC横表 + 手机端响应式小卡片) */
.pending-summary-topbar-btn {
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%) !important;
  color: #ffffff !important;
  border: none !important;
  font-weight: 700 !important;
  font-size: 13.5px !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 0 16px !important;
  height: 38px !important;
  border-radius: 8px !important;
  box-shadow: 0 3px 10px rgba(234, 88, 12, 0.22) !important;
  transition: all 0.2s ease !important;
  white-space: nowrap !important;
  flex-shrink: 0 !important;
}

.pending-summary-topbar-btn:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 5px 14px rgba(234, 88, 12, 0.32) !important;
}

.badge-count-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  color: #ea580c;
  font-size: 11.5px;
  font-weight: 800;
  min-width: 20px;
  height: 20px;
  border-radius: 10px;
  padding: 0 5px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  white-space: nowrap;
}

/* 弹窗遮罩与主容器 */
.pending-super-overlay {
  background: rgba(15, 23, 42, 0.5) !important;
  backdrop-filter: blur(6px) !important;
  z-index: 1050 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.pending-clean-modal-container {
  max-width: 1360px !important;
  width: 94vw !important;
  max-height: 88vh !important;
  height: 88vh !important;
  padding: 0 !important;
  border-radius: 16px !important;
  box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.22) !important;
  overflow: hidden !important;
  display: flex !important;
  flex-direction: column !important;
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
}

/* 1. 简洁清爽 Header (单行流) */
.pending-clean-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  gap: 16px;
}

.header-left-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
}

.header-left-info .header-icon {
  font-size: 24px;
  line-height: 1;
}

.header-left-info .header-title {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.2px;
  white-space: nowrap;
}

.header-count-pill {
  display: inline-flex;
  align-items: center;
  background: #fff7ed;
  color: #ea580c;
  border: 1px solid #ffedd5;
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
  white-space: nowrap;
}

.header-right-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.btn-clean-ghost {
  height: 36px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap !important;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.btn-clean-ghost:hover:not(:disabled) {
  background: #f1f5f9;
  color: #0f172a;
  border-color: #94a3b8;
}

.btn-clean-ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-clean-export {
  height: 36px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap !important;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
  transition: all 0.15s ease;
}

.btn-clean-export:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);
}

.btn-clean-export:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-clean-close {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #64748b;
  font-size: 15px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.btn-clean-close:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
}

/* 2. 通透筛选工具栏 */
.pending-clean-toolbar {
  display: flex;
  align-items: center;
  padding: 12px 24px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  gap: 12px;
  flex-wrap: nowrap;
  overflow-x: auto;
  flex-shrink: 0;
}

.capsule-group {
  display: inline-flex;
  background: #e2e8f0;
  padding: 3px;
  border-radius: 8px;
  flex-shrink: 0;
  white-space: nowrap;
}

.capsule-item {
  border: none;
  background: transparent;
  padding: 5px 12px;
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap !important;
  transition: all 0.15s ease;
}

.capsule-item:hover {
  color: #0f172a;
}

.capsule-item.active {
  background: #ffffff;
  color: #0f172a;
  font-weight: 700;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.clean-select {
  height: 34px;
  padding: 0 12px;
  font-size: 12.5px;
  font-weight: 500;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  outline: none;
  flex-shrink: 0;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.15s;
}

.clean-select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

/* 🚛 车次合并开关 */
.btn-group-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap !important;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.btn-group-toggle:hover {
  background: #f8fafc;
  color: #0f172a;
  border-color: #94a3b8;
}

.btn-group-toggle.is-active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.toggle-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e1;
  display: inline-block;
  transition: background-color 0.15s ease;
}

.toggle-indicator.active {
  background: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2);
}

.sub-count-tag {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  font-weight: 700;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 0 5px;
  border-radius: 4px;
  vertical-align: middle;
}

.clean-search-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.clean-search-wrap .search-ic {
  position: absolute;
  left: 9px;
  font-size: 12px;
  color: #94a3b8;
  pointer-events: none;
}

.clean-search-input {
  height: 34px;
  padding: 0 28px 0 28px;
  font-size: 12.5px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  outline: none;
  width: 210px;
  transition: all 0.15s ease;
}

.clean-search-input:focus {
  border-color: #2563eb;
  width: 250px;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.clean-search-clear {
  position: absolute;
  right: 6px;
  width: 18px;
  height: 18px;
  border-radius: 9px;
  background: #e2e8f0;
  border: none;
  color: #64748b;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 3. 主体内容区 */
.pending-clean-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  position: relative;
}

.pending-content-wrapper {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* A. 桌面端通透大横表 (PC Table) */
.clean-table-scroll-wrap {
  flex: 1;
  overflow: auto;
}

.clean-wide-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
  min-width: 1200px;
}

.clean-wide-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
  background: #f8fafc;
}

.clean-wide-table th {
  padding: 13px 12px;
  background: #f8fafc;
  color: #475569;
  font-weight: 700;
  font-size: 12.5px;
  border-bottom: 1.5px solid #e2e8f0;
  white-space: nowrap;
}

.clean-sort-th {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.clean-sort-th:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.sort-icon-tag {
  font-size: 11px;
  color: #2563eb;
  background: #eff6ff;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 700;
}

.clean-table-tr {
  border-bottom: 1px solid #f1f5f9;
  transition: background-color 0.12s ease;
}

.clean-table-tr:hover {
  background-color: #f8fafc;
}

.clean-table-tr.tr-warning {
  background-color: #fffdf5;
}

.clean-table-tr.tr-severe {
  background-color: #fff8f8;
}

.clean-wide-table td {
  padding: 12px 12px;
  color: #334155;
  vertical-align: middle;
}

/* 单元格精细样式 */
.clean-cat-badge {
  display: inline-block;
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 6px;
  white-space: nowrap;
}

.clean-cat-badge.pipe {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #dbeafe;
}

.clean-cat-badge.fitting {
  background: #f5f3ff;
  color: #6d28d9;
  border: 1px solid #ede9fe;
}

.clean-status-badge {
  display: inline-block;
  font-size: 11.5px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 6px;
  white-space: nowrap;
}

.clean-status-badge.st-arriving {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}

.clean-status-badge.st-receiving {
  background: #f5f3ff;
  color: #7c3aed;
  border: 1px solid #ddd6fe;
}

.clean-status-badge.st-diff {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.clean-section-tag {
  display: inline-block;
  background: #f1f5f9;
  color: #0f172a;
  font-weight: 700;
  font-size: 12.5px;
  padding: 2px 8px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  white-space: nowrap;
}

.order-code-main {
  font-weight: 700;
  color: #0f172a;
  font-size: 12.5px;
  white-space: nowrap;
}

.shipment-code-sub {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap;
}

.clean-plate-pill {
  display: inline-block;
  background: #1e3a8a;
  color: #ffffff;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 700;
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid #3b82f6;
  white-space: nowrap;
}

.supply-entity-cell {
  color: #475569;
  font-size: 12.5px;
  white-space: nowrap;
}

.material-name-cell strong {
  color: #0f172a;
  font-size: 13px;
  line-height: 1.4;
}

.qty-highlight {
  font-size: 13.5px;
  font-weight: 800;
  color: #1d4ed8;
  white-space: nowrap;
}

.time-cell-text {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.clean-elapsed-pill {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #334155;
  font-weight: 700;
  font-size: 12px;
  white-space: nowrap;
}

.clean-elapsed-pill.is-warning {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
}

.clean-elapsed-pill.is-severe {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
}

.clean-elapsed-pill.unconfirmed {
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
  font-weight: 600;
}

.clean-elapsed-pill.unconfirmed.is-warning {
  background: #fef3c7 !important;
  color: #92400e !important;
  border: 1px solid #fde68a !important;
}

.clean-elapsed-pill.unconfirmed.is-severe {
  background: #fee2e2 !important;
  color: #b91c1c !important;
  border: 1px solid #fca5a5 !important;
}

.m-elapsed-box {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

/* 表格操作按钮组 (绝对不串行) */
.clean-op-btn-group {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}

.op-btn-jump {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap !important;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.op-btn-jump:hover {
  background: #2563eb;
  color: #ffffff;
}

.op-btn-detail {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap !important;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.op-btn-detail:hover {
  background: #f1f5f9;
  color: #0f172a;
}

/* B. 移动端小卡片 (PC端默认隐藏) */
.mobile-only-cards-grid {
  display: none;
}

/* 4. 清爽底栏 Footer */
.pending-clean-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.footer-stats-left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
}

.f-divider {
  color: #cbd5e1;
}

.text-blue { color: #2563eb; }
.text-purple { color: #7c3aed; }

.btn-clean-close-foot {
  height: 34px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  border-radius: 7px;
  cursor: pointer;
  white-space: nowrap !important;
  transition: all 0.15s ease;
}

.btn-clean-close-foot:hover {
  background: #f1f5f9;
  color: #0f172a;
}

/* 状态提示 */
.clean-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: #64748b;
}

.empty-emoji {
  font-size: 40px;
  margin-bottom: 8px;
}

.clean-empty-state h4 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #0f172a;
  font-weight: 700;
}

.clean-empty-state p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.clean-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}

.clean-error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
  border-bottom: 1px solid #fee2e2;
}

.spin-anim {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

/* 📱 手机端响应式专属：横表隐藏，展示小卡片 */
@media (max-width: 768px) {
  .pending-clean-modal-container {
    width: 100vw !important;
    height: 100vh !important;
    max-height: 100vh !important;
    border-radius: 0 !important;
    border: none !important;
  }

  .pending-clean-header {
    padding: 12px 14px;
    gap: 8px;
  }

  .header-left-info .header-title {
    font-size: 15px;
  }

  .header-count-pill {
    display: none;
  }

  .pending-clean-toolbar {
    padding: 10px 14px;
    gap: 8px;
  }

  .clean-search-input {
    width: 140px;
  }

  .clean-search-input:focus {
    width: 160px;
  }

  /* 隐藏 PC 大横表 */
  .pc-only-table {
    display: none !important;
  }

  /* 展示手机小卡片 */
  .mobile-only-cards-grid {
    display: flex !important;
    flex-direction: column;
    gap: 12px;
    padding: 14px;
    overflow-y: auto;
    flex: 1;
    background: #f8fafc;
  }

  .mobile-ticket-card {
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    padding: 12px 14px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .mobile-ticket-card.card-severe {
    border-left: 4px solid #ef4444;
  }

  .mobile-ticket-card.card-warning {
    border-left: 4px solid #f59e0b;
  }

  .m-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }

  .m-tags-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .clean-elapsed-pill.mini {
    font-size: 11px;
    padding: 2px 6px;
  }

  .m-card-body {
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: #f8fafc;
    padding: 8px 10px;
    border-radius: 8px;
  }

  .m-mat-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }

  .m-mat-name {
    font-size: 14px;
    font-weight: 800;
    color: #0f172a;
  }

  .m-qty-val {
    font-size: 14px;
    font-weight: 800;
    color: #2563eb;
    white-space: nowrap;
  }

  .m-info-line {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #475569;
    flex-wrap: wrap;
  }

  .m-info-k {
    color: #94a3b8;
  }

  .clean-plate-pill.mini {
    font-size: 11px;
    padding: 0 4px;
  }

  .m-supplier {
    font-size: 11.5px;
    color: #64748b;
  }

  .m-contact-line {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11.5px;
    color: #2563eb;
    background: #eff6ff;
    padding: 4px 8px;
    border-radius: 6px;
    width: fit-content;
    cursor: pointer;
  }

  .m-phone-txt {
    font-weight: 700;
  }

  .m-copy-tag {
    font-size: 10px;
    background: #dbeafe;
    padding: 1px 4px;
    border-radius: 4px;
  }

  .m-card-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
  }

  .m-btn-ghost {
    height: 32px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    white-space: nowrap !important;
    cursor: pointer;
  }

  .m-btn-primary {
    height: 32px;
    padding: 0 12px;
    font-size: 12.5px;
    font-weight: 700;
    color: #ffffff;
    background: #2563eb;
    border: none;
    border-radius: 6px;
    white-space: nowrap !important;
    cursor: pointer;
  }

  .pending-clean-footer {
    flex-direction: column;
    gap: 8px;
    padding: 10px 14px;
  }

  .footer-stats-left {
    font-size: 12px;
    flex-wrap: wrap;
  }
}

/* ==================== 🏛️ 全标段现场综合督办中心专属样式 ==================== */
.pending-modal-nav-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 24px;
  background: #f8fafc;
  border-bottom: 1.5px solid #e2e8f0;
  flex-shrink: 0;
}

.modal-nav-item {
  height: 38px;
  padding: 0 16px;
  font-size: 13.5px;
  font-weight: 700;
  color: #475569;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.15s ease;
  white-space: nowrap !important;
}

.modal-nav-item:hover {
  background: #f1f5f9;
  color: #0f172a;
  border-color: #94a3b8;
}

.modal-nav-item.active {
  color: #ffffff;
  background: #2563eb;
  border-color: #2563eb;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
}

.nav-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.nav-badge.warning {
  background: #fef3c7;
  color: #b45309;
}

.modal-nav-item.active .nav-badge.warning {
  background: #fbbf24;
  color: #78350f;
}

.nav-badge.info {
  background: #eff6ff;
  color: #1d4ed8;
}

.modal-nav-item.active .nav-badge.info {
  background: #ffffff;
  color: #1d4ed8;
}

.nav-badge.success {
  background: #ecfdf5;
  color: #047857;
}

.modal-nav-item.active .nav-badge.success {
  background: #ffffff;
  color: #047857;
}

.nav-badge.gray {
  background: #f1f5f9;
  color: #94a3b8;
}

.modal-nav-item.active .nav-badge.gray {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.supervision-tab-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* 4 大 KPI 卡片横栏 */
.gov-kpi-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 12px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.gov-kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #ffffff;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.gov-kpi-ic {
  font-size: 24px;
  line-height: 1;
}

.gov-kpi-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.gov-kpi-lbl {
  font-size: 11.5px;
  font-weight: 600;
  color: #64748b;
  white-space: nowrap;
}

.gov-kpi-val {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap;
}

.gov-kpi-val .unit {
  font-size: 11px;
  font-weight: normal;
  color: #94a3b8;
}

.gov-kpi-sub {
  font-size: 10.5px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.gov-sub-toolbar {
  background: #ffffff !important;
  border-bottom: 1px solid #e2e8f0;
}

.gov-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* ==================== 🏛️ 各标段填报履约督办精细化样式 (零串行、通透对齐) ==================== */
.sec-name-box {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap !important;
}

.sec-name-txt {
  font-size: 13.5px;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap !important;
}

.sec-region-badge {
  display: inline-block;
  font-size: 10.5px;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  padding: 1px 5px;
  border-radius: 4px;
  white-space: nowrap !important;
}

.sec-region-badge.mini {
  font-size: 10px;
}

.gov-cell-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  white-space: nowrap !important;
}

.gov-pill-line {
  display: flex;
  align-items: center;
  white-space: nowrap !important;
}

.gov-status-pill {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  font-size: 11.5px;
  font-weight: 700;
  border-radius: 5px;
  white-space: nowrap !important;
}

.gov-status-pill.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.gov-status-pill.warning {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}

.gov-status-pill.info {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.gov-status-pill.info.severe {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.gov-status-pill.gray {
  background: #f8fafc;
  color: #94a3b8;
  border: 1px solid #e2e8f0;
}

.gov-meta-line {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: #475569;
  white-space: nowrap !important;
}

.gov-meta-label {
  color: #64748b;
  font-size: 11px;
}

.gov-meta-val {
  font-size: 12px;
}

.gov-time-sub {
  font-size: 10.5px;
  color: #94a3b8;
  font-family: monospace;
}

.gov-loss-sub {
  font-size: 11px;
  color: #d97706;
}

.gov-history-txt {
  font-size: 11.5px;
  color: #b45309;
  white-space: nowrap !important;
}

.gov-history-none {
  font-size: 11.5px;
  color: #94a3b8;
  font-style: italic;
  white-space: nowrap !important;
}

.gov-del-breakdown {
  font-size: 11px;
  color: #64748b;
  white-space: nowrap !important;
}

.gov-severe-pill {
  font-size: 11px;
  font-weight: 700;
  color: #dc2626;
  background: #fee2e2;
  padding: 1px 5px;
  border-radius: 4px;
  white-space: nowrap !important;
}

.btn-gov-action {
  height: 32px;
  padding: 0 12px;
  font-size: 12.5px;
  font-weight: 700;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  white-space: nowrap !important;
  transition: all 0.15s ease;
}

.btn-gov-action:hover {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.2);
}

.m-btn-jump.full-w {
  width: 100%;
  height: 34px;
  font-size: 13px;
}

@media (max-width: 900px) {
  .gov-kpi-bar {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    padding: 10px;
  }
}

.user-matrix-link {
  cursor: pointer !important;
  color: #4f46e5 !important;
  font-weight: 600 !important;
  text-decoration: underline dotted #818cf8 !important;
  text-underline-offset: 3px !important;
  transition: all 0.2s ease !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 2px !important;
}

.user-matrix-link:hover {
  color: #312e81 !important;
  background: #eef2ff !important;
  border-radius: 4px !important;
  text-decoration: underline solid #4f46e5 !important;
  box-shadow: 0 0 0 2px #e0e7ff !important;
}

/* --- 📈 保温管需求与库存信息统计专有样式 --- */
.demand-overview-pane {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 1. 顶部 4 张关键态势概览指标卡片 */
.overview-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.overview-kpi-card {
  padding: 16px 20px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s ease;
}

.overview-kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.1);
}

.overview-kpi-card.kpi-purple {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-color: rgba(139, 92, 246, 0.25);
}

.overview-kpi-card.kpi-green {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-color: rgba(16, 185, 129, 0.25);
}

.overview-kpi-card.kpi-blue {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-color: rgba(2, 132, 199, 0.25);
}

.overview-kpi-card.kpi-red {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border-color: rgba(239, 68, 68, 0.35);
}

.overview-kpi-card.kpi-safe {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-color: #cbd5e1;
}

.overview-kpi-card.is-alert-pulse {
  animation: pulse-danger-glow 2.5s infinite ease-in-out;
}

@keyframes pulse-danger-glow {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.kpi-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kpi-icon {
  font-size: 20px;
}

.kpi-title {
  font-size: 13.5px;
  font-weight: 600;
  color: #475569;
}

.kpi-main-val {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.kpi-number {
  font-size: 26px;
  font-weight: 800;
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  color: #0f172a;
  letter-spacing: -0.5px;
}

.kpi-purple .kpi-number { color: #6d28d9; }
.kpi-green .kpi-number { color: #047857; }
.kpi-blue .kpi-number { color: #0369a1; }
.kpi-red .kpi-number { color: #b91c1c; }

.kpi-unit {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.kpi-footer-note {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

/* 2. 可视化图表区 */
.overview-chart-box {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.overview-chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f1f5f9;
}

.chart-box-title {
  font-size: 14.5px;
  font-weight: 700;
  color: #1e293b;
}

.chart-legend-hint {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 12px;
  color: #64748b;
}

.chart-legend-hint .dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 4px;
}

.chart-legend-hint .dot.purple { background: #7c3aed; }
.chart-legend-hint .dot.green { background: #059669; }
.chart-legend-hint .dot.blue { background: #0284c7; }
.chart-legend-hint .dot.red { background: #dc2626; }

.overview-chart-stage {
  position: relative;
  width: 100%;
  min-height: 380px;
  display: block;
}

.overview-echarts-dom {
  width: 100% !important;
  min-width: 100% !important;
  height: 380px !important;
  display: block;
}

.chart-loading-placeholder,
.chart-empty-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(2px);
  z-index: 10;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
  color: #64748b;
  font-size: 14px;
}

/* 3. 数据表格区 */
.overview-table-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.overview-table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 4px 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-heading {
  font-size: 14.5px;
  font-weight: 700;
  color: #1e293b;
}

.toolbar-count-tag {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 500;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gap-filter-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #b91c1c;
  cursor: pointer;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 5px 12px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.15s ease;
}

.gap-filter-checkbox:hover {
  background: #fee2e2;
}

.overview-search-input {
  height: 34px;
  width: 220px;
  padding: 0 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  transition: all 0.2s ease;
}

.overview-search-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.overview-data-table th {
  background: #f8fafc;
  padding: 10px 8px !important;
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
}

.overview-data-table td {
  padding: 8px 8px !important;
  font-size: 13px;
  border-bottom: 1px solid #f1f5f9;
}

.highlight-gap-row {
  background: rgba(254, 242, 242, 0.45) !important;
}

.gap-warning-pill {
  display: inline-block;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 4px;
  padding: 2px 6px;
  font-weight: 700;
}

.status-pill {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-pill.pill-danger {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.status-pill.pill-info {
  background: #f0f9ff;
  color: #0284c7;
  border: 1px solid #bae6fd;
}

.status-pill.pill-success {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.status-pill.pill-neutral {
  background: #f8fafc;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.row-actions-group {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
}

.btn-xs {
  height: 24px;
  padding: 0 6px;
  font-size: 11.5px;
  border-radius: 4px;
}

.summary-total-row td {
  background: #f8fafc;
  border-top: 2px solid #cbd5e1;
  font-size: 13px;
}

@media (max-width: 1024px) {
  .overview-kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .overview-kpi-grid {
    grid-template-columns: 1fr;
  }
}
</style>
