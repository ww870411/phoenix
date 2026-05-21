<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <header class="topbar">
        <div>
          <h2>全局管理入口</h2>
          <p class="sub">仅供 Global_admin 使用。优先按分块修改和保存，减少一次性误改全局配置的风险。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost" type="button" @click="goProjectPages">返回功能页</button>
          <button class="btn ghost" type="button" :disabled="loading" @click="loadConfig">
            {{ loading ? '加载中…' : '刷新配置' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>
      <p v-if="globalMessage" :class="['page-tip', globalMessage.type]">{{ globalMessage.text }}</p>

      <section class="card elevated">
        <div class="card-header-row">
          <div class="card-header">核心参数</div>
          <div class="section-actions">
            <button class="btn" type="button" :disabled="isSaving('core_dates')" @click="saveCoreDatesSection">
              {{ isSaving('core_dates') ? '保存中…' : '保存本区块' }}
            </button>
          </div>
        </div>
        <div class="field-grid">
          <label class="field">
            <span>biz_date</span>
            <input v-model="bizDate" type="date" />
          </label>
          <label class="field">
            <span>plan_start_date</span>
            <input v-model="planStartDate" type="date" />
          </label>
          <label class="field">
            <span>plan_editable_days</span>
            <input v-model.number="planEditableDays" type="number" min="0" max="3" step="1" />
            <small class="field-help">`3` 为三天都可改，`2` 为最后两天可改，`1` 为仅最后一天可改，`0` 为全部不可改。</small>
          </label>
        </div>
        <p v-if="sectionMessage('core_dates')" :class="['section-tip', sectionMessage('core_dates').type]">
          {{ sectionMessage('core_dates').text }}
        </p>
        <div class="summary-row">
          <span class="summary-chip">供给主体：{{ supplyEntities.length }}</span>
          <span class="summary-chip">换热站：{{ demandEntities.length }}</span>
          <span class="summary-chip">型号：{{ pipeModels.length }}</span>
          <span class="summary-chip">负责人映射：{{ managerAssignments.length }}</span>
          <span class="summary-chip">施工单位：{{ constructionUnits.length }}</span>
          <span class="summary-chip">施工映射：{{ constructionAssignments.length }}</span>
          <span class="summary-chip">基准预设：{{ baselinePresets.length }}</span>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header-row">
          <div class="card-header">供给主体</div>
          <div class="section-actions">
            <button class="btn ghost" type="button" @click="addSupplyEntity">新增一行</button>
            <button class="btn" type="button" :disabled="isSaving('supply_entities')" @click="saveSection('supply_entities')">
              {{ isSaving('supply_entities') ? '保存中…' : '保存本区块' }}
            </button>
          </div>
        </div>
        <p v-if="sectionMessage('supply_entities')" :class="['section-tip', sectionMessage('supply_entities').type]">
          {{ sectionMessage('supply_entities').text }}
        </p>
        <div class="table-wrap">
          <table class="table editor-table">
            <thead>
              <tr>
                <th>主体ID</th>
                <th>主体名称</th>
                <th>简称</th>
                <th>联系人</th>
                <th>联系电话</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in supplyEntities" :key="`${item.entity_id || 'new'}-${index}`">
                <td><input v-model.trim="item.entity_id" type="text" /></td>
                <td><input v-model.trim="item.entity_name" type="text" /></td>
                <td><input v-model.trim="item.entity_short_name" type="text" /></td>
                <td><input v-model.trim="item.contact_name" type="text" /></td>
                <td><input v-model.trim="item.contact_phone" type="text" /></td>
                <td><input v-model.trim="item.status" type="text" /></td>
                <td><button class="btn danger" type="button" @click="removeRow(supplyEntities, index)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header-row">
          <div class="card-header">换热站</div>
          <div class="section-actions">
            <button class="btn ghost" type="button" @click="addDemandEntity">新增一行</button>
            <button class="btn" type="button" :disabled="isSaving('demand_entities')" @click="saveSection('demand_entities')">
              {{ isSaving('demand_entities') ? '保存中…' : '保存本区块' }}
            </button>
          </div>
        </div>
        <p v-if="sectionMessage('demand_entities')" :class="['section-tip', sectionMessage('demand_entities').type]">
          {{ sectionMessage('demand_entities').text }}
        </p>
        <div class="table-wrap">
          <table class="table editor-table">
            <thead>
              <tr>
                <th>站点ID</th>
                <th>站点名称</th>
                <th>区域</th>
                <th>标段</th>
                <th>施工状态</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in demandEntities" :key="`${item.station_id || 'new'}-${index}`">
                <td><input v-model.trim="item.station_id" type="text" /></td>
                <td><input v-model.trim="item.station_name" type="text" /></td>
                <td><input v-model.trim="item.region" type="text" /></td>
                <td><input v-model.trim="item.section" type="text" /></td>
                <td><input v-model.trim="item.construction_status" type="text" /></td>
                <td><input v-model.trim="item.status" type="text" /></td>
                <td><button class="btn danger" type="button" @click="removeRow(demandEntities, index)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header-row">
          <div class="card-header">保温管型号</div>
          <div class="section-actions">
            <button class="btn ghost" type="button" @click="addPipeModel">新增一行</button>
            <button class="btn" type="button" :disabled="isSaving('pipe_models')" @click="saveSection('pipe_models')">
              {{ isSaving('pipe_models') ? '保存中…' : '保存本区块' }}
            </button>
          </div>
        </div>
        <p class="sub block-sub">如果要增加或删除型号，直接在这里操作即可；保存后，基准量预设区可以再按站点补齐缺失型号。</p>
        <p v-if="sectionMessage('pipe_models')" :class="['section-tip', sectionMessage('pipe_models').type]">
          {{ sectionMessage('pipe_models').text }}
        </p>
        <div class="table-wrap">
          <table class="table editor-table">
            <thead>
              <tr>
                <th>型号ID</th>
                <th>型号名称</th>
                <th>口径标签</th>
                <th>单位</th>
                <th>分类</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in pipeModels" :key="`${item.pipe_model_id || 'new'}-${index}`">
                <td><input v-model.trim="item.pipe_model_id" type="text" /></td>
                <td><input v-model.trim="item.pipe_model_name" type="text" /></td>
                <td><input v-model.trim="item.diameter_label" type="text" /></td>
                <td><input v-model.trim="item.unit" type="text" /></td>
                <td><input v-model.trim="item.category" type="text" /></td>
                <td><input v-model.trim="item.status" type="text" /></td>
                <td><button class="btn danger" type="button" @click="removeRow(pipeModels, index)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header-row">
          <div class="card-header">现场负责人映射</div>
          <div class="section-actions">
            <button class="btn ghost" type="button" @click="addManagerAssignment">新增一行</button>
            <button class="btn" type="button" :disabled="isSaving('manager_assignments')" @click="saveSection('manager_assignments')">
              {{ isSaving('manager_assignments') ? '保存中…' : '保存本区块' }}
            </button>
          </div>
        </div>
        <p class="sub block-sub">多个换热站请用英文逗号分隔，例如 `station_a, station_b`。</p>
        <p v-if="sectionMessage('manager_assignments')" :class="['section-tip', sectionMessage('manager_assignments').type]">
          {{ sectionMessage('manager_assignments').text }}
        </p>
        <div class="table-wrap">
          <table class="table editor-table">
            <thead>
              <tr>
                <th>负责人ID</th>
                <th>负责人名称</th>
                <th>换热站ID列表</th>
                <th>换热站名称列表</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in managerAssignments" :key="`${item.manager_id || 'new'}-${index}`">
                <td><input v-model.trim="item.manager_id" type="text" /></td>
                <td><input v-model.trim="item.manager_name" type="text" /></td>
                <td><input v-model.trim="item.station_ids_text" type="text" /></td>
                <td><input v-model.trim="item.station_names_text" type="text" /></td>
                <td><input v-model.trim="item.status" type="text" /></td>
                <td><button class="btn danger" type="button" @click="removeRow(managerAssignments, index)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header-row">
          <div class="card-header">施工单位</div>
          <div class="section-actions">
            <button class="btn ghost" type="button" @click="addConstructionUnit">新增一行</button>
            <button class="btn" type="button" :disabled="isSaving('construction_units')" @click="saveSection('construction_units')">
              {{ isSaving('construction_units') ? '保存中…' : '保存本区块' }}
            </button>
          </div>
        </div>
        <p v-if="sectionMessage('construction_units')" :class="['section-tip', sectionMessage('construction_units').type]">
          {{ sectionMessage('construction_units').text }}
        </p>
        <div class="table-wrap">
          <table class="table editor-table">
            <thead>
              <tr>
                <th>单位ID</th>
                <th>单位名称</th>
                <th>联系人</th>
                <th>联系电话</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in constructionUnits" :key="`${item.unit_id || 'new'}-${index}`">
                <td><input v-model.trim="item.unit_id" type="text" /></td>
                <td><input v-model.trim="item.unit_name" type="text" /></td>
                <td><input v-model.trim="item.contact_name" type="text" /></td>
                <td><input v-model.trim="item.contact_phone" type="text" /></td>
                <td><input v-model.trim="item.status" type="text" /></td>
                <td><button class="btn danger" type="button" @click="removeRow(constructionUnits, index)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header-row">
          <div class="card-header">施工单位映射</div>
          <div class="section-actions">
            <button class="btn ghost" type="button" @click="addConstructionAssignment">新增一行</button>
            <button class="btn" type="button" :disabled="isSaving('construction_assignments')" @click="saveSection('construction_assignments')">
              {{ isSaving('construction_assignments') ? '保存中…' : '保存本区块' }}
            </button>
          </div>
        </div>
        <p class="sub block-sub">多个换热站请用英文逗号分隔，例如 `station_a, station_c`。</p>
        <p v-if="sectionMessage('construction_assignments')" :class="['section-tip', sectionMessage('construction_assignments').type]">
          {{ sectionMessage('construction_assignments').text }}
        </p>
        <div class="table-wrap">
          <table class="table editor-table">
            <thead>
              <tr>
                <th>单位ID</th>
                <th>单位名称</th>
                <th>换热站ID列表</th>
                <th>换热站名称列表</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in constructionAssignments" :key="`${item.unit_id || 'new'}-${index}`">
                <td><input v-model.trim="item.unit_id" type="text" /></td>
                <td><input v-model.trim="item.unit_name" type="text" /></td>
                <td><input v-model.trim="item.station_ids_text" type="text" /></td>
                <td><input v-model.trim="item.station_names_text" type="text" /></td>
                <td><input v-model.trim="item.status" type="text" /></td>
                <td><button class="btn danger" type="button" @click="removeRow(constructionAssignments, index)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="card elevated">
        <div class="card-header-row">
          <div>
            <div class="card-header">基准量预设</div>
            <p class="sub block-sub">先选择换热站，再维护该站点下的型号与设计值，避免一次展开全部换热站。</p>
          </div>
          <div class="section-actions baseline-actions">
            <label class="field inline-field">
              <span>换热站</span>
              <select v-model="selectedBaselineStationId">
                <option v-for="station in demandEntities" :key="station.station_id" :value="station.station_id">
                  {{ station.station_name || station.station_id }}
                </option>
              </select>
            </label>
            <button class="btn ghost" type="button" @click="addBaselinePreset">新增一行</button>
            <button class="btn ghost" type="button" @click="fillMissingPipeModelsForSelectedStation">补齐缺失型号</button>
            <button class="btn" type="button" :disabled="isSaving('baseline_presets')" @click="saveSection('baseline_presets')">
              {{ isSaving('baseline_presets') ? '保存中…' : '保存本区块' }}
            </button>
          </div>
        </div>
        <p v-if="sectionMessage('baseline_presets')" :class="['section-tip', sectionMessage('baseline_presets').type]">
          {{ sectionMessage('baseline_presets').text }}
        </p>
        <div class="summary-row baseline-summary">
          <span class="summary-chip">当前站点：{{ selectedBaselineStationName }}</span>
          <span class="summary-chip">当前显示：{{ filteredBaselinePresets.length }} 条</span>
          <span class="summary-chip">全量预设：{{ baselinePresets.length }} 条</span>
        </div>
        <div class="table-wrap">
          <table class="table editor-table baseline-table">
            <thead>
              <tr>
                <th>型号</th>
                <th>设计值(m)</th>
                <th>计划使用量(m)</th>
                <th>备注</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filteredBaselinePresets" :key="item.__row_key">
                <td>
                  <select v-model="item.pipe_model_id" @change="syncBaselinePipeModelName(item)">
                    <option v-for="model in pipeModels" :key="model.pipe_model_id" :value="model.pipe_model_id">
                      {{ model.pipe_model_name || model.pipe_model_id }}
                    </option>
                  </select>
                </td>
                <td><input v-model.number="item.design_qty" type="number" min="0" step="1" /></td>
                <td><input v-model.number="item.purchase_plan_qty" type="number" min="0" step="1" /></td>
                <td><input v-model.trim="item.remark" type="text" /></td>
                <td><button class="btn danger" type="button" @click="removeBaselinePreset(item.__row_key)">删除</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <details class="card elevated json-details">
        <summary>原始 JSON 折叠查看</summary>
        <p class="sub block-sub">这里只用于核对最终保存内容，日常维护建议优先使用上面的分块编辑区。</p>
        <textarea :value="configPreviewText" class="json-editor" readonly spellcheck="false"></textarea>
      </details>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'
import {
  getTubeGlobalManagementConfig,
  saveTubeGlobalManagementConfigSection,
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'

const {
  loading,
  errorMessage,
  breadcrumbItems,
  goProjectPages,
} = useTubePageShell('全局管理入口')

const configPath = ref('')
const bizDate = ref('')
const planStartDate = ref('')
const planEditableDays = ref(3)
const globalMessage = ref(null)
const sectionMessages = ref({})
const savingSections = ref({})

const supplyEntities = ref([])
const demandEntities = ref([])
const pipeModels = ref([])
const managerAssignments = ref([])
const constructionUnits = ref([])
const constructionAssignments = ref([])
const baselinePresets = ref([])
const selectedBaselineStationId = ref('')

function setGlobalMessage(type, text) {
  globalMessage.value = { type, text }
}

function clearGlobalMessage() {
  globalMessage.value = null
}

function setSectionMessage(section, type, text) {
  sectionMessages.value = {
    ...sectionMessages.value,
    [section]: { type, text },
  }
}

function sectionMessage(section) {
  return sectionMessages.value[section] || null
}

function setSaving(section, value) {
  savingSections.value = {
    ...savingSections.value,
    [section]: value,
  }
}

function isSaving(section) {
  return Boolean(savingSections.value[section])
}

function cloneRows(rows) {
  return JSON.parse(JSON.stringify(Array.isArray(rows) ? rows : []))
}

function listToText(value) {
  return Array.isArray(value) ? value.join(', ') : ''
}

function textToList(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

function defaultQtyByCategory(category) {
  const normalized = String(category || '').trim()
  if (normalized === '中口径') return 160
  if (normalized === '大口径') return 260
  return 240
}

function defaultRemarkByCategory(category) {
  const normalized = String(category || '').trim()
  if (normalized === '中口径') return '演示预设-中口径偏低'
  if (normalized === '大口径') return '演示预设-大口径偏高'
  return '演示预设-小口径偏高'
}

function normalizeAssignmentRows(rows, idKey, nameKey) {
  return cloneRows(rows).map((item) => ({
    ...item,
    station_ids_text: listToText(item.station_ids),
    station_names_text: listToText(item.station_names),
    [idKey]: item[idKey] || '',
    [nameKey]: item[nameKey] || '',
    status: item.status || 'active',
  }))
}

function normalizeBaselineRows(rows) {
  return cloneRows(rows).map((item, index) => ({
    ...item,
    __row_key: `${item.station_id || 'station'}::${item.pipe_model_id || 'model'}::${index}`,
    design_qty: Number(item.design_qty || 0),
    purchase_plan_qty: Number(item.purchase_plan_qty || 0),
    remark: item.remark || '',
  }))
}

function rebuildBaselineRowKeys() {
  baselinePresets.value = baselinePresets.value.map((item, index) => ({
    ...item,
    __row_key: `${item.station_id || 'station'}::${item.pipe_model_id || 'model'}::${index}`,
  }))
}

function syncSelectedBaselineStation() {
  const stationIds = demandEntities.value
    .map((item) => String(item.station_id || '').trim())
    .filter(Boolean)
  if (!stationIds.length) {
    selectedBaselineStationId.value = ''
    return
  }
  if (!stationIds.includes(selectedBaselineStationId.value)) {
    selectedBaselineStationId.value = stationIds[0]
  }
}

function applyConfig(config) {
  configPath.value = configPath.value || ''
  bizDate.value = config.biz_date || ''
  planStartDate.value = config.plan_start_date || config.biz_date || ''
  planEditableDays.value = Number(config.plan_editable_days ?? 3)
  supplyEntities.value = cloneRows(config.supply_entities)
  demandEntities.value = cloneRows(config.demand_entities)
  pipeModels.value = cloneRows(config.pipe_models)
  managerAssignments.value = normalizeAssignmentRows(config.manager_assignments, 'manager_id', 'manager_name')
  constructionUnits.value = cloneRows(config.construction_units)
  constructionAssignments.value = normalizeAssignmentRows(config.construction_assignments, 'unit_id', 'unit_name')
  baselinePresets.value = normalizeBaselineRows(config.baseline_presets)
  syncSelectedBaselineStation()
}

const selectedBaselineStationName = computed(() => {
  const matched = demandEntities.value.find((item) => item.station_id === selectedBaselineStationId.value)
  return matched?.station_name || selectedBaselineStationId.value || '未选择'
})

const filteredBaselinePresets = computed(() =>
  baselinePresets.value.filter((item) => item.station_id === selectedBaselineStationId.value),
)

function buildSectionPayload(section) {
  if (section === 'biz_date') {
    return bizDate.value || ''
  }
  if (section === 'plan_start_date') {
    return planStartDate.value || ''
  }
  if (section === 'plan_editable_days') {
    return Number(planEditableDays.value ?? 3)
  }
  if (section === 'supply_entities') {
    return cloneRows(supplyEntities.value)
  }
  if (section === 'demand_entities') {
    return cloneRows(demandEntities.value)
  }
  if (section === 'pipe_models') {
    return cloneRows(pipeModels.value)
  }
  if (section === 'manager_assignments') {
    return managerAssignments.value.map((item) => ({
      manager_id: item.manager_id || '',
      manager_name: item.manager_name || '',
      station_ids: textToList(item.station_ids_text),
      station_names: textToList(item.station_names_text),
      status: item.status || 'active',
    }))
  }
  if (section === 'construction_units') {
    return cloneRows(constructionUnits.value)
  }
  if (section === 'construction_assignments') {
    return constructionAssignments.value.map((item) => ({
      unit_id: item.unit_id || '',
      unit_name: item.unit_name || '',
      station_ids: textToList(item.station_ids_text),
      station_names: textToList(item.station_names_text),
      status: item.status || 'active',
    }))
  }
  if (section === 'baseline_presets') {
    return baselinePresets.value.map((item) => ({
      station_id: item.station_id || '',
      station_name: item.station_name || '',
      pipe_model_id: item.pipe_model_id || '',
      pipe_model_name: item.pipe_model_name || '',
      design_qty: Number(item.design_qty || 0),
      purchase_plan_qty: Number(item.purchase_plan_qty || 0),
      remark: item.remark || '',
    }))
  }
  return null
}

const configPreviewText = computed(() =>
  JSON.stringify(
    {
      biz_date: bizDate.value || '',
      plan_start_date: planStartDate.value || '',
      plan_editable_days: Number(planEditableDays.value ?? 3),
      supply_entities: buildSectionPayload('supply_entities'),
      demand_entities: buildSectionPayload('demand_entities'),
      pipe_models: buildSectionPayload('pipe_models'),
      manager_assignments: buildSectionPayload('manager_assignments'),
      construction_units: buildSectionPayload('construction_units'),
      construction_assignments: buildSectionPayload('construction_assignments'),
      baseline_presets: buildSectionPayload('baseline_presets'),
    },
    null,
    2,
  ),
)

async function loadConfig() {
  clearGlobalMessage()
  try {
    const response = await getTubeGlobalManagementConfig(PROJECT_KEY)
    const config = response.config || {}
    configPath.value = response.config_path || ''
    applyConfig(config)
  } catch (error) {
    setGlobalMessage('error', error?.message || '读取全局配置失败')
  }
}

async function saveSection(section) {
  clearGlobalMessage()
  setSectionMessage(section, 'success', '')
  setSaving(section, true)
  try {
    const response = await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section,
      data: buildSectionPayload(section),
    })
    configPath.value = response.config_path || configPath.value
    applyConfig(response.config || {})
    if (response.biz_date) {
      bizDate.value = response.biz_date
    }
    if (response.plan_start_date) {
      planStartDate.value = response.plan_start_date
    }
    if (response.plan_editable_days !== undefined) {
      planEditableDays.value = Number(response.plan_editable_days ?? 3)
    }
    setSectionMessage(section, 'success', '本区块已保存。')
  } catch (error) {
    setSectionMessage(section, 'error', error?.message || '保存失败')
  } finally {
    setSaving(section, false)
  }
}

async function saveCoreDatesSection() {
  clearGlobalMessage()
  setSaving('core_dates', true)
  try {
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'biz_date',
      data: bizDate.value || '',
    })
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'plan_start_date',
      data: planStartDate.value || '',
    })
    const response = await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'plan_editable_days',
      data: Number(planEditableDays.value ?? 3),
    })
    applyConfig(response.config || {})
    if (response.biz_date) {
      bizDate.value = response.biz_date
    }
    if (response.plan_start_date) {
      planStartDate.value = response.plan_start_date
    }
    if (response.plan_editable_days !== undefined) {
      planEditableDays.value = Number(response.plan_editable_days ?? 3)
    }
    setSectionMessage('core_dates', 'success', '核心日期已保存。')
  } catch (error) {
    setSectionMessage('core_dates', 'error', error?.message || '保存失败')
  } finally {
    setSaving('core_dates', false)
  }
}

