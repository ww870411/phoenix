<template>
  <div class="data-analysis-view">
    <AppHeader />
    <main class="analysis-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <section class="card elevated analysis-block">
        <header class="card-header">
          <div>
            <h2>{{ pageDisplayName }}</h2>
            <p class="analysis-subtitle"></p>
          </div>
          <span class="analysis-tag">Beta</span>
        </header>

        <div v-if="loading" class="page-state">配置加载中，请稍候…</div>
        <div v-else-if="errorMessage" class="page-state error">{{ errorMessage }}</div>

        <template v-else>
          <div class="form-layout">
            <div class="form-grid form-grid--top">
              <div class="form-panel form-panel--compact">
                <div class="panel-header">
                  <h3>单位选择（多选）</h3>
                  <span class="panel-hint">已选 {{ selectedUnits.length }} / {{ unitOptions.length }}</span>
                </div>
                <div class="chip-group">
                  <label
                    v-for="unit in unitOptions"
                    :key="unit.value"
                    class="chip checkbox"
                  >
                    <input
                      type="checkbox"
                      :checked="selectedUnits.includes(unit.value)"
                      @change="handleUnitSelection(unit.value, $event.target.checked)"
                    />
                    <span class="chip-label">
                      <span v-if="getUnitSelectionOrder(unit.value)" class="chip-order">
                        {{ getUnitSelectionOrder(unit.value) }}
                      </span>
                      <span>{{ unit.label }}</span>
                    </span>
                  </label>
                </div>
              </div>

              <div class="form-panel form-panel--compact">
                <div class="panel-header">
                  <h3>分析模式</h3>
                  <span class="panel-hint">切换单日或区间累计</span>
                </div>
                <div class="chip-group compact">
                  <label
                    v-for="mode in analysisModes"
                    :key="mode.value"
                    class="chip radio"
                  >
                    <input
                      type="radio"
                      name="analysisMode"
                      :value="mode.value"
                      v-model="analysisMode"
                    />
                    <span>{{ mode.label }}</span>
                  </label>
                </div>
                <div class="date-subsection">
                  <div class="panel-header">
                    <h4>日期范围</h4>
                    <span class="panel-hint">与分析模式联动</span>
                  </div>
                  <div class="date-grid">
                    <label class="date-field">
                      <span>起始日期</span>
                      <input type="date" v-model="startDate" />
                    </label>
                    <label class="date-field">
                      <span>结束日期</span>
                      <input type="date" v-model="endDate" :disabled="analysisMode === 'daily'" />
                    </label>
                  </div>
                  <p class="panel-hint">
                    {{ analysisMode === 'daily' ? '单日模式会自动将结束日期同步为起始日期。' : '累计模式支持跨日期区间。' }}
                  </p>
                </div>
              </div>
            </div>

            <div class="form-panel form-panel--metrics">
              <div class="panel-header">
                <h3>指标选择（多选）</h3>
                <div class="panel-actions">
                  <button class="btn ghost xs" type="button" @click="selectAllMetrics">
                    全选
                  </button>
                  <button class="btn ghost xs" type="button" @click="clearMetrics">
                    清空
                  </button>
                </div>
              </div>
              <p class="panel-hint">
                已选择 {{ selectedMetrics.size }} 项
              </p>
              <div class="metrics-panel-body">
                <div v-if="resolvedMetricGroups.length" class="metrics-groups">
                  <div
                    v-for="group in resolvedMetricGroups"
                    :key="group.key"
                    class="metrics-group"
                  >
                    <div class="metrics-group-header">
                      <div class="metrics-group-title">
                        <h4>{{ group.label }}</h4>
                        <span class="panel-hint">共 {{ group.options.length }} 项</span>
                      </div>
                      <div class="metrics-group-actions">
                        <span v-if="group.key === 'constant'" class="group-badge">常量</span>
                        <span
                          v-else-if="group.key === 'adjustment'"
                          class="group-badge group-badge--outline"
                        >
                          调整
                        </span>
                        <span
                          v-else-if="group.key === 'temperature'"
                          class="group-badge group-badge--temp"
                        >
                          气温
                        </span>
                      </div>
                    </div>
                    <div class="metrics-grid">
                      <label
                        v-for="metric in group.options"
                        :key="`${group.key}-${metric.value}`"
                        class="chip checkbox"
                      >
                        <input
                          type="checkbox"
                          :value="metric.value"
                          :checked="selectedMetrics.has(metric.value)"
                          :disabled="queryLoading"
                          @change="toggleMetric(metric.value)"
                        />
                        <span class="chip-label">
                          <span v-if="getMetricSelectionOrder(metric.value)" class="chip-order">
                            {{ getMetricSelectionOrder(metric.value) }}
                          </span>
                          <span>{{ metric.label }}</span>
                        </span>
                      </label>
                    </div>
                  </div>
                </div>
                <div v-else class="panel-hint">
                  暂无可选指标，请检查配置文件。
                </div>
              </div>
            </div>

          </div>

          <div v-if="formError" class="page-state error">{{ formError }}</div>

          <div class="form-actions">
            <button
              class="btn primary"
              type="button"
              :disabled="queryLoading"
              @click="runAnalysis"
            >
              {{ queryLoading ? '生成中…' : '生成分析结果' }}
            </button>
            <button class="btn ghost" type="button" :disabled="queryLoading" @click="resetSelections">
              重置选择
            </button>
            <div class="ai-report-controls">
              <label class="ai-report-toggle">
                <input
                  type="checkbox"
                  v-model="aiReportEnabled"
                  :disabled="queryLoading || !aiFeatureAccessible"
                  :title="!aiFeatureAccessible ? '当前账号未被授权使用智能报告' : ''"
                />
                <span>智能报告生成（BETA）</span>
              </label>
              <span v-if="!aiFeatureAccessible" class="ai-report-hint">
                当前账号未开放智能报告
              </span>
              <button
                v-if="canConfigureAiSettings"
                type="button"
                class="btn ghost ai-settings-btn"
                :disabled="aiSettingsLoading || aiSettingsSaving"
                @click="openAiSettingsDialog"
              >
                智能体设定
              </button>
            </div>
          </div>
        </template>
      </section>

      <section class="card elevated result-block">
        <header class="card-header">
          <div>
            <h3>分析结果预览</h3>
            <p class="analysis-subtitle">
              <template v-if="lastQueryMeta">
                {{ lastQueryMeta.analysis_mode_label || analysisModeLabel }} ｜ 单位：{{ lastQueryMeta.unit_label }}
                <template v-if="lastQueryMeta.start_date">
                  ｜ 日期：
                  <span>
                    <template v-if="lastQueryMeta.end_date && lastQueryMeta.end_date !== lastQueryMeta.start_date">
                      {{ lastQueryMeta.start_date }} ~ {{ lastQueryMeta.end_date }}
                    </template>
                    <template v-else>
                      {{ lastQueryMeta.start_date }}
                    </template>
                  </span>
                </template>
              </template>
              <template v-else>
                单位：{{ activeUnitLabel }} ｜ 指标数：{{ selectedMetrics.size }}
              </template>
            </p>
          </div>
          <div class="result-header-actions">
            <button
              class="btn ghost"
              type="button"
              :disabled="!resultUnitKeys.length || queryLoading"
              @click="downloadExcel"
            >
              下载 Excel
            </button>
            <button
              class="btn ghost"
              type="button"
              :disabled="aiReportButtonDisabled"
              @click="downloadAiReport"
            >
              {{ aiReportButtonLabel }}
            </button>
          </div>
        </header>
        <p v-if="aiReportStatusMessage" class="ai-report-status">{{ aiReportStatusMessage }}</p>

        <div v-if="queryLoading" class="page-state">正在生成分析结果，请稍候…</div>
        <div v-else-if="!previewRows.length" class="page-state muted">
          <template v-if="resultUnitKeys.length">
            当前单位暂无可显示的数据，请尝试切换其它单位或调整指标。
          </template>
          <template v-else>
            请选择单位、指标与日期后点击“生成分析结果”，即可在此查看组合预览。
          </template>
        </div>
        <div v-else>
          <div v-if="resultUnitKeys.length > 1" class="unit-switch">
            <span class="unit-switch__label">切换单位：</span>
            <div class="unit-switch__chips">
              <button
                v-for="unitKey in resultUnitKeys"
                :key="`result-unit-${unitKey}`"
                type="button"
                class="unit-toggle"
                :class="{ active: activeUnit === unitKey }"
                @click="handleSwitchUnit(unitKey)"
              >
                {{ resolveUnitLabel(unitKey) }}
              </button>
            </div>
          </div>
          <div class="info-banner" v-if="infoBanner">{{ infoBanner }}</div>
          <ul v-if="queryWarnings.length" class="warning-list">
            <li v-for="(warning, idx) in queryWarnings" :key="`warn-${idx}`">
              ⚠ {{ warning }}
            </li>
          </ul>
          <section v-if="analysisSummaryEntries.length" class="card summary-card headline-card">
            <header class="card-header card-header--tight">
              <div>
                <h3>数据简报</h3>
                <p class="panel-hint">基于当前单位与区间的自动摘要</p>
              </div>
              <button
                class="btn ghost xs"
                type="button"
                :disabled="!analysisSummaryText"
                @click="copyAnalysisSummary"
              >
                复制简报
              </button>
            </header>
            <ul class="headline-list">
              <li v-for="(line, idx) in analysisSummaryEntries" :key="`headline-${idx}`">
                {{ line }}
              </li>
            </ul>
            <div v-if="correlationMatrixState.ready" class="correlation-matrix-panel">
              <div class="correlation-matrix__header">
                <h4>相关矩阵</h4>
                <span class="panel-hint">r=1 表示完全正相关，-1 表示完全负相关</span>
              </div>
              <div class="correlation-matrix__table-wrapper">
                <table class="correlation-matrix__table">
                  <thead>
                    <tr>
                      <th>指标</th>
                      <th v-for="label in correlationMatrixState.headers" :key="`corr-col-${label}`">{{ label }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rowIndex) in correlationMatrixState.rows" :key="`corr-row-${row.label}`">
                      <th>{{ row.label }}</th>
                      <td
                        v-for="(cell, cellIndex) in row.cells"
                        :key="`corr-cell-${rowIndex}-${cellIndex}`"
                        :class="['corr-cell', `corr-cell--${cell.tone || 'neutral'}`]"
                      >
                        <span class="corr-cell__value">{{ cell.formatted }}</span>
                        <span v-if="cell.strength > 0" class="corr-cell__meter" aria-hidden="true">
                          <span
                            class="corr-cell__meter-bar"
                            :class="`corr-cell__meter-bar--${cell.tone || 'neutral'}`"
                            :style="{ width: `${Math.round(cell.strength * 100)}%` }"
                          ></span>
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p v-if="correlationMatrixState.notes.length" class="panel-hint warning correlation-matrix__notes">
                {{ correlationMatrixState.notes.join('；') }}
              </p>
            </div>
            <div v-if="summaryCopyMessage" class="summary-copy-hint">{{ summaryCopyMessage }}</div>
          </section>
          <div class="comparison-section" v-if="previewRows.length">
            <h3 class="comparison-title">同比比较</h3>
            <table class="result-table result-table--centered">
              <thead>
                <tr>
                  <th>指标</th>
                  <th>本期累计</th>
                  <th>同期累计</th>
                  <th>同比</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in previewRows"
                  :key="row.key"
                  :class="{ 'result-row--missing': row.missing }"
                >
                  <td>
                    <div class="metric-label">
                      <span>{{ row.label }}</span>
                      <span v-if="row.value_type === 'temperature'" class="tag tag--subtle">气温</span>
                      <span v-else-if="row.value_type === 'constant'" class="tag tag--subtle">常量</span>
                      <span v-if="row.missing" class="tag tag--subtle">缺失</span>
                    </div>
                  </td>
                  <td>
                    <div class="value-cell">
                      <span class="value-number">{{ formatNumber(resolveValue(row, 'current'), row.decimals || 2) }}</span>
                      <span v-if="row.unit" class="value-unit">{{ row.unit }}</span>
                    </div>
                  </td>
                  <td>
                    <div class="value-cell">
                      <span class="value-number">{{ formatNumber(resolveValue(row, 'peer'), row.decimals || 2) }}</span>
                      <span v-if="row.unit" class="value-unit">{{ row.unit }}</span>
                    </div>
                  </td>
                  <td
                    class="delta-cell"
                    :class="resolveDelta(row) === null ? '' : resolveDelta(row) >= 0 ? 'delta-up' : 'delta-down'"
                  >
                    {{ formatDelta(resolveDelta(row)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="comparison-section" v-if="ringComparisonEntries.length">
            <h3 class="comparison-title">环比比较</h3>
            <div class="panel-hint" v-if="ringPreviousRangeLabel">
              {{ ringCurrentRangeLabel }} vs {{ ringPreviousRangeLabel }}
            </div>
            <table class="result-table result-table--centered">
              <thead>
                <tr>
                  <th>指标</th>
                  <th>本期累计</th>
                  <th>上期累计</th>
                  <th>环比</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in ringComparisonEntries" :key="`ring-${entry.key}`">
                  <td>{{ entry.label }}</td>
                  <td>
                    <span class="value-number">{{ formatNumber(entry.current, entry.decimals || 2) }}</span>
                    <span v-if="entry.unit" class="value-unit">{{ entry.unit }}</span>
                  </td>
                  <td>
                    <span class="value-number">{{ formatNumber(entry.prev, entry.decimals || 2) }}</span>
                    <span v-if="entry.unit" class="value-unit">{{ entry.unit }}</span>
                  </td>
                  <td
                    class="delta-cell"
                    :class="entry.rate === null ? '' : entry.rate >= 0 ? 'delta-up' : 'delta-down'"
                  >
                    {{ entry.rate === null ? '—' : formatDelta(entry.rate) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else-if="ringComparisonNote" class="panel-hint warning">{{ ringComparisonNote }}</p>
          <div class="comparison-section" v-if="planComparisonEntries.length">
            <h3 class="comparison-title">计划比较</h3>
            <div class="panel-hint" v-if="planComparisonMonthLabel">
              计划月份：{{ planComparisonMonthLabel }}
              <span v-if="planComparisonPeriodText">（{{ planComparisonPeriodText }}）</span>
            </div>
            <table class="result-table result-table--centered">
              <thead>
                <tr>
                  <th>指标</th>
                  <th>截至本期末完成</th>
                  <th>月度计划</th>
                  <th>完成率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in planComparisonEntries" :key="`plan-${entry.key}`">
                  <td>{{ entry.label }}</td>
                  <td>
                    <span class="value-number">{{ formatNumber(entry.actualValue, entry.decimals) }}</span>
                    <span v-if="entry.unit" class="value-unit">{{ entry.unit }}</span>
                  </td>
                  <td>
                    <span class="value-number">{{ formatNumber(entry.planValue, entry.decimals) }}</span>
                    <span v-if="entry.unit" class="value-unit">{{ entry.unit }}</span>
                  </td>
                  <td>
                    <div class="plan-progress" :class="resolvePlanProgressClass(entry.completionRate)">
                      <div class="plan-progress__bar">
                        <span
                          class="plan-progress__bar-fill"
                          :style="{ width: formatPlanProgressWidth(entry.completionRate) }"
                        ></span>
                      </div>
                      <div class="plan-progress__meta">
                        <span class="plan-progress__value">
                          {{ entry.completionRate === null ? '—' : formatPercentValue(entry.completionRate) }}
                        </span>
                        <span class="plan-progress__status">{{ formatPlanStatusLabel(entry.completionRate) }}</span>
                      </div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else-if="planComparisonNote" class="panel-hint warning">{{ planComparisonNote }}</p>
        </div>
      </section>

      <section v-if="hasTimelineGrid" class="card elevated result-block">
        <header class="card-header">
          <div>
            <h3>区间明细（逐日）</h3>
          </div>
        </header>
        <div v-if="resultUnitKeys.length > 1" class="unit-switch unit-switch--inline unit-switch--grid">
          <span class="unit-switch__label">切换单位：</span>
          <div class="unit-switch__chips">
            <button
              v-for="unitKey in resultUnitKeys"
              :key="`timeline-grid-unit-${unitKey}`"
              type="button"
              class="unit-toggle"
              :class="{ active: activeUnit === unitKey }"
              @click="handleSwitchUnit(unitKey)"
            >
              {{ resolveUnitLabel(unitKey) }}
            </button>
          </div>
        </div>
        <div class="timeline-grid-wrapper">
          <RevoGrid
            class="timeline-grid"
            theme="material"
            :readonly="true"
            :columns="timelineGrid.columns"
            :source="timelineGrid.rows"
            :autoSizeColumn="true"
          />
        </div>
        <div class="timeline-chart-panel">
          <div v-if="resultUnitKeys.length > 1" class="unit-switch unit-switch--inline">
            <span class="unit-switch__label">切换单位：</span>
            <div class="unit-switch__chips">
              <button
                v-for="unitKey in resultUnitKeys"
                :key="`timeline-unit-${unitKey}`"
                type="button"
                class="unit-toggle"
                :class="{ active: activeUnit === unitKey }"
                @click="handleSwitchUnit(unitKey)"
              >
                {{ resolveUnitLabel(unitKey) }}
              </button>
            </div>
          </div>
          <div class="timeline-chart-toolbar" v-if="timelineMetrics.length">
            <div class="timeline-chart-toolbar__info">
              <h4>趋势洞察</h4>
              <span class="panel-hint">切换单位与指标，即时对比本期与同期</span>
            </div>
            <div class="timeline-chart-toolbar__metrics">
              <button
                v-for="metric in timelineMetrics"
                :key="`timeline-metric-${metric.key}`"
                type="button"
                class="chip chip--toggle"
                :class="{ active: isTimelineMetricActive(metric.key) }"
                @click="toggleTimelineMetric(metric.key)"
              >
                <span>{{ metric.label }}</span>
                <span v-if="metric.unit" class="chip-hint">（{{ metric.unit }}）</span>
              </button>
            </div>
          </div>
          <div v-if="timelineAxisHints" class="timeline-axis-hint">
            <span>左轴：{{ timelineAxisHints.left }}</span>
            <span v-if="timelineAxisHints.right.length">｜ 右轴：{{ timelineAxisHints.right.join('、') }}</span>
          </div>
          <TrendChart v-if="timelineChartOption" :option="timelineChartOption" height="420px" />
          <div v-else class="timeline-chart-empty">
            请选择至少一个包含逐日数据的指标以生成趋势图
          </div>
        </div>
      </section>
    </main>
    <transition name="fade">
      <div
        v-if="aiSettingsDialogVisible"
        class="ai-settings-dialog__backdrop"
        role="dialog"
        aria-modal="true"
        aria-label="智能体设定"
      >
        <div class="ai-settings-dialog__panel">
          <header class="ai-settings-dialog__header">
            <div>
              <h4>智能体设定</h4>
              <p>配置智能报告使用的 API Key 与模型。</p>
            </div>
            <button
              type="button"
              class="ai-settings-dialog__close"
              :disabled="aiSettingsSaving"
              aria-label="关闭智能体设定"
              @click="closeAiSettingsDialog"
            >
              ×
            </button>
          </header>
          <div class="ai-settings-dialog__body">
            <div v-if="aiSettingsLoading" class="ai-settings-dialog__loading">配置读取中，请稍候…</div>
            <template v-else>
              <label class="ai-settings-dialog__field">
                <span>API Key</span>
                <input
                  type="text"
                  v-model="aiSettingsForm.apiKey"
                  :disabled="aiSettingsSaving"
                  autocomplete="off"
                />
              </label>
              <label class="ai-settings-dialog__field">
                <span>模型</span>
                <input
                  type="text"
                  v-model="aiSettingsForm.model"
                  :disabled="aiSettingsSaving"
                  autocomplete="off"
                />
              </label>
              <label class="ai-settings-dialog__field">
                <span>智能体提示词（instruction）</span>
                <textarea
                  rows="5"
                  v-model="aiSettingsForm.instruction"
                  :disabled="aiSettingsSaving"
                  placeholder="可填写多条指引，用于追加到提示词末尾。"
                ></textarea>
              </label>
              <label class="ai-settings-dialog__toggle">
                <input
                  type="checkbox"
                  v-model="aiSettingsForm.validationEnabled"
                  :disabled="aiSettingsSaving"
                />
                <span>启用检查核实（第 4 阶段自检）</span>
              </label>
              <label class="ai-settings-dialog__toggle">
                <input
                  type="checkbox"
                  v-model="aiSettingsForm.allowNonAdmin"
                  :disabled="aiSettingsSaving"
                />
                <span>允许非 Global_admin 启用智能报告</span>
              </label>
              <p class="ai-settings-dialog__hint">保存后将同步更新 backend_data/api_key.json。</p>
            </template>
            <p v-if="aiSettingsError" class="ai-settings-dialog__alert ai-settings-dialog__alert--error">
              {{ aiSettingsError }}
            </p>
            <p
              v-else-if="aiSettingsSuccess"
              class="ai-settings-dialog__alert ai-settings-dialog__alert--success"
            >
              {{ aiSettingsSuccess }}
            </p>
          </div>
          <footer class="ai-settings-dialog__actions">
            <button
              type="button"
              class="btn ghost"
              :disabled="aiSettingsSaving"
              @click="closeAiSettingsDialog"
            >
              取消
            </button>
            <button
              type="button"
              class="btn primary"
              :disabled="aiSettingsLoading || aiSettingsSaving"
              @click="handleAiSettingsSave"
            >
              {{ aiSettingsSaving ? '保存中…' : '保存' }}
            </button>
          </footer>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import RevoGrid from '@revolist/vue3-datagrid'
import * as XLSX from 'xlsx'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { getProjectNameById } from '../composables/useProjects'
import {
  getDataAnalysisSchema,
  getDashboardBizDate,
  runDataAnalysis,
  getDataAnalysisAiReport,
  getAiSettings,
  updateAiSettings,
} from '../services/api'
import { useAuthStore } from '../store/auth'

const TrendChart = defineComponent({
  name: 'TrendChart',
  props: {
    option: { type: Object, required: true },
    height: { type: [Number, String], default: '320px' },
    autoresize: { type: Boolean, default: true },
  },
  setup(props) {
    const container = ref(null)
    const chart = shallowRef(null)
    const latestOption = shallowRef(null)
    const styleHeight = computed(() =>
      typeof props.height === 'number' ? `${props.height}px` : props.height || '320px',
    )

    const dispose = () => {
      if (chart.value) {
        chart.value.dispose()
        chart.value = null
      }
    }

    const ensureChart = () => {
      if (!container.value) return
      if (!window.echarts) {
        return
      }
      if (!chart.value) {
        chart.value = window.echarts.init(container.value)
      }
      if (latestOption.value) {
        chart.value.setOption(latestOption.value, { notMerge: true, lazyUpdate: false })
      }
    }

    const handleResize = () => {
      if (chart.value) {
        chart.value.resize()
      }
    }

    onMounted(() => {
      ensureChart()
      if (props.autoresize) {
        window.addEventListener('resize', handleResize)
      }
    })

    onBeforeUnmount(() => {
      if (props.autoresize) {
        window.removeEventListener('resize', handleResize)
      }
      dispose()
    })

    watch(
      () => props.option,
      (option) => {
        latestOption.value = option || null
        ensureChart()
      },
      { deep: true, immediate: true },
    )

    return () =>
      h('div', {
        ref: container,
        class: 'timeline-chart',
        style: { height: styleHeight.value },
      })
  },
})

const route = useRoute()
const auth = useAuthStore()
const projectKey = computed(() => String(route.params.projectKey ?? ''))
const pageKey = computed(() => String(route.params.pageKey ?? ''))
const pageConfig = computed(() => (typeof route.query.config === 'string' ? route.query.config : ''))
const pageDisplayName = computed(() => {
  const raw = typeof route.query.pageName === 'string' ? route.query.pageName.trim() : ''
  return raw || '数据分析页面'
})
const projectName = computed(() => getProjectNameById(projectKey.value) ?? projectKey.value)
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
  { label: pageDisplayName.value, to: null },
])

const loading = ref(false)
const errorMessage = ref('')
const schema = ref(null)
const isGlobalAdmin = computed(() => (auth.user?.group || '').trim() === 'Global_admin')
const canConfigureAiSettings = computed(() => isGlobalAdmin.value)
const aiSchemaFlags = computed(() => schema.value?.ai_report_flags || {})
const allowNonAdminAiReport = computed(() => Boolean(aiSchemaFlags.value.allow_non_admin))
const aiSettingsDialogVisible = ref(false)
const aiSettingsLoading = ref(false)
const aiSettingsSaving = ref(false)
const aiSettingsError = ref('')
const aiSettingsSuccess = ref('')
const aiSettingsForm = reactive({
  apiKey: '',
  model: '',
  instruction: '',
  validationEnabled: true,
  allowNonAdmin: false,
})

function applyAiSettingsPayload(payload) {
  aiSettingsForm.apiKey = payload?.api_key ?? ''
  aiSettingsForm.model = payload?.model ?? ''
  aiSettingsForm.instruction = payload?.instruction ?? ''
  aiSettingsForm.validationEnabled =
    payload?.enable_validation !== undefined ? Boolean(payload.enable_validation) : true
  aiSettingsForm.allowNonAdmin =
    payload?.allow_non_admin_report !== undefined
      ? Boolean(payload.allow_non_admin_report)
      : false
}

function closeAiSettingsDialog() {
  if (aiSettingsSaving.value) return
  aiSettingsDialogVisible.value = false
}

async function openAiSettingsDialog() {
  if (!canConfigureAiSettings.value || !projectKey.value) return
  aiSettingsDialogVisible.value = true
  aiSettingsLoading.value = true
  aiSettingsError.value = ''
  aiSettingsSuccess.value = ''
  try {
    const payload = await getAiSettings(projectKey.value)
    applyAiSettingsPayload(payload)
  } catch (err) {
    aiSettingsError.value = err instanceof Error ? err.message : String(err)
  } finally {
    aiSettingsLoading.value = false
  }
}

async function handleAiSettingsSave() {
  if (!canConfigureAiSettings.value || !projectKey.value) return
  if (aiSettingsLoading.value || aiSettingsSaving.value) return
  aiSettingsSaving.value = true
  aiSettingsError.value = ''
  aiSettingsSuccess.value = ''
  try {
    const payload = await updateAiSettings(projectKey.value, {
      api_key: aiSettingsForm.apiKey || '',
      model: aiSettingsForm.model || '',
      instruction: aiSettingsForm.instruction || '',
      enable_validation: Boolean(aiSettingsForm.validationEnabled),
      allow_non_admin_report: Boolean(aiSettingsForm.allowNonAdmin),
    })
    applyAiSettingsPayload(payload)
    aiSettingsSuccess.value = '智能体配置已保存'
  } catch (err) {
    aiSettingsError.value = err instanceof Error ? err.message : String(err)
  } finally {
    aiSettingsSaving.value = false
  }
}

function resolveUnitOptions(payload) {
  if (!payload) return []
  const dict = payload.unit_dict || {}
  const displayOpts = Array.isArray(payload.display_unit_options) ? payload.display_unit_options : null
  if (displayOpts && displayOpts.length) return displayOpts
  const displayKeys = Array.isArray(payload.display_unit_keys) ? payload.display_unit_keys : null
  if (displayKeys && displayKeys.length) {
    return displayKeys
      .map((key) => ({
        value: key,
        label: dict?.[key] || key,
      }))
      .filter((item) => item.value)
  }
  if (Array.isArray(payload.unit_options) && payload.unit_options.length) {
    return payload.unit_options
  }
  return Object.entries(dict).map(([value, label]) => ({ value, label }))
}

function normalizeMetricOptions(options) {
  if (!Array.isArray(options)) return []
  return options
    .map((item) => ({
      value: item?.value ?? '',
      label: item?.label ?? item?.value ?? '',
    }))
    .filter((item) => item.value)
}

function resolveMetricGroups(payload) {
  const groups = []
  if (!payload) return groups
  const provided = Array.isArray(payload.metric_groups) ? payload.metric_groups : []
  for (const group of provided) {
    if (!group || !group.options) continue
    const normalized = normalizeMetricOptions(group.options)
    if (!normalized.length) continue
    groups.push({
      key: group.key || group.label || 'metrics',
      label: group.label || group.key || '指标',
      options: normalized,
    })
  }
  if (!groups.length) {
    const fallback = normalizeMetricOptions(payload.metric_options || [])
    if (fallback.length) {
      groups.push({
        key: 'all',
        label: '全部指标',
        options: fallback,
      })
    }
  }
  return groups
}

const unitOptions = computed(() => resolveUnitOptions(schema.value))
const metricGroups = computed(() => resolveMetricGroups(schema.value))
const unitDict = computed(() => schema.value?.unit_dict || {})
const metricDict = computed(() => schema.value?.metric_dict || {})
const metricDecimalsMap = computed(() => schema.value?.metric_decimals || {})
const viewMapping = computed(() => schema.value?.view_mapping || {})
const TEMPERATURE_KEYWORDS = ['气温', '温度']
const TEMPERATURE_PRIORITY_LABELS = ['平均气温', '平均温度']

function getTemperatureWeight(label = '') {
  if (typeof label !== 'string' || !label) return 0
  const normalized = label.trim()
  const hasKeyword = TEMPERATURE_KEYWORDS.some((keyword) => normalized.includes(keyword))
  if (!hasKeyword) return 0
  if (TEMPERATURE_PRIORITY_LABELS.some((keyword) => normalized.includes(keyword))) return 4
  if (normalized.includes('平均')) return 3
  return 1
}

function findDefaultTemperatureKeys(payload) {
  if (!payload) return []
  const result = []
  let order = 0
  const visit = (options = [], bonus = 0) => {
    if (!Array.isArray(options)) return
    options.forEach((option) => {
      const value = option?.value
      if (!value) return
      const label = option?.label ?? option?.name ?? ''
      const weight = getTemperatureWeight(label)
      if (!weight) return
      result.push({
        value,
        weight: weight + bonus,
        order: order++,
      })
    })
  }
  const groups = Array.isArray(payload?.metric_groups) ? payload.metric_groups : []
  groups
    .filter((group) => group?.options && group.key === 'temperature')
    .forEach((group) => visit(group.options, 2))
  groups
    .filter((group) => group?.options && group.key !== 'temperature')
    .forEach((group) => visit(group.options))
  if (!result.length) {
    visit(payload?.metric_options || [])
  }
  if (!result.length && payload?.metric_dict) {
    Object.entries(payload.metric_dict).forEach(([value, label]) => {
      const weight = getTemperatureWeight(label)
      if (weight) {
        result.push({
          value,
          weight,
          order: order++,
        })
      }
    })
  }
  return result
    .sort((a, b) => {
      if (b.weight !== a.weight) return b.weight - a.weight
      return a.order - b.order
    })
    .map((item) => item.value)
}

const temperatureCandidates = computed(() => findDefaultTemperatureKeys(schema.value))
const temperatureMetricKey = computed(() => temperatureCandidates.value[0] || null)

const selectedUnits = ref([])
const activeUnit = ref('')
const unitResults = ref({})
const selectedMetrics = ref(new Set())
const analysisMode = ref('daily')
const MIN_ANALYSIS_DATE = '2025-11-01'
const analysisModes = computed(() => {
  const modes = Array.isArray(schema.value?.analysis_modes) ? schema.value.analysis_modes : []
  if (modes.length) return modes
  return [
    { value: 'daily', label: '单日数据' },
    { value: 'range', label: '累计数据' },
  ]
})
const hasConstantMetrics = computed(() =>
  metricGroups.value.some((group) => group.key === 'constant'),
)
const hasTimelineGrid = computed(
  () => analysisMode.value === 'range' && timelineGrid.value.rows.length > 0,
)

const defaultBizDate = ref('')
const startDate = ref('')
const endDate = ref('')
const previewRows = ref([])
const infoBanner = ref('')
const formError = ref('')
const queryWarnings = ref([])
const lastQueryMeta = ref(null)
const queryLoading = ref(false)
const aiReportEnabled = ref(false)
const aiReportJobId = ref('')
const aiReportStatus = ref('idle')
const aiReportContent = ref('')
const aiReportStatusMessage = ref('')
const aiReportStage = ref('')
const aiFeatureAccessible = computed(() => isGlobalAdmin.value || allowNonAdminAiReport.value)
watch(
  () => aiFeatureAccessible.value,
  (allowed) => {
    if (!allowed && aiReportEnabled.value) {
      aiReportEnabled.value = false
    }
  },
  { immediate: true },
)

const AI_REPORT_STAGE_STEPS = [
  { key: 'insight', order: 1, label: '洞察分析' },
  { key: 'layout', order: 2, label: '结构规划' },
  { key: 'content', order: 3, label: '内容撰写' },
  { key: 'review', order: 4, label: '检查核实' },
]
const AI_REPORT_STAGE_TOTAL = AI_REPORT_STAGE_STEPS.length
const AI_REPORT_STAGE_LOOKUP = AI_REPORT_STAGE_STEPS.reduce((acc, step) => {
  acc[step.key] = step
  return acc
}, {})

function formatAiReportProgress(stageKey) {
  if (stageKey === 'ready') {
    return `（阶段 ${AI_REPORT_STAGE_TOTAL}/${AI_REPORT_STAGE_TOTAL}：完成）`
  }
  if (stageKey === 'failed') {
    return `（任务失败）`
  }
  if (stageKey === 'pending') {
    return `（等待后台任务启动）`
  }
  const step = AI_REPORT_STAGE_LOOKUP[stageKey]
  if (step) {
    return `（阶段 ${step.order}/${AI_REPORT_STAGE_TOTAL}：${step.label}）`
  }
  return `（进行中…）`
}

function buildAiRunningMessage(stageKey) {
  return `智能报告生成中…${formatAiReportProgress(stageKey)}`
}

function updateAiReportStage(stageKey) {
  aiReportStage.value = stageKey || ''
}

function setAiReportRunningMessage(stageKey) {
  const key = stageKey || aiReportStage.value || 'pending'
  aiReportStatusMessage.value = buildAiRunningMessage(key)
}
const timelineGrid = ref({ columns: [], rows: [] })
const activeTimelineMetricKeys = ref([])

let aiReportPollTimer = null

const timelineMetrics = computed(() =>
  previewRows.value.filter((row) => Array.isArray(row.timeline) && row.timeline.length),
)

const activeTimelineMetrics = computed(() => {
  const metricMap = new Map()
  timelineMetrics.value.forEach((metric) => {
    metricMap.set(metric.key, metric)
  })
  return activeTimelineMetricKeys.value.map((key) => metricMap.get(key)).filter(Boolean)
})

// 所有被选中（勾选）的指标中，具备 timeline 的集合，用于统计/简报
const selectedTimelineMetrics = computed(() => {
  const selectedKeys = new Set(selectedMetrics.value || [])
  return timelineMetrics.value.filter(
    (metric) => metric.key && selectedKeys.has(metric.key) && Array.isArray(metric.timeline) && metric.timeline.length,
  )
})

function buildTimelineValueMap(metric) {
  const map = new Map()
  if (!metric || !Array.isArray(metric.timeline)) return map
  metric.timeline.forEach((entry) => {
    if (!entry?.date) return
    const value = Number(entry.current)
    if (!Number.isFinite(value)) return
    map.set(entry.date, value)
  })
  return map
}

function computeCorrelationFromMaps(mapA, mapB) {
  if (!mapA || !mapB) return null
  const alignedA = []
  const alignedB = []
  mapA.forEach((value, date) => {
    const other = mapB.get(date)
    if (!Number.isFinite(other)) return
    alignedA.push(value)
    alignedB.push(other)
  })
  if (alignedA.length < 2 || alignedB.length < 2) return null
  return computeCorrelation(alignedA, alignedB)
}

const correlationMatrixState = computed(() => {
  const state = {
    ready: false,
    headers: [],
    rows: [],
    notes: [],
    insufficientMetrics: [],
  }
  const metrics = selectedTimelineMetrics.value
  if (!metrics.length) return state
  const prepared = []
  metrics.forEach((metric) => {
    const valueMap = buildTimelineValueMap(metric)
    if (valueMap.size >= 2) {
      prepared.push({ key: metric.key, label: metric.label, valueMap })
    } else {
      state.insufficientMetrics.push(metric.label)
    }
  })
  if (prepared.length < 2) return state
  const headers = prepared.map((metric) => metric.label)
  const pairCache = new Map()
  const missingPairs = new Set()
  const rows = prepared.map((metricA, rowIndex) => ({
    label: metricA.label,
    cells: prepared.map((metricB, columnIndex) => {
      if (rowIndex === columnIndex) {
        return { value: 1, formatted: '1.00', tone: 'neutral' }
      }
      const cacheKey =
        rowIndex < columnIndex ? `${metricA.key}__${metricB.key}` : `${metricB.key}__${metricA.key}`
      if (!pairCache.has(cacheKey)) {
        const corr = computeCorrelationFromMaps(metricA.valueMap, metricB.valueMap)
        if (corr === null) {
          missingPairs.add(`${metricA.label} × ${metricB.label}`)
        }
        pairCache.set(cacheKey, corr)
      }
      const value = pairCache.get(cacheKey)
      return {
        value,
        formatted: typeof value === 'number' ? value.toFixed(2) : '—',
        tone:
          typeof value === 'number'
            ? value > 0
              ? 'positive'
              : value < 0
                ? 'negative'
                : 'neutral'
            : 'muted',
        strength: typeof value === 'number' ? Math.min(Math.abs(value), 1) : 0,
      }
    }),
  }))
  state.ready = true
  state.headers = headers
  state.rows = rows
  state.notes = []
  if (state.insufficientMetrics.length) {
    state.notes.push(`以下指标逐日样本不足：${state.insufficientMetrics.slice(0, 4).join('、')}`)
  }
  if (missingPairs.size) {
    state.notes.push(`部分组合缺少共同日期：${Array.from(missingPairs).slice(0, 4).join('、')}`)
  }
  return state
})

const timelineCategories = computed(() =>
  timelineGrid.value.rows
    .filter((row) => row?.date && row.date !== '总计')
    .map((row) => row.date),
)

watch(
  timelineMetrics,
  (metrics) => {
    const available = metrics.map((item) => item.key).filter(Boolean)
    if (!available.length) {
      activeTimelineMetricKeys.value = []
      return
    }
    const retained = activeTimelineMetricKeys.value.filter((key) => available.includes(key))
    const ordered = reorderMetricKeys(retained, temperatureMetricKey.value, available)
    if (ordered.length) {
      activeTimelineMetricKeys.value = ordered
      return
    }
    if (temperatureMetricKey.value) {
      const other = available.find((key) => key !== temperatureMetricKey.value)
      activeTimelineMetricKeys.value = other ? [other, temperatureMetricKey.value] : [temperatureMetricKey.value]
      return
    }
    activeTimelineMetricKeys.value = [available[0]]
  },
  { immediate: true },
)

const timelinePalette = [
  { current: '#2563eb', peer: '#93c5fd' },
  { current: '#f97316', peer: '#fdba74' },
  { current: '#0ea5e9', peer: '#7dd3fc' },
  { current: '#a855f7', peer: '#d8b4fe' },
  { current: '#22c55e', peer: '#86efac' },
]

function assignAxisSlots(metrics, temperatureKey) {
  if (!Array.isArray(metrics) || !metrics.length) return []
  const isTempMetric = (metric) => {
    if (!metric) return false
    if (temperatureKey && metric.key === temperatureKey) return true
    return isTemperatureMetric(metric)
  }
  const hasTemperature = metrics.length >= 2 && metrics.some((metric) => isTempMetric(metric))
  return metrics.map((metric, index) => {
    const slot = {
      key: metric?.key || `__timeline_metric_${index}`,
      axis: 'left',
    }
    if (metrics.length >= 2) {
      if (hasTemperature && isTempMetric(metric)) {
        slot.axis = 'right'
      } else if (!hasTemperature && index >= 1) {
        slot.axis = 'right'
      }
    }
    return slot
  })
}

const timelineChartOption = computed(() => {
  if (!hasTimelineGrid.value || !timelineCategories.value.length) return null
  const activeMetrics = activeTimelineMetrics.value
  if (!activeMetrics.length) return null

  const categories = timelineCategories.value
  const series = []
  const legend = []
  const seriesMeta = {}
  const axisSlots = assignAxisSlots(activeMetrics, temperatureMetricKey.value)
  const hasRightAxis = axisSlots.some((slot) => slot.axis === 'right')

  const makeAxisBase = () => ({
    type: 'value',
    axisLabel: { color: '#475569' },
    splitLine: { lineStyle: { type: 'dashed', color: 'rgba(148, 163, 184, 0.35)' } },
  })

  const yAxis = hasRightAxis
    ? [
        makeAxisBase(),
        {
          ...makeAxisBase(),
          position: 'right',
          axisLabel: { color: '#475569' },
        },
      ]
    : makeAxisBase()

  activeMetrics.forEach((metric, index) => {
    const palette = timelinePalette[index % timelinePalette.length]
    const decimals = metric.decimals ?? 2
    const timelineMap = {}
    ;(metric.timeline || []).forEach((entry) => {
      if (entry?.date) {
        timelineMap[entry.date] = {
          current: normalizeChartValue(entry.current, decimals),
          peer: normalizeChartValue(entry.peer, decimals),
        }
      }
    })
    const currentName = `${metric.label}（本期）`
    const peerName = `${metric.label}（同期）`
    const currentData = categories.map((date) => timelineMap[date]?.current ?? null)
    const peerData = categories.map((date) => timelineMap[date]?.peer ?? null)
    const axisSlot = axisSlots[index] || { axis: 'left' }
    const yAxisIndex = hasRightAxis && axisSlot.axis === 'right' ? 1 : 0

    series.push({
      name: currentName,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      showSymbol: categories.length <= 31,
      data: currentData,
      yAxisIndex,
      lineStyle: { width: 3, color: palette.current },
      areaStyle: {
        opacity: 0.18,
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: withAlpha(palette.current, 0.45) },
            { offset: 1, color: 'rgba(255,255,255,0)' },
          ],
        },
      },
      emphasis: { focus: 'series' },
    })
    series.push({
      name: peerName,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      showSymbol: categories.length <= 31,
      data: peerData,
      yAxisIndex,
      lineStyle: { width: 2, color: palette.peer, type: 'dashed' },
      emphasis: { focus: 'series' },
    })
    legend.push(currentName, peerName)
    seriesMeta[currentName] = {
      unit: metric.unit || '',
      type: 'current',
      label: metric.label,
      getEntry: (date) => timelineMap[date],
    }
    seriesMeta[peerName] = {
      unit: metric.unit || '',
      type: 'peer',
      label: metric.label,
      getEntry: (date) => timelineMap[date],
    }
  })

  const tooltipFormatter = (params = []) => {
    if (!Array.isArray(params) || !params.length) return ''
    const dateLabel = params[0].axisValue ?? ''
    const lines = [`<div class="chart-tooltip__title">${dateLabel}</div>`]
    params.forEach((item) => {
      const meta = seriesMeta[item.seriesName] || {}
      const unit = meta.unit ? ` ${meta.unit}` : ''
      const value =
        item.data === null || item.data === undefined
          ? '—'
          : formatNumber(item.data, 2)
      const delta = meta.type === 'current' ? formatChartDelta(meta.getEntry?.(dateLabel)) : ''
      const colorChip =
        typeof item.color === 'string'
          ? item.color
          : Array.isArray(item.color)
            ? item.color[0]
            : '#2563eb'
      lines.push(
        `<div class="chart-tooltip__item"><span class="chart-tooltip__dot" style="background:${colorChip}"></span>${item.seriesName}：${value}${unit}${delta}</div>`,
      )
    })
    return lines.join('')
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(15, 23, 42, 0.94)',
      borderWidth: 0,
      textStyle: { color: '#f8fafc' },
      formatter: tooltipFormatter,
      extraCssText: 'box-shadow: 0 10px 40px rgba(15,23,42,0.35); border-radius: 12px; padding: 12px 16px;',
    },
    legend: {
      type: 'scroll',
      top: 0,
      icon: 'roundRect',
      inactiveColor: '#cbd5f5',
      data: legend,
    },
    grid: { left: 48, right: 24, top: 70, bottom: 90 },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', height: 18, bottom: 30, borderColor: 'transparent', backgroundColor: 'rgba(148,163,184,0.15)' },
    ],
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: categories,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.5)' } },
      axisLabel: { color: '#475569' },
      axisPointer: {
        label: {
          show: true,
          backgroundColor: '#0f172a',
          color: '#f8fafc',
        },
      },
    },
    yAxis,
    series,
  }
})

