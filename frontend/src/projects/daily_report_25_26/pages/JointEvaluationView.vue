<template>
  <div class="joint-eval-view">
    <AppHeader />
    <main class="joint-eval-main">
      <div class="top-nav-bar">
        <Breadcrumbs :items="breadcrumbItems" />
        <div class="header-actions">
          <button
            class="btn ghost-btn"
            type="button"
            :disabled="loading"
            @click="fetchEvaluation"
          >
            <span>🔄</span>
            <span>{{ loading ? '测算中…' : '刷新测算' }}</span>
          </button>
          <button
            class="btn export-btn"
            type="button"
            :disabled="loading || !dailyRows.length"
            @click="exportExcel"
          >
            <span>📥</span>
            <span>导出 Excel</span>
          </button>
        </div>
      </div>

      <!-- 顶部横幅与口径说明 -->
      <section class="hero-banner">
        <div class="hero-left">
          <div class="hero-badges">
            <span class="badge-season">{{ seasonPeriodLabel }} 供暖期</span>
            <span class="badge-window">有效评价窗口：{{ seasonWindowLabel }}</span>
          </div>
          <h1 class="hero-title">主城区供热联合评价模型</h1>
          <p class="hero-subtitle">
            以采暖度日数HDD20为基础，构建“投入偏差 × 服务效果”双维联合诊断体系
          </p>
        </div>

        <div class="hero-meta-grid">
          <div class="meta-tile">
            <span class="meta-label">基准业务日期</span>
            <strong class="meta-value font-mono">{{ payload?.default_biz_date || '—' }}</strong>
          </div>
          <div class="meta-tile">
            <span class="meta-label">主城区收费面积（GongRe）</span>
            <strong class="meta-value font-mono" :class="{ 'text-warn': areaMissing }">
              {{ areaText }}
            </strong>
          </div>
          <div class="meta-tile">
            <span class="meta-label">有效测算天数</span>
            <strong class="meta-value font-mono">{{ payload?.valid_day_count ?? 0 }} 天</strong>
          </div>
        </div>
      </section>

      <!-- 异常/缺失提醒条 -->
      <div v-if="areaMissing && !loading" class="alert-banner alert-error">
        <span>⚠️ 未读取到当前供暖季（{{ payload?.season_period }}）常量表中 <code>GongRe</code> 的供暖收费面积（<code>amount_heating_fee_area</code>），请先前往“常量指标页面”完成维护后再进行联合测算。</span>
      </div>
      <div v-if="excludedCount > 0" class="alert-banner alert-warn">
        <span>
          🧹 已自动剔除 <b>{{ excludedCount }}</b> 个测算外日期（11.1–11.4 启动期 / 4.1–4.5 供暖末期）：
          <span class="excluded-preview">{{ excludedDatesPreview }}</span>
        </span>
      </div>
      <div v-if="incompleteDaysCount > 0" class="alert-banner alert-info">
        <span>
          ℹ️ 当前区间内有 <b>{{ incompleteDaysCount }}</b> 天缺少完整日报、投诉或前 3 日气温数据（明细表中已标注），汇总比值仅基于完整有效维度累加计算。
        </span>
      </div>

      <!-- 控制台 -->
      <section class="card control-deck">
        <div class="control-row">
          <div class="mode-tabs" role="tablist" aria-label="评价时间模式">
            <button
              v-for="m in modeOptions"
              :key="m.value"
              type="button"
              role="tab"
              :aria-selected="queryState.mode === m.value"
              :class="['mode-tab', { active: queryState.mode === m.value }]"
              @click="switchMode(m.value)"
            >
              <span>{{ m.icon }}</span>
              <span>{{ m.label }}</span>
            </button>
          </div>

          <div class="quick-presets">
            <span class="preset-title">快捷视图：</span>
            <button
              v-for="preset in quickPresets"
              :key="preset.key"
              type="button"
              class="preset-chip"
              @click="applyQuickPreset(preset.key)"
            >
              {{ preset.label }}
            </button>
          </div>
        </div>

        <!-- 各模式专属参数区 -->
        <div class="params-row">
          <!-- 单日模式 -->
          <template v-if="queryState.mode === 'single'">
            <label class="param-field">
              <span class="param-label">评价单日</span>
              <input
                v-model="queryState.bizDate"
                type="date"
                class="param-input"
                @change="fetchEvaluation"
              />
            </label>
            <div class="param-field">
              <span class="param-label">附带轨迹周期数（自当日向前）</span>
              <div class="pill-group">
                <button
                  v-for="n in [1, 7, 14]"
                  :key="`single-trace-${n}`"
                  type="button"
                  :class="['count-pill', { active: queryState.singleTraceDays === n }]"
                  @click="setSingleTraceDays(n)"
                >
                  {{ n === 1 ? '仅当日' : `近 ${n} 日` }}
                </button>
              </div>
            </div>
          </template>

          <!-- 多周期滚动模式 -->
          <template v-else-if="queryState.mode === 'rolling'">
            <label class="param-field">
              <span class="param-label">截止基准日</span>
              <input
                v-model="queryState.endDate"
                type="date"
                class="param-input"
                @change="fetchEvaluation"
              />
            </label>
            <div class="param-field">
              <span class="param-label">单周期跨度</span>
              <div class="pill-group">
                <button
                  v-for="opt in periodSpanOptions"
                  :key="`span-${opt.days}`"
                  type="button"
                  :class="['count-pill', { active: queryState.periodDays === opt.days }]"
                  @click="setRollingSpan(opt.days)"
                >
                  {{ opt.label }}
                </button>
              </div>
            </div>
            <div class="param-field">
              <span class="param-label">显示周期数量</span>
              <div class="pill-group">
                <button
                  v-for="cnt in [3, 5, 7, 10, 12]"
                  :key="`cnt-${cnt}`"
                  type="button"
                  :class="['count-pill', { active: queryState.periodCount === cnt }]"
                  @click="setRollingCount(cnt)"
                >
                  {{ cnt }} 期
                </button>
                <input
                  v-model.number="queryState.periodCount"
                  type="number"
                  min="1"
                  max="60"
                  class="param-number-input"
                  title="自定义显示周期数量（1~60）"
                  @change="clampAndFetchRollingCount"
                />
              </div>
            </div>
          </template>

          <!-- 自定义时段模式 -->
          <template v-else>
            <label class="param-field">
              <span class="param-label">起始日期</span>
              <input
                v-model="queryState.startDate"
                type="date"
                class="param-input"
                @change="fetchEvaluation"
              />
            </label>
            <label class="param-field">
              <span class="param-label">结束日期</span>
              <input
                v-model="queryState.endDate"
                type="date"
                class="param-input"
                @change="fetchEvaluation"
              />
            </label>
          </template>
        </div>
      </section>

      <!-- 加载或错误态 -->
      <section v-if="errorMessage" class="card state-card error-state">
        <p>{{ errorMessage }}</p>
      </section>
      <section v-else-if="loading && !payload" class="card state-card">
        <p>正在计算主城区联合评价模型，请稍候…</p>
      </section>
      <section v-else-if="payload && !hasValidEvaluation" class="card state-card empty-eval-state">
        <div class="empty-icon">📅</div>
        <h3>所选日期不在模型有效测算范围内</h3>
        <p>
          当前模型有效评价区间为 <b>每年 11月5日 — 次年3月31日</b>（已自动剔除 11.1–11.4 启动初期与 4.1–4.5 供暖末期）。
          请切换至有效区间内的日期查看联合评价结果。
        </p>
      </section>

      <!-- 主体结果区 -->
      <template v-else-if="payload && summary">
        <!-- 4 张诊断 KPI 卡 -->
        <section class="kpi-grid">
          <!-- 卡 1：供热偏差率 -->
          <article class="kpi-card" :class="deviationToneClass">
            <div class="kpi-head">
              <span class="kpi-title">气象修正供热偏差率</span>
              <span class="kpi-tag">{{ summaryLabel }}</span>
            </div>
            <div class="kpi-main">
              <span class="kpi-value font-mono">{{ formatSignedPercent(summary.heat_deviation_pct) }}</span>
              <span class="kpi-sub-badge">{{ bandBadgeText }}</span>
            </div>
            <div class="kpi-details">
              <div class="kpi-detail-item">
                <span>实际总耗热</span>
                <strong class="font-mono">{{ formatNum(summary.actual_heat_gj, 0) }} GJ</strong>
              </div>
              <div class="kpi-detail-item">
                <span>参考总耗热</span>
                <strong class="font-mono">{{ formatNum(summary.ref_heat_gj, 0) }} GJ</strong>
              </div>
              <div class="kpi-detail-item">
                <span>耗热差额</span>
                <strong class="font-mono">{{ formatSignedNum(summary.heat_delta_gj, 0) }} GJ</strong>
              </div>
            </div>
            <p class="kpi-footnote">{{ summary.band_status?.label || '—' }}</p>
          </article>

          <!-- 卡 2：投诉强度指数 -->
          <article class="kpi-card" :class="complaintToneClass">
            <div class="kpi-head">
              <span class="kpi-title">用户投诉强度指数</span>
              <span class="kpi-tag">基准线 = 100</span>
            </div>
            <div class="kpi-main">
              <span class="kpi-value font-mono">{{ formatNum(summary.complaint_index, 1) }}</span>
              <span class="kpi-sub-badge">
                {{ complaintIndexDeltaText }}
              </span>
            </div>
            <div class="kpi-details">
              <div class="kpi-detail-item">
                <span>实际省市投诉</span>
                <strong class="font-mono">{{ formatNum(summary.actual_complaints, 0) }} 件</strong>
              </div>
              <div class="kpi-detail-item">
                <span>同月参考投诉</span>
                <strong class="font-mono">{{ formatNum(summary.ref_complaints, 1) }} 件</strong>
              </div>
              <div class="kpi-detail-item">
                <span>投诉差额</span>
                <strong class="font-mono">{{ formatSignedNum(summary.complaint_delta, 1) }} 件</strong>
              </div>
            </div>
            <p class="kpi-footnote">基于近两季同口径分月单位面积投诉率折算</p>
          </article>

          <!-- 卡 3：四象限联合定性 -->
          <article class="kpi-card kpi-quadrant" :style="quadrantCardStyle">
            <div class="kpi-head">
              <span class="kpi-title">四象限联合诊断</span>
              <span class="kpi-tag">投入 × 服务</span>
            </div>
            <div class="quadrant-hero">
              <span class="quadrant-pill" :style="{ backgroundColor: activeQuadrantColor }">
                {{ summary.quadrant?.name || '暂无定性' }}
              </span>
              <span class="quadrant-diagnosis">{{ summary.quadrant?.diagnosis || '数据不完整' }}</span>
            </div>
            <p class="quadrant-action">
              {{ summary.quadrant?.action || '请核对当日站内耗热量、投诉量及前 3 日气温是否完整。' }}
            </p>
          </article>

          <!-- 卡 4：气象与单耗表现 -->
          <article class="kpi-card tone-slate">
            <div class="kpi-head">
              <span class="kpi-title">气象需求与日均单耗</span>
              <span class="kpi-tag">有效 {{ summary.valid_days }} 天</span>
            </div>
            <div class="kpi-main">
              <span class="kpi-value font-mono">{{ formatNum(summary.actual_unit_heat_avg, 2) }}</span>
              <span class="kpi-unit">GJ/万㎡·日</span>
            </div>
            <div class="kpi-details">
              <div class="kpi-detail-item">
                <span>模型参考单耗</span>
                <strong class="font-mono">{{ formatNum(summary.ref_unit_heat_avg, 2) }} GJ/万㎡</strong>
              </div>
              <div class="kpi-detail-item">
                <span>区间平均气温</span>
                <strong class="font-mono">{{ formatNum(summary.avg_temp, 2) }} ℃</strong>
              </div>
              <div class="kpi-detail-item">
                <span>当日 / 前3日 HDD20</span>
                <strong class="font-mono">
                  {{ formatNum(summary.avg_hdd20_today, 2) }} / {{ formatNum(summary.avg_hdd20_prev3, 2) }}
                </strong>
              </div>
            </div>
            <p class="kpi-footnote">
              {{ queryState.mode === 'single' && trajectorySummary ? `近 ${trajectorySummary.valid_days} 日轨迹累计偏差 ${formatSignedPercent(trajectorySummary.heat_deviation_pct)}，指数 ${formatNum(trajectorySummary.complaint_index, 1)}` : '先累计区间总量，再求偏差率与投诉指数' }}
            </p>
          </article>
        </section>

        <!-- 图表区：左侧四象限主图 + 右侧双区趋势对照图 -->
        <section class="charts-layout">
          <!-- 四象限演进轨迹图 -->
          <article class="card chart-card quadrant-chart-card">
            <header class="chart-header">
              <div>
                <h2 class="chart-title">四象限联合评价演进轨迹</h2>
                <p class="chart-desc">
                  横轴：气象修正供热偏差率（0% 为中性线）；纵轴：用户投诉强度指数（100 为中性线）。按时间序号串联演进路径。
                </p>
              </div>
              <div class="chart-toggles">
                <button
                  v-if="highlightedRowKey"
                  type="button"
                  class="lock-focus-chip"
                  title="点击解除锁定"
                  @click="toggleFocusedRow(highlightedRowKey)"
                >
                  <span>📌 已锁定：{{ focusedPointLabel }}</span>
                  <span class="lock-close">✕</span>
                </button>
                <label class="toggle-chip">
                  <input v-model="chartOptions.showEmpiricalBand" type="checkbox" @change="renderQuadrantChart" />
                  <span>5%–95% 经验带</span>
                </label>
                <label class="toggle-chip">
                  <input v-model="chartOptions.colorByTime" type="checkbox" @change="renderQuadrantChart" />
                  <span>时间渐变轨迹</span>
                </label>
                <label v-if="hasAggregatePoint" class="toggle-chip">
                  <input v-model="chartOptions.showAggregateStar" type="checkbox" @change="renderQuadrantChart" />
                  <span>★ 区间汇总点</span>
                </label>
              </div>
            </header>

            <div v-if="chartOptions.colorByTime && trajectoryTimeMeta" class="time-order-strip">
              <span class="time-order-badge start">起点 {{ trajectoryTimeMeta.firstLabel }}</span>
              <span class="time-order-bar" aria-hidden="true"></span>
              <span class="time-order-badge end">最新 {{ trajectoryTimeMeta.lastLabel }}</span>
              <span class="time-order-hint">点位由小到大、颜色由晴空蓝渐变至珊瑚红，箭头指示推进方向</span>
            </div>

            <div ref="quadrantChartEl" class="chart-canvas quadrant-canvas"></div>
          </article>

          <!-- 逐日/逐期单耗与投诉联动图 -->
          <article class="card chart-card trend-chart-card">
            <header class="chart-header">
              <div>
                <h2 class="chart-title">单耗对照与投诉强度联动走势</h2>
                <p class="chart-desc">
                  上图：实际单耗 vs HDD20 参考单耗（含日均气温）；下图：实际投诉量（按象限着色）vs 同月参考基准。
                </p>
              </div>
              <div class="chart-toggles">
                <span class="trend-scope-badge">
                  {{ queryState.mode === 'rolling' && queryState.periodDays > 1 ? `按 ${periods.length} 个周期展示` : `共 ${dailyRows.length} 个有效日` }}
                </span>
              </div>
            </header>
            <div ref="trendChartEl" class="chart-canvas trend-canvas"></div>
          </article>
        </section>

        <!-- 结构化明细表 -->
        <section class="card table-card">
          <header class="table-header">
            <div class="table-title-group">
              <h2 class="chart-title">联合评价测算明细</h2>
              <div v-if="queryState.mode === 'rolling' && queryState.periodDays > 1" class="table-view-switch">
                <button
                  type="button"
                  :class="['sub-tab', { active: tableViewMode === 'periods' }]"
                  @click="tableViewMode = 'periods'"
                >
                  按周期汇总 ({{ periods.length }})
                </button>
                <button
                  type="button"
                  :class="['sub-tab', { active: tableViewMode === 'daily' }]"
                  @click="tableViewMode = 'daily'"
                >
                  逐日明细 ({{ dailyRows.length }})
                </button>
              </div>
            </div>

            <div class="quadrant-filters">
              <button
                type="button"
                :class="['q-filter-btn', { active: selectedQuadrantFilter === 'ALL' }]"
                @click="selectedQuadrantFilter = 'ALL'"
              >
                全部 ({{ activeTableSourceRows.length }})
              </button>
              <button
                v-for="q in quadrantLegendList"
                :key="`filter-${q.code}`"
                type="button"
                :class="['q-filter-btn', { active: selectedQuadrantFilter === q.code }]"
                @click="selectedQuadrantFilter = q.code"
              >
                <i class="q-dot" :style="{ backgroundColor: q.color }"></i>
                {{ q.short_name }} ({{ countRowsByQuadrant(q.code) }})
              </button>
            </div>
          </header>

          <p class="mobile-scroll-hint">← 左右滑动查看全列指标，轻触行可锁定图内联动 →</p>
          <div class="table-scroll">
            <table class="eval-table">
              <thead>
                <tr>
                  <th>{{ tableViewMode === 'periods' && queryState.mode === 'rolling' && queryState.periodDays > 1 ? '评价周期' : '日期' }}</th>
                  <th class="num">日均气温(℃)</th>
                  <th class="num">当日HDD20</th>
                  <th class="num">前3日均值</th>
                  <th class="num">实际单耗<br /><small>GJ/万㎡·日</small></th>
                  <th class="num">参考单耗<br /><small>GJ/万㎡·日</small></th>
                  <th class="num">实际耗热(GJ)</th>
                  <th class="num">参考耗热(GJ)</th>
                  <th class="num">供热偏差率(%)</th>
                  <th class="num">实际投诉(件)</th>
                  <th class="num">参考投诉(件)</th>
                  <th class="num">投诉强度指数</th>
                  <th>象限归属</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in filteredTableRows"
                  :key="row._rowKey"
                  :class="{
                    'row-highlighted': highlightedRowKey === row._rowKey,
                    'row-hovered': hoveredRowKey === row._rowKey && highlightedRowKey !== row._rowKey,
                    'row-incomplete': row._isIncomplete,
                  }"
                  @click="toggleFocusedRow(row._rowKey)"
                  @mouseenter="previewRowInCharts(row._rowKey)"
                  @mouseleave="clearChartSyncPreview"
                >
                  <td class="font-mono cell-date">
                    <span>{{ row._label }}</span>
                    <span v-if="row._daysLabel" class="days-mini-tag">{{ row._daysLabel }}</span>
                    <span v-if="row._missingHint" class="missing-tip" :title="row._missingHint">缺数</span>
                  </td>
                  <td class="num font-mono">{{ formatNum(row._avgTemp, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(row._hddToday, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(row._hddPrev3, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(row._actualUnitHeat, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(row._refUnitHeat, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(row._actualHeat, 0) }}</td>
                  <td class="num font-mono">{{ formatNum(row._refHeat, 0) }}</td>
                  <td class="num font-mono" :class="deviationTextClass(row._deviation)">
                    {{ formatSignedPercent(row._deviation) }}
                  </td>
                  <td class="num font-mono">{{ formatNum(row._actualComplaints, 0) }}</td>
                  <td class="num font-mono">{{ formatNum(row._refComplaints, 1) }}</td>
                  <td class="num font-mono" :class="complaintTextClass(row._complaintIndex)">
                    {{ formatNum(row._complaintIndex, 1) }}
                  </td>
                  <td>
                    <span
                      v-if="row._quadrant"
                      class="table-q-badge"
                      :style="{ backgroundColor: `${row._quadrant.color}1A`, color: row._quadrant.color, borderColor: `${row._quadrant.color}55` }"
                    >
                      {{ row._quadrant.short_name }}
                    </span>
                    <span v-else class="text-muted">—</span>
                  </td>
                </tr>
              </tbody>
              <tfoot v-if="summaryForTableFoot">
                <tr class="summary-foot-row">
                  <td><strong>合计</strong></td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.avg_temp, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.avg_hdd20_today, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.avg_hdd20_prev3, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.actual_unit_heat_avg, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.ref_unit_heat_avg, 2) }}</td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.actual_heat_gj, 0) }}</td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.ref_heat_gj, 0) }}</td>
                  <td class="num font-mono" :class="deviationTextClass(summaryForTableFoot.heat_deviation_pct)">
                    {{ formatSignedPercent(summaryForTableFoot.heat_deviation_pct) }}
                  </td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.actual_complaints, 0) }}</td>
                  <td class="num font-mono">{{ formatNum(summaryForTableFoot.ref_complaints, 1) }}</td>
                  <td class="num font-mono" :class="complaintTextClass(summaryForTableFoot.complaint_index)">
                    {{ formatNum(summaryForTableFoot.complaint_index, 1) }}
                  </td>
                  <td>
                    <span
                      v-if="summaryForTableFoot.quadrant"
                      class="table-q-badge"
                      :style="{ backgroundColor: `${summaryForTableFoot.quadrant.color}1A`, color: summaryForTableFoot.quadrant.color, borderColor: `${summaryForTableFoot.quadrant.color}55` }"
                    >
                      {{ summaryForTableFoot.quadrant.short_name }}
                    </span>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </section>

        <!-- 可折叠模型基准参数透明卡 -->
        <section class="card spec-card">
          <button
            type="button"
            class="spec-toggle-btn"
            :aria-expanded="showModelSpec"
            @click="showModelSpec = !showModelSpec"
          >
            <span>📐 模型公式与参数</span>
            <span class="spec-chevron">{{ showModelSpec ? '▲' : '▼' }}</span>
          </button>

          <div v-if="showModelSpec && payload?.model_spec" class="spec-body">
            <div class="spec-formula-box">
              <div class="formula-title">气象修正参考单耗公式</div>
              <code class="formula-code">{{ payload.model_spec.equation }}</code>
              <p class="formula-meta">
                适用窗口：{{ payload.model_spec.valid_window_rule }} ｜ 区间汇总方式：先累计区间总实际值与总参考值，再计算偏差率与投诉强度指数。
              </p>
            </div>

            <div class="spec-tables-grid">
              <div class="spec-mini-box">
                <h4>分月参考修正与投诉率基准</h4>
                <div class="mini-table-scroll">
                  <table class="mini-spec-table">
                    <thead>
                      <tr>
                        <th>月份</th>
                        <th class="num">耗热月份修正 (GJ/万㎡·日)</th>
                        <th class="num">参考投诉率 (件/万㎡·日)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(adj, idx) in payload.model_spec.month_heat_adjustments" :key="adj.month">
                        <td>{{ adj.label }}</td>
                        <td class="num font-mono">{{ adj.adjustment > 0 ? `+${adj.adjustment.toFixed(4)}` : adj.adjustment.toFixed(4) }}</td>
                        <td class="num font-mono">{{ payload.model_spec.month_complaint_rates[idx]?.rate_per_10k_m2_day?.toFixed(6) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="spec-mini-box">
                <h4>历史经验波动参考带（5%—95% 分位）</h4>
                <div class="mini-table-scroll">
                  <table class="mini-spec-table">
                    <thead>
                      <tr>
                        <th>评价周期</th>
                        <th class="num">5%下界(%)</th>
                        <th class="num">中位数(%)</th>
                        <th class="num">95%上界(%)</th>
                        <th class="num">偏差率RMSE(%)</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="band in payload.model_spec.empirical_bands" :key="band.period_days">
                        <td>{{ band.label }}</td>
                        <td class="num font-mono">{{ band.p5.toFixed(2) }}</td>
                        <td class="num font-mono">{{ band.median > 0 ? `+${band.median.toFixed(2)}` : band.median.toFixed(2) }}</td>
                        <td class="num font-mono">+{{ band.p95.toFixed(2) }}</td>
                        <td class="num font-mono">{{ band.rmse.toFixed(2) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as echarts from 'echarts'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'
import { getJointEvaluation } from '../services/api'
import { exportJointEvaluationExcelFile } from '../utils/jointEvaluationExcelExport'

const PROJECT_KEY = 'daily_report_25_26'

const loading = ref(false)
const errorMessage = ref('')
const payload = ref(null)
const showModelSpec = ref(false)
const tableViewMode = ref('daily')
const selectedQuadrantFilter = ref('ALL')
const highlightedRowKey = ref('')
const hoveredRowKey = ref('')

const quadrantChartEl = ref(null)
const trendChartEl = ref(null)
let quadrantChart = null
let trendChart = null
let chartResizeObserver = null
let resizeRafId = 0
let quadrantIndexByRowKey = new Map()
let trendIndexByRowKey = new Map()
let trendRowKeys = []
let activeSyncSource = null
const isMobileViewport = () => typeof window !== 'undefined' && window.innerWidth <= 640
let lastMobileChartMode = isMobileViewport()

const queryState = reactive({
  mode: 'single',
  bizDate: '',
  startDate: '',
  endDate: '',
  singleTraceDays: 7,
  periodDays: 7,
  periodCount: 4,
})

const chartOptions = reactive({
  showEmpiricalBand: true,
  colorByTime: true,
  showAggregateStar: true,
})

const modeOptions = [
  { value: 'single', label: '单日诊断', icon: '🎯' },
  { value: 'rolling', label: '周期滚动对比', icon: '🔁' },
  { value: 'range', label: '自定义时段', icon: '📆' },
]

const periodSpanOptions = [
  { days: 1, label: '1日/期' },
  { days: 7, label: '7日/周' },
  { days: 14, label: '14日/双周' },
  { days: 30, label: '30日/月' },
]

const quickPresets = [
  { key: 'biz_day', label: '业务日当日' },
  { key: 'last_7d', label: '近 7 日轨迹' },
  { key: 'last_4w', label: '近 4 周演进' },
  { key: 'month_to_date', label: '本月至今' },
  { key: 'season_to_date', label: '本季累计 (11.5起)' },
]

const projectName = computed(() => getProjectNameById(PROJECT_KEY) ?? PROJECT_KEY)
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${PROJECT_KEY}/pages` },
  { label: '主城区供热联合评价模型', to: null },
])

const seasonPeriodLabel = computed(() => {
  const code = String(payload.value?.season_period || '26-27')
  const parts = code.split('-')
  if (parts.length === 2) {
    return `20${parts[0]}–20${parts[1]}`
  }
  return code
})

const seasonWindowLabel = computed(() => {
  const code = String(payload.value?.season_period || '26-27')
  const parts = code.split('-')
  if (parts.length === 2) {
    return `20${parts[0]}年11月5日 — 20${parts[1]}年3月31日`
  }
  return '2026年11月5日 — 2027年3月31日'
})

const areaMissing = computed(() => Boolean(payload.value?.area_source?.area_missing))
const areaText = computed(() => {
  const m2 = payload.value?.area_source?.area_m2
  const wM2 = payload.value?.area_source?.area_10k_m2
  if (m2 == null || m2 <= 0) return '未维护'
  return `${Number(m2).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ㎡ (${Number(wM2).toFixed(2)} 万㎡)`
})

const excludedCount = computed(() => Number(payload.value?.excluded_count || 0))
const excludedDatesPreview = computed(() => {
  const list = Array.isArray(payload.value?.excluded_dates) ? payload.value.excluded_dates : []
  if (list.length <= 6) return list.join('、')
  return `${list.slice(0, 4).join('、')} 等共 ${list.length} 天`
})

const dailyRows = computed(() => (Array.isArray(payload.value?.daily_rows) ? payload.value.daily_rows : []))
const periods = computed(() => (Array.isArray(payload.value?.periods) ? payload.value.periods : []))
const summary = computed(() => payload.value?.summary || null)
const trajectorySummary = computed(() => payload.value?.trajectory_summary || null)
const hasValidEvaluation = computed(() => {
  if (!payload.value) return false
  if (queryState.mode === 'single') {
    return Boolean(payload.value.anchor_in_valid_window)
  }
  return Number(payload.value.valid_day_count || 0) > 0
})

const incompleteDaysCount = computed(() => dailyRows.value.filter(row => !row.is_complete).length)

const quadrantLegendList = computed(() => {
  const list = payload.value?.model_spec?.quadrants
  if (Array.isArray(list) && list.length) return list
  return [
    { code: 'I', name: 'Ⅰ 高耗热·高投诉', short_name: 'Ⅰ 高耗高诉', diagnosis: '投入与效果背离', color: '#ef4444' },
    { code: 'II', name: 'Ⅱ 低耗热·高投诉', short_name: 'Ⅱ 低耗高诉', diagnosis: '供热不足或滞后', color: '#f59e0b' },
    { code: 'III', name: 'Ⅲ 低耗热·低投诉', short_name: 'Ⅲ 低耗低诉', diagnosis: '潜在能效改善区', color: '#10b981' },
    { code: 'IV', name: 'Ⅳ 高耗热·低投诉', short_name: 'Ⅳ 高耗低诉', diagnosis: '服务良好但偏粗放', color: '#3b82f6' },
  ]
})

const summaryLabel = computed(() => {
  if (!summary.value) return ''
  return queryState.mode === 'single' ? `单日 ${summary.value.label}` : `${summary.value.valid_days} 个有效日累计`
})

const activeQuadrantColor = computed(() => summary.value?.quadrant?.color || '#64748b')
const quadrantCardStyle = computed(() => {
  const color = activeQuadrantColor.value
  return {
    borderTopColor: color,
    background: `linear-gradient(135deg, ${color}14 0%, #ffffff 65%)`,
  }
})

const deviationToneClass = computed(() => {
  const dev = summary.value?.heat_deviation_pct
  if (dev == null) return 'tone-slate'
  return dev > 0 ? 'tone-warm' : 'tone-cool'
})

const complaintToneClass = computed(() => {
  const idx = summary.value?.complaint_index
  if (idx == null) return 'tone-slate'
  return idx > 100 ? 'tone-danger' : 'tone-emerald'
})

const bandBadgeText = computed(() => {
  const band = summary.value?.empirical_band
  const status = summary.value?.band_status?.status
  if (!band) return '—'
  if (status === 'within_band') return `✓ ${band.label}经验带内`
  if (status === 'above_p95') return `↑ 超${band.label}95%上界`
  if (status === 'below_p5') return `↓ 低${band.label}5%下界`
  return `${band.label}参考`
})

const complaintIndexDeltaText = computed(() => {
  const idx = summary.value?.complaint_index
  if (idx == null) return '—'
  const diff = idx - 100
  if (Math.abs(diff) < 0.05) return '持平历史基准'
  return diff > 0 ? `高于基准 +${diff.toFixed(1)}` : `低于基准 ${diff.toFixed(1)}`
})

const hasAggregatePoint = computed(() => {
  if (queryState.mode === 'single') {
    return dailyRows.value.length > 1 && Boolean(trajectorySummary.value)
  }
  return (queryState.mode === 'rolling' ? periods.value.length : dailyRows.value.length) > 1
})

const trajectoryTimeMeta = computed(() => {
  const pts = getTrajectoryPoints()
  if (pts.length <= 1) return null
  const usePeriods = queryState.mode === 'rolling' && queryState.periodDays > 1
  return {
    count: pts.length,
    firstLabel: usePeriods ? pts[0].name : pts[0].shortLabel,
    lastLabel: usePeriods ? pts[pts.length - 1].name : pts[pts.length - 1].shortLabel,
  }
})

const activeTableSourceRows = computed(() => {
  if (queryState.mode === 'rolling' && queryState.periodDays > 1 && tableViewMode.value === 'periods') {
    return periods.value.map((p, idx) => ({
      _rowKey: `period-${idx}-${p.start_date}`,
      _label: p.label,
      _daysLabel: `${p.valid_days}天`,
      _avgTemp: p.avg_temp,
      _hddToday: p.avg_hdd20_today,
      _hddPrev3: p.avg_hdd20_prev3,
      _actualUnitHeat: p.actual_unit_heat_avg,
      _refUnitHeat: p.ref_unit_heat_avg,
      _actualHeat: p.actual_heat_gj,
      _refHeat: p.ref_heat_gj,
      _deviation: p.heat_deviation_pct,
      _actualComplaints: p.actual_complaints,
      _refComplaints: p.ref_complaints,
      _complaintIndex: p.complaint_index,
      _quadrant: p.quadrant,
      _isIncomplete: (p.incomplete_dates || []).length > 0,
      _missingHint: (p.incomplete_dates || []).length > 0 ? `含 ${(p.incomplete_dates || []).length} 个缺数日` : '',
    }))
  }
  return dailyRows.value.map((r) => ({
    _rowKey: r.date,
    _label: r.date,
    _daysLabel: '',
    _avgTemp: r.avg_temp,
    _hddToday: r.hdd20_today,
    _hddPrev3: r.hdd20_prev3,
    _actualUnitHeat: r.actual_unit_heat,
    _refUnitHeat: r.ref_unit_heat,
    _actualHeat: r.actual_heat_gj,
    _refHeat: r.ref_heat_gj,
    _deviation: r.heat_deviation_pct,
    _actualComplaints: r.actual_complaints,
    _refComplaints: r.ref_complaints,
    _complaintIndex: r.complaint_index,
    _quadrant: r.quadrant,
    _isIncomplete: !r.is_complete,
    _missingHint: (r.missing_reasons || []).join('；'),
  }))
})

const filteredTableRows = computed(() => {
  if (selectedQuadrantFilter.value === 'ALL') return activeTableSourceRows.value
  return activeTableSourceRows.value.filter(r => r._quadrant?.code === selectedQuadrantFilter.value)
})

const summaryForTableFoot = computed(() => {
  if (queryState.mode === 'single') {
    return dailyRows.value.length > 1 ? trajectorySummary.value : summary.value
  }
  return summary.value
})

const focusedPointLabel = computed(() => {
  if (!highlightedRowKey.value) return ''
  const matched = activeTableSourceRows.value.find(r => r._rowKey === highlightedRowKey.value)
  return matched?._label || highlightedRowKey.value
})

function countRowsByQuadrant(code) {
  return activeTableSourceRows.value.filter(r => r._quadrant?.code === code).length
}

function formatNum(val, digits = 2) {
  if (val === null || val === undefined || !Number.isFinite(Number(val))) return '—'
  return Number(val).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function formatSignedNum(val, digits = 2) {
  if (val === null || val === undefined || !Number.isFinite(Number(val))) return '—'
  const num = Number(val)
  const prefix = num > 0 ? '+' : ''
  return `${prefix}${num.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`
}

function formatSignedPercent(val) {
  if (val === null || val === undefined || !Number.isFinite(Number(val))) return '—'
  const num = Number(val)
  const prefix = num > 0 ? '+' : ''
  return `${prefix}${num.toFixed(2)}%`
}

function deviationTextClass(val) {
  if (val == null) return ''
  return Number(val) > 0 ? 'num-warm' : 'num-cool'
}

function complaintTextClass(val) {
  if (val == null) return ''
  return Number(val) > 100 ? 'num-danger' : 'num-emerald'
}

function getDefaultBizDate() {
  return payload.value?.default_biz_date || queryState.bizDate || ''
}

function shiftIsoDate(iso, deltaDays) {
  if (!iso) return ''
  const [y, m, d] = iso.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  dt.setUTCDate(dt.getUTCDate() + deltaDays)
  return dt.toISOString().slice(0, 10)
}

function getSeasonStartFor(iso) {
  if (!iso) return ''
  const [y, m] = iso.split('-').map(Number)
  const startYear = m >= 10 ? y : y - 1
  return `${startYear}-11-05`
}

function switchMode(newMode) {
  if (queryState.mode === newMode) return
  const baseDate = getDefaultBizDate()
  queryState.mode = newMode
  if (newMode === 'single') {
    queryState.bizDate = queryState.bizDate || baseDate
  } else if (newMode === 'rolling') {
    queryState.endDate = queryState.endDate || baseDate
    tableViewMode.value = queryState.periodDays > 1 ? 'periods' : 'daily'
  } else if (newMode === 'range') {
    queryState.endDate = queryState.endDate || baseDate
    if (!queryState.startDate) {
      queryState.startDate = shiftIsoDate(queryState.endDate, -17)
    }
    tableViewMode.value = 'daily'
  }
  fetchEvaluation()
}

function setSingleTraceDays(days) {
  queryState.singleTraceDays = days
  fetchEvaluation()
}

function setRollingSpan(days) {
  queryState.periodDays = days
  tableViewMode.value = days > 1 ? 'periods' : 'daily'
  fetchEvaluation()
}

function setRollingCount(count) {
  queryState.periodCount = count
  fetchEvaluation()
}

function clampAndFetchRollingCount() {
  const val = Number(queryState.periodCount)
  queryState.periodCount = Number.isFinite(val) ? Math.max(1, Math.min(60, Math.round(val))) : 4
  fetchEvaluation()
}

function applyQuickPreset(key) {
  const base = getDefaultBizDate()
  if (!base) return
  if (key === 'biz_day') {
    queryState.mode = 'single'
    queryState.bizDate = base
    queryState.singleTraceDays = 7
  } else if (key === 'last_7d') {
    queryState.mode = 'rolling'
    queryState.endDate = base
    queryState.periodDays = 1
    queryState.periodCount = 7
    tableViewMode.value = 'daily'
  } else if (key === 'last_4w') {
    queryState.mode = 'rolling'
    queryState.endDate = base
    queryState.periodDays = 7
    queryState.periodCount = 4
    tableViewMode.value = 'periods'
  } else if (key === 'month_to_date') {
    queryState.mode = 'range'
    queryState.startDate = `${base.slice(0, 7)}-01`
    queryState.endDate = base
    tableViewMode.value = 'daily'
  } else if (key === 'season_to_date') {
    queryState.mode = 'range'
    queryState.startDate = getSeasonStartFor(base)
    queryState.endDate = base
    tableViewMode.value = 'daily'
  }
  fetchEvaluation()
}

async function fetchEvaluation() {
  loading.value = true
  errorMessage.value = ''
  try {
    const params = { mode: queryState.mode }
    if (queryState.mode === 'single') {
      if (queryState.bizDate) params.biz_date = queryState.bizDate
      params.period_days = 1
      params.period_count = queryState.singleTraceDays
    } else if (queryState.mode === 'rolling') {
      if (queryState.endDate) params.end_date = queryState.endDate
      params.period_days = queryState.periodDays
      params.period_count = queryState.periodCount
    } else {
      if (queryState.startDate) params.start_date = queryState.startDate
      if (queryState.endDate) params.end_date = queryState.endDate
    }

    const res = await getJointEvaluation(PROJECT_KEY, params)
    payload.value = res
    if (!queryState.bizDate && res?.default_biz_date) {
      queryState.bizDate = res.default_biz_date
    }
    if (!queryState.endDate && res?.anchor_date) {
      queryState.endDate = res.anchor_date
    }
    if (!queryState.startDate && res?.default_biz_date) {
      queryState.startDate = shiftIsoDate(res.default_biz_date, -17)
    }
    selectedQuadrantFilter.value = 'ALL'
    highlightedRowKey.value = ''
    hoveredRowKey.value = ''
    activeSyncSource = null

    await nextTick()
    renderAllCharts()
  } catch (err) {
    console.error(err)
    errorMessage.value = err instanceof Error ? err.message : '加载主城区供热联合评价模型失败'
  } finally {
    loading.value = false
  }
}

// 计算明亮单调时间色盘（晴空蓝(最早) -> 亮靛蓝 -> 亮洋红 -> 珊瑚红(最新)）
function interpolateColor(ratio) {
  const stops = [
    [14, 165, 233],
    [99, 102, 241],
    [217, 70, 239],
    [239, 68, 68],
  ]
  const clamped = Math.max(0, Math.min(1, ratio))
  const scaled = clamped * (stops.length - 1)
  const idx = Math.min(stops.length - 2, Math.floor(scaled))
  const local = scaled - idx
  const c1 = stops[idx]
  const c2 = stops[idx + 1]
  const r = Math.round(c1[0] + (c2[0] - c1[0]) * local)
  const g = Math.round(c1[1] + (c2[1] - c1[1]) * local)
  const b = Math.round(c1[2] + (c2[2] - c1[2]) * local)
  return `rgb(${r}, ${g}, ${b})`
}

function getTrajectoryPoints() {
  const usePeriods = queryState.mode === 'rolling' && queryState.periodDays > 1
  if (usePeriods) {
    return periods.value
      .filter(p => p.heat_deviation_pct != null && p.complaint_index != null)
      .map((p, idx) => ({
        key: `period-${idx}-${p.start_date}`,
        shortLabel: `${idx + 1}`,
        name: p.label,
        dateRange: `${p.start_date} ~ ${p.end_date}`,
        x: Number(p.heat_deviation_pct),
        y: Number(p.complaint_index),
        avgTemp: p.avg_temp,
        actualUnitHeat: p.actual_unit_heat_avg,
        refUnitHeat: p.ref_unit_heat_avg,
        actualComplaints: p.actual_complaints,
        refComplaints: p.ref_complaints,
        quadrant: p.quadrant,
        seq: idx + 1,
      }))
  }
  return dailyRows.value
    .filter(r => r.heat_deviation_pct != null && r.complaint_index != null)
    .map((r, idx) => ({
      key: r.date,
      shortLabel: r.date.slice(5),
      name: r.date,
      dateRange: r.date,
      x: Number(r.heat_deviation_pct),
      y: Number(r.complaint_index),
      avgTemp: r.avg_temp,
      actualUnitHeat: r.actual_unit_heat,
      refUnitHeat: r.ref_unit_heat,
      actualComplaints: r.actual_complaints,
      refComplaints: r.ref_complaints,
      quadrant: r.quadrant,
      seq: idx + 1,
    }))
}

function syncHoverToTrend(rowKey) {
  if (!trendChart || !rowKey) return
  const tIdx = trendIndexByRowKey.get(rowKey)
  if (tIdx == null) return
  hoveredRowKey.value = rowKey
  trendChart.dispatchAction({ type: 'downplay' })
  trendChart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: tIdx })
  trendChart.dispatchAction({ type: 'highlight', seriesIndex: 3, dataIndex: tIdx })
  trendChart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: tIdx })
}

