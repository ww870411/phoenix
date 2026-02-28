<template>
  <div class="monthly-page">
    <AppHeader />
    <main class="monthly-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>月报拉取工作台</h2>
          <p class="sub">导入映射规则后，按“源文件 ↔ 目标底表”关系完成匹配并执行导表。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn warn" type="button" :disabled="clearing" @click="handleClearWorkspace">
            {{ clearing ? '清理中...' : '清空目录' }}
          </button>
          <button class="btn primary" type="button" :disabled="downloading" @click="handleDownloadOutputsZip">
            {{ downloading ? '打包中...' : '打包下载' }}
          </button>
          <button class="btn ghost" type="button" @click="goProjects">返回项目列表</button>
        </div>
      </header>

      <section v-if="step === 1" class="card">
        <h3>步骤 1：导入映射规则</h3>
        <div class="upload-row">
          <input ref="mappingInputRef" type="file" accept=".xlsx,.xlsm,.xltx,.xltm" />
          <button class="btn primary" type="button" :disabled="analyzing" @click="analyzeMapping">
            {{ analyzing ? '解析中...' : '解析映射并生成关系' }}
          </button>
        </div>
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
      </section>

      <section v-if="step >= 2" class="card">
        <h3>步骤 2：关系确认与文件匹配</h3>
        <div class="summary">
          <span>映射文件：{{ mappingFileName || '-' }}</span>
          <span>规则总行数：{{ totalRows }}</span>
          <span>业务分组数：{{ groups.length }}</span>
        </div>
        <div class="batch-row">
          <input ref="batchSrcInputRef" class="hidden-input" type="file" multiple accept=".xlsx,.xlsm,.xltx,.xltm" @change="handleBatchPick('src', $event)" />
          <input ref="batchTgtInputRef" class="hidden-input" type="file" multiple accept=".xlsx,.xlsm,.xltx,.xltm" @change="handleBatchPick('tgt', $event)" />
          <button class="btn" type="button" :disabled="batchUploading" @click="triggerBatchUpload('src')">
            {{ batchUploading ? '处理中...' : '批量上传源文件并识别' }}
          </button>
          <button class="btn" type="button" :disabled="batchUploading" @click="triggerBatchUpload('tgt')">
            {{ batchUploading ? '处理中...' : '批量上传底表并识别' }}
          </button>
        </div>
        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>
        <div v-if="batchPreview" class="batch-preview">
          <h4>批量识别预览（{{ batchPreview.type === 'src' ? '源文件' : '目标底表' }}）</h4>
          <table class="preview-table">
            <thead>
              <tr>
                <th>文件名</th>
                <th>识别结果</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in batchPreview.items" :key="item.filename">
                <td>{{ item.filename }}</td>
                <td>
                  <span v-if="item.matchedKey">{{ normalizeReferenceName(item.matchedKey) || item.matchedKey }}</span>
                  <span v-else class="unmatched">未匹配</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div class="preview-actions">
            <button class="btn primary" type="button" :disabled="batchUploading || batchPreview.matchedCount === 0" @click="applyBatchPreview">
              {{ batchUploading ? '上传中...' : `确认应用（${batchPreview.matchedCount}）` }}
            </button>
            <button class="btn" type="button" :disabled="batchUploading" @click="clearBatchPreview">
              取消
            </button>
          </div>
        </div>

        <div class="group-list">
          <article class="group-card" v-for="group in groups" :key="group.id">
            <header>
              <h4>业务组 {{ group.id + 1 }}</h4>
            </header>
            <div class="group-body">
              <section class="side">
                <h5>源文件</h5>
                <div v-for="key in group.src" :key="`src-${group.id}-${key}`" class="slot-card">
                  <div class="slot-title">{{ normalizeReferenceName(key) }}</div>
                  <div class="slot-actions">
                    <input type="file" accept=".xlsx,.xlsm,.xltx,.xltm" @change="pickFile('src', key, $event)" />
                  </div>
                  <div class="slot-file">{{ fileState.src[key]?.name || '未选择文件' }}</div>
                  <div class="sheet-map" v-if="fileState.src[key]?.sheets?.length">
                    <div v-if="sheetRequirements[key]?.length" class="sheet-map-list">
                      <div class="sheet-row" v-for="ruleSheet in sheetRequirements[key]" :key="`${key}-${ruleSheet}`">
                        <span class="label">{{ ruleSheet }}</span>
                        <select
                          :value="fileState.src[key]?.sheetMapping?.[ruleSheet] || fileState.src[key]?.sheets?.[0]"
                          @change="updateSheetMapping(key, ruleSheet, $event.target.value)"
                        >
                          <option v-for="sheet in fileState.src[key]?.sheets" :key="sheet" :value="sheet">{{ sheet }}</option>
                        </select>
                      </div>
                    </div>
                    <div v-else class="sheet-row">
                      <span class="label">工作表</span>
                      <select :value="fileState.src[key]?.defaultSheet || ''" @change="updateDefaultSheet('src', key, $event.target.value)">
                        <option v-for="sheet in fileState.src[key]?.sheets" :key="sheet" :value="sheet">{{ sheet }}</option>
                      </select>
                    </div>
                  </div>
                </div>
              </section>

              <section class="side">
                <h5>目标底表</h5>
                <div v-for="key in group.tgt" :key="`tgt-${group.id}-${key}`" class="slot-card">
                  <div class="slot-title">{{ normalizeReferenceName(key) }}</div>
                  <div class="slot-actions">
                    <input type="file" accept=".xlsx,.xlsm,.xltx,.xltm" @change="pickFile('tgt', key, $event)" />
                  </div>
                  <div class="slot-file">{{ fileState.tgt[key]?.name || '未选择文件' }}</div>
                  <div class="sheet-map" v-if="fileState.tgt[key]?.sheets?.length">
                    <div class="sheet-row">
                      <span class="label">工作表</span>
                      <select :value="fileState.tgt[key]?.defaultSheet || ''" @change="updateDefaultSheet('tgt', key, $event.target.value)">
                        <option v-for="sheet in fileState.tgt[key]?.sheets" :key="sheet" :value="sheet">{{ sheet }}</option>
                      </select>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </article>
        </div>

        <div class="action-row">
          <button class="btn primary" type="button" :disabled="executing || !canExecute" @click="executeJob">
            {{ executing ? '执行中...' : '步骤 3：执行导表' }}
          </button>
          <span class="hint" v-if="!canExecute">请先为所有源文件与目标底表完成上传与 sheet 选择。</span>
        </div>
      </section>

      <section v-if="step === 3" class="card">
        <h3>步骤 3：导表结果</h3>
        <ul class="result-list">
          <li v-for="name in resultFiles" :key="name">
            <button class="result-download" type="button" @click="handleDownloadOutput(name)">{{ name }}</button>
          </li>
        </ul>
        <div class="exception-section" v-if="exceptionLogName">
          <h4>异常清单</h4>
          <div class="exception-summary" v-if="exceptionSummary">
            <span>总行数：{{ exceptionSummary.rows_total || 0 }}</span>
            <span>累计一致：{{ exceptionSummary.acc_ok || 0 }}</span>
            <span>累计不一致：{{ exceptionSummary.acc_mismatch || 0 }}</span>
            <span>保留公式：{{ exceptionSummary.acc_skipped_formula || 0 }}</span>
            <span>公式未校验：{{ exceptionSummary.acc_formula_not_verifiable || 0 }}</span>
          </div>
          <p v-if="!exceptionItems.length" class="hint">未发现异常行。</p>
          <table v-else class="exception-table">
            <thead>
              <tr>
                <th>行号</th>
                <th>指标名称</th>
                <th>源键</th>
                <th>目标键</th>
                <th>状态</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in exceptionItems" :key="item.key">
                <td>{{ item.row_index }}</td>
                <td>{{ item.indicator_name || '-' }}</td>
                <td>{{ normalizeReferenceName(item.src_key || '') || '-' }}</td>
                <td>{{ normalizeReferenceName(item.tgt_key || '') || '-' }}</td>
                <td>{{ item.status }}</td>
                <td>{{ item.message }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card">
        <h3>默认目录</h3>
        <ul class="path-list">
          <li v-for="item in pathItems" :key="item.key">
            <span class="label">{{ item.label }}</span>
            <code class="value">{{ item.value }}</code>
          </li>
        </ul>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import {
  analyzeMonthlyDataPullMapping,
  clearMonthlyDataPullWorkspace,
  downloadMonthlyDataPullOutputFile,
  downloadMonthlyDataPullOutputsZip,
  executeMonthlyDataPull,
  getMonthlyDataPullSheets,
  getMonthlyDataPullWorkspace,
} from '../../daily_report_25_26/services/api'

const route = useRoute()
const router = useRouter()
const projectKey = computed(() => String(route.params.projectKey || 'monthly_data_pull'))
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '月报拉取工作台', to: null },
])

