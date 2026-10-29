<template>
  <div class="dynamic-plan-view">
    <AppHeader />
    <main class="dynamic-plan-main">
      <div class="top-nav-bar">
        <Breadcrumbs :items="breadcrumbItems" />
        <div class="header-actions">
          <button class="btn ghost-btn" type="button" :disabled="loading" @click="fetchData">
            <span class="btn-icon">🔄</span>
            <span>刷新数据</span>
          </button>
          <button class="btn export-btn" type="button" :disabled="loading || !metricsList.length" @click="exportToExcel">
            <span class="btn-icon">📥</span>
            <span>导出当前计划表</span>
          </button>
        </div>
      </div>

      <!-- 页面主标题卡片 -->
      <section class="card banner-card">
        <div class="banner-content">
          <div class="banner-title-row">
            <span class="badge-tag">2026–2027 供暖期</span>
            <h2>动态计划指标图谱</h2>
            <span class="status-indicator live">● 数据库已同步</span>
          </div>
          <p class="banner-desc">
            全维度展示各主体月度计划基准（2026-10 至 2027-04），支持按单位口径、连续月度区间筛选，呈现供热、燃料、电水及单耗多维趋势与分布规律。
          </p>
        </div>
      </section>

      <!-- 筛选与控制栏 -->
      <section class="card filter-card">
        <!-- 维度一：单位口径选择 -->
        <div class="filter-group unit-group">
          <div class="filter-label">
            <span class="label-icon">🏢</span>
            <span>单位口径：</span>
          </div>
          <div class="unit-pills-wrapper">
            <button
              v-for="unit in unitOptions"
              :key="unit.company"
              type="button"
              :class="['unit-pill', { active: currentCompany === unit.company }]"
              @click="handleUnitChange(unit.company)"
            >
              <span class="pill-title">{{ unit.company_cn }}</span>
            </button>
          </div>
        </div>

        <!-- 维度二：连续月份区间选择与快捷预设 -->
        <div class="filter-group month-group">
          <div class="filter-label">
            <span class="label-icon">📅</span>
            <span>月份区间：</span>
          </div>
          <div class="month-controls">
            <div class="range-selects">
              <select v-model="startMonth" class="form-select" @change="handleMonthChange">
                <option v-for="m in availableMonths" :key="'start_' + m" :value="m">{{ formatMonthCn(m) }}</option>
              </select>
              <span class="range-separator">至</span>
              <select v-model="endMonth" class="form-select" @change="handleMonthChange">
                <option v-for="m in availableMonths" :key="'end_' + m" :value="m">{{ formatMonthCn(m) }}</option>
              </select>
            </div>

            <!-- 快捷预设按钮 -->
            <div class="preset-buttons">
              <button
                v-for="p in presetRanges"
                :key="p.key"
                type="button"
                :class="['preset-btn', { active: isPresetActive(p) }]"
                @click="applyPreset(p)"
              >
                {{ p.label }}
              </button>
            </div>

            <!-- 气温预报同步按钮 -->
            <button
              type="button"
              class="preset-btn btn-import-weather"
              :class="{ 'is-loading': weatherImporting }"
              :disabled="weatherImporting"
              title="从 Open-Meteo 集合预报（31个member逐小时算术平均）拉取未来 35 天气温并入库（标记为 far）"
              @click="handleImportEnsembleWeather"
            >
              <span class="weather-btn-icon">{{ weatherImporting ? '⏳' : '⛅' }}</span>
              <span>{{ weatherImporting ? '正在拉取预报...' : '导入35天预报' }}</span>
            </button>

            <!-- 同步状态提示 -->
            <span v-if="weatherSyncStatus" :class="['weather-status-badge', weatherSyncStatus.success ? 'success' : 'error']">
              {{ weatherSyncStatus.message }}
            </span>
          </div>
        </div>

        <!-- 维度三：指标下拉复选列表 -->
        <div class="filter-group metric-select-group" ref="metricDropdownRef">
          <div class="filter-label">
            <span class="label-icon">📊</span>
            <span>选择指标：</span>
          </div>
          <div class="metric-multiselect-container">
            <div
              class="multiselect-trigger"
              :class="{ 'is-open': isMetricDropdownOpen }"
              @click="toggleMetricDropdown"
            >
              <div class="trigger-text">
                <span v-if="isAllMetricsSelected" class="select-summary">全部指标 (已全选 {{ metricsList.length }} 项)</span>
                <span v-else-if="selectedMetricKeys.length === 0" class="select-summary placeholder">未选择指标 (点击展开勾选)</span>
                <span v-else class="select-summary">已选 {{ selectedMetricKeys.length }} / {{ metricsList.length }} 项指标</span>
              </div>
              <span class="dropdown-arrow" :class="{ 'is-open': isMetricDropdownOpen }">▼</span>
            </div>

            <!-- 下拉展开面板 -->
            <div v-show="isMetricDropdownOpen" class="multiselect-dropdown-panel" @click.stop>
              <!-- 快捷操作栏 -->
              <div class="dropdown-actions-bar">
                <div class="action-btn-group">
                  <button type="button" class="action-link-btn" @click="selectAllMetrics">全选</button>
                  <span class="action-divider">|</span>
                  <button type="button" class="action-link-btn" @click="clearAllMetrics">清空</button>
                  <span class="action-divider">|</span>
                  <button type="button" class="action-link-btn" @click="invertMetricsSelection">反选</button>
                </div>
                <span class="selected-counter">已勾选 {{ selectedMetricKeys.length }} 项</span>
              </div>

              <!-- 指标复选滚动列表 -->
              <div class="dropdown-list-scroll">
                <label
                  v-for="m in metricsList"
                  :key="m.item"
                  class="dropdown-checkbox-item"
                  :class="{ 'is-checked': selectedMetricKeys.includes(m.item) }"
                >
                  <input
                    type="checkbox"
                    :value="m.item"
                    v-model="selectedMetricKeys"
                    class="item-checkbox"
                  />
                  <span class="item-name">{{ m.item_cn }}</span>
                  <span v-if="m.unit" class="item-unit">({{ m.unit }})</span>
                </label>
              </div>
            </div>
          </div>

          <!-- 恢复全选快捷按钮 -->
          <button
            v-if="!isAllMetricsSelected"
            type="button"
            class="btn-reset-metrics"
            title="一键恢复展示全部指标"
            @click="selectAllMetrics"
          >
            ↺ 恢复全选
          </button>
        </div>
      </section>

      <!-- 核心指标统计卡片 (KPI Summary Cards) -->
      <section v-if="!loading" class="kpi-grid">
        <div class="kpi-card heat-kpi">
          <div class="kpi-icon">🔥</div>
          <div class="kpi-info">
            <div class="kpi-label">供热量计划总量</div>
            <div class="kpi-value-row">
              <span class="kpi-value">{{ formatNumber(summaryCards.heat_supply_total) }}</span>
              <span class="kpi-unit">GJ</span>
            </div>
            <div class="kpi-meta">
              <span>月均: {{ formatNumber(getMetricAverage('amount_heat_supply')) }} GJ</span>
              <span v-if="getMetricPeakMonth('amount_heat_supply')" class="kpi-peak">
                峰值: {{ getMetricPeakMonth('amount_heat_supply') }}
              </span>
            </div>
          </div>
        </div>

        <div class="kpi-card coal-kpi">
          <div class="kpi-icon">⚖️</div>
          <div class="kpi-info">
            <div class="kpi-label">标煤耗量总量</div>
            <div class="kpi-value-row">
              <span class="kpi-value">{{ formatNumber(summaryCards.std_coal_total) }}</span>
              <span class="kpi-unit">吨</span>
            </div>
            <div class="kpi-meta">
              <span>月均: {{ formatNumber(getMetricAverage('consumption_std_coal')) }} 吨</span>
              <span v-if="getMetricPeakMonth('consumption_std_coal')" class="kpi-peak">
                峰值: {{ getMetricPeakMonth('consumption_std_coal') }}
              </span>
            </div>
          </div>
        </div>

        <div class="kpi-card raw-coal-kpi">
          <div class="kpi-icon">⛰️</div>
          <div class="kpi-info">
            <div class="kpi-label">原煤耗量总量</div>
            <div class="kpi-value-row">
              <span class="kpi-value">{{ formatNumber(summaryCards.raw_coal_total) }}</span>
              <span class="kpi-unit">吨</span>
            </div>
            <div class="kpi-meta">
              <span>月均: {{ formatNumber(getMetricAverage('consumption_amount_raw_coal')) }} 吨</span>
              <span class="kpi-extra">折标比: {{ getCoalRatioText() }}</span>
            </div>
          </div>
        </div>

        <div class="kpi-card power-kpi">
          <div class="kpi-icon">⚡</div>
          <div class="kpi-info">
            <div class="kpi-label">{{ summaryCards.power_generation_total > 0 ? '发电量计划总量' : '外购电量计划总量' }}</div>
            <div class="kpi-value-row">
              <span class="kpi-value">
                {{ formatNumber(summaryCards.power_generation_total > 0 ? summaryCards.power_generation_total : summaryCards.purchased_power_total) }}
              </span>
              <span class="kpi-unit">万kWh</span>
            </div>
            <div class="kpi-meta">
              <span v-if="summaryCards.power_generation_total > 0 || summaryCards.power_sales_total > 0">
                售电量: {{ formatNumber(summaryCards.power_sales_total || getMetricTotal('amount_power_sales')) }} 万kWh
              </span>
              <span v-else>月均电量: {{ formatNumber(getMetricAverage('consumption_purchased_power')) }} 万kWh</span>
            </div>
          </div>
        </div>

        <div class="kpi-card water-kpi">
          <div class="kpi-icon">💧</div>
          <div class="kpi-info">
            <div class="kpi-label">耗水计划总量</div>
            <div class="kpi-value-row">
              <span class="kpi-value">{{ formatNumber(summaryCards.water_total) }}</span>
              <span class="kpi-unit">吨</span>
            </div>
            <div class="kpi-meta">
              <span>月均耗水: {{ formatNumber(getMetricAverage('consumption_water')) }} 吨</span>
            </div>
          </div>
        </div>

        <div class="kpi-card efficiency-kpi">
          <div class="kpi-icon">📐</div>
          <div class="kpi-info">
            <div class="kpi-label">供暖综合单耗 (累计)</div>
            <div class="kpi-value-row">
              <span class="kpi-value">{{ formatNumber(summaryCards.heat_rate_total || getMetricTotal('rate_heat_per_10k_m2')) }}</span>
              <span class="kpi-unit">GJ/万m²</span>
            </div>
            <div class="kpi-meta">
              <span>水单耗: {{ formatNumber(summaryCards.water_rate_total || getMetricTotal('rate_water_per_10k_m2')) }} 吨/万m²</span>
              <span>电单耗: {{ formatNumber(summaryCards.power_rate_total || getMetricTotal('rate_power_per_10k_m2')) }} kWh/万m²</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 图形化展示区 -->
      <section class="card chart-section">
        <header class="chart-header">
          <div class="chart-tabs">
            <button
              v-for="tab in chartTabs"
              :key="tab.key"
              type="button"
              :class="['chart-tab-btn', { active: activeChartTab === tab.key }]"
              @click="switchChartTab(tab.key)"
            >
              <span>{{ tab.icon }}</span>
              <span>{{ tab.label }}</span>
            </button>
          </div>
          <div class="chart-actions">
            <!-- 动态分解独立高质感开关 -->
            <label class="decomp-toggle-pill" :class="{ 'is-active': isDynamicDecomposeEnabled }" title="基于目标月份逐日气温HDD20与k值模型，将月度计划自适应分解至每日">
              <input
                type="checkbox"
                v-model="isDynamicDecomposeEnabled"
                class="decomp-toggle-input"
                @change="handleDynamicDecomposeToggle"
              />
              <span class="toggle-dot"></span>
              <span class="toggle-text">⚡ 动态分解</span>
            </label>

            <!-- 图表专属二次指标筛选下拉器（默认相同，可下拉取消勾选） -->
            <div ref="chartMetricDropdownRef" class="chart-multiselect-dropdown">
              <button
                type="button"
                class="chart-dropdown-trigger"
                :class="{ 'is-active': isChartMetricDropdownOpen }"
                @click="toggleChartMetricDropdown"
                title="自定义图表中呈现的指标曲线"
              >
                <span class="chart-trigger-icon">📉</span>
                <span class="chart-trigger-text">
                  图表呈现: <b>{{ chartSelectedMetricKeys.length }}</b> / {{ filteredMetrics.length }} 项
                </span>
                <span class="dropdown-arrow" :class="{ 'is-open': isChartMetricDropdownOpen }">▼</span>
              </button>

              <div v-show="isChartMetricDropdownOpen" class="chart-dropdown-panel" @click.stop>
                <div class="chart-dropdown-header">
                  <span class="chart-dropdown-title">二次筛选指标</span>
                  <div class="action-btn-group">
                    <button type="button" class="action-link-btn" title="全选当前列表全部指标" @click="selectAllChartMetrics">全选</button>
                    <span class="action-divider">|</span>
                    <button type="button" class="action-link-btn" title="清空全部图表指标" @click="clearAllChartMetrics">清空</button>
                  </div>
                </div>

                <div class="chart-dropdown-scroll">
                  <label
                    v-for="m in filteredMetrics"
                    :key="'chart_' + m.item"
                    class="dropdown-checkbox-item"
                    :class="{ 'is-checked': chartSelectedMetricKeys.includes(m.item) }"
                  >
                    <input
                      type="checkbox"
                      :value="m.item"
                      v-model="chartSelectedMetricKeys"
                      class="item-checkbox"
                      @change="isChartCustomized = true"
                    />
                    <span class="item-name">{{ m.item_cn }}</span>
                    <span v-if="m.unit" class="item-unit">({{ m.unit }})</span>
                  </label>
                  <div v-if="!filteredMetrics.length" class="dropdown-empty-tip">
                    上方表格未勾选任何指标
                  </div>
                </div>
              </div>
            </div>

            <!-- 聚焦高亮标签 -->
            <span
              v-if="focusedMetricKey"
              class="focused-metric-tag"
              title="点击取消聚焦高亮"
              @click="focusedMetricKey = ''; renderChart()"
            >
              🎯 聚焦: {{ getFocusedMetricName() }} ✕
            </span>

            <span v-if="!isDynamicDecomposeEnabled" class="chart-range-tag">
              {{ currentUnitLabel }} ｜ {{ formatMonthCn(startMonth) }} ~ {{ formatMonthCn(endMonth) }}
            </span>
          </div>
        </header>

        <!-- 动态分解专属控制横栏 (仅开启动态分解时展示，排版整洁大方，绝不拥挤换行) -->
        <div v-if="isDynamicDecomposeEnabled" class="decomp-sub-toolbar">
          <div class="decomp-sub-left">
            <span v-if="dynamicDecompData?.is_rollup" class="sub-label">总量：子口径逐日汇总；单耗：本口径分解</span>
            <span class="sub-label">📅 分解计划月份：</span>
            <select
              v-model="dynamicTargetMonth"
              class="decomp-month-select"
              @change="loadDynamicDecompositionData"
              title="选择动态日分解的目标计划月份"
            >
              <option v-for="m in displayedMonths" :key="'decomp_' + m" :value="m">
                {{ formatMonthCn(m) }}
              </option>
            </select>

            <template v-if="dynamicDecompData?.has_full_month">
              <span class="decomp-info-pill">
                🌡️ 全月日均温: <b>{{ dynamicDecompData.avg_temperature }} ℃</b>
              </span>
              <span class="decomp-info-pill">
                🔥 月平均 HDD20: <b>{{ dynamicDecompData.avg_hdd20 }}</b>
              </span>
              <span class="decomp-badge-audit">
                ✓ 逐日计划加总与分解基准一致
              </span>
            </template>
          </div>

          <div class="decomp-sub-right">
            <!-- 平均气温曲线显隐切换胶囊 -->
            <label
              v-if="dynamicDecompData?.has_full_month"
              class="decomp-temp-pill"
              :class="{ 'is-active': showDecompTemperature }"
              title="开启或关闭每日平均气温(℃)参考曲线"
            >
              <input
                type="checkbox"
                v-model="showDecompTemperature"
                class="decomp-temp-checkbox"
                @change="renderChart"
              />
              <span class="temp-indicator-dot"></span>
              <span class="temp-label">🌡️ 平均气温曲线</span>
            </label>

            <!-- 动态分解算法与 k 值模型开关按钮 -->
            <button
              type="button"
              class="btn-toggle-decomp-algorithm"
              :class="{ active: showDecompAlgorithmPanel }"
              @click="showDecompAlgorithmPanel = !showDecompAlgorithmPanel"
              title="展开/收起动态分解数学算法原理与各指标 k 值模型"
            >
              {{ showDecompAlgorithmPanel ? '📐 收起算法与 k 值' : '📐 查看算法与 k 值' }}
            </button>

            <button
              type="button"
              class="btn-toggle-decomp-table"
              :class="{ active: showDecompDetailTable }"
              @click="showDecompDetailTable = !showDecompDetailTable"
              title="展开/收起全月逐日分解明细核对表"
            >
              {{ showDecompDetailTable ? '📋 收起 30 天逐日明细表' : '📋 查看 30 天逐日明细表' }}
            </button>
          </div>
        </div>

        <!-- 动态分解算法原理与各指标 k 值模型展示面板 -->
        <div v-if="isDynamicDecomposeEnabled && showDecompAlgorithmPanel" class="decomp-algorithm-panel">
          <div class="panel-header">
            <div class="panel-title-wrap">
              <span class="panel-badge-icon">📐</span>
              <h4 class="panel-heading">动态分解算法原理与各指标气温敏感度 k 值模型</h4>
              <span class="panel-context-tag">
                🏢 {{ currentUnitLabel }} ｜ 📅 {{ formatMonthCn(dynamicTargetMonth) }}
              </span>
            </div>
            <button
              type="button"
              class="btn-close-panel"
              title="收起算法与 k 值面板"
              @click="showDecompAlgorithmPanel = false"
            >
              ✕ 收起
            </button>
          </div>

          <!-- 管理员操作反馈提示条 -->
          <div v-if="paramFeedback" :class="['admin-param-alert', paramFeedback.type]">
            <span class="alert-icon">{{ paramFeedback.type === 'success' ? '✅' : paramFeedback.type === 'info' ? 'ℹ️' : '⚠️' }}</span>
            <span class="alert-text">{{ paramFeedback.message }}</span>
          </div>

          <div class="panel-body-grid">
            <!-- 左侧：算法数学公式与逻辑推演 -->
            <div class="algo-formula-col">
              <div class="algo-sub-title">
                <span class="sub-step-num">∑</span>
                <span>HDD20 采暖度日与日计划分解模型原理</span>
              </div>
              <div class="formula-cards-list">
                <div class="formula-card">
                  <div class="formula-card-header">
                    <span class="card-step-badge">1. 供热度日 (HDD20)</span>
                    <span class="card-tag">室外负荷驱动</span>
                  </div>
                  <div class="formula-math-box">
                    <code>HDD20<sub>d</sub> = max(20 - T<sub>d</sub>, 0)</code>
                  </div>
                  <p class="formula-card-desc">
                    以 <b>20℃</b> 为采暖平衡室外基准气温，<code>T<sub>d</sub></code> 为当日平均气温。当室外均温低于 20℃ 时产生供热负荷需求，温度越低度日越大。
                  </p>
                </div>

                <div class="formula-card">
                  <div class="formula-card-header">
                    <span class="card-step-badge">2. 日敏感度权重 (W<sub>d</sub>)</span>
                    <span class="card-tag">k 参数弹性调制</span>
                  </div>
                  <div class="formula-math-box">
                    <code>W<sub>d</sub> = max(0, 1 + (k × m) × (HDD20<sub>d</sub> - avg_HDD20))</code>
                  </div>
                  <p class="formula-card-desc">
                    <code>avg_HDD20</code> 为全月平均度日；<code>k</code> 为基准敏感度参数；<code>m</code> 为人工缩放系数（默认 1.0）。
                    实际生效系数 <code>k<sub>eff</sub> = k × m</code>。当 <code>k<sub>eff</sub> > 0</code> 时负荷随气温偏冷上浮、偏暖下浮；若无模型或为 0 则权重恒为 <code>1.0</code>（日均摊水平直线）。
                  </p>
                </div>

                <div class="formula-card">
                  <div class="formula-card-header">
                    <span class="card-step-badge">3. 全月守恒日分解计划 (P<sub>d</sub>)</span>
                    <span class="card-tag">总量绝对守恒</span>
                  </div>
                  <div class="formula-math-box">
                    <code>P<sub>d</sub> = P<sub>month</sub> × (W<sub>d</sub> / &sum;W<sub>i</sub>)</code>
                  </div>
                  <p class="formula-card-desc">
                    按权重归一化分解月度计划总量 <code>P<sub>month</sub></code>，并实施分厘平差调整，确保全月各日分解合计严格守恒等于月计划总量。
                  </p>
                </div>
              </div>
            </div>

            <!-- 右侧：当前口径当前月份各指标 k 值参数矩阵表 -->
            <div class="algo-k-col">
              <div class="algo-sub-title">
                <div class="title-with-count">
                  <span class="sub-step-num">k</span>
                  <span>{{ currentUnitLabel }} ｜ 各指标 k 值字典 (含 m 缩放)</span>
                  <span v-if="isGlobalAdmin" class="admin-role-badge" title="当前登录为 Global_admin，可直接编辑单元格输入数值并保存生效">
                    🔑 管理员可编辑
                  </span>
                </div>
                <div class="algo-k-header-actions">
                  <span v-if="decompositionMetricsWithK.length" class="k-count-badge">
                    共 {{ decompositionMetricsWithK.length }} 项指标（{{ decompositionMetricsWithK.filter(m => m.has_k).length }} 项受气温驱动）
                  </span>
                  <template v-if="isGlobalAdmin && modifiedParamsCount > 0">
                    <button
                      type="button"
                      class="btn-admin-save-all"
                      :disabled="savingParams"
                      @click="saveAllModifiedParams"
                      title="保存全部已修改的 m 缩放系数"
                    >
                      {{ savingParams ? '⏳ 保存中...' : `💾 保存修改 (${modifiedParamsCount})` }}
                    </button>
                    <button
                      type="button"
                      class="btn-admin-reset-all"
                      :disabled="savingParams"
                      @click="resetParamEdits"
                      title="撤销未保存的改动"
                    >
                      ↩️ 撤销
                    </button>
                  </template>
                </div>
              </div>

              <div class="k-table-scroll-wrap">
                <table class="k-dictionary-table">
                  <thead>
                    <tr>
                      <th class="th-k-item">指标名称</th>
                      <th class="th-k-unit text-center">单位</th>
                      <th class="th-k-val text-right">基准 k 值</th>
                      <th class="th-m-val text-center">
                        m 缩放系数
                        <small v-if="isGlobalAdmin" class="th-admin-tip">(点击输入)</small>
                      </th>
                      <th class="th-k-type text-center">模型机制</th>
                      <th class="th-k-plan text-right">月计划总量</th>
                      <th class="th-k-action text-center">
                        {{ isGlobalAdmin ? '操作 / 聚焦' : '图表聚焦' }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="m in decompositionMetricsWithK"
                      :key="'k_tbl_' + m.item"
                      :class="{
                        'row-focused': focusedMetricKey === m.item,
                        'row-modified': isGlobalAdmin && isParamRowModified(m.item)
                      }"
                    >
                      <td class="td-k-item">
                        <i class="color-dot" :style="{ backgroundColor: getMetricColor(m.item) }"></i>
                        <span class="item-name font-bold">{{ m.item_cn }}</span>
                        <span v-if="isGlobalAdmin && isParamRowModified(m.item)" class="modified-dot" title="存在未保存的 m 缩放系数改动">●</span>
                      </td>
                      <td class="td-k-unit text-center text-muted">{{ m.unit || '—' }}</td>
                      <td class="td-k-val text-right font-mono">
                        <!-- 基准 k 值保持只读 -->
                        <span v-if="m.aggregation_method === 'sum_children'">子口径参数</span>
                        <span v-else-if="m.has_k" class="k-badge-num active" :title="'基准 k 值: ' + m.k_value">
                          {{ Number(m.k_value).toFixed(6) }}
                        </span>
                        <span v-else class="k-badge-num zero" title="未配置 k 值模型，视作 0 等额均摊">
                          0.000000
                        </span>
                      </td>
                      <td class="td-m-val text-center font-mono">
                        <!-- 管理员在线输入 m 缩放系数 -->
                        <template v-if="m.aggregation_method === 'sum_children'">—</template>
                        <template v-else-if="isGlobalAdmin && editingParams[m.item]">
                          <input
                            type="number"
                            step="0.05"
                            min="0"
                            class="admin-inline-input m-input"
                            :class="{ modified: Math.abs(Number(editingParams[m.item].m_value !== undefined ? editingParams[m.item].m_value : 1.0) - Number(editingParams[m.item].origin_m !== undefined ? editingParams[m.item].origin_m : 1.0)) > 1e-5 }"
                            v-model.number="editingParams[m.item].m_value"
                            title="设定 m 缩放系数（默认 1.0）"
                            placeholder="1.0000"
                          />
                        </template>
                        <!-- 非管理员只读展示 -->
                        <template v-else>
                          <span
                            class="m-val-badge"
                            :class="{ modified: Number(m.m_value || 1.0) !== 1.0 }"
                            :title="'m 缩放系数: ' + (m.m_value !== undefined ? m.m_value : 1.0) + (Number(m.m_value || 1.0) !== 1.0 ? ' (生效 k=' + Number(m.effective_k).toFixed(6) + ')' : '')"
                          >
                            {{ Number(m.m_value !== undefined ? m.m_value : 1.0).toFixed(4) }}
                          </span>
                        </template>
                      </td>
                      <td class="td-k-type text-center">
                        <span v-if="m.aggregation_method === 'sum_children'">子口径逐日汇总</span>
                        <span v-else-if="m.has_k" class="k-type-pill temp-driven">🔥 气温驱动</span>
                        <span v-else class="k-type-pill baseline">➖ 基线均摊</span>
                      </td>
                      <td class="td-k-plan text-right font-mono font-bold">
                        {{ formatNumber(m.month_plan) }}
                      </td>
                      <td class="td-k-action text-center">
                        <div class="k-row-actions">
                          <button
                            type="button"
                            class="btn-k-focus"
                            :class="{ active: focusedMetricKey === m.item }"
                            title="在图表中高亮聚焦该指标走势"
                            @click="focusMetric(m)"
                          >
                            {{ focusedMetricKey === m.item ? '已聚焦' : '🎯 聚焦' }}
                          </button>
                          <button
                            v-if="isGlobalAdmin && isParamRowModified(m.item)"
                            type="button"
                            class="btn-k-save-single"
                            :disabled="savingParams"
                            title="保存当前指标设置"
                            @click="saveSingleParam(m)"
                          >
                            💾
                          </button>
                        </div>
                      </td>
                    </tr>
                    <tr v-if="!decompositionMetricsWithK.length">
                      <td colspan="7" class="td-k-empty">
                        {{ dynamicDecompLoading ? '正在加载当前口径 k 值模型与计划数据…' : '暂无当前月份的指标 k 值数据' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- 双纵轴/多纵轴对应指引条 (恢复左右轴高质感标签徽标与指标药丸卡片) -->
        <div v-if="chartAxisMappingInfo.showBanner" class="axis-mapping-banner">
          <!-- 左轴对应指标组 -->
          <div class="axis-indicator-group axis-left-group">
            <span class="axis-badge axis-left-badge">左纵轴 ({{ chartAxisMappingInfo.leftUnit }})</span>
            <div class="axis-metric-tags">
              <span
                v-for="m in chartAxisMappingInfo.leftMetrics"
                :key="'axis_l_' + m.item"
                class="axis-metric-pill left-metric"
                :class="{ 'is-focused': focusedMetricKey === m.item }"
                title="点击聚焦高亮该指标（对应左纵轴刻度）"
                @click="focusMetric(m)"
              >
                <i class="color-dot" :style="{ backgroundColor: getMetricColor(m.item) }"></i>
                <span class="metric-text">{{ m.item_cn }}</span>
              </span>
            </div>
          </div>

          <!-- 右轴对应指标组（支持多个右轴单位或气温曲线依次排布） -->
          <div class="axis-right-wrapper">
            <div
              v-for="group in chartAxisMappingInfo.rightGroups"
              :key="'axis_r_grp_' + group.unit"
              class="axis-indicator-group axis-right-group"
            >
              <span class="axis-badge axis-right-badge">右纵轴 ({{ group.unit }})</span>
              <div class="axis-metric-tags">
                <span
                  v-for="m in group.metrics"
                  :key="'axis_r_' + m.item"
                  class="axis-metric-pill right-metric"
                  :class="{ 'is-focused': focusedMetricKey === m.item }"
                  title="点击聚焦高亮该指标（对应右纵轴刻度）"
                  @click="focusMetric(m)"
                >
                  <i class="color-dot" :style="{ backgroundColor: getMetricColor(m.item) }"></i>
                  <span class="metric-text">{{ m.item_cn }}</span>
                </span>
              </div>
            </div>

            <!-- 动态分解模式下包含气温曲线时的右轴指引 -->
            <div v-if="chartAxisMappingInfo.hasTempRightAxis" class="axis-indicator-group axis-right-group">
              <span class="axis-badge axis-right-badge axis-temp-badge">右纵轴 (℃)</span>
              <div class="axis-metric-tags">
                <span class="axis-metric-pill right-metric axis-temp-pill" title="全月逐日平均气温（对应右纵轴刻度）">
                  <i class="color-dot" style="background-color: #0284c7;"></i>
                  <span class="metric-text">平均气温</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="chart-body">
          <div ref="chartContainerRef" class="echarts-container"></div>
          <div v-if="loading || dynamicDecompLoading" class="chart-loading">
            <div class="spinner"></div>
            <span>{{ dynamicDecompLoading ? '正在核对全月气温并试算动态日分解计划…' : '计划数据加载与图谱渲染中…' }}</span>
          </div>
        </div>

        <!-- 气温不完整提示横幅 -->
        <div v-if="isDynamicDecomposeEnabled && dynamicDecompError" class="decomp-warning-banner">
          <span class="warning-icon">⚠️</span>
          <span class="warning-text">{{ dynamicDecompError }}</span>
          <button
            type="button"
            class="btn-quick-import-weather"
            :disabled="weatherImporting"
            @click="handleImportEnsembleWeather"
          >
            {{ weatherImporting ? '⏳ 正在拉取预报...' : '⛅ 立即拉取35天预报' }}
          </button>
        </div>

        <!-- 全月逐日分解明细表格（支持折叠） -->
        <div v-if="isDynamicDecomposeEnabled && dynamicDecompData?.has_full_month && showDecompDetailTable" class="decomp-detail-section">
          <div class="decomp-detail-header">
            <h4>📅 {{ dynamicDecompData.company_cn }} ｜ {{ formatMonthCn(dynamicTargetMonth) }} 逐日动态计划分解明细</h4>
            <div class="decomp-detail-meta">
              <span>全月平均气温: <b>{{ dynamicDecompData.avg_temperature }} ℃</b></span>
              <span>月平均 HDD20: <b>{{ dynamicDecompData.avg_hdd20 }}</b></span>
              <span class="badge-audit">✓ 各日分解合计守恒</span>
            </div>
          </div>
          <div class="decomp-table-wrapper">
            <table class="decomp-matrix-table">
              <thead>
                <tr>
                  <th class="th-date">日期</th>
                  <th class="th-temp">日均温(℃)</th>
                  <th class="th-hdd">HDD20</th>
                  <th v-for="m in activeDecompositionMetrics" :key="'th_d_' + m.item" class="th-metric">
                    {{ m.item_cn }} ({{ m.unit }})
                    <span v-if="m.aggregation_method === 'sum_children'" class="th-k">子口径逐日汇总</span>
                    <span v-else class="th-k">k={{ Number(m.k_value || 0).toFixed(4) }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(d, idx) in dynamicDecompData.dates" :key="'tr_d_' + d">
                  <td class="td-date font-mono">{{ dynamicDecompData.day_labels[idx] }}</td>
                  <td class="td-temp font-mono">{{ dynamicDecompData.temperatures[idx] }}</td>
                  <td class="td-hdd font-mono">{{ dynamicDecompData.hdd20_series[idx] }}</td>
                  <td v-for="m in activeDecompositionMetrics" :key="'td_dv_' + m.item + '_' + idx" class="td-val font-mono">
                    {{ formatNumber(m.daily_plans[idx]) }}
                  </td>
                </tr>
                <tr class="tr-total">
                  <td class="td-date font-bold">全月合计</td>
                  <td class="td-temp font-bold">{{ dynamicDecompData.avg_temperature }} (均值)</td>
                  <td class="td-hdd font-bold">{{ dynamicDecompData.avg_hdd20 }} (均值)</td>
                  <td v-for="m in activeDecompositionMetrics" :key="'td_d_sum_' + m.item" class="td-val font-bold text-primary">
                    {{ formatNumber(m.daily_plans.reduce((a, b) => a + b, 0)) }}
                    <span v-if="m.aggregation_method === 'sum_children' && m.reported_month_plan != null && Math.abs(m.month_plan_difference) > 0.01" class="sub-target">直报: {{ formatNumber(m.reported_month_plan) }}；差额: {{ formatNumber(m.month_plan_difference) }}</span>
                    <span class="sub-target" title="分解基准值">({{ m.aggregation_method === 'sum_children' ? '子口径月计划合计' : '原计划' }}: {{ formatNumber(m.month_plan) }})</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- 详细指标数据矩阵表格 -->
      <section class="card table-section">
        <header class="table-header">
          <div class="table-title">
            <h3>指标全量计划数据矩阵</h3>
            <span class="count-tag">共 {{ filteredMetrics.length }} 项指标</span>
          </div>
          <div class="table-note">
            💡 点击指标行可在上方图表中单独聚焦查看；支持快捷横向滚动。
          </div>
        </header>

        <div class="table-container">
          <table class="matrix-table">
            <thead>
              <tr>
                <th class="col-pinned col-name">指标名称</th>
                <th class="col-unit">单位</th>
                <th v-for="m in displayedMonths" :key="'th_' + m" class="col-month">
                  {{ formatMonthCn(m) }}
                </th>
                <th class="col-stat col-total">区间总计</th>
                <th class="col-stat col-avg">月度均值</th>
                <th class="col-stat col-peak">峰值月份</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in filteredMetrics"
                :key="row.item"
                :class="['data-row', { highlighted: focusedMetricKey === row.item }]"
                @click="focusMetric(row)"
              >
                <td class="col-pinned col-name">
                  <span class="metric-title">{{ row.item_cn }}</span>
                  <span v-if="row.is_rollup" class="rollup-pill" title="由下辖实体单位向上汇总求和">全口径聚合</span>
                  <span v-else-if="row.is_ratio" class="ratio-pill">单耗指标</span>
                </td>
                <td class="col-unit text-center">{{ row.unit || '—' }}</td>
                <td
                  v-for="m in displayedMonths"
                  :key="'td_' + row.item + '_' + m"
                  class="col-month text-right"
                  :class="{ 'cell-peak': row.max_month === m && row.values[m] > 0 }"
                >
                  <span class="val-num">{{ formatCell(row.values[m]) }}</span>
                  <span
                    v-if="row.distribution && row.distribution[m] > 0"
                    class="val-ratio"
                    title="该月占全期百分比"
                  >
                    {{ row.distribution[m] }}%
                  </span>
                </td>
                <td class="col-stat col-total text-right font-bold">
                  {{ formatCell(row.total) }}
                </td>
                <td class="col-stat col-avg text-right">
                  {{ formatCell(row.average) }}
                </td>
                <td class="col-stat col-peak text-center">
                  <span v-if="row.max_month && row.max_value > 0" class="peak-badge">
                    {{ formatMonthCn(row.max_month) }}
                  </span>
                  <span v-else class="text-muted">—</span>
                </td>
              </tr>
              <tr v-if="!filteredMetrics.length && !loading">
                <td :colspan="5 + displayedMonths.length" class="empty-cell">
                  未勾选任何指标，请在上方【选择指标】下拉列表中勾选需要展示的指标项。
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import * as XLSX from 'xlsx'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { getDynamicPlanMeta, getDynamicPlanData, importEnsembleTemperature, fetchDynamicDailyDecomposition, updateDynamicPlanKParameters } from '../services/api'
import { getProjectNameById, ensureProjectsLoaded } from '../composables/useProjects'
import { useAuthStore } from '../store/auth'

const route = useRoute()
const auth = useAuthStore()
const projectKey = String(route.params.projectKey || 'daily_report_25_26')
const projectName = computed(() => getProjectNameById(projectKey) || '2026-2027供暖期生产日报')

// 全局管理员身份鉴权：只有 Global_admin 或系统超管 ww870411 具备前台在线设定 k 与 m 参数的权限
const isGlobalAdmin = computed(() => {
  const grp = String(auth.user?.group || '').toLowerCase()
  const name = String(auth.user?.username || '').toLowerCase()
  return grp === 'global_admin' || name === 'ww870411' || Boolean(auth.canAccessAdminConsole)
})

// 管理员在线参数编辑状态池：{ [item]: { k_value, m_value, origin_k, origin_m, item_cn, unit } }
const editingParams = ref({})
const savingParams = ref(false)
const paramFeedback = ref(null)

function syncEditingParamsFromMetrics(metrics) {
  const next = {}
  ;(metrics || []).forEach((m) => {
    if (m.aggregation_method === 'sum_children') return
    const k = Number(m.k_value || 0)
    const mv = Number(m.m_value !== undefined ? m.m_value : 1.0)
    next[m.item] = {
      k_value: k,
      m_value: mv,
      origin_k: k,
      origin_m: mv,
      item_cn: m.item_cn || m.item,
      unit: m.unit || '',
    }
  })
  editingParams.value = next
}

function isParamRowModified(itemKey) {
  const cur = editingParams.value[itemKey]
  if (!cur) return false
  const diffM = Math.abs(Number(cur.m_value !== undefined ? cur.m_value : 1.0) - Number(cur.origin_m !== undefined ? cur.origin_m : 1.0)) > 1e-5
  return diffM
}

const modifiedParamRows = computed(() => {
  const rows = []
  for (const [key, p] of Object.entries(editingParams.value)) {
    if (isParamRowModified(key)) {
      rows.push({ item: key, ...p })
    }
  }
  return rows
})

const modifiedParamsCount = computed(() => modifiedParamRows.value.length)

function resetParamEdits() {
  for (const p of Object.values(editingParams.value)) {
    p.m_value = p.origin_m
  }
  paramFeedback.value = {
    type: 'info',
    message: '已撤销当前未保存的 m 缩放系数改动',
  }
  setTimeout(() => {
    if (paramFeedback.value?.type === 'info') paramFeedback.value = null
  }, 2500)
}

const targetMonthNumber = computed(() => {
  const parts = String(dynamicTargetMonth.value || '2026-11').split('-')
  return parts.length >= 2 ? parseInt(parts[1], 10) : 11
})

async function saveSingleParam(m) {
  const p = editingParams.value[m.item]
  if (!p) return
  await executeSaveParams([
    {
      company: currentCompany.value,
      month: targetMonthNumber.value,
      item: m.item,
      item_cn: m.item_cn,
      unit: m.unit,
      m_value: Number(p.m_value !== undefined ? p.m_value : 1.0),
    },
  ])
}

async function saveAllModifiedParams() {
  const list = modifiedParamRows.value.map((p) => ({
    company: currentCompany.value,
    month: targetMonthNumber.value,
    item: p.item,
    item_cn: p.item_cn,
    unit: p.unit,
    m_value: Number(p.m_value !== undefined ? p.m_value : 1.0),
  }))
  if (!list.length) return
  await executeSaveParams(list)
}

async function executeSaveParams(updates) {
  if (savingParams.value) return
  savingParams.value = true
  paramFeedback.value = null
  try {
    const res = await updateDynamicPlanKParameters(projectKey, { updates })
    if (res.ok) {
      paramFeedback.value = {
        type: 'success',
        message: res.message || 'm 缩放系数保存成功，已实时重新试算日分解分布律！',
      }
      updates.forEach((u) => {
        if (editingParams.value[u.item]) {
          editingParams.value[u.item].origin_m = u.m_value
        }
      })
      // 重新加载日分解计算数据，使图表、Tooltip与表格即时响应
      await loadDynamicDecompositionData()
    } else {
      paramFeedback.value = {
        type: 'error',
        message: res.message || '保存 m 缩放系数失败',
      }
    }
  } catch (err) {
    paramFeedback.value = {
      type: 'error',
      message: err.message || '网络连接或后端异常',
    }
  } finally {
    savingParams.value = false
    setTimeout(() => {
      paramFeedback.value = null
    }, 6000)
  }
}

const pageDisplayName = computed(() => {
  const raw = route.query.pageName
  const legacyNames = new Set(['动态计划指标', '动态计划模块'])
  if (typeof raw === 'string' && raw.trim() && !legacyNames.has(raw.trim())) {
    return raw.trim()
  }
  return '计划动态分解模块'
})

// 页面基础响应状态
const loading = ref(false)
const unitOptions = ref([])
const availableMonths = ref(['2026-10', '2026-11', '2026-12', '2027-01', '2027-02', '2027-03', '2027-04'])

const currentCompany = ref('Group')
const startMonth = ref('2026-11')
const endMonth = ref('2027-04')
const focusedMetricKey = ref('')

// 35天集合气温预报同步状态
const weatherImporting = ref(false)
const weatherSyncStatus = ref(null)

async function handleImportEnsembleWeather() {
  if (weatherImporting.value) return
  weatherImporting.value = true
  weatherSyncStatus.value = null
  try {
    const res = await importEnsembleTemperature(projectKey)
    if (res.ok) {
      weatherSyncStatus.value = {
        success: true,
        message: `预报同步成功：写入 ${res.inserted_or_updated} 条，保留已有近端气温 ${res.skipped_near || 0} 条，预报截止 ${res.end_time?.replace('T', ' ')}`,
      }
    } else {
      weatherSyncStatus.value = {
        success: false,
        message: res.message || '拉取35天集合气温预报失败',
      }
    }
  } catch (err) {
    weatherSyncStatus.value = {
      success: false,
      message: err.message || '网络连接或后端异常',
    }
  } finally {
    weatherImporting.value = false
    setTimeout(() => {
      weatherSyncStatus.value = null
    }, 7000)
  }
}

// ==================== 动态计划月度日分解状态与控制 ====================
const isDynamicDecomposeEnabled = ref(false) // 默认不选中
const dynamicTargetMonth = ref('2026-11') // 默认目标月份
const dynamicDecompLoading = ref(false)
const dynamicDecompData = ref(null)
const dynamicDecompError = ref('')
const showDecompDetailTable = ref(false)
const showDecompTemperature = ref(true) // 动态分解时默认展示平均气温曲线，支持勾选切换关闭
const showDecompAlgorithmPanel = ref(false) // 动态分解算法与各指标 k 值面板（默认收起状态）

// 当前单位口径在目标月份下的全部指标及 k 值字典列表（按是否有 k 值与数值大小排序）
const decompositionMetricsWithK = computed(() => {
  if (!dynamicDecompData.value || !dynamicDecompData.value.metrics) return []
  return [...dynamicDecompData.value.metrics].sort((a, b) => {
    if (a.has_k && !b.has_k) return -1
    if (!a.has_k && b.has_k) return 1
    const diffK = Number(b.k_value || 0) - Number(a.k_value || 0)
    if (Math.abs(diffK) > 1e-6) return diffK
    return (a.item_cn || '').localeCompare(b.item_cn || '', 'zh-CN')
  })
})

// 监听指标列表变化，同步初始化管理员编辑池
watch(
  decompositionMetricsWithK,
  (list) => {
    syncEditingParamsFromMetrics(list)
  },
  { immediate: true }
)

// 当前在动态分解模式下处于激活展示状态的指标（与图表二次筛选严格联动）
const activeDecompositionMetrics = computed(() => {
  if (!dynamicDecompData.value || !dynamicDecompData.value.metrics) return []
  // 若用户在二次筛选中清空了勾选，严格返回空，不呈现任何指标
  if (chartSelectedMetricKeys.value.length === 0) {
    return []
  }
  const allDecomp = dynamicDecompData.value.metrics
  const selectedSet = new Set(chartSelectedMetricKeys.value)
  return allDecomp.filter((m) => selectedSet.has(m.item))
})

// 只接受当前口径的最新响应，避免旧请求覆盖新选择。
let decompositionRequestId = 0
let planRequestId = 0
async function loadDynamicDecompositionData() {
  const requestId = ++decompositionRequestId
  const company = currentCompany.value
  const yearMonth = dynamicTargetMonth.value
  const isCurrent = () => requestId === decompositionRequestId && company === currentCompany.value && yearMonth === dynamicTargetMonth.value && isDynamicDecomposeEnabled.value
  if (!isDynamicDecomposeEnabled.value) {
    renderChart()
    return
  }
  dynamicDecompLoading.value = true
  dynamicDecompData.value = null
  dynamicDecompError.value = ''
  try {
    const res = await fetchDynamicDailyDecomposition({
      projectKey,
      company,
      yearMonth,
    })
    if (!isCurrent()) return
    dynamicDecompData.value = res
    if (!res.has_full_month) {
      dynamicDecompError.value = res.message || `${dynamicTargetMonth.value} 气温数据不完整，缺少全月气温，无法执行动态分解`
    }
  } catch (err) {
    if (!isCurrent()) return
    dynamicDecompData.value = null
    dynamicDecompError.value = err.message || '加载动态日分解数据失败'
  } finally {
    if (!isCurrent()) return
    dynamicDecompLoading.value = false
    await nextTick()
    renderChart()
  }
}

function handleDynamicDecomposeToggle() {
  ++decompositionRequestId
  dynamicDecompLoading.value = false
  dynamicDecompData.value = null
  if (isDynamicDecomposeEnabled.value) {
    showDecompTemperature.value = true // 选中“动态分解”时，默认开启平均气温参考曲线
    showDecompAlgorithmPanel.value = false // 算法与各指标 k 值面板默认保持收起状态
    if (startMonth.value === endMonth.value) {
      dynamicTargetMonth.value = startMonth.value
    } else if (displayedMonths.value.includes('2026-11')) {
      dynamicTargetMonth.value = '2026-11'
    } else {
      dynamicTargetMonth.value = startMonth.value
    }
    loadDynamicDecompositionData()
  } else {
    dynamicDecompError.value = ''
    renderChart()
  }
}

// 指标下拉复选控制状态（全局/表格）
const metricDropdownRef = ref(null)
const isMetricDropdownOpen = ref(false)
const selectedMetricKeys = ref([])

// 图表专属二次指标筛选状态（默认仅选中供热量、发电量、标煤耗量，可下拉取消或增选）
const chartMetricDropdownRef = ref(null)
const isChartMetricDropdownOpen = ref(false)
const chartSelectedMetricKeys = ref([])
const isChartCustomized = ref(false)

// 默认选中的核心生产指标：供热量、发电量、标煤耗量
const DEFAULT_CORE_METRIC_KEYS = ['amount_heat_supply', 'amount_power_generation', 'consumption_std_coal']

function getDefaultChartMetricKeys(availableMetrics) {
  const availableSet = new Set((availableMetrics || []).map((m) => m.item))
  const matched = DEFAULT_CORE_METRIC_KEYS.filter((k) => availableSet.has(k))
  if (matched.length > 0) {
    return matched
  }
  return (availableMetrics || []).slice(0, 3).map((m) => m.item)
}

const isAllMetricsSelected = computed(() => {
  return metricsList.value.length > 0 && selectedMetricKeys.value.length === metricsList.value.length
})

// 数据集
const displayedMonths = ref([])
const metricsList = ref([])
const summaryCards = ref({})

// ECharts
const chartContainerRef = ref(null)
let chartInstance = null
let resizeObserver = null
const activeChartTab = ref('dynamic_trend')

const chartTabs = [
  { key: 'dynamic_trend', label: '已选指标月度走势 (动态联动)', icon: '📈' },
  { key: 'dynamic_bar', label: '已选指标柱状对比', icon: '📊' },
  { key: 'donut_distribution', label: '已选指标负荷占比 (环形图)', icon: '🥧' },
]

const presetRanges = [
  { key: 'full_season', label: '🌟 全采暖期 (11~4月)', start: '2026-11', end: '2027-04' },
  { key: 'with_oct', label: '🍂 含供暖初期 (10~4月)', start: '2026-10', end: '2027-04' },
]

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: pageDisplayName.value, to: null },
])

