<template>
  <div class="min-h-screen bg-slate-50 p-5 md:p-8">
    <!-- 头部 -->
    <header class="mb-6 flex flex-col md:flex-row md:items-end md:justify-between gap-3">
      <div>
        <div class="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-800">
          大连洁净能源集团生产日报
        </div>
        <div class="text-slate-500">Daily Production Report &amp; Dashboard</div>
      </div>
      <div class="text-right text-sm text-slate-500">
        <div>今日：{{ today }}</div>
        <div>业务日期（昨日）：{{ biz }}</div>
      </div>
    </header>

    <!-- 顶部摘要：关键卡片 -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div class="bg-gradient-to-br from-slate-800 to-slate-600 text-white rounded-2xl p-5 shadow">
        <div class="text-xs opacity-80">平均气温（7日当期）</div>
        <div class="text-2xl font-bold">{{ avgTempNow.toFixed(1) }}℃</div>
      </div>
      <div class="bg-white rounded-2xl p-5 shadow border border-slate-100">
        <div class="text-xs text-slate-500">集团当日边际利润（演示）</div>
        <div class="text-2xl font-bold text-slate-800">{{ marginData[0].margin }} 万元</div>
      </div>
      <div class="bg-white rounded-2xl p-5 shadow border border-slate-100">
        <div class="text-xs text-slate-500">集团标煤消耗（当期）</div>
        <div class="text-2xl font-bold text-slate-800">{{ coalStdNow[0] }} 吨标煤</div>
      </div>
      <div class="bg-white rounded-2xl p-5 shadow border border-slate-100">
        <div class="text-xs text-slate-500">集团当日投诉量</div>
        <div class="text-2xl font-bold text-slate-800">{{ complaintsNow[0].count }} 件</div>
      </div>
    </section>

    <!-- 主体网格布局（两列 / 三列自适应） -->
    <main class="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <!-- 1. 气温变化：折线 + 表格 -->
      <div class="lg:col-span-6 xl:col-span-5">
        <Card title="气温变化情况（7日窗口，含同期）" subtitle="平均气温" extra="单位：℃">
          <EChart :option="tempOpt" height="260px" />
          <div class="mt-3">
            <DataTable
              :columns="['日期', '当期(℃)', '同期(℃)']"
              :rows="tempDates.map((d, i) => [d, tempNow[i], tempPeer[i]])"
            />
          </div>
        </Card>
      </div>

      <!-- 2. 边际利润简报：表格 + 组合图 -->
      <div class="lg:col-span-6 xl:col-span-7">
        <Card title="边际利润简报" subtitle="集团/各单位" extra="单位：万元">
          <EChart :option="marginOpt" height="260px" />
          <div class="mt-3">
            <DataTable
              :columns="['单位', '直接收入', '煤成本', '可计量辅材', '边际利润', '可比煤价边际']"
              :rows="marginData.map(d => [d.org, d.direct, d.coal, d.materials, d.margin, d.margin_cmp_coal])"
            />
          </div>
        </Card>
      </div>

      <!-- 3. 收入分类对比（集团） -->
      <div class="lg:col-span-6 xl:col-span-4">
        <Card title="收入分类对比（集团）" subtitle="当期 vs 同期" extra="单位：万元">
          <EChart :option="incomeOpt" height="260px" />
        </Card>
      </div>

      <!-- 4. 单耗对比（6家单位） -->
      <div class="lg:col-span-6 xl:col-span-8">
        <Card title="单耗对比" subtitle="热/电/水单耗" extra="单位：每单位供暖量">
          <EChart :option="unitOpt" height="260px" />
        </Card>
      </div>

      <!-- 5. 标煤消耗量对比：表格 + 图 -->
      <div class="lg:col-span-6">
        <Card title="标煤消耗量对比" subtitle="当期 vs 同期" extra="单位：吨标煤">
          <EChart :option="coalStdOpt" height="260px" />
          <div class="mt-3">
            <DataTable
              :columns="['单位', '当期', '同期', '差值']"
              :rows="coalStdOrgs.map((o, i) => [o, coalStdNow[i], coalStdPeer[i], coalStdNow[i] - coalStdPeer[i]])"
            />
          </div>
        </Card>
      </div>

      <!-- 6. 投诉量：表格 + 图 -->
      <div class="lg:col-span-6">
        <Card title="投诉量" subtitle="当日省市平台服务投诉量" extra="单位：件">
          <EChart :option="complaintOpt" height="260px" />
          <div class="mt-3">
            <DataTable :columns="['单位', '当日投诉量']" :rows="complaintsNow.map(d => [d.org, d.count])" />
          </div>
        </Card>
      </div>

      <!-- 7. 煤炭库存：堆积柱状图 -->
      <div class="lg:col-span-12">
        <Card title="煤炭库存" subtitle="厂内/港口/在途（堆积）" extra="单位：吨">
          <EChart :option="coalStockOpt" height="300px" />
        </Card>
      </div>
    </main>

    <!-- 页脚 -->
    <footer class="text-center text-xs text-slate-400 mt-8">
      本页面为 ECharts 演示框架：可无缝替换为后端 API / 视图数据（如 average_temperature_data、sum_coal_inventory_data 等）。
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

