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
            <span class="meta-label">供给主体数</span>
            <strong class="meta-value">{{ supplyEntities.length }} 个注册主体</strong>
          </div>
          <div class="meta-card">
            <span class="meta-label">管理的换热站</span>
            <strong class="meta-value">{{ demandEntities.length }} 个运营站点</strong>
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
            <span class="meta-label">换热站提交状态</span>
            <strong class="meta-value highlight-num">{{ submittedStationCount }} / {{ demandEntities.length }} 站已提交</strong>
          </div>
        </div>
      </section>

      <!-- 纵向双栏侧边控制台 -->
      <div class="admin-workbench-layout">
        
        <!-- 左侧纵向选项卡菜单 -->
        <aside class="admin-sidebar">
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'core' }]" 
            @click="activeTab = 'core'"
          >
            ⚙️ 核心参数与状态
          </button>
          <button 
            type="button" 
            :class="['sidebar-tab-btn', { active: activeTab === 'station' }]" 
            @click="activeTab = 'station'"
          >
            📍 换热站基础台账
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
            :class="['sidebar-tab-btn', { active: activeTab === 'json' }]" 
            @click="activeTab = 'json'"
          >
            💻 原始 JSON 预览
          </button>
        </aside>

        <!-- 右侧当前选中的配置主卡片 -->
        <div class="admin-content-pane">
          
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
              <div class="field-grid">
                <label class="field">
                  <span>展示/业务日期 (show_date)</span>
                  <input v-model="showDate" type="date" class="input" />
                </label>
                <label class="field">
                  <span>滚动计划起始日期 (plan_start_date)</span>
                  <input v-model="planStartDate" type="date" class="input" :disabled="autoUpdatePlanStartDate" />
                  <small class="field-help">开启自动更新后，该日期会随真实日期自动变化。</small>
                </label>
                <label class="field">
                  <span>起始日期是否自动随今天变化</span>
                  <select v-model="autoUpdatePlanStartDate" class="input" @change="handleAutoPlanStartDateChange">
                    <option :value="false">否 (手动维护起始日期)</option>
                    <option :value="true">是 (每天随日期自动后移)</option>
                  </select>
                </label>
                <label class="field">
                  <span>计划可填报修改天数 (plan_editable_days)</span>
                  <input v-model.number="planEditableDays" class="input" type="number" min="0" max="3" step="1" />
                  <small class="field-help">`3`为三天都可改，`2`为最后两天可改，`0`为不可填报。</small>
                </label>
              </div>
              <p v-if="sectionMessage('core_dates')" :class="['section-tip', sectionMessage('core_dates').type]">
                {{ sectionMessage('core_dates').text }}
              </p>
            </section>

            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">换热站昨日提交状态审计</div>
                  <p class="sub block-sub">审计昨日三日计划上报进度，判断昨日消耗数据及滚动计划是否全部锁盘入库。</p>
                </div>
              </div>
              <div class="table-wrap">
                <table class="table editor-table submission-table">
                  <thead>
                    <tr>
                      <th>换热站</th>
                      <th>提交状态</th>
                      <th>最近一次提交日期</th>
                      <th>提交完成物理时间</th>
                      <th>现场填报人</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in submissionStatusRows" :key="item.station_id">
                      <td class="cell-text" :title="item.station_name || item.station_id">{{ item.station_name || item.station_id }}</td>
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

          <!-- Tab 2: 换热站基础台账 -->
          <div v-if="activeTab === 'station'" class="pane-content-wrapper">
            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">换热站基础档案信息</div>
                  <p class="sub block-sub">管理保温管物理覆盖的所有换热站点、地理区域及标段映射。</p>
                </div>
                <div class="section-actions">
                  <button class="btn ghost" type="button" @click="addDemandEntity">➕ 新增站点</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('demand_entities')" @click="saveSection('demand_entities')">
                    {{ isSaving('demand_entities') ? '正在同步…' : '💾 保存站点台账' }}
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
                      <th>换热站ID (唯一)</th>
                      <th>换热站编码</th>
                      <th>换热站名称</th>
                      <th>管线所属区域</th>
                      <th>所属施工标段</th>
                      <th>当前施工状态</th>
                      <th>物理移除</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in demandEntities" :key="`${item.station_id || 'new'}-${index}`">
                      <td><input v-model.trim="item.station_id" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.code" class="input table-cell-input" type="text" maxlength="8" placeholder="如 AA" /></td>
                      <td><input v-model.trim="item.station_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.region" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.section" class="input table-cell-input" type="text" /></td>
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
                      <th>发货联系人</th>
                      <th>联系电话</th>
                      <th>物理移除</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in supplyEntities" :key="`${item.entity_id || 'new'}-${index}`">
                      <td><input v-model.trim="item.entity_id" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.code" class="input table-cell-input" type="text" maxlength="8" placeholder="如 SA" /></td>
                      <td><input v-model.trim="item.entity_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.contact_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.contact_phone" class="input table-cell-input" type="text" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(supplyEntities, index)">删除</button></td>
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
                    <tr v-for="(item, index) in pipeModels" :key="`${item.pipe_model_id || 'new'}-${index}`">
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
                    <tr v-for="(item, index) in productionCapacities" :key="`${item.supply_entity_name || 'supplier'}-${item.pipe_model_name || 'model'}-${index}`">
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
                  <p class="sub block-sub">授权不同负责人账号所分管的换热站列表。多个换热站请用英文逗号(,)分隔。</p>
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
                      <th>所分管的换热站ID列表 (逗号分隔)</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in managerAssignments" :key="`${item.manager_id || 'new'}-${index}`">
                      <td><input v-model.trim="item.manager_id" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.manager_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.station_ids_text" class="input table-cell-input" type="text" placeholder="如 station_a, station_b" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(managerAssignments, index)">删除</button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section class="card elevated section-card">
              <div class="card-header-row">
                <div>
                  <div class="card-header">施工分包单位及站点映射</div>
                  <p class="sub block-sub">配置各施工标段分包商基本联络方式及分管站点。多个换热站请用英文逗号(,)分隔。</p>
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
                      <th>分管的换热站ID列表 (逗号分隔)</th>
                      <th>操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, index) in constructionUnits" :key="`${item.unit_id || 'new'}-${index}`">
                      <td><input v-model.trim="item.unit_id" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.unit_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.contact_name" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.contact_phone" class="input table-cell-input" type="text" /></td>
                      <td><input v-model.trim="item.station_ids_text" class="input table-cell-input" type="text" placeholder="如 station_a, station_c" /></td>
                      <td><button class="btn danger-ghost compact-btn" type="button" @click="removeRow(constructionUnits, index)">删除</button></td>
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
                  <div class="card-header">换热站管线基准设计量</div>
                  <p class="sub block-sub">维护特定换热站的设计基准总量及计划采购总量，用以评估物流净缺口。请先选择站点过滤。</p>
                </div>
                <div class="section-actions baseline-actions-panel">
                  <div class="station-filter-inline">
                    <span>过滤站点：</span>
                    <select v-model="selectedBaselineStationId" class="input inline-select">
                      <option v-for="station in demandEntities" :key="station.station_id" :value="station.station_id">
                        {{ station.station_name || station.station_id }}
                      </option>
                    </select>
                  </div>
                  <button class="btn ghost" type="button" @click="addBaselinePreset">➕ 新增型号行</button>
                  <button class="btn ghost btn-action-tool" type="button" @click="fillMissingPipeModelsForSelectedStation">补齐缺失规格</button>
                  <button class="btn primary shadow-accent" type="button" :disabled="isSaving('baseline_presets')" @click="saveSection('baseline_presets')">
                    {{ isSaving('baseline_presets') ? '保存中…' : '💾 保存设计基准' }}
                  </button>
                </div>
              </div>
              <p v-if="sectionMessage('baseline_presets')" :class="['section-tip', sectionMessage('baseline_presets').type]">
                {{ sectionMessage('baseline_presets').text }}
              </p>
              <div class="summary-row baseline-summary">
                <span class="summary-chip">当前站点：{{ selectedBaselineStationName }}</span>
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
                          <option v-for="model in pipeModels" :key="model.pipe_model_id" :value="model.pipe_model_id">
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

        </div>

      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { AppHeader, Breadcrumbs, useTubePageShell, useTubeRealtimeRefresh } from './shared'
