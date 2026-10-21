<template>
  <button class="cache-manager-button" type="button" @click="open">缓存管理</button>
  <Teleport to="body">
    <div v-if="visible" class="cache-manager-mask" @click.self="close">
      <section class="cache-manager" role="dialog" aria-modal="true" aria-label="看板缓存管理" @keydown.esc="close">
        <header><h2>看板缓存管理</h2><button type="button" aria-label="关闭缓存管理" @click="close">关闭</button></header>
        <p>日期区间均包含开始日和结束日，可跨供暖期。缓存是看板计算结果的快照。</p>
        <div class="cache-inventory">
          <strong>已缓存 {{ dates.length }} 天</strong>
          <span>{{ disabled ? '当前已停用缓存，文件仍保留' : '缓存已启用' }}</span>
          <button type="button" :disabled="busy || loading" @click="reload">{{ loading ? '读取中…' : '刷新日期清单' }}</button>
          <p v-if="!dates.length">暂无缓存日期。</p>
          <ul v-else class="cache-ranges"><li v-for="range in ranges" :key="range.start">{{ range.start }}<template v-if="range.end !== range.start"> 至 {{ range.end }}</template>（{{ range.count }} 天）</li></ul>
          <details v-if="dates.length"><summary>查看全部已缓存日期</summary><div class="cache-date-grid"><span v-for="day in dates" :key="day">{{ day }}</span></div></details>
        </div>
        <section class="cache-operation">
          <h3>生成区间缓存</h3>
          <div class="cache-range-inputs">
            <label>生成开始日期<input v-model="publishStart" type="date" :disabled="busy || running" /></label>
            <span>至</span>
            <label>生成结束日期<input v-model="publishEnd" type="date" :disabled="busy || running" /></label>
            <button type="button" :disabled="busy || loading || running || !publishCount" @click="publish">生成缓存</button>
          </div>
          <p v-if="publishCount">共 {{ publishCount }} 天：新增 {{ publishCount - publishExisting }} 天，覆盖已有 {{ publishExisting }} 天；其他日期保留。</p>
          <p v-else>请选择有效的开始、结束日期。</p>
        </section>
        <section class="cache-operation">
          <h3>清除区间缓存</h3>
          <div class="cache-range-inputs">
            <label>清除开始日期<input v-model="deleteStart" type="date" :disabled="busy || running" @input="confirming = false" /></label>
            <span>至</span>
            <label>清除结束日期<input v-model="deleteEnd" type="date" :disabled="busy || running" @input="confirming = false" /></label>
            <button type="button" :disabled="busy || loading || running || !deleteValid" @click="previewDelete">预览清除</button>
          </div>
          <p v-if="deleteValid">区间内已有缓存 {{ deleteDates.length }} 天，区间外 {{ dates.length - deleteDates.length }} 天保留。</p>
          <div v-if="confirming" class="cache-delete-preview">
            <p v-if="deleteDates.length">将清除以下 {{ deleteDates.length }} 天的缓存文件；业务原始数据不受影响。</p>
            <p v-else>所选区间没有缓存，无需清除。</p>
            <div class="cache-date-grid"><span v-for="day in deleteDates" :key="day">{{ day }}</span></div>
            <button class="cache-danger" type="button" :disabled="busy || running || !deleteDates.length" @click="remove">确认清除 {{ deleteDates.length }} 天</button>
            <button type="button" :disabled="busy" @click="confirming = false">取消</button>
          </div>
        </section>
        <p v-if="running">缓存生成中：{{ job.processed || 0 }}/{{ job.total || 0 }} 天 · {{ job.current_label || job.currentLabel || '' }}<button type="button" :disabled="busy" @click="cancel">停止生成</button></p>
        <p v-else-if="job.status === 'failed'" role="alert">生成失败：{{ job.error || '请查看任务日志' }}；已完成日期保留，可重新生成剩余区间。</p>
        <p v-else-if="job.status === 'aborted'">生成已停止，已完成日期保留。</p>
        <p class="cache-manager-message" role="status">{{ message }}</p>
        <p v-if="error" class="cache-manager-error" role="alert">{{ error }}</p>
        <footer>查看未缓存日期时实时计算，不会自动写入缓存。可分次生成多个区间，清除后也可重新生成。</footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { cancelCachePublishJob, deleteDashboardCacheRange, getDashboardCacheInventory, publishDashboardCache } from '../services/api'

const props = defineProps({ projectKey: { type: String, required: true } })
const emit = defineEmits(['started', 'changed'])
const visible = ref(false)
const dates = ref([])
const disabled = ref(false)
const job = ref({})
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const message = ref('')
const publishStart = ref('')
const publishEnd = ref('')
const deleteStart = ref('')
const deleteEnd = ref('')
const confirming = ref(false)
let timer
let disposed = false
const running = computed(() => job.value.status === 'running')
// 使用 UTC 日期差，避免时区或夏令时造成天数错位。
const dayNumber = (value) => Date.parse(`${value}T00:00:00Z`) / 86400000
const validRange = (start, end) => !!start && !!end && Number.isFinite(dayNumber(start)) && Number.isFinite(dayNumber(end)) && start <= end
const publishCount = computed(() => validRange(publishStart.value, publishEnd.value) ? dayNumber(publishEnd.value) - dayNumber(publishStart.value) + 1 : 0)
const publishExisting = computed(() => dates.value.filter(day => day >= publishStart.value && day <= publishEnd.value).length)
const deleteValid = computed(() => validRange(deleteStart.value, deleteEnd.value))
const deleteDates = computed(() => deleteValid.value ? dates.value.filter(day => day >= deleteStart.value && day <= deleteEnd.value) : [])
const ranges = computed(() => {
  const result = []
  for (const day of dates.value) {
    const last = result[result.length - 1]
    if (last && dayNumber(day) - dayNumber(last.end) === 1) { last.end = day; last.count += 1 }
    else result.push({ start: day, end: day, count: 1 })
  }
  return result
})

