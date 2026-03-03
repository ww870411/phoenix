<template>
  <div class="monthly-query-page">
    <AppHeader />
    <main class="monthly-query-main">
      <Breadcrumbs :items="breadcrumbItems" />
      <section class="card">
        <h2>月报数据查询工具</h2>
        <p class="sub">按来源月份、业务日期、口径与指标查询 monthly_data_show 表，并查看基础汇总。</p>
      </section>

      <section class="card">
        <h3>筛选条件</h3>
        <div class="filter-grid">
          <label class="field month-field">
            <span>业务月份起</span>
            <div class="month-input-wrap">
              <input class="month-input" type="month" v-model="filters.dateMonthFrom" />
            </div>
          </label>
          <label class="field month-field">
            <span>业务月份止（非必选）</span>
            <div class="month-input-wrap">
              <input class="month-input" type="month" v-model="filters.dateMonthTo" />
            </div>
          </label>
          <div class="field span-full">
            <div class="field-head">
              <span class="panel-title">口径（可多选）</span>
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
              <span class="panel-title">指标（可多选）</span>
              <div class="inline-actions">
                <button class="btn mini" type="button" @click="toggleAllItems(true)">全选</button>
                <button class="btn mini" type="button" @click="toggleAllItems(false)">全不选</button>
              </div>
            </div>
            <div class="check-list sections compact">
              <div class="section-block" v-for="section in itemSections" :key="section.key">
                <div class="section-title-row">
                  <div class="section-title">{{ section.title }}</div>
                  <button
                    v-if="section.key === 'calculated'"
                    class="btn mini formula-btn"
                    type="button"
                    @click.stop="showFormulaDialog = true"
                  >
                    查看公式
                  </button>
                </div>
                <div class="section-items grouped" v-if="section.key === 'current' && section.groups && section.groups.length">
                  <div class="basic-group-block" v-for="group in section.groups" :key="`${section.key}-${group.name}`">
                    <div class="basic-group-title">{{ group.name }}</div>
                    <div class="basic-group-items">
                      <label class="check-item" v-for="value in group.items" :key="`${section.key}-${group.name}-${value}`">
                        <input type="checkbox" :value="value" v-model="filters.items" />
                        <span>{{ value }}</span>
                        <span v-if="getSelectionOrder(filters.items, value) > 0" class="order-badge">
                          {{ getSelectionOrder(filters.items, value) }}
                        </span>
                      </label>
                    </div>
                  </div>
                </div>
                <div class="section-items" v-else>
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
            <div class="inline-layout">
              <div class="inline-col order-col">
                <div class="field-head">
                  <span class="panel-title">数据层次顺序</span>
                </div>
                <div class="order-inline">
                  <label class="check-item" v-for="layer in layerOptions" :key="layer.value">
                    <input type="checkbox" :value="layer.value" v-model="filters.orderFields" />
                    <span>{{ layer.label }}</span>
                    <span v-if="getSelectionOrder(filters.orderFields, layer.value) > 0" class="order-badge">
                      {{ getSelectionOrder(filters.orderFields, layer.value) }}
                    </span>
                  </label>
                </div>
              </div>
              <div class="inline-col aggregate-col">
                <div class="field-head">
                  <span class="panel-title">聚合开关</span>
                </div>
                <div class="aggregate-inline">
                  <label class="switch-item aggregate-item">
                    <input type="checkbox" v-model="filters.aggregateCompanies" />
                    <span>{{ filters.aggregateCompanies ? '已聚合口径' : '逐口径列出' }}</span>
                  </label>
                  <label class="switch-item aggregate-item">
                    <input type="checkbox" v-model="filters.aggregateMonths" />
                    <span>{{ filters.aggregateMonths ? '已聚合期间月份' : '逐月列出' }}</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
        <p class="sub" v-if="!filters.companies.length || !filters.items.length">
          口径、指标均需至少各选 1 项；若任一为空将不提取任何数据。
        </p>
        <div class="actions">
          <button class="btn primary" type="button" :disabled="loading || !filters.companies.length || !filters.items.length" @click="runQuery(true)">
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
        <div class="ai-toolbar">
          <label class="switch-item">
            <input type="checkbox" v-model="aiReportEnabled" />
            <span>智能报告生成（BETA）</span>
          </label>
          <button
            v-if="isGlobalAdmin"
            class="btn ghost"
            type="button"
            :disabled="!isGlobalAdmin"
            @click="openAiSettingsDialog"
          >
            智能体设定
          </button>
          <button
            class="btn ghost"
            type="button"
            :disabled="!aiReportEnabled || loading || !comparisonRows.length || aiReportStatus === 'running' || aiReportStatus === 'pending'"
            @click="triggerAiReport"
          >
            {{ aiReportStatus === 'running' || aiReportStatus === 'pending' ? '生成中…' : '生成智能报告' }}
          </button>
          <button
            class="btn ghost"
            type="button"
            :disabled="!aiReportContent"
            @click="downloadAiReport"
          >
            下载智能报告
          </button>
        </div>
        <label v-if="aiReportEnabled" class="ai-prompt-field">
          <span>本次分析要求（可选）</span>
          <textarea
            v-model="aiUserPrompt"
            rows="3"
            maxlength="2000"
            :disabled="aiReportStatus === 'running' || aiReportStatus === 'pending'"
            placeholder="例如：优先关注水耗率异常口径，并给出3条可执行优化建议。"
          ></textarea>
        </label>
        <p v-if="aiReportStatusMessage" class="sub ai-status">{{ aiReportStatusMessage }}</p>
        <div v-if="showAiReportProgress" class="ai-progress">
          <div class="ai-progress__bar">
            <span class="ai-progress__fill" :style="{ width: `${aiReportProgressPercent}%` }"></span>
          </div>
          <div class="ai-progress__meta">
            <span>进度 {{ aiReportProgressPercent }}%</span>
            <span>{{ aiReportProgressLabel }}</span>
          </div>
          <div class="ai-progress__steps">
            <span
              v-for="step in AI_REPORT_STAGE_STEPS"
              :key="`monthly-ai-step-${step.key}`"
              class="ai-progress__step"
              :class="{ active: aiReportProgressOrder >= step.order }"
            >
              {{ step.order }}.{{ step.label }}
            </span>
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
                <th v-for="col in resultColumns" :key="`head-${col.field}`">{{ col.label }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in rows" :key="`${row.company}-${row.item}-${row.date}-${row.period}-${row.type}-${idx}`">
                <td v-for="col in resultColumns" :key="`cell-${col.field}-${idx}`">{{ getResultCellValue(row, col.field) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="hasSearched && comparisonRows.length" class="analysis-section">
          <h4>同比/环比/计划比（实时窗口）</h4>
          <p class="sub">
            当前月份：{{ comparisonLatestMonthLabel }}；同比月份：{{ comparisonYoYMonthLabel || '无' }}；环比月份：{{ comparisonMoMMonthLabel || '无' }}；计划窗口：{{ comparisonPlanMonthLabel || '无' }}
          </p>
          <div class="viz-toolbar">
            <div class="viz-field viz-switch-field">
              <span>图表口径</span>
              <div class="mode-switch-group">
                <button
                  type="button"
                  class="mode-switch-btn"
                  :class="{ active: comparisonViewMode === 'yoy' }"
                  @click="comparisonViewMode = 'yoy'"
                >
                  同比
                </button>
                <button
                  type="button"
                  class="mode-switch-btn"
                  :class="{ active: comparisonViewMode === 'mom' }"
                  @click="comparisonViewMode = 'mom'"
                >
                  环比
                </button>
                <button
                  type="button"
                  class="mode-switch-btn"
                  :class="{ active: comparisonViewMode === 'plan' }"
                  @click="comparisonViewMode = 'plan'"
                >
                  计划比
                </button>
              </div>
            </div>
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
              <h5 class="viz-title-nowrap">{{ comparisonModeLabel }}热力图（纵轴=指标，横轴=口径）</h5>
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
              <h5>{{ comparisonModeLabel }}波动 TopN（绝对值）</h5>
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
                  <th>本期值</th>
                  <th>同期值</th>
                  <th>同比</th>
                  <th>上期值</th>
                  <th>环比</th>
                  <th>计划值</th>
                  <th>计划比</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in comparisonRows" :key="entry.key">
                  <td>{{ entry.company }}</td>
                  <td>{{ entry.item }}</td>
                  <td>{{ entry.currentValue == null ? 'NULL' : formatValue(entry.currentValue, entry.unit, entry.item) }}</td>
                  <td>{{ entry.yoyValue == null ? 'NULL' : formatValue(entry.yoyValue, entry.unit, entry.item) }}</td>
                  <td :class="deltaClass(entry.yoyRate)">{{ formatRate(entry.yoyRate) }}</td>
                  <td>{{ entry.momValue == null ? 'NULL' : formatValue(entry.momValue, entry.unit, entry.item) }}</td>
                  <td :class="deltaClass(entry.momRate)">{{ formatRate(entry.momRate) }}</td>
                  <td>{{ entry.planValue == null ? 'NULL' : formatValue(entry.planValue, entry.unit, entry.item) }}</td>
                  <td :class="deltaClass(entry.planRate)">{{ formatRate(entry.planRate) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-if="hasSearched && analysisInsights.length" class="analysis-section">
          <h4>简要分析</h4>
          <div class="insight-list">
            <p
              v-for="(line, idx) in analysisInsights"
              :key="`insight-${idx}`"
              class="insight-line"
              :class="analysisLineClass(line)"
            >
              {{ line }}
            </p>
          </div>
        </div>
        <div v-if="hasSearched && showTemperaturePanel" class="analysis-section temperature-section">
          <div class="temperature-head">
            <h4>平均气温区间分析（默认折叠）</h4>
            <button class="btn mini" type="button" @click="temperatureExpanded = !temperatureExpanded">
              {{ temperatureExpanded ? '收起' : '展开' }}
            </button>
          </div>
          <p class="sub">
            当前窗口：{{ comparisonLatestMonthLabel }}；同比窗口：{{ comparisonYoYMonthLabel || '无' }}。
          </p>
          <div v-if="temperatureExpanded">
            <div class="summary-grid temp-summary-grid">
              <div class="summary-item">
                <div class="label">本期平均气温</div>
                <div class="value">{{ formatTemperature(temperatureSummary.currentAvgTemp) }}</div>
              </div>
              <div class="summary-item">
                <div class="label">同期平均气温</div>
                <div class="value">{{ formatTemperature(temperatureSummary.yoyAvgTemp) }}</div>
              </div>
              <div class="summary-item">
                <div class="label">同比差值</div>
                <div class="value" :class="deltaClass(temperatureSummary.yoyAvgDiff)">{{ formatSignedNumber(temperatureSummary.yoyAvgDiff) }}</div>
              </div>
              <div class="summary-item">
                <div class="label">同比差异率</div>
                <div class="value" :class="deltaClass(temperatureSummary.yoyAvgRate)">{{ formatRate(temperatureSummary.yoyAvgRate) }}</div>
              </div>
            </div>
            <div class="temp-chart-wrap">
              <h5>本期与同期每日气温曲线</h5>
              <div v-if="temperatureChart.hasData" class="temp-chart-container">
                <svg class="temp-chart-svg" :viewBox="temperatureChart.viewBox" preserveAspectRatio="none">
                  <line
                    :x1="temperatureChart.pad"
                    :y1="temperatureChart.height - temperatureChart.pad"
                    :x2="temperatureChart.width - temperatureChart.pad"
                    :y2="temperatureChart.height - temperatureChart.pad"
                    class="temp-axis"
                  />
                  <line
                    :x1="temperatureChart.pad"
                    :y1="temperatureChart.pad"
                    :x2="temperatureChart.pad"
                    :y2="temperatureChart.height - temperatureChart.pad"
                    class="temp-axis"
                  />
                  <path v-if="temperatureChart.currentPath" :d="temperatureChart.currentPath" class="temp-line current" />
                  <path v-if="temperatureChart.yoyPath" :d="temperatureChart.yoyPath" class="temp-line yoy" />
                </svg>
                <div class="temp-legend">
                  <span class="legend-item"><i class="legend-dot current"></i>本期</span>
                  <span class="legend-item"><i class="legend-dot yoy"></i>同期</span>
                </div>
              </div>
              <p v-else class="sub">该区间暂无可用气温曲线数据。</p>
            </div>
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>本期日期</th>
                    <th>本期气温(℃)</th>
                    <th>同期日期</th>
                    <th>同期气温(℃)</th>
                    <th>同比差值(℃)</th>
                    <th>同比差异率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in temperatureDailyRows" :key="`temp-${row.currentDate}`">
                    <td>{{ row.currentDate }}</td>
                    <td>{{ formatTemperature(row.currentTemp) }}</td>
                    <td>{{ row.yoyDate }}</td>
                    <td>{{ formatTemperature(row.yoyTemp) }}</td>
                    <td :class="deltaClass(row.yoyDiff)">{{ formatSignedNumber(row.yoyDiff) }}</td>
                    <td :class="deltaClass(row.yoyRate)">{{ formatRate(row.yoyRate) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </main>
    <AiAgentSettingsDialog
      v-model="aiSettingsDialogVisible"
      :can-manage="isGlobalAdmin"
      :load-settings="loadAiSettingsPayload"
      :save-settings="saveAiSettingsPayload"
      :test-settings="testAiSettingsPayload"
    />
    <div v-if="showFormulaDialog" class="formula-dialog-mask" @click.self="showFormulaDialog = false">
      <section class="formula-dialog">
        <div class="formula-dialog-head">
          <h4>计算指标公式说明</h4>
          <button class="btn mini" type="button" @click="showFormulaDialog = false">关闭</button>
        </div>
        <p class="sub">缺失指标按 0 处理；分母为 0 时结果按 0 处理。比例类指标以小数存储，展示时按百分比格式显示。</p>
        <div class="table-wrap">
          <table class="data-table formula-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>公式</th>
                <th>单位</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in calculatedFormulaRows" :key="entry.item">
                <td>{{ entry.item }}</td>
                <td>{{ entry.formula }}</td>
                <td>{{ entry.unit }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as XLSX from 'xlsx'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import AiAgentSettingsDialog from '../../daily_report_25_26/components/AiAgentSettingsDialog.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import {
  getAdminAiSettings,
  testAdminAiSettings,
  getMonthlyDataShowQueryOptions,
  getMonthlyDataShowAiReport,
  queryMonthlyDataShow,
  queryMonthlyDataShowComparison,
  startMonthlyDataShowAiReport,
  updateAdminAiSettings,
} from '../../daily_report_25_26/services/api'
import { useAuthStore } from '../../daily_report_25_26/store/auth'

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '月报导入与查询', to: '/projects/monthly_data_show/pages' },
  { label: '月报数据查询工具', to: null },
])
const auth = useAuthStore()
const normalizedGroup = computed(() => String(auth.user?.group || '').toLowerCase())
const isGlobalAdmin = computed(() => normalizedGroup.value === 'global_admin')

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
  companies: [],
  items: [],
  periods: ['month'],
  types: ['real'],
  orderMode: 'company_first',
  orderFields: ['time', 'company', 'item'],
  aggregateCompanies: false,
  aggregateMonths: false,
})
const layerOptions = [
  { value: 'time', label: '时间' },
  { value: 'company', label: '口径' },
  { value: 'item', label: '指标' },
]
const RESULT_DIMENSION_FIELDS = ['time', 'company', 'item']
const RESULT_COLUMN_LABELS = {
  time: '时间',
  company: '口径',
  item: '指标名',
  value: '值',
  unit: '计量单位',
}

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
const AVERAGE_TEMPERATURE_ITEM = '平均气温'
const indicatorConfig = reactive({
  basicSectionTitle: '基本指标',
  calculatedSectionTitle: '计算指标',
  categoryPlaceholder: '【待配置分类】',
  basicGroups: [],
  basicItems: [],
  calculatedItems: [],
})
const calculatedItemSet = computed(() => {
  const names = (indicatorConfig.calculatedItems || []).map((x) => String(x?.name || '').trim()).filter(Boolean)
  return new Set(names)
})
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
  const configuredNames = [
    ...(indicatorConfig.basicItems || []).map((x) => String(x?.name || '').trim()),
    ...(indicatorConfig.calculatedItems || []).map((x) => String(x?.name || '').trim()),
  ].filter(Boolean)
  const configuredRank = new Map(configuredNames.map((name, idx) => [name, idx]))
  const input = Array.isArray(options.items) ? [...options.items] : []
  return input
    .map((name, index) => ({ name, index, key: buildItemOrderKey(name, index) }))
    .sort((a, b) => {
      const ar = configuredRank.has(a.name) ? configuredRank.get(a.name) : Number.MAX_SAFE_INTEGER
      const br = configuredRank.has(b.name) ? configuredRank.get(b.name) : Number.MAX_SAFE_INTEGER
      if (ar !== br) return ar - br
      return compareItemOrderKey(a.key, b.key)
    })
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
  const sourceSet = new Set(orderedItems.value)
  const calcSet = calculatedItemSet.value
  const fallbackBasic = []
  const configuredBasic = (indicatorConfig.basicItems || [])
    .map((x) => String(x?.name || '').trim())
    .filter(Boolean)
  const configuredCalculated = (indicatorConfig.calculatedItems || [])
    .map((x) => String(x?.name || '').trim())
    .filter(Boolean)
  for (const item of configuredBasic) {
    if (item && sourceSet.has(item) && !calcSet.has(item)) {
      fallbackBasic.push(item)
    }
  }
  for (const item of orderedItems.value) {
    if (calcSet.has(item)) continue
    if (!fallbackBasic.includes(item)) {
      fallbackBasic.push(item)
    }
  }
  const configuredBasicGroups = Array.isArray(indicatorConfig.basicGroups) ? indicatorConfig.basicGroups : []
  const groupSeen = new Set()
  const grouped = []
  for (const group of configuredBasicGroups) {
    const groupName = String(group?.name || '').trim() || '未命名分组'
    const groupItemsRaw = Array.isArray(group?.items) ? group.items : []
    const groupItems = []
    for (const row of groupItemsRaw) {
      const itemName = String(row?.name || row || '').trim()
      if (!itemName || groupSeen.has(itemName) || !sourceSet.has(itemName) || calcSet.has(itemName)) continue
      groupSeen.add(itemName)
      groupItems.push(itemName)
    }
    if (groupItems.length) {
      grouped.push({ name: groupName, items: groupItems })
    }
  }
  const ungrouped = fallbackBasic.filter((x) => !groupSeen.has(x))
  if (ungrouped.length) {
    grouped.push({ name: '未分组', items: ungrouped })
  }
  const current = grouped.flatMap((x) => x.items)
  const mergedCalculated = configuredCalculated.length ? configuredCalculated : orderedItems.value.filter((x) => calculatedItemSet.value.has(x))
  const calcTitleText = String(indicatorConfig.calculatedSectionTitle || '').trim()
  const calcTitle = calcTitleText && !/（0项）$/.test(calcTitleText)
    ? calcTitleText
    : `计算指标（${mergedCalculated.length}项）`
  return [
    { key: 'current', title: indicatorConfig.basicSectionTitle || '基本指标', items: current, groups: grouped },
    { key: 'calculated', title: calcTitle, items: mergedCalculated },
  ]
})
const resultDimensionFields = computed(() => {
  const selected = (Array.isArray(filters.orderFields) ? filters.orderFields : [])
    .map((x) => String(x || '').trim())
    .filter((x) => RESULT_DIMENSION_FIELDS.includes(x))
  const merged = []
  for (const field of selected) {
    if (!merged.includes(field)) merged.push(field)
  }
  for (const field of RESULT_DIMENSION_FIELDS) {
    if (!merged.includes(field)) merged.push(field)
  }
  return merged
})
const resultColumns = computed(() => [
  ...resultDimensionFields.value.map((field) => ({ field, label: RESULT_COLUMN_LABELS[field] })),
  { field: 'value', label: RESULT_COLUMN_LABELS.value },
  { field: 'unit', label: RESULT_COLUMN_LABELS.unit },
])

