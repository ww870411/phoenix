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
        <div v-else>
          <div v-for="group in groupedSheets" :key="group.groupKey" class="sheet-group">
            <h3 class="group-title">{{ group.groupName }}</h3>
            <div class="card-grid">
              <button
                v-for="sheet in group.items"
                :key="sheet.sheet_key"
                type="button"
                class="card elevated sheet-card"
                @click="openSheet(sheet)"
              >
                <div class="sheet-card-title">{{ sheet.sheet_name }}</div>
                <div class="sheet-card-desc">填报单位：{{ sheet.unit_name || '未配置' }}</div>
              </button>
            </div>
          </div>
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
import { listSheets, getValidationMasterSwitch, setValidationMasterSwitch } from '../services/api'
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
const canToggleValidation = computed(() => auth.user?.group === 'Global_admin')
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
  try {
    await ensureProjectsLoaded()
    const response = await listSheets(projectKey.value, pageConfig.value)
    const catalog = response?.content || response // 兼容旧结构
    const entries = catalog && typeof catalog === 'object' ? Object.entries(catalog) : []
    rawSheets.value = entries.map(([sheetKey, meta]) => ({
      sheet_key: sheetKey,
      sheet_name: meta?.sheet_name ?? sheetKey,
      unit_name: meta?.unit_name ?? '',
    }))
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

onMounted(() => {
  loadSheets()
  loadValidationMasterSwitch()
})
function applySheetFilter() {
  sheets.value = auth.filterSheetsByRule(pageKey.value, rawSheets.value)
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

.sheet-card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-700);
}

.sheet-card-desc {
  font-size: 14px;
  color: var(--neutral-500);
}
</style>