const step = ref(1)
const analyzing = ref(false)
const executing = ref(false)
const clearing = ref(false)
const downloading = ref(false)
const batchUploading = ref(false)
const errorMessage = ref('')
const mappingInputRef = ref(null)
const batchSrcInputRef = ref(null)
const batchTgtInputRef = ref(null)
const mappingFileName = ref('')
const mappingStoredName = ref('')
const totalRows = ref(0)
const groups = ref([])
const sheetRequirements = ref({})
const requiredSrcFiles = ref([])
const requiredTgtFiles = ref([])
const resultFiles = ref([])
const workspacePaths = ref({})
const batchPreview = ref(null)
const exceptionItems = ref([])
const exceptionSummary = ref(null)
const exceptionLogName = ref('')

const fileState = reactive({ src: {}, tgt: {} })

const pathItems = computed(() => [
  { key: 'mapping_rules_dir', label: '映射规则目录', value: workspacePaths.value.mapping_rules_dir || '-' },
  { key: 'source_reports_dir', label: '源文件目录', value: workspacePaths.value.source_reports_dir || '-' },
  { key: 'target_templates_dir', label: '目标底表目录', value: workspacePaths.value.target_templates_dir || '-' },
  { key: 'outputs_dir', label: '输出目录', value: workspacePaths.value.outputs_dir || '-' },
])