function removeRow(targetRef, index) {
  targetRef.value.splice(index, 1)
}

function addSupplyEntity() {
  supplyEntities.value.push({
    entity_id: '',
    entity_name: '',
    entity_short_name: '',
    contact_name: '',
    contact_phone: '',
    status: 'active',
  })
}

function addDemandEntity() {
  demandEntities.value.push({
    station_id: '',
    station_name: '',
    region: '',
    section: '',
    construction_status: '',
    status: 'active',
  })
}

function addPipeModel() {
  pipeModels.value.push({
    pipe_model_id: '',
    pipe_model_name: '',
    diameter_label: '',
    unit: '米',
    category: '小口径',
    status: 'active',
  })
}

function addManagerAssignment() {
  managerAssignments.value.push({
    manager_id: '',
    manager_name: '',
    station_ids_text: '',
    station_names_text: '',
    status: 'active',
  })
}

function addConstructionUnit() {
  constructionUnits.value.push({
    unit_id: '',
    unit_name: '',
    contact_name: '',
    contact_phone: '',
    status: 'active',
  })
}

function addConstructionAssignment() {
  constructionAssignments.value.push({
    unit_id: '',
    unit_name: '',
    station_ids_text: '',
    station_names_text: '',
    status: 'active',
  })
}

function resolvePipeModelById(pipeModelId) {
  return pipeModels.value.find((item) => item.pipe_model_id === pipeModelId) || null
}

