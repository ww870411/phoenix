<template>
  <div class="page-main">
    <AppHeader />
    <div class="page-content">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card elevated template-shell">
        <header class="template-designer-header card-header">
          <div class="card-header__title">
            <h2>模板设计器（新表）</h2>
            <p class="subtext">用于未来新报表的可视化设计：支持行列拖拽排序、单元格预览与 JSON 兼容编辑。</p>
          </div>
          <div class="header-actions">
            <button class="btn" @click="handleCreateDraft">新建草稿</button>
            <button class="btn btn-primary" :disabled="saving" @click="handleSave">
              {{ saving ? "保存中..." : "保存模板" }}
            </button>
            <button class="btn btn-success" :disabled="publishing || !form.template_key" @click="handlePublish">
              {{ publishing ? "发布中..." : "发布模板" }}
            </button>
          </div>
        </header>

        <section class="template-designer-main">
      <aside class="template-list-panel">
        <h2>模板列表</h2>
        <div v-if="loadingList" class="hint">加载中...</div>
        <div v-else-if="!templates.length" class="hint">暂无模板</div>
        <ul v-else class="template-list">
          <li v-for="item in templates" :key="item.template_key">
            <button
              class="template-item"
              :class="{ active: item.template_key === activeTemplateKey }"
              @click="loadTemplate(item.template_key)"
            >
              <span class="name">{{ item.template_name }}</span>
              <span class="meta">{{ item.table_type }} · v{{ item.version }} · {{ item.status }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <div class="template-editor-panel">
        <div class="form-grid">
          <label>
            <span>模板键</span>
            <input v-model.trim="form.template_key" placeholder="如：new_heat_summary_sheet" />
          </label>
          <label>
            <span>模板名称</span>
            <input v-model.trim="form.template_name" placeholder="如：新供热汇总表" />
          </label>
          <label>
            <span>表类型</span>
            <select v-model="form.table_type">
              <option value="tall">长表（tall）</option>
              <option value="matrix">交叉表（matrix）</option>
            </select>
          </label>
          <label class="form-grid-wide">
            <span>模板说明</span>
            <input v-model="form.description" placeholder="填写模板用途、适用范围、注意事项" />
          </label>
        </div>

        <section class="editor-block">
          <div class="block-header">
            <h3>固定字段配置</h3>
          </div>
          <div class="fixed-fields-grid">
            <label class="inline-check">
              <input v-model="fixedFields.row_label" type="checkbox" />
              <span>启用行标题字段（row_label）</span>
            </label>
            <label>
              <span>行标题默认值</span>
              <input v-model="fixedFieldDefaults.row_label" placeholder="如：未命名项目" />
            </label>
            <label class="inline-check">
              <input v-model="fixedFields.unit" type="checkbox" />
              <span>启用计量单位字段（unit）</span>
            </label>
            <label>
              <span>计量单位默认值</span>
              <input v-model="fixedFieldDefaults.unit" placeholder="如：万kWh" />
            </label>
          </div>
          <div class="hint">说明：关闭固定字段后，该字段不再强制出现在行编辑和预览中；如需该信息，可改为在“列定义”中自行配置。</div>
        </section>

        <section class="editor-block">
          <div class="block-header">
            <h3>列定义（可拖拽排序）</h3>
            <button class="btn btn-sm" @click="addColumn">新增列</button>
          </div>
          <table class="editor-table">
            <thead>
              <tr>
                <th class="drag-col">拖拽</th>
                <th>列键名</th>
                <th>列标题</th>
                <th>值类型</th>
                <th>必填</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(column, idx) in form.columns"
                :key="`col-${idx}`"
                draggable="true"
                :class="{ dragging: dragColumnIndex === idx }"
                @dragstart="onColumnDragStart(idx)"
                @dragover.prevent
                @drop="onColumnDrop(idx)"
                @dragend="onColumnDragEnd"
              >
                <td class="drag-col"><span class="drag-handle">⋮⋮</span></td>
                <td><input v-model.trim="column.key" placeholder="column_key" /></td>
                <td><input v-model.trim="column.label" placeholder="列标题" /></td>
                <td>
                  <select v-model="column.value_type">
                    <option value="text">text</option>
                    <option value="num">num</option>
                  </select>
                </td>
                <td><input v-model="column.required" type="checkbox" /></td>
                <td><button class="btn btn-danger btn-sm" @click="removeColumn(idx)">删除</button></td>
              </tr>
              <tr v-if="!form.columns.length">
                <td colspan="6" class="hint">请先定义列结构</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="editor-block">
          <div class="block-header">
            <h3>行定义（可拖拽排序）</h3>
            <button class="btn btn-sm" @click="addRow">新增行</button>
          </div>
          <table class="editor-table">
            <thead>
              <tr>
                <th class="drag-col">拖拽</th>
                <th>行键名</th>
                <th v-if="fixedFields.row_label">行标题</th>
                <th v-if="fixedFields.unit">计量单位</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in form.rows"
                :key="`row-${idx}`"
                draggable="true"
                :class="{ dragging: dragRowIndex === idx }"
                @dragstart="onRowDragStart(idx)"
                @dragover.prevent
                @drop="onRowDrop(idx)"
                @dragend="onRowDragEnd"
              >
                <td class="drag-col"><span class="drag-handle">⋮⋮</span></td>
                <td><input v-model.trim="row.row_key" placeholder="row_key" /></td>
                <td v-if="fixedFields.row_label"><input v-model.trim="row.row_label" placeholder="如：发电量" /></td>
                <td v-if="fixedFields.unit"><input v-model.trim="row.unit" placeholder="如：万kWh" /></td>
                <td><button class="btn btn-danger btn-sm" @click="removeRow(idx)">删除</button></td>
              </tr>
              <tr v-if="!form.rows.length">
                <td :colspan="rowTableColspan" class="hint">请先定义行结构</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="editor-block">
          <div class="block-header">
            <h3>预览网格（编辑单元格初始值）</h3>
            <button class="btn btn-sm" @click="clearAllCells">清空单元格</button>
          </div>
          <div v-if="!form.columns.length || !form.rows.length" class="hint">请先至少定义 1 列和 1 行，再进行网格预览。</div>
          <div v-else class="preview-wrap">
            <table class="preview-table">
              <thead>
                <tr>
                  <th v-if="fixedFields.row_label">项目</th>
                  <th v-if="fixedFields.unit">计量单位</th>
                  <th v-for="(column, cIdx) in form.columns" :key="`preview-col-${cIdx}`">
                    {{ column.label || column.key || `列${cIdx + 1}` }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rIdx) in form.rows" :key="`preview-row-${rIdx}`">
                  <td v-if="fixedFields.row_label">{{ row.row_label || row.row_key || `行${rIdx + 1}` }}</td>
                  <td v-if="fixedFields.unit">{{ row.unit || "-" }}</td>
                  <td v-for="(column, cIdx) in form.columns" :key="`preview-cell-${rIdx}-${cIdx}`">
                    <input
                      v-model="row.cells[getColumnCellKey(column, cIdx)]"
                      :placeholder="column.value_type === 'num' ? '数值' : '文本'"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="editor-block">
          <div class="block-header">
            <h3>行定义 JSON（兼容模式）</h3>
            <button class="btn btn-sm" @click="applyRowsJson">应用 JSON 到可视编辑</button>
          </div>
          <textarea
            v-model="rowsJson"
            class="rows-json"
            placeholder='示例：[{"row_key":"row_1","row_label":"发电量","unit":"万kWh","cells":{"today":"12.3"}}]'
          />
          <div class="hint">你可直接编辑 JSON，点击“应用 JSON 到可视编辑”后会覆盖当前行定义。</div>
        </section>

        <div v-if="error" class="message error">{{ error }}</div>
        <div v-if="success" class="message success">{{ success }}</div>
      </div>
      </section>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
import { useRoute } from "vue-router"
import AppHeader from "../components/AppHeader.vue"
import Breadcrumbs from "../components/Breadcrumbs.vue"
import {
  createTemplateDesignerTemplate,
  getTemplateDesignerTemplate,
  listTemplateDesignerTemplates,
  publishTemplateDesignerTemplate,
  updateTemplateDesignerTemplate,
} from "../services/api"

const route = useRoute()
const projectKey = String(route.params.projectKey || "daily_report_25_26")
const projectName = computed(() => {
  if (projectKey === "daily_report_25_26") return "2025-2026供暖期生产日报"
  return String(projectKey || "项目")
})
const pageDisplayName = computed(() => String(route.query.pageName || "模板设计器（新表）"))
const breadcrumbItems = computed(() => [
  { label: "项目选择", to: "/projects" },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: pageDisplayName.value, to: null },
])