function syncHoverToQuadrant(rowKey) {
  if (!quadrantChart || !rowKey) return
  const qIdx = quadrantIndexByRowKey.get(rowKey)
  hoveredRowKey.value = rowKey
  quadrantChart.dispatchAction({ type: 'downplay', seriesName: '运行点位' })
  if (qIdx == null) {
    quadrantChart.dispatchAction({ type: 'hideTip' })
    return
  }
  quadrantChart.dispatchAction({ type: 'highlight', seriesName: '运行点位', dataIndex: qIdx })
  quadrantChart.dispatchAction({ type: 'showTip', seriesName: '运行点位', dataIndex: qIdx })
}

function previewRowInCharts(rowKey) {
  if (!rowKey) return
  activeSyncSource = 'table'
  syncHoverToQuadrant(rowKey)
  syncHoverToTrend(rowKey)
}

function clearChartSyncPreview() {
  activeSyncSource = null
  hoveredRowKey.value = ''
  quadrantChart?.dispatchAction({ type: 'downplay', seriesName: '运行点位' })
  quadrantChart?.dispatchAction({ type: 'hideTip' })
  trendChart?.dispatchAction({ type: 'downplay' })
  trendChart?.dispatchAction({ type: 'hideTip' })
}

function toggleFocusedRow(rowKey) {
  if (!rowKey) return
  highlightedRowKey.value = highlightedRowKey.value === rowKey ? '' : rowKey
  renderAllCharts()
}

