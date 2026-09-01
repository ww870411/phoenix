<template>
  <div class="tube-page-root">
    <AppHeader />
    <main class="tube-page-main container">
      <Breadcrumbs :items="breadcrumbItems" />
      
      <!-- 高级控制台头部 -->
      <header class="topbar premium-topbar">
        <div>
          <h2>系统全局控制台 (管理员)</h2>
          <p class="sub">仅供 Global_admin 全局管理员使用。按区块纵向管理，独立校验并保存，降低一次性误改全局配置的安全风险。</p>
        </div>
        <div class="topbar-actions">
          <button class="btn ghost btn-back" type="button" @click="goProjectPages">返回功能页</button>
          <button class="btn ghost" type="button" :disabled="loading" @click="loadConfig">
            {{ loading ? '同步配置中…' : '🔄 刷新同步全局配置' }}
          </button>
        </div>
      </header>

      <p v-if="errorMessage" class="page-error">{{ errorMessage }}</p>
      <p v-if="globalMessage" :class="['page-tip', globalMessage.type]">{{ globalMessage.text }}</p>

      <!-- 磨砂玻璃态全局数据看板 (Quick Dashboard) -->
      <section class="card elevated quick-dashboard-card">
        <div class="meta-dashboard">
          <div class="meta-card">
            <span class="meta-label">供给主体数 (正常+自定义)</span>
            <strong class="meta-value">{{ normalSupplyEntitiesCount }}+{{ customSupplyEntitiesCount }} 个注册主体</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">管理的需求主体</span>
            <strong class="meta-value">{{ demandEntities.length }} 个运营需求主体</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">系统保温管型号</span>
            <strong class="meta-value">{{ pipeModels.length }} 种规格</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">当前计划起始日期</span>
            <strong class="meta-value">{{ planStartDate || '未设置' }}</strong>
          </div>
          <div class="meta-card highlight">
            <span class="meta-label">需求主体提交状态</span>
            <strong class="meta-value highlight-num">{{ submittedSection1Count }} / {{ demandEntities.length }} 已提交</strong>
          </div>
        </div>
      </section>

      <!-- 纵向双栏侧边控制台 -->
      <div class="admin-workbench-layout">
        
        <!-- 左侧纵向选项卡菜单 -->
        <aside class="admin-sidebar">
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'submissions' }]"
            @click="activeTab = 'submissions'; fetchSubmissionLogs(1)"
          >
            📋 业务操作记录
          </button>
          <button
            type="button"
            :class="['sidebar-tab-btn', { active: activeTab === 'core' }]" 
            @click="activeTab = 'core'"
          >
            ⚙️ 核心参数与状态
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'section1' }]" 
            @click="activeTab = 'section1'"
          >
            📍 需求主体基础台账
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'supply' }]" 
            @click="activeTab = 'supply'"
          >
            🚚 供给主体与产能
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'people' }]" 
            @click="activeTab = 'people'"
          >
            👥 人员映射与施工
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'baseline' }]" 
            @click="activeTab = 'baseline'"
          >
            📋 基准设计量预设
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'weather' }]" 
            @click="activeTab = 'weather'"
          >
            ⛅ 气温数据管理
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'gis' }]" 
            @click="activeTab = 'gis'"
          >
            🗺️ GIS 地图 API 配置
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'gemini_config' }]" 
            @click="activeTab = 'gemini_config'"
          >
            ⚡ 单据识别模型与 API 配置
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'json' }]" 
            @click="activeTab = 'json'"
          >
            💻 原始 JSON 预览
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'audit' }]" 
            @click="activeTab = 'audit'; fetchAuditLogs(1)"
          >
            📜 操作审计日志
          </button>
        </aside>

        <!-- 右侧当前选中的配置主卡片 -->
        <div class="admin-content-pane">
          
          <!-- Tab 0: 业务操作记录 (放在第一个位置) -->
          <div v-if="activeTab === 'submissions'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">📋 业务操作记录</div>
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
                    <div class="submission-metric__label">需求侧提交</div>
                    <div class="submission-metric__value">{{ demand24hCount }} <span>笔</span></div>
                  </div>
                  <div class="submission-metric submission-metric--supply">
                    <div class="submission-metric__label">供给侧发货</div>
                    <div class="submission-metric__value">{{ supply24hCount }} <span>笔</span></div>
                  </div>
                  <div class="submission-metric submission-metric--query">
                    <div class="submission-metric__label">综合查询行为</div>
                    <div class="submission-metric__value">{{ query24hCount }} <span>笔</span></div>
                  </div>
                </div>
              </div>

              <!-- 结构化过滤控制面板：提供“提交”和“查询”两大分类联动 -->
              <div class="submission-filter-panel">
                <label class="submission-filter-item">
                  <span>操作行为大类</span>
                  <select v-model="submissionFilters.category" class="select" @change="onSubmissionCategoryChange">
                    <option value="">全部大类 (提交与查询)</option>
                    <option value="submission">📥 业务数据提交类</option>
                    <option value="query">🔍 综合数据查询类</option>
                  </select>
                </label>

                <label class="submission-filter-item">
                  <span>主体与渠道分类</span>
                  <select v-model="submissionFilters.entityType" class="select" @change="fetchSubmissionLogs(1)">
                    <option value="">全部主体与渠道</option>
                    <template v-if="submissionFilters.category !== 'query'">
                      <option value="demand">📍 需求主体 (施工队)</option>
                      <option value="supply">🚚 供给主体 (厂家)</option>
                      <option value="warehouse">🏢 库管主体</option>
                    </template>
                    <template v-if="submissionFilters.category !== 'submission'">
                      <option value="query">🔍 综合数据查询中心</option>
                    </template>
                  </select>
                </label>

                <label class="submission-filter-item">
                  <span>具体操作行为</span>
                  <select v-model="submissionFilters.actionType" class="select">
                    <option value="">全部具体行为</option>
                    <optgroup v-if="submissionFilters.category !== 'query'" label="📥 业务数据提交行为">
                      <option value="SAVE_PLAN">📅 保存三日计划</option>
                      <option value="SUBMIT_USAGE">🔋 上报施工消耗</option>
                      <option value="SUBMIT_STATUS">✅ 提交填报完成</option>
                      <option value="CONFIRM_ARRIVAL">👷 到货签收</option>
                      <option value="CONFIRM_CONSTRUCTION">👷 施工接收</option>
                      <option value="CREATE_DELIVERY">🚚 厂家发货</option>
                      <option value="CREATE_DELIVERY_BATCH">🚚 批量发货</option>
                      <option value="CANCEL_DELIVERY">❌ 撤销发货</option>
                      <option value="CONFIRM_WAREHOUSE">🏢 库管确认</option>
                      <option value="SUBMIT_FITTING_DELIVERY">🔩 管件发货</option>
                      <option value="DELETE_FITTING_DELIVERY">🗑️ 撤销管件发货</option>
                    </optgroup>
                    <optgroup v-if="submissionFilters.category !== 'submission'" label="🔍 综合数据查询行为">
                      <option value="QUERY_DAILY_FLOW">📅 查询每日流转台账</option>
                      <option value="QUERY_BASELINE_PROGRESS">📐 查询设计采购进度</option>
                      <option value="QUERY_MATERIAL_PRICES">💰 调阅采购单价字典</option>
                      <option value="QUERY_SUPPLIER_LEDGER">🏭 查询供给方发货台账</option>
                      <option value="QUERY_ENTITY_DIRECTORY">🏢 查询责任主体矩阵</option>
                      <option value="OCR_DELIVERY_BILL">📷 业务单据智能识别</option>
                    </optgroup>
                  </select>
                </label>

                <label class="submission-filter-item">
                  <span>操作账号/操作人</span>
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
              <div v-if="submissionLoading" class="loading-placeholder" style="padding: 40px; text-align: center; color: #64748b;">业务操作记录加载中...</div>
              <div v-else-if="submissionLogs.length === 0" class="empty-placeholder" style="padding: 40px; text-align: center; color: #777;">未查询到任何业务操作记录。</div>
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
                            <button 
                              v-if="log.client_ip" 
                              class="submission-ip clickable-ip" 
                              type="button"
                              title="点击查看 IP 归属地与网络运营商"
                              @click.stop="triggerIpPopover($event, log.client_ip)"
                            >
                              📍 IP: {{ log.client_ip }}
                            </button>
                          </div>
                        </td>
                        <td class="submission-operator-cell">
                          <div 
                            class="submission-operator-name clickable-user-link" 
                            title="点击在责任主体矩阵中定位该人员/主体"
                            @click="handleGoToUserDirectory(log.operator)"
                          >
                            <span class="user-name-text">{{ log.operator }}</span>
                            <span class="link-hint-icon">↗</span>
                          </div>
                          <div v-if="log.operator_group" class="submission-operator-meta">
                            <span class="submission-group-chip">
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
                            <span v-if="getSection1NameFromLog(log)" class="submission-section-chip" :title="`关联需求主体: ${getSection1NameFromLog(log)}`">
                              📍 {{ getSection1NameFromLog(log) }}
                            </span>
                            <span>{{ getCleanActionDesc(log) }}</span>
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

          <!-- Tab 1: 核心参数与提交状态 -->
          <div v-if="activeTab === 'core'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div class="card-header">⚙️ 核心控制参数</div>
                <div class="section-actions">
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('core_dates')" @click="saveCoreDatesSection">
                    {{ isSaving('core_dates') ? '保存中…' : '💾 保存核心参数' }}
                  </button>
                </div>
              </div>
              <div class="field-grid core-field-grid">
                <label class="field">
                  <span>展示/业务日期 (show_date)</span>
                  <input v-model="showDate" type="date" class="input" :disabled="isAllDatesAutoUpdateEnabled" />
                  <small class="field-help">决定大盘看板及历史消耗数据统计的宏观切断视界。</small>
                </label>
                <label class="field">
                  <span>消耗采集日期 (usage_collection_date)</span>
                  <input v-model="usageCollectionDate" type="date" class="input" :disabled="isPlanDateAutoUpdateEnabled" />
                  <small class="field-help">需求侧施工队上报实际施工消耗与现场损耗的基准日期。</small>
                </label>
                <label class="field">
                  <span>滚动计划起始日期 (plan_start_date)</span>
                  <input v-model="planStartDate" type="date" class="input" :disabled="isPlanDateAutoUpdateEnabled" />
                  <small class="field-help">未来三日计划采集的物理起始日期锚点（滚动计划 T 日）。</small>
                </label>
                <label class="field">
                  <span>起始日期是否自动随今天变化</span>
                  <select v-model="autoUpdatePlanStartDate" class="input" @change="handleAutoPlanStartDateChange">
                    <option :value="false">否 (手动维护起始日期)</option>
                    <option :value="true">是 (计划与消耗日期自动后移)</option>
                    <option value="all">全部是 (三个日期均自动后移)</option>
                  </select>
                  <small class="field-help">北京时间每日 06:30 换日；“全部是”还会把展示/业务日期自动设为业务当天的昨日。</small>
                </label>
                <label class="field">
                  <span>计划可填报修改天数 (plan_editable_days)</span>
                  <input v-model.number="planEditableDays" class="input" type="number" min="0" max="3" step="1" />
                  <small class="field-help">3 为三天都可填，2 为后两天可填，0 为计划全部锁盘不可填。</small>
                </label>
                <label class="field">
                  <span>超时自动施工接收小时数 (auto_receive_timeout_hours)</span>
                  <input v-model.number="autoReceiveTimeoutHours" class="input" type="number" step="0.5" placeholder="默认 12, 设定 -1 为关闭" />
                  <small class="field-help">到货后超出该时长未施工接收由系统强制接收（直管与管件通用）；设为 -1 则关闭自动功能。</small>
                </label>
                <label class="field field-span-2">
                  <span>严格计划填报流程管控 (strict_planning_flow_control)</span>
                  <select v-model="strictPlanningFlowControl" class="input">
                    <option :value="true">开启 (现场必须先结清前日消耗，才解锁第三日计划)</option>
                    <option :value="false">关闭 (现场可直接独立填报第三日计划，不强加顺序)</option>
                  </select>
                  <small class="field-help">开启后强力规范现场工作流顺序并激活滚动盈缺预测，关闭则保障紧急状态下的独立填报弹性。</small>
                </label>
              </div>
              <p v-if="sectionMessage('core_dates')" :class="['section-tip', sectionMessage('core_dates').type]">
                {{ sectionMessage('core_dates').text }}
              </p>
            </section>

            <section class="card elevated section-card">
              <div class="card-header-row">
                <div class="card-header">🔩 管件基础参数与强校验配置</div>
                <div class="section-actions">
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('fitting_config')" @click="saveSection('fitting_config')">
                    {{ isSaving('fitting_config') ? '保存中…' : '💾 保存管件配置' }}
                  </button>
                </div>
              </div>
              <div class="field-grid core-field-grid">
                <label class="field">
                  <span>合规管件单位列表 (allowed_units)</span>
                  <input v-model="fittingAllowedUnitsText" type="text" class="input" placeholder="例如: 个, 套" />
                  <small class="field-help">填报或导入管件时强校验允许的文字单位（多个单位用逗号分隔）。</small>
                </label>
                <label class="field field-span-2">
                  <span>常用标准管件类型 (standard_types)</span>
                  <input v-model="fittingStandardTypesText" type="text" class="input" placeholder="例如: 弯头, 三通, 大小头, 封头, 直缝弯管, 补偿器, 固定节" />
                  <small class="field-help">管件填报时识别常用规范类型的白名单（多个类型用逗号分隔）。</small>
                </label>
              </div>
              <p v-if="sectionMessage('fitting_config')" :class="['section-tip', sectionMessage('fitting_config').type]">
                {{ sectionMessage('fitting_config').text }}
              </p>
            </section>

            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">需求主体昨日提交状态审计</div>
                  <p class="sub block-sub">审计昨日三日计划上报进度，判断昨日消耗数据及滚动计划是否全部锁盘入库。</p>
                </div>
              </div>
              <div class="table-wrap">
                <table class="table editor-table submission-table">
                  <thead>
                    <tr>
                      <th>需求主体</th>
                      <th>提交状态</th>
                      <th>最近一次提交日期</th>
                      <th>提交完成物理时间</th>
                      <th>现场填报人</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in submissionStatusRows" :key="item.section_1_id">
                      <td class="cell-text" :title="item.section_1_name || item.section_1_id">{{ item.section_1_name || item.section_1_id }}</td>
                      <td>
                        <span :class="['status-chip', item.is_submitted ? 'success' : 'pending']">
                          {{ item.is_submitted ? '✓ 已上报' : '⌛ 未上报' }}
                        </span>
                      </td>
                      <td>{{ item.data_submit_date || '—' }}</td>
                      <td class="cell-datetime">{{ item.submitted_at || '—' }}</td>
                      <td>{{ item.submitted_by || '—' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <!-- Tab 2: 换热站/标段基础台账 -->
          <div v-if="activeTab === 'section1'" class="pane-content-wrapper">


            <!-- 基础档案信息表格 -->
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">需求主体基础档案信息</div>
                  <p class="sub block-sub">管理保温管物理覆盖的所有需求主体及所属第二维度 (如所属区域) 映射。</p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost" type="button" @click="addDemandEntity">➕ 新增需求主体</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('demand_entities')" @click="saveSection('demand_entities')">
                    {{ isSaving('demand_entities') ? '正在同步…' : '💾 保存需求主体台账' }}
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
                      <th>需求主体ID (唯一)</th>
                      <th>需求主体编码</th>
                      <th>需求主体名称</th>
                      <th>第二维度 (如所属区域)</th>
                      <th>第三维度 (如所属标段)</th>
                      <th>当前施工状态</th>
                      <th>物理移除</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in demandEntities" :key="index">
                      <td><input v-model.trim="item.section_1_id" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.code" class="input table-cell-input" type="text" maxlength="8" placeholder="如 AA" /></td>
                      <td><input v-model.trim="item.section_1_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.section_2" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.section_3" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.construction_status" class="input table-cell-input" type="text" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(demandEntities, index)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <!-- Tab 3: 供给主体与产能 -->
          <div v-if="activeTab === 'supply'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">供货商与供给主体档案</div>
                  <p class="sub block-sub">配置参与本次管材物流链的所有保温管制造厂主体及发货人默认信息。</p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost" type="button" @click="addSupplyEntity">➕ 新增主体</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('supply_entities')" @click="saveSection('supply_entities')">
                    {{ isSaving('supply_entities') ? '保存中…' : '💾 保存主体信息' }}
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
                      <th>主体ID (唯一)</th>
                      <th>主体编码</th>
                      <th>供给主体名称</th>
                      <th>对应的需求主体 (供货标段)</th>
                      <th>发货联系人</th>
                      <th>联系电话</th>
                      <th>物理移除</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in supplyEntities" :key="index">
                      <td><input v-model.trim="item.entity_id" class="input table-cell-input" type="text" placeholder="如 supplier_a" /></td>
                      <td><input v-model.trim="item.code" class="input table-cell-input" type="text" maxlength="8" placeholder="如 SA" /></td>
                      <td><input v-model.trim="item.entity_name" class="input table-cell-input" type="text" placeholder="供给主体名称" /></td>
                      <td>
                        <input 
                          v-model.trim="item.section_1_ids_text" 
                          class="input table-cell-input text-indigo font-bold" 
                          type="text" 
                          placeholder="输入需求主体ID/标段名称（逗号分隔）" 
                          :title="`对应需求主体: ${item.section_1_ids_text || '暂未指定'}`"
                        />
                      </td>
                      <td><input v-model.trim="item.contact_name" class="input table-cell-input" type="text" placeholder="联系人" /></td>
                      <td><input v-model.trim="item.contact_phone" class="input table-cell-input" type="text" placeholder="联系电话" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(supplyEntities, index)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <!-- 专属卡片：现场补录/自定义供给主体档案 -->
            <section class="card elevated section-card" style="border: 1px dashed #818cf8; background: #faf5ff;">
              <div class="card-header-row">
                <div>
                  <div class="card-header" style="color: #6b21a8; display: flex; align-items: center; gap: 8px;">
                    🏷️ 现场补录 / 自定义供给主体档案
                    <span class="badge" style="font-size: 12px; font-weight: normal; padding: 2px 10px; border-radius: 12px; background: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe;">
                      共 {{ customSupplyEntitiesList.length }} 个补录主体
                    </span>
                  </div>
                  <p class="sub block-sub">配置在现场发货工作台中由管理员手填补录的临时/自定义供给主体，可在此补充联系人信息或物理清退。</p>
                </div>
                <div class="section-actions">
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('supply_entities')" @click="saveSection('supply_entities')">
                    {{ isSaving('supply_entities') ? '保存中…' : '💾 保存自定义主体设置' }}
                  </button>
                </div>
              </div>

              <div v-if="customSupplyEntitiesList.length === 0" class="empty-placeholder" style="padding: 24px; text-align: center; color: #9333ea; font-size: 13.5px; background: #ffffff; border-radius: 8px; border: 1px dashed #e9d5ff;">
                🌱 当前暂无手动录入的自定义供给主体。在现场管理工作台中选择“手动输入自定义供给方”后将自动保存并同步至此。
              </div>

              <div v-else class="table-wrap">
                <table class="table editor-table">
                  <thead>
                    <tr style="background: #f3e8ff;">
                      <th>主体ID (唯一)</th>
                      <th>主体编码</th>
                      <th>自定义供给主体名称</th>
                      <th>供货需求主体 (标段)</th>
                      <th>发货联系人</th>
                      <th>联系电话</th>
                      <th>物理清退</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in customSupplyEntitiesList" :key="item.entity_id">
                      <td><span style="font-weight: bold; color: #7e22ce;">{{ item.entity_id }}</span></td>
                      <td><input v-model.trim="item.code" class="input table-cell-input" type="text" maxlength="12" placeholder="如 CUST_01" /></td>
                      <td><input v-model.trim="item.entity_name" class="input table-cell-input font-bold" type="text" placeholder="主体名称" /></td>
                      <td>
                        <input 
                          v-model.trim="item.section_1_ids_text" 
                          class="input table-cell-input text-indigo font-bold" 
                          type="text" 
                          placeholder="需求主体ID/标段名称（逗号分隔）" 
                          :title="`对应需求主体: ${item.section_1_ids_text || '暂未指定'}`"
                        />
                      </td>
                      <td><input v-model.trim="item.contact_name" class="input table-cell-input" type="text" placeholder="联系人" /></td>
                      <td><input v-model.trim="item.contact_phone" class="input table-cell-input" type="text" placeholder="联系电话" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeCustomEntity(item)">清退</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">系统保温管型号规格</div>
                  <p class="sub block-sub">定义系统中支持登记的保温管径规格，通常符合 DN 命名规范。</p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost" type="button" @click="addPipeModel">➕ 新增型号</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('pipe_models')" @click="saveSection('pipe_models')">
                    {{ isSaving('pipe_models') ? '保存中…' : '💾 保存管径规格' }}
                  </button>
                </div>
              </div>
              <p v-if="sectionMessage('pipe_models')" :class="['section-tip', sectionMessage('pipe_models').type]">
                {{ sectionMessage('pipe_models').text }}
              </p>
              <div class="table-wrap">
                <table class="table editor-table">
                  <thead>
                    <tr>
                      <th>型号规格ID (如 DN200)</th>
                      <th>展示名称</th>
                      <th>物理计量单位</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in pipeModels" :key="index">
                      <td><input v-model.trim="item.pipe_model_id" class="input table-cell-input" type="text" @change="syncPipeModelIdentity(item, 'id')" /></td>
                      <td><input v-model.trim="item.pipe_model_name" class="input table-cell-input" type="text" @change="syncPipeModelIdentity(item, 'name')" /></td>
                      <td><input v-model.trim="item.unit" class="input table-cell-input" type="text" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(pipeModels, index)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">供给侧制造产能预设</div>
                  <p class="sub block-sub">维护每个供给厂、各型号保温管的每日最大制造上限（米/日）。</p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost" type="button" @click="addProductionCapacity">➕ 新增产能</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('production_capacities')" @click="saveSection('production_capacities')">
                    {{ isSaving('production_capacities') ? '保存中…' : '💾 保存产能数据' }}
                  </button>
                </div>
              </div>
              <p v-if="sectionMessage('production_capacities')" :class="['section-tip', sectionMessage('production_capacities').type]">
                {{ sectionMessage('production_capacities').text }}
              </p>
              <div class="table-wrap">
                <table class="table editor-table">
                  <thead>
                    <tr>
                      <th>供给主体</th>
                      <th>保温管型号</th>
                      <th>每日制造上限 (米)</th>
                      <th>特殊限制说明</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in productionCapacities" :key="index">
                      <td><input v-model.trim="item.supply_entity_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.pipe_model_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.number="item.max_daily_output_qty" class="input table-cell-input" type="number" min="0" step="1" /></td>
                      <td><input v-model.trim="item.remark" class="input table-cell-input" type="text" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(productionCapacities, index)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <!-- Tab 4: 人员映射与施工单位 -->
          <div v-if="activeTab === 'people'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">现场主管负责人映射</div>
                  <p class="sub block-sub">授权不同负责人账号所分管的需求主体列表。多个需求主体请用英文逗号(,)分隔。</p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost" type="button" @click="addManagerAssignment">➕ 新增主管</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('manager_assignments')" @click="saveSection('manager_assignments')">
                    {{ isSaving('manager_assignments') ? '保存中…' : '💾 保存主管映射' }}
                  </button>
                </div>
              </div>
              <p v-if="sectionMessage('manager_assignments')" :class="['section-tip', sectionMessage('manager_assignments').type]">
                {{ sectionMessage('manager_assignments').text }}
              </p>
              <div class="table-wrap">
                <table class="table editor-table">
                  <thead>
                    <tr>
                      <th>分管人账号ID (对应登录名)</th>
                      <th>分管负责人姓名</th>
                      <th>联系电话</th>
                      <th>所分管的需求主体ID列表 (逗号分隔)</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in managerAssignments" :key="index">
                      <td><input v-model.trim="item.manager_id" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.manager_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.contact_phone" class="input table-cell-input" type="text" placeholder="输入联系电话" /></td>
                      <td><input v-model.trim="item.section_1_ids_text" class="input table-cell-input" type="text" placeholder="如主体A, 主体B（逗号分隔）" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(managerAssignments, index)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">施工分包单位及需求主体映射</div>
                  <p class="sub block-sub">配置各分包商基本联络方式及分管需求主体。多个需求主体请用英文逗号(,)分隔。</p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost" type="button" @click="addConstructionUnit">➕ 新增分包商</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('construction_units')" @click="saveSection('construction_units')">
                    {{ isSaving('construction_units') ? '保存中…' : '💾 保存施工映射' }}
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
                      <th>分包单位ID (唯一)</th>
                      <th>施工单位名称</th>
                      <th>工地联系人</th>
                      <th>联系电话</th>
                      <th>分管的需求主体ID列表 (逗号分隔)</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in constructionUnits" :key="index">
                      <td><input v-model.trim="item.unit_id" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.unit_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.contact_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.contact_phone" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.section_1_ids_text" class="input table-cell-input" type="text" placeholder="如主体A, 主体C（逗号分隔）" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(constructionUnits, index)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">库管人员映射</div>
                  <p class="sub block-sub">配置库房管理员的真实姓名和联系电话等基本信息。</p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost" type="button" @click="addWarehouseKeeper">➕ 新增库管</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('warehouse_keepers')" @click="saveSection('warehouse_keepers')">
                    {{ isSaving('warehouse_keepers') ? '保存中…' : '💾 保存库管映射' }}
                  </button>
                </div>
              </div>
              <p v-if="sectionMessage('warehouse_keepers')" :class="['section-tip', sectionMessage('warehouse_keepers').type]">
                {{ sectionMessage('warehouse_keepers').text }}
              </p>
              <div class="table-wrap">
                <table class="table editor-table">
                  <thead>
                    <tr>
                      <th>库管账号ID (对应登录名)</th>
                      <th>库管员姓名</th>
                      <th>联系电话</th>
                      <th>分管的需求主体ID列表 (逗号分隔)</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in warehouseKeepers" :key="index">
                      <td><input v-model.trim="item.keeper_id" class="input table-cell-input" type="text" placeholder="如 warehouse_keeper_a" /></td>
                      <td><input v-model.trim="item.keeper_name" class="input table-cell-input" type="text" placeholder="输入姓名" /></td>
                      <td><input v-model.trim="item.contact_phone" class="input table-cell-input" type="text" placeholder="输入联系电话" /></td>
                      <td><input v-model.trim="item.section_1_ids_text" class="input table-cell-input" type="text" placeholder="如 high_lot_1, low_lot_1（逗号分隔）" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(warehouseKeepers, index)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>

          <!-- Tab 5: 基准量预设 -->
          <div v-if="activeTab === 'baseline'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row baseline-header-row">
                <div class="card-header baseline-title-heading">📐 需求主体管线基准设计量</div>
                <div class="section-actions baseline-actions-panel">
                  <div class="section1-filter-inline">
                    <span class="filter-label">过滤需求主体：</span>
                    <select v-model="selectedBaselineSection1Id" class="input inline-select">
                      <option v-for="section1 in demandEntities" :key="section1.section_1_id" :value="section1.section_1_id">
                        {{ section1.section_1_name || section1.section_1_id }}
                      </option>
                    </select>
                  </div>
                  <button class="btn ghost" type="button" @click="addBaselinePreset">➕ 新增型号行</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('baseline_presets')" @click="saveSection('baseline_presets')">
                    {{ isSaving('baseline_presets') ? '保存中…' : '💾 保存设计基准' }}
                  </button>
                </div>
              </div>

              <p v-if="sectionMessage('baseline_presets')" :class="['section-tip', sectionMessage('baseline_presets').type]">
                {{ sectionMessage('baseline_presets').text }}
              </p>

              <div class="summary-row baseline-summary">
                <span class="summary-chip">📍 当前站点：<strong>{{ selectedBaselineSection1Name }}</strong></span>
                <span class="summary-chip">📊 当前显示：<strong>{{ filteredBaselinePresets.length }}</strong> 条</span>
                <span class="summary-chip">🗂️ 全量预设：<strong>{{ baselinePresets.length }}</strong> 条</span>
              </div>

              <div class="table-wrap">
                <table class="table editor-table baseline-table">
                  <colgroup>
                    <col class="col-spec-width" style="width: 200px;" />
                    <col class="col-num-width" style="width: 120px;" />
                    <col class="col-num-width" style="width: 135px;" />
                    <col class="col-remark-width" />
                    <col class="col-act-width" style="width: 85px;" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th class="col-model-spec">管材型号</th>
                      <th class="col-num-design">设计量 (米)</th>
                      <th class="col-num-plan">计划采购总量 (米)</th>
                      <th class="col-text-remark">说明备注</th>
                      <th class="col-action-btn">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in filteredBaselinePresets" :key="item.__row_key">
                      <td class="col-model-spec">
                        <select v-model="item.pipe_model_id" class="input table-cell-input" @change="syncBaselinePipeModelName(item)">
                          <option 
                            v-for="model in selectableBaselinePipeModels" 
                            :key="model.pipe_model_id" 
                            :value="model.pipe_model_id"
                            :disabled="filteredBaselinePresets.some(preset => preset.pipe_model_id === model.pipe_model_id && preset !== item)"
                          >
                            {{ model.pipe_model_name || model.pipe_model_id }}
                          </option>
                        </select>
                      </td>
                      <td class="col-num-design">
                        <input v-model.number="item.design_qty" class="input table-cell-input text-right" type="number" min="0" step="1" placeholder="0" />
                      </td>
                      <td class="col-num-plan">
                        <input v-model.number="item.purchase_plan_qty" class="input table-cell-input text-right" type="number" min="0" step="1" placeholder="0" />
                      </td>
                      <td class="col-text-remark">
                        <input v-model.trim="item.remark" class="input table-cell-input" type="text" placeholder="选填备注说明" />
                      </td>
                      <td class="col-action-btn">
                        <button class="btn danger-ghost compact-btn" type="button" @click="removeBaselinePreset(item.__row_key)">删除</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <!-- 卡片 2: 需求主体管件基准设计量与计划采购量 (RevoGrid 自由高性能表格) -->
            <section class="card elevated section-card" style="margin-top: 24px;">
              <div class="card-header-row baseline-header-row">
                <div>
                  <div class="card-header baseline-title-heading">🔩 需求主体管件基准设计量与计划采购量</div>
                  <p class="sub" style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">
                    支持自由录入任意管件类别与规格，支持从 Excel 直接批量复制粘贴或文件一键导入。
                  </p>
                </div>
                <div class="section-actions baseline-actions-panel" style="flex-wrap: wrap; gap: 8px;">
                  <div class="section1-filter-inline">
                    <span class="filter-label">过滤需求主体：</span>
                    <select v-model="selectedFittingSection1Id" class="input inline-select">
                      <option value="ALL">🌐 全部标段 (全量查看与维护)</option>
                      <option v-for="section1 in demandEntities" :key="section1.section_1_id" :value="section1.section_1_id">
                        {{ section1.section_1_name || section1.section_1_id }} ({{ section1.section_1_id }})
                      </option>
                    </select>
                  </div>
                  <button class="btn ghost compact-btn" type="button" @click="addFittingBaselineRow">➕ 增行</button>
                  <button class="btn ghost compact-btn" type="button" @click="addFittingBaselineRows(5)">➕ 增5行</button>
                  <button class="btn ghost compact-btn" type="button" @click="exportFittingBaselineTemplate">📥 导出模板</button>
                  <button class="btn ghost compact-btn" type="button" @click="triggerFittingExcelUpload">📤 导入Excel</button>
                  <button class="btn danger-ghost compact-btn" type="button" @click="clearCurrentSectionFittingBaselines">
                    🗑️ {{ selectedFittingSection1Id === 'ALL' ? '清空全部数据' : '清空本标段' }}
                  </button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('fitting_baselines')" @click="saveSection('fitting_baselines')">
                    {{ isSaving('fitting_baselines') ? '保存中…' : '💾 保存管件基准' }}
                  </button>
                  <input ref="fittingExcelFileInput" type="file" accept=".xlsx, .xls" style="display: none;" @change="handleFittingExcelFile" />
                </div>
              </div>

              <p v-if="sectionMessage('fitting_baselines')" :class="['section-tip', sectionMessage('fitting_baselines').type]">
                {{ sectionMessage('fitting_baselines').text }}
              </p>

              <div class="summary-row baseline-summary">
                <span class="summary-chip">📍 当前站点：<strong>{{ selectedFittingSection1Name }}</strong></span>
                <span class="summary-chip">📊 当前显示：<strong>{{ filteredFittingBaselines.length }}</strong> 条管件</span>
                <span class="summary-chip">🗂️ 全量管件：<strong>{{ fittingBaselines.length }}</strong> 条</span>
                <span class="summary-chip" style="color: #64748b;">💡 提示：双击单元格可自由编辑，支持从 Excel 复制后直接按 Ctrl+V 批量填入</span>
              </div>

              <div class="table-wrap card" style="min-height: 320px; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden; background: #fff; margin-top: 10px;">
                <RevoGrid
                  ref="fittingGridRef"
                  :row-headers="true"
                  :hide-attribution="true"
                  :stretch="true"
                  :row-size="34"
                  :resize="true"
                  :range="true"
                  :can-focus="true"
                  :apply-on-close="true"
                  :columns="fittingGridColumns"
                  :source="fittingGridSource"
                  style="height: 380px; width: 100%;"
                  @afteredit="handleFittingGridAfterEdit"
                  @afterEdit="handleFittingGridAfterEdit"
                />
              </div>
            </section>
          </div>

          <!-- Tab 5.5: 气温数据管理 (恢复原始干净架构) -->
          <div v-if="activeTab === 'weather'" class="pane-content-wrapper">
            <!-- 1. 气象库已存数据统计 -->
            <section class="card elevated section-card weather-stats-overview">
              <div class="card-header">⛅ 气象库已存数据统计</div>
              <p class="sub">统计当前管网系统底层数据库中缓存的日级天气与逐小时温度的总记录状况。</p>
              
              <div class="weather-meta-grid">
                <div class="weather-meta-item">
                  <span class="weather-meta-label">日级气象已存</span>
                  <strong class="weather-meta-value">{{ dailyCount }} 条记录</strong>
                  <span class="weather-meta-desc">历史日期区间：{{ minDate }} 至 {{ maxDate }}</span>
                </div>
                <div class="weather-meta-item">
                  <span class="weather-meta-label">逐小时气温缓存</span>
                  <strong class="weather-meta-value">{{ hourlyCount }} 条温度点</strong>
                  <span class="weather-meta-desc">用于精确日最高、平均温算术解算</span>
                </div>
                <div class="weather-meta-item highlight">
                  <span class="weather-meta-label">当前运行模式</span>
                  <strong class="weather-meta-value">{{ weatherProvider === 'amap' ? '高德气象 API (推荐)' : 'Open-Meteo API' }}</strong>
                  <span class="weather-meta-desc">{{ weatherProvider === 'amap' ? '中国气象局官方数据源与实时解析' : 'WMO 标准天气解码与降雨推导校正' }}</span>
                </div>
              </div>
            </section>

            <!-- 2. 气象数据源模式切换 (纯粹独立切换选框) -->
            <section class="card elevated section-card weather-provider-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">🌐 气象数据源模式切换 (Weather Provider Switch)</div>
                  <p class="sub block-sub">
                    在此自由切换系统底层气象数据的服务提供商。推荐使用中国气象局官方权威数据源（高德天气 API）。
                  </p>
                </div>
              </div>

              <div class="provider-selector-grid">
                <label class="provider-option-card" :class="{ active: weatherProvider === 'amap' }">
                  <input type="radio" value="amap" v-model="weatherProvider" name="weatherProviderRadio" />
                  <div class="provider-card-content">
                    <div class="provider-title">
                      <span class="provider-badge amap">📍 高德气象 API (推荐)</span>
                      <span class="provider-source">中国气象局官方站点数据源</span>
                    </div>
                    <p class="provider-desc">
                      由中国气象局官方气象台实时提供大连市主城区（210200）权威预报，天气状况描述与 WeatherCode 100% 准确自洽。
                    </p>
                  </div>
                </label>

                <label class="provider-option-card" :class="{ active: weatherProvider === 'open_meteo' }">
                  <input type="radio" value="open_meteo" v-model="weatherProvider" name="weatherProviderRadio" />
                  <div class="provider-card-content">
                    <div class="provider-title">
                      <span class="provider-badge open-meteo">🌐 Open-Meteo 全球 API</span>
                      <span class="provider-source">包含日降水量 (rain_sum) 动态推理修正</span>
                    </div>
                    <p class="provider-desc">
                      基于开源全球数值模型，已自动注入针对“零降雨量误报阵雨”问题的逻辑安全纠偏规则。
                    </p>
                  </div>
                </label>
              </div>

              <div class="provider-save-bar">
                <button 
                  class="btn primary compact-btn" 
                  type="button" 
                  :disabled="isSaving('weather_provider')" 
                  @click="saveWeatherProvider"
                >
                  {{ isSaving('weather_provider') ? '正在保存模式...' : '💾 保存气象数据源模式' }}
                </button>
                <p v-if="sectionMessage('weather_provider')" :class="['section-tip', sectionMessage('weather_provider').type]" style="margin: 0;">
                  {{ sectionMessage('weather_provider').text }}
                </p>
              </div>
            </section>

            <!-- 3. 配置 API 网址与高德 Key 面板 (独立集中在下方) -->
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">🛠️ 气象数据接口与 API 密钥配置</div>
                  <p class="sub block-sub">
                    在此集中维护高德 Web 服务 REST Key 与 Open-Meteo 接口网址。修改后点击保存可写入系统的配置文件。
                  </p>
                </div>
              </div>

              <div class="weather-config-form">
                <!-- 高德 Web 服务 API Key 配置项 -->
                <div class="field">
                  <span>🔑 高德 Web服务 (REST API) 密钥 Key</span>
                  <div class="input-with-action" style="display: flex; gap: 8px; width: 100%;">
                    <input 
                      v-model="amapRestKey" 
                      :type="showAmapRestKey ? 'text' : 'password'" 
                      class="input" 
                      style="flex: 1; font-family: monospace;" 
                      placeholder="请输入高德开放平台申请的 Web服务 (REST API) Key..." 
                    />
                    <button 
                      type="button" 
                      class="btn ghost" 
                      @click="showAmapRestKey = !showAmapRestKey"
                    >
                      {{ showAmapRestKey ? '🙈 隐藏' : '👁️ 显示' }}
                    </button>
                  </div>
                  <small class="field-help">
                    说明：需为高德开放平台申请的【Web服务】类型 Key，用于服务端实时连线气象接口。
                  </small>
                </div>

                <!-- Open-Meteo 网址配置项 -->
                <div class="field">
                  <span>🌐 Open-Meteo 气象 API 网址 (weather_api_url)</span>
                  <textarea 
                    v-model="weatherApiUrl" 
                    class="input weather-textarea" 
                    placeholder="请输入 Open-Meteo API 地址..."
                    rows="3"
                  ></textarea>
                  <small class="field-help">
                    说明：预设大连主城区坐标。输入框可自由编辑。若直接点击“拉取评估与导入”，系统将按照当前编辑框内的临时 API 连线拉取。
                  </small>
                </div>

                <p v-if="sectionMessage('weather_api_url')" :class="['section-tip', sectionMessage('weather_api_url').type]">
                  {{ sectionMessage('weather_api_url').text }}
                </p>

                <div class="weather-actions-panel">
                  <button 
                    class="btn ghost" 
                    type="button" 
                    @click="weatherApiUrl = 'https://api.open-meteo.com/v1/forecast?latitude=38.875&longitude=121.625&timezone=Asia%2FSingapore&daily=weather_code,rain_sum,uv_index_max&hourly=temperature_2m&past_days=5'"
                  >
                    🔄 恢复默认网址
                  </button>
                  <div class="action-btn-group">
                    <button 
                      class="btn ghost" 
                      type="button" 
                      :disabled="isSaving('weather_api_url')" 
                      @click="saveWeatherApiUrl"
                    >
                      {{ isSaving('weather_api_url') ? '正在保存…' : '💾 保存配置修改' }}
                    </button>
                    <button 
                      class="btn primary shadow-accent" 
                      type="button" 
                      :disabled="evalLoading" 
                      @click="handleEvalWeatherImport"
                    >
                      {{ evalLoading ? '正在连线拉取评估…' : '📊 拉取评估并物理导入' }}
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </div>

          <!-- Tab 5.8: 高德地图 GIS API 配置 -->
          <div v-if="activeTab === 'gis'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">🗺️ 高德地图 (AMap API & Security Key) 配置</div>
                  <p class="sub block-sub">
                    设置高德地图 Web JS API 2.0 的 API Key 与安全密钥 (Security Code)。
                    系统将以简单 XOR+Base64 加密算法存入 <code>tube_config.json</code>，确保物理磁盘配置文件不裸露明文密钥。
                  </p>
                </div>
                <div class="section-actions">
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('amap_config')" @click="saveSection('amap_config')">
                    {{ isSaving('amap_config') ? '保存中…' : '💾 保存高德地图配置' }}
                  </button>
                </div>
              </div>

              <div class="field-grid core-field-grid">
                <label class="field field-span-2">
                  <span>高德地图 API Key (api_key)</span>
                  <div class="input-with-action" style="display: flex; gap: 8px; width: 100%;">
                    <input 
                      v-model="amapApiKey" 
                      :type="showAmapKeys ? 'text' : 'password'" 
                      class="input" 
                      placeholder="请输入高德地图应用 Key (如: f49ff8e523dd...)" 
                    />
                  </div>
                  <small class="field-help">用于前端调用高德 Web JS API 2.0 渲染地图、搜寻 POI 与绘制管道连线。</small>
                </label>
                
                <label class="field field-span-2">
                  <span>高德地图安全密钥 (security_code / securityJsCode)</span>
                  <div class="input-with-action" style="display: flex; gap: 8px; width: 100%;">
                    <input 
                      v-model="amapSecurityCode" 
                      :type="showAmapKeys ? 'text' : 'password'" 
                      class="input" 
                      placeholder="请输入高德地图安全 Key (如: 7573fa30e86...)" 
                    />
                  </div>
                  <small class="field-help">用于高德 API 2.0 安全校验 (window._AMapSecurityConfig.securityJsCode)。</small>
                </label>
              </div>

              <div style="margin-top: 15px; display: flex; align-items: center; gap: 10px;">
                <button class="btn ghost compact-btn" type="button" @click="showAmapKeys = !showAmapKeys">
                  {{ showAmapKeys ? '🔒 隐藏密钥明文' : '👁️ 显示密钥明文' }}
                </button>
                <span style="font-size: 12px; color: #64748b;">
                  存储加密协议：<code>enc_v1: [XOR+Base64]</code> 存入 <code>tube_config.json</code>
                </span>
              </div>

              <p v-if="sectionMessage('amap_config')" :class="['section-tip', sectionMessage('amap_config').type]">
                {{ sectionMessage('amap_config').text }}
              </p>
            </section>
          </div>

          <!-- Tab: 单据识别模型与 API 密钥配置 (Gemini Config) -->
          <div v-if="activeTab === 'gemini_config'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">⚡ 单据识别模型与 API 密钥配置</div>
                  <p class="sub block-sub">
                    按调用次序手填 3 个识别模型名称（首选模型与 2 个备选兜底模型），以及 Gemini API Key。
                  </p>
                </div>
                <div class="section-actions">
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('ocr_tool_config')" @click="saveSection('ocr_tool_config')">
                    {{ isSaving('ocr_tool_config') ? '保存中…' : '💾 保存配置' }}
                  </button>
                </div>
              </div>

              <div class="field-grid core-field-grid">
                <!-- 1. 模型列表（3个手填型号输入框） -->
                <div class="field field-span-2" style="display: flex; flex-direction: column; gap: 14px;">
                  <span style="font-weight: 600; color: #334155; font-size: 14px;">识别模型列表（按先后次序自动兜底）：</span>
                  
                  <label class="field" style="margin: 0;">
                    <span style="font-size: 13px; font-weight: 600; color: #1e293b;">模型 1 (首选主力)</span>
                    <input
                      v-model="ocrModel1"
                      type="text"
                      class="input"
                      placeholder="手填首选模型名称，例如: gemini-3.5-flash-lite"
                    />
                  </label>

                  <label class="field" style="margin: 0;">
                    <span style="font-size: 13px; font-weight: 600; color: #475569;">模型 2 (第 1 备选兜底)</span>
                    <input
                      v-model="ocrModel2"
                      type="text"
                      class="input"
                      placeholder="手填第 1 备选模型名称，例如: gemini-3.7-flash"
                    />
                  </label>

                  <label class="field" style="margin: 0;">
                    <span style="font-size: 13px; font-weight: 600; color: #475569;">模型 3 (第 2 备选兜底)</span>
                    <input
                      v-model="ocrModel3"
                      type="text"
                      class="input"
                      placeholder="手填第 2 备选模型名称，例如: gemini-3.5-flash"
                    />
                  </label>
                </div>

                <!-- 2. Gemini API Key -->
                <label class="field field-span-2">
                  <span style="font-weight: 600; color: #334155; font-size: 14px;">Gemini API Key (api_key)</span>
                  <div class="input-with-action" style="display: flex; gap: 8px; width: 100%;">
                    <input 
                      v-model="ocrApiKey" 
                      :type="showOcrKeys ? 'text' : 'password'" 
                      class="input" 
                      placeholder="请输入 Google Gemini API Key (如: AIzaSy...)" 
                    />
                    <button class="btn ghost compact-btn" type="button" @click="showOcrKeys = !showOcrKeys">
                      {{ showOcrKeys ? '🔒 隐藏' : '👁️ 显示' }}
                    </button>
                  </div>
                </label>
              </div>

              <div style="margin-top: 15px; display: flex; align-items: center; gap: 10px;">
                <span class="status-indicator" v-if="ocrApiKey">
                  🟢 当前已配置独立密钥
                </span>
                <span class="status-indicator warning" v-else>
                  🟡 尚未配置独立密钥（系统将自动尝试读取全局共享密钥）
                </span>
              </div>

              <p v-if="sectionMessage('ocr_tool_config')" :class="['section-tip', sectionMessage('ocr_tool_config').type]">
                {{ sectionMessage('ocr_tool_config').text }}
              </p>
            </section>
          </div>

          <!-- Tab 6: 原始 JSON 预览 -->
          <div v-if="activeTab === 'json'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">原始 JSON 数据配置控制台</div>
                  <p class="sub block-sub">直接编辑底层的 JSON 结构并一键落盘。编辑后点击右下角“保存 JSON 配置”，系统将进行实时合法性校验并覆盖全局数据库。</p>
                </div>
              </div>
              
              <!-- 本地 JSON 校验错误高亮展示框 -->
              <div v-if="jsonErrorMessage" class="json-error-banner">
                <div class="json-error-banner__header">
                  <strong>🚨 配置解析阻断：输入语法错误</strong>
                  <button class="btn link-btn" style="color: #ffffff !important;" @click="jsonErrorMessage = ''">×</button>
                </div>
                <div class="json-error-banner__body">{{ jsonErrorMessage }}</div>
              </div>

              <textarea 
                v-model="jsonEditVal" 
                :class="['json-editor-textarea', { 'has-error': jsonErrorMessage }]" 
                spellcheck="false" 
                placeholder="原始整个 JSON 结构在此加载并允许编辑..."
              ></textarea>
              <div class="json-editor-actions">
                <span class="json-editor-hint">⚠️ 请极其谨慎操作！JSON 配置格式损坏（如逗号、中括号缺失）可能会直接导致平台报错！</span>
                <div class="action-btn-group">
                  <button class="btn ghost" type="button" @click="resetJsonEditVal">重置当前编辑</button>
                  <button class="btn primary" type="button" :disabled="savingJson" @click="handleSaveRawJson">
                    {{ savingJson ? '正在提交配置...' : '保存 JSON 配置' }}
                  </button>
                </div>
              </div>
            </section>
          </div>

          <!-- Tab 8: 操作审计日志 -->
          <div v-if="activeTab === 'audit'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">📜 操作审计日志</div>
                </div>
                <div class="section-actions">
                  <button class="btn ghost compact-btn" type="button" @click="fetchAuditLogs(1)">
                    🔄 刷新审计日志
                  </button>
                </div>
              </div>

              <!-- 态势概览看板 -->
              <div class="audit-overview">
                <div class="audit-overview__lead">
                  <div class="audit-overview__icon" aria-hidden="true">⏱️</div>
                  <div class="audit-overview__copy">
                    <div class="audit-overview__label">数据库最新操作物理时间</div>
                    <div class="audit-overview__time">
                      <span>{{ auditLatestTime ? formatDateTime(auditLatestTime) : '尚无操作记录' }}</span>
                      <span
                        v-if="auditLatestTime"
                        class="audit-overview__age"
                        :style="getTimeAgoBadgeStyle(auditLatestTime)"
                      >
                        {{ formatTimeAgo(auditLatestTime) }}
                      </span>
                    </div>
                  </div>
                </div>

                <!-- 核心态势指标看板 -->
                <div class="audit-metrics">
                  <div class="audit-metric audit-metric--total">
                    <div class="audit-metric__label">今日操作总量</div>
                    <div class="audit-metric__value">{{ auditTodayCount }} <span>笔</span></div>
                  </div>
                  <div
                    class="audit-metric audit-metric--sensitive"
                    :class="{ 'is-active': auditFilters.isSensitive, 'has-alert': auditSensitiveCount > 0 }"
                    @click="toggleSensitiveFilter"
                    title="点击快捷切换筛选高危敏感操作"
                  >
                    <div class="audit-metric__label">
                      <span v-if="auditSensitiveCount > 0">🚨 </span>高危敏感操作
                    </div>
                    <div class="audit-metric__value">{{ auditSensitiveCount }} <span>笔</span></div>
                  </div>
                  <div class="audit-metric audit-metric--operator">
                    <div class="audit-metric__label">活跃操作账号</div>
                    <div class="audit-metric__value">{{ auditOperatorCount }} <span>人</span></div>
                  </div>
                </div>
              </div>
              
              <!-- 6 列工整过滤控制面板 -->
              <div class="audit-filter-panel">
                <label class="audit-filter-item">
                  <span>操作行为分类</span>
                  <select v-model="auditFilters.actionType" class="select" @change="fetchAuditLogs(1)">
                    <option value="">全部行为类型 (All Actions)</option>
                    <optgroup label="🚨 高危与特殊管理">
                      <option value="SUPER_UPDATE_DELIVERY">🚨 超管强改 (SUPER_UPDATE)</option>
                      <option value="SUPER_UPDATE_FITTING_DELIVERY">🚨 超管强改管件 (SUPER_UPDATE_FITTING)</option>
                      <option value="UPDATE_CONFIG">⚙️ 配置修改 (UPDATE_CONFIG)</option>
                      <option value="CANCEL_DELIVERY">❌ 撤销发货 (CANCEL_DELIVERY)</option>
                      <option value="CANCEL_FITTING_DELIVERY">❌ 撤销管件发货 (CANCEL_FITTING)</option>
                      <option value="DELETE_FITTING_DELIVERY">🗑️ 废弃管件发货 (DELETE_FITTING)</option>
                    </optgroup>
                    <optgroup label="🚚 管道物流与履约">
                      <option value="CREATE_DELIVERY">🚚 新增发货单 (CREATE_DELIVERY)</option>
                      <option value="CONFIRM_ARRIVAL">👷 现场到货确认 (CONFIRM_ARRIVAL)</option>
                      <option value="CONFIRM_CONSTRUCTION">🏗️ 施工接收确认 (CONFIRM_CONSTRUCTION)</option>
                      <option value="CONFIRM_WAREHOUSE">🏢 库管入库确认 (CONFIRM_WAREHOUSE)</option>
                    </optgroup>
                    <optgroup label="🔩 管件物流与流转">
                      <option value="SUBMIT_FITTING_DELIVERY">🔩 提交管件发货 (SUBMIT_FITTING)</option>
                      <option value="CONFIRM_FITTING_ARRIVAL">👷 管件到货确认 (FITTING_ARRIVAL)</option>
                      <option value="CONFIRM_FITTING_CONSTRUCTION">🏗️ 管件施工接收 (FITTING_CONSTRUCTION)</option>
                      <option value="CONFIRM_FITTING_WAREHOUSE">🏢 管件库管确认 (FITTING_WAREHOUSE)</option>
                    </optgroup>
                    <optgroup label="📋 计划与消耗填报">
                      <option value="SAVE_PLAN">📅 保存三日计划 (SAVE_PLAN)</option>
                      <option value="SUBMIT_USAGE">🔋 上报消耗损耗 (SUBMIT_USAGE)</option>
                      <option value="SUBMIT_STATUS">✅ 提交填报完成 (SUBMIT_STATUS)</option>
                    </optgroup>
                  </select>
                </label>

                <label class="audit-filter-item">
                  <span>关联单号 / 资源 ID</span>
                  <input v-model.trim="auditFilters.resourceId" class="input" type="text" placeholder="发货单号/换热站ID" @keyup.enter="fetchAuditLogs(1)" />
                </label>

                <label class="audit-filter-item">
                  <span>操作账号 / 姓名</span>
                  <input v-model.trim="auditFilters.operator" class="input" type="text" placeholder="搜索账号或姓名" @keyup.enter="fetchAuditLogs(1)" />
                </label>

                <label class="audit-filter-item">
                  <span>操作详情关键词</span>
                  <input v-model.trim="auditFilters.keyword" class="input" type="text" placeholder="搜索详情说明/参数" @keyup.enter="fetchAuditLogs(1)" />
                </label>

                <label class="audit-filter-item">
                  <span>开始日期</span>
                  <input v-model="auditFilters.startDate" class="input" type="date" />
                </label>

                <label class="audit-filter-item">
                  <span>结束日期</span>
                  <input v-model="auditFilters.endDate" class="input" type="date" />
                </label>

                <!-- 第三行：左侧敏感过滤开关，右侧按钮组 -->
                <div class="audit-filter-toggle-wrap">
                  <label class="audit-toggle-chip" :class="{ active: auditFilters.isSensitive }">
                    <input type="checkbox" v-model="auditFilters.isSensitive" @change="fetchAuditLogs(1)" />
                    <span class="audit-toggle-text">🚨 仅看高危敏感操作 (强改/配置/撤销)</span>
                  </label>
                </div>

                <div class="audit-filter-actions">
                  <button class="btn primary audit-query-btn" type="button" @click="fetchAuditLogs(1)">
                    🔍 查询日志
                  </button>
                  <button class="btn ghost audit-reset-btn" type="button" @click="resetAuditFilters">
                    🔄 重置
                  </button>
                  <button class="btn ghost audit-export-btn" type="button" :disabled="exportLoading" @click="handleExportLogs">
                    <span>{{ exportLoading ? '导出中…' : '📥 导出 CSV' }}</span>
                  </button>
                </div>
              </div>

              <!-- 日志明细列表 -->
              <div v-if="auditLoading" class="loading-placeholder" style="padding: 40px; text-align: center; color: #64748b;">
                数据审计日志加载中...
              </div>
              <div v-else-if="auditLogs.length === 0" class="empty-placeholder" style="padding: 40px; text-align: center; color: #777;">
                未查询到任何匹配的操作审计日志。
              </div>
              <div v-else>
                <div class="audit-table-wrap">
                  <table class="table editor-table audit-log-table">
                    <colgroup>
                      <col class="audit-col-time" />
                      <col class="audit-col-resource" />
                      <col class="audit-col-operator" />
                      <col class="audit-col-action" />
                      <col class="audit-col-desc" />
                      <col class="audit-col-diff" />
                    </colgroup>
                    <thead>
                      <tr>
                        <th>操作时间与来源 IP</th>
                        <th>关联单号 / 资源 ID</th>
                        <th>操作账号 / 角色</th>
                        <th>行为类型</th>
                        <th>数据操作内容与详情说明</th>
                        <th>快照对比</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="log in auditLogs" :key="log.id" :class="{ 'audit-row--sensitive': isSensitiveAction(log.action_type) }">
                        <!-- 操作时间与 IP -->
                        <td class="audit-time-cell">
                          <div class="audit-time-value">{{ formatDateTime(log.created_at) }}</div>
                          <div class="audit-time-meta">
                            <span v-if="isRecent24h(log.created_at)" class="audit-recent-badge">
                              🔥 最新
                            </span>
                            <button 
                              v-if="log.client_ip" 
                              class="audit-ip clickable-ip" 
                              type="button"
                              title="点击查看 IP 归属地与网络运营商"
                              @click.stop="triggerIpPopover($event, log.client_ip)"
                            >
                              📍 IP: {{ log.client_ip }}
                            </button>
                          </div>
                        </td>

                        <!-- 关联单号 / 资源 ID -->
                        <td class="audit-resource-cell">
                          <div v-if="log.resource_id" class="audit-resource-box">
                            <span class="audit-resource-code" :title="log.resource_id">{{ log.resource_id }}</span>
                            <div class="audit-resource-actions">
                              <button class="audit-micro-btn" title="复制单号" @click="copyResourceId(log.resource_id)">
                                {{ auditCopiedId === log.resource_id ? '✓' : '📋' }}
                              </button>
                              <button class="audit-micro-btn" title="以此单号筛选" @click="filterByResourceId(log.resource_id)">
                                🔍
                              </button>
                            </div>
                          </div>
                          <span v-else class="audit-empty-dash">—</span>
                        </td>

                        <!-- 操作人与角色 -->
                        <td class="audit-operator-cell">
                          <div class="audit-operator-name">{{ log.operator || '系统' }}</div>
                          <div v-if="log.operator_group" class="audit-operator-meta">
                            <span class="submission-group-chip">
                              {{ log.operator_group }}
                            </span>
                          </div>
                        </td>

                        <!-- 行为类型 -->
                        <td class="audit-action-cell">
                          <span class="badge audit-action-badge" :style="getActionTypeBadgeStyle(log.action_type)">
                            <span v-if="isSensitiveAction(log.action_type)" class="audit-sensitive-dot">🚨 </span>
                            {{ translateActionType(log.action_type) }}
                          </span>
                        </td>

                        <!-- 操作详情说明 -->
                        <td class="audit-desc-cell">
                          <div class="audit-desc-text" :title="log.action_desc">
                            <span v-if="getSection1NameFromLog(log)" class="submission-section-chip" :title="`对应需求主体: ${getSection1NameFromLog(log)}`">
                              📍 {{ getSection1NameFromLog(log) }}
                            </span>
                            <span>{{ getCleanActionDesc(log) }}</span>
                          </div>
                        </td>

                        <!-- 快照对比 -->
                        <td class="audit-diff-cell">
                          <button 
                            v-if="log.before_value || log.after_value" 
                            class="btn ghost compact-btn audit-diff-trigger-btn" 
                            @click="showDiffModal(log)"
                          >
                            🔍 智能对比
                          </button>
                          <span v-else class="audit-empty-dash">无快照</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 分页控制栏 -->
                <div class="pagination-bar audit-pagination-bar">
                  <div class="audit-pagination-left">
                    <span>共计 <strong>{{ auditTotal }}</strong> 条审计记录</span>
                    <span class="audit-pagination-divider">|</span>
                    <div class="audit-page-size-wrap">
                      <span>每页</span>
                      <select v-model="auditLimit" class="select audit-limit-select" @change="fetchAuditLogs(1)">
                        <option :value="15">15 条</option>
                        <option :value="20">20 条</option>
                        <option :value="50">50 条</option>
                        <option :value="100">100 条</option>
                      </select>
                    </div>
                  </div>
                  
                  <div class="audit-pagination-right">
                    <button class="btn ghost compact-btn" :disabled="auditPage <= 1" @click="fetchAuditLogs(auditPage - 1)">上一页</button>
                    <span class="audit-page-info">
                      第 <strong>{{ auditPage }}</strong> 页 / 共 <strong>{{ Math.ceil(auditTotal / auditLimit) || 1 }}</strong> 页
                    </span>
                    <button class="btn ghost compact-btn" :disabled="auditPage >= Math.ceil(auditTotal / auditLimit)" @click="fetchAuditLogs(auditPage + 1)">下一页</button>
                    
                    <div class="audit-jump-box">
                      <input v-model.number="auditJumpPage" type="number" min="1" :max="Math.ceil(auditTotal / auditLimit) || 1" placeholder="页码" class="input audit-jump-input" @keyup.enter="handleAuditJumpPage" />
                      <button class="btn ghost compact-btn" @click="handleAuditJumpPage">跳转</button>
                    </div>
                  </div>
                </div>
              </div> <!-- 闭合 v-else -->
            </section>
          </div>

        </div>

      </div>
    </main>

    <!-- 快照 Diff 智能对比弹窗 -->
    <div v-if="diffModalVisible" class="modal-overlay audit-modal-overlay" @click.self="diffModalVisible = false">
      <div class="modal-card audit-diff-modal">
        <header class="modal-header audit-modal-header">
          <div class="audit-modal-header__main">
            <h3 class="modal-title audit-modal-title">
              🔍 实体变更快照智能对比与追溯
              <span v-if="selectedLog && isSensitiveAction(selectedLog.action_type)" class="badge danger audit-modal-sensitive-tag">🚨 高危操作</span>
            </h3>
            <div class="audit-modal-subtitle">
              <span>单号: <strong>{{ selectedLog?.resource_id || '—' }}</strong></span>
              <span class="audit-sep">•</span>
              <span>操作人: <strong>{{ selectedLog?.operator || '未知' }}</strong></span>
              <span class="audit-sep">•</span>
              <span>类型: <strong>{{ translateActionType(selectedLog?.action_type) }}</strong></span>
              <span class="audit-sep">•</span>
              <span>时间: {{ formatDateTime(selectedLog?.created_at) }}</span>
            </div>
          </div>
          
          <div class="audit-modal-header__actions">
            <!-- 视图模式切换 -->
            <div class="audit-view-tabs">
              <button 
                class="audit-view-tab" 
                :class="{ 'is-active': diffViewMode === 'smart' }" 
                @click="diffViewMode = 'smart'"
              >
                ⚡ 智能差异解析
              </button>
              <button 
                class="audit-view-tab" 
                :class="{ 'is-active': diffViewMode === 'raw' }" 
                @click="diffViewMode = 'raw'"
              >
                📋 原始快照对比
              </button>
            </div>
            <button class="btn-close" type="button" @click="diffModalVisible = false">×</button>
          </div>
        </header>

        <!-- 弹窗 Body -->
        <div class="modal-body audit-modal-body">
          <!-- 模式 1: 智能差异解析 (Smart Diff) -->
          <div v-if="diffViewMode === 'smart'" class="audit-smart-diff-container">
            <!-- 状态 1: 纯新增 -->
            <div v-if="!selectedLog?.before_value && selectedLog?.after_value" class="audit-diff-banner audit-diff-banner--create">
              <div class="audit-diff-banner__icon">🌟</div>
              <div class="audit-diff-banner__content">
                <strong>初始新增录入</strong>
                <p>该条记录属于初始新增创建操作，无历史变更前数据。以下为本次提交录入的全部字段快照：</p>
              </div>
            </div>

            <!-- 状态 2: 纯删除/撤销 -->
            <div v-else-if="selectedLog?.before_value && !selectedLog?.after_value" class="audit-diff-banner audit-diff-banner--delete">
              <div class="audit-diff-banner__icon">🗑️</div>
              <div class="audit-diff-banner__content">
                <strong>实体撤销或删除</strong>
                <p>该条记录属于删除作废或撤销操作。以下为被清理实体的最终历史数据快照：</p>
              </div>
            </div>

            <!-- 状态 3: 字段修改或两端皆有 -->
            <div v-else-if="selectedLog?.before_value && selectedLog?.after_value" class="audit-diff-banner audit-diff-banner--modify">
              <div class="audit-diff-banner__icon">🔄</div>
              <div class="audit-diff-banner__content">
                <strong>实体数据字段变更</strong>
                <p>系统已比对提取出变更前后的差异字段，便于快速审计关键参数变动：</p>
              </div>
            </div>

            <!-- 结构化差异比对表格 -->
            <div class="audit-smart-table-wrap">
              <table class="table editor-table audit-smart-diff-table">
                <colgroup>
                  <col style="width: 220px;" />
                  <col style="width: 38%;" />
                  <col style="width: 40px;" />
                  <col style="width: 38%;" />
                </colgroup>
                <thead>
                  <tr>
                    <th>变更字段与属性</th>
                    <th>变更前数据 (Before)</th>
                    <th style="text-align: center;">➔</th>
                    <th>变更后数据 (After)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="diff in computedSmartDiff" :key="diff.key" :class="`audit-diff-row--${diff.changeType}`">
                    <td class="audit-diff-field-cell">
                      <div class="audit-diff-field-name">{{ diff.label }}</div>
                      <div class="audit-diff-field-key"><code>{{ diff.key }}</code></div>
                      <span class="badge compact" :class="getDiffTypeBadgeClass(diff.changeType)">
                        {{ getDiffTypeLabel(diff.changeType) }}
                      </span>
                    </td>
                    <td class="audit-diff-val-cell audit-diff-val-cell--before">
                      <div v-if="diff.changeType === 'added'" class="audit-val-placeholder">（无原值）</div>
                      <div v-else class="audit-val-content audit-val-content--del">
                        {{ formatDiffValue(diff.oldVal) }}
                      </div>
                    </td>
                    <td class="audit-diff-arrow-cell">➔</td>
                    <td class="audit-diff-val-cell audit-diff-val-cell--after">
                      <div v-if="diff.changeType === 'deleted'" class="audit-val-placeholder">（已清除）</div>
                      <div v-else class="audit-val-content audit-val-content--add">
                        {{ formatDiffValue(diff.newVal) }}
                      </div>
                    </td>
                  </tr>
                  <tr v-if="computedSmartDiff.length === 0">
                    <td colspan="4" class="audit-diff-empty">
                      前后快照字段值完全一致或无可解析差异项。
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 模式 2: 原始 JSON 对照 (Raw JSON) -->
          <div v-else class="audit-raw-json-container">
            <div class="audit-raw-column">
              <div class="audit-raw-header audit-raw-header--before">
                <span class="audit-raw-dot"></span>
                <span>变更前原始快照 (Before Snapshot)</span>
                <button class="btn ghost compact-btn audit-copy-json-btn" type="button" @click="copyJsonText(selectedLog?.before_value)">📋 复制 JSON</button>
              </div>
              <pre class="audit-json-pre audit-json-pre--before">{{ selectedLog?.before_value ? JSON.stringify(selectedLog.before_value, null, 2) : '（无原始数据快照 - 属于新增操作）' }}</pre>
            </div>

            <div class="audit-raw-column">
              <div class="audit-raw-header audit-raw-header--after">
                <span class="audit-raw-dot"></span>
                <span>变更后最新快照 (After Snapshot)</span>
                <button class="btn ghost compact-btn audit-copy-json-btn" type="button" @click="copyJsonText(selectedLog?.after_value)">📋 复制 JSON</button>
              </div>
              <pre class="audit-json-pre audit-json-pre--after">{{ selectedLog?.after_value ? JSON.stringify(selectedLog.after_value, null, 2) : '（无最新数据快照 - 属于删除或撤销操作）' }}</pre>
            </div>
          </div>
        </div>

        <footer class="modal-footer audit-modal-footer">
          <div v-if="diffCopyToast" class="audit-copy-toast">✓ 已复制快照数据到剪贴板</div>
          <button class="btn ghost compact-btn" type="button" @click="diffModalVisible = false">关闭窗口</button>
        </footer>
      </div>
    </div>

    <!-- 📍 IP 地理位置与运营商气泡弹窗 (Popover) -->
    <div v-if="ipPopoverState.visible" class="ip-popover-mask" @click="closeIpPopover">
      <div 
        class="ip-popover-card" 
        :style="{ left: `${ipPopoverState.x}px`, top: `${ipPopoverState.y}px` }"
        @click.stop
      >
        <div class="ip-popover-header">
          <div class="ip-popover-title">
            <span>🌐 IP 来源与地理位置</span>
          </div>
          <button class="ip-popover-close" type="button" @click="closeIpPopover">×</button>
        </div>

        <div class="ip-popover-body">
          <div class="ip-popover-address-row">
            <span class="ip-code">{{ ipPopoverState.ip }}</span>
            <button class="ip-copy-btn" type="button" :title="ipCopied ? '已复制' : '复制 IP'" @click="copyIpAddress(ipPopoverState.ip)">
              {{ ipCopied ? '✓ 已复制' : '📋 复制' }}
            </button>
          </div>

          <div v-if="ipPopoverState.loading" class="ip-popover-loading">
            <div class="ip-loading-spinner"></div>
            <span>正在查询 IP 归属地…</span>
          </div>

          <div v-else-if="ipPopoverState.error" class="ip-popover-error">
            <span>⚠️ {{ ipPopoverState.error }}</span>
          </div>

          <div v-else-if="ipPopoverState.data" class="ip-popover-details">
            <div class="ip-detail-item">
              <span class="ip-detail-label">📍 地理位置</span>
              <span class="ip-detail-value ip-detail-value--loc">
                {{ ipPopoverState.data.location || '未知位置' }}
              </span>
            </div>
            
            <div v-if="ipPopoverState.data.isp" class="ip-detail-item">
              <span class="ip-detail-label">🏢 网络运营</span>
              <span class="ip-detail-value">{{ ipPopoverState.data.isp }}</span>
            </div>

            <div v-if="ipPopoverState.data.adcode" class="ip-detail-item">
              <span class="ip-detail-label">🏷️ 行政代码</span>
              <span class="ip-detail-value ip-adcode-tag">{{ ipPopoverState.data.adcode }}</span>
            </div>

            <div class="ip-detail-item">
              <span class="ip-detail-label">🛡️ 网络类型</span>
              <span class="ip-detail-value">
                <span class="badge compact" :class="ipPopoverState.data.is_private ? 'badge-private-ip' : 'badge-public-ip'">
                  {{ ipPopoverState.data.is_private ? '内网 / 私有地址' : '公网 IPv4' }}
                </span>
              </span>
            </div>

            <div v-if="ipPopoverState.data.provider" class="ip-detail-item ip-detail-item--footer">
              <span class="ip-detail-label">⚡ 数据来源</span>
              <span class="ip-provider-tag">{{ ipPopoverState.data.provider }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 气象导入二次确认 Modal 弹窗 -->
    <div v-if="showEvalModal" class="weather-modal-mask">
      <div class="weather-modal-container card elevated">
        <header class="weather-modal-header">
          <h3>⛅ 气象数据导入变更预审与对照评估</h3>
          <button class="btn-close" type="button" @click="showEvalModal = false">×</button>
        </header>

        <div class="weather-modal-body">
          <div class="eval-summary-banner">
            <div class="eval-summary-title">📊 预审评估完成：连线 Open-Meteo 数据分析结果</div>
            
            <div class="eval-metrics-row">
              <div class="eval-metric-capsule">
                <span class="lbl">预评估天数</span>
                <strong class="val">{{ evalResult?.daily_stats?.total }} 天</strong>
              </div>
              <div class="eval-metric-capsule success">
                <span class="lbl">🌱 预计新增</span>
                <strong class="val">{{ evalResult?.daily_stats?.inserted }} 天</strong>
              </div>
              <div class="eval-metric-capsule warning">
                <span class="lbl">🔄 冲突覆盖</span>
                <strong class="val">{{ evalResult?.daily_stats?.updated }} 天</strong>
              </div>
              <div class="eval-metric-capsule info">
                <span class="lbl">💤 完全未变</span>
                <strong class="val">{{ evalResult?.daily_stats?.unchanged }} 天</strong>
              </div>
            </div>
            <p class="eval-summary-desc">
              提示：本次评估比对仅涉及日级气象属性（天气描述、最高/平均气温、降水量、紫外线），小时级细精温度将自动对齐做 Upsert 入库。重复日期的记录将使用新获取的外部数据完美覆盖合并。
            </p>
          </div>

          <!-- 待导入数据日级对照预览列表 -->
          <div class="weather-preview-table-wrap">
            <table class="table editor-table preview-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>天气情况 (WMO)</th>
                  <th>最高气温</th>
                  <th>算术平均温</th>
                  <th>最低气温</th>
                  <th>预计降水</th>
                  <th>最大紫外线</th>
                  <th>预审状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in evalResult?.preview_list" :key="row.date">
                  <td class="cell-date"><strong>{{ row.date }}</strong></td>
                  <td>{{ row.weather_text }} <small class="wmo-code-gray">(Code: {{ row.weather_code }})</small></td>
                  <td class="cell-num">{{ row.temp_max != null ? row.temp_max.toFixed(1) + ' °C' : '—' }}</td>
                  <td class="cell-num highlight-temp">{{ row.temp_mean != null ? row.temp_mean.toFixed(1) + ' °C' : '—' }}</td>
                  <td class="cell-num">{{ row.temp_min != null ? row.temp_min.toFixed(1) + ' °C' : '—' }}</td>
                  <td class="cell-num text-rain">{{ row.rain_sum != null ? row.rain_sum.toFixed(1) + ' mm' : '—' }}</td>
                  <td class="cell-num">{{ row.uv_index_max != null ? row.uv_index_max.toFixed(1) : '—' }}</td>
                  <td>
                    <span :class="['status-chip', row.status === 'inserted' ? 'success' : row.status === 'updated' ? 'warning' : 'pending']">
                      {{ row.status === 'inserted' ? '+ 新增' : row.status === 'updated' ? '✎ 覆盖更新' : '— 完全未变' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <footer class="weather-modal-footer">
          <span class="footer-hint">⚠️ 点击「确认物理导入」后，数据将写入 PostgreSQL 数据库，操作不可撤回！</span>
          <div class="action-btn-group">
            <button class="btn ghost" type="button" @click="showEvalModal = false">取消</button>
            <button 
              class="btn primary shadow-accent" 
              type="button" 
              :disabled="importLoading" 
              @click="handleConfirmWeatherImport"
            >
              {{ importLoading ? '正在物理覆盖入库中…' : '✓ 确认物理导入' }}
            </button>
          </div>
        </footer>
    </div>

    <!-- 操作详情气泡提示浮层 -->
    <div v-if="activePopoverLog" class="popover-overlay" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 9990; background: transparent;" @click="activePopoverLog = null"></div>
    <div v-if="activePopoverLog" :style="popoverStyle" style="position: fixed; z-index: 9995; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 14px 18px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05); max-width: 380px; min-width: 260px; font-size: 13px; color: #1e293b; line-height: 1.6; pointer-events: auto;">
      <!-- 小三角箭头 -->
      <div style="position: absolute; bottom: -6px; left: 50%; transform: translateX(-50%) rotate(45deg); width: 10px; height: 10px; background: #ffffff; border-right: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1;"></div>
      <div style="font-weight: 700; color: #475569; margin-bottom: 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
        <span style="display: flex; align-items: center; gap: 4px;">📋 操作详情描述</span>
        <span style="color: #94a3b8; font-size: 10px; font-weight: normal;">点击空白处关闭</span>
      </div>
      <div style="word-break: break-all; white-space: pre-wrap; color: #334155; font-size: 13px;">{{ activePopoverLog.action_desc }}</div>
    </div>
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import RevoGrid from '@revolist/vue3-datagrid'
import * as XLSX from 'xlsx-js-style'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh, navigateToUserInDirectory } from './shared'
import {
  getTubeGlobalManagementConfig,
  saveTubeGlobalManagementConfig,
  saveTubeGlobalManagementConfigSection,
  getTubeWeatherConfig,
  evaluateTubeWeatherImport,
  importTubeWeatherData,
  getTubeSubmissionLogs,
  getTubeAuditLogs,
  exportTubeAuditLogs,
  getTubeIpLocation,
} from '../../daily_report_25_26/services/api'

const router = useRouter()
const PROJECT_KEY = 'insulation_pipe_supply_2026'

const {
  loading,
  errorMessage,
  breadcrumbItems,
  goProjectPages,
  managementMode,
  modeLabels,
} = useTubePageShell('全局管理入口')

const activeTab = ref('submissions')

// 📥 主体数据提交记录相关 Ref 变量
const submissionLogs = ref([])
const submissionTotal = ref(0)
const submissionLoading = ref(false)
const submissionPage = ref(1)
const submissionLimit = ref(15)
const submissionLatestTime = ref(null)
const recent24hCount = ref(0)
const demand24hCount = ref(0)
const supply24hCount = ref(0)
const query24hCount = ref(0)
const submissionFilters = ref({
  category: '', // '' (全部) | 'submission' (提交类) | 'query' (查询类)
  entityType: '',
  actionType: '',
  operator: '',
  startDate: '',
  endDate: '',
})

// 📜 操作审计日志相关 Ref 变量与响应式状态
const auditLogs = ref([])
const auditTotal = ref(0)
const exportLoading = ref(false)
const auditLoading = ref(false)
const auditPage = ref(1)
const auditLimit = ref(20)
const auditLatestTime = ref(null)
const auditTodayCount = ref(0)
const auditSensitiveCount = ref(0)
const auditOperatorCount = ref(0)
const auditJumpPage = ref('')
const auditCopiedId = ref(null)

const auditFilters = ref({
  actionType: '',
  operator: '',
  resourceId: '',
  keyword: '',
  isSensitive: false,
  startDate: '',
  endDate: '',
})

// Diff 弹窗相关状态
const diffModalVisible = ref(false)
const selectedLog = ref(null)
const diffViewMode = ref('smart') // 'smart' 智能差异解析 vs 'raw' 原始 JSON 对照
const diffCopyToast = ref(false)

// 天气气温导入相关 Ref 变量
const dailyCount = ref(0)
const hourlyCount = ref(0)
const minDate = ref('—')
const maxDate = ref('—')
const weatherApiUrl = ref('')
const weatherProvider = ref('amap')
const amapRestKey = ref('')
const showAmapRestKey = ref(false)
const evalLoading = ref(false)
const importLoading = ref(false)
const showEvalModal = ref(false)
const evalResult = ref(null)

// 高德地图 GIS 配置 Ref 变量
const amapApiKey = ref('')
const amapSecurityCode = ref('')
const showAmapKeys = ref(false)

// ⚡ 单据识别引擎与 API 配置 Ref 变量（手填3个模型列表）
const ocrModel1 = ref('gemini-3.5-flash-lite')
const ocrModel2 = ref('gemini-3.7-flash')
const ocrModel3 = ref('gemini-3.5-flash')
const ocrApiKey = ref('')
const showOcrKeys = ref(false)

// 🔩 管件基础参数与校验配置 Ref 变量
const fittingAllowedUnitsText = ref('个, 套')
const fittingStandardTypesText = ref('弯头, 三通, 大小头, 封头, 直缝弯管, 补偿器, 固定节')

async function loadWeatherConfig() {
  try {
    const res = await getTubeWeatherConfig(PROJECT_KEY)
    dailyCount.value = res.daily_count ?? 0
    hourlyCount.value = res.hourly_count ?? 0
    minDate.value = res.min_date || '—'
    maxDate.value = res.max_date || '—'
    weatherApiUrl.value = res.weather_api_url || ''
    weatherProvider.value = res.weather_provider || 'amap'
    amapRestKey.value = res.amap_api_key || ''
  } catch (error) {
    console.error('加载天气配置与统计失败:', error)
  }
}

async function saveWeatherProvider() {
  clearGlobalMessage()
  setSectionMessage('weather_provider', 'success', '')
  setSaving('weather_provider', true)
  try {
    const val = String(weatherProvider.value || 'amap').trim()
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'weather_provider',
      data: val,
    })
    await loadWeatherConfig()
    setSectionMessage('weather_provider', 'success', `气象数据源模式已成功更新为【${val === 'amap' ? '高德气象 API' : 'Open-Meteo API'}】！`)
  } catch (error) {
    setSectionMessage('weather_provider', 'error', error?.message || '保存气象数据源模式失败')
  } finally {
    setSaving('weather_provider', false)
  }
}

async function saveWeatherApiUrl() {
  clearGlobalMessage()
  setSectionMessage('weather_api_url', 'success', '')
  setSaving('weather_api_url', true)
  try {
    const urlVal = String(weatherApiUrl.value || '').trim()
    if (!urlVal) {
      throw new Error('API 网址不能为空')
    }
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'weather_api_url',
      data: urlVal,
    })

    if (amapRestKey.value.trim()) {
      await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
        section: 'amap_config',
        data: { api_key: amapRestKey.value.trim(), security_code: '' },
      })
    }

    await loadWeatherConfig()
    setSectionMessage('weather_api_url', 'success', '气象 API 网址与高德 Web服务 REST Key 已成功保存生效！')
  } catch (error) {
    setSectionMessage('weather_api_url', 'error', error?.message || '保存配置失败')
  } finally {
    setSaving('weather_api_url', false)
  }
}



