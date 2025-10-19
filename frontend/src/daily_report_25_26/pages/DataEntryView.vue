<template>
  <div>
    <AppHeader />
    <div class="container">
    <header class="topbar">
      <div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;">
        <button class="btn light" @click="goDashboard">← 返回仪表盘</button>
        <div>
          <h2>数据填报</h2>
          <div class="sub">项目：{{ projectName }} ｜ 表：{{ sheetDisplayName }}</div>
        </div>
      </div>
      <div class="right" style="display:flex;align-items:center;gap:8px;">
        <label class="date">
          <span>业务日期</span>
          <input type="date" v-model="bizDate" @change="loadExisting" />
        </label>
        <button class="btn ghost" @click="reloadTemplate">重载模板</button>
        <button class="btn primary" @click="onSubmit">提交</button>
      </div>
    </header>
    <Breadcrumbs />

    <div class="table-wrap card" v-if="columns.length">
      <RevoGrid
        ref="gridRef"
        :row-headers="true"
        :hide-attribution="true"
        :stretch="true"
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
// 注意：@revolist/revogrid 未在 exports 中暴露 css 入口，
// 直接导入 css 会导致 Vite 依赖扫描报错（Missing specifier）。
// 使用官方 Vue 包装组件自动注册自定义元素，并结合自定义外层样式。
import AppHeader from '../components/AppHeader.vue'
import { useRouter } from 'vue-router'
import { computed, nextTick, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { getTemplate, queryData, submitData } from '../services/api';
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects';

const route = useRoute();
const router = useRouter();
const projectKey = String(route.params.projectKey ?? '');
const sheetKey = String(route.params.sheetKey ?? '');
const initialDate = new Date().toISOString().slice(0,10);

if (!projectKey || !sheetKey) {
  router.replace({ name: 'projects' });
}
const projectName = computed(() => getProjectNameById(projectKey));

const sheetName = ref('');
const sheetDisplayName = computed(() => sheetName.value || sheetKey);
const columns = ref([]);
const rows = ref([]);
const bizDate = ref(String(initialDate));
const values = reactive({});
const gridColumns = ref([]);
const gridSource = ref([]);
const gridRef = ref(null);
let textMeasureCtx = null;
function toKey(ri, ci) { return `${ri}-${ci}`; }

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

// 在数据流完成后调用 RevoGrid 的 autoSize，保证首列根据行名重新计算宽度
async function autoSizeFirstColumn() {
  await nextTick();
  if (!gridColumns.value.length) return;
  const gridComponent = gridRef.value;
  const gridElement = gridComponent?.$el ?? gridComponent;
  if (!gridElement) return;

  const computed = typeof window !== 'undefined' ? window.getComputedStyle(gridElement) : null;
  const font = computed?.font || '14px/1.4 "Segoe UI", Arial, sans-serif';
  const candidates = [];
  if (columns.value[0]) candidates.push(columns.value[0]);
  for (const row of gridSource.value) {
    if (row && row.c0 != null) candidates.push(row.c0);
  }
  const widest = candidates.reduce((max, content) => {
    const width = measureTextWidth(content, font);
    return width > max ? width : max;
  }, 0);
  const padding = 36; // 预留左右内边距与排序指示器空间
  const target = Math.max(gridColumns.value[0]?.minSize ?? 160, Math.ceil(widest) + padding);
  gridColumns.value = gridColumns.value.map((col, index) => {
    if (index !== 0) return col;
    return { ...col, size: target };
  });

  if (typeof gridElement.autoSizeColumn === 'function') {
    try {
      gridElement.autoSizeColumn('c0', true);
    } catch (err) {
      try {
        gridElement.autoSizeColumn(0, true);
      } catch (innerErr) {
        // 保底静默失败，避免影响主流程
      }
    }
  }
}

async function loadTemplate() {
  const tpl = await getTemplate(projectKey, sheetKey);
  sheetName.value = tpl.sheet_name || '';
  columns.value = tpl.columns || [];
  rows.value = tpl.rows || [];
  // 清空当前值
  Object.keys(values).forEach(k => delete values[k]);

  // 构造 RevoGrid 列配置：c0=项目(只读)、c1=计量单位(只读)、c2+ 可编辑
  const colDefs = [];
  colDefs.push({
    prop: 'c0',
    name: columns.value[0] ?? '项目',
    readonly: true,
    autoSize: true,
    minSize: 160,
  });
  colDefs.push({
    prop: 'c1',
    name: columns.value[1] ?? '计量单位',
    readonly: true,
    autoSize: true,
    minSize: 120,
  });
  const fillable = columns.value.map((_, i) => i).filter(i => i >= 2);
  for (const ci of fillable) {
    colDefs.push({
      prop: `c${ci}`,
      name: String(columns.value[ci] ?? ''),
      autoSize: true,
      minSize: 120,
    });
  }
  gridColumns.value = colDefs;

  // 初始行数据
  const src = rows.value.map(r => {
    const rec = { c0: r[0], c1: r[1] ?? '' };
    for (const ci of fillable) rec[`c${ci}`] = '';
    return rec;
  });
  gridSource.value = src;
  await autoSizeFirstColumn();
}

async function loadExisting() {
  const q = await queryData({ project_key: projectKey, sheet_key: sheetKey, biz_date: bizDate.value });
  // 将已填报的值映射到 values
  if (Array.isArray(q.cells)) {
    for (const cell of q.cells) {
      const { row_label, col_index, value_type, value_num, value_text } = cell;
      const ri = rows.value.findIndex(r => r[0] === row_label);
      if (ri >= 0 && col_index >= 0) {
        values[toKey(ri, col_index)] = value_type === 'num' ? String(value_num ?? '') : String(value_text ?? '');
        // 同步到 gridSource
        if (gridSource.value[ri]) {
          gridSource.value[ri][`c${col_index}`] = values[toKey(ri, col_index)];
        }
      }
    }
  }
  await autoSizeFirstColumn();
}

async function reloadTemplate() {
  await loadTemplate();
  await loadExisting();
}

async function onSubmit() {
  const cells = [];
  const fillableCols = columns.value.map((_, i) => i).filter(i => i >= 2);
  for (let ri = 0; ri < rows.value.length; ri++) {
    const row = rows.value[ri];
    for (const ci of fillableCols) {
      const raw = gridSource.value?.[ri]?.[`c${ci}`];
      if (raw === undefined || raw === null || raw === '') continue;
      const asNum = Number(raw);
      const isNum = !Number.isNaN(asNum) && /^-?\d+(\.\d+)?$/.test(String(raw));
      cells.push({
        row_label: row[0],
        unit: row[1] ?? '',
        col_index: ci,
        value_type: isNum ? 'num' : 'text',
        value_num: isNum ? asNum : undefined,
        value_text: isNum ? undefined : String(raw),
      });
    }
  }
  const payload = {
    project_key: projectKey,
    sheet_key: sheetKey,
    sheet_name: sheetName.value || '',
    biz_date: bizDate.value,
    cells,
  };
  await submitData(payload);
  // 简单提示
  alert('提交成功');
}

onMounted(async () => {
  await nextTick();
  await ensureProjectsLoaded().catch(() => {});
  await loadTemplate();
  await loadExisting();
});

function handleAfterEdit(evt) {
  const detail = evt?.detail ?? evt;
  const changes = Array.isArray(detail?.changes) ? detail.changes : (detail ? [detail] : []);
  for (const change of changes) {
    const { rowIndex, prop, val } = change || {};
    if (rowIndex == null || !prop) continue;
    if (!gridSource.value[rowIndex]) continue;
    gridSource.value[rowIndex][prop] = val;
    const match = String(prop).match(/^c(\d+)$/);
    if (match) {
      const ci = Number(match[1]);
      values[toKey(rowIndex, ci)] = val;
    }
  }
}

function goDashboard() {
  router.push(`/projects/${encodeURIComponent(projectKey)}/sheets`);
}
</script>

<style scoped>
.topbar { gap: 12px; margin-bottom: 16px; }
.date { display: inline-flex; align-items: center; gap: 8px; margin-right: 8px; }
</style>