const currentUnitLabel = computed(() => {
  const item = unitOptions.value.find((u) => u.company === currentCompany.value)
  return item ? item.company_cn : currentCompany.value
})

const isPlantUnit = computed(() => {
  return ['BeiHai', 'XiangHai', 'JinZhou', 'BeiFang'].includes(currentCompany.value)
})

// 过滤后的指标列表（按复选框勾选过滤，控制下方矩阵表格）
const filteredMetrics = computed(() => {
  if (!selectedMetricKeys.value.length) return []
  const selectedSet = new Set(selectedMetricKeys.value)
  return metricsList.value.filter((m) => selectedSet.has(m.item))
})

// 图表最终呈现的指标列表（在表格已选指标基础上进行图表二次筛选）
const chartMetrics = computed(() => {
  if (!chartSelectedMetricKeys.value.length) return []
  const chartSet = new Set(chartSelectedMetricKeys.value)
  // 图表呈现指标严格限制在表格指标池内
  return filteredMetrics.value.filter((m) => chartSet.has(m.item))
})

// 图表通用美化调色板
const METRIC_PALETTE = [
  '#2563eb', '#f97316', '#10b981', '#8b5cf6', '#06b6d4',
  '#ec4899', '#f59e0b', '#6366f1', '#14b8a6', '#e11d48',
  '#84cc16', '#0284c7', '#a855f7', '#d97706', '#64748b',
]

