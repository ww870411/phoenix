<template>
  <div class="bigscreen-container" :class="[currentTheme, `mobile-tab-${activeMobileTab}`]" ref="containerRef">
    <!-- 顶部科技流光控制栏 -->
    <header class="bigscreen-header">
      <div class="header-left">
        <div class="header-badge" :class="{ 'live-mode': isLiveStreamMode }">
          <span class="pulse-dot" :class="{ live: isLiveStreamMode }"></span>
          <span class="badge-text"><span class="badge-desktop-prefix">全链追踪 · </span>实时调度中心</span>
        </div>
        <div class="header-time">{{ currentTimeStr }}</div>
      </div>

      <div class="header-title-box">
        <h1 class="header-title">
          <span class="title-desktop">大连洁净能源集团·2026年度老旧供热管网升级改造项目物流链智慧管理平台</span>
          <span class="title-mobile">
            <span class="title-mobile-line1">大连洁净能源集团 · 2026年度</span>
            <span class="title-mobile-line2">老旧管网改造项目物流链智慧管理平台</span>
          </span>
        </h1>
      </div>

      <!-- 右侧：单一整合控制中心按钮 + 展开式控制面板 -->
      <div class="header-right" ref="controlMenuRef">
        <div class="control-center-wrapper">
          <!-- 触发主按钮 -->
          <button 
            class="action-btn control-trigger-btn"
            :class="{ active: isControlMenuOpen, 'live-active': isLiveStreamMode }"
            @click.stop="toggleControlMenu"
            title="点击打开/收起大屏控制中心"
          >
            <span class="btn-icon">⚙️</span>
            <span class="btn-text">调度控制中心</span>
            <span class="control-caret">{{ isControlMenuOpen ? '▲' : '▼' }}</span>
            <span v-if="isLiveStreamMode" class="mini-live-tag">实况中</span>
          </button>

          <!-- 浮层下拉控制面板 -->
          <transition name="control-dropdown">
            <div v-if="isControlMenuOpen" class="control-menu-popover" @click.stop>
              <div class="popover-header">
                <span class="popover-title">🎮 调度与大屏控制台</span>
                <button class="popover-close-btn" @click="isControlMenuOpen = false" title="关闭">✕</button>
              </div>

              <div class="popover-group">
                <div class="group-title">数据与视图模式</div>
                <div class="group-buttons-grid">
                  <!-- 接入真实数据流 -->
                  <button 
                    class="action-btn live-stream-btn" 
                    :class="{ active: isLiveStreamMode }" 
                    @click="toggleLiveStreamMode"
                    :title="isLiveStreamMode ? '已接入真实数据流（只读安全感知），点击断开' : '点击接入真实数据库实时数据流，展示真实数据状态与实时发运累计'"
                  >
                    <span class="btn-icon">{{ isLiveStreamMode ? '🟢' : '📡' }}</span>
                    <span>{{ isLiveStreamMode ? '断开实况' : '接入实况' }}</span>
                  </button>

                  <!-- 浅色/深色模式切换 -->
                  <button 
                    class="action-btn theme-toggle-btn" 
                    @click="toggleTheme"
                    :title="isDark ? '切换至明亮浅色模式' : '切换至科技深色模式'"
                  >
                    <span class="btn-icon">{{ isDark ? '☀️' : '🌙' }}</span>
                    <span>{{ isDark ? '浅色' : '深色' }}</span>
                  </button>

                  <!-- 强制刷新 -->
                  <button class="action-btn icon-btn" @click="loadRealData(true)" title="即刻强制刷新数据库全量数据">
                    <span class="btn-icon">🔄</span>
                    <span>刷新数据</span>
                  </button>

                  <!-- 全屏展示 -->
                  <button class="action-btn icon-btn" @click="toggleFullscreen" title="全屏展示">
                    <span class="btn-icon">{{ isFullscreen ? '🗗' : '⛶' }}</span>
                    <span>{{ isFullscreen ? '退出全屏' : '全屏展示' }}</span>
                  </button>
                </div>
              </div>

              <!-- ⚙️ 核心：大屏运行参数与节律配置 (实时生效并持久化保存在 tube_config.json) -->
              <div class="popover-group settings-group">
                <div class="group-title-with-action">
                  <span class="group-title">⚙️ 大屏运行节律与参数配置</span>
                  <span v-if="configSaveStatus" class="save-status-badge" :class="configSaveStatus.type">
                    {{ configSaveStatus.msg }}
                  </span>
                </div>

                <div class="settings-form-grid">
                  <!-- 1. 动效高亮展示时长 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">⏱️ 动效高亮展示</span>
                      <span class="setting-val-tag">{{ bsConfig.animation_active_duration_sec }} 秒</span>
                    </div>
                    <input 
                      type="range" 
                      min="1" 
                      max="30" 
                      step="1" 
                      v-model.number="bsConfig.animation_active_duration_sec" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="发货飞线与标段光晕高亮展示时长"
                    />
                    <div class="setting-hint">发货飞线与标段光晕点亮时长</div>
                  </div>

                  <!-- 2. 动效静息间隔时长 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">⏸️ 动效静息间隔</span>
                      <span class="setting-val-tag">{{ bsConfig.animation_rest_duration_sec }} 秒</span>
                    </div>
                    <input 
                      type="range" 
                      min="0" 
                      max="30" 
                      step="1" 
                      v-model.number="bsConfig.animation_rest_duration_sec" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="飞线消退后全景静止沉淀时长"
                    />
                    <div class="setting-hint">飞线消退后全景静止沉淀时长</div>
                  </div>

                  <!-- 3. 常规后台刷新周期 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">🔄 常规刷新周期</span>
                      <span class="setting-val-tag">{{ bsConfig.auto_sync_interval_sec }} 秒</span>
                    </div>
                    <input 
                      type="range" 
                      min="5" 
                      max="120" 
                      step="5" 
                      v-model.number="bsConfig.auto_sync_interval_sec" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="后台静默同步数据库指标的轮询周期"
                    />
                    <div class="setting-hint">后台静默同步全量数据库周期</div>
                  </div>

                  <!-- 4. 实况心跳频率 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">⚡ 实况心跳频率</span>
                      <span class="setting-val-tag">{{ bsConfig.live_stream_interval_sec }} 秒</span>
                    </div>
                    <input 
                      type="range" 
                      min="1" 
                      max="15" 
                      step="1" 
                      v-model.number="bsConfig.live_stream_interval_sec" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="接入实况模式下感知新增单据频率"
                    />
                    <div class="setting-hint">实况直连模式增量监听频率</div>
                  </div>

                  <!-- 5. 飞线粒子流速 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">🚀 飞线粒子流速</span>
                      <span class="setting-val-tag">{{ bsConfig.flyline_travel_sec }} 秒</span>
                    </div>
                    <input 
                      type="range" 
                      min="0.5" 
                      max="5.0" 
                      step="0.1" 
                      v-model.number="bsConfig.flyline_travel_sec" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="激光粒子由管厂跨越飞向标段耗时"
                    />
                    <div class="setting-hint">激光粒子跨越飞向标段耗时</div>
                  </div>

                  <!-- 6. 战报显示条数 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">📜 战报显示条数</span>
                      <span class="setting-val-tag">{{ bsConfig.feed_limit }} 条</span>
                    </div>
                    <input 
                      type="range" 
                      min="10" 
                      max="80" 
                      step="5" 
                      v-model.number="bsConfig.feed_limit" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="动态流水截取的最大最新单据记录数"
                    />
                    <div class="setting-hint">动态流水截取的最大最新记录数</div>
                  </div>

                  <!-- 7. 天气缓存刷新周期 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">🌤️ 天气缓存周期</span>
                      <span class="setting-val-tag">{{ bsConfig.weather_cache_duration_min || 15 }} 分钟</span>
                    </div>
                    <input 
                      type="range" 
                      min="1" 
                      max="60" 
                      step="1" 
                      v-model.number="bsConfig.weather_cache_duration_min" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="向高德地图拉取天气实况与预报的缓存更新周期"
                    />
                    <div class="setting-hint">向高德气象拉取实况/预报周期</div>
                  </div>

                  <!-- 8. 在途时效剔除下限 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">⏱️ 在途剔除下限</span>
                      <span class="setting-val-tag">{{ bsConfig.transit_duration_min_hours !== undefined ? bsConfig.transit_duration_min_hours : 1.0 }} 小时</span>
                    </div>
                    <input 
                      type="range" 
                      min="0" 
                      max="10" 
                      step="0.5" 
                      v-model.number="bsConfig.transit_duration_min_hours" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="剔除在途低于此阈值的单据（过滤秒点与同城测试单）"
                    />
                    <div class="setting-hint">低于此时长剔除(防秒点测试)</div>
                  </div>

                  <!-- 9. 在途时效剔除上限 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">⏳ 在途剔除上限</span>
                      <span class="setting-val-tag">{{ bsConfig.transit_duration_max_hours !== undefined ? bsConfig.transit_duration_max_hours : 36.0 }} 小时</span>
                    </div>
                    <input 
                      type="range" 
                      min="12" 
                      max="168" 
                      step="1" 
                      v-model.number="bsConfig.transit_duration_max_hours" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="剔除在途高于此阈值的单据（过滤漏确认与离群极端值）"
                    />
                    <div class="setting-hint">高于此时长剔除(防极端滞留)</div>
                  </div>

                  <!-- 10. 周战报交替切换周期 -->
                  <div class="setting-item">
                    <div class="setting-label-row">
                      <span class="setting-name">📅 周战报轮播周期</span>
                      <span class="setting-val-tag">{{ bsConfig.weekly_rotation_interval_sec || 10 }} 秒</span>
                    </div>
                    <input 
                      type="range" 
                      min="3" 
                      max="60" 
                      step="1" 
                      v-model.number="bsConfig.weekly_rotation_interval_sec" 
                      @input="applyConfigLocally"
                      class="setting-slider"
                      title="本周保温管施工战报与管件施工战报自动交替轮播的停留周期"
                    />
                    <div class="setting-hint">保温管与管件双战报轮播周期</div>
                  </div>
                </div>

                <!-- 保存与重置操作按钮 (仅限 Global_admin 可点击) -->
                <div class="settings-actions-bar">
                  <button 
                    class="action-btn save-config-btn" 
                    :disabled="isSavingConfig || !isGlobalAdmin" 
                    @click="handleSaveConfigToBackend"
                    :title="isGlobalAdmin ? '将当前调节后的设定持久化写入后端 tube_config.json' : '权限受限：仅限 Global_admin 超级管理员可以保存大屏设定'"
                    :class="{ 'disabled-permission': !isGlobalAdmin }"
                  >
                    <span class="btn-icon">💾</span>
                    <span>{{ isSavingConfig ? '正在保存...' : (isGlobalAdmin ? '保存设定' : '保存设定 (仅限管理员)') }}</span>
                  </button>
                  <button 
                    class="action-btn reset-config-btn" 
                    :disabled="!isGlobalAdmin"
                    @click="handleResetConfigToDefault"
                    :title="isGlobalAdmin ? '恢复出厂默认参数设置' : '权限受限：仅限 Global_admin 超级管理员可以重置大屏设定'"
                    :class="{ 'disabled-permission': !isGlobalAdmin }"
                  >
                    <span class="btn-icon">🔄</span>
                    <span>重置默认</span>
                  </button>
                </div>
              </div>

              <div class="popover-group">
                <div class="group-title">沙盒演示与模拟</div>
                <div class="group-buttons-grid">
                  <!-- 自动演示 -->
                  <button 
                    class="action-btn demo-btn" 
                    :class="{ active: autoDemoRunning }" 
                    @click="toggleAutoDemo"
                    title="开启/暂停沙盒自动演示流"
                  >
                    <span class="btn-icon">{{ autoDemoRunning ? '⏸️' : '▶️' }}</span>
                    <span>{{ autoDemoRunning ? '演示中' : '自动演示' }}</span>
                  </button>

                  <!-- 模拟管材 -->
                  <button class="action-btn sim-btn" @click="triggerSimulateDelivery('pipe')">
                    <span class="btn-icon">🏭</span>
                    <span>模拟管材</span>
                  </button>

                  <!-- 模拟管件 -->
                  <button class="action-btn sim-btn fitting" @click="triggerSimulateDelivery('fitting')">
                    <span class="btn-icon">📦</span>
                    <span>模拟管件</span>
                  </button>
                </div>
              </div>

              <div class="popover-footer">
                <button class="action-btn back-btn" @click="goBackToStandardDashboard" title="返回标准看板">
                  <span class="btn-icon">↩</span>
                  <span>返回标准看板</span>
                </button>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </header>

    <!-- 移动端专属导航选项卡 (<= 900px 自动显现，一触即切) -->
    <nav class="mobile-nav-tabs" role="tablist">
      <button 
        class="mobile-tab-btn" 
        :class="{ active: activeMobileTab === 'kpi' }"
        @click="setMobileTab('kpi')"
        type="button"
        role="tab"
      >
        <span class="tab-icon">📊</span>
        <span class="tab-label">指标大盘</span>
      </button>
      <button 
        class="mobile-tab-btn" 
        :class="{ active: activeMobileTab === 'topology' }"
        @click="setMobileTab('topology')"
        type="button"
        role="tab"
      >
        <span class="tab-icon">
          <svg class="tab-svg-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
        </span>
        <span class="tab-label">供需拓扑</span>
      </button>
      <button 
        class="mobile-tab-btn" 
        :class="{ active: activeMobileTab === 'feed' }"
        @click="setMobileTab('feed')"
        type="button"
        role="tab"
      >
        <span class="tab-icon">📢</span>
        <span class="tab-label">动态战报</span>
        <span v-if="liveFeedList.length" class="tab-badge">{{ Math.min(liveFeedList.length, 99) }}</span>
      </button>
    </nav>

    <!-- 主展示区：三栏网格体系 -->
    <main class="bigscreen-content" :class="['mobile-tab-' + activeMobileTab]">
      <!-- 左侧栏：全局指标体系与管材/管件双轨大盘 (100% 真实数据库计算) -->
      <section class="screen-col left-col" :class="{ 'mobile-active-col': activeMobileTab === 'kpi' }">
        <!-- 核心气象：今日天气与施工环境 (高德实时数据) -->
        <div class="panel-box weather-kpi-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon title-icon-weather">
                <svg class="title-svg-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="7" r="3.5" fill="#fbbf24" fill-opacity="0.35" stroke="#fbbf24" stroke-width="2"/>
                  <line x1="12" y1="1" x2="12" y2="2.5" stroke="#fbbf24" stroke-width="2"/>
                  <line x1="16.5" y1="2.5" x2="15.5" y2="3.8" stroke="#fbbf24" stroke-width="2"/>
                  <line x1="18" y1="7" x2="19.5" y2="7" stroke="#fbbf24" stroke-width="2"/>
                  <path d="M18.5 19H7a4.5 4.5 0 0 1-.8-8.9 5.5 5.5 0 0 1 10.6-1.5A3.5 3.5 0 0 1 18.5 19z" fill="#38bdf8" fill-opacity="0.35" stroke="#38bdf8" stroke-width="2"/>
                </svg>
              </span>
              <span>今日天气与施工条件</span>
            </div>
            <span class="panel-tag" :class="liveWeatherData.status_level === 'danger' ? 'danger' : (liveWeatherData.status_level === 'warning' ? 'gold' : 'green')">
              {{ liveWeatherData.status_tag || '适宜施工' }}
            </span>
          </div>

          <div class="weather-panel-body">
            <!-- 施工现场位置与报告时间 -->
            <div class="weather-loc-bar">
              <span class="loc-pin">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle;">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                  <circle cx="12" cy="10" r="3"></circle>
                </svg>
              </span>
              <span class="loc-text">{{ liveWeatherData.city || '主城区施工现场' }}</span>
              <span class="loc-dot">·</span>
              <span class="loc-time">{{ liveWeatherData.is_live_source === false ? '仿真' : '实况' }}</span>
            </div>

            <!-- 横向核心气象数据行（原版经典横向 + 同框全天预报） -->
            <div class="weather-metrics-row">
              <div class="weather-temp-block">
                <span class="weather-emoji" :title="liveWeatherData.weather || '多云'">
                  <svg v-if="getWeatherCategory(liveWeatherData.weather) === 'sunny'" class="weather-svg-icon sunny" viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#fbbf24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="5" fill="#fbbf24" fill-opacity="0.25"></circle>
                    <line x1="12" y1="1" x2="12" y2="3"></line>
                    <line x1="12" y1="21" x2="12" y2="23"></line>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                    <line x1="1" y1="12" x2="3" y2="12"></line>
                    <line x1="21" y1="12" x2="23" y2="12"></line>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                  </svg>
                  <svg v-else-if="getWeatherCategory(liveWeatherData.weather) === 'cloudy'" class="weather-svg-icon cloudy" viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" fill="#38bdf8" fill-opacity="0.25"></path>
                  </svg>
                  <svg v-else-if="getWeatherCategory(liveWeatherData.weather) === 'overcast'" class="weather-svg-icon overcast" viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z" fill="#94a3b8" fill-opacity="0.3"></path>
                  </svg>
                  <svg v-else-if="getWeatherCategory(liveWeatherData.weather) === 'rain'" class="weather-svg-icon rain" viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M16 13a4 4 0 0 0-7.8-1.2A5 5 0 0 0 4 16h14a3 3 0 0 0 0-6h-.8z" fill="#00f2fe" fill-opacity="0.25"></path>
                    <line x1="8" y1="18" x2="7" y2="21" stroke="#00f2fe" stroke-width="2"></line>
                    <line x1="12" y1="18" x2="11" y2="21" stroke="#00f2fe" stroke-width="2"></line>
                    <line x1="16" y1="18" x2="15" y2="21" stroke="#00f2fe" stroke-width="2"></line>
                  </svg>
                  <svg v-else-if="getWeatherCategory(liveWeatherData.weather) === 'thunder'" class="weather-svg-icon thunder" viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#a855f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M19 16.9A5 5 0 0 0 18 7h-1.26a8 8 0 1 0-11.62 9" fill="#a855f7" fill-opacity="0.25"></path>
                    <polyline points="13 11 9 17 15 17 11 23" stroke="#fbbf24" stroke-width="2" fill="#fbbf24"></polyline>
                  </svg>
                  <svg v-else-if="getWeatherCategory(liveWeatherData.weather) === 'snow'" class="weather-svg-icon snow" viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#e0f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="2" x2="12" y2="22"></line>
                    <line x1="2" y1="12" x2="22" y2="12"></line>
                    <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
                    <line x1="19.07" y1="4.93" x2="4.93" y2="19.07"></line>
                  </svg>
                  <svg v-else class="weather-svg-icon default" viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="4" fill="#fbbf24" fill-opacity="0.3"></circle>
                    <path d="M12 2v2"></path><path d="M12 20v2"></path>
                    <path d="M4.93 4.93l1.41 1.41"></path><path d="M17.66 17.66l1.41 1.41"></path>
                    <path d="M2 12h2"></path><path d="M20 12h2"></path>
                  </svg>
                </span>
                <div class="temp-detail">
                  <span class="weather-name">{{ liveWeatherData.weather || '多云' }}</span>
                  <span class="temp-degree">{{ liveWeatherData.temperature }}<small>°C</small></span>
                </div>
              </div>

              <div class="weather-params-block">
                <div class="param-item">
                  <span class="param-k">湿度</span>
                  <span class="param-v">{{ liveWeatherData.humidity }}%</span>
                </div>
                <div class="param-item">
                  <span class="param-k">风力</span>
                  <span class="param-v">{{ liveWeatherData.wind_direction }}风 {{ liveWeatherData.wind_power }}级</span>
                </div>
              </div>

              <!-- 同一框体下方的全天预报条 -->
              <div class="weather-forecast-subrow">
                <span class="fc-icon">
                  <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline-block; vertical-align:middle;">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                    <line x1="16" y1="2" x2="16" y2="6"></line>
                    <line x1="8" y1="2" x2="8" y2="6"></line>
                    <line x1="3" y1="10" x2="21" y2="10"></line>
                  </svg>
                </span>
                <span class="fc-range">全天 {{ liveWeatherData.forecast?.temp_range || '24°C ~ 29°C' }}</span>
                <span class="fc-dot">·</span>
                <span class="fc-dn">白天 {{ liveWeatherData.forecast?.day_weather || '阴' }} / 夜间 {{ liveWeatherData.forecast?.night_weather || '阴' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 核心指标1：管材全网发运与在途 (真实数据库聚合) -->
        <div class="panel-box pipe-kpi-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon title-icon-pipe">
                <svg class="title-svg-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 7h18M3 17h18" stroke="#38bdf8" stroke-width="2"/>
                  <circle cx="7" cy="12" r="2.8" fill="rgba(56, 189, 248, 0.3)" stroke="#38bdf8" stroke-width="1.8"/>
                  <circle cx="17" cy="12" r="2.8" fill="rgba(56, 189, 248, 0.3)" stroke="#38bdf8" stroke-width="1.8"/>
                  <line x1="9.8" y1="12" x2="14.2" y2="12" stroke="#00f2fe" stroke-width="2" stroke-dasharray="2 2"/>
                </svg>
              </span>
              <span>保温管全网发运情报</span>
            </div>
            <span class="panel-tag cyan">保温管总线</span>
          </div>

          <div class="kpi-metric-grid">
            <!-- 1. 全网计划采购量 -->
            <div class="metric-item">
              <div class="metric-label-box">
                <span class="metric-label">全网计划采购量</span>
              </div>
              <div class="metric-val">
                <span class="num hero-num">{{ formatNumber(kpiData.pipeDesignKm) }}</span>
                <span class="unit">km</span>
              </div>
            </div>

            <!-- 2. 累计发货总量 + 在途状态胶囊 -->
            <div class="metric-item highlight-cyan">
              <div class="metric-label-box">
                <span class="metric-label">累计发货总量</span>
                <span class="metric-capsule cyan-capsule" title="当前运输在途量">
                  在途 {{ formatNumber(kpiData.pipeTransitKm) }}
                </span>
              </div>
              <div class="metric-val">
                <span class="num hero-num count-num">{{ formatNumber(kpiData.pipeShippedKm) }}</span>
                <span class="unit">km</span>
                <transition name="bubble-fade">
                  <span v-if="bubbles.pipeShipped" class="delta-bubble">+{{ bubbles.pipeShipped }}m</span>
                </transition>
              </div>
            </div>

            <!-- 3. 累计施工量 -->
            <div class="metric-item highlight-purple">
              <div class="metric-label-box">
                <span class="metric-label">累计施工量</span>
              </div>
              <div class="metric-val">
                <span class="num hero-num count-num purple-text">{{ formatNumber(kpiData.pipeInstalledKm) }}</span>
                <span class="unit">km</span>
              </div>
            </div>

            <!-- 4. 现场库存总量 + 缺口状态胶囊 -->
            <div class="metric-item highlight-green">
              <div class="metric-label-box">
                <span class="metric-label">现场库存总量</span>
                <span 
                  class="metric-capsule" 
                  :class="kpiData.pipeThreeDayGapKm > 0 ? 'red-capsule alert-pulse' : 'gray-capsule'" 
                  :title="kpiData.pipeThreeDayGapKm > 0 ? '未来三日存在净缺口' : '未来三日要料满足，无净缺口'"
                >
                  缺口 {{ formatNumber(kpiData.pipeThreeDayGapKm) }}
                </span>
              </div>
              <div class="metric-val">
                <span class="num hero-num green-text">{{ formatNumber(kpiData.pipeStockKm) }}</span>
                <span class="unit">km</span>
              </div>
            </div>
          </div>

          <!-- 管材保供进度充能条 -->
          <div class="energy-progress-box">
            <div class="energy-progress-info">
              <span>全网保温管供应进度</span>
              <strong class="cyan-text">{{ pipeCoveragePercent }}%</strong>
            </div>
            <div class="energy-bar-track">
              <div 
                class="energy-bar-fill cyan-glow" 
                :style="{ width: pipeCoveragePercent + '%' }"
              >
                <div class="energy-bar-light"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 核心指标2：管件全网发运情报 -->
        <div class="panel-box fitting-kpi-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon title-icon-fitting">
                <svg class="title-svg-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="4.5" fill="rgba(251, 191, 36, 0.25)" stroke="#fbbf24" stroke-width="2"/>
                  <path d="M12 2v4M12 18v4M2 12h4M18 12h4" stroke="#fbbf24" stroke-width="2"/>
                  <circle cx="12" cy="12" r="1.5" fill="#fbbf24"/>
                </svg>
              </span>
              <span>管件全网发运情报</span>
            </div>
            <span class="panel-tag gold">10个大类</span>
          </div>

          <div class="kpi-metric-grid">
            <div class="metric-item">
              <div class="metric-label-box">
                <span class="metric-label">全网计划采购量</span>
              </div>
              <div class="metric-val">
                <span class="num hero-num">{{ kpiData.fittingTotalPcs }}</span>
                <span class="unit">件/套</span>
              </div>
            </div>
            <div class="metric-item highlight-gold">
              <div class="metric-label-box">
                <span class="metric-label">累计发货总量</span>
                <span class="metric-capsule amber-capsule" title="当前在途直运件数">
                  在途 {{ kpiData.fittingTransitPcs }}
                </span>
              </div>
              <div class="metric-val">
                <span class="num hero-num count-num">{{ kpiData.fittingShippedPcs }}</span>
                <span class="unit">件</span>
                <transition name="bubble-fade">
                  <span v-if="bubbles.fittingShipped" class="delta-bubble gold">+{{ bubbles.fittingShipped }}件</span>
                </transition>
              </div>
            </div>
            <div class="metric-item highlight-purple">
              <div class="metric-label-box">
                <span class="metric-label">累计安装量</span>
              </div>
              <div class="metric-val">
                <span class="num hero-num count-num purple-text">{{ kpiData.fittingInstalledPcs || 0 }}</span>
                <span class="unit">件</span>
              </div>
            </div>
            <div class="metric-item highlight-green">
              <div class="metric-label-box">
                <span class="metric-label">现场库存量</span>
              </div>
              <div class="metric-val">
                <span class="num hero-num green-text">{{ kpiData.fittingStockPcs ?? kpiData.fittingArrivedPcs }}</span>
                <span class="unit">件</span>
              </div>
            </div>
          </div>

          <!-- 管件供应进度条 -->
          <div class="energy-progress-box">
            <div class="energy-progress-info">
              <span>全网管件供应进度</span>
              <strong class="gold-text">{{ fittingCoveragePercent }}%</strong>
            </div>
            <div class="energy-bar-track">
              <div 
                class="energy-bar-fill gold-glow" 
                :style="{ width: fittingCoveragePercent + '%' }"
              >
                <div class="energy-bar-light"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 供应链安全保障与效率雷达 -->
        <div class="panel-box safety-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon title-icon-shield">
                <svg class="title-svg-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" fill="rgba(16, 185, 129, 0.25)" stroke="#10b981" stroke-width="2"/>
                  <path d="M9 12l2 2 4-4" stroke="#10b981" stroke-width="2.2"/>
                </svg>
              </span>
              <span>保供效能与履约保障</span>
            </div>
            <span class="panel-tag green">100% 履约受控</span>
          </div>
          <div class="safety-grid">
            <div class="safety-card">
              <div class="safety-icon">
                <svg class="safety-svg-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M2 20h20M4 20V9l5 3.5V9l5 3.5V4h6v16" stroke="#10b981" stroke-width="2" fill="rgba(16, 185, 129, 0.15)"/>
                </svg>
              </div>
              <div class="safety-info">
                <div class="safety-val">{{ supplyNodes.length }} 家</div>
                <div class="safety-desc">核心制造管厂</div>
              </div>
            </div>
            <div class="safety-card">
              <div class="safety-icon">
                <svg class="safety-svg-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="9" stroke="#10b981" stroke-width="2" fill="rgba(16, 185, 129, 0.15)"/>
                  <circle cx="12" cy="12" r="5" stroke="#10b981" stroke-width="1.8"/>
                  <circle cx="12" cy="12" r="2" fill="#10b981"/>
                </svg>
              </div>
              <div class="safety-info">
                <div class="safety-val">{{ sectionProgressList.length }} 个</div>
                <div class="safety-desc">施工标段现场</div>
              </div>
            </div>
            <div class="safety-card">
              <div class="safety-icon">
                <svg class="safety-svg-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" stroke="#10b981" stroke-width="2" fill="rgba(16, 185, 129, 0.15)"/>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96" stroke="#10b981" stroke-width="2"/>
                  <line x1="12" y1="22.08" x2="12" y2="12" stroke="#10b981" stroke-width="2"/>
                </svg>
              </div>
              <div class="safety-info">
                <div class="safety-val">{{ kpiData.warehouseConfirmRate !== undefined ? kpiData.warehouseConfirmRate + '%' : '100%' }}</div>
                <div class="safety-desc">库管确认率</div>
              </div>
            </div>
            <div class="safety-card">
              <div class="safety-icon">
                <svg class="safety-svg-icon" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="13" r="8" stroke="#10b981" stroke-width="2" fill="rgba(16, 185, 129, 0.15)"/>
                  <path d="M12 9v4l2.5 2.5" stroke="#10b981" stroke-width="2"/>
                  <path d="M10 2h4M12 2v3" stroke="#10b981" stroke-width="2"/>
                </svg>
              </div>
              <div class="safety-info">
                <div class="safety-val">{{ kpiData.avgTransitHours !== undefined ? kpiData.avgTransitHours + ' 小时' : '16.4 小时' }}</div>
                <div class="safety-desc">平均在途时长</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 中间栏：重构升级版 · 高工规整双系统拓扑中枢 (默认通透极简，发货在途/悬停显现) -->
      <section class="screen-col center-col" :class="{ 'mobile-active-col': activeMobileTab === 'topology' }">
        <div class="panel-box map-topology-master-panel">
          <!-- 拓扑头部导航与状态过滤 -->
          <div class="topology-header-bar">
            <div class="panel-title">
              <span class="title-icon">
                <svg class="title-svg-globe" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="2" y1="12" x2="22" y2="12"></line>
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                </svg>
              </span>
              <span>供需流向拓扑</span>
            </div>

            <!-- 图例说明 -->
            <div class="topology-legend">
              <span class="legend-item"><span class="dot-line cyan"></span>保温管在途</span>
              <span class="legend-item"><span class="dot-line gold"></span>管件在途</span>
              <span class="legend-item"><span class="dot-point active"></span>实况节点</span>
            </div>
          </div>

          <!-- 移动端专属手势滑动提示 (<= 900px 自动显现) -->
          <div class="mobile-topo-scroll-hint" v-if="activeMobileTab === 'topology'">
            <span>👆 支持 2D 自由手势滑动 · 查看全网 3 家管厂与 10 大施工标段流向拓扑 ➔</span>
          </div>

          <!-- 拓扑主舞台：左管厂 (230px) + 中流向通道 (50px) + 右双系统立柱 (1fr) -->
          <div class="topology-container" ref="topologyContainerRef" @scroll="recalculateFlylines">
            <!-- 动态贝塞尔飞线与激光粒子 SVG 视层 (默认不显示任何线条，仅在发货在途或悬停时显现) -->
            <svg class="topology-svg" ref="svgRef">
              <defs>
                <linearGradient id="grad-pipe-line" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#00f2fe" />
                  <stop offset="100%" stop-color="#38bdf8" />
                </linearGradient>
                <linearGradient id="grad-fitting-line" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#fbbf24" />
                  <stop offset="100%" stop-color="#f97316" />
                </linearGradient>
              </defs>

              <!-- 专供运输管道与流光组合 (已发货: 经典流动光带; 未发货: 细静止连线) -->
              <g class="flylines-layer">
                <g 
                  v-for="line in flylines" 
                  :key="line.id"
                  class="flyline-group"
                  :class="{
                    'is-shipped': isLineShipped(line),
                    'is-unshipped': !isLineShipped(line)
                  }"
                  v-show="isLineVisible(line)"
                >
                  <!-- 管道基础轨迹：已发货为标准基准线，未发货为细静止连线 -->
                  <path 
                    :d="line.d" 
                    class="flyline-base"
                    :class="[
                      getLineMaterialType(line),
                      isLineShipped(line) ? 'shipped' : 'unshipped'
                    ]"
                  />
                  <!-- 在途流动光带（仅实际已发货标段专享经典流光） -->
                  <path 
                    v-if="isLineShipped(line)"
                    :d="line.d" 
                    class="flyline-stream"
                    :class="getLineMaterialType(line)"
                  />
                </g>
              </g>

              <!-- 发货时触发的单点高亮激光能量包粒子 -->
              <g class="particles-layer">
                <circle 
                  v-for="p in activeParticles" 
                  :key="p.id"
                  r="5" 
                  :fill="p.type === 'pipe' ? '#00f2fe' : '#fbbf24'"
                  class="laser-particle"
                >
                  <animateMotion 
                    :path="p.d" 
                    :dur="p.duration + 's'" 
                    begin="0s"
                    repeatCount="1"
                    fill="freeze"
                  />
                </circle>
              </g>
            </svg>

            <!-- 拓扑节点排版架构：左管厂 (230px) + 中通道 (50px) + 右双系统立柱 (1fr) -->
            <div class="topology-layout-grid">
              <!-- 1. 左侧：供给制造基地 (Supply Hub) -->
              <div class="supply-hub-col">
                <div class="supply-cards-stack">
                  <div 
                    v-for="sup in supplyNodes" 
                    :key="sup.id" 
                    class="supply-node-card"
                    :class="{ 
                      active: activeNodeIds.has(sup.id),
                      hovered: hoveredSupplierId === sup.id,
                      'is-shipping-source': isAnimationRunning && activeEventCategory === 'dispatch' && activeSupplierId === sup.id,
                      [`mat-${activeMaterialType}`]: isAnimationRunning && activeEventCategory === 'dispatch' && activeSupplierId === sup.id,
                      dimmed: (hoveredSupplierId && hoveredSupplierId !== sup.id) || 
                              (hoveredSectionId && !isSupplierOfSection(sup.id, hoveredSectionId)) ||
                              (isAnimationRunning && activeEventCategory === 'dispatch' && activeSupplierId && activeSupplierId !== sup.id && !hoveredSupplierId && !hoveredSectionId)
                    }"
                    :id="'node-' + sup.id"
                    @mouseenter="handleNodeMouseEnter('sup', sup.id)"
                    @mouseleave="handleNodeMouseLeave('sup')"
                  >
                    <strong class="sup-title" :title="sup.name">{{ sup.name }}</strong>

                    <!-- 物理对齐连接端口 (右锚点) -->
                    <div class="node-port port-out" :id="'port-out-' + sup.id" title="发运输出端口">
                      <span class="port-dot"></span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 2. 中间：流向传输主通道 (Transit Corridor) -->
              <div class="transit-channel-col">
                <div class="channel-track">
                  <div class="channel-glow-line"></div>
                  <div class="channel-text">专线直达</div>
                </div>
              </div>

              <!-- 3. 右侧：10 大施工标段（按 高温水干线 与 低温水分支 两大规整立柱排布） -->
              <div class="demand-hub-col">
                <div class="demand-systems-split" @scroll="recalculateFlylines">
                  <!-- 第 1 标段立柱：5 标段 (H1 ~ H4 + L1) -->
                  <div class="system-sub-col high-system">
                    <div class="system-cards-list">
                      <div 
                        v-for="sec in col1Sections" 
                        :key="sec.id" 
                        class="demand-node-card"
                        :class="[
                          sec.system_type === 'high' ? 'high-system' : 'low-system',
                          { 
                            active: activeNodeIds.has('sec_' + sec.id),
                            highlighted: lastImpactedSectionId === sec.id || (hoveredSupplierId && isSuppliedBy(sec.id, hoveredSupplierId)),
                            'is-event-target': isAnimationRunning && activeSectionId === sec.id,
                            [`event-cat-${activeEventCategory}`]: isAnimationRunning && activeSectionId === sec.id,
                            [`event-mat-${activeMaterialType}`]: isAnimationRunning && activeSectionId === sec.id,
                            dimmed: (hoveredSupplierId && !isSuppliedBy(sec.id, hoveredSupplierId)) || 
                                    (hoveredSectionId && hoveredSectionId !== sec.id) ||
                                    (isAnimationRunning && activeSectionId && activeSectionId !== sec.id && !hoveredSectionId && !hoveredSupplierId),
                            completed: sec.pipePercent >= 100 && sec.fittingPercent >= 100
                          }
                        ]"
                        :id="'node-sec_' + sec.id"
                        @mouseenter="handleNodeMouseEnter('sec', sec.id)"
                        @mouseleave="handleNodeMouseLeave('sec')"
                      >
                        <!-- 物理对齐连接端口 (左锚点) -->
                        <div class="node-port port-in" :id="'port-in-sec_' + sec.id" title="标段签收入口">
                          <span class="port-dot"></span>
                        </div>

                        <div class="sec-card-header">
                          <div class="sec-badge-name">
                            <span class="sec-sys-badge" :class="sec.system_type">{{ sec.system_type === 'high' ? '🔥 高温' : '💧 低温' }}</span>
                            <strong class="sec-title" :title="sec.name">{{ sec.name }}</strong>
                          </div>
                          <span class="sec-status-chip" :class="{ running: sec.construction_status === '施工中' }">
                            <span class="chip-dot"></span>
                            <span>{{ sec.construction_status }}</span>
                          </span>
                        </div>

                        <!-- 保温管、施工量与管件三轨微进度 (支持在途差值高亮闪动) -->
                        <div class="sec-metrics-body">
                          <!-- 1. 保温管 -->
                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label pipe-tag">
                                <svg class="tag-mini-icon" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M21 21H3V3l18 18z"/>
                                  <path d="M8 17v2"/>
                                  <path d="M12 17v2"/>
                                  <path d="M16 17v2"/>
                                </svg>
                                <span>保温管</span>
                              </span>
                              <span class="line-val cyan-text">
                                {{ sec.arrivedKm !== undefined ? sec.arrivedKm : sec.shippedKm }}<span v-if="sec.transitKm > 0" class="transit-num-tag cyan-transit" title="在途运送量">(+{{ sec.transitKm }})</span> / {{ sec.designKm }} km
                              </span>
                              <span class="line-pct cyan-text">{{ sec.pipePercent }}%</span>
                            </div>
                            <div class="micro-bar-bg" :title="`到货: ${sec.arrivedKm !== undefined ? sec.arrivedKm : sec.shippedKm}km | 在途: ${sec.transitKm || 0}km | 设计: ${sec.designKm}km`">
                              <!-- 实体到货 (实色) -->
                              <div 
                                class="micro-bar-fill cyan" 
                                :style="{ width: Math.min(sec.arrivedPercent !== undefined ? sec.arrivedPercent : sec.pipePercent, 100) + '%' }"
                              ></div>
                              <!-- 发货与到货差值 (在途闪烁高亮) -->
                              <div 
                                v-if="sec.transitPercent > 0"
                                class="micro-bar-transit cyan-transit" 
                                :style="{ 
                                  left: Math.min(sec.arrivedPercent, 100) + '%', 
                                  width: Math.min(sec.transitPercent, 100 - sec.arrivedPercent) + '%' 
                                }"
                                :title="`直管在途运送: ${sec.transitKm} km`"
                              ></div>
                            </div>
                          </div>

                          <!-- 2. 施工量 -->
                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label construct-tag">
                                <svg class="tag-mini-icon" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M2 22h20"/>
                                  <path d="M13 2v20"/>
                                  <path d="M5 2h14l-7 7"/>
                                  <path d="M13 9h-3l-2 5h5"/>
                                  <circle cx="6" cy="14" r="1" fill="currentColor"/>
                                </svg>
                                <span>施工量</span>
                              </span>
                              <span class="line-val green-text">{{ sec.installedKm || '0.00' }} / {{ sec.designKm }} km</span>
                              <span class="line-pct green-text">{{ sec.installedPercent || 0 }}%</span>
                            </div>
                            <div class="micro-bar-bg" :title="`已安装施工: ${sec.installedKm || '0.00'} km`">
                              <div class="micro-bar-fill green" :style="{ width: Math.min(sec.installedPercent || 0, 100) + '%' }"></div>
                            </div>
                          </div>

                          <!-- 3. 管件 -->
                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label fitting-tag">
                                <svg class="tag-mini-icon" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M12 2l7 4.5v9L12 20l-7-4.5v-9L12 2z"/>
                                  <circle cx="12" cy="11" r="3"/>
                                </svg>
                                <span>管件</span>
                              </span>
                              <span class="line-val gold-text">
                                {{ sec.arrivedFittings !== undefined ? sec.arrivedFittings : sec.shippedFittings }}<span v-if="sec.transitFittings > 0" class="transit-num-tag gold-transit" title="在途运送量">(+{{ sec.transitFittings }})</span> / {{ sec.totalFittings }} 件
                              </span>
                              <span class="line-pct gold-text">{{ sec.fittingPercent }}%</span>
                            </div>
                            <div class="micro-bar-bg" :title="`到货: ${sec.arrivedFittings !== undefined ? sec.arrivedFittings : sec.shippedFittings}件 | 在途: ${sec.transitFittings || 0}件 | 计划: ${sec.totalFittings}件`">
                              <!-- 实体到货 (实色) -->
                              <div 
                                class="micro-bar-fill gold" 
                                :style="{ width: Math.min(sec.arrivedFittingPercent !== undefined ? sec.arrivedFittingPercent : sec.fittingPercent, 100) + '%' }"
                              ></div>
                              <!-- 发货与到货差值 (在途闪烁高亮) -->
                              <div 
                                v-if="sec.transitFittingPercent > 0"
                                class="micro-bar-transit gold-transit" 
                                :style="{ 
                                  left: Math.min(sec.arrivedFittingPercent, 100) + '%', 
                                  width: Math.min(sec.transitFittingPercent, 100 - sec.arrivedFittingPercent) + '%' 
                                }"
                                :title="`管件在途运送: ${sec.transitFittings} 件`"
                              ></div>
                            </div>
                          </div>

                          <!-- 4. 现场存量微核算条 (方案三) -->
                          <div class="sec-stock-strip">
                            <div class="stock-item pipe-stock" :title="`保温管现场可用库存: ${sec.stockKm !== undefined ? sec.stockKm : Math.max(0, Math.round(((sec.arrivedKm !== undefined ? sec.arrivedKm : sec.shippedKm) - (sec.installedKm || 0)) * 100) / 100)} km (到货 - 施工)`">
                              <span class="stock-dot green"></span>
                              <span class="stock-label">保温管库存量:</span>
                              <strong class="stock-val green-text">{{ sec.stockKm !== undefined ? sec.stockKm : Math.max(0, Math.round(((sec.arrivedKm !== undefined ? sec.arrivedKm : sec.shippedKm) - (sec.installedKm || 0)) * 100) / 100) }}<span class="stock-unit">km</span></strong>
                            </div>
                            <span class="stock-divider">/</span>
                            <div class="stock-item fitting-stock" :title="`管件现场可用库存: ${sec.stockFittings !== undefined ? sec.stockFittings : Math.max(0, (sec.arrivedFittings || 0) - (sec.installedFittings || 0))} 件 (到货 - 安装)`">
                              <span class="stock-dot gold"></span>
                              <span class="stock-label">管件库存量:</span>
                              <strong class="stock-val gold-text">{{ sec.stockFittings !== undefined ? sec.stockFittings : Math.max(0, (sec.arrivedFittings || 0) - (sec.installedFittings || 0)) }}<span class="stock-unit">件</span></strong>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 第 2 标段立柱：5 标段 (L2 ~ L6) -->
                  <div class="system-sub-col low-system">
                    <div class="system-cards-list">
                      <div 
                        v-for="sec in col2Sections" 
                        :key="sec.id" 
                        class="demand-node-card"
                        :class="[
                          sec.system_type === 'high' ? 'high-system' : 'low-system',
                          { 
                            active: activeNodeIds.has('sec_' + sec.id),
                            highlighted: lastImpactedSectionId === sec.id || (hoveredSupplierId && isSuppliedBy(sec.id, hoveredSupplierId)),
                            'is-event-target': isAnimationRunning && activeSectionId === sec.id,
                            [`event-cat-${activeEventCategory}`]: isAnimationRunning && activeSectionId === sec.id,
                            [`event-mat-${activeMaterialType}`]: isAnimationRunning && activeSectionId === sec.id,
                            dimmed: (hoveredSupplierId && !isSuppliedBy(sec.id, hoveredSupplierId)) || 
                                    (hoveredSectionId && hoveredSectionId !== sec.id) ||
                                    (isAnimationRunning && activeSectionId && activeSectionId !== sec.id && !hoveredSectionId && !hoveredSupplierId),
                            completed: sec.pipePercent >= 100 && sec.fittingPercent >= 100
                          }
                        ]"
                        :id="'node-sec_' + sec.id"
                        @mouseenter="handleNodeMouseEnter('sec', sec.id)"
                        @mouseleave="handleNodeMouseLeave('sec')"
                      >
                        <!-- 物理对齐连接端口 (左锚点) -->
                        <div class="node-port port-in" :id="'port-in-sec_' + sec.id" title="标段签收入口">
                          <span class="port-dot"></span>
                        </div>

                        <div class="sec-card-header">
                          <div class="sec-badge-name">
                            <span class="sec-sys-badge" :class="sec.system_type">{{ sec.system_type === 'high' ? '🔥 高温' : '💧 低温' }}</span>
                            <strong class="sec-title" :title="sec.name">{{ sec.name }}</strong>
                          </div>
                          <span class="sec-status-chip" :class="{ running: sec.construction_status === '施工中' }">
                            <span class="chip-dot"></span>
                            <span>{{ sec.construction_status }}</span>
                          </span>
                        </div>

                        <!-- 保温管、施工量与管件三轨微进度 (支持在途差值高亮闪动) -->
                        <div class="sec-metrics-body">
                          <!-- 1. 保温管 -->
                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label pipe-tag">
                                <svg class="tag-mini-icon" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M21 21H3V3l18 18z"/>
                                  <path d="M8 17v2"/>
                                  <path d="M12 17v2"/>
                                  <path d="M16 17v2"/>
                                </svg>
                                <span>保温管</span>
                              </span>
                              <span class="line-val cyan-text">
                                {{ sec.arrivedKm !== undefined ? sec.arrivedKm : sec.shippedKm }}<span v-if="sec.transitKm > 0" class="transit-num-tag cyan-transit" title="在途运送量">(+{{ sec.transitKm }})</span> / {{ sec.designKm }} km
                              </span>
                              <span class="line-pct cyan-text">{{ sec.pipePercent }}%</span>
                            </div>
                            <div class="micro-bar-bg" :title="`到货: ${sec.arrivedKm !== undefined ? sec.arrivedKm : sec.shippedKm}km | 在途: ${sec.transitKm || 0}km | 设计: ${sec.designKm}km`">
                              <!-- 实体到货 (实色) -->
                              <div 
                                class="micro-bar-fill cyan" 
                                :style="{ width: Math.min(sec.arrivedPercent !== undefined ? sec.arrivedPercent : sec.pipePercent, 100) + '%' }"
                              ></div>
                              <!-- 发货与到货差值 (在途闪烁高亮) -->
                              <div 
                                v-if="sec.transitPercent > 0"
                                class="micro-bar-transit cyan-transit" 
                                :style="{ 
                                  left: Math.min(sec.arrivedPercent, 100) + '%', 
                                  width: Math.min(sec.transitPercent, 100 - sec.arrivedPercent) + '%' 
                                }"
                                :title="`直管在途运送: ${sec.transitKm} km`"
                              ></div>
                            </div>
                          </div>

                          <!-- 2. 施工量 -->
                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label construct-tag">
                                <svg class="tag-mini-icon" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M2 22h20"/>
                                  <path d="M13 2v20"/>
                                  <path d="M5 2h14l-7 7"/>
                                  <path d="M13 9h-3l-2 5h5"/>
                                  <circle cx="6" cy="14" r="1" fill="currentColor"/>
                                </svg>
                                <span>施工量</span>
                              </span>
                              <span class="line-val green-text">{{ sec.installedKm || '0.00' }} / {{ sec.designKm }} km</span>
                              <span class="line-pct green-text">{{ sec.installedPercent || 0 }}%</span>
                            </div>
                            <div class="micro-bar-bg" :title="`已安装施工: ${sec.installedKm || '0.00'} km`">
                              <div class="micro-bar-fill green" :style="{ width: Math.min(sec.installedPercent || 0, 100) + '%' }"></div>
                            </div>
                          </div>

                          <!-- 3. 管件 -->
                          <div class="sec-metric-line">
                            <div class="line-info">
                              <span class="line-label fitting-tag">
                                <svg class="tag-mini-icon" viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M12 2l7 4.5v9L12 20l-7-4.5v-9L12 2z"/>
                                  <circle cx="12" cy="11" r="3"/>
                                </svg>
                                <span>管件</span>
                              </span>
                              <span class="line-val gold-text">
                                {{ sec.arrivedFittings !== undefined ? sec.arrivedFittings : sec.shippedFittings }}<span v-if="sec.transitFittings > 0" class="transit-num-tag gold-transit" title="在途运送量">(+{{ sec.transitFittings }})</span> / {{ sec.totalFittings }} 件
                              </span>
                              <span class="line-pct gold-text">{{ sec.fittingPercent }}%</span>
                            </div>
                            <div class="micro-bar-bg" :title="`到货: ${sec.arrivedFittings !== undefined ? sec.arrivedFittings : sec.shippedFittings}件 | 在途: ${sec.transitFittings || 0}件 | 计划: ${sec.totalFittings}件`">
                              <!-- 实体到货 (实色) -->
                              <div 
                                class="micro-bar-fill gold" 
                                :style="{ width: Math.min(sec.arrivedFittingPercent !== undefined ? sec.arrivedFittingPercent : sec.fittingPercent, 100) + '%' }"
                              ></div>
                              <!-- 发货与到货差值 (在途闪烁高亮) -->
                              <div 
                                v-if="sec.transitFittingPercent > 0"
                                class="micro-bar-transit gold-transit" 
                                :style="{ 
                                  left: Math.min(sec.arrivedFittingPercent, 100) + '%', 
                                  width: Math.min(sec.transitFittingPercent, 100 - sec.arrivedFittingPercent) + '%' 
                                }"
                                :title="`管件在途运送: ${sec.transitFittings} 件`"
                              ></div>
                            </div>
                          </div>

                          <!-- 4. 现场存量微核算条 (方案三) -->
                          <div class="sec-stock-strip">
                            <div class="stock-item pipe-stock" :title="`保温管现场可用库存: ${sec.stockKm !== undefined ? sec.stockKm : Math.max(0, Math.round(((sec.arrivedKm !== undefined ? sec.arrivedKm : sec.shippedKm) - (sec.installedKm || 0)) * 100) / 100)} km (到货 - 施工)`">
                              <span class="stock-dot green"></span>
                              <span class="stock-label">保温管库存量:</span>
                              <strong class="stock-val green-text">{{ sec.stockKm !== undefined ? sec.stockKm : Math.max(0, Math.round(((sec.arrivedKm !== undefined ? sec.arrivedKm : sec.shippedKm) - (sec.installedKm || 0)) * 100) / 100) }}<span class="stock-unit">km</span></strong>
                            </div>
                            <span class="stock-divider">/</span>
                            <div class="stock-item fitting-stock" :title="`管件现场可用库存: ${sec.stockFittings !== undefined ? sec.stockFittings : Math.max(0, (sec.arrivedFittings || 0) - (sec.installedFittings || 0))} 件 (到货 - 安装)`">
                              <span class="stock-dot gold"></span>
                              <span class="stock-label">管件库存量:</span>
                              <strong class="stock-val gold-text">{{ sec.stockFittings !== undefined ? sec.stockFittings : Math.max(0, (sec.arrivedFittings || 0) - (sec.installedFittings || 0)) }}<span class="stock-unit">件</span></strong>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧栏：实时战报动态流水与重大保供里程碑 (基于真实工程全链路数据) -->
      <section class="screen-col right-col" :class="{ 'mobile-active-col': activeMobileTab === 'feed' }">
        <!-- 实时工程战报流 -->
        <div class="panel-box live-feed-panel">
          <div class="panel-header">
            <div class="panel-title">
              <span class="title-icon title-icon-broadcast">
                <svg class="title-svg-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 11l13-4.5v11L3 13v-2z" fill="rgba(56, 189, 248, 0.25)" stroke="#38bdf8" stroke-width="2"/>
                  <path d="M6 14v4a2 2 0 0 0 2 2h1" stroke="#38bdf8" stroke-width="2"/>
                  <path d="M19 8c1.5 1 2.2 2.3 2.2 4s-.7 3-2.2 4" stroke="#00f2fe" stroke-width="2"/>
                </svg>
              </span>
              <span>全网工程实时动态播报</span>
            </div>
            <div 
              class="live-status-pill live-connected" 
              :class="{ 'is-refreshing': isManualRefreshing }"
              @click="handleManualRefresh"
              title="系统已实时直连数据库 (点击立即强制同步最新数据)"
            >
              <span class="live-dot live-pulse"></span>
              <span class="status-label">{{ isManualRefreshing ? '正在同步...' : '实时直连中' }}</span>
              <span class="refresh-sym" :class="{ 'spin-anim': isManualRefreshing }">🔄</span>
            </div>
          </div>

          <!-- 统一业务分类筛选按钮与展开式点选浮层 (纯净分类选择，无条数后缀) -->
          <div class="feed-filter-unified-bar" ref="feedFilterMenuRef">
            <div class="filter-dropdown-wrapper">
              <button 
                class="unified-filter-btn" 
                :class="{ 'menu-open': isFeedFilterMenuOpen, 'is-filtered': feedFilter !== 'all' }"
                @click.stop="isFeedFilterMenuOpen = !isFeedFilterMenuOpen"
                title="点击展开/收起业务分类筛选菜单"
              >
                <div class="filter-btn-left">
                  <span class="filter-btn-icon">{{ currentFilterOption.icon }}</span>
                  <span class="filter-btn-label">业务分类:</span>
                  <strong class="filter-btn-current">{{ currentFilterOption.label }}</strong>
                </div>
                <div class="filter-btn-right">
                  <span class="filter-caret">{{ isFeedFilterMenuOpen ? '▲' : '▼' }}</span>
                </div>
              </button>

              <!-- 展开式点选面板 -->
              <transition name="filter-dropdown-anim">
                <div v-if="isFeedFilterMenuOpen" class="feed-filter-popover" @click.stop>
                  <div class="popover-tip-header">
                    <span class="popover-title-text">⚡ 选择业务动态分类</span>
                    <button 
                      v-if="feedFilter !== 'all'" 
                      class="reset-filter-link" 
                      @click="selectFeedFilter('all')"
                    >重置全部</button>
                  </div>
                  <div class="popover-options-grid">
                    <div 
                      v-for="opt in feedFilterOptions" 
                      :key="opt.key"
                      class="filter-option-row"
                      :class="{ active: feedFilter === opt.key }"
                      @click="selectFeedFilter(opt.key)"
                    >
                      <div class="option-tag-part">
                        <span class="option-dot" :style="{ background: opt.color, boxShadow: '0 0 6px ' + opt.color }"></span>
                        <span class="option-icon">{{ opt.icon }}</span>
                        <span class="option-title">{{ opt.label }}</span>
                      </div>
                      <div class="option-meta-part">
                        <span v-if="feedFilter === opt.key" class="option-check">✓</span>
                      </div>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </div>

          <!-- 战报消息动态上浮列表 -->
          <div class="feed-list-wrapper">
            <transition-group name="feed-item" tag="div" class="feed-list">
              <div 
                v-for="feed in filteredFeedList" 
                :key="feed.id" 
                class="feed-card"
                :class="[
                  feed.category_key || 'dispatch',
                  feed.type === 'fitting' ? 'mat-fitting' : 'mat-pipe',
                  { 
                    'just-arrived': feed.isNew,
                    'is-active-feed': isAnimationRunning && activeEvent && activeEvent.id === feed.id,
                    'is-fitting-event': feed.type === 'fitting'
                  }
                ]"
                @mouseenter="hoveredFeedItem = feed"
                @mouseleave="hoveredFeedItem = null"
                @click="handleFeedClick(feed)"
                title="悬停/点击在中心拓扑图上即时聚焦并高亮该业务动态关联节点与路线"
                style="cursor: pointer;"
              >
                <!-- Row 1: 分类标签 + 经办人 + 发生时间 -->
                <div class="feed-card-header">
                  <div class="header-left-meta">
                    <span 
                      class="feed-category-tag" 
                      :class="[
                        feed.category_key || 'dispatch',
                        feed.type === 'fitting' ? 'mat-fitting' : 'mat-pipe'
                      ]"
                    >
                      {{ feed.category }}
                    </span>
                    <span v-if="feed.operator" class="feed-operator-tag" :title="'经办人: ' + feed.operator">
                      👤 {{ feed.operator }}
                    </span>
                  </div>
                  <span class="feed-time">{{ feed.time }}</span>
                </div>

                <!-- Row 2: 动态标题与流向行 (仅发货展示流向箭头，其他类型清晰两端对齐展示) -->
                <div class="feed-card-headline">
                  <div class="route-line-box" :class="{ 'is-dispatch': feed.category_key === 'dispatch' || feed.category === '厂家发货' }">
                    <span class="route-source" :title="getFeedSourceOrAction(feed)">
                      {{ getFeedSourceOrAction(feed) }}
                    </span>
                    <!-- 仅在厂家发货动态时展示流向箭头 -->
                    <span v-if="feed.category_key === 'dispatch' || feed.category === '厂家发货'" class="route-arrow">──►</span>
                    <span class="route-target" :title="feed.target">
                      {{ feed.target }}
                    </span>
                  </div>
                </div>

                <!-- Row 3: 规格与数量明细栏 (左侧规格截断，右侧高亮数量，永不串行) -->
                <div class="feed-spec-box">
                  <div class="spec-text-col" :title="feed.specification">
                    <span class="spec-name">{{ feed.specification }}</span>
                  </div>
                  <div class="spec-qty-col">
                    <span class="spec-amount-badge" :class="feed.type">{{ feed.amount }}</span>
                  </div>
                </div>

                <!-- Row 4: 单号/车牌 + 正向动态评价 -->
                <div class="feed-card-footer">
                  <span class="feed-code-tag" :title="feed.shipmentCode">
                    <span class="code-icon">🔖</span>
                    <span class="code-val">{{ feed.shipmentCode }}</span>
                  </span>
                  <span class="feed-pos-tag" :title="feed.positiveTag">✨ {{ feed.positiveTag }}</span>
                </div>
              </div>
            </transition-group>
          </div>
        </div>

        <!-- 🏆 本周战报：保温管 vs 管件 10 秒自动轮播交替展示（丝滑过渡动效） -->
        <div
          class="panel-box weekly-report-panel"
          :class="{ 'is-switching': isWeeklySwitching, 'tab-pipe': activeWeeklyTab === 'pipe', 'tab-fitting': activeWeeklyTab === 'fitting' }"
          @mouseenter="isWeeklyHovered = true"
          @mouseleave="isWeeklyHovered = false"
        >
          <div class="panel-header">
            <div class="panel-title" :title="activeWeeklyTab === 'pipe' ? `当前展示：本周保温管施工战报（每 ${bsConfig.weekly_rotation_interval_sec || 10} 秒自动轮播）` : `当前展示：本周管件施工战报（每 ${bsConfig.weekly_rotation_interval_sec || 10} 秒自动轮播）`">
              <transition name="weekly-title-anim" mode="out-in">
                <div :key="activeWeeklyTab" class="panel-title-anim-box">
                  <span class="title-icon">
                    <svg v-if="activeWeeklyTab === 'pipe'" class="title-svg-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" fill="rgba(0, 242, 254, 0.15)" stroke="#00f2fe" stroke-width="2"/>
                      <line x1="16" y1="2" x2="16" y2="6" stroke="#00f2fe" stroke-width="2"/>
                      <line x1="8" y1="2" x2="8" y2="6" stroke="#00f2fe" stroke-width="2"/>
                      <line x1="3" y1="10" x2="21" y2="10" stroke="#00f2fe" stroke-width="2"/>
                      <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01" stroke="#00f2fe" stroke-width="2.5"/>
                    </svg>
                    <svg v-else class="title-svg-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="3" y="3" width="7.5" height="7.5" rx="1.5" fill="rgba(251, 191, 36, 0.2)" stroke="#fbbf24" stroke-width="2"/>
                      <rect x="13.5" y="3" width="7.5" height="7.5" rx="1.5" fill="rgba(251, 191, 36, 0.2)" stroke="#fbbf24" stroke-width="2"/>
                      <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.5" fill="rgba(251, 191, 36, 0.2)" stroke="#fbbf24" stroke-width="2"/>
                      <rect x="3" y="13.5" width="7.5" height="7.5" rx="1.5" fill="rgba(251, 191, 36, 0.2)" stroke="#fbbf24" stroke-width="2"/>
                      <circle cx="12" cy="12" r="1.8" fill="#fbbf24"/>
                    </svg>
                  </span>
                  <span class="title-text">{{ activeWeeklyTab === 'pipe' ? '本周保温管施工战报' : '本周管件施工战报' }}</span>
                </div>
              </transition>
            </div>
            <div class="header-right-meta" style="display: flex; align-items: center; gap: 6px;">
              <!-- 轮播倒计时徽章 -->
              <span
                class="weekly-countdown-badge"
                :class="{ paused: isWeeklyHovered }"
                :title="isWeeklyHovered ? '鼠标悬停中：已暂停交替轮播' : `每 ${bsConfig.weekly_rotation_interval_sec || 10} 秒自动交替轮播（倒计时 ${weeklyCountdownSec} 秒）`"
              >
                <span class="countdown-pulse-dot" :class="{ paused: isWeeklyHovered }"></span>
                <span class="countdown-text">{{ isWeeklyHovered ? '已暂停' : `${weeklyCountdownSec}s` }}</span>
              </span>
              <transition name="weekly-fade-fast" mode="out-in">
                <span :key="currentWeeklyDateRange" class="panel-tag gold" :title="'统计周期: ' + currentWeeklyDateRange">
                  {{ currentWeeklyDateRange }}
                </span>
              </transition>
            </div>
          </div>

          <!-- 1. 顶部固定双 KPI：保温管 (km) vs 管件 (件) 丝滑切换过渡 -->
          <transition name="weekly-kpi-anim" mode="out-in">
            <div :key="activeWeeklyTab" class="weekly-kpi-grid">
              <div class="weekly-kpi-card ship-card" :title="activeWeeklyTab === 'pipe' ? '近7日累计发运保温管总量' : '近7日累计发运管件总量'">
                <div class="kpi-card-header">
                  <span class="kpi-dot cyan"></span>
                  <span class="kpi-title">{{ activeWeeklyTab === 'pipe' ? '7日累计发货量' : '7日累计发运量' }}</span>
                </div>
                <div class="kpi-main-val cyan-text">
                  {{ activeWeeklyTab === 'pipe' ? formatWeeklyKm(weeklyReport.total_shipped_km) : formatWeeklyInt(weeklyFittingReport.total_shipped_pcs) }}
                  <span class="unit">{{ activeWeeklyTab === 'pipe' ? 'km' : '件' }}</span>
                </div>
                <div class="weekly-kpi-note">{{ activeWeeklyTab === 'pipe' ? weeklyShipNote : weeklyFitShipNote }}</div>
              </div>

              <div
                class="weekly-kpi-card"
                :class="activeWeeklyTab === 'pipe' ? 'fit-usage-card' : 'usage-card'"
                :title="activeWeeklyTab === 'pipe' ? '近7日现场累计施工使用（敷设）总量' : '近7日现场累计安装使用管件总量'"
              >
                <div class="kpi-card-header">
                  <span class="kpi-dot" :class="activeWeeklyTab === 'pipe' ? 'emerald' : 'gold'"></span>
                  <span class="kpi-title">{{ activeWeeklyTab === 'pipe' ? '7日累计施工量' : '7日累计安装量' }}</span>
                </div>
                <div class="kpi-main-val" :class="activeWeeklyTab === 'pipe' ? 'emerald-text' : 'gold-text'">
                  {{ activeWeeklyTab === 'pipe' ? formatWeeklyKm(weeklyReport.total_usage_km) : formatWeeklyInt(weeklyFittingReport.total_usage_pcs) }}
                  <span class="unit">{{ activeWeeklyTab === 'pipe' ? 'km' : '件' }}</span>
                </div>
                <div class="weekly-kpi-note">{{ activeWeeklyTab === 'pipe' ? weeklyUsageNote : weeklyFitUsageNote }}</div>
              </div>
            </div>
          </transition>

          <!-- 2. 固定趋势区：根据 activeWeeklyTab 动态绘制折线 -->
          <div class="weekly-chart-heading">
            <transition name="weekly-fade-fast" mode="out-in">
              <span :key="activeWeeklyTab">每日趋势 ({{ activeWeeklyTab === 'pipe' ? 'km' : '件' }})</span>
            </transition>
            <transition name="weekly-fade-fast" mode="out-in">
              <span :key="activeWeeklyTab" style="font-size: 9.5px; opacity: 0.75;">{{ activeWeeklyTab === 'pipe' ? '双轨：发货 vs 施工' : '双轨：发运 vs 安装' }}</span>
            </transition>
          </div>
          <div class="weekly-chart-box">
            <div ref="weeklyChartRef" class="weekly-echarts-dom"></div>
            <transition name="weekly-fade-fast">
              <div v-if="!currentWeeklyHasBusinessData" class="weekly-empty-state">
                <strong>本周暂无{{ activeWeeklyTab === 'pipe' ? '保温管' : '管件' }}业务数据</strong>
                <span>累计指标与趋势将在数据同步后自动更新</span>
              </div>
            </transition>
          </div>

          <!-- 3. 固定复盘栏：根据 activeWeeklyTab 展示峰值与昨日数据 (带过渡) -->
          <transition name="weekly-insight-anim" mode="out-in">
            <div :key="activeWeeklyTab" class="weekly-insight-grid">
              <div>
                <span>{{ activeWeeklyTab === 'pipe' ? '发货峰值日' : '发运峰值日' }}</span>
                <strong>{{ activeWeeklyTab === 'pipe' ? weeklyShipPeakText : weeklyFitShipPeakText }}</strong>
              </div>
              <div>
                <span>{{ activeWeeklyTab === 'pipe' ? '施工峰值日' : '安装峰值日' }}</span>
                <strong>{{ activeWeeklyTab === 'pipe' ? weeklyUsagePeakText : weeklyFitUsagePeakText }}</strong>
              </div>
              <div>
                <span>{{ activeWeeklyTab === 'pipe' ? '昨日发货 / 施工' : '昨日发运 / 安装' }}</span>
                <strong>{{ activeWeeklyTab === 'pipe' ? weeklyTodayText : weeklyFitTodayText }}</strong>
              </div>
            </div>
          </transition>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { ref, reactive, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../../daily_report_25_26/store/auth'
import {
  getTubeWorkspaceConfigSummary,
  getTubeBigScreenData,
  updateTubeBigScreenConfig,
  recordTubeBigScreenAccess
} from '../../daily_report_25_26/services/api'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const projectKey = computed(() => String(route.params.projectKey || 'insulation_pipe_supply_2026'))

// 仅限 Global_admin 角色具备保存/持久化大屏设定的特权
const isGlobalAdmin = computed(() => {
  const group = String(auth?.user?.group || '').trim()
  return group === 'Global_admin'
})

// --- ⚙️ 大屏运行参数与节律配置状态 (持久化存储于 tube_config.json) ---
const bsConfig = reactive({
  animation_active_duration_sec: 5,
  animation_rest_duration_sec: 5,
  auto_sync_interval_sec: 20,
  live_stream_interval_sec: 3,
  flyline_travel_sec: 1.8,
  feed_limit: 40,
  weather_cache_duration_min: 15,
  transit_duration_min_hours: 1.0,
  transit_duration_max_hours: 36.0,
  weekly_rotation_interval_sec: 10
})
const isSavingConfig = ref(false)
const configSaveStatus = ref(null)
let configSaveStatusTimer = null

function showSaveStatus(msg, type = 'success') {
  configSaveStatus.value = { msg, type }
  if (configSaveStatusTimer) clearTimeout(configSaveStatusTimer)
  configSaveStatusTimer = setTimeout(() => {
    configSaveStatus.value = null
  }, 3000)
}

// 调节滑块时本地即刻动态生效
function applyConfigLocally() {
  startAnimationLoop()
  startWeeklyRotation()
  
  if (!isLiveStreamMode.value && !autoDemoRunning.value) {
    if (autoSyncTimer) clearInterval(autoSyncTimer)
    const intervalMs = Math.max(5, Number(bsConfig.auto_sync_interval_sec) || 20) * 1000
    autoSyncTimer = setInterval(loadRealData, intervalMs)
  }
  
  if (isLiveStreamMode.value) {
    if (liveStreamTimer) clearInterval(liveStreamTimer)
    const liveMs = Math.max(1, Number(bsConfig.live_stream_interval_sec) || 3) * 1000
    liveStreamTimer = setInterval(pollLiveRealData, liveMs)
  }
  
  if (liveFeedList.value && liveFeedList.value.length > bsConfig.feed_limit) {
    liveFeedList.value = liveFeedList.value.slice(0, bsConfig.feed_limit)
  }
}

// 持久化保存至后端 tube_config.json (仅限 Global_admin)
async function handleSaveConfigToBackend() {
  if (!isGlobalAdmin.value) {
    showSaveStatus('⚠️ 权限不足：仅限 Global_admin 管理员可以保存大屏设定', 'error')
    return
  }
  isSavingConfig.value = true
  try {
    applyConfigLocally()
    const res = await updateTubeBigScreenConfig(projectKey.value, bsConfig)
    if (res && res.ok) {
      if (res.big_screen_config) {
        Object.assign(bsConfig, res.big_screen_config)
      }
      showSaveStatus('✅ 已持久化保存至配置文件', 'success')
    } else {
      showSaveStatus('⚠️ 保存异常', 'error')
    }
  } catch (err) {
    console.error('保存大屏配置失败:', err)
    showSaveStatus('❌ 保存失败: ' + (err.message || '网络异常'), 'error')
  } finally {
    isSavingConfig.value = false
  }
}

// 恢复出厂默认参数设置 (仅限 Global_admin)
async function handleResetConfigToDefault() {
  if (!isGlobalAdmin.value) {
    showSaveStatus('⚠️ 权限不足：仅限 Global_admin 管理员可以重置设定', 'error')
    return
  }
  bsConfig.animation_active_duration_sec = 5
  bsConfig.animation_rest_duration_sec = 5
  bsConfig.auto_sync_interval_sec = 20
  bsConfig.live_stream_interval_sec = 3
  bsConfig.flyline_travel_sec = 1.8
  bsConfig.feed_limit = 40
  bsConfig.weather_cache_duration_min = 15
  bsConfig.transit_duration_min_hours = 1.0
  bsConfig.transit_duration_max_hours = 36.0
  bsConfig.weekly_rotation_interval_sec = 10
  await handleSaveConfigToBackend()
  showSaveStatus('🔄 已恢复出厂默认设定', 'success')
}

// --- 主题切换状态 ---
const currentTheme = ref(localStorage.getItem('phoenix_tube_bigscreen_theme') || 'dark')
const isDark = computed(() => currentTheme.value === 'dark')

function toggleTheme() {
  currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem('phoenix_tube_bigscreen_theme', currentTheme.value)
  recalculateFlylines()
}

// --- 基础状态 ---
const containerRef = ref(null)
const topologyContainerRef = ref(null)
const svgRef = ref(null)
const isFullscreen = ref(false)
const configSummary = ref(null)
const realShowDate = ref('')
const currentTimeStr = ref('')
const isControlMenuOpen = ref(false)
const controlMenuRef = ref(null)
const isFeedFilterMenuOpen = ref(false)
const feedFilterMenuRef = ref(null)

// --- 移动端专属响应式状态 ---
const activeMobileTab = ref('kpi') // 'kpi' | 'topology' | 'feed'

function setMobileTab(tabKey) {
  activeMobileTab.value = tabKey
  if (tabKey === 'topology') {
    setTimeout(() => {
      recalculateFlylines()
    }, 60)
    setTimeout(() => {
      recalculateFlylines()
    }, 250)
  } else if (tabKey === 'feed') {
    setTimeout(() => {
      handleResizeWeeklyChart()
    }, 60)
    setTimeout(() => {
      handleResizeWeeklyChart()
    }, 250)
  }
}

function toggleControlMenu() {
  isControlMenuOpen.value = !isControlMenuOpen.value
}

function handleGlobalClick(e) {
  if (isControlMenuOpen.value && controlMenuRef.value && !controlMenuRef.value.contains(e.target)) {
    isControlMenuOpen.value = false
  }
  if (isFeedFilterMenuOpen.value && feedFilterMenuRef.value && !feedFilterMenuRef.value.contains(e.target)) {
    isFeedFilterMenuOpen.value = false
  }
}
let timerClock = null
let autoDemoTimer = null
let autoSyncTimer = null
let liveStreamTimer = null
let resizeObserver = null
let rAFId = null
const autoDemoRunning = ref(false)
const feedFilter = ref('all')

const feedFilterOptions = [
  { key: 'all', label: '全部', icon: '🌐', color: '#00f2fe' },
  { key: 'dispatch', label: '厂家发货', icon: '🚚', color: '#38bdf8' },
  { key: 'arrival', label: '确认到货', icon: '📍', color: '#60a5fa' },
  { key: 'receive', label: '施工单位收货', icon: '🏗️', color: '#f59e0b' },
  { key: 'warehouse', label: '库管确认', icon: '🛡️', color: '#10b981' },
  { key: 'usage', label: '施工量确认', icon: '📐', color: '#a855f7' },
  { key: 'plan', label: '需求量申报', icon: '📋', color: '#f43f5e' },
]

function getFeedCountByCategory(categoryKey) {
  if (categoryKey === 'all') return liveFeedList.value.length
  return liveFeedList.value.filter(item => item.category_key === categoryKey || item.type === categoryKey).length
}

const currentFilterOption = computed(() => {
  return feedFilterOptions.find(o => o.key === feedFilter.value) || feedFilterOptions[0]
})

function selectFeedFilter(key) {
  feedFilter.value = key
  isFeedFilterMenuOpen.value = false
}
const lastImpactedSectionId = ref(null)
const activeSectionTab = ref('all') // 'all' | 'high' | 'low'

// --- 生产实况 · 真实数据流直连模式 (Live Stream Mode) ---
const isLiveStreamMode = ref(false)
const knownFeedIds = ref(new Set())
let initialDataLoaded = false

// --- 交互悬停聚焦状态 (Hover Focus: 仅在 PC 桌面鼠标设备生效，触屏/移动端彻底禁用) ---
const hoveredSupplierId = ref(null)
const hoveredSectionId = ref(null)
const activeShipmentLineIds = ref(new Set()) // 默认全部静止基准线，仅在真实发货或 PC 鼠标悬停时按需激活
const isAnyHovered = computed(() => !!hoveredSupplierId.value || !!hoveredSectionId.value)

function isMobileOrTouchEvent() {
  if (typeof window === 'undefined') return false
  if (window.innerWidth <= 900) return true
  if (window.matchMedia && window.matchMedia('(hover: none)').matches) return true
  return false
}

function handleNodeMouseEnter(type, id) {
  if (isMobileOrTouchEvent()) return
  if (type === 'sup') {
    hoveredSupplierId.value = id
  } else if (type === 'sec') {
    hoveredSectionId.value = id
  }
}

function handleNodeMouseLeave(type) {
  if (isMobileOrTouchEvent()) return
  if (type === 'sup') {
    hoveredSupplierId.value = null
  } else if (type === 'sec') {
    hoveredSectionId.value = null
  }
}

// --- 权威默认数据源 (保证第一帧即刻渲染完整节点与飞线) ---
const defaultSupplyNodes = [
  {
    id: 'sup_kaiyuan',
    raw_id: 'kaiyuan',
    code: 'SA',
    name: '大连开元热力管道',
    assigned_sections: ['高温水 1、2 标'],
    assigned_section_ids: ['high_lot_1', 'high_lot_2']
  },
  {
    id: 'sup_xinruide',
    raw_id: 'xinruide',
    code: 'SB',
    name: '河北鑫瑞得管道',
    assigned_sections: ['低温水 1、2、3 标'],
    assigned_section_ids: ['low_lot_1', 'low_lot_2', 'low_lot_3']
  },
  {
    id: 'sup_吴近',
    raw_id: '吴近',
    code: 'SC',
    name: '能源集团保温管厂',
    assigned_sections: ['高水 3、4 标 / 低水 4、5、6 标'],
    assigned_section_ids: ['high_lot_3', 'high_lot_4', 'low_lot_4', 'low_lot_5', 'low_lot_6']
  }
]

const defaultSectionList = [
  { id: 'high_lot_1', name: '高温水_标段1', code: 'H1', system_type: 'high', construction_status: '施工中', designKm: 18.5, shippedKm: 12.0, arrivedKm: 10.0, transitKm: 2.0, pipePercent: 64.9, arrivedPercent: 54.1, transitPercent: 10.8, installedKm: 0.23, installedPercent: 1.2, totalFittings: 400, shippedFittings: 280, arrivedFittings: 240, transitFittings: 40, fittingPercent: 70.0, arrivedFittingPercent: 60.0, transitFittingPercent: 10.0 },
  { id: 'high_lot_2', name: '高温水_标段2', code: 'H2', system_type: 'high', construction_status: '未开工', designKm: 15.2, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 350, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 },
  { id: 'high_lot_3', name: '高温水_标段3', code: 'H3', system_type: 'high', construction_status: '未开工', designKm: 14.8, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 320, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 },
  { id: 'high_lot_4', name: '高温水_标段4', code: 'H4', system_type: 'high', construction_status: '未开工', designKm: 16.0, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 360, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 },
  { id: 'low_lot_1', name: '低温水_标段1', code: 'L1', system_type: 'low', construction_status: '未开工', designKm: 8.6, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 180, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 },
  { id: 'low_lot_2', name: '低温水_标段2', code: 'L2', system_type: 'low', construction_status: '未开工', designKm: 9.1, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 195, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 },
  { id: 'low_lot_3', name: '低温水_标段3', code: 'L3', system_type: 'low', construction_status: '未开工', designKm: 11.2, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 240, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 },
  { id: 'low_lot_4', name: '低温水_标段4', code: 'L4', system_type: 'low', construction_status: '未开工', designKm: 10.5, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 220, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 },
  { id: 'low_lot_5', name: '低温水_标段5', code: 'L5', system_type: 'low', construction_status: '未开工', designKm: 7.8, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 160, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 },
  { id: 'low_lot_6', name: '低温水_标段6', code: 'L6', system_type: 'low', construction_status: '未开工', designKm: 8.2, shippedKm: 0.0, arrivedKm: 0.0, transitKm: 0.0, pipePercent: 0.0, arrivedPercent: 0.0, transitPercent: 0.0, installedKm: 0.0, installedPercent: 0.0, totalFittings: 175, shippedFittings: 0, arrivedFittings: 0, transitFittings: 0, fittingPercent: 0.0, arrivedFittingPercent: 0.0, transitFittingPercent: 0.0 }
]

// 真实实体库引用
let rawSupplyEntities = []
let rawDemandEntities = []
let rawPipeModels = []

// --- 核心指标状态 (由后端数据库精准聚合统计) ---
const kpiData = reactive({
  pipeDesignKm: 0.0,
  pipeShippedKm: 0.0,
  pipeTransitKm: 0.0,
  pipeInstalledKm: 0.0,
  pipeStockKm: 0.0,
  pipeThreeDayPlanKm: 0.0,
  pipeThreeDayGapKm: 0.0,
  pipeDeliveredKm: 0.0,
  fittingTotalPcs: 0,
  fittingShippedPcs: 0,
  fittingTransitPcs: 0,
  fittingInstalledPcs: 0,
  fittingStockPcs: 0,
  fittingArrivedPcs: 0,
  fittingCategoryCount: 0,
  warehouseConfirmRate: 100.0,
  avgTransitHours: 16.4
})

// 今日天气与施工环境 (高德实时数据)
const liveWeatherData = reactive({
  city: '主城区施工现场',
  weather: '多云',
  temperature: '26',
  wind_direction: '微风',
  wind_power: '≤3',
  humidity: '68',
  report_time: '',
  status_tag: '适宜施工',
  status_level: 'success',
  advice: '【适宜施工】当前气象条件良好，可正常组织管网吊装下沟与沟槽焊接作业。',
  forecast: {
    date: '',
    day_weather: '阴',
    night_weather: '阴',
    temp_min: '24',
    temp_max: '29',
    temp_range: '24°C ~ 29°C',
    day_wind: '南风 1-3级',
    night_wind: '南风 1-3级'
  }
})

const getWeatherEmoji = (weatherStr) => {
  const w = String(weatherStr || '').trim()
  if (w.includes('雷')) return '🌩️'
  if (w.includes('暴雨') || w.includes('大雨')) return '⛈️'
  if (w.includes('雨')) return '🌧️'
  if (w.includes('雪')) return '❄️'
  if (w.includes('阴')) return '☁️'
  if (w.includes('多云') || w.includes('少云')) return '⛅'
  if (w.includes('晴')) return '☀️'
  if (w.includes('雾') || w.includes('霾')) return '🌫️'
  return '🌤️'
}

const getWeatherCategory = (weatherStr) => {
  const w = String(weatherStr || '').trim()
  if (w.includes('雷')) return 'thunder'
  if (w.includes('雪')) return 'snow'
  if (w.includes('雨')) return 'rain'
  if (w.includes('阴')) return 'overcast'
  if (w.includes('晴')) return 'sunny'
  if (w.includes('多云') || w.includes('少云')) return 'cloudy'
  if (w.includes('雾') || w.includes('霾')) return 'fog'
  return 'cloudy'
}

const formatWeatherTime = (timeStr) => {
  if (!timeStr) return ''
  const parts = String(timeStr).trim().split(' ')
  if (parts.length >= 2) {
    const timeParts = parts[1].split(':')
    return `${timeParts[0]}:${timeParts[1]}`
  }
  return timeStr
}

// 飘字气泡 (Delta Bubbles)
const bubbles = reactive({
  pipeShipped: null,
  pipeTransit: null,
  fittingShipped: null,
  fittingTransit: null
})

// 活跃高亮节点集合
const activeNodeIds = ref(new Set())

// 激光飞线与粒子状态
const flylines = ref([])
const activeParticles = ref([])

// 实时战报流列表（100% 绑定底层真实业务数据库单据记录）
const liveFeedList = ref([])

// 过滤后的战报流
const filteredFeedList = computed(() => {
  if (feedFilter.value === 'all') return liveFeedList.value
  return liveFeedList.value.filter(item => item.category_key === feedFilter.value || item.type === feedFilter.value)
})

// 管材保供百分比
const pipeCoveragePercent = computed(() => {
  if (!kpiData.pipeDesignKm || kpiData.pipeDesignKm <= 0) return 0
  return Math.min(Math.round((kpiData.pipeShippedKm / kpiData.pipeDesignKm) * 1000) / 10, 100)
})

// 管件保供发运百分比
const fittingCoveragePercent = computed(() => {
  if (!kpiData.fittingTotalPcs || kpiData.fittingTotalPcs <= 0) return 0
  return Math.min(Math.round((kpiData.fittingShippedPcs / kpiData.fittingTotalPcs) * 1000) / 10, 100)
})

// 热门管件类型汇总
const fittingTypeSummary = ref([])

// 管件实际大类数量
const fittingCategoryCount = computed(() => {
  if (kpiData.fittingCategoryCount && kpiData.fittingCategoryCount > 0) {
    return kpiData.fittingCategoryCount
  }
  if (Array.isArray(fittingTypeSummary.value) && fittingTypeSummary.value.length > 0) {
    return fittingTypeSummary.value.length
  }
  return 5
})

// 拓扑节点定义 (3 大真实管厂)
const supplyNodes = ref([...defaultSupplyNodes])

// 真实 10 大标段健康矩阵数据
const sectionProgressList = ref([...defaultSectionList])

// 高温水与低温水系统立柱分离（均衡分配为两列各 5 个标段，避免底部留白）
const highWaterSections = computed(() => sectionProgressList.value.filter(s => s.system_type === 'high'))
const lowWaterSections = computed(() => sectionProgressList.value.filter(s => s.system_type === 'low'))
const col1Sections = computed(() => {
  const half = Math.ceil(sectionProgressList.value.length / 2)
  return sectionProgressList.value.slice(0, half)
})
const col2Sections = computed(() => {
  const half = Math.ceil(sectionProgressList.value.length / 2)
  return sectionProgressList.value.slice(half)
})

function setSectionTab(tab) {
  activeSectionTab.value = tab
  recalculateFlylines()
}

// 供需隶属判断辅助函数
function isSuppliedBy(secId, supId) {
  const sup = supplyNodes.value.find(s => s.id === supId)
  if (!sup) return false
  const assigned = sup.assigned_section_ids || []
  return assigned.includes(secId)
}

function isSupplierOfSection(supId, secId) {
  return isSuppliedBy(secId, supId)
}

// 判断指定标段是否有实际发货/到货履约流水（发货实绩 > 0）
function isSectionShipped(secId) {
  if (!secId) return false
  const cleanId = String(secId).replace(/^sec_/, '')
  const sec = sectionProgressList.value.find(s => s.id === cleanId)
  if (!sec) return false
  const shippedKm = Number(sec.shippedKm) || 0
  const shippedFittings = Number(sec.shippedFittings) || 0
  const arrivedKm = Number(sec.arrivedKm) || 0
  const arrivedFittings = Number(sec.arrivedFittings) || 0
  return shippedKm > 0 || shippedFittings > 0 || arrivedKm > 0 || arrivedFittings > 0
}

// 判断指定连线是否属于实际发生发货的活跃通道
function isLineShipped(line) {
  if (!line) return false
  // 实时战报发货播报或临时激光粒子激活
  if (activeShipmentLineIds.value.has(line.id)) return true
  if (isAnimationRunning.value && activeEventCategory.value === 'dispatch' && activeSupplierId.value && activeSectionId.value) {
    if (line.fromId === activeSupplierId.value && line.toId === 'sec_' + activeSectionId.value) {
      return true
    }
  }
  return isSectionShipped(line.secId || line.toId)
}

// 获取指定连线的主材质色彩类型 ('pipe' | 'fitting')
function getLineMaterialType(line) {
  if (activeMaterialType.value) return activeMaterialType.value
  if (!line) return 'pipe'
  const cleanId = String(line.secId || line.toId || '').replace(/^sec_/, '')
  const sec = sectionProgressList.value.find(s => s.id === cleanId)
  if (!sec) return 'pipe'
  const shippedKm = Number(sec.shippedKm) || 0
  const shippedFittings = Number(sec.shippedFittings) || 0
  if (shippedKm > 0) return 'pipe'
  if (shippedFittings > 0) return 'fitting'
  return 'pipe'
}

function getSupplierStats(sup) {
  const assigned = sup.assigned_section_ids || []
  const matched = sectionProgressList.value.filter(s => assigned.includes(s.id))
  if (matched.length === 0) {
    return {
      designKm: '0.00',
      shippedKm: '0.00',
      pipePercent: 0,
      totalFittings: 0,
      shippedFittings: 0,
      fittingPercent: 0
    }
  }
  const designKm = matched.reduce((acc, s) => acc + (Number(s.designKm) || 0), 0)
  const shippedKm = matched.reduce((acc, s) => acc + (Number(s.shippedKm) || 0), 0)
  const totalFittings = matched.reduce((acc, s) => acc + (Number(s.totalFittings) || 0), 0)
  const shippedFittings = matched.reduce((acc, s) => acc + (Number(s.shippedFittings) || 0), 0)
  const pipePercent = designKm > 0 ? Number(((shippedKm / designKm) * 100).toFixed(1)) : 0
  const fittingPercent = totalFittings > 0 ? Number(((shippedFittings / totalFittings) * 100).toFixed(1)) : 0

  return {
    designKm: designKm.toFixed(2),
    shippedKm: shippedKm.toFixed(2),
    pipePercent: Math.min(pipePercent, 100),
    totalFittings,
    shippedFittings,
    fittingPercent: Math.min(fittingPercent, 100)
  }
}

const hoveredFeedItem = ref(null)

// 响应式解析当前驱动全屏拓扑的焦点事件（用户鼠标悬停战报卡片优先，默认锁定实时战报第一条最新情报）
const activeEvent = computed(() => {
  if (hoveredFeedItem.value) return hoveredFeedItem.value
  if (filteredFeedList.value && filteredFeedList.value.length > 0) return filteredFeedList.value[0]
  if (liveFeedList.value && liveFeedList.value.length > 0) return liveFeedList.value[0]
  return null
})

// 解析当前焦点事件的供给方 ID（仅发货类事件关联具体发运供给方）
const activeSupplierId = computed(() => {
  if (!activeEvent.value) return null
  const ev = activeEvent.value
  const cat = ev.category_key || ev.category || ''
  if (cat === 'dispatch' || cat === '厂家发货') {
    if (ev.supplier_id) {
      const sup = supplyNodes.value.find(s => s.id === ev.supplier_id || s.raw_id === ev.supplier_id || s.name === ev.supplier_id)
      if (sup) return sup.id
    }
    const sup = supplyNodes.value.find(s => s.name === ev.supplier || (ev.supplier && ev.supplier.includes(s.name)) || s.raw_id === ev.supplier)
    return sup ? sup.id : (supplyNodes.value[0]?.id || null)
  }
  return null
})

// 解析当前焦点事件的标段 ID
const activeSectionId = computed(() => {
  if (!activeEvent.value) return null
  const ev = activeEvent.value
  if (ev.section_id) {
    const sec = sectionProgressList.value.find(s => s.id === ev.section_id || s.code === ev.section_id)
    if (sec) return sec.id
  }
  const sec = sectionProgressList.value.find(s => s.name === ev.target || (ev.target && ev.target.includes(s.name)) || s.id === ev.target)
  return sec ? sec.id : null
})

// 解析当前焦点事件的业务大类 (dispatch | arrival | usage | plan)
const activeEventCategory = computed(() => {
  if (!activeEvent.value) return null
  const ev = activeEvent.value
  const cat = ev.category_key || ev.category || ''
  if (cat === 'dispatch' || cat === '厂家发货') return 'dispatch'
  if (['arrival', 'receive', 'warehouse', '确认到货', '施工单位收货', '库管核销', '库管确认', '库管已确认'].includes(cat)) return 'arrival'
  if (cat === 'usage' || cat === '施工量确认') return 'usage'
  if (cat === 'plan' || cat === '需求量申报') return 'plan'
  return 'other'
})

// 解析当前焦点事件的物料类型 (pipe | fitting)
const activeMaterialType = computed(() => {
  return activeEvent.value?.type || 'pipe'
})

// 解析战报事件卡片左侧动作/来源摘要（右侧统一固定对齐标段名称）
function getFeedSourceOrAction(feed) {
  if (!feed) return ''
  if (feed.category_key === 'dispatch' || feed.category === '厂家发货') {
    return feed.supplier || '管厂调度发运'
  }
  if (feed.category_key === 'arrival' || feed.category === '确认到货') {
    return feed.type === 'fitting' ? '管件进场到货' : '车辆进场到货'
  }
  if (feed.category_key === 'receive' || feed.category === '施工单位收货') {
    return feed.type === 'fitting' ? '施工接收管件' : '施工实物收货'
  }
  if (feed.category_key === 'warehouse' || feed.category === '库管核销' || feed.category === '库管确认' || feed.category === '库管已确认') {
    return feed.type === 'fitting' ? '管件库管已确认' : '库管已确认'
  }
  if (feed.category_key === 'usage' || feed.category === '施工量确认') {
    return '现场施工安装'
  }
  if (feed.category_key === 'plan' || feed.category === '需求量申报') {
    if (feed.headline && feed.headline.includes('申报') && feed.headline.includes('要料')) {
      const parts = feed.headline.split(/[──►·|]/)
      return parts[0].trim()
    }
    return '申报滚动要料'
  }
  if (feed.headline) {
    const parts = feed.headline.split(/[──►·|]/)
    return parts[0].replace(/【.*?】/g, '').trim()
  }
  return feed.supplier || '业务办理'
}

// --- 动效生命周期与间隔律动管理（5 秒高亮展示 -> 5 秒静息恢复 -> 循环执行，新动态产生即刻重置）---
const ANIMATION_ACTIVE_DURATION = 5000 // 5 秒动效高亮展示期
const ANIMATION_REST_DURATION = 5000   // 5 秒静息恢复期
const isAnimationCycleActive = ref(true)
let animationCycleTimeout = null

// 计算当前是否处于有效动效激活状态（若用户鼠标正在悬停某战报项，则保持常亮；否则跟随 5s/5s 周期律动）
const isAnimationRunning = computed(() => {
  if (hoveredFeedItem.value) return true
  return isAnimationCycleActive.value
})

function startAnimationLoop() {
  if (animationCycleTimeout) clearTimeout(animationCycleTimeout)
  isAnimationCycleActive.value = true

  const activeDurationMs = Math.max(1, Number(bsConfig.animation_active_duration_sec) || 5) * 1000
  const restDurationMs = Math.max(0, bsConfig.animation_rest_duration_sec !== undefined ? Number(bsConfig.animation_rest_duration_sec) : 5) * 1000

  // 动效展示期结束，进入静息期
  animationCycleTimeout = setTimeout(() => {
    isAnimationCycleActive.value = false

    // 静息期结束，再次循环进入展示期
    animationCycleTimeout = setTimeout(() => {
      startAnimationLoop()
    }, restDurationMs)
  }, activeDurationMs)
}

function isLineVisible(line) {
  // 1. 鼠标手动悬停管厂或标段时临时显现专供直达线路
  if (hoveredSupplierId.value && line.fromId === hoveredSupplierId.value) return true
  if (hoveredSectionId.value && line.toId === 'sec_' + hoveredSectionId.value) return true

  // 2. 当前焦点事件是“厂家发货”且处于 5 秒高亮动效周期内时，点亮对应供给方至标段的专属连线
  if (isAnimationRunning.value && activeEventCategory.value === 'dispatch' && activeSupplierId.value && activeSectionId.value) {
    if (line.fromId === activeSupplierId.value && line.toId === 'sec_' + activeSectionId.value) {
      return true
    }
  }

  // 3. 有临时触发的激光粒子运输时显现
  if (activeShipmentLineIds.value.has(line.id)) return true
  return false
}

// --- 🏆 本周战报（连续 7 日保温管 vs 管件 施工使用态势 10秒自动交替轮播） ---
const activeWeeklyTab = ref('pipe') // 'pipe' | 'fitting'
const isWeeklyRotating = ref(true)
const isWeeklyHovered = ref(false)
const weeklyRotationSeconds = 10
let weeklyRotationTimer = null

const weeklyReport = ref({
  date_range_str: '近7日',
  total_shipped_km: 0.0,
  total_shipped_m: 0,
  total_usage_km: 0.0,
  total_usage_m: 0,
  days: []
})

const weeklyFittingReport = ref({
  date_range_str: '近7日',
  total_shipped_pcs: 0,
  total_usage_pcs: 0,
  days: []
})

function formatWeeklyKm(value) {
  const amount = Number(value) || 0
  return amount.toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  })
}

