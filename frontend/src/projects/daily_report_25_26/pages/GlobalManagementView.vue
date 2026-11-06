<template>
  <div class="tube-page-root dr-global-mgmt-view">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <!-- 高级控制台顶栏 -->
      <header class="topbar premium-topbar">
        <div>
          <h2>生产日报子项目 · 全局管理控制台</h2>
          <p class="sub">统一管控供热生产指标与算法体系、供暖期核心参数、常量价格基准与底层计算引擎。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost btn-back" type="button" @click="goProjectPages">⬅️ 返回功能页</button>
          <button class="btn ghost" type="button" :disabled="loading" @click="refreshAll">
            {{ loading ? '同步配置中…' : '🔄 刷新全局状态' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>
      <p v-if="globalTip" :class="['page-tip', globalTip.type]">{{ globalTip.text }}</p>

      <!-- 磨砂玻璃态全局数据看板 (Quick Dashboard) -->
      <section class="card elevated quick-dashboard-card">
        <div class="meta-dashboard">
          <div class="meta-card">
            <span class="meta-label">核心算法指标</span>
            <strong class="meta-value">{{ catalogList.length || 69 }} 项收录</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">业务分类大类</span>
            <strong class="meta-value">{{ categories.length || 7 }} 大领域</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">底层计算引擎</span>
            <strong class="meta-value highlight-num">DailyDashboardEngine (0.1s)</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">当前运行供暖期</span>
            <strong class="meta-value">{{ currentSeasonCode || '25-26期' }}</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">基准业务日期</span>
            <strong class="meta-value">{{ currentBizDate || '加载中…' }}</strong>
          </div>
        </div>
      </section>

      <!-- 纵向双栏侧边控制台 -->
      <div class="admin-workbench-layout">
        <!-- 移动端专属快捷功能板块切换器 (仅在手机窄屏显示) -->
        <div class="mobile-tab-switcher">
          <div class="switcher-header">
            <span class="switcher-title">⚙️ 当前管理板块</span>
            <span class="switcher-hint">可下拉选择 / 下方支持左右横滑</span>
          </div>
          <div class="mobile-select-wrap">
            <select v-model="activeTab" class="mobile-tab-select" @change="onMobileSelectChange">
              <option value="algorithms">🧮 生产指标与算法体系</option>
              <option value="season_params">⚙️ 供暖期与时间参数</option>
              <option value="kdocs_complaint">📋 12345投诉底表(金山文档)</option>
              <option value="constants">📊 常量指标与价格基准</option>
              <option value="entities">🏢 供热单位与组织架构</option>
              <option value="weather_mgmt">⛅ 气温与气象数据管理</option>
              <option value="raw_config">💻 原始配置结构预览</option>
            </select>
            <span class="select-arrow-icon">▼</span>
          </div>
        </div>

        <!-- 选项卡菜单 (桌面端纵向侧栏 / 移动端横向平滑滚动胶囊栏) -->
        <aside class="admin-sidebar" ref="sidebarRef">
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'algorithms' }]"
            @click="selectTab('algorithms', $event)"
          >
            🧮 生产指标与算法体系
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'season_params' }]"
            @click="selectTab('season_params', $event)"
          >
            ⚙️ 供暖期与时间参数
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'kdocs_complaint' }]"
            @click="selectTab('kdocs_complaint', $event)"
          >
            📋 12345投诉底表(金山文档)
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'constants' }]"
            @click="selectTab('constants', $event)"
          >
            📊 常量指标与价格基准
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'entities' }]"
            @click="selectTab('entities', $event)"
          >
            🏢 供热单位与组织架构
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'weather_mgmt' }]"
            @click="selectTab('weather_mgmt', $event)"
          >
            ⛅ 气温与气象数据管理
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'raw_config' }]"
            @click="selectTab('raw_config', $event)"
          >
            💻 原始配置结构预览
          </button>
        </aside>

        <!-- 右侧当前选中的配置主卡片 -->
        <div class="admin-content-pane">
          <!-- ========================================== -->
          <!-- Tab 1: 🧮 生产指标与算法体系 (首发核心功能) -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'algorithms'" class="pane-content-wrapper">
            <!-- 检索与分类筛选工具栏 -->
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">🧮 供热生产指标与算法体系字典</div>
                  <p class="sub block-sub">
                    收口纯 Python 高性能计算引擎（heating_metrics）中的全部核心指标算法、分子分母构成、底表依赖与内部交易抵消机制。
                  </p>
                </div>
                <div class="section-actions">
                  <div class="view-mode-toggle">
                    <button
                      type="button"
                      :class="['btn ghost compact-btn', { active: viewMode === 'cards' }]"
                      @click="viewMode = 'cards'"
                    >
                      🗂️ 卡片视图
                    </button>
                    <button
                      type="button"
                      :class="['btn ghost compact-btn', { active: viewMode === 'table' }]"
                      @click="viewMode = 'table'"
                    >
                      📑 紧凑表格
                    </button>
                  </div>
                </div>
              </div>

              <!-- 搜索与大类筛选 -->
              <div class="filter-toolbar">
                <div class="search-box">
                  <span class="search-icon">🔍</span>
                  <input
                    v-model.trim="searchKeyword"
                    type="text"
                    class="input search-input"
                    placeholder="输入指标中文名、英文 Key（如 rate_std）、单位或公式关键字过滤…"
                  />
                  <button v-if="searchKeyword" class="btn-clear" type="button" @click="searchKeyword = ''">✕</button>
                </div>

                <div class="filter-dropdowns">
                  <select v-model="selectedScopeFilter" class="input scope-select">
                    <option value="all">适用主体: 全部单位</option>
                    <option value="plant">适用主体: 仅热电厂</option>
                    <option value="heating">适用主体: 仅供热分公司</option>
                    <option value="group">适用主体: 集团/主城区汇总</option>
                  </select>

                  <select v-model="selectedDerivedFilter" class="input derived-select">
                    <option value="all">指标属性: 全部</option>
                    <option value="derived">指标属性: 仅引擎派生计算项</option>
                    <option value="base">指标属性: 仅基础申报项</option>
                  </select>
                </div>
              </div>

              <!-- 分类标签胶囊列表 -->
              <div class="category-pills">
                <button
                  v-for="cat in categories"
                  :key="cat.key"
                  type="button"
                  :class="['category-pill', { active: activeCategoryKey === cat.key }]"
                  @click="activeCategoryKey = cat.key"
                >
                  <span class="pill-icon">{{ cat.icon }}</span>
                  <span class="pill-name">{{ cat.name }}</span>
                  <span class="pill-count">({{ getCategoryCount(cat.key) }})</span>
                </button>
              </div>
            </section>

            <!-- A. 卡片视图 -->
            <section v-if="viewMode === 'cards'" class="catalog-cards-container">
              <div v-if="filteredCatalog.length === 0" class="panel-state empty-state">
                未找到匹配的算法指标
              </div>
              <div v-else class="catalog-grid">
                <div
                  v-for="item in filteredCatalog"
                  :key="item.item"
                  class="card elevated metric-card"
                  :class="getCategoryClass(item.category_key)"
                >
                  <div class="metric-card-header">
                    <div class="metric-title-wrap">
                      <span class="category-badge">{{ item.category_cn }}</span>
                      <h4 class="metric-name">{{ item.item_cn }}</h4>
                    </div>
                    <span v-if="item.unit" class="unit-badge">{{ item.unit }}</span>
                  </div>

                  <div class="metric-key-bar">
                    <code class="metric-key" title="点击复制英文标识" @click="copyKey(item.item)">
                      {{ item.item }}
                    </code>
                    <button class="btn-copy-icon" type="button" title="复制" @click="copyKey(item.item)">
                      📋
                    </button>
                    <span v-if="copiedKey === item.item" class="copy-success-tip">已复制!</span>
                  </div>

                  <!-- 数学公式展示区 -->
                  <div class="formula-box">
                    <span class="formula-label">数学公式与规则：</span>
                    <div class="formula-code">{{ item.formula_display }}</div>
                  </div>

                  <p class="metric-desc">{{ item.formula_description }}</p>

                  <div class="metric-meta-details">
                    <div class="meta-row">
                      <span class="row-label">数据依赖:</span>
                      <span class="row-val">{{ formatDependencies(item.dependencies) }}</span>
                    </div>
                    <div class="meta-row">
                      <span class="row-label">适用范围:</span>
                      <span class="row-val">{{ item.applicable_scope }}</span>
                    </div>
                    <div v-if="item.special_rules" class="meta-row special-rule-row">
                      <span class="row-label">特殊逻辑:</span>
                      <span class="row-val highlight-rule">{{ item.special_rules }}</span>
                    </div>
                    <div class="meta-row">
                      <span class="row-label">时态支持:</span>
                      <div class="time-tags">
                        <span v-for="w in item.time_windows" :key="w" class="time-tag">{{ w }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="card-footer-action">
                    <button class="btn ghost compact-btn sandbox-trigger-btn" type="button" @click="quickFillSandbox(item)">
                      🧪 载入沙盒实时验算 ➔
                    </button>
                  </div>
                </div>
              </div>
            </section>

            <!-- B. 紧凑表格视图 -->
            <section v-else class="card elevated section-card">
              <div class="mobile-table-hint">💡 提示：表格内容较宽，可左右横向滑动查看完整指标</div>
              <div class="table-wrap">
                <table class="table editor-table catalog-table">
                  <thead>
                    <tr>
                      <th style="width: 140px;">指标中文名称</th>
                      <th style="width: 170px;">英文标识 (Key)</th>
                      <th style="width: 70px;">单位</th>
                      <th style="width: 130px;">所属大类</th>
                      <th>数学公式与算法规则</th>
                      <th style="width: 160px;">适用主体</th>
                      <th style="width: 110px;">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in filteredCatalog" :key="item.item">
                      <td class="cell-text font-bold">{{ item.item_cn }}</td>
                      <td>
                        <div class="table-key-cell">
                          <code class="clickable-key" @click="copyKey(item.item)">{{ item.item }}</code>
                          <span v-if="copiedKey === item.item" class="copy-success-tip">✓</span>
                        </div>
                      </td>
                      <td><span class="unit-badge">{{ item.unit || '—' }}</span></td>
                      <td><span class="category-badge-table">{{ item.category_cn }}</span></td>
                      <td class="cell-formula">
                        <div class="formula-inline"><strong>{{ item.formula_display }}</strong></div>
                        <small class="formula-desc-inline">{{ item.formula_description }}</small>
                      </td>
                      <td class="cell-text text-sm">{{ item.applicable_scope }}</td>
                      <td>
                        <button class="btn ghost compact-btn" type="button" @click="quickFillSandbox(item)">
                          🧪 验算
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <!-- ========================================== -->
            <!-- 🧪 算法在线实时验算沙盒 (Live Sandbox)      -->
            <!-- ========================================== -->
            <section id="sandbox-section" class="card elevated section-card sandbox-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">🧪 算法在线实时验算沙盒 (Live Calculator Sandbox)</div>
                  <p class="sub block-sub">
                    选择具体业务日、生产单位与指标，直接由底层计算引擎实时解构输入参数、展开推导步骤并输出 8 窗口值与同比分析。
                  </p>
                </div>
              </div>

              <!-- 沙盒控制面板 -->
              <div class="sandbox-control-grid">
                <label class="field">
                  <span>业务日期 (biz_date)</span>
                  <div class="date-input-group">
                    <input v-model="sandboxDate" type="date" class="input" />
                    <button class="btn ghost compact-btn" type="button" @click="fillLatestBizDate">填入最新</button>
                  </div>
                </label>

                <label class="field">
                  <span>目标单位 (company)</span>
                  <select v-model="sandboxCompany" class="input">
                    <optgroup label="全集团与区域加权汇总">
                      <option value="Group">全集团全口径汇总 (Group)</option>
                      <option value="ZhuChengQu">主城区加权汇总 (ZhuChengQu)</option>
                    </optgroup>
                    <optgroup label="热电联产电厂">
                      <option value="BeiHai">北海热电厂 (BeiHai)</option>
                      <option value="JinZhou">金州热电 (JinZhou)</option>
                      <option value="BeiFang">北方热电 (BeiFang)</option>
                      <option value="JinPu">金普热电 (JinPu)</option>
                      <option value="ZhuangHe">庄河热电 (ZhuangHe)</option>
                    </optgroup>
                    <optgroup label="供热分公司与特区">
                      <option value="GongRe">供热分公司 (GongRe)</option>
                      <option value="XiangHai">香海热电厂 (XiangHai)</option>
                      <option value="YanJiuYuan">热力研究院 (YanJiuYuan)</option>
                    </optgroup>
                  </select>
                </label>

                <label class="field">
                  <span>验算指标 (item)</span>
                  <select v-model="sandboxItem" class="input">
                    <option v-for="m in catalogList" :key="m.item" :value="m.item">
                      {{ m.item_cn }} ({{ m.item }})
                    </option>
                  </select>
                </label>

                <div class="sandbox-action-wrap">
                  <button
                    class="btn primary shadow-accent execute-sandbox-btn"
                    type="button"
                    :disabled="sandboxLoading"
                    @click="executeSandbox"
                  >
                    {{ sandboxLoading ? '⚡ 正在实时运算…' : '⚡ 立即执行验算' }}
                  </button>
                </div>
              </div>

              <!-- 验算结果展示区 -->
              <div v-if="sandboxResult" class="sandbox-results-panel">
                <div class="result-headline-card">
                  <div class="headline-left">
                    <span class="indicator-badge">已完成演算</span>
                    <h3 class="headline-title">{{ sandboxResult.meta?.item_cn }} ({{ sandboxResult.meta?.item }})</h3>
                    <p class="headline-meta">
                      单位：<strong>{{ getCompanyName(sandboxResult.query?.company) }}</strong> ｜ 
                      业务日：<strong>{{ sandboxResult.query?.biz_date }}</strong> ({{ sandboxResult.query?.biz_period }}) ｜ 
                      历史同期：<strong>{{ sandboxResult.query?.peer_date }}</strong> ({{ sandboxResult.query?.peer_period }})
                    </p>
                  </div>
                  <div class="headline-right">
                    <span class="final-unit-pill">单位: {{ sandboxResult.meta?.unit || '—' }}</span>
                  </div>
                </div>

                <!-- 8 窗口结果矩阵卡片 -->
                <div class="matrix-8-windows">
                  <div class="window-card">
                    <div class="win-label">当日数值</div>
                    <div class="win-val">{{ formatVal(sandboxResult.results_8_windows?.value_biz_date) }}</div>
                    <div class="win-peer">同期: {{ formatVal(sandboxResult.results_8_windows?.value_peer_date) }}</div>
                    <div :class="['win-growth', getGrowthClass(sandboxResult.results_8_windows?.growth_daily)]">
                      同比: {{ sandboxResult.results_8_windows?.growth_daily }}
                    </div>
                  </div>

                  <div class="window-card">
                    <div class="win-label">7天滑动累计</div>
                    <div class="win-val">{{ formatVal(sandboxResult.results_8_windows?.sum_7d_biz) }}</div>
                    <div class="win-peer">同期: {{ formatVal(sandboxResult.results_8_windows?.sum_7d_peer) }}</div>
                    <div :class="['win-growth', getGrowthClass(sandboxResult.results_8_windows?.growth_7d)]">
                      同比: {{ sandboxResult.results_8_windows?.growth_7d }}
                    </div>
                  </div>

                  <div class="window-card">
                    <div class="win-label">本月累计</div>
                    <div class="win-val">{{ formatVal(sandboxResult.results_8_windows?.sum_month_biz) }}</div>
                    <div class="win-peer">同期: {{ formatVal(sandboxResult.results_8_windows?.sum_month_peer) }}</div>
                    <div :class="['win-growth', getGrowthClass(sandboxResult.results_8_windows?.growth_month)]">
                      同比: {{ sandboxResult.results_8_windows?.growth_month }}
                    </div>
                  </div>

                  <div class="window-card highlight-win">
                    <div class="win-label">全供暖期累计</div>
                    <div class="win-val">{{ formatVal(sandboxResult.results_8_windows?.sum_ytd_biz) }}</div>
                    <div class="win-peer">同期: {{ formatVal(sandboxResult.results_8_windows?.sum_ytd_peer) }}</div>
                    <div :class="['win-growth', getGrowthClass(sandboxResult.results_8_windows?.growth_ytd)]">
                      同比: {{ sandboxResult.results_8_windows?.growth_ytd }}
                    </div>
                  </div>
                </div>

                <!-- 推演步骤列表 -->
                <div class="derivation-steps-block">
                  <h4 class="steps-heading">📐 演算推导步骤与数据代入记录：</h4>
                  <div class="steps-timeline">
                    <div v-for="step in sandboxResult.steps" :key="step.step_no" class="timeline-step-item">
                      <div class="step-num-badge">{{ step.step_no }}</div>
                      <div class="step-content-box">
                        <div class="step-title">{{ step.title }}</div>
                        <p class="step-desc">{{ step.description }}</p>

                        <!-- 输入参数细项表 -->
                        <div v-if="step.breakdown && step.breakdown.length" class="step-breakdown-table-wrap">
                          <table class="table step-subtable">
                            <thead>
                              <tr>
                                <th>参数名称</th>
                                <th>本期值 ({{ sandboxResult.query?.biz_period }})</th>
                                <th>同期值 ({{ sandboxResult.query?.peer_period }})</th>
                                <th>来源</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="(b, bIdx) in step.breakdown" :key="bIdx">
                                <td class="cell-text font-bold">{{ b.param_name }}</td>
                                <td>{{ b.biz_value }}</td>
                                <td>{{ b.peer_value }}</td>
                                <td class="cell-text text-sm text-sub">{{ b.source }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <!-- ========================================== -->
          <!-- Tab 2: ⚙️ 供暖期与时间参数 (预留扩展模块)  -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'season_params'" class="pane-content-wrapper">
            <!-- 供暖期滚动与控制中枢卡片 -->
            <!-- ============================================== -->
            <!-- 板块 1：📅 系统基准业务日期管控 (Base Business Date) -->
            <!-- ============================================== -->
            <section class="card elevated section-card biz-date-controller-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">📅 全局基准业务日期管控 (Global Business Date)</div>
                  <p class="sub block-sub">
                    设定系统默认的业务基准日期（<code>set_biz_date</code>）。此日期决定生产大盘首屏、日报填报默认日历及各模块的锚点基准。
                  </p>
                </div>
                <div class="section-actions">
                  <button
                    class="btn primary shadow-accent execute-sandbox-btn"
                    type="button"
                    :disabled="savingBizDate"
                    @click="saveBizDate"
                  >
                    {{ savingBizDate ? '💾 正在保存…' : '💾 保存业务日期生效' }}
                  </button>
                </div>
              </div>

              <!-- 业务日期反馈提示 -->
              <div v-if="bizDateTip" :class="['season-tip-banner', bizDateTip.type]">
                {{ bizDateTip.text }}
              </div>

              <div class="biz-date-form-row">
                <label class="field date-picker-field">
                  <span class="field-title">📌 选择目标基准业务日期</span>
                  <div class="date-picker-wrap">
                    <input v-model="standaloneBizDate" type="date" class="input highlight-date-input" />
                    <button class="btn ghost compact-btn" type="button" @click="setBizDateQuick('today')">今日</button>
                    <button class="btn ghost compact-btn" type="button" @click="setBizDateQuick('yesterday')">昨日</button>
                  </div>
                  <small class="field-help">修改保存后，大盘、填报与分析页面将立即对齐该日期（当前库内最新数据日通常为昨日）。</small>
                </label>

                <div class="date-status-card">
                  <span class="status-label">当前生效日期</span>
                  <strong class="status-val">{{ currentBizDate || '未设置' }}</strong>
                  <span class="status-sub">文件：backend_data/.../date.json</span>
                </div>
              </div>
            </section>

            <!-- ============================================== -->
            <!-- 板块 2：⚙️ 供暖期同项目无损滚动中枢 (Season Roll) -->
            <!-- ============================================== -->
            <section class="card elevated section-card season-controller-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">⚙️ 供暖期同项目滚动控制台</div>
                  <p class="sub block-sub">
                    手动设置或滚动当前供暖期。系统将自动联动：常量表动态列头、历史同期只读参考、入库 period 编码及基准业务日期。
                  </p>
                </div>
                <div class="section-actions">
                  <button
                    class="btn primary shadow-accent execute-sandbox-btn"
                    type="button"
                    :disabled="savingSeason"
                    @click="saveSeasonConfig"
                  >
                    {{ savingSeason ? '💾 正在保存生效…' : '💾 保存并切换供暖期' }}
                  </button>
                </div>
              </div>

              <!-- 切换反馈提示 -->
              <div v-if="seasonTip" :class="['season-tip-banner', seasonTip.type]">
                {{ seasonTip.text }}
              </div>

              <!-- 控制表单栅格 -->
              <div class="season-control-form-grid">
                <label class="field">
                  <span class="field-title">🎯 目标激活供暖期 (active_period)</span>
                  <select v-model="selectedPeriod" class="input season-select" @change="onPeriodSelectChange">
                    <option v-for="s in seasonConfig.available_seasons || ['24-25', '25-26', '26-27', '27-28', '28-29']" :key="s" :value="s">
                      {{ s }} 供暖期 {{ s === currentSeasonCode ? '（当前运行）' : '' }}
                    </option>
                  </select>
                  <small class="field-help">选择新供暖期后，系统将自动推导历史同期并调整各页面列名与入库标签。</small>
                </label>

                <label class="field">
                  <span class="field-title">🔄 自动推导历史同期 (peer_period)</span>
                  <input type="text" class="input readonly-input" :value="seasonConfig.peer_period || '24-25'" disabled />
                  <small class="field-help">由中枢引擎自动向前推算一年，作为新供暖期的历史同期对比基准。</small>
                </label>

                <label class="field">
                  <span class="field-title">📅 业务日期自适应联动</span>
                  <div class="checkbox-align-box">
                    <input v-model="autoAlignBizDate" type="checkbox" id="auto-align-date-check" class="align-checkbox" />
                    <label for="auto-align-date-check" class="align-checkbox-label">自动将基准业务日期对齐至新开栓首日 ({{ formStartDate }})</label>
                  </div>
                  <small class="field-help">开启后，切换供暖期将全自动将全局业务基准日期设为上方开栓日。</small>
                </label>

                <label class="field">
                  <span class="field-title">日报统计开始日</span>
                  <input v-model="formStartDate" type="date" class="input" />
                  <small class="field-help">月累计、近7日与供暖期累计均只统计此日起的数据，当日明细不受限制。</small>
                </label>

                <label class="field">
                  <span class="field-title">日报统计结束日</span>
                  <input v-model="formEndDate" type="date" class="input" />
                  <small class="field-help">累计统计止于此日，之后录入的当日明细仍可查询。</small>
                </label>

                <label class="field">
                  <span class="field-title">本期平均气温起算日</span>
                  <input v-model="formTemperatureStartDate" type="date" class="input" />
                  <small class="field-help">默认当期11月1日，独立于日报统计开始日；期均温计算至查询日，最晚统计结束日。</small>
                </label>
                <label class="field">
                  <span class="field-title">同期平均气温起算日（{{ seasonConfig.peer_period }}）</span>
                  <input v-model="formPeerTemperatureStartDate" type="date" class="input" />
                </label>
                <label class="field">
                  <span class="field-title">同期日报统计开始日</span>
                  <input v-model="formPeerStartDate" type="date" class="input" />
                </label>
                <label class="field">
                  <span class="field-title">同期日报统计结束日</span>
                  <input v-model="formPeerEndDate" type="date" class="input" />
                  <small class="field-help">本期与同期分别保存各自的日期设置，回看历史时使用历史期的设置。</small>
                </label>

                <label class="field full-width">
                  <span class="field-title">📝 供暖期切换说明 / 备注</span>
                  <input v-model="formDescription" type="text" class="input" placeholder="输入切换原因或备忘说明…" />
                </label>
              </div>

              <!-- 历史数据安全保障说明看板 -->
              <div class="season-safety-notice">
                <div class="safety-title">🛡️ 历史数据 100% 完整保留与安全隔离保证</div>
                <ul class="safety-list">
                  <li><strong>历史记录不删除：</strong> 数据库中已有的 <code>24-25</code>、<code>25-26</code> 等所有历史周期的常量指标和日报数据一条不删，全量保留。</li>
                  <li><strong>动态列头自动对齐：</strong> 打开常量指标页面时，列头自动变为 <code>[{{ selectedPeriod }}, {{ seasonConfig.peer_period }}]</code>，同期列自动只读作为基准参考。</li>
                  <li><strong>新录入标识跟随变更：</strong> 保存常量或填报数据时，数据库记录中的 <code>period</code> 字段将自动打上最新的 <code>{{ selectedPeriod }}</code> 标识，完美隔离。</li>
                </ul>
              </div>
            </section>

            <!-- 规则说明卡片 -->
            <div v-if="false">
              <div class="card-header-row">
                <div>
                  <div class="card-header">⚙️ 供暖期与时间窗口参数管理</div>
                  <p class="sub block-sub">暖收入按各期设定的统计起止日期等额分摊，天数自动计算并包含首尾日期。</p>
                </div>
              </div>
              <div class="field-grid core-field-grid">
                <label class="field">
                  <span>当前激活供暖期</span>
                  <input type="text" class="input" :value="currentSeasonCode" disabled />
                  <small class="field-help">由 season_utils 根据当前系统日期自动推导，免人工硬编码。</small>
                </label>
                <label class="field">
                  <span>当期暖收入分摊天数</span>
                  <input type="number" class="input" :value="seasonConfig.stat_days" disabled />
                  <small class="field-help">整期暖收入 ÷ 当期统计总天数；只向设定区间内的日期分摊，同期按其自身设置计算。</small>
                </label>
                <label class="field">
                  <span>新旧采暖季切换基准月日</span>
                  <input type="text" class="input" value="10-01" disabled />
                  <small class="field-help">每年 10 月 1 日起自动转入新供暖季周期（如 2026-10-01 自动识别为 26-27 期）。</small>
                </label>
                <label class="field">
                  <span>闰年同期日映射规则</span>
                  <input type="text" class="input" value="2月29日 ➔ 2月28日" disabled />
                  <small class="field-help">针对闰年 2 月 29 日无损向平年对齐，杜绝日期越界异常。</small>
                </label>
              </div>
            </div>
          </div>

          <!-- ========================================== -->
          <!-- Tab 3: 📋 12345投诉底表 (金山文档) 接入与配置  -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'kdocs_complaint'" class="pane-content-wrapper">
            <section class="card elevated section-card kdocs-config-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">📋 12345 诉求件统计底表 · 金山文档 (KDocs) 接入配置</div>
                  <p class="sub block-sub">
                    统一维护金山文档共享链接及用于免登录调取直链的授权凭证 (<code>wps_sid</code>)。支持免人工下载直接自动拉取最新底表并计算。
                  </p>
                </div>
                <div class="section-actions">
                  <button
                    class="btn primary shadow-accent execute-sandbox-btn"
                    type="button"
                    :disabled="savingKdocs"
                    @click="saveKdocsConfig"
                  >
                    {{ savingKdocs ? '💾 正在保存…' : '💾 保存配置' }}
                  </button>
                </div>
              </div>

              <!-- 提示通知横幅 -->
              <div v-if="kdocsTip" :class="['season-tip-banner', kdocsTip.type]">
                {{ kdocsTip.text }}
              </div>

              <!-- 表单区域 -->
              <div class="kdocs-form-layout">
                <label class="field">
                  <span class="field-title">🔗 金山文档分享链接 (Share URL)</span>
                  <input
                    v-model="kdocsConfig.share_link"
                    type="text"
                    class="input kdocs-input-link"
                    placeholder="例如: https://www.kdocs.cn/l/cj8e1PTQW0uN"
                    @input="handleShareLinkInput"
                  />
                  <small class="field-help">
                    支持带参数的完整分享链接，输入后系统会自动提取并识别下方的 Share ID。
                  </small>
                </label>

                <div class="kdocs-two-col">
                  <label class="field">
                    <span class="field-title">🆔 分享标识符 (Share ID)</span>
                    <input
                      v-model="kdocsConfig.share_id"
                      type="text"
                      class="input readonly-style"
                      readonly
                    />
                    <small class="field-help">金山文档分配给该共享文件的唯一短码。</small>
                  </label>

                  <label class="field">
                    <span class="field-title">📝 配置说明与备注</span>
                    <input
                      v-model="kdocsConfig.description"
                      type="text"
                      class="input"
                      placeholder="配置备注说明"
                    />
                    <small class="field-help">用于标注该底表所属的业务年度或维护部门。</small>
                  </label>
                </div>

                <label class="field">
                  <div class="field-title-row">
                    <span class="field-title">🔑 WPS 账号身份凭据 (wps_sid Cookie)</span>
                    <button
                      type="button"
                      class="btn-text-action"
                      @click="showWpsSid = !showWpsSid"
                    >
                      {{ showWpsSid ? '🙈 隐藏明文' : '👁️ 显示明文' }}
                    </button>
                  </div>
                  <div class="sid-input-wrap">
                    <input
                      v-if="!showWpsSid"
                      v-model="kdocsConfig.wps_sid"
                      type="password"
                      class="input kdocs-sid-input font-mono"
                      placeholder="请粘贴浏览器中获取的 wps_sid Cookie 值"
                    />
                    <textarea
                      v-else
                      v-model="kdocsConfig.wps_sid"
                      rows="2"
                      class="input kdocs-sid-textarea font-mono"
                      placeholder="请粘贴浏览器中获取的 wps_sid Cookie 值"
                    ></textarea>
                  </div>
                  <small class="field-help">
                    用于直接换取免登录下载直链的身份凭据。在浏览器登录 <a href="https://www.kdocs.cn" target="_blank" class="link">kdocs.cn</a> 后按 F12 → Application → Cookies 获取。
                  </small>
                </label>
              </div>

              <!-- 操作与连通性检测区 -->
              <div class="kdocs-action-bar">
                <div class="left-actions">
                  <button
                    class="btn ghost compact-btn"
                    type="button"
                    :disabled="testingKdocs"
                    @click="testKdocsConnection"
                  >
                    {{ testingKdocs ? '⏳ 正在测试连通性…' : '🔌 测试连接与凭证有效性' }}
                  </button>

                  <button
                    class="btn ghost compact-btn"
                    type="button"
                    :disabled="downloadingKdocs"
                    title="从金山文档下载当前最新的 12345 诉求件统计底表 .xlsx 文件到本地电脑"
                    @click="downloadKdocsToLocal"
                  >
                    {{ downloadingKdocs ? '⏳ 正在下载中…' : '📥 下载底表到本地' }}
                  </button>

                  <button
                    class="btn ghost compact-btn"
                    type="button"
                    :disabled="syncingKdocs"
                    @click="syncKdocsComplaints"
                  >
                    {{ syncingKdocs ? '⚡ 正在拉取试算…' : '⚡ 立即拉取并试算当日投诉' }}
                  </button>
                </div>

                <div class="status-summary">
                  <span class="status-badge" :class="kdocsTestBadgeClass">
                    {{ kdocsTestBadgeText }}
                  </span>
                </div>
              </div>

              <!-- 连通性测试报告卡片 -->
              <div v-if="kdocsConfig.last_test_time || kdocsTestResult" class="kdocs-status-card">
                <div class="status-row">
                  <span class="status-label">最近测试时间：</span>
                  <span class="status-val">{{ kdocsTestResult?.test_time || kdocsConfig.last_test_time || '未测试' }}</span>
                </div>
                <div class="status-row">
                  <span class="status-label">诊断结果说明：</span>
                  <span class="status-val status-desc">{{ kdocsTestResult?.message || kdocsConfig.last_test_message || '暂无信息' }}</span>
                </div>
                <div v-if="kdocsConfig.last_sync_time" class="status-row">
                  <span class="status-label">最后同步时间：</span>
                  <span class="status-val">{{ kdocsConfig.last_sync_time }}</span>
                </div>
              </div>

              <!-- 试算结果预览卡片 -->
              <div v-if="kdocsSyncResult" class="card elevated sync-preview-card">
                <div class="preview-header">
                  <strong>🎉 试算成功反馈 (业务日期: {{ kdocsSyncResult.biz_date }})</strong>
                  <span class="sub">底表文件: {{ kdocsSyncResult.filename }}</span>
                </div>
                <div class="preview-metrics-grid">
                  <div class="metric-mini-card">
                    <span class="m-label">市直办/转办</span>
                    <strong class="m-val">{{ kdocsSyncResult.data?.group?.daily_city ?? 0 }} 件</strong>
                  </div>
                  <div class="metric-mini-card">
                    <span class="m-label">省办</span>
                    <strong class="m-val">{{ kdocsSyncResult.data?.group?.daily_province ?? 0 }} 件</strong>
                  </div>
                  <div class="metric-mini-card">
                    <span class="m-label">日总诉求量</span>
                    <strong class="m-val highlight">{{ kdocsSyncResult.data?.group?.daily_total ?? 0 }} 件</strong>
                  </div>
                  <div class="metric-mini-card">
                    <span class="m-label">未办结</span>
                    <strong class="m-val warning">{{ kdocsSyncResult.data?.group?.unresolved_complaints ?? 0 }} 件</strong>
                  </div>
                </div>
              </div>
            </section>

            <!-- 帮助指南卡片 -->
            <section class="card elevated section-card help-guide-card">
              <div class="card-header">💡 如何获取或更新 WPS 身份凭证 (wps_sid)？</div>
              <ol class="kdocs-guide-steps">
                <li>使用电脑 Chrome / Edge 浏览器打开 <a href="https://www.kdocs.cn" target="_blank" class="link">https://www.kdocs.cn</a>，登录你的任意普通 WPS 账号；</li>
                <li>按键盘 <code>F12</code> 打开浏览器开发者工具，切换到顶部的 <strong>Application (应用程序)</strong> 标签页；</li>
                <li>在左侧菜单依次展开 <strong>Storage → Cookies → https://www.kdocs.cn</strong>；</li>
                <li>在右侧列表中找到名为 <strong><code>wps_sid</code></strong> 的一行，双击其 Value 并复制（以 <code>V02S...</code> 开头）；</li>
                <li>粘贴至上方“WPS 账号身份凭据”输入框并点击“保存配置”即可。该 Cookie 通常具备较长有效期（1~3个月），过期失效时重新提取一次即可。</li>
              </ol>
            </section>
          </div>

          <!-- ========================================== -->
          <!-- Tab 4: 📊 常量指标与价格基准 (预留扩展模块)  -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'constants'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">📊 常量指标与各厂价格基准</div>
                  <p class="sub block-sub">管理供热收费面积、标煤单价、天然气价格、外购电价及各厂辅材价格。</p>
                </div>
              </div>
              <div class="panel-state">
                常量指标由 <code>constant_data</code> 实体表统一驱动。可通过日常常量指标页面或数据库管理工具统一维护。
              </div>
            </section>
          </div>

          <!-- ========================================== -->
          <!-- Tab 4: 🏢 供热单位与组织架构 (预留扩展模块)  -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'entities'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">🏢 供热单位与组织架构</div>
                  <p class="sub block-sub">纳管集团下属 11 家电厂、供热分公司与科研机构的编码映射。</p>
                </div>
              </div>
              <div class="entities-grid">
                <div v-for="u in unitList" :key="u.code" class="entity-card">
                  <div class="entity-name">{{ u.name }}</div>
                  <code class="entity-code">{{ u.code }}</code>
                  <span class="entity-type-badge">{{ u.type }}</span>
                </div>
              </div>
            </section>
          </div>

          <!-- ========================================== -->
          <!-- Tab 5: ⛅ 气温与气象数据管理 -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'weather_mgmt'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">⛅ 气温与气象数据管理</div>
                  <p class="sub block-sub">逐小时温度数据接入、Open-Meteo 天气同步与日度聚合状态。</p>
                </div>
              </div>
              <form class="weather-config-form" @submit.prevent="saveWeatherConfig">
                <label class="field">
                  <span class="field-title">气温导入 API 地址</span>
                  <textarea v-model.trim="weatherApiUrl" class="input" rows="4" required
                    :disabled="loadingWeather || savingWeather" placeholder="请输入完整的 HTTP / HTTPS API 地址（含查询参数）"></textarea>
                </label>
                <p class="sub block-sub">保存后，下次在数据看板或项目后台点击“导入气温”即使用此地址，无需重启。查询参数可调整经纬度、时区及历史天数。</p>
                <p class="sub block-sub">接口须返回 Open-Meteo 兼容的 hourly.time 和 hourly.temperature_2m 数组。保存配置不会请求天气接口或写入气温数据。</p>
                <div class="section-actions">
                  <button class="btn primary" type="submit" :disabled="loadingWeather || savingWeather || !weatherApiUrl">
                    {{ savingWeather ? '保存中…' : '保存气温 API 配置' }}
                  </button>
                  <button class="btn ghost" type="button" :disabled="loadingWeather || savingWeather" @click="loadWeatherConfig">
                    {{ loadingWeather ? '读取中…' : '重新读取' }}
                  </button>
                </div>
                <p v-if="weatherTip" :class="['page-tip', weatherTip.type]" role="status">{{ weatherTip.text }}</p>
              </form>
            </section>
          </div>

          <!-- ========================================== -->
          <!-- Tab 6: 💻 原始配置结构预览 (预留扩展模块)  -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'raw_config'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">💻 生产指标算法元数据 JSON 原生配置</div>
                  <p class="sub block-sub">只读展示后端 catalog_data.py 输出的完整 JSON 结构。</p>
                </div>
              </div>
              <pre class="json-code-box">{{ JSON.stringify(catalogList, null, 2) }}</pre>
            </section>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import Breadcrumbs from '../components/Breadcrumbs.vue'
import { getProjectNameById, ensureProjectsLoaded } from '../composables/useProjects'
import { getTemperatureImportConfig, saveTemperatureImportConfig } from '../services/api'

const route = useRoute()
const router = useRouter()
const projectKey = String(route.params.projectKey || 'daily_report_25_26')
const projectName = computed(() => getProjectNameById(projectKey) || '2026-2027供暖期生产日报')

const pageDisplayName = computed(() => {
  const raw = route.query.pageName
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim()
  }
  return '全局管理中心'
})

const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: projectName.value, to: `/projects/${encodeURIComponent(projectKey)}/pages` },
  { label: pageDisplayName.value, to: null },
])

