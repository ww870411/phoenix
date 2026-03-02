<template>
  <div class="monthly-show-page">
    <AppHeader />
    <main class="monthly-show-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="topbar">
        <div>
          <h2>月报导入工作台</h2>
          <p class="sub">上传月报文件，按口径与字段提取入库 CSV。</p>
        </div>
      </section>

      <section class="card">
        <h3>步骤 1：上传并读取可选项</h3>
        <div class="upload-row">
          <input ref="fileInputRef" type="file" accept=".xlsx,.xlsm,.xltx,.xltm" @change="onFileChange" />
          <button class="btn primary" type="button" :disabled="inspecting || !selectedFile" @click="inspectFile">
            {{ inspecting ? '读取中...' : '读取口径与字段' }}
          </button>
        </div>
        <p class="hint" v-if="selectedFile">当前文件：{{ selectedFile.name }}</p>
      </section>

      <section class="card">
        <h3>步骤 2：复选提取范围</h3>
        <p v-if="!sourceColumns.length && !companies.length && !fields.length" class="hint">
          请先在步骤 1 上传文件并点击“读取口径与字段”，然后在此处进行复选。
        </p>

        <div class="panel">
          <div class="panel-head">
            <h4>报告月份设定（自动识别，可修改）</h4>
          </div>
          <div class="month-config-row">
            <label class="month-field">
              <span>年份</span>
              <input class="num-input" type="number" min="2000" max="2099" step="1" v-model.number="reportYearInput" />
            </label>
            <label class="month-field">
              <span>月份</span>
              <input class="num-input" type="number" min="1" max="12" step="1" v-model.number="reportMonthInput" />
            </label>
            <span class="hint">来源月份将写入：{{ reportMonthDatePreview }}</span>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h4>源字段（计划/实际口径）</h4>
            <div class="actions">
              <button class="btn small" type="button" :disabled="!sourceColumns.length" @click="toggleAllSourceColumns(true)">全选</button>
              <button class="btn small" type="button" :disabled="!sourceColumns.length" @click="toggleAllSourceColumns(false)">全不选</button>
            </div>
          </div>
          <div class="checkbox-grid">
            <label v-for="col in sourceColumns" :key="col" class="check-item">
              <input type="checkbox" :value="col" v-model="selectedSourceColumns" />
              <span>{{ col }}</span>
            </label>
          </div>
          <p v-if="!sourceColumns.length" class="hint">暂无可选源字段</p>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h4>常量注入设定</h4>
            <label class="check-item">
              <input type="checkbox" v-model="constantsEnabled" :disabled="!constantRules.length" />
              <span>启用常量注入</span>
            </label>
          </div>
          <p class="hint">默认值已按你提供的规则预置，可直接修改数值，并设置写入源字段。</p>
          <div class="table-wrap" v-if="constantRules.length">
            <table class="constant-table">
              <thead>
                <tr>
                  <th>口径</th>
                  <th>指标</th>
                  <th>单位</th>
                  <th>值</th>
                  <th>写入源字段</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(rule, idx) in constantRules" :key="`${rule.company}-${rule.item}-${idx}`">
                  <td>{{ rule.company }}</td>
                  <td>{{ rule.item }}</td>
                  <td>{{ rule.unit }}</td>
                  <td>
                    <input
                      class="num-input"
                      type="number"
                      step="0.0001"
                      v-model.number="rule.value"
                      :disabled="!constantsEnabled"
                    />
                  </td>
                  <td>
                    <div class="inline-checks">
                      <label class="check-item compact" v-for="col in sourceColumns" :key="`${idx}-${col}`">
                        <input
                          type="checkbox"
                          :value="col"
                          :disabled="!constantsEnabled"
                          :checked="Array.isArray(rule.source_columns) && rule.source_columns.includes(col)"
                          @change="toggleRuleSourceColumn(idx, col, $event.target?.checked)"
                        />
                        <span>{{ col }}</span>
                      </label>
                    </div>
                    <p class="hint" v-if="!sourceColumns.length">暂无可用源字段</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="hint">暂无常量规则</p>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h4>口径（子工作表）</h4>
            <div class="actions">
              <button class="btn small" type="button" :disabled="!companies.length" @click="toggleAllCompanies(true)">全选</button>
              <button class="btn small" type="button" :disabled="!companies.length" @click="toggleAllCompanies(false)">全不选</button>
            </div>
          </div>
          <div class="checkbox-grid">
            <label v-for="company in companies" :key="company" class="check-item">
              <input type="checkbox" :value="company" v-model="selectedCompanies" />
              <span>{{ company }}</span>
            </label>
          </div>
          <p v-if="!companies.length" class="hint">暂无可选口径</p>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h4>字段</h4>
            <div class="actions">
              <button class="btn small" type="button" :disabled="!fields.length" @click="toggleAllFields(true)">全选</button>
              <button class="btn small" type="button" :disabled="!fields.length" @click="toggleAllFields(false)">全不选</button>
            </div>
          </div>
          <div class="checkbox-grid">
            <label v-for="field in fields" :key="field" class="check-item">
              <input type="checkbox" :value="field" v-model="selectedFields" />
              <span>{{ field }}</span>
            </label>
          </div>
          <p v-if="!fields.length" class="hint">暂无可选字段</p>
        </div>

        <div class="panel">
          <div class="panel-head">
            <h4>规则执行选择</h4>
            <div class="actions">
              <button class="btn small" type="button" :disabled="!extractionRules.length" @click="showRulePickerDialog = true">打开规则列表</button>
            </div>
          </div>
          <p class="hint" v-if="extractionRules.length">已选择 {{ selectedExtractionRuleIds.length }} / {{ extractionRules.length }} 项规则</p>
          <p class="hint" v-if="selectedRuleSummaryText">当前规则：{{ selectedRuleSummaryText }}</p>
          <p class="hint" v-if="!extractionRules.length">暂无可选规则</p>
        </div>
      </section>

      <section class="card">
        <h3>步骤 3：导出 CSV</h3>
        <div class="upload-row">
          <button
            class="btn primary"
            type="button"
            :disabled="extracting || !selectedFile || !selectedCompanies.length || !selectedFields.length || !selectedSourceColumns.length || !selectedExtractionRuleIds.length"
            @click="extractCsv"
          >
            {{ extracting ? '提取中...' : '提取 CSV' }}
          </button>
          <button
            class="btn primary"
            type="button"
            :disabled="extracting || !lastExtractedCsvFile"
            @click="downloadExtractedCsv"
          >
            下载 CSV
          </button>
        </div>
        <p class="hint" v-if="extractMessage">{{ extractMessage }}</p>
        <div class="actions" v-if="extractRuleDetailLines.length">
          <button class="btn small" type="button" @click="showRuleDetailDialog = true">查看规则命中详情</button>
        </div>
        <p class="hint">默认已忽略口径：恒流、天然气炉、中水。</p>
      </section>

      <section class="card">
        <h3>步骤 4：CSV 入库（写入 monthly_data_show）</h3>
        <div class="upload-row">
          <input type="file" accept=".csv" @change="onCsvFileChange" />
          <button class="btn primary" type="button" :disabled="importing || !lastExtractedCsvFile" @click="importLastExtractedCsv">
            {{ importing ? '入库中...' : '使用第3步结果一键入库' }}
          </button>
          <button class="btn primary" type="button" :disabled="importing || !selectedCsvFile" @click="importCsvToDatabase">
            {{ importing ? '入库中...' : '上传 CSV 并入库' }}
          </button>
        </div>
        <p class="hint" v-if="lastExtractedCsvFile">第3步已缓存：{{ lastExtractedCsvFile.name }}</p>
        <p class="hint" v-if="selectedCsvFile">当前 CSV：{{ selectedCsvFile.name }}</p>
        <p class="hint" v-if="importMessage">{{ importMessage }}</p>
      </section>

      <p class="error" v-if="errorMessage">{{ errorMessage }}</p>
    </main>

    <div class="dialog-mask" v-if="showRuleDetailDialog" @click.self="showRuleDetailDialog = false">
      <div class="dialog-card">
        <div class="dialog-head">
          <h4>规则命中详情</h4>
          <button class="btn small" type="button" @click="showRuleDetailDialog = false">关闭</button>
        </div>
        <div class="dialog-body">
          <div class="rule-line" v-for="(line, idx) in extractRuleDetailLines" :key="`rule-${idx}`">{{ line }}</div>
        </div>
      </div>
    </div>
    <div class="dialog-mask" v-if="showRulePickerDialog" @click.self="showRulePickerDialog = false">
      <div class="dialog-card">
        <div class="dialog-head">
          <h4>规则执行选择</h4>
          <div class="actions">
            <button class="btn small" type="button" :disabled="!extractionRules.length" @click="toggleAllExtractionRules(true)">全选</button>
            <button class="btn small" type="button" :disabled="!extractionRules.length" @click="toggleAllExtractionRules(false)">全不选</button>
            <button class="btn small" type="button" @click="showRulePickerDialog = false">完成</button>
          </div>
        </div>
        <div class="dialog-body">
          <label class="rule-row" v-for="rule in extractionRules" :key="`picker-${rule.id}`">
            <input type="checkbox" :value="rule.id" v-model="selectedExtractionRuleIds" />
            <div class="rule-text">
              <div class="rule-name">{{ rule.name }}</div>
              <div class="rule-desc" v-if="rule.description">{{ rule.description }}</div>
            </div>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import { extractMonthlyDataShowCsv, importMonthlyDataShowCsv, inspectMonthlyDataShowFile } from '../../daily_report_25_26/services/api'