function getMetricColor(itemKey) {
  const index = chartMetrics.value.findIndex((m) => m.item === itemKey)
  if (index >= 0) {
    return METRIC_PALETTE[index % METRIC_PALETTE.length]
  }
  const allIndex = metricsList.value.findIndex((m) => m.item === itemKey)
  if (allIndex >= 0) {
    return METRIC_PALETTE[allIndex % METRIC_PALETTE.length]
  }
  return '#64748b'
}

// 智能计算双纵轴映射与提示指引信息
// 所有数值图统一按计量单位分轴；第三种单位也拥有独立刻度。
function metricUnits(metrics) {
  return [...new Set(metrics.map(m => m.unit || '数值'))].sort((a, b) => a === b ? 0 : a === 'GJ' ? -1 : b === 'GJ' ? 1 : a.localeCompare(b))
}
function metricAxes(metrics) {
  return metricUnits(metrics).map((unit, index) => ({
    type: 'value', name: unit, position: index === 0 ? 'left' : 'right',
    offset: index > 0 ? (index - 1) * 65 : 0,
    splitLine: { show: index === 0 }, axisLabel: { formatter: formatAxisNum },
  }))
}
const chartAxisMappingInfo = computed(() => {
  const targets = isDynamicDecomposeEnabled.value ? activeDecompositionMetrics.value : chartMetrics.value
  const units = metricUnits(targets)
  const leftUnit = units[0] || ''
  const leftMetrics = targets.filter(m => (m.unit || '数值') === leftUnit)

  // 右侧单位组：units.slice(1) 每个单位对应的指标列表（支持多右轴单位依次并列）
  const rightGroups = units.slice(1).map(u => ({
    unit: u,
    metrics: targets.filter(m => (m.unit || '数值') === u),
  }))

  const rightMetrics = targets.filter(m => (m.unit || '数值') !== leftUnit)
  const rightUnit = units[1] || ''

  // 动态分解模式下是否启用了平均气温曲线
  const hasTempRightAxis =
    isDynamicDecomposeEnabled.value &&
    showDecompTemperature.value &&
    (dynamicDecompData.value?.temperatures?.length > 0)

  // 支持左右轴对照指引的图表模式
  const isSupportedTab =
    isDynamicDecomposeEnabled.value ||
    ['dynamic_trend', 'dynamic_bar'].includes(activeChartTab.value)

  // 只要涉及 2 个及以上不同计量单位，或开启动态分解且带气温曲线时，均展示左右轴对照指引条
  const showBanner = isSupportedTab && (units.length >= 2 || hasTempRightAxis)

  return {
    units,
    showBanner,
    hasDualAxis: units.length > 1,
    leftUnit,
    rightUnit,
    leftMetrics,
    rightMetrics,
    rightGroups,
    hasTempRightAxis,
    leftKeys: new Set(leftMetrics.map(m => m.item)),
    rightKeys: new Set(rightMetrics.map(m => m.item)),
  }
})