async function handleEvalWeatherImport() {
  clearGlobalMessage()
  setSectionMessage('weather_api_url', 'success', '')
  const urlVal = String(weatherApiUrl.value || '').trim()
  if (!urlVal) {
    setSectionMessage('weather_api_url', 'error', '请输入有效的气象 API 网址后再试')
    return
  }
  evalLoading.value = true
  try {
    const res = await evaluateTubeWeatherImport(PROJECT_KEY, { api_url: urlVal })
    if (res.ok) {
      evalResult.value = res
      showEvalModal.value = true
    } else {
      throw new Error(res.detail || '评估拉取失败')
    }
  } catch (error) {
    setSectionMessage('weather_api_url', 'error', error?.message || '拉取天气数据评估失败，请检查连线状态或 API 格式。')
  } finally {
    evalLoading.value = false
  }
}

async function handleConfirmWeatherImport() {
  if (!evalResult.value) return
  importLoading.value = true
  try {
    const urlVal = String(weatherApiUrl.value || '').trim()
    const res = await importTubeWeatherData(PROJECT_KEY, { api_url: urlVal })
    if (res.ok) {
      showEvalModal.value = false
      setSectionMessage('weather_api_url', 'success', `🎉 气温数据物理导入成功！本次共导入了 ${res.daily_count} 条日级记录，${res.hourly_count} 条逐小时温度记录，历史冲突数据已完美覆盖合并！`)
      // 刷新最新统计
      await loadWeatherConfig()
    } else {
      throw new Error(res.detail || '导入失败')
    }
  } catch (error) {
    setSectionMessage('weather_api_url', 'error', error?.message || '写入天气数据库失败，事务已安全回滚。')
  } finally {
    importLoading.value = false
  }
}
const showDate = ref('')
const usageCollectionDate = ref('')
const planStartDate = ref('')
const autoUpdatePlanStartDate = ref(false)
const isPlanDateAutoUpdateEnabled = computed(() => autoUpdatePlanStartDate.value !== false)
const isAllDatesAutoUpdateEnabled = computed(() => autoUpdatePlanStartDate.value === 'all')
const planEditableDays = ref(3)
const autoReceiveTimeoutHours = ref(12)
const strictPlanningFlowControl = ref(true)
const globalMessage = ref(null)
const jsonEditVal = ref('')
const jsonErrorMessage = ref('')
const savingJson = ref(false)
const sectionMessages = ref({})
const savingSections = ref({})

