<template>
  <div class="admin-console-view">
    <AppHeader />
    <main class="admin-console-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <section class="card elevated">
        <header class="card-header">
          <h2>后台文件编辑</h2>
          <p class="subtext">目录：`backend_data`</p>
        </header>
        <div class="file-editor-grid">
          <div class="file-panel">
            <h3>子目录</h3>
            <button
              v-for="dir in directories"
              :key="dir"
              class="list-btn"
              :class="{ active: dir === selectedDirectory }"
              type="button"
              @click="selectDirectory(dir)"
            >
              {{ dir }}
            </button>
          </div>

          <div class="file-panel">
            <h3>文件列表</h3>
            <div v-if="fileListLoading" class="panel-state">文件加载中…</div>
            <button
              v-for="file in files"
              :key="file.path"
              class="list-btn"
              :class="{ active: file.path === selectedFilePath }"
              type="button"
              @click="selectFile(file.path)"
            >
              {{ file.path }}
            </button>
          </div>

          <div class="file-panel editor-panel">
            <div class="editor-head">
              <h3>文件内容</h3>
              <button
                class="btn primary"
                type="button"
                :disabled="!selectedFilePath || fileSaving"
                @click="saveCurrentFile"
              >
                {{ fileSaving ? '保存中…' : '提交保存' }}
              </button>
            </div>
            <div v-if="fileContentLoading" class="panel-state">文件读取中…</div>
            <textarea
              v-else
              v-model="fileContent"
              class="editor"
              placeholder="请选择文件后编辑内容"
            />
            <p v-if="fileMessage" class="subtext">{{ fileMessage }}</p>
          </div>
        </div>
      </section>

      <section class="card elevated">
        <header class="card-header">
          <h2>项目后台设定</h2>
        </header>
        <div class="project-switch">
          <button
            v-for="item in projects"
            :key="item.project_key"
            class="list-btn"
            :class="{ active: item.project_key === selectedProjectKey }"
            type="button"
            @click="selectProject(item.project_key)"
          >
            {{ item.project_name }}（{{ item.project_key }}）
          </button>
        </div>

        <div v-if="selectedProjectKey !== TARGET_PROJECT_KEY" class="panel-state">
          当前项目的后台设定暂未接入。请选择 {{ TARGET_PROJECT_KEY }} 查看现有配置模块。
        </div>

        <template v-else>
          <section class="inner-card">
            <header class="section-header">
              <h3>设定概览</h3>
            </header>
            <div v-if="loading" class="panel-state">加载中…</div>
            <div v-else-if="errorMessage" class="panel-state error">{{ errorMessage }}</div>
            <div v-else class="overview-grid">
              <div class="overview-item">
                <span class="label">校验开关管理</span>
                <strong>{{ actionLabel(overview?.actions?.can_manage_validation) }}</strong>
              </div>
              <div class="overview-item">
                <span class="label">AI 设置管理</span>
                <strong>{{ actionLabel(overview?.actions?.can_manage_ai_settings) }}</strong>
              </div>
              <div class="overview-item">
                <span class="label">缓存发布管理</span>
                <strong>{{ actionLabel(overview?.actions?.can_publish_cache) }}</strong>
              </div>
            </div>
          </section>

          <section class="inner-card">
            <header class="section-header">
              <h3>数据校验总开关</h3>
              <button
                class="btn primary"
                type="button"
                :disabled="!canManageValidation || validationPending"
                @click="toggleValidationMaster"
              >
                {{ validationPending ? '保存中…' : '切换开关' }}
              </button>
            </header>
            <p class="subtext">当前状态：{{ validationMasterEnabled ? '已开启' : '已关闭' }}</p>
          </section>

          <section class="inner-card">
            <header class="section-header">
              <h3>AI 设置</h3>
              <button
                class="btn primary"
                type="button"
                :disabled="!canManageAiSettings || aiPending"
                @click="saveAiConfig"
              >
                {{ aiPending ? '保存中…' : '保存设置' }}
              </button>
            </header>
            <div class="form-grid">
              <label>
                <span>模型</span>
                <input v-model="aiForm.model" :disabled="!canManageAiSettings" type="text" />
              </label>
              <label>
                <span>报告模式</span>
                <select v-model="aiForm.reportMode" :disabled="!canManageAiSettings">
                  <option value="full">full</option>
                  <option value="summary">summary</option>
                </select>
              </label>
              <label class="span-2">
                <span>API Key（每行一个）</span>
                <textarea v-model="aiForm.apiKeysText" :disabled="!canManageAiSettings" rows="4" />
              </label>
              <label class="span-2">
                <span>提示词补充</span>
                <textarea v-model="aiForm.instruction" :disabled="!canManageAiSettings" rows="5" />
              </label>
              <label class="switch-row">
                <input v-model="aiForm.enableValidation" :disabled="!canManageAiSettings" type="checkbox" />
                <span>启用报告校验</span>
              </label>
              <label class="switch-row">
                <input v-model="aiForm.allowNonAdminReport" :disabled="!canManageAiSettings" type="checkbox" />
                <span>允许非管理员使用 AI 报告</span>
              </label>
            </div>
          </section>

          <section class="inner-card">
            <header class="section-header">
              <h3>看板缓存任务</h3>
            </header>
            <div class="cache-actions">
              <label>
                <span>发布天数</span>
                <select v-model.number="publishDays" :disabled="!canManageCache || cachePending">
                  <option :value="1">1</option>
                  <option :value="3">3</option>
                  <option :value="7">7</option>
                </select>
              </label>
              <label>
                <span>刷新日期</span>
                <input v-model="refreshDate" :disabled="!canManageCache || cachePending" type="date" />
              </label>
              <button class="btn primary" type="button" :disabled="!canManageCache || cachePending" @click="publishCache">发布缓存</button>
              <button class="btn ghost" type="button" :disabled="!canManageCache || cachePending" @click="refreshCache">刷新单日</button>
              <button class="btn ghost" type="button" :disabled="!canManageCache || cachePending" @click="cancelPublish">停止任务</button>
              <button class="btn danger" type="button" :disabled="!canManageCache || cachePending" @click="disableCache">禁用缓存</button>
            </div>
            <p class="subtext">任务状态：{{ cacheJobStatus }}</p>
          </section>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { useAuthStore } from '../store/auth'