const canExecute = computed(() => {
  const srcOk = requiredSrcFiles.value.every((key) => Boolean(fileState.src[key]?.stored_name) && Boolean(resolveSheetValue('src', key)))
  const tgtOk = requiredTgtFiles.value.every((key) => Boolean(fileState.tgt[key]?.stored_name) && Boolean(resolveSheetValue('tgt', key)))
  return Boolean(mappingStoredName.value) && srcOk && tgtOk
})

function goProjects() {
  router.push('/projects')
}

function resetExceptionPanel() {
  exceptionItems.value = []
  exceptionSummary.value = null
  exceptionLogName.value = ''
}

async function handleClearWorkspace() {
  if (clearing.value) return
  const confirmed = window.confirm('确认清空 mapping_rules/source_reports/target_templates/outputs 四个目录中的文件吗？')
  if (!confirmed) return
  clearing.value = true
  errorMessage.value = ''
  try {
    const payload = await clearMonthlyDataPullWorkspace(projectKey.value)
    const stats = payload?.cleared || {}
    alert(
      `目录清理完成：映射${stats.mapping_rules || 0}，源文件${stats.source_reports || 0}，目标底表${stats.target_templates || 0}，输出${stats.outputs || 0}`,
    )
    mappingFileName.value = ''
    mappingStoredName.value = ''
    totalRows.value = 0
    groups.value = []
    sheetRequirements.value = {}
    requiredSrcFiles.value = []
    requiredTgtFiles.value = []
    resultFiles.value = []
    fileState.src = {}
    fileState.tgt = {}
    batchPreview.value = null
    resetExceptionPanel()
    step.value = 1
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '清空目录失败'
  } finally {
    clearing.value = false
  }
}

