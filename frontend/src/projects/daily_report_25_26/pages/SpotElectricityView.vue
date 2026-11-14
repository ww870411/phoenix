<template>
  <div class="spot-elec-view">
    <AppHeader />
    <main class="spot-elec-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <!-- 顶栏介绍与数据状态卡片 -->
      <section class="card elevated banner-card">
        <div class="banner-content">
          <div class="banner-title-row">
            <div class="banner-icon">⚡</div>
            <div>
              <h2 class="banner-title">辽宁省电力现货市场数据查询服务</h2>
              <p class="banner-subtitle">
                15分钟日前/实时电价、实时与日前价差走势
              </p>
            </div>
          </div>
          <div class="banner-meta">
            <span class="meta-tag">
              <span class="dot live"></span> 
              数据范围：{{ metaRangeText }}
            </span>
            <span class="meta-tag">
              已录入时序：<strong>{{ meta.total_points.toLocaleString() }}</strong> 点位 ({{ meta.total_days }} 天)
            </span>
          </div>
        </div>
      </section>

      <SpotSettlementImport v-if="canImportBills" :project-key="projectKey" @imported="fetchData" />

      <!-- 错误警告提示 -->
      <section v-if="loadError" class="card elevated error-banner">
        <div class="error-msg">⚠️ {{ loadError }}</div>
        <button class="btn ghost btn-retry" type="button" @click="fetchData">重新加载</button>
      </section>

      <!-- 控制筛选工具栏：严格分为两行（第一行模式与时间选择，第二行聚合子模式与导出过滤） -->
      <section class="card elevated control-toolbar">
        <!-- 第一行：模式选择与时间范围设定 -->
        <div class="toolbar-row toolbar-row-top">
          <!-- 模式切换：单日分时精细 vs 区间走势分析 -->
          <div class="view-mode-tabs">
            <button
              :class="['mode-tab-btn', { active: viewMode === 'single' }]"
              type="button"
              @click="switchViewMode('single')"
            >
              📅 单日分时精细
            </button>
            <button
              :class="['mode-tab-btn', { active: viewMode === 'range' }]"
              type="button"
              @click="switchViewMode('range')"
            >
              📈 区间走势分析
            </button>
          </div>

          <!-- 单日模式控制：日期选择 -->
          <div v-if="viewMode === 'single'" class="date-picker-group">
            <button class="btn icon-btn" type="button" title="前一天" @click="shiftDay(-1)">◀</button>
            <input
              v-model="selectedDate"
              type="date"
              class="form-input date-input"
              :min="meta.min_date || '2026-01-01'"
              :max="meta.max_date || undefined"
              @change="fetchData"
            />
            <button class="btn icon-btn" type="button" title="后一天" @click="shiftDay(1)">▶</button>
            <button class="btn ghost quick-btn" type="button" @click="setLatestDay">最新一天</button>
          </div>

          <!-- 区间模式控制：起止日期与快捷区间 -->
          <div v-else class="range-picker-group">
            <div class="range-inputs">
              <input
                v-model="rangeStartDate"
                type="date"
                class="form-input date-input"
                :min="meta.min_date || '2026-01-01'"
                :max="meta.max_date || undefined"
                @change="fetchData"
              />
              <span class="range-sep">至</span>
              <input
                v-model="rangeEndDate"
                type="date"
                class="form-input date-input"
                :min="meta.min_date || '2026-01-01'"
                :max="meta.max_date || undefined"
                @change="fetchData"
              />
            </div>
            <div class="quick-range-chips">
              <button class="chip-btn" type="button" @click="setQuickRange(7)">近7天</button>
              <button class="chip-btn" type="button" @click="setQuickRange(30)">近30天</button>
              <button class="chip-btn" type="button" @click="setQuickRange('all')">全部数据</button>
              <button class="btn primary-outline query-btn" type="button" @click="fetchData">查询</button>
            </div>
          </div>
        </div>

        <!-- 第二行：聚合子模式 / 粒度提示 与 操作项（负电价过滤 + 导出数据） -->
        <div class="toolbar-row toolbar-row-bottom">
          <div class="toolbar-sub-left">
            <!-- 区间聚合子模式切换：按每日平均值 vs 按每月平均值 vs 按时段平均值 vs 连续显示 -->
            <div v-if="viewMode === 'range'" class="range-submode-tabs">
              <button
                :class="['submode-btn', { active: rangeSubMode === 'daily' }]"
                type="button"
                title="按日期查看每天的日前/实时平均电价走势"
                @click="switchRangeSubMode('daily')"
              >
                📅 按每日平均值
              </button>
              <button
                :class="['submode-btn', { active: rangeSubMode === 'monthly' }]"
                type="button"
                title="按月份统计每月日前/实时平均电价走势"
                @click="switchRangeSubMode('monthly')"
              >
                🗓️ 按每月平均值
              </button>
              <button
                :class="['submode-btn', { active: rangeSubMode === 'period' }]"
                type="button"
                title="统计选定日期区间内每个15分钟时段（00:15~24:00共96点）的平均电价曲线"
                @click="switchRangeSubMode('period')"
              >
                ⏰ 按时段平均值 (0:15~24:00)
              </button>
              <button
                :class="['submode-btn', { active: rangeSubMode === 'continuous' }]"
                type="button"
                title="从区间首个时段至最后一个时段连续完整展现每一个15分钟点位，不做聚合统计"
                @click="switchRangeSubMode('continuous')"
              >
                〰️ 连续显示
              </button>
            </div>
            <!-- 单日模式粒度说明提示 -->
            <div v-else class="single-mode-hint">
              <span class="hint-badge">⏱️ 15分钟高精分时</span>
              <span class="hint-text">全天 96 个交易结算时序点位</span>
            </div>
          </div>

          <div class="toolbar-right">
            <div class="plant-sales-filter-group">
              <label class="checkbox-filter plant-sales-toggle" :class="{ 'is-disabled': !canShowPlantSales }"
                :title="hasPlantSalesData ? '显示上网电量曲线（支持全部或单厂筛选），缺失数据的时段断开' : '所选日期范围暂无电厂上网电量数据'">
                <input v-model="showPlantSales" type="checkbox" :disabled="!canShowPlantSales" />
                <span class="checkbox-label">显示两厂上网电量</span>
              </label>
              <div v-if="showPlantSales && canShowPlantSales" class="plant-sales-scope-tabs" role="group" aria-label="上网电量电厂筛选">
                <button
                  v-for="opt in plantSalesScopeOptions"
                  :key="opt.key"
                  type="button"
                  :class="['scope-btn', { active: plantSalesScope === opt.key }]"
                  :title="opt.title"
                  @click="plantSalesScope = opt.key"
                >
                  <span v-if="opt.color" class="scope-dot" :style="{ backgroundColor: opt.color }"></span>
                  <span>{{ opt.label }}</span>
                </button>
              </div>
            </div>
            <!-- 负电价高亮过滤 -->
            <label class="checkbox-filter" title="仅展示出现负电价的时段区间（保持横轴全天刻度不变）">
              <input v-model="onlyNegative" type="checkbox" @change="onNegativeFilterChange" />
              <span class="checkbox-label">❄️ 仅负电价时段</span>
            </label>

            <!-- Global_admin 系统控制选项按钮 (仅 Global_admin 可见) -->
            <button
              v-if="isGlobalAdmin"
              class="btn admin-control-btn"
              type="button"
              title="设置现货数据每日自动拉取开关、时间、间隔或手动实时拉取 (仅 Global_admin 可操作)"
              @click="openAdminControlModal"
            >
              ⚙️ 系统控制选项
            </button>

            <!-- 导出按钮 -->
            <button
              class="btn primary export-btn"
              type="button"
              :disabled="loading || (viewMode === 'range' && rangeSubMode === 'period' ? !periodTrends.length : viewMode === 'range' && rangeSubMode === 'monthly' ? !monthlyTrends.length : viewMode === 'range' && rangeSubMode === 'daily' && dailyTableSubMode === 'dailySummary' ? !dailyTrends.length : !points.length)"
              @click="exportCurrentData"
            >
              📥 导出数据 (Excel/CSV)
            </button>
          </div>
        </div>
      </section>

      <!-- 核心指标大盘 KPI 卡片 -->
      <section class="kpi-section">
        <!-- 价格与价差指标网格 -->
        <div class="kpi-grid kpi-grid-prices">
          <div class="kpi-card">
            <div class="kpi-title">
              <span>日前均价</span>
              <span class="kpi-unit">元/MWh</span>
            </div>
            <div class="kpi-value text-blue">
              {{ formatNum(summary?.avg_day_ahead_price) }}
            </div>
            <div class="kpi-sub">
              <span>最高: {{ formatNum(summary?.max_day_ahead_price) }}</span>
              <span>最低: {{ formatNum(summary?.min_day_ahead_price) }}</span>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-title">
              <span>实时均价</span>
              <span class="kpi-unit">元/MWh</span>
            </div>
            <div class="kpi-value text-orange">
              {{ formatNum(summary?.avg_real_time_price) }}
            </div>
            <div class="kpi-sub">
              <span>最高: {{ formatNum(summary?.max_real_time_price) }}</span>
              <span>最低: {{ formatNum(summary?.min_real_time_price) }}</span>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-title">
              <span>平均价差 (实时-日前)</span>
              <span class="kpi-unit">元/MWh</span>
            </div>
            <div :class="['kpi-value', getSpreadColorClass(summary?.avg_price_spread)]">
              {{ (summary?.avg_price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(summary?.avg_price_spread) }}
            </div>
            <div class="kpi-sub">
              <span :title="`选定区间内实时电价高于日前电价的最大差值：${(summary?.max_price_spread ?? 0) > 0 ? '+' : ''}${formatNum(summary?.max_price_spread)} 元/MWh`">
                最大正价差: {{ (summary?.max_price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(summary?.max_price_spread) }}
              </span>
              <span :title="`选定区间内实时电价低于日前电价的最大差值：${formatNum(summary?.min_price_spread)} 元/MWh`">
                最大负价差: {{ formatNum(summary?.min_price_spread) }}
              </span>
            </div>
          </div>

          <div class="kpi-card">
            <div class="kpi-title">
              <span>负电价时点数</span>
              <span class="kpi-unit">个时段 (15min)</span>
            </div>
            <div class="kpi-value text-blue">
              {{ summary?.negative_price_points ?? 0 }}
            </div>
            <!-- 单日模式：展示时段占比与分子分母 -->
            <div v-if="viewMode === 'single'" class="kpi-sub">
              <span>占全天时段:</span>
              <span v-if="(summary?.negative_price_points ?? 0) > 0" class="badge-blue">
                {{ negativePointRatioText }} ({{ summary?.negative_price_points ?? 0 }}/{{ totalQueryPoints.toLocaleString() }})
              </span>
              <span v-else class="text-muted">
                0.0% (0/{{ totalQueryPoints.toLocaleString() }})
              </span>
            </div>

            <!-- 区间走势分析：单行双指标（左侧时段占比，右侧天数及占比），高度与前序卡片严丝合缝对齐 -->
            <div
              v-else
              class="kpi-sub kpi-sub-dual"
            >
              <span
                class="sub-item"
                :title="`选定区间负电价时点数：${summary?.negative_price_points ?? 0}点，占总查询时段(${totalQueryPoints.toLocaleString()}点)的 ${negativePointRatioText}`"
              >
                时段占比: <strong class="text-blue">{{ negativePointRatioText }}</strong>
              </span>
              <span
                class="sub-item"
                :title="`选定区间出现负电价的天数：${negativeDaysCount}天，占总查询天数(${totalQueryDays}天)的 ${negativeDaysRatioText}`"
              >
                天数: <span v-if="negativeDaysCount > 0" class="badge-blue">{{ negativeDaysCount }}天 (占比{{ negativeDaysRatioText }})</span>
                <span v-else class="text-muted">0天 (占比0.0%)</span>
              </span>
            </div>
          </div>
        </div>

        <!-- 两厂量价测算基准切换与卡片并排展示 -->
        <div class="sales-basis-bar">
          <div class="sales-basis-label">
            <span>两厂量价测算基准：</span>
            <span :class="['basis-status-badge', salesPriceBasis === 'day_ahead' ? 'is-da' : 'is-rt']">
              {{ salesPriceBasis === 'day_ahead' ? '日前电价（参考测算）' : '账单实时电价' }}
            </span>
            <span v-if="salesPriceBasis === 'day_ahead'" class="basis-hint">
              每时段电费 = 上网电量 × 该时段日前电价（合约差价保持不变，仅供对比参考）
            </span>
          </div>
          <div class="basis-tabs" role="group" aria-label="两厂量价测算基准">
            <button
              type="button"
              :class="['basis-btn', { active: salesPriceBasis === 'real_time' }]"
              title="按日账单省内实时电价结算口径展示"
              @click="salesPriceBasis = 'real_time'"
            >
              实时电价（账单）
            </button>
            <button
              type="button"
              :class="['basis-btn', { active: salesPriceBasis === 'day_ahead' }]"
              title="将每时段单价替换为日前电价测算电费与加权均价，供复盘参考"
              @click="salesPriceBasis = 'day_ahead'"
            >
              日前电价（参考测算）
            </button>
          </div>
        </div>

        <!-- 两厂量价并排展示，缺失值弱化，电费按整数元显示。 -->
        <div class="kpi-grid kpi-grid-sales">
          <div
            v-for="plant in plantCardMetrics"
            :key="plant.key"
            :class="['kpi-card', 'plant-card', { 'is-da-basis': salesPriceBasis === 'day_ahead' }]"
          >
            <div class="plant-heading">
              <div class="plant-title-wrap">
                <strong>{{ plant.name }}</strong>
                <span v-if="salesPriceBasis === 'day_ahead'" class="basis-ref-tag">日前测算</span>
              </div>
              <span>{{ plant.units }}</span>
            </div>
            <dl class="plant-metrics">
              <div>
                <dt>售电量</dt>
                <dd :class="{ 'metric-empty': plant.sales == null }">{{ formatPlantMetric(plant.sales, 'MWh') }}</dd>
              </div>
              <div :title="plant.spotFeeTooltip">
                <dt>{{ viewMode === 'single' ? '当日' : '区间' }}现货电费</dt>
                <dd :class="{ 'metric-empty': plant.spotFee == null }">
                  {{ formatPlantMetric(plant.spotFee, '元') }}
                  <span
                    v-if="salesPriceBasis === 'day_ahead' && plant.spotFee != null && plant.spotFeeDiff != null"
                    :class="['spot-fee-diff', getSpreadColorClass(plant.spotFeeDiff)]"
                  >(较实时 {{ formatSignedFeeDiff(plant.spotFeeDiff) }})</span>
                </dd>
              </div>
              <div title="逐机组、逐15分钟计算合约差价电量 × 合约差价电价，再求和">
                <dt>{{ viewMode === 'single' ? '当日' : '区间' }}合约差价电费</dt>
                <dd :class="{ 'metric-empty': plant.contractFee == null }">{{ formatPlantMetric(plant.contractFee, '元') }}</dd>
              </div>
              <div :title="plant.revenueTooltip">
                <dt>{{ viewMode === 'single' ? '当日' : '区间' }}电量电费收入</dt>
                <dd :class="{ 'metric-empty': plant.revenueFee == null }">{{ formatPlantMetric(plant.revenueFee, '元') }}</dd>
              </div>
              <div :title="plant.avgPriceTooltip">
                <dt>平均现货电价</dt>
                <dd :class="{ 'metric-empty': plant.avgSpotPrice == null }">
                  {{ formatPlantMetric(plant.avgSpotPrice, '元/MWh') }}
                  <span v-if="salesPriceBasis === 'real_time' && plant.avgSpotPrice != null" class="plant-price-difference">({{ formatSpotPriceRate(plant.diffRate) }})</span>
                  <span
                    v-else-if="salesPriceBasis === 'day_ahead' && plant.avgSpotPrice != null && plant.spotPriceDiff != null"
                    :class="['spot-fee-diff', getSpreadColorClass(plant.spotPriceDiff)]"
                  >(较实时 {{ formatSignedPriceDiff(plant.spotPriceDiff) }})</span>
                </dd>
              </div>
            </dl>
            <div
              v-if="plant.corrDayAhead || plant.corrRealTime"
              class="plant-corr-footer"
              title="波形相关系数 (r)：+1完全同向随电价起伏，0无联动，-1反向；多日查询时优先展示按日去均值后的日内调峰相关度，以排除供热负荷变化干扰"
            >
              <div class="plant-corr-label-group">
                <span class="plant-corr-title">波形相关系数</span>
                <span class="plant-corr-meaning">+1完全同向 / 0无联动 / -1反向</span>
              </div>
              <div class="plant-corr-badges">
                <span v-if="plant.corrDayAhead" class="plant-corr-pill is-da">
                  <span class="pill-basis">对日前</span>
                  <strong :class="getSpreadColorClass(plant.corrDayAhead.primary)">
                    {{ formatPlantCorrelation(plant.corrDayAhead) }}
                  </strong>
                  <span v-if="plant.corrDayAhead.sub != null" class="pill-global">
                    (全局 {{ formatCorrelationR(plant.corrDayAhead.sub, true) }})
                  </span>
                </span>
                <span v-if="plant.corrRealTime" class="plant-corr-pill is-rt">
                  <span class="pill-basis">对实时</span>
                  <strong :class="getSpreadColorClass(plant.corrRealTime.primary)">
                    {{ formatPlantCorrelation(plant.corrRealTime) }}
                  </strong>
                  <span v-if="plant.corrRealTime.sub != null" class="pill-global">
                    (全局 {{ formatCorrelationR(plant.corrRealTime.sub, true) }})
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 现货单价区间 · 上网电量分布分析下拉信息窗 (当两厂机组有数据时显示) -->
      <section v-if="hasPlantSalesData" class="card elevated price-dist-window">
        <!-- 信息窗顶栏操作栏 -->
        <div class="dist-header" @click="isDistributionWindowOpen = !isDistributionWindowOpen">
          <div class="dist-title-group">
            <span class="dist-icon">⚡</span>
            <div>
              <div class="dist-title-row">
                <h4 class="dist-title">现货单价区间 · 上网电量分布分析</h4>
                <span class="dist-badge">{{ salesPriceBasis === 'day_ahead' ? '按日前电价 · 供分析参考' : '按实时电价 · 供分析参考' }}</span>
              </div>
              <p class="dist-subtitle">
                按现货单价区间透视所选期间发电机组在负电价、低谷、常规平段及顶峰高价期的上网电量分布与占比结构
              </p>
            </div>
          </div>

          <!-- 控制区：电厂切换胶囊与折叠开关 -->
          <div class="dist-controls" @click.stop>
            <div class="dist-capsule-tabs">
              <button
                type="button"
                class="capsule-btn"
                :class="{ active: selectedDistributionPlant === 'all' }"
                @click="selectedDistributionPlant = 'all'"
              >
                两厂总计
              </button>
              <button
                type="button"
                class="capsule-btn"
                :class="{ active: selectedDistributionPlant === 'xianghai' }"
                @click="selectedDistributionPlant = 'xianghai'"
              >
                香海热电厂 (4台机)
              </button>
              <button
                type="button"
                class="capsule-btn"
                :class="{ active: selectedDistributionPlant === 'beihai' }"
                @click="selectedDistributionPlant = 'beihai'"
              >
                北海热电厂 (3台机)
              </button>
            </div>

            <button
              type="button"
              class="dist-toggle-btn"
              :title="isDistributionWindowOpen ? '收起分析窗' : '展开分析窗'"
              @click="isDistributionWindowOpen = !isDistributionWindowOpen"
            >
              <span>{{ isDistributionWindowOpen ? '收起分析窗' : '展开分析窗' }}</span>
              <span class="chevron" :class="{ 'is-open': isDistributionWindowOpen }">▼</span>
            </button>
          </div>
        </div>

        <!-- 折叠状态下的单行摘要小横条 -->
        <div v-if="!isDistributionWindowOpen" class="dist-summary-strip" @click="isDistributionWindowOpen = true">
          <span class="summary-prefix">当前电量分布概览：</span>
          <div class="summary-chips">
            <span
              v-for="item in plantDistributionStats.intervals"
              :key="item.key"
              class="summary-chip"
              :style="{ backgroundColor: item.bgColor, borderColor: item.borderColor, color: item.textColor }"
            >
              <strong>{{ item.label }}</strong>
              <span>{{ item.ratioFormatted }}</span>
              <span class="chip-mwh">({{ item.salesFormatted }} MWh)</span>
            </span>
          </div>
        </div>

        <!-- 展开内容区域 -->
        <div v-show="isDistributionWindowOpen" class="dist-body">
          <!-- 1. 多色连续堆叠电量占比可视化条 -->
          <div class="stacked-bar-container">
            <div class="stacked-bar-meta">
              <span class="meta-label">
                <strong>{{ selectedDistributionPlant === 'all' ? '两厂总计' : selectedDistributionPlant === 'xianghai' ? '香海热电厂' : '北海热电厂' }}</strong>
                期间总上网电量：<strong>{{ plantDistributionStats.totalSalesFormatted }} MWh</strong>
                <span class="meta-points">({{ plantDistributionStats.totalPoints }} 时点)</span>
              </span>
              <span class="meta-legend">
                <span v-for="item in plantDistributionStats.intervals" :key="item.key" class="legend-dot-item">
                  <span class="legend-dot" :style="{ backgroundColor: item.color }"></span>
                  {{ item.label }}: {{ item.ratioFormatted }}
                </span>
              </span>
            </div>

            <!-- 堆叠分布横条 -->
            <div class="stacked-bar">
              <div
                v-for="item in plantDistributionStats.intervals"
                :key="item.key"
                class="bar-segment"
                :style="{
                  width: `${Math.max(item.ratio, item.sales > 0 ? 0.8 : 0)}%`,
                  backgroundColor: item.color,
                }"
                :title="`${item.name} ${item.label}：电量 ${item.salesFormatted} MWh，占比 ${item.ratioFormatted}，时段 ${item.pointCount} 点`"
              >
                <span v-if="item.ratio >= 8" class="segment-text">
                  {{ item.label }} · {{ item.ratioFormatted }}
                </span>
              </div>
            </div>
          </div>

          <!-- 2. 四宫格区间指标卡 -->
          <div class="interval-cards-grid">
            <div
              v-for="item in plantDistributionStats.intervals"
              :key="item.key"
              class="interval-card"
              :style="{ borderTopColor: item.color, backgroundColor: item.bgColor }"
            >
              <div class="card-head">
                <span class="range-badge" :style="{ backgroundColor: item.color }">{{ item.label }} {{ item.unit }}</span>
                <span class="range-tag">{{ item.desc }}</span>
              </div>
              <div class="card-ratio" :style="{ color: item.color }">
                {{ item.ratioFormatted }}
              </div>
              <div class="card-metric-list">
                <div class="metric-row">
                  <span class="m-label">上网电量:</span>
                  <strong class="m-val">{{ item.salesFormatted }} MWh</strong>
                </div>
                <div class="metric-row">
                  <span class="m-label">覆盖时段:</span>
                  <span class="m-val">{{ item.pointCount }} 点 ({{ item.pointRatioFormatted }})</span>
                </div>
                <div class="metric-row">
                  <span class="m-label">加权结算均价:</span>
                  <span class="m-val">{{ item.avgPriceFormatted }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 3. 机组明细穿透折叠抽屉 -->
          <div class="unit-breakdown-section">
            <button
              type="button"
              class="breakdown-toggle-btn"
              @click="showUnitBreakdown = !showUnitBreakdown"
            >
              <span>{{ showUnitBreakdown ? '▼ 收起各机组区间电量明细' : '▶ 查看各机组区间电量穿透明细' }}</span>
              <span class="breakdown-hint">包含各机组在不同电价区间的具体发电出力与占比</span>
            </button>

            <div v-if="showUnitBreakdown" class="unit-breakdown-table-wrap">
              <table class="unit-breakdown-table">
                <thead>
                  <tr>
                    <th style="width: 140px;">机组名称</th>
                    <th style="width: 120px;">总上网电量</th>
                    <th style="width: 130px;">综合加权均价</th>
                    <th>[-100, 0) 负电价</th>
                    <th>[0, 200) 低电价</th>
                    <th>[200, 400) 常规基准</th>
                    <th>>= 400 高电价</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="unit in plantDistributionStats.unitStats" :key="unit.key">
                    <td class="unit-name-cell">
                      <strong>{{ unit.name }}</strong>
                    </td>
                    <td class="unit-total-cell">{{ unit.totalSalesFormatted }} MWh</td>
                    <td class="unit-avg-cell">{{ unit.avgPriceFormatted }}</td>
                    <td class="cell-neg">
                      {{ unit.intervals.neg.salesFormatted }} MWh
                      <span class="cell-ratio">({{ unit.intervals.neg.ratio }})</span>
                    </td>
                    <td class="cell-low">
                      {{ unit.intervals.low.salesFormatted }} MWh
                      <span class="cell-ratio">({{ unit.intervals.low.ratio }})</span>
                    </td>
                    <td class="cell-mid">
                      {{ unit.intervals.mid.salesFormatted }} MWh
                      <span class="cell-ratio">({{ unit.intervals.mid.ratio }})</span>
                    </td>
                    <td class="cell-high">
                      {{ unit.intervals.high.salesFormatted }} MWh
                      <span class="cell-ratio">({{ unit.intervals.high.ratio }})</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- 可视化图表区 -->
      <section class="card elevated chart-container-card">
        <div class="chart-header">
          <div class="chart-title-wrap">
            <h3 class="chart-title">
              {{
                viewMode === 'single'
                  ? `【${selectedDate}】辽宁省统一结算点电价数据`
                  : rangeSubMode === 'daily'
                    ? `【${rangeStartDate} 至 ${rangeEndDate}】辽宁省统一结算点电价数据（日均走势）`
                    : rangeSubMode === 'monthly'
                      ? `【${rangeStartDate} 至 ${rangeEndDate}】辽宁省统一结算点电价数据（月均走势）`
                      : rangeSubMode === 'continuous'
                        ? `【${rangeStartDate} 至 ${rangeEndDate}】辽宁省统一结算点电价数据（连续15分钟原始走势）`
                        : `【${rangeStartDate} 至 ${rangeEndDate}】辽宁省统一结算点电价数据（时段均值 00:15 ~ 24:00）`
              }}
            </h3>
            <span class="chart-badge">
              {{
                viewMode === 'single'
                  ? '时点颗粒度: 15分钟'
                  : rangeSubMode === 'daily'
                    ? `按日聚合 (${dailyTrends.length} 天)`
                    : rangeSubMode === 'monthly'
                      ? `按月聚合 (${monthlyTrends.length} 个月)`
                      : rangeSubMode === 'continuous'
                        ? `连续原始时序 (${points.length.toLocaleString()} 点位)`
                        : '时段聚合平均 (96 点位)'
              }}
            </span>
          </div>
          <!-- 动态指标开关选择器：允许自由勾选显隐，默认显示日前与实时电价 -->
          <div class="chart-indicators-selector">
            <span class="selector-label">图表指标：</span>
            <!-- 单日模式及区间连续显示模式指标切换 -->
            <template v-if="viewMode === 'single' || rangeSubMode === 'continuous'">
              <button
                :class="['indicator-chip', 'chip-blue', { active: visibleSeries.dayAhead }]"
                type="button"
                title="点击切换日前电价曲线显示"
                @click="toggleSeries('dayAhead')"
              >
                <span class="chip-dot"></span>
                日前电价
              </button>
              <button
                :class="['indicator-chip', 'chip-orange', { active: visibleSeries.realTime }]"
                type="button"
                title="点击切换实时电价曲线显示"
                @click="toggleSeries('realTime')"
              >
                <span class="chip-dot"></span>
                实时电价
              </button>
              <button
                :class="['indicator-chip', 'chip-green', { active: visibleSeries.spread }]"
                type="button"
                title="点击切换价差（实时-日前）柱状图显示"
                @click="toggleSeries('spread')"
              >
                <span class="chip-bar"></span>
                价差（实时-日前）
              </button>
            </template>
            <!-- 区间模式：按每日平均值 -->
            <template v-else-if="rangeSubMode === 'daily'">
              <button
                :class="['indicator-chip', 'chip-blue', { active: visibleRangeSeries.dayAheadAvg }]"
                type="button"
                title="点击切换日前日均价曲线显示"
                @click="toggleRangeSeries('dayAheadAvg')"
              >
                <span class="chip-dot"></span>
                日前日均价
              </button>
              <button
                :class="['indicator-chip', 'chip-orange', { active: visibleRangeSeries.realTimeAvg }]"
                type="button"
                title="点击切换实时日均价曲线显示"
                @click="toggleRangeSeries('realTimeAvg')"
              >
                <span class="chip-dot"></span>
                实时日均价
              </button>
              <button
                :class="['indicator-chip', 'chip-red', { active: visibleRangeSeries.negativeCount }]"
                type="button"
                title="点击切换负电价时点数显示"
                @click="toggleRangeSeries('negativeCount')"
              >
                <span class="chip-bar"></span>
                负电价时点数
              </button>
            </template>
            <!-- 区间模式：按每月平均值 -->
            <template v-else-if="rangeSubMode === 'monthly'">
              <button
                :class="['indicator-chip', 'chip-blue', { active: visibleMonthlySeries.dayAheadAvg }]"
                type="button"
                title="点击切换日前月均价曲线显示"
                @click="toggleMonthlySeries('dayAheadAvg')"
              >
                <span class="chip-dot"></span>
                日前月均价
              </button>
              <button
                :class="['indicator-chip', 'chip-orange', { active: visibleMonthlySeries.realTimeAvg }]"
                type="button"
                title="点击切换实时月均价曲线显示"
                @click="toggleMonthlySeries('realTimeAvg')"
              >
                <span class="chip-dot"></span>
                实时月均价
              </button>
              <button
                :class="['indicator-chip', 'chip-green', { active: visibleMonthlySeries.spread }]"
                type="button"
                title="点击切换现货月均价差柱状图显示"
                @click="toggleMonthlySeries('spread')"
              >
                <span class="chip-bar"></span>
                月均价差
              </button>
              <button
                :class="['indicator-chip', 'chip-red', { active: visibleMonthlySeries.negativeCount }]"
                type="button"
                title="点击切换负电价时点数显示"
                @click="toggleMonthlySeries('negativeCount')"
              >
                <span class="chip-bar"></span>
                负电价时点数
              </button>
            </template>
            <!-- 区间模式：按时段平均值 (0:15~24:00) -->
            <template v-else>
              <button
                :class="['indicator-chip', 'chip-blue', { active: visiblePeriodSeries.dayAheadAvg }]"
                type="button"
                title="点击切换日前时段均价曲线显示"
                @click="togglePeriodSeries('dayAheadAvg')"
              >
                <span class="chip-dot"></span>
                日前均价
              </button>
              <button
                :class="['indicator-chip', 'chip-orange', { active: visiblePeriodSeries.realTimeAvg }]"
                type="button"
                title="点击切换实时时段均价曲线显示"
                @click="togglePeriodSeries('realTimeAvg')"
              >
                <span class="chip-dot"></span>
                实时均价
              </button>
              <button
                :class="['indicator-chip', 'chip-green', { active: visiblePeriodSeries.spread }]"
                type="button"
                title="点击切换时段平均价差柱状图显示"
                @click="togglePeriodSeries('spread')"
              >
                <span class="chip-bar"></span>
                平均价差
              </button>
              <button
                :class="['indicator-chip', 'chip-red', { active: visiblePeriodSeries.negativeDays }]"
                type="button"
                title="点击切换负电价发生天数柱状图显示"
                @click="togglePeriodSeries('negativeDays')"
              >
                <span class="chip-bar"></span>
                负电价天数
              </button>
            </template>
          </div>
        </div>

        <!-- 图表主体容器：chartRef 始终保持 100% 宽度，loading 采用绝对定位半透明遮罩 -->
        <div class="chart-wrapper">
          <div v-show="loading" class="chart-loading-overlay">
            <div class="spinner"></div>
            <span>正在更新电价图表…</span>
          </div>
          <div ref="chartRef" class="main-chart"></div>
        </div>
      </section>

      <!-- 明细表格与手机端微卡片区域 -->
      <section class="card elevated table-card">
        <header class="table-card-header">
          <div class="table-title-group">
            <h3>数据详细列表</h3>
            <span class="table-count">
              {{
                viewMode === 'range' && rangeSubMode === 'period'
                  ? `共 ${displayedPeriodTrends.length} 个时段聚合记录 (00:15 ~ 24:00)`
                  : viewMode === 'range' && rangeSubMode === 'monthly'
                    ? `共 ${displayedMonthlyTrends.length} 个月份聚合记录`
                    : viewMode === 'range' && rangeSubMode === 'daily' && dailyTableSubMode === 'dailySummary'
                      ? `共 ${displayedDailyTrends.length} 天日均聚合记录`
                      : `共 ${displayedPoints.length} 条 15 分钟时序记录 (第 ${currentPage}/${totalPages} 页)`
              }}
            </span>
          </div>

          <!-- 区间日度走势下的表格子视图切换 (按日均价汇总 vs 15分钟分时明细) -->
          <div v-if="viewMode === 'range' && rangeSubMode === 'daily'" class="table-submode-switch">
            <button
              :class="['table-toggle-btn', { active: dailyTableSubMode === 'dailySummary' }]"
              type="button"
              title="按天查看每一天的日前/实时均价及售电汇总"
              @click="dailyTableSubMode = 'dailySummary'"
            >
              📅 每日均价汇总
            </button>
            <button
              :class="['table-toggle-btn', { active: dailyTableSubMode === 'pointsDetail' }]"
              type="button"
              title="穿透查看区间内所有 15 分钟交易时序点位明细 (带分页)"
              @click="dailyTableSubMode = 'pointsDetail'"
            >
              ⏱️ 15分钟分时明细
            </button>
          </div>

          <!-- 手机端专属切换：卡片流 vs 大表格 -->
          <div class="mobile-layout-switch">
            <button
              :class="['switch-btn', { active: mobileLayout === 'card' }]"
              type="button"
              @click="mobileLayout = 'card'"
            >
              微卡片
            </button>
            <button
              :class="['switch-btn', { active: mobileLayout === 'table' }]"
              type="button"
              @click="mobileLayout = 'table'"
            >
              紧凑大表
            </button>
          </div>
        </header>

        <!-- 手机端专属微卡片视图 (仅在手机窄屏且未切换为紧凑大表时显示) -->
        <div v-if="isMobileScreen && mobileLayout === 'card'" class="mobile-cards-wrap">
          <div v-if="loading" class="empty-cards">
            <div class="spinner"></div>
            <span>时序数据加载中…</span>
          </div>
          <!-- 1. 时段聚合模式微卡片 -->
          <template v-else-if="viewMode === 'range' && rangeSubMode === 'period'">
            <div v-if="!displayedPeriodTrends.length" class="empty-cards">
              未查询到符合条件的电力现货时段数据
            </div>
            <div
              v-for="item in displayedPeriodTrends"
              v-else
              :key="`period_card_${item.point_index}`"
              :class="['spot-mobile-card', { 'is-negative': isPeriodNegative(item) }]"
            >
              <div class="card-top-row">
                <div class="time-block">
                  <span class="point-badge">#{{ item.point_index }}</span>
                  <span class="time-text">{{ item.time_label }}</span>
                  <span class="period-text">{{ item.period_start_time }}~{{ item.period_end_time }}</span>
                </div>
                <div class="status-wrap">
                  <span v-if="isPeriodNegative(item)" class="badge-neg">❄️ 负电价</span>
                </div>
              </div>

              <div class="card-price-grid">
                <div class="price-cell">
                  <span class="cell-label">日前均价</span>
                  <span :class="['cell-val text-blue', { 'val-neg': item.avg_day_ahead_price < 0 }]">
                    {{ formatNum(item.avg_day_ahead_price) }}
                  </span>
                </div>
                <div class="price-cell">
                  <span class="cell-label">实时均价</span>
                  <span :class="['cell-val text-orange', { 'val-neg': item.avg_real_time_price < 0 }]">
                    {{ formatNum(item.avg_real_time_price) }}
                  </span>
                </div>
                <div class="price-cell">
                  <span class="cell-label">平均价差</span>
                  <span :class="['cell-val', getSpreadColorClass(item.avg_price_spread)]">
                    {{ (item.avg_price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(item.avg_price_spread) }}
                  </span>
                </div>
              </div>

              <div class="card-bottom-info">
                <span>负电价: {{ item.negative_days_count }} 天</span>
                <span>北海均值: {{ item.avg_beihai_sales != null ? `${item.avg_beihai_sales} MWh` : '—' }}</span>
              </div>
            </div>
          </template>

          <!-- 2. 月份聚合模式微卡片 -->
          <template v-else-if="viewMode === 'range' && rangeSubMode === 'monthly'">
            <div v-if="!displayedMonthlyTrends.length" class="empty-cards">
              未查询到符合条件的电力现货月度数据
            </div>
            <div
              v-for="item in displayedMonthlyTrends"
              v-else
              :key="`monthly_card_${item.month_label}`"
              :class="['spot-mobile-card', { 'is-negative': isMonthlyNegative(item) }]"
            >
              <div class="card-top-row">
                <div class="time-block">
                  <span class="point-badge">🗓️ 月份</span>
                  <span class="time-text">{{ item.month_label }}</span>
                  <span class="period-text">{{ item.day_count }} 天 / {{ item.point_count }} 点位</span>
                </div>
                <div class="status-wrap">
                  <span v-if="isMonthlyNegative(item)" class="badge-neg">❄️ 负电价 ({{ item.negative_count }}点)</span>
                </div>
              </div>

              <div class="card-price-grid">
                <div class="price-cell">
                  <span class="cell-label">日前月均价</span>
                  <span :class="['cell-val text-blue', { 'val-neg': item.avg_day_ahead_price < 0 }]">
                    {{ formatNum(item.avg_day_ahead_price) }}
                  </span>
                </div>
                <div class="price-cell">
                  <span class="cell-label">实时月均价</span>
                  <span :class="['cell-val text-orange', { 'val-neg': item.avg_real_time_price < 0 }]">
                    {{ formatNum(item.avg_real_time_price) }}
                  </span>
                </div>
                <div class="price-cell">
                  <span class="cell-label">月均价差</span>
                  <span :class="['cell-val', getSpreadColorClass(item.avg_price_spread)]">
                    {{ (item.avg_price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(item.avg_price_spread) }}
                  </span>
                </div>
              </div>

              <div class="card-bottom-info">
                <span>负电价: {{ item.negative_count }} 时点</span>
                <span>北海售电: {{ item.beihai_sales != null ? `${formatNum(item.beihai_sales)} MWh` : '—' }}</span>
              </div>
            </div>
          </template>

          <!-- 3. 区间按日均价汇总微卡片 -->
          <template v-else-if="viewMode === 'range' && rangeSubMode === 'daily' && dailyTableSubMode === 'dailySummary'">
            <div v-if="!displayedDailyTrends.length" class="empty-cards">
              未查询到符合条件的日度均价汇总记录
            </div>
            <div
              v-for="(item, idx) in displayedDailyTrends"
              v-else
              :key="`daily_card_${item.trade_date}`"
              :class="['spot-mobile-card', { 'is-negative': (item.negative_count || 0) > 0 }]"
            >
              <div class="card-top-row">
                <div class="time-block">
                  <span class="point-badge">#{{ idx + 1 }}</span>
                  <span class="time-text font-bold">{{ item.trade_date }}</span>
                </div>
                <div class="status-wrap">
                  <span v-if="(item.negative_count || 0) > 0" class="badge-neg">❄️ 负电价 ({{ item.negative_count }}点)</span>
                </div>
              </div>

              <div class="card-price-grid">
                <div class="price-cell">
                  <span class="cell-label">日前日均价</span>
                  <span :class="['cell-val text-blue', { 'val-neg': item.avg_day_ahead_price < 0 }]">
                    {{ formatNum(item.avg_day_ahead_price) }}
                  </span>
                </div>
                <div class="price-cell">
                  <span class="cell-label">实时日均价</span>
                  <span :class="['cell-val text-orange', { 'val-neg': item.avg_real_time_price < 0 }]">
                    {{ formatNum(item.avg_real_time_price) }}
                  </span>
                </div>
                <div class="price-cell">
                  <span class="cell-label">日均价差</span>
                  <span :class="['cell-val', getSpreadColorClass(item.avg_price_spread)]">
                    {{ (item.avg_price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(item.avg_price_spread) }}
                  </span>
                </div>
              </div>

              <div class="card-bottom-info">
                <span>北海售电: {{ item.beihai_sales != null ? `${formatNum(item.beihai_sales)} MWh` : '—' }}</span>
                <span>香海售电: {{ item.xianghai_sales != null ? `${formatNum(item.xianghai_sales)} MWh` : '—' }}</span>
              </div>
            </div>
          </template>

          <!-- 4. 单日分时或穿透 15 分钟分时微卡片 (轻量分页切片) -->
          <template v-else>
            <div v-if="!paginatedPoints.length" class="empty-cards">
              未查询到符合条件的电力现货时序数据
            </div>
            <div
              v-for="item in paginatedPoints"
              v-else
              :key="item.id || `${item.trade_date}_${item.point_index}`"
              :class="['spot-mobile-card', { 'is-negative': isPointNegative(item) }]"
            >
              <div class="card-top-row">
                <div class="time-block">
                  <span class="point-badge">#{{ item.point_index }}</span>
                  <span class="time-text">{{ item.time_label }}</span>
                  <span class="period-text">{{ item.period_start_time }}~{{ item.period_end_time }}</span>
                </div>
                <div class="status-wrap">
                  <span v-if="isPointNegative(item)" class="badge-neg">❄️ 负电价</span>
                </div>
              </div>

              <div class="card-price-grid">
                <div class="price-cell">
                  <span class="cell-label">日前电价</span>
                  <span :class="['cell-val text-blue', { 'val-neg': item.day_ahead_price < 0 }]">
                    {{ formatNum(item.day_ahead_price) }}
                  </span>
                </div>
                <div class="price-cell">
                  <span class="cell-label">实时电价</span>
                  <span :class="['cell-val text-orange', { 'val-neg': item.real_time_price < 0 }]">
                    {{ formatNum(item.real_time_price) }}
                  </span>
                </div>
                <div class="price-cell">
                  <span class="cell-label">价差（实时-日前）</span>
                  <span :class="['cell-val', getSpreadColorClass(item.price_spread)]">
                    {{ (item.price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(item.price_spread) }}
                  </span>
                </div>
              </div>

              <!-- 售电量展开折叠预览 -->
              <div class="card-bottom-info">
                <span>北海售电: {{ item.beihai_total_sales != null ? `${item.beihai_total_sales} MWh` : '暂无数据' }}</span>
                <span>香海售电: {{ item.xianghai_total_sales != null ? `${item.xianghai_total_sales} MWh` : '暂无数据' }}</span>
              </div>
            </div>
          </template>
        </div>

        <!-- 桌面端与紧凑大表格视图 (Table View) -->
        <div v-else class="table-responsive">
          <!-- 1. 时段聚合模式表格 (96 点位时段均价) -->
          <table v-if="viewMode === 'range' && rangeSubMode === 'period'" class="spot-table">
            <thead>
              <tr>
                <th class="col-center">序号</th>
                <th>官方时刻</th>
                <th>时段区间</th>
                <th class="col-right">日前均价 (元/MWh)</th>
                <th class="col-right">实时均价 (元/MWh)</th>
                <th class="col-right">平均价差 (元/MWh)</th>
                <th class="col-right">负电价天数</th>
                <th class="col-right">北海平均 (MWh)</th>
                <th class="col-right">香海平均 (MWh)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="10" class="empty-cell">
                  <div class="table-loading-wrap">
                    <div class="spinner"></div>
                    <span>数据正在加载中…</span>
                  </div>
                </td>
              </tr>
              <tr v-else-if="!displayedPeriodTrends.length">
                <td colspan="10" class="empty-cell">未查询到符合条件的时段聚合均价记录</td>
              </tr>
              <tr
                v-for="item in displayedPeriodTrends"
                :key="`period_row_${item.point_index}`"
                :class="{ 'row-negative': isPeriodNegative(item) }"
              >
                <td class="col-center text-muted">{{ item.point_index }}</td>
                <td class="mono font-bold">{{ item.time_label }}</td>
                <td class="mono text-muted">{{ item.period_start_time }}~{{ item.period_end_time }}</td>
                <td class="col-right mono font-bold text-blue">
                  <span v-if="item.avg_day_ahead_price < 0" class="badge-neg-inline">❄️ {{ formatNum(item.avg_day_ahead_price) }}</span>
                  <span v-else>{{ formatNum(item.avg_day_ahead_price) }}</span>
                </td>
                <td class="col-right mono font-bold text-orange">
                  <span v-if="item.avg_real_time_price < 0" class="badge-neg-inline">❄️ {{ formatNum(item.avg_real_time_price) }}</span>
                  <span v-else>{{ formatNum(item.avg_real_time_price) }}</span>
                </td>
                <td :class="['col-right mono font-bold', getSpreadColorClass(item.avg_price_spread)]">
                  {{ (item.avg_price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(item.avg_price_spread) }}
                </td>
                <td class="col-right mono font-bold text-danger">
                  {{ item.negative_days_count }} 天
                </td>
                <td class="col-right mono text-muted">
                  {{ item.avg_beihai_sales != null ? formatNum(item.avg_beihai_sales) : '—' }}
                </td>
                <td class="col-right mono text-muted">
                  {{ item.avg_xianghai_sales != null ? formatNum(item.avg_xianghai_sales) : '—' }}
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 2. 月份聚合模式表格 -->
          <table v-else-if="viewMode === 'range' && rangeSubMode === 'monthly'" class="spot-table">
            <thead>
              <tr>
                <th class="col-center">序号</th>
                <th>月份</th>
                <th>统计天数</th>
                <th class="col-right">日前月均价 (元/MWh)</th>
                <th class="col-right">实时月均价 (元/MWh)</th>
                <th class="col-right">月均价差 (元/MWh)</th>
                <th class="col-right">负电价时点数</th>
                <th class="col-right">北海总售电 (MWh)</th>
                <th class="col-right">香海总售电 (MWh)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="10" class="empty-cell">
                  <div class="table-loading-wrap">
                    <div class="spinner"></div>
                    <span>数据正在加载中…</span>
                  </div>
                </td>
              </tr>
              <tr v-else-if="!displayedMonthlyTrends.length">
                <td colspan="10" class="empty-cell">未查询到符合条件的月度聚合记录</td>
              </tr>
              <tr
                v-for="(item, idx) in displayedMonthlyTrends"
                :key="`monthly_row_${item.month_label}`"
                :class="{ 'row-negative': isMonthlyNegative(item) }"
              >
                <td class="col-center text-muted">{{ idx + 1 }}</td>
                <td class="mono font-bold">{{ item.month_label }}</td>
                <td class="mono text-muted">{{ item.day_count }} 天 ({{ item.point_count }} 点位)</td>
                <td class="col-right mono font-bold text-blue">
                  <span v-if="item.avg_day_ahead_price < 0" class="badge-neg-inline">❄️ {{ formatNum(item.avg_day_ahead_price) }}</span>
                  <span v-else>{{ formatNum(item.avg_day_ahead_price) }}</span>
                </td>
                <td class="col-right mono font-bold text-orange">
                  <span v-if="item.avg_real_time_price < 0" class="badge-neg-inline">❄️ {{ formatNum(item.avg_real_time_price) }}</span>
                  <span v-else>{{ formatNum(item.avg_real_time_price) }}</span>
                </td>
                <td :class="['col-right mono font-bold', getSpreadColorClass(item.avg_price_spread)]">
                  {{ (item.avg_price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(item.avg_price_spread) }}
                </td>
                <td class="col-right mono font-bold text-danger">
                  {{ item.negative_count }}
                </td>
                <td class="col-right mono text-muted">
                  {{ item.beihai_sales != null ? formatNum(item.beihai_sales) : '—' }}
                </td>
                <td class="col-right mono text-muted">
                  {{ item.xianghai_sales != null ? formatNum(item.xianghai_sales) : '—' }}
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 3. 区间按日均价汇总大表 (每日一条汇总记录，毫秒级极速渲染) -->
          <table v-else-if="viewMode === 'range' && rangeSubMode === 'daily' && dailyTableSubMode === 'dailySummary'" class="spot-table">
            <thead>
              <tr>
                <th class="col-center">序号</th>
                <th>交易日期</th>
                <th class="col-right">日前日均价 (元/MWh)</th>
                <th class="col-right">实时日均价 (元/MWh)</th>
                <th class="col-right">日均价差 (元/MWh)</th>
                <th class="col-right">负电价时点数</th>
                <th class="col-right">北海总售电 (MWh)</th>
                <th class="col-right">香海总售电 (MWh)</th>
                <th class="col-right">两厂总售电 (MWh)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="10" class="empty-cell">
                  <div class="table-loading-wrap">
                    <div class="spinner"></div>
                    <span>数据正在加载中…</span>
                  </div>
                </td>
              </tr>
              <tr v-else-if="!displayedDailyTrends.length">
                <td colspan="10" class="empty-cell">未查询到符合条件的日度均价汇总记录</td>
              </tr>
              <tr
                v-for="(item, idx) in displayedDailyTrends"
                :key="`daily_row_${item.trade_date}`"
                :class="{ 'row-negative': (item.negative_count || 0) > 0 }"
              >
                <td class="col-center text-muted">{{ idx + 1 }}</td>
                <td class="mono font-bold">{{ item.trade_date }}</td>
                <td class="col-right mono font-bold text-blue">
                  <span v-if="item.avg_day_ahead_price < 0" class="badge-neg-inline">❄️ {{ formatNum(item.avg_day_ahead_price) }}</span>
                  <span v-else>{{ formatNum(item.avg_day_ahead_price) }}</span>
                </td>
                <td class="col-right mono font-bold text-orange">
                  <span v-if="item.avg_real_time_price < 0" class="badge-neg-inline">❄️ {{ formatNum(item.avg_real_time_price) }}</span>
                  <span v-else>{{ formatNum(item.avg_real_time_price) }}</span>
                </td>
                <td :class="['col-right mono font-bold', getSpreadColorClass(item.avg_price_spread)]">
                  {{ (item.avg_price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(item.avg_price_spread) }}
                </td>
                <td class="col-right mono font-bold text-danger">
                  <span v-if="item.negative_count > 0" class="badge-neg-inline">❄️ {{ item.negative_count }} 点</span>
                  <span v-else class="text-muted">0</span>
                </td>
                <td class="col-right mono text-muted">
                  {{ item.beihai_sales != null ? formatNum(item.beihai_sales) : '—' }}
                </td>
                <td class="col-right mono text-muted">
                  {{ item.xianghai_sales != null ? formatNum(item.xianghai_sales) : '—' }}
                </td>
                <td class="col-right mono text-muted">
                  {{ item.total_sales != null ? formatNum(item.total_sales) : '—' }}
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 4. 单日分时或穿透 15 分钟时序点位大表 (轻量分页渲染，单页最多 96 条，杜绝 DOM 爆炸) -->
          <table v-else class="spot-table">
            <thead>
              <tr>
                <th class="col-center">序号</th>
                <th>日期</th>
                <th>官方时刻</th>
                <th>时段区间</th>
                <th class="col-right">日前电价 (元/MWh)</th>
                <th class="col-right">实时电价 (元/MWh)</th>
                <th class="col-right">价差（实时-日前） (元/MWh)</th>
                <th class="col-right">北海合计 (MWh)</th>
                <th class="col-right">香海合计 (MWh)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td colspan="10" class="empty-cell">
                  <div class="table-loading-wrap">
                    <div class="spinner"></div>
                    <span>数据正在加载中…</span>
                  </div>
                </td>
              </tr>
              <tr v-else-if="!paginatedPoints.length">
                <td colspan="10" class="empty-cell">未查询到符合条件的电力现货时序记录</td>
              </tr>
              <tr
                v-for="item in paginatedPoints"
                :key="item.id || `${item.trade_date}_${item.point_index}`"
                :class="{ 'row-negative': isPointNegative(item) }"
              >
                <td class="col-center text-muted">{{ item.point_index }}</td>
                <td class="mono">{{ item.trade_date }}</td>
                <td class="mono font-bold">{{ item.time_label }}</td>
                <td class="mono text-muted">{{ item.period_start_time }}~{{ item.period_end_time }}</td>
                <td class="col-right mono font-bold text-blue">
                  <span v-if="item.day_ahead_price < 0" class="badge-neg-inline">❄️ {{ formatNum(item.day_ahead_price) }}</span>
                  <span v-else>{{ formatNum(item.day_ahead_price) }}</span>
                </td>
                <td class="col-right mono font-bold text-orange">
                  <span v-if="item.real_time_price < 0" class="badge-neg-inline">❄️ {{ formatNum(item.real_time_price) }}</span>
                  <span v-else>{{ formatNum(item.real_time_price) }}</span>
                </td>
                <td :class="['col-right mono font-bold', getSpreadColorClass(item.price_spread)]">
                  {{ (item.price_spread ?? 0) > 0 ? '+' : '' }}{{ formatNum(item.price_spread) }}
                </td>
                <td class="col-right mono text-muted">
                  {{ item.beihai_total_sales != null ? formatNum(item.beihai_total_sales) : '—' }}
                </td>
                <td class="col-right mono text-muted">
                  {{ item.xianghai_total_sales != null ? formatNum(item.xianghai_total_sales) : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 轻量分页控制器：单日分时、区间连续显示或穿透 15 分钟分时明细视图下展示 -->
        <div
          v-if="showPointsPagination && displayedPoints.length > 0"
          class="pagination-bar"
        >
          <div class="pagination-info">
            <span>共 <strong>{{ totalPointsCount.toLocaleString() }}</strong> 条时序记录</span>
            <span class="pagination-sep">|</span>
            <span>第 <strong>{{ currentPage }}</strong> / <strong>{{ totalPages }}</strong> 页</span>
          </div>

          <div class="pagination-controls">
            <button
              class="btn-page"
              type="button"
              :disabled="currentPage <= 1"
              title="跳转到第 1 页"
              @click="goToPage(1)"
            >
              « 首页
            </button>
            <button
              class="btn-page"
              type="button"
              :disabled="currentPage <= 1"
              title="前一页"
              @click="goToPage(currentPage - 1)"
            >
              ‹ 上一页
            </button>

            <!-- 紧凑页码输入跳转 -->
            <div class="page-num-indicator">
              <span class="page-label">页码</span>
              <input
                type="number"
                class="page-jump-input"
                :value="currentPage"
                min="1"
                :max="totalPages"
                @change="goToPage($event.target.value)"
              />
              <span class="page-total-label">/ {{ totalPages }}</span>
            </div>

            <button
              class="btn-page"
              type="button"
              :disabled="currentPage >= totalPages"
              title="后一页"
              @click="goToPage(currentPage + 1)"
            >
              下一页 ›
            </button>
            <button
              class="btn-page"
              type="button"
              :disabled="currentPage >= totalPages"
              title="跳转到最后一页"
              @click="goToPage(totalPages)"
            >
              末页 »
            </button>

            <div class="page-size-selector">
              <span class="page-label">每页</span>
              <select
                :value="pageSize"
                class="page-select"
                @change="changePageSize($event.target.value)"
              >
                <option v-for="opt in pageSizeOptions" :key="opt" :value="opt">
                  {{ opt }} 条{{ opt === 96 ? ' (1天)' : '' }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </section>

      <!-- Global_admin 系统控制选项弹窗 (自动同步与手动拉取设置) -->
      <div v-if="showAdminControlModal" class="admin-modal-backdrop" @click="showAdminControlModal = false">
        <div class="admin-modal-card" @click.stop>
          <div class="admin-modal-header">
            <div class="modal-title-group">
              <span class="modal-badge-admin">🔒 仅 Global_admin 可见</span>
              <h3>⚙️ 电力现货数据自动获取与系统控制</h3>
            </div>
            <button class="modal-close-btn" type="button" @click="showAdminControlModal = false">✕</button>
          </div>

          <div class="admin-modal-body">
            <!-- 当前运行状态面板 -->
            <div class="status-summary-card">
              <div class="status-indicator-row">
                <div class="indicator-left">
                  <span
                    class="pulse-status-dot"
                    :class="syncConfig.enabled ? (syncConfig.last_run_status === 'RETRYING' ? 'dot-retrying' : 'dot-online') : 'dot-paused'"
                  ></span>
                  <span class="status-title">调度运行状态：</span>
                  <strong
                    class="status-name"
                    :class="syncConfig.enabled ? (syncConfig.last_run_status === 'RETRYING' ? 'text-orange' : 'text-green') : 'text-muted'"
                  >
                    {{ !syncConfig.enabled ? '已暂停自动拉取' : syncConfig.last_run_status === 'RETRYING' ? '重试探测中' : '正常守候中' }}
                  </strong>
                </div>
                <div class="indicator-right">
                  <button class="btn-refresh-status" type="button" :disabled="syncConfigLoading" @click="fetchSyncConfig">
                    {{ syncConfigLoading ? '刷新中...' : '🔄 刷新状态' }}
                  </button>
                </div>
              </div>
              <div class="status-meta-grid">
                <div class="meta-item">
                  <span class="meta-label">下次计划探测</span>
                  <span class="meta-val highlight">{{ syncConfig.next_run_time || '等待计算' }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">最近入库日期</span>
                  <span class="meta-val">{{ syncConfig.last_sync_date || '暂无记录' }}</span>
                </div>
                <div class="meta-item">
                  <span class="meta-label">最近探测时间</span>
                  <span class="meta-val">{{ syncConfig.last_run_time || '尚未触发' }}</span>
                </div>
              </div>
              <div v-if="syncConfig.last_run_message" class="status-msg-banner">
                <span>📢 状态信息：{{ syncConfig.last_run_message }}</span>
              </div>
            </div>

            <!-- 配置表单区块 1：自动化调度参数 -->
            <div class="control-section">
              <div class="section-title-row">
                <h4>⏰ 每日自动拉取规则设置</h4>
                <span class="section-desc">发改委每日约 08:00 发布前一日现货电价，可设置提早探测与轮询策略</span>
              </div>

              <div class="control-form-grid">
                <div class="form-row">
                  <div class="form-label">
                    <span class="label-txt">自动拉取开关</span>
                    <small>开启后后台守护程序将每日定时抓取</small>
                  </div>
                  <div class="form-field">
                    <label class="toggle-switch">
                      <input type="checkbox" v-model="syncConfig.enabled" />
                      <span class="slider round"></span>
                    </label>
                    <span class="toggle-text">{{ syncConfig.enabled ? '已开启' : '已关闭' }}</span>
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-label">
                    <span class="label-txt">每日初次尝试时间</span>
                    <small>建议设为 07:40，提前守候发改委发布</small>
                  </div>
                  <div class="form-field">
                    <input type="time" class="input-time" v-model="syncConfig.cron_time" />
                  </div>
                </div>

                <div class="form-row">
                  <div class="form-label">
                    <span class="label-txt">未更新时重试间隔</span>
                    <small>若初次探测未发布，每隔多少分钟重试一次直至完成</small>
                  </div>
                  <div class="form-field">
                    <div class="input-unit-wrap">
                      <input
                        type="number"
                        class="input-number"
                        v-model.number="syncConfig.retry_interval_minutes"
                        min="1"
                        max="120"
                      />
                      <span class="input-unit">分钟</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="section-action-row">
                <button
                  class="btn primary save-config-btn"
                  type="button"
                  :disabled="savingSyncConfig"
                  @click="handleSaveSyncConfig"
                >
                  {{ savingSyncConfig ? '正在保存...' : '💾 保存自动拉取设置' }}
                </button>
              </div>
            </div>

            <!-- 配置表单区块 2：手动实时拉取与历史补录 -->
            <div class="control-section">
              <div class="section-title-row">
                <h4>🚀 手动实时拉取 / 历史补录</h4>
                <span class="section-desc">无需等待定时任务，直接向发改委接口请求数据并原子幂等入库</span>
              </div>

              <div class="manual-sync-box">
                <div class="sync-mode-radios">
                  <label class="radio-label">
                    <input type="radio" value="yesterday" v-model="manualSyncMode" />
                    <span>拉取最新数据（昨日现货电价：<strong>{{ yesterdayDateStr }}</strong>）</span>
                  </label>
                  <label class="radio-label">
                    <input type="radio" value="specific" v-model="manualSyncMode" />
                    <span>指定某日补录</span>
                  </label>
                </div>

                <div v-if="manualSyncMode === 'specific'" class="specific-date-picker-row">
                  <span class="picker-label">请选择目标补录日期：</span>
                  <input type="date" class="input-date" v-model="manualSyncSpecificDate" />
                </div>

                <!-- 存在性覆盖确认警告区 -->
                <div v-if="showOverwriteConfirm" class="overwrite-confirm-box">
                  <div class="confirm-alert-header">
                    <span class="confirm-icon">⚠️</span>
                    <strong class="confirm-title">数据已存在，是否覆盖？</strong>
                  </div>
                  <div class="confirm-desc">
                    {{ overwriteConfirmMessage }}
                  </div>
                  <div class="confirm-actions">
                    <button
                      class="btn danger btn-confirm-overwrite"
                      type="button"
                      :disabled="manualSyncLoading"
                      @click="handleConfirmOverwrite"
                    >
                      <span v-if="manualSyncLoading" class="btn-spinner"></span>
                      <span>{{ manualSyncLoading ? '正在覆盖入库中...' : `⚠️ 确认覆盖【${overwriteTargetDate}】数据` }}</span>
                    </button>
                    <button
                      class="btn default btn-cancel-overwrite"
                      type="button"
                      :disabled="manualSyncLoading"
                      @click="handleCancelOverwrite"
                    >
                      取消
                    </button>
                  </div>
                </div>

                <div v-else class="manual-btn-row">
                  <button
                    class="btn manual-trigger-btn"
                    type="button"
                    :disabled="manualSyncLoading"
                    @click="() => handleManualSync(false)"
                  >
                    <span v-if="manualSyncLoading" class="btn-spinner"></span>
                    <span>{{ manualSyncLoading ? '正在向发改委请求并入库中...' : (manualSyncMode === 'yesterday' ? `⚡ 立即拉取昨日【${yesterdayDateStr}】入库` : `⚡ 立即拉取【${manualSyncSpecificDate || '未选择日期'}】入库`) }}</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- 结果反馈横幅 -->
            <div v-if="syncFeedbackMsg" :class="['feedback-alert', `alert-${syncFeedbackType}`]">
              <span class="alert-icon">{{ syncFeedbackType === 'success' ? '✅' : syncFeedbackType === 'warning' ? '⚠️' : '❌' }}</span>
              <span class="alert-text">{{ syncFeedbackMsg }}</span>
            </div>
          </div>

          <div class="admin-modal-footer">
            <span class="footer-tip">💡 提示：写入数据采用 ON CONFLICT (trade_date, point_index) 幂等更新，不会影响已有电厂售电量数据。</span>
            <button class="btn default" type="button" @click="showAdminControlModal = false">关闭</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import * as XLSX from 'xlsx'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import SpotSettlementImport from '../components/SpotSettlementImport.vue'
import { addPlantSalesToOption } from '../utils/spotPlantSalesChart'
import { buildContinuousTimeline } from '../utils/spotContinuousSeries'
import { buildPlantAlignmentReport } from '../utils/spotCurveAlignment'
import { getProjectNameById } from '../composables/useProjects'
import { useAuthStore } from '../store/auth'
import {
  getSpotElectricityMeta,
  getSpotElectricitySummary,
  getSpotElectricityPoints,
  getSpotElectricityDailyTrends,
  getSpotElectricityPeriodTrends,
  getSpotElectricityMonthlyTrends,
  getSpotElectricitySyncConfig,
  saveSpotElectricitySyncConfig,
  manualSyncSpotElectricity,
  recordDailyReportOperationLog,
} from '../services/api'

const route = useRoute()
const router = useRouter()
const projectKey = String(route.params.projectKey || 'daily_report_25_26')
const projectName = computed(() => getProjectNameById(projectKey) || '2026-2027供暖期生产日报')

const pageDisplayName = computed(() => {
  const raw = route.query.pageName
  if (typeof raw === 'string' && raw.trim() && raw.trim() !== '电力市场数据') {
    return raw.trim()
  }
  return '电力现货市场数据'
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: pageDisplayName.value, to: null },
])

// 状态管理
const loading = ref(false)
const loadError = ref('')
const viewMode = ref('single') // 'single' | 'range'
const rangeSubMode = ref('daily') // 'daily' | 'monthly' | 'period' | 'continuous'
const dailyTableSubMode = ref('dailySummary') // 区间日度走势下表格展示：'dailySummary' (按日均价汇总，默认) | 'pointsDetail' (15分钟分时明细，分页)
const mobileLayout = ref('card') // 'card' | 'table'
const isMobileScreen = ref(false)

function checkMobileScreen() {
  if (typeof window !== 'undefined') {
    isMobileScreen.value = window.innerWidth <= 768
  }
}

const onlyNegative = ref(false)

// 动态计算默认初始日期（默认前一日，贴合辽宁现货电价发布周期），避免写死过往历史日期导致初次渲染闪烁跳动
function getInitialDateStr(offsetDays = 1) {
  const d = new Date()
  d.setDate(d.getDate() - offsetDays)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const defaultLatestDate = getInitialDateStr(1)
const defaultStartDate = getInitialDateStr(12)

const selectedDate = ref(defaultLatestDate)
const rangeStartDate = ref(defaultStartDate)
const rangeEndDate = ref(defaultLatestDate)

const meta = ref({
  has_data: false,
  min_date: '2026-01-01',
  max_date: defaultLatestDate,
  total_days: 0,
  total_points: 0,
})

// 纯展示批量时序数据使用 shallowRef，避免 Vue 深度递归对 10,000+ 个对象进行 Proxy 包装，大幅节省内存与消除 GC 卡顿
const points = shallowRef([])
const dailyTrends = shallowRef([])
const periodTrends = shallowRef([])
const monthlyTrends = shallowRef([])

const summary = ref(null)
const showPlantSales = ref(false)
const plantSalesScope = ref('all') // 'all' | 'beihai' | 'xianghai'
const plantSalesScopeOptions = [
  { key: 'all', label: '两厂', title: '同时显示北海与香海上网电量曲线' },
  { key: 'beihai', label: '北海', color: '#0891b2', title: '仅显示北海热电厂上网电量曲线' },
  { key: 'xianghai', label: '香海', color: '#8b5cf6', title: '仅显示香海热电厂上网电量曲线' },
]
const hasPlantSalesData = computed(() => {
  if (summary.value?.has_plant_sales_data === true) return true
  const pts = points.value
  if (!pts || !pts.length) return false
  return pts.some(pt => (
    (pt.xianghai_total_sales ?? 0) > 0 ||
    (pt.beihai_total_sales ?? 0) > 0 ||
    pt.xianghai_unit1_sales != null ||
    pt.beihai_unit1_sales != null
  ))
})
const canShowPlantSales = computed(() => hasPlantSalesData.value && !loading.value && !loadError.value)
watch(showPlantSales, () => { if (!loading.value) renderChart() })
watch(plantSalesScope, () => { if (!loading.value && showPlantSales.value) renderChart() })
watch(hasPlantSalesData, available => { if (!available) showPlantSales.value = false })

const totalQueryPoints = computed(() => {
  return summary.value?.point_count || points.value?.length || 0
})

const negativePointRatioText = computed(() => {
  const neg = summary.value?.negative_price_points ?? 0
  const total = totalQueryPoints.value
  if (!total || total <= 0) return '0.0%'
  const pct = (neg / total) * 100
  return `${pct.toFixed(1)}%`
})

// 区间走势分析：总查询天数
const totalQueryDays = computed(() => {
  if (summary.value?.day_count) {
    return Number(summary.value.day_count)
  }
  if (dailyTrends.value?.length) {
    return dailyTrends.value.length
  }
  return 0
})

// 区间走势分析：负电价天数（优先后端权威统计，兜底由前端日走势聚合）
const negativeDaysCount = computed(() => {
  if (summary.value?.negative_price_days != null) {
    return Number(summary.value.negative_price_days)
  }
  if (Array.isArray(dailyTrends.value) && dailyTrends.value.length > 0) {
    return dailyTrends.value.filter((d) => (d.negative_count || 0) > 0).length
  }
  return 0
})

// 区间走势分析：负电价天数占比文本
const negativeDaysRatioText = computed(() => {
  const days = totalQueryDays.value
  if (!days || days <= 0) return '0.0%'
  const negDays = negativeDaysCount.value
  const pct = (negDays / days) * 100
  return `${pct.toFixed(1)}%`
})

const chartRef = ref(null)
let chartInstance = null

// 图表指标显隐控制（默认显示日前电价与实时电价，价差为可选参数，默认不显示）
const visibleSeries = ref({
  dayAhead: true,
  realTime: true,
  spread: false,
})

const visibleRangeSeries = ref({
  dayAheadAvg: true,
  realTimeAvg: true,
  negativeCount: false,
})

const visibleMonthlySeries = ref({
  dayAheadAvg: true,
  realTimeAvg: true,
  spread: false,
  negativeCount: false,
})

const visiblePeriodSeries = ref({
  dayAheadAvg: true,
  realTimeAvg: true,
  spread: false,
  negativeDays: false,
})

function toggleSeries(key) {
  const nextVal = !visibleSeries.value[key]
  // 保持至少一个指标可见，避免图表完全空白
  if (!nextVal) {
    const activeCount = Object.values(visibleSeries.value).filter(Boolean).length
    if (activeCount <= 1) return
  }
  visibleSeries.value[key] = nextVal
  renderChart()
}

function toggleRangeSeries(key) {
  const nextVal = !visibleRangeSeries.value[key]
  if (!nextVal) {
    const activeCount = Object.values(visibleRangeSeries.value).filter(Boolean).length
    if (activeCount <= 1) return
  }
  visibleRangeSeries.value[key] = nextVal
  renderChart()
}

function toggleMonthlySeries(key) {
  const nextVal = !visibleMonthlySeries.value[key]
  if (!nextVal) {
    const activeCount = Object.values(visibleMonthlySeries.value).filter(Boolean).length
    if (activeCount <= 1) return
  }
  visibleMonthlySeries.value[key] = nextVal
  renderChart()
}

function togglePeriodSeries(key) {
  const nextVal = !visiblePeriodSeries.value[key]
  if (!nextVal) {
    const activeCount = Object.values(visiblePeriodSeries.value).filter(Boolean).length
    if (activeCount <= 1) return
  }
  visiblePeriodSeries.value[key] = nextVal
  renderChart()
}

function switchRangeSubMode(subMode) {
  rangeSubMode.value = subMode
  if (subMode === 'period' && !periodTrends.value.length) {
    fetchData()
  } else if (subMode === 'monthly' && !monthlyTrends.value.length) {
    fetchData()
  } else if (subMode === 'continuous' && !points.value.length) {
    fetchData()
  } else {
    renderChart()
  }
}

const metaRangeText = computed(() => {
  if (!meta.value.min_date || !meta.value.max_date) return '加载中…'
  return `${meta.value.min_date} 至 ${meta.value.max_date}`
})

// 工具函数
const salesPriceBasis = ref('real_time') // 'real_time' | 'day_ahead'
const plantCards = [
  { key: 'beihai', name: '北海热电厂', units: '1–3号机组合计' },
  { key: 'xianghai', name: '香海热电厂', units: '1–4号机组合计' },
]
function toCorrDisplay(metrics) {
  if (!metrics || metrics.validPoints <= 0) return null
  if (metrics.dayCount > 1) {
    return {
      dayCount: metrics.dayCount,
      primary: metrics.intradayCorrelation ?? metrics.correlation,
      sub: metrics.intradayCorrelation != null ? metrics.correlation : null,
      isIntraday: metrics.intradayCorrelation != null,
    }
  }
  return {
    dayCount: 1,
    primary: metrics.correlation,
    sub: null,
    isIntraday: false,
  }
}

const plantAlignmentReport = computed(() => buildPlantAlignmentReport(points.value))
const plantCardMetrics = computed(() => {
  const s = summary.value
  const isDa = salesPriceBasis.value === 'day_ahead'
  const feePrefix = isDa ? 'da_' : ''
  const corrByKey = plantAlignmentReport.value?.byKey || {}
  return plantCards.map(plant => {
    const plantCorr = corrByKey[plant.key]
    return {
      ...plant,
      sales: s?.[`sum_${plant.key}_sales`],
      spotFee: s?.[`sum_${plant.key}_${feePrefix}spot_fee`],
      spotFeeDiff: isDa ? s?.[`sum_${plant.key}_da_spot_fee_diff`] : null,
      contractFee: s?.[`sum_${plant.key}_contract_fee`],
      revenueFee: s?.[`sum_${plant.key}_${feePrefix}revenue_fee`],
      avgSpotPrice: s?.[`avg_${plant.key}_${feePrefix}spot_price`],
      diffRate: isDa ? null : s?.[`${plant.key}_spot_price_diff_rate`],
      spotPriceDiff: isDa ? s?.[`avg_${plant.key}_da_spot_price_diff`] : null,
      corrDayAhead: toCorrDisplay(plantCorr?.dayAhead),
      corrRealTime: toCorrDisplay(plantCorr?.realTime),
      spotFeeTooltip: isDa
        ? '逐15分钟汇总全部机组上网电量 × 该时段日前电价（测算参考）；较实时差异 = 日前测算现货电费 − 账单实时现货电费'
        : '逐15分钟汇总全部机组上网电量 × 该时段账单实时电价',
      revenueTooltip: `${isDa ? '日前测算' : ''}现货电费与合约差价电费之和，先求和再四舍五入`,
      avgPriceTooltip: isDa
        ? '平均现货电价=该厂未舍入日前测算现货电费÷上网电量；较实时差额 = 日前测算加权均价 − 实时账单加权均价。电量为0时均价不可计算。'
        : '平均现货电价=该厂未舍入现货电费÷上网电量；差异率=(该厂均价−实时价算术均值)÷实时价算术均值。电量为0时均价不可计算，基准均价为0时差异率显示—。',
    }
  })
})
const feeNumberFormatter = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0, useGrouping: true })
const signedFeeDiffFormatter = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0, useGrouping: true, signDisplay: 'exceptZero' })
const signedPriceDiffFormatter = new Intl.NumberFormat('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: false, signDisplay: 'exceptZero' })
function formatPlantMetric(value, unit) {
  if (value == null) return '暂无数据'
  const amount = unit === '元' ? feeNumberFormatter.format(value).replace(/^-0$/, '0') : formatNum(value)
  return `${amount} ${unit}`
}
function formatSignedFeeDiff(value) {
  if (value == null) return '—'
  const rounded = Math.round(Number(value))
  const text = Object.is(rounded, -0) || rounded === 0 ? '0' : signedFeeDiffFormatter.format(rounded)
  return `${text} 元`
}
function formatSignedPriceDiff(value) {
  if (value == null) return '—'
  const rounded = Math.round(Number(value) * 100) / 100
  const text = Object.is(rounded, -0) || rounded === 0 ? '0.00' : signedPriceDiffFormatter.format(rounded)
  return `${text} 元/MWh`
}
function formatNum(val) {
  if (val === null || val === undefined || isNaN(val)) return '—'
  return Number(val).toFixed(2)
}
const spotPriceRateFormatter = new Intl.NumberFormat('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'exceptZero' })
function formatSpotPriceRate(value) {
  return value == null ? '—' : `${spotPriceRateFormatter.format(value)}%`
}

// 波形相关系数格式化
function formatCorrelationR(val, withSign = false) {
  if (val == null || isNaN(val)) return '—'
  const rounded = Math.round(Number(val) * 100) / 100
  if (rounded === 0 || Object.is(rounded, -0)) return '0.00'
  const sign = withSign && rounded > 0 ? '+' : ''
  return `${sign}${rounded.toFixed(2)}`
}

function formatPlantCorrelation(corr) {
  if (!corr || corr.primary == null) return '—'
  const text = formatCorrelationR(corr.primary, true)
  return corr.isIntraday ? `日内 ${text}` : text
}

// ==========================================
// 现货单价区间上网电量分布分析模块（响应式状态与统计计算）
// ==========================================
const isDistributionWindowOpen = ref(true)
const selectedDistributionPlant = ref('all') // 'all' | 'xianghai' | 'beihai'
const showUnitBreakdown = ref(false)

const PRICE_INTERVAL_CONFIGS = [
  {
    key: 'neg',
    label: '[-100, 0)',
    unit: '元/MWh',
    name: '负电价',
    desc: '极度供大于求 / 弃电调峰',
    color: '#2563eb', // 蓝色
    bgColor: '#eff6ff',
    borderColor: '#bfdbfe',
    textColor: '#1d4ed8',
  },
  {
    key: 'low',
    label: '[0, 200)',
    unit: '元/MWh',
    name: '低电价',
    desc: '低谷消纳 / 边际承压',
    color: '#10b981', // 浅绿色
    bgColor: '#ecfdf5',
    borderColor: '#a7f3d0',
    textColor: '#047857',
  },
  {
    key: 'mid',
    label: '[200, 400)',
    unit: '元/MWh',
    name: '常规基准',
    desc: '燃煤基准价区间 (374.9)',
    color: '#f97316', // 浅橙色
    bgColor: '#fff7ed',
    borderColor: '#fed7aa',
    textColor: '#c2410c',
  },
  {
    key: 'high',
    label: '>= 400',
    unit: '元/MWh',
    name: '高电价',
    desc: '负荷高峰 / 高收益时段',
    color: '#ef4444', // 浅红色
    bgColor: '#fef2f2',
    borderColor: '#fecaca',
    textColor: '#b91c1c',
  },
]

// 电量区间分布核心计算属性
const plantDistributionStats = computed(() => {
  const pts = points.value || []
  const plantMode = selectedDistributionPlant.value // 'all' | 'xianghai' | 'beihai'

  const allUnits = [
    { key: 'xianghai_unit1', name: '香海 #1 机组', plant: 'xianghai', prop: 'xianghai_unit1_sales' },
    { key: 'xianghai_unit2', name: '香海 #2 机组', plant: 'xianghai', prop: 'xianghai_unit2_sales' },
    { key: 'xianghai_unit3', name: '香海 #3 机组', plant: 'xianghai', prop: 'xianghai_unit3_sales' },
    { key: 'xianghai_unit4', name: '香海 #4 机组', plant: 'xianghai', prop: 'xianghai_unit4_sales' },
    { key: 'beihai_unit1', name: '北海 #1 机组', plant: 'beihai', prop: 'beihai_unit1_sales' },
    { key: 'beihai_unit2', name: '北海 #2 机组', plant: 'beihai', prop: 'beihai_unit2_sales' },
    { key: 'beihai_unit3', name: '北海 #3 机组', plant: 'beihai', prop: 'beihai_unit3_sales' },
  ]

  const targetUnits = plantMode === 'all'
    ? allUnits
    : allUnits.filter(u => u.plant === plantMode)

  const intervalMap = {}
  PRICE_INTERVAL_CONFIGS.forEach(cfg => {
    intervalMap[cfg.key] = {
      ...cfg,
      sales: 0,
      revenue: 0,
      pointCount: 0,
    }
  })

  const unitMap = {}
  targetUnits.forEach(u => {
    unitMap[u.key] = {
      key: u.key,
      name: u.name,
      plant: u.plant,
      totalSales: 0,
      totalRevenue: 0,
      intervals: {
        neg: { sales: 0, revenue: 0 },
        low: { sales: 0, revenue: 0 },
        mid: { sales: 0, revenue: 0 },
        high: { sales: 0, revenue: 0 },
      },
    }
  })

  let totalSales = 0
  let totalRevenue = 0
  const totalPoints = pts.length

  pts.forEach(pt => {
    const price = salesPriceBasis.value === 'day_ahead'
      ? pt.day_ahead_price
      : (pt.bill_real_time_price ?? pt.real_time_price)
    if (price == null) return

    let targetIntervalKey = 'mid'
    if (price < 0) {
      targetIntervalKey = 'neg'
    } else if (price < 200) {
      targetIntervalKey = 'low'
    } else if (price < 400) {
      targetIntervalKey = 'mid'
    } else {
      targetIntervalKey = 'high'
    }

    intervalMap[targetIntervalKey].pointCount++

    let ptPlantSales = 0
    targetUnits.forEach(u => {
      const uSales = Number(pt[u.prop]) || 0
      if (uSales > 0) {
        ptPlantSales += uSales
        unitMap[u.key].totalSales += uSales
        unitMap[u.key].totalRevenue += uSales * price
        unitMap[u.key].intervals[targetIntervalKey].sales += uSales
        unitMap[u.key].intervals[targetIntervalKey].revenue += uSales * price
      }
    })

    if (ptPlantSales === 0) {
      if (plantMode === 'all') {
        const xTot = Number(pt.xianghai_total_sales) || 0
        const bTot = Number(pt.beihai_total_sales) || 0
        ptPlantSales = xTot + bTot
      } else if (plantMode === 'xianghai') {
        ptPlantSales = Number(pt.xianghai_total_sales) || 0
      } else if (plantMode === 'beihai') {
        ptPlantSales = Number(pt.beihai_total_sales) || 0
      }
    }

    if (ptPlantSales > 0) {
      totalSales += ptPlantSales
      totalRevenue += ptPlantSales * price
      intervalMap[targetIntervalKey].sales += ptPlantSales
      intervalMap[targetIntervalKey].revenue += ptPlantSales * price
    }
  })

  const intervals = PRICE_INTERVAL_CONFIGS.map(cfg => {
    const data = intervalMap[cfg.key]
    const ratio = totalSales > 0 ? (data.sales / totalSales) * 100 : 0
    const pointRatio = totalPoints > 0 ? (data.pointCount / totalPoints) * 100 : 0
    const avgPrice = data.sales > 0 ? (data.revenue / data.sales) : null

    return {
      key: cfg.key,
      label: cfg.label,
      unit: cfg.unit,
      name: cfg.name,
      desc: cfg.desc,
      color: cfg.color,
      bgColor: cfg.bgColor,
      borderColor: cfg.borderColor,
      textColor: cfg.textColor,
      sales: data.sales,
      salesFormatted: data.sales.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
      ratio: ratio,
      ratioFormatted: `${ratio.toFixed(2)}%`,
      pointCount: data.pointCount,
      pointRatioFormatted: `${pointRatio.toFixed(1)}%`,
      avgPriceFormatted: avgPrice != null ? `${avgPrice.toFixed(2)} 元/MWh` : '—',
    }
  })

  const unitStats = targetUnits.map(u => {
    const uData = unitMap[u.key]
    const uTotal = uData.totalSales
    const uAvg = uTotal > 0 ? (uData.totalRevenue / uTotal) : null

    const formattedIntervals = {}
    PRICE_INTERVAL_CONFIGS.forEach(cfg => {
      const iData = uData.intervals[cfg.key]
      const ratio = uTotal > 0 ? (iData.sales / uTotal) * 100 : 0
      formattedIntervals[cfg.key] = {
        sales: iData.sales,
        salesFormatted: iData.sales.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
        ratio: `${ratio.toFixed(2)}%`,
      }
    })

    return {
      key: u.key,
      name: u.name,
      totalSales: uTotal,
      totalSalesFormatted: uTotal.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
      avgPriceFormatted: uAvg != null ? `${uAvg.toFixed(2)} 元/MWh` : '—',
      intervals: formattedIntervals,
    }
  })

  return {
    totalSales,
    totalSalesFormatted: totalSales.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    totalPoints,
    intervals,
    unitStats,
  }
})

// 价差文本色彩辅助函数（国内统一红涨绿跌规范：正数显红，负数显绿，零为中性灰）
function getSpreadColorClass(val) {
  if (val === null || val === undefined || isNaN(val)) return 'text-gray'
  const num = Number(val)
  if (num > 0) return 'text-danger' // 正数为红
  if (num < 0) return 'text-green'  // 负数为绿
  return 'text-gray'
}

// 极值数据标签生成函数（自适应圆角胶囊标签，支持色彩定制，彻底消除数字溢出）
function createMinMaxMarkPoint(color = '#2563eb', isInteger = false) {
  return {
    symbol: 'circle',
    symbolSize: 5,
    itemStyle: {
      color: color,
      borderColor: '#ffffff',
      borderWidth: 1.5,
    },
    data: [
      {
        type: 'max',
        name: '最高',
        label: {
          position: 'top',
          distance: 6,
        },
      },
      {
        type: 'min',
        name: '最低',
        label: {
          position: 'bottom',
          distance: 6,
        },
      },
    ],
    label: {
      show: true,
      backgroundColor: color,
      borderRadius: 4,
      padding: [2.5, 6.5],
      color: '#ffffff',
      fontSize: 10,
      fontWeight: '600',
      shadowBlur: 4,
      shadowColor: 'rgba(0, 0, 0, 0.25)',
      shadowOffsetY: 1,
      formatter: (params) => {
        const val = params.value
        if (val === null || val === undefined || isNaN(val)) return ''
        const isMax = params.data.type === 'max'
        const prefix = isMax ? '▲ ' : '▼ '
        const numStr = isInteger ? String(Math.round(val)) : Number(val).toFixed(2)
        return `${prefix}${params.name} ${numStr}`
      },
    },
  }
}

function isPointNegative(item) {
  return (item.day_ahead_price !== null && item.day_ahead_price < 0) ||
         (item.real_time_price !== null && item.real_time_price < 0)
}

// 判定某一时段是否满足负电价条件：在当前勾选显示的日前电价和实时电价指标中，至少有一个是负电价
function isItemNegativeBySelection(item) {
  if (!item) return false
  const checkDayAhead = visibleSeries.value.dayAhead && item.day_ahead_price !== null && item.day_ahead_price < 0
  const checkRealTime = visibleSeries.value.realTime && item.real_time_price !== null && item.real_time_price < 0

  if (visibleSeries.value.dayAhead || visibleSeries.value.realTime) {
    return checkDayAhead || checkRealTime
  }
  // 极端兜底（若日前与实时均未勾选，例如仅勾选价差）：按存在任一负电价判定
  return (item.day_ahead_price !== null && item.day_ahead_price < 0) ||
         (item.real_time_price !== null && item.real_time_price < 0)
}

// 判定时段均价是否为负电价
function isPeriodNegative(item) {
  if (!item) return false
  return (item.avg_day_ahead_price !== null && item.avg_day_ahead_price < 0) ||
         (item.avg_real_time_price !== null && item.avg_real_time_price < 0) ||
         (item.negative_days_count > 0)
}

// 在当前勾选的时段均价指标中判定是否满足负电价
function isPeriodItemNegativeBySelection(item) {
  if (!item) return false
  const checkDayAhead = visiblePeriodSeries.value.dayAheadAvg && item.avg_day_ahead_price !== null && item.avg_day_ahead_price < 0
  const checkRealTime = visiblePeriodSeries.value.realTimeAvg && item.avg_real_time_price !== null && item.avg_real_time_price < 0

  if (visiblePeriodSeries.value.dayAheadAvg || visiblePeriodSeries.value.realTimeAvg) {
    return checkDayAhead || checkRealTime
  }
  return isPeriodNegative(item)
}

// 判定月度均价是否为负电价
function isMonthlyNegative(item) {
  if (!item) return false
  return (item.avg_day_ahead_price !== null && item.avg_day_ahead_price < 0) ||
         (item.avg_real_time_price !== null && item.avg_real_time_price < 0) ||
         (item.negative_count > 0)
}

// 在当前勾选的月度均价指标中判定是否满足负电价
function isMonthlyItemNegativeBySelection(item) {
  if (!item) return false
  const checkDayAhead = visibleMonthlySeries.value.dayAheadAvg && item.avg_day_ahead_price !== null && item.avg_day_ahead_price < 0
  const checkRealTime = visibleMonthlySeries.value.realTimeAvg && item.avg_real_time_price !== null && item.avg_real_time_price < 0

  if (visibleMonthlySeries.value.dayAheadAvg || visibleMonthlySeries.value.realTimeAvg) {
    return checkDayAhead || checkRealTime
  }
  return isMonthlyNegative(item)
}

// 日度聚合模式展示列表：勾选“仅负电价时段”时按出现负电价的天数过滤
const displayedDailyTrends = computed(() => {
  if (!onlyNegative.value) {
    return dailyTrends.value
  }
  return dailyTrends.value.filter(d => (d.negative_count || 0) > 0)
})

// 表格与卡片展示的数据列表：勾选“仅负电价时段”时根据勾选指标动态过滤
const displayedPoints = computed(() => {
  if (!onlyNegative.value) {
    return points.value
  }
  return points.value.filter(p => isItemNegativeBySelection(p))
})

// -----------------------------------------------------------------------------
// 前端轻量分页切片（核心性能优化：无论总数据有几万条，DOM仅渲染当前页，彻底消除死机卡顿）
// -----------------------------------------------------------------------------
const currentPage = ref(1)
const pageSize = ref(96) // 默认 96 条（刚好 1 天 96 点位，贴合电力现货业务语义）
const pageSizeOptions = [50, 96, 200]

const totalPointsCount = computed(() => displayedPoints.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalPointsCount.value / pageSize.value)))

// 截取当前页展示的时序记录（DOM 节点从 100,000 锐减至 960）
const paginatedPoints = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return displayedPoints.value.slice(start, start + pageSize.value)
})

const showPointsPagination = computed(() => {
  if (viewMode.value === 'single') return true
  if (viewMode.value !== 'range') return false
  if (rangeSubMode.value === 'continuous') return true
  return rangeSubMode.value === 'daily' && dailyTableSubMode.value === 'pointsDetail'
})

function goToPage(page) {
  const target = Math.max(1, Math.min(Number(page) || 1, totalPages.value))
  currentPage.value = target
}

function changePageSize(size) {
  pageSize.value = Number(size) || 96
  currentPage.value = 1
}

// 切换查询日期、模式或过滤条件时自动重置为第 1 页
watch([selectedDate, rangeStartDate, rangeEndDate, viewMode, rangeSubMode, dailyTableSubMode, onlyNegative], () => {
  currentPage.value = 1
})

// 时段聚合模式表格与卡片展示列表
const displayedPeriodTrends = computed(() => {
  if (!onlyNegative.value) {
    return periodTrends.value
  }
  return periodTrends.value.filter(p => isPeriodItemNegativeBySelection(p))
})

// 月度聚合模式表格与卡片展示列表
const displayedMonthlyTrends = computed(() => {
  if (!onlyNegative.value) {
    return monthlyTrends.value
  }
  return monthlyTrends.value.filter(m => isMonthlyItemNegativeBySelection(m))
})

// 仅负电价时段切换事件：统一在前端保留完整轴并按勾选指标断点展示，避免破坏区间分布统计与连续时间轴
function onNegativeFilterChange() {
  renderChart()
}

// 切换模式
function switchViewMode(mode) {
  viewMode.value = mode
  fetchData()
}

// 日期前后调整
function shiftDay(offset) {
  const cur = new Date(selectedDate.value)
  if (isNaN(cur.getTime())) return
  cur.setDate(cur.getDate() + offset)
  const y = cur.getFullYear()
  const m = String(cur.getMonth() + 1).padStart(2, '0')
  const d = String(cur.getDate()).padStart(2, '0')
  const nextStr = `${y}-${m}-${d}`

  if (meta.value.min_date && nextStr < meta.value.min_date) return
  if (meta.value.max_date && nextStr > meta.value.max_date) return

  selectedDate.value = nextStr
  fetchData()
}

function setLatestDay() {
  if (meta.value.max_date) {
    selectedDate.value = meta.value.max_date
    fetchData()
  }
}

function setQuickRange(days) {
  const maxD = meta.value.max_date ? new Date(meta.value.max_date) : new Date(defaultLatestDate)
  rangeEndDate.value = meta.value.max_date || defaultLatestDate

  if (days === 'all') {
    rangeStartDate.value = meta.value.min_date || '2026-01-01'
  } else {
    const sDate = new Date(maxD)
    sDate.setDate(sDate.getDate() - (days - 1))
    const y = sDate.getFullYear()
    const m = String(sDate.getMonth() + 1).padStart(2, '0')
    const d = String(sDate.getDate()).padStart(2, '0')
    rangeStartDate.value = `${y}-${m}-${d}`
  }
  fetchData()
}

// 获取 Meta 元数据
async function fetchMeta() {
  try {
    const data = await getSpotElectricityMeta(projectKey)
    if (data && data.ok && data.has_data) {
      meta.value = data
      if (data.max_date) {
        selectedDate.value = data.max_date
        rangeEndDate.value = data.max_date
        // 默认近12天
        const d = new Date(data.max_date)
        d.setDate(d.getDate() - 11)
        const y = d.getFullYear()
        const m = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        rangeStartDate.value = `${y}-${m}-${day}`
      }
    }
  } catch (err) {
    console.error('获取电力现货元数据失败:', err)
  }
}

// 主数据加载
let dataRequest = 0
async function fetchData() {
  const request = ++dataRequest
  loading.value = true
  loadError.value = ''
  try {
    let sDate = selectedDate.value
    let eDate = selectedDate.value

    if (viewMode.value === 'range') {
      if (rangeStartDate.value && rangeEndDate.value && rangeStartDate.value > rangeEndDate.value) {
        const tmp = rangeStartDate.value
        rangeStartDate.value = rangeEndDate.value
        rangeEndDate.value = tmp
      }
      sDate = rangeStartDate.value
      eDate = rangeEndDate.value
    }

    // 1. 获取汇总 Summary
    const sumData = await getSpotElectricitySummary(projectKey, sDate, eDate)
    if (request !== dataRequest) return
    if (sumData && sumData.ok) {
      summary.value = sumData.data
    }

    // 2. 获取点位 Points（始终拉取完整时序点位，保证区间连续时间轴、电量分布统计与仅负电价本地断点过滤口径一致）
    const pData = await getSpotElectricityPoints(projectKey, {
      startDate: sDate,
      endDate: eDate,
      onlyNegative: false,
      limit: null,
    })
    if (request !== dataRequest) return
    if (pData && pData.ok) {
      points.value = pData.items || []
    }

    // 3. 区间模式下额外获取日度趋势、时段聚合与月度聚合平均走势
    if (viewMode.value === 'range') {
      const [tData, pTrendData, mTrendData] = await Promise.all([
        getSpotElectricityDailyTrends(projectKey, sDate, eDate),
        getSpotElectricityPeriodTrends(projectKey, sDate, eDate),
        getSpotElectricityMonthlyTrends(projectKey, sDate, eDate),
      ])
      if (request !== dataRequest) return
      if (tData && tData.ok) {
        dailyTrends.value = tData.days || []
      }
      if (pTrendData && pTrendData.ok) {
        periodTrends.value = pTrendData.periods || []
      }
      if (mTrendData && mTrendData.ok) {
        monthlyTrends.value = mTrendData.months || []
      }
    }

    // 数据加载完毕后在 finally 中进行渲染
  } catch (err) {
    if (request !== dataRequest) return
    console.error('加载电力现货数据失败:', err)
    loadError.value = err instanceof Error ? err.message : '获取电力现货数据失败，请检查网络或刷新重试'
    summary.value = null
    points.value = []; dailyTrends.value = []; monthlyTrends.value = []; periodTrends.value = []
    showPlantSales.value = false
  } finally {
    if (request === dataRequest) {
      loading.value = false
      await nextTick()
      if (request === dataRequest) renderChart()
      setTimeout(() => {
        if (request === dataRequest && chartInstance && chartRef.value && chartRef.value.clientWidth > 0) {
          chartInstance.resize()
        }
      }, 60)
    }
  }
}

// 渲染 ECharts
/**
 * 构造单日分时与区间“连续显示”共用的 15 分钟电价/价差 ECharts Option。
 * 当点数较大时不进行降采样，仅关闭平滑、面积阴影和动画以保证完整呈现每一点并维持流畅交互。
 */
function buildPointSeriesChartOption(timeline, { isContinuous = false } = {}) {
  const xData = timeline.map(p => (isContinuous ? (p.axisLabel || `${p.trade_date} ${p.time_label}`) : p.time_label))
  const isLargeSeries = timeline.length > 1000

  const mapMetricValue = (p, field) => {
    if (!p || p.__missing) return null
    if (onlyNegative.value && !isItemNegativeBySelection(p)) return null
    return p[field]
  }

  const daPrices = timeline.map(p => mapMetricValue(p, 'day_ahead_price'))
  const rtPrices = timeline.map(p => mapMetricValue(p, 'real_time_price'))
  const spreads = timeline.map(p => mapMetricValue(p, 'price_spread'))

  const hasPrice = visibleSeries.value.dayAhead || visibleSeries.value.realTime
  const hasSpread = visibleSeries.value.spread
  const series = []

  if (visibleSeries.value.dayAhead) {
    series.push({
      name: '日前电价',
      type: 'line',
      yAxisIndex: 0,
      data: daPrices,
      smooth: !isLargeSeries,
      connectNulls: false,
      showSymbol: onlyNegative.value && timeline.length <= 2000,
      symbolSize: 6,
      lineStyle: { width: isLargeSeries ? 1.5 : 2.5, color: '#2563eb' },
      ...(isLargeSeries ? {} : {
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.18)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.01)' },
          ]),
        },
      }),
      markPoint: createMinMaxMarkPoint('#2563eb', false),
      markLine: {
        silent: true,
        symbol: 'none',
        data: [{ yAxis: 0, lineStyle: { color: '#ef4444', type: 'dashed' } }],
      },
    })
  }

  if (visibleSeries.value.realTime) {
    series.push({
      name: '实时电价',
      type: 'line',
      yAxisIndex: 0,
      data: rtPrices,
      smooth: !isLargeSeries,
      connectNulls: false,
      showSymbol: onlyNegative.value && timeline.length <= 2000,
      symbolSize: 6,
      lineStyle: { width: isLargeSeries ? 1.5 : 2.5, color: '#f97316' },
      ...(isLargeSeries ? {} : {
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(249, 115, 22, 0.18)' },
            { offset: 1, color: 'rgba(249, 115, 22, 0.01)' },
          ]),
        },
      }),
      markPoint: createMinMaxMarkPoint('#ea580c', false),
    })
  }

  if (visibleSeries.value.spread) {
    series.push({
      name: '价差（实时-日前）',
      type: 'bar',
      yAxisIndex: 1,
      data: spreads,
      large: isLargeSeries,
      markPoint: createMinMaxMarkPoint('#059669', false),
      itemStyle: {
        color: params => (params.value >= 0 ? '#ef4444' : '#10b981'),
      },
    })
  }

  let axisLabelConfig = {
    color: '#64748b',
    interval: 7, // 单日每2小时一个刻度
  }

  if (isContinuous) {
    if (timeline.length <= 192) {
      axisLabelConfig = {
        color: '#64748b',
        interval: 7,
        formatter: val => (typeof val === 'string' && val.length >= 16 ? val.slice(5) : val),
      }
    } else {
      const dayStartIndices = []
      let lastDate = ''
      for (let i = 0; i < timeline.length; i++) {
        const d = timeline[i].trade_date || ''
        if (d !== lastDate) {
          dayStartIndices.push(i)
          lastDate = d
        }
      }
      const dayStep = Math.max(1, Math.ceil(dayStartIndices.length / 14))
      const visibleTickSet = new Set()
      for (let k = 0; k < dayStartIndices.length; k += dayStep) {
        visibleTickSet.add(dayStartIndices[k])
      }
      axisLabelConfig = {
        color: '#64748b',
        hideOverlap: true,
        interval: index => visibleTickSet.has(index),
        formatter: val => (typeof val === 'string' && val.length >= 10 ? val.slice(5, 10) : val),
      }
    }
  }

  const option = {
    backgroundColor: 'transparent',
    animation: !isLargeSeries,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params) => {
        if (!params || !params.length) return ''
        const idx = params[0].dataIndex
        const item = timeline[idx] || {}
        const titlePrefix = isContinuous && item.trade_date ? `${item.trade_date} ` : ''
        if (item.__missing) {
          return `<div style="font-weight: bold; margin-bottom: 2px;">#${item.point_index} ${titlePrefix}${item.time_label}</div><div style="color: #94a3b8; font-size: 12px;">（该时段暂无数据）</div>`
        }
        if (onlyNegative.value && !isItemNegativeBySelection(item)) {
          return `<div style="font-weight: bold; margin-bottom: 2px;">#${item.point_index} ${titlePrefix}时刻: ${item.time_label}</div><div style="color: #94a3b8; font-size: 12px;">（当前时段非负电价）</div>`
        }
        let tip = `<div style="font-weight: bold; margin-bottom: 4px;">#${item.point_index} ${titlePrefix}时刻: ${item.time_label} (${item.period_start_time || ''}~${item.period_end_time || ''})</div>`
        if (visibleSeries.value.dayAhead) {
          tip += `<div style="color: #2563eb;">● 日前电价: <strong>${formatNum(item.day_ahead_price)}</strong> 元/MWh</div>`
        }
        if (visibleSeries.value.realTime) {
          tip += `<div style="color: #ea580c;">● 实时电价: <strong>${formatNum(item.real_time_price)}</strong> 元/MWh</div>`
        }
        if (visibleSeries.value.spread) {
          tip += `<div style="color: ${(item.price_spread ?? 0) >= 0 ? '#ef4444' : '#10b981'};">● 价差（实时-日前）: <strong>${(item.price_spread ?? 0) > 0 ? '+' : ''}${formatNum(item.price_spread)}</strong> 元/MWh</div>`
        }
        return tip
      },
    },
    grid: {
      top: 48,
      left: '2%',
      right: '2%',
      bottom: 50,
      containLabel: true,
    },
    legend: {
      show: false,
    },
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: axisLabelConfig,
    },
    yAxis: [
      {
        type: 'value',
        name: hasPrice ? '电价 (元/MWh)' : '',
        show: hasPrice,
        nameTextStyle: { color: '#64748b' },
        splitLine: { lineStyle: { color: '#f1f5f9' } },
        axisLabel: { color: '#64748b' },
      },
      {
        type: 'value',
        name: hasSpread ? '价差 (元/MWh)' : '',
        show: hasSpread,
        nameTextStyle: { color: '#64748b' },
        splitLine: { show: false },
        axisLabel: { color: '#94a3b8' },
      },
    ],
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', bottom: 5, height: 20, borderColor: '#e2e8f0' },
    ],
    series,
  }

  return { option, rows: timeline }
}

