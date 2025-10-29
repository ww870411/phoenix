<template>
  <div>
    <AppHeader />
    <div class="container">
    <Breadcrumbs :items="breadcrumbItems" class="breadcrumb-spacing" />
    <header class="topbar">
      <div style="display:flex;flex-direction:column;gap:6px;">
        <h2>数据填报</h2>
        <div class="sub">项目：{{ projectName }} ｜ 表：{{ sheetDisplayName }}</div>
      </div>
      <div class="right" style="display:flex;align-items:center;gap:8px;">
        <span class="submit-time" v-if="submitTime">最近提交：{{ submitTime }}</span>
        <label v-if="isDailyPage" class="date-group" title="业务日期" style="display:inline-flex;align-items:center;gap:6px;margin-right:8px;">
          <span>业务日期：</span>
          <input type="date" v-model="bizDate" />
        </label>
        <button class="btn ghost" @click="reloadTemplate">重载模板</button>
        <button class="btn primary" @click="onSubmit">提交</button>
      </div>
    </header>

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
  </div>
  </div>
</template>

<script setup>
import '../styles/theme.css'
import RevoGrid from '@revolist/vue3-datagrid'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { useRouter } from 'vue-router'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { getTemplate, queryData, submitData } from '../services/api';
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects';
import { useTemplatePlaceholders } from '../composables/useTemplatePlaceholders';

// --- 基本路由和状态 --- 
const route = useRoute();
const router = useRouter();
const { applyTemplatePlaceholders } = useTemplatePlaceholders();
const projectKey = String(route.params.projectKey ?? '');
const pageKey = String(route.params.pageKey ?? '');
const sheetKey = String(route.params.sheetKey ?? '');
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
const bizDate = ref(String(initialDate));
const latestRequestId = ref('');
function newRequestId() { return `${Date.now()}_${Math.random().toString(36).slice(2,8)}` }
// 在模板加载过程中，抑制由程序性设置 bizDate 引发的 watch 重入
const isLoadingTemplate = ref(false);

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

// --- RevoGrid 状态 ---
const gridColumns = ref([]);
const gridSource = ref([]);
const gridRef = ref(null);

// 根据模板类型控制列拉伸行为：常量指标页不拉伸，避免最后一列占满剩余空间
const gridStretch = computed(() => {
  return templateType.value !== 'constant'
});

// --- Helper --- 
function cloneDictValue(value) {
  if (value && typeof value === 'object') {
    try { return JSON.parse(JSON.stringify(value)); } catch (err) { return value; }
  }
  return value;
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

// --- 渲染逻辑：标准模板 ---
async function setupStandardGrid(tpl) {
  const readonlyLimit = resolveReadonlyLimit(tpl.columns);
  const colDefs = tpl.columns.map((colName, index) => {
    const base = {
      prop: `c${index}`,
      name: String(colName ?? ''),
      autoSize: true,
      minSize: index === 0 ? 160 : 120,
    };
    if (index <= readonlyLimit) {
      base.readonly = true;
    }
    return base;
  });
  gridColumns.value = colDefs;

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
  const colDefs = tpl.columns.map((name, index) => {
    const base = {
      prop: `c${index}`,
      name: String(name ?? ''),
      autoSize: true,
      minSize: index === 0 ? 160 : 120,
    };
    if (index <= readonlyLimit) {
      base.readonly = true;
    }
    return base;
  });
  gridColumns.value = colDefs;

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
  // 交叉表需先搭好列与占位行，再执行镜像查询，避免后续初始化覆盖查询结果
  if (templateType.value === 'crosstab') {
    await setupCrosstabGrid(tpl);
  } else {
    // 标准模板也需要预先搭好骨架，再查询填充
    await setupStandardGrid(tpl);
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
        } else {
          const colDefs = q.columns.map((name, index) => ({
            name: String(name ?? ''),
            prop: `c${index}`,
            size: index === 0 ? 180 : undefined,
            minSize: index === 0 ? 160 : 100,
            readonly: index < 2,
          }));
          gridColumns.value = colDefs;
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

  await submitData(projectKey, sheetKey, payload, { config: pageConfig.value });
  submitTime.value = currentSubmitTime;
}

// --- RevoGrid 事件处理 ---
function handleAfterEdit(evt) {
  const detail = evt?.detail ?? evt;
  const changes = Array.isArray(detail?.changes) ? detail.changes : (detail ? [detail] : []);
  for (const change of changes) {
    const { rowIndex, prop, val } = change || {};
    if (rowIndex == null || !prop) continue;
    if (!gridSource.value[rowIndex]) continue;
    gridSource.value[rowIndex][prop] = val;
  }
}

// --- 生命周期 ---
onMounted(async () => {
  await nextTick();
  await ensureProjectsLoaded().catch(() => {});
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
      }));
      gridColumns.value = colDefs;
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
        } else {
          const colDefs = q.columns.map((name, index) => ({
            name: String(name ?? ''),
            prop: `c${index}`,
            size: index === 0 ? 180 : undefined,
            minSize: index === 0 ? 160 : 100,
            readonly: index < 2,
          }));
          gridColumns.value = colDefs;
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

</script>

<style scoped>
.topbar { gap: 12px; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
.date-group input[type="date"] { padding: 4px 8px; border: 1px solid var(--border); border-radius: 6px; }
.breadcrumb-spacing { margin-bottom: 12px; display: inline-block; }
.submit-time { font-size: 13px; color: var(--muted); margin-right: auto; }
</style>
