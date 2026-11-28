<template>
  <div class="seating-app">
    <AppHeader class="noprint" />

    <div class="seating-shell">
      <Breadcrumbs class="noprint" :items="breadcrumbItems" />

      <!-- 顶部工具与存档管理栏 -->
      <section class="top-toolbar card noprint">
        <div class="toolbar-main">
          <div class="title-block">
            <div class="title-row">
              <h2>会议排座助手</h2>
              <span class="admin-pill">Global_admin 专属</span>
              <span class="save-badge" :class="saveStateClass">{{ saveStateText }}</span>
            </div>
            <p class="sub">
              实景三桌拼接会场 · 按边设置座位数 · 多方案云端配置文件存档与 A4 打印
            </p>
          </div>

          <div class="toolbar-actions">
            <button type="button" class="btn sm" :disabled="!history.length" @click="undo">撤销</button>
            <button type="button" class="btn sm" :disabled="!future.length" @click="redo">重做</button>
            <button type="button" class="btn sm warn" @click="initSeatingOnly">初始化排座</button>
            <button type="button" class="btn sm warn" @click="openResetLayoutModal">初始化布局</button>
            <button type="button" class="btn sm" @click="exportJson">导出方案</button>
            <button type="button" class="btn sm" @click="triggerImport">导入方案</button>
            <button type="button" class="btn sm" @click="exportCsv">导出名单</button>
            <button type="button" class="btn sm primary" @click="handlePrint">打印 / PDF</button>
            <button type="button" class="btn sm ghost" @click="goProjects">返回项目</button>
            <input
              ref="importInputRef"
              type="file"
              accept=".json,application/json"
              class="hidden-file"
              @change="onImportFile"
            />
          </div>
        </div>

        <!-- 配置文件多存档控制条 -->
        <div class="profile-bar">
          <div class="profile-select-group">
            <label class="profile-label" for="profile-select">当前存档</label>
            <select
              id="profile-select"
              class="profile-select"
              :value="activeProfileId"
              :disabled="profileBusy"
              @change="onSwitchProfile($event.target.value)"
            >
              <option v-for="p in profiles" :key="p.id" :value="p.id">
                {{ p.name }}（{{ p.summary?.assigned_seats ?? 0 }}/{{ p.summary?.total_seats ?? 0 }}席）
              </option>
            </select>
          </div>

          <div class="profile-btn-group">
            <button type="button" class="btn sm primary" :disabled="profileBusy || !activeProfileId" @click="saveCurrentProfile(true)">
              保存存档
            </button>
            <button type="button" class="btn sm" :disabled="profileBusy" @click="openProfileModal('create')">
              ＋新建存档
            </button>
            <button type="button" class="btn sm" :disabled="profileBusy || !activeProfileId" @click="openProfileModal('rename')">
              重命名
            </button>
            <button
              type="button"
              class="btn sm danger-outline"
              :disabled="profileBusy || profiles.length <= 1"
              @click="handleDeleteProfile"
            >
              删除存档
            </button>
          </div>
        </div>
      </section>

      <!-- 主工作区：左侧（或移动端下侧）控制面板 + 右侧（或移动端上侧）交互平面图 -->
      <div class="workspace-grid">
        <!-- 移动端分栏切换条 -->
        <div class="mobile-tabs noprint" role="tablist" aria-label="编辑面板切换">
          <button
            v-for="tab in panelTabs"
            :key="tab.key"
            type="button"
            class="mobile-tab-btn"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- 控制面板 -->
        <aside class="panel card noprint">
          <!-- Tab 1: 会议资料与会场设施 -->
          <section v-show="isTabVisible('info')" class="panel-section">
            <h3>01 · 会议资料与会场设施</h3>
            <label class="field-label" for="meeting-title">会议名称</label>
            <input
              id="meeting-title"
              :value="layout.meeting"
              maxlength="100"
              @input="mutateLayout((d) => { d.meeting = $event.target.value })"
            />
            <label class="field-label" for="meeting-sub">日期 / 地点 / 备注</label>
            <input
              id="meeting-sub"
              :value="layout.subtitle"
              maxlength="120"
              placeholder="例如：2026年11月 · 集团二楼大会议室"
              @input="mutateLayout((d) => { d.subtitle = $event.target.value })"
            />

            <div class="row-2col" style="margin-top: 10px">
              <div>
                <label class="field-label" for="paper-dir">打印方向</label>
                <select
                  id="paper-dir"
                  :value="layout.paper"
                  @change="mutateLayout((d) => { d.paper = $event.target.value === 'portrait' ? 'portrait' : 'landscape' })"
                >
                  <option value="landscape">A4 横向</option>
                  <option value="portrait">A4 纵向</option>
                </select>
              </div>
              <div class="checks-stack">
                <label class="checkline">
                  <input
                    type="checkbox"
                    :checked="layout.mono"
                    @change="mutateLayout((d) => { d.mono = $event.target.checked })"
                  />
                  黑白打印
                </label>
                <label class="checkline">
                  <input
                    type="checkbox"
                    :checked="layout.numbers"
                    @change="mutateLayout((d) => { d.numbers = $event.target.checked })"
                  />
                  显示座位编号
                </label>
              </div>
            </div>

            <div style="margin-top: 8px">
              <label class="field-label" for="empty-seat-display">空位显示方式</label>
              <select
                id="empty-seat-display"
                :value="layout.emptySeatDisplay || 'label'"
                @change="mutateLayout((d) => { d.emptySeatDisplay = normalizeEmptySeatDisplay($event.target.value) })"
              >
                <option value="label">显示“空位”</option>
                <option value="dash">显示“-”</option>
                <option value="blank">显示为空白</option>
              </select>
            </div>

            <div class="sub-box">
              <div class="sub-box-title">会场门窗与设备室</div>
              <div class="checks-stack">
                <label class="checkline">
                  <input
                    type="checkbox"
                    :checked="layout.room?.door?.enabled"
                    @change="mutateLayout((d) => { d.room.door.enabled = $event.target.checked })"
                  />
                  右上位置双开外开门（朝上方外开）
                </label>
                <label class="checkline">
                  <input
                    type="checkbox"
                    :checked="layout.room?.equipmentRoom?.enabled !== false"
                    @change="mutateLayout((d) => {
                      if (!d.room.equipmentRoom) d.room.equipmentRoom = { enabled: true, label: '设备室' }
                      d.room.equipmentRoom.enabled = $event.target.checked
                    })"
                  />
                  左上角设备室（含玻璃观察窗）
                </label>
              </div>
              <div class="row-2col" style="margin-top: 8px">
                <div>
                  <label class="field-label" for="left-win">左侧窗户数</label>
                  <input
                    id="left-win"
                    type="number"
                    min="0"
                    max="8"
                    :value="layout.room?.leftWindows ?? 4"
                    @change="mutateLayout((d) => { d.room.leftWindows = clampInt($event.target.value, 0, 8) })"
                  />
                </div>
                <div>
                  <label class="field-label" for="right-win">右侧窗户数</label>
                  <input
                    id="right-win"
                    type="number"
                    min="0"
                    max="8"
                    :value="layout.room?.rightWindows ?? 4"
                    @change="mutateLayout((d) => { d.room.rightWindows = clampInt($event.target.value, 0, 8) })"
                  />
                </div>
              </div>
            </div>
          </section>

          <!-- Tab 2: 按边/排设置座位数量、显隐与花盆控制 -->
          <section v-show="isTabVisible('layout')" class="panel-section">
            <div class="section-head">
              <h3>02 · 座位布局（按边/排设置）</h3>
              <button type="button" class="btn xs warn" @click="openResetLayoutModal">初始化布局</button>
            </div>
            <p class="hint">中央各边 3 桌拼接（屏幕席 6 席、主席席 7 席、其余 8 席），后方各排 4 桌 8 席；点击排名称可改名，数量范围 0–24，可整排隐藏。</p>

            <div class="rows-list">
              <div
                v-for="r in layout.rows"
                :key="r.id"
                class="rowitem"
                :class="{ active: selectedSeat?.rowId === r.id, 'is-hidden-row': r.hidden }"
              >
                <button
                  type="button"
                  class="rowname"
                  title="点击修改排名称"
                  @click="openRowRenameModal(r)"
                >
                  {{ r.id }} {{ r.label }}
                </button>
                <button type="button" class="btn xxs" :disabled="r.seats.length === 0" @click="resizeRow(r.id, r.seats.length - 1)">
                  −
                </button>
                <input
                  type="number"
                  min="0"
                  max="24"
                  :value="r.seats.length"
                  :aria-label="`${r.label}座位数`"
                  @change="resizeRow(r.id, $event.target.value)"
                />
                <button type="button" class="btn xxs" :disabled="r.seats.length >= 24" @click="resizeRow(r.id, r.seats.length + 1)">
                  +
                </button>
                <button
                  type="button"
                  class="btn xxs"
                  :class="{ warn: r.hidden }"
                  :title="r.hidden ? '恢复显示此排桌椅' : '隐藏此排桌椅'"
                  @click="toggleRowHidden(r.id)"
                >
                  {{ r.hidden ? '显' : '隐' }}
                </button>
                <button
                  type="button"
                  class="btn xxs danger-outline"
                  title="删除此排"
                  :disabled="isFixedZone(r.zone)"
                  @click="deleteRow(r)"
                >
                  ×
                </button>
              </div>
            </div>

            <div class="flex-row" style="margin-top: 8px">
              <select v-model="newRowZone" class="grow" aria-label="新增排位置">
                <option value="rear">后方长桌</option>
                <option value="right">右侧外围</option>
                <option value="left">左侧外围</option>
              </select>
              <button type="button" class="btn sm" @click="addRow">＋新增排</button>
            </div>

            <div class="sub-box">
              <div class="sub-box-title">
                <span>花盆管理（图中直接拖动调整位置）</span>
                <button type="button" class="btn xxs" @click="resetPlantsOnly">复位花盆</button>
              </div>
              <div class="plants-grid">
                <div v-for="p in layout.plants" :key="p.id" class="plant-chip">
                  <span>{{ p.label }}</span>
                  <button type="button" class="btn xxs" :class="{ warn: p.hidden }" @click="togglePlantHidden(p.id)">
                    {{ p.hidden ? '显示' : '隐藏' }}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <!-- Tab 3: 座位姓名编辑 -->
          <section v-show="isTabVisible('seat')" class="panel-section">
            <h3>03 · 座位编辑</h3>
            <div class="selected-banner">
              <template v-if="activeSeatInfo">
                <strong>{{ activeSeatInfo.rowLabel }} · {{ activeSeatInfo.code }}</strong>
                <span v-if="swapSource" class="swap-hint">（请点击目标座位完成互换）</span>
                <span v-else-if="activeSeatInfo.hidden" class="hidden-hint">（该座位当前已隐藏）</span>
              </template>
              <template v-else>点击右侧平面图中的任意座位开始录入</template>
            </div>

            <div class="flex-row">
              <input
                ref="personInputRef"
                v-model="personDraft"
                class="grow"
                maxlength="40"
                placeholder="输入姓名，Enter 保存并跳下一座"
                :disabled="!activeSeatInfo"
                @keydown="onPersonKeydown"
              />
              <button type="button" class="btn sm primary" :disabled="!activeSeatInfo" @click="applySeatName(false)">
                确认
              </button>
            </div>

            <div class="flex-row" style="margin-top: 8px">
              <button type="button" class="btn sm grow" :disabled="!canStepPrev" @click="applyAndStep(-1)">上一座</button>
              <button type="button" class="btn sm grow" :disabled="!canStepNext" @click="applyAndStep(1)">下一座</button>
              <button type="button" class="btn sm" :disabled="!activeSeatInfo" @click="clearCurrentSeat">清空</button>
            </div>

            <div class="flex-row" style="margin-top: 8px">
              <button type="button" class="btn sm grow" :disabled="!activeSeatInfo" @click="toggleSwapMode">
                {{ swapSource ? '取消互换' : '与另一座互换' }}
              </button>
              <button
                type="button"
                class="btn sm"
                :disabled="!activeSeatInfo"
                @click="toggleSelectedSeatHidden"
              >
                {{ activeSeatInfo?.ownHidden ? '恢复此座' : '隐藏此座' }}
              </button>
            </div>
            <div class="flex-row" style="margin-top: 8px">
              <button type="button" class="btn sm warn grow" @click="initSeatingOnly">初始化排座（清空名单）</button>
            </div>
            <p class="hint">桌面端可直接拖动两个座位互换人员（含空座）；拖动花盆可调整花盆位置。</p>
          </section>

          <!-- Tab 4: 批量排座、搜索与参考 -->
          <section v-show="isTabVisible('bulk')" class="panel-section">
            <h3>04 · 批量排座与查找</h3>
            <textarea
              v-model="bulkText"
              rows="4"
              placeholder="粘贴名单，每行一人；也支持逗号、顿号、Tab 分隔"
            ></textarea>
            <select v-model="bulkScope" style="margin-top: 6px" aria-label="批量填充范围">
              <option value="all">全场可见空位（按排列表顺序）</option>
              <option v-for="r in layout.rows" :key="r.id" :value="r.id">
                {{ r.id }} {{ r.label }} 可见空位
              </option>
            </select>
            <div class="flex-row" style="margin-top: 6px">
              <button type="button" class="btn sm primary grow" @click="bulkFillNames">依次填入空座</button>
              <button type="button" class="btn sm danger-outline" @click="initSeatingOnly">初始化排座</button>
            </div>

            <div class="sub-box">
              <label class="field-label" for="seat-search">搜索姓名或座位编号</label>
              <input id="seat-search" v-model="searchQuery" placeholder="输入姓名或如 A-01" />
              <div v-if="searchQuery.trim()" class="search-results">
                <div v-if="!searchMatches.length" class="hint">未找到匹配座位</div>
                <button
                  v-for="m in searchMatches"
                  :key="`${m.rowId}-${m.seatIdx}`"
                  type="button"
                  class="found-btn"
                  @click="locateSeat(m)"
                >
                  {{ m.name || '空座' }} · {{ m.rowLabel }} {{ m.code }}
                </button>
              </div>
            </div>

            <div class="flex-row" style="margin-top: 10px">
              <button type="button" class="btn sm warn grow" @click="openResetLayoutModal">
                初始化布局
              </button>
              <button type="button" class="btn sm danger-outline grow" @click="resetToInitial">
                全部初始化（布局+排座）
              </button>
            </div>

            <details class="photo-details">
              <summary>查看会场实景参考照片</summary>
              <div class="photos-grid">
                <a :href="roomPhoto1" target="_blank" rel="noopener">
                  <img :src="roomPhoto1" alt="会场角度一" />
                </a>
                <a :href="roomPhoto2" target="_blank" rel="noopener">
                  <img :src="roomPhoto2" alt="会场角度二" />
                </a>
              </div>
              <p class="hint">默认 3 桌拼接回字布局与花盆点位已结合实景及门窗方向校准。</p>
            </details>
          </section>
        </aside>

        <!-- 右侧/上方主平面图画布区 -->
        <main class="stage card">
          <div class="stagebar noprint">
            <div class="stats">
              <div class="stat"><b>{{ stats.totalSeats }}</b><span>总座位</span></div>
              <div class="stat"><b>{{ stats.assignedSeats }}</b><span>已安排</span></div>
              <div class="stat"><b>{{ stats.emptySeats }}</b><span>空座</span></div>
              <div v-if="stats.hiddenCount > 0" class="stat muted-stat">
                <b>{{ stats.hiddenCount }}</b><span>已隐藏</span>
              </div>
            </div>

            <div class="stage-controls">
              <label class="checkline">
                <input
                  type="checkbox"
                  :checked="layout.flip"
                  @change="mutateLayout((d) => { d.flip = $event.target.checked })"
                />
                左右镜像
              </label>
              <label class="checkline">
                <input
                  type="checkbox"
                  :checked="layout.showHiddenPreview"
                  @change="mutateLayout((d) => { d.showHiddenPreview = $event.target.checked })"
                />
                显示隐藏项
              </label>

              <div class="zoom-group">
                <button type="button" class="btn xs" @click="setZoom(zoom - 0.15)">－</button>
                <button type="button" class="btn xs" @click="setZoom(1)">适应</button>
                <button type="button" class="btn xs" @click="setZoom(zoom + 0.15)">＋</button>
              </div>
            </div>
          </div>

          <div ref="stageBodyRef" class="stagebody">
            <div
              class="print-sheet"
              :class="{ mono: layout.mono, 'is-portrait': layout.paper === 'portrait' }"
              :style="sheetStyle"
            >
              <div class="sheethead">
                <h2>{{ layout.meeting || '会议座位安排图' }}</h2>
                <div v-if="layout.subtitle" class="sheetsub">{{ layout.subtitle }}</div>
              </div>

              <div class="mapwrap">
                <SeatingCanvas
                  :layout="layout"
                  :selected-seat="selectedSeat"
                  :is-printing="isPrinting"
                  @select-seat="onSelectSeat"
                  @swap-seats="onSwapSeats"
                  @move-plant="onMovePlant"
                  @commit-plant-move="commitPendingPlantMove"
                />
              </div>

              <div class="legend">
                <span><i class="swatch assignedsw"></i>已安排</span>
                <span><i class="swatch"></i>空座</span>
                <span class="selectedlegend"><i class="swatch selectedsw"></i>当前选中</span>
              </div>

              <div class="sheetfoot">
                <span>{{ footerCountText }}</span>
                <span>显示屏方向为会场正前方 · 右上双开外开出入口</span>
              </div>
            </div>
          </div>

          <!-- 手机窄屏选中座位快捷录入条 -->
          <div v-if="activeSeatInfo" class="mobile-quick-bar noprint">
            <div class="mq-top">
              <strong>{{ activeSeatInfo.rowLabel }} · {{ activeSeatInfo.code }}</strong>
              <button type="button" class="btn xxs" @click="toggleSelectedSeatHidden">
                {{ activeSeatInfo.ownHidden ? '恢复此座' : '隐藏此座' }}
              </button>
            </div>
            <div class="mq-row">
              <input
                v-model="personDraft"
                class="grow"
                maxlength="40"
                placeholder="输入姓名"
                @keydown="onPersonKeydown"
              />
              <button type="button" class="btn sm primary" @click="applyAndStep(1)">保存并下一座</button>
            </div>
          </div>

          <div class="notice noprint" aria-live="polite">{{ noticeText }}</div>
        </main>
      </div>
    </div>

    <!-- 新建 / 重命名存档弹窗 -->
    <div v-if="profileModal.open" class="modal-backdrop noprint" @click.self="profileModal.open = false">
      <div class="modal-card">
        <h4>{{ profileModal.mode === 'create' ? '新建布局存档' : '重命名存档' }}</h4>
        <label class="field-label" for="modal-profile-name">存档名称</label>
        <input
          id="modal-profile-name"
          v-model="profileModal.name"
          maxlength="60"
          placeholder="例如：集团季度调度会方案"
          @keydown.enter.prevent="submitProfileModal"
        />
        <div v-if="profileModal.mode === 'create'" style="margin-top: 10px">
          <label class="field-label">初始化方式</label>
          <div class="flex-row">
            <label class="checkline">
              <input v-model="profileModal.source" type="radio" value="current" />
              基于当前布局另存
            </label>
            <label class="checkline">
              <input v-model="profileModal.source" type="radio" value="default" />
              新建默认布局
            </label>
          </div>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn sm" @click="profileModal.open = false">取消</button>
          <button type="button" class="btn sm primary" :disabled="profileBusy" @click="submitProfileModal">
            确定
          </button>
        </div>
      </div>
    </div>

    <!-- 排名称重命名弹窗 -->
    <div v-if="rowRenameModal.open" class="modal-backdrop noprint" @click.self="rowRenameModal.open = false">
      <div class="modal-card">
        <h4>修改排名称</h4>
        <label class="field-label" for="modal-row-name">排名称</label>
        <input
          id="modal-row-name"
          v-model="rowRenameModal.label"
          maxlength="32"
          @keydown.enter.prevent="submitRowRenameModal"
        />
        <div class="modal-actions">
          <button type="button" class="btn sm" @click="rowRenameModal.open = false">取消</button>
          <button type="button" class="btn sm primary" @click="submitRowRenameModal">保存</button>
        </div>
      </div>
    </div>

    <!-- 初始化布局弹窗 -->
    <div v-if="resetLayoutModal.open" class="modal-backdrop noprint" @click.self="resetLayoutModal.open = false">
      <div class="modal-card">
        <h4>初始化会场布局</h4>
        <p class="hint" style="margin-bottom: 10px">
          将恢复默认桌椅配置（屏幕席 6 席、主席席 7 席，右侧/后排各 8 席）、4 盆花盆位置、门窗设置并取消隐藏；支持随时「撤销」。
        </p>
        <div class="checks-stack">
          <label class="checkline">
            <input v-model="resetLayoutModal.preserveNames" type="radio" :value="true" />
            仅初始化布局（按排尽量保留已排姓名）
          </label>
          <label class="checkline">
            <input v-model="resetLayoutModal.preserveNames" type="radio" :value="false" />
            全部初始化（恢复默认布局并清空所有座位姓名）
          </label>
        </div>
        <div class="modal-actions">
          <button type="button" class="btn sm" @click="resetLayoutModal.open = false">取消</button>
          <button type="button" class="btn sm primary" @click="submitResetLayoutModal">确认初始化</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import SeatingCanvas from '../components/SeatingCanvas.vue'