const supplyEntities = ref([])
const demandEntities = ref([])
const pipeModels = ref([])
const productionCapacities = ref([])
const managerAssignments = ref([])
const constructionUnits = ref([])
const warehouseKeepers = ref([])
const baselinePresets = ref([])
const submissionStatusPath = ref('')
const latestSubmissions = ref([])
const historySubmissions = ref([])
const selectedBaselineSection1Id = ref('')
const fittingBaselines = ref([])
const selectedFittingSection1Id = ref('ALL')
const fittingGridRef = ref(null)
const fittingExcelFileInput = ref(null)

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

function normalizePipeModelCode(value) {
  return String(value || '').trim().toUpperCase()
}

function parsePipeModelDiameter(value) {
  const matched = normalizePipeModelCode(value).match(/^DN(\d+)$/)
  return matched ? Number(matched[1]) : 0
}

function resolvePipeModelBucket(value) {
  const diameter = parsePipeModelDiameter(value)
  if (diameter >= 300) return 'large'
  if (diameter >= 150) return 'medium'
  if (diameter > 0) return 'small'
  return 'small'
}

function defaultQtyByPipeModel(pipeModelCode) {
  return null
}

function defaultRemarkByPipeModel(pipeModelCode) {
  return ''
}

function normalizeAssignmentRows(rows, idKey, nameKey) {
  return cloneRows(rows).map((item) => ({
    ...item,
    section_1_ids_text: listToText(item.section_1_ids),
    [idKey]: item[idKey] || '',
    [nameKey]: item[nameKey] || '',
  }))
}

