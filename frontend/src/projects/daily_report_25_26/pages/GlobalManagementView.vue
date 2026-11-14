<template>
  <div class="tube-page-root dr-global-mgmt-view">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />

      <!-- 控制台顶栏 -->
      <header class="topbar premium-topbar">
        <div class="topbar-title-group">
          <h2>生产日报子项目 · 全局管理控制台</h2>
          <p class="sub">集中管控业务操作追溯、指标算法字典与沙盒验算、供暖期与业务日期、12345 投诉底表接入及气温自动定时导入。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost btn-back" type="button" @click="goProjectPages">⬅️ 返回功能页</button>
          <button class="btn ghost" type="button" :disabled="loading" @click="refreshAll">
            {{ loading ? '同步配置中…' : '🔄 刷新全局状态' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-tip error">{{ errorMessage }}</p>
      <p v-if="globalTip" :class="['page-tip', globalTip.type]">{{ globalTip.text }}</p>

      <!-- 全局运行概览条 (Quick Dashboard) -->
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
          <div class="meta-card is-highlight">
            <span class="meta-label">底层计算引擎</span>
            <strong class="meta-value highlight-num">DailyDashboardEngine (0.1s)</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">当前运行供暖期</span>
            <strong class="meta-value">{{ currentSeasonCode || '25-26期' }}</strong>
          </div>
          <div class="meta-card is-highlight">
            <span class="meta-label">基准业务日期</span>
            <strong class="meta-value highlight-num">{{ currentBizDate || '加载中…' }}</strong>
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
              <option value="submissions">📋 业务操作记录</option>
              <option value="algorithms">🧮 生产指标与算法体系</option>
              <option value="season_params">⚙️ 供暖期与时间参数</option>
              <option value="kdocs_complaint">📋 12345投诉底表(金山文档)</option>
              <option value="weather_mgmt">⛅ 导入气温数据管理</option>
            </select>
            <span class="select-arrow-icon">▼</span>
          </div>
        </div>

        <!-- 选项卡菜单 (桌面端纵向侧栏 / 移动端横向平滑滚动胶囊栏) -->
        <aside class="admin-sidebar" ref="sidebarRef">
          <div class="sidebar-group-title">管理板块导航</div>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'submissions' }]"
            @click="selectTab('submissions', $event)"
          >
            <span class="tab-icon" aria-hidden="true">📋</span>
            <span class="tab-label">业务操作记录</span>
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'algorithms' }]"
            @click="selectTab('algorithms', $event)"
          >
            <span class="tab-icon" aria-hidden="true">🧮</span>
            <span class="tab-label">生产指标与算法体系</span>
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'season_params' }]"
            @click="selectTab('season_params', $event)"
          >
            <span class="tab-icon" aria-hidden="true">⚙️</span>
            <span class="tab-label">供暖期与时间参数</span>
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'kdocs_complaint' }]"
            @click="selectTab('kdocs_complaint', $event)"
          >
            <span class="tab-icon" aria-hidden="true">📊</span>
            <span class="tab-label">12345投诉底表(金山)</span>
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'weather_mgmt' }]"
            @click="selectTab('weather_mgmt', $event)"
          >
            <span class="tab-icon" aria-hidden="true">⛅</span>
            <span class="tab-label">导入气温数据管理</span>
          </button>
        </aside>

        <!-- 右侧当前选中的配置主卡片 -->
        <div class="admin-content-pane">
          <!-- ========================================== -->
          <!-- Tab 0: 📋 业务操作记录 (首发核心监控板块) -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'submissions'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">📋 业务操作记录</div>
                  <p class="sub block-sub">
                    全链路物理追溯与核验生产单位填报提交、审核流转、气象数据抓取、现货同步与综合调阅流水。
                  </p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost compact-btn" type="button" @click="fetchSubmissionLogs(1)">
                    🔄 刷新操作记录
                  </button>
                </div>
              </div>

              <!-- 数据新旧核对面板 -->
              <div class="submission-overview">
                <div class="submission-overview__lead">
                  <div class="submission-overview__icon" aria-hidden="true">⏱️</div>
                  <div class="submission-overview__copy">
                    <div class="submission-overview__label">数据库最新操作物理时间</div>
                    <div class="submission-overview__time">
                      <span>{{ submissionLatestTime ? formatDateTime(submissionLatestTime) : '尚无操作记录' }}</span>
                      <span
                        v-if="submissionLatestTime"
                        class="submission-overview__age"
                        :style="getTimeAgoBadgeStyle(submissionLatestTime)"
                      >
                        {{ formatTimeAgo(submissionLatestTime) }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- 24h 操作小计数看板 -->
                <div class="submission-metrics">
                  <div class="submission-metric submission-metric--total">
                    <div class="submission-metric__label">24h 操作总量</div>
                    <div class="submission-metric__value">{{ recent24hCount }} <span>笔</span></div>
                  </div>
                  <div class="submission-metric submission-metric--demand">
                    <div class="submission-metric__label">数据填报提交</div>
                    <div class="submission-metric__value">{{ submission24hCount }} <span>笔</span></div>
                  </div>
                  <div class="submission-metric submission-metric--supply">
                    <div class="submission-metric__label">审核与发布流转</div>
                    <div class="submission-metric__value">{{ workflow24hCount }} <span>笔</span></div>
                  </div>
                  <div class="submission-metric submission-metric--query">
                    <div class="submission-metric__label">综合数据调阅</div>
                    <div class="submission-metric__value">{{ query24hCount }} <span>笔</span></div>
                  </div>
                </div>
              </div>

              <!-- 结构化过滤控制面板 -->
              <div class="submission-filter-panel">
                <label class="submission-filter-item">
                  <span>操作行为大类</span>
                  <select v-model="submissionFilters.category" class="select" @change="onSubmissionCategoryChange">
                    <option value="">全部大类 (提交 / 审核 / 调阅)</option>
                    <option value="submission">📥 业务数据提交类</option>
                    <option value="workflow">⚖️ 审核与流转类</option>
                    <option value="query">🔍 综合数据调阅类</option>
                  </select>
                </label>

                <label class="submission-filter-item">
                  <span>生产单位与主体分类</span>
                  <select v-model="submissionFilters.entityType" class="select" @change="fetchSubmissionLogs(1)">
                    <option value="">全部主体与单位</option>
                    <option value="北海">🏭 北海热电厂 (BeiHai)</option>
                    <option value="金州">🏭 金州热电 (JinZhou)</option>
                    <option value="香海">🏭 香海热电厂 (XiangHai)</option>
                    <option value="北方">🏭 北方热电 (BeiFang)</option>
                    <option value="金普">🏭 金普热电 (JinPu)</option>
                    <option value="庄河">🏭 庄河热电 (ZhuangHe)</option>
                    <option value="供热">🏢 供热分公司 (GongRe)</option>
                    <option value="主城区">🏙️ 主城区 (ZhuChengQu)</option>
                    <option value="售电">⚡ 售电公司 (ShouDian)</option>
                    <option value="研究院">🔬 研究院 (YanJiuYuan)</option>
                    <option value="集团">🏢 集团经济运行部 / 汇总</option>
                    <option value="调度">⏱️ 生产调度中心</option>
                    <option value="现货">⚡ 电力现货交易中心</option>
                  </select>
                </label>

                <label class="submission-filter-item">
                  <span>具体操作行为</span>
                  <select v-model="submissionFilters.actionType" class="select" @change="fetchSubmissionLogs(1)">
                    <option value="">全部具体行为</option>
                    <optgroup v-if="submissionFilters.category !== 'query' && submissionFilters.category !== 'workflow'" label="📥 业务数据提交行为">
                      <option value="SUBMIT_ENTRY">📝 日报数据填报提交</option>
                      <option value="SUBMIT_CORRECTION">🛠️ 提交数据修正申请</option>
                      <option value="IMPORT_COMPLAINT">📋 12345投诉底表拉取填入</option>
                      <option value="IMPORT_TEMPERATURE">⛅ 气象气温导入入库</option>
                      <option value="SYNC_SPOT_ELEC">⚡ 电力现货量价数据同步</option>
                      <option value="IMPORT_DISPATCH">⏱️ 机炉调度信息维护</option>
                      <option value="IMPORT_EFFICIENCY">📊 能效/生产Excel导入</option>
                      <option value="UPDATE_COAL_PLAN">🎯 标煤动态分解计划维护</option>
                      <option value="UPDATE_CONFIG">⚙️ 全局核心运行参数修改</option>
                    </optgroup>
                    <optgroup v-if="submissionFilters.category !== 'submission' && submissionFilters.category !== 'query'" label="⚖️ 审核与发布流转">
                      <option value="APPROVE_UNIT">✅ 单位填报审核通过</option>
                      <option value="REVOKE_UNIT">↩️ 撤销单位审核状态</option>
                      <option value="PUBLISH_DAILY">📢 正式发布集团生产日报</option>
                      <option value="REVOKE_PUBLISH">❌ 撤销已发布日报状态</option>
                      <option value="APPROVE_CORRECTION">✅ 批准数据修正申请</option>
                      <option value="REJECT_CORRECTION">🚫 驳回数据修正申请</option>
                    </optgroup>
                    <optgroup v-if="submissionFilters.category !== 'submission' && submissionFilters.category !== 'workflow'" label="🔍 综合数据调阅与导出">
                      <option value="EXPORT_DASHBOARD_PDF">📑 导出标准宽屏看板 PDF</option>
                      <option value="EXPORT_DAILY_BRIEF_PDF">📰 导出每日内参简报 PDF</option>
                      <option value="EXPORT_SHEET_DATA">📥 导出报表 Excel / CSV / 截图</option>
                      <option value="QUERY_DASHBOARD">📊 调阅生产经营数据看板</option>
                      <option value="QUERY_SHEET_DATA">📋 查阅单位报表明细</option>
                      <option value="QUERY_DATA_ANALYSIS">📈 生产多维数据智能分析</option>
                      <option value="QUERY_DISPATCH_INFO">⏱️ 调阅机炉运行调度记录</option>
                      <option value="QUERY_DYNAMIC_PLAN">🎯 调阅标煤动态分解计划</option>
                      <option value="QUERY_SPOT_ELEC">⚡ 查阅电力现货市场行情</option>
                      <option value="QUERY_DAILY_BRIEF">📰 调阅每日生产内参简报</option>
                    </optgroup>
                  </select>
                </label>

                <label class="submission-filter-item">
                  <span>操作账号 / 操作人</span>
                  <input v-model.trim="submissionFilters.operator" class="input" type="text" placeholder="搜索账号或姓名" />
                </label>

                <label class="submission-filter-item">
                  <span>开始日期</span>
                  <input v-model="submissionFilters.startDate" class="input" type="date" />
                </label>

                <label class="submission-filter-item">
                  <span>结束日期</span>
                  <input v-model="submissionFilters.endDate" class="input" type="date" />
                </label>

                <div class="submission-filter-actions">
                  <button class="btn ghost submission-reset-btn" type="button" @click="resetSubmissionFilters">
                    🔄 重置
                  </button>
                  <button class="btn primary submission-query-btn" type="button" @click="fetchSubmissionLogs(1)">
                    🔍 查询操作记录
                  </button>
                </div>
              </div>

              <!-- 操作记录明细列表 -->
              <div v-if="submissionLoading" class="table-state-placeholder">正在加载业务操作记录…</div>
              <div v-else-if="submissionLogs.length === 0" class="table-state-placeholder">未查询到符合条件的业务操作记录。</div>
              <div v-else>
                <div class="submission-table-wrap">
                  <table class="table editor-table submission-log-table">
                    <colgroup>
                      <col class="submission-col-time" />
                      <col class="submission-col-operator" />
                      <col class="submission-col-action" />
                      <col class="submission-col-detail" />
                    </colgroup>
                    <thead>
                      <tr>
                        <th>操作时间与来源 IP</th>
                        <th>操作主体 / 操作人</th>
                        <th>行为类型</th>
                        <th>业务操作内容与详情说明</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="log in submissionLogs" :key="log.id">
                        <td class="submission-time-cell">
                          <div class="submission-time-value">
                            {{ formatDateTime(log.created_at) }}
                          </div>
                          <div class="submission-time-meta">
                            <span v-if="isRecent24h(log.created_at)" class="submission-recent-badge">
                              🔥 新操作
                            </span>
                            <span v-if="log.client_ip" class="submission-ip" :title="`来源 IP: ${log.client_ip}`">
                              📍 IP: {{ log.client_ip }}
                            </span>
                          </div>
                        </td>
                        <td class="submission-operator-cell">
                          <div class="submission-operator-name">
                            <span class="user-name-text">{{ log.operator }}</span>
                          </div>
                          <div class="submission-operator-meta">
                            <span v-if="log.unit" class="submission-group-chip submission-unit-chip" :title="`所属单位: ${log.unit}`">
                              🏢 {{ log.unit }}
                            </span>
                            <span v-if="log.operator_group && log.operator_group !== log.unit" class="submission-group-chip">
                              {{ log.operator_group }}
                            </span>
                          </div>
                        </td>
                        <td class="submission-action-cell">
                          <span class="badge submission-action-badge" :style="getActionTypeBadgeStyle(log.action_type)">
                            {{ translateActionType(log.action_type) }}
                          </span>
                        </td>
                        <td class="submission-detail-cell">
                          <div class="submission-detail-text">
                            <span v-if="log.resource_id" class="submission-section-chip" :title="`关联业务标识: ${log.resource_id}`">
                              🏷️ {{ log.resource_id }}
                            </span>
                            <span class="submission-desc-text">{{ log.action_desc }}</span>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 分页栏 -->
                <div class="submission-pagination">
                  <span class="submission-pagination__summary">共计 <strong>{{ submissionTotal }}</strong> 条业务操作记录</span>
                  <div class="submission-pagination__controls">
                    <button class="btn ghost compact-btn submission-page-btn" type="button" :disabled="submissionPage <= 1" @click="fetchSubmissionLogs(submissionPage - 1)">上一页</button>
                    <span>第 <strong>{{ submissionPage }}</strong> 页 / 共 <strong>{{ Math.ceil(submissionTotal / submissionLimit) || 1 }}</strong> 页</span>
                    <button class="btn ghost compact-btn submission-page-btn" type="button" :disabled="submissionPage >= Math.ceil(submissionTotal / submissionLimit)" @click="fetchSubmissionLogs(submissionPage + 1)">下一页</button>
                  </div>
                </div>
              </div>
            </section>
          </div>

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

              <!-- 筛选命中汇总栏 -->
              <div class="catalog-result-bar">
                <span class="catalog-result-summary">
                  当前显示 <strong>{{ filteredCatalog.length }}</strong> / {{ catalogList.length }} 项指标
                </span>
                <button
                  v-if="searchKeyword || selectedScopeFilter !== 'all' || selectedDerivedFilter !== 'all' || activeCategoryKey !== 'all'"
                  type="button"
                  class="btn ghost compact-btn"
                  @click="searchKeyword = ''; selectedScopeFilter = 'all'; selectedDerivedFilter = 'all'; activeCategoryKey = 'all'"
                >
                  ✕ 清空全部筛选
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
                  <div class="card-header-with-tag">
                    <span class="card-header">🧪 算法在线实时验算沙盒 (Live Calculator Sandbox)</span>
                    <span class="header-pill is-primary">实时引擎直连</span>
                  </div>
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
          <!-- Tab 2: ⚙️ 供暖期与时间参数 -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'season_params'" class="pane-content-wrapper">
            <!-- 板块 1：📅 系统基准业务日期管控 (Base Business Date) -->
            <section class="card elevated section-card biz-date-controller-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header-with-tag">
                    <span class="card-header">📅 全局基准业务日期管控 (Global Business Date)</span>
                    <span class="header-pill is-success">全站时间锚点</span>
                  </div>
                  <p class="sub block-sub">
                    设定系统默认的业务基准日期（<code>set_biz_date</code>）。此日期决定生产大盘首屏、日报填报默认日历及各模块的锚点基准。
                  </p>
                </div>
                <div class="section-actions">
                  <button
                    class="btn primary execute-sandbox-btn"
                    type="button"
                    :disabled="savingBizDate"
                    @click="saveBizDate"
                  >
                    {{ savingBizDate ? '💾 正在保存…' : '💾 保存业务日期生效' }}
                  </button>
                </div>
              </div>

              <!-- 业务日期反馈提示 -->
              <div v-if="bizDateTip" :class="['page-tip', bizDateTip.type]">
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
                  <span class="status-label">当前生效业务日期</span>
                  <strong class="status-val">{{ currentBizDate || '未设置' }}</strong>
                  <span class="status-sub">存储：config/project_settings.json → biz_date</span>
                </div>
              </div>
            </section>

            <!-- 板块 2：⚙️ 供暖期同项目无损滚动中枢 (Season Roll) -->
            <section class="card elevated section-card season-controller-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header-with-tag">
                    <span class="card-header">⚙️ 供暖期同项目滚动控制台</span>
                    <span class="header-pill is-primary">当前期 {{ currentSeasonCode || selectedPeriod }}</span>
                  </div>
                  <p class="sub block-sub">
                    手动设置或滚动当前供暖期。系统将自动联动：常量表动态列头、历史同期只读参考、入库 period 编码及基准业务日期。
                  </p>
                </div>
                <div class="section-actions">
                  <button
                    class="btn primary execute-sandbox-btn"
                    type="button"
                    :disabled="savingSeason"
                    @click="saveSeasonConfig"
                  >
                    {{ savingSeason ? '💾 正在保存生效…' : '💾 保存并切换供暖期' }}
                  </button>
                </div>
              </div>

              <!-- 切换反馈提示 -->
              <div v-if="seasonTip" :class="['page-tip', seasonTip.type]">
                {{ seasonTip.text }}
              </div>

              <!-- 分组 1：周期选择与联动 -->
              <div class="form-group-panel">
                <div class="form-group-title">1. 供暖周期选择与日期联动</div>
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
                      <label for="auto-align-date-check" class="align-checkbox-label">自动对齐至开栓首日 ({{ formStartDate }})</label>
                    </div>
                    <small class="field-help">开启后，切换供暖期将自动将全局业务基准日期设为开栓日。</small>
                  </label>
                </div>
              </div>

              <!-- 分组 2：统计时间窗口参数（本期 3 项 + 同期 3 项，三列对称） -->
              <div class="form-group-panel">
                <div class="form-group-title">2. 本期与历史同期统计时间窗口</div>
                <div class="season-control-form-grid">
                  <label class="field">
                    <span class="field-title">日报统计开始日（本期）</span>
                    <input v-model="formStartDate" type="date" class="input" />
                    <small class="field-help">月累计、近7日与供暖期累计均只统计此日起的数据。</small>
                  </label>

                  <label class="field">
                    <span class="field-title">日报统计结束日（本期）</span>
                    <input v-model="formEndDate" type="date" class="input" />
                    <small class="field-help">累计统计止于此日，之后录入的当日明细仍可查询。</small>
                  </label>

                  <label class="field">
                    <span class="field-title">平均气温起算日（本期）</span>
                    <input v-model="formTemperatureStartDate" type="date" class="input" />
                    <small class="field-help">默认当期 11 月 1 日，期均温计算至查询日。</small>
                  </label>

                  <label class="field">
                    <span class="field-title">同期日报统计开始日（{{ seasonConfig.peer_period }}）</span>
                    <input v-model="formPeerStartDate" type="date" class="input" />
                  </label>

                  <label class="field">
                    <span class="field-title">同期日报统计结束日（{{ seasonConfig.peer_period }}）</span>
                    <input v-model="formPeerEndDate" type="date" class="input" />
                  </label>

                  <label class="field">
                    <span class="field-title">同期平均气温起算日（{{ seasonConfig.peer_period }}）</span>
                    <input v-model="formPeerTemperatureStartDate" type="date" class="input" />
                    <small class="field-help">本期与同期分别保存各自日期设置，互不干扰。</small>
                  </label>

                  <label class="field full-width">
                    <span class="field-title">📝 供暖期切换说明 / 备注</span>
                    <input v-model="formDescription" type="text" class="input" placeholder="输入切换原因或备忘说明…" />
                  </label>
                </div>
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
          </div>

          <!-- ========================================== -->
          <!-- Tab 3: 📋 12345投诉底表 (金山文档) 接入与配置 -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'kdocs_complaint'" class="pane-content-wrapper">
            <section class="card elevated section-card kdocs-config-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header-with-tag">
                    <span class="card-header">📊 12345 诉求件统计底表 · 金山文档接入配置</span>
                    <span class="header-pill is-primary">底表直连同步</span>
                  </div>
                  <p class="sub block-sub">
                    统一维护金山文档共享链接及授权凭证 (<code>wps_sid</code>)，支持免人工下载直接拉取最新底表并试算当日投诉指标。
                  </p>
                </div>
                <div class="section-actions">
                  <button
                    class="btn primary execute-sandbox-btn"
                    type="button"
                    :disabled="savingKdocs"
                    @click="saveKdocsConfig"
                  >
                    {{ savingKdocs ? '💾 正在保存…' : '💾 保存配置' }}
                  </button>
                </div>
              </div>

              <!-- 提示通知横幅 -->
              <div v-if="kdocsTip" :class="['page-tip', kdocsTip.type]">
                {{ kdocsTip.text }}
              </div>

              <!-- 表单区域 -->
              <div class="form-group-panel kdocs-form-panel">
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
                        class="input readonly-input font-mono"
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
                    class="btn light compact-btn"
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
                  <span class="status-label">最近测试时间</span>
                  <span class="status-val font-mono">{{ kdocsTestResult?.test_time || kdocsConfig.last_test_time || '未测试' }}</span>
                </div>
                <div class="status-row">
                  <span class="status-label">诊断结果说明</span>
                  <span class="status-val status-desc">{{ kdocsTestResult?.message || kdocsConfig.last_test_message || '暂无信息' }}</span>
                </div>
                <div v-if="kdocsConfig.last_sync_time" class="status-row">
                  <span class="status-label">最后同步时间</span>
                  <span class="status-val font-mono">{{ kdocsConfig.last_sync_time }}</span>
                </div>
              </div>

              <!-- 试算结果预览卡片 -->
              <div v-if="kdocsSyncResult" class="sync-preview-card">
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
              <div class="card-header-row">
                <div>
                  <div class="card-header">💡 如何获取或更新 WPS 身份凭证 (wps_sid)？</div>
                  <p class="sub block-sub">当提示凭证失效或需更换授权账号时，按下方步骤在浏览器重新复制 Cookie 即可。</p>
                </div>
              </div>
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
          <!-- Tab 4: ⛅ 导入气温数据管理 -->
          <!-- ========================================== -->
          <div v-if="activeTab === 'weather_mgmt'" class="pane-content-wrapper">
            <section class="card elevated section-card weather-module-header-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header-with-tag">
                    <span class="card-header">⛅ 气温导入数据管理中心</span>
                    <span class="header-pill is-primary">双模块独立调度</span>
                  </div>
                  <p class="sub block-sub">
                    实况与短期气温导入（数据看板）与 35 天集合气温预报导入（计划情景分解模型）各自独立工作，支持分别配置 API 地址、每日多时段自动获取与成功/失败状态追踪；两处业务页面的手动导入功能同步保留。
                  </p>
                </div>
              </div>

              <div class="weather-subtab-bar" role="tablist" aria-label="气温导入模块切换">
                <button
                  type="button"
                  role="tab"
                  :aria-selected="weatherSubTab === 'near'"
                  :class="['weather-subtab-btn', { active: weatherSubTab === 'near' }]"
                  @click="weatherSubTab = 'near'"
                >
                  <span class="subtab-main">🌡️ 近端实况气温导入（数据看板）</span>
                  <span class="subtab-tag">type=near</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  :aria-selected="weatherSubTab === 'ensemble'"
                  :class="['weather-subtab-btn', { active: weatherSubTab === 'ensemble' }]"
                  @click="weatherSubTab = 'ensemble'"
                >
                  <span class="subtab-main">🔮 35天集合气温预报导入（计划情景模型）</span>
                  <span class="subtab-tag">type=far</span>
                </button>
              </div>
            </section>

            <WeatherImportModulePanel
              v-show="weatherSubTab === 'near'"
              ref="nearWeatherPanelRef"
              :project-key="projectKey"
              title="🌡️ 近端实况气温导入（数据看板）"
              subtitle="集中管理 Open-Meteo 逐小时实况与短期预报（type=near）API 来源、多时段自动定时获取与入库状态追踪；数据看板手动“导入气温”同步保留并记录到本模块历史。"
              schedule-hint="针对气温 API 偶发无法连接的情况，可设置每日多个尝试时间点（北京时间 24 小时制）；到点后系统自动尝试拉取并按时间覆盖写入 temperature_data（type=near）。"
              api-title="🔗 近端实况气温 API 数据源配置"
              api-subtitle="数据看板手动“导入气温”与管理中心自动定时获取共用此数据源地址。"
              api-field-label="近端气温导入 API 地址"
              api-format-hint="接口须返回 Open-Meteo 兼容的 hourly.time 和 hourly.temperature_2m 数组。保存配置不会请求天气接口或写入气温数据。"
              default-new-time="08:00"
              :get-api-config-fn="getTemperatureImportConfig"
              :save-api-config-fn="saveTemperatureImportConfig"
              :get-auto-status-fn="getTemperatureAutoImportStatus"
              :save-auto-config-fn="saveTemperatureAutoImportConfig"
              :run-import-now-fn="runTemperatureImportNow"
            />

            <WeatherImportModulePanel
              v-show="weatherSubTab === 'ensemble'"
              ref="ensembleWeatherPanelRef"
              :project-key="projectKey"
              title="🔮 35天集合气温预报导入（计划情景模型）"
              subtitle="集中管理 Open-Meteo Ensemble API 未来 35 天逐小时均值气温预报（type=far）的来源、多时段自动定时获取与状态追踪；计划情景分解模型页原有“导入35天预报”按钮同步保留。"
              schedule-hint="可设置每日多个尝试时间点（北京时间 24 小时制）；到点后自动拉取 35 天集合预报并按小时均值入库（仅写入未存在近端实况的时段，不会覆盖 type=near 数据）。"
              api-title="🔗 35天集合气温预报 API 数据源配置"
              api-subtitle="计划情景分解模型页面手动“导入35天预报”与本模块定时任务共用此 API 地址。"
              api-field-label="35天集合预报 API 地址"
              api-format-hint="接口须返回 Open-Meteo Ensemble API 兼容的 hourly.time 以及多个 temperature_2m* 成员数组。保存配置不会立即请求天气接口或写入数据库。"
              default-new-time="07:30"
              :get-api-config-fn="getEnsembleTemperatureImportConfig"
              :save-api-config-fn="saveEnsembleTemperatureImportConfig"
              :get-auto-status-fn="getEnsembleTemperatureAutoImportStatus"
              :save-auto-config-fn="saveEnsembleTemperatureAutoImportConfig"
              :run-import-now-fn="runEnsembleTemperatureImportNow"
            />
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
import WeatherImportModulePanel from '../components/WeatherImportModulePanel.vue'
import { getProjectNameById, ensureProjectsLoaded } from '../composables/useProjects'
import {
  getTemperatureImportConfig,
  saveTemperatureImportConfig,
  getTemperatureAutoImportStatus,
  saveTemperatureAutoImportConfig,
  runTemperatureImportNow,
  getEnsembleTemperatureImportConfig,
  saveEnsembleTemperatureImportConfig,
  getEnsembleTemperatureAutoImportStatus,
  saveEnsembleTemperatureAutoImportConfig,
  runEnsembleTemperatureImportNow,
  getDailyReportSubmissionLogs,
} from '../services/api'

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
const initialTab = String(route.query.tab || '').trim() || 'submissions'
const activeTab = ref(initialTab)
const viewMode = ref('cards') // 'cards' | 'table'
const sidebarRef = ref(null)

function selectTab(tabKey, event) {
  activeTab.value = tabKey
  if (tabKey === 'submissions') {
    fetchSubmissionLogs(1)
  } else if (tabKey === 'weather_mgmt') {
    refreshWeatherPanels()
  }
  if (event && event.currentTarget && typeof event.currentTarget.scrollIntoView === 'function') {
    event.currentTarget.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  }
}

function onMobileSelectChange() {
  if (activeTab.value === 'submissions') {
    fetchSubmissionLogs(1)
  } else if (activeTab.value === 'weather_mgmt') {
    refreshWeatherPanels()
  }
  setTimeout(() => {
    const activeEl = sidebarRef.value?.querySelector('.sidebar-tab-btn.active')
    if (activeEl && typeof activeEl.scrollIntoView === 'function') {
      activeEl.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
    }
  }, 50)
}

// ==================== 📋 业务操作记录响应式状态与逻辑 ====================
const submissionLoading = ref(false)
const submissionLogs = ref([])
const submissionTotal = ref(0)
const submissionPage = ref(1)
const submissionLimit = ref(50)
const submissionLatestTime = ref(null)
const recent24hCount = ref(0)
const submission24hCount = ref(0)
const workflow24hCount = ref(0)
const query24hCount = ref(0)

const submissionFilters = ref({
  category: '',
  entityType: '',
  actionType: '',
  operator: '',
  startDate: '',
  endDate: '',
})

function onSubmissionCategoryChange() {
  const categoryActions = {
    submission: [
      'SUBMIT_ENTRY', 'SUBMIT_SHEET', 'SUBMIT_CORRECTION',
      'IMPORT_COMPLAINT', 'IMPORT_TEMPERATURE', 'SYNC_SPOT_ELEC',
      'IMPORT_DISPATCH', 'IMPORT_EFFICIENCY', 'IMPORT_XLSX',
      'UPDATE_COAL_PLAN', 'UPDATE_CONFIG',
    ],
    workflow: [
      'APPROVE_UNIT', 'REVOKE_UNIT', 'PUBLISH_DAILY', 'REVOKE_PUBLISH',
      'APPROVE_CORRECTION', 'REJECT_CORRECTION', 'AUDIT_RESET',
    ],
    query: [
      'EXPORT_DASHBOARD_PDF', 'EXPORT_DAILY_BRIEF_PDF', 'EXPORT_SHEET_DATA',
      'QUERY_DASHBOARD', 'QUERY_SHEET_DATA', 'QUERY_DATA_ANALYSIS',
      'QUERY_DISPATCH_INFO', 'QUERY_DYNAMIC_PLAN', 'QUERY_SPOT_ELEC', 'QUERY_DAILY_BRIEF',
    ],
  }
  const allowed = categoryActions[submissionFilters.value.category]
  if (allowed && submissionFilters.value.actionType && !allowed.includes(submissionFilters.value.actionType)) {
    submissionFilters.value.actionType = ''
  }
  fetchSubmissionLogs(1)
}

function resetSubmissionFilters() {
  submissionFilters.value = {
    category: '',
    entityType: '',
    actionType: '',
    operator: '',
    startDate: '',
    endDate: '',
  }
  fetchSubmissionLogs(1)
}

async function fetchSubmissionLogs(page = 1) {
  submissionLoading.value = true
  submissionPage.value = page
  try {
    const res = await getDailyReportSubmissionLogs(projectKey, {
      category: submissionFilters.value.category,
      entityType: submissionFilters.value.entityType,
      actionType: submissionFilters.value.actionType,
      operator: submissionFilters.value.operator,
      startDate: submissionFilters.value.startDate,
      endDate: submissionFilters.value.endDate,
      page: submissionPage.value,
      limit: submissionLimit.value,
    })
    submissionLogs.value = res.rows || []
    submissionTotal.value = res.total || 0
    submissionLatestTime.value = res.latest_submitted_at || null
    recent24hCount.value = res.recent_24h_count || 0
    submission24hCount.value = res.submission_24h_count || 0
    workflow24hCount.value = res.workflow_24h_count || 0
    query24hCount.value = res.query_24h_count || 0
  } catch (err) {
    console.error('加载生产日报业务操作记录失败:', err)
  } finally {
    submissionLoading.value = false
  }
}

function isRecent24h(isoString) {
  if (!isoString) return false
  const t = new Date(isoString).getTime()
  return Date.now() - t <= 24 * 60 * 60 * 1000
}

function formatTimeAgo(isoString) {
  if (!isoString) return ''
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  return `${Math.floor(diff / 86400)} 天前`
}

function getTimeAgoBadgeStyle(isoString) {
  if (!isoString) return {}
  const hours = (Date.now() - new Date(isoString).getTime()) / (3600 * 1000)
  if (hours <= 2) return { background: '#fef2f2', color: '#dc2626', border: '1px solid #fca5a5' }
  if (hours <= 24) return { background: '#fffbe3', color: '#b45309', border: '1px solid #fde68a' }
  return { background: '#f1f5f9', color: '#475569', border: '1px solid #cbd5e1' }
}

function formatDateTime(isoString) {
  if (!isoString) return '—'
  const d = new Date(isoString)
  if (Number.isNaN(d.getTime())) return String(isoString)
  const Y = d.getFullYear()
  const M = String(d.getMonth() + 1).padStart(2, '0')
  const D = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  return `${Y}-${M}-${D} ${h}:${m}:${s}`
}

function getActionTypeBadgeStyle(actionType) {
  const type = String(actionType || '').toUpperCase()
  if (type.startsWith('SUBMIT') || type === 'SAVE_ENTRY') {
    return { background: '#ecfdf5', color: '#059669', border: '1px solid #a7f3d0' }
  }
  if (type.startsWith('APPROVE') || type.startsWith('PUBLISH')) {
    return { background: '#f5f3ff', color: '#7c3aed', border: '1px solid #ddd6fe' }
  }
  if (type.startsWith('IMPORT') || type.startsWith('SYNC')) {
    return { background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe' }
  }
  if (type.startsWith('REVOKE') || type.startsWith('REJECT') || type.includes('CANCEL') || type.includes('RESET')) {
    return { background: '#fff7ed', color: '#ea580c', border: '1px solid #fed7aa' }
  }
  if (type.startsWith('QUERY') || type.startsWith('EXPORT')) {
    return { background: '#f0fdf4', color: '#16a34a', border: '1px solid #bbf7d0' }
  }
  return { background: '#f8fafc', color: '#475569', border: '1px solid #e2e8f0' }
}

function translateActionType(actionType) {
  const map = {
    SUBMIT_ENTRY: '📝 填报提交',
    SUBMIT_SHEET: '📝 表单提交',
    SUBMIT_CORRECTION: '🛠️ 提交修正',
    IMPORT_COMPLAINT: '📋 投诉拉取',
    IMPORT_TEMPERATURE: '⛅ 气象导入',
    SYNC_SPOT_ELEC: '⚡ 现货同步',
    IMPORT_DISPATCH: '⏱️ 调度维护',
    IMPORT_EFFICIENCY: '📊 能效导入',
    IMPORT_XLSX: '📥 表格导入',
    UPDATE_COAL_PLAN: '🎯 标煤维护',
    UPDATE_CONFIG: '⚙️ 参数修改',
    APPROVE_UNIT: '✅ 审核通过',
    REVOKE_UNIT: '↩️ 撤销审核',
    PUBLISH_DAILY: '📢 日报发布',
    REVOKE_PUBLISH: '❌ 撤销发布',
    APPROVE_CORRECTION: '✅ 批准修正',
    REJECT_CORRECTION: '🚫 驳回修正',
    AUDIT_RESET: '🔄 审计重置',
    EXPORT_DASHBOARD_PDF: '📑 导出PDF',
    EXPORT_DAILY_BRIEF_PDF: '📰 导出简报',
    EXPORT_SHEET_DATA: '📥 导出明细',
    QUERY_DASHBOARD: '📊 看板调阅',
    QUERY_SHEET_DATA: '📋 报表调阅',
    QUERY_DATA_ANALYSIS: '📈 综合分析',
    QUERY_DISPATCH_INFO: '⏱️ 调度调阅',
    QUERY_DYNAMIC_PLAN: '🎯 计划调阅',
    QUERY_SPOT_ELEC: '⚡ 现货调阅',
    QUERY_DAILY_BRIEF: '📰 简报调阅',
  }
  return map[actionType] || actionType
}

// 基础状态
const loading = ref(false)
const errorMessage = ref('')
const globalTip = ref(null)
// 气温导入双模块（近端实况气温 + 35天集合预报）切换与统一刷新
const weatherSubTab = ref('near')
const nearWeatherPanelRef = ref(null)
const ensembleWeatherPanelRef = ref(null)

async function refreshWeatherPanels() {
  await Promise.all([
    nearWeatherPanelRef.value?.refresh?.(),
    ensembleWeatherPanelRef.value?.refresh?.(),
  ])
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
  fetchSubmissionLogs(1).catch(() => {})
  await loadSeasonConfig()
  await loadBizDate()
  await loadCatalog()
  await loadKdocsConfig()
  await refreshWeatherPanels()
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
  await fetchSubmissionLogs(submissionPage.value || 1).catch(() => {})
  await refreshWeatherPanels()
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
/* ==================== 🎨 全局统一布局骨架与设计系统 ==================== */
.dr-global-mgmt-view {
  min-height: 100vh;
  background: #f4f7fb;
  color: #0f172a;
}

.tube-page-main {
  max-width: 1440px;
  margin: 0 auto;
  padding: 18px 24px 64px;
}

/* 统一输入与按钮尺度，消除跨标签高低差 */
.dr-global-mgmt-view :deep(.input),
.dr-global-mgmt-view .input,
.dr-global-mgmt-view .select {
  height: 38px;
  min-width: 0;
  padding: 0 12px;
  border: 1px solid #cbd5e1;
  border-radius: 9px;
  background: #ffffff;
  color: #0f172a;
  font-size: 13.5px;
  box-sizing: border-box;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.dr-global-mgmt-view textarea.input {
  height: auto;
  padding: 9px 12px;
  line-height: 1.5;
}

.dr-global-mgmt-view .input:focus,
.dr-global-mgmt-view .select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
  outline: none;
}

.dr-global-mgmt-view .btn {
  height: 38px;
  padding: 0 15px;
  border-radius: 9px;
  font-size: 13.5px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.16s ease;
  white-space: nowrap;
}

.dr-global-mgmt-view .btn.compact-btn {
  height: 34px;
  padding: 0 12px;
  font-size: 12.5px;
  border-radius: 8px;
}

.dr-global-mgmt-view .btn.primary {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  border-color: #1d4ed8;
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.22);
}

.dr-global-mgmt-view .btn.primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
  transform: translateY(-0.5px);
}

.dr-global-mgmt-view .btn.ghost {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #334155;
}

.dr-global-mgmt-view .btn.ghost:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #94a3b8;
  color: #0f172a;
}