const route = useRoute()
const projectKey = computed(() => String(route.params.projectKey || 'monthly_data_show'))
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '月报导入与查询', to: '/projects/monthly_data_show/pages' },
  { label: '月报导入工作台', to: null },
])

const fileInputRef = ref(null)
const selectedFile = ref(null)
const inspecting = ref(false)
const extracting = ref(false)
const importing = ref(false)
const errorMessage = ref('')
const extractMessage = ref('')
const importMessage = ref('')
const selectedCsvFile = ref(null)
const lastExtractedCsvFile = ref(null)
const showRuleDetailDialog = ref(false)
const showRulePickerDialog = ref(false)
const extractRuleDetails = ref(null)

const companies = ref([])
const fields = ref([])
const sourceColumns = ref([])
const selectedCompanies = ref([])
const selectedFields = ref([])
const selectedSourceColumns = ref([])
const extractionRules = ref([])
const selectedExtractionRuleIds = ref([])
const constantsEnabled = ref(true)
const constantRules = ref([])
const reportYearInput = ref(null)
const reportMonthInput = ref(null)

const reportMonthDatePreview = computed(() => {
  const year = Number(reportYearInput.value)
  const month = Number(reportMonthInput.value)
  if (!Number.isInteger(year) || !Number.isInteger(month)) return '—'
  if (year < 2000 || year > 2099 || month < 1 || month > 12) return '—'
  return `${year}-${String(month).padStart(2, '0')}-01`
})

