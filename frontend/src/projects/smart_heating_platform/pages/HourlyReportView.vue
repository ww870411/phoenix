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
            <span class="badge-yang">阳面精算视图</span>
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
              <input v-model="selectedDate" type="date" class="ctrl-input" @change="onDateChange" />
            </label>
            <div class="hour-picker-group" role="group" aria-label="小时时段切换">
              <button
                class="hour-step-btn"
                type="button"
                title="上一小时"
                :disabled="selectedHour === null || selectedHour <= 0"
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
                  {{ item.label }}{{ item.has_data ? ` (${item.station_count}站)` : ' (暂无)' }}
                </option>
              </select>
              <button
                class="hour-step-btn"
                type="button"
                title="下一小时"
                :disabled="selectedHour === null || selectedHour >= 23"
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
              <button
                class="hour-action-btn"
                type="button"
                :title="playing ? '暂停 24 小时轮播' : '开启 24 小时自动轮播'"
                @click="togglePlay"
              >
                {{ playing ? '⏸ 暂停' : '▶ 轮播' }}
              </button>
            </div>
            <div class="mode-switch" role="group" aria-label="数据口径切换">
              <button
                type="button"
                :class="['mode-btn', { active: mode === 'clean' }]"
                @click="switchMode('clean')"
              >
                净化精算口径
              </button>
              <button
                type="button"
                :class="['mode-btn', { active: mode === 'raw' }]"
                @click="switchMode('raw')"
              >
                原始值对照
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
              @click="handleExport"
            >
              📥 导出本小时 Excel
            </button>
          </div>
        </div>
      </section>

      <div v-if="notice.text" :class="['notice-banner', notice.type]">{{ notice.text }}</div>

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
          <strong class="kpi-val">{{ fmt(kpis.hour_heat_gj, ' GJ') }}</strong>
          <span class="kpi-sub">瞬时负荷 {{ fmt(kpis.instant_load_gjh, ' GJ/h') }}</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">实时折算热指标</span>
          <strong class="kpi-val">{{ fmt(kpis.heat_index_wm2, ' W/㎡') }}</strong>
          <span class="kpi-sub">万平耗热 {{ fmt(kpis.heat_per_wan_gj, ' GJ/万㎡·h') }}</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">小时累计补水量</span>
          <strong class="kpi-val">{{ fmt(kpis.hour_water_t, ' t') }}</strong>
          <span class="kpi-sub">万平补水 {{ fmt(kpis.water_per_wan_t, ' t/万㎡') }}</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">一网流量加权均温</span>
          <strong class="kpi-val">{{ fmt(kpis.avg_sup_temp) }} / {{ fmt(kpis.avg_ret_temp) }} ℃</strong>
          <span class="kpi-sub">加权温差 {{ fmt(kpis.avg_temp_diff, ' ℃') }}</span>
        </div>
        <div class="card elevated kpi-card">
          <span class="kpi-label">全网真实平均室温</span>
          <strong class="kpi-val text-ok">{{ fmt(kpis.avg_room_temp, ' ℃') }}</strong>
          <span class="kpi-sub">达标率 {{ fmt(kpis.temp_pass_rate_pct, '%') }} · 舒适率 {{ fmt(kpis.temp_comfort_rate_pct, '%') }}</span>
        </div>
      </section>

      <!-- 24小时趋势图 -->
      <section class="card elevated chart-section">
        <div class="section-head">
          <h3>当日 24 小时运行负荷与供回温走势</h3>
          <button class="btn ghost btn-xs" type="button" @click="showTrendChart = !showTrendChart">
            {{ showTrendChart ? '收起图表' : '展开图表' }}
          </button>
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
                  <th>类别</th>
                  <th>子类</th>
                  <th class="sticky-col">测点标准名称</th>
                  <th>采集时间</th>
                  <th>温度 (℃)</th>
                  <th>压力 (MPa)</th>
                  <th>瞬时流量</th>
                  <th>瞬时热量</th>
                  <th>小时积分 (GJ)</th>
                  <th>数据来源</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="filteredUpstream.length === 0">
                  <td colspan="10" class="empty-td">当前时刻暂无上游数据，请点击右上角“立即采集当前时段”</td>
                </tr>
                <tr v-for="u in filteredUpstream" :key="`${u.data_zone}_${u.source_name}`" @click="openUpstreamDrawer(u)" class="clickable-row">
                  <td>{{ u.category }}</td>
                  <td>{{ u.sub_category || '-' }}</td>
                  <td class="sticky-col font-bold">{{ u.display_name }}</td>
                  <td class="mono">{{ u.source_time || '-' }}</td>
                  <td>
                    <span>{{ fmt(u.temp) }}</span>
                    <span v-if="u.value_source !== 'REAL'" class="audit-star" :title="`已清洗平滑（原值：${u.temp_raw}℃）`">*</span>
                  </td>
                  <td>{{ fmt(u.pressure, '', 3) }}</td>
                  <td>{{ fmt(u.flow) }}</td>
                  <td>{{ fmt(u.heat) }}</td>
                  <td class="font-bold">{{ fmt(u.hour_heat_gj) }}</td>
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
            <div class="mode-switch">
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
                  <th class="sticky-col">聚合主体名称</th>
                  <th>在线/总站</th>
                  <th>面积 (万㎡)</th>
                  <th>小时供热量 (GJ)</th>
                  <th>折算热指标 (W/㎡)</th>
                  <th>万平耗热 (GJ/万㎡)</th>
                  <th>小时补水 (t)</th>
                  <th>加权供/回温 (℃)</th>
                  <th>平均室温 (℃)</th>
                  <th>室温达标率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="g in activeGroupRows" :key="g.group_key">
                  <td class="sticky-col font-bold">{{ g.group_name }}</td>
                  <td>{{ g.online_stations }}/{{ g.total_stations }} ({{ g.online_rate_pct }}%)</td>
                  <td>{{ fmt(g.covered_area_wan) }}</td>
                  <td class="font-bold">{{ fmt(g.hour_heat_gj) }}</td>
                  <td>{{ fmt(g.heat_index_wm2) }}</td>
                  <td>{{ fmt(g.heat_per_wan_gj) }}</td>
                  <td>{{ fmt(g.hour_water_t) }}</td>
                  <td>{{ fmt(g.avg_sup_temp) }} / {{ fmt(g.avg_ret_temp) }}</td>
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
            <select v-model="stationFilter.mainId" class="ctrl-input" @change="onMainChange">
              <option value="">全部主干网</option>
              <option v-for="m in mainOptions" :key="m.id" :value="String(m.id)">{{ m.name }}</option>
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
                  <th class="sticky-col">换热站名称</th>
                  <th>中心 / 支线</th>
                  <th>面积 (㎡)</th>
                  <th>状态</th>
                  <th>一网供/回温 (℃)</th>
                  <th>一网供/回压 (MPa)</th>
                  <th>一网瞬时热 (GJ/h)</th>
                  <th>小时供热 (GJ)</th>
                  <th>热指标 (W/㎡)</th>
                  <th>补水 (t)</th>
                  <th>均温 (℃)</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="s in filteredStations" :key="s.station_id">
                  <tr :class="{ 'row-interp': s.value_source !== 'REAL' && s.value_source !== 'NO_DATA' }">
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
                    <td>{{ fmt(s.e3) }} / {{ fmt(s.e4) }}</td>
                    <td>{{ fmt(s.e7, '', 3) }} / {{ fmt(s.e8, '', 3) }}</td>
                    <td>{{ fmt(s.e11) }}</td>
                    <td class="font-bold">
                      {{ fmt(s.hour_heat_gj) }}
                      <span v-if="s.hour_heat_source === 'METER_DIFF'" class="meter-tag" title="表底差值校准">表</span>
                    </td>
                    <td>{{ fmt(s.heat_index_wm2) }}</td>
                    <td>{{ fmt(s.e14) }}</td>
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
                <span>阳面剔除未入账：<strong>{{ tempSummary.unregistered_excluded }}</strong></span>
              </div>
              <div ref="roomPieEl" class="pie-box"></div>
            </div>
            <div class="temp-rank-panel">
              <h4>按换热站真实室温排名（点击站名下钻单户明细）</h4>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>换热站</th>
                      <th>服务中心</th>
                      <th>有效户数</th>
                      <th>平均室温 (℃)</th>
                      <th>达标率 (≥18℃)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-if="tempSummary.station_rankings.length === 0">
                      <td colspan="5" class="empty-td">当前时刻暂无居民室温数据（请检查 Cookie 与整点采集）</td>
                    </tr>
                    <tr
                      v-for="r in tempSummary.station_rankings"
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
            <span>商业小时总耗热：<strong>{{ fmt(merchantSummary.total_hour_heat_gj, ' GJ') }}</strong></span>
            <span>商业小时总流量：<strong>{{ fmt(merchantSummary.total_hour_flow_t, ' t') }}</strong></span>
            <span>已剔除未入账测试户：<strong>{{ merchantSummary.unregistered_excluded ?? 0 }}</strong></span>
          </div>
          <div class="filter-bar">
            <select v-model="merchantFilter.rdfz" class="ctrl-input">
              <option value="">全部热源大网</option>
              <option v-for="r in merchantRdfzOptions" :key="r" :value="r">{{ r }}</option>
            </select>
            <select v-model="merchantFilter.mainId" class="ctrl-input">
              <option value="">全部主干网</option>
              <option v-for="m in merchantMainOptions" :key="m.id" :value="String(m.id)">{{ m.name }}</option>
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
                  <th class="sticky-col">商业户名称</th>
                  <th>大网 / 支线</th>
                  <th>状态</th>
                  <th>供水流量 (t/h)</th>
                  <th>供/回温 (℃)</th>
                  <th>供/回压 (MPa)</th>
                  <th>瞬时热量 (GJ/h)</th>
                  <th>小时供热量 (GJ)</th>
                  <th>小时流量 (t)</th>
                  <th>阀门开度 (%)</th>
                  <th>数据来源</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="filteredMerchants.length === 0">
                  <td colspan="11" class="empty-td">暂无匹配的商业用户小时数据</td>
                </tr>
                <tr v-for="m in filteredMerchants" :key="m.merchant_id">
                  <td class="sticky-col font-bold">
                    {{ m.name }}
                    <span
                      v-if="m.value_source !== 'REAL' && m.value_source !== 'NO_DATA'"
                      class="audit-star"
                      :title="`数据状态：${sourceLabel(m.value_source)}`"
                    >*</span>
                  </td>
                  <td class="muted-cell">{{ m.rdfz || '-' }} / {{ m.branch_name }}</td>
                  <td>
                    <span :class="['src-pill', m.online ? 'src-real' : 'src-off']">
                      {{ m.online ? '在线' : (m.has_record ? '离线' : '无数据') }}
                    </span>
                  </td>
                  <td>{{ fmt(m.flow) }}</td>
                  <td>{{ fmt(m.temp_sup) }} / {{ fmt(m.temp_ret) }}</td>
                  <td>{{ fmt(m.pres_sup, '', 3) }} / {{ fmt(m.pres_ret, '', 3) }}</td>
                  <td>{{ fmt(m.heat) }}</td>
                  <td class="font-bold">{{ fmt(m.hour_heat_gj) }}</td>
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
                  <th>小时</th>
                  <th>温度 (℃)</th>
                  <th>压力 (MPa)</th>
                  <th>瞬时流量</th>
                  <th>瞬时热量</th>
                  <th>积分热量 (GJ)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pt in drawer.rows" :key="pt.hour">
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
                  <th>门牌号</th>
                  <th>型号</th>
                  <th>清洗室温 (℃)</th>
                  <th>原始室温</th>
                  <th>最后上传</th>
                  <th>状态</th>
                  <th>巡检备注</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in drawer.rows" :key="d.temp_device_id">
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
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  downloadPlatformExcel,
  fetchHourlyReport,
  fetchStationTempDevices,
  fetchUpstreamTrend24h,
  triggerManualCollect,
} from '../services/api'