function formatMonthCn(mStr) {
  if (!mStr) return ''
  const parts = mStr.split('-')
  if (parts.length === 2) {
    return `${parts[0]}年${parseInt(parts[1], 10)}月`
  }
  return mStr
}

function formatNumber(val) {
  if (val === null || val === undefined || isNaN(val)) return '0.00'
  return Number(val).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function formatCell(val) {
  if (val === null || val === undefined) return '—'
  if (val === 0) return '0'
  return Number(val).toLocaleString('zh-CN', {
    maximumFractionDigits: 4,
  })
}

function getMetricAverage(itemKey) {
  const m = metricsList.value.find((i) => i.item === itemKey)
  return m ? m.average : 0
}

function getMetricTotal(itemKey) {
  const m = metricsList.value.find((i) => i.item === itemKey)
  return m ? m.total : 0
}

function getMetricPeakMonth(itemKey) {
  const m = metricsList.value.find((i) => i.item === itemKey)
  if (m && m.max_month && m.max_value > 0) {
    return formatMonthCn(m.max_month)
  }
  return ''
}

function getFocusedMetricName() {
  const m = metricsList.value.find((i) => i.item === focusedMetricKey.value)
  return m ? m.item_cn : focusedMetricKey.value
}

function formatAxisNum(val) {
  if (val === null || val === undefined || isNaN(val)) return '0'
  const abs = Math.abs(val)
  if (abs >= 10000) {
    return (val / 10000).toFixed(1) + '万'
  }
  if (abs >= 1000) {
    return Math.round(val)
  }
  return Number(val.toFixed(2))
}

function getCoalRatioText() {
  const raw = summaryCards.value.raw_coal_total || 0
  const std = summaryCards.value.std_coal_total || 0
  if (raw > 0 && std > 0) {
    return (raw / std).toFixed(2)
  }
  return '—'
}

function toggleMetricDropdown() {
  isMetricDropdownOpen.value = !isMetricDropdownOpen.value
}

function selectAllMetrics() {
  selectedMetricKeys.value = metricsList.value.map((m) => m.item)
}

function clearAllMetrics() {
  selectedMetricKeys.value = []
}

function invertMetricsSelection() {
  const currentSet = new Set(selectedMetricKeys.value)
  selectedMetricKeys.value = metricsList.value
    .filter((m) => !currentSet.has(m.item))
    .map((m) => m.item)
}

// 图表专属二次筛选操作
function toggleChartMetricDropdown() {
  isChartMetricDropdownOpen.value = !isChartMetricDropdownOpen.value
}

// 还原默认选中的核心生产指标：供热量、发电量、标煤耗量
function resetToDefaultChartMetrics() {
  isChartCustomized.value = false
  chartSelectedMetricKeys.value = getDefaultChartMetricKeys(filteredMetrics.value)
}

function selectAllChartMetrics() {
  isChartCustomized.value = true
  chartSelectedMetricKeys.value = filteredMetrics.value.map((m) => m.item)
}

function clearAllChartMetrics() {
  isChartCustomized.value = true
  chartSelectedMetricKeys.value = []
}

function handleGlobalClick(e) {
  if (metricDropdownRef.value && !metricDropdownRef.value.contains(e.target)) {
    isMetricDropdownOpen.value = false
  }
  if (chartMetricDropdownRef.value && !chartMetricDropdownRef.value.contains(e.target)) {
    isChartMetricDropdownOpen.value = false
  }
}

function isPresetActive(p) {
  return startMonth.value === p.start && endMonth.value === p.end
}

function applyPreset(p) {
  startMonth.value = p.start
  endMonth.value = p.end
  fetchData()
}

function handleUnitChange(companyCode) {
  currentCompany.value = companyCode
  fetchData()
}

function handleMonthChange() {
  if (startMonth.value > endMonth.value) {
    const temp = startMonth.value
    startMonth.value = endMonth.value
    endMonth.value = temp
  }
  fetchData()
}

function focusMetric(row) {
  if (focusedMetricKey.value === row.item) {
    focusedMetricKey.value = ''
  } else {
    focusedMetricKey.value = row.item
    // 点击表格行时，若未在全局勾选列表中，自动加入
    if (!selectedMetricKeys.value.includes(row.item)) {
      selectedMetricKeys.value.push(row.item)
    }
    // 确保在图表呈现指标中也予以勾选展示
    if (!chartSelectedMetricKeys.value.includes(row.item)) {
      chartSelectedMetricKeys.value.push(row.item)
    }
  }
  renderChart()
  if (chartInstance) {
    chartInstance.resize()
  }
}

// 全局指标筛选变动时，确保图表选中的项不超出全局指标池
watch(
  selectedMetricKeys,
  (newKeys) => {
    const newSet = new Set(newKeys)
    // 仅保留上方仍处于勾选状态的图表指标
    chartSelectedMetricKeys.value = chartSelectedMetricKeys.value.filter((k) => newSet.has(k))
    nextTick(() => {
      renderChart()
    })
  },
  { deep: true },
)

// 图表二次筛选改变时，标记为已定制并触发重绘
watch(
  chartSelectedMetricKeys,
  () => {
    nextTick(() => {
      renderChart()
    })
  },
  { deep: true },
)

function switchChartTab(tabKey) {
  activeChartTab.value = tabKey
  nextTick(() => {
    renderChart()
    if (chartInstance) {
      chartInstance.resize()
    }
  })
}

// -------------------------------------------------------------
// 数据请求逻辑
// -------------------------------------------------------------
async function initMeta() {
  try {
    const res = await getDynamicPlanMeta(projectKey)
    if (res.ok) {
      unitOptions.value = res.units || []
      if (res.available_months && res.available_months.length) {
        availableMonths.value = res.available_months
      }
      if (res.default_range) {
        startMonth.value = res.default_range.start_month || '2026-11'
        endMonth.value = res.default_range.end_month || '2027-04'
      }
    }
  } catch (err) {
    console.error('初始化动态计划元数据失败:', err)
  }
}

async function fetchData() {
  const requestId = ++planRequestId
  const company = currentCompany.value
  const start = startMonth.value
  const end = endMonth.value
  const isCurrent = () => requestId === planRequestId && company === currentCompany.value && start === startMonth.value && end === endMonth.value
  ++decompositionRequestId
  dynamicDecompLoading.value = false
  dynamicDecompData.value = null
  metricsList.value = []
  summaryCards.value = {}
  loading.value = true
  try {
    const res = await getDynamicPlanData(projectKey, {
      company,
      start_month: start,
      end_month: end,
      plan_type: 'plan',
    })
    if (!isCurrent()) return
    if (res.ok) {
      displayedMonths.value = res.months || []
      if (!displayedMonths.value.includes(dynamicTargetMonth.value)) {
        dynamicTargetMonth.value = displayedMonths.value[0] || ''
      }
      metricsList.value = res.metrics || []
      summaryCards.value = res.summary_cards || {}
      // 表格保持全选当前单位下的全部指标
      selectedMetricKeys.value = (res.metrics || []).map((m) => m.item)
      // 图表二次筛选默认仅选中：供热量、发电量、标煤耗量三个指标
      chartSelectedMetricKeys.value = getDefaultChartMetricKeys(res.metrics || [])
      isChartCustomized.value = false

      // 若开启动态分解模式，同步刷新动态日分解数据
      if (isDynamicDecomposeEnabled.value && dynamicTargetMonth.value) {
        await loadDynamicDecompositionData()
      }
    }
  } catch (err) {
    if (!isCurrent()) return
    displayedMonths.value = []
    dynamicDecompError.value = err.message || '读取计划失败，请刷新重试'
    console.error('读取动态计划数据失败:', err)
  } finally {
    if (!isCurrent()) return
    loading.value = false
    await nextTick()
    renderChart()
    setTimeout(() => {
      if (chartInstance) {
        chartInstance.resize()
      }
    }, 60)
  }
}

// -------------------------------------------------------------
// 动态日计划分解图表渲染引擎 (基于 HDD20 与 k 值模型)
// -------------------------------------------------------------
function renderDynamicDecomposeChart() {
  if (!chartContainerRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainerRef.value)
  }

  // 1. 若气温不完整或发生错误
  if (!dynamicDecompData.value || !dynamicDecompData.value.has_full_month) {
    chartInstance.setOption(
      {
        title: {
          text: `⚠️ ${formatMonthCn(dynamicTargetMonth.value)} 气温数据不完整，无法进行动态分解`,
          subtext:
            dynamicDecompError.value ||
            '该月份在数据库中缺少全月完整气温数据，请先导入预报或选择气温完整的月份（如 2026-11）',
          left: 'center',
          top: 'center',
          textStyle: { color: '#f59e0b', fontSize: 16, fontWeight: 600 },
          subtextStyle: { color: '#64748b', fontSize: 13 },
        },
        xAxis: { show: false },
        yAxis: { show: false },
        series: [],
      },
      true,
    )
    return
  }

  const {
    day_labels,
    dates,
    temperatures,
    hdd20_series,
    avg_temperature,
    avg_hdd20,
    company_cn,
  } = dynamicDecompData.value

  const activeMetrics = activeDecompositionMetrics.value

  if (!activeMetrics.length) {
    chartInstance.setOption(
      {
        title: {
          text: '未勾选具备 k 值的分解指标',
          subtext: '请在右上角【图表呈现】中勾选具备 k 模型的指标项（如供热量、发电量、耗煤等）',
          left: 'center',
          top: 'center',
          textStyle: { color: '#94a3b8', fontSize: 16, fontWeight: 500 },
          subtextStyle: { color: '#cbd5e1', fontSize: 13 },
        },
        xAxis: { show: false },
        yAxis: { show: false },
        series: [],
      },
      true,
    )
    return
  }

  // 分析这批指标的单位分布
  const unitList = metricUnits(activeMetrics)
  const leftUnit = unitList[0] || ''
  const rightUnit = unitList.length > 1 ? unitList[1] : ''
  const hasDualAxis = unitList.length > 1

  const series = []

  // 1. 各生产指标的每日计划平滑曲线
  activeMetrics.forEach((m) => {
    const isFocused = focusedMetricKey.value === m.item
    const hasFocus = !!focusedMetricKey.value
    const color = getMetricColor(m.item)
    const useRightAxis = hasDualAxis && m.unit === rightUnit

    const baseSeries = {
      name: `${m.item_cn} (${m.unit || '—'})`,
      type: 'line',
      yAxisIndex: unitList.indexOf(m.unit || '数值'),
      smooth: true,
      symbol: isFocused ? 'circle' : 'emptyCircle',
      symbolSize: isFocused ? 8 : 5,
      data: m.daily_plans,
      z: isFocused ? 10 : 3,
      lineStyle: {
        width: isFocused ? 4 : 2.5,
        color,
        opacity: hasFocus && !isFocused ? 0.3 : 1,
      },
      itemStyle: { color },
    }

    if (activeMetrics.length === 1 && !showDecompTemperature.value) {
      baseSeries.areaStyle = {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(37, 99, 235, 0.3)' },
          { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
        ]),
      }
    }
    series.push(baseSeries)
  })

  // 2. 气温曲线配置（默认开启平均气温，亦可勾选关闭）
  const includeTemp = showDecompTemperature.value && temperatures && temperatures.length > 0
  let tempYAxisIndex = -1

  const yAxes = metricAxes(activeMetrics)

  if (includeTemp) {
    if (!hasDualAxis) {
      tempYAxisIndex = 1
      yAxes.push({
        type: 'value',
        name: '平均气温 (℃)',
        position: 'right',
        nameTextStyle: { color: '#0284c7', fontSize: 11, padding: [0, 0, 4, 0] },
        splitLine: { show: false },
        axisLabel: { formatter: (v) => `${v}℃` },
        axisLine: { show: true, lineStyle: { color: '#0284c7' } },
      })
    } else {
      tempYAxisIndex = unitList.length
      yAxes.push({
        type: 'value',
        name: '平均气温 (℃)',
        position: 'right',
        offset: (unitList.length - 1) * 65,
        nameTextStyle: { color: '#0284c7', fontSize: 11, padding: [0, 0, 4, 0] },
        splitLine: { show: false },
        axisLabel: { formatter: (v) => `${v}℃` },
        axisLine: { show: true, lineStyle: { color: '#0284c7' } },
      })
    }

    series.push({
      name: '平均气温 (℃)',
      type: 'line',
      yAxisIndex: tempYAxisIndex,
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      data: temperatures,
      z: 2,
      lineStyle: {
        width: 2.2,
        color: '#0284c7',
        type: 'dashed',
        opacity: 0.9,
      },
      itemStyle: { color: '#0284c7' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(2, 132, 199, 0.12)' },
          { offset: 1, color: 'rgba(2, 132, 199, 0.01)' },
        ]),
      },
    })
  }

  chartInstance.setOption(
    {
      title: { show: false },
      legend: {
        type: 'scroll',
        top: 8,
        left: 20,
        right: 20,
        textStyle: { fontSize: 12, color: '#334155' },
        pageButtonPosition: 'end',
      },
      grid: {
        left: '3%',
        right: Math.max(65, (unitList.length - 1 + (includeTemp ? 1 : 0)) * 65),
        top: 48,
        bottom: '8%',
        containLabel: true,
      },
      tooltip: {
        trigger: 'axis',
        confine: true,
        axisPointer: { type: 'cross', lineStyle: { color: '#94a3b8', type: 'dashed' } },
        formatter: (params) => {
          if (!params || !params.length) return ''
          const idx = params[0].dataIndex
          const dFull = dates[idx]
          const temp = temperatures[idx]
          const hdd = hdd20_series[idx]

          let tip = `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px;display:flex;justify-content:space-between;gap:16px;">
            <span>📅 ${dFull}</span>
            <span style="color:#0284c7;">🌡️ ${temp} ℃ (HDD20: ${hdd})</span>
          </div>`

          params.forEach((p) => {
            if (p.seriesName.includes('气温')) {
              tip += `<div style="display:flex;align-items:center;justify-content:space-between;font-size:12px;margin:2px 0;color:#0284c7;">
                <span>● ${p.seriesName}:</span>
                <span style="font-weight:700;">${p.value} ℃</span>
              </div>`
              return
            }
            const metricItem = activeMetrics.find((m) => `${m.item_cn} (${m.unit || '—'})` === p.seriesName)
            const w = metricItem?.daily_weights?.[idx]
            const hasK = metricItem?.has_k !== false
            tip += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:12px;margin:3px 0;">
              <span style="display:inline-flex;align-items:center;gap:6px;">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
                <span>${p.seriesName}:</span>
              </span>
              <span style="font-weight:700;">${formatNumber(p.value)} ${hasK && w !== undefined ? `<small style="color:#64748b;font-weight:normal;">(权重 ${w})</small>` : `<small style="color:#94a3b8;font-weight:normal;">${metricItem?.aggregation_method === 'sum_children' ? '(子口径逐日汇总)' : '(无k·日均摊)'}</small>`}</span>
            </div>`
          })
          return tip
        },
      },
      xAxis: {
        type: 'category',
        data: day_labels,
        axisLabel: { interval: 0, rotate: 0, fontSize: 11 },
        show: true,
      },
      yAxis: yAxes,
      series,
    },
    true,
  )
  chartInstance.resize()
}

// -------------------------------------------------------------
// ECharts 图表渲染引擎
// -------------------------------------------------------------
function renderChart() {
  if (!chartContainerRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainerRef.value)
  }

  // 若开启动态分解模式，则执行动态日计划分解走势图渲染
  if (isDynamicDecomposeEnabled.value) {
    renderDynamicDecomposeChart()
    return
  }

  const months = displayedMonths.value
  const monthLabels = months.map(formatMonthCn)
  const targetMetrics = chartMetrics.value

  // 1. 模式一：已选指标月度走势（折线动态联动，默认）
  if (activeChartTab.value === 'dynamic_trend') {
    if (!targetMetrics.length) {
      chartInstance.setOption(
        {
          title: {
            text: '未勾选任何图表呈现指标',
            subtext: '请在图表右上角【图表呈现】下拉框中勾选需要对比的指标项',
            left: 'center',
            top: 'center',
            textStyle: { color: '#94a3b8', fontSize: 16, fontWeight: 500 },
            subtextStyle: { color: '#cbd5e1', fontSize: 13 },
          },
          series: [],
        },
        true,
      )
      return
    }

    const mapping = chartAxisMappingInfo.value
    const hasDualAxis = mapping.hasDualAxis

    const series = targetMetrics.map((m) => {
      const isFocused = focusedMetricKey.value === m.item
      const hasFocus = !!focusedMetricKey.value
      const isSingle = targetMetrics.length === 1
      const color = getMetricColor(m.item)
      const useRightAxis = hasDualAxis && mapping.rightKeys.has(m.item)

      const baseSeries = {
        name: `${m.item_cn} (${m.unit || '—'})`,
        type: 'line',
        yAxisIndex: metricUnits(targetMetrics).indexOf(m.unit || '数值'),
        smooth: true,
        symbol: isFocused || isSingle ? 'circle' : 'emptyCircle',
        symbolSize: isFocused ? 10 : isSingle ? 8 : 6,
        data: months.map((mo) => m.values[mo] ?? 0),
        z: isFocused ? 10 : 2,
        lineStyle: {
          width: isFocused ? 4.5 : 2.5,
          color,
          opacity: hasFocus && !isFocused ? 0.28 : 1,
          shadowColor: isFocused ? color : 'transparent',
          shadowBlur: isFocused ? 10 : 0,
        },
        itemStyle: {
          color,
          opacity: hasFocus && !isFocused ? 0.28 : 1,
        },
      }

      // 单指标时添加渐变面积填充
      if (isSingle) {
        baseSeries.areaStyle = {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.35)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
          ]),
        }
      }

      return baseSeries
    })

    const yAxes = metricAxes(targetMetrics)

    chartInstance.setOption(
      {
        title: { show: false },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross', lineStyle: { color: '#94a3b8', type: 'dashed' } },
          formatter: (params) => {
            let tip = `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px;">${params[0]?.axisValue}</div>`
            params.forEach((p) => {
              tip += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:12px;margin:3px 0;">
                <span style="display:inline-flex;align-items:center;gap:6px;">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
                  <span>${p.seriesName}:</span>
                </span>
                <span style="font-weight:700;">${formatNumber(p.value)}</span>
              </div>`
            })
            return tip
          },
        },
        legend: {
          type: 'scroll',
          top: 8,
          right: 16,
          left: 100,
          textStyle: { fontSize: 12 },
        },
        grid: { left: '3%', right: Math.max(65, (metricUnits(targetMetrics).length - 1) * 65), bottom: '8%', top: '16%', containLabel: true },
        xAxis: { type: 'category', data: monthLabels, axisLabel: { interval: 0, rotate: 12 } },
        yAxis: yAxes,
        series,
      },
      true,
    )
    chartInstance.resize()
    return
  }

  // 2. 模式二：已选指标柱状对比（动态联动）
  if (activeChartTab.value === 'dynamic_bar') {
    if (!targetMetrics.length) {
      chartInstance.setOption(
        {
          title: {
            text: '未勾选任何图表呈现指标',
            subtext: '请在图表右上角【图表呈现】下拉框中勾选指标以生成柱状对比图',
            left: 'center',
            top: 'center',
            textStyle: { color: '#94a3b8', fontSize: 16, fontWeight: 500 },
            subtextStyle: { color: '#cbd5e1', fontSize: 13 },
          },
          series: [],
        },
        true,
      )
      return
    }

    const mapping = chartAxisMappingInfo.value
    const hasDualAxis = mapping.hasDualAxis

    const series = targetMetrics.map((m) => {
      const isFocused = focusedMetricKey.value === m.item
      const hasFocus = !!focusedMetricKey.value
      const color = getMetricColor(m.item)
      const useRightAxis = hasDualAxis && mapping.rightKeys.has(m.item)

      return {
        name: `${m.item_cn} (${m.unit || '—'})`,
        type: 'bar',
        yAxisIndex: metricUnits(targetMetrics).indexOf(m.unit || '数值'),
        barMaxWidth: targetMetrics.length > 4 ? 20 : 32,
        data: months.map((mo) => m.values[mo] ?? 0),
        itemStyle: {
          color,
          opacity: hasFocus && !isFocused ? 0.35 : 1,
          borderRadius: [4, 4, 0, 0],
        },
      }
    })

    const yAxes = metricAxes(targetMetrics)

    chartInstance.setOption(
      {
        title: { show: false },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params) => {
            let tip = `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px;">${params[0]?.axisValue}</div>`
            params.forEach((p) => {
              tip += `<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:12px;margin:3px 0;">
                <span style="display:inline-flex;align-items:center;gap:6px;">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
                  <span>${p.seriesName}:</span>
                </span>
                <span style="font-weight:700;">${formatNumber(p.value)}</span>
              </div>`
            })
            return tip
          },
        },
        legend: {
          type: 'scroll',
          top: 8,
          right: 16,
          left: 100,
          textStyle: { fontSize: 12 },
        },
        grid: { left: '3%', right: Math.max(65, (metricUnits(targetMetrics).length - 1) * 65), bottom: '8%', top: '16%', containLabel: true },
        xAxis: { type: 'category', data: monthLabels, axisLabel: { interval: 0, rotate: 12 } },
        yAxis: yAxes,
        series,
      },
      true,
    )
    chartInstance.resize()
    return
  }

  // 3. 模式三：负荷分布占比图（环形饼图，动态联动）
  if (activeChartTab.value === 'donut_distribution') {
    let target = null
    if (focusedMetricKey.value) {
      target = metricsList.value.find((m) => m.item === focusedMetricKey.value)
    }
    if (!target && targetMetrics.length) {
      target = targetMetrics[0]
    }
    if (!target) {
      target = metricsList.value.find((m) => m.item === 'amount_heat_supply') || metricsList.value[0]
    }

    if (!target) {
      chartInstance.setOption({ series: [] }, true)
      return
    }

    const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768
    const pieData = months.map((m) => ({
      name: formatMonthCn(m),
      value: target.values[m] || 0,
      pct: target.distribution?.[m] || 0,
    }))

    chartInstance.setOption(
      {
        title: {
          text: `【${target.item_cn}】各月计划负荷分布比例`,
          subtext: `全月合计 = 100% ｜ 区间总计: ${formatNumber(target.total)} ${target.unit}`,
          left: 'center',
          top: isMobile ? 6 : 10,
          textStyle: { fontSize: isMobile ? 13 : 15, fontWeight: 700, color: '#0f172a' },
          subtextStyle: { fontSize: isMobile ? 11 : 12, color: '#64748b' },
        },
        tooltip: {
          trigger: 'item',
          confine: true,
          formatter: '{b}: <br/><b>{c}</b> ' + (target.unit || '') + ' ({d}%)',
        },
        legend: isMobile
          ? { orient: 'horizontal', bottom: 4, left: 'center', textStyle: { fontSize: 11 } }
          : { orient: 'vertical', left: 24, top: 'middle' },
        series: [
          {
            name: `${target.item_cn}分布`,
            type: 'pie',
            radius: isMobile ? ['36%', '60%'] : ['44%', '72%'],
            center: isMobile ? ['50%', '52%'] : ['56%', '56%'],
            avoidLabelOverlap: true,
            itemStyle: {
              borderRadius: 6,
              borderColor: '#fff',
              borderWidth: 2,
            },
            label: {
              show: true,
              formatter: '{b}\n{d}%',
              fontWeight: 'bold',
            },
            data: pieData,
          },
        ],
      },
      true,
    )
    chartInstance.resize()
    return
  }
}

let resizeTimer = null
function handleResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    if (chartInstance) {
      renderChart()
    }
  }, 100)
}

