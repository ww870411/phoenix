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
        <label class="dashboard-header__date-group" title="业务日期">
          <span>业务日期：</span>
          <input type="date" v-model="bizDateInput" />
          <span class="dashboard-header__date-hint" v-if="effectiveBizDate">当前：{{ effectiveBizDate }}</span>
          <span class="dashboard-header__date-hint" v-else>当前：regular</span>
        </label>
        <button class="pdf-download-btn" @click="downloadPDF">下载PDF</button>
      </div>
    </header>

    <div v-if="isLoading" class="dashboard-loading-hint">数据载入中，请稍候…</div>

    <section class="dashboard-summary">
      <div class="summary-card summary-card--primary">
        <div class="summary-card__icon summary-card__icon--sunrise" aria-hidden="true"></div>
        <div class="summary-card__meta">
          <div class="summary-card__label">当日平均气温（及同比增量）</div>
          <div class="summary-card__value">
            <template v-if="Number.isFinite(averageTempToday.main)">
              {{ averageTempToday.main.toFixed(1) }}℃
              <span v-if="Number.isFinite(averageTempToday.diff)" class="summary-card__delta">
                ({{ averageTempToday.diff >= 0 ? '+' : '' }}{{ averageTempToday.diff.toFixed(1) }})
              </span>
            </template>
            <template v-else>—</template>
          </div>
        </div>
      </div>
      <div class="summary-card summary-card--success">
        <div class="summary-card__icon summary-card__icon--profit" aria-hidden="true"></div>
        <div class="summary-card__meta">
          <div class="summary-card__label">当日集团可比煤价边际利润</div>
          <div class="summary-card__value">
            <template v-if="primaryMarginHeadline.value !== null">
              {{ formatHeadlineNumber(primaryMarginHeadline.value, primaryMarginHeadline.digits) }} 万元
              <span
                v-if="primaryMarginHeadline.diff !== null"
                class="summary-card__delta"
              >
                （{{ formatHeadlineDelta(
                  primaryMarginHeadline.diff,
                  primaryMarginHeadline.deltaDigits,
                ) }}）
              </span>
            </template>
            <template v-else>—</template>
          </div>
        </div>
      </div>
      <div class="summary-card summary-card--warning">
        <div class="summary-card__icon summary-card__icon--coal" aria-hidden="true"></div>
        <div class="summary-card__meta">
          <div class="summary-card__label">当日集团标煤消耗</div>
          <div class="summary-card__value">
            <template v-if="primaryCoalHeadline.value !== null">
              {{ formatHeadlineNumber(
                primaryCoalHeadline.value,
                primaryCoalHeadline.digits,
                { useThousands: true },
              ) }} 吨标煤
              <span
                v-if="primaryCoalHeadline.diff !== null"
                class="summary-card__delta"
              >
                （{{ formatHeadlineDelta(
                  primaryCoalHeadline.diff,
                  primaryCoalHeadline.deltaDigits,
                  { useThousands: true },
                ) }}）
              </span>
            </template>
            <template v-else>—</template>
          </div>
        </div>
      </div>
      <div class="summary-card summary-card--danger">
        <div class="summary-card__icon summary-card__icon--complaint" aria-hidden="true"></div>
        <div class="summary-card__meta">
          <div class="summary-card__label">当日集团投诉量</div>
          <div class="summary-card__value">
            <template v-if="primaryComplaintHeadline.value !== null">
              {{ primaryComplaintHeadline.value }} 件
              <span
                v-if="primaryComplaintHeadline.diff !== null"
                class="summary-card__delta"
              >
                （{{ formatHeadlineDelta(primaryComplaintHeadline.diff, 0) }}）
              </span>
            </template>
            <template v-else>—</template>
          </div>
        </div>
      </div>
      <div class="summary-card summary-card--outline summary-card--compact">
        <div class="summary-card__meta summary-card__meta--centered">
          <div class="summary-card__label">供暖期平均气温</div>
          <div class="summary-card__value">
            <template v-if="cumulativeSeasonAverageHeadline.value !== null">
              {{ formatHeadlineNumber(
                cumulativeSeasonAverageHeadline.value,
                cumulativeSeasonAverageHeadline.digits,
                { useThousands: cumulativeSeasonAverageHeadline.useThousands },
              ) }}{{ cumulativeSeasonAverageHeadline.unit }}
              <span class="summary-card__delta">
                （{{ formatHeadlineDelta(
                  cumulativeSeasonAverageHeadline.diff,
                  cumulativeSeasonAverageHeadline.deltaDigits,
                  { useThousands: cumulativeSeasonAverageHeadline.useThousands },
                ) }}）
              </span>
            </template>
            <template v-else>—</template>
          </div>
        </div>
      </div>
      <div class="summary-card summary-card--outline summary-card--compact">
        <div class="summary-card__meta summary-card__meta--centered">
          <div class="summary-card__label">供暖期可比煤价边际利润</div>
          <div class="summary-card__value">
            <template v-if="cumulativeMarginHeadline.value !== null">
              {{ formatHeadlineNumber(
                cumulativeMarginHeadline.value,
                cumulativeMarginHeadline.digits,
                { useThousands: cumulativeMarginHeadline.useThousands },
              ) }} {{ cumulativeMarginHeadline.unit }}
              <span class="summary-card__delta">
                （{{ formatHeadlineDelta(
                  cumulativeMarginHeadline.diff,
                  cumulativeMarginHeadline.deltaDigits,
                  { useThousands: cumulativeMarginHeadline.useThousands },
                ) }}）
              </span>
            </template>
            <template v-else>—</template>
          </div>
        </div>
      </div>
      <div class="summary-card summary-card--outline summary-card--compact">
        <div class="summary-card__meta summary-card__meta--centered">
          <div class="summary-card__label">供暖期标煤耗量</div>
          <div class="summary-card__value">
            <template v-if="cumulativeCoalHeadline.value !== null">
              {{ formatHeadlineNumber(
                cumulativeCoalHeadline.value,
                cumulativeCoalHeadline.digits,
                { useThousands: cumulativeCoalHeadline.useThousands },
              ) }} {{ cumulativeCoalHeadline.unit }}
              <span class="summary-card__delta">
                （{{ formatHeadlineDelta(
                  cumulativeCoalHeadline.diff,
                  cumulativeCoalHeadline.deltaDigits,
                  { useThousands: cumulativeCoalHeadline.useThousands },
                ) }}）
              </span>
            </template>
            <template v-else>—</template>
          </div>
        </div>
      </div>
      <div class="summary-card summary-card--outline summary-card--compact">
        <div class="summary-card__meta summary-card__meta--centered">
          <div class="summary-card__label">供暖期投诉量</div>
          <div class="summary-card__value">
            <template v-if="cumulativeComplaintHeadline.value !== null">
              {{ formatHeadlineNumber(
                cumulativeComplaintHeadline.value,
                cumulativeComplaintHeadline.digits,
                { useThousands: cumulativeComplaintHeadline.useThousands },
              ) }} {{ cumulativeComplaintHeadline.unit }}
              <span class="summary-card__delta">
                （{{ formatHeadlineDelta(
                  cumulativeComplaintHeadline.diff,
                  cumulativeComplaintHeadline.deltaDigits,
                  { useThousands: cumulativeComplaintHeadline.useThousands },
                ) }}）
              </span>
            </template>
            <template v-else>—</template>
          </div>
        </div>
      </div>
    </section>

    <main class="dashboard-grid">
      <section class="dashboard-grid__item dashboard-grid__item--temp">
        <Card title="气温变化情况（向后预测3日，含同期）" subtitle="平均气温" extra="单位：℃">
          <EChart :option="tempOpt" height="280px" />
          <div class="dashboard-table-wrapper">
            <Table :columns="temperatureColumns" :data="temperatureTableData" />
          </div>
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--margin">
        <Card title="边际利润简报" extra="单位：万元">
          <EChart :option="marginOpt" height="300px" />
          <div class="dashboard-table-wrapper dashboard-table-wrapper--compact">
            <Table :columns="marginColumns" :data="marginTableData" font-size="11px" />
          </div>
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--income">
        <Card title="收入分类对比（集团）" extra="单位：万元">
          <EChart :option="incomeOpt" height="380px" />
          <div class="dashboard-table-wrapper dashboard-table-wrapper--compact">
            <Table :columns="incomeColumns" :data="incomeTableData" />
          </div>
        </Card>
      </section>
      
      <section class="dashboard-grid__item dashboard-grid__item--complaint">
        <Card
          title="投诉量分项"
          subtitle="本期与同期对比"
          :extra="`单位：${complaintUnit || '件'}`"
        >
          <div class="complaint-charts">
            <div
              v-for="chart in complaintChartConfigs"
              :key="chart.key"
              class="complaint-charts__item"
            >
              <div class="complaint-charts__title">{{ chart.title }}</div>
              <div class="complaint-charts__chart">
                <EChart :option="chart.option" height="260px" />
              </div>
            </div>
          </div>
          <div class="dashboard-table-wrapper dashboard-table-wrapper--small">
            <Table :columns="complaintColumns" :data="complaintTableData" font-size="9px" />
          </div>
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--unit">
        <Card title="供暖热单耗对比" :extra="`单位：${unitSeries.units['供暖热单耗'] || '—'}`">
          <EChart :option="unitHeatOpt" height="450px" />
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--unit">
        <Card title="供暖电单耗对比" :extra="`单位：${unitSeries.units['供暖电单耗'] || '—'}`">
          <EChart :option="unitElecOpt" height="450px" />
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--unit">
        <Card title="供暖水单耗对比" :extra="`单位：${unitSeries.units['供暖水单耗'] || '—'}`">
          <EChart :option="unitWaterOpt" height="450px" />
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--center">
        <Card title="供热分中心单耗明细" :extra="heatingCenterExtraLabel">
          <div class="center-card__controls" role="group" aria-label="供热分中心单耗排序">
            <span class="center-card__controls-label">排序指标：</span>
            <button
              v-for="option in heatingCenterMetricOptions"
              :key="option.key"
              type="button"
              class="center-card__metric-btn"
              :class="{ 'is-active': option.key === heatingCenterMetric }"
              @click="selectHeatingCenterMetric(option.key)"
            >
              {{ option.label }}
            </button>
          </div>
          <div class="center-card__content">
            <EChart :option="heatingCenterOpt" height="340px" />
            <div class="center-card__table">
              <Table
                :columns="heatingCenterTableColumns"
                :data="heatingCenterTableData"
                font-size="7px"
                rowHeight="31px"
              />
            </div>
          </div>
        </Card>
      </section>

      <section class="dashboard-grid__item dashboard-grid__item--coal">
        <Card title="标煤消耗量对比" extra="单位：吨标煤">
          <EChart :option="coalStdOpt" height="340px" />
          <div class="dashboard-table-wrapper">
            <Table :columns="coalStdColumns" :data="coalStdTableData" />
          </div>
        </Card>
      </section>

      

      <section class="dashboard-grid__item dashboard-grid__item--stock">
        <Card title="煤炭库存" subtitle="厂内/港口/在途（堆积）" extra="单位：吨">
          <EChart :option="coalStockOpt" height="300px" />
          <div class="dashboard-table-wrapper">
            <Table :columns="coalStockColumns" :data="coalStockTableData" />
          </div>
        </Card>
      </section>
    </main>

    <footer class="dashboard-footer">
      大连洁净能源集团有限公司  生产日报系统
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
      required: true
    },
    data: {
      type: Array,
      required: true
    },
    fontSize: {
      type: String,
      default: '13px'
    },
    rowHeight: {
      type: String,
      default: ''
    }
  },
  setup(props) {
    const thStyle = {
      padding: '8px 12px',
      fontWeight: '600',
      textAlign: 'left',
      backgroundColor: '#fafafa',
      borderBottom: '1px solid #f0f0f0',
      fontSize: props.fontSize,
      height: props.rowHeight || undefined,
    };
    const tdStyle = {
      padding: '8px 12px',
      borderBottom: '1px solid #f0f0f0',
      fontSize: props.fontSize,
      height: props.rowHeight || undefined,
    };

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
    const normalizeRow = (row, index) => {
      if (Array.isArray(row)) {
        return { key: index, cells: row, meta: {} }
      }
      if (row && typeof row === 'object') {
        const cells = Array.isArray(row.value) ? row.value : []
        const meta =
          row.meta && typeof row.meta === 'object'
            ? row.meta
            : {}
        const key = row.key ?? meta.key ?? index
        return { key, cells, meta }
      }
      return { key: index, cells: [], meta: {} }
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
                  props.columns.map((column) => {
                    const content = Array.isArray(column)
                      ? h('div', { style: { display: 'flex', flexDirection: 'column', alignItems: 'center' } }, [
                          h('div', null, column[0]),
                          h('div', { style: { fontSize: '0.8em', opacity: 0.8 } }, column[1]),
                        ])
                      : column
                    return h(
                      'th',
                      {
                        key: Array.isArray(column) ? column.join('-') : column,
                        style: { ...headerCellInlineStyle, height: props.rowHeight || undefined },
                      },
                      content,
                    )
                  }),
                ),
              )
            : null,
          hasData.value
            ? h(
                'tbody',
                null,
                props.data.map((row, rowIndex) => {
                  const normalized = normalizeRow(row, rowIndex)
                  return h(
                    'tr',
                    {
                      key: normalized.key,
                      class: {
                        'dashboard-table__row--highlight': Boolean(normalized.meta.highlight),
                      },
                    },
                    normalized.cells.map((cell, cellIndex) => {
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
                            height: props.rowHeight || undefined,
                          },
                        },
                        display,
                      )
                    }),
                  )
                }),
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
const bizDateInput = ref('')
const effectiveBizDate = computed(() => {
  const value = bizDateInput.value
  return typeof value === 'string' && value.trim() ? value.trim() : ''
})