const comparisonRows = ref([])
const aiReportEnabled = ref(false)
const aiModeId = ref('monthly_analysis_v1')
const aiUserPrompt = ref('')
const aiReportJobId = ref('')
const aiReportStatus = ref('idle')
const aiReportContent = ref('')
const aiReportStatusMessage = ref('')
const aiReportStage = ref('')
const aiSettingsDialogVisible = ref(false)
let aiReportPollTimer = null
const showFormulaDialog = ref(false)
const temperatureExpanded = ref(false)
const temperatureDailyRows = ref([])
const temperatureSummary = reactive({
  currentAvgTemp: null,
  yoyAvgTemp: null,
  yoyAvgDiff: null,
  yoyAvgRate: null,
})
const calculatedFormulaRows = computed(() => (indicatorConfig.calculatedItems || []).map((x) => ({
  item: String(x?.name || ''),
  formula: String(x?.formula || ''),
  unit: String(x?.unit || ''),
})))
const comparisonViewMode = ref('yoy')
const comparisonTopN = ref(15)
const comparisonMeta = reactive({
  currentWindowLabel: '',
  yoyWindowLabel: '',
  momWindowLabel: '',
  planWindowLabel: '',
})
const comparisonLatestMonthLabel = computed(() => comparisonMeta.currentWindowLabel || '—')
const comparisonYoYMonthLabel = computed(() => comparisonMeta.yoyWindowLabel || '—')
const comparisonMoMMonthLabel = computed(() => comparisonMeta.momWindowLabel || '—')
const comparisonPlanMonthLabel = computed(() => comparisonMeta.planWindowLabel || '—')
const comparisonModeLabel = computed(() => {
  if (comparisonViewMode.value === 'mom') return '环比'
  if (comparisonViewMode.value === 'plan') return '计划比'
  return '同比'
})
const AI_REPORT_STAGE_STEPS = [
  { key: 'insight', order: 1, label: '洞察分析' },
  { key: 'layout', order: 2, label: '结构规划' },
  { key: 'content', order: 3, label: '内容撰写' },
  { key: 'review', order: 4, label: '检查核实' },
]
const AI_REPORT_STAGE_TOTAL = AI_REPORT_STAGE_STEPS.length
const AI_REPORT_STAGE_LOOKUP = AI_REPORT_STAGE_STEPS.reduce((acc, step) => {
  acc[step.key] = step
  return acc
}, {})
const AI_STAGE_ALIAS_ORDER = {
  revision_pending: 3,
  revision_content: 3,
}
const aiReportProgressOrder = computed(() => {
  if (aiReportStatus.value === 'ready') return AI_REPORT_STAGE_TOTAL
  const step = AI_REPORT_STAGE_LOOKUP[aiReportStage.value]
  if (step?.order) return step.order
  if (AI_STAGE_ALIAS_ORDER[aiReportStage.value]) return AI_STAGE_ALIAS_ORDER[aiReportStage.value]
  return 0
})
const aiReportProgressPercent = computed(() => {
  if (aiReportStatus.value === 'ready') return 100
  const ratio = aiReportProgressOrder.value > 0
    ? Math.round((aiReportProgressOrder.value / AI_REPORT_STAGE_TOTAL) * 100)
    : 8
  if (aiReportStatus.value === 'failed') return Math.max(10, ratio)
  return Math.min(95, Math.max(8, ratio))
})
const aiReportProgressLabel = computed(() => {
  if (aiReportStatus.value === 'ready') return '报告生成完成'
  if (aiReportStatus.value === 'failed') return '报告生成失败'
  if (aiReportStage.value === 'pending' || !aiReportStage.value) return '任务排队中'
  const step = AI_REPORT_STAGE_LOOKUP[aiReportStage.value]
  if (step?.label) return `当前阶段：${step.label}`
  return '正在处理中'
})
const showAiReportProgress = computed(() => (
  aiReportEnabled.value
  && (aiReportStatus.value === 'pending'
    || aiReportStatus.value === 'running'
    || aiReportStatus.value === 'ready'
    || aiReportStatus.value === 'failed')
))
const showTemperaturePanel = computed(() => {
  if (!filters.items.includes(AVERAGE_TEMPERATURE_ITEM)) return false
  if (temperatureDailyRows.value.length > 0) return true
  return (
    temperatureSummary.currentAvgTemp != null
    || temperatureSummary.yoyAvgTemp != null
    || temperatureSummary.yoyAvgDiff != null
    || temperatureSummary.yoyAvgRate != null
  )
})

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

