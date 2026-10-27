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
            <label class="decomp-toggle-pill" :class="{ 'is-active': isDynamicDecomposeEnabled }" title="基于目标月份逐日气温HDD20与优化建议k模型，将月度计划自适应分解至每日">
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
                ✓ 逐日计划加总严格等于月计划
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

        <!-- 双纵轴对应指引条 (只要分左右轴即呈现对应指标标签名) -->
        <div v-if="chartAxisMappingInfo.showBanner" class="axis-mapping-banner">
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
          <div class="axis-indicator-group axis-right-group">
            <span class="axis-badge axis-right-badge">右纵轴 ({{ chartAxisMappingInfo.rightUnit }})</span>
            <div class="axis-metric-tags">
              <span
                v-for="m in chartAxisMappingInfo.rightMetrics"
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
                    <span class="th-k">k={{ Number(m.k_value || 0).toFixed(4) }}</span>
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
                    <span class="sub-target" title="月计划基准值">(原计划: {{ formatNumber(m.month_plan) }})</span>
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
import { getDynamicPlanMeta, getDynamicPlanData, importEnsembleTemperature, fetchDynamicDailyDecomposition } from '../services/api'

const route = useRoute()
const projectKey = String(route.params.projectKey || 'daily_report_25_26')

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
        message: `预报同步成功：共入库 ${res.inserted_or_updated} 条逐小时均值，覆盖至 ${res.end_time?.slice(0, 10)} 10:00 (type=far)`,
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

async function loadDynamicDecompositionData() {
  if (!isDynamicDecomposeEnabled.value) {
    renderChart()
    return
  }
  dynamicDecompLoading.value = true
  dynamicDecompError.value = ''
  try {
    const res = await fetchDynamicDailyDecomposition({
      projectKey,
      company: currentCompany.value,
      yearMonth: dynamicTargetMonth.value,
    })
    dynamicDecompData.value = res
    if (!res.has_full_month) {
      dynamicDecompError.value = res.message || `${dynamicTargetMonth.value} 气温数据不完整，缺少全月气温，无法执行动态分解`
    }
  } catch (err) {
    dynamicDecompError.value = err.message || '加载动态日分解数据失败'
  } finally {
    dynamicDecompLoading.value = false
    await nextTick()
    renderChart()
  }
}

