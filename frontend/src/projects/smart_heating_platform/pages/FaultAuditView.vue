<template>
  <div class="shp-page-root">
    <AppHeader />
    <main class="shp-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <header class="card elevated topbar">
        <div>
          <div class="title-row">
            <h2>异常数据监测</h2>
            <span class="badge-yin">先诊断源头缺数 · 再追溯拦截明细</span>
          </div>
          <p class="subtitle">
            实时呈现各监测主体从源站取数的完整度、自动降级补救比例与坏表隔离原因，一眼区分「源站本身没传/坏表」与系统精算口径。
          </p>
        </div>
        <div class="topbar-actions">
          <button class="btn secondary btn-sm" type="button" @click="goBackPages">
            ⬅️ 返回功能页
          </button>
          <DateStepPicker v-model="selectedDate" aria-label="选择监测日期" @change="scheduleLoadAll" />
          <select v-if="activeTab === 'tickets'" v-model.number="days" class="ctrl-input" @change="loadAll">
            <option :value="1">当天（24h）</option>
            <option :value="3">近 3 天</option>
            <option :value="7">近 7 天</option>
            <option :value="30">近 30 天</option>
          </select>
          <button class="btn primary btn-sm" type="button" :disabled="auditing" @click="handleHeatAuditFix">
            {{ auditing ? '回看修正中…' : '🔧 立即回看检测与修正' }}
          </button>
          <button class="btn secondary btn-sm" type="button" @click="exportParty('RESEARCH_INSTITUTE')">
            📥 导出下位机故障清单
          </button>
          <button class="btn secondary btn-sm" type="button" @click="exportParty('UNIVERSITY_SOFTWARE')">
            📥 导出上位机缺陷清单
          </button>
        </div>
      </header>

      <div v-if="notice.text" :class="['notice-banner', notice.type]">{{ notice.text }}</div>

      <!-- 顶部主标签页切换：1. 异常看板（默认） / 2. 取数诊断明细 / 3. 异常拦截工单明细 -->
      <nav class="card elevated tab-bar" aria-label="监测视角切换">
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'board' }]"
          @click="activeTab = 'board'"
        >
          <span>📌 异常总览看板</span>
          <span class="tab-pill">数量与占比</span>
        </button>
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'coverage' }]"
          @click="activeTab = 'coverage'"
        >
          <span>📊 当日取数诊断与源头缺损</span>
          <span class="tab-pill">{{ totalSourceGapCount }} 项源头缺损/降级</span>
        </button>
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'tickets' }]"
          @click="activeTab = 'tickets'"
        >
          <span>🛡️ 异常拦截工单明细</span>
          <span class="tab-pill">{{ summary.total_tickets ?? 0 }} 条拦截记录</span>
        </button>
      </nav>

      <!-- 标签页 1（默认）：图形化异常总览看板 -->
      <template v-if="activeTab === 'board'">
        <section v-if="coverage" ref="boardSectionEl" class="board-stack">
          <!-- 口径图例与全站汇总提示条 -->
          <div class="card elevated board-overview-bar">
            <div class="legend-pills">
              <span class="legend-chip"><i class="dot dot-ok"></i>表计直采可用</span>
              <span class="legend-chip"><i class="dot dot-est"></i>可用算法估算</span>
              <span class="legend-chip"><i class="dot dot-miss"></i>数据缺失/无法估算</span>
            </div>
            <div class="board-overview-summary">
              换热站任一维度数据异常的站有
              <strong class="text-err">{{ coverage.station.anomaly_summary?.total_anomaly_stations ?? coverage.station.anomaly_stations.length }}</strong>
              / {{ coverage.station.total }} 站（{{ pct(coverage.station.anomaly_summary?.total_anomaly_stations ?? coverage.station.anomaly_stations.length, coverage.station.total) }}%）
            </div>
          </div>

          <!-- 顶部 6 大核心指标卡片（通俗管理口径 + 微型占比条 + 点击下钻） -->
          <div class="board-kpi-strip">
            <button type="button" class="card elevated kpi-mini kpi-tone-warn" @click="jumpStationFilter('heat_anomaly')">
              <div class="kpi-mini-head">
                <span class="kpi-mini-label">🔥 换热站累计供热量数据缺失</span>
                <span class="kpi-badge badge-warn">缺 {{ pct(coverage.station.heat.missing_cum_total, coverage.station.total) }}%</span>
              </div>
              <strong class="kpi-mini-val">
                {{ coverage.station.heat.missing_cum_total }} <small>站 / {{ coverage.station.total }} 站</small>
              </strong>
              <div class="kpi-micro-bar" aria-hidden="true">
                <span class="bar-ok" :style="{ width: pct(coverage.station.heat.meter_diff_ok, coverage.station.total) + '%' }"></span>
                <span class="bar-est" :style="{ width: pct(coverage.station.heat.fallback_integral, coverage.station.total) + '%' }"></span>
                <span class="bar-miss" :style="{ width: pct(coverage.station.heat.both_missing, coverage.station.total) + '%' }"></span>
              </div>
              <span class="kpi-mini-sub"><i class="dot dot-est"></i>可用瞬时热量估算 {{ coverage.station.heat.fallback_integral }} 站（{{ pct(coverage.station.heat.fallback_integral, coverage.station.total) }}%）</span>
              <span class="kpi-mini-sub"><i class="dot dot-miss"></i>数据缺失/无法估算 {{ coverage.station.heat.both_missing }} 站（{{ pct(coverage.station.heat.both_missing, coverage.station.total) }}%）</span>
              <span v-if="coverage.station.heat.scaled_ok || coverage.station.heat.partial_fallback || coverage.station.other.sensor_or_inversion" class="kpi-mini-note">
                含倍率折算 {{ coverage.station.heat.scaled_ok }} 站、局部估算 {{ coverage.station.heat.partial_fallback }} 站、温压异常 {{ coverage.station.other.sensor_or_inversion }} 站
              </span>
              <span class="kpi-mini-foot">
                供热及工况数据异常的站有 <strong>{{ coverage.station.anomaly_summary?.heat_anomaly_stations ?? coverage.station.heat.missing_cum_total }}</strong> 站（{{ pct(coverage.station.anomaly_summary?.heat_anomaly_stations ?? coverage.station.heat.missing_cum_total, coverage.station.total) }}%）
              </span>
            </button>

            <button type="button" class="card elevated kpi-mini kpi-tone-err" @click="jumpStationFilter('water_anomaly')">
              <div class="kpi-mini-head">
                <span class="kpi-mini-label">💧 换热站累计补水量数据缺失</span>
                <span class="kpi-badge badge-err">缺 {{ pct(coverage.station.water.missing_cum_total, coverage.station.total) }}%</span>
              </div>
              <strong class="kpi-mini-val">
                {{ coverage.station.water.missing_cum_total }} <small>站 / {{ coverage.station.total }} 站</small>
              </strong>
              <div class="kpi-micro-bar" aria-hidden="true">
                <span class="bar-ok" :style="{ width: pct(coverage.station.water.meter_diff_ok, coverage.station.total) + '%' }"></span>
                <span class="bar-est" :style="{ width: pct(coverage.station.water.fallback_integral, coverage.station.total) + '%' }"></span>
                <span class="bar-miss" :style="{ width: pct(coverage.station.water.both_missing, coverage.station.total) + '%' }"></span>
              </div>
              <span class="kpi-mini-sub">
                <i class="dot dot-est"></i>可用瞬时流量估算 {{ coverage.station.water.fallback_integral }} 站（{{ pct(coverage.station.water.fallback_integral, coverage.station.total) }}%，其中 {{ coverage.station.water.fallback_zero }} 站始终为 0）
              </span>
              <span class="kpi-mini-sub"><i class="dot dot-miss"></i>数据缺失/无法估算 {{ coverage.station.water.both_missing }} 站（{{ pct(coverage.station.water.both_missing, coverage.station.total) }}%）</span>
              <span class="kpi-mini-foot">
                补水数据异常的站有 <strong>{{ coverage.station.anomaly_summary?.water_anomaly_stations ?? coverage.station.water.missing_cum_total }}</strong> 站（{{ pct(coverage.station.anomaly_summary?.water_anomaly_stations ?? coverage.station.water.missing_cum_total, coverage.station.total) }}%）
              </span>
            </button>

            <button type="button" class="card elevated kpi-mini kpi-tone-err" @click="jumpStationFilter('elec_anomaly')">
              <div class="kpi-mini-head">
                <span class="kpi-mini-label">⚡ 换热站累计耗电量数据缺失</span>
                <span class="kpi-badge badge-err">缺 {{ pct(coverage.station.elec.missing_total, coverage.station.total) }}%</span>
              </div>
              <strong class="kpi-mini-val">
                {{ coverage.station.elec.missing_total }} <small>站 / {{ coverage.station.total }} 站</small>
              </strong>
              <div class="kpi-micro-bar" aria-hidden="true">
                <span class="bar-ok" :style="{ width: pct(coverage.station.elec.meter_ok, coverage.station.total) + '%' }"></span>
                <span class="bar-miss" :style="{ width: pct(coverage.station.elec.missing_total, coverage.station.total) + '%' }"></span>
              </div>
              <span class="kpi-mini-sub">
                <i class="dot dot-miss"></i>未接入或无信号 {{ coverage.station.elec.f253_none }} 站（{{ pct(coverage.station.elec.f253_none, coverage.station.total) }}%）、读数始终为 0 {{ coverage.station.elec.f253_const_zero }} 站
              </span>
              <span class="kpi-mini-sub">
                <i class="dot dot-miss"></i>表底冻结/溢出 {{ coverage.station.elec.f253_frozen_or_overflow }} 站、表底跳变 {{ coverage.station.elec.f253_broken_isolated }} 站（无法估算）
              </span>
              <span class="kpi-mini-foot">
                耗电数据异常的站有 <strong>{{ coverage.station.anomaly_summary?.elec_anomaly_stations ?? coverage.station.elec.missing_total }}</strong> 站（{{ pct(coverage.station.anomaly_summary?.elec_anomaly_stations ?? coverage.station.elec.missing_total, coverage.station.total) }}%）
              </span>
            </button>

            <button type="button" class="card elevated kpi-mini kpi-tone-info" @click="jumpMerchantFilter('all')">
              <div class="kpi-mini-head">
                <span class="kpi-mini-label">🏬 商业用户供热数据异常</span>
                <span class="kpi-badge badge-warn">异常 {{ pct(coverage.merchant.anomaly_merchants.length, coverage.merchant.total) }}%</span>
              </div>
              <strong class="kpi-mini-val">
                {{ coverage.merchant.hourly.missing_count }} <small>户 / {{ coverage.merchant.total }} 户</small>
              </strong>
              <div class="kpi-micro-bar" aria-hidden="true">
                <span class="bar-ok" :style="{ width: pct(coverage.merchant.hourly.valid_count, coverage.merchant.total) + '%' }"></span>
                <span class="bar-miss" :style="{ width: pct(coverage.merchant.hourly.missing_count, coverage.merchant.total) + '%' }"></span>
              </div>
              <span class="kpi-mini-sub">
                <i class="dot dot-miss"></i>当日无有效热量 {{ coverage.merchant.hourly.missing_count }} 户（全天离线 {{ coverage.merchant.hourly.offline_count }} 户）
              </span>
              <span class="kpi-mini-sub">
                <template v-if="coverage.merchant.daily.has_data">
                  <i class="dot dot-est"></i>日结缺记录 {{ coverage.merchant.daily.missing_record_count }} 户、表底倒走 {{ coverage.merchant.daily.rollback_count }} 户
                </template>
                <template v-else>
                  <i class="dot dot-est"></i>传感器异常清洗 {{ coverage.merchant.hourly.fault_count }} 户 · 剔除测试户 {{ coverage.merchant.hourly.unregistered_test_count }} 户
                </template>
              </span>
              <span class="kpi-mini-foot">
                用热或仪表数据异常的商户有 <strong>{{ coverage.merchant.anomaly_merchants.length }}</strong> 户（{{ pct(coverage.merchant.anomaly_merchants.length, coverage.merchant.total) }}%）
              </span>
            </button>

            <button type="button" class="card elevated kpi-mini kpi-tone-ok" @click="jumpTempFilter('all')">
              <div class="kpi-mini-head">
                <span class="kpi-mini-label">🌡️ 居民室温采集异常</span>
                <span class="kpi-badge badge-ok">异常 {{ pct(coverage.temp_device.invalid_or_missing_total, coverage.temp_device.dict_total) }}%</span>
              </div>
              <strong class="kpi-mini-val">
                {{ coverage.temp_device.invalid_or_missing_total }} <small>户 / {{ coverage.temp_device.dict_total }} 户</small>
              </strong>
              <div class="kpi-micro-bar" aria-hidden="true">
                <span class="bar-ok" :style="{ width: pct(coverage.temp_device.valid_count, coverage.temp_device.dict_total) + '%' }"></span>
                <span class="bar-miss" :style="{ width: pct(coverage.temp_device.invalid_or_missing_total, coverage.temp_device.dict_total) + '%' }"></span>
              </div>
              <span class="kpi-mini-sub">
                <i class="dot dot-miss"></i>未回传 {{ coverage.temp_device.missing_in_source }} 户（{{ pct(coverage.temp_device.missing_in_source, coverage.temp_device.dict_total) }}%）、超7天离线 {{ coverage.temp_device.offline_gt7d }} 户
              </span>
              <span class="kpi-mini-sub">
                <i class="dot dot-est"></i>读数超正常范围 {{ coverage.temp_device.out_of_range }} 户 · 另有 {{ coverage.temp_device.unregistered_count }} 户未入正式台账
              </span>
              <span class="kpi-mini-foot">
                室温数据异常的终端有 <strong>{{ coverage.temp_device.invalid_or_missing_total + coverage.temp_device.unregistered_count }}</strong> 户（采样 {{ coverage.temp_device.snapshot_hour || '无' }}）
              </span>
            </button>

            <button type="button" class="card elevated kpi-mini kpi-tone-warn" @click="jumpUpstreamFilter('all')">
              <div class="kpi-mini-head">
                <span class="kpi-mini-label">🏭 上游热源及站基础异常</span>
                <span class="kpi-badge badge-warn">异常 {{ pct(coverage.upstream.anomaly_upstream.length, coverage.upstream.total) }}%</span>
              </div>
              <strong class="kpi-mini-val">
                {{ coverage.upstream.missing_count }} <small>处 / {{ coverage.upstream.total }} 处</small>
              </strong>
              <div class="kpi-micro-bar" aria-hidden="true">
                <span class="bar-ok" :style="{ width: pct(Math.max(0, coverage.upstream.total - coverage.upstream.anomaly_upstream.length), coverage.upstream.total) + '%' }"></span>
                <span class="bar-est" :style="{ width: pct(coverage.upstream.fault_count, coverage.upstream.total) + '%' }"></span>
                <span class="bar-miss" :style="{ width: pct(coverage.upstream.missing_count, coverage.upstream.total) + '%' }"></span>
              </div>
              <span class="kpi-mini-sub">
                <i class="dot dot-miss"></i>上游全天缺热/流量 {{ coverage.upstream.missing_count }} 处 · <i class="dot dot-est"></i>温压异常 {{ coverage.upstream.fault_count }} 处
              </span>
              <span class="kpi-mini-sub">
                <i class="dot dot-est"></i>换热站缺供热面积 {{ coverage.station.other.missing_area }} 站、温压越限/倒挂 {{ coverage.station.other.sensor_or_inversion }} 站
              </span>
              <span class="kpi-mini-foot">
                上游热源数据异常的有 <strong>{{ coverage.upstream.anomaly_upstream.length }}</strong> 处 · 拦截记录 <strong>{{ summary.total_tickets ?? 0 }}</strong> 次
              </span>
            </button>
          </div>

          <!-- 核心图形可视化区 -->
          <div class="board-charts-grid">
            <article class="card elevated board-chart-card">
              <div class="board-panel-head">
                <div>
                  <h3>📊 全网核心指标数据来源构成</h3>
                  <p class="board-panel-sub">直观对比各指标“表计直采可用 / 可用算法估算 / 数据缺失无法估算”真实占比</p>
                </div>
                <button type="button" class="btn secondary btn-xs" @click="activeTab = 'coverage'">逐站诊断 ↗</button>
              </div>
              <div ref="boardCoverageChartEl" class="board-chart-box"></div>
            </article>

            <article class="card elevated board-chart-card">
              <div class="board-panel-head">
                <div>
                  <h3>🔍 换热站计量与传感异常原因拆解</h3>
                  <p class="board-panel-sub">按异常站数降序排列（浅灰底条为全网 242 站参照，点击柱条查看站点清单）</p>
                </div>
                <button type="button" class="btn secondary btn-xs" @click="jumpStationFilter('all')">全部异常站 ↗</button>
              </div>
              <div ref="boardStationPieEl" class="board-chart-box"></div>
            </article>
          </div>
        </section>
      </template>

      <!-- 标签页 2：当日取数诊断与源头缺损总览 -->
      <template v-else-if="activeTab === 'coverage'">
        <div class="card elevated diag-callout">
          <strong>🔎 口径说明：</strong>
          <span>
            下列缺损与“0值/空值”均来自<strong>源站采集端无上传、死值冻结或表底倒走</strong>，而非本平台算错。凡具备瞬时热量/瞬时补水的站点，系统已自动采用 15 分钟积分补救；确认损坏的锯齿表底则主动置空隔离，防止虚假数据拉偏汇总。点击任意红色/橙色数字可直接查看对应站户清单。
          </span>
        </div>

        <!-- 四大主体诊断总览网格 -->
        <section class="diag-grid" v-if="coverage">
          <!-- 1. 换热站 242 座 -->
          <article class="card elevated diag-card diag-card-wide">
            <div class="diag-card-head">
              <div>
                <h3>🏭 换热站取数完整度（共 {{ coverage.station.total }} 座）</h3>
                <p class="diag-sub">
                  基础台账/运行：缺面积 <strong>{{ coverage.station.other.missing_area }}</strong> 站 · 通讯离线 <strong>{{ coverage.station.other.comm_offline }}</strong> 站 · 温压越限/倒挂 <strong>{{ coverage.station.other.sensor_or_inversion }}</strong> 站
                </p>
              </div>
              <button class="btn secondary btn-xs" type="button" @click="jumpStationFilter('all')">查看异常/降级清单 ↗</button>
            </div>

            <div class="metric-rows">
              <!-- 供热量 -->
              <div class="metric-diag-row">
                <div class="metric-diag-title">
                  <strong>🔥 供热量</strong>
                  <span class="diag-hint">首选累计热量表底 f221，缺失/跳变用瞬时热量 f222 积分兜底</span>
                </div>
                <div class="pill-group">
                  <span class="stat-pill pill-ok">表底正常 {{ coverage.station.heat.meter_diff_ok }} 站（含倍率修正 {{ coverage.station.heat.scaled_ok }} 站）</span>
                  <button type="button" class="stat-pill pill-warn clickable" @click="jumpStationFilter('heat_missing_cum')">
                    无正确累计表底 {{ coverage.station.heat.missing_cum_total }} 站
                  </button>
                  <button type="button" class="stat-pill pill-info clickable" @click="jumpStationFilter('heat_fallback')">
                    └ 已用瞬时 f222 补救 {{ coverage.station.heat.fallback_integral }} 站
                  </button>
                  <button type="button" class="stat-pill pill-err clickable" @click="jumpStationFilter('heat_zero_frozen')">
                    └ 在线零耗热/表底冻结 {{ coverage.station.other.heat_zero_frozen ?? 0 }} 站
                  </button>
                  <button type="button" class="stat-pill pill-err clickable" @click="jumpStationFilter('heat_both_missing')">
                    └ 无正确瞬时热量（彻底无热）{{ Math.max(0, (coverage.station.heat.both_missing || 0) - (coverage.station.other.heat_zero_frozen || 0)) }} 站
                  </button>
                </div>
              </div>

              <!-- 补水量 -->
              <div class="metric-diag-row">
                <div class="metric-diag-title">
                  <strong>💧 补水量</strong>
                  <span class="diag-hint">首选累计水表 f254，缺失/异常自动用瞬时补水流量 f209 积分补救</span>
                </div>
                <div class="pill-group">
                  <span class="stat-pill pill-ok">累计水表正常 {{ coverage.station.water.meter_diff_ok }} 站</span>
                  <button type="button" class="stat-pill pill-warn clickable" @click="jumpStationFilter('water_missing_cum')">
                    无正确累计水表 {{ coverage.station.water.missing_cum_total }} 站
                  </button>
                  <button type="button" class="stat-pill pill-info clickable" @click="jumpStationFilter('water_fallback')">
                    └ 已用瞬时 f209 补齐 {{ coverage.station.water.fallback_integral }} 站（有水 {{ coverage.station.water.fallback_nonzero }} / 恒0 {{ coverage.station.water.fallback_zero }}）
                  </button>
                  <button type="button" class="stat-pill pill-err clickable" @click="jumpStationFilter('water_both_missing')">
                    └ 无正确瞬时补水（彻底无水/坏表屏蔽）{{ coverage.station.water.both_missing }} 站
                  </button>
                </div>
              </div>

              <!-- 耗电量 -->
              <div class="metric-diag-row">
                <div class="metric-diag-title">
                  <strong>⚡ 耗电量</strong>
                  <span class="diag-hint">仅源站累计电表 f253（源站无瞬时电功率字段可替代），有效计电面积 {{ coverage.station.elec.ok_area_wan }} 万㎡（{{ coverage.station.elec.ok_area_pct }}%）</span>
                </div>
                <div class="pill-group">
                  <span class="stat-pill pill-ok">电表正常走字 {{ coverage.station.elec.meter_ok }} 站</span>
                  <button type="button" class="stat-pill pill-err clickable" @click="jumpStationFilter('elec_missing')">
                    无正确累计耗电 {{ coverage.station.elec.missing_total }} 站
                  </button>
                  <button type="button" class="stat-pill pill-muted clickable" @click="jumpStationFilter('elec_none')">
                    └ 未传(空) {{ coverage.station.elec.f253_none }} 站
                  </button>
                  <button type="button" class="stat-pill pill-muted clickable" @click="jumpStationFilter('elec_zero')">
                    └ 恒零死值 {{ coverage.station.elec.f253_const_zero }} 站
                  </button>
                  <button type="button" class="stat-pill pill-muted clickable" @click="jumpStationFilter('elec_frozen')">
                    └ 冻结/十亿 {{ coverage.station.elec.f253_frozen_or_overflow }} 站
                  </button>
                  <button type="button" class="stat-pill pill-warn clickable" @click="jumpStationFilter('elec_broken')">
                    └ 锯齿坏表隔离 {{ coverage.station.elec.f253_broken_isolated }} 站
                  </button>
                </div>
              </div>
            </div>
          </article>

          <!-- 2. 商业用户 464 户 -->
          <article class="card elevated diag-card">
            <div class="diag-card-head">
              <div>
                <h3>🏬 商业用户取数情况（共 {{ coverage.merchant.total }} 户）</h3>
                <p class="diag-sub">实时 15 分钟瞬时积分 + 次日 08:30 日结表底双轨采集</p>
              </div>
              <button class="btn secondary btn-xs" type="button" @click="jumpEntityTab('merchant')">查看明细 ↗</button>
            </div>
            <div class="metric-rows">
              <div class="metric-diag-row compact">
                <div class="metric-diag-title"><strong>⏱️ 当日小时积分</strong></div>
                <div class="pill-group">
                  <span class="stat-pill pill-ok">有效 {{ coverage.merchant.hourly.valid_count }} 户</span>
                  <button type="button" class="stat-pill pill-err clickable" @click="jumpMerchantFilter('hourly_bad')">
                    无有效热量 {{ coverage.merchant.hourly.missing_count }} 户（离线 {{ coverage.merchant.hourly.offline_count }} 户）
                  </button>
                  <button type="button" class="stat-pill pill-warn clickable" @click="jumpMerchantFilter('fault')">
                    触发清洗 {{ coverage.merchant.hourly.fault_count }} 户
                  </button>
                  <span class="stat-pill pill-muted">剔除未入账测试户 {{ coverage.merchant.hourly.unregistered_test_count }} 户</span>
                </div>
              </div>
              <div class="metric-diag-row compact">
                <div class="metric-diag-title"><strong>📅 日结表底</strong></div>
                <div class="pill-group" v-if="coverage.merchant.daily.has_data">
                  <span class="stat-pill pill-ok">正常 {{ coverage.merchant.daily.valid_count }} 户</span>
                  <button type="button" class="stat-pill pill-warn clickable" @click="jumpMerchantFilter('daily_bad')">
                    缺日结记录 {{ coverage.merchant.daily.missing_record_count }} 户
                  </button>
                  <button type="button" class="stat-pill pill-err clickable" @click="jumpMerchantFilter('daily_bad')">
                    表底倒走 {{ coverage.merchant.daily.rollback_count }} 户
                  </button>
                </div>
                <div class="pill-group" v-else>
                  <span class="stat-pill pill-muted">今日尚未到次日 08:30 日结采集时间（历史日期可查日结偏差）</span>
                </div>
              </div>
            </div>
          </article>

          <!-- 3. 居民室温 2,097 台账终端 -->
          <article class="card elevated diag-card">
            <div class="diag-card-head">
              <div>
                <h3>🌡️ 居民室温终端（台账 {{ coverage.temp_device.dict_total }} 户）</h3>
                <p class="diag-sub">
                  <template v-if="coverage.temp_device.snapshot_hour">
                    检查断面：{{ coverage.temp_device.snapshot_hour }}
                    <span v-if="coverage.temp_device.is_fallback_snapshot" class="text-warn">（选定日期暂无断面，已展示最近有效采样）</span>
                  </template>
                  <template v-else>当前库内暂无室温快照（请核查 Cookie 或 48h 滚动保留策略）</template>
                </p>
              </div>
              <button class="btn secondary btn-xs" type="button" @click="jumpEntityTab('temp')">查看明细 ↗</button>
            </div>
            <div class="pill-group">
              <span class="stat-pill pill-ok">有效可用 {{ coverage.temp_device.valid_count }} 户</span>
              <button type="button" class="stat-pill pill-err clickable" @click="jumpTempFilter('all')">
                无正确可用数据 {{ coverage.temp_device.invalid_or_missing_total }} 户
              </button>
              <button type="button" class="stat-pill pill-muted clickable" @click="jumpTempFilter('MISSING_IN_SOURCE')">
                └ 源站未返回 {{ coverage.temp_device.missing_in_source }} 户
              </button>
              <button type="button" class="stat-pill pill-warn clickable" @click="jumpTempFilter('OFFLINE_GT7D')">
                └ 超7天离线 {{ coverage.temp_device.offline_gt7d }} 户
              </button>
              <button type="button" class="stat-pill pill-warn clickable" @click="jumpTempFilter('OUT_OF_RANGE')">
                └ 温度越限 {{ coverage.temp_device.out_of_range }} 户
              </button>
              <button type="button" class="stat-pill pill-muted clickable" @click="jumpTempFilter('UNREGISTERED')">
                另剔除未入台账 {{ coverage.temp_device.unregistered_count }} 户
              </button>
            </div>
          </article>

          <!-- 4. 上游热源/网口 -->
          <article class="card elevated diag-card diag-card-wide">
            <div class="diag-card-head">
              <div>
                <h3>⚡ 上游热源 / 首站 / 网口（{{ coverage.upstream.total }} 测点，其中《工况一览》核心 {{ coverage.upstream.core_total }} 点）</h3>
                <p class="diag-sub">电厂/首站每 5~15 分钟采自 `/gk_get_data/`；温度/压力异常自动屏蔽并沿用前值，停运备机流量≤1 不误报</p>
              </div>
              <button class="btn secondary btn-xs" type="button" @click="jumpEntityTab('upstream')">查看明细 ↗</button>
            </div>
            <div class="pill-group">
              <span class="stat-pill pill-ok">有效采集 {{ coverage.upstream.valid_count }} 点</span>
              <button type="button" class="stat-pill pill-err clickable" @click="jumpUpstreamFilter('MISSING')">
                全天无有效热/流数据 {{ coverage.upstream.missing_count }} 点（含核心点 {{ coverage.upstream.core_missing }} 点）
              </button>
              <button type="button" class="stat-pill pill-warn clickable" @click="jumpUpstreamFilter('FAULT')">
                曾触发越限/通讯滞后 {{ coverage.upstream.fault_count }} 点
              </button>
            </div>
          </article>
        </section>

        <!-- 下钻明细表 -->
        <section class="card elevated list-card" v-if="coverage">
          <div class="drill-head">
            <div class="sub-tab-pills">
              <button type="button" :class="['kind-pill', { active: diagEntity === 'station' }]" @click="diagEntity = 'station'">
                🏭 换热站明细 ({{ stationAnomaliesFiltered.length }})
              </button>
              <button type="button" :class="['kind-pill', { active: diagEntity === 'merchant' }]" @click="diagEntity = 'merchant'">
                🏬 商业用户明细 ({{ merchantAnomaliesFiltered.length }})
              </button>
              <button type="button" :class="['kind-pill', { active: diagEntity === 'temp' }]" @click="diagEntity = 'temp'">
                🌡️ 居民室温明细 ({{ tempAnomaliesFiltered.length }})
              </button>
              <button type="button" :class="['kind-pill', { active: diagEntity === 'upstream' }]" @click="diagEntity = 'upstream'">
                ⚡ 上游测点明细 ({{ upstreamAnomaliesFiltered.length }})
              </button>
            </div>

            <div class="filter-bar">
              <select v-if="diagEntity === 'station'" v-model="stationFilter" class="ctrl-input">
                <option value="all">全部数据异常换热站</option>
                <option value="heat_anomaly">🔥 供热及工况数据异常（全部）</option>
                <option value="heat_missing_cum">└ 无正确累计供热量</option>
                <option value="heat_fallback">└ 仅用瞬时热量估算</option>
                <option value="heat_zero_frozen">└ 在线零耗热/热表冻结</option>
                <option value="heat_both_missing">❌ 供热量累计与瞬时均缺失</option>
                <option value="sensor_anomaly">🌡️ 温压越限/供回水倒挂</option>
                <option value="water_anomaly">💧 补水数据异常（全部）</option>
                <option value="water_missing_cum">└ 无正确累计补水量</option>
                <option value="water_fallback">└ 仅用瞬时流量估算（全部）</option>
                <option value="water_fallback_nonzero">└ 瞬时估算（有补水波动）</option>
                <option value="water_fallback_zero">└ 瞬时估算（数据始终为 0）</option>
                <option value="water_both_missing">❌ 补水量累计与瞬时均缺失</option>
                <option value="elec_anomaly">⚡ 耗电数据异常（全部）</option>
                <option value="elec_missing">└ 累计耗电缺失（全部）</option>
                <option value="elec_none">└ 电表未接入或无信号</option>
                <option value="elec_zero">└ 电表读数始终为 0</option>
                <option value="elec_frozen">└ 电表表底冻结/溢出</option>
                <option value="elec_broken">└ 电表表底跳变异常</option>
                <option value="missing_area">📏 台账缺失供热面积</option>
              </select>
              <select v-else-if="diagEntity === 'merchant'" v-model="merchantFilter" class="ctrl-input">
                <option value="all">全部异常/缺数商户</option>
                <option value="hourly_bad">当日小时积分缺失/离线</option>
                <option value="daily_bad">日结表底缺记录/倒走</option>
                <option value="fault">曾触发传感/倒挂清洗</option>
              </select>
              <select v-else-if="diagEntity === 'temp'" v-model="tempFilter" class="ctrl-input">
                <option value="all">全部失效/未返回/未入账终端</option>
                <option value="MISSING_IN_SOURCE">源站未返回</option>
                <option value="OFFLINE_GT7D">掉线超过 7 天</option>
                <option value="OUT_OF_RANGE">温度读数越限</option>
                <option value="UNREGISTERED">未入标准台账</option>
              </select>
              <select v-else v-model="upstreamFilter" class="ctrl-input">
                <option value="all">全部缺数/清洗测点</option>
                <option value="MISSING">全天无有效热/流数据</option>
                <option value="FAULT">曾触发越限/通讯滞后</option>
              </select>
              <input v-model="diagKeyword" type="search" class="ctrl-input" placeholder="按站名/中心/商户/原因搜索…" />
            </div>
          </div>

          <!-- 换热站明细表 -->
          <div v-if="diagEntity === 'station'" class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="换热站" sort-key="name" :sort-state="stDiagSort.state" @sort="stDiagSort.toggle" />
                  <SortableTh label="服务中心" sort-key="center_name" :sort-state="stDiagSort.state" @sort="stDiagSort.toggle" />
                  <SortableTh label="面积(万㎡)" sort-key="area_wan" :sort-state="stDiagSort.state" @sort="stDiagSort.toggle" />
                  <SortableTh label="供热计量状态" sort-key="heat_note" :sort-state="stDiagSort.state" @sort="stDiagSort.toggle" />
                  <SortableTh label="补水计量状态" sort-key="water_note" :sort-state="stDiagSort.state" @sort="stDiagSort.toggle" />
                  <SortableTh label="电表计量状态" sort-key="elec_note" :sort-state="stDiagSort.state" @sort="stDiagSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-if="stDiagSort.sortedRows.value.length === 0">
                  <td colspan="6" class="empty-td">当前筛选条件下无缺损换热站</td>
                </tr>
                <tr v-for="s in stDiagSort.sortedRows.value" :key="s.station_id">
                  <td class="font-bold">{{ s.name }}</td>
                  <td>{{ s.center_name }}</td>
                  <td class="mono">{{ s.missing_area ? '缺面积' : s.area_wan }}</td>
                  <td>
                    <span :class="['status-tag', statusClass(s.heat_status)]">{{ s.heat_note }}</span>
                  </td>
                  <td>
                    <span :class="['status-tag', statusClass(s.water_status)]">{{ s.water_note }}</span>
                  </td>
                  <td>
                    <span :class="['status-tag', statusClass(s.elec_status)]">{{ s.elec_note }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 商业用户明细表 -->
          <div v-else-if="diagEntity === 'merchant'" class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="商业户名称" sort-key="name" :sort-state="mcDiagSort.state" @sort="mcDiagSort.toggle" />
                  <SortableTh label="主干热网" sort-key="rdfz" :sort-state="mcDiagSort.state" @sort="mcDiagSort.toggle" />
                  <SortableTh label="介质" sort-key="rdry" :sort-state="mcDiagSort.state" @sort="mcDiagSort.toggle" />
                  <SortableTh label="当日小时积分情况" sort-key="hourly_note" :sort-state="mcDiagSort.state" @sort="mcDiagSort.toggle" />
                  <SortableTh label="日结表底情况" sort-key="daily_note" :sort-state="mcDiagSort.state" @sort="mcDiagSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-if="mcDiagSort.sortedRows.value.length === 0">
                  <td colspan="5" class="empty-td">当前筛选条件下无异常商业户</td>
                </tr>
                <tr v-for="m in mcDiagSort.sortedRows.value" :key="m.merchant_id">
                  <td class="font-bold">{{ m.name }}</td>
                  <td>{{ m.rdfz || '-' }}</td>
                  <td>{{ m.rdry || '-' }}</td>
                  <td><span :class="['status-tag', m.hourly_status === 'OK' ? 'tag-warn' : 'tag-err']">{{ m.hourly_note }}</span></td>
                  <td><span :class="['status-tag', m.daily_status === 'OK' || m.daily_status === 'PENDING' ? 'tag-muted' : 'tag-err']">{{ m.daily_note }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 居民室温明细表 -->
          <div v-else-if="diagEntity === 'temp'" class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="终端编码" sort-key="temp_device_id" :sort-state="tdDiagSort.state" @sort="tdDiagSort.toggle" />
                  <SortableTh label="归属换热站" sort-key="station_name" :sort-state="tdDiagSort.state" @sort="tdDiagSort.toggle" />
                  <SortableTh label="小区/门牌" sort-key="village_name" :sort-state="tdDiagSort.state" @sort="tdDiagSort.toggle" />
                  <SortableTh label="原始室温(℃)" sort-key="temp_raw" :sort-state="tdDiagSort.state" @sort="tdDiagSort.toggle" />
                  <SortableTh label="最后上报时间" sort-key="upload_time" :sort-state="tdDiagSort.state" @sort="tdDiagSort.toggle" />
                  <SortableTh label="缺损/剔除原因" sort-key="note" :sort-state="tdDiagSort.state" @sort="tdDiagSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-if="tdDiagSort.sortedRows.value.length === 0">
                  <td colspan="6" class="empty-td">当前筛选条件下无异常室温终端</td>
                </tr>
                <tr v-for="(d, i) in tdDiagSort.sortedRows.value" :key="`${d.temp_device_id}-${i}`">
                  <td class="mono">{{ d.temp_device_id }}</td>
                  <td class="font-bold">{{ d.station_name || '-' }}</td>
                  <td>{{ d.village_name || '-' }}</td>
                  <td class="mono">{{ d.temp_raw ?? '-' }}</td>
                  <td class="mono">{{ d.upload_time || '-' }}</td>
                  <td><span class="status-tag tag-err">{{ d.note }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 上游测点明细表 -->
          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="点位名称" sort-key="name" :sort-state="upDiagSort.state" @sort="upDiagSort.toggle" />
                  <SortableTh label="类别" sort-key="category" :sort-state="upDiagSort.state" @sort="upDiagSort.toggle" />
                  <SortableTh label="子系统/来源区" sort-key="sub_category" :sort-state="upDiagSort.state" @sort="upDiagSort.toggle" />
                  <SortableTh label="《工况一览》核心" sort-key="is_core_gk" :sort-state="upDiagSort.state" @sort="upDiagSort.toggle" />
                  <SortableTh label="诊断说明" sort-key="note" :sort-state="upDiagSort.state" @sort="upDiagSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-if="upDiagSort.sortedRows.value.length === 0">
                  <td colspan="5" class="empty-td">当前筛选条件下无异常上游测点</td>
                </tr>
                <tr v-for="(u, i) in upDiagSort.sortedRows.value" :key="`${u.data_zone}-${u.name}-${i}`">
                  <td class="font-bold">{{ u.name }}</td>
                  <td>{{ u.category }}</td>
                  <td>{{ u.sub_category || u.data_zone }}</td>
                  <td>{{ u.is_core_gk ? '核心点' : '非核心/字典点' }}</td>
                  <td><span :class="['status-tag', u.status === 'MISSING' ? 'tag-err' : 'tag-warn']">{{ u.note }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>

      <!-- 标签页 2：原有异常拦截工单明细 -->
      <template v-else>
        <!-- 总览统计与 ECharts 分布 -->
        <section class="summary-grid">
          <div class="summary-cards">
            <div class="card elevated stat-card">
              <span class="stat-label">时段拦截异常总数</span>
              <strong class="stat-val text-err">{{ summary.total_tickets ?? 0 }} 条</strong>
            </div>
            <div
              v-for="ow in summary.by_owner || []"
              :key="ow.owner_party"
              class="card elevated stat-card"
            >
              <span class="stat-label">{{ ow.label }}</span>
              <strong class="stat-val">{{ ow.count }} 条</strong>
            </div>
            <div class="card elevated stat-card">
              <span class="stat-label">台账待补录项</span>
              <strong class="stat-val text-warn">
                {{ summary.missing_area_stations ?? 0 }} 站缺面积 / {{ summary.missing_tag_merchants ?? 0 }} 商户缺标签
              </strong>
            </div>
          </div>
          <div class="card elevated chart-card">
            <div ref="faultChartEl" class="chart-box"></div>
          </div>
        </section>

        <!-- 异常筛选与列表 -->
        <section class="card elevated list-card">
          <div class="filter-bar">
            <select v-model="filters.owner_party" class="ctrl-input" @change="loadTickets">
              <option value="">全部问题类别</option>
              <option value="RESEARCH_INSTITUTE">下位机/传感器故障</option>
              <option value="UNIVERSITY_SOFTWARE">上位机/台账缺陷</option>
              <option value="SHARED">现场与平台协同排查</option>
            </select>
            <select v-model="filters.fault_code" class="ctrl-input" @change="loadTickets">
              <option value="">全部 7 类故障</option>
              <option value="SENSOR_OUT_OF_RANGE">1.传感器断路/越限</option>
              <option value="COMM_OFFLINE">2.通讯中断与僵尸死数</option>
              <option value="HEAT_IMBALANCE">3.一二网热平衡失真</option>
              <option value="TEMP_INVERSION">4.供回水物理倒挂</option>
              <option value="METER_JUMP">5.累计表底跳变/清零</option>
              <option value="SOFTWARE_DEFECT">6.上位机接口与台账缺陷</option>
              <option value="HEAT_METER_ZERO">7.在线站零耗热/热表挂零</option>
            </select>
            <input v-model="filters.keyword" type="search" class="ctrl-input" placeholder="搜索站点、测点或异常值…" @keyup.enter="loadTickets" />
            <button class="btn secondary btn-sm" type="button" @click="loadTickets">🔍 查询</button>
          </div>

          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <SortableTh label="发生小时" sort-key="biz_hour" :sort-state="ticketSort.state" @sort="ticketSort.toggle" />
                  <SortableTh label="主体类型" sort-key="entity_type" :sort-state="ticketSort.state" @sort="ticketSort.toggle" />
                  <SortableTh label="站点 / 测点名称" sort-key="entity_name" :sort-state="ticketSort.state" @sort="ticketSort.toggle" />
                  <SortableTh label="故障类型" sort-key="fault_label" :sort-state="ticketSort.state" @sort="ticketSort.toggle" />
                  <SortableTh label="问题类别" sort-key="owner_label" :sort-state="ticketSort.state" @sort="ticketSort.toggle" />
                  <SortableTh label="原始异常值快照" sort-key="raw_value_text" :sort-state="ticketSort.state" @sort="ticketSort.toggle" />
                  <SortableTh label="清洗处置策略" sort-key="clean_strategy" :sort-state="ticketSort.state" @sort="ticketSort.toggle" />
                </tr>
              </thead>
              <tbody>
                <tr v-if="tickets.length === 0">
                  <td colspan="7" class="empty-td">当前筛选条件下暂无异常监测记录</td>
                </tr>
                <tr v-for="t in ticketSort.sortedRows.value" :key="t.ticket_id">
                  <td class="mono">{{ t.biz_hour }}</td>
                  <td>{{ t.entity_type }}</td>
                  <td class="font-bold">{{ t.entity_name }}</td>
                  <td>{{ t.fault_label }}</td>
                  <td>
                    <span :class="['owner-pill', t.owner_party === 'UNIVERSITY_SOFTWARE' ? 'owner-uni' : 'owner-res']">
                      {{ t.owner_label }}
                    </span>
                  </td>
                  <td class="mono raw-cell">{{ t.raw_value_text }}</td>
                  <td class="muted-cell">{{ t.clean_strategy }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import '../../daily_report_25_26/styles/theme.css'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import DateStepPicker from '../components/DateStepPicker.vue'
import SortableTh from '../components/SortableTh.vue'
import { useTableSort } from '../utils/tableSort'
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  downloadPlatformExcel,
  fetchFaultCoverage,
  fetchFaultSummary,
  fetchFaultTickets,
  triggerHeatAuditFix,
} from '../services/api'

const router = useRouter()

function goBackPages() {
  router.push('/projects/smart_heating_platform/pages')
}

function todayIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const activeTab = ref('board')
const selectedDate = ref(todayIso())
const days = ref(1)
const auditing = ref(false)
const coverage = ref(null)
const summary = ref({ total_tickets: 0, by_fault_code: [], by_owner: [] })
const tickets = ref([])
const ticketSort = useTableSort(tickets)
const notice = reactive({ type: 'info', text: '' })
const filters = reactive({ owner_party: '', fault_code: '', keyword: '' })

const diagEntity = ref('station')
const stationFilter = ref('all')
const merchantFilter = ref('all')
const tempFilter = ref('all')
const upstreamFilter = ref('all')
const diagKeyword = ref('')

const totalSourceGapCount = computed(() => {
  if (!coverage.value) return 0
  const st = coverage.value.station || {}
  const mc = coverage.value.merchant || {}
  const td = coverage.value.temp_device || {}
  const up = coverage.value.upstream || {}
  return (
    (st.heat?.missing_cum_total || 0)
    + (st.water?.missing_cum_total || 0)
    + (st.elec?.missing_total || 0)
    + (mc.hourly?.missing_count || 0)
    + (td.invalid_or_missing_total || 0)
    + (up.missing_count || 0)
  )
})

const stationAnomaliesFiltered = computed(() => {
  const list = coverage.value?.station?.anomaly_stations || []
  const kw = diagKeyword.value.trim().toLowerCase()
  return list.filter((s) => {
    const f = stationFilter.value
    if (f === 'heat_anomaly' && !s.heat_anomaly) return false
    if (f === 'heat_missing_cum' && s.heat_status === 'OK') return false
    if (f === 'heat_fallback' && s.heat_status !== 'FALLBACK_INT') return false
    if (f === 'heat_zero_frozen' && !s.has_heat_zero_frozen) return false
    if (f === 'heat_both_missing' && s.heat_status !== 'BOTH_MISSING') return false
    if (f === 'sensor_anomaly' && !s.has_sensor_or_inversion) return false
    if (f === 'water_anomaly' && !s.water_anomaly) return false
    if (f === 'water_missing_cum' && s.water_status === 'OK') return false
    if (f === 'water_fallback' && s.water_status !== 'FALLBACK_INT') return false
    if (f === 'water_fallback_nonzero' && !s.water_nonzero_fallback) return false
    if (f === 'water_fallback_zero' && !s.water_zero_fallback) return false
    if (f === 'water_both_missing' && s.water_status !== 'BOTH_MISSING') return false
    if (f === 'elec_anomaly' && !s.elec_anomaly) return false
    if (f === 'elec_missing' && s.elec_status === 'OK') return false
    if (f === 'elec_none' && s.elec_status !== 'F253_NONE') return false
    if (f === 'elec_zero' && s.elec_status !== 'F253_CONST_ZERO') return false
    if (f === 'elec_frozen' && s.elec_status !== 'F253_FROZEN_OR_OVERFLOW') return false
    if (f === 'elec_broken' && s.elec_status !== 'BROKEN_ISOLATED') return false
    if (f === 'missing_area' && !s.missing_area) return false
    if (!kw) return true
    return `${s.name} ${s.center_name} ${s.heat_note} ${s.water_note} ${s.elec_note}`.toLowerCase().includes(kw)
  })
})

const merchantAnomaliesFiltered = computed(() => {
  const list = coverage.value?.merchant?.anomaly_merchants || []
  const kw = diagKeyword.value.trim().toLowerCase()
  return list.filter((m) => {
    const f = merchantFilter.value
    if (f === 'hourly_bad' && m.hourly_status === 'OK') return false
    if (f === 'daily_bad' && (m.daily_status === 'OK' || m.daily_status === 'PENDING')) return false
    if (f === 'fault' && !String(m.hourly_note || '').includes('清洗')) return false
    if (!kw) return true
    return `${m.name} ${m.rdfz || ''} ${m.hourly_note} ${m.daily_note}`.toLowerCase().includes(kw)
  })
})

const tempAnomaliesFiltered = computed(() => {
  const list = coverage.value?.temp_device?.anomaly_temp_devices || []
  const kw = diagKeyword.value.trim().toLowerCase()
  return list.filter((d) => {
    if (tempFilter.value !== 'all' && d.status_type !== tempFilter.value) return false
    if (!kw) return true
    return `${d.temp_device_id} ${d.station_name || ''} ${d.village_name || ''} ${d.note}`.toLowerCase().includes(kw)
  })
})

const upstreamAnomaliesFiltered = computed(() => {
  const list = coverage.value?.upstream?.anomaly_upstream || []
  const kw = diagKeyword.value.trim().toLowerCase()
  return list.filter((u) => {
    if (upstreamFilter.value !== 'all' && u.status !== upstreamFilter.value) return false
    if (!kw) return true
    return `${u.name} ${u.category} ${u.sub_category || ''} ${u.note}`.toLowerCase().includes(kw)
  })
})

const stDiagSort = useTableSort(stationAnomaliesFiltered)
const mcDiagSort = useTableSort(merchantAnomaliesFiltered)
const tdDiagSort = useTableSort(tempAnomaliesFiltered)
const upDiagSort = useTableSort(upstreamAnomaliesFiltered)

function pct(part, total) {
  const t = Number(total || 0)
  if (t <= 0) return '0.0'
  return ((Number(part || 0) / t) * 100).toFixed(1)
}

function statusClass(st) {
  if (st === 'OK') return 'tag-ok'
  if (st === 'FALLBACK_INT') return 'tag-info'
  if (st === 'BROKEN_ISOLATED') return 'tag-warn'
  return 'tag-err'
}

function jumpStationFilter(filterKey) {
  activeTab.value = 'coverage'
  diagEntity.value = 'station'
  stationFilter.value = filterKey
}

function jumpMerchantFilter(filterKey) {
  activeTab.value = 'coverage'
  diagEntity.value = 'merchant'
  merchantFilter.value = filterKey
}

function jumpTempFilter(filterKey) {
  activeTab.value = 'coverage'
  diagEntity.value = 'temp'
  tempFilter.value = filterKey
}

function jumpUpstreamFilter(filterKey) {
  activeTab.value = 'coverage'
  diagEntity.value = 'upstream'
  upstreamFilter.value = filterKey
}

function jumpEntityTab(ent) {
  activeTab.value = 'coverage'
  diagEntity.value = ent
}

const boardSectionEl = ref(null)
const boardCoverageChartEl = ref(null)
const boardStationPieEl = ref(null)
const faultChartEl = ref(null)
let boardCoverageChart = null
let boardStationPie = null
let faultChart = null

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '智慧供热平台精算模块', to: '/projects/smart_heating_platform/pages' },
  { label: '异常数据监测', to: null },
])

let auditSeq = 0
let auditAbortCtrl = null
let auditDebounceTimer = null

function scheduleLoadAll(delayMs = 180) {
  if (auditDebounceTimer) {
    clearTimeout(auditDebounceTimer)
    auditDebounceTimer = null
  }
  auditDebounceTimer = setTimeout(() => {
    auditDebounceTimer = null
    loadAll()
  }, delayMs)
}

async function loadCoverage(reqId, signal) {
  const res = await fetchFaultCoverage(
    { date: selectedDate.value },
    signal ? { signal } : {},
  )
  if (reqId !== auditSeq) return
  if (res?.data) {
    coverage.value = res.data
    await nextTick()
    if (reqId === auditSeq && activeTab.value === 'board') renderBoardCharts()
  }
}

async function loadSummary(reqId, signal) {
  const res = await fetchFaultSummary(
    { date: selectedDate.value, days: days.value },
    signal ? { signal } : {},
  )
  if (reqId !== auditSeq) return
  if (res?.data) {
    summary.value = res.data
    await nextTick()
    if (reqId === auditSeq && activeTab.value === 'tickets') renderChart()
  }
}

async function loadTickets(reqId = null, signal = undefined) {
  const standalone = reqId === null
  let effectiveId = reqId
  let effectiveSignal = signal
  if (standalone) {
    effectiveId = ++auditSeq
    if (auditAbortCtrl) auditAbortCtrl.abort()
    auditAbortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
    effectiveSignal = auditAbortCtrl ? auditAbortCtrl.signal : undefined
  }
  try {
    const res = await fetchFaultTickets(
      {
        date: selectedDate.value,
        days: days.value,
        ...filters,
      },
      effectiveSignal ? { signal: effectiveSignal } : {},
    )
    if (effectiveId !== auditSeq) return
    if (res?.data) tickets.value = res.data
  } catch (err) {
    if (standalone && (err?.name === 'AbortError' || effectiveId !== auditSeq)) return
    throw err
  }
}

async function loadAll() {
  if (auditDebounceTimer) {
    clearTimeout(auditDebounceTimer)
    auditDebounceTimer = null
  }
  const reqId = ++auditSeq
  if (auditAbortCtrl) {
    auditAbortCtrl.abort()
  }
  auditAbortCtrl = typeof AbortController !== 'undefined' ? new AbortController() : null
  const signal = auditAbortCtrl ? auditAbortCtrl.signal : undefined
  try {
    await Promise.all([loadCoverage(reqId, signal), loadSummary(reqId, signal), loadTickets(reqId, signal)])
  } catch (err) {
    if (err?.name === 'AbortError' || reqId !== auditSeq) return
    notice.type = 'error'
    notice.text = `加载监测数据失败：${err.message}`
  }
}

watch(activeTab, async (val) => {
  if (val === 'board') {
    faultChart?.dispose()
    faultChart = null
    await nextTick()
    renderBoardCharts()
  } else if (val === 'tickets') {
    boardCoverageChart?.dispose()
    boardCoverageChart = null
    boardStationPie?.dispose()
    boardStationPie = null
    await nextTick()
    renderChart()
  } else {
    boardCoverageChart?.dispose()
    boardCoverageChart = null
    boardStationPie?.dispose()
    boardStationPie = null
    faultChart?.dispose()
    faultChart = null
  }
})

async function handleHeatAuditFix() {
  auditing.value = true
  notice.type = 'info'
  notice.text = `正在回看检测并修正 ${selectedDate.value} 及选定范围的越限热量与倍率异常…`
  try {
    const res = await triggerHeatAuditFix({
      target_date: selectedDate.value,
      lookback_days: days.value,
    })
    const stCnt = Number(res?.fixed_station_hours || 0)
    const upCnt = Number(res?.fixed_upstream_hours || 0)
    const tktCnt = Number(res?.fault_tickets_written || 0)
    notice.type = 'success'
    notice.text = `回看检测修正完成：修正换热站 ${stCnt} 时、上游测点 ${upCnt} 时，生成/更新异常审计记录 ${tktCnt} 条。`
    await loadAll()
  } catch (err) {
    notice.type = 'error'
    notice.text = `回看检测修正失败：${err.message}`
  } finally {
    auditing.value = false
  }
}

async function exportParty(ownerParty) {
  try {
    const label = ownerParty === 'RESEARCH_INSTITUTE' ? '下位机故障' : (ownerParty === 'UNIVERSITY_SOFTWARE' ? '上位机缺陷' : '全部异常')
    await downloadPlatformExcel(
      `/faults/export?owner_party=${ownerParty}&date=${encodeURIComponent(selectedDate.value)}&days=${days.value}`,
      `智慧供热异常监测清单_${label}_${selectedDate.value}.xlsx`,
    )
  } catch (err) {
    notice.type = 'error'
    notice.text = err.message
  }
}

function renderBoardCharts() {
  if (!coverage.value) return
  const st = coverage.value.station || {}
  const mc = coverage.value.merchant || {}
  const td = coverage.value.temp_device || {}
  const up = coverage.value.upstream || {}
  const stTot = st.total || 242
  const mcTot = mc.total || 464
  const tdTot = td.dict_total || 2097
  const upTot = up.total || 82
  const toPct = (v, tot) => (tot > 0 ? Number(((Number(v || 0) / tot) * 100).toFixed(1)) : 0)
  const isNarrow = typeof window !== 'undefined' && window.innerWidth <= 640

  if (boardCoverageChartEl.value) {
    if (!boardCoverageChart) {
      boardCoverageChart = echarts.init(boardCoverageChartEl.value)
      chartResizeObserver?.observe(boardCoverageChartEl.value)
    }
    const rows = [
      {
        title: '累计供热量',
        unit: '站',
        tot: stTot,
        ok: st.heat?.meter_diff_ok || 0,
        est: st.heat?.fallback_integral || 0,
        miss: st.heat?.both_missing || 0,
      },
      {
        title: '累计补水量',
        unit: '站',
        tot: stTot,
        ok: st.water?.meter_diff_ok || 0,
        est: st.water?.fallback_integral || 0,
        miss: st.water?.both_missing || 0,
      },
      {
        title: '累计耗电量',
        unit: '站',
        tot: stTot,
        ok: st.elec?.meter_ok || 0,
        est: 0,
        miss: st.elec?.missing_total || 0,
      },
      {
        title: '商业用户供热',
        unit: '户',
        tot: mcTot,
        ok: mc.hourly?.valid_count || 0,
        est: 0,
        miss: mc.hourly?.missing_count || 0,
      },
      {
        title: '居民室温采集',
        unit: '户',
        tot: tdTot,
        ok: td.valid_count || 0,
        est: 0,
        miss: td.invalid_or_missing_total || 0,
      },
      {
        title: '上游热源监测',
        unit: '处',
        tot: upTot,
        ok: up.valid_count || 0,
        est: 0,
        miss: up.missing_count || 0,
      },
    ]
    const cats = rows.map((r) => `{t|${r.title}}\n{s|共 ${r.tot} ${r.unit}}`)
    const okPcts = rows.map((r) => toPct(r.ok, r.tot))
    const estPcts = rows.map((r) => toPct(r.est, r.tot))
    const missPcts = rows.map((r) => {
      const rest = Number((100 - toPct(r.ok, r.tot) - toPct(r.est, r.tot)).toFixed(1))
      return r.miss === 0 ? 0 : Math.max(0, rest)
    })

    boardCoverageChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(15, 23, 42, 0.04)' } },
        backgroundColor: 'rgba(15, 23, 42, 0.94)',
        borderWidth: 0,
        padding: [10, 14],
        textStyle: { color: '#f8fafc', fontSize: 12.5 },
        formatter: (params) => {
          const i = params[0]?.dataIndex ?? 0
          const r = rows[i]
          return `<div style="font-weight:700;margin-bottom:6px;font-size:13px">${r.title}（共 ${r.tot} ${r.unit}）</div>`
            + `<div style="display:flex;justify-content:space-between;gap:18px;line-height:1.7"><span><span style="color:#10b981">●</span> 表计直采可用</span><strong>${r.ok} ${r.unit} (${okPcts[i]}%)</strong></div>`
            + `<div style="display:flex;justify-content:space-between;gap:18px;line-height:1.7"><span><span style="color:#f59e0b">●</span> 可用算法估算</span><strong>${r.est} ${r.unit} (${estPcts[i]}%)</strong></div>`
            + `<div style="display:flex;justify-content:space-between;gap:18px;line-height:1.7"><span><span style="color:#ef4444">●</span> 数据缺失/无法估算</span><strong>${r.miss} ${r.unit} (${missPcts[i]}%)</strong></div>`
        },
      },
      legend: {
        top: 2,
        left: 'center',
        itemWidth: isNarrow ? 10 : 12,
        itemHeight: isNarrow ? 10 : 12,
        itemGap: isNarrow ? 10 : 18,
        icon: 'roundRect',
        textStyle: { fontSize: isNarrow ? 11 : 12.5, color: '#334155', fontWeight: 600 },
      },
      grid: { left: isNarrow ? 4 : 10, right: isNarrow ? 8 : 18, top: isNarrow ? 40 : 44, bottom: 16, containLabel: true },
      xAxis: {
        type: 'value',
        max: 100,
        axisLabel: { formatter: '{value}%', color: '#64748b', fontSize: isNarrow ? 10.5 : 11.5 },
        splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } },
      },
      yAxis: {
        type: 'category',
        inverse: true,
        data: cats,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          lineHeight: isNarrow ? 15 : 17,
          rich: {
            t: { fontSize: isNarrow ? 11 : 12.5, fontWeight: 700, color: '#0f172a' },
            s: { fontSize: isNarrow ? 10 : 11, color: '#64748b' },
          },
        },
      },
      series: [
        {
          name: '表计直采可用',
          type: 'bar',
          stack: 'total',
          barWidth: isNarrow ? 20 : 24,
          data: okPcts,
          itemStyle: { color: '#10b981', borderColor: '#ffffff', borderWidth: 2, borderRadius: 4 },
          label: { show: true, formatter: (p) => (p.value >= (isNarrow ? 14 : 10) ? `${p.value}%` : ''), color: '#fff', fontWeight: 700, fontSize: isNarrow ? 10.5 : 11.5 },
        },
        {
          name: '可用算法估算',
          type: 'bar',
          stack: 'total',
          barWidth: isNarrow ? 20 : 24,
          data: estPcts,
          itemStyle: { color: '#f59e0b', borderColor: '#ffffff', borderWidth: 2, borderRadius: 4 },
          label: { show: true, formatter: (p) => (p.value >= (isNarrow ? 14 : 9) ? `${p.value}%` : ''), color: '#fff', fontWeight: 700, fontSize: isNarrow ? 10.5 : 11.5 },
        },
        {
          name: '数据缺失/无法估算',
          type: 'bar',
          stack: 'total',
          barWidth: isNarrow ? 20 : 24,
          data: missPcts,
          itemStyle: { color: '#ef4444', borderColor: '#ffffff', borderWidth: 2, borderRadius: 4 },
          label: { show: true, formatter: (p) => (p.value >= (isNarrow ? 12 : 6) ? `${p.value}%` : ''), color: '#fff', fontWeight: 700, fontSize: isNarrow ? 10.5 : 11.5 },
        },
      ],
    }, true)
    boardCoverageChart.resize()
  }

  if (boardStationPieEl.value) {
    if (!boardStationPie) {
      boardStationPie = echarts.init(boardStationPieEl.value)
      chartResizeObserver?.observe(boardStationPieEl.value)
      boardStationPie.on('click', (p) => {
        const fk = p?.data?.filterKey
        if (fk) jumpStationFilter(fk)
      })
    }
    const items = [
      { name: '水表·无累计（有水估算）', value: st.water?.fallback_nonzero || 0, color: '#f59e0b', tag: '可用算法估算', filterKey: 'water_fallback_nonzero' },
      { name: '水表·无累计（始终为 0）', value: st.water?.fallback_zero || 0, color: '#f59e0b', tag: '可用算法估算（始终为 0）', filterKey: 'water_fallback_zero' },
      { name: '电表·未接入或无信号', value: st.elec?.f253_none || 0, color: '#ef4444', tag: '数据缺失/无法估算', filterKey: 'elec_none' },
      { name: '电表·读数始终为 0', value: st.elec?.f253_const_zero || 0, color: '#ef4444', tag: '数据缺失/无法估算', filterKey: 'elec_zero' },
      { name: '电表·表底冻结或溢出', value: st.elec?.f253_frozen_or_overflow || 0, color: '#ef4444', tag: '数据缺失/无法估算', filterKey: 'elec_frozen' },
      { name: '水表·累计与瞬时均缺失', value: st.water?.both_missing || 0, color: '#dc2626', tag: '数据缺失/无法估算', filterKey: 'water_both_missing' },
      { name: '供热·温压越限或倒挂', value: st.other?.sensor_or_inversion || 0, color: '#f59e0b', tag: '传感器/工况异常', filterKey: 'sensor_anomaly' },
      { name: '供热·仅瞬时热量可用', value: st.heat?.fallback_integral || 0, color: '#f59e0b', tag: '可用算法估算', filterKey: 'heat_fallback' },
      { name: '供热·在线零耗热/表底冻结', value: st.other?.heat_zero_frozen || 0, color: '#dc2626', tag: '数据缺失/无法估算', filterKey: 'heat_zero_frozen' },
      { name: '供热·累计与瞬时均缺失', value: Math.max(0, (st.heat?.both_missing || 0) - (st.other?.heat_zero_frozen || 0)), color: '#dc2626', tag: '数据缺失/无法估算', filterKey: 'heat_both_missing' },
      { name: '电表·表底跳变异常', value: st.elec?.f253_broken_isolated || 0, color: '#dc2626', tag: '数据缺失/无法估算', filterKey: 'elec_broken' },
    ].sort((a, b) => b.value - a.value)

    boardStationPie.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(15, 23, 42, 0.04)' } },
        backgroundColor: 'rgba(15, 23, 42, 0.94)',
        borderWidth: 0,
        padding: [10, 14],
        textStyle: { color: '#f8fafc', fontSize: 12.5 },
        formatter: (params) => {
          const d = params[0]
          const item = items[d.dataIndex]
          return `<div style="font-weight:700;margin-bottom:4px">${item.name}</div>`
            + `<div>异常规模：<strong>${item.value} / ${stTot} 站（${toPct(item.value, stTot)}%）</strong></div>`
            + `<div style="color:#cbd5e1;font-size:11.5px;margin-top:2px">性质：${item.tag} · 点击查看明细站点</div>`
        },
      },
      grid: { left: isNarrow ? 4 : 10, right: isNarrow ? 54 : 88, top: 10, bottom: 20, containLabel: true },
      xAxis: {
        type: 'value',
        max: stTot,
        axisLabel: { color: '#64748b', fontSize: isNarrow ? 10 : 11, formatter: '{value}站' },
        splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } },
      },
      yAxis: {
        type: 'category',
        inverse: true,
        data: items.map((x) => x.name),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: isNarrow ? 10.5 : 12, color: '#1e293b', fontWeight: 500 },
      },
      series: [
        {
          type: 'bar',
          barWidth: isNarrow ? 14 : 16,
          showBackground: true,
          backgroundStyle: { color: '#f1f5f9', borderRadius: [0, 6, 6, 0] },
          data: items.map((x) => ({
            value: x.value,
            filterKey: x.filterKey,
            itemStyle: { color: x.color, borderRadius: [0, 6, 6, 0] },
          })),
          label: {
            show: true,
            position: 'right',
            fontSize: isNarrow ? 10.5 : 11.5,
            fontWeight: 700,
            color: '#334155',
            formatter: (p) => (isNarrow ? `${p.value}站` : `${p.value}站 (${toPct(p.value, stTot)}%)`),
          },
        },
      ],
    }, true)
    boardStationPie.resize()
  }
}