function applyPlantSales(option, rows, { fields, suffix = '', include }) {
  return addPlantSalesToOption(option, rows, {
    enabled: showPlantSales.value && canShowPlantSales.value,
    scope: plantSalesScope.value,
    fields,
    suffix,
    include,
  })
}

function renderChart() {
  if (!chartRef.value) return

  // 防护：若当前容器尚未计算出有效宽度，推迟到下一动画帧渲染
  const containerWidth = chartRef.value.clientWidth
  if (containerWidth <= 0) {
    requestAnimationFrame(() => {
      renderChart()
    })
    return
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  if (viewMode.value === 'single') {
    const { option, rows } = buildPointSeriesChartOption(points.value, { isContinuous: false })
    chartInstance.setOption(applyPlantSales(option, rows, {
      fields: ['beihai_total_sales', 'xianghai_total_sales'], suffix: '',
      include: item => !onlyNegative.value || isItemNegativeBySelection(item),
    }), true)
  } else if (rangeSubMode.value === 'continuous') {
    const timeline = buildContinuousTimeline(points.value)
    if (!timeline.length) {
      chartInstance.clear()
      return
    }
    const { option, rows } = buildPointSeriesChartOption(timeline, { isContinuous: true })
    chartInstance.setOption(applyPlantSales(option, rows, {
      fields: ['beihai_total_sales', 'xianghai_total_sales'], suffix: '',
      include: item => !item.__missing && (!onlyNegative.value || isItemNegativeBySelection(item)),
    }), true)
  } else if (rangeSubMode.value === 'daily') {
    // 1. 区间走势：按每日平均值
    const dates = dailyTrends.value.map(d => d.trade_date)
    const daAver = dailyTrends.value.map(d => d.avg_day_ahead_price)
    const rtAver = dailyTrends.value.map(d => d.avg_real_time_price)
    const negCounts = dailyTrends.value.map(d => d.negative_count)

    const hasRangePrice = visibleRangeSeries.value.dayAheadAvg || visibleRangeSeries.value.realTimeAvg
    const hasNegCount = visibleRangeSeries.value.negativeCount

    const series = []

    if (visibleRangeSeries.value.dayAheadAvg) {
      series.push({
        name: '日前日均价',
        type: 'line',
        yAxisIndex: 0,
        data: daAver,
        smooth: true,
        lineStyle: { width: 3, color: '#2563eb' },
        itemStyle: { color: '#2563eb' },
        markPoint: createMinMaxMarkPoint('#2563eb', false),
      })
    }

    if (visibleRangeSeries.value.realTimeAvg) {
      series.push({
        name: '实时日均价',
        type: 'line',
        yAxisIndex: 0,
        data: rtAver,
        smooth: true,
        lineStyle: { width: 3, color: '#f97316' },
        itemStyle: { color: '#f97316' },
        markPoint: createMinMaxMarkPoint('#ea580c', false),
      })
    }

    if (visibleRangeSeries.value.negativeCount) {
      series.push({
        name: '负电价时点数',
        type: 'bar',
        yAxisIndex: 1,
        data: negCounts,
        itemStyle: { color: '#ef4444' },
        markPoint: createMinMaxMarkPoint('#ef4444', true),
      })
    }

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      grid: {
        top: 48,
        left: '2%',
        right: '2%',
        bottom: 50,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b' },
      },
      yAxis: [
        {
          type: 'value',
          name: hasRangePrice ? '日均电价 (元/MWh)' : '',
          show: hasRangePrice,
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          axisLabel: { color: '#64748b' },
        },
        {
          type: 'value',
          name: hasNegCount ? '负电价时点数' : '',
          show: hasNegCount,
          splitLine: { show: false },
          axisLabel: { color: '#94a3b8' },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', bottom: 5, height: 20, borderColor: '#e2e8f0' },
      ],
      series,
    }
    chartInstance.setOption(applyPlantSales(option, dailyTrends.value, {
      fields: ['beihai_sales', 'xianghai_sales'], suffix: '（日合计）',
    }), true)
  } else if (rangeSubMode.value === 'monthly') {
    // 2. 区间走势：按每月平均值
    if (!monthlyTrends.value.length) {
      chartInstance.clear()
      return
    }

    const xData = monthlyTrends.value.map(m => m.month_label)

    const daPrices = monthlyTrends.value.map(m => {
      if (onlyNegative.value && !isMonthlyItemNegativeBySelection(m)) return null
      return m.avg_day_ahead_price
    })
    const rtPrices = monthlyTrends.value.map(m => {
      if (onlyNegative.value && !isMonthlyItemNegativeBySelection(m)) return null
      return m.avg_real_time_price
    })
    const spreads = monthlyTrends.value.map(m => {
      if (onlyNegative.value && !isMonthlyItemNegativeBySelection(m)) return null
      return m.avg_price_spread
    })
    const negCounts = monthlyTrends.value.map(m => {
      if (onlyNegative.value && !isMonthlyItemNegativeBySelection(m)) return null
      return m.negative_count
    })

    const hasPrice = visibleMonthlySeries.value.dayAheadAvg || visibleMonthlySeries.value.realTimeAvg
    const hasSpread = visibleMonthlySeries.value.spread
    const hasNegCount = visibleMonthlySeries.value.negativeCount
    const hasRightAxis = hasSpread || hasNegCount

    const series = []

    if (visibleMonthlySeries.value.dayAheadAvg) {
      series.push({
        name: '日前月均价',
        type: 'line',
        yAxisIndex: 0,
        data: daPrices,
        smooth: true,
        showSymbol: true,
        symbolSize: 7,
        lineStyle: { width: 3, color: '#2563eb' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.18)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.01)' },
          ]),
        },
        markPoint: createMinMaxMarkPoint('#2563eb', false),
        markLine: {
          silent: true,
          symbol: 'none',
          data: [{ yAxis: 0, lineStyle: { color: '#ef4444', type: 'dashed' } }],
        },
      })
    }

    if (visibleMonthlySeries.value.realTimeAvg) {
      series.push({
        name: '实时月均价',
        type: 'line',
        yAxisIndex: 0,
        data: rtPrices,
        smooth: true,
        showSymbol: true,
        symbolSize: 7,
        lineStyle: { width: 3, color: '#f97316' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(249, 115, 22, 0.18)' },
            { offset: 1, color: 'rgba(249, 115, 22, 0.01)' },
          ]),
        },
        markPoint: createMinMaxMarkPoint('#ea580c', false),
      })
    }

    if (visibleMonthlySeries.value.spread) {
      series.push({
        name: '月均价差',
        type: 'bar',
        yAxisIndex: 1,
        data: spreads,
        markPoint: createMinMaxMarkPoint('#059669', false),
        itemStyle: {
          color: (params) => {
            return params.value >= 0 ? '#ef4444' : '#10b981'
          },
        },
      })
    }

    if (visibleMonthlySeries.value.negativeCount) {
      series.push({
        name: '负电价时点数',
        type: 'bar',
        yAxisIndex: 1,
        data: negCounts,
        itemStyle: { color: '#ef4444' },
        markPoint: createMinMaxMarkPoint('#ef4444', true),
      })
    }

    const rightAxisName = hasSpread ? '价差 (元/MWh)' : hasNegCount ? '负电价时点数 (次)' : ''

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params) => {
          if (!params || !params.length) return ''
          const idx = params[0].dataIndex
          const item = monthlyTrends.value[idx] || {}
          if (onlyNegative.value && !isMonthlyItemNegativeBySelection(item)) {
            return `<div style="font-weight: bold; margin-bottom: 2px;">月份: ${item.month_label}</div><div style="color: #94a3b8; font-size: 12px;">（当前月份非负电价月份）</div>`
          }
          let tip = `<div style="font-weight: bold; margin-bottom: 4px;">月份: ${item.month_label}（统计天数: ${item.day_count}天 / ${item.point_count}点）</div>`
          if (visibleMonthlySeries.value.dayAheadAvg) {
            tip += `<div style="color: #2563eb;">● 日前月均价: <strong>${formatNum(item.avg_day_ahead_price)}</strong> 元/MWh</div>`
          }
          if (visibleMonthlySeries.value.realTimeAvg) {
            tip += `<div style="color: #ea580c;">● 实时月均价: <strong>${formatNum(item.avg_real_time_price)}</strong> 元/MWh</div>`
          }
          if (visibleMonthlySeries.value.spread) {
            tip += `<div style="color: ${(item.avg_price_spread ?? 0) >= 0 ? '#ef4444' : '#10b981'};">● 月均价差: <strong>${(item.avg_price_spread ?? 0) > 0 ? '+' : ''}${formatNum(item.avg_price_spread)}</strong> 元/MWh</div>`
          }
          if (visibleMonthlySeries.value.negativeCount) {
            tip += `<div style="color: #ef4444;">● 负电价时点数: <strong>${item.negative_count}</strong> 次</div>`
          }
          return tip
        },
      },
      grid: {
        top: 48,
        left: '2%',
        right: '2%',
        bottom: 50,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: xData,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: { color: '#64748b' },
      },
      yAxis: [
        {
          type: 'value',
          name: hasPrice ? '月均电价 (元/MWh)' : '',
          show: hasPrice,
          nameTextStyle: { color: '#64748b' },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          axisLabel: { color: '#64748b' },
        },
        {
          type: 'value',
          name: rightAxisName,
          show: hasRightAxis,
          nameTextStyle: { color: '#64748b' },
          splitLine: { show: false },
          axisLabel: { color: '#94a3b8' },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', bottom: 5, height: 20, borderColor: '#e2e8f0' },
      ],
      series,
    }
    chartInstance.setOption(applyPlantSales(option, monthlyTrends.value, {
      fields: ['beihai_sales', 'xianghai_sales'], suffix: '（月合计）',
      include: item => !onlyNegative.value || isMonthlyItemNegativeBySelection(item),
    }), true)
  } else {
    // 3. 区间走势：按每个时段的平均值显示从 00:15 到 24:00 的曲线 (96 时段)
    if (!periodTrends.value.length) {
      chartInstance.clear()
      return
    }

    const xData = periodTrends.value.map(p => p.time_label)

    const daPrices = periodTrends.value.map(p => {
      if (onlyNegative.value && !isPeriodItemNegativeBySelection(p)) return null
      return p.avg_day_ahead_price
    })
    const rtPrices = periodTrends.value.map(p => {
      if (onlyNegative.value && !isPeriodItemNegativeBySelection(p)) return null
      return p.avg_real_time_price
    })
    const spreads = periodTrends.value.map(p => {
      if (onlyNegative.value && !isPeriodItemNegativeBySelection(p)) return null
      return p.avg_price_spread
    })
    const negDays = periodTrends.value.map(p => {
      if (onlyNegative.value && !isPeriodItemNegativeBySelection(p)) return null
      return p.negative_days_count
    })

    const hasPrice = visiblePeriodSeries.value.dayAheadAvg || visiblePeriodSeries.value.realTimeAvg
    const hasSpread = visiblePeriodSeries.value.spread
    const hasNegDays = visiblePeriodSeries.value.negativeDays
    const hasRightAxis = hasSpread || hasNegDays

    const series = []

    if (visiblePeriodSeries.value.dayAheadAvg) {
      series.push({
        name: '日前时段均价',
        type: 'line',
        yAxisIndex: 0,
        data: daPrices,
        smooth: true,
        showSymbol: onlyNegative.value,
        symbolSize: 6,
        lineStyle: { width: 2.5, color: '#2563eb' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.18)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.01)' },
          ]),
        },
        markPoint: createMinMaxMarkPoint('#2563eb', false),
        markLine: {
          silent: true,
          symbol: 'none',
          data: [{ yAxis: 0, lineStyle: { color: '#ef4444', type: 'dashed' } }],
        },
      })
    }

    if (visiblePeriodSeries.value.realTimeAvg) {
      series.push({
        name: '实时时段均价',
        type: 'line',
        yAxisIndex: 0,
        data: rtPrices,
        smooth: true,
        showSymbol: onlyNegative.value,
        symbolSize: 6,
        lineStyle: { width: 2.5, color: '#f97316' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(249, 115, 22, 0.18)' },
            { offset: 1, color: 'rgba(249, 115, 22, 0.01)' },
          ]),
        },
        markPoint: createMinMaxMarkPoint('#ea580c', false),
      })
    }

    if (visiblePeriodSeries.value.spread) {
      series.push({
        name: '时段平均价差',
        type: 'bar',
        yAxisIndex: 1,
        data: spreads,
        markPoint: createMinMaxMarkPoint('#059669', false),
        itemStyle: {
          color: (params) => {
            return params.value >= 0 ? '#ef4444' : '#10b981'
          },
        },
      })
    }

    if (visiblePeriodSeries.value.negativeDays) {
      series.push({
        name: '负电价发生天数',
        type: 'bar',
        yAxisIndex: 1,
        data: negDays,
        itemStyle: { color: '#ef4444' },
        markPoint: createMinMaxMarkPoint('#ef4444', true),
      })
    }

    const rightAxisName = hasSpread ? '价差 (元/MWh)' : hasNegDays ? '负电价天数 (天)' : ''

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params) => {
          if (!params || !params.length) return ''
          const idx = params[0].dataIndex
          const item = periodTrends.value[idx] || {}
          if (onlyNegative.value && !isPeriodItemNegativeBySelection(item)) {
            return `<div style="font-weight: bold; margin-bottom: 2px;">#${item.point_index} 时刻: ${item.time_label}</div><div style="color: #94a3b8; font-size: 12px;">（当前时段均价非负电价）</div>`
          }
          let tip = `<div style="font-weight: bold; margin-bottom: 4px;">#${item.point_index} 时刻: ${item.time_label} (${item.period_start_time || ''}~${item.period_end_time || ''})</div>`
          tip += `<div style="color: #64748b; font-size: 11.5px; margin-bottom: 4px;">统计区间: ${rangeStartDate.value} 至 ${rangeEndDate.value}</div>`
          if (visiblePeriodSeries.value.dayAheadAvg) {
            tip += `<div style="color: #2563eb;">● 日前均价: <strong>${formatNum(item.avg_day_ahead_price)}</strong> 元/MWh <span style="color:#94a3b8;font-size:11px;">[${formatNum(item.min_day_ahead_price)}~${formatNum(item.max_day_ahead_price)}]</span></div>`
          }
          if (visiblePeriodSeries.value.realTimeAvg) {
            tip += `<div style="color: #ea580c;">● 实时均价: <strong>${formatNum(item.avg_real_time_price)}</strong> 元/MWh <span style="color:#94a3b8;font-size:11px;">[${formatNum(item.min_real_time_price)}~${formatNum(item.max_real_time_price)}]</span></div>`
          }
          if (visiblePeriodSeries.value.spread) {
            tip += `<div style="color: ${(item.avg_price_spread ?? 0) >= 0 ? '#ef4444' : '#10b981'};">● 平均价差: <strong>${(item.avg_price_spread ?? 0) > 0 ? '+' : ''}${formatNum(item.avg_price_spread)}</strong> 元/MWh</div>`
          }
          if (visiblePeriodSeries.value.negativeDays) {
            tip += `<div style="color: #ef4444;">● 负电价天数: <strong>${item.negative_days_count}</strong> 天</div>`
          }
          return tip
        },
      },
      grid: {
        top: 48,
        left: '2%',
        right: '2%',
        bottom: 50,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: xData,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#cbd5e1' } },
        axisLabel: {
          color: '#64748b',
          interval: 7, // 每2小时一个刻度
        },
      },
      yAxis: [
        {
          type: 'value',
          name: hasPrice ? '时段均价 (元/MWh)' : '',
          show: hasPrice,
          nameTextStyle: { color: '#64748b' },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          axisLabel: { color: '#64748b' },
        },
        {
          type: 'value',
          name: rightAxisName,
          show: hasRightAxis,
          nameTextStyle: { color: '#64748b' },
          splitLine: { show: false },
          axisLabel: { color: '#94a3b8' },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', bottom: 5, height: 20, borderColor: '#e2e8f0' },
      ],
      series,
    }
    chartInstance.setOption(applyPlantSales(option, periodTrends.value, {
      fields: ['avg_beihai_sales', 'avg_xianghai_sales'], suffix: '（时段均值）',
      include: item => !onlyNegative.value || isPeriodItemNegativeBySelection(item),
    }), true)
  }

  // 统一显式触发自适应重排
  chartInstance.resize()
}