const projectKey = 'daily_report_25_26'
let suppressDashboardWatch = false
let activeDashboardRequests = 0
const isLoading = ref(false)

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
  activeDashboardRequests += 1
  isLoading.value = true
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
    activeDashboardRequests = Math.max(activeDashboardRequests - 1, 0)
    suppressDashboardWatch = activeDashboardRequests > 0
    if (activeDashboardRequests === 0) {
      isLoading.value = false
    }
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

const sectionIndexMap = computed(() => {
  const sections = dashboardData.sections || {}
  const map = {}
  Object.keys(sections).forEach((key) => {
    if (typeof key !== 'string') return
    const match = key.match(/^(\d+)\./)
    if (match && !map[match[1]]) {
      map[match[1]] = key
    }
  })
  return map
})

function resolveSection(index, legacyKey) {
  const sections = dashboardData.sections || {}
  const key = sectionIndexMap.value[index]
  if (key && sections[key] && typeof sections[key] === 'object') {
    return sections[key]
  }
  if (legacyKey && sections[legacyKey] && typeof sections[legacyKey] === 'object') {
    return sections[legacyKey]
  }
  return undefined
}

const temperatureSection = computed(() => {
  const section = resolveSection('1', '1.逐小时气温')
  return section && typeof section === 'object' ? section : {}
})

const calcAverageFromList = (values) => {
  if (!Array.isArray(values) || !values.length) return null
  const numbers = values.filter((item) => typeof item === 'number' && Number.isFinite(item))
  if (!numbers.length) return null
  const sum = numbers.reduce((acc, item) => acc + item, 0)
  return Number((sum / numbers.length).toFixed(2))
}

const normalizeDateKey = (value) => {
  if (!value) return ''
  const str = String(value)
  if (str.includes('T')) {
    return str.split('T')[0]
  }
  if (str.includes(' ')) {
    return str.split(' ')[0]
  }
  return str
}

const toDate = (value) => {
  const key = normalizeDateKey(value)
  if (!key) return null
  const timestamp = Date.parse(key)
  return Number.isNaN(timestamp) ? null : new Date(timestamp)
}

const formatDateKey = (date) => {
  if (!(date instanceof Date) || Number.isNaN(date.valueOf())) {
    return ''
  }
  return date.toISOString().slice(0, 10)
}

const shiftDate = (date, offsetDays) => {
  const result = new Date(date)
  result.setDate(result.getDate() + offsetDays)
  return result
}

const shiftYears = (date, offsetYears) => {
  const result = new Date(date)
  const originalMonth = result.getMonth()
  result.setFullYear(result.getFullYear() + offsetYears)
  if (result.getMonth() !== originalMonth) {
    result.setDate(0)
  }
  return result
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
  let labels = mainLabels.length ? mainLabels : peerLabels

  const highlightKey = normalizeDateKey(pushDateValue.value)
  let windowStart = null
  if (highlightKey) {
    const highlightDate = toDate(highlightKey)
    if (highlightDate instanceof Date && !Number.isNaN(highlightDate.valueOf())) {
      windowStart = shiftDate(highlightDate, -3)
      labels = labels.filter((label) => {
        const date = toDate(label)
        if (!(date instanceof Date) || Number.isNaN(date.valueOf())) {
          return true
        }
        return date >= windowStart
      })
    }
  }

  const mapPeerValue = (label) => {
    const date = toDate(label)
    if (!(date instanceof Date) || Number.isNaN(date.valueOf())) {
      return calcAverageFromList(peerBucket[label])
    }
    const peerDate = shiftYears(date, -1)
    const peerKey = formatDateKey(peerDate)
    return calcAverageFromList(peerBucket[peerKey])
  }

  const mainAverages = labels.map((label) => calcAverageFromList(mainBucket[label]))
  const peerAverages = labels.map((label) => mapPeerValue(label))

  const tableRows = labels.map((label, index) => ({
    value: [
      label,
      Number.isFinite(mainAverages[index]) ? mainAverages[index] : '—',
      Number.isFinite(peerAverages[index]) ? peerAverages[index] : '—',
    ],
    meta: {
      highlight: Boolean(
        highlightKey && normalizeDateKey(label) === highlightKey,
      ),
    },
    key: label,
  }))

  return {
    labels,
    mainAverages,
    peerAverages,
    mainChart: mainAverages.map((value) => (Number.isFinite(value) ? value : 0)),
    peerChart: peerAverages.map((value) => (Number.isFinite(value) ? value : 0)),
    tableRows,
  }
})

const averageTempToday = computed(() => {
  const series = temperatureSeries.value
  const highlightKey = normalizeDateKey(pushDateValue.value)
  if (!highlightKey || !series?.labels?.length) {
    return { main: null, peer: null, diff: null }
  }
  const index = series.labels.findIndex(label => normalizeDateKey(label) === highlightKey)
  if (index === -1) {
    return { main: null, peer: null, diff: null }
  }
  const main = series.mainAverages?.[index]
  const peer = series.peerAverages?.[index]
  const diff = (Number.isFinite(main) && Number.isFinite(peer)) ? main - peer : null
  return { main, peer, diff }
})