function syncBaselinePipeModelName(row) {
  const matched = resolvePipeModelById(row.pipe_model_id)
  if (!matched) return
  row.pipe_model_name = matched.pipe_model_name || matched.pipe_model_id
  if (!row.design_qty) {
    row.design_qty = defaultQtyByCategory(matched.category)
  }
  if (!row.purchase_plan_qty) {
    row.purchase_plan_qty = defaultQtyByCategory(matched.category)
  }
  if (!row.remark) {
    row.remark = defaultRemarkByCategory(matched.category)
  }
}

function addBaselinePreset() {
  const currentStation = demandEntities.value.find((item) => item.station_id === selectedBaselineStationId.value)
  const firstModel = pipeModels.value[0] || null
  baselinePresets.value.push({
    __row_key: `new::${Date.now()}`,
    station_id: selectedBaselineStationId.value || '',
    station_name: currentStation?.station_name || '',
    pipe_model_id: firstModel?.pipe_model_id || '',
    pipe_model_name: firstModel?.pipe_model_name || '',
    design_qty: defaultQtyByCategory(firstModel?.category),
    purchase_plan_qty: defaultQtyByCategory(firstModel?.category),
    remark: defaultRemarkByCategory(firstModel?.category),
  })
  rebuildBaselineRowKeys()
}

