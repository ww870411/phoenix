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
                v-if="canExtractXlsx"
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

            <!-- 第 3 列：业务时段 (每日流转与供给方台账均支持日期查询) -->
            <div class="filter-cell date-cell" v-if="activeTab === 'daily_flow' || activeTab === 'supplier_ledger'">
              <div class="cell-label-row">
                <span class="cell-label">📅 查询时段</span>
                <div class="capsule-group">
                  <button 
                    type="button" 
                    :class="['capsule-btn', { active: activeDateCapsule === 'project' }]"
                    @click="setDateRangeByCapsule('project')"
                  >项目至今</button>
                  <button 
                    type="button" 
                    :class="['capsule-btn', { active: activeDateCapsule === '30days' }]"
                    @click="setDateRangeByCapsule('30days')"
                  >近30天</button>
                  <button 
                    type="button" 
                    :class="['capsule-btn', { active: activeDateCapsule === '7days' }]"
                    @click="setDateRangeByCapsule('7days')"
                  >近7天</button>
                </div>
              </div>
              <div class="date-range-box">
                <input v-model="filterStartDate" class="input date-control" type="date" @change="onDateInputChange" />
                <span class="range-arrow">➔</span>
                <input v-model="filterEndDate" class="input date-control" type="date" @change="onDateInputChange" />
              </div>
            </div>

            <!-- 第 4 列：全局模糊速搜 -->
            <div class="filter-cell search-cell" :class="{ 'grid-span-2': activeTab !== 'daily_flow' && activeTab !== 'supplier_ledger' }">
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

        <!-- 📑 4 大核心综合标签页 (Tabs) -->
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
            <span class="tab-label-full">📐 设计量、采购量与采购价格</span>
            <span class="tab-label-short">📐 设计·采购·价格</span>
          </button>
          <button
            type="button"
            :class="['tab-pill-btn', { active: activeTab === 'supplier_ledger' }]"
            @click="switchMainTab('supplier_ledger')"
          >
            <span class="tab-label-full">🏭 供给方发货流转台账</span>
            <span class="tab-label-short">🏭 供给方台账</span>
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
          <!-- 子品类切换 (直管 / 管件 / 采购价格) -->
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
            <button 
              type="button" 
              :class="['sub-pill', { active: subMaterialType === 'price' }]"
              @click="switchSubMaterial('price')"
            >
              💰 采购价格 <span class="sub-pill-lock-tag">{{ isPriceUnlocked ? '🔓' : '🔒' }}</span>
            </button>
          </div>

          <!-- 🔐 未解锁采购价格时的受控保护卡片 -->
          <div v-if="subMaterialType === 'price' && !isPriceUnlocked" class="card elevated price-locked-view">
            <div class="price-locked-content">
              <div class="price-locked-icon">🔐</div>
              <h3 class="price-locked-title">物料采购价格字典已受控保护</h3>
              <p class="price-locked-desc">查看保温管与管件采购基准单价需要输入 4 位安全访问码</p>
              <button type="button" class="btn btn-primary btn-unlock-action" @click="openPriceAuthModal">
                🔑 输入访问码解锁查看
              </button>
            </div>
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

          <div class="kpi-banner-grid" v-else-if="subMaterialType === 'fitting'">
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

          <!-- 💰 采购价格专属 KPI 看板 (已解锁时展示) -->
          <div class="kpi-banner-grid" v-else-if="subMaterialType === 'price' && isPriceUnlocked">
            <div class="kpi-card">
              <span class="kpi-label">🏷️ 筛选单价条目</span>
              <span class="kpi-val text-slate">{{ filteredMaterialPriceRows.length }} <small>/ {{ materialPriceList.length }} 项</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🏭 涉及供货单位</span>
              <span class="kpi-val text-sky">{{ priceSuppliersCount }} <small>家企业</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🔥 保温管单价</span>
              <span class="kpi-val text-orange">{{ pricePipeCount }} <small>项规格</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🔧 管件单价</span>
              <span class="kpi-val text-blue">{{ priceFittingCount }} <small>项品类</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">💎 覆盖物理品类</span>
              <span class="kpi-val text-indigo">{{ priceCategoriesCount }} <small>种类别</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📊 筛选物料均价</span>
              <span class="kpi-val text-emerald font-mono">¥{{ priceAverageDisplay }}</span>
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

          <!-- 对照表格 (未解锁价格时不渲染价格表格) -->
          <div v-if="subMaterialType !== 'price' || isPriceUnlocked" class="card elevated table-card">
            <!-- 🎛️ 表格顶部紧凑工具栏 (含聚合维度下拉选择器 / 价格筛选器) -->
            <div class="table-toolbar-row">
              <div class="toolbar-left">
                <span class="toolbar-title">
                  <template v-if="subMaterialType === 'pipe'">📐 保温管设计采购与施工进度基准对照</template>
                  <template v-else-if="subMaterialType === 'fitting' && fittingTab2SubView === 'baseline'">📐 管件设计与计划采购基准表</template>
                  <template v-else-if="subMaterialType === 'fitting'">🚚 管件全周期累计流转与现场库存表</template>
                  <template v-else>💰 保温管与管件标准物料采购单价字典</template>
                </span>
                <span class="toolbar-count font-mono text-muted">
                  <template v-if="subMaterialType === 'price'">
                    ({{ filteredMaterialPriceRows.length }} / {{ materialPriceList.length }} 项单价)
                  </template>
                  <template v-else>
                    ({{ subMaterialType === 'pipe' ? aggregatedBaselineRows.length : (fittingTab2SubView === 'baseline' ? aggregatedFittingBaselineRows.length : aggregatedFittingFlowRows.length) }} 组聚合数据)
                  </template>
                </span>
              </div>

              <!-- 💰 价格模式专属紧凑筛选器 -->
              <div v-if="subMaterialType === 'price'" class="toolbar-right price-filters-inline">
                <!-- 大类筛选 -->
                <div class="filter-select-item">
                  <label class="filter-item-label">大类:</label>
                  <select v-model="priceFilterKind" class="form-select-compact">
                    <option value="all">全部大类</option>
                    <option value="pipe">🔥 保温管</option>
                    <option value="fitting">🔧 管件</option>
                  </select>
                </div>

                <!-- 供给方筛选 -->
                <div class="filter-select-item">
                  <label class="filter-item-label">供给方:</label>
                  <select v-model="priceFilterSupplier" class="form-select-compact">
                    <option value="all">全部供给方 ({{ priceSupplierOptions.length }})</option>
                    <option v-for="sup in priceSupplierOptions" :key="`p-sup-${sup}`" :value="sup">{{ sup }}</option>
                  </select>
                </div>

                <!-- 物理类别筛选 -->
                <div class="filter-select-item">
                  <label class="filter-item-label">物理类别:</label>
                  <select v-model="priceFilterCategory" class="form-select-compact">
                    <option value="all">全部类别 ({{ priceCategoryOptions.length }})</option>
                    <option v-for="cat in priceCategoryOptions" :key="`p-cat-${cat}`" :value="cat">{{ cat }}</option>
                  </select>
                </div>

                <!-- 搜索框 -->
                <div class="filter-search-item">
                  <input 
                    v-model="priceFilterKeyword" 
                    type="text" 
                    placeholder="🔍 搜索规格/型号/材料..." 
                    class="form-input-compact" 
                  />
                  <button v-if="priceFilterKeyword" type="button" class="btn-clear-kw" @click="priceFilterKeyword = ''">×</button>
                </div>

                <!-- 重置 -->
                <button 
                  type="button" 
                  class="btn-reset-price-filter" 
                  title="重置价格表筛选"
                  @click="resetPriceFilters"
                >
                  🔄 重置
                </button>

                <!-- 锁定 -->
                <button 
                  type="button" 
                  class="btn-reset-price-filter btn-lock-price" 
                  title="安全退出并重新加锁"
                  @click="lockPriceAccess"
                >
                  🔒 重新加锁
                </button>
              </div>

              <div v-else class="toolbar-right">
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
              <table v-else-if="subMaterialType === 'fitting' && fittingTab2SubView === 'baseline'" class="data-table">
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
                        <span class="font-medium text-sky">{{ row.supplier_name }}</span>
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
              <table v-else-if="subMaterialType === 'fitting'" class="data-table">
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

              <!-- 4. 保温管与管件物料采购单价字典表 (采购价格专属子表) -->
              <table v-else-if="subMaterialType === 'price'" class="data-table">
                <thead>
                  <tr>
                    <th class="text-center" style="width: 55px;">#</th>
                    <th 
                      class="text-center sortable-th" 
                      style="width: 95px;"
                      :class="{ 'sorted-col': isColumnSorted('price_table', 'material_kind') }"
                      @click="handleTableSort('price_table', 'material_kind')"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell text-center">
                        <span>大类</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('price_table', 'material_kind') }">{{ getSortIcon('price_table', 'material_kind') }}</span>
                      </div>
                    </th>
                    <th 
                      class="text-left sortable-th"
                      :class="{ 'sorted-col': isColumnSorted('price_table', 'supplier_name') }"
                      @click="handleTableSort('price_table', 'supplier_name')"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>供给方全称</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('price_table', 'supplier_name') }">{{ getSortIcon('price_table', 'supplier_name') }}</span>
                      </div>
                    </th>
                    <th 
                      class="text-left sortable-th" 
                      style="width: 110px;"
                      :class="{ 'sorted-col': isColumnSorted('price_table', 'category') }"
                      @click="handleTableSort('price_table', 'category')"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>物理类别</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('price_table', 'category') }">{{ getSortIcon('price_table', 'category') }}</span>
                      </div>
                    </th>
                    <th 
                      class="text-left sortable-th"
                      :class="{ 'sorted-col': isColumnSorted('price_table', 'material_name') }"
                      @click="handleTableSort('price_table', 'material_name')"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>材料标准名称</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('price_table', 'material_name') }">{{ getSortIcon('price_table', 'material_name') }}</span>
                      </div>
                    </th>
                    <th 
                      class="text-left sortable-th"
                      :class="{ 'sorted-col': isColumnSorted('price_table', 'model_spec') }"
                      @click="handleTableSort('price_table', 'model_spec')"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>规格型号描述</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('price_table', 'model_spec') }">{{ getSortIcon('price_table', 'model_spec') }}</span>
                      </div>
                    </th>
                    <th 
                      class="text-center sortable-th" 
                      style="width: 70px;"
                      :class="{ 'sorted-col': isColumnSorted('price_table', 'unit') }"
                      @click="handleTableSort('price_table', 'unit')"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell text-center">
                        <span>单位</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('price_table', 'unit') }">{{ getSortIcon('price_table', 'unit') }}</span>
                      </div>
                    </th>
                    <th 
                      class="text-right sortable-th" 
                      style="width: 145px;"
                      :class="{ 'sorted-col': isColumnSorted('price_table', 'unit_price') }"
                      @click="handleTableSort('price_table', 'unit_price')"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell text-right">
                        <span>单价 (元)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('price_table', 'unit_price') }">{{ getSortIcon('price_table', 'unit_price') }}</span>
                      </div>
                    </th>
                    <th class="text-left" style="min-width: 160px;">备注说明</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="sortedMaterialPriceRows.length === 0">
                    <td colspan="9" class="empty-cell">未查询到符合条件的物料采购价格记录</td>
                  </tr>
                  <tr v-for="(row, idx) in sortedMaterialPriceRows" :key="`price-row-${row.id || idx}`">
                    <td class="text-center text-muted font-mono">{{ idx + 1 }}</td>
                    <td class="text-center">
                      <span :class="['badge-tag', row.material_kind === 'pipe' ? 'badge-pipe' : 'badge-fitting']">
                        {{ row.material_kind === 'pipe' ? '🔥 保温管' : '🔧 管件' }}
                      </span>
                    </td>
                    <td class="text-left font-bold text-sky">{{ row.supplier_name }}</td>
                    <td class="text-left text-slate font-medium">{{ row.category }}</td>
                    <td class="text-left text-dark font-medium">{{ row.material_name }}</td>
                    <td class="text-left font-bold text-slate">
                      <span>{{ row.model_spec }}</span>
                    </td>
                    <td class="text-center text-muted font-medium">{{ row.unit || '个' }}</td>
                    <td class="text-right font-mono font-bold text-emerald" style="font-size: 14px;">
                      ¥{{ Number(row.unit_price).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                    </td>
                    <td class="text-left text-muted" style="font-size: 12px;">{{ row.remark || '—' }}</td>
                  </tr>

                  <!-- 汇总行 -->
                  <tr v-if="sortedMaterialPriceRows.length > 0" class="summary-footer-row">
                    <td colspan="7" class="text-left">
                      💰 当前筛选物料单价总览 (共 {{ sortedMaterialPriceRows.length }} 条记录 / 覆盖 {{ priceFilteredSuppliersCount }} 家供给方)
                    </td>
                    <td class="text-right font-mono font-bold text-emerald">
                      均价: ¥{{ priceFilteredAvgDisplay }}
                    </td>
                    <td class="text-center text-muted">—</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- ==================================================================== -->
        <!-- 🏭 Tab 3: 供给方发货流转台账 (纯发货订单驱动) -->
        <!-- ==================================================================== -->
        <section v-else-if="activeTab === 'supplier_ledger'" class="tab-content-section">
          <!-- 子品类切换与总价联动选框 -->
          <div class="sub-pill-bar flex justify-between items-center">
            <div class="flex gap-2">
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

            <!-- 💰 保温管结合厂家与型号计算总价选框 -->
            <div v-if="subMaterialType === 'pipe'" class="pipe-calc-price-toggle-wrap">
              <label class="calc-price-label" title="结合供给主体与规格型号自动匹配基准单价，核算发运与到货货值总价">
                <input 
                  type="checkbox" 
                  :checked="showPipeAmountCalc" 
                  @change="handlePipeCalcToggle" 
                  class="calc-price-checkbox"
                />
                <span class="calc-price-text">💰 结合供给方与型号计算总价</span>
                <span v-if="showPipeAmountCalc" class="calc-active-tag">已开启计算</span>
              </label>
            </div>
          </div>

          <!-- 顶部 KPI 开会速读看板 -->
          <div class="kpi-banner-grid" v-if="subMaterialType === 'pipe'">
            <div class="kpi-card">
              <span class="kpi-label">🏭 供给侧累计发货</span>
              <span class="kpi-val text-sky">{{ formatQty(supplierLedgerSummary.total_shipped_qty) }} <small>米</small></span>
              <span v-if="showPipeAmountCalc" class="kpi-amount-sub text-sky font-mono font-bold">
                ¥{{ formatAmountWan(supplierLedgerSummary.total_shipped_amount) }} 万元
              </span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📥 现场确认总到货</span>
              <span class="kpi-val text-blue">{{ formatQty(supplierLedgerSummary.total_arrived_qty) }} <small>米</small></span>
              <span v-if="showPipeAmountCalc" class="kpi-amount-sub text-blue font-mono font-bold">
                ¥{{ formatAmountWan(supplierLedgerSummary.total_arrived_amount) }} 万元
              </span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">👷 施工接收总量</span>
              <span class="kpi-val text-indigo">{{ formatQty(supplierLedgerSummary.total_received_qty) }} <small>米</small></span>
              <span v-if="showPipeAmountCalc" class="kpi-amount-sub text-indigo font-mono font-bold">
                ¥{{ formatAmountWan(supplierLedgerSummary.total_received_amount) }} 万元
              </span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">💼 库管已入库总量</span>
              <span class="kpi-val text-amber">{{ formatQty(supplierLedgerSummary.total_warehouse_qty) }} <small>米</small></span>
              <span v-if="showPipeAmountCalc" class="kpi-amount-sub text-amber font-mono font-bold">
                ¥{{ formatAmountWan(supplierLedgerSummary.total_warehouse_amount) }} 万元
              </span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">🚚 发运订单车次</span>
              <span class="kpi-val text-slate">{{ supplierLedgerSummary.total_orders_count }} <small>单/车</small></span>
              <span v-if="showPipeAmountCalc" class="kpi-amount-sub text-slate font-mono">
                单均货值 ¥{{ formatAmountWan(supplierLedgerSummary.avg_order_amount) }}万
              </span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">⏱️ 平均在途时长</span>
              <span class="kpi-val text-slate">{{ supplierLedgerSummary.overall_avg_transit }}</span>
              <span v-if="showPipeAmountCalc" class="kpi-amount-sub text-emerald font-mono font-bold">
                履约货值率 {{ supplierLedgerSummary.overall_fulfillment_rate }}%
              </span>
            </div>
          </div>

          <div class="kpi-banner-grid" v-else>
            <div class="kpi-card">
              <span class="kpi-label">🏭 累计发货管件</span>
              <span class="kpi-val text-sky">{{ supplierLedgerSummary.total_shipped_qty }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📥 确认到货总数</span>
              <span class="kpi-val text-blue">{{ supplierLedgerSummary.total_arrived_qty }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">👷 施工接收总数</span>
              <span class="kpi-val text-indigo">{{ supplierLedgerSummary.total_received_qty }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">💼 库管已入库</span>
              <span class="kpi-val text-amber">{{ supplierLedgerSummary.total_warehouse_qty }} <small>件</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">📦 发货批次订单</span>
              <span class="kpi-val text-slate">{{ supplierLedgerSummary.total_orders_count }} <small>单/批</small></span>
            </div>
            <div class="kpi-card">
              <span class="kpi-label">⏱️ 平均在途时长</span>
              <span class="kpi-val text-slate">{{ supplierLedgerSummary.overall_avg_transit }}</span>
            </div>
          </div>

          <!-- 表格主体 -->
          <div class="card elevated table-card">
            <!-- 🎛️ 表格顶部紧凑工具栏 (含聚合维度下拉选择器) -->
            <div class="table-toolbar-row">
              <div class="toolbar-left">
                <span class="toolbar-title">🏭 供给方发运台账明细与多维透视</span>
                <span class="toolbar-count font-mono text-muted">({{ aggregatedSupplierLedgerRows.length }} 组聚合 / {{ filteredSupplierLedgerRows.length }} 单)</span>
              </div>

              <div class="toolbar-right">
                <!-- 聚合维度下拉触发与菜单 -->
                <div class="pivot-dropdown-wrap">
                  <button 
                    type="button" 
                    :class="['btn-pivot-trigger', { active: activePivotDropdown === 'supplier_ledger' }]"
                    @click.stop="togglePivotDropdown('supplier_ledger')"
                  >
                    <span class="trigger-icon">🎛️</span>
                    <span class="trigger-label">聚合维度:</span>
                    <span class="trigger-chain">{{ getDimensionChainText('supplier_ledger') }}</span>
                    <span class="trigger-arrow">▾</span>
                  </button>

                  <!-- 背景点击遮罩 -->
                  <div 
                    v-if="activePivotDropdown === 'supplier_ledger'" 
                    class="pivot-backdrop" 
                    @click.stop="closePivotDropdown"
                  ></div>

                  <!-- 浮层下拉列表面板 -->
                  <div 
                    v-if="activePivotDropdown === 'supplier_ledger'" 
                    class="pivot-dropdown-panel card elevated"
                    @click.stop
                  >
                    <div class="panel-header">
                      <span class="panel-title">选择透视维度（按勾选顺序依次分组）</span>
                      <button type="button" class="btn-panel-reset" @click="resetToDefaultDimensions('supplier_ledger')">↺ 恢复默认</button>
                    </div>

                    <!-- 维度有序多选列表 -->
                    <div class="panel-options-list">
                      <div 
                        v-for="dim in getAvailableDimensions('supplier_ledger')" 
                        :key="`sup-opt-${dim.id}`"
                        :class="['panel-opt-item', { checked: isDimensionSelected('supplier_ledger', dim.id) }]"
                        @click="toggleDimensionSelection('supplier_ledger', dim.id)"
                      >
                        <div class="opt-badge-slot">
                          <span v-if="isDimensionSelected('supplier_ledger', dim.id)" class="badge-active-num">{{ getDimensionOrder('supplier_ledger', dim.id) }}</span>
                          <span v-else class="badge-unchecked"></span>
                        </div>
                        <span class="opt-name">{{ dim.label }}</span>
                        
                        <div v-if="isDimensionSelected('supplier_ledger', dim.id)" class="opt-order-btns" @click.stop>
                          <button 
                            type="button" 
                            class="btn-rank" 
                            :disabled="getDimensionOrder('supplier_ledger', dim.id) === 1"
                            title="提升此维度分组优先级"
                            @click="moveDimensionUp('supplier_ledger', dim.id)"
                          >
                            ↑
                          </button>
                          <button 
                            type="button" 
                            class="btn-rank" 
                            :disabled="getDimensionOrder('supplier_ledger', dim.id) === supplierLedgerDimensions.length"
                            title="降低此维度分组优先级"
                            @click="moveDimensionDown('supplier_ledger', dim.id)"
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
                          v-for="(p, pIdx) in supplierLedgerDimensionPresets"
                          :key="`p-sup-${pIdx}`"
                          type="button"
                          :class="['btn-preset-chip', { active: isCurrentPreset('supplier_ledger', p.dims) }]"
                          @click="applyDimensionPreset('supplier_ledger', p.dims)"
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
              <span>⏳ 正在汇总供给方发货流转数据...</span>
            </div>
            
            <div v-else-if="aggregatedSupplierLedgerRows.length === 0" class="empty-box">未查询到符合条件的供给方发货单记录。</div>

            <div v-else class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <!-- 动态维度表头 -->
                    <th 
                      v-for="dim in supplierLedgerDimensions" 
                      :key="`th-sup-${dim}`"
                      :class="['text-left', 'th-dimension', `th-dim-${dim}`, 'sortable-th', { 'sorted-col': isColumnSorted('supplier_ledger', dim) }]"
                      @click="handleTableSort('supplier_ledger', dim)"
                      title="点击切换排序：升序 / 降序 / 恢复默认"
                    >
                      <div class="th-inner-cell">
                        <span>{{ getDimensionDef(dim).colHeader }}</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', dim) }">{{ getSortIcon('supplier_ledger', dim) }}</span>
                      </div>
                    </th>

                    <!-- 💰 单价 (元/米) -->
                    <th v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'unit_price') }" @click="handleTableSort('supplier_ledger', 'unit_price')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span class="text-slate font-bold">单价 (元/米)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'unit_price') }">{{ getSortIcon('supplier_ledger', 'unit_price') }}</span>
                      </div>
                    </th>

                    <!-- 发货量 -->
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'shipped_qty') }" @click="handleTableSort('supplier_ledger', 'shipped_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>发货量 ({{ subMaterialType === 'pipe' ? '米' : '件' }})</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'shipped_qty') }">{{ getSortIcon('supplier_ledger', 'shipped_qty') }}</span>
                      </div>
                    </th>
                    <!-- 💰 发货总额 -->
                    <th v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'shipped_amount') }" @click="handleTableSort('supplier_ledger', 'shipped_amount')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span class="text-sky font-bold">发货金额 (元)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'shipped_amount') }">{{ getSortIcon('supplier_ledger', 'shipped_amount') }}</span>
                      </div>
                    </th>

                    <!-- 确认到货 -->
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'arrived_qty') }" @click="handleTableSort('supplier_ledger', 'arrived_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>确认到货 ({{ subMaterialType === 'pipe' ? '米' : '件' }})</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'arrived_qty') }">{{ getSortIcon('supplier_ledger', 'arrived_qty') }}</span>
                      </div>
                    </th>
                    <!-- 💰 到货总额 -->
                    <th v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'arrived_amount') }" @click="handleTableSort('supplier_ledger', 'arrived_amount')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span class="text-blue font-bold">到货金额 (元)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'arrived_amount') }">{{ getSortIcon('supplier_ledger', 'arrived_amount') }}</span>
                      </div>
                    </th>

                    <!-- 施工接收 -->
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'received_qty') }" @click="handleTableSort('supplier_ledger', 'received_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>施工接收 ({{ subMaterialType === 'pipe' ? '米' : '件' }})</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'received_qty') }">{{ getSortIcon('supplier_ledger', 'received_qty') }}</span>
                      </div>
                    </th>
                    <!-- 💰 接收总额 -->
                    <th v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'received_amount') }" @click="handleTableSort('supplier_ledger', 'received_amount')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span class="text-indigo font-bold">接收金额 (元)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'received_amount') }">{{ getSortIcon('supplier_ledger', 'received_amount') }}</span>
                      </div>
                    </th>

                    <!-- 库管确认 -->
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'warehouse_qty') }" @click="handleTableSort('supplier_ledger', 'warehouse_qty')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>库管已确认 ({{ subMaterialType === 'pipe' ? '米' : '件' }})</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'warehouse_qty') }">{{ getSortIcon('supplier_ledger', 'warehouse_qty') }}</span>
                      </div>
                    </th>
                    <!-- 💰 入库总额 -->
                    <th v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'warehouse_amount') }" @click="handleTableSort('supplier_ledger', 'warehouse_amount')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span class="text-amber font-bold">入库金额 (元)</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'warehouse_amount') }">{{ getSortIcon('supplier_ledger', 'warehouse_amount') }}</span>
                      </div>
                    </th>

                    <!-- 在途时长 -->
                    <th class="text-center">在途时长</th>

                    <!-- 发运单数 -->
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'orders_count') }" @click="handleTableSort('supplier_ledger', 'orders_count')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>发运单数</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'orders_count') }">{{ getSortIcon('supplier_ledger', 'orders_count') }}</span>
                      </div>
                    </th>

                    <!-- 到货确认率进度 -->
                    <th class="text-left" style="min-width: 120px;">到货确认率</th>

                    <!-- 接收确认率 -->
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'receipt_rate') }" @click="handleTableSort('supplier_ledger', 'receipt_rate')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>接收确认率</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'receipt_rate') }">{{ getSortIcon('supplier_ledger', 'receipt_rate') }}</span>
                      </div>
                    </th>

                    <!-- 库管确认率 -->
                    <th class="text-right sortable-th" :class="{ 'sorted-col': isColumnSorted('supplier_ledger', 'warehouse_rate') }" @click="handleTableSort('supplier_ledger', 'warehouse_rate')" title="点击切换排序：升序 / 降序 / 恢复默认">
                      <div class="th-inner-cell text-right">
                        <span>库管确认率</span>
                        <span class="sort-arrow" :class="{ active: isColumnSorted('supplier_ledger', 'warehouse_rate') }">{{ getSortIcon('supplier_ledger', 'warehouse_rate') }}</span>
                      </div>
                    </th>

                    <!-- 操作/穿透 -->
                    <th class="text-center" style="min-width: 90px;">发运单穿透</th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="(row, idx) in sortedSupplierLedgerRows" 
                    :key="idx" 
                    class="clickable-row"
                    @click="openSupplierOrderModal(row)"
                  >
                    <!-- 动态维度单元格 -->
                    <td 
                      v-for="dim in supplierLedgerDimensions" 
                      :key="`td-sup-${dim}`" 
                      :class="['text-left', `td-dim-${dim}`]"
                    >
                      <template v-if="dim === 'supplier'">
                        <span class="font-bold text-sky">{{ row.supplier_name }}</span>
                      </template>
                      <template v-else-if="dim === 'model'">
                        <template v-if="subMaterialType === 'pipe'">
                          <span class="badge model-badge">{{ row.pipe_model_name }}</span>
                        </template>
                        <template v-else>
                          <span class="font-bold text-slate">{{ row.fitting_type }}</span>
                          <span class="font-medium text-muted" style="margin-left: 4px;">{{ row.model_spec }}</span>
                        </template>
                      </template>
                      <template v-else-if="dim === 'date'">
                        <span class="font-mono font-medium">{{ row.biz_date }}</span>
                      </template>
                      <template v-else-if="dim === 'section'">
                        <span class="font-bold text-dark section-cell-text">{{ row.section_1_name }}</span>
                      </template>
                    </td>

                    <!-- 💰 单价 (元/米) -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-slate">
                      <template v-if="typeof row.unit_price === 'number'">
                        <span class="price-val-text">¥{{ formatAmount(row.unit_price) }}</span>
                        <small v-if="row.is_avg_price" class="text-muted text-xs ml-0.5">(均)</small>
                        <!-- 💡 兜底/工程容差匹配备注角标 -->
                        <span 
                          v-if="row.has_tolerance_price && row.price_note" 
                          class="price-note-icon" 
                          :title="`💡 单价匹配说明：\n${row.price_note}`"
                        >
                          ℹ️
                        </span>
                      </template>
                      <template v-else-if="row.unit_price === 'multiple'">
                        <span class="text-muted text-xs">多项单价</span>
                      </template>
                      <template v-else>
                        <span class="text-muted">—</span>
                      </template>
                    </td>

                    <!-- 发货量 -->
                    <td class="text-right font-medium text-sky">{{ subMaterialType === 'pipe' ? formatQty(row.shipped_qty) : row.shipped_qty }}</td>
                    <!-- 💰 发货金额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-sky">
                      ¥{{ formatAmount(row.shipped_amount) }}
                    </td>

                    <!-- 确认到货 -->
                    <td class="text-right font-bold text-blue">{{ subMaterialType === 'pipe' ? formatQty(row.arrived_qty) : row.arrived_qty }}</td>
                    <!-- 💰 到货金额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-blue">
                      ¥{{ formatAmount(row.arrived_amount) }}
                    </td>

                    <!-- 施工接收 -->
                    <td class="text-right font-medium text-indigo">{{ subMaterialType === 'pipe' ? formatQty(row.received_qty) : row.received_qty }}</td>
                    <!-- 💰 接收金额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-indigo">
                      ¥{{ formatAmount(row.received_amount) }}
                    </td>

                    <!-- 库管确认 -->
                    <td class="text-right font-bold text-amber">{{ subMaterialType === 'pipe' ? formatQty(row.warehouse_qty) : row.warehouse_qty }}</td>
                    <!-- 💰 入库金额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-amber">
                      ¥{{ formatAmount(row.warehouse_amount) }}
                    </td>

                    <td class="text-center font-mono text-muted">{{ row.avg_transit_display }}</td>
                    <td class="text-right font-mono text-slate">{{ row.orders_count }} 单</td>

                    <!-- 履约进度条 -->
                    <td class="text-left">
                      <div class="progress-wrap">
                        <div class="progress-bar-bg">
                          <div class="progress-bar-fill fill-blue" :style="{ width: `${Math.min(100, row.fulfillment_rate)}%` }"></div>
                        </div>
                        <span class="progress-text">{{ row.fulfillment_rate }}%</span>
                      </div>
                    </td>

                    <!-- 接收确认率 -->
                    <td class="text-right font-mono font-bold text-indigo">{{ row.receipt_rate }}%</td>

                    <!-- 库管确认率 -->
                    <td class="text-right font-mono font-bold text-amber">{{ row.warehouse_rate }}%</td>

                    <!-- 穿透操作 -->
                    <td class="text-center" @click.stop>
                      <button 
                        type="button" 
                        class="btn-order-drill"
                        @click="openSupplierOrderModal(row)"
                      >
                        🔍 查看 ({{ row.orders_count }})
                      </button>
                    </td>
                  </tr>

                  <!-- 汇总底栏 (与 Tab 1/2 完全统一) -->
                  <tr class="summary-footer-row">
                    <td :colspan="supplierLedgerDimensions.length" class="text-left">
                      🏭 全项目供给方发货流转汇总 (已聚合为 {{ aggregatedSupplierLedgerRows.length }} 组)
                    </td>
                    <!-- 💰 全项目加权平均单价 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-slate">
                      ¥{{ (supplierLedgerSummary.total_shipped_qty > 0 ? formatAmount(supplierLedgerSummary.total_shipped_amount / supplierLedgerSummary.total_shipped_qty) : '0.00') }} <small class="text-muted text-xs">(均)</small>
                    </td>

                    <td class="text-right font-bold text-sky">{{ subMaterialType === 'pipe' ? formatQty(supplierLedgerSummary.total_shipped_qty) : supplierLedgerSummary.total_shipped_qty }}</td>
                    <!-- 💰 发货总额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-sky">
                      ¥{{ formatAmount(supplierLedgerSummary.total_shipped_amount) }}
                    </td>

                    <td class="text-right font-bold text-blue">{{ subMaterialType === 'pipe' ? formatQty(supplierLedgerSummary.total_arrived_qty) : supplierLedgerSummary.total_arrived_qty }}</td>
                    <!-- 💰 到货总额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-blue">
                      ¥{{ formatAmount(supplierLedgerSummary.total_arrived_amount) }}
                    </td>

                    <td class="text-right font-bold text-indigo">{{ subMaterialType === 'pipe' ? formatQty(supplierLedgerSummary.total_received_qty) : supplierLedgerSummary.total_received_qty }}</td>
                    <!-- 💰 接收总额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-indigo">
                      ¥{{ formatAmount(supplierLedgerSummary.total_received_amount) }}
                    </td>

                    <td class="text-right font-bold text-amber">{{ subMaterialType === 'pipe' ? formatQty(supplierLedgerSummary.total_warehouse_qty) : supplierLedgerSummary.total_warehouse_qty }}</td>
                    <!-- 💰 入库总额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-amber">
                      ¥{{ formatAmount(supplierLedgerSummary.total_warehouse_amount) }}
                    </td>

                    <td class="text-center font-mono">{{ supplierLedgerSummary.overall_avg_transit }}</td>
                    <td class="text-right font-mono text-slate">{{ supplierLedgerSummary.total_orders_count }} 单</td>
                    <td class="text-left">
                      <div class="progress-wrap">
                        <div class="progress-bar-bg">
                          <div class="progress-bar-fill fill-blue" :style="{ width: `${Math.min(100, supplierLedgerSummary.overall_fulfillment_rate)}%` }"></div>
                        </div>
                        <span class="progress-text">{{ supplierLedgerSummary.overall_fulfillment_rate }}%</span>
                      </div>
                    </td>
                    <td class="text-right font-mono font-bold text-indigo">{{ supplierLedgerSummary.overall_receipt_rate }}%</td>
                    <td class="text-right font-mono font-bold text-amber">{{ supplierLedgerSummary.overall_warehouse_rate }}%</td>
                    <td class="text-center text-muted">—</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- ==================================================================== -->
        <!-- 🏢 Tab 4: 责任主体与人员管辖速查矩阵 (可折叠分组架构 + 按标段视图) -->
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
                日期：{{ pipeDetailModalData.biz_date }} | 供给方：{{ pipeDetailModalData.supplier_name }} | 标段：{{ pipeDetailModalData.section_1_name }} | 型号：{{ pipeDetailModalData.pipe_model_name }}
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

    <!-- 供给方真实发货单穿透明细弹窗 -->
    <Transition name="fade">
      <div v-if="supplierOrderModalVisible && selectedSupplierOrderRow" class="block-modal-overlay" @click.self="supplierOrderModalVisible = false">
        <div class="block-modal-container modal-xl">
          <div class="block-modal-header bg-sky">
            <span class="modal-header-icon">📦</span>
            <div class="modal-header-title-wrap">
              <h3 class="modal-title">供给方发运订单穿透明细</h3>
              <p class="modal-sub">
                供给方：<strong>{{ selectedSupplierOrderRow?.supplier_name }}</strong>
                <span v-if="selectedSupplierOrderRow?.pipe_model_name" class="ml-2">| 型号：<strong>{{ selectedSupplierOrderRow?.pipe_model_name }}</strong></span>
                <span v-if="selectedSupplierOrderRow?.fitting_type" class="ml-2">| 品类：<strong>{{ selectedSupplierOrderRow?.fitting_type }} {{ selectedSupplierOrderRow?.model_spec }}</strong></span>
                <span v-if="selectedSupplierOrderRow?.section_1_name" class="ml-2">| 标段：<strong>{{ selectedSupplierOrderRow?.section_1_name }}</strong></span>
                <span v-if="selectedSupplierOrderRow?.biz_date" class="ml-2">| 日期：<strong class="font-mono">{{ selectedSupplierOrderRow?.biz_date }}</strong></span>
              </p>
            </div>
            <button type="button" class="btn-modal-close-icon" @click="supplierOrderModalVisible = false" title="关闭窗口">✕</button>
          </div>

          <!-- 弹窗内部小 KPI 概览条 -->
          <div class="modal-summary-banner">
            <div class="modal-sum-item">
              <span class="sum-lbl">发货总量</span>
              <span class="sum-val text-sky">{{ subMaterialType === 'pipe' ? formatQty(selectedSupplierOrderRow?.shipped_qty) : selectedSupplierOrderRow?.shipped_qty }} <small>{{ subMaterialType === 'pipe' ? '米' : '件' }}</small></span>
            </div>
            <div class="modal-sum-item">
              <span class="sum-lbl">确认到货</span>
              <span class="sum-val text-blue">{{ subMaterialType === 'pipe' ? formatQty(selectedSupplierOrderRow?.arrived_qty) : selectedSupplierOrderRow?.arrived_qty }} <small>{{ subMaterialType === 'pipe' ? '米' : '件' }}</small></span>
            </div>
            <div class="modal-sum-item">
              <span class="sum-lbl">施工接收</span>
              <span class="sum-val text-indigo">{{ subMaterialType === 'pipe' ? formatQty(selectedSupplierOrderRow?.received_qty) : selectedSupplierOrderRow?.received_qty }} <small>{{ subMaterialType === 'pipe' ? '米' : '件' }}</small></span>
            </div>
            <div class="modal-sum-item">
              <span class="sum-lbl">库管入库</span>
              <span class="sum-val text-amber">{{ subMaterialType === 'pipe' ? formatQty(selectedSupplierOrderRow?.warehouse_qty) : selectedSupplierOrderRow?.warehouse_qty }} <small>{{ subMaterialType === 'pipe' ? '米' : '件' }}</small></span>
            </div>
            <div class="modal-sum-item">
              <span class="sum-lbl">接收确认率</span>
              <span class="sum-val text-indigo font-mono">{{ selectedSupplierOrderRow?.receipt_rate }}%</span>
            </div>
            <div class="modal-sum-item">
              <span class="sum-lbl">库管确认率</span>
              <span class="sum-val text-amber font-mono">{{ selectedSupplierOrderRow?.warehouse_rate }}%</span>
            </div>
            <div class="modal-sum-item">
              <span class="sum-lbl">发运单数</span>
              <span class="sum-val text-slate">{{ selectedSupplierOrderRow?.orders_count }} <small>单</small></span>
            </div>
            <div class="modal-sum-item">
              <span class="sum-lbl">平均在途</span>
              <span class="sum-val text-slate font-mono">{{ selectedSupplierOrderRow?.avg_transit_display }}</span>
            </div>
          </div>

          <div class="modal-body modal-scroll-body">
            <div class="table-container modal-table-container">
              <table class="data-table modal-data-table">
                <thead>
                  <tr>
                    <th class="text-left">运单号/批次</th>
                    <th class="text-left">需求标段</th>
                    <th class="text-left">规格型号</th>
                    <th v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right">单价 (元/米)</th>
                    <th class="text-center">发货日期</th>
                    <th class="text-left">车辆 / 司机 / 电话</th>
                    <th class="text-right">发货量 ({{ subMaterialType === 'pipe' ? '米' : '件' }})</th>
                    <th v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right text-sky font-bold">发货金额 (元)</th>
                    <th class="text-right">确认到货 ({{ subMaterialType === 'pipe' ? '米' : '件' }})</th>
                    <th v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right text-blue font-bold">到货金额 (元)</th>
                    <th class="text-right">施工接收 ({{ subMaterialType === 'pipe' ? '米' : '件' }})</th>
                    <th class="text-right">库管确认 ({{ subMaterialType === 'pipe' ? '米' : '件' }})</th>
                    <th class="text-center">在途时长</th>
                    <th class="text-center">运单状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="order in selectedSupplierOrderRow?.order_items || []" :key="order.id">
                    <td class="text-left font-mono font-bold text-slate">{{ order.batch_no }}</td>
                    <td class="text-left"><span class="font-bold text-dark">{{ order.section_1_name }}</span></td>
                    <td class="text-left">
                      <template v-if="subMaterialType === 'pipe'">
                        <span class="badge model-badge">{{ order.pipe_model_name }}</span>
                      </template>
                      <template v-else>
                        <span class="font-bold text-slate">{{ order.fitting_type }}</span>
                        <span class="font-medium text-muted ml-1">{{ order.model_spec }}</span>
                      </template>
                    </td>
                    <!-- 💰 单价 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-slate">
                      <template v-if="order.unit_price != null">
                        <span>¥{{ formatAmount(order.unit_price) }}</span>
                        <!-- 💡 兜底/工程容差匹配备注角标 -->
                        <span 
                          v-if="!order.is_exact_price && order.price_note" 
                          class="price-note-icon" 
                          :title="`💡 单价匹配说明：\n${order.price_note}`"
                        >
                          ℹ️
                        </span>
                      </template>
                      <template v-else>
                        <span class="text-muted">—</span>
                      </template>
                    </td>
                    <td class="text-center font-mono text-xs">{{ order.biz_date }}</td>
                    <td class="text-left text-xs">
                      <div class="font-bold text-slate-700">{{ order.vehicle_no || '—' }}</div>
                      <div class="text-slate-500 font-mono">{{ order.driver_name }} {{ order.driver_phone }}</div>
                    </td>
                    <td class="text-right font-medium text-sky">{{ subMaterialType === 'pipe' ? formatQty(order.shipped_qty) : order.shipped_qty }}</td>
                    <!-- 💰 发货总额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-sky">
                      ¥{{ formatAmount(order.shipped_amount) }}
                    </td>
                    <td class="text-right font-bold text-blue">{{ subMaterialType === 'pipe' ? formatQty(order.arrived_qty) : order.arrived_qty }}</td>
                    <!-- 💰 到货总额 -->
                    <td v-if="subMaterialType === 'pipe' && showPipeAmountCalc" class="text-right font-mono font-bold text-blue">
                      ¥{{ formatAmount(order.arrived_amount) }}
                    </td>
                    <td class="text-right font-medium text-indigo">{{ subMaterialType === 'pipe' ? formatQty(order.received_qty) : order.received_qty }}</td>
                    <td class="text-right font-bold text-amber">{{ subMaterialType === 'pipe' ? formatQty(order.warehouse_qty) : order.warehouse_qty }}</td>
                    <td class="text-center font-mono text-muted text-xs">{{ order.transit_display }}</td>
                    <td class="text-center">
                      <span :class="['badge-status-pill', `status-${order.status}`]">
                        {{ order.status === 'completed' ? '已入库' : order.status === 'received' ? '已接收' : order.status === 'arrived' ? '已到货' : '在途中' }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="block-modal-actions flex justify-between items-center">
            <span class="text-xs text-muted font-mono">共穿透 {{ selectedSupplierOrderRow?.order_items?.length || 0 }} 笔真实发货运单记录</span>
            <div class="flex gap-2">
              <button v-if="canExtractXlsx" type="button" class="btn btn-export btn-sm" @click="exportCurrentOrderItemsExcel">
                📥 导出此运单明细
              </button>
              <button type="button" class="btn secondary" @click="supplierOrderModalVisible = false">关闭窗口</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 🔐 弹窗：采购价格访问安全授权验证 Modal -->
    <Transition name="fade">
      <div v-if="priceAuthModalVisible" class="block-modal-overlay" @click.self="closePriceAuthModal">
        <div class="block-modal-container price-auth-modal" role="dialog" aria-modal="true">
          <!-- 头部 Header -->
          <div class="block-modal-header price-auth-header">
            <div class="price-auth-header-icon-wrap">
              <span class="price-auth-icon">🔐</span>
            </div>
            <div class="modal-header-title-wrap">
              <h3 class="modal-title">
                {{ pendingAuthTarget === 'pipe_calc' ? '保温管总价核算安全验证' : '采购价格安全访问验证' }}
              </h3>
              <p class="modal-sub">
                {{ pendingAuthTarget === 'pipe_calc' ? '敏感核算数据受限，需验证访问权限' : '敏感价格字典受限，需验证访问权限' }}
              </p>
            </div>
            <button type="button" class="btn-modal-close-icon" @click="closePriceAuthModal" title="关闭窗口">✕</button>
          </div>

          <!-- 表单 Body -->
          <form class="auth-modal-form" @submit.prevent="handleVerifyPriceCode">
            <div class="auth-modal-body">
              <!-- 安全说明卡片 -->
              <div class="auth-notice-card">
                <span class="notice-icon">🛡️</span>
                <div class="notice-content">
                  <strong>安全保护提示</strong>
                  <p>{{ pendingAuthTarget === 'pipe_calc' ? '联动单价字典计算发运与到货总价属于敏感数据，请输入 4 位授权访问码解锁。' : '查看保温管及管件采购基准价格属于敏感物资数据，请输入 4 位授权访问码解锁。' }}</p>
                </div>
              </div>

              <!-- 密码输入区域 -->
              <div class="auth-field-group">
                <label class="auth-input-label" for="price-auth-input">
                  <span>请输入 4 位数字访问码</span>
                </label>
                <div class="auth-input-wrapper">
                  <span class="auth-input-icon">🔑</span>
                  <input
                    id="price-auth-input"
                    ref="priceInputRef"
                    v-model="priceAccessCodeInput"
                    type="password"
                    maxlength="10"
                    class="auth-input-field font-mono"
                    placeholder="••••"
                    autocomplete="off"
                    @input="priceAccessErrorMsg = ''"
                    @keydown.enter.prevent="handleVerifyPriceCode"
                  />
                </div>
              </div>

              <!-- 错误提示 -->
              <Transition name="fade">
                <div v-if="priceAccessErrorMsg" class="auth-error-tip">
                  <span class="error-icon">⚠️</span>
                  <span>{{ priceAccessErrorMsg }}</span>
                </div>
              </Transition>
            </div>

            <!-- 底部操作栏 -->
            <div class="block-modal-actions auth-modal-actions">
              <button type="button" class="btn secondary modal-cancel-btn" @click="closePriceAuthModal">取消</button>
              <button
                type="submit"
                class="btn btn-unlock-confirm"
                :disabled="!priceAccessCodeInput.trim()"
              >
                <span>🔓 验证并进入</span>
              </button>
            </div>
          </form>
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
import { useAuthStore } from '@/projects/daily_report_25_26/store/auth'
import {
  fetchTubeConfig,
  getComprehensiveDailyFlow,
  getComprehensiveBaselineProgress,
  getComprehensiveSupplierLedger,
  getComprehensiveEntityDirectory,
  getTubeMaterialPrices,
} from '@/projects/daily_report_25_26/services/api'

const router = useRouter()
const auth = useAuthStore()
const projectKey = 'insulation_pipe_supply_2026'
const canExtractXlsx = computed(() => auth.canExtractXlsxFor(projectKey))

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
const activeTab = ref('daily_flow') // 'daily_flow' | 'baseline_progress' | 'supplier_ledger' | 'directory'
const subMaterialType = ref('pipe') // 'pipe' | 'fitting'
const fittingTab2SubView = ref('baseline') // 'baseline' (设计采购基准表) | 'flow' (全周期累计流转与现场库存表)
const directoryCategory = ref('all') // 'all' | 'suppliers' | 'site_managers' | 'demand_sections' | 'warehouse_keepers' | 'global_members'

// 责任主体专属视图切换模式 ('by_category': 按主体类别 | 'by_section': 按标段综合穿透)
const directoryViewMode = ref('by_category')

// -----------------------------------------------------------------------------
// 🔐 采购价格安全访问验证状态 (访问码 0411)
// -----------------------------------------------------------------------------
const PRICE_ACCESS_CODE = '0411'
const isPriceUnlocked = ref(sessionStorage.getItem('phoenix_price_unlocked') === '1')
const priceAuthModalVisible = ref(false)
const priceAccessCodeInput = ref('')
const priceAccessErrorMsg = ref('')
const priceInputRef = ref(null)
const pendingAuthTarget = ref('price_tab') // 'price_tab' (采购价格表) | 'pipe_calc' (保温管总价核算选框)

function openPriceAuthModal(target = 'price_tab') {
  pendingAuthTarget.value = target
  priceAccessCodeInput.value = ''
  priceAccessErrorMsg.value = ''
  priceAuthModalVisible.value = true
  setTimeout(() => {
    if (priceInputRef.value) {
      priceInputRef.value.focus()
    }
  }, 100)
}

function closePriceAuthModal() {
  priceAuthModalVisible.value = false
  priceAccessCodeInput.value = ''
  priceAccessErrorMsg.value = ''
}

async function handleVerifyPriceCode() {
  const code = (priceAccessCodeInput.value || '').trim()
  if (code === PRICE_ACCESS_CODE) {
    isPriceUnlocked.value = true
    sessionStorage.setItem('phoenix_price_unlocked', '1')
    priceAuthModalVisible.value = false
    priceAccessCodeInput.value = ''
    priceAccessErrorMsg.value = ''

    // 确保单价字典数据已加载
    if (materialPriceList.value.length === 0) {
      try {
        const res = await getTubeMaterialPrices(projectKey)
        if (res && res.data) {
          materialPriceList.value = res.data
        }
      } catch (err) {
        console.error('加载物料单价字典失败:', err)
      }
    }

    if (pendingAuthTarget.value === 'price_tab') {
      subMaterialType.value = 'price'
      fetchActiveTabData()
    } else if (pendingAuthTarget.value === 'pipe_calc') {
      showPipeAmountCalc.value = true
    }
  } else {
    priceAccessErrorMsg.value = '访问码错误，请重新输入'
    priceAccessCodeInput.value = ''
    if (priceInputRef.value) {
      priceInputRef.value.focus()
    }
  }
}

function lockPriceAccess() {
  isPriceUnlocked.value = false
  sessionStorage.removeItem('phoenix_price_unlocked')
  showPipeAmountCalc.value = false
  subMaterialType.value = 'pipe'
  fetchActiveTabData()
}

// -----------------------------------------------------------------------------
// 💰 供给方台账保温管金额联动核算状态 (Tab 3)
// -----------------------------------------------------------------------------
const showPipeAmountCalc = ref(false)

async function handlePipeCalcToggle(e) {
  const checked = e.target.checked
  if (checked) {
    if (!isPriceUnlocked.value) {
      e.target.checked = false
      openPriceAuthModal('pipe_calc')
      return
    }
    if (materialPriceList.value.length === 0) {
      try {
        const res = await getTubeMaterialPrices(projectKey)
        if (res && res.data) {
          materialPriceList.value = res.data
        }
      } catch (err) {
        console.error('加载物料单价字典失败:', err)
      }
    }
    showPipeAmountCalc.value = true
  } else {
    showPipeAmountCalc.value = false
  }
}

// 保温管规格工程解析器 (提取工作管与外护管参数及甲供属性)
function parsePipeSpec(str) {
  if (!str) return null
  const s = String(str).replace(/\s+/g, '')
  const isJiaGong = s.includes('甲供')

  // 双层格式：外径1*壁厚1 / 外径2*壁厚2 (例如 Φ89×4.0/Φ175×3.0 或 89*4/176*3)
  const doubleMatch = s.match(/(?:Φ|DN)?(\d+(?:\.\d+)?)[×*](\d+(?:\.\d+)?)\s*[\/]\s*(?:Φ|DN)?(\d+(?:\.\d+)?)[×*]?(\d+(?:\.\d+)?)?/i)
  if (doubleMatch) {
    return {
      d1: parseFloat(doubleMatch[1]),
      t1: doubleMatch[2] ? parseFloat(doubleMatch[2]) : null,
      d2: doubleMatch[3] ? parseFloat(doubleMatch[3]) : null,
      t2: doubleMatch[4] ? parseFloat(doubleMatch[4]) : null,
      isJiaGong
    }
  }

  // 单层带壁厚格式：例如 Φ89×4.0
  const singleMatch = s.match(/(?:Φ|DN)?(\d+(?:\.\d+)?)[×*](\d+(?:\.\d+)?)/i)
  if (singleMatch) {
    return {
      d1: parseFloat(singleMatch[1]),
      t1: parseFloat(singleMatch[2]),
      d2: null,
      t2: null,
      isJiaGong
    }
  }

  // DN 格式：例如 DN80
  const dnMatch = s.match(/DN\s*(\d+)/i)
  if (dnMatch) {
    const dnVal = parseInt(dnMatch[1], 10)
    return {
      dn: dnVal,
      d1: dnVal,
      t1: null,
      d2: null,
      t2: null,
      isJiaGong
    }
  }

  const numMatch = s.match(/\d+/)
  return {
    d1: numMatch ? parseFloat(numMatch[0]) : null,
    t1: null,
    d2: null,
    t2: null,
    isJiaGong
  }
}

// 结合供货厂家全称与保温管规格型号精准匹配基准单价及备注
function getPipeUnitPriceInfo(supplierName, pipeModelName) {
  const defRes = {
    unitPrice: null,
    matchedSpec: '',
    targetSpec: pipeModelName || '',
    matchType: null, // 'exact' | 'tolerance' | 'dn_fallback'
    matchNote: '',
    isExact: false
  }

  if (!materialPriceList.value || materialPriceList.value.length === 0) return defRes
  const supClean = (supplierName || '').trim()
  const modelClean = (pipeModelName || '').trim()
  if (!supClean || !modelClean) return defRes

  const pipePrices = materialPriceList.value.filter(p => p.material_kind === 'pipe')

  // 1. 优先供给方全称精确匹配或包含匹配
  const matchedSupPrices = pipePrices.filter(p => {
    const pSup = (p.supplier_name || '').trim()
    if (!pSup) return false
    return pSup === supClean || pSup.includes(supClean) || supClean.includes(pSup)
  })

  if (matchedSupPrices.length === 0) return defRes

  // 2. 匹配型号 (第 1 优先级：字符级完全精确匹配)
  const exactMatched = matchedSupPrices.find(p => 
    (p.model_spec && p.model_spec.replace(/\s+/g, '') === modelClean.replace(/\s+/g, '')) ||
    (p.raw_model_spec && p.raw_model_spec.replace(/\s+/g, '') === modelClean.replace(/\s+/g, ''))
  )
  if (exactMatched) {
    return {
      unitPrice: Number(exactMatched.unit_price) || 0,
      matchedSpec: exactMatched.model_spec || exactMatched.raw_model_spec || modelClean,
      targetSpec: modelClean,
      matchType: 'exact',
      matchNote: '', // 精确匹配无需特别备注
      isExact: true
    }
  }

  // 3. 结构化工程参数解析匹配 (第 2 优先级：工作管外径+壁厚一致，外护管允许工程级微差容差匹配)
  const targetParsed = parsePipeSpec(modelClean)
  if (targetParsed && targetParsed.d1 != null) {
    for (const p of matchedSupPrices) {
      const pParsed = parsePipeSpec(p.model_spec || p.raw_model_spec || '')
      if (!pParsed || pParsed.d1 == null) continue

      // 甲供状态必须一致 (避免把普通管匹配为甲供钢管)
      if (targetParsed.isJiaGong !== pParsed.isJiaGong) continue

      // 工作管外径必须一致
      if (targetParsed.d1 === pParsed.d1) {
        // 若双方均有工作管壁厚，壁厚必须相同
        if (targetParsed.t1 != null && pParsed.t1 != null && targetParsed.t1 !== pParsed.t1) {
          continue
        }

        // 外护管外径容差判断 (<= 3mm 视为工程模具微差容差)
        let isTolerance = false
        if (targetParsed.d2 != null && pParsed.d2 != null) {
          const diff = Math.abs(targetParsed.d2 - pParsed.d2)
          if (diff <= 3) {
            isTolerance = true
          }
        } else {
          isTolerance = true
        }

        if (isTolerance) {
          const matchedSpec = p.model_spec || p.raw_model_spec || ''
          return {
            unitPrice: Number(p.unit_price) || 0,
            matchedSpec,
            targetSpec: modelClean,
            matchType: 'tolerance',
            matchNote: `单据规格【${modelClean}】匹配基准报价【${matchedSpec}】（工作管Φ${targetParsed.d1}×${targetParsed.t1 || ''}参数一致，外护管工程容差匹配）`,
            isExact: false
          }
        }
      }
    }
  }

  // 4. 口径数值提取兜底匹配 (第 3 优先级：主工作管径/DN对齐)
  const getDnNum = (str) => {
    const m = str.match(/DN\s*(\d+)/i)
    if (m) return Number(m[1])
    const n = str.match(/\d+/)
    return n ? Number(n[0]) : null
  }
  const targetDn = getDnNum(modelClean)
  if (targetDn != null) {
    const dnMatched = matchedSupPrices.find(p => {
      const pParsed = parsePipeSpec(p.model_spec || p.raw_model_spec || '')
      if (pParsed && targetParsed && pParsed.isJiaGong !== targetParsed.isJiaGong) return false
      const pDn = getDnNum(p.model_spec || p.raw_model_spec || '')
      return pDn === targetDn
    })
    if (dnMatched) {
      const matchedSpec = dnMatched.model_spec || dnMatched.raw_model_spec || ''
      return {
        unitPrice: Number(dnMatched.unit_price) || 0,
        matchedSpec,
        targetSpec: modelClean,
        matchType: 'dn_fallback',
        matchNote: `单据规格【${modelClean}】匹配基准报价【${matchedSpec}】（按主工作管径/DN对齐兜底匹配）`,
        isExact: false
      }
    }
  }

  return defRes
}

// 保持兼容的单价数值获取方法
function getPipeUnitPrice(supplierName, pipeModelName) {
  const info = getPipeUnitPriceInfo(supplierName, pipeModelName)
  return info.unitPrice
}

function formatAmount(val) {
  if (val == null || isNaN(val)) return '0.00'
  return Number(val).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatAmountWan(val) {
  if (val == null || isNaN(val)) return '0.00'
  const wan = Number(val) / 10000
  return wan.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// -----------------------------------------------------------------------------
// 💰 物料采购价格字典状态 (Tab 2 采购价格子视图)
// -----------------------------------------------------------------------------
const materialPriceList = ref([])
const priceFilterKind = ref('all') // 'all' | 'pipe' | 'fitting'
const priceFilterSupplier = ref('all') // 'all' | 某供给方全称
const priceFilterCategory = ref('all') // 'all' | 某物理品类
const priceFilterKeyword = ref('') // 规格型号/材料搜索

function resetPriceFilters() {
  priceFilterKind.value = 'all'
  priceFilterSupplier.value = 'all'
  priceFilterCategory.value = 'all'
  priceFilterKeyword.value = ''
  if (tableSortStates.value.price_table) {
    tableSortStates.value.price_table = { key: 'material_kind', order: 'desc' }
  }
}

// 分组折叠状态 (默认全部展开)
const groupCollapseState = reactive({
  suppliers: false,
  demand_sections: false,
  site_managers: false,
  warehouse_keepers: false,
  global_members: false,
})

function toggleGroupCollapse(grp) {
  groupCollapseState[grp] = !groupCollapseState[grp]
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
  date: { id: 'date', label: '📅 时间日期', shortLabel: '日期', colHeader: '时间日期', icon: '📅' },
  section: { id: 'section', label: '🏗️ 需求标段', shortLabel: '标段', colHeader: '需求标段', icon: '🏗️' },
  supplier: { id: 'supplier', label: '🏭 供给方', shortLabel: '供给方', colHeader: '供给方', icon: '🏭' },
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
]

// Tab 2 (设计采购基准进度) 当前激活维度层级 (默认: 标段 ➔ 型号)
const baselineDimensions = ref(['section', 'model'])

// Tab 2 快捷透视预设方案
const baselineDimensionPresets = [
  { label: '⚡ 默认 (标段➔型号)', dims: ['section', 'model'] },
  { label: '🌟 全网型号总览 (标段合计)', dims: ['model'] },
  { label: '📐 型号➔标段对比', dims: ['model', 'section'] },
  { label: '🏗️ 纯标段合计', dims: ['section'] },
]

// Tab 3 (供给方发货流转台账) 当前激活维度层级 (默认: 供给方 ➔ 型号)
const supplierLedgerDimensions = ref(['supplier', 'model'])

// Tab 3 快捷透视预设方案
const supplierLedgerDimensionPresets = [
  { label: '🏭 供给方➔型号 (默认汇总)', dims: ['supplier', 'model'] },
  { label: '🏭 供给方➔日期➔型号', dims: ['supplier', 'date', 'model'] },
  { label: '🏭 供给方➔标段➔型号', dims: ['supplier', 'section', 'model'] },
  { label: '🏭 供给方汇总', dims: ['supplier'] },
  { label: '📅 日期➔供给方➔型号', dims: ['date', 'supplier', 'model'] },
  { label: '🏗️ 标段➔供给方➔型号', dims: ['section', 'supplier', 'model'] },
  { label: '📐 纯型号汇总', dims: ['model'] },
]

function getTargetDimensionRef(tab) {
  if (tab === 'daily') return dailyDimensions
  if (tab === 'supplier_ledger') return supplierLedgerDimensions
  return baselineDimensions
}

function isCurrentPreset(tab, dims) {
  const current = getTargetDimensionRef(tab).value
  return current.join(',') === dims.join(',')
}

function applyDimensionPreset(tab, dims) {
  getTargetDimensionRef(tab).value = [...dims]
}

// 🎛️ 多维透视聚合控制器状态 (下拉列表选择模式)
const activePivotDropdown = ref(null) // 'daily' | 'baseline' | 'supplier_ledger' | null

function togglePivotDropdown(tab) {
  activePivotDropdown.value = activePivotDropdown.value === tab ? null : tab
}

function closePivotDropdown() {
  activePivotDropdown.value = null
}

// 获取当前维度链条精简展示文字 (例如 "1.供给方 ➔ 2.型号")
function getDimensionChainText(tab) {
  const current = getTargetDimensionRef(tab).value
  if (!current || current.length === 0) return '未选维度 (全量汇总)'
  return current.map((id, idx) => `${idx + 1}.${getDimensionDef(id).shortLabel}`).join(' ➔ ')
}

// 获取可用维度定义列表
function getAvailableDimensions(tab) {
  if (tab === 'daily') {
    return ['model', 'date', 'section'].map(id => getDimensionDef(id))
  }
  if (tab === 'supplier_ledger') {
    return ['supplier', 'model', 'date', 'section'].map(id => getDimensionDef(id))
  }
  return ['model', 'section'].map(id => getDimensionDef(id))
}

function isDimensionSelected(tab, dimId) {
  const list = getTargetDimensionRef(tab).value
  return list.includes(dimId)
}

function getDimensionOrder(tab, dimId) {
  const list = getTargetDimensionRef(tab).value
  const idx = list.indexOf(dimId)
  return idx !== -1 ? idx + 1 : null
}

// 有序切换勾选：未勾选时按点击先后顺序追加到末尾；已勾选时取消勾选
function toggleDimensionSelection(tab, dimId) {
  const listRef = getTargetDimensionRef(tab)
  const list = listRef.value
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
  const list = getTargetDimensionRef(tab).value
  const idx = list.indexOf(dimId)
  if (idx > 0) {
    const item = list.splice(idx, 1)[0]
    list.splice(idx - 1, 0, item)
  }
}

function moveDimensionDown(tab, dimId) {
  const list = getTargetDimensionRef(tab).value
  const idx = list.indexOf(dimId)
  if (idx !== -1 && idx < list.length - 1) {
    const item = list.splice(idx, 1)[0]
    list.splice(idx + 1, 0, item)
  }
}

function resetToDefaultDimensions(tab) {
  if (tab === 'daily') {
    dailyDimensions.value = ['date', 'section', 'model']
  } else if (tab === 'supplier_ledger') {
    supplierLedgerDimensions.value = ['supplier', 'model']
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
const supplierLedgerData = ref({ items: [], summary: {} })
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

const supplierOrderModalVisible = ref(false)
const selectedSupplierOrderRow = ref(null)

function openSupplierOrderModal(row) {
  selectedSupplierOrderRow.value = row
  supplierOrderModalVisible.value = true
}

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

function getSupplierNameBySection(secId) {
  if (!secId) return '—'
  const cfg = configSummary.value
  if (!cfg) return '—'
  const supplyEntities = cfg.supply_entities || cfg.suppliers || []

  for (const sup of supplyEntities) {
    const secIds = sup.section_1_ids || []
    if (secIds.includes(secId)) {
      return sup.entity_name || sup.supplier_name || sup.name || sup.entity_id || '—'
    }
  }
  return '—'
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
        (r.supplier_name && r.supplier_name.toLowerCase().includes(kw)) ||
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
        const val = row.supplier_name || row.supplier_entity_name || getSupplierNameBySection(row.section_1_id) || '—'
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

  // 多维逐级排序：规格型号按大口径到小口径降序
  result.sort((a, b) => {
    for (const dim of activeDims) {
      if (dim === 'date') {
        const valA = a.biz_date || ''
        const valB = b.biz_date || ''
        if (valA !== valB) return valB.localeCompare(valA, 'zh-CN', { numeric: true }) // 日期默认最新在前
      } else if (dim === 'supplier') {
        const valA = a.supplier_name || ''
        const valB = b.supplier_name || ''
        if (valA !== valB) return valA.localeCompare(valB, 'zh-CN', { numeric: true })
      } else if (dim === 'section') {
        const valA = a.section_1_name || ''
        const valB = b.section_1_name || ''
        if (valA !== valB) return valA.localeCompare(valB, 'zh-CN', { numeric: true })
      } else if (dim === 'model') { 
        const valA = subMaterialType.value === 'pipe' ? (a.pipe_model_name || '') : (`${a.fitting_type || ''} ${a.model_spec || ''}`).trim();
        const valB = subMaterialType.value === 'pipe' ? (b.pipe_model_name || '') : (`${b.fitting_type || ''} ${b.model_spec || ''}`).trim();
        if (valA !== valB) {
          const comp = compareModelSpecs(valA, valB, 'desc')
          if (comp !== 0) return comp
        }
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

// -----------------------------------------------------------------------------
// Tab 2: 设计采购基准与进度对照数据计算 (含管件)
// -----------------------------------------------------------------------------

const filteredBaselineRows = computed(() => {
  let list = baselineProgressData.value.items || []
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(r => selectedSectionIds.value.includes(r.section_1_id))
  }
  if (subMaterialType.value === 'pipe' && selectedPipeModelIds.value.length > 0) {
    list = list.filter(r => selectedPipeModelIds.value.includes(r.pipe_model_id))
  }
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(r => 
      (r.section_1_name && r.section_1_name.toLowerCase().includes(kw)) ||
      (r.pipe_model_name && r.pipe_model_name.toLowerCase().includes(kw)) ||
      (r.supplier_name && r.supplier_name.toLowerCase().includes(kw))
    )
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
      (r.supplier_name && r.supplier_name.toLowerCase().includes(kw)) ||
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
        const val = row.supplier_name || getSupplierNameBySection(row.section_1_id) || '—'
        keyParts.push(val)
        dimValues.supplier_name = val
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
    const modelA = `${a.fitting_type || ''} ${a.model_spec || ''}`.trim()
    const modelB = `${b.fitting_type || ''} ${b.model_spec || ''}`.trim()
    return compareModelSpecs(modelA, modelB, 'desc')
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
        const val = row.supplier_name || getSupplierNameBySection(row.section_1_id) || '—'
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
    const modelA = `${a.fitting_type || ''} ${a.model_spec || ''}`.trim()
    const modelB = `${b.fitting_type || ''} ${b.model_spec || ''}`.trim()
    return compareModelSpecs(modelA, modelB, 'desc')
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
        const val = row.supplier_name || getSupplierNameBySection(row.section_1_id) || '—'
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
      if (dim === 'supplier') {
        const valA = a.supplier_name || ''
        const valB = b.supplier_name || ''
        if (valA !== valB) return valA.localeCompare(valB, 'zh-CN', { numeric: true })
      } else if (dim === 'section') {
        const valA = a.section_1_name || ''
        const valB = b.section_1_name || ''
        if (valA !== valB) return valA.localeCompare(valB, 'zh-CN', { numeric: true })
      } else if (dim === 'model') {
        const valA = a.pipe_model_name || ''
        const valB = b.pipe_model_name || ''
        if (valA !== valB) {
          const comp = compareModelSpecs(valA, valB, 'desc')
          if (comp !== 0) return comp
        }
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
  fitting_flow: { key: '', order: '' },
  price_table: { key: 'material_kind', order: 'desc' },
  supplier_ledger: { key: '', order: '' }
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

// 规格型号数值智能比较 (默认降序: DN1400 > DN1200 > DN1000 > ... > DN80)
function compareModelSpecs(strA, strB, order = 'desc') {
  const sA = (strA || '').trim()
  const sB = (strB || '').trim()
  if (!sA && !sB) return 0
  if (!sA) return order === 'desc' ? 1 : -1
  if (!sB) return order === 'desc' ? -1 : 1

  // 提取数字序列，例如 "DN1400/1600" -> [1400, 1600], "DN300 90°弯头" -> [300, 90]
  const numsA = sA.match(/\d+/g)?.map(Number) || []
  const numsB = sB.match(/\d+/g)?.map(Number) || []

  // 逐个数字比较
  const minLen = Math.min(numsA.length, numsB.length)
  for (let i = 0; i < minLen; i++) {
    if (numsA[i] !== numsB[i]) {
      return order === 'desc' ? (numsB[i] - numsA[i]) : (numsA[i] - numsB[i])
    }
  }

  if (numsA.length !== numsB.length) {
    return order === 'desc' ? (numsB.length - numsA.length) : (numsA.length - numsB.length)
  }

  // 数字完全相同或无数字时按字符串比较
  const strComp = sA.localeCompare(sB, 'zh-CN', { numeric: true, sensitivity: 'base' })
  return order === 'desc' ? -strComp : strComp
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

    if (key === 'model') {
      return compareModelSpecs(String(valA), String(valB), order)
    }

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
// 💰 物料采购价格字典计算属性与 KPI (Tab 2 采购价格专属)
// -----------------------------------------------------------------------------

// 供给方下拉选项列表
const priceSupplierOptions = computed(() => {
  const sups = new Set()
  materialPriceList.value.forEach(p => {
    if (p.supplier_name) sups.add(p.supplier_name)
  })
  return Array.from(sups).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

// 物理类别下拉选项列表（联动大类）
const priceCategoryOptions = computed(() => {
  const cats = new Set()
  materialPriceList.value.forEach(p => {
    if (priceFilterKind.value !== 'all' && p.material_kind !== priceFilterKind.value) return
    if (p.category) cats.add(p.category)
  })
  return Array.from(cats).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

// 筛选后的单价行数据
const filteredMaterialPriceRows = computed(() => {
  let list = materialPriceList.value || []
  if (priceFilterKind.value !== 'all') {
    list = list.filter(p => p.material_kind === priceFilterKind.value)
  }
  if (priceFilterSupplier.value !== 'all') {
    list = list.filter(p => p.supplier_name === priceFilterSupplier.value)
  }
  if (priceFilterCategory.value !== 'all') {
    list = list.filter(p => p.category === priceFilterCategory.value)
  }
  if (priceFilterKeyword.value.trim()) {
    const kw = priceFilterKeyword.value.trim().toLowerCase()
    list = list.filter(p => 
      (p.model_spec && p.model_spec.toLowerCase().includes(kw)) ||
      (p.material_name && p.material_name.toLowerCase().includes(kw)) ||
      (p.raw_model_spec && p.raw_model_spec.toLowerCase().includes(kw)) ||
      (p.remark && p.remark.toLowerCase().includes(kw))
    )
  }
  return list
})

// 排序后的单价行数据 (默认大类降序: 保温管在前、管件在后，同大类内按供给方与规格型号口径降序排列)
const sortedMaterialPriceRows = computed(() => {
  const current = tableSortStates.value.price_table
  const list = filteredMaterialPriceRows.value || []
  if (!current || !current.key || !current.order) {
    // 默认大类降序
    const copy = [...list]
    copy.sort((a, b) => {
      if (a.material_kind !== b.material_kind) {
        return (b.material_kind || '').localeCompare(a.material_kind || '')
      }
      if (a.supplier_name !== b.supplier_name) {
        return (a.supplier_name || '').localeCompare(b.supplier_name || '', 'zh-CN')
      }
      return compareModelSpecs(a.model_spec || '', b.model_spec || '', 'desc')
    })
    return copy
  }

  // 若用户显式点击大类排序
  if (current.key === 'material_kind') {
    const isDesc = current.order === 'desc'
    const copy = [...list]
    copy.sort((a, b) => {
      if (a.material_kind !== b.material_kind) {
        return isDesc 
          ? (b.material_kind || '').localeCompare(a.material_kind || '') 
          : (a.material_kind || '').localeCompare(b.material_kind || '')
      }
      if (a.supplier_name !== b.supplier_name) {
        return (a.supplier_name || '').localeCompare(b.supplier_name || '', 'zh-CN')
      }
      return compareModelSpecs(a.model_spec || '', b.model_spec || '', 'desc')
    })
    return copy
  }

  return sortRows(list, 'price_table', {
    material_kind: r => r.material_kind || '',
    supplier_name: r => r.supplier_name || '',
    category: r => r.category || '',
    material_name: r => r.material_name || '',
    model_spec: r => r.model_spec || '',
    unit: r => r.unit || '',
    unit_price: r => Number(r.unit_price) || 0
  })
})

// 采购价格看板卡片指标
const priceSuppliersCount = computed(() => {
  const s = new Set()
  materialPriceList.value.forEach(p => { if (p.supplier_name) s.add(p.supplier_name) })
  return s.size
})

const pricePipeCount = computed(() => {
  return materialPriceList.value.filter(p => p.material_kind === 'pipe').length
})

const priceFittingCount = computed(() => {
  return materialPriceList.value.filter(p => p.material_kind === 'fitting').length
})

const priceCategoriesCount = computed(() => {
  const c = new Set()
  materialPriceList.value.forEach(p => { if (p.category) c.add(p.category) })
  return c.size
})

const priceAverageDisplay = computed(() => {
  const list = filteredMaterialPriceRows.value.length > 0 ? filteredMaterialPriceRows.value : materialPriceList.value
  if (!list || list.length === 0) return '0.00'
  const sum = list.reduce((acc, cur) => acc + (Number(cur.unit_price) || 0), 0)
  return (sum / list.length).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const priceFilteredSuppliersCount = computed(() => {
  const s = new Set()
  filteredMaterialPriceRows.value.forEach(p => { if (p.supplier_name) s.add(p.supplier_name) })
  return s.size
})

const priceFilteredAvgDisplay = computed(() => {
  const list = filteredMaterialPriceRows.value
  if (!list || list.length === 0) return '0.00'
  const sum = list.reduce((acc, cur) => acc + (Number(cur.unit_price) || 0), 0)
  return (sum / list.length).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const priceFilteredMinDisplay = computed(() => {
  const list = filteredMaterialPriceRows.value
  if (!list || list.length === 0) return '0.00'
  const min = Math.min(...list.map(p => Number(p.unit_price) || 0))
  return min.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

const priceFilteredMaxDisplay = computed(() => {
  const list = filteredMaterialPriceRows.value
  if (!list || list.length === 0) return '0.00'
  const max = Math.max(...list.map(p => Number(p.unit_price) || 0))
  return max.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

// -----------------------------------------------------------------------------
// 🏭 供给方发货流转台账 (Tab 3: 供给方视角动态透视与指标聚合)
// -----------------------------------------------------------------------------

const filteredSupplierLedgerRows = computed(() => {
  let list = supplierLedgerData.value.items || []
  if (selectedSectionIds.value.length > 0) {
    list = list.filter(r => selectedSectionIds.value.includes(r.section_1_id))
  }
  if (subMaterialType.value === 'pipe' && selectedPipeModelIds.value.length > 0) {
    list = list.filter(r => selectedPipeModelIds.value.includes(r.pipe_model_id))
  }
  if (subMaterialType.value === 'fitting' && fittingKeyword.value.trim()) {
    const kw = fittingKeyword.value.trim().toLowerCase()
    list = list.filter(r => 
      (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
      (r.model_spec && r.model_spec.toLowerCase().includes(kw))
    )
  }
  if (globalSearchKeyword.value.trim()) {
    const kw = globalSearchKeyword.value.trim().toLowerCase()
    list = list.filter(r => {
      const matchBasic = (
        (r.biz_date && r.biz_date.toLowerCase().includes(kw)) ||
        (r.section_1_name && r.section_1_name.toLowerCase().includes(kw)) ||
        (r.supplier_name && r.supplier_name.toLowerCase().includes(kw)) ||
        (r.batch_no && r.batch_no.toLowerCase().includes(kw)) ||
        (r.vehicle_no && r.vehicle_no.toLowerCase().includes(kw)) ||
        (r.driver_name && r.driver_name.toLowerCase().includes(kw)) ||
        (r.driver_phone && r.driver_phone.includes(kw))
      )
      if (subMaterialType.value === 'pipe') {
        return matchBasic || (r.pipe_model_name && r.pipe_model_name.toLowerCase().includes(kw))
      }
      return matchBasic || (
        (r.fitting_type && r.fitting_type.toLowerCase().includes(kw)) ||
        (r.model_spec && r.model_spec.toLowerCase().includes(kw))
      )
    })
  }
  return list
})

const aggregatedSupplierLedgerRows = computed(() => {
  const rawList = filteredSupplierLedgerRows.value
  const activeDims = supplierLedgerDimensions.value
  if (!activeDims || activeDims.length === 0) return rawList

  const groupsMap = new Map()

  for (const row of rawList) {
    const keyParts = []
    const dimValues = {}

    for (const dim of activeDims) {
      if (dim === 'supplier') {
        const val = row.supplier_name || '—'
        keyParts.push(val)
        dimValues.supplier_name = val
        dimValues.supplier_id = row.supplier_id
      } else if (dim === 'model') {
        if (subMaterialType.value === 'pipe') {
          const val = row.pipe_model_name || '—'
          keyParts.push(val)
          dimValues.pipe_model_name = val
          dimValues.pipe_model_id = row.pipe_model_id
        } else {
          const val = `${row.fitting_type || ''} ${row.model_spec || ''}`.trim() || '—'
          keyParts.push(val)
          dimValues.fitting_type = row.fitting_type || '—'
          dimValues.model_spec = row.model_spec || '—'
        }
      } else if (dim === 'date') {
        const val = row.biz_date || '—'
        keyParts.push(val)
        dimValues.biz_date = val
      } else if (dim === 'section') {
        const val = row.section_1_name || '—'
        keyParts.push(val)
        dimValues.section_1_name = val
        dimValues.section_1_id = row.section_1_id
      }
    }

    const groupKey = keyParts.join('____')

    // 💰 保温管单项货值金额核算与单价匹配说明
    const priceInfo = subMaterialType.value === 'pipe' ? getPipeUnitPriceInfo(row.supplier_name, row.pipe_model_name) : { unitPrice: null, matchNote: '', isExact: true }
    const itPrice = priceInfo.unitPrice
    const itShippedAmt = itPrice != null ? ((Number(row.shipped_qty) || 0) * itPrice) : 0
    const itArrivedAmt = itPrice != null ? ((Number(row.arrived_qty) || 0) * itPrice) : 0
    const itReceivedAmt = itPrice != null ? ((Number(row.received_qty) || 0) * itPrice) : 0
    const itWarehouseAmt = itPrice != null ? ((Number(row.warehouse_qty) || 0) * itPrice) : 0

    const enrichedItem = {
      ...row,
      unit_price: itPrice,
      price_info: priceInfo,
      price_note: priceInfo.matchNote || '',
      is_exact_price: priceInfo.isExact,
      shipped_amount: itShippedAmt,
      arrived_amount: itArrivedAmt,
      received_amount: itReceivedAmt,
      warehouse_amount: itWarehouseAmt
    }

    if (!groupsMap.has(groupKey)) {
      groupsMap.set(groupKey, {
        ...dimValues,
        unit: subMaterialType.value === 'pipe' ? '米' : '件',
        shipped_qty: 0,
        arrived_qty: 0,
        received_qty: 0,
        warehouse_qty: 0,
        shipped_amount: 0,
        arrived_amount: 0,
        received_amount: 0,
        warehouse_amount: 0,
        transit_seconds_sum: 0,
        transit_count: 0,
        orders_count: 0,
        order_items: [],
      })
    }

    const target = groupsMap.get(groupKey)
    target.shipped_qty += Number(row.shipped_qty) || 0
    target.arrived_qty += Number(row.arrived_qty) || 0
    target.received_qty += Number(row.received_qty) || 0
    target.warehouse_qty += Number(row.warehouse_qty) || 0
    target.shipped_amount += itShippedAmt
    target.arrived_amount += itArrivedAmt
    target.received_amount += itReceivedAmt
    target.warehouse_amount += itWarehouseAmt
    target.orders_count += 1
    target.order_items.push(enrichedItem)
    if (Number(row.transit_seconds) > 0) {
      target.transit_seconds_sum += Number(row.transit_seconds)
      target.transit_count += 1
    }
  }

  const result = Array.from(groupsMap.values()).map(g => {
    let avg_transit_display = '在途中'
    if (g.transit_count > 0) {
      const avgSec = g.transit_seconds_sum / g.transit_count
      const h = Math.floor(avgSec / 3600)
      const m = Math.floor((avgSec % 3600) / 60)
      avg_transit_display = h > 0 ? `${h}小时${m}分` : (m > 0 ? `${m}分钟` : '<1分钟')
    } else if (g.arrived_qty > 0) {
      avg_transit_display = '—'
    }
    const fulfillment_rate = g.shipped_qty > 0 ? Math.min(100, (g.arrived_qty / g.shipped_qty * 100)) : 0
    const receipt_rate = g.arrived_qty > 0 ? Math.min(100, (g.received_qty / g.arrived_qty * 100)) : 0
    const warehouse_rate = g.arrived_qty > 0 
      ? Math.min(100, (g.warehouse_qty / g.arrived_qty * 100)) 
      : (g.shipped_qty > 0 ? Math.min(100, (g.warehouse_qty / g.shipped_qty * 100)) : 0)

    // 单价归纳 (若组内所有项单价一致则直接输出精准单价，多项规格混合则输出加权均价)
    const validPrices = Array.from(new Set(g.order_items.map(it => it.unit_price).filter(p => p != null)))
    let unit_price = null
    let is_avg_price = false
    if (validPrices.length === 1) {
      unit_price = validPrices[0]
    } else if (validPrices.length > 1) {
      unit_price = g.shipped_qty > 0 ? (g.shipped_amount / g.shipped_qty) : null
      is_avg_price = true
    }

    // 提取该聚合组内所有的非空单价匹配说明
    const notesSet = new Set(g.order_items.map(it => it.price_note).filter(n => Boolean(n)))
    const price_note = Array.from(notesSet).join('；')
    const has_tolerance_price = g.order_items.some(it => it.price_info && !it.price_info.isExact)

    return {
      ...g,
      unit_price,
      is_avg_price,
      price_note,
      has_tolerance_price,
      avg_transit_display,
      fulfillment_rate: Math.round(fulfillment_rate * 10) / 10,
      receipt_rate: Math.round(receipt_rate * 10) / 10,
      warehouse_rate: Math.round(warehouse_rate * 10) / 10,
    }
  })

  // 多维逐级排序：供给方升序聚合，规格型号默认按大口径到小口径降序排列
  result.sort((a, b) => {
    for (const dim of activeDims) {
      if (dim === 'supplier') {
        const valA = a.supplier_name || ''
        const valB = b.supplier_name || ''
        if (valA !== valB) return valA.localeCompare(valB, 'zh-CN', { numeric: true })
      } else if (dim === 'model') {
        const valA = subMaterialType.value === 'pipe' ? (a.pipe_model_name || '') : (`${a.fitting_type || ''} ${a.model_spec || ''}`).trim();
        const valB = subMaterialType.value === 'pipe' ? (b.pipe_model_name || '') : (`${b.fitting_type || ''} ${b.model_spec || ''}`).trim();
        if (valA !== valB) {
          const comp = compareModelSpecs(valA, valB, 'desc')
          if (comp !== 0) return comp
        }
      } else if (dim === 'date') {
        const valA = a.biz_date || ''
        const valB = b.biz_date || ''
        if (valA !== valB) return valB.localeCompare(valA, 'zh-CN', { numeric: true }) // 日期默认最新在前
      } else if (dim === 'section') {
        const valA = a.section_1_name || ''
        const valB = b.section_1_name || ''
        if (valA !== valB) return valA.localeCompare(valB, 'zh-CN', { numeric: true })
      }
    }
    return 0
  })

  return result
})

const sortedSupplierLedgerRows = computed(() => {
  return sortRows(aggregatedSupplierLedgerRows.value, 'supplier_ledger', {
    supplier: r => r.supplier_name || '',
    model: r => subMaterialType.value === 'pipe' ? (r.pipe_model_name || '') : (`${r.fitting_type || ''} ${r.model_spec || ''}`),
    date: r => r.biz_date || '',
    section: r => r.section_1_name || '',
    unit_price: r => typeof r.unit_price === 'number' ? r.unit_price : 0,
    shipped_qty: r => Number(r.shipped_qty) || 0,
    shipped_amount: r => Number(r.shipped_amount) || 0,
    arrived_qty: r => Number(r.arrived_qty) || 0,
    arrived_amount: r => Number(r.arrived_amount) || 0,
    received_qty: r => Number(r.received_qty) || 0,
    received_amount: r => Number(r.received_amount) || 0,
    warehouse_qty: r => Number(r.warehouse_qty) || 0,
    warehouse_amount: r => Number(r.warehouse_amount) || 0,
    receipt_rate: r => Number(r.receipt_rate) || 0,
    warehouse_rate: r => Number(r.warehouse_rate) || 0,
    orders_count: r => Number(r.orders_count) || 0,
  })
})

const supplierLedgerSummary = computed(() => {
  const rows = filteredSupplierLedgerRows.value
  let total_shipped_qty = 0
  let total_arrived_qty = 0
  let total_received_qty = 0
  let total_warehouse_qty = 0
  let total_shipped_amount = 0
  let total_arrived_amount = 0
  let total_received_amount = 0
  let total_warehouse_amount = 0
  let transit_sum = 0
  let transit_cnt = 0

  for (const r of rows) {
    const sQty = Number(r.shipped_qty) || 0
    const aQty = Number(r.arrived_qty) || 0
    const rQty = Number(r.received_qty) || 0
    const wQty = Number(r.warehouse_qty) || 0
    total_shipped_qty += sQty
    total_arrived_qty += aQty
    total_received_qty += rQty
    total_warehouse_qty += wQty

    if (subMaterialType.value === 'pipe') {
      const price = getPipeUnitPrice(r.supplier_name, r.pipe_model_name)
      if (price != null) {
        total_shipped_amount += sQty * price
        total_arrived_amount += aQty * price
        total_received_amount += rQty * price
        total_warehouse_amount += wQty * price
      }
    }

    if (Number(r.transit_seconds) > 0) {
      transit_sum += Number(r.transit_seconds)
      transit_cnt += 1
    }
  }

  let avg_transit = transit_cnt === 0 && rows.length > 0 ? '在途中' : '—'
  if (transit_cnt > 0) {
    const avgSec = transit_sum / transit_cnt
    const h = Math.floor(avgSec / 3600)
    const m = Math.floor((avgSec % 3600) / 60)
    avg_transit = h > 0 ? `${h}小时${m}分` : (m > 0 ? `${m}分钟` : '<1分钟')
  }

  const fulfillment_rate = total_shipped_qty > 0 ? Math.min(100, (total_arrived_qty / total_shipped_qty * 100)) : 0
  const receipt_rate = total_arrived_qty > 0 ? Math.min(100, (total_received_qty / total_arrived_qty * 100)) : 0
  const warehouse_rate = total_arrived_qty > 0 
    ? Math.min(100, (total_warehouse_qty / total_arrived_qty * 100)) 
    : (total_shipped_qty > 0 ? Math.min(100, (total_warehouse_qty / total_shipped_qty * 100)) : 0)

  const avg_order_amount = rows.length > 0 ? (total_shipped_amount / rows.length) : 0

  return {
    total_shipped_qty: Math.round(total_shipped_qty * 100) / 100,
    total_arrived_qty: Math.round(total_arrived_qty * 100) / 100,
    total_received_qty: Math.round(total_received_qty * 100) / 100,
    total_warehouse_qty: Math.round(total_warehouse_qty * 100) / 100,
    total_shipped_amount: Math.round(total_shipped_amount * 100) / 100,
    total_arrived_amount: Math.round(total_arrived_amount * 100) / 100,
    total_received_amount: Math.round(total_received_amount * 100) / 100,
    total_warehouse_amount: Math.round(total_warehouse_amount * 100) / 100,
    avg_order_amount: Math.round(avg_order_amount * 100) / 100,
    total_orders_count: rows.length,
    overall_avg_transit: avg_transit,
    overall_fulfillment_rate: Math.round(fulfillment_rate * 10) / 10,
    overall_receipt_rate: Math.round(receipt_rate * 10) / 10,
    overall_warehouse_rate: Math.round(warehouse_rate * 10) / 10,
  }
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
  setDateRangeByCapsule('project')
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
  } else if (capsule === 'project' || capsule === 'all') {
    filterStartDate.value = '2026-07-28'
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
      const isPriceMode = subMaterialType.value === 'price'
      const promises = [
        getComprehensiveBaselineProgress(projectKey, {
          section1Ids: selectedSectionIds.value,
          pipeModelIds: selectedPipeModelIds.value,
          materialType: isPriceMode ? 'pipe' : subMaterialType.value,
        })
      ]
      // 只要进入 Tab 2 或当前是 price 模式，拉取物料单价字典
      if (isPriceMode || materialPriceList.value.length === 0) {
        promises.push(getTubeMaterialPrices(projectKey))
      }
      const results = await Promise.all(promises)
      baselineProgressData.value = results[0]
      if (results[1] && results[1].data) {
        materialPriceList.value = results[1].data
      }
    } else if (activeTab.value === 'supplier_ledger') {
      const res = await getComprehensiveSupplierLedger(projectKey, {
        startDate: filterStartDate.value,
        endDate: filterEndDate.value,
        section1Ids: selectedSectionIds.value,
        pipeModelIds: selectedPipeModelIds.value,
        materialType: subMaterialType.value === 'price' ? 'pipe' : subMaterialType.value,
      })
      supplierLedgerData.value = res
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
  if (tab === 'supplier_ledger') {
    subMaterialType.value = 'pipe'
  }
  fetchActiveTabData()
}

function switchSubMaterial(mat) {
  if (mat === 'price' && !isPriceUnlocked.value) {
    openPriceAuthModal()
    return
  }
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
  resetPriceFilters()
  setDateRangeByCapsule('project')
  tableSortStates.value = {
    daily_pipe: { key: '', order: '' },
    daily_fitting: { key: '', order: '' },
    baseline_pipe: { key: '', order: '' },
    fitting_baseline: { key: '', order: '' },
    fitting_flow: { key: '', order: '' },
    price_table: { key: '', order: '' },
    supplier_ledger: { key: '', order: '' }
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
// 📥 高规格 Excel 导出引擎 (基于 xlsx-js-style，支持分供给方汇总 + 多维明细小计 + 多Sheet)
// -----------------------------------------------------------------------------

function getExcelCellAlignment(val, isHeader, isFirstCol) {
  if (isHeader) return { horizontal: 'center', vertical: 'center' }
  if (val === undefined || val === null || val === '') return { horizontal: 'center', vertical: 'center' }
  
  if (typeof val === 'number') {
    return { horizontal: 'right', vertical: 'center' }
  }
  
  const str = String(val).trim()
  
  // 百分比率 (如 "100.0%", "66.7%") 靠右对齐与数值列保持一致
  if (/^\d+(\.\d+)?%$/.test(str)) {
    return { horizontal: 'right', vertical: 'center' }
  }
  
  // 占位符横杠
  if (str === '—' || str === '-') {
    return { horizontal: 'center', vertical: 'center' }
  }
  
  // 日期格式 (YYYY-MM-DD)
  if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
    return { horizontal: 'center', vertical: 'center' }
  }
  
  // 在途时长描述
  if (str.includes('小时') || str.includes('分钟') || str === '在途中' || str === '<1分钟') {
    return { horizontal: 'center', vertical: 'center' }
  }
  
  // 状态、车牌号、手机号、纯单位
  if (['已入库', '已接收', '已到货', '在途中', '已发货', '米', '件', '个'].includes(str) || /^1\d{10}$/.test(str) || /^[\u4e00-\u9fa5][A-Z][A-Z0-9]{5,6}$/.test(str)) {
    return { horizontal: 'center', vertical: 'center' }
  }
  
  // 小计或总计首列
  if (str.startsWith('【小计】') || str.startsWith('【全项目总计】') || str.startsWith('【本组穿透汇总】')) {
    return { horizontal: 'left', vertical: 'center' }
  }
  
  // 文本类（供给方名称、型号规格、标段名称等）首列或文本列靠左对齐
  return { horizontal: isFirstCol ? 'left' : 'left', vertical: 'center' }
}

function buildStyledWorksheet(headers, dataRows, subtotalRowIndices = [], grandTotalRowIndex = null) {
  const wsData = [headers, ...dataRows]
  const ws = XLSX.utils.aoa_to_sheet(wsData)

  const headerStyle = {
    font: { name: 'Microsoft YaHei', sz: 11, bold: true, color: { rgb: 'FFFFFF' } },
    fill: { fgColor: { rgb: '1E293B' } },
    alignment: { horizontal: 'center', vertical: 'center' },
    border: {
      top: { style: 'thin', color: { rgb: 'CBD5E1' } },
      bottom: { style: 'medium', color: { rgb: '0F172A' } },
      left: { style: 'thin', color: { rgb: 'CBD5E1' } },
      right: { style: 'thin', color: { rgb: 'CBD5E1' } },
    },
  }

  const cellBorder = {
    top: { style: 'thin', color: { rgb: 'E2E8F0' } },
    bottom: { style: 'thin', color: { rgb: 'E2E8F0' } },
    left: { style: 'thin', color: { rgb: 'E2E8F0' } },
    right: { style: 'thin', color: { rgb: 'E2E8F0' } },
  }

  const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:A1')
  for (let R = range.s.r; R <= range.e.r; ++R) {
    const isHeader = R === 0
    const isSubtotal = subtotalRowIndices.includes(R)
    const isGrandTotal = grandTotalRowIndex === R

    for (let C = range.s.c; C <= range.e.c; ++C) {
      const cellRef = XLSX.utils.encode_cell({ r: R, c: C })
      if (!ws[cellRef]) ws[cellRef] = { v: '' }

      const val = ws[cellRef].v
      const align = getExcelCellAlignment(val, isHeader, C === 0)

      if (isHeader) {
        ws[cellRef].s = headerStyle
      } else if (isSubtotal) {
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 10, bold: true, color: { rgb: '0369A1' } },
          fill: { fgColor: { rgb: 'E0F2FE' } },
          alignment: align,
          border: {
            top: { style: 'thin', color: { rgb: 'BAE6FD' } },
            bottom: { style: 'thin', color: { rgb: '0284C7' } },
            left: { style: 'thin', color: { rgb: 'BAE6FD' } },
            right: { style: 'thin', color: { rgb: 'BAE6FD' } },
          },
        }
      } else if (isGrandTotal) {
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 10.5, bold: true, color: { rgb: '0F172A' } },
          fill: { fgColor: { rgb: 'F1F5F9' } },
          alignment: align,
          border: {
            top: { style: 'medium', color: { rgb: '64748B' } },
            bottom: { style: 'double', color: { rgb: '0F172A' } },
            left: { style: 'thin', color: { rgb: 'CBD5E1' } },
            right: { style: 'thin', color: { rgb: 'CBD5E1' } },
          },
        }
      } else {
        const isNum = typeof val === 'number'
        ws[cellRef].s = {
          font: { name: 'Microsoft YaHei', sz: 10, bold: isNum },
          fill: { fgColor: { rgb: R % 2 === 0 ? 'FFFFFF' : 'F8FAFC' } },
          alignment: align,
          border: cellBorder,
        }
      }
    }
  }

  // 自动计算黄金列宽
  const colWidths = headers.map((h, i) => {
    let maxLen = (h || '').length * 2.2
    dataRows.forEach(row => {
      const str = String(row[i] || '')
      if (str.length * 1.6 > maxLen) maxLen = str.length * 1.6
    })
    return { wch: Math.max(12, Math.min(65, Math.ceil(maxLen) + 3)) }
  })
  ws['!cols'] = colWidths

  return ws
}

async function exportCurrentTabExcel() {
  exportLoading.value = true
  try {
    const wb = XLSX.utils.book_new()
    let defaultFilename = ''

    if (activeTab.value === 'supplier_ledger') {
      // =======================================================================
      // 🏭 Tab 3: 供给方发运台账 (单 Sheet: 多维明细台账 含单价金额、供给方小计与全项目总计)
      // =======================================================================
      const isPipe = subMaterialType.value === 'pipe'
      const withCalc = isPipe && showPipeAmountCalc.value
      const activeDims = supplierLedgerDimensions.value
      const dimHeaders = activeDims.map(d => getDimensionDef(d).colHeader)

      let detailHeaders = []
      if (isPipe) {
        if (withCalc) {
          detailHeaders = [...dimHeaders, '单价(元/米)', '发货量(米)', '发货金额(元)', '确认到货量(米)', '到货金额(元)', '施工接收量(米)', '接收金额(元)', '库管确认量(米)', '入库金额(元)', '发运车次(单)', '平均在途时长', '到货确认率', '接收确认率', '库管确认率', '单价核算备注']
        } else {
          detailHeaders = [...dimHeaders, '发货量(米)', '确认到货量(米)', '施工接收量(米)', '库管确认量(米)', '发运车次(单)', '平均在途时长', '到货确认率', '接收确认率', '库管确认率']
        }
      } else {
        detailHeaders = [...dimHeaders, '发货数量(件)', '确认到货数(件)', '施工接收数(件)', '库管确认数(件)', '发货批次(单)', '平均在途时长', '到货确认率', '接收确认率', '库管确认率']
      }

      // 按供给方分组并插入小计行
      const detailRows = []
      const subtotalIndices = []
      let totalShipped = 0, totalArrived = 0, totalReceived = 0, totalWarehouse = 0, totalOrders = 0
      let totalShippedAmt = 0, totalArrivedAmt = 0, totalReceivedAmt = 0, totalWarehouseAmt = 0

      // 检查当前排序明细
      const groupedBySupplier = new Map()
      sortedSupplierLedgerRows.value.forEach(r => {
        const sup = r.supplier_name || '未知供给方'
        if (!groupedBySupplier.has(sup)) groupedBySupplier.set(sup, [])
        groupedBySupplier.get(sup).push(r)
      })

      groupedBySupplier.forEach((rows, supName) => {
        let subShipped = 0, subArrived = 0, subReceived = 0, subWarehouse = 0, subOrders = 0
        let subShippedAmt = 0, subArrivedAmt = 0, subReceivedAmt = 0, subWarehouseAmt = 0
        let subTransitSumSec = 0, subTransitCount = 0

        rows.forEach(r => {
          const sQty = Number(r.shipped_qty) || 0
          const aQty = Number(r.arrived_qty) || 0
          const rQty = Number(r.received_qty) || 0
          const wQty = Number(r.warehouse_qty) || 0
          const oCnt = Number(r.orders_count) || 0

          const sAmt = Number(r.shipped_amount) || 0
          const aAmt = Number(r.arrived_amount) || 0
          const rAmt = Number(r.received_amount) || 0
          const wAmt = Number(r.warehouse_amount) || 0

          subShipped += sQty
          subArrived += aQty
          subReceived += rQty
          subWarehouse += wQty
          subOrders += oCnt

          subShippedAmt += sAmt
          subArrivedAmt += aAmt
          subReceivedAmt += rAmt
          subWarehouseAmt += wAmt

          totalShipped += sQty
          totalArrived += aQty
          totalReceived += rQty
          totalWarehouse += wQty
          totalOrders += oCnt

          totalShippedAmt += sAmt
          totalArrivedAmt += aAmt
          totalReceivedAmt += rAmt
          totalWarehouseAmt += wAmt

          // 累加已到货单据在途秒数
          const itemsList = r.order_items || [r]
          itemsList.forEach(item => {
            if (Number(item.transit_seconds) > 0) {
              subTransitSumSec += Number(item.transit_seconds)
              subTransitCount++
            }
          })

          const dimVals = activeDims.map(d => {
            if (d === 'supplier') return r.supplier_name || '—'
            if (d === 'model') return isPipe ? (r.pipe_model_name || '—') : (`${r.fitting_type || ''} ${r.model_spec || ''}`.trim() || '—')
            if (d === 'date') return r.biz_date || '—'
            if (d === 'section') return r.section_1_name || '—'
            return '—'
          })

          if (withCalc) {
            const priceVal = typeof r.unit_price === 'number' 
              ? Number(r.unit_price.toFixed(2)) 
              : (r.unit_price === 'multiple' ? '多项单价' : '—')

            const noteVal = r.price_note || (r.is_avg_price ? '多规格综合加权均价' : '—')

            detailRows.push([
              ...dimVals,
              priceVal,
              Number(sQty.toFixed(2)),
              Number(sAmt.toFixed(2)),
              Number(aQty.toFixed(2)),
              Number(aAmt.toFixed(2)),
              Number(rQty.toFixed(2)),
              Number(rAmt.toFixed(2)),
              Number(wQty.toFixed(2)),
              Number(wAmt.toFixed(2)),
              r.orders_count,
              r.avg_transit_display || '—',
              `${r.fulfillment_rate}%`,
              `${r.receipt_rate}%`,
              `${r.warehouse_rate}%`,
              noteVal
            ])
          } else {
            detailRows.push([
              ...dimVals,
              isPipe ? Number(r.shipped_qty.toFixed(2)) : r.shipped_qty,
              isPipe ? Number(r.arrived_qty.toFixed(2)) : r.arrived_qty,
              isPipe ? Number(r.received_qty.toFixed(2)) : r.received_qty,
              isPipe ? Number(r.warehouse_qty.toFixed(2)) : r.warehouse_qty,
              r.orders_count,
              r.avg_transit_display || '—',
              `${r.fulfillment_rate}%`,
              `${r.receipt_rate}%`,
              `${r.warehouse_rate}%`
            ])
          }
        })

        // 插入当前供给方的小计行（仅统计已到货单据的平均在途时长）
        const subAvgTransitSec = subTransitCount > 0 ? Math.round(subTransitSumSec / subTransitCount) : 0
        const subTransitDisp = subTransitCount > 0 
          ? (subAvgTransitSec >= 3600 ? `${Math.floor(subAvgTransitSec / 3600)}小时${Math.floor((subAvgTransitSec % 3600) / 60)}分` : `${Math.floor(subAvgTransitSec / 60)}分钟`)
          : (subOrders > 0 ? '在途中' : '—')

        const subFulfill = subShipped > 0 ? Math.min(100, ((subArrived / subShipped) * 100)).toFixed(1) : '0.0'
        const subReceipt = subArrived > 0 ? Math.min(100, ((subReceived / subArrived) * 100)).toFixed(1) : '0.0'
        const subWarehouseRate = subArrived > 0 ? Math.min(100, ((subWarehouse / subArrived) * 100)).toFixed(1) : (subShipped > 0 ? Math.min(100, ((subWarehouse / subShipped) * 100)).toFixed(1) : '0.0')
        const subDimVals = activeDims.map((d, i) => i === 0 ? `【小计】${supName}` : '—')

        if (withCalc) {
          const subAvgPrice = subShipped > 0 ? Number((subShippedAmt / subShipped).toFixed(2)) : '—'
          detailRows.push([
            ...subDimVals,
            subAvgPrice,
            Number(subShipped.toFixed(2)),
            Number(subShippedAmt.toFixed(2)),
            Number(subArrived.toFixed(2)),
            Number(subArrivedAmt.toFixed(2)),
            Number(subReceived.toFixed(2)),
            Number(subReceivedAmt.toFixed(2)),
            Number(subWarehouse.toFixed(2)),
            Number(subWarehouseAmt.toFixed(2)),
            subOrders,
            subTransitDisp,
            `${subFulfill}%`,
            `${subReceipt}%`,
            `${subWarehouseRate}%`,
            '供给方小计均价核算'
          ])
        } else {
          detailRows.push([
            ...subDimVals,
            isPipe ? Number(subShipped.toFixed(2)) : subShipped,
            isPipe ? Number(subArrived.toFixed(2)) : subArrived,
            isPipe ? Number(subReceived.toFixed(2)) : subReceived,
            isPipe ? Number(subWarehouse.toFixed(2)) : subWarehouse,
            subOrders,
            subTransitDisp,
            `${subFulfill}%`,
            `${subReceipt}%`,
            `${subWarehouseRate}%`
          ])
        }
        subtotalIndices.push(detailRows.length)
      })

      // 插入明细表的最后总计行
      const overallFulfillment = totalShipped > 0 ? Math.min(100, ((totalArrived / totalShipped) * 100)).toFixed(1) : '0.0'
      const overallReceipt = totalArrived > 0 ? Math.min(100, ((totalReceived / totalArrived) * 100)).toFixed(1) : '0.0'
      const overallWarehouse = totalArrived > 0 ? Math.min(100, ((totalWarehouse / totalArrived) * 100)).toFixed(1) : (totalShipped > 0 ? Math.min(100, ((totalWarehouse / totalShipped) * 100)).toFixed(1) : '0.0')
      const grandDimVals = activeDims.map((d, i) => i === 0 ? '【全项目总计】' : '—')

      if (withCalc) {
        const totalAvgPrice = totalShipped > 0 ? Number((totalShippedAmt / totalShipped).toFixed(2)) : '—'
        detailRows.push([
          ...grandDimVals,
          totalAvgPrice,
          Number(totalShipped.toFixed(2)),
          Number(totalShippedAmt.toFixed(2)),
          Number(totalArrived.toFixed(2)),
          Number(totalArrivedAmt.toFixed(2)),
          Number(totalReceived.toFixed(2)),
          Number(totalReceivedAmt.toFixed(2)),
          Number(totalWarehouse.toFixed(2)),
          Number(totalWarehouseAmt.toFixed(2)),
          totalOrders,
          supplierLedgerSummary.value.overall_avg_transit || '—',
          `${overallFulfillment}%`,
          `${overallReceipt}%`,
          `${overallWarehouse}%`,
          '全项目综合均价核算'
        ])
      } else {
        detailRows.push([
          ...grandDimVals,
          isPipe ? Number(totalShipped.toFixed(2)) : totalShipped,
          isPipe ? Number(totalArrived.toFixed(2)) : totalArrived,
          isPipe ? Number(totalReceived.toFixed(2)) : totalReceived,
          isPipe ? Number(totalWarehouse.toFixed(2)) : totalWarehouse,
          totalOrders,
          supplierLedgerSummary.value.overall_avg_transit || '—',
          `${overallFulfillment}%`,
          `${overallReceipt}%`,
          `${overallWarehouse}%`
        ])
      }

      const wsDetail = buildStyledWorksheet(detailHeaders, detailRows, subtotalIndices, detailRows.length)
      XLSX.utils.book_append_sheet(wb, wsDetail, '多维明细台账')

      defaultFilename = isPipe
        ? `保温管供给方发运综合台账_${filterStartDate.value}_${filterEndDate.value}.xlsx`
        : `管件供给方发运综合台账_${filterStartDate.value}_${filterEndDate.value}.xlsx`

    } else if (activeTab.value === 'daily_flow') {
      // =======================================================================
      // 📅 Tab 1: 每日历史流转台账 (分供给方汇总 Sheet + 每日流转透视 Sheet)
      // =======================================================================
      const isPipe = subMaterialType.value === 'pipe'
      const activeDims = dailyDimensions.value
      const dimHeaders = activeDims.map(d => getDimensionDef(d).colHeader)

      // 1. 分供给方流转汇总 Sheet
      const supMap = new Map()
      if (isPipe) {
        sortedDailyPipeRows.value.forEach(r => {
          const sup = r.supplier_name || '未知供货单位'
          if (!supMap.has(sup)) supMap.set(sup, { sup, plan: 0, shipped: 0, arrived: 0, received: 0, usage: 0, loss: 0, warehouse: 0 })
          const item = supMap.get(sup)
          item.plan += Number(r.plan_qty) || 0
          item.shipped += Number(r.shipped_qty) || 0
          item.arrived += Number(r.arrived_qty) || 0
          item.received += Number(r.received_qty) || 0
          item.usage += Number(r.usage_qty) || 0
          item.loss += Number(r.loss_qty) || 0
          item.warehouse += Number(r.warehouse_qty) || 0
        })

        const sHeaders = ['供给方', '计划总量(米)', '发货总量(米)', '到货总量(米)', '施工接收(米)', '实际使用(米)', '损耗量(米)', '库管已确认(米)', '到货确认率']
        const sRows = []
        let gPlan = 0, gShip = 0, gArr = 0, gRec = 0, gUse = 0, gLoss = 0, gWh = 0

        supMap.forEach(s => {
          gPlan += s.plan; gShip += s.shipped; gArr += s.arrived; gRec += s.received; gUse += s.usage; gLoss += s.loss; gWh += s.warehouse
          const rate = s.shipped > 0 ? ((s.arrived / s.shipped) * 100).toFixed(1) : '0.0'
          sRows.push([s.sup, Number(s.plan.toFixed(2)), Number(s.shipped.toFixed(2)), Number(s.arrived.toFixed(2)), Number(s.received.toFixed(2)), Number(s.usage.toFixed(2)), Number(s.loss.toFixed(2)), Number(s.warehouse.toFixed(2)), `${rate}%`])
        })
        const gRate = gShip > 0 ? ((gArr / gShip) * 100).toFixed(1) : '0.0'
        sRows.push(['【全项目总计】', Number(gPlan.toFixed(2)), Number(gShip.toFixed(2)), Number(gArr.toFixed(2)), Number(gRec.toFixed(2)), Number(gUse.toFixed(2)), Number(gLoss.toFixed(2)), Number(gWh.toFixed(2)), `${gRate}%`])

        const wsSup = buildStyledWorksheet(sHeaders, sRows, [], sRows.length)
        XLSX.utils.book_append_sheet(wb, wsSup, '分供给方流转汇总')
      } else {
        sortedDailyFittingRows.value.forEach(r => {
          const sup = r.supplier_name || '未知供货单位'
          if (!supMap.has(sup)) supMap.set(sup, { sup, shipped: 0, arrived: 0, received: 0, usage: 0, warehouse: 0 })
          const item = supMap.get(sup)
          item.shipped += Number(r.shipped_qty) || 0
          item.arrived += Number(r.arrived_qty) || 0
          item.received += Number(r.received_qty) || 0
          item.usage += Number(r.usage_qty) || 0
          item.warehouse += Number(r.warehouse_qty) || 0
        })

        const sHeaders = ['供给方', '发货数量(件)', '到货数量(件)', '施工接收(件)', '现场安装(件)', '库管已确认(件)', '现场结余(件)', '到货确认率']
        const sRows = []
        let gShip = 0, gArr = 0, gRec = 0, gUse = 0, gWh = 0

        supMap.forEach(s => {
          gShip += s.shipped; gArr += s.arrived; gRec += s.received; gUse += s.usage; gWh += s.warehouse
          const rate = s.shipped > 0 ? ((s.arrived / s.shipped) * 100).toFixed(1) : '0.0'
          sRows.push([s.sup, s.shipped, s.arrived, s.received, s.usage, s.warehouse, Math.max(0, s.arrived - s.usage), `${rate}%`])
        })
        const gRate = gShip > 0 ? ((gArr / gShip) * 100).toFixed(1) : '0.0'
        sRows.push(['【全项目总计】', gShip, gArr, gRec, gUse, gWh, Math.max(0, gArr - gUse), `${gRate}%`])

        const wsSup = buildStyledWorksheet(sHeaders, sRows, [], sRows.length)
        XLSX.utils.book_append_sheet(wb, wsSup, '分供给方流转汇总')
      }

      // 2. 流转明细台账 Sheet
      const dHeaders = isPipe
        ? [...dimHeaders, '计划量(米)', '发货量(米)', '到货量(米)', '施工接收(米)', '现场使用(米)', '损耗量(米)', '库管已确认(米)']
        : [...dimHeaders, '发货数量(件)', '到货数量(件)', '施工接收(件)', '现场安装(件)', '库管已确认(件)', '现场结余(件)']

      const dRows = (isPipe ? sortedDailyPipeRows.value : sortedDailyFittingRows.value).map(r => {
        const dimVals = activeDims.map(d => {
          if (d === 'date') return r.biz_date || '—'
          if (d === 'section') return r.section_1_name || '—'
          if (d === 'model') return isPipe ? (r.pipe_model_name || '—') : (`${r.fitting_type || ''} ${r.model_spec || ''}`.trim() || '—')
          if (d === 'supplier') return r.supplier_name || '—'
          return '—'
        })
        return isPipe
          ? [...dimVals, Number((Number(r.plan_qty) || 0).toFixed(2)), Number((Number(r.shipped_qty) || 0).toFixed(2)), Number((Number(r.arrived_qty) || 0).toFixed(2)), Number((Number(r.received_qty) || 0).toFixed(2)), Number((Number(r.usage_qty) || 0).toFixed(2)), Number((Number(r.loss_qty) || 0).toFixed(2)), Number((Number(r.warehouse_qty) || 0).toFixed(2))]
          : [...dimVals, Number(r.shipped_qty) || 0, Number(r.arrived_qty) || 0, Number(r.received_qty) || 0, Number(r.usage_qty) || 0, Number(r.warehouse_qty) || 0, Math.max(0, (Number(r.arrived_qty) || 0) - (Number(r.usage_qty) || 0))]
      })

      // 补上明细表末尾【全项目总计】行
      const grandDimVals = activeDims.map((d, i) => i === 0 ? '【全项目总计】' : '—')
      if (isPipe) {
        const sum = dailyPipeSummary.value
        dRows.push([
          ...grandDimVals,
          Number((Number(sum.total_plan_qty) || 0).toFixed(2)),
          Number((Number(sum.total_shipped_qty) || 0).toFixed(2)),
          Number((Number(sum.total_arrived_qty) || 0).toFixed(2)),
          Number((Number(sum.total_received_qty) || 0).toFixed(2)),
          Number((Number(sum.total_usage_qty) || 0).toFixed(2)),
          Number((Number(sum.total_loss_qty) || 0).toFixed(2)),
          Number((Number(sum.total_warehouse_qty) || 0).toFixed(2))
        ])
      } else {
        const sum = dailyFittingSummary.value
        dRows.push([
          ...grandDimVals,
          Number(sum.total_shipped_qty) || 0,
          Number(sum.total_arrived_qty) || 0,
          Number(sum.total_received_qty) || 0,
          Number(sum.total_usage_qty) || 0,
          Number(sum.total_warehouse_qty) || 0,
          Number(sum.site_stock_pcs) || 0
        ])
      }

      const wsDetail = buildStyledWorksheet(dHeaders, dRows, [], dRows.length)
      XLSX.utils.book_append_sheet(wb, wsDetail, '流转透视明细')

      defaultFilename = isPipe
        ? `保温管每日历史流转综合台账_${filterStartDate.value}_${filterEndDate.value}.xlsx`
        : `管件每日历史流转综合台账_${filterStartDate.value}_${filterEndDate.value}.xlsx`

    } else if (activeTab.value === 'baseline_progress') {
      // =======================================================================
      // 📐 Tab 2: 设计基准进度 / 采购价格 (分供给方基准汇总 Sheet + 明细表 Sheet)
      // =======================================================================
      if (subMaterialType.value === 'price') {
        // 💰 导出采购价格字典 (不包含累计汇总行，仅输出纯净明细数据)
        const pHeaders = ['序号', '物料大类', '供给方全称', '物理类别', '材料标准名称', '规格型号描述', '计量单位', '单价（元）', '备注说明']
        const pRows = sortedMaterialPriceRows.value.map((r, idx) => [
          idx + 1,
          r.material_kind === 'pipe' ? '保温管' : '管件',
          r.supplier_name || '—',
          r.category || '—',
          r.material_name || '—',
          r.model_spec || '—',
          r.unit || '个',
          Number(Number(r.unit_price || 0).toFixed(2)),
          (r.remark && String(r.remark).trim()) ? String(r.remark).trim() : '—'
        ])

        const wsPrice = buildStyledWorksheet(pHeaders, pRows, [], null)
        XLSX.utils.book_append_sheet(wb, wsPrice, '物料采购单价字典')
        defaultFilename = `保温管与管件物料采购价格基准字典_${new Date().toISOString().split('T')[0]}.xlsx`

      } else if (subMaterialType.value === 'pipe') {
        const isPipe = true
        const activeDims = baselineDimensions.value
        const dimHeaders = activeDims.map(d => getDimensionDef(d).colHeader)
        // 1. 分供给方基准汇总
        const supMap = new Map()
        sortedBaselinePipeRows.value.forEach(r => {
          const sup = r.supplier_name || '未知供货单位'
          if (!supMap.has(sup)) supMap.set(sup, { sup, design: 0, plan: 0, ship: 0, arr: 0, use: 0, stock: 0 })
          const item = supMap.get(sup)
          item.design += Number(r.design_qty) || 0
          item.plan += Number(r.purchase_plan_qty) || 0
          item.ship += Number(r.total_shipped_qty) || 0
          item.arr += Number(r.total_arrived_qty) || 0
          item.use += Number(r.total_usage_qty) || 0
          item.stock += Number(r.stock_qty) || 0
        })

        const sHeaders = ['供给方', '设计总量(米)', '计划采购量(米)', '累计发货(米)', '累计到货(米)', '累计使用(米)', '现场库存(米)', '采购完成率', '施工进度率']
        const sRows = []
        let gDes = 0, gPlan = 0, gShip = 0, gArr = 0, gUse = 0, gStock = 0

        supMap.forEach(s => {
          gDes += s.design; gPlan += s.plan; gShip += s.ship; gArr += s.arr; gUse += s.use; gStock += s.stock
          const pRate = s.plan > 0 ? ((s.arr / s.plan) * 100).toFixed(1) : '0.0'
          const iRate = s.design > 0 ? ((s.use / s.design) * 100).toFixed(1) : '0.0'
          sRows.push([s.sup, Number(s.design.toFixed(2)), Number(s.plan.toFixed(2)), Number(s.ship.toFixed(2)), Number(s.arr.toFixed(2)), Number(s.use.toFixed(2)), Number(s.stock.toFixed(2)), `${pRate}%`, `${iRate}%`])
        })
        const gpRate = gPlan > 0 ? ((gArr / gPlan) * 100).toFixed(1) : '0.0'
        const giRate = gDes > 0 ? ((gUse / gDes) * 100).toFixed(1) : '0.0'
        sRows.push(['【全项目总计】', Number(gDes.toFixed(2)), Number(gPlan.toFixed(2)), Number(gShip.toFixed(2)), Number(gArr.toFixed(2)), Number(gUse.toFixed(2)), Number(gStock.toFixed(2)), `${gpRate}%`, `${giRate}%`])

        const wsSup = buildStyledWorksheet(sHeaders, sRows, [], sRows.length)
        XLSX.utils.book_append_sheet(wb, wsSup, '分供给方基准汇总')

        // 2. 明细 Sheet
        const dHeaders = [...dimHeaders, '设计量(米)', '计划采购量(米)', '累计发货(米)', '累计到货(米)', '累计使用(米)', '现场库存(米)', '采购完成率', '施工进度率']
        const dRows = sortedBaselinePipeRows.value.map(r => {
          const dimVals = activeDims.map(d => {
            if (d === 'section') return r.section_1_name || '—'
            if (d === 'model') return r.pipe_model_name || '—'
            if (d === 'supplier') return r.supplier_name || '—'
            return '—'
          })
          return [...dimVals, Number((Number(r.design_qty) || 0).toFixed(2)), Number((Number(r.purchase_plan_qty) || 0).toFixed(2)), Number((Number(r.total_shipped_qty) || 0).toFixed(2)), Number((Number(r.total_arrived_qty) || 0).toFixed(2)), Number((Number(r.total_usage_qty) || 0).toFixed(2)), Number((Number(r.stock_qty) || 0).toFixed(2)), `${r.purchase_rate}%`, `${r.install_rate}%`]
        })

        // 补上基准进度明细表末尾【全项目总计】行
        const grandDimVals = activeDims.map((d, i) => i === 0 ? '【全项目总计】' : '—')
        const sum = baselinePipeSummary.value
        dRows.push([
          ...grandDimVals,
          Number((Number(sum.total_design_qty) || 0).toFixed(2)),
          Number((Number(sum.total_purchase_plan_qty) || 0).toFixed(2)),
          Number((Number(sum.total_shipped_qty) || 0).toFixed(2)),
          Number((Number(sum.total_arrived_qty) || 0).toFixed(2)),
          Number((Number(sum.total_usage_qty) || 0).toFixed(2)),
          Number((Number(sum.total_stock_qty) || 0).toFixed(2)),
          `${sum.overall_purchase_rate}%`,
          `${sum.overall_install_rate}%`
        ])

        const wsDetail = buildStyledWorksheet(dHeaders, dRows, [], dRows.length)
        XLSX.utils.book_append_sheet(wb, wsDetail, '基准进度明细')
        defaultFilename = '保温管设计采购基准进度综合报表.xlsx'

      } else if (fittingTab2SubView.value === 'baseline') {
        // 管件基准表
        const dHeaders = [...dimHeaders, '单位', '设计使用量', '计划采购量']
        const dRows = sortedFittingBaselineRows.value.map(r => {
          const dimVals = activeDims.map(d => {
            if (d === 'section') return r.section_1_name || '—'
            if (d === 'model') return `${r.fitting_type || r.standard_name || r.category || ''} ${r.model_spec || ''}`.trim() || '—'
            if (d === 'supplier') return r.supplier_name || '—'
            return '—'
          })
          return [...dimVals, r.unit || '个', Number(r.design_qty) || 0, Number(r.purchase_plan_qty) || 0]
        })

        // 补上管件设计与采购基准表末尾【全项目总计】行
        const grandDimVals = activeDims.map((d, i) => i === 0 ? '【全项目总计】' : '—')
        const sum = baselineFittingSummary.value
        dRows.push([
          ...grandDimVals,
          '件',
          Number(sum.total_design_qty) || 0,
          Number(sum.total_purchase_plan_qty) || 0
        ])

        const wsDetail = buildStyledWorksheet(dHeaders, dRows, [], dRows.length)
        XLSX.utils.book_append_sheet(wb, wsDetail, '管件设计与采购基准')
        defaultFilename = '管件设计与计划采购基准表.xlsx'
      } else {
        // 管件全周期流转
        const dHeaders = [...dimHeaders, '单位', '累计发货量', '累计到货量', '现场安装量', '现场库存余量']
        const dRows = sortedFittingFlowRows.value.map(r => {
          const dimVals = activeDims.map(d => {
            if (d === 'section') return r.section_1_name || '—'
            if (d === 'model') return `${r.fitting_type || ''} ${r.model_spec || ''}`.trim() || '—'
            if (d === 'supplier') return r.supplier_name || '—'
            return '—'
          })
          return [...dimVals, '件', Number(r.total_shipped_qty) || 0, Number(r.total_arrived_qty) || 0, Number(r.total_usage_qty) || 0, Number(r.stock_qty) || 0]
        })

        // 补上管件全周期流转与库存表末尾【全项目总计】行
        const grandDimVals = activeDims.map((d, i) => i === 0 ? '【全项目总计】' : '—')
        const sum = baselineFittingSummary.value
        dRows.push([
          ...grandDimVals,
          '件',
          Number(sum.total_shipped_qty) || 0,
          Number(sum.total_arrived_qty) || 0,
          Number(sum.total_usage_qty) || 0,
          Number(sum.total_stock_qty) || 0
        ])

        const wsDetail = buildStyledWorksheet(dHeaders, dRows, [], dRows.length)
        XLSX.utils.book_append_sheet(wb, wsDetail, '管件全周期流转库存')
        defaultFilename = '管件全周期累计流转与现场库存表.xlsx'
      }

    } else if (activeTab.value === 'supplier_ledger') {
      // =======================================================================
      // 🏭 Tab 3: 供给方发货流转台账专属导出 (支持单价与金额联动)
      // =======================================================================
      const isPipe = subMaterialType.value === 'pipe'
      const activeDims = supplierLedgerDimensions.value
      const dimHeaders = activeDims.map(d => getDimensionDef(d).colHeader)

      let sHeaders = []
      if (isPipe) {
        if (showPipeAmountCalc.value) {
          sHeaders = [...dimHeaders, '发货量(米)', '发货金额(元)', '确认到货(米)', '到货金额(元)', '施工接收(米)', '接收金额(元)', '库管已确认(米)', '入库金额(元)', '在途时长', '发运单数', '到货确认率']
        } else {
          sHeaders = [...dimHeaders, '发货量(米)', '确认到货(米)', '施工接收(米)', '库管已确认(米)', '在途时长', '发运单数', '到货确认率']
        }
      } else {
        sHeaders = [...dimHeaders, '发货数量(件)', '确认到货(件)', '施工接收(件)', '库管已确认(件)', '在途时长', '发货批次数', '到货确认率']
      }

      const sRows = sortedSupplierLedgerRows.value.map(r => {
        const dimVals = activeDims.map(d => {
          if (d === 'supplier') return r.supplier_name || '—'
          if (d === 'model') return isPipe ? (r.pipe_model_name || '—') : (`${r.fitting_type || ''} ${r.model_spec || ''}`.trim() || '—')
          if (d === 'date') return r.biz_date || '—'
          if (d === 'section') return r.section_1_name || '—'
          return '—'
        })

        if (isPipe) {
          if (showPipeAmountCalc.value) {
            return [
              ...dimVals,
              Number((Number(r.shipped_qty) || 0).toFixed(2)),
              Number((Number(r.shipped_amount) || 0).toFixed(2)),
              Number((Number(r.arrived_qty) || 0).toFixed(2)),
              Number((Number(r.arrived_amount) || 0).toFixed(2)),
              Number((Number(r.received_qty) || 0).toFixed(2)),
              Number((Number(r.received_amount) || 0).toFixed(2)),
              Number((Number(r.warehouse_qty) || 0).toFixed(2)),
              Number((Number(r.warehouse_amount) || 0).toFixed(2)),
              r.avg_transit_display || '—',
              Number(r.orders_count) || 0,
              `${r.fulfillment_rate}%`
            ]
          } else {
            return [
              ...dimVals,
              Number((Number(r.shipped_qty) || 0).toFixed(2)),
              Number((Number(r.arrived_qty) || 0).toFixed(2)),
              Number((Number(r.received_qty) || 0).toFixed(2)),
              Number((Number(r.warehouse_qty) || 0).toFixed(2)),
              r.avg_transit_display || '—',
              Number(r.orders_count) || 0,
              `${r.fulfillment_rate}%`
            ]
          }
        } else {
          return [
            ...dimVals,
            Number(r.shipped_qty) || 0,
            Number(r.arrived_qty) || 0,
            Number(r.received_qty) || 0,
            Number(r.warehouse_qty) || 0,
            r.avg_transit_display || '—',
            Number(r.orders_count) || 0,
            `${r.fulfillment_rate}%`
          ]
        }
      })

      // 补上末尾【全项目总计】
      const grandDimVals = activeDims.map((d, i) => i === 0 ? '【全项目总计】' : '—')
      const sum = supplierLedgerSummary.value
      if (isPipe) {
        if (showPipeAmountCalc.value) {
          sRows.push([
            ...grandDimVals,
            Number((Number(sum.total_shipped_qty) || 0).toFixed(2)),
            Number((Number(sum.total_shipped_amount) || 0).toFixed(2)),
            Number((Number(sum.total_arrived_qty) || 0).toFixed(2)),
            Number((Number(sum.total_arrived_amount) || 0).toFixed(2)),
            Number((Number(sum.total_received_qty) || 0).toFixed(2)),
            Number((Number(sum.total_received_amount) || 0).toFixed(2)),
            Number((Number(sum.total_warehouse_qty) || 0).toFixed(2)),
            Number((Number(sum.total_warehouse_amount) || 0).toFixed(2)),
            sum.overall_avg_transit || '—',
            Number(sum.total_orders_count) || 0,
            `${sum.overall_fulfillment_rate}%`
          ])
        } else {
          sRows.push([
            ...grandDimVals,
            Number((Number(sum.total_shipped_qty) || 0).toFixed(2)),
            Number((Number(sum.total_arrived_qty) || 0).toFixed(2)),
            Number((Number(sum.total_received_qty) || 0).toFixed(2)),
            Number((Number(sum.total_warehouse_qty) || 0).toFixed(2)),
            sum.overall_avg_transit || '—',
            Number(sum.total_orders_count) || 0,
            `${sum.overall_fulfillment_rate}%`
          ])
        }
      } else {
        sRows.push([
          ...grandDimVals,
          Number(sum.total_shipped_qty) || 0,
          Number(sum.total_arrived_qty) || 0,
          Number(sum.total_received_qty) || 0,
          Number(sum.total_warehouse_qty) || 0,
          sum.overall_avg_transit || '—',
          Number(sum.total_orders_count) || 0,
          `${sum.overall_fulfillment_rate}%`
        ])
      }

      const wsLedger = buildStyledWorksheet(sHeaders, sRows, [], sRows.length)
      XLSX.utils.book_append_sheet(wb, wsLedger, '供给方发货流转台账')
      defaultFilename = isPipe
        ? `供给方保温管发货流转台账_${filterStartDate.value}_${filterEndDate.value}.xlsx`
        : `供给方管件发货流转台账_${filterStartDate.value}_${filterEndDate.value}.xlsx`

    } else if (activeTab.value === 'directory') {
      // =======================================================================
      // 🏢 Tab 4: 责任主体与人员矩阵
      // =======================================================================
      if (directoryViewMode.value === 'by_section') {
        const headers = ['标段ID', '标段名称', '责任角色', '主体/单位/人名', '职务/职责', '联系电话']
        const dataRows = []
        sectionEntityMatrix.value.forEach(sec => {
          sec.suppliers.forEach(s => dataRows.push([sec.section_1_id, sec.section_1_name, '供货厂家', s.entity_name, `联系人: ${s.contact_name}`, s.contact_phone]))
          sec.site_managers.forEach(m => dataRows.push([sec.section_1_id, sec.section_1_name, '现场负责人', m.person_name, '标段主管', m.contact_phone]))
          sec.construction_units.forEach(c => dataRows.push([sec.section_1_id, sec.section_1_name, '施工单位', c.construction_unit_name, `项目经理: ${c.contact_name}`, c.contact_phone]))
          sec.warehouse_keepers.forEach(w => dataRows.push([sec.section_1_id, sec.section_1_name, '物资库管', w.person_name, '现场库管员', w.contact_phone]))
        })
        globalPersonnel.value.managers.forEach(gm => dataRows.push(['GLOBAL', '全网统筹', '集团总调度', gm.person_name, '现场总协调', gm.contact_phone]))
        globalPersonnel.value.suppliers.forEach(gs => dataRows.push(['GLOBAL', '全网统筹', '供给侧全局管理', gs.contact_name, `主体: ${gs.entity_name}`, gs.contact_phone]))
        globalPersonnel.value.keepers.forEach(gw => dataRows.push(['GLOBAL', '全网统筹', '物资总库管', gw.person_name, '总库管理', gw.contact_phone]))
        globalPersonnel.value.members.forEach(mem => dataRows.push(['GLOBAL', '全网统筹', '系统指挥观察', mem.username, mem.role_name, '集团专线']))

        const ws = buildStyledWorksheet(headers, dataRows)
        XLSX.utils.book_append_sheet(wb, ws, '标段责任主体矩阵')
        defaultFilename = '项目各标段责任主体与人员综合矩阵表.xlsx'
      } else {
        const headers = ['主体分类', '主体/标段/姓名', '负责人/职务', '联系电话', '管辖/供货范围', '归属单位/账号']
        const dataRows = [
          ...filteredSuppliers.value.map(s => ['供货厂家', s.entity_name, s.contact_name, s.contact_phone, (s.managed_sections && s.managed_sections.length > 0) ? s.managed_sections.join('、') : '暂未分配供应标段', `调度账号: ${s.accounts.join(', ')}`]),
          ...filteredSiteManagers.value.map(m => ['现场负责人', `${m.person_name} (负责人)`, m.contact_name, m.contact_phone, m.scope_desc, m.is_global ? '集团总指挥协调' : `管辖: ${m.scope_desc}`]),
          ...filteredDemandSections.value.map(d => ['施工单位', d.section_1_name, d.contact_name, d.contact_phone, d.section_1_name, `施工单位: ${d.construction_unit_name}`]),
          ...filteredWarehouseKeepers.value.map(w => ['物资库管', `${w.person_name} (库管)`, w.person_name, w.contact_phone, w.scope_desc, `系统账号: ${w.username}`]),
          ...filteredGlobalMembers.value.map(g => ['系统管理', g.username, g.contact_name, '集团专线', '全网全局透视', g.scope_desc]),
        ]
        const ws = buildStyledWorksheet(headers, dataRows)
        XLSX.utils.book_append_sheet(wb, ws, '主体类别速查表')
        defaultFilename = '项目责任主体与人员管辖矩阵表.xlsx'
      }
    }

    XLSX.writeFile(wb, defaultFilename)
  } catch (err) {
    console.error('导出 Excel 失败:', err)
    alert('导出 Excel 发生错误，请稍后重试。')
  } finally {
    exportLoading.value = false
  }
}

// -----------------------------------------------------------------------------
// 📥 导出当前弹窗中的穿透发运单明细
// -----------------------------------------------------------------------------

function exportCurrentOrderItemsExcel() {
  if (!selectedSupplierOrderRow.value || !selectedSupplierOrderRow.value.order_items) return
  const isPipe = subMaterialType.value === 'pipe'
  const row = selectedSupplierOrderRow.value
  const items = row.order_items

  const withCalc = isPipe && showPipeAmountCalc.value
  const headers = withCalc
    ? ['运单号/批次', '需求标段', '物料大类', '规格型号', '单价(元/米)', '发货日期', '车牌号', '司机姓名', '联系电话', '发货量(米)', '发货金额(元)', '确认到货量(米)', '到货金额(元)', '施工接收量(米)', '库管确认量(米)', '在途时长', '运单状态', '单价核算备注']
    : ['运单号/批次', '需求标段', '物料大类', '规格型号', '发货日期', '车牌号', '司机姓名', '联系电话', `发货量(${isPipe ? '米' : '件'})`, `确认到货量(${isPipe ? '米' : '件'})`, `施工接收量(${isPipe ? '米' : '件'})`, `库管确认量(${isPipe ? '米' : '件'})`, '在途时长', '运单状态']

  let sumShip = 0, sumArr = 0, sumRec = 0, sumWh = 0
  let sumShipAmt = 0, sumArrAmt = 0

  const dataRows = items.map(o => {
    const sQty = Number(o.shipped_qty) || 0
    const aQty = Number(o.arrived_qty) || 0
    const rQty = Number(o.received_qty) || 0
    const wQty = Number(o.warehouse_qty) || 0
    sumShip += sQty
    sumArr += aQty
    sumRec += rQty
    sumWh += wQty

    const statusText = o.status === 'completed' ? '已入库' : o.status === 'received' ? '已接收' : o.status === 'arrived' ? '已到货' : '在途中'

    if (withCalc) {
      const sAmt = Number(o.shipped_amount) || 0
      const aAmt = Number(o.arrived_amount) || 0
      sumShipAmt += sAmt
      sumArrAmt += aAmt
      const noteVal = o.price_note || '—'
      return [
        o.batch_no || '—',
        o.section_1_name || '—',
        '保温管',
        o.pipe_model_name || '—',
        o.unit_price != null ? Number(Number(o.unit_price).toFixed(2)) : '—',
        o.biz_date || '—',
        o.vehicle_no || '—',
        o.driver_name || '—',
        o.driver_phone || '—',
        Number(sQty.toFixed(2)),
        Number(sAmt.toFixed(2)),
        Number(aQty.toFixed(2)),
        Number(aAmt.toFixed(2)),
        Number(rQty.toFixed(2)),
        Number(wQty.toFixed(2)),
        o.transit_display || '—',
        statusText,
        noteVal
      ]
    }

    return [
      o.batch_no || '—',
      o.section_1_name || '—',
      isPipe ? '保温管' : (o.fitting_type || '预制管件'),
      isPipe ? (o.pipe_model_name || '—') : (o.model_spec || '—'),
      o.biz_date || '—',
      o.vehicle_no || '—',
      o.driver_name || '—',
      o.driver_phone || '—',
      isPipe ? Number(sQty.toFixed(2)) : sQty,
      isPipe ? Number(aQty.toFixed(2)) : aQty,
      isPipe ? Number(rQty.toFixed(2)) : rQty,
      isPipe ? Number(wQty.toFixed(2)) : wQty,
      o.transit_display || '—',
      statusText
    ]
  })

  // 本组汇总行
  if (withCalc) {
    dataRows.push([
      '【本组穿透汇总】',
      `共 ${items.length} 笔订单`,
      '—',
      '—',
      '—',
      '—',
      '—',
      '—',
      '—',
      Number(sumShip.toFixed(2)),
      Number(sumShipAmt.toFixed(2)),
      Number(sumArr.toFixed(2)),
      Number(sumArrAmt.toFixed(2)),
      Number(sumRec.toFixed(2)),
      Number(sumWh.toFixed(2)),
      row.avg_transit_display || '—',
      '—',
      '穿透批次汇总'
    ])
  } else {
    dataRows.push([
      '【本组穿透汇总】',
      `共 ${items.length} 笔订单`,
      '—',
      '—',
      '—',
      '—',
      '—',
      '—',
      isPipe ? Number(sumShip.toFixed(2)) : sumShip,
      isPipe ? Number(sumArr.toFixed(2)) : sumArr,
      isPipe ? Number(sumRec.toFixed(2)) : sumRec,
      isPipe ? Number(sumWh.toFixed(2)) : sumWh,
      row.avg_transit_display || '—',
      '—'
    ])
  }

  const ws = buildStyledWorksheet(headers, dataRows, [], dataRows.length)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '发运单穿透明细')

  const filename = `${row.supplier_name || '供给方'}_发运订单明细_${filterStartDate.value}_${filterEndDate.value}.xlsx`
  XLSX.writeFile(wb, filename)
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

.price-note-icon {
  display: inline-block;
  margin-left: 4px;
  cursor: help;
  font-size: 11px;
  opacity: 0.85;
  transition: transform 0.15s ease, opacity 0.15s ease;
  user-select: none;
}
.price-note-icon:hover {
  opacity: 1;
  transform: scale(1.2);
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

/* ========================================================================== */
/* 🏭 Tab 3: 供给方发货流转台账专属视觉微调 */
/* ========================================================================== */
.btn-order-drill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: #f0f9ff;
  color: #0284c7;
  border: 1px solid #bae6fd;
  border-radius: 4px;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-order-drill:hover {
  background: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
  box-shadow: 0 1px 4px rgba(2, 132, 199, 0.3);
}

/* 弹窗内部小 KPI 概览条 */
.modal-summary-banner {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  padding: 10px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.modal-sum-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: #ffffff;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.modal-sum-item .sum-lbl {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
}

.modal-sum-item .sum-val {
  font-size: 15px;
  font-weight: 800;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.modal-sum-item .sum-val small {
  font-size: 11px;
  font-weight: 600;
  margin-left: 2px;
}

.modal-data-table {
  font-size: 12.5px;
}

.modal-data-table th {
  padding: 8px 10px;
  font-size: 12px;
}

.modal-data-table td {
  padding: 7px 10px;
}

/* 运单状态徽章 */
.badge-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
}

.status-shipped {
  background: #e0f2fe;
  color: #0284c7;
  border: 1px solid #bae6fd;
}

.status-arrived {
  background: #dbeafe;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.status-received {
  background: #ede9fe;
  color: #6d28d9;
  border: 1px solid #ddd6fe;
}

.status-completed {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.modal-xl {
  max-width: 1100px;
  width: 95vw;
}

.modal-header-title-wrap {
  flex: 1;
}

.btn-modal-close-icon {
  background: none;
  border: none;
  color: #ffffff;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  opacity: 0.85;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.15s;
}

.btn-modal-close-icon:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.2);
}

.modal-table-container {
  max-height: 52vh;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

/* 💰 采购价格专属紧凑筛选器与徽章样式 */
.price-filters-inline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-select-item, .filter-search-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  position: relative;
}

.filter-item-label {
  font-size: 11.5px;
  font-weight: 700;
  color: #475569;
  white-space: nowrap;
}

.form-select-compact {
  height: 28px;
  padding: 2px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background-color: #ffffff;
  color: #1e293b;
  font-size: 12px;
  font-weight: 600;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.form-select-compact:focus {
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.form-input-compact {
  height: 28px;
  width: 170px;
  padding: 2px 22px 2px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background-color: #ffffff;
  color: #1e293b;
  font-size: 12px;
  outline: none;
  transition: border-color 0.15s, width 0.2s;
}

.form-input-compact:focus {
  width: 200px;
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.btn-clear-kw {
  position: absolute;
  right: 6px;
  background: none;
  border: none;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  line-height: 1;
  padding: 0;
}

.btn-clear-kw:hover {
  color: #ef4444;
}

.btn-reset-price-filter {
  height: 28px;
  padding: 0 10px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  color: #475569;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-reset-price-filter:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.badge-tag {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.badge-pipe {
  background: #fff7ed;
  color: #c2410c;
  border: 1px solid #fed7aa;
}

.badge-fitting {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.sub-pill-lock-tag {
  font-size: 11px;
  margin-left: 3px;
  opacity: 0.85;
}

.btn-lock-price {
  background: #fef2f2 !important;
  color: #b91c1c !important;
  border-color: #fecaca !important;
}

.btn-lock-price:hover {
  background: #fee2e2 !important;
  color: #991b1b !important;
  border-color: #fca5a5 !important;
}

/* 🔐 采购价格未解锁受控保护卡片 */
.price-locked-view {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 20px;
}

.price-locked-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  max-width: 420px;
}

.price-locked-icon {
  font-size: 48px;
  margin-bottom: 12px;
  animation: pulse-lock 2s infinite ease-in-out;
}

@keyframes pulse-lock {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}

.price-locked-title {
  font-size: 18px;
  font-weight: 800;
  color: #1e293b;
  margin: 0 0 8px 0;
}

.price-locked-desc {
  font-size: 13.5px;
  color: #64748b;
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.btn-unlock-action {
  padding: 9px 24px;
  font-size: 14px;
  font-weight: 700;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-unlock-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(2, 132, 199, 0.35);
}

/* 🔐 访问码验证弹窗专用精致样式 */
.price-auth-modal {
  max-width: 440px !important;
  width: 92%;
  border-radius: 16px;
  box-shadow: 0 25px 60px -15px rgba(15, 23, 42, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.1);
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.8);
  animation: modalPop 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalPop {
  0% { transform: scale(0.95) translateY(8px); opacity: 0; }
  100% { transform: scale(1) translateY(0); opacity: 1; }
}

.price-auth-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, #b45309 0%, #d97706 50%, #f59e0b 100%);
  color: #ffffff;
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
}

.price-auth-header-icon-wrap {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.price-auth-icon {
  font-size: 22px;
}

.price-auth-header .modal-header-title-wrap {
  flex: 1;
  min-width: 0;
}

.price-auth-header .modal-title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.2px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}

.price-auth-header .modal-sub {
  margin: 3px 0 0 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.auth-modal-form {
  display: flex;
  flex-direction: column;
  margin: 0;
}

.auth-modal-body {
  padding: 22px 24px 18px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #ffffff;
}

/* 安全说明小卡片 */
.auth-notice-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 12px 14px;
}

.notice-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}

.notice-content {
  flex: 1;
}

.notice-content strong {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #92400e;
  margin-bottom: 2px;
}

.notice-content p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #b45309;
}

/* 输入框区域 */
.auth-field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-input-label {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.auth-input-wrapper {
  position: relative;
  width: 100%;
  display: flex;
  align-items: center;
}

.auth-input-icon {
  position: absolute;
  left: 14px;
  font-size: 16px;
  color: #94a3b8;
  pointer-events: none;
}

.auth-input-field {
  width: 100%;
  height: 48px;
  padding: 0 16px 0 42px;
  font-size: 20px;
  letter-spacing: 8px;
  text-align: left;
  font-weight: 800;
  color: #0f172a;
  background: #f8fafc;
  border: 2px solid #cbd5e1;
  border-radius: 10px;
  outline: none;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-sizing: border-box;
}

.auth-input-field:focus {
  background: #ffffff;
  border-color: #d97706;
  box-shadow: 0 0 0 4px rgba(217, 119, 6, 0.15);
}

.auth-input-field::placeholder {
  letter-spacing: 4px;
  color: #94a3b8;
  font-weight: 500;
}

/* 错误提示 */
.auth-error-tip {
  font-size: 12.5px;
  font-weight: 600;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 8px 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  animation: authShake 0.35s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}

@keyframes authShake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-3px, 0, 0); }
  40%, 60% { transform: translate3d(3px, 0, 0); }
}

/* 底部操作条 */
.auth-modal-actions {
  padding: 14px 24px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
}

.modal-cancel-btn {
  height: 38px;
  padding: 0 16px;
  font-size: 13.5px;
  font-weight: 600;
  border-radius: 8px;
}

.btn-unlock-confirm {
  height: 38px;
  padding: 0 20px;
  font-size: 13.5px;
  font-weight: 700;
  border-radius: 8px;
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
  color: #ffffff;
  border: none;
  box-shadow: 0 2px 8px rgba(217, 119, 6, 0.35);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.btn-unlock-confirm:hover:not(:disabled) {
  background: linear-gradient(135deg, #b45309 0%, #92400e 100%);
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.45);
  transform: translateY(-1px);
}

.btn-unlock-confirm:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(217, 119, 6, 0.3);
}

.btn-unlock-confirm:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
  background: #94a3b8;
}

/* 💰 Tab 3 供给方台账保温管金额核算联动选框与样式 */
.pipe-calc-price-toggle-wrap {
  display: flex;
  align-items: center;
}

.calc-price-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 20px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s ease;
}

.calc-price-label:hover {
  background: #dcfce7;
  border-color: #86efac;
  box-shadow: 0 2px 6px rgba(34, 197, 94, 0.15);
}

.calc-price-checkbox {
  width: 15px;
  height: 15px;
  accent-color: #16a34a;
  cursor: pointer;
}

.calc-price-text {
  font-size: 12.5px;
  font-weight: 700;
  color: #15803d;
}

.calc-active-tag {
  font-size: 11px;
  font-weight: 800;
  color: #ffffff;
  background: #16a34a;
  padding: 1px 6px;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(22, 163, 74, 0.3);
}

.kpi-amount-sub {
  font-size: 12px;
  margin-top: 2px;
  opacity: 0.95;
}
</style>

