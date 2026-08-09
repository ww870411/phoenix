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
            📥 提交记录
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
          
          <!-- Tab 0: 提交记录 (放在第一个位置) -->
          <div v-if="activeTab === 'submissions'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">📥 提交记录</div>
                </div>
                <div class="section-actions">
                  <button class="btn ghost compact-btn" type="button" @click="fetchSubmissionLogs(1)">
                    🔄 刷新提交记录
                  </button>
                </div>
              </div>

              <!-- 数据新旧核对面板 -->
              <div class="submission-overview">
                <div class="submission-overview__lead">
                  <div class="submission-overview__icon" aria-hidden="true">⏱️</div>
                  <div class="submission-overview__copy">
                    <div class="submission-overview__label">数据库最新提交物理时间</div>
                    <div class="submission-overview__time">
                      <span>{{ submissionLatestTime ? formatDateTime(submissionLatestTime) : '尚无提交记录' }}</span>
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

                <!-- 24h 提交小计数看板 -->
                <div class="submission-metrics">
                  <div class="submission-metric submission-metric--total">
                    <div class="submission-metric__label">24h 提交总量</div>
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
                </div>
              </div>

              <!-- 两行三列过滤控制面板，避免日期控件挤出卡片边界 -->
              <div class="submission-filter-panel">
                <label class="submission-filter-item">
                  <span>提交主体分类</span>
                  <select v-model="submissionFilters.entityType" class="select" @change="fetchSubmissionLogs(1)">
                    <option value="">全部主体</option>
                    <option value="demand">📍 需求主体 (施工队)</option>
                    <option value="supply">🚚 供给主体 (厂家)</option>
                    <option value="warehouse">🏢 库管主体</option>
                  </select>
                </label>

                <label class="submission-filter-item">
                  <span>具体提交行为</span>
                  <select v-model="submissionFilters.actionType" class="select">
                    <option value="">全部提交行为</option>
                    <option value="SAVE_PLAN">📅 保存三日计划</option>
                    <option value="SUBMIT_USAGE">🔋 上报施工消耗</option>
                    <option value="SUBMIT_STATUS">✅ 提交填报完成</option>
                    <option value="CONFIRM_ARRIVAL">👷 到货签收</option>
                    <option value="CONFIRM_CONSTRUCTION">👷 施工接收</option>
                    <option value="CREATE_DELIVERY">🚚 厂家发货</option>
                    <option value="CREATE_DELIVERY_BATCH">🚚 批量发货</option>
                    <option value="CANCEL_DELIVERY">❌ 撤销发货</option>
                    <option value="CONFIRM_WAREHOUSE">🏢 库管确认</option>
                  </select>
                </label>

                <label class="submission-filter-item">
                  <span>提交账号/操作人</span>
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
                  <button class="btn primary submission-query-btn" type="button" @click="fetchSubmissionLogs(1)">
                    🔍 查询记录
                  </button>
                </div>
              </div>

              <!-- 提交记录明细列表 -->
              <div v-if="submissionLoading" class="loading-placeholder" style="padding: 40px; text-align: center; color: #64748b;">数据提交记录加载中...</div>
              <div v-else-if="submissionLogs.length === 0" class="empty-placeholder" style="padding: 40px; text-align: center; color: #777;">未查询到任何主体提交的数据记录。</div>
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
                        <th>提交时间与来源 IP</th>
                        <th>提交主体 / 操作人</th>
                        <th>行为类型</th>
                        <th>数据提交内容与详情说明</th>
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
                              🔥 新提交
                            </span>
                            <span v-if="log.client_ip" class="submission-ip">
                              IP: {{ log.client_ip }}
                            </span>
                          </div>
                        </td>
                        <td class="submission-operator-cell">
                          <div class="submission-operator-name">{{ log.operator }}</div>
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
                            {{ log.action_desc }}
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- 分页栏 -->
                <div class="submission-pagination">
                  <span class="submission-pagination__summary">共计 <strong>{{ submissionTotal }}</strong> 条数据提交记录</span>
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
                  <input v-model="showDate" type="date" class="input" />
                  <small class="field-help">决定大盘看板及历史消耗数据统计的宏观切断视界。</small>
                </label>
                <label class="field">
                  <span>消耗采集日期 (usage_collection_date)</span>
                  <input v-model="usageCollectionDate" type="date" class="input" :disabled="autoUpdatePlanStartDate" />
                  <small class="field-help">需求侧施工队上报实际施工消耗与现场损耗的基准日期。</small>
                </label>
                <label class="field">
                  <span>滚动计划起始日期 (plan_start_date)</span>
                  <input v-model="planStartDate" type="date" class="input" :disabled="autoUpdatePlanStartDate" />
                  <small class="field-help">未来三日计划采集的物理起始日期锚点（滚动计划 T 日）。</small>
                </label>
                <label class="field">
                  <span>起始日期是否自动随今天变化</span>
                  <select v-model="autoUpdatePlanStartDate" class="input" @change="handleAutoPlanStartDateChange">
                    <option :value="false">否 (手动维护起始日期)</option>
                    <option :value="true">是 (每天随日期自动后移)</option>
                  </select>
                  <small class="field-help">开启自动更新后，该日期会随物理时间每天自动向后平推。</small>
                </label>
                <label class="field">
                  <span>计划可填报修改天数 (plan_editable_days)</span>
                  <input v-model.number="planEditableDays" class="input" type="number" min="0" max="3" step="1" />
                  <small class="field-help">3 为三天都可填，2 为后两天可填，0 为计划全部锁盘不可填。</small>
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
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in warehouseKeepers" :key="index">
                      <td><input v-model.trim="item.keeper_id" class="input table-cell-input" type="text" placeholder="如 warehouse_keeper_a" /></td>
                      <td><input v-model.trim="item.keeper_name" class="input table-cell-input" type="text" placeholder="输入姓名" /></td>
                      <td><input v-model.trim="item.contact_phone" class="input table-cell-input" type="text" placeholder="输入联系电话" /></td>
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
              <div class="card-header-row">
                <div>
                  <div class="card-header">需求主体管线基准设计量</div>
                  <p class="sub block-sub">维护特定需求主体的设计基准总量及计划采购总量，用以评估物流净缺口。请先选择需求主体过滤。</p>
                </div>
                <div class="section-actions baseline-actions-panel">
                  <div class="section1-filter-inline">
                    <span>过滤需求主体：</span>
                    <select v-model="selectedBaselineSection1Id" class="input inline-select">
                      <option v-for="section1 in demandEntities" :key="section1.section_1_id" :value="section1.section_1_id">
                        {{ section1.section_1_name || section1.section_1_id }}
                      </option>
                    </select>
                  </div>
                  <button class="btn ghost" type="button" @click="addBaselinePreset">➕ 新增型号行</button>
                  <button class="btn ghost btn-action-tool" type="button" @click="fillMissingPipeModelsForSelectedSection1">补齐缺失规格</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('baseline_presets')" @click="saveSection('baseline_presets')">
                    {{ isSaving('baseline_presets') ? '保存中…' : '💾 保存设计基准' }}
                  </button>
                </div>
              </div>
              <p v-if="sectionMessage('baseline_presets')" :class="['section-tip', sectionMessage('baseline_presets').type]">
                {{ sectionMessage('baseline_presets').text }}
              </p>
              <div class="summary-row baseline-summary">
                <span class="summary-chip">当前站点：{{ selectedBaselineSection1Name }}</span>
                <span class="summary-chip">当前显示：{{ filteredBaselinePresets.length }} 条</span>
                <span class="summary-chip">全量预设：{{ baselinePresets.length }} 条</span>
              </div>
              <div class="table-wrap">
                <table class="table editor-table baseline-table">
                  <thead>
                    <tr>
                      <th>管材型号</th>
                      <th>设计量(米)</th>
                      <th>计划采购总量(米)</th>
                      <th>说明备注</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in filteredBaselinePresets" :key="item.__row_key">
                      <td>
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
                      <td><input v-model.number="item.design_qty" class="input table-cell-input" type="number" min="0" step="1" /></td>
                      <td><input v-model.number="item.purchase_plan_qty" class="input table-cell-input" type="number" min="0" step="1" /></td>
                      <td><input v-model.trim="item.remark" class="input table-cell-input" type="text" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeBaselinePreset(item.__row_key)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
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
                  <div class="card-header">📜 物理操作与配置审计日志</div>
                  <p class="sub block-sub">记录保温管系统的核心写操作（填报、物流、到货、施工、配置修改），支持快照 Diff 追溯。</p>
                </div>
              </div>
              
              <!-- 过滤条件与导出栏 -->
              <div class="filter-panel" style="display: flex; gap: 15px; margin-bottom: 20px; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; flex-wrap: wrap;">
                <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
                  <label style="font-size: 12px; color: #64748b; font-weight: 500;">操作类型</label>
                  <select v-model="auditFilters.actionType" class="select" style="min-width: 150px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; height: 32px; padding: 0 8px; font-size: 13px;">
                    <option value="">全部类型</option>
                    <option value="CREATE_DELIVERY">🚚 新增发货单</option>
                    <option value="CANCEL_DELIVERY">❌ 撤销发货</option>
                    <option value="CONFIRM_ARRIVAL">👷 确认到货</option>
                    <option value="CONFIRM_CONSTRUCTION">👷 施工接收</option>
                    <option value="CONFIRM_WAREHOUSE">🏢 库管确认</option>
                    <option value="SAVE_PLAN">📅 更新三日计划</option>
                    <option value="SUBMIT_USAGE">🔋 上报消耗损耗</option>
                    <option value="SUBMIT_STATUS">✅ 提交填报状态</option>
                    <option value="UPDATE_CONFIG">⚙️ 配置修改</option>
                    <option value="SUPER_UPDATE_DELIVERY">🚨 超管强改</option>
                  </select>
                </div>
                
                <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
                  <label style="font-size: 12px; color: #64748b; font-weight: 500;">操作人</label>
                  <input v-model.trim="auditFilters.operator" class="input" type="text" placeholder="模糊搜索操作人" style="height: 32px; width: 140px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
                </div>
                
                <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
                  <label style="font-size: 12px; color: #64748b; font-weight: 500;">开始日期</label>
                  <input v-model="auditFilters.startDate" class="input" type="date" style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
                </div>
                
                <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
                  <label style="font-size: 12px; color: #64748b; font-weight: 500;">结束日期</label>
                  <input v-model="auditFilters.endDate" class="input" type="date" style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
                </div>
 
                <div class="filter-item" style="display: flex; gap: 8px; align-self: flex-end; margin-left: auto;">
                  <button class="btn primary" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 5px; cursor: pointer;" @click="fetchAuditLogs(1)">
                    🔍 查询日志
                  </button>
                  <button class="btn ghost" :disabled="exportLoading" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 5px; border-color: #cbd5e1; cursor: pointer; background: #fff;" @click="handleExportLogs">
                    <span>{{ exportLoading ? '正在导出...' : '📥 导出 Excel (CSV)' }}</span>
                  </button>
                </div>
              </div>
 
              <!-- 日志明细列表 -->
              <div v-if="auditLoading" class="loading-placeholder" style="padding: 40px; text-align: center; color: #64748b;">加载审计日志中...</div>
              <div v-else-if="auditLogs.length === 0" class="empty-placeholder" style="padding: 40px; text-align: center; color: #777;">未查询到任何匹配的操作日志。</div>
              <div v-else>
                <div class="table-wrap" style="max-height: 550px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
                  <table class="table editor-table" style="margin: 0; width: 100%; border-collapse: collapse;">
                    <thead>
                      <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                        <th style="width: 170px; text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px;">时间与IP</th>
                        <th style="width: 130px; text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px;">操作人</th>
                        <th style="width: 140px; text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px;">类型</th>
                        <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px;">操作详情</th>
                        <th style="width: 110px; text-align: center; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px;">快照对比</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="log in auditLogs" :key="log.id" style="border-bottom: 1px solid #e2e8f0; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f8fafc'" onmouseout="this.style.backgroundColor='transparent'">
                        <td style="color: #64748b; font-size: 12px; padding: 12px 16px; white-space: nowrap; line-height: 1.4; vertical-align: middle;">
                          <div style="font-weight: 500; color: #475569;">{{ formatDateTime(log.created_at) }}</div>
                          <div v-if="log.client_ip" style="font-family: monospace; color: #94a3b8; font-size: 11px; margin-top: 3px; display: flex; align-items: center; gap: 3px;">
                            <span style="display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: #cbd5e1;"></span>
                            IP: {{ log.client_ip }}
                          </div>
                          <div v-else style="font-family: monospace; color: #cbd5e1; font-size: 11px; margin-top: 3px; display: flex; align-items: center; gap: 3px;">
                            <span style="display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: #e2e8f0;"></span>
                            IP: —
                          </div>
                        </td>
                        <td style="padding: 12px 16px; vertical-align: middle;">
                          <span style="font-weight: 600; color: #334155; display: block; font-size: 13px;">{{ log.operator }}</span>
                          <span v-if="log.operator_group" style="display: block; font-size: 11px; color: #94a3b8; margin-top: 2px;">{{ log.operator_group }}</span>
                        </td>
                        <td style="padding: 12px 16px; vertical-align: middle;">
                          <span class="badge" :style="getActionTypeBadgeStyle(log.action_type)" style="font-size: 11px; padding: 3px 8px; border-radius: 6px; font-weight: 600; display: inline-block;">
                            {{ translateActionType(log.action_type) }}
                          </span>
                        </td>
                        <td style="font-size: 13px; color: #334155; padding: 12px 16px; line-height: 1.5; max-width: 240px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; transition: color 0.2s; vertical-align: middle;" onmouseover="this.style.color='#2563eb'" onmouseout="this.style.color='#334155'" @click="togglePopover($event, log)">
                          <span style="border-bottom: 1px dashed #cbd5e1; padding-bottom: 2px;">{{ log.action_desc }}</span>
                        </td>
                        <td style="text-align: center; padding: 12px 16px; vertical-align: middle;">
                          <button 
                            v-if="log.before_value || log.after_value" 
                            class="btn-text" 
                            style="color: #2563eb; cursor: pointer; background: none; border: none; font-size: 12px; font-weight: 600; padding: 4px 8px; border-radius: 4px; transition: background 0.2s;"
                            onmouseover="this.style.background='rgba(37,99,235,0.06)'"
                            onmouseout="this.style.background='none'"
                            @click="showDiffModal(log)"
                          >
                            🔍 查看 Diff
                          </button>
                          <span v-else style="color: #94a3b8; font-size: 12px;">无快照</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                
                <!-- 分页栏 -->
                <div class="pagination-bar" style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center; color: #475569; font-size: 13px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 16px; border-radius: 8px;">
                  <span>共计 <strong style="color: #0f172a;">{{ auditTotal }}</strong> 条记录</span>
                  <div style="display: flex; gap: 10px; align-items: center;">
                    <button class="btn ghost compact-btn" style="padding: 4px 12px; border-radius: 6px; background: #fff; border: 1px solid #cbd5e1; color: #334155; cursor: pointer;" :disabled="auditPage <= 1" @click="fetchAuditLogs(auditPage - 1)">上一页</button>
                    <span style="color: #64748b;">第 <strong style="color: #0f172a;">{{ auditPage }}</strong> 页 / 共 <strong style="color: #0f172a;">{{ Math.ceil(auditTotal / auditLimit) || 1 }}</strong> 页</span>
                    <button class="btn ghost compact-btn" style="padding: 4px 12px; border-radius: 6px; background: #fff; border: 1px solid #cbd5e1; color: #334155; cursor: pointer;" :disabled="auditPage >= Math.ceil(auditTotal / auditLimit)" @click="fetchAuditLogs(auditPage + 1)">下一页</button>
                  </div>
                </div>
              </div> <!-- 闭合 v-else -->
            </section>
          </div>

        </div>

      </div>
    </main>

    <!-- 快照 Diff 对比弹窗 -->
    <div v-if="diffModalVisible" class="modal-overlay" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.45); display: flex; align-items: center; justify-content: center; z-index: 9999; backdrop-filter: blur(8px);">
      <div class="modal-card" style="width: 85%; max-width: 1000px; max-height: 85vh; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); animation: modalEnter 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);">
        <div class="modal-header" style="padding: 18px 24px; border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; background: linear-gradient(to bottom, #f8fafc, #ffffff);">
          <div>
            <h4 class="modal-title" style="margin: 0; font-size: 16px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 8px;">🔍 数据快照变更审计</h4>
            <span style="font-size: 12px; color: #64748b; margin-top: 4px; display: block;">单号/资源: <strong style="color: #334155;">{{ selectedLog?.resource_id || '未知' }}</strong> | 操作人: <strong style="color: #334155;">{{ selectedLog?.operator }}</strong></span>
          </div>
          <button style="background: none; border: none; color: #94a3b8; font-size: 24px; cursor: pointer; line-height: 1; transition: color 0.2s;" onmouseover="this.style.color='#0f172a'" onmouseout="this.style.color='#94a3b8'" @click="diffModalVisible = false">×</button>
        </div>
        <div class="modal-body" style="padding: 24px; overflow-y: auto; flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; background: #ffffff;">
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <div style="font-size: 13px; font-weight: 700; color: #dc2626; display: flex; align-items: center; gap: 6px;">
              <span style="width: 8px; height: 8px; border-radius: 50%; background: #dc2626;"></span>
              变更前数据 (Before)
            </div>
            <pre style="background: #fff5f5; border: 1px solid #fca5a5; border-radius: 8px; padding: 16px; margin: 0; font-family: Consolas, Monaco, monospace; font-size: 12px; color: #991b1b; overflow-x: auto; max-height: 450px; white-space: pre-wrap; text-align: left; line-height: 1.6; box-shadow: inset 0 1px 3px rgba(220, 38, 38, 0.02);">{{ selectedLog?.before_value ? JSON.stringify(selectedLog.before_value, null, 2) : '（无原始数据快照 - 属于新增操作）' }}</pre>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <div style="font-size: 13px; font-weight: 700; color: #16a34a; display: flex; align-items: center; gap: 6px;">
              <span style="width: 8px; height: 8px; border-radius: 50%; background: #16a34a;"></span>
              变更后数据 (After)
            </div>
            <pre style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin: 0; font-family: Consolas, Monaco, monospace; font-size: 12px; color: #166534; overflow-x: auto; max-height: 450px; white-space: pre-wrap; text-align: left; line-height: 1.6; box-shadow: inset 0 1px 3px rgba(22, 163, 74, 0.02);">{{ selectedLog?.after_value ? JSON.stringify(selectedLog.after_value, null, 2) : '（无新数据快照 - 属于删除或撤销操作）' }}</pre>
          </div>
        </div>
        <div class="modal-footer" style="padding: 16px 24px; border-top: 1px solid #f1f5f9; display: flex; justify-content: flex-end; gap: 10px; background: #f8fafc;">
          <button class="btn ghost compact-btn" style="padding: 6px 18px; border-radius: 6px; background: #ffffff; border: 1px solid #cbd5e1; color: #334155; cursor: pointer; font-size: 13px; font-weight: 600;" @click="diffModalVisible = false">关闭</button>
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
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh } from './shared'
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
} from '../../daily_report_25_26/services/api'

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
const submissionFilters = ref({
  entityType: '',
  actionType: '',
  operator: '',
  startDate: '',
  endDate: '',
})

