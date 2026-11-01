<template>
  <section class="monthly-coal-card" aria-label="各单位标煤消耗量及计划完成情况">
    <header class="monthly-coal-header">
      <p><strong>{{ isSeason ? '全期计划完成率' : '月计划完成率' }}</strong> <span>{{ scopeLabel }} · 截至 {{ bizDate }} · 累计实际 / 计划（吨标煤）</span></p>
      <button type="button" :disabled="loading" @click="load">刷新</button>
    </header>
    <div v-if="loading" class="monthly-coal-message" role="status">正在读取完成率…</div>
    <div v-else-if="error" class="monthly-coal-message error" role="alert">{{ error }} <button type="button" @click="load">重试</button></div>
    <div v-else class="completion-badges" aria-label="各单位计划完成率">
      <span v-for="row in displayRows" :key="row.name" class="completion-badge" :style="completionStyle(row.completion_percent)" :title="completionDetail(row)" :aria-label="completionDetail(row)" tabindex="0">
        <span class="completion-badge-top">
          <span>{{ row.name }}</span>
          <strong>{{ row.completion_percent == null ? '—' : row.completion_percent.toFixed(0) + '%' }}</strong>
        </span>
        <span class="completion-values">{{ number(row.actual_value) }} / {{ number(row.plan_value) }}</span>
      </span>
    </div>
    <slot />
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { fetchMonthlyCoalProgress } from '../services/api'

const props = defineProps({
  projectKey: { type: String, required: true }, bizDate: { type: String, required: true },
  phase: { type: String, default: 'daily' },
  comparisonRows: { type: Array, default: () => [] },
})
const emit = defineEmits(['loading'])
const loading = ref(false), data = ref(null), error = ref('')
let requestId = 0, controller, disposed = false
const monthLabel = computed(() => props.bizDate ? `${props.bizDate.slice(0, 4)}年${Number(props.bizDate.slice(5, 7))}月` : '—')
const isSeason = computed(() => props.phase === 'seasonal')
const scopeLabel = computed(() => isSeason.value ? `${data.value?.season?.period || '—'}供暖期` : monthLabel.value)
// 使用明确别名对齐原对比表与接口主体，禁止按下标关联，避免集团/主城区错配。
const aliases = { 集团汇总: 'Group', 集团: 'Group', 集团全口径: 'Group', 主城区: 'ZhuChengQu', 北海: 'BeiHai', 北海热电: 'BeiHai', 北海热电厂: 'BeiHai', 香海: 'XiangHai', 香海热电: 'XiangHai', 香海热电厂: 'XiangHai', 供热公司: 'GongRe', 金州热电: 'JinZhou', 北方热电: 'BeiFang', 金普热电: 'JinPu', 庄河环海: 'ZhuangHe', 研究院: 'YanJiuYuan' }
const displayRows = computed(() => {
  const items = (isSeason.value ? data.value?.season?.items : data.value?.items) || []
  return (props.comparisonRows || []).map(([name, ...comparison]) => {
    const code = aliases[name] || name
    const plan = items.find(row => row.company === code || row.company_cn === name)
    return { ...plan, name, comparison, status: plan?.status || 'missing_plan' }
  })
})
// 展示取整，百分比计算与渐变配色仍使用接口返回的原始精度。
const number = value => value === null || value === undefined ? '—' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
const statusLabel = status => ({ missing_plan: '未配置有效计划', zero_plan: '计划为0', missing_actual: '暂无实际', incomplete_actual: '实际数据不完整' }[status] || '待核对')
// 连续插值提示静态计划消耗比例，不代表与时间进度比较；只限制色阶，不限制真实百分比。
const completionStyle = percent => {
  if (typeof percent !== 'number' || !Number.isFinite(percent)) return {}
  const stops = [[0, [71, 119, 155]], [60, [29, 78, 216]], [90, [180, 83, 9]], [100, [194, 65, 12]], [120, [185, 28, 28]]]
  const value = Math.max(0, Math.min(120, percent))
  const index = stops.findIndex((stop, i) => i > 0 && value <= stop[0])
  const [from, to] = [stops[index - 1], stops[index]]
  const ratio = (value - from[0]) / (to[0] - from[0])
  const color = from[1].map((channel, i) => Math.round(channel + (to[1][i] - channel) * ratio))
  const tint = amount => `rgb(${color.map(channel => Math.round(channel + (255 - channel) * amount)).join(', ')})`
  return {
    '--completion-color': `rgb(${color.join(', ')})`,
    '--completion-bg-start': tint(0.95), '--completion-bg-end': tint(0.87),
    '--completion-border': tint(0.76),
  }
}
// 图旁直接显示累计实际/计划与完成率，悬停补充口径及缺数原因。
const completionDetail = row => {
  const scope = isSeason.value ? '供暖期' : '本月'
  const status = row.completion_percent == null ? (isSeason.value && row.status === 'missing_plan' ? '全期计划不完整' : statusLabel(row.status)) : `完成率 ${row.completion_percent.toFixed(0)}%`
  return `${row.name}：${status}；${scope}截至业务日累计实际 ${number(row.actual_value)} ÷ ${isSeason.value ? '静态全期' : '静态全月'}计划 ${number(row.plan_value)}（吨标煤）`
}

