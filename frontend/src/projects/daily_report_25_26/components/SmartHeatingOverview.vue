<template>
  <section class="overview">
    <div class="overview-toolbar">
      <div>
        <h3>工况一览</h3>
        <p>电厂 · 首站 · 一网 · 换热站及商户，共 82 项重点工况</p>
      </div>
      <label class="overview-search">搜索测点 <input v-model="keyword" type="search" placeholder="输入名称或采集名称" /></label>
      <span class="freshness" :class="{ live: available }">{{ available ? '工况数据已接入' : '暂无实时工况' }}</span>
    </div>
    <p v-if="!available" class="overview-notice" role="status">
      {{ collectedEpoch ? '工况一览数据链路未连接或采集已超时，请检查客户端采集状态。' : '尚未收到有效工况一览数据，请确认已运行新版客户端且新接口采集成功。' }}
    </p>
    <div class="overview-meta">
      <p class="collection-time">采集时间：<time title="取本页测点中出现最多的源采集时间；不同来源可能略有差异">{{ collectedTime }}</time></p>
      <p class="overview-note">温度 ℃ / 压力 MPa / 流量 t/h / 热量 GJ</p>
    </div>
    <nav class="group-navigation" aria-label="工况分区快捷导航">
      <a v-for="(group, index) in filteredGroups" :key="group.title" :href="`#heating-group-${index}`">{{ group.title }} <span>{{ group.rows.length }}</span></a>
    </nav>
    <div class="overview-grid">
      <div v-for="(column, columnIndex) in layoutColumns" :key="columnIndex" class="overview-column">
      <section v-for="group in column" :id="`heating-group-${group.index}`" :key="group.title" class="overview-panel">
        <header><div class="group-heading"><span class="group-index">0{{ group.index + 1 }}</span><h4>{{ group.title }}</h4></div><span>{{ group.rows.length }} 项</span></header>
        <div class="table-content">
          <table>
            <colgroup><col class="column-order" /><col class="column-name" /><col v-for="field in fields" :key="field" class="column-value" /></colgroup>
            <thead><tr><th>序号</th><th>名称</th><th>温度</th><th>压力</th><th>流量</th><th>热量</th></tr></thead>
            <tbody>
              <tr v-for="(row, rowIndex) in group.rows" :key="row.no" :title="pointTitle(row)" :class="{ 'section-break': hasBreakBefore(group, rowIndex) }">
                <td class="row-order">{{ row.no }}</td><th scope="row">{{ row.name }}<span class="mobile-source">{{ row.sourceName }}</span></th>
                <td v-for="field in fields" :key="field" :data-label="fieldLabels[field]">{{ value(row, field) }}</td>
              </tr>
              <tr v-if="!group.rows.length"><td colspan="6" class="empty">没有匹配的测点</td></tr>
            </tbody>
          </table>
        </div>
      </section>
      </div>
    </div>
    <p class="overview-note">“—”表示未收到数值；0 为上游实际返回值。悬停测点可查看采集名称。</p>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import { OVERVIEW_GROUPS } from '../constants/smartHeatingOverview'

const props = defineProps({
  data: { type: Object, default: null },
  collectedEpoch: { type: Number, default: null },
  online: { type: Boolean, default: false },
  now: { type: Number, required: true },
})
const keyword = ref('')
const fields = ['WENDU', 'YALI', 'LIULIANG', 'RELIANG']
const fieldLabels = { WENDU: '温度 · ℃', YALI: '压力 · MPa', LIULIANG: '流量 · t/h', RELIANG: '热量 · GJ' }
// 工况独立采集时效，其他接口持续推流不能延长该页的有效时间。
const available = computed(() => props.online && props.data && props.collectedEpoch &&
  props.now / 1000 - props.collectedEpoch >= 0 && props.now / 1000 - props.collectedEpoch <= 180)
