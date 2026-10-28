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
      <div class="topbar__title-group">
        <h2>{{ unitGroupName ? `${unitGroupName} 数据填报` : '数据填报' }}</h2>
        <div class="sub">项目：{{ projectName }} ｜ 当前表：{{ sheetDisplayName }}</div>
      </div>
      <div class="topbar__actions">
        <div class="topbar__status-row">
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
          <label v-if="shouldShowSheetAiToggle" class="unit-analysis-inline" title="开放智能报告给其他用户">
            <input
              type="checkbox"
              :checked="sheetAiReportEnabled"
              :disabled="sheetAiToggleDisabled"
              @change="onSheetAiToggle"
            />
            <span>开放智能报告</span>
          </label>
        </div>
        <div class="topbar__action-row">
          <label v-if="isDailyPage" class="date-group topbar__date" title="业务日期">
            <span>业务日期：</span>
            <input type="date" v-model="bizDate" />
          </label>
          <div class="topbar__buttons">
            <button class="btn ghost" type="button" @click="reloadTemplate()">重载模板</button>
            <button
              v-if="canUploadEfficiency"
              class="btn secondary efficiency-upload-btn"
              type="button"
              :disabled="efficiencyUploading"
              :title="efficiencyUploadTitle"
              @click="triggerEfficiencyUpload"
            >
              <span v-if="efficiencyUploading">⏳ 解析中…</span>
              <span v-else>📁 上传能效分析表</span>
            </button>
            <input
              v-if="canUploadEfficiency"
              ref="efficiencyFileInputRef"
              type="file"
              accept=".xlsx, .xls"
              style="display: none"
              @change="onEfficiencyFileSelected"
            />
            <button
              v-if="unitSheets.length > 1"
              class="btn primary submit-all-btn"
              type="button"
              :disabled="submitButtonDisabled"
              :title="`一并提交 ${unitGroupName || '本单位'} 全部 ${unitSheets.length} 张表格`"
              @click="onSubmitAll"
            >
              {{ canSubmitCurrentProject ? `一并提交全部表格 (共${unitSheets.length}张)` : '当前账号无提交权限' }}
            </button>
            <button
              v-else
              class="btn primary"
              type="button"
              :disabled="submitButtonDisabled"
              @click="onSubmit"
            >
              {{ canSubmitCurrentProject ? '提交' : '当前账号无提交权限' }}
            </button>
            <button
              v-if="unitSheets.length > 1"
              class="btn ghost text-btn"
              type="button"
              :disabled="submitButtonDisabled"
              title="仅提交当前选中的这一张表格"
              @click="onSubmit"
            >
              仅提交当前表
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- 多表格单位现代分段标签栏 (Segmented Tabs) -->
    <div v-if="unitSheets.length > 1" class="unit-tabs-nav-wrapper">
      <div class="unit-tabs-nav" role="tablist" aria-label="单位所属报表切换">
        <button
          v-for="s in unitSheets"
          :key="s.sheet_key"
          type="button"
          role="tab"
          :aria-selected="s.sheet_key === activeSheetKey"
          :class="['unit-tab-pill', { 'unit-tab-pill--active': s.sheet_key === activeSheetKey }]"
          @click="onSwitchSheetTab(s.sheet_key)"
        >
          <span class="tab-index" v-if="parseSheetNumber(s.sheet_name)">{{ parseSheetNumber(s.sheet_name) }}</span>
          <span class="tab-name">{{ cleanTabTitle(s.sheet_name, unitGroupName) }}</span>
          <span
            v-if="getSheetTabBadge(s.sheet_key)"
            :class="['tab-status-dot', getSheetTabBadge(s.sheet_key).badgeClass]"
            :title="getSheetTabBadge(s.sheet_key).text"
          ></span>
        </button>
      </div>
    </div>

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
      :ai-feature-accessible="aiFeatureAccessible"
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
  listSheets,
  getSheetValidationSwitch,
  setSheetValidationSwitch,
  getSheetAiSwitch,
  setSheetAiSwitch,
  getDataAnalysisSchema,
  uploadBeihaiEfficiencyReport,
  uploadXianghaiEfficiencyReport,
  uploadGongreEfficiencyReport,
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
const activeSheetKey = ref(String(route.params.sheetKey ?? ''))
const sheetKey = computed(() => activeSheetKey.value)

