<template>
  <div class="water-dumbbell-card">
    <!-- 1. 顶部标题与图例栏 -->
    <div class="water-dumbbell-header">
      <div class="water-dumbbell-header__left">
        <h3 class="water-dumbbell-title">各单位热网耗水量对比情况</h3>
      </div>

      <div class="water-dumbbell-header__right">
        <!-- 图例标识 -->
        <div class="water-legend-chips">
          <span class="legend-chip">
            <span class="chip-dot chip-dot--curr"></span>今年本期
          </span>
          <span class="legend-chip">
            <span class="chip-tick chip-tick--peer"></span>去年同期 (标杆线)
          </span>
          <span class="legend-chip">
            <span class="chip-line chip-line--saving"></span>节水/少补
          </span>
          <span class="legend-chip">
            <span class="chip-line chip-line--waste"></span>增耗/多补
          </span>
          <span class="water-unit-hint">单位：吨</span>
        </div>

      </div>
    </div>

    <!-- 2. 全口径指标概览栏（置于最上方） -->
    <div v-if="hasData" class="water-global-summary-bar">
      <!-- 本日全口径 -->
      <div class="water-global-metric">
        <div class="water-global-metric__title">
          <span class="water-global-metric__name">本日全口径热网耗水量</span>
          <span class="water-global-metric__date">({{ dayDimData.biz_range }})</span>
        </div>
        <div class="water-global-metric__body">
          <div class="water-global-metric__val">
            <strong>{{ formatNumber(dayTotal.current) }}</strong>
            <span class="water-global-metric__unit">吨</span>
          </div>
          <div class="water-global-metric__compare" :class="dayTotal.diff <= 0 ? 'is-good' : 'is-warn'">
            <span class="water-global-metric__peer">去年同期 {{ formatNumber(dayTotal.peer) }} 吨</span>
            <span class="water-global-metric__sep">|</span>
            <span class="water-global-metric__diff">
              {{ dayTotal.diff <= 0 ? '▼ 同比少补' : '▲ 同比多补' }}
              {{ formatNumber(Math.abs(dayTotal.diff)) }} 吨
              ({{ (dayTotal.diff_rate > 0 ? '+' : '') + dayTotal.diff_rate }}%)
            </span>
          </div>
        </div>
      </div>

      <div class="water-global-metric__divider"></div>

      <!-- 供暖期全口径 -->
      <div class="water-global-metric">
        <div class="water-global-metric__title">
          <span class="water-global-metric__name">供暖期全口径热网耗水量</span>
          <span class="water-global-metric__date">({{ seasonDimData.biz_range }})</span>
        </div>
        <div class="water-global-metric__body">
          <div class="water-global-metric__val">
            <strong>{{ formatNumber(seasonTotal.current) }}</strong>
            <span class="water-global-metric__unit">吨</span>
          </div>
          <div class="water-global-metric__compare" :class="seasonTotal.diff <= 0 ? 'is-good' : 'is-warn'">
            <span class="water-global-metric__peer">去年同期 {{ formatNumber(seasonTotal.peer) }} 吨</span>
            <span class="water-global-metric__sep">|</span>
            <span class="water-global-metric__diff">
              {{ seasonTotal.diff <= 0 ? '▼ 同比少补' : '▲ 同比多补' }}
              {{ formatNumber(Math.abs(seasonTotal.diff)) }} 吨
              ({{ (seasonTotal.diff_rate > 0 ? '+' : '') + seasonTotal.diff_rate }}%)
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载中与错误态 -->
    <div v-if="loading && !hasData" class="water-state-box">
      <div class="water-spinner"></div>
      <span>正在读取各单位热网耗水数据…</span>
    </div>
    <div v-else-if="errorMsg" class="water-state-box water-state-box--error">
      <span>{{ errorMsg }}</span>
      <button type="button" class="water-retry-btn" @click="loadData">重试</button>
    </div>

    <!-- 3. 左右双栏：左侧本日，右侧供暖期累计（双层自适应标尺） -->
    <div v-show="hasData" class="water-columns-grid">
      <!-- ===== 左栏：本日 ===== -->
      <div class="water-column">
        <div class="water-column-header">
          <div class="water-column-header__left">
            <span class="water-dim-badge water-dim-badge--day">本日</span>
          </div>
        </div>

        <!-- 左侧哑铃图（包含集团汇总、主城区与外围双标尺） -->
        <div class="water-chart-wrapper">
          <div ref="dayChartRef" class="water-chart-container" style="height: 450px;"></div>
          <div class="water-scale-divider">
            <div class="water-scale-divider__line"></div>
            <span class="water-scale-divider__text">标尺尺度不同</span>
            <div class="water-scale-divider__line"></div>
          </div>
        </div>
      </div>

      <!-- 中间竖向分割线 -->
      <div class="water-columns-divider"></div>

      <!-- ===== 右栏：供暖期累计 ===== -->
      <div class="water-column">
        <div class="water-column-header">
          <div class="water-column-header__left">
            <span class="water-dim-badge water-dim-badge--season">供暖期累计</span>
          </div>
        </div>

        <!-- 右侧哑铃图（包含集团汇总、主城区与外围双标尺） -->
        <div class="water-chart-wrapper">
          <div ref="seasonChartRef" class="water-chart-container" style="height: 450px;"></div>
          <div class="water-scale-divider">
            <div class="water-scale-divider__line"></div>
            <span class="water-scale-divider__text">标尺尺度不同</span>
            <div class="water-scale-divider__line"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getDashboardNetworkWaterDumbbell } from '../services/api'