async function handleDownloadOutputsZip() {
  if (downloading.value) return
  downloading.value = true
  errorMessage.value = ''
  try {
    const { blob, filename } = await downloadMonthlyDataPullOutputsZip(projectKey.value)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename || 'monthly_data_pull_outputs.zip'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '打包下载失败'
  } finally {
    downloading.value = false
  }
}

function normalizeReferenceName(name) {
  const text = String(name || '').trim()
  if (!text) return ''
  const withoutExt = text.replace(/\.[^.]+$/, '')
  const normalized = withoutExt
    .replace(/（[^）]*）/g, '')
    .replace(/\([^)]*\)/g, '')
    .replace(/【[^】]*】/g, '')
    .replace(/\[[^\]]*\]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  return normalized || withoutExt
}

function normalizeMatchToken(name) {
  return String(name || '')
    .trim()
    .toLowerCase()
    .replace(/\.[^.]+$/, '')
    .replace(/（[^）]*）/g, '')
    .replace(/\([^)]*\)/g, '')
    .replace(/【[^】]*】/g, '')
    .replace(/\[[^\]]*\]/g, '')
    .replace(/[^\p{L}\p{N}]+/gu, '')
}

function pickBestSheetName(ruleSheet, actualSheets = []) {
  const expected = normalizeMatchToken(ruleSheet)
  if (!expected || !Array.isArray(actualSheets) || actualSheets.length === 0) {
    return actualSheets?.[0] || ''
  }
  let best = actualSheets[0] || ''
  let bestScore = -1
  for (const sheet of actualSheets) {
    const token = normalizeMatchToken(sheet)
    if (!token) continue
    let score = 0
    if (token === expected) score = 1000 + token.length
    else if (token.includes(expected)) score = 700 + expected.length
    else if (expected.includes(token)) score = 500 + token.length
    if (score > bestScore) {
      bestScore = score
      best = sheet
    }
  }
  return best || actualSheets[0] || ''
}

function findBestSlotKey(filename, keys = [], takenSet = new Set()) {
  const fileToken = normalizeMatchToken(filename)
  if (!fileToken || !Array.isArray(keys) || keys.length === 0) return ''
  let bestKey = ''
  let bestScore = -1
  let duplicateBest = false

  for (const key of keys) {
    if (takenSet.has(key)) continue
    const keyToken = normalizeMatchToken(key)
    if (!keyToken) continue
    let score = -1
    if (fileToken === keyToken) score = 1000 + keyToken.length
    else if (fileToken.includes(keyToken)) score = 800 + keyToken.length
    else if (keyToken.includes(fileToken)) score = 600 + fileToken.length
    if (score < 0) continue
    if (score > bestScore) {
      bestScore = score
      bestKey = key
      duplicateBest = false
    } else if (score === bestScore) {
      duplicateBest = true
    }
  }

  if (duplicateBest) return ''
  return bestKey
}

function applyUploadedFile(type, key, file, payload) {
  const bucket = type === 'src' ? 'source_reports' : 'target_templates'
  fileState[type][key] = {
    name: file.name,
    stored_name: payload.stored_name,
    bucket,
    sheets: payload.sheets || [],
    defaultSheet: (payload.sheets || [])[0] || '',
    sheetMapping: {},
  }
  if (type === 'src' && Array.isArray(sheetRequirements.value[key]) && sheetRequirements.value[key].length > 0) {
    const autoMap = {}
    const availableSheets = payload.sheets || []
    for (const ruleSheet of sheetRequirements.value[key]) {
      autoMap[ruleSheet] = pickBestSheetName(ruleSheet, availableSheets)
    }
    fileState[type][key].sheetMapping = autoMap
  }
}