function toggleTimelineMetric(metricKey) {
  const list = [...activeTimelineMetricKeys.value]
  const index = list.indexOf(metricKey)
  if (index >= 0) {
    list.splice(index, 1)
  } else {
    list.push(metricKey)
  }
  activeTimelineMetricKeys.value = list
}

function isTimelineMetricActive(metricKey) {
  return activeTimelineMetricKeys.value.includes(metricKey)
}

const timelineAxisHints = computed(() => {
  const metrics = activeTimelineMetrics.value
  if (!metrics.length) return null
  const axisSlots = assignAxisSlots(metrics, temperatureMetricKey.value)
  const hasRightAxis = axisSlots.some((slot) => slot.axis === 'right')
  if (!hasRightAxis) return null
  const leftLabels = []
  const rightLabels = []
  axisSlots.forEach((slot, index) => {
    const label = metrics[index]?.label || ''
    if (!label) return
    if (slot.axis === 'right') {
      rightLabels.push(label)
    } else {
      leftLabels.push(label)
    }
  })
  if (!leftLabels.length && !rightLabels.length) return null
  return { left: leftLabels.join('、'), right: rightLabels }
})

const metricSnapshot = computed(() =>
  previewRows.value.map((row) => ({
    label: row.label,
    unit: row.unit || '',
    value: resolveValue(row, 'current'),
    peer: resolveValue(row, 'peer'),
    delta: resolveDelta(row),
    missing: !!row.missing,
  })),
)

