<template>
  <section class="lifecycle-card" aria-label="主设备启停生命周期">
    <header class="lifecycle-header">
      <div><span class="eyebrow">运行轨迹 · OPERATION TIMELINE</span><h3>主设备启停生命周期</h3><p>一台设备一条轨迹，启停过程沿时间展开</p></div>
      <div class="view-badge">依据调度日报还原</div>
    </header>

    <form class="range-bar" @submit.prevent="loadRange">
      <label>开始日期<input v-model="startDate" type="date" required aria-label="生命周期开始日期" /></label>
      <span class="range-divider">至</span>
      <label>结束日期<input v-model="endDate" type="date" required aria-label="生命周期结束日期" /></label>
      <button class="primary" type="submit">{{ loading ? '读取中…' : '查看轨迹' }}</button>
      <button type="button" :disabled="!canExport || exporting" @click="exportGraph('png')">{{ exporting ? '导出中…' : '导出 PNG' }}</button>
      <button type="button" :disabled="!canExport || exporting" @click="exportGraph('svg')">导出 SVG</button>
      <div class="quick-ranges"><button v-for="days in [7, 30, 90]" :key="days" type="button" :title="'截至最新日报 ' + latestDate" @click="quickRange(days)">近{{ days }}天</button></div>
    </form>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="exportError" class="error" role="alert">{{ exportError }}</p>
    <p v-if="exportNotice" class="export-notice" role="status">{{ exportNotice }}</p>
    <p v-if="loadedRange && rangeChanged" class="export-notice">日期已修改，请先点击“查看轨迹”后再导出。</p>
    <div v-if="loading" class="loading" role="status">正在读取所选阶段的设备记录…</div>
    <template v-else-if="loadedRange">
      <div class="stat-strip">
        <div><strong>{{ model.reportDays }}<small> / {{ rangeDays }} 天</small></strong><span>有日报记录</span></div>
        <div><strong>{{ visibleDevices.length }}</strong><span>当前显示设备</span></div>
        <div><strong class="amber">{{ starts }}</strong><span>启动动作</span></div>
        <div><strong class="rose">{{ stops }}</strong><span>停止动作</span></div>
        <div><strong :class="pending ? 'amber' : ''">{{ pending }}</strong><span>待核对设备日</span></div>
        <div><strong>{{ totalRuntime.toFixed(2) }}</strong><span>推算运行 · 设备小时</span></div>
      </div>
      <fieldset class="subject-picker">
        <legend>主体（可多选）</legend>
        <label class="subject-option"><input type="checkbox" :checked="selectedSubjects === null" @change="selectedSubjects = $event.target.checked ? null : []" />全部主体</label>
        <label v-for="subject in subjectOptions" :key="subject" class="subject-option" :class="{ unavailable: !availableSubjects.includes(subject) }">
          <input type="checkbox" :checked="availableSubjects.includes(subject) && (selectedSubjects === null || selectedSubjects.includes(subject))" :disabled="!availableSubjects.includes(subject)" @change="toggleSubject(subject, $event.target.checked)" />{{ subject }}
        </label>
      </fieldset>
      <div class="filter-bar">
        <div class="filters">
          <select v-model="type" aria-label="生命周期设备类型"><option value="ALL">全部机炉</option><option value="汽机">汽机</option><option value="锅炉">锅炉</option></select>
          <label class="toggle"><input v-model="onlyActive" type="checkbox" />只看有操作或差异的设备</label>
        </div>
        <span class="loaded-range">{{ loadedRange.start }} — {{ loadedRange.end }}</span>
      </div>
      <div class="legend">
        <span v-for="(color, state) in STATE_COLORS" :key="state"><i :style="{ background: color }"></i>{{ state }}</span>
        <span class="node-key">▲ 启动　◆ 并入/投运　■ 停止</span><span class="conflict-key">虚线框：状态待确认</span>
      </div>

      <div v-if="!model.reportDays" class="empty">这个阶段没有调度日报。请选择其他日期范围。</div>
      <div v-else-if="!visibleDevices.length" class="empty">当前筛选下没有设备记录。请选择主体，或关闭“只看有操作或差异的设备”。</div>
      <div v-else class="timeline-layout">
        <div class="chart-panel">
          <div ref="dateAxisViewport" class="date-axis-viewport" :style="{ width: axisViewportWidth ? axisViewportWidth + 'px' : undefined }" role="img" aria-label="固定日期刻度，随主图同步滚动和缩放">
            <div class="date-axis-inner" :style="{ width: chartPixelWidth + 'px' }">
              <span v-for="tick in dateTicks" :key="tick.day" class="date-tick" :style="{ left: tick.left + 'px' }">{{ tick.label }}</span>
            </div>
          </div>
          <div ref="chartScroll" class="chart-scroll" @scroll="syncHorizontalScroll">
            <div class="chart-width">
              <div ref="chartElement" class="lifecycle-chart" :style="{ height: chartHeight + 'px' }" role="img" :aria-label="`设备时间轴，共${visibleDevices.length}台，操作节点${visibleEvents.length}个；下方可按设备查看文字详情`"></div>
            </div>
          </div>
          <p class="chart-hint">横轴按日显示；拖动底部滑块查看后续日期或缩放时间，点击色带或操作节点查看详情。</p>
        </div>
        <aside v-if="selectedDevice" class="device-detail">
          <div class="detail-heading"><span>设备详情</span><select v-model="selectedKey" aria-label="生命周期设备详情选择"><option v-for="device in visibleDevices" :key="device.key" :value="device.key">{{ lifecycleSubjectName(device.plant) }} · {{ device.name }}</option></select></div>
          <h4>{{ selectedDevice.name }} <small>{{ lifecycleSubjectName(selectedDevice.plant) }}</small></h4>
          <p class="detail-summary">{{ selectedDevice.snapshots.length }} 份日报 · {{ selectedDevice.events.length }} 条主设备操作</p>
          <div v-if="selectedRuntime" class="runtime-summary">
            <strong>{{ selectedRuntime.hours.toFixed(2) }} <small>小时 · 推算运行时长</small></strong>
            <p>操作计时 {{ selectedRuntime.actionHours.toFixed(2) }}h · 日报估算 {{ selectedRuntime.snapshotHours.toFixed(2) }}h</p>
            <p v-if="selectedRuntime.unknownHours">另有 {{ selectedRuntime.unknownHours.toFixed(2) }} 小时时长待核对，未计入合计。</p>
          </div>
          <div v-if="selectedDevice.conflicts.length" class="detail-warning">有 {{ selectedDevice.conflicts.length }} 个设备日存在待确认差异，色带暂按当前日报显示状态绘制。</div>
          <ol v-if="selectedDevice.events.length" class="event-list">
            <li v-for="event in selectedDevice.events" :key="event.id" :class="['event-item', event.kind, { selected: selectedEvent === event.id }]">
              <time>{{ event.day }} {{ event.timestamp === null ? '时间待核对' : event.time }}</time>
              <strong>{{ event.action }} <span :style="{ color: STATE_COLORS[event.status] }">{{ event.status }}</span></strong>
              <p>{{ event.sourceDescription }}</p><small>来源：{{ event.fileName || '调度日报' }}</small>
            </li>
          </ol>
          <p v-else class="no-events">所选阶段仅有状态快照，没有识别到明确的主设备启停操作。</p>
          <details class="snapshots"><summary>查看日报状态与确认依据</summary><div v-for="snapshot in selectedDevice.snapshots" :key="snapshot.day"><strong>{{ snapshot.day }} · {{ snapshot.status }}</strong><p>原表：{{ snapshot.tableStatus }} · {{ sourceLabel(snapshot) }}</p><small>{{ snapshot.fileName }}</small></div></details>
          <details v-if="selectedRuntime" class="snapshots runtime-days"><summary>查看每日运行时长及计算依据</summary><div v-for="day in selectedRuntime.days" :key="day.day"><strong>{{ day.day }} · {{ day.hours.toFixed(2) }}h</strong><p>{{ day.basis }}</p><small v-if="day.unknownHours">未确定 {{ day.unknownHours.toFixed(2) }}h</small><small v-if="day.conflict"> · 状态或操作需核对</small></div></details>
        </aside>
      </div>
      <p class="data-note">浅色带是该日的日报状态快照，节点是有明确时刻的实际操作；无色区间表示缺少该设备日报。</p>
    </template>
    <p v-else-if="!loading" class="empty">{{ latestDate ? '2026年10月起尚无调度记录，请手动选择时间阶段。' : '等待调度日报日期…' }}</p>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { queryDispatchData } from '../services/dispatchApi'
