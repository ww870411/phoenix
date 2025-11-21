<template>
  <div>
    <AppHeader />
    <div class="container">
    <Breadcrumbs :items="breadcrumbItems" class="breadcrumb-spacing" />
    <transition name="submit-feedback-fade">
      <div
        v-if="submitFeedback.visible"
        :class="['submit-feedback', `submit-feedback--${submitFeedback.type}`]"
        role="status"
        aria-live="polite"
      >
        <span>{{ submitFeedback.message }}</span>
        <span v-if="refreshCountdown > 0" class="submit-countdown">（{{ refreshCountdown }} 秒后自动刷新）</span>
      </div>
    </transition>
    <header class="topbar">
      <div style="display:flex;flex-direction:column;gap:6px;">
        <h2>数据填报</h2>
        <div class="sub">项目：{{ projectName }} ｜ 表：{{ sheetDisplayName }}</div>
      </div>
      <div class="right" style="display:flex;align-items:center;gap:8px;">
        <span class="submit-time" v-if="submitTime">最近提交：{{ submitTime }}</span>
        <input
          v-if="shouldShowSheetValidationToggle"
          type="checkbox"
          class="sheet-validation-toggle"
          :checked="sheetValidationEnabled"
          :disabled="sheetValidationToggleDisabled"
          aria-label="表级校验开关"
          @change="onSheetValidationToggle"
        />
        <label v-if="isDailyPage" class="date-group" title="业务日期" style="display:inline-flex;align-items:center;gap:6px;margin-right:8px;">
          <span>业务日期：</span>
          <input type="date" v-model="bizDate" />
        </label>
        <button class="btn ghost" type="button" @click="reloadTemplate()">重载模板</button>
        <button class="btn primary" type="button" :disabled="submitButtonDisabled" @click="onSubmit">提交</button>
      </div>
    </header>

    <section
      v-if="validationEnabled && validationIssues.length"
      class="validation-panel card"
      role="alert"
      aria-live="assertive"
    >
      <div class="validation-panel__header">
        <strong>校验提醒</strong>
        <span class="validation-panel__hint" v-if="hasBlockingValidation">（存在需修正的错误，提交按钮已锁定）</span>
        <span class="validation-panel__hint" v-else>（存在提示信息，建议确认后再提交）</span>
      </div>
      <ul class="validation-panel__list">
        <li
          v-for="issue in validationIssues"
          :key="issue.id"
          :class="['validation-panel__item', `validation-panel__item--${issue.level}`]"
        >
          <span class="validation-panel__badge">{{ issue.level === 'warning' ? '提示' : '错误' }}</span>
          <span class="validation-panel__label">{{ issue.rowLabel }} · {{ issue.columnLabel }}</span>
          <span class="validation-panel__message">{{ issue.message }}</span>
        </li>
      </ul>
    </section>

    <div class="table-wrap card" v-if="columns.length">
      <RevoGrid
        ref="gridRef"
        :row-headers="true"
        :hide-attribution="true"
        :stretch="gridStretch"
        :auto-size-column="false"
        :row-size="30"
        :resize="true"
        :range="true"
        :apply-on-close="true"
        :columns="gridColumns"
        :source="gridSource"
        style="height: 70vh; width: 100%;"
        @afteredit="handleAfterEdit"
        @afterEdit="handleAfterEdit"
      />
    </div>
    <div v-else class="placeholder">无模板数据</div>

    <section class="analysis-lite card">
      <header class="analysis-lite__header">
        <div>
          <h3>本单位数据分析（仅当前单位）</h3>
          <p class="analysis-lite__hint">默认折叠，展开后按时间段生成汇总对比</p>
        </div>
        <div class="analysis-lite__actions">
          <button class="btn ghost" type="button" @click="toggleAnalysisFold">
            {{ analysisFolded ? '展开' : '收起' }}
          </button>
          <button
            class="btn ghost"
            type="button"
            :disabled="analysisResult.rows.length === 0"
            @click="downloadAnalysisExcel"
          >
            导出本单位汇总
          </button>
        </div>
      </header>

      <div v-if="analysisFolded" class="analysis-lite__fold-hint">
        点击“展开”即可针对当前单位（{{ unitName || unitId || '未知单位' }}）按时间段生成汇总对比。
      </div>

      <div v-else class="analysis-lite__body">
        <div v-if="analysisSchemaLoading" class="page-state">分析配置加载中…</div>
        <div v-else-if="analysisSchemaError" class="page-state error">{{ analysisSchemaError }}</div>
        <template v-else>
          <div class="analysis-lite__form">
            <div class="analysis-lite__field">
              <label>时间范围（累计）</label>
              <div class="analysis-lite__dates">
                <input type="date" v-model="analysisStartDate" />
                <span>~</span>
                <input type="date" v-model="analysisEndDate" />
              </div>
            </div>
          <div class="analysis-lite__field">
            <div class="analysis-lite__field-header">
              <label>指标选择（多选）</label>
              <div class="analysis-lite__field-actions">
                <button class="btn ghost xs" type="button" @click="selectAllAnalysisMetrics">全选</button>
                <button class="btn ghost xs" type="button" @click="clearAnalysisMetrics">清空</button>
              </div>
            </div>
            <div v-if="analysisMetricGroups.length" class="analysis-lite__grid">
              <div
                v-for="group in analysisMetricGroups"
                :key="`metric-group-${group.key}`"
                class="analysis-lite__group-card"
              >
                <div class="analysis-lite__group-header">
                  <strong>{{ group.label || '指标' }}</strong>
                  <span class="analysis-lite__hint">共 {{ (group.options || []).length }} 项</span>
                </div>
                <div class="analysis-lite__metrics-grid">
                  <label
                    v-for="metric in group.options"
                    :key="`metric-${group.key}-${metric.value}`"
                    class="chip checkbox"
                  >
                    <input
                      type="checkbox"
                      :value="metric.value"
                      :checked="selectedMetricKeys.has(metric.value)"
                      @change="toggleAnalysisMetric(metric.value)"
                    />
                    <span class="chip-label">
                      <span
                        v-if="getAnalysisMetricSelectionOrder(metric.value)"
                        class="chip-order"
                      >
                        {{ getAnalysisMetricSelectionOrder(metric.value) }}
                      </span>
                      <span>{{ metric.label }}</span>
                    </span>
                  </label>
                </div>
              </div>
            </div>
            <div v-else-if="analysisMetricOptions.length" class="analysis-lite__metrics-grid">
              <label
                v-for="metric in analysisMetricOptions"
                :key="`metric-${metric.value}`"
                class="chip checkbox"
              >
                <input
                  type="checkbox"
                  :value="metric.value"
                  :checked="selectedMetricKeys.has(metric.value)"
                  @change="toggleAnalysisMetric(metric.value)"
                />
                <span class="chip-label">
                  <span
                    v-if="getAnalysisMetricSelectionOrder(metric.value)"
                    class="chip-order"
                  >
                    {{ getAnalysisMetricSelectionOrder(metric.value) }}
                  </span>
                  <span>{{ metric.label }}</span>
                </span>
              </label>
            </div>
            <p v-else class="analysis-lite__hint">暂无可选指标，请检查数据分析配置。</p>
          </div>
            <div class="analysis-lite__form-actions">
              <button class="btn primary" type="button" :disabled="analysisLoading" @click="runUnitAnalysis">
                {{ analysisLoading ? '生成中…' : '生成汇总对比' }}
              </button>
              <span class="analysis-lite__unit-label">当前单位：{{ unitName || unitId || '未知' }}</span>
            </div>
          </div>

          <div v-if="analysisFormError" class="page-state error">{{ analysisFormError }}</div>
          <div v-else-if="analysisLoading" class="page-state">正在生成汇总，请稍候…</div>
          <div v-else-if="!analysisResult.rows.length" class="page-state muted">
            运行后将在此显示本单位的汇总对比结果。
          </div>
          <div v-else class="analysis-lite__result">
            <div v-if="analysisResult.warnings.length" class="analysis-lite__warnings">
              <strong>提示：</strong>
              <ul>
                <li v-for="(warn, i) in analysisResult.warnings" :key="`warn-${i}`">{{ warn }}</li>
              </ul>
            </div>
            <table class="analysis-lite__table">
              <colgroup>
                <col style="width: 32%;" />
                <col style="width: 22%;" />
                <col style="width: 22%;" />
                <col style="width: 24%;" />
              </colgroup>
              <thead>
                <tr>
                  <th>指标</th>
                  <th>本期</th>
                  <th>同期</th>
                  <th>同比</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in analysisResult.rows" :key="row.key">
                  <td class="analysis-lite__metric">{{ row.label }}</td>
                <td>
                  <div class="analysis-lite__value">
                    <span class="analysis-lite__number">{{ formatNumber(row.total_current ?? row.current, row.decimals || 2) }}</span>
                    <span v-if="row.unit" class="analysis-lite__unit">{{ row.unit }}</span>
                  </div>
                </td>
                <td>
                  <div class="analysis-lite__value">
                    <span class="analysis-lite__number">{{ formatNumber(row.total_peer ?? row.peer, row.decimals || 2) }}</span>
                    <span v-if="row.unit" class="analysis-lite__unit">{{ row.unit }}</span>
                  </div>
                </td>
                <td :class="resolveDeltaClass(row)">
                  {{ formatDelta(resolveRowDelta(row)) }}
                </td>
              </tr>
              </tbody>
            </table>
            <section v-if="hasTimelineData" class="analysis-lite__timeline">
              <header class="analysis-lite__timeline-header">
                <div>
                  <h3>区间明细（逐日）</h3>
                  <p class="analysis-lite__hint">展示所选指标的逐日数据与趋势</p>
                </div>
              </header>
              <div v-if="analysisTimelineMetrics.length" class="analysis-lite__timeline-metrics">
                <button
                  v-for="metric in analysisTimelineMetrics"
                  :key="`timeline-chip-${metric.key}`"
                  type="button"
                  class="chip chip--toggle"
                  :class="{ active: activeTimelineMetricKeys.includes(metric.key) }"
                  @click="toggleTimelineMetric(metric.key)"
                >
                  <span>{{ metric.label }}</span>
                  <span v-if="metric.unit" class="chip-hint">（{{ metric.unit }}）</span>
                </button>
              </div>
              <div class="analysis-lite__timeline-grid">
                <RevoGrid
                  class="timeline-grid"
                  theme="material"
                  :readonly="true"
                  :columns="analysisTimelineGrid.columns"
                  :source="analysisTimelineGrid.rows"
                  :autoSizeColumn="true"
                  :rowSize="30"
                />
              </div>
              <div class="analysis-lite__timeline-chart">
                <TrendChart v-if="timelineChartOption" :option="timelineChartOption" height="360px" />
                <div v-else class="page-state muted">请选择至少一个包含逐日数据的指标生成趋势图</div>
              </div>
            </section>
          </div>
        </template>
      </div>
    </section>
  </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import RevoGrid from '@revolist/vue3-datagrid'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { useRouter, useRoute } from 'vue-router'
import { computed, defineComponent, h, nextTick, onBeforeUnmount, onMounted, reactive, ref, shallowRef, watch } from 'vue'
import {
  getTemplate,
  queryData,
  submitData,
  getSheetValidationSwitch,
  setSheetValidationSwitch,
  getUnitAnalysisMetrics,
  runDataAnalysis,
  getDashboardBizDate,
} from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'
import { useTemplatePlaceholders } from '../composables/useTemplatePlaceholders'
import { useAuthStore } from '../store/auth'
import * as XLSX from 'xlsx'

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
      if (!container.value || !window.echarts) return
      if (!chart.value) {
        chart.value = window.echarts.init(container.value)
      }
      if (latestOption.value) {
        chart.value.setOption(latestOption.value, { notMerge: true, lazyUpdate: false })
      }
    }

    const handleResize = () => {
      if (chart.value) chart.value.resize()
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

// --- 基本路由和状态 --- 
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { applyTemplatePlaceholders } = useTemplatePlaceholders()
const projectKey = String(route.params.projectKey ?? '')
const pageKey = String(route.params.pageKey ?? '')
const sheetKey = String(route.params.sheetKey ?? '')
const pageConfig = computed(() => {
  const raw = route.query.config;
  return typeof raw === 'string' ? raw : '';
});
const pageDisplayName = computed(() => {
  const raw = route.query.pageName;
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim();
  }
  return pageKey || '页面';
});

// 是否为“每日数据填报页面”
const isDailyPage = computed(() => {
  const name = pageDisplayName.value || ''
  return name.includes('每日数据填报')
});

const userGroup = computed(() => auth.user?.group ?? '')
const normalizedGroup = computed(() => userGroup.value.toLowerCase())
const isUnitScopedEditor = computed(() => normalizedGroup.value === 'unit_admin' || normalizedGroup.value === 'unit_filler')
const analysisMetricGroups = computed(() => analysisSchema.value?.groups || []);
const analysisMetricOptions = computed(() => {
  if (!analysisMetricGroups.value.length) {
    return (analysisSchema.value?.options || []).slice().sort((a, b) => (a.label || '').localeCompare(b.label || ''));
  }
  return analysisMetricGroups.value.flatMap((group) =>
    (group.options || []).slice().sort((a, b) => (a.label || '').localeCompare(b.label || '')),
  );
});