// --- 单位多表格 Tabs 支持 ---
const unitSheets = ref([])
const unitGroupName = ref('')
const currentEfficiencyUnitType = computed(() => {
  const gName = (unitGroupName.value || unitName.value || '').trim()
  const sKey = (activeSheetKey.value || '').toLowerCase()
  if (gName.includes('北海') || sKey.startsWith('beihai')) return 'beihai'
  if (gName.includes('香海') || sKey.startsWith('xianghai')) return 'xianghai'
  if (gName.includes('供热') || sKey.startsWith('gongre')) return 'gongre'
  return null
})
const canUploadEfficiency = computed(() => !!currentEfficiencyUnitType.value)
const isBeihaiUnit = computed(() => currentEfficiencyUnitType.value === 'beihai')
const efficiencyUploadTitle = computed(() => {
  const type = currentEfficiencyUnitType.value
  if (type === 'beihai') return '上传《北海能效分析表》Excel，自动根据当前业务日期识别并填入北海三张表格'
  if (type === 'xianghai') return '上传《香海能效分析表》Excel，自动根据当前业务日期识别并填入香海热电厂表格'
  if (type === 'gongre') return '上传《供热公司能效表》Excel，自动根据当前业务日期识别并填入供热公司表及分中心补水量'
  return ''
})
const efficiencyUploading = ref(false)
const efficiencyFileInputRef = ref(null)
const sheetCache = new Map() // sheet_key -> 完整表格状态缓存
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
const isGlobalAdmin = computed(() => normalizedGroup.value === 'global_admin')
const isGroupAdminOrHigher = computed(() => normalizedGroup.value === 'global_admin' || normalizedGroup.value === 'group_admin')
const allowNonAdminAiReport = ref(false)
const sheetAiReportEnabled = ref(false)
const sheetAiSwitchLoading = ref(false)
const sheetAiSwitchSaving = ref(false)
const aiFeatureAccessible = computed(() => isGlobalAdmin.value || isGroupAdminOrHigher.value || sheetAiReportEnabled.value)
const shouldShowSheetAiToggle = computed(() => isGroupAdminOrHigher.value && activeSheetKey.value !== 'Coal_inventory_Sheet')
const sheetAiToggleDisabled = computed(() => sheetAiSwitchLoading.value || sheetAiSwitchSaving.value)

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
  if (!activeSheetKey.value) return false;
  const map = unitAnalysisToggleMap.value || {};
  if (Object.prototype.hasOwnProperty.call(map, activeSheetKey.value)) {
    return !!map[activeSheetKey.value];
  }
  return UNIT_ANALYSIS_DEFAULT_ENABLED.has(activeSheetKey.value);
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
  if (!activeSheetKey.value) return;
  const nextMap = { ...(unitAnalysisToggleMap.value || {}) };
  nextMap[activeSheetKey.value] = !!value;
  unitAnalysisToggleMap.value = nextMap;
  persistUnitAnalysisToggle(nextMap);
}

function handleUnitAnalysisToggleChange(event) {
  if (!canEditUnitAnalysisToggle.value) return;
  updateUnitAnalysisToggle(event.target.checked);
}

if (!projectKey || !pageKey || !activeSheetKey.value) {
  router.replace({ name: 'projects' });
}

// --- 模板和表格状态 ---
const projectName = computed(() => getProjectNameById(projectKey));
const sheetName = ref('');
const unitName = ref('');
const sheetDisplayName = computed(() => sheetName.value || activeSheetKey.value);

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
const shouldShowSheetValidationToggle = computed(() => activeSheetKey.value !== 'Coal_inventory_Sheet');
const canToggleSheetValidation = computed(() => auth.canManageValidationFor(projectKey));
const sheetValidationToggleDisabled = computed(
  () =>
    !shouldShowSheetValidationToggle.value ||
    !canToggleSheetValidation.value ||
    sheetValidationLoading.value ||
    sheetValidationSaving.value,
);

const isReadOnlyForDate = computed(() => isDailyPage.value && isUnitScopedEditor.value && bizDate.value !== canonicalBizDate.value);
const canSubmitCurrentProject = computed(() => auth.canSubmitFor(projectKey));
const submitDisabled = computed(() => !canSubmitCurrentProject.value || isReadOnlyForDate.value);
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

// 智能识别“同期值”列索引（对除 Global_admin 之外全量锁定只读）
function isPeerColumnIndex(index, colName = null) {
  // 1. 优先检查原始未替换占位符的列名
  const rawName = Array.isArray(baseColumns.value) ? baseColumns.value[index] : null;
  if (typeof rawName === 'string') {
    if (rawName.includes('同期') || rawName.includes('去年')) return true;
  }
  // 2. 检查当前显示的列名或日期
  const currentName = colName || (Array.isArray(columns.value) ? columns.value[index] : null);
  if (typeof currentName === 'string') {
    if (currentName.includes('同期') || currentName.includes('去年')) return true;
    const peerStr = peerDateYYYYMMDD(bizDate.value);
    if (peerStr && currentName.includes(peerStr)) return true;
  }
  // 3. 5 列标准日报表 (项目, 计量单位, 本期日, 同期日, 解释说明) -> 第 3 列固定为同期日
  if (Array.isArray(columns.value) && columns.value.length === 5 && index === 3) {
    return true;
  }
  return false;
}

function applyReadonlyToColumns() {
  if (!Array.isArray(gridColumns.value)) return;
  const shouldLockAll = isReadOnlyForDate.value;
  gridColumns.value = gridColumns.value.map((def, index) => {
    let locked = Boolean(def.__locked) || (shouldLockAll && (templateType.value === 'standard' || templateType.value === 'crosstab'));
    // 同期值字段权限控制：除 Global_admin 之外，全量强制设为只读不可修改
    if (!isGlobalAdmin.value && isPeerColumnIndex(index, def.name)) {
      locked = true;
    }
    const currentReadonly = def.readonly === undefined ? false : def.readonly;
    if (currentReadonly === locked) {
      return def;
    }
    return { ...def, readonly: locked, __locked: Boolean(def.__locked) || (!isGlobalAdmin.value && isPeerColumnIndex(index, def.name)) };
  });
}