const props = defineProps({
  projectKey: {
    type: String,
    default: 'daily_report_25_26',
  },
  bizDate: {
    type: String,
    default: '',
  },
})

const loading = ref(false)
const errorMsg = ref('')
const dumbbellData = ref(null)

const dayChartRef = ref(null)
const seasonChartRef = ref(null)

let dayChartInstance = null
let seasonChartInstance = null
let resizeObserver = null
let abortController = null

const dayDimData = computed(() => dumbbellData.value?.dimensions?.day || null)
const seasonDimData = computed(() => dumbbellData.value?.dimensions?.season || null)

const hasData = computed(() => !!(dayDimData.value && seasonDimData.value))

const dayTotal = computed(() => {
  return dayDimData.value?.total || { current: 0, peer: 0, diff: 0, diff_rate: 0 }
})

const seasonTotal = computed(() => {
  return seasonDimData.value?.total || { current: 0, peer: 0, diff: 0, diff_rate: 0 }
})

const formatNumber = (val) => {
  if (val === null || val === undefined || isNaN(val)) return '—'
  return Math.round(Number(val)).toLocaleString('zh-CN')
}

const formatCompactValue = (val) => {
  const absVal = Math.abs(val)
  if (absVal >= 100000) {
    const wan = absVal / 10000
    return wan % 1 === 0 ? `${wan}万` : `${Math.round(wan)}万`
  }
  return `${formatNumber(absVal)}`
}

// 刻度按整千划分，换算成“万”最多一位小数，不影响数据标签整数显示。
const formatAxisTick = (value) => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return ''
  if (Math.abs(numeric) >= 10000) {
    return `${Number((numeric / 10000).toFixed(1))}万`
  }
  return `${Math.round(numeric)}`
}

const loadData = async () => {
  abortController?.abort()
  const requestController = new AbortController()
  abortController = requestController

  // 新查询开始即隐藏旧结果，避免切换日期失败后继续展示上一日期的汇总和图表。
  dumbbellData.value = null
  loading.value = true
  errorMsg.value = ''

  try {
    const res = await getDashboardNetworkWaterDumbbell(props.projectKey, {
      showDate: props.bizDate,
      signal: requestController.signal,
    })

    // 即使请求未响应取消，也只允许最新查询提交结果。
    if (abortController !== requestController) return
    if (res?.ok && res.dimensions) {
      dumbbellData.value = res
      await nextTick()
      if (abortController === requestController) renderBothCharts()
    } else {
      throw new Error(res?.message || '返回数据格式不符合预期')
    }
  } catch (err) {
    if (abortController === requestController && err.name !== 'AbortError') {
      errorMsg.value = err.message || '获取热网耗水量数据失败'
      console.error('[NetworkWaterDumbbell] 加载失败:', err)
    }
  } finally {
    if (abortController === requestController) loading.value = false
  }
}