const temperatureChart = computed(() => {
  const labels = temperatureDailyRows.value.map((row) => String(row.currentDate || '').slice(5))
  const currentValues = temperatureDailyRows.value.map((row) => toFiniteOrNull(row.currentTemp))
  const yoyValues = temperatureDailyRows.value.map((row) => toFiniteOrNull(row.yoyTemp))
  const merged = [...currentValues, ...yoyValues].filter((v) => v != null)
  if (!merged.length) {
    return {
      hasData: false,
      width: 960,
      height: 320,
      pad: 32,
      viewBox: '0 0 960 320',
      currentPath: '',
      yoyPath: '',
      labels,
    }
  }
  const min = Math.min(...merged)
  const max = Math.max(...merged)
  const paddingValue = Math.max(1, (max - min) * 0.1)
  const yMin = min - paddingValue
  const yMax = max + paddingValue
  const width = 960
  const height = 320
  const pad = 32
  return {
    hasData: true,
    width,
    height,
    pad,
    viewBox: `0 0 ${width} ${height}`,
    currentPath: buildLinePath(currentValues, yMin, yMax, width, height, pad),
    yoyPath: buildLinePath(yoyValues, yMin, yMax, width, height, pad),
    labels,
  }
})

const analysisInsights = computed(() => {
  if (!comparisonRows.value.length) return []
  const orderFields = (Array.isArray(filters.orderFields) ? filters.orderFields : [])
    .map((x) => String(x || '').trim())
    .filter((x) => ['time', 'company', 'item'].includes(x))
  const resolvedFields = orderFields.length ? orderFields : ['time', 'company', 'item']
  const fieldLabels = {
    time: '时间',
    company: '口径',
    item: '指标',
  }
  const yoyReady = comparisonRows.value.filter((x) => x.yoyRate != null)
  const momReady = comparisonRows.value.filter((x) => x.momRate != null)
  const planReady = comparisonRows.value.filter((x) => x.planRate != null)
  const lines = [
    `一、总体情况：本期窗口为 ${comparisonMeta.currentWindowLabel || '—'}，共纳入 ${comparisonRows.value.length} 条有效对比序列；同比可比 ${yoyReady.length} 条，环比可比 ${momReady.length} 条，计划可比 ${planReady.length} 条。`,
  ]
  lines.push(`二、分层分析：以下按“${resolvedFields.map((f) => fieldLabels[f]).join(' > ')}”顺序展开。`)
  const MAX_DETAIL_LINES = 180
  let detailCount = 0
  const shouldSkipAnalysisRow = (row) => {
    const values = [
      toFiniteOrNull(row?.currentValue),
      toFiniteOrNull(row?.yoyValue),
      toFiniteOrNull(row?.momValue),
      toFiniteOrNull(row?.planValue),
    ]
    return values.every((v) => v === 0)
  }
  const hasEffectiveRows = (rows) => Array.isArray(rows) && rows.some((row) => !shouldSkipAnalysisRow(row))
  const appendByLevel = (rows, level) => {
    if (detailCount >= MAX_DETAIL_LINES) return
    if (level >= resolvedFields.length) {
      for (const row of rows) {
        if (detailCount >= MAX_DETAIL_LINES) break
        if (shouldSkipAnalysisRow(row)) continue
        const yoyDiff = row.currentValue == null || row.yoyValue == null ? null : row.currentValue - row.yoyValue
        const momDiff = row.currentValue == null || row.momValue == null ? null : row.currentValue - row.momValue
        const planDiff = row.currentValue == null || row.planValue == null ? null : row.currentValue - row.planValue
        const yoyTrend = yoyDiff == null ? '—' : yoyDiff > 0 ? '增加' : yoyDiff < 0 ? '减少' : '持平'
        const momTrend = momDiff == null ? '—' : momDiff > 0 ? '增加' : momDiff < 0 ? '减少' : '持平'
        const planTrend = planDiff == null ? '—' : planDiff > 0 ? '增加' : planDiff < 0 ? '减少' : '持平'
        const segments = [
          `本期 ${formatValueWithUnit(row.currentValue, row.unit, row.item)}`,
          `同期 ${formatValueWithUnit(row.yoyValue, row.unit, row.item)}，同比${yoyTrend}${formatSignedNumber(yoyDiff, row.item)}，差异率 ${formatRate(row.yoyRate)}`,
        ]
        if (row.momValue != null) {
          segments.push(`上期 ${formatValueWithUnit(row.momValue, row.unit, row.item)}，环比${momTrend}${formatSignedNumber(momDiff, row.item)}，差异率 ${formatRate(row.momRate)}`)
        }
        segments.push(`本期计划值 ${formatValueWithUnit(row.planValue, row.unit, row.item)}，较计划${planTrend}${formatSignedNumber(planDiff, row.item)}，差异率 ${formatRate(row.planRate)}`)
        lines.push(`  ${segments.join('；')}。`)
        detailCount += 1
      }
      return
    }
    const field = resolvedFields[level]
    const groups = []
    const groupMap = new Map()
    for (const row of rows) {
      const key = field === 'time'
        ? String(comparisonMeta.currentWindowLabel || '当前窗口')
        : String(row[field] ?? '—')
      if (!groupMap.has(key)) {
        const bucket = { key, rows: [] }
        groupMap.set(key, bucket)
        groups.push(bucket)
      }
      groupMap.get(key).rows.push(row)
    }
    for (const group of groups) {
      if (detailCount >= MAX_DETAIL_LINES) break
      if (!hasEffectiveRows(group.rows)) continue
      if (field === 'item') {
        lines.push(`•${group.key}`)
      } else {
        lines.push(`${fieldLabels[field]}：${group.key}`)
      }
      appendByLevel(group.rows, level + 1)
    }
  }
  appendByLevel(comparisonRows.value, 0)
  if (detailCount >= MAX_DETAIL_LINES) {
    lines.push(`说明：分层明细较多，已按前 ${MAX_DETAIL_LINES} 条展示。`)
  }

  const highRiskCount = comparisonRows.value.filter((row) => {
    const r = rateValue(row)
    return r != null && Math.abs(r) >= 0.2
  }).length
  lines.push(`四、风险提示：|差异率| ≥ 20% 的序列共 ${highRiskCount} 条，建议优先核查源数据质量、口径一致性与计划设定合理性。`)
  const nullRate = summary.totalRows > 0 ? summary.valueNullRows / summary.totalRows : 0
  lines.push(`五、数据完整性：查询结果空值占比 ${formatPercent(nullRate)}，建议持续完善缺失值填报并复核关键指标。`)
  return lines
})