function notifySpotExport(fileName, mode, rowCount) {
  recordDailyReportOperationLog(projectKey, {
    unit: '电力现货交易中心',
    action_type: 'EXPORT_SHEET_DATA',
    action_desc: `导出电力现货数据 Excel（${fileName}，共 ${rowCount} 行）`,
    resource_id: `spot_electricity:${mode}`,
    after_value: { file_name: fileName, mode, row_count: rowCount },
  })
}

// 导出 Excel / CSV
function exportCurrentData() {
  if (viewMode.value === 'range' && rangeSubMode.value === 'monthly') {
    const target = displayedMonthlyTrends.value.length ? displayedMonthlyTrends.value : monthlyTrends.value
    if (!target.length) return

    const exportRows = target.map((p, idx) => ({
      '序号': idx + 1,
      '月份': p.month_label,
      '统计天数': p.day_count,
      '统计点位数': p.point_count,
      '日前月均电价（元/兆瓦时）': p.avg_day_ahead_price,
      '实时月均电价（元/兆瓦时）': p.avg_real_time_price,
      '月均价差（元/兆瓦时）': p.avg_price_spread,
      '负电价时点数（次）': p.negative_count,
      '北海月度总售电量(MWh)': p.beihai_sales,
      '香海月度总售电量(MWh)': p.xianghai_sales,
      '两厂月度总售电量(MWh)': p.total_sales,
    }))

    const worksheet = XLSX.utils.json_to_sheet(exportRows)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '月度均价走势')

    const fileName = `辽宁电力现货月度均价走势_${rangeStartDate.value}_至_${rangeEndDate.value}.xlsx`
    XLSX.writeFile(workbook, fileName)
    notifySpotExport(fileName, 'range_monthly', exportRows.length)
    return
  }

  if (viewMode.value === 'range' && rangeSubMode.value === 'period') {
    const target = displayedPeriodTrends.value.length ? displayedPeriodTrends.value : periodTrends.value
    if (!target.length) return

    const exportRows = target.map((p) => ({
      '时点序号': p.point_index,
      '官方时刻': p.time_label,
      '起始时间': p.period_start_time || '',
      '截止时间': p.period_end_time || '',
      '日前平均电价（元/兆瓦时）': p.avg_day_ahead_price,
      '日前最高电价（元/兆瓦时）': p.max_day_ahead_price,
      '日前最低电价（元/兆瓦时）': p.min_day_ahead_price,
      '实时平均电价（元/兆瓦时）': p.avg_real_time_price,
      '实时最高电价（元/兆瓦时）': p.max_real_time_price,
      '实时最低电价（元/兆瓦时）': p.min_real_time_price,
      '时段平均价差（元/兆瓦时）': p.avg_price_spread,
      '负电价发生天数（天）': p.negative_days_count,
      '北海时段平均售电量(MWh)': p.avg_beihai_sales,
      '香海时段平均售电量(MWh)': p.avg_xianghai_sales,
      '两厂时段平均总售电量(MWh)': p.avg_total_sales,
    }))

    const worksheet = XLSX.utils.json_to_sheet(exportRows)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '时段均价走势')

    const fileName = `辽宁电力现货时段均价走势_${rangeStartDate.value}_至_${rangeEndDate.value}.xlsx`
    XLSX.writeFile(workbook, fileName)
    notifySpotExport(fileName, 'range_period', exportRows.length)
    return
  }

  if (viewMode.value === 'range' && rangeSubMode.value === 'daily' && dailyTableSubMode.value === 'dailySummary') {
    const target = displayedDailyTrends.value.length ? displayedDailyTrends.value : dailyTrends.value
    if (!target.length) return

    const exportRows = target.map((p, idx) => ({
      '序号': idx + 1,
      '交易日期': p.trade_date,
      '日前日均电价（元/兆瓦时）': p.avg_day_ahead_price,
      '实时日均电价（元/兆瓦时）': p.avg_real_time_price,
      '日均价差（元/兆瓦时）': p.avg_price_spread,
      '负电价时点数（次）': p.negative_count,
      '北海日总售电量(MWh)': p.beihai_sales,
      '香海日总售电量(MWh)': p.xianghai_sales,
      '两厂日总售电量(MWh)': p.total_sales,
    }))

    const worksheet = XLSX.utils.json_to_sheet(exportRows)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '日度均价走势')

    const fileName = `辽宁电力现货日均电价走势_${rangeStartDate.value}_至_${rangeEndDate.value}.xlsx`
    XLSX.writeFile(workbook, fileName)
    notifySpotExport(fileName, 'range_daily', exportRows.length)
    return
  }

  if (!points.value.length) return

  const exportTarget = displayedPoints.value.length ? displayedPoints.value : points.value
  const exportRows = exportTarget.map((p) => ({
    '交易日期': p.trade_date,
    '时点序号': p.point_index,
    '官方时刻': p.time_label,
    '起始时间': p.period_start_time || '',
    '截止时间': p.period_end_time || '',
    '日前电价（元/兆瓦时）': p.day_ahead_price,
    '实时电价（元/兆瓦时）': p.real_time_price,
    '价差（实时-日前）（元/兆瓦时）': p.price_spread,
    '北海#1机组售电量(MWh)': p.beihai_unit1_sales,
    '北海#2机组售电量(MWh)': p.beihai_unit2_sales,
    '北海#3机组售电量(MWh)': p.beihai_unit3_sales,
    '北海售电量合计(MWh)': p.beihai_total_sales,
    '香海#1机组售电量(MWh)': p.xianghai_unit1_sales,
    '香海#2机组售电量(MWh)': p.xianghai_unit2_sales,
    '香海#3机组售电量(MWh)': p.xianghai_unit3_sales,
    '香海#4机组售电量(MWh)': p.xianghai_unit4_sales,
    '香海售电量合计(MWh)': p.xianghai_total_sales,
    '两厂总售电量(MWh)': p.total_power_sales,
    '备注': p.remarks || '',
  }))

  const worksheet = XLSX.utils.json_to_sheet(exportRows)
  const workbook = XLSX.utils.book_new()
  const sheetName = viewMode.value === 'single' ? '单日15分钟明细' : '15分钟分时明细'
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName)

  const negSuffix = onlyNegative.value ? '_仅负电价时段' : ''
  const fileName = viewMode.value === 'single'
    ? `辽宁电力现货15分钟数据_${selectedDate.value}${negSuffix}.xlsx`
    : `辽宁电力现货15分钟分时明细_${rangeStartDate.value}_至_${rangeEndDate.value}${negSuffix}.xlsx`

  XLSX.writeFile(workbook, fileName)
  notifySpotExport(fileName, viewMode.value === 'single' ? 'single_points' : 'range_points', exportRows.length)
}