const loadingList = ref(false)
const saving = ref(false)
const publishing = ref(false)
const templates = ref([])
const activeTemplateKey = ref("")
const error = ref("")
const success = ref("")
const dragColumnIndex = ref(-1)
const dragRowIndex = ref(-1)

const form = ref({
  template_key: "",
  template_name: "",
  table_type: "tall",
  description: "",
  columns: [],
  rows: [],
  meta: {},
})

const rowsJson = ref("[]")
const rowTableColspan = computed(() => {
  let count = 2
  if (fixedFields.value.row_label) count += 1
  if (fixedFields.value.unit) count += 1
  count += 1
  return count
})

function ensureMetaShape(meta = {}) {
  const fixedFields = meta?.fixed_fields && typeof meta.fixed_fields === "object" ? meta.fixed_fields : {}
  const defaultValues = meta?.default_values && typeof meta.default_values === "object" ? meta.default_values : {}
  return {
    ...meta,
    fixed_fields: {
      row_label: fixedFields.row_label !== false,
      unit: Boolean(fixedFields.unit),
    },
    default_values: {
      row_label: String(defaultValues.row_label || ""),
      unit: String(defaultValues.unit || ""),
    },
  }
}

const fixedFields = computed({
  get() {
    form.value.meta = ensureMetaShape(form.value.meta)
    return form.value.meta.fixed_fields
  },
  set(next) {
    const current = ensureMetaShape(form.value.meta)
    current.fixed_fields = {
      row_label: next?.row_label !== false,
      unit: Boolean(next?.unit),
    }
    form.value.meta = current
  },
})