/* 统一页面/表单反馈横幅 */
.page-tip,
.page-error {
  margin: 0 0 16px;
  padding: 11px 15px;
  border-radius: 10px;
  font-size: 13.5px;
  font-weight: 500;
  line-height: 1.5;
}

.page-tip.success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.page-tip.error,
.page-error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

/* 顶栏 */
.premium-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin: 10px 0 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.topbar-title-group {
  min-width: 0;
}

.premium-topbar h2 {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.01em;
  margin: 0 0 4px;
}

.premium-topbar .sub {
  font-size: 13.5px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

/* 全局运行概览条 (Quick Dashboard) */
.quick-dashboard-card {
  margin-bottom: 20px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 6px 18px rgba(15, 23, 42, 0.03);
}

.meta-dashboard {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.meta-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.meta-card.is-highlight {
  background: linear-gradient(180deg, #eff6ff 0%, #f8fbff 100%);
  border-color: #bfdbfe;
}

.meta-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.meta-value {
  font-size: 16.5px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}

.highlight-num {
  color: #1d4ed8;
}

/* 双栏工作台 */
.admin-workbench-layout {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.mobile-tab-switcher {
  display: none;
}

.admin-sidebar {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  position: sticky;
  top: 76px;
  z-index: 10;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 6px 18px rgba(15, 23, 42, 0.03);
}

.sidebar-group-title {
  padding: 4px 12px 8px;
  font-size: 11.5px;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 1px solid #f1f5f9;
  margin-bottom: 4px;
}

.sidebar-tab-btn {
  position: relative;
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 13.5px;
  font-weight: 600;
  color: #475569;
  text-align: left;
  cursor: pointer;
  transition: all 0.16s ease;
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.sidebar-tab-btn .tab-icon {
  width: 20px;
  text-align: center;
  font-size: 15px;
  flex-shrink: 0;
}

.sidebar-tab-btn .tab-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-tab-btn:hover {
  color: #0f172a;
  background: #f8fafc;
}

.sidebar-tab-btn.active {
  color: #1d4ed8;
  background: #eff6ff;
  border-color: #bfdbfe;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.08);
}

.sidebar-tab-btn.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: #2563eb;
}

.admin-content-pane {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.pane-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
}

/* 统一标准主卡片与头部 */
.section-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 22px 24px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 6px 18px rgba(15, 23, 42, 0.03);
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f1f5f9;
}

.card-header-with-tag {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.card-header {
  font-size: 16.5px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  line-height: 1.4;
}

.header-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
}

.header-pill.is-primary {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.header-pill.is-success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.block-sub {
  font-size: 13px;
  color: #64748b;
  margin: 5px 0 0;
  line-height: 1.55;
}

.section-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  flex-shrink: 0;
}

.table-state-placeholder {
  padding: 44px 20px;
  text-align: center;
  color: #64748b;
  font-size: 13.5px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
}

.form-group-panel {
  padding: 16px 18px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 16px;
}

.form-group-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #cbd5e1;
}

/* ==================== 📋 业务操作记录样式 ==================== */
.submission-overview {
  display: grid;
  grid-template-columns: minmax(240px, 1fr) minmax(360px, 1.35fr);
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 14px 16px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.submission-overview__lead {
  display: flex;
  align-items: center;
  gap: 12px;
}

.submission-overview__icon {
  font-size: 28px;
  line-height: 1;
}

.submission-overview__copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.submission-overview__label {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.submission-overview__time {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.submission-overview__age {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 999px;
  line-height: 1.4;
}

.submission-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.submission-metric {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  text-align: center;
}

.submission-metric__label {
  font-size: 11.5px;
  color: #64748b;
  font-weight: 500;
}

.submission-metric__value {
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}

.submission-metric__value span {
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
}

.submission-metric--total .submission-metric__value {
  color: #2563eb;
}

.submission-metric--demand .submission-metric__value {
  color: #059669;
}

.submission-metric--supply .submission-metric__value {
  color: #7c3aed;
}

.submission-metric--query .submission-metric__value {
  color: #d97706;
}

.submission-filter-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 12px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  margin-bottom: 16px;
  align-items: flex-end;
}

.submission-filter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #475569;
  font-weight: 600;
  min-width: 0;
}

.submission-filter-item .select,
.submission-filter-item .input {
  width: 100%;
}

.submission-filter-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.submission-reset-btn,
.submission-query-btn {
  flex: 1;
}

.submission-table-wrap {
  overflow-x: auto;
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  background: #ffffff;
  margin-bottom: 14px;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.03);
}

.submission-log-table {
  width: 100%;
  min-width: 940px;
  margin: 0;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
  text-align: left;
}

.submission-col-time {
  width: 220px;
}

.submission-col-operator {
  width: 185px;
}

.submission-col-action {
  width: 165px;
}

.submission-col-detail {
  width: auto;
}

.submission-log-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 11px 14px;
  text-align: left;
  color: #475569;
  background: #f4f7fb;
  border-bottom: 1px solid #dbe4ef;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.submission-log-table tbody td {
  padding: 12px 14px;
  vertical-align: top;
  border-bottom: 1px solid #eef2f6;
  text-align: left;
}

.submission-log-table tbody tr {
  background: #ffffff;
  transition: background-color 0.16s ease;
}

.submission-log-table tbody tr:nth-child(even) {
  background: #fbfdff;
}

.submission-log-table tbody tr:hover {
  background: #f5f9ff;
}

.submission-log-table tbody tr:last-child td {
  border-bottom: none;
}

.submission-time-cell {
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.submission-time-value {
  color: #0f172a;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12.5px;
  font-weight: 700;
  white-space: nowrap;
}

.submission-time-meta {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 6px 8px;
  margin-top: 6px;
}

.submission-recent-badge {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
  color: #dc2626;
  background: #fff1f2;
  border: 1px solid #fecaca;
  border-radius: 5px;
}

.submission-ip {
  min-width: 0;
  font-size: 11px;
  color: #64748b;
  font-family: Consolas, Monaco, monospace;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.submission-operator-cell {
  line-height: 1.5;
  vertical-align: top;
}

.submission-operator-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.submission-operator-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.submission-group-chip {
  display: inline-flex;
  max-width: 100%;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 500;
  color: #526276;
  background: #f1f5f9;
  border-radius: 5px;
  border: 1px solid #e2e8f0;
  overflow-wrap: anywhere;
}

.submission-unit-chip {
  color: #0369a1;
  background: #f0f9ff;
  border-color: #bae6fd;
}

.submission-action-cell {
  line-height: 1.5;
  vertical-align: top;
  white-space: nowrap;
}

.submission-action-badge {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 4px 10px;
  font-size: 11.5px;
  font-weight: 600;
  border-radius: 7px;
  white-space: nowrap;
}

.submission-detail-cell {
  color: #334155;
  font-size: 13px;
  line-height: 1.6;
  vertical-align: top;
  overflow-wrap: anywhere;
}

.submission-detail-text {
  min-height: 40px;
  box-sizing: border-box;
  padding: 8px 12px;
  color: #1e293b;
  background: #f8fafc;
  border-left: 3px solid #93c5fd;
  border-radius: 0 8px 8px 0;
  overflow-wrap: anywhere;
}

.submission-section-chip {
  display: inline-flex;
  align-items: center;
  margin-right: 8px;
  padding: 1px 7px;
  font-size: 11px;
  font-weight: 600;
  color: #0369a1;
  background: #e0f2fe;
  border: 1px solid #bae6fd;
  border-radius: 4px;
  vertical-align: middle;
}

.submission-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 13px;
  color: #64748b;
}

.submission-pagination__controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ⛅ 气温模块子标签（分段控件） */
.weather-subtab-bar {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 6px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.weather-subtab-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border: 1px solid transparent;
  background: transparent;
  color: #475569;
  border-radius: 9px;
  padding: 10px 14px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;
  text-align: left;
}

.weather-subtab-btn:hover {
  color: #0f172a;
  background: rgba(255, 255, 255, 0.6);
}

.weather-subtab-btn.active {
  background: #ffffff;
  border-color: #bfdbfe;
  color: #1d4ed8;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
}

.subtab-main {
  min-width: 0;
}

.subtab-tag {
  flex-shrink: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
}

.weather-subtab-btn.active .subtab-tag {
  background: #dbeafe;
  color: #1d4ed8;
}

@media (max-width: 1100px) {
  .meta-dashboard {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1024px) {
  .admin-workbench-layout {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .mobile-tab-switcher {
    display: flex;
    flex-direction: column;
    gap: 8px;
    background: #ffffff;
    border: 1px solid #bfdbfe;
    border-radius: 12px;
    padding: 12px 14px;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.06);
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
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 9px;
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

  .admin-sidebar {
    position: static;
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 #f8fafc;
    padding: 8px;
    border-radius: 12px;
    gap: 8px;
  }

  .sidebar-group-title {
    display: none;
  }

  .sidebar-tab-btn {
    width: auto;
    min-width: max-content;
    flex: 0 0 auto;
    padding: 8px 14px;
    font-size: 13px;
    border-radius: 9px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
  }

  .sidebar-tab-btn.active {
    background: #2563eb;
    color: #ffffff;
    border-color: #2563eb;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.28);
  }

  .sidebar-tab-btn.active::before {
    display: none;
  }
}

@media (max-width: 900px) {
  .submission-overview {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .submission-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .weather-subtab-bar {
    grid-template-columns: 1fr;
  }
  .submission-filter-panel {
    grid-template-columns: 1fr;
  }
  .submission-filter-actions {
    flex-direction: row;
  }
  .submission-pagination {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
}

/* ==================== 🧮 算法字典与沙盒样式 ==================== */
.view-mode-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.view-mode-toggle .btn {
  height: 30px;
  border: 1px solid transparent;
  background: transparent;
  color: #475569;
  box-shadow: none;
  border-radius: 7px;
}

.view-mode-toggle .btn:hover {
  background: rgba(255, 255, 255, 0.65);
  color: #0f172a;
}

.view-mode-toggle .btn.active {
  background: #ffffff;
  color: #1d4ed8;
  border-color: #bfdbfe;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
}

.filter-toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.search-box {
  position: relative;
  flex: 1;
  min-width: 260px;
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
  padding-left: 36px;
  padding-right: 32px;
  height: 38px;
  border-radius: 9px;
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

.btn-clear:hover {
  color: #475569;
}

.filter-dropdowns {
  display: flex;
  gap: 10px;
}

.scope-select,
.derived-select {
  height: 38px;
  border-radius: 9px;
  font-size: 13px;
}

/* 分类胶囊 */
.category-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 14px;
  border-top: 1px dashed #e2e8f0;
}

.category-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 13px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.16s ease;
}

.category-pill:hover {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1e40af;
}

.category-pill.active {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.22);
}

.category-pill.active .pill-count {
  color: rgba(255, 255, 255, 0.88);
}

.pill-count {
  font-size: 11px;
  color: #64748b;
}

.catalog-result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
}

.catalog-result-summary {
  font-size: 12.5px;
  color: #64748b;
}

.catalog-result-summary strong {
  color: #1d4ed8;
}

/* 卡片网格 */
.catalog-cards-container {
  width: 100%;
}

.panel-state.empty-state {
  padding: 44px 20px;
  text-align: center;
  color: #64748b;
  font-size: 13.5px;
  background: #ffffff;
  border: 1px dashed #cbd5e1;
  border-radius: 14px;
}

.catalog-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.metric-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 11px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 6px 16px rgba(15, 23, 42, 0.025);
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.07);
  border-color: #bfdbfe;
}

.metric-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.metric-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.category-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
  align-self: flex-start;
}

