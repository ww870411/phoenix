<template>
  <div class="dashboard-page">
    <header class="dashboard-header">
      <div class="dashboard-header__titles">
        <div class="dashboard-header__title">大连洁净能源集团生产日报</div>
        <div class="dashboard-header__subtitle">Daily Production Report &amp; Dashboard</div>
      </div>
      <div class="dashboard-header__meta">
        <div>今日：{{ todayText }}</div>
        <div>业务日期（昨日）：{{ bizDateText }}</div>
      </div>
    </header>

    <section class="dashboard-summary">
      <div class="summary-card summary-card--gradient">
        <div class="summary-card__label">平均气温（7日当期）</div>
        <div class="summary-card__value">{{ averageTemp }}℃</div>
      </div>
      <div class="summary-card">
        <div class="summary-card__label">集团当日边际利润（演示）</div>
        <div class="summary-card__value">{{ marginHeadline }} 万元</div>
      </div>
      <div class="summary-card">
        <div class="summary-card__label">集团标煤消耗（当期）</div>
        <div class="summary-card__value">{{ coalStdHeadline }} 吨标煤</div>
      </div>
      <div class="summary-card">
        <div class="summary-card__label">集团当日投诉量</div>
        <div class="summary-card__value">{{ complaintsHeadline }} 件</div>
      </div>
    </section>

    <main class="dashboard-grid">
      <section class="dashboard-grid__item dashboard-grid__item--temp">
        <Card title="气温变化情况（7日窗口，含同期）" subtitle="平均气温" extra="单位：℃">
          <EChart :option="tempOpt" height="260px" />
          <div class="dashboard-table-wrapper">
            <Table :columns="temperatureColumns" :data="temperatureTableData" />
          </div>
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--margin">
        <Card title="边际利润简报" subtitle="集团/各单位" extra="单位：万元">
          <EChart :option="marginOpt" height="260px" />
          <div class="dashboard-table-wrapper">
            <Table :columns="marginColumns" :data="marginTableData" />
          </div>
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--income">
        <Card title="收入分类对比（集团）" subtitle="当期 vs 同期" extra="单位：万元">
          <EChart :option="incomeOpt" height="260px" />
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--unit">
        <Card title="单耗对比" subtitle="热/电/水单耗" extra="单位：每单位供暖量">
          <EChart :option="unitOpt" height="260px" />
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--coal">
        <Card title="标煤消耗量对比" subtitle="当期 vs 同期" extra="单位：吨标煤">
          <EChart :option="coalStdOpt" height="260px" />
          <div class="dashboard-table-wrapper">
            <Table :columns="coalStdColumns" :data="coalStdTableData" />
          </div>
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--complaint">
        <Card title="投诉量" subtitle="当日省市平台服务投诉量" extra="单位：件">
          <EChart :option="complaintOpt" height="260px" />
          <div class="dashboard-table-wrapper">
            <Table :columns="complaintColumns" :data="complaintTableData" />
          </div>
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--stock">
        <Card title="煤炭库存" subtitle="厂内/港口/在途（堆积）" extra="单位：吨">
          <EChart :option="coalStockOpt" height="300px" />
        </Card>
      </section>
    </main>

    <footer class="dashboard-footer">
      本页面为 ECharts 演示框架：可无缝替换为后端 API / 视图数据（如 average_temperature_data、sum_coal_inventory_data 等）。
    </footer>
  </div>
</template>

<script setup>
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'

// --- 仪表盘局部组件 ---
const Card = defineComponent({
  name: 'DashboardCard',
  props: {
    title: { type: String, required: true },
    subtitle: { type: String, default: '' },
    extra: { type: String, default: '' },
  },
  setup(props, { slots }) {
    return () =>
      h('section', { class: 'dashboard-card' }, [
        h('div', { class: 'dashboard-card__header' }, [
          h('div', { class: 'dashboard-card__header-left' }, [
            props.subtitle ? h('div', { class: 'dashboard-card__subtitle' }, props.subtitle) : null,
            h('h3', { class: 'dashboard-card__title' }, props.title),
          ]),
          props.extra ? h('div', { class: 'dashboard-card__extra' }, props.extra) : null,
        ]),
        h('div', { class: 'dashboard-card__body' }, (slots.default && slots.default()) || null),
      ])
  },
})