function renderQuadrantChart() {
  if (!quadrantChartEl.value || !hasValidEvaluation.value) return
  if (!quadrantChart) {
    quadrantChart = echarts.init(quadrantChartEl.value)
    quadrantChart.on('click', (params) => {
      if (params?.data?.rowKey) {
        toggleFocusedRow(params.data.rowKey)
      }
    })
    quadrantChart.on('mouseover', (params) => {
      if (params?.seriesName === '运行点位' && params?.data?.rowKey) {
        activeSyncSource = 'quadrant'
        syncHoverToTrend(params.data.rowKey)
      }
    })
    quadrantChart.on('globalout', () => {
      if (activeSyncSource === 'quadrant') {
        clearChartSyncPreview()
      }
    })
  }

  const pts = getTrajectoryPoints()
  quadrantIndexByRowKey = new Map()
  pts.forEach((p, idx) => {
    quadrantIndexByRowKey.set(p.key, idx)
  })
  const aggSource = queryState.mode === 'single' ? trajectorySummary.value : summary.value
  const aggPoint =
    chartOptions.showAggregateStar &&
    hasAggregatePoint.value &&
    aggSource?.heat_deviation_pct != null &&
    aggSource?.complaint_index != null
      ? {
          name: queryState.mode === 'single' ? '轨迹区间累计' : '所选区间累计',
          x: Number(aggSource.heat_deviation_pct),
          y: Number(aggSource.complaint_index),
          quadrant: aggSource.quadrant,
          actualHeat: aggSource.actual_heat_gj,
          refHeat: aggSource.ref_heat_gj,
          actualComp: aggSource.actual_complaints,
          refComp: aggSource.ref_complaints,
        }
      : null

  const allX = pts.map(p => p.x).concat(aggPoint ? [aggPoint.x] : [])
  const allY = pts.map(p => p.y).concat(aggPoint ? [aggPoint.y] : [])
  const band = summary.value?.empirical_band
  if (chartOptions.showEmpiricalBand && band) {
    allX.push(Number(band.p5), Number(band.p95))
  }

  const minXRaw = allX.length ? Math.min(...allX, -15) : -25
  const maxXRaw = allX.length ? Math.max(...allX, 15) : 25
  const maxAbsX = Math.max(24, Math.ceil(Math.max(Math.abs(minXRaw), Math.abs(maxXRaw)) / 5) * 5 + 3)
  const xMin = -maxAbsX
  const xMax = maxAbsX

  const maxYRaw = allY.length ? Math.max(...allY, 160) : 200
  const yMin = 0
  const yMax = Math.max(200, Math.ceil((maxYRaw + 25) / 20) * 20)

  const totalPts = pts.length
  const scatterData = pts.map((p, idx) => {
    const ratio = totalPts <= 1 ? 1 : idx / (totalPts - 1)
    const color = chartOptions.colorByTime ? interpolateColor(ratio) : (p.quadrant?.color || '#3b82f6')
    const isStart = idx === 0
    const isLatest = idx === totalPts - 1
    const isFocused = highlightedRowKey.value === p.key
    const baseSize = chartOptions.colorByTime
      ? 10 + Math.round(ratio * 7)
      : (isLatest ? 16 : 11)
    const labelText = isFocused
      ? `📌 ${p.shortLabel}`
      : chartOptions.colorByTime && totalPts > 1 && isLatest
        ? `最新 ${p.shortLabel}`
        : chartOptions.colorByTime && totalPts > 1 && isStart
          ? `起 ${p.shortLabel}`
          : p.shortLabel
    const labelColor = isFocused
      ? '#6d28d9'
      : chartOptions.colorByTime && totalPts > 1 && isLatest
        ? '#dc2626'
        : chartOptions.colorByTime && totalPts > 1 && isStart
          ? '#0369a1'
          : '#334155'
    const labelBg = isFocused
      ? 'rgba(245, 243, 255, 0.96)'
      : chartOptions.colorByTime && totalPts > 1 && isLatest
        ? 'rgba(254, 242, 242, 0.96)'
        : chartOptions.colorByTime && totalPts > 1 && isStart
          ? 'rgba(224, 242, 254, 0.94)'
          : 'rgba(255, 255, 255, 0.88)'
    const labelBorder = isFocused
      ? '#c4b5fd'
      : chartOptions.colorByTime && totalPts > 1 && isLatest
        ? '#fca5a5'
        : chartOptions.colorByTime && totalPts > 1 && isStart
          ? '#7dd3fc'
          : 'transparent'

    return {
      value: [p.x, p.y],
      rowKey: p.key,
      meta: p,
      symbolSize: isFocused ? Math.max(baseSize + 3, 20) : baseSize,
      itemStyle: {
        color,
        opacity: chartOptions.colorByTime ? Number((0.84 + ratio * 0.16).toFixed(2)) : 1,
        borderColor: isFocused ? '#7c3aed' : '#ffffff',
        borderWidth: isFocused ? 3.5 : 2,
        shadowBlur: isFocused ? 18 : isLatest ? 14 : 6,
        shadowColor: isFocused ? 'rgba(124, 58, 237, 0.72)' : `${color}88`,
      },
      emphasis: {
        scale: 1.4,
        itemStyle: {
          opacity: 1,
          borderColor: '#0f172a',
          borderWidth: 3,
          shadowBlur: 18,
          shadowColor: 'rgba(15, 23, 42, 0.45)',
        },
      },
      label: {
        show: totalPts <= 22 || isLatest || isFocused || isStart,
        position: 'top',
        distance: isLatest || isFocused ? 8 : 6,
        formatter: labelText,
        fontSize: isFocused || isLatest ? 11.5 : 10,
        fontWeight: isFocused || isLatest || isStart ? 700 : 500,
        color: labelColor,
        backgroundColor: labelBg,
        borderColor: labelBorder,
        borderWidth: labelBorder === 'transparent' ? 0 : 1,
        padding: [2, 5],
        borderRadius: 4,
      },
    }
  })

  // 构造带方向箭头的平滑分步轨迹线（线宽与透明度随时间递增）
  const lineEdges = []
  for (let i = 0; i < pts.length - 1; i += 1) {
    const ratio = pts.length <= 2 ? 1 : i / (pts.length - 2)
    const segColor = chartOptions.colorByTime ? interpolateColor(ratio) : '#6366f1'
    lineEdges.push({
      coords: [
        [pts[i].x, pts[i].y],
        [pts[i + 1].x, pts[i + 1].y],
      ],
      lineStyle: {
        color: segColor,
        width: chartOptions.colorByTime ? Number((1.8 + ratio * 1.6).toFixed(2)) : 2.2,
        opacity: chartOptions.colorByTime ? Number((0.62 + ratio * 0.36).toFixed(2)) : 0.78,
        curveness: 0.12,
      },
    })
  }

  const latestPoint = totalPts ? scatterData[totalPts - 1] : null
  const focusedPoint = highlightedRowKey.value
    ? scatterData.find(item => item.rowKey === highlightedRowKey.value) || null
    : null

  const isMobile = isMobileViewport()
  const areaLabelSize = isMobile ? 10 : 12
  const areaLabelPad = isMobile ? [6, 6] : [10, 12]

  const markAreas = [
    [
      {
        name: 'Ⅰ 高耗热 · 高投诉\n投入与效果背离',
        xAxis: 0,
        yAxis: 100,
        itemStyle: { color: 'rgba(254, 226, 226, 0.52)' },
        label: { position: 'insideTopRight', color: '#dc2626', fontSize: areaLabelSize, fontWeight: 700, padding: areaLabelPad },
      },
      { xAxis: xMax, yAxis: yMax },
    ],
    [
      {
        name: 'Ⅱ 低耗热 · 高投诉\n供热不足或滞后',
        xAxis: xMin,
        yAxis: 100,
        itemStyle: { color: 'rgba(254, 243, 199, 0.55)' },
        label: { position: 'insideTopLeft', color: '#d97706', fontSize: areaLabelSize, fontWeight: 700, padding: areaLabelPad },
      },
      { xAxis: 0, yAxis: yMax },
    ],
    [
      {
        name: 'Ⅲ 低耗热 · 低投诉\n潜在能效改善区',
        xAxis: xMin,
        yAxis: yMin,
        itemStyle: { color: 'rgba(209, 250, 229, 0.52)' },
        label: { position: 'insideBottomLeft', color: '#059669', fontSize: areaLabelSize, fontWeight: 700, padding: areaLabelPad },
      },
      { xAxis: 0, yAxis: 100 },
    ],
    [
      {
        name: 'Ⅳ 高耗热 · 低投诉\n服务良好但偏粗放',
        xAxis: 0,
        yAxis: yMin,
        itemStyle: { color: 'rgba(219, 234, 254, 0.52)' },
        label: { position: 'insideBottomRight', color: '#2563eb', fontSize: areaLabelSize, fontWeight: 700, padding: areaLabelPad },
      },
      { xAxis: xMax, yAxis: 100 },
    ],
  ]

  const markLines = [
    { xAxis: 0, lineStyle: { color: '#334155', width: 1.8, type: 'dashed' }, label: { formatter: '偏差率 0%', position: 'insideEndTop', color: '#334155', fontSize: isMobile ? 10 : 11, fontWeight: 600 } },
    { yAxis: 100, lineStyle: { color: '#334155', width: 1.8, type: 'dashed' }, label: { formatter: '投诉指数 100', position: 'insideEndTop', color: '#334155', fontSize: isMobile ? 10 : 11, fontWeight: 600 } },
  ]

  if (chartOptions.showEmpiricalBand && band) {
    markAreas.push([
      {
        name: `${band.label}历史5%~95%经验带`,
        xAxis: band.p5,
        yAxis: yMin,
        itemStyle: {
          color: 'rgba(15, 118, 110, 0.08)',
          borderColor: 'rgba(15, 118, 110, 0.35)',
          borderWidth: 1,
          borderType: 'dashed',
        },
        label: { position: 'insideBottom', color: '#0f766e', fontSize: 10, padding: [0, 0, 6, 0] },
      },
      { xAxis: band.p95, yAxis: yMax },
    ])
  }

  const series = [
    {
      name: '背景象限',
      type: 'scatter',
      data: [],
      silent: true,
      markArea: { silent: true, data: markAreas },
      markLine: { silent: true, symbol: ['none', 'none'], data: markLines },
    },
    {
      name: '演进路径',
      type: 'lines',
      coordinateSystem: 'cartesian2d',
      symbol: ['none', 'arrow'],
      symbolSize: 10,
      data: lineEdges,
      silent: true,
      z: 3,
    },
    {
      name: '运行点位',
      type: 'scatter',
      data: scatterData,
      labelLayout: { hideOverlap: true },
      z: 5,
    },
  ]

  if (latestPoint) {
    series.push({
      name: '最新位置',
      type: 'effectScatter',
      coordinateSystem: 'cartesian2d',
      data: [{ value: latestPoint.value, meta: latestPoint.meta }],
      symbolSize: 19,
      rippleEffect: { brushType: 'stroke', scale: 2.4, period: 3.2 },
      itemStyle: { color: latestPoint.itemStyle.color, borderColor: '#fff', borderWidth: 2 },
      silent: true,
      z: 4,
    })
  }

  if (focusedPoint) {
    series.push({
      name: '当前锁定点',
      type: 'effectScatter',
      coordinateSystem: 'cartesian2d',
      data: [{ value: focusedPoint.value, meta: focusedPoint.meta }],
      symbolSize: 22,
      rippleEffect: { brushType: 'stroke', scale: 2.8, period: 2.2 },
      itemStyle: { color: '#7c3aed', borderColor: '#ffffff', borderWidth: 2.5 },
      silent: true,
      z: 6,
    })
  }

  if (aggPoint) {
    series.push({
      name: '区间汇总',
      type: 'scatter',
      symbol: 'path://M512 64l138.24 280.32 309.12 44.8-223.68 218.24 52.8 307.84L512 769.92 235.52 915.2l52.8-307.84L64.64 389.12l309.12-44.8z',
      symbolSize: 22,
      data: [{
        value: [aggPoint.x, aggPoint.y],
        agg: aggPoint,
        itemStyle: {
          color: '#f59e0b',
          borderColor: '#78350f',
          borderWidth: 1.5,
          shadowBlur: 12,
          shadowColor: 'rgba(245, 158, 11, 0.55)',
        },
        label: {
          show: true,
          position: 'bottom',
          formatter: `★ ${aggPoint.name}`,
          color: '#92400e',
          fontWeight: 700,
          fontSize: 11,
          backgroundColor: 'rgba(254, 243, 199, 0.92)',
          padding: [2, 6],
          borderRadius: 4,
        },
      }],
      z: 7,
    })
  }

  quadrantChart.setOption(
    {
      animationDuration: 550,
      grid: isMobile
        ? { left: 40, right: 14, top: 20, bottom: 38 }
        : { left: 56, right: 28, top: 24, bottom: 44 },
      tooltip: {
        trigger: 'item',
        confine: true,
        backgroundColor: 'rgba(15, 23, 42, 0.94)',
        borderColor: '#334155',
        borderWidth: 1,
        textStyle: { color: '#f8fafc', fontSize: 12 },
        formatter: (params) => {
          if (params.data?.agg) {
            const a = params.data.agg
            return [
              `<div style="font-weight:700;color:#fbbf24;margin-bottom:6px">★ ${a.name}</div>`,
              `<div>象限归属：<b>${a.quadrant?.name || '—'}</b></div>`,
              `<div>供热偏差率：<b>${formatSignedPercent(a.x)}</b></div>`,
              `<div>投诉强度指数：<b>${formatNum(a.y, 1)}</b></div>`,
              `<div>累计耗热：${formatNum(a.actualHeat, 0)} / 参考 ${formatNum(a.refHeat, 0)} GJ</div>`,
              `<div>累计投诉：${formatNum(a.actualComp, 0)} / 参考 ${formatNum(a.refComp, 1)} 件</div>`,
            ].join('')
          }
          const m = params.data?.meta
          if (!m) return ''
          const seqHint = totalPts > 1 && m.seq ? `（第 ${m.seq} / ${totalPts} 步）` : ''
          return [
            `<div style="font-weight:700;margin-bottom:6px">${m.name} <span style="color:#94a3b8;font-weight:500">${seqHint}</span></div>`,
            `<div>象限归属：<b style="color:${m.quadrant?.color || '#fff'}">${m.quadrant?.name || '—'}</b></div>`,
            `<div>供热偏差率：<b>${formatSignedPercent(m.x)}</b></div>`,
            `<div>投诉强度指数：<b>${formatNum(m.y, 1)}</b></div>`,
            `<div>日均气温：${formatNum(m.avgTemp, 2)} ℃</div>`,
            `<div>单耗（实际/参考）：${formatNum(m.actualUnitHeat, 2)} / ${formatNum(m.refUnitHeat, 2)} GJ/万㎡·日</div>`,
            `<div>投诉（实际/参考）：${formatNum(m.actualComplaints, 0)} / ${formatNum(m.refComplaints, 1)} 件</div>`,
          ].join('')
        },
      },
      xAxis: {
        type: 'value',
        name: '气象修正供热偏差率 (%)',
        nameLocation: 'middle',
        nameGap: isMobile ? 22 : 26,
        nameTextStyle: { color: '#475569', fontSize: isMobile ? 11 : 12 },
        min: xMin,
        max: xMax,
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.22)' } },
        axisLabel: { color: '#475569', fontSize: isMobile ? 10 : 12, formatter: '{value}%' },
      },
      yAxis: {
        type: 'value',
        name: '投诉强度指数',
        nameTextStyle: { color: '#475569', fontSize: isMobile ? 11 : 12 },
        min: yMin,
        max: yMax,
        splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.22)' } },
        axisLabel: { color: '#475569', fontSize: isMobile ? 10 : 12 },
      },
      series,
    },
    true,
  )
}