import { buildLifecycle, buildLifecycleOption, buildLifecycleDateTicks, defaultLifecycleRange, DAY_MS, dayTime, loadLifecycleReports, shiftDay, STATE_COLORS, LIFECYCLE_SUBJECTS, lifecycleSubjectName, compareLifecycleSubjects } from '../utils/dispatchLifecycle'
import { buildLifecycleExport, renderLifecycleSvg, lifecycleSvgToPng, downloadLifecycleBlob } from '../utils/dispatchLifecycleExport'
import { calculateDeviceRuntime } from '../utils/dispatchRuntime'

const props = defineProps({ projectKey: { type: String, required: true }, latestDate: { type: String, default: '' }, availableDates: { type: Array, default: () => [] }, refreshKey: { type: Number, default: 0 } })
const startDate = ref(''), endDate = ref(''), loadedRange = ref(null), reports = ref([])
const loading = ref(false), error = ref(''), selectedSubjects = ref(null), type = ref('ALL'), onlyActive = ref(true)
const selectedKey = ref(''), selectedEvent = ref(''), chartElement = ref(null)
const dateAxisViewport = ref(null), chartScroll = ref(null), dateTicks = ref([]), chartPixelWidth = ref(560)
const axisViewportWidth = ref(null)
const exporting = ref(false), exportError = ref(''), exportNotice = ref('')
let chart, resizeObserver, requestId = 0, renderId = 0, disposed = false, initializedProject = ''
const model = computed(() => loadedRange.value ? buildLifecycle(reports.value, loadedRange.value.start, loadedRange.value.end) : { devices: [], reportDays: 0 })
const availableSubjects = computed(() => [...new Set(model.value.devices.map(d => lifecycleSubjectName(d.plant)))].sort(compareLifecycleSubjects))
const subjectOptions = computed(() => [...new Set([...LIFECYCLE_SUBJECTS.map(s => s.name), ...availableSubjects.value])].sort(compareLifecycleSubjects))
const visibleDevices = computed(() => model.value.devices.filter(d => (selectedSubjects.value === null || selectedSubjects.value.includes(lifecycleSubjectName(d.plant))) && (type.value === 'ALL' || d.type === type.value) && (!onlyActive.value || d.events.length || d.conflicts.length)))
const visibleEvents = computed(() => visibleDevices.value.flatMap(d => d.events))
const starts = computed(() => visibleEvents.value.filter(e => e.kind === 'start').length)
const stops = computed(() => visibleEvents.value.filter(e => e.kind === 'stop').length)
const pending = computed(() => visibleDevices.value.reduce((n, d) => n + d.conflicts.length, 0))
const rangeDays = computed(() => loadedRange.value ? Math.round((dayTime(loadedRange.value.end) - dayTime(loadedRange.value.start)) / DAY_MS) + 1 : 0)
const selectedDevice = computed(() => visibleDevices.value.find(d => d.key === selectedKey.value) || visibleDevices.value[0])
const chartHeight = computed(() => Math.max(230, visibleDevices.value.length * 55 + 100))
const runtimeByDevice = computed(() => new Map(loadedRange.value ? visibleDevices.value.map(device => [device.key, calculateDeviceRuntime(device, loadedRange.value)]) : []))
const selectedRuntime = computed(() => selectedDevice.value ? runtimeByDevice.value.get(selectedDevice.value.key) : null)
const totalRuntime = computed(() => [...runtimeByDevice.value.values()].reduce((n, runtime) => n + runtime.hours, 0))
const rangeChanged = computed(() => loadedRange.value && (startDate.value !== loadedRange.value.start || endDate.value !== loadedRange.value.end))
const canExport = computed(() => !loading.value && !rangeChanged.value && loadedRange.value && visibleDevices.value.length > 0)