function renderChart() {
  if (!faultChartEl.value) return
  if (!faultChart) faultChart = echarts.init(faultChartEl.value)
  const items = summary.value.by_fault_code || []
  const isNarrow = typeof window !== 'undefined' && window.innerWidth <= 640
  faultChart.setOption({
    title: { text: '6 大类数据质量异常分布', textStyle: { fontSize: isNarrow ? 12 : 13 } },
    tooltip: { trigger: 'axis' },
    grid: { left: isNarrow ? 8 : 155, right: 24, top: 36, bottom: 24, containLabel: isNarrow },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: items.map((i) => i.label).reverse() },
    series: [
      {
        type: 'bar',
        data: items.map((i) => i.count).reverse(),
        itemStyle: { color: '#b91c1c' },
        label: { show: true, position: 'right' },
      },
    ],
  }, true)
  faultChart.resize()
}

function onResize() {
  boardCoverageChart?.resize()
  boardStationPie?.resize()
  faultChart?.resize()
}

let chartResizeObserver = null
onMounted(() => {
  window.addEventListener('resize', onResize)
  if (typeof ResizeObserver !== 'undefined') {
    chartResizeObserver = new ResizeObserver(() => onResize())
    if (faultChartEl.value) chartResizeObserver.observe(faultChartEl.value)
  }
  loadAll()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartResizeObserver?.disconnect()
  if (auditDebounceTimer) clearTimeout(auditDebounceTimer)
  auditAbortCtrl?.abort()
  boardCoverageChart?.dispose()
  boardStationPie?.dispose()
  faultChart?.dispose()
})
</script>

