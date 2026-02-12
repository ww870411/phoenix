<template>
  <div class="spring-view">
    <AppHeader />
    <main class="container spring-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card elevated">
        <header class="card-header">
          <h2>春节简化数据看板生成</h2>
          <p class="sub">上传 xlsx 后提取为 byDate JSON（当前阶段）</p>
        </header>

        <div v-if="isOtherProject" class="state">
          <p>当前项目未启用直达单页模式，正在跳转到页面选择界面。</p>
        </div>

        <div v-else class="form-block">
          <div class="row">
            <label class="label" for="xlsx-file">选择 xlsx 文件</label>
            <input id="xlsx-file" type="file" accept=".xlsx,.xlsm,.xltx,.xltm" @change="onFileChange" />
          </div>
          <div class="row">
            <label class="label" for="sheet-name">工作表（可选）</label>
            <input
              id="sheet-name"
              v-model.trim="sheetName"
              class="text-input"
              placeholder="留空则默认第一个工作表"
              type="text"
            />
          </div>
          <div class="row checkbox-row">
            <label><input v-model="keepDiffCell" type="checkbox" /> 保留 diffCell</label>
            <label><input v-model="computeDiff" type="checkbox" /> 计算 diff=(本期-同期)/同期</label>
            <label><input v-model="normalizeMetric" type="checkbox" /> 规范化指标名称</label>
          </div>
          <div class="row actions">
            <button class="btn primary" :disabled="parsing || !selectedFile" type="button" @click="parseFile">
              {{ parsing ? '解析中…' : '上传并提取 JSON' }}
            </button>
            <button class="btn" :disabled="!parsedPayload" type="button" @click="goToDashboard">
              生成数据看板
            </button>
          </div>
          <p v-if="errorMessage" class="state error">{{ errorMessage }}</p>
          <p v-if="successMessage" class="state success">{{ successMessage }}</p>
        </div>
      </section>

      <section class="card elevated" v-if="parsedPayload">
        <header class="card-header">
          <h3>提取结果预览</h3>
          <p class="sub">
            dates={{ parsedPayload.dates?.length || 0 }}，sheet={{ parsedPayload.meta?.sheetName || '-' }}
          </p>
        </header>
        <pre class="json-preview">{{ jsonPreview }}</pre>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import { ensureProjectsLoaded, getProjectNameById } from '../../daily_report_25_26/composables/useProjects'
import { extractSpringFestivalJson, setLatestExtractedPayload } from '../services/api'

const route = useRoute()
const router = useRouter()
const projectKey = computed(() => String(route.params.projectKey || ''))
const TARGET_PROJECT_KEY = 'daily_report_spring_festval_2026'
const isOtherProject = computed(() => projectKey.value !== TARGET_PROJECT_KEY)

const selectedFile = ref(null)
const sheetName = ref('')
const keepDiffCell = ref(true)
const computeDiff = ref(true)
const normalizeMetric = ref(true)
const parsing = ref(false)
const parsedPayload = ref(null)
const errorMessage = ref('')
const successMessage = ref('')

const projectName = computed(() => getProjectNameById(projectKey.value) || projectKey.value)
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: null },
])

const jsonPreview = computed(() => {
  if (!parsedPayload.value) return '{}'
  return JSON.stringify(parsedPayload.value, null, 2)
})

watch(
  () => projectKey.value,
  (value) => {
    if (value && value !== TARGET_PROJECT_KEY) {
      router.replace(`/projects/${encodeURIComponent(value)}/pages`)
    }
  },
  { immediate: true },
)

ensureProjectsLoaded().catch(() => {})

function onFileChange(event) {
  const files = event?.target?.files || []
  selectedFile.value = files[0] || null
  errorMessage.value = ''
  successMessage.value = ''
}

async function parseFile() {
  if (!selectedFile.value) {
    errorMessage.value = '请先选择 xlsx 文件'
    return
  }
  parsing.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const payload = await extractSpringFestivalJson(projectKey.value, selectedFile.value, {
      sheetName: sheetName.value || '',
      keepDiffCell: keepDiffCell.value,
      computeDiff: computeDiff.value,
      normalizeMetric: normalizeMetric.value,
    })
    parsedPayload.value = payload
    setLatestExtractedPayload(payload)
    localStorage.setItem(
      `spring_festival_payload_${projectKey.value}`,
      JSON.stringify(payload),
    )
    sessionStorage.setItem(
      `spring_festival_payload_${projectKey.value}`,
      JSON.stringify(payload),
    )
    successMessage.value = '解析完成，已生成 JSON 预览。'
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '解析失败，请重试'
  } finally {
    parsing.value = false
  }
}

function goToDashboard() {
  if (!parsedPayload.value) {
    errorMessage.value = '请先上传并提取 JSON'
    return
  }
  router.push(`/projects/${encodeURIComponent(projectKey.value)}/spring-dashboard`)
}
</script>

<style scoped>
.spring-main {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px 0;
}

.sub {
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
}

.form-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.checkbox-row {
  font-size: 13px;
}

.label {
  min-width: 120px;
  font-size: 13px;
  color: var(--muted);
}

.text-input {
  min-width: 280px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #d0d7de;
}

.actions {
  margin-top: 4px;
}

.state {
  margin: 0;
  font-size: 13px;
}

.state.error {
  color: #b42318;
}

.state.success {
  color: #067647;
}

.json-preview {
  margin: 0;
  max-height: 58vh;
  overflow: auto;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  font-size: 12px;
}
</style>