function formatWeeklyInt(value) {
  const amount = Math.round(Number(value) || 0)
  return amount.toLocaleString('zh-CN')
}

const weeklyCountdownSec = ref(10)
let weeklyCountdownTimer = null
const isWeeklySwitching = ref(false)

function triggerWeeklySwitch(tabKey) {
  if (activeWeeklyTab.value === tabKey && isWeeklySwitching.value) return
  isWeeklySwitching.value = true
  activeWeeklyTab.value = tabKey
  setTimeout(() => {
    isWeeklySwitching.value = false
  }, 450)
}

function startWeeklyRotation() {
  if (weeklyCountdownTimer) clearInterval(weeklyCountdownTimer)
  const initialSec = Math.max(3, Number(bsConfig.weekly_rotation_interval_sec) || 10)
  weeklyCountdownSec.value = initialSec

  weeklyCountdownTimer = setInterval(() => {
    if (isWeeklyHovered.value || !isWeeklyRotating.value) {
      // 鼠标悬停时暂停倒计时
      return
    }
    if (weeklyCountdownSec.value > 1) {
      weeklyCountdownSec.value -= 1
    } else {
      const nextSec = Math.max(3, Number(bsConfig.weekly_rotation_interval_sec) || 10)
      weeklyCountdownSec.value = nextSec
      const nextTab = activeWeeklyTab.value === 'pipe' ? 'fitting' : 'pipe'
      triggerWeeklySwitch(nextTab)
    }
  }, 1000)
}