// --- 边际利润数据映射 ---
const normalizeMetricValue = (value) => {
  if (value === null || value === undefined) return null
  if (typeof value === 'number' && Number.isFinite(value)) return value
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const roundOrZero = (value) => {
  if (value === null || value === undefined) return 0
  return Number.isFinite(value) ? Number(value.toFixed(2)) : 0
}

const LABEL_EPSILON = 1e-9
const shouldDisplayLabel = (value) => Number.isFinite(value) && Math.abs(value) >= LABEL_EPSILON
const formatLabelNumber = (value, digits) => {
  if (!shouldDisplayLabel(value)) return ''
  if (typeof digits === 'number') {
    return Number(value).toFixed(digits)
  }
  return value
}

const roundOrNull = (value, digits = 2) => {
  const normalized = normalizeMetricValue(value)
  return Number.isFinite(normalized) ? Number(normalized.toFixed(digits)) : null
}

const formatIncomeValue = (value) => {
  if (!Number.isFinite(value)) return '—'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatHeadlineNumber = (value, digits = 2, { useThousands = false } = {}) => {
  if (!Number.isFinite(value)) return '—'
  return useThousands
    ? formatWithThousands(value, digits)
    : Number(value).toFixed(digits)
}

const formatHeadlineDelta = (value, digits = 2, { useThousands = false } = {}) => {
  if (!Number.isFinite(value)) return '—'
  const formatted = useThousands
    ? formatWithThousands(Math.abs(value), digits)
    : Math.abs(value).toFixed(digits)
  const sign = value > 0 ? '+' : value < 0 ? '-' : '+'
  return `${sign}${formatted}`
}

const buildCumulativeHeadline = (main, peer, options = {}) => {
  const {
    digits = 2,
    deltaDigits = digits,
    unit = '',
    useThousands = false,
  } = options

  if (!Number.isFinite(main)) {
    return {
      value: null,
      diff: null,
      unit,
      digits,
      deltaDigits,
      useThousands,
    }
  }

  const diff = Number.isFinite(peer) ? main - peer : null
  return {
    value: main,
    diff,
    unit,
    digits,
    deltaDigits,
    useThousands,
  }
}

const computeAverageFromEntries = (entries) => {
  if (!Array.isArray(entries) || !entries.length) return null
  const values = entries
    .map((entry) => normalizeMetricValue(entry?.value))
    .filter((value) => Number.isFinite(value))
  if (!values.length) return null
  const sum = values.reduce((acc, value) => acc + value, 0)
  return sum / values.length
}

const cumulativeSection = computed(() => {
  const section = resolveSection('9', '9.累计卡片')
  return section && typeof section === 'object' ? section : {}
})

const cumulativeUnits = computed(() => {
  const bucket = cumulativeSection.value['计量单位']
  return {
    temperature: bucket?.['平均气温'] || '℃',
    margin: bucket?.['可比煤价边际利润'] || '万元',
    coal: bucket?.['标煤耗量'] || '吨',
    complaints: bucket?.['省市平台投诉量'] || '件',
  }
})

const cumulativeSeasonAverageHeadline = computed(() => {
  const averageBucket = cumulativeSection.value['供暖期平均气温']
  if (!averageBucket || typeof averageBucket !== 'object') {
    return buildCumulativeHeadline(null, null, { unit: cumulativeUnits.value.temperature })
  }
  const main = computeAverageFromEntries(averageBucket['本期'])
  const peer = computeAverageFromEntries(averageBucket['同期'])
  return buildCumulativeHeadline(main, peer, {
    digits: 2,
    unit: cumulativeUnits.value.temperature,
  })
})

const getCumulativeMetric = (label) => {
  const bucket = cumulativeSection.value[label]
  if (!bucket || typeof bucket !== 'object') {
    return { main: null, peer: null }
  }
  return {
    main: normalizeMetricValue(bucket['本期']),
    peer: normalizeMetricValue(bucket['同期']),
  }
}

const cumulativeMarginHeadline = computed(() => {
  const { main, peer } = getCumulativeMetric('集团汇总供暖期可比煤价边际利润')
  return buildCumulativeHeadline(main, peer, {
    digits: 2,
    unit: cumulativeUnits.value.margin,
    useThousands: true,
  })
})

const cumulativeCoalHeadline = computed(() => {
  const { main, peer } = getCumulativeMetric('集团汇总供暖期标煤耗量')
  return buildCumulativeHeadline(main, peer, {
    digits: 0,
    deltaDigits: 0,
    unit: cumulativeUnits.value.coal,
    useThousands: true,
  })
})

const cumulativeComplaintHeadline = computed(() => {
  const { main, peer } = getCumulativeMetric('集团汇总供暖期省市平台投诉量')
  return buildCumulativeHeadline(main, peer, {
    digits: 0,
    deltaDigits: 0,
    unit: cumulativeUnits.value.complaints,
    useThousands: true,
  })
})

const UNIT_COMPANY_ORDER = ['研究院', '庄河环海', '金普热电', '北方热电', '金州热电', '主城区', '集团汇总']
const PREFERRED_GROUP_NAMES = ['集团汇总', '集团全口径', 'Group']

const findPreferredIndex = (candidates = []) => {
  if (!Array.isArray(candidates) || !candidates.length) return -1
  for (const name of PREFERRED_GROUP_NAMES) {
    const idx = candidates.indexOf(name)
    if (idx !== -1) {
      return idx
    }
  }
  return candidates.length ? 0 : -1
}

const pickPreferredOrgValue = (bucket, extractor) => {
  if (!bucket || typeof bucket !== 'object') return null
  const names = [...PREFERRED_GROUP_NAMES, ...Object.keys(bucket)]
  for (const name of names) {
    const record = bucket[name]
    if (!record || typeof record !== 'object') continue
    const value = extractor(record)
    if (Number.isFinite(value)) {
      return value
    }
  }
  return null
}

const unitMetrics = ['供暖热单耗', '供暖电单耗', '供暖水单耗']
const unitFallbackOrgs = [...UNIT_COMPANY_ORDER]
const unitFallbackSeries = unitFallbackOrgs.map((org) => ({
  org,
  heat: 0,
  elec: 0,
  water: 0,
}))
const unitFallbackUnits = {
  '供暖热单耗': 'GJ/万㎡',
  '供暖电单耗': 'kWh/万㎡',
  '供暖水单耗': '吨/万㎡',
}
const unitFallbackMatrix = {
  '供暖热单耗': unitFallbackSeries.map((item) => item.heat),
  '供暖电单耗': unitFallbackSeries.map((item) => item.elec),
  '供暖水单耗': unitFallbackSeries.map((item) => item.water),
}
const orderUnitCompanies = (items) => {
  const seen = new Set()
  const result = []
  UNIT_COMPANY_ORDER.forEach((org) => {
    const found = items.find((item) => item.org === org)
    if (found) {
      result.push(found)
      seen.add(found)
    }
  })
  items.forEach((item) => {
    if (!seen.has(item)) {
      result.push(item)
    }
  })
  return result
}
const coalStdFallbackCategories = ['集团汇总', '主城区', '金州热电', '北方热电', '金普热电', '庄河环海']
const coalStdFallbackCurrent = Array(coalStdFallbackCategories.length).fill(0)
const coalStdFallbackPeer = Array(coalStdFallbackCategories.length).fill(0)
const complaintMetricOrder = ['当日省市平台投诉量', '当日省市平台服务投诉量', '当日净投诉量']
const complaintMetricTitleMap = {
  当日省市平台投诉量: '省市平台投诉量',
  当日省市平台服务投诉量: '省市平台服务投诉量',
  当日净投诉量: '净投诉量',
}
const complaintFallbackCompanies = ['集团汇总', '主城区', '金州热电', '北方热电', '金普热电', '庄河环海', '研究院']

const normalizeComplaintValue = (value) => {
  const normalized = normalizeMetricValue(value)
  if (!Number.isFinite(normalized)) return null
  return Math.round(normalized)
}

const marginSection = computed(() => {
  const section = resolveSection('2', '2.边际利润')
  return section && typeof section === 'object' ? section : {}
})

const marginCurrent = computed(() => {
  const bucket = marginSection.value?.['本期']
  return bucket && typeof bucket === 'object' ? bucket : {}
})

const marginPeer = computed(() => {
  const bucket = marginSection.value?.['同期']
  return bucket && typeof bucket === 'object' ? bucket : {}
})

const marginOrganizations = computed(() => {
  const currentKeys = Object.keys(marginCurrent.value || {})
  if (currentKeys.length) {
    return currentKeys
  }
  return Object.keys(marginPeer.value || {})
})

const marginSeries = computed(() => {
  const orgs = marginOrganizations.value
  return orgs.map((org) => {
    const current = marginCurrent.value?.[org] || {}
    const peer = marginPeer.value?.[org] || {}
    return {
      org,
      direct: normalizeMetricValue(current['直接收入']),
      coal: normalizeMetricValue(current['煤成本']),
      purchaseHeat: normalizeMetricValue(current['外购热成本']),
      utilities: normalizeMetricValue(current['水、电及辅材成本']),
      margin: normalizeMetricValue(current['边际利润']),
      marginCmpCoal: normalizeMetricValue(current['可比煤价边际利润']),
      peerMarginCmpCoal: normalizeMetricValue(peer['可比煤价边际利润']),
    }
  })
})

const incomeSection = computed(() => {
  const section = resolveSection('3', '3.集团汇总收入明细', '3.集团全口径收入明细')
  return section && typeof section === 'object' ? section : {}
})

const incomeCurrent = computed(() => {
  const bucket = incomeSection.value?.['本期']
  return bucket && typeof bucket === 'object' ? bucket : {}
})

const incomePeer = computed(() => {
  const bucket = incomeSection.value?.['同期']
  return bucket && typeof bucket === 'object' ? bucket : {}
})

const incomeSeries = computed(() => {
  const categories = []
  const seen = new Set()
  const currentEntries = incomeCurrent.value
  const peerEntries = incomePeer.value
  if (currentEntries && typeof currentEntries === 'object') {
    for (const key of Object.keys(currentEntries)) {
      if (!seen.has(key)) {
        seen.add(key)
        categories.push(key)
      }
    }
  }
  if (peerEntries && typeof peerEntries === 'object') {
    for (const key of Object.keys(peerEntries)) {
      if (!seen.has(key)) {
        seen.add(key)
        categories.push(key)
      }
    }
  }
  const currentValues = categories.map((label) => normalizeMetricValue(currentEntries?.[label]))
  const peerValues = categories.map((label) => normalizeMetricValue(peerEntries?.[label]))
  return {
    categories,
    current: currentValues,
    peer: peerValues,
  }
})

const complaintSection = computed(() => {
  const section = resolveSection('6', '6.当日省市平台服务投诉量')
  return section && typeof section === 'object' ? section : {}
})

const complaintUnit = computed(() => {
  const unit = complaintSection.value?.['计量单位']
  if (typeof unit === 'string' && unit.trim()) {
    return unit.trim()
  }
  return '件'
})

const complaintMetricKeys = computed(() => {
  const section = complaintSection.value || {}
  const metaKeys = new Set(['数据来源', '查询结构', '计量单位'])
  const ordered = []
  complaintMetricOrder.forEach((metric) => {
    if (Object.prototype.hasOwnProperty.call(section, metric)) {
      ordered.push(metric)
    }
  })
  for (const key of Object.keys(section)) {
    if (metaKeys.has(key) || ordered.includes(key)) continue
    ordered.push(key)
  }
  return ordered.length ? ordered : complaintMetricOrder
})

const complaintBuckets = computed(() => {
  const section = complaintSection.value || {}
  const buckets = {}
  complaintMetricKeys.value.forEach((metric) => {
    const bucket = section[metric]
    if (bucket && typeof bucket === 'object') {
      buckets[metric] = bucket
    }
  })
  return buckets
})

const complaintCompanies = computed(() => {
  const list = []
  const seen = new Set()
  const buckets = complaintBuckets.value
  const phases = ['本期', '同期']
  complaintMetricKeys.value.forEach((metric) => {
    const container = buckets[metric]
    if (!container || typeof container !== 'object') return
    phases.forEach((phase) => {
      const companyBucket = container[phase]
      if (!companyBucket || typeof companyBucket !== 'object') return
      Object.keys(companyBucket).forEach((company) => {
        if (!seen.has(company)) {
          seen.add(company)
          list.push(company)
        }
      })
    })
  })
  return list.length ? list : complaintFallbackCompanies
})

const complaintColumns = computed(() => {
  const columns = ['单位']
  const regex = /(.+)(（.+）)/ // Splits "Metric（unit）" into ["Metric", "（unit）"]
  complaintMetricKeys.value.forEach((metric) => {
    const currentHeader = `${metric}（本期）`
    const peerHeader = `${metric}（同期）`
    const currentMatch = currentHeader.match(regex)
    const peerMatch = peerHeader.match(regex)

    if (currentMatch) {
      columns.push([currentMatch[1], currentMatch[2]])
    } else {
      columns.push(currentHeader)
    }

    if (peerMatch) {
      columns.push([peerMatch[1], peerMatch[2]])
    } else {
      columns.push(peerHeader)
    }
  })
  return columns
})

const complaintTableData = computed(() => {
  const buckets = complaintBuckets.value
  const phases = ['本期', '同期']
  return complaintCompanies.value.map((company) => {
    const row = [company]
    complaintMetricKeys.value.forEach((metric) => {
      phases.forEach((phase) => {
        const value = normalizeComplaintValue(buckets[metric]?.[phase]?.[company])
        row.push(Number.isFinite(value) ? value : '')
      })
    })
    return row
  })
})

const coalStockSection = computed(() => {
  const section = resolveSection('7', '7.煤炭库存明细')
  return section && typeof section === 'object' ? section : {}
})

const coalStockSeries = computed(() => {
  const section = coalStockSection.value
  const metaKeys = new Set(['数据来源', '查询结构', '根指标', '计量单位'])
  const companies = []
  const stacks = []
  const seenStacks = new Set()

  Object.entries(section).forEach(([company, storageMap]) => {
    if (metaKeys.has(company)) return
    if (!storageMap || typeof storageMap !== 'object') return
    companies.push(company)
    Object.keys(storageMap).forEach((storage) => {
      const storageName = String(storage || '').trim()
      if (!storageName || seenStacks.has(storageName)) return
      seenStacks.add(storageName)
      stacks.push(storageName)
    })
  })

  const stacksToUse = stacks.length ? stacks : coalStockFallbackStacks
  const companiesToUse = companies.length ? companies : coalStockFallbackCompanies
  const matrix = stacksToUse.map((stack, stackIndex) => {
    const fallbackRow =
      coalStockFallbackMatrix[stackIndex] ?? companiesToUse.map(() => 0)
    return companiesToUse.map((company, companyIndex) => {
      if (!companies.length) {
        const fallbackValue = Array.isArray(fallbackRow) ? fallbackRow[companyIndex] : 0
        return Number(fallbackValue) || 0
      }
      const raw = section?.[company]?.[stack]
      const numeric = normalizeMetricValue(raw)
      if (Number.isFinite(numeric)) {
        return Number(numeric)
      }
      const fallbackValue = Array.isArray(fallbackRow) ? fallbackRow[companyIndex] : 0
      return Number(fallbackValue) || 0
    })
  })
  const totals = companiesToUse.map((_, companyIndex) =>
    matrix.reduce((sum, stackRow) => {
      const value = stackRow?.[companyIndex]
      return sum + (Number.isFinite(value) ? Number(value) : 0)
    }, 0),
  )

  return { companies: companiesToUse, stacks: stacksToUse, matrix, totals }
})

const coalStockColumns = computed(() => {
  const stacks = coalStockSeries.value.stacks || coalStockFallbackStacks
  return ['单位', ...stacks, '合计']
})

const formatWithThousands = (value, fractionDigits = 0) => {
  if (!Number.isFinite(value)) return ''
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

const coalStockTableData = computed(() => {
  const { companies, stacks, matrix, totals } = coalStockSeries.value
  return companies.map((company, rowIndex) => {
    let total = 0
    const stackValues = stacks.map((_, stackIndex) => {
      const raw =
        Array.isArray(matrix?.[stackIndex]) && Number.isFinite(matrix[stackIndex][rowIndex])
          ? Number(matrix[stackIndex][rowIndex])
          : Number.NaN
      if (Number.isFinite(raw)) {
        total += raw
        return raw
      }
      return null
    })
    const formattedStacks = stackValues.map((value) =>
      value === null ? '' : formatWithThousands(value, 0),
    )
    const totalFormatted = Number.isFinite(totals?.[rowIndex])
      ? formatWithThousands(totals[rowIndex], 0)
      : Number.isFinite(total)
        ? formatWithThousands(total, 0)
        : ''
    return [company, ...formattedStacks, totalFormatted]
  })
})

const unitSection = computed(() => {
  const section = resolveSection('4', '4.供暖单耗')
  return section && typeof section === 'object' ? section : {}
})

const unitCurrent = computed(() => {
  const bucket = unitSection.value?.['本期']
  return bucket && typeof bucket === 'object' ? bucket : {}
})

const unitPeer = computed(() => {
  const bucket = unitSection.value?.['同期']
  return bucket && typeof bucket === 'object' ? bucket : {}
})

const unitOrganizations = computed(() => {
  const categories = []
  const seen = new Set()
  const appendFromBucket = (bucket) => {
    if (!bucket || typeof bucket !== 'object') return
    for (const key of Object.keys(bucket)) {
      if (key === '计量单位') continue
      if (!seen.has(key)) {
        seen.add(key)
        categories.push(key)
      }
    }
  }
  appendFromBucket(unitCurrent.value)
  appendFromBucket(unitPeer.value)
  return categories
})

const unitSeries = computed(() => {
  const categories = unitOrganizations.value
  const metrics = unitMetrics
  const currentEntries = unitCurrent.value
  const peerEntries = unitPeer.value
  const units = unitSection.value?.['计量单位']
  if (!categories.length) {
    return {
      categories: unitFallbackOrgs,
      metrics,
      current: [
        unitFallbackSeries.map((item) => roundOrNull(item.heat)),
        unitFallbackSeries.map((item) => roundOrNull(item.elec)),
        unitFallbackSeries.map((item) => roundOrNull(item.water)),
      ],
      peer: metrics.map(() => unitFallbackOrgs.map(() => null)),
      units: unitFallbackUnits,
    }
  }
  const current = metrics.map((metric) =>
    categories.map((org) => roundOrNull(currentEntries?.[org]?.[metric])),
  )
  const peer = metrics.map((metric) =>
    categories.map((org) => roundOrNull(peerEntries?.[org]?.[metric])),
  )
  return {
    categories,
    metrics,
    current,
    peer,
    units: units && typeof units === 'object' ? units : unitFallbackUnits,
  }
})

const heatingCenterMetricKeys = ['供暖热单耗', '供暖电单耗', '供暖水单耗']
const heatingCenterMetaKeys = new Set(['数据来源', '查询结构', '计量单位'])

const heatingCenterSection = computed(() => {
  const section = resolveSection('8', '8.供热分中心单耗明细')
  return section && typeof section === 'object' ? section : {}
})

const heatingCenterUnits = computed(() => {
  const rawUnits = heatingCenterSection.value?.['计量单位']
  if (rawUnits && typeof rawUnits === 'object') {
    return rawUnits
  }
  return {
    '供暖热单耗': 'GJ/万㎡',
    '供暖电单耗': 'kWh/万㎡',
    '供暖水单耗': '吨/万㎡',
  }
})

const heatingCenterCenters = computed(() => {
  const section = heatingCenterSection.value
  const centers = []
  for (const [name, payload] of Object.entries(section)) {
    if (heatingCenterMetaKeys.has(name)) continue
    if (!payload || typeof payload !== 'object') continue
    const metrics = {}
    let hasValue = false
    heatingCenterMetricKeys.forEach((metric) => {
      const normalized = normalizeMetricValue(payload?.[metric])
      if (Number.isFinite(normalized)) {
        metrics[metric] = Number(normalized)
        hasValue = true
      } else {
        metrics[metric] = null
      }
    })
    if (hasValue) {
      centers.push({ name, metrics })
    }
  }
  return centers
})

const heatingCenterMetricOptions = computed(() => {
  const units = heatingCenterUnits.value || {}
  return heatingCenterMetricKeys.map((metric) => ({
    key: metric,
    label: metric,
    unit: units?.[metric] || '',
  }))
})

const heatingCenterMetric = ref(heatingCenterMetricKeys[0])

watch(
  heatingCenterMetricOptions,
  (options) => {
    if (!options.length) {
      heatingCenterMetric.value = ''
      return
    }
    if (!options.some((option) => option.key === heatingCenterMetric.value)) {
      heatingCenterMetric.value = options[0].key
    }
  },
  { immediate: true },
)

const heatingCenterData = computed(() => {
  const centers = heatingCenterCenters.value
  const metric = heatingCenterMetric.value
  const units = heatingCenterUnits.value || {}
  if (!metric || !centers.length) {
    return { metric, unit: units?.[metric] || '', list: [], average: null }
  }
  const sorted = [...centers].sort((a, b) => {
    const av = a.metrics?.[metric]
    const bv = b.metrics?.[metric]
    if (!Number.isFinite(av) && !Number.isFinite(bv)) return 0
    if (!Number.isFinite(av)) return 1
    if (!Number.isFinite(bv)) return -1
    return av - bv
  })
  const enriched = sorted.map((item, index) => ({
    name: item.name,
    rank: index + 1,
    metrics: item.metrics,
    metricValue: item.metrics?.[metric],
  }))
  const validValues = enriched
    .map((item) => item.metricValue)
    .filter((value) => Number.isFinite(value))
  const average =
    validValues.length > 0
      ? validValues.reduce((sum, value) => sum + Number(value), 0) / validValues.length
      : null
  return {
    metric,
    unit: units?.[metric] || '',
    list: enriched,
    average,
    units,
  }
})

const heatingCenterOpt = computed(() => useHeatingCenterOption(heatingCenterData.value))

const heatingCenterTableColumns = computed(() => {
  const units = heatingCenterUnits.value || {}
  const withUnit = (metric) => {
    const unit = units?.[metric]
    return unit ? [metric, `（${unit}）`] : metric
  }
  return ['排名', '中心', withUnit('供暖热单耗'), withUnit('供暖电单耗'), withUnit('供暖水单耗')]
})

const formatMetricDisplay = (value, digits = 2) => {
  if (!Number.isFinite(value)) return '—'
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

const heatingCenterTableData = computed(() => {
  const list = heatingCenterData.value.list || []
  return list.map((item) => {
    const row = [
      String(item.rank),
      item.name,
      formatMetricDisplay(item.metrics?.['供暖热单耗']),
      formatMetricDisplay(item.metrics?.['供暖电单耗']),
      formatMetricDisplay(item.metrics?.['供暖水单耗']),
    ]
    return {
      key: `${item.rank}-${item.name}`,
      value: row,
      meta: {
        highlight: item.rank === 1,
      },
    }
  })
})

const heatingCenterExtraLabel = computed(() => {
  const unit = heatingCenterData.value.unit
  return unit ? `单位：${unit}` : ''
})

const selectHeatingCenterMetric = (metric) => {
  if (metric && heatingCenterMetric.value !== metric) {
    heatingCenterMetric.value = metric
  }
}

const coalStdSection = computed(() => {
  const section = resolveSection('5', '5.标煤耗量')
  return section && typeof section === 'object' ? section : {}
})

const coalStdCurrent = computed(() => {
  const bucket = coalStdSection.value?.['本期']
  return bucket && typeof bucket === 'object' ? bucket : {}
})

const coalStdPeer = computed(() => {
  const bucket = coalStdSection.value?.['同期']
  return bucket && typeof bucket === 'object' ? bucket : {}
})

const coalStdSeries = computed(() => {
  const categories = []
  const seen = new Set()
  const currentEntries = coalStdCurrent.value
  const peerEntries = coalStdPeer.value
  if (currentEntries && typeof currentEntries === 'object') {
    for (const key of Object.keys(currentEntries)) {
      if (!seen.has(key)) {
        seen.add(key)
        categories.push(key)
      }
    }
  }
  if (peerEntries && typeof peerEntries === 'object') {
    for (const key of Object.keys(peerEntries)) {
      if (!seen.has(key)) {
        seen.add(key)
        categories.push(key)
      }
    }
  }
  if (!categories.length) {
    return {
      categories: coalStdFallbackCategories,
      current: coalStdFallbackCurrent,
      peer: coalStdFallbackPeer,
    }
  }
  const current = categories.map((org) => roundOrNull(currentEntries?.[org], 2) ?? 0)
  const peer = categories.map((org) => roundOrNull(peerEntries?.[org], 2) ?? 0)
  return { categories, current, peer }
})

// --- 模拟数据（后续可替换为后端数据源） ---

const coalStockFallbackStacks = ['厂内存煤', '港口存煤', '在途煤炭']
const coalStockFallbackCompanies = ['集团汇总', '主城区', '金州热电', '北方热电', '金普热电', '庄河环海']
const coalStockFallbackMatrix = coalStockFallbackStacks.map(() =>
  coalStockFallbackCompanies.map(() => 0),
)

// --- 图表配置构造 ---
const pushDateValue = computed(() => dashboardData.meta.pushDate || dashboardData.meta.showDate || '')

const useTempOption = (series, highlightDate) => {
  const highlightKey = normalizeDateKey(highlightDate)
  const highlightIndex =
    highlightKey && Array.isArray(series.labels)
      ? series.labels.findIndex((label) => normalizeDateKey(label) === highlightKey)
      : -1
  const highlightExists = highlightIndex !== -1
  const highlightLabel = highlightExists ? series.labels[highlightIndex] : ''
  const mainChartValue = highlightExists ? series.mainChart?.[highlightIndex] : null
  const peerChartValue = highlightExists ? series.peerChart?.[highlightIndex] : null
  const mainRawValue =
    highlightExists && Array.isArray(series.mainAverages)
      ? series.mainAverages[highlightIndex]
      : null
  const peerRawValue =
    highlightExists && Array.isArray(series.peerAverages)
      ? series.peerAverages[highlightIndex]
      : null

  const formatTempDisplay = (value) => {
    if (!Number.isFinite(value)) return '—'
    return Number(value.toFixed(1)).toString()
  }

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['本期', '同期'], bottom: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: series.labels },
    yAxis: { type: 'value' },
    series: [
      {
        name: '本期',
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
                formatter: () => `业务日期 ${highlightLabel}`,
                color: '#f59e0b',
              },
              data: [{ xAxis: highlightLabel }],
            }
          : undefined,
        markPoint:
          highlightExists && shouldDisplayLabel(mainRawValue) && shouldDisplayLabel(mainChartValue)
            ? {
                symbol: 'circle',
                symbolSize: 10,
                itemStyle: { color: '#1d4ed8', borderColor: '#fff', borderWidth: 1 },
                label: {
                  show: true,
                  formatter: () => `本期 ${formatTempDisplay(mainRawValue)}`,
                  position: 'top',
                  color: '#1d4ed8',
                  fontWeight: 600,
                  borderRadius: 6,
                  padding: [4, 6],
                },
                data: [
                  {
                    coord: [highlightLabel, mainChartValue],
                    value: mainChartValue,
                  },
                ],
              }
            : undefined,
      },
      {
        name: '同期',
        type: 'line',
        smooth: true,
        data: series.peerChart,
        markPoint:
          highlightExists && shouldDisplayLabel(peerRawValue) && shouldDisplayLabel(peerChartValue)
            ? {
                symbol: 'diamond',
                symbolSize: 12,
                itemStyle: { color: '#f97316', borderColor: '#fff', borderWidth: 1 },
                label: {
                  show: true,
                  formatter: () => `同期 ${formatTempDisplay(peerRawValue)}`,
                  position: 'bottom',
                  color: '#f97316',
                  fontWeight: 600,
                  borderRadius: 6,
                  padding: [4, 6],
                },
                data: [
                  {
                    coord: [highlightLabel, peerChartValue],
                    value: peerChartValue,
                  },
                ],
              }
            : undefined,
      },
    ],
  }
}