function normalizeBaselineRows(rows) {
  return cloneRows(rows).map((item, index) => ({
    ...item,
    pipe_model_id: normalizePipeModelCode(item.pipe_model_id),
    pipe_model_name: normalizePipeModelCode(item.pipe_model_name || item.pipe_model_id),
    __row_key: `${item.section_1_id || 'section1'}::${normalizePipeModelCode(item.pipe_model_id) || 'model'}::${index}`,
    design_qty: Number(item.design_qty || 0),
    purchase_plan_qty: Number(item.purchase_plan_qty || 0),
    remark: item.remark || '',
  }))
}

function normalizeFittingBaselineRows(rows) {
  return cloneRows(rows).map((item, index) => ({
    ...item,
    section_1_id: String(item.section_1_id || '').trim(),
    system_type: String(item.system_type || '高温水').trim(),
    category: String(item.category || item.fitting_type || '管件').trim(),
    fitting_type: String(item.category || item.fitting_type || '管件').trim(),
    standard_name: String(item.standard_name || '').trim(),
    model_spec: String(item.model_spec || '').trim(),
    sub_model_spec: String(item.sub_model_spec || '').trim(),
    unit: String(item.unit || '个').trim() || '个',
    design_qty: Number(item.design_qty || 0),
    purchase_plan_qty: Number(item.purchase_plan_qty || 0),
    main_dn: item.main_dn != null ? Number(item.main_dn) : null,
    sub_dn: item.sub_dn != null ? Number(item.sub_dn) : null,
    angle: item.angle != null ? Number(item.angle) : null,
    bending_radius_ratio: item.bending_radius_ratio != null ? Number(item.bending_radius_ratio) : null,
    bending_radius_m: item.bending_radius_m != null ? Number(item.bending_radius_m) : null,
    valve_model: String(item.valve_model || '').trim(),
    outer_diameter: item.outer_diameter != null ? Number(item.outer_diameter) : null,
    wall_thickness: item.wall_thickness != null ? Number(item.wall_thickness) : null,
    length_m: item.length_m != null ? Number(item.length_m) : null,
    pressure_rating: String(item.pressure_rating || '').trim(),
    compensation_mm: item.compensation_mm != null ? Number(item.compensation_mm) : null,
    flow_direction: String(item.flow_direction || '').trim(),
    raw_model_spec: String(item.raw_model_spec || '').trim(),
    raw_name: String(item.raw_name || '').trim(),
    remark: String(item.remark || '').trim(),
    __row_key: `fitting::${item.section_1_id || 'sec'}::${item.system_type || 'sys'}::${item.standard_name || 'std'}::${item.model_spec || 'model'}::${index}`,
  }))
}

function normalizeSubmissionRows(rows) {
  return cloneRows(rows).map((item) => ({
    section_1_id: item.section_1_id || '',
    section_1_name: item.section_1_name || '',
    data_submit_date: item.data_submit_date || '',
    submitted_at: item.submitted_at || '',
    submitted_by: item.submitted_by || '',
    plan_start_date: item.plan_start_date || '',
    usage_date: item.usage_date || '',
    remark: item.remark || '',
  }))
}

function rebuildBaselineRowKeys() {
  baselinePresets.value = baselinePresets.value.map((item, index) => ({
    ...item,
    __row_key: `${item.section_1_id || 'section1'}::${normalizePipeModelCode(item.pipe_model_id) || 'model'}::${index}`,
  }))
}

function normalizePipeModelRows(rows) {
  return cloneRows(rows).map((item) => {
    const normalizedCode = normalizePipeModelCode(item.pipe_model_id || item.pipe_model_name)
    return {
      pipe_model_id: normalizedCode,
      pipe_model_name: normalizedCode,
      unit: String(item.unit || '米').trim() || '米',
    }
  })
}

function syncPipeModelIdentity(row, source = 'id') {
  const baseValue = source === 'name' ? row.pipe_model_name : row.pipe_model_id
  const normalizedCode = normalizePipeModelCode(baseValue)
  row.pipe_model_id = normalizedCode
  row.pipe_model_name = normalizedCode
  row.unit = String(row.unit || '米').trim() || '米'
}

function syncSelectedBaselineSection1() {
  const items = demandEntities.value.filter((item) => String(item.section_1_id || '').trim())
  if (!items.length) {
    selectedBaselineSection1Id.value = ''
    return
  }
  const validIds = items.map((item) => String(item.section_1_id || '').trim())

  // 若当前未选中或选中的 ID 无效，优先匹配“高温水_标段1”
  if (!selectedBaselineSection1Id.value || !validIds.includes(selectedBaselineSection1Id.value)) {
    const targetMatch = items.find((item) => {
      const name = String(item.section_1_name || '').trim()
      const id = String(item.section_1_id || '').trim()
      return name === '高温水_标段1' || name.includes('高温水_标段1') || id === 'high_lot_1' || id.includes('high_lot_1')
    })
    if (targetMatch && targetMatch.section_1_id) {
      selectedBaselineSection1Id.value = targetMatch.section_1_id
    } else {
      selectedBaselineSection1Id.value = validIds[0]
    }
  }
}

function syncSelectedFittingSection1() {
  if (selectedFittingSection1Id.value === 'ALL') {
    return
  }
  const items = demandEntities.value.filter((item) => String(item.section_1_id || '').trim())
  if (!items.length) {
    selectedFittingSection1Id.value = 'ALL'
    return
  }
  const validIds = items.map((item) => String(item.section_1_id || '').trim())
  if (!selectedFittingSection1Id.value || !validIds.includes(selectedFittingSection1Id.value)) {
    selectedFittingSection1Id.value = 'ALL'
  }
}