function toggleSubject(subject, checked) {
  const selected = new Set(selectedSubjects.value === null ? availableSubjects.value : selectedSubjects.value)
  if (checked) selected.add(subject)
  else selected.delete(subject)
  selectedSubjects.value = availableSubjects.value.every(name => selected.has(name)) ? null : [...selected].sort(compareLifecycleSubjects)
}

async function exportGraph(format) {
  if (!canExport.value || exporting.value) return
  exporting.value = true
  exportError.value = ''
  exportNotice.value = ''
  // 在点击时冻结已加载范围和筛选结果，导出期间修改控件不会混入旧图。
  try {
    const spec = buildLifecycleExport(visibleDevices.value, loadedRange.value, { subjects: selectedSubjects.value === null ? null : [...selectedSubjects.value], type: type.value, onlyActive: onlyActive.value }, model.value.reportDays)
    if (document.fonts?.ready) await document.fonts.ready
    const svg = renderLifecycleSvg(spec)
    const blob = format === 'png' ? await lifecycleSvgToPng(svg, spec.width, spec.height) : new Blob([svg], { type: 'image/svg+xml;charset=utf-8' })
    if (!disposed) {
      downloadLifecycleBlob(blob, `${spec.filename}.${format}`)
      exportNotice.value = `已生成${format.toUpperCase()}并发起下载，包含当前筛选的全部设备及完整日期范围。`
    }
  } catch (err) {
    if (!disposed) exportError.value = err.message || '导出失败，请重试'
  } finally { if (!disposed) exporting.value = false }
}