// ---------- 小组件：卡片 & 表格 ----------
const Card = defineComponent({
  name: 'Card',
  props: { title: String, subtitle: String, extra: String },
  setup(props, { slots }) {
    return () => (
      <div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-4 flex flex-col gap-3">
        <div class="flex items-start justify-between">
          <div>
            <div class="text-sm text-slate-500">{props.subtitle}</div>
            <h3 class="text-lg font-semibold text-slate-800">{props.title}</h3>
          </div>
          {props.extra ? <div class="text-xs text-slate-500">{props.extra}</div> : null}
        </div>
        <div class="min-h-[220px]">{slots.default?.()}</div>
      </div>
    )
  }
})

const DataTable = defineComponent({
  name: 'DataTable',
  props: { columns: Array, rows: Array },
  setup(props) {
    return () => (
      <div class="overflow-auto rounded-xl border border-slate-100">
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50 text-slate-600">
            <tr>
              {props.columns?.map((c) => (
                <th class="px-3 py-2 text-left whitespace-nowrap">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            {props.rows?.map((row) => (
              <tr class="hover:bg-slate-50">
                {row.map((cell) => (
                  <td class="px-3 py-2 whitespace-nowrap">{String(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
})

// ---------- 通用 EChart 组件（修复不出图/自适应） ----------
const EChart = defineComponent({
  name: 'EChart',
  props: { option: Object, height: { type: String, default: '260px' } },
  setup(props) {
    const el = ref(null)
    let chart = null
    let ro = null

    const init = () => {
      if (!el.value) return
      chart = echarts.init(el.value)
      if (props.option) chart.setOption(props.option, true)
      // 自适应：ResizeObserver + window resize，避免“图不显示/容器变动后空白”
      if (window.ResizeObserver) {
        ro = new ResizeObserver(() => chart && chart.resize())
        ro.observe(el.value)
      }
      window.addEventListener('resize', handleResize)
    }

    const handleResize = () => { chart && chart.resize() }

    onMounted(init)
    onUnmounted(() => {
      window.removeEventListener('resize', handleResize)
      if (ro) ro.disconnect()
      if (chart) { chart.dispose(); chart = null }
    })

    watch(() => props.option, (opt) => { if (chart && opt) chart.setOption(opt, true) }, { deep: true })

    return () => <div ref={el} style={{ width: '100%', height: props.height }} />
  }
})

// ---------- 工具函数 ----------
const fmt = (d) => d.toISOString().slice(0, 10)
const today = fmt(new Date())
const _biz = new Date(); _biz.setDate(_biz.getDate() - 1)
const biz = fmt(_biz)

// ---------- 演示数据（与 React 版一致，可替换为 API） ----------
// 1. 气温（7日窗口 + 同期）
const tempDates = Array.from({ length: 7 }, (_, i) => {
  const d = new Date(_biz)
  d.setDate(d.getDate() - 3 + i)
  return fmt(d)
})
const tempNow = [14.2, 14.1, 14.4, 14.6, 15.6, 16.3, 16.9]
const tempPeer = [12.9, 12.5, 12.2, 12.8, 13.4, 13.9, 14.1]
const avgTempNow = computed(() => tempNow.reduce((a, b) => a + b, 0) / tempNow.length)

// 2. 边际利润（单位：万元）
const orgs7 = ['集团全口径', '主城区', '金州热电', '北方热电', '金普热电', '庄河环海', '研究院']
const marginData = orgs7.map((o, i) => ({
  org: o,
  direct: 1000 - i * 60,
  coal: 520 - i * 30,
  materials: 80 - i * 5,
  margin: 400 - i * 20,
  margin_cmp_coal: 430 - i * 18,
}))

// 3. 收入分类（集团）
const incomeCat = ['暖收入', '售电收入', '售高温水收入', '售汽收入']
const incomeNow = [600, 240, 120, 80]
const incomePeer = [560, 260, 110, 70]

// 4. 单耗对比（单位：每单位供暖量）
const orgs6 = ['主城区', '金州热电', '北方热电', '金普热电', '庄河环海', '研究院']
const unitHeat = orgs6.map((o, i) => ({ org: o, heat: 0.95 + i * 0.03, elec: 0.42 + i * 0.02, water: 0.21 + i * 0.015 }))
const unitHeatPeer = orgs6.map((o, i) => ({ org: o, heat: 0.98 + i * 0.02, elec: 0.45 + i * 0.018, water: 0.23 + i * 0.012 }))

// 5. 标煤消耗量（单位：吨标煤）
const coalStdOrgs = ['集团全口径', '主城区', '金州热电', '北方热电', '金普热电', '庄河环海']
const coalStdNow = [980, 420, 160, 180, 120, 100]
const coalStdPeer = [1020, 440, 150, 190, 130, 90]

// 6. 投诉量（当日件数）
const complaintsNow = orgs7.map((o, i) => ({ org: o, count: 30 - i * 3 }))

// 7. 煤炭库存（单位：吨）
const stockOrgs = ['北海热电厂', '香海热电厂', '金州热电', '北方热电', '金普热电', '庄河环海']
const stockData = stockOrgs.map((o, i) => ({
  org: o,
  inPlant: 30000 - i * 2000,
  inPort: 10000 - i * 800,
  inTransit: 6000 - i * 500,
}))

// ---------- ECharts Options ----------
const tempOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['当期', '同期'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: tempDates },
  yAxis: { type: 'value', name: '℃' },
  series: [
    { name: '当期', type: 'line', smooth: true, data: tempNow },
    { name: '同期', type: 'line', smooth: true, data: tempPeer },
  ],
}))

const marginOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['直接收入', '煤成本', '可计量辅材成本', '边际利润', '可比煤价边际利润'] },
  grid: { left: 40, right: 20, top: 40, bottom: 60 },
  xAxis: { type: 'category', data: orgs7 },
  yAxis: { type: 'value', name: '万元' },
  series: [
    { name: '直接收入', type: 'bar', stack: 'base', data: marginData.map(d => d.direct) },
    { name: '煤成本', type: 'bar', stack: 'base', data: marginData.map(d => -d.coal) },
    { name: '可计量辅材成本', type: 'bar', stack: 'base', data: marginData.map(d => -d.materials) },
    { name: '边际利润', type: 'line', data: marginData.map(d => d.margin) },
    { name: '可比煤价边际利润', type: 'line', data: marginData.map(d => d.margin_cmp_coal) },
  ],
}))

const incomeOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['当期', '同期'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: incomeCat },
  yAxis: { type: 'value', name: '万元' },
  series: [
    { name: '当期', type: 'bar', data: incomeNow },
    { name: '同期', type: 'bar', data: incomePeer },
  ],
}))

const unitOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['热单耗', '电单耗', '水单耗'] },
  grid: { left: 40, right: 20, top: 40, bottom: 60 },
  xAxis: { type: 'category', data: orgs6 },
  yAxis: { type: 'value', name: '单位/供暖量' },
  series: [
    { name: '热单耗', type: 'bar', data: unitHeat.map(d => d.heat) },
    { name: '电单耗', type: 'bar', data: unitHeat.map(d => d.elec) },
    { name: '水单耗', type: 'bar', data: unitHeat.map(d => d.water) },
  ],
}))

const coalStdOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['当期', '同期'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: coalStdOrgs },
  yAxis: { type: 'value', name: '吨标煤' },
  series: [
    { name: '当期', type: 'bar', data: coalStdNow },
    { name: '同期', type: 'bar', data: coalStdPeer },
  ],
}))

const complaintOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 20, bottom: 40 },
  xAxis: { type: 'category', data: orgs7 },
  yAxis: { type: 'value', name: '件' },
  series: [
    { name: '当日投诉量', type: 'bar', data: complaintsNow.map(d => d.count), label: { show: true, position: 'top' } },
  ],
}))

const coalStockOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['厂内存煤', '港口存煤', '在途煤炭'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: stockOrgs },
  yAxis: { type: 'value', name: '吨' },
  series: [
    { name: '厂内存煤', type: 'bar', stack: 'total', data: stockData.map(d => d.inPlant) },
    { name: '港口存煤', type: 'bar', stack: 'total', data: stockData.map(d => d.inPort) },
    { name: '在途煤炭', type: 'bar', stack: 'total', data: stockData.map(d => d.inTransit) },
  ],
}))
</script>

<!-- SFC 样式（可按需微调） -->
<style scoped>
/* 这里留空，主要用 Tailwind；如需覆盖可在此补充 */
</style>