// 选项卡状态与移动端导航
const activeTab = ref('algorithms')
const viewMode = ref('cards') // 'cards' | 'table'
const sidebarRef = ref(null)

function selectTab(tabKey, event) {
  activeTab.value = tabKey
  if (event && event.currentTarget && typeof event.currentTarget.scrollIntoView === 'function') {
    event.currentTarget.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  }
}

function onMobileSelectChange() {
  setTimeout(() => {
    const activeEl = sidebarRef.value?.querySelector('.sidebar-tab-btn.active')
    if (activeEl && typeof activeEl.scrollIntoView === 'function') {
      activeEl.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
    }
  }, 50)
}

// 基础状态
const loading = ref(false)
const errorMessage = ref('')
const globalTip = ref(null)
const weatherApiUrl = ref('')
const loadingWeather = ref(false)
const savingWeather = ref(false)
const weatherTip = ref(null)

async function loadWeatherConfig() {
  loadingWeather.value = true
  weatherTip.value = null
  try {
    const result = await getTemperatureImportConfig(projectKey)
    weatherApiUrl.value = result.data.api_url
  } catch (err) {
    weatherTip.value = { type: 'error', text: err.message }
  } finally {
    loadingWeather.value = false
  }
}

async function saveWeatherConfig() {
  savingWeather.value = true
  weatherTip.value = null
  try {
    const result = await saveTemperatureImportConfig(projectKey, weatherApiUrl.value)
    weatherApiUrl.value = result.data.api_url
    weatherTip.value = { type: 'success', text: '配置已保存，下次导入气温时生效。' }
  } catch (err) {
    weatherTip.value = { type: 'error', text: err.message }
  } finally {
    savingWeather.value = false
  }
}
const currentBizDate = ref('')
const currentSeasonCode = ref('25-26')
const seasonConfig = ref({
  active_period: '25-26',
  peer_period: '24-25',
  start_date: '2025-11-01',
  end_date: '2026-04-05',
  stat_days: 156,
  switch_date_rule: '10-01',
  available_seasons: ['24-25', '25-26', '26-27', '27-28', '28-29'],
})
const selectedPeriod = ref('25-26')
const formBizDate = ref('')
const formStartDate = ref('')
const formEndDate = ref('')
const formTemperatureStartDate = ref('')
const formPeerStartDate = ref('')
const formPeerEndDate = ref('')
const formPeerTemperatureStartDate = ref('')
const formDescription = ref('')
const savingSeason = ref(false)
const seasonTip = ref(null)
const standaloneBizDate = ref('')
const savingBizDate = ref(false)
const bizDateTip = ref(null)
const autoAlignBizDate = ref(true)