function onFileChange(event) {
  const file = event?.target?.files?.[0] || null
  selectedFile.value = file
  errorMessage.value = ''
  companies.value = []
  fields.value = []
  selectedCompanies.value = []
  selectedFields.value = []
  sourceColumns.value = []
  selectedSourceColumns.value = []
  constantsEnabled.value = true
  constantRules.value = []
  extractionRules.value = []
  selectedExtractionRuleIds.value = []
  reportYearInput.value = null
  reportMonthInput.value = null
  lastExtractedCsvFile.value = null
  selectedCsvFile.value = null
  extractMessage.value = ''
  extractRuleDetails.value = null
  showRuleDetailDialog.value = false
  showRulePickerDialog.value = false
  importMessage.value = ''
}

function onCsvFileChange(event) {
  selectedCsvFile.value = event?.target?.files?.[0] || null
  errorMessage.value = ''
  importMessage.value = ''
}

function toggleAllCompanies(checked) {
  selectedCompanies.value = checked ? [...companies.value] : []
}

function toggleAllFields(checked) {
  selectedFields.value = checked ? [...fields.value] : []
}

function toggleAllSourceColumns(checked) {
  selectedSourceColumns.value = checked ? [...sourceColumns.value] : []
}

function toggleAllExtractionRules(checked) {
  selectedExtractionRuleIds.value = checked
    ? extractionRules.value.map((x) => String(x?.id || '')).filter(Boolean)
    : []
}