async function load() {
  const id = ++requestId
  controller?.abort()
  controller = new AbortController()
  const signal = controller.signal
  data.value = null
  error.value = ''
  if (!props.bizDate) { loading.value = false; emit('loading', false); return }
  loading.value = true
  emit('loading', true)
  const targetDate = props.bizDate
  try {
    const result = await fetchMonthlyCoalProgress(props.projectKey, targetDate, signal)
    if (disposed || id !== requestId || signal.aborted) return
    if (!result?.ok || result.biz_date !== targetDate || !Array.isArray(result.items)) throw new Error(result?.message || '月度计划数据响应异常')
    data.value = result
  } catch (err) {
    if (!disposed && id === requestId && err.name !== 'AbortError') error.value = err.message || '月度标煤计划读取失败'
  } finally {
    if (!disposed && id === requestId) { loading.value = false; emit('loading', false) }
  }
}
watch(() => [props.projectKey, props.bizDate], load, { immediate: true })
onBeforeUnmount(() => { disposed = true; requestId++; controller?.abort(); emit('loading', false) })
</script>

<style scoped>
.monthly-coal-card { color: #334155; }
.monthly-coal-header { padding: 6px 0; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.monthly-coal-header p { margin: 0; font-size: 11px; color: #8494a7; }.monthly-coal-header strong { color: #526b82; margin-right: 8px; font-weight: 500; }
button { font: inherit; font-size: 11px; cursor: pointer; color: #64748b; border: 1px solid #dce5ef; border-radius: 5px; padding: 3px 7px; background: #fff; }button:disabled { opacity: .5; cursor: default; }
.completion-badges { display: flex; flex-wrap: nowrap; gap: 6px; padding: 2px 0 8px; overflow-x: auto; }
.completion-badge { display: flex; flex: 1 0 auto; flex-direction: column; min-width: 100px; gap: 5px; padding: 6px 8px; background: linear-gradient(110deg, var(--completion-bg-start, #f8fafc), var(--completion-bg-end, #f1f5f9)); border: 1px solid var(--completion-border, #e2e8f0); border-radius: 5px; font-size: 11px; color: #63788d; }
.completion-badge-top { display: flex; justify-content: space-between; align-items: baseline; gap: 6px; white-space: nowrap; }
.completion-values { text-align: center; font-variant-numeric: tabular-nums; white-space: nowrap; color: #52667b; }
.completion-badge strong { color: var(--completion-color, #94a3b8); font-size: 12px; font-variant-numeric: tabular-nums; }
.completion-badge:focus-visible { outline: 2px solid #3275b2; outline-offset: 2px; }
.monthly-coal-message { padding: 7px 0; font-size: 11px; color: #8494a7; }.monthly-coal-message.error { color: #b85d49; }
</style>