// 导出当前表格到 Excel
function exportToExcel() {
  if (!metricsList.value.length) return
  const headers = ['单位/口径', '指标名称', '计量单位', ...displayedMonths.value.map(formatMonthCn), '区间合计', '月度均值', '峰值月份']
  const dataRows = filteredMetrics.value.map((m) => [
    currentUnitLabel.value,
    m.item_cn,
    m.unit,
    ...displayedMonths.value.map((mo) => m.values[mo] ?? 0),
    m.total,
    m.average,
    m.max_month ? formatMonthCn(m.max_month) : '—',
  ])

  const ws = XLSX.utils.aoa_to_sheet([headers, ...dataRows])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '动态计划数据')
  const fileName = `${currentUnitLabel.value}_${pageDisplayName.value}_${startMonth.value}_${endMonth.value}.xlsx`
  XLSX.writeFile(wb, fileName)
}

onMounted(async () => {
  ensureProjectsLoaded().catch(() => {})
  window.addEventListener('resize', handleResize)
  window.addEventListener('click', handleGlobalClick)
  if (chartContainerRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      clearTimeout(resizeTimer)
      resizeTimer = setTimeout(() => {
        if (chartInstance) {
          renderChart()
        }
      }, 100)
    })
    resizeObserver.observe(chartContainerRef.value)
  }
  await initMeta()
  await fetchData()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('click', handleGlobalClick)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.dynamic-plan-view {
  min-height: 100vh;
  background-color: #f8fafc;
  color: #1e293b;
  display: flex;
  flex-direction: column;
}