function applyConfig(config) {
  showDate.value = config.show_date || config.biz_date || ''
  usageCollectionDate.value = config.usage_collection_date || ''
  planStartDate.value = config.plan_start_date || showDate.value || ''
  autoUpdatePlanStartDate.value = normalizeAutoUpdateSetting(config.auto_update_plan_start_date)
  planEditableDays.value = Number(config.plan_editable_days ?? 3)
  autoReceiveTimeoutHours.value = config.auto_receive_timeout_hours !== undefined ? Number(config.auto_receive_timeout_hours) : 12
  strictPlanningFlowControl.value = config.strict_planning_flow_control ?? true
  supplyEntities.value = cloneRows(config.supply_entities).map(item => ({
    ...item,
    section_1_ids_text: listToText(item.section_1_ids),
  }))
  demandEntities.value = cloneRows(config.demand_entities)
  syncSelectedBaselineSection1()
  syncSelectedFittingSection1()
  pipeModels.value = normalizePipeModelRows(config.pipe_models)
  productionCapacities.value = cloneRows(config.production_capacities).map((item) => ({
    ...item,
    pipe_model_name: normalizePipeModelCode(item.pipe_model_name),
    max_daily_output_qty: Number(item.max_daily_output_qty || 0),
    remark: item.remark || '',
  }))
  managerAssignments.value = normalizeAssignmentRows(config.manager_assignments, 'manager_id', 'manager_name')
  constructionUnits.value = normalizeAssignmentRows(config.construction_units, 'unit_id', 'unit_name')
  warehouseKeepers.value = (config.warehouse_keepers || []).map((item) => ({
    keeper_id: item.keeper_id || '',
    keeper_name: item.keeper_name || '',
    contact_phone: item.contact_phone || '',
    section_1_ids_text: listToText(item.section_1_ids),
  }))
  baselinePresets.value = normalizeBaselineRows(config.baseline_presets)
  fittingBaselines.value = normalizeFittingBaselineRows(config.fitting_baselines)
  weatherApiUrl.value = config.weather_api_url || ''
  weatherProvider.value = config.weather_provider || 'amap'
  amapRestKey.value = config.amap_config?.api_key || ''
  
  const fittingCfg = config.fitting_config || {}
  fittingAllowedUnitsText.value = listToText(fittingCfg.allowed_units || ['个', '套'])
  fittingStandardTypesText.value = listToText(fittingCfg.standard_types || ['弯头', '三通', '大小头', '封头', '直缝弯管', '补偿器', '固定节'])
  
  if (config.ocr_tool_config) {
    ocrModel1.value = config.ocr_tool_config.model || 'gemini-3.5-flash-lite'
    const rawFb = config.ocr_tool_config.fallback_models
    if (Array.isArray(rawFb)) {
      ocrModel2.value = rawFb[0] || ''
      ocrModel3.value = rawFb[1] || ''
    } else if (typeof rawFb === 'string' && rawFb.trim()) {
      ocrModel2.value = rawFb.trim()
      ocrModel3.value = ''
    } else {
      ocrModel2.value = 'gemini-3.7-flash'
      ocrModel3.value = 'gemini-3.5-flash'
    }
  }
  
  loadWeatherConfig()
  syncSelectedBaselineSection1()
  syncSelectedFittingSection1()
}

function normalizeAutoUpdateSetting(value) {
  if (value === 'all') return 'all'
  return value === true
}

function getBeijingBusinessDateString(offsetDays = 0) {
  const now = new Date()
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(now).map(part => [part.type, part.value]),
  )
  const hour = Number(parts.hour || 0)
  const minute = Number(parts.minute || 0)
  const switched = hour > 6 || (hour === 6 && minute >= 30)
  const baseDate = Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day))
  const businessDate = baseDate + (switched ? 0 : -86400000) + Number(offsetDays || 0) * 86400000
  return new Date(businessDate).toISOString().slice(0, 10)
}

function syncAutoDateFields() {
  if (!isPlanDateAutoUpdateEnabled.value) return
  planStartDate.value = getBeijingBusinessDateString()
  usageCollectionDate.value = getBeijingBusinessDateString(-1)
  if (isAllDatesAutoUpdateEnabled.value) {
    showDate.value = getBeijingBusinessDateString(-1)
  }
}

function handleAutoPlanStartDateChange() {
  syncAutoDateFields()
}

const selectedBaselineSection1Name = computed(() => {
  const matched = demandEntities.value.find((item) => item.section_1_id === selectedBaselineSection1Id.value)
  return matched?.section_1_name || selectedBaselineSection1Id.value || '未选择'
})

const filteredBaselinePresets = computed(() =>
  baselinePresets.value.filter((item) => item.section_1_id === selectedBaselineSection1Id.value),
)

// 管件基准量 (Fitting Baseline) 响应式计算属性与操作方法
const selectedFittingSection1Name = computed(() => {
  if (selectedFittingSection1Id.value === 'ALL') {
    return '🌐 全部标段 (全网物料)'
  }
  const matched = demandEntities.value.find((item) => item.section_1_id === selectedFittingSection1Id.value)
  return matched?.section_1_name ? `${matched.section_1_name} (${matched.section_1_id})` : selectedFittingSection1Id.value || '未选择'
})

const filteredFittingBaselines = computed(() => {
  if (!selectedFittingSection1Id.value || selectedFittingSection1Id.value === 'ALL') {
    return fittingBaselines.value
  }
  return fittingBaselines.value.filter((item) => item.section_1_id === selectedFittingSection1Id.value)
})

const fittingGridSource = computed(() => {
  return filteredFittingBaselines.value.map((item, idx) => ({
    ...item,
    __index: idx + 1,
  }))
})

const fittingGridColumns = computed(() => [
  {
    name: '序号',
    prop: '__index',
    size: 55,
    readonly: true,
    cellClass: 'text-center text-muted',
  },
  {
    name: '标段ID (section_1_id)',
    prop: 'section_1_id',
    size: 130,
    sortable: true,
    cellClass: 'font-mono text-indigo font-bold',
  },
  {
    name: '系统类型',
    prop: 'system_type',
    size: 90,
    cellClass: 'text-center',
    sortable: true,
  },
  {
    name: '物理类别',
    prop: 'category',
    size: 100,
    sortable: true,
  },
  {
    name: '标准名称',
    prop: 'standard_name',
    size: 170,
    sortable: true,
  },
  {
    name: '型号规格',
    prop: 'model_spec',
    size: 180,
    sortable: true,
  },
  {
    name: '细分规格/子型号',
    prop: 'sub_model_spec',
    size: 130,
    sortable: true,
  },
  {
    name: '主径DN',
    prop: 'main_dn',
    size: 80,
    cellClass: 'text-right',
    sortable: true,
  },
  {
    name: '次径DN',
    prop: 'sub_dn',
    size: 80,
    cellClass: 'text-right',
    sortable: true,
  },
  {
    name: '角度(°)',
    prop: 'angle',
    size: 75,
    cellClass: 'text-right',
    sortable: true,
  },
  {
    name: '弯曲倍数',
    prop: 'bending_radius_ratio',
    size: 80,
    cellClass: 'text-right',
  },
  {
    name: '弯曲半径(m)',
    prop: 'bending_radius_m',
    size: 95,
    cellClass: 'text-right',
  },
  {
    name: '阀门型号',
    prop: 'valve_model',
    size: 110,
  },
  {
    name: '外径Φ(mm)',
    prop: 'outer_diameter',
    size: 90,
    cellClass: 'text-right',
  },
  {
    name: '壁厚(mm)',
    prop: 'wall_thickness',
    size: 80,
    cellClass: 'text-right',
  },
  {
    name: '长度(m)',
    prop: 'length_m',
    size: 80,
    cellClass: 'text-right',
  },
  {
    name: '公称压力',
    prop: 'pressure_rating',
    size: 95,
  },
  {
    name: '补偿量(mm)',
    prop: 'compensation_mm',
    size: 100,
    cellClass: 'text-right',
  },
  {
    name: '流向',
    prop: 'flow_direction',
    size: 75,
    cellClass: 'text-center',
  },
  {
    name: '单位',
    prop: 'unit',
    size: 65,
    cellClass: 'text-center',
  },
  {
    name: '设计使用量',
    prop: 'design_qty',
    size: 110,
    cellClass: 'text-right',
    sortable: true,
  },
  {
    name: '计划采购总量',
    prop: 'purchase_plan_qty',
    size: 120,
    cellClass: 'text-right',
    sortable: true,
  },
  {
    name: '原型号规格',
    prop: 'raw_model_spec',
    size: 160,
    sortable: true,
  },
  {
    name: '原名称',
    prop: 'raw_name',
    size: 150,
    sortable: true,
  },
  {
    name: '说明备注',
    prop: 'remark',
    size: 180,
  },
])

function handleFittingGridAfterEdit(event) {
  const detail = event?.detail
  if (!detail || detail.row === undefined || !detail.prop) return
  const currentSectionRows = filteredFittingBaselines.value
  const targetRow = currentSectionRows[detail.row]
  if (targetRow) {
    let val = detail.value
    const numProps = [
      'design_qty', 'purchase_plan_qty', 'main_dn', 'sub_dn', 'angle',
      'bending_radius_ratio', 'bending_radius_m', 'outer_diameter', 'wall_thickness',
      'length_m', 'compensation_mm'
    ]
    if (numProps.includes(detail.prop)) {
      val = val === '' || val == null ? null : Number(val)
    } else if (typeof val === 'string') {
      val = val.trim()
    }
    targetRow[detail.prop] = val
    if (detail.prop === 'category') {
      targetRow.fitting_type = val
    }
  }
}

function addFittingBaselineRow() {
  addFittingBaselineRows(1)
}

function addFittingBaselineRows(count = 1) {
  const isAllMode = !selectedFittingSection1Id.value || selectedFittingSection1Id.value === 'ALL'
  const fallbackSecId = demandEntities.value?.[0]?.section_1_id || 'high_lot_1'
  const defaultSecId = isAllMode ? fallbackSecId : selectedFittingSection1Id.value

  for (let i = 0; i < count; i++) {
    fittingBaselines.value.push({
      section_1_id: defaultSecId,
      system_type: '高温水',
      category: '管件',
      fitting_type: '管件',
      standard_name: '',
      model_spec: '',
      sub_model_spec: '',
      unit: '个',
      design_qty: 0,
      purchase_plan_qty: 0,
      main_dn: null,
      sub_dn: null,
      angle: null,
      bending_radius_ratio: null,
      bending_radius_m: null,
      valve_model: '',
      outer_diameter: null,
      wall_thickness: null,
      length_m: null,
      pressure_rating: '',
      compensation_mm: null,
      flow_direction: '',
      remark: '',
      __row_key: `fitting::${defaultSecId}::${Date.now()}::${Math.random()}`,
    })
  }
  setSectionMessage('fitting_baselines', 'info', `已在当前视图增加 ${count} 行数据，可直接在【标段ID】及各参数列中输入或按 Ctrl+V 批量粘贴数据。`)
}

function clearCurrentSectionFittingBaselines() {
  const isAllMode = !selectedFittingSection1Id.value || selectedFittingSection1Id.value === 'ALL'
  if (isAllMode) {
    if (!confirm(`⚠️ 危险确认：确认清空【全部标段】的所有管件基准量数据吗？点击确定后本地将全量清空，点击【保存管件基准】后同步至数据库。`)) {
      return
    }
    fittingBaselines.value = []
    setSectionMessage('fitting_baselines', 'success', `已清空全部标段的管件数据。点击【保存管件基准】后将同步至数据库。`)
  } else {
    if (!confirm(`确认清空【${selectedFittingSection1Name.value}】的所有管件基准量数据吗？`)) {
      return
    }
    fittingBaselines.value = fittingBaselines.value.filter(
      (item) => item.section_1_id !== selectedFittingSection1Id.value
    )
    setSectionMessage('fitting_baselines', 'success', `已清空【${selectedFittingSection1Name.value}】的管件数据。点击【保存管件基准】后将同步至数据库。`)
  }
}

function exportFittingBaselineTemplate() {
  const isAllMode = !selectedFittingSection1Id.value || selectedFittingSection1Id.value === 'ALL'
  const currentSecId = isAllMode ? 'high_lot_1' : selectedFittingSection1Id.value
  const headers = [
    '序号', '标段ID', '系统类型', '物理类别', '标准名称', '型号规格', '单位',
    '设计使用量', '计划采购量', '主径DN', '次径DN', '角度(°)', '弯曲半径倍数',
    '弯曲半径(m)', '阀门型号', '外径Φ(mm)', '壁厚(mm)', '长度(m)',
    '公称压力/压力等级', '补偿量(mm)', '流向/方向', '备注', '原型号规格', '原名称'
  ]
  
  let rows = []
  if (filteredFittingBaselines.value.length > 0) {
    rows = filteredFittingBaselines.value.map((item, idx) => [
      idx + 1,
      item.section_1_id || currentSecId,
      item.system_type || '高温水',
      item.category || item.fitting_type || '管件',
      item.standard_name || '',
      item.model_spec || '',
      item.unit || '个',
      item.design_qty != null ? item.design_qty : 0,
      item.purchase_plan_qty != null ? item.purchase_plan_qty : 0,
      item.main_dn,
      item.sub_dn,
      item.angle,
      item.bending_radius_ratio,
      item.bending_radius_m,
      item.valve_model || '',
      item.outer_diameter,
      item.wall_thickness,
      item.length_m,
      item.pressure_rating || '',
      item.compensation_mm,
      item.flow_direction || '',
      item.remark || '',
      item.raw_model_spec || '',
      item.raw_name || '',
    ])
  } else {
    rows = [
      [1, currentSecId, '高温水', '弯头', '塑套钢预制保温弯头', '90° DN1000 R=1.5DN', '个', 24, 24, 1000, null, 90, 1.5, null, '', null, null, null, '', null, '', '', '90° DN1000 R=1.5DN', '塑套钢预制保温弯头'],
      [2, currentSecId, '高温水', '三通', '塑套钢预制保温跨越三通', 'DN1000/DN600', '个', 8, 8, 1000, 600, null, null, null, '', null, null, null, '', null, '', '', 'DN1000/DN600', '塑套钢预制保温跨越三通'],
    ]
  }

  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '标准化数据')
  const fileNameSuffix = isAllMode ? '全部标段' : selectedFittingSection1Id.value
  XLSX.writeFile(wb, `管件与物料基准量_${fileNameSuffix}.xlsx`)
}

function triggerFittingExcelUpload() {
  if (fittingExcelFileInput.value) {
    fittingExcelFileInput.value.value = ''
    fittingExcelFileInput.value.click()
  }
}

function handleFittingExcelFile(event) {
  const file = event?.target?.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheetName = workbook.SheetNames[0]
      const worksheet = workbook.Sheets[firstSheetName]
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 })

      if (!jsonData || jsonData.length < 2) {
        throw new Error('Excel 文件内容为空或格式不正确')
      }

      const headers = (jsonData[0] || []).map((h) => String(h || '').trim())
      const isFullStandardFormat = headers.includes('物理类别') || headers.includes('标准名称') || headers.includes('主径DN')
      const colMap = {}
      headers.forEach((h, idx) => {
        if (h) colMap[h] = idx
      })

      const dataRows = jsonData.slice(1)
      let importedCount = 0
      const isAllMode = !selectedFittingSection1Id.value || selectedFittingSection1Id.value === 'ALL'
      const fallbackSecId = demandEntities.value?.[0]?.section_1_id || 'high_lot_1'
      const currentSecId = isAllMode ? fallbackSecId : selectedFittingSection1Id.value

      const parsedItems = []
      for (const row of dataRows) {
        if (!row || !row.length) continue

        let item = {}
        if (isFullStandardFormat) {
          const getVal = (colName) => {
            const idx = colMap[colName]
            return idx !== undefined ? row[idx] : undefined
          }
          const rawSecVal = String(getVal('标段ID') || getVal('需求主体ID') || getVal('标段') || '').trim()
          let secVal = rawSecVal || currentSecId
          if (rawSecVal) {
            const matchedEntity = demandEntities.value.find(
              (d) => d.section_1_id === rawSecVal || d.section_1_name === rawSecVal || d.code === rawSecVal
            )
            if (matchedEntity) {
              secVal = matchedEntity.section_1_id
            }
          }

          const mSpec = String(getVal('型号规格') || '').trim()
          if (!mSpec) continue

          const cleanNum = (v) => (v === '' || v == null || isNaN(Number(v)) ? null : Number(v))

          item = {
            section_1_id: secVal,
            system_type: String(getVal('系统类型') || '高温水').trim(),
            category: String(getVal('物理类别') || '管件').trim(),
            fitting_type: String(getVal('物理类别') || '管件').trim(),
            standard_name: String(getVal('标准名称') || '').trim(),
            model_spec: mSpec,
            sub_model_spec: String(getVal('子型号') || getVal('子型号规格') || '').trim(),
            unit: String(getVal('单位') || '个').trim() || '个',
            design_qty: cleanNum(getVal('设计使用量')) || 0,
            purchase_plan_qty: cleanNum(getVal('计划采购量')) || 0,
            main_dn: cleanNum(getVal('主径DN')),
            sub_dn: cleanNum(getVal('次径DN')),
            angle: cleanNum(getVal('角度(°)') ?? getVal('角度')),
            bending_radius_ratio: cleanNum(getVal('弯曲半径倍数')),
            bending_radius_m: cleanNum(getVal('弯曲半径(m)') ?? getVal('弯曲半径')),
            valve_model: String(getVal('阀门型号') || '').trim(),
            outer_diameter: cleanNum(getVal('外径Φ(mm)') ?? getVal('外径')),
            wall_thickness: cleanNum(getVal('壁厚(mm)') ?? getVal('壁厚')),
            length_m: cleanNum(getVal('长度(m)') ?? getVal('长度')),
            pressure_rating: String(getVal('公称压力/压力等级') ?? getVal('公称压力') ?? '').trim(),
            compensation_mm: cleanNum(getVal('补偿量(mm)') ?? getVal('补偿量')),
            flow_direction: String(getVal('流向/方向') ?? getVal('流向') ?? '').trim(),
            raw_model_spec: String(getVal('原型号规格') || getVal('原始型号规格') || '').trim(),
            raw_name: String(getVal('原名称') || getVal('原始名称') || '').trim(),
            remark: String(getVal('备注') || '').trim(),
          }
        } else {
          // 兼容旧版简单 8 列格式
          let secVal = String(row[0] || '').trim()
          let fType = String(row[1] || '').trim()
          let mSpec = String(row[2] || '').trim()
          let subSpec = String(row[3] || '').trim()
          let unit = String(row[4] || '个').trim() || '个'
          let dQty = Number(row[5] || 0)
          let pQty = Number(row[6] || 0)
          let remark = String(row[7] || '').trim()

          if (!fType && !mSpec) continue
          item = {
            section_1_id: secVal || currentSecId,
            system_type: '高温水',
            category: fType || '管件',
            fitting_type: fType || '管件',
            standard_name: '',
            model_spec: mSpec,
            sub_model_spec: subSpec,
            unit: unit,
            design_qty: isNaN(dQty) ? 0 : dQty,
            purchase_plan_qty: isNaN(pQty) ? 0 : pQty,
            remark: remark,
          }
        }

        item.__row_key = `fitting::${item.section_1_id}::${item.system_type}::${item.standard_name}::${item.model_spec}::${Date.now()}::${importedCount}`
        parsedItems.push(item)
        importedCount++
      }

      if (!parsedItems.length) {
        throw new Error('未从 Excel 中读取到有效的管件型号数据')
      }

      // 如果是全量导入或包含了多个标段，追加或更新到本地列表
      fittingBaselines.value.push(...parsedItems)
      setSectionMessage('fitting_baselines', 'success', `🎉 成功从 Excel 导入 ${importedCount} 条标准化物料基准量！请核对后点击【保存管件基准】。`)
    } catch (err) {
      setSectionMessage('fitting_baselines', 'error', `导入 Excel 失败: ${err?.message || err}`)
    }
  }

  reader.readAsArrayBuffer(file)
}

const submissionStatusRows = computed(() => {
  const latestBySection1Id = new Map(
    latestSubmissions.value
      .filter((item) => item.section_1_id)
      .map((item) => [String(item.section_1_id), item]),
  )
  return demandEntities.value.map((section1) => {
    const section1Id = String(section1.section_1_id || '')
    const latest = latestBySection1Id.get(section1Id) || {}
    const dataSubmitDate = String(latest.data_submit_date || '')
    return {
      section_1_id: section1Id,
      section_1_name: section1.section_1_name || section1Id,
      data_submit_date: dataSubmitDate,
      submitted_at: latest.submitted_at || '',
      submitted_by: latest.submitted_by || '',
      is_submitted: Boolean(dataSubmitDate && planStartDate.value && dataSubmitDate === planStartDate.value),
    }
  })
})

const submittedSection1Count = computed(() => submissionStatusRows.value.filter((item) => item.is_submitted).length)
const pendingSection1Count = computed(() => submissionStatusRows.value.filter((item) => !item.is_submitted).length)