/**
 * 构建双层分级自适应标尺图表 Option
 * Grid 0: 主城区 (专属万吨级标尺，避免压扁外围)
 * Grid 1: 外围五单位 (自适应千吨级精细标尺，分辨率瞬间放大 3.5 ~ 4 倍!)
 */
const buildDumbbellOption = (dimData, isSeason = false) => {
  if (!dimData || !Array.isArray(dimData.items) || dimData.items.length === 0) {
    return {}
  }

  const allItems = dimData.items
  // 分离主城区与外围 5 家单位
  const mainItem = allItems.find((i) => i.key === 'ZhuChengQu') || allItems[0]
  const subItems = allItems.filter((i) => i.key !== 'ZhuChengQu')

  // 构建集团汇总项（置于主城区上方，与主城区共用标尺）
  const groupTotalItem = {
    key: 'JiTuanHuiZong',
    name: '集团汇总',
    desc: '全口径热网耗水量总和',
    current: dimData.total?.current ?? 0,
    peer: dimData.total?.peer ?? 0,
    diff: dimData.total?.diff ?? 0,
    diff_rate: dimData.total?.diff_rate ?? 0,
  }

  // --- Grid 0: 集团汇总 + 主城区（共用同一标尺）---
  const topItems = [groupTotalItem, mainItem]
  const topCategories = ['集团汇总', '主城区']
  const topMax = Math.max(...topItems.flatMap((i) => [i.current, i.peer]), 100)
  const topTrackEnd = Math.ceil(topMax * 1.05 / 1000) * 1000

  const topTrackData = topItems.map(() => topTrackEnd)
  const topBaseBarData = topItems.map((i) => Math.min(i.current, i.peer))
  const topRodBarData = topItems.map((i) => ({
    value: Math.abs(i.diff),
    itemStyle: {
      color: i.diff <= 0 ? '#10b981' : '#f43f5e',
      borderRadius: 3,
    },
  }))
  const topPeerScatterData = topItems.map((i, idx) => [i.peer, idx, i])
  const topCurrScatterData = topItems.map((i, idx) => [i.current, idx, i])
  const topLabelScatterData = topItems.map((i, idx) => [Math.max(i.current, i.peer), idx, i])

  // --- Grid 1: 外围五单位标尺计算（主城区标尺上限的 2/5 并向上取整到整千）---
  const subCategories = subItems.map((i) => i.name)
  const subMax = Math.max(...subItems.flatMap((i) => [i.current, i.peer]), 100)
  // 主城区自身的最大值上限
  const mainMax = Math.max(mainItem.current, mainItem.peer, 100)
  const mainTrackEnd = Math.ceil(mainMax * 1.05 / 1000) * 1000
  // 规则：下方各单位标尺最大值 = 主城区标尺上限的 2/5 并向上取整（整千）
  const twoFifthsMain = (mainTrackEnd * 2) / 5
  const ceilThousand = Math.ceil(twoFifthsMain / 1000) * 1000
  const subTrackEnd = Math.max(ceilThousand, 1000, Math.ceil(subMax * 1.06 / 1000) * 1000)

  const subTrackData = subItems.map(() => subTrackEnd)
  const subBaseBarData = subItems.map((i) => Math.min(i.current, i.peer))
  const subRodBarData = subItems.map((i) => ({
    value: Math.abs(i.diff),
    itemStyle: {
      color: i.diff <= 0 ? '#10b981' : '#f43f5e',
      borderRadius: 3,
    },
  }))
  const subPeerScatterData = subItems.map((i, idx) => [i.peer, idx, i])
  const subCurrScatterData = subItems.map((i, idx) => [i.current, idx, i])
  const subLabelScatterData = subItems.map((i, idx) => [Math.max(i.current, i.peer), idx, i])

  const currValFormatter = (params) => {
    const d = params.data?.[2]
    if (!d || d.current == null) return ''
    const val = Number(d.current)
    if (isNaN(val)) return ''
    if (isSeason && Math.abs(val) >= 100000) {
      const wan = Math.abs(val) / 10000
      const roundedWan = Math.round(wan)
      return `${val < 0 ? '-' : ''}${roundedWan}万`
    }
    return Math.round(val).toLocaleString('zh-CN')
  }

  const labelFormatter = (params) => {
    const d = params.data?.[2]
    if (!d) return ''
    const diffSign = d.diff > 0 ? '+' : ''
    const rateStr = d.diff_rate != null ? ` (${diffSign}${d.diff_rate}%)` : ''
    const diffVal = formatCompactValue(d.diff)

    if (d.diff < 0) {
      return `{saving|▼ -${diffVal}${rateStr}}`
    } else if (d.diff > 0) {
      return `{waste|▲ +${diffVal}${rateStr}}`
    } else {
      return '{equal|-- 持平}'
    }
  }

  const containerWidth = dayChartRef.value?.clientWidth || (typeof window !== 'undefined' ? window.innerWidth : 800)
  const isNarrow = containerWidth > 0 && containerWidth < 500

  const richStyles = {
    saving: {
      color: '#047857',
      backgroundColor: '#ecfdf5',
      borderColor: '#a7f3d0',
      borderWidth: 1.5,
      borderRadius: 6,
      padding: isNarrow ? [2, 5] : [3, 7],
      fontSize: isNarrow ? 11 : 12,
      fontWeight: 700,
    },
    waste: {
      color: '#b91c1c',
      backgroundColor: '#fef2f2',
      borderColor: '#fecaca',
      borderWidth: 1.5,
      borderRadius: 6,
      padding: isNarrow ? [2, 5] : [3, 7],
      fontSize: isNarrow ? 11 : 12,
      fontWeight: 700,
    },
    equal: {
      color: '#475569',
      backgroundColor: '#f8fafc',
      borderColor: '#cbd5e1',
      borderWidth: 1,
      borderRadius: 6,
      padding: isNarrow ? [2, 5] : [3, 7],
      fontSize: isNarrow ? 11 : 12,
      fontWeight: 600,
    },
  }

  return {
    animationDuration: 600,
    animationEasing: 'cubicOut',
    // 两个垂直叠放的绘图 Grid（左侧留足大字号单位名称，右侧留足大胶囊空间）
    grid: [
      // Grid 0: 集团汇总 + 主城区 (顶部独立双行，共用同一大标尺)
      {
        top: 20,
        height: 76,
        left: isNarrow ? 70 : 84,
        right: isNarrow ? 86 : 105,
        containLabel: false,
      },
      // Grid 1: 外围五单位 (下方5行自适应区域，标尺为主城区的2/5向上取整千)
      {
        top: 160,
        height: 230,
        left: isNarrow ? 70 : 84,
        right: isNarrow ? 86 : 105,
        containLabel: false,
      },
    ],
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.94)',
      borderColor: 'rgba(148, 163, 184, 0.25)',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: '#fff', fontSize: 13 },
      extraCssText: 'box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4); border-radius: 8px; z-index: 99;',
      formatter: (params) => {
        const d = params.data?.[2]
        if (!d) return ''
        const isSaving = d.diff <= 0
        const statusText = isSaving ? '节水 / 少补' : '增耗 / 多补'
        const statusColor = isSaving ? '#34d399' : '#f87171'
        const diffSign = d.diff > 0 ? '+' : ''
        const rateText = d.diff_rate != null ? ` (${diffSign}${d.diff_rate}%)` : ''
        const scopeTitle = isSeason ? '供暖期累计' : '本日'

        return `
          <div style="font-weight: 600; font-size: 14px; margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.15); padding-bottom: 4px;">
            🏢 【${d.name}】热网耗水量 (${scopeTitle})
            <span style="font-size:11px; font-weight:normal; color:#94a3b8; margin-left:6px;">(${d.desc})</span>
          </div>
          <div style="font-size: 12px; line-height: 1.9;">
            <div>🔵 <span style="color:#94a3b8">今年本期：</span><strong style="color:#38bdf8; font-size:13px;">${formatNumber(d.current)} 吨</strong></div>
            <div>🟠 <span style="color:#94a3b8">去年同期：</span><strong style="color:#fbbf24; font-size:13px;">${formatNumber(d.peer)} 吨</strong></div>
            <div style="margin-top: 4px; border-top: 1px dashed rgba(255,255,255,0.15); padding-top: 4px;">
              <span style="color:${statusColor}">● 同比变动：</span>
              <strong style="color:${statusColor}; font-size:13px;">${diffSign}${formatNumber(d.diff)} 吨${rateText}</strong>
              <span style="display:inline-block; margin-left:8px; font-size:10px; padding:1px 6px; border-radius:4px; background:${isSaving ? 'rgba(52,211,153,0.2)' : 'rgba(248,113,113,0.2)'}; color:${statusColor}">
                ${statusText}
              </span>
            </div>
          </div>
        `
      },
    },
    // 两个独立的 X 轴标尺（字号加大、加粗加深）
    xAxis: [
      // X 轴 0: 集团汇总与主城区专属万吨级标尺
      {
        gridIndex: 0,
        type: 'value',
        name: '吨',
        nameLocation: 'end',
        nameTextStyle: { color: '#0369a1', fontSize: 12, fontWeight: 700, padding: [0, 0, 0, 3] },
        min: 0,
        max: topTrackEnd,
        minInterval: 1000,
        splitLine: { lineStyle: { type: 'dashed', color: 'rgba(3, 105, 161, 0.15)' } },
        axisLabel: {
          color: '#334155',
          fontSize: 12,
          fontWeight: 600,
          formatter: formatAxisTick,
        },
      },
      // X 轴 1: 外围五单位自适应千吨精细标尺
      {
        gridIndex: 1,
        type: 'value',
        name: '吨',
        nameLocation: 'end',
        nameTextStyle: { color: '#334155', fontSize: 12, fontWeight: 700, padding: [0, 0, 0, 3] },
        min: 0,
        max: subTrackEnd,
        minInterval: 1000,
        splitLine: { lineStyle: { type: 'dashed', color: 'rgba(148, 163, 184, 0.2)' } },
        axisLabel: {
          color: '#334155',
          fontSize: 12,
          fontWeight: 600,
          formatter: formatAxisTick,
        },
      },
    ],
    // 两个独立的 Y 轴（加大字号到 13.5~14px，加粗，深碳墨黑）
    yAxis: [
      // Y 轴 0: 集团汇总 + 主城区（inverse: true 确保集团汇总在最上方）
      {
        gridIndex: 0,
        type: 'category',
        inverse: true,
        data: topCategories,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: '#0f172a',
          fontSize: isNarrow ? 12.5 : 14,
          fontWeight: 800,
          margin: isNarrow ? 8 : 12,
        },
      },
      // Y 轴 1: 外围五单位
      {
        gridIndex: 1,
        type: 'category',
        inverse: true,
        data: subCategories,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#0f172a', fontSize: isNarrow ? 12 : 13.5, fontWeight: 700, margin: isNarrow ? 8 : 12 },
      },
    ],
    series: [
      // ================= 上层系列 (Grid 0: 集团汇总 + 主城区) =================
      {
        name: '上层轨道',
        xAxisIndex: 0,
        yAxisIndex: 0,
        type: 'bar',
        barWidth: 4,
        silent: true,
        itemStyle: { color: '#e0f2fe', borderRadius: 2 },
        data: topTrackData,
        z: 1,
      },
      {
        name: '上层基座',
        xAxisIndex: 0,
        yAxisIndex: 0,
        type: 'bar',
        stack: 'top_rod',
        barWidth: 6,
        silent: true,
        data: topBaseBarData,
        itemStyle: { color: 'transparent' },
        z: 2,
      },
      {
        name: '上层变动区间',
        xAxisIndex: 0,
        yAxisIndex: 0,
        type: 'bar',
        stack: 'top_rod',
        barWidth: 6,
        silent: false,
        data: topRodBarData,
        z: 3,
      },
      {
        name: '上层去年同期',
        xAxisIndex: 0,
        yAxisIndex: 0,
        type: 'scatter',
        symbol: 'rect',
        symbolSize: [4, 22],
        data: topPeerScatterData,
        itemStyle: { color: '#f59e0b', borderRadius: 1.5, shadowColor: 'rgba(245, 158, 11, 0.45)', shadowBlur: 4 },
        z: 4,
      },
      {
        name: '上层今年本期',
        xAxisIndex: 0,
        yAxisIndex: 0,
        type: 'scatter',
        symbol: 'circle',
        symbolSize: 15,
        data: topCurrScatterData,
        itemStyle: { color: '#0284c7', borderColor: '#ffffff', borderWidth: 2, shadowColor: 'rgba(2, 132, 199, 0.55)', shadowBlur: 6 },
        label: {
          show: true,
          position: 'top',
          distance: 5,
          formatter: currValFormatter,
          fontSize: isNarrow ? 11.5 : 13,
          fontWeight: 800,
          color: '#0284c7',
          textBorderColor: '#ffffff',
          textBorderWidth: 3,
        },
        z: 5,
      },
      {
        name: '上层差额标签',
        xAxisIndex: 0,
        yAxisIndex: 0,
        type: 'scatter',
        data: topLabelScatterData,
        symbolSize: 0,
        silent: true,
        label: {
          show: true,
          position: 'right',
          distance: 8,
          formatter: labelFormatter,
          rich: richStyles,
        },
        z: 6,
      },

      // ================= 外围五单位系列 (Grid 1 - 自适应放大标尺) =================
      {
        name: '外围轨道',
        xAxisIndex: 1,
        yAxisIndex: 1,
        type: 'bar',
        barWidth: 4,
        silent: true,
        itemStyle: { color: '#f1f5f9', borderRadius: 2 },
        data: subTrackData,
        z: 1,
      },
      {
        name: '外围基座',
        xAxisIndex: 1,
        yAxisIndex: 1,
        type: 'bar',
        stack: 'sub_rod',
        barWidth: 6,
        silent: true,
        data: subBaseBarData,
        itemStyle: { color: 'transparent' },
        z: 2,
      },
      {
        name: '外围变动区间',
        xAxisIndex: 1,
        yAxisIndex: 1,
        type: 'bar',
        stack: 'sub_rod',
        barWidth: 6,
        silent: false,
        data: subRodBarData,
        z: 3,
      },
      {
        name: '外围去年同期',
        xAxisIndex: 1,
        yAxisIndex: 1,
        type: 'scatter',
        symbol: 'rect',
        symbolSize: [4, 22],
        data: subPeerScatterData,
        itemStyle: { color: '#f59e0b', borderRadius: 1.5, shadowColor: 'rgba(245, 158, 11, 0.45)', shadowBlur: 4 },
        z: 4,
      },
      {
        name: '外围今年本期',
        xAxisIndex: 1,
        yAxisIndex: 1,
        type: 'scatter',
        symbol: 'circle',
        symbolSize: 15,
        data: subCurrScatterData,
        itemStyle: { color: '#0284c7', borderColor: '#ffffff', borderWidth: 2, shadowColor: 'rgba(2, 132, 199, 0.55)', shadowBlur: 6 },
        label: {
          show: true,
          position: 'top',
          distance: 5,
          formatter: currValFormatter,
          fontSize: isNarrow ? 11.5 : 13,
          fontWeight: 800,
          color: '#0284c7',
          textBorderColor: '#ffffff',
          textBorderWidth: 3,
        },
        z: 5,
      },
      {
        name: '外围差额标签',
        xAxisIndex: 1,
        yAxisIndex: 1,
        type: 'scatter',
        data: subLabelScatterData,
        symbolSize: 0,
        silent: true,
        label: {
          show: true,
          position: 'right',
          distance: 8,
          formatter: labelFormatter,
          rich: richStyles,
        },
        z: 6,
      },
    ],
  }
}