.dynamic-plan-main {
  flex: 1;
  max-width: 1520px;
  width: 100%;
  margin: 0 auto;
  padding: 18px 24px 48px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.top-nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
  border: 1px solid transparent;
}

.ghost-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #334155;
}
.ghost-btn:hover:not(:disabled) {
  background: #f1f5f9;
  border-color: #94a3b8;
}

.export-btn {
  background: #1f497d;
  color: #ffffff;
}
.export-btn:hover:not(:disabled) {
  background: #153257;
}

/* 顶部 Banner */
.banner-card {
  padding: 16px 22px;
  background: linear-gradient(135deg, #ffffff 0%, #f0f4f9 100%);
  border-left: 5px solid #1f497d;
  border: 1px solid #e2e8f0;
  border-left-width: 5px;
  border-radius: 8px;
}

.banner-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.banner-title-row h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.badge-tag {
  background: #e0e7ff;
  color: #3730a3;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 12px;
}

.status-indicator {
  font-size: 12px;
  color: #10b981;
  font-weight: 600;
}

.banner-desc {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

/* 筛选区卡片 */
.filter-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.filter-group {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 90px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  padding-top: 6px;
}

.unit-pills-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.unit-pill {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.unit-pill:hover {
  border-color: #94a3b8;
  background: #f1f5f9;
}

.unit-pill.active {
  background: #1f497d;
  color: #ffffff;
  border-color: #1f497d;
  box-shadow: 0 2px 6px rgba(31, 73, 125, 0.25);
}

.month-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  flex: 1;
}

.range-selects {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-select {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  font-size: 13px;
  color: #1e293b;
  outline: none;
}
.form-select:focus {
  border-color: #1f497d;
}

.range-separator {
  color: #94a3b8;
  font-size: 12px;
}

.preset-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-btn {
  padding: 5px 10px;
  border-radius: 4px;
  border: 1px dashed #cbd5e1;
  background: transparent;
  color: #475569;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.preset-btn:hover {
  border-color: #1f497d;
  color: #1f497d;
}

.preset-btn.active {
  background: #e2e8f0;
  border-color: #1f497d;
  color: #1f497d;
  font-weight: 600;
}

.btn-import-weather {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%) !important;
  color: #15803d !important;
  border: 1px solid #86efac !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 2px rgba(21, 128, 61, 0.08);
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.btn-import-weather:hover:not(:disabled) {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%) !important;
  color: #166534 !important;
  border-color: #4ade80 !important;
  transform: translateY(-1px);
}

.btn-import-weather:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.weather-status-badge {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 4px;
  animation: dropdownFadeIn 0.2s ease;
  white-space: nowrap;
  align-self: center;
}

.weather-status-badge.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
  font-weight: 500;
}

.weather-status-badge.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  font-weight: 500;
}