import roomPhoto1 from '../assets/room_angle_1.jpg'
import roomPhoto2 from '../assets/room_angle_2.jpg'
import {
  activateSeatingProfile,
  createSeatingProfile,
  deleteSeatingProfile,
  fetchSeatingProfile,
  fetchSeatingProfiles,
  renameSeatingProfile,
  updateSeatingProfile,
} from '../services/api'
import {
  buildDefaultLayout,
  buildSeatCatalog,
  cloneLayout,
  defaultPlants,
  makeRow,
  normalizeEmptySeatDisplay,
  normalizeOrMigrateLayout,
  resetRoomLayout,
  resetSeatingNames,
} from '../utils/seatingLayout'

const router = useRouter()

const breadcrumbItems = [
  { label: '项目选择', to: '/projects' },
  { label: '会议排座助手', to: null },
]

const panelTabs = [
  { key: 'layout', label: '座位布局' },
  { key: 'seat', label: '座位编辑' },
  { key: 'bulk', label: '批量/查找' },
  { key: 'info', label: '资料/会场' },
]

const FIXED_ZONES = new Set(['front', 'innerLeft', 'innerRight', 'innerRear'])

const layout = ref(buildDefaultLayout())
const profiles = ref([])
const activeProfileId = ref('')
const profileBusy = ref(false)
const saveState = ref('saved')
const saveError = ref('')

