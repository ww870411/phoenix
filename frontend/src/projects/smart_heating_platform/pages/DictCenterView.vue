<template>
  <div class="shp-page-root">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <PlatformSubNav current="dict_center" />

      <header class="card elevated topbar">
        <div>
          <h2>8类主体标准台账中心</h2>
          <p class="subtitle">
            基于《成果_智慧供热平台基础台账.xlsx》构建，支持在网供热总面积（当前 {{ ((overview.total_covered_area_m2 || 0) / 10000).toFixed(2) }} 万㎡）与缺失标签在线补录。
          </p>
        </div>
        <button class="btn secondary btn-sm" type="button" @click="loadAll">🔄 刷新台账</button>
      </header>

      <div v-if="notice.text" :class="['notice-banner', notice.type]">{{ notice.text }}</div>

      <!-- 8类主体切换卡片 -->
      <section class="entity-grid">
        <button
          v-for="e in entityTabs"
          :key="e.key"
          type="button"
          :class="['card elevated entity-btn', { active: activeEntity === e.key }]"
          @click="selectEntity(e.key)"
        >
          <span class="ent-label">{{ e.label }}</span>
          <strong class="ent-count">{{ overview[e.countKey] ?? '-' }}</strong>
          <span v-if="e.warnKey && overview[e.warnKey] > 0" class="ent-warn">
            {{ e.warnText(overview[e.warnKey]) }}
          </span>
        </button>
      </section>

      <!-- 主列表卡片 -->
      <section class="card elevated list-card">
        <div class="filter-bar">
          <input v-model="keyword" type="search" class="ctrl-input" placeholder="输入名称/编号过滤…" @keyup.enter="loadItems" />
          <label v-if="canFilterMissing" class="check-inline">
            <input v-model="onlyMissing" type="checkbox" @change="loadItems" />
            <span>{{ missingFilterLabel }}</span>
          </label>
          <button class="btn secondary btn-sm" type="button" @click="loadItems">🔍 查询</button>
        </div>

        <div class="table-wrap">
          <!-- 换热站 (支持在线补录面积) -->
          <table v-if="activeEntity === 'stations'" class="data-table">
            <thead>
              <tr>
                <th>站名</th>
                <th>中心</th>
                <th>支线网</th>
                <th>主干热网 (rdfz)</th>
                <th>分表名 (rd_code)</th>
                <th>供热面积 (㎡)</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in items" :key="r.station_id">
                <td class="font-bold">{{ r.name }}</td>
                <td>{{ r.center_name }}</td>
                <td>{{ r.branch_name }}</td>
                <td>{{ r.rdfz }}</td>
                <td class="mono">{{ r.rd_code }}</td>
                <td :class="{ 'text-warn font-bold': r.covered_area == null }">
                  {{ r.covered_area != null ? r.covered_area.toLocaleString() : '待补录' }}
                </td>
                <td>
                  <button class="btn secondary btn-xs" type="button" @click="openEditStation(r)">✏️ 补录/修改面积</button>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 商业用户 (支持在线补录五维标签) -->
          <table v-else-if="activeEntity === 'merchants'" class="data-table">
            <thead>
              <tr>
                <th>商户名</th>
                <th>支线网</th>
                <th>分表名</th>
                <th>rdfz</th>
                <th>rdry</th>
                <th>rdss</th>
                <th>rdjg</th>
                <th>rdgz</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in items" :key="r.merchant_id">
                <td class="font-bold">{{ r.name }}</td>
                <td>{{ r.branch_name }}</td>
                <td class="mono">{{ r.table_name }}</td>
                <td>{{ r.rdfz || '缺失' }}</td>
                <td>{{ r.rdry || '缺失' }}</td>
                <td>{{ r.rdss || '缺失' }}</td>
                <td>{{ r.rdjg || '缺失' }}</td>
                <td>{{ r.rdgz || '缺失' }}</td>
                <td>
                  <button class="btn secondary btn-xs" type="button" @click="openEditMerchant(r)">✏️ 补录标签</button>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- 9大主干热网 (按 rdfz 汇总) -->
          <table v-else-if="activeEntity === 'main_networks'" class="data-table">
            <thead>
              <tr>
                <th>主干热网名称 (rdfz)</th>
                <th>下辖换热站数</th>
                <th>在网供热面积 (㎡)</th>
                <th>待补面积站数</th>
                <th>关联商业户数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="items.length === 0">
                <td colspan="5" class="empty-td">暂无主干热网记录</td>
              </tr>
              <tr v-for="r in items" :key="r.name">
                <td class="font-bold">{{ r.name }}</td>
                <td>{{ r.station_count }}</td>
                <td>{{ Number(r.covered_area_m2 || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
                <td :class="{ 'text-warn font-bold': r.missing_area_stations > 0 }">{{ r.missing_area_stations }}</td>
                <td>{{ r.merchant_count }}</td>
              </tr>
            </tbody>
          </table>

          <!-- 通用只读展示表格 -->
          <table v-else class="data-table">
            <thead>
              <tr>
                <th v-for="col in genericColumns" :key="col">{{ col }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="items.length === 0">
                <td :colspan="Math.max(genericColumns.length, 1)" class="empty-td">暂无记录</td>
              </tr>
              <tr v-for="(r, idx) in items" :key="idx">
                <td v-for="col in genericColumns" :key="col">{{ r[col] ?? '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 补录弹窗 -->
      <div v-if="editModal.open" class="modal-backdrop" @click.self="editModal.open = false">
        <div class="modal-box card elevated">
          <h3>{{ editModal.title }}</h3>
          <div v-if="editModal.kind === 'station'" class="modal-fields">
            <label>
              <span>在网供热面积（㎡）</span>
              <input v-model.number="editModal.covered_area" type="number" step="0.01" min="0" class="ctrl-input" />
            </label>
            <label>
              <span>主干热网（rdfz）</span>
              <input v-model="editModal.rdfz" type="text" class="ctrl-input" />
            </label>
          </div>
          <div v-else-if="editModal.kind === 'merchant'" class="modal-fields">
            <label><span>rdfz（主干热网）</span><input v-model="editModal.rdfz" type="text" class="ctrl-input" /></label>
            <label><span>rdry（供热介质）</span><input v-model="editModal.rdry" type="text" class="ctrl-input" /></label>
            <label><span>rdss（产权归属）</span><input v-model="editModal.rdss" type="text" class="ctrl-input" /></label>
            <label><span>rdjg（价格分类）</span><input v-model="editModal.rdjg" type="text" class="ctrl-input" /></label>
            <label><span>rdgz（改造批次）</span><input v-model="editModal.rdgz" type="text" class="ctrl-input" /></label>
          </div>
          <div class="modal-actions">
            <button class="btn secondary btn-sm" type="button" @click="editModal.open = false">取消</button>
            <button class="btn primary btn-sm" type="button" @click="saveModal">保存修改</button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import PlatformSubNav from '../components/PlatformSubNav.vue'
import { computed, onMounted, reactive, ref } from 'vue'
import {
  fetchDictItems,
  fetchDictOverview,
  patchMerchantDict,
  patchStationDict,
} from '../services/api'

const overview = ref({})
const activeEntity = ref('stations')
const items = ref([])
const keyword = ref('')
const onlyMissing = ref(false)
const notice = reactive({ type: 'info', text: '' })

const editModal = reactive({
  open: false,
  kind: '',
  id: '',
  title: '',
  covered_area: null,
  rdfz: '',
  rdry: '',
  rdss: '',
  rdjg: '',
  rdgz: '',
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热平台精算模块', to: '/projects/smart_heating_platform/pages' },
  { label: '8类主体台账', to: null },
])

const entityTabs = [
  { key: 'stations', label: '换热站', countKey: 'stations', warnKey: 'missing_area_stations', warnText: (n) => `${n} 座缺面积` },
  { key: 'zones', label: '二次网分区', countKey: 'zones', warnKey: 'offline_zones', warnText: (n) => `${n} 个常离线` },
  { key: 'temp_devices', label: '居民测温户', countKey: 'temp_devices', warnKey: 'alias_groups', warnText: (n) => `${n} 组别名归口` },
  { key: 'merchants', label: '商业用户', countKey: 'merchants', warnKey: 'missing_tag_merchants', warnText: (n) => `${n} 户缺标签` },
  { key: 'upstream_points', label: '上游核心测点', countKey: 'upstream_points' },
  { key: 'centers', label: '服务中心', countKey: 'centers' },
  { key: 'main_networks', label: '主干热网', countKey: 'main_networks' },
  { key: 'branch_networks', label: '支线网', countKey: 'branch_networks' },
  { key: 'unregistered_temp_devices', label: '未入账室温终端', countKey: 'unregistered_temp_devices' },
]

const canFilterMissing = computed(() =>
  ['stations', 'zones', 'temp_devices', 'merchants'].includes(activeEntity.value),
)

const missingFilterLabel = computed(() => {
  if (activeEntity.value === 'stations') return `仅看缺失供热面积 (${overview.value.missing_area_stations ?? 0})`
  if (activeEntity.value === 'zones') return `仅看台账常离线分区 (${overview.value.offline_zones ?? 0})`
  if (activeEntity.value === 'temp_devices') return `仅看非标别名归口户 (${overview.value.alias_groups ?? 0})`
  if (activeEntity.value === 'merchants') return `仅看缺失五维标签 (${overview.value.missing_tag_merchants ?? 0})`
  return ''
})

const genericColumns = computed(() => (items.value.length ? Object.keys(items.value[0]) : []))

async function loadOverview() {
  const res = await fetchDictOverview()
  if (res?.data) overview.value = res.data
}

async function loadItems() {
  const res = await fetchDictItems(activeEntity.value, {
    only_missing: onlyMissing.value ? 'true' : '',
    keyword: keyword.value,
  })
  if (res?.data) items.value = res.data
}

async function loadAll() {
  try {
    await Promise.all([loadOverview(), loadItems()])
  } catch (err) {
    notice.type = 'error'
    notice.text = err.message
  }
}

function selectEntity(key) {
  activeEntity.value = key
  onlyMissing.value = false
  keyword.value = ''
  loadItems()
}

function openEditStation(row) {
  editModal.open = true
  editModal.kind = 'station'
  editModal.id = row.station_id
  editModal.title = `补录换热站台账：${row.name}`
  editModal.covered_area = row.covered_area
  editModal.rdfz = row.rdfz || ''
}

function openEditMerchant(row) {
  editModal.open = true
  editModal.kind = 'merchant'
  editModal.id = row.merchant_id
  editModal.title = `补录商业用户五维标签：${row.name}`
  editModal.rdfz = row.rdfz || ''
  editModal.rdry = row.rdry || ''
  editModal.rdss = row.rdss || ''
  editModal.rdjg = row.rdjg || ''
  editModal.rdgz = row.rdgz || ''
}

async function saveModal() {
  try {
    if (editModal.kind === 'station') {
      await patchStationDict(editModal.id, {
        covered_area: editModal.covered_area,
        rdfz: editModal.rdfz || null,
      })
    } else if (editModal.kind === 'merchant') {
      await patchMerchantDict(editModal.id, {
        rdfz: editModal.rdfz || null,
        rdry: editModal.rdry || null,
        rdss: editModal.rdss || null,
        rdjg: editModal.rdjg || null,
        rdgz: editModal.rdgz || null,
      })
    }
    editModal.open = false
    notice.type = 'success'
    notice.text = '台账记录已保存更新。'
    await loadAll()
  } catch (err) {
    notice.type = 'error'
    notice.text = `保存失败：${err.message}`
  }
}

onMounted(loadAll)
</script>

<style scoped>
.shp-main { padding: 18px 16px 40px; max-width: 1400px; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.topbar { padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.topbar h2 { margin: 0; font-size: 18px; }
.subtitle { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.notice-banner { padding: 10px 14px; border-radius: 8px; font-size: 13px; }
.notice-banner.success { background: #ecfdf5; color: #065f46; }
.notice-banner.error { background: #fef2f2; color: #991b1b; }
.entity-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
.entity-btn { padding: 12px 14px; text-align: left; display: flex; flex-direction: column; gap: 4px; cursor: pointer; border: 2px solid transparent; }
.entity-btn.active { border-color: #1d4ed8; background: #eff6ff; }
.ent-label { font-size: 12px; color: #475569; }
.ent-count { font-size: 18px; color: #0f172a; }
.ent-warn { font-size: 11px; color: #d97706; font-weight: 600; }
.list-card { padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.filter-bar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.ctrl-input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 10px; font-size: 13px; background: #fff; }
.check-inline { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.table-wrap { overflow-x: auto; max-height: 540px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.data-table th, .data-table td { padding: 9px 11px; border-bottom: 1px solid #e2e8f0; text-align: left; }
.data-table thead th { position: sticky; top: 0; background: #f8fafc; font-weight: 600; z-index: 4; }
.font-bold { font-weight: 600; }
.text-warn { color: #d97706; }
.empty-td { text-align: center !important; color: #64748b; padding: 28px !important; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.modal-backdrop { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45); display: flex; align-items: center; justify-content: center; z-index: 60; }
.modal-box { width: min(460px, 92vw); padding: 20px 22px; display: flex; flex-direction: column; gap: 14px; }
.modal-box h3 { margin: 0; font-size: 16px; }
.modal-fields { display: flex; flex-direction: column; gap: 10px; }
.modal-fields label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; font-weight: 600; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; }

@media (max-width: 768px) {
  .shp-main { padding: 12px 10px 28px; gap: 10px; }
  .topbar, .list-card { padding: 12px; }
  .topbar h2 { font-size: 16px; }
  .entity-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .entity-btn { padding: 10px 11px; }
  .ent-count { font-size: 16px; }
  .filter-bar > .ctrl-input { flex: 1 1 160px; min-width: 0; }
  .data-table { font-size: 12px; }
  .data-table th, .data-table td { padding: 7px 8px; }
  .modal-box { padding: 16px; }
}
</style>