function syncHorizontalScroll() {
  if (dateAxisViewport.value && chartScroll.value) dateAxisViewport.value.scrollLeft = chartScroll.value.scrollLeft
}

function updateDateAxis() {
  if (!chart || !loadedRange.value) return
  chartPixelWidth.value = chart.getWidth()
  axisViewportWidth.value = chartScroll.value?.clientWidth || null
  dateTicks.value = buildLifecycleDateTicks(chart, model.value.start, model.value.end)
  nextTick(syncHorizontalScroll)
}

function sourceLabel(snapshot) {
  if (snapshot.conflict) return '差异尚未确认'
  if (snapshot.source === 'events') return '已确认以事件为准'
  if (snapshot.source.startsWith('status:')) return '手动指定'
  return snapshot.confirmed ? '已确认以原表为准' : '原表状态'
}

async function loadRange() {
  const currentRequest = ++requestId
  const start = startDate.value, end = endDate.value
  loading.value = true
  error.value = ''
  exportError.value = ''
  exportNotice.value = ''
  disposeChart()
  try {
    const data = await loadLifecycleReports(queryDispatchData, props.projectKey, start, end)
    if (currentRequest !== requestId || disposed) return
    reports.value = data
    loadedRange.value = { start, end }
    selectedSubjects.value = null
    type.value = 'ALL'
    selectedKey.value = ''
    selectedEvent.value = ''
    onlyActive.value = model.value.devices.some(d => d.events.length || d.conflicts.length)
  } catch (err) {
    if (currentRequest === requestId && !disposed) {
      error.value = err.message || '生命周期读取失败，请重试'
      reports.value = []
      loadedRange.value = null
    }
  } finally {
    if (currentRequest === requestId && !disposed) loading.value = false
  }
}

function quickRange(days) {
  endDate.value = props.latestDate || endDate.value
  startDate.value = shiftDay(endDate.value, 1 - days)
  loadRange()
}

function disposeChart() {
  resizeObserver?.disconnect()
  resizeObserver = null
  dateTicks.value = []
  chart?.dispose()
  chart = null
}

async function renderChart() {
  const rendering = ++renderId
  disposeChart()
  await nextTick()
  if (rendering !== renderId || disposed || loading.value || !chartElement.value || !visibleDevices.value.length || !loadedRange.value) return
  chart = echarts.init(chartElement.value)
  const visibleDays = Math.max(1, Math.floor((chartElement.value.clientWidth - 170) / 52))
  const option = buildLifecycleOption(visibleDevices.value, model.value.start, model.value.end, visibleDays)
  option.xAxis.axisLabel.show = false
  option.grid.top = 12
  chart.setOption(option)
  chart.on('datazoom', updateDateAxis)
  updateDateAxis()
  chart.on('click', params => {
    if (params.data?.deviceKey) {
      selectedKey.value = params.data.deviceKey
      selectedEvent.value = params.data.event?.id || ''
    }
  })
  resizeObserver = new ResizeObserver(() => { chart?.resize(); updateDateAxis() })
  resizeObserver.observe(chartElement.value)
  if (!visibleDevices.value.some(d => d.key === selectedKey.value)) selectedKey.value = visibleDevices.value[0].key
}