<style scoped>
.shp-page-root { overflow-x: clip; }
.shp-main { padding: 18px 16px 40px; max-width: 1400px; width: 100%; box-sizing: border-box; margin: 0 auto; display: flex; flex-direction: column; gap: 14px; }
.shp-main > * { min-width: 0; max-width: 100%; box-sizing: border-box; }
.topbar { padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.title-row { display: flex; align-items: center; gap: 10px; }
.title-row h2 { margin: 0; font-size: 18px; }
.badge-yin { font-size: 12px; font-weight: 600; background: #fee2e2; color: #991b1b; padding: 2px 10px; border-radius: 999px; }
.subtitle { margin: 6px 0 0; font-size: 13px; color: #64748b; }
.topbar-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.ctrl-input { border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px 10px; font-size: 13px; background: #fff; }
.btn-xs { padding: 4px 10px; font-size: 12px; }
.notice-banner { padding: 10px 14px; border-radius: 8px; font-size: 13px; }
.notice-banner.info { background: #eff6ff; color: #1d4ed8; }
.notice-banner.success { background: #f0fdf4; color: #166534; }
.notice-banner.error { background: #fef2f2; color: #991b1b; }

.tab-bar { padding: 10px 14px; display: flex; gap: 10px; flex-wrap: wrap; }
.tab-btn { display: inline-flex; align-items: center; gap: 8px; padding: 9px 16px; border-radius: 8px; border: 1.5px solid #cbd5e1; background: #f8fafc; color: #334155; font-size: 14px; font-weight: 700; cursor: pointer; }
.tab-btn.active { background: #0f172a; border-color: #0f172a; color: #fff; }
.tab-pill { font-size: 11.5px; font-weight: 600; padding: 2px 8px; border-radius: 999px; background: rgba(148, 163, 184, 0.25); }
.tab-btn.active .tab-pill { background: rgba(255, 255, 255, 0.2); color: #f8fafc; }

.board-stack { display: flex; flex-direction: column; gap: 14px; }
.board-overview-bar { padding: 11px 18px; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; background: linear-gradient(90deg, #f8fafc 0%, #ffffff 100%); border: 1px solid #e2e8f0; }
.legend-pills { display: flex; gap: 18px; align-items: center; flex-wrap: wrap; font-size: 13px; font-weight: 600; color: #1e293b; }
.legend-chip { display: inline-flex; align-items: center; gap: 7px; }
.board-overview-summary { font-size: 13.5px; color: #334155; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; margin-right: 6px; vertical-align: middle; }
.legend-chip .dot { margin-right: 0; width: 10px; height: 10px; }
.dot-ok { background: #10b981; }
.dot-est { background: #f59e0b; }
.dot-miss { background: #ef4444; }

.board-kpi-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.kpi-mini { padding: 14px 16px 12px; display: flex; flex-direction: column; gap: 6px; text-align: left; border: 1px solid #e2e8f0; border-top: 3px solid #cbd5e1; background: #fff; cursor: pointer; transition: transform 0.14s ease, box-shadow 0.14s ease, border-color 0.14s ease; }
.kpi-mini:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08); }
.kpi-tone-err { border-top-color: #ef4444; }
.kpi-tone-warn { border-top-color: #f59e0b; }
.kpi-tone-info { border-top-color: #3b82f6; }
.kpi-tone-ok { border-top-color: #10b981; }
.kpi-mini-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.kpi-mini-label { font-size: 13.5px; font-weight: 700; color: #0f172a; }
.kpi-badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
.badge-err { background: #fee2e2; color: #b91c1c; }
.badge-warn { background: #fef3c7; color: #b45309; }
.badge-ok { background: #dcfce7; color: #15803d; }
.kpi-mini-val { font-size: 24px; font-weight: 800; color: #0f172a; line-height: 1.2; letter-spacing: -0.02em; }
.kpi-mini-val small { font-size: 13.5px; font-weight: 600; color: #64748b; }
.kpi-micro-bar { display: flex; height: 7px; width: 100%; border-radius: 999px; overflow: hidden; background: #f1f5f9; margin: 2px 0 3px; }
.bar-ok { background: #10b981; }
.bar-est { background: #f59e0b; }
.bar-miss { background: #ef4444; }
.kpi-mini-sub { font-size: 12.5px; color: #475569; line-height: 1.45; }
.kpi-mini-note { font-size: 11.5px; color: #64748b; line-height: 1.4; }
.kpi-mini-foot { margin-top: auto; padding: 7px 10px; border-radius: 6px; background: #f8fafc; border: 1px solid #f1f5f9; font-size: 12.5px; color: #1e293b; }

.board-charts-grid { display: grid; grid-template-columns: 1.05fr 1fr; gap: 14px; }
.board-chart-card { padding: 18px 20px; display: flex; flex-direction: column; gap: 8px; min-width: 0; border: 1px solid #e2e8f0; }
.board-panel-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
.board-panel-head h3 { margin: 0; font-size: 15.5px; font-weight: 700; color: #0f172a; }
.board-panel-sub { margin: 3px 0 0; font-size: 12px; color: #64748b; }
.board-chart-box { height: 390px; width: 100%; min-width: 0; }
@media (max-width: 1024px) { .board-kpi-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } .board-charts-grid { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .board-kpi-strip { grid-template-columns: 1fr; } .board-chart-box { height: 340px; } }

.diag-callout { padding: 12px 16px; background: #fffbeb; border: 1px solid #fde68a; font-size: 13px; color: #78350f; line-height: 1.6; }
.diag-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.diag-card-wide { grid-column: 1 / -1; }
.diag-card { padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.diag-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
.diag-card-head h3 { margin: 0; font-size: 15.5px; color: #0f172a; }
.diag-sub { margin: 4px 0 0; font-size: 12.5px; color: #64748b; }
.metric-rows { display: flex; flex-direction: column; gap: 10px; }
.metric-diag-row { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; gap: 7px; }
.metric-diag-row.compact { padding: 8px 10px; }
.metric-diag-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 13.5px; }
.diag-hint { font-size: 12px; color: #64748b; }
.pill-group { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
.stat-pill { font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 999px; border: 1px solid transparent; display: inline-flex; align-items: center; }
.stat-pill.clickable { cursor: pointer; transition: transform 0.12s ease, box-shadow 0.12s ease; }
.stat-pill.clickable:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(15, 23, 42, 0.1); }
.pill-ok { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
.pill-info { background: #dbeafe; color: #1e40af; border-color: #bfdbfe; }
.pill-warn { background: #fef3c7; color: #92400e; border-color: #fde68a; }
.pill-err { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
.pill-muted { background: #f1f5f9; color: #475569; border-color: #cbd5e1; }

.drill-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.sub-tab-pills { display: flex; gap: 8px; flex-wrap: wrap; }
.kind-pill { padding: 6px 12px; border-radius: 999px; border: 1px solid #cbd5e1; background: #f8fafc; color: #475569; font-size: 12.5px; font-weight: 600; cursor: pointer; }
.kind-pill.active { background: #1d4ed8; border-color: #1d4ed8; color: #fff; }

.status-tag { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; line-height: 1.45; }
.tag-ok { background: #f0fdf4; color: #166534; }
.tag-info { background: #eff6ff; color: #1e40af; }
.tag-warn { background: #fffbeb; color: #92400e; }
.tag-err { background: #fef2f2; color: #991b1b; }
.tag-muted { background: #f8fafc; color: #475569; }

.summary-grid { display: grid; grid-template-columns: 1fr 1.2fr; gap: 14px; }
@media (max-width: 960px) { .summary-grid, .diag-grid { grid-template-columns: 1fr; } }
.summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
.stat-card { padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 12px; color: #64748b; }
.stat-val { font-size: 18px; color: #0f172a; }
.stat-sub { font-size: 12px; color: #64748b; }
.chart-card { padding: 14px 16px; min-width: 0; overflow: hidden; }
.chart-box { height: 220px; width: 100%; min-width: 0; max-width: 100%; overflow: hidden; }
.list-card { padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.filter-bar { display: flex; gap: 10px; flex-wrap: wrap; }
.table-wrap { overflow-x: auto; max-height: 540px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th, .data-table td { padding: 9px 11px; border-bottom: 1px solid #e2e8f0; text-align: left; }
.data-table thead th { position: sticky; top: 0; background: #f8fafc; font-weight: 600; z-index: 4; }
.owner-pill { padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.owner-res { background: #ffedd5; color: #9a3412; }
.owner-uni { background: #e0e7ff; color: #3730a3; }
.raw-cell { color: #b91c1c; max-width: 260px; word-break: break-all; }
.muted-cell { color: #64748b; max-width: 240px; }
.empty-td { text-align: center !important; color: #64748b; padding: 28px !important; }
.font-bold { font-weight: 600; }
.text-err { color: #dc2626; }
.text-warn { color: #d97706; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }

@media (max-width: 768px) {
  .shp-main { padding: 12px 10px 28px; gap: 10px; }
  .topbar, .list-card, .chart-card, .diag-card, .board-chart-card { padding: 12px; }
  .title-row { flex-wrap: wrap; gap: 6px; }
  .title-row h2 { font-size: 16px; }
  .topbar-actions { width: 100%; display: grid; grid-template-columns: 1fr; gap: 8px; }
  .topbar-actions > .ctrl-input, .topbar-actions > .btn { width: 100%; justify-content: center; }
  .tab-bar { padding: 8px 10px; display: grid; grid-template-columns: 1fr; gap: 6px; }
  .tab-btn { width: 100%; justify-content: space-between; padding: 9px 12px; font-size: 13px; }
  .board-overview-bar { padding: 10px 12px; gap: 8px; }
  .legend-pills { gap: 8px 14px; font-size: 12px; }
  .board-overview-summary { font-size: 12.5px; }
  .kpi-mini-val { font-size: 21px; }
  .board-panel-head h3 { font-size: 14.5px; }
  .sub-tab-pills { width: 100%; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
  .kind-pill { text-align: center; padding: 7px 6px; font-size: 12px; }
  .summary-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .stat-card { padding: 11px 12px; }
  .filter-bar { width: 100%; gap: 8px; }
  .filter-bar > .ctrl-input { flex: 1 1 140px; min-width: 0 !important; }
  .filter-bar > .btn { width: 100%; justify-content: center; }
  .data-table { font-size: 12px; white-space: nowrap; }
  .data-table th, .data-table td { padding: 7px 8px; }
  .data-table td:first-child,
  .data-table th:first-child { position: sticky; left: 0; background: #fff; z-index: 3; max-width: 120px; overflow: hidden; text-overflow: ellipsis; box-shadow: 3px 0 6px -2px rgba(15, 23, 42, 0.08); }
  .data-table thead th:first-child { background: #f8fafc; z-index: 6; }
  .raw-cell, .muted-cell { max-width: 210px; white-space: normal; }
}
</style>