function todayIso() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const selectedDate = ref('')
const selectedHour = ref(null)
const mode = ref('clean')
const loading = ref(false)
const collecting = ref(false)
const calibrating = ref(false)
const playing = ref(false)
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
const stationFilter = reactive({ centerId: '', mainId: '', branchId: '', statusFilter: '', keyword: '' })
const merchantFilter = reactive({ rdfz: '', mainId: '', statusFilter: '', keyword: '' })
const drawer = reactive({ open: false, kind: '', title: '', rows: [] })

const heatChartEl = ref(null)
const tempChartEl = ref(null)
const roomPieEl = ref(null)
let heatChart = null
let tempChart = null
let roomPieChart = null
let playTimer = null
let chartResizeObserver = null

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热旁路精算与质检平台', to: '/projects/smart_heating_platform/pages' },
  { label: '逐小时精细化运行报告', to: null },
])

const reportTabs = [
  { key: 'groups', label: '🏢 中心/大网小时汇总' },
  { key: 'upstream', label: '🔥 热源与首站' },
  { key: 'stations', label: '🏭 242座换热站明细' },
  { key: 'merchants', label: '🏬 464商业用户小时明细' },
  { key: 'temps', label: '🌡️ 居民室温达标分布' },
]

const groupDimensions = [
  { key: 'by_center', label: '按 9 大服务中心' },
  { key: 'by_rdfz', label: '按 9 大热源大网' },
  { key: 'by_main', label: '按 15 条主干网' },
  { key: 'by_branch', label: '按 41 条支线网' },
]