// 算法元数据
const categories = ref([])
const catalogList = ref([])
const activeCategoryKey = ref('all')
const searchKeyword = ref('')
const selectedScopeFilter = ref('all')
const selectedDerivedFilter = ref('all')
const copiedKey = ref('')

// ==========================================
// 金山文档 (KDocs) 12345 投诉底表接入与配置状态
// ==========================================
const kdocsConfig = ref({
  share_link: 'https://www.kdocs.cn/l/cj8e1PTQW0uN',
  share_id: 'cj8e1PTQW0uN',
  wps_sid: 'V02SdZ9VTFSbBK9yGbjfj93LeD4okis00ab8df8f0012fc69e2',
  description: '2026-2027年度市12345诉求件统计底表（金山文档共享）',
  auto_sync_enabled: false,
  last_sync_time: '',
  last_test_status: '',
  last_test_time: '',
  last_test_message: '',
})
const showWpsSid = ref(false)
const savingKdocs = ref(false)
const testingKdocs = ref(false)
const downloadingKdocs = ref(false)
const syncingKdocs = ref(false)
const kdocsTip = ref(null)
const kdocsTestResult = ref(null)
const kdocsSyncResult = ref(null)

const kdocsTestBadgeText = computed(() => {
  const status = kdocsTestResult.value
    ? (kdocsTestResult.value.ok ? 'SUCCESS' : 'FAILED')
    : kdocsConfig.value.last_test_status
  if (status === 'SUCCESS') return '🟢 连接畅通'
  if (status === 'FAILED') return '🔴 授权失效/连接失败'
  if (status === 'ERROR') return '⚠️ 异常错误'
  return '⚪ 尚未检测'
})