function buildItemOrderKey(name, fallbackIndex) {
  const text = String(name || '').trim()
  const isCalculated = calculatedItemSet.value.has(text) ? 1 : 0
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

const FOUR_DECIMAL_ITEMS = new Set(['供暖热耗率', '供暖水耗率', '供暖电耗率'])

function valueDecimalDigitsByItem(item) {
  const normalized = String(item || '').trim()
  return FOUR_DECIMAL_ITEMS.has(normalized) ? 4 : 2
}

function formatNumber(value, fractionDigits = 2) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0'
  const safeDigits = Number.isInteger(fractionDigits) && fractionDigits >= 0 ? fractionDigits : 2
  const base = 10 ** safeDigits
  const rounded = Math.round(num * base) / base
  const isIntegerLike = Math.abs(rounded - Math.trunc(rounded)) < 1e-9
  if (isIntegerLike) {
    return rounded.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
  }
  return rounded.toLocaleString('zh-CN', {
    minimumFractionDigits: safeDigits,
    maximumFractionDigits: safeDigits,
  })
}

function toFiniteOrNull(value) {
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

function calcRate(currentValue, baseValue) {
  const current = toFiniteOrNull(currentValue)
  const base = toFiniteOrNull(baseValue)
  if (current == null || base == null || base === 0) return null
  return (current - base) / Math.abs(base)
}

function formatValue(value, unit, item) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0'
  const normalizedUnit = String(unit || '').trim()
  const fractionDigits = valueDecimalDigitsByItem(item)
  if (normalizedUnit === '%') {
    return `${formatNumber(num * 100, fractionDigits)}%`
  }
  return formatNumber(num, fractionDigits)
}

function formatValueWithUnit(value, unit, item) {
  if (value == null) return '—'
  const base = formatValue(value, unit, item)
  const normalizedUnit = String(unit || '').trim()
  if (!normalizedUnit || normalizedUnit === '%') return base
  return `${base} ${normalizedUnit}`
}

function formatRate(rate) {
  if (rate == null || !Number.isFinite(rate)) return '—'
  return `${rate >= 0 ? '+' : ''}${(rate * 100).toFixed(2)}%`
}

function formatSignedNumber(value, item) {
  const num = toFiniteOrNull(value)
  if (num == null) return '—'
  const absText = formatNumber(Math.abs(num), valueDecimalDigitsByItem(item))
  if (num > 0) return `+${absText}`
  if (num < 0) return `-${absText}`
  return absText
}