const activeTab = ref('seat')
const isNarrowViewport = ref(typeof window !== 'undefined' ? window.innerWidth <= 960 : false)
const newRowZone = ref('rear')
const isPrinting = ref(false)

const selectedSeat = ref(null) // { rowId, seatIdx }
const swapSource = ref(null)
const personDraft = ref('')
const bulkText = ref('')
const bulkScope = ref('all')
const searchQuery = ref('')
const zoom = ref(1)
const noticeText = ref('点击任意座位录入姓名；拖动座位可交换人员，拖动花盆可调整位置。')

const history = ref([])
const future = ref([])
const pendingPlantSnapshot = ref(null)

const personInputRef = ref(null)
const importInputRef = ref(null)
const stageBodyRef = ref(null)

const profileModal = ref({
  open: false,
  mode: 'create',
  name: '',
  source: 'current',
})

const rowRenameModal = ref({
  open: false,
  rowId: '',
  label: '',
})

const resetLayoutModal = ref({
  open: false,
  preserveNames: true,
})

let autoSaveTimer = null
let dynamicPageStyleEl = null

function clampInt(val, min, max) {
  const n = Math.floor(Number(val))
  if (!Number.isFinite(n)) return min
  return Math.max(min, Math.min(max, n))
}

function isFixedZone(zone) {
  return FIXED_ZONES.has(zone)
}