function switchWeeklyTab(tabKey) {
  triggerWeeklySwitch(tabKey)
  startWeeklyRotation()
}

// 1. 保温管计算属性 (单位: km)
const weeklyDays = computed(() => (
  Array.isArray(weeklyReport.value?.days) ? weeklyReport.value.days : []
))
const weeklyHasBusinessData = computed(() => weeklyDays.value.some(day => (
  (Number(day?.shipped_km) || 0) > 0 || (Number(day?.usage_km) || 0) > 0
)))
// 统计期末日（对应业务基准日/昨日）发货与施工数据
const weeklyToday = computed(() => weeklyDays.value.at(-1) || {
  shipped_km: 0,
  usage_km: 0
})

function getWeeklyPeak(metricKey) {
  if (!weeklyHasBusinessData.value || weeklyDays.value.length === 0) return null
  return weeklyDays.value.reduce((peak, day) => (
    (Number(day?.[metricKey]) || 0) > (Number(peak?.[metricKey]) || 0) ? day : peak
  ), weeklyDays.value[0])
}

const weeklyShipPeakText = computed(() => {
  const peak = getWeeklyPeak('shipped_km')
  return peak && Number(peak.shipped_km) > 0
    ? `${peak.date} · ${formatWeeklyKm(peak.shipped_km)} km`
    : '—'
})
const weeklyUsagePeakText = computed(() => {
  const peak = getWeeklyPeak('usage_km')
  return peak && Number(peak.usage_km) > 0
    ? `${peak.date} · ${formatWeeklyKm(peak.usage_km)} km`
    : '—'
})
const weeklyTodayText = computed(() => (
  `${formatWeeklyKm(weeklyToday.value.shipped_km)} / ${formatWeeklyKm(weeklyToday.value.usage_km)} km`
))
const weeklyShipNote = computed(() => (
  weeklyHasBusinessData.value
    ? `昨日 ${formatWeeklyKm(weeklyToday.value.shipped_km)} km`
    : '本周暂无发货记录'
))
const weeklyUsageNote = computed(() => (
  weeklyHasBusinessData.value
    ? `昨日 ${formatWeeklyKm(weeklyToday.value.usage_km)} km`
    : '本周暂无施工记录'
))

