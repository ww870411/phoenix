<template>
  <div class="dashboard-page" :style="pageStyles">
    <header class="dashboard-header">
      <div class="dashboard-header__info">
        <div class="dashboard-header__titles">
          <div class="dashboard-header__title">大连洁净能源集团生产日报</div>
          <div class="dashboard-header__subtitle">Daily Production Report &amp; Dashboard</div>
        </div>
      </div>
      <div class="dashboard-header__actions">
        <label class="dashboard-header__checkbox" title="开启后返回详细求值轨迹">
          <input type="checkbox" v-model="traceEnabled" />
          <span>Trace</span>
        </label>
        <label class="dashboard-header__date-group" title="业务日期">
          <span>业务日期：</span>
          <input type="date" v-model="bizDateInput" />
          <span class="dashboard-header__date-hint" v-if="effectiveBizDate">当前：{{ effectiveBizDate }}</span>
          <span class="dashboard-header__date-hint" v-else>当前：regular</span>
        </label>
      </div>
    </header>

    <section class="dashboard-summary">
      <div class="summary-card summary-card--primary">
        <div class="summary-card__icon summary-card__icon--sunrise" aria-hidden="true"></div>
        <div class="summary-card__meta">
          <div class="summary-card__label">平均气温（7日当期）</div>
          <div class="summary-card__value">{{ averageTemp }}℃</div>
        </div>
      </div>
      <div class="summary-card summary-card--success">
        <div class="summary-card__icon summary-card__icon--profit" aria-hidden="true"></div>
        <div class="summary-card__meta">
          <div class="summary-card__label">集团全口径可比煤价边际利润</div>
          <div class="summary-card__value">{{ marginHeadline }} 万元</div>
        </div>
      </div>
      <div class="summary-card summary-card--warning">
        <div class="summary-card__icon summary-card__icon--coal" aria-hidden="true"></div>
        <div class="summary-card__meta">
          <div class="summary-card__label">集团标煤消耗（当期）</div>
          <div class="summary-card__value">{{ coalStdHeadline }} 吨标煤</div>
        </div>
      </div>
      <div class="summary-card summary-card--danger">
        <div class="summary-card__icon summary-card__icon--complaint" aria-hidden="true"></div>
        <div class="summary-card__meta">
          <div class="summary-card__label">集团当日投诉量</div>
          <div class="summary-card__value">{{ complaintsHeadline }} 件</div>
        </div>
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
import { computed, defineComponent, h, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { getDashboardData } from '../services/api'

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
    const hasColumns = computed(() => Array.isArray(props.columns) && props.columns.length > 0)
    const hasData = computed(() => Array.isArray(props.data) && props.data.length > 0)

    const isNumericValue = (value) => {
      if (typeof value === 'number') {
        return Number.isFinite(value)
      }
      if (typeof value === 'string') {
        const trimmed = value.trim()
        if (!trimmed) return false
        const parsed = Number(trimmed.replace(/,/g, ''))
        return Number.isFinite(parsed)
      }
      return false
    }

    const tableInlineStyle = {
      width: '100%',
      borderCollapse: 'collapse',
      borderSpacing: '0',
      borderWidth: '1px',
      borderStyle: 'solid',
      borderColor: 'rgba(148, 163, 184, 0.35)',
    }
    const headerCellInlineStyle = {
      borderWidth: '1px',
      borderStyle: 'solid',
      borderColor: 'rgba(148, 163, 184, 0.35)',
      textAlign: 'center',
      verticalAlign: 'middle',
    }
    const emptyCellInlineStyle = {
      borderWidth: '1px',
      borderStyle: 'solid',
      borderColor: 'rgba(226, 232, 240, 0.9)',
      textAlign: 'center',
      verticalAlign: 'middle',
    }

    return () =>
      h(
        'div',
        {
          class: 'dashboard-table',
          style: {
            width: '100%',
          },
        },
        [
          h('table', { style: tableInlineStyle }, [
            hasColumns.value
              ? h(
                'thead',
                null,
                h(
                  'tr',
                  null,
                  props.columns.map((column) =>
                    h(
                      'th',
                      {
                        key: column,
                        style: headerCellInlineStyle,
                      },
                      column,
                    ),
                  ),
                ),
              )
            : null,
          hasData.value
            ? h(
                'tbody',
                null,
                props.data.map((row, rowIndex) =>
                  h(
                    'tr',
                    { key: rowIndex },
                    row.map((cell, cellIndex) => {
                      const numeric = isNumericValue(cell) && cell !== ''
                      const display =
                        numeric && typeof cell === 'number'
                          ? cell.toLocaleString('zh-CN')
                          : cell ?? '—'
                      return h(
                        'td',
                        {
                          key: `${rowIndex}-${cellIndex}`,
                          class: {
                            'dashboard-table__numeric': numeric,
                            'dashboard-table__first': cellIndex === 0,
                          },
                          style: {
                            borderWidth: '1px',
                            borderStyle: 'solid',
                            borderColor:
                              cellIndex === 0
                                ? 'rgba(148, 163, 184, 0.35)'
                                : 'rgba(226, 232, 240, 0.9)',
                            textAlign: 'center',
                            verticalAlign: 'middle',
                          },
                        },
                        display,
                      )
                    }),
                  ),
                ),
              )
            : h('tbody', null, [
                h('tr', null, [
                  h(
                    'td',
                    {
                      class: 'dashboard-table__empty',
                      colspan: hasColumns.value ? props.columns.length : 1,
                      style: emptyCellInlineStyle,
                    },
                    '暂无数据',
                  ),
                ]),
              ]),
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
const defaultBizDate = (() => {
  const bizDate = new Date(today)
  bizDate.setDate(bizDate.getDate() - 1)
  return fmt(bizDate)
})()

// --- 数据看板顶部交互占位 ---
const traceEnabled = ref(false)
const bizDateInput = ref('')
const effectiveBizDate = computed(() => {
  const value = bizDateInput.value
  return typeof value === 'string' && value.trim() ? value.trim() : ''
})

const projectKey = 'daily_report_25_26'
let suppressDashboardWatch = false

const dashboardData = reactive({
  meta: {
    projectKey,
    showDate: '',
    pushDate: '',
    generatedAt: '',
  },
  sections: {},
})

async function loadDashboardData(showDate = '') {
  suppressDashboardWatch = true
  try {
    const payload = await getDashboardData(projectKey, { showDate })
    if (payload?.push_date) {
      bizDateInput.value = payload.push_date
    } else if (!bizDateInput.value) {
      bizDateInput.value = defaultBizDate
    }
    if (payload && typeof payload === 'object') {
      dashboardData.meta.showDate = typeof payload.show_date === 'string' ? payload.show_date : ''
      dashboardData.meta.pushDate = typeof payload.push_date === 'string' ? payload.push_date : ''
      dashboardData.meta.generatedAt =
        typeof payload.generated_at === 'string' ? payload.generated_at : ''

      const rawSections =
        payload.data && typeof payload.data === 'object' ? { ...payload.data } : {}
      if (typeof rawSections.push_date === 'string' && !dashboardData.meta.pushDate) {
        dashboardData.meta.pushDate = rawSections.push_date
      }
      delete rawSections.push_date
      if (Object.prototype.hasOwnProperty.call(rawSections, '展示日期')) {
        delete rawSections['展示日期']
      }
      dashboardData.sections = rawSections
    }
    // TODO: 数据映射逻辑将在接入真实数据时实现
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    console.error('[dashboard] 数据加载失败', message)
    if (!bizDateInput.value) {
      bizDateInput.value = defaultBizDate
    }
  } finally {
    suppressDashboardWatch = false
  }
}

onMounted(() => {
  loadDashboardData()
})

watch(
  () => bizDateInput.value,
  (value, oldValue) => {
    if (suppressDashboardWatch) return
    if (value === oldValue) return
    loadDashboardData(value || '')
  },
)

const temperatureSection = computed(() => {
  const section = dashboardData.sections?.['1.逐小时气温']
  return section && typeof section === 'object' ? section : {}
})

const calcAverageFromList = (values) => {
  if (!Array.isArray(values) || !values.length) return null
  const numbers = values.filter((item) => typeof item === 'number' && Number.isFinite(item))
  if (!numbers.length) return null
  const sum = numbers.reduce((acc, item) => acc + item, 0)
  return Number((sum / numbers.length).toFixed(2))
}

const temperatureSeries = computed(() => {
  const section = temperatureSection.value
  const mainBucket =
    section && typeof section === 'object' && typeof section['本期'] === 'object'
      ? section['本期']
      : {}
  const peerBucket =
    section && typeof section === 'object' && typeof section['同期'] === 'object'
      ? section['同期']
      : {}

  const mainLabels = Object.keys(mainBucket || {}).sort()
  const peerLabels = Object.keys(peerBucket || {}).sort()
  const labels = mainLabels.length ? mainLabels : peerLabels

  const mainAverages = labels.map((label) => calcAverageFromList(mainBucket[label]))
  const peerAverages = labels.map((_, index) => {
    const peerKey = peerLabels[index]
    return calcAverageFromList(peerBucket[peerKey])
  })

  const tableRows = labels.map((label, index) => [
    label,
    Number.isFinite(mainAverages[index]) ? mainAverages[index] : '—',
    Number.isFinite(peerAverages[index]) ? peerAverages[index] : '—',
  ])

  return {
    labels,
    mainAverages,
    peerAverages,
    mainChart: mainAverages.map((value) => (Number.isFinite(value) ? value : 0)),
    peerChart: peerAverages.map((value) => (Number.isFinite(value) ? value : 0)),
    tableRows,
  }
})

// --- 模拟数据（后续可替换为后端数据源） ---

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
const pushDateValue = computed(() => dashboardData.meta.pushDate || dashboardData.meta.showDate || '')

const useTempOption = (series, highlightDate) => {
  const highlightExists = highlightDate && series.labels.includes(highlightDate)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['当期', '同期'] },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: series.labels },
    yAxis: { type: 'value', name: '℃' },
    series: [
      {
        name: '当期',
        type: 'line',
        smooth: true,
        data: series.mainChart,
        markLine: highlightExists
          ? {
              symbol: 'none',
              lineStyle: { type: 'dashed', color: '#f59e0b' },
              label: {
                show: true,
                position: 'end',
                formatter: '业务日期',
                color: '#f59e0b',
              },
              data: [{ xAxis: highlightDate }],
            }
          : undefined,
      },
      { name: '同期', type: 'line', smooth: true, data: series.peerChart },
    ],
  }
}

const useMarginOption = () => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['直接收入', '煤成本', '可计量辅材成本', '可比煤价边际利润'] },
  grid: { left: 40, right: 20, top: 40, bottom: 60 },
  xAxis: { type: 'category', data: orgs7 },
  yAxis: { type: 'value', name: '万元' },
  series: [
    { name: '直接收入', type: 'bar', stack: 'base', data: marginData.map((item) => item.direct) },
    { name: '煤成本', type: 'bar', stack: 'base', data: marginData.map((item) => -item.coal) },
    { name: '可计量辅材成本', type: 'bar', stack: 'base', data: marginData.map((item) => -item.materials) },
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
const tempOpt = computed(() => useTempOption(temperatureSeries.value, pushDateValue.value))
const marginOpt = useMarginOption()
const incomeOpt = useIncomeCompareOption()
const unitOpt = useUnitConsumptionOption()
const coalStdOpt = useCoalStdOption()
const complaintOpt = useComplaintsOption()
const coalStockOpt = useCoalStockOption()

// --- 表格列与数据 ---
const temperatureColumns = ['日期', '当期(℃)', '同期(℃)']
const temperatureTableData = computed(() => temperatureSeries.value.tableRows)

const marginColumns = ['单位', '直接收入', '煤成本', '可计量辅材', '可比煤价边际']
const marginTableData = marginData.map((item) => [
  item.org,
  item.direct,
  item.coal,
  item.materials,
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
const averageTemp = computed(() => {
  const pushDate = dashboardData.meta.pushDate || dashboardData.meta.showDate || ''
  const mainBucket =
    temperatureSection.value && typeof temperatureSection.value === 'object'
      ? temperatureSection.value['本期']
      : null
  if (!pushDate || !mainBucket || typeof mainBucket !== 'object') {
    return '—'
  }
  const values = mainBucket[pushDate]
  const avg = calcAverageFromList(values)
  if (avg === null || Number.isNaN(avg)) {
    return '—'
  }
  return avg.toFixed(2)
})
const marginHeadline = marginData[0] ? marginData[0].margin : 0
const coalStdHeadline = coalStdNow[0] ?? 0
const complaintsHeadline = complaintsNow[0] ? complaintsNow[0].count : 0

const chartPalette = ref(['#2563eb', '#38bdf8', '#10b981', '#f97316', '#facc15', '#ec4899'])

const pageStyles = computed(() => {
  const colors = chartPalette.value
  const primary = colors[0] || '#2563eb'
  const secondary = colors[1] || '#38bdf8'
  const accent = colors[3] || '#f97316'
  return {
    '--dashboard-table-border': `linear-gradient(90deg, ${primary}, ${accent})`,
    '--dashboard-table-header': `linear-gradient(135deg, ${primary}1A, ${secondary}0F)`,
    '--dashboard-table-hover': `${primary}12`,
    '--dashboard-border-color': `${primary}30`,
  }
})

onMounted(() => {
  const candidate = window.echarts?.config?.color
  if (Array.isArray(candidate) && candidate.length) {
    chartPalette.value = candidate
  }
})
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

.dashboard-header__info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 768px) {
  .dashboard-header__info {
    flex-direction: row;
    align-items: flex-end;
    gap: 24px;
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

.dashboard-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.6);
  padding: 12px 16px;
  border-radius: 12px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
}

.dashboard-header__checkbox {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #0f172a;
}

.dashboard-header__date-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #0f172a;
}

.dashboard-header__date-group input[type='date'] {
  border: 1px solid #cbd5f5;
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 14px;
  background-color: #ffffff;
  color: #0f172a;
}

.dashboard-header__date-group input[type='date']:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.dashboard-header__date-hint {
  font-size: 12px;
  color: #64748b;
}

.dashboard-summary {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  margin-bottom: 32px;
  position: relative;
  z-index: 1;
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
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 18px;
  color: #ffffff;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.16);
}

.summary-card::after {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.08;
  background: radial-gradient(circle at 20% 20%, #ffffff, transparent 60%);
}

.summary-card__icon {
  z-index: 1;
  width: 54px;
  height: 54px;
  border-radius: 18px;
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: inherit;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.32);
}

.summary-card__icon::before {
  content: '';
  display: block;
  width: 32px;
  height: 32px;
  mask-size: contain;
  mask-repeat: no-repeat;
  background-color: currentColor;
}

.summary-card__icon--sunrise::before {
  mask-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M11 8V2h2v6Zm6.36 1.64L20.5 6.5l1.41 1.41l-3.13 3.15ZM4 13h16v2H4Zm-.91-4.09L4.5 6.5l3.15 3.14L6.24 10.5ZM12 18a5 5 0 0 1-5-5h10a5 5 0 0 1-5 5Zm-6 3h12v2H6Z"/></svg>');
}

.summary-card__icon--profit::before {
  mask-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M5 3h14v2H5Zm0 4h10v2H5Zm0 4h7v2H5Zm0 4h4v2H5Zm0 4h7v2H5Zm10.5-5q-1.4 0-2.7.75t-1.9 2.1l1.85.75q.35-1.05 1.23-1.65T15.5 15q1.75 0 2.88 1.1Q19.5 17.25 19.5 19q0 1.75-1.12 2.88Q17.25 23 15.5 23q-1.35 0-2.27-.65T11.35 20h-2q.35 1.95 1.82 3.225Q12.65 24.5 15.5 24.5q2.3 0 3.9-1.6t1.6-3.9q0-2.3-1.6-3.9t-3.9-1.6Z"/></svg>');
}

.summary-card__icon--coal::before {
  mask-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="m13 22-10-2l2-4l-2-4l10-2l10 2l-2 4l2 4l-10 2Zm0-2.15L18.15 18L19 16l-1.85-1.85L13 13.15l-4.15 1L7 16l1.85 1.85Z"/></svg>');
}

.summary-card__icon--complaint::before {
  mask-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M12 12q-.825 0-1.412-.587T10 10t.588-1.413T12 8t1.413.587T14 10t-.587 1.413T12 12Zm0 8.5q1.35 0 2.612-.387t2.301-1.088l2.087.538l-.55-2.05q.9-1.05 1.4-2.35T20.85 12q0-3.2-2.3-5.5T13.05 4.3L12 2l-1.05 2.3q-3.2.2-5.5 2.5T3.15 12q0 1.625.5 2.937T5.05 17l-.55 2.05l2.087-.538q1.05.7 2.312 1.088T12 20.5Z"/></svg>');
}

.summary-card__meta {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-card__label {
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.78;
}

.summary-card__value {
  font-size: 28px;
  font-weight: 700;
}

.summary-card--primary {
  background: linear-gradient(135deg, #2563eb, #60a5fa);
}

.summary-card--success {
  background: linear-gradient(135deg, #10b981, #34d399);
}

.summary-card--warning {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
}

.summary-card--danger {
  background: linear-gradient(135deg, #ef4444, #fb7185);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

.dashboard-grid__item {
  min-width: 0;
  position: relative;
  z-index: 0;
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
  border: 1px solid rgba(148, 163, 184, 0.28);
  box-shadow: 0 22px 36px rgba(15, 23, 42, 0.12);
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
  width: 100%;
}

.dashboard-table {
  width: 100%;
  display: block;
  overflow-x: auto;
  border-radius: 16px;
  border: 1px solid transparent;
  background: #ffffff;
  border-image: var(
      --dashboard-table-border,
      linear-gradient(90deg, #2563eb, #f97316)
    )
    1;
  box-shadow: 0 16px 28px rgba(15, 23, 42, 0.12);
}

.dashboard-table table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  table-layout: fixed;
  font-size: 13px;
  color: #0f172a;
  background: #ffffff;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.35);
  margin: 0;
}

.dashboard-table thead {
  background: var(
    --dashboard-table-header,
    linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(56, 189, 248, 0.05))
  );
}

.dashboard-table th {
  color: #1d4ed8;
  font-weight: 600;
  padding: 14px 18px;
  text-align: center;
  vertical-align: middle;
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.dashboard-table td {
  padding: 14px 18px;
  text-align: center;
  vertical-align: middle;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: #ffffff;
}

.dashboard-table__numeric {
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.dashboard-table__first {
  text-align: center;
  color: #1f2937;
  font-weight: 600;
}

.dashboard-table tbody td:not(.dashboard-table__first) {
  color: #0f172a;
}

.dashboard-table tbody tr:nth-child(even) td {
  background: rgba(248, 250, 252, 0.7);
}

.dashboard-table tr:hover td {
  background: var(--dashboard-table-hover, rgba(37, 99, 235, 0.08));
}

.dashboard-table__empty {
  text-align: center;
  color: #64748b;
  padding: 24px 16px;
}

.dashboard-footer {
  margin-top: 32px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}
</style>