const selectedRuleSummaryText = computed(() => {
  if (!selectedExtractionRuleIds.value.length) return ''
  const picked = new Set(selectedExtractionRuleIds.value.map((x) => String(x)))
  return extractionRules.value
    .filter((rule) => picked.has(rule.id))
    .map((rule) => rule.name)
    .join('、')
})

async function inspectFile() {
  if (!selectedFile.value || inspecting.value) return
  inspecting.value = true
  errorMessage.value = ''
  try {
    const payload = await inspectMonthlyDataShowFile(projectKey.value, selectedFile.value)
    companies.value = Array.isArray(payload?.companies) ? payload.companies : []
    fields.value = Array.isArray(payload?.fields) ? payload.fields : []
    sourceColumns.value = Array.isArray(payload?.source_columns) ? payload.source_columns : []
    selectedCompanies.value = [...companies.value]
    selectedFields.value = Array.isArray(payload?.default_selected_fields) && payload.default_selected_fields.length
      ? payload.default_selected_fields.filter((field) => fields.value.includes(field))
      : [...fields.value]
    selectedSourceColumns.value = Array.isArray(payload?.default_selected_source_columns) && payload.default_selected_source_columns.length
      ? payload.default_selected_source_columns.filter((col) => sourceColumns.value.includes(col))
      : [...sourceColumns.value]
    constantsEnabled.value = payload?.constants_enabled_default === undefined
      ? true
      : Boolean(payload?.constants_enabled_default)
    const defaultSourceCols = Array.isArray(payload?.default_selected_source_columns) && payload.default_selected_source_columns.length
      ? payload.default_selected_source_columns.filter((col) => sourceColumns.value.includes(col))
      : [...sourceColumns.value]
    constantRules.value = Array.isArray(payload?.constant_rules)
      ? payload.constant_rules.map((rule) => ({
        company: String(rule?.company || ''),
        item: String(rule?.item || ''),
        unit: String(rule?.unit || ''),
        value: Number(rule?.value ?? 0),
        source_columns: [...defaultSourceCols],
      }))
      : []
    extractionRules.value = Array.isArray(payload?.extraction_rules)
      ? payload.extraction_rules.map((rule) => ({
        id: String(rule?.id || ''),
        name: String(rule?.name || ''),
        description: String(rule?.description || ''),
      })).filter((rule) => rule.id && rule.name)
      : []
    selectedExtractionRuleIds.value = extractionRules.value.map((rule) => rule.id)
    reportYearInput.value = Number.isInteger(payload?.inferred_report_year)
      ? payload.inferred_report_year
      : null
    reportMonthInput.value = Number.isInteger(payload?.inferred_report_month)
      ? payload.inferred_report_month
      : null
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '读取可选项失败'
  } finally {
    inspecting.value = false
  }
}

