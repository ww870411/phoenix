<template>
  <div class="smart-heating-view">
    <AppHeader />
    <main class="smart-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <!-- 顶部 Banner 卡片 -->
      <section class="card elevated banner-card">
        <div class="banner-content">
          <div class="banner-title-row">
            <div class="banner-icon">🔥</div>
            <div>
              <div class="title-with-badge">
                <h2 class="banner-title">智慧供热实时工况监控</h2>
                <span class="badge-role">生产实时大屏</span>
              </div>
              <p class="banner-subtitle">
                热网首站环路 · 电厂热源机组 · 换热站一次网生产运行全景实时监控
                <span v-if="!isRelayOnline" class="offline-note">（数据链路未连接 · 暂无实时数据）</span>
              </p>
            </div>
          </div>

          <div class="banner-actions">
            <div class="status-indicator" :class="{ online: isRelayOnline, offline: !isRelayOnline }">
              <span class="dot"></span>
              <span class="status-text">{{ isRelayOnline ? '实时数据传输中' : '数据链路未连接' }}</span>
              <span class="time-sub">({{ formattedTimeAgo }})</span>
            </div>

            <div class="action-buttons">
              <button
                class="btn secondary btn-sm btn-download"
                type="button"
                :disabled="downloading"
                title="下载专用的数据同步客户端脚本"
                @click="handleDownloadScript"
              >
                {{ downloading ? '下载中…' : '📥 下载同步客户端' }}
              </button>

              <label class="auto-refresh-toggle">
                <input v-model="autoRefresh" type="checkbox" />
                <span>自动刷新 (30s)</span>
              </label>

              <button class="btn primary btn-sm" :disabled="loading" @click="fetchData">
                {{ loading ? '刷新中…' : '立即刷新 ⟳' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 核心指标摘要条 -->
        <div class="metric-strip">
          <div class="metric-item">
            <span class="metric-label">主管网瞬时供水流量</span>
            <div class="metric-val-row">
              <span class="metric-value">{{ isRelayOnline && totalMainSupplyFlow ? formatNum(totalMainSupplyFlow, 1) : '—' }}</span>
              <span class="metric-unit">m³/h</span>
            </div>
            <span class="metric-hint">东环 + 南环供水流量</span>
          </div>

          <div class="metric-item">
            <span class="metric-label">换热站平均供水温度</span>
            <div class="metric-val-row">
              <span class="metric-value text-warm">{{ isRelayOnline && avgStationSupplyTemp ? formatNum(avgStationSupplyTemp, 1) : '—' }}</span>
              <span class="metric-unit">℃</span>
            </div>
            <span class="metric-hint">一次网供水平均</span>
          </div>

          <div class="metric-item">
            <span class="metric-label">换热站平均回水温度</span>
            <div class="metric-val-row">
              <span class="metric-value text-cool">{{ isRelayOnline && avgStationReturnTemp ? formatNum(avgStationReturnTemp, 1) : '—' }}</span>
              <span class="metric-unit">℃</span>
            </div>
            <span class="metric-hint">一次网回水平均</span>
          </div>

          <div class="metric-item">
            <span class="metric-label">换热站平均供回温差</span>
            <div class="metric-val-row">
              <span class="metric-value text-accent">{{ isRelayOnline && avgStationTempDiff ? formatNum(avgStationTempDiff, 1) : '—' }}</span>
              <span class="metric-unit">℃</span>
            </div>
            <span class="metric-hint">平均供回温降</span>
          </div>

          <div class="metric-item">
            <span class="metric-label">在线换热站数</span>
            <div class="metric-val-row">
              <span class="metric-value text-success">{{ isRelayOnline ? activeStationCount : 0 }}</span>
              <span class="metric-unit">/ {{ isRelayOnline ? ywDataList.length : 0 }} 座</span>
            </div>
            <span class="metric-hint">正常接入运行</span>
          </div>
        </div>
      </section>

      <!-- 未连接提示横幅 -->
      <section v-if="!isRelayOnline" class="card elevated offline-callout">
        <div class="offline-icon">🔌</div>
        <div class="offline-body">
          <div class="offline-title">数据链路未连接 · 暂无实时数据</div>
          <div class="offline-desc">
            系统严格遵循实时数据规范，在未接收到客户端推流前不呈现任何数据。请在办公电脑上运行数据同步客户端（smart_heating_sync.py）以开启实时推流。
          </div>
        </div>
        <button
          class="btn primary btn-sm btn-callout-dl"
          type="button"
          :disabled="downloading"
          @click="handleDownloadScript"
        >
          {{ downloading ? '下载中…' : '📥 下载客户端脚本' }}
        </button>
      </section>

      <!-- 选项卡导航与检索工具栏 -->
      <div class="nav-and-filter-card card elevated">
        <div class="tabs-container">
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'yw' }"
            @click="currentTab = 'yw'"
          >
            🏢 换热站一次网工况 ({{ ywDataList.length }})
          </button>
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'sz' }"
            @click="currentTab = 'sz'"
          >
            🔄 主管网与首站测点 ({{ szDataList.length }})
          </button>
          <button
            class="tab-btn"
            :class="{ active: currentTab === 'dc' }"
            @click="currentTab = 'dc'"
          >
            ⚡ 电厂与热源机组 ({{ dcDataList.length }})
          </button>
        </div>

        <div v-if="currentTab === 'yw'" class="yw-filter-row">
          <input
            v-model="searchKeyword"
            type="text"
            class="input-search"
            placeholder="搜索换热站名称 (如: 金广, 海港, 东港)..."
          />
          <div class="sort-selector">
            <span>排序:</span>
            <select v-model="sortBy" class="select-sort">
              <option value="default">默认顺序</option>
              <option value="f3_desc">供水温度 (从高到低)</option>
              <option value="f3_asc">供水温度 (从低到高)</option>
              <option value="f2_desc">瞬时流量 (从大到小)</option>
              <option value="diff_desc">供回温差 (从大到小)</option>
            </select>
          </div>
        </div>
      </div>

      <!-- 选项卡 1: 换热站一次网实时监测 -->
      <section v-if="currentTab === 'yw'" class="card elevated data-section">
        <header class="section-header">
          <div class="header-left">
            <h3>换热站一次网实时监测矩阵</h3>
            <span class="badge-count">共 {{ filteredYwList.length }} 座站</span>
          </div>
          <span class="header-tip">采集频率：30秒/次 ｜ 覆盖主城区核心直供换热站</span>
        </header>

        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 50px;">#</th>
                <th style="width: 140px;">换热站名称</th>
                <th>供水温度</th>
                <th>回水温度</th>
                <th>供回温差 (ΔT)</th>
                <th>供水压力</th>
                <th>回水压力</th>
                <th>供回压差 (ΔP)</th>
                <th>瞬时流量</th>
                <th>瞬时热量</th>
                <th>采集时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(station, idx) in filteredYwList" :key="station.name || idx">
                <td class="col-center text-muted">{{ idx + 1 }}</td>
                <td class="col-station font-bold">{{ station.name || '—' }}</td>
                <td class="col-num text-warm font-mono font-bold">
                  {{ formatVal(station.f3, '℃') }}
                </td>
                <td class="col-num text-cool font-mono">
                  {{ formatVal(station.f5, '℃') }}
                </td>
                <td class="col-num font-mono">
                  <span
                    class="diff-badge"
                    :class="getTempDiffBadgeClass(station.f3, station.f5)"
                  >
                    {{ calcDiff(station.f3, station.f5, '℃') }}
                  </span>
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(station.f1, 'MPa', 3) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(station.f4, 'MPa', 3) }}
                </td>
                <td class="col-num font-mono">
                  {{ calcDiff(station.f1, station.f4, 'MPa', 3) }}
                </td>
                <td class="col-num font-mono font-bold">
                  {{ formatVal(station.f2, 'm³/h', 1) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(station.f222, 'GJ/h', 1) }}
                </td>
                <td class="col-center font-mono text-muted text-sm">
                  {{ station.update_time || '—' }}
                </td>
              </tr>
              <tr v-if="filteredYwList.length === 0">
                <td colspan="11" class="empty-cell">
                  {{ isRelayOnline ? '未查询到符合条件的换热站数据' : '数据链路未连接，暂无实时数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 选项卡 2: 主管网与首站工况 -->
      <section v-if="currentTab === 'sz'" class="card elevated data-section">
        <header class="section-header">
          <div class="header-left">
            <h3>主管网各环路与首站实时测点</h3>
            <span class="badge-count">{{ isRelayOnline ? szDataList.length : 0 }} 组测点</span>
          </div>
          <span class="header-tip">含东环、南环、北网供回补水、板换一次二次及热泵运行工况</span>
        </header>

        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 50px;">#</th>
                <th>测点 / 回路名称</th>
                <th>瞬时温度</th>
                <th>瞬时压力</th>
                <th>瞬时流量</th>
                <th>瞬时热量</th>
                <th>当前负荷</th>
                <th>频率</th>
                <th>采集时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in szDataList" :key="item.name || idx">
                <td class="col-center text-muted">{{ idx + 1 }}</td>
                <td class="col-station font-bold">
                  <span class="circuit-tag" :class="getCircuitTagClass(item.name)">{{ getCircuitType(item.name) }}</span>
                  {{ item.name }}
                </td>
                <td class="col-num font-mono font-bold" :class="item.WENDU > 35 ? 'text-warm' : 'text-cool'">
                  {{ formatVal(item.WENDU, '℃', 1) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.YALI, 'MPa', 3) }}
                </td>
                <td class="col-num font-mono font-bold">
                  {{ formatVal(item.LIULIANG, 'm³/h', 1) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.RELIANG, 'GJ', 1) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.FUHE, 'MW', 1) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.PINLV, 'Hz', 1) }}
                </td>
                <td class="col-center font-mono text-muted text-sm">
                  {{ item.SHIJIAN || '—' }}
                </td>
              </tr>
              <tr v-if="szDataList.length === 0">
                <td colspan="9" class="empty-cell">
                  {{ isRelayOnline ? '暂无首站与管网测点数据' : '数据链路未连接，暂无实时数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 选项卡 3: 电厂与热源机组运行参数 -->
      <section v-if="currentTab === 'dc'" class="card elevated data-section">
        <header class="section-header">
          <div class="header-left">
            <h3>热电厂机组与热源供网监测</h3>
            <span class="badge-count">{{ isRelayOnline ? dcDataList.length : 0 }} 组测点</span>
          </div>
          <span class="header-tip">覆盖北海 #1~#3 汽轮机进抽汽、#1~#4 锅炉主汽、燃气炉群及管网进气</span>
        </header>

        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 50px;">#</th>
                <th>机组 / 测点名称</th>
                <th>运行温度</th>
                <th>主汽压力</th>
                <th>瞬时流量</th>
                <th>瞬时热量</th>
                <th>采集时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in dcDataList" :key="item.name || idx">
                <td class="col-center text-muted">{{ idx + 1 }}</td>
                <td class="col-station font-bold">
                  <span class="plant-tag" :class="getPlantTagClass(item.name)">{{ getPlantType(item.name) }}</span>
                  {{ item.name }}
                </td>
                <td class="col-num font-mono font-bold" :class="item.WENDU > 50 ? 'text-warm' : ''">
                  {{ formatVal(item.WENDU, '℃', 1) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.YALI, 'MPa', 3) }}
                </td>
                <td class="col-num font-mono font-bold">
                  {{ formatVal(item.LIULIANG, 't/h', 1) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.RELIANG, 'GJ', 1) }}
                </td>
                <td class="col-center font-mono text-muted text-sm">
                  {{ item.SHIJIAN || '—' }}
                </td>
              </tr>
              <tr v-if="dcDataList.length === 0">
                <td colspan="7" class="empty-cell">
                  {{ isRelayOnline ? '暂无电厂与热源数据' : '数据链路未连接，暂无实时数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import {
  getSmartHeatingLatest,
  getSmartHeatingStatus,
  downloadSmartHeatingClientScript,
} from '../services/api'

const route = useRoute()
const projectKey = String(route.params.projectKey || 'daily_report_25_26')

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '生产日报', to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: '智慧供热实时工况', to: null },
])