import {
  getTubeGlobalManagementConfig,
  saveTubeGlobalManagementConfig,
  saveTubeGlobalManagementConfigSection,
} from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'

const {
  loading,
  errorMessage,
  breadcrumbItems,
  goProjectPages,
} = useTubePageShell('全局管理入口')

const configPath = ref('')
const activeTab = ref('core')
const showDate = ref('')
const planStartDate = ref('')
const autoUpdatePlanStartDate = ref(false)
const planEditableDays = ref(3)
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
const baselinePresets = ref([])
const submissionStatusPath = ref('')
const latestSubmissions = ref([])
const historySubmissions = ref([])
const selectedBaselineStationId = ref('')

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
  const bucket = resolvePipeModelBucket(pipeModelCode)
  if (bucket === 'medium') return 160
  if (bucket === 'large') return 260
  return 240
}

function defaultRemarkByPipeModel(pipeModelCode) {
  const bucket = resolvePipeModelBucket(pipeModelCode)
  if (bucket === 'medium') return '演示预设-中管径偏低'
  if (bucket === 'large') return '演示预设-大管径偏高'
  return '演示预设-小口径偏高'
}

function normalizeAssignmentRows(rows, idKey, nameKey) {
  return cloneRows(rows).map((item) => ({
    ...item,
    station_ids_text: listToText(item.station_ids),
    [idKey]: item[idKey] || '',
    [nameKey]: item[nameKey] || '',
  }))
}