async function extractCsv() {
  if (!selectedFile.value || extracting.value) return
  extracting.value = true
  errorMessage.value = ''
  extractMessage.value = ''
  extractRuleDetails.value = null
  showRuleDetailDialog.value = false
  showRulePickerDialog.value = false
  try {
    const reportYear = Number(reportYearInput.value)
    const reportMonth = Number(reportMonthInput.value)
    if (!Number.isInteger(reportYear) || reportYear < 2000 || reportYear > 2099) {
      errorMessage.value = '请填写有效年份（2000-2099）'
      return
    }
    if (!Number.isInteger(reportMonth) || reportMonth < 1 || reportMonth > 12) {
      errorMessage.value = '请填写有效月份（1-12）'
      return
    }
    const constantSourceColumns = constantsEnabled.value
      ? constantRules.value.flatMap((rule) => (Array.isArray(rule?.source_columns) ? rule.source_columns : []))
      : []
    const effectiveSourceColumns = Array.from(new Set([...selectedSourceColumns.value, ...constantSourceColumns]))
    const { blob, filename, stats } = await extractMonthlyDataShowCsv(
      projectKey.value,
      selectedFile.value,
      selectedCompanies.value,
      selectedFields.value,
      effectiveSourceColumns,
      selectedExtractionRuleIds.value,
      reportYear,
      reportMonth,
      constantsEnabled.value,
      constantRules.value,
    )
    const cachedFile = new File([blob], filename || 'monthly_data_show_extract.csv', { type: 'text/csv' })
    lastExtractedCsvFile.value = cachedFile
    selectedCsvFile.value = cachedFile
    const semiCount = Number(stats?.semiCalculatedCompleted || 0)
    const jinpuCount = Number(stats?.jinpuHeatingAreaAdjusted || 0)
    const totalRows = Number(stats?.extractedTotalRows || 0)
    extractRuleDetails.value = stats?.ruleDetails || null
    extractMessage.value = `提取完成：${cachedFile.name}（可下载或一键入库）｜补齐规则命中 ${semiCount} 条｜金普面积扣减 ${jinpuCount} 条｜提取总行数 ${totalRows} 条`
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '提取 CSV 失败'
  } finally {
    extracting.value = false
  }
}

const extractRuleDetailLines = computed(() => {
  const details = extractRuleDetails.value
  if (!details || typeof details !== 'object') return []
  const lines = []
  const semiDetailMap = details.semi_calculated_details && typeof details.semi_calculated_details === 'object'
    ? details.semi_calculated_details
    : {}
  const selectedRuleSet = new Set(Array.isArray(details.selected_rule_ids) ? details.selected_rule_ids.map((x) => String(x || '')) : [])
  lines.push(`半计算补齐总命中：${Number(details.semi_calculated_completed || 0)} 条`)
  lines.push(`指标剔除命中：${Number(details.item_exclude_hits || 0)} 条`)
  lines.push(`指标重命名命中：${Number(details.item_rename_hits || 0)} 条`)
  for (const [name, count] of Object.entries(semiDetailMap)) {
    lines.push(`${name}：${Number(count || 0)} 条`)
  }
  lines.push(`金普面积扣减命中：${Number(details.jinpu_heating_area_adjusted || 0)} 条`)
  lines.push(`常量注入命中：${Number(details.constants_injected || 0)} 条`)
  lines.push(`提取总行数：${Number(details.extracted_total_rows || 0)} 条`)
  if (extractionRules.value.length) {
    const selectedNames = extractionRules.value
      .filter((rule) => selectedRuleSet.has(rule.id))
      .map((rule) => rule.name)
    lines.push(`本次选中规则：${selectedNames.join('、') || '无'}`)
  }
  return lines
})