/* 指标复选下拉样式 */
.metric-select-group {
  align-items: center;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
  position: relative;
}

.metric-multiselect-container {
  position: relative;
  min-width: 320px;
  max-width: 480px;
  flex: 1;
}

.multiselect-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.multiselect-trigger:hover {
  border-color: #1f497d;
}

.multiselect-trigger.is-open {
  border-color: #1f497d;
  box-shadow: 0 0 0 3px rgba(31, 73, 125, 0.12);
}

.trigger-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
}

.trigger-text .placeholder {
  color: #94a3b8;
  font-weight: normal;
}

.dropdown-arrow {
  font-size: 10px;
  color: #64748b;
  margin-left: 8px;
  transition: transform 0.2s ease;
}

.dropdown-arrow.is-open {
  transform: rotate(180deg);
}

/* 下拉展开面板 */
.multiselect-dropdown-panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  min-width: 380px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08);
  z-index: 9999;
  overflow: hidden;
  animation: dropdownFadeIn 0.15s ease;
}

@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
}

.action-btn-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-link-btn {
  background: transparent;
  border: none;
  color: #1f497d;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
}

.action-link-btn:hover {
  background: #e2e8f0;
  color: #0f2a4a;
}

.action-divider {
  color: #cbd5e1;
  font-size: 11px;
}

.selected-counter {
  color: #64748b;
  font-size: 11px;
}

.dropdown-list-scroll {
  max-height: 280px;
  overflow-y: auto;
  padding: 4px 0;
}

.dropdown-checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  cursor: pointer;
  font-size: 12px;
  color: #334155;
  transition: background 0.12s ease;
  user-select: none;
}

.dropdown-checkbox-item:hover {
  background: #f1f5f9;
}

.dropdown-checkbox-item.is-checked {
  background: #f0f7ff;
  color: #1f497d;
  font-weight: 500;
}

.item-checkbox {
  cursor: pointer;
  accent-color: #1f497d;
  width: 14px;
  height: 14px;
}

.item-name {
  flex: 1;
}

.item-unit {
  color: #94a3b8;
  font-size: 11px;
  font-weight: normal;
}

.btn-reset-metrics {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  color: #1f497d;
  font-size: 12px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-reset-metrics:hover {
  background: #e2e8f0;
  border-color: #1f497d;
}

/* KPI 统计卡片网格 */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.kpi-icon {
  font-size: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: #f1f5f9;
  flex-shrink: 0;
}

.heat-kpi .kpi-icon { background: #ffedd5; }
.coal-kpi .kpi-icon { background: #dbeafe; }
.raw-coal-kpi .kpi-icon { background: #d1fae5; }
.power-kpi .kpi-icon { background: #ede9fe; }
.water-kpi .kpi-icon { background: #cffafe; }
.efficiency-kpi .kpi-icon { background: #fef3c7; }

.kpi-info {
  flex: 1;
  min-width: 0;
}

.kpi-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  margin-bottom: 2px;
}

.kpi-value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.kpi-value {
  font-size: 19px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.3px;
}

.kpi-unit {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.kpi-meta {
  margin-top: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: #64748b;
}

.kpi-peak {
  color: #ea580c;
  font-weight: 600;
}

.kpi-extra {
  color: #059669;
}

/* 图表展示区 */
.chart-section {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 20px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  width: 100%;
  box-sizing: border-box;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
  overflow: visible;
}

.chart-tabs {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.chart-tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.chart-tab-btn:hover {
  background: #f1f5f9;
  color: #1f497d;
}

.chart-tab-btn.active {
  background: #1f497d;
  color: #ffffff;
  border-color: #1f497d;
  font-weight: 600;
}

.chart-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  overflow: visible;
}

/* 图表专属二次指标筛选下拉器 */
.chart-multiselect-dropdown {
  position: relative;
  display: inline-block;
}

.chart-dropdown-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 12px;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chart-dropdown-trigger:hover {
  background: #f8fafc;
  border-color: #1f497d;
  color: #1f497d;
}

.chart-dropdown-trigger.is-active {
  border-color: #1f497d;
  box-shadow: 0 0 0 2px rgba(31, 73, 125, 0.15);
}

.chart-trigger-icon {
  font-size: 13px;
}

.chart-trigger-text b {
  color: #1f497d;
  font-weight: 700;
}

.chart-dropdown-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  width: 320px;
  max-width: 90vw;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
  z-index: 9999;
  overflow: hidden;
  animation: dropdownFadeIn 0.15s ease;
}

.chart-dropdown-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
}

.chart-dropdown-title {
  font-weight: 600;
  color: #334155;
}

.chart-dropdown-scroll {
  max-height: 260px;
  overflow-y: auto;
  padding: 6px 8px;
}

.dropdown-empty-tip {
  padding: 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
}

.focused-metric-tag {
  font-size: 12px;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s ease;
}
.focused-metric-tag:hover {
  background: #dbeafe;
  border-color: #93c5fd;
}

.chart-count-tag {
  font-size: 12px;
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  padding: 4px 10px;
  border-radius: 6px;
  font-weight: 500;
}

.chart-range-tag {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 4px 10px;
  border-radius: 4px;
}

/* 双纵轴映射对照指引条 */
.axis-mapping-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: linear-gradient(135deg, #f0f7ff 0%, #f8fafc 50%, #fff7ed 100%);
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 8px 14px;
  margin-top: 12px;
  margin-bottom: 4px;
  box-shadow: 0 1px 3px rgba(31, 73, 125, 0.05);
  flex-wrap: wrap;
}

.axis-right-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.axis-indicator-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.axis-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2px;
  white-space: nowrap;
}

.axis-left-badge {
  background: #1f497d;
  color: #ffffff;
  box-shadow: 0 1px 2px rgba(31, 73, 125, 0.2);
}

.axis-right-badge {
  background: #ea580c;
  color: #ffffff;
  box-shadow: 0 1px 2px rgba(234, 88, 12, 0.2);
}

.axis-metric-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.axis-metric-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  font-size: 11px;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.axis-metric-pill:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.axis-metric-pill.left-metric:hover {
  border-color: #2563eb;
  color: #1d4ed8;
}

.axis-metric-pill.right-metric:hover {
  border-color: #ea580c;
  color: #c2410c;
}

.axis-metric-pill.is-focused {
  font-weight: 700;
  border-width: 1.5px;
}

.axis-metric-pill.left-metric.is-focused {
  border-color: #1f497d;
  background: #eff6ff;
  color: #1f497d;
  box-shadow: 0 0 0 2px rgba(31, 73, 125, 0.15);
}

.axis-metric-pill.right-metric.is-focused {
  border-color: #ea580c;
  background: #fff7ed;
  color: #c2410c;
  box-shadow: 0 0 0 2px rgba(234, 88, 12, 0.15);
}

.axis-temp-badge {
  background: #0284c7 !important;
  color: #ffffff !important;
  box-shadow: 0 1px 2px rgba(2, 132, 199, 0.25) !important;
}

.axis-temp-pill {
  cursor: default !important;
}
.axis-temp-pill:hover {
  transform: none !important;
  border-color: #cbd5e1 !important;
  color: #334155 !important;
  box-shadow: none !important;
}

.color-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.metric-text {
  white-space: nowrap;
}

.chart-body {
  position: relative;
  width: 100%;
  min-height: 400px;
  margin-top: 14px;
}

.echarts-container {
  width: 100%;
  min-width: 100%;
  height: 400px;
}

.chart-loading {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
  font-size: 13px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #1f497d;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 数据矩阵表格 */
.table-section {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.table-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.table-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.count-tag {
  font-size: 11px;
  background: #f1f5f9;
  color: #475569;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.table-note {
  font-size: 12px;
  color: #94a3b8;
}

.table-container {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 900px;
}

.matrix-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  padding: 10px 12px;
  border-bottom: 1px solid #cbd5e1;
  border-right: 1px solid #f1f5f9;
  white-space: nowrap;
}

.matrix-table td {
  padding: 9px 12px;
  border-bottom: 1px solid #f1f5f9;
  border-right: 1px solid #f8fafc;
  color: #334155;
}

.matrix-table tbody tr:hover td {
  background-color: #f1f5f9;
  cursor: pointer;
}

.matrix-table tbody tr.highlighted td {
  background-color: #e0f2fe;
}

.col-pinned {
  position: sticky;
  background: #ffffff;
  z-index: 2;
}

.matrix-table thead .col-pinned {
  background: #f8fafc;
  z-index: 3;
}

.matrix-table tbody tr.highlighted .col-pinned {
  background-color: #e0f2fe;
}

.col-name {
  left: 0;
  min-width: 240px;
  max-width: 320px;
  box-shadow: 2px 0 6px rgba(0, 0, 0, 0.05);
}

.metric-title {
  font-weight: 600;
  color: #0f172a;
}

.ratio-pill {
  margin-left: 6px;
  font-size: 10px;
  background: #fef3c7;
  color: #b45309;
  padding: 1px 4px;
  border-radius: 3px;
}

.rollup-pill {
  margin-left: 6px;
  font-size: 10px;
  background: #ede9fe;
  color: #6d28d9;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 500;
}

.col-month {
  min-width: 105px;
}

.cell-peak {
  background: #fff7ed !important;
}

.val-num {
  font-family: 'Consolas', monospace;
  font-weight: 500;
}

.val-ratio {
  display: block;
  font-size: 10px;
  color: #94a3b8;
  font-family: sans-serif;
}

.cell-peak .val-ratio {
  color: #ea580c;
  font-weight: 600;
}

.col-stat {
  min-width: 110px;
}

.col-total {
  background: #fafaf9;
}

.col-peak {
  min-width: 90px;
}

.peak-badge {
  display: inline-block;
  padding: 2px 6px;
  background: #ffedd5;
  color: #c2410c;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.text-center { text-align: center; }
.text-right { text-align: right; }
.font-bold { font-weight: 700; }
.text-muted { color: #cbd5e1; }

.empty-cell {
  text-align: center;
  padding: 32px;
  color: #94a3b8;
  font-size: 13px;
}

/* ---------------- 动态分解控制器与明细表格样式 ---------------- */
/* 动态分解独立切换胶囊开关 */
.decomp-toggle-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
  border-radius: 20px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  flex-shrink: 0;
}

.decomp-toggle-pill:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.decomp-toggle-pill.is-active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.decomp-toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.toggle-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  transition: all 0.2s ease;
}

.decomp-toggle-pill.is-active .toggle-dot {
  background: #2563eb;
  box-shadow: 0 0 8px #60a5fa;
}

/* 动态分解专属二级控制横栏 (排版舒展、独立一行) */
.decomp-sub-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding: 8px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  animation: fadeInDown 0.15s ease;
}

.decomp-sub-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.sub-label {
  color: #475569;
  font-weight: 600;
}

.decomp-month-select {
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #0f172a;
  outline: none;
  cursor: pointer;
  font-weight: 500;
}

.decomp-info-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  color: #334155;
}

.decomp-info-pill b {
  color: #0284c7;
}

.decomp-badge-audit {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #059669;
  border-radius: 12px;
  font-weight: 600;
}

.decomp-sub-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* 平均气温曲线切换胶囊 */
.decomp-temp-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  cursor: pointer;
  font-weight: 500;
  user-select: none;
  transition: all 0.15s ease;
}

.decomp-temp-pill:hover {
  background: #f8fafc;
  color: #0284c7;
  border-color: #93c5fd;
}

.decomp-temp-pill.is-active {
  background: #f0f9ff;
  border-color: #0284c7;
  color: #0284c7;
  font-weight: 600;
}

.decomp-temp-checkbox {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.temp-indicator-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
  transition: all 0.2s ease;
}

.decomp-temp-pill.is-active .temp-indicator-dot {
  background: #0284c7;
  box-shadow: 0 0 6px rgba(2, 132, 199, 0.6);
}

.btn-toggle-decomp-algorithm {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.btn-toggle-decomp-algorithm:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}

.btn-toggle-decomp-algorithm.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}

.btn-toggle-decomp-table {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s ease;
}

.btn-toggle-decomp-table:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}

.btn-toggle-decomp-table.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}

/* 动态分解算法与各指标 k 值模型展示面板 */
.decomp-algorithm-panel {
  margin-top: 12px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.06);
  animation: fadeInDown 0.2s ease;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 14px;
}

.panel-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.panel-badge-icon {
  font-size: 16px;
}

.panel-heading {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.panel-context-tag {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.btn-close-panel {
  padding: 3px 8px;
  font-size: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #f8fafc;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-close-panel:hover {
  background: #fee2e2;
  border-color: #fca5a5;
  color: #dc2626;
}

.panel-body-grid {
  display: grid;
  grid-template-columns: 1fr 1.35fr;
  gap: 16px;
}

@media (max-width: 1024px) {
  .panel-body-grid {
    grid-template-columns: 1fr;
  }
}

.algo-formula-col,
.algo-k-col {
  display: flex;
  flex-direction: column;
}

.algo-sub-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 10px;
}

.title-with-count {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sub-step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: #eff6ff;
  color: #2563eb;
  border-radius: 4px;
  font-weight: 800;
  font-size: 12px;
}

.k-count-badge {
  font-size: 11px;
  font-weight: 500;
  color: #0284c7;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  padding: 2px 8px;
  border-radius: 10px;
}

/* 公式卡片列表 */
.formula-cards-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.formula-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  transition: all 0.15s ease;
}