const currentTab = ref('yw')
const loading = ref(false)
const downloading = ref(false)
const autoRefresh = ref(true)
const searchKeyword = ref('')
const sortBy = ref('default')

const latestPayload = ref({
  timestamp: '',
  received_at: '',
  source: '',
  sz_data: [],
  dc_data: [],
  yw_data: [],
})

const relayStatus = ref({
  is_online: false,
  seconds_ago: null,
  last_received_at: null,
})

let timer = null

// 严格依据后端真实心跳状态判定链路是否在线，杜绝根据快照时间伪造“在线”
const isRelayOnline = computed(() => Boolean(relayStatus.value?.is_online))

const szDataList = computed(() => (isRelayOnline.value ? latestPayload.value?.sz_data || [] : []))
const dcDataList = computed(() => (isRelayOnline.value ? latestPayload.value?.dc_data || [] : []))
const ywDataList = computed(() => (isRelayOnline.value ? latestPayload.value?.yw_data || [] : []))

const lastUpdateTime = computed(() =>
  isRelayOnline.value ? latestPayload.value?.received_at || latestPayload.value?.timestamp || '' : ''
)

const formattedTimeAgo = computed(() => {
  if (isRelayOnline.value && relayStatus.value?.seconds_ago !== null) {
    const sec = relayStatus.value.seconds_ago
    return sec <= 5 ? '刚刚推送' : `${sec} 秒前推送`
  }
  return '等待客户端启动推流'
})