function handleResize() {
  checkMobileScreen()
  if (chartInstance && chartRef.value && chartRef.value.clientWidth > 0) {
    chartInstance.resize()
  }
}

let resizeObserver = null

function initResizeObserver() {
  if (!chartRef.value || typeof ResizeObserver === 'undefined') return
  resizeObserver = new ResizeObserver(() => {
    if (chartInstance && chartRef.value && chartRef.value.clientWidth > 0) {
      chartInstance.resize()
    }
  })
  resizeObserver.observe(chartRef.value)
}

// ==============================================================================
// Global_admin 现货数据自动获取与系统控制管理
// ==============================================================================
const auth = useAuthStore()
const canImportBills = computed(() => String(auth.user?.group || '').trim().toLowerCase() === 'global_admin')
const isGlobalAdmin = computed(() => {
  return auth.user?.group === 'Global_admin' || Boolean(auth.canAccessAdminConsole)
})

const showAdminControlModal = ref(false)
const syncConfigLoading = ref(false)
const savingSyncConfig = ref(false)
const manualSyncLoading = ref(false)
const manualSyncMode = ref('yesterday') // 'yesterday' | 'specific'

// 动态计算昨日日期（本地/北京时间），用于默认补录日期和单选框提示
const yesterdayDateStr = computed(() => {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
})