let lastRenderedWidth = 0

const renderBothCharts = () => {
  if (!hasData.value) return
  const echarts = window.echarts
  if (!echarts) {
    console.warn('[NetworkWaterDumbbell] window.echarts 未找到，延迟重试')
    setTimeout(renderBothCharts, 200)
    return
  }

  lastRenderedWidth = dayChartRef.value?.clientWidth || 0

  // 1. 渲染左侧：本日（主城区 + 外围五单位双标尺）
  if (dayChartRef.value) {
    if (!dayChartInstance) {
      dayChartInstance = echarts.init(dayChartRef.value)
    }
    const dayOpt = buildDumbbellOption(dayDimData.value, false)
    dayChartInstance.setOption(dayOpt, true)
  }

  // 2. 渲染右侧：供暖期累计（主城区 + 外围五单位双标尺）
  if (seasonChartRef.value) {
    if (!seasonChartInstance) {
      seasonChartInstance = echarts.init(seasonChartRef.value)
    }
    const seasonOpt = buildDumbbellOption(seasonDimData.value, true)
    seasonChartInstance.setOption(seasonOpt, true)
  }
}

const handleResize = () => {
  if (!hasData.value) return
  const currentWidth = dayChartRef.value?.clientWidth || 0
  const wasNarrow = lastRenderedWidth > 0 && lastRenderedWidth < 500
  const isNarrowNow = currentWidth > 0 && currentWidth < 500

  // 跨越窄屏/宽屏阈值，或宽度变动超过 50px（如切入/退出 1800px PDF 导出状态），重算 Option 并重绘
  if (Math.abs(currentWidth - lastRenderedWidth) > 50 || wasNarrow !== isNarrowNow) {
    renderBothCharts()
  } else {
    dayChartInstance?.resize()
    seasonChartInstance?.resize()
  }
}