// 过滤与排序后的换热站数据
const filteredYwList = computed(() => {
  let list = [...ywDataList.value]
  const kw = searchKeyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter((item) => String(item.name || '').toLowerCase().includes(kw))
  }

  if (sortBy.value === 'f3_desc') {
    list.sort((a, b) => (Number(b.f3) || 0) - (Number(a.f3) || 0))
  } else if (sortBy.value === 'f3_asc') {
    list.sort((a, b) => (Number(a.f3) || 0) - (Number(b.f3) || 0))
  } else if (sortBy.value === 'f2_desc') {
    list.sort((a, b) => (Number(b.f2) || 0) - (Number(a.f2) || 0))
  } else if (sortBy.value === 'diff_desc') {
    list.sort((a, b) => {
      const diffB = (Number(b.f3) || 0) - (Number(b.f5) || 0)
      const diffA = (Number(a.f3) || 0) - (Number(a.f5) || 0)
      return diffB - diffA
    })
  }

  return list
})

// 统计指标计算
const totalMainSupplyFlow = computed(() => {
  let sum = 0
  szDataList.value.forEach((item) => {
    const name = String(item.name || '')
    if (name.includes('供水') && (name.includes('东环') || name.includes('南环'))) {
      const v = Number(item.LIULIANG)
      if (Number.isFinite(v)) sum += v
    }
  })
  return sum
})