const useMarginOption = (seriesData) => {
  const series = Array.isArray(seriesData) ? seriesData : []
  const categories = series.map((item) => item.org)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['直接收入', '煤成本', '外购热成本', '水电辅材成本', '可比煤价边际利润'], bottom: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 80 },
    xAxis: { type: 'category', data: categories },
    yAxis: { type: 'value' },
    series: [
      { name: '直接收入', type: 'bar', stack: 'base', data: series.map((item) => roundOrZero(item.direct)) },
      { name: '煤成本', type: 'bar', stack: 'base', data: series.map((item) => -roundOrZero(item.coal)) },
      { name: '外购热成本', type: 'bar', stack: 'base', data: series.map((item) => -roundOrZero(item.purchaseHeat)) },
      { name: '水电辅材成本', type: 'bar', stack: 'base', data: series.map((item) => -roundOrZero(item.utilities)) },
      {
        name: '可比煤价边际利润',
        type: 'line',
        data: series.map((item) => roundOrZero(item.marginCmpCoal)),
        label: {
          show: true,
          formatter: ({ value }) => formatLabelNumber(value, 1),
          position: 'top',
          color: '#0f172a',
          borderRadius: 6,
          padding: [4, 6],
          backgroundColor: 'rgba(255, 255, 255, 0.75)',
        },
        itemStyle: { color: '#2563eb' },
        emphasis: { focus: 'series' },
      },
    ],
  }
}