function resolveSheetValue(type, key) {
  const item = fileState[type][key]
  if (!item) return ''
  if (type === 'src' && item.sheetMapping && Object.keys(item.sheetMapping).length > 0) {
    return JSON.stringify(item.sheetMapping)
  }
  return item.defaultSheet || ''
}

async function loadWorkspace() {
  const payload = await getMonthlyDataPullWorkspace(projectKey.value)
  workspacePaths.value = payload?.paths || {}
}

async function analyzeMapping() {
  errorMessage.value = ''
  const file = mappingInputRef.value?.files?.[0]
  if (!file) {
    errorMessage.value = '请先选择映射文件。'
    return
  }
  analyzing.value = true
  try {
    const payload = await analyzeMonthlyDataPullMapping(projectKey.value, file)
    mappingFileName.value = file.name
    mappingStoredName.value = payload?.filename || ''
    totalRows.value = Number(payload?.data?.total_rows || 0)
    groups.value = payload?.data?.groups || []
    sheetRequirements.value = payload?.data?.sheet_requirements || {}
    requiredSrcFiles.value = payload?.data?.required_src_files || []
    requiredTgtFiles.value = payload?.data?.required_tgt_files || []
    step.value = 2
    resultFiles.value = []
    batchPreview.value = null
    resetExceptionPanel()
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '映射解析失败'
  } finally {
    analyzing.value = false
  }
}

async function pickFile(type, key, event) {
  const file = event?.target?.files?.[0]
  if (!file) return
  errorMessage.value = ''
  try {
    const bucket = type === 'src' ? 'source_reports' : 'target_templates'
    const payload = await getMonthlyDataPullSheets(projectKey.value, bucket, file)
    applyUploadedFile(type, key, file, payload)
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '读取工作表失败'
  }
}

async function handleBatchPick(type, event) {
  const files = Array.from(event?.target?.files || [])
  if (!files.length) return
  if (batchUploading.value) return
  errorMessage.value = ''

  const isSrc = type === 'src'
  const keys = isSrc ? requiredSrcFiles.value : requiredTgtFiles.value
  const taken = new Set()
  const items = files.map((file) => {
    const matchedKey = findBestSlotKey(file.name, keys, taken)
    if (matchedKey) taken.add(matchedKey)
    return {
      file,
      filename: file.name,
      matchedKey,
    }
  })

  batchPreview.value = {
    type,
    items,
    matchedCount: items.filter((item) => Boolean(item.matchedKey)).length,
  }

  const inputRef = isSrc ? batchSrcInputRef.value : batchTgtInputRef.value
  if (inputRef) inputRef.value = ''
}

async function applyBatchPreview() {
  if (!batchPreview.value || batchUploading.value) return
  const preview = batchPreview.value
  const isSrc = preview.type === 'src'
  const bucket = isSrc ? 'source_reports' : 'target_templates'
  const matched = []
  const unmatched = []
  batchUploading.value = true
  errorMessage.value = ''
  try {
    for (const item of preview.items) {
      if (!item.matchedKey) {
        unmatched.push(item.filename)
        continue
      }
      const payload = await getMonthlyDataPullSheets(projectKey.value, bucket, item.file)
      applyUploadedFile(preview.type, item.matchedKey, item.file, payload)
      matched.push(`${item.filename} -> ${normalizeReferenceName(item.matchedKey) || item.matchedKey}`)
    }
    const lines = []
    lines.push(`已自动匹配 ${matched.length} 个文件。`)
    if (matched.length) lines.push(matched.join('\n'))
    if (unmatched.length) lines.push(`未匹配 ${unmatched.length} 个文件：${unmatched.join('、')}`)
    alert(lines.join('\n\n'))
    batchPreview.value = null
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '批量上传失败'
    alert(errorMessage.value)
  } finally {
    batchUploading.value = false
  }
}

function clearBatchPreview() {
  if (batchUploading.value) return
  batchPreview.value = null
}

function triggerBatchUpload(type) {
  if (batchUploading.value) return
  const inputRef = type === 'src' ? batchSrcInputRef.value : batchTgtInputRef.value
  if (inputRef) inputRef.click()
}