const avgStationSupplyTemp = computed(() => {
  const valid = ywDataList.value.filter((i) => Number.isFinite(Number(i.f3)) && Number(i.f3) > 10)
  if (!valid.length) return 0
  const sum = valid.reduce((acc, cur) => acc + Number(cur.f3), 0)
  return sum / valid.length
})

const avgStationReturnTemp = computed(() => {
  const valid = ywDataList.value.filter((i) => Number.isFinite(Number(i.f5)) && Number(i.f5) > 10)
  if (!valid.length) return 0
  const sum = valid.reduce((acc, cur) => acc + Number(cur.f5), 0)
  return sum / valid.length
})

const avgStationTempDiff = computed(() => {
  const diff = avgStationSupplyTemp.value - avgStationReturnTemp.value
  return diff > 0 ? diff : 0
})

const activeStationCount = computed(() => {
  return ywDataList.value.filter((i) => i.f3 !== null && i.f3 !== undefined && i.f3 !== '').length
})

function formatNum(val, digits = 1) {
  if (val === null || val === undefined || !Number.isFinite(Number(val))) return '—'
  return Number(val).toFixed(digits)
}

function formatVal(val, unit = '', digits = 1) {
  if (val === null || val === undefined || val === '' || !Number.isFinite(Number(val))) return '—'
  const num = Number(val).toFixed(digits)
  return unit ? `${num} ${unit}` : num
}

