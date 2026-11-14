<template>
  <div class="weather-module-panel">
    <!-- 1. 运行状态与最近成功/失败记录 -->
    <section class="card elevated section-card">
      <div class="card-header-row">
        <div>
          <div class="card-header">{{ title }}</div>
          <p class="sub block-sub">{{ subtitle }}</p>
        </div>
        <div class="section-actions weather-header-actions">
          <button
            class="btn ghost compact-btn"
            type="button"
            :disabled="loadingAuto || runningNow"
            @click="loadAutoStatus"
          >
            {{ loadingAuto ? '刷新中…' : '🔄 刷新状态' }}
          </button>
          <button
            class="btn primary compact-btn"
            type="button"
            :disabled="runningNow || loadingAuto"
            @click="handleRunNow"
          >
            {{ runningNow ? '⏳ 正在获取并入库…' : '⚡ 立即尝试获取并入库' }}
          </button>
        </div>
      </div>

      <div class="weather-status-bar">
        <span
          :class="[
            'weather-status-pill',
            autoStatus.is_running || runningNow
              ? 'is-running'
              : autoStatus.enabled
                ? 'is-enabled'
                : 'is-paused',
          ]"
        >
          <span class="weather-status-dot"></span>
          {{
            autoStatus.is_running || runningNow
              ? '正在执行气温获取与入库…'
              : autoStatus.enabled
                ? '自动定时获取：已开启'
                : '自动定时获取：已暂停'
          }}
        </span>
        <span class="weather-next-run-chip">
          ⏰ 下次计划尝试：
          <strong>
            {{
              !autoStatus.enabled
                ? '已暂停自动获取'
                : autoStatus.next_run_time || '未设置定时时间点'
            }}
          </strong>
        </span>
      </div>

      <div v-if="runTip" :class="['page-tip', runTip.type]" role="status">
        {{ runTip.text }}
      </div>

      <!-- 成功 / 失败 / 最近尝试 概览卡片 -->
      <div class="weather-metrics-grid">
        <div class="weather-metric-card is-success">
          <div class="weather-metric-label">✅ 上次成功导入时间</div>
          <div class="weather-metric-time">
            {{ autoStatus.last_success_time || '暂无成功记录' }}
          </div>
          <div v-if="autoStatus.last_success_time" class="weather-metric-meta">
            <span class="weather-trigger-tag">{{ autoStatus.last_success_trigger || '—' }}</span>
            <span class="weather-age-text">{{ formatWeatherTimeAgo(autoStatus.last_success_time) }}</span>
          </div>
          <p class="weather-metric-desc">
            {{ autoStatus.last_success_message || '尚未完成过数据入库' }}
          </p>
        </div>

        <div class="weather-metric-card is-failure">
          <div class="weather-metric-label">❌ 上次失败时间</div>
          <div class="weather-metric-time">
            {{ autoStatus.last_failure_time || '暂无失败记录' }}
          </div>
          <div v-if="autoStatus.last_failure_time" class="weather-metric-meta">
            <span class="weather-trigger-tag">{{ autoStatus.last_failure_trigger || '—' }}</span>
            <span class="weather-age-text">{{ formatWeatherTimeAgo(autoStatus.last_failure_time) }}</span>
          </div>
          <p class="weather-metric-desc">
            {{ autoStatus.last_failure_message || '最近运行未出现连接或入库异常' }}
          </p>
        </div>

        <div class="weather-metric-card is-latest">
          <div class="weather-metric-label">📡 最近一次尝试状态</div>
          <div class="weather-metric-time">
            <span
              :class="[
                'weather-result-badge',
                autoStatus.last_attempt_status === 'SUCCESS'
                  ? 'badge-ok'
                  : autoStatus.last_attempt_status === 'FAILED'
                    ? 'badge-err'
                    : 'badge-idle',
              ]"
            >
              {{ formatWeatherStatusLabel(autoStatus.last_attempt_status) }}
            </span>
            <span v-if="autoStatus.last_attempt_time" class="weather-latest-at">
              {{ autoStatus.last_attempt_time }}
            </span>
          </div>
          <div v-if="autoStatus.last_attempt_trigger" class="weather-metric-meta">
            <span class="weather-trigger-tag">{{ autoStatus.last_attempt_trigger }}</span>
          </div>
          <p class="weather-metric-desc">
            {{ autoStatus.last_attempt_message || '等待首次执行' }}
          </p>
        </div>
      </div>
    </section>

    <!-- 2. 自动获取时间设置（支持多个时间） -->
    <section class="card elevated section-card">
      <div class="card-header-row">
        <div>
          <div class="card-header">⏰ 自动获取时间设置（支持多时段尝试）</div>
          <p class="sub block-sub">
            {{ scheduleHint }}
          </p>
        </div>
        <div class="section-actions">
          <button
            class="btn primary"
            type="button"
            :disabled="savingAuto || loadingAuto"
            @click="saveAutoConfig"
          >
            {{ savingAuto ? '保存中…' : '💾 保存自动获取设置' }}
          </button>
        </div>
      </div>

      <div class="weather-schedule-controls">
        <label class="weather-switch-row">
          <input v-model="autoImportEnabled" type="checkbox" class="weather-switch-input" />
          <span class="weather-switch-label">
            启用每日自动定时获取与入库
            <small>（关闭后仅暂停定时触发，不影响已保存的时间列表与页面手动导入）</small>
          </span>
        </label>

        <div class="weather-time-adder">
          <div class="weather-time-input-group">
            <input
              v-model="newScheduleTime"
              type="time"
              class="input weather-time-input"
              aria-label="新增自动获取时间"
            />
            <button class="btn ghost compact-btn" type="button" @click="addScheduleTime">
              ➕ 添加时间点
            </button>
          </div>
          <div class="weather-preset-actions">
            <button
              class="btn ghost compact-btn"
              type="button"
              @click="applyPresetScheduleTimes(['06:30', '12:00', '18:00'])"
            >
              ✨ 早中晚3次 (06:30 / 12:00 / 18:00)
            </button>
            <button
              class="btn ghost compact-btn"
              type="button"
              @click="applyPresetScheduleTimes(['02:00', '06:00', '10:00', '14:00', '18:00', '22:00'])"
            >
              🔁 每4小时一次 (共6次)
            </button>
            <button
              v-if="autoScheduleTimes.length > 0"
              class="btn ghost compact-btn weather-clear-btn"
              type="button"
              @click="clearScheduleTimes"
            >
              🗑️ 清空时间点
            </button>
          </div>
        </div>

        <div v-if="autoScheduleTimes.length === 0" class="weather-empty-slots">
          暂未设置自动获取时间点。请使用上方时间选择器添加至少一个时间点，然后点击“保存自动获取设置”。
        </div>
        <div v-else class="weather-slots-list">
          <div v-for="slot in autoScheduleTimes" :key="slot" class="weather-slot-chip">
            <span class="weather-slot-time">🕒 {{ slot }}</span>
            <span
              v-if="autoStatus.executed_slots_today && autoStatus.executed_slots_today[slot]"
              class="weather-slot-done-tag"
              :title="`今日执行状态：${autoStatus.executed_slots_today[slot]}`"
            >
              {{
                String(autoStatus.executed_slots_today[slot]).startsWith('跳过')
                  ? '今日跳过'
                  : '今日已尝试'
              }}
            </span>
            <button
              type="button"
              class="weather-slot-remove"
              :title="`移除时间点 ${slot}`"
              @click="removeScheduleTime(slot)"
            >
              ×
            </button>
          </div>
        </div>
      </div>

      <p v-if="autoTip" :class="['page-tip', autoTip.type]" role="status">
        {{ autoTip.text }}
      </p>
    </section>

    <!-- 3. API 数据源地址配置 -->
    <section class="card elevated section-card">
      <div class="card-header-row">
        <div>
          <div class="card-header">{{ apiTitle }}</div>
          <p class="sub block-sub">{{ apiSubtitle }}</p>
        </div>
      </div>
      <form class="weather-config-form" @submit.prevent="saveApiConfig">
        <label class="field">
          <span class="field-title">{{ apiFieldLabel }}</span>
          <textarea
            v-model.trim="apiUrl"
            class="input"
            rows="4"
            required
            :disabled="loadingApi || savingApi"
            placeholder="请输入完整的 HTTP / HTTPS API 地址（含查询参数）"
          ></textarea>
        </label>
        <p class="sub block-sub">{{ apiFormatHint }}</p>
        <div class="section-actions">
          <button class="btn primary" type="submit" :disabled="loadingApi || savingApi || !apiUrl">
            {{ savingApi ? '保存中…' : '保存 API 配置' }}
          </button>
          <button class="btn ghost" type="button" :disabled="loadingApi || savingApi" @click="loadApiConfig">
            {{ loadingApi ? '读取中…' : '重新读取' }}
          </button>
        </div>
        <p v-if="apiTip" :class="['page-tip', apiTip.type]" role="status">{{ apiTip.text }}</p>
      </form>
    </section>

    <!-- 4. 最近导入尝试记录明细 -->
    <section class="card elevated section-card">
      <div class="card-header-row">
        <div>
          <div class="card-header">📜 最近导入尝试记录（近 30 次）</div>
          <p class="sub block-sub">记录每次定时自动获取、管理中心手动触发以及业务页面手动导入的执行结果。</p>
        </div>
      </div>
      <div v-if="!historyRows.length" class="weather-empty-slots">
        暂无导入尝试历史记录。
      </div>
      <div v-else class="table-wrap">
        <table class="table editor-table weather-history-table">
          <thead>
            <tr>
              <th style="width: 175px;">尝试时间</th>
              <th style="width: 155px;">触发方式</th>
              <th style="width: 95px;">结果状态</th>
              <th>执行结果详情</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in historyRows" :key="`${item.time}-${idx}`">
              <td class="font-mono">{{ item.time }}</td>
              <td>
                <span class="weather-trigger-tag">{{ item.trigger_label || item.trigger || '—' }}</span>
              </td>
              <td>
                <span :class="['weather-result-badge', item.status === 'SUCCESS' ? 'badge-ok' : 'badge-err']">
                  {{ item.status === 'SUCCESS' ? '成功' : '失败' }}
                </span>
              </td>
              <td class="weather-history-msg">{{ item.message }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  projectKey: { type: String, required: true },
  title: { type: String, required: true },
  subtitle: { type: String, required: true },
  scheduleHint: { type: String, required: true },
  apiTitle: { type: String, required: true },
  apiSubtitle: { type: String, required: true },
  apiFieldLabel: { type: String, required: true },
  apiFormatHint: { type: String, required: true },
  defaultNewTime: { type: String, default: '08:00' },
  getApiConfigFn: { type: Function, required: true },
  saveApiConfigFn: { type: Function, required: true },
  getAutoStatusFn: { type: Function, required: true },
  saveAutoConfigFn: { type: Function, required: true },
  runImportNowFn: { type: Function, required: true },
})