import {
  cancelAdminCachePublishJob,
  disableAdminCache,
  getAdminAiSettings,
  getAdminOverview,
  getAdminValidationMasterSwitch,
  listAdminFileDirectories,
  listAdminFiles,
  listAdminProjects,
  publishAdminDashboardCache,
  readAdminFile,
  refreshAdminCache,
  saveAdminFile,
  setAdminValidationMasterSwitch,
  updateAdminAiSettings,
} from '../services/api'

const TARGET_PROJECT_KEY = 'daily_report_25_26'
const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const errorMessage = ref('')
const overview = ref(null)
const validationMasterEnabled = ref(true)
const validationPending = ref(false)
const aiPending = ref(false)
const cachePending = ref(false)
const publishDays = ref(1)
const refreshDate = ref('')

const directories = ref([])
const selectedDirectory = ref('')
const files = ref([])
const selectedFilePath = ref('')
const fileContent = ref('')
const fileListLoading = ref(false)
const fileContentLoading = ref(false)
const fileSaving = ref(false)
const fileMessage = ref('')

const projects = ref([])
const selectedProjectKey = ref(TARGET_PROJECT_KEY)

const aiForm = reactive({
  apiKeysText: '',
  model: '',
  instruction: '',
  reportMode: 'full',
  enableValidation: true,
  allowNonAdminReport: false,
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '管理后台', to: null },
])

const canManageValidation = computed(() => auth.canManageValidationFor(TARGET_PROJECT_KEY))
const canManageAiSettings = computed(() => auth.canManageAiSettingsFor(TARGET_PROJECT_KEY))
const canManageCache = computed(() => auth.canPublishFor(TARGET_PROJECT_KEY))