const summaryOverallLine = computed(() => {
  if (!metricSnapshot.value.length) return ''
  const withValue = metricSnapshot.value.filter((item) => Number.isFinite(item.value))
  const withDelta = metricSnapshot.value.filter((item) => Number.isFinite(item.delta))
  if (!withValue.length) {
    return `当前共 ${metricSnapshot.value.length} 项指标，暂无可用数据。`
  }
  const upCount = withDelta.filter((item) => item.delta >= 0).length
  const downCount = withDelta.filter((item) => item.delta < 0).length
  const missingCount = Math.max(metricSnapshot.value.length - withValue.length, 0)
  const baseText = `共 ${withValue.length} 项指标`
  const deltaText = withDelta.length ? `同比上升 ${upCount} 项、下降 ${downCount} 项` : '暂无同比参考'
  const missingText = missingCount ? `；另有 ${missingCount} 项暂缺数据` : ''
  return `${baseText}，${deltaText}${missingText}。`
})

function formatMetricPair(metric) {
  return `${metric.label} ${formatNumber(metric.value, 2)}${metric.unit || ''}（同比 ${formatDelta(metric.delta)}）`
}

const summaryTimelineInsight = computed(() => {
  if (!hasTimelineGrid.value || !timelineCategories.value.length) return ''
  const metrics = selectedTimelineMetrics.value.length
    ? selectedTimelineMetrics.value
    : activeTimelineMetrics.value
  if (!metrics.length) return ''
  const phrases = metrics
    .map((metric) => {
      if (!metric || !Array.isArray(metric.timeline)) return ''
      const currentValues = []
      const peerValues = []
      metric.timeline.forEach((entry) => {
        if (Number.isFinite(entry?.current)) currentValues.push(Number(entry.current))
        if (Number.isFinite(entry?.peer)) peerValues.push(Number(entry.peer))
      })
      const currentAvg = computeAverage(currentValues)
      if (!Number.isFinite(currentAvg)) return ''
      const peerAvg = computeAverage(peerValues)
      const unit = metric.unit ? ` ${metric.unit}` : ''
      const decimals = Number.isInteger(metric.decimals) ? metric.decimals : 2
      let comparisonText = '较同期暂无数据'
      if (Number.isFinite(peerAvg)) {
        const denominator = Math.abs(peerAvg) > 1e-6 ? Math.abs(peerAvg) : null
        if (denominator) {
          const pct = ((currentAvg - peerAvg) / denominator) * 100
          comparisonText = `较同期${formatDelta(pct)}`
        } else {
          const diff = currentAvg - peerAvg
          comparisonText = `较同期差值 ${formatNumber(diff, decimals)}${unit}`
        }
      }
      return `${metric.label} 区间均值 ${formatNumber(currentAvg, decimals)}${unit}（${comparisonText}）`
    })
    .filter(Boolean)
  if (!phrases.length) return ''
  return `区间趋势：${phrases.join('；')}。`
})