const apiUrl = ref('')
const loadingApi = ref(false)
const savingApi = ref(false)
const apiTip = ref(null)

const autoStatus = ref({
  enabled: true,
  schedule_times: [],
  last_attempt_time: null,
  last_attempt_status: 'IDLE',
  last_attempt_trigger: null,
  last_attempt_message: '尚未执行过自动或手动导入',
  last_success_time: null,
  last_success_trigger: null,
  last_success_message: null,
  last_failure_time: null,
  last_failure_trigger: null,
  last_failure_message: null,
  next_run_time: null,
  executed_slots_today: {},
  history: [],
  is_running: false,
})
const autoImportEnabled = ref(true)
const autoScheduleTimes = ref([])
const newScheduleTime = ref(props.defaultNewTime)
const loadingAuto = ref(false)
const savingAuto = ref(false)
const runningNow = ref(false)
const autoTip = ref(null)
const runTip = ref(null)

const historyRows = computed(() => (
  Array.isArray(autoStatus.value?.history) ? autoStatus.value.history : []
))

function formatWeatherStatusLabel(status) {
  if (status === 'SUCCESS') return '成功'
  if (status === 'FAILED') return '失败'
  return '待执行'
}

function formatWeatherTimeAgo(timeStr) {
  if (!timeStr) return ''
  const isoText = String(timeStr).trim().replace(' ', 'T')
  const normalized = /[Zz]|[+-]\d{2}:\d{2}$/.test(isoText) ? isoText : `${isoText}+08:00`
  const ts = new Date(normalized).getTime()
  if (Number.isNaN(ts)) return ''
  const diff = Math.max(0, Math.floor((Date.now() - ts) / 1000))
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
}