function isTabVisible(key) {
  if (!isNarrowViewport.value) return true
  return activeTab.value === key
}

function goProjects() {
  router.push('/projects')
}

function updatePagePrintStyle() {
  if (typeof document === 'undefined') return
  if (!dynamicPageStyleEl) {
    dynamicPageStyleEl = document.createElement('style')
    dynamicPageStyleEl.setAttribute('data-meeting-seating-page', '1')
    document.head.appendChild(dynamicPageStyleEl)
  }
  const dir = layout.value.paper === 'landscape' ? 'landscape' : 'portrait'
  const printHeight = dir === 'landscape' ? '188mm' : '276mm'
  dynamicPageStyleEl.textContent = `
    @page { size: A4 ${dir}; margin: 6mm; }
    @media print {
      html, body {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        height: ${printHeight} !important;
        max-height: ${printHeight} !important;
        min-height: 0 !important;
        background: #ffffff !important;
        overflow: hidden !important;
      }
      body > *:not(#app),
      #app > *:not(.seating-app) {
        display: none !important;
      }
      #app {
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        height: ${printHeight} !important;
        max-height: ${printHeight} !important;
        min-height: 0 !important;
        background: #ffffff !important;
        overflow: hidden !important;
      }
    }
  `
  document.documentElement.style.setProperty('--seating-print-height', printHeight)
}

watch(
  () => layout.value.paper,
  () => {
    updatePagePrintStyle()
  },
  { immediate: true },
)

const saveStateClass = computed(() => `state-${saveState.value}`)
const saveStateText = computed(() => {
  if (saveState.value === 'saving') return '正在写入配置文件…'
  if (saveState.value === 'dirty') return '有未保存更改'
  if (saveState.value === 'error') return `保存失败：${saveError.value || '请重试'}`
  return '已同步至配置文件'
})

const sheetStyle = computed(() => {
  if (isPrinting.value || zoom.value === 1) return {}
  const baseW = layout.value.paper === 'portrait' ? 1020 : 1280
  const scaledW = Math.round(baseW * zoom.value)
  if (zoom.value < 1) {
    return {
      width: '100%',
      maxWidth: `${scaledW}px`,
    }
  }
  return {
    width: `${scaledW}px`,
    maxWidth: 'none',
  }
})

const visibleCatalog = computed(() => buildSeatCatalog(layout.value.rows, false))
const fullCatalog = computed(() => buildSeatCatalog(layout.value.rows, true))

const stats = computed(() => {
  const list = visibleCatalog.value.list
  const assignedSeats = list.filter((s) => s.name.trim()).length
  const hiddenCount = (layout.value.rows || []).reduce(
    (acc, r) => acc + (r.hidden ? r.seats.length : r.seats.filter((s) => s.hidden).length),
    0,
  )
  return {
    totalSeats: list.length,
    assignedSeats,
    emptySeats: list.length - assignedSeats,
    hiddenCount,
  }
})

const footerCountText = computed(() => {
  const d = visibleCatalog.value.dupCounts
  const dupCount = Object.keys(d).filter((k) => d[k] > 1).length
  return `总计 ${stats.value.totalSeats} 席 · 已安排 ${stats.value.assignedSeats} 席 · 空座 ${stats.value.emptySeats} 席${
    dupCount ? ` · ${dupCount} 个重名` : ''
  }`
})

const activeSeatInfo = computed(() => {
  if (!selectedSeat.value) return null
  return (
    fullCatalog.value.list.find(
      (s) => s.rowId === selectedSeat.value.rowId && s.seatIdx === selectedSeat.value.seatIdx,
    ) || null
  )
})

watch(activeSeatInfo, (info) => {
  personDraft.value = info ? info.name : ''
})

const stepList = computed(() => visibleCatalog.value.list)
const activeStepIdx = computed(() => {
  if (!selectedSeat.value) return -1
  return stepList.value.findIndex(
    (s) => s.rowId === selectedSeat.value.rowId && s.seatIdx === selectedSeat.value.seatIdx,
  )
})
const canStepPrev = computed(() => activeStepIdx.value > 0)
const canStepNext = computed(() => activeStepIdx.value >= 0 && activeStepIdx.value < stepList.value.length - 1)

const searchMatches = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return []
  return fullCatalog.value.list.filter(
    (s) => s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q),
  )
})

function pushHistory(snapshot) {
  history.value.push(snapshot)
  if (history.value.length > 80) history.value.shift()
  future.value = []
}

function scheduleAutoSave() {
  saveState.value = 'dirty'
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    saveCurrentProfile(false)
  }, 900)
}

function mutateLayout(mutator) {
  const prev = cloneLayout(layout.value)
  mutator(layout.value)
  if (JSON.stringify(prev) === JSON.stringify(layout.value)) return
  pushHistory(prev)
  scheduleAutoSave()
}

function undo() {
  if (!history.value.length) return
  future.value.push(cloneLayout(layout.value))
  layout.value = history.value.pop()
  swapSource.value = null
  noticeText.value = '已撤销上一步操作'
  scheduleAutoSave()
}

function redo() {
  if (!future.value.length) return
  history.value.push(cloneLayout(layout.value))
  layout.value = future.value.pop()
  swapSource.value = null
  noticeText.value = '已重做'
  scheduleAutoSave()
}