function renderTrendChart() {
  if (!trendChartEl.value || !hasValidEvaluation.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartEl.value)
    trendChart.on('updateAxisPointer', (event) => {
      if (activeSyncSource === 'quadrant' || activeSyncSource === 'table') return
      const axisInfo = Array.isArray(event?.axesInfo) ? event.axesInfo[0] : null
      const rawIdx = axisInfo?.value
      const idx = typeof rawIdx === 'number' ? rawIdx : Number(rawIdx)
      if (!Number.isInteger(idx) || idx < 0 || idx >= trendRowKeys.length) return
      activeSyncSource = 'trend'
      syncHoverToQuadrant(trendRowKeys[idx])
    })
    trendChart.on('globalout', () => {
      if (activeSyncSource === 'trend') {
        clearChartSyncPreview()
      }
    })
    trendChart.getZr().on('click', (event) => {
      if (!trendChart || !trendRowKeys.length) return
      const pt = [event.offsetX, event.offsetY]
      if (!trendChart.containPixel({ gridIndex: 0 }, pt) && !trendChart.containPixel({ gridIndex: 1 }, pt)) {
        return
      }
      const gridIdx = trendChart.containPixel({ gridIndex: 0 }, pt) ? 0 : 1
      const coord = trendChart.convertFromPixel({ seriesIndex: gridIdx === 0 ? 0 : 3 }, pt)
      const idx = Array.isArray(coord) ? Math.round(coord[0]) : -1
      if (idx >= 0 && idx < trendRowKeys.length) {
        toggleFocusedRow(trendRowKeys[idx])
      }
    })
  }

  const usePeriods = queryState.mode === 'rolling' && queryState.periodDays > 1
  const items = usePeriods ? periods.value : dailyRows.value

  trendRowKeys = items.map((item, idx) => (usePeriods ? `period-${idx}-${item.start_date}` : item.date))
  trendIndexByRowKey = new Map()
  trendRowKeys.forEach((key, idx) => {
    trendIndexByRowKey.set(key, idx)
  })
  const focusedTrendIndex = highlightedRowKey.value ? trendIndexByRowKey.get(highlightedRowKey.value) : null

  const xLabels = items.map(item => (usePeriods ? item.label : item.date.slice(5)))
  const actualUnit = items.map(item => (usePeriods ? item.actual_unit_heat_avg : item.actual_unit_heat))
  const refUnit = items.map(item => (usePeriods ? item.ref_unit_heat_avg : item.ref_unit_heat))
  const avgTemp = items.map(item => item.avg_temp)
  const actualComplaints = items.map((item, idx) => {
    const isFocused = focusedTrendIndex === idx
    return {
      value: item.actual_complaints,
      itemStyle: {
        color: item.quadrant?.color || '#94a3b8',
        borderRadius: [4, 4, 0, 0],
        borderColor: isFocused ? '#7c3aed' : 'transparent',
        borderWidth: isFocused ? 2.5 : 0,
      },
    }
  })
  const refComplaints = items.map(item => item.ref_complaints)

  const focusMarkLineTop =
    focusedTrendIndex != null
      ? {
          silent: true,
          symbol: ['none', 'none'],
          lineStyle: { color: '#7c3aed', width: 2, type: 'dashed' },
          label: {
            position: 'insideEndTop',
            formatter: `📌 ${xLabels[focusedTrendIndex]}`,
            color: '#6d28d9',
            fontWeight: 700,
            backgroundColor: '#f5f3ff',
            padding: [2, 6],
            borderRadius: 4,
          },
          data: [{ xAxis: focusedTrendIndex }],
        }
      : undefined

  const focusMarkLineBottom =
    focusedTrendIndex != null
      ? {
          silent: true,
          symbol: ['none', 'none'],
          lineStyle: { color: '#7c3aed', width: 2, type: 'dashed' },
          label: { show: false },
          data: [{ xAxis: focusedTrendIndex }],
        }
      : undefined

  const isMobile = isMobileViewport()

  trendChart.setOption(
    {
      animationDuration: 450,
      tooltip: {
        trigger: 'axis',
        confine: true,
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(15, 23, 42, 0.94)',
        borderColor: '#334155',
        textStyle: { color: '#f8fafc', fontSize: 12 },
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      legend: [
        {
          top: 2,
          left: 'center',
          itemGap: isMobile ? 8 : 14,
          itemWidth: isMobile ? 12 : 16,
          itemHeight: isMobile ? 9 : 10,
          textStyle: { color: '#334155', fontSize: isMobile ? 10.5 : 11 },
          data: ['实际单耗', 'HDD20参考单耗', '日均气温'],
        },
        {
          top: isMobile ? 222 : 250,
          left: 'center',
          itemGap: isMobile ? 10 : 16,
          itemWidth: isMobile ? 14 : 18,
          itemHeight: isMobile ? 9 : 10,
          textStyle: { color: '#334155', fontSize: isMobile ? 10.5 : 11 },
          formatter: name => (name === '实际投诉量' ? '实际投诉量(按象限着色)' : name),
          data: ['实际投诉量', '参考投诉基准'],
        },
      ],
      grid: isMobile
        ? [
            { left: 38, right: 38, top: 50, height: 154 },
            { left: 38, right: 38, top: 272, height: 138 },
          ]
        : [
            { left: 50, right: 48, top: 56, height: 174 },
            { left: 50, right: 48, top: 304, height: 158 },
          ],
      xAxis: [
        {
          type: 'category',
          data: xLabels,
          gridIndex: 0,
          axisLabel: { show: false },
          axisLine: { lineStyle: { color: '#cbd5e1' } },
        },
        {
          type: 'category',
          data: xLabels,
          gridIndex: 1,
          axisLabel: {
            color: '#475569',
            fontSize: isMobile ? 10 : 11,
            rotate: isMobile && xLabels.length > 7 ? 35 : 0,
          },
          axisLine: { lineStyle: { color: '#cbd5e1' } },
        },
      ],
      yAxis: [
        {
          type: 'value',
          name: '单耗',
          nameGap: isMobile ? 8 : 10,
          gridIndex: 0,
          nameTextStyle: { color: '#64748b', fontSize: isMobile ? 10 : 11 },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          axisLabel: { color: '#475569', fontSize: isMobile ? 10 : 11 },
        },
        {
          type: 'value',
          name: '气温℃',
          nameGap: isMobile ? 8 : 10,
          gridIndex: 0,
          nameTextStyle: { color: '#0284c7', fontSize: isMobile ? 10 : 11 },
          splitLine: { show: false },
          axisLabel: { color: '#0284c7', fontSize: isMobile ? 10 : 11, formatter: '{value}℃' },
        },
        {
          type: 'value',
          name: '投诉(件)',
          nameGap: isMobile ? 8 : 10,
          gridIndex: 1,
          nameTextStyle: { color: '#64748b', fontSize: isMobile ? 10 : 11 },
          splitLine: { lineStyle: { color: '#f1f5f9' } },
          axisLabel: { color: '#475569', fontSize: isMobile ? 10 : 11 },
        },
      ],
      series: [
        {
          name: '实际单耗',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          smooth: 0.25,
          symbolSize: 7,
          data: actualUnit,
          markLine: focusMarkLineTop,
          itemStyle: { color: '#2563eb' },
          lineStyle: { width: 2.5, color: '#2563eb' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(37, 99, 235, 0.20)' },
              { offset: 1, color: 'rgba(37, 99, 235, 0.01)' },
            ]),
          },
        },
        {
          name: 'HDD20参考单耗',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 0,
          smooth: 0.25,
          symbolSize: 6,
          data: refUnit,
          itemStyle: { color: '#f97316' },
          lineStyle: { width: 2.2, type: 'dashed', color: '#f97316' },
        },
        {
          name: '日均气温',
          type: 'line',
          xAxisIndex: 0,
          yAxisIndex: 1,
          smooth: 0.25,
          symbol: 'none',
          data: avgTemp,
          itemStyle: { color: '#06b6d4' },
          lineStyle: { width: 1.5, type: 'dotted', color: '#06b6d4' },
        },
        {
          name: '实际投诉量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 2,
          barMaxWidth: 26,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#ef4444' },
              { offset: 0.34, color: '#f59e0b' },
              { offset: 0.67, color: '#10b981' },
              { offset: 1, color: '#3b82f6' },
            ]),
            borderRadius: [4, 4, 0, 0],
          },
          data: actualComplaints,
          markLine: focusMarkLineBottom,
        },
        {
          name: '参考投诉基准',
          type: 'line',
          xAxisIndex: 1,
          yAxisIndex: 2,
          symbol: 'none',
          data: refComplaints,
          itemStyle: { color: '#0f766e' },
          lineStyle: { width: 2, type: 'dashed', color: '#0f766e' },
        },
      ],
    },
    true,
  )
}