const summaryWarningLine = computed(() => {
  const warnings = [...(queryWarnings.value || [])]
  const missingLabels = metricSnapshot.value.filter((item) => item.missing).map((item) => item.label)
  if (missingLabels.length) {
    warnings.push(`以下指标暂缺数据：${missingLabels.slice(0, 3).join('、')}`)
  }
  return warnings.join('；')
})

function computeCorrelation(valuesA = [], valuesB = []) {
  if (!Array.isArray(valuesA) || !Array.isArray(valuesB)) return null
  const n = Math.min(valuesA.length, valuesB.length)
  if (!n) return null
  let sumA = 0
  let sumB = 0
  let sumASq = 0
  let sumBSq = 0
  let sumAB = 0
  let count = 0
  for (let i = 0; i < n; i += 1) {
    const a = Number(valuesA[i])
    const b = Number(valuesB[i])
    if (!Number.isFinite(a) || !Number.isFinite(b)) continue
    sumA += a
    sumB += b
    sumASq += a * a
    sumBSq += b * b
    sumAB += a * b
    count += 1
  }
  if (count < 2) return null
  const numerator = count * sumAB - sumA * sumB
  const denominator = Math.sqrt((count * sumASq - sumA * sumA) * (count * sumBSq - sumB * sumB))
  if (!Number.isFinite(denominator) || denominator === 0) return null
  const result = numerator / denominator
  return Number.isFinite(result) ? result : null
}

function computeAverage(values = []) {
  const valid = Array.isArray(values) ? values.filter((value) => Number.isFinite(value)) : []
  if (!valid.length) return null
  const sum = valid.reduce((total, value) => total + Number(value), 0)
  return sum / valid.length
}

const summaryCorrelationLines = computed(() => {
  const state = correlationMatrixState.value
  if (state.ready) {
    if (!state.notes.length) {
      return ['【相关性】已生成相关矩阵（r=1 表示完全正相关，-1 表示完全负相关）。']
    }
    return [
      `【相关性】已生成相关矩阵（r=1 表示完全正相关，-1 表示完全负相关），${state.notes.join('；')}`,
    ]
  }
  const metrics = selectedTimelineMetrics.value
  if (!metrics.length) {
    return ['【相关性】请选择至少两个指标（且需包含逐日数据）以生成相关矩阵。']
  }
  const availableCount = metrics.length - (state.insufficientMetrics?.length || 0)
  if (availableCount < 2) {
    return ['【相关性】当前勾选指标的逐日样本不足，暂无法生成相关矩阵。']
  }
  return []
})

const ringComparisonEntries = computed(() => {
  const unitKey = activeUnit.value
  const unitResult = unitResults.value[unitKey]
  if (!unitResult?.ringCompare?.range || !unitResult.ringCompare.prevTotals) return []
  return previewRows.value
    .map((row) => {
      const current = resolveTotalCurrentFromRow(row)
      const prev = unitResult.ringCompare.prevTotals[row.key]
      if (!Number.isFinite(current) || !Number.isFinite(prev)) return null
      const rate = computeRelativeRate(current, prev)
      return {
        key: row.key,
        label: row.label,
        unit: row.unit || '',
        decimals: row.decimals ?? 2,
        current,
        prev,
        rate,
      }
    })
    .filter(Boolean)
})

const ringComparisonNote = computed(() => {
  const unitKey = activeUnit.value
  const unitResult = unitResults.value[unitKey]
  if (!unitResult?.ringCompare) return ''
  if (unitResult.ringCompare.range && unitResult.ringCompare.prevTotals) {
    return ringComparisonEntries.value.length ? '' : '当前指标无可用环比数据'
  }
  return unitResult.ringCompare.note || ''
})

const ringCurrentRangeLabel = computed(() => {
  const meta = lastQueryMeta.value
  if (!meta?.start_date || !meta?.end_date) return ''
  return meta.start_date === meta.end_date ? meta.start_date : `${meta.start_date} ~ ${meta.end_date}`
})

const ringPreviousRangeLabel = computed(() => {
  const unitKey = activeUnit.value
  const range = unitResults.value[unitKey]?.ringCompare?.range
  if (!range?.start || !range?.end) return ''
  return range.start === range.end ? range.start : `${range.start} ~ ${range.end}`
})

const ringSummaryLines = computed(() => {
  if (!ringComparisonEntries.value.length) return []
  const rangeNote = ringPreviousRangeLabel.value ? `（上期：${ringPreviousRangeLabel.value}）` : ''
  const phrases = ringComparisonEntries.value.slice(0, 3).map((entry) => {
    const unitText = entry.unit ? entry.unit : ''
    const prevText = formatNumber(entry.prev, entry.decimals || 2)
    const rateText = entry.rate === null ? '—' : formatDelta(entry.rate)
    return `${entry.label} 上期 ${prevText}${unitText}，环比 ${rateText}`
  })
  const suffix = ringComparisonEntries.value.length > 3 ? '（其余略）' : ''
  return phrases.length ? [`【环比】${phrases.join('；')}${suffix}${rangeNote}`] : []
})

const planComparisonPayload = computed(() => {
  const unitKey = activeUnit.value
  return unitResults.value[unitKey]?.planComparison || null
})

const planComparisonEntries = computed(() => {
  const unitKey = activeUnit.value
  const unitResult = unitResults.value[unitKey]
  if (!unitResult) return []
  return mapPlanComparisonEntries(unitResult.planComparison, unitResult.rows)
})

const planComparisonNote = computed(() => {
  const unitKey = activeUnit.value
  return unitResults.value[unitKey]?.planComparisonNote || ''
})

const planComparisonMonthLabel = computed(() => {
  const payload = planComparisonPayload.value
  if (!payload) return ''
  if (payload.month_label) return payload.month_label
  if (payload.period_start && payload.period_start.length >= 7) {
    return payload.period_start.slice(0, 7)
  }
  return ''
})

const planComparisonPeriodText = computed(() => {
  const payload = planComparisonPayload.value
  if (!payload?.period_start || !payload?.period_end) return ''
  if (payload.period_start === payload.period_end) return payload.period_start
  return `${payload.period_start} ~ ${payload.period_end}`
})