const manualSyncSpecificDate = ref(yesterdayDateStr.value)
const syncFeedbackMsg = ref('')
const syncFeedbackType = ref('success') // 'success' | 'warning' | 'error'

// 某日数据已存在时的覆盖确认状态
const showOverwriteConfirm = ref(false)
const overwriteTargetDate = ref('')
const overwriteConfirmMessage = ref('')
const overwritePendingPoints = ref(0)
const overwritePendingPricePoints = ref(0)

watch([manualSyncMode, manualSyncSpecificDate], () => {
  // 切换拉取模式或日期时重置覆盖确认框
  showOverwriteConfirm.value = false
})

const syncConfig = ref({
  enabled: true,
  cron_time: '07:40',
  retry_interval_minutes: 20,
  max_retries_per_day: 30,
  last_sync_date: '',
  last_run_time: '',
  last_run_status: 'IDLE',
  last_run_message: '',
  next_run_time: '',
  retry_count_today: 0,
})

async function openAdminControlModal() {
  showAdminControlModal.value = true
  syncFeedbackMsg.value = ''
  showOverwriteConfirm.value = false
  // 打开控制台时，若尚未指定日期，默认填入昨日
  if (!manualSyncSpecificDate.value) {
    manualSyncSpecificDate.value = yesterdayDateStr.value
  }
  await fetchSyncConfig()
}