// 2. 管件计算属性 (单位: 件)
const weeklyFitDays = computed(() => (
  Array.isArray(weeklyFittingReport.value?.days) ? weeklyFittingReport.value.days : []
))
const weeklyFitHasBusinessData = computed(() => weeklyFitDays.value.some(day => (
  (Number(day?.shipped_pcs) || 0) > 0 || (Number(day?.usage_pcs) || 0) > 0
)))
// 统计期末日（对应业务基准日/昨日）发运与安装数据
const weeklyFitToday = computed(() => weeklyFitDays.value.at(-1) || {
  shipped_pcs: 0,
  usage_pcs: 0
})

function getWeeklyFitPeak(metricKey) {
  if (!weeklyFitHasBusinessData.value || weeklyFitDays.value.length === 0) return null
  return weeklyFitDays.value.reduce((peak, day) => (
    (Number(day?.[metricKey]) || 0) > (Number(peak?.[metricKey]) || 0) ? day : peak
  ), weeklyFitDays.value[0])
}

const weeklyFitShipPeakText = computed(() => {
  const peak = getWeeklyFitPeak('shipped_pcs')
  return peak && Number(peak.shipped_pcs) > 0
    ? `${peak.date} · ${formatWeeklyInt(peak.shipped_pcs)} 件`
    : '—'
})
const weeklyFitUsagePeakText = computed(() => {
  const peak = getWeeklyFitPeak('usage_pcs')
  return peak && Number(peak.usage_pcs) > 0
    ? `${peak.date} · ${formatWeeklyInt(peak.usage_pcs)} 件`
    : '—'
})
const weeklyFitTodayText = computed(() => (
  `${formatWeeklyInt(weeklyFitToday.value.shipped_pcs)} / ${formatWeeklyInt(weeklyFitToday.value.usage_pcs)} 件`
))
const weeklyFitShipNote = computed(() => (
  weeklyFitHasBusinessData.value
    ? `昨日 ${formatWeeklyInt(weeklyFitToday.value.shipped_pcs)} 件`
    : '本周暂无发运记录'
))
const weeklyFitUsageNote = computed(() => (
  weeklyFitHasBusinessData.value
    ? `昨日 ${formatWeeklyInt(weeklyFitToday.value.usage_pcs)} 件`
    : '本周暂无安装记录'
))

// 3. 当前展示状态的复合计算
const currentWeeklyDateRange = computed(() => (
  activeWeeklyTab.value === 'pipe'
    ? (weeklyReport.value?.date_range_str || '近7日')
    : (weeklyFittingReport.value?.date_range_str || '近7日')
))
const currentWeeklyHasBusinessData = computed(() => (
  activeWeeklyTab.value === 'pipe' ? weeklyHasBusinessData.value : weeklyFitHasBusinessData.value
))

// --- 🏆 本周战报 ECharts 专业工业大屏双轨图表 ---
const weeklyChartRef = ref(null)
let weeklyChartInstance = null
let chartResizeObserver = null

function renderWeeklyChart() {
  try {
    if (!weeklyChartRef.value) return
    if (!weeklyChartInstance) {
      weeklyChartInstance = echarts.init(weeklyChartRef.value)
      if (window.ResizeObserver) {
        chartResizeObserver = new ResizeObserver(() => {
          handleResizeWeeklyChart()
        })
        chartResizeObserver.observe(weeklyChartRef.value)
      }
    }

    const isLight = currentTheme.value === 'light'
    const isPipe = activeWeeklyTab.value === 'pipe'

    const days = isPipe ? (weeklyReport.value?.days || []) : (weeklyFittingReport.value?.days || [])
    const xLabels = days.map(d => `${d.date}\n${d.day_name}`)
    const series1Data = days.map(d => isPipe ? (Number(d.shipped_km) || 0) : (Number(d.shipped_pcs) || 0))
    const series2Data = days.map(d => isPipe ? (Number(d.usage_km) || 0) : (Number(d.usage_pcs) || 0))

    const series1Name = isPipe ? '发货量' : '发运量'
    const series2Name = isPipe ? '施工量' : '安装量'
    const unitStr = isPipe ? 'km' : '件'

    const textColor = isLight ? '#64748b' : '#94a3b8'
    const splitLineColor = isLight ? 'rgba(203, 213, 225, 0.6)' : 'rgba(255, 255, 255, 0.08)'

    const series1Color = isLight ? '#0284c7' : '#00f2fe'
    const series2Color = isPipe
      ? (isLight ? '#059669' : '#34d399')
      : (isLight ? '#d97706' : '#fbbf24')

    const option = {
      animation: true,
      animationDuration: 500,
      animationDurationUpdate: 650,
      animationEasing: 'cubicOut',
      animationEasingUpdate: 'cubicOut',
      tooltip: {
        trigger: 'axis',
        backgroundColor: isLight ? 'rgba(255, 255, 255, 0.98)' : 'rgba(10, 20, 38, 0.96)',
        borderColor: isLight ? '#cbd5e1' : (isPipe ? 'rgba(52, 211, 153, 0.4)' : 'rgba(251, 191, 36, 0.4)'),
        borderWidth: 1,
        padding: [8, 12],
        textStyle: {
          color: isLight ? '#0f172a' : '#f1f5f9',
          fontSize: 11
        },
        axisPointer: {
          type: 'line',
          lineStyle: {
            color: isLight ? 'rgba(2, 132, 199, 0.4)' : (isPipe ? 'rgba(52, 211, 153, 0.6)' : 'rgba(251, 191, 36, 0.6)'),
            type: 'dashed',
            width: 1.2
          }
        },
        formatter: function(params) {
          if (!params || params.length === 0) return ''
          const dayObj = days[params[0].dataIndex] || {}
          let html = `<div style="font-weight: 700; border-bottom: 1px solid ${isLight ? '#e2e8f0' : 'rgba(255,255,255,0.12)'}; padding-bottom: 4px; margin-bottom: 6px;">📅 ${dayObj.full_date || ''} (${dayObj.day_name || ''})</div>`
          params.forEach(p => {
            const isS1 = p.seriesName === series1Name
            const color = isS1 ? series1Color : series2Color
            const valDisplay = isPipe ? `${p.value} km` : `${p.value} 件`
            html += `<div style="display: flex; align-items: center; justify-content: space-between; gap: 14px; font-size: 11px; line-height: 1.6;">
              <span style="color: ${textColor}; display: flex; align-items: center; gap: 4px;">${p.marker} ${p.seriesName}:</span>
              <strong style="color: ${color}; font-family: 'JetBrains Mono', monospace;">${valDisplay}</strong>
            </div>`
          })
          return html
        }
      },
      legend: {
        top: 2,
        right: 8,
        itemWidth: 12,
        itemHeight: 3,
        itemGap: 10,
        textStyle: {
          color: isLight ? '#475569' : '#cbd5e1',
          fontSize: 10.5,
          fontWeight: 500
        },
        data: [series1Name, series2Name]
      },
      grid: {
        top: 18,
        left: 2,
        right: 12,
        bottom: 2,
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: xLabels,
        boundaryGap: false,
        axisLine: {
          lineStyle: { color: isLight ? '#cbd5e1' : 'rgba(255, 255, 255, 0.18)' }
        },
        axisTick: { show: false },
        axisLabel: {
          color: isLight ? '#475569' : '#94a3b8',
          fontSize: 10,
          interval: 0,
          lineHeight: 12,
          fontWeight: 500,
          fontFamily: 'JetBrains Mono, Consolas, sans-serif'
        }
      },
      yAxis: {
        type: 'value',
        minInterval: isPipe ? undefined : 1,
        splitLine: {
          lineStyle: {
            color: splitLineColor,
            type: 'dashed'
          }
        },
        axisLabel: {
          color: isLight ? '#64748b' : '#94a3b8',
          fontSize: 10,
          fontFamily: 'JetBrains Mono, Consolas, monospace'
        }
      },
      series: [
        {
          name: series1Name,
          type: 'line',
          smooth: 0.35,
          symbol: 'circle',
          symbolSize: 5,
          itemStyle: {
            color: series1Color,
            borderColor: isLight ? '#ffffff' : '#090e1a',
            borderWidth: 1.5
          },
          lineStyle: {
            width: 2,
            color: series1Color,
            shadowColor: isLight ? 'rgba(2, 132, 199, 0.25)' : 'rgba(0, 242, 254, 0.4)',
            shadowBlur: 6
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: isLight ? 'rgba(2, 132, 199, 0.28)' : 'rgba(0, 242, 254, 0.38)' },
                { offset: 1, color: isLight ? 'rgba(2, 132, 199, 0.0)' : 'rgba(0, 242, 254, 0.0)' }
              ]
            }
          },
          data: series1Data
        },
        {
          name: series2Name,
          type: 'line',
          smooth: 0.35,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: {
            color: series2Color,
            borderColor: isLight ? '#ffffff' : '#090e1a',
            borderWidth: 2
          },
          lineStyle: {
            width: 2.2,
            color: series2Color,
            shadowColor: isPipe
              ? (isLight ? 'rgba(5, 150, 105, 0.3)' : 'rgba(52, 211, 153, 0.4)')
              : (isLight ? 'rgba(217, 119, 6, 0.3)' : 'rgba(251, 191, 36, 0.4)'),
            shadowBlur: 8
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: isPipe ? [
                { offset: 0, color: isLight ? 'rgba(5, 150, 105, 0.24)' : 'rgba(52, 211, 153, 0.28)' },
                { offset: 1, color: isLight ? 'rgba(5, 150, 105, 0.0)' : 'rgba(52, 211, 153, 0.0)' }
              ] : [
                { offset: 0, color: isLight ? 'rgba(217, 119, 6, 0.24)' : 'rgba(251, 191, 36, 0.28)' },
                { offset: 1, color: isLight ? 'rgba(217, 119, 6, 0.0)' : 'rgba(251, 191, 36, 0.0)' }
              ]
            }
          },
          data: series2Data
        }
      ]
    }

    weeklyChartInstance.setOption(option, true)
    nextTick(() => {
      handleResizeWeeklyChart()
    })
    requestAnimationFrame(() => {
      handleResizeWeeklyChart()
    })
  } catch (e) {
    console.warn('渲染本周战报 ECharts 异常 (已安全降级):', e)
  }
}

function handleResizeWeeklyChart() {
  try {
    if (!weeklyChartInstance && weeklyChartRef.value && weeklyChartRef.value.clientWidth > 0) {
      renderWeeklyChart()
      return
    }
    if (weeklyChartInstance && weeklyChartRef.value) {
      weeklyChartInstance.resize({
        width: weeklyChartRef.value.clientWidth || 'auto',
        height: weeklyChartRef.value.clientHeight || 'auto'
      })
    }
  } catch (e) {
    // 忽略自适应异常
  }
}

watch(activeWeeklyTab, () => {
  nextTick(renderWeeklyChart)
})

watch(weeklyReport, () => {
  if (activeWeeklyTab.value === 'pipe') {
    nextTick(renderWeeklyChart)
  }
}, { deep: true })

watch(weeklyFittingReport, () => {
  if (activeWeeklyTab.value === 'fitting') {
    nextTick(renderWeeklyChart)
  }
}, { deep: true })

watch(currentTheme, () => {
  nextTick(renderWeeklyChart)
})

// --- 点击战报卡片即时在拓扑图上发射激光飞线并高亮相关节点 ---
function handleFeedClick(feed) {
  if (!feed) return
  const isDispatch = feed.category_key === 'dispatch' || feed.category === '厂家发货'
  
  let sup = null
  if (feed.supplier_id) {
    sup = supplyNodes.value.find(s => s.id === feed.supplier_id || s.raw_id === feed.supplier_id)
  }
  if (!sup) {
    sup = supplyNodes.value.find(s => s.name === feed.supplier || (feed.supplier && feed.supplier.includes(s.name)) || s.raw_id === feed.supplier)
  }

  let sec = null
  if (feed.section_id) {
    sec = sectionProgressList.value.find(s => s.id === feed.section_id || s.code === feed.section_id)
  }
  if (!sec) {
    sec = sectionProgressList.value.find(s => s.name === feed.target || (feed.target && feed.target.includes(s.name)) || s.id === feed.target)
  }

  const fromId = sup ? sup.id : (supplyNodes.value[0]?.id || 'sup_kaiyuan')
  const toId = sec ? ('sec_' + sec.id) : ('sec_' + (sectionProgressList.value[0]?.id || 'high_lot_1'))

  if (isDispatch) {
    // 1. 发货事件发射专属激光飞线并高亮供给方
    shootLaserParticle(fromId, toId, feed.type || 'pipe')
    if (sup) hoveredSupplierId.value = sup.id
  }

  // 2. 临时高亮对应标段节点
  if (sec) hoveredSectionId.value = sec.id
  setTimeout(() => {
    hoveredSupplierId.value = null
    hoveredSectionId.value = null
  }, 2500)
}

// --- 🔄 点击“实时直连”徽章立即强制同步数据库最新数据 ---
const isManualRefreshing = ref(false)
async function handleManualRefresh() {
  if (isManualRefreshing.value) return
  isManualRefreshing.value = true
  try {
    await loadRealData(true)
  } catch (err) {
    console.warn('手动同步真实数据异常:', err)
  } finally {
    setTimeout(() => {
      isManualRefreshing.value = false
    }, 700)
  }
}

// --- 切换真实数据实时流直连模式 ---
function toggleLiveStreamMode() {
  isLiveStreamMode.value = !isLiveStreamMode.value
  if (isLiveStreamMode.value) {
    // 1. 关闭沙盒自动演示
    if (autoDemoRunning.value) toggleAutoDemo()
    // 2. 立即拉取并完全对齐数据库最新全量真实数据
    loadRealData(true)
    // 3. 启动高频心跳轮询（每 3 秒检测数据库增量发货/签收动态）
    if (liveStreamTimer) clearInterval(liveStreamTimer)
    liveStreamTimer = setInterval(pollLiveRealData, 3000)

    // 4. 即刻触发实况接入动画（高亮首张卡片并向中心拓扑图发射一道连接激活飞线）
    if (liveFeedList.value && liveFeedList.value.length > 0) {
      const topFeed = liveFeedList.value[0]
      topFeed.isNew = true
      handleFeedClick(topFeed)
      setTimeout(() => {
        topFeed.isNew = false
      }, 3500)
    }
  } else {
    // 关闭实时流监听，恢复常规 20 秒静默轮询
    if (liveStreamTimer) clearInterval(liveStreamTimer)
    liveStreamTimer = null
  }
}

// --- 高频轮询并感知数据库最新产生的真实发货与累计状态 (只读安全感知) ---
async function pollLiveRealData() {
  try {
    const res = await getTubeBigScreenData(projectKey.value)
    if (!res || !res.ok) return

    // 1. 检查是否有新增真实发货单据
    if (Array.isArray(res.live_feed_list)) {
      const newArrivals = []
      res.live_feed_list.forEach(feed => {
        if (!knownFeedIds.value.has(feed.id)) {
          knownFeedIds.value.add(feed.id)
          if (initialDataLoaded) {
            newArrivals.push(feed)
          }
        }
      })

      // 如果检测到现场或管厂提交了新的真实单据
      if (newArrivals.length > 0) {
        newArrivals.forEach(feed => {
          feed.isNew = true
          // 查找匹配管厂与标段
          const sup = supplyNodes.value.find(s => s.name === feed.supplier || feed.supplier.includes(s.name) || s.raw_id === feed.supplier)
          const sec = sectionProgressList.value.find(s => s.name === feed.target || feed.target.includes(s.name) || s.id === feed.target)
          const fromId = sup ? sup.id : (supplyNodes.value[0]?.id || 'sup_kaiyuan')
          const toId = sec ? ('sec_' + sec.id) : ('sec_' + (sectionProgressList.value[0]?.id || 'high_lot_1'))

          shootLaserParticle(fromId, toId, feed.type)

          if (feed.type === 'pipe') {
            const meters = parseInt(feed.amount) || 120
            bubbles.pipeShipped = meters
            bubbles.pipeTransit = meters
          } else {
            const pcs = parseInt(feed.amount) || 2
            bubbles.fittingShipped = pcs
            bubbles.fittingTransit = pcs
          }
          setTimeout(() => {
            bubbles.pipeShipped = null
            bubbles.pipeTransit = null
            bubbles.fittingShipped = null
            bubbles.fittingTransit = null
          }, 2400)
        })

        // 更新战报列表并即刻重置启动 5 秒动效展示期
        liveFeedList.value = res.live_feed_list
        startAnimationLoop()
        setTimeout(() => {
          liveFeedList.value.forEach(f => f.isNew = false)
        }, 3500)
      } else {
        liveFeedList.value = res.live_feed_list
      }
    }

    // 2. 实时同步全网真实大盘与累计指标
    if (res.kpi) {
      kpiData.pipeDesignKm = Number(res.kpi.pipeDesignKm || 0)
      kpiData.pipeShippedKm = Number(res.kpi.pipeShippedKm || 0)
      kpiData.pipeTransitKm = Number(res.kpi.pipeTransitKm || 0)
      kpiData.pipeInstalledKm = Number(res.kpi.pipeInstalledKm || 0)
      kpiData.pipeStockKm = Number(res.kpi.pipeStockKm || 0)
      kpiData.pipeThreeDayPlanKm = Number(res.kpi.pipeThreeDayPlanKm || 0)
      kpiData.pipeThreeDayGapKm = Number(res.kpi.pipeThreeDayGapKm || 0)
      kpiData.pipeDeliveredKm = Number(res.kpi.pipeDeliveredKm || 0)
      kpiData.fittingTotalPcs = Number(res.kpi.fittingTotalPcs || 1138)
      kpiData.fittingShippedPcs = Number(res.kpi.fittingShippedPcs || 0)
      kpiData.fittingTransitPcs = Number(res.kpi.fittingTransitPcs || 0)
      kpiData.fittingInstalledPcs = Number(res.kpi.fittingInstalledPcs || 0)
      kpiData.fittingStockPcs = Number(res.kpi.fittingStockPcs !== undefined ? res.kpi.fittingStockPcs : (res.kpi.fittingArrivedPcs || 0))
      kpiData.fittingArrivedPcs = Number(res.kpi.fittingArrivedPcs || 0)
      kpiData.fittingCategoryCount = Number(res.kpi.fittingCategoryCount || 0)
      kpiData.warehouseConfirmRate = res.kpi.warehouseConfirmRate !== undefined ? Number(res.kpi.warehouseConfirmRate) : 100.0
      kpiData.avgTransitHours = res.kpi.avgTransitHours !== undefined ? Number(res.kpi.avgTransitHours) : 16.4
    }

    // 2.5 实时同步现场天气与施工环境
    if (res.live_weather && typeof res.live_weather === 'object') {
      Object.assign(liveWeatherData, res.live_weather)
    }

    // 3. 实时同步 10 大标段真实进度
    if (Array.isArray(res.section_progress_list) && res.section_progress_list.length > 0) {
      sectionProgressList.value = res.section_progress_list
    }

    // 4. 实时同步管件类型汇总
    if (Array.isArray(res.fitting_type_summary)) {
      fittingTypeSummary.value = res.fitting_type_summary
    }

    // 5. 实时同步 7 日双战报大盘
    if (res.weekly_report && typeof res.weekly_report === 'object') {
      weeklyReport.value = res.weekly_report
    }
    if (res.weekly_fitting_report && typeof res.weekly_fitting_report === 'object') {
      weeklyFittingReport.value = res.weekly_fitting_report
    }

  } catch (err) {
    console.warn('实时心跳拉取异常:', err)
  }
}

// --- 高性能规整流向几何计算 (定向直达专线，绝不产生杂乱交叉) ---
function recalculateFlylines() {
  if (rAFId) cancelAnimationFrame(rAFId)
  rAFId = requestAnimationFrame(() => {
    rAFId = null
    if (!topologyContainerRef.value) return
    const container = topologyContainerRef.value
    const containerRect = container.getBoundingClientRect()
    if (containerRect.width <= 0 || containerRect.height <= 0) return

    const scrollLeft = container.scrollLeft || 0
    const scrollTop = container.scrollTop || 0

    // 1. 批量读取港口坐标，单次回流 (含移动端滚动偏移容错)
    const supRects = new Map()
    supplyNodes.value.forEach(sup => {
      const el = document.getElementById('port-out-' + sup.id)
      if (el) {
        const r = el.getBoundingClientRect()
        supRects.set(sup.id, {
          x: r.left + r.width / 2 - containerRect.left + scrollLeft,
          y: r.top + r.height / 2 - containerRect.top + scrollTop
        })
      }
    })

    const secRects = new Map()
    sectionProgressList.value.forEach(sec => {
      const el = document.getElementById('port-in-sec_' + sec.id)
      if (el) {
        const r = el.getBoundingClientRect()
        secRects.set(sec.id, {
          x: r.left + r.width / 2 - containerRect.left + scrollLeft,
          y: r.top + r.height / 2 - containerRect.top + scrollTop
        })
      }
    })

    // 2. 批量构建规整专属定向飞线 (精准直连负责标段，不再盲目全连)
    const newFlylines = []
    supplyNodes.value.forEach((sup, sIdx) => {
      const p1 = supRects.get(sup.id)
      if (!p1) return
      const assignedIds = sup.assigned_section_ids || []

      sectionProgressList.value.forEach((sec) => {
        // 仅在属于当前激活 Tab 且符合真实责任划分时绘制管道
        const inActiveTab = activeSectionTab.value === 'all' || activeSectionTab.value === sec.system_type
        const isMatched = assignedIds.includes(sec.id)

        if (inActiveTab && isMatched) {
          const p2 = secRects.get(sec.id)
          if (p2) {
            const dx = Math.max(Math.abs(p2.x - p1.x), 40)
            const cx1 = p1.x + dx * 0.45
            const cy1 = p1.y
            const cx2 = p2.x - dx * 0.45
            const cy2 = p2.y
            const d = `M ${p1.x} ${p1.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${p2.x} ${p2.y}`
            newFlylines.push({
              id: `flyline-${sup.id}-${sec.id}`,
              fromId: sup.id,
              toId: 'sec_' + sec.id,
              supId: sup.id,
              secId: sec.id,
              type: 'pipe',
              d
            })
          }
        }
      })
    })

    flylines.value = newFlylines
  })
}

// 触发一道激光粒子飞行动画并在途显现线路
function shootLaserParticle(fromId, toId, type = 'pipe') {
  let targetLine = flylines.value.find(l => l.fromId === fromId && l.toId === toId)
  if (!targetLine) {
    targetLine = flylines.value.find(l => l.toId === toId)
  }
  if (!targetLine) {
    targetLine = flylines.value.find(l => l.fromId === fromId)
  }
  if (!targetLine) {
    targetLine = flylines.value[0]
  }
  if (!targetLine) return

  const particleId = 'p_' + Date.now() + '_' + Math.floor(Math.random() * 1000)
  const duration = Math.max(0.5, Number(bsConfig.flyline_travel_sec) || 1.8)

  // 1. 点亮显现在途运输线路（使用确切 targetLine 的端点，确保线路与发光节点100%对齐）
  activeShipmentLineIds.value.add(targetLine.id)
  activeNodeIds.value.add(targetLine.fromId)
  activeNodeIds.value.add(targetLine.toId)

  activeParticles.value.push({
    id: particleId,
    d: targetLine.d,
    type,
    duration
  })

  // 2. 激光粒子到达后移除粒子与高亮
  setTimeout(() => {
    activeParticles.value = activeParticles.value.filter(p => p.id !== particleId)
    activeNodeIds.value.delete(targetLine.fromId)
    activeNodeIds.value.delete(targetLine.toId)
  }, duration * 1000 + 100)

  // 3. 在途运输持续 4.0 秒后线路平滑隐去
  setTimeout(() => {
    activeShipmentLineIds.value.delete(targetLine.id)
  }, 4000)
}

// --- 核心业务：触发发货与现场业务事件（支持真实数据或沙盒演示模拟）---
function triggerSimulateDelivery(mode = 'pipe') {
  // 手动模拟或演示时自动退出实况模式
  if (isLiveStreamMode.value) {
    toggleLiveStreamMode()
  }

  const timeNow = new Date().toTimeString().split(' ')[0].slice(0, 5)
  const validSuppliers = supplyNodes.value.length > 0 ? supplyNodes.value : defaultSupplyNodes

  // 1. 严格从当前供给方中选取管厂与可供标段
  const chosenSup = validSuppliers[Math.floor(Math.random() * validSuppliers.length)]
  const supNodeId = chosenSup.id
  const supName = chosenSup.name
  const assignedSectionIds = (chosenSup.assigned_section_ids && chosenSup.assigned_section_ids.length > 0)
    ? chosenSup.assigned_section_ids
    : ['high_lot_1', 'high_lot_2']

  // 严格选取管厂负责的标段，确保物理拓扑飞线 100% 存在且与标段卡片完全一致
  const chosenSecId = assignedSectionIds[Math.floor(Math.random() * assignedSectionIds.length)]
  const secTarget = sectionProgressList.value.find(s => s.id === chosenSecId) || sectionProgressList.value[0]
  const secNodeId = 'sec_' + secTarget.id
  const secName = secTarget.name

  const eventId = 'sim_' + Date.now() + '_' + Math.floor(Math.random() * 1000)

  // 2. 决定事件类别与物料类型
  let categoryKey = 'dispatch'
  let categoryName = '厂家发货'
  let matType = (mode === 'fitting') ? 'fitting' : 'pipe'

  if (mode === 'auto') {
    const roll = Math.random()
    if (roll < 0.50) {
      categoryKey = 'dispatch'
      categoryName = '厂家发货'
      matType = Math.random() > 0.45 ? 'pipe' : 'fitting'
    } else if (roll < 0.70) {
      categoryKey = 'arrival'
      categoryName = '确认到货'
      matType = Math.random() > 0.5 ? 'pipe' : 'fitting'
    } else if (roll < 0.82) {
      categoryKey = 'receive'
      categoryName = '施工单位收货'
      matType = Math.random() > 0.5 ? 'pipe' : 'fitting'
    } else if (roll < 0.92) {
      categoryKey = 'warehouse'
      categoryName = '库管确认'
      matType = Math.random() > 0.5 ? 'pipe' : 'fitting'
    } else {
      categoryKey = 'usage'
      categoryName = '施工量确认'
      matType = 'pipe'
    }
  }

  // 3. 构造完整规范的战报实体并联动指标
  let newFeed = null

  if (categoryKey === 'dispatch') {
    if (matType === 'pipe') {
      const models = rawPipeModels.length > 0 ? rawPipeModels : ['DN600', 'DN800', 'DN1000', 'DN1200', 'DN500']
      const model = models[Math.floor(Math.random() * models.length)]
      const meters = [120, 240, 360, 480][Math.floor(Math.random() * 4)]
      const kmDelta = Math.round((meters / 1000) * 100) / 100

      newFeed = {
        id: eventId,
        category: '厂家发货',
        category_key: 'dispatch',
        type: 'pipe',
        supplier_id: chosenSup.id,
        section_id: secTarget.id,
        supplier: supName,
        target: secName,
        headline: `${supName} ──► ${secName}`,
        specification: `${model} 预制直埋保温管`,
        amount: `${meters} 米`,
        shipmentCode: 'DL-P-' + Math.floor(1000 + Math.random() * 9000),
        vehiclePlate: '辽B·' + Math.floor(1000 + Math.random() * 9000),
        operator: '管厂调度发运',
        time: timeNow,
        positiveTag: `保温管专车直达标段 +${meters}米 🚀`,
        isNew: true
      }

      kpiData.pipeShippedKm = Math.round((kpiData.pipeShippedKm + kmDelta) * 100) / 100
      kpiData.pipeTransitKm = Math.round((kpiData.pipeTransitKm + kmDelta) * 100) / 100
      secTarget.shippedKm = Math.round(((Number(secTarget.shippedKm) || 0) + kmDelta) * 100) / 100
      secTarget.transitKm = Math.round(((Number(secTarget.transitKm) || 0) + kmDelta) * 100) / 100
      if (secTarget.designKm > 0) {
        secTarget.pipePercent = Math.min(Math.round((secTarget.shippedKm / secTarget.designKm) * 1000) / 10, 100)
        secTarget.transitPercent = Math.min(Math.round((secTarget.transitKm / secTarget.designKm) * 1000) / 10, 100)
      }

      bubbles.pipeShipped = meters
      bubbles.pipeTransit = meters
      setTimeout(() => { bubbles.pipeShipped = null; bubbles.pipeTransit = null }, 2400)

    } else {
      // 管件发货
      const fittings = ['90°大口径弯头', '同心变径管', '异径三通', '直埋波纹补偿器', '直埋焊接球阀']
      const fittingName = fittings[Math.floor(Math.random() * fittings.length)]
      const pcs = [2, 4, 6, 8, 12][Math.floor(Math.random() * 5)]

      newFeed = {
        id: eventId,
        category: '厂家发货',
        category_key: 'dispatch',
        type: 'fitting',
        supplier_id: chosenSup.id,
        section_id: secTarget.id,
        supplier: supName,
        target: secName,
        headline: `${supName} ──► ${secName}`,
        specification: fittingName,
        amount: `${pcs} 件套`,
        shipmentCode: 'FT-SH-' + Math.floor(1000 + Math.random() * 9000),
        vehiclePlate: '冀B·' + Math.floor(1000 + Math.random() * 9000),
        operator: '管厂调度发运',
        time: timeNow,
        positiveTag: `关键配件专车直达 +${pcs}件 ✨`,
        isNew: true
      }

      kpiData.fittingShippedPcs += pcs
      kpiData.fittingTransitPcs += pcs
      secTarget.shippedFittings = (Number(secTarget.shippedFittings) || 0) + pcs
      secTarget.transitFittings = (Number(secTarget.transitFittings) || 0) + pcs
      if (secTarget.totalFittings > 0) {
        secTarget.fittingPercent = Math.min(Math.round((secTarget.shippedFittings / secTarget.totalFittings) * 1000) / 10, 100)
        secTarget.transitFittingPercent = Math.min(Math.round((secTarget.transitFittings / secTarget.totalFittings) * 1000) / 10, 100)
      }

      bubbles.fittingShipped = pcs
      bubbles.fittingTransit = pcs
      setTimeout(() => { bubbles.fittingShipped = null; bubbles.fittingTransit = null }, 2400)
    }

  } else if (categoryKey === 'arrival') {
    const meters = [120, 240, 360][Math.floor(Math.random() * 3)]
    const kmDelta = Math.round((meters / 1000) * 100) / 100

    newFeed = {
      id: eventId,
      category: '确认到货',
      category_key: 'arrival',
      type: matType,
      supplier_id: chosenSup.id,
      section_id: secTarget.id,
      supplier: supName,
      target: secName,
      headline: matType === 'fitting' ? `管件进场到货 · ${secName}` : `车辆进场到货 · ${secName}`,
      specification: matType === 'pipe' ? 'DN800 预制直埋保温管' : '90°大口径弯头 DN800',
      amount: matType === 'pipe' ? `${meters} 米` : `4 件套`,
      shipmentCode: 'ARR-' + Math.floor(1000 + Math.random() * 9000),
      vehiclePlate: '辽B·' + Math.floor(1000 + Math.random() * 9000),
      operator: '现场负责人',
      time: timeNow,
      positiveTag: matType === 'fitting' ? '关键管件专车已进场完成核验' : '车辆已进场完成到货核验',
      isNew: true
    }

    if (matType === 'pipe') {
      kpiData.pipeDeliveredKm = Math.round((kpiData.pipeDeliveredKm + kmDelta) * 100) / 100
      kpiData.pipeTransitKm = Math.max(0, Math.round((kpiData.pipeTransitKm - kmDelta) * 100) / 100)
      kpiData.pipeStockKm = Math.round((kpiData.pipeStockKm + kmDelta) * 100) / 100
      kpiData.pipeThreeDayGapKm = Math.max(0, Math.round(((kpiData.pipeThreeDayPlanKm || 0) - kpiData.pipeStockKm) * 100) / 100)
      secTarget.arrivedKm = Math.round(((Number(secTarget.arrivedKm) || 0) + kmDelta) * 100) / 100
      secTarget.transitKm = Math.max(0, Math.round(((Number(secTarget.transitKm) || 0) - kmDelta) * 100) / 100)
      if (secTarget.designKm > 0) {
        secTarget.arrivedPercent = Math.min(Math.round((secTarget.arrivedKm / secTarget.designKm) * 1000) / 10, 100)
        secTarget.transitPercent = Math.min(Math.round((secTarget.transitKm / secTarget.designKm) * 1000) / 10, 100)
      }
    } else {
      kpiData.fittingArrivedPcs += 4
      kpiData.fittingTransitPcs = Math.max(0, kpiData.fittingTransitPcs - 4)
      secTarget.arrivedFittings = (Number(secTarget.arrivedFittings) || 0) + 4
      secTarget.transitFittings = Math.max(0, (Number(secTarget.transitFittings) || 0) - 4)
      if (secTarget.totalFittings > 0) {
        secTarget.arrivedFittingPercent = Math.min(Math.round((secTarget.arrivedFittings / secTarget.totalFittings) * 1000) / 10, 100)
        secTarget.transitFittingPercent = Math.min(Math.round((secTarget.transitFittings / secTarget.totalFittings) * 1000) / 10, 100)
      }
    }

  } else if (categoryKey === 'receive') {
    newFeed = {
      id: eventId,
      category: '施工单位收货',
      category_key: 'receive',
      type: matType,
      supplier_id: chosenSup.id,
      section_id: secTarget.id,
      supplier: supName,
      target: secName,
      headline: matType === 'fitting' ? `施工接收管件 · ${secName}` : `施工实物收货 · ${secName}`,
      specification: matType === 'fitting' ? '90°大口径弯头 DN800' : 'DN800 预制直埋保温管',
      amount: matType === 'fitting' ? '4 件套' : '240 米',
      shipmentCode: 'REC-' + Math.floor(1000 + Math.random() * 9000),
      vehiclePlate: '辽B·' + Math.floor(1000 + Math.random() * 9000),
      operator: '现场施工接收员',
      time: timeNow,
      positiveTag: matType === 'fitting' ? '施工队完成特种管件核验签收' : '施工队完成实物卸车接收',
      isNew: true
    }

  } else if (categoryKey === 'warehouse') {
    newFeed = {
      id: eventId,
      category: '库管确认',
      category_key: 'warehouse',
      type: matType,
      supplier_id: chosenSup.id,
      section_id: secTarget.id,
      supplier: supName,
      target: secName,
      headline: matType === 'fitting' ? `管件库管已确认 · ${secName}` : `库管已确认 · ${secName}`,
      specification: matType === 'fitting' ? '90°大口径弯头 DN800' : 'DN800 预制直埋保温管',
      amount: matType === 'fitting' ? '4 件套' : '240 米',
      shipmentCode: 'WH-' + Math.floor(1000 + Math.random() * 9000),
      vehiclePlate: '辽B·' + Math.floor(1000 + Math.random() * 9000),
      operator: '专职库管员',
      time: timeNow,
      positiveTag: matType === 'fitting' ? '管件实物核验无误，库管确认完成' : '实测核验无误，库管确认完成',
      isNew: true
    }

  } else if (categoryKey === 'usage') {
    const meters = [60, 120, 180][Math.floor(Math.random() * 3)]
    const kmDelta = Math.round((meters / 1000) * 100) / 100

    newFeed = {
      id: eventId,
      category: '施工量确认',
      category_key: 'usage',
      type: 'pipe',
      supplier_id: null,
      section_id: secTarget.id,
      supplier: '施工现场班组',
      target: secName,
      headline: `现场施工安装 · ${secName}`,
      specification: 'DN800 预制直埋保温管',
      amount: `铺设安装 ${meters} 米`,
      shipmentCode: 'SG-' + Math.floor(1000 + Math.random() * 9000),
      vehiclePlate: '工区现场铺设',
      operator: '现场施工负责人',
      time: timeNow,
      positiveTag: '完成管网下沟敷设，记录已确认',
      isNew: true
    }

    kpiData.pipeInstalledKm = Math.round((kpiData.pipeInstalledKm + kmDelta) * 100) / 100
    kpiData.pipeStockKm = Math.max(0, Math.round((kpiData.pipeStockKm - kmDelta) * 100) / 100)
    kpiData.pipeThreeDayGapKm = Math.max(0, Math.round(((kpiData.pipeThreeDayPlanKm || 0) - kpiData.pipeStockKm) * 100) / 100)
    secTarget.installedKm = Math.round(((parseFloat(secTarget.installedKm) || 0) + kmDelta) * 100) / 100
    if (secTarget.designKm > 0) {
      secTarget.installedPercent = Math.min(Math.round((secTarget.installedKm / secTarget.designKm) * 1000) / 10, 100)
    }
  }

  // 4. 将新战报排在最前，并允许持续累积记录（最高保留 100 条流水）
  if (newFeed) {
    liveFeedList.value.unshift(newFeed)
    if (liveFeedList.value.length > 100) liveFeedList.value = liveFeedList.value.slice(0, 100)
    lastImpactedSectionId.value = secTarget.id

    // 立即启动 5 秒周期动效联动
    startAnimationLoop()

    setTimeout(() => {
      newFeed.isNew = false
    }, 3500)
  }
}

