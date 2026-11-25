<template>
  <div ref="dcsRootEl" :class="['dcs-shell', { 'is-fullscreen': isFullscreen }]">
    <AppHeader v-if="!isFullscreen" />
    <main class="dcs-main">
      <template v-if="!isFullscreen">
        <Breadcrumbs :items="breadcrumbItems" />
        <PlatformSubNav current="dcs_workbench" />
      </template>

      <!-- Experion Orion 顶层控制台 -->
      <header class="dcs-topbar dcs-panel">
        <div class="topbar-brand">
          <div class="dcs-tag-chip">
            <span :class="['status-led', loading ? 'led-busy' : 'led-ok']"></span>
            <span>EXP-PKS // HPHMI-ASM</span>
          </div>
          <div class="topbar-title-block">
            <h1>主城区智慧供热 · DCS 工艺监控试验台</h1>
            <span class="meta-mono">
              断面：<strong>{{ meta.biz_hour_label || '--' }}</strong>
              ｜ 在网：<strong>{{ kpis.online_stations ?? 0 }}/{{ kpis.total_stations ?? 242 }} 站</strong>
              <template v-if="meta.last_run?.finished_at"> ｜ 末次采数：{{ meta.last_run.finished_at }}</template>
            </span>
          </div>
        </div>

        <div class="topbar-controls">
          <DateStepPicker v-model="selectedDate" aria-label="选择 DCS 监测日期" @change="onDateChange" />
          <div class="dcs-step-group" role="group" aria-label="小时切换">
            <button type="button" class="dcs-btn-sq" :disabled="!canStepPrevHour" title="上一小时" @click="stepHour(-1)">◀</button>
            <select v-model.number="selectedHour" class="dcs-select" aria-label="选择小时" @change="loadReport">
              <option v-if="selectedHour === null" :value="null" disabled>定位最新…</option>
              <option v-for="h in trend24h" :key="h.hour" :value="h.hour">
                {{ h.label }}{{ h.has_data ? '' : ' (无)' }}
              </option>
            </select>
            <button type="button" class="dcs-btn-sq" :disabled="!canStepNextHour" title="下一小时" @click="stepHour(1)">▶</button>
            <button type="button" class="dcs-btn" :disabled="loading" @click="jumpToLatest">最新</button>
          </div>

          <div class="dcs-mode-group" role="group" aria-label="数据口径切换">
            <button
              type="button"
              :class="['dcs-btn', { 'is-active': mode === 'clean' }]"
              @click="switchMode('clean')"
            >
              净化工艺值
            </button>
            <button
              type="button"
              :class="['dcs-btn', { 'is-raw': mode === 'raw' }]"
              title="切换至未清洗原始传感器值，直观观察原始故障报警"
              @click="switchMode(mode === 'raw' ? 'clean' : 'raw')"
            >
              {{ mode === 'raw' ? '还原净化值' : '原始信号(RAW)' }}
            </button>
          </div>

          <button type="button" class="dcs-btn" :disabled="loading" @click="loadReport">🔄 刷新</button>
          <button type="button" class="dcs-btn desktop-only" @click="toggleFullscreen">
            {{ isFullscreen ? '退出全屏' : '⛶ 全屏台' }}
          </button>
        </div>
      </header>

      <!-- ISA-18.2 常驻报警横幅 (Alarm Banner) -->
      <section class="dcs-alarm-banner dcs-panel" aria-label="实时异常报警横幅">
        <div class="alarm-counts">
          <button
            type="button"
            :class="['alm-pill alm-crit', { active: stationStatusFilter === 'CRITICAL' }]"
            @click="toggleStatusFilter('CRITICAL')"
          >
            <span>◆ 严重 {{ alarmCounts.critical }}</span>
          </button>
          <button
            type="button"
            :class="['alm-pill alm-warn', { active: stationStatusFilter === 'WARN' }]"
            @click="toggleStatusFilter('WARN')"
          >
            <span>▲ 警告/降级 {{ alarmCounts.warning }}</span>
          </button>
          <button
            type="button"
            :class="['alm-pill alm-oos', { active: stationStatusFilter === 'OFFLINE' }]"
            @click="toggleStatusFilter('OFFLINE')"
          >
            <span>● 离线/无数据 {{ alarmCounts.offline }}</span>
          </button>
        </div>

        <div class="alarm-ticker">
          <template v-if="topAlarms.length">
            <button
              v-for="alm in topAlarms.slice(0, 3)"
              :key="alm.id"
              type="button"
              :class="['alarm-strip-item', `sev-${alm.severity}`]"
              :title="`点击定位并调阅 ${alm.entityName} 工艺图`"
              @click="focusAlarm(alm)"
            >
              <span class="alm-code">{{ alm.tag }}</span>
              <span class="alm-msg">{{ alm.entityName }}：{{ alm.summary }}</span>
            </button>
          </template>
          <span v-else class="alarm-clear">✓ 当前时段全网工艺参数平稳，无未处理关键异常</span>
        </div>

        <div class="alarm-actions">
          <button type="button" class="dcs-btn" @click="alarmDrawerOpen = !alarmDrawerOpen">
            {{ alarmDrawerOpen ? '收起报警单' : `报警单 (${allAlarms.length})` }}
          </button>
        </div>
      </section>

      <!-- 可展开完整报警列表 -->
      <section v-if="alarmDrawerOpen" class="dcs-panel alarm-drawer">
        <div class="panel-head">
          <h3>ISA-18.2 异常事件与报警一览（{{ allAlarms.length }} 条 · 点击任意行直接切换工艺组态画面）</h3>
          <div class="alarm-filter-inline">
            <button
              v-for="opt in [{k:'ALL',l:'全部'},{k:'critical',l:'◆ 严重'},{k:'warning',l:'▲ 警告'},{k:'offline',l:'● 离线'}]"
              :key="opt.k"
              type="button"
              :class="['dcs-btn-xs', { 'is-active': alarmSeverityFilter === opt.k }]"
              @click="alarmSeverityFilter = opt.k"
            >
              {{ opt.l }}
            </button>
            <button type="button" class="dcs-btn-xs" @click="alarmDrawerOpen = false">✕ 关闭</button>
          </div>
        </div>
        <div class="alarm-table-scroll">
          <table class="dcs-table">
            <thead>
              <tr>
                <th>级别</th>
                <th>对象</th>
                <th>位号/名称</th>
                <th>归属</th>
                <th>异常描述</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="alm in filteredAlarmList.slice(0, 80)"
                :key="alm.id"
                class="clickable"
                @click="focusAlarm(alm)"
              >
                <td>
                  <span :class="['sev-badge', `sev-${alm.severity}`]">
                    {{ alm.severity === 'critical' ? '◆ 严重' : (alm.severity === 'warning' ? '▲ 警告' : '● 离线') }}
                  </span>
                </td>
                <td class="mono">{{ alm.kindLabel }}</td>
                <td class="bold">{{ alm.entityName }}</td>
                <td>{{ alm.scopeText }}</td>
                <td>{{ alm.summary }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div v-if="errorMsg" class="dcs-error-strip">⚠️ 接口加载异常：{{ errorMsg }}</div>

      <!-- 主工艺画布切换：全网PFD工艺总貌 vs 单站P&ID设备实景组态 -->
      <section class="dcs-panel stage-switch-panel">
        <div class="panel-head">
          <div class="stage-tabs">
            <button
              type="button"
              :class="['dcs-tab', { active: mainCanvasMode === 'network_pfd' }]"
              @click="mainCanvasMode = 'network_pfd'"
            >
              🔀 LEVEL 1 · 全网工艺总貌组态 (PFD)
            </button>
            <button
              type="button"
              :class="['dcs-tab', { active: mainCanvasMode === 'unit_pid' }]"
              @click="mainCanvasMode = 'unit_pid'"
            >
              🏭 LEVEL 2 · 单站/节点设备工艺实景图 (P&amp;ID)
            </button>
            <button
              type="button"
              :class="['dcs-tab', { active: mainCanvasMode === 'aux_table' }]"
              @click="mainCanvasMode = 'aux_table'"
            >
              ▤ 辅助参数数值表
            </button>
          </div>
          <div class="panel-right-chips">
            <span v-if="selectedRdfz" class="filter-chip">
              管网聚焦：<strong>{{ selectedRdfz }}</strong>
              <button type="button" class="chip-clear" @click="selectedRdfz = ''">✕</button>
            </span>
            <span class="l1-chip">室外 <strong>{{ fmt(kpis.outdoor_temp, '℃', 1) }}</strong></span>
            <span class="l1-chip">总供热 <strong>{{ fmt(kpis.hour_heat_gj, ' GJ', 1) }}</strong></span>
            <span class="l1-chip">热指标 <strong>{{ fmt(kpis.heat_index_wm2, ' W/㎡', 1) }}</strong></span>
            <span class="l1-chip">室温 <strong>{{ fmt(kpis.avg_room_temp, '℃', 2) }}</strong></span>
          </div>
        </div>

        <!-- 画面 A：全网工艺流向总貌 PFD（默认上方常驻或全画幅，这里支持单独切换或上下并排） -->
        <DcsNetworkPfd
          v-if="mainCanvasMode === 'network_pfd'"
          :plant-nodes="plantNodes"
          :hub-nodes="hubNodes"
          :rdfz-blocks="rdfzBlocks"
          :kpis="kpis"
          :merchant-summary="merchantSummary"
          :temp-summary="tempSummary"
          :selected-rdfz="selectedRdfz"
          @select-plant="onSelectPlant"
          @select-hub="onSelectHub"
          @toggle-rdfz="toggleRdfz"
          @open-merchants="onOpenMerchants"
        />
      </section>

      <!-- 核心操作区：左（242站微缩状态点阵导览） + 中（当前站/热源设备 P&ID 工艺图 或 辅助数值表） + 右（Experion Faceplate） -->
      <div :class="['dcs-console-grid', { 'has-faceplate': Boolean(selectedTarget) }]">
        <!-- 左侧：高密度微缩导览器（替代大卡片和冗长表格） -->
        <aside class="dcs-panel nav-rail">
          <div class="rail-tabs">
            <button
              type="button"
              :class="['rail-tab', { active: navKind === 'stations' }]"
              @click="navKind = 'stations'"
            >
              站阵 ({{ filteredStations.length }})
            </button>
            <button
              type="button"
              :class="['rail-tab', { active: navKind === 'upstream' }]"
              @click="navKind = 'upstream'"
            >
              热源 ({{ filteredUpstream.length }})
            </button>
            <button
              type="button"
              :class="['rail-tab', { active: navKind === 'merchants' }]"
              @click="navKind = 'merchants'"
            >
              商户 ({{ filteredMerchants.length }})
            </button>
          </div>

          <div class="rail-filters">
            <input
              v-if="navKind === 'stations'"
              v-model="stationKeyword"
              type="search"
              class="dcs-input-full"
              placeholder="搜站名 / 中心…"
            />
            <input
              v-else-if="navKind === 'upstream'"
              v-model="upstreamKeyword"
              type="search"
              class="dcs-input-full"
              placeholder="搜电厂 / 首站…"
            />
            <input
              v-else
              v-model="merchantKeyword"
              type="search"
              class="dcs-input-full"
              placeholder="搜商业户…"
            />

            <div v-if="navKind === 'stations'" class="rail-selects">
              <select v-model="stationCenterFilter" class="dcs-select-sm">
                <option value="">全部中心</option>
                <option v-for="c in centerOptions" :key="c.id" :value="String(c.id)">{{ c.name.replace('服务中心', '') }}</option>
              </select>
              <select v-model="stationStatusFilter" class="dcs-select-sm">
                <option value="ALL">全状态</option>
                <option value="CRITICAL">◆ 严重</option>
                <option value="WARN">▲ 警告</option>
                <option value="OFFLINE">● 离线</option>
                <option value="COLD">室温&lt;18</option>
              </select>
            </div>
            <div v-else-if="navKind === 'upstream'" class="rail-selects">
              <select v-model="upstreamCategoryFilter" class="dcs-select-sm">
                <option value="">全部类别</option>
                <option value="电厂">电厂</option>
                <option value="首站">首站</option>
                <option value="网口">网口</option>
              </select>
            </div>
            <div v-else class="rail-selects">
              <select v-model="merchantStatusFilter" class="dcs-select-sm">
                <option value="ALL">全部状态</option>
                <option value="ACTIVE">有用热负荷</option>
                <option value="ABNORMAL">异常/离线</option>
              </select>
            </div>
          </div>

          <!-- 242 站极简微缩矩阵导览 -->
          <div v-if="navKind === 'stations'" class="micro-list">
            <button
              v-for="s in filteredStations"
              :key="s.station_id"
              type="button"
              :class="[
                'micro-item',
                `sev-${s._severity}`,
                { active: selectedTarget?.kind === 'station' && selectedTarget.id === s.station_id },
              ]"
              @click="selectStationFromNav(s)"
            >
              <span :class="['micro-led', `led-${s._severity}`]"></span>
              <span class="micro-name" :title="`${s.name} (${s.center_name})`">{{ s.name }}</span>
              <span class="micro-val">{{ fmt(s.heat_index_wm2, 'W', 0) }}</span>
              <span class="micro-temp">{{ fmt(s.e3, '°', 0) }}</span>
            </button>
          </div>

          <!-- 上游点位微缩导览 -->
          <div v-else-if="navKind === 'upstream'" class="micro-list">
            <button
              v-for="u in filteredUpstream"
              :key="`${u.data_zone}:${u.source_name}`"
              type="button"
              :class="[
                'micro-item',
                `sev-${u._severity}`,
                { active: selectedTarget?.kind === 'upstream' && selectedTarget.id === `${u.data_zone}:${u.source_name}` },
              ]"
              @click="selectUpstreamFromNav(u)"
            >
              <span :class="['micro-led', `led-${u._severity}`]"></span>
              <span class="micro-name" :title="u.display_name">{{ u.display_name }}</span>
              <span class="micro-val">{{ fmt(u.temp, '℃', 0) }}</span>
            </button>
          </div>

          <!-- 商户微缩导览 -->
          <div v-else class="micro-list">
            <button
              v-for="m in filteredMerchants"
              :key="m.merchant_id"
              type="button"
              :class="[
                'micro-item',
                `sev-${m._severity}`,
                { active: selectedTarget?.kind === 'merchant' && selectedTarget.id === m.merchant_id },
              ]"
              @click="selectMerchantFromNav(m)"
            >
              <span :class="['micro-led', `led-${m._severity}`]"></span>
              <span class="micro-name" :title="`${m.name} (${m.branch_name})`">{{ m.name }}</span>
              <span class="micro-val">{{ fmt(m.hour_heat_gj, 'GJ', 1) }}</span>
              <span class="micro-temp">{{ m.valve_open != null ? `${fmt(m.valve_open, '%', 0)}` : '--' }}</span>
            </button>
          </div>
        </aside>

        <!-- 中央主区：单站/热源实时 P&ID 设备工艺组态图（或可选辅助明细表） -->
        <section class="dcs-panel center-stage">
          <DcsStationPid
            v-if="mainCanvasMode !== 'aux_table'"
            :target="selectedTarget"
            :upstream-points="upstreamWithMeta"
            :trend-rows="fpTrendRows"
            :trend-loading="fpTrendLoading"
            @select-upstream="selectUpstreamFromNav"
          />

          <div v-else class="aux-table-wrap">
            <div class="aux-head">
              <h3>辅助工艺参数列表（点击行切回单站 P&amp;ID 工艺图）</h3>
              <button type="button" class="dcs-btn-xs" @click="mainCanvasMode = 'network_pfd'">↩ 返回工艺组态</button>
            </div>
            <div class="l2-table-scroll">
              <table v-if="navKind === 'stations'" class="dcs-table">
                <thead>
                  <tr>
                    <SortableTh label="状态" sort-key="_sevOrder" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                    <SortableTh label="换热站" sort-key="name" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                    <SortableTh label="中心/热网" sort-key="center_name" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                    <SortableTh label="一网供/回温(℃)" sort-key="e3" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                    <SortableTh label="小时热量(GJ)" sort-key="hour_heat_gj" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                    <SortableTh label="热指标(W/㎡)" sort-key="heat_index_wm2" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                    <SortableTh label="补水(t)" sort-key="hour_water_t" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                    <SortableTh label="电耗(kWh)" sort-key="hour_elec_kwh" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                    <SortableTh label="室温(℃)" sort-key="avg_room_temp" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="s in stationSort.sortedRows.value"
                    :key="s.station_id"
                    :class="['clickable', { 'row-selected': selectedTarget?.kind === 'station' && selectedTarget.id === s.station_id }]"
                    @click="selectStationFromNav(s)"
                  >
                    <td><span :class="['sev-badge', `sev-${s._severity}`]">{{ s._statusCode }}</span></td>
                    <td class="bold">{{ s.name }}</td>
                    <td>{{ s.center_name.replace('服务中心', '') }} / {{ s.rdfz }}</td>
                    <td class="mono">{{ fmt(s.e3, '', 1) }} / {{ fmt(s.e4, '', 1) }}</td>
                    <td class="mono bold">{{ fmt(s.hour_heat_gj, '', 2) }}</td>
                    <td class="mono">{{ fmt(s.heat_index_wm2, '', 1) }}</td>
                    <td class="mono">{{ fmt(s.hour_water_t ?? s.e14, '', 2) }}</td>
                    <td class="mono">{{ fmt(s.hour_elec_kwh, '', 1) }}</td>
                    <td :class="['mono bold', s.avg_room_temp !== null && s.avg_room_temp < 18 ? 'cold-txt' : '']">
                      {{ fmt(s.avg_room_temp, '', 1) }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <table v-else-if="navKind === 'upstream'" class="dcs-table">
                <thead>
                  <tr>
                    <SortableTh label="状态" sort-key="_sevOrder" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                    <SortableTh label="类别/子类" sort-key="category" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                    <SortableTh label="测点名称" sort-key="display_name" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                    <SortableTh label="温度(℃)" sort-key="temp" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                    <SortableTh label="压力(MPa)" sort-key="pressure" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                    <SortableTh label="流量(t/h)" sort-key="flow" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                    <SortableTh label="小时积分(GJ)" sort-key="hour_heat_gj" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="u in upstreamSort.sortedRows.value"
                    :key="`${u.data_zone}:${u.source_name}`"
                    class="clickable"
                    @click="selectUpstreamFromNav(u)"
                  >
                    <td><span :class="['sev-badge', `sev-${u._severity}`]">{{ u._statusCode }}</span></td>
                    <td>{{ u.category }} · {{ u.sub_category || '-' }}</td>
                    <td class="bold">{{ u.display_name }}</td>
                    <td class="mono">{{ fmt(u.temp, '', 1) }}</td>
                    <td class="mono">{{ fmt(u.pressure, '', 3) }}</td>
                    <td class="mono">{{ fmt(u.flow, '', 1) }}</td>
                    <td class="mono bold">{{ fmt(u.hour_heat_gj, '', 2) }}</td>
                  </tr>
                </tbody>
              </table>
              <table v-else class="dcs-table">
                <thead>
                  <tr>
                    <SortableTh label="状态" sort-key="_sevOrder" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                    <SortableTh label="商业户" sort-key="name" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                    <SortableTh label="热网/支线" sort-key="branch_name" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                    <SortableTh label="供/回温(℃)" sort-key="temp_sup" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                    <SortableTh label="流量(t/h)" sort-key="flow" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                    <SortableTh label="小时热(GJ)" sort-key="hour_heat_gj" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                    <SortableTh label="阀位" sort-key="valve_open" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="m in merchantSort.sortedRows.value"
                    :key="m.merchant_id"
                    :class="['clickable', { 'row-selected': selectedTarget?.kind === 'merchant' && selectedTarget.id === m.merchant_id }]"
                    @click="selectMerchantFromNav(m)"
                  >
                    <td><span :class="['sev-badge', `sev-${m._severity}`]">{{ m._statusCode }}</span></td>
                    <td class="bold">{{ m.name }}</td>
                    <td>{{ m.rdfz || '-' }} / {{ m.branch_name }}</td>
                    <td class="mono">{{ fmt(m.temp_sup, '', 1) }} / {{ fmt(m.temp_ret, '', 1) }}</td>
                    <td class="mono">{{ fmt(m.flow, '', 2) }}</td>
                    <td class="mono bold">{{ fmt(m.hour_heat_gj, '', 2) }}</td>
                    <td class="mono">{{ m.valve_open != null ? `${fmt(m.valve_open, '%', 0)}` : '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- 右侧：Experion 标准 Faceplate 面板 -->
        <aside v-if="selectedTarget" class="dcs-panel faceplate-panel" aria-label="DCS 标准对象面板">
          <div class="fp-header">
            <div class="fp-tag-row">
              <span class="fp-tag-id">{{ selectedTarget.tagId }}</span>
              <span :class="['fp-mode-pill', `sev-${selectedTarget.severity}`]">
                只读 · {{ selectedTarget.modeLabel }}
              </span>
              <button type="button" class="dcs-btn-xs" title="关闭面板" @click="selectedTarget = null">✕</button>
            </div>
            <h3 class="fp-title">{{ selectedTarget.title }}</h3>
            <p class="fp-subtitle">{{ selectedTarget.subtitle }}</p>
          </div>

          <template v-if="selectedTarget.kind === 'station'">
            <div class="fp-section">
              <div class="fp-sec-title">模拟量工艺参数与量程带 (PV / RANGE)</div>
              <div class="fp-gauges">
                <DcsAnalogBar
                  label="一次网供温 (e3)"
                  :value="selectedTarget.raw.e3"
                  :min="0"
                  :max="130"
                  :safe-min="45"
                  :safe-max="115"
                  unit="℃"
                />
                <DcsAnalogBar
                  label="一次网回温 (e4)"
                  :value="selectedTarget.raw.e4"
                  :min="0"
                  :max="90"
                  :safe-min="25"
                  :safe-max="65"
                  unit="℃"
                />
                <DcsAnalogBar
                  label="折算热指标"
                  :value="selectedTarget.raw.heat_index_wm2"
                  :min="0"
                  :max="90"
                  :safe-min="15"
                  :safe-max="55"
                  :warn-high="65"
                  unit=" W/㎡"
                />
                <DcsAnalogBar
                  label="一次供压 (e7)"
                  :value="selectedTarget.raw.e7"
                  :min="0"
                  :max="1.6"
                  :safe-min="0.2"
                  :safe-max="1.2"
                  :decimals="3"
                  unit=" MPa"
                />
              </div>

              <div class="fp-kv-grid">
                <div class="fp-kv">
                  <span>小时供热 ({{ selectedTarget.raw.hour_heat_source === 'METER_DIFF' ? '表底' : '积分' }})</span>
                  <strong>{{ fmt(selectedTarget.raw.hour_heat_gj, ' GJ', 2) }}</strong>
                </div>
                <div class="fp-kv">
                  <span>表底 totJ</span>
                  <strong>{{ fmt(selectedTarget.raw.tot_j, ' GJ', 1) }}</strong>
                </div>
                <div class="fp-kv">
                  <span>小时补水</span>
                  <strong>{{ fmt(selectedTarget.raw.hour_water_t ?? selectedTarget.raw.e14, ' t', 2) }}</strong>
                </div>
                <div class="fp-kv">
                  <span>小时电耗</span>
                  <strong>{{ fmt(selectedTarget.raw.hour_elec_kwh, ' kWh', 1) }}</strong>
                </div>
              </div>

              <div v-if="selectedTarget.notesList.length" class="fp-alarm-notes">
                <div v-for="(nt, idx) in selectedTarget.notesList" :key="idx" class="fp-note-item">
                  ▲ {{ nt }}
                </div>
              </div>
            </div>

            <div class="fp-section">
              <div class="fp-sec-title">
                <span>站区居民室温 ({{ selectedTarget.raw.temp_valid_count ?? 0 }} 有效户)</span>
                <button type="button" class="dcs-btn-xs" @click="loadFpTempDevices">
                  {{ fpTempsLoaded ? '刷新' : '展开单户' }}
                </button>
              </div>
              <DcsAnalogBar
                label="平均室温 (红线 18℃)"
                :value="selectedTarget.raw.avg_room_temp"
                :min="12"
                :max="28"
                :safe-min="20"
                :safe-max="25"
                :alarm-low="18"
                unit="℃"
              />
              <div v-if="fpTempsLoaded" class="fp-temp-list">
                <div v-if="fpTempDevices.length === 0" class="muted-mini">暂无室温终端记录</div>
                <div v-for="d in fpTempDevices.slice(0, 20)" :key="d.temp_device_id" class="fp-temp-row">
                  <span class="fp-temp-addr">{{ d.village_name }}</span>
                  <span :class="['mono bold', !d.is_online_valid ? 'muted-mini' : (d.temp_clean < 18 ? 'cold-txt' : '')]">
                    {{ d.is_online_valid ? `${fmt(d.temp_clean, '℃', 1)}` : `剔除` }}
                  </span>
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="selectedTarget.kind === 'upstream'">
            <div class="fp-section">
              <div class="fp-sec-title">上游关键工艺参数 (PV)</div>
              <div class="fp-gauges">
                <DcsAnalogBar
                  label="瞬时温度"
                  :value="selectedTarget.raw.temp"
                  :min="0"
                  :max="selectedTarget.isSteam ? 600 : 150"
                  :safe-min="30"
                  :safe-max="selectedTarget.isSteam ? 560 : 135"
                  unit="℃"
                />
                <DcsAnalogBar
                  label="瞬时压力"
                  :value="selectedTarget.raw.pressure"
                  :min="0"
                  :max="selectedTarget.isSteam ? 12 : 2.5"
                  :safe-min="0.1"
                  :safe-max="selectedTarget.isSteam ? 10 : 2.0"
                  :decimals="3"
                  unit=" MPa"
                />
              </div>
              <div v-if="selectedTarget.notesList.length" class="fp-alarm-notes">
                <div v-for="(nt, idx) in selectedTarget.notesList" :key="idx" class="fp-note-item">
                  ▲ {{ nt }}
                </div>
              </div>
            </div>
          </template>

          <template v-else-if="selectedTarget.kind === 'merchant'">
            <div class="fp-section">
              <div class="fp-sec-title">商业户调节阀与一次侧工况 (PV)</div>
              <div class="fp-gauges">
                <DcsAnalogBar
                  label="调节阀实测开度"
                  :value="selectedTarget.raw.valve_open"
                  :min="0"
                  :max="100"
                  :safe-min="0"
                  :safe-max="100"
                  unit="%"
                />
                <DcsAnalogBar
                  label="供水温度"
                  :value="selectedTarget.raw.temp_sup"
                  :min="0"
                  :max="selectedTarget.isSteam ? 300 : 130"
                  :safe-min="35"
                  :safe-max="selectedTarget.isSteam ? 260 : 115"
                  unit="℃"
                />
                <DcsAnalogBar
                  label="回水温度"
                  :value="selectedTarget.raw.temp_ret"
                  :min="0"
                  :max="90"
                  :safe-min="20"
                  :safe-max="65"
                  unit="℃"
                />
              </div>
              <div class="fp-kv-grid">
                <div class="fp-kv">
                  <span>小时积分热量</span>
                  <strong>{{ fmt(selectedTarget.raw.hour_heat_gj, ' GJ', 3) }}</strong>
                </div>
                <div class="fp-kv">
                  <span>小时流量</span>
                  <strong>{{ fmt(selectedTarget.raw.hour_flow_t, ' t', 2) }}</strong>
                </div>
                <div class="fp-kv">
                  <span>瞬时流量 / 热量</span>
                  <strong>{{ fmt(selectedTarget.raw.flow, ' t/h', 2) }} / {{ fmt(selectedTarget.raw.heat, ' GJ/h', 2) }}</strong>
                </div>
                <div class="fp-kv">
                  <span>供热介质</span>
                  <strong>{{ selectedTarget.raw.rdry || '高温水' }}</strong>
                </div>
              </div>
              <div v-if="selectedTarget.notesList.length" class="fp-alarm-notes">
                <div v-for="(nt, idx) in selectedTarget.notesList" :key="idx" class="fp-note-item">
                  ▲ {{ nt }}
                </div>
              </div>
            </div>
          </template>
        </aside>
      </div>
    </main>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import PlatformSubNav from '../components/PlatformSubNav.vue'
import DateStepPicker from '../components/DateStepPicker.vue'
import SortableTh from '../components/SortableTh.vue'
import DcsAnalogBar from '../components/DcsAnalogBar.vue'
import DcsNetworkPfd from '../components/DcsNetworkPfd.vue'
import DcsStationPid from '../components/DcsStationPid.vue'
import { useTableSort } from '../utils/tableSort'
import { MIN_PLATFORM_DATE, shiftIsoDate, todayLocalIso } from '../utils/dateUtils'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  fetchEntityTrend24h,
  fetchHourlyReport,
  fetchMerchantTrend24h,
  fetchStationTempDevices,
  fetchUpstreamTrend24h,
} from '../services/api'

const dcsRootEl = ref(null)
const isFullscreen = ref(false)
const selectedDate = ref('')
const selectedHour = ref(null)
const mode = ref('clean')
const loading = ref(false)
const errorMsg = ref('')

const mainCanvasMode = ref('network_pfd') // network_pfd | unit_pid | aux_table
const navKind = ref('stations') // stations | upstream | merchants
const alarmDrawerOpen = ref(false)
const alarmSeverityFilter = ref('ALL')
const selectedRdfz = ref('')
const stationCenterFilter = ref('')
const stationStatusFilter = ref('ALL')
const stationKeyword = ref('')
const upstreamCategoryFilter = ref('')
const upstreamKeyword = ref('')
const merchantStatusFilter = ref('ALL')
const merchantKeyword = ref('')

const selectedTarget = ref(null)
const fpTrendLoading = ref(false)
const fpTrendRows = ref([])
const fpTempsLoaded = ref(false)
const fpTempDevices = ref([])
let reportAbortCtrl = null
let reportSeq = 0

const reportData = ref({
  meta: {},
  kpis: {},
  trend_24h: Array.from({ length: 24 }, (_, h) => ({ hour: h, label: `${String(h).padStart(2, '0')}:00`, has_data: false })),
  upstream_points: [],
  group_summaries: { by_center: [], by_rdfz: [] },
  stations: [],
  merchants: [],
  merchant_summary: {},
  temp_summary: { valid_devices: 0, station_rankings: [] },
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热平台精算模块', to: '/projects/smart_heating_platform/pages' },
  { label: 'DCS工艺监控台（试验）', to: null },
])

const meta = computed(() => reportData.value.meta || {})
const kpis = computed(() => reportData.value.kpis || {})
const trend24h = computed(() => reportData.value.trend_24h || [])
const merchantSummary = computed(() => reportData.value.merchant_summary || {})
const tempSummary = computed(() => reportData.value.temp_summary || {})

function fmt(val, suffix = '', fixed = 2) {
  if (val === null || val === undefined || val === '') return '--'
  const num = Number(val)
  if (!Number.isFinite(num)) return '--'
  return `${num.toFixed(fixed).replace(/\.00$/, '')}${suffix}`
}

function classifyStation(s) {
  const notes = Object.values(s.field_notes || {}).filter(Boolean)
  const ftag = String(s.fault_tag || '')
  if (!s.has_record || s.value_source === 'OFFLINE_PERMANENT' || s.value_source === 'NO_DATA') {
    return { severity: 'offline', sevOrder: 2, statusCode: 'OOS', modeLabel: '无数据/常离线', notes }
  }
  if (!s.online || ftag.includes('TEMP_INVERSION') || ftag.includes('SENSOR_OUT_OF_RANGE') || (s.avg_room_temp !== null && s.avg_room_temp < 18)) {
    return {
      severity: 'critical',
      sevOrder: 0,
      statusCode: !s.online ? 'OFF' : (ftag.includes('TEMP_INVERSION') ? 'INV' : 'ALM'),
      modeLabel: !s.online ? '通讯掉线' : '严重越限/倒挂',
      notes,
    }
  }
  if (notes.length > 0 || (s.value_source && s.value_source !== 'REAL') || ftag.includes('METER_JUMP') || ftag.includes('HEAT_IMBALANCE') || s.covered_area == null) {
    return {
      severity: 'warning',
      sevOrder: 1,
      statusCode: 'WRN',
      modeLabel: s.value_source === 'REAL' ? '告警/隔离' : '降级估值(*)',
      notes,
    }
  }
  return { severity: 'normal', sevOrder: 3, statusCode: 'RUN', modeLabel: '自动 · 实测', notes }
}

function classifyUpstream(u) {
  const notes = Object.values(u.field_notes || {}).filter(Boolean)
  const ftag = String(u.fault_tag || '')
  if (u.value_source === 'NO_DATA' || u.value_source === 'OFFLINE_PERMANENT') {
    return { severity: 'offline', sevOrder: 2, statusCode: 'OOS', modeLabel: '无数据', notes }
  }
  if (ftag.includes('SENSOR_OUT_OF_RANGE') || ftag.includes('COMM_OFFLINE')) {
    return { severity: 'critical', sevOrder: 0, statusCode: 'ALM', modeLabel: '越限/停滞', notes }
  }
  if (notes.length > 0 || (u.value_source && u.value_source !== 'REAL')) {
    return { severity: 'warning', sevOrder: 1, statusCode: 'WRN', modeLabel: '平滑保持(*)', notes }
  }
  return { severity: 'normal', sevOrder: 3, statusCode: 'RUN', modeLabel: '在线实测', notes }
}

function classifyMerchant(m) {
  const notes = Object.values(m.field_notes || {}).filter(Boolean)
  if (!m.has_record || m.value_source === 'SOURCE_EMPTY' || m.value_source === 'NO_DATA') {
    return { severity: 'offline', sevOrder: 2, statusCode: 'OOS', modeLabel: '源站无数据', notes }
  }
  if (!m.online || String(m.fault_tag || '').includes('TEMP_INVERSION') || String(m.fault_tag || '').includes('SENSOR_OUT_OF_RANGE')) {
    return { severity: 'critical', sevOrder: 0, statusCode: !m.online ? 'OFF' : 'ALM', modeLabel: !m.online ? '通讯离线' : '传感越限/倒挂', notes }
  }
  if (notes.length > 0 || (m.value_source && m.value_source !== 'REAL')) {
    return { severity: 'warning', sevOrder: 1, statusCode: 'WRN', modeLabel: '平滑/折算(*)', notes }
  }
  return { severity: 'normal', sevOrder: 3, statusCode: 'RUN', modeLabel: '自动 · 实测', notes }
}

const stationsWithMeta = computed(() =>
  (reportData.value.stations || []).map((s) => {
    const cls = classifyStation(s)
    return { ...s, _severity: cls.severity, _sevOrder: cls.sevOrder, _statusCode: cls.statusCode, _modeLabel: cls.modeLabel, _notes: cls.notes }
  })
)

const upstreamWithMeta = computed(() =>
  (reportData.value.upstream_points || []).map((u) => {
    const cls = classifyUpstream(u)
    return { ...u, _severity: cls.severity, _sevOrder: cls.sevOrder, _statusCode: cls.statusCode, _modeLabel: cls.modeLabel, _notes: cls.notes }
  })
)

const merchantsWithMeta = computed(() =>
  (reportData.value.merchants || []).map((m) => {
    const cls = classifyMerchant(m)
    return { ...m, _severity: cls.severity, _sevOrder: cls.sevOrder, _statusCode: cls.statusCode, _modeLabel: cls.modeLabel, _notes: cls.notes }
  })
)

const allAlarms = computed(() => {
  const list = []
  for (const s of stationsWithMeta.value) {
    if (s._severity === 'normal') continue
    const summary = s._notes[0]
      || (!s.online && s.has_record ? '换热站通讯离线' : '')
      || (s.avg_room_temp !== null && s.avg_room_temp < 18 ? `平均室温 ${fmt(s.avg_room_temp, '℃', 1)} 低于 18℃` : '')
      || (s.covered_area == null ? '站台账缺供热面积' : '')
      || (s.value_source !== 'REAL' ? `数据状态：${s._modeLabel}` : '存在运行异常')
    list.push({
      id: `st-${s.station_id}`,
      kind: 'station',
      kindLabel: '换热站',
      tag: s._statusCode,
      severity: s._severity,
      sevOrder: s._sevOrder,
      entityName: s.name,
      scopeText: `${s.center_name.replace('服务中心', '')} / ${s.rdfz}`,
      summary,
      raw: s,
    })
  }
  for (const u of upstreamWithMeta.value) {
    if (u._severity === 'normal') continue
    list.push({
      id: `up-${u.data_zone}-${u.source_name}`,
      kind: 'upstream',
      kindLabel: u.category || '上游',
      tag: u._statusCode,
      severity: u._severity,
      sevOrder: u._sevOrder,
      entityName: u.display_name,
      scopeText: `${u.category} · ${u.sub_category || u.data_zone}`,
      summary: u._notes[0] || u._modeLabel,
      raw: u,
    })
  }
  return list.sort((a, b) => a.sevOrder - b.sevOrder)
})

const alarmCounts = computed(() => {
  let critical = 0
  let warning = 0
  let offline = 0
  for (const a of allAlarms.value) {
    if (a.severity === 'critical') critical += 1
    else if (a.severity === 'warning') warning += 1
    else offline += 1
  }
  return { critical, warning, offline }
})

const topAlarms = computed(() => allAlarms.value.filter((a) => a.severity === 'critical' || a.severity === 'warning'))

const filteredAlarmList = computed(() => {
  if (alarmSeverityFilter.value === 'ALL') return allAlarms.value
  return allAlarms.value.filter((a) => a.severity === alarmSeverityFilter.value)
})

const plantNodes = computed(() => {
  const pts = upstreamWithMeta.value.filter((u) => u.category === '电厂')
  const groups = [
    { key: 'beihai', title: '北海热电厂', match: (u) => String(u.sub_category || u.display_name || '').includes('北海') },
    { key: 'xianghai', title: '香海热电厂', match: (u) => String(u.sub_category || u.display_name || '').includes('香海') },
  ]
  return groups.map((g) => {
    const items = pts.filter(g.match)
    const temps = items.map((x) => Number(x.temp)).filter((n) => Number.isFinite(n) && n > 0)
    const hourHeat = items.reduce((acc, x) => acc + (Number(x.hour_heat_gj) || 0), 0)
    const running = items.some((x) => (Number(x.flow) || 0) > 1 || (Number(x.heat) || 0) > 1 || (Number(x.hour_heat_gj) || 0) > 1)
      || (hourHeat > 1 || (temps.length > 0 && Math.max(...temps) > 120))
    const severity = items.some((x) => x._severity === 'critical') ? 'critical' : (items.some((x) => x._severity === 'warning') ? 'warning' : 'normal')
    return {
      key: g.key,
      title: g.title,
      count: items.length,
      hourHeat: items.length ? hourHeat : null,
      avgTemp: temps.length ? temps.reduce((a, b) => a + b, 0) / temps.length : null,
      running,
      severity,
    }
  })
})

const hubNodes = computed(() => {
  const pts = upstreamWithMeta.value.filter((u) => u.category === '首站' || u.category === '网口')
  const defs = [
    {
      key: 'b2',
      title: '北海#2首站/北网',
      match: (u) => {
        const nm = `${u.sub_category || ''} ${u.display_name || ''}`
        return /北海#2|北网|北海南网/.test(nm) && !/香-北/.test(nm)
      },
    },
    {
      key: 'b1',
      title: '北海#1/水炉首站',
      match: (u) => {
        const nm = `${u.sub_category || ''} ${u.display_name || ''}`
        return /北海#1|水炉|厂界|中心区|东环|南环|造船（北）/.test(nm) && !/香海/.test(nm)
      },
    },
    {
      key: 'xh',
      title: '香海首站/低真空',
      match: (u) => {
        const nm = `${u.sub_category || ''} ${u.display_name || ''}`
        return /香海|香-北联络|造船（香）/.test(nm)
      },
    },
  ]
  return defs.map((d) => {
    const items = pts.filter(d.match)
    const temps = items.map((x) => Number(x.temp)).filter((n) => Number.isFinite(n) && n > 0)
    const flows = items.map((x) => Number(x.flow)).filter((n) => Number.isFinite(n) && n > 0)
    const severity = items.some((x) => x._severity === 'critical') ? 'critical' : (items.some((x) => x._severity === 'warning') ? 'warning' : 'normal')
    return {
      key: d.key,
      title: d.title,
      count: items.length,
      maxTemp: temps.length ? Math.max(...temps) : null,
      sumFlow: flows.length ? flows.reduce((a, b) => a + b, 0) : null,
      severity,
    }
  })
})

const rdfzBlocks = computed(() => {
  const list = reportData.value.group_summaries?.by_rdfz || []
  const sevMap = new Map()
  for (const s of stationsWithMeta.value) {
    const cur = sevMap.get(s.rdfz) || 'normal'
    if (s._severity === 'critical') sevMap.set(s.rdfz, 'critical')
    else if (s._severity === 'warning' && cur === 'normal') sevMap.set(s.rdfz, 'warning')
  }
  return list.map((g) => ({
    ...g,
    severity: sevMap.get(g.group_name) || 'normal',
  }))
})

const centerOptions = computed(() => {
  const map = new Map()
  for (const s of reportData.value.stations || []) {
    if (!map.has(s.center_id)) map.set(s.center_id, s.center_name)
  }
  return Array.from(map.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.id - b.id)
})

const filteredStations = computed(() => {
  const kw = stationKeyword.value.trim().toLowerCase()
  return stationsWithMeta.value.filter((s) => {
    if (selectedRdfz.value && s.rdfz !== selectedRdfz.value) return false
    if (stationCenterFilter.value && String(s.center_id) !== stationCenterFilter.value) return false
    if (stationStatusFilter.value === 'CRITICAL' && s._severity !== 'critical') return false
    if (stationStatusFilter.value === 'WARN' && s._severity !== 'warning') return false
    if (stationStatusFilter.value === 'OFFLINE' && s._severity !== 'offline') return false
    if (stationStatusFilter.value === 'COLD' && !(s.avg_room_temp !== null && s.avg_room_temp < 18)) return false
    if (kw && !`${s.name || ''} ${s.branch_name || ''} ${s.center_name || ''}`.toLowerCase().includes(kw)) return false
    return true
  })
})

const filteredUpstream = computed(() => {
  const kw = upstreamKeyword.value.trim().toLowerCase()
  return upstreamWithMeta.value.filter((u) => {
    if (upstreamCategoryFilter.value && u.category !== upstreamCategoryFilter.value) return false
    if (kw && !`${u.display_name || ''} ${u.sub_category || ''}`.toLowerCase().includes(kw)) return false
    return true
  })
})

const filteredMerchants = computed(() => {
  const kw = merchantKeyword.value.trim().toLowerCase()
  return merchantsWithMeta.value.filter((m) => {
    if (selectedRdfz.value && m.rdfz !== selectedRdfz.value) return false
    if (merchantStatusFilter.value === 'ACTIVE' && !(m.heat > 0)) return false
    if (merchantStatusFilter.value === 'ABNORMAL' && m._severity === 'normal') return false
    if (kw && !`${m.name || ''} ${m.branch_name || ''}`.toLowerCase().includes(kw)) return false
    return true
  })
})

const stationSort = useTableSort(filteredStations, {
  center_name: (s) => `${s.center_name}/${s.rdfz}`,
})
const upstreamSort = useTableSort(filteredUpstream)
const merchantSort = useTableSort(filteredMerchants, {
  branch_name: (m) => `${m.rdfz}/${m.branch_name}`,
})

function toggleRdfz(name) {
  selectedRdfz.value = selectedRdfz.value === name ? '' : name
  navKind.value = 'stations'
  if (filteredStations.value.length && selectedTarget.value?.raw?.rdfz !== selectedRdfz.value) {
    openStationFaceplate(filteredStations.value[0])
  }
}

function toggleStatusFilter(code) {
  navKind.value = 'stations'
  stationStatusFilter.value = stationStatusFilter.value === code ? 'ALL' : code
}

function onSelectPlant(plant) {
  navKind.value = 'upstream'
  upstreamCategoryFilter.value = '电厂'
  upstreamKeyword.value = plant.key === 'beihai' ? '北海' : '香海'
  if (filteredUpstream.value.length) {
    openUpstreamFaceplate(filteredUpstream.value[0])
  }
}

function onSelectHub(hub) {
  navKind.value = 'upstream'
  upstreamCategoryFilter.value = ''
  upstreamKeyword.value = hub.key === 'b1' ? '北海#1' : (hub.key === 'b2' ? '北海#2' : '香海')
  if (filteredUpstream.value.length) {
    openUpstreamFaceplate(filteredUpstream.value[0])
  }
}

function onOpenMerchants() {
  navKind.value = 'merchants'
  if (mainCanvasMode.value === 'aux_table') mainCanvasMode.value = 'unit_pid'
  const firstMc = filteredMerchants.value.find((m) => m.online && (m.heat > 0 || m.hour_heat_gj > 0)) || filteredMerchants.value[0]
  if (firstMc) openMerchantFaceplate(firstMc)
}

function selectStationFromNav(s) {
  if (mainCanvasMode.value === 'aux_table') mainCanvasMode.value = 'unit_pid'
  openStationFaceplate(s)
}

function selectUpstreamFromNav(u) {
  if (mainCanvasMode.value === 'aux_table') mainCanvasMode.value = 'unit_pid'
  openUpstreamFaceplate(u)
}

function selectMerchantFromNav(m) {
  if (mainCanvasMode.value === 'aux_table') mainCanvasMode.value = 'unit_pid'
  openMerchantFaceplate(m)
}

function focusAlarm(alm) {
  alarmDrawerOpen.value = false
  mainCanvasMode.value = 'unit_pid'
  if (alm.kind === 'station') {
    navKind.value = 'stations'
    openStationFaceplate(alm.raw)
  } else {
    navKind.value = 'upstream'
    openUpstreamFaceplate(alm.raw)
  }
}

async function openStationFaceplate(s) {
  const notesList = Object.entries(s.field_notes || {})
    .filter(([, v]) => Boolean(v))
    .map(([, v]) => v)
  selectedTarget.value = {
    kind: 'station',
    id: s.station_id,
    tagId: `STN-${String(s.station_id).slice(0, 6).toUpperCase()}`,
    title: s.name,
    subtitle: `${s.center_name} · ${s.rdfz} · ${s.branch_name}`,
    severity: s._severity,
    modeLabel: s._modeLabel,
    notesList,
    raw: s,
  }
  fpTempsLoaded.value = false
  fpTempDevices.value = []
  fpTrendLoading.value = true
  try {
    const dateStr = selectedDate.value || meta.value?.date || todayLocalIso()
    const res = await fetchEntityTrend24h({ date: dateStr, scope: 'station', key: s.station_id, mode: mode.value })
    fpTrendRows.value = res?.data?.trend_24h || []
  } catch {
    fpTrendRows.value = []
  } finally {
    fpTrendLoading.value = false
  }
}

async function openUpstreamFaceplate(u) {
  const isSteam = /汽|蒸汽|主汽|抽汽|排汽|调门|母管/.test(`${u.display_name || ''} ${u.sub_category || ''}`)
  const notesList = Object.entries(u.field_notes || {})
    .filter(([, v]) => Boolean(v))
    .map(([, v]) => v)
  selectedTarget.value = {
    kind: 'upstream',
    id: `${u.data_zone}:${u.source_name}`,
    tagId: `UP-${String(u.data_zone || '').replace('_dict', '').toUpperCase()}`,
    title: u.display_name,
    subtitle: `${u.category} · ${u.sub_category || u.source_name}`,
    severity: u._severity,
    modeLabel: u._modeLabel,
    isSteam,
    notesList,
    raw: u,
  }
  fpTrendLoading.value = true
  try {
    const dateStr = selectedDate.value || meta.value?.date || todayLocalIso()
    const res = await fetchUpstreamTrend24h({ date: dateStr, data_zone: u.data_zone, source_name: u.source_name })
    fpTrendRows.value = res?.data || []
  } catch {
    fpTrendRows.value = []
  } finally {
    fpTrendLoading.value = false
  }
}

async function openMerchantFaceplate(m) {
  const isSteam = String(m.rdry || '').trim() === '蒸汽'
  selectedTarget.value = {
    kind: 'merchant',
    id: m.merchant_id,
    tagId: `MC-${String(m.merchant_id).slice(0, 6).toUpperCase()}`,
    title: m.name,
    subtitle: `${m.rdfz || '-'} · ${m.branch_name || '-'} · ${m.rdry || '高温水'}`,
    severity: m._severity,
    modeLabel: m._modeLabel,
    isSteam,
    notesList: m._notes || [],
    raw: m,
  }
  fpTrendLoading.value = true
  try {
    const dateStr = selectedDate.value || meta.value?.date || todayLocalIso()
    const res = await fetchMerchantTrend24h({ date: dateStr, merchant_id: m.merchant_id, mode: mode.value })
    fpTrendRows.value = res?.data || []
  } catch {
    fpTrendRows.value = []
  } finally {
    fpTrendLoading.value = false
  }
}

async function loadFpTempDevices() {
  if (selectedTarget.value?.kind !== 'station') return
  try {
    const res = await fetchStationTempDevices({
      date: selectedDate.value || meta.value?.date,
      hour: selectedHour.value,
      station_id: selectedTarget.value.id,
    })
    fpTempDevices.value = res?.data || []
    fpTempsLoaded.value = true
  } catch {
    fpTempDevices.value = []
    fpTempsLoaded.value = true
  }
}

async function loadReport() {
  const reqId = ++reportSeq
  if (reportAbortCtrl) reportAbortCtrl.abort()
  reportAbortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { mode: mode.value }
    if (selectedDate.value) params.date = selectedDate.value
    if (selectedHour.value !== null && selectedHour.value !== undefined) params.hour = selectedHour.value
    const res = await fetchHourlyReport(params, reportAbortCtrl ? { signal: reportAbortCtrl.signal } : {})
    if (reqId !== reportSeq) return
    if (res?.data) {
      reportData.value = res.data
      if (res.data.meta?.date && !selectedDate.value) selectedDate.value = res.data.meta.date
      if (res.data.meta?.hour !== undefined && selectedHour.value === null) selectedHour.value = Number(res.data.meta.hour)

      await nextTick()
      if (selectedTarget.value?.kind === 'station') {
        const refreshed = stationsWithMeta.value.find((x) => x.station_id === selectedTarget.value.id)
        if (refreshed) openStationFaceplate(refreshed)
      } else if (selectedTarget.value?.kind === 'upstream') {
        const refreshed = upstreamWithMeta.value.find((x) => `${x.data_zone}:${x.source_name}` === selectedTarget.value.id)
        if (refreshed) openUpstreamFaceplate(refreshed)
      } else if (selectedTarget.value?.kind === 'merchant') {
        const refreshed = merchantsWithMeta.value.find((x) => x.merchant_id === selectedTarget.value.id)
        if (refreshed) openMerchantFaceplate(refreshed)
      } else if (stationsWithMeta.value.length) {
        const firstSt = stationsWithMeta.value.find((s) => s.online && s._severity === 'normal')
          || stationsWithMeta.value[0]
        if (firstSt) openStationFaceplate(firstSt)
      }
    }
  } catch (err) {
    if (err?.name === 'AbortError' || reqId !== reportSeq) return
    errorMsg.value = err.message || '加载失败'
  } finally {
    if (reqId === reportSeq) loading.value = false
  }
}

function onDateChange() {
  selectedHour.value = null
  loadReport()
}

function jumpToLatest() {
  selectedDate.value = ''
  selectedHour.value = null
  loadReport()
}

const canStepPrevHour = computed(() => {
  if (selectedHour.value === null) return false
  if (Number(selectedHour.value) > 0) return true
  return (selectedDate.value || todayLocalIso()) > MIN_PLATFORM_DATE
})

const canStepNextHour = computed(() => {
  if (selectedHour.value === null) return false
  if (Number(selectedHour.value) < 23) return true
  return (selectedDate.value || todayLocalIso()) < todayLocalIso()
})

function stepHour(delta) {
  if (selectedHour.value === null) return
  const h = Number(selectedHour.value)
  const d = selectedDate.value || todayLocalIso()
  if (delta < 0) {
    if (h > 0) {
      selectedHour.value = h - 1
      loadReport()
    } else {
      const prev = shiftIsoDate(d, -1)
      if (prev >= MIN_PLATFORM_DATE) {
        selectedDate.value = prev
        selectedHour.value = 23
        loadReport()
      }
    }
    return
  }
  if (h < 23) {
    selectedHour.value = h + 1
    loadReport()
  } else if (d < todayLocalIso()) {
    selectedDate.value = shiftIsoDate(d, 1)
    selectedHour.value = 0
    loadReport()
  }
}

function switchMode(m) {
  mode.value = m
  loadReport()
}

function toggleFullscreen() {
  if (!dcsRootEl.value) return
  if (!document.fullscreenElement) {
    dcsRootEl.value.requestFullscreen?.().catch(() => {
      isFullscreen.value = !isFullscreen.value
    })
  } else {
    document.exitFullscreen?.()
  }
}

function onFullscreenChange() {
  isFullscreen.value = Boolean(document.fullscreenElement)
}

onMounted(() => {
  document.addEventListener('fullscreenchange', onFullscreenChange)
  loadReport()
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  reportAbortCtrl?.abort()
})
</script>

<style scoped>
.dcs-shell {
  min-height: 100vh;
  background: #d3d9e2;
  color: #16202e;
  font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
}

.dcs-shell.is-fullscreen {
  padding: 10px 14px;
  overflow-y: auto;
}

.dcs-main {
  max-width: 1580px;
  margin: 0 auto;
  padding: 12px 16px 32px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dcs-panel {
  background: #e5eaf0;
  border: 1px solid #aeb9c7;
  box-shadow: inset 1px 1px 0 #f5f7fa;
  border-radius: 3px;
}

.dcs-topbar {
  padding: 8px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.dcs-tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #233042;
  color: #e2e8f0;
  padding: 4px 10px;
  border-radius: 2px;
  font-family: Consolas, monospace;
  font-size: 11px;
  font-weight: 700;
}

.status-led { width: 8px; height: 8px; border-radius: 50%; }
.led-ok { background: #38bdf8; }
.led-busy { background: #f59e0b; }

.topbar-title-block h1 { margin: 0; font-size: 16px; font-weight: 700; color: #0f172a; }
.meta-mono { font-size: 12px; color: #475569; font-variant-numeric: tabular-nums; }

.topbar-controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.dcs-step-group, .dcs-mode-group { display: inline-flex; align-items: center; gap: 2px; }

.dcs-btn, .dcs-btn-sq, .dcs-btn-xs {
  border: 1px solid #96a4b5;
  background: linear-gradient(180deg, #f3f6f9 0%, #dde3eb 100%);
  color: #1e293b;
  font-size: 12px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 2px;
  cursor: pointer;
}
.dcs-btn-sq { padding: 5px 8px; }
.dcs-btn-xs { padding: 3px 8px; font-size: 11px; }
.dcs-btn:hover:not(:disabled), .dcs-btn-sq:hover:not(:disabled), .dcs-btn-xs:hover:not(:disabled) { background: #cfd8e3; }
.dcs-btn.is-active, .dcs-btn-xs.is-active { background: #2b4c6f; border-color: #1e3a5f; color: #ffffff; }
.dcs-btn.is-raw { background: #b91c1c; border-color: #7f1d1d; color: #ffffff; }

.dcs-select, .dcs-select-sm, .dcs-input-full {
  border: 1px solid #96a4b5;
  background: #f8fafc;
  color: #0f172a;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 2px;
}
.dcs-select-sm { padding: 3px 5px; font-size: 11px; flex: 1; min-width: 0; }
.dcs-input-full { width: 100%; box-sizing: border-box; font-size: 11.5px; padding: 4px 7px; }

/* Alarm Banner */
.dcs-alarm-banner {
  padding: 6px 12px;
  background: #dce2ea;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}
.alarm-counts { display: flex; align-items: center; gap: 6px; }
.alm-pill {
  padding: 3px 9px;
  border-radius: 2px;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid #94a3b8;
}
.alm-pill.alm-crit { border-color: #dc2626; color: #991b1b; background: #fee2e2; }
.alm-pill.alm-crit.active { background: #dc2626; color: #ffffff; }
.alm-pill.alm-warn { border-color: #d97706; color: #92400e; background: #fef3c7; }
.alm-pill.alm-warn.active { background: #d97706; color: #ffffff; }
.alm-pill.alm-oos { border-color: #64748b; color: #334155; background: #e2e8f0; }
.alm-pill.alm-oos.active { background: #475569; color: #ffffff; }

.alarm-ticker { flex: 1; min-width: 240px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.alarm-strip-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 2px;
  font-size: 11.5px;
  cursor: pointer;
  border: 1px solid transparent;
  max-width: 340px;
}
.alarm-strip-item.sev-critical { background: #fee2e2; border-color: #ef4444; color: #7f1d1d; }
.alarm-strip-item.sev-warning { background: #fef3c7; border-color: #f59e0b; color: #78350f; }
.alm-code { font-family: Consolas, monospace; font-weight: 700; font-size: 10.5px; padding: 0 4px; background: rgba(255, 255, 255, 0.7); border-radius: 2px; }
.alm-msg { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.alarm-clear { font-size: 12px; color: #2f5e4e; font-weight: 600; }

.alarm-drawer { padding: 10px 12px; }
.alarm-table-scroll { max-height: 220px; overflow: auto; border: 1px solid #b6c0cc; background: #f1f4f8; }
.dcs-error-strip { padding: 8px 12px; background: #fee2e2; border: 1px solid #ef4444; color: #991b1b; font-size: 12.5px; font-weight: 600; }

/* Stage Switch & PFD */
.stage-switch-panel { padding: 8px 12px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
.stage-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.dcs-tab {
  border: 1px solid #96a4b5;
  background: #dce2ea;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  padding: 5px 11px;
  border-radius: 2px;
  cursor: pointer;
}
.dcs-tab.active { background: #233042; border-color: #0f172a; color: #ffffff; }

.panel-right-chips { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.l1-chip { background: #f1f5f9; border: 1px solid #b6c0cc; padding: 2px 8px; border-radius: 2px; font-size: 11.5px; font-variant-numeric: tabular-nums; }
.filter-chip { display: inline-flex; align-items: center; gap: 6px; background: #dbeafe; border: 1px solid #60a5fa; color: #1e3a8a; padding: 2px 8px; border-radius: 2px; font-size: 11.5px; }
.chip-clear { border: none; background: transparent; color: #1e3a8a; font-weight: 700; cursor: pointer; }

/* 3-Pane DCS Operator Console */
.dcs-console-grid {
  display: grid;
  grid-template-columns: 268px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.dcs-console-grid.has-faceplate {
  grid-template-columns: 268px minmax(0, 1fr) 330px;
}

/* 左侧微缩点阵导览 */
.nav-rail {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  height: 580px;
}

.rail-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3px;
}

.rail-tab {
  border: 1px solid #96a4b5;
  background: #dce2ea;
  color: #334155;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 2px;
  border-radius: 2px;
  cursor: pointer;
}

.rail-tab.active {
  background: #233042;
  color: #ffffff;
  border-color: #0f172a;
}

.rail-filters { display: flex; flex-direction: column; gap: 5px; }
.rail-selects { display: flex; gap: 4px; }

.micro-list {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #b6c0cc;
  background: #eef2f6;
  display: flex;
  flex-direction: column;
}

.micro-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 7px;
  border: none;
  border-bottom: 1px solid #dce2ea;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font-size: 11.5px;
  color: #1e293b;
  font-variant-numeric: tabular-nums;
}

.micro-item:hover { background: #dfe6ef; }
.micro-item.active { background: #cfe0f5; font-weight: 700; }
.micro-item.sev-critical { background: #fef2f2; }
.micro-item.sev-critical.active { background: #fecaca; }
.micro-item.sev-warning { background: #fffbeb; }
.micro-item.sev-offline { color: #64748b; }
.micro-item.static-micro { cursor: default; }

.micro-led { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.micro-led.led-normal { background: #3b6b8f; }
.micro-led.led-warning { background: #d97706; }
.micro-led.led-critical { background: #dc2626; }
.micro-led.led-offline { background: #94a3b8; }

.micro-name {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.micro-val, .micro-temp {
  font-family: Consolas, monospace;
  font-size: 10.5px;
  color: #475569;
  flex-shrink: 0;
}

/* 中央工艺组态舞台 */
.center-stage {
  padding: 10px 12px;
  min-width: 0;
}

.aux-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.aux-head h3 { margin: 0; font-size: 13px; color: #0f172a; }

.l2-table-scroll {
  max-height: 520px;
  overflow: auto;
  border: 1px solid #b6c0cc;
  background: #f4f6f9;
}

.dcs-table { width: 100%; border-collapse: collapse; font-size: 12px; font-variant-numeric: tabular-nums; }
.dcs-table th {
  position: sticky; top: 0; z-index: 2;
  background: #cfd7e2; color: #1e293b; font-weight: 700;
  text-align: left; padding: 6px 8px; border-bottom: 1px solid #96a4b5; white-space: nowrap;
}
.dcs-table td { padding: 5px 8px; border-bottom: 1px solid #dce2ea; white-space: nowrap; }
.dcs-table tr.clickable { cursor: pointer; }
.dcs-table tr.clickable:hover { background: #e2e8f0; }
.dcs-table tr.row-selected { background: #dbeafe !important; }

.mono { font-family: Consolas, monospace; }
.bold { font-weight: 700; color: #0f172a; }
.cold-txt { color: #b91c1c !important; font-weight: 700; }

.sev-badge {
  display: inline-block;
  font-family: Consolas, monospace;
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 2px;
}
.sev-badge.sev-normal { background: #dce6ef; color: #24455e; }
.sev-badge.sev-warning { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
.sev-badge.sev-critical { background: #fee2e2; color: #991b1b; border: 1px solid #ef4444; }
.sev-badge.sev-offline { background: #cbd5e1; color: #475569; }

/* Faceplate */
.faceplate-panel {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fp-header { border-bottom: 1px solid #b6c0cc; padding-bottom: 8px; }
.fp-tag-row { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-bottom: 4px; }
.fp-tag-id { font-family: Consolas, monospace; font-size: 11px; font-weight: 700; background: #233042; color: #e2e8f0; padding: 2px 6px; border-radius: 2px; }
.fp-mode-pill { font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 2px; }
.fp-mode-pill.sev-normal { background: #dce6ef; color: #1e3a5f; }
.fp-mode-pill.sev-warning { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; }
.fp-mode-pill.sev-critical { background: #fee2e2; color: #991b1b; border: 1px solid #ef4444; }
.fp-mode-pill.sev-offline { background: #cbd5e1; color: #334155; }
.fp-title { margin: 0; font-size: 14.5px; font-weight: 700; color: #0f172a; }
.fp-subtitle { margin: 2px 0 0; font-size: 11px; color: #475569; }

.fp-section {
  background: #eef2f6;
  border: 1px solid #bac4d0;
  border-radius: 2px;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.fp-sec-title {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 11px; font-weight: 700; color: #334155;
  border-bottom: 1px dashed #cbd5e1; padding-bottom: 4px;
}
.fp-gauges { display: flex; flex-direction: column; gap: 7px; }
.fp-kv-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.fp-kv { background: #e3e8ef; border: 1px solid #c5ced9; padding: 4px 7px; border-radius: 2px; display: flex; flex-direction: column; }
.fp-kv span { font-size: 10px; color: #475569; }
.fp-kv strong { font-family: Consolas, monospace; font-size: 12px; color: #0f172a; }

.fp-alarm-notes { display: flex; flex-direction: column; gap: 4px; }
.fp-note-item { font-size: 11px; background: #fef3c7; border: 1px solid #f59e0b; color: #78350f; padding: 4px 6px; border-radius: 2px; line-height: 1.4; }
.fp-temp-list { max-height: 140px; overflow-y: auto; border-top: 1px solid #cbd5e1; padding-top: 5px; display: flex; flex-direction: column; gap: 3px; }
.fp-temp-row { display: flex; justify-content: space-between; font-size: 11px; padding: 2px 4px; background: #e5eaf0; }
.fp-temp-addr { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px; }
.muted-mini { font-size: 10.5px; color: #64748b; }

@media (max-width: 1200px) {
  .dcs-console-grid,
  .dcs-console-grid.has-faceplate {
    grid-template-columns: 1fr;
  }
  .nav-rail { height: 280px; }
}

@media (max-width: 768px) {
  .dcs-main { padding: 10px 8px 24px; }
  .desktop-only { display: none; }
}
</style>