function buildSectionPayload(section) {
  if (section === 'show_date') {
    return showDate.value || ''
  }
  if (section === 'plan_start_date') {
    return planStartDate.value || ''
  }
  if (section === 'auto_update_plan_start_date') {
    return normalizeAutoUpdateSetting(autoUpdatePlanStartDate.value)
  }
  if (section === 'plan_editable_days') {
    return Number(planEditableDays.value ?? 3)
  }
  if (section === 'strict_planning_flow_control') {
    return Boolean(strictPlanningFlowControl.value)
  }
  if (section === 'supply_entities') {
    return supplyEntities.value.map((item) => ({
      entity_id: item.entity_id || '',
      code: String(item.code || '').trim().toUpperCase(),
      entity_name: item.entity_name || '',
      contact_name: item.contact_name || '',
      contact_phone: item.contact_phone || '',
      section_1_ids: textToList(item.section_1_ids_text),
      is_custom: Boolean(item.is_custom),
    }))
  }
  if (section === 'demand_entities') {
    return demandEntities.value.map((item) => ({
      section_1_id: item.section_1_id || '',
      code: String(item.code || '').trim().toUpperCase(),
      section_1_name: item.section_1_name || '',
      section_2: item.section_2 || '',
      section_3: item.section_3 || '',
      construction_status: item.construction_status || '',
    }))
  }
  if (section === 'pipe_models') {
    return pipeModels.value.map((item) => {
      const normalizedCode = normalizePipeModelCode(item.pipe_model_id || item.pipe_model_name)
      return {
        pipe_model_id: normalizedCode,
        pipe_model_name: normalizedCode,
        unit: String(item.unit || '米').trim() || '米',
      }
    })
  }
  if (section === 'production_capacities') {
    return productionCapacities.value.map((item) => ({
      supply_entity_name: item.supply_entity_name || '',
      pipe_model_name: normalizePipeModelCode(item.pipe_model_name),
      max_daily_output_qty: Number(item.max_daily_output_qty || 0),
      remark: item.remark || '',
    }))
  }
  if (section === 'manager_assignments') {
    return managerAssignments.value.map((item) => ({
      manager_id: item.manager_id || '',
      manager_name: item.manager_name || '',
      contact_phone: item.contact_phone || '',
      section_1_ids: textToList(item.section_1_ids_text),
    }))
  }
  if (section === 'construction_units') {
    return constructionUnits.value.map((item) => ({
      unit_id: item.unit_id || '',
      unit_name: item.unit_name || '',
      contact_name: item.contact_name || '',
      contact_phone: item.contact_phone || '',
      section_1_ids: textToList(item.section_1_ids_text),
    }))
  }
  if (section === 'warehouse_keepers') {
    return warehouseKeepers.value.map((item) => ({
      keeper_id: item.keeper_id || '',
      keeper_name: item.keeper_name || '',
      contact_phone: item.contact_phone || '',
      section_1_ids: textToList(item.section_1_ids_text),
    }))
  }
  if (section === 'baseline_presets') {
    return baselinePresets.value.map((item) => ({
      section_1_id: item.section_1_id || '',
      pipe_model_id: normalizePipeModelCode(item.pipe_model_id),
      design_qty: Number(item.design_qty || 0),
      purchase_plan_qty: Number(item.purchase_plan_qty || 0),
      remark: item.remark || '',
    }))
  }
  if (section === 'fitting_baselines') {
    return fittingBaselines.value.map((item) => ({
      section_1_id: String(item.section_1_id || '').trim(),
      system_type: String(item.system_type || '高温水').trim(),
      category: String(item.category || item.fitting_type || '管件').trim(),
      fitting_type: String(item.category || item.fitting_type || '管件').trim(),
      standard_name: String(item.standard_name || '').trim(),
      model_spec: String(item.model_spec || '').trim(),
      sub_model_spec: String(item.sub_model_spec || '').trim(),
      unit: String(item.unit || '个').trim() || '个',
      design_qty: Number(item.design_qty || 0),
      purchase_plan_qty: Number(item.purchase_plan_qty || 0),
      main_dn: item.main_dn != null ? Number(item.main_dn) : null,
      sub_dn: item.sub_dn != null ? Number(item.sub_dn) : null,
      angle: item.angle != null ? Number(item.angle) : null,
      bending_radius_ratio: item.bending_radius_ratio != null ? Number(item.bending_radius_ratio) : null,
      bending_radius_m: item.bending_radius_m != null ? Number(item.bending_radius_m) : null,
      valve_model: String(item.valve_model || '').trim(),
      outer_diameter: item.outer_diameter != null ? Number(item.outer_diameter) : null,
      wall_thickness: item.wall_thickness != null ? Number(item.wall_thickness) : null,
      length_m: item.length_m != null ? Number(item.length_m) : null,
      pressure_rating: String(item.pressure_rating || '').trim(),
      compensation_mm: item.compensation_mm != null ? Number(item.compensation_mm) : null,
      flow_direction: String(item.flow_direction || '').trim(),
      raw_model_spec: String(item.raw_model_spec || '').trim(),
      raw_name: String(item.raw_name || '').trim(),
      remark: String(item.remark || '').trim(),
    }))
  }
  if (section === 'weather_api_url') {
    return weatherApiUrl.value || ''
  }
  if (section === 'amap_config') {
    return {
      api_key: amapApiKey.value || '',
      security_code: amapSecurityCode.value || '',
    }
  }
  if (section === 'ocr_tool_config') {
    const m1 = String(ocrModel1.value || '').trim() || 'gemini-3.5-flash-lite'
    const m2 = String(ocrModel2.value || '').trim()
    const m3 = String(ocrModel3.value || '').trim()
    const fallbacks = [m2, m3].filter(Boolean)
    return {
      model: m1,
      fallback_models: fallbacks,
      api_key: ocrApiKey.value || '',
    }
  }
  if (section === 'fitting_config') {
    return {
      allowed_units: textToList(fittingAllowedUnitsText.value),
      standard_types: textToList(fittingStandardTypesText.value),
    }
  }
  return null
}

const configPreviewText = computed(() =>
  JSON.stringify(
    {
      show_date: showDate.value || '',
      usage_collection_date: usageCollectionDate.value || '',
      plan_start_date: planStartDate.value || '',
      auto_update_plan_start_date: normalizeAutoUpdateSetting(autoUpdatePlanStartDate.value),
      plan_editable_days: Number(planEditableDays.value ?? 3),
      strict_planning_flow_control: Boolean(strictPlanningFlowControl.value),
      fitting_config: buildSectionPayload('fitting_config'),
      supply_entities: buildSectionPayload('supply_entities'),
      demand_entities: buildSectionPayload('demand_entities'),
      pipe_models: buildSectionPayload('pipe_models'),
      production_capacities: buildSectionPayload('production_capacities'),
      manager_assignments: buildSectionPayload('manager_assignments'),
      construction_units: buildSectionPayload('construction_units'),
      warehouse_keepers: buildSectionPayload('warehouse_keepers'),
      baseline_presets: buildSectionPayload('baseline_presets'),
      weather_api_url: weatherApiUrl.value || '',
      amap_config: buildSectionPayload('amap_config'),
      ocr_tool_config: buildSectionPayload('ocr_tool_config'),
    },
    null,
    2,
  ),
)

// 切换到原始 JSON Tab 时，自动将当前解析数据格式化覆盖可编辑值
watch(activeTab, (newTab) => {
  if (newTab === 'json') {
    jsonEditVal.value = configPreviewText.value
    jsonErrorMessage.value = '' // 切换 Tab 时自动清空历史校验错误
  }
})

// 实时监听 JSON 编辑器的内容变化，进行即时语法校验，让用户增删字符时瞬间看到红边框和警示栏
watch(jsonEditVal, (newVal) => {
  if (activeTab.value !== 'json') return
  if (!newVal || !newVal.trim()) {
    jsonErrorMessage.value = ''
    return
  }
  try {
    JSON.parse(newVal)
    jsonErrorMessage.value = '' // 解析成功，即时清空错误
  } catch (error) {
    // 实时显示详细的 JSON 语法错误，帮助用户精确定位
    jsonErrorMessage.value = `🚨 JSON 语法错误：${error.message}！请检查标点、逗号或括号是否闭环！`
  }
})

function resetJsonEditVal() {
  jsonEditVal.value = configPreviewText.value
  jsonErrorMessage.value = ''
}

async function handleSaveRawJson() {
  clearGlobalMessage()
  jsonErrorMessage.value = ''
  
  let parsedConfig = null
  try {
    parsedConfig = JSON.parse(jsonEditVal.value)
  } catch (error) {
    // 语法错误拦截，并弹出高雅提示
    jsonErrorMessage.value = `🚨 JSON 格式解析错误：${error.message}！请检查标点、逗号或括号是否闭环！`
    return
  }
  
  savingJson.value = true
  try {
    await saveTubeGlobalManagementConfig(PROJECT_KEY, { config: parsedConfig })
    setGlobalMessage('success', '🎉 原始整个 JSON 配置已成功整体保存！已自动同步刷新各版块状态。')
    jsonErrorMessage.value = '' // 保存成功，彻底清空
    // 自动重载配置
    await loadConfig()
  } catch (error) {
    console.error(error)
    jsonErrorMessage.value = error instanceof Error ? error.message : '保存原始配置数据失败'
  } finally {
    savingJson.value = false
  }
}

async function loadConfig() {
  clearGlobalMessage()
  try {
    const response = await getTubeGlobalManagementConfig(PROJECT_KEY)
    const config = response.config || {}
    submissionStatusPath.value = response.submission_status_path || ''
    latestSubmissions.value = normalizeSubmissionRows(response.submission_status?.latest_submissions || [])
    historySubmissions.value = normalizeSubmissionRows(response.submission_status?.history_submissions || [])
    applyConfig(config)
    await loadWeatherConfig()

    if (response.amap_config_decrypted) {
      amapApiKey.value = response.amap_config_decrypted.api_key || ''
      amapSecurityCode.value = response.amap_config_decrypted.security_code || ''
    }

    if (response.ocr_tool_config_decrypted) {
      const dec = response.ocr_tool_config_decrypted
      ocrModel1.value = dec.model || 'gemini-3.5-flash-lite'
      if (Array.isArray(dec.fallback_models)) {
        ocrModel2.value = dec.fallback_models[0] || ''
        ocrModel3.value = dec.fallback_models[1] || ''
      }
      ocrApiKey.value = dec.api_key || ''
    }

    if (response.show_date) {
      showDate.value = response.show_date
    }
    if (response.usage_collection_date) {
      usageCollectionDate.value = response.usage_collection_date
    }
    if (response.plan_start_date) {
      planStartDate.value = response.plan_start_date
    }
    
    // 如果当前已经是原始编辑 Tab，同步一下内容
    if (activeTab.value === 'json') {
      jsonEditVal.value = configPreviewText.value
    }
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
    applyConfig(response.config || {})
    if (response.ocr_tool_config_decrypted) {
      const dec = response.ocr_tool_config_decrypted
      ocrModel1.value = dec.model || 'gemini-3.5-flash-lite'
      if (Array.isArray(dec.fallback_models)) {
        ocrModel2.value = dec.fallback_models[0] || ''
        ocrModel3.value = dec.fallback_models[1] || ''
      }
      ocrApiKey.value = dec.api_key || ''
    }
    if (response.amap_config_decrypted) {
      amapApiKey.value = response.amap_config_decrypted.api_key || ''
      amapSecurityCode.value = response.amap_config_decrypted.security_code || ''
    }
    if (response.show_date) {
      showDate.value = response.show_date
    }
    if (response.usage_collection_date) {
      usageCollectionDate.value = response.usage_collection_date
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
    syncAutoDateFields()
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'show_date',
      data: showDate.value || '',
    })
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'usage_collection_date',
      data: usageCollectionDate.value || '',
    })
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'plan_start_date',
      data: planStartDate.value || '',
    })
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'auto_update_plan_start_date',
      data: normalizeAutoUpdateSetting(autoUpdatePlanStartDate.value),
    })
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'strict_planning_flow_control',
      data: Boolean(strictPlanningFlowControl.value),
    })
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'auto_receive_timeout_hours',
      data: autoReceiveTimeoutHours.value !== null && autoReceiveTimeoutHours.value !== '' ? Number(autoReceiveTimeoutHours.value) : 12,
    })
    const response = await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'plan_editable_days',
      data: Number(planEditableDays.value ?? 3),
    })
    applyConfig(response.config || {})
    if (response.show_date) {
      showDate.value = response.show_date
    }
    if (response.usage_collection_date) {
      usageCollectionDate.value = response.usage_collection_date
    }
    if (response.plan_start_date) {
      planStartDate.value = response.plan_start_date
    }
    autoUpdatePlanStartDate.value = normalizeAutoUpdateSetting(response.config?.auto_update_plan_start_date)
    if (response.plan_editable_days !== undefined) {
      planEditableDays.value = Number(response.plan_editable_days ?? 3)
    }
    if (response.config?.auto_receive_timeout_hours !== undefined) {
      autoReceiveTimeoutHours.value = Number(response.config.auto_receive_timeout_hours)
    }
    setSectionMessage('core_dates', 'success', '核心参数已保存。')
  } catch (error) {
    setSectionMessage('core_dates', 'error', error?.message || '保存失败')
  } finally {
    setSaving('core_dates', false)
  }
}

function removeRow(targetRef, index) {
  if (Array.isArray(targetRef)) {
    targetRef.splice(index, 1)
    return
  }
  if (targetRef && Array.isArray(targetRef.value)) {
    targetRef.value.splice(index, 1)
  }
}

const normalSupplyEntitiesCount = computed(() => {
  return supplyEntities.value.filter((item) => !item.is_custom).length
})

const customSupplyEntitiesCount = computed(() => {
  return supplyEntities.value.filter((item) => item.is_custom).length
})

const customSupplyEntitiesList = computed(() => {
  return supplyEntities.value.filter((item) => item.is_custom)
})

const removeCustomEntity = (item) => {
  const idx = supplyEntities.value.indexOf(item)
  if (idx !== -1) {
    supplyEntities.value.splice(idx, 1)
  }
}

function addSupplyEntity() {
  supplyEntities.value.push({
    entity_id: '',
    code: '',
    entity_name: '',
    section_1_ids_text: '',
    contact_name: '',
    contact_phone: '',
  })
}

function addDemandEntity() {
  demandEntities.value.push({
    section_1_id: '',
    code: '',
    section_1_name: '',
    section_2: '',
    section_3: '',
    construction_status: '',
  })
}

function addPipeModel() {
  pipeModels.value.push({
    pipe_model_id: '',
    pipe_model_name: '',
    unit: '米',
  })
}

function addManagerAssignment() {
  managerAssignments.value.push({
    manager_id: '',
    manager_name: '',
    contact_phone: '',
    section_1_ids_text: '',
  })
}

function defaultCapacityByPipeModel(pipeModelCode) {
  const bucket = resolvePipeModelBucket(pipeModelCode)
  if (bucket === 'medium') return 420
  if (bucket === 'large') return 300
  return 600
}

function addProductionCapacity() {
  const firstEntity = supplyEntities.value[0] || null
  const firstModel = pipeModels.value[0] || null
  productionCapacities.value.push({
    supply_entity_name: firstEntity?.entity_name || '',
    pipe_model_name: firstModel?.pipe_model_name || '',
    max_daily_output_qty: defaultCapacityByPipeModel(firstModel?.pipe_model_id),
    remark: '',
  })
}

function addConstructionUnit() {
  constructionUnits.value.push({
    unit_id: '',
    unit_name: '',
    contact_name: '',
    contact_phone: '',
    section_1_ids_text: '',
  })
}

function addWarehouseKeeper() {
  warehouseKeepers.value.push({
    keeper_id: '',
    keeper_name: '',
    contact_phone: '',
    section_1_ids_text: '',
  })
}

function parsePipeModelDiameters(modelCode) {
  if (!modelCode) return { main: 0, outer: 0 }
  const str = String(modelCode).trim()
  const parts = str.split('/')
  const leftStr = parts[0] || ''
  const rightStr = parts[1] || ''
  const leftMatch = leftStr.match(/(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)/i)
  const rightMatch = rightStr.match(/(?:[ΦφDN])?\s*(\d+(?:\.\d+)?)/i)
  const main = leftMatch ? parseFloat(leftMatch[1]) || 0 : 0
  const outer = rightMatch ? parseFloat(rightMatch[1]) || 0 : 0
  return { main, outer }
}

function sortPipeModelsByDiameterDesc(modelList) {
  return [...modelList].sort((a, b) => {
    const codeA = a.pipe_model_id || a.pipe_model_name
    const codeB = b.pipe_model_id || b.pipe_model_name
    const dA = parsePipeModelDiameters(codeA)
    const dB = parsePipeModelDiameters(codeB)
    if (dB.main !== dA.main) {
      return dB.main - dA.main
    }
    if (dB.outer !== dA.outer) {
      return dB.outer - dA.outer
    }
    return String(codeA || '').localeCompare(String(codeB || ''))
  })
}

const selectableBaselinePipeModels = computed(() => {
  const modelMap = new Map()
  pipeModels.value.forEach((m) => {
    if (m && m.pipe_model_id) modelMap.set(m.pipe_model_id, m)
  })
  baselinePresets.value.forEach((b) => {
    if (b && b.pipe_model_id && !modelMap.has(b.pipe_model_id)) {
      modelMap.set(b.pipe_model_id, {
        pipe_model_id: b.pipe_model_id,
        pipe_model_name: b.pipe_model_id,
        unit: '米',
      })
    }
  })
  return sortPipeModelsByDiameterDesc(Array.from(modelMap.values()))
})

function resolvePipeModelById(pipeModelId) {
  const normalizedCode = normalizePipeModelCode(pipeModelId)
  return selectableBaselinePipeModels.value.find((item) => normalizePipeModelCode(item.pipe_model_id) === normalizedCode) || null
}

function syncBaselinePipeModelName(row) {
  const matched = resolvePipeModelById(row.pipe_model_id)
  if (!matched) return
  row.pipe_model_name = matched.pipe_model_name || matched.pipe_model_id
  row.pipe_model_id = matched.pipe_model_id
  if (!row.design_qty) {
    row.design_qty = defaultQtyByPipeModel(matched.pipe_model_id)
  }
  if (!row.purchase_plan_qty) {
    row.purchase_plan_qty = defaultQtyByPipeModel(matched.pipe_model_id)
  }
  if (!row.remark) {
    row.remark = defaultRemarkByPipeModel(matched.pipe_model_id)
  }
}

function addBaselinePreset() {
  const currentSection1 = demandEntities.value.find((item) => item.section_1_id === selectedBaselineSection1Id.value)
  const usedModelIds = new Set(
    baselinePresets.value
      .filter((item) => item.section_1_id === selectedBaselineSection1Id.value)
      .map((item) => item.pipe_model_id)
  )
  const unusedModel = selectableBaselinePipeModels.value.find((model) => model.pipe_model_id && !usedModelIds.has(model.pipe_model_id)) || selectableBaselinePipeModels.value[0] || null

  baselinePresets.value.push({
    __row_key: `new::${Date.now()}`,
    section_1_id: selectedBaselineSection1Id.value || '',
    pipe_model_id: unusedModel?.pipe_model_id || '',
    design_qty: defaultQtyByPipeModel(unusedModel?.pipe_model_id),
    purchase_plan_qty: defaultQtyByPipeModel(unusedModel?.pipe_model_id),
    remark: defaultRemarkByPipeModel(unusedModel?.pipe_model_id),
  })
  rebuildBaselineRowKeys()
}

function removeBaselinePreset(rowKey) {
  baselinePresets.value = baselinePresets.value.filter((item) => item.__row_key !== rowKey)
  rebuildBaselineRowKeys()
}

watch(demandEntities, () => {
  syncSelectedBaselineSection1()
}, { deep: true, immediate: true })

watch(activeTab, (newTab) => {
  if (newTab === 'baseline') {
    syncSelectedBaselineSection1()
  }
})

onMounted(async () => {
  await loadConfig()
  syncSelectedBaselineSection1()
  if (activeTab.value === 'submissions') {
    fetchSubmissionLogs(1)
  }
})

// ==================== 📋 业务操作记录 JS 业务逻辑 ====================

function handleGoToUserDirectory(operator) {
  if (!operator) return
  navigateToUserInDirectory(router, operator, PROJECT_KEY)
}

function onSubmissionCategoryChange() {
  const cat = submissionFilters.value.category
  if (cat === 'submission') {
    if (submissionFilters.value.entityType === 'query') {
      submissionFilters.value.entityType = ''
    }
    const queryActions = [
      'QUERY_DAILY_FLOW',
      'QUERY_BASELINE_PROGRESS',
      'QUERY_MATERIAL_PRICES',
      'QUERY_SUPPLIER_LEDGER',
      'QUERY_ENTITY_DIRECTORY',
      'OCR_DELIVERY_BILL',
    ]
    if (queryActions.includes(submissionFilters.value.actionType)) {
      submissionFilters.value.actionType = ''
    }
  } else if (cat === 'query') {
    submissionFilters.value.entityType = 'query'
    const submissionActions = [
      'SAVE_PLAN', 'SUBMIT_USAGE', 'SUBMIT_STATUS',
      'CONFIRM_ARRIVAL', 'CONFIRM_CONSTRUCTION', 'CREATE_DELIVERY',
      'CREATE_DELIVERY_BATCH', 'CANCEL_DELIVERY', 'CONFIRM_WAREHOUSE',
      'SUBMIT_FITTING_DELIVERY', 'DELETE_FITTING_DELIVERY',
    ]
    if (submissionActions.includes(submissionFilters.value.actionType)) {
      submissionFilters.value.actionType = ''
    }
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
    const res = await getTubeSubmissionLogs(PROJECT_KEY, {
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
    demand24hCount.value = res.demand_24h_count || 0
    supply24hCount.value = res.supply_24h_count || 0
    query24hCount.value = res.query_24h_count || 0
  } catch (error) {
    console.error('加载业务操作记录失败:', error)
  } finally {
    submissionLoading.value = false
  }
}

function isRecent24h(isoString) {
  if (!isoString) return false
  const t = new Date(isoString).getTime()
  return (Date.now() - t) <= 24 * 60 * 60 * 1000
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

/**
 * 🏷️ 智能解析并提取日志中发货对应的需求主体/标段名称
 */
function getSection1NameFromLog(log) {
  if (!log) return ''
  
  // 1. 优先从结构化快照中解析 section_1_id
  const payload = log.after_value || log.before_value || {}
  let rawSecId = payload.section_1_id || payload.section1_id || payload.section_id || ''
  if (!rawSecId && Array.isArray(payload.items) && payload.items.length > 0) {
    rawSecId = payload.items[0].section_1_id || ''
  }
  
  if (rawSecId) {
    const matched = demandEntities.value.find(
      e => String(e.section_1_id || '').trim() === String(rawSecId).trim() ||
           String(e.code || '').trim() === String(rawSecId).trim()
    )
    if (matched && matched.section_1_name) {
      return matched.section_1_name
    }
    return rawSecId
  }

  // 2. 从 action_desc 中正则提取“需求主体【...】”或“接收标段: ...”
  const desc = String(log.action_desc || '')
  const matchBracket = desc.match(/需求主体【(.*?)】/)
  if (matchBracket && matchBracket[1]) {
    return matchBracket[1]
  }
  const matchColon = desc.match(/接收标段:\s*([^\)）]+)/)
  if (matchColon && matchColon[1]) {
    const matched = demandEntities.value.find(
      e => String(e.section_1_id || '').trim() === String(matchColon[1]).trim()
    )
    return matched?.section_1_name || matchColon[1]
  }

  return ''
}

/**
 * 🧼 提取清洗后的详情说明文字（避免与需求主体 Badge 重复）
 */
function getCleanActionDesc(log) {
  if (!log || !log.action_desc) return '无详情说明'
  let desc = String(log.action_desc)
  // 如果提取出了主体徽章，可将文本内部重复的 "需求主体【...】，" 清洗掉
  desc = desc.replace(/需求主体【.*?】[，,]?\s*/g, '')
  return desc
}

// ==================== 📍 IP 归属地与网络运营商气泡弹窗逻辑 ====================

const ipPopoverState = ref({
  visible: false,
  x: 0,
  y: 0,
  ip: '',
  loading: false,
  error: '',
  data: null,
})

const ipLocationLocalCache = ref({})
const ipCopied = ref(false)

async function triggerIpPopover(event, ip) {
  if (!ip) return
  event.stopPropagation()

  // 计算点击元素在屏幕上的位置
  const rect = event.currentTarget.getBoundingClientRect()
  
  const popoverWidth = 280
  let left = rect.left
  if (left + popoverWidth > window.innerWidth - 20) {
    left = window.innerWidth - popoverWidth - 20
  }
  if (left < 20) left = 20

  let top = rect.bottom + 8
  if (top + 180 > window.innerHeight) {
    top = Math.max(10, rect.top - 180)
  }

  ipPopoverState.value = {
    visible: true,
    x: left,
    y: top,
    ip: ip,
    loading: false,
    error: '',
    data: null,
  }

  // 命中本地缓存直接展示
  if (ipLocationLocalCache.value[ip]) {
    ipPopoverState.value.data = ipLocationLocalCache.value[ip]
    return
  }

  ipPopoverState.value.loading = true
  try {
    const res = await getTubeIpLocation(PROJECT_KEY, ip)
    ipPopoverState.value.data = res
    ipLocationLocalCache.value[ip] = res
  } catch (err) {
    console.error('查询 IP 归属地失败:', err)
    ipPopoverState.value.error = 'IP 归属地查询失败或网络超时'
  } finally {
    ipPopoverState.value.loading = false
  }
}

function closeIpPopover() {
  ipPopoverState.value.visible = false
}

async function copyIpAddress(ip) {
  if (!ip) return
  try {
    await navigator.clipboard.writeText(ip)
    ipCopied.value = true
    setTimeout(() => {
      ipCopied.value = false
    }, 1800)
  } catch (e) {
    console.warn('复制 IP 失败:', e)
  }
}

// ==================== 📜 操作审计日志 JS 业务逻辑 ====================

const SENSITIVE_ACTION_SET = new Set([
  'SUPER_UPDATE_DELIVERY',
  'SUPER_UPDATE_FITTING_DELIVERY',
  'UPDATE_CONFIG',
  'CANCEL_DELIVERY',
  'CANCEL_FITTING_DELIVERY',
  'DELETE_FITTING_DELIVERY',
])

function isSensitiveAction(actionType) {
  return SENSITIVE_ACTION_SET.has(String(actionType || ''))
}

const FIELD_LABEL_MAP = {
  show_date: '展示业务日期',
  usage_collection_date: '消耗归集日期',
  plan_start_date: '三日计划起始日',
  auto_update_plan_start_date: '计划日自动顺延',
  plan_editable_days: '计划可编辑天数',
  strict_planning_flow_control: '严格计划流控',
  supply_entities: '供给侧主体列表',
  demand_entities: '需求侧主体列表',
  pipe_models: '管型规格定义',
  production_capacities: '厂家日产能预设',
  manager_assignments: '人员管辖映射',
  construction_units: '施工单位映射',
  warehouse_keepers: '库管人员映射',
  baseline_presets: '基准设计量预设',
  weather_api_url: '气象接口 URL',
  weather_provider: '气象数据源模式',
  amap_config: '高德 API 密钥配置',
  fitting_config: '管件流转规则配置',
  delivery_id: '发货单号 (ID)',
  order_no: '订单号',
  shipment_no: '物流运单号',
  pipe_model_id: '管型规格 ID',
  pipe_model_name: '管型名称',
  unit: '计量单位',
  delivery_qty: '发货数量',
  arrived_qty: '到货数量',
  construction_received_qty: '施工接收数量',
  warehouse_confirmed_qty: '库管确认数量',
  license_plate: '运输车牌号',
  driver_name: '司机姓名',
  driver_phone: '司机联系电话',
  operator: '操作人账号',
  operator_group: '操作人角色组',
  action_type: '操作动作类型',
  action_desc: '操作描述说明',
  max_daily_output_qty: '日最大产能',
  design_qty: '设计基准量',
  purchase_plan_qty: '采购计划量',
  remark: '备注批注',
  diff_note: '接收差异说明',
  diff_status: '差异审批状态',
  section_1_id: '需求侧换热站 ID',
  section_1_name: '换热站名称',
  section_2_id: '施工标段 ID',
  factory_id: '生产厂商 ID',
  delivery_date: '发货日期',
  shipped_at: '实际发货时间',
  arrived_at: '实际到货时间',
  received_at: '施工接收时间',
  warehouse_at: '库管确认时间',
}

async function fetchAuditLogs(page = 1) {
  auditLoading.value = true
  auditPage.value = page
  try {
    const res = await getTubeAuditLogs(PROJECT_KEY, {
      actionType: auditFilters.value.actionType,
      operator: auditFilters.value.operator,
      resourceId: auditFilters.value.resourceId,
      keyword: auditFilters.value.keyword,
      isSensitive: auditFilters.value.isSensitive,
      startDate: auditFilters.value.startDate,
      endDate: auditFilters.value.endDate,
      page: auditPage.value,
      limit: auditLimit.value,
    })
    auditLogs.value = res.rows || []
    auditTotal.value = res.total || 0
    auditLatestTime.value = res.latest_operated_at || null
    auditTodayCount.value = res.today_count || 0
    auditSensitiveCount.value = res.sensitive_count || 0
    auditOperatorCount.value = res.operator_count || 0
  } catch (error) {
    console.error('加载操作审计日志失败:', error)
  } finally {
    auditLoading.value = false
  }
}

function resetAuditFilters() {
  auditFilters.value = {
    actionType: '',
    operator: '',
    resourceId: '',
    keyword: '',
    isSensitive: false,
    startDate: '',
    endDate: '',
  }
  fetchAuditLogs(1)
}

function toggleSensitiveFilter() {
  auditFilters.value.isSensitive = !auditFilters.value.isSensitive
  fetchAuditLogs(1)
}

async function copyResourceId(id) {
  if (!id) return
  try {
    await navigator.clipboard.writeText(String(id))
    auditCopiedId.value = id
    setTimeout(() => {
      if (auditCopiedId.value === id) {
        auditCopiedId.value = null
      }
    }, 1500)
  } catch (e) {
    console.error('复制单号失败:', e)
  }
}

function filterByResourceId(id) {
  if (!id) return
  auditFilters.value.resourceId = id
  fetchAuditLogs(1)
}

function handleAuditJumpPage() {
  const maxPage = Math.ceil(auditTotal.value / auditLimit.value) || 1
  let page = parseInt(auditJumpPage.value, 10)
  if (isNaN(page) || page < 1) page = 1
  if (page > maxPage) page = maxPage
  auditJumpPage.value = ''
  fetchAuditLogs(page)
}

function showDiffModal(log) {
  selectedLog.value = log
  diffViewMode.value = 'smart'
  diffModalVisible.value = true
}

async function copyJsonText(val) {
  if (!val) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(val, null, 2))
    diffCopyToast.value = true
    setTimeout(() => {
      diffCopyToast.value = false
    }, 1500)
  } catch (e) {
    console.error('复制 JSON 失败:', e)
  }
}

