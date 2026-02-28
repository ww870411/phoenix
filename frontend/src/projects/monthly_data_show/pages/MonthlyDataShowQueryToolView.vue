<template>
  <div class="monthly-query-page">
    <AppHeader />
    <main class="monthly-query-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card">
        <h2>月报数据查询工具</h2>
        <p class="sub">按来源月份、业务日期、口径与指标查询 month_data_show 表，并查看基础汇总。</p>
      </section>

      <section class="card">
        <h3>筛选条件</h3>
        <div class="filter-grid">
          <label class="field">
            <span>业务月份起</span>
            <input type="month" v-model="filters.dateMonthFrom" />
          </label>
          <label class="field">
            <span>业务月份止</span>
            <input type="month" v-model="filters.dateMonthTo" />
          </label>
          <label class="field">
            <span>来源月份起</span>
            <input type="month" v-model="filters.reportMonthFrom" />
          </label>
          <label class="field">
            <span>来源月份止</span>
            <input type="month" v-model="filters.reportMonthTo" />
          </label>
          <div class="field span-full">
            <div class="field-head">
              <span>口径（可多选）</span>
              <div class="inline-actions">
                <button class="btn mini" type="button" @click="toggleAllCompanies(true)">全选</button>
                <button class="btn mini" type="button" @click="toggleAllCompanies(false)">全不选</button>
              </div>
            </div>
            <div class="check-list company-list">
              <label class="check-item" v-for="value in orderedCompanies" :key="value">
                <input type="checkbox" :value="value" v-model="filters.companies" />
                <span>{{ value }}</span>
                <span v-if="getSelectionOrder(filters.companies, value) > 0" class="order-badge">
                  {{ getSelectionOrder(filters.companies, value) }}
                </span>
              </label>
            </div>
          </div>
          <div class="field span-full">
            <div class="field-head">
              <span>指标（可多选）</span>
              <div class="inline-actions">
                <button class="btn mini" type="button" @click="toggleAllItems(true)">全选</button>
                <button class="btn mini" type="button" @click="toggleAllItems(false)">全不选</button>
              </div>
            </div>
            <div class="check-list sections compact">
              <div class="section-block" v-for="section in itemSections" :key="section.key">
                <div class="section-title">{{ section.title }}</div>
                <div class="section-items">
                  <label class="check-item" v-for="value in section.items" :key="`${section.key}-${value}`">
                    <input type="checkbox" :value="value" v-model="filters.items" />
                    <span>{{ value }}</span>
                    <span v-if="getSelectionOrder(filters.items, value) > 0" class="order-badge">
                      {{ getSelectionOrder(filters.items, value) }}
                    </span>
                  </label>
                  <span class="section-empty" v-if="!section.items.length">暂无</span>
                </div>
              </div>
            </div>
          </div>
          <div class="field span-full">
            <div class="inline-four">
              <div class="inline-col">
                <div class="field-head">
                  <span>期间（可多选）</span>
                  <div class="inline-actions">
                    <button class="btn mini" type="button" @click="toggleAllPeriods(true)">全选</button>
                    <button class="btn mini" type="button" @click="toggleAllPeriods(false)">全不选</button>
                  </div>
                </div>
                <div class="check-list slim">
                  <label class="check-item" v-for="value in options.periods" :key="value">
                    <input type="checkbox" :value="value" v-model="filters.periods" />
                    <span>{{ value }}</span>
                    <span v-if="getSelectionOrder(filters.periods, value) > 0" class="order-badge">
                      {{ getSelectionOrder(filters.periods, value) }}
                    </span>
                  </label>
                </div>
              </div>
              <div class="inline-col">
                <div class="field-head">
                  <span>类型（可多选）</span>
                  <div class="inline-actions">
                    <button class="btn mini" type="button" @click="toggleAllTypes(true)">全选</button>
                    <button class="btn mini" type="button" @click="toggleAllTypes(false)">全不选</button>
                  </div>
                </div>
                <div class="check-list slim">
                  <label class="check-item" v-for="value in orderedTypes" :key="value">
                    <input type="checkbox" :value="value" v-model="filters.types" />
                    <span>{{ value }}</span>
                    <span v-if="getSelectionOrder(filters.types, value) > 0" class="order-badge">
                      {{ getSelectionOrder(filters.types, value) }}
                    </span>
                  </label>
                </div>
              </div>
              <div class="inline-col">
                <div class="field-head">
                  <span>数据层次顺序</span>
                  <div class="inline-actions">
                    <button class="btn mini" type="button" @click="resetOrderFields">重置默认</button>
                  </div>
                </div>
                <div class="check-list slim">
                  <label class="check-item" v-for="layer in layerOptions" :key="layer.value">
                    <input type="checkbox" :value="layer.value" v-model="filters.orderFields" />
                    <span>{{ layer.label }}</span>
                    <span v-if="getSelectionOrder(filters.orderFields, layer.value) > 0" class="order-badge">
                      {{ getSelectionOrder(filters.orderFields, layer.value) }}
                    </span>
                  </label>
                </div>
              </div>
              <div class="inline-col">
                <div class="field-head">
                  <span>聚合开关</span>
                </div>
                <div class="switch-row switch-full">
                  <label class="switch-item">
                    <input type="checkbox" v-model="filters.aggregateCompanies" />
                    <span>{{ filters.aggregateCompanies ? '已聚合（显示聚合口径）' : '不聚合口径（逐口径列出）' }}</span>
                  </label>
                </div>
                <div class="switch-row switch-full">
                  <label class="switch-item">
                    <input type="checkbox" v-model="filters.aggregateMonths" />
                    <span>{{ filters.aggregateMonths ? '已聚合期间月份（区间汇总）' : '不聚合期间月份（逐月列出）' }}</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
        <p class="sub" v-if="!filters.companies.length || !filters.items.length || !filters.periods.length || !filters.types.length">
          口径、指标、期间、类型均需至少各选 1 项；若任一为空将不提取任何数据。
        </p>
        <div class="actions">
          <button class="btn primary" type="button" :disabled="loading || !filters.companies.length || !filters.items.length || !filters.periods.length || !filters.types.length" @click="runQuery(true)">
            {{ loading ? '查询中...' : '查询' }}
          </button>
          <button class="btn" type="button" :disabled="loading" @click="resetFilters">重置</button>
        </div>
      </section>

      <section class="card">
        <h3>汇总信息</h3>
        <div class="summary-grid">
          <div class="summary-item">
            <div class="label">总记录数</div>
            <div class="value">{{ summary.totalRows }}</div>
          </div>
          <div class="summary-item">
            <div class="label">数值非空</div>
            <div class="value">{{ summary.valueNonNullRows }}</div>
          </div>
          <div class="summary-item">
            <div class="label">数值空值</div>
            <div class="value">{{ summary.valueNullRows }}</div>
          </div>
        </div>
      </section>

      <section class="card">
        <div class="result-head">
          <h3>查询结果</h3>
          <div class="result-actions">
            <button class="btn" type="button" :disabled="loading || !rows.length" @click="downloadXlsx">
              导出 XLSX
            </button>
          </div>
          <div class="pager">
            <button class="btn" type="button" :disabled="loading || offset <= 0" @click="prevPage">上一页</button>
            <span>第 {{ pageNumber }} 页 / 共 {{ totalPages }} 页</span>
            <button class="btn" type="button" :disabled="loading || !hasNextPage" @click="nextPage">下一页</button>
          </div>
        </div>
        <p class="sub">共 {{ total }} 条，当前显示 {{ rows.length }} 条（每页 {{ limit }} 条）。</p>
        <div v-if="loading" class="empty">数据加载中...</div>
        <div v-else-if="errorMessage" class="empty error">{{ errorMessage }}</div>
        <div v-else-if="!hasSearched" class="empty">请先设置筛选条件并点击“查询”。</div>
        <div v-else-if="!rows.length" class="empty">暂无数据</div>
        <div v-else class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>company</th>
                <th>item</th>
                <th>unit</th>
                <th>value</th>
                <th>date</th>
                <th>period</th>
                <th>type</th>
                <th>report_month</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in rows" :key="`${row.company}-${row.item}-${row.date}-${row.period}-${row.type}-${idx}`">
                <td>{{ row.company }}</td>
                <td>{{ row.item }}</td>
                <td>{{ row.unit || '—' }}</td>
                <td>{{ row.value == null ? 'NULL' : formatNumber(row.value) }}</td>
                <td>{{ row.date || '—' }}</td>
                <td>{{ row.period || '—' }}</td>
                <td>{{ row.type || '—' }}</td>
                <td>{{ row.report_month || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="hasSearched && comparisonRows.length" class="analysis-section">
          <h4>同比与环比（实时窗口）</h4>
          <p class="sub">
            当前月份：{{ comparisonLatestMonthLabel }}；同比月份：{{ comparisonYoYMonthLabel || '无' }}；环比月份：{{ comparisonMoMMonthLabel || '无' }}
          </p>
          <div class="viz-toolbar">
            <label class="viz-field">
              <span>展示口径</span>
              <select v-model="comparisonViewMode">
                <option value="yoy">同比</option>
                <option value="mom">环比</option>
              </select>
            </label>
            <label class="viz-field">
              <span>TopN 指标</span>
              <select v-model.number="comparisonTopN">
                <option :value="10">10</option>
                <option :value="15">15</option>
                <option :value="20">20</option>
                <option :value="30">30</option>
              </select>
            </label>
          </div>
          <div class="viz-grid">
            <div class="viz-card">
              <h5 class="viz-title-nowrap">热力图（纵轴=指标，横轴=口径）</h5>
              <div
                class="heatmap-grid"
                v-if="heatmapItems.length && heatmapCompanies.length"
                :style="heatmapGridStyle"
              >
                <div class="heatmap-header"></div>
                <div class="heatmap-header" v-for="company in heatmapCompanies" :key="`h-h-${company}`">{{ company }}</div>
                <template v-for="item in heatmapItems" :key="`h-r-${item}`">
                  <div class="heatmap-label">{{ item }}</div>
                  <div
                    v-for="company in heatmapCompanies"
                    :key="`h-c-${item}-${company}`"
                    class="heatmap-cell"
                    :style="heatmapCellStyle(item, company)"
                    :title="heatmapCellTitle(item, company)"
                  >
                    {{ heatmapCellText(item, company) }}
                  </div>
                </template>
              </div>
              <p v-else class="sub">暂无可视化样本</p>
            </div>
            <div class="viz-card">
              <h5>波动 TopN（绝对值）</h5>
              <div v-if="topChangeRows.length" class="bars-wrap">
                <div class="bar-row" v-for="row in topChangeRows" :key="`bar-${row.key}`">
                  <div class="bar-label">{{ row.company }} / {{ row.item }}</div>
                  <div class="bar-track">
                    <div class="bar-fill" :class="deltaClass(rateValue(row))" :style="{ width: `${Math.max(2, Math.round(barWidth(rateValue(row))))}%` }"></div>
                  </div>
                  <div class="bar-value" :class="deltaClass(rateValue(row))">{{ formatRate(rateValue(row)) }}</div>
                </div>
              </div>
              <p v-else class="sub">暂无可比较的波动序列</p>
            </div>
          </div>
          <div class="table-wrap">
            <table class="data-table compare-table">
              <thead>
                <tr>
                  <th>口径</th>
                  <th>指标</th>
                  <th>期间</th>
                  <th>类型</th>
                  <th>当前值</th>
                  <th>同比值</th>
                  <th>同比</th>
                  <th>环比值</th>
                  <th>环比</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in comparisonRows" :key="entry.key">
                  <td>{{ entry.company }}</td>
                  <td>{{ entry.item }}</td>
                  <td>{{ entry.period }}</td>
                  <td>{{ entry.type }}</td>
                  <td>{{ entry.currentValue == null ? 'NULL' : formatNumber(entry.currentValue) }}</td>
                  <td>{{ entry.yoyValue == null ? 'NULL' : formatNumber(entry.yoyValue) }}</td>
                  <td :class="deltaClass(entry.yoyRate)">{{ formatRate(entry.yoyRate) }}</td>
                  <td>{{ entry.momValue == null ? 'NULL' : formatNumber(entry.momValue) }}</td>
                  <td :class="deltaClass(entry.momRate)">{{ formatRate(entry.momRate) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-if="hasSearched && analysisInsights.length" class="analysis-section">
          <h4>专业分析要点</h4>
          <ul class="insight-list">
            <li v-for="(line, idx) in analysisInsights" :key="`insight-${idx}`">{{ line }}</li>
          </ul>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import * as XLSX from 'xlsx'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import {
  getMonthlyDataShowQueryOptions,
  queryMonthlyDataShow,
  queryMonthlyDataShowComparison,
} from '../../daily_report_25_26/services/api'

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '月报导入与查询', to: '/projects/monthly_data_show/pages' },
  { label: '月报数据查询工具', to: null },
])

const limit = 200
const offset = ref(0)
const total = ref(0)
const hasSearched = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const rows = ref([])
const summary = reactive({
  totalRows: 0,
  valueNonNullRows: 0,
  valueNullRows: 0,
  valueSum: 0,
})
const options = reactive({
  companies: [],
  items: [],
  periods: [],
  types: [],
})
const filters = reactive({
  dateMonthFrom: '',
  dateMonthTo: '',
  reportMonthFrom: '',
  reportMonthTo: '',
  companies: [],
  items: [],
  periods: ['month'],
  types: ['real'],
  orderMode: 'company_first',
  orderFields: ['company', 'item', 'period', 'type'],
  aggregateCompanies: false,
  aggregateMonths: false,
})
const layerOptions = [
  { value: 'company', label: '口径' },
  { value: 'item', label: '指标' },
  { value: 'period', label: '期间' },
  { value: 'type', label: '类型' },
]

const pageNumber = computed(() => Math.floor(offset.value / limit) + 1)
const totalPages = computed(() => Math.max(1, Math.ceil((total.value || 0) / limit)))
const hasNextPage = computed(() => offset.value + limit < total.value)
const COMPANY_ORDER = [
  '全口径',
  '主城区',
  '集团本部',
  '股份本部',
  '北海',
  '北海水炉',
  '香海',
  '供热公司',
  '金州',
  '北方',
  '金普',
  '庄河',
  '研究院',
  '主城区电锅炉',
]
const CALCULATED_ITEM_SET = new Set([
  '综合厂用电率',
  '发电标准煤耗率',
  '供电标准煤耗率',
  '供热标准煤耗率',
  '发电水耗率',
  '供热水耗率',
  '供暖热耗率',
  '供暖水耗率',
  '供暖电耗率',
  '发电设备利用率',
  '供热设备利用率',
  '入炉煤低位发热量',
  '发电厂用电率',
  '供热厂用电率',
  '全厂热效率',
  '热电比',
  '热分摊比',
  '供热用电率',
  '供暖标准煤耗率',
])
const AVERAGE_TEMPERATURE_ITEM = '平均气温'
const CONSTANT_ITEM_ORDER = ['发电设备容量', '锅炉设备容量']
const CONSTANT_ITEM_SET = new Set(CONSTANT_ITEM_ORDER)
const CALCULATED_ITEM_ORDER = [
  '综合厂用电率',
  '发电标准煤耗率',
  '供电标准煤耗率',
  '供热标准煤耗率',
  '发电水耗率',
  '供热水耗率',
  '供暖热耗率',
  '供暖水耗率',
  '供暖电耗率',
  '发电设备利用率',
  '供热设备利用率',
  '入炉煤低位发热量',
  '发电厂用电率',
  '供热厂用电率',
  '全厂热效率',
  '热电比',
  '热分摊比',
  '供热用电率',
  '供暖标准煤耗率',
]
const orderedCompanies = computed(() => {
  const orderMap = new Map(COMPANY_ORDER.map((name, idx) => [name, idx]))
  const input = Array.isArray(options.companies) ? options.companies : []
  return [...input].sort((a, b) => {
    const ai = orderMap.has(a) ? orderMap.get(a) : Number.MAX_SAFE_INTEGER
    const bi = orderMap.has(b) ? orderMap.get(b) : Number.MAX_SAFE_INTEGER
    if (ai !== bi) return ai - bi
    return String(a).localeCompare(String(b), 'zh-CN')
  })
})
const orderedItems = computed(() => {
  const input = Array.isArray(options.items) ? [...options.items] : []
  return input
    .map((name, index) => ({ name, index, key: buildItemOrderKey(name, index) }))
    .sort((a, b) => compareItemOrderKey(a.key, b.key))
    .map((x) => x.name)
})
const orderedTypes = computed(() => {
  const src = Array.isArray(options.types) ? [...options.types] : []
  return src.sort((a, b) => {
    const aa = String(a || '').toLowerCase()
    const bb = String(b || '').toLowerCase()
    if (aa === 'real' && bb !== 'real') return -1
    if (bb === 'real' && aa !== 'real') return 1
    return 0
  })
})
const itemSections = computed(() => {
  const currentBase = []
  const currentConstants = []
  const currentTail = []
  const sourceSet = new Set(orderedItems.value)
  for (const item of orderedItems.value) {
    if (CALCULATED_ITEM_SET.has(item)) continue
    if (item === AVERAGE_TEMPERATURE_ITEM) {
      currentTail.push(item)
      continue
    }
    if (CONSTANT_ITEM_SET.has(item)) {
      currentConstants.push(item)
    } else {
      currentBase.push(item)
    }
  }
  const constantOrderMap = new Map(CONSTANT_ITEM_ORDER.map((name, idx) => [name, idx]))
  const calculatedOrderMap = new Map(CALCULATED_ITEM_ORDER.map((name, idx) => [name, idx]))
  currentConstants.sort((a, b) => {
    const ai = constantOrderMap.has(a) ? constantOrderMap.get(a) : Number.MAX_SAFE_INTEGER
    const bi = constantOrderMap.has(b) ? constantOrderMap.get(b) : Number.MAX_SAFE_INTEGER
    if (ai !== bi) return ai - bi
    return String(a).localeCompare(String(b), 'zh-CN')
  })
  const calculated = [...CALCULATED_ITEM_ORDER]
  calculated.sort((a, b) => {
    const ai = calculatedOrderMap.has(a) ? calculatedOrderMap.get(a) : Number.MAX_SAFE_INTEGER
    const bi = calculatedOrderMap.has(b) ? calculatedOrderMap.get(b) : Number.MAX_SAFE_INTEGER
    if (ai !== bi) return ai - bi
    return String(a).localeCompare(String(b), 'zh-CN')
  })
  const current = [...currentBase, ...currentConstants, ...currentTail]
  const mergedCalculated = calculated.map((name) => (sourceSet.has(name) ? name : name))
  return [
    { key: 'current', title: '基本指标', items: current },
    { key: 'calculated', title: '计算指标（19项）', items: mergedCalculated },
  ]
})

const comparisonRows = ref([])
const comparisonViewMode = ref('yoy')
const comparisonTopN = ref(15)
const comparisonMeta = reactive({
  currentWindowLabel: '',
  yoyWindowLabel: '',
  momWindowLabel: '',
})
const comparisonLatestMonthLabel = computed(() => comparisonMeta.currentWindowLabel || '—')
const comparisonYoYMonthLabel = computed(() => comparisonMeta.yoyWindowLabel || '—')
const comparisonMoMMonthLabel = computed(() => comparisonMeta.momWindowLabel || '—')

const heatmapCompanies = computed(() => {
  const all = [...new Set(comparisonRows.value.map((row) => String(row.company || '')))].filter(Boolean)
  const orderMap = new Map(COMPANY_ORDER.map((name, idx) => [name, idx]))
  return all.sort((a, b) => {
    const ai = orderMap.has(a) ? orderMap.get(a) : Number.MAX_SAFE_INTEGER
    const bi = orderMap.has(b) ? orderMap.get(b) : Number.MAX_SAFE_INTEGER
    if (ai !== bi) return ai - bi
    return a.localeCompare(b, 'zh-CN')
  })
})

const heatmapItems = computed(() => {
  const scoreMap = new Map()
  for (const row of comparisonRows.value) {
    const key = String(row.item || '')
    if (!key) continue
    const rate = rateValue(row)
    if (rate == null) continue
    const prev = scoreMap.get(key) ?? 0
    scoreMap.set(key, Math.max(prev, Math.abs(rate)))
  }
  return [...scoreMap.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, Math.max(1, Number(comparisonTopN.value || 15)))
    .map((x) => x[0])
})

const heatmapValueMap = computed(() => {
  const map = new Map()
  for (const row of comparisonRows.value) {
    const item = String(row.item || '')
    const company = String(row.company || '')
    if (!item || !company) continue
    const k = `${item}|${company}`
    const rate = rateValue(row)
    if (rate == null) continue
    if (!map.has(k) || Math.abs(rate) > Math.abs(map.get(k))) {
      map.set(k, rate)
    }
  }
  return map
})

const heatmapGridStyle = computed(() => ({
  gridTemplateColumns: `220px repeat(${Math.max(1, heatmapCompanies.value.length)}, minmax(92px, 1fr))`,
}))

const topChangeRows = computed(() => {
  const withRate = comparisonRows.value
    .map((row) => ({ ...row, __rate: rateValue(row) }))
    .filter((row) => row.__rate != null)
    .sort((a, b) => Math.abs(b.__rate) - Math.abs(a.__rate))
  return withRate.slice(0, Math.max(1, Number(comparisonTopN.value || 15)))
})

const analysisInsights = computed(() => {
  if (!comparisonRows.value.length) return []
  const yoyReady = comparisonRows.value.filter((x) => x.yoyRate != null)
  const momReady = comparisonRows.value.filter((x) => x.momRate != null)
  const yoyUp = yoyReady.filter((x) => x.yoyRate > 0).length
  const yoyDown = yoyReady.filter((x) => x.yoyRate < 0).length
  const yoyFlat = yoyReady.length - yoyUp - yoyDown
  const momUp = momReady.filter((x) => x.momRate > 0).length
  const momDown = momReady.filter((x) => x.momRate < 0).length
  const lines = [
    `当前窗口 ${comparisonMeta.currentWindowLabel || '—'} 共 ${comparisonRows.value.length} 个对比序列；可同比 ${yoyReady.length} 个（上升 ${yoyUp}、下降 ${yoyDown}、持平 ${yoyFlat}），可环比 ${momReady.length} 个（上升 ${momUp}、下降 ${momDown}）。`,
  ]
  const topAbsYoy = [...yoyReady]
    .sort((a, b) => Math.abs(b.yoyRate) - Math.abs(a.yoyRate))
    .slice(0, 3)
  if (topAbsYoy.length) {
    lines.push(`同比波动最大项：${topAbsYoy.map((x) => `${x.company}/${x.item} ${formatRate(x.yoyRate)}`).join('；')}。`)
  }
  const topAbsMom = [...momReady]
    .sort((a, b) => Math.abs(b.momRate) - Math.abs(a.momRate))
    .slice(0, 3)
  if (topAbsMom.length) {
    lines.push(`环比波动最大项：${topAbsMom.map((x) => `${x.company}/${x.item} ${formatRate(x.momRate)}`).join('；')}。`)
  }
  const nullRate = summary.totalRows > 0 ? summary.valueNullRows / summary.totalRows : 0
  lines.push(`查询结果空值占比 ${formatPercent(nullRate)}，建议优先核查空值较多序列的上报完整性。`)
  return lines
})

function buildItemOrderKey(name, fallbackIndex) {
  const text = String(name || '').trim()
  const isCalculated = CALCULATED_ITEM_SET.has(text) ? 1 : 0
  const mainGroup = getItemMainGroup(text)
  const consumeSubGroup = getConsumeSubGroup(text)
  const baseName = text.replace(/^总/, '')
  const totalFirst = text.startsWith('总') ? 0 : 1
  return [isCalculated, mainGroup, consumeSubGroup, baseName, totalFirst, fallbackIndex]
}

function compareItemOrderKey(a, b) {
  const len = Math.max(a.length, b.length)
  for (let i = 0; i < len; i += 1) {
    if (a[i] < b[i]) return -1
    if (a[i] > b[i]) return 1
  }
  return 0
}

function getItemMainGroup(text) {
  if (text.includes('产量')) return 10
  if (text.includes('销售量') || text.includes('售热量') || text.includes('售汽量')) return 20
  if (text.includes('消耗') || text.includes('耗')) return 30
  return 40
}

function getConsumeSubGroup(text) {
  if (!(text.includes('消耗') || text.includes('耗'))) return 99
  if (text.includes('煤')) return 0
  if (text.includes('油')) return 1
  if (text.includes('水')) return 2
  if (text.includes('电')) return 3
  if (text.includes('气')) return 4
  return 5
}

function formatNumber(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0'
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 8 })
}