// 操作审计日志相关 Ref 变量
const auditLogs = ref([])
const auditTotal = ref(0)
const exportLoading = ref(false)
const auditLoading = ref(false)
const auditPage = ref(1)
const auditLimit = ref(15)
const auditFilters = ref({
  actionType: '',
  operator: '',
  startDate: '',
  endDate: '',
})
const diffModalVisible = ref(false)
const selectedLog = ref(null)

// 操作详情悬浮气泡状态
const activePopoverLog = ref(null)
const popoverStyle = ref({ top: '0px', left: '0px' })

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
const planEditableDays = ref(3)
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
  const section1Ids = demandEntities.value
    .map((item) => String(item.section_1_id || '').trim())
    .filter(Boolean)
  if (!section1Ids.length) {
    selectedBaselineSection1Id.value = ''
    return
  }
  if (!section1Ids.includes(selectedBaselineSection1Id.value)) {
    selectedBaselineSection1Id.value = section1Ids[0]
  }
}

function applyConfig(config) {
  showDate.value = config.show_date || config.biz_date || ''
  usageCollectionDate.value = config.usage_collection_date || ''
  planStartDate.value = config.plan_start_date || showDate.value || ''
  autoUpdatePlanStartDate.value = Boolean(config.auto_update_plan_start_date)
  planEditableDays.value = Number(config.plan_editable_days ?? 3)
  strictPlanningFlowControl.value = config.strict_planning_flow_control ?? true
  supplyEntities.value = cloneRows(config.supply_entities).map(item => ({
    ...item,
    section_1_ids_text: listToText(item.section_1_ids),
  }))
  demandEntities.value = cloneRows(config.demand_entities)
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
  }))
  baselinePresets.value = normalizeBaselineRows(config.baseline_presets)
  weatherApiUrl.value = config.weather_api_url || ''
  weatherProvider.value = config.weather_provider || 'amap'
  amapRestKey.value = config.amap_config?.api_key || ''
  loadWeatherConfig()
}

