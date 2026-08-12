<template>
  <div class="history-query-view page-layout" @click="activeDropdown = null">
    <AppHeader />
    <main class="page-main container">
      <!-- 统一面包屑导航 -->
      <Breadcrumbs :items="breadcrumbItems" />
      
      <div v-if="loading && !configSummary" class="loading-state">系统数据加载中...</div>
      <div v-else-if="errorMessage" class="error-state">{{ errorMessage }}</div>
      <div v-else class="page-content">
        <!-- 头部导航或说明 -->
        <header class="page-title-row">
          <div class="title-wrap">
            <h2>📊 历史数据查询</h2>
            <p class="subtitle">历史时段内需求主体与供给侧的计划、消耗、到货及管件发货历史明细与多维透视</p>
          </div>
          <button class="btn ghost back-btn" type="button" @click="goProjectPages">
            ← 返回项目主页
          </button>
        </header>

        <!-- 选项卡 Pills 切换 -->
        <div class="history-tab-bar">
          <button
            type="button"
            :class="['tab-pill-btn', { active: activeTab === 'pipe' }]"
            @click="activeTab = 'pipe'"
          >
            🔥 保温管历史数据
          </button>
          <button
            type="button"
            :class="['tab-pill-btn', { active: activeTab === 'fitting' }]"
            @click="activeTab = 'fitting'"
          >
            🔧 管件发货历史数据
          </button>
        </div>

        <!-- 1. 保温管历史数据 Tab -->
        <section v-if="activeTab === 'pipe'" class="card elevated section-card">
          <div class="card-header-row">
            <div>
              <div class="card-header">📊 需求主体填报与到货历史数据查询</div>
              <p class="sub block-sub">查询各需求主体每日保温管计划量、实际消耗、确认到货量及运输在途时长，包含时段内汇总统计。</p>
            </div>
          </div>
          
          <!-- 过滤查询栏 -->
          <div class="filter-panel" style="display: flex; gap: 15px; margin-bottom: 20px; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; flex-wrap: wrap;">
            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px; position: relative;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">选择需求主体 (可勾选多选)</label>
              <div 
                class="custom-select-trigger" 
                style="min-width: 210px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; height: 32px; padding: 0 10px; font-size: 13px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; user-select: none;"
                @click.stop="toggleDropdown('historySection1')"
              >
                <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 170px;">{{ historySection1TriggerText }}</span>
                <span style="font-size: 10px; color: #94a3b8;">▼</span>
              </div>

              <div 
                v-if="activeDropdown === 'historySection1'" 
                class="custom-dropdown-panel"
                style="position: absolute; top: 58px; left: 0; min-width: 240px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.05); z-index: 100; padding: 8px 0;"
                @click.stop
              >
                <div style="display: flex; justify-content: space-between; padding: 4px 12px 8px; border-bottom: 1px solid #f1f5f9; font-size: 12px;">
                  <button type="button" style="color: #2563eb; background: none; border: none; cursor: pointer; padding: 0; font-weight: 500;" @click="selectAllHistorySection1">✓ 全选</button>
                  <button type="button" style="color: #64748b; background: none; border: none; cursor: pointer; padding: 0;" @click="clearHistorySection1">✕ 清空</button>
                </div>
                <div style="max-height: 200px; overflow-y: auto; padding: 4px 0;">
                  <label 
                    v-for="st in demandEntities" 
                    :key="st.section_1_id" 
                    style="display: flex; align-items: center; gap: 8px; padding: 6px 12px; font-size: 13px; color: #334155; cursor: pointer;"
                  >
                    <input type="checkbox" :value="st.section_1_id" v-model="historyFilter.section1Ids" style="cursor: pointer;" />
                    <span>{{ st.section_1_name }}</span>
                  </label>
                </div>
              </div>
            </div>
            
            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">开始日期</label>
              <input v-model="historyFilter.startDate" class="input" type="date" style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
            </div>
            
            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">结束日期</label>
              <input v-model="historyFilter.endDate" class="input" type="date" style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
            </div>

            <div class="filter-item" style="display: flex; gap: 8px; align-self: flex-end; margin-left: auto;">
              <button class="btn primary" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 5px; cursor: pointer;" @click="handleHistoryQuery">
                🔍 查询
              </button>
              <button class="btn ghost" :disabled="historyExportLoading" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 5px; border-color: #cbd5e1; cursor: pointer; background: #fff;" @click="handleHistoryExport">
                <span>{{ historyExportLoading ? '正在导出...' : '📥 导出台账 (.xlsx)' }}</span>
              </button>
            </div>
          </div>

          <!-- 历史数据明细列表 -->
          <div v-if="historyLoading" class="loading-placeholder" style="padding: 40px; text-align: center; color: #64748b;">数据加载中...</div>
          <div v-else-if="historyRows.length === 0" class="empty-placeholder" style="padding: 40px; text-align: center; color: #777;">未查询到任何历史记录。</div>
          <div v-else>
            <div class="table-wrap" style="max-height: 550px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
              <table class="table editor-table" style="margin: 0; width: 100%; border-collapse: collapse;">
                <thead>
                  <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 10;">
                    <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">日期</th>
                    <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">需求主体</th>
                    <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">包含管材型号概览</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">当日总计划量 (米)</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">当日总发货量 (米)</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">当日总使用量 (米)</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">当日总损耗量 (米)</th>
                    <th style="text-align: right; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">确认总到货量 (米)</th>
                    <th style="text-align: left; padding: 12px 16px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">平均在途时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr 
                    v-for="(row, idx) in groupedHistoryRows" 
                    :key="idx" 
                    style="border-bottom: 1px solid #e2e8f0; transition: background-color 0.2s; cursor: pointer;" 
                    onmouseover="this.style.backgroundColor='#f1f5f9'" 
                    onmouseout="this.style.backgroundColor='transparent'"
                    @click="openPipeDetailModal(row)"
                  >
                    <td style="padding: 12px 16px; vertical-align: middle; color: #475569; font-size: 13px; font-weight: 500;">{{ row.biz_date }}</td>
                    <td style="padding: 12px 16px; vertical-align: middle; color: #1e293b; font-size: 13px; font-weight: 600;">{{ row.section_1_name }}</td>
                    <td style="padding: 12px 16px; vertical-align: middle; color: #334155; font-size: 13px; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" :title="`${row.pipe_models_summary} (点击可查看分型号数据)`">
                      <span style="background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px; font-weight: 600;">{{ row.models.length }}个型号</span>
                      <span>{{ row.pipe_models_summary }}</span>
                    </td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #475569;">{{ formatQty(row.plan_qty) }}</td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #0284c7;">{{ formatQty(row.shipped_qty) }}</td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #16a34a;">{{ formatQty(row.usage_qty) }}</td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #dc2626;">{{ formatQty(row.loss_qty) }}</td>
                    <td style="text-align: right; padding: 12px 16px; vertical-align: middle; font-weight: 500; font-size: 13px; color: #2563eb;">{{ formatQty(row.arrived_qty) }}</td>
                    <td style="padding: 12px 16px; vertical-align: middle; color: #475569; font-size: 13px;">
                      {{ row.arrived_batch_count > 0 ? formatSeconds(row.total_transit_seconds / row.arrived_batch_count) : '-' }}
                    </td>
                  </tr>
                  
                  <!-- 汇总统计行 -->
                  <tr style="background: #f1f5f9; font-weight: bold; border-top: 2px solid #cbd5e1; position: sticky; bottom: 0; z-index: 5;">
                    <td colspan="3" style="padding: 14px 16px; font-size: 13px; color: #1e293b; background: #f1f5f9;">📊 历史时段内汇总统计</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #1e293b; background: #f1f5f9;">{{ formatQty(totalPlan) }}</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #0284c7; background: #f1f5f9;">{{ formatQty(totalShipped) }}</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #16a34a; background: #f1f5f9;">{{ formatQty(totalUsage) }}</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #dc2626; background: #f1f5f9;">{{ formatQty(totalLoss) }}</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 13px; color: #2563eb; background: #f1f5f9;">{{ formatQty(totalArrived) }}</td>
                    <td style="padding: 14px 16px; font-size: 13px; color: #1e293b; background: #f1f5f9;">{{ overallAvgTransit }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 决策辅助透视 -->
            <div v-if="historyRows.length > 0" style="margin-top: 15px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 16px; border-radius: 6px; font-size: 13px; color: #334155; line-height: 1.8;">
              <div style="font-weight: 700; color: #0f172a; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                <span>💡 历史时段决策透视数据：</span>
              </div>
              <div style="display: flex; flex-wrap: wrap; gap: 10px 30px;">
                <span>🟢 物资综合保障率：<strong style="color: #0f172a;">{{ fulfillmentRate }}</strong> (计划 {{ formatQty(totalPlan) }} 米 / 到货 {{ formatQty(totalArrived) }} 米)</span>
                <span>📦 累计发货总量：<strong style="color: #0284c7;">{{ formatQty(totalShipped) }} 米</strong></span>
                <span>📅 计划消耗契合度：<strong style="color: #0f172a;">{{ planUsageAlignment }}</strong> (实际消耗 {{ formatQty(totalUsage) }} 米 / 计划 {{ formatQty(totalPlan) }} 米)</span>
                <span>🔴 施工综合损耗率：<strong style="color: #dc2626;">{{ lossRate }}</strong> (消耗 {{ formatQty(totalUsage) }} 米 / 损耗 {{ formatQty(totalLoss) }} 米)</span>
                <span>🔵 施工消耗强度：<strong style="color: #2563eb;">{{ dailyConsumption }} 米/天</strong> (实际施工 {{ activeDays }} 天)</span>
                <span>🚚 物流配送效率区间：最快 <strong style="color: #16a34a;">{{ minTransit }}</strong> / 最慢 <strong style="color: #ea580c;">{{ maxTransit }}</strong> (平均 {{ overallAvgTransit }})</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 2. 管件发货历史数据 Tab -->
        <section v-else-if="activeTab === 'fitting'" class="card elevated section-card">
          <div class="card-header-row">
            <div>
              <div class="card-header">🔧 供给侧管件发货历史台账与明细查询</div>
              <p class="sub block-sub">多维查询弯头、三通、大小头等各规格管件的发货时间、车牌号、接收标段及全生命周期流转记录。</p>
            </div>
          </div>

          <!-- 管件多维过滤查询栏 -->
          <div class="filter-panel" style="display: flex; gap: 15px; margin-bottom: 20px; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; flex-wrap: wrap;">
            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">供给主体</label>
              <select v-model="fittingFilter.supplyEntityId" class="select" style="min-width: 150px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; height: 32px; padding: 0 8px; font-size: 13px;">
                <option value="">— 全部供给主体 —</option>
                <option v-for="ent in supplyEntitiesOptions" :key="ent.entity_id" :value="ent.entity_id">
                  {{ ent.entity_name }} ({{ ent.entity_id }})
                </option>
              </select>
            </div>

            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px; position: relative;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">接收标段 (可勾选多选)</label>
              <div 
                class="custom-select-trigger" 
                style="min-width: 210px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; height: 32px; padding: 0 10px; font-size: 13px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; user-select: none;"
                @click.stop="toggleDropdown('fittingSection1')"
              >
                <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 170px;">{{ fittingSection1TriggerText }}</span>
                <span style="font-size: 10px; color: #94a3b8;">▼</span>
              </div>

              <div 
                v-if="activeDropdown === 'fittingSection1'" 
                class="custom-dropdown-panel"
                style="position: absolute; top: 58px; left: 0; min-width: 240px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.05); z-index: 100; padding: 8px 0;"
                @click.stop
              >
                <div style="display: flex; justify-content: space-between; padding: 4px 12px 8px; border-bottom: 1px solid #f1f5f9; font-size: 12px;">
                  <button type="button" style="color: #2563eb; background: none; border: none; cursor: pointer; padding: 0; font-weight: 500;" @click="selectAllFittingSection1">✓ 全选</button>
                  <button type="button" style="color: #64748b; background: none; border: none; cursor: pointer; padding: 0;" @click="clearFittingSection1">✕ 清空</button>
                </div>
                <div style="max-height: 200px; overflow-y: auto; padding: 4px 0;">
                  <label 
                    v-for="st in demandEntities" 
                    :key="st.section_1_id" 
                    style="display: flex; align-items: center; gap: 8px; padding: 6px 12px; font-size: 13px; color: #334155; cursor: pointer;"
                  >
                    <input type="checkbox" :value="st.section_1_id" v-model="fittingFilter.section1Ids" style="cursor: pointer;" />
                    <span>{{ st.section_1_name }}</span>
                  </label>
                </div>
              </div>
            </div>

            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">开始日期</label>
              <input v-model="fittingFilter.startDate" class="input" type="date" style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
            </div>

            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">结束日期</label>
              <input v-model="fittingFilter.endDate" class="input" type="date" style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 8px; font-size: 13px;" />
            </div>

            <div class="filter-item" style="display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 200px;">
              <label style="font-size: 12px; color: #64748b; font-weight: 500;">关键字检索</label>
              <input v-model="fittingFilter.searchKeyword" class="input" type="text" placeholder="车牌/发货单号/类型/型号/备注..." style="height: 32px; background: #fff; color: #334155; border: 1px solid #cbd5e1; border-radius: 6px; padding: 0 10px; font-size: 13px;" @keyup.enter="handleFittingQuery" />
            </div>

            <div class="filter-item" style="display: flex; gap: 8px; align-self: flex-end;">
              <button class="btn primary" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 5px; cursor: pointer;" @click="handleFittingQuery">
                🔍 查询
              </button>
              <button class="btn ghost" :disabled="fittingExportLoading" style="height: 32px; padding: 0 16px; border-radius: 6px; font-size: 13px; display: flex; align-items: center; gap: 5px; border-color: #cbd5e1; cursor: pointer; background: #fff;" @click="handleFittingExport">
                <span>{{ fittingExportLoading ? '正在导出...' : '📥 导出台账 (.xlsx)' }}</span>
              </button>
            </div>
          </div>

          <!-- 管件发货历史表格 -->
          <div v-if="fittingLoading" class="loading-placeholder" style="padding: 40px; text-align: center; color: #64748b;">管件数据加载中...</div>
          <div v-else-if="fittingRows.length === 0" class="empty-placeholder" style="padding: 40px; text-align: center; color: #777;">未查询到符合条件的管件发货历史记录。</div>
          <div v-else>
            <div class="table-wrap" style="max-height: 550px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
              <table class="table editor-table" style="margin: 0; width: 100%; border-collapse: collapse;">
                <thead>
                  <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 10;">
                    <th style="text-align: left; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">发货时间</th>
                    <th style="text-align: left; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">发货单号</th>
                    <th style="text-align: left; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">车牌号</th>
                    <th style="text-align: left; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">供给主体</th>
                    <th style="text-align: left; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">接收标段</th>
                    <th style="text-align: left; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">管件类型</th>
                    <th style="text-align: left; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc; min-width: 200px;">型号/规格</th>
                    <th style="text-align: right; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">发货数量</th>
                    <th style="text-align: left; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">备注</th>
                    <th style="text-align: center; padding: 12px 14px; color: #475569; font-weight: 600; font-size: 13px; background: #f8fafc;">流转凭证</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in fittingRows" :key="row.id" style="border-bottom: 1px solid #e2e8f0; transition: background-color 0.2s;" onmouseover="this.style.backgroundColor='#f8fafc'" onmouseout="this.style.backgroundColor='transparent'">
                    <td style="padding: 10px 14px; vertical-align: middle; color: #475569; font-size: 12.5px; font-family: monospace;">{{ formatDateTimeDisplay(row.shipped_at) }}</td>
                    <td style="padding: 10px 14px; vertical-align: middle; color: #4f46e5; font-size: 12.5px; font-weight: 600; font-family: monospace;">{{ row.shipment_no || '—' }}</td>
                    <td style="padding: 10px 14px; vertical-align: middle; color: #1e293b; font-size: 13px; font-weight: 600;">{{ row.vehicle_plate_no || '—' }}</td>
                    <td style="padding: 10px 14px; vertical-align: middle; color: #334155; font-size: 13px;">{{ row.supply_entity_name || row.supply_entity_id || '—' }}</td>
                    <td style="padding: 10px 14px; vertical-align: middle; color: #334155; font-size: 13px; font-weight: 500;">{{ row.section_1_name || row.section_1_id || '—' }}</td>
                    <td style="padding: 10px 14px; vertical-align: middle; color: #0f172a; font-size: 13px; font-weight: 600;">
                      <span :style="{ color: isStandardFittingType(row.fitting_type) ? '#0f172a' : '#ea580c' }">
                        {{ row.fitting_type }}
                      </span>
                    </td>
                    <td style="padding: 10px 14px; vertical-align: middle; color: #334155; font-size: 13px; font-weight: 500;">{{ row.model_spec || '—' }}</td>
                    <td style="text-align: right; padding: 10px 14px; vertical-align: middle; font-weight: 700; font-size: 13px; color: #2563eb;">{{ row.shipped_qty }} {{ row.unit || '个' }}</td>
                    <td style="padding: 10px 14px; vertical-align: middle; color: #64748b; font-size: 12.5px;">{{ row.ship_remark || '—' }}</td>
                    <td style="text-align: center; padding: 10px 14px; vertical-align: middle;">
                      <button type="button" class="btn ghost btn-sm" style="padding: 4px 10px; font-size: 12px; color: #4f46e5; border-color: #c7d2fe; background: #eef2ff;" @click="openDeliveryDetailModal(row)">
                        🚚 流转凭证
                      </button>
                    </td>
                  </tr>

                  <!-- 管件汇总统计行 -->
                  <tr style="background: #f1f5f9; font-weight: bold; border-top: 2px solid #cbd5e1; position: sticky; bottom: 0; z-index: 5;">
                    <td colspan="7" style="padding: 14px 16px; font-size: 13px; color: #1e293b; background: #f1f5f9;">📊 筛选时段内管件汇总统计（共 {{ fittingTotalBatches }} 批次）</td>
                    <td style="text-align: right; padding: 14px 16px; font-size: 14px; color: #2563eb; background: #f1f5f9;">{{ fittingTotalQty }} 个</td>
                    <td colspan="2" style="padding: 14px 16px; font-size: 13px; color: #475569; background: #f1f5f9;">包含常用标准管件与异形管件件数汇总</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 管件决策辅助透视卡片 -->
            <div v-if="fittingRows.length > 0" style="margin-top: 15px; background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px 18px; border-radius: 8px; font-size: 13px; color: #334155; line-height: 1.8;">
              <div style="font-weight: 700; color: #0f172a; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                <span>💡 历史管件发货决策透视：</span>
              </div>
              <div style="display: flex; flex-wrap: wrap; gap: 10px 30px;">
                <span>🚚 发货总车次：<strong style="color: #0f172a;">{{ fittingTotalBatches }} 车/批</strong></span>
                <span>📦 累计发货管件：<strong style="color: #2563eb;">{{ fittingTotalQty }} 个</strong></span>
                <span>🟢 常用标准管件：<strong style="color: #16a34a;">{{ fittingStandardQty }} 个</strong> (弯头/三通/大小头等)</span>
                <span>🟧 非常用/异形管件：<strong style="color: #ea580c;">{{ fittingNonStandardQty }} 个</strong></span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- 保温管各型号日明细 modal -->
    <Transition name="fade">
      <div v-if="pipeDetailModalVisible && pipeDetailModalData" class="block-modal-overlay" @click.self="pipeDetailModalVisible = false">
        <div class="block-modal-container" style="max-width: 820px; max-height: 85vh; overflow-y: auto; text-align: left;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;">
            <span class="block-warning-icon">📊</span>
            <h3 style="margin-top: 5px; color: #fff;">保温管分规格型号填报与到货明细</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">
              日期：{{ pipeDetailModalData.biz_date }} | 需求主体：{{ pipeDetailModalData.section_1_name }}
            </p>
          </div>

          <div style="padding: 20px;">
            <div style="margin-bottom: 14px; font-size: 13px; color: #475569; display: flex; gap: 18px; background: #f8fafc; padding: 10px 14px; border-radius: 6px; border: 1px solid #e2e8f0; flex-wrap: wrap;">
              <span>当日总计划：<strong style="color: #0f172a;">{{ formatQty(pipeDetailModalData.plan_qty) }} 米</strong></span>
              <span>当日总发货：<strong style="color: #0284c7;">{{ formatQty(pipeDetailModalData.shipped_qty) }} 米</strong></span>
              <span>当日总使用：<strong style="color: #16a34a;">{{ formatQty(pipeDetailModalData.usage_qty) }} 米</strong></span>
              <span>当日总损耗：<strong style="color: #dc2626;">{{ formatQty(pipeDetailModalData.loss_qty) }} 米</strong></span>
              <span>确认总到货：<strong style="color: #2563eb;">{{ formatQty(pipeDetailModalData.arrived_qty) }} 米</strong></span>
            </div>

            <table class="table" style="width: 100%; border-collapse: collapse; font-size: 13px; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;">
              <thead>
                <tr style="background: #f8fafc; border-bottom: 1px solid #cbd5e1;">
                  <th style="text-align: left; padding: 10px 12px; color: #475569; font-weight: 600;">管材型号</th>
                  <th style="text-align: right; padding: 10px 12px; color: #475569; font-weight: 600;">当日计划量 (米)</th>
                  <th style="text-align: right; padding: 10px 12px; color: #475569; font-weight: 600;">当日发货量 (米)</th>
                  <th style="text-align: right; padding: 10px 12px; color: #475569; font-weight: 600;">当日使用量 (米)</th>
                  <th style="text-align: right; padding: 10px 12px; color: #475569; font-weight: 600;">当日损耗量 (米)</th>
                  <th style="text-align: right; padding: 10px 12px; color: #475569; font-weight: 600;">确认到货量 (米)</th>
                  <th style="text-align: left; padding: 10px 12px; color: #475569; font-weight: 600;">在途时间/批次</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(sub, idx) in pipeDetailModalData.models" :key="idx" style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 10px 12px; font-weight: 600; color: #1e293b;">
                    {{ sub.pipe_model_name || sub.pipe_model_id }}
                  </td>
                  <td style="padding: 10px 12px; text-align: right; color: #334155;">
                    {{ formatQty(sub.plan_qty) }}
                  </td>
                  <td style="padding: 10px 12px; text-align: right; color: #0284c7; font-weight: 500;">
                    {{ formatQty(sub.shipped_qty) }}
                  </td>
                  <td style="padding: 10px 12px; text-align: right; color: #16a34a; font-weight: 500;">
                    {{ formatQty(sub.usage_qty) }}
                  </td>
                  <td style="padding: 10px 12px; text-align: right; color: #dc2626; font-weight: 500;">
                    {{ formatQty(sub.loss_qty) }}
                  </td>
                  <td style="padding: 10px 12px; text-align: right; font-weight: 600; color: #2563eb;">
                    {{ formatQty(sub.arrived_qty) }}
                  </td>
                  <td style="padding: 10px 12px; color: #64748b; font-size: 12px;">
                    {{ sub.arrived_batch_count > 0 ? `${formatSeconds(sub.total_transit_seconds / sub.arrived_batch_count)} (${sub.arrived_batch_count}批)` : '-' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="block-modal-actions" style="padding: 12px 20px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end;">
            <button type="button" class="btn secondary" style="padding: 6px 18px; border-radius: 6px; cursor: pointer;" @click="pipeDetailModalVisible = false">
              关闭窗口
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 运输单全生命周期流转轨迹时光轴 modal -->
    <Transition name="fade">
      <div v-if="deliveryDetailModalVisible && deliveryDetailModalData" class="block-modal-overlay" @click.self="deliveryDetailModalVisible = false">
        <div class="block-modal-container" style="max-width: 600px; max-height: 85vh; overflow-y: auto;">
          <div class="block-modal-header" style="background: linear-gradient(135deg, #4f46e5 0%, #312e81 100%) !important;">
            <span class="block-warning-icon">🚚</span>
            <h3 style="margin-top: 5px; color: #fff;">订单全生命周期流转凭证</h3>
            <p class="block-warning-desc" style="color: rgba(255,255,255,0.9);">单号：{{ deliveryDetailModalData.deliveryCode || deliveryDetailModalData.deliveryId }}</p>
          </div>
          
          <!-- 信息概述 -->
          <div class="block-modal-metrics" style="grid-template-columns: repeat(3, 1fr); padding: 15px; gap: 8px; background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
            <div class="metric-block-card">
              <span class="lbl">车牌号</span>
              <span class="val" style="font-size: 13px; font-weight: bold; color: #1e293b;">{{ deliveryDetailModalData.vehiclePlateNo || '—' }}</span>
            </div>
            <div class="metric-block-card" style="grid-column: span 2;">
              <span class="lbl">规格型号</span>
              <span class="val model-val" style="font-size: 11px; line-height: 1.3;" :title="deliveryDetailModalData.pipeModelName">{{ deliveryDetailModalData.pipeModelName }}</span>
            </div>
          </div>

          <!-- 时光轴内容 Timeline -->
          <div style="padding: 25px 25px 15px 35px; text-align: left; position: relative; width: 100%; box-sizing: border-box;">
            <!-- 时光轴中轴线 -->
            <div style="position: absolute; left: 17px; top: 30px; bottom: 30px; width: 2px; border-left: 2px dashed #cbd5e1;"></div>

            <!-- 1. 发货阶段 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; background: #4f46e5; border: 2px solid #fff; box-shadow: 0 0 0 2px #4f46e5; display: inline-block;"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold; color: #1e293b;">🏭 供给侧装车发货</span>
                  <span style="font-size: 11px; color: #64748b; font-family: monospace;">{{ formatDateTimeDisplay(deliveryDetailModalData.shippedAt) }}</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px;">
                  <div>发货数量：<strong>{{ deliveryDetailModalData.shippedQty }} {{ deliveryDetailModalData.unit || '米' }}</strong></div>
                  <div>操作账号：<span>{{ deliveryDetailModalData.createdBy || '供给端调度' }}</span></div>
                  <div>经办人：<span>{{ deliveryDetailModalData.shipContactName || '—' }}</span></div>
                  <div>联系电话：<span>{{ deliveryDetailModalData.shipContactPhone || '—' }}</span></div>
                  <div style="grid-column: span 2;">供给主体：<span>{{ deliveryDetailModalData.supplyEntityName || '—' }} ({{ deliveryDetailModalData.supplyEntityId || '—' }})</span></div>
                  <div style="grid-column: span 2;" v-if="deliveryDetailModalData.shipRemark">发货备注：<span style="color: #64748b; font-style: italic;">“{{ deliveryDetailModalData.shipRemark }}”</span></div>
                </div>
              </div>
            </div>

            <!-- 2. 到货与妥投状态 -->
            <div style="position: relative; margin-bottom: 20px;">
              <span style="position: absolute; left: -24px; top: 2px; width: 12px; height: 12px; border-radius: 99px; background: #10b981; border: 2px solid #fff; box-shadow: 0 0 0 2px #10b981; display: inline-block;"></span>
              <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                  <span style="font-size: 13px; font-weight: bold; color: #1e293b;">🚚 标段接收与登记状态</span>
                  <span style="font-size: 11px; color: #10b981; font-weight: bold;">已出厂配送发货</span>
                </div>
                <div style="font-size: 11px; color: #475569; background: #fafafa; padding: 6px 10px; border-radius: 6px;">
                  <div>接收标段：<span>{{ deliveryDetailModalData.section1Name || '—' }} ({{ deliveryDetailModalData.section1Id || '—' }})</span></div>
                </div>
              </div>
            </div>
          </div>

          <div class="block-modal-footer" style="padding: 12px 20px; text-align: right; background: #f8fafc; border-top: 1px solid #e2e8f0;">
            <button type="button" class="btn primary" style="padding: 6px 20px;" @click="deliveryDetailModalVisible = false">关闭窗口</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import * as XLSX from 'xlsx'
import { AppHeader, Breadcrumbs, useTubePageShell } from './shared'
import { getTubeHistoryData, exportTubeHistoryData, getFittingDeliveriesList } from '../../daily_report_25_26/services/api'

const PROJECT_KEY = 'insulation_pipe_supply_2026'

const {
  loading,
  errorMessage,
  configSummary,
  breadcrumbItems,
  goProjectPages,
} = useTubePageShell('历史数据查询')

const activeTab = ref('pipe')
const activeDropdown = ref(null)

function toggleDropdown(name) {
  if (activeDropdown.value === name) {
    activeDropdown.value = null
  } else {
    activeDropdown.value = name
  }
}

const demandEntities = computed(() => configSummary.value?.demand_entities || [])
const supplyEntitiesOptions = computed(() => configSummary.value?.supply_entities || [])

const standardFittingTypes = computed(() => {
  return configSummary.value?.fitting_config?.standard_types || ['弯头', '三通', '大小头', '封头', '直缝弯管', '补偿器', '固定节']
})

function isStandardFittingType(typeStr) {
  if (!typeStr) return true
  return standardFittingTypes.value.includes(String(typeStr).trim())
}

const getPastDateStr = (days) => {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().split('T')[0]
}
const getTodayStr = () => {
  return new Date().toISOString().split('T')[0]
}

// 1. 保温管历史数据 Ref 变量
const historyRows = ref([])
const historyLoading = ref(false)
const historyExportLoading = ref(false)

const historyFilter = ref({
  section1Ids: [],
  startDate: getPastDateStr(30),
  endDate: getTodayStr(),
})

// 2. 管件发货历史数据 Ref 变量
const fittingRows = ref([])
const fittingLoading = ref(false)
const fittingExportLoading = ref(false)

const fittingFilter = ref({
  supplyEntityId: '',
  section1Ids: [],
  startDate: getPastDateStr(30),
  endDate: getTodayStr(),
  searchKeyword: '',
})

function selectAllHistorySection1() {
  historyFilter.value.section1Ids = demandEntities.value.map(item => item.section_1_id)
}

function clearHistorySection1() {
  historyFilter.value.section1Ids = []
}

function selectAllFittingSection1() {
  fittingFilter.value.section1Ids = demandEntities.value.map(item => item.section_1_id)
}

function clearFittingSection1() {
  fittingFilter.value.section1Ids = []
}

const historySection1TriggerText = computed(() => {
  const total = demandEntities.value.length
  const count = historyFilter.value.section1Ids.length
  if (count === 0 || (total > 0 && count === total)) return '— 全部需求主体 —'
  if (count === 1) {
    const found = demandEntities.value.find(item => item.section_1_id === historyFilter.value.section1Ids[0])
    return found ? found.section_1_name : historyFilter.value.section1Ids[0]
  }
  return `已选 ${count} 个需求主体`
})

const fittingSection1TriggerText = computed(() => {
  const total = demandEntities.value.length
  const count = fittingFilter.value.section1Ids.length
  if (count === 0 || (total > 0 && count === total)) return '— 全部接收标段 —'
  if (count === 1) {
    const found = demandEntities.value.find(item => item.section_1_id === fittingFilter.value.section1Ids[0])
    return found ? found.section_1_name : fittingFilter.value.section1Ids[0]
  }
  return `已选 ${count} 个接收标段`
})

// 凭证 Modal 控制
const deliveryDetailModalVisible = ref(false)
const deliveryDetailModalData = ref(null)

const pipeDetailModalVisible = ref(false)
const pipeDetailModalData = ref(null)

function openPipeDetailModal(groupRow) {
  pipeDetailModalData.value = groupRow
  pipeDetailModalVisible.value = true
}

const groupedHistoryRows = computed(() => {
  if (!historyRows.value.length) return []
  
  const map = new Map()
  
  historyRows.value.forEach(row => {
    const secId = row.section_1_id || 'DEFAULT'
    const key = `${row.biz_date}_${secId}`
    if (!map.has(key)) {
      map.set(key, {
        key,
        biz_date: row.biz_date,
        section_1_id: row.section_1_id,
        section_1_name: row.section_1_name || row.section_1_id,
        plan_qty: 0,
        shipped_qty: 0,
        usage_qty: 0,
        loss_qty: 0,
        arrived_qty: 0,
        total_transit_seconds: 0,
        arrived_batch_count: 0,
        models: []
      })
    }
    const item = map.get(key)
    item.plan_qty += (row.plan_qty || 0)
    item.shipped_qty += (row.shipped_qty || 0)
    item.usage_qty += (row.usage_qty || 0)
    item.loss_qty += (row.loss_qty || 0)
    item.arrived_qty += (row.arrived_qty || 0)
    item.total_transit_seconds += (row.total_transit_seconds || 0)
    item.arrived_batch_count += (row.arrived_batch_count || 0)
    item.models.push(row)
  })

  return Array.from(map.values()).map(group => {
    const modelSummaries = group.models.map(m => {
      const parts = []
      if (m.plan_qty > 0) parts.push(`计划:${m.plan_qty}m`)
      if (m.shipped_qty > 0) parts.push(`发:${m.shipped_qty}m`)
      if (m.usage_qty > 0) parts.push(`用:${m.usage_qty}m`)
      if (m.arrived_qty > 0) parts.push(`到货:${m.arrived_qty}m`)
      const desc = parts.length ? ` (${parts.join(', ')})` : ''
      return `${m.pipe_model_name || m.pipe_model_id}${desc}`
    })
    
    return {
      ...group,
      pipe_models_summary: modelSummaries.join('； ')
    }
  })
})

function openDeliveryDetailModal(row) {
  deliveryDetailModalData.value = {
    deliveryCode: row.shipment_no || row.order_no || String(row.id),
    vehiclePlateNo: row.vehicle_plate_no || '—',
    pipeModelName: `${row.fitting_type} (${row.model_spec || '未填'})`,
    shippedQty: row.shipped_qty,
    unit: row.unit || ((row.pipe_model_id || row.pipe_model_name || row.pipeModelId || row.pipeModelName) ? '米' : (row.fitting_type ? '个' : '米')),
    shippedAt: row.shipped_at,
    createdBy: row.operator || row.created_by || '供给端调度',
    shipContactName: row.ship_contact_name,
    shipContactPhone: row.ship_contact_phone,
    supplyEntityName: row.supply_entity_name || row.supply_entity_id,
    supplyEntityId: row.supply_entity_id,
    section1Name: row.section_1_name || row.section_1_id,
    section1Id: row.section_1_id,
    shipRemark: row.ship_remark,
    status: row.status || 'shipped',
  }
  deliveryDetailModalVisible.value = true
}

function formatDateTimeDisplay(val) {
  if (!val) return '—'
  return String(val).replace('T', ' ').slice(0, 16)
}

// 保温管历史查询核心逻辑
async function handleHistoryQuery() {
  historyLoading.value = true
  try {
    const res = await getTubeHistoryData(PROJECT_KEY, {
      section1Id: historyFilter.value.section1Ids.join(','),
      startDate: historyFilter.value.startDate,
      endDate: historyFilter.value.endDate,
    })
    if (res && res.ok) {
      historyRows.value = res.rows || []
    }
  } catch (error) {
    console.error('查询保温管历史数据失败:', error)
    alert(error?.message || '查询保温管历史数据失败')
  } finally {
    historyLoading.value = false
  }
}

function handleHistoryExport() {
  if (!historyRows.value.length) {
    alert('暂无保温管历史记录可导出')
    return
  }
  historyExportLoading.value = true
  try {
    const exportData = historyRows.value.map(r => ({
      '日期': r.biz_date || '—',
      '需求主体': r.section_1_name || r.section_1_id || '—',
      '保温管型号': r.pipe_model_name || r.pipe_model_id || '—',
      '当日计划量(米)': r.plan_qty ?? 0,
      '当日发货量(米)': r.shipped_qty ?? 0,
      '当日使用量(米)': r.usage_qty ?? 0,
      '当日损耗量(米)': r.loss_qty ?? 0,
      '确认到货量(米)': r.arrived_qty ?? 0,
      '到货批次数量': r.arrived_batch_count || 0,
      '平均运输在途时间': r.arrived_batch_count > 0 ? formatSeconds(r.total_transit_seconds / r.arrived_batch_count) : '—',
    }))

    const worksheet = XLSX.utils.json_to_sheet(exportData)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '保温管历史数据明细')

    const now = new Date()
    const timestamp = now.toISOString().replace(/[-:T.]/g, '').slice(0, 14)
    XLSX.writeFile(workbook, `pipe_history_records_${timestamp}.xlsx`)
  } catch (error) {
    console.error('导出保温管历史数据失败:', error)
    alert(error?.message || '导出保温管历史数据失败')
  } finally {
    historyExportLoading.value = false
  }
}

// 管件发货历史查询核心逻辑
async function handleFittingQuery() {
  fittingLoading.value = true
  try {
    const res = await getFittingDeliveriesList(PROJECT_KEY, {
      section1Id: fittingFilter.value.section1Ids.join(','),
      supplyEntityId: fittingFilter.value.supplyEntityId,
      startDate: fittingFilter.value.startDate,
      endDate: fittingFilter.value.endDate,
      searchKeyword: fittingFilter.value.searchKeyword,
      limit: 300,
    })
    if (res && res.ok) {
      fittingRows.value = res.items || []
    }
  } catch (error) {
    console.error('查询管件发货历史失败:', error)
    alert(error?.message || '查询管件发货历史失败')
  } finally {
    fittingLoading.value = false
  }
}

function handleFittingExport() {
  if (!fittingRows.value.length) {
    alert('暂无管件发货记录可导出')
    return
  }
  fittingExportLoading.value = true
  try {
    const exportData = fittingRows.value.map(r => ({
      '发货单号': r.shipment_no || '—',
      '订单号': r.order_no || '—',
      '运输车牌号': r.vehicle_plate_no || '—',
      '供给主体': r.supply_entity_name || r.supply_entity_id || '—',
      '接收标段': r.section_1_name || r.section_1_id || '—',
      '管件类型': r.fitting_type || '—',
      '型号/规格': r.model_spec || '—',
      '发货数量': r.shipped_qty ?? '—',
      '单位': r.unit || '个',
      '发货时间': formatDateTimeDisplay(r.shipped_at),
      '经办人': r.ship_contact_name || '—',
      '联系电话': r.ship_contact_phone || '—',
      '整车备注': r.ship_remark || '—',
    }))

    const worksheet = XLSX.utils.json_to_sheet(exportData)
    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '管件发货历史台账')

    const timestamp = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 14)
    XLSX.writeFile(workbook, `fitting_history_${timestamp}.xlsx`)
  } catch (error) {
    console.error('导出管件历史数据失败:', error)
    alert('导出管件历史数据失败')
  } finally {
    fittingExportLoading.value = false
  }
}