const cacheJobStatus = computed(() => {
  const status = overview.value?.cache_publish_job?.status
  if (!status) return '暂无任务'
  const total = Number(overview.value?.cache_publish_job?.total || 0)
  const processed = Number(overview.value?.cache_publish_job?.processed || 0)
  return `${status}（${processed}/${total}）`
})

function actionLabel(flag) {
  return flag ? '已授权' : '未授权'
}

async function loadProjectSettings() {
  if (selectedProjectKey.value !== TARGET_PROJECT_KEY) return
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await getAdminOverview(TARGET_PROJECT_KEY)
    overview.value = payload
    validationMasterEnabled.value = Boolean(payload?.validation?.master_enabled)
  } catch (err) {
    console.error(err)
    errorMessage.value = err instanceof Error ? err.message : '加载管理后台失败'
  } finally {
    loading.value = false
  }
}

async function loadAiConfig() {
  if (!canManageAiSettings.value || selectedProjectKey.value !== TARGET_PROJECT_KEY) return
  try {
    const payload = await getAdminAiSettings()
    aiForm.apiKeysText = Array.isArray(payload?.api_keys) ? payload.api_keys.join('\n') : ''
    aiForm.model = String(payload?.model || '')
    aiForm.instruction = String(payload?.instruction || '')
    aiForm.reportMode = String(payload?.report_mode || 'full')
    aiForm.enableValidation = Boolean(payload?.enable_validation ?? true)
    aiForm.allowNonAdminReport = Boolean(payload?.allow_non_admin_report ?? false)
  } catch (err) {
    console.error(err)
  }
}

async function selectProject(projectKey) {
  selectedProjectKey.value = String(projectKey || '')
  if (selectedProjectKey.value === TARGET_PROJECT_KEY) {
    await loadProjectSettings()
    if (canManageValidation.value) {
      const payload = await getAdminValidationMasterSwitch()
      validationMasterEnabled.value = Boolean(payload?.validation_enabled)
    }
    await loadAiConfig()
  }
}

async function loadProjects() {
  try {
    const payload = await listAdminProjects()
    projects.value = Array.isArray(payload?.projects) ? payload.projects : []
    const hasTarget = projects.value.some((item) => item.project_key === TARGET_PROJECT_KEY)
    if (!hasTarget) {
      projects.value.unshift({
        project_key: TARGET_PROJECT_KEY,
        project_name: '2025-2026供暖期生产日报',
      })
    }
  } catch (err) {
    console.error(err)
    projects.value = [{ project_key: TARGET_PROJECT_KEY, project_name: '2025-2026供暖期生产日报' }]
  }
}

async function loadDirectories() {
  try {
    const payload = await listAdminFileDirectories()
    directories.value = Array.isArray(payload?.directories) ? payload.directories : []
    if (directories.value.length) {
      await selectDirectory(directories.value[0])
    }
  } catch (err) {
    console.error(err)
    fileMessage.value = err instanceof Error ? err.message : '目录读取失败'
  }
}

async function selectDirectory(dir) {
  selectedDirectory.value = String(dir || '')
  selectedFilePath.value = ''
  fileContent.value = ''
  fileMessage.value = ''
  fileListLoading.value = true
  try {
    const payload = await listAdminFiles(selectedDirectory.value)
    files.value = Array.isArray(payload?.files) ? payload.files : []
  } catch (err) {
    console.error(err)
    files.value = []
    fileMessage.value = err instanceof Error ? err.message : '文件列表读取失败'
  } finally {
    fileListLoading.value = false
  }
}

async function selectFile(path) {
  selectedFilePath.value = String(path || '')
  fileContentLoading.value = true
  fileMessage.value = ''
  try {
    const payload = await readAdminFile(selectedFilePath.value)
    fileContent.value = String(payload?.content || '')
  } catch (err) {
    console.error(err)
    fileMessage.value = err instanceof Error ? err.message : '文件读取失败'
  } finally {
    fileContentLoading.value = false
  }
}