function applyAutoStatusSnapshot(data) {
  if (!data || typeof data !== 'object') return
  autoStatus.value = {
    ...autoStatus.value,
    ...data,
  }
  autoImportEnabled.value = Boolean(data.enabled)
  autoScheduleTimes.value = Array.isArray(data.schedule_times) ? [...data.schedule_times] : []
}

async function loadApiConfig() {
  loadingApi.value = true
  apiTip.value = null
  try {
    const result = await props.getApiConfigFn(props.projectKey)
    apiUrl.value = result?.data?.api_url || ''
  } catch (err) {
    apiTip.value = { type: 'error', text: err.message }
  } finally {
    loadingApi.value = false
  }
}

async function saveApiConfig() {
  savingApi.value = true
  apiTip.value = null
  try {
    const result = await props.saveApiConfigFn(props.projectKey, apiUrl.value)
    apiUrl.value = result?.data?.api_url || apiUrl.value
    apiTip.value = { type: 'success', text: 'API 配置已保存，下次自动获取或手动导入时生效。' }
  } catch (err) {
    apiTip.value = { type: 'error', text: err.message }
  } finally {
    savingApi.value = false
  }
}

async function loadAutoStatus() {
  loadingAuto.value = true
  try {
    const result = await props.getAutoStatusFn(props.projectKey)
    applyAutoStatusSnapshot(result?.data)
  } catch (err) {
    autoTip.value = { type: 'error', text: err.message }
  } finally {
    loadingAuto.value = false
  }
}