// --- 沙盒演示自动轮播控制（每 8 秒触发一次新动态）---
const AUTO_DEMO_INTERVAL = 8000

function toggleAutoDemo() {
  autoDemoRunning.value = !autoDemoRunning.value
  if (autoDemoRunning.value) {
    // 1. 开启演示模式时，自动退出并断开实况模式
    if (isLiveStreamMode.value) {
      toggleLiveStreamMode()
    }
    triggerSimulateDelivery('auto')
    if (autoDemoTimer) clearInterval(autoDemoTimer)
    autoDemoTimer = setInterval(() => {
      triggerSimulateDelivery('auto')
    }, AUTO_DEMO_INTERVAL)
  } else {
    if (autoDemoTimer) clearInterval(autoDemoTimer)
    autoDemoTimer = null
  }
}

// 全屏切换
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    if (containerRef.value?.requestFullscreen) {
      containerRef.value.requestFullscreen()
      isFullscreen.value = true
    }
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen()
      isFullscreen.value = false
    }
  }
}

// 返回常规看板
function goBackToStandardDashboard() {
  router.push(`/projects/${encodeURIComponent(projectKey.value)}/pages/dashboard`)
}

// 格式化数字
function formatNumber(val) {
  if (val === null || val === undefined) return '0.00'
  return Number(val).toFixed(2)
}

// 时钟更新
function updateClock() {
  const d = new Date()
  const year = d.getFullYear()
  const mon = String(d.getMonth() + 1).padStart(2, '0')
  const date = String(d.getDate()).padStart(2, '0')
  const hour = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  const sec = String(d.getSeconds()).padStart(2, '0')
  const weekDay = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'][d.getDay()]
  currentTimeStr.value = `${year}-${mon}-${date} ${hour}:${min}:${sec} ${weekDay}`
}

// 加载 100% 真实项目与数据库数据 (只读感知，不写数据库)
async function loadRealData(isForce = false) {
  // 若当前正处于沙盒演示模式且非手动强制刷新，则跳过后台静默覆盖，确保演示流水持续累积沉淀
  if (autoDemoRunning.value && !isForce) {
    return
  }

  try {
    const res = await getTubeBigScreenData(projectKey.value)
    if (res && res.ok) {
      realShowDate.value = res.show_date || ''
      
      // 1. KPI 绑定
      if (res.kpi) {
        kpiData.pipeDesignKm = Number(res.kpi.pipeDesignKm || 0)
        kpiData.pipeShippedKm = Number(res.kpi.pipeShippedKm || 0)
        kpiData.pipeTransitKm = Number(res.kpi.pipeTransitKm || 0)
        kpiData.pipeInstalledKm = Number(res.kpi.pipeInstalledKm || 0)
        kpiData.pipeStockKm = Number(res.kpi.pipeStockKm || 0)
        kpiData.pipeThreeDayPlanKm = Number(res.kpi.pipeThreeDayPlanKm || 0)
        kpiData.pipeThreeDayGapKm = Number(res.kpi.pipeThreeDayGapKm || 0)
        kpiData.pipeDeliveredKm = Number(res.kpi.pipeDeliveredKm || 0)
        kpiData.fittingTotalPcs = Number(res.kpi.fittingTotalPcs || 1138)
        kpiData.fittingShippedPcs = Number(res.kpi.fittingShippedPcs || 0)
        kpiData.fittingTransitPcs = Number(res.kpi.fittingTransitPcs || 0)
        kpiData.fittingInstalledPcs = Number(res.kpi.fittingInstalledPcs || 0)
        kpiData.fittingStockPcs = Number(res.kpi.fittingStockPcs !== undefined ? res.kpi.fittingStockPcs : (res.kpi.fittingArrivedPcs || 0))
        kpiData.fittingArrivedPcs = Number(res.kpi.fittingArrivedPcs || 0)
        kpiData.fittingCategoryCount = Number(res.kpi.fittingCategoryCount || 0)
        kpiData.warehouseConfirmRate = res.kpi.warehouseConfirmRate !== undefined ? Number(res.kpi.warehouseConfirmRate) : 100.0
        kpiData.avgTransitHours = res.kpi.avgTransitHours !== undefined ? Number(res.kpi.avgTransitHours) : 16.4
      }

      // 1.5 实时同步现场天气与施工环境
      if (res.live_weather && typeof res.live_weather === 'object') {
        Object.assign(liveWeatherData, res.live_weather)
      }

      // 2. 管件真实分类统计
      if (Array.isArray(res.fitting_type_summary)) {
        fittingTypeSummary.value = res.fitting_type_summary
      }

      // 3. 真实 10 大标段健康矩阵
      if (Array.isArray(res.section_progress_list) && res.section_progress_list.length > 0) {
        sectionProgressList.value = res.section_progress_list
      }

      // 4. 真实全网动态战报流水 (100% 呈现数据库最新真实单据)
      if (Array.isArray(res.live_feed_list)) {
        liveFeedList.value = res.live_feed_list
        res.live_feed_list.forEach(f => knownFeedIds.value.add(f.id))
      }

      // 5. 真实拓扑节点 (3 大管厂)
      if (Array.isArray(res.supply_nodes)) {
        supplyNodes.value = res.supply_nodes
      }

      // 5.5. 大屏持久化运行参数绑定
      if (res.big_screen_config) {
        Object.assign(bsConfig, res.big_screen_config)
      }

      // 6. 真实 7 日双战报大盘（保温管 + 管件）
      if (res.weekly_report && typeof res.weekly_report === 'object') {
        weeklyReport.value = res.weekly_report
      }
      if (res.weekly_fitting_report && typeof res.weekly_fitting_report === 'object') {
        weeklyFittingReport.value = res.weekly_fitting_report
      }

      // 7. 保存底层字典供交互使用
      if (Array.isArray(res.supply_entities_raw)) {
        rawSupplyEntities = res.supply_entities_raw
      }
      if (Array.isArray(res.demand_entities_raw)) {
        rawDemandEntities = res.demand_entities_raw
      }
      if (Array.isArray(res.pipe_models)) {
        rawPipeModels = res.pipe_models
      }

      initialDataLoaded = true
      recalculateFlylines()
      startAnimationLoop()
    }
  } catch (err) {
    console.warn('读取真实大屏聚合数据接口异常，使用配置与内置字典:', err)
    const summary = await getTubeWorkspaceConfigSummary(projectKey.value).catch(() => null)
    if (summary) {
      configSummary.value = summary
      rawSupplyEntities = summary.supply_entities || []
      rawDemandEntities = summary.demand_entities || []
      rawPipeModels = (summary.pipe_models || []).map(m => m.pipe_model_name || m.id || m)
    }
    initialDataLoaded = true
    recalculateFlylines()
    startAnimationLoop()
  }
}

onMounted(() => {
  updateClock()
  timerClock = setInterval(updateClock, 1000)
  loadRealData()
  startAnimationLoop()

  // 记录查看展示大屏审计日志（归属于综合数据查询类）
  const sourceLabel = route.query.from ? `调度工作台 (${route.query.from})` : '数字指挥展示大屏'
  recordTubeBigScreenAccess(projectKey.value, { entry_source: sourceLabel }).catch(() => {})

  // 初始化 ECharts 本周战报图表并开启10秒自动交替轮播
  nextTick(() => {
    renderWeeklyChart()
    startWeeklyRotation()
  })

  // 监听尺寸变化自适应重算飞线 (rAF 节流)
  if (topologyContainerRef.value && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      recalculateFlylines()
      handleResizeWeeklyChart()
    })
    resizeObserver.observe(topologyContainerRef.value)
  }

  // 初始加载测量
  setTimeout(recalculateFlylines, 100)
  setTimeout(recalculateFlylines, 400)

  // 静默拉取数据库最新状态，使用配置中设定的同步周期
  const defaultIntervalMs = Math.max(5, Number(bsConfig.auto_sync_interval_sec) || 20) * 1000
  autoSyncTimer = setInterval(loadRealData, defaultIntervalMs)
  window.addEventListener('resize', recalculateFlylines, { passive: true })
  window.addEventListener('resize', handleResizeWeeklyChart, { passive: true })
  window.addEventListener('click', handleGlobalClick)
})

onBeforeUnmount(() => {
  if (timerClock) clearInterval(timerClock)
  if (autoDemoTimer) clearInterval(autoDemoTimer)
  if (autoSyncTimer) clearInterval(autoSyncTimer)
  if (liveStreamTimer) clearInterval(liveStreamTimer)
  if (weeklyRotationTimer) clearInterval(weeklyRotationTimer)
  if (weeklyCountdownTimer) clearInterval(weeklyCountdownTimer)
  if (animationCycleTimeout) clearTimeout(animationCycleTimeout)
  if (resizeObserver) resizeObserver.disconnect()
  if (chartResizeObserver) chartResizeObserver.disconnect()
  if (rAFId) cancelAnimationFrame(rAFId)
  if (weeklyChartInstance) {
    weeklyChartInstance.dispose()
    weeklyChartInstance = null
  }
  window.removeEventListener('resize', recalculateFlylines)
  window.removeEventListener('resize', handleResizeWeeklyChart)
  window.removeEventListener('click', handleGlobalClick)
})
</script>

<style scoped>
/* ==========================================================================
   2026 预制直埋保温管智慧供应链数字指挥大屏 (工业规整立柱布局 + 生产实况实时直连)
   ========================================================================== */

/* --- 默认深色科技主题 (Dark Theme) --- */
.bigscreen-container {
  width: 100vw;
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  background: #060913;
  color: #e2e8f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji", "PingFang SC", "Microsoft YaHei", sans-serif;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  transform: translateZ(0);
}

.title-svg-globe,
.title-svg-icon,
.tab-svg-icon,
.safety-svg-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}

.weather-svg-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
  filter: drop-shadow(0 0 6px currentColor);
}

/* --- 顶栏 Header --- */
.bigscreen-header {
  height: 70px;
  min-height: 70px;
  max-height: 70px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: relative;
  background: #090e1a;
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  z-index: 1000;
}

.header-left {
  position: absolute;
  left: 24px;
  bottom: 18px;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  z-index: 10;
  line-height: 1;
}

.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 3px 10px;
  background: rgba(0, 242, 254, 0.1);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 20px;
  font-size: 12px;
  color: #00f2fe;
  transition: all 0.3s ease;
  flex-shrink: 0;
  line-height: 1.2;
}

.header-badge.live-mode {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
  color: #10b981;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00f2fe;
  box-shadow: 0 0 6px #00f2fe;
  animation: pulse-ring 2s infinite;
}

.pulse-dot.live {
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.header-time {
  font-family: 'Consolas', 'Segoe UI', monospace;
  font-size: 13px;
  color: #94a3b8;
  letter-spacing: 0.4px;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1.2;
  padding-bottom: 2px;
}

.header-title-box {
  position: absolute;
  left: calc(50% + 55px);
  bottom: 18px;
  transform: translateX(-50%);
  text-align: center;
  z-index: 5;
  white-space: nowrap;
  pointer-events: none;
  line-height: 1;
}

.header-title {
  margin: 0;
  font-size: clamp(20px, 1.7vw, 27px);
  font-weight: 800;
  letter-spacing: clamp(0.6px, 0.1vw, 1.8px);
  color: #ffffff;
  text-shadow: 0 2px 18px rgba(0, 242, 254, 0.55);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.15;
}

.title-desktop {
  display: inline;
}

.title-mobile {
  display: none;
}

.badge-desktop-prefix {
  display: inline;
}

/* 移动端专属导航选项卡 (默认在 PC 桌面端完全隐藏) */
.mobile-nav-tabs {
  display: none;
  height: 44px;
  background: #090e1a;
  border-bottom: 1px solid rgba(0, 242, 254, 0.2);
  align-items: stretch;
  justify-content: space-around;
  padding: 0 4px;
  flex-shrink: 0;
  z-index: 100;
  box-sizing: border-box;
}

.mobile-tab-btn {
  flex: 1;
  height: 100%;
  background: transparent;
  border: none;
  border-bottom: 2.5px solid transparent;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0 4px;
  position: relative;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.mobile-tab-btn .tab-icon {
  font-size: 14px;
}

.mobile-tab-btn .tab-badge {
  font-size: 10px;
  font-weight: 700;
  background: rgba(0, 242, 254, 0.2);
  color: #00f2fe;
  border: 1px solid rgba(0, 242, 254, 0.4);
  padding: 0 5px;
  border-radius: 10px;
  line-height: 1.4;
}

.mobile-tab-btn.active {
  color: #00f2fe;
  font-weight: 700;
  border-bottom-color: #00f2fe;
  background: rgba(0, 242, 254, 0.08);
}

.mobile-topo-scroll-hint {
  display: none;
  font-size: 11px;
  color: #38bdf8;
  background: rgba(0, 242, 254, 0.08);
  border: 1px dashed rgba(0, 242, 254, 0.3);
  border-radius: 6px;
  padding: 4px 8px;
  text-align: center;
  margin-bottom: 6px;
  animation: hint-shimmer 2.5s infinite ease-in-out;
}

@keyframes hint-shimmer {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.header-right {
  position: absolute;
  right: 24px;
  bottom: 18px;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  z-index: 1050;
}

.control-center-wrapper {
  position: relative;
}

/* 调度控制中心触发主按钮 */
.control-trigger-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(0, 242, 254, 0.4);
  border-radius: 20px;
  color: #00f2fe;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), inset 0 0 10px rgba(0, 242, 254, 0.1);
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.control-trigger-btn:hover,
.control-trigger-btn.active {
  background: rgba(0, 242, 254, 0.15);
  border-color: #00f2fe;
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.4);
  color: #ffffff;
}

.control-trigger-btn.live-active {
  border-color: #10b981;
  color: #10b981;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.3);
}

.control-caret {
  font-size: 10px;
  opacity: 0.7;
}

.mini-live-tag {
  font-size: 10px;
  background: rgba(16, 185, 129, 0.25);
  border: 1px solid rgba(16, 185, 129, 0.6);
  color: #10b981;
  padding: 1px 6px;
  border-radius: 8px;
}

/* 下拉菜单浮层 Popover */
.control-menu-popover {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 530px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 90px);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 242, 254, 0.4) transparent;
  background: rgba(9, 14, 26, 0.96);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 242, 254, 0.3);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 242, 254, 0.15);
  z-index: 1100;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.group-title-with-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.save-status-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
  animation: fadeIn 0.2s ease;
}

.save-status-badge.success {
  background: rgba(16, 185, 129, 0.2);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.4);
}

.save-status-badge.error {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.4);
}

.settings-form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 9px 10px;
}

.setting-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 7px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  transition: all 0.2s ease;
}

.setting-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(0, 242, 254, 0.25);
}

.setting-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.setting-name {
  font-size: 11px;
  font-weight: 600;
  color: #cbd5e1;
}

.setting-val-tag {
  font-size: 11px;
  font-weight: 700;
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
}

.setting-slider {
  width: 100%;
  height: 4px;
  accent-color: #00f2fe;
  cursor: pointer;
  margin: 3px 0;
}

.setting-hint {
  font-size: 9.5px;
  color: #64748b;
}

.settings-actions-bar {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.save-config-btn {
  flex: 1.5;
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.25), rgba(79, 172, 254, 0.35));
  border: 1px solid #00f2fe;
  color: #ffffff;
  font-weight: 700;
  padding: 7px 12px;
  justify-content: center;
}

.save-config-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.4), rgba(79, 172, 254, 0.55));
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.4);
}

.reset-config-btn {
  flex: 1;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #94a3b8;
  padding: 7px 10px;
  justify-content: center;
}

.reset-config-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
}

.save-config-btn:disabled,
.reset-config-btn:disabled,
.action-btn.disabled-permission {
  opacity: 0.45 !important;
  cursor: not-allowed !important;
  filter: grayscale(0.85);
  border-color: rgba(255, 255, 255, 0.1) !important;
  background: rgba(255, 255, 255, 0.04) !important;
  color: #64748b !important;
  box-shadow: none !important;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.popover-title {
  font-size: 13px;
  font-weight: 700;
  color: #e2e8f0;
}

.popover-close-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.popover-close-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.1);
}

.popover-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.group-title {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.5px;
}

.group-buttons-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.group-buttons-grid .action-btn {
  width: 100%;
  justify-content: center;
  padding: 7px 10px;
  font-size: 12px;
}

.popover-footer {
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.popover-footer .back-btn {
  width: 100%;
  justify-content: center;
  padding: 7px 12px;
}

/* 下拉动画 */
.control-dropdown-enter-active,
.control-dropdown-leave-active {
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}

.control-dropdown-enter-from,
.control-dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.96);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: #0f172a;
  color: #f1f5f9;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: #1e293b;
  border-color: #00f2fe;
}

/* 核心：生产实况直连按钮 */
.live-stream-btn {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.4);
  color: #10b981;
  font-weight: 600;
}

.live-stream-btn:hover {
  background: rgba(16, 185, 129, 0.25);
  border-color: #10b981;
}

.live-stream-btn.active {
  background: #10b981;
  border-color: #10b981;
  color: #04130d;
  font-weight: 700;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.5);
}

.theme-toggle-btn {
  background: rgba(0, 242, 254, 0.1);
  border-color: rgba(0, 242, 254, 0.35);
  color: #00f2fe;
}

.demo-btn {
  background: rgba(0, 242, 254, 0.12);
  border-color: rgba(0, 242, 254, 0.4);
  color: #00f2fe;
}

.demo-btn.active {
  background: rgba(59, 130, 246, 0.25);
  border-color: #3b82f6;
  color: #93c5fd;
}

.sim-btn {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
  color: #93c5fd;
}

.sim-btn.fitting {
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.4);
  color: #fde047;
}

.icon-btn {
  padding: 5px 9px;
  font-size: 14px;
}

.back-btn {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

/* --- 主内容网格 Content Layout --- */
.bigscreen-content {
  flex: 1;
  min-height: 0;
  min-width: 0;
  height: calc(100vh - 70px);
  display: grid;
  grid-template-columns: 330px 1fr 370px;
  gap: 16px;
  padding: 14px 22px 18px;
  box-sizing: border-box;
  overflow: hidden;
}

.screen-col {
  height: 100%;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  position: relative;
}

.left-col {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.left-col::-webkit-scrollbar {
  display: none;
}

/* 4 大卡片高度自适应拉伸填充整个左侧区域，零底部留白 */
.left-col .weather-kpi-panel {
  flex-shrink: 0;
  padding: 8px 12px;
}

.left-col .pipe-kpi-panel,
.left-col .fitting-kpi-panel,
.left-col .safety-panel {
  flex: 1 1 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 10px 12px;
}

.left-col .panel-header {
  margin-bottom: 6px;
  flex-shrink: 0;
}

.left-col .panel-title {
  font-size: 13.5px;
  font-weight: 700;
  gap: 6px;
}

.left-col .panel-tag {
  font-size: 11px;
  padding: 1px 6px;
}

.left-col .kpi-metric-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 6px;
}

.left-col .metric-item {
  padding: 4px 8px;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  min-height: 0;
}

.left-col .metric-label {
  font-size: 11px;
}

.left-col .metric-capsule {
  font-size: 10px;
  padding: 1px 4px;
}

.left-col .metric-val .num.hero-num {
  font-size: 19px;
  font-weight: 700;
  line-height: 1.1;
}

.left-col .metric-val .num {
  font-size: 17px;
  font-weight: 700;
  line-height: 1.1;
}

.left-col .energy-progress-box {
  margin-top: auto;
  padding-top: 3px;
  flex-shrink: 0;
}

.left-col .energy-progress-info {
  font-size: 11.5px;
  margin-bottom: 3px;
}

.left-col .energy-bar-track {
  height: 7.5px;
  border-radius: 4px;
}

.left-col .safety-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.left-col .safety-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  min-height: 0;
}

.left-col .safety-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.left-col .safety-val {
  font-size: 14px;
  font-weight: 700;
}

.left-col .safety-desc {
  font-size: 11px;
}

.left-col .weather-loc-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 7px;
}

.left-col .weather-loc-bar .loc-pin {
  font-size: 12.5px;
}

.left-col .weather-loc-bar .loc-text {
  color: #f1f5f9;
  font-weight: 600;
}

.left-col .weather-loc-bar .loc-time {
  color: #38bdf8;
  font-family: 'DIN Alternate', 'Consolas', sans-serif;
  font-size: 11.5px;
}

.left-col .weather-metrics-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(0, 242, 254, 0.16);
  border-radius: 6px;
  padding: 9px 13px;
}

.left-col .weather-temp-block {
  display: flex;
  align-items: center;
  gap: 10px;
}

.left-col .weather-emoji {
  font-size: 28px;
  line-height: 1;
  filter: drop-shadow(0 2px 5px rgba(0, 242, 254, 0.25));
}

.left-col .temp-detail {
  display: flex;
  flex-direction: column;
}

.left-col .weather-name {
  font-size: 13px;
  font-weight: 700;
  color: #ffffff;
}

.left-col .temp-degree {
  font-family: 'DIN Alternate', 'Consolas', sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: #00f2fe;
  line-height: 1.1;
}

.left-col .temp-degree small {
  font-size: 13px;
  font-weight: normal;
  color: #94a3b8;
  margin-left: 2px;
}

.left-col .weather-params-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.left-col .param-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
}

.left-col .param-k {
  color: #94a3b8;
}

.left-col .param-v {
  color: #ffffff;
  font-family: 'DIN Alternate', 'Consolas', sans-serif;
  font-weight: 700;
}

/* 同框体下方的全天预报条（居中展示） */
.left-col .weather-forecast-subrow {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 7px;
  padding-top: 7px;
  border-top: 1px dashed rgba(0, 242, 254, 0.15);
  font-size: 11.5px;
}

.left-col .weather-forecast-subrow .fc-icon {
  font-size: 12px;
}

.left-col .weather-forecast-subrow .fc-range {
  color: #fbbf24;
  font-family: 'DIN Alternate', 'Consolas', sans-serif;
  font-weight: 700;
  font-size: 12.5px;
}

.left-col .weather-forecast-subrow .fc-dot {
  color: #64748b;
}

.left-col .weather-forecast-subrow .fc-dn {
  color: #cbd5e1;
  font-weight: 600;
  font-size: 11.5px;
}

/* --- 通用卡片样式 Panel Box --- */
.panel-box {
  background: #0b1322;
  border: 1px solid rgba(0, 242, 254, 0.18);
  border-radius: 9px;
  padding: 15px 16px;
  position: relative;
  box-sizing: border-box;
}

.panel-box::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 14px;
  height: 2px;
  background: #00f2fe;
}

.panel-box::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 2px;
  height: 14px;
  background: #00f2fe;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #f8fafc;
}

.title-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  line-height: 1;
  flex-shrink: 0;
}

.panel-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.panel-tag.cyan {
  background: rgba(0, 242, 254, 0.12);
  color: #38bdf8;
  border: 1px solid rgba(0, 242, 254, 0.3);
  font-weight: 600;
}

.panel-tag.gold {
  background: rgba(251, 191, 36, 0.12);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
  font-weight: 600;
}

.panel-tag.green {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.panel-tag.danger,
.panel-tag.red {
  background: rgba(244, 63, 94, 0.15);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.35);
}

/* --- 今日天气与施工环境 (Weather KPI Panel) --- */
.weather-kpi-panel {
  padding: 8px 12px;
}

.weather-loc-bar {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.weather-loc-bar .loc-pin {
  font-size: 11.5px;
}

.weather-loc-bar .loc-text {
  color: #e2e8f0;
  font-weight: 500;
}

.weather-loc-bar .loc-dot {
  color: #64748b;
}

.weather-loc-bar .loc-time {
  color: #00f2fe;
  font-family: 'DIN Alternate', 'Consolas', sans-serif;
  font-size: 10.5px;
}

.weather-metrics-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(15, 23, 42, 0.7);
  border: 1px solid rgba(0, 242, 254, 0.12);
  border-radius: 6px;
  padding: 6px 10px;
}

.weather-temp-block {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weather-emoji {
  font-size: 22px;
  line-height: 1;
  filter: drop-shadow(0 2px 5px rgba(0, 242, 254, 0.25));
}

.temp-detail {
  display: flex;
  flex-direction: column;
}

.weather-name {
  font-size: 11.5px;
  font-weight: 600;
  color: #cbd5e1;
}

.temp-degree {
  font-family: 'DIN Alternate', 'Consolas', sans-serif;
  font-size: 19px;
  font-weight: 700;
  color: #f8fafc;
  line-height: 1.1;
}

.temp-degree small {
  font-size: 11px;
  font-weight: normal;
  color: #94a3b8;
  margin-left: 2px;
}

.weather-params-block {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.param-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
}

.param-k {
  color: #94a3b8;
}

.param-v {
  color: #e2e8f0;
  font-family: 'DIN Alternate', 'Consolas', sans-serif;
  font-weight: 600;
}

.weather-advice-banner {
  border-radius: 6px;
  padding: 7px 9px;
  font-size: 11.5px;
  line-height: 1.45;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.weather-advice-banner.advice-success {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.3);
}

.weather-advice-banner.advice-warning {
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.3);
}

.weather-advice-banner.advice-danger {
  background: rgba(244, 63, 94, 0.08);
  border-color: rgba(244, 63, 94, 0.35);
}

.advice-title-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 2px;
  font-weight: 600;
}

.advice-bulb {
  font-size: 12px;
}

.advice-label {
  font-size: 11.5px;
  color: #00f2fe;
}

.advice-text {
  color: #cbd5e1;
  font-size: 11px;
  line-height: 1.45;
}

/* --- KPI Metric Grid --- */
.kpi-metric-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.metric-item {
  background: #111c30;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
  padding: 8px 10px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-label-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  margin-bottom: 4px;
}

.metric-label {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 0;
  white-space: nowrap;
}

.metric-capsule {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
  line-height: 1.2;
  white-space: nowrap;
  letter-spacing: 0.2px;
}

.metric-capsule.cyan-capsule {
  background: rgba(0, 242, 254, 0.12);
  color: #38bdf8;
  border: 1px solid rgba(0, 242, 254, 0.3);
}

.metric-capsule.amber-capsule {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.metric-capsule.purple-capsule {
  background: rgba(168, 85, 247, 0.18);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.45);
}

.metric-capsule.red-capsule {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.5);
}