function getTodayDateString() {
  return new Date().toISOString().slice(0, 10)
}

function handleAutoPlanStartDateChange() {
  if (autoUpdatePlanStartDate.value) {
    planStartDate.value = getTodayDateString()
  }
}

const selectedBaselineSection1Name = computed(() => {
  const matched = demandEntities.value.find((item) => item.section_1_id === selectedBaselineSection1Id.value)
  return matched?.section_1_name || selectedBaselineSection1Id.value || '未选择'
})

const filteredBaselinePresets = computed(() =>
  baselinePresets.value.filter((item) => item.section_1_id === selectedBaselineSection1Id.value),
)

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
    return Boolean(autoUpdatePlanStartDate.value)
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
  if (section === 'weather_api_url') {
    return weatherApiUrl.value || ''
  }
  if (section === 'amap_config') {
    return {
      api_key: amapApiKey.value || '',
      security_code: amapSecurityCode.value || '',
    }
  }
  return null
}

const configPreviewText = computed(() =>
  JSON.stringify(
    {
      show_date: showDate.value || '',
      plan_start_date: planStartDate.value || '',
      auto_update_plan_start_date: Boolean(autoUpdatePlanStartDate.value),
      plan_editable_days: Number(planEditableDays.value ?? 3),
      strict_planning_flow_control: Boolean(strictPlanningFlowControl.value),
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

    if (response.show_date) {
      showDate.value = response.show_date
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
    if (response.show_date) {
      showDate.value = response.show_date
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
    if (autoUpdatePlanStartDate.value) {
      planStartDate.value = getTodayDateString()
    }
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
      data: Boolean(autoUpdatePlanStartDate.value),
    })
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'strict_planning_flow_control',
      data: Boolean(strictPlanningFlowControl.value),
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
    autoUpdatePlanStartDate.value = Boolean(response.config?.auto_update_plan_start_date)
    if (response.plan_editable_days !== undefined) {
      planEditableDays.value = Number(response.plan_editable_days ?? 3)
    }
    setSectionMessage('core_dates', 'success', '核心日期已保存。')
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

function fillMissingPipeModelsForSelectedSection1() {
  const currentSection1 = demandEntities.value.find((item) => item.section_1_id === selectedBaselineSection1Id.value)
  if (!currentSection1) {
    setGlobalMessage('error', '请先选择一个有效需求主体。')
    return
  }
  const existingModelIds = new Set(
    baselinePresets.value
      .filter((item) => item.section_1_id === selectedBaselineSection1Id.value)
      .map((item) => item.pipe_model_id),
  )
  pipeModels.value.forEach((model) => {
    if (!model.pipe_model_id || existingModelIds.has(model.pipe_model_id)) {
      return
    }
    baselinePresets.value.push({
      __row_key: `new::${currentSection1.section_1_id}::${model.pipe_model_id}::${Date.now()}`,
      section_1_id: currentSection1.section_1_id,
      pipe_model_id: model.pipe_model_id,
      design_qty: defaultQtyByPipeModel(model.pipe_model_id),
      purchase_plan_qty: defaultQtyByPipeModel(model.pipe_model_id),
      remark: defaultRemarkByPipeModel(model.pipe_model_id),
    })
  })
  rebuildBaselineRowKeys()
  setSectionMessage('baseline_presets', 'success', '已为当前换热站补齐缺失型号。记得点击“保存本区块”。')
}

onMounted(async () => {
  await loadConfig()
  if (activeTab.value === 'submissions') {
    fetchSubmissionLogs(1)
  }
})

// ==================== 📥 主体数据提交记录 JS 业务逻辑 ====================

async function fetchSubmissionLogs(page = 1) {
  submissionLoading.value = true
  submissionPage.value = page
  try {
    const res = await getTubeSubmissionLogs(PROJECT_KEY, {
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
  } catch (error) {
    console.error('加载主体提交数据记录失败:', error)
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

// ==================== 📜 操作审计日志 JS 业务逻辑 ====================

async function fetchAuditLogs(page = 1) {
  auditLoading.value = true
  auditPage.value = page
  try {
    const res = await getTubeAuditLogs(PROJECT_KEY, {
      actionType: auditFilters.value.actionType,
      operator: auditFilters.value.operator,
      startDate: auditFilters.value.startDate,
      endDate: auditFilters.value.endDate,
      page: auditPage.value,
      limit: auditLimit.value,
    })
    auditLogs.value = res.rows || []
    auditTotal.value = res.total || 0
  } catch (error) {
    console.error('加载操作审计日志失败:', error)
  } finally {
    auditLoading.value = false
  }
}

function showDiffModal(log) {
  selectedLog.value = log
  diffModalVisible.value = true
}

function togglePopover(event, log) {
  if (activePopoverLog.value && activePopoverLog.value.id === log.id) {
    activePopoverLog.value = null
    return
  }
  activePopoverLog.value = log
  
  const rect = event.currentTarget.getBoundingClientRect()
  
  // 气泡定位在单元格上方居中，直接使用相对于视口的 rect.top 和 rect.left (对应 position: fixed 展现)
  popoverStyle.value = {
    top: `${rect.top - 8}px`,
    left: `${rect.left + rect.width / 2}px`,
    transform: 'translate(-50%, -100%)',
  }
}

watch(activeTab, () => {
  activePopoverLog.value = null
})

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
    CONFIRM_ARRIVAL: '👷 确认到货',
    CONFIRM_CONSTRUCTION: '👷 施工接收',
    CONFIRM_WAREHOUSE: '🏢 库管确认',
    SAVE_PLAN: '📅 更新三日计划',
    SUBMIT_USAGE: '🔋 上报消耗损耗',
    SUBMIT_STATUS: '✅ 提交填报状态',
    UPDATE_CONFIG: '⚙️ 配置修改',
    SUPER_UPDATE_DELIVERY: '🚨 超管强改',
  }
  return dict[type] || type
}

function getActionTypeBadgeStyle(type) {
  const colors = {
    CREATE_DELIVERY: { bg: '#e8f4fd', color: '#1d88e5' },
    CANCEL_DELIVERY: { bg: '#fde8e8', color: '#e53935' },
    CONFIRM_ARRIVAL: { bg: '#fef3d6', color: '#f5b000' },
    CONFIRM_CONSTRUCTION: { bg: '#e8f7f0', color: '#2dca73' },
    CONFIRM_WAREHOUSE: { bg: '#f4eafc', color: '#8e44ad' },
    SAVE_PLAN: { bg: '#e8f4fd', color: '#1d88e5' },
    SUBMIT_USAGE: { bg: '#fef3d6', color: '#f5b000' },
    SUBMIT_STATUS: { bg: '#e8f7f0', color: '#2dca73' },
    UPDATE_CONFIG: { bg: '#f4f5f7', color: '#5a6b82' },
    SUPER_UPDATE_DELIVERY: { bg: '#fde8e8', color: '#e53935' },
  }
  const match = colors[type] || { bg: '#f4f5f7', color: '#5a6b82' }
  return {
    backgroundColor: match.bg,
    color: match.color,
  }
}

async function handleExportLogs() {
  exportLoading.value = true
  try {
    const blob = await exportTubeAuditLogs(PROJECT_KEY, {
      actionType: auditFilters.value.actionType,
      operator: auditFilters.value.operator,
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
    a.download = `operation_logs_${timestamp}.csv`
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
.baseline-summary { margin-top: 0; margin-bottom: 12px; }
.summary-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #eef2ff;
  color: #334155;
  font-size: 13px;
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
.baseline-table {
  min-width: 920px;
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
  grid-column: span 2;
  display: flex;
  align-items: flex-end;
  min-width: 0;
}
.submission-query-btn {
  width: 100%;
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 18px;
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
</style>
