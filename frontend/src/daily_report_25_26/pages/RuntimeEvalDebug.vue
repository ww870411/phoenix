<template>
  <div class="debug-container">
    <h2>运行时表达式求值 · 调试页</h2>
    <section class="form">
      <div class="row">
        <label>选择字典</label>
        <select v-model="sheetKey">
          <option v-for="opt in sheetOptions" :key="opt.key" :value="opt.key">
            {{ opt.label }}
          </option>
        </select>
        <button class="btn" @click="loadSheets" :disabled="loading">刷新</button>
        <span class="hint">来源：{{ defaultConfigPath }}</span>
      </div>
      <div class="row">
        <label>company</label>
        <input v-model="company" placeholder="如：BeiHai" />
      </div>
      <div class="row">
        <label>biz_date</label>
        <select v-model="bizDateMode">
          <option value="regular">regular（默认，取物化视图）</option>
          <option value="custom">自定义日期</option>
        </select>
        <input v-if="bizDateMode==='custom'" v-model="bizDate" type="date" />
      </div>
      <div class="row">
        <label>trace</label>
        <input type="checkbox" v-model="trace" />
      </div>
      <div class="row">
        <button @click="runEval" :disabled="loading">请求 → /runtime/spec/eval</button>
      </div>
      <div class="row" v-if="error">
        <span class="error">错误：{{ error }}</span>
      </div>
    </section>

    <section v-if="resp" class="result">
      <h3>结果</h3>
      <div class="meta">
        <div>sheet_key：{{ resp.sheet_key }}</div>
        <div>sheet_name：{{ resp.sheet_name }}</div>
        <div>unit_id：{{ resp.unit_id }}</div>
        <div>unit_name：{{ resp.unit_name }}</div>
      </div>
      <div class="table-wrap" v-if="Array.isArray(resp.columns) && Array.isArray(resp.rows)">
        <table>
          <thead>
            <tr>
              <th v-for="(c,i) in resp.columns" :key="'c'+i">{{ c }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(r,ri) in resp.rows" :key="'r'+ri">
              <td v-for="(cell,ci) in (Array.isArray(r)?r:[])" :key="'cell'+ri+'-'+ci">
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <details v-if="trace && resp.debug" class="debug">
        <summary>查看 _trace</summary>
        <pre>{{ pretty(resp.debug) }}</pre>
      </details>
    </section>
  </div>
  </template>

<script setup>
import { ref, onMounted } from 'vue'

const sheetKey = ref('')
const company = ref('')
const defaultConfigPath = 'configs/字典样例.json'
const bizDateMode = ref('regular') // 'regular' | 'custom'
const bizDate = ref('')
const trace = ref(false)
const loading = ref(false)
const error = ref('')
const resp = ref(null)
const API_BASE = import.meta.env?.VITE_API_BASE || ''
const sheetOptions = ref([])

function pretty(obj) {
  try { return JSON.stringify(obj, null, 2) } catch { return String(obj) }
}

async function loadSheets() {
  error.value = ''
  try {
    const url = `${API_BASE}/api/v1/projects/daily_report_25_26/data_entry/sheets?config=${encodeURIComponent(defaultConfigPath)}`
    const res = await fetch(url)
    if (!res.ok) throw new Error(`加载字典列表失败: ${res.status}`)
    const data = await res.json()
    // data 是 { [sheet_key]: { unit_id, unit_name, sheet_name } }
    const entries = []
    for (const [key, meta] of Object.entries(data || {})) {
      const label = `${meta?.sheet_name || key} (${key})`
      entries.push({ key, label })
    }
    // 保持稳定顺序
    entries.sort((a, b) => a.label.localeCompare(b.label, 'zh-Hans-CN'))
    sheetOptions.value = entries
    if (!sheetKey.value && entries.length > 0) {
      sheetKey.value = entries[0].key
    }
  } catch (e) {
    error.value = e?.message || String(e)
  }
}

async function runEval() {
  error.value = ''
  resp.value = null
  loading.value = true
  try {
    const body = {
      sheet_key: sheetKey.value || undefined,
      project_key: 'daily_report_25_26',
      primary_key: company.value ? { company: company.value } : undefined,
      config: defaultConfigPath,
      biz_date: bizDateMode.value === 'regular' ? 'regular' : (bizDate.value || undefined),
      trace: !!trace.value,
    }
    const url = `${API_BASE}/api/v1/projects/daily_report_25_26/runtime/spec/eval`
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const ct = res.headers.get('content-type') || ''
    let payload
    if (ct.includes('application/json')) {
      payload = await res.json()
    } else {
      const text = await res.text()
      throw new Error(text || `HTTP ${res.status}`)
    }
    if (!res.ok || payload.ok === false) {
      throw new Error(payload.message || `HTTP ${res.status}`)
    }
    resp.value = payload
  } catch (e) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSheets()
})
</script>

<style scoped>
.debug-container { padding: 16px; }
.form { margin-bottom: 12px; }
.row { display: flex; align-items: center; gap: 8px; margin: 6px 0; }
label { width: 100px; color: #555; }
input[type="text"], input[type="date"], input:not([type]) { flex: 1; padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; }
button { padding: 6px 12px; }
.error { color: #c00; }
.meta { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; margin: 8px 0; }
.table-wrap { overflow: auto; border: 1px solid #ddd; border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { border: 1px solid #eee; padding: 6px 8px; white-space: nowrap; }
th { background: #f9f9f9; position: sticky; top: 0; }
.debug pre { background: #f6f8fa; padding: 8px; border-radius: 6px; overflow: auto; }
.hint { color: #888; font-size: 12px; }
</style>
