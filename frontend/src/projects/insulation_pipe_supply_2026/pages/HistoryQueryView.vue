<template>
  <div class="history-query-view page-layout" @click="activeDropdown = null">
    <AppHeader />
    <main class="page-main container">
      <!-- 统一面包屑导航 -->
      <Breadcrumbs :items="breadcrumbItems" />
      
      <div v-if="loading && !configSummary" class="loading-state">
        <div class="spinner"></div>
        <span>系统数据初始化加载中...</span>
      </div>
      <div v-else-if="errorMessage" class="error-state">{{ errorMessage }}</div>
      <div v-else class="page-content">
        <!-- 头部导航与标题 -->
        <header class="page-title-row">
          <div class="title-wrap">
            <h2>📊 综合数据查询中心</h2>
            <p class="subtitle">全生命周期每日流转、设计采购基准进度、责任主体与人员管辖多维综合查询与开会速查枢纽</p>
          </div>
          <button class="btn ghost back-btn" type="button" @click="goProjectPages">
            ← 返回项目主页
          </button>
        </header>

        <!-- 🔍 全局多维智能筛选控制台 (标准网格排版，拒绝串行) -->
        <section class="card filter-hub-card">
          <!-- 筛选器顶栏操作 -->
          <div class="filter-hub-header">
            <div class="filter-hub-title">
              <span class="hub-icon">🔍</span>
              <span class="hub-text">多维综合数据筛选器</span>
              <span class="hub-tag">实时联动过滤</span>
            </div>
            <div class="filter-hub-actions">
              <button type="button" class="btn btn-sm btn-ghost" @click="resetAllFilters">
                <span>🔄 重置全部</span>
              </button>
              <button type="button" class="btn btn-sm btn-primary" @click="triggerCurrentQuery">
                <span>🔍 立即查询</span>
              </button>
              <button 
                type="button" 
                class="btn btn-sm btn-export" 
                :disabled="exportLoading"
                @click="exportCurrentTabExcel"
              >
                <span>{{ exportLoading ? '⏳ 导出中...' : '📥 导出 Excel (.xlsx)' }}</span>
              </button>
            </div>
          </div>

          <!-- 4 列等高整齐网格控制区 -->
          <div class="filter-grid-layout">
            <!-- 第 1 列：标段多选 -->
            <div class="filter-cell relative">
              <div class="cell-label-row">
                <span class="cell-label">🏗️ 需求标段 (可多选)</span>
                <span v-if="selectedSectionIds.length > 0" class="badge-count">已选 {{ selectedSectionIds.length }} 个</span>
              </div>
              <div 
                class="custom-select-trigger" 
                @click.stop="toggleDropdown('section1')"
              >
                <span class="trigger-text">{{ section1TriggerText }}</span>
                <span class="dropdown-arrow">▼</span>
              </div>

              <!-- 标段多选下拉浮层 -->
              <div 
                v-if="activeDropdown === 'section1'" 
                class="custom-dropdown-panel"
                @click.stop
              >
                <div class="dropdown-actions">
                  <button type="button" class="btn-link" @click="selectAllSections">✓ 全选</button>
                  <button type="button" class="btn-link text-muted" @click="clearSections">✕ 清空</button>
                </div>
                <div class="dropdown-list">
                  <label 
                    v-for="st in demandEntities" 
                    :key="st.section_1_id" 
                    class="checkbox-item"
                  >
                    <input 
                      type="checkbox" 
                      :value="st.section_1_id" 
                      v-model="selectedSectionIds" 
                      @change="onFilterChange"
                    />
                    <span>{{ st.section_1_name || st.name || st.section_1_id }}</span>
                  </label>
                </div>
              </div>
            </div>

            <!-- 第 2 列：型号规格 -->
            <div class="filter-cell relative" v-if="activeTab !== 'directory'">
              <div class="cell-label-row">
                <span class="cell-label">{{ subMaterialType === 'pipe' ? '🔥 保温管型号 (可多选)' : '🔧 管件类型/规格' }}</span>
                <span v-if="subMaterialType === 'pipe' && selectedPipeModelIds.length > 0" class="badge-count">已选 {{ selectedPipeModelIds.length }} 个</span>
              </div>

              <!-- 保温管型号下拉 -->
              <template v-if="subMaterialType === 'pipe'">
                <div 
                  class="custom-select-trigger" 
                  @click.stop="toggleDropdown('pipeModel')"
                >
                  <span class="trigger-text">{{ pipeModelTriggerText }}</span>
                  <span class="dropdown-arrow">▼</span>
                </div>

                <div 
                  v-if="activeDropdown === 'pipeModel'" 
                  class="custom-dropdown-panel"
                  @click.stop
                >
                  <div class="dropdown-actions">
                    <button type="button" class="btn-link" @click="selectAllPipeModels">✓ 全选</button>
                    <button type="button" class="btn-link text-muted" @click="clearPipeModels">✕ 清空</button>
                  </div>
                  <div class="dropdown-list">
                    <label 
                      v-for="pm in pipeModelOptions" 
                      :key="pm.pipe_model_id" 
                      class="checkbox-item"
                    >
                      <input 
                        type="checkbox" 
                        :value="pm.pipe_model_id" 
                        v-model="selectedPipeModelIds" 
                        @change="onFilterChange"
                      />
                      <span>{{ pm.pipe_model_name || pm.name || pm.pipe_model_id }}</span>
                    </label>
                  </div>
                </div>
              </template>

              <!-- 管件关键字搜索 -->
              <template v-else>
                <div class="input-with-clear">
                  <input 
                    v-model="fittingKeyword" 
                    class="input form-control" 
                    type="text" 
                    placeholder="输入弯头/三通/DN规格..." 
                    @input="onFilterChange"
                  />
                  <span v-if="fittingKeyword" class="clear-btn" @click="fittingKeyword = ''; onFilterChange()">✕</span>
                </div>
              </template>
            </div>

            <!-- 第 3 列：业务时段 (仅每日流转需日期，其他Tab占位或扩展) -->
            <div class="filter-cell date-cell" v-if="activeTab === 'daily_flow'">
              <div class="cell-label-row">
                <span class="cell-label">📅 查询时段</span>
                <div class="capsule-group">
                  <button 
                    type="button" 
                    :class="['capsule-btn', { active: activeDateCapsule === 'all' }]"
                    @click="setDateRangeByCapsule('all')"
                  >全部</button>
                  <button 
                    type="button" 
                    :class="['capsule-btn', { active: activeDateCapsule === '7days' }]"
                    @click="setDateRangeByCapsule('7days')"
                  >近7天</button>
                  <button 
                    type="button" 
                    :class="['capsule-btn', { active: activeDateCapsule === '30days' }]"
                    @click="setDateRangeByCapsule('30days')"
                  >近30天</button>
                </div>
              </div>
              <div class="date-range-box">
                <input v-model="filterStartDate" class="input date-control" type="date" @change="onDateInputChange" />
                <span class="range-arrow">➔</span>
                <input v-model="filterEndDate" class="input date-control" type="date" @change="onDateInputChange" />
              </div>
            </div>

            <!-- 第 4 列：全局模糊速搜 -->
            <div class="filter-cell search-cell" :class="{ 'grid-span-2': activeTab !== 'daily_flow' }">
              <div class="cell-label-row">
                <span class="cell-label">🔎 关键字全局速搜</span>
              </div>
              <div class="input-with-clear">
                <input 
                  v-model="globalSearchKeyword" 
                  class="input form-control" 
                  type="text" 
                  placeholder="人名/手机号/标段/单号/单位/车牌..." 
                  @input="onFilterChange"
                  @keyup.enter="triggerCurrentQuery"
                />
                <span v-if="globalSearchKeyword" class="clear-btn" @click="globalSearchKeyword = ''; onFilterChange()">✕</span>
              </div>
            </div>
          </div>

          <!-- 已选条件 Chips 标签栏 (选中有值时展示) -->
          <div v-if="hasActiveFilterChips" class="active-chips-bar">
            <span class="chips-title">已选条件：</span>
            
            <!-- 标段 Chips -->
            <span 
              v-for="secId in selectedSectionIds" 
              :key="`sec-${secId}`" 
              class="filter-chip chip-section"
            >
              <span>{{ getSectionName(secId) }}</span>
              <button type="button" class="chip-remove" @click="removeSection(secId)">✕</button>
            </span>

            <!-- 保温管型号 Chips -->
            <span 
              v-for="pmId in selectedPipeModelIds" 
              :key="`pm-${pmId}`" 
              class="filter-chip chip-model"
            >
              <span>{{ getPipeModelName(pmId) }}</span>
              <button type="button" class="chip-remove" @click="removePipeModel(pmId)">✕</button>
            </span>

            <!-- 管件关键字 Chip -->
            <span v-if="fittingKeyword.trim()" class="filter-chip chip-keyword">
              <span>管件: {{ fittingKeyword }}</span>
              <button type="button" class="chip-remove" @click="fittingKeyword = ''; onFilterChange()">✕</button>
            </span>

            <!-- 全局搜索 Chip -->
            <span v-if="globalSearchKeyword.trim()" class="filter-chip chip-search">
              <span>搜: {{ globalSearchKeyword }}</span>
              <button type="button" class="chip-remove" @click="globalSearchKeyword = ''; onFilterChange()">✕</button>
            </span>

            <button type="button" class="btn-clear-chips" @click="resetAllFilters">清空全部筛选</button>
          </div>
        </section>

        <!-- 📑 3 大核心综合标签页 (Tabs) -->
        <div class="history-tab-bar">
          <button
            type="button"
            :class="['tab-pill-btn', { active: activeTab === 'daily_flow' }]"
            @click="switchMainTab('daily_flow')"
          >
            <span class="tab-label-full">📅 每日历史综合流转台账</span>
            <span class="tab-label-short">📅 每日流转</span>
          </button>
          <button
            type="button"
            :class="['tab-pill-btn', { active: activeTab === 'baseline_progress' }]"
            @click="switchMainTab('baseline_progress')"
          >
            <span class="tab-label-full">📐 设计采购与基准量进度</span>
            <span class="tab-label-short">📐 基准进度</span>
          </button>
          <button
            type="button"
            :class="['tab-pill-btn', { active: activeTab === 'directory' }]"
            @click="switchMainTab('directory')"
          >
            <span class="tab-label-full">🏢 责任主体与人员管辖矩阵</span>
            <span class="tab-label-short">🏢 责任主体</span>
          </button>
        </div>

        <!-- ==================================================================== -->
        <!-- 📅 Tab 1: 每日历史综合流转台账 -->
        <!-- ==================================================================== -->
        <section v-if="activeTab === 'daily_flow'" class="tab-content-section">
          <!-- 子品类切换 -->
          <div class="sub-pill-bar">
            <button 
              type="button" 
              :class="['sub-pill', { active: subMaterialType === 'pipe' }]"
              @click="switchSubMaterial('pipe')"
            >
              🔥 保温管
            </button>
            <button 
              type="button" 
              :class="['sub-pill', { active: subMaterialType === 'fitting' }]"
              @click="switchSubMaterial('fitting')"
            >
              🔧 管件
            </button>
          </div>

          <!-- 顶部 KPI 开会速读看板 -->
          <div class="kpi-banner-grid" v-if="subMaterialType === 'pipe'">
            <div class="kpi-card">
              <span class="kpi-label">📦 时段累计计划量</span>
              <span class="kpi-val text-slate">{{ formatQty(dailyPipeSummary.total_plan_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🚚 供给侧累计发货</span>
              <span class="kpi-val text-sky">{{ formatQty(dailyPipeSummary.total_shipped_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📥 现场确认总到货</span>
              <span class="kpi-val text-blue">{{ formatQty(dailyPipeSummary.total_arrived_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">👷 施工接收总量</span>
              <span class="kpi-val text-indigo">{{ formatQty(dailyPipeSummary.total_received_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🔧 现场实际使用量</span>
              <span class="kpi-val text-emerald">{{ formatQty(dailyPipeSummary.total_usage_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">💼 库管已确认总量</span>
              <span class="kpi-val text-amber">{{ formatQty(dailyPipeSummary.total_warehouse_qty) }} <small>米</small></span>
            </div>
          </div>

          <div class="kpi-banner-grid" v-else>
            <div class="kpi-card">
              <span class="kpi-label">🚚 累计发货管件</span>
              <span class="kpi-val text-sky">{{ dailyFittingSummary.total_shipped_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📥 确认到货总数</span>
              <span class="kpi-val text-blue">{{ dailyFittingSummary.total_arrived_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">👷 施工接收总数</span>
              <span class="kpi-val text-indigo">{{ dailyFittingSummary.total_received_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🔧 现场安装总数</span>
              <span class="kpi-val text-emerald">{{ dailyFittingSummary.total_usage_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📦 当前现场库存结余</span>
              <span class="kpi-val text-amber">{{ dailyFittingSummary.site_stock_pcs || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">💼 库管已确认</span>
              <span class="kpi-val text-slate">{{ dailyFittingSummary.total_warehouse_qty || 0 }} <small>件</small></span>
            </div>
          </div>

          <!-- 表格主体 -->
          <div class="card elevated table-card">
            <!-- 🎛️ 表格顶部紧凑工具栏 (含聚合维度下拉选择器) -->
            <div class="table-toolbar-row">
              <div class="toolbar-left">
                <span class="toolbar-title">📊 流转台账明细与透视</span>
                <span class="toolbar-count font-mono text-muted">({{ aggregatedDailyRows.length }} 组聚合数据)</span>
              </div>

              <div class="toolbar-right">
                <!-- 聚合维度下拉触发与菜单 -->
                <div class="pivot-dropdown-wrap">
                  <button 
                    type="button" 
                    :class="['btn-pivot-trigger', { active: activePivotDropdown === 'daily' }]"
                    @click.stop="togglePivotDropdown('daily')"
                  >
                    <span class="trigger-icon">🎛️</span>
                    <span class="trigger-label">聚合维度:</span>
                    <span class="trigger-chain">{{ getDimensionChainText('daily') }}</span>
                    <span class="trigger-arrow">▾</span>
                  </button>

                  <!-- 背景点击遮罩 -->
                  <div 
                    v-if="activePivotDropdown === 'daily'" 
                    class="pivot-backdrop" 
                    @click.stop="closePivotDropdown"
                  ></div>

                  <!-- 浮层下拉列表面板 -->
                  <div 
                    v-if="activePivotDropdown === 'daily'" 
                    class="pivot-dropdown-panel card elevated"
                    @click.stop
                  >
                    <div class="panel-header">
                      <span class="panel-title">选择透视维度（按勾选顺序依次分组）</span>
                      <button type="button" class="btn-panel-reset" @click="resetToDefaultDimensions('daily')">↺ 恢复默认</button>
                    </div>

                    <!-- 维度有序多选列表 -->
                    <div class="panel-options-list">
                      <div 
                        v-for="dim in getAvailableDimensions('daily')" 
                        :key="`daily-opt-${dim.id}`"
                        :class="['panel-opt-item', { checked: isDimensionSelected('daily', dim.id) }]"
                        @click="toggleDimensionSelection('daily', dim.id)"
                      >
                        <div class="opt-badge-slot">
                          <span v-if="isDimensionSelected('daily', dim.id)" class="badge-active-num">{{ getDimensionOrder('daily', dim.id) }}</span>
                          <span v-else class="badge-unchecked"></span>
                        </div>
                        <span class="opt-name">{{ dim.label }}</span>
                        
                        <div v-if="isDimensionSelected('daily', dim.id)" class="opt-order-btns" @click.stop>
                          <button 
                            type="button" 
                            class="btn-rank" 
                            :disabled="getDimensionOrder('daily', dim.id) === 1"
                            title="提升此维度分组优先级"
                            @click="moveDimensionUp('daily', dim.id)"
                          >
                            ↑
                          </button>
                          <button 
                            type="button" 
                            class="btn-rank" 
                            :disabled="getDimensionOrder('daily', dim.id) === dailyDimensions.length"
                            title="降低此维度分组优先级"
                            @click="moveDimensionDown('daily', dim.id)"
                          >
                            ↓
                          </button>
                        </div>
                      </div>
                    </div>

                    <!-- 常用快捷方案 -->
                    <div class="panel-presets-row">
                      <span class="presets-caption">⚡ 常用：</span>
                      <div class="presets-btn-chips">
                        <button
                          v-for="(p, pIdx) in dailyDimensionPresets"
                          :key="`p-daily-${pIdx}`"
                          type="button"
                          :class="['btn-preset-chip', { active: isCurrentPreset('daily', p.dims) }]"
                          @click="applyDimensionPreset('daily', p.dims)"
                        >
                          {{ p.label }}
                        </button>
                      </div>
                    </div>

                    <div class="panel-footer">
                      <button type="button" class="btn-panel-done" @click="closePivotDropdown">完成</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="tabLoading" class="loading-box">
              <div class="spinner-sm"></div>
              <span>⏳ 正在聚合历史流转台账数据...</span>
            </div>
            <div v-else-if="aggregatedDailyRows.length === 0" class="empty-box">未查询到符合条件的每日流转历史记录。</div>
            <div v-else class="table-container">
              <table class="data-table">
                <thead>
                  <tr v-if="subMaterialType === 'pipe'">
                    <th 
                      v-for="dim in dailyDimensions" 
                      :key="`th-daily-${dim}`"
                      :class="['text-left', 'th-dimension', `th-dim-${dim}`, 'sortable-th', { 'sorted-col': isColumnSorted('daily_pipe', dim) }]"
                      @click="handleTableSort('daily_pipe', dim)"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>{{ getDimensionDef(dim).colHeader }}</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', dim) }">{{ getSortIcon('daily_pipe', dim) }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_pipe', 'plan_qty') }" @click="handleTableSort('daily_pipe', 'plan_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>计划量 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', 'plan_qty') }">{{ getSortIcon('daily_pipe', 'plan_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_pipe', 'shipped_qty') }" @click="handleTableSort('daily_pipe', 'shipped_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>发货量 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', 'shipped_qty') }">{{ getSortIcon('daily_pipe', 'shipped_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_pipe', 'arrived_qty') }" @click="handleTableSort('daily_pipe', 'arrived_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>到货量 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', 'arrived_qty') }">{{ getSortIcon('daily_pipe', 'arrived_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_pipe', 'received_qty') }" @click="handleTableSort('daily_pipe', 'received_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>施工接收 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', 'received_qty') }">{{ getSortIcon('daily_pipe', 'received_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_pipe', 'usage_qty') }" @click="handleTableSort('daily_pipe', 'usage_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>实际使用 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', 'usage_qty') }">{{ getSortIcon('daily_pipe', 'usage_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_pipe', 'loss_qty') }" @click="handleTableSort('daily_pipe', 'loss_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>损耗量 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', 'loss_qty') }">{{ getSortIcon('daily_pipe', 'loss_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_pipe', 'warehouse_qty') }" @click="handleTableSort('daily_pipe', 'warehouse_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>库管已确认 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', 'warehouse_qty') }">{{ getSortIcon('daily_pipe', 'warehouse_qty') }}</span>
                      </div>
                    </th>
                    <th v-if="dailyDimensions.includes('date')" class="text-center sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_pipe', 'avg_transit') }" @click="handleTableSort('daily_pipe', 'avg_transit')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-center">
                        <span>在途时长</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_pipe', 'avg_transit') }">{{ getSortIcon('daily_pipe', 'avg_transit') }}</span>
                      </div>
                    </th>
                  </tr>
                  <tr v-else>
                    <th 
                      v-for="dim in dailyDimensions" 
                      :key="`th-daily-fit-${dim}`"
                      :class="['text-left', 'th-dimension', `th-dim-${dim}`, 'sortable-th', { 'sorted-col': isColumnSorted('daily_fitting', dim) }]"
                      @click="handleTableSort('daily_fitting', dim)"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>{{ getDimensionDef(dim).colHeader }}</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_fitting', dim) }">{{ getSortIcon('daily_fitting', dim) }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_fitting', 'shipped_qty') }" @click="handleTableSort('daily_fitting', 'shipped_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>发货数量 (件)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_fitting', 'shipped_qty') }">{{ getSortIcon('daily_fitting', 'shipped_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_fitting', 'arrived_qty') }" @click="handleTableSort('daily_fitting', 'arrived_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>到货数量 (件)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_fitting', 'arrived_qty') }">{{ getSortIcon('daily_fitting', 'arrived_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_fitting', 'received_qty') }" @click="handleTableSort('daily_fitting', 'received_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>施工接收 (件)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_fitting', 'received_qty') }">{{ getSortIcon('daily_fitting', 'received_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_fitting', 'usage_qty') }" @click="handleTableSort('daily_fitting', 'usage_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>现场安装 (件)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_fitting', 'usage_qty') }">{{ getSortIcon('daily_fitting', 'usage_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_fitting', 'warehouse_qty') }" @click="handleTableSort('daily_fitting', 'warehouse_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>库管已确认 (件)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_fitting', 'warehouse_qty') }">{{ getSortIcon('daily_fitting', 'warehouse_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('daily_fitting', 'site_stock_pcs') }" @click="handleTableSort('daily_fitting', 'site_stock_pcs')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>现场结余 (件)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('daily_fitting', 'site_stock_pcs') }">{{ getSortIcon('daily_fitting', 'site_stock_pcs') }}</span>
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <template v-if="subMaterialType === 'pipe'">
                    <tr 
                      v-for="(row, idx) in sortedDailyPipeRows" 
                      :key="idx"
                      :class="{ 'clickable-row': isDefaultFullDaily }"
                      @click="isDefaultFullDaily && openDailyPipeDetail(row)"
                    >
                      <!-- 动态渲染激活的维度列 -->
                      <td 
                        v-for="dim in dailyDimensions" 
                        :key="`td-daily-${dim}`"
                        :class="['text-left', `td-dim-${dim}`]"
                      >
                        <template v-if="dim === 'date'">
                          <span class="font-mono font-medium">{{ row.biz_date }}</span>
                        </template>
                        <template v-else-if="dim === 'section'">
                          <span class="font-bold text-dark section-cell-text">{{ row.section_1_name }}</span>
                        </template>
                        <template v-else-if="dim === 'model'">
                          <span class="badge model-badge">{{ row.pipe_model_name }}</span>
                        </template>
                        <template v-else-if="dim === 'supplier'">
                          <span class="font-medium text-sky">{{ row.supplier_name }}</span>
                        </template>
                      </td>

                      <td class="text-right font-medium text-slate">{{ formatQty(row.plan_qty) }}</td>
                      <td class="text-right font-medium text-sky">{{ formatQty(row.shipped_qty) }}</td>
                      <td class="text-right font-bold text-blue">{{ formatQty(row.arrived_qty) }}</td>
                      <td class="text-right font-medium text-indigo">{{ formatQty(row.received_qty) }}</td>
                      <td class="text-right font-bold text-emerald">{{ formatQty(row.usage_qty) }}</td>
                      <td class="text-right font-medium text-rose">{{ formatQty(row.loss_qty) }}</td>
                      <td class="text-right font-bold text-amber">{{ formatQty(row.warehouse_qty) }}</td>
                      <td v-if="dailyDimensions.includes('date')" class="text-center font-mono text-muted">{{ row.avg_transit_display }}</td>
                    </tr>
                  </template>

                  <template v-else>
                    <tr 
                      v-for="(row, idx) in sortedDailyFittingRows" 
                      :key="idx"
                    >
                      <!-- 动态渲染管件维度列 -->
                      <td 
                        v-for="dim in dailyDimensions" 
                        :key="`td-daily-fit-${dim}`"
                        :class="['text-left', `td-dim-${dim}`]"
                      >
                        <template v-if="dim === 'date'">
                          <span class="font-mono font-medium">{{ row.biz_date }}</span>
                        </template>
                        <template v-else-if="dim === 'section'">
                          <span class="font-bold text-dark section-cell-text">{{ row.section_1_name }}</span>
                        </template>
                        <template v-else-if="dim === 'model'">
                          <span class="font-bold text-slate">{{ row.fitting_type }}</span>
                          <span class="font-medium text-muted" style="margin-left: 4px;">{{ row.model_spec }}</span>
                        </template>
                        <template v-else-if="dim === 'supplier'">
                          <span class="font-medium text-sky">{{ row.supplier_name }}</span>
                        </template>
                      </td>

                      <td class="text-right font-medium text-sky">{{ row.shipped_qty }}</td>
                      <td class="text-right font-bold text-blue">{{ row.arrived_qty }}</td>
                      <td class="text-right font-medium text-indigo">{{ row.received_qty }}</td>
                      <td class="text-right font-bold text-emerald">{{ row.usage_qty }}</td>
                      <td class="text-right font-bold text-amber">{{ row.warehouse_qty }}</td>
                      <td class="text-right font-bold text-slate">{{ Math.max(0, row.arrived_qty - row.usage_qty) }}</td>
                    </tr>
                  </template>

                  <!-- 汇总底栏 (colspan 动态匹配维度数量) -->
                  <tr class="summary-footer-row">
                    <td :colspan="dailyDimensions.length" class="text-left">
                      📊 筛选范围内总量汇总 (已聚合为 {{ aggregatedDailyRows.length }} 组)
                    </td>
                    <template v-if="subMaterialType === 'pipe'">
                      <td class="text-right">{{ formatQty(dailyPipeSummary.total_plan_qty) }}</td>
                      <td class="text-right text-sky">{{ formatQty(dailyPipeSummary.total_shipped_qty) }}</td>
                      <td class="text-right text-blue">{{ formatQty(dailyPipeSummary.total_arrived_qty) }}</td>
                      <td class="text-right text-indigo">{{ formatQty(dailyPipeSummary.total_received_qty) }}</td>
                      <td class="text-right text-emerald">{{ formatQty(dailyPipeSummary.total_usage_qty) }}</td>
                      <td class="text-right text-rose">{{ formatQty(dailyPipeSummary.total_loss_qty) }}</td>
                      <td class="text-right text-amber">{{ formatQty(dailyPipeSummary.total_warehouse_qty) }}</td>
                      <td v-if="dailyDimensions.includes('date')" class="text-center font-mono">{{ dailyPipeSummary.overall_avg_transit }}</td>
                    </template>
                    <template v-else>
                      <td class="text-right text-sky">{{ dailyFittingSummary.total_shipped_qty }}</td>
                      <td class="text-right text-blue">{{ dailyFittingSummary.total_arrived_qty }}</td>
                      <td class="text-right text-indigo">{{ dailyFittingSummary.total_received_qty }}</td>
                      <td class="text-right text-emerald">{{ dailyFittingSummary.total_usage_qty }}</td>
                      <td class="text-right text-amber">{{ dailyFittingSummary.total_warehouse_qty }}</td>
                      <td class="text-right text-slate">{{ dailyFittingSummary.site_stock_pcs }}</td>
                    </template>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- ==================================================================== -->
        <!-- 📐 Tab 2: 设计使用量与计划采购量对照 -->
        <!-- ==================================================================== -->
        <section v-else-if="activeTab === 'baseline_progress'" class="tab-content-section">
          <!-- 子品类切换 -->
          <div class="sub-pill-bar">
            <button 
              type="button" 
              :class="['sub-pill', { active: subMaterialType === 'pipe' }]"
              @click="switchSubMaterial('pipe')"
            >
              🔥 保温管
            </button>
            <button 
              type="button" 
              :class="['sub-pill', { active: subMaterialType === 'fitting' }]"
              @click="switchSubMaterial('fitting')"
            >
              🔧 管件
            </button>
          </div>

          <!-- 顶部 KPI 开会看板 -->
          <div class="kpi-banner-grid" v-if="subMaterialType === 'pipe'">
            <div class="kpi-card">
              <span class="kpi-label">📐 全项目总设计量</span>
              <span class="kpi-val text-slate">{{ formatQty(baselinePipeSummary.total_design_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📋 全项目计划采购量</span>
              <span class="kpi-val text-slate">{{ formatQty(baselinePipeSummary.total_purchase_plan_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🚚 累计已发货</span>
              <span class="kpi-val text-sky">{{ formatQty(baselinePipeSummary.total_shipped_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📥 累计已到货</span>
              <span class="kpi-val text-blue">{{ formatQty(baselinePipeSummary.total_arrived_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🔧 累计已安装</span>
              <span class="kpi-val text-emerald">{{ formatQty(baselinePipeSummary.total_usage_qty) }} <small>米</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📦 现场库存余量</span>
              <span class="kpi-val text-amber">{{ formatQty(baselinePipeSummary.total_stock_qty) }} <small>米</small></span>
            </div>
          </div>

          <div class="kpi-banner-grid" v-else>
            <div class="kpi-card">
              <span class="kpi-label">📐 总设计管件数</span>
              <span class="kpi-val text-slate">{{ baselineFittingSummary.total_design_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📋 计划采购总数</span>
              <span class="kpi-val text-slate">{{ baselineFittingSummary.total_purchase_plan_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🚚 累计已发货</span>
              <span class="kpi-val text-sky">{{ baselineFittingSummary.total_shipped_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📥 累计已到货</span>
              <span class="kpi-val text-blue">{{ baselineFittingSummary.total_arrived_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🔧 累计已安装</span>
              <span class="kpi-val text-emerald">{{ baselineFittingSummary.total_usage_qty || 0 }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📦 现场可用库存</span>
              <span class="kpi-val text-amber">{{ baselineFittingSummary.total_stock_qty || 0 }} <small>件</small></span>
            </div>
          </div>

          <!-- 🔧 管件模式专属子视图切换栏 (双表独立查询) -->
          <div v-if="subMaterialType === 'fitting'" class="fitting-tab2-sub-nav">
            <button 
              type="button"
              :class="['btn-sub-view', { active: fittingTab2SubView === 'baseline' }]" 
              @click="fittingTab2SubView = 'baseline'"
            >
              📐 管件设计与计划采购基准表 
              <span class="sub-view-badge">({{ aggregatedFittingBaselineRows.length }} 组 / {{ filteredFittingBaselineRows.length }} 项)</span>
            </button>
            <button 
              type="button" 
              :class="['btn-sub-view', { active: fittingTab2SubView === 'flow' }]" 
              @click="fittingTab2SubView = 'flow'"
            >
              🚚 管件全周期累计流转与现场库存 
              <span class="sub-view-badge">({{ aggregatedFittingFlowRows.length }} 组 / {{ filteredFittingFlowRows.length }} 项)</span>
            </button>
          </div>

          <!-- 对照表格 -->
          <div class="card elevated table-card">
            <!-- 🎛️ 表格顶部紧凑工具栏 (含聚合维度下拉选择器) -->
            <div class="table-toolbar-row">
              <div class="toolbar-left">
                <span class="toolbar-title">
                  <template v-if="subMaterialType === 'pipe'">📐 保温管设计采购与施工进度基准对照</template>
                  <template v-else-if="fittingTab2SubView === 'baseline'">📐 管件设计与计划采购基准表</template>
                  <template v-else>🚚 管件全周期累计流转与现场库存表</template>
                </span>
                <span class="toolbar-count font-mono text-muted">
                  ({{ subMaterialType === 'pipe' ? aggregatedBaselineRows.length : (fittingTab2SubView === 'baseline' ? aggregatedFittingBaselineRows.length : aggregatedFittingFlowRows.length) }} 组聚合数据)
                </span>
              </div>

              <div class="toolbar-right">
                <!-- 聚合维度下拉触发与菜单 -->
                <div class="pivot-dropdown-wrap">
                  <button 
                    type="button" 
                    :class="['btn-pivot-trigger', { active: activePivotDropdown === 'baseline' }]"
                    @click.stop="togglePivotDropdown('baseline')"
                  >
                    <span class="trigger-icon">🎛️</span>
                    <span class="trigger-label">聚合维度:</span>
                    <span class="trigger-chain">{{ getDimensionChainText('baseline') }}</span>
                    <span class="trigger-arrow">▾</span>
                  </button>

                  <!-- 背景点击遮罩 -->
                  <div 
                    v-if="activePivotDropdown === 'baseline'" 
                    class="pivot-backdrop" 
                    @click.stop="closePivotDropdown"
                  ></div>

                  <!-- 浮层下拉列表面板 -->
                  <div 
                    v-if="activePivotDropdown === 'baseline'" 
                    class="pivot-dropdown-panel card elevated"
                    @click.stop
                  >
                    <div class="panel-header">
                      <span class="panel-title">选择透视维度（按勾选顺序依次分组）</span>
                      <button type="button" class="btn-panel-reset" @click="resetToDefaultDimensions('baseline')">↺ 恢复默认</button>
                    </div>

                    <!-- 维度有序多选列表 -->
                    <div class="panel-options-list">
                      <div 
                        v-for="dim in getAvailableDimensions('baseline')" 
                        :key="`base-opt-${dim.id}`"
                        :class="['panel-opt-item', { checked: isDimensionSelected('baseline', dim.id) }]"
                        @click="toggleDimensionSelection('baseline', dim.id)"
                      >
                        <div class="opt-badge-slot">
                          <span v-if="isDimensionSelected('baseline', dim.id)" class="badge-active-num">{{ getDimensionOrder('baseline', dim.id) }}</span>
                          <span v-else class="badge-unchecked"></span>
                        </div>
                        <span class="opt-name">{{ dim.label }}</span>
                        
                        <div v-if="isDimensionSelected('baseline', dim.id)" class="opt-order-btns" @click.stop>
                          <button 
                            type="button" 
                            class="btn-rank" 
                            :disabled="getDimensionOrder('baseline', dim.id) === 1"
                            title="提升此维度分组优先级"
                            @click="moveDimensionUp('baseline', dim.id)"
                          >
                            ↑
                          </button>
                          <button 
                            type="button" 
                            class="btn-rank" 
                            :disabled="getDimensionOrder('baseline', dim.id) === baselineDimensions.length"
                            title="降低此维度分组优先级"
                            @click="moveDimensionDown('baseline', dim.id)"
                          >
                            ↓
                          </button>
                        </div>
                      </div>
                    </div>

                    <!-- 常用快捷方案 -->
                    <div class="panel-presets-row">
                      <span class="presets-caption">⚡ 常用：</span>
                      <div class="presets-btn-chips">
                        <button
                          v-for="(p, pIdx) in baselineDimensionPresets"
                          :key="`p-base-${pIdx}`"
                          type="button"
                          :class="['btn-preset-chip', { active: isCurrentPreset('baseline', p.dims) }]"
                          @click="applyDimensionPreset('baseline', p.dims)"
                        >
                          {{ p.label }}
                        </button>
                      </div>
                    </div>

                    <div class="panel-footer">
                      <button type="button" class="btn-panel-done" @click="closePivotDropdown">完成</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="tabLoading" class="loading-box">
              <div class="spinner-sm"></div>
              <span>⏳ 正在检索基准量与进度数据...</span>
            </div>
            
            <!-- 表格容器 -->
            <div v-else class="table-container">
              <!-- 1. 保温管基准与进度对照表 -->
              <table v-if="subMaterialType === 'pipe'" class="data-table">
                <thead>
                  <tr>
                    <th 
                      v-for="dim in baselineDimensions" 
                      :key="`th-base-${dim}`"
                      :class="['text-left', 'th-dimension', `th-dim-${dim}`, 'sortable-th', { 'sorted-col': isColumnSorted('baseline_pipe', dim) }]"
                      @click="handleTableSort('baseline_pipe', dim)"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>{{ getDimensionDef(dim).colHeader }}</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', dim) }">{{ getSortIcon('baseline_pipe', dim) }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('baseline_pipe', 'design_qty') }" @click="handleTableSort('baseline_pipe', 'design_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>设计量 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', 'design_qty') }">{{ getSortIcon('baseline_pipe', 'design_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('baseline_pipe', 'purchase_plan_qty') }" @click="handleTableSort('baseline_pipe', 'purchase_plan_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>计划采购量 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', 'purchase_plan_qty') }">{{ getSortIcon('baseline_pipe', 'purchase_plan_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('baseline_pipe', 'total_shipped_qty') }" @click="handleTableSort('baseline_pipe', 'total_shipped_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>累计发货 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', 'total_shipped_qty') }">{{ getSortIcon('baseline_pipe', 'total_shipped_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('baseline_pipe', 'total_arrived_qty') }" @click="handleTableSort('baseline_pipe', 'total_arrived_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>累计到货 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', 'total_arrived_qty') }">{{ getSortIcon('baseline_pipe', 'total_arrived_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('baseline_pipe', 'total_usage_qty') }" @click="handleTableSort('baseline_pipe', 'total_usage_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>累计使用 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', 'total_usage_qty') }">{{ getSortIcon('baseline_pipe', 'total_usage_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('baseline_pipe', 'stock_qty') }" @click="handleTableSort('baseline_pipe', 'stock_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>现场库存 (米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', 'stock_qty') }">{{ getSortIcon('baseline_pipe', 'stock_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-left sortable-th" style="min-width: 140px;" :class="{ 'sorted-col': isColumnSorted('baseline_pipe', 'purchase_rate') }" @click="handleTableSort('baseline_pipe', 'purchase_rate')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell">
                        <span>采购到货进度</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', 'purchase_rate') }">{{ getSortIcon('baseline_pipe', 'purchase_rate') }}</span>
                      </div>
                    </th>
                    <th class="text-left sortable-th" style="min-width: 140px;" :class="{ 'sorted-col': isColumnSorted('baseline_pipe', 'install_rate') }" @click="handleTableSort('baseline_pipe', 'install_rate')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell">
                        <span>施工安装进度</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('baseline_pipe', 'install_rate') }">{{ getSortIcon('baseline_pipe', 'install_rate') }}</span>
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="aggregatedBaselineRows.length === 0">
                    <td :colspan="baselineDimensions.length + 8" class="empty-cell">未查询到保温管基准对照数据</td>
                  </tr>
                  <tr v-for="(row, idx) in sortedBaselinePipeRows" :key="idx">
                    <td 
                      v-for="dim in baselineDimensions" 
                      :key="`td-base-${dim}`"
                      :class="['text-left', `td-dim-${dim}`]"
                    >
                      <template v-if="dim === 'section'">
                        <span class="font-bold text-dark section-cell-text">{{ row.section_1_name }}</span>
                      </template>
                      <template v-else-if="dim === 'model'">
                        <span class="badge model-badge">{{ row.pipe_model_name }}</span>
                      </template>
                      <template v-else-if="dim === 'supplier'">
                        <span class="font-medium text-sky">{{ row.supplier_name }}</span>
                      </template>
                    </td>

                    <td class="text-right font-medium text-slate">{{ formatQty(row.design_qty) }}</td>
                    <td class="text-right font-medium text-slate">{{ formatQty(row.purchase_plan_qty) }}</td>
                    <td class="text-right font-medium text-sky">{{ formatQty(row.total_shipped_qty) }}</td>
                    <td class="text-right font-bold text-blue">{{ formatQty(row.total_arrived_qty) }}</td>
                    <td class="text-right font-bold text-emerald">{{ formatQty(row.total_usage_qty) }}</td>
                    <td class="text-right font-bold text-amber">{{ formatQty(row.stock_qty) }}</td>
                    <td class="text-left">
                      <div class="progress-wrap">
                        <div class="progress-bar-bg">
                          <div class="progress-bar-fill fill-blue" :style="{ width: `${Math.min(100, row.purchase_rate)}%` }"></div>
                        </div>
                        <span class="progress-text">{{ row.purchase_rate }}%</span>
                      </div>
                    </td>
                    <td class="text-left">
                      <div class="progress-wrap">
                        <div class="progress-bar-bg">
                          <div class="progress-bar-fill fill-emerald" :style="{ width: `${Math.min(100, row.install_rate)}%` }"></div>
                        </div>
                        <span class="progress-text">{{ row.install_rate }}%</span>
                      </div>
                    </td>
                  </tr>

                  <!-- 汇总行 -->
                  <tr v-if="aggregatedBaselineRows.length > 0" class="summary-footer-row">
                    <td :colspan="baselineDimensions.length" class="text-left">
                      📊 全项目基准与进度总量汇总 (已聚合为 {{ aggregatedBaselineRows.length }} 组)
                    </td>
                    <td class="text-right">{{ formatQty(baselinePipeSummary.total_design_qty) }}</td>
                    <td class="text-right">{{ formatQty(baselinePipeSummary.total_purchase_plan_qty) }}</td>
                    <td class="text-right text-sky">{{ formatQty(baselinePipeSummary.total_shipped_qty) }}</td>
                    <td class="text-right text-blue">{{ formatQty(baselinePipeSummary.total_arrived_qty) }}</td>
                    <td class="text-right text-emerald">{{ formatQty(baselinePipeSummary.total_usage_qty) }}</td>
                    <td class="text-right text-amber">{{ formatQty(baselinePipeSummary.total_stock_qty) }}</td>
                    <td class="text-left font-bold text-blue">{{ baselinePipeSummary.overall_purchase_rate }}%</td>
                    <td class="text-left font-bold text-emerald">{{ baselinePipeSummary.overall_install_rate }}%</td>
                  </tr>
                </tbody>
              </table>

              <!-- 2. 管件设计与计划采购基准表 (独立子表 1) -->
              <table v-else-if="fittingTab2SubView === 'baseline'" class="data-table">
                <thead>
                  <tr>
                    <th 
                      v-for="dim in baselineDimensions" 
                      :key="`th-base-fit-d-${dim}`"
                      :class="['text-left', 'th-dimension', `th-dim-${dim}`, 'sortable-th', { 'sorted-col': isColumnSorted('fitting_baseline', dim) }]"
                      @click="handleTableSort('fitting_baseline', dim)"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>{{ getDimensionDef(dim).colHeader }}</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_baseline', dim) }">{{ getSortIcon('fitting_baseline', dim) }}</span>
                      </div>
                    </th>
                    <th class="text-center sortable-th" style="width: 80px;" :class="{ 'sorted-col': isColumnSorted('fitting_baseline', 'unit') }" @click="handleTableSort('fitting_baseline', 'unit')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-center">
                        <span>单位</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_baseline', 'unit') }">{{ getSortIcon('fitting_baseline', 'unit') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('fitting_baseline', 'design_qty') }" @click="handleTableSort('fitting_baseline', 'design_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>设计使用量</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_baseline', 'design_qty') }">{{ getSortIcon('fitting_baseline', 'design_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('fitting_baseline', 'purchase_plan_qty') }" @click="handleTableSort('fitting_baseline', 'purchase_plan_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>计划采购量</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_baseline', 'purchase_plan_qty') }">{{ getSortIcon('fitting_baseline', 'purchase_plan_qty') }}</span>
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="aggregatedFittingBaselineRows.length === 0">
                    <td :colspan="baselineDimensions.length + 3" class="empty-cell">未查询到管件基准数据</td>
                  </tr>
                  <tr v-for="(row, idx) in sortedFittingBaselineRows" :key="`fit-base-${idx}`">
                    <td 
                      v-for="dim in baselineDimensions" 
                      :key="`td-fit-base-${dim}`"
                      :class="['text-left', `td-dim-${dim}`]"
                    >
                      <template v-if="dim === 'section'">
                        <span class="font-bold text-dark section-cell-text">{{ row.section_1_name }}</span>
                      </template>
                      <template v-else-if="dim === 'model'">
                        <span class="font-bold text-slate">{{ row.fitting_type || row.standard_name || row.category }}</span>
                        <span class="font-medium text-muted" style="margin-left: 6px;">{{ row.model_spec }}</span>
                        <span v-if="row.sub_model_spec" class="badge-sub-model">{{ row.sub_model_spec }}</span>
                      </template>
                      <template v-else-if="dim === 'supplier'">
                        <span class="text-muted">（设计基准）</span>
                      </template>
                    </td>

                    <td class="text-center text-muted font-medium">{{ row.unit || '个' }}</td>
                    <td class="text-right font-medium text-dark">{{ Number(row.design_qty).toLocaleString() }}</td>
                    <td class="text-right font-bold text-slate">{{ Number(row.purchase_plan_qty).toLocaleString() }}</td>
                  </tr>

                  <!-- 汇总行 -->
                  <tr v-if="aggregatedFittingBaselineRows.length > 0" class="summary-footer-row">
                    <td :colspan="baselineDimensions.length" class="text-left">
                      📐 全项目管件设计与计划采购基准汇总 (已聚合为 {{ aggregatedFittingBaselineRows.length }} 组)
                    </td>
                    <td class="text-center text-muted">—</td>
                    <td class="text-right font-bold">{{ baselineFittingSummary.total_design_qty.toLocaleString() }}</td>
                    <td class="text-right font-bold text-blue">{{ baselineFittingSummary.total_purchase_plan_qty.toLocaleString() }}</td>
                  </tr>
                </tbody>
              </table>

              <!-- 3. 管件全周期累计流转与现场库存表 (独立子表 2) -->
              <table v-else class="data-table">
                <thead>
                  <tr>
                    <th 
                      v-for="dim in baselineDimensions" 
                      :key="`th-flow-fit-d-${dim}`"
                      :class="['text-left', 'th-dimension', `th-dim-${dim}`, 'sortable-th', { 'sorted-col': isColumnSorted('fitting_flow', dim) }]"
                      @click="handleTableSort('fitting_flow', dim)"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>{{ getDimensionDef(dim).colHeader }}</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_flow', dim) }">{{ getSortIcon('fitting_flow', dim) }}</span>
                      </div>
                    </th>
                    <th class="text-center sortable-th" style="width: 80px;" :class="{ 'sorted-col': isColumnSorted('fitting_flow', 'unit') }" @click="handleTableSort('fitting_flow', 'unit')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-center">
                        <span>单位</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_flow', 'unit') }">{{ getSortIcon('fitting_flow', 'unit') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('fitting_flow', 'total_shipped_qty') }" @click="handleTableSort('fitting_flow', 'total_shipped_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>累计发货量</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_flow', 'total_shipped_qty') }">{{ getSortIcon('fitting_flow', 'total_shipped_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('fitting_flow', 'total_arrived_qty') }" @click="handleTableSort('fitting_flow', 'total_arrived_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>累计到货量</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_flow', 'total_arrived_qty') }">{{ getSortIcon('fitting_flow', 'total_arrived_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('fitting_flow', 'total_usage_qty') }" @click="handleTableSort('fitting_flow', 'total_usage_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>现场安装量</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_flow', 'total_usage_qty') }">{{ getSortIcon('fitting_flow', 'total_usage_qty') }}</span>
                      </div>
                    </th>
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('fitting_flow', 'stock_qty') }" @click="handleTableSort('fitting_flow', 'stock_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>现场库存余量</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('fitting_flow', 'stock_qty') }">{{ getSortIcon('fitting_flow', 'stock_qty') }}</span>
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="aggregatedFittingFlowRows.length === 0">
                    <td :colspan="baselineDimensions.length + 5" class="empty-cell">未查询到管件发运或流转记录</td>
                  </tr>
                  <tr v-for="(row, idx) in sortedFittingFlowRows" :key="`fit-flow-${idx}`">
                    <td 
                      v-for="dim in baselineDimensions" 
                      :key="`td-fit-flow-${dim}`"
                      :class="['text-left', `td-dim-${dim}`]"
                    >
                      <template v-if="dim === 'section'">
                        <span class="font-bold text-dark section-cell-text">{{ row.section_1_name }}</span>
                      </template>
                      <template v-else-if="dim === 'model'">
                        <span class="font-bold text-slate">{{ row.fitting_type }}</span>
                        <span class="font-medium text-muted" style="margin-left: 6px;">{{ row.model_spec }}</span>
                      </template>
                      <template v-else-if="dim === 'supplier'">
                        <span class="font-medium text-sky">{{ row.supplier_name }}</span>
                      </template>
                    </td>

                    <td class="text-center text-muted font-medium">件</td>
                    <td class="text-right font-medium text-sky">{{ Number(row.total_shipped_qty).toLocaleString() }}</td>
                    <td class="text-right font-bold text-blue">{{ Number(row.total_arrived_qty).toLocaleString() }}</td>
                    <td class="text-right font-bold text-emerald">{{ Number(row.total_usage_qty).toLocaleString() }}</td>
                    <td class="text-right font-bold text-amber">{{ Number(row.stock_qty).toLocaleString() }}</td>
                  </tr>

                  <!-- 汇总行 -->
                  <tr v-if="aggregatedFittingFlowRows.length > 0" class="summary-footer-row">
                    <td :colspan="baselineDimensions.length" class="text-left">
                      🚚 全项目管件全周期流转与现场库存汇总 (已聚合为 {{ aggregatedFittingFlowRows.length }} 组)
                    </td>
                    <td class="text-center text-muted">—</td>
                    <td class="text-right font-bold text-sky">{{ baselineFittingSummary.total_shipped_qty.toLocaleString() }}</td>
                    <td class="text-right font-bold text-blue">{{ baselineFittingSummary.total_arrived_qty.toLocaleString() }}</td>
                    <td class="text-right font-bold text-emerald">{{ baselineFittingSummary.total_usage_qty.toLocaleString() }}</td>
                    <td class="text-right font-bold text-amber">{{ baselineFittingSummary.total_stock_qty.toLocaleString() }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- ==================================================================== -->
        <!-- 🏢 Tab 3: 责任主体与人员管辖速查矩阵 (可折叠分组架构 + 按标段视图) -->
        <!-- ==================================================================== -->
        <section v-else-if="activeTab === 'directory'" class="tab-content-section">
          <!-- 顶栏快捷操作区：模式切换器 + 分类胶囊 / 折叠按钮 -->
          <div class="directory-top-toolbar">
            <!-- 视图模式切换器 -->
            <div class="view-mode-toggle-group">
              <button 
                type="button" 
                :class="['mode-toggle-btn', { active: directoryViewMode === 'by_category' }]"
                @click="directoryViewMode = 'by_category'"
              >
                🏢 按主体类别分组
              </button>
              <button 
                type="button" 
                :class="['mode-toggle-btn', { active: directoryViewMode === 'by_section' }]"
                @click="directoryViewMode = 'by_section'"
              >
                🏗️ 按标段综合穿透
              </button>
            </div>

            <!-- 模式A下的分类胶囊 -->
            <div v-if="directoryViewMode === 'by_category'" class="sub-pill-bar">
              <button 
                type="button" 
                :class="['sub-pill', { active: directoryCategory === 'all' }]"
                @click="directoryCategory = 'all'"
              >
                全部主体 ({{ totalDirectoryCount }})
              </button>
              <button 
                type="button" 
                :class="['sub-pill', { active: directoryCategory === 'suppliers' }]"
                @click="directoryCategory = 'suppliers'"
              >
                🏭 供货厂家 ({{ filteredSuppliers.length }})
              </button>
              <button 
                type="button" 
                :class="['sub-pill', { active: directoryCategory === 'site_managers' }]"
                @click="directoryCategory = 'site_managers'"
              >
                👷 现场负责人 ({{ filteredSiteManagers.length }})
              </button>
              <button 
                type="button" 
                :class="['sub-pill', { active: directoryCategory === 'demand_sections' }]"
                @click="directoryCategory = 'demand_sections'"
              >
                🏗️ 施工单位 ({{ filteredDemandSections.length }})
              </button>
              <button 
                type="button" 
                :class="['sub-pill', { active: directoryCategory === 'warehouse_keepers' }]"
                @click="directoryCategory = 'warehouse_keepers'"
              >
                📦 物资库管 ({{ filteredWarehouseKeepers.length }})
              </button>
              <button 
                type="button" 
                :class="['sub-pill', { active: directoryCategory === 'global_members' }]"
                @click="directoryCategory = 'global_members'"
              >
                👥 系统管理 ({{ filteredGlobalMembers.length }})
              </button>
            </div>

            <!-- 模式A下的全局展开折叠 -->
            <div v-if="directoryViewMode === 'by_category'" class="group-collapse-controls">
              <button type="button" class="btn btn-sm btn-ghost" @click="expandAllGroups">
                📖 展开全部
              </button>
              <button type="button" class="btn btn-sm btn-ghost" @click="collapseAllGroups">
                📕 折叠全部
              </button>
            </div>

            <!-- 模式B下的状态徽章与折叠控制 -->
            <div v-else class="section-view-controls">
              <span class="summary-pill">⚡ {{ sectionEntityMatrix.length }} 个标段全息贯通</span>
              <div class="group-collapse-controls">
                <button type="button" class="btn btn-sm btn-ghost" @click="expandAllSections">
                  📖 展开全部标段
                </button>
                <button type="button" class="btn btn-sm btn-ghost" @click="collapseAllSections">
                  📕 折叠全部标段
                </button>
              </div>
            </div>
          </div>

          <div v-if="tabLoading" class="loading-box">
            <div class="spinner-sm"></div>
            <span>⏳ 正在加载主体与账号管辖矩阵...</span>
          </div>
          
          <!-- ================================================================ -->
          <!-- 模式 A: 按主体类别分组 (手风琴折叠) -->
          <!-- ================================================================ -->
          <div v-else-if="directoryViewMode === 'by_category'" class="directory-accordion-layout">
            <!-- 1. 🏭 供货厂家分组 -->
            <div 
              v-if="directoryCategory === 'all' || directoryCategory === 'suppliers'" 
              class="card accordion-group-card"
            >
              <div 
                class="accordion-header" 
                @click="toggleGroupCollapse('suppliers')"
              >
                <div class="accordion-title-left">
                  <span class="group-icon">🏭</span>
                  <span class="group-title">供货厂家</span>
                  <span class="badge badge-supplier">{{ filteredSuppliers.length }} 家</span>
                  <span class="group-desc">负责保温直管与管件生产、车辆装运与物流调度</span>
                </div>
                <div class="accordion-toggle-arrow">
                  <span>{{ groupCollapseState.suppliers ? '▼ 展开' : '▲ 收起' }}</span>
                </div>
              </div>

              <div v-show="!groupCollapseState.suppliers" class="accordion-body">
                <div v-if="filteredSuppliers.length === 0" class="group-empty-tip">未查询到符合条件的供货厂家。</div>
                <div v-else class="directory-cards-grid">
                  <div 
                    v-for="(sup, idx) in filteredSuppliers" 
                    :key="`sup-${idx}`" 
                    class="compact-entity-card"
                  >
                    <div class="card-header-row">
                      <div class="card-title-group">
                        <span class="card-main-title">{{ sup.entity_name }}</span>
                        <span class="card-sub-title">{{ sup.entity_id }}</span>
                      </div>
                      <span class="category-badge badge-supplier">供货厂家</span>
                    </div>

                    <div class="card-body-compact">
                      <div class="contact-highlight-row">
                        <span class="contact-person">👤 {{ sup.contact_name }}</span>
                        <span 
                          v-if="sup.contact_phone && sup.contact_phone !== '—'" 
                          class="contact-phone-btn" 
                          title="点击复制电话号码"
                          @click="copyPhone(sup.contact_phone)"
                        >
                          📞 {{ sup.contact_phone }} <span class="copy-icon">📋</span>
                        </span>
                        <span v-else class="text-muted font-mono">📞 内部协调</span>
                      </div>

                      <div class="scope-row">
                        <span class="scope-label">📍 供应：</span>
                        <span class="scope-tags">
                          <template v-if="sup.managed_sections && sup.managed_sections.length">
                            <span 
                              v-for="(sec, sIdx) in sup.managed_sections" 
                              :key="sIdx" 
                              class="scope-chip"
                            >
                              {{ sec }}
                            </span>
                          </template>
                          <span v-else class="scope-chip chip-unassigned">暂未分配供应标段</span>
                        </span>
                      </div>

                      <div class="extra-info-row">
                        <span class="extra-label">🔑 调度账号: {{ sup.accounts.join(', ') }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 2. 👷 现场负责人分组 -->
            <div 
              v-if="directoryCategory === 'all' || directoryCategory === 'site_managers'" 
              class="card accordion-group-card"
            >
              <div 
                class="accordion-header" 
                @click="toggleGroupCollapse('site_managers')"
              >
                <div class="accordion-title-left">
                  <span class="group-icon">👷</span>
                  <span class="group-title">现场负责人</span>
                  <span class="badge badge-manager">{{ filteredSiteManagers.length }} 人</span>
                  <span class="group-desc">负责现场施工组织、进度协调调度与供需对接</span>
                </div>
                <div class="accordion-toggle-arrow">
                  <span>{{ groupCollapseState.site_managers ? '▼ 展开' : '▲ 收起' }}</span>
                </div>
              </div>

              <div v-show="!groupCollapseState.site_managers" class="accordion-body">
                <div v-if="filteredSiteManagers.length === 0" class="group-empty-tip">未查询到符合条件的现场负责人。</div>
                <div v-else class="directory-cards-grid">
                  <div 
                    v-for="(m, idx) in filteredSiteManagers" 
                    :key="`mgr-${idx}`" 
                    class="compact-entity-card"
                  >
                    <div class="card-header-row">
                      <div class="card-title-group">
                        <span class="card-main-title">{{ m.person_name }}</span>
                        <span class="card-sub-title">{{ m.is_global ? '全标段总调度' : '标段责任人' }}</span>
                      </div>
                      <span class="category-badge badge-manager">现场负责人</span>
                    </div>

                    <div class="card-body-compact">
                      <div class="contact-highlight-row">
                        <span class="contact-person">👤 {{ m.contact_name }}</span>
                        <span 
                          v-if="m.contact_phone && m.contact_phone !== '—'" 
                          class="contact-phone-btn" 
                          title="点击复制电话号码"
                          @click="copyPhone(m.contact_phone)"
                        >
                          📞 {{ m.contact_phone }} <span class="copy-icon">📋</span>
                        </span>
                        <span v-else class="text-muted font-mono">📞 内部协调</span>
                      </div>

                      <div class="scope-row">
                        <span class="scope-label">📍 管辖：</span>
                        <span class="scope-tags">
                          <template v-if="m.managed_sections && m.managed_sections.length && !m.is_global">
                            <span 
                              v-for="(sec, sIdx) in m.managed_sections" 
                              :key="sIdx" 
                              class="scope-chip"
                            >
                              {{ sec }}
                            </span>
                          </template>
                          <span v-else class="scope-chip chip-global">{{ m.scope_desc }}</span>
                        </span>
                      </div>

                      <div class="extra-info-row">
                        <span class="extra-label">🏢 职责: {{ m.is_global ? '集团现场总调度与全线统筹' : `负责 ${m.scope_desc} 现场管理` }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 3. 🏗️ 施工单位分组 -->
            <div 
              v-if="directoryCategory === 'all' || directoryCategory === 'demand_sections'" 
              class="card accordion-group-card"
            >
              <div 
                class="accordion-header" 
                @click="toggleGroupCollapse('demand_sections')"
              >
                <div class="accordion-title-left">
                  <span class="group-icon">🏗️</span>
                  <span class="group-title">施工单位</span>
                  <span class="badge badge-section">{{ filteredDemandSections.length }} 家单位</span>
                  <span class="group-desc">已明确签约施工单位的企业与管辖标段，空缺标段暂不列出</span>
                </div>
                <div class="accordion-toggle-arrow">
                  <span>{{ groupCollapseState.demand_sections ? '▼ 展开' : '▲ 收起' }}</span>
                </div>
              </div>

              <div v-show="!groupCollapseState.demand_sections" class="accordion-body">
                <div v-if="filteredDemandSections.length === 0" class="group-empty-tip">当前选定标段暂未配置施工企业。</div>
                <div v-else class="directory-cards-grid">
                  <div 
                    v-for="(sec, idx) in filteredDemandSections" 
                    :key="`sec-${idx}`" 
                    class="compact-entity-card"
                  >
                    <div class="card-header-row">
                      <div class="card-title-group">
                        <span class="card-main-title">{{ sec.section_1_name }}</span>
                        <span class="card-sub-title">{{ sec.construction_unit_name }}</span>
                      </div>
                      <span class="category-badge badge-section">施工单位</span>
                    </div>

                    <div class="card-body-compact">
                      <div class="contact-highlight-row">
                        <span class="contact-person">👤 {{ sec.contact_name }}</span>
                        <span 
                          v-if="sec.contact_phone && sec.contact_phone !== '—'" 
                          class="contact-phone-btn" 
                          title="点击复制电话号码"
                          @click="copyPhone(sec.contact_phone)"
                        >
                          📞 {{ sec.contact_phone }} <span class="copy-icon">📋</span>
                        </span>
                        <span v-else class="text-muted font-mono">📞 内部协调</span>
                      </div>

                      <div class="scope-row">
                        <span class="scope-label">📍 标段：</span>
                        <span class="scope-tags">
                          <span class="scope-chip">{{ sec.section_1_name }}</span>
                        </span>
                      </div>

                      <div class="extra-info-row">
                        <span class="extra-label">🏢 单位: {{ sec.construction_unit_name }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 4. 📦 物资仓储与库管核验人员分组 -->
            <div 
              v-if="directoryCategory === 'all' || directoryCategory === 'warehouse_keepers'" 
              class="card accordion-group-card"
            >
              <div 
                class="accordion-header" 
                @click="toggleGroupCollapse('warehouse_keepers')"
              >
                <div class="accordion-title-left">
                  <span class="group-icon">📦</span>
                  <span class="group-title">物资仓储与库管核验人员</span>
                  <span class="badge badge-keeper">{{ filteredWarehouseKeepers.length }} 人</span>
                  <span class="group-desc">负责现场物资到货二次核验、整车台账确认与物资管理</span>
                </div>
                <div class="accordion-toggle-arrow">
                  <span>{{ groupCollapseState.warehouse_keepers ? '▼ 展开' : '▲ 收起' }}</span>
                </div>
              </div>

              <div v-show="!groupCollapseState.warehouse_keepers" class="accordion-body">
                <div v-if="filteredWarehouseKeepers.length === 0" class="group-empty-tip">未查询到符合条件的库管人员。</div>
                <div v-else class="directory-cards-grid">
                  <div 
                    v-for="(wh, idx) in filteredWarehouseKeepers" 
                    :key="`wh-${idx}`" 
                    class="compact-entity-card"
                  >
                    <div class="card-header-row">
                      <div class="card-title-group">
                        <span class="card-main-title">{{ wh.person_name }} (库管员)</span>
                        <span class="card-sub-title">{{ wh.is_global ? '全项目物资总库' : '标段物资核验' }}</span>
                      </div>
                      <span class="category-badge badge-keeper">物资库管</span>
                    </div>

                    <div class="card-body-compact">
                      <div class="contact-highlight-row">
                        <span class="contact-person">👤 {{ wh.person_name }}</span>
                        <span 
                          v-if="wh.contact_phone && wh.contact_phone !== '—'" 
                          class="contact-phone-btn" 
                          title="点击复制电话号码"
                          @click="copyPhone(wh.contact_phone)"
                        >
                          📞 {{ wh.contact_phone }} <span class="copy-icon">📋</span>
                        </span>
                        <span v-else class="text-muted font-mono">📞 内部协调</span>
                      </div>

                      <div class="scope-row">
                        <span class="scope-label">📍 库区：</span>
                        <span class="scope-tags">
                          <template v-if="wh.managed_sections && wh.managed_sections.length && !wh.is_global">
                            <span 
                              v-for="(sec, sIdx) in wh.managed_sections" 
                              :key="sIdx" 
                              class="scope-chip"
                            >
                              {{ sec }}
                            </span>
                          </template>
                          <span v-else class="scope-chip chip-global">{{ wh.scope_desc }}</span>
                        </span>
                      </div>

                      <div class="extra-info-row">
                        <span class="extra-label">🔑 系统账号: {{ wh.username }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 5. 👥 系统管理与全局调度分组 -->
            <div 
              v-if="directoryCategory === 'all' || directoryCategory === 'global_members'" 
              class="card accordion-group-card"
            >
              <div 
                class="accordion-header" 
                @click="toggleGroupCollapse('global_members')"
              >
                <div class="accordion-title-left">
                  <span class="group-icon">👥</span>
                  <span class="group-title">系统管理与全局调度观察员</span>
                  <span class="badge badge-global">{{ filteredGlobalMembers.length }} 人</span>
                  <span class="group-desc">集团指挥部、系统超管与全局数据透视账号</span>
                </div>
                <div class="accordion-toggle-arrow">
                  <span>{{ groupCollapseState.global_members ? '▼ 展开' : '▲ 收起' }}</span>
                </div>
              </div>

              <div v-show="!groupCollapseState.global_members" class="accordion-body">
                <div class="directory-cards-grid">
                  <div 
                    v-for="(gm, idx) in filteredGlobalMembers" 
                    :key="`gm-${idx}`" 
                    class="compact-entity-card"
                  >
                    <div class="card-header-row">
                      <div class="card-title-group">
                        <span class="card-main-title">{{ gm.username }}</span>
                        <span class="card-sub-title">{{ gm.role_name }}</span>
                      </div>
                      <span class="category-badge badge-global">{{ gm.category }}</span>
                    </div>

                    <div class="card-body-compact">
                      <div class="contact-highlight-row">
                        <span class="contact-person">👤 {{ gm.contact_name }}</span>
                        <span class="text-muted font-mono">📞 集团专线</span>
                      </div>

                      <div class="scope-row">
                        <span class="scope-label">📍 权限：</span>
                        <span class="scope-tags">
                          <span class="scope-chip chip-global">全网全局透视</span>
                        </span>
                      </div>

                      <div class="extra-info-row">
                        <span class="extra-label">🏢 {{ gm.scope_desc }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>

          <!-- ================================================================ -->
          <!-- 模式 B: 🏗️ 按标段综合穿透视图 (标段矩阵卡片) -->
          <!-- ================================================================ -->
          <div v-else class="section-matrix-layout">
            <div v-if="sectionEntityMatrix.length === 0" class="empty-box">
              未查询到符合当前条件的标段责任矩阵数据。
            </div>

            <!-- 各标段卡片网格 -->
            <div v-else class="section-matrix-grid">
              <div 
                v-for="sec in sectionEntityMatrix" 
                :key="sec.section_1_id" 
                class="card section-matrix-card"
              >
                <!-- 标段卡片标题栏 (支持点击折叠/展开) -->
                <div class="sec-card-header" @click="toggleSectionCollapse(sec.section_1_id)">
                  <div class="sec-title-wrap">
                    <span class="sec-badge-icon">🏗️</span>
                    <span class="sec-title-text">{{ sec.section_1_name }}</span>
                    <span class="sec-id-tag">{{ sec.section_1_id }}</span>
                  </div>
                  <div class="sec-header-right">
                    <div class="sec-summary-badges">
                      <span class="badge badge-supplier">{{ sec.suppliers.length }} 厂家</span>
                      <span class="badge badge-manager">{{ sec.site_managers.length }} 负责人</span>
                      <span class="badge badge-section">{{ sec.construction_units.length }} 施工</span>
                      <span class="badge badge-keeper">{{ sec.warehouse_keepers.length }} 库管</span>
                    </div>
                    <span class="sec-toggle-arrow">
                      {{ sectionCollapseState[sec.section_1_id] ? '▼ 展开' : '▲ 收起' }}
                    </span>
                  </div>
                </div>

                <!-- 标段内部 4 大角色网格区 -->
                <div v-show="!sectionCollapseState[sec.section_1_id]" class="sec-card-roles-grid">
                  <!-- 1. 🏭 供货厂家 -->
                  <div class="role-column-block">
                    <div class="role-block-header role-hdr-supplier">
                      <span>🏭 供货厂家 ({{ sec.suppliers.length }})</span>
                    </div>
                    <div class="role-block-content">
                      <div v-if="sec.suppliers.length === 0" class="role-empty-text text-muted">暂未指定供货厂家</div>
                      <div 
                        v-for="(sup, sIdx) in sec.suppliers" 
                        :key="`sec-sup-${sIdx}`" 
                        class="role-person-item"
                      >
                        <span class="role-main-name">{{ sup.entity_name }}</span>
                        <div class="role-contact-line">
                          <span class="text-slate font-medium">👤 {{ sup.contact_name }}</span>
                          <span 
                            v-if="sup.contact_phone && sup.contact_phone !== '—'" 
                            class="phone-copy-link" 
                            title="点击复制电话"
                            @click.stop="copyPhone(sup.contact_phone)"
                          >
                            📞 {{ sup.contact_phone }} 📋
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 2. 👷 现场负责人 -->
                  <div class="role-column-block">
                    <div class="role-block-header role-hdr-manager">
                      <span>👷 现场负责人 ({{ sec.site_managers.length }})</span>
                    </div>
                    <div class="role-block-content">
                      <div v-if="sec.site_managers.length === 0" class="role-empty-text">由集团现场总调度协调</div>
                      <div 
                        v-for="(mgr, mIdx) in sec.site_managers" 
                        :key="`sec-mgr-${mIdx}`" 
                        class="role-person-item"
                      >
                        <span class="role-main-name">{{ mgr.person_name }}</span>
                        <div class="role-contact-line">
                          <span 
                            v-if="mgr.contact_phone && mgr.contact_phone !== '—'" 
                            class="phone-copy-link" 
                            title="点击复制电话"
                            @click.stop="copyPhone(mgr.contact_phone)"
                          >
                            📞 {{ mgr.contact_phone }} 📋
                          </span>
                          <span v-else class="text-muted font-mono">📞 内部协同</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 3. 🏗️ 施工单位 -->
                  <div class="role-column-block">
                    <div class="role-block-header role-hdr-construction">
                      <span>🏗️ 施工单位 ({{ sec.construction_units.length }})</span>
                    </div>
                    <div class="role-block-content">
                      <div v-if="sec.construction_units.length === 0" class="role-empty-text text-muted">暂未签约配置施工企业</div>
                      <div 
                        v-for="(cUnit, cIdx) in sec.construction_units" 
                        :key="`sec-con-${cIdx}`" 
                        class="role-person-item"
                      >
                        <span class="role-main-name text-indigo">{{ cUnit.construction_unit_name }}</span>
                        <div class="role-contact-line">
                          <span class="text-slate font-medium">👤 {{ cUnit.contact_name }}</span>
                          <span 
                            v-if="cUnit.contact_phone && cUnit.contact_phone !== '—'" 
                            class="phone-copy-link" 
                            title="点击复制电话"
                            @click.stop="copyPhone(cUnit.contact_phone)"
                          >
                            📞 {{ cUnit.contact_phone }} 📋
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 4. 📦 物资库管人员 -->
                  <div class="role-column-block">
                    <div class="role-block-header role-hdr-keeper">
                      <span>📦 物资库管 ({{ sec.warehouse_keepers.length }})</span>
                    </div>
                    <div class="role-block-content">
                      <div v-if="sec.warehouse_keepers.length === 0" class="role-empty-text">由全项目总库协调</div>
                      <div 
                        v-for="(wh, wIdx) in sec.warehouse_keepers" 
                        :key="`sec-wh-${wIdx}`" 
                        class="role-person-item"
                      >
                        <span class="role-main-name text-amber">{{ wh.person_name }}</span>
                        <div class="role-contact-line">
                          <span 
                            v-if="wh.contact_phone && wh.contact_phone !== '—'" 
                            class="phone-copy-link" 
                            title="点击复制电话"
                            @click.stop="copyPhone(wh.contact_phone)"
                          >
                            📞 {{ wh.contact_phone }} 📋
                          </span>
                          <span v-else class="text-muted font-mono">📞 内部协调</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 额外专门展示：🌐 全网统筹与指挥观察人员 (全局角色) -->
            <div class="card global-dispatch-card">
              <div class="global-card-header">
                <div class="global-title-left">
                  <span class="global-icon">🌐</span>
                  <span class="global-title">全网统筹协调与指挥观察人员 (全局角色)</span>
                  <span class="badge badge-global">{{ globalPersonnel.totalCount }} 人</span>
                  <span class="global-desc">负责全网总协调、物资总库管理与全局数据透视指挥</span>
                </div>
              </div>

              <div class="global-card-body-grid">
                <!-- 1. 集团现场总调度主管 -->
                <div class="global-role-col">
                  <span class="global-col-title">👑 集团现场总调度 ({{ globalPersonnel.managers.length }}人)</span>
                  <div class="global-tags-list">
                    <div 
                      v-for="(gm, gIdx) in globalPersonnel.managers" 
                      :key="`gm-${gIdx}`"
                      class="global-person-item"
                    >
                      <span class="font-bold text-dark">👤 {{ gm.person_name }}</span>
                      <span 
                        v-if="gm.contact_phone && gm.contact_phone !== '—'" 
                        class="phone-copy-link" 
                        @click="copyPhone(gm.contact_phone)"
                      >
                        📞 {{ gm.contact_phone }} 📋
                      </span>
                    </div>
                  </div>
                </div>

                <!-- 2. 供给侧全局管理 -->
                <div class="global-role-col" v-if="globalPersonnel.suppliers.length > 0">
                  <span class="global-col-title">🏭 供给侧全局管理 ({{ globalPersonnel.suppliers.length }}人)</span>
                  <div class="global-tags-list">
                    <div 
                      v-for="(gs, sIdx) in globalPersonnel.suppliers" 
                      :key="`gs-${sIdx}`"
                      class="global-person-item"
                    >
                      <span class="font-bold text-dark">👤 {{ gs.contact_name }} ({{ gs.entity_name }})</span>
                      <span 
                        v-if="gs.contact_phone && gs.contact_phone !== '—'" 
                        class="phone-copy-link" 
                        title="点击复制电话"
                        @click="copyPhone(gs.contact_phone)"
                      >
                        📞 {{ gs.contact_phone }} 📋
                      </span>
                      <span v-else class="text-muted font-mono">📞 调度专线</span>
                    </div>
                  </div>
                </div>

                <!-- 3. 全局物资总库管 -->
                <div class="global-role-col">
                  <span class="global-col-title">📦 物资总库管理 ({{ globalPersonnel.keepers.length }}人)</span>
                  <div class="global-tags-list">
                    <div 
                      v-for="(gw, wIdx) in globalPersonnel.keepers" 
                      :key="`gw-${wIdx}`"
                      class="global-person-item"
                    >
                      <span class="font-bold text-dark">👤 {{ gw.person_name }}</span>
                      <span 
                        v-if="gw.contact_phone && gw.contact_phone !== '—'" 
                        class="phone-copy-link" 
                        @click="copyPhone(gw.contact_phone)"
                      >
                        📞 {{ gw.contact_phone }} 📋
                      </span>
                    </div>
                  </div>
                </div>

                <!-- 4. 超管与全局观察员 -->
                <div class="global-role-col">
                  <span class="global-col-title">👥 系统管理与指挥观察 ({{ globalPersonnel.members.length }}人)</span>
                  <div class="global-tags-list">
                    <div 
                      v-for="(mem, mIdx) in globalPersonnel.members" 
                      :key="`mem-${mIdx}`"
                      class="global-person-item"
                    >
                      <span class="font-bold text-dark">🔑 {{ mem.username }} ({{ mem.role_name }})</span>
                      <span class="text-muted font-mono">📞 集团专线</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

      </div>
    </main>

    <!-- 弹窗：每日保温管明细详情 Modal -->
    <Transition name="fade">
      <div v-if="pipeDetailModalVisible && pipeDetailModalData" class="block-modal-overlay" @click.self="pipeDetailModalVisible = false">
        <div class="block-modal-container modal-lg">
          <div class="block-modal-header bg-sky">
            <span class="modal-header-icon">📊</span>
            <div>
              <h3 class="modal-title">保温管日流转明细穿透</h3>
              <p class="modal-sub">
                日期：{{ pipeDetailModalData.biz_date }} | 标段：{{ pipeDetailModalData.section_1_name }} | 型号：{{ pipeDetailModalData.pipe_model_name }}
              </p>
            </div>
          </div>

          <div class="modal-body">
            <div class="detail-flow-chain">
              <div class="chain-step">
                <span class="step-lbl">1. 计划量</span>
                <span class="step-val text-slate">{{ formatQty(pipeDetailModalData.plan_qty) }} 米</span>
              </div>
              <div class="chain-arrow">➔</div>
              <div class="chain-step">
                <span class="step-lbl">2. 供给发货</span>
                <span class="step-val text-sky">{{ formatQty(pipeDetailModalData.shipped_qty) }} 米</span>
              </div>
              <div class="chain-arrow">➔</div>
              <div class="chain-step">
                <span class="step-lbl">3. 确认到货</span>
                <span class="step-val text-blue">{{ formatQty(pipeDetailModalData.arrived_qty) }} 米</span>
              </div>
              <div class="chain-arrow">➔</div>
              <div class="chain-step">
                <span class="step-lbl">4. 施工接收</span>
                <span class="step-val text-indigo">{{ formatQty(pipeDetailModalData.received_qty) }} 米</span>
              </div>
              <div class="chain-arrow">➔</div>
              <div class="chain-step">
                <span class="step-lbl">5. 现场安装</span>
                <span class="step-val text-emerald">{{ formatQty(pipeDetailModalData.usage_qty) }} 米</span>
              </div>
              <div class="chain-arrow">➔</div>
              <div class="chain-step">
                <span class="step-lbl">6. 库管已确认</span>
                <span class="step-val text-amber">{{ formatQty(pipeDetailModalData.warehouse_qty) }} 米</span>
              </div>
            </div>

            <div class="modal-metrics-grid">
              <div class="metric-item">
                <span class="lbl">履约到货率</span>
                <span class="val font-bold text-blue">{{ pipeDetailModalData.fulfillment_rate }}%</span>
              </div>
              <div class="metric-item">
                <span class="lbl">安装转化率</span>
                <span class="val font-bold text-emerald">{{ pipeDetailModalData.conversion_rate }}%</span>
              </div>
              <div class="metric-item">
                <span class="lbl">施工损耗量</span>
                <span class="val font-bold text-rose">{{ formatQty(pipeDetailModalData.loss_qty) }} 米</span>
              </div>
              <div class="metric-item">
                <span class="lbl">平均在途时间</span>
                <span class="val font-mono">{{ pipeDetailModalData.avg_transit_display }}</span>
              </div>
            </div>
          </div>

          <div class="block-modal-actions">
            <button type="button" class="btn secondary" @click="pipeDetailModalVisible = false">关闭窗口</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { AppHeader, Breadcrumbs } from './shared'
import * as XLSX from 'xlsx-js-style'

import {
  fetchTubeConfig,
  getComprehensiveDailyFlow,
  getComprehensiveBaselineProgress,
  getComprehensiveEntityDirectory,
} from '@/projects/daily_report_25_26/services/api'

const router = useRouter()
const projectKey = 'insulation_pipe_supply_2026'

// 面包屑规范化
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '2026年度保温管物流链管理系统', to: `/projects/${projectKey}/pages` },
  { label: '综合数据查询中心' }
])

// 基础状态
const loading = ref(true)
const tabLoading = ref(false)
const errorMessage = ref('')
const configSummary = ref(null)
const activeDropdown = ref(null)
const exportLoading = ref(false)

// 标签页状态
const activeTab = ref('daily_flow') // 'daily_flow' | 'baseline_progress' | 'directory'
const subMaterialType = ref('pipe') // 'pipe' | 'fitting'
const fittingTab2SubView = ref('baseline') // 'baseline' (设计采购基准表) | 'flow' (全周期累计流转与现场库存表)
const directoryCategory = ref('all') // 'all' | 'suppliers' | 'site_managers' | 'demand_sections' | 'warehouse_keepers' | 'global_members'

// Tab 3 专属视图切换模式 ('by_category': 按主体类别 | 'by_section': 按标段综合穿透)
const directoryViewMode = ref('by_category')

// 分组折叠状态 (默认全部展开)
const groupCollapseState = reactive({
  suppliers: false,
  demand_sections: false,
  site_managers: false,
  warehouse_keepers: false,
  global_members: false,
})

function toggleGroupCollapse(groupKey) {
  groupCollapseState[groupKey] = !groupCollapseState[groupKey]
}

function expandAllGroups() {
  Object.keys(groupCollapseState).forEach(k => {
    groupCollapseState[k] = false
  })
}

function collapseAllGroups() {
  Object.keys(groupCollapseState).forEach(k => {
    groupCollapseState[k] = true
  })
}

// 标段卡片折叠状态 (默认全部展开)
const sectionCollapseState = reactive({})

function toggleSectionCollapse(secId) {
  sectionCollapseState[secId] = !sectionCollapseState[secId]
}

function expandAllSections() {
  sectionEntityMatrix.value.forEach(s => {
    sectionCollapseState[s.section_1_id] = false
  })
}

function collapseAllSections() {
  sectionEntityMatrix.value.forEach(s => {
    sectionCollapseState[s.section_1_id] = true
  })
}

// -----------------------------------------------------------------------------
// 🎛️ 多维透视聚合控制器状态 (Dynamic Multi-Dimensional Pivot & Aggregation)
// -----------------------------------------------------------------------------

// 可选维度定义字典
const DIMENSION_DEFS = {
  model: { id: 'model', label: '📐 规格型号', shortLabel: '型号', colHeader: '规格型号', icon: '📐' },
  date: { id: 'date', label: '📅 业务日期', shortLabel: '日期', colHeader: '业务日期', icon: '📅' },
  section: { id: 'section', label: '🏗️ 需求标段', shortLabel: '标段', colHeader: '需求标段', icon: '🏗️' },
  supplier: { id: 'supplier', label: '🏭 供货厂家', shortLabel: '厂家', colHeader: '供货厂家', icon: '🏭' },
}

function getDimensionDef(dimId) {
  return DIMENSION_DEFS[dimId] || { id: dimId, label: dimId, shortLabel: dimId, colHeader: dimId, icon: '🏷️' }
}

// Tab 1 (每日历史流转台账) 当前激活维度层级 (默认: 日期 ➔ 标段 ➔ 型号)
const dailyDimensions = ref(['date', 'section', 'model'])

// Tab 1 快捷透视预设方案
const dailyDimensionPresets = [
  { label: '⚡ 默认明细 (日/标/型)', dims: ['date', 'section', 'model'] },
  { label: '🌟 型号➔日期 (标段全合并)', dims: ['model', 'date'] },
  { label: '🏗️ 标段➔型号汇总', dims: ['section', 'model'] },
  { label: '📐 纯型号合计', dims: ['model'] },
  { label: '📅 纯日期走势', dims: ['date'] },
  { label: '🏭 厂家➔标段', dims: ['supplier', 'section'] },
]

// Tab 2 (设计采购基准进度) 当前激活维度层级 (默认: 标段 ➔ 型号)
const baselineDimensions = ref(['section', 'model'])

// Tab 2 快捷透视预设方案
const baselineDimensionPresets = [
  { label: '⚡ 默认 (标段➔型号)', dims: ['section', 'model'] },
  { label: '🌟 全网型号总览 (标段合计)', dims: ['model'] },
  { label: '📐 型号➔标段对比', dims: ['model', 'section'] },
  { label: '🏗️ 纯标段合计', dims: ['section'] },
  { label: '🏭 厂家➔标段', dims: ['supplier', 'section'] },
]

function isCurrentPreset(tab, dims) {
  const current = tab === 'daily' ? dailyDimensions.value : baselineDimensions.value
  return current.join(',') === dims.join(',')
}

function applyDimensionPreset(tab, dims) {
  if (tab === 'daily') {
    dailyDimensions.value = [...dims]
  } else {
    baselineDimensions.value = [...dims]
  }
}

// 🎛️ 多维透视聚合控制器状态 (下拉列表选择模式)
const activePivotDropdown = ref(null) // 'daily' | 'baseline' | null

function togglePivotDropdown(tab) {
  activePivotDropdown.value = activePivotDropdown.value === tab ? null : tab
}

function closePivotDropdown() {
  activePivotDropdown.value = null
}

// 获取当前维度链条精简展示文字 (例如 "1.型号 ➔ 2.日期")
function getDimensionChainText(tab) {
  const current = tab === 'daily' ? dailyDimensions.value : baselineDimensions.value
  if (!current || current.length === 0) return '未选维度 (全量汇总)'
  return current.map((id, idx) => `${idx + 1}.${getDimensionDef(id).shortLabel}`).join(' ➔ ')
}

// 获取可用维度定义列表
function getAvailableDimensions(tab) {
  const allIds = tab === 'daily' 
    ? ['model', 'date', 'section', 'supplier'] 
    : ['model', 'section', 'supplier']
  return allIds.map(id => getDimensionDef(id))
}

function isDimensionSelected(tab, dimId) {
  const list = tab === 'daily' ? dailyDimensions.value : baselineDimensions.value
  return list.includes(dimId)
}

function getDimensionOrder(tab, dimId) {
  const list = tab === 'daily' ? dailyDimensions.value : baselineDimensions.value
  const idx = list.indexOf(dimId)
  return idx !== -1 ? idx + 1 : null
}

// 有序切换勾选：未勾选时按点击先后顺序追加到末尾；已勾选时取消勾选
function toggleDimensionSelection(tab, dimId) {
  const list = tab === 'daily' ? dailyDimensions.value : baselineDimensions.value
  const idx = list.indexOf(dimId)
  if (idx === -1) {
    list.push(dimId)
  } else {
    if (list.length <= 1) {
      alert('请至少保留 1 个聚合维度')
      return
    }
    list.splice(idx, 1)
  }
}

function moveDimensionUp(tab, dimId) {
  const list = tab === 'daily' ? dailyDimensions.value : baselineDimensions.value
  const idx = list.indexOf(dimId)
  if (idx > 0) {
    const item = list.splice(idx, 1)[0]
    list.splice(idx - 1, 0, item)
  }
}

function moveDimensionDown(tab, dimId) {
  const list = tab === 'daily' ? dailyDimensions.value : baselineDimensions.value
  const idx = list.indexOf(dimId)
  if (idx !== -1 && idx < list.length - 1) {
    const item = list.splice(idx, 1)[0]
    list.splice(idx + 1, 0, item)
  }
}

function resetToDefaultDimensions(tab) {
  if (tab === 'daily') {
    dailyDimensions.value = ['date', 'section', 'model']
  } else {
    baselineDimensions.value = ['section', 'model']
  }
}

const isDefaultFullDaily = computed(() => {
  return dailyDimensions.value.length === 3 && dailyDimensions.value.join(',') === 'date,section,model'
})

// 筛选器状态
const selectedSectionIds = ref([])
const selectedPipeModelIds = ref([])
const fittingKeyword = ref('')
const globalSearchKeyword = ref('')
const activeDateCapsule = ref('30days') // 'all' | '7days' | '30days'
const filterStartDate = ref('')
const filterEndDate = ref('')

// 数据存储
const dailyFlowData = ref({ items: [], summary: {} })
const baselineProgressData = ref({ items: [], summary: {} })
const entityDirectoryData = ref({ 
  suppliers: [], 
  demand_sections: [], 
  site_managers: [], 
  warehouse_keepers: [], 
  global_members: [] 
})

// 弹窗
const pipeDetailModalVisible = ref(false)
const pipeDetailModalData = ref(null)

// -----------------------------------------------------------------------------
// 配置与选项衍生
// -----------------------------------------------------------------------------

const demandEntities = computed(() => {
  return configSummary.value?.section_1s || configSummary.value?.demand_entities || configSummary.value?.section_1 || []
})

const pipeModelOptions = computed(() => {
  return configSummary.value?.pipe_models || configSummary.value?.pipe_model || []
})

function getSectionName(secId) {
  const found = demandEntities.value.find(s => s.section_1_id === secId)
  return found ? (found.section_1_name || found.name || secId) : secId
}

function getPipeModelName(pmId) {
  const found = pipeModelOptions.value.find(m => m.pipe_model_id === pmId)
  return found ? (found.pipe_model_name || found.name || pmId) : pmId
}

const section1TriggerText = computed(() => {
  if (selectedSectionIds.value.length === 0) return '— 全部标段 (可勾选多选) —'
  if (selectedSectionIds.value.length === demandEntities.value.length && demandEntities.value.length > 0) {
    return `全部标段 (已选 ${selectedSectionIds.value.length} 个)`
  }
  const names = selectedSectionIds.value.map(id => getSectionName(id))
  return names.join('、')
})

const pipeModelTriggerText = computed(() => {
  if (selectedPipeModelIds.value.length === 0) return '— 全部保温管型号 —'
  if (selectedPipeModelIds.value.length === pipeModelOptions.value.length && pipeModelOptions.value.length > 0) {
    return `全部型号 (已选 ${selectedPipeModelIds.value.length} 个)`
  }
  const names = selectedPipeModelIds.value.map(id => getPipeModelName(id))
  return names.join('、')
})

const hasActiveFilterChips = computed(() => {
  return (
    selectedSectionIds.value.length > 0 ||
    selectedPipeModelIds.value.length > 0 ||
    Boolean(fittingKeyword.value.trim()) ||
    Boolean(globalSearchKeyword.value.trim())
  )
})

// -----------------------------------------------------------------------------
// 过滤与计算数据 (Tab 1 & Tab 2)
// -----------------------------------------------------------------------------

const filteredDailyRows = computed(() => {
  let list = dailyFlowData.value.items || []

  // 标段过滤
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(r => selectedSectionIds.value.includes(r.section_1_id))
  }

  // 型号过滤 (保温管)
  if (subMaterialType.value === 'pipe' && selectedPipeModelIds.value.length > 0) {
    list = list.filter(r => selectedPipeModelIds.value.includes(r.pipe_model_id))
  }

  // 管件关键字过滤
  if (subMaterialType.value === 'fitting' && fittingKeyword.value.trim()) {
    const kw = fittingKeyword.value.trim().toLowerCase()
    list = list.filter(r => {
      return (
        (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
        (r.model_spec && r.model_spec.toLowerCase().includes(kw))
      )
    })
  }

  // 全局关键字过滤
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(r => {
      return (
        (r.section_1_name && r.section_1_name.toLowerCase().includes(kw)) ||
        (r.pipe_model_name && r.pipe_model_name.toLowerCase().includes(kw)) ||
        (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
        (r.model_spec && r.model_spec.toLowerCase().includes(kw)) ||
        (r.biz_date && r.biz_date.includes(kw))
      )
    })
  }
  return list
})

// Tab 1 动态多维聚合行数据 (根据 dailyDimensions 实时分组求和)
const aggregatedDailyRows = computed(() => {
  const rawList = filteredDailyRows.value
  const activeDims = dailyDimensions.value
  if (!activeDims || activeDims.length === 0) return rawList

  // 如果选定的是默认维度组合 'date,section,model'，直接返回 rawList
  if (activeDims.length === 3 && activeDims.join(',') === 'date,section,model') {
    return rawList
  }

  const groupsMap = new Map()

  for (const row of rawList) {
    const keyParts = []
    const dimValues = {}

    for (const dim of activeDims) {
      if (dim === 'date') {
        const val = row.biz_date || '—'
        keyParts.push(val)
        dimValues.biz_date = val
      } else if (dim === 'section') {
        const val = row.section_1_name || '—'
        keyParts.push(val)
        dimValues.section_1_name = val
        dimValues.section_1_id = row.section_1_id
      } else if (dim === 'model') {
        if (subMaterialType.value === 'pipe') {
          const val = row.pipe_model_name || '—'
          keyParts.push(val)
          dimValues.pipe_model_name = val
          dimValues.pipe_model_id = row.pipe_model_id
        } else {
          const val = `${row.fitting_type || ''} ${row.model_spec || ''}`
          keyParts.push(val)
          dimValues.fitting_type = row.fitting_type || '—'
          dimValues.model_spec = row.model_spec || '—'
        }
      } else if (dim === 'supplier') {
        const val = row.supplier_name || row.supplier_entity_name || '—'
        keyParts.push(val)
        dimValues.supplier_name = val
      }
    }

    const groupKey = keyParts.join('____')

    if (!groupsMap.has(groupKey)) {
      groupsMap.set(groupKey, {
        ...dimValues,
        plan_qty: 0,
        shipped_qty: 0,
        arrived_qty: 0,
        received_qty: 0,
        usage_qty: 0,
        loss_qty: 0,
        warehouse_qty: 0,
        avg_transit_display: row.avg_transit_display || '—',
        _aggregated_count: 0
      })
    }

    const target = groupsMap.get(groupKey)
    target.plan_qty += Number(row.plan_qty) || 0
    target.shipped_qty += Number(row.shipped_qty) || 0
    target.arrived_qty += Number(row.arrived_qty) || 0
    target.received_qty += Number(row.received_qty) || 0
    target.usage_qty += Number(row.usage_qty) || 0
    target.loss_qty += Number(row.loss_qty) || 0
    target.warehouse_qty += Number(row.warehouse_qty) || 0
    target._aggregated_count += 1
  }

  const result = Array.from(groupsMap.values())

  // 多维逐级排序
  result.sort((a, b) => {
    for (const dim of activeDims) {
      let valA = ''
      let valB = ''
      if (dim === 'date') { valA = a.biz_date || ''; valB = b.biz_date || ''; }
      else if (dim === 'section') { valA = a.section_1_name || ''; valB = b.section_1_name || ''; }
      else if (dim === 'model') { 
        valA = subMaterialType.value === 'pipe' ? (a.pipe_model_name || '') : (`${a.fitting_type || ''} ${a.model_spec || ''}`);
        valB = subMaterialType.value === 'pipe' ? (b.pipe_model_name || '') : (`${b.fitting_type || ''} ${b.model_spec || ''}`);
      }
      else if (dim === 'supplier') { valA = a.supplier_name || ''; valB = b.supplier_name || ''; }

      if (valA !== valB) {
        return valA.localeCompare(valB, 'zh-CN', { numeric: true })
      }
    }
    return 0
  })

  return result
})

const dailyPipeSummary = computed(() => {
  if (subMaterialType.value !== 'pipe') return {}
  const rows = filteredDailyRows.value
  let total_plan_qty = 0
  let total_shipped_qty = 0
  let total_arrived_qty = 0
  let total_received_qty = 0
  let total_usage_qty = 0
  let total_loss_qty = 0
  let total_warehouse_qty = 0

  for (const r of rows) {
    total_plan_qty += Number(r.plan_qty) || 0
    total_shipped_qty += Number(r.shipped_qty) || 0
    total_arrived_qty += Number(r.arrived_qty) || 0
    total_received_qty += Number(r.received_qty) || 0
    total_usage_qty += Number(r.usage_qty) || 0
    total_loss_qty += Number(r.loss_qty) || 0
    total_warehouse_qty += Number(r.warehouse_qty) || 0
  }

  const fulfillment_rate = total_plan_qty > 0 ? (total_arrived_qty / total_plan_qty * 100) : 0
  const conversion_rate = total_arrived_qty > 0 ? (total_usage_qty / total_arrived_qty * 100) : 0

  return {
    total_plan_qty,
    total_shipped_qty,
    total_arrived_qty,
    total_received_qty,
    total_usage_qty,
    total_loss_qty,
    total_warehouse_qty,
    overall_fulfillment_rate: Math.round(fulfillment_rate * 10) / 10,
    overall_conversion_rate: Math.round(conversion_rate * 10) / 10,
    overall_avg_transit: dailyFlowData.value.summary?.overall_avg_transit || '—',
  }
})

const dailyFittingSummary = computed(() => {
  if (subMaterialType.value !== 'fitting') return {}
  const rows = filteredDailyRows.value
  let total_shipped_qty = 0
  let total_arrived_qty = 0
  let total_received_qty = 0
  let total_usage_qty = 0
  let total_warehouse_qty = 0

  for (const r of rows) {
    total_shipped_qty += Number(r.shipped_qty) || 0
    total_arrived_qty += Number(r.arrived_qty) || 0
    total_received_qty += Number(r.received_qty) || 0
    total_usage_qty += Number(r.usage_qty) || 0
    total_warehouse_qty += Number(r.warehouse_qty) || 0
  }

  return {
    total_shipped_qty,
    total_arrived_qty,
    total_received_qty,
    total_usage_qty,
    total_warehouse_qty,
    site_stock_pcs: Math.max(0, total_arrived_qty - total_usage_qty),
  }
})

const filteredBaselineRows = computed(() => {
  let list = baselineProgressData.value.items || []

  if (selectedSectionIds.value.length > 0) {
    list = list.filter(r => selectedSectionIds.value.includes(r.section_1_id))
  }

  if (subMaterialType.value === 'pipe' && selectedPipeModelIds.value.length > 0) {
    list = list.filter(r => selectedPipeModelIds.value.includes(r.pipe_model_id))
  }

  if (subMaterialType.value === 'fitting' && fittingKeyword.value.trim()) {
    const kw = fittingKeyword.value.trim().toLowerCase()
    list = list.filter(r => {
      return (
        (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
        (r.model_spec && r.model_spec.toLowerCase().includes(kw))
      )
    })
  }

  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(r => {
      return (
        (r.section_1_name && r.section_1_name.toLowerCase().includes(kw)) ||
        (r.pipe_model_name && r.pipe_model_name.toLowerCase().includes(kw)) ||
        (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
        (r.model_spec && r.model_spec.toLowerCase().includes(kw))
      )
    })
  }
  return list
})

// 1. 管件设计与计划采购基准行过滤 (来自 baseline_items)
const filteredFittingBaselineRows = computed(() => {
  let list = baselineProgressData.value.baseline_items || baselineProgressData.value.items || []
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(r => selectedSectionIds.value.includes(r.section_1_id))
  }
  if (fittingKeyword.value.trim()) {
    const kw = fittingKeyword.value.trim().toLowerCase()
    list = list.filter(r => 
      (r.category && r.category.toLowerCase().includes(kw)) ||
      (r.standard_name && r.standard_name.toLowerCase().includes(kw)) ||
      (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
      (r.model_spec && r.model_spec.toLowerCase().includes(kw)) ||
      (r.sub_model_spec && r.sub_model_spec.toLowerCase().includes(kw))
    )
  }
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(r => 
      (r.section_1_name && r.section_1_name.toLowerCase().includes(kw)) ||
      (r.category && r.category.toLowerCase().includes(kw)) ||
      (r.standard_name && r.standard_name.toLowerCase().includes(kw)) ||
      (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
      (r.model_spec && r.model_spec.toLowerCase().includes(kw)) ||
      (r.sub_model_spec && r.sub_model_spec.toLowerCase().includes(kw))
    )
  }
  return list
})

// 2. 管件全周期累计流转与现场库存行过滤 (来自 flow_items)
const filteredFittingFlowRows = computed(() => {
  let list = baselineProgressData.value.flow_items || []
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(r => selectedSectionIds.value.includes(r.section_1_id))
  }
  if (fittingKeyword.value.trim()) {
    const kw = fittingKeyword.value.trim().toLowerCase()
    list = list.filter(r => 
      (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
      (r.model_spec && r.model_spec.toLowerCase().includes(kw))
    )
  }
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(r => 
      (r.section_1_name && r.section_1_name.toLowerCase().includes(kw)) ||
      (r.supplier_name && r.supplier_name.toLowerCase().includes(kw)) ||
      (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
      (r.model_spec && r.model_spec.toLowerCase().includes(kw))
    )
  }
  return list
})

// 管件基准表多维聚合
const aggregatedFittingBaselineRows = computed(() => {
  const rawList = filteredFittingBaselineRows.value
  const activeDims = baselineDimensions.value
  if (!activeDims || activeDims.length === 0) return rawList

  const groupsMap = new Map()
  for (const row of rawList) {
    const keyParts = []
    const dimValues = {}

    for (const dim of activeDims) {
      if (dim === 'section') {
        const val = row.section_1_name || '—'
        keyParts.push(val)
        dimValues.section_1_name = val
        dimValues.section_1_id = row.section_1_id
      } else if (dim === 'model') {
        const val = `${row.fitting_type || row.standard_name || row.category || ''} ${row.model_spec || ''}`.trim() || '—'
        keyParts.push(val)
        dimValues.fitting_type = row.fitting_type || row.standard_name || row.category || '—'
        dimValues.category = row.category || '—'
        dimValues.standard_name = row.standard_name || ''
        dimValues.model_spec = row.model_spec || '—'
        dimValues.sub_model_spec = row.sub_model_spec || ''
      } else if (dim === 'supplier') {
        keyParts.push('全部主体')
        dimValues.supplier_name = '—'
      }
    }

    const groupKey = keyParts.join('____')
    if (!groupsMap.has(groupKey)) {
      groupsMap.set(groupKey, {
        ...dimValues,
        unit: row.unit || '个',
        design_qty: 0,
        purchase_plan_qty: 0,
        _aggregated_count: 0
      })
    }

    const target = groupsMap.get(groupKey)
    target.design_qty += Number(row.design_qty) || 0
    target.purchase_plan_qty += Number(row.purchase_plan_qty) || 0
    target._aggregated_count += 1
  }

  const result = Array.from(groupsMap.values())
  result.sort((a, b) => {
    const secCompare = (a.section_1_name || '').localeCompare(b.section_1_name || '', 'zh-CN', { numeric: true })
    if (secCompare !== 0) return secCompare
    return (a.fitting_type || '').localeCompare(b.fitting_type || '', 'zh-CN')
  })
  return result
})

// 管件流转与库存表多维聚合
const aggregatedFittingFlowRows = computed(() => {
  const rawList = filteredFittingFlowRows.value
  const activeDims = baselineDimensions.value
  if (!activeDims || activeDims.length === 0) return rawList

  const groupsMap = new Map()
  for (const row of rawList) {
    const keyParts = []
    const dimValues = {}

    for (const dim of activeDims) {
      if (dim === 'section') {
        const val = row.section_1_name || '—'
        keyParts.push(val)
        dimValues.section_1_name = val
        dimValues.section_1_id = row.section_1_id
      } else if (dim === 'model') {
        const val = `${row.fitting_type || ''} ${row.model_spec || ''}`.trim() || '—'
        keyParts.push(val)
        dimValues.fitting_type = row.fitting_type || '—'
        dimValues.model_spec = row.model_spec || '—'
      } else if (dim === 'supplier') {
        const val = row.supplier_name || '—'
        keyParts.push(val)
        dimValues.supplier_name = val
      }
    }

    const groupKey = keyParts.join('____')
    if (!groupsMap.has(groupKey)) {
      groupsMap.set(groupKey, {
        ...dimValues,
        unit: '件',
        total_shipped_qty: 0,
        total_arrived_qty: 0,
        total_usage_qty: 0,
        stock_qty: 0,
        _aggregated_count: 0
      })
    }

    const target = groupsMap.get(groupKey)
    target.total_shipped_qty += Number(row.total_shipped_qty) || 0
    target.total_arrived_qty += Number(row.total_arrived_qty) || 0
    target.total_usage_qty += Number(row.total_usage_qty) || 0
    target.stock_qty += Number(row.stock_qty) || 0
    target._aggregated_count += 1
  }

  const result = Array.from(groupsMap.values())
  result.sort((a, b) => {
    const secCompare = (a.section_1_name || '').localeCompare(b.section_1_name || '', 'zh-CN', { numeric: true })
    if (secCompare !== 0) return secCompare
    return (a.fitting_type || '').localeCompare(b.fitting_type || '', 'zh-CN')
  })
  return result
})

// Tab 2 动态多维聚合行数据 (保温管通用)
const aggregatedBaselineRows = computed(() => {
  if (subMaterialType.value === 'fitting') {
    return fittingTab2SubView.value === 'baseline' 
      ? aggregatedFittingBaselineRows.value 
      : aggregatedFittingFlowRows.value
  }

  const rawList = filteredBaselineRows.value
  const activeDims = baselineDimensions.value
  if (!activeDims || activeDims.length === 0) return rawList

  if (activeDims.length === 2 && activeDims.join(',') === 'section,model') {
    return rawList
  }

  const groupsMap = new Map()

  for (const row of rawList) {
    const keyParts = []
    const dimValues = {}

    for (const dim of activeDims) {
      if (dim === 'section') {
        const val = row.section_1_name || '—'
        keyParts.push(val)
        dimValues.section_1_name = val
        dimValues.section_1_id = row.section_1_id
      } else if (dim === 'model') {
        const val = row.pipe_model_name || '—'
        keyParts.push(val)
        dimValues.pipe_model_name = val
        dimValues.pipe_model_id = row.pipe_model_id
      } else if (dim === 'supplier') {
        const val = row.supplier_name || '—'
        keyParts.push(val)
        dimValues.supplier_name = val
      }
    }

    const groupKey = keyParts.join('____')

    if (!groupsMap.has(groupKey)) {
      groupsMap.set(groupKey, {
        ...dimValues,
        design_qty: 0,
        purchase_plan_qty: 0,
        total_shipped_qty: 0,
        total_arrived_qty: 0,
        total_usage_qty: 0,
        stock_qty: 0,
        _aggregated_count: 0
      })
    }

    const target = groupsMap.get(groupKey)
    target.design_qty += Number(row.design_qty) || 0
    target.purchase_plan_qty += Number(row.purchase_plan_qty) || 0
    target.total_shipped_qty += Number(row.total_shipped_qty) || 0
    target.total_arrived_qty += Number(row.total_arrived_qty) || 0
    target.total_usage_qty += Number(row.total_usage_qty) || 0
    target.stock_qty += Number(row.stock_qty) || 0
    target._aggregated_count += 1
  }

  const result = Array.from(groupsMap.values())

  // 精准重新计算比率 (基于求和后的总量)
  result.forEach(r => {
    r.purchase_rate = r.purchase_plan_qty > 0 ? Math.round((r.total_arrived_qty / r.purchase_plan_qty) * 1000) / 10 : 0
    r.install_rate = r.design_qty > 0 ? Math.round((r.total_usage_qty / r.design_qty) * 1000) / 10 : 0
  })

  // 多维逐级排序
  result.sort((a, b) => {
    for (const dim of activeDims) {
      let valA = ''
      let valB = ''
      if (dim === 'section') { valA = a.section_1_name || ''; valB = b.section_1_name || ''; }
      else if (dim === 'model') { valA = a.pipe_model_name || ''; valB = b.pipe_model_name || ''; }
      else if (dim === 'supplier') { valA = a.supplier_name || ''; valB = b.supplier_name || ''; }

      if (valA !== valB) {
        return valA.localeCompare(valB, 'zh-CN', { numeric: true })
      }
    }
    return 0
  })

  return result
})

const baselinePipeSummary = computed(() => {
  if (subMaterialType.value !== 'pipe') return {}
  const rows = filteredBaselineRows.value
  let total_design_qty = 0
  let total_purchase_plan_qty = 0
  let total_shipped_qty = 0
  let total_arrived_qty = 0
  let total_usage_qty = 0
  let total_loss_qty = 0
  let total_stock_qty = 0

  for (const r of rows) {
    total_design_qty += Number(r.design_qty) || 0
    total_purchase_plan_qty += Number(r.purchase_plan_qty) || 0
    total_shipped_qty += Number(r.total_shipped_qty) || 0
    total_arrived_qty += Number(r.total_arrived_qty) || 0
    total_usage_qty += Number(r.total_usage_qty) || 0
    total_loss_qty += Number(r.total_loss_qty) || 0
    total_stock_qty += Number(r.stock_qty) || 0
  }

  const purchase_rate = total_purchase_plan_qty > 0 ? (total_arrived_qty / total_purchase_plan_qty * 100) : 0
  const install_rate = total_design_qty > 0 ? (total_usage_qty / total_design_qty * 100) : 0

  return {
    total_design_qty,
    total_purchase_plan_qty,
    total_shipped_qty,
    total_arrived_qty,
    total_usage_qty,
    total_loss_qty,
    total_stock_qty,
    overall_purchase_rate: Math.round(purchase_rate * 10) / 10,
    overall_install_rate: Math.round(install_rate * 10) / 10,
  }
})

const baselineFittingSummary = computed(() => {
  if (subMaterialType.value !== 'fitting') return {}
  const bRows = filteredFittingBaselineRows.value
  const fRows = filteredFittingFlowRows.value

  let total_design_qty = 0
  let total_purchase_plan_qty = 0
  for (const r of bRows) {
    const isMeter = r.unit && (r.unit.trim() === '米' || r.unit.trim().toLowerCase() === 'm')
    total_design_qty += isMeter ? 0 : (Number(r.design_qty) || 0)
    total_purchase_plan_qty += isMeter ? 0 : (Number(r.purchase_plan_qty) || 0)
  }

  let total_shipped_qty = 0
  let total_arrived_qty = 0
  let total_usage_qty = 0
  let total_stock_qty = 0
  for (const r of fRows) {
    total_shipped_qty += Number(r.total_shipped_qty) || 0
    total_arrived_qty += Number(r.total_arrived_qty) || 0
    total_usage_qty += Number(r.total_usage_qty) || 0
    total_stock_qty += Number(r.stock_qty) || 0
  }

  const purchase_rate = total_purchase_plan_qty > 0 ? (total_arrived_qty / total_purchase_plan_qty * 100) : 0
  const install_rate = total_design_qty > 0 ? (total_usage_qty / total_design_qty * 100) : 0

  return {
    total_design_qty,
    total_purchase_plan_qty,
    total_shipped_qty,
    total_arrived_qty,
    total_usage_qty,
    total_stock_qty,
    overall_purchase_rate: Math.round(purchase_rate * 10) / 10,
    overall_install_rate: Math.round(install_rate * 10) / 10,
  }
})

// -----------------------------------------------------------------------------
// 🔀 表格字段动态排序状态与方法 (支持 升序 -> 降序 -> 清除排序 循环切换)
// -----------------------------------------------------------------------------

const tableSortStates = ref({
  daily_pipe: { key: '', order: '' }, // order: '' | 'asc' | 'desc'
  daily_fitting: { key: '', order: '' },
  baseline_pipe: { key: '', order: '' },
  fitting_baseline: { key: '', order: '' },
  fitting_flow: { key: '', order: '' }
})

function handleTableSort(tableKey, columnKey) {
  if (!tableSortStates.value[tableKey]) {
    tableSortStates.value[tableKey] = { key: '', order: '' }
  }
  const current = tableSortStates.value[tableKey]
  if (current.key === columnKey) {
    if (current.order === 'asc') {
      current.order = 'desc'
    } else if (current.order === 'desc') {
      current.key = ''
      current.order = ''
    } else {
      current.order = 'asc'
    }
  } else {
    current.key = columnKey
    current.order = 'asc'
  }
}

function isColumnSorted(tableKey, columnKey) {
  const current = tableSortStates.value[tableKey]
  return !!(current && current.key === columnKey && current.order)
}

function getSortIcon(tableKey, columnKey) {
  const current = tableSortStates.value[tableKey]
  if (!current || current.key !== columnKey || !current.order) {
    return '↕'
  }
  return current.order === 'asc' ? '▲' : '▼'
}

function sortRows(list, tableKey, customGetters = {}) {
  const current = tableSortStates.value[tableKey]
  if (!current || !current.key || !current.order) {
    return list
  }
  const { key, order } = current
  const isAsc = order === 'asc'
  const getter = customGetters[key] || (r => r[key])

  const copy = [...list]
  copy.sort((a, b) => {
    let valA = getter(a)
    let valB = getter(b)

    if (valA === undefined || valA === null) valA = ''
    if (valB === undefined || valB === null) valB = ''

    if (typeof valA === 'number' && typeof valB === 'number') {
      return isAsc ? valA - valB : valB - valA
    }

    const numA = Number(valA)
    const numB = Number(valB)
    if (!isNaN(numA) && !isNaN(numB) && typeof valA !== 'boolean' && typeof valB !== 'boolean' && valA !== '' && valB !== '') {
      return isAsc ? numA - numB : numB - numA
    }

    const strA = String(valA)
    const strB = String(valB)
    const comp = strA.localeCompare(strB, 'zh-CN', { numeric: true, sensitivity: 'base' })
    return isAsc ? comp : -comp
  })

  return copy
}

// Tab 1 保温管排序后行数据
const sortedDailyPipeRows = computed(() => {
  return sortRows(aggregatedDailyRows.value, 'daily_pipe', {
    date: r => r.biz_date || '',
    section: r => r.section_1_name || '',
    model: r => r.pipe_model_name || '',
    supplier: r => r.supplier_name || '',
    avg_transit: r => parseFloat(r.avg_transit_display) || (Number(r.avg_transit_days) || 0)
  })
})

// Tab 1 管件排序后行数据
const sortedDailyFittingRows = computed(() => {
  return sortRows(aggregatedDailyRows.value, 'daily_fitting', {
    date: r => r.biz_date || '',
    section: r => r.section_1_name || '',
    model: r => `${r.fitting_type || ''} ${r.model_spec || ''}`.trim(),
    supplier: r => r.supplier_name || '',
    site_stock_pcs: r => Math.max(0, (Number(r.arrived_qty) || 0) - (Number(r.usage_qty) || 0))
  })
})

// Tab 2 保温管基准与进度对照排序后行数据
const sortedBaselinePipeRows = computed(() => {
  return sortRows(aggregatedBaselineRows.value, 'baseline_pipe', {
    section: r => r.section_1_name || '',
    model: r => r.pipe_model_name || '',
    supplier: r => r.supplier_name || ''
  })
})

// Tab 2 管件设计与计划采购基准排序后行数据
const sortedFittingBaselineRows = computed(() => {
  return sortRows(aggregatedFittingBaselineRows.value, 'fitting_baseline', {
    section: r => r.section_1_name || '',
    model: r => `${r.fitting_type || r.standard_name || r.category || ''} ${r.model_spec || ''} ${r.sub_model_spec || ''}`.trim(),
    supplier: r => r.supplier_name || ''
  })
})

// Tab 2 管件全周期累计流转与现场库存排序后行数据
const sortedFittingFlowRows = computed(() => {
  return sortRows(aggregatedFittingFlowRows.value, 'fitting_flow', {
    section: r => r.section_1_name || '',
    model: r => `${r.fitting_type || ''} ${r.model_spec || ''}`.trim(),
    supplier: r => r.supplier_name || ''
  })
})

// -----------------------------------------------------------------------------
// 🏢 责任主体与人员管辖 (Tab 3 模式 A 过滤与分组)
// -----------------------------------------------------------------------------

const filteredSuppliers = computed(() => {
  let list = entityDirectoryData.value.suppliers || []
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(s => {
      const ids = s.managed_section_ids || []
      return ids.some(id => selectedSectionIds.value.includes(id))
    })
  }
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(s => 
      s.entity_name.toLowerCase().includes(kw) || 
      s.contact_name.toLowerCase().includes(kw) || 
      s.contact_phone.includes(kw)
    )
  }
  return list
})

const filteredDemandSections = computed(() => {
  let list = entityDirectoryData.value.demand_sections || []
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(s => {
      const ids = s.managed_section_ids || [s.section_1_id]
      return ids.some(id => selectedSectionIds.value.includes(id))
    })
  }
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(s => 
      s.section_1_name.toLowerCase().includes(kw) || 
      s.construction_unit_name.toLowerCase().includes(kw) || 
      s.contact_name.toLowerCase().includes(kw) || 
      s.contact_phone.includes(kw)
    )
  }
  return list
})

const filteredSiteManagers = computed(() => {
  let list = entityDirectoryData.value.site_managers || []
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(m => {
      if (m.is_global) return true
      const ids = m.managed_section_ids || []
      return ids.some(id => selectedSectionIds.value.includes(id))
    })
  }
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(m => 
      m.person_name.toLowerCase().includes(kw) || 
      m.contact_phone.includes(kw) ||
      m.scope_desc.toLowerCase().includes(kw)
    )
  }
  return list
})

const filteredWarehouseKeepers = computed(() => {
  let list = entityDirectoryData.value.warehouse_keepers || []
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(w => {
      if (w.is_global) return true
      const ids = w.managed_section_ids || []
      return ids.some(id => selectedSectionIds.value.includes(id))
    })
  }
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(w => 
      w.person_name.toLowerCase().includes(kw) || 
      w.contact_phone.includes(kw) ||
      w.scope_desc.toLowerCase().includes(kw) ||
      w.username.toLowerCase().includes(kw)
    )
  }
  return list
})

const filteredGlobalMembers = computed(() => {
  let list = entityDirectoryData.value.global_members || []
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(g => 
      g.username.toLowerCase().includes(kw) || 
      g.role_name.toLowerCase().includes(kw) ||
      g.scope_desc.toLowerCase().includes(kw)
    )
  }
  return list
})

const totalDirectoryCount = computed(() => {
  return (
    filteredSuppliers.value.length +
    filteredDemandSections.value.length +
    filteredSiteManagers.value.length +
    filteredWarehouseKeepers.value.length +
    filteredGlobalMembers.value.length
  )
})

// -----------------------------------------------------------------------------
// 🏗️ 责任主体与人员管辖 (Tab 3 模式 B: 按标段综合穿透矩阵)
// -----------------------------------------------------------------------------

const sectionEntityMatrix = computed(() => {
  const sections = demandEntities.value || []
  const suppliers = entityDirectoryData.value.suppliers || []
  const siteManagers = entityDirectoryData.value.site_managers || []
  const demandSections = entityDirectoryData.value.demand_sections || []
  const warehouseKeepers = entityDirectoryData.value.warehouse_keepers || []
  
  let list = sections.map(sec => {
    const secId = sec.section_1_id
    const secName = sec.section_1_name || sec.name || secId
    
    // 1. 供货厂家 (明确供应当前标段)
    const secSuppliers = suppliers.filter(s => {
      const ids = s.managed_section_ids || []
      return ids.includes(secId)
    })
    
    // 2. 现场负责人 (负责当前标段，非全局)
    const secManagers = siteManagers.filter(m => {
      if (m.is_global) return false
      const ids = m.managed_section_ids || []
      return ids.includes(secId)
    })
    
    // 3. 施工单位 (签约当前标段)
    const secConstructions = demandSections.filter(c => {
      const ids = c.managed_section_ids || [c.section_1_id]
      return ids.includes(secId)
    })
    
    // 4. 物资库管 (核验当前标段，非全局)
    const secKeepers = warehouseKeepers.filter(w => {
      if (w.is_global) return false
      const ids = w.managed_section_ids || []
      return ids.includes(secId)
    })
    
    return {
      section_1_id: secId,
      section_1_name: secName,
      suppliers: secSuppliers,
      site_managers: secManagers,
      construction_units: secConstructions,
      warehouse_keepers: secKeepers,
    }
  })

  // 标段多选过滤
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(item => selectedSectionIds.value.includes(item.section_1_id))
  }

  // 关键字全局搜索
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(item => {
      if (item.section_1_name.toLowerCase().includes(kw)) return true
      const supMatch = item.suppliers.some(s => s.entity_name.toLowerCase().includes(kw) || s.contact_name.toLowerCase().includes(kw) || s.contact_phone.includes(kw))
      const mgrMatch = item.site_managers.some(m => m.person_name.toLowerCase().includes(kw) || m.contact_phone.includes(kw))
      const conMatch = item.construction_units.some(c => c.construction_unit_name.toLowerCase().includes(kw) || c.contact_name.toLowerCase().includes(kw) || c.contact_phone.includes(kw))
      const whMatch = item.warehouse_keepers.some(w => w.person_name.toLowerCase().includes(kw) || w.contact_phone.includes(kw))
      return supMatch || mgrMatch || conMatch || whMatch
    })
  }

  return list
})

// 全局角色衍生 (集团现场总调度、供给侧全局管理、物资总库管理、系统指挥观察员)
const globalPersonnel = computed(() => {
  const siteManagers = entityDirectoryData.value.site_managers || []
  const suppliers = entityDirectoryData.value.suppliers || []
  const warehouseKeepers = entityDirectoryData.value.warehouse_keepers || []
  const globalMembers = entityDirectoryData.value.global_members || []
  
  let globalMgrs = siteManagers.filter(m => m.is_global)
  let globalSuppliers = suppliers.filter(s => !s.managed_section_ids || s.managed_section_ids.length === 0)
  let globalWhs = warehouseKeepers.filter(w => w.is_global)
  let globalMems = globalMembers

  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    globalMgrs = globalMgrs.filter(m => m.person_name.toLowerCase().includes(kw) || m.contact_phone.includes(kw))
    globalSuppliers = globalSuppliers.filter(s => s.entity_name.toLowerCase().includes(kw) || s.contact_name.toLowerCase().includes(kw) || s.contact_phone.includes(kw))
    globalWhs = globalWhs.filter(w => w.person_name.toLowerCase().includes(kw) || w.contact_phone.includes(kw))
    globalMems = globalMems.filter(g => g.username.toLowerCase().includes(kw) || g.role_name.toLowerCase().includes(kw))
  }

  return {
    managers: globalMgrs,
    suppliers: globalSuppliers,
    keepers: globalWhs,
    members: globalMems,
    totalCount: globalMgrs.length + globalSuppliers.length + globalWhs.length + globalMems.length
  }
})

// -----------------------------------------------------------------------------
// 初始化与数据加载
// -----------------------------------------------------------------------------

onMounted(async () => {
  setDateRangeByCapsule('30days')
  try {
    loading.value = true
    const cfg = await fetchTubeConfig(projectKey)
    configSummary.value = cfg
    await fetchActiveTabData()
  } catch (err) {
    errorMessage.value = err.message || '加载配置失败'
  } finally {
    loading.value = false
  }
})

function setDateRangeByCapsule(capsule) {
  activeDateCapsule.value = capsule
  const today = new Date()
  const formatDate = (d) => d.toISOString().split('T')[0]
  filterEndDate.value = formatDate(today)

  if (capsule === '7days') {
    const d = new Date()
    d.setDate(d.getDate() - 7)
    filterStartDate.value = formatDate(d)
  } else if (capsule === '30days') {
    const d = new Date()
    d.setDate(d.getDate() - 30)
    filterStartDate.value = formatDate(d)
  } else if (capsule === 'all') {
    const d = new Date()
    d.setDate(d.getDate() - 180)
    filterStartDate.value = formatDate(d)
  }
  fetchActiveTabData()
}

function onDateInputChange() {
  activeDateCapsule.value = 'custom'
  fetchActiveTabData()
}

function onFilterChange() {
  // 前端计算属性会自动即时过滤
}

async function fetchActiveTabData() {
  tabLoading.value = true
  try {
    if (activeTab.value === 'daily_flow') {
      const res = await getComprehensiveDailyFlow(projectKey, {
        startDate: filterStartDate.value,
        endDate: filterEndDate.value,
        section1Ids: selectedSectionIds.value,
        pipeModelIds: selectedPipeModelIds.value,
        materialType: subMaterialType.value,
      })
      dailyFlowData.value = res
    } else if (activeTab.value === 'baseline_progress') {
      const res = await getComprehensiveBaselineProgress(projectKey, {
        section1Ids: selectedSectionIds.value,
        pipeModelIds: selectedPipeModelIds.value,
        materialType: subMaterialType.value,
      })
      baselineProgressData.value = res
    } else if (activeTab.value === 'directory') {
      const res = await getComprehensiveEntityDirectory(projectKey)
      entityDirectoryData.value = res
    }
  } catch (err) {
    console.error('加载综合数据失败:', err)
  } finally {
    tabLoading.value = false
  }
}

function switchMainTab(tab) {
  activeTab.value = tab
  fetchActiveTabData()
}

function switchSubMaterial(mat) {
  subMaterialType.value = mat
  fetchActiveTabData()
}

function triggerCurrentQuery() {
  fetchActiveTabData()
}

function resetAllFilters() {
  selectedSectionIds.value = []
  selectedPipeModelIds.value = []
  fittingKeyword.value = ''
  globalSearchKeyword.value = ''
  setDateRangeByCapsule('30days')
  tableSortStates.value = {
    daily_pipe: { key: '', order: '' },
    daily_fitting: { key: '', order: '' },
    baseline_pipe: { key: '', order: '' },
    fitting_baseline: { key: '', order: '' },
    fitting_flow: { key: '', order: '' }
  }
}

// -----------------------------------------------------------------------------
// 下拉框交互与 Chip 操作
// -----------------------------------------------------------------------------

function toggleDropdown(name) {
  activeDropdown.value = activeDropdown.value === name ? null : name
}

function selectAllSections() {
  selectedSectionIds.value = demandEntities.value.map(s => s.section_1_id)
}

function clearSections() {
  selectedSectionIds.value = []
}

function selectAllPipeModels() {
  selectedPipeModelIds.value = pipeModelOptions.value.map(m => m.pipe_model_id)
}

function clearPipeModels() {
  selectedPipeModelIds.value = []
}

function removeSection(secId) {
  selectedSectionIds.value = selectedSectionIds.value.filter(id => id !== secId)
}

function removePipeModel(pmId) {
  selectedPipeModelIds.value = selectedPipeModelIds.value.filter(id => id !== pmId)
}

// -----------------------------------------------------------------------------
// 弹窗与详情
// -----------------------------------------------------------------------------

function openDailyPipeDetail(row) {
  pipeDetailModalData.value = row
  pipeDetailModalVisible.value = true
}

function copyPhone(phone) {
  if (!phone || phone === '—') return
  navigator.clipboard.writeText(phone)
  alert(`已复制电话号码：${phone}`)
}

function goProjectPages() {
  router.push(`/projects/${projectKey}/pages`)
}

function formatQty(val) {
  if (val === undefined || val === null || val === '') return '0'
  const num = Number(val)
  return isNaN(num) ? '0' : num.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

// -----------------------------------------------------------------------------
// 📥 高规格 Excel 导出 (基于 xlsx-js-style)
// -----------------------------------------------------------------------------

async function exportCurrentTabExcel() {
  exportLoading.value = true
  try {
    let headers = []
    let dataRows = []
    let filename = ''

    if (activeTab.value === 'daily_flow') {
      const activeDims = dailyDimensions.value
      const dimHeaders = activeDims.map(d => getDimensionDef(d).colHeader)

      if (subMaterialType.value === 'pipe') {
        headers = [...dimHeaders, '计划量(米)', '发货量(米)', '到货量(米)', '施工接收(米)', '现场使用(米)', '损耗量(米)', '库管已确认(米)']
        if (activeDims.includes('date')) headers.push('在途时长')

        dataRows = sortedDailyPipeRows.value.map(r => {
          const dimVals = activeDims.map(d => {
            if (d === 'date') return r.biz_date || '—'
            if (d === 'section') return r.section_1_name || '—'
            if (d === 'model') return r.pipe_model_name || '—'
            if (d === 'supplier') return r.supplier_name || '—'
            return '—'
          })
          const row = [...dimVals, r.plan_qty, r.shipped_qty, r.arrived_qty, r.received_qty, r.usage_qty, r.loss_qty, r.warehouse_qty]
          if (activeDims.includes('date')) row.push(r.avg_transit_display || '—')
          return row
        })
        filename = `保温管每日流转透视台账_${filterStartDate.value}_${filterEndDate.value}.xlsx`
      } else {
        headers = [...dimHeaders, '发货数量(件)', '到货数量(件)', '施工接收(件)', '现场安装(件)', '库管已确认(件)', '现场结余(件)']
        dataRows = sortedDailyFittingRows.value.map(r => {
          const dimVals = activeDims.map(d => {
            if (d === 'date') return r.biz_date || '—'
            if (d === 'section') return r.section_1_name || '—'
            if (d === 'model') return `${r.fitting_type || ''} ${r.model_spec || ''}`.trim() || '—'
            if (d === 'supplier') return r.supplier_name || '—'
            return '—'
          })
          return [...dimVals, r.shipped_qty, r.arrived_qty, r.received_qty, r.usage_qty, r.warehouse_qty, Math.max(0, r.arrived_qty - r.usage_qty)]
        })
        filename = `管件每日流转透视台账_${filterStartDate.value}_${filterEndDate.value}.xlsx`
      }
    } else if (activeTab.value === 'baseline_progress') {
      const activeDims = baselineDimensions.value
      const dimHeaders = activeDims.map(d => getDimensionDef(d).colHeader)

      if (subMaterialType.value === 'pipe') {
        headers = [...dimHeaders, '设计量(米)', '计划采购量(米)', '累计发货(米)', '累计到货(米)', '累计使用(米)', '现场库存(米)', '采购完成率', '施工进度率']
        dataRows = sortedBaselinePipeRows.value.map(r => {
          const dimVals = activeDims.map(d => {
            if (d === 'section') return r.section_1_name || '—'
            if (d === 'model') return r.pipe_model_name || '—'
            if (d === 'supplier') return r.supplier_name || '—'
            return '—'
          })
          return [...dimVals, r.design_qty, r.purchase_plan_qty, r.total_shipped_qty, r.total_arrived_qty, r.total_usage_qty, r.stock_qty, `${r.purchase_rate}%`, `${r.install_rate}%`]
        })
        filename = '保温管设计采购基准进度透视表.xlsx'
      } else if (fittingTab2SubView.value === 'baseline') {
        headers = [...dimHeaders, '单位', '设计使用量', '计划采购量']
        dataRows = sortedFittingBaselineRows.value.map(r => {
          const dimVals = activeDims.map(d => {
            if (d === 'section') return r.section_1_name || '—'
            if (d === 'model') return `${r.fitting_type || r.standard_name || r.category || ''} ${r.model_spec || ''}`.trim() || '—'
            if (d === 'supplier') return '（设计基准）'
            return '—'
          })
          return [...dimVals, r.unit || '个', r.design_qty, r.purchase_plan_qty]
        })
        filename = '管件设计与计划采购基准表.xlsx'
      } else {
        headers = [...dimHeaders, '单位', '累计发货量', '累计到货量', '现场安装量', '现场库存余量']
        dataRows = sortedFittingFlowRows.value.map(r => {
          const dimVals = activeDims.map(d => {
            if (d === 'section') return r.section_1_name || '—'
            if (d === 'model') return `${r.fitting_type || ''} ${r.model_spec || ''}`.trim() || '—'
            if (d === 'supplier') return r.supplier_name || '—'
            return '—'
          })
          return [...dimVals, '件', r.total_shipped_qty, r.total_arrived_qty, r.total_usage_qty, r.stock_qty]
        })
        filename = '管件全周期累计流转与现场库存表.xlsx'
      }
    } else if (activeTab.value === 'directory') {
      if (directoryViewMode.value === 'by_section') {
        // 按标段穿透导出
        headers = ['标段ID', '标段名称', '责任角色', '主体/单位/人名', '职务/职责', '联系电话']
        dataRows = []
        sectionEntityMatrix.value.forEach(sec => {
          sec.suppliers.forEach(s => dataRows.push([sec.section_1_id, sec.section_1_name, '供货厂家', s.entity_name, `联系人: ${s.contact_name}`, s.contact_phone]))
          sec.site_managers.forEach(m => dataRows.push([sec.section_1_id, sec.section_1_name, '现场负责人', m.person_name, '标段主管', m.contact_phone]))
          sec.construction_units.forEach(c => dataRows.push([sec.section_1_id, sec.section_1_name, '施工单位', c.construction_unit_name, `项目经理: ${c.contact_name}`, c.contact_phone]))
          sec.warehouse_keepers.forEach(w => dataRows.push([sec.section_1_id, sec.section_1_name, '物资库管', w.person_name, '现场库管员', w.contact_phone]))
        })
        // 追加全局角色
        globalPersonnel.value.managers.forEach(gm => dataRows.push(['GLOBAL', '全网统筹', '集团总调度', gm.person_name, '现场总协调', gm.contact_phone]))
        globalPersonnel.value.suppliers.forEach(gs => dataRows.push(['GLOBAL', '全网统筹', '供给侧全局管理', gs.contact_name, `主体: ${gs.entity_name}`, gs.contact_phone]))
        globalPersonnel.value.keepers.forEach(gw => dataRows.push(['GLOBAL', '全网统筹', '物资总库管', gw.person_name, '总库管理', gw.contact_phone]))
        globalPersonnel.value.members.forEach(mem => dataRows.push(['GLOBAL', '全网统筹', '系统指挥观察', mem.username, mem.role_name, '集团专线']))
        filename = '项目各标段责任主体与人员综合矩阵表.xlsx'
      } else {
        headers = ['主体分类', '主体/标段/姓名', '负责人/职务', '联系电话', '管辖/供货范围', '归属单位/账号']
        // 收集 5 大组数据 (按供货厂家、现场负责人、施工单位、物资库管、系统管理排序)
        dataRows = [
          ...filteredSuppliers.value.map(s => ['供货厂家', s.entity_name, s.contact_name, s.contact_phone, (s.managed_sections && s.managed_sections.length > 0) ? s.managed_sections.join('、') : '暂未分配供应标段', `调度账号: ${s.accounts.join(', ')}`]),
          ...filteredSiteManagers.value.map(m => ['现场负责人', `${m.person_name} (负责人)`, m.contact_name, m.contact_phone, m.scope_desc, m.is_global ? '集团总指挥协调' : `管辖: ${m.scope_desc}`]),
          ...filteredDemandSections.value.map(d => ['施工单位', d.section_1_name, d.contact_name, d.contact_phone, d.section_1_name, `施工单位: ${d.construction_unit_name}`]),
          ...filteredWarehouseKeepers.value.map(w => ['物资库管', `${w.person_name} (库管)`, w.person_name, w.contact_phone, w.scope_desc, `系统账号: ${w.username}`]),
          ...filteredGlobalMembers.value.map(g => ['系统管理', g.username, g.contact_name, '集团专线', '全网全局透视', g.scope_desc]),
        ]
        filename = '项目责任主体与人员管辖矩阵表.xlsx'
      }
    }

    const wsData = [headers, ...dataRows]
    const ws = XLSX.utils.aoa_to_sheet(wsData)

    // 样式美化
    const headerStyle = {
      font: { name: 'Microsoft YaHei', sz: 11, bold: true, color: { rgb: 'FFFFFF' } },
      fill: { fgColor: { rgb: '334155' } },
      alignment: { horizontal: 'center', vertical: 'center' },
      border: {
        top: { style: 'thin', color: { rgb: 'CBD5E1' } },
        bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
        left: { style: 'thin', color: { rgb: 'CBD5E1' } },
        right: { style: 'thin', color: { rgb: 'CBD5E1' } },
      },
    }

    const cellBorder = {
      top: { style: 'thin', color: { rgb: 'CBD5E1' } },
      bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
      left: { style: 'thin', color: { rgb: 'CBD5E1' } },
      right: { style: 'thin', color: { rgb: 'CBD5E1' } },
    }

    const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:A1')
    for (let R = range.s.r; R <= range.e.r; ++R) {
      for (let C = range.s.c; C <= range.e.c; ++C) {
        const cellRef = XLSX.utils.encode_cell({ r: R, c: C })
        if (!ws[cellRef]) ws[cellRef] = { v: '' }
        
        if (R === 0) {
          ws[cellRef].s = headerStyle
        } else {
          const val = ws[cellRef].v
          const isNum = typeof val === 'number'
          ws[cellRef].s = {
            font: { name: 'Microsoft YaHei', sz: 10, bold: isNum },
            fill: { fgColor: { rgb: R % 2 === 0 ? 'FFFFFF' : 'F8FAFC' } },
            alignment: { horizontal: isNum ? 'right' : 'left', vertical: 'center' },
            border: cellBorder,
          }
        }
      }
    }

    // 设置列宽
    const colWidths = headers.map((h, i) => {
      let maxLen = h.length * 2.2
      dataRows.forEach(row => {
        const str = String(row[i] || '')
        if (str.length * 1.6 > maxLen) maxLen = str.length * 1.6
      })
      return { wch: Math.max(12, Math.min(40, Math.ceil(maxLen) + 2)) }
    })
    ws['!cols'] = colWidths

    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '综合台账')
    XLSX.writeFile(wb, filename)
  } catch (err) {
    console.error('导出 Excel 失败:', err)
    alert('导出 Excel 发生错误，请稍后重试。')
  } finally {
    exportLoading.value = false
  }
}
</script>

<style scoped>
.page-layout {
  min-height: 100vh;
  background-color: #f1f5f9;
  padding-bottom: 60px;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  box-sizing: border-box;
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.page-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.page-title-row h2 {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 4px 0 0;
}

/* ========================================================================== */
/* 🔍 全局多维智能筛选控制台 (标准网格排版，拒绝串行) */
/* ========================================================================== */
.filter-hub-card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.05);
}

.filter-hub-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 12px;
}

.filter-hub-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hub-icon {
  font-size: 16px;
}

.hub-text {
  font-size: 14px;
  font-weight: 800;
  color: #1e293b;
}

.hub-tag {
  font-size: 11px;
  background: #eff6ff;
  color: #2563eb;
  padding: 2px 8px;
  border-radius: 99px;
  font-weight: 600;
}

.filter-hub-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-sm {
  height: 32px;
  padding: 0 14px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-ghost {
  background: #f8fafc;
  color: #475569;
  border: 1px solid #cbd5e1;
}
.btn-ghost:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.btn-primary {
  background: #2563eb;
  color: #ffffff;
  border: 1px solid #1d4ed8;
}
.btn-primary:hover {
  background: #1d4ed8;
}

.btn-export {
  background: #ffffff;
  color: #047857;
  border: 1px solid #a7f3d0;
}
.btn-export:hover {
  background: #ecfdf5;
  border-color: #6ee7b7;
}

/* 标准 4 列网格 */
.filter-grid-layout {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  align-items: start;
}

.filter-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.grid-span-2 {
  grid-column: span 2;
}

.cell-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 20px;
}

.cell-label {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.badge-count {
  font-size: 11px;
  color: #2563eb;
  font-weight: 700;
  background: #dbeafe;
  padding: 1px 6px;
  border-radius: 4px;
}

/* 下拉触发器 */
.relative { position: relative; }

.custom-select-trigger {
  width: 100%;
  height: 34px;
  background: #ffffff;
  color: #1e293b;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 10px;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  box-sizing: border-box;
}

.custom-select-trigger:hover {
  border-color: #94a3b8;
}

.trigger-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.dropdown-arrow {
  font-size: 10px;
  color: #94a3b8;
  margin-left: 6px;
}

/* 浮层面板 */
.custom-dropdown-panel {
  position: absolute;
  top: 62px;
  left: 0;
  width: 100%;
  min-width: 240px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0,0,0,0.15), 0 8px 10px -6px rgba(0,0,0,0.08);
  z-index: 100;
  padding: 8px 0;
}

.dropdown-actions {
  display: flex;
  justify-content: space-between;
  padding: 4px 12px 8px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 12px;
}

.btn-link {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  padding: 0;
  font-weight: 700;
}
.btn-link.text-muted { color: #64748b; font-weight: normal; }

.dropdown-list {
  max-height: 240px;
  overflow-y: auto;
  padding: 4px 0;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  transition: background 0.1s;
}
.checkbox-item:hover { background: #f1f5f9; }

/* 输入框 */
.input-with-clear {
  position: relative;
  width: 100%;
}

.form-control {
  width: 100%;
  height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 28px 0 10px;
  font-size: 13px;
  box-sizing: border-box;
  background: #fff;
  color: #1e293b;
}
.form-control:focus {
  border-color: #3b82f6;
  outline: none;
}

.clear-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  cursor: pointer;
  font-size: 11px;
  padding: 2px 4px;
}
.clear-btn:hover { color: #475569; }

/* 日期胶囊与起止框 */
.date-cell {
  min-width: 0;
}

.capsule-group {
  display: flex;
  gap: 4px;
}

.capsule-btn {
  padding: 1px 6px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #64748b;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}
.capsule-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
  font-weight: 700;
}

.date-range-box {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.date-control {
  flex: 1;
  min-width: 0;
  height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 6px;
  font-size: 12px;
  box-sizing: border-box;
  background: #fff;
  color: #1e293b;
}

.range-arrow {
  color: #94a3b8;
  font-size: 11px;
  flex-shrink: 0;
}

/* 已选 Chips 标签栏 */
.active-chips-bar {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.chips-title {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.chip-section { background: #ede9fe; color: #6d28d9; }
.chip-model { background: #e0f2fe; color: #0284c7; }
.chip-keyword { background: #fef3c7; color: #b45309; }
.chip-search { background: #f1f5f9; color: #334155; }

.chip-remove {
  background: none;
  border: none;
  font-size: 11px;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;
  padding: 0;
  margin-left: 2px;
}
.chip-remove:hover { opacity: 1; }

.btn-clear-chips {
  background: none;
  border: none;
  color: #ef4444;
  font-size: 12px;
  cursor: pointer;
  margin-left: auto;
  font-weight: 600;
}
.btn-clear-chips:hover { text-decoration: underline; }

/* ========================================================================== */
/* 📑 标签页栏与子内容区排版 */
/* ========================================================================== */
.tab-content-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 100%;
}

.history-tab-bar {
  display: flex;
  gap: 10px;
  margin: 2px 0 0 0;
}

.tab-pill-btn {
  padding: 10px 22px;
  border-radius: 10px;
  border: 1.5px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  font-size: 13.5px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

.tab-label-full { display: inline; }
.tab-label-short { display: none; }

.tab-pill-btn:hover {
  background: #f8fafc;
  color: #1e293b;
  border-color: #94a3b8;
}

.tab-pill-btn.active {
  background: #1e293b;
  color: #ffffff;
  border-color: #1e293b;
  box-shadow: 0 4px 10px -2px rgba(15, 23, 42, 0.2);
}

/* 子品类栏 (一级子分类：🔥 保温管 | 🔧 管件) */
.sub-pill-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  width: fit-content;
}

.sub-pill {
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
}

.sub-pill:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.sub-pill.active {
  background: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
  box-shadow: 0 2px 6px -1px rgba(2, 132, 199, 0.3);
}

/* 📊 顶部 KPI 看板 (6 列规整网格，统一层级) */
.kpi-banner-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin: 0;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 6px;
  box-shadow: 0 2px 6px -1px rgba(15, 23, 42, 0.04);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px -2px rgba(15, 23, 42, 0.08);
  border-color: #94a3b8;
}

.kpi-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-val {
  font-size: 20px;
  font-weight: 800;
  line-height: 1.15;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-variant-numeric: tabular-nums;
}
.kpi-val small { font-size: 12px; font-weight: 600; margin-left: 2px; }

/* ========================================================================== */
/* 🎛️ 多维透视聚合控制器样式 */
/* ========================================================================== */
/* ========================================================================== */
/* 🎛️ 表格顶部工具栏与多维透视聚合下拉选择器 */
/* ========================================================================== */
.table-toolbar-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  border-radius: 8px 8px 0 0;
}

.toolbar-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.toolbar-title {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
}

.toolbar-count {
  font-size: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 触发器与包装容器 */
.pivot-dropdown-wrap {
  position: relative;
}

.btn-pivot-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #ffffff;
  border: 1.5px solid #0284c7;
  border-radius: 20px;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(2, 132, 199, 0.12);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-pivot-trigger:hover {
  background: #f0f9ff;
  border-color: #0369a1;
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(2, 132, 199, 0.2);
}

.btn-pivot-trigger.active {
  background: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.25);
}

.btn-pivot-trigger.active .trigger-chain {
  color: #e0f2fe;
  background: rgba(0, 0, 0, 0.15);
}

.trigger-icon {
  font-size: 13px;
}

.trigger-label {
  font-weight: 800;
}

.trigger-chain {
  background: #e0f2fe;
  color: #0369a1;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11.5px;
  font-weight: 700;
}

.trigger-arrow {
  font-size: 10px;
  margin-left: 2px;
  transition: transform 0.2s;
}

.btn-pivot-trigger.active .trigger-arrow {
  transform: rotate(180deg);
}

/* 背景点击关闭遮罩 */
.pivot-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 990;
  background: rgba(0, 0, 0, 0.05);
}

/* 浮层面板 */
.pivot-dropdown-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 999;
  width: 330px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15), 0 8px 10px -6px rgba(15, 23, 42, 0.1);
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: dropdownFadeIn 0.18s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes dropdownFadeIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 8px;
}

.panel-title {
  font-size: 12px;
  font-weight: 800;
  color: #334155;
}

.btn-panel-reset {
  background: none;
  border: none;
  color: #64748b;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.btn-panel-reset:hover {
  background: #f1f5f9;
  color: #0284c7;
}

/* 维度选择列表 */
.panel-options-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.panel-opt-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}

.panel-opt-item:hover {
  background: #f0f9ff;
  border-color: #bae6fd;
}

.panel-opt-item.checked {
  background: #f0fdf4;
  border-color: #86efac;
}

.opt-badge-slot {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.badge-active-num {
  width: 20px;
  height: 20px;
  background: #16a34a;
  color: #ffffff;
  font-size: 11px;
  font-weight: 800;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 2px rgba(22, 163, 74, 0.3);
}

.badge-unchecked {
  width: 16px;
  height: 16px;
  border: 1.5px solid #cbd5e1;
  border-radius: 4px;
  background: #ffffff;
}

.opt-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  flex: 1;
}

.opt-order-btns {
  display: flex;
  align-items: center;
  gap: 2px;
}

.btn-rank {
  width: 22px;
  height: 22px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: 4px;
  font-size: 11px;
  font-weight: bold;
  color: #475569;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-rank:hover:not(:disabled) {
  background: #e2e8f0;
  color: #0f172a;
}

.btn-rank:disabled {
  opacity: 0.25;
  cursor: not-allowed;
}

/* 常用方案 */
.panel-presets-row {
  background: #f8fafc;
  border-radius: 8px;
  padding: 8px 10px;
  border: 1px dashed #cbd5e1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.presets-caption {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
}

.presets-btn-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.btn-preset-chip {
  padding: 3px 8px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-preset-chip:hover {
  background: #e0f2fe;
  border-color: #7dd3fc;
  color: #0369a1;
}

.btn-preset-chip.active {
  background: #0284c7;
  border-color: #0284c7;
  color: #ffffff;
  font-weight: 700;
}

.panel-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

.btn-panel-done {
  padding: 6px 16px;
  background: #0284c7;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-panel-done:hover {
  background: #0369a1;
}

.th-dimension {
  background: #f1f5f9 !important;
  color: #0f172a !important;
  font-weight: 800 !important;
  border-right: 1px solid #e2e8f0;
}

/* 🏷️ 核心维度透视列宽 (基于实际文本长度的黄金比例) */
.td-dim-date, .th-dim-date {
  min-width: 110px;
  width: 110px;
  text-align: center !important;
  white-space: nowrap;
}

.td-dim-section, .th-dim-section {
  min-width: 160px;
  text-align: left;
  white-space: nowrap;
}

.td-dim-model, .th-dim-model {
  min-width: 165px;
  text-align: left;
  white-space: nowrap;
}

.td-dim-supplier, .th-dim-supplier {
  min-width: 140px;
  text-align: left;
  white-space: nowrap;
}

.section-cell-text {
  display: inline-block;
  white-space: nowrap;
}

.text-slate { color: #334155; }
.text-sky { color: #0284c7; }
.text-blue { color: #2563eb; }
.text-indigo { color: #4f46e5; }
.text-emerald { color: #059669; }
.text-amber { color: #d97706; }
.text-rose { color: #dc2626; }
.text-dark { color: #0f172a; }

/* 📋 数据表格整体排版与列宽协调 */
.table-card {
  padding: 0;
  overflow: hidden;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #fff;
  position: relative;
  box-shadow: 0 2px 6px -1px rgba(15, 23, 42, 0.04);
}

.table-container {
  max-height: 580px;
  overflow-x: auto;
  overflow-y: auto;
  width: 100%;
  -webkit-overflow-scrolling: touch;
}

.data-table {
  width: 100%;
  min-width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin: 0;
  white-space: nowrap;
}

.data-table thead tr {
  background: #f8fafc;
  border-bottom: 1px solid #cbd5e1;
  position: sticky;
  top: 0;
  z-index: 10;
}

.data-table th {
  padding: 12px 14px;
  font-weight: 700;
  color: #334155;
  background: #f8fafc;
  white-space: nowrap;
}

/* 🔀 表头排序样式 */
.data-table th.sortable-th {
  cursor: pointer;
  user-select: none;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.data-table th.sortable-th:hover {
  background: #f1f5f9;
  color: #0284c7;
}

.data-table th.sortable-th.sorted-col {
  background: #f0f9ff;
  color: #0284c7;
  font-weight: 800;
}

.th-inner-cell {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.th-inner-cell.text-right {
  justify-content: flex-end;
  width: 100%;
}

.th-inner-cell.text-center {
  justify-content: center;
  width: 100%;
}

.sort-arrow {
  font-size: 11px;
  line-height: 1;
  color: #94a3b8;
  opacity: 0.5;
  transition: all 0.15s ease;
}

.sortable-th:hover .sort-arrow {
  opacity: 1;
  color: #0284c7;
}

.sort-arrow.active {
  opacity: 1;
  color: #0284c7;
  font-weight: 900;
}

.data-table td {
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
  white-space: nowrap;
}

/* 🔢 数值量化指标列 (统一 105~110px 等宽字体对齐) */
.data-table th.text-right,
.data-table td.text-right {
  min-width: 105px;
  width: 110px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* 📍 计量单位与状态居中列 */
.data-table th.text-center,
.data-table td.text-center {
  min-width: 70px;
  white-space: nowrap;
}

.clickable-row {
  cursor: pointer;
  transition: background 0.15s;
}
.clickable-row:hover {
  background: #f8fafc;
}

.summary-footer-row {
  background: #f1f5f9;
  font-weight: bold;
  border-top: 2px solid #cbd5e1;
  position: sticky;
  bottom: 0;
  z-index: 5;
}
.summary-footer-row td {
  padding: 12px 14px;
  color: #1e293b;
  background: #f1f5f9;
}

.model-badge {
  background: #e0f2fe;
  color: #0369a1;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 4px;
}

/* 进度条 */
.progress-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar-bg {
  flex: 1;
  height: 8px;
  background: #e2e8f0;
  border-radius: 99px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 99px;
  transition: width 0.3s;
}

.fill-blue { background: #2563eb; }
.fill-emerald { background: #10b981; }

.progress-text {
  font-size: 11.5px;
  font-weight: 700;
  color: #475569;
  min-width: 40px;
}

/* ========================================================================== */
/* 🏢 Tab 3: 顶栏工具条与双视图模式 */
/* ========================================================================== */
.directory-top-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

/* 视图模式切换器 (Segmented Switcher) */
.view-mode-toggle-group {
  display: inline-flex;
  background: #e2e8f0;
  padding: 3px;
  border-radius: 8px;
  gap: 2px;
}

.mode-toggle-btn {
  padding: 6px 14px;
  border: none;
  background: transparent;
  color: #475569;
  font-size: 12.5px;
  font-weight: 700;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-toggle-btn.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.1);
}

.section-view-summary {
  display: flex;
  align-items: center;
}

.summary-pill {
  font-size: 12px;
  font-weight: 700;
  background: #ede9fe;
  color: #6d28d9;
  padding: 4px 10px;
  border-radius: 6px;
}

.group-collapse-controls {
  display: flex;
  gap: 8px;
}

/* 模式 A：手风琴卡片 */
.directory-accordion-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.accordion-group-card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(15, 23, 42, 0.03);
}

.accordion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}

.accordion-header:hover {
  background: #f1f5f9;
}

.accordion-title-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.group-icon {
  font-size: 18px;
}

.group-title {
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
}

.group-desc {
  font-size: 12px;
  color: #64748b;
  margin-left: 4px;
}

.accordion-toggle-arrow {
  font-size: 12px;
  font-weight: 700;
  color: #2563eb;
  display: flex;
  align-items: center;
  gap: 4px;
}

.accordion-body {
  padding: 16px 18px;
  background: #ffffff;
}

.group-empty-tip {
  padding: 20px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.directory-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.compact-entity-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
  transition: transform 0.15s, box-shadow 0.15s;
}

.compact-entity-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px -2px rgba(15, 23, 42, 0.08);
  border-color: #cbd5e1;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 6px;
}

.card-title-group {
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex: 1;
}

.card-main-title {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.3;
}

.card-sub-title {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}

.category-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.badge-supplier { background: #e0f2fe; color: #0284c7; }
.badge-section { background: #ede9fe; color: #6d28d9; }
.badge-manager { background: #dcfce7; color: #15803d; }
.badge-keeper { background: #fef3c7; color: #b45309; }
.badge-global { background: #fee2e2; color: #b91c1c; }

.card-body-compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
}

.contact-highlight-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  padding: 5px 8px;
  border-radius: 6px;
  border: 1px solid #f1f5f9;
}

.contact-person {
  font-weight: 700;
  color: #1e293b;
}

.contact-phone-btn {
  color: #2563eb;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.contact-phone-btn:hover {
  text-decoration: underline;
  color: #1d4ed8;
}

.copy-icon { font-size: 11px; }

.scope-row {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  line-height: 1.4;
}

.scope-label {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  flex-shrink: 0;
  margin-top: 2px;
}

.scope-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.scope-chip {
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 10.5px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 3px;
  border: 1px solid #dbeafe;
}

.chip-global {
  background: #f1f5f9;
  color: #475569;
  border-color: #e2e8f0;
}

.chip-unassigned {
  background: #f8fafc;
  color: #94a3b8;
  border-color: #e2e8f0;
  font-style: italic;
}

.extra-info-row {
  font-size: 11px;
  color: #64748b;
  padding-top: 4px;
  border-top: 1px dashed #f1f5f9;
}

/* ========================================================================== */
/* 🏗️ 模式 B: 按标段综合穿透视图样式 */
/* ========================================================================== */
.section-matrix-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-matrix-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-matrix-card {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 14px 18px;
  box-shadow: 0 2px 4px rgba(15, 23, 42, 0.03);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sec-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
}

.sec-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sec-badge-icon {
  font-size: 18px;
}

.sec-title-text {
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
}

.sec-id-tag {
  font-size: 11px;
  font-family: monospace;
  background: #f1f5f9;
  color: #64748b;
  padding: 1px 6px;
  border-radius: 4px;
}

.sec-summary-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.sec-header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sec-toggle-arrow {
  font-size: 11.5px;
  font-weight: 700;
  color: #2563eb;
  background: #eff6ff;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #dbeafe;
  user-select: none;
}

/* 标段内部 4 大角色网格 */
.sec-card-roles-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.role-column-block {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.role-block-header {
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
  border-bottom: 1px solid rgba(0,0,0,0.05);
}

.role-hdr-supplier { background: #e0f2fe; color: #0369a1; }
.role-hdr-manager { background: #dcfce7; color: #15803d; }
.role-hdr-construction { background: #ede9fe; color: #6d28d9; }
.role-hdr-keeper { background: #fef3c7; color: #b45309; }

.role-block-content {
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  max-height: 220px;
  overflow-y: auto;
}

.role-empty-text {
  font-size: 11.5px;
  color: #94a3b8;
  font-style: italic;
  padding: 4px 0;
}

.role-person-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  border-bottom: 1px dashed #e2e8f0;
  padding-bottom: 5px;
}
.role-person-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.role-main-name {
  font-size: 12.5px;
  font-weight: 700;
  color: #0f172a;
}

.role-contact-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
}

.phone-copy-link {
  color: #2563eb;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.phone-copy-link:hover {
  text-decoration: underline;
  color: #1d4ed8;
}

/* 全网统筹与指挥观察人员卡片 */
.global-dispatch-card {
  background: #ffffff;
  border: 1px solid #fca5a5;
  border-radius: 10px;
  padding: 14px 18px;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.05);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.global-card-header {
  border-bottom: 1px solid #fee2e2;
  padding-bottom: 8px;
}

.global-title-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.global-icon { font-size: 18px; }
.global-title { font-size: 15px; font-weight: 800; color: #991b1b; }
.global-desc { font-size: 12px; color: #64748b; margin-left: 4px; }

.global-card-body-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.global-role-col {
  background: #fff5f5;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.global-col-title {
  font-size: 12.5px;
  font-weight: 700;
  color: #991b1b;
  border-bottom: 1px solid #fee2e2;
  padding-bottom: 4px;
}

.global-tags-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.global-person-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding: 3px 0;
  border-bottom: 1px dashed #fed7d7;
}
.global-person-item:last-child {
  border-bottom: none;
}

/* 弹窗样式 */
.block-modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.block-modal-container {
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
  max-width: 680px;
  width: 100%;
}
.modal-lg { max-width: 780px; }

.block-modal-header {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.bg-sky { background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: #fff; }

.modal-header-icon { font-size: 24px; }
.modal-title { margin: 0; font-size: 16px; font-weight: 800; color: #fff; }
.modal-sub { margin: 2px 0 0; font-size: 12px; color: rgba(255,255,255,0.9); }

.modal-body { padding: 20px; }

.detail-flow-chain {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 16px;
}

.chain-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.step-lbl { font-size: 11px; color: #64748b; font-weight: 600; }
.step-val { font-size: 13.5px; font-weight: 800; }
.chain-arrow { color: #cbd5e1; font-weight: bold; }

.modal-metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.metric-item .lbl { font-size: 11px; color: #64748b; }
.metric-item .val { font-size: 14px; }

.block-modal-actions {
  padding: 12px 20px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
}

.loading-box, .empty-box {
  padding: 40px;
  text-align: center;
  color: #64748b;
  font-size: 13.5px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.font-medium { font-weight: 500; }
.text-left { text-align: left; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.text-muted { color: #64748b; }

/* ========================================================================== */
/* 📱 移动端与平板端高精细响应式排版体系 (放置在样式表最底部，确保高优先级覆盖) */
/* ========================================================================== */

@media (max-width: 1024px) {
  .filter-grid-layout { grid-template-columns: repeat(2, 1fr); }
  .grid-span-2 { grid-column: span 1; }
  .sec-card-roles-grid { grid-template-columns: repeat(2, 1fr); }
  .global-card-body-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 768px) {
  .page-layout {
    padding-bottom: 40px;
  }

  .page-content {
    gap: 12px;
  }

  /* 页面头部紧凑排版 */
  .page-title-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    margin-top: 0;
  }

  .page-title-row h2 {
    font-size: 18px;
  }

  .subtitle {
    font-size: 12px;
    line-height: 1.4;
  }

  .back-btn {
    align-self: flex-start;
    font-size: 12px;
    padding: 4px 10px;
  }

  /* 筛选器控制台移动端 */
  .filter-hub-card {
    padding: 12px 14px;
    border-radius: 10px;
  }

  .filter-hub-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    padding-bottom: 10px;
    margin-bottom: 10px;
  }

  .filter-hub-actions {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 1fr 1.3fr;
    gap: 6px;
  }

  .filter-hub-actions .btn-sm {
    width: 100%;
    justify-content: center;
    padding: 0 4px;
    font-size: 11.5px;
    height: 32px;
  }

  .filter-grid-layout {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .custom-dropdown-panel {
    position: fixed;
    top: auto;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    max-height: 60vh;
    border-radius: 16px 16px 0 0;
    box-shadow: 0 -10px 25px rgba(0,0,0,0.2);
    z-index: 1000;
  }

  .active-chips-bar {
    margin-top: 10px;
    padding-top: 8px;
    gap: 6px;
  }

  .filter-chip {
    font-size: 11px;
    padding: 2px 6px;
  }

  /* 移动端主 Tab 栏与子分类栏：3 等分整齐网格排布 (100% 紧凑贴合屏幕，零超出，零横向滚动) */
  .tab-label-full { display: none !important; }
  .tab-label-short { display: inline !important; font-weight: 700; }

  .history-tab-bar {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 6px !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 0 10px 0 !important;
    padding: 0 !important;
    box-sizing: border-box !important;
  }

  .tab-pill-btn {
    padding: 9px 2px !important;
    font-size: 12px !important;
    text-align: center !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    width: 100% !important;
    border-radius: 8px !important;
    box-sizing: border-box !important;
  }

  /* 子分类胶囊栏 (全部/供货/现场/施工/库管/系统) 3 列网格排布 (零超出) */
  .sub-pill-bar {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 6px !important;
    width: 100% !important;
    max-width: 100% !important;
    padding: 0 !important;
    box-sizing: border-box !important;
  }

  .sub-pill {
    padding: 7px 2px !important;
    font-size: 11.5px !important;
    text-align: center !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }

  /* 模式切换器移动端平分宽度 */
  .directory-top-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .view-mode-toggle-group {
    width: 100%;
    display: flex;
  }

  .mode-toggle-btn {
    flex: 1;
    text-align: center;
    padding: 7px 6px;
    font-size: 12px;
  }

  .section-view-controls {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .group-collapse-controls {
    width: 100%;
    justify-content: flex-end;
  }

  /* KPI 看板 2 列精巧自适应 */
  .kpi-banner-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 12px;
  }

  .kpi-card {
    padding: 8px 10px;
    gap: 2px;
  }

  .kpi-label {
    font-size: 11px;
  }

  .kpi-val {
    font-size: 16px;
  }

  .kpi-sub {
    font-size: 10px;
  }

  /* 移动端表格工具栏与聚合下拉选择器 */
  .table-toolbar-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 10px 12px;
  }

  .toolbar-left {
    justify-content: space-between;
  }

  .toolbar-right {
    width: 100%;
  }

  .pivot-dropdown-wrap {
    width: 100%;
  }

  .btn-pivot-trigger {
    width: 100%;
    justify-content: space-between;
    padding: 7px 12px;
  }

  .pivot-dropdown-panel {
    position: fixed;
    top: auto;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100vw;
    border-radius: 16px 16px 0 0;
    box-shadow: 0 -8px 30px rgba(0, 0, 0, 0.25);
    z-index: 1000;
    max-height: 80vh;
    overflow-y: auto;
    padding: 16px;
  }

  /* 表格移动端 */
  .table-container {
    max-height: 480px;
    -webkit-overflow-scrolling: touch;
  }

  .data-table th, .data-table td {
    padding: 8px 10px;
    font-size: 12px;
    white-space: nowrap;
  }

  .summary-footer-row td {
    padding: 10px 10px;
    font-size: 12px;
  }

  .progress-wrap {
    min-width: 100px;
  }

  /* 模式 A: 手风琴卡片移动端 */
  .accordion-header {
    padding: 10px 14px;
  }

  .accordion-title-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .group-title {
    font-size: 14px;
  }

  .group-desc {
    font-size: 11px;
    margin-left: 0;
  }

  .accordion-body {
    padding: 10px;
  }

  .directory-cards-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .compact-entity-card {
    padding: 10px 12px;
  }

  .contact-phone-btn {
    background: #eff6ff;
    padding: 3px 8px;
    border-radius: 4px;
    border: 1px solid #dbeafe;
    font-size: 12px;
  }

  /* ======================================================================== */
  /* 🏗️ 模式 B: 按标段综合穿透卡片在手机端的极致清爽化重构 */
  /* ======================================================================== */
  .section-matrix-card {
    padding: 0 !important;
    overflow: hidden;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important;
    margin-bottom: 10px;
    gap: 0 !important;
  }

  .sec-card-header {
    padding: 12px 14px !important;
    background: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .sec-title-wrap {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .sec-title-text {
    font-size: 15px;
  }

  .sec-header-right {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
  }

  .sec-summary-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .sec-summary-badges .badge {
    font-size: 10.5px;
    padding: 1px 5px;
  }

  .sec-toggle-arrow {
    font-size: 11px;
    padding: 2px 7px;
    flex-shrink: 0;
  }

  .sec-card-roles-grid {
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
    background: #ffffff;
  }

  .role-column-block {
    background: #ffffff !important;
    border: none !important;
    border-bottom: 1px solid #f1f5f9 !important;
    border-radius: 0 !important;
    padding: 10px 14px !important;
  }
  .role-column-block:last-child {
    border-bottom: none !important;
  }

  .role-block-header {
    background: transparent !important;
    padding: 0 0 6px 0 !important;
    border-bottom: none !important;
    font-size: 12.5px !important;
    font-weight: 800;
  }
  .role-hdr-supplier { color: #0284c7 !important; }
  .role-hdr-manager { color: #15803d !important; }
  .role-hdr-construction { color: #6d28d9 !important; }
  .role-hdr-keeper { color: #b45309 !important; }

  .role-block-content {
    padding: 0 !important;
    gap: 6px !important;
    max-height: none !important;
    overflow: visible !important;
  }

  .role-person-item {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 0;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .role-main-name {
    font-size: 13px;
    font-weight: 700;
  }

  .role-contact-line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
  }

  .phone-copy-link {
    background: #eff6ff !important;
    padding: 3px 8px !important;
    border-radius: 4px !important;
    border: 1px solid #dbeafe !important;
    font-size: 11.5px !important;
    font-weight: 700 !important;
  }

  /* 🌐 全网统筹卡片手机端 */
  .global-dispatch-card {
    padding: 0 !important;
    overflow: hidden;
    border: 1px solid #fca5a5 !important;
    border-radius: 10px !important;
    gap: 0 !important;
  }

  .global-card-header {
    padding: 12px 14px !important;
    background: #fff5f5;
    border-bottom: 1px solid #fee2e2;
  }

  .global-title-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .global-title {
    font-size: 14.5px;
  }

  .global-desc {
    font-size: 11px;
    margin-left: 0;
  }

  .global-card-body-grid {
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
    background: #ffffff;
  }

  .global-role-col {
    background: #ffffff !important;
    border: none !important;
    border-bottom: 1px solid #fef2f2 !important;
    border-radius: 0 !important;
    padding: 10px 14px !important;
    gap: 6px;
  }
  .global-role-col:last-child {
    border-bottom: none !important;
  }

  .global-col-title {
    padding-bottom: 4px;
    margin-bottom: 4px;
    font-size: 12.5px;
  }

  .global-person-item {
    background: #fff5f5;
    border: 1px solid #fed7d7;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
  }

  /* 弹窗移动端 */
  .block-modal-overlay {
    padding: 10px;
  }

  .block-modal-container {
    border-radius: 10px;
    max-height: 90vh;
    overflow-y: auto;
  }

  .block-modal-header {
    padding: 12px 14px;
    gap: 8px;
  }

  .modal-body {
    padding: 12px 14px;
  }

  .detail-flow-chain {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    padding: 10px;
  }

  .chain-arrow {
    display: none;
  }
}

@media (max-width: 1200px) {
  .kpi-banner-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .kpi-banner-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .filter-grid-layout {
    grid-template-columns: 1fr;
  }
  .grid-span-2 {
    grid-column: span 1;
  }
}

@media (max-width: 480px) {
  .kpi-banner-grid { grid-template-columns: 1fr; }
  .filter-hub-actions { grid-template-columns: 1fr; }
  .detail-flow-chain { grid-template-columns: 1fr; }
  .modal-metrics-grid { grid-template-columns: 1fr; }
  .fitting-tab2-sub-nav { flex-direction: column; }
}

/* ========================================================================== */
/* 🔧 管件模式专属子视图切换导航栏 (双表独立查询) */
/* ========================================================================== */
.fitting-tab2-sub-nav {
  display: flex;
  gap: 10px;
  background: #ffffff;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid #cbd5e1;
  box-shadow: 0 2px 6px -1px rgba(15, 23, 42, 0.04);
}

.btn-sub-view {
  flex: 1;
  height: 40px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-size: 13.5px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
}

.btn-sub-view:hover {
  background: #f1f5f9;
  color: #1e293b;
  border-color: #cbd5e1;
}

.btn-sub-view.active {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #93c5fd;
  box-shadow: 0 2px 8px -2px rgba(37, 99, 235, 0.15);
}

.sub-view-badge {
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
  opacity: 0.85;
}

.badge-sub-model {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 6px;
}

.empty-cell {
  text-align: center;
  padding: 40px 20px;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 500;
}
</style>