.metric-capsule.gray-capsule {
  background: rgba(148, 163, 184, 0.1);
  color: #94a3b8;
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.metric-val {
  display: flex;
  align-items: baseline;
  gap: 4px;
  position: relative;
}

.metric-val .num {
  font-size: 19px;
  font-weight: 700;
  font-family: 'DIN Alternate', 'Helvetica Neue', Arial, sans-serif;
  color: #f1f5f9;
}

.metric-val .num.hero-num {
  font-size: 22px;
  font-weight: 800;
  line-height: 1.1;
}

.metric-val .unit {
  font-size: 11px;
  color: #64748b;
}

.highlight-cyan .num {
  color: #00f2fe;
}

.highlight-amber .num {
  color: #fbbf24;
}

.highlight-green .num {
  color: #10b981;
}

.highlight-purple .num,
.purple-text {
  color: #c084fc !important;
}

.highlight-gold .num {
  color: #fbbf24;
}

.highlight-orange .num {
  color: #f97316;
}

.metric-val.dual-val {
  display: flex;
  align-items: baseline;
  flex-wrap: nowrap;
  gap: 2px;
}

.metric-val.dual-val .num {
  font-size: 15.5px;
  font-weight: 700;
}

.metric-val.dual-val .sub-num {
  font-size: 13.5px;
  font-weight: 700;
}

.metric-val.dual-val .sep {
  font-size: 12px;
  color: #64748b;
  margin: 0 1px;
}

.amber-text {
  color: #fbbf24 !important;
}

.green-text {
  color: #10b981 !important;
}

.red-text {
  color: #f43f5e !important;
}

.gray-text {
  color: #94a3b8 !important;
}

.alert-pulse {
  animation: alertTextPulse 1.6s infinite ease-in-out;
}

@keyframes alertTextPulse {
  0%, 100% { opacity: 1; transform: scale(1); text-shadow: 0 0 6px rgba(244, 63, 94, 0.6); }
  50% { opacity: 0.7; transform: scale(0.96); text-shadow: none; }
}

/* 飘字气泡 (Delta Bubble) */
.delta-bubble {
  position: absolute;
  top: -16px;
  right: 0;
  font-size: 12px;
  font-weight: 700;
  color: #00ff87;
  background: rgba(0, 255, 135, 0.2);
  padding: 1px 6px;
  border-radius: 10px;
  border: 1px solid #00ff87;
  pointer-events: none;
}

.delta-bubble.amber {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.2);
  border-color: #fbbf24;
}

.delta-bubble.gold {
  color: #fde047;
  background: rgba(253, 224, 71, 0.2);
  border-color: #fde047;
}

.delta-bubble.orange {
  color: #f97316;
  background: rgba(249, 115, 22, 0.2);
  border-color: #f97316;
}

.bubble-fade-enter-active,
.bubble-fade-leave-active {
  transition: all 0.5s ease-out;
}

.bubble-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.bubble-fade-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

/* --- 能量槽充能 Progress --- */
.energy-progress-box {
  margin-top: 4px;
}

.energy-progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: #cbd5e1;
  margin-bottom: 5px;
}

.energy-progress-info strong {
  font-size: 14px;
  font-weight: 700;
  font-family: 'DIN Alternate', 'Helvetica Neue', Arial, sans-serif;
}

.cyan-text {
  color: #00f2fe;
}

.gold-text {
  color: #fbbf24;
}

.energy-bar-track {
  width: 100%;
  height: 10px;
  background: #111c30;
  border-radius: 5px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.energy-bar-fill {
  height: 100%;
  border-radius: 5px;
  position: relative;
  transition: width 0.8s ease-out;
}

.energy-bar-fill.cyan-glow {
  background: linear-gradient(90deg, #0052d4, #00f2fe);
}

.energy-bar-fill.gold-glow {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

.energy-bar-light {
  position: absolute;
  top: 0;
  right: 0;
  width: 10px;
  height: 100%;
  background: #ffffff;
}

/* --- 管件类型 Pills --- */
.fitting-types-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.fitting-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #111c30;
  border: 1px solid rgba(251, 191, 36, 0.25);
  border-radius: 5px;
  padding: 4px 8px;
  font-size: 11px;
}

.pill-name {
  color: #cbd5e1;
}

.pill-count {
  color: #fbbf24;
  font-weight: 600;
}

/* --- 安全与效率雷达面板 --- */
.safety-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.safety-card {
  display: flex;
  align-items: center;
  gap: 9px;
  background: #111c30;
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 6px;
  padding: 8px 10px;
}

.safety-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}

.safety-val {
  font-size: 14px;
  font-weight: 700;
  color: #10b981;
}

.safety-desc {
  font-size: 10.5px;
  color: #64748b;
}

/* ==========================================================================
   中间栏：数字孪生全景拓扑中枢 (规整双立柱架构 + 在途/交互按需显现)
   ========================================================================== */

.map-topology-master-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 12px 14px;
}

.topology-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  flex-shrink: 0;
  gap: 12px;
}

.topo-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topo-sub-tag {
  font-size: 11px;
  color: #64748b;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
}

/* 系统切换 Tabs */
.system-tabs {
  display: flex;
  gap: 6px;
}

.sys-tab-btn {
  background: #111c30;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 3px 10px;
  font-size: 11px;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sys-tab-btn:hover {
  border-color: #00f2fe;
  color: #f1f5f9;
}

.sys-tab-btn.active {
  background: rgba(0, 242, 254, 0.2);
  border-color: #00f2fe;
  color: #00f2fe;
  font-weight: 600;
}

.sys-tab-btn.high.active {
  background: rgba(239, 68, 68, 0.2);
  border-color: #ef4444;
  color: #fca5a5;
}

.sys-tab-btn.low.active {
  background: rgba(56, 189, 248, 0.2);
  border-color: #38bdf8;
  color: #7dd3fc;
}

.topology-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: #94a3b8;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.dot-line {
  width: 12px;
  height: 3px;
  border-radius: 2px;
}

.dot-line.cyan {
  background: #00f2fe;
}

.dot-line.gold {
  background: #fbbf24;
}

.dot-point.active {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #00ff87;
}

/* 拓扑主体舞台容器 */
.topology-container {
  flex: 1;
  min-height: 0;
  position: relative;
  border: 1px solid rgba(0, 242, 254, 0.2);
  border-radius: 8px;
  background: #070d19;
  overflow-x: auto;
  overflow-y: hidden;
  box-sizing: border-box;
  transform: translateZ(0);
}

.topology-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 20;
  will-change: transform;
}

/* 动态飞线组合层 (默认无发货在途时完全隐藏，出现时平滑渐显) */
.flyline-group {
  transition: opacity 0.35s ease;
}

.flyline-base {
  fill: none;
  transition: all 0.3s ease;
}

/* 已发货标段：经典标准底管 */
.flyline-base.shipped {
  stroke-width: 1.5;
  opacity: 0.45;
}

.flyline-base.shipped.pipe {
  stroke: #00f2fe;
}

.flyline-base.shipped.fitting {
  stroke: #fbbf24;
}

/* 未发货标段：1.6px 醒目静止虚线 (清晰可辨规划路径，纯静态无流光) */
.flyline-base.unshipped {
  stroke-width: 1.6;
  stroke-dasharray: 6 5;
  opacity: 0.75;
}

.flyline-base.unshipped.pipe {
  stroke: #00f2fe;
}

.flyline-base.unshipped.fitting {
  stroke: #fbbf24;
}

/* 经典在途流动光带 (仅已发货专线) */
.flyline-stream {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-dasharray: 6 10;
  opacity: 0.95;
  animation: flow-travel 1.4s linear infinite;
  will-change: stroke-dashoffset;
}

.flyline-stream.pipe {
  stroke: url(#grad-pipe-line);
}

.flyline-stream.fitting {
  stroke: url(#grad-fitting-line);
}

@keyframes flow-travel {
  from {
    stroke-dashoffset: 32;
  }
  to {
    stroke-dashoffset: 0;
  }
}

.laser-particle {
  pointer-events: none;
}

/* 拓扑主排版三栏布局 (左: 供货单位基地随窗口弹性缩放 clamp(120px, 24%, 260px), 中: 28px 通道, 右: 1fr 需求标段) */
.topology-layout-grid {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: clamp(120px, 24%, 260px) 28px 1fr;
  padding: 10px 14px;
  box-sizing: border-box;
  z-index: 10;
  gap: 0;
}

/* 1. 供给制造基地列 */
.supply-hub-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: visible;
}

.supply-cards-stack {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  gap: 14px;
  overflow: visible;
  padding: 4px 2px;
  box-sizing: border-box;
}

.supply-node-card {
  background: linear-gradient(135deg, rgba(17, 34, 60, 0.85) 0%, rgba(11, 20, 36, 0.95) 100%);
  border: 1px solid rgba(0, 242, 254, 0.22);
  border-left: 3px solid #00f2fe;
  border-radius: 6px;
  padding: 10px 14px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-height: 60px;
  min-width: 0;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-sizing: border-box;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.22);
}

.supply-node-card:nth-child(2) {
  border-left-color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.22);
  background: linear-gradient(135deg, rgba(38, 30, 18, 0.75) 0%, rgba(15, 25, 45, 0.95) 100%);
}

.supply-node-card:nth-child(3) {
  border-left-color: #00ff87;
  border-color: rgba(0, 255, 135, 0.22);
  background: linear-gradient(135deg, rgba(16, 38, 30, 0.75) 0%, rgba(15, 25, 45, 0.95) 100%);
}

.supply-node-card:hover,
.supply-node-card.active,
.supply-node-card.hovered {
  border-color: #00f2fe;
  transform: translateX(3px);
  box-shadow: 0 4px 16px rgba(0, 242, 254, 0.18);
}

.supply-node-card:nth-child(2):hover,
.supply-node-card:nth-child(2).hovered {
  border-color: #fbbf24;
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.18);
}

.supply-node-card:nth-child(3):hover,
.supply-node-card:nth-child(3).hovered {
  border-color: #00ff87;
  box-shadow: 0 4px 16px rgba(0, 255, 135, 0.18);
}

.supply-node-card.is-shipping-source {
  border-color: #00f2fe;
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.22) 0%, #11263d 80%);
  box-shadow: 0 0 20px rgba(0, 242, 254, 0.5), inset 0 0 10px rgba(0, 242, 254, 0.18);
  animation: supplier-shipping-pulse 1.6s infinite ease-in-out;
  transform: translateX(3px);
  z-index: 5;
}

.supply-node-card.is-shipping-source.mat-fitting {
  border-color: #fbbf24;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.22) 0%, #11263d 80%);
  box-shadow: 0 0 20px rgba(251, 191, 36, 0.5), inset 0 0 10px rgba(251, 191, 36, 0.18);
}

.supply-node-card.is-shipping-source .node-port.port-out {
  box-shadow: 0 0 12px #00f2fe;
  background: #00f2fe;
}

.supply-node-card.is-shipping-source.mat-fitting .node-port.port-out {
  box-shadow: 0 0 12px #fbbf24;
  background: #fbbf24;
  border-color: #fbbf24;
}

@keyframes supplier-shipping-pulse {
  0%, 100% {
    box-shadow: 0 0 12px rgba(0, 242, 254, 0.35);
  }
  50% {
    box-shadow: 0 0 26px rgba(0, 242, 254, 0.8), inset 0 0 14px rgba(0, 242, 254, 0.3);
  }
}

.supply-node-card.dimmed {
  opacity: 0.3;
}

.sup-title {
  font-size: 13.5px;
  font-weight: 700;
  color: #ffffff;
  white-space: normal;
  line-height: 1.35;
  letter-spacing: 0.2px;
  word-break: break-word;
  padding-right: 4px;
}

/* 2. 中间传输通道 */
.transit-channel-col {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.channel-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  opacity: 0.6;
}

.channel-glow-line {
  width: 2px;
  height: 80px;
  background: linear-gradient(180deg, transparent, #00f2fe, transparent);
}

.channel-text {
  writing-mode: vertical-rl;
  font-size: 9.5px;
  color: #64748b;
  letter-spacing: 2px;
}

/* 3. 需求标段矩阵列：规整的高温水/低温水双立柱体系 */
.demand-hub-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  min-width: 0;
  padding-left: 6px;
  overflow: visible;
}

.demand-systems-split {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  overflow: visible;
  padding: 2px 4px;
  box-sizing: border-box;
}

.system-sub-col {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: visible;
}

.system-cards-list {
  flex: 1;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 6px;
  overflow: visible;
  padding: 1px;
  box-sizing: border-box;
}

.demand-node-card {
  flex: 1 1 0;
  min-height: 0;
  min-width: 0;
  background: #0f192b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 7px;
  padding: 5px 8px;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  cursor: pointer;
  transition: transform 0.2s ease, opacity 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
  box-sizing: border-box;
}

.demand-node-card.high-system {
  border-left: 3.5px solid #ef4444;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, #0f192b 40%);
}

.demand-node-card.low-system {
  border-left: 3.5px solid #0ea5e9;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.08) 0%, #0f192b 40%);
}

.demand-node-card.highlighted {
  border-color: #00f2fe;
  background: #11263d;
  transform: translateY(-1px);
}

/* 标段事件驱动高亮状态 */
.demand-node-card.is-event-target {
  transform: translateY(-2px);
  z-index: 5;
}

/* 1. 厂家发货接收端 */
.demand-node-card.is-event-target.event-cat-dispatch {
  border-color: #00f2fe;
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.18) 0%, #11263d 70%);
  box-shadow: 0 0 24px rgba(0, 242, 254, 0.6), inset 0 0 12px rgba(0, 242, 254, 0.18);
  animation: target-dispatch-pulse 1.6s infinite ease-in-out;
}

.demand-node-card.is-event-target.event-cat-dispatch.event-mat-fitting {
  border-color: #fbbf24;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.18) 0%, #11263d 70%);
  box-shadow: 0 0 24px rgba(251, 191, 36, 0.6), inset 0 0 12px rgba(251, 191, 36, 0.18);
}

.demand-node-card.is-event-target.event-cat-dispatch .node-port.port-in {
  box-shadow: 0 0 12px #00f2fe;
  background: #00f2fe;
}

/* 2. 确认到货/确权/库管确认端 */
.demand-node-card.is-event-target.event-cat-arrival {
  border-color: #38bdf8;
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.18) 0%, #11263d 70%);
  box-shadow: 0 0 24px rgba(56, 189, 248, 0.6), inset 0 0 12px rgba(56, 189, 248, 0.2);
  animation: target-arrival-pulse 1.6s infinite ease-in-out;
}

/* 管件到货/施工接收管件/管件库管确认 - 专属琥珀金光晕 */
.demand-node-card.is-event-target.event-cat-arrival.event-mat-fitting {
  border-color: #fbbf24;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.18) 0%, #11263d 70%);
  box-shadow: 0 0 24px rgba(251, 191, 36, 0.6), inset 0 0 12px rgba(251, 191, 36, 0.18);
  animation: target-fitting-pulse 1.6s infinite ease-in-out;
}

.demand-node-card.is-event-target.event-cat-arrival.event-mat-fitting .node-port.port-in {
  box-shadow: 0 0 12px #fbbf24;
  background: #fbbf24;
}

/* 3. 施工量确认/下沟安装端 */
.demand-node-card.is-event-target.event-cat-usage {
  border-color: #10b981;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, #0f192b 70%);
  box-shadow: 0 0 24px rgba(16, 185, 129, 0.65), inset 0 0 12px rgba(16, 185, 129, 0.25);
  animation: target-usage-pulse 1.6s infinite ease-in-out;
}

/* 4. 需求量申报/三日计划端 */
.demand-node-card.is-event-target.event-cat-plan {
  border-color: #f59e0b;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, #0f192b 70%);
  box-shadow: 0 0 24px rgba(245, 158, 11, 0.65), inset 0 0 12px rgba(245, 158, 11, 0.25);
  animation: target-plan-pulse 1.6s infinite ease-in-out;
}

@keyframes target-dispatch-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(0, 242, 254, 0.35); }
  50% { box-shadow: 0 0 28px rgba(0, 242, 254, 0.85), inset 0 0 14px rgba(0, 242, 254, 0.35); }
}

@keyframes target-fitting-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(251, 191, 36, 0.35); }
  50% { box-shadow: 0 0 28px rgba(251, 191, 36, 0.85), inset 0 0 14px rgba(251, 191, 36, 0.35); }
}

@keyframes target-arrival-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(56, 189, 248, 0.35); }
  50% { box-shadow: 0 0 28px rgba(56, 189, 248, 0.85), inset 0 0 14px rgba(56, 189, 248, 0.35); }
}

@keyframes target-usage-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(16, 185, 129, 0.35); }
  50% { box-shadow: 0 0 28px rgba(16, 185, 129, 0.9), inset 0 0 14px rgba(16, 185, 129, 0.4); }
}

@keyframes target-plan-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(245, 158, 11, 0.35); }
  50% { box-shadow: 0 0 28px rgba(245, 158, 11, 0.9), inset 0 0 14px rgba(245, 158, 11, 0.4); }
}

.demand-node-card.dimmed {
  opacity: 0.35;
}

.demand-node-card.completed {
  border-color: rgba(251, 191, 36, 0.35);
}

.sec-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  flex-shrink: 0;
}

.sec-badge-name {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  flex: 1;
}

.sec-sys-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
  line-height: 1.2;
  flex-shrink: 0;
}

.sec-sys-badge.high {
  background: rgba(239, 68, 68, 0.22);
  border: 1px solid rgba(239, 68, 68, 0.45);
  color: #fca5a5;
}

.sec-sys-badge.low {
  background: rgba(56, 189, 248, 0.18);
  border: 1px solid rgba(56, 189, 248, 0.45);
  color: #7dd3fc;
}

.sec-code-tag {
  font-family: monospace;
  font-size: 11px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
}

.sec-code-tag.high {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}

.sec-code-tag.low {
  background: rgba(56, 189, 248, 0.15);
  color: #7dd3fc;
}

.sec-title {
  font-size: 13.5px;
  font-weight: 700;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: 0.2px;
  line-height: 1.2;
}

.sec-status-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  padding: 1.5px 7px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  color: #cbd5e1;
  white-space: nowrap;
  font-weight: 500;
  flex-shrink: 0;
}

.sec-status-chip.running {
  background: rgba(239, 68, 68, 0.2);
  color: #ff4d4f;
  border: 1px solid rgba(255, 77, 79, 0.4);
  font-weight: 700;
}

.chip-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #94a3b8;
}

.sec-status-chip.running .chip-dot {
  background: #ff4d4f;
  box-shadow: 0 0 5px #ff4d4f;
}

/* 三轨微进度条与存量微条 (高清晰度、紧凑内聚与饱满进度条) */
.sec-metrics-body {
  display: flex;
  flex-direction: column;
  gap: 3.5px;
  margin-top: 1px;
  min-height: 0;
}

.sec-metric-line {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}

/* 标段卡片现场存量微核算条 (方案三) */
.sec-stock-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 4px;
  padding: 1.5px 6px;
  margin-top: 2px;
  font-size: 10px;
  line-height: 1.2;
}

.stock-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  min-width: 0;
}

.stock-dot {
  width: 4.5px;
  height: 4.5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stock-dot.green {
  background: #10b981;
  box-shadow: 0 0 4px #10b981;
}

.stock-dot.gold {
  background: #f59e0b;
  box-shadow: 0 0 4px #f59e0b;
}

.stock-label {
  color: #94a3b8;
  font-weight: 500;
  font-size: 10px;
  white-space: nowrap;
}

.stock-val {
  font-family: 'DIN Alternate', 'JetBrains Mono', 'Helvetica Neue', Arial, monospace;
  font-weight: 700;
  font-size: 11px;
  white-space: nowrap;
}

.stock-unit {
  font-size: 9px;
  font-weight: 500;
  margin-left: 1.5px;
  color: #94a3b8;
}

.stock-divider {
  color: rgba(255, 255, 255, 0.2);
  font-size: 9px;
  margin: 0 2px;
}

.line-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  width: 100%;
}

.line-label {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 3px;
  color: #ffffff;
  letter-spacing: 0.1px;
  line-height: 1.2;
  flex-shrink: 0;
  white-space: nowrap;
}

.tag-mini-icon {
  width: 11px;
  height: 11px;
  flex-shrink: 0;
  stroke: currentColor;
  display: inline-block;
  vertical-align: middle;
}

.line-label.pipe-tag {
  background: rgba(56, 189, 248, 0.14);
  border: 1px solid rgba(56, 189, 248, 0.35);
  color: #ffffff;
}

.line-label.construct-tag {
  background: rgba(16, 185, 129, 0.14);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #ffffff;
}

.line-label.fitting-tag {
  background: rgba(245, 158, 11, 0.14);
  border: 1px solid rgba(245, 158, 11, 0.35);
  color: #ffffff;
}

.line-val {
  font-family: 'DIN Alternate', 'JetBrains Mono', 'Helvetica Neue', Arial, monospace;
  font-size: 11.5px;
  font-weight: 600;
  flex: 1;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.line-val.cyan-text,
.line-pct.cyan-text {
  color: #00f2fe;
}

.line-val.green-text,
.line-pct.green-text {
  color: #10b981;
}

.line-val.gold-text,
.line-pct.gold-text {
  color: #fbbf24;
}

.line-pct {
  font-weight: 800;
  font-size: 11.5px;
  flex-shrink: 0;
  min-width: 32px;
  text-align: right;
}

.transit-num-tag {
  font-size: 10px;
  font-weight: 700;
  margin-left: 1px;
  padding: 0 2px;
  border-radius: 2px;
  display: inline-block;
  animation: transit-text-sync-glow 1.4s infinite ease-in-out;
}

.transit-num-tag.cyan-transit {
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.15);
  border: 1px solid rgba(0, 242, 254, 0.35);
}

.transit-num-tag.gold-transit {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.15);
  border: 1px solid rgba(251, 191, 36, 0.35);
}

.micro-bar-bg {
  position: relative;
  width: 100%;
  height: 7.5px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 4px;
  overflow: hidden;
}

.micro-bar-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  border-radius: 4px;
  transition: width 0.8s ease;
  z-index: 1;
}

.micro-bar-fill.cyan {
  background: linear-gradient(90deg, #0052d4, #00f2fe);
}

.micro-bar-fill.green {
  background: linear-gradient(90deg, #059669, #10b981);
}

.micro-bar-fill.gold {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

/* 在途差值段：动态流光闪烁高亮 (与上方在途角标严格同频 1.4s 呼吸) */
.micro-bar-transit {
  position: absolute;
  top: 0;
  height: 100%;
  border-radius: 2px;
  transition: all 0.8s ease;
  animation: transit-bar-sync-glow 1.4s infinite ease-in-out;
  z-index: 2;
}

.micro-bar-transit.cyan-transit {
  background: repeating-linear-gradient(
    -45deg,
    #00f2fe,
    #00f2fe 3px,
    #0284c7 3px,
    #0284c7 6px
  );
  box-shadow: 0 0 10px #00f2fe, inset 0 0 4px #ffffff;
}

.micro-bar-transit.gold-transit {
  background: repeating-linear-gradient(
    -45deg,
    #fbbf24,
    #fbbf24 3px,
    #d97706 3px,
    #d97706 6px
  );
  box-shadow: 0 0 10px #fbbf24, inset 0 0 4px #ffffff;
}

/* 同频呼吸动画：0% 与 100% 处于柔和基态，50% 处于高亮爆发态 */
@keyframes transit-bar-sync-glow {
  0%, 100% {
    opacity: 0.45;
    filter: brightness(1.05);
  }
  50% {
    opacity: 1;
    filter: brightness(1.9) drop-shadow(0 0 6px #ffffff);
  }
}

@keyframes transit-text-sync-glow {
  0%, 100% {
    opacity: 0.55;
    transform: scale(0.97);
  }
  50% {
    opacity: 1;
    transform: scale(1.03);
    text-shadow: 0 0 8px currentColor;
  }
}

/* 连接锚点 Node Ports (物理对齐) */
.node-port {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 15;
}

.node-port.port-out {
  right: -5px;
  background: #060913;
  border: 1.5px solid #00f2fe;
}

.node-port.port-in {
  left: -5px;
  background: #060913;
  border: 1.5px solid #38bdf8;
}

.port-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: #00ff87;
}

/* --- 右侧栏：实时战报流 Live Feed --- */
.live-feed-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 10px 14px 8px;
}

.live-status-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  color: #00ff87;
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.35);
  border-radius: 12px;
  padding: 1.5px 8px;
  cursor: pointer;
  user-select: none;
  transition: all 0.25s ease;
  box-shadow: 0 0 8px rgba(0, 255, 135, 0.1);
}

.live-status-pill:hover {
  background: rgba(16, 185, 129, 0.25);
  border-color: #00ff87;
  box-shadow: 0 0 12px rgba(0, 255, 135, 0.3);
  transform: translateY(-0.5px);
}

.live-status-pill:active {
  transform: scale(0.96);
}

.live-status-pill.is-refreshing {
  border-color: #00f2fe;
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.18);
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.3);
}

.live-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #00ff87;
  box-shadow: 0 0 6px #00ff87;
  flex-shrink: 0;
  animation: pulse-ring 2s infinite;
}

.refresh-sym {
  font-size: 9.5px;
  opacity: 0.75;
  transition: transform 0.3s ease, opacity 0.2s ease;
}

.live-status-pill:hover .refresh-sym {
  opacity: 1;
}

.refresh-sym.spin-anim {
  animation: rotate-refresh 0.65s linear infinite;
  opacity: 1;
}

@keyframes rotate-refresh {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* ==================== 统一业务分类筛选器 (折叠式下拉面板) ==================== */
.feed-filter-unified-bar {
  margin-bottom: 6px;
  flex-shrink: 0;
  position: relative;
  z-index: 40;
}

.filter-dropdown-wrapper {
  position: relative;
  width: 100%;
}

.unified-filter-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, rgba(17, 28, 48, 0.95) 0%, rgba(13, 22, 38, 0.95) 100%);
  border: 1px solid rgba(0, 242, 254, 0.25);
  border-radius: 6px;
  padding: 5px 9px;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: inset 0 0 8px rgba(0, 242, 254, 0.05);
}

.unified-filter-btn:hover {
  background: linear-gradient(135deg, rgba(22, 36, 62, 0.95) 0%, rgba(15, 27, 48, 0.95) 100%);
  border-color: #00f2fe;
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.2), inset 0 0 10px rgba(0, 242, 254, 0.1);
}

.unified-filter-btn.menu-open {
  border-color: #00f2fe;
  box-shadow: 0 0 12px rgba(0, 242, 254, 0.25);
}

.unified-filter-btn.is-filtered {
  border-color: #38bdf8;
  background: linear-gradient(135deg, rgba(14, 116, 144, 0.25) 0%, rgba(15, 23, 42, 0.9) 100%);
}

.filter-btn-left {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.filter-btn-icon {
  font-size: 13px;
}

.filter-btn-label {
  color: #94a3b8;
  font-size: 11px;
}

.filter-btn-current {
  color: #00f2fe;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.filter-btn-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-btn-badge {
  font-size: 10.5px;
  background: rgba(0, 242, 254, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(0, 242, 254, 0.3);
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 500;
}

.filter-caret {
  font-size: 9px;
  color: #64748b;
  transition: transform 0.2s ease;
}

/* 下拉浮层面板 */
.feed-filter-popover {
  position: absolute;
  top: calc(100% + 5px);
  left: 0;
  right: 0;
  background: rgba(10, 18, 32, 0.98);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 242, 254, 0.4);
  border-radius: 8px;
  padding: 8px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.75), 0 0 15px rgba(0, 242, 254, 0.15);
  z-index: 100;
}

.popover-tip-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 6px 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  margin-bottom: 6px;
}

.popover-title-text {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.reset-filter-link {
  font-size: 10.5px;
  color: #38bdf8;
  background: none;
  border: none;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

.reset-filter-link:hover {
  color: #00f2fe;
}

.popover-options-grid {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.filter-option-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-option-row:hover {
  background: rgba(0, 242, 254, 0.08);
  border-color: rgba(0, 242, 254, 0.2);
}

.filter-option-row.active {
  background: rgba(0, 242, 254, 0.18);
  border-color: #00f2fe;
}

.option-tag-part {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
}

.option-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.option-icon {
  font-size: 12px;
}

.option-title {
  color: #e2e8f0;
}

.filter-option-row.active .option-title {
  color: #00f2fe;
  font-weight: 600;
}

.option-meta-part {
  display: flex;
  align-items: center;
  gap: 6px;
}

.option-badge {
  font-size: 10px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 5px;
  border-radius: 8px;
}

.filter-option-row.active .option-badge {
  background: rgba(0, 242, 254, 0.25);
  color: #00f2fe;
  font-weight: 600;
}

.option-check {
  font-size: 11px;
  color: #00f2fe;
  font-weight: bold;
}

/* 展开动画 */
.filter-dropdown-anim-enter-active,
.filter-dropdown-anim-leave-active {
  transition: all 0.2s ease;
}

.filter-dropdown-anim-enter-from,
.filter-dropdown-anim-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.feed-list-wrapper {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 2px 4px 4px 4px;
  box-sizing: border-box;
}

.feed-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 1px 2px;
  box-sizing: border-box;
}

.feed-card {
  background: #0f192b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 6.5px 9px;
  display: flex;
  flex-direction: column;
  gap: 3.5px;
  position: relative;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
  box-sizing: border-box;
  width: 100%;
}

.feed-card:hover {
  background: #14223a;
  border-color: rgba(0, 242, 254, 0.4);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.45);
}

.feed-card.is-active-feed {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.12) 0%, #13243d 100%);
  border-color: #00f2fe;
  box-shadow: 0 0 16px rgba(0, 242, 254, 0.45);
}

.feed-card.is-active-feed.mat-fitting,
.feed-card.is-active-feed.is-fitting-event {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.14) 0%, #1a2233 100%);
  border-color: #fbbf24;
  box-shadow: 0 0 16px rgba(251, 191, 36, 0.45);
}

.feed-card.is-active-feed.arrival:not(.mat-fitting) {
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.12) 0%, #13243d 100%);
  border-color: #38bdf8;
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.4);
}

.feed-card.is-active-feed.usage {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.14) 0%, #112620 100%);
  border-color: #10b981;
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.4);
}

.feed-card.is-active-feed.plan {
  background: linear-gradient(135deg, rgba(244, 63, 94, 0.14) 0%, #201322 100%);
  border-color: #f43f5e;
  box-shadow: 0 0 16px rgba(244, 63, 94, 0.4);
}

/* 6 大核心业务分类卡片左侧标识色 */
.feed-card.dispatch {
  border-left: 3.5px solid #00f2fe;
}
.feed-card.dispatch.mat-fitting,
.feed-card.dispatch.is-fitting-event {
  border-left: 3.5px solid #fbbf24;
}

.feed-card.arrival {
  border-left: 3.5px solid #38bdf8;
}
.feed-card.arrival.mat-fitting,
.feed-card.arrival.is-fitting-event {
  border-left: 3.5px solid #fbbf24;
}

.feed-card.receive {
  border-left: 3.5px solid #38bdf8;
}
.feed-card.receive.mat-fitting,
.feed-card.receive.is-fitting-event {
  border-left: 3.5px solid #fbbf24;
}

.feed-card.warehouse {
  border-left: 3.5px solid #38bdf8;
}
.feed-card.warehouse.mat-fitting,
.feed-card.warehouse.is-fitting-event {
  border-left: 3.5px solid #fbbf24;
}

.feed-card.usage {
  border-left: 3.5px solid #10b981;
}

.feed-card.plan {
  border-left: 3.5px solid #f43f5e;
}

.feed-card.just-arrived {
  background: #12223a;
  animation: card-arrive-pulse 2s ease;
}

@keyframes card-arrive-pulse {
  0% { box-shadow: 0 0 15px rgba(0, 242, 254, 0.6); }
  100% { box-shadow: none; }
}

/* Row 1: 顶栏 (分类标签 + 经办人 + 时间) */
.feed-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
}

.header-left-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

/* 6 大分类徽章微胶囊 */
.feed-category-tag {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1.5px 6px;
  border-radius: 3px;
  white-space: nowrap;
  flex-shrink: 0;
}

.feed-category-tag.dispatch {
  background: rgba(0, 242, 254, 0.14);
  border: 1px solid rgba(0, 242, 254, 0.3);
  color: #38bdf8;
}
.feed-category-tag.dispatch.mat-fitting {
  background: rgba(251, 191, 36, 0.14);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}

.feed-category-tag.arrival {
  background: rgba(56, 189, 248, 0.14);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38bdf8;
}
.feed-category-tag.arrival.mat-fitting {
  background: rgba(251, 191, 36, 0.14);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}

.feed-category-tag.receive {
  background: rgba(56, 189, 248, 0.14);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38bdf8;
}
.feed-category-tag.receive.mat-fitting {
  background: rgba(251, 191, 36, 0.14);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}