function renderAllCharts() {
  renderQuadrantChart()
  renderTrendChart()
  ensureChartResizeObserver()
}

function syncChartViewportLayout() {
  const nextMobile = isMobileViewport()
  const modeChanged = nextMobile !== lastMobileChartMode
  lastMobileChartMode = nextMobile
  quadrantChart?.resize()
  trendChart?.resize()
  if (modeChanged && hasValidEvaluation.value) {
    renderAllCharts()
    quadrantChart?.resize()
    trendChart?.resize()
  }
}

function scheduleChartResize() {
  if (resizeRafId) cancelAnimationFrame(resizeRafId)
  resizeRafId = requestAnimationFrame(() => {
    resizeRafId = 0
    syncChartViewportLayout()
  })
}

function ensureChartResizeObserver() {
  if (typeof ResizeObserver === 'undefined') return
  if (!chartResizeObserver) {
    chartResizeObserver = new ResizeObserver(() => {
      scheduleChartResize()
    })
  }
  if (quadrantChartEl.value) chartResizeObserver.observe(quadrantChartEl.value)
  if (trendChartEl.value) chartResizeObserver.observe(trendChartEl.value)
}

function handleResize() {
  scheduleChartResize()
}

function exportExcel() {
  if (!dailyRows.value.length) return
  exportJointEvaluationExcelFile(payload.value, {
    mode: queryState.mode,
    singleTraceDays: queryState.singleTraceDays,
    periodDays: queryState.periodDays,
    periodCount: queryState.periodCount,
  })
}