function updateSheetMapping(srcKey, ruleSheet, actualSheet) {
  if (!fileState.src[srcKey]) return
  const next = { ...(fileState.src[srcKey].sheetMapping || {}) }
  next[ruleSheet] = actualSheet
  fileState.src[srcKey].sheetMapping = next
}

function updateDefaultSheet(type, key, sheet) {
  if (!fileState[type][key]) return
  fileState[type][key].defaultSheet = sheet
}

async function executeJob() {
  if (!canExecute.value || executing.value) return
  executing.value = true
  errorMessage.value = ''
  try {
    const srcPayload = {}
    const tgtPayload = {}
    for (const key of requiredSrcFiles.value) {
      const item = fileState.src[key]
      srcPayload[key] = {
        bucket: item.bucket,
        stored_name: item.stored_name,
        sheet: resolveSheetValue('src', key),
      }
    }
    for (const key of requiredTgtFiles.value) {
      const item = fileState.tgt[key]
      tgtPayload[key] = {
        bucket: item.bucket,
        stored_name: item.stored_name,
        sheet: resolveSheetValue('tgt', key),
      }
    }

    const payload = await executeMonthlyDataPull(projectKey.value, {
      mapping_file: mappingStoredName.value,
      src_files: srcPayload,
      tgt_files: tgtPayload,
    })
    resultFiles.value = payload?.files || []
    await loadExceptionPanel(resultFiles.value)
    step.value = 3
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '执行导表失败'
  } finally {
    executing.value = false
  }
}

function toExceptionMessage(logRow) {
  const messages = []
  if (logRow?.status && String(logRow.status).startsWith('error_')) {
    messages.push(`执行失败：${logRow.status}`)
  }
  if (logRow?.acc_compare_status === 'mismatch') {
    messages.push(`累计不一致，差值=${logRow?.acc_compare_diff ?? '-'}`)
  }
  if (logRow?.acc_compare_status === 'formula_not_verifiable') {
    messages.push('累计公式无法校验，请检查公式是否包含函数/复杂引用')
  }
  if (logRow?.status === 'warn_formula_text_from_source') {
    messages.push('源值为公式文本，可能导致目标异常')
  }
  if (logRow?.error) {
    messages.push(`错误：${logRow.error}`)
  }
  if (logRow?.message) {
    messages.push(logRow.message)
  }
  return messages.join('；') || '-'
}

async function loadExceptionPanel(files = []) {
  resetExceptionPanel()
  const list = Array.isArray(files) ? files : []
  const logName = list
    .filter((name) => String(name || '').toLowerCase().endsWith('.json') && String(name || '').includes('execution_log_'))
    .sort()
    .pop()
  if (!logName) return

  try {
    const { blob } = await downloadMonthlyDataPullOutputFile(projectKey.value, logName)
    const text = await blob.text()
    const payload = JSON.parse(text || '{}')
    const logs = Array.isArray(payload?.logs) ? payload.logs : []
    const exceptions = logs
      .filter((item) => {
        const status = String(item?.status || '')
        const accStatus = String(item?.acc_compare_status || '')
        return (
          status.startsWith('error_') ||
          status === 'warn_formula_text_from_source' ||
          status === 'warn_source_empty' ||
          status === 'warn_month_expr_invalid' ||
          status === 'warn_acc_expr_invalid' ||
          accStatus === 'mismatch' ||
          accStatus === 'formula_not_verifiable'
        )
      })
      .map((item, idx) => ({
        key: `${item?.row_index || 'x'}-${idx}`,
        row_index: item?.row_index || '-',
        indicator_name: item?.indicator_name || '',
        src_key: item?.src_key || '',
        tgt_key: item?.tgt_key || '',
        status: item?.acc_compare_status === 'mismatch' ? 'acc_mismatch' : String(item?.status || '-'),
        message: toExceptionMessage(item),
      }))
    exceptionItems.value = exceptions
    exceptionSummary.value = {
      rows_total: Number(payload?.rows_total || 0),
      acc_ok: Number(payload?.acc_compare_stats?.ok || 0),
      acc_mismatch: Number(payload?.acc_compare_stats?.mismatch || 0),
      acc_skipped_formula: Number(payload?.acc_compare_stats?.skipped_target_formula || 0),
      acc_formula_not_verifiable: Number(payload?.acc_compare_stats?.formula_not_verifiable || 0),
    }
    exceptionLogName.value = String(logName)
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '读取异常清单失败'
  }
}