async function loadProfiles() {
  profileBusy.value = true
  try {
    const res = await fetchSeatingProfiles()
    profiles.value = Array.isArray(res?.profiles) ? res.profiles : []
    activeProfileId.value = res?.active_id || profiles.value[0]?.id || ''
    if (res?.active_profile?.layout) {
      layout.value = normalizeOrMigrateLayout(res.active_profile.layout)
    }
    history.value = []
    future.value = []
    saveState.value = 'saved'
  } catch (err) {
    saveState.value = 'error'
    saveError.value = err instanceof Error ? err.message : '加载存档失败'
    noticeText.value = `加载后端存档失败：${saveError.value}`
  } finally {
    profileBusy.value = false
  }
}

async function saveCurrentProfile(showTip = false) {
  if (!activeProfileId.value) return
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
    autoSaveTimer = null
  }
  saveState.value = 'saving'
  saveError.value = ''
  try {
    const res = await updateSeatingProfile(activeProfileId.value, {
      layout: layout.value,
    })
    if (Array.isArray(res?.profiles)) {
      profiles.value = res.profiles
    }
    saveState.value = 'saved'
    if (showTip) {
      noticeText.value = '已保存当前布局至配置文件'
    }
  } catch (err) {
    saveState.value = 'error'
    saveError.value = err instanceof Error ? err.message : '保存失败'
  }
}

async function onSwitchProfile(targetId) {
  if (!targetId || targetId === activeProfileId.value) return
  if (saveState.value === 'dirty') {
    await saveCurrentProfile(false)
  }
  profileBusy.value = true
  try {
    await activateSeatingProfile(targetId)
    const detail = await fetchSeatingProfile(targetId)
    activeProfileId.value = targetId
    if (detail?.profile?.layout) {
      layout.value = normalizeOrMigrateLayout(detail.profile.layout)
    }
    selectedSeat.value = null
    swapSource.value = null
    history.value = []
    future.value = []
    saveState.value = 'saved'
    noticeText.value = `已切换至存档「${detail?.profile?.name || ''}」`
  } catch (err) {
    noticeText.value = `切换存档失败：${err instanceof Error ? err.message : String(err)}`
  } finally {
    profileBusy.value = false
  }
}

function openProfileModal(modalMode) {
  const currentMeta = profiles.value.find((p) => p.id === activeProfileId.value)
  profileModal.value = {
    open: true,
    mode: modalMode,
    name: modalMode === 'rename' ? currentMeta?.name || '' : '',
    source: 'current',
  }
}

async function submitProfileModal() {
  const name = profileModal.value.name.trim()
  if (!name) {
    noticeText.value = '请输入存档名称'
    return
  }
  profileBusy.value = true
  try {
    if (profileModal.value.mode === 'create') {
      if (saveState.value === 'dirty') {
        await saveCurrentProfile(false)
      }
      const initialLayout =
        profileModal.value.source === 'default' ? buildDefaultLayout() : cloneLayout(layout.value)
      const res = await createSeatingProfile({
        name,
        layout: initialLayout,
        activate: true,
      })
      profiles.value = res.profiles || []
      activeProfileId.value = res.active_id
      layout.value = normalizeOrMigrateLayout(res.profile.layout)
      history.value = []
      future.value = []
      saveState.value = 'saved'
      noticeText.value = `已新建并切换至存档「${name}」`
    } else if (activeProfileId.value) {
      const res = await renameSeatingProfile(activeProfileId.value, name)
      profiles.value = res.profiles || []
      noticeText.value = `存档已重命名为「${name}」`
    }
    profileModal.value.open = false
  } catch (err) {
    noticeText.value = `操作失败：${err instanceof Error ? err.message : String(err)}`
  } finally {
    profileBusy.value = false
  }
}

async function handleDeleteProfile() {
  if (profiles.value.length <= 1 || !activeProfileId.value) return
  const currentMeta = profiles.value.find((p) => p.id === activeProfileId.value)
  if (!window.confirm(`确认删除存档「${currentMeta?.name || ''}」？此操作不可撤销。`)) return
  profileBusy.value = true
  try {
    const res = await deleteSeatingProfile(activeProfileId.value)
    profiles.value = res.profiles || []
    activeProfileId.value = res.active_id
    if (res.active_profile?.layout) {
      layout.value = normalizeOrMigrateLayout(res.active_profile.layout)
    }
    selectedSeat.value = null
    history.value = []
    future.value = []
    saveState.value = 'saved'
    noticeText.value = '已删除存档'
  } catch (err) {
    noticeText.value = `删除失败：${err instanceof Error ? err.message : String(err)}`
  } finally {
    profileBusy.value = false
  }
}

function resizeRow(rowId, rawCount) {
  const row = layout.value.rows.find((r) => r.id === rowId)
  if (!row) return
  const n = clampInt(rawCount, 0, 24)
  if (
    n < row.seats.length &&
    row.seats.slice(n).some((s) => s.name.trim()) &&
    !window.confirm(`减少座位将清除末尾 ${row.seats.length - n} 个座位及其中姓名，继续？`)
  ) {
    return
  }
  mutateLayout((d) => {
    const target = d.rows.find((r) => r.id === rowId)
    if (!target) return
    while (target.seats.length < n) {
      target.seats.push({ id: `${target.id}-${target.seats.length + 1}`, name: '', hidden: false })
    }
    if (target.seats.length > n) {
      target.seats.length = n
    }
  })
}

function openRowRenameModal(row) {
  rowRenameModal.value = {
    open: true,
    rowId: row.id,
    label: row.label,
  }
}

function submitRowRenameModal() {
  const next = rowRenameModal.value.label.trim().slice(0, 32)
  if (!next) return
  const rid = rowRenameModal.value.rowId
  mutateLayout((d) => {
    const target = d.rows.find((r) => r.id === rid)
    if (target) target.label = next
  })
  rowRenameModal.value.open = false
}

function toggleRowHidden(rowId) {
  mutateLayout((d) => {
    const target = d.rows.find((r) => r.id === rowId)
    if (target) target.hidden = !target.hidden
  })
}

function addRow() {
  if (layout.value.rows.length >= 30) {
    noticeText.value = '最多支持 30 排'
    return
  }
  const zone = newRowZone.value
  const labels = { rear: '后方', right: '右侧外围', left: '左侧外围' }
  const num = layout.value.rows.filter((r) => r.zone === zone).length + 1
  mutateLayout((d) => {
    let id
    do {
      id = `R${d.seq++}`
    } while (d.rows.some((r) => r.id === id))
    d.rows.push(makeRow(id, `${labels[zone] || '自定义'}第${num}排`, zone, zone === 'rear' ? 8 : 6))
  })
}

function deleteRow(row) {
  if (isFixedZone(row.zone)) return
  if (!window.confirm(`删除「${row.label}」及其全部座位？`)) return
  mutateLayout((d) => {
    d.rows = d.rows.filter((r) => r.id !== row.id)
  })
  if (selectedSeat.value?.rowId === row.id) selectedSeat.value = null
}

function onMovePlant(move) {
  if (!pendingPlantSnapshot.value) {
    pendingPlantSnapshot.value = cloneLayout(layout.value)
  }
  const p = layout.value.plants.find((item) => item.id === move.id)
  if (p) {
    p.x = move.x
    p.y = move.y
  }
}