const Table = defineComponent({
  name: 'DashboardTable',
  props: {
    columns: {
      type: Array,
      default: () => [],
    },
    data: {
      type: Array,
      default: () => [],
    },
  },
  setup(props) {
    return () =>
      h('div', { class: 'dashboard-table' }, [
        h('table', null, [
          h(
            'thead',
            null,
            h(
              'tr',
              null,
              props.columns.map((column) =>
                h('th', { key: column }, column),
              ),
            ),
          ),
          h(
            'tbody',
            null,
            props.data.map((row, rowIndex) =>
              h(
                'tr',
                { key: rowIndex },
                row.map((cell, cellIndex) =>
                  h('td', { key: `${rowIndex}-${cellIndex}` }, cell ?? ''),
                ),
              ),
            ),
          ),
        ]),
      ])
  },
})

const EChart = defineComponent({
  name: 'DashboardEChart',
  props: {
    option: {
      type: Object,
      required: true,
    },
    height: {
      type: [Number, String],
      default: '260px',
    },
    autoresize: {
      type: Boolean,
      default: true,
    },
  },
  setup(props) {
    const container = ref(null)
    const styleHeight = computed(() =>
      typeof props.height === 'number' ? `${props.height}px` : props.height || '260px',
    )
    let chart = null

    const dispose = () => {
      if (chart) {
        chart.dispose()
        chart = null
      }
    }

    const ensureChart = () => {
      if (!container.value) return
      if (!window.echarts) {
        console.warn('ECharts 全局对象未加载，检查 index.html 是否引入 CDN 脚本')
        return
      }
      if (!chart) {
        chart = window.echarts.init(container.value)
      }
      if (props.option) {
        chart.setOption(props.option, true)
      }
    }

    const handleResize = () => {
      if (chart) {
        chart.resize()
      }
    }

    onMounted(() => {
      ensureChart()
      if (props.autoresize) {
        window.addEventListener('resize', handleResize)
      }
    })

    onBeforeUnmount(() => {
      if (props.autoresize) {
        window.removeEventListener('resize', handleResize)
      }
      dispose()
    })

    watch(
      () => props.option,
      () => {
        ensureChart()
      },
      { deep: true, immediate: true },
    )

    return () =>
      h('div', {
        ref: container,
        class: 'dashboard-chart',
        style: { height: styleHeight.value },
      })
  },
})

// --- 通用工具函数 ---
const fmt = (date) => date.toISOString().slice(0, 10)

// --- 日期与摘要指标 ---
const today = new Date()
const todayText = fmt(today)

const bizDate = new Date(today)
bizDate.setDate(bizDate.getDate() - 1)
const bizDateText = fmt(bizDate)

// --- 模拟数据（后续可替换为后端数据源） ---
const tempDates = Array.from({ length: 7 }, (_, index) => {
  const point = new Date(bizDate)
  point.setDate(point.getDate() - 3 + index)
  return fmt(point)
})
const tempNow = [14.2, 14.1, 14.4, 14.6, 15.6, 16.3, 16.9]
const tempPeer = [12.9, 12.5, 12.2, 12.8, 13.4, 13.9, 14.1]

const orgs7 = ['集团全口径', '主城区', '金州热电', '北方热电', '金普热电', '庄河环海', '研究院']
const marginData = orgs7.map((org, index) => ({
  org,
  direct: 1000 - index * 60,
  coal: 520 - index * 30,
  materials: 80 - index * 5,
  margin: 400 - index * 20,
  margin_cmp_coal: 430 - index * 18,
}))

const incomeCat = ['暖收入', '售电收入', '售高温水收入', '售汽收入']
const incomeNow = [600, 240, 120, 80]
const incomePeer = [560, 260, 110, 70]

const orgs6 = ['主城区', '金州热电', '北方热电', '金普热电', '庄河环海', '研究院']
const unitHeat = orgs6.map((org, index) => ({
  org,
  heat: 0.95 + index * 0.03,
  elec: 0.42 + index * 0.02,
  water: 0.21 + index * 0.015,
}))

const coalStdOrgs = ['集团全口径', '主城区', '金州热电', '北方热电', '金普热电', '庄河环海']
const coalStdNow = [980, 420, 160, 180, 120, 100]
const coalStdPeer = [1020, 440, 150, 190, 130, 90]