const kdocsTestBadgeClass = computed(() => {
  const status = kdocsTestResult.value
    ? (kdocsTestResult.value.ok ? 'SUCCESS' : 'FAILED')
    : kdocsConfig.value.last_test_status
  if (status === 'SUCCESS') return 'badge-success'
  if (status === 'FAILED') return 'badge-danger'
  if (status === 'ERROR') return 'badge-warning'
  return 'badge-neutral'
})

// 沙盒状态
const sandboxDate = ref('')
const sandboxCompany = ref('JinZhou')
const sandboxItem = ref('rate_std_coal_per_heat')
const sandboxLoading = ref(false)
const sandboxResult = ref(null)

// 组织机构列表
const unitList = [
  { name: '北海热电厂', code: 'BeiHai', type: '热电联产电厂' },
  { name: '金州热电', code: 'JinZhou', type: '热电联产电厂' },
  { name: '北方热电', code: 'BeiFang', type: '热电联产电厂' },
  { name: '金普热电', code: 'JinPu', type: '热电联产电厂' },
  { name: '庄河热电', code: 'ZhuangHe', type: '热电联产电厂' },
  { name: '香海热电厂', code: 'XiangHai', type: '调峰电厂' },
  { name: '供热分公司', code: 'GongRe', type: '供热管网及换热站' },
  { name: '热力研究院', code: 'YanJiuYuan', type: '科研技术单位' },
  { name: '主城区汇总', code: 'ZhuChengQu', type: '主城供热区域' },
  { name: '全集团汇总', code: 'Group', type: '全口径合并' },
]