function formatTemperature(value) {
  const num = toFiniteOrNull(value)
  if (num == null) return '—'
  return `${formatNumber(num)}℃`
}

function formatPercent(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '0.00%'
  return `${(num * 100).toFixed(2)}%`
}

function analysisLineClass(line) {
  const text = String(line || '').trim()
  if (!text) return ''
  if (/^[一二三四五六七八九十]+、/.test(text)) return 'level-1'
  if (/^口径：/.test(text)) return 'level-2 company-title'
  if (/^•/.test(text)) return 'level-2 item-title'
  if (/^(口径|指标|期间|类型)：/.test(text)) return 'level-2'
  return 'level-3'
}

function rateValue(row) {
  if (!row) return null
  if (comparisonViewMode.value === 'mom') return row.momRate
  if (comparisonViewMode.value === 'plan') return row.planRate
  return row.yoyRate
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
  const modeLabel = comparisonViewMode.value === 'mom'
    ? '环比'
    : comparisonViewMode.value === 'plan'
      ? '计划比'
      : '同比'
  return `${company} / ${item} / ${modeLabel}：${formatRate(rate)}`
}

function barWidth(rate) {
  if (rate == null || !Number.isFinite(rate)) return 0
  return clamp(Math.abs(rate) / 0.5, 0, 1) * 100
}

function buildLinePath(values, minValue, maxValue, width, height, pad) {
  if (!Array.isArray(values) || !values.length) return ''
  const innerWidth = Math.max(1, width - pad * 2)
  const innerHeight = Math.max(1, height - pad * 2)
  const range = Math.max(1e-9, maxValue - minValue)
  const points = []
  for (let i = 0; i < values.length; i += 1) {
    const value = values[i]
    if (value == null || !Number.isFinite(value)) continue
    const x = pad + (innerWidth * i) / Math.max(1, values.length - 1)
    const y = pad + ((maxValue - value) / range) * innerHeight
    points.push([x, y])
  }
  if (!points.length) return ''
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point[0]} ${point[1]}`).join(' ')
}

function sanitizeSheetName(name) {
  if (!name) return 'Sheet'
  return String(name).replace(/[\\/?*\[\]:]/g, '_').slice(0, 31) || 'Sheet'
}

function formatMonthTag(year, month) {
  const y = Number(year)
  const m = Number(month)
  if (!Number.isInteger(y) || !Number.isInteger(m) || m < 1 || m > 12) return ''
  return `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}`
}

function formatResultMonth(dateText) {
  const text = String(dateText || '').trim()
  if (!text) return '—'
  const matched = text.match(/^(\d{4})-(\d{2})(?:-\d{2})?$/)
  if (!matched) return text
  return `${matched[1]}年${Number(matched[2])}月`
}

function isPercentUnit(unit) {
  return String(unit || '').trim() === '%'
}

function buildDecimalFormat(decimals = 2) {
  const safe = Number.isInteger(decimals) && decimals >= 0 ? decimals : 2
  if (safe <= 0) return '#,##0'
  return `#,##0.${'0'.repeat(safe)}`
}

function buildExcelValueFormat(unit, item) {
  const digits = valueDecimalDigitsByItem(item)
  if (isPercentUnit(unit)) {
    if (digits <= 0) return '0%'
    return `0.${'0'.repeat(digits)}%`
  }
  return buildDecimalFormat(digits)
}

function setSheetNumericCell(sheet, rowIndex, colIndex, value, numFmt) {
  const num = toFiniteOrNull(value)
  if (num == null) return
  const address = XLSX.utils.encode_cell({ r: rowIndex, c: colIndex })
  sheet[address] = { t: 'n', v: num, z: numFmt || '#,##0.00' }
}

function getResultCellValue(row, field) {
  if (field === 'time') {
    return formatResultMonth(row?.report_month || row?.date || '')
  }
  if (field === 'company') {
    return row?.company || '—'
  }
  if (field === 'item') {
    return row?.item || '—'
  }
  if (field === 'value') {
    return row?.value == null ? 'NULL' : formatValue(row.value, row.unit, row.item)
  }
  if (field === 'unit') {
    return row?.unit || '—'
  }
  return '—'
}

function resolveExportMonthTag() {
  const fromDate = String(filters.dateMonthFrom || '').trim()
  const toDate = String(filters.dateMonthTo || '').trim()
  const monthRe = /^(\d{4})-(\d{2})$/

  if (monthRe.test(fromDate) && monthRe.test(toDate) && fromDate !== toDate) {
    return `${fromDate}_~_${toDate}`
  }
  if (monthRe.test(fromDate) && (!toDate || fromDate === toDate)) {
    return fromDate
  }
  if (!fromDate && monthRe.test(toDate)) {
    return toDate
  }

  const windowLabel = String(comparisonMeta.currentWindowLabel || '').trim()
  const rangeMatch = windowLabel.match(/^(\d{4})-(\d{2})-\d{2}\s*~\s*(\d{4})-(\d{2})-\d{2}$/)
  if (rangeMatch) {
    const y1 = Number(rangeMatch[1])
    const m1 = Number(rangeMatch[2])
    const y2 = Number(rangeMatch[3])
    const m2 = Number(rangeMatch[4])
    const startTag = formatMonthTag(y1, m1)
    const endTag = formatMonthTag(y2, m2)
    if (startTag && endTag) {
      return startTag === endTag ? startTag : `${startTag}_~_${endTag}`
    }
  }
  const singleMatch = windowLabel.match(/^(\d{4})-(\d{2})-\d{2}$/)
  if (singleMatch) {
    const tag = formatMonthTag(Number(singleMatch[1]), Number(singleMatch[2]))
    if (tag) return tag
  }

  const monthTags = [...new Set(
    rows.value
      .map((row) => String(row?.report_month || row?.date || '').slice(0, 7))
      .filter((x) => monthRe.test(x))
  )].sort()
  if (monthTags.length === 1) return monthTags[0]
  if (monthTags.length > 1) {
    return `${monthTags[0]}_~_${monthTags[monthTags.length - 1]}`
  }

  const now = new Date()
  return formatMonthTag(now.getFullYear(), now.getMonth() + 1) || 'unknown'
}

function finalizeSheet(sheet, columnWidths = []) {
  if (!sheet) return
  if (columnWidths.length) {
    sheet['!cols'] = columnWidths.map((wch) => ({ wch }))
  }
  const ref = sheet['!ref']
  if (!ref) return
  const range = XLSX.utils.decode_range(ref)
  if (range.e.c >= range.s.c) {
    const headerRef = XLSX.utils.encode_range({
      s: { r: 0, c: range.s.c },
      e: { r: 0, c: range.e.c },
    })
    sheet['!autofilter'] = { ref: headerRef }
  }
}