function classifyPlanCompletion(rate) {
  if (!Number.isFinite(rate)) return 'neutral'
  if (Math.abs(rate - 100) < 1e-6) return 'ontarget'
  return rate > 100 ? 'ahead' : 'lag'
}

function formatPlanProgressWidth(rate) {
  if (!Number.isFinite(rate)) return '0%'
  const clamped = Math.max(0, Math.min(rate, 130))
  return `${clamped}%`
}

function formatPlanStatusLabel(rate) {
  const status = classifyPlanCompletion(rate)
  if (status === 'ahead') return '超出计划'
  if (status === 'ontarget') return '达成计划'
  if (status === 'lag') return '落后计划'
  return '无数据'
}

function resolvePlanProgressClass(rate) {
  return `plan-progress--${classifyPlanCompletion(rate)}`
}

const yoySummaryLines = computed(() => {
  if (!previewRows.value.length) return []
  const entries = previewRows.value
    .map((row) => {
      const current = resolveValue(row, 'current')
      const peer = resolveValue(row, 'peer')
      const delta = resolveDelta(row)
      if (!Number.isFinite(current) || !Number.isFinite(peer)) return null
      return {
        label: row.label,
        unit: row.unit || '',
        current,
        peer,
        decimals: row.decimals ?? 2,
        delta,
      }
    })
    .filter(Boolean)
  if (!entries.length) return []
  const phrases = entries.slice(0, 3).map((entry) => {
    const unitText = entry.unit ? entry.unit : ''
    const currentText = `${formatNumber(entry.current, entry.decimals)}${unitText}`
    const peerText = `${formatNumber(entry.peer, entry.decimals)}${unitText}`
    const deltaText = entry.delta === null ? '同比暂无数据' : `同比 ${formatDelta(entry.delta)}`
    return `${entry.label} 本期 ${currentText}，同期 ${peerText}，${deltaText}`
  })
  const suffix = entries.length > 3 ? '（其余略）' : ''
  return [`【同比】${phrases.join('；')}${suffix}`]
})

const planSummaryLines = computed(() => {
  if (!planComparisonEntries.value.length) return []
  const monthNote = planComparisonMonthLabel.value ? `（${planComparisonMonthLabel.value}）` : ''
  const phrases = planComparisonEntries.value.slice(0, 3).map((entry) => {
    const actual = Number.isFinite(entry.actualValue)
      ? `${formatNumber(entry.actualValue, entry.decimals)}${entry.unit || ''}`
      : '—'
    const planText = `${formatNumber(entry.planValue, entry.decimals)}${entry.unit || ''}`
    const completion =
      entry.completionRate === null ? '完成率暂无' : `完成率 ${formatPercentValue(entry.completionRate)}`
    const statusText = formatPlanStatusLabel(entry.completionRate)
    return `${entry.label} 本期 ${actual}，计划 ${planText}，${completion}（${statusText}）`
  })
  const suffix = planComparisonEntries.value.length > 3 ? '（其余略）' : ''
  return phrases.length ? [`【计划】${phrases.join('；')}${suffix}${monthNote}`] : []
})

const analysisSummaryEntries = computed(() => {
  const entries = []
  if (summaryOverallLine.value) {
    entries.push(`【整体概览】${summaryOverallLine.value}`)
  }
  if (summaryTimelineInsight.value) {
    entries.push(`【趋势观测】${summaryTimelineInsight.value}`)
  }
  yoySummaryLines.value.forEach((line) => entries.push(line))
  ringSummaryLines.value.forEach((line) => entries.push(line))
  planSummaryLines.value.forEach((line) => entries.push(line))
  summaryCorrelationLines.value.forEach((line) => entries.push(line))
  if (summaryWarningLine.value) {
    entries.push(`【风险提示】${summaryWarningLine.value}`)
  }
  return entries
})

const analysisSummaryText = computed(() => {
  if (!analysisSummaryEntries.value.length) return ''
  const header = infoBanner.value || `${analysisModeLabel.value} ｜ 单位：${activeUnitLabel.value}`
  return [header, ...analysisSummaryEntries.value.map((line, index) => `${index + 1}. ${line}`)].join('\n')
})

const summaryCopyMessage = ref('')
async function copyAnalysisSummary() {
  if (!analysisSummaryText.value) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(analysisSummaryText.value)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = analysisSummaryText.value
      textarea.style.position = 'fixed'
      document.body.appendChild(textarea)
      textarea.focus()
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    summaryCopyMessage.value = '已复制到剪贴板'
    setTimeout(() => {
      summaryCopyMessage.value = ''
    }, 2000)
  } catch (err) {
    summaryCopyMessage.value = '复制失败，请手动选择文本'
    setTimeout(() => {
      summaryCopyMessage.value = ''
    }, 2000)
  }
}

function clearAiReportPolling() {
  if (aiReportPollTimer !== null) {
    clearTimeout(aiReportPollTimer)
    aiReportPollTimer = null
  }
}

function resetAiReportState() {
  clearAiReportPolling()
  aiReportJobId.value = ''
  aiReportStatus.value = 'idle'
  aiReportContent.value = ''
  aiReportStatusMessage.value = ''
  aiReportStage.value = ''
}

function startAiReportPolling(jobId) {
  clearAiReportPolling()
  if (!jobId) return
  aiReportStatus.value = 'pending'
  updateAiReportStage('pending')
  setAiReportRunningMessage('pending')
  const poll = async () => {
    // Prevent zombie pollers if active job changed during await
    if (aiReportJobId.value !== jobId) return

    try {
      const payload = await getDataAnalysisAiReport(projectKey.value, jobId)
      if (!payload?.ok) {
        throw new Error(payload?.message || '获取智能报告失败')
      }
      
      // Re-check active job ID after await
      if (aiReportJobId.value !== jobId) return

      const status = payload.status || 'pending'
      const stageKey = payload.stage || ''
      if (stageKey) {
        updateAiReportStage(stageKey)
      }
      aiReportStatus.value = status
      if (status === 'ready' && typeof payload.report === 'string') {
        aiReportContent.value = payload.report
        aiReportStatusMessage.value = ''
        updateAiReportStage('ready')
        clearAiReportPolling()
        return
      }
      if (status === 'failed') {
        aiReportStatusMessage.value = payload.error || '智能报告生成失败'
        updateAiReportStage('failed')
        clearAiReportPolling()
        return
      }
      setAiReportRunningMessage(stageKey || 'pending')
    } catch (err) {
      // Re-check active job ID after await
      if (aiReportJobId.value !== jobId) return
      aiReportStatusMessage.value = err instanceof Error ? err.message : String(err)
    }
    if (aiReportStatus.value !== 'ready' && aiReportStatus.value !== 'failed') {
      aiReportPollTimer = window.setTimeout(poll, 2000)
    }
  }
  poll()
}

onBeforeUnmount(() => {
  clearAiReportPolling()
})

const shortConfig = computed(() => {
  if (!pageConfig.value) return ''
  const idx = pageConfig.value.lastIndexOf('/')
  return idx >= 0 ? pageConfig.value.slice(idx + 1) : pageConfig.value
})

function resolveUnitLabel(unitKey) {
  if (!unitKey) return '—'
  return unitDict.value[unitKey] || unitKey
}

const activeUnitLabel = computed(() => resolveUnitLabel(activeUnit.value || selectedUnits.value[0] || ''))
const analysisModeLabel = computed(() => {
  const found = analysisModes.value.find((item) => item.value === analysisMode.value)
  return found?.label || (analysisMode.value === 'daily' ? '单日数据' : '累计数据')
})

const viewLabelMap = { daily: '单日数据', range: '累计数据' }
function resolveViewNameForUnit(unitKey) {
  const label = resolveUnitLabel(unitKey)
  const modeLabel = viewLabelMap[analysisMode.value] || analysisModeLabel.value
  const target = viewMapping.value[modeLabel]
  if (target && typeof target === 'object') {
    for (const [viewName, units] of Object.entries(target)) {
      if (Array.isArray(units) && units.includes(label)) {
        return viewName
      }
    }
  }
  return analysisMode.value === 'daily' ? 'company_daily_analysis' : 'company_sum_analysis'
}

const resultUnitKeys = computed(() => {
  const ordered = selectedUnits.value.filter((key) => unitResults.value[key])
  const leftovers = Object.keys(unitResults.value).filter((key) => !ordered.includes(key))
  return [...ordered, ...leftovers]
})

const aiReportButtonLabel = computed(() => {
  if (aiReportEnabled.value && aiReportJobId.value && aiReportStatus.value !== 'ready') {
    return '智能报告生成中'
  }
  return '下载智能分析报告'
})

const aiReportButtonDisabled = computed(() => {
  if (!aiFeatureAccessible.value) return true
  if (!aiReportEnabled.value) return true
  if (!resultUnitKeys.value.length) return true
  if (queryLoading.value) return true
  if (!aiReportJobId.value) return true
  return aiReportStatus.value !== 'ready'
})

const resolvedMetricGroups = computed(() => metricGroups.value)

const availableMetricKeys = computed(() => {
  const bucket = new Set()
  resolvedMetricGroups.value.forEach((group) => {
    if (!Array.isArray(group.options)) return
    group.options.forEach((option) => {
      if (option?.value) bucket.add(option.value)
    })
  })
  return bucket
})

const breadcrumbProjectPath = computed(
  () => `/projects/${encodeURIComponent(projectKey.value)}/pages/${encodeURIComponent(pageKey.value)}`,
)

async function loadSchema() {
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await getDataAnalysisSchema(projectKey.value, { config: pageConfig.value })
    if (!payload?.ok) {
      throw new Error(payload?.message || '配置加载失败')
    }
    schema.value = payload
    selectedUnits.value = []
    activeUnit.value = ''
    const defaultTempKey = temperatureMetricKey.value
    selectedMetrics.value = defaultTempKey ? new Set([defaultTempKey]) : new Set()
    analysisMode.value = payload.analysis_modes?.[0]?.value || 'daily'
    await ensureDefaultBizDate()
    applyDateDefaults(payload.date_defaults)
    clearPreviewState()
  } catch (err) {
    errorMessage.value = err?.message || '数据分析配置加载失败'
  } finally {
    loading.value = false
  }
}

async function loadDefaultBizDate() {
  const today = new Date().toISOString().slice(0, 10)
  try {
    const payload = await getDashboardBizDate(projectKey.value)
    const fromApi =
      typeof payload?.set_biz_date === 'string' ? payload.set_biz_date.trim() : ''
    defaultBizDate.value = fromApi || today
  } catch (err) {
    defaultBizDate.value = today
  }
  return defaultBizDate.value
}

async function ensureDefaultBizDate() {
  if (defaultBizDate.value) {
    return defaultBizDate.value
  }
  return loadDefaultBizDate()
}

function applyDateDefaults(defaults = {}) {
  const fallbackDate = defaultBizDate.value || new Date().toISOString().slice(0, 10)
  const start =
    typeof defaults?.起始日期 === 'string' && defaults.起始日期 ? defaults.起始日期 : fallbackDate
  startDate.value = start
  endDate.value =
    typeof defaults?.结束日期 === 'string' && defaults.结束日期 ? defaults.结束日期 : start
}