onMounted(async () => {
  ensureProjectsLoaded().catch(() => {})
  await loadSeasonConfig()
  await loadBizDate()
  await loadCatalog()
  await loadKdocsConfig()
  await loadWeatherConfig()
})

function goProjectPages() {
  router.push(`/projects/${encodeURIComponent(projectKey)}/pages`)
}

async function loadSeasonConfig() {
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/season/config`)
    if (res.ok) {
      const data = await res.json()
      if (data.ok) {
        seasonConfig.value = data
        currentSeasonCode.value = data.active_period || '25-26'
        selectedPeriod.value = data.active_period || '25-26'
        formBizDate.value = data.current_biz_date || currentBizDate.value || ''
        formStartDate.value = data.start_date || '2025-11-01'
        formEndDate.value = data.end_date || '2026-04-05'
        formTemperatureStartDate.value = data.temperature_start_date || `${data.start_date.slice(0, 4)}-11-01`
        formPeerStartDate.value = data.peer_settings.start_date
        formPeerEndDate.value = data.peer_settings.end_date
        formPeerTemperatureStartDate.value = data.peer_settings.temperature_start_date
      }
    }
  } catch (err) {
    console.error('加载供暖期配置失败', err)
  }
}

function onPeriodSelectChange() {
  const p = selectedPeriod.value
  const parts = p.split('-')
  if (parts.length === 2) {
    const y1 = parseInt(parts[0], 10)
    const y2 = parseInt(parts[1], 10)
    if (!isNaN(y1) && !isNaN(y2)) {
      const py1 = (y1 - 1 + 100) % 100
      const py2 = (y2 - 1 + 100) % 100
      seasonConfig.value.peer_period = `${String(py1).padStart(2, '0')}-${String(py2).padStart(2, '0')}`
      formStartDate.value = `20${String(y1).padStart(2, '0')}-11-01`
      formEndDate.value = `20${String(y2).padStart(2, '0')}-04-05`
      const saved = seasonConfig.value.seasons?.[p]
      formStartDate.value = saved?.start_date || formStartDate.value
      formEndDate.value = saved?.end_date || formEndDate.value
      formTemperatureStartDate.value = saved?.temperature_start_date || `20${String(y1).padStart(2, '0')}-11-01`
      const peerSaved = seasonConfig.value.seasons?.[seasonConfig.value.peer_period]
      formPeerStartDate.value = peerSaved?.start_date || `20${String(py1).padStart(2, '0')}-11-01`
      formPeerEndDate.value = peerSaved?.end_date || `20${String(py2).padStart(2, '0')}-04-05`
      formPeerTemperatureStartDate.value = peerSaved?.temperature_start_date || `20${String(py1).padStart(2, '0')}-11-01`
      formBizDate.value = formStartDate.value
    }
  }
}

async function saveSeasonConfig() {
  savingSeason.value = true
  seasonTip.value = null
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/season/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        active_period: selectedPeriod.value,
        biz_date: autoAlignBizDate.value ? formStartDate.value : (standaloneBizDate.value || currentBizDate.value),
        start_date: formStartDate.value,
        end_date: formEndDate.value,
        temperature_start_date: formTemperatureStartDate.value,
        peer_start_date: formPeerStartDate.value,
        peer_end_date: formPeerEndDate.value,
        peer_temperature_start_date: formPeerTemperatureStartDate.value,
        description: formDescription.value || `切换供暖期至 ${selectedPeriod.value}`,
      }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    seasonTip.value = {
      type: 'success',
      text: `✅ 供暖期已成功滚动切换至【${selectedPeriod.value}】（同期自动对齐为【${data.peer_period}】）！基准业务日期已对齐至 ${data.current_biz_date}。系统内各填报表、常量指标表与多维分析已全自动联动！`,
    }
    currentSeasonCode.value = data.active_period
    currentBizDate.value = data.current_biz_date
    sandboxDate.value = data.current_biz_date
    standaloneBizDate.value = data.current_biz_date
    await loadSeasonConfig()
  } catch (err) {
    seasonTip.value = {
      type: 'error',
      text: `❌ 保存供暖期配置失败: ${err.message}`,
    }
  } finally {
    savingSeason.value = false
  }
}

async function loadBizDate() {
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/dashboard/date`)
    if (res.ok) {
      const data = await res.json()
      if (data.set_biz_date) {
        currentBizDate.value = data.set_biz_date
        sandboxDate.value = data.set_biz_date
        standaloneBizDate.value = data.set_biz_date
      }
    }
  } catch (err) {
    console.error('加载基准日期失败', err)
  }
}

function setBizDateQuick(type) {
  const d = new Date()
  if (type === 'today') {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    standaloneBizDate.value = `${y}-${m}-${day}`
  } else if (type === 'yesterday') {
    d.setDate(d.getDate() - 1)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    standaloneBizDate.value = `${y}-${m}-${day}`
  }
}

async function saveBizDate() {
  if (!standaloneBizDate.value) {
    bizDateTip.value = { type: 'error', text: '请先选择有效的业务日期' }
    return
  }
  savingBizDate.value = true
  bizDateTip.value = null
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/dashboard/date`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ set_biz_date: standaloneBizDate.value }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`)
    currentBizDate.value = data.set_biz_date
    sandboxDate.value = data.set_biz_date
    bizDateTip.value = {
      type: 'success',
      text: `✅ 基准业务日期已成功设置为【${data.set_biz_date}】并即时生效！生产大盘、数据填报日历与分析模块已完成同步对齐！`,
    }
  } catch (err) {
    bizDateTip.value = {
      type: 'error',
      text: `❌ 保存业务日期失败: ${err.message}`,
    }
  } finally {
    savingBizDate.value = false
  }
}

async function loadCatalog() {
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/metrics/catalog`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (data.ok) {
      categories.value = data.categories || []
      catalogList.value = data.catalog || []
    }
  } catch (err) {
    errorMessage.value = `加载指标算法元数据失败: ${err.message}`
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  await loadWeatherConfig()
  await loadSeasonConfig()
  await loadBizDate()
  await loadCatalog()
  await loadKdocsConfig()
  if (sandboxResult.value) {
    await executeSandbox()
  }
}

function handleShareLinkInput() {
  const link = kdocsConfig.value.share_link || ''
  const match = link.match(/kdocs\.cn\/l\/([a-zA-Z0-9_-]+)/)
  if (match) {
    kdocsConfig.value.share_id = match[1]
  } else if (link && !link.includes('/')) {
    kdocsConfig.value.share_id = link.trim()
  }
}

async function loadKdocsConfig() {
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/data_entry/complaints/kdocs/config`)
    if (res.ok) {
      const json = await res.json()
      if (json.ok && json.data) {
        kdocsConfig.value = Object.assign({}, kdocsConfig.value, json.data)
      }
    }
  } catch (err) {
    console.error('加载金山文档配置失败:', err)
  }
}

async function saveKdocsConfig() {
  savingKdocs.value = true
  kdocsTip.value = null
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/data_entry/complaints/kdocs/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(kdocsConfig.value),
    })
    const json = await res.json()
    if (res.ok && json.ok) {
      kdocsTip.value = {
        type: 'success',
        text: json.message || '金山文档接入配置已成功保存！',
      }
      kdocsConfig.value = Object.assign({}, kdocsConfig.value, json.data)
    } else {
      kdocsTip.value = {
        type: 'error',
        text: json.detail || json.message || '保存配置失败',
      }
    }
  } catch (err) {
    kdocsTip.value = { type: 'error', text: `保存请求异常: ${err.message}` }
  } finally {
    savingKdocs.value = false
  }
}

async function testKdocsConnection() {
  testingKdocs.value = true
  kdocsTip.value = null
  kdocsTestResult.value = null
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/data_entry/complaints/kdocs/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        share_link: kdocsConfig.value.share_link,
        wps_sid: kdocsConfig.value.wps_sid,
      }),
    })
    const json = await res.json()
    kdocsTestResult.value = {
      ok: json.ok,
      message: json.message,
      test_time: json.data?.test_time || new Date().toLocaleString(),
    }
    if (json.ok) {
      kdocsTip.value = { type: 'success', text: json.message }
      kdocsConfig.value.last_test_status = 'SUCCESS'
      kdocsConfig.value.last_test_message = json.message
      kdocsConfig.value.last_test_time = json.data?.test_time || new Date().toLocaleString()
    } else {
      kdocsTip.value = { type: 'error', text: json.message }
      kdocsConfig.value.last_test_status = 'FAILED'
      kdocsConfig.value.last_test_message = json.message
    }
  } catch (err) {
    kdocsTip.value = { type: 'error', text: `测试请求失败: ${err.message}` }
  } finally {
    testingKdocs.value = false
  }
}

