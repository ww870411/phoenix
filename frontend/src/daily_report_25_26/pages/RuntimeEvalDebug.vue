<template>
  <div class="debug-container">
    <h2>运行时表达式求值 · 调试页</h2>
    <section class="form">
      <div class="row">
        <label>sheet_key</label>
        <input v-model="sheetKey" placeholder="如：BeiHai_co_generation_approval_Sheet" />
      </div>
      <div class="row">
        <label>company</label>
        <input v-model="company" placeholder="如：BeiHai" />
      </div>
      <div class="row">
        <label>config（可选）</label>
        <input v-model="configPath" placeholder="如：configs/字典样例.json（相对 data 目录）" />
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
import { ref } from 'vue'

const sheetKey = ref('BeiHai_co_generation_approval_Sheet')
const company = ref('BeiHai')
const configPath = ref('configs/字典样例.json')
const bizDateMode = ref('regular') // 'regular' | 'custom'
const bizDate = ref('')
const trace = ref(false)
const loading = ref(false)
const error = ref('')
const resp = ref(null)

function pretty(obj) {
  try { return JSON.stringify(obj, null, 2) } catch { return String(obj) }
}

async function runEval() {
  error.value = ''
  resp.value = null
  if (!sheetKey.value || !company.value) {
    error.value = 'sheet_key 与 company 为必填'
    return
  }
  loading.value = true
  try {
    const body = {
      sheet_key: sheetKey.value,
      project_key: 'daily_report_25_26',
      primary_key: { company: company.value },
      config: configPath.value || undefined,
      biz_date: bizDateMode.value === 'regular' ? 'regular' : (bizDate.value || undefined),
      trace: !!trace.value,
    }
    const res = await fetch('/api/v1/projects/daily_report_25_26/runtime/spec/eval', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const json = await res.json()
    if (!res.ok || json.ok === false) {
      throw new Error(json.message || `HTTP ${res.status}`)
    }
    resp.value = json
  } catch (e) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}
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
</style>