function scheduleReload() {
  clearTimeout(timer)
  if (visible.value && running.value && !disposed) timer = setTimeout(() => reload(), 3000)
}
async function reload() {
  if (loading.value || disposed) return false
  loading.value = true
  error.value = ''
  try {
    const payload = await getDashboardCacheInventory(props.projectKey)
    const wasRunning = running.value
    dates.value = payload.available_dates || []
    disabled.value = !!payload.disabled
    job.value = payload.job || {}
    if (!publishStart.value) publishStart.value = payload.default_range?.start_date || ''
    if (!publishEnd.value) publishEnd.value = payload.default_range?.end_date || ''
    if (wasRunning && !running.value) { message.value = '任务已结束，缓存日期清单已更新'; emit('changed') }
    return true
  } catch (err) { error.value = err.message || String(err); return false }
  finally { loading.value = false; scheduleReload() }
}
async function open() { visible.value = true; error.value = ''; await reload() }
function close() { if (!busy.value) { visible.value = false; clearTimeout(timer) } }
async function publish() {
  if (!publishCount.value || busy.value || running.value) return
  busy.value = true; error.value = ''; confirming.value = false
  try {
    const result = await publishDashboardCache(props.projectKey, { startDate: publishStart.value, endDate: publishEnd.value })
    job.value = result.job || {}
    message.value = result.started ? `已启动 ${publishStart.value} 至 ${publishEnd.value} 的缓存生成` : '已有生成任务运行中，请等待或停止后再操作'
    emit('started', result.job)
    await reload()
  } catch (err) { error.value = err.message || String(err) }
  finally { busy.value = false; scheduleReload() }
}
async function previewDelete() {
  error.value = ''; confirming.value = false
  if (await reload()) confirming.value = !running.value
}
async function remove() {
  if (!confirming.value || busy.value || running.value || !deleteDates.value.length) return
  busy.value = true; error.value = ''
  try {
    const result = await deleteDashboardCacheRange(props.projectKey, { startDate: deleteStart.value, endDate: deleteEnd.value })
    dates.value = result.available_dates || []
    message.value = `已清除 ${result.deleted_count} 天缓存，保留 ${dates.value.length} 天`
    confirming.value = false
    emit('changed')
  } catch (err) { error.value = err.message || String(err) }
  finally { busy.value = false }
}
async function cancel() {
  busy.value = true; error.value = ''
  try { await cancelCachePublishJob(props.projectKey); message.value = '已请求停止，正在等待任务结束'; await reload() }
  catch (err) { error.value = err.message || String(err) }
  finally { busy.value = false }
}
onBeforeUnmount(() => { disposed = true; clearTimeout(timer) })
</script>

<style scoped>
.cache-manager-button,.cache-manager button{padding:7px 12px;border:1px solid #a8b7ca;border-radius:6px;background:#fff;color:#1e3a5f;cursor:pointer;font:inherit}
.cache-manager button:disabled{opacity:.5;cursor:not-allowed}
.cache-manager-mask{position:fixed;inset:0;z-index:10000;background:#14283d99;display:flex;align-items:center;justify-content:center;padding:20px;color:#243449;text-align:left;font:14px/1.6 system-ui,sans-serif}
.cache-manager{width:880px;max-width:100%;max-height:90vh;overflow:auto;background:#fff;border-radius:14px;padding:24px;box-shadow:0 20px 80px #0004}
.cache-manager header{display:flex;align-items:center;justify-content:space-between;gap:20px}
.cache-manager h2{font-size:21px;margin:0}.cache-manager h3{font-size:16px;margin:0 0 12px}.cache-manager p{margin:10px 0}
.cache-inventory{background:#eff5fb;border:1px solid #d3e1ee;padding:15px;border-radius:8px}.cache-inventory>span{margin:0 15px}
.cache-ranges{max-height:140px;overflow:auto;padding-left:22px;margin:10px 0}.cache-date-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(105px,1fr));gap:5px;max-height:180px;overflow:auto;margin:10px 0}.cache-date-grid span{background:#e7edf3;border-radius:4px;text-align:center;padding:3px}
.cache-operation{padding:18px 0;border-bottom:1px solid #dce4ec}.cache-range-inputs{display:flex;gap:12px;align-items:end;flex-wrap:wrap}.cache-range-inputs label{display:flex;flex-direction:column;gap:5px}.cache-range-inputs input{padding:7px;border:1px solid #a8b7ca;border-radius:5px;color:#243449;background:#fff;font:inherit}
.cache-delete-preview{padding:12px;background:#fff3ed;border-radius:7px;margin-top:12px}.cache-manager .cache-danger{background:#b83a31;color:white;border-color:#b83a31;margin-right:10px}.cache-manager-error{color:#b42318}.cache-manager-message{color:#176b43}.cache-manager footer{margin-top:16px;font-size:12px;color:#53667a}.cache-manager summary{cursor:pointer}
@media(max-width:600px){.cache-manager-mask{padding:8px}.cache-manager{padding:16px}.cache-inventory>span{display:block;margin:8px 0}}
</style>