async function syncKdocsComplaints() {
  syncingKdocs.value = true
  kdocsTip.value = null
  kdocsSyncResult.value = null
  try {
    const targetDate = formBizDate.value || currentBizDate.value || ''
    const res = await fetch(`/api/v1/projects/${projectKey}/data_entry/complaints/kdocs/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ biz_date: targetDate }),
    })
    const json = await res.json()
    if (res.ok && json.ok) {
      kdocsSyncResult.value = json
      kdocsTip.value = { type: 'success', text: json.message }
      kdocsConfig.value.last_sync_time = new Date().toLocaleString()
    } else {
      kdocsTip.value = {
        type: 'error',
        text: json.detail || json.message || '拉取试算失败',
      }
    }
  } catch (err) {
    kdocsTip.value = { type: 'error', text: `拉取请求失败: ${err.message}` }
  } finally {
    syncingKdocs.value = false
  }
}

async function downloadKdocsToLocal() {
  downloadingKdocs.value = true
  kdocsTip.value = null
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/data_entry/complaints/kdocs/download`)
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      throw new Error(errJson.detail || errJson.message || `HTTP ${res.status}`)
    }
    const cd = res.headers.get('content-disposition') || ''
    let filename = '2026-2027年度市12345诉求件统计表.xlsx'
    const match = cd.match(/filename\*=UTF-8''([^;&]+)/i)
    if (match) {
      filename = decodeURIComponent(match[1])
    }
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    kdocsTip.value = { type: 'success', text: `✔ 底表文件【${filename}】已成功下载至本地！` }
  } catch (err) {
    kdocsTip.value = { type: 'error', text: `下载失败: ${err.message}` }
  } finally {
    downloadingKdocs.value = false
  }
}

// 统计大类数量
function getCategoryCount(catKey) {
  if (catKey === 'all') return catalogList.value.length
  return catalogList.value.filter((m) => m.category_key === catKey).length
}

// 过滤后的指标列表
const filteredCatalog = computed(() => {
  return catalogList.value.filter((m) => {
    // 1. 分类过滤
    if (activeCategoryKey.value !== 'all' && m.category_key !== activeCategoryKey.value) {
      return false
    }
    // 2. 适用主体过滤
    if (selectedScopeFilter.value === 'plant' && !m.applicable_scope.includes('电厂')) {
      return false
    }
    if (selectedScopeFilter.value === 'heating' && !m.applicable_scope.includes('供热')) {
      return false
    }
    if (selectedScopeFilter.value === 'group' && !m.applicable_scope.includes('集团') && !m.applicable_scope.includes('主城区')) {
      return false
    }
    // 3. 派生属性过滤
    if (selectedDerivedFilter.value === 'derived' && !m.is_derived) {
      return false
    }
    if (selectedDerivedFilter.value === 'base' && m.is_derived) {
      return false
    }
    // 4. 关键字搜索
    if (searchKeyword.value) {
      const q = searchKeyword.value.toLowerCase()
      const matchName = String(m.item_cn || '').toLowerCase().includes(q)
      const matchKey = String(m.item || '').toLowerCase().includes(q)
      const matchUnit = String(m.unit || '').toLowerCase().includes(q)
      const matchFormula = String(m.formula_display || '').toLowerCase().includes(q)
      const matchDesc = String(m.formula_description || '').toLowerCase().includes(q)
      return matchName || matchKey || matchUnit || matchFormula || matchDesc
    }
    return true
  })
})

function getCategoryClass(catKey) {
  if (catKey === 'production_supply') return 'theme-supply'
  if (catKey === 'consumption_material') return 'theme-consumption'
  if (catKey === 'intensity_unit') return 'theme-intensity'
  if (catKey === 'economic_revenue_cost') return 'theme-economic'
  if (catKey === 'service_quality') return 'theme-service'
  if (catKey === 'weather_reserve') return 'theme-weather'
  if (catKey === 'consolidation_rules') return 'theme-consolidation'
  return ''
}

function formatDependencies(deps) {
  if (!Array.isArray(deps) || !deps.length) return '—'
  return deps.join('、')
}

async function copyKey(keyText) {
  try {
    await navigator.clipboard.writeText(keyText)
    copiedKey.value = keyText
    setTimeout(() => {
      if (copiedKey.value === keyText) copiedKey.value = ''
    }, 2000)
  } catch (e) {
    console.error('复制失败', e)
  }
}

function quickFillSandbox(item) {
  sandboxItem.value = item.item
  if (item.applicable_scope.includes('仅供热分公司')) {
    sandboxCompany.value = 'GongRe'
  } else if (item.applicable_scope.includes('主城区')) {
    sandboxCompany.value = 'ZhuChengQu'
  } else if (item.applicable_scope.includes('全集团')) {
    sandboxCompany.value = 'Group'
  }
  const el = document.getElementById('sandbox-section')
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
  executeSandbox()
}

function fillLatestBizDate() {
  if (currentBizDate.value) {
    sandboxDate.value = currentBizDate.value
  }
}

function getCompanyName(code) {
  const match = unitList.find((u) => u.code === code)
  return match ? `${match.name} (${code})` : code
}

function formatVal(v) {
  if (v === null || v === undefined) return '—'
  const num = Number(v)
  if (Number.isNaN(num)) return String(v)
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 4 })
}

function getGrowthClass(str) {
  if (!str || str === '—') return ''
  if (str.startsWith('+')) return 'growth-up'
  if (str.startsWith('-')) return 'growth-down'
  return ''
}

// 执行沙盒验算
async function executeSandbox() {
  sandboxLoading.value = true
  errorMessage.value = ''
  try {
    const res = await fetch(`/api/v1/projects/${projectKey}/metrics/sandbox`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        biz_date: sandboxDate.value || currentBizDate.value || '',
        company: sandboxCompany.value,
        item: sandboxItem.value,
      }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (data.ok) {
      sandboxResult.value = data
    } else {
      throw new Error(data.message || '演算失败')
    }
  } catch (err) {
    errorMessage.value = `执行算法验算失败: ${err.message}`
  } finally {
    sandboxLoading.value = false
  }
}
</script>

<style scoped>
.weather-config-form {
  display: grid;
  gap: 12px;
}

.weather-config-form .field {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.weather-config-form textarea {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  overflow-wrap: anywhere;
}

.dr-global-mgmt-view {
  min-height: 100vh;
  background: #f8fafc;
  color: #0f172a;
}

.tube-page-main {
  max-width: 1440px;
  margin: 0 auto;
  padding: 16px 24px 64px;
}

/* 顶栏 */
.premium-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 12px 0;
  border-bottom: 1px solid #e2e8f0;
}

.premium-topbar h2 {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 4px;
}

.premium-topbar .sub {
  font-size: 13.5px;
  color: #64748b;
  margin: 0;
}

.topbar-actions {
  display: flex;
  gap: 10px;
}

/* 磨砂玻璃态快速看板 */
.quick-dashboard-card {
  margin-bottom: 24px !important;
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(226, 232, 240, 0.9) !important;
  border-radius: 12px !important;
  padding: 16px 20px !important;
}

.meta-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.meta-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.meta-value {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
}

.highlight-num {
  color: #2563eb !important;
}

/* 双栏工作台 */
.admin-workbench-layout {
  display: grid !important;
  grid-template-columns: 240px 1fr !important;
  gap: 24px !important;
  align-items: start !important;
}

.mobile-tab-switcher {
  display: none !important;
}

.admin-sidebar {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(226, 232, 240, 0.8) !important;
  border-radius: 14px !important;
  padding: 12px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  position: sticky;
  top: 80px;
  z-index: 10;
}

.sidebar-tab-btn {
  width: 100% !important;
  border: none !important;
  background: transparent !important;
  padding: 12px 16px !important;
  border-radius: 10px !important;
  font-size: 13.5px !important;
  font-weight: 600 !important;
  color: #475569 !important;
  text-align: left !important;
  cursor: pointer !important;
  transition: all 0.2s ease !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 10px !important;
}

.sidebar-tab-btn:hover {
  color: #1e293b !important;
  background: rgba(241, 245, 249, 0.7) !important;
}

.sidebar-tab-btn.active {
  color: #2563eb !important;
  background: #eff6ff !important;
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.15) !important;
}

@media (max-width: 1024px) {
  .admin-workbench-layout {
    grid-template-columns: 1fr !important;
    gap: 12px !important;
  }

  /* 移动端专属快捷功能板块切换器 */
  .mobile-tab-switcher {
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
    background: #ffffff !important;
    border: 1.5px solid #93c5fd !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08) !important;
  }

  .switcher-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .switcher-title {
    font-size: 13px;
    font-weight: 700;
    color: #1e40af;
  }

  .switcher-hint {
    font-size: 11px;
    color: #64748b;
  }

  .mobile-select-wrap {
    position: relative;
    width: 100%;
  }

  .mobile-tab-select {
    width: 100%;
    height: 40px;
    font-size: 14px;
    font-weight: 700;
    color: #1e293b;
    background: #f0f7ff;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    padding: 0 34px 0 12px;
    appearance: none;
    cursor: pointer;
  }

  .select-arrow-icon {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    color: #2563eb;
    pointer-events: none;
  }

  /* 移动端侧栏转为横向平滑滚动条 */
  .admin-sidebar {
    position: static !important;
    flex-direction: row !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    scrollbar-color: #94a3b8 #f1f5f9;
    padding: 6px !important;
    border-radius: 10px !important;
    gap: 8px !important;
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  }

  /* 优雅细微的滚动条，明确提示右侧有内容可滑动 */
  .admin-sidebar::-webkit-scrollbar {
    height: 4px !important;
    display: block !important;
  }

  .admin-sidebar::-webkit-scrollbar-track {
    background: #f1f5f9 !important;
    border-radius: 4px !important;
  }

  .admin-sidebar::-webkit-scrollbar-thumb {
    background: #94a3b8 !important;
    border-radius: 4px !important;
  }

  /* 核心修复：移动端按钮自适应紧凑药丸，绝不占 100% 宽度 */
  .sidebar-tab-btn {
    width: auto !important;
    min-width: max-content !important;
    flex: 0 0 auto !important;
    white-space: nowrap !important;
    padding: 8px 14px !important;
    font-size: 13px !important;
    border-radius: 8px !important;
    background: #f1f5f9 !important;
    border: 1px solid #cbd5e1 !important;
    color: #334155 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    box-shadow: none !important;
  }

  .sidebar-tab-btn:hover {
    background: #e2e8f0 !important;
    color: #0f172a !important;
  }

  .sidebar-tab-btn.active {
    background: #2563eb !important;
    color: #ffffff !important;
    border-color: #2563eb !important;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.35) !important;
  }
}

.admin-content-pane {
  display: flex !important;
  flex-direction: column !important;
  gap: 20px !important;
  min-width: 0 !important;
}