function formatDateYYYYMMDD(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return String(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

function peerDateYYYYMMDD(dateStr) {
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return ''
  d.setFullYear(d.getFullYear() - 1)
  return formatDateYYYYMMDD(d.toISOString().slice(0, 10))
}

function replaceDatePlaceholdersInColumns(cols) {
  if (!Array.isArray(cols)) return cols
  const main = formatDateYYYYMMDD(bizDate.value)
  const peer = peerDateYYYYMMDD(bizDate.value)
  return cols.map((name) => {
    const s = String(name ?? '')
    return s
      .replace(/\(本期日\)|本期日|\(本期\)|本期/g, main || '本期')
      .replace(/\(同期日\)|同期日|\(同期\)|同期/g, peer || '同期')
  })
}
// 默认业务日期使用本地“昨日”，避免 UTC 偏移导致初次查询当天无数据
function formatLocalYYYYMMDD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
function computeDefaultBizDate() {
  const now = new Date();
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  d.setDate(d.getDate() - 1);
  return formatLocalYYYYMMDD(d);
}
const initialDate = computeDefaultBizDate();
const canonicalBizDate = ref(String(initialDate));
const bizDate = ref(String(initialDate));
const latestRequestId = ref('');
function newRequestId() { return `${Date.now()}_${Math.random().toString(36).slice(2,8)}` }
// 在模板加载过程中，抑制由程序性设置 bizDate 引发的 watch 重入
const isLoadingTemplate = ref(false);

// --- 本单位分析（轻量版） ---
function toggleAnalysisFold() {
  analysisFolded.value = !analysisFolded.value;
  if (!analysisFolded.value) {
    ensureAnalysisDefaultDates();
    ensureAnalysisSchema();
  }
}

function shiftDateByDays(dateStr, offsetDays) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return '';
  date.setDate(date.getDate() + offsetDays);
  return formatLocalYYYYMMDD(date);
}

function applyAnalysisDateWindow(endDate) {
  if (!endDate) return;
  const normalizedEnd = formatDateYYYYMMDD(endDate) || endDate;
  const start = shiftDateByDays(normalizedEnd, -6) || normalizedEnd;
  analysisStartDate.value = start;
  analysisEndDate.value = normalizedEnd;
}

async function loadAnalysisDefaultBizDate() {
  if (analysisDefaultBizDate.value) {
    return analysisDefaultBizDate.value;
  }
  try {
    const payload = await getDashboardBizDate(projectKey);
    const value = typeof payload?.set_biz_date === 'string' ? payload.set_biz_date.trim() : '';
    if (value) {
      analysisDefaultBizDate.value = value;
      return analysisDefaultBizDate.value;
    }
  } catch (err) {
    // 忽略，回退到当前业务日期
  }
  const fallback = bizDate.value || canonicalBizDate.value || initialDate;
  analysisDefaultBizDate.value = fallback;
  return fallback;
}

async function ensureAnalysisDefaultDates() {
  if (analysisDefaultDateApplied.value) return;
  const base = await loadAnalysisDefaultBizDate();
  applyAnalysisDateWindow(base);
  analysisDefaultDateApplied.value = true;
}

async function ensureAnalysisSchema() {
  if (analysisSchema.value || analysisSchemaLoading.value) return;
  analysisSchemaLoading.value = true;
  analysisSchemaError.value = '';
  try {
    const payload = await getUnitAnalysisMetrics(projectKey, {
      unit_key: unitId.value || sheetKey || '',
    });
    if (!payload?.ok) {
      throw new Error(payload?.message || '分析配置加载失败');
    }
    analysisSchema.value = payload;
    if (!selectedMetricKeys.value.size) {
      const defaultTemp = analysisTemperatureMetricKey.value;
      selectedMetricKeys.value = defaultTemp ? new Set([defaultTemp]) : new Set();
    }
  } catch (err) {
    analysisSchemaError.value = err instanceof Error ? err.message : '分析配置加载失败';
  } finally {
    analysisSchemaLoading.value = false;
  }
}

function toggleAnalysisMetric(key) {
  const next = new Set(selectedMetricKeys.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  selectedMetricKeys.value = next;
}

function getAnalysisMetricSelectionOrder(metricKey) {
  const order = Array.from(selectedMetricKeys.value);
  const index = order.indexOf(metricKey);
  if (index === -1) return '';
  return String(index + 1);
}

function selectAllAnalysisMetrics() {
  const next = new Set();
  analysisMetricOptions.value.forEach((item) => next.add(item.value));
  selectedMetricKeys.value = next;
}

function clearAnalysisMetrics() {
  selectedMetricKeys.value = new Set();
}

function resolveRowDelta(row) {
  if (row.total_delta !== undefined && row.total_delta !== null) return row.total_delta;
  return row.delta;
}

function resolveDeltaClass(row) {
  const delta = resolveRowDelta(row);
  if (delta === null || delta === undefined || Number.isNaN(Number(delta))) return '';
  return Number(delta) >= 0 ? 'delta-up' : 'delta-down';
}

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return '—';
  return num.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function formatDelta(value) {
  if (value === null || value === undefined) return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return '—';
  const sign = num > 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}%`;
}

function formatPercentValue(value) {
  if (value === null || value === undefined) return null;
  const num = Number(value);
  if (Number.isNaN(num)) return null;
  return `${num.toFixed(2)}%`;
}

function applyDecimals(value, decimals = 2) {
  if (value === null || value === undefined) return null;
  const num = Number(value);
  if (Number.isNaN(num)) return null;
  return Number(num.toFixed(decimals));
}

function createDeltaCellPayload(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return { text: '—', delta: null };
  }
  const deltaNumber = Number(value);
  return {
    text: formatPercentValue(deltaNumber) || '—',
    delta: deltaNumber,
  };
}

const timelineDeltaCellTemplate = (createElement, props) => {
  const rawValue = props?.model?.[props.prop];
  const text =
    typeof rawValue === 'object' && rawValue !== null
      ? rawValue.text ?? '—'
      : typeof rawValue === 'string'
        ? rawValue
        : '—';
  const deltaNumber =
    typeof rawValue === 'object' && rawValue !== null && typeof rawValue.delta === 'number'
      ? rawValue.delta
      : null;
  const style = { color: deltaNumber === null ? '#475569' : deltaNumber >= 0 ? '#b91c1c' : '#0f9d58' };
  return createElement('span', { style }, text || '—');
};

function normalizeAnalysisRows(rows) {
  if (!Array.isArray(rows)) return [];
  return rows.map((row) => ({
    ...row,
    decimals: metricDecimalsMap.value?.[row.key] ?? row.decimals ?? 2,
  }));
}

function toggleTimelineMetric(metricKey) {
  const list = [...activeTimelineMetricKeys.value];
  const index = list.indexOf(metricKey);
  if (index >= 0) {
    list.splice(index, 1);
  } else {
    list.push(metricKey);
  }
  activeTimelineMetricKeys.value = list;
}

function extractTimelineCellText(value) {
  if (value && typeof value === 'object') {
    return value.text ?? '';
  }
  return value ?? '';
}

function normalizeChartValue(value, decimals = 2) {
  if (value === null || value === undefined) return null;
  const num = Number(value);
  if (Number.isNaN(num)) return null;
  return Number(num.toFixed(decimals));
}

function withAlpha(hex, alpha) {
  if (typeof hex !== 'string' || !hex.startsWith('#')) return hex;
  const value = hex.slice(1);
  if (value.length !== 6) return hex;
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function formatChartDelta(entry) {
  if (!entry || entry.peer === null || entry.peer === undefined) return '';
  const current = Number(entry.current);
  const peer = Number(entry.peer);
  if (!Number.isFinite(current) || !Number.isFinite(peer) || peer === 0) {
    return '';
  }
  const delta = ((current - peer) / peer) * 100;
  if (!Number.isFinite(delta)) return '';
  const sign = delta >= 0 ? '+' : '';
  return `<span class="chart-tooltip__delta">${sign}${delta.toFixed(2)}%</span>`;
}

function isAnalysisTemperatureMetric(metric) {
  if (!metric) return false;
  if (analysisTemperatureMetricCandidates.value.includes(metric.key)) return true;
  if (metric.value_type === 'temperature') return true;
  const label = metric.label || '';
  return TEMPERATURE_KEYWORDS.some((keyword) => label.includes(keyword));
}

function assignTimelineAxisSlots(metrics, temperatureKey) {
  if (!Array.isArray(metrics) || !metrics.length) return [];
  const hasTemp = metrics.length >= 2 && metrics.some((metric) => {
    if (!metric) return false;
    if (temperatureKey && metric.key === temperatureKey) return true;
    return isAnalysisTemperatureMetric(metric);
  });
  return metrics.map((metric, index) => {
    const slot = { key: metric?.key || `__timeline_metric_${index}`, axis: 'left' };
    if (metrics.length >= 2) {
      if (hasTemp && isAnalysisTemperatureMetric(metric)) {
        slot.axis = 'right';
      } else if (!hasTemp && index >= 1) {
        slot.axis = 'right';
      }
    }
    return slot;
  });
}

function buildTimelineGrid(rows) {
  const dateSet = new Set();
  const metrics = [];
  rows.forEach((row) => {
    if (Array.isArray(row.timeline) && row.timeline.length) {
      metrics.push(row);
      row.timeline.forEach((entry) => {
        if (entry?.date) {
          dateSet.add(entry.date);
        }
      });
    }
  });
  const sortedDates = Array.from(dateSet).sort();
  if (!sortedDates.length || !metrics.length) {
    return { columns: [], rows: [] };
  }
  const metricState = metrics.map((row) => ({
    key: row.key,
    label: row.label,
    timeline: row.timeline,
    decimals: row.decimals ?? 2,
    valueType: row.value_type || 'analysis',
    totalCurrent: row.total_current ?? null,
    totalPeer: row.total_peer ?? null,
    sumCurrent: 0,
    sumPeer: 0,
  }));
  const columns = [{ prop: 'date', name: '日期', size: 110 }];
  metricState.forEach((row) => {
    columns.push({ prop: `${row.key}__current`, name: `${row.label}(本期)`, size: 140 });
    columns.push({ prop: `${row.key}__peer`, name: `${row.label}(同期)`, size: 140 });
    columns.push({
      prop: `${row.key}__delta`,
      name: `${row.label}(同比%)`,
      size: 120,
      cellTemplate: timelineDeltaCellTemplate,
    });
  });
  const gridRows = sortedDates.map((date) => {
    const record = { date };
    metricState.forEach((row) => {
      const entry = row.timeline.find((item) => item.date === date);
      const current = entry?.current ?? null;
      const peer = entry?.peer ?? null;
      if (current !== null) {
        row.sumCurrent += Number(current);
      }
      if (peer !== null) {
        row.sumPeer += Number(peer);
      }
      record[`${row.key}__current`] = current !== null ? applyDecimals(current, row.decimals) : null;
      record[`${row.key}__peer`] = peer !== null ? applyDecimals(peer, row.decimals) : null;
      const deltaValue =
        peer !== null && peer !== 0 && current !== null ? ((current - peer) / peer) * 100 : null;
      record[`${row.key}__delta`] = createDeltaCellPayload(deltaValue);
    });
    return record;
  });
  const totalRecord = { date: '总计' };
  metricState.forEach((row) => {
    let totalCurrent = row.totalCurrent;
    let totalPeer = row.totalPeer;
    if (totalCurrent == null) {
      if (row.valueType === 'constant' && row.timeline && row.timeline.length) {
        totalCurrent = row.timeline[0]?.current ?? null;
      } else {
        totalCurrent = row.sumCurrent || null;
      }
    }
    if (totalPeer == null) {
      if (row.valueType === 'constant' && row.timeline && row.timeline.length) {
        totalPeer = row.timeline[0]?.peer ?? null;
      } else {
        totalPeer = row.sumPeer || null;
      }
    }
    totalRecord[`${row.key}__current`] =
      totalCurrent !== null ? applyDecimals(totalCurrent, row.decimals) : null;
    totalRecord[`${row.key}__peer`] =
      totalPeer !== null ? applyDecimals(totalPeer, row.decimals) : null;
    const deltaValue =
      totalPeer !== null && totalPeer !== 0 && totalCurrent !== null
        ? ((totalCurrent - totalPeer) / totalPeer) * 100
        : null;
    totalRecord[`${row.key}__delta`] = createDeltaCellPayload(deltaValue);
  });
  gridRows.push(totalRecord);
  return { columns, rows: gridRows };
}

async function runUnitAnalysis() {
  analysisFormError.value = '';
  if (!analysisUnitKey.value) {
    analysisFormError.value = '缺少单位信息，无法生成分析。';
    return;
  }
  if (!selectedMetricKeys.value.size) {
    analysisFormError.value = '请至少选择一个指标。';
    return;
  }
  if (!analysisStartDate.value || !analysisEndDate.value) {
    analysisFormError.value = '请选择时间范围。';
    return;
  }
  const start = analysisStartDate.value;
  const end = analysisEndDate.value;
  if (start > end) {
    analysisFormError.value = '开始日期不能晚于结束日期。';
    return;
  }
  analysisLoading.value = true;
  analysisResult.value = { rows: [], warnings: [], meta: null };
  resetAnalysisTimeline();
  try {
    const payload = {
      unit_key: analysisUnitKey.value,
      metrics: Array.from(selectedMetricKeys.value),
      analysis_mode: 'range',
      start_date: start,
      end_date: end,
    };
    const response = await runDataAnalysis(projectKey, payload, {});
    if (!response?.ok) {
      throw new Error(response?.message || '分析生成失败');
    }
    const decoratedRows = normalizeAnalysisRows(response.rows);
    analysisResult.value = {
      rows: decoratedRows,
      warnings: Array.isArray(response.warnings) ? response.warnings : [],
      meta: {
        unit_label: response.unit_label || unitName.value || unitId.value,
        start_date: response.start_date || start,
        end_date: response.end_date || end,
      },
    };
    analysisTimelineGrid.value = buildTimelineGrid(decoratedRows);
    analysisTimelineMetrics.value = decoratedRows
      .filter((row) => Array.isArray(row.timeline) && row.timeline.length)
      .map((row) => ({
        key: row.key,
        label: row.label,
        unit: row.unit,
        decimals: row.decimals,
        value_type: row.value_type,
        timeline: row.timeline?.map((entry) => ({ ...entry })) || [],
      }));
  } catch (err) {
    analysisFormError.value = err instanceof Error ? err.message : '分析生成失败';
    resetAnalysisTimeline();
  } finally {
    analysisLoading.value = false;
  }
}

function buildAnalysisMetaRows() {
  const rows = analysisResult.value.rows || [];
  return [
    ['单位', analysisResult.value.meta?.unit_label || unitName.value || unitId.value || ''],
    ['开始日期', analysisResult.value.meta?.start_date || analysisStartDate.value || ''],
    ['结束日期', analysisResult.value.meta?.end_date || analysisEndDate.value || ''],
    ['指标数量', rows.length],
  ];
}

function buildAnalysisTimelineSheetData() {
  const columns = Array.isArray(analysisTimelineGrid.value?.columns)
    ? analysisTimelineGrid.value.columns
    : [];
  const rows = Array.isArray(analysisTimelineGrid.value?.rows) ? analysisTimelineGrid.value.rows : [];
  if (!columns.length || !rows.length) return null;
  const header = columns.map((column) => column.name || column.prop || '');
  const body = rows.map((record) =>
    columns.map((column) => extractTimelineCellText(record[column.prop])),
  );
  return [header, ...body];
}

function buildAnalysisSheetData() {
  const header = ['指标', '本期', '同期', '同比', '单位'];
  const rows = analysisResult.value.rows || [];
  const mapped = rows.map((row) => [
    row.label,
    row.total_current ?? row.current ?? '',
    row.total_peer ?? row.peer ?? '',
    formatDelta(resolveRowDelta(row)) || '',
    row.unit || '',
  ]);
  const result = [header, ...mapped];
  const timeline = buildAnalysisTimelineSheetData();
  if (timeline && timeline.length) {
    result.push([]);
    result.push(['区间明细']);
    timeline.forEach((row) => result.push(row));
  }
  result.push([]);
  result.push(['查询信息']);
  buildAnalysisMetaRows().forEach((row) => result.push(row));
  return result;
}

function downloadAnalysisExcel() {
  if (!analysisResult.value.rows.length) return;
  const wb = XLSX.utils.book_new();
  const sheet = XLSX.utils.aoa_to_sheet(buildAnalysisSheetData());
  XLSX.utils.book_append_sheet(wb, sheet, '本单位汇总');
  const filename = `本单位数据汇总_${analysisResult.value.meta?.unit_label || unitName.value || unitId.value || 'unit'}_${Date.now()}.xlsx`;
  XLSX.writeFile(wb, filename);
}

function resetAnalysisResult() {
  analysisResult.value = { rows: [], warnings: [], meta: null };
  analysisFormError.value = '';
  resetAnalysisTimeline();
}

function resetAnalysisTimeline() {
  analysisTimelineGrid.value = { columns: [], rows: [] };
  analysisTimelineMetrics.value = [];
  activeTimelineMetricKeys.value = [];
}

// --- 本单位分析（轻量版，默认折叠） ---
const analysisFolded = ref(true);
const analysisSchema = ref(null);
const analysisSchemaLoading = ref(false);
const analysisSchemaError = ref('');
const analysisStartDate = ref(bizDate.value);
const analysisEndDate = ref(bizDate.value);
const analysisDefaultBizDate = ref('');
const analysisDefaultDateApplied = ref(false);
const selectedMetricKeys = ref(new Set());
const analysisLoading = ref(false);
const analysisFormError = ref('');
const analysisResult = ref({ rows: [], warnings: [], meta: null });
const metricDecimalsMap = computed(() => analysisSchema.value?.decimals || {});
const analysisUnitKey = computed(() => analysisSchema.value?.unit_key || unitId.value || sheetKey || '');
const analysisTimelineGrid = ref({ columns: [], rows: [] });
const analysisTimelineMetrics = ref([]);
const activeTimelineMetricKeys = ref([]);
const hasTimelineData = computed(
  () =>
    Array.isArray(analysisTimelineGrid.value?.columns) &&
    analysisTimelineGrid.value.columns.length > 1 &&
    Array.isArray(analysisTimelineGrid.value?.rows) &&
    analysisTimelineGrid.value.rows.length > 0,
);
const timelinePalette = [
  { current: '#2563eb', peer: '#93c5fd' },
  { current: '#f97316', peer: '#fdba74' },
  { current: '#0ea5e9', peer: '#7dd3fc' },
  { current: '#a855f7', peer: '#d8b4fe' },
  { current: '#22c55e', peer: '#86efac' },
];
const TEMPERATURE_KEYWORDS = ['气温', '温度'];

const analysisTemperatureMetricCandidates = computed(() => {
  const groups = Array.isArray(analysisSchema.value?.groups) ? analysisSchema.value.groups : [];
  const candidates = [];
  groups.forEach((group) => {
    if (!group || group.key !== 'temperature') return;
    (group.options || []).forEach((option) => {
      if (option?.value) {
        candidates.push(option.value);
      }
    });
  });
  return Array.from(new Set(candidates));
});
const analysisTemperatureMetricKey = computed(() => analysisTemperatureMetricCandidates.value[0] || null);

const timelineCategories = computed(() =>
  analysisTimelineGrid.value.rows
    .filter((row) => row?.date && row.date !== '总计')
    .map((row) => row.date),
);

const analysisTimelineMetricMap = computed(() => {
  const map = new Map();
  analysisTimelineMetrics.value.forEach((metric) => {
    if (metric?.key) {
      map.set(metric.key, metric);
    }
  });
  return map;
});

const activeTimelineMetrics = computed(() =>
  activeTimelineMetricKeys.value.map((key) => analysisTimelineMetricMap.value.get(key)).filter(Boolean),
);

const timelineChartOption = computed(() => {
  const categories = timelineCategories.value;
  const metrics = activeTimelineMetrics.value;
  if (!categories.length || !metrics.length) return null;

  const series = [];
  const legend = [];
  const seriesMeta = {};
  const axisSlots = assignTimelineAxisSlots(metrics, analysisTemperatureMetricKey.value);
  const hasRightAxis = axisSlots.some((slot) => slot.axis === 'right');

  const makeAxisBase = () => ({
    type: 'value',
    axisLabel: { color: '#475569' },
    splitLine: { lineStyle: { type: 'dashed', color: 'rgba(148, 163, 184, 0.35)' } },
  });

  const yAxis = hasRightAxis
    ? [
        makeAxisBase(),
        {
          ...makeAxisBase(),
          position: 'right',
          axisLabel: { color: '#475569' },
        },
      ]
    : makeAxisBase();

  metrics.forEach((metric, index) => {
    if (!metric) return;
    const palette = timelinePalette[index % timelinePalette.length];
    const decimals = Number.isInteger(metric.decimals) ? metric.decimals : 2;
    const timelineMap = {};
    (metric.timeline || []).forEach((entry) => {
      if (entry?.date) {
        timelineMap[entry.date] = {
          current: normalizeChartValue(entry.current, decimals),
          peer: normalizeChartValue(entry.peer, decimals),
        };
      }
    });
    const currentName = `${metric.label}（本期）`;
    const peerName = `${metric.label}（同期）`;
    const currentData = categories.map((date) => timelineMap[date]?.current ?? null);
    const peerData = categories.map((date) => timelineMap[date]?.peer ?? null);
    const axisSlot = axisSlots[index] || { axis: 'left' };
    const yAxisIndex = hasRightAxis && axisSlot.axis === 'right' ? 1 : 0;

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
    });
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
    });
    legend.push(currentName, peerName);
    seriesMeta[currentName] = {
      unit: metric.unit || '',
      type: 'current',
      label: metric.label,
      getEntry: (date) => timelineMap[date],
    };
    seriesMeta[peerName] = {
      unit: metric.unit || '',
      type: 'peer',
      label: metric.label,
      getEntry: (date) => timelineMap[date],
    };
  });

  const tooltipFormatter = (params = []) => {
    if (!Array.isArray(params) || !params.length) return '';
    const dateLabel = params[0].axisValue ?? '';
    const lines = [`<div class="chart-tooltip__title">${dateLabel}</div>`];
    params.forEach((item) => {
      const meta = seriesMeta[item.seriesName] || {};
      const unit = meta.unit ? ` ${meta.unit}` : '';
      const value =
        item.data === null || item.data === undefined ? '—' : formatNumber(item.data, 2);
      const delta = meta.type === 'current' ? formatChartDelta(meta.getEntry?.(dateLabel)) : '';
      const colorChip =
        typeof item.color === 'string'
          ? item.color
          : Array.isArray(item.color)
            ? item.color[0]
            : '#2563eb';
      lines.push(
        `<div class="chart-tooltip__item"><span class="chart-tooltip__dot" style="background:${colorChip}"></span>${item.seriesName}：${value}${unit}${delta}</div>`,
      );
    });
    return lines.join('');
  };

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
    grid: { left: 48, right: 24, top: 72, bottom: 90 },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
        height: 18,
        bottom: 30,
        borderColor: 'transparent',
        backgroundColor: 'rgba(148, 163, 184, 0.15)',
      },
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
  };
});

if (!projectKey || !pageKey || !sheetKey || !pageConfig.value) {
  router.replace({ name: 'projects' });
}

// --- 模板和表格状态 ---
const projectName = computed(() => getProjectNameById(projectKey));
const sheetName = ref('');
const unitName = ref('');
const sheetDisplayName = computed(() => sheetName.value || sheetKey);

const pageListPath = computed(() => {
  const base = `/projects/${encodeURIComponent(projectKey)}/pages/${encodeURIComponent(pageKey)}/sheets`;
  const q = new URLSearchParams();
  if (pageConfig.value) q.set('config', pageConfig.value);
  if (pageDisplayName.value) q.set('pageName', pageDisplayName.value);
  const qs = q.toString();
  return qs ? `${base}?${qs}` : base;
});

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value || projectKey, to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: pageDisplayName.value, to: pageListPath.value },
  { label: sheetDisplayName.value, to: null },
]);
const unitId = ref('');
const columns = ref([]);
// 基准列缓存：保存“未替换占位符”的原始列头，便于日历变更时重新计算
const baseColumns = ref([]);
const rows = ref([]);
const templateType = ref('standard'); // 新增：模板类型
const templateDicts = ref({ entries: {}, itemPrimary: null, companyPrimary: null });
const submitTime = ref('');
const refreshCountdown = ref(0);
const linkageMap = ref(new Map());
let isApplyingLinkage = false;
const isSubmitting = ref(false);
const submitFeedback = reactive({
  visible: false,
  type: 'success',
  message: '',
});
let submitFeedbackTimer = null;
let refreshCountdownTimer = null;
// --- RevoGrid 状态 ---
const gridColumns = ref([]);
const gridSource = ref([]);
const gridRef = ref(null);
const readOnlyThreshold = ref(1);
const rowLabelIndex = ref(new Map());
const templateValidationRaw = ref(null);
const validationRuleMap = ref(new Map());
const validationDependents = ref(new Map());
const cellValidationMap = ref(new Map());
const virtualValidationRules = ref([]);
const validationEnabled = ref(true);
const sheetValidationEnabled = ref(true);
const sheetValidationLoading = ref(false);
const sheetValidationSaving = ref(false);
const sheetValidationError = ref('');
const validationExplanationMap = ref(new Map());
const validationIssues = computed(() => {
  if (!validationEnabled.value) {
    return [];
  }
  const issues = Array.from(cellValidationMap.value.values());
  return issues.sort((a, b) => {
    if (a.level !== b.level) {
      return a.level === 'error' ? -1 : 1;
    }
    if (a.rowIndex !== b.rowIndex) {
      return a.rowIndex - b.rowIndex;
    }
    if (a.colIndex !== b.colIndex) {
      return a.colIndex - b.colIndex;
    }
    return a.id.localeCompare(b.id);
  });
});
const explanationColumnIndex = computed(() => {
  if (!Array.isArray(columns.value)) return -1;
  for (let i = 0; i < columns.value.length; i += 1) {
    const label = columns.value[i];
    if (typeof label !== 'string') continue;
    const trimmed = label.trim();
    if (!trimmed) continue;
    if (trimmed.includes('解释说明') || trimmed.endsWith('说明')) {
      return i;
    }
  }
  return -1;
});

function resolveIssueExplanationRowIndex(issue) {
  if (issue && issue.rowIndex != null && issue.rowIndex >= 0) {
    return issue.rowIndex;
  }
  const map = validationExplanationMap.value;
  if (!(map instanceof Map) || map.size === 0) {
    return null;
  }
  const normalizedIssueLabel = normalizeRowLabelValue(issue?.rowLabel);
  if (!normalizedIssueLabel) {
    return null;
  }
  const mappedLabel = map.get(normalizedIssueLabel);
  if (!mappedLabel) {
    return null;
  }
  const normalizedMapped = normalizeRowLabelValue(mappedLabel);
  if (!normalizedMapped) {
    return null;
  }
  const targetIndex = rowLabelIndex.value?.get(normalizedMapped);
  return typeof targetIndex === 'number' ? targetIndex : null;
}

function isIssueExplained(issue) {
  if (!issue || issue.level !== 'error') {
    return false;
  }
  const explainCol = explanationColumnIndex.value;
  if (explainCol < 0) {
    return false;
  }
  const targetRowIdx = resolveIssueExplanationRowIndex(issue);
  if (targetRowIdx == null) {
    return false;
  }
  const record = Array.isArray(gridSource.value) ? gridSource.value[targetRowIdx] : null;
  if (!record) {
    return false;
  }
  const raw = record[`c${explainCol}`];
  if (raw == null) {
    return false;
  }
  const text = String(raw).trim();
  return text.length > 0;
}

const blockingValidationIssues = computed(() => {
  if (!validationEnabled.value) {
    return [];
  }
  return validationIssues.value.filter(
    issue => issue.level === 'error' && !isIssueExplained(issue),
  );
});

const hasBlockingValidation = computed(() => blockingValidationIssues.value.length > 0);
const shouldShowSheetValidationToggle = computed(() => sheetKey !== 'Coal_inventory_Sheet');
const canToggleSheetValidation = computed(() => auth.user?.group === 'Global_admin');
const sheetValidationToggleDisabled = computed(
  () =>
    !shouldShowSheetValidationToggle.value ||
    !canToggleSheetValidation.value ||
    sheetValidationLoading.value ||
    sheetValidationSaving.value,
);

const isReadOnlyForDate = computed(() => isDailyPage.value && isUnitScopedEditor.value && bizDate.value !== canonicalBizDate.value);
const submitDisabled = computed(() => isReadOnlyForDate.value);
const submitButtonDisabled = computed(() => submitDisabled.value || isSubmitting.value || hasBlockingValidation.value);

watch(
  () => isReadOnlyForDate.value,
  () => applyReadonlyToColumns()
);

// 根据模板类型控制列拉伸行为：常量指标页不拉伸，避免最后一列占满剩余空间
const gridStretch = computed(() => {
  return templateType.value !== 'constant'
});

// --- Helper --- 
function clearRefreshCountdown() {
  if (refreshCountdownTimer !== null) {
    clearInterval(refreshCountdownTimer);
    refreshCountdownTimer = null;
  }
  refreshCountdown.value = 0;
}

function cloneDictValue(value) {
  if (value && typeof value === 'object') {
    try { return JSON.parse(JSON.stringify(value)); } catch (err) { return value; }
  }
  return value;
}

function showSubmitFeedback(type, message, options = {}) {
  const { autoHide = true, duration = 3200 } = options;
  if (submitFeedbackTimer !== null) {
    clearTimeout(submitFeedbackTimer);
    submitFeedbackTimer = null;
  }
  if (autoHide) {
    clearRefreshCountdown();
  }
  submitFeedback.type = type;
  submitFeedback.message = message;
  submitFeedback.visible = true;
  if (autoHide) {
    submitFeedbackTimer = window.setTimeout(() => {
    submitFeedback.visible = false;
    submitFeedbackTimer = null;
  }, duration);
  }
}

function startRefreshCountdown(seconds) {
  clearRefreshCountdown();
  refreshCountdown.value = seconds;
  showSubmitFeedback('success', '提交成功，数据已入库！', { autoHide: false });
  refreshCountdownTimer = window.setInterval(() => {
    if (refreshCountdown.value > 1) {
      refreshCountdown.value -= 1;
      return;
    }
    clearRefreshCountdown();
    showSubmitFeedback('success', '正在刷新数据，请稍候…', { autoHide: false });
    reloadTemplate()
      .then(() => {
        showSubmitFeedback('success', `数据已刷新（业务日期：${bizDate.value}）。`, { autoHide: true, duration: 2600 });
      })
      .catch((err) => {
        const message = err instanceof Error ? err.message : String(err);
        showSubmitFeedback('error', `刷新失败：${message || '请手动刷新页面'}`);
      });
  }, 1000);
}

function normalizeDictPayload(raw) {
  const cloned = cloneDictValue(raw);
  if (!cloned) return null;
  if (Array.isArray(cloned)) {
    const converted = {};
    for (const entry of cloned) {
      if (!entry) continue;
      if (Array.isArray(entry) && entry.length >= 2) {
        converted[String(entry[0])] = entry[1];
      } else if (typeof entry === 'object') {
        for (const [innerKey, innerValue] of Object.entries(entry)) {
          converted[String(innerKey)] = innerValue;
        }
      }
    }
    return Object.keys(converted).length ? converted : null;
  }
  if (typeof cloned === 'object') {
    return cloned;
  }
  return null;
}

function normalizeExplanationMapping(raw) {
  const map = new Map();
  if (!raw || typeof raw !== 'object') {
    return map;
  }
  Object.entries(raw).forEach(([ruleLabel, explanationLabel]) => {
    const normalizedRule = normalizeRowLabelValue(ruleLabel);
    const normalizedExplanation = normalizeRowLabelValue(explanationLabel);
    if (normalizedRule && normalizedExplanation) {
      map.set(normalizedRule, normalizedExplanation);
    }
  });
  return map;
}

function resolveValidationEnabledFlag(payload) {
  if (!payload || typeof payload !== 'object') return true;
  const keys = ['validation_enabled', 'enable_validation', '校验开关'];
  for (const key of keys) {
    if (!Object.prototype.hasOwnProperty.call(payload, key)) continue;
    const raw = payload[key];
    if (typeof raw === 'boolean') return raw;
    if (typeof raw === 'number') return Boolean(raw);
    if (typeof raw === 'string') {
      const lowered = raw.trim().toLowerCase();
      if (['false', '0', 'no', 'off'].includes(lowered)) return false;
      if (['true', '1', 'yes', 'on'].includes(lowered)) return true;
    }
  }
  return true;
}

function pickLinkageDict(source) {
  if (!source || typeof source !== 'object') return null;
  if (source.linkage_dict && typeof source.linkage_dict === 'object') {
    return source.linkage_dict;
  }
  if (source.entries && typeof source.entries === 'object') {
    const nested = source.entries.linkage_dict;
    if (nested && typeof nested === 'object') {
      return nested;
    }
  }
  if (source['指标联动'] && typeof source['指标联动'] === 'object') {
    return source['指标联动'];
  }
  return null;
}

function ensureLinkedRowsAligned() {
  const map = linkageMap.value;
  if (!(map instanceof Map) || map.size === 0) return;
  if (!Array.isArray(gridSource.value) || !Array.isArray(columns.value)) return;
  const readonlyLimit = resolveReadonlyLimit(columns.value);
  const startCol = Math.max(readonlyLimit + 1, 2);
  const totalColumns = columns.value.length;
  if (startCol >= totalColumns) return;
  const updatedRows = new Set();
  const processedPairs = new Set();
  map.forEach((neighbors, srcIdx) => {
    const sourceRow = gridSource.value?.[srcIdx];
    if (!sourceRow) return;
    neighbors.forEach((dstIdx) => {
      const targetRow = gridSource.value?.[dstIdx];
      if (!targetRow) return;
      const pairKey = srcIdx < dstIdx ? `${srcIdx}-${dstIdx}` : `${dstIdx}-${srcIdx}`;
      if (processedPairs.has(pairKey)) return;
      processedPairs.add(pairKey);
      for (let col = startCol; col < totalColumns; col += 1) {
        const propKey = `c${col}`;
        targetRow[propKey] = sourceRow[propKey];
      }
      updatedRows.add(srcIdx);
      updatedRows.add(dstIdx);
    });
  });
  if (updatedRows.size > 0) {
    gridSource.value = gridSource.value.map((row, idx) => {
      if (!updatedRows.has(idx)) return row;
      if (row && typeof row === 'object') {
        return { ...row };
      }
      return row ?? {};
    });
    if (validationEnabled.value) {
      runFullValidation();
    }
  }
}

function rebuildLinkageMapFromPayload(rowsCandidate, dictSource, options = {}) {
  const { syncGrid = false } = options;
  const map = new Map();
  const linkage = pickLinkageDict(dictSource);
  const rowsArray = Array.isArray(rowsCandidate) ? rowsCandidate : [];
  if (linkage && rowsArray.length) {
    const labelIndex = new Map();
    rowsArray.forEach((row, idx) => {
      if (!Array.isArray(row)) return;
      const rawLabel = row[0];
      const label = typeof rawLabel === 'string'
        ? rawLabel.trim()
        : rawLabel != null
          ? String(rawLabel).trim()
          : '';
      if (label) {
        labelIndex.set(label, idx);
      }
    });
    Object.entries(linkage).forEach(([srcLabelRaw, targetsRaw]) => {
      const srcLabel = (srcLabelRaw ?? '').toString().trim();
      if (!srcLabel) return;
      const srcIdx = labelIndex.get(srcLabel);
      if (srcIdx == null) return;
      const targets = Array.isArray(targetsRaw) ? targetsRaw : [targetsRaw];
      targets.forEach((targetLabelRaw) => {
        const targetLabel = (targetLabelRaw ?? '').toString().trim();
        if (!targetLabel) return;
        const targetIdx = labelIndex.get(targetLabel);
        if (targetIdx == null) return;
        if (!map.has(srcIdx)) map.set(srcIdx, new Set());
        map.get(srcIdx).add(targetIdx);
        if (!map.has(targetIdx)) map.set(targetIdx, new Set());
        map.get(targetIdx).add(srcIdx);
      });
    });
  }
  linkageMap.value = map;
  if (syncGrid) {
    ensureLinkedRowsAligned();
  }
}

// --- 数据校验 ---
function normalizeRowLabelValue(label) {
  if (label == null) return '';
  if (typeof label === 'string') return label.trim();
  return String(label).trim();
}

function getRowLabelByIndex(rowIdx) {
  const row = rows.value?.[rowIdx];
  const raw = Array.isArray(row) ? row[0] : row?.c0;
  const normalized = normalizeRowLabelValue(raw);
  return normalized || `第 ${rowIdx + 1} 行`;
}

function getColumnLabel(colIdx) {
  if (!Array.isArray(columns.value)) return `列 ${colIdx + 1}`;
  const raw = columns.value[colIdx];
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim();
  }
  return `列 ${colIdx + 1}`;
}

function getDefaultDataColumnsIndexes() {
  if (!Array.isArray(columns.value) || !columns.value.length) return [];
  const total = columns.value.length;
  const start = Math.max(readOnlyThreshold.value + 1, 2);
  const result = [];
  for (let ci = start; ci < total; ci += 1) {
    result.push(ci);
  }
  return result;
}

function getRowIndexByLabel(label) {
  if (!label) return null;
  const normalized = normalizeRowLabelValue(label);
  if (!normalized) return null;
  return rowLabelIndex.value.get(normalized);
}

function getRowValueByLabel(label, columnIndex) {
  const rowIdx = getRowIndexByLabel(label);
  if (rowIdx == null) return null;
  return getCellNumericValue(rowIdx, columnIndex);
}

function parseNumericValue(value) {
  if (value == null) return null;
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  const str = String(value).trim();
  if (!str) return null;
  const normalized = str.replace(/[,，]/g, '').replace(/％$/, '');
  if (!normalized) return null;
  const num = Number(normalized);
  return Number.isFinite(num) ? num : null;
}

function formatNumericDisplay(value, options = {}) {
  const num = Number(value);
  if (!Number.isFinite(num)) return '';
  const { maximumFractionDigits = Math.abs(num) >= 1 ? 2 : 4 } = options;
  try {
    return num.toLocaleString('zh-CN', {
      minimumFractionDigits: 0,
      maximumFractionDigits,
    });
  } catch {
    const digits = Math.min(Math.max(maximumFractionDigits, 0), 6);
    return num.toFixed(digits);
  }
}

function formatViolationDetail(rule, violation) {
  if (!violation) return '';
  const parts = [];
  if (typeof violation.cellValue === 'number' && Number.isFinite(violation.cellValue)) {
    parts.push(`当前值：${formatNumericDisplay(violation.cellValue)}`);
  }
  const isExpressionReason = typeof violation.reason === 'string' && violation.reason.startsWith('expression');
  if (isExpressionReason && typeof violation.actual === 'number' && Number.isFinite(violation.actual)) {
    parts.push(`计算结果：${formatNumericDisplay(violation.actual)}`);
  }
  const isRatioReason = typeof violation.reason === 'string' && violation.reason.includes('ratio');
  if (isRatioReason && typeof violation.actual === 'number' && Number.isFinite(violation.actual)) {
    parts.push(`当前比例：${formatNumericDisplay(violation.actual, { maximumFractionDigits: 4 })}`);
  }
  if (typeof violation.referenceValue === 'number' && Number.isFinite(violation.referenceValue)) {
    const refLabel = violation.referenceColumnLabel || rule.referenceLabel || '参照值';
    parts.push(`${refLabel}：${formatNumericDisplay(violation.referenceValue)}`);
  }
  if (!parts.length && typeof violation.actual === 'number' && Number.isFinite(violation.actual)) {
    parts.push(`当前值：${formatNumericDisplay(violation.actual)}`);
  }
  return parts.length ? `（${parts.join('，')}）` : '';
}

function compileRuleExpression(expression) {
  if (!expression || typeof expression !== 'string') return null;
  try {
    const fn = new Function(
      'ctx',
      `
        const { value, columnIndex } = ctx;
        return (${expression});
      `
    );
    return (ctx) => {
      try {
        const result = fn(ctx || {});
        if (typeof result === 'number' && Number.isFinite(result)) {
          return result;
        }
        return null;
      } catch {
        return null;
      }
    };
  } catch {
    return null;
  }
}

function evaluateExpressionRule(rule, columnIndex) {
  if (!rule || typeof rule.compiledExpression !== 'function') return null;
  const evaluator = rule.compiledExpression;
  const ctx = {
    columnIndex,
    value: (label, overrideColumn) => {
      const targetColumn = typeof overrideColumn === 'number' ? overrideColumn : columnIndex;
      return getRowValueByLabel(label, targetColumn);
    },
  };
  const result = evaluator(ctx);
  if (typeof result === 'number' && Number.isFinite(result)) {
    return result;
  }
  return parseNumericValue(result);
}

function getCellNumericValue(rowIdx, colIdx) {
  const record = Array.isArray(gridSource.value) ? gridSource.value[rowIdx] : null;
  if (!record) return null;
  const prop = `c${colIdx}`;
  const raw = record[prop];
  return parseNumericValue(raw);
}

function getRuleColumns(rule) {
  if (rule && Array.isArray(rule.columns) && rule.columns.length) {
    return rule.columns;
  }
  return getDefaultDataColumnsIndexes();
}

function collectRuleIssues(rule, rowIdx) {
  const issues = [];
  const columns = getRuleColumns(rule);
  const targetRowIdx = typeof rowIdx === 'number' ? rowIdx : (typeof rule.rowIndex === 'number' ? rule.rowIndex : null);
  const rowLabel = targetRowIdx != null ? getRowLabelByIndex(targetRowIdx) : (rule.targetLabel || '系统校验');
  columns.forEach((colIdx) => {
    const violation = evaluateRule(rule, targetRowIdx, colIdx);
    if (!violation) return;
    const columnLabel = getColumnLabel(colIdx);
    const baseMessage = rule.message || buildDefaultRuleMessage(rule, columnLabel, violation);
    const detail = formatViolationDetail(rule, violation);
    const message = detail ? `${baseMessage}${detail}` : baseMessage;
    const keyPrefix = targetRowIdx != null ? `${targetRowIdx}` : `virtual:${rule.id}`;
    const key = `${keyPrefix}:${colIdx}:${rule.id}`;
    issues.push({
      key,
      issue: {
        id: key,
        rowIndex: targetRowIdx ?? -1,
        colIndex: colIdx,
        rowLabel,
        columnLabel,
        level: rule.level,
        message: message || `${columnLabel} 未通过校验`,
      },
    });
  });
  return issues;
}

function clearIssuesByPrefix(map, prefix) {
  if (!map || !map.size) return { map, mutated: false };
  const next = new Map();
  let mutated = false;
  map.forEach((value, key) => {
    if (key.startsWith(prefix)) {
      mutated = true;
      return;
    }
    next.set(key, value);
  });
  return { map: mutated ? next : map, mutated };
}

function applyIssues(map, issues) {
  if (!issues.length) return { map, mutated: false };
  const next = map instanceof Map ? new Map(map) : new Map();
  issues.forEach(({ key, issue }) => {
    next.set(key, issue);
  });
  return { map: next, mutated: true };
}

function revalidateVirtualRulesForRow(rowIdx, workingMap = cellValidationMap.value) {
  if (!validationEnabled.value || !Array.isArray(virtualValidationRules.value) || !virtualValidationRules.value.length) {
    return { map: workingMap, mutated: false };
  }
  const targetRules = virtualValidationRules.value.filter(rule => rule.dependencies?.has(rowIdx));
  if (!targetRules.length) return { map: workingMap, mutated: false };
  let currentMap = workingMap instanceof Map ? workingMap : new Map();
  let mutated = false;
  targetRules.forEach((rule) => {
    const prefix = `virtual:${rule.id}:`;
    const cleared = clearIssuesByPrefix(currentMap, prefix);
    currentMap = cleared.map;
    mutated = mutated || cleared.mutated;
    const issues = collectRuleIssues(rule, null);
    const applied = applyIssues(currentMap, issues);
    currentMap = applied.map;
    mutated = mutated || applied.mutated;
  });
  return { map: currentMap, mutated };
}

function registerRowDependency(dependentsMap, dependencyIdx, targetRowIdx) {
  if (dependencyIdx == null || targetRowIdx == null) {
    return;
  }
  if (!dependentsMap.has(dependencyIdx)) {
    dependentsMap.set(dependencyIdx, new Set());
  }
  dependentsMap.get(dependencyIdx).add(targetRowIdx);
}

function clearAllValidationIssues() {
  if (cellValidationMap.value.size) {
    cellValidationMap.value = new Map();
  }
}

function rebuildValidationRulesFromRows(rowsPayload = rows.value) {
  if (!validationEnabled.value || templateType.value !== 'standard') {
    validationRuleMap.value = new Map();
    validationDependents.value = new Map();
    virtualValidationRules.value = [];
    clearAllValidationIssues();
    return;
  }
  const rawRules = templateValidationRaw.value;
  if (!rawRules || typeof rawRules !== 'object' || !Array.isArray(rowsPayload)) {
    validationRuleMap.value = new Map();
    validationDependents.value = new Map();
    virtualValidationRules.value = [];
    clearAllValidationIssues();
    return;
  }
  const labelIndex = new Map();
  rowsPayload.forEach((row, idx) => {
    const label = Array.isArray(row) ? row[0] : row?.c0;
    const normalized = normalizeRowLabelValue(label);
    if (normalized) {
      labelIndex.set(normalized, idx);
    }
  });
  rowLabelIndex.value = labelIndex;
  const totalColumns = Array.isArray(columns.value) ? columns.value.length : 0;
  const defaultColumns = getDefaultDataColumnsIndexes();
  const ruleMap = new Map();
  const dependents = new Map();
  const virtualRules = [];
  let ruleSerial = 0;
  Object.entries(rawRules).forEach(([rawLabel, definitions]) => {
    const normalizedLabel = normalizeRowLabelValue(rawLabel);
    if (!normalizedLabel) return;
    const rowIdx = labelIndex.get(normalizedLabel);
    const list = Array.isArray(definitions) ? definitions : [definitions];
    list.forEach((definition) => {
      if (!definition || typeof definition !== 'object') return;
      ruleSerial += 1;
      const normalizedRule = normalizeRuleDefinition(definition, {
        rowIdx,
        totalColumns,
        defaultColumns,
        labelIndex,
        ruleId: `rule_${rowIdx ?? 'virtual'}_${ruleSerial}`,
        ruleLabel: normalizedLabel,
      });
      if (!normalizedRule) return;
      if (normalizedRule.virtual && normalizedRule.rowIndex == null) {
        normalizedRule.targetLabel = normalizedRule.targetLabel || normalizedLabel || normalizedRule.id;
        virtualRules.push(normalizedRule);
        return;
      }
      const targetRowIdx = normalizedRule.rowIndex != null ? normalizedRule.rowIndex : rowIdx;
      if (targetRowIdx == null) {
        normalizedRule.targetLabel = normalizedRule.targetLabel || normalizedLabel || normalizedRule.id;
        virtualRules.push(normalizedRule);
        return;
      }
      if (!ruleMap.has(targetRowIdx)) {
        ruleMap.set(targetRowIdx, []);
      }
      ruleMap.get(targetRowIdx).push(normalizedRule);
      if (normalizedRule.referenceRowIndex != null) {
        registerRowDependency(dependents, normalizedRule.referenceRowIndex, targetRowIdx);
      }
      if (normalizedRule.dependencies && normalizedRule.dependencies.size) {
        normalizedRule.dependencies.forEach((depIdx) => {
          registerRowDependency(dependents, depIdx, targetRowIdx);
        });
      }
    });
  });
  validationRuleMap.value = ruleMap;
  validationDependents.value = dependents;
  virtualValidationRules.value = virtualRules;
}

function normalizeRuleDefinition(definition, context) {
  const type = typeof definition.type === 'string'
    ? definition.type.toLowerCase()
    : 'number_range';
  const normalized = {
    id: context.ruleId,
    type,
    level: definition.level === 'warning' ? 'warning' : 'error',
    columns: resolveColumnIndexes(definition.columns, context),
    min: typeof definition.min === 'number' ? definition.min : null,
    max: typeof definition.max === 'number' ? definition.max : null,
    allowEmpty: definition.allow_empty === false ? false : true,
    referenceRowIndex: null,
    referenceLabel: '',
    tolerance: typeof definition.tolerance === 'number' ? definition.tolerance : 0,
    message: typeof definition.message === 'string' ? definition.message.trim() : '',
    referenceColumn: resolveSingleColumnIndex(
      definition.reference_column ?? definition.compare_column ?? definition.peer_column,
      context
    ),
    minRatio: typeof definition.min_ratio === 'number' ? definition.min_ratio : null,
    maxRatio: typeof definition.max_ratio === 'number' ? definition.max_ratio : null,
    compiledExpression: null,
    expression: typeof definition.expression === 'string' ? definition.expression.trim() : '',
    dependencies: new Set(),
    rowIndex: typeof context.rowIdx === 'number' ? context.rowIdx : null,
    virtual: definition.virtual === true || context.rowIdx == null,
    targetLabel: typeof definition.target_label === 'string' && definition.target_label.trim()
      ? definition.target_label.trim()
      : (typeof context.ruleLabel === 'string' ? context.ruleLabel : ''),
  };
  if (!normalized.columns.length) {
    normalized.columns = context.defaultColumns.slice();
  }
  if (definition.reference_row || definition.reference_label) {
    const referenceLabel = normalizeRowLabelValue(definition.reference_row || definition.reference_label);
    if (referenceLabel) {
      const idx = context.labelIndex.get(referenceLabel);
      if (idx != null) {
        normalized.referenceRowIndex = idx;
        normalized.referenceLabel = referenceLabel;
        normalized.dependencies.add(idx);
      }
    }
  }
  if (Array.isArray(definition.depends_on)) {
    definition.depends_on.forEach((labelRaw) => {
      const label = normalizeRowLabelValue(labelRaw);
      if (!label) return;
      const idx = context.labelIndex.get(label);
      if (idx != null) {
        normalized.dependencies.add(idx);
      }
    });
  }
  if (normalized.expression && (type === 'expression_range' || type === 'expression')) {
    normalized.compiledExpression = compileRuleExpression(normalized.expression);
  }
  if (normalized.columns.length === 0) {
    return null;
  }
  return normalized;
}

function resolveColumnIndexes(columnsDef, context) {
  if (!context || typeof context.totalColumns !== 'number') return [];
  const max = context.totalColumns;
  const validIndexes = [];
  const appendIndex = (value) => {
    const idx = Number(value);
    if (Number.isInteger(idx) && idx >= 0 && idx < max) {
      validIndexes.push(idx);
    }
  };
  if (Array.isArray(columnsDef)) {
    columnsDef.forEach(appendIndex);
    return validIndexes;
  }
  if (typeof columnsDef === 'number') {
    appendIndex(columnsDef);
    return validIndexes;
  }
  if (typeof columnsDef === 'string') {
    const lowered = columnsDef.toLowerCase();
    if (lowered === 'all' || lowered === 'data' || lowered === 'all_data') {
      return context.defaultColumns.slice();
    }
  }
  return [];
}

function resolveSingleColumnIndex(columnDef, context) {
  if (!context || typeof context.totalColumns !== 'number') return null;
  const max = context.totalColumns;
  if (typeof columnDef === 'number' && Number.isInteger(columnDef) && columnDef >= 0 && columnDef < max) {
    return columnDef;
  }
  if (typeof columnDef === 'string') {
    const trimmed = columnDef.trim();
    if (/^\\d+$/.test(trimmed)) {
      const idx = Number(trimmed);
      return Number.isInteger(idx) && idx >= 0 && idx < max ? idx : null;
    }
    const byName = findColumnIndexByName(trimmed);
    if (byName != null) return byName;
  }
  return null;
}

function findColumnIndexByName(name) {
  if (!name || !Array.isArray(columns.value)) return null;
  const target = String(name).trim();
  if (!target) return null;
  for (let i = 0; i < columns.value.length; i += 1) {
    const label = String(columns.value[i] ?? '').trim();
    if (label === target) return i;
  }
  return null;
}

function runFullValidation() {
  if (!validationEnabled.value || templateType.value !== 'standard') {
    clearAllValidationIssues();
    return;
  }
  const ruleMap = validationRuleMap.value;
  const hasVirtual = Array.isArray(virtualValidationRules.value) && virtualValidationRules.value.length > 0;
  if (!(ruleMap instanceof Map) || ruleMap.size === 0) {
    if (!hasVirtual) {
      clearAllValidationIssues();
      return;
    }
  }
  const nextIssues = new Map();
  ruleMap.forEach((ruleList, rowIdx) => {
    ruleList.forEach((rule) => {
      const issues = collectRuleIssues(rule, rowIdx);
      issues.forEach(({ key, issue }) => {
        nextIssues.set(key, issue);
      });
    });
  });
  if (hasVirtual) {
    virtualValidationRules.value.forEach((rule) => {
      const issues = collectRuleIssues(rule, null);
      issues.forEach(({ key, issue }) => {
        nextIssues.set(key, issue);
      });
    });
  }
  cellValidationMap.value = nextIssues;
}

function evaluateRule(rule, rowIdx, colIdx) {
  const numericValue = getCellNumericValue(rowIdx, colIdx);
  if (rule.type === 'number_range') {
    if (numericValue == null) {
      if (rule.allowEmpty === false) {
        return { reason: 'required' };
      }
      return null;
    }
    if (typeof rule.min === 'number' && numericValue < rule.min) {
      return { reason: 'min', expected: rule.min, actual: numericValue, cellValue: numericValue };
    }
    if (typeof rule.max === 'number' && numericValue > rule.max) {
      return { reason: 'max', expected: rule.max, actual: numericValue, cellValue: numericValue };
    }
    return null;
  }
  if (rule.type === 'less_equal_than') {
    if (numericValue == null || rule.referenceRowIndex == null) {
      return null;
    }
    const referenceValue = getCellNumericValue(rule.referenceRowIndex, colIdx);
    if (referenceValue == null) {
      return null;
    }
    const tolerance = typeof rule.tolerance === 'number' ? rule.tolerance : 0;
    if (numericValue > referenceValue + tolerance) {
      return {
        reason: 'greater_than_reference',
        referenceValue,
        cellValue: numericValue,
      };
    }
    return null;
  }
  if (rule.type === 'column_ratio') {
    if (numericValue == null) {
      if (rule.allowEmpty === false) {
        return { reason: 'required' };
      }
      return null;
    }
    if (rule.referenceColumn == null) {
      return null;
    }
    const referenceValue = getCellNumericValue(rowIdx, rule.referenceColumn);
    if (referenceValue == null || referenceValue === 0) {
      return null;
    }
    const ratio = numericValue / referenceValue;
    if (typeof rule.minRatio === 'number' && ratio < rule.minRatio) {
      return {
        reason: 'ratio_min',
        expected: rule.minRatio,
        actual: ratio,
        referenceColumnLabel: getColumnLabel(rule.referenceColumn),
        cellValue: numericValue,
        referenceValue,
      };
    }
    if (typeof rule.maxRatio === 'number' && ratio > rule.maxRatio) {
      return {
        reason: 'ratio_max',
        expected: rule.maxRatio,
        actual: ratio,
        referenceColumnLabel: getColumnLabel(rule.referenceColumn),
        cellValue: numericValue,
        referenceValue,
      };
    }
    return null;
  }
  if (rule.type === 'expression_range' || rule.type === 'expression') {
    const expressionValue = evaluateExpressionRule(rule, colIdx);
    if (expressionValue == null) {
      if (rule.allowEmpty === false) {
        return { reason: 'expression_required' };
      }
      return null;
    }
    if (typeof rule.min === 'number' && expressionValue < rule.min) {
      return {
        reason: 'expression_min',
        expected: rule.min,
        actual: expressionValue,
        expressionValue,
      };
    }
    if (typeof rule.max === 'number' && expressionValue > rule.max) {
      return {
        reason: 'expression_max',
        expected: rule.max,
        actual: expressionValue,
        expressionValue,
      };
    }
    if (rule.referenceColumn != null && (typeof rule.minRatio === 'number' || typeof rule.maxRatio === 'number')) {
      const referenceValue = evaluateExpressionRule(rule, rule.referenceColumn);
      if (referenceValue != null && referenceValue !== 0) {
        const ratio = expressionValue / referenceValue;
        if (typeof rule.minRatio === 'number' && ratio < rule.minRatio) {
          return {
            reason: 'expression_ratio_min',
            expected: rule.minRatio,
            actual: ratio,
            referenceColumnLabel: getColumnLabel(rule.referenceColumn),
            expressionValue,
            referenceValue,
          };
        }
        if (typeof rule.maxRatio === 'number' && ratio > rule.maxRatio) {
          return {
            reason: 'expression_ratio_max',
            expected: rule.maxRatio,
            actual: ratio,
            referenceColumnLabel: getColumnLabel(rule.referenceColumn),
            expressionValue,
            referenceValue,
          };
        }
      }
    }
    return null;
  }
  return null;
}

function buildDefaultRuleMessage(rule, columnLabel, violation) {
  if (!violation) return '';
  if (rule.type === 'number_range') {
    if (violation.reason === 'required') {
      return `${columnLabel} 不能为空`;
    }
    if (violation.reason === 'min') {
      return `${columnLabel} 不得小于 ${violation.expected}`;
    }
    if (violation.reason === 'max') {
      return `${columnLabel} 不得大于 ${violation.expected}`;
    }
  }
  if (rule.type === 'less_equal_than') {
    const referenceLabel = rule.referenceLabel || '参照指标';
    return `${columnLabel} 不得大于 ${referenceLabel}`;
  }
  if (rule.type === 'column_ratio') {
    const referenceColumnLabel = violation.referenceColumnLabel || '参照列';
    if (violation.reason === 'ratio_min') {
      return `${columnLabel} 相比 ${referenceColumnLabel} 的比例不得低于 ${violation.expected}`;
    }
    if (violation.reason === 'ratio_max') {
      return `${columnLabel} 相比 ${referenceColumnLabel} 的比例不得高于 ${violation.expected}`;
    }
  }
  if (rule.type === 'expression_range' || rule.type === 'expression') {
    if (violation.reason === 'expression_required') {
      return `${columnLabel} 的计算结果不能为空`;
    }
    if (violation.reason === 'expression_min') {
      return `${columnLabel} 的计算结果不得小于 ${violation.expected}`;
    }
    if (violation.reason === 'expression_max') {
      return `${columnLabel} 的计算结果不得大于 ${violation.expected}`;
    }
    if (violation.reason === 'expression_ratio_min') {
      const ref = violation.referenceColumnLabel || '参照列';
      return `${columnLabel} 相比 ${ref} 的计算结果比例不得低于 ${violation.expected}`;
    }
    if (violation.reason === 'expression_ratio_max') {
      const ref = violation.referenceColumnLabel || '参照列';
      return `${columnLabel} 相比 ${ref} 的计算结果比例不得高于 ${violation.expected}`;
    }
  }
  return `${columnLabel} 未通过校验`;
}

function validateRow(rowIdx) {
  if (!validationEnabled.value || templateType.value !== 'standard') {
    return;
  }
  const ruleList = validationRuleMap.value.get(rowIdx);
  const currentIssues = cellValidationMap.value;
  const cleared = clearIssuesByPrefix(currentIssues, `${rowIdx}:`);
  let workingMap = cleared.map;
  let mutated = cleared.mutated;
  if (ruleList && ruleList.length) {
    const newIssues = [];
    ruleList.forEach((rule) => {
      newIssues.push(...collectRuleIssues(rule, rowIdx));
    });
    const applied = applyIssues(workingMap, newIssues);
    workingMap = applied.map;
    mutated = mutated || applied.mutated;
  }
  const virtualResult = revalidateVirtualRulesForRow(rowIdx, workingMap);
  workingMap = virtualResult.map;
  mutated = mutated || virtualResult.mutated;
  if (mutated) {
    cellValidationMap.value = workingMap;
  }
}

function resolveReadonlyLimit(columnList) {
  if (!Array.isArray(columnList)) {
    return 1;
  }
  const targetIndex = columnList.findIndex(col => {
    if (typeof col !== 'string') return false;
    return col.trim().includes('计量单位');
  });
  return targetIndex >= 0 ? targetIndex : 1;
}

function applyReadonlyToColumns() {
  if (!Array.isArray(gridColumns.value)) return;
  const shouldLockAll = isReadOnlyForDate.value;
  gridColumns.value = gridColumns.value.map((def, index) => {
    const locked = Boolean(def.__locked) || (shouldLockAll && (templateType.value === 'standard' || templateType.value === 'crosstab'));
    const currentReadonly = def.readonly === undefined ? false : def.readonly;
    if (currentReadonly === locked) {
      return def;
    }
    return { ...def, readonly: locked };
  });
}

async function loadSheetValidationSwitch() {
  if (!shouldShowSheetValidationToggle.value || !projectKey || !sheetKey) {
    sheetValidationEnabled.value = true;
    return;
  }
  sheetValidationLoading.value = true;
  sheetValidationError.value = '';
  try {
    const payload = await getSheetValidationSwitch(projectKey, sheetKey, { config: pageConfig.value });
    sheetValidationEnabled.value = Boolean(payload?.validation_enabled ?? true);
  } catch (err) {
    console.error(err);
    sheetValidationError.value = err instanceof Error ? err.message : String(err);
  } finally {
    sheetValidationLoading.value = false;
  }
}

async function updateSheetValidationSwitch(nextValue) {
  if (
    !shouldShowSheetValidationToggle.value ||
    !canToggleSheetValidation.value ||
    !projectKey ||
    !sheetKey
  ) {
    return;
  }
  sheetValidationSaving.value = true;
  const previous = sheetValidationEnabled.value;
  sheetValidationEnabled.value = nextValue;
  try {
    await setSheetValidationSwitch(projectKey, sheetKey, nextValue, { config: pageConfig.value });
    await reloadTemplate();
    await loadSheetValidationSwitch();
  } catch (err) {
    console.error(err);
    sheetValidationEnabled.value = previous;
  } finally {
    sheetValidationSaving.value = false;
  }
}

function onSheetValidationToggle(event) {
  if (sheetValidationToggleDisabled.value) {
    if (event?.target) {
      event.target.checked = sheetValidationEnabled.value;
    }
    return;
  }
  const checked = Boolean(event?.target?.checked);
  updateSheetValidationSwitch(checked);
}

// --- 渲染逻辑：标准模板 ---
async function setupStandardGrid(tpl) {
  const readonlyLimit = resolveReadonlyLimit(tpl.columns);
  readOnlyThreshold.value = readonlyLimit;
  gridColumns.value = tpl.columns.map((colName, index) => ({
    prop: `c${index}`,
    name: String(colName ?? ''),
    autoSize: true,
    minSize: index === 0 ? 160 : 120,
    __locked: index <= readonlyLimit,
    readonly: index <= readonlyLimit || isReadOnlyForDate.value,
  }));
  applyReadonlyToColumns();

  const src = tpl.rows.map(row => {
    const record = {};
    for (let ci = 0; ci < tpl.columns.length; ci++) {
      record[`c${ci}`] = row?.[ci] ?? '';
    }
    return record;
  });
  gridSource.value = src;
  await autoSizeFirstColumn();
}

// --- 渲染逻辑：交叉表模板 (煤炭库存) ---
async function setupCrosstabGrid(tpl) {
  const readonlyLimit = resolveReadonlyLimit(tpl.columns);
  readOnlyThreshold.value = readonlyLimit;
  gridColumns.value = tpl.columns.map((name, index) => ({
    prop: `c${index}`,
    name: String(name ?? ''),
    autoSize: true,
    minSize: index === 0 ? 160 : 120,
    __locked: index <= readonlyLimit,
    readonly: index <= readonlyLimit || isReadOnlyForDate.value,
  }));
  applyReadonlyToColumns();

  gridSource.value = tpl.rows.map(r => {
    const record = {};
    for (let i = 0; i < tpl.columns.length; i++) {
      record[`c${i}`] = r[i] ?? '';
    }
    return record;
  });
}

// --- 主数据加载逻辑 ---
async function loadTemplate() {
  isLoadingTemplate.value = true;
  linkageMap.value = new Map();
  const rawTemplate = await getTemplate(projectKey, sheetKey, { config: pageConfig.value });
  // 强制首次查询已移除，统一在下方“初次加载后的镜像查询”中处理
  // 应用日期占位到列头（仅每日数据填报页面）
  if (isDailyPage.value && Array.isArray(rawTemplate?.columns)) {
    // 缓存原始列头以便后续根据日历重算
    baseColumns.value = Array.isArray(rawTemplate.columns) ? [...rawTemplate.columns] : []
    rawTemplate.columns = replaceDatePlaceholdersInColumns(baseColumns.value)
  }
  const { template: tpl } = applyTemplatePlaceholders(rawTemplate);
  // 若模板给出权威业务日期，优先设置并等待一帧，确保首次查询使用正确日期
  if (tpl.biz_date) {
    canonicalBizDate.value = tpl.biz_date;
    bizDate.value = tpl.biz_date;
    await nextTick();
  }
  
  // 存储基础信息
  sheetName.value = tpl.sheet_name || '';
  unitName.value = tpl.unit_name || '';
  unitId.value = tpl.unit_id || '';
  columns.value = tpl.columns || [];
  // 提前确定模板类型与行数据，避免初始化顺序导致回填被覆盖
  rows.value = tpl.rows || [];
  templateType.value = tpl.template_type || 'standard';
  validationEnabled.value = resolveValidationEnabledFlag(tpl);
  validationExplanationMap.value = normalizeExplanationMapping(
    tpl.validation_explanation_map || tpl['校验说明映射']
  );
  if (templateType.value === 'standard') {
    templateValidationRaw.value = tpl.validation_rules || tpl['校验规则'] || null;
  } else {
    templateValidationRaw.value = null;
  }
  rebuildValidationRulesFromRows(rows.value);
  // 交叉表需先搭好列与占位行，再执行镜像查询，避免后续初始化覆盖查询结果
  if (templateType.value === 'crosstab') {
    await setupCrosstabGrid(tpl);
  } else {
    // 标准模板也需要预先搭好骨架，再查询填充
    await setupStandardGrid(tpl);
    if (validationEnabled.value) {
      runFullValidation();
    } else {
      clearAllValidationIssues();
    }
  }
  // 初次加载后进行一次镜像查询（按当前 bizDate 或模板类型）；便于刷新后直接看到已填数据
  try {
    if (templateType.value === 'standard') {
      const __rid1 = newRequestId(); latestRequestId.value = __rid1;
      const q = await queryData(
        projectKey,
        sheetKey,
        { project_key: projectKey, sheet_key: sheetKey, biz_date: bizDate.value, request_id: __rid1 },
        { config: pageConfig.value }
      );
      if (q && q.__request_id && q.__request_id !== latestRequestId.value) {
        return
      }
      await applyStandardQueryResult(q);
    } else if (templateType.value === 'constant') {
      // 常量指标：无需 biz_date；按模板 columns 的 period 标签由后端映射回填
      const __ridc = newRequestId(); latestRequestId.value = __ridc;
      const q = await queryData(
        projectKey,
        sheetKey,
        { project_key: projectKey, sheet_key: sheetKey, request_id: __ridc },
        { config: pageConfig.value }
      );
      if (q && q.__request_id && q.__request_id !== latestRequestId.value) {
        return
      }
      await applyStandardQueryResult(q);
    } else if (templateType.value === 'crosstab') {
      const __rid2 = newRequestId(); latestRequestId.value = __rid2;
      const q = await queryData(
        projectKey,
        sheetKey,
        { project_key: projectKey, sheet_key: sheetKey, biz_date: bizDate.value, request_id: __rid2 },
        { config: pageConfig.value }
      );
      if (q && q.__request_id && q.__request_id !== latestRequestId.value) {
        return
      }
      // 更新列头（若由后端基于日期生成），并对齐 gridColumns
      if (q && Array.isArray(q.columns)) {
        columns.value = q.columns;
        if (Array.isArray(gridColumns.value) && gridColumns.value.length === q.columns.length) {
          gridColumns.value = gridColumns.value.map((def, i) => ({ ...def, name: q.columns[i] }));
          applyReadonlyToColumns();
        } else {
          const colDefs = q.columns.map((name, index) => ({
            name: String(name ?? ''),
            prop: `c${index}`,
            size: index === 0 ? 180 : undefined,
            minSize: index === 0 ? 160 : 100,
            __locked: index <= readOnlyThreshold.value,
            readonly: index <= readOnlyThreshold.value || isReadOnlyForDate.value,
          }));
          gridColumns.value = colDefs;
          applyReadonlyToColumns();
        }
      }
      if (q && Array.isArray(q.rows)) {
        gridSource.value = q.rows.map(r => Array.isArray(r)
          ? r.reduce((acc, val, idx) => {
              acc[`c${idx}`] = (val === null || val === undefined) ? '' : String(val);
              return acc;
            }, {})
          : r
        );
        rows.value = Array.isArray(q.rows) ? q.rows : rows.value;
      }
    }
  } catch (err) {
    // console.error('initial query failed:', err);
  }

  // 如果后端下发了权威的业务日期，则使用它
  if (tpl.biz_date) {
    canonicalBizDate.value = tpl.biz_date;
    bizDate.value = tpl.biz_date;
  }

  // 存储字典
  const dictSnapshot = {};
  let itemPrimary = null;
  let companyPrimary = null;
  Object.entries(tpl).forEach(([key, rawValue]) => {
    if (typeof key !== 'string' || !key.endsWith('_dict')) return;
    const normalizedDict = normalizeDictPayload(rawValue);
    if (!normalizedDict) return;
    dictSnapshot[key] = normalizedDict;
    if (!itemPrimary && key === 'item_dict') itemPrimary = normalizedDict;
    if (!companyPrimary && key === 'company_dict') companyPrimary = normalizedDict;
  });
  if (!dictSnapshot.item_dict) {
    const normalized = normalizeDictPayload(tpl.item_dict);
    if (normalized) {
      dictSnapshot.item_dict = normalized;
      if (!itemPrimary) itemPrimary = normalized;
    }
  }
  if (!dictSnapshot.company_dict) {
    const normalized = normalizeDictPayload(tpl.company_dict);
    if (normalized) {
      dictSnapshot.company_dict = normalized;
      if (!companyPrimary) companyPrimary = normalized;
    }
  }
  templateDicts.value = { entries: dictSnapshot, itemPrimary, companyPrimary };
  const linkagePayload = {
    entries: dictSnapshot,
    linkage_dict: tpl.linkage_dict,
    ['指标联动']: tpl['指标联动'],
  };
  rebuildLinkageMapFromPayload(rows.value, linkagePayload);

  isLoadingTemplate.value = false;
}

async function loadExisting() {
  // 注意：当前查询和回填逻辑只适用于 standard 模板
  if (templateType.value !== 'standard') return;

  const __rid3 = newRequestId(); latestRequestId.value = __rid3;
  const q = await queryData(
    projectKey,
    sheetKey,
    { project_key: projectKey, sheet_key: sheetKey, biz_date: bizDate.value, request_id: __rid3 },
    { config: pageConfig.value },
  );
  if (q && q.__request_id && q.__request_id !== latestRequestId.value) {
    return
  }
  // cells 路径已删除（rows-only 渲染）
  if (false) {
    for (const _ of []) {
      const { row_label, col_index, value_num, value_text } = cell;
      const ri = rows.value.findIndex(r => r[0] === row_label);
      if (ri >= 0 && col_index >= 0 && gridSource.value[ri]) {
        gridSource.value[ri][`c${col_index}`] = value_num != null ? String(value_num) : String(value_text ?? '');
      }
    }
  }
  await autoSizeFirstColumn();
  if (validationEnabled.value) {
    runFullValidation();
  }
}

async function reloadTemplate() {
  await loadTemplate();
}

// --- 提交逻辑 ---
function handleSubmitStandard() {
  const readonlyLimit = resolveReadonlyLimit(columns.value);
  const filledRows = rows.value.map((row, ri) => {
    const newRow = [...row];
    const record = gridSource.value?.[ri] ?? {};
    for (let ci = readonlyLimit + 1; ci < columns.value.length; ci++) {
      const key = `c${ci}`;
      if (record[key] !== undefined) {
        newRow[ci] = record[key];
      }
    }
    return newRow;
  });

  return {
    columns: columns.value,
    rows: filledRows,
  };
}

function handleSubmitCrosstab() {
  // 对于交叉表，我们直接提交 gridSource，后端需要新的解析器
  // 这里我们先按前端能做到的最清晰结构进行构建
  return {
    columns: columns.value,
    rows: gridSource.value.map(record => columns.value.map((_, i) => record[`c${i}`] ?? '')),
  };
}

async function onSubmit() {
  if (submitDisabled.value) {
    window.alert('所选日期仅支持查看，不能提交修改。');
    return;
  }
  if (isSubmitting.value) {
    return;
  }
  if (validationEnabled.value) {
    runFullValidation();
    if (hasBlockingValidation.value) {
      showSubmitFeedback('error', '存在未通过的校验项，请先修正提示后再提交。', { autoHide: false });
      return;
    }
  }
  let submissionData;
  if (templateType.value === 'crosstab') {
    submissionData = handleSubmitCrosstab();
  } else {
    submissionData = handleSubmitStandard();
  }

  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  const currentSubmitTime = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
  
  const payload = {
    project_key: projectKey,
    project_name: projectName.value || projectKey,
    sheet_key: sheetKey,
    sheet_name: sheetName.value || '',
    unit_name: unitName.value || '',
    biz_date: bizDate.value,
    unit_id: unitId.value,
    submit_time: currentSubmitTime,
    status: 'submit',
    ...submissionData,
  };

  // 添加字典
  const dictBundle = templateDicts.value || {};
  const entryMap = dictBundle.entries || {};
  for (const [dictKey, dictValue] of Object.entries(entryMap)) {
    payload[dictKey] = cloneDictValue(dictValue);
  }
  if (!payload.item_dict && dictBundle.itemPrimary) {
    payload.item_dict = cloneDictValue(dictBundle.itemPrimary);
  }
  if (!payload.company_dict && dictBundle.companyPrimary) {
    payload.company_dict = cloneDictValue(dictBundle.companyPrimary);
  }

  isSubmitting.value = true;
  try {
    await submitData(projectKey, sheetKey, payload, { config: pageConfig.value });
    submitTime.value = currentSubmitTime;
    startRefreshCountdown(3);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error('[data-entry] 提交失败', message);
    clearRefreshCountdown();
    showSubmitFeedback('error', `提交失败：${message || '请稍后重试'}`);
  } finally {
    isSubmitting.value = false;
  }
}

// --- RevoGrid 事件处理 ---
function handleAfterEdit(evt) {
  if (isReadOnlyForDate.value) {
    return;
  }
  const detail = evt?.detail ?? evt;
  const changes = Array.isArray(detail?.changes) ? detail.changes : (detail ? [detail] : []);
  for (const change of changes) {
    const { rowIndex, prop, val } = change || {};
    if (rowIndex == null || !prop) continue;
    if (!gridSource.value[rowIndex]) continue;
    gridSource.value[rowIndex][prop] = val;
    const isStandardTemplate = templateType.value === 'standard';
    const shouldValidate = isStandardTemplate && validationEnabled.value;
    const rowsToRevalidate = shouldValidate ? new Set() : null;
    const scheduleValidation = (idx) => {
      if (!rowsToRevalidate || idx == null) return;
      rowsToRevalidate.add(idx);
      const dependents = validationDependents.value.get(idx);
      if (dependents && dependents.size) {
        dependents.forEach(dep => rowsToRevalidate.add(dep));
      }
    };
    scheduleValidation(rowIndex);
    if (isStandardTemplate) {
      const map = linkageMap.value;
      if (map instanceof Map && map.size > 0) {
        const related = map.get(rowIndex);
        if (related && related.size > 0) {
          if (isApplyingLinkage) {
            continue;
          }
          isApplyingLinkage = true;
          try {
            related.forEach((linkedIdx) => {
              if (!gridSource.value[linkedIdx]) return;
              gridSource.value[linkedIdx][prop] = val;
              scheduleValidation(linkedIdx);
            });
          } finally {
            isApplyingLinkage = false;
          }
        }
      }
    }
    if (rowsToRevalidate && rowsToRevalidate.size) {
      rowsToRevalidate.forEach((idx) => validateRow(idx));
    }
  }
}

// --- 生命周期 ---
onMounted(async () => {
  await nextTick();
  await ensureProjectsLoaded().catch(() => {});
  await loadSheetValidationSwitch();
  await loadTemplate();
});

// --- 遗留功能：仅用于标准模板 ---
async function autoSizeFirstColumn() {
  if (templateType.value !== 'standard' || !gridColumns.value.length) return;
  await nextTick();
  const gridComponent = gridRef.value;
  const gridElement = gridComponent?.$el ?? gridComponent;
  if (!gridElement) return;

  const computed = typeof window !== 'undefined' ? window.getComputedStyle(gridElement) : null;
  const font = computed?.font || '14px/1.4 "Segoe UI", Arial, sans-serif';
  const candidates = [columns.value[0] ?? ''];
  gridSource.value.forEach(row => candidates.push(row?.c0 ?? ''));
  
  const widest = Math.max(...candidates.map(c => measureTextWidth(c, font)));
  const padding = 36;
  const target = Math.max(gridColumns.value[0]?.minSize ?? 160, Math.ceil(widest) + padding);

  gridColumns.value[0].size = target;
  gridColumns.value = [...gridColumns.value];
}

let textMeasureCtx = null;
function getTextMeasureContext() {
  if (typeof document === 'undefined') return null;
  if (textMeasureCtx) return textMeasureCtx;
  const canvas = document.createElement('canvas');
  textMeasureCtx = canvas.getContext('2d');
  return textMeasureCtx;
}

function measureTextWidth(content, font) {
  const ctx = getTextMeasureContext();
  const text = String(content ?? '');
  if (!ctx || !text) return text.length * 14;
  ctx.font = font || '14px/1.4 "Segoe UI", Arial, sans-serif';
  return ctx.measureText(text).width;
}

async function applyStandardQueryResult(payload) {
  if (!payload || typeof payload !== 'object') return;
  const q = payload;
  if (Array.isArray(q.columns)) {
    if (!isDailyPage.value) {
      columns.value = q.columns;
      const colDefs = q.columns.map((name, index) => ({
        name: String(name ?? ''),
        prop: `c${index}`,
        size: index === 0 ? 220 : 120,
        __locked: index <= readOnlyThreshold.value,
        readonly: index <= readOnlyThreshold.value || isReadOnlyForDate.value,
      }));
      gridColumns.value = colDefs;
      applyReadonlyToColumns();
    }
  }
  if (Array.isArray(q.rows)) {
    gridSource.value = q.rows.map(r => Array.isArray(r)
      ? r.reduce((acc, val, idx) => {
          acc[`c${idx}`] = (val === null || val === undefined) ? '' : String(val);
          return acc;
        }, {})
      : r
    );
    rows.value = q.rows;
    await autoSizeFirstColumn();
    applyReadonlyToColumns();
  }
  const linkagePayload = {
    entries: (templateDicts.value && templateDicts.value.entries) ? templateDicts.value.entries : {},
    linkage_dict: q && typeof q === 'object' ? q.linkage_dict : undefined,
    ['指标联动']: q && typeof q === 'object' ? q['指标联动'] : undefined,
  };
  rebuildLinkageMapFromPayload(rows.value, linkagePayload, { syncGrid: true });
  if (templateType.value === 'standard') {
    rebuildValidationRulesFromRows(rows.value);
    if (validationEnabled.value) {
      runFullValidation();
    } else {
      clearAllValidationIssues();
    }
  }
}
// 监听业务日期变更，标准表需用新日期重算列头与网格列定义
const stop = watch(
  () => bizDate.value,
  async () => {
    if (isLoadingTemplate.value) return;
    if (templateType.value === 'standard') {
      if (!Array.isArray(baseColumns.value) || !baseColumns.value.length) return;
      const recalculated = replaceDatePlaceholdersInColumns(baseColumns.value);
      columns.value = recalculated;
      if (Array.isArray(gridColumns.value) && gridColumns.value.length === recalculated.length) {
        gridColumns.value = gridColumns.value.map((def, i) => ({ ...def, name: recalculated[i] }));
        applyReadonlyToColumns();
      }
    }
    // 日历变更后，触发一次镜像查询，回填当日数据与备注
    try {
      await nextTick();
      const __rid4 = newRequestId(); latestRequestId.value = __rid4;
      const q = await queryData(
        projectKey,
        sheetKey,
        { project_key: projectKey, sheet_key: sheetKey, biz_date: bizDate.value, request_id: __rid4 },
        { config: pageConfig.value }
      );
      if (q && q.__request_id && q.__request_id !== latestRequestId.value) {
        return
      }
      await applyStandardQueryResult(q);
    } catch (err) {
      // console.error('query on bizDate change failed:', err);
    }
  }
)

// crosstab：业务日期变化时重新查询并渲染 rows
watch(
  () => bizDate.value,
  async () => {
    if (isLoadingTemplate.value) return;
    if (templateType.value !== 'crosstab') return;
    try {
      const __rid5 = newRequestId(); latestRequestId.value = __rid5;
      const q = await queryData(
        projectKey,
        sheetKey,
        { project_key: projectKey, sheet_key: sheetKey, biz_date: bizDate.value, request_id: __rid5 },
        { config: pageConfig.value }
      );
      if (q && q.__request_id && q.__request_id !== latestRequestId.value) {
        return
      }
      if (q && Array.isArray(q.columns)) {
        columns.value = q.columns;
        if (Array.isArray(gridColumns.value) && gridColumns.value.length === q.columns.length) {
          gridColumns.value = gridColumns.value.map((def, i) => ({ ...def, name: q.columns[i] }));
          applyReadonlyToColumns();
        } else {
          const colDefs = q.columns.map((name, index) => ({
            name: String(name ?? ''),
            prop: `c${index}`,
            size: index === 0 ? 180 : undefined,
            minSize: index === 0 ? 160 : 100,
            __locked: index <= readOnlyThreshold.value,
            readonly: index <= readOnlyThreshold.value || isReadOnlyForDate.value,
          }));
          gridColumns.value = colDefs;
          applyReadonlyToColumns();
        }
      }
      if (q && Array.isArray(q.rows)) {
        gridSource.value = q.rows.map(r => Array.isArray(r)
          ? r.reduce((acc, val, idx) => {
              acc[`c${idx}`] = (val === null || val === undefined) ? '' : String(val);
              return acc;
            }, {})
          : r
        );
        rows.value = Array.isArray(q.rows) ? q.rows : rows.value;
      }
    } catch (err) {
      // console.error('crosstab query on bizDate change failed:', err);
    }
  }
)

watch(
  () => route.params.sheetKey,
  () => {
    loadSheetValidationSwitch();
  },
);

watch(
  () => pageConfig.value,
  () => {
    loadSheetValidationSwitch();
  },
);

watch(
  () => analysisTimelineMetrics.value,
  (metrics) => {
    const available = metrics.map((item) => item?.key).filter(Boolean);
    if (!available.length) {
      activeTimelineMetricKeys.value = [];
      return;
    }
    const retained = activeTimelineMetricKeys.value.filter((key) => available.includes(key));
    if (retained.length) {
      activeTimelineMetricKeys.value = retained;
      return;
    }
    activeTimelineMetricKeys.value = available.slice(0, Math.min(2, available.length));
  },
  { immediate: true },
);

watch(
  () => bizDate.value,
  (value) => {
    if (!value) return;
    applyAnalysisDateWindow(value);
    analysisDefaultDateApplied.value = true;
    resetAnalysisResult();
  },
);

onBeforeUnmount(() => {
  if (submitFeedbackTimer !== null) {
    clearTimeout(submitFeedbackTimer);
    submitFeedbackTimer = null;
  }
  clearRefreshCountdown();
});
</script>

<style scoped>
.topbar { gap: 12px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
.date-group input[type="date"] { padding: 4px 8px; border: 1px solid var(--border); border-radius: 6px; }
.breadcrumb-spacing { margin-bottom: 12px; display: inline-block; }
.submit-time { font-size: 13px; color: var(--muted); margin-right: auto; }
.sheet-validation-toggle {
  width: 16px;
  height: 16px;
  margin-right: 4px;
  accent-color: var(--primary-600, #2563eb);
  cursor: pointer;
}
.sheet-validation-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}
.submit-feedback { margin: 0 auto 20px; padding: 14px 24px; border-radius: 16px; font-weight: 600; font-size: 14px; line-height: 1.55; display: flex; justify-content: center; align-items: center; gap: 10px; border: 1px solid rgba(148, 163, 184, 0.28); box-shadow: none; width: min(100%, 620px); }
.submit-feedback--success { background: rgba(187, 247, 208, 0.9); color: #0f5132; border-color: rgba(34, 197, 94, 0.45); }
.submit-feedback--error { background: rgba(254, 226, 226, 0.92); color: #7f1d1d; border-color: rgba(248, 113, 113, 0.45); }
.submit-countdown { font-weight: 500; }
.submit-feedback-fade-enter-active,
.submit-feedback-fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.submit-feedback-fade-enter-from,
.submit-feedback-fade-leave-to { opacity: 0; transform: translateY(-8px); }
.validation-panel { margin-bottom: 16px; padding: 16px 20px; border: 1px dashed rgba(248, 113, 113, 0.6); background: rgba(254, 242, 242, 0.8); border-radius: 12px; }
.validation-panel__header { display: flex; gap: 8px; align-items: baseline; margin-bottom: 12px; font-size: 14px; }
.validation-panel__hint { color: #7f1d1d; font-weight: 500; }
.validation-panel__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.validation-panel__item { display: flex; align-items: center; gap: 10px; font-size: 13px; line-height: 1.5; padding: 8px 12px; border-radius: 8px; background: rgba(255, 255, 255, 0.65); border: 1px solid rgba(248, 113, 113, 0.35); }
.validation-panel__item--warning { border-color: rgba(251, 191, 36, 0.5); background: rgba(255, 251, 235, 0.8); color: #92400e; }
.validation-panel__badge { font-size: 12px; font-weight: 700; padding: 2px 8px; border-radius: 999px; background: rgba(248, 113, 113, 0.15); color: #b91c1c; }
.validation-panel__item--warning .validation-panel__badge { background: rgba(251, 191, 36, 0.2); color: #b45309; }
.validation-panel__label { font-weight: 600; color: #1f2937; }
.validation-panel__message { flex: 1; color: #374151; }
.analysis-lite { margin-top: 20px; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.analysis-lite__header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.analysis-lite__actions { display: flex; gap: 8px; }
.analysis-lite__hint { color: #64748b; font-size: 13px; }
.analysis-lite__fold-hint { padding: 12px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 10px; color: #475569; }
.analysis-lite__body { display: flex; flex-direction: column; gap: 12px; }
.analysis-lite__form { display: flex; flex-direction: column; gap: 12px; }
.analysis-lite__field { display: flex; flex-direction: column; gap: 6px; }
.analysis-lite__field-header { display: flex; justify-content: space-between; align-items: center; }
.analysis-lite__field-actions { display: flex; gap: 6px; }
.analysis-lite__dates { display: flex; align-items: center; gap: 8px; }
.analysis-lite__metrics { max-height: 200px; overflow: auto; }
.analysis-lite__grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }
.analysis-lite__group-card { padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; background: #f8fafc; display: flex; flex-direction: column; gap: 8px; }
.analysis-lite__group-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.analysis-lite__metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; max-height: 220px; overflow: auto; padding-right: 4px; }
.analysis-lite__form-actions { display: flex; align-items: center; gap: 12px; }
.analysis-lite__unit-label { font-size: 13px; color: #475569; }
.analysis-lite__result { display: flex; flex-direction: column; gap: 10px; }
.analysis-lite__warnings { padding: 10px 12px; background: #fff7ed; border: 1px solid #fdba74; border-radius: 8px; color: #9a3412; }
.analysis-lite__table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.analysis-lite__table th, .analysis-lite__table td { border-bottom: 1px solid #e2e8f0; padding: 10px 8px; vertical-align: middle; }
.analysis-lite__table th { text-align: center; white-space: nowrap; }
.analysis-lite__table td { text-align: center; }
.analysis-lite__metric { font-weight: 600; color: #0f172a; min-width: 160px; }
.analysis-lite__value { display: inline-flex; justify-content: center; align-items: baseline; gap: 6px; color: #0f172a; width: 100%; }
.analysis-lite__number { font-weight: 700; }
.analysis-lite__unit { color: #475569; font-size: 13px; }
.analysis-lite__table .delta-up { color: #b91c1c; }
.analysis-lite__table .delta-down { color: #0f9d58; }
.analysis-lite__timeline { margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
.analysis-lite__timeline-header { display: flex; justify-content: space-between; align-items: center; }
.analysis-lite__timeline-metrics { display: flex; flex-wrap: wrap; gap: 8px; }
.chip--toggle { border: 1px solid #cbd5f5; background: #fff; }
.chip--toggle.active { background: #2563eb; color: #fff; border-color: #2563eb; }
.chip-label { display: inline-flex; align-items: center; gap: 6px; }
.chip-order {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: var(--primary-50, #eef2ff);
  color: var(--primary-700, #1d4ed8);
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--primary-100, #dbeafe);
}
.analysis-lite__timeline-grid { border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
.analysis-lite__timeline-chart { border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; background: #fff; }
.chart-tooltip__title { font-weight: 700; margin-bottom: 8px; }
.chart-tooltip__item { display: flex; align-items: center; gap: 6px; font-size: 13px; line-height: 1.6; }
.chart-tooltip__dot { display: inline-flex; width: 10px; height: 10px; border-radius: 999px; }
.chart-tooltip__delta { margin-left: 6px; color: #fecdd3; font-weight: 600; }

</style>