function toggleMetric(key) {
  const next = new Set(selectedMetrics.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  selectedMetrics.value = next
}

function selectAllMetrics() {
  if (!availableMetricKeys.value.size) {
    formError.value = '当前视图暂无可选指标。'
    return
  }
  selectedMetrics.value = new Set(availableMetricKeys.value)
}

function clearMetrics() {
  selectedMetrics.value = new Set()
}

function clearPreviewState() {
  previewRows.value = []
  infoBanner.value = ''
  queryWarnings.value = []
  lastQueryMeta.value = null
  timelineGrid.value = { columns: [], rows: [] }
  unitResults.value = {}
  resetAiReportState()
  if (!selectedUnits.value.includes(activeUnit.value)) {
    activeUnit.value = selectedUnits.value[0] || ''
  }
}

function resetSelections() {
  selectedUnits.value = []
  activeUnit.value = ''
  const defaultTempKey = temperatureMetricKey.value
  selectedMetrics.value = defaultTempKey ? new Set([defaultTempKey]) : new Set()
  applyDateDefaults(schema.value?.date_defaults || {})
  formError.value = ''
  aiReportEnabled.value = false
  clearPreviewState()
}

function parseDateStrict(value) {
  if (!value) return null
  const ts = Date.parse(String(value))
  if (Number.isNaN(ts)) return null
  return new Date(ts)
}

function formatDateIso(date) {
  if (!(date instanceof Date) || Number.isNaN(date.valueOf())) return ''
  return date.toISOString().slice(0, 10)
}

function shiftDays(date, offset) {
  const cloned = new Date(date)
  cloned.setDate(cloned.getDate() + offset)
  return cloned
}

function daysBetweenInclusive(start, end) {
  const msPerDay = 24 * 60 * 60 * 1000
  return Math.floor((end - start) / msPerDay) + 1
}

function isFullMonthRange(startDateStr, endDateStr) {
  const start = parseDateStrict(startDateStr)
  const end = parseDateStrict(endDateStr)
  if (!start || !end) return false
  if (start.getFullYear() !== end.getFullYear() || start.getMonth() !== end.getMonth()) return false
  const firstDay = new Date(start.getFullYear(), start.getMonth(), 1)
  const lastDay = new Date(start.getFullYear(), start.getMonth() + 1, 0)
  return start.getTime() === firstDay.getTime() && end.getTime() === lastDay.getTime()
}

function computePreviousRangeForRing(startDateStr, endDateStr, mode) {
  if (mode !== 'range') return { range: null, note: '环比仅支持累计模式' }
  if (!startDateStr || !endDateStr) return { range: null, note: '缺少起止日期，无法计算环比' }
  if (startDateStr === endDateStr) return { range: null, note: '单日不计算环比' }
  const start = parseDateStrict(startDateStr)
  const end = parseDateStrict(endDateStr)
  if (!start || !end) return { range: null, note: '日期格式异常，环比已跳过' }
  const minDate = parseDateStrict(MIN_ANALYSIS_DATE)
  if (!minDate) return { range: null, note: '最早日期未设置，环比已跳过' }

  let prevStart = null
  let prevEnd = null
  if (isFullMonthRange(startDateStr, endDateStr)) {
    prevStart = new Date(start.getFullYear(), start.getMonth() - 1, 1)
    prevEnd = new Date(start.getFullYear(), start.getMonth(), 0)
  } else {
    const span = daysBetweenInclusive(start, end)
    prevEnd = shiftDays(start, -1)
    prevStart = shiftDays(start, -span)
  }

  if (prevStart < minDate) {
    return { range: null, note: `起始早于 ${MIN_ANALYSIS_DATE}，环比已跳过` }
  }

  return {
    range: {
      start: formatDateIso(prevStart),
      end: formatDateIso(prevEnd),
    },
    note: '',
  }
}

function resolveTotalCurrentFromRow(row) {
  if (!row) return null
  if (row.total_current !== undefined && row.total_current !== null) {
    const num = Number(row.total_current)
    return Number.isFinite(num) ? num : null
  }
  if (Array.isArray(row.timeline)) {
    const sum = row.timeline.reduce((acc, entry) => {
      const num = Number(entry?.current)
      if (Number.isFinite(num)) return acc + num
      return acc
    }, 0)
    return Number.isFinite(sum) ? sum : null
  }
  return null
}

function buildTotalsMap(rows) {
  const map = {}
  if (!Array.isArray(rows)) return map
  rows.forEach((row) => {
    if (!row?.key) return
    const total = resolveTotalCurrentFromRow(row)
    if (total !== null) {
      map[row.key] = total
    }
  })
  return map
}

function accumulateValueToMonthEnd(timelineEntries, periodEnd) {
  if (!Array.isArray(timelineEntries) || !timelineEntries.length) return null
  const cutoff = periodEnd ? Date.parse(periodEnd) : Number.NaN
  let sum = 0
  let hasValue = false
  timelineEntries.forEach((entry) => {
    if (!entry?.date) return
    const ts = Date.parse(entry.date)
    if (Number.isNaN(ts)) return
    if (!Number.isNaN(cutoff) && ts > cutoff) return
    const value = Number(entry.current)
    if (!Number.isFinite(value)) return
    sum += value
    hasValue = true
  })
  return hasValue ? sum : null
}

function mapPlanComparisonEntries(planPayload, rows = [], timelineMap = new Map()) {
  if (!planPayload?.entries || !planPayload.entries.length) return []
  return planPayload.entries
    .map((entry) => {
      if (!entry?.key) return null
      const row = rows.find((item) => item.key === entry.key)
      const timelineEntries = timelineMap.get(entry.key) || row?.timeline || []
      const decimals = Number.isInteger(row?.decimals) ? row.decimals : 2
      const actualValue =
        entry.actual_value !== undefined && entry.actual_value !== null
          ? Number(entry.actual_value)
          : accumulateValueToMonthEnd(timelineEntries, planPayload.period_end)
      const planValue =
        entry.plan_value !== undefined && entry.plan_value !== null ? Number(entry.plan_value) : null
      if (!Number.isFinite(planValue)) return null
      const completionRate =
        entry.completion_rate !== undefined && entry.completion_rate !== null
          ? Number(entry.completion_rate)
          : Number.isFinite(actualValue) && planValue !== 0
            ? (actualValue / planValue) * 100
            : null
      return {
        key: entry.key,
        label: entry.label || row?.label || entry.key,
        unit: entry.unit || row?.unit || '',
        planValue,
        actualValue: Number.isFinite(actualValue) ? actualValue : null,
        completionRate: Number.isFinite(completionRate) ? completionRate : null,
        decimals,
      }
    })
    .filter(Boolean)
}

async function runAnalysis() {
  formError.value = ''
  const targetUnits = Array.from(new Set(selectedUnits.value.filter((unit) => unit && typeof unit === 'string')))
  if (!targetUnits.length) {
    formError.value = '请选择至少一个单位。'
    return
  }
  if (!selectedMetrics.value.size) {
    formError.value = '至少选择一个指标。'
    return
  }
  if (!startDate.value || !endDate.value) {
    formError.value = '请选择起止日期。'
    return
  }
  clearPreviewState()
  queryLoading.value = true
  const startedAt = Date.now()
  try {
  const runMetrics = Array.from(selectedMetrics.value)
  const requestBase = {
    metrics: runMetrics,
    analysis_mode: analysisMode.value,
    start_date: startDate.value,
    end_date: endDate.value,
    request_ai_report: aiReportEnabled.value && aiFeatureAccessible.value,
  }
  if (aiReportEnabled.value && aiFeatureAccessible.value) {
    aiReportStatus.value = 'pending'
    updateAiReportStage('pending')
    setAiReportRunningMessage('pending')
    aiReportContent.value = ''
  } else {
      resetAiReportState()
    }
    const prevRangeInfo = computePreviousRangeForRing(startDate.value, endDate.value, analysisMode.value)
    const aggregatedResults = {}
    const errors = []
    for (const unitKey of targetUnits) {
      const payload = { ...requestBase, unit_key: unitKey }
      try {
        const response = await runDataAnalysis(projectKey.value, payload, { config: pageConfig.value })
        if (!response?.ok) {
          throw new Error(response?.message || '分析查询失败')
        }
        const decoratedRows = Array.isArray(response.rows)
          ? response.rows.map((row) => ({
              ...row,
              decimals: metricDecimalsMap.value?.[row.key] ?? 2,
            }))
          : []
        const aiJobId = typeof response.ai_report_job_id === 'string' ? response.ai_report_job_id : ''
        if (aiReportEnabled.value && aiJobId) {
          aiReportJobId.value = aiJobId
          startAiReportPolling(aiJobId)
        }
        let ringComparePayload = null
        if (response.ring_compare || response.ringCompare) {
          const payloadSource = response.ring_compare || response.ringCompare
          if (payloadSource?.prevTotals && payloadSource.range) {
            ringComparePayload = {
              range: payloadSource.range,
              prevTotals: payloadSource.prevTotals,
              note: payloadSource.note || '',
            }
          } else if (payloadSource?.note) {
            ringComparePayload = {
              range: payloadSource.range || null,
              prevTotals: payloadSource.prevTotals || null,
              note: payloadSource.note,
            }
          }
        }
        if (!ringComparePayload) {
          let prevTotals = null
          let ringNote = prevRangeInfo.note
          if (prevRangeInfo.range) {
            try {
              const prevPayload = {
                ...payload,
                start_date: prevRangeInfo.range.start,
                end_date: prevRangeInfo.range.end,
                request_ai_report: false,
              }
              const prevResponse = await runDataAnalysis(projectKey.value, prevPayload, { config: pageConfig.value })
              if (prevResponse?.ok) {
                const prevRows = Array.isArray(prevResponse.rows) ? prevResponse.rows : []
                prevTotals = buildTotalsMap(prevRows)
              } else {
                ringNote = prevResponse?.message || '环比数据获取失败'
              }
            } catch (err) {
              ringNote = err instanceof Error ? err.message : String(err)
            }
          }
          ringComparePayload = {
            range: prevRangeInfo.range || null,
            prevTotals,
            note: ringNote,
          }
        }
        const meta = {
          unit_key: unitKey,
          unit_label: response.unit_label || resolveUnitLabel(unitKey),
          analysis_mode_label: response.analysis_mode_label || analysisModeLabel.value,
          view: response.view || resolveViewNameForUnit(unitKey),
          start_date: response.start_date || startDate.value,
          end_date: response.end_date || endDate.value,
          ai_report_job_id: aiJobId,
        }
        aggregatedResults[unitKey] = {
          rows: decoratedRows,
          warnings: Array.isArray(response.warnings) ? response.warnings : [],
          timeline: buildTimelineGrid(decoratedRows),
          infoBanner: buildInfoBannerFromMeta(meta),
          ringCompare: ringComparePayload,
          planComparison: response.plan_comparison || null,
          planComparisonNote: response.plan_comparison_note || '',
          meta,
          aiReportJobId: aiJobId,
        }
      } catch (err) {
        errors.push(`${resolveUnitLabel(unitKey)}：${err instanceof Error ? err.message : String(err)}`)
      }
    }
    const populatedKeys = Object.keys(aggregatedResults)
    if (!populatedKeys.length) {
      throw new Error(errors.join('；') || '分析查询失败')
    }
    unitResults.value = aggregatedResults
    const nextActiveCandidate =
      activeUnit.value && aggregatedResults[activeUnit.value] && targetUnits.includes(activeUnit.value)
        ? activeUnit.value
        : targetUnits.find((unit) => aggregatedResults[unit]) || ''
    applyActiveUnitResult(nextActiveCandidate || '')
    formError.value = errors.length ? errors.join('；') : ''
  } catch (err) {
    formError.value = err instanceof Error ? err.message : '分析查询失败'
    clearPreviewState()
  } finally {
    queryLoading.value = false
  }
}

function buildInfoBannerFromMeta(meta) {
  if (!meta) return ''
  const dateRange =
    meta.start_date && meta.end_date
      ? meta.start_date === meta.end_date
        ? meta.start_date
        : `${meta.start_date} ~ ${meta.end_date}`
      : meta.start_date || meta.end_date || ''
  return [
    meta.analysis_mode_label,
    `单位：${meta.unit_label}`,
    dateRange ? `日期：${dateRange}` : null,
  ]
    .filter(Boolean)
    .join(' ｜ ')
}

function applyActiveUnitResult(unitKey) {
  if (!unitKey || !unitResults.value[unitKey]) {
    previewRows.value = []
    infoBanner.value = ''
    queryWarnings.value = []
    lastQueryMeta.value = null
    timelineGrid.value = { columns: [], rows: [] }
    activeUnit.value = ''
    resetAiReportState()
    return
  }
  const result = unitResults.value[unitKey]
  previewRows.value = cloneResultRows(result.rows)
  infoBanner.value = result.infoBanner
  queryWarnings.value = result.warnings
  lastQueryMeta.value = result.meta
  timelineGrid.value = cloneTimelineGrid(result.timeline)
  activeUnit.value = unitKey
  if (aiReportEnabled.value) {
    const jobId = result.aiReportJobId || result.meta?.ai_report_job_id || aiReportJobId.value || ''
    if (jobId) {
      if (aiReportJobId.value !== jobId) {
        aiReportJobId.value = jobId
        aiReportContent.value = ''
        startAiReportPolling(jobId)
      } else if (
        aiReportStatus.value === 'pending' &&
        !aiReportContent.value &&
        aiReportPollTimer === null
      ) {
        startAiReportPolling(jobId)
      }
    } else {
      aiReportStatus.value = 'pending'
      aiReportStatusMessage.value = '已提交生成请求，等待后台任务启动…'
      updateAiReportStage('')
      aiReportJobId.value = ''
    }
  } else {
    resetAiReportState()
  }
}

function ensureActiveUnitFromSelection() {
  if (activeUnit.value && selectedUnits.value.includes(activeUnit.value)) {
    return
  }
  activeUnit.value = selectedUnits.value[0] || ''
}

function handleSwitchUnit(unitKey) {
  if (!unitKey || unitKey === activeUnit.value) return
  if (!unitResults.value[unitKey]) return
  applyActiveUnitResult(unitKey)
}

function handleUnitSelection(unitKey, checked) {
  const next = [...selectedUnits.value]
  const exists = next.indexOf(unitKey)
  if (checked && exists === -1) {
    next.push(unitKey)
  } else if (!checked && exists !== -1) {
    next.splice(exists, 1)
  }
  selectedUnits.value = next
}

function getUnitSelectionOrder(unitKey) {
  const index = selectedUnits.value.indexOf(unitKey)
  if (index === -1) return ''
  return String(index + 1)
}

function getMetricSelectionOrder(metricKey) {
  const order = Array.from(selectedMetrics.value)
  const index = order.indexOf(metricKey)
  if (index === -1) return ''
  return String(index + 1)
}

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

function formatDelta(value) {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

function normalizeChartValue(value, decimals = 2) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return Number(num.toFixed(decimals))
}

function withAlpha(hex, alpha) {
  if (typeof hex !== 'string' || !hex.startsWith('#')) return hex
  const value = hex.slice(1)
  if (value.length !== 6) return hex
  const r = parseInt(value.slice(0, 2), 16)
  const g = parseInt(value.slice(2, 4), 16)
  const b = parseInt(value.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function formatChartDelta(entry) {
  if (!entry || entry.peer === null || entry.peer === undefined) return ''
  const current = Number(entry.current)
  const peer = Number(entry.peer)
  if (!Number.isFinite(current) || !Number.isFinite(peer) || peer === 0) {
    return ''
  }
  const delta = ((current - peer) / peer) * 100
  if (!Number.isFinite(delta)) return ''
  const sign = delta >= 0 ? '+' : ''
  return `<span class="chart-tooltip__delta">${sign}${delta.toFixed(2)}%</span>`
}

function cloneResultRows(rows) {
  if (!Array.isArray(rows)) return []
  return rows.map((row) => ({ ...row }))
}

function cloneTimelineGrid(timeline) {
  if (!timeline || typeof timeline !== 'object') {
    return { columns: [], rows: [] }
  }
  const columns = Array.isArray(timeline.columns)
    ? timeline.columns.map((col) => ({ ...col }))
    : []
  const rows = Array.isArray(timeline.rows)
    ? timeline.rows.map((row) => ({ ...row }))
    : []
  return { columns, rows }
}

function isTemperatureMetric(metric) {
  if (!metric) return false
  if (metric.value_type === 'temperature') return true
  const label = metric.label || ''
  return TEMPERATURE_KEYWORDS.some((keyword) => label.includes(keyword))
}

function reorderMetricKeys(keys, temperatureKey, availableKeys = []) {
  if (!keys || !keys.length) return []
  const filtered = keys.filter((key) => !availableKeys.length || availableKeys.includes(key))
  if (!filtered.length) return []
  if (!temperatureKey) return filtered.slice(0, 2)
  const hasTemp = filtered.includes(temperatureKey)
  const withoutTemp = filtered.filter((key) => key !== temperatureKey)
  if (!hasTemp) return filtered.slice(0, 2)
  if (!withoutTemp.length) return [temperatureKey]
  const ordered = withoutTemp.slice(0, 1)
  ordered.push(temperatureKey)
  return ordered
}

function resolveValue(row, field) {
  const totalKey = `total_${field}`
  if (analysisMode.value === 'range' && row[totalKey] !== undefined && row[totalKey] !== null) {
    return row[totalKey]
  }
  return row[field]
}

function computeRelativeRate(current, reference) {
  const curr = Number(current)
  const ref = Number(reference)
  if (!Number.isFinite(curr) || !Number.isFinite(ref) || Math.abs(ref) < 1e-9) {
    return null
  }
  return ((curr - ref) / Math.abs(ref)) * 100
}

function resolveDelta(row) {
  const current = resolveValue(row, 'current')
  const peer = resolveValue(row, 'peer')
  return computeRelativeRate(current, peer)
}

function applyDecimals(value, decimals = 2) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return Number(num.toFixed(decimals))
}

function formatPercentValue(value) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  return `${num.toFixed(2)}%`
}

function createDeltaCellPayload(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return { text: '—', delta: null }
  }
  const deltaNumber = Number(value)
  return {
    text: formatPercentValue(deltaNumber) || '—',
    delta: deltaNumber,
  }
}