.pane-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.section-card {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  padding: 20px !important;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.card-header {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
}

.block-sub {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
}

.compact-btn {
  padding: 6px 12px !important;
  font-size: 12.5px !important;
}

/* 过滤工具栏 */
.filter-toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 280px;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  font-size: 14px;
  color: #94a3b8;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding-left: 36px !important;
  padding-right: 32px !important;
  height: 38px;
  border-radius: 8px;
  font-size: 13.5px;
}

.btn-clear {
  position: absolute;
  right: 10px;
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
}

.filter-dropdowns {
  display: flex;
  gap: 10px;
}

.scope-select, .derived-select {
  height: 38px;
  border-radius: 8px;
  font-size: 13px;
}

/* 分类胶囊 */
.category-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
}

.category-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}

.category-pill:hover {
  background: #e2e8f0;
  border-color: #94a3b8;
}

.category-pill.active {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25);
}

.category-pill.active .pill-count {
  color: rgba(255, 255, 255, 0.85);
}

.pill-count {
  font-size: 11px;
  color: #64748b;
}

/* 卡片网格 */
.catalog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.metric-card {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  padding: 16px !important;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.05) !important;
  border-color: #cbd5e1 !important;
}

.metric-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.metric-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.category-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #475569;
  align-self: flex-start;
}

.metric-name {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.unit-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 3px 8px;
  background: #e0f2fe;
  color: #0369a1;
  border-radius: 6px;
}

.metric-key-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f8fafc;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.metric-key {
  font-family: Consolas, Monaco, monospace;
  font-size: 12.5px;
  color: #1e293b;
  cursor: pointer;
}

.btn-copy-icon {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 13px;
  padding: 0 2px;
}

.copy-success-tip {
  font-size: 11px;
  color: #16a34a;
  font-weight: 700;
}

.formula-box {
  background: #f8fafc;
  border-left: 3px solid #3b82f6;
  padding: 8px 10px;
  border-radius: 0 6px 6px 0;
}

.formula-label {
  font-size: 11.5px;
  color: #64748b;
  font-weight: 600;
  display: block;
  margin-bottom: 2px;
}

.formula-code {
  font-family: Consolas, Monaco, monospace;
  font-size: 12.5px;
  font-weight: 700;
  color: #0284c7;
  word-break: break-all;
}

.metric-desc {
  font-size: 12.5px;
  color: #475569;
  line-height: 1.5;
  margin: 0;
}

.metric-meta-details {
  border-top: 1px dashed #e2e8f0;
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.meta-row {
  display: flex;
  gap: 6px;
  align-items: baseline;
}

.row-label {
  color: #94a3b8;
  font-weight: 600;
  white-space: nowrap;
}

.row-val {
  color: #334155;
}

.highlight-rule {
  color: #d97706 !important;
  font-weight: 600;
}

.time-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.time-tag {
  background: #f1f5f9;
  color: #475569;
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 4px;
}

.card-footer-action {
  margin-top: auto;
  padding-top: 8px;
}

.sandbox-trigger-btn {
  width: 100%;
  justify-content: center;
  color: #2563eb !important;
  border-color: #bfdbfe !important;
}

.sandbox-trigger-btn:hover {
  background: #eff6ff !important;
}

/* 表格视图 */
.catalog-table {
  width: 100%;
  border-collapse: collapse;
}

.table-key-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.clickable-key {
  font-family: monospace;
  font-size: 12px;
  cursor: pointer;
  color: #2563eb;
}

.category-badge-table {
  font-size: 11px;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
}

.cell-formula {
  max-width: 380px;
}

.formula-inline {
  color: #0284c7;
  font-family: monospace;
  font-size: 12.5px;
}

.formula-desc-inline {
  display: block;
  color: #64748b;
  font-size: 11.5px;
  margin-top: 2px;
}

/* ================== 沙盒样式 ================== */
.sandbox-card {
  border: 1.5px solid #93c5fd !important;
  background: linear-gradient(180deg, #ffffff 0%, #f0f7ff 100%) !important;
}

.sandbox-control-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) auto;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 20px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
}

.date-input-group {
  display: flex;
  gap: 6px;
}

.sandbox-action-wrap {
  display: flex;
  align-items: flex-end;
}

.execute-sandbox-btn {
  height: 38px;
  padding: 0 20px !important;
  font-size: 14px !important;
}

.sandbox-results-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-headline-card {
  background: #ffffff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.indicator-badge {
  font-size: 11px;
  font-weight: 700;
  color: #16a34a;
  background: #dcfce7;
  padding: 2px 8px;
  border-radius: 999px;
}

.headline-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin: 6px 0 4px;
}

.headline-meta {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}

.final-unit-pill {
  font-size: 13px;
  font-weight: 700;
  padding: 4px 12px;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 6px;
}

/* 8 窗口结果矩阵卡片 */
.matrix-8-windows {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}

.window-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.window-card.highlight-win {
  border-color: #3b82f6;
  background: #f8fafc;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.win-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.win-val {
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
}

.win-peer {
  font-size: 12px;
  color: #94a3b8;
}

.win-growth {
  font-size: 12px;
  font-weight: 700;
  margin-top: 4px;
}

.growth-up {
  color: #dc2626;
}

.growth-down {
  color: #16a34a;
}

/* 步骤时间轴 */
.derivation-steps-block {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
}

.steps-heading {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 16px;
}

.steps-timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.timeline-step-item {
  display: flex;
  gap: 12px;
}

.step-num-badge {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #2563eb;
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-content-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.step-desc {
  font-size: 13px;
  color: #475569;
  margin: 0;
  line-height: 1.5;
}

.step-breakdown-table-wrap {
  margin-top: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
}

.step-subtable {
  width: 100%;
  font-size: 12px;
}

/* 组织架构 */
.entities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.entity-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.entity-name {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.entity-code {
  font-family: monospace;
  font-size: 12px;
  color: #2563eb;
}

.entity-type-badge {
  font-size: 11px;
  background: #e2e8f0;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
  align-self: flex-start;
}

.json-code-box {
  background: #0f172a;
  color: #38bdf8;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  padding: 16px;
  border-radius: 8px;
  max-height: 480px;
  overflow: auto;
}

/* 基准业务日期控制卡片专属样式 */
.biz-date-controller-card {
  border-left: 4px solid #10b981;
  margin-bottom: 20px;
}

.biz-date-form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  align-items: flex-start;
}

.date-picker-field {
  flex: 1 1 360px;
}

.date-picker-wrap {
  display: flex;
  gap: 8px;
  align-items: center;
}

.highlight-date-input {
  font-weight: 700;
  font-size: 15px;
  color: #0f766e;
  background: #f0fdf4;
  border-color: #86efac;
}

.date-status-card {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 12px 18px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 200px;
}

.status-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.status-val {
  font-size: 18px;
  color: #047857;
  font-weight: 700;
  font-family: monospace;
}

.status-sub {
  font-size: 11px;
  color: #94a3b8;
}

.checkbox-align-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px 12px;
  margin-top: 2px;
}

.align-checkbox {
  cursor: pointer;
  width: 16px;
  height: 16px;
}

.align-checkbox-label {
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  margin: 0;
  user-select: none;
}

/* 供暖期控制台专属样式 */
.season-controller-card {
  border-left: 4px solid #3b82f6;
}

.season-tip-banner {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 16px;
}
.season-tip-banner.success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}
.season-tip-banner.error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.season-control-form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.season-control-form-grid .full-width {
  grid-column: 1 / -1;
}

.field-title {
  font-weight: 600;
  color: #1e293b;
  font-size: 13px;
  margin-bottom: 4px;
  display: block;
}

.season-select {
  font-weight: 600;
  color: #1d4ed8;
  background: #f8fafc;
}

.readonly-input {
  background: #f1f5f9;
  color: #64748b;
  cursor: not-allowed;
}

.season-safety-notice {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 16px 20px;
}
.safety-title {
  font-size: 14px;
  font-weight: 700;
  color: #166534;
  margin-bottom: 8px;
}
.safety-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #15803d;
  line-height: 1.7;
}
.safety-list code {
  background: #dcfce7;
  color: #14532d;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

/* ============================================================================== */
/* 📋 金山文档 (KDocs) 12345 底表配置样式 */
/* ============================================================================== */
.kdocs-config-card {
  border-top: 3px solid #2563eb !important;
}

.kdocs-form-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 10px;
}

.kdocs-two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 768px) {
  .kdocs-two-col {
    grid-template-columns: 1fr;
  }
}

.kdocs-input-link {
  width: 100%;
}

.readonly-style {
  background-color: #f1f5f9 !important;
  color: #475569 !important;
  cursor: not-allowed !important;
  font-family: monospace;
}

.field-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.btn-text-action {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 12.5px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.btn-text-action:hover {
  background: #eff6ff;
  text-decoration: underline;
}

.kdocs-sid-input,
.kdocs-sid-textarea {
  width: 100%;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  line-height: 1.4;
}

.kdocs-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #e2e8f0;
}

.left-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12.5px;
  font-weight: 600;
}

.badge-success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.badge-danger {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.badge-warning {
  background: #fffbeb;
  color: #92400e;
  border: 1px solid #fde68a;
}

.badge-neutral {
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
}

.kdocs-status-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-row {
  display: flex;
  font-size: 13px;
  line-height: 1.5;
}

.status-label {
  color: #64748b;
  width: 105px;
  flex-shrink: 0;
  font-weight: 600;
}

.status-val {
  color: #1e293b;
  font-weight: 500;
}

.status-desc {
  color: #0369a1;
}

.sync-preview-card {
  margin-top: 16px !important;
  background: #f0fdf4 !important;
  border: 1px solid #86efac !important;
  border-radius: 10px !important;
  padding: 16px !important;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  color: #166534;
}

.preview-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
}

.metric-mini-card {
  background: #ffffff;
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  border: 1px solid #bbf7d0;
}