function formatRate(rate) {
  if (rate == null || !Number.isFinite(rate)) return '—'
  return `${rate >= 0 ? '+' : ''}${(rate * 100).toFixed(2)}%`
}

function formatPercent(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0.00%'
  return `${(num * 100).toFixed(2)}%`
}

function rateValue(row) {
  if (!row) return null
  return comparisonViewMode.value === 'mom' ? row.momRate : row.yoyRate
}

function deltaClass(rate) {
  if (rate == null || !Number.isFinite(rate)) return ''
  return rate >= 0 ? 'delta-up' : 'delta-down'
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function heatmapCellStyle(item, company) {
  const rate = heatmapValueMap.value.get(`${item}|${company}`)
  if (rate == null || !Number.isFinite(rate)) {
    return { backgroundColor: '#f1f5f9', color: '#64748b' }
  }
  const intensity = clamp(Math.abs(rate) / 0.5, 0, 1)
  if (rate >= 0) {
    return { backgroundColor: `rgba(220, 38, 38, ${0.2 + intensity * 0.65})`, color: '#450a0a' }
  }
  return { backgroundColor: `rgba(22, 163, 74, ${0.2 + intensity * 0.65})`, color: '#052e16' }
}

function heatmapCellText(item, company) {
  const rate = heatmapValueMap.value.get(`${item}|${company}`)
  return formatRate(rate)
}

function heatmapCellTitle(item, company) {
  const rate = heatmapValueMap.value.get(`${item}|${company}`)
  return `${company} / ${item} / ${comparisonViewMode.value === 'mom' ? '环比' : '同比'}：${formatRate(rate)}`
}

function barWidth(rate) {
  if (rate == null || !Number.isFinite(rate)) return 0
  return clamp(Math.abs(rate) / 0.5, 0, 1) * 100
}

function sanitizeSheetName(name) {
  if (!name) return 'Sheet'
  return String(name).replace(/[\\/?*\[\]:]/g, '_').slice(0, 31) || 'Sheet'
}

function downloadXlsx() {
  if (!rows.value.length) return
  const wb = XLSX.utils.book_new()
  const resultHeader = ['company', 'item', 'unit', 'value', 'date', 'period', 'type', 'report_month']
  const resultData = rows.value.map((row) => [
    row.company ?? '',
    row.item ?? '',
    row.unit ?? '',
    row.value == null ? '' : row.value,
    row.date ?? '',
    row.period ?? '',
    row.type ?? '',
    row.report_month ?? '',
  ])
  const resultSheet = XLSX.utils.aoa_to_sheet([resultHeader, ...resultData])
  XLSX.utils.book_append_sheet(wb, resultSheet, sanitizeSheetName('查询结果'))

  if (comparisonRows.value.length) {
    const compareHeader = ['company', 'item', 'period', 'type', 'current_value', 'yoy_value', 'yoy_rate', 'mom_value', 'mom_rate']
    const compareData = comparisonRows.value.map((x) => [
      x.company,
      x.item,
      x.period,
      x.type,
      x.currentValue,
      x.yoyValue == null ? '' : x.yoyValue,
      x.yoyRate == null ? '' : x.yoyRate,
      x.momValue == null ? '' : x.momValue,
      x.momRate == null ? '' : x.momRate,
    ])
    const compareSheet = XLSX.utils.aoa_to_sheet([compareHeader, ...compareData])
    XLSX.utils.book_append_sheet(wb, compareSheet, sanitizeSheetName('同比环比对比'))
  }

  if (analysisInsights.value.length) {
    const insightData = analysisInsights.value.map((line, idx) => [`要点${idx + 1}`, line])
    const insightSheet = XLSX.utils.aoa_to_sheet([['序号', '分析结论'], ...insightData])
    XLSX.utils.book_append_sheet(wb, insightSheet, sanitizeSheetName('专业分析'))
  }

  const latest = (comparisonMeta.currentWindowLabel || 'unknown').replace(/\s+/g, '_')
  const filename = `月报查询分析_${latest}_${Date.now()}.xlsx`
  XLSX.writeFile(wb, filename)
}

function buildPayload() {
  return {
    report_month_from: toMonthStartDate(filters.reportMonthFrom),
    report_month_to: toMonthEndDate(filters.reportMonthTo),
    date_from: toMonthStartDate(filters.dateMonthFrom),
    date_to: toMonthEndDate(filters.dateMonthTo),
    companies: [...filters.companies],
    items: [...filters.items],
    periods: [...filters.periods],
    types: [...filters.types],
    order_mode: filters.orderMode,
    order_fields: [...filters.orderFields],
    aggregate_companies: Boolean(filters.aggregateCompanies),
    aggregate_months: Boolean(filters.aggregateMonths),
    limit,
    offset: offset.value,
  }
}

function toMonthStartDate(monthText) {
  const text = String(monthText || '').trim()
  if (!text) return null
  const matched = text.match(/^(\d{4})-(\d{2})$/)
  if (!matched) return null
  return `${matched[1]}-${matched[2]}-01`
}

function toMonthEndDate(monthText) {
  const text = String(monthText || '').trim()
  if (!text) return null
  const matched = text.match(/^(\d{4})-(\d{2})$/)
  if (!matched) return null
  const year = Number(matched[1])
  const month = Number(matched[2])
  if (!Number.isInteger(year) || !Number.isInteger(month)) return null
  const end = new Date(year, month, 0)
  const y = end.getFullYear()
  const m = String(end.getMonth() + 1).padStart(2, '0')
  const d = String(end.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function toggleAllCompanies(checked) {
  filters.companies = checked ? [...orderedCompanies.value] : []
}

function toggleAllItems(checked) {
  if (!checked) {
    filters.items = []
    return
  }
  const merged = []
  for (const section of itemSections.value) {
    for (const item of section.items) {
      if (!merged.includes(item)) merged.push(item)
    }
  }
  filters.items = merged
}

function toggleAllPeriods(checked) {
  filters.periods = checked ? [...options.periods] : []
}

function toggleAllTypes(checked) {
  filters.types = checked ? [...orderedTypes.value] : []
}

function resetOrderFields() {
  filters.orderFields = ['company', 'item', 'period', 'type']
}

function getSelectionOrder(selectedList, value) {
  const idx = Array.isArray(selectedList) ? selectedList.indexOf(value) : -1
  return idx >= 0 ? idx + 1 : 0
}

async function loadOptions() {
  const payload = await getMonthlyDataShowQueryOptions('monthly_data_show')
  options.companies = Array.isArray(payload?.companies) ? payload.companies : []
  options.items = Array.isArray(payload?.items) ? payload.items : []
  if (!options.items.includes(AVERAGE_TEMPERATURE_ITEM)) {
    options.items.push(AVERAGE_TEMPERATURE_ITEM)
  }
  options.periods = Array.isArray(payload?.periods) ? payload.periods : []
  options.types = Array.isArray(payload?.types) ? payload.types : []
  filters.periods = options.periods.includes('month')
    ? ['month']
    : (options.periods[0] ? [options.periods[0]] : [])
  filters.types = orderedTypes.value.includes('real')
    ? ['real']
    : (orderedTypes.value[0] ? [orderedTypes.value[0]] : [])
}

async function runQuery(resetOffset = false) {
  hasSearched.value = true
  if (resetOffset) offset.value = 0
  if (!filters.companies.length || !filters.items.length || !filters.periods.length || !filters.types.length) {
    rows.value = []
    total.value = 0
    comparisonRows.value = []
    comparisonMeta.currentWindowLabel = ''
    comparisonMeta.yoyWindowLabel = ''
    comparisonMeta.momWindowLabel = ''
    summary.totalRows = 0
    summary.valueNonNullRows = 0
    summary.valueNullRows = 0
    summary.valueSum = 0
    errorMessage.value = ''
    return
  }
  loading.value = true
  errorMessage.value = ''
  try {
    const queryPayload = buildPayload()
    const [payload, comparePayload] = await Promise.all([
      queryMonthlyDataShow('monthly_data_show', queryPayload),
      queryMonthlyDataShowComparison('monthly_data_show', queryPayload),
    ])
    rows.value = Array.isArray(payload?.rows) ? payload.rows : []
    total.value = Number(payload?.total || 0)
    const respSummary = payload?.summary || {}
    summary.totalRows = Number(respSummary.total_rows || 0)
    summary.valueNonNullRows = Number(respSummary.value_non_null_rows || 0)
    summary.valueNullRows = Number(respSummary.value_null_rows || 0)
    summary.valueSum = Number(respSummary.value_sum || 0)
    comparisonRows.value = Array.isArray(comparePayload?.rows)
      ? comparePayload.rows.map((row) => ({
          key: `${row.company}|${row.item}|${row.period}|${row.type}|${row.unit}`,
          company: row.company,
          item: row.item,
          period: row.period,
          type: row.type,
          unit: row.unit,
          currentValue: row.current_value,
          yoyValue: row.yoy_value,
          yoyRate: row.yoy_rate,
          momValue: row.mom_value,
          momRate: row.mom_rate,
        }))
      : []
    comparisonMeta.currentWindowLabel = String(comparePayload?.current_window_label || '')
    comparisonMeta.yoyWindowLabel = String(comparePayload?.yoy_window_label || '')
    comparisonMeta.momWindowLabel = String(comparePayload?.mom_window_label || '')
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '查询失败'
    rows.value = []
    total.value = 0
    comparisonRows.value = []
    comparisonMeta.currentWindowLabel = ''
    comparisonMeta.yoyWindowLabel = ''
    comparisonMeta.momWindowLabel = ''
    summary.totalRows = 0
    summary.valueNonNullRows = 0
    summary.valueNullRows = 0
    summary.valueSum = 0
  } finally {
    loading.value = false
  }
}

async function resetFilters() {
  filters.dateMonthFrom = ''
  filters.dateMonthTo = ''
  filters.reportMonthFrom = ''
  filters.reportMonthTo = ''
  filters.companies = []
  filters.items = []
  filters.periods = options.periods.includes('month')
    ? ['month']
    : (options.periods[0] ? [options.periods[0]] : [])
  filters.types = orderedTypes.value.includes('real')
    ? ['real']
    : (orderedTypes.value[0] ? [orderedTypes.value[0]] : [])
  filters.orderMode = 'company_first'
  filters.orderFields = ['company', 'item', 'period', 'type']
  filters.aggregateCompanies = false
  filters.aggregateMonths = false
  hasSearched.value = false
  rows.value = []
  total.value = 0
  comparisonRows.value = []
  comparisonMeta.currentWindowLabel = ''
  comparisonMeta.yoyWindowLabel = ''
  comparisonMeta.momWindowLabel = ''
  summary.totalRows = 0
  summary.valueNonNullRows = 0
  summary.valueNullRows = 0
  summary.valueSum = 0
  errorMessage.value = ''
}

async function prevPage() {
  if (offset.value <= 0) return
  offset.value = Math.max(0, offset.value - limit)
  await runQuery(false)
}

async function nextPage() {
  if (!hasNextPage.value) return
  offset.value += limit
  await runQuery(false)
}

onMounted(async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    await loadOptions()
    hasSearched.value = false
    rows.value = []
    total.value = 0
    comparisonRows.value = []
    comparisonMeta.currentWindowLabel = ''
    comparisonMeta.yoyWindowLabel = ''
    comparisonMeta.momWindowLabel = ''
    summary.totalRows = 0
    summary.valueNonNullRows = 0
    summary.valueNullRows = 0
    summary.valueSum = 0
  } catch (error) {
    console.error(error)
    errorMessage.value = error instanceof Error ? error.message : '初始化查询页失败'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.monthly-query-page {
  min-height: 100vh;
  background: #f8fafc;
}

.monthly-query-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 18px 24px 26px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
}

.sub {
  margin-top: 8px;
  color: #64748b;
  font-size: 13px;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
  color: #334155;
}

.span-2 {
  grid-column: span 2;
}

.span-full {
  grid-column: 1 / -1;
}

.field input,
.field select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 13px;
  background: #fff;
}

.field select[multiple] {
  min-height: 100px;
}

.field-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.inline-actions {
  display: flex;
  gap: 8px;
}

.inline-four {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.inline-col {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 8px;
  background: #f8fbff;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.check-list {
  max-height: 240px;
  min-height: 132px;
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  padding: 10px;
  background: #f8fbff;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px 12px;
}

.check-list.slim {
  max-height: 200px;
  min-height: 110px;
  grid-template-columns: 1fr;
  gap: 6px;
  padding: 8px;
  background: #fff;
}

.check-list.sections {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  overflow-x: hidden;
}

.check-list.sections.compact {
  max-height: 460px;
  min-height: 240px;
}

.check-list.company-list {
  max-height: 200px;
  min-height: 96px;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 6px 8px;
  padding: 8px;
}

.check-list.company-list .check-item {
  min-height: 22px;
  gap: 5px;
}

.section-block {
  flex: 0 0 auto;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #fff;
  overflow: visible;
}

.section-title {
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 600;
  color: #1e40af;
  background: #eff6ff;
  border-bottom: 1px solid #dbeafe;
}

.section-items {
  padding: 10px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px 12px;
  max-height: 220px;
  overflow-y: auto;
  overflow-x: hidden;
}

.section-empty {
  font-size: 12px;
  color: #64748b;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #334155;
  min-height: 26px;
}

.check-item span {
  white-space: normal;
  line-height: 1.3;
}

.order-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  font-size: 11px;
  line-height: 1;
  font-weight: 600;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
  padding: 10px 12px;
}

.switch-row.switch-full {
  min-height: 56px;
  align-items: center;
  justify-content: flex-start;
  background: #fff;
}

.switch-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.summary-item {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 12px;
  background: #f8fbff;
}

.summary-item .label {
  font-size: 12px;
  color: #64748b;
}

.summary-item .value {
  margin-top: 6px;
  font-size: 18px;
  color: #1d4ed8;
  font-weight: 600;
}

.result-head {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
}

.result-actions {
  margin-left: auto;
}

.pager {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #475569;
}

.analysis-section {
  margin-top: 14px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 12px;
  background: #f8fbff;
}

.analysis-section h4 {
  margin: 0;
  color: #1e3a8a;
  font-size: 14px;
}

.compare-table {
  min-width: 1080px;
}

.delta-up {
  color: #b91c1c;
  font-weight: 600;
}

.delta-down {
  color: #15803d;
  font-weight: 600;
}

.insight-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #334155;
  font-size: 13px;
  line-height: 1.7;
}

.viz-toolbar {
  margin-top: 8px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.viz-field {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #334155;
}

.viz-field select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 4px 8px;
  background: #fff;
}

.viz-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 10px;
}