function downloadXlsx() {
  if (!rows.value.length) return
  const wb = XLSX.utils.book_new()
  const summarySheet = XLSX.utils.aoa_to_sheet([
    ['字段', '内容'],
    ['总记录数', summary.totalRows],
    ['数值非空条数', summary.valueNonNullRows],
    ['数值空值条数', summary.valueNullRows],
    ['查询窗口', comparisonMeta.currentWindowLabel || ''],
    ['同比窗口', comparisonMeta.yoyWindowLabel || ''],
    ['环比窗口', comparisonMeta.momWindowLabel || ''],
    ['计划窗口', comparisonMeta.planWindowLabel || ''],
    ['当前图表口径', comparisonModeLabel.value],
    ['导出时间', new Date().toLocaleString('zh-CN')],
  ])
  finalizeSheet(summarySheet, [18, 50])
  XLSX.utils.book_append_sheet(wb, summarySheet, sanitizeSheetName('汇总信息'))

  const resultHeader = resultColumns.value.map((col) => col.label)
  const resultData = rows.value.map((row) => resultColumns.value.map((col) => {
    if (col.field === 'value') return row?.value == null ? '' : toFiniteOrNull(row.value)
    return getResultCellValue(row, col.field)
  }))
  const resultColWidths = resultColumns.value.map((col) => {
    if (col.field === 'company') return 12
    if (col.field === 'item') return 26
    if (col.field === 'time') return 14
    if (col.field === 'value') return 14
    if (col.field === 'unit') return 12
    return 12
  })
  const resultSheet = XLSX.utils.aoa_to_sheet([resultHeader, ...resultData])
  const resultValueCol = resultColumns.value.findIndex((col) => col.field === 'value')
  if (resultValueCol >= 0) {
    rows.value.forEach((row, index) => {
      setSheetNumericCell(
        resultSheet,
        index + 1,
        resultValueCol,
        row?.value,
        buildExcelValueFormat(row?.unit, row?.item),
      )
    })
  }
  finalizeSheet(resultSheet, resultColWidths)
  XLSX.utils.book_append_sheet(wb, resultSheet, sanitizeSheetName('查询结果'))

  if (comparisonRows.value.length) {
    const compareHeader = ['口径', '指标', '期间', '类型', '本期值', '同期值', '同比差值', '同比差异率', '上期值', '环比差值', '环比差异率', '计划值', '计划差值', '计划差异率']
    const compareData = comparisonRows.value.map((x) => [
      x.company,
      x.item,
      x.period,
      x.type,
      x.currentValue == null ? '' : toFiniteOrNull(x.currentValue),
      x.yoyValue == null ? '' : toFiniteOrNull(x.yoyValue),
      x.currentValue == null || x.yoyValue == null ? '' : toFiniteOrNull(x.currentValue - x.yoyValue),
      x.yoyRate == null ? '' : toFiniteOrNull(x.yoyRate),
      x.momValue == null ? '' : toFiniteOrNull(x.momValue),
      x.currentValue == null || x.momValue == null ? '' : toFiniteOrNull(x.currentValue - x.momValue),
      x.momRate == null ? '' : toFiniteOrNull(x.momRate),
      x.planValue == null ? '' : toFiniteOrNull(x.planValue),
      x.currentValue == null || x.planValue == null ? '' : toFiniteOrNull(x.currentValue - x.planValue),
      x.planRate == null ? '' : toFiniteOrNull(x.planRate),
    ])
    const compareSheet = XLSX.utils.aoa_to_sheet([compareHeader, ...compareData])
    comparisonRows.value.forEach((x, index) => {
      const rowIndex = index + 1
      const valueFormat = buildExcelValueFormat(x.unit, x.item)
      setSheetNumericCell(compareSheet, rowIndex, 4, x.currentValue, valueFormat)
      setSheetNumericCell(compareSheet, rowIndex, 5, x.yoyValue, valueFormat)
      setSheetNumericCell(
        compareSheet,
        rowIndex,
        6,
        x.currentValue == null || x.yoyValue == null ? null : x.currentValue - x.yoyValue,
        valueFormat,
      )
      setSheetNumericCell(compareSheet, rowIndex, 7, x.yoyRate, '0.00%')
      setSheetNumericCell(compareSheet, rowIndex, 8, x.momValue, valueFormat)
      setSheetNumericCell(
        compareSheet,
        rowIndex,
        9,
        x.currentValue == null || x.momValue == null ? null : x.currentValue - x.momValue,
        valueFormat,
      )
      setSheetNumericCell(compareSheet, rowIndex, 10, x.momRate, '0.00%')
      setSheetNumericCell(compareSheet, rowIndex, 11, x.planValue, valueFormat)
      setSheetNumericCell(
        compareSheet,
        rowIndex,
        12,
        x.currentValue == null || x.planValue == null ? null : x.currentValue - x.planValue,
        valueFormat,
      )
      setSheetNumericCell(compareSheet, rowIndex, 13, x.planRate, '0.00%')
    })
    finalizeSheet(compareSheet, [12, 24, 10, 10, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12])
    XLSX.utils.book_append_sheet(wb, compareSheet, sanitizeSheetName('对比明细'))
  }

  if (analysisInsights.value.length) {
    const insightData = analysisInsights.value.map((line, idx) => [`要点${idx + 1}`, line])
    const insightSheet = XLSX.utils.aoa_to_sheet([['序号', '分析结论'], ...insightData])
    finalizeSheet(insightSheet, [12, 120])
    XLSX.utils.book_append_sheet(wb, insightSheet, sanitizeSheetName('专业分析'))
  }

  if (temperatureDailyRows.value.length) {
    const tempRows = temperatureDailyRows.value.map((row) => [
      row.currentDate,
      toFiniteOrNull(row.currentTemp),
      row.yoyDate,
      toFiniteOrNull(row.yoyTemp),
      toFiniteOrNull(row.yoyDiff),
      toFiniteOrNull(row.yoyRate),
    ])
    const tempSheet = XLSX.utils.aoa_to_sheet([
      ['本期日期', '本期气温(℃)', '同期日期', '同期气温(℃)', '同比差值', '同比差异率'],
      ...tempRows,
    ])
    temperatureDailyRows.value.forEach((row, index) => {
      const rowIndex = index + 1
      setSheetNumericCell(tempSheet, rowIndex, 1, row.currentTemp, buildDecimalFormat(2))
      setSheetNumericCell(tempSheet, rowIndex, 3, row.yoyTemp, buildDecimalFormat(2))
      setSheetNumericCell(tempSheet, rowIndex, 4, row.yoyDiff, buildDecimalFormat(2))
      setSheetNumericCell(tempSheet, rowIndex, 5, row.yoyRate, '0.00%')
    })
    finalizeSheet(tempSheet, [14, 12, 14, 12, 12, 12])
    XLSX.utils.book_append_sheet(wb, tempSheet, sanitizeSheetName('气温日序同比'))
    const tempSummarySheet = XLSX.utils.aoa_to_sheet([
      ['字段', '内容'],
      ['本期平均气温', toFiniteOrNull(temperatureSummary.currentAvgTemp)],
      ['同期平均气温', toFiniteOrNull(temperatureSummary.yoyAvgTemp)],
      ['同比差值', toFiniteOrNull(temperatureSummary.yoyAvgDiff)],
      ['同比差异率', toFiniteOrNull(temperatureSummary.yoyAvgRate)],
    ])
    setSheetNumericCell(tempSummarySheet, 1, 1, temperatureSummary.currentAvgTemp, buildDecimalFormat(2))
    setSheetNumericCell(tempSummarySheet, 2, 1, temperatureSummary.yoyAvgTemp, buildDecimalFormat(2))
    setSheetNumericCell(tempSummarySheet, 3, 1, temperatureSummary.yoyAvgDiff, buildDecimalFormat(2))
    setSheetNumericCell(tempSummarySheet, 4, 1, temperatureSummary.yoyAvgRate, '0.00%')
    finalizeSheet(tempSummarySheet, [18, 24])
    XLSX.utils.book_append_sheet(wb, tempSummarySheet, sanitizeSheetName('气温汇总'))
  }

  const monthTag = resolveExportMonthTag()
  const filename = `月报查询分析_${monthTag}.xlsx`
  XLSX.writeFile(wb, filename)
}

function resetAiReportState() {
  aiReportJobId.value = ''
  aiReportStatus.value = 'idle'
  aiReportContent.value = ''
  aiReportStatusMessage.value = ''
  aiReportStage.value = ''
}

function stopAiReportPolling() {
  if (aiReportPollTimer) {
    clearTimeout(aiReportPollTimer)
    aiReportPollTimer = null
  }
}

async function pollAiReport(jobId) {
  if (!jobId) return
  try {
    const payload = await getMonthlyDataShowAiReport('monthly_data_show', jobId)
    if (aiReportJobId.value !== jobId) return
    const status = String(payload?.status || 'pending')
    aiReportStage.value = String(payload?.stage || aiReportStage.value || 'pending')
    aiReportStatus.value = status
    if (status === 'ready') {
      aiReportStage.value = 'ready'
      aiReportContent.value = String(payload?.report || '')
      aiReportStatusMessage.value = aiReportContent.value ? '智能报告生成完成，可下载。' : '智能报告生成完成，但内容为空。'
      stopAiReportPolling()
      return
    }
    if (status === 'failed') {
      aiReportStage.value = 'failed'
      aiReportStatusMessage.value = String(payload?.error || '智能报告生成失败')
      stopAiReportPolling()
      return
    }
    aiReportStatusMessage.value = '智能报告生成中，请稍候…'
    stopAiReportPolling()
    aiReportPollTimer = setTimeout(() => {
      pollAiReport(jobId).catch((err) => console.error(err))
    }, 2000)
  } catch (err) {
    if (aiReportJobId.value !== jobId) return
    aiReportStatusMessage.value = err instanceof Error ? err.message : '获取智能报告状态失败'
    stopAiReportPolling()
  }
}