const useIncomeCompareOption = (seriesData) => {
  const categories = Array.isArray(seriesData?.categories) ? seriesData.categories : []
  const current = Array.isArray(seriesData?.current) ? seriesData.current : []
  const peer = Array.isArray(seriesData?.peer) ? seriesData.peer : []

  const wrapAxisLabel = (label) => {
    if (typeof label !== 'string') return label
    if (label.length <= 4) return label
    return label.replace(/(.{4})/g, '$1\n')
  }

  const tooltipFormatter = (params) => {
    if (!params || !params.length) return ''
    const axisValue = params[0]?.axisValue || params[0]?.name
    const index = categories.indexOf(axisValue)
    if (index === -1) return ''
    const currentVal = current[index]
    const peerVal = peer[index]
    const lines = [`<strong>${axisValue}</strong>`]
    lines.push(`本期：${formatIncomeValue(currentVal)}`)
    lines.push(`同期：${formatIncomeValue(peerVal)}`)
    return lines.join('<br/>')
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: tooltipFormatter,
    },
    legend: { data: ['本期', '同期'], bottom: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 80 },
    xAxis: {
      type: 'category',
      data: categories,
      axisTick: { alignWithLabel: true },
      axisLabel: {
        interval: 0,
        hideOverlap: false,
        formatter: wrapAxisLabel,
        fontSize: 11,
        lineHeight: 16,
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value) => formatIncomeValue(value),
      },
      splitLine: { lineStyle: { type: 'dashed' } },
    },
    series: [
      {
        name: '本期',
        type: 'bar',
        barWidth: 26,
        data: current.map((value) => (Number.isFinite(value) ? value : 0)),
        itemStyle: { color: '#2563eb' },
        label: {
          show: true,
          position: 'top',
          distance: 6,
          formatter: ({ value }) => formatLabelNumber(value, 1),
          color: '#0f172a',
          borderRadius: 6,
          padding: [4, 6],
        },
        labelLayout: { moveOverlap: 'shiftY' },
      },
      {
        name: '同期',
        type: 'bar',
        barWidth: 26,
        data: peer.map((value) => (Number.isFinite(value) ? value : 0)),
        itemStyle: {
          color: '#0ea5e9',
          decal: {
            symbol: 'rect',
            dashArrayX: [1, 0],
            dashArrayY: [4, 4],
            rotation: Math.PI / 4,
            color: 'rgba(14, 165, 233, 0.45)',
          },
        },
        label: {
          show: true,
          position: 'top',
          distance: 6,
          formatter: ({ value }) => formatLabelNumber(value, 1),
          color: '#0f172a',
          borderRadius: 6,
          padding: [4, 6],
        },
        labelLayout: { moveOverlap: 'shiftY' },
      },
    ],
  }
}