function getDeltaColor(deltaNumber) {
  if (deltaNumber === null || deltaNumber === undefined || Number.isNaN(deltaNumber)) {
    return 'var(--neutral-600, #5f6368)'
  }
  return deltaNumber >= 0 ? 'var(--danger-600, #d93025)' : 'var(--success-600, #0f9d58)'
}

const timelineDeltaCellTemplate = (createElement, props) => {
  const rawValue = props?.model?.[props.prop]
  const text =
    typeof rawValue === 'object' && rawValue !== null
      ? rawValue.text ?? '—'
      : typeof rawValue === 'string'
        ? rawValue
        : '—'
  const deltaNumber =
    typeof rawValue === 'object' && rawValue !== null && typeof rawValue.delta === 'number'
      ? rawValue.delta
      : null
  const style = { color: getDeltaColor(deltaNumber) }
  return createElement('span', { style }, text || '—')
}

function extractTimelineCellText(value) {
  if (value && typeof value === 'object') {
    return value.text ?? ''
  }
  return value ?? ''
}

function buildTimelineGrid(rows) {
  const dateSet = new Set()
  const metrics = []
  rows.forEach((row) => {
    if (Array.isArray(row.timeline) && row.timeline.length) {
      metrics.push(row)
      row.timeline.forEach((entry) => {
        if (entry?.date) {
          dateSet.add(entry.date)
        }
      })
    }
  })
  const sortedDates = Array.from(dateSet).sort()
  if (!sortedDates.length || !metrics.length) {
    return { columns: [], rows: [] }
  }
  const metricState = metrics.map((row) => ({
    key: row.key,
    label: row.label,
    timeline: row.timeline,
    decimals: row.decimals ?? 2,
    sumCurrent: 0,
    sumPeer: 0,
    valueType: row.value_type || 'analysis',
    totalCurrent: row.total_current ?? null,
    totalPeer: row.total_peer ?? null,
  }))
  const columns = [{ prop: 'date', name: '日期', size: 110 }]
  metricState.forEach((row) => {
    columns.push({ prop: `${row.key}__current`, name: `${row.label}(本期)`, size: 140 })
    columns.push({ prop: `${row.key}__peer`, name: `${row.label}(同期)`, size: 140 })
    columns.push({
      prop: `${row.key}__delta`,
      name: `${row.label}(同比%)`,
      size: 120,
      cellTemplate: timelineDeltaCellTemplate,
    })
  })
  const gridRows = sortedDates.map((date) => {
    const record = { date }
    metricState.forEach((row) => {
      const entry = row.timeline.find((item) => item.date === date)
      const current = entry?.current ?? null
      const peer = entry?.peer ?? null
      if (current !== null) {
        row.sumCurrent += Number(current)
      }
      if (peer !== null) {
        row.sumPeer += Number(peer)
      }
      const currentFormatted = current !== null ? applyDecimals(current, row.decimals) : null
      const peerFormatted = peer !== null ? applyDecimals(peer, row.decimals) : null
      record[`${row.key}__current`] = currentFormatted
      record[`${row.key}__peer`] = peerFormatted
      const hasPeer = peer !== null && peer !== undefined
      const deltaValue = hasPeer && peer !== 0 ? (((current ?? 0) - peer) / peer) * 100 : null
      record[`${row.key}__delta`] = createDeltaCellPayload(deltaValue)
    })
    return record
  })
  const totalRecord = { date: '总计' }
  metricState.forEach((row) => {
    let totalCurrent = row.totalCurrent
    let totalPeer = row.totalPeer
    if (totalCurrent == null) {
      if (row.valueType === 'constant' && row.timeline && row.timeline.length) {
        totalCurrent = row.timeline[0]?.current ?? null
      } else if (row.valueType === 'analysis') {
        totalCurrent = row.sumCurrent || null
      } else {
        totalCurrent = row.sumCurrent || null
      }
    }
    if (totalPeer == null) {
      if (row.valueType === 'constant' && row.timeline && row.timeline.length) {
        totalPeer = row.timeline[0]?.peer ?? null
      } else if (row.valueType === 'analysis') {
        totalPeer = row.sumPeer || null
      } else {
        totalPeer = row.sumPeer || null
      }
    }
    totalRecord[`${row.key}__current`] = totalCurrent !== null ? applyDecimals(totalCurrent, row.decimals) : null
    totalRecord[`${row.key}__peer`] = totalPeer !== null ? applyDecimals(totalPeer, row.decimals) : null
    const totalDelta =
      totalPeer !== null && totalPeer !== 0 && totalCurrent !== null
        ? ((totalCurrent - totalPeer) / totalPeer) * 100
        : null
    totalRecord[`${row.key}__delta`] = createDeltaCellPayload(totalDelta)
  })
  gridRows.push(totalRecord)
  return { columns, rows: gridRows }
}

function formatExportNumber(value, decimals = 2) {
  if (value === null || value === undefined || value === '—') return ''
  const num = Number(value)
  if (Number.isNaN(num)) return value
  return Number(num.toFixed(decimals))
}

function buildSummarySheetData(rows) {
  const header = ['指标', '本期', '同期', '同比', '计量单位']
  const source = Array.isArray(rows) ? rows : []
  const mapped = source.map((row) => [
    row.label,
    formatExportNumber(resolveValue(row, 'current'), row.decimals || 2),
    formatExportNumber(resolveValue(row, 'peer'), row.decimals || 2),
    formatPercentValue(resolveDelta(row)) || '',
    row.unit || '',
  ])
  return [header, ...mapped]
}

function buildRingSheetData(result) {
  const prevTotals = result?.ringCompare?.prevTotals
  const range = result?.ringCompare?.range
  if (!prevTotals || !range) return null
  const rows = Array.isArray(result?.rows) ? result.rows : []
  const header = ['指标', '上期累计', '本期累计', '环比', '单位']
  const mapped = rows.map((row) => {
    const current = resolveTotalCurrentFromRow(row)
    const prev = prevTotals[row.key]
    const rate =
      Number.isFinite(prev) && prev !== 0 && Number.isFinite(current)
        ? ((current - prev) / prev) * 100
        : null
    return [
      row.label,
      formatExportNumber(prev, row.decimals || 2),
      formatExportNumber(current, row.decimals || 2),
      formatPercentValue(rate) || '',
      row.unit || '',
    ]
  })
  return [header, ...mapped]
}

function buildPlanSheetData(result) {
  const entries = mapPlanComparisonEntries(result?.planComparison, result?.rows || [])
  if (!entries.length) return null
  const header = ['指标', '截至本期末完成', '月度计划', '完成率', '状态', '计量单位']
  const mapped = entries.map((entry) => [
    entry.label,
    formatExportNumber(entry.actualValue, entry.decimals),
    formatExportNumber(entry.planValue, entry.decimals),
    formatPercentValue(entry.completionRate) || '',
    formatPlanStatusLabel(entry.completionRate),
    entry.unit || '',
  ])
  const payload = [header, ...mapped]
  if (result?.planComparison?.month_label) {
    payload.push([])
    payload.push(['计划月份', result.planComparison.month_label])
  }
  return payload
}

function buildTimelineSheetData(timeline) {
  if (!timeline || !Array.isArray(timeline.columns) || !timeline.columns.length) return null
  const columns = timeline.columns
  const header = columns.map((col) => col.name || col.prop)
  const rows = (timeline.rows || []).map((record) =>
    columns.map((col) => extractTimelineCellText(record[col.prop])),
  )
  return [header, ...rows]
}

function buildMetaSheetData(meta) {
  const data = [
    ['项目', pageDisplayName.value],
    ['单位', meta?.unit_label || activeUnitLabel.value],
    ['分析模式', meta?.analysis_mode_label || analysisModeLabel.value],
    [
      '日期范围',
      meta && meta.start_date && meta.end_date ? `${meta.start_date} ~ ${meta.end_date}` : `${startDate.value} ~ ${endDate.value}`,
    ],
    ['生成时间', new Date().toLocaleString()],
    ['指标数量', selectedMetrics.value.size],
  ]
  return data
}

function buildUnitSheetData(result) {
  const sheetData = []
  const summary = buildSummarySheetData(result?.rows)
  summary.forEach((row) => sheetData.push(row))
  const ringData = buildRingSheetData(result)
  if (ringData && ringData.length) {
    sheetData.push([])
    sheetData.push(['环比比较'])
    ringData.forEach((row) => sheetData.push(row))
  } else if (result?.ringCompare?.note) {
    sheetData.push([])
    sheetData.push(['环比比较'])
    sheetData.push([result.ringCompare.note])
  }
  const planData = buildPlanSheetData(result)
  if (planData && planData.length) {
    sheetData.push([])
    sheetData.push(['计划比较'])
    planData.forEach((row) => sheetData.push(row))
  }
  const timelineData = buildTimelineSheetData(result?.timeline)
  if (timelineData && timelineData.length) {
    sheetData.push([])
    sheetData.push(['区间明细'])
    timelineData.forEach((row) => sheetData.push(row))
  }
  sheetData.push([])
  sheetData.push(['查询信息'])
  buildMetaSheetData(result?.meta).forEach((row) => sheetData.push(row))
  return sheetData
}

function sanitizeSheetName(name) {
  if (!name) return 'Sheet'
  return name.replace(/[\\/?*\\[\\]:]/g, '_').slice(0, 31) || 'Sheet'
}

function resolveSheetName(baseName, usedNames) {
  const sanitized = sanitizeSheetName(baseName)
  if (!usedNames.has(sanitized)) {
    usedNames.add(sanitized)
    return sanitized
  }
  let counter = 2
  while (true) {
    const candidate = sanitizeSheetName(`${sanitized}_${counter}`)
    if (!usedNames.has(candidate)) {
      usedNames.add(candidate)
      return candidate
    }
    counter += 1
  }
}

function downloadExcel() {
  if (!resultUnitKeys.value.length) return
  const wb = XLSX.utils.book_new()
  const usedSheetNames = new Set()
  resultUnitKeys.value.forEach((unitKey) => {
    const result = unitResults.value[unitKey]
    if (!result) return
    const unitName = result.meta?.unit_label || resolveUnitLabel(unitKey)
    const sheet = XLSX.utils.aoa_to_sheet(buildUnitSheetData(result))
    const sheetName = resolveSheetName(unitName, usedSheetNames)
    XLSX.utils.book_append_sheet(wb, sheet, sheetName)
  })
  const filename = `数据分析_${analysisMode.value === 'range' ? '累计' : '单日'}_${Date.now()}.xlsx`
  XLSX.writeFile(wb, filename)
}