function formatQty(val) {
  if (val === null || val === undefined || val === 0) return '-'
  return Number(val).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function formatSeconds(totalSeconds) {
  if (!totalSeconds || totalSeconds <= 0) return '-'
  const secondsInt = Math.max(Math.floor(totalSeconds), 0)
  const days = Math.floor(secondsInt / 86400)
  const remainder1 = secondsInt % 86400
  const hours = Math.floor(remainder1 / 3600)
  const remainder2 = remainder1 % 3600
  const minutes = Math.floor(remainder2 / 60)
  const seconds = remainder2 % 60
  
  if (days > 0) return `${days}天${hours}小时${minutes}分`
  if (hours > 0) return `${hours}小时${minutes}分`
  if (minutes > 0) return `${minutes}分${seconds}秒`
  return `${seconds}秒`
}

// 保温管计算属性
const totalPlan = computed(() => historyRows.value.reduce((sum, r) => sum + (r.plan_qty || 0), 0))
const totalShipped = computed(() => historyRows.value.reduce((sum, r) => sum + (r.shipped_qty || 0), 0))
const totalUsage = computed(() => historyRows.value.reduce((sum, r) => sum + (r.usage_qty || 0), 0))
const totalLoss = computed(() => historyRows.value.reduce((sum, r) => sum + (r.loss_qty || 0), 0))
const totalArrived = computed(() => historyRows.value.reduce((sum, r) => sum + (r.arrived_qty || 0), 0))
const overallAvgTransit = computed(() => {
  const totalSeconds = historyRows.value.reduce((sum, r) => sum + (r.total_transit_seconds || 0), 0)
  const totalBatches = historyRows.value.reduce((sum, r) => sum + (r.arrived_batch_count || 0), 0)
  if (totalBatches > 0) {
    return `${formatSeconds(totalSeconds / totalBatches)} (共${totalBatches}批)`
  }
  return '-'
})

const fulfillmentRate = computed(() => {
  if (totalPlan.value === 0) return '-'
  return (totalArrived.value / totalPlan.value * 100).toFixed(1) + '%'
})

const planUsageAlignment = computed(() => {
  if (totalPlan.value === 0) return '-'
  return (totalUsage.value / totalPlan.value * 100).toFixed(1) + '%'
})

const lossRate = computed(() => {
  const sum = totalUsage.value + totalLoss.value
  if (sum === 0) return '-'
  return (totalLoss.value / sum * 100).toFixed(1) + '%'
})

const activeDays = computed(() => {
  const dates = new Set()
  historyRows.value.forEach(r => {
    if (r.usage_qty > 0 && r.biz_date) {
      dates.add(r.biz_date)
    }
  })
  return dates.size
})

const dailyConsumption = computed(() => {
  if (activeDays.value === 0) return '-'
  return (totalUsage.value / activeDays.value).toFixed(1)
})

const minTransit = computed(() => {
  const val = historyRows.value.reduce((min, r) => {
    if (r.min_transit_seconds !== null && r.min_transit_seconds !== undefined) {
      return min === null ? r.min_transit_seconds : Math.min(min, r.min_transit_seconds)
    }
    return min
  }, null)
  return formatSeconds(val)
})

const maxTransit = computed(() => {
  const val = historyRows.value.reduce((max, r) => {
    if (r.max_transit_seconds !== null && r.max_transit_seconds !== undefined) {
      return max === null ? r.max_transit_seconds : Math.max(max, r.max_transit_seconds)
    }
    return max
  }, null)
  return formatSeconds(val)
})

// 管件计算属性
const fittingTotalQty = computed(() => {
  return fittingRows.value.reduce((sum, r) => sum + (Number(r.shipped_qty) || 0), 0)
})

const fittingTotalBatches = computed(() => {
  const set = new Set(fittingRows.value.map(r => r.shipment_no || r.id))
  return set.size
})

const fittingStandardQty = computed(() => {
  return fittingRows.value
    .filter(r => isStandardFittingType(r.fitting_type))
    .reduce((sum, r) => sum + (Number(r.shipped_qty) || 0), 0)
})

const fittingNonStandardQty = computed(() => {
  return Math.max(0, fittingTotalQty.value - fittingStandardQty.value)
})

onMounted(() => {
  handleHistoryQuery()
  handleFittingQuery()
})
</script>

<style scoped>
.page-layout {
  min-height: 100vh;
  background: var(--neutral-50);
  display: flex;
  flex-direction: column;
}

.page-main {
  flex: 1;
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.page-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title-row h2 {
  font-size: 24px;
  color: var(--neutral-800);
  margin: 0 0 6px 0;
}

.page-title-row .subtitle {
  font-size: 14px;
  color: var(--neutral-500);
  margin: 0;
}

.history-tab-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 12px;
}

.tab-pill-btn {
  padding: 8px 20px;
  border-radius: 20px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #475569;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-pill-btn:hover {
  border-color: #4f46e5;
  color: #4f46e5;
  background: #f8fafc;
}

.tab-pill-btn.active {
  background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%);
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
}

.section-card {
  padding: 24px;
}

.card-header {
  font-size: 16px;
  font-weight: 700;
  color: var(--neutral-800);
  margin-bottom: 8px;
}

.block-sub {
  font-size: 13px;
  color: var(--neutral-500);
  margin: 0 0 20px 0;
}

.table-wrap {
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.editor-table th, .editor-table td {
  border-bottom: 1px solid #e2e8f0;
}

.loading-state, .error-state {
  text-align: center;
  padding: 60px 0;
  color: var(--neutral-600);
}

.error-state {
  color: var(--danger);
}

/* Modal overlay 基础属性 */
.block-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.block-modal-container {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  width: 100%;
  overflow: hidden;
  animation: modalPop 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.block-modal-header {
  padding: 20px 24px;
  color: #fff;
  text-align: center;
}

.block-warning-icon {
  font-size: 28px;
}

.block-modal-metrics {
  display: grid;
}

.metric-block-card {
  display: flex;
  flex-direction: column;
  background: #fff;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.metric-block-card .lbl {
  font-size: 11px;
  color: #64748b;
}

.metric-block-card .val {
  font-size: 13px;
  color: #1e293b;
  margin-top: 2px;
}

@keyframes modalPop {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
</style>