watch(
  () => [props.projectKey, props.bizDate],
  () => {
    loadData()
  },
  { immediate: true, flush: 'sync' },
)

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    handleResize()
  })

  if (dayChartRef.value) resizeObserver.observe(dayChartRef.value)
  if (seasonChartRef.value) resizeObserver.observe(seasonChartRef.value)
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  abortController?.abort()
  abortController = null
  resizeObserver?.disconnect()
  window.removeEventListener('resize', handleResize)
  if (dayChartInstance) {
    dayChartInstance.dispose()
    dayChartInstance = null
  }
  if (seasonChartInstance) {
    seasonChartInstance.dispose()
    seasonChartInstance = null
  }
})

defineExpose({
  renderBothCharts,
  resize: handleResize,
})
</script>

<style scoped>
.water-dumbbell-card {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

/* 顶部头部排版 */
.water-dumbbell-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 860px) {
  .water-dumbbell-header {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }
}

.water-dumbbell-header__left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.water-dumbbell-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.water-dumbbell-header__right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

/* 图例标识 */
.water-legend-chips {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}

.legend-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}

.chip-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.chip-dot--curr {
  background: #0284c7;
  border: 1px solid #fff;
  box-shadow: 0 0 4px rgba(2, 132, 199, 0.5);
}

.chip-tick {
  width: 4px;
  height: 14px;
  border-radius: 1px;
}