async function fetchSyncConfig() {
  if (!isGlobalAdmin.value) return
  syncConfigLoading.value = true
  try {
    const res = await getSpotElectricitySyncConfig(projectKey)
    if (res && res.data) {
      syncConfig.value = { ...syncConfig.value, ...res.data }
    }
  } catch (err) {
    console.error('获取现货同步配置失败:', err)
  } finally {
    syncConfigLoading.value = false
  }
}

async function handleSaveSyncConfig() {
  savingSyncConfig.value = true
  syncFeedbackMsg.value = ''
  try {
    const res = await saveSpotElectricitySyncConfig(projectKey, {
      enabled: Boolean(syncConfig.value.enabled),
      cron_time: String(syncConfig.value.cron_time || '07:40').trim(),
      retry_interval_minutes: Number(syncConfig.value.retry_interval_minutes) || 20,
    })
    if (res && res.data) {
      syncConfig.value = { ...syncConfig.value, ...res.data }
      syncFeedbackMsg.value = res.message || '自动同步配置保存成功并已即时生效！'
      syncFeedbackType.value = 'success'
    }
  } catch (err) {
    syncFeedbackMsg.value = err.message || '保存配置失败'
    syncFeedbackType.value = 'error'
  } finally {
    savingSyncConfig.value = false
  }
}