watch(hasValidEvaluation, async (ready) => {
  if (ready) {
    await nextTick()
    renderAllCharts()
  }
})

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  await ensureProjectsLoaded()
  await fetchEvaluation()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (resizeRafId) cancelAnimationFrame(resizeRafId)
  chartResizeObserver?.disconnect()
  chartResizeObserver = null
  quadrantChart?.dispose()
  trendChart?.dispose()
  quadrantChart = null
  trendChart = null
})
</script>

<style scoped>
.joint-eval-view {
  min-height: 100vh;
  background: linear-gradient(180deg, #f1f5f9 0%, #f8fafc 45%, #eef2f7 100%);
  color: #0f172a;
}

.joint-eval-main {
  max-width: 1460px;
  margin: 0 auto;
  padding: 20px 24px 48px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.top-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.ghost-btn {
  background: #ffffff;
  color: #1e293b;
  border-color: #cbd5e1;
}

.ghost-btn:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #94a3b8;
}

.export-btn {
  background: linear-gradient(135deg, #2563eb 0%, #0ea5e9 100%);
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22);
}

.export-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.3);
}

/* 顶部英雄横幅 */
.hero-banner {
  border-radius: 18px;
  padding: 22px 26px;
  background: linear-gradient(125deg, #0f172a 0%, #1e3a8a 52%, #0f766e 100%);
  color: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.14);
}