// 统一展示源数据中最常见的采集时间，避免将中继抓取时间误当成测点采集时间。
// 统计固定展示清单，不随搜索变化；兼容上游月份、日期未补零的写法。
const collectedTime = computed(() => {
  if (!available.value) return '—'
  const counts = new Map()
  for (const group of OVERVIEW_GROUPS) {
    for (const row of group.rows) {
      const record = props.data?.[row.dictName]?.[row.sourceName]
      const raw = String(record?.SHIJIAN || record?.update_time || '').trim()
      const match = raw.match(/^(\d{4})-(\d{1,2})-(\d{1,2})[ T](\d{1,2}):(\d{2}):(\d{2})$/)
      if (!match) continue
      const [, year, month, day, hour, minute, second] = match
      const timestamp = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')} ${hour.padStart(2, '0')}:${minute}:${second}`
      counts.set(timestamp, (counts.get(timestamp) || 0) + 1)
    }
  }
  return [...counts].sort((a, b) => b[1] - a[1] || b[0].localeCompare(a[0]))[0]?.[0] || '—'
})
const filteredGroups = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return OVERVIEW_GROUPS.map((group, index) => ({ ...group, index,
    rows: group.rows.filter(row => `${row.name} ${row.sourceName}`.toLowerCase().includes(query)),
  }))
})
// 左列电厂，中列首站与一网，右列换热站及商户，保留各组导航锚点。
const layoutColumns = computed(() => [[filteredGroups.value[0]], [filteredGroups.value[1], filteredGroups.value[2]], [filteredGroups.value[3]]])
// 按原始序号分段，搜索后保留分组边界，但不在首条结果前添加空分隔。
const groupBreaks = [[10, 22, 25], [], [5], [5, 11, 15, 19, 23]]
function hasBreakBefore(group, rowIndex) {
  if (rowIndex === 0) return false
  return groupBreaks[group.index].some(start => group.rows[rowIndex - 1].no < start && group.rows[rowIndex].no >= start)
}
function point(row) { return available.value ? props.data?.[row.dictName]?.[row.sourceName] : null }
function value(row, field) {
  const raw = point(row)?.[field]
  if (raw === null || raw === undefined || raw === '' || String(raw).trim() === '') return '—'
  const numeric = Number(raw)
  return Number.isFinite(numeric) ? numeric.toLocaleString('zh-CN', { maximumFractionDigits: 3 }) : '—'
}
function pointTitle(row) {
  return `采集名称：${row.sourceName}`
}
</script>