function downloadExtractedCsv() {
  if (!lastExtractedCsvFile.value) return
  const url = URL.createObjectURL(lastExtractedCsvFile.value)
  const link = document.createElement('a')
  link.href = url
  link.download = lastExtractedCsvFile.value.name || 'monthly_data_show_extract.csv'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

async function importCsvToDatabase() {
  if (!selectedCsvFile.value || importing.value) return
  importing.value = true
  errorMessage.value = ''
  importMessage.value = ''
  try {
    const result = await importMonthlyDataShowCsv(projectKey.value, selectedCsvFile.value)
    const importedRows = Number(result?.imported_rows || 0)
    const nullValueRows = Number(result?.null_value_rows || 0)
    const insertedRows = Number(result?.inserted_rows || 0)
    const updatedRows = Number(result?.updated_rows || 0)
    importMessage.value = `入库成功：共处理 ${importedRows} 条（新增 ${insertedRows} 条，更新 ${updatedRows} 条，空值入库 ${nullValueRows} 条）`
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : 'CSV 入库失败'
  } finally {
    importing.value = false
  }
}

async function importLastExtractedCsv() {
  if (!lastExtractedCsvFile.value || importing.value) return
  selectedCsvFile.value = lastExtractedCsvFile.value
  await importCsvToDatabase()
}

function toggleRuleSourceColumn(index, column, checked) {
  const rule = constantRules.value[index]
  if (!rule) return
  const next = Array.isArray(rule.source_columns) ? [...rule.source_columns] : []
  if (checked) {
    if (!next.includes(column)) next.push(column)
  } else {
    const pos = next.indexOf(column)
    if (pos >= 0) next.splice(pos, 1)
  }
  rule.source_columns = next
}

watch(
  selectedSourceColumns,
  (newCols, oldCols) => {
    const nextSet = new Set(newCols || [])
    const prevSet = new Set(oldCols || [])
    const added = [...nextSet].filter((col) => !prevSet.has(col))
    const removed = [...prevSet].filter((col) => !nextSet.has(col))
    if (!added.length && !removed.length) return
    for (const rule of constantRules.value) {
      const current = Array.isArray(rule.source_columns) ? [...rule.source_columns] : []
      const currentSet = new Set(current)
      for (const col of removed) {
        currentSet.delete(col)
      }
      for (const col of added) {
        currentSet.add(col)
      }
      rule.source_columns = sourceColumns.value.filter((col) => currentSet.has(col))
    }
  },
  { deep: true },
)
</script>

<style scoped>
.monthly-show-page {
  min-height: 100vh;
  background: #f8fafc;
}

.monthly-show-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 18px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.topbar h2 {
  margin: 0;
}

.sub {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
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

.panel {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px;
  margin-top: 10px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.panel-head h4 {
  margin: 0;
  font-size: 14px;
}

.month-config-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.month-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 6px;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 6px 10px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.table-wrap {
  overflow-x: auto;
}

.constant-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.constant-table th,
.constant-table td {
  border: 1px solid #dbeafe;
  padding: 6px 8px;
  text-align: left;
}

.num-input {
  width: 120px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px 6px;
}

.inline-checks {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.check-item.compact {
  font-size: 12px;
}

.hint {
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
}

.error {
  margin-top: 8px;
  color: #b91c1c;
  font-size: 13px;
}

.btn {
  border: 1px solid #94a3b8;
  border-radius: 8px;
  background: #fff;
  color: #0f172a;
  font-size: 13px;
  padding: 6px 10px;
  cursor: pointer;
}

.btn.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.btn.small {
  padding: 4px 8px;
  font-size: 12px;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 1100;
}

.dialog-card {
  width: min(720px, 96vw);
  max-height: 78vh;
  overflow: auto;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 12px;
}

.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.dialog-head h4 {
  margin: 0;
  font-size: 15px;
}

.dialog-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rule-line {
  font-size: 13px;
  color: #1e293b;
}

.rule-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 10px;
  background: #f8fafc;
}

.rule-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rule-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.rule-desc {
  font-size: 12px;
  color: #475569;
}
</style>