async function saveCurrentFile() {
  if (!selectedFilePath.value) return
  fileSaving.value = true
  fileMessage.value = ''
  try {
    await saveAdminFile(selectedFilePath.value, fileContent.value)
    fileMessage.value = '保存成功'
  } catch (err) {
    console.error(err)
    fileMessage.value = err instanceof Error ? err.message : '保存失败'
  } finally {
    fileSaving.value = false
  }
}

async function toggleValidationMaster() {
  if (!canManageValidation.value) return
  validationPending.value = true
  try {
    const next = !validationMasterEnabled.value
    await setAdminValidationMasterSwitch(next)
    validationMasterEnabled.value = next
    await loadProjectSettings()
  } finally {
    validationPending.value = false
  }
}

async function saveAiConfig() {
  if (!canManageAiSettings.value) return
  aiPending.value = true
  try {
    const apiKeys = aiForm.apiKeysText
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean)
    await updateAdminAiSettings({
      api_keys: apiKeys,
      model: aiForm.model.trim(),
      instruction: aiForm.instruction,
      report_mode: aiForm.reportMode,
      enable_validation: aiForm.enableValidation,
      allow_non_admin_report: aiForm.allowNonAdminReport,
    })
    await loadProjectSettings()
  } finally {
    aiPending.value = false
  }
}

async function publishCache() {
  if (!canManageCache.value) return
  cachePending.value = true
  try {
    await publishAdminDashboardCache({ days: publishDays.value })
    await loadProjectSettings()
  } finally {
    cachePending.value = false
  }
}

async function refreshCache() {
  if (!canManageCache.value) return
  cachePending.value = true
  try {
    await refreshAdminCache({ showDate: refreshDate.value })
    await loadProjectSettings()
  } finally {
    cachePending.value = false
  }
}

async function cancelPublish() {
  if (!canManageCache.value) return
  cachePending.value = true
  try {
    await cancelAdminCachePublishJob()
    await loadProjectSettings()
  } finally {
    cachePending.value = false
  }
}

async function disableCache() {
  if (!canManageCache.value) return
  cachePending.value = true
  try {
    await disableAdminCache()
    await loadProjectSettings()
  } finally {
    cachePending.value = false
  }
}

onMounted(async () => {
  if (!auth.canAccessAdminConsole) {
    router.replace('/projects')
    return
  }
  await loadProjects()
  await loadDirectories()
  await selectProject(TARGET_PROJECT_KEY)
})
</script>

<style scoped>
.admin-console-main {
  padding: 24px;
  max-width: 1240px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.subtext {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--neutral-500);
}

.file-editor-grid {
  display: grid;
  grid-template-columns: 220px 360px minmax(0, 1fr);
  gap: 12px;
}

.file-panel {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  display: grid;
  gap: 8px;
  align-content: start;
  max-height: 520px;
  overflow: auto;
}

.editor-panel {
  overflow: visible;
}

.editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.editor {
  width: 100%;
  min-height: 420px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px;
  font-size: 13px;
  line-height: 1.5;
  font-family: Consolas, 'Courier New', monospace;
}

.project-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.inner-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  margin-top: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.overview-item {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 12px;
  display: grid;
  gap: 8px;
}

.overview-item .label {
  font-size: 12px;
  color: var(--neutral-500);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-grid label {
  display: grid;
  gap: 6px;
  font-size: 13px;
}

.span-2 {
  grid-column: span 2;
}

.switch-row {
  display: flex !important;
  align-items: center;
  gap: 8px;
}

.cache-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
}

.cache-actions label {
  display: grid;
  gap: 6px;
  font-size: 13px;
}

.list-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #1f2937;
  border-radius: 8px;
  padding: 8px 10px;
  text-align: left;
  cursor: pointer;
}

.list-btn.active {
  border-color: var(--primary-400);
  background: rgba(59, 130, 246, 0.1);
}

.panel-state {
  padding: 16px 0;
  color: var(--neutral-600);
}

.panel-state.error {
  color: var(--danger);
}

.btn.ghost {
  border: 1px solid var(--primary-200);
  background: transparent;
  color: var(--primary-600);
}

@media (max-width: 1200px) {
  .file-editor-grid {
    grid-template-columns: 1fr;
  }
}
</style>