watch([visibleDevices, loading], renderChart, { flush: 'post' })
watch(() => [props.projectKey, props.availableDates], ([project, dates]) => {
  const range = defaultLifecycleRange(dates)
  if (!range || initializedProject === project) return
  initializedProject = project
  endDate.value = range.end
  startDate.value = range.start
  loadRange()
}, { immediate: true })
watch(() => props.refreshKey, () => { if (loadedRange.value) loadRange() })
onBeforeUnmount(() => { disposed = true; requestId++; disposeChart() })
</script>

<style scoped>
.lifecycle-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; box-shadow: 0 5px 20px #0f172a05; color: #334155; }
.lifecycle-header { padding: 22px 26px 18px; display: flex; justify-content: space-between; align-items: center; background: linear-gradient(110deg, #f0f8ff, #fff 70%); border-bottom: 1px solid #edf2f7; }
.eyebrow { color: #4c83b1; letter-spacing: 1.2px; font-size: 10px; font-weight: 700; }
h3 { font-size: 21px; margin: 6px 0; color: #18344f; letter-spacing: .4px; } .lifecycle-header p { margin: 0; color: #74869a; font-size: 12px; }
.view-badge { color: #527697; background: #edf5fc; padding: 6px 11px; border-radius: 20px; font-size: 11px; }
.range-bar { display: flex; align-items: end; gap: 12px; flex-wrap: wrap; padding: 18px 26px; }
.range-bar label { display: grid; gap: 6px; font-size: 11px; color: #64748b; } input[type=date], select { background: #fff; border: 1px solid #dce5ef; border-radius: 7px; padding: 8px 10px; color: #334155; font: inherit; font-size: 12px; min-height: 35px; box-sizing: border-box; }
.range-divider { padding-bottom: 10px; color: #94a3b8; font-size: 12px; } button { cursor: pointer; font: inherit; font-size: 12px; border: 1px solid #dce5ef; background: #fff; color: #52677e; border-radius: 7px; padding: 9px 12px; }
button:hover { background: #edf5fc; } button.primary { background: #215e96; color: #fff; border-color: #215e96; } button.primary:hover { background: #184975; }
.quick-ranges { margin-left: auto; display: flex; gap: 6px; } .quick-ranges button { border: 0; background: #f1f5f9; }
.stat-strip { margin: 0 26px 18px; background: #f8fafc; border: 1px solid #ecf0f5; border-radius: 10px; display: grid; grid-template-columns: repeat(6, 1fr); padding: 15px 0; }
.stat-strip > div { display: grid; gap: 5px; padding: 0 20px; border-right: 1px solid #e2e8f0; }.stat-strip > div:last-child { border: 0; }.stat-strip strong { font-size: 24px; color: #234665; font-variant-numeric: tabular-nums; }.stat-strip small { color: #94a3b8; font-size: 12px; font-weight: 400; }.stat-strip span { color: #718398; font-size: 11px; }.stat-strip .amber { color: #b97811; }.stat-strip .rose { color: #ce4c60; }
.filter-bar { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 0 26px 14px; flex-wrap: wrap; }.filters { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }.toggle { font-size: 12px; display: flex; gap: 5px; align-items: center; color: #64748b; margin-left: 5px; }.loaded-range { font-size: 11px; color: #8293a6; }
.legend { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; padding: 12px 26px; border-top: 1px solid #f1f5f9; font-size: 11px; color: #64748b; }.legend span { display: inline-flex; align-items: center; gap: 5px; }.legend i { width: 9px; height: 9px; border-radius: 2px; opacity: .65; }.node-key { margin-left: auto; }.conflict-key { color: #b97811; }
.timeline-layout { display: grid; grid-template-columns: minmax(0, 1fr) 290px; border-top: 1px solid #edf2f7; }.chart-panel { min-width: 0; }.chart-scroll { max-height: 530px; overflow: auto; }.lifecycle-chart { width: 100%; min-width: 560px; }.chart-hint { font-size: 10px; color: #94a3b8; margin: 0; padding: 0 18px 12px; }.device-detail { background: #fbfcfe; border-left: 1px solid #e8eef5; padding: 16px; max-height: 565px; overflow: auto; }
.detail-heading { display: grid; gap: 8px; font-size: 10px; color: #8293a6; }.detail-heading select { width: 100%; } h4 { font-size: 20px; margin: 16px 0 5px; color: #234665; } h4 small { font-size: 11px; color: #8293a6; font-weight: 400; }.detail-summary { font-size: 11px; color: #8293a6; margin: 0 0 14px; }.detail-warning { font-size: 11px; line-height: 1.6; color: #a96d10; background: #fff6e5; padding: 8px; border-radius: 6px; margin-bottom: 14px; }
.chart-width { min-width: 560px; width: 100%; }
.date-axis-viewport { overflow: hidden; height: 42px; background: #fff; border-bottom: 1px solid #e8eef5; box-shadow: 0 2px 4px #0f172a08; }
.date-axis-inner { position: relative; height: 42px; min-width: 560px; }
.date-tick { position: absolute; bottom: 10px; transform: translateX(-50%); color: #64748b; font-size: 12px; white-space: nowrap; }
button:disabled { cursor: not-allowed; opacity: .5; }
.export-notice { margin: 0; padding: 8px 26px; font-size: 12px; color: #527697; background: #f0f8ff; }
.runtime-summary { padding: 10px; margin-bottom: 14px; background: #eef5fc; border-radius: 8px; }
.runtime-summary > strong { font-size: 21px; color: #215e96; }
.runtime-summary p { font-size: 11px; line-height: 1.6; margin: 6px 0; color: #64748b; }
.runtime-summary small { font-size: 10px; font-weight: 400; color: #718398; line-height: 1.6; }
.runtime-days { margin-top: 14px; }
.subject-picker { margin: 0 26px 14px; padding: 10px 14px 13px; display: flex; flex-wrap: wrap; gap: 10px 16px; border: 1px solid #e2e8f0; border-radius: 8px; }
.subject-picker legend { font-size: 11px; padding: 0 5px; color: #64748b; }
.subject-option { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; cursor: pointer; color: #334155; }
.subject-option.unavailable { opacity: .45; cursor: default; }
@media (max-width: 640px) { .subject-picker { margin-left: 16px; margin-right: 16px; } }
.event-list { padding: 0 0 0 14px; margin: 0; list-style: none; }.event-item { padding: 0 0 18px 14px; border-left: 1px solid #dbe4ee; position: relative; }.event-item::before { content: ''; position: absolute; width: 8px; height: 8px; background: #059669; border: 2px solid #fff; border-radius: 50%; left: -6px; top: 2px; }.event-item.start::before { background: #e79919; }.event-item.stop::before { background: #dc5263; }.event-item.selected { background: #eef5fc; border-radius: 4px; }.event-item time { font-size: 10px; color: #8293a6; }.event-item strong { display: block; font-size: 13px; margin: 5px 0; }.event-item strong span { font-size: 10px; font-weight: 400; margin-left: 6px; }.event-item p { font-size: 11px; color: #64748b; margin: 5px 0; overflow-wrap: anywhere; line-height: 1.6; }.event-item small, .snapshots small { font-size: 10px; color: #94a3b8; }.no-events { font-size: 12px; color: #8293a6; line-height: 1.8; }.snapshots { border-top: 1px solid #e8eef5; padding-top: 12px; font-size: 11px; }.snapshots summary { cursor: pointer; color: #527697; }.snapshots > div { padding: 10px 0; border-bottom: 1px solid #edf2f7; }.snapshots p { margin: 4px 0; color: #8293a6; }
.data-note { border-top: 1px solid #edf2f7; margin: 0; padding: 12px 26px; font-size: 11px; line-height: 1.7; color: #8293a6; }.empty, .loading { padding: 38px 26px; text-align: center; font-size: 13px; color: #8293a6; }.error { background: #fff1f2; color: #be3450; padding: 12px 26px; font-size: 12px; margin: 0; }
@media (max-width: 1000px) { .timeline-layout { grid-template-columns: 1fr; }.device-detail { border-left: 0; border-top: 1px solid #e8eef5; max-height: 340px; }.node-key { margin-left: 0; } }
@media (max-width: 640px) { .lifecycle-header { padding: 18px 16px; }.view-badge { display: none; }.range-bar { padding: 16px; gap: 8px; }.quick-ranges { margin-left: 0; width: 100%; }.stat-strip { margin: 0 16px 14px; grid-template-columns: repeat(3, 1fr); gap: 14px 0; }.stat-strip > div { padding: 0 12px; }.stat-strip strong { font-size: 20px; }.stat-strip > div:nth-child(3) { border: 0; }.filter-bar, .legend { padding-left: 16px; padding-right: 16px; }.data-note { padding: 12px 16px; } }
</style>