async function loadSheetValidationSwitch() {
  if (!shouldShowSheetValidationToggle.value || !projectKey || !activeSheetKey.value) {
    sheetValidationEnabled.value = true;
    return;
  }
  sheetValidationLoading.value = true;
  sheetValidationError.value = '';
  try {
    const payload = await getSheetValidationSwitch(projectKey, activeSheetKey.value, { config: pageConfig.value });
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
    !activeSheetKey.value
  ) {
    return;
  }
  sheetValidationSaving.value = true;
  const previous = sheetValidationEnabled.value;
  sheetValidationEnabled.value = nextValue;
  try {
    await setSheetValidationSwitch(projectKey, activeSheetKey.value, nextValue, { config: pageConfig.value });
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

async function loadSheetAiSwitch() {
  if (!projectKey || !activeSheetKey.value) {
    sheetAiReportEnabled.value = false
    return
  }
  sheetAiSwitchLoading.value = true
  try {
    const payload = await getSheetAiSwitch(projectKey, activeSheetKey.value, { config: pageConfig.value })
    sheetAiReportEnabled.value = Boolean(payload?.ai_report_enabled)
  } catch (err) {
    // fail silently or log
    console.error('Failed to load AI switch:', err)
  } finally {
    sheetAiSwitchLoading.value = false
  }
}

async function updateSheetAiSwitch(nextValue) {
  if (!projectKey || !activeSheetKey.value || !shouldShowSheetAiToggle.value) return
  sheetAiSwitchSaving.value = true
  const previous = sheetAiReportEnabled.value
  sheetAiReportEnabled.value = nextValue
  try {
    await setSheetAiSwitch(projectKey, activeSheetKey.value, nextValue, { config: pageConfig.value })
  } catch (err) {
    console.error('Failed to save AI switch:', err)
    sheetAiReportEnabled.value = previous
    alert('更新 AI 开关失败：' + (err.message || '未知错误'))
  } finally {
    sheetAiSwitchSaving.value = false
  }
}

function onSheetAiToggle(event) {
  if (sheetAiToggleDisabled.value) {
    if (event?.target) event.target.checked = sheetAiReportEnabled.value
    return
  }
  const checked = Boolean(event?.target?.checked)
  updateSheetAiSwitch(checked)
}

// --- 渲染逻辑：标准模板 ---
async function setupStandardGrid(tpl) {
  const readonlyLimit = resolveReadonlyLimit(tpl.columns);
  readOnlyThreshold.value = readonlyLimit;
  const isConstant = templateType.value === 'constant';
  gridColumns.value = tpl.columns.map((colName, index) => {
    const isConstantPeerColumn = isConstant && (index === tpl.columns.length - 1) && (index > readonlyLimit);
    const isPeer = isPeerColumnIndex(index, colName);
    const locked = index <= readonlyLimit || isConstantPeerColumn || (!isGlobalAdmin.value && isPeer);
    return {
      prop: `c${index}`,
      name: String(colName ?? ''),
      autoSize: true,
      minSize: index === 0 ? 160 : 120,
      __locked: locked,
      readonly: locked || isReadOnlyForDate.value,
    };
  });
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
async function loadTemplate(targetKey = null) {
  const currentKey = targetKey || activeSheetKey.value;
  isLoadingTemplate.value = true;
  linkageMap.value = new Map();
  const rawTemplate = await getTemplate(projectKey, currentKey, { config: pageConfig.value });
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
        currentKey,
        { project_key: projectKey, sheet_key: currentKey, biz_date: bizDate.value, request_id: __rid1 },
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
        currentKey,
        { project_key: projectKey, sheet_key: currentKey, request_id: __ridc },
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
        currentKey,
        { project_key: projectKey, sheet_key: currentKey, biz_date: bizDate.value, request_id: __rid2 },
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
  if (!canSubmitCurrentProject.value) {
    window.alert('当前账号未获授权提交该项目日报数据。');
    return;
  }
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
    sheet_key: activeSheetKey.value,
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
    await submitData(projectKey, activeSheetKey.value, payload, { config: pageConfig.value });
    submitTime.value = currentSubmitTime;
    saveCurrentSheetToCache(activeSheetKey.value);
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

// --- 单位多表格 Tabs 支持与一并提交方法 ---

function parseSheetNumber(sheetName) {
  if (!sheetName) return ''
  const m = String(sheetName).match(/^(\d+)[\.、\s]*/)
  return m ? m[1] : ''
}

function cleanTabTitle(title, unitNameStr) {
  if (!title) return ''
  let s = String(title)
  // 去掉前导序号（由 parseSheetNumber 独立展示数字徽标）
  s = s.replace(/^\d+[\.、\s]*/, '').trim()
  // 去掉单位名重复
  if (unitNameStr && s.includes(unitNameStr)) {
    const trimmed = s.replace(unitNameStr, '').trim()
    if (trimmed && trimmed !== '表' && trimmed !== '（表）' && trimmed !== '()') {
      s = trimmed
    }
  }
  // 去掉外层括号
  s = s.replace(/^[（\(](.*?)[）\)]/, '$1').trim()
  if (!s.endsWith('表')) {
    s += '表'
  }
  return s || title
}

function getSheetTabBadge(targetKey) {
  const cached = sheetCache.get(targetKey)
  if (!cached) return null
  const issues = Array.from(cached.cellValidationMap?.values() || [])
  const hasErr = issues.some(i => i.level === 'error')
  if (hasErr) {
    return { text: '校验未通过', badgeClass: 'tab-status-dot--error' }
  }
  if (cached.submitTime) {
    return { text: '已提交', badgeClass: 'tab-status-dot--success' }
  }
  return null
}

async function loadUnitSheets() {
  if (!projectKey || !pageConfig.value) return
  try {
    const res = await listSheets(projectKey, pageConfig.value)
    const catalog = res?.content || res
    if (!catalog || typeof catalog !== 'object') return
    
    let targetUnit = ''
    for (const [k, meta] of Object.entries(catalog)) {
      if (k === activeSheetKey.value) {
        targetUnit = meta?.unit_name ? String(meta.unit_name).trim() : ''
        break
      }
    }
    unitGroupName.value = targetUnit
    
    if (targetUnit) {
      const matched = []
      for (const [k, meta] of Object.entries(catalog)) {
        const u = meta?.unit_name ? String(meta.unit_name).trim() : ''
        if (u === targetUnit) {
          matched.push({
            sheet_key: k,
            sheet_name: meta?.sheet_name || k,
            unit_name: u,
          })
        }
      }
      unitSheets.value = matched
    } else {
      unitSheets.value = [{
        sheet_key: activeSheetKey.value,
        sheet_name: sheetName.value || activeSheetKey.value,
        unit_name: unitName.value || ''
      }]
    }
  } catch (err) {
    console.warn('[DataEntryView] 加载单位表格列表失败', err)
  }
}

function saveCurrentSheetToCache(key = null) {
  const targetKey = key || activeSheetKey.value
  if (!targetKey) return
  sheetCache.set(targetKey, {
    columns: [...columns.value],
    baseColumns: [...baseColumns.value],
    rows: JSON.parse(JSON.stringify(rows.value || [])),
    gridColumns: [...gridColumns.value],
    gridSource: JSON.parse(JSON.stringify(gridSource.value || [])),
    sheetName: sheetName.value,
    unitName: unitName.value,
    unitId: unitId.value,
    templateType: templateType.value,
    templateDicts: JSON.parse(JSON.stringify(templateDicts.value || {})),
    submitTime: submitTime.value,
    readOnlyThreshold: readOnlyThreshold.value,
    linkageMap: new Map(linkageMap.value),
    rowLabelIndex: new Map(rowLabelIndex.value),
    templateValidationRaw: templateValidationRaw.value,
    validationRuleMap: new Map(validationRuleMap.value),
    validationDependents: new Map(validationDependents.value),
    cellValidationMap: new Map(cellValidationMap.value),
    virtualValidationRules: [...virtualValidationRules.value],
    validationExplanationMap: new Map(validationExplanationMap.value),
    sheetValidationEnabled: sheetValidationEnabled.value,
    sheetAiReportEnabled: sheetAiReportEnabled.value,
    isLoaded: true,
  })
}

function restoreSheetFromCache(targetKey) {
  const cached = sheetCache.get(targetKey)
  if (!cached) return
  columns.value = [...cached.columns]
  baseColumns.value = [...cached.baseColumns]
  rows.value = JSON.parse(JSON.stringify(cached.rows))
  gridColumns.value = [...cached.gridColumns]
  gridSource.value = JSON.parse(JSON.stringify(cached.gridSource))
  sheetName.value = cached.sheetName
  unitName.value = cached.unitName
  unitId.value = cached.unitId
  templateType.value = cached.templateType
  templateDicts.value = JSON.parse(JSON.stringify(cached.templateDicts))
  submitTime.value = cached.submitTime
  readOnlyThreshold.value = cached.readOnlyThreshold
  linkageMap.value = new Map(cached.linkageMap)
  rowLabelIndex.value = new Map(cached.rowLabelIndex)
  templateValidationRaw.value = cached.templateValidationRaw
  validationRuleMap.value = new Map(cached.validationRuleMap)
  validationDependents.value = new Map(cached.validationDependents)
  cellValidationMap.value = new Map(cached.cellValidationMap)
  virtualValidationRules.value = [...cached.virtualValidationRules]
  validationExplanationMap.value = new Map(cached.validationExplanationMap)
  sheetValidationEnabled.value = cached.sheetValidationEnabled
  sheetAiReportEnabled.value = cached.sheetAiReportEnabled
}

async function onSwitchSheetTab(targetKey) {
  if (!targetKey || targetKey === activeSheetKey.value || isSubmitting.value) {
    return
  }
  // 1. 保存当前 sheet 的状态到缓存
  saveCurrentSheetToCache(activeSheetKey.value)

  // 2. 切换当前活跃 sheetKey
  activeSheetKey.value = targetKey

  // 3. 尝试从缓存恢复
  if (sheetCache.has(targetKey)) {
    restoreSheetFromCache(targetKey)
    if (templateType.value === 'standard') {
      rebuildValidationRulesFromRows(rows.value)
      const linkagePayload = {
        entries: (templateDicts.value && templateDicts.value.entries) ? templateDicts.value.entries : {},
        linkage_dict: templateDicts.value ? templateDicts.value.linkage_dict : undefined,
        ['指标联动']: templateDicts.value ? templateDicts.value['指标联动'] : undefined,
      }
      rebuildLinkageMapFromPayload(rows.value, linkagePayload, { syncGrid: false })
      if (validationEnabled.value) {
        runFullValidation()
      } else {
        clearAllValidationIssues()
      }
    }
    applyReadonlyToColumns()
  } else {
    // 4. 首次加载该 sheet
    await loadTemplate(targetKey)
    saveCurrentSheetToCache(targetKey)
  }

  // 5. 替换 URL 路由，保持当前 Tab 状态
  try {
    router.replace({
      params: { ...route.params, sheetKey: targetKey },
      query: route.query,
    })
  } catch (err) {
    // 忽略导航相同路由报错
  }

  // 6. 重新检查校验状态与分析开关
  loadSheetValidationSwitch()
  loadSheetAiSwitch()
}

function buildPayloadForCachedState(targetSheetKey, cached, currentSubmitTime) {
  let submissionData
  if (cached.templateType === 'crosstab') {
    submissionData = {
      columns: cached.columns,
      rows: (cached.gridSource || []).map(record => cached.columns.map((_, i) => record[`c${i}`] ?? '')),
    }
  } else {
    const readonlyLimit = resolveReadonlyLimit(cached.columns)
    const filledRows = (cached.rows || []).map((row, ri) => {
      const newRow = [...row]
      const record = cached.gridSource?.[ri] ?? {}
      for (let ci = readonlyLimit + 1; ci < cached.columns.length; ci++) {
        const key = `c${ci}`
        if (record[key] !== undefined) {
          newRow[ci] = record[key]
        }
      }
      return newRow
    })
    submissionData = {
      columns: cached.columns,
      rows: filledRows,
    }
  }

  const payload = {
    project_key: projectKey,
    project_name: projectName.value || projectKey,
    sheet_key: targetSheetKey,
    sheet_name: cached.sheetName || targetSheetKey,
    unit_name: cached.unitName || unitGroupName.value || '',
    biz_date: bizDate.value,
    unit_id: cached.unitId || '',
    submit_time: currentSubmitTime,
    status: 'submit',
    ...submissionData,
  }

  const dictBundle = cached.templateDicts || {}
  const entryMap = dictBundle.entries || {}
  for (const [dictKey, dictValue] of Object.entries(entryMap)) {
    payload[dictKey] = cloneDictValue(dictValue)
  }
  if (!payload.item_dict && dictBundle.itemPrimary) {
    payload.item_dict = cloneDictValue(dictBundle.itemPrimary)
  }
  if (!payload.company_dict && dictBundle.companyPrimary) {
    payload.company_dict = cloneDictValue(dictBundle.companyPrimary)
  }
  return payload
}

async function onSubmitAll() {
  if (!canSubmitCurrentProject.value) {
    window.alert('当前账号未获授权提交该项目日报数据。')
    return
  }
  if (submitDisabled.value) {
    window.alert('所选日期仅支持查看，不能提交修改。')
    return
  }
  if (isSubmitting.value) {
    return
  }

  // 1. 保存当前活跃表格状态
  saveCurrentSheetToCache(activeSheetKey.value)

  // 2. 补齐尚未加载过的其他表格
  for (const s of unitSheets.value) {
    if (!sheetCache.has(s.sheet_key)) {
      try {
        await onSwitchSheetTab(s.sheet_key)
        saveCurrentSheetToCache(s.sheet_key)
      } catch (e) {
        console.error(`补齐加载表格 ${s.sheet_key} 失败`, e)
      }
    }
  }

  // 3. 统一全局校验：检查每一张表格是否有阻断性错误
  if (validationEnabled.value) {
    for (const s of unitSheets.value) {
      const cached = sheetCache.get(s.sheet_key)
      if (!cached) continue
      const issues = Array.from(cached.cellValidationMap?.values() || [])
      const blocking = issues.filter(issue => issue.level === 'error')
      if (blocking.length > 0) {
        await onSwitchSheetTab(s.sheet_key)
        showSubmitFeedback('error', `【${cleanTabTitle(s.sheet_name, unitGroupName.value)}】存在未通过的校验项，已为您自动切换到该表，请修正后再提交。`, { autoHide: false })
        return
      }
    }
  }

  // 4. 并发向后端提交全部表格
  isSubmitting.value = true
  const now = new Date()
  const pad = n => String(n).padStart(2, '0')
  const currentSubmitTime = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`

  try {
    const submitTasks = unitSheets.value.map(async (s) => {
      const cached = sheetCache.get(s.sheet_key)
      if (!cached) return { ok: true }
      const payload = buildPayloadForCachedState(s.sheet_key, cached, currentSubmitTime)
      return submitData(projectKey, s.sheet_key, payload, { config: pageConfig.value })
    })

    await Promise.all(submitTasks)
    submitTime.value = currentSubmitTime
    for (const s of unitSheets.value) {
      const cached = sheetCache.get(s.sheet_key)
      if (cached) cached.submitTime = currentSubmitTime
    }

    showSubmitFeedback('success', `【${unitGroupName.value || unitName.value}】全部报表（共 ${unitSheets.value.length} 张）数据已成功一并提交入库！`)
    startRefreshCountdown(3)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    console.error('[data-entry] 一并提交失败', message)
    clearRefreshCountdown()
    showSubmitFeedback('error', `一并提交失败：${message || '请稍后重试'}`)
  } finally {
    isSubmitting.value = false
  }
}

// --- 能效报表上传与回填（支持北海、香海、供热公司） ---
function triggerEfficiencyUpload() {
  if (efficiencyUploading.value) return
  if (efficiencyFileInputRef.value) {
    efficiencyFileInputRef.value.value = ''
    efficiencyFileInputRef.value.click()
  }
}

async function onEfficiencyFileSelected(event) {
  const files = event?.target?.files
  if (!files || !files.length) return
  const file = files[0]
  if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
    alert('请选择 Excel 文件（.xlsx 或 .xls）')
    return
  }

  const unitType = currentEfficiencyUnitType.value
  const unitDisplayName = unitType === 'beihai' ? '北海热电厂' : (unitType === 'xianghai' ? '香海热电厂' : '供热公司')

  efficiencyUploading.value = true
  showSubmitFeedback('info', `正在智能解析${unitDisplayName}能效报表（业务日期: ${bizDate.value}）…`, { autoHide: false })
  try {
    let res = null
    if (unitType === 'beihai') {
      res = await uploadBeihaiEfficiencyReport(projectKey, file, bizDate.value)
    } else if (unitType === 'xianghai') {
      res = await uploadXianghaiEfficiencyReport(projectKey, file, bizDate.value)
    } else if (unitType === 'gongre') {
      res = await uploadGongreEfficiencyReport(projectKey, file, bizDate.value)
    } else {
      throw new Error('当前单位暂不支持能效报表上传解析')
    }

    if (!res || !res.ok) {
      throw new Error(res?.message || '解析能效分析表失败')
    }

    await applyEfficiencyDataToSheets(res.data)

    showSubmitFeedback(
      'success',
      `🎉 ${res.summary?.message || `已成功自动识别填入${unitDisplayName}报表本期数据！`}（同期值严格保持原状未修改，请核对各标签页确认无误后点击“一并提交”入库）。`,
      { autoHide: false }
    )
  } catch (err) {
    console.error('[DataEntryView] 解析能效分析表失败', err)
    showSubmitFeedback('error', `解析能效报表失败：${err.message || String(err)}`, { autoHide: false })
  } finally {
    efficiencyUploading.value = false
    if (event?.target) event.target.value = ''
  }
}

function findRowIndexInList(rowsList, cell) {
  if (!Array.isArray(rowsList)) return -1
  const targetLabel = String(cell.row_label || '').trim()
  const targetSub = cell.sub_label ? String(cell.sub_label).trim() : ''
  if (targetSub) {
    const found = rowsList.findIndex(row => {
      const c0 = String(row.c0 || '').trim()
      const c1 = String(row.c1 || '').trim()
      const labelMatch = c0 === targetLabel || c0.includes(targetLabel) || targetLabel.includes(c0)
      const subMatch = c1 === targetSub || c1.startsWith(targetSub) || targetSub.startsWith(c1)
      return labelMatch && subMatch
    })
    if (found !== -1) return found
  }
  return rowsList.findIndex(row => String(row.c0 || '').trim() === targetLabel)
}

function isPeerColumnForTable(colIdx, tableCols, baseCols = null) {
  if (!Array.isArray(tableCols) || colIdx < 0 || colIdx >= tableCols.length) return false
  if (Array.isArray(baseCols) && typeof baseCols[colIdx] === 'string') {
    const raw = baseCols[colIdx]
    if (raw.includes('同期') || raw.includes('去年')) return true
  }
  const cName = String(tableCols[colIdx] ?? '')
  if (cName.includes('同期') || cName.includes('去年')) return true
  const peerStr = peerDateYYYYMMDD(bizDate.value)
  if (peerStr && cName.includes(peerStr)) return true
  if (tableCols.length === 5 && colIdx === 3 && !cName.includes('本期')) {
    return true
  }
  return false
}

async function applyEfficiencyDataToSheets(sheetsData) {
  if (!sheetsData || typeof sheetsData !== 'object') return

  saveCurrentSheetToCache(activeSheetKey.value)

  const NOTE_ONLY_LABELS = new Set(['主设备启停情况', '设备启停情况', '突发情况说明'])

  for (const [sheetKey, sheetPayload] of Object.entries(sheetsData)) {
    const cells = sheetPayload?.cells || []
    if (!cells.length) continue

    if (sheetKey === activeSheetKey.value) {
      // 当前活动表格
      const curCols = columns.value || []
      const curBaseCols = baseColumns.value || []
      let updatedCount = 0
      for (const cell of cells) {
        const targetLabel = String(cell.row_label || '').trim()
        const rIdx = findRowIndexInList(gridSource.value, cell)
        if (rIdx === -1) continue

        // 规范安全保护：设备启停情况与突发情况说明绝不写入本期或同期列，必须保留占位符，说明只能填在最后一列（备注）
        if (NOTE_ONLY_LABELS.has(targetLabel) || String(gridSource.value[rIdx]?.c2 || '').includes('若有请填右侧')) {
          const lastColIdx = (curCols.length || 5) - 1
          const noteProp = `c${lastColIdx}`
          const valStr = cell.value !== null && cell.value !== undefined ? String(cell.value).trim() : ''
          if (valStr && valStr !== '（若有请填右侧）' && valStr !== '——→') {
            gridSource.value[rIdx][noteProp] = valStr
            if (rows.value && rows.value[rIdx]) rows.value[rIdx][lastColIdx] = valStr
            updatedCount++
          }
          continue
        }

        let targetCol = (cell.col_index !== undefined && cell.col_index !== null) ? Number(cell.col_index) : -1
        if (targetCol === -1) {
          const currentIdx = curCols.findIndex(c => String(c ?? '').includes('本期'))
          targetCol = currentIdx !== -1 ? currentIdx : 2
        }
        // 安全保护：表级严格判定，严禁向同期列写入数据
        if (isPeerColumnForTable(targetCol, curCols, curBaseCols)) continue

        const valStr = cell.value !== null && cell.value !== undefined ? String(cell.value) : ''
        const colProp = `c${targetCol}`
        gridSource.value[rIdx][colProp] = valStr
        if (rows.value && rows.value[rIdx]) rows.value[rIdx][targetCol] = valStr
        updatedCount++
      }
      if (updatedCount > 0) {
        gridSource.value = [...gridSource.value]
        // 联动关联行同步
        const map = linkageMap.value
        if (map instanceof Map && map.size > 0) {
          for (let r = 0; r < gridSource.value.length; r++) {
            const related = map.get(r)
            if (related && related.size > 0) {
              const val = gridSource.value[r]?.c2
              related.forEach(linkedIdx => {
                if (gridSource.value[linkedIdx]) {
                  gridSource.value[linkedIdx].c2 = val
                  if (rows.value && rows.value[linkedIdx]) rows.value[linkedIdx][2] = val
                }
              })
            }
          }
        }
        // 校验当前表所有行
        if (validationEnabled.value && templateType.value === 'standard') {
          for (let r = 0; r < gridSource.value.length; r++) {
            validateRow(r)
          }
        }
        saveCurrentSheetToCache(activeSheetKey.value)
      }
    } else {
      // 其它子表格（缓存在 sheetCache）
      let cached = sheetCache.get(sheetKey)
      if (!cached) {
        try {
          const rawTpl = await getTemplate(projectKey, sheetKey, { config: pageConfig.value })
          if (rawTpl && Array.isArray(rawTpl.rows)) {
            // 处理列头日期占位符（生成权威日期列头，如 2026-11-05 与 2025-11-05）
            const baseCols = Array.isArray(rawTpl.columns) ? [...rawTpl.columns] : []
            const renderedCols = isDailyPage.value ? replaceDatePlaceholdersInColumns(baseCols) : baseCols
            rawTpl.columns = renderedCols
            const { template: tpl } = applyTemplatePlaceholders(rawTpl)

            // 关键：必须调用 queryData 镜像查询，拉取该表在当前业务日期下的数据库已存数据（尤其是同期值！）
            let tplRows = tpl.rows || []
            try {
              const q = await queryData(
                projectKey,
                sheetKey,
                { project_key: projectKey, sheet_key: sheetKey, biz_date: bizDate.value },
                { config: pageConfig.value }
              )
              if (q && Array.isArray(q.rows)) {
                tplRows = q.rows
              }
            } catch (qErr) {
              console.warn('[DataEntryView] 预加载子表格 queryData 失败', sheetKey, qErr)
            }

            const readonlyLimit = resolveReadonlyLimit(tpl.columns)
            const isConstant = (tpl.template_type || 'standard') === 'constant'
            const gridCols = (tpl.columns || []).map((name, index) => {
              const isConstantPeer = isConstant && (index === tpl.columns.length - 1) && (index > readonlyLimit)
              const isPeer = isPeerColumnIndex(index, name)
              const locked = index <= readonlyLimit || isConstantPeer || (!isGlobalAdmin.value && isPeer)
              return {
                prop: `c${index}`,
                name: String(name ?? '') + (!isGlobalAdmin.value && isPeer ? ' 🔒' : ''),
                size: index === 0 ? 220 : 120,
                __locked: locked,
                readonly: locked || isReadOnlyForDate.value,
              }
            })

            const src = tplRows.map(row => {
              const rec = {}
              for (let ci = 0; ci < (tpl.columns?.length || 5); ci++) {
                rec[`c${ci}`] = (row?.[ci] !== null && row?.[ci] !== undefined) ? String(row[ci]) : ''
              }
              return rec
            })

            sheetCache.set(sheetKey, {
              columns: tpl.columns || [],
              baseColumns: baseCols,
              rows: JSON.parse(JSON.stringify(tplRows)),
              gridColumns: gridCols,
              gridSource: src,
              sheetName: tpl.sheet_name || sheetKey,
              unitName: tpl.unit_name || unitGroupName.value || '',
              unitId: tpl.unit_id || '',
              templateType: tpl.template_type || 'standard',
              templateDicts: tpl.dicts || {},
              submitTime: '',
              readOnlyThreshold: readonlyLimit,
              linkageMap: new Map(),
              rowLabelIndex: new Map(),
              templateValidationRaw: tpl.validation || null,
              validationRuleMap: new Map(),
              validationDependents: new Map(),
              cellValidationMap: new Map(),
              virtualValidationRules: [],
              validationExplanationMap: new Map(),
              sheetValidationEnabled: true,
              sheetAiReportEnabled: false,
              isLoaded: true,
            })
            cached = sheetCache.get(sheetKey)
          }
        } catch (e) {
          console.warn('[DataEntryView] 预加载子表格失败', sheetKey, e)
        }
      }

      if (cached && Array.isArray(cached.gridSource)) {
        const cachedCols = cached.columns || []
        const cachedBaseCols = cached.baseColumns || []
        for (const cell of cells) {
          const targetLabel = String(cell.row_label || '').trim()
          const rIdx = findRowIndexInList(cached.gridSource, cell)
          if (rIdx === -1) continue

          if (NOTE_ONLY_LABELS.has(targetLabel) || String(cached.gridSource[rIdx]?.c2 || '').includes('若有请填右侧')) {
            const lastColIdx = (cachedCols.length || 5) - 1
            const noteProp = `c${lastColIdx}`
            const valStr = cell.value !== null && cell.value !== undefined ? String(cell.value).trim() : ''
            if (valStr && valStr !== '（若有请填右侧）' && valStr !== '——→') {
              cached.gridSource[rIdx][noteProp] = valStr
              if (cached.rows && cached.rows[rIdx]) cached.rows[rIdx][lastColIdx] = valStr
            }
            continue
          }

          let targetCol = (cell.col_index !== undefined && cell.col_index !== null) ? Number(cell.col_index) : -1
          if (targetCol === -1) {
            const currentIdx = cachedCols.findIndex(c => String(c ?? '').includes('本期'))
            targetCol = currentIdx !== -1 ? currentIdx : 2
          }
          if (isPeerColumnForTable(targetCol, cachedCols, cachedBaseCols)) continue

          const valStr = cell.value !== null && cell.value !== undefined ? String(cell.value) : ''
          const colProp = `c${targetCol}`
          cached.gridSource[rIdx][colProp] = valStr
          if (cached.rows && cached.rows[rIdx]) cached.rows[rIdx][targetCol] = valStr
        }
      }
    }
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
    // 非 Global_admin 用户严禁修改同期值列
    const colIdx = parseInt(String(prop).replace('c', ''), 10);
    if (!isNaN(colIdx) && !isGlobalAdmin.value && isPeerColumnIndex(colIdx)) {
      continue;
    }
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
  await loadUnitSheets();
  await loadSheetValidationSwitch();
  await loadSheetAiSwitch();
  await loadTemplate();
  saveCurrentSheetToCache(activeSheetKey.value);
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
      const isConstant = templateType.value === 'constant';
      const colDefs = q.columns.map((name, index) => {
        const isConstantPeerColumn = isConstant && (index === q.columns.length - 1) && (index > readOnlyThreshold.value);
        const locked = index <= readOnlyThreshold.value || isConstantPeerColumn;
        return {
          name: String(name ?? ''),
          prop: `c${index}`,
          size: index === 0 ? 220 : 120,
          __locked: locked,
          readonly: locked || isReadOnlyForDate.value,
        };
      });
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
    // 日期变更时清空多表旧日期缓存
    sheetCache.clear();
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
        activeSheetKey.value,
        { project_key: projectKey, sheet_key: activeSheetKey.value, biz_date: bizDate.value, request_id: __rid4 },
        { config: pageConfig.value }
      );
      if (q && q.__request_id && q.__request_id !== latestRequestId.value) {
        return
      }
      await applyStandardQueryResult(q);
      saveCurrentSheetToCache(activeSheetKey.value);
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
    sheetCache.clear();
    try {
      const __rid5 = newRequestId(); latestRequestId.value = __rid5;
      const q = await queryData(
        projectKey,
        activeSheetKey.value,
        { project_key: projectKey, sheet_key: activeSheetKey.value, biz_date: bizDate.value, request_id: __rid5 },
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
    loadSheetAiSwitch();
  },
);

watch(
  () => pageConfig.value,
  () => {
    loadSheetValidationSwitch();
    loadSheetAiSwitch();
  },
);

async function loadAiFlag() {
  try {
    const payload = await getDataAnalysisSchema(projectKey)
    const flags = payload?.ai_report_flags || {}
    allowNonAdminAiReport.value = Boolean(flags.allow_non_admin)
  } catch (err) {
    allowNonAdminAiReport.value = false
  }
}

watch(
  () => pageConfig.value,
  () => {
    loadAiFlag()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (submitFeedbackTimer !== null) {
    clearTimeout(submitFeedbackTimer);
    submitFeedbackTimer = null;
  }
  clearRefreshCountdown();
});
</script>

<style scoped>
.topbar {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  align-items: flex-start;
  justify-content: space-between;
}
.topbar__title-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1 1 220px;
}
.topbar__actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-end;
  flex: 1 1 320px;
}
.topbar__status-row,
.topbar__action-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  width: 100%;
}
.topbar__buttons {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}
.topbar__buttons .btn {
  min-width: 120px;
}
.topbar__date {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-right: 8px;
}

.table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.table-wrap :deep(revo-grid) {
  min-width: 980px;
}

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
.table-wrap { overflow: auto; }

@media (max-width: 768px) {
  .topbar {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    margin-bottom: 12px;
  }
  .topbar__title-group {
    flex: none;
    gap: 4px;
  }
  .topbar__actions {
    align-items: stretch;
    flex: none;
    gap: 8px;
  }
  .topbar__status-row,
  .topbar__action-row {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .submit-time {
    margin-right: 0;
    width: auto;
    flex: 1 1 100%;
  }
  .topbar__status-row {
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
  }
  .unit-analysis-inline {
    width: auto;
    justify-content: flex-start;
    flex: 0 0 auto;
    max-width: 100%;
  }
  .topbar__date {
    width: 100%;
    justify-content: space-between;
  }
  .topbar__buttons {
    flex-direction: column;
  }
  .topbar__buttons .btn {
    width: 100%;
  }
  .validation-panel__item {
    flex-direction: column;
    align-items: flex-start;
  }
  .table-wrap {
    margin: 0 -12px;
    padding: 0 12px;
  }
  .table-wrap.card {
    border-radius: 0;
  }
}

/* 多表格单位 Tabs 栏样式 */
/* 多表格单位现代分段胶囊标签栏 (Segmented Pill Tabs) */
.unit-tabs-nav-wrapper {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  overflow-x: auto;
  scrollbar-width: none;
}
.unit-tabs-nav-wrapper::-webkit-scrollbar {
  display: none;
}

.unit-tabs-nav {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background-color: #f1f5f9;
  padding: 4px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05);
}

.unit-tab-pill {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: #64748b;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.unit-tab-pill:hover:not(.unit-tab-pill--active) {
  color: #1e293b;
  background-color: rgba(255, 255, 255, 0.7);
}

.unit-tab-pill--active {
  background-color: #ffffff !important;
  color: #1d4ed8 !important;
  font-weight: 600;
  border-color: #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 4px 6px -1px rgba(15, 23, 42, 0.04);
}

.tab-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 5px;
  border-radius: 6px;
  background-color: #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  transition: all 0.2s ease;
}

.unit-tab-pill--active .tab-index {
  background-color: #eff6ff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
}

.tab-name {
  line-height: 1.2;
}

.tab-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  display: inline-block;
  margin-left: 2px;
}

.tab-status-dot--success {
  background-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
}

.tab-status-dot--error {
  background-color: #ef4444;
  box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.25);
}

/* 顶部操作区按钮优化 */
.efficiency-upload-btn {
  font-weight: 600 !important;
  color: #0369a1 !important;
  background: #f0f9ff !important;
  border: 1px solid #bae6fd !important;
  border-radius: 8px !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(2, 132, 199, 0.08);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.efficiency-upload-btn:hover {
  background: #e0f2fe !important;
  border-color: #7dd3fc !important;
  color: #0284c7 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(2, 132, 199, 0.15);
}

.submit-all-btn {
  font-weight: 600 !important;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border-color: #047857 !important;
  box-shadow: 0 2px 4px rgba(5, 150, 105, 0.2);
  transition: all 0.2s ease;
}
.submit-all-btn:hover {
  background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
  box-shadow: 0 4px 8px rgba(5, 150, 105, 0.25);
  transform: translateY(-1px);
}
.text-btn {
  font-size: 13px !important;
  color: #64748b !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  padding: 6px 10px !important;
}
.text-btn:hover {
  color: #1e293b !important;
  background: #f1f5f9 !important;
}
</style>