function addScheduleTime() {
  autoTip.value = null
  const val = String(newScheduleTime.value || '').trim()
  if (!/^\d{2}:\d{2}$/.test(val)) {
    autoTip.value = { type: 'error', text: '请选择有效的 HH:MM 时间。' }
    return
  }
  if (autoScheduleTimes.value.includes(val)) {
    autoTip.value = { type: 'error', text: `时间点 ${val} 已存在，无需重复添加。` }
    return
  }
  autoScheduleTimes.value = [...autoScheduleTimes.value, val].sort()
}

function removeScheduleTime(slot) {
  autoScheduleTimes.value = autoScheduleTimes.value.filter((item) => item !== slot)
}

function applyPresetScheduleTimes(presets) {
  autoTip.value = null
  autoScheduleTimes.value = Array.from(new Set([...autoScheduleTimes.value, ...presets])).sort()
}

function clearScheduleTimes() {
  autoScheduleTimes.value = []
}

async function saveAutoConfig() {
  savingAuto.value = true
  autoTip.value = null
  try {
    const result = await props.saveAutoConfigFn(props.projectKey, {
      enabled: Boolean(autoImportEnabled.value),
      schedule_times: autoScheduleTimes.value,
    })
    applyAutoStatusSnapshot(result?.data)
    autoTip.value = {
      type: 'success',
      text: result?.message || '自动获取时间设置已保存并生效。',
    }
  } catch (err) {
    autoTip.value = { type: 'error', text: err.message }
  } finally {
    savingAuto.value = false
  }
}

async function handleRunNow() {
  if (runningNow.value) return
  runningNow.value = true
  runTip.value = null
  try {
    const result = await props.runImportNowFn(props.projectKey)
    if (result?.data) {
      applyAutoStatusSnapshot(result.data)
    }
    runTip.value = {
      type: result?.ok ? 'success' : 'error',
      text: result?.message || (result?.ok ? '气温获取并入库成功。' : '气温获取或入库失败。'),
    }
  } catch (err) {
    runTip.value = { type: 'error', text: err.message }
    await loadAutoStatus().catch(() => {})
  } finally {
    runningNow.value = false
  }
}

async function refresh() {
  await Promise.all([loadApiConfig(), loadAutoStatus()])
}

defineExpose({
  refresh,
  loadAutoStatus,
  loadApiConfig,
})

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.weather-module-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.section-card {
  border-radius: 14px;
  padding: 22px 24px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 6px 18px rgba(15, 23, 42, 0.03);
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.card-header {
  font-size: 16.5px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  line-height: 1.4;
}

.block-sub {
  margin: 5px 0 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.55;
}

.section-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.compact-btn {
  height: 34px;
  padding: 0 12px;
  font-size: 12.5px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.03);
}