function commitPendingPlantMove() {
  if (!pendingPlantSnapshot.value) return
  const prev = pendingPlantSnapshot.value
  pendingPlantSnapshot.value = null
  if (JSON.stringify(prev) !== JSON.stringify(layout.value)) {
    pushHistory(prev)
    scheduleAutoSave()
  }
}

function togglePlantHidden(plantId) {
  mutateLayout((d) => {
    const p = d.plants.find((item) => item.id === plantId)
    if (p) p.hidden = !p.hidden
  })
}

function resetPlantsOnly() {
  mutateLayout((d) => {
    d.plants = defaultPlants()
  })
  noticeText.value = '已复位花盆默认位置'
}

function onSelectSeat(seatPos) {
  if (swapSource.value) {
    if (swapSource.value.rowId === seatPos.rowId && swapSource.value.seatIdx === seatPos.seatIdx) {
      swapSource.value = null
      return
    }
    onSwapSeats(swapSource.value, seatPos)
    swapSource.value = null
    return
  }
  selectedSeat.value = { rowId: seatPos.rowId, seatIdx: seatPos.seatIdx }
  personInputRef.value?.focus?.({ preventScroll: true })
}

function onSwapSeats(from, to) {
  if (!from || !to) return
  if (from.rowId === to.rowId && from.seatIdx === to.seatIdx) return
  const rFrom = layout.value.rows.find((r) => r.id === from.rowId)
  const rTo = layout.value.rows.find((r) => r.id === to.rowId)
  if (!rFrom?.seats?.[from.seatIdx] || !rTo?.seats?.[to.seatIdx]) return

  mutateLayout((d) => {
    const a = d.rows.find((r) => r.id === from.rowId).seats[from.seatIdx]
    const b = d.rows.find((r) => r.id === to.rowId).seats[to.seatIdx]
    const tmp = a.name
    a.name = b.name
    b.name = tmp
  })
  selectedSeat.value = { rowId: to.rowId, seatIdx: to.seatIdx }
  noticeText.value = '已完成座位人员互换'
}

function applySeatName(goNext = false) {
  if (!selectedSeat.value) return
  const { rowId, seatIdx } = selectedSeat.value
  const val = personDraft.value.trim()
  mutateLayout((d) => {
    const row = d.rows.find((r) => r.id === rowId)
    if (row?.seats?.[seatIdx]) {
      row.seats[seatIdx].name = val
    }
  })
  noticeText.value = `已保存 ${activeSeatInfo.value?.code || ''}${val ? `：${val}` : '（空座）'}`
  if (goNext) stepSeat(1)
}

function stepSeat(delta) {
  const list = stepList.value
  const idx = activeStepIdx.value
  const target = list[idx + delta]
  if (target) {
    selectedSeat.value = { rowId: target.rowId, seatIdx: target.seatIdx }
    personInputRef.value?.focus?.({ preventScroll: true })
  }
}

function applyAndStep(delta) {
  applySeatName(false)
  stepSeat(delta)
}

function onPersonKeydown(e) {
  if (e.key === 'Enter' && !e.isComposing) {
    e.preventDefault()
    applySeatName(true)
  }
}

function clearCurrentSeat() {
  if (!selectedSeat.value) return
  personDraft.value = ''
  applySeatName(false)
}

function toggleSwapMode() {
  if (!selectedSeat.value) return
  if (swapSource.value) {
    swapSource.value = null
    noticeText.value = '已取消互换'
  } else {
    swapSource.value = { ...selectedSeat.value }
    noticeText.value = '请点击目标座位完成人员互换'
  }
}

function toggleSelectedSeatHidden() {
  if (!selectedSeat.value) return
  const { rowId, seatIdx } = selectedSeat.value
  mutateLayout((d) => {
    const row = d.rows.find((r) => r.id === rowId)
    if (row?.seats?.[seatIdx]) {
      row.seats[seatIdx].hidden = !row.seats[seatIdx].hidden
    }
  })
  noticeText.value = '已切换该座位显隐状态'
}

function bulkFillNames() {
  const names = bulkText.value
    .split(/[\n\r\t,，、;；]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (!names.length) {
    noticeText.value = '请先输入人员名单'
    return
  }
  const targets = visibleCatalog.value.list.filter(
    (s) => !s.name.trim() && (bulkScope.value === 'all' || s.rowId === bulkScope.value),
  )
  const fillCount = Math.min(names.length, targets.length)
  mutateLayout((d) => {
    for (let i = 0; i < fillCount; i += 1) {
      const target = targets[i]
      const row = d.rows.find((r) => r.id === target.rowId)
      if (row?.seats?.[target.seatIdx]) {
        row.seats[target.seatIdx].name = names[i].slice(0, 40)
      }
    }
  })
  bulkText.value = names.slice(fillCount).join('\n')
  noticeText.value = `已批量安排 ${fillCount} 人${names.length > fillCount ? `，剩余 ${names.length - fillCount} 人待安排` : ''}`
}

function initSeatingOnly() {
  if (!window.confirm('确认初始化排座？将清空所有座位姓名，并保留当前各边座位数、显隐与花盆布局。')) return
  const next = resetSeatingNames(layout.value)
  mutateLayout((d) => {
    Object.assign(d, next)
  })
  personDraft.value = ''
  swapSource.value = null
  noticeText.value = '已初始化排座（姓名已清空，布局已保留，可撤销）'
}

function openResetLayoutModal() {
  resetLayoutModal.value = {
    open: true,
    preserveNames: true,
  }
}

function submitResetLayoutModal() {
  const preserve = Boolean(resetLayoutModal.value.preserveNames)
  const next = resetRoomLayout(layout.value, { preserveNames: preserve })
  mutateLayout((d) => {
    Object.assign(d, next)
  })
  selectedSeat.value = null
  swapSource.value = null
  if (!preserve) personDraft.value = ''
  resetLayoutModal.value.open = false
  noticeText.value = preserve
    ? '已初始化默认布局，并保留了已排姓名（可撤销）'
    : '已完成全部初始化（恢复默认布局并清空排座，可撤销）'
}

function resetToInitial() {
  if (!window.confirm('确认全部初始化为默认布局并清空已填名单？')) return
  const fresh = resetRoomLayout(layout.value, { preserveNames: false, clearMeta: true })
  mutateLayout((d) => {
    Object.assign(d, fresh)
  })
  selectedSeat.value = null
  swapSource.value = null
  personDraft.value = ''
  noticeText.value = '已全部初始化为默认布局'
}

function locateSeat(item) {
  selectedSeat.value = { rowId: item.rowId, seatIdx: item.seatIdx }
  const el = stageBodyRef.value?.querySelector?.(
    `[data-row-id="${CSS.escape(item.rowId)}"][data-seat-idx="${item.seatIdx}"]`,
  )
  el?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' })
}

function setZoom(next) {
  zoom.value = Math.max(0.7, Math.min(2.4, Number(next.toFixed(2))))
}

function downloadFile(name, content, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function safeFileBase() {
  return (layout.value.meeting || '会议排座').replace(/[\\/:*?"<>|]/g, '_')
}

function exportJson() {
  downloadFile(`${safeFileBase()}.json`, JSON.stringify(layout.value, null, 2), 'application/json;charset=utf-8')
}

function triggerImport() {
  importInputRef.value?.click?.()
}

function onImportFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const parsed = normalizeOrMigrateLayout(JSON.parse(String(reader.result || '{}')))
      if (window.confirm('导入方案将替换当前存档中的布局及名单，继续？')) {
        mutateLayout((d) => {
          Object.assign(d, parsed)
        })
        selectedSeat.value = null
        swapSource.value = null
        noticeText.value = '方案已导入'
      }
    } catch (err) {
      noticeText.value = `导入失败：${err instanceof Error ? err.message : String(err)}`
    }
  }
  reader.readAsText(file, 'utf-8')
}

function exportCsv() {
  const lines = [['排名称', '座位编号', '姓名']]
  visibleCatalog.value.list.forEach((s) => {
    lines.push([s.rowLabel, s.code, s.name])
  })
  const cell = (v) => {
    let s = String(v || '')
    if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`
    return `"${s.replace(/"/g, '""')}"`
  }
  downloadFile(
    `${safeFileBase()}_名单.csv`,
    `\ufeff${lines.map((row) => row.map(cell).join(',')).join('\r\n')}`,
    'text/csv;charset=utf-8',
  )
}