async function triggerAiReport() {
  if (!aiReportEnabled.value || !comparisonRows.value.length) return
  stopAiReportPolling()
  aiReportStatus.value = 'pending'
  aiReportStage.value = 'pending'
  aiReportStatusMessage.value = '已提交生成请求，正在启动任务…'
  aiReportContent.value = ''
  try {
    const payload = await startMonthlyDataShowAiReport('monthly_data_show', {
      rows: rows.value,
      comparison_rows: comparisonRows.value,
      current_window_label: comparisonMeta.currentWindowLabel || '',
      yoy_window_label: comparisonMeta.yoyWindowLabel || '',
      mom_window_label: comparisonMeta.momWindowLabel || '',
      plan_window_label: comparisonMeta.planWindowLabel || '',
      ai_mode_id: aiModeId.value,
      ai_user_prompt: aiUserPrompt.value.trim(),
    })
    const jobId = String(payload?.ai_report_job_id || '')
    if (!jobId) {
      aiReportStatus.value = 'failed'
      aiReportStatusMessage.value = '智能报告任务未返回 job_id'
      return
    }
    aiReportJobId.value = jobId
    aiReportStatus.value = 'running'
    aiReportStage.value = 'pending'
    aiReportStatusMessage.value = '智能报告生成中，请稍候…'
    await pollAiReport(jobId)
  } catch (err) {
    aiReportStatus.value = 'failed'
    aiReportStage.value = 'failed'
    aiReportStatusMessage.value = err instanceof Error ? err.message : '启动智能报告失败'
  }
}