async function handleDownloadOutput(filename) {
  errorMessage.value = ''
  try {
    const { blob, filename: actualName } = await downloadMonthlyDataPullOutputFile(projectKey.value, filename)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = actualName || filename || 'download.bin'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '下载文件失败'
    alert(errorMessage.value)
  }
}

onMounted(() => {
  loadWorkspace().catch((error) => {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '读取默认目录失败'
  })
})
</script>

<style scoped>
.monthly-page {
  min-height: 100vh;
  background: #f8fafc;
}

.monthly-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 18px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.topbar h2 {
  margin: 0;
}

.sub {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
}

.upload-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.summary {
  display: flex;
  gap: 12px;
  color: #334155;
  font-size: 13px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.batch-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.hidden-input {
  display: none;
}

.batch-preview {
  border: 1px solid #dbeafe;
  background: #f8fbff;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 10px;
}

.batch-preview h4 {
  margin: 0 0 8px;
  font-size: 14px;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
}

.preview-table th,
.preview-table td {
  border: 1px solid #dbeafe;
  padding: 6px 8px;
  font-size: 12px;
  text-align: left;
}

.preview-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.unmatched {
  color: #b91c1c;
}

.group-list {
  display: grid;
  gap: 12px;
}

.group-card {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 10px;
  background: #f8fbff;
}

.group-card h4 {
  margin: 0 0 8px;
}

.group-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.side h5 {
  margin: 0 0 6px;
  color: #475569;
}

.slot-card {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
  margin-bottom: 8px;
}

.slot-title {
  font-weight: 600;
  font-size: 13px;
}

.slot-actions {
  margin-top: 6px;
}

.slot-file {
  margin-top: 4px;
  color: #64748b;
  font-size: 12px;
}

.sheet-map {
  margin-top: 8px;
}

.sheet-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 6px;
  align-items: center;
}

.sheet-row .label {
  font-size: 12px;
  color: #475569;
}

select {
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px 6px;
  background: #fff;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.hint {
  color: #64748b;
  font-size: 12px;
}

.result-list {
  margin: 0;
  padding-left: 18px;
}

.result-list li {
  margin-bottom: 4px;
}

.result-list a {
  color: #1d4ed8;
}

.result-download {
  border: none;
  background: transparent;
  color: #1d4ed8;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
  font-size: 13px;
}

.exception-section {
  margin-top: 12px;
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
}

.exception-section h4 {
  margin: 0 0 8px;
}

.exception-summary {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #475569;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.exception-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.exception-table th,
.exception-table td {
  border: 1px solid #dbeafe;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}

.path-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}

.path-list li {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 8px;
  align-items: center;
}

.path-list .label {
  color: #475569;
  font-size: 12px;
}

.value {
  display: block;
  padding: 6px 8px;
  background: #f1f5f9;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  word-break: break-all;
}

.error {
  margin-top: 8px;
  color: #b91c1c;
  font-size: 13px;
}

.btn {
  border: 1px solid #94a3b8;
  border-radius: 8px;
  padding: 8px 12px;
  cursor: pointer;
  background: #fff;
}

.btn.primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.btn.warn {
  background: #ef4444;
  border-color: #ef4444;
  color: #fff;
}

.btn.ghost {
  color: #334155;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 960px) {
  .group-body {
    grid-template-columns: 1fr;
  }
  .path-list li {
    grid-template-columns: 1fr;
  }
}
</style>