.feed-category-tag.warehouse {
  background: rgba(56, 189, 248, 0.14);
  border: 1px solid rgba(56, 189, 248, 0.3);
  color: #38bdf8;
}
.feed-category-tag.warehouse.mat-fitting {
  background: rgba(251, 191, 36, 0.14);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}

.feed-category-tag.usage {
  background: rgba(16, 185, 129, 0.14);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #34d399;
}

.feed-category-tag.plan {
  background: rgba(244, 63, 94, 0.14);
  border: 1px solid rgba(244, 63, 94, 0.3);
  color: #fb7185;
}

.feed-operator-tag {
  font-size: 10px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 90px;
}

.feed-time {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 10.5px;
  color: #64748b;
  font-weight: 500;
  flex-shrink: 0;
  white-space: nowrap;
}

/* Row 2: 标题 / 流向行 (左侧主体或动作 ──► 右侧统一固定标段名称) */
.feed-card-headline {
  width: 100%;
  overflow: hidden;
}

.route-line-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
}

.route-source {
  color: #f1f5f9;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  text-align: left;
}

.route-arrow {
  color: #00f2fe;
  font-size: 10.5px;
  flex-shrink: 0;
  opacity: 0.85;
}

.route-target {
  color: #38bdf8;
  font-size: 11.5px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
  max-width: 55%;
  text-align: right;
  letter-spacing: 0.2px;
}