const complaintsNow = orgs7.map((org, index) => ({
  org,
  count: 30 - index * 3,
}))

const stockOrgs = ['北海热电厂', '香海热电厂', '金州热电', '北方热电', '金普热电', '庄河环海']
const stockData = stockOrgs.map((org, index) => ({
  org,
  inPlant: 30000 - index * 2000,
  inPort: 10000 - index * 800,
  inTransit: 6000 - index * 500,
}))

// --- 图表配置构造 ---
const useTempOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['当期', '同期'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: tempDates },
  yAxis: { type: 'value', name: '℃' },
  series: [
    { name: '当期', type: 'line', smooth: true, data: tempNow },
    { name: '同期', type: 'line', smooth: true, data: tempPeer },
  ],
})

const useMarginOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['直接收入', '煤成本', '可计量辅材成本', '边际利润', '可比煤价边际利润'] },
  grid: { left: 40, right: 20, top: 40, bottom: 60 },
  xAxis: { type: 'category', data: orgs7 },
  yAxis: { type: 'value', name: '万元' },
  series: [
    { name: '直接收入', type: 'bar', stack: 'base', data: marginData.map((item) => item.direct) },
    { name: '煤成本', type: 'bar', stack: 'base', data: marginData.map((item) => -item.coal) },
    { name: '可计量辅材成本', type: 'bar', stack: 'base', data: marginData.map((item) => -item.materials) },
    { name: '边际利润', type: 'line', data: marginData.map((item) => item.margin) },
    { name: '可比煤价边际利润', type: 'line', data: marginData.map((item) => item.margin_cmp_coal) },
  ],
})

const useIncomeCompareOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['当期', '同期'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: incomeCat },
  yAxis: { type: 'value', name: '万元' },
  series: [
    { name: '当期', type: 'bar', data: incomeNow },
    { name: '同期', type: 'bar', data: incomePeer },
  ],
})

const useUnitConsumptionOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['热单耗', '电单耗', '水单耗'] },
  grid: { left: 40, right: 20, top: 40, bottom: 60 },
  xAxis: { type: 'category', data: orgs6 },
  yAxis: { type: 'value', name: '单位/供暖量' },
  series: [
    { name: '热单耗', type: 'bar', data: unitHeat.map((item) => item.heat) },
    { name: '电单耗', type: 'bar', data: unitHeat.map((item) => item.elec) },
    { name: '水单耗', type: 'bar', data: unitHeat.map((item) => item.water) },
  ],
})

const useCoalStdOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['当期', '同期'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: coalStdOrgs },
  yAxis: { type: 'value', name: '吨标煤' },
  series: [
    { name: '当期', type: 'bar', data: coalStdNow },
    { name: '同期', type: 'bar', data: coalStdPeer },
  ],
})

const useComplaintsOption = () => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 20, bottom: 40 },
  xAxis: { type: 'category', data: orgs7 },
  yAxis: { type: 'value', name: '件' },
  series: [
    {
      name: '当日投诉量',
      type: 'bar',
      data: complaintsNow.map((item) => item.count),
      label: { show: true, position: 'top' },
    },
  ],
})

const useCoalStockOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['厂内存煤', '港口存煤', '在途煤炭'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: stockOrgs },
  yAxis: { type: 'value', name: '吨' },
  series: [
    { name: '厂内存煤', type: 'bar', stack: 'total', data: stockData.map((item) => item.inPlant) },
    { name: '港口存煤', type: 'bar', stack: 'total', data: stockData.map((item) => item.inPort) },
    { name: '在途煤炭', type: 'bar', stack: 'total', data: stockData.map((item) => item.inTransit) },
  ],
})

// --- 图表 option 实例 ---
const tempOpt = useTempOption()
const marginOpt = useMarginOption()
const incomeOpt = useIncomeCompareOption()
const unitOpt = useUnitConsumptionOption()
const coalStdOpt = useCoalStdOption()
const complaintOpt = useComplaintsOption()
const coalStockOpt = useCoalStockOption()

// --- 表格列与数据 ---
const temperatureColumns = ['日期', '当期(℃)', '同期(℃)']
const temperatureTableData = tempDates.map((date, index) => [date, tempNow[index], tempPeer[index]])