.metric-name {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  line-height: 1.35;
}

.unit-badge {
  flex-shrink: 0;
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 9px;
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  border-radius: 7px;
}

.metric-key-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f8fafc;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.metric-key {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
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
  color: #059669;
  font-weight: 700;
}

.formula-box {
  background: #f8fbff;
  border: 1px solid #dbeafe;
  border-left: 3px solid #3b82f6;
  padding: 9px 12px;
  border-radius: 0 8px 8px 0;
}

.formula-label {
  font-size: 11.5px;
  color: #64748b;
  font-weight: 600;
  display: block;
  margin-bottom: 3px;
}

.formula-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12.5px;
  font-weight: 700;
  color: #1d4ed8;
  word-break: break-all;
}

.metric-desc {
  font-size: 12.5px;
  color: #475569;
  line-height: 1.55;
  margin: 0;
}

.metric-meta-details {
  border-top: 1px dashed #e2e8f0;
  padding-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
}

.meta-row {
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.row-label {
  color: #64748b;
  font-weight: 600;
  white-space: nowrap;
}

.row-val {
  color: #334155;
}

.highlight-rule {
  color: #b45309;
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
  border: 1px solid #e2e8f0;
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 5px;
}

.card-footer-action {
  margin-top: auto;
  padding-top: 8px;
}

.sandbox-trigger-btn {
  width: 100%;
  justify-content: center;
  color: #1d4ed8;
  border-color: #bfdbfe;
  background: #f8fbff;
}

.sandbox-trigger-btn:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

/* 表格视图 */
.catalog-table {
  width: 100%;
  border-collapse: collapse;
}

.catalog-table thead th {
  background: #f4f7fb;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  border-bottom: 1px solid #dbe4ef;
}

.table-key-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.clickable-key {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  cursor: pointer;
  color: #2563eb;
}

.category-badge-table {
  font-size: 11px;
  font-weight: 600;
  background: #f1f5f9;
  color: #475569;
  padding: 2px 7px;
  border-radius: 5px;
}

.cell-formula {
  max-width: 380px;
}

.formula-inline {
  color: #1d4ed8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12.5px;
}

.formula-desc-inline {
  display: block;
  color: #64748b;
  font-size: 11.5px;
  margin-top: 2px;
}

/* ================== 🧪 沙盒样式（统一规范） ================== */
.sandbox-control-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  gap: 14px;
  align-items: flex-end;
  margin-bottom: 18px;
  padding: 16px 18px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.sandbox-control-grid .field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: #334155;
}

