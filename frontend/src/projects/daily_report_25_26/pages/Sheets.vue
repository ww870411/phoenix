<template>
  <div class="sheets-view">
    <AppHeader />
    <main class="sheets-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card elevated sheets-block">
        <header class="card-header">
          <div class="card-header__title">
            <h2>{{ pageDisplayName }}</h2>
            <p class="sheet-subtitle">项目：{{ projectName }}</p>
          </div>
          <div class="validation-toggle" role="group" aria-label="全局校验开关">
            <label class="validation-toggle__control">
              <input
                type="checkbox"
                class="validation-toggle__checkbox"
                :checked="validationMasterEnabled"
                :disabled="validationToggleDisabled"
                @change="onValidationMasterToggle"
              />
              <span>全局校验开关</span>
            </label>
            <span
              class="validation-toggle__status"
              :class="{ 'validation-toggle__status--off': !validationMasterEnabled }"
            >
              {{ validationMasterEnabled ? '已开启' : '已关闭' }}
            </span>
            <span v-if="validationMasterLoading" class="validation-toggle__hint">状态加载中…</span>
            <span v-else-if="validationMasterSaving" class="validation-toggle__hint">保存中…</span>
            <span
              v-if="validationMasterError"
              class="validation-toggle__hint validation-toggle__hint--error"
            >
              {{ validationMasterError }}
            </span>
          </div>
        </header>
        <div v-if="loading" class="sheet-state">表格列表加载中，请稍候…</div>
        <div v-else-if="errorMessage" class="sheet-state error">{{ errorMessage }}</div>
        <div v-else class="unit-card-grid">
          <button
            v-for="group in groupedSheets"
            :key="group.groupKey"
            type="button"
            class="card elevated unit-card"
            @click="openUnit(group)"
          >
            <div class="unit-card-header">
              <div class="unit-card-title">{{ group.groupName }}</div>
              <div
                class="status-indicator"
                :class="getUnitStatus(group).statusClass"
                :title="getUnitStatus(group).title"
              >
                <span class="status-text">{{ getUnitStatus(group).statusText }}</span>
              </div>
            </div>
            <div class="unit-card-body">
              <div class="unit-card-meta">
                <span class="unit-table-count">共 {{ group.items.length }} 张表格</span>
              </div>
              <div class="unit-tags-row">
                <span
                  v-for="sheet in group.items"
                  :key="sheet.sheet_key"
                  class="unit-sheet-pill"
                  :title="sheet.sheet_name"
                >
                  <span class="pill-number" v-if="parseSheetNumber(sheet.sheet_name)">{{ parseSheetNumber(sheet.sheet_name) }}</span>
                  <span class="pill-title">{{ cleanSheetBodyName(sheet.sheet_name, group.groupName) }}</span>
                </span>
              </div>
            </div>
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { listSheets, getValidationMasterSwitch, setValidationMasterSwitch, getSheetsSubmissionStatus } from '../services/api'
import { ensureProjectsLoaded, getProjectNameById } from '../composables/useProjects'
import { useAuthStore } from '../store/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const projectKey = computed(() => String(route.params.projectKey ?? ''))
const pageKey = computed(() => String(route.params.pageKey ?? ''))
const pageConfig = computed(() => {
  const raw = route.query.config
  return typeof raw === 'string' ? raw : ''
})
const pageDisplayName = computed(() => {
  const raw = route.query.pageName
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim()
  }
  return pageKey.value || '页面'
})

const rawSheets = ref([])
const sheets = ref([])
const submissionStatus = ref({}) // { sheet_key: { count: 10 } }
const groupedSheets = computed(() => {
  const groups = new Map()
  for (const s of sheets.value) {
    const name = (s.unit_name && String(s.unit_name).trim()) || '未分组'
    if (!groups.has(name)) groups.set(name, [])
    groups.get(name).push(s)
  }
  const result = []
  for (const [name, items] of groups.entries()) {
    result.push({ groupKey: name, groupName: name, items })
  }
  // 严格保持配置文件（后端返回）的单位出现顺序，不再排序
  return result
})
const loading = ref(false)
const errorMessage = ref('')
const validationMasterEnabled = ref(true)
const validationMasterLoading = ref(true)
const validationMasterSaving = ref(false)
const validationMasterError = ref('')