const useUnitConsumptionOption = (seriesData, metricName, orientation = 'vertical') => {
  const categories =
    Array.isArray(seriesData?.categories) && seriesData.categories.length
      ? [...seriesData.categories]
      : [...UNIT_COMPANY_ORDER]
  const metrics = Array.isArray(seriesData?.metrics) ? seriesData.metrics : []
  const currentMatrix = Array.isArray(seriesData?.current) ? seriesData.current : []
  const peerMatrix = Array.isArray(seriesData?.peer) ? seriesData.peer : []
  const units = seriesData && typeof seriesData.units === 'object' ? seriesData.units : unitFallbackUnits
  const targetIndex = metrics.indexOf(metricName)
  const metricLabel = targetIndex >= 0 ? metricName : metricName
  const currentData =
    targetIndex >= 0 && Array.isArray(currentMatrix[targetIndex]) && currentMatrix[targetIndex].length
      ? currentMatrix[targetIndex].map((value) => (Number.isFinite(value) ? value : null))
      : unitFallbackMatrix[metricLabel] || categories.map(() => null)
  const peerData =
    targetIndex >= 0 && Array.isArray(peerMatrix[targetIndex]) && peerMatrix[targetIndex].length
      ? peerMatrix[targetIndex].map((value) => (Number.isFinite(value) ? value : null))
      : categories.map(() => null)

  const legendData = []
  const chartSeries = []
  const currentBarColor = '#2563eb'
  const peerBarColor = '#f97316'
  const peerDecalColor = 'rgba(249, 115, 22, 0.35)'

  const resolveItemValue = (item) => {
    if (!item) return Number.NaN
    if (typeof item.value === 'number') return item.value
    if (Array.isArray(item.value)) {
      const candidate = item.value[item.value.length - 1]
      return typeof candidate === 'number' ? candidate : Number.NaN
    }
    if (typeof item.data === 'number') return item.data
    return Number.NaN
  }

  const formatLabelValue = (params) => {
    const value = resolveItemValue(params)
    if (!shouldDisplayLabel(value)) return ''
    return Number(value).toFixed(2)
  }

  const tooltipFormatter = (params) => {
    if (!Array.isArray(params) || !params.length) return ''
    const axisLabel = params[0]?.axisValue ?? params[0]?.name ?? ''
    const lines = [`<strong>${axisLabel}</strong>`]
    params.forEach((item) => {
      const rawName = typeof item.seriesName === 'string' ? item.seriesName : ''
      const metricName = rawName.replace(/（本期）|（同期）/g, '')
      const resolved = resolveItemValue(item)
      const numericValue = Number.isFinite(resolved) ? Number(resolved).toFixed(2) : '—'
      const color = item.color || '#475569'
      lines.push(
        `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:4px;"></span>${rawName}：${numericValue}`,
      )
    })
    return lines.join('<br/>')
  }

  const metricsToRender = targetIndex >= 0 ? [metricLabel] : [metricLabel]

  let chartCategories = categories

  metricsToRender.forEach((metric) => {
    const currentLabel = `${metric}（本期）`
    const peerLabel = `${metric}（同期）`
    legendData.push(currentLabel, peerLabel)

    const zipped = categories.map((org, index) => ({
      org,
      current: currentData[index],
      peer: peerData[index],
    }))
    const ordered = orderUnitCompanies(zipped)
    const filtered = ordered.filter(
      (item) => Number.isFinite(item.current) || Number.isFinite(item.peer),
    )
    const plotItems =
      filtered.length > 0
        ? filtered
        : ordered.length > 0
          ? ordered
          : zipped
    chartCategories = plotItems.map((item) => item.org)
    const plotCurrent = plotItems.map((item) =>
      Number.isFinite(item.current) ? Number(item.current) : null,
    )
    const plotPeer = plotItems.map((item) =>
      Number.isFinite(item.peer) ? Number(item.peer) : null,
    )

    chartSeries.push({
      name: currentLabel,
      type: 'bar',
      barWidth: 24,
      barCategoryGap: '45%',
      barGap: '10%',
      itemStyle: { color: currentBarColor },
      data: plotCurrent,
      label: {
        show: true,
        position: 'top',
        distance: 6,
        formatter: formatLabelValue,
        color: '#0f172a',
        lineHeight: 16,
        borderRadius: 6,
        padding: [4, 6],
        offset: [0, -8],
      },
      labelLayout: { moveOverlap: 'shiftY' },
      emphasis: { focus: 'series' },
    })
    chartSeries.push({
      name: peerLabel,
      type: 'bar',
      barWidth: 24,
      barCategoryGap: '45%',
      barGap: '10%',
      itemStyle: {
        color: peerBarColor,
        opacity: 0.9,
        decal: {
          symbol: 'rect',
          dashArrayX: [1, 0],
          dashArrayY: [4, 4],
          rotation: Math.PI / 4,
          color: peerDecalColor,
        },
      },
      data: plotPeer,
      label: {
        show: true,
        position: 'top',
        distance: 6,
        formatter: formatLabelValue,
        color: '#7c2d12',
        lineHeight: 16,
        borderRadius: 6,
        padding: [4, 6],
        offset: [0, -8],
      },
      emphasis: { focus: 'series' },
    })
  })

  const isHorizontal = orientation === 'horizontal'
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: isHorizontal ? 'shadow' : 'shadow' },
      formatter: tooltipFormatter,
    },
    legend: {
      data: legendData,
      type: 'scroll',
      bottom: 0,
      itemWidth: 16,
      itemHeight: 10,
      icon: 'roundRect',
    },
    grid: isHorizontal
      ? { left: 120, right: 50, top: 50, bottom: 90 }
      : { left: 50, right: 50, top: 70, bottom: 90 },
    xAxis: isHorizontal
      ? {
          type: 'value',
          splitLine: { lineStyle: { type: 'dashed' } },
        }
      : {
          type: 'category',
          data: chartCategories,
          axisTick: { alignWithLabel: true },
          axisLabel: {
            interval: 0,
            hideOverlap: false,
            rotate: 30,
            fontSize: 11,
          },
        },
    yAxis: isHorizontal
      ? {
          type: 'category',
          data: chartCategories,
          axisTick: { alignWithLabel: true },
          axisLabel: { interval: 0, hideOverlap: false },
        }
      : {
          type: 'value',
          splitLine: { lineStyle: { type: 'dashed' } },
        },
    series: chartSeries.map((series) =>
      isHorizontal
        ? {
            ...series,
            barWidth: 16,
            label: series.label
              ? {
                  ...series.label,
                  position: 'right',
                  offset: [6, 0],
                }
              : series.label,
          }
        : series,
    ),
  }
}

const useHeatingCenterOption = (payload) => {
  const list = Array.isArray(payload?.list) ? payload.list : []
  const metric = payload?.metric || ''
  const units = payload?.units || {}
  const unitLabel = units?.[metric] || ''

  const categories = list.map((item) => `${item.rank}. ${item.name}`)
  const dataSource = list.map((item, index) => ({
    value: Number.isFinite(item.metricValue) ? Number(item.metricValue) : 0,
    realValue: item.metricValue,
    name: item.name,
    metrics: item.metrics,
    rank: item.rank,
    index,
  }))

  const formatValue = (value, digits = 2) =>
    Number.isFinite(value)
      ? Number(value).toLocaleString('zh-CN', {
          minimumFractionDigits: digits,
          maximumFractionDigits: digits,
        })
      : '—'

  const tooltipFormatter = (params) => {
    if (!Array.isArray(params) || !params.length) return ''
    const param = params[0]
    const data = param?.data
    if (!data || typeof data !== 'object') return ''
    const centerName = data.name || categories[param.dataIndex] || ''
    const lines = [`<strong>${centerName}</strong>`]
    heatingCenterMetricKeys.forEach((metricKey) => {
      const unit = units?.[metricKey] || ''
      const raw = data.metrics?.[metricKey]
      lines.push(
        `${metricKey}：${formatValue(raw)}${unit ? ` ${unit}` : ''}`,
      )
    })
    return lines.join('<br/>')
  }

  const average = Number.isFinite(payload?.average) ? Number(payload.average) : null

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: tooltipFormatter,
    },
    grid: { left: 120, right: 40, top: 50, bottom: 30 },
    xAxis: {
      type: 'value',
      axisLabel: {
        show: false,
      },
      axisTick: { show: false },
      axisLine: {
        lineStyle: { color: 'rgba(148, 163, 184, 0.4)' },
      },
      splitLine: { lineStyle: { type: 'dashed' } },
      name: '',
    },
    yAxis: {
      type: 'category',
      data: categories,
      axisLabel: { interval: 0, hideOverlap: true },
      axisTick: { alignWithLabel: true },
    },
    series: [
      {
        name: metric,
        type: 'bar',
        barWidth: 16,
        data: dataSource,
        itemStyle: { color: '#2563eb' },
        label: {
          show: true,
          position: 'right',
          color: '#0f172a',
          fontWeight: 500,
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          borderRadius: 6,
          padding: [4, 6],
          formatter: ({ data }) => formatValue(data?.realValue),
        },
        emphasis: { focus: 'series' },
        markLine: average
          ? {
              symbol: 'none',
              lineStyle: { type: 'dashed', color: '#94a3b8' },
              label: {
                show: true,
                formatter: () => `平均 ${formatValue(average)}`,
                color: '#475569',
                padding: [4, 6],
                backgroundColor: 'rgba(241, 245, 249, 0.9)',
                borderRadius: 6,
              },
              data: [{ xAxis: average }],
            }
          : undefined,
      },
    ],
  }
}

const useCoalStdOption = (seriesData) => {
  const categories = Array.isArray(seriesData?.categories) ? seriesData.categories : coalStdFallbackCategories
  const current = Array.isArray(seriesData?.current) ? seriesData.current : coalStdFallbackCurrent
  const peer = Array.isArray(seriesData?.peer) ? seriesData.peer : coalStdFallbackPeer

  const formatValue = (value) => {
    if (!shouldDisplayLabel(value)) return ''
    return formatWithThousands(value, 1)
  }

  const phaseGap = '15%'
  const metricGap = '55%'

  const formatCombinedLabel = ({ value, dataIndex }) => {
    const currentValue = Number.isFinite(value) ? Number(value) : null
    const currentText = formatValue(currentValue)
    const peerValue =
      Array.isArray(peer) && typeof dataIndex === 'number' ? peer[dataIndex] : null
    const peerText = formatValue(peerValue)
    const parts = []
    if (currentText) parts.push(`本期 ${currentText}`)
    if (peerText) parts.push(`同期 ${peerText}`)
    return parts.join('\n') || ''
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        if (!Array.isArray(params) || !params.length) return ''
        const axisLabel = params[0]?.axisValue ?? params[0]?.name ?? ''
        const lines = [`<strong>${axisLabel}</strong>`]
        params.forEach((item) => {
          const color = item.color || '#475569'
          const resolved = Number.isFinite(item.value) ? Number(item.value) : Number.NaN
          lines.push(
            `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:4px;"></span>${item.seriesName}：${Number.isFinite(resolved) ? resolved.toFixed(1) : '—'}`,
          )
        })
        return lines.join('<br/>')
      },
    },
    legend: { data: ['本期', '同期'], bottom: 0 },
    grid: { left: 40, right: 30, top: 50, bottom: 60 },
    xAxis: {
      type: 'category',
      data: categories,
    axisTick: { alignWithLabel: true },
    axisLabel: {
      interval: 0,
      hideOverlap: false,
      rotate: 30,
      fontSize: 11,
    },
  },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { type: 'dashed' } },
      axisLabel: {
        formatter: (val) => (Number.isFinite(val) ? formatWithThousands(val, 0) : val),
      },
    },
    series: [
      {
        name: '本期',
        type: 'bar',
        barWidth: 18,
        data: current.map((value) => (Number.isFinite(value) ? value : null)),
        itemStyle: { color: '#2563eb' },
        label: {
          show: true,
          position: 'top',
          distance: 6,
          formatter: formatCombinedLabel,
          color: '#0f172a',
          lineHeight: 16,
          borderRadius: 6,
          padding: [4, 6],
          offset: [0, -12],
        },
        labelLayout: { moveOverlap: 'shiftY' },
        emphasis: { focus: 'series' },
      },
      {
        name: '同期',
        type: 'bar',
        barWidth: 18,
        data: peer.map((value) => (Number.isFinite(value) ? value : null)),
        itemStyle: {
          color: '#0ea5e9',
          decal: {
            symbol: 'rect',
            dashArrayX: [1, 0],
            dashArrayY: [4, 4],
            rotation: Math.PI / 4,
            color: 'rgba(14, 165, 233, 0.45)',
          },
        },
        label: { show: false },
        labelLayout: { moveOverlap: 'shiftY' },
        emphasis: { focus: 'series' },
      },
    ],
  }
}