.hero-left {
  flex: 1 1 560px;
  min-width: 0;
}

.hero-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.badge-season,
.badge-window {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 999px;
}

.badge-season {
  background: rgba(56, 189, 248, 0.22);
  color: #bae6fd;
  border: 1px solid rgba(56, 189, 248, 0.4);
}

.badge-window {
  background: rgba(16, 185, 129, 0.2);
  color: #a7f3d0;
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.hero-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 0.3px;
}

.hero-subtitle {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(241, 245, 249, 0.86);
  max-width: 760px;
}

.hero-meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(150px, auto));
  gap: 12px;
}

.meta-tile {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 12px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 11px;
  color: rgba(226, 232, 240, 0.82);
}

.meta-value {
  font-size: 14px;
  color: #ffffff;
}

.text-warn {
  color: #fca5a5;
}

/* 提示横幅 */
.alert-banner {
  border-radius: 12px;
  padding: 11px 16px;
  font-size: 13px;
  line-height: 1.5;
}

.alert-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.alert-warn {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
}

.alert-info {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
}

.excluded-preview {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}

/* 通用卡片 */
.card {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

/* 控制台 */
.control-deck {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.control-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.mode-tabs {
  display: inline-flex;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 12px;
  gap: 4px;
}

.mode-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 7px 14px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.18s ease;
}

.mode-tab.active {
  background: #ffffff;
  color: #1d4ed8;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}

.quick-presets {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.preset-title {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.preset-chip {
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #334155;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.preset-chip:hover {
  background: #eff6ff;
  border-color: #60a5fa;
  color: #1d4ed8;
}

.params-row {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
}

.param-field {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.param-label {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
}

.param-input,
.param-number-input {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  color: #0f172a;
  background: #ffffff;
}

.param-number-input {
  width: 66px;
  text-align: center;
}

.pill-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.count-pill {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  padding: 5px 11px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.count-pill.active {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #ffffff;
}

/* KPI 网格 */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(220px, 1fr));
  gap: 16px;
}

.kpi-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-top: 4px solid #64748b;
  border-radius: 16px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
}

.kpi-card.tone-warm { border-top-color: #f97316; background: linear-gradient(135deg, #fff7ed 0%, #ffffff 60%); }
.kpi-card.tone-cool { border-top-color: #0ea5e9; background: linear-gradient(135deg, #f0f9ff 0%, #ffffff 60%); }
.kpi-card.tone-danger { border-top-color: #ef4444; background: linear-gradient(135deg, #fef2f2 0%, #ffffff 60%); }
.kpi-card.tone-emerald { border-top-color: #10b981; background: linear-gradient(135deg, #ecfdf5 0%, #ffffff 60%); }
.kpi-card.tone-slate { border-top-color: #6366f1; background: linear-gradient(135deg, #eef2ff 0%, #ffffff 60%); }

.kpi-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.kpi-title {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.kpi-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: #475569;
  font-weight: 600;
}

.kpi-main {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.kpi-value {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
}

.kpi-unit {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.kpi-sub-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.07);
  color: #1e293b;
}

.kpi-details {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e2e8f0;
}

.kpi-detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
  color: #64748b;
}

.kpi-detail-item strong {
  font-size: 12px;
  color: #1e293b;
}

.kpi-footnote {
  margin: 0;
  font-size: 11px;
  color: #64748b;
  line-height: 1.4;
}

.quadrant-hero {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.quadrant-pill {
  color: #ffffff;
  font-size: 14px;
  font-weight: 800;
  padding: 6px 12px;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.14);
}

.quadrant-diagnosis {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.quadrant-action {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: #334155;
}

/* 图表网格 */
.charts-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
  gap: 18px;
}

.chart-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.chart-title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #0f172a;
}

.chart-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: #64748b;
}

.chart-toggles {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toggle-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.lock-focus-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #6d28d9;
  background: #f5f3ff;
  border: 1px solid #c4b5fd;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
}

.lock-focus-chip:hover {
  background: #ede9fe;
}

.lock-close {
  font-size: 11px;
  opacity: 0.75;
}

.trend-scope-badge {
  font-size: 12px;
  font-weight: 600;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 4px 10px;
  border-radius: 999px;
}

.q-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}

.time-order-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 11.5px;
  color: #475569;
}

.time-order-badge {
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
}

.time-order-badge.start {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #7dd3fc;
}

.time-order-badge.end {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fca5a5;
}

.time-order-bar {
  width: 88px;
  height: 7px;
  border-radius: 999px;
  background: linear-gradient(90deg, #0ea5e9 0%, #6366f1 35%, #d946ef 70%, #ef4444 100%);
  display: inline-block;
}

.time-order-hint {
  color: #64748b;
  font-size: 11px;
}

.chart-canvas {
  width: 100%;
}

.quadrant-canvas {
  height: 460px;
}

.trend-canvas {
  height: 498px;
}

/* 明细表 */
.table-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.table-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.table-view-switch {
  display: inline-flex;
  background: #f1f5f9;
  padding: 3px;
  border-radius: 8px;
  gap: 4px;
}

.sub-tab {
  border: none;
  background: transparent;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
}

.sub-tab.active {
  background: #ffffff;
  color: #1d4ed8;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
}

.quadrant-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.q-filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.q-filter-btn.active {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
}

.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.mobile-scroll-hint {
  display: none;
  margin: 0;
  font-size: 11.5px;
  color: #64748b;
}

.mini-table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.eval-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  min-width: 1040px;
}

.eval-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 700;
  padding: 10px;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.eval-table th small {
  font-weight: 500;
  color: #94a3b8;
}

.eval-table td {
  padding: 9px 10px;
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
}

.eval-table tbody tr {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.eval-table tbody tr:hover {
  background: #f8fafc;
}

.eval-table tbody tr.row-highlighted {
  background: #ede9fe;
  box-shadow: inset 3px 0 0 #7c3aed;
}

.eval-table tbody tr.row-hovered {
  background: #eff6ff;
}

.eval-table tbody tr.row-incomplete {
  background: #fffbeb66;
}

.eval-table .num {
  text-align: right;
}

.cell-date {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.days-mini-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
}

.missing-tip {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  background: #fef3c7;
  color: #b45309;
}

.table-q-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  white-space: nowrap;
}

.summary-foot-row td {
  background: #f1f5f9;
  font-weight: 700;
  border-top: 2px solid #cbd5e1;
}

.num-warm { color: #ea580c; font-weight: 700; }
.num-cool { color: #0284c7; font-weight: 700; }
.num-danger { color: #dc2626; font-weight: 700; }
.num-emerald { color: #059669; font-weight: 700; }
.text-muted { color: #94a3b8; }

/* 模型参数透明卡 */
.spec-card {
  overflow: hidden;
}

.spec-toggle-btn {
  width: 100%;
  border: none;
  background: #f8fafc;
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  cursor: pointer;
}

.spec-body {
  padding: 16px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.spec-formula-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 16px;
}

.formula-title {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 6px;
}

.formula-code {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: #1d4ed8;
  margin-bottom: 6px;
}

.formula-meta {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}

.spec-tables-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.spec-mini-box h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #1e293b;
}

.mini-spec-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.mini-spec-table th,
.mini-spec-table td {
  padding: 7px 10px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.mini-spec-table .num {
  text-align: right;
}

.state-card {
  padding: 48px 24px;
  text-align: center;
  color: #475569;
}

.error-state {
  color: #b91c1c;
  background: #fef2f2;
  border-color: #fecaca;
}

.empty-icon {
  font-size: 36px;
  margin-bottom: 8px;
}

.font-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

@media (max-width: 1180px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .charts-layout {
    grid-template-columns: 1fr;
  }
  .spec-tables-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .joint-eval-main {
    padding: 12px 12px 36px;
    gap: 14px;
  }
  .top-nav-bar {
    align-items: stretch;
  }
  .header-actions {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
  .header-actions .btn {
    justify-content: center;
    padding: 8px 10px;
  }
  .hero-banner {
    padding: 16px;
    border-radius: 14px;
    gap: 14px;
  }
  .hero-title {
    font-size: 19px;
    line-height: 1.3;
  }
  .hero-subtitle {
    font-size: 12.5px;
  }
  .hero-meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    width: 100%;
  }
  .meta-tile {
    padding: 8px 11px;
  }
  .meta-tile:nth-child(2) {
    grid-column: 1 / -1;
  }
  .meta-value {
    font-size: 13px;
  }
  .control-deck {
    padding: 14px;
    gap: 12px;
  }
  .mode-tabs {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }
  .mode-tab {
    justify-content: center;
    padding: 8px 4px;
    font-size: 12px;
    gap: 4px;
    white-space: nowrap;
  }
  .quick-presets {
    width: 100%;
    gap: 6px;
  }
  .preset-title {
    width: 100%;
  }
  .preset-chip {
    padding: 5px 10px;
    font-size: 11.5px;
  }
  .params-row {
    gap: 12px;
  }
  .param-field {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
  }
  .param-input {
    min-width: 0;
    width: 100%;
    box-sizing: border-box;
  }
  .pill-group {
    width: 100%;
  }
  .count-pill {
    flex: 1 1 auto;
    text-align: center;
    padding: 6px 8px;
  }
  .kpi-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .kpi-card {
    padding: 14px 15px;
  }
  .kpi-main {
    flex-wrap: wrap;
  }
  .kpi-value {
    font-size: 24px;
  }
  .kpi-details {
    gap: 6px;
  }
  .chart-card,
  .table-card {
    padding: 14px;
  }
  .chart-title {
    font-size: 15px;
  }
  .quadrant-canvas {
    height: 360px;
  }
  .trend-canvas {
    height: 456px;
  }
  .quadrant-filters {
    width: 100%;
    gap: 6px;
  }
  .q-filter-btn {
    padding: 5px 9px;
    font-size: 11.5px;
  }
  .mobile-scroll-hint {
    display: block;
  }
  .table-scroll {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
  }
  .eval-table th:first-child,
  .eval-table td:first-child {
    position: sticky;
    left: 0;
    z-index: 2;
    box-shadow: 2px 0 6px rgba(15, 23, 42, 0.06);
  }
  .eval-table thead th:first-child {
    z-index: 3;
    background: #f8fafc;
  }
  .eval-table tbody td:first-child {
    background: #ffffff;
  }
  .eval-table tbody tr.row-incomplete td:first-child {
    background: #fefce8;
  }
  .eval-table tbody tr.row-hovered td:first-child {
    background: #eff6ff;
  }
  .eval-table tbody tr.row-highlighted td:first-child {
    background: #ede9fe;
  }
  .eval-table tfoot tr.summary-foot-row td:first-child {
    background: #f1f5f9;
  }
  .spec-toggle-btn {
    padding: 12px 14px;
    font-size: 13px;
    text-align: left;
    gap: 8px;
  }
  .spec-body {
    padding: 12px 14px 16px;
  }
  .formula-code {
    font-size: 12px;
    word-break: break-word;
  }
}

@media (max-width: 420px) {
  .mode-tab {
    font-size: 11.5px;
    padding: 7px 2px;
  }
}
</style>