const computedSmartDiff = computed(() => {
  if (!selectedLog.value) return []
  const before = selectedLog.value.before_value
  const after = selectedLog.value.after_value
  
  const diffList = []
  
  // 场景 1: 仅有新增 (After)
  if (!before && after && typeof after === 'object') {
    for (const [key, newVal] of Object.entries(after)) {
      diffList.push({
        key,
        label: FIELD_LABEL_MAP[key] || key,
        changeType: 'added',
        oldVal: null,
        newVal,
      })
    }
    return diffList
  }

  // 场景 2: 仅有删除 (Before)
  if (before && !after && typeof before === 'object') {
    for (const [key, oldVal] of Object.entries(before)) {
      diffList.push({
        key,
        label: FIELD_LABEL_MAP[key] || key,
        changeType: 'deleted',
        oldVal,
        newVal: null,
      })
    }
    return diffList
  }

  // 场景 3: 变更前后比对
  if (before && after && typeof before === 'object' && typeof after === 'object') {
    const allKeys = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]))
    for (const key of allKeys) {
      const oldVal = before[key]
      const newVal = after[key]
      
      const oldStr = JSON.stringify(oldVal)
      const newStr = JSON.stringify(newVal)
      
      if (oldStr !== newStr) {
        let changeType = 'modified'
        if (oldVal === undefined) changeType = 'added'
        else if (newVal === undefined) changeType = 'deleted'

        diffList.push({
          key,
          label: FIELD_LABEL_MAP[key] || key,
          changeType,
          oldVal,
          newVal,
        })
      }
    }
  }

  return diffList
})

function formatDiffValue(val) {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'object') {
    return JSON.stringify(val, null, 2)
  }
  if (typeof val === 'boolean') {
    return val ? '是 (true)' : '否 (false)'
  }
  return String(val)
}

function getDiffTypeLabel(type) {
  const map = {
    modified: '修改',
    added: '新增',
    deleted: '删除',
  }
  return map[type] || type
}

function getDiffTypeBadgeClass(type) {
  const map = {
    modified: 'warning',
    added: 'success',
    deleted: 'danger',
  }
  return map[type] || 'muted'
}

function formatDateTime(isoString) {
  if (!isoString) return '—'
  try {
    const date = new Date(isoString)
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    const hh = String(date.getHours()).padStart(2, '0')
    const mm = String(date.getMinutes()).padStart(2, '0')
    const ss = String(date.getSeconds()).padStart(2, '0')
    return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
  } catch (e) {
    return isoString
  }
}

function translateActionType(type) {
  const dict = {
    CREATE_DELIVERY: '🚚 新增发货单',
    CANCEL_DELIVERY: '❌ 撤销发货',
    CONFIRM_ARRIVAL: '👷 现场到货确认',
    CONFIRM_CONSTRUCTION: '🏗️ 施工接收确认',
    CONFIRM_WAREHOUSE: '🏢 库管入库确认',
    SAVE_PLAN: '📅 更新三日计划',
    SUBMIT_USAGE: '🔋 上报消耗损耗',
    SUBMIT_STATUS: '✅ 提交填报状态',
    UPDATE_CONFIG: '⚙️ 配置修改',
    SUPER_UPDATE_DELIVERY: '🚨 超管强改',
    SUPER_UPDATE_FITTING_DELIVERY: '🚨 超管强改管件',
    SUBMIT_FITTING_DELIVERY: '🔩 提交管件发货',
    DELETE_FITTING_DELIVERY: '🗑️ 废弃管件发货',
    CONFIRM_FITTING_ARRIVAL: '👷 管件到货确认',
    CONFIRM_FITTING_CONSTRUCTION: '🏗️ 管件施工接收',
    CONFIRM_FITTING_WAREHOUSE: '🏢 管件库管确认',
    CANCEL_FITTING_DELIVERY: '❌ 撤销管件发货',
    QUERY_DAILY_FLOW: '📅 综合流转查询',
    QUERY_BASELINE_PROGRESS: '📐 基准进度查询',
    QUERY_MATERIAL_PRICES: '💰 采购单价查询',
    QUERY_SUPPLIER_LEDGER: '🏭 供给台账查询',
    QUERY_ENTITY_DIRECTORY: '🏢 责任主体查询',
    OCR_DELIVERY_BILL: '📷 业务单据识别',
  }
  return dict[type] || type || '—'
}