.viz-card {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
}

.viz-card h5 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #1d4ed8;
}

.viz-title-nowrap {
  white-space: nowrap;
}

.heatmap-grid {
  display: grid;
  gap: 6px;
  align-items: stretch;
}

.heatmap-header {
  font-size: 11px;
  color: #334155;
  text-align: center;
  font-weight: 600;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  padding: 6px 4px;
}

.heatmap-label {
  font-size: 12px;
  color: #334155;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 8px;
  background: #f8fafc;
}

.heatmap-cell {
  font-size: 11px;
  border-radius: 6px;
  padding: 6px 4px;
  text-align: center;
  font-weight: 600;
}

.bars-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-row {
  display: grid;
  grid-template-columns: 1.2fr 1fr auto;
  align-items: center;
  gap: 8px;
}

.bar-label {
  font-size: 12px;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bar-track {
  height: 10px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: inherit;
  background: #64748b;
}

.bar-fill.delta-up {
  background: #dc2626;
}

.bar-fill.delta-down {
  background: #16a34a;
}

.bar-value {
  min-width: 64px;
  text-align: right;
  font-size: 12px;
}

.table-wrap {
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 980px;
}

.data-table th,
.data-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 10px;
  text-align: left;
  font-size: 12px;
  white-space: nowrap;
}

.data-table thead th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  color: #334155;
  z-index: 1;
}

.empty {
  padding: 24px 0;
  text-align: center;
  color: #64748b;
}

.empty.error {
  color: #b91c1c;
}

.btn {
  border: 1px solid #94a3b8;
  border-radius: 8px;
  background: #fff;
  color: #0f172a;
  font-size: 13px;
  padding: 7px 11px;
  cursor: pointer;
}

.btn.primary {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.btn.mini {
  padding: 3px 8px;
  font-size: 12px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .inline-four {
    grid-template-columns: 1fr 1fr;
  }
  .span-2 {
    grid-column: span 1;
  }
  .span-full {
    grid-column: span 1;
  }
  .check-list,
  .section-items {
    grid-template-columns: 1fr;
  }
  .viz-grid {
    grid-template-columns: 1fr;
  }
  .heatmap-grid {
    min-width: 720px;
  }
}

@media (max-width: 640px) {
  .inline-four {
    grid-template-columns: 1fr;
  }
}
</style>