function handleDynamicDecomposeToggle() {
  if (isDynamicDecomposeEnabled.value) {
    showDecompTemperature.value = true // 选中“动态分解”时，默认开启平均气温参考曲线
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
  { key: 'trend_heat_coal', label: '供热燃煤基准专题', icon: '🔥' },
]

const presetRanges = [
  { key: 'full_season', label: '🌟 全采暖期 (11~4月)', start: '2026-11', end: '2027-04' },
  { key: 'with_oct', label: '🍂 含供暖初期 (10~4月)', start: '2026-10', end: '2027-04' },
]

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '2025-2026供暖期生产日报', to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: '动态计划指标', to: null },
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
const chartAxisMappingInfo = computed(() => {
  const targets = chartMetrics.value
  if (!targets.length) {
    return {
      showBanner: false,
      hasDualAxis: false,
      leftMetrics: [],
      rightMetrics: [],
      leftUnit: '',
      rightUnit: '',
      leftKeys: new Set(),
      rightKeys: new Set(),
    }
  }

  // 统计各单位
  const unitMap = new Map()
  targets.forEach((m) => {
    const u = m.unit || '数值'
    if (!unitMap.has(u)) {
      unitMap.set(u, [])
    }
    unitMap.get(u).push(m)
  })

  // 如果仅有一种单位，无需双轴
  if (unitMap.size <= 1) {
    const onlyUnit = Array.from(unitMap.keys())[0] || ''
    return {
      showBanner: false,
      hasDualAxis: false,
      leftMetrics: targets,
      rightMetrics: [],
      leftUnit: onlyUnit,
      rightUnit: '',
      leftKeys: new Set(targets.map((m) => m.item)),
      rightKeys: new Set(),
    }
  }

  // 存在多种单位：优先将 GJ（热力行业核心生产量）定为左主轴；若无 GJ 则按指标项数最多者为主轴
  let leftUnit = ''
  if (unitMap.has('GJ')) {
    leftUnit = 'GJ'
  } else {
    let maxCount = -1
    for (const [u, list] of unitMap.entries()) {
      if (list.length > maxCount) {
        maxCount = list.length
        leftUnit = u
      }
    }
  }

  const leftMetrics = unitMap.get(leftUnit) || []
  const rightMetrics = []
  const rightUnits = []

  for (const [u, list] of unitMap.entries()) {
    if (u !== leftUnit) {
      rightMetrics.push(...list)
      rightUnits.push(u)
    }
  }

  const rightUnit = rightUnits.join(' / ')
  const leftKeys = new Set(leftMetrics.map((m) => m.item))
  const rightKeys = new Set(rightMetrics.map((m) => m.item))

  // 只要分属左右双轴（存在双轴映射），即使仅选中两个指标，也呈现对照指引横幅
  const showBanner =
    targets.length >= 2 &&
    rightMetrics.length > 0 &&
    ['dynamic_trend', 'dynamic_bar'].includes(activeChartTab.value)

  return {
    showBanner,
    hasDualAxis: rightMetrics.length > 0,
    leftMetrics,
    rightMetrics,
    leftUnit,
    rightUnit,
    leftKeys,
    rightKeys,
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
  loading.value = true
  try {
    const res = await getDynamicPlanData(projectKey, {
      company: currentCompany.value,
      start_month: startMonth.value,
      end_month: endMonth.value,
      plan_type: 'plan',
    })
    if (res.ok) {
      displayedMonths.value = res.months || []
      metricsList.value = res.metrics || []
      summaryCards.value = res.summary_cards || {}
      // 表格保持全选当前单位下的全部指标
      selectedMetricKeys.value = (res.metrics || []).map((m) => m.item)
      // 图表二次筛选默认仅选中：供热量、发电量、标煤耗量三个指标
      chartSelectedMetricKeys.value = getDefaultChartMetricKeys(res.metrics || [])
      isChartCustomized.value = false

      // 若开启动态分解模式，同步刷新动态日分解数据
      if (isDynamicDecomposeEnabled.value) {
        await loadDynamicDecompositionData()
      }
    }
  } catch (err) {
    console.error('读取动态计划数据失败:', err)
  } finally {
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
// 动态日计划分解图表渲染引擎 (基于 HDD20 与建议 k 模型)
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
          subtext: '请在右上角【图表呈现】中勾选具备建议 k 模型的指标项（如供热量、发电量、耗煤等）',
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
  const unitList = Array.from(new Set(activeMetrics.map((m) => m.unit).filter(Boolean)))
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
      yAxisIndex: useRightAxis ? 1 : 0,
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

  const yAxes = [
    {
      type: 'value',
      name: leftUnit ? `左纵轴 (${leftUnit})` : '',
      nameTextStyle: { color: '#64748b', fontSize: 11, padding: [0, 0, 4, 0] },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { formatter: (v) => formatAxisNum(v) },
    },
  ]

  if (hasDualAxis) {
    yAxes.push({
      type: 'value',
      name: `右纵轴 (${rightUnit})`,
      position: 'right',
      nameTextStyle: { color: '#64748b', fontSize: 11, padding: [0, 0, 4, 0] },
      splitLine: { show: false },
      axisLabel: { formatter: (v) => formatAxisNum(v) },
    })
  }

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
      tempYAxisIndex = 2
      yAxes.push({
        type: 'value',
        name: '平均气温 (℃)',
        position: 'right',
        offset: 55,
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
        right: hasDualAxis && includeTemp ? '8%' : (hasDualAxis || includeTemp ? '5%' : '3%'),
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
              <span style="font-weight:700;">${formatNumber(p.value)} ${hasK && w !== undefined ? `<small style="color:#64748b;font-weight:normal;">(权重 ${w})</small>` : '<small style="color:#94a3b8;font-weight:normal;">(无k·日均摊)</small>'}</span>
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
        yAxisIndex: useRightAxis ? 1 : 0,
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

    const yAxes = [
      {
        type: 'value',
        name: mapping.leftUnit ? `左纵轴 (${mapping.leftUnit})` : '',
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { formatter: (v) => formatAxisNum(v) },
      },
    ]
    if (hasDualAxis) {
      yAxes.push({
        type: 'value',
        name: mapping.rightUnit ? `右纵轴 (${mapping.rightUnit})` : '',
        splitLine: { show: false },
        axisLabel: { formatter: (v) => formatAxisNum(v) },
      })
    }

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
        grid: { left: '3%', right: hasDualAxis ? '4%' : '3%', bottom: '8%', top: '16%', containLabel: true },
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
        yAxisIndex: useRightAxis ? 1 : 0,
        barMaxWidth: targetMetrics.length > 4 ? 20 : 32,
        data: months.map((mo) => m.values[mo] ?? 0),
        itemStyle: {
          color,
          opacity: hasFocus && !isFocused ? 0.35 : 1,
          borderRadius: [4, 4, 0, 0],
        },
      }
    })

    const yAxes = [
      {
        type: 'value',
        name: mapping.leftUnit ? `左纵轴 (${mapping.leftUnit})` : '',
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { formatter: (v) => formatAxisNum(v) },
      },
    ]
    if (hasDualAxis) {
      yAxes.push({
        type: 'value',
        name: mapping.rightUnit ? `右纵轴 (${mapping.rightUnit})` : '',
        splitLine: { show: false },
        axisLabel: { formatter: (v) => formatAxisNum(v) },
      })
    }

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
        grid: { left: '3%', right: hasDualAxis ? '4%' : '3%', bottom: '8%', top: '16%', containLabel: true },
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

    const pieData = months.map((m) => ({
      name: formatMonthCn(m),
      value: target.values[m] || 0,
      pct: target.distribution?.[m] || 0,
    }))

    chartInstance.setOption(
      {
        title: {
          text: `【${target.item_cn}】各月计划负荷分布比例`,
          subtext: `全月合计 = 100% ｜ 区间总计: ${formatNumber(target.total)} ${target.unit}（在下方表格点击指标行可切换环形图分析对象）`,
          left: 'center',
          top: 10,
          textStyle: { fontSize: 15, fontWeight: 700, color: '#0f172a' },
          subtextStyle: { fontSize: 12, color: '#64748b' },
        },
        tooltip: {
          trigger: 'item',
          formatter: '{b}: <br/><b>{c}</b> ' + (target.unit || '') + ' ({d}%)',
        },
        legend: { orient: 'vertical', left: 24, top: 'middle' },
        series: [
          {
            name: `${target.item_cn}分布`,
            type: 'pie',
            radius: ['44%', '72%'],
            center: ['56%', '56%'],
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

  // 4. 模式四：供热燃煤基准专题（经典暖通双Y轴曲线）
  if (activeChartTab.value === 'trend_heat_coal') {
    const heatItem = metricsList.value.find((m) => m.item === 'amount_heat_supply')
    const stdCoalItem = metricsList.value.find((m) => m.item === 'consumption_std_coal')
    const rawCoalItem = metricsList.value.find((m) => m.item === 'consumption_amount_raw_coal')

    const heatVals = months.map((m) => heatItem?.values[m] || 0)
    const stdCoalVals = months.map((m) => stdCoalItem?.values[m] || 0)
    const rawCoalVals = months.map((m) => rawCoalItem?.values[m] || 0)

    const series = [
      {
        name: '供热量 (GJ)',
        type: 'bar',
        barMaxWidth: 38,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#f97316' },
            { offset: 1, color: '#ea580c' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        data: heatVals,
      },
      {
        name: '标煤耗量 (吨)',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 8,
        lineStyle: { width: 3, color: '#2563eb' },
        itemStyle: { color: '#2563eb' },
        data: stdCoalVals,
      },
      {
        name: '原煤耗量 (吨)',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 8,
        lineStyle: { width: 2, color: '#059669', type: 'dashed' },
        itemStyle: { color: '#059669' },
        data: rawCoalVals,
      },
    ]

    chartInstance.setOption(
      {
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          formatter: (params) => {
            let tip = `<div style="font-weight:bold;margin-bottom:6px;">${params[0]?.axisValue}</div>`
            params.forEach((p) => {
              tip += `<div style="display:flex;align-items:center;gap:8px;font-size:12px;margin:3px 0;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color};"></span>
                <span style="flex:1;">${p.seriesName}:</span>
                <span style="font-weight:bold;">${formatNumber(p.value)}</span>
              </div>`
            })
            return tip
          },
        },
        legend: { top: 10, right: 20 },
        grid: { left: '3%', right: '4%', bottom: '8%', top: '16%', containLabel: true },
        xAxis: { type: 'category', data: monthLabels, axisLabel: { interval: 0, rotate: 15 } },
        yAxis: [
          {
            type: 'value',
            name: '供热量 (GJ)',
            splitLine: { lineStyle: { color: '#f1f5f9' } },
          },
          {
            type: 'value',
            name: '煤耗量 (吨)',
            splitLine: { show: false },
          },
        ],
        series,
      },
      true,
    )
    chartInstance.resize()
  }
}

function handleResize() {
  if (chartInstance) {
    chartInstance.resize()
  }
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
  const fileName = `${currentUnitLabel.value}_动态计划指标_${startMonth.value}_${endMonth.value}.xlsx`
  XLSX.writeFile(wb, fileName)
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  window.addEventListener('click', handleGlobalClick)
  if (chartContainerRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      if (chartInstance) {
        chartInstance.resize()
      }
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

</style>