.feed-card.dispatch .route-arrow { color: #00f2fe; }
.feed-card.dispatch .route-target { color: #38bdf8; }

.feed-card.dispatch.mat-fitting .route-arrow,
.feed-card.dispatch.is-fitting-event .route-arrow { color: #fbbf24; }
.feed-card.dispatch.mat-fitting .route-target,
.feed-card.dispatch.is-fitting-event .route-target { color: #fbbf24; }

.feed-card.arrival .route-target { color: #38bdf8; }
.feed-card.arrival.mat-fitting .route-target,
.feed-card.arrival.is-fitting-event .route-target { color: #fbbf24; }

.feed-card.receive .route-target { color: #38bdf8; }
.feed-card.receive.mat-fitting .route-target,
.feed-card.receive.is-fitting-event .route-target { color: #fbbf24; }

.feed-card.warehouse .route-target { color: #38bdf8; }
.feed-card.warehouse.mat-fitting .route-target,
.feed-card.warehouse.is-fitting-event .route-target { color: #fbbf24; }

.feed-card.usage .route-target { color: #10b981; }

.feed-card.plan .route-target { color: #f43f5e; }

/* Row 3: 规格与数量明细栏 */
.feed-spec-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 2.5px 6px;
  border-radius: 4px;
  width: 100%;
  box-sizing: border-box;
}

.spec-text-col {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.spec-name {
  font-size: 10.5px;
  color: #cbd5e1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.spec-qty-col {
  flex-shrink: 0;
}

.spec-amount-badge {
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
  padding: 1px 5px;
  border-radius: 3px;
}

.spec-amount-badge.pipe {
  background: rgba(0, 242, 254, 0.15);
  color: #00f2fe;
}

.spec-amount-badge.fitting {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}

/* Row 4: 底栏 (单号/车牌 + 正向动态评价) */
.feed-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
}

.feed-code-tag {
  display: flex;
  align-items: center;
  gap: 3px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 9.5px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 1;
}

.code-icon {
  font-size: 9px;
  flex-shrink: 0;
}

.code-val {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.feed-pos-tag {
  font-size: 9.5px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
  flex-shrink: 0;
}

/* 战报动画 TransitionGroup */
.feed-item-enter-active,
.feed-item-leave-active {
  transition: all 0.35s ease-out;
}

.feed-item-enter-from {
  opacity: 0;
  transform: translateY(-12px);
}

.feed-item-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

/* --- 🏆 本周战报（连续 7 日发货 vs 施工态势）Weekly Report Panel --- */
.weekly-report-panel {
  flex-shrink: 0;
  height: 352px;
  min-height: 340px;
  max-height: 365px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  padding: 12px 14px 10px;
  transition: border-color 0.4s ease, box-shadow 0.4s ease;
}

/* 轮播切换瞬间微光流动质感 */
.weekly-report-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00f2fe, #34d399, transparent);
  transition: left 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  pointer-events: none;
  z-index: 5;
}

.weekly-report-panel.is-switching::before {
  left: 100%;
}

.weekly-report-panel.is-switching {
  box-shadow: inset 0 0 16px rgba(0, 242, 254, 0.15), 0 0 12px rgba(0, 242, 254, 0.2);
}

.panel-title-anim-box {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* 标题切换过渡动画 */
.weekly-title-anim-enter-active,
.weekly-title-anim-leave-active {
  transition: all 0.32s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.weekly-title-anim-enter-from {
  opacity: 0;
  transform: translateY(-8px);
  filter: blur(2px);
}

.weekly-title-anim-leave-to {
  opacity: 0;
  transform: translateY(8px);
  filter: blur(2px);
}

/* KPI 卡片组平滑入场与缩放动画 */
.weekly-kpi-anim-enter-active,
.weekly-kpi-anim-leave-active {
  transition: all 0.36s cubic-bezier(0.34, 1.3, 0.64, 1);
}

.weekly-kpi-anim-enter-from {
  opacity: 0;
  transform: scale(0.96) translateY(6px);
  filter: blur(2px);
}

.weekly-kpi-anim-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(-6px);
  filter: blur(2px);
}

/* 底部复盘栏平滑过渡 */
.weekly-insight-anim-enter-active,
.weekly-insight-anim-leave-active {
  transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.weekly-insight-anim-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.weekly-insight-anim-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* 轻量文本快速淡入淡出 */
.weekly-fade-fast-enter-active,
.weekly-fade-fast-leave-active {
  transition: opacity 0.25s ease;
}

.weekly-fade-fast-enter-from,
.weekly-fade-fast-leave-to {
  opacity: 0;
}

.weekly-report-panel .panel-header {
  margin-bottom: 8px;
  flex-shrink: 0;
}

/* 战报自动轮播倒计时徽章 */
.weekly-countdown-badge {
  display: inline-flex;
  align-items: center;
  gap: 4.5px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 10px;
  font-weight: 700;
  color: #00f2fe;
  background: rgba(0, 242, 254, 0.12);
  border: 1px solid rgba(0, 242, 254, 0.28);
  padding: 1.5px 7px;
  border-radius: 12px;
  line-height: 1.3;
  user-select: none;
  transition: all 0.25s ease;
  box-shadow: 0 0 6px rgba(0, 242, 254, 0.1);
}

.weekly-countdown-badge.paused {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.12);
  border-color: rgba(148, 163, 184, 0.25);
  box-shadow: none;
}

.countdown-pulse-dot {
  width: 4.5px;
  height: 4.5px;
  border-radius: 50%;
  background: #00f2fe;
  box-shadow: 0 0 5px #00f2fe;
  animation: weekly-pulse-dot 1.5s infinite ease-in-out;
  flex-shrink: 0;
}

.countdown-pulse-dot.paused {
  background: #94a3b8;
  box-shadow: none;
  animation: none;
}

.countdown-text {
  font-family: 'JetBrains Mono', Consolas, monospace;
  letter-spacing: 0.2px;
}

@keyframes weekly-pulse-dot {
  0%, 100% { opacity: 0.4; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1.2); }
}

/* 1. 顶部固定双 KPI：无数据时仅替换辅助文案 */
.weekly-kpi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.weekly-kpi-card {
  min-height: 64px;
  border-radius: 6px;
  padding: 6px 10px 5px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
  transition: all 0.2s ease;
}

.weekly-kpi-card.ship-card {
  background: linear-gradient(135deg, rgba(0, 242, 254, 0.08) 0%, rgba(15, 23, 42, 0.7) 100%);
  border: 1px solid rgba(0, 242, 254, 0.25);
  border-left: 3px solid #00f2fe;
}

.weekly-kpi-card.usage-card {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.08) 0%, rgba(15, 23, 42, 0.7) 100%);
  border: 1px solid rgba(251, 191, 36, 0.25);
  border-left: 3px solid #fbbf24;
}

.weekly-kpi-card.fit-usage-card {
  background: linear-gradient(135deg, rgba(52, 211, 153, 0.08) 0%, rgba(15, 23, 42, 0.7) 100%);
  border: 1px solid rgba(52, 211, 153, 0.25);
  border-left: 3px solid #34d399;
}

.kpi-card-header {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  overflow: hidden;
}

.kpi-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.kpi-dot.cyan { background: #00f2fe; box-shadow: 0 0 4px #00f2fe; }
.kpi-dot.gold { background: #fbbf24; box-shadow: 0 0 4px #fbbf24; }
.kpi-dot.emerald { background: #34d399; box-shadow: 0 0 4px #34d399; }

.kpi-title {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-main-val {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 17.5px;
  font-weight: 900;
  line-height: 1.1;
  white-space: nowrap;
  flex-shrink: 0;
}

.kpi-main-val.cyan-text { color: #00f2fe; text-shadow: 0 0 6px rgba(0, 242, 254, 0.3); }
.kpi-main-val.gold-text { color: #fbbf24; text-shadow: 0 0 6px rgba(251, 191, 36, 0.3); }
.kpi-main-val.emerald-text { color: #34d399; text-shadow: 0 0 6px rgba(52, 211, 153, 0.3); }

.kpi-main-val .unit {
  font-size: 10px;
  font-weight: 600;
  color: #64748b;
  margin-left: 1px;
}

.weekly-kpi-note {
  width: 100%;
  color: #64748b;
  font-size: 9.5px;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.weekly-chart-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px 4px;
  color: #cbd5e1;
  font-size: 10px;
  font-weight: 600;
  flex-shrink: 0;
}

.weekly-chart-heading span:last-child {
  color: #64748b;
  font-size: 9px;
  font-weight: 500;
}

/* 2. 固定趋势区：保留图表骨架，空数据时展示清晰状态 */
.weekly-chart-box {
  flex: 1;
  min-height: 165px;
  max-height: 185px;
  height: 175px;
  width: 100%;
  position: relative;
  background: rgba(11, 19, 35, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  box-sizing: border-box;
  overflow: hidden;
}

.weekly-echarts-dom {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100% !important;
  height: 100% !important;
  min-height: 0;
}

.weekly-empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  pointer-events: none;
  background: rgba(11, 19, 35, 0.52);
  text-align: center;
}

.weekly-empty-state strong {
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 700;
}

.weekly-empty-state span {
  color: #94a3b8;
  font-size: 10px;
}

.weekly-insight-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 5px;
  padding-top: 5px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.weekly-insight-grid > div {
  min-width: 0;
  padding: 0 4px;
  text-align: center;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

.weekly-insight-grid > div:first-child {
  padding-left: 0;
}

.weekly-insight-grid > div:last-child {
  padding-right: 0;
  border-right: 0;
}

.weekly-insight-grid span,
.weekly-insight-grid strong {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.weekly-insight-grid span {
  color: #64748b;
  font-size: 9px;
  line-height: 1.2;
}

.weekly-insight-grid strong {
  margin-top: 3px;
  color: #e2e8f0;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 10px;
  line-height: 1.15;
  font-weight: 700;
}

/* --- 精美深色科技细滚动条 Custom Scrollbars --- */
.left-col::-webkit-scrollbar,
.feed-list-wrapper::-webkit-scrollbar,
.system-cards-list::-webkit-scrollbar,
.milestone-list::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

.left-col::-webkit-scrollbar-track,
.feed-list-wrapper::-webkit-scrollbar-track,
.system-cards-list::-webkit-scrollbar-track,
.milestone-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 2px;
}

.left-col::-webkit-scrollbar-thumb,
.feed-list-wrapper::-webkit-scrollbar-thumb,
.system-cards-list::-webkit-scrollbar-thumb,
.milestone-list::-webkit-scrollbar-thumb {
  background: rgba(0, 242, 254, 0.25);
  border-radius: 2px;
}

/* ==========================================================================
   明亮浅色高科技模式 (Light Clean Tech Theme)
   ========================================================================== */

.bigscreen-container.light {
  background-color: #f1f5f9;
  background-image: none;
  color: #0f172a;
}

.bigscreen-container.light .bigscreen-header {
  background: #ffffff;
  border-bottom: 1px solid rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .header-badge {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.3);
  color: #0284c7;
}

.bigscreen-container.light .header-badge.live-mode {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
  color: #059669;
}

.bigscreen-container.light .header-time {
  color: #475569;
}

.bigscreen-container.light .header-title {
  color: #0f172a;
  text-shadow: none;
}

.bigscreen-container.light .title-mobile-line1 {
  color: #64748b;
}

.bigscreen-container.light .title-mobile-line2 {
  color: #0f172a;
  text-shadow: none;
}

.bigscreen-container.light .mobile-nav-tabs {
  background: #ffffff;
  border-bottom: 1px solid rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .mobile-tab-btn {
  color: #64748b;
}

.bigscreen-container.light .mobile-tab-btn.active {
  color: #0284c7;
  border-bottom-color: #0284c7;
  background: rgba(2, 132, 199, 0.08);
}

.bigscreen-container.light .mobile-tab-btn .tab-badge {
  background: #e0f2fe;
  color: #0369a1;
  border-color: #bae6fd;
}

.bigscreen-container.light .mobile-topo-scroll-hint {
  color: #0284c7;
  background: rgba(2, 132, 199, 0.08);
  border-color: rgba(2, 132, 199, 0.3);
}

.bigscreen-container.light .control-trigger-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #0284c7;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}

.bigscreen-container.light .control-trigger-btn:hover,
.bigscreen-container.light .control-trigger-btn.active {
  background: #f0f9ff;
  border-color: #0284c7;
  color: #0369a1;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2);
}

.bigscreen-container.light .control-menu-popover {
  background: rgba(255, 255, 255, 0.98);
  border-color: #cbd5e1;
  box-shadow: 0 16px 36px -8px rgba(15, 23, 42, 0.15);
}

.bigscreen-container.light .popover-title {
  color: #0f172a;
}

.bigscreen-container.light .group-title {
  color: #64748b;
}

.bigscreen-container.light .popover-header,
.bigscreen-container.light .popover-footer {
  border-color: #e2e8f0;
}

.bigscreen-container.light .action-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #334155;
}

.bigscreen-container.light .action-btn:hover {
  background: #f8fafc;
  color: #0f172a;
  border-color: #94a3b8;
}

.bigscreen-container.light .live-stream-btn {
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.5);
  color: #059669;
}

.bigscreen-container.light .live-stream-btn.active {
  background: #059669;
  border-color: #059669;
  color: #ffffff;
}

.bigscreen-container.light .setting-item {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.bigscreen-container.light .setting-item:hover {
  background: #f1f5f9;
  border-color: #0284c7;
}

.bigscreen-container.light .setting-name {
  color: #334155;
}

.bigscreen-container.light .setting-val-tag {
  color: #0284c7;
  background: rgba(2, 132, 199, 0.1);
}

.bigscreen-container.light .setting-slider {
  accent-color: #0284c7;
}

.bigscreen-container.light .save-config-btn {
  background: linear-gradient(135deg, #0284c7, #0369a1);
  border-color: #0284c7;
  color: #ffffff;
}

.bigscreen-container.light .reset-config-btn {
  background: #f1f5f9;
  border-color: #cbd5e1;
  color: #64748b;
}

.bigscreen-container.light .theme-toggle-btn {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.35);
  color: #0284c7;
}

.bigscreen-container.light .demo-btn {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.35);
  color: #0284c7;
}

.bigscreen-container.light .demo-btn.active {
  background: rgba(16, 185, 129, 0.15);
  border-color: rgba(16, 185, 129, 0.5);
  color: #059669;
}

.bigscreen-container.light .sim-btn {
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.3);
  color: #0284c7;
}

.bigscreen-container.light .sim-btn.fitting {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.3);
  color: #d97706;
}

.bigscreen-container.light .back-btn {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.25);
  color: #dc2626;
}

.bigscreen-container.light .panel-box {
  background: #ffffff;
  border: 1px solid rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .panel-box::before,
.bigscreen-container.light .panel-box::after {
  background: #0284c7;
}

.bigscreen-container.light .panel-title {
  color: #0f172a;
}

.bigscreen-container.light .panel-tag.cyan {
  background: rgba(2, 132, 199, 0.12);
  color: #0284c7;
  border: 1px solid rgba(2, 132, 199, 0.35);
}

.bigscreen-container.light .panel-tag.gold {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.35);
}

.bigscreen-container.light .panel-tag.green {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.35);
  font-weight: 700;
}

.bigscreen-container.light .panel-tag.danger,
.bigscreen-container.light .panel-tag.red {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.35);
  font-weight: 700;
}

/* 浅色模式：今日天气与施工条件卡片高对比度支持 */
.bigscreen-container.light .left-col .weather-loc-bar .loc-pin {
  color: #0284c7;
}

.bigscreen-container.light .left-col .weather-loc-bar .loc-text {
  color: #0f172a;
  font-weight: 700;
}

.bigscreen-container.light .left-col .weather-loc-bar .loc-dot {
  color: #64748b;
}

.bigscreen-container.light .left-col .weather-loc-bar .loc-time {
  color: #0284c7;
  font-weight: 700;
}

.bigscreen-container.light .left-col .weather-metrics-row {
  background: #f1f5f9;
  border: 1px solid rgba(203, 213, 225, 0.9);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.bigscreen-container.light .left-col .weather-name {
  color: #0f172a;
  font-weight: 800;
}

.bigscreen-container.light .left-col .temp-degree {
  color: #0284c7;
  font-weight: 800;
}

.bigscreen-container.light .left-col .temp-degree small {
  color: #475569;
  font-weight: 700;
}

.bigscreen-container.light .left-col .param-k {
  color: #475569;
  font-weight: 600;
}

.bigscreen-container.light .left-col .param-v {
  color: #0f172a;
  font-weight: 800;
}

.bigscreen-container.light .left-col .weather-forecast-subrow {
  border-top: 1px dashed #cbd5e1;
}

.bigscreen-container.light .left-col .weather-forecast-subrow .fc-range {
  color: #b45309;
  font-weight: 800;
}

.bigscreen-container.light .left-col .weather-forecast-subrow .fc-dot {
  color: #94a3b8;
}

.bigscreen-container.light .left-col .weather-forecast-subrow .fc-dn {
  color: #0f172a;
  font-weight: 700;
}

.bigscreen-container.light .topo-sub-tag {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #64748b;
}

.bigscreen-container.light .sys-tab-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #64748b;
}

.bigscreen-container.light .sys-tab-btn.active {
  background: rgba(2, 132, 199, 0.15);
  border-color: #0284c7;
  color: #0284c7;
}

.bigscreen-container.light .metric-item {
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.bigscreen-container.light .metric-label {
  color: #64748b;
}

.bigscreen-container.light .metric-capsule.cyan-capsule {
  background: rgba(2, 132, 199, 0.12);
  color: #0284c7;
  border: 1px solid rgba(2, 132, 199, 0.35);
}

.bigscreen-container.light .metric-capsule.amber-capsule {
  background: #fef3c7;
  color: #b45309;
  border-color: #fde68a;
}

.bigscreen-container.light .metric-capsule.purple-capsule {
  background: #f3e8ff;
  color: #7e22ce;
  border-color: #d8b4fe;
}

.bigscreen-container.light .metric-capsule.red-capsule {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fca5a5;
}

.bigscreen-container.light .metric-capsule.gray-capsule {
  background: #f1f5f9;
  color: #64748b;
  border-color: #e2e8f0;
}

.bigscreen-container.light .metric-val .num {
  color: #0f172a;
}

.bigscreen-container.light .highlight-cyan .num {
  color: #0284c7;
}

.bigscreen-container.light .highlight-amber .num {
  color: #d97706;
}

.bigscreen-container.light .highlight-green .num {
  color: #059669;
}

.bigscreen-container.light .highlight-purple .num,
.bigscreen-container.light .purple-text {
  color: #9333ea !important;
}

.bigscreen-container.light .metric-val.dual-val .sep {
  color: #94a3b8;
}

.bigscreen-container.light .amber-text {
  color: #d97706 !important;
}

.bigscreen-container.light .green-text {
  color: #059669 !important;
}

.bigscreen-container.light .red-text {
  color: #e11d48 !important;
}

.bigscreen-container.light .gray-text {
  color: #64748b !important;
}

.bigscreen-container.light .highlight-gold .num {
  color: #d97706;
}

.bigscreen-container.light .highlight-orange .num {
  color: #ea580c;
}

.bigscreen-container.light .energy-progress-info {
  color: #475569;
}

.bigscreen-container.light .cyan-text {
  color: #0284c7;
}

.bigscreen-container.light .gold-text {
  color: #d97706;
}

.bigscreen-container.light .energy-bar-track {
  background: #e2e8f0;
  border-color: rgba(203, 213, 225, 0.6);
}

.bigscreen-container.light .energy-bar-fill.cyan-glow {
  background: linear-gradient(90deg, #0284c7, #38bdf8);
}

.bigscreen-container.light .energy-bar-fill.gold-glow {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

.bigscreen-container.light .fitting-pill {
  background: #ffffff;
  border-color: rgba(245, 158, 11, 0.3);
}

.bigscreen-container.light .pill-name {
  color: #475569;
}

.bigscreen-container.light .pill-count {
  color: #d97706;
}

.bigscreen-container.light .safety-card {
  background: #f8fafc;
  border-color: rgba(16, 185, 129, 0.3);
}

.bigscreen-container.light .safety-val {
  color: #059669;
}

.bigscreen-container.light .safety-desc {
  color: #64748b;
}

.bigscreen-container.light .topology-legend {
  color: #475569;
}

.bigscreen-container.light .dot-line.cyan {
  background: #0284c7;
}

.bigscreen-container.light .dot-line.gold {
  background: #ea580c;
}

.bigscreen-container.light .topology-container {
  background: #f8fafc;
  border-color: rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .flyline-base.shipped.pipe {
  stroke: #0284c7;
  stroke-width: 1.5;
  opacity: 0.35;
}

.bigscreen-container.light .flyline-base.shipped.fitting {
  stroke: #ea580c;
  stroke-width: 1.5;
  opacity: 0.35;
}

.bigscreen-container.light .flyline-base.unshipped.pipe {
  stroke: #0284c7;
  stroke-width: 1.6;
  stroke-dasharray: 6 5;
  opacity: 0.65;
}

.bigscreen-container.light .flyline-base.unshipped.fitting {
  stroke: #ea580c;
  stroke-width: 1.6;
  stroke-dasharray: 6 5;
  opacity: 0.65;
}

.bigscreen-container.light .flyline-stream.pipe {
  stroke: #0284c7;
}

.bigscreen-container.light .flyline-stream.fitting {
  stroke: #ea580c;
}

.bigscreen-container.light .system-sub-col {
  background: transparent;
  border: none;
}

.bigscreen-container.light .supply-node-card {
  background: #ffffff;
  border-color: rgba(203, 213, 225, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.bigscreen-container.light .supply-node-card:nth-child(1) {
  border-left-color: #0284c7;
}

.bigscreen-container.light .supply-node-card:nth-child(2) {
  border-left-color: #d97706;
}

.bigscreen-container.light .supply-node-card:nth-child(3) {
  border-left-color: #059669;
}

.bigscreen-container.light .supply-node-card:hover,
.bigscreen-container.light .supply-node-card.active,
.bigscreen-container.light .supply-node-card.hovered {
  border-color: #0284c7;
  background: #f8fafc;
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.12);
}

.bigscreen-container.light .sup-title {
  color: #0f172a;
}

.bigscreen-container.light .demand-node-card {
  background: #ffffff;
  border-color: rgba(226, 232, 240, 0.9);
}

.bigscreen-container.light .demand-node-card.high-system {
  border-left: 3.5px solid #dc2626;
  background: linear-gradient(135deg, rgba(254, 226, 226, 0.5) 0%, #ffffff 40%);
}

.bigscreen-container.light .demand-node-card.low-system {
  border-left: 3.5px solid #0284c7;
  background: linear-gradient(135deg, rgba(224, 242, 254, 0.5) 0%, #ffffff 40%);
}

.bigscreen-container.light .demand-node-card.highlighted {
  border-color: #0284c7;
  background: #f0f9ff;
}

.bigscreen-container.light .sec-sys-badge.high {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.35);
  color: #dc2626;
}

.bigscreen-container.light .sec-sys-badge.low {
  background: rgba(2, 132, 199, 0.12);
  border: 1px solid rgba(2, 132, 199, 0.35);
  color: #0284c7;
}

.bigscreen-container.light .sec-code-tag.high {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}

.bigscreen-container.light .sec-code-tag.low {
  background: rgba(2, 132, 199, 0.1);
  color: #0369a1;
}

.bigscreen-container.light .sec-title {
  color: #0f172a;
}

.bigscreen-container.light .sec-status-chip {
  background: #f1f5f9;
  color: #475569;
}

.bigscreen-container.light .sec-status-chip.running {
  background: #fee2e2;
  color: #dc2626;
  border: 1px solid #fca5a5;
  font-weight: 700;
}

.bigscreen-container.light .sec-status-chip.running .chip-dot {
  background: #dc2626;
  box-shadow: 0 0 5px rgba(220, 38, 38, 0.5);
}

.bigscreen-container.light .line-label {
  color: #0f172a;
}

.bigscreen-container.light .line-label.pipe-tag {
  background: rgba(2, 132, 199, 0.12);
  border: 1px solid rgba(2, 132, 199, 0.35);
  color: #0369a1;
}

.bigscreen-container.light .line-label.construct-tag {
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.35);
  color: #059669;
}

.bigscreen-container.light .line-val.cyan-text,
.bigscreen-container.light .line-pct.cyan-text {
  color: #0284c7;
}

.bigscreen-container.light .line-val.green-text,
.bigscreen-container.light .line-pct.green-text {
  color: #059669;
}

.bigscreen-container.light .line-val.gold-text,
.bigscreen-container.light .line-pct.gold-text {
  color: #d97706;
}

.bigscreen-container.light .line-label.fitting-tag {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.4);
  color: #b45309;
}

.bigscreen-container.light .sec-stock-strip {
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.07);
}

.bigscreen-container.light .stock-label,
.bigscreen-container.light .stock-unit {
  color: #64748b;
}

.bigscreen-container.light .stock-divider {
  color: rgba(0, 0, 0, 0.2);
}

.bigscreen-container.light .micro-bar-bg {
  background: #e2e8f0;
}

.bigscreen-container.light .micro-bar-fill.cyan {
  background: linear-gradient(90deg, #0284c7, #38bdf8);
}

.bigscreen-container.light .micro-bar-fill.green {
  background: linear-gradient(90deg, #059669, #10b981);
}

.bigscreen-container.light .micro-bar-fill.gold {
  background: linear-gradient(90deg, #d97706, #fbbf24);
}

.bigscreen-container.light .transit-num-tag.cyan-transit {
  color: #0284c7;
  background: rgba(2, 132, 199, 0.12);
  border-color: rgba(2, 132, 199, 0.35);
}

.bigscreen-container.light .transit-num-tag.gold-transit {
  color: #b45309;
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.35);
}

.bigscreen-container.light .micro-bar-transit.cyan-transit {
  background: repeating-linear-gradient(
    -45deg,
    #0284c7,
    #0284c7 3px,
    #38bdf8 3px,
    #38bdf8 6px
  );
  box-shadow: 0 0 8px rgba(2, 132, 199, 0.6);
}

.bigscreen-container.light .micro-bar-transit.gold-transit {
  background: repeating-linear-gradient(
    -45deg,
    #d97706,
    #d97706 3px,
    #fbbf24 3px,
    #fbbf24 6px
  );
  box-shadow: 0 0 8px rgba(217, 119, 6, 0.6);
}

.bigscreen-container.light .node-port.port-out {
  background: #ffffff;
  border-color: #0284c7;
}

.bigscreen-container.light .node-port.port-in {
  background: #ffffff;
  border-color: #0284c7;
}

.bigscreen-container.light .unified-filter-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.bigscreen-container.light .unified-filter-btn:hover {
  border-color: #0284c7;
  background: #f8fafc;
}

.bigscreen-container.light .filter-btn-current {
  color: #0284c7;
}

.bigscreen-container.light .filter-btn-badge {
  background: #e0f2fe;
  color: #0284c7;
  border-color: #bae6fd;
}

.bigscreen-container.light .feed-filter-popover {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12);
}

.bigscreen-container.light .filter-option-row {
  background: transparent;
}

.bigscreen-container.light .filter-option-row:hover {
  background: #f1f5f9;
  border-color: #e2e8f0;
}

.bigscreen-container.light .filter-option-row.active {
  background: #e0f2fe;
  border-color: #0284c7;
}

.bigscreen-container.light .filter-option-row .option-title {
  color: #1e293b;
}

.bigscreen-container.light .filter-option-row.active .option-title {
  color: #0284c7;
}

.bigscreen-container.light .filter-option-row.active .option-check {
  color: #0284c7;
}

.bigscreen-container.light .feed-card {
  background: #ffffff;
  border-color: rgba(226, 232, 240, 0.9);
}

.bigscreen-container.light .feed-card.dispatch {
  border-left: 3.5px solid #0284c7;
}
.bigscreen-container.light .feed-card.dispatch.mat-fitting,
.bigscreen-container.light .feed-card.dispatch.is-fitting-event {
  border-left: 3.5px solid #d97706;
}

.bigscreen-container.light .feed-card.arrival {
  border-left: 3.5px solid #2563eb;
}
.bigscreen-container.light .feed-card.arrival.mat-fitting,
.bigscreen-container.light .feed-card.arrival.is-fitting-event {
  border-left: 3.5px solid #d97706;
}

.bigscreen-container.light .feed-card.receive {
  border-left: 3.5px solid #2563eb;
}
.bigscreen-container.light .feed-card.receive.mat-fitting,
.bigscreen-container.light .feed-card.receive.is-fitting-event {
  border-left: 3.5px solid #d97706;
}

.bigscreen-container.light .feed-card.warehouse {
  border-left: 3.5px solid #2563eb;
}
.bigscreen-container.light .feed-card.warehouse.mat-fitting,
.bigscreen-container.light .feed-card.warehouse.is-fitting-event {
  border-left: 3.5px solid #d97706;
}

.bigscreen-container.light .feed-card.usage {
  border-left: 3.5px solid #059669;
}

.bigscreen-container.light .feed-card.plan {
  border-left: 3.5px solid #e11d48;
}

/* 浅色模式下的实时直连徽章 (高对比度墨绿+高清晰字阶，杜绝发虚) */
.bigscreen-container.light .live-status-pill {
  color: #047857;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(5, 150, 105, 0.35);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  font-weight: 600;
}

.bigscreen-container.light .live-status-pill:hover {
  background: rgba(16, 185, 129, 0.22);
  border-color: #059669;
  box-shadow: 0 0 10px rgba(5, 150, 105, 0.2);
}

.bigscreen-container.light .live-status-pill.is-refreshing {
  border-color: #0284c7;
  color: #0284c7;
  background: rgba(2, 132, 199, 0.15);
  box-shadow: 0 0 8px rgba(2, 132, 199, 0.2);
}

.bigscreen-container.light .live-dot {
  background: #059669;
  box-shadow: 0 0 4px #059669;
}

.bigscreen-container.light .feed-category-tag.dispatch {
  background: rgba(2, 132, 199, 0.12);
  border: 1px solid rgba(2, 132, 199, 0.25);
  color: #0284c7;
}
.bigscreen-container.light .feed-category-tag.dispatch.mat-fitting {
  background: rgba(217, 119, 6, 0.12);
  border: 1px solid rgba(217, 119, 6, 0.25);
  color: #d97706;
}

.bigscreen-container.light .feed-category-tag.arrival {
  background: rgba(37, 99, 235, 0.12);
  border: 1px solid rgba(37, 99, 235, 0.25);
  color: #2563eb;
}
.bigscreen-container.light .feed-category-tag.arrival.mat-fitting {
  background: rgba(217, 119, 6, 0.12);
  border: 1px solid rgba(217, 119, 6, 0.25);
  color: #d97706;
}

.bigscreen-container.light .feed-category-tag.receive {
  background: rgba(37, 99, 235, 0.12);
  border: 1px solid rgba(37, 99, 235, 0.25);
  color: #2563eb;
}
.bigscreen-container.light .feed-category-tag.receive.mat-fitting {
  background: rgba(217, 119, 6, 0.12);
  border: 1px solid rgba(217, 119, 6, 0.25);
  color: #d97706;
}

.bigscreen-container.light .feed-category-tag.warehouse {
  background: rgba(37, 99, 235, 0.12);
  border: 1px solid rgba(37, 99, 235, 0.25);
  color: #2563eb;
}
.bigscreen-container.light .feed-category-tag.warehouse.mat-fitting {
  background: rgba(217, 119, 6, 0.12);
  border: 1px solid rgba(217, 119, 6, 0.25);
  color: #d97706;
}

.bigscreen-container.light .feed-category-tag.usage {
  background: rgba(5, 150, 105, 0.12);
  border: 1px solid rgba(5, 150, 105, 0.25);
  color: #059669;
}

.bigscreen-container.light .feed-category-tag.plan {
  background: rgba(225, 29, 72, 0.12);
  border: 1px solid rgba(225, 29, 72, 0.25);
  color: #e11d48;
}

.bigscreen-container.light .feed-card.just-arrived {
  background: #f0f9ff;
}

.bigscreen-container.light .feed-operator-tag {
  background: #f1f5f9;
  border-color: #e2e8f0;
  color: #475569;
}

.bigscreen-container.light .route-source {
  color: #0f172a;
}

.bigscreen-container.light .route-arrow {
  color: #0284c7;
}

.bigscreen-container.light .route-target {
  color: #0284c7;
}

.bigscreen-container.light .feed-card.dispatch .route-arrow,
.bigscreen-container.light .feed-card.dispatch .route-target { color: #0284c7; }

.bigscreen-container.light .feed-card.dispatch.mat-fitting .route-arrow,
.bigscreen-container.light .feed-card.dispatch.mat-fitting .route-target,
.bigscreen-container.light .feed-card.dispatch.is-fitting-event .route-arrow,
.bigscreen-container.light .feed-card.dispatch.is-fitting-event .route-target { color: #d97706; }

.bigscreen-container.light .feed-card.arrival .route-target { color: #2563eb; }
.bigscreen-container.light .feed-card.arrival.mat-fitting .route-target,
.bigscreen-container.light .feed-card.arrival.is-fitting-event .route-target { color: #d97706; }

.bigscreen-container.light .feed-card.receive .route-target { color: #2563eb; }
.bigscreen-container.light .feed-card.receive.mat-fitting .route-target,
.bigscreen-container.light .feed-card.receive.is-fitting-event .route-target { color: #d97706; }

.bigscreen-container.light .feed-card.warehouse .route-target { color: #2563eb; }
.bigscreen-container.light .feed-card.warehouse.mat-fitting .route-target,
.bigscreen-container.light .feed-card.warehouse.is-fitting-event .route-target { color: #d97706; }

.bigscreen-container.light .feed-card.usage .route-target { color: #059669; }

.bigscreen-container.light .feed-card.plan .route-target { color: #e11d48; }

.bigscreen-container.light .feed-spec-box {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.bigscreen-container.light .spec-name {
  color: #334155;
}

.bigscreen-container.light .spec-amount-badge.pipe {
  background: rgba(2, 132, 199, 0.12);
  color: #0284c7;
}

.bigscreen-container.light .spec-amount-badge.fitting {
  background: rgba(217, 119, 6, 0.12);
  color: #d97706;
}

.bigscreen-container.light .feed-code-tag {
  color: #64748b;
}

.bigscreen-container.light .feed-pos-tag {
  background: #ecfdf5;
  border-color: #a7f3d0;
  color: #059669;
}

.bigscreen-container.light .weekly-countdown-badge {
  color: #0284c7;
  background: rgba(2, 132, 199, 0.1);
  border-color: rgba(2, 132, 199, 0.28);
  box-shadow: none;
}

.bigscreen-container.light .weekly-countdown-badge.paused {
  color: #64748b;
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.bigscreen-container.light .countdown-pulse-dot {
  background: #0284c7;
  box-shadow: 0 0 4px #0284c7;
}

.bigscreen-container.light .weekly-kpi-card.ship-card {
  background: #ffffff;
  border-color: rgba(2, 132, 199, 0.3);
  border-left: 3px solid #0284c7;
}

.bigscreen-container.light .weekly-kpi-card.usage-card {
  background: #ffffff;
  border-color: rgba(217, 119, 6, 0.3);
  border-left: 3px solid #d97706;
}

.bigscreen-container.light .weekly-kpi-card.fit-usage-card {
  background: #ffffff;
  border-color: rgba(5, 150, 105, 0.3);
  border-left: 3px solid #059669;
}

.bigscreen-container.light .kpi-main-val.emerald-text { color: #059669; text-shadow: none; }

.bigscreen-container.light .weekly-chart-box {
  background: #ffffff;
  border-color: rgba(226, 232, 240, 0.9);
}

.bigscreen-container.light .weekly-chart-heading {
  color: #334155;
}

.bigscreen-container.light .weekly-empty-state {
  background: rgba(255, 255, 255, 0.88);
}

.bigscreen-container.light .weekly-empty-state strong,
.bigscreen-container.light .weekly-insight-grid strong {
  color: #334155;
}

.bigscreen-container.light .weekly-empty-state span {
  color: #64748b;
}

.bigscreen-container.light .weekly-insight-grid,
.bigscreen-container.light .weekly-insight-grid > div {
  border-color: rgba(203, 213, 225, 0.8);
}

.bigscreen-container.light .kpi-title {
  color: #64748b;
}

.bigscreen-container.light .kpi-sub-desc {
  color: #64748b;
}

.bigscreen-container.light .kpi-sub-desc .num {
  color: #0f172a;
}

.bigscreen-container.light .kpi-main-val.cyan-text { color: #0284c7; text-shadow: none; }
.bigscreen-container.light .kpi-main-val.gold-text { color: #d97706; text-shadow: none; }

.bigscreen-container.light .legend-indicator.ship { background: #0284c7; }
.bigscreen-container.light .legend-indicator.usage { background: #d97706; }

.bigscreen-container.light .chart-grid-lines .grid-line {
  stroke: rgba(203, 213, 225, 0.6);
}

.bigscreen-container.light .chart-grid-lines .grid-line.base {
  stroke: rgba(148, 163, 184, 0.8);
}

.bigscreen-container.light .chart-dot.ship {
  fill: #0284c7;
  stroke: #ffffff;
  filter: drop-shadow(0 0 2px rgba(2, 132, 199, 0.4));
}

.bigscreen-container.light .chart-dot.usage {
  fill: #d97706;
  stroke: #ffffff;
  filter: drop-shadow(0 0 2px rgba(217, 119, 6, 0.4));
}

.bigscreen-container.light .chart-x-axis .chart-x-label {
  fill: #475569;
}

.bigscreen-container.light .chart-x-axis .chart-x-sublabel {
  fill: #94a3b8;
}

.bigscreen-container.light .chart-x-axis .chart-x-label.active,
.bigscreen-container.light .chart-x-axis .chart-x-sublabel.active {
  fill: #0284c7;
}

.bigscreen-container.light .chart-tooltip-bubble {
  background: #ffffff;
  border-color: #cbd5e1;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.15);
}

.bigscreen-container.light .tooltip-date {
  color: #0f172a;
  border-bottom-color: #e2e8f0;
}

.bigscreen-container.light .supply-node-card.is-shipping-source {
  border-color: #0284c7;
  background: linear-gradient(135deg, rgba(2, 132, 199, 0.12) 0%, #ffffff 80%);
  box-shadow: 0 0 18px rgba(2, 132, 199, 0.45);
}

.bigscreen-container.light .supply-node-card.is-shipping-source.mat-fitting {
  border-color: #d97706;
  background: linear-gradient(135deg, rgba(217, 119, 6, 0.12) 0%, #ffffff 80%);
  box-shadow: 0 0 18px rgba(217, 119, 6, 0.45);
}

.bigscreen-container.light .demand-node-card.is-event-target.event-cat-dispatch {
  border-color: #0284c7;
  background: linear-gradient(135deg, rgba(2, 132, 199, 0.12) 0%, #ffffff 70%);
  box-shadow: 0 0 20px rgba(2, 132, 199, 0.5);
}

.bigscreen-container.light .demand-node-card.is-event-target.event-cat-dispatch.event-mat-fitting {
  border-color: #d97706;
  background: linear-gradient(135deg, rgba(217, 119, 6, 0.12) 0%, #ffffff 70%);
  box-shadow: 0 0 20px rgba(217, 119, 6, 0.5);
}

.bigscreen-container.light .demand-node-card.is-event-target.event-cat-arrival {
  border-color: #2563eb;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12) 0%, #ffffff 70%);
  box-shadow: 0 0 20px rgba(37, 99, 235, 0.5);
}

.bigscreen-container.light .demand-node-card.is-event-target.event-cat-arrival.event-mat-fitting {
  border-color: #d97706;
  background: linear-gradient(135deg, rgba(217, 119, 6, 0.12) 0%, #ffffff 70%);
  box-shadow: 0 0 20px rgba(217, 119, 6, 0.5);
}

.bigscreen-container.light .demand-node-card.is-event-target.event-cat-usage {
  border-color: #059669;
  background: linear-gradient(135deg, rgba(5, 150, 105, 0.12) 0%, #ffffff 70%);
  box-shadow: 0 0 20px rgba(5, 150, 105, 0.55);
}

.bigscreen-container.light .demand-node-card.is-event-target.event-cat-plan {
  border-color: #d97706;
  background: linear-gradient(135deg, rgba(217, 119, 6, 0.12) 0%, #ffffff 70%);
  box-shadow: 0 0 20px rgba(217, 119, 6, 0.55);
}

.bigscreen-container.light .feed-card.is-active-feed {
  background: linear-gradient(135deg, rgba(2, 132, 199, 0.1) 0%, #ffffff 100%);
  border-color: #0284c7;
  box-shadow: 0 0 14px rgba(2, 132, 199, 0.3);
}

.bigscreen-container.light .feed-card.is-active-feed.mat-fitting,
.bigscreen-container.light .feed-card.is-active-feed.is-fitting-event {
  background: linear-gradient(135deg, rgba(217, 119, 6, 0.1) 0%, #ffffff 100%);
  border-color: #d97706;
  box-shadow: 0 0 14px rgba(217, 119, 6, 0.35);
}

.bigscreen-container.light .feed-card.is-active-feed.usage {
  background: linear-gradient(135deg, rgba(5, 150, 105, 0.1) 0%, #ffffff 100%);
  border-color: #059669;
  box-shadow: 0 0 14px rgba(5, 150, 105, 0.35);
}

.bigscreen-container.light .feed-card.is-active-feed.plan {
  background: linear-gradient(135deg, rgba(225, 29, 72, 0.1) 0%, #ffffff 100%);
  border-color: #e11d48;
  box-shadow: 0 0 14px rgba(225, 29, 72, 0.35);
}

/* --- 关键帧动画 Keyframes --- */
@keyframes pulse-ring {
  0% {
    opacity: 0.8;
  }
  50% {
    opacity: 0.2;
  }
  100% {
    opacity: 0.8;
  }
}

/* --- 响应式适配 Responsive Layout --- */
@media (max-width: 1680px) {
  .badge-desktop-prefix {
    display: none;
  }
}

@media (max-width: 1440px) {
  .topology-layout-grid {
    grid-template-columns: clamp(110px, 23%, 220px) 24px 1fr;
    padding: 8px 12px;
  }
  .supply-node-card {
    padding: 8px 11px;
    min-height: 54px;
  }
  .sup-title {
    font-size: 12.5px;
  }
  .demand-systems-split {
    gap: 10px;
    padding: 2px;
  }
  .demand-node-card {
    padding: 5px 8px;
  }
}

@media (max-width: 1200px) {
  .bigscreen-content {
    grid-template-columns: 290px 1fr 320px;
    gap: 10px;
    padding: 8px 12px;
  }
  .topology-layout-grid {
    grid-template-columns: clamp(100px, 22%, 180px) 20px 1fr;
    padding: 6px 8px;
  }
  .supply-node-card {
    padding: 6px 8px;
    min-height: 48px;
  }
  .sup-title {
    font-size: 11.5px;
  }
  .demand-systems-split {
    gap: 8px;
    padding: 1px 2px;
  }
  .demand-node-card {
    padding: 4px 6px;
    gap: 3px;
  }
}

/* --- 🖥️ 垂直高度受限屏幕 / 非全屏模式弹性压缩适配 (max-height: 880px / 720px) --- */
@media (max-height: 880px) and (min-width: 901px) {
  .bigscreen-header {
    height: 56px;
    min-height: 56px;
    max-height: 56px;
  }
  .header-left {
    bottom: 12px;
  }
  .bigscreen-content {
    height: calc(100vh - 56px);
    padding: 8px 14px 10px;
    gap: 10px;
  }
  .left-col {
    gap: 6px;
  }
  .left-col .weather-kpi-panel {
    padding: 6px 10px;
  }
  .left-col .weather-loc-bar {
    margin-bottom: 4px;
    font-size: 11px;
  }
  .left-col .weather-metrics-row {
    padding: 6px 10px;
  }
  .left-col .weather-temp-block {
    gap: 6px;
  }
  .left-col .temp-degree {
    font-size: 20px;
  }
  .left-col .weather-name {
    font-size: 11.5px;
  }
  .left-col .weather-forecast-subrow {
    font-size: 10px;
    margin-top: 3px;
  }
  .left-col .pipe-kpi-panel,
  .left-col .fitting-kpi-panel,
  .left-col .safety-panel {
    padding: 6px 10px;
  }
  .left-col .panel-header {
    margin-bottom: 4px;
  }
  .left-col .kpi-metric-grid {
    gap: 4px;
    margin-bottom: 4px;
  }
  .left-col .metric-item {
    padding: 3px 6px;
    border-radius: 4px;
  }
  .left-col .metric-label {
    font-size: 10px;
  }
  .left-col .metric-capsule {
    font-size: 9px;
    padding: 0.5px 3px;
  }
  .left-col .metric-val .num.hero-num {
    font-size: 16px;
  }
  .left-col .metric-val .num {
    font-size: 14px;
  }
  .left-col .metric-val .unit {
    font-size: 9.5px;
  }
  .left-col .energy-progress-box {
    padding-top: 2px;
  }
  .left-col .energy-progress-info {
    font-size: 10.5px;
    margin-bottom: 2px;
  }
  .left-col .energy-bar-track {
    height: 6.5px;
  }
  .left-col .safety-grid {
    gap: 4px;
  }
  .left-col .safety-card {
    padding: 3px 6px;
    gap: 5px;
  }
  .left-col .safety-icon {
    font-size: 14px;
  }
  .left-col .safety-val {
    font-size: 12px;
  }
  .left-col .safety-desc {
    font-size: 9.5px;
  }

  /* 中间供需拓扑标段卡片压缩 */
  .system-cards-list {
    gap: 4px;
    padding: 1px;
  }
  .demand-node-card {
    padding: 5px 8px;
    gap: 3px;
    border-radius: 5px;
  }
  .sec-sys-badge {
    font-size: 9.5px;
    padding: 0.5px 3px;
  }
  .sec-title {
    font-size: 11.5px;
  }
  .sec-status-chip {
    font-size: 9.5px;
    padding: 1px 5px;
  }
  .sec-metrics-body {
    gap: 3px;
  }
  .line-info {
    font-size: 9.5px;
  }
  .line-label {
    font-size: 9px;
    padding: 0px 3px;
  }
  .line-val {
    font-size: 9.5px;
  }
  .line-pct {
    font-size: 9.5px;
    min-width: 26px;
  }
  .micro-bar-bg {
    height: 6px;
  }

  /* 供给基地卡片压缩 */
  .supply-cards-stack {
    gap: 8px;
  }
  .supply-node-card {
    padding: 8px 12px;
    min-height: 50px;
  }
  .sup-title {
    font-size: 12px;
  }

  /* 右侧战报与本周看板 */
  .weekly-report-panel {
    padding: 8px 10px 6px;
  }
  .weekly-kpi-grid {
    gap: 5px;
    margin-bottom: 5px;
  }
  .weekly-kpi-card {
    min-height: 56px;
    padding: 4px 8px;
  }
  .weekly-kpi-card .kpi-main-val {
    font-size: 16px;
  }
  .weekly-insight-grid {
    padding-top: 4px;
    margin-top: 4px;
  }
}

@media (max-height: 720px) and (min-width: 901px) {
  .bigscreen-header {
    height: 48px;
    min-height: 48px;
    max-height: 48px;
  }
  .header-left {
    bottom: 8px;
  }
  .header-title {
    font-size: 16px;
  }
  .bigscreen-content {
    height: calc(100vh - 48px);
    padding: 6px 10px 8px;
    gap: 8px;
  }
  .left-col .metric-val .num.hero-num {
    font-size: 14.5px;
  }
  .left-col .metric-val .num {
    font-size: 13px;
  }
  .demand-node-card {
    padding: 4px 6px;
    gap: 2px;
  }
  .sec-title {
    font-size: 11px;
  }
  .micro-bar-bg {
    height: 5px;
  }
}

/* 📱 移动端与平板竖屏全量适配 (<= 900px) */
@media (max-width: 900px) {
  .bigscreen-container {
    height: 100%;
    min-height: 100dvh;
    max-height: none;
    overflow-x: hidden;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }

  /* 顶栏紧凑高质感化 */
  .bigscreen-header {
    height: 64px;
    min-height: 64px;
    max-height: 64px;
    padding: 0 12px;
    gap: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .header-left {
    min-width: auto;
    gap: 6px;
    flex-shrink: 0;
  }

  .header-badge {
    padding: 3px 8px;
    font-size: 11px;
    gap: 5px;
  }

  .badge-desktop-prefix {
    display: none;
  }

  .header-time {
    display: none;
  }

  .header-title-box {
    position: static;
    transform: none;
    flex: 1;
    text-align: center;
    padding: 0 4px;
    overflow: hidden;
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .title-desktop {
    display: none;
  }

  .title-mobile {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    width: 100%;
  }

  .title-mobile-line1 {
    font-size: 11.5px;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.8px;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }

  .title-mobile-line2 {
    font-size: 14.5px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
    line-height: 1.25;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
    text-shadow: 0 0 14px rgba(0, 242, 254, 0.6);
  }

  .header-title {
    font-size: 14.5px;
    letter-spacing: 0.5px;
    line-height: 1.2;
    margin: 0;
    width: 100%;
  }

  .header-right {
    flex-shrink: 0;
  }

  .control-trigger-btn {
    padding: 5px 9px;
    font-size: 11.5px;
    gap: 4px;
    border-radius: 16px;
  }

  .control-trigger-btn .btn-text {
    display: none;
  }

  .control-trigger-btn .mini-live-tag {
    display: inline-block;
    padding: 0 4px;
    font-size: 9px;
  }

  /* 控制中心浮层在移动端自适应全屏弹窗 */
  .control-menu-popover {
    position: fixed !important;
    top: 60px !important;
    left: 12px !important;
    right: 12px !important;
    width: auto !important;
    max-width: 480px !important;
    max-height: calc(100dvh - 80px) !important;
    overflow-y: auto !important;
    -webkit-overflow-scrolling: touch !important;
    margin: 0 auto !important;
    border-radius: 14px !important;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.9), 0 0 20px rgba(0, 242, 254, 0.25) !important;
    z-index: 2000 !important;
  }

  /* 显现移动端导航选项卡 */
  .mobile-nav-tabs {
    display: flex;
  }

  /* 主内容区改为单列流式结构 */
  .bigscreen-content {
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: calc(100dvh - 100px);
    padding: 10px 10px 24px;
    gap: 12px;
    overflow: visible;
  }

  /* 默认隐藏未激活的列，仅显示当前 Tab 对应的列 (或全览模式全部显示) */
  .screen-col {
    display: none !important;
    width: 100%;
    height: auto;
    min-height: 0;
    overflow: visible;
    gap: 12px;
    flex: none;
  }

  .screen-col.mobile-active-col {
    display: flex !important;
  }

  /* 1. 左侧指标大盘移动端调优 (仅在激活时呈现自然流式展开) */
  .left-col {
    display: none !important;
    padding-right: 0;
    overflow-y: visible;
    gap: 14px;
  }

  .left-col.mobile-active-col {
    display: flex !important;
    flex-direction: column !important;
    height: auto !important;
    min-height: auto !important;
    max-height: none !important;
    flex: none !important;
    justify-content: flex-start !important;
    padding-right: 0 !important;
    overflow: visible !important;
    gap: 10px !important;
  }

  .left-col .panel-box,
  .left-col .weather-kpi-panel,
  .left-col .pipe-kpi-panel,
  .left-col .fitting-kpi-panel,
  .left-col .safety-panel {
    flex: none !important;
    height: auto !important;
    min-height: auto !important;
    max-height: none !important;
    justify-content: flex-start !important;
    padding: 10px 12px !important;
    border-radius: 10px !important;
    background: linear-gradient(180deg, rgba(17, 28, 48, 0.92) 0%, rgba(11, 20, 36, 0.98) 100%) !important;
    border: 1px solid rgba(0, 242, 254, 0.22) !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35) !important;
  }

  .left-col .panel-header {
    margin-bottom: 8px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    flex-shrink: 0 !important;
  }

  .left-col .panel-title {
    font-size: 14px !important;
    font-weight: 700 !important;
    gap: 6px !important;
  }

  .left-col .panel-tag {
    font-size: 10.5px !important;
    padding: 1.5px 6px !important;
    border-radius: 4px !important;
  }

  /* 天气面板手机端专属适配 (紧凑缩减20%) */
  .left-col .weather-loc-bar {
    font-size: 11.5px !important;
    margin-bottom: 6px !important;
  }

  .left-col .weather-metrics-row {
    padding: 8px 10px !important;
    border-radius: 8px !important;
    background: rgba(15, 23, 42, 0.85) !important;
    border: 1px solid rgba(0, 242, 254, 0.18) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
  }

  .left-col .weather-temp-block {
    gap: 8px !important;
  }

  .left-col .temp-degree {
    font-size: 24px !important;
    font-weight: 800 !important;
  }

  .left-col .weather-params-block {
    gap: 3px !important;
  }

  .left-col .param-item {
    font-size: 11.5px !important;
    gap: 6px !important;
  }

  .left-col .weather-forecast-subrow {
    font-size: 11px !important;
    margin-top: 6px !important;
    padding-top: 6px !important;
    line-height: 1.3 !important;
    flex-wrap: wrap !important;
  }

  /* 2×2 KPI 指标卡片手机端专属适配 (高度与内边距缩减20%) */
  .left-col .kpi-metric-grid {
    flex: none !important;
    height: auto !important;
    min-height: auto !important;
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 7px !important;
    margin-bottom: 8px !important;
  }

  .left-col .metric-item {
    flex: none !important;
    padding: 8px 10px !important;
    border-radius: 8px !important;
    background: rgba(15, 25, 45, 0.92) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    min-height: 60px !important;
    box-sizing: border-box !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
  }

  .left-col .metric-label-box {
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: 4px !important;
    width: 100% !important;
    margin-bottom: 2px !important;
  }

  .left-col .metric-label {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
  }

  .left-col .metric-capsule {
    font-size: 9.5px !important;
    font-weight: 700 !important;
    padding: 1px 4px !important;
    border-radius: 4px !important;
    flex-shrink: 0 !important;
    white-space: nowrap !important;
  }

  .left-col .metric-val {
    display: flex !important;
    align-items: baseline !important;
    justify-content: flex-start !important;
    margin-top: 1px !important;
    gap: 2px !important;
  }

  .left-col .metric-val .num.hero-num,
  .left-col .metric-val .num {
    font-size: 20px !important;
    font-weight: 800 !important;
    font-family: 'DIN Alternate', 'JetBrains Mono', 'Consolas', monospace !important;
    line-height: 1.1 !important;
  }

  .left-col .metric-val .unit {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #64748b !important;
    margin-left: 2px !important;
  }

  /* 充能进度条 */
  .left-col .energy-progress-box {
    flex: none !important;
    height: auto !important;
    margin-top: 2px !important;
    padding-top: 6px !important;
    border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
  }

  .left-col .energy-progress-info {
    font-size: 12px !important;
    font-weight: 700 !important;
    margin-bottom: 3px !important;
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
  }

  .left-col .energy-bar-track {
    height: 7.5px !important;
    border-radius: 4px !important;
    background: rgba(255, 255, 255, 0.12) !important;
  }

  /* 安全效能保障卡片 (高度缩减20%) */
  .left-col .safety-grid {
    flex: none !important;
    height: auto !important;
    min-height: auto !important;
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 7px !important;
  }

  .left-col .safety-card {
    flex: none !important;
    min-height: 50px !important;
    padding: 7px 10px !important;
    border-radius: 8px !important;
    background: rgba(15, 25, 45, 0.92) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    box-sizing: border-box !important;
  }

  .left-col .safety-icon {
    font-size: 20px !important;
    line-height: 1 !important;
    flex-shrink: 0 !important;
  }

  .left-col .safety-info {
    display: flex !important;
    flex-direction: column !important;
    gap: 1px !important;
    min-width: 0 !important;
  }

  .left-col .safety-val {
    font-size: 15px !important;
    font-weight: 800 !important;
    font-family: 'DIN Alternate', 'JetBrains Mono', monospace !important;
    color: #00ff87 !important;
    line-height: 1.15 !important;
  }

  .left-col .safety-desc {
    font-size: 10.5px !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
  }

  /* 2. 中间供需拓扑移动端调优 (根治卡片压扁与重叠，支持 2D 平滑手势滑动) */
  .center-col {
    display: none !important;
    height: calc(100dvh - 110px);
    min-height: 540px;
    overflow: hidden;
  }

  .center-col.mobile-active-col {
    display: flex !important;
    flex-direction: column !important;
  }

  .bigscreen-content.mobile-tab-topology .map-topology-master-panel,
  .mobile-tab-topology .map-topology-master-panel {
    height: 100% !important;
    flex: 1 !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
  }

  .bigscreen-content.mobile-tab-topology .topology-container,
  .mobile-tab-topology .topology-container {
    flex: 1 !important;
    height: 100% !important;
    min-height: 460px !important;
    overflow: auto !important;
    -webkit-overflow-scrolling: touch !important;
    position: relative !important;
  }

  .map-topology-master-panel {
    height: 100%;
    flex: 1;
    min-height: 0;
    padding: 10px;
  }

  .mobile-topo-scroll-hint {
    display: block;
  }

  .topology-container {
    flex: 1;
    min-height: 0;
    overflow: auto !important;
    -webkit-overflow-scrolling: touch;
    position: relative;
    border-radius: 6px;
  }

  .topology-layout-grid {
    min-width: 860px;
    min-height: 780px;
    width: 100%;
    height: 100%;
    grid-template-columns: 220px 38px 1fr;
    padding: 12px 14px;
    box-sizing: border-box;
  }

  .topology-svg {
    min-width: 860px;
    min-height: 780px;
    width: 100%;
    height: 100%;
  }

  .supply-cards-stack {
    gap: 16px;
    padding: 2px 0;
    height: 100%;
    min-height: 740px;
    justify-content: space-around;
    box-sizing: border-box;
  }

  .supply-node-card {
    min-height: 96px;
    flex: 1 0 96px;
    padding: 12px 14px;
    box-sizing: border-box;
  }

  /* 📱 移动端与触屏模式：彻底消除触碰导致的卡片压暗变黑与粘滞位移 */
  .supply-node-card.dimmed,
  .demand-node-card.dimmed {
    opacity: 1 !important;
  }

  .supply-node-card:hover,
  .supply-node-card.hovered,
  .demand-node-card:hover,
  .demand-node-card.highlighted {
    transform: none !important;
  }

  .sup-title {
    font-size: 13px;
  }

  .demand-systems-split {
    gap: 14px;
    height: 100%;
    min-height: 740px;
    box-sizing: border-box;
  }

  .system-sub-col {
    height: 100%;
    min-height: 740px;
  }

  .system-cards-list {
    gap: 10px;
    padding: 2px 0;
    height: 100%;
    min-height: 740px;
    justify-content: space-between;
    box-sizing: border-box;
  }

  .demand-node-card {
    min-height: 146px;
    flex: 1 0 146px;
    padding: 6px 10px;
    gap: 4px;
    box-sizing: border-box;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .sec-card-header {
    height: 22px;
    flex-shrink: 0;
    margin-bottom: 2px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .sec-badge-name {
    display: flex;
    align-items: center;
    gap: 5px;
    min-width: 0;
    flex: 1;
  }

  .sec-sys-badge {
    font-size: 10.5px;
    padding: 1px 5px;
    flex-shrink: 0;
  }

  .sec-title {
    font-size: 13px;
    font-weight: 700;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sec-status-chip {
    font-size: 10px;
    padding: 1px 6px;
    flex-shrink: 0;
  }

  .sec-metrics-body {
    display: flex;
    flex-direction: column;
    gap: 3.5px;
    flex: 1;
    justify-content: space-around;
    min-height: 0;
  }

  .sec-metric-line {
    display: flex;
    flex-direction: column;
    gap: 1.5px;
    flex-shrink: 0;
  }

  .sec-metric-line .line-info {
    font-size: 11px;
    line-height: 1.2;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    white-space: nowrap;
    width: 100%;
  }

  .sec-metric-line .line-label {
    font-size: 10.5px;
    padding: 1px 4px;
    flex-shrink: 0;
    border-radius: 3px;
    white-space: nowrap;
  }

  .sec-metric-line .line-val {
    font-size: 11.5px;
    font-weight: 600;
    flex: 1;
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .sec-metric-line .line-pct {
    font-size: 11.5px;
    font-weight: 800;
    flex-shrink: 0;
    min-width: 34px;
    text-align: right;
  }

  .micro-bar-bg {
    height: 5px;
    border-radius: 3px;
    flex-shrink: 0;
  }

  /* 📱 移动端专属：现场库存微核算条显式保障 */
  .demand-node-card .sec-stock-strip {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 2px 6px !important;
    margin-top: 1px !important;
    font-size: 9.5px !important;
    line-height: 1.2 !important;
    border-radius: 4px !important;
    flex-shrink: 0 !important;
    box-sizing: border-box !important;
  }

  .demand-node-card .sec-stock-strip .stock-item {
    display: flex !important;
    align-items: center !important;
    gap: 3px !important;
    min-width: 0 !important;
  }

  .demand-node-card .sec-stock-strip .stock-label {
    font-size: 9.5px !important;
    white-space: nowrap !important;
    color: #94a3b8 !important;
  }

  .demand-node-card .sec-stock-strip .stock-val {
    font-size: 10.5px !important;
    font-weight: 700 !important;
    white-space: nowrap !important;
  }

  .transit-channel-col .channel-text {
    font-size: 9px;
  }

  /* 3. 右侧实时动态与成果榜移动端调优 */
  .right-col {
    display: none !important;
    overflow: visible;
  }

  .right-col.mobile-active-col {
    display: flex !important;
    flex-direction: column !important;
  }

  .live-feed-panel {
    flex: none;
    min-height: 380px;
  }

  .feed-list-wrapper {
    max-height: 480px;
    padding: 2px 4px;
  }

  .weekly-report-panel {
    flex: none !important;
    height: auto !important;
    min-height: auto !important;
    max-height: none !important;
    padding: 12px 14px 10px !important;
  }

  .weekly-chart-box {
    height: 240px !important;
    min-height: 220px !important;
    max-height: none !important;
  }

  .weekly-kpi-grid {
    gap: 6px;
  }

  .weekly-kpi-card {
    padding: 5px 8px;
  }

  .kpi-main-val {
    font-size: 15px;
  }
}

/* 📱 超窄小屏手机深度优化 (<= 480px) */
@media (max-width: 480px) {
  .weekly-insight-grid span {
    font-size: 8.5px;
  }
  .weekly-insight-grid strong {
    font-size: 9.5px;
  }

  .bigscreen-header {
    padding: 0 8px;
  }

  .header-badge {
    padding: 2px 5px;
    font-size: 10.5px;
  }

  .title-mobile-line1 {
    font-size: 10.5px;
    letter-spacing: 0.4px;
  }

  .title-mobile-line2 {
    font-size: 13px;
    letter-spacing: 0.3px;
  }

  .mobile-tab-btn {
    font-size: 12px;
    gap: 3px;
  }

  .mobile-tab-btn .tab-icon {
    font-size: 13px;
  }

  .kpi-metric-grid {
    grid-template-columns: 1fr 1fr;
  }

  .metric-val .num {
    font-size: 15.5px;
  }

  .fitting-types-pills {
    gap: 4px;
  }

  .fitting-pill {
    padding: 3px 6px;
    font-size: 10.5px;
  }
}

/* 📱 触屏设备（无鼠标精确指针设备）：彻底消除悬停导致的卡片压暗与伪类位移 */
@media (hover: none) {
  .supply-node-card.dimmed,
  .demand-node-card.dimmed {
    opacity: 1 !important;
  }

  .supply-node-card:hover,
  .supply-node-card.hovered,
  .demand-node-card:hover,
  .demand-node-card.highlighted {
    transform: none !important;
  }
}
</style>