function removeBaselinePreset(rowKey) {
  baselinePresets.value = baselinePresets.value.filter((item) => item.__row_key !== rowKey)
  rebuildBaselineRowKeys()
}

function fillMissingPipeModelsForSelectedStation() {
  const currentStation = demandEntities.value.find((item) => item.station_id === selectedBaselineStationId.value)
  if (!currentStation) {
    setGlobalMessage('error', '请先选择一个有效换热站。')
    return
  }
  const existingModelIds = new Set(
    baselinePresets.value
      .filter((item) => item.station_id === selectedBaselineStationId.value)
      .map((item) => item.pipe_model_id),
  )
  pipeModels.value.forEach((model) => {
    if (!model.pipe_model_id || existingModelIds.has(model.pipe_model_id)) {
      return
    }
    baselinePresets.value.push({
      __row_key: `new::${currentStation.station_id}::${model.pipe_model_id}::${Date.now()}`,
      station_id: currentStation.station_id,
      station_name: currentStation.station_name || currentStation.station_id,
      pipe_model_id: model.pipe_model_id,
      pipe_model_name: model.pipe_model_name || model.pipe_model_id,
      design_qty: defaultQtyByCategory(model.category),
      purchase_plan_qty: defaultQtyByCategory(model.category),
      remark: defaultRemarkByCategory(model.category),
    })
  })
  rebuildBaselineRowKeys()
  setSectionMessage('baseline_presets', 'success', '已为当前换热站补齐缺失型号。记得点击“保存本区块”。')
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.tube-page-root { min-height: 100vh; background: var(--bg); }
.tube-page-main { display: flex; flex-direction: column; gap: 16px; padding-top: 18px; padding-bottom: 24px; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.page-error { margin: 0; color: var(--danger); }
.page-tip { margin: 0; font-size: 14px; }
.page-tip.success { color: #15803d; }
.page-tip.error { color: var(--danger); }
.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.section-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: flex-end;
}
.field-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field-help { color: #64748b; font-size: 12px; line-height: 1.5; }
.inline-field {
  min-width: 220px;
}
.field span { font-size: 13px; color: var(--muted); }
.field input,
.field select,
.editor-table input,
.editor-table select,
.json-editor {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  box-sizing: border-box;
  width: 100%;
  background: #fff;
}
.readonly-box {
  min-height: 42px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  color: #475569;
  word-break: break-all;
}
.summary-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
.baseline-summary { margin-top: 0; margin-bottom: 12px; }
.summary-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef2ff;
  color: #334155;
  font-size: 13px;
}
.block-sub { margin: 0 0 12px; }
.section-tip {
  margin: 0 0 12px;
  font-size: 13px;
}
.section-tip.success { color: #15803d; }
.section-tip.error { color: var(--danger); }
.editor-table th,
.editor-table td {
  vertical-align: top;
}
.baseline-table {
  min-width: 920px;
}
.json-details summary {
  cursor: pointer;
  font-weight: 600;
  color: #0f172a;
}
.json-editor {
  width: 100%;
  min-height: 320px;
  margin-top: 12px;
  font-family: Consolas, Monaco, monospace;
  line-height: 1.5;
  resize: vertical;
  background: #f8fafc;
}
@media (max-width: 900px) {
  .card-header-row,
  .topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .section-actions {
    align-items: stretch;
  }
}
</style>