const marginColumns = ['单位', '直接收入', '煤成本', '可计量辅材', '边际利润', '可比煤价边际']
const marginTableData = marginData.map((item) => [
  item.org,
  item.direct,
  item.coal,
  item.materials,
  item.margin,
  item.margin_cmp_coal,
])

const coalStdColumns = ['单位', '当期', '同期', '差值']
const coalStdTableData = coalStdOrgs.map((org, index) => [
  org,
  coalStdNow[index],
  coalStdPeer[index],
  coalStdNow[index] - coalStdPeer[index],
])

const complaintColumns = ['单位', '当日投诉量']
const complaintTableData = complaintsNow.map((item) => [item.org, item.count])

// --- 顶部指标展示 ---
const averageTemp = (tempNow.reduce((sum, value) => sum + value, 0) / tempNow.length).toFixed(1)
const marginHeadline = marginData[0] ? marginData[0].margin : 0
const coalStdHeadline = coalStdNow[0] ?? 0
const complaintsHeadline = complaintsNow[0] ? complaintsNow[0].count : 0
</script>

<style scoped>
.dashboard-page {
  min-height: 100vh;
  background: #f8fafc;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

@media (min-width: 768px) {
  .dashboard-page {
    padding: 32px;
  }
}

.dashboard-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

@media (min-width: 768px) {
  .dashboard-header {
    flex-direction: row;
    align-items: flex-end;
    justify-content: space-between;
  }
}

.dashboard-header__titles {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dashboard-header__title {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1f2937;
}

@media (min-width: 1024px) {
  .dashboard-header__title {
    font-size: 32px;
  }
}

.dashboard-header__subtitle {
  font-size: 14px;
  color: #64748b;
}

.dashboard-header__meta {
  font-size: 14px;
  color: #64748b;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
}

@media (min-width: 768px) {
  .dashboard-header__meta {
    text-align: right;
  }
}

.dashboard-summary {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 28px;
}

@media (min-width: 640px) {
  .dashboard-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .dashboard-summary {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.summary-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 24px;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 120px;
  justify-content: space-between;
}

.summary-card__label {
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}

.summary-card__value {
  font-size: 26px;
  font-weight: 600;
  color: #0f172a;
}

.summary-card--gradient {
  background: linear-gradient(135deg, #1f2937, #475569);
  border: none;
  color: #ffffff;
  box-shadow: 0 20px 36px rgba(15, 23, 42, 0.18);
}

.summary-card--gradient .summary-card__label {
  color: rgba(248, 250, 252, 0.8);
}

.summary-card--gradient .summary-card__value {
  color: #ffffff;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}

.dashboard-grid__item {
  min-width: 0;
}

@media (min-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: repeat(12, minmax(0, 1fr));
  }

  .dashboard-grid__item--temp {
    grid-column: span 5;
  }

  .dashboard-grid__item--margin {
    grid-column: span 7;
  }

  .dashboard-grid__item--income {
    grid-column: span 4;
  }

  .dashboard-grid__item--unit {
    grid-column: span 8;
  }

  .dashboard-grid__item--coal {
    grid-column: span 6;
  }

  .dashboard-grid__item--complaint {
    grid-column: span 6;
  }

  .dashboard-grid__item--stock {
    grid-column: span 12;
  }
}

.dashboard-card {
  background: #ffffff;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: 100%;
}

.dashboard-card__header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 640px) {
  .dashboard-card__header {
    flex-direction: row;
    align-items: flex-start;
    justify-content: space-between;
  }
}

.dashboard-card__header-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dashboard-card__subtitle {
  font-size: 13px;
  color: #64748b;
}

.dashboard-card__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}

.dashboard-card__extra {
  font-size: 12px;
  color: #94a3b8;
}

.dashboard-card__body {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dashboard-chart {
  width: 100%;
}

.dashboard-table-wrapper {
  margin-top: 8px;
}

.dashboard-table {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
}

.dashboard-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  color: #1f2937;
}

.dashboard-table th {
  background: #eef2f6;
  color: #475569;
  font-weight: 600;
  padding: 10px 12px;
  text-align: left;
  white-space: nowrap;
}

.dashboard-table td {
  padding: 10px 12px;
  white-space: nowrap;
  border-top: 1px solid #e2e8f0;
}

.dashboard-table tr:hover td {
  background: #f8fafc;
}

.dashboard-footer {
  margin-top: 32px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}
</style>