function calcDiff(val1, val2, unit = '', digits = 1) {
  const n1 = Number(val1)
  const n2 = Number(val2)
  if (!Number.isFinite(n1) || !Number.isFinite(n2)) return '—'
  const diff = (n1 - n2).toFixed(digits)
  return unit ? `${diff} ${unit}` : diff
}

function getTempDiffBadgeClass(t1, t2) {
  const n1 = Number(t1)
  const n2 = Number(t2)
  if (!Number.isFinite(n1) || !Number.isFinite(n2)) return ''
  const diff = n1 - n2
  if (diff >= 28) return 'badge-success'
  if (diff >= 20) return 'badge-normal'
  return 'badge-warning'
}

function getCircuitType(name = '') {
  if (name.includes('东环')) return '东环'
  if (name.includes('南环')) return '南环'
  if (name.includes('北网')) return '北网'
  if (name.includes('板换')) return '板换'
  if (name.includes('热泵')) return '热泵'
  return '管网'
}

function getCircuitTagClass(name = '') {
  if (name.includes('东环')) return 'tag-dong'
  if (name.includes('南环')) return 'tag-nan'
  if (name.includes('北网')) return 'tag-bei'
  if (name.includes('板换')) return 'tag-ban'
  return 'tag-default'
}

function getPlantType(name = '') {
  if (name.includes('燃气')) return '燃气炉'
  if (name.includes('机')) return '汽轮机'
  if (name.includes('炉')) return '锅炉'
  return '电厂'
}

function getPlantTagClass(name = '') {
  if (name.includes('燃气')) return 'tag-gas'
  if (name.includes('机')) return 'tag-turbine'
  if (name.includes('炉')) return 'tag-boiler'
  return 'tag-default'
}

async function handleDownloadScript() {
  downloading.value = true
  try {
    await downloadSmartHeatingClientScript(projectKey)
  } catch (err) {
    alert(err?.message || '下载同步客户端失败，请联系管理员确认权限')
  } finally {
    downloading.value = false
  }
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getSmartHeatingLatest(projectKey)
    if (res?.data) {
      latestPayload.value = res.data
    }
    const statusRes = await getSmartHeatingStatus(projectKey)
    if (statusRes) {
      relayStatus.value = statusRes
    }
  } catch (err) {
    console.error('获取智慧供热实时数据失败:', err)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchData()
  timer = setInterval(() => {
    if (autoRefresh.value) {
      fetchData()
    }
  }, 30000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.smart-heating-view {
  min-height: 100vh;
  background-color: #f1f5f9;
  display: flex;
  flex-direction: column;
}

.smart-main {
  flex: 1;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  padding: 16px 24px 48px;
  box-sizing: border-box;
}

/* 顶部 Banner */
.banner-card {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #f8fafc;
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
  border: 1px solid #334155;
}

.banner-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}

.banner-title-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.banner-icon {
  font-size: 32px;
  background: rgba(255, 255, 255, 0.1);
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 10px;
}

.banner-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.badge-role {
  background: #0284c7;
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 600;
}

.banner-subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #94a3b8;
}

.banner-actions {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid #475569;
  font-size: 13px;
  transition: all 0.3s ease;
}

.status-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  display: inline-block;
}

.status-indicator.online {
  border-color: rgba(34, 197, 94, 0.4);
  background: rgba(34, 197, 94, 0.12);
}

.status-indicator.online .dot {
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
  animation: pulse-dot 2s infinite ease-in-out;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.4;
    transform: scale(0.85);
  }
}

.status-indicator.online .status-text {
  color: #4ade80;
  font-weight: 600;
}

.status-indicator.offline {
  border-color: rgba(148, 163, 184, 0.3);
  background: rgba(15, 23, 42, 0.45);
}

.status-indicator.offline .dot {
  background: #64748b;
  box-shadow: none;
}

.status-indicator.offline .status-text {
  color: #94a3b8;
  font-weight: 500;
}

.offline-note {
  color: #fbbf24;
  font-size: 12px;
  margin-left: 6px;
  font-weight: 500;
}

/* 离线警示横幅 */
.offline-callout {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-left: 4px solid #f59e0b;
  border-radius: 8px;
  padding: 14px 20px;
  margin-bottom: 20px;
}