.chip-tick--peer {
  background: #f59e0b;
  box-shadow: 0 0 4px rgba(245, 158, 11, 0.5);
}

.chip-line {
  width: 14px;
  height: 5px;
  border-radius: 2px;
}

.chip-line--saving {
  background: #10b981;
}

.chip-line--waste {
  background: #f43f5e;
}

.water-unit-hint {
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  margin-left: 4px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 顶部全口径指标概览栏（置于最上方） */
.water-global-summary-bar {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 22px;
}

@media (min-width: 900px) {
  .water-global-summary-bar {
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 24px;
  }
}

.water-global-metric {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.water-global-metric__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  color: #1e293b;
  font-weight: 700;
}

.water-global-metric__name {
  color: #0f172a;
}

.water-global-metric__date {
  font-size: 12px;
  color: #64748b;
  font-weight: normal;
}

.water-global-metric__body {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 14px;
}

.water-global-metric__val {
  font-size: 24px;
  font-weight: 800;
  color: #0369a1;
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}

.water-global-metric:last-child .water-global-metric__val {
  color: #ea580c;
}

.water-global-metric__unit {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.water-global-metric__compare {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
}

.water-global-metric__peer {
  color: #475569;
}

.water-global-metric__sep {
  color: #cbd5e1;
}

.water-global-metric__compare.is-good .water-global-metric__diff {
  color: #047857;
  font-weight: 700;
}

.water-global-metric__compare.is-warn .water-global-metric__diff {
  color: #b91c1c;
  font-weight: 700;
}

.water-global-metric__divider {
  display: none;
}

@media (min-width: 900px) {
  .water-global-metric__divider {
    display: block;
    width: 1px;
    height: 44px;
    background: #cbd5e1;
  }
}

/* 双栏 Grid 布局：左侧本日，右侧供暖期 */
.water-columns-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  width: 100%;
}

@media (min-width: 1024px) {
  .water-columns-grid {
    grid-template-columns: 1fr auto 1fr;
    gap: 16px;
    align-items: stretch;
  }
}

.water-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.water-columns-divider {
  display: none;
}

@media (min-width: 1024px) {
  .water-columns-divider {
    display: block;
    width: 1px;
    background: #e2e8f0;
    margin: 4px 0;
  }
}

.water-column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px;
}