.formula-card:hover {
  border-color: #cbd5e1;
  background: #f1f5f9;
}

.formula-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.card-step-badge {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}

.card-tag {
  font-size: 11px;
  color: #475569;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  padding: 1px 6px;
  border-radius: 4px;
}

.formula-math-box {
  background: #1e293b;
  color: #38bdf8;
  padding: 6px 10px;
  border-radius: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  margin-bottom: 6px;
  letter-spacing: 0.3px;
  overflow-x: auto;
}

.formula-card-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
  margin: 0;
}

.formula-card-desc b {
  color: #1e293b;
}

.formula-card-desc code {
  background: #e2e8f0;
  color: #334155;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}

/* k 值矩阵表 */
.k-table-scroll-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  max-height: 310px;
  overflow-y: auto;
  background: #ffffff;
}

.k-dictionary-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.k-dictionary-table th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  padding: 8px 10px;
  border-bottom: 1px solid #e2e8f0;
  z-index: 1;
  font-size: 11px;
  white-space: nowrap;
}

.k-dictionary-table td {
  padding: 7px 10px;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
}

.k-dictionary-table tr:hover td {
  background: #f8fafc;
}

.k-dictionary-table tr.row-focused td {
  background: #eff6ff;
}

.td-k-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.k-badge-num {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  letter-spacing: 0.2px;
}

.k-badge-num.active {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 700;
  border: 1px solid #bfdbfe;
}

.k-badge-num.zero {
  background: #f1f5f9;
  color: #94a3b8;
  font-weight: 500;
}

.m-val-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  color: #334155;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.m-val-badge.modified {
  background: #fef3c7;
  border-color: #f59e0b;
  color: #b45309;
  font-weight: 700;
}

.k-type-pill {
  display: inline-block;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 600;
  white-space: nowrap;
}

.k-type-pill.temp-driven {
  background: #fff7ed;
  color: #ea580c;
  border: 1px solid #fed7aa;
}

.k-type-pill.baseline {
  background: #f8fafc;
  color: #64748b;
  border: 1px solid #e2e8f0;
}

.btn-k-focus {
  padding: 2px 8px;
  font-size: 11px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s ease;
}

.btn-k-focus:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}

.btn-k-focus.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #ffffff;
  font-weight: 600;
}

/* Global_admin 在线参数编辑控制样式 */
.admin-role-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  background: #fef3c7;
  border: 1px solid #fde047;
  color: #854d0e;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.algo-k-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-admin-save-all {
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 700;
  color: #ffffff;
  background: #16a34a;
  border: 1px solid #15803d;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 3px rgba(22, 163, 74, 0.3);
}

.btn-admin-save-all:hover:not(:disabled) {
  background: #15803d;
}

.btn-admin-save-all:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-admin-reset-all {
  padding: 3px 8px;
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-admin-reset-all:hover:not(:disabled) {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fca5a5;
}

.th-admin-tip {
  font-size: 10px;
  color: #2563eb;
  font-weight: normal;
  margin-left: 2px;
}

.admin-inline-input {
  width: 90px;
  padding: 2px 6px;
  font-size: 11px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  text-align: right;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: #ffffff;
  color: #0f172a;
  transition: all 0.15s ease;
}

.admin-inline-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.admin-inline-input.k-input {
  width: 98px;
}

.admin-inline-input.m-input {
  width: 78px;
  text-align: center;
}

.admin-inline-input.modified {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #b45309;
  font-weight: 700;
  box-shadow: 0 0 0 1px #f59e0b;
}

.modified-dot {
  color: #f59e0b;
  font-size: 10px;
  margin-left: 2px;
}

.k-row-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.btn-k-save-single {
  padding: 2px 5px;
  font-size: 11px;
  border: 1px solid #86efac;
  border-radius: 4px;
  background: #f0fdf4;
  color: #16a34a;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-k-save-single:hover:not(:disabled) {
  background: #16a34a;
  color: #ffffff;
}

.row-modified td {
  background-color: #fffdf5 !important;
}

.admin-param-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  animation: fadeInDown 0.2s ease;
}

.admin-param-alert.success {
  background: #f0fdf4;
  border: 1px solid #86efac;
  color: #15803d;
}

.admin-param-alert.error {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  color: #b91c1c;
}

.admin-param-alert.info {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  color: #0369a1;
}

.td-k-empty {
  text-align: center;
  padding: 24px;
  color: #94a3b8;
  font-size: 12px;
}

.decomp-meta-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  color: #0369a1;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.decomp-warning-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 16px 0;
  padding: 10px 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  color: #b45309;
  font-size: 13px;
}

.warning-icon {
  font-size: 16px;
}

.warning-text {
  flex: 1;
  font-weight: 500;
}

.btn-quick-import-weather {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 6px;
  border: 1px solid #f59e0b;
  background: #f59e0b;
  color: #ffffff;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-quick-import-weather:hover:not(:disabled) {
  background: #d97706;
}

.btn-quick-import-weather:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.decomp-detail-section {
  margin: 16px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.decomp-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.decomp-detail-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.decomp-detail-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 12px;
  color: #64748b;
}

.badge-audit {
  padding: 2px 8px;
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.decomp-table-wrapper {
  max-height: 380px;
  overflow-y: auto;
  overflow-x: auto;
  border: 1px solid #f1f5f9;
  border-radius: 6px;
}

.decomp-matrix-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: right;
}

.decomp-matrix-table th,
.decomp-matrix-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
}

.decomp-matrix-table thead th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  z-index: 2;
  box-shadow: 0 1px 0 #e2e8f0;
}

.th-date, .td-date {
  text-align: left;
  min-width: 70px;
  position: sticky;
  left: 0;
  background: #ffffff;
  z-index: 1;
}

.decomp-matrix-table thead th.th-date {
  z-index: 3;
  background: #f8fafc;
}

.th-temp, .td-temp {
  min-width: 90px;
  color: #0284c7;
}

.th-hdd, .td-hdd {
  min-width: 80px;
  color: #d97706;
}

.th-metric {
  min-width: 120px;
}

.th-k {
  display: block;
  font-size: 10px;
  font-weight: normal;
  color: #94a3b8;
}

.tr-total {
  background: #f8fafc;
  border-top: 2px solid #cbd5e1;
}

.tr-total .td-date {
  background: #f8fafc;
}

.text-primary {
  color: #2563eb;
}

.sub-target {
  display: block;
  font-size: 10px;
  font-weight: normal;
  color: #64748b;
}

.font-mono {
  font-family: 'Consolas', 'Courier New', monospace;
}

/* ---------------- 移动端窄屏手机响应式排版适配 ---------------- */
@media (max-width: 768px) {
  .dynamic-plan-main {
    padding: 10px 12px 36px;
    gap: 12px;
  }

  .top-nav-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .header-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    width: 100%;
  }

  .header-actions .btn {
    justify-content: center;
    padding: 6px 10px;
    font-size: 12px;
  }

  /* 顶部 Banner 卡片移动端紧凑化 */
  .banner-card {
    padding: 12px 14px;
    border-left-width: 4px;
  }

  .banner-title-row {
    flex-wrap: wrap;
    gap: 6px 10px;
  }

  .banner-title-row h2 {
    font-size: 16px;
  }

  .banner-desc {
    font-size: 12px;
    line-height: 1.45;
  }

  /* 筛选卡片移动端纵向流式重构 */
  .filter-card {
    padding: 12px 14px;
    gap: 12px;
  }

  .filter-group {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .filter-label {
    min-width: unset;
    padding-top: 0;
    font-size: 13px;
  }

  .unit-pills-wrapper {
    gap: 6px;
  }

  .unit-pill {
    padding: 5px 10px;
    font-size: 12px;
  }

  .month-controls {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .range-selects {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .range-selects .form-select {
    flex: 1;
    min-width: 0;
    padding: 6px 8px;
    font-size: 12px;
  }

  .preset-buttons {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .preset-btn {
    flex: 1;
    min-width: calc(33.333% - 6px);
    text-align: center;
    padding: 5px 6px;
    font-size: 11px;
  }

  .btn-import-weather {
    width: 100%;
    justify-content: center;
    padding: 6px 12px;
    font-size: 12px;
  }

  .weather-status-badge {
    align-self: flex-start;
    white-space: normal;
    word-break: break-all;
  }

  /* 指标下拉多选框移动端满宽适配 */
  .metric-multiselect-container {
    min-width: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
  }

  .multiselect-dropdown-panel {
    min-width: 0 !important;
    width: 100% !important;
    max-width: 100% !important;
    left: 0 !important;
    right: 0 !important;
  }

  .btn-reset-metrics {
    width: 100%;
    text-align: center;
    margin-top: 4px;
    padding: 6px;
  }

  /* 核心指标 KPI 统计卡片网格自适应 */
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .kpi-card {
    padding: 10px 10px;
    gap: 8px;
    flex-direction: column;
    align-items: flex-start;
  }

  .kpi-icon {
    width: 36px;
    height: 36px;
    font-size: 20px;
    border-radius: 8px;
  }

  .kpi-label {
    font-size: 11px;
  }

  .kpi-value {
    font-size: 16px;
  }

  .kpi-meta {
    flex-direction: column;
    gap: 2px;
    font-size: 10px;
  }

  /* 图表区域移动端紧凑化 */
  .chart-section {
    padding: 12px 12px 16px;
  }

  .chart-header {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .chart-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 4px;
    width: 100%;
    flex-wrap: nowrap;
  }

  .chart-tab-btn {
    padding: 5px 10px;
    font-size: 12px;
    white-space: nowrap;
  }

  .chart-actions {
    flex-wrap: wrap;
    gap: 6px;
    width: 100%;
  }

  .decomp-toggle-pill {
    padding: 4px 10px;
    font-size: 12px;
  }

  .chart-dropdown-trigger {
    padding: 4px 10px;
    font-size: 11px;
  }

  .chart-dropdown-panel {
    right: 0;
    left: auto;
    width: 280px;
    max-width: calc(100vw - 32px);
  }

  .chart-range-tag {
    font-size: 11px;
    padding: 3px 8px;
    width: 100%;
    box-sizing: border-box;
    text-align: center;
  }

  .chart-body {
    min-height: 320px;
    margin-top: 10px;
  }

  .echarts-container {
    height: 320px !important;
    min-height: 320px !important;
  }

  /* 双纵轴指引条 */
  .axis-mapping-banner {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 8px 10px;
    font-size: 11px;
  }

  .axis-right-wrapper {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    width: 100%;
  }

  .axis-indicator-group {
    width: 100%;
  }

  /* 动态分解横向二级工具栏 */
  .decomp-sub-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 10px 12px;
  }

  .decomp-sub-left {
    flex-wrap: wrap;
    gap: 6px;
    width: 100%;
  }

  .decomp-month-select {
    flex: 1;
    min-width: 110px;
  }

  .decomp-info-pill,
  .decomp-badge-audit {
    font-size: 11px;
    padding: 2px 8px;
  }

  .decomp-sub-right {
    flex-wrap: wrap;
    gap: 6px;
    width: 100%;
  }

  .decomp-temp-pill,
  .btn-toggle-decomp-algorithm,
  .btn-toggle-decomp-table {
    flex: 1;
    min-width: calc(50% - 6px);
    justify-content: center;
    text-align: center;
    padding: 5px 8px;
    font-size: 11px;
    white-space: nowrap;
  }

  /* 动态分解算法与模型面板 */
  .decomp-algorithm-panel {
    padding: 10px 12px;
  }

  .panel-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .panel-title-wrap {
    gap: 6px;
  }

  .panel-heading {
    font-size: 13px;
  }

  .algo-sub-title {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .algo-k-header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .k-table-scroll-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    max-height: 280px;
  }

  .k-dictionary-table th,
  .k-dictionary-table td {
    padding: 6px 8px;
    font-size: 11px;
  }

  .admin-inline-input {
    width: 65px;
    font-size: 11px;
  }

  /* 逐日明细表格 */
  .decomp-detail-section {
    margin: 10px 0 0;
    padding: 10px 12px;
  }

  .decomp-detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .decomp-detail-meta {
    flex-wrap: wrap;
    gap: 6px 12px;
  }

  .decomp-table-wrapper {
    -webkit-overflow-scrolling: touch;
  }

  /* 指标矩阵数据表格移动端优化 */
  .table-section {
    padding: 12px 12px;
  }

  .table-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .table-container {
    -webkit-overflow-scrolling: touch;
  }

  .matrix-table {
    font-size: 12px;
  }

  .col-name {
    min-width: 120px !important;
    max-width: 130px !important;
    padding: 6px 8px !important;
  }

  .metric-title {
    font-size: 12px;
  }

  .matrix-table th,
  .matrix-table td {
    padding: 6px 8px;
  }
}

@media (max-width: 480px) {
  .header-actions {
    grid-template-columns: 1fr;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
  }

  .kpi-card {
    padding: 8px 8px;
  }

  .kpi-value {
    font-size: 15px;
  }

  .decomp-temp-pill,
  .btn-toggle-decomp-algorithm,
  .btn-toggle-decomp-table {
    min-width: 100%;
  }
}

</style>