function normalizeBaselineRows(rows) {
  return cloneRows(rows).map((item, index) => ({
    ...item,
    pipe_model_id: normalizePipeModelCode(item.pipe_model_id),
    pipe_model_name: normalizePipeModelCode(item.pipe_model_name || item.pipe_model_id),
    __row_key: `${item.station_id || 'station'}::${normalizePipeModelCode(item.pipe_model_id) || 'model'}::${index}`,
    design_qty: Number(item.design_qty || 0),
    purchase_plan_qty: Number(item.purchase_plan_qty || 0),
    remark: item.remark || '',
  }))
}

function normalizeSubmissionRows(rows) {
  return cloneRows(rows).map((item) => ({
    station_id: item.station_id || '',
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
    __row_key: `${item.station_id || 'station'}::${normalizePipeModelCode(item.pipe_model_id) || 'model'}::${index}`,
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

function syncSelectedBaselineStation() {
  const stationIds = demandEntities.value
    .map((item) => String(item.station_id || '').trim())
    .filter(Boolean)
  if (!stationIds.length) {
    selectedBaselineStationId.value = ''
    return
  }
  if (!stationIds.includes(selectedBaselineStationId.value)) {
    selectedBaselineStationId.value = stationIds[0]
  }
}

function applyConfig(config) {
  configPath.value = configPath.value || ''
  showDate.value = config.show_date || config.biz_date || ''
  planStartDate.value = config.plan_start_date || showDate.value || ''
  autoUpdatePlanStartDate.value = Boolean(config.auto_update_plan_start_date)
  planEditableDays.value = Number(config.plan_editable_days ?? 3)
  supplyEntities.value = cloneRows(config.supply_entities)
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
  baselinePresets.value = normalizeBaselineRows(config.baseline_presets)
  syncSelectedBaselineStation()
}

function getTodayDateString() {
  return new Date().toISOString().slice(0, 10)
}

function handleAutoPlanStartDateChange() {
  if (autoUpdatePlanStartDate.value) {
    planStartDate.value = getTodayDateString()
  }
}

const selectedBaselineStationName = computed(() => {
  const matched = demandEntities.value.find((item) => item.station_id === selectedBaselineStationId.value)
  return matched?.station_name || selectedBaselineStationId.value || '未选择'
})

const filteredBaselinePresets = computed(() =>
  baselinePresets.value.filter((item) => item.station_id === selectedBaselineStationId.value),
)

const submissionStatusRows = computed(() => {
  const latestByStationId = new Map(
    latestSubmissions.value
      .filter((item) => item.station_id)
      .map((item) => [String(item.station_id), item]),
  )
  return demandEntities.value.map((station) => {
    const stationId = String(station.station_id || '')
    const latest = latestByStationId.get(stationId) || {}
    const dataSubmitDate = String(latest.data_submit_date || '')
    return {
      station_id: stationId,
      station_name: station.station_name || stationId,
      data_submit_date: dataSubmitDate,
      submitted_at: latest.submitted_at || '',
      submitted_by: latest.submitted_by || '',
      is_submitted: Boolean(dataSubmitDate && planStartDate.value && dataSubmitDate === planStartDate.value),
    }
  })
})

const submittedStationCount = computed(() => submissionStatusRows.value.filter((item) => item.is_submitted).length)
const pendingStationCount = computed(() => submissionStatusRows.value.filter((item) => !item.is_submitted).length)

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
  if (section === 'supply_entities') {
    return supplyEntities.value.map((item) => ({
      entity_id: item.entity_id || '',
      code: String(item.code || '').trim().toUpperCase(),
      entity_name: item.entity_name || '',
      contact_name: item.contact_name || '',
      contact_phone: item.contact_phone || '',
    }))
  }
  if (section === 'demand_entities') {
    return demandEntities.value.map((item) => ({
      station_id: item.station_id || '',
      code: String(item.code || '').trim().toUpperCase(),
      station_name: item.station_name || '',
      region: item.region || '',
      section: item.section || '',
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
      station_ids: textToList(item.station_ids_text),
    }))
  }
  if (section === 'construction_units') {
    return constructionUnits.value.map((item) => ({
      unit_id: item.unit_id || '',
      unit_name: item.unit_name || '',
      contact_name: item.contact_name || '',
      contact_phone: item.contact_phone || '',
      station_ids: textToList(item.station_ids_text),
    }))
  }
  if (section === 'baseline_presets') {
    return baselinePresets.value.map((item) => ({
      station_id: item.station_id || '',
      station_name: item.station_name || '',
      pipe_model_id: normalizePipeModelCode(item.pipe_model_id),
      pipe_model_name: resolvePipeModelById(item.pipe_model_id)?.pipe_model_name || normalizePipeModelCode(item.pipe_model_name || item.pipe_model_id),
      design_qty: Number(item.design_qty || 0),
      purchase_plan_qty: Number(item.purchase_plan_qty || 0),
      remark: item.remark || '',
    }))
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
      supply_entities: buildSectionPayload('supply_entities'),
      demand_entities: buildSectionPayload('demand_entities'),
      pipe_models: buildSectionPayload('pipe_models'),
      production_capacities: buildSectionPayload('production_capacities'),
      manager_assignments: buildSectionPayload('manager_assignments'),
      construction_units: buildSectionPayload('construction_units'),
      baseline_presets: buildSectionPayload('baseline_presets'),
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
    configPath.value = response.config_path || ''
    submissionStatusPath.value = response.submission_status_path || ''
    latestSubmissions.value = normalizeSubmissionRows(response.submission_status?.latest_submissions || [])
    historySubmissions.value = normalizeSubmissionRows(response.submission_status?.history_submissions || [])
    applyConfig(config)
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
    configPath.value = response.config_path || configPath.value
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
      section: 'plan_start_date',
      data: planStartDate.value || '',
    })
    await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'auto_update_plan_start_date',
      data: Boolean(autoUpdatePlanStartDate.value),
    })
    const response = await saveTubeGlobalManagementConfigSection(PROJECT_KEY, {
      section: 'plan_editable_days',
      data: Number(planEditableDays.value ?? 3),
    })
    applyConfig(response.config || {})
    if (response.show_date) {
      showDate.value = response.show_date
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

function addSupplyEntity() {
  supplyEntities.value.push({
    entity_id: '',
    code: '',
    entity_name: '',
    contact_name: '',
    contact_phone: '',
  })
}

function addDemandEntity() {
  demandEntities.value.push({
    station_id: '',
    code: '',
    station_name: '',
    region: '',
    section: '',
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
    station_ids_text: '',
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
    station_ids_text: '',
  })
}

function resolvePipeModelById(pipeModelId) {
  const normalizedCode = normalizePipeModelCode(pipeModelId)
  return pipeModels.value.find((item) => normalizePipeModelCode(item.pipe_model_id) === normalizedCode) || null
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
  const currentStation = demandEntities.value.find((item) => item.station_id === selectedBaselineStationId.value)
  const firstModel = pipeModels.value[0] || null
  baselinePresets.value.push({
    __row_key: `new::${Date.now()}`,
    station_id: selectedBaselineStationId.value || '',
    station_name: currentStation?.station_name || '',
    pipe_model_id: firstModel?.pipe_model_id || '',
    pipe_model_name: firstModel?.pipe_model_name || '',
    design_qty: defaultQtyByPipeModel(firstModel?.pipe_model_id),
    purchase_plan_qty: defaultQtyByPipeModel(firstModel?.pipe_model_id),
    remark: defaultRemarkByPipeModel(firstModel?.pipe_model_id),
  })
  rebuildBaselineRowKeys()
}

function removeBaselinePreset(rowKey) {
  baselinePresets.value = baselinePresets.value.filter((item) => item.__row_key !== rowKey)
  rebuildBaselineRowKeys()
}

function fillMissingPipeModelsForSelectedStation() {
  const currentStation = demandEntities.value.find((item) => item.station_id === selectedBaselineStationId.value)
  if (!currentStation) {
    setGlobalMessage('error', '请先选择一个有效换热站。')
    return
  }
  const existingModelIds = new Set(
    baselinePresets.value
      .filter((item) => item.station_id === selectedBaselineStationId.value)
      .map((item) => item.pipe_model_id),
  )
  pipeModels.value.forEach((model) => {
    if (!model.pipe_model_id || existingModelIds.has(model.pipe_model_id)) {
      return
    }
    baselinePresets.value.push({
      __row_key: `new::${currentStation.station_id}::${model.pipe_model_id}::${Date.now()}`,
      station_id: currentStation.station_id,
      station_name: currentStation.station_name || currentStation.station_id,
      pipe_model_id: model.pipe_model_id,
      pipe_model_name: model.pipe_model_name || model.pipe_model_id,
      design_qty: defaultQtyByPipeModel(model.pipe_model_id),
      purchase_plan_qty: defaultQtyByPipeModel(model.pipe_model_id),
      remark: defaultRemarkByPipeModel(model.pipe_model_id),
    })
  })
  rebuildBaselineRowKeys()
  setSectionMessage('baseline_presets', 'success', '已为当前换热站补齐缺失型号。记得点击“保存本区块”。')
}

onMounted(() => {
  loadConfig()
})

useTubeRealtimeRefresh(loadConfig)
</script>

<style scoped>
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
</style>