.water-column-header__left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.water-dim-badge {
  font-size: 14.5px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 6px;
}

.water-dim-badge--day {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #bae6fd;
}

.water-dim-badge--season {
  background: #ffedd5;
  color: #c2410c;
  border: 1px solid #fed7aa;
}

.water-column-subtitle {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

/* 状态容器 */
.water-state-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px;
  color: #64748b;
  font-size: 14px;
}

.water-state-box--error {
  color: #dc2626;
}

.water-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #cbd5e1;
  border-top-color: #0284c7;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.water-retry-btn {
  border: 1px solid #fecaca;
  background: #fff;
  color: #dc2626;
  padding: 2px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

/* ECharts 挂载区域与标尺虚线分割包装 */
.water-chart-wrapper {
  position: relative;
  width: 100%;
}

.water-chart-container {
  width: 100%;
}

.water-scale-divider {
  position: absolute;
  top: 132px;
  left: 12px;
  right: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 2;
}

.water-scale-divider__line {
  flex: 1;
  border-top: 1.5px dashed #cbd5e1;
}

.water-scale-divider__text {
  padding: 0 10px;
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  background: #ffffff;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

/* ============================================================
   📱 窄屏手机响应式适配 (max-width: 767px)
   ============================================================ */
@media (max-width: 767px) {
  .water-dumbbell-card {
    padding: 14px 12px;
    border-radius: 12px;
    gap: 12px;
  }

  .water-dumbbell-title {
    font-size: 16px;
  }

  .water-legend-chips {
    gap: 8px 10px;
  }

  .legend-chip {
    font-size: 11px;
    gap: 4px;
  }

  .water-global-summary-bar {
    flex-direction: column;
    gap: 12px;
    padding: 12px 14px;
  }

  .water-global-metric__val {
    font-size: 20px;
  }

  .water-global-metric__compare {
    font-size: 12px;
    flex-wrap: wrap;
    gap: 4px 8px;
  }

  .water-global-metric__divider {
    display: none !important;
  }
}

/* ============================================================
   📄 PDF 导出标准版式锁定样式 (消除手机端小视口双栏折叠与画布错位)
   ============================================================ */
:global(.dashboard-page--export-standard) .water-dumbbell-header {
  flex-direction: row !important;
  align-items: center !important;
  justify-content: space-between !important;
}

:global(.dashboard-page--export-standard) .water-global-summary-bar {
  display: grid !important;
  grid-template-columns: 1fr auto 1fr !important;
  align-items: center !important;
  gap: 24px !important;
  padding: 16px 22px !important;
}

:global(.dashboard-page--export-standard) .water-global-metric__val {
  font-size: 24px !important;
}

:global(.dashboard-page--export-standard) .water-global-metric__compare {
  font-size: 13.5px !important;
}

:global(.dashboard-page--export-standard) .water-global-metric__divider {
  display: block !important;
  width: 1px !important;
  height: 44px !important;
  background: #cbd5e1 !important;
}

:global(.dashboard-page--export-standard) .water-columns-grid {
  display: grid !important;
  grid-template-columns: 1fr auto 1fr !important;
  gap: 16px !important;
  align-items: stretch !important;
}

:global(.dashboard-page--export-standard) .water-columns-divider {
  display: block !important;
  width: 1px !important;
  background: #e2e8f0 !important;
  margin: 4px 0 !important;
}

:global(.dashboard-page--export-standard) .water-column {
  min-width: 0 !important;
}

:global(.dashboard-page--export-standard) .water-dumbbell-card {
  padding: 20px 24px !important;
  border-radius: 16px !important;
  gap: 16px !important;
}

:global(.dashboard-page--export-standard) .water-dumbbell-title {
  font-size: 20px !important;
}
</style>