async function handleManualSync(forceOverwrite = false) {
  manualSyncLoading.value = true
  syncFeedbackMsg.value = ''
  try {
    // 若用户点击的是确认覆盖，严格锁定待覆盖的目标日期
    let targetDate = ''
    if (forceOverwrite && overwriteTargetDate.value) {
      targetDate = overwriteTargetDate.value
    } else if (manualSyncMode.value === 'specific') {
      targetDate = String(manualSyncSpecificDate.value || yesterdayDateStr.value).trim()
    } else {
      targetDate = yesterdayDateStr.value
    }

    const res = await manualSyncSpotElectricity(projectKey, {
      date: targetDate,
      overwrite: Boolean(forceOverwrite),
    })

    // 若数据库中已存在某日数据且未确认覆盖，提示用户并呼出确认选项
    if (res && res.status === 'ALREADY_EXISTS') {
      const existDate = res.target_date || targetDate || yesterdayDateStr.value
      overwriteTargetDate.value = existDate
      overwriteConfirmMessage.value = res.message || `数据库中已存在【${existDate}】的数据，是否确认覆盖？`
      overwritePendingPoints.value = res.points_count || 96
      overwritePendingPricePoints.value = res.price_points || 0
      showOverwriteConfirm.value = true
      syncFeedbackMsg.value = `⚠️ 检测到【${existDate}】已存在 ${overwritePendingPricePoints.value} 个电价点位，请在上方确认是否覆盖。`
      syncFeedbackType.value = 'warning'
      return
    }

    if (res && res.ok) {
      showOverwriteConfirm.value = false
      syncFeedbackMsg.value = res.message || '手动拉取入库成功！'
      syncFeedbackType.value = 'success'
      // 成功后若有目标日期，自动将主看板日期定位至新入库的数据
      if (res.target_date) {
        selectedDate.value = res.target_date
      }
      await fetchMeta()
      await fetchData()
      await fetchSyncConfig()
    } else {
      showOverwriteConfirm.value = false
      syncFeedbackMsg.value = res?.message || '发改委数据尚未发布或接口未返回有效数据'
      syncFeedbackType.value = 'warning'
    }
  } catch (err) {
    showOverwriteConfirm.value = false
    syncFeedbackMsg.value = err.message || '手动拉取请求失败，请稍后重试'
    syncFeedbackType.value = 'error'
  } finally {
    manualSyncLoading.value = false
  }
}

// 用户确认覆盖
async function handleConfirmOverwrite() {
  await handleManualSync(true)
}

// 用户取消覆盖
function handleCancelOverwrite() {
  showOverwriteConfirm.value = false
  syncFeedbackMsg.value = `已取消对【${overwriteTargetDate.value}】数据的覆盖操作。`
  syncFeedbackType.value = 'warning'
}

onMounted(async () => {
  if (route.query.pageName === '电力市场数据') {
    router.replace({
      query: {
        ...route.query,
        pageName: '电力现货市场数据',
      },
    })
  }
  checkMobileScreen()
  window.addEventListener('resize', handleResize)
  initResizeObserver()
  await fetchMeta()
  await fetchData()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
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
.spot-elec-view {
  min-height: 100vh;
  background-color: #f8fafc;
}

.spot-elec-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  padding: 12px 16px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13.5px;
}

.btn-retry {
  border: 1px solid #f87171;
  color: #b91c1c;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.empty-cell {
  text-align: center;
  padding: 40px 16px !important;
  color: #94a3b8;
  font-size: 13.5px;
}

.empty-cards {
  text-align: center;
  padding: 30px 16px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
  color: #94a3b8;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.table-loading-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}

/* 顶部 Banner：天蓝色过渡效果质感卡片 */
.banner-card {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 35%, #bae6fd 70%, #7dd3fc 100%);
  color: #0369a1;
  padding: 18px 22px;
  border-radius: 12px;
  border: 1px solid #bae6fd;
  box-shadow: 0 4px 16px rgba(14, 165, 233, 0.12);
}

.banner-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.banner-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.banner-icon {
  font-size: 26px;
  width: 48px;
  height: 48px;
  background: #ffffff;
  color: #0284c7;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.95);
  box-shadow: 0 2px 8px rgba(2, 132, 199, 0.15);
}

.banner-title {
  margin: 0;
  font-size: 19px;
  font-weight: 700;
  color: #0369a1;
}

.banner-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #0284c7;
  opacity: 0.95;
}

.banner-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.meta-tag {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(186, 230, 253, 0.85);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12.5px;
  color: #0369a1;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 1px 3px rgba(14, 165, 233, 0.08);
}

.meta-tag strong {
  color: #0c4a6e;
}

.dot.live {
  width: 8px;
  height: 8px;
  background-color: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.5);
}

/* 工具栏：始终分为两行布局 */
.control-toolbar {
  padding: 14px 20px;
  background: #ffffff;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid #e2e8f0;
}

.toolbar-row {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-row-top {
  justify-content: flex-start;
  gap: 14px;
}

.toolbar-row-bottom {
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px dashed #f1f5f9;
}

.toolbar-sub-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.single-mode-hint {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.hint-badge {
  background: #eff6ff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
}

.hint-text {
  color: #64748b;
  font-size: 12.5px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-left: auto;
}

.view-mode-tabs {
  display: flex;
  background: #f1f5f9;
  padding: 3px;
  border-radius: 8px;
}

.mode-tab-btn {
  border: none;
  background: transparent;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-tab-btn.active {
  background: #ffffff;
  color: #1e293b;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.date-picker-group,
.range-picker-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.form-input.date-input {
  border: 1px solid #cbd5e1;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 13.5px;
  color: #1e293b;
  background: #ffffff;
  outline: none;
}

.form-input.date-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 6px;
}

.range-sep {
  color: #64748b;
  font-size: 13px;
}

.quick-range-chips {
  display: flex;
  gap: 6px;
  align-items: center;
}

.chip-btn {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.chip-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.btn.primary-outline.query-btn {
  border: 1px solid #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}

.range-submode-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
  border: 1px solid #e2e8f0;
}

.submode-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  font-size: 12.5px;
  font-weight: 500;
  color: #64748b;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.submode-btn:hover {
  color: #1e293b;
}

.submode-btn.active {
  background: #ffffff;
  color: #2563eb;
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}


.btn.icon-btn {
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.btn.quick-btn {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12.5px;
  cursor: pointer;
  color: #334155;
}

.checkbox-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #475569;
  user-select: none;
}

.plant-sales-filter-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.plant-sales-scope-tabs {
  display: inline-flex;
  align-items: center;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  padding: 2px;
  gap: 2px;
}

.scope-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  padding: 3px 9px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.scope-btn:hover {
  color: #1e293b;
}

.scope-btn.active {
  background: #ffffff;
  color: #0f172a;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.scope-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.btn.primary.export-btn {
  background: #2563eb;
  color: #ffffff;
  border: none;
  padding: 7px 16px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.2);
  transition: background 0.15s;
}

.btn.primary.export-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn.primary.export-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* KPI 大盘指标板块 */
.kpi-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.kpi-grid {
  display: grid;
  gap: 12px;
}

.kpi-grid-prices {
  grid-template-columns: repeat(4, 1fr);
}

.kpi-grid-sales {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;
}

.sales-basis-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 14px;
  padding: 6px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
}

.sales-basis-label {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
}

.basis-status-badge {
  font-size: 11.5px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}

.basis-status-badge.is-rt {
  background: #e0f2fe;
  color: #0369a1;
}

.basis-status-badge.is-da {
  background: #fef3c7;
  color: #b45309;
}

.basis-hint {
  font-size: 11.5px;
  font-weight: 400;
  color: #94a3b8;
}

.basis-tabs {
  display: inline-flex;
  align-items: center;
  background: #e2e8f0;
  border-radius: 7px;
  padding: 2px;
  gap: 2px;
}

.basis-btn {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 11px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.basis-btn:hover {
  color: #1e293b;
}

.basis-btn.active {
  background: #ffffff;
  color: #0f172a;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.plant-title-wrap {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.basis-ref-tag {
  font-size: 10.5px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
}

.plant-card.is-da-basis {
  background: #fffdf7;
}

.spot-fee-diff {
  display: inline-block;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.02);
}

.kpi-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12.5px;
  color: #64748b;
  font-weight: 500;
}

.kpi-unit {
  font-size: 11px;
  color: #94a3b8;
}

.kpi-value {
  font-size: 22px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: #0f172a;
}