function downloadAiReport() {
  if (!aiReportContent.value) return
  const blob = new Blob([aiReportContent.value], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `月报智能报告_${resolveExportMonthTag()}.html`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function openAiSettingsDialog() {
  if (!isGlobalAdmin.value) return
  aiSettingsDialogVisible.value = true
}

const loadAiSettingsPayload = () => getAdminAiSettings()
const saveAiSettingsPayload = (payload) => updateAdminAiSettings(payload)
const testAiSettingsPayload = (payload) => testAdminAiSettings(payload)

function buildPayload() {
  const normalizedDateFrom = toMonthStartDate(filters.dateMonthFrom)
  const normalizedDateTo = (() => {
    const explicitTo = toMonthEndDate(filters.dateMonthTo)
    if (explicitTo) return explicitTo
    if (normalizedDateFrom) return toMonthEndDate(filters.dateMonthFrom)
    return null
  })()
  return {
    report_month_from: null,
    report_month_to: null,
    date_from: normalizedDateFrom,
    date_to: normalizedDateTo,
    companies: [...filters.companies],
    items: [...filters.items],
    periods: ['month'],
    types: ['real'],
    order_mode: filters.orderMode,
    order_fields: [...filters.orderFields].filter((x) => x === 'time' || x === 'company' || x === 'item'),
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

function formatMonthInputValue(year, month) {
  return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`
}

function currentMonthText() {
  const now = new Date()
  return formatMonthInputValue(now.getFullYear(), now.getMonth() + 1)
}

function shiftMonthText(monthText, delta) {
  const text = String(monthText || '').trim()
  const matched = text.match(/^(\d{4})-(\d{2})$/)
  const base = matched
    ? new Date(Number(matched[1]), Number(matched[2]) - 1, 1)
    : new Date()
  base.setMonth(base.getMonth() + Number(delta || 0))
  return formatMonthInputValue(base.getFullYear(), base.getMonth() + 1)
}

function ensureBusinessMonthRangeOrder() {
  const from = String(filters.dateMonthFrom || '').trim()
  const to = String(filters.dateMonthTo || '').trim()
  if (!from || !to) return
  if (from <= to) return
  filters.dateMonthTo = from
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

function getSelectionOrder(selectedList, value) {
  const idx = Array.isArray(selectedList) ? selectedList.indexOf(value) : -1
  return idx >= 0 ? idx + 1 : 0
}

async function loadOptions() {
  const payload = await getMonthlyDataShowQueryOptions('monthly_data_show')
  options.companies = Array.isArray(payload?.companies) ? payload.companies : []
  options.items = Array.isArray(payload?.items) ? payload.items : []
  const indicatorPayload = payload?.indicator_config || {}
  indicatorConfig.basicSectionTitle = String(indicatorPayload.basic_section_title || '基本指标')
  indicatorConfig.calculatedSectionTitle = String(indicatorPayload.calculated_section_title || '计算指标')
  indicatorConfig.categoryPlaceholder = String(indicatorPayload.category_placeholder || '【待配置分类】')
  indicatorConfig.basicGroups = Array.isArray(indicatorPayload.basic_groups) ? indicatorPayload.basic_groups : []
  indicatorConfig.basicItems = Array.isArray(indicatorPayload.basic_items) ? indicatorPayload.basic_items : []
  indicatorConfig.calculatedItems = Array.isArray(indicatorPayload.calculated_items) ? indicatorPayload.calculated_items : []
  if (!options.items.includes(AVERAGE_TEMPERATURE_ITEM)) {
    options.items.push(AVERAGE_TEMPERATURE_ITEM)
  }
  options.periods = Array.isArray(payload?.periods) ? payload.periods : []
  options.types = Array.isArray(payload?.types) ? payload.types : []
  filters.periods = ['month']
  filters.types = ['real']
  const previousMonth = shiftMonthText(currentMonthText(), -1)
  filters.dateMonthFrom = previousMonth
  filters.dateMonthTo = ''
}

async function runQuery(resetOffset = false) {
  hasSearched.value = true
  if (resetOffset) offset.value = 0
  if (!filters.companies.length || !filters.items.length) {
    stopAiReportPolling()
    resetAiReportState()
    rows.value = []
    total.value = 0
    comparisonRows.value = []
    temperatureDailyRows.value = []
    temperatureSummary.currentAvgTemp = null
    temperatureSummary.yoyAvgTemp = null
    temperatureSummary.yoyAvgDiff = null
    temperatureSummary.yoyAvgRate = null
    temperatureExpanded.value = false
    comparisonMeta.currentWindowLabel = ''
    comparisonMeta.yoyWindowLabel = ''
    comparisonMeta.momWindowLabel = ''
    comparisonMeta.planWindowLabel = ''
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
          planValue: row.plan_value,
          planRate: row.plan_rate,
        }))
      : []
    const tempPayload = comparePayload?.temperature_comparison
    temperatureDailyRows.value = Array.isArray(tempPayload?.rows)
      ? tempPayload.rows.map((row) => ({
          currentDate: String(row.current_date || ''),
          currentTemp: row.current_temp == null ? null : Number(row.current_temp),
          yoyDate: String(row.yoy_date || ''),
          yoyTemp: row.yoy_temp == null ? null : Number(row.yoy_temp),
          yoyDiff: row.yoy_diff == null ? null : Number(row.yoy_diff),
          yoyRate: row.yoy_rate == null ? null : Number(row.yoy_rate),
        }))
      : []
    temperatureSummary.currentAvgTemp = tempPayload?.summary?.current_avg_temp == null ? null : Number(tempPayload.summary.current_avg_temp)
    temperatureSummary.yoyAvgTemp = tempPayload?.summary?.yoy_avg_temp == null ? null : Number(tempPayload.summary.yoy_avg_temp)
    temperatureSummary.yoyAvgDiff = tempPayload?.summary?.yoy_avg_diff == null ? null : Number(tempPayload.summary.yoy_avg_diff)
    temperatureSummary.yoyAvgRate = tempPayload?.summary?.yoy_avg_rate == null ? null : Number(tempPayload.summary.yoy_avg_rate)
    temperatureExpanded.value = false
    comparisonMeta.currentWindowLabel = String(comparePayload?.current_window_label || '')
    comparisonMeta.yoyWindowLabel = String(comparePayload?.yoy_window_label || '')
    comparisonMeta.momWindowLabel = String(comparePayload?.mom_window_label || '')
    comparisonMeta.planWindowLabel = String(comparePayload?.plan_window_label || '')
    stopAiReportPolling()
    resetAiReportState()
  } catch (error) {
    console.error(error)
    stopAiReportPolling()
    resetAiReportState()
    errorMessage.value = error instanceof Error ? error.message : '查询失败'
    rows.value = []
    total.value = 0
    comparisonRows.value = []
    temperatureDailyRows.value = []
    temperatureSummary.currentAvgTemp = null
    temperatureSummary.yoyAvgTemp = null
    temperatureSummary.yoyAvgDiff = null
    temperatureSummary.yoyAvgRate = null
    temperatureExpanded.value = false
    comparisonMeta.currentWindowLabel = ''
    comparisonMeta.yoyWindowLabel = ''
    comparisonMeta.momWindowLabel = ''
    comparisonMeta.planWindowLabel = ''
    summary.totalRows = 0
    summary.valueNonNullRows = 0
    summary.valueNullRows = 0
    summary.valueSum = 0
  } finally {
    loading.value = false
  }
}

async function resetFilters() {
  stopAiReportPolling()
  resetAiReportState()
  const previousMonth = shiftMonthText(currentMonthText(), -1)
  filters.dateMonthFrom = previousMonth
  filters.dateMonthTo = ''
  filters.companies = []
  filters.items = []
  filters.periods = ['month']
  filters.types = ['real']
  filters.orderMode = 'company_first'
  filters.orderFields = ['time', 'company', 'item']
  filters.aggregateCompanies = false
  filters.aggregateMonths = false
  hasSearched.value = false
  rows.value = []
  total.value = 0
  comparisonRows.value = []
  temperatureDailyRows.value = []
  temperatureSummary.currentAvgTemp = null
  temperatureSummary.yoyAvgTemp = null
  temperatureSummary.yoyAvgDiff = null
  temperatureSummary.yoyAvgRate = null
  temperatureExpanded.value = false
  comparisonMeta.currentWindowLabel = ''
  comparisonMeta.yoyWindowLabel = ''
  comparisonMeta.momWindowLabel = ''
  comparisonMeta.planWindowLabel = ''
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
    temperatureDailyRows.value = []
    temperatureSummary.currentAvgTemp = null
    temperatureSummary.yoyAvgTemp = null
    temperatureSummary.yoyAvgDiff = null
    temperatureSummary.yoyAvgRate = null
    temperatureExpanded.value = false
    comparisonMeta.currentWindowLabel = ''
    comparisonMeta.yoyWindowLabel = ''
    comparisonMeta.momWindowLabel = ''
    comparisonMeta.planWindowLabel = ''
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

onBeforeUnmount(() => {
  stopAiReportPolling()
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
  box-sizing: border-box;
}

.field select[multiple] {
  min-height: 100px;
}

.month-field {
  background: linear-gradient(180deg, #f8fbff 0%, #f1f7ff 100%);
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 8px 10px;
  box-sizing: border-box;
}

.month-input-wrap {
  display: block;
  min-width: 0;
}

.month-input {
  width: 100%;
  min-width: 0;
  height: 34px;
  border-color: #93c5fd !important;
  background: #fff;
  box-sizing: border-box;
}

.month-input:focus {
  outline: none;
  border-color: #2563eb !important;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.field-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-title {
  font-weight: 700;
  color: #1f3a8a;
  font-size: 14px;
  letter-spacing: 0.2px;
}

.inline-actions {
  display: flex;
  gap: 8px;
}

.inline-layout {
  display: grid;
  grid-template-columns: minmax(320px, 1.25fr) minmax(360px, 1fr);
  gap: 10px;
  align-items: stretch;
}

.inline-col {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 8px;
  background: #f8fbff;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 126px;
}

.inline-col .field-head {
  min-height: 28px;
  align-items: center;
}

.order-col,
.aggregate-col {
  justify-content: space-between;
}

.order-col .check-list.slim {
  min-height: 124px;
}

.order-inline {
  display: flex;
  align-items: center;
  gap: 18px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #fff;
  padding: 10px 12px;
  min-height: 66px;
  flex: 1;
}

.order-inline .check-item {
  min-height: 22px;
  white-space: nowrap;
}

.aggregate-col {
  justify-content: flex-start;
}

.aggregate-inline {
  display: flex;
  align-items: center;
  gap: 14px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #fff;
  padding: 10px 12px;
  min-height: 66px;
  flex: 1;
}

.aggregate-item {
  min-height: 22px;
  align-items: center;
  white-space: nowrap;
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

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-bottom: 1px solid #dbeafe;
  background: #eff6ff;
  padding: 0 10px 0 0;
}

.section-title-row .section-title {
  border-bottom: 0;
  background: transparent;
  padding-left: 0;
}

.formula-btn {
  white-space: nowrap;
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

.section-items.grouped {
  grid-template-columns: 1fr;
  gap: 10px;
  max-height: 260px;
}

.basic-group-block {
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
  padding: 8px;
}

.basic-group-title {
  font-size: 12px;
  font-weight: 700;
  color: #1e3a8a;
  margin-bottom: 6px;
}

.basic-group-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px 12px;
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

.ai-toolbar {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ai-prompt-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.ai-prompt-field span {
  font-size: 12px;
  color: #475569;
}

.ai-prompt-field textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  box-sizing: border-box;
}

.ai-status {
  margin-top: 6px;
}

.ai-progress {
  margin: 8px 0 6px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ai-progress__bar {
  height: 8px;
  border-radius: 999px;
  background: #dbeafe;
  overflow: hidden;
}

.ai-progress__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2563eb, #1d4ed8);
  transition: width 0.3s ease;
}

.ai-progress__meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #475569;
}

.ai-progress__steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ai-progress__step {
  font-size: 12px;
  color: #94a3b8;
}

.ai-progress__step.active {
  color: #1d4ed8;
  font-weight: 600;
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
  min-width: 860px;
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
  color: #334155;
  font-size: 13px;
  line-height: 1.7;
}

.insight-line {
  margin: 0;
  white-space: pre-wrap;
}

.insight-line + .insight-line {
  margin-top: 4px;
}

.insight-line.level-1 {
  font-weight: 600;
  color: #0f172a;
  margin-top: 8px;
}

.insight-line.level-2 {
  padding-left: 14px;
  color: #1f2937;
}

.insight-line.level-2.company-title {
  margin-top: 10px;
  padding: 4px 10px;
  border-left: 4px solid #2563eb;
  background: #eff6ff;
  color: #1e3a8a;
  font-size: 14px;
  font-weight: 700;
  border-radius: 6px;
}

.insight-line.level-2.item-title {
  font-weight: 600;
}

.insight-line.level-3 {
  padding-left: 28px;
  color: #334155;
}

.temperature-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.temperature-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.temp-summary-grid {
  margin-top: 4px;
}

.temp-chart-wrap {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  padding: 10px;
  background: #fff;
}

.temp-chart-wrap h5 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #1d4ed8;
}

.temp-chart-container {
  width: 100%;
}

.temp-chart-svg {
  width: 100%;
  height: 220px;
  background: #f8fbff;
  border: 1px solid #dbeafe;
  border-radius: 8px;
}

.temp-axis {
  stroke: #94a3b8;
  stroke-width: 1;
}

.temp-line {
  fill: none;
  stroke-width: 2.4;
}

.temp-line.current {
  stroke: #2563eb;
}

.temp-line.yoy {
  stroke: #16a34a;
  stroke-dasharray: 5 4;
}

.temp-legend {
  margin-top: 6px;
  display: flex;
  gap: 14px;
  font-size: 12px;
  color: #334155;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.legend-dot.current {
  background: #2563eb;
}

.legend-dot.yoy {
  background: #16a34a;
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

.viz-switch-field {
  align-items: center;
}

.mode-switch-group {
  display: inline-flex;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  overflow: hidden;
  background: #eff6ff;
}

.mode-switch-btn {
  border: 0;
  background: transparent;
  color: #1e3a8a;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  line-height: 1.2;
}

.mode-switch-btn + .mode-switch-btn {
  border-left: 1px solid #bfdbfe;
}

.mode-switch-btn.active {
  background: #2563eb;
  color: #fff;
  font-weight: 600;
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

.btn.ghost {
  border-color: #bfdbfe;
  color: #1e40af;
  background: #eff6ff;
  white-space: nowrap;
  writing-mode: horizontal-tb;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.formula-dialog-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.formula-dialog {
  width: min(1100px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #cbd5e1;
  padding: 14px;
}

.formula-dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.formula-dialog-head h4 {
  margin: 0;
}

.formula-table td:nth-child(2) {
  white-space: normal;
  line-height: 1.45;
}

@media (max-width: 900px) {
  .inline-layout {
    grid-template-columns: 1fr 1fr;
  }
  .order-inline,
  .aggregate-inline {
    flex-wrap: wrap;
    row-gap: 8px;
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
  .inline-layout {
    grid-template-columns: 1fr;
  }
}
</style>