async function handlePrint() {
  updatePagePrintStyle()
  isPrinting.value = true
  await nextTick()
  const cleanup = () => {
    isPrinting.value = false
    window.removeEventListener('afterprint', cleanup)
  }
  window.addEventListener('afterprint', cleanup)
  requestAnimationFrame(() => {
    window.print()
    setTimeout(cleanup, 500)
  })
}

function onWindowResize() {
  isNarrowViewport.value = window.innerWidth <= 960
}

function onGlobalKeydown(e) {
  const tag = document.activeElement?.tagName
  if ((e.ctrlKey || e.metaKey) && !['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) {
    const k = e.key.toLowerCase()
    if (k === 'z') {
      e.preventDefault()
      if (e.shiftKey) redo()
      else undo()
    } else if (k === 'y') {
      e.preventDefault()
      redo()
    }
  }
}

onMounted(() => {
  loadProfiles()
  window.addEventListener('resize', onWindowResize)
  window.addEventListener('keydown', onGlobalKeydown)
})

onBeforeUnmount(() => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  if (dynamicPageStyleEl && dynamicPageStyleEl.parentNode) {
    dynamicPageStyleEl.parentNode.removeChild(dynamicPageStyleEl)
  }
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<style scoped>
.seating-app {
  min-height: 100vh;
  background: #f2f5f2;
  color: #20342e;
}

.seating-app,
.seating-app *,
.seating-app *::before,
.seating-app *::after {
  box-sizing: border-box;
}

.seating-shell {
  max-width: 1920px;
  margin: 0 auto;
  padding: 12px 16px 24px;
}

.top-toolbar {
  margin-bottom: 14px;
  padding: 14px 16px;
  border: 1px solid #dce4df;
  border-radius: 12px;
  background: #ffffff;
}

.toolbar-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.title-row h2 {
  margin: 0;
  font-size: 20px;
  color: #153b30;
}

.admin-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e1eee5;
  color: #1d5744;
  font-weight: 600;
}

.save-badge {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #edf5ef;
  color: #22644f;
}

.save-badge.state-dirty,
.save-badge.state-saving {
  background: #fff4d9;
  color: #8a5b24;
}

.save-badge.state-error {
  background: #fee2e2;
  color: #991b1b;
}

.sub {
  margin: 4px 0 0;
  font-size: 12.5px;
  color: #607268;
}

.toolbar-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.hidden-file {
  display: none;
}

.profile-bar {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e6ede8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.profile-select-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1 1 260px;
  min-width: 0;
}

.profile-label {
  font-size: 13px;
  font-weight: 600;
  color: #324b41;
  white-space: nowrap;
}

.profile-select {
  flex: 1;
  min-width: 0;
  max-width: 360px;
}

.profile-btn-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.mobile-tabs {
  display: none;
}

.panel {
  background: #ffffff;
  border: 1px solid #dce4df;
  border-radius: 12px;
  padding: 14px;
}

.panel-section {
  padding: 12px 0;
  border-top: 1px solid #e6ede8;
}

.panel-section:first-child {
  border-top: 0;
  padding-top: 0;
}

.panel-section h3 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #153b30;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.section-head h3 {
  margin: 0;
}

.field-label {
  display: block;
  font-size: 12px;
  color: #607268;
  margin: 8px 0 4px;
}

.hint {
  font-size: 12px;
  color: #687970;
  margin: 4px 0 0;
  line-height: 1.45;
}

input:not([type='checkbox']):not([type='radio']),
select,
textarea {
  width: 100%;
  min-width: 0 !important;
  max-width: 100%;
  padding: 6px 9px;
  border: 1px solid #ccd8d0;
  border-radius: 7px;
  background: #fff;
  color: #20342e;
  font: inherit;
  font-size: 13px;
  line-height: 1.3;
  box-sizing: border-box;
}

input:not([type='checkbox']):not([type='radio']),
select {
  height: 32px;
}

textarea {
  resize: vertical;
  min-height: 82px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  border: 1px solid #ccd8d0;
  border-radius: 7px;
  height: 34px;
  padding: 0 11px;
  background: #fff;
  color: #20342e;
  font: inherit;
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
  box-sizing: border-box;
}

.btn:hover:not(:disabled) {
  background: #e9f1ec;
}

.btn:disabled {
  opacity: 0.45;
  cursor: default;
}

.btn.sm {
  height: 32px;
  padding: 0 10px;
  font-size: 12.5px;
}

.btn.xs {
  height: 28px;
  padding: 0 9px;
  font-size: 12px;
}

.btn.xxs {
  height: 24px;
  padding: 0 7px;
  font-size: 11px;
  border-radius: 5px;
}

.btn.primary {
  background: #22644f;
  border-color: #22644f;
  color: #fff;
}

.btn.primary:hover:not(:disabled) {
  background: #1a503f;
}

.btn.danger-outline {
  color: #a43e36;
  border-color: #e4c1bd;
}

.btn.warn {
  color: #8a5b24;
  border-color: #e6d0ad;
}

.btn.ghost {
  background: #f6f8f7;
}

.row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  align-items: end;
}

.checks-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: #4b5e54;
  white-space: nowrap;
  cursor: pointer;
}

.checkline input {
  width: auto;
  margin: 0;
}

.flex-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.grow {
  flex: 1;
  min-width: 0;
}

.sub-box {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #f7faf8;
  border: 1px solid #e4ece7;
}

.sub-box-title {
  font-size: 12px;
  font-weight: 600;
  color: #354e43;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rows-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.rowitem {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px 46px 28px 30px 28px;
  gap: 4px;
  align-items: center;
}

.rowitem input {
  height: 28px;
  padding: 0 2px;
  text-align: center;
  font-size: 12.5px;
}

.rowitem .btn.xxs {
  width: 100%;
  height: 28px;
  padding: 0;
  font-size: 12px;
}

.rowitem .rowname {
  display: flex;
  align-items: center;
  height: 28px;
  text-align: left;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  padding: 0 8px;
  border: 0;
  border-radius: 6px;
  background: #f1f5f2;
  color: #1f332c;
  font-size: 12.5px;
  cursor: pointer;
}

.rowitem.active .rowname {
  background: #dbece2;
  font-weight: 700;
}

.rowitem.is-hidden-row {
  opacity: 0.6;
}

.plants-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.plant-chip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 4px 8px;
  border-radius: 6px;
  background: #ffffff;
  border: 1px solid #e0e8e3;
  font-size: 12px;
  min-width: 0;
}

