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
        <label class="unit-analysis-inline" title="本单位数据分析开关">
          <input
            type="checkbox"
            :checked="isUnitAnalysisEnabled"
            :disabled="!canEditUnitAnalysisToggle"
            @change="handleUnitAnalysisToggleChange"
          />
          <span>本单位分析</span>
        </label>
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

    <UnitAnalysisLite
      v-if="isUnitAnalysisEnabled"
      :project-key="projectKey"
      :unit-key="unitId || sheetKey"
      :unit-name="unitName || unitId || sheetKey"
      :sheet-key="sheetKey"
      :page-config="pageConfig"
      :biz-date="bizDate"
    />
  </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import RevoGrid from '@revolist/vue3-datagrid'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import UnitAnalysisLite from '../components/UnitAnalysisLite.vue'
import { useRouter, useRoute } from 'vue-router'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  getTemplate,
  queryData,
  submitData,
  getSheetValidationSwitch,
  setSheetValidationSwitch,
} from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'
import { useTemplatePlaceholders } from '../composables/useTemplatePlaceholders'
import { useAuthStore } from '../store/auth'

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

// --- 本单位分析启用开关 ---
const UNIT_ANALYSIS_DEFAULT_ENABLED = new Set([
  'BeiHai_co_generation_Sheet',
  'XiangHai_Sheet',
  'GongRe_Sheet',
  'JinZhou_Sheet',
  'BeiFang_Sheet',
  'JinPu_Sheet',
  'ZhuangHe_Sheet',
  'YanJiuYuan_Sheet',
]);
const UNIT_ANALYSIS_STORAGE_KEY = 'unit_analysis_enabled_map';

function loadUnitAnalysisToggleMap() {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(UNIT_ANALYSIS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed === 'object') {
      return parsed;
    }
  } catch (err) {
    // ignore
  }
  return {};
}

const unitAnalysisToggleMap = ref(loadUnitAnalysisToggleMap());
const canEditUnitAnalysisToggle = computed(() => normalizedGroup.value === 'global_admin');

const isUnitAnalysisEnabled = computed(() => {
  if (!sheetKey) return false;
  const map = unitAnalysisToggleMap.value || {};
  if (Object.prototype.hasOwnProperty.call(map, sheetKey)) {
    return !!map[sheetKey];
  }
  return UNIT_ANALYSIS_DEFAULT_ENABLED.has(sheetKey);
});

function persistUnitAnalysisToggle(map) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(UNIT_ANALYSIS_STORAGE_KEY, JSON.stringify(map));
  } catch (err) {
    // ignore
  }
}

function updateUnitAnalysisToggle(value) {
  if (!sheetKey) return;
  const nextMap = { ...(unitAnalysisToggleMap.value || {}) };
  nextMap[sheetKey] = !!value;
  unitAnalysisToggleMap.value = nextMap;
  persistUnitAnalysisToggle(nextMap);
}

function handleUnitAnalysisToggleChange(event) {
  if (!canEditUnitAnalysisToggle.value) return;
  updateUnitAnalysisToggle(event.target.checked);
}

if (!projectKey || !pageKey || !sheetKey) {
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
.unit-analysis-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--neutral-50);
  color: var(--neutral-700);
}
.unit-analysis-inline input {
  width: 16px;
  height: 16px;
  accent-color: var(--primary-600, #2563eb);
}
.unit-analysis-toggle__hint { color: #64748b; font-size: 13px; }
.unit-analysis-toggle__switch { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; color: #0f172a; }
.unit-analysis-toggle__switch input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--primary-600, #2563eb);
}
.unit-analysis-toggle__switch input:disabled + span { color: #94a3b8; }

</style>