const fixedFieldDefaults = computed({
  get() {
    form.value.meta = ensureMetaShape(form.value.meta)
    return form.value.meta.default_values
  },
  set(next) {
    const current = ensureMetaShape(form.value.meta)
    current.default_values = {
      row_label: String(next?.row_label || ""),
      unit: String(next?.unit || ""),
    }
    form.value.meta = current
  },
})

function resetMessages() {
  error.value = ""
  success.value = ""
}

function createEmptyRow() {
  const meta = ensureMetaShape(form.value.meta)
  return {
    row_key: "",
    row_label: meta.default_values.row_label || "",
    unit: meta.fixed_fields.unit ? meta.default_values.unit || "" : "",
    cells: {},
  }
}

function normalizeColumn(column = {}) {
  return {
    key: String(column.key || "").trim(),
    label: String(column.label || ""),
    value_type: column.value_type === "num" ? "num" : "text",
    required: Boolean(column.required),
  }
}

function normalizeRow(row = {}) {
  const meta = ensureMetaShape(form.value.meta)
  const normalized = {
    row_key: String(row.row_key || "").trim(),
    row_label: meta.fixed_fields.row_label ? String(row.row_label || meta.default_values.row_label || "") : "",
    unit: meta.fixed_fields.unit ? String(row.unit || meta.default_values.unit || "") : "",
    cells: {},
  }
  const rawCells = row.cells && typeof row.cells === "object" ? row.cells : {}
  for (const [key, value] of Object.entries(rawCells)) {
    normalized.cells[String(key)] = value == null ? "" : String(value)
  }
  return normalized
}

function sanitizeRowsByColumns(rows) {
  const validKeys = new Set(
    (form.value.columns || [])
      .map((column, idx) => getColumnCellKey(column, idx))
      .filter(Boolean),
  )
  return (rows || []).map((row) => {
    const next = normalizeRow(row)
    const filtered = {}
    for (const [key, value] of Object.entries(next.cells || {})) {
      if (validKeys.has(key)) filtered[key] = value
    }
    next.cells = filtered
    return next
  })
}

function syncRowsJsonFromForm() {
  rowsJson.value = JSON.stringify(form.value.rows || [], null, 2)
}

function resetForm() {
  form.value = {
    template_key: "",
    template_name: "",
    table_type: "tall",
    description: "",
    columns: [],
    rows: [],
    meta: ensureMetaShape({}),
  }
  rowsJson.value = "[]"
  activeTemplateKey.value = ""
}

function addColumn() {
  form.value.columns.push(
    normalizeColumn({
      key: "",
      label: "",
      value_type: "text",
      required: false,
    }),
  )
}

function removeColumn(index) {
  const removed = form.value.columns[index]
  form.value.columns.splice(index, 1)
  const removedKey = String(removed?.key || "").trim()
  if (!removedKey) return
  form.value.rows = (form.value.rows || []).map((row) => {
    const next = normalizeRow(row)
    if (next.cells && Object.prototype.hasOwnProperty.call(next.cells, removedKey)) {
      delete next.cells[removedKey]
    }
    return next
  })
}

