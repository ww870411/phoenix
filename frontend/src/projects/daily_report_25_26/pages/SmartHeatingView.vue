<template>
  <div class="smart-heating-view">
    <AppHeader />
    <main class="smart-main" :class="{ 'overview-main': activeTab === 'overview' }">
      <Breadcrumbs :items="breadcrumbItems" />

      <div class="page-tabs" role="tablist" aria-label="智慧供热信息">
        <button id="source-tab" type="button" role="tab" :aria-selected="activeTab === 'source'" aria-controls="source-panel" @click="activeTab = 'source'">热源信息</button>
        <button id="overview-tab" type="button" role="tab" :aria-selected="activeTab === 'overview'" aria-controls="overview-panel" @click="activeTab = 'overview'">工况一览</button>
      </div>

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
                {{ activeTab === 'source' ? '按全网统一分类标准实时采集 · 涵盖首站、电厂、一次网三大层级 344 个标准采集点' : '重点生产工况 · 涵盖电厂、首站、一网、换热站及商户 82 项参数' }}
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
              <!-- 本地开发环境专属一键从线上同步按钮 -->
              <button
                v-if="isLocalhost"
                class="btn secondary btn-sm btn-sync-remote"
                type="button"
                :disabled="isSyncingRemote"
                title="本地开发环境专用：直接从远程生产服务器中继拉取最新工况"
                @click="handleSyncFromRemote"
              >
                {{ isSyncingRemote ? '同步中…' : '📥 从线上中继同步' }}
              </button>

              <!-- 服务器中继配置开关按钮 -->
              <button
                class="btn secondary btn-sm btn-relay-cfg"
                :class="{ 'relay-active': relayConfig.forward_enabled }"
                type="button"
                title="设置服务器是否向本地开发环境或其他节点中继转发实时数据"
                @click="showRelayModal = true"
              >
                <span class="relay-dot" :class="{ 'on': relayConfig.forward_enabled }"></span>
                <span>服务器中继: {{ relayConfig.forward_enabled ? '已开启' : '已关闭' }}</span>
              </button>

              <!-- 客户端脚本下载：严格仅限 Global_admin -->
              <button
                v-if="isGlobalAdmin"
                class="btn secondary btn-sm btn-download"
                type="button"
                :disabled="downloading"
                title="下载专用的数据同步客户端脚本 (仅限 Global_admin)"
                @click="handleDownloadScript"
              >
                {{ downloading ? '下载中…' : '📥 客户端脚本' }}
              </button>

              <label class="auto-refresh-toggle">
                <input v-model="autoRefresh" type="checkbox" />
                <span>自动刷新</span>
              </label>
              <label class="refresh-interval-control">
                <span>刷新间隔</span>
                <select v-model.number="refreshIntervals[activeTab]" aria-label="当前标签页刷新间隔，仅本次页面有效" title="仅本次页面有效，重新打开恢复 1m">
                  <option :value="15000">15s</option>
                  <option :value="30000">30s</option>
                  <option :value="60000">1m</option>
                  <option :value="120000">2m</option>
                  <option :value="300000">5m</option>
                </select>
              </label>

              <button class="btn primary btn-sm" :disabled="loading" @click="fetchData">
                {{ loading ? '刷新中…' : '立即刷新 ⟳' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 核心指标摘要条 -->
        <div v-show="activeTab === 'source'" class="metric-strip">
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
            <span class="metric-hint">一次网供水加权平均</span>
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
            <span class="metric-label">标准采集点在线数</span>
            <div class="metric-val-row">
              <span class="metric-value text-success">{{ isRelayOnline ? totalOnlinePointCount : 0 }}</span>
              <span class="metric-unit">/ 344 个</span>
            </div>
            <span class="metric-hint">按主体分组表规范入库</span>
          </div>
        </div>
      </section>

      <SmartHeatingOverview v-if="activeTab === 'overview'" id="overview-panel" role="tabpanel" aria-labelledby="overview-tab"
        :data="latestPayload.gk_data || null" :collected-epoch="latestPayload.gk_collected_epoch || null" :online="isRelayOnline" :now="currentTime" />

      <div v-show="activeTab === 'source'" id="source-panel" role="tabpanel" aria-labelledby="source-tab">
      <!-- 未连接提示横幅 -->
      <section v-if="!isRelayOnline" class="card elevated offline-callout">
        <div class="offline-icon">🔌</div>
        <div class="offline-body">
          <div class="offline-title">数据链路未连接 · 暂无实时数据</div>
          <div class="offline-desc">
            系统严格遵循实时数据规范，在未接收到客户端推流前不呈现任何数据。
            <template v-if="isLocalhost">
              检测到当前处于<strong>本地开发环境 (localhost)</strong>：若服务器已开启中继，您可以直接点击右侧按钮一键从线上同步实时数据流。
            </template>
            <template v-else>
              请在办公电脑上运行数据同步客户端（smart_heating_relay_win7.py）以开启全网实时推流。
            </template>
          </div>
        </div>
        <div class="callout-actions">
          <button
            v-if="isLocalhost"
            class="btn primary btn-sm btn-callout-sync"
            type="button"
            :disabled="isSyncingRemote"
            @click="handleSyncFromRemote"
          >
            {{ isSyncingRemote ? '同步中…' : '📥 从线上中继拉取数据' }}
          </button>
          <button
            v-if="isGlobalAdmin"
            class="btn secondary btn-sm btn-callout-dl"
            type="button"
            :disabled="downloading"
            title="下载专用的数据同步客户端脚本 (仅限 Global_admin)"
            @click="handleDownloadScript"
          >
            {{ downloading ? '下载中…' : '📥 客户端脚本' }}
          </button>
        </div>
      </section>

      <!-- 分类与筛选工具栏 -->
      <div class="nav-and-filter-card card elevated">
        <div class="category-tabs-wrapper">
          <span class="filter-label-prefix">一级分类:</span>
          <div class="tabs-container">
            <button
              class="tab-btn"
              :class="{ active: currentLevel1 === '首站' }"
              @click="handleLevel1Change('首站')"
            >
              🔄 首站 ({{ countByLevel1['首站'] || 54 }})
            </button>
            <button
              class="tab-btn"
              :class="{ active: currentLevel1 === '电厂' }"
              @click="handleLevel1Change('电厂')"
            >
              ⚡ 电厂 ({{ countByLevel1['电厂'] || 48 }})
            </button>
            <button
              class="tab-btn"
              :class="{ active: currentLevel1 === '一次网' }"
              @click="handleLevel1Change('一次网')"
            >
              🏢 一次网 ({{ countByLevel1['一次网'] || 242 }})
            </button>
            <button
              class="tab-btn"
              :class="{ active: currentLevel1 === 'all' }"
              @click="handleLevel1Change('all')"
            >
              🌐 全网总览 ({{ totalTaxonomyCount }})
            </button>
          </div>
        </div>

        <div class="filter-controls-wrapper">
          <!-- 二级分类下拉 -->
          <div class="selector-group">
            <span class="filter-label">二级分类:</span>
            <select v-model="selectedLevel2" class="select-box">
              <option value="all">
                {{ currentLevel1 === 'all' ? '全部二级分类 (15个)' : `全部${currentLevel1} (${currentLevel2Options.length}个)` }}
              </option>
              <option v-for="opt in currentLevel2Options" :key="opt.name" :value="opt.name">
                {{ opt.name }} ({{ opt.count }}个采集点)
              </option>
            </select>
          </div>

          <!-- 采集点搜索框 -->
          <div class="search-group">
            <span class="filter-label">采集点:</span>
            <input
              v-model="searchKeyword"
              type="text"
              class="input-search"
              placeholder="搜索采集点名称 (如: 进汽, 锅炉, 碧海)..."
            />
          </div>

          <!-- 排序选择 -->
          <div class="selector-group">
            <span class="filter-label">排序:</span>
            <select v-model="sortBy" class="select-box">
              <option value="default">默认顺序 (按表严格排序)</option>
              <option value="temp_desc">温度从高到低</option>
              <option value="temp_asc">温度从低到高</option>
              <option value="flow_desc">瞬时流量从大到小</option>
              <option v-if="currentLevel1 === '一次网'" value="diff_desc">供回温差从大到小</option>
            </select>
          </div>
        </div>
      </div>

      <!-- 手机窄屏使用同一筛选结果生成卡片，保留完整测点参数。 -->
      <SmartHeatingPointCards :items="displayList" :online="isRelayOnline" />

      <!-- 数据内容展示区域 -->

      <!-- 视图 1: 首站采集点矩阵 -->
      <section v-if="currentLevel1 === '首站'" class="card elevated data-section">
        <header class="section-header">
          <div class="header-left">
            <h3>首站工况实时监测矩阵</h3>
            <span class="badge-count">{{ isRelayOnline ? displayList.length : 0 }} 个采集点</span>
          </div>
          <span class="header-tip">覆盖北海#1首站、北海#2首站、北海水炉、香海首站等全部回路与泵组</span>
        </header>

        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 50px;">#</th>
                <th style="width: 90px;">一级分类</th>
                <th style="width: 120px;">二级分类</th>
                <th style="width: 220px;">采集点</th>
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
              <tr v-for="(item, idx) in displayList" :key="item.pointName || idx">
                <td class="col-center text-muted font-mono font-bold">{{ item.order || idx + 1 }}</td>
                <td class="col-center">
                  <span class="badge-level1 badge-sz">首站</span>
                </td>
                <td class="col-center">
                  <span class="badge-level2">{{ item.level2 }}</span>
                </td>
                <td class="col-station font-bold">
                  <span class="circuit-tag" :class="getCircuitTagClass(item.pointName)">{{ getCircuitType(item.pointName) }}</span>
                  {{ item.pointName }}
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
              <tr v-if="displayList.length === 0">
                <td colspan="11" class="empty-cell">
                  {{ isRelayOnline ? '未检索到符合条件的首站采集点' : '数据链路未连接，暂无实时数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 视图 2: 电厂采集点矩阵 -->
      <section v-if="currentLevel1 === '电厂'" class="card elevated data-section">
        <header class="section-header">
          <div class="header-left">
            <h3>热电厂机组与热源监测矩阵</h3>
            <span class="badge-count">{{ isRelayOnline ? displayList.length : 0 }} 个采集点</span>
          </div>
          <span class="header-tip">按分组规范收录北海电厂 (23项)、香海电厂 (25项) 全部锅炉、机组进汽与联络管</span>
        </header>

        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 50px;">#</th>
                <th style="width: 90px;">一级分类</th>
                <th style="width: 120px;">二级分类</th>
                <th style="width: 220px;">采集点</th>
                <th>运行温度</th>
                <th>主汽压力</th>
                <th>瞬时流量</th>
                <th>瞬时热量</th>
                <th>采集时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in displayList" :key="item.pointName || idx">
                <td class="col-center text-muted font-mono font-bold">{{ item.order || idx + 1 }}</td>
                <td class="col-center">
                  <span class="badge-level1 badge-dc">电厂</span>
                </td>
                <td class="col-center">
                  <span
                    class="badge-level2"
                    :class="item.level2 === '香海电厂' ? 'tag-xianghai' : 'tag-beihai'"
                  >
                    {{ item.level2 }}
                  </span>
                </td>
                <td class="col-station font-bold">
                  <span class="plant-tag" :class="getPlantTagClass(item.pointName)">{{ getPlantType(item.pointName) }}</span>
                  {{ item.pointName }}
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
              <tr v-if="displayList.length === 0">
                <td colspan="9" class="empty-cell">
                  {{ isRelayOnline ? '未检索到符合条件的电厂采集点' : '数据链路未连接，暂无实时数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 视图 3: 一次网换热站采集点矩阵 -->
      <section v-if="currentLevel1 === '一次网'" class="card elevated data-section">
        <header class="section-header">
          <div class="header-left">
            <h3>换热站一次网实时监测矩阵</h3>
            <span class="badge-count">{{ isRelayOnline ? displayList.length : 0 }} 个采集点</span>
          </div>
          <span class="header-tip">按分组规范覆盖 9 大供热中心全网 242 座换热站</span>
        </header>

        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 50px;">#</th>
                <th style="width: 90px;">一级分类</th>
                <th style="width: 120px;">二级分类</th>
                <th style="width: 180px;">采集点</th>
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
              <tr v-for="(item, idx) in displayList" :key="item.pointName || idx">
                <td class="col-center text-muted font-mono font-bold">{{ item.order || idx + 1 }}</td>
                <td class="col-center">
                  <span class="badge-level1 badge-yw">一次网</span>
                </td>
                <td class="col-center">
                  <span class="badge-level2">{{ item.level2 }}</span>
                </td>
                <td class="col-station font-bold">{{ item.pointName }}</td>
                <td class="col-num text-warm font-mono font-bold">
                  {{ formatVal(item.f3, '℃') }}
                </td>
                <td class="col-num text-cool font-mono">
                  {{ formatVal(item.f5, '℃') }}
                </td>
                <td class="col-num font-mono">
                  <span class="diff-badge" :class="getTempDiffBadgeClass(item.f3, item.f5)">
                    {{ calcDiff(item.f3, item.f5, '℃') }}
                  </span>
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.f1, 'MPa', 3) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.f4, 'MPa', 3) }}
                </td>
                <td class="col-num font-mono">
                  {{ calcDiff(item.f1, item.f4, 'MPa', 3) }}
                </td>
                <td class="col-num font-mono font-bold">
                  {{ formatVal(item.f2, 'm³/h', 1) }}
                </td>
                <td class="col-num font-mono">
                  {{ formatVal(item.f222, 'GJ/h', 1) }}
                </td>
                <td class="col-center font-mono text-muted text-sm">
                  {{ item.update_time || item.SHIJIAN || '—' }}
                </td>
              </tr>
              <tr v-if="displayList.length === 0">
                <td colspan="13" class="empty-cell">
                  {{ isRelayOnline ? '未检索到符合条件的一次网换热站采集点' : '数据链路未连接，暂无实时数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 视图 4: 全网采集点总览 (344 个标准采集点，严格按 Excel 顺序) -->
      <section v-if="currentLevel1 === 'all'" class="card elevated data-section">
        <header class="section-header">
          <div class="header-left">
            <h3>全网标准采集点总览矩阵</h3>
            <span class="badge-count">{{ isRelayOnline ? displayList.length : 0 }} 个采集点</span>
          </div>
          <span class="header-tip">严格按《11.3 智慧供热平台主体分组表》顺序展示全网 344 项标准采集点工况</span>
        </header>

        <div class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width: 60px;">序号</th>
                <th style="width: 100px;">一级分类</th>
                <th style="width: 130px;">二级分类</th>
                <th style="width: 220px;">采集点</th>
                <th>核心温度</th>
                <th>核心压力</th>
                <th>瞬时流量</th>
                <th>瞬时热量</th>
                <th>工况分类参数</th>
                <th>采集时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in displayList" :key="item.pointName || idx">
                <td class="col-center text-muted font-mono font-bold">{{ item.order || idx + 1 }}</td>
                <td class="col-center">
                  <span
                    class="badge-level1"
                    :class="{
                      'badge-sz': item.level1 === '首站',
                      'badge-dc': item.level1 === '电厂',
                      'badge-yw': item.level1 === '一次网'
                    }"
                  >
                    {{ item.level1 }}
                  </span>
                </td>
                <td class="col-center">
                  <span class="badge-level2">{{ item.level2 }}</span>
                </td>
                <td class="col-station font-bold">
                  {{ item.pointName }}
                </td>

                <!-- 核心温度 -->
                <td class="col-num font-mono font-bold">
                  <span v-if="item.level1 === '一次网'" class="text-warm">{{ formatVal(item.f3, '℃') }}</span>
                  <span v-else-if="item.WENDU" :class="Number(item.WENDU) > 35 ? 'text-warm' : ''">{{ formatVal(item.WENDU, '℃', 1) }}</span>
                  <span v-else class="text-muted">—</span>
                </td>

                <!-- 核心压力 -->
                <td class="col-num font-mono">
                  <span v-if="item.level1 === '一次网'">{{ formatVal(item.f1, 'MPa', 3) }}</span>
                  <span v-else-if="item.YALI">{{ formatVal(item.YALI, 'MPa', 3) }}</span>
                  <span v-else class="text-muted">—</span>
                </td>

                <!-- 瞬时流量 -->
                <td class="col-num font-mono font-bold">
                  <span v-if="item.level1 === '一次网'">{{ formatVal(item.f2, 'm³/h', 1) }}</span>
                  <span v-else-if="item.level1 === '电厂'">{{ formatVal(item.LIULIANG, 't/h', 1) }}</span>
                  <span v-else-if="item.LIULIANG">{{ formatVal(item.LIULIANG, 'm³/h', 1) }}</span>
                  <span v-else class="text-muted">—</span>
                </td>

                <!-- 瞬时热量 -->
                <td class="col-num font-mono">
                  <span v-if="item.level1 === '一次网'">{{ formatVal(item.f222, 'GJ/h', 1) }}</span>
                  <span v-else-if="item.RELIANG">{{ formatVal(item.RELIANG, 'GJ', 1) }}</span>
                  <span v-else class="text-muted">—</span>
                </td>

                <!-- 工况说明 -->
                <td class="col-center font-mono text-sm">
                  <span v-if="item.level1 === '一次网'" class="text-cool">回温 {{ formatVal(item.f5, '℃') }}</span>
                  <span v-else-if="item.level1 === '首站' && item.FUHE" class="text-accent">负荷 {{ formatVal(item.FUHE, 'MW', 1) }}</span>
                  <span v-else-if="item.level1 === '首站' && item.PINLV" class="text-muted">频率 {{ formatVal(item.PINLV, 'Hz', 1) }}</span>
                  <span v-else class="text-muted">常规监控</span>
                </td>

                <td class="col-center font-mono text-muted text-sm">
                  {{ item.update_time || item.SHIJIAN || '—' }}
                </td>
              </tr>
              <tr v-if="displayList.length === 0">
                <td colspan="10" class="empty-cell">
                  {{ isRelayOnline ? '未检索到符合条件的采集点数据' : '数据链路未连接，暂无实时数据' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      </div>
      <!-- 中继转发与同步配置弹窗 (仅管理员) -->
      <div v-if="showRelayModal" class="modal-backdrop" @click.self="showRelayModal = false">
        <div class="relay-modal card elevated">
          <header class="modal-header">
            <h3>📡 服务器数据中继与本地同步配置</h3>
            <button class="btn-close" type="button" @click="showRelayModal = false">×</button>
          </header>

          <div class="modal-body">
            <div class="form-item form-switch-row">
              <div class="switch-label-col">
                <span class="label-title">服务器中继转发开关</span>
                <span class="label-desc">当办公电脑推流至服务器后，服务器是否自动中继并转发数据包（默认开启）</span>
              </div>
              <label class="switch">
                <input v-model="relayConfig.forward_enabled" type="checkbox" />
                <span class="slider round"></span>
              </label>
            </div>

            <div class="form-item">
              <label class="input-label">中继转发目标接收端 (Webhook / 内网穿透或开发环境地址)</label>
              <input
                v-model="relayConfig.forward_target_url"
                type="text"
                class="modal-input font-mono"
                placeholder="http://127.0.0.1:8000/api/v1/projects/daily_report_25_26/smart-heating/receive-relay"
              />
              <span class="input-hint">生产服务器接收到新数据时，异步 POST 推送到该地址。</span>
            </div>

            <div class="form-item">
              <label class="input-label">本地拉取远端服务器地址 (localhost 专用主动拉取源)</label>
              <input
                v-model="relayConfig.remote_server_url"
                type="text"
                class="modal-input font-mono"
                placeholder="https://platform.smartview.top"
              />
              <span class="input-hint">当开发环境位于防火墙或局域网内无法直接被推送时，本地前端可通过此中继接口拉取实时流。</span>
            </div>

            <div class="form-item">
              <label class="input-label">中继安全通信密钥 (Token)</label>
              <input
                v-model="relayConfig.relay_secret"
                type="text"
                class="modal-input font-mono"
                placeholder="phoenix_smart_heating_secret_2026"
              />
            </div>
          </div>

          <footer class="modal-footer">
            <button
              v-if="isLocalhost"
              class="btn secondary btn-sm"
              type="button"
              :disabled="isSyncingRemote"
              @click="handleSyncFromRemote"
            >
              {{ isSyncingRemote ? '同步中…' : '📥 立即测试从远端同步' }}
            </button>
            <div class="footer-right">
              <button class="btn secondary btn-sm" type="button" @click="showRelayModal = false">取消</button>
              <button
                class="btn primary btn-sm"
                type="button"
                :disabled="isSavingRelayConfig"
                @click="handleSaveRelayConfig"
              >
                {{ isSavingRelayConfig ? '保存中…' : '保存配置' }}
              </button>
            </div>
          </footer>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import SmartHeatingOverview from '../components/SmartHeatingOverview.vue'
import SmartHeatingPointCards from '../components/SmartHeatingPointCards.vue'
import { useAuthStore } from '../store/auth'
import {
  getSmartHeatingLatest,
  getSmartHeatingStatus,
  downloadSmartHeatingClientScript,
  getSmartHeatingRelayConfig,
  updateSmartHeatingRelayConfig,
  syncSmartHeatingFromRemote,
} from '../services/api'
import {
  LEVEL1_ORDER,
  LEVEL2_BY_LEVEL1,
  TAXONOMY_LIST,
  TAXONOMY_MAP,
  normalizePoint,
} from '../constants/smartHeatingTaxonomy'

const route = useRoute()
const activeTab = ref('source')
const currentTime = ref(Date.now())
let freshnessTimer = null
const projectKey = String(route.params.projectKey || 'daily_report_25_26')
const auth = useAuthStore()

// 判定当前用户是否具备 Global_admin 全局管理员权限
const isGlobalAdmin = computed(() => {
  const g = auth.user?.group
  const groups = auth.user?.groups || []
  return g === 'Global_admin' || groups.includes('Global_admin')
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '生产日报', to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: '智慧供热实时工况', to: null },
])

// 检测是否处于本地开发环境 (localhost / 127.0.0.1)
const isLocalhost = computed(() => {
  if (typeof window === 'undefined') return false
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1' || host === '::1'
})

// 中继与同步状态控制
const showRelayModal = ref(false)
const isSyncingRemote = ref(false)
const isSavingRelayConfig = ref(false)

const relayConfig = ref({
  forward_enabled: true,
  forward_target_url: 'http://127.0.0.1:8000/api/v1/projects/daily_report_25_26/smart-heating/receive-relay',
  remote_server_url: 'https://platform.smartview.top',
  relay_secret: 'phoenix_smart_heating_secret_2026',
})

// 选中的一级分类（默认首站，与 Excel 表顺序一致）
const currentLevel1 = ref('首站')
// 选中的二级分类（默认全部）
const selectedLevel2 = ref('all')
// 采集点关键词搜索
const searchKeyword = ref('')
// 排序方式（默认严格依据 Excel 次序）
const sortBy = ref('default')

const loading = ref(false)
const downloading = ref(false)
const autoRefresh = ref(true)
// 仅保存在当前页面内存中，两个标签独立设置，重新打开均恢复为 1 分钟。
const refreshIntervals = ref({ source: 60000, overview: 60000 })
const refreshIntervalMs = computed(() => refreshIntervals.value[activeTab.value])

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

// 严格依据后端真实状态判定是否在线
const isRelayOnline = computed(() => Boolean(relayStatus.value?.is_online))

const szDataList = computed(() => (isRelayOnline.value ? latestPayload.value?.sz_data || [] : []))
const dcDataList = computed(() => (isRelayOnline.value ? latestPayload.value?.dc_data || [] : []))
const ywDataList = computed(() => (isRelayOnline.value ? latestPayload.value?.yw_data || [] : []))

const formattedTimeAgo = computed(() => {
  if (isRelayOnline.value && relayStatus.value?.seconds_ago !== null) {
    const sec = relayStatus.value.seconds_ago
    return sec <= 5 ? '刚刚推送' : `${sec} 秒前推送`
  }
  return '等待客户端启动推流'
})

// 一级分类切换处理
function handleLevel1Change(level1) {
  currentLevel1.value = level1
  selectedLevel2.value = 'all'
}

// 归一化并排序首站采集点列表
const normalizedSzList = computed(() => {
  if (!isRelayOnline.value) return []
  return szDataList.value.map((item) => {
    const norm = normalizePoint(item.name)
    return {
      ...item,
      order: norm.order,
      level1: norm.level1,
      level2: norm.level2,
      pointName: norm.pointName,
    }
  }).sort((a, b) => a.order - b.order)
})

// 归一化并排序电厂采集点列表（严格依据 Excel 规范，过滤未收录项）
const normalizedDcList = computed(() => {
  if (!isRelayOnline.value) return []
  return dcDataList.value.map((item) => {
    const norm = normalizePoint(item.name)
    return {
      ...item,
      order: norm.order,
      level1: norm.level1,
      level2: norm.level2,
      pointName: norm.pointName,
    }
  })
  .filter((item) => item.order <= 344 && item.level1 === '电厂')
  .sort((a, b) => a.order - b.order)
})

// 归一化并排序一次网换热站采集点列表
const normalizedYwList = computed(() => {
  if (!isRelayOnline.value) return []
  return ywDataList.value.map((item) => {
    const norm = normalizePoint(item.name)
    return {
      ...item,
      order: norm.order,
      level1: norm.level1,
      level2: norm.level2,
      pointName: norm.pointName,
    }
  }).sort((a, b) => a.order - b.order)
})

// 全网 344 个标准采集点合并集合
const allNormalizedPoints = computed(() => {
  if (!isRelayOnline.value) return []
  return [...normalizedSzList.value, ...normalizedDcList.value, ...normalizedYwList.value]
    .sort((a, b) => a.order - b.order)
})

// 统计各一级分类下的采集点总数
const countByLevel1 = computed(() => {
  return {
    首站: normalizedSzList.value.length,
    电厂: normalizedDcList.value.length,
    一次网: normalizedYwList.value.length,
  }
})

const totalTaxonomyCount = computed(() => {
  return allNormalizedPoints.value.length
})

const totalOnlinePointCount = computed(() => {
  return allNormalizedPoints.value.length
})

// 当前一级分类下的二级分类下拉选项
const currentLevel2Options = computed(() => {
  const result = []
  if (currentLevel1.value === 'all') {
    // 聚合全部 15 个二级分类
    LEVEL1_ORDER.forEach((l1) => {
      const l2List = LEVEL2_BY_LEVEL1[l1] || []
      l2List.forEach((l2) => {
        const count = allNormalizedPoints.value.filter((p) => p.level2 === l2).length
        result.push({ name: l2, count })
      })
    })
  } else {
    const l2List = LEVEL2_BY_LEVEL1[currentLevel1.value] || []
    const sourceList =
      currentLevel1.value === '首站'
        ? normalizedSzList.value
        : currentLevel1.value === '电厂'
        ? normalizedDcList.value
        : normalizedYwList.value

    l2List.forEach((l2) => {
      const count = sourceList.filter((p) => p.level2 === l2).length
      result.push({ name: l2, count })
    })
  }
  return result
})

// 最终呈现的数据列表（经一级分类、二级分类、搜索关键字及排序规则过滤）
const displayList = computed(() => {
  if (!isRelayOnline.value) return []

  let list = []
  if (currentLevel1.value === '首站') {
    list = [...normalizedSzList.value]
  } else if (currentLevel1.value === '电厂') {
    list = [...normalizedDcList.value]
  } else if (currentLevel1.value === '一次网') {
    list = [...normalizedYwList.value]
  } else {
    list = [...allNormalizedPoints.value]
  }

  // 1. 二级分类过滤
  if (selectedLevel2.value !== 'all') {
    list = list.filter((item) => item.level2 === selectedLevel2.value)
  }

  // 2. 采集点搜索过滤
  const kw = searchKeyword.value.trim().toLowerCase()
  if (kw) {
    list = list.filter((item) => {
      const pName = String(item.pointName || '').toLowerCase()
      const l2 = String(item.level2 || '').toLowerCase()
      return pName.includes(kw) || l2.includes(kw)
    })
  }

  // 3. 排序规则应用
  if (sortBy.value === 'default') {
    list.sort((a, b) => (a.order || 9999) - (b.order || 9999))
  } else if (sortBy.value === 'temp_desc') {
    list.sort((a, b) => {
      const vB = Number(b.f3 !== undefined ? b.f3 : b.WENDU) || 0
      const vA = Number(a.f3 !== undefined ? a.f3 : a.WENDU) || 0
      return vB - vA
    })
  } else if (sortBy.value === 'temp_asc') {
    list.sort((a, b) => {
      const vB = Number(b.f3 !== undefined ? b.f3 : b.WENDU) || 0
      const vA = Number(a.f3 !== undefined ? a.f3 : a.WENDU) || 0
      return vA - vB
    })
  } else if (sortBy.value === 'flow_desc') {
    list.sort((a, b) => {
      const vB = Number(b.f2 !== undefined ? b.f2 : b.LIULIANG) || 0
      const vA = Number(a.f2 !== undefined ? a.f2 : a.LIULIANG) || 0
      return vB - vA
    })
  } else if (sortBy.value === 'diff_desc' && currentLevel1.value === '一次网') {
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
  if (name.includes('炉')) return '水炉'
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
  if (!isGlobalAdmin.value) {
    alert('下载同步客户端仅限 Global_admin 角色使用')
    return
  }
  downloading.value = true
  try {
    await downloadSmartHeatingClientScript(projectKey)
  } catch (err) {
    alert(err?.message || '下载同步客户端失败，请联系管理员确认权限')
  } finally {
    downloading.value = false
  }
}

async function fetchRelayConfig() {
  try {
    const res = await getSmartHeatingRelayConfig(projectKey)
    const cfg = res?.data || res?.config
    if (cfg) {
      relayConfig.value = {
        ...relayConfig.value,
        ...cfg,
      }
    }
  } catch (err) {
    // 忽略未授权或普通错误
  }
}

async function handleSaveRelayConfig() {
  isSavingRelayConfig.value = true
  try {
    await updateSmartHeatingRelayConfig(projectKey, {
      forward_enabled: relayConfig.value.forward_enabled,
      forward_target_url: relayConfig.value.forward_target_url,
      remote_server_url: relayConfig.value.remote_server_url,
      relay_secret: relayConfig.value.relay_secret,
    })
    showRelayModal.value = false
    alert('中继转发配置已保存生效')
  } catch (err) {
    alert(err?.message || '保存中继配置失败')
  } finally {
    isSavingRelayConfig.value = false
  }
}

async function handleSyncFromRemote() {
  isSyncingRemote.value = true
  try {
    const res = await syncSmartHeatingFromRemote(projectKey, {
      remote_url: relayConfig.value.remote_server_url,
      token: relayConfig.value.relay_secret,
    })
    if (res?.ok) {
      await fetchData()
      alert('已成功从线上服务器中继拉取最新工况数据！')
    } else {
      alert(res?.message || '从线上服务器拉取失败')
    }
  } catch (err) {
    alert(err?.message || '同步失败，请检查网络连接与安全Token')
  } finally {
    isSyncingRemote.value = false
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
    relayStatus.value = { is_online: false, seconds_ago: null, last_received_at: null }
    console.error('获取智慧供热实时数据失败:', err)
  } finally {
    loading.value = false
  }
}

// 切换标签或自动刷新开关时重建计时器，保证各标签按自己的周期刷新。
function restartAutoRefresh() {
  if (timer) clearInterval(timer)
  timer = null
  if (!autoRefresh.value) return
  timer = setInterval(() => {
    if (!loading.value) fetchData()
  }, refreshIntervalMs.value)
}

watch([activeTab, autoRefresh, refreshIntervalMs], restartAutoRefresh)

onMounted(async () => {
  freshnessTimer = setInterval(() => { currentTime.value = Date.now() }, 1000)
  restartAutoRefresh()
  await fetchData()
  await fetchRelayConfig()
})

onUnmounted(() => {
  if (freshnessTimer) clearInterval(freshnessTimer)
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.page-tabs { display: inline-flex; gap: 6px; padding: 5px; margin: 12px 0 20px; background: #e2e8f0; border-radius: 12px; }
.page-tabs button { min-height: 44px; padding: 10px 28px; background: transparent; border: 0; border-radius: 9px; color: #64748b; font-size: 15px; cursor: pointer; }
.page-tabs button[aria-selected="true"] { color: #0369a1; background: #fff; box-shadow: 0 2px 6px #0f172a0a; font-weight: 600; }
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
.smart-main.overview-main { max-width: 1840px; }
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

.offline-callout .callout-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.offline-callout .btn-callout-sync {
  background: #0284c7;
  border-color: #0284c7;
  color: #fff;
  white-space: nowrap;
}

.offline-callout .btn-callout-sync:hover {
  background: #0369a1;
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
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.btn-sync-remote {
  background: #0284c7;
  color: #ffffff;
  border: 1px solid #38bdf8;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.btn-sync-remote:hover {
  background: #0369a1;
}

.btn-relay-cfg {
  background: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.2);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.btn-relay-cfg:hover {
  background: rgba(255, 255, 255, 0.18);
  color: #ffffff;
}

.btn-relay-cfg.relay-active {
  border-color: rgba(56, 189, 248, 0.5);
  background: rgba(14, 165, 233, 0.15);
  color: #38bdf8;
}

.relay-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #64748b;
  display: inline-block;
}

.relay-dot.on {
  background: #38bdf8;
  box-shadow: 0 0 6px #38bdf8;
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

.refresh-interval-control { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; color: #cbd5e1; font-size: 13px; }
.refresh-interval-control select { min-height: 40px; padding: 8px 10px; border: 1px solid #64748b; border-radius: 8px; background: #1e293b; color: #f8fafc; font-size: 16px; cursor: pointer; }
.refresh-interval-control select:focus-visible { outline: 3px solid #38bdf8; outline-offset: 2px; }

/* 核心指标条 */
.metric-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
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

/* 分类与筛选工具栏 */
.nav-and-filter-card {
  padding: 12px 18px;
  border-radius: 10px;
  background: #ffffff;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.category-tabs-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-label-prefix {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
  white-space: nowrap;
}

.tabs-container {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tab-btn {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  padding: 7px 14px;
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
  border-color: #0284c7;
  color: #ffffff;
  box-shadow: 0 2px 4px rgba(2, 132, 199, 0.2);
}

.filter-controls-wrapper {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.selector-group, .search-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  white-space: nowrap;
}

.select-box {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-size: 12px;
  background: #fff;
  color: #1e293b;
  outline: none;
  min-width: 140px;
}

.select-box:focus {
  border-color: #0284c7;
}

.input-search {
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-size: 12px;
  width: 220px;
  outline: none;
}

.input-search:focus {
  border-color: #0284c7;
}

/* 分类徽章样式 */
.badge-level1 {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 4px;
  white-space: nowrap;
  letter-spacing: 0.02em;
}

.badge-level1.badge-sz {
  background: #ede9fe;
  color: #6d28d9;
}

.badge-level1.badge-dc {
  background: #ffedd5;
  color: #c2410c;
}

.badge-level1.badge-yw {
  background: #e0f2fe;
  color: #0369a1;
}

.badge-level2 {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
  white-space: nowrap;
  border: 1px solid #e2e8f0;
}

.badge-level2.tag-beihai {
  background: #ecfdf5;
  color: #047857;
  border-color: #a7f3d0;
}

.badge-level2.tag-xianghai {
  background: #fff7ed;
  color: #c2410c;
  border-color: #fed7aa;
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
  min-width: 1080px;
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

/* 中继与同步弹窗 */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}

.relay-modal {
  display: flex;
  flex-direction: column;
  max-height: calc(100dvh - 40px);
  background: #ffffff;
  border-radius: 12px;
  width: 100%;
  max-width: 580px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.btn-close {
  background: none;
  border: none;
  font-size: 22px;
  color: #64748b;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}

.btn-close:hover {
  color: #0f172a;
}

.modal-body {
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-switch-row {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.switch-label-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.label-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.label-desc {
  font-size: 12px;
  color: #64748b;
}

.input-label {
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}

.modal-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  box-sizing: border-box;
  color: #0f172a;
  outline: none;
  transition: border-color 0.2s;
}

.modal-input:focus {
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.input-hint {
  font-size: 11px;
  color: #94a3b8;
}

/* Switch 开关组件 */
.switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e1;
  transition: .3s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .3s;
}

input:checked + .slider {
  background-color: #0284c7;
}

input:checked + .slider:before {
  transform: translateX(22px);
}

.slider.round {
  border-radius: 26px;
}

.slider.round:before {
  border-radius: 50%;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

/* 中屏先重排工具栏，手机使用测点卡片，避免整页横向滚动。 */
.modal-header, .modal-footer { flex-shrink: 0; }
.smart-main, .banner-title-row > div, .banner-actions, .filter-controls-wrapper { min-width: 0; }
.title-with-badge, .header-left { flex-wrap: wrap; }
.banner-subtitle, .header-tip { line-height: 1.7; }
.banner-actions { flex: 1 1 100%; justify-content: space-between; padding-top: 4px; }
.action-buttons .btn, .callout-actions .btn { min-height: 40px; }
.banner-icon, .status-indicator .dot, .relay-dot { flex-shrink: 0; }
.metric-item { min-width: 0; }
.metric-val-row { flex-wrap: wrap; }
.metric-value { overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.table-responsive { max-width: 100%; border: 1px solid #e2e8f0; border-radius: 10px; overscroll-behavior-x: contain; }
.data-table .col-num { white-space: nowrap; }
.page-tabs button:focus-visible, .tab-btn:focus-visible, .btn:focus-visible { outline: 3px solid #38bdf8; outline-offset: 3px; }
@media (max-width: 1100px) {
  .metric-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .filter-controls-wrapper { width: 100%; }
  .banner-actions { align-items: flex-start; gap: 12px; }
}
@media (max-width: 640px) {
  .smart-main { padding: 12px 12px 32px; }
  .page-tabs { display: flex; margin: 12px 0 16px; }
  .page-tabs button { flex: 1; padding: 10px 12px; }
  .banner-card { padding: 18px 14px; border-radius: 16px; }
  .banner-content { gap: 16px; margin-bottom: 12px; }
  .banner-title-row { gap: 10px; align-items: flex-start; width: 100%; }
  .banner-icon { width: 38px; height: 38px; font-size: 23px; border-radius: 10px; }
  .banner-title { font-size: 19px; line-height: 1.4; }
  .badge-role { font-size: 10px; }
  .title-with-badge { gap: 6px; }
  .banner-subtitle { font-size: 12px; margin-top: 8px; }
  .offline-note { display: block; margin: 4px 0 0; }
  .banner-actions { display: grid; width: 100%; gap: 14px; }
  .status-indicator { justify-self: start; flex-wrap: wrap; padding: 7px 10px; font-size: 12px; }
  .action-buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .action-buttons .btn { min-width: 0; min-height: 44px; padding: 9px 8px; font-size: 12px; justify-content: center; white-space: normal; line-height: 1.5; }
  .auto-refresh-toggle { min-height: 44px; font-size: 12px; justify-content: center; }
  .refresh-interval-control { justify-content: center; min-width: 0; font-size: 12px; }
  .refresh-interval-control select { min-height: 44px; min-width: 0; }
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; padding-top: 14px; }
  .metric-item { padding: 11px 10px; }
  .metric-item:last-child { grid-column: 1 / -1; }
  .metric-label { font-size: 11px; line-height: 1.5; }
  .metric-value { font-size: 21px; }
  .metric-hint { line-height: 1.5; }
  .offline-callout { padding: 16px; flex-wrap: wrap; gap: 10px; }
  .offline-callout .offline-icon { font-size: 24px; }
  .offline-callout .offline-body { flex-basis: calc(100% - 40px); min-width: 0; }
  .offline-callout .offline-title { line-height: 1.5; }
  .offline-callout .callout-actions { width: 100%; flex-wrap: wrap; }
  .callout-actions .btn { flex: 1 1 140px; white-space: normal; min-height: 44px; }
  .nav-and-filter-card { padding: 14px; gap: 14px; }
  .category-tabs-wrapper { width: 100%; gap: 8px; }
  .filter-label-prefix { display: none; }
  .tabs-container { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); width: 100%; gap: 5px; }
  .tab-btn { min-height: 44px; padding: 8px 3px; font-size: 12px; }
  .filter-controls-wrapper { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 10px; }
  .selector-group, .search-group { min-width: 0; display: flex; flex-direction: column; align-items: stretch; gap: 6px; }
  .search-group { grid-column: 1 / -1; grid-row: 1; }
  .select-box, .input-search { box-sizing: border-box; width: 100%; min-width: 0; min-height: 44px; font-size: 16px; padding: 10px; }
  .data-section { display: none; }
  .modal-backdrop { padding: 12px; }
  .relay-modal { width: 100%; max-height: calc(100dvh - 24px); min-width: 0; }
  .modal-header, .modal-body, .modal-footer { padding: 16px; }
  .modal-header h3 { font-size: 16px; line-height: 1.5; }
  .form-switch-row { gap: 12px; }
  .switch { flex-shrink: 0; }
  .modal-input { box-sizing: border-box; min-width: 0; font-size: 16px; }
  .modal-footer { flex-wrap: wrap; gap: 10px; }
  .modal-footer > .btn, .footer-right { width: 100%; }
  .footer-right .btn { flex: 1; min-height: 44px; }
}
</style>