const projectName = computed(() => getProjectNameById(projectKey.value) ?? projectKey.value)
const canToggleValidation = computed(() => auth.canManageValidationFor(projectKey.value))
const validationToggleDisabled = computed(
  () => validationMasterLoading.value || validationMasterSaving.value || !canToggleValidation.value,
)

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey.value)}/pages` },
  { label: pageDisplayName.value, to: null },
])

function ensureValidRoute() {
  if (!projectKey.value || !pageKey.value) {
    router.replace('/projects')
    return false
  }
  if (!pageConfig.value) {
    errorMessage.value = '页面缺少模板配置文件参数，无法继续。'
    return false
  }
  return true
}

async function loadSheets() {
  if (!ensureValidRoute()) {
    return
  }
  loading.value = true
  errorMessage.value = ''
  submissionStatus.value = {}
  try {
    await ensureProjectsLoaded()
    const [sheetRes, statusRes] = await Promise.all([
      listSheets(projectKey.value, pageConfig.value),
      getSheetsSubmissionStatus(projectKey.value, pageConfig.value)
    ])
    
    const catalog = sheetRes?.content || sheetRes // 兼容旧结构
    const entries = catalog && typeof catalog === 'object' ? Object.entries(catalog) : []
    rawSheets.value = entries.map(([sheetKey, meta]) => ({
      sheet_key: sheetKey,
      sheet_name: meta?.sheet_name ?? sheetKey,
      unit_name: meta?.unit_name ?? '',
    }))
    
    if (statusRes && statusRes.ok && statusRes.status) {
      submissionStatus.value = statusRes.status
    }

    applySheetFilter()
    if (!rawSheets.value.length) {
      errorMessage.value = '该页面暂未配置任何表格。'
    }
  } catch (err) {
    console.error(err)
    errorMessage.value =
      '无法获取表格清单，请确认后端接口 /api/v1/projects/{project_key}/data_entry/sheets 已完成配置。'
  } finally {
    loading.value = false
  }
}

function getSheetStatus(sheetKey) {
  const st = submissionStatus.value[sheetKey]
  // 煤炭表特殊处理：如果找不到 sheetKey，尝试查找 __coal_inventory__
  if (!st && (sheetKey.toLowerCase().includes('coal') || sheetKey.toLowerCase().includes('inventory'))) {
    return submissionStatus.value['__coal_inventory__'] || null
  }
  return st || null
}

function openSheet(sheet) {
  const name = typeof pageDisplayName.value === 'string' ? pageDisplayName.value : ''
  const isApproval = name.includes('审批')
  const isDisplay = name.includes('展示') || (typeof pageConfig.value === 'string' && pageConfig.value.includes('数据结构_全口径展示表.json'))
  const base = `/projects/${encodeURIComponent(projectKey.value)}/pages/${encodeURIComponent(pageKey.value)}`
  let path
  if (isApproval) {
    path = `${base}/approval/${encodeURIComponent(sheet.sheet_key)}`
  } else if (isDisplay) {
    path = `${base}/display/${encodeURIComponent(sheet.sheet_key)}`
  } else {
    path = `${base}/sheets/${encodeURIComponent(sheet.sheet_key)}`
  }
  router.push({ path, query: { config: pageConfig.value, pageName: pageDisplayName.value } })
}

function openUnit(unit) {
  if (!unit || !unit.items || unit.items.length === 0) return
  openSheet(unit.items[0])
}

function getUnitStatus(unit) {
  if (!unit || !unit.items || unit.items.length === 0) {
    return { statusClass: '', statusText: '暂无表格', title: '暂无表格' }
  }
  const total = unit.items.length
  let completeCount = 0
  let partialCount = 0
  for (const s of unit.items) {
    const st = getSheetStatus(s.sheet_key)
    if (st?.count > 0 && st?.expected > 0 && st.count / st.expected >= 0.85) {
      completeCount++
    } else if (st?.count > 0) {
      partialCount++
    }
  }
  if (completeCount === total) {
    return {
      statusClass: 'status-indicator--complete',
      statusText: total > 1 ? `已填报 ${total}/${total}` : '已提交',
      title: '该单位所有表格均已提交'
    }
  }
  if (completeCount > 0 || partialCount > 0) {
    return {
      statusClass: 'status-indicator--partial',
      statusText: `已填报 ${completeCount}/${total}`,
      title: `该单位已填报 ${completeCount}/${total} 张表格`
    }
  }
  return {
    statusClass: '',
    statusText: total > 1 ? `共 ${total} 张表` : '待填报',
    title: '暂未提交数据'
  }
}

function parseSheetNumber(sheetName) {
  if (!sheetName) return ''
  const m = String(sheetName).match(/^(\d+)[\.、\s]*/)
  return m ? m[1] : ''
}

function cleanSheetBodyName(sheetName, unitName) {
  if (!sheetName) return ''
  let s = String(sheetName)
  // 去除序号部分
  s = s.replace(/^\d+[\.、\s]*/, '').trim()
  // 去除单位名重复
  if (unitName && s.includes(unitName)) {
    const trimmed = s.replace(unitName, '').trim()
    if (trimmed && trimmed !== '表' && trimmed !== '（表）' && trimmed !== '()') {
      s = trimmed
    }
  }
  // 去除外层括号
  s = s.replace(/^[（\(](.*?)[）\)]/, '$1').trim()
  if (!s.endsWith('表')) {
    s += '表'
  }
  return s || sheetName
}

onMounted(() => {
  loadSheets()
  loadValidationMasterSwitch()
})
function applySheetFilter() {
  sheets.value = auth.filterSheetsByRule(projectKey.value, pageKey.value, rawSheets.value)
  if (!sheets.value.length && rawSheets.value.length) {
    errorMessage.value = '当前账号无权访问该页面下的表格，请联系管理员调整权限。'
  }
}

async function loadValidationMasterSwitch() {
  if (!projectKey.value) {
    validationMasterLoading.value = false
    return
  }
  validationMasterLoading.value = true
  validationMasterError.value = ''
  try {
    const payload = await getValidationMasterSwitch(projectKey.value)
    validationMasterEnabled.value = Boolean(payload?.validation_enabled ?? true)
  } catch (err) {
    console.error(err)
    validationMasterError.value =
      err instanceof Error ? err.message : '无法查询全局校验开关状态。'
  } finally {
    validationMasterLoading.value = false
  }
}

async function updateValidationMasterSwitch(nextValue) {
  if (!canToggleValidation.value || !projectKey.value) return
  validationMasterSaving.value = true
  validationMasterError.value = ''
  const previous = validationMasterEnabled.value
  validationMasterEnabled.value = nextValue
  try {
    const payload = await setValidationMasterSwitch(projectKey.value, nextValue)
    validationMasterEnabled.value = Boolean(payload?.validation_enabled ?? nextValue)
  } catch (err) {
    console.error(err)
    validationMasterEnabled.value = previous
    validationMasterError.value =
      err instanceof Error ? err.message : '更新校验总开关失败，请稍后再试。'
  } finally {
    validationMasterSaving.value = false
  }
}

function onValidationMasterToggle(event) {
  if (!canToggleValidation.value) return
  const checked = Boolean(event?.target?.checked)
  updateValidationMasterSwitch(checked)
}

watch(
  () => auth.permissions,
  () => {
    applySheetFilter()
  },
  { deep: true },
)

watch([projectKey, pageKey, pageConfig], loadSheets)
watch(projectKey, () => {
  loadValidationMasterSwitch()
})
</script>

<style scoped>
.sheets-main {
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sheets-block {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.sheet-subtitle {
  margin-top: 8px;
  font-size: 14px;
  color: var(--neutral-500);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.card-header__title {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.validation-toggle {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-end;
  text-align: right;
  min-width: 220px;
  margin-top: 20px;
  margin-left: auto;
}

.validation-toggle__control {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--neutral-700);
}

.validation-toggle__checkbox {
  width: 18px;
  height: 18px;
}

.validation-toggle__status {
  font-size: 14px;
  color: var(--success-600, #0f8a5f);
  align-self: flex-end;
  text-align: right;
  width: 100%;
}

.validation-toggle__status--off {
  color: var(--warning-700, #c45d00);
}

.validation-toggle__hint {
  font-size: 12px;
  color: var(--neutral-500);
}

.validation-toggle__hint--error {
  color: var(--danger, #d93026);
}

.sheet-state {
  padding: 40px 0;
  text-align: center;
  color: var(--neutral-600);
}

.sheet-state.error {
  color: var(--danger);
}

.sheet-card {
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: transform 0.2s ease;
}

.sheet-card:hover {
  transform: translateY(-2px);
}

.sheet-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 12px; /* Pill shape */
  background-color: #f3f4f6; /* Gray-100 */
  color: #9ca3af; /* Gray-400 */
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
  margin-left: 8px;
  border: 1px solid #e5e7eb; /* Gray-200 */
  min-width: 20px; /* Ensure visibility if empty */
  height: 20px;
}

.status-indicator--partial {
  background-color: #fef9c3; /* Yellow-100 */
  color: #854d0e; /* Yellow-800 */
  border-color: #fef08a; /* Yellow-200 */
}

.status-indicator--complete {
  background-color: #10b981; /* Emerald-500 */
  color: white;
  border-color: #059669; /* Emerald-600 */
}

.status-text {
  line-height: 1;
}

.sheet-card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-700);
}

.sheet-card-desc {
  font-size: 14px;
  color: var(--neutral-500);
}

.unit-card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-top: 16px;
  width: 100%;
  box-sizing: border-box;
}

@media (max-width: 640px) {
  .unit-card-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.unit-card {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  text-align: left;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  padding: 20px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.unit-card:hover {
  transform: translateY(-3px);
  border-color: #3b82f6;
  box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.15), 0 8px 10px -6px rgba(59, 130, 246, 0.1);
}

.unit-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  min-width: 0;
}

.unit-card-title {
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.unit-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.unit-card-meta {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.unit-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  width: 100%;
  min-width: 0;
  min-height: 28px;
  align-items: center;
}

.unit-sheet-pill {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 6px;
  background-color: #f1f5f9;
  color: #334155;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.pill-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 4px;
  background-color: #e2e8f0;
  color: #1e293b;
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  flex-shrink: 0;
}

.pill-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.unit-card:hover .unit-sheet-pill {
  background-color: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}

.unit-card:hover .pill-number {
  background-color: #dbeafe;
  color: #1d4ed8;
}
</style>