function addRow() {
  form.value.rows.push(createEmptyRow())
}

function removeRow(index) {
  form.value.rows.splice(index, 1)
}

function onColumnDragStart(index) {
  dragColumnIndex.value = index
}

function onColumnDrop(targetIndex) {
  const from = dragColumnIndex.value
  if (from < 0 || from === targetIndex) return
  const cols = [...form.value.columns]
  const [moved] = cols.splice(from, 1)
  cols.splice(targetIndex, 0, moved)
  form.value.columns = cols
  dragColumnIndex.value = -1
}

function onColumnDragEnd() {
  dragColumnIndex.value = -1
}

function onRowDragStart(index) {
  dragRowIndex.value = index
}

function onRowDrop(targetIndex) {
  const from = dragRowIndex.value
  if (from < 0 || from === targetIndex) return
  const rows = [...form.value.rows]
  const [moved] = rows.splice(from, 1)
  rows.splice(targetIndex, 0, moved)
  form.value.rows = rows
  dragRowIndex.value = -1
}

function onRowDragEnd() {
  dragRowIndex.value = -1
}

function getColumnCellKey(column, index) {
  const key = String(column?.key || "").trim()
  if (key) return key
  return `column_${index + 1}`
}

function clearAllCells() {
  form.value.rows = (form.value.rows || []).map((row) => ({
    ...normalizeRow(row),
    cells: {},
  }))
}

function parseRowsJson() {
  let parsed = []
  try {
    parsed = JSON.parse(rowsJson.value || "[]")
  } catch (err) {
    throw new Error(`行定义 JSON 不合法：${err?.message || "解析失败"}`)
  }
  if (!Array.isArray(parsed)) {
    throw new Error("行定义 JSON 必须是数组")
  }
  return sanitizeRowsByColumns(parsed)
}

function applyRowsJson() {
  resetMessages()
  try {
    form.value.rows = parseRowsJson()
    syncRowsJsonFromForm()
    success.value = "已应用 JSON 到可视编辑区域"
  } catch (err) {
    error.value = err?.message || "应用 JSON 失败"
  }
}

async function refreshTemplateList() {
  loadingList.value = true
  try {
    const payload = await listTemplateDesignerTemplates(projectKey)
    templates.value = Array.isArray(payload?.templates) ? payload.templates : []
  } catch (err) {
    error.value = err?.message || "加载模板列表失败"
  } finally {
    loadingList.value = false
  }
}

async function loadTemplate(templateKey) {
  resetMessages()
  try {
    const payload = await getTemplateDesignerTemplate(projectKey, templateKey)
    form.value = {
      template_key: payload.template_key || "",
      template_name: payload.template_name || "",
      table_type: payload.table_type || "tall",
      description: payload.description || "",
      columns: Array.isArray(payload.columns) ? payload.columns.map(normalizeColumn) : [],
      rows: Array.isArray(payload.rows) ? payload.rows.map(normalizeRow) : [],
      meta: ensureMetaShape(payload.meta && typeof payload.meta === "object" ? payload.meta : {}),
    }
    form.value.rows = sanitizeRowsByColumns(form.value.rows)
    syncRowsJsonFromForm()
    activeTemplateKey.value = form.value.template_key
  } catch (err) {
    error.value = err?.message || "加载模板详情失败"
  }
}

function buildPayload() {
  const meta = ensureMetaShape(form.value.meta)
  const columns = (form.value.columns || []).map(normalizeColumn)
  if (!columns.length) throw new Error("至少需要 1 个列定义")
  const validColumnKeys = new Set(columns.map((column, idx) => getColumnCellKey(column, idx)))
  const rows = parseRowsJson().map((row) => {
    const next = normalizeRow(row)
    if (!meta.fixed_fields.row_label) next.row_label = ""
    if (!meta.fixed_fields.unit) next.unit = ""
    const filtered = {}
    for (const [key, value] of Object.entries(next.cells || {})) {
      if (!validColumnKeys.has(key)) continue
      filtered[key] = value
    }
    next.cells = filtered
    return next
  })
  const payload = {
    template_key: String(form.value.template_key || "").trim(),
    template_name: String(form.value.template_name || "").trim(),
    table_type: form.value.table_type === "matrix" ? "matrix" : "tall",
    description: String(form.value.description || ""),
    columns,
    rows,
    meta,
  }
  if (!payload.template_key) throw new Error("模板键不能为空")
  if (!payload.template_name) throw new Error("模板名称不能为空")
  return payload
}