async function downloadAiReport() {
  if (aiReportButtonDisabled.value) return
  try {
    if (!aiReportContent.value && aiReportJobId.value) {
      const payload = await getDataAnalysisAiReport(projectKey.value, aiReportJobId.value)
      if (payload?.status === 'ready' && typeof payload.report === 'string') {
        aiReportContent.value = payload.report
        aiReportStatus.value = 'ready'
      } else if (payload?.status === 'failed') {
        aiReportStatus.value = 'failed'
        aiReportStatusMessage.value = payload?.error || '智能报告生成失败'
        return
      } else {
        aiReportStatus.value = payload?.status || 'pending'
        updateAiReportStage(payload?.stage || '')
        setAiReportRunningMessage(payload?.stage || 'pending')
        return
      }
    }
    if (!aiReportContent.value) {
      aiReportStatusMessage.value = '暂未获取到智能报告内容'
      return
    }
    const meta = unitResults.value[activeUnit.value]?.meta || lastQueryMeta.value || {}
    const unitName = meta.unit_label || resolveUnitLabel(activeUnit.value) || '未知单位'
    const start = meta.start_date || startDate.value || ''
    const end = meta.end_date || endDate.value || start
    const rangeLabel = start && end ? (start === end ? start : `${start}_${end}`) : '日期未定'
    const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14)
    const safeUnitName = unitName.replace(/[\\/:*?"<>|]/g, '_')
    const filename = `智能分析报告_${safeUnitName}_${rangeLabel}_${timestamp}.html`
    const blob = new Blob([aiReportContent.value], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (err) {
    aiReportStatusMessage.value = err instanceof Error ? err.message : String(err)
  }
}

watch(
  () => aiReportEnabled.value,
  (enabled) => {
    if (!enabled) {
      resetAiReportState()
      return
    }
    if (aiReportJobId.value) {
      startAiReportPolling(aiReportJobId.value)
    } else {
      aiReportStatus.value = 'pending'
      aiReportStatusMessage.value = '请生成分析结果后稍候，系统将自动获取智能报告'
      updateAiReportStage('')
    }
  },
)

watch(
  () => analysisMode.value,
  (mode) => {
    if (mode === 'daily') {
      endDate.value = startDate.value
    }
    clearPreviewState()
  },
)

watch(
  () => startDate.value,
  (value, oldValue) => {
    if (!value) return
    if (analysisMode.value === 'daily') {
      endDate.value = value
    } else if (endDate.value && value > endDate.value) {
      endDate.value = value
    }
    if (value !== oldValue) {
      clearPreviewState()
    }
  },
)

watch(
  () => endDate.value,
  (value, oldValue) => {
    if (!value) return
    if (analysisMode.value === 'daily' && value !== startDate.value) {
      startDate.value = value
    }
    if (value !== oldValue) {
      clearPreviewState()
    }
  },
)

watch(
  selectedUnits,
  () => {
    ensureActiveUnitFromSelection()
    clearPreviewState()
  },
  { deep: true },
)

watch(
  () => selectedMetrics.value,
  () => {
    clearPreviewState()
  },
  { deep: true },
)

watch(
  resolvedMetricGroups,
  () => {
    if (!selectedMetrics.value.size) return
    const allowed = availableMetricKeys.value
    if (!allowed.size) {
      selectedMetrics.value = new Set()
      clearPreviewState()
      return
    }
    const filtered = new Set([...selectedMetrics.value].filter((key) => allowed.has(key)))
    if (filtered.size !== selectedMetrics.value.size) {
      selectedMetrics.value = filtered
      clearPreviewState()
    }
  },
  { deep: true },
)

onMounted(() => {
  loadSchema()
})

onBeforeUnmount(() => {
  clearAiReportPolling()
})
</script>

<style scoped>
.analysis-main {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-block {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.analysis-subtitle {
  margin-top: 6px;
  font-size: 14px;
  color: var(--neutral-500);
}

.analysis-tag {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--primary-50);
  color: var(--primary-600);
  font-size: 12px;
  font-weight: 600;
  align-self: flex-start;
}

.form-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.form-grid--top {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  align-items: stretch;
}

.form-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-panel--metrics {
  width: 100%;
}

.form-panel--compact {
  min-height: 220px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.panel-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.panel-hint {
  font-size: 13px;
  color: var(--neutral-500);
}

.panel-hint.warning {
  color: var(--warning-600, #b45309);
}

.panel-hint.muted {
  color: var(--neutral-400);
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.chip-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 6px 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
}

.chip input {
  accent-color: var(--primary-600);
}

.chip.radio {
  background: var(--card-bg);
}

.chip.checkbox {
  border-radius: var(--radius);
}

.chip-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.chip-order {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: var(--primary-50);
  color: var(--primary-700);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--primary-100);
}

.chip.compact {
  padding: 4px 10px;
}

.metrics-panel-body {
  max-height: 420px;
  overflow-y: auto;
  padding-right: 6px;
}

.metrics-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.metrics-group {
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.correlation-matrix-panel {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light, rgba(0, 0, 0, 0.05));
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.correlation-matrix__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.correlation-matrix__table-wrapper {
  overflow-x: auto;
}

.correlation-matrix__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 360px;
}

.correlation-matrix__table th,
.correlation-matrix__table td {
  border: 1px solid var(--border-light, rgba(0, 0, 0, 0.08));
  padding: 6px 10px;
  text-align: center;
  font-size: 13px;
}

.correlation-matrix__table th {
  background: var(--neutral-50, #f8fafc);
  font-weight: 600;
}

.corr-cell {
  font-variant-numeric: tabular-nums;
}

.corr-cell--positive {
  color: var(--danger-600, #dc2626);
}

.corr-cell--negative {
  color: var(--success-600, #16a34a);
}

.corr-cell--neutral {
  color: var(--neutral-600, #475569);
}

.corr-cell--muted {
  color: var(--neutral-400, #94a3b8);
}

.corr-cell__meter {
  display: block;
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: var(--neutral-100, #f1f5f9);
  margin-top: 4px;
  overflow: hidden;
}

.corr-cell__meter-bar {
  display: block;
  height: 100%;
  border-radius: inherit;
  transition: width 0.2s ease;
}

.corr-cell__meter-bar--positive {
  background: linear-gradient(90deg, rgba(220, 38, 38, 0.15), rgba(220, 38, 38, 0.85));
}

.corr-cell__meter-bar--negative {
  background: linear-gradient(90deg, rgba(22, 163, 74, 0.15), rgba(22, 163, 74, 0.85));
}

.corr-cell__meter-bar--neutral {
  background: linear-gradient(90deg, rgba(71, 85, 105, 0.15), rgba(71, 85, 105, 0.8));
}

.corr-cell__meter-bar--muted {
  background: linear-gradient(90deg, rgba(148, 163, 184, 0.15), rgba(148, 163, 184, 0.4));
}

.correlation-matrix__notes {
  margin: 0;
}

.ring-summary {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-light, rgba(0, 0, 0, 0.05));
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ring-summary__header {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.ring-summary__table {
  width: 100%;
}

.metrics-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.metrics-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metrics-group-header h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.metrics-group-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--neutral-100);
  color: var(--neutral-600);
}

.group-badge--outline {
  border: 1px solid var(--primary-200);
  color: var(--primary-600);
  background: transparent;
}

.group-badge--temp {
  background: var(--info-50, #eff6ff);
  color: var(--info-600, #2563eb);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
  padding-right: 4px;
}

.date-subsection {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-light, rgba(0, 0, 0, 0.05));
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.date-subsection .panel-header {
  padding: 0;
}

.date-subsection h4 {
  font-size: 14px;
  margin: 0;
  font-weight: 600;
}

.date-subsection .date-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.date-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: var(--neutral-600);
}

.date-field input {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px;
}

.mode-desc {
  font-size: 13px;
  color: var(--neutral-600);
  margin-top: -4px;
}

.form-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.ai-report-controls {
  margin-left: auto;
  display: inline-flex;
  gap: 8px;
  align-items: center;
}

.ai-report-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--neutral-600);
  cursor: pointer;
}

.ai-report-toggle input {
  width: 16px;
  height: 16px;
}

.ai-report-hint {
  font-size: 12px;
  color: var(--neutral-500);
}

.ai-settings-btn {
  font-size: 13px;
  padding: 6px 12px;
}

.result-header-actions {
  display: flex;
  gap: 8px;
}

.ai-report-status {
  font-size: 12px;
  color: var(--neutral-500);
  margin: -8px 0 8px;
  text-align: right;
}

.result-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  text-align: center;
  font-size: 14px;
}

.result-table th {
  background: var(--neutral-50);
  color: var(--neutral-700);
}

.result-table--centered th,
.result-table--centered td {
  text-align: center;
}

.result-table .metric-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  text-align: center;
  width: 100%;
}

.result-table .value-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  text-align: center;
  width: 100%;
}

.result-table .value-number {
  text-align: center;
  display: inline-block;
}

.ai-settings-dialog__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 2000;
}

.ai-settings-dialog__panel {
  width: 100%;
  max-width: 420px;
  max-height: 90vh;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.3);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-settings-dialog__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.ai-settings-dialog__header h4 {
  margin: 0 0 4px;
  font-size: 18px;
}

.ai-settings-dialog__header p {
  margin: 0;
  color: var(--neutral-500);
  font-size: 13px;
}

.ai-settings-dialog__close {
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  color: var(--neutral-500);
  padding: 2px 6px;
}

.ai-settings-dialog__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding-right: 4px;
}

.ai-settings-dialog__loading {
  padding: 12px 0;
  font-size: 14px;
  color: var(--neutral-600);
}

.ai-settings-dialog__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--neutral-600);
}

.ai-settings-dialog__field input {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 10px;
  font-size: 14px;
}

.ai-settings-dialog__field textarea {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 10px;
  font-size: 14px;
  resize: vertical;
  min-height: 120px;
  line-height: 1.5;
}

.ai-settings-dialog__hint {
  margin: 0;
  font-size: 12px;
  color: var(--neutral-500);
}

.ai-settings-dialog__alert {
  margin: 4px 0 0;
  font-size: 13px;
  padding: 6px 10px;
  border-radius: var(--radius);
}

.ai-settings-dialog__alert--error {
  background: rgba(248, 113, 113, 0.1);
  color: #b91c1c;
}

.ai-settings-dialog__alert--success {
  background: rgba(16, 185, 129, 0.1);
  color: #047857;
}

.ai-settings-dialog__toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--neutral-600);
}

.ai-settings-dialog__toggle input {
  width: 16px;
  height: 16px;
}

.ai-settings-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.plan-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.plan-progress__bar {
  position: relative;
  width: 100%;
  height: 8px;
  background: var(--neutral-100, #f1f5f9);
  border-radius: 999px;
  overflow: hidden;
}

.plan-progress__bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0%;
  border-radius: inherit;
  transition: width 0.3s ease;
}

.plan-progress__meta {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--neutral-600);
}

.plan-progress__value {
  font-weight: 600;
}

.plan-progress__status {
  color: var(--neutral-500);
}

.plan-progress--ahead .plan-progress__bar-fill {
  background: var(--success-500, #16a34a);
}

.plan-progress--ontarget .plan-progress__bar-fill {
  background: var(--primary-500, #2563eb);
}

.plan-progress--lag .plan-progress__bar-fill {
  background: var(--danger-500, #dc2626);
}

.plan-progress--neutral .plan-progress__bar-fill {
  background: var(--neutral-300, #cbd5f5);
}

.plan-progress--ahead .plan-progress__value {
  color: var(--success-600, #15803d);
}

.plan-progress--ontarget .plan-progress__value {
  color: var(--primary-600, #1d4ed8);
}

.plan-progress--lag .plan-progress__value {
  color: var(--danger-600, #b91c1c);
}

.warning-list {
  margin: 4px 0 0;
  padding-left: 18px;
  color: var(--warning-600, #b45309);
  font-size: 13px;
}

.unit-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.unit-switch__label {
  color: var(--neutral-500);
  font-size: 14px;
}

.unit-switch__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.unit-switch--grid {
  margin: 0 24px 12px;
}

.unit-toggle {
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  color: var(--neutral-700);
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.unit-toggle:hover {
  border-color: var(--primary-300);
  color: var(--primary-700);
}

.unit-toggle.active {
  background: var(--primary-50);
  border-color: var(--primary-400);
  color: var(--primary-700);
  font-weight: 600;
}

.unit-switch--inline {
  margin-bottom: 8px;
}

.timeline-grid-wrapper {
  width: 100%;
  overflow: hidden;
}

.timeline-grid {
  height: 420px;
}

.comparison-section {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.comparison-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--neutral-800, #1f2937);
}

.timeline-chart-panel {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid var(--neutral-100);
  border-radius: var(--radius);
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timeline-chart-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.timeline-chart-toolbar__info h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.timeline-chart-toolbar__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.timeline-axis-hint {
  font-size: 13px;
  color: var(--neutral-600);
  display: flex;
  gap: 8px;
  align-items: center;
}

.chip--toggle {
  border-radius: 999px;
  border: 1px solid var(--neutral-200);
  background: var(--neutral-50);
  color: var(--neutral-700);
  transition: all 0.2s ease;
}

.chip--toggle .chip-hint {
  font-size: 12px;
  color: var(--neutral-500);
}

.chip--toggle.active {
  border-color: var(--primary-400);
  background: rgba(37, 99, 235, 0.08);
  color: var(--primary-700);
  font-weight: 600;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.12);
}

.timeline-chart-empty {
  padding: 18px;
  border: 1px dashed var(--neutral-200);
  border-radius: var(--radius);
  text-align: center;
  color: var(--neutral-500);
  font-size: 14px;
}

.chart-tooltip__title {
  font-weight: 700;
  margin-bottom: 8px;
}

.chart-tooltip__item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  line-height: 1.6;
}

.chart-tooltip__dot {
  display: inline-flex;
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.chart-tooltip__delta {
  margin-left: 6px;
  color: var(--danger-100, #fecdd3);
  font-weight: 600;
}

.headline-card {
  margin-bottom: 16px;
}

.card-header--tight {
  padding-bottom: 10px;
}

.headline-list {
  list-style: disc;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
  color: #0f172a;
}

.summary-copy-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--primary-600);
}


.metric-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 999px;
  font-size: 12px;
}

.tag--subtle {
  background: var(--neutral-100);
  color: var(--neutral-600);
}

.value-cell {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.value-number {
  font-weight: 600;
}

.value-unit {
  font-size: 12px;
  color: var(--neutral-500);
}

.result-row--missing .value-number {
  color: var(--neutral-400);
}

.delta-up {
  color: var(--danger-600, #d93025);
}

.delta-down {
  color: var(--success-600, #0f9d58);
}

.page-state {
  padding: 24px;
  text-align: center;
  border-radius: var(--radius);
}

.page-state.error {
  color: var(--danger-600, #d93025);
  background: var(--danger-50, #fdeaea);
}

.page-state.muted {
  color: var(--neutral-500);
}

.info-banner {
  padding: 12px 16px;
  border-radius: var(--radius);
  background: var(--primary-50);
  color: var(--primary-700);
  font-size: 14px;
  margin-bottom: 12px;
}

.btn.xs {
  font-size: 12px;
  padding: 4px 10px;
}
</style>