.plant-card { min-width: 0; gap: 14px; border-top: 3px solid #0891b2; }
.plant-card + .plant-card { border-top-color: #8b5cf6; }
.plant-heading { display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 4px 10px; }
.plant-heading strong { font-size: 14px; color: #334155; }
.plant-heading span { font-size: 11px; color: #94a3b8; }
.plant-metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin: 0; }
.plant-metrics > div { min-width: 0; }
.plant-metrics > div + div { border-left: 1px solid #f1f5f9; padding-left: 10px; }
.plant-sales-toggle.is-disabled { color: #94a3b8; cursor: not-allowed; }
.plant-sales-toggle input:disabled { cursor: not-allowed; }
.plant-metrics dt { font-size: 11.5px; line-height: 1.5; color: #64748b; margin-bottom: 4px; }
.plant-metrics dd { margin: 0; font-size: 14px; line-height: 1.6; font-weight: 600; color: #0f172a; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.plant-price-difference { font-size: 11px; font-weight: 400; color: #64748b; white-space: nowrap; }
.plant-metrics dd.metric-empty { font-size: 12px; font-weight: 400; color: #94a3b8; }
@media (max-width: 480px) {
  .plant-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px 12px; }
  .plant-metrics > div:nth-child(odd) { border-left: 0; padding-left: 0; }
}

/* =========================================================
   现货单价区间 · 上网电量分布分析下拉信息窗
   ========================================================= */
.price-dist-window {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-top: 3px solid #2563eb;
  border-radius: 12px;
  padding: 0;
  overflow: hidden;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.dist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e2e8f0;
  cursor: pointer;
  user-select: none;
  gap: 16px;
  flex-wrap: wrap;
}

.dist-header:hover {
  background: linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
}

.dist-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 260px;
}

.dist-icon {
  font-size: 24px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #eff6ff;
  color: #2563eb;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.15);
  flex-shrink: 0;
}

.dist-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dist-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
  line-height: 1.3;
}

.dist-badge {
  font-size: 11px;
  font-weight: 600;
  color: #1d4ed8;
  background: #dbeafe;
  padding: 2px 8px;
  border-radius: 9999px;
  white-space: nowrap;
}

.dist-subtitle {
  font-size: 12px;
  color: #64748b;
  margin: 2px 0 0;
  line-height: 1.4;
}

.dist-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.dist-capsule-tabs {
  display: inline-flex;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 9999px;
  padding: 3px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.capsule-btn {
  border: none;
  background: transparent;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.18s ease;
  white-space: nowrap;
}

.capsule-btn:hover {
  color: #1e293b;
  background: #f1f5f9;
}

.capsule-btn.active {
  background: #2563eb;
  color: #ffffff;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.35);
}

.dist-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #ffffff;
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dist-toggle-btn:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  color: #0f172a;
}

.chevron {
  display: inline-block;
  font-size: 10px;
  transition: transform 0.25s ease;
  color: #64748b;
}

.chevron.is-open {
  transform: rotate(180deg);
}

/* 折叠小横条摘要 */
.dist-summary-strip {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding: 10px 18px;
  background: #fafafa;
  cursor: pointer;
  border-top: 1px dashed #e2e8f0;
  flex-wrap: wrap;
  gap: 12px;
}

.dist-summary-strip:hover {
  background: #f1f5f9;
}

.summary-prefix {
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
}

.summary-chips {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  padding: 3px 9px;
  border-radius: 6px;
  border: 1px solid transparent;
}

.chip-mwh {
  opacity: 0.85;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 展开主体区 */
.dist-body {
  padding: 18px 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #ffffff;
}

/* 1. 堆叠条 */
.stacked-bar-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stacked-bar-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #334155;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-points {
  color: #94a3b8;
  font-size: 12px;
  margin-left: 4px;
}

.meta-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
  flex-wrap: wrap;
}

.legend-dot-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.stacked-bar {
  display: flex;
  width: 100%;
  height: 24px;
  background: #f1f5f9;
  border-radius: 9999px;
  overflow: hidden;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.08);
}

.bar-segment {
  height: 100%;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  min-width: 0;
}

.segment-text {
  font-size: 11px;
  font-weight: 700;
  color: #ffffff;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 4px;
}

/* 2. 四宫格指标卡 */
.interval-cards-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

@media (max-width: 992px) {
  .interval-cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .interval-cards-grid {
    grid-template-columns: 1fr;
  }
}

.interval-card {
  border: 1px solid #e2e8f0;
  border-top-width: 3px;
  border-radius: 10px;
  padding: 14px 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.interval-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.range-badge {
  font-size: 11.5px;
  font-weight: 700;
  color: #ffffff;
  padding: 2px 7px;
  border-radius: 5px;
  letter-spacing: 0.2px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.range-tag {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-ratio {
  font-size: 26px;
  font-weight: 800;
  line-height: 1.15;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  margin: 4px 0 2px;
}

.card-metric-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
  padding-top: 6px;
  margin-top: 2px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
}

.m-label {
  color: #64748b;
}

.m-val {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: #1e293b;
}

/* 3. 机组明细折叠穿透 */
.unit-breakdown-section {
  border-top: 1px solid #f1f5f9;
  padding-top: 10px;
}

.breakdown-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 7px 12px;
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  justify-content: space-between;
}

.breakdown-toggle-btn:hover {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #4338ca;
}

.breakdown-hint {
  font-size: 11.5px;
  font-weight: normal;
  color: #94a3b8;
}

.unit-breakdown-table-wrap {
  margin-top: 10px;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #ffffff;
}

.unit-breakdown-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: left;
}

.unit-breakdown-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  padding: 8px 12px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

.unit-breakdown-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f1f5f9;
  white-space: nowrap;
}

.unit-breakdown-table tbody tr:hover {
  background: #f8fafc;
}

.unit-name-cell {
  color: #1e293b;
}

.unit-total-cell,
.unit-avg-cell {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
  color: #334155;
}

.cell-neg {
  color: #2563eb;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.cell-low {
  color: #059669;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.cell-mid {
  color: #ea580c;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.cell-high {
  color: #dc2626;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.cell-ratio {
  font-weight: 700;
  margin-left: 2px;
}

.kpi-sub {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  color: #64748b;
  margin-top: 2px;
}

.kpi-sub + .kpi-sub {
  margin-top: 5px;
}

.kpi-sub-dual {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  font-size: 11px;
}

.kpi-sub-dual .sub-item {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
  flex-shrink: 0;
}

.kpi-sub-dual .badge-alert,
.kpi-sub-dual .badge-blue {
  padding: 1px 5px;
  font-size: 10.5px;
}

.sub-dim {
  color: #94a3b8;
  font-size: 10.5px;
  font-weight: normal;
}

.text-blue { color: #2563eb !important; }
.text-orange { color: #ea580c !important; }
.text-green { color: #16a34a !important; }
.text-purple { color: #9333ea !important; }
.text-danger { color: #dc2626 !important; }
.text-gray { color: #94a3b8 !important; }
.text-province { color: #0284c7 !important; }

.badge-alert {
  color: #dc2626;
  font-weight: 600;
  background: #fef2f2;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.badge-blue {
  color: #2563eb;
  font-weight: 600;
  background: #eff6ff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

/* 电厂卡片底栏：量价波形相关系数 */
.plant-corr-footer {
  margin-top: 2px;
  padding-top: 10px;
  border-top: 1px dashed #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.plant-corr-label-group {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px;
}

.plant-corr-title {
  font-size: 11.5px;
  font-weight: 600;
  color: #475569;
}

.plant-corr-meaning {
  font-size: 10.5px;
  color: #94a3b8;
}

.plant-corr-badges {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.plant-corr-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 11.5px;
  border: 1px solid #e2e8f0;
  font-variant-numeric: tabular-nums;
}

.plant-corr-pill.is-da {
  background: #eff6ff;
  border-color: #dbeafe;
}

.plant-corr-pill.is-rt {
  background: #fff7ed;
  border-color: #ffedd5;
}

.pill-basis {
  color: #64748b;
  font-size: 11px;
}

.pill-global {
  color: #64748b;
  font-size: 10.5px;
}

/* 图表区 */
.chart-container-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 18px 20px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 10px;
}

.chart-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chart-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.chart-badge {
  background: #eff6ff;
  color: #2563eb;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11.5px;
  font-weight: 500;
}

.chart-indicators-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.selector-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
  margin-right: 2px;
}

.indicator-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #94a3b8;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.indicator-chip:hover {
  border-color: #cbd5e1;
  color: #475569;
}

.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #cbd5e1;
  transition: background-color 0.2s;
}

.chip-bar {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background-color: #cbd5e1;
  transition: background-color 0.2s;
}

/* 激活态 (Active) */
.indicator-chip.chip-blue.active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.08);
}
.indicator-chip.chip-blue.active .chip-dot {
  background-color: #2563eb;
  box-shadow: 0 0 4px rgba(37, 99, 235, 0.4);
}

.indicator-chip.chip-orange.active {
  background: #fff7ed;
  border-color: #fdba74;
  color: #c2410c;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(249, 115, 22, 0.08);
}
.indicator-chip.chip-orange.active .chip-dot {
  background-color: #f97316;
  box-shadow: 0 0 4px rgba(249, 115, 22, 0.4);
}

.indicator-chip.chip-green.active {
  background: #f0fdf4;
  border-color: #86efac;
  color: #15803d;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(16, 185, 129, 0.08);
}
.indicator-chip.chip-green.active .chip-bar {
  background-color: #10b981;
  box-shadow: 0 0 4px rgba(16, 185, 129, 0.4);
}

.indicator-chip.chip-red.active {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #b91c1c;
  font-weight: 600;
  box-shadow: 0 1px 2px rgba(239, 68, 68, 0.08);
}
.indicator-chip.chip-red.active .chip-bar {
  background-color: #ef4444;
  box-shadow: 0 0 4px rgba(239, 68, 68, 0.4);
}

/* 图表主容器：彻底消除缩在左侧问题 */
.chart-wrapper {
  position: relative;
  width: 100%;
  min-height: 380px;
}

.main-chart {
  width: 100% !important;
  min-width: 100% !important;
  height: 380px;
  display: block;
}

.chart-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(2px);
  z-index: 10;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
  color: #475569;
  font-size: 13.5px;
  font-weight: 500;
  border-radius: 8px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 表格卡片 */
.table-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 20px;
}

.table-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.table-title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.table-title-group h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.table-count {
  font-size: 12px;
  color: #64748b;
}

.mobile-layout-switch {
  display: none; /* PC 隐藏，移动端展示 */
}

.table-responsive {
  width: 100%;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  max-height: 520px;
  overflow-y: auto;
}

.spot-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  text-align: left;
}

.spot-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
  z-index: 2;
  white-space: nowrap;
}

.spot-table td {
  padding: 9px 12px;
  border-bottom: 1px solid #f1f5f9;
  white-space: nowrap;
}

.spot-table tr:hover td {
  background-color: #f8fafc;
}

.row-negative td {
  background-color: #f0fdf4 !important;
}

.col-center { text-align: center; }
.col-right { text-align: right; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.font-bold { font-weight: 600; }
.text-muted { color: #64748b; }

.badge-neg-inline {
  background: #dbeafe;
  color: #1e40af;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.badge-status {
  padding: 2px 7px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.badge-status.raw { background: #f1f5f9; color: #475569; }
.badge-status.submitted { background: #dcfce7; color: #15803d; }

.table-submode-switch {
  display: inline-flex;
  align-items: center;
  background: #f1f5f9;
  padding: 3px;
  border-radius: 8px;
  gap: 2px;
}

.table-toggle-btn {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.table-toggle-btn:hover {
  color: #0f172a;
}

.table-toggle-btn.active {
  background: #ffffff;
  color: #2563eb;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

/* 轻量级现代分页控制条 */
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  font-size: 12.5px;
  color: #64748b;
}

.pagination-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-sep {
  color: #cbd5e1;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.btn-page {
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #475569;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-page:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #1e293b;
}

.btn-page:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  background: #f8fafc;
}

.page-num-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: 0 4px;
}

.page-jump-input {
  width: 52px;
  height: 28px;
  padding: 0 6px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
  outline: none;
}

.page-jump-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.page-total-label {
  font-weight: 600;
  color: #64748b;
  font-size: 12px;
}

.page-size-selector {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 8px;
  padding-left: 8px;
  border-left: 1px solid #e2e8f0;
}

.page-label {
  font-size: 12px;
  color: #64748b;
}

.page-select {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 3px 6px;
  font-size: 12px;
  color: #334155;
  background: #ffffff;
  outline: none;
  cursor: pointer;
}

.page-select:focus {
  border-color: #3b82f6;
}

/* 手机端微卡片容器 (默认桌面端隐藏) */
.mobile-cards-wrap {
  display: none;
}

/* ==========================================================================
   手机移动端专属响应式设计 (<= 768px)
   ========================================================================== */
@media (max-width: 768px) {
  .spot-elec-main {
    padding: 10px 10px 30px;
    gap: 10px;
    max-width: 100%;
    box-sizing: border-box;
    overflow-x: hidden;
  }

  /* 1. 顶部天蓝看板卡片移动端优化 */
  .banner-card {
    padding: 14px 14px;
  }
  .banner-content {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .banner-title-row {
    align-items: flex-start;
    gap: 12px;
  }
  .banner-icon {
    font-size: 22px;
    width: 38px;
    height: 38px;
    flex-shrink: 0;
  }
  .banner-title {
    font-size: 16px;
    line-height: 1.35;
  }
  .banner-subtitle {
    font-size: 11.5px;
    line-height: 1.4;
  }
  .banner-meta {
    flex-direction: column;
    gap: 6px;
    width: 100%;
  }
  .meta-tag {
    width: 100%;
    box-sizing: border-box;
    font-size: 11.5px;
    padding: 5px 10px;
  }

  /* 2. 筛选控制工具栏移动端排版优化 */
  .control-toolbar {
    padding: 12px;
    gap: 10px;
  }
  .toolbar-row-top,
  .toolbar-row-bottom {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .toolbar-row-bottom {
    padding-top: 10px;
  }
  .toolbar-sub-left,
  .toolbar-right {
    width: 100%;
    justify-content: space-between;
    margin-left: 0;
  }

  .view-mode-tabs {
    width: 100%;
    display: flex;
  }
  .mode-tab-btn {
    flex: 1;
    text-align: center;
    padding: 7px 4px;
    font-size: 12px;
  }

  /* 单日日期选择组 */
  .date-picker-group {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .date-picker-group .btn.icon-btn {
    padding: 6px 10px;
    flex-shrink: 0;
  }
  .date-picker-group .form-input.date-input {
    flex: 1;
    min-width: 0;
    text-align: center;
    font-size: 13px;
    padding: 6px 4px;
  }
  .date-picker-group .btn.quick-btn {
    padding: 6px 10px;
    font-size: 11.5px;
    flex-shrink: 0;
    white-space: nowrap;
  }

  /* 区间模式控制组 */
  .range-picker-group {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .range-inputs {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
  }
  .range-inputs .form-input.date-input {
    flex: 1;
    min-width: 0;
    text-align: center;
    font-size: 12.5px;
    padding: 6px 4px;
  }
  .range-sep {
    font-size: 12px;
    color: #64748b;
    flex-shrink: 0;
  }
  .quick-range-chips {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .quick-range-chips .chip-btn {
    flex: 1;
    text-align: center;
    padding: 5px 2px;
    font-size: 11px;
    white-space: nowrap;
  }
  .quick-range-chips .query-btn {
    padding: 5px 12px;
    font-size: 11.5px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* 区间聚合维度 tabs */
  .range-submode-tabs {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    padding: 2px;
  }
  .submode-btn {
    flex: 1 1 auto;
    justify-content: center;
    padding: 6px 6px;
    font-size: 10.5px;
    white-space: nowrap;
  }
  .single-mode-hint {
    font-size: 11px;
    gap: 6px;
  }
  .hint-text {
    font-size: 11px;
  }

  /* 底部操作区：负电价勾选与导出按钮 */
  .toolbar-right {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    gap: 10px;
  }
  .checkbox-filter {
    font-size: 12px;
    white-space: nowrap;
  }
  .btn.primary.export-btn {
    flex: initial;
    padding: 6px 12px;
    font-size: 11.5px;
    white-space: nowrap;
  }

  /* 3. KPI 核心指标卡片：2 列自适应网格与长文本优化 */
  .kpi-section {
    gap: 10px;
  }
  .kpi-grid-prices {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  .kpi-grid-sales {
    grid-template-columns: minmax(0, 1fr);
    gap: 8px;
  }
  .kpi-card {
    padding: 10px 10px;
  }
  .kpi-title {
    font-size: 11px;
    line-height: 1.35;
  }
  .kpi-value {
    font-size: 17px;
    margin: 4px 0;
  }
  .kpi-sub {
    font-size: 10px;
    flex-direction: column;
    gap: 3px;
  }
  .kpi-sub-dual {
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
  }
  .badge-alert,
  .badge-blue {
    padding: 2px 5px;
    font-size: 9.5px;
    line-height: 1.2;
    display: inline-block;
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* 4. 图表区移动端上下分层与横滑优化 */
  .chart-container-card {
    padding: 12px;
  }
  .chart-header {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .chart-title-wrap {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  .chart-title {
    font-size: 14px;
    line-height: 1.4;
  }
  .chart-badge {
    align-self: flex-start;
    font-size: 10.5px;
  }
  .chart-indicators-selector {
    width: 100%;
    justify-content: flex-start;
    overflow-x: auto;
    padding: 4px 2px;
    gap: 6px;
    -webkit-overflow-scrolling: touch;
  }
  .indicator-chip {
    padding: 4px 8px;
    font-size: 11px;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .chart-wrapper {
    min-height: 300px;
  }
  .main-chart {
    height: 300px;
    width: 100% !important;
  }

  /* 5. 表格区移动端切换与微卡片排版重构 */
  .table-card-header {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .table-title-group {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 6px;
  }
  .table-title-group h3 {
    font-size: 14.5px;
  }
  .table-count {
    font-size: 11px;
  }
  .mobile-layout-switch {
    display: flex;
    width: 100%;
    background: #f1f5f9;
    padding: 3px;
    border-radius: 6px;
  }
  .switch-btn {
    flex: 1;
    text-align: center;
    border: none;
    background: transparent;
    font-size: 12px;
    padding: 5px 8px;
    border-radius: 4px;
    color: #64748b;
    cursor: pointer;
  }
  .switch-btn.active {
    background: #ffffff;
    color: #0f172a;
    font-weight: 600;
  }

  /* 微卡片流排版 */
  .mobile-cards-wrap {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .spot-mobile-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
  }
  .spot-mobile-card.is-negative {
    border-left: 3px solid #3b82f6;
    background: #f8fafc;
  }

  .card-top-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .time-block {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .point-badge {
    background: #e2e8f0;
    color: #334155;
    font-size: 11px;
    font-weight: 600;
    padding: 1px 5px;
    border-radius: 4px;
  }
  .time-text {
    font-size: 14px;
    font-weight: 700;
    font-family: ui-monospace, monospace;
    color: #0f172a;
  }
  .period-text {
    font-size: 10.5px;
    color: #64748b;
  }
  .badge-neg {
    background: #dbeafe;
    color: #1d4ed8;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 10.5px;
    font-weight: 600;
  }

  /* 核心价格网格：第 3 列 1.35fr 空间自适应容纳“价差（实时-日前）” */
  .card-price-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1.35fr;
    background: #f8fafc;
    border-radius: 6px;
    padding: 6px 8px;
    gap: 4px;
    align-items: center;
  }
  .price-cell {
    display: flex;
    flex-direction: column;
    gap: 2px;
    text-align: center;
    overflow: hidden;
  }
  .cell-label {
    font-size: 10px;
    color: #64748b;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cell-val {
    font-size: 13.5px;
    font-weight: 700;
    font-family: ui-monospace, monospace;
    white-space: nowrap;
  }
  .cell-val.val-neg {
    color: #2563eb !important;
  }

  .card-bottom-info {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 12px;
    font-size: 10.5px;
    color: #64748b;
    border-top: 1px dashed #f1f5f9;
    padding-top: 6px;
  }

  .table-responsive {
    max-height: 480px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  .spot-table th,
  .spot-table td {
    padding: 8px 8px;
    font-size: 11px;
    white-space: nowrap;
  }
}

/* ==========================================================
   Global_admin 系统控制选项与定时调度弹窗样式
   ========================================================== */
.admin-control-btn {
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  color: #f8fafc;
  border: 1px solid #475569;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  transition: all 0.2s ease;
}
.admin-control-btn:hover {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #38bdf8;
  border-color: #38bdf8;
  transform: translateY(-1px);
}

.admin-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
  animation: modalFadeIn 0.2s ease-out;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.admin-modal-card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  width: 100%;
  max-width: 640px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.admin-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.admin-modal-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.modal-badge-admin {
  background: #fee2e2;
  color: #991b1b;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 9999px;
  border: 1px solid #fecaca;
}

.admin-modal-title-wrap h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.modal-close-btn {
  background: transparent;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.15s ease;
}
.modal-close-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.admin-modal-body {
  padding: 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 状态概览卡片 */
.status-summary-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-indicator-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.indicator-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.pulse-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}
.dot-online {
  background-color: #22c55e;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.2);
}
.dot-retrying {
  background-color: #f97316;
  box-shadow: 0 0 0 2px rgba(249, 115, 22, 0.2);
  animation: pulseDot 1.5s infinite;
}
.dot-paused {
  background-color: #94a3b8;
}

@keyframes pulseDot {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.btn-refresh-status {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  color: #334155;
  transition: all 0.15s;
}
.btn-refresh-status:hover {
  border-color: #0284c7;
  color: #0284c7;
}

.status-meta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  background: #ffffff;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid #edf2f7;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.meta-label {
  font-size: 11px;
  color: #64748b;
}
.meta-val {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  font-family: ui-monospace, monospace;
}
.meta-val.highlight {
  color: #0284c7;
}

.status-msg-banner {
  font-size: 12px;
  color: #475569;
  background: #eff6ff;
  border-left: 3px solid #3b82f6;
  padding: 6px 10px;
  border-radius: 4px;
}

/* 控制区块 */
.control-section {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #ffffff;
}

.section-title-row {
  margin-bottom: 14px;
}
.section-title-row h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}
.section-desc {
  font-size: 12px;
  color: #64748b;
}

.control-form-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px dashed #f1f5f9;
}
.form-row:last-child {
  border-bottom: none;
}

.form-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.form-label .label-txt {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}
.form-label small {
  font-size: 11px;
  color: #64748b;
}

.form-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 开关组件 */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e1;
  transition: .3s;
  border-radius: 24px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .3s;
  border-radius: 50%;
}
input:checked + .slider {
  background-color: #0284c7;
}
input:checked + .slider:before {
  transform: translateX(20px);
}
.toggle-text {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.input-time,
.input-number,
.input-date {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
  color: #1e293b;
  outline: none;
  transition: border-color 0.15s;
}
.input-time:focus,
.input-number:focus,
.input-date:focus {
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.input-unit-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}
.input-number {
  width: 80px;
}
.input-unit {
  font-size: 12px;
  color: #64748b;
}

.section-action-row {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
.save-config-btn {
  font-size: 13px;
  padding: 7px 16px;
}

/* 手动拉取区块 */
.manual-sync-box {
  background: #f8fafc;
  border-radius: 6px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sync-mode-radios {
  display: flex;
  gap: 18px;
}
.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
}

.specific-date-picker-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}
.picker-label {
  font-size: 12px;
  color: #475569;
}

.manual-btn-row {
  display: flex;
  justify-content: flex-start;
}
.manual-trigger-btn {
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
  color: #ffffff;
  border: none;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.manual-trigger-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
  transform: translateY(-1px);
}
.manual-trigger-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

/* 覆盖确认警示框 */
.overwrite-confirm-box {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: modalFadeIn 0.2s ease-out;
}
.confirm-alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.confirm-icon {
  font-size: 16px;
}
.confirm-title {
  font-size: 14px;
  color: #92400e;
  font-weight: 700;
}
.confirm-desc {
  font-size: 13px;
  color: #78350f;
  line-height: 1.5;
}
.confirm-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}
.btn-confirm-overwrite {
  background: #dc2626;
  color: #ffffff;
  border: none;
  font-weight: 600;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-confirm-overwrite:hover:not(:disabled) {
  background: #b91c1c;
}
.btn-cancel-overwrite {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  padding: 7px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-cancel-overwrite:hover {
  background: #f1f5f9;
  color: #1e293b;
}

/* 反馈横幅 */
.feedback-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
  animation: modalFadeIn 0.2s ease-out;
}
.alert-success {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
}
.alert-warning {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}
.alert-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.admin-modal-footer {
  padding: 12px 20px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.footer-tip {
  font-size: 11px;
  color: #64748b;
  line-height: 1.4;
}
</style>