async function handleSave() {
  resetMessages()
  saving.value = true
  try {
    const payload = buildPayload()
    const isUpdate = templates.value.some((item) => item.template_key === payload.template_key)
    const result = isUpdate
      ? await updateTemplateDesignerTemplate(projectKey, payload.template_key, payload)
      : await createTemplateDesignerTemplate(projectKey, payload)
    success.value = isUpdate ? "模板更新成功" : "模板创建成功"
    activeTemplateKey.value = result.template_key
    form.value.rows = payload.rows
    syncRowsJsonFromForm()
    await refreshTemplateList()
  } catch (err) {
    error.value = err?.message || "保存模板失败"
  } finally {
    saving.value = false
  }
}

async function handlePublish() {
  resetMessages()
  publishing.value = true
  try {
    const payload = buildPayload()
    await updateTemplateDesignerTemplate(projectKey, payload.template_key, payload)
    await publishTemplateDesignerTemplate(projectKey, payload.template_key)
    success.value = "模板发布成功"
    activeTemplateKey.value = payload.template_key
    form.value.rows = payload.rows
    syncRowsJsonFromForm()
    await refreshTemplateList()
  } catch (err) {
    error.value = err?.message || "发布模板失败"
  } finally {
    publishing.value = false
  }
}

function handleCreateDraft() {
  resetMessages()
  resetForm()
}

watch(
  () => form.value.rows,
  () => {
    syncRowsJsonFromForm()
  },
  { deep: true },
)

watch(
  () => [fixedFields.value.row_label, fixedFields.value.unit, fixedFieldDefaults.value.row_label, fixedFieldDefaults.value.unit],
  () => {
    form.value.rows = (form.value.rows || []).map((row) => normalizeRow(row))
    syncRowsJsonFromForm()
  },
  { deep: true },
)

onMounted(async () => {
  await refreshTemplateList()
})
</script>

<style scoped>
.page-main {
  min-height: 100vh;
}

.page-content {
  max-width: 1440px;
  margin: 0 auto;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.template-shell {
  padding: 12px;
}

.template-designer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.template-designer-header h2 {
  margin: 0;
  font-size: 20px;
}

.subtext {
  margin: 6px 0 0;
  color: #4b5563;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.template-designer-main {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
}

.template-list-panel,
.template-editor-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
}

.template-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.template-item {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  text-align: left;
  padding: 8px;
  cursor: pointer;
}

.template-item.active {
  border-color: #2563eb;
  background: #eff6ff;
}

.template-item .name {
  display: block;
  font-weight: 600;
}

.template-item .meta {
  display: block;
  font-size: 12px;
  color: #6b7280;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.form-grid-wide {
  grid-column: 1 / -1;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

input,
select,
textarea {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px;
  font-size: 14px;
}

.editor-block {
  margin-top: 16px;
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.fixed-fields-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
  margin-bottom: 8px;
}

.inline-check {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.editor-table,
.preview-table {
  width: 100%;
  border-collapse: collapse;
}

.editor-table th,
.editor-table td,
.preview-table th,
.preview-table td {
  border: 1px solid #e5e7eb;
  padding: 6px;
}

.drag-col {
  width: 56px;
  text-align: center;
}

.drag-handle {
  display: inline-block;
  font-size: 14px;
  color: #6b7280;
  cursor: grab;
  user-select: none;
}

tr.dragging {
  opacity: 0.55;
  background: #f8fafc;
}

.preview-wrap {
  overflow: auto;
}

.preview-table {
  min-width: 720px;
}

.rows-json {
  width: 100%;
  min-height: 180px;
  font-family: Consolas, "Courier New", monospace;
}

.btn {
  border: 1px solid #d1d5db;
  background: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.btn-success {
  background: #059669;
  color: #fff;
  border-color: #059669;
}

.btn-danger {
  background: #dc2626;
  color: #fff;
  border-color: #dc2626;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.hint {
  color: #6b7280;
  font-size: 12px;
}

.message {
  margin-top: 12px;
  padding: 8px;
  border-radius: 8px;
  font-size: 13px;
}

.message.success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #10b981;
}

.message.error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #ef4444;
}

@media (max-width: 1024px) {
  .template-designer-main {
    grid-template-columns: 1fr;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
  .fixed-fields-grid {
    grid-template-columns: 1fr;
  }
}
</style>
