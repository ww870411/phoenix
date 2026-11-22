<template>
  <div class="shp-page-root">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      <PlatformSubNav current="hourly_report" />

      <!-- 吸顶控制台：日期 + 紧凑时段选择器 + 口径切换 + 操作按钮 -->
      <section class="card elevated control-bar">
        <div class="control-top">
          <div class="control-left">
            <h2>主城区智慧供热 · 逐小时精细化运行报告</h2>
            <span class="slot-badge">
              断面：<strong>{{ meta.biz_hour_label || (selectedDate ? `${selectedDate} ${selectedHour == null ? '--' : String(selectedHour).padStart(2, '0')}:00` : '定位最新小时…') }}</strong>
            </span>
            <span v-if="meta.last_run?.finished_at" class="run-meta">
              最近采集：{{ meta.last_run.finished_at }}（{{ meta.station_records_count }}/242 站）
            </span>
          </div>
          <div class="control-right">
            <label class="inline-field">
              <span>日期</span>
              <DateStepPicker v-model="selectedDate" aria-label="选择报告日期" @change="onDateChange" />
            </label>
            <div class="hour-picker-group" role="group" aria-label="小时时段切换">
              <button
                class="hour-step-btn"
                type="button"
                title="上一小时（00:00 时自动切至前一天 23:00）"
                :disabled="!canStepPrevHour"
                @click="stepHour(-1)"
              >
                ◀
              </button>
              <select
                v-model.number="selectedHour"
                class="ctrl-input hour-select"
                aria-label="选择小时时段"
                @change="loadReport"
              >
                <option v-if="selectedHour === null" :value="null" disabled>定位最新…</option>
                <option
                  v-for="item in trend24h"
                  :key="item.hour"
                  :value="item.hour"
                >
                  {{ item.label }}{{ item.has_data ? '' : ' (暂无)' }}
                </option>
              </select>
              <button
                class="hour-step-btn"
                type="button"
                title="下一小时（23:00 时自动切至后一天 00:00）"
                :disabled="!canStepNextHour"
                @click="stepHour(1)"
              >
                ▶
              </button>
              <button
                class="hour-action-btn"
                type="button"
                title="跳转最新有数据时段"
                :disabled="loading"
                @click="jumpToLatest"
              >
                最新
              </button>
            </div>
            <div class="mode-switch" role="group" aria-label="数据口径切换">
              <button
                type="button"
                :class="['mode-btn', { active: mode === 'clean' }]"
                title="默认展示突发异常已修正、表底已校准数据"
                @click="switchMode('clean')"
              >
                修正后数据
              </button>
              <button
                type="button"
                :class="['mode-btn', { 'raw-active': mode === 'raw' }]"
                title="一键还原未经清洗与折算的原始采集数据"
                @click="switchMode(mode === 'raw' ? 'clean' : 'raw')"
              >
                {{ mode === 'raw' ? '✨ 恢复修正后数据' : '🔄 一键还原原始数据' }}
              </button>
            </div>
            <button
              class="btn secondary btn-sm"
              type="button"
              :disabled="collecting || calibrating"
              @click="handleCollectNow"
            >
              {{ collecting ? '采集中…' : '⚡ 采集上游/商户/室温' }}
            </button>
            <button
              class="btn secondary btn-sm"
              type="button"
              :disabled="calibrating || collecting"
              @click="handleCalibNow"
            >
              {{ calibrating ? '并行校准中…' : '📏 校准换热站表底' }}
            </button>
            <button
              class="btn primary btn-sm"
              type="button"
              :disabled="loading"
              title="导出当天 24 小时逐时统计、横向矩阵、突发记录与当前小时明细 Excel"
              @click="handleExport"
            >
              📥 导出当日逐小时报告
            </button>
          </div>
        </div>
      </section>

      <div v-if="mode === 'raw'" class="raw-mode-banner">
        <span>⚠️ 当前已一键还原显示 <strong>原始采集数据</strong>（未剔除突发跳变尖刺与表底单位倍数），红色标注代表突发异常原始极值。</span>
        <button class="btn primary btn-sm" type="button" @click="switchMode('clean')">✨ 恢复修正后数据</button>
      </div>

      <div v-if="notice.text" :class="['notice-banner', notice.type]">{{ notice.text }}</div>

      <div v-if="gapStatus && (gapStatus.has_gaps || gapStatus.running)" class="gap-banner">
        <div class="gap-banner-text">
          <template v-if="gapStatus.running">
            <strong>🩹 正在后台自动补足停机真空期历史数据…</strong>
            <span class="gap-step-inline">
              步骤 {{ gapStatus.current_step_index || 0 }}/{{ gapStatus.total_steps || 0 }}
              <template v-if="gapStatus.current_step_label"> · {{ gapStatus.current_step_label }}</template>
            </span>
          </template>
          <template v-else>
            <strong>⚠️ 检测到停机真空期数据缺口：</strong>
            <span>
              涉及日期 {{ (gapStatus.missing_dates || []).join('、') || '-' }}
              （换热站缺 {{ gapStatus.tracks?.stations?.missing_count || 0 }} 时 · 上游缺 {{ gapStatus.tracks?.upstream?.missing_count || 0 }} 时 · 商业缺 {{ gapStatus.tracks?.merchant_hourly?.missing_count || 0 }} 时）
            </span>
          </template>
        </div>
        <div class="gap-banner-actions">
          <button
            class="btn secondary btn-sm"
            type="button"
            @click="openGapDetailDrawer"
          >
            📋 查看详情
          </button>
          <button
            class="btn secondary btn-sm"
            type="button"
            :disabled="recovering || gapStatus.running"
            @click="handleGapRecoverNow"
          >
            {{ recovering || gapStatus.running ? '补采执行中…' : '🩹 一键补足真空期' }}
          </button>
          <button class="btn secondary btn-sm" type="button" @click="loadGapStatus">刷新状态</button>
        </div>
      </div>

      <!-- 7 张全网核心指标 KPI 卡片 -->
      <section class="kpi-grid">
        <div class="card elevated kpi-card">
          <span class="kpi-label">当前室外气温</span>
          <strong class="kpi-val">{{ fmt(kpis.outdoor_temp, ' ℃') }}</strong>
          <span class="kpi-sub">近端实况气象数据</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">全网在网面积</span>
          <strong class="kpi-val">{{ fmt(kpis.covered_area_wan, ' 万㎡') }}</strong>
          <span class="kpi-sub">在线 {{ kpis.online_stations ?? 0 }}/{{ kpis.total_stations ?? 242 }} 站（{{ kpis.missing_area_count ?? 32 }}站待补面积）</span>
        </div>
        <div class="card elevated kpi-card highlight">
          <span class="kpi-label">小时累计供热量</span>
          <strong class="kpi-val">
            <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.hour_heat_gj, ' GJ')" :note="kpis.anomalies?.hour_heat_gj?.note" />
          </strong>
          <span class="kpi-sub">
            瞬时负荷 <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.instant_load_gjh, ' GJ/h')" :note="kpis.anomalies?.instant_load_gjh?.note" />
          </span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">实时折算热指标</span>
          <strong class="kpi-val">
            <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.heat_index_wm2, ' W/㎡')" :note="kpis.anomalies?.heat_index_wm2?.note" />
          </strong>
          <span class="kpi-sub">
            万平耗热 <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.heat_per_wan_gj, ' GJ/万㎡·h')" :note="kpis.anomalies?.heat_per_wan_gj?.note" />
          </span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">小时累计补水量</span>
          <strong class="kpi-val">
            <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.hour_water_t, ' t')" :note="kpis.anomalies?.hour_water_t?.note" />
          </strong>
          <span class="kpi-sub">
            万平补水 <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.water_per_wan_t, ' t/万㎡')" :note="kpis.anomalies?.water_per_wan_t?.note" />
          </span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">小时累计电耗</span>
          <strong class="kpi-val">{{ fmt(kpis.hour_elec_kwh, ' kWh') }}</strong>
          <span class="kpi-sub">万平电耗 {{ fmt(kpis.elec_per_wan_kwh, ' kWh/万㎡') }}</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">一网流量加权均温</span>
          <strong class="kpi-val">
            <AnomalyBadgeValue placement="bottom" :text="`${fmt(kpis.avg_sup_temp)} / ${fmt(kpis.avg_ret_temp)} ℃`" :note="kpis.anomalies?.avg_sup_temp?.note" />
          </strong>
          <span class="kpi-sub">
            加权温差 <AnomalyBadgeValue placement="bottom" :text="fmt(kpis.avg_temp_diff, ' ℃')" :note="kpis.anomalies?.avg_temp_diff?.note" />
          </span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">全网真实平均室温</span>
          <strong class="kpi-val text-ok">{{ fmt(kpis.avg_room_temp, ' ℃') }}</strong>
          <span class="kpi-sub">达标率 {{ fmt(kpis.temp_pass_rate_pct, '%') }} · 舒适率 {{ fmt(kpis.temp_comfort_rate_pct, '%') }}</span>
        </div>
      </section>

      <!-- 24小时趋势图 -->
      <section ref="chartSectionEl" class="card elevated chart-section">
        <div class="section-head">
          <div class="head-title-group">
            <h3>
              {{ selectedEntity ? `${selectedEntity.name} · 24 小时运行负荷与供回温走势` : '当日 24 小时运行负荷与供回温走势' }}
            </h3>
            <span v-if="selectedEntity" class="slot-badge">
              {{ selectedEntity.scopeLabel }} · {{ selectedEntity.stationCount }} 站
            </span>
            <span v-else class="run-meta">（点击下方主体或换热站行，可切换显示该主体柱形图与曲线）</span>
            <span v-if="entityLoading" class="run-meta">正在加载主体走势…</span>
          </div>
          <div class="head-actions-group">
            <button
              v-if="selectedEntity"
              class="btn secondary btn-xs"
              type="button"
              @click="clearSelectedEntity"
            >
              ↩ 返回全网走势
            </button>
            <button class="btn ghost btn-xs" type="button" @click="showTrendChart = !showTrendChart">
              {{ showTrendChart ? '收起图表' : '展开图表' }}
            </button>
          </div>
        </div>
        <div v-show="showTrendChart" class="chart-pair">
          <div ref="heatChartEl" class="chart-box"></div>
          <div ref="tempChartEl" class="chart-box"></div>
        </div>
      </section>

      <!-- 四维切换报表 -->
      <section class="card elevated report-tabs-card">
        <div class="tab-bar">
          <button
            v-for="tab in reportTabs"
            :key="tab.key"
            type="button"
            :class="['tab-btn', { active: activeTab === tab.key }]"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- Tab 1: 热源与首站 -->
        <div v-if="activeTab === 'upstream'" class="tab-panel">
          <div class="filter-bar">
            <select v-model="upstreamFilter.category" class="ctrl-input">
              <option value="">全部类别</option>
              <option value="电厂">电厂</option>
              <option value="首站">首站</option>
              <option value="网口">网口汇总</option>
            </select>
            <input v-model="upstreamFilter.keyword" type="search" class="ctrl-input" placeholder="搜索测点名称…" />
            <label class="check-inline">
              <input v-model="upstreamFilter.onlyCore" type="checkbox" />
              <span>仅看《工况一览》82 核心点</span>
            </label>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="类别" sort-key="category" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh label="子类" sort-key="sub_category" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh class="sticky-col" label="测点标准名称" sort-key="display_name" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh label="采集时间" sort-key="source_time" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh label="温度 (℃)" sort-key="temp" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh label="压力 (MPa)" sort-key="pressure" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh label="瞬时流量" sort-key="flow" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh label="瞬时热量" sort-key="heat" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh label="小时积分 (GJ)" sort-key="hour_heat_gj" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                  <SortableTh label="数据来源" sort-key="value_source" :sort-state="upstreamSort.state" @sort="upstreamSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-if="filteredUpstream.length === 0">
                  <td colspan="10" class="empty-td">当前时刻暂无上游数据，请点击右上角“立即采集当前时段”</td>
                </tr>
                <tr v-for="u in upstreamSort.sortedRows.value" :key="`${u.data_zone}_${u.source_name}`" @click="openUpstreamDrawer(u)" class="clickable-row">
                  <td>{{ u.category }}</td>
                  <td>{{ u.sub_category || '-' }}</td>
                  <td class="sticky-col font-bold">{{ u.display_name }}</td>
                  <td class="mono">{{ u.source_time || '-' }}</td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(u.temp)" :note="u.field_notes?.temp" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(u.pressure, '', 3)" :note="u.field_notes?.pressure" />
                  </td>
                  <td>{{ fmt(u.flow) }}</td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(u.heat)" :note="u.field_notes?.heat" />
                  </td>
                  <td class="font-bold">
                    <AnomalyBadgeValue :text="fmt(u.hour_heat_gj)" :note="u.field_notes?.hour_heat_gj" />
                  </td>
                  <td>
                    <span :class="['src-pill', u.value_source === 'REAL' ? 'src-real' : 'src-interp']">
                      {{ sourceLabel(u.value_source) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tab 2: 9中心 / 9大网 / 15主干 / 41支线 -->
        <div v-if="activeTab === 'groups'" class="tab-panel">
          <div class="filter-bar">
            <div class="mode-switch group-dim-switch">
              <button
                v-for="dim in groupDimensions"
                :key="dim.key"
                type="button"
                :class="['mode-btn', { active: groupDim === dim.key }]"
                @click="groupDim = dim.key"
              >
                {{ dim.label }}
              </button>
            </div>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh class="sticky-col" label="聚合主体名称" sort-key="group_name" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="在线/总站" sort-key="online_stations" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="面积 (万㎡)" sort-key="covered_area_wan" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="小时供热量 (GJ)" sort-key="hour_heat_gj" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="折算热指标 (W/㎡)" sort-key="heat_index_wm2" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="万平耗热 (GJ/万㎡)" sort-key="heat_per_wan_gj" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="小时补水 (t)" sort-key="hour_water_t" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="小时电耗 (kWh)" sort-key="hour_elec_kwh" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="加权供/回温 (℃)" sort-key="avg_sup_temp" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="平均室温 (℃)" sort-key="avg_room_temp" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                  <SortableTh label="室温达标率" sort-key="temp_pass_rate_pct" :sort-state="groupSort.state" @sort="groupSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="g in groupSort.sortedRows.value"
                  :key="g.group_key"
                  :class="[
                    'clickable-row',
                    { 'row-selected': selectedEntity?.scope === groupDim && selectedEntity?.key === String(g.group_key) },
                  ]"
                  title="点击上方展示该主体的 24 小时柱形图与供回温曲线（再次点击返回全网）"
                  @click="selectEntityTrend(groupDim, g.group_key, g.group_name, g.total_stations)"
                >
                  <td class="sticky-col font-bold">
                    {{ g.group_name }}
                    <span class="chart-hint-tag" title="点击查看24小时柱形图与曲线">📈</span>
                  </td>
                  <td>{{ g.online_stations }}/{{ g.total_stations }} ({{ g.online_rate_pct }}%)</td>
                  <td>{{ fmt(g.covered_area_wan) }}</td>
                  <td class="font-bold">
                    <AnomalyBadgeValue :text="fmt(g.hour_heat_gj)" :note="g.anomalies?.hour_heat_gj?.note" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(g.heat_index_wm2)" :note="g.anomalies?.heat_index_wm2?.note" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(g.heat_per_wan_gj)" :note="g.anomalies?.heat_per_wan_gj?.note" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(g.hour_water_t)" :note="g.anomalies?.hour_water_t?.note" />
                  </td>
                  <td>{{ fmt(g.hour_elec_kwh) }}</td>
                  <td>
                    <AnomalyBadgeValue :text="`${fmt(g.avg_sup_temp)} / ${fmt(g.avg_ret_temp)}`" :note="g.anomalies?.avg_sup_temp?.note" />
                  </td>
                  <td class="font-bold">{{ fmt(g.avg_room_temp) }}</td>
                  <td>{{ fmt(g.temp_pass_rate_pct, '%') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tab 3: 242座换热站一次网及表底精算 -->
        <div v-if="activeTab === 'stations'" class="tab-panel">
          <div class="filter-bar">
            <select v-model="stationFilter.centerId" class="ctrl-input" @change="onCenterChange">
              <option value="">全部服务中心</option>
              <option v-for="c in centerOptions" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
            </select>
            <select v-model="stationFilter.rdfz" class="ctrl-input" @change="onRdfzChange">
              <option value="">全部主干热网</option>
              <option v-for="r in stationRdfzOptions" :key="r" :value="r">{{ r }}</option>
            </select>
            <select v-model="stationFilter.branchId" class="ctrl-input">
              <option value="">全部支线网</option>
              <option v-for="b in branchOptions" :key="b.id" :value="String(b.id)">{{ b.name }}</option>
            </select>
            <select v-model="stationFilter.statusFilter" class="ctrl-input">
              <option value="">全部状态</option>
              <option value="REAL">仅在线实测</option>
              <option value="INTERP">含平滑估值</option>
              <option value="NO_AREA">缺失面积站</option>
            </select>
            <input v-model="stationFilter.keyword" type="search" class="ctrl-input" placeholder="搜索站名…" />
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh class="sticky-col" label="换热站名称" sort-key="name" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="中心 / 支线" sort-key="center_name" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="面积 (㎡)" sort-key="covered_area" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="状态" sort-key="online" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="一网供/回温 (℃)" sort-key="e3" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="一网供/回压 (MPa)" sort-key="e7" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="一网瞬时热 (GJ/h)" sort-key="e11" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="小时供热 (GJ)" sort-key="hour_heat_gj" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="热指标 (W/㎡)" sort-key="heat_index_wm2" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="补水 (t)" sort-key="e14" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="电耗 (kWh)" sort-key="hour_elec_kwh" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                  <SortableTh label="均温 (℃)" sort-key="avg_room_temp" :sort-state="stationSort.state" @sort="stationSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <template v-for="s in stationSort.sortedRows.value" :key="s.station_id">
                  <tr
                    :class="[
                      'clickable-row',
                      {
                        'row-interp': s.value_source !== 'REAL' && s.value_source !== 'NO_DATA',
                        'row-selected': selectedEntity?.scope === 'station' && selectedEntity?.key === String(s.station_id),
                      },
                    ]"
                    title="点击上方展示该换热站的 24 小时柱形图与供回温曲线（再次点击返回全网）"
                    @click="selectEntityTrend('station', s.station_id, s.name, 1)"
                  >
                    <td class="sticky-col font-bold">
                      {{ s.name }}
                      <span
                        v-if="s.value_source !== 'REAL' && s.value_source !== 'NO_DATA'"
                        class="audit-star"
                        :title="`数据状态：${sourceLabel(s.value_source)}`"
                      >*</span>
                    </td>
                    <td class="muted-cell">{{ s.center_name }} / {{ s.branch_name }}</td>
                    <td>{{ s.covered_area ? s.covered_area.toLocaleString() : '待补录' }}</td>
                    <td>
                      <span :class="['src-pill', s.online ? 'src-real' : 'src-off']">
                        {{ s.online ? '在线' : (s.has_record ? '离线' : '无数据') }}
                      </span>
                    </td>
                    <td>
                      <AnomalyBadgeValue :text="`${fmt(s.e3)} / ${fmt(s.e4)}`" :note="s.field_notes?.e3_e4" />
                    </td>
                    <td>
                      <AnomalyBadgeValue :text="`${fmt(s.e7, '', 3)} / ${fmt(s.e8, '', 3)}`" :note="s.field_notes?.e7_e8" />
                    </td>
                    <td>
                      <AnomalyBadgeValue :text="fmt(s.e11)" :note="s.field_notes?.e11" />
                    </td>
                    <td class="font-bold">
                      <AnomalyBadgeValue :text="fmt(s.hour_heat_gj)" :note="s.field_notes?.hour_heat_gj" />
                      <span v-if="s.hour_heat_source === 'METER_DIFF'" class="meter-tag" title="表底差值校准">表</span>
                    </td>
                    <td>
                      <AnomalyBadgeValue :text="fmt(s.heat_index_wm2)" :note="s.field_notes?.heat_index_wm2" />
                    </td>
                    <td>
                      <AnomalyBadgeValue :text="fmt(s.e14)" :note="s.field_notes?.e14" />
                    </td>
                    <td>{{ fmt(s.hour_elec_kwh) }}</td>
                    <td>{{ fmt(s.avg_room_temp) }}</td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Tab 4: 居民室温分布与站级达标 -->
        <div v-if="activeTab === 'temps'" class="tab-panel">
          <div class="temp-layout">
            <div class="temp-chart-panel">
              <div class="temp-stat-badges">
                <span>接口总抓回：<strong>{{ tempSummary.total_fetched_devices }}</strong></span>
                <span>有效样本：<strong>{{ tempSummary.valid_devices }}</strong></span>
                <span>剔除僵尸/越限：<strong>{{ tempSummary.offline_invalid_excluded }}</strong></span>
                <span>精算剔除未入账：<strong>{{ tempSummary.unregistered_excluded }}</strong></span>
              </div>
              <div ref="roomPieEl" class="pie-box"></div>
            </div>
            <div class="temp-rank-panel">
              <h4>按换热站真实室温排名（点击站名下钻单户明细）</h4>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <SortableTh label="换热站" sort-key="name" :sort-state="tempRankSort.state" @sort="tempRankSort.toggle" />
                      <SortableTh label="服务中心" sort-key="center_name" :sort-state="tempRankSort.state" @sort="tempRankSort.toggle" />
                      <SortableTh label="有效户数" sort-key="valid_count" :sort-state="tempRankSort.state" @sort="tempRankSort.toggle" />
                      <SortableTh label="平均室温 (℃)" sort-key="avg_room_temp" :sort-state="tempRankSort.state" @sort="tempRankSort.toggle" />
                      <SortableTh label="达标率 (≥18℃)" sort-key="pass_rate_pct" :sort-state="tempRankSort.state" @sort="tempRankSort.toggle" />
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="tempSummary.station_rankings.length === 0">
                      <td colspan="5" class="empty-td">当前时刻暂无居民室温数据（请检查 Cookie 与整点采集）</td>
                    </tr>
                    <tr
                      v-for="r in tempRankSort.sortedRows.value"
                      :key="r.station_id"
                      class="clickable-row"
                      @click="openStationTempsDrawer(r)"
                    >
                      <td class="font-bold">{{ r.name }}</td>
                      <td>{{ r.center_name }}</td>
                      <td>{{ r.valid_count }}</td>
                      <td :class="['font-bold', (r.avg_room_temp ?? 99) < 18 ? 'text-err' : 'text-ok']">{{ fmt(r.avg_room_temp) }}</td>
                      <td>{{ fmt(r.pass_rate_pct, '%') }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- Tab 5: 464户商业用户小时运行与积分耗量 -->
        <div v-if="activeTab === 'merchants'" class="tab-panel">
          <div class="temp-stat-badges" style="margin-bottom: 10px;">
            <span>台账在网商业户：<strong>{{ merchantSummary.total_merchants ?? 464 }}</strong></span>
            <span>在线户数：<strong>{{ merchantSummary.online_merchants ?? 0 }}</strong></span>
            <span>有用热负荷户数：<strong>{{ merchantSummary.active_heat_merchants ?? 0 }}</strong></span>
            <span>商业小时总耗热：
              <strong>
                <AnomalyBadgeValue :text="fmt(merchantSummary.total_hour_heat_gj, ' GJ')" :note="merchantSummary.heat_anomaly?.note" />
              </strong>
            </span>
            <span>商业小时总流量：<strong>{{ fmt(merchantSummary.total_hour_flow_t, ' t') }}</strong></span>
            <span>已剔除未入账测试户：<strong>{{ merchantSummary.unregistered_excluded ?? 0 }}</strong></span>
          </div>
          <div class="filter-bar">
            <select v-model="merchantFilter.rdfz" class="ctrl-input">
              <option value="">全部主干热网</option>
              <option v-for="r in merchantRdfzOptions" :key="r" :value="r">{{ r }}</option>
            </select>
            <select v-model="merchantFilter.statusFilter" class="ctrl-input">
              <option value="">全部状态</option>
              <option value="ACTIVE">仅有用热负荷</option>
              <option value="ONLINE">仅在线</option>
              <option value="OFFLINE">仅离线</option>
            </select>
            <input v-model="merchantFilter.keyword" type="search" class="ctrl-input" placeholder="搜索商业户名称/支线…" />
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh class="sticky-col" label="商业户名称" sort-key="name" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="大网 / 支线" sort-key="branch_name" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="状态" sort-key="online" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="供水流量 (t/h)" sort-key="flow" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="供/回温 (℃)" sort-key="temp_sup" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="供/回压 (MPa)" sort-key="pres_sup" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="瞬时热量 (GJ/h)" sort-key="heat" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="小时供热量 (GJ)" sort-key="hour_heat_gj" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="小时流量 (t)" sort-key="hour_flow_t" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="阀门开度 (%)" sort-key="valve_open" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                  <SortableTh label="数据来源" sort-key="value_source" :sort-state="merchantSort.state" @sort="merchantSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-if="filteredMerchants.length === 0">
                  <td colspan="11" class="empty-td">暂无匹配的商业用户小时数据</td>
                </tr>
                <tr v-for="m in merchantSort.sortedRows.value" :key="m.merchant_id">
                  <td class="sticky-col font-bold">
                    {{ m.name }}
                    <span
                      v-if="m.value_source !== 'REAL' && m.value_source !== 'NO_DATA' && m.value_source !== 'SOURCE_EMPTY'"
                      class="audit-star"
                      :title="`数据状态：${sourceLabel(m.value_source)}`"
                    >*</span>
                  </td>
                  <td class="muted-cell">{{ m.rdfz || '-' }} / {{ m.branch_name }}</td>
                  <td>
                    <span :class="['src-pill', m.online ? 'src-real' : 'src-off']">
                      {{ m.online ? '在线' : (m.value_source === 'SOURCE_EMPTY' ? '源站无数据' : (m.has_record ? '离线' : '无数据')) }}
                    </span>
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(m.flow)" :note="m.field_notes?.flow" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="`${fmt(m.temp_sup)} / ${fmt(m.temp_ret)}`" :note="m.field_notes?.temp" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="`${fmt(m.pres_sup, '', 3)} / ${fmt(m.pres_ret, '', 3)}`" :note="m.field_notes?.pres" />
                  </td>
                  <td>
                    <AnomalyBadgeValue :text="fmt(m.heat)" :note="m.field_notes?.heat" />
                  </td>
                  <td class="font-bold">
                    <AnomalyBadgeValue :text="fmt(m.hour_heat_gj)" :note="m.field_notes?.hour_heat_gj" />
                  </td>
                  <td>{{ fmt(m.hour_flow_t) }}</td>
                  <td>{{ m.valve_open != null ? `${fmt(m.valve_open)}% / ${fmt(m.valve_set)}%` : '-' }}</td>
                  <td>
                    <span :class="['src-pill', m.value_source === 'REAL' ? 'src-real' : 'src-interp']">
                      {{ sourceLabel(m.value_source) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- 下钻抽屉：上游24h趋势或单站居民室温 -->
      <div v-if="drawer.open" class="drawer-backdrop" @click.self="drawer.open = false">
        <div class="drawer-panel card elevated">
          <div class="drawer-head">
            <h3>{{ drawer.title }}</h3>
            <button class="btn ghost btn-xs" type="button" @click="drawer.open = false">✕ 关闭</button>
          </div>
          <div v-if="drawer.kind === 'upstream'" class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="小时" sort-key="hour" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="温度 (℃)" sort-key="temp" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="压力 (MPa)" sort-key="pressure" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="瞬时流量" sort-key="flow" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="瞬时热量" sort-key="heat" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="积分热量 (GJ)" sort-key="hour_heat_gj" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="pt in drawerSort.sortedRows.value" :key="pt.hour">
                  <td>{{ pt.label }}</td>
                  <td>{{ fmt(pt.temp) }}</td>
                  <td>{{ fmt(pt.pressure, '', 3) }}</td>
                  <td>{{ fmt(pt.flow) }}</td>
                  <td>{{ fmt(pt.heat) }}</td>
                  <td>{{ fmt(pt.hour_heat_gj) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else-if="drawer.kind === 'station_temps'" class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="门牌号" sort-key="village_name" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="型号" sort-key="zdxh" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="清洗室温 (℃)" sort-key="temp_clean" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="原始室温" sort-key="temp_raw" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="最后上传" sort-key="upload_time" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="状态" sort-key="is_online_valid" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                  <SortableTh label="巡检备注" sort-key="remark" :sort-state="drawerSort.state" @sort="drawerSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in drawerSort.sortedRows.value" :key="d.temp_device_id">
                  <td class="font-bold">{{ d.village_name }}</td>
                  <td class="mono">{{ d.zdxh }}</td>
                  <td class="font-bold">{{ fmt(d.temp_clean) }}</td>
                  <td>{{ fmt(d.temp_raw) }}</td>
                  <td class="mono">{{ d.upload_time || '-' }}</td>
                  <td>
                    <span :class="['src-pill', d.is_online_valid ? 'src-real' : 'src-off']">
                      {{ d.is_online_valid ? '有效' : '已剔除' }}
                    </span>
                  </td>
                  <td class="muted-cell">{{ d.remark || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else-if="drawer.kind === 'gap_detail'" class="gap-detail-box">
            <div class="gap-detail-toolbar">
              <div class="gap-status-badge-row">
                <span
                  :class="['src-pill', gapStatus?.running ? 'src-interp' : (gapStatus?.has_gaps ? 'src-off' : 'src-real')]"
                  title="仅用于检测停机真空期漏采小时，不代表单户表计或日报源站缺项"
                >
                  {{ gapStatus?.running ? '后台运行中' : (gapStatus?.has_gaps ? '存在待补缺口' : '无停机采集缺口') }}
                </span>
                <span
                  v-if="gapStatus?.running"
                  :class="['src-pill', (gapStatus.heartbeat_age_seconds ?? 0) > 60 ? 'src-off' : 'src-real']"
                >
                  {{
                    (gapStatus.heartbeat_age_seconds ?? 0) > 60
                      ? `心跳停滞 ${gapStatus.heartbeat_age_seconds}s（等待源站或异常）`
                      : `心跳正常（${gapStatus.heartbeat_age_seconds ?? 0}s 前活跃）`
                  }}
                </span>
              </div>
              <div class="gap-detail-btns">
                <button class="btn secondary btn-sm" type="button" @click="loadGapStatus">🔄 立即刷新</button>
                <button
                  class="btn primary btn-sm"
                  type="button"
                  :disabled="recovering || gapStatus?.running"
                  @click="handleGapRecoverNow"
                >
                  {{ recovering || gapStatus?.running ? '补采执行中…' : '🩹 立即执行补采' }}
                </button>
              </div>
            </div>

            <div class="gap-meta-grid">
              <div class="gap-meta-item">
                <span class="kpi-label">检查区间</span>
                <strong>{{ gapStatus?.start_date || '2026-11-01' }} ~ {{ gapStatus?.latest_completed_hour || '-' }}</strong>
              </div>
              <div class="gap-meta-item">
                <span class="kpi-label">最近任务启动 / 耗时</span>
                <strong>{{ gapStatus?.running_started_at || gapStatus?.last_recovery_run?.started_at || '-' }}（{{ formatDuration(gapStatus?.elapsed_seconds) }}）</strong>
              </div>
              <div class="gap-meta-item">
                <span class="kpi-label">最近心跳时间</span>
                <strong>{{ gapStatus?.last_heartbeat_at || '-' }}</strong>
              </div>
              <div class="gap-meta-item">
                <span class="kpi-label">触发方式</span>
                <strong>{{ gapStatus?.running_trigger || gapStatus?.last_recovery_run?.summary?.trigger || '-' }}</strong>
              </div>
            </div>

            <div v-if="gapStatus?.total_steps > 0 || gapStatus?.running" class="gap-progress-card">
              <div class="gap-progress-head">
                <strong>当前执行进度：步骤 {{ gapStatus?.current_step_index || 0 }} / {{ gapStatus?.total_steps || 0 }}</strong>
                <span class="mono">{{ gapStepPercent }}%</span>
              </div>
              <div class="gap-progress-track">
                <div class="gap-progress-fill" :style="{ width: `${gapStepPercent}%` }"></div>
              </div>
              <p class="gap-progress-label">{{ gapStatus?.current_step_label || '准备中…' }}</p>
              <div v-if="gapStatus?.sub_total > 0" class="gap-sub-progress">
                <span>当前赛道主体进度：{{ gapStatus.sub_done }} / {{ gapStatus.sub_total }}（{{ gapSubPercent }}%）</span>
                <div class="gap-progress-track small">
                  <div class="gap-progress-fill sub" :style="{ width: `${gapSubPercent}%` }"></div>
                </div>
              </div>
              <div class="gap-recovered-chips">
                <span class="slot-badge">换热站 +{{ gapStatus?.recovered_counts?.station_hours || 0 }} 时</span>
                <span class="slot-badge">上游 +{{ gapStatus?.recovered_counts?.upstream_hours || 0 }} 时</span>
                <span class="slot-badge">商业小时 +{{ gapStatus?.recovered_counts?.merchant_hours || 0 }} 时</span>
                <span class="slot-badge">商业日报 +{{ gapStatus?.recovered_counts?.merchant_daily_days || 0 }} 天</span>
              </div>
            </div>

            <div class="gap-detail-section">
              <h4>1. 当前待补缺口明细（共 {{ gapStatus?.total_missing_track_hours || 0 }} 个赛道·小时）</h4>
              <div class="gap-track-list">
                <div class="gap-track-row">
                  <strong>换热站 (fact_station_hourly)：</strong>
                  <span>缺 {{ gapStatus?.tracks?.stations?.missing_count || 0 }} 时</span>
                  <div v-if="gapStatus?.tracks?.stations?.missing_hours?.length" class="gap-hour-tags">
                    <code v-for="h in gapStatus.tracks.stations.missing_hours.slice(0, 24)" :key="`st-${h}`">{{ h }}</code>
                    <span v-if="gapStatus.tracks.stations.missing_hours.length > 24">等共 {{ gapStatus.tracks.stations.missing_hours.length }} 项</span>
                  </div>
                </div>
                <div class="gap-track-row">
                  <strong>上游电厂/首站 (fact_upstream_hourly)：</strong>
                  <span>缺 {{ gapStatus?.tracks?.upstream?.missing_count || 0 }} 时</span>
                  <div v-if="gapStatus?.tracks?.upstream?.missing_hours?.length" class="gap-hour-tags">
                    <code v-for="h in gapStatus.tracks.upstream.missing_hours.slice(0, 24)" :key="`up-${h}`">{{ h }}</code>
                    <span v-if="gapStatus.tracks.upstream.missing_hours.length > 24">等共 {{ gapStatus.tracks.upstream.missing_hours.length }} 项</span>
                  </div>
                </div>
                <div class="gap-track-row">
                  <strong>商业小时 (fact_merchant_hourly)：</strong>
                  <span>缺 {{ gapStatus?.tracks?.merchant_hourly?.missing_count || 0 }} 时</span>
                  <div v-if="gapStatus?.tracks?.merchant_hourly?.missing_hours?.length" class="gap-hour-tags">
                    <code v-for="h in gapStatus.tracks.merchant_hourly.missing_hours.slice(0, 24)" :key="`mh-${h}`">{{ h }}</code>
                    <span v-if="gapStatus.tracks.merchant_hourly.missing_hours.length > 24">等共 {{ gapStatus.tracks.merchant_hourly.missing_hours.length }} 项</span>
                  </div>
                </div>
                <div class="gap-track-row">
                  <strong>商业日报 (fact_merchant_daily)：</strong>
                  <span>缺 {{ gapStatus?.tracks?.merchant_daily?.missing_count || 0 }} 天</span>
                  <div v-if="gapStatus?.tracks?.merchant_daily?.missing_dates?.length" class="gap-hour-tags">
                    <code v-for="d in gapStatus.tracks.merchant_daily.missing_dates" :key="`md-${d}`">{{ d }}</code>
                  </div>
                </div>
              </div>
            </div>

            <div class="gap-detail-section">
              <h4>2. 实时执行流水（最新 {{ gapStatus?.recent_logs?.length || 0 }} 条）</h4>
              <div v-if="gapStatus?.recent_logs?.length" class="gap-log-list">
                <div v-for="(lg, idx) in [...gapStatus.recent_logs].reverse()" :key="idx" :class="['gap-log-line', `log-${lg.level}`]">
                  <span class="mono">{{ lg.time }}</span>
                  <span>{{ lg.message }}</span>
                </div>
              </div>
              <p v-else class="muted-cell">暂无本进程内实况流水（服务刚启动或尚未触发补采）。</p>
            </div>

            <div v-if="gapStatus?.recent_recovery_runs?.length" class="gap-detail-section">
              <h4>3. 最近后台补采审计记录（GAP_RECOVERY）</h4>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <SortableTh label="批次ID" sort-key="run_id" :sort-state="gapRunsSort.state" @sort="gapRunsSort.toggle" />
                      <SortableTh label="状态" sort-key="status" :sort-state="gapRunsSort.state" @sort="gapRunsSort.toggle" />
                      <SortableTh label="开始时间" sort-key="started_at" :sort-state="gapRunsSort.state" @sort="gapRunsSort.toggle" />
                      <SortableTh label="耗时" sort-key="duration_ms" :sort-state="gapRunsSort.state" @sort="gapRunsSort.toggle" />
                      <SortableTh label="入库汇总" sort-key="summary_count" :sort-state="gapRunsSort.state" @sort="gapRunsSort.toggle" />
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="run in gapRunsSort.sortedRows.value" :key="run.run_id">
                      <td class="mono">#{{ run.run_id }}</td>
                      <td>
                        <span :class="['src-pill', run.status === 'SUCCESS' ? 'src-real' : 'src-interp']">{{ run.status }}</span>
                      </td>
                      <td class="mono">{{ run.started_at || '-' }}</td>
                      <td class="mono">{{ run.duration_ms != null ? `${(run.duration_ms / 1000).toFixed(1)}s` : '进行中' }}</td>
                      <td class="muted-cell">
                        站+{{ run.summary?.recovered_station_hours ?? 0 }} /
                        上游+{{ run.summary?.recovered_upstream_hours ?? 0 }} /
                        商业+{{ run.summary?.recovered_merchant_hours ?? 0 }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
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
import DateStepPicker from '../components/DateStepPicker.vue'
import AnomalyBadgeValue from '../components/AnomalyBadgeValue.vue'
import SortableTh from '../components/SortableTh.vue'
import { useTableSort } from '../utils/tableSort'
import { MIN_PLATFORM_DATE, shiftIsoDate, todayLocalIso } from '../utils/dateUtils'
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  downloadPlatformExcel,
  fetchEntityTrend24h,
  fetchGapStatus,
  fetchHourlyReport,
  fetchStationTempDevices,
  fetchUpstreamTrend24h,
  triggerManualCollect,
} from '../services/api'

const todayIso = todayLocalIso

const selectedDate = ref('')
const selectedHour = ref(null)
const mode = ref('clean')
const loading = ref(false)
const collecting = ref(false)
const calibrating = ref(false)
const recovering = ref(false)
const gapStatus = ref(null)
const showTrendChart = ref(true)
const activeTab = ref('groups')
const groupDim = ref('by_center')
const notice = reactive({ type: 'info', text: '' })

const reportData = ref({
  meta: {},
  kpis: {},
  trend_24h: Array.from({ length: 24 }, (_, h) => ({ hour: h, label: `${String(h).padStart(2, '0')}:00`, has_data: false })),
  upstream_points: [],
  group_summaries: { by_center: [], by_rdfz: [], by_main: [], by_branch: [] },
  stations: [],
  merchants: [],
  merchant_summary: {},
  temp_summary: { total_fetched_devices: 0, valid_devices: 0, unregistered_excluded: 0, offline_invalid_excluded: 0, distribution: {}, station_rankings: [] },
})

const upstreamFilter = reactive({ category: '', keyword: '', onlyCore: false })
const stationFilter = reactive({ centerId: '', rdfz: '', branchId: '', statusFilter: '', keyword: '' })
const merchantFilter = reactive({ rdfz: '', statusFilter: '', keyword: '' })
const drawer = reactive({ open: false, kind: '', title: '', rows: [] })
const selectedEntity = ref(null)
const entityLoading = ref(false)
const chartSectionEl = ref(null)

const heatChartEl = ref(null)
const tempChartEl = ref(null)
const roomPieEl = ref(null)
let heatChart = null
let tempChart = null
let roomPieChart = null
let chartResizeObserver = null

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热平台精算模块', to: '/projects/smart_heating_platform/pages' },
  { label: '逐小时精细化运行报告', to: null },
])

const reportTabs = [
  { key: 'groups', label: '🏢 服务中心与热网' },
  { key: 'upstream', label: '🔥 热源与首站' },
  { key: 'stations', label: '🏭 换热站明细' },
  { key: 'merchants', label: '🏬 商业用户明细' },
  { key: 'temps', label: '🌡️ 居民室温统计' },
]

const groupDimensions = [
  { key: 'by_center', label: '服务中心（9）' },
  { key: 'by_rdfz', label: '主干热网（9）' },
  { key: 'by_branch', label: '支线热网（41）' },
]

const meta = computed(() => reportData.value.meta || {})
const kpis = computed(() => reportData.value.kpis || {})
const trend24h = computed(() => reportData.value.trend_24h || [])
const chartTrend = computed(() => selectedEntity.value?.trend_24h || trend24h.value)
const tempSummary = computed(() => reportData.value.temp_summary || { distribution: {}, station_rankings: [] })
const merchantSummary = computed(() => reportData.value.merchant_summary || {})
const activeGroupRows = computed(() => reportData.value.group_summaries?.[groupDim.value] || [])

const filteredUpstream = computed(() => {
  const kw = upstreamFilter.keyword.trim().toLowerCase()
  return (reportData.value.upstream_points || []).filter((u) => {
    if (upstreamFilter.category && u.category !== upstreamFilter.category) return false
    if (upstreamFilter.onlyCore && !u.is_core_gk) return false
    if (kw && !String(u.display_name || '').toLowerCase().includes(kw)) return false
    return true
  })
})

const centerOptions = computed(() => {
  const map = new Map()
  for (const s of reportData.value.stations || []) {
    if (!map.has(s.center_id)) map.set(s.center_id, s.center_name)
  }
  return Array.from(map.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.id - b.id)
})

const stationRdfzOptions = computed(() => {
  const set = new Set()
  for (const s of reportData.value.stations || []) {
    if (stationFilter.centerId && String(s.center_id) !== stationFilter.centerId) continue
    if (s.rdfz) set.add(s.rdfz)
  }
  return Array.from(set).sort()
})

const branchOptions = computed(() => {
  const map = new Map()
  for (const s of reportData.value.stations || []) {
    if (stationFilter.centerId && String(s.center_id) !== stationFilter.centerId) continue
    if (stationFilter.rdfz && s.rdfz !== stationFilter.rdfz) continue
    if (!map.has(s.branch_network_id)) map.set(s.branch_network_id, s.branch_name)
  }
  return Array.from(map.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.id - b.id)
})

const filteredStations = computed(() => {
  const kw = stationFilter.keyword.trim().toLowerCase()
  return (reportData.value.stations || []).filter((s) => {
    if (stationFilter.centerId && String(s.center_id) !== stationFilter.centerId) return false
    if (stationFilter.rdfz && s.rdfz !== stationFilter.rdfz) return false
    if (stationFilter.branchId && String(s.branch_network_id) !== stationFilter.branchId) return false
    if (stationFilter.statusFilter === 'REAL' && s.value_source !== 'REAL') return false
    if (stationFilter.statusFilter === 'INTERP' && (s.value_source === 'REAL' || s.value_source === 'NO_DATA')) return false
    if (stationFilter.statusFilter === 'NO_AREA' && s.covered_area != null) return false
    if (kw && !String(s.name || '').toLowerCase().includes(kw)) return false
    return true
  })
})

const merchantRdfzOptions = computed(() => {
  const set = new Set()
  for (const m of reportData.value.merchants || []) {
    if (m.rdfz) set.add(m.rdfz)
  }
  return Array.from(set).sort()
})

const filteredMerchants = computed(() => {
  const kw = merchantFilter.keyword.trim().toLowerCase()
  return (reportData.value.merchants || []).filter((m) => {
    if (merchantFilter.rdfz && m.rdfz !== merchantFilter.rdfz) return false
    if (merchantFilter.statusFilter === 'ACTIVE' && !(m.heat > 0)) return false
    if (merchantFilter.statusFilter === 'ONLINE' && !m.online) return false
    if (merchantFilter.statusFilter === 'OFFLINE' && m.online) return false
    if (kw && !`${m.name || ''} ${m.branch_name || ''}`.toLowerCase().includes(kw)) return false
    return true
  })
})

const upstreamSort = useTableSort(filteredUpstream)
const groupSort = useTableSort(activeGroupRows)
const stationSort = useTableSort(filteredStations, {
  center_name: (s) => `${s.center_name}/${s.branch_name}`,
  online: (s) => (s.online ? 2 : s.has_record ? 1 : 0),
})
const tempRankSort = useTableSort(() => tempSummary.value.station_rankings || [])
const merchantSort = useTableSort(filteredMerchants, {
  branch_name: (m) => `${m.rdfz}/${m.branch_name}`,
  online: (m) => (m.online ? 2 : m.has_record ? 1 : 0),
})
const drawerSort = useTableSort(() => drawer.rows || [], {
  is_online_valid: (d) => (d.is_online_valid ? 1 : 0),
})
const gapRunsSort = useTableSort(() => gapStatus.value?.recent_recovery_runs || [], {
  summary_count: (r) =>
    (r.summary?.recovered_station_hours ?? 0) +
    (r.summary?.recovered_upstream_hours ?? 0) +
    (r.summary?.recovered_merchant_hours ?? 0),
})

function fmt(val, suffix = '', fixed = 2) {
  if (val === null || val === undefined || val === '') return '-'
  const num = Number(val)
  if (Number.isNaN(num)) return '-'
  return `${num.toFixed(fixed).replace(/\.00$/, '')}${suffix}`
}

function sourceLabel(src) {
  if (src === 'REAL') return '实测'
  if (src === 'MASKED_PREV_HOLD') return '断路平滑'
  if (src === 'INTERP_TEMP_OFFLINE') return '临离估值'
  if (src === 'OFFLINE_PERMANENT') return '常离线'
  if (src === 'SOURCE_EMPTY') return '源站无数据'
  if (src === 'NO_DATA') return '无数据'
  return src || '-'
}

function onCenterChange() {
  stationFilter.rdfz = ''
  stationFilter.branchId = ''
}
function onRdfzChange() {
  stationFilter.branchId = ''
}

let reportSeq = 0
let reportAbortCtrl = null
let reportDebounceTimer = null
let entitySeq = 0
let entityAbortCtrl = null

const ENTITY_SCOPE_LABELS = {
  by_center: '服务中心',
  by_rdfz: '主干热网',
  by_branch: '支线热网',
  station: '换热站',
}

async function fetchAndRenderEntityTrend(scope, key, name, stationCount, targetDateStr, { scroll = false } = {}) {
  if (!targetDateStr) return
  const reqId = ++entitySeq
  if (entityAbortCtrl) entityAbortCtrl.abort()
  entityAbortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
  entityLoading.value = true
  const scopeLabel = ENTITY_SCOPE_LABELS[scope] || '主体'
  selectedEntity.value = {
    scope,
    key: String(key),
    name: name || String(key),
    scopeLabel,
    stationCount: stationCount ?? 0,
    trend_24h: selectedEntity.value?.scope === scope && selectedEntity.value?.key === String(key)
      ? selectedEntity.value.trend_24h
      : null,
  }
  showTrendChart.value = true
  try {
    const res = await fetchEntityTrend24h(
      { date: targetDateStr, scope, key: String(key), mode: mode.value },
      entityAbortCtrl ? { signal: entityAbortCtrl.signal } : {},
    )
    if (reqId !== entitySeq) return
    if (res?.data) {
      selectedEntity.value = {
        scope,
        key: String(key),
        name: res.data.entity_name || name || String(key),
        scopeLabel: res.data.scope_label || scopeLabel,
        stationCount: res.data.station_count ?? stationCount ?? 0,
        trend_24h: res.data.trend_24h || [],
      }
      await nextTick()
      if (reqId === entitySeq) {
        renderCharts()
        if (scroll && chartSectionEl.value) {
          chartSectionEl.value.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
        }
      }
    }
  } catch (err) {
    if (err?.name === 'AbortError' || reqId !== entitySeq) return
    notice.type = 'error'
    notice.text = `加载主体趋势失败：${err.message}`
  } finally {
    if (reqId === entitySeq) entityLoading.value = false
  }
}

function selectEntityTrend(scope, key, name, stationCount) {
  if (selectedEntity.value?.scope === scope && selectedEntity.value?.key === String(key)) {
    clearSelectedEntity()
    return
  }
  const dateStr = selectedDate.value || meta.value?.date || todayIso()
  fetchAndRenderEntityTrend(scope, key, name, stationCount, dateStr, { scroll: true })
}

async function clearSelectedEntity() {
  entitySeq++
  entityAbortCtrl?.abort()
  entityLoading.value = false
  selectedEntity.value = null
  await nextTick()
  renderCharts()
}

function scheduleLoadReport(delayMs = 180) {
  if (reportDebounceTimer) {
    clearTimeout(reportDebounceTimer)
    reportDebounceTimer = null
  }
  reportDebounceTimer = setTimeout(() => {
    reportDebounceTimer = null
    loadReport()
  }, delayMs)
}

async function loadReport() {
  if (reportDebounceTimer) {
    clearTimeout(reportDebounceTimer)
    reportDebounceTimer = null
  }
  const reqId = ++reportSeq
  if (reportAbortCtrl) {
    reportAbortCtrl.abort()
  }
  reportAbortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
  const requestedDate = selectedDate.value || ''
  const requestedHour = selectedHour.value
  loading.value = true
  try {
    const params = { mode: mode.value }
    if (requestedDate) params.date = requestedDate
    if (requestedHour !== null && requestedHour !== undefined) params.hour = requestedHour
    const res = await fetchHourlyReport(
      params,
      reportAbortCtrl ? { signal: reportAbortCtrl.signal } : {},
    )
    if (reqId !== reportSeq) return
    if (res?.data) {
      reportData.value = res.data
      if (res.data.meta?.date && (!requestedDate || requestedDate === selectedDate.value)) {
        selectedDate.value = res.data.meta.date
      }
      if (
        res.data.meta?.hour !== undefined &&
        res.data.meta?.hour !== null &&
        (requestedHour === null || requestedHour === undefined || Number(requestedHour) === Number(selectedHour.value))
      ) {
        selectedHour.value = Number(res.data.meta.hour)
      }
      await nextTick()
      if (reqId === reportSeq) {
        if (selectedEntity.value) {
          const d = res.data.meta?.date || selectedDate.value
          fetchAndRenderEntityTrend(
            selectedEntity.value.scope,
            selectedEntity.value.key,
            selectedEntity.value.name,
            selectedEntity.value.stationCount,
            d,
          )
        } else {
          renderCharts()
        }
      }
    }
  } catch (err) {
    if (err?.name === 'AbortError' || reqId !== reportSeq) return
    notice.type = 'error'
    notice.text = `加载逐小时报告失败：${err.message}`
  } finally {
    if (reqId === reportSeq) {
      loading.value = false
    }
  }
}

function onDateChange() {
  selectedHour.value = null
  scheduleLoadReport(180)
}

function jumpToLatest() {
  selectedDate.value = ''
  selectedHour.value = null
  loadReport()
}

const canStepPrevHour = computed(() => {
  if (selectedHour.value === null || selectedHour.value === undefined) return false
  const curHour = Number(selectedHour.value)
  if (curHour > 0) return true
  const curDate = selectedDate.value || todayIso()
  return curDate > MIN_PLATFORM_DATE
})

const canStepNextHour = computed(() => {
  if (selectedHour.value === null || selectedHour.value === undefined) return false
  const curHour = Number(selectedHour.value)
  if (curHour < 23) return true
  const curDate = selectedDate.value || todayIso()
  return curDate < todayIso()
})

function stepHour(delta) {
  if (selectedHour.value === null || selectedHour.value === undefined) return
  const curHour = Number(selectedHour.value)
  const curDate = selectedDate.value || todayIso()
  const maxDate = todayIso()

  if (delta < 0) {
    if (curHour > 0) {
      selectedHour.value = curHour - 1
      scheduleLoadReport(180)
      return
    }
    const prevDate = shiftIsoDate(curDate, -1)
    if (prevDate >= MIN_PLATFORM_DATE) {
      selectedDate.value = prevDate
      selectedHour.value = 23
      scheduleLoadReport(180)
    }
    return
  }

  if (delta > 0) {
    if (curHour < 23) {
      selectedHour.value = curHour + 1
      scheduleLoadReport(180)
      return
    }
    if (curDate < maxDate) {
      const nextDate = shiftIsoDate(curDate, 1)
      if (nextDate <= maxDate) {
        selectedDate.value = nextDate
        selectedHour.value = 0
        scheduleLoadReport(180)
      }
    }
  }
}
function switchMode(m) {
  mode.value = m
  loadReport()
}

async function handleCollectNow() {
  collecting.value = true
  notice.type = 'info'
  notice.text = '正在并行采集上游点位、464 户商业用户实时断面与居民室温，请稍候…'
  try {
    const res = await triggerManualCollect({ action: 'snapshot', include_jumin: true })
    notice.type = 'success'
    notice.text = `采集完成：更新上游 ${res.upstream_hourly} 点、商业用户 ${res.merchant_hourly} 户、居民室温 ${res.temp_hourly} 户、异常工单 ${res.fault_tickets} 条。`
    await loadReport()
  } catch (err) {
    notice.type = 'error'
    notice.text = `采集失败：${err.message}`
  } finally {
    collecting.value = false
  }
}

async function handleCalibNow() {
  calibrating.value = true
  const targetDate = selectedDate.value || todayIso()
  notice.type = 'info'
  notice.text = `正在并行拉取 ${targetDate} 全网 242 座换热站表底（/hrz_ls_zb/），请稍候…`
  try {
    const res = await triggerManualCollect({ action: 'calib', target_date: targetDate })
    notice.type = 'success'
    notice.text = `表底校准完成：更新 ${res.updated_station_hours} 站·小时记录（并发 ${res.max_workers} 线程），跳变异常 ${res.jump_faults} 条。`
    selectedHour.value = null
    await loadReport()
  } catch (err) {
    notice.type = 'error'
    notice.text = `表底校准失败：${err.message}`
  } finally {
    calibrating.value = false
  }
}

let gapPollTimer = null

const gapStepPercent = computed(() => {
  const total = Number(gapStatus.value?.total_steps || 0)
  const cur = Number(gapStatus.value?.current_step_index || 0)
  if (!total) return gapStatus.value?.running ? 0 : 100
  return Math.min(100, Math.round((cur / total) * 100))
})

const gapSubPercent = computed(() => {
  const total = Number(gapStatus.value?.sub_total || 0)
  const done = Number(gapStatus.value?.sub_done || 0)
  if (!total) return 0
  return Math.min(100, Math.round((done / total) * 100))
})

function formatDuration(sec) {
  if (sec === null || sec === undefined) return '-'
  const s = Math.max(0, Number(sec))
  if (s < 60) return `${s} 秒`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m} 分 ${rem} 秒`
}

function syncGapPolling(isRunning) {
  if (isRunning && !gapPollTimer) {
    gapPollTimer = setInterval(() => {
      loadGapStatus()
    }, 2500)
  } else if (!isRunning && gapPollTimer) {
    clearInterval(gapPollTimer)
    gapPollTimer = null
  }
}

async function loadGapStatus() {
  const wasRunning = Boolean(gapStatus.value?.running)
  try {
    const res = await fetchGapStatus()
    gapStatus.value = res?.data || null
    const nowRunning = Boolean(gapStatus.value?.running)
    syncGapPolling(nowRunning)
    if (wasRunning && !nowRunning) {
      await loadReport()
    }
  } catch {
    // 真空期巡检状态读取失败不影响主报表渲染
  }
}

function openGapDetailDrawer() {
  drawer.open = true
  drawer.kind = 'gap_detail'
  drawer.title = '停机真空期自动补齐 · 实况进度与明细'
  drawer.rows = []
  loadGapStatus()
}

async function handleGapRecoverNow() {
  recovering.value = true
  notice.type = 'info'
  notice.text = '正在自动识别并并行补足停机真空期缺失整点，请稍候…'
  try {
    const res = await triggerManualCollect({ action: 'gap_recovery' })
    if (res.already_running) {
      notice.type = 'info'
      notice.text = '后台真空期自动补采正在运行中，可点击“查看详情”实时观测进度与心跳。'
    } else {
      notice.type = 'success'
      notice.text = `真空期补全完成：换热站 ${res.recovered_station_hours || 0} 站·小时、上游 ${res.recovered_upstream_hours || 0} 点·小时、商业用户 ${res.recovered_merchant_hours || 0} 户·小时、商业日耗 ${res.recovered_merchant_daily_days || 0} 天。`
      selectedHour.value = null
      await loadReport()
    }
    await loadGapStatus()
  } catch (err) {
    notice.type = 'error'
    notice.text = `真空期补采失败：${err.message}`
  } finally {
    recovering.value = false
  }
}

async function handleExport() {
  try {
    const scopeParam = selectedEntity.value ? `&scope=${encodeURIComponent(selectedEntity.value.scope)}&key=${encodeURIComponent(selectedEntity.value.key)}` : ''
    const modeTag = mode.value === 'raw' ? '原始数据' : '修正后'
    await downloadPlatformExcel(
      `/reports/hourly/export?date=${encodeURIComponent(selectedDate.value)}&hour=${selectedHour.value}&mode=${mode.value}${scopeParam}`,
      `逐小时统计报告_${selectedDate.value}_${modeTag}_${String(selectedHour.value).padStart(2, '0')}时断面.xlsx`,
    )
  } catch (err) {
    notice.type = 'error'
    notice.text = err.message
  }
}

async function openUpstreamDrawer(item) {
  drawer.open = true
  drawer.kind = 'upstream'
  drawer.title = `${item.display_name} — ${selectedDate.value} 24小时走势`
  drawer.rows = []
  drawerSort.reset()
  try {
    const res = await fetchUpstreamTrend24h({
      date: selectedDate.value,
      data_zone: item.data_zone,
      source_name: item.source_name,
    })
    drawer.rows = res?.data || []
  } catch (err) {
    notice.type = 'error'
    notice.text = err.message
  }
}

async function openStationTempsDrawer(st) {
  drawer.open = true
  drawer.kind = 'station_temps'
  drawer.title = `${st.name}（${st.center_name}）— 居民室温单户明细`
  drawer.rows = []
  drawerSort.reset()
  try {
    const res = await fetchStationTempDevices({
      date: selectedDate.value,
      hour: selectedHour.value,
      station_id: st.station_id,
    })
    drawer.rows = res?.data || []
  } catch (err) {
    notice.type = 'error'
    notice.text = err.message
  }
}

function escHtml(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function buildAnomalyTooltipFormatter() {
  return (params) => {
    const items = Array.isArray(params) ? params : [params]
    if (!items.length) return ''
    const title = escHtml(items[0].axisValueLabel ?? items[0].name ?? '')
    const lines = [`<div style="font-weight:700;margin-bottom:4px;">${title}</div>`]
    const notes = []
    for (const p of items) {
      const val = p.value !== null && p.value !== undefined && typeof p.value === 'object' ? p.value.value : p.value
      const disp = val === null || val === undefined || val === '' ? '-' : escHtml(val)
      const hasAnom = Boolean(p.data && typeof p.data === 'object' && p.data.anomalyNote)
      const valStyle = hasAnom ? 'color:#f87171;font-weight:700;' : 'font-weight:600;'
      const mark = hasAnom ? ' <span style="color:#f87171;">*</span>' : ''
      lines.push(
        `<div style="display:flex;justify-content:space-between;gap:12px;"><span>${p.marker}${escHtml(p.seriesName)}</span><span style="${valStyle}">${disp}${mark}</span></div>`,
      )
      if (hasAnom && !notes.includes(p.data.anomalyNote)) {
        notes.push(p.data.anomalyNote)
      }
    }
    if (notes.length) {
      lines.push(
        ...notes.map(
          (note) =>
            `<div style="margin-top:6px;padding-top:4px;border-top:1px dashed #ef4444;color:#fca5a5;max-width:300px;white-space:normal;line-height:1.45;">⚠️ ${escHtml(note)}</div>`,
        ),
      )
    }
    return lines.join('')
  }
}

function bindChartHourClick(chartInstance) {
  const zr = chartInstance.getZr()
  zr.on('mousemove', (event) => {
    const inside = chartInstance.containPixel('grid', [event.offsetX, event.offsetY])
    zr.setCursorStyle(inside ? 'pointer' : 'default')
  })
  zr.on('click', (event) => {
    const pointInPixel = [event.offsetX, event.offsetY]
    if (!chartInstance.containPixel('grid', pointInPixel)) return
    const pointInGrid = chartInstance.convertFromPixel({ seriesIndex: 0 }, pointInPixel)
    if (!Array.isArray(pointInGrid) || Number.isNaN(pointInGrid[0])) return
    const idx = Math.round(pointInGrid[0])
    const targetRow = chartTrend.value?.[idx]
    if (!targetRow || targetRow.hour === null || targetRow.hour === undefined) return
    const nextHour = Number(targetRow.hour)
    if (nextHour !== Number(selectedHour.value)) {
      selectedHour.value = nextHour
      scheduleLoadReport(80)
    }
  })
}

function renderCharts() {
  const rows = chartTrend.value
  const entityName = selectedEntity.value?.name
  const prefix = entityName ? `【${entityName}】` : '全网'
  const isSingleStation = selectedEntity.value?.scope === 'station'
  const labels = rows.map((r) => r.label)
  const isNarrow = typeof window !== 'undefined' && window.innerWidth <= 640
  const tooltipFormatter = buildAnomalyTooltipFormatter()
  const activeLabel =
    selectedHour.value !== null && selectedHour.value !== undefined
      ? `${String(selectedHour.value).padStart(2, '0')}:00`
      : null

  const xAxisBottom = {
    type: 'category',
    data: labels,
    axisLabel: {
      formatter: (val) => (activeLabel && val === activeLabel ? `{active|${val}}` : val),
      rich: {
        active: {
          color: '#1d4ed8',
          fontWeight: 700,
        },
      },
    },
  }

  const xAxisTopArrow = {
    type: 'category',
    position: 'top',
    data: labels,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: false },
    axisLabel: {
      interval: 0,
      margin: 4,
      color: '#1d4ed8',
      fontSize: 12,
      fontWeight: 700,
      formatter: (val) => (activeLabel && val === activeLabel ? '▼' : ''),
    },
  }

  const topAxisAnchorSeries = {
    name: '__hour_marker__',
    type: 'line',
    xAxisIndex: 1,
    data: [],
    silent: true,
    showSymbol: false,
    tooltip: { show: false },
  }

  if (heatChartEl.value) {
    if (!heatChart) {
      heatChart = echarts.init(heatChartEl.value)
      bindChartHourClick(heatChart)
    }
    heatChart.setOption({
      title: { text: `${prefix}小时供热量 (GJ) & 室外气温 (℃)`, textStyle: { fontSize: isNarrow ? 12 : 13 } },
      tooltip: { trigger: 'axis', formatter: tooltipFormatter },
      legend: { bottom: 0, type: 'scroll', data: ['小时供热量(GJ)', '热指标(W/㎡)', '室外气温(℃)'] },
      grid: { left: isNarrow ? 8 : 48, right: isNarrow ? 8 : 48, top: 44, bottom: 38, containLabel: true },
      xAxis: [xAxisBottom, xAxisTopArrow],
      yAxis: [
        { type: 'value', name: isNarrow ? '' : 'GJ / W/㎡' },
        { type: 'value', name: isNarrow ? '' : '℃' },
      ],
      series: [
        {
          name: '小时供热量(GJ)',
          type: 'bar',
          itemStyle: { color: '#3b82f6' },
          data: rows.map((r) => {
            const isSel = activeLabel && r.label === activeLabel
            if (r.anomalies?.hour_heat_gj) {
              return {
                value: r.hour_heat_gj,
                itemStyle: { color: isSel ? '#b91c1c' : '#dc2626' },
                anomalyNote: r.anomalies.hour_heat_gj.note,
              }
            }
            if (isSel) {
              return {
                value: r.hour_heat_gj,
                itemStyle: { color: '#1d4ed8' },
              }
            }
            return r.hour_heat_gj
          }),
        },
        {
          name: '热指标(W/㎡)',
          type: 'line',
          smooth: true,
          itemStyle: { color: '#f59e0b' },
          data: rows.map((r) =>
            r.anomalies?.heat_index_wm2
              ? {
                  value: r.heat_index_wm2,
                  symbol: 'circle',
                  symbolSize: 9,
                  itemStyle: { color: '#dc2626', borderColor: '#fff', borderWidth: 1.5 },
                  anomalyNote: r.anomalies.heat_index_wm2.note,
                }
              : r.heat_index_wm2,
          ),
        },
        { name: '室外气温(℃)', type: 'line', yAxisIndex: 1, smooth: true, data: rows.map((r) => r.outdoor_temp), itemStyle: { color: '#06b6d4' } },
        topAxisAnchorSeries,
      ],
    }, true)
    heatChart.resize()
  }

  if (tempChartEl.value) {
    if (!tempChart) {
      tempChart = echarts.init(tempChartEl.value)
      bindChartHourClick(tempChart)
    }
    tempChart.setOption({
      title: {
        text: isSingleStation ? `${prefix}一网供回温 (℃)` : `${prefix}流量加权供回温 (℃)`,
        textStyle: { fontSize: isNarrow ? 12 : 13 },
      },
      tooltip: { trigger: 'axis', formatter: tooltipFormatter },
      legend: { bottom: 0, type: 'scroll', data: ['一网供温', '一网回温'] },
      grid: { left: isNarrow ? 8 : 45, right: isNarrow ? 8 : 20, top: 44, bottom: 38, containLabel: true },
      xAxis: [xAxisBottom, xAxisTopArrow],
      yAxis: { type: 'value', name: isNarrow ? '' : '℃' },
      series: [
        {
          name: '一网供温',
          type: 'line',
          smooth: true,
          itemStyle: { color: '#dc2626' },
          data: rows.map((r) => {
            const isSel = activeLabel && r.label === activeLabel
            if (r.anomalies?.avg_sup_temp) {
              return {
                value: r.avg_sup_temp,
                symbol: 'diamond',
                symbolSize: isSel ? 10 : 9,
                itemStyle: { color: '#b91c1c', borderColor: '#fecaca', borderWidth: 2 },
                anomalyNote: r.anomalies.avg_sup_temp.note,
              }
            }
            return isSel
              ? {
                  value: r.avg_sup_temp,
                  symbol: 'circle',
                  symbolSize: 8,
                  itemStyle: { color: '#dc2626', borderColor: '#fff', borderWidth: 2 },
                }
              : r.avg_sup_temp
          }),
        },
        {
          name: '一网回温',
          type: 'line',
          smooth: true,
          itemStyle: { color: '#2563eb' },
          data: rows.map((r) => {
            const isSel = activeLabel && r.label === activeLabel
            if (r.anomalies?.avg_ret_temp) {
              return {
                value: r.avg_ret_temp,
                symbol: 'diamond',
                symbolSize: isSel ? 10 : 9,
                itemStyle: { color: '#dc2626', borderColor: '#fecaca', borderWidth: 2 },
                anomalyNote: r.anomalies.avg_ret_temp.note,
              }
            }
            return isSel
              ? {
                  value: r.avg_ret_temp,
                  symbol: 'circle',
                  symbolSize: 8,
                  itemStyle: { color: '#1d4ed8', borderColor: '#fff', borderWidth: 2 },
                }
              : r.avg_ret_temp
          }),
        },
        topAxisAnchorSeries,
      ],
    }, true)
    tempChart.resize()
  }

  if (activeTab.value === 'temps' && roomPieEl.value) {
    if (!roomPieChart) roomPieChart = echarts.init(roomPieEl.value)
    const d = tempSummary.value.distribution || {}
    roomPieChart.setOption({
      title: { text: '居民真实室温区间分布', left: 'center', textStyle: { fontSize: isNarrow ? 13 : 14 } },
      tooltip: { trigger: 'item', formatter: '{b}: {c} 户 ({d}%)' },
      legend: isNarrow ? { bottom: 0, type: 'scroll' } : undefined,
      series: [
        {
          type: 'pie',
          radius: isNarrow ? ['36%', '60%'] : ['42%', '70%'],
          center: isNarrow ? ['50%', '46%'] : ['50%', '54%'],
          label: { show: !isNarrow },
          data: [
            { value: d.under_18 || 0, name: '<18℃ 不达标', itemStyle: { color: '#ef4444' } },
            { value: d.ok_18_20 || 0, name: '18~20℃ 合格', itemStyle: { color: '#f59e0b' } },
            { value: d.comfort_20_25 || 0, name: '20~25℃ 舒适', itemStyle: { color: '#10b981' } },
            { value: d.over_25 || 0, name: '>25℃ 过热', itemStyle: { color: '#3b82f6' } },
          ],
        },
      ],
    }, true)
    roomPieChart.resize()
  }
}

watch(selectedHour, async () => {
  await nextTick()
  renderCharts()
})

watch(showTrendChart, async (val) => {
  if (val) {
    await nextTick()
    onResize()
  }
})

watch(activeTab, async (val) => {
  if (val === 'temps') {
    await nextTick()
    if (chartResizeObserver && roomPieEl.value) {
      chartResizeObserver.observe(roomPieEl.value)
    }
    renderCharts()
  }
})

function onResize() {
  heatChart?.resize()
  tempChart?.resize()
  roomPieChart?.resize()
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  if (typeof ResizeObserver !== 'undefined') {
    chartResizeObserver = new ResizeObserver(() => onResize())
    if (heatChartEl.value) chartResizeObserver.observe(heatChartEl.value)
    if (tempChartEl.value) chartResizeObserver.observe(tempChartEl.value)
    if (roomPieEl.value) chartResizeObserver.observe(roomPieEl.value)
  }
  loadReport()
  loadGapStatus()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartResizeObserver?.disconnect()
  if (reportDebounceTimer) clearTimeout(reportDebounceTimer)
  reportAbortCtrl?.abort()
  entityAbortCtrl?.abort()
  if (gapPollTimer) clearInterval(gapPollTimer)
  heatChart?.dispose()
  tempChart?.dispose()
  roomPieChart?.dispose()
})
</script>

<style scoped>
.shp-page-root { overflow-x: clip; }
.shp-main { padding: 18px 16px 40px; max-width: 1420px; width: 100%; box-sizing: border-box; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.shp-main > * { min-width: 0; max-width: 100%; box-sizing: border-box; }
.control-bar { padding: 12px 18px; display: flex; flex-direction: column; gap: 8px; position: sticky; top: 8px; z-index: 20; }
.control-top { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
.control-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.control-left h2 { margin: 0; font-size: 18px; }
.badge-yang { font-size: 12px; font-weight: 600; background: #dcfce7; color: #166534; padding: 2px 10px; border-radius: 999px; }
.gap-banner { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 14px; border-radius: 10px; background: #fffbeb; border: 1px solid #fde68a; color: #92400e; font-size: 13px; }
.gap-banner-text { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.gap-banner-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.slot-badge { font-size: 12px; background: #eff6ff; color: #1e40af; padding: 2px 10px; border-radius: 999px; border: 1px solid #bfdbfe; }
.run-meta { font-size: 12px; color: #64748b; }
.control-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.inline-field { display: inline-flex; align-items: center; gap: 6px; height: 34px; font-size: 13px; font-weight: 600; color: #334155; white-space: nowrap; }
.ctrl-input { height: 34px; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; padding: 0 10px; font-size: 13px; background: #fff; }
.hour-picker-group { display: inline-flex; align-items: center; height: 34px; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; background: #fff; flex-shrink: 0; }
.hour-step-btn, .hour-action-btn { height: 100%; box-sizing: border-box; border: none; background: #f8fafc; color: #334155; padding: 0 10px; font-size: 13px; font-weight: 600; line-height: 1; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; border-right: 1px solid #e2e8f0; white-space: nowrap; }
.hour-action-btn:last-child { border-right: none; }
.hour-step-btn:hover:not(:disabled), .hour-action-btn:hover:not(:disabled) { background: #eff6ff; color: #1d4ed8; }
.hour-step-btn:disabled, .hour-action-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.hour-select { height: 100%; box-sizing: border-box; border: none; border-right: 1px solid #e2e8f0; border-radius: 0; padding: 0 8px; min-width: 104px; font-size: 13px; font-weight: 600; color: #0f172a; line-height: 32px; }
.mode-switch { display: inline-flex; align-items: center; height: 34px; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; background: #f8fafc; flex-shrink: 0; }
.mode-btn { height: 100%; box-sizing: border-box; padding: 0 12px; font-size: 13px; line-height: 1; display: inline-flex; align-items: center; justify-content: center; border: none; background: #f8fafc; color: #475569; cursor: pointer; font-weight: 600; white-space: nowrap; }
.mode-btn + .mode-btn { border-left: 1px solid #e2e8f0; }
.mode-btn.active { background: #1d4ed8; color: #fff; }
.mode-btn.raw-active { background: #dc2626; color: #fff; }
.raw-mode-banner { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 14px; border-radius: 10px; background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; font-size: 13px; }
.control-right > .btn-sm { height: 34px; box-sizing: border-box; padding: 0 12px; font-size: 13px; line-height: 1; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; gap: 5px; white-space: nowrap; flex-shrink: 0; }
.notice-banner { padding: 10px 14px; border-radius: 8px; font-size: 13px; }
.notice-banner.success { background: #ecfdf5; color: #065f46; }
.notice-banner.error { background: #fef2f2; color: #991b1b; }
.notice-banner.info { background: #eff6ff; color: #1e40af; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap: 12px; }
.kpi-card { padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.kpi-card.highlight { background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%); border: 1px solid #bfdbfe; }
.kpi-label { font-size: 12px; color: #64748b; }
.kpi-val { font-size: 18px; color: #0f172a; }
.kpi-sub { font-size: 12px; color: #64748b; }
.chart-section { padding: 16px 20px; min-width: 0; overflow: hidden; }
.section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px; flex-wrap: wrap; }
.section-head h3 { margin: 0; font-size: 15px; }
.head-title-group, .head-actions-group { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.chart-pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr)); gap: 16px; min-width: 0; }
.chart-box { height: 270px; width: 100%; min-width: 0; max-width: 100%; overflow: hidden; }
.report-tabs-card { padding: 16px 20px; display: flex; flex-direction: column; gap: 14px; min-width: 0; overflow: hidden; }
.tab-bar { display: flex; gap: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; flex-wrap: wrap; }
.tab-btn { padding: 8px 16px; border: 1px solid transparent; border-radius: 8px; background: #f1f5f9; color: #334155; font-size: 13px; font-weight: 600; cursor: pointer; }
.tab-btn.active { background: #0f172a; color: #fff; }
.filter-bar { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
.check-inline { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.table-wrap { overflow-x: auto; max-height: 540px; -webkit-overflow-scrolling: touch; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.data-table th, .data-table td { padding: 9px 11px; border-bottom: 1px solid #e2e8f0; text-align: left; }
.data-table thead th { position: sticky; top: 0; background: #f8fafc; color: #334155; font-weight: 600; z-index: 5; }
.sticky-col { position: sticky; left: 0; background: #fff; z-index: 4; }
.data-table thead th.sticky-col { z-index: 6; background: #f8fafc; }
.clickable-row { cursor: pointer; }
.clickable-row:hover td { background: #f8fafc; }
.row-selected td, .row-selected:hover td { background: #dbeafe !important; }
.chart-hint-tag { margin-left: 4px; font-size: 11px; opacity: 0.72; }
.row-interp td { background: #fffbeb; }
.audit-star { color: #d97706; font-weight: 700; margin-left: 3px; cursor: help; }
.meter-tag { font-size: 10px; background: #dbeafe; color: #1d4ed8; padding: 1px 4px; border-radius: 4px; margin-left: 4px; }
.src-pill { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
.src-real { background: #dcfce7; color: #166534; }
.src-interp { background: #fef3c7; color: #92400e; }
.src-off { background: #f1f5f9; color: #64748b; }
.temp-layout { display: grid; grid-template-columns: 360px 1fr; gap: 16px; min-width: 0; }
.temp-chart-panel, .temp-rank-panel { min-width: 0; max-width: 100%; overflow: hidden; }
@media (max-width: 960px) { .temp-layout { grid-template-columns: 1fr; } }
.temp-stat-badges { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px; margin-bottom: 10px; background: #f8fafc; padding: 10px; border-radius: 8px; }
.pie-box { height: 280px; width: 100%; min-width: 0; max-width: 100%; overflow: hidden; }
.font-bold { font-weight: 600; }
.muted-cell { color: #64748b; }
.empty-td { text-align: center !important; color: #64748b; padding: 28px !important; }
.text-ok { color: #059669; }
.text-err { color: #dc2626; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
.drawer-backdrop { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45); display: flex; justify-content: flex-end; z-index: 60; }
.drawer-panel { width: min(760px, 95vw); height: 100%; border-radius: 0; padding: 20px; overflow-y: auto; }
.drawer-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; gap: 8px; }
.drawer-head h3 { margin: 0; font-size: 16px; }
.gap-step-inline { color: #78350f; font-size: 12px; }
.gap-detail-box { display: flex; flex-direction: column; gap: 16px; }
.gap-detail-toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
.gap-status-badge-row, .gap-detail-btns { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.gap-meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; }
.gap-meta-item { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
.gap-progress-card { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; }
.gap-progress-head { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: #1e3a8a; }
.gap-progress-track { width: 100%; height: 10px; border-radius: 999px; background: #dbeafe; overflow: hidden; }
.gap-progress-track.small { height: 7px; }
.gap-progress-fill { height: 100%; background: #2563eb; border-radius: 999px; transition: width 0.25s ease; }
.gap-progress-fill.sub { background: #10b981; }
.gap-progress-label { margin: 0; font-size: 13px; color: #1e40af; }
.gap-sub-progress { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #065f46; }
.gap-recovered-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.gap-detail-section h4 { margin: 0 0 8px; font-size: 14px; color: #0f172a; }
.gap-track-list { display: flex; flex-direction: column; gap: 8px; }
.gap-track-row { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 9px 12px; font-size: 12px; display: flex; flex-direction: column; gap: 6px; }
.gap-hour-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.gap-hour-tags code { background: #fff; border: 1px solid #cbd5e1; border-radius: 4px; padding: 1px 6px; font-size: 11px; }
.gap-log-list { background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 10px 12px; max-height: 220px; overflow-y: auto; display: flex; flex-direction: column; gap: 5px; font-size: 12px; }
.gap-log-line { display: flex; gap: 8px; align-items: baseline; line-height: 1.45; }
.gap-log-line.log-success { color: #86efac; }
.gap-log-line.log-warn { color: #fde047; }
.gap-log-line.log-error { color: #fca5a5; }

@media (max-width: 768px) {
  .shp-main { padding: 12px 10px 28px; gap: 10px; }
  .control-bar { position: static; padding: 12px; gap: 10px; }
  .control-left { gap: 6px; }
  .control-left h2 { font-size: 16px; line-height: 1.35; }
  .control-right { width: 100%; display: grid; grid-template-columns: 1fr; gap: 8px; }
  .inline-field { width: 100%; height: auto; justify-content: space-between; }
  .inline-field .ctrl-input { flex: 1; min-width: 0; }
  .hour-picker-group { width: 100%; height: 36px; display: flex; }
  .hour-select { flex: 1; min-width: 0; line-height: 34px; }
  .mode-switch { width: 100%; height: auto; min-height: 36px; display: grid; grid-template-columns: 1fr 1fr; }
  .mode-switch.group-dim-switch { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .mode-btn { padding: 8px 6px; font-size: 12px; }
  .control-right > .btn { width: 100%; justify-content: center; height: 36px; }
  .gap-banner-actions { width: 100%; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
  .gap-banner-actions > .btn:last-child:nth-child(odd) { grid-column: 1 / -1; }
  .gap-banner-actions > .btn { width: 100%; justify-content: center; }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .kpi-card { padding: 11px 12px; }
  .kpi-val { font-size: 16px; }
  .chart-section, .report-tabs-card { padding: 12px; }
  .chart-pair { grid-template-columns: 1fr; gap: 12px; }
  .chart-box { height: 220px; }
  .tab-bar { flex-wrap: wrap; gap: 6px; padding-bottom: 10px; }
  .tab-btn { flex: 1 1 calc(50% - 6px); padding: 8px 8px; font-size: 12px; text-align: center; }
  .tab-btn:last-child:nth-child(odd) { flex-basis: 100%; }
  .filter-bar { gap: 8px; }
  .filter-bar > .ctrl-input { flex: 1 1 140px; min-width: 0 !important; }
  .data-table { font-size: 12px; }
  .data-table th, .data-table td { padding: 7px 8px; }
  .sticky-col { max-width: 124px; overflow: hidden; text-overflow: ellipsis; box-shadow: 3px 0 6px -2px rgba(15, 23, 42, 0.08); }
  .temp-stat-badges { grid-template-columns: 1fr; }
  .pie-box { height: 240px; }
  .drawer-panel { width: 100vw; max-width: 100vw; padding: 14px 12px; }
  .gap-meta-grid { grid-template-columns: 1fr; }
  .gap-detail-btns { width: 100%; display: grid; grid-template-columns: 1fr 1fr; }
  .gap-detail-btns > .btn { width: 100%; justify-content: center; }
  .gap-log-line { flex-wrap: wrap; word-break: break-word; }
}

@media (max-width: 420px) {
  .hour-step-btn, .hour-action-btn { padding: 0 8px; font-size: 12px; }
  .mode-switch.group-dim-switch .mode-btn { font-size: 11px; padding: 7px 4px; }
}
</style>