const useComplaintSingleOption = (metricKey, { companies, buckets, unitLabel }) => {
  const categories =
    Array.isArray(companies) && companies.length ? companies : complaintFallbackCompanies

  const resolveSeriesData = (phase) =>
    categories.map((company) => {
      const raw = buckets?.[metricKey]?.[phase]?.[company]
      const value = normalizeComplaintValue(raw)
      return Number.isFinite(value) ? value : 0
    })

  const currentData = resolveSeriesData('本期')
  const peerData = resolveSeriesData('同期')
  const formatComplaintLabel = ({ value }) => {
    if (!Number.isFinite(value)) return '—'
    return Number(value).toLocaleString('zh-CN', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })
  }

  const tooltipFormatter = (params) => {
    if (!Array.isArray(params) || !params.length) return ''
    const axisLabel = params[0]?.axisValue ?? params[0]?.name ?? ''
    const suffix = unitLabel ? unitLabel : ''
    const lines = [`<strong>${axisLabel}</strong>`]
    params.forEach((item) => {
      const color = item.color || '#475569'
      const resolved = Number.isFinite(item.value) ? item.value : '—'
      lines.push(
        `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};margin-right:4px;"></span>${item.seriesName}：${resolved}${suffix}`,
      )
    })
    return lines.join('<br/>')
  }

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: tooltipFormatter,
    },
    legend: { data: ['本期', '同期'], bottom: 0 },
    grid: { left: 40, right: 24, top: 50, bottom: 60 },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: {
        hideOverlap: false,
        interval: 0,
        rotate: 30,
        fontSize: 10,
      },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: 'value',
      min: 0,
      minInterval: 1,
      splitLine: { lineStyle: { type: 'dashed' } },
      axisLabel: { hideOverlap: true },
    },
    series: [
      {
        name: '本期',
        type: 'bar',
        barWidth: 20,
        data: currentData,
        itemStyle: { color: '#2563eb' },
        label: {
          show: true,
          position: 'top',
          distance: 6,
          color: '#0f172a',
          formatter: formatComplaintLabel,
        },
        labelLayout: { moveOverlap: 'shiftY' },
        emphasis: { focus: 'series' },
      },
      {
        name: '同期',
        type: 'bar',
        barWidth: 20,
        data: peerData,
        itemStyle: {
          color: '#f97316',
        },
        label: {
          show: true,
          position: 'top',
          distance: 6,
          color: '#0f172a',
          formatter: formatComplaintLabel,
        },
        labelLayout: { moveOverlap: 'shiftY' },
        emphasis: { focus: 'series' },
      },
    ],
  }
}

const useCoalStockOption = (seriesPayload) => {
  const payload = seriesPayload || {}
  const companies =
    Array.isArray(payload.companies) && payload.companies.length
      ? payload.companies
      : coalStockFallbackCompanies
  const stacks =
    Array.isArray(payload.stacks) && payload.stacks.length ? payload.stacks : coalStockFallbackStacks
  const matrix =
    Array.isArray(payload.matrix) && payload.matrix.length === stacks.length
      ? payload.matrix
      : coalStockFallbackMatrix

  const colorMap = {
    厂内存煤: '#2563eb',
    港口存煤: '#f97316',
    在途煤炭: '#22c55e',
  }
  const palette = ['#2563eb', '#f97316', '#22c55e', '#d946ef', '#facc15', '#0ea5e9', '#ef4444']

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: [...stacks], bottom: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 60 },
    xAxis: {
      type: 'category',
      data: companies,
      axisLabel: { hideOverlap: true },
      axisTick: { alignWithLabel: true },
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [
      ...stacks.map((stack, index) => {
        const values = Array.isArray(matrix[index]) ? matrix[index] : companies.map(() => 0)
        return {
          name: stack,
          type: 'bar',
          stack: 'total',
          data: values.map((value) => (Number.isFinite(value) ? Number(value) : 0)),
          itemStyle: { color: colorMap[stack] || palette[index % palette.length] },
        }
      }),
      {
        name: '合计',
        type: 'scatter',
        symbol: 'circle',
        symbolSize: 0,
        data: (payload.totals || []).map((value) => (Number.isFinite(value) ? Number(value) : 0)),
        label: {
          show: true,
          position: 'top',
        formatter: ({ value }) =>
          Number.isFinite(value) ? formatWithThousands(value, 0) : '',
          color: '#0f172a',
          borderRadius: 6,
          padding: [4, 6],
          distance: 6,
        },
        itemStyle: { color: 'transparent' },
        z: 5,
        emphasis: { focus: 'series' },
      },
    ],
  }
}

// --- 图表 option 实例 ---
const tempOpt = computed(() => useTempOption(temperatureSeries.value, pushDateValue.value))
const marginOpt = computed(() => useMarginOption(marginSeries.value))
const incomeOpt = computed(() => useIncomeCompareOption(incomeSeries.value))
const unitHeatOpt = computed(() =>
  useUnitConsumptionOption(unitSeries.value, '供暖热单耗', 'horizontal'),
)
const unitElecOpt = computed(() =>
  useUnitConsumptionOption(unitSeries.value, '供暖电单耗', 'horizontal'),
)
const unitWaterOpt = computed(() =>
  useUnitConsumptionOption(unitSeries.value, '供暖水单耗', 'horizontal'),
)
const coalStdOpt = computed(() => useCoalStdOption(coalStdSeries.value))
const complaintChartConfigs = computed(() => {
  const companies = complaintCompanies.value
  const buckets = complaintBuckets.value
  const unitLabel = complaintUnit.value
  const baseMetrics = complaintMetricKeys.value.length
    ? [...complaintMetricKeys.value]
    : [...complaintMetricOrder]
  const selected = baseMetrics.slice(0, 2)
  if (selected.length < 2) {
    complaintMetricOrder.forEach((metric) => {
      if (!selected.includes(metric)) {
        selected.push(metric)
      }
      if (selected.length === 2) return
    })
  }
  if (!selected.length) {
    selected.push(complaintMetricOrder[0])
  }
  return selected.slice(0, 2).map((metric) => ({
    key: metric,
    title: complaintMetricTitleMap[metric] || metric,
    option: useComplaintSingleOption(metric, { companies, buckets, unitLabel }),
  }))
})
const coalStockOpt = computed(() => useCoalStockOption(coalStockSeries.value))

// --- 表格列与数据 ---
const incomeColumns = ['分类', '本期', '同期']
const temperatureColumns = ['日期', '本期(℃)', '同期(℃)']
const temperatureTableData = computed(() => temperatureSeries.value.tableRows)

const incomeTableData = computed(() => {
  const categories = incomeSeries.value.categories
  const current = incomeSeries.value.current
  const peer = incomeSeries.value.peer
  return categories.map((label, index) => {
    const currentVal = current[index]
    const peerVal = peer[index]
    return [
      label,
      Number.isFinite(currentVal) ? formatIncomeValue(currentVal) : '—',
      Number.isFinite(peerVal) ? formatIncomeValue(peerVal) : '—',
    ]
  })
})

const marginColumns = [
  '单位',
  '直接收入',
  '煤成本',
  '外购热成本',
  '水电辅材成本',
  '边际利润',
  '可比煤价边际利润',
]
const marginTableData = computed(() =>
  marginSeries.value.map((item) => [
    item.org,
    Number.isFinite(item.direct) ? Number(item.direct.toFixed(2)) : null,
    Number.isFinite(item.coal) ? Number(item.coal.toFixed(2)) : null,
    Number.isFinite(item.purchaseHeat) ? Number(item.purchaseHeat.toFixed(2)) : null,
    Number.isFinite(item.utilities) ? Number(item.utilities.toFixed(2)) : null,
    Number.isFinite(item.margin) ? Number(item.margin.toFixed(2)) : null,
    Number.isFinite(item.marginCmpCoal) ? Number(item.marginCmpCoal.toFixed(2)) : null,
  ]),
)

const coalStdColumns = ['单位', '本期', '同期', '差值']
const coalStdTableData = computed(() => {
  const categories = coalStdSeries.value.categories
  const current = coalStdSeries.value.current
  const peer = coalStdSeries.value.peer
  return categories.map((org, index) => {
    const currentVal = current[index]
    const peerVal = peer[index]
    const diff =
      Number.isFinite(currentVal) && Number.isFinite(peerVal)
        ? Number((currentVal - peerVal).toFixed(1))
        : null
    return [
      org,
      Number.isFinite(currentVal) ? Number(currentVal.toFixed(1)) : null,
      Number.isFinite(peerVal) ? Number(peerVal.toFixed(1)) : null,
      diff,
    ]
  })
})


const downloadPDF = () => {
  const { jsPDF } = window.jspdf;
  const dashboard = document.querySelector('.dashboard-page');

  html2canvas(dashboard, {
    useCORS: true,
    scale: 2,
    onclone: (document) => {
      const btn = document.querySelector('.pdf-download-btn');
      if (btn) {
        btn.style.display = 'none';
      }
    },
  }).then(canvas => {
    const imgData = canvas.toDataURL('image/jpeg', 0.95);
    const imgWidth = canvas.width;
    const imgHeight = canvas.height;

    // A4 width in mm is 210. Use this as a standard width.
    const pdfWidth = 210;
    // Calculate the height based on the image's aspect ratio to create a long page.
    const pdfHeight = (imgHeight * pdfWidth) / imgWidth;

    const pdf = new jsPDF({
      orientation: 'p',
      unit: 'mm',
      format: [pdfWidth, pdfHeight]
    });

    pdf.addImage(imgData, 'JPEG', 0, 0, pdfWidth, pdfHeight);
    const formattedDate = (effectiveBizDate.value || bizDateInput.value || '').replace(/-/g, '.');
    pdf.save(`${formattedDate} 洁净能源集团生产日报数据看板.pdf`);
  });
};

// --- 顶部指标展示 ---
const resolveDailyValues = (bucket, targetDate) => {
  if (!bucket || typeof bucket !== 'object' || !targetDate) return undefined
  if (Object.prototype.hasOwnProperty.call(bucket, targetDate)) {
    return bucket[targetDate]
  }
  const normalizedTarget = normalizeDateKey(targetDate)
  return Object.entries(bucket).find(
    ([key]) => normalizeDateKey(key) === normalizedTarget,
  )?.[1]
}