function getActionTypeBadgeStyle(type) {
  const colors = {
    CREATE_DELIVERY: { bg: '#e8f4fd', color: '#1d88e5', border: '1px solid #bae6fd' },
    CANCEL_DELIVERY: { bg: '#fde8e8', color: '#e53935', border: '1px solid #fecaca' },
    CONFIRM_ARRIVAL: { bg: '#fef3d6', color: '#d97706', border: '1px solid #fde68a' },
    CONFIRM_CONSTRUCTION: { bg: '#e8f7f0', color: '#059669', border: '1px solid #a7f3d0' },
    CONFIRM_WAREHOUSE: { bg: '#f4eafc', color: '#7c3aed', border: '1px solid #ddd6fe' },
    SAVE_PLAN: { bg: '#e8f4fd', color: '#0284c7', border: '1px solid #bae6fd' },
    SUBMIT_USAGE: { bg: '#fef3d6', color: '#d97706', border: '1px solid #fde68a' },
    SUBMIT_STATUS: { bg: '#e8f7f0', color: '#059669', border: '1px solid #a7f3d0' },
    UPDATE_CONFIG: { bg: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' },
    SUPER_UPDATE_DELIVERY: { bg: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' },
    SUPER_UPDATE_FITTING_DELIVERY: { bg: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' },
    SUBMIT_FITTING_DELIVERY: { bg: '#eef2ff', color: '#4f46e5', border: '1px solid #c7d2fe' },
    DELETE_FITTING_DELIVERY: { bg: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' },
    CONFIRM_FITTING_ARRIVAL: { bg: '#fef3d6', color: '#d97706', border: '1px solid #fde68a' },
    CONFIRM_FITTING_CONSTRUCTION: { bg: '#e8f7f0', color: '#059669', border: '1px solid #a7f3d0' },
    CONFIRM_FITTING_WAREHOUSE: { bg: '#f4eafc', color: '#7c3aed', border: '1px solid #ddd6fe' },
    CANCEL_FITTING_DELIVERY: { bg: '#fee2e2', color: '#b91c1c', border: '1px solid #fca5a5' },
    QUERY_DAILY_FLOW: { bg: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe' },
    QUERY_BASELINE_PROGRESS: { bg: '#f0fdfa', color: '#0f766e', border: '1px solid #99f6e4' },
    QUERY_MATERIAL_PRICES: { bg: '#fefce8', color: '#a16207', border: '1px solid #fef08a' },
    QUERY_SUPPLIER_LEDGER: { bg: '#f5f3ff', color: '#6d28d9', border: '1px solid #ddd6fe' },
    QUERY_ENTITY_DIRECTORY: { bg: '#f8fafc', color: '#334155', border: '1px solid #cbd5e1' },
    OCR_DELIVERY_BILL: { bg: '#fdf2f8', color: '#db2777', border: '1px solid #fbcfe8' },
  }
  const match = colors[type] || { bg: '#f8fafc', color: '#475569', border: '1px solid #cbd5e1' }
  return {
    backgroundColor: match.bg,
    color: match.color,
    border: match.border,
  }
}

async function handleExportLogs() {
  exportLoading.value = true
  try {
    const blob = await exportTubeAuditLogs(PROJECT_KEY, {
      actionType: auditFilters.value.actionType,
      operator: auditFilters.value.operator,
      resourceId: auditFilters.value.resourceId,
      keyword: auditFilters.value.keyword,
      isSensitive: auditFilters.value.isSensitive,
      startDate: auditFilters.value.startDate,
      endDate: auditFilters.value.endDate,
    })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')
    const hh = String(now.getHours()).padStart(2, '0')
    const mm = String(now.getMinutes()).padStart(2, '0')
    const ss = String(now.getSeconds()).padStart(2, '0')
    const timestamp = `${y}${m}${d}_${hh}${mm}${ss}`
    a.download = `tube_audit_logs_${timestamp}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('导出操作日志失败:', error)
    alert(error?.message || '导出操作日志失败')
  } finally {
    exportLoading.value = false
  }
}

</script>

<style scoped>
/* ==================== ⛅ 气温数据管理与导入 CSS ==================== */
.weather-stats-overview {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.8), rgba(240, 249, 255, 0.7));
  backdrop-filter: blur(12px);
  border: 1px solid rgba(186, 230, 253, 0.5) !important;
}
.weather-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin-top: 12px;
}
.weather-meta-item {
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.25s ease;
}
.weather-meta-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
}
.weather-meta-item.highlight {
  background: linear-gradient(135deg, rgba(240, 253, 250, 0.8), rgba(204, 251, 241, 0.6));
  border-color: rgba(153, 246, 228, 0.8);
}
.weather-meta-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 6px;
}
.weather-meta-value {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
}
.weather-meta-desc {
  font-size: 12px;
  color: #94a3b8;
}
.weather-config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.weather-textarea {
  min-height: 80px;
  resize: vertical;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px !important;
  line-height: 1.5;
  background: #f8fafc !important;
  border-color: #e2e8f0 !important;
}
.weather-actions-panel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  gap: 12px;
  flex-wrap: wrap;
}

/* Modal Mask & Layout */
.weather-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  box-sizing: border-box;
}
.weather-modal-container {
  width: 100%;
  max-width: 960px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 16px;
  box-shadow: 0 24px 48px -12px rgba(15, 23, 42, 0.18);
  overflow: hidden;
  animation: modalEnter 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes modalEnter {
  from { transform: scale(0.96) translateY(12px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}
.weather-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: linear-gradient(to bottom, #f8fafc, #ffffff);
  border-bottom: 1px solid #f1f5f9;
}
.weather-modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #94a3b8;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  transition: color 0.2s;
}
.btn-close:hover {
  color: #0f172a;
}
.weather-modal-body {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.eval-summary-banner {
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.9), rgba(241, 245, 249, 0.8));
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
}
.eval-summary-title {
  font-size: 14px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 12px;
}
.eval-metrics-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.eval-metric-capsule {
  flex: 1;
  min-width: 140px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 14px;
}
.eval-metric-capsule .lbl {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}
.eval-metric-capsule .val {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}
.eval-metric-capsule.success {
  border-color: #bbf7d0;
  background: #f0fdf4;
}
.eval-metric-capsule.success .val {
  color: #166534;
}
.eval-metric-capsule.warning {
  border-color: #fed7aa;
  background: #fff7ed;
}
.eval-metric-capsule.warning .val {
  color: #c2410c;
}
.eval-metric-capsule.info {
  border-color: #cbd5e1;
  background: #f8fafc;
}
.eval-metric-capsule.info .val {
  color: #475569;
}
.eval-summary-desc {
  font-size: 12px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}
.weather-preview-table-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  max-height: 280px;
  overflow-y: auto;
  box-shadow: inset 0 2px 4px rgba(15, 23, 42, 0.02);
}
.weather-preview-table-wrap th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  z-index: 10;
}
.preview-table {
  margin: 0;
}
.wmo-code-gray {
  color: #94a3b8;
  font-size: 11px;
}
.highlight-temp {
  font-weight: 700;
  color: #0f172a;
  background: rgba(241, 245, 249, 0.5);
}
.text-rain {
  color: #0284c7;
  font-weight: 600;
}
.weather-modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}
.footer-hint {
  font-size: 12px;
  color: #ef4444;
  font-weight: 500;
}

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

/* PC端“基准设计量预设”头部与控件组 100% 单行平铺垂直居中与精准对齐 */
.baseline-header-row {
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  gap: 16px !important;
  margin-bottom: 14px !important;
  padding-bottom: 12px !important;
  border-bottom: 1px solid #f1f5f9 !important;
}

.baseline-title-heading {
  font-size: 16px !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  margin: 0 !important;
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  white-space: nowrap !important;
}

.baseline-actions-panel {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  flex-wrap: wrap !important;
}

.section1-filter-inline {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 3px 8px 3px 12px;
}

.section1-filter-inline .filter-label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}

.section1-filter-inline select.inline-select {
  height: 32px !important;
  padding: 2px 8px !important;
  font-size: 13px !important;
  border: 1px solid #cbd5e1 !important;
  border-radius: 6px !important;
  background-color: #ffffff !important;
  box-sizing: border-box !important;
}

/* 统计卡片芯片居中对齐微调 */
.baseline-summary {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  margin-top: 4px !important;
  margin-bottom: 14px !important;
}

.baseline-summary .summary-chip {
  display: inline-flex !important;
  align-items: center !important;
  gap: 4px !important;
  padding: 6px 14px !important;
  border-radius: 6px !important;
  background: #f1f5f9 !important;
  border: 1px solid #e2e8f0 !important;
  color: #475569 !important;
  font-size: 12.5px !important;
}

.baseline-summary .summary-chip strong {
  color: #1e293b !important;
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

/* 基准设计量表格 PC 端对齐重构 */
.baseline-table {
  width: 100% !important;
  min-width: 720px !important;
  table-layout: fixed !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
}

.baseline-table th {
  vertical-align: middle !important;
  background: #f8fafc !important;
  color: #475569 !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  padding: 10px 12px !important;
  border-bottom: 1px solid #cbd5e1 !important;
}

.baseline-table td {
  vertical-align: middle !important;
  padding: 6px 8px !important;
  border-bottom: 1px solid #f1f5f9 !important;
}

/* 文本/数值列精准对齐规则 */
.baseline-table th.col-model-spec { text-align: left !important; }
.baseline-table th.col-num-design,
.baseline-table th.col-num-plan { text-align: right !important; }
.baseline-table th.col-text-remark { text-align: left !important; }
.baseline-table th.col-action-btn,
.baseline-table td.col-action-btn { text-align: center !important; }

.baseline-table .table-cell-input {
  height: 36px !important;
  line-height: 1.4 !important;
  box-sizing: border-box !important;
  padding: 6px 10px !important;
  font-size: 13px !important;
  border: 1px solid #cbd5e1 !important;
  border-radius: 6px !important;
  background-color: #ffffff !important;
}

.baseline-table .table-cell-input.text-right {
  text-align: right !important;
  font-family: monospace, sans-serif !important;
  font-size: 13.5px !important;
  font-weight: 600 !important;
  color: #1d4ed8 !important;
}

.baseline-table td.col-action-btn .compact-btn {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 32px !important;
  margin: 0 auto !important;
}
.submission-table {
  min-width: 760px;
}
.status-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.status-chip.success {
  background: #dcfce7;
  color: #166534;
}
.status-chip.pending {
  background: #fee2e2;
  color: #b91c1c;
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

/* 磨砂玻璃态全局数据看板 */
.quick-dashboard-card {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin-bottom: 8px !important;
}

.meta-dashboard {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 14px;
}

.meta-card {
  background: rgba(255, 255, 255, 0.65) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(226, 232, 240, 0.8) !important;
  border-radius: 14px !important;
  padding: 16px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative !important;
  overflow: hidden !important;
  box-sizing: border-box;
}

.meta-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  width: 4px;
  background: linear-gradient(180deg, #6366f1 0%, #3b82f6 100%);
}

.meta-card.highlight::before {
  background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);
}

.meta-card:hover {
  transform: translateY(-4px) !important;
  background: rgba(255, 255, 255, 0.85) !important;
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.08), 0 4px 6px -2px rgba(59, 130, 246, 0.04) !important;
  border-color: rgba(147, 197, 253, 0.5) !important;
}

.meta-label {
  font-size: 12px !important;
  color: #64748b !important;
  font-weight: 500 !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-value {
  font-size: 20px !important;
  color: #1e293b !important;
  font-weight: 700 !important;
  font-family: "Inter", "Outfit", -apple-system, sans-serif !important;
}

.highlight-num {
  color: #2563eb !important;
}

/* 高级侧边控制台布局 */
.admin-workbench-layout {
  display: grid !important;
  grid-template-columns: 240px 1fr !important;
  gap: 24px !important;
  align-items: start !important;
  margin-top: 16px !important;
}

@media (max-width: 1024px) {
  .admin-workbench-layout {
    grid-template-columns: 1fr !important;
  }
}

.admin-sidebar {
  background: rgba(255, 255, 255, 0.75) !important;
  backdrop-filter: blur(12px) !important;
  -webkit-backdrop-filter: blur(12px) !important;
  border: 1px solid rgba(226, 232, 240, 0.8) !important;
  border-radius: 14px !important;
  padding: 12px !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  box-sizing: border-box;
}

.sidebar-tab-btn {
  width: 100% !important;
  border: none !important;
  background: transparent !important;
  padding: 12px 16px !important;
  border-radius: 10px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
  color: #475569 !important;
  text-align: left !important;
  cursor: pointer !important;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 10px !important;
  box-sizing: border-box;
}

.sidebar-tab-btn:hover {
  color: #1e293b !important;
  background: rgba(241, 245, 249, 0.6) !important;
}

.sidebar-tab-btn.active {
  color: #2563eb !important;
  background: #eff6ff !important;
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.1) !important;
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
  margin: 0 !important;
}

/* ==================== 📥 提交记录排版 ==================== */
.submission-overview {
  display: grid;
  grid-template-columns: minmax(230px, 1fr) minmax(360px, 1.1fr);
  align-items: center;
  gap: 18px;
  margin-bottom: 18px;
  padding: 16px 18px;
  background: linear-gradient(135deg, #f8fafc 0%, #f4f7fb 100%);
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.025);
}
.submission-overview__lead {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.submission-overview__icon {
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 20px;
}
.submission-overview__copy {
  min-width: 0;
}
.submission-overview__label {
  margin-bottom: 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}
.submission-overview__time {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 750;
  line-height: 1.35;
}
.submission-overview__age {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 650;
}
.submission-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  min-width: 0;
}
.submission-metric {
  min-width: 0;
  padding: 9px 12px;
  text-align: center;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #dbe4ef;
  border-radius: 9px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.035);
}
.submission-metric__label {
  margin-bottom: 2px;
  color: #64748b;
  font-size: 11px;
  white-space: nowrap;
}
.submission-metric__value {
  color: #2563eb;
  font-size: 18px;
  font-weight: 750;
  line-height: 1.35;
}
.submission-metric__value span {
  color: #64748b;
  font-size: 12px;
  font-weight: 400;
}
.submission-metric--demand .submission-metric__value { color: #059669; }
.submission-metric--supply .submission-metric__value { color: #d97706; }
.submission-metric--query .submission-metric__value { color: #7c3aed; }

.submission-filter-panel {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
  border-radius: 12px;
}
.submission-filter-item {
  grid-column: span 2;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}
.submission-filter-item > span {
  color: #526276;
  font-size: 12px;
  font-weight: 650;
}
.submission-filter-item .input,
.submission-filter-item .select {
  width: 100%;
  min-width: 0;
  height: 38px;
  box-sizing: border-box;
  padding: 0 11px;
  color: #334155;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.submission-filter-item .input:focus,
.submission-filter-item .select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}
.submission-filter-actions {
  grid-column: span 6;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  align-items: center;
  min-width: 0;
  margin-top: 4px;
}
.submission-reset-btn {
  min-height: 38px;
  padding: 0 16px;
  border-radius: 7px;
  font-size: 13px;
  color: #475569;
  border: 1px solid #cbd5e1;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}
.submission-reset-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
  border-color: #94a3b8;
}
.submission-query-btn {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 22px;
  border-radius: 7px;
  font-size: 13px;
  white-space: nowrap;
}

.submission-table-wrap {
  max-height: 600px;
  overflow: auto;
  scrollbar-gutter: stable;
  background: #fff;
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.035);
}
.submission-log-table {
  width: 100%;
  min-width: 960px;
  margin: 0;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
}
.submission-col-time { width: 230px; }
.submission-col-operator { width: 180px; }
.submission-col-action { width: 165px; }
.submission-col-detail { width: auto; }
.submission-log-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 12px 16px;
  text-align: left;
  color: #475569;
  background: #f1f5f9;
  border-bottom: 1px solid #cbd5e1;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.submission-log-table tbody td {
  padding: 14px 16px;
  vertical-align: top;
  border-bottom: 1px solid #e8edf3;
}
.submission-log-table tbody tr {
  background: #fff;
  transition: background-color 0.18s;
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
  font-size: 13px;
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
  color: #dc2626;
  background: #fff1f2;
  border: 1px solid #fecaca;
  border-radius: 5px;
  font-size: 10px;
  font-weight: 700;
}
.submission-ip {
  min-width: 0;
  color: #64748b;
  font-family: Consolas, Monaco, monospace;
  font-size: 11px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.submission-operator-cell {
  line-height: 1.5;
}
.submission-operator-name {
  color: #1e293b;
  font-size: 13px;
  font-weight: 700;
}
.submission-operator-meta {
  margin-top: 6px;
}
.submission-group-chip {
  display: inline-flex;
  max-width: 100%;
  padding: 2px 7px;
  color: #526276;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  font-size: 11px;
  font-weight: 500;
  overflow-wrap: anywhere;
}
.submission-action-cell {
  line-height: 1.5;
}
.submission-action-badge {
  display: inline-flex !important;
  align-items: center;
  max-width: 100%;
  padding: 4px 10px !important;
  border-radius: 7px !important;
  font-size: 11px !important;
  font-weight: 650 !important;
  white-space: nowrap;
}
.submission-detail-cell {
  color: #334155;
  font-size: 13px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.submission-detail-text {
  min-height: 42px;
  box-sizing: border-box;
  padding: 8px 12px;
  color: #1e293b;
  background: #f8fafc;
  border-left: 3px solid #bfdbfe;
  border-radius: 0 7px 7px 0;
}
.submission-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
  padding: 11px 14px;
  color: #526276;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
  border-radius: 10px;
  font-size: 13px;
}
.submission-pagination strong {
  color: #0f172a;
}
.submission-pagination__controls {
  display: flex;
  align-items: center;
  gap: 10px;
}
.submission-page-btn {
  padding: 5px 12px !important;
  color: #334155 !important;
  background: #fff !important;
  border: 1px solid #cbd5e1 !important;
  border-radius: 7px !important;
}
.submission-page-btn:disabled {
  color: #94a3b8 !important;
  background: #f1f5f9 !important;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .submission-overview {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .submission-filter-panel {
    grid-template-columns: 1fr;
  }
  .submission-filter-item,
  .submission-filter-actions {
    grid-column: 1 / -1;
  }
  .submission-metrics {
    grid-template-columns: 1fr;
  }
  .submission-pagination {
    align-items: stretch;
  }
  .submission-pagination__summary {
    width: 100%;
  }
  .submission-pagination__controls {
    justify-content: space-between;
    width: 100%;
  }
}

.table-cell-input {
  padding: 6px 10px !important;
  font-size: 13px !important;
  border-radius: 6px !important;
  border-color: #e2e8f0 !important;
}

.table-cell-input:focus {
  border-color: #2563eb !important;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1) !important;
}

.compact-btn {
  padding: 6px 12px !important;
  font-size: 12px !important;
  border-radius: 6px !important;
}

.danger-ghost {
  border: 1px solid #fee2e2 !important;
  color: #ef4444 !important;
  background: #fef2f2 !important;
  cursor: pointer;
  transition: all 0.2s ease;
}

.danger-ghost:hover {
  background: #ef4444 !important;
  color: #ffffff !important;
  border-color: #ef4444 !important;
}

/* 升级表格 Hover 和对齐 */
.table th, .table td {
  padding: 12px 14px !important;
  vertical-align: middle !important;
}

.table tbody tr:hover {
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.02) 0%, rgba(255, 255, 255, 0) 100%) !important;
}

.shadow-accent {
  box-shadow: 0 4px 12px 0 rgba(37, 99, 235, 0.25) !important;
}

.json-editor-textarea {
  width: 100%;
  min-height: 480px;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 16px;
  font-family: "Consolas", "Monaco", monospace;
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  background: #ffffff;
  box-sizing: border-box;
  transition: all 0.2s ease-in-out;
}

.json-editor-textarea.has-error {
  border-color: #ef4444 !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15) !important;
  outline: none !important;
}

.json-error-banner {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: #ffffff;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  box-shadow: 0 4px 12px 0 rgba(239, 68, 68, 0.2);
  font-size: 13px;
  animation: slide-down-fade 0.25s ease-out;
}

.json-error-banner__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-weight: 700;
}

.json-error-banner__body {
  line-height: 1.5;
  font-family: "Consolas", "Monaco", monospace;
  background: rgba(0, 0, 0, 0.15);
  padding: 8px 12px;
  border-radius: 6px;
  word-break: break-all;
}

@keyframes slide-down-fade {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.json-editor-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
  gap: 16px;
  flex-wrap: wrap;
}

.json-editor-hint {
  font-size: 13px;
  color: #ea580c;
  font-weight: 600;
  display: flex;
  align-items: center;
}

.action-btn-group {
  display: flex;
  gap: 10px;
}

.cell-text {
  max-width: 180px !important;
  min-width: 130px !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.cell-datetime {
  font-family: "Consolas", "Courier New", monospace !important;
  font-size: 13px !important;
  min-width: 132px;
}

/* ==========================================================================
   气象数据源模式切换 - 精美高保真双卡片样式
   ========================================================================== */
.weather-provider-card {
  margin-top: 16px;
}

.provider-selector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
  margin-top: 16px;
  margin-bottom: 20px;
}

.provider-option-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 20px;
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  position: relative;
}

.provider-option-card:hover {
  border-color: #93c5fd;
  background: #f8fafc;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px -2px rgba(59, 130, 246, 0.1);
}

.provider-option-card.active {
  border-color: #2563eb;
  background: #eff6ff;
  box-shadow: 0 6px 18px -2px rgba(37, 99, 235, 0.16);
}

.provider-option-card input[type="radio"] {
  margin-top: 3px;
  accent-color: #2563eb;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  cursor: pointer;
}

.provider-card-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.provider-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.provider-badge {
  font-size: 13px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
}

.provider-badge.amap {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

.provider-badge.open-meteo {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #e2e8f0;
}

.provider-source {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.provider-desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.55;
  margin: 2px 0 0 0;
}

.provider-save-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-top: 14px;
  border-top: 1px dashed #e2e8f0;
}

/* 按钮 Premium 居中与防折行加固 */
.btn, .primary-button, .button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  text-align: center !important;
  white-space: nowrap !important;
  word-break: keep-all !important;
  box-sizing: border-box !important;
}

/* ⚙️ 核心参数板块 $3\times2$ 规整双栏矩阵 */
.core-field-grid {
  display: grid !important;
  grid-template-columns: repeat(2, 1fr) !important;
  gap: 20px 32px !important; /* 行距20px，列距32px */
  align-items: start !important;
}

@media (max-width: 860px) {
  .core-field-grid {
    grid-template-columns: 1fr !important; /* 移动端折叠为单栏 */
    gap: 16px !important;
  }
}

/* ==========================================================================
   📜 操作审计日志 (Audit Log) - 高质感看板、6列工整过滤、锁宽表格与智能 Diff 弹窗
   ========================================================================== */

/* 态势概览看板 */
.audit-overview {
  display: grid;
  grid-template-columns: minmax(230px, 1fr) minmax(360px, 1.1fr);
  align-items: center;
  gap: 18px;
  margin-bottom: 18px;
  padding: 16px 18px;
  background: linear-gradient(135deg, #f8fafc 0%, #f4f7fb 100%);
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.025);
}

.audit-overview__lead {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.audit-overview__icon {
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 20px;
}

.audit-overview__copy {
  min-width: 0;
}

.audit-overview__label {
  margin-bottom: 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.audit-overview__time {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 750;
  line-height: 1.35;
}

.audit-overview__age {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 650;
}

.audit-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  min-width: 0;
}

.audit-metric {
  min-width: 0;
  padding: 9px 12px;
  text-align: center;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid #dbe4ef;
  border-radius: 9px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.035);
  transition: all 0.2s ease;
}

.audit-metric__label {
  margin-bottom: 2px;
  color: #64748b;
  font-size: 11px;
  white-space: nowrap;
}

.audit-metric__value {
  color: #2563eb;
  font-size: 18px;
  font-weight: 750;
  line-height: 1.35;
}

.audit-metric__value span {
  color: #64748b;
  font-size: 12px;
  font-weight: 400;
}

.audit-metric--sensitive {
  cursor: pointer;
  border-color: #fecaca;
  background: #fffafa;
}

.audit-metric--sensitive .audit-metric__value {
  color: #dc2626;
}

.audit-metric--sensitive:hover {
  border-color: #f87171;
  background: #fef2f2;
  transform: translateY(-1px);
}

.audit-metric--sensitive.is-active {
  border-color: #dc2626;
  background: #fee2e2;
  box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.2);
}

.audit-metric--operator .audit-metric__value {
  color: #059669;
}

/* 6列严整过滤面板 (与提交记录完全对齐) */
.audit-filter-panel {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
  border-radius: 12px;
}

.audit-filter-item {
  grid-column: span 2;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.audit-filter-item > span {
  color: #526276;
  font-size: 12px;
  font-weight: 650;
}

.audit-filter-item .input,
.audit-filter-item .select {
  width: 100%;
  min-width: 0;
  height: 38px;
  box-sizing: border-box;
  padding: 0 11px;
  color: #334155;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.audit-filter-item .input:focus,
.audit-filter-item .select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* 过滤面板第3行：左侧敏感Toggle，右侧查询与导出按钮 */
.audit-filter-toggle-wrap {
  grid-column: span 3;
  display: flex;
  align-items: center;
  min-width: 0;
}

.audit-toggle-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: #ffffff;
  border: 1px solid #fecaca;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.audit-toggle-chip:hover {
  background: #fff5f5;
  border-color: #f87171;
}

.audit-toggle-chip.active {
  background: #fee2e2;
  border-color: #dc2626;
  box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.15);
}

.audit-toggle-chip input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #dc2626;
  cursor: pointer;
  margin: 0;
}

.audit-toggle-text {
  font-size: 12.5px;
  font-weight: 700;
  color: #b91c1c;
}

.audit-filter-actions {
  grid-column: span 3;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}

.audit-query-btn,
.audit-reset-btn,
.audit-export-btn {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 16px;
  border-radius: 7px;
  font-size: 13px;
  white-space: nowrap;
}

.audit-reset-btn,
.audit-export-btn {
  background: #ffffff;
  border-color: #cbd5e1;
  color: #334155;
}

.audit-reset-btn:hover,
.audit-export-btn:hover {
  background: #f8fafc;
  border-color: #94a3b8;
}

/* 表格容器与锁宽 colgroup */
.audit-table-wrap {
  max-height: 600px;
  overflow: auto;
  scrollbar-gutter: stable;
  background: #fff;
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.035);
}

.audit-log-table {
  width: 100%;
  min-width: 1060px;
  margin: 0;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
}

.audit-col-time { width: 190px; }
.audit-col-resource { width: 180px; }
.audit-col-operator { width: 140px; }
.audit-col-action { width: 165px; }
.audit-col-desc { width: auto; }
.audit-col-diff { width: 130px; }

.audit-log-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 12px 16px;
  text-align: left;
  color: #475569;
  background: #f1f5f9;
  border-bottom: 1px solid #cbd5e1;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.audit-log-table tbody td {
  padding: 12px 16px;
  vertical-align: middle;
  border-bottom: 1px solid #e8edf3;
}

.audit-log-table tbody tr {
  background: #fff;
  transition: background-color 0.18s;
}

.audit-log-table tbody tr:hover {
  background: #f8fafc;
}

.audit-row--sensitive {
  background: #fffafa !important;
}

.audit-row--sensitive:hover {
  background: #fff1f2 !important;
}

/* 时间列 */
.audit-time-cell {
  min-width: 0;
}

.audit-time-value {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.35;
}

.audit-time-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.audit-recent-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 11px;
  font-weight: 700;
}

.audit-ip {
  color: #64748b;
  font-family: Consolas, Monaco, monospace;
  font-size: 11px;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 4px;
}

/* 单号列 */
.audit-resource-box {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  max-width: 156px;
  box-sizing: border-box;
  padding: 4px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.audit-resource-code {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audit-resource-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.audit-micro-btn {
  background: transparent;
  border: none;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  line-height: 1;
  color: #64748b;
  transition: all 0.15s;
}

.audit-micro-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

/* 操作人列 */
.audit-operator-name {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.audit-operator-meta {
  margin-top: 4px;
}

/* 行为类型列 */
.audit-action-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.3;
}

.audit-sensitive-dot {
  font-size: 12px;
}

/* 操作详情说明 */
.audit-desc-text,
.submission-detail-text {
  color: #334155;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-all;
}

.submission-section-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 7px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  font-size: 11.5px;
  font-weight: 700;
  border-radius: 5px;
  margin-right: 6px;
  vertical-align: middle;
  white-space: nowrap;
}

/* 差异对比列 */
.audit-diff-cell {
  text-align: center;
}

.audit-diff-trigger-btn {
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
  color: #2563eb;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.audit-diff-trigger-btn:hover {
  background: #dbeafe;
  border-color: #93c5fd;
}

.audit-empty-dash {
  color: #94a3b8;
  font-size: 12px;
}

/* 分页控制栏 (与提交记录 100% 对齐) */
.audit-pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
  padding: 10px 16px;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
  border-radius: 10px;
  font-size: 13px;
  color: #475569;
}

.audit-pagination-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.audit-pagination-divider {
  color: #cbd5e1;
}

.audit-page-size-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.audit-limit-select {
  height: 28px;
  padding: 0 6px;
  font-size: 12px;
  border-radius: 5px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
}

.audit-pagination-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.audit-page-info strong {
  color: #0f172a;
}

.audit-jump-box {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 6px;
}

.audit-jump-input {
  width: 54px;
  height: 28px;
  padding: 0 6px;
  font-size: 12px;
  text-align: center;
  border-radius: 5px;
}

/* 智能 Diff 弹窗高质感样式 */
.audit-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(8px);
}

.audit-diff-modal {
  width: 90%;
  max-width: 1040px;
  max-height: 86vh;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.audit-modal-header {
  padding: 16px 22px;
  background: linear-gradient(to bottom, #f8fafc, #ffffff);
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.audit-modal-title {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
}

.audit-modal-sensitive-tag {
  font-size: 11px;
}

.audit-modal-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 5px;
  font-size: 12px;
  color: #64748b;
  flex-wrap: wrap;
}

.audit-modal-subtitle strong {
  color: #1e293b;
}

.audit-sep {
  color: #cbd5e1;
}

.audit-modal-header__actions {
  display: flex;
  align-items: center;
  gap: 14px;
}

.audit-view-tabs {
  display: flex;
  background: #f1f5f9;
  padding: 3px;
  border-radius: 8px;
  gap: 2px;
}

.audit-view-tab {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 650;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.18s;
}

.audit-view-tab.is-active {
  background: #ffffff;
  color: #2563eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.audit-modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  flex: 1;
  background: #ffffff;
}

/* 智能差异视图 */
.audit-smart-diff-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.audit-diff-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 10px;
}

.audit-diff-banner__icon {
  font-size: 22px;
}

.audit-diff-banner__content strong {
  display: block;
  font-size: 13.5px;
  margin-bottom: 2px;
}

.audit-diff-banner__content p {
  margin: 0;
  font-size: 12px;
}

.audit-diff-banner--create {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
}

.audit-diff-banner--delete {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.audit-diff-banner--modify {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.audit-smart-table-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: hidden;
}

.audit-smart-diff-table {
  width: 100%;
  margin: 0;
  table-layout: fixed;
  border-collapse: collapse;
}

.audit-smart-diff-table thead th {
  background: #f8fafc;
  padding: 10px 14px;
  font-size: 12px;
  color: #475569;
  font-weight: 700;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.audit-smart-diff-table tbody td {
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
  vertical-align: middle;
}

.audit-diff-field-name {
  font-weight: 700;
  color: #1e293b;
  font-size: 13px;
}

.audit-diff-field-key code {
  font-family: Consolas, Monaco, monospace;
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  padding: 1px 4px;
  border-radius: 3px;
}

.audit-diff-arrow-cell {
  text-align: center;
  color: #94a3b8;
  font-weight: 700;
}

.audit-val-content {
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.audit-val-content--del {
  background: #fff1f2;
  color: #be123c;
  text-decoration: line-through;
  border: 1px solid #fecdd3;
}

.audit-val-content--add {
  background: #f0fdf4;
  color: #15803d;
  font-weight: 600;
  border: 1px solid #bbf7d0;
}

.audit-val-placeholder {
  color: #94a3b8;
  font-style: italic;
  font-size: 12px;
}

.audit-diff-empty {
  text-align: center;
  padding: 30px;
  color: #64748b;
}

/* 原始快照对比双栏 */
.audit-raw-json-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.audit-raw-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.audit-raw-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 700;
  padding: 2px 0;
}

.audit-raw-header--before { color: #dc2626; }
.audit-raw-header--after { color: #16a34a; }

.audit-raw-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 6px;
}

.audit-raw-header--before .audit-raw-dot { background: #dc2626; }
.audit-raw-header--after .audit-raw-dot { background: #16a34a; }

.audit-copy-json-btn {
  font-size: 11px;
}

.audit-json-pre {
  border-radius: 8px;
  padding: 14px;
  margin: 0;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  overflow-x: auto;
  max-height: 440px;
  white-space: pre-wrap;
  text-align: left;
  line-height: 1.6;
}

.audit-json-pre--before {
  background: #fff5f5;
  border: 1px solid #fca5a5;
  color: #991b1b;
}

.audit-json-pre--after {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.audit-modal-footer {
  padding: 12px 22px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
}

.audit-copy-toast {
  color: #16a34a;
  font-size: 12px;
  font-weight: 700;
}

/* ==================== 📍 IP 归属地气泡浮窗 (Popover) 样式 ==================== */
.clickable-ip {
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.18s ease;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 6px;
}

.clickable-ip:hover {
  background: #e2e8f0 !important;
  color: #1d4ed8 !important;
  border-color: #93c5fd !important;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
}

.clickable-ip:active {
  transform: translateY(0);
}

.ip-popover-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1200;
  background: transparent;
}

.ip-popover-card {
  position: absolute;
  width: 290px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.18), 0 8px 10px -6px rgba(15, 23, 42, 0.1);
  padding: 14px;
  z-index: 1201;
  animation: popoverFadeIn 0.15s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes popoverFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.ip-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 8px;
  margin-bottom: 10px;
}

.ip-popover-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.ip-popover-close {
  background: none;
  border: none;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  border-radius: 4px;
  transition: all 0.15s;
}

.ip-popover-close:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.ip-popover-address-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 10px;
}

.ip-code {
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.ip-copy-btn {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s;
}

.ip-copy-btn:hover {
  background: #f1f5f9;
  color: #1d4ed8;
  border-color: #93c5fd;
}

.ip-popover-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 18px 0;
  font-size: 12.5px;
  color: #64748b;
}

.ip-loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.ip-popover-error {
  padding: 12px;
  background: #fff5f5;
  border: 1px solid #fecaca;
  border-radius: 6px;
  color: #dc2626;
  font-size: 12px;
}

.ip-popover-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ip-detail-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12.5px;
}

.ip-detail-label {
  color: #64748b;
  font-weight: 500;
}

.ip-detail-value {
  color: #0f172a;
  font-weight: 600;
  text-align: right;
}

.ip-detail-value--loc {
  color: #1d4ed8;
  font-weight: 700;
}

.badge-private-ip {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.badge-public-ip {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.ip-adcode-tag {
  font-family: Consolas, Monaco, monospace;
  font-size: 11.5px;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 4px;
  color: #475569;
}

.ip-detail-item--footer {
  border-top: 1px dashed #f1f5f9;
  padding-top: 6px;
  margin-top: 2px;
}

.ip-provider-tag {
  font-size: 11px;
  color: #0284c7;
  font-weight: 600;
}

.clickable-user-link {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #4f46e5 !important;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
  user-select: none;
}

.clickable-user-link:hover {
  background: #eef2ff;
  color: #3730a3 !important;
  text-decoration: underline;
}

.clickable-user-link .link-hint-icon {
  font-size: 11px;
  opacity: 0.7;
  transition: transform 0.15s ease;
}

.clickable-user-link:hover .link-hint-icon {
  opacity: 1;
  transform: translate(1px, -1px);
}
</style>