const meta = computed(() => reportData.value.meta || {})
const kpis = computed(() => reportData.value.kpis || {})
const trend24h = computed(() => reportData.value.trend_24h || [])
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

const mainOptions = computed(() => {
  const map = new Map()
  for (const s of reportData.value.stations || []) {
    if (stationFilter.centerId && String(s.center_id) !== stationFilter.centerId) continue
    if (!map.has(s.main_network_id)) map.set(s.main_network_id, s.main_name)
  }
  return Array.from(map.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.id - b.id)
})

const branchOptions = computed(() => {
  const map = new Map()
  for (const s of reportData.value.stations || []) {
    if (stationFilter.centerId && String(s.center_id) !== stationFilter.centerId) continue
    if (stationFilter.mainId && String(s.main_network_id) !== stationFilter.mainId) continue
    if (!map.has(s.branch_network_id)) map.set(s.branch_network_id, s.branch_name)
  }
  return Array.from(map.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.id - b.id)
})

const filteredStations = computed(() => {
  const kw = stationFilter.keyword.trim().toLowerCase()
  return (reportData.value.stations || []).filter((s) => {
    if (stationFilter.centerId && String(s.center_id) !== stationFilter.centerId) return false
    if (stationFilter.mainId && String(s.main_network_id) !== stationFilter.mainId) return false
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

const merchantMainOptions = computed(() => {
  const map = new Map()
  for (const m of reportData.value.merchants || []) {
    if (!map.has(m.main_network_id)) map.set(m.main_network_id, m.main_name)
  }
  return Array.from(map.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.id - b.id)
})

const filteredMerchants = computed(() => {
  const kw = merchantFilter.keyword.trim().toLowerCase()
  return (reportData.value.merchants || []).filter((m) => {
    if (merchantFilter.rdfz && m.rdfz !== merchantFilter.rdfz) return false
    if (merchantFilter.mainId && String(m.main_network_id) !== merchantFilter.mainId) return false
    if (merchantFilter.statusFilter === 'ACTIVE' && !(m.heat > 0)) return false
    if (merchantFilter.statusFilter === 'ONLINE' && !m.online) return false
    if (merchantFilter.statusFilter === 'OFFLINE' && m.online) return false
    if (kw && !`${m.name || ''} ${m.branch_name || ''}`.toLowerCase().includes(kw)) return false
    return true
  })
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
  return src || '-'
}

function onCenterChange() {
  stationFilter.mainId = ''
  stationFilter.branchId = ''
}
function onMainChange() {
  stationFilter.branchId = ''
}

async function loadReport() {
  loading.value = true
  try {
    const params = { mode: mode.value }
    if (selectedDate.value) params.date = selectedDate.value
    if (selectedHour.value !== null && selectedHour.value !== undefined) params.hour = selectedHour.value
    const res = await fetchHourlyReport(params)
    if (res?.data) {
      reportData.value = res.data
      if (res.data.meta?.date) selectedDate.value = res.data.meta.date
      if (res.data.meta?.hour !== undefined && res.data.meta?.hour !== null) {
        selectedHour.value = Number(res.data.meta.hour)
      }
      await nextTick()
      renderCharts()
    }
  } catch (err) {
    notice.type = 'error'
    notice.text = `加载逐小时报告失败：${err.message}`
  } finally {
    loading.value = false
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

function stepHour(delta) {
  const cur = Number(selectedHour.value ?? 0)
  const next = Math.max(0, Math.min(23, cur + delta))
  if (next !== cur) {
    selectedHour.value = next
    loadReport()
  }
}
function switchMode(m) {
  mode.value = m
  loadReport()
}

function togglePlay() {
  if (playing.value) {
    playing.value = false
    if (playTimer) clearInterval(playTimer)
    playTimer = null
    return
  }
  playing.value = true
  playTimer = setInterval(() => {
    selectedHour.value = (Number(selectedHour.value ?? 0) + 1) % 24
    loadReport()
  }, 2500)
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

async function handleExport() {
  try {
    await downloadPlatformExcel(
      `/reports/hourly/export?date=${encodeURIComponent(selectedDate.value)}&hour=${selectedHour.value}&mode=${mode.value}`,
      `逐小时精细化运行报告_${selectedDate.value}_${String(selectedHour.value).padStart(2, '0')}时.xlsx`,
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

function renderCharts() {
  const rows = trend24h.value
  const labels = rows.map((r) => r.label)
  const isNarrow = typeof window !== 'undefined' && window.innerWidth <= 640

  if (heatChartEl.value) {
    if (!heatChart) heatChart = echarts.init(heatChartEl.value)
    heatChart.setOption({
      title: { text: '全网小时供热量 (GJ) & 室外气温 (℃)', textStyle: { fontSize: isNarrow ? 12 : 13 } },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0, type: 'scroll', data: ['小时供热量(GJ)', '热指标(W/㎡)', '室外气温(℃)'] },
      grid: { left: isNarrow ? 8 : 48, right: isNarrow ? 8 : 48, top: 40, bottom: 38, containLabel: true },
      xAxis: { type: 'category', data: labels },
      yAxis: [
        { type: 'value', name: isNarrow ? '' : 'GJ / W/㎡' },
        { type: 'value', name: isNarrow ? '' : '℃' },
      ],
      series: [
        { name: '小时供热量(GJ)', type: 'bar', data: rows.map((r) => r.hour_heat_gj), itemStyle: { color: '#2563eb' } },
        { name: '热指标(W/㎡)', type: 'line', smooth: true, data: rows.map((r) => r.heat_index_wm2), itemStyle: { color: '#f59e0b' } },
        { name: '室外气温(℃)', type: 'line', yAxisIndex: 1, smooth: true, data: rows.map((r) => r.outdoor_temp), itemStyle: { color: '#06b6d4' } },
      ],
    }, true)
    heatChart.resize()
  }

  if (tempChartEl.value) {
    if (!tempChart) tempChart = echarts.init(tempChartEl.value)
    tempChart.setOption({
      title: { text: '一网流量加权供回温 & 真实平均室温 (℃)', textStyle: { fontSize: isNarrow ? 12 : 13 } },
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0, type: 'scroll', data: ['一网供温', '一网回温', '平均室温'] },
      grid: { left: isNarrow ? 8 : 45, right: isNarrow ? 8 : 20, top: 40, bottom: 38, containLabel: true },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value', name: isNarrow ? '' : '℃' },
      series: [
        { name: '一网供温', type: 'line', smooth: true, data: rows.map((r) => r.avg_sup_temp), itemStyle: { color: '#dc2626' } },
        { name: '一网回温', type: 'line', smooth: true, data: rows.map((r) => r.avg_ret_temp), itemStyle: { color: '#2563eb' } },
        { name: '平均室温', type: 'line', smooth: true, data: rows.map((r) => r.avg_room_temp), itemStyle: { color: '#10b981' } },
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
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartResizeObserver?.disconnect()
  if (playTimer) clearInterval(playTimer)
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
.slot-badge { font-size: 12px; background: #eff6ff; color: #1e40af; padding: 2px 10px; border-radius: 999px; border: 1px solid #bfdbfe; }
.run-meta { font-size: 12px; color: #64748b; }
.control-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.inline-field { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: #334155; }
.ctrl-input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 10px; font-size: 13px; background: #fff; }
.hour-picker-group { display: inline-flex; align-items: center; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; background: #fff; }
.hour-step-btn, .hour-action-btn { border: none; background: #f8fafc; color: #334155; padding: 6px 9px; font-size: 12px; font-weight: 600; cursor: pointer; border-right: 1px solid #e2e8f0; }
.hour-action-btn:last-child { border-right: none; }
.hour-step-btn:hover:not(:disabled), .hour-action-btn:hover:not(:disabled) { background: #eff6ff; color: #1d4ed8; }
.hour-step-btn:disabled, .hour-action-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.hour-select { border: none; border-right: 1px solid #e2e8f0; border-radius: 0; padding: 6px 8px; min-width: 122px; font-weight: 600; color: #0f172a; }
.mode-switch { display: inline-flex; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; }
.mode-btn { padding: 6px 12px; font-size: 12px; border: none; background: #f8fafc; color: #475569; cursor: pointer; font-weight: 600; }
.mode-btn.active { background: #1d4ed8; color: #fff; }
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

@media (max-width: 768px) {
  .shp-main { padding: 12px 10px 28px; gap: 10px; }
  .control-bar { position: static; padding: 12px; gap: 10px; }
  .control-left { gap: 6px; }
  .control-left h2 { font-size: 16px; line-height: 1.35; }
  .control-right { width: 100%; display: grid; grid-template-columns: 1fr; gap: 8px; }
  .inline-field { width: 100%; justify-content: space-between; }
  .inline-field .ctrl-input { flex: 1; min-width: 0; }
  .hour-picker-group { width: 100%; display: flex; }
  .hour-select { flex: 1; min-width: 0; }
  .mode-switch { width: 100%; display: grid; grid-template-columns: 1fr 1fr; }
  .control-right > .btn { width: 100%; justify-content: center; }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .kpi-grid > .kpi-card:last-child { grid-column: 1 / -1; }
  .kpi-card { padding: 11px 12px; }
  .kpi-val { font-size: 16px; }
  .chart-section, .report-tabs-card { padding: 12px; }
  .chart-pair { grid-template-columns: 1fr; gap: 12px; }
  .chart-box { height: 220px; }
  .tab-bar { flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; gap: 6px; padding-bottom: 8px; }
  .tab-btn { flex-shrink: 0; padding: 7px 12px; font-size: 12px; }
  .filter-bar { gap: 8px; }
  .filter-bar > .ctrl-input { flex: 1 1 140px; min-width: 0; }
  .data-table { font-size: 12px; }
  .data-table th, .data-table td { padding: 7px 8px; }
  .sticky-col { max-width: 132px; overflow: hidden; text-overflow: ellipsis; }
  .temp-stat-badges { grid-template-columns: 1fr; }
  .pie-box { height: 240px; }
  .drawer-panel { width: 100vw; padding: 14px; }
}

@media (max-width: 420px) {
  .hour-step-btn, .hour-action-btn { padding: 6px 7px; font-size: 11px; }
}
</style>