.date-input-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.date-input-group .input {
  flex: 1;
}

.sandbox-action-wrap {
  display: flex;
  align-items: flex-end;
}

.execute-sandbox-btn {
  height: 38px;
  padding: 0 18px;
  font-size: 13.5px;
}

.sandbox-results-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: fadeIn 0.24s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.result-headline-card {
  background: linear-gradient(180deg, #eff6ff 0%, #f8fbff 100%);
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.indicator-badge {
  font-size: 11px;
  font-weight: 700;
  color: #065f46;
  background: #dcfce7;
  padding: 2px 9px;
  border-radius: 999px;
}

.headline-title {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
  margin: 6px 0 4px;
}

.headline-meta {
  font-size: 13px;
  color: #475569;
  margin: 0;
}

.final-unit-pill {
  flex-shrink: 0;
  font-size: 12.5px;
  font-weight: 700;
  padding: 5px 12px;
  background: #ffffff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  border-radius: 8px;
}

/* 8 窗口结果矩阵卡片 */
.matrix-8-windows {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.window-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 11px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.window-card.highlight-win {
  border-color: #93c5fd;
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
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
  color: #64748b;
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
  color: #059669;
}

/* 步骤时间轴 */
.derivation-steps-block {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 18px;
}

.steps-heading {
  font-size: 14.5px;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 14px;
}

.steps-timeline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.timeline-step-item {
  display: flex;
  gap: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px 14px;
}

.step-num-badge {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #2563eb;
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.step-content-box {
  flex: 1;
  min-width: 0;
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
  line-height: 1.55;
}

.step-breakdown-table-wrap {
  margin-top: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.step-subtable {
  width: 100%;
  font-size: 12px;
}

@media (max-width: 1120px) {
  .sandbox-control-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .matrix-8-windows {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* ==================== ⚙️ 供暖期与基准业务日期样式 ==================== */
.biz-date-form-row {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(240px, 0.9fr);
  gap: 18px;
  align-items: stretch;
}

.date-picker-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px 18px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
}

.date-picker-wrap {
  display: flex;
  gap: 8px;
  align-items: center;
}

.highlight-date-input {
  flex: 1;
  font-weight: 700;
  font-size: 14.5px;
  color: #0f766e;
  background: #ffffff;
  border-color: #86efac;
}

.date-status-card {
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.status-label {
  font-size: 12px;
  color: #475569;
  font-weight: 600;
}

.status-val {
  font-size: 20px;
  color: #047857;
  font-weight: 800;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.status-sub {
  font-size: 11.5px;
  color: #64748b;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.checkbox-align-box {
  height: 38px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 9px;
  padding: 0 12px;
}

.align-checkbox {
  cursor: pointer;
  width: 16px;
  height: 16px;
  accent-color: #2563eb;
}

.align-checkbox-label {
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  margin: 0;
  user-select: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.season-control-form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px 16px;
}

.season-control-form-grid .field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.season-control-form-grid .full-width {
  grid-column: 1 / -1;
}

.field-title {
  font-weight: 600;
  color: #1e293b;
  font-size: 13px;
  display: block;
}

.field-help {
  font-size: 11.5px;
  color: #64748b;
  line-height: 1.45;
}

.season-select {
  font-weight: 600;
  color: #1d4ed8;
}

.readonly-input {
  background: #f1f5f9 !important;
  color: #64748b !important;
  cursor: not-allowed;
}

.season-safety-notice {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 16px 20px;
}

.safety-title {
  font-size: 13.5px;
  font-weight: 700;
  color: #166534;
  margin-bottom: 8px;
}

.safety-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12.5px;
  color: #15803d;
  line-height: 1.7;
}

.safety-list code {
  background: #dcfce7;
  color: #14532d;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}

@media (max-width: 1100px) {
  .season-control-form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* ==================== 📊 金山文档 (KDocs) 底表配置样式 ==================== */
.kdocs-form-panel {
  margin-bottom: 0;
}

.kdocs-form-layout {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.kdocs-form-layout .field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.kdocs-two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.kdocs-input-link {
  width: 100%;
}

.field-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-text-action {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 3px 9px;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.btn-text-action:hover {
  background: #dbeafe;
}

.kdocs-sid-input,
.kdocs-sid-textarea {
  width: 100%;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}

.kdocs-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #e2e8f0;
}

.left-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  border-radius: 999px;
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
  border-radius: 10px;
  padding: 14px 16px;
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 13px;
  line-height: 1.5;
}

.status-label {
  color: #64748b;
  width: 96px;
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
  margin-top: 14px;
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 100%);
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 16px 18px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  color: #166534;
}

.preview-metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
  gap: 10px;
}

.metric-mini-card {
  background: #ffffff;
  border-radius: 10px;
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
  font-size: 17px;
  font-weight: 800;
  color: #0f172a;
}

.m-val.highlight {
  color: #2563eb;
}

.m-val.warning {
  color: #d97706;
}

/* 带圆点序号的步骤说明列表 */
.kdocs-guide-steps {
  margin: 0;
  padding: 0;
  list-style: none;
  counter-reset: guide-step;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.kdocs-guide-steps li {
  counter-increment: guide-step;
  position: relative;
  padding: 10px 14px 10px 44px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.65;
  color: #334155;
}

.kdocs-guide-steps li::before {
  content: counter(guide-step);
  position: absolute;
  left: 12px;
  top: 10px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #2563eb;
  color: #ffffff;
  font-size: 11.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kdocs-guide-steps code {
  background: #eff6ff;
  color: #1d4ed8;
  padding: 1px 6px;
  border-radius: 5px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.link {
  color: #2563eb;
  text-decoration: underline;
}

/* ==================== 📱 移动端与手机窄屏适配 ==================== */
.mobile-table-hint {
  display: none;
  font-size: 11.5px;
  color: #0369a1;
  background: #f0f9ff;
  border: 1px dashed #bae6fd;
  border-radius: 8px;
  padding: 6px 10px;
  margin-bottom: 10px;
  text-align: center;
}

@media (max-width: 768px) {
  .mobile-table-hint {
    display: block;
  }

  .dr-global-mgmt-view {
    overflow-x: hidden;
    width: 100%;
  }

  .tube-page-main {
    padding: 10px 12px 48px;
  }

  .premium-topbar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    margin: 6px 0 14px;
    padding-bottom: 12px;
  }

  .premium-topbar h2 {
    font-size: 18px;
    line-height: 1.35;
  }

  .premium-topbar .sub {
    font-size: 12px;
  }

  .topbar-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    width: 100%;
  }

  .topbar-actions .btn {
    width: 100%;
    padding: 0 8px;
    font-size: 13px;
  }

  .quick-dashboard-card {
    padding: 10px;
    margin-bottom: 14px;
    border-radius: 12px;
  }

  .meta-dashboard {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .meta-dashboard .meta-card {
    padding: 8px 10px;
  }

  .meta-dashboard .meta-card:nth-child(3) {
    grid-column: 1 / -1;
  }

  .meta-label {
    font-size: 11px;
  }

  .meta-value {
    font-size: 14.5px;
  }

  .section-card {
    padding: 16px 14px;
    border-radius: 12px;
  }

  .card-header-row {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    margin-bottom: 14px;
    padding-bottom: 12px;
  }

  .card-header {
    font-size: 15.5px;
  }

  .block-sub {
    font-size: 12px;
  }

  .section-actions,
  .section-actions .execute-sandbox-btn {
    width: 100%;
  }

  .view-mode-toggle {
    display: grid;
    grid-template-columns: 1fr 1fr;
    width: 100%;
  }

  .view-mode-toggle .btn {
    width: 100%;
  }

  .filter-toolbar {
    flex-direction: column;
    gap: 10px;
  }

  .search-box {
    width: 100%;
    min-width: 0;
  }

  .filter-dropdowns {
    flex-direction: column;
    width: 100%;
    gap: 8px;
  }

  .scope-select,
  .derived-select {
    width: 100%;
  }

  .category-pills {
    flex-wrap: nowrap;
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding-top: 10px;
    padding-bottom: 4px;
  }

  .category-pills::-webkit-scrollbar {
    display: none;
  }

  .category-pill {
    flex-shrink: 0;
    white-space: nowrap;
    padding: 5px 11px;
    font-size: 12px;
  }

  .catalog-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .metric-card {
    padding: 14px;
    border-radius: 12px;
  }

  .metric-key {
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
    flex: 1;
  }

  .table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
  }

  .catalog-table {
    min-width: 680px;
  }

  .sandbox-control-grid {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 12px;
  }

  .date-input-group input[type='date'] {
    flex: 1;
    min-width: 0;
  }

  .sandbox-action-wrap {
    width: 100%;
  }

  .execute-sandbox-btn {
    width: 100%;
    height: 40px;
  }

  .result-headline-card {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    padding: 12px;
  }

  .final-unit-pill {
    align-self: flex-start;
  }

  .matrix-8-windows {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .window-card {
    padding: 10px;
  }

  .win-val {
    font-size: 17px;
  }

  .derivation-steps-block {
    padding: 12px;
  }

  .step-breakdown-table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .step-subtable {
    min-width: 320px;
  }

  .form-group-panel {
    padding: 12px;
  }

  .biz-date-form-row,
  .season-control-form-grid,
  .kdocs-two-col {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .date-picker-field {
    padding: 12px;
  }

  .date-picker-wrap {
    flex-wrap: wrap;
  }

  .kdocs-action-bar {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .status-summary,
  .status-badge,
  .left-actions,
  .left-actions .btn {
    width: 100%;
  }

  .left-actions {
    flex-direction: column;
  }

  .status-row {
    flex-direction: column;
    gap: 2px;
  }

  .status-label {
    width: auto;
  }

  .preview-metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }
}

@media (max-width: 420px) {
  .tube-page-main {
    padding: 8px 8px 40px;
  }

  .premium-topbar h2 {
    font-size: 16.5px;
  }

  .topbar-actions .btn {
    font-size: 12px;
    padding: 0 4px;
  }

  .win-val {
    font-size: 15px;
  }
}
</style>