.plant-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-banner {
  background: #edf4ef;
  padding: 8px 10px;
  border-radius: 7px;
  margin-bottom: 8px;
  font-size: 12.5px;
}

.swap-hint {
  color: #b45309;
  font-weight: 600;
}

.hidden-hint {
  color: #7c8a82;
}

.search-results {
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 150px;
  overflow-y: auto;
}

.found-btn {
  text-align: left;
  border: 0;
  background: #fff4d9;
  padding: 5px 8px;
  border-radius: 5px;
  font-size: 12px;
  cursor: pointer;
}

.photo-details {
  margin-top: 10px;
}

.photo-details summary {
  cursor: pointer;
  color: #22644f;
  font-size: 12.5px;
  font-weight: 600;
}

.photos-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-top: 8px;
}

.photos-grid img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid #dce4df;
}

.stage {
  min-width: 0;
  background: #ffffff;
  border: 1px solid #dce4df;
  border-radius: 12px;
  overflow: hidden;
}

.stagebar {
  padding: 11px 14px;
  border-bottom: 1px solid #dce4df;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.stats {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.stat b {
  font-size: 18px;
  font-variant-numeric: tabular-nums;
  color: #153b30;
}

.stat span {
  font-size: 12px;
  color: #687970;
  margin-left: 4px;
}

.muted-stat b {
  color: #7d8c84;
}

.stage-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.zoom-group {
  display: inline-flex;
  gap: 4px;
}

.stagebody {
  padding: 10px;
  background: #f7f9f7;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
}

.print-sheet {
  width: 100%;
  background: #ffffff;
  border: 1px solid #dce4df;
  padding: 12px 14px;
  max-width: 1280px;
  margin: auto;
  display: flex;
  flex-direction: column;
}

.print-sheet.is-portrait {
  max-width: 1020px;
}

.sheethead {
  text-align: center;
  margin-bottom: 8px;
}

.sheethead h2 {
  margin: 0;
  font-size: 23px;
  letter-spacing: 0.06em;
  overflow-wrap: anywhere;
}

.sheetsub {
  font-size: 12px;
  color: #65756d;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.mapwrap {
  width: 100%;
  min-width: 0;
}

.legend {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 11px;
  color: #5b6c62;
  margin-top: 8px;
}

.swatch {
  display: inline-block;
  width: 12px;
  height: 10px;
  border: 1px solid #8a9b91;
  border-radius: 2px;
  margin-right: 4px;
  vertical-align: middle;
}

.assignedsw {
  background: #e1eee5;
  border-color: #42765e;
}

.selectedsw {
  border: 2px solid #ca8b23;
}

.mono .assignedsw {
  background: #eee;
  border-color: #222;
}

.mono .selectedsw {
  border-color: #999;
}

.sheetfoot {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #748278;
  gap: 10px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.notice {
  min-height: 22px;
  color: #8a5b24;
  font-size: 12px;
  padding: 7px 14px;
  border-top: 1px solid #edf2ee;
  background: #fcfdfb;
}

.mobile-quick-bar {
  display: none;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 1200;
}

.modal-card {
  width: 100%;
  max-width: 410px;
  background: #ffffff;
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.2);
}

.modal-card h4 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #153b30;
}

.modal-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 960px) {
  .seating-shell {
    padding: 10px 10px 24px;
  }

  .top-toolbar {
    padding: 12px;
  }

  .title-row h2 {
    font-size: 18px;
  }

  .profile-select-group {
    min-width: 100%;
  }

  .profile-select {
    max-width: none;
    flex: 1;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .stage {
    order: 1;
  }

  .mobile-tabs {
    order: 2;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 6px;
    background: #ffffff;
    padding: 6px;
    border-radius: 10px;
    border: 1px solid #dce4df;
  }

  .mobile-tab-btn {
    border: 0;
    border-radius: 7px;
    padding: 8px 4px;
    font-size: 12.5px;
    background: #f4f7f5;
    color: #3a5248;
    cursor: pointer;
    font-weight: 500;
  }

  .mobile-tab-btn.active {
    background: #22644f;
    color: #ffffff;
    font-weight: 600;
  }

  .panel {
    order: 3;
    padding: 12px;
  }

  .panel-section {
    border-top: 0;
    padding: 0;
  }

  .stagebar {
    padding: 10px;
    gap: 8px;
  }

  .stats {
    gap: 10px;
  }

  .stat b {
    font-size: 16px;
  }

  .stagebody {
    padding: 4px;
  }

  .print-sheet,
  .print-sheet.is-portrait {
    padding: 6px;
    max-width: none;
  }

  .sheethead h2 {
    font-size: 17px;
  }

  .mobile-quick-bar {
    display: block;
    padding: 10px 12px;
    background: #edf5ef;
    border-top: 1px solid #cfe0d6;
  }

  .mq-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    font-size: 13px;
    color: #153b30;
  }

  .mq-row {
    display: flex;
    gap: 6px;
    align-items: center;
  }
}

@media (max-width: 480px) {
  .toolbar-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }

  .toolbar-actions .btn.sm {
    width: 100%;
    height: 30px;
    padding: 0 4px;
    font-size: 12px;
  }

  .profile-btn-group {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .profile-btn-group .btn.sm {
    width: 100%;
    height: 32px;
    padding: 0 6px;
    font-size: 12px;
  }

  .stage-controls {
    width: 100%;
    justify-content: space-between;
  }

  .mobile-tab-btn {
    font-size: 12px;
    padding: 7px 2px;
  }
}

@media print {
  .seating-app {
    background: #ffffff !important;
    height: var(--seating-print-height, 276mm) !important;
    max-height: var(--seating-print-height, 276mm) !important;
    min-height: 0 !important;
    overflow: hidden !important;
  }

  .seating-shell {
    padding: 0 !important;
    margin: 0 !important;
    max-width: none !important;
    height: 100% !important;
    overflow: hidden !important;
  }

  .noprint {
    display: none !important;
  }

  .workspace-grid,
  .stage,
  .stagebody {
    display: block !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 0 !important;
    box-shadow: none !important;
    background: #ffffff !important;
    max-width: none !important;
    height: 100% !important;
    overflow: hidden !important;
  }

  .print-sheet {
    border: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    max-width: none !important;
    width: 100% !important;
    height: var(--seating-print-height, 276mm) !important;
    max-height: var(--seating-print-height, 276mm) !important;
    display: flex !important;
    flex-direction: column !important;
    break-inside: avoid;
    page-break-inside: avoid;
    break-after: avoid;
    page-break-after: avoid;
    overflow: hidden !important;
  }

  .sheethead {
    flex: 0 0 auto !important;
    margin: 0 0 1.5mm;
  }

  .sheethead h2 {
    font-size: 16pt;
  }

  .sheetsub {
    font-size: 9pt;
  }

  .mapwrap {
    flex: 1 1 0% !important;
    min-height: 0 !important;
    min-width: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
  }

  .mapwrap :deep(.canvas-shell),
  .mapwrap :deep(.seating-svg) {
    width: 100% !important;
    height: 100% !important;
    max-width: 100% !important;
    max-height: 100% !important;
    display: block !important;
    overflow: hidden !important;
  }

  .legend,
  .sheetfoot {
    flex: 0 0 auto !important;
    font-size: 8.5pt;
    margin-top: 1mm;
  }

  .selectedlegend {
    display: none !important;
  }

  * {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }
}
</style>