<style scoped>
.overview-toolbar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin: 24px 0 16px; }
h3, h4, p { margin: 0; }
h3 { color: #0f172a; font-size: 22px; }
.overview-toolbar p, .overview-note { color: #64748b; font-size: 13px; margin-top: 8px; line-height: 1.7; }
.overview-meta { display: flex; align-items: center; justify-content: space-between; gap: 8px 20px; flex-wrap: wrap; margin-top: 12px; }
.collection-time { color: #475569; font-size: 13px; line-height: 1.7; }
.collection-time time { color: #0f172a; font-weight: 600; font-variant-numeric: tabular-nums; }
.overview-meta .overview-note { margin-top: 0; }
.overview-toolbar label { margin-left: auto; color: #475569; font-size: 13px; }
input { box-sizing: border-box; min-height: 44px; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 10px; margin-left: 8px; width: 220px; background: #fff; color: #0f172a; }
input:focus-visible { outline: 3px solid #bae6fd; border-color: #0284c7; }
.freshness { color: #92400e; background: #fef3c7; padding: 7px 12px; border-radius: 20px; font-size: 13px; }
.freshness.live { color: #047857; background: #d1fae5; }
.overview-notice { padding: 16px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px; color: #92400e; margin-bottom: 16px; }
/* 三列自然展开，中列独立堆叠两张表，不设置区块高度或内部滚动。 */
.overview-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 16px; align-items: start; }
.overview-column { display: flex; flex-direction: column; gap: 20px; min-width: 0; }
.overview-panel { box-sizing: border-box; min-width: 0; scroll-margin-top: 20px; background: white; border: 1px solid #e2e8f0; border-radius: 14px; box-shadow: 0 4px 16px #0f172a05; }
.overview-panel header { display: flex; flex: 0 0 auto; align-items: center; min-height: 65px; box-sizing: border-box; gap: 12px; justify-content: space-between; padding: 18px 16px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; color: #0f172a; }
.group-heading { display: flex; align-items: center; gap: 10px; }
.overview-panel header .group-index { color: #0284c7; background: #e0f2fe; padding: 5px 7px; border-radius: 7px; font-weight: 700; font-size: 11px; }
.overview-panel header span { font-size: 13px; color: #64748b; }
.table-content { padding-bottom: 4px; }
table { width: 100%; table-layout: fixed; border-collapse: separate; border-spacing: 0; font-size: 12px; white-space: normal; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.column-order { width: 8%; }
.column-name { width: 32%; }
.column-value { width: 15%; }
th, td { padding: 11px 6px; border-bottom: 1px solid #f1f5f9; text-align: right; line-height: 1.6; }
thead { background: #eef4fa; color: #475569; }
thead th { background: #eef4fa; }
th:nth-child(2), tbody th { text-align: left; }
tbody th { font-weight: 500; color: #334155; }
tbody tr.section-break > * { border-top: 10px solid #e9eff5; }
tbody td { color: #0f172a; }
tbody td:first-child { color: #94a3b8; }
tbody tr:hover { background: #f0f9ff; }
.mobile-source { display: none; }
.group-navigation { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
.group-navigation a { display: inline-flex; align-items: center; gap: 10px; padding: 10px 14px; min-height: 24px; color: #475569; text-decoration: none; background: white; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 13px; }
.group-navigation a:hover { border-color: #7dd3fc; color: #0369a1; }
.group-navigation a:focus-visible { outline: 3px solid #7dd3fc; outline-offset: 2px; }
.group-navigation span { color: #0284c7; font-size: 11px; font-variant-numeric: tabular-nums; }
.empty { text-align: center; color: #64748b; }
@media (max-width: 1100px) { .overview-grid { grid-template-columns: minmax(0, 1fr); } }
/* 手机把同一表格重排为两列参数卡片，保留原始数据与名称顺序。 */
@media (max-width: 640px) {
  .overview-toolbar { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; margin-top: 20px; }
  h3 { font-size: 20px; }
  .overview-toolbar p { font-size: 12px; }
  .overview-toolbar label { display: grid; gap: 8px; margin-left: 0; order: 2; }
  input { width: 100%; margin-left: 0; font-size: 16px; }
  .freshness { justify-self: start; font-size: 12px; }
  .overview-notice { font-size: 13px; padding: 14px; line-height: 1.7; }
  .overview-note { font-size: 12px; overflow-wrap: anywhere; }
  .group-navigation { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .group-navigation a { justify-content: space-between; padding: 10px; font-size: 12px; }
  .overview-grid { grid-template-columns: minmax(0, 1fr); gap: 20px; }
  .overview-panel { height: auto; overflow: visible; background: transparent; border: 0; box-shadow: none; }
  .overview-panel header { padding: 12px 2px; border: 0; background: transparent; }
  .overview-panel h4 { font-size: 15px; }
  .table-content { padding-bottom: 0; }
  table, tbody { display: block; min-width: 0; white-space: normal; }
  colgroup { display: none; }
  thead { display: none; }
  tbody { display: grid; gap: 10px; }
  tbody tr { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; padding: 14px; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; }
  tbody tr:hover { background: #fff; }
  tbody .row-order { display: none; }
  tbody th[scope="row"] { grid-column: 1 / -1; padding: 0 0 5px; border: 0; font-weight: 650; font-size: 14px; line-height: 1.6; overflow: visible; overflow-wrap: anywhere; }
  td[data-label] { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; min-width: 0; padding: 10px; background: #f8fafc; border: 0; border-radius: 8px; text-align: left; font-size: 18px; font-weight: 600; overflow-wrap: anywhere; }
  td[data-label]::before { content: attr(data-label); font-size: 11px; font-weight: 400; color: #64748b; }
  td[data-label]:nth-child(3) { color: #c2410c; }
  tbody tr.section-break { margin-top: 10px; border-top: 3px solid #cbd5e1; }
  tbody tr.section-break > * { border-top: 0; }
  .mobile-source { display: block; margin-top: 5px; color: #64748b; font-size: 11px; line-height: 1.6; font-weight: 400; overflow-wrap: anywhere; }
  .empty { grid-column: 1 / -1; border: 0; padding: 16px 0; }
}
</style>