.offline-callout .offline-icon {
  font-size: 26px;
  line-height: 1;
}

.offline-callout .offline-body {
  flex: 1;
}

.offline-callout .offline-title {
  font-size: 15px;
  font-weight: 600;
  color: #92400e;
  margin-bottom: 4px;
}

.offline-callout .offline-desc {
  font-size: 13px;
  color: #b45309;
  line-height: 1.5;
}

.offline-callout .btn-callout-dl {
  background: #d97706;
  border-color: #d97706;
  color: #fff;
  white-space: nowrap;
}

.offline-callout .btn-callout-dl:hover {
  background: #b45309;
}

.time-sub {
  color: #94a3b8;
  font-size: 12px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-download {
  background: rgba(255, 255, 255, 0.12);
  color: #f1f5f9;
  border: 1px solid rgba(255, 255, 255, 0.25);
  transition: all 0.2s ease;
}

.btn-download:hover {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.auto-refresh-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #cbd5e1;
  cursor: pointer;
  user-select: none;
}

.auto-refresh-toggle input {
  cursor: pointer;
}

/* 核心指标条 */
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 16px;
}

.metric-item {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.metric-label {
  font-size: 12px;
  color: #94a3b8;
  display: block;
  margin-bottom: 6px;
}

.metric-val-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.metric-unit {
  font-size: 12px;
  color: #94a3b8;
}

.metric-hint {
  font-size: 11px;
  color: #64748b;
  display: block;
  margin-top: 4px;
}

/* 选项卡栏 */
.nav-and-filter-card {
  padding: 8px 16px;
  border-radius: 10px;
  background: #ffffff;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.tabs-container {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tab-btn {
  border: none;
  background: #f1f5f9;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.tab-btn.active {
  background: #0284c7;
  color: #ffffff;
}

.yw-filter-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.input-search {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-size: 13px;
  width: 220px;
  outline: none;
}

.input-search:focus {
  border-color: #0284c7;
}

.sort-selector {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.select-sort {
  padding: 5px 8px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-size: 12px;
  background: #fff;
  outline: none;
}

/* 数据部分卡片 */
.data-section {
  background: #ffffff;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f1f5f9;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.badge-count {
  background: #e0f2fe;
  color: #0369a1;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 600;
}

.header-tip {
  font-size: 12px;
  color: #64748b;
}

/* 表格样式 */
.table-responsive {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}

.data-table thead th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  padding: 10px 12px;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.data-table tbody td {
  padding: 10px 12px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.data-table tbody tr:hover {
  background: #f8fafc;
}

.col-center {
  text-align: center;
}

.col-num {
  text-align: right;
}

.col-station {
  color: #0f172a;
}

.font-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.font-bold {
  font-weight: 600;
}

.text-warm {
  color: #e11d48;
}

.text-cool {
  color: #0284c7;
}

.text-accent {
  color: #f59e0b;
}

.text-success {
  color: #16a34a;
}

.text-danger {
  color: #dc2626;
}

.text-muted {
  color: #94a3b8;
}

.text-sm {
  font-size: 11px;
}

.diff-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.badge-success {
  background: #dcfce7;
  color: #15803d;
}

.badge-normal {
  background: #fef3c7;
  color: #b45309;
}

.badge-warning {
  background: #fee2e2;
  color: #b91c1c;
}

.circuit-tag, .plant-tag {
  display: inline-block;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 6px;
  font-weight: 600;
}

.tag-dong { background: #e0e7ff; color: #4338ca; }
.tag-nan { background: #fae8ff; color: #86198f; }
.tag-bei { background: #dbeafe; color: #1e40af; }
.tag-ban { background: #ffedd5; color: #c2410c; }
.tag-gas { background: #fef08a; color: #854d0e; }
.tag-turbine { background: #e0f2fe; color: #0369a1; }
.tag-boiler { background: #fee2e2; color: #991b1b; }
.tag-default { background: #f1f5f9; color: #475569; }

.empty-cell {
  text-align: center;
  padding: 36px 0;
  color: #94a3b8;
  font-size: 14px;
}
</style>