.m-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.m-val {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.m-val.highlight {
  color: #2563eb;
}

.m-val.warning {
  color: #d97706;
}

.help-guide-card {
  background: #fdfdfd !important;
  border-left: 4px solid #6366f1 !important;
}

.kdocs-guide-steps {
  margin: 12px 0 0;
  padding-left: 20px;
  font-size: 13.5px;
  line-height: 1.8;
  color: #334155;
}

.kdocs-guide-steps li {
  margin-bottom: 6px;
}

.kdocs-guide-steps code {
  background: #f1f5f9;
  color: #2563eb;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.link {
  color: #2563eb;
  text-decoration: underline;
}

/* ============================================================================== */
/* 📱 移动端与手机窄屏极致体验适配 (Mobile & Narrow Screen Optimization)           */
/* ============================================================================== */

/* 移动端表格横向滑动提示条 */
.mobile-table-hint {
  display: none;
  font-size: 11.5px;
  color: #0369a1;
  background: #f0f9ff;
  border: 1px dashed #bae6fd;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 10px;
  text-align: center;
}

@media (max-width: 768px) {
  .mobile-table-hint {
    display: block;
  }

  /* 根容器与主容器适配：消除两边过大空白 */
  .dr-global-mgmt-view {
    overflow-x: hidden;
    width: 100%;
  }

  .tube-page-main {
    padding: 10px 12px 48px !important;
  }

  /* 顶栏垂直流式排布：标题居上，操作按钮均分双列居下 */
  .premium-topbar {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 12px !important;
    margin-bottom: 14px !important;
    padding: 6px 0 12px !important;
  }

  .premium-topbar h2 {
    font-size: 18px !important;
    line-height: 1.35;
    margin-bottom: 4px;
  }

  .premium-topbar .sub {
    font-size: 12px !important;
    line-height: 1.5;
  }

  .topbar-actions {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 8px !important;
    width: 100% !important;
  }

  .topbar-actions .btn {
    width: 100% !important;
    height: 38px !important;
    justify-content: center !important;
    font-size: 13px !important;
    padding: 0 8px !important;
  }

  /* 磨砂玻璃态全局数据看板：2 列网格紧凑重构，引擎项整行通栏突出 */
  .quick-dashboard-card {
    padding: 12px 10px !important;
    margin-bottom: 14px !important;
    border-radius: 10px !important;
  }

  .meta-dashboard {
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 8px !important;
  }

  .meta-dashboard .meta-card {
    padding: 8px 10px;
    background: rgba(248, 250, 252, 0.85);
    border: 1px solid rgba(226, 232, 240, 0.8);
    border-radius: 8px;
    gap: 2px;
  }

  .meta-dashboard .meta-card:nth-child(3) {
    grid-column: 1 / -1; /* 底层计算引擎卡片通栏跨两列 */
    background: #eff6ff;
    border-color: #bfdbfe;
  }

  .meta-label {
    font-size: 11px !important;
  }

  .meta-value {
    font-size: 15px !important;
  }

  /* 通用配置卡片内边距紧凑适配 */
  .section-card {
    padding: 14px 12px !important;
    border-radius: 10px !important;
  }

  .card-header-row {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 10px !important;
    margin-bottom: 12px !important;
  }

  .card-header {
    font-size: 16px !important;
    line-height: 1.4;
  }

  .block-sub {
    font-size: 12px !important;
    line-height: 1.5;
  }

  /* 视图切换按钮（卡片 / 表格）：全宽分段开关 (Segmented Control) */
  .view-mode-toggle {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    width: 100% !important;
    gap: 6px !important;
  }

  .view-mode-toggle .btn {
    width: 100% !important;
    height: 34px !important;
    justify-content: center !important;
  }

  /* 筛选工具栏单列化 */
  .filter-toolbar {
    flex-direction: column !important;
    gap: 10px !important;
    margin-bottom: 12px !important;
  }

  .search-box {
    width: 100% !important;
    min-width: 0 !important;
  }

  .filter-dropdowns {
    flex-direction: column !important;
    width: 100% !important;
    gap: 8px !important;
  }

  .scope-select,
  .derived-select {
    width: 100% !important;
    height: 38px !important;
    font-size: 13px !important;
  }

  /* 分类胶囊栏：横向单行顺滑滚动，防止垂直堆叠占满屏幕 */
  .category-pills {
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-top: 10px !important;
    padding-bottom: 6px !important;
    gap: 6px !important;
  }

  .category-pills::-webkit-scrollbar {
    display: none;
  }

  .category-pill {
    flex-shrink: 0 !important;
    white-space: nowrap !important;
    padding: 5px 11px !important;
    font-size: 12px !important;
  }

  /* 🧮 算法指标卡片网格：单列撑满，消除 360px 宽度导致的屏幕横向溢出 */
  .catalog-grid {
    grid-template-columns: 1fr !important;
    gap: 12px !important;
  }

  .metric-card {
    padding: 14px 12px !important;
    border-radius: 10px !important;
  }

  .metric-card-header {
    gap: 8px;
  }

  .metric-title-wrap {
    min-width: 0;
    flex: 1;
  }

  .metric-name {
    font-size: 15px !important;
    word-break: break-word;
  }

  .unit-badge {
    flex-shrink: 0;
    align-self: flex-start;
  }

  .metric-key-bar {
    min-width: 0;
    padding: 4px 6px;
  }

  .metric-key {
    font-size: 12px !important;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
    flex: 1;
  }

  .formula-box {
    padding: 6px 8px !important;
  }

  .formula-code {
    font-size: 12px !important;
  }

  .metric-meta-details {
    font-size: 11.5px !important;
    gap: 6px !important;
  }

  .meta-row {
    flex-wrap: wrap;
    gap: 4px;
  }

  .row-label {
    min-width: 58px;
  }

  .sandbox-trigger-btn {
    height: 38px !important;
    font-size: 13px !important;
  }

  /* 紧凑表格视图横向滚动包裹 */
  .table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
  }

  .catalog-table {
    min-width: 680px;
  }

  /* 🧪 在线沙盒控制区：垂直单列排布，大触控区 */
  .sandbox-control-grid {
    grid-template-columns: 1fr !important;
    gap: 12px !important;
    padding: 12px 10px !important;
  }

  .date-input-group {
    display: flex;
    gap: 6px;
  }

  .date-input-group input[type="date"] {
    flex: 1;
    min-width: 0;
  }

  .sandbox-action-wrap {
    width: 100%;
  }

  .execute-sandbox-btn {
    width: 100% !important;
    height: 42px !important;
    font-size: 14px !important;
    justify-content: center !important;
  }

  /* 沙盒验算结果头部卡片 */
  .result-headline-card {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 8px !important;
    padding: 12px 10px !important;
  }

  .headline-title {
    font-size: 16px !important;
  }

  .headline-meta {
    font-size: 12px !important;
    line-height: 1.5;
  }

  .final-unit-pill {
    align-self: flex-start;
    font-size: 12px !important;
    padding: 2px 8px !important;
  }

  /* 8 窗口结果矩阵卡片：2x2 双列对比排布，在手机上一屏对比 4 个阶段 */
  .matrix-8-windows {
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 8px !important;
  }

  .window-card {
    padding: 10px 8px !important;
  }

  .win-label {
    font-size: 11px !important;
  }

  .win-val {
    font-size: 17px !important;
  }

  .win-peer {
    font-size: 11px !important;
  }

  .win-growth {
    font-size: 11.5px !important;
  }

  /* 推导步骤卡片 */
  .derivation-steps-block {
    padding: 12px 10px !important;
  }

  .steps-heading {
    font-size: 14px !important;
    margin-bottom: 12px !important;
  }

  .timeline-step-item {
    gap: 8px !important;
  }

  .step-num-badge {
    width: 22px !important;
    height: 22px !important;
    font-size: 11px !important;
  }

  .step-title {
    font-size: 13.5px !important;
  }

  .step-desc {
    font-size: 12px !important;
  }

  .step-breakdown-table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .step-subtable {
    min-width: 320px;
  }

  /* Tab 2: ⚙️ 供暖期与时间参数管控 */
  .biz-date-form-row {
    flex-direction: column !important;
    gap: 12px !important;
  }

  .date-picker-field,
  .date-status-card {
    width: 100% !important;
    min-width: 0 !important;
  }

  .date-picker-wrap {
    flex-wrap: wrap;
    gap: 6px;
  }

  .highlight-date-input {
    flex: 1 1 180px;
    min-width: 0;
  }

  .season-control-form-grid {
    grid-template-columns: 1fr !important;
    gap: 12px !important;
  }

  .season-safety-notice {
    padding: 12px 14px !important;
  }

  .safety-title {
    font-size: 13.5px !important;
  }

  .safety-list {
    font-size: 12px !important;
    padding-left: 16px;
  }

  /* Tab 3: 📋 12345 投诉底表 (金山文档) 移动端排版 */
  .kdocs-two-col {
    grid-template-columns: 1fr !important;
    gap: 12px !important;
  }

  .kdocs-action-bar {
    flex-direction: column-reverse !important;
    align-items: stretch !important;
    gap: 12px !important;
    padding-top: 12px !important;
    margin-top: 14px !important;
  }

  .status-summary {
    width: 100%;
    display: flex;
    justify-content: center;
  }

  .status-badge {
    width: 100% !important;
    text-align: center;
    padding: 6px 12px !important;
  }

  .left-actions {
    flex-direction: column !important;
    width: 100% !important;
    gap: 8px !important;
  }

  .left-actions .btn {
    width: 100% !important;
    height: 38px !important;
    justify-content: center !important;
    font-size: 13px !important;
    padding: 0 10px !important;
  }

  .status-row {
    flex-direction: column;
    gap: 2px;
  }

  .status-label {
    width: auto !important;
    font-size: 12px;
  }

  .status-val {
    font-size: 12.5px;
  }

  .preview-metrics-grid {
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 8px !important;
  }

  .metric-mini-card {
    padding: 8px 10px !important;
  }

  .m-val {
    font-size: 15px !important;
  }

  .kdocs-guide-steps {
    padding-left: 16px;
    font-size: 12.5px !important;
    line-height: 1.6;
  }

  /* Tab 5: 🏢 供热单位与组织架构 2 列紧凑排布 */
  .entities-grid {
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 8px !important;
  }

  .entity-card {
    padding: 10px 8px !important;
    gap: 4px !important;
  }

  .entity-name {
    font-size: 13px !important;
  }

  .entity-code {
    font-size: 11px !important;
  }

  .entity-type-badge {
    font-size: 10px !important;
  }

  /* Tab 6: 💻 原始配置代码盒 */
  .json-code-box {
    padding: 10px !important;
    font-size: 11px !important;
    max-height: 320px !important;
  }
}

/* 针对更极窄手机屏幕 (<= 420px，如 iPhone SE, 375px 小屏) 的细节微调 */
@media (max-width: 420px) {
  .tube-page-main {
    padding: 8px 8px 40px !important;
  }

  .premium-topbar h2 {
    font-size: 16.5px !important;
  }

  .topbar-actions .btn {
    font-size: 12px !important;
    padding: 0 4px !important;
  }

  .meta-dashboard {
    gap: 6px !important;
  }

  .meta-dashboard .meta-card {
    padding: 6px 8px !important;
  }

  .meta-value {
    font-size: 14px !important;
  }

  .matrix-8-windows {
    gap: 6px !important;
  }

  .win-val {
    font-size: 15px !important;
  }

  .category-pill {
    padding: 4px 9px !important;
    font-size: 11.5px !important;
  }
}
</style>