const averageTemp = computed(() => {
  const pushDate = dashboardData.meta.pushDate || dashboardData.meta.showDate || ''
  const mainBucket =
    temperatureSection.value && typeof temperatureSection.value === 'object'
      ? temperatureSection.value['本期']
      : null
  if (!pushDate || !mainBucket || typeof mainBucket !== 'object') {
    return '—'
  }
  const values = resolveDailyValues(mainBucket, pushDate)
  const avg = calcAverageFromList(values)
  if (avg === null || Number.isNaN(avg)) {
    return '—'
  }
  const peerBucket =
    temperatureSection.value && typeof temperatureSection.value === 'object'
      ? temperatureSection.value['同期']
      : null
  const peerValues =
    peerBucket && typeof peerBucket === 'object'
      ? resolveDailyValues(peerBucket, pushDate) ??
        resolveDailyValues(peerBucket, dashboardData.meta.showDate || '')
      : undefined
  const peerAvg = calcAverageFromList(peerValues)
  if (peerAvg === null || Number.isNaN(peerAvg)) {
    return avg.toFixed(2)
  }
  const delta = Number((avg - peerAvg).toFixed(2))
  const sign = delta > 0 ? '+' : delta < 0 ? '' : ''
  return `${avg.toFixed(2)}（${sign}${delta}）`
})
const resolvePreferredMarginEntry = () => {
  const entries = Array.isArray(marginSeries.value) ? marginSeries.value : []
  if (!entries.length) {
    return undefined
  }
  for (const name of PREFERRED_GROUP_NAMES) {
    const entry = entries.find((item) => item.org === name)
    if (entry) {
      return entry
    }
  }
  return entries[0]
}

const primaryMarginHeadline = computed(() => {
  const entry = resolvePreferredMarginEntry()
  const current = normalizeMetricValue(entry?.marginCmpCoal)
  const peer = normalizeMetricValue(entry?.peerMarginCmpCoal)
  return buildCumulativeHeadline(current, peer, {
    digits: 2,
    deltaDigits: 2,
    unit: '万元',
  })
})

const primaryCoalHeadline = computed(() => {
  const series = coalStdSeries.value || {}
  const categories = Array.isArray(series.categories) ? series.categories : []
  const current = Array.isArray(series.current) ? series.current : []
  const peer = Array.isArray(series.peer) ? series.peer : []
  const index = findPreferredIndex(categories)
  const currentValue = index !== -1 ? normalizeMetricValue(current[index]) : null
  const peerValue = index !== -1 ? normalizeMetricValue(peer[index]) : null
  return buildCumulativeHeadline(currentValue, peerValue, {
    digits: 1,
    deltaDigits: 1,
    unit: '吨标煤',
    useThousands: true,
  })
})

const primaryComplaintHeadline = computed(() => {
  const buckets = complaintBuckets.value
  const metricKey = complaintMetricOrder[0]
  const preferredCompanies = ['集团汇总', '主城区', ...complaintCompanies.value]

  const pickValue = (bucket) => {
    if (!bucket || typeof bucket !== 'object') return null
    for (const company of preferredCompanies) {
      const value = normalizeComplaintValue(bucket[company])
      if (Number.isFinite(value)) {
        return value
      }
    }
    for (const key of Object.keys(bucket)) {
      const value = normalizeComplaintValue(bucket[key])
      if (Number.isFinite(value)) {
        return value
      }
    }
    return null
  }

  const main = pickValue(buckets[metricKey]?.['本期'])
  const peer = pickValue(buckets[metricKey]?.['同期'])

  return buildCumulativeHeadline(main, peer, {
    digits: 0,
    deltaDigits: 0,
    unit: '件',
  })
})

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
    gap: 28px;
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

.dashboard-loading-hint {
  margin: 16px 0 32px;
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px dashed rgba(148, 163, 184, 0.55);
  background: rgba(248, 250, 252, 0.95);
  color: #0f172a;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
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
  border-radius: 16px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.16);
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
  width: 44px;
  height: 44px;
  border-radius: 14px;
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
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

.summary-card__meta--centered {
  align-items: center;
  text-align: center;
  width: 100%;
}

.summary-card__value {
  font-size: 24px;
  font-weight: 700;
}

.summary-card__delta {
  margin-left: 6px;
  font-size: 0.85em;
  font-weight: 600;
}

.summary-card--compact {
  padding: 14px;
  gap: 10px;
}

.summary-card--compact .summary-card__icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  font-size: 16px;
}

.summary-card--compact .summary-card__icon::before {
  width: 26px;
  height: 26px;
}

.summary-card--compact .summary-card__label {
  font-size: 11px;
}

.summary-card--compact .summary-card__value {
  font-size: 19px;
}

.summary-card--outline {
  background: transparent;
  color: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.18);
  box-shadow: none;
  justify-content: center;
}

.summary-card--outline::after {
  display: none;
}

.summary-card--outline .summary-card__label {
  color: #475569;
  opacity: 1;
  text-transform: none;
  letter-spacing: 0.04em;
  font-size: 14px;
}

.summary-card--outline .summary-card__value {
  color: #0f172a;
  font-size: 20px;
  text-align: center;
}

.summary-card--outline .summary-card__delta {
  color: #2563eb;
}

.summary-card--outline.summary-card--compact {
  padding: 12px;
  gap: 8px;
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

.summary-card--stock {
  background: linear-gradient(135deg, #1f2937, #4b5563);
}

.summary-card--heat {
  background: linear-gradient(135deg, #f97316, #fb923c);
}

.summary-card--electric {
  background: linear-gradient(135deg, #6366f1, #a855f7);
}

.summary-card--water {
  background: linear-gradient(135deg, #0ea5e9, #22d3ee);
}

.summary-card__icon--storage::before {
  mask-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M3 20V8l9-5l9 5v12H3Zm9-7l7-3.89l-7-3.89l-7 3.89Zm0 2.1l-7-3.89V18l7 3.89l7-3.89v-6.79Z"/></svg>');
}

.summary-card__icon--heat::before {
  mask-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M11.5 22q-2.3 0-3.9-1.6T6 16.5q0-1.05.413-2.1T7.5 12q1.05-1.2 1.775-2.563T10 6q0-1.2-.4-2.275T8.5 1q2.2 1.05 3.35 2.938T13 8.5q0 1.5-.363 2.938T11.5 13.5q-1.2 1.45-1.85 2.738T9 19q0 1.2.8 2.1t1.7.9q1.05 0 1.775-.787T14 19.5q0-.95-.4-1.9t-1.1-2q2.2 1.25 3.35 2.887T17 19.5q0 2.1-1.45 3.8T11.5 22Z"/></svg>');
}

.summary-card__icon--electric::before {
  mask-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M9 22v-7H5l8-13v7h4Z"/></svg>');
}

.summary-card__icon--water::before {
  mask-image: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M12 22q-3.225 0-5.612-2.188T4 14.5q0-1.05.363-2.138T5.5 10Q7.6 7.45 8.8 5.075T10 1q1.45 1.75 2.725 3.4T15.5 10q1.1 1.35 1.55 2.437T17 14.5q0 3.125-2.388 5.313T12 22Z"/></svg>');
}

  .dashboard-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 14px;
    grid-auto-rows: minmax(300px, auto);
    align-items: stretch;
  }

  .dashboard-grid__item {
    min-width: 0;
    position: relative;
    z-index: auto;
    display: flex;
  }

  .dashboard-grid__item > .dashboard-card {
    flex: 1 1 auto;
  }

@media (min-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: repeat(12, minmax(0, 1fr));
  }

  .dashboard-grid__item--temp {
    grid-column: span 6;
  }

  .dashboard-grid__item--margin {
    grid-column: span 6;
  }

  .dashboard-grid__item--temp .dashboard-card,
  .dashboard-grid__item--margin .dashboard-card {
    min-height: 320px;
  }

  .dashboard-grid__item--income {
    grid-column: span 4;
  }

  .dashboard-grid__item--unit {
    grid-column: span 4;
  }

  .dashboard-grid__item--coal {
    grid-column: span 6;
  }

  .dashboard-grid__item--center {
    grid-column: 1 / -1;
  }

  .dashboard-grid__item--complaint {
    grid-column: span 8;
    min-height: 360px;
  }

  .dashboard-grid__item--stock {
    grid-column: span 6;
  }
}

.dashboard-card {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.10);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  height: 100%;
  min-height: 100%;
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
  flex: 1 1 auto;
}

.dashboard-chart {
  width: 100%;
}

.dashboard-table-wrapper {
  margin-top: 8px;
  width: 100%;
}

.dashboard-table-wrapper--compact {
  flex: 1 1 auto;
  display: flex;
}

.dashboard-table-wrapper--compact > .dashboard-table {
  flex: 1 1 auto;
  overflow: auto;
}

.dashboard-table-wrapper--small .dashboard-table table {
  font-size: 11px;
}

.complaint-charts {
  display: grid;
  gap: 16px;
}

@media (min-width: 768px) {
  .complaint-charts {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.complaint-charts__item {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.complaint-charts__title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.complaint-charts__chart {
  flex: 1 1 auto;
  min-height: 0;
}

.center-card__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.center-card__controls-label {
  font-size: 13px;
  color: #475569;
}

.center-card__metric-btn {
  border: 1px solid rgba(148, 163, 184, 0.5);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  color: #475569;
  background: rgba(248, 250, 252, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
}

.center-card__metric-btn.is-active {
  color: #0f172a;
  background: rgba(37, 99, 235, 0.12);
  border-color: #2563eb;
  font-weight: 600;
}

.center-card__content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (min-width: 1024px) {
  .center-card__content {
    flex-direction: row;
    align-items: stretch;
    gap: 24px;
  }
}

.center-card__content .dashboard-chart {
  flex: 0 0 50%;
  min-width: 0;
}

.center-card__table {
  flex: 1 1 50%;
  min-width: 0; /* Allow shrinking */
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 8px 0 0;
  height: 100%;
}

.center-card__table .dashboard-table {
  box-shadow: none;
  flex: 1 1 auto;
}

@media (max-width: 1023px) {
  .center-card__content .dashboard-chart,
  .center-card__table {
    flex: 1 1 auto;
    padding: 0;
  }

  .center-card__table {
    max-height: none;
  }
}

.center-card__table .dashboard-table th,
.center-card__table .dashboard-table td {
  padding: 12px 18px;
}

.dashboard-table-wrapper--small .dashboard-table th,
.dashboard-table-wrapper--small .dashboard-table td {
  padding: 8px 12px;
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
  box-sizing: border-box;
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

.dashboard-table__row--highlight td {
  background: rgba(37, 99, 235, 0.12);
  font-weight: 600;
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

/* === layout polish patch (added) === */

/* Table cards: vertical scroll + sticky headers */
@media (min-width: 1024px) {
  .dashboard-card .dashboard-table-wrapper {
    max-height: 320px;
    overflow: auto;
    -webkit-overflow-scrolling: touch;
  }
}
.dashboard-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--card-bg, #fff);
}

/* Keep table cells tidy on wide rows */
.dashboard-table th,
.dashboard-table td {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 0;
}

/* Optional: make table-heavy cards take a full row on desktop */
@media (min-width: 1024px) {
  .dashboard-grid__item--table { grid-column: 1 / -1; }
}
/* === end patch === */

.pdf-download-btn {
  background-color: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.pdf-download-btn:hover {
  background-color: #1d4ed8;
}



</style>
  padding: 0;