.weather-history-table {
  margin: 0;
  font-size: 13px;
}

.weather-history-table thead th {
  background: #f4f7fb;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  border-bottom: 1px solid #dbe4ef;
}

.weather-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}

.weather-status-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  margin-bottom: 16px;
}

.weather-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 600;
}

.weather-status-pill.is-enabled {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.weather-status-pill.is-paused {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
}

.weather-status-pill.is-running {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.weather-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.weather-next-run-chip {
  font-size: 13px;
  color: #475569;
}

.weather-next-run-chip strong {
  color: #0f172a;
}

.weather-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px;
}

.weather-metric-card {
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.weather-metric-card.is-success {
  border-color: #bbf7d0;
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
}

.weather-metric-card.is-failure {
  border-color: #fecaca;
  background: linear-gradient(180deg, #fef2f2 0%, #ffffff 100%);
}

.weather-metric-card.is-latest {
  border-color: #bfdbfe;
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
}

.weather-metric-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.weather-metric-time {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 15.5px;
  font-weight: 700;
  color: #0f172a;
}

.weather-latest-at {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.weather-metric-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.weather-trigger-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #334155;
  font-size: 11.5px;
  font-weight: 600;
}

.weather-age-text {
  font-size: 12px;
  color: #64748b;
}

.weather-metric-desc {
  margin: 2px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: #475569;
  word-break: break-word;
}

.weather-result-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
}

.weather-result-badge.badge-ok {
  background: #dcfce7;
  color: #15803d;
}

.weather-result-badge.badge-err {
  background: #fee2e2;
  color: #b91c1c;
}

.weather-result-badge.badge-idle {
  background: #e2e8f0;
  color: #475569;
}

.weather-schedule-controls {
  display: grid;
  gap: 14px;
}

.weather-switch-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.weather-switch-row:hover {
  border-color: #cbd5e1;
}

.weather-switch-input {
  margin-top: 3px;
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #2563eb;
}

.weather-switch-label {
  font-size: 13.5px;
  font-weight: 600;
  color: #0f172a;
  line-height: 1.45;
}

.weather-switch-label small {
  display: inline-block;
  font-weight: 400;
  color: #64748b;
}

.weather-time-adder {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.weather-time-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weather-time-input {
  width: 136px;
  height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 10px;
  background: #ffffff;
  font-size: 13px;
  color: #0f172a;
}

.weather-preset-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.weather-clear-btn {
  color: #dc2626;
  border-color: #fecaca;
}

.weather-clear-btn:hover {
  background: #fef2f2;
  border-color: #fca5a5;
}

.weather-empty-slots {
  padding: 18px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  color: #64748b;
  font-size: 13px;
  text-align: center;
}

.weather-slots-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.weather-slot-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 11px;
  border-radius: 9px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
  font-size: 13px;
  font-weight: 600;
}

.weather-slot-done-tag {
  padding: 1px 7px;
  border-radius: 999px;
  background: #dcfce7;
  color: #166534;
  font-size: 11px;
  font-weight: 600;
}

.weather-slot-remove {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 0 2px;
}

.weather-slot-remove:hover {
  color: #dc2626;
}

.weather-config-form {
  display: grid;
  gap: 12px;
}

.weather-config-form .field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.field-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.weather-config-form textarea {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  overflow-wrap: anywhere;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 9px;
  background: #ffffff;
  color: #0f172a;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.5;
  outline: none;
}

.weather-config-form textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.weather-history-msg {
  word-break: break-word;
  line-height: 1.55;
}

.page-tip {
  margin: 12px 0 0;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
}

.page-tip.success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.page-tip.error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

@media (max-width: 768px) {
  .section-card {
    padding: 16px 14px;
    border-radius: 12px;
  }

  .card-header-row {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .weather-header-actions {
    width: 100%;
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .weather-time-adder {
    flex-direction: column;
    align-items: stretch;
  }

  .weather-time-input-group {
    width: 100%;
  }

  .weather-time-input {
    flex: 1;
  }
}
</style>
