<template>
  <details class="bill-import card elevated">
    <summary>日账单上传入库 <span>按电厂、机组、96时段保存量价</span></summary>
    <div class="bill-body">
      <p class="hint">提取各机组计量电量、中长期合约电量和电价，省内实时价共用一份。保留零值与空白；原始Excel完整归档，其他科目、电费及日合计不写入15分钟表。</p>
      <div class="actions">
        <label class="file-picker">选择日账单（可多选）<input ref="fileInput" type="file" accept=".xlsx" multiple :disabled="busy" @change="chooseFiles" /></label>
        <button type="button" :disabled="busy || !files.length" @click="preview">{{ busy && phase === 'preview' ? '正在读取…' : '读取并预览' }}</button>
        <button v-if="previewData" type="button" :disabled="busy" @click="confirm">{{ busy && phase === 'confirm' ? '正在入库…' : overwriteRequired ? '确认覆盖该厂同日数据' : '确认入库' }}</button>
      </div>
      <p v-if="error" role="alert" class="error">{{ error }}</p>
      <p v-if="message" role="status">{{ message }}</p>
      <div v-if="previewData" class="preview">
        <div v-for="file in previewData.files" :key="file.file_sha256" class="file-preview">
          <strong>{{ file.source_file }}</strong>
          <p class="hint">{{ file.units.length }} 台机组 · 每台96时段 · 下方合计用于核对原账单，不写入分时表</p>
          <p class="hint">{{ file.units[0]?.unit_label }}</p>
          <div class="table-scroll"><table>
            <thead><tr><th>结算日期</th><th>电厂/机组</th><th>计量电量（MWh）</th><th>账单小计（元）</th><th>科目数</th></tr></thead>
            <tbody><tr v-for="unit in file.units" :key="unit.worksheet + unit.settlement_unit_id">
              <td>{{ unit.settlement_date }}</td><td>{{ unit.settlement_unit_name }}</td>
              <td>{{ cellValue(unit.unit_metered_quantity) }}</td><td>{{ cellValue(unit.unit_total_fee) }}</td><td>{{ unit.subjects }}</td>
            </tr></tbody>
          </table></div>
          <p v-for="warning in file.warnings" :key="warning" class="warning">{{ warning }}</p>
        </div>
      </div>
    </div>
  </details>
</template>

<script setup>
import { ref } from 'vue'
import { previewSpotBills, confirmSpotBills } from '../services/api'

const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['imported'])
const files = ref([]), previewData = ref(null), busy = ref(false), phase = ref(''), error = ref(''), message = ref('')
const overwriteRequired = ref(false)
const fileInput = ref(null)
function cellValue(value) { return value === null || value === undefined ? '空白' : String(value) }
function chooseFiles(event) {
  files.value = Array.from(event.target.files || [])
  previewData.value = null
  overwriteRequired.value = false
  error.value = message.value = ''
}
async function preview() {
  overwriteRequired.value = false
  busy.value = true; phase.value = 'preview'; error.value = message.value = ''; previewData.value = null
  try { previewData.value = await previewSpotBills(props.projectKey, files.value) }
  catch (err) { error.value = err.message }
  finally { busy.value = false }
}
async function confirm() {
  if (!previewData.value || busy.value) return
  busy.value = true; phase.value = 'confirm'; error.value = ''
  try {
    const result = await confirmSpotBills(props.projectKey, previewData.value.token, overwriteRequired.value)
    if (result.needs_overwrite) {
      overwriteRequired.value = true
      error.value = `${result.conflicts.join('；')}。请核对预览后点击“确认覆盖该厂同日数据”。`
      return
    }
    message.value = `入库完成：写入/更新 ${result.inserted} 个15分钟时点，${result.imported.length} 份文件；相同文件跳过 ${result.skipped.length} 份。`
    overwriteRequired.value = false
    previewData.value = null
    files.value = []
    if (fileInput.value) fileInput.value.value = ''
    emit('imported')
  } catch (err) { error.value = `${err.message}。未确认成功时可重试同一批文件。` }
  finally { busy.value = false }
}
</script>

<style scoped>
.bill-import { padding: 12px 16px; background: #fff; border: 1px solid #dbeafe; border-radius: 10px; min-width: 0; }
summary { cursor: pointer; font-weight: 600; }
summary span, .hint { color: #64748b; font-size: 12px; font-weight: 400; }
.bill-body { display: flex; flex-direction: column; gap: 10px; padding-top: 10px; min-width: 0; }
.bill-body p { margin: 4px 0; }
.actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.file-picker { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 13px; }
input[type=file] { max-width: 100%; }
button, select { border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px 9px; background: #f8fafc; cursor: pointer; }
button:disabled { opacity: .5; cursor: default; }
.file-preview { padding: 10px; background: #f8fbff; border: 1px solid #dbeafe; border-radius: 6px; }
.table-scroll { max-width: 100%; overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th, td { text-align: left; padding: 6px 8px; border: 1px solid #e2e8f0; white-space: nowrap; }
th { background: #f1f5f9; }
.error { color: #b91c1c; }.warning { color: #92400e; }
</style>
