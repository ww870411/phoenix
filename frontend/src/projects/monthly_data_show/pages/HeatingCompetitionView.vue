<template>
  <div class="competition-page">
    <AppHeader />
    <main class="competition-main">
      <Breadcrumbs :items="breadcrumbItems" />

      <!-- 顶部控制条与标题 Hero -->
      <header class="topbar-hero">
        <div class="hero-left">
          <div class="title-with-badge">
            <span class="trophy-icon">🏆</span>
            <div class="title-text-group">
              <div class="title-row">
                <h2>供暖期指标竞赛专题</h2>
                <span class="season-badge">2026-2027 供暖期</span>
                <span class="stage-tag">月度考评 · 动态激励</span>
              </div>
              <p class="hero-sub">
                生产经营核心指标月度横向竞赛、分层穿透考核与激励兑现全景工作台
              </p>
            </div>
          </div>
        </div>

        <div class="hero-right">
          <!-- 考核月份选择器 -->
          <div class="month-selector-card">
            <span class="calendar-icon">📅</span>
            <div class="month-select-inner">
              <label for="month-select" class="month-label">考核月份</label>
              <select
                id="month-select"
                v-model="selectedMonth"
                class="month-select"
                @change="onMonthChange"
              >
                <option
                  v-for="opt in availableMonths"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </option>
              </select>
            </div>
          </div>

          <!-- 操作按钮组 -->
          <div class="hero-actions">
            <button
              type="button"
              class="btn-hero btn-secondary"
              title="重置当前月份为初始标准基准值"
              :disabled="isFetchingAuto || isSavingRecord || isExportingExcel"
              @click="resetToDefaultData"
            >
              🔄 重置基准
            </button>
            <button
              type="button"
              class="btn-hero btn-auto-fetch"
              title="从系统数据库自动提取月报计划与完成值、日报服务投诉累计量"
              :disabled="isFetchingAuto || isSavingRecord || isExportingExcel"
              @click="handleAutoFetchData"
            >
              <span v-if="isFetchingAuto">⚡ 取数中...</span>
              <span v-else>⚡ 从系统自动取数</span>
              <span v-if="!isFetchingAuto" class="fetch-badge-live">月报+日报</span>
            </button>
            <button
              type="button"
              class="btn-hero btn-export"
              title="导出含考评兑现汇总、指标得分矩阵、计算过程明细的 3-Sheet Excel 汇报文件"
              :disabled="isFetchingAuto || isSavingRecord || isExportingExcel"
              @click="handleExportExcel"
            >
              <span v-if="isExportingExcel">📥 导出中...</span>
              <span v-else>📥 导出竞赛报表</span>
            </button>
            <button
              type="button"
              class="btn-hero btn-primary"
              title="将当前 7 家参评单位测算明细与奖金暂存保存到数据库（状态：saved）"
              :disabled="isFetchingAuto || isSavingRecord || isPublishingFinal || isExportingExcel"
              @click="handleSaveRecord"
            >
              <span v-if="isSavingRecord">💾 保存中...</span>
              <span v-else>💾 保存至系统数据库</span>
            </button>
            <button
              type="button"
              class="btn-hero btn-publish"
              title="重新保存当前数据并标记为正式定稿（状态：final），计入供暖期定稿兑现汇总"
              :disabled="isFetchingAuto || isSavingRecord || isPublishingFinal || isExportingExcel"
              @click="handlePublishFinal"
            >
              <span v-if="isPublishingFinal">📢 发布中...</span>
              <span v-else>📢 发布结果</span>
            </button>
          </div>
        </div>
      </header>

      <!-- 数据状态提示条 -->
      <div v-if="recordStatusNote" class="status-ribbon-bar" :class="{ 'is-final': recordStatus === 'final' }">
        <div class="status-ribbon-inner">
          <span class="status-dot" :class="recordStatusClass">●</span>
          <span v-if="recordStatus === 'final'" class="ribbon-state-badge badge-final">FINAL · 已定稿</span>
          <span v-else-if="recordStatus === 'saved'" class="ribbon-state-badge badge-saved">SAVED · 已保存</span>
          <span class="status-text">{{ recordStatusNote }}</span>
        </div>
      </div>

      <!-- 主导航标签页切换 -->
      <nav class="competition-tabs" aria-label="指标竞赛模块切换">
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'rules' }]"
          @click="activeTab = 'rules'"
        >
          <span class="tab-icon">📋</span>
          <span class="tab-title">指标竞赛规则与方案全景</span>
        </button>
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'season_records' }]"
          @click="openSeasonRecordsTab"
        >
          <span class="tab-icon">📜</span>
          <span class="tab-title">供暖期兑现记录</span>
        </button>
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'calculation' }]"
          @click="activeTab = 'calculation'"
        >
          <span class="tab-icon">📊</span>
          <span class="tab-title">指标评分测算台</span>
        </button>
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'complaints' }]"
          @click="activeTab = 'complaints'"
        >
          <span class="tab-icon">📢</span>
          <span class="tab-title">投诉率排名</span>
        </button>
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'extra_rewards' }]"
          @click="activeTab = 'extra_rewards'"
        >
          <span class="tab-icon">🏅</span>
          <span class="tab-title">额外嘉奖</span>
        </button>
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'overview' }]"
          @click="activeTab = 'overview'"
        >
          <span class="tab-icon">🏆</span>
          <span class="tab-title">结果总览</span>
          <span class="tab-amount-chip">拟兑现 ¥{{ Math.round(totalSimulatedReward).toLocaleString() }}</span>
        </button>
      </nav>

      <!-- ================= 标签页 1：指标竞赛规则 ================= -->
      <section v-if="activeTab === 'rules'" class="tab-content rules-section">
        <!-- 核心机制与组织原则 -->
        <div class="rules-overview-grid">
          <div class="rule-card highlight-card">
            <div class="card-title-bar">
              <span class="card-icon blue-icon">🎯</span>
              <div class="card-title-wrap">
                <h3>竞赛目标与工作原则</h3>
                <span class="card-subtitle">集团冬供核心考核导向</span>
              </div>
            </div>
            <ul class="rule-list">
              <li>
                <strong class="text-blue">核心目标</strong>：提升供暖期生产经营质量，加强生产能耗与供热服务核心指标全周期穿透管控，充分激发一线运维队伍的主动性与创造力。
              </li>
              <li>
                <strong class="text-blue">工作原则</strong>：坚持“奖优评先、激励为主”；专项奖励<strong>不占用竞赛单位工资总额</strong>，设立专项总奖金池，定向向生产一线和关键岗位倾斜。
              </li>
              <li>
                <strong class="text-blue">考评周期</strong>：2026年11月1日至2027年4月5日（11月~3月按月考评兑现，4月并入供暖期末综合总考评）。
              </li>
              <li>
                <strong class="text-blue">考评机构</strong>：成立冬供指标竞赛领导小组（组长：兰良生），考评办公室设在经济运行部，负责日常测算与复核。
              </li>
            </ul>
          </div>

          <div class="rule-card warning-card">
            <div class="card-title-bar">
              <span class="card-icon red-icon">🚨</span>
              <div class="card-title-wrap">
                <h3>红线一票否决与资格限制</h3>
                <span class="card-subtitle text-danger">出现下列情形取消当月兑现资格</span>
              </div>
            </div>
            <ul class="rule-list redline-list">
              <li>
                <span class="tag-red">末位淘汰</span>
                <span>当月竞赛考核总得分<strong>排在最后一名且得分低于 85 分</strong>，直接取消当月奖励兑现资格（奖金归零）。</span>
              </li>
              <li>
                <span class="tag-red">投诉黑榜</span>
                <span>民生供热服务投诉率若<strong>进入周度或月度黑榜</strong>，实行一票否决，取消当月考评资格不予兑现。</span>
              </li>
              <li>
                <span class="tag-red">重大事故</span>
                <span>生产运行中若发生<strong>较大及以上安全环保事故</strong>，实行一票否决，取消当月考评奖励兑现资格。</span>
              </li>
              <li>
                <span class="tag-gray">廉洁纪律</span>
                <span>竞赛奖励资金必须严格用于内部二次分配，全面面向一线人员，<strong>严禁私自截留、私设小金库或搞平均主义大锅饭</strong>。</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- 7家参评单位月度奖励基数 -->
        <div class="content-block">
          <div class="block-header">
            <div class="bh-left">
              <h4>💰 各单位月度竞赛奖励基数（月度总额度 280,000 元）</h4>
              <span class="bh-sub">依据业务体量、保供面积、机炉规模与人员配比科学核定基数</span>
            </div>
            <span class="calc-formula">兑现公式：月度奖励 = 奖励基数 × 考核综合得分%</span>
          </div>

          <div class="base-reward-grid">
            <div
              v-for="unit in unitBaseRewardList"
              :key="unit.code"
              class="base-reward-card"
            >
              <div class="brc-top">
                <span class="unit-share-pill">{{ ((unit.baseAmount / 280000) * 100).toFixed(1) }}% 份额</span>
              </div>
              <div class="unit-name">{{ unit.name }}</div>
              <div class="reward-amount-box">
                <span class="currency">¥</span>
                <span class="reward-amount">{{ unit.baseAmount.toLocaleString() }}</span>
                <span class="amount-unit">元/月</span>
              </div>
              <div class="progress-bar-wrap">
                <div
                  class="progress-bar-fill"
                  :style="{ width: `${(unit.baseAmount / 70000) * 100}%` }"
                ></div>
              </div>
            </div>
          </div>
          <p class="section-hint">
            * 提示：研究院、能源工程公司、售电公司申报管理创新专项激励，不计入生产月度指标打分，由集团另行组织专项表彰。
          </p>
        </div>

        <!-- 各单位指标与分值分布对照表 -->
        <div class="content-block">
          <div class="block-header">
            <div class="bh-left">
              <h4>📐 各单位月度竞赛指标与分值分布对照表（满分 100 分）</h4>
              <span class="bh-sub">7 家单位分层分类指标设置矩阵一览</span>
            </div>
          </div>
          <div class="table-responsive">
            <table class="matrix-table modern-table">
              <thead>
                <tr class="thead-row-1">
                  <th rowspan="2" class="th-cat">指标类别</th>
                  <th colspan="2" class="th-unit-group">北海热电厂</th>
                  <th colspan="2" class="th-unit-group">香海热电厂</th>
                  <th colspan="2" class="th-unit-group">供热公司</th>
                  <th colspan="2" class="th-unit-group">金州热电</th>
                  <th colspan="2" class="th-unit-group">北方热电</th>
                  <th colspan="2" class="th-unit-group">金普公司</th>
                  <th colspan="2" class="th-unit-group">庄河环海</th>
                </tr>
                <tr class="thead-row-2">
                  <th>项目</th><th>分值</th>
                  <th>项目</th><th>分值</th>
                  <th>项目</th><th>分值</th>
                  <th>项目</th><th>分值</th>
                  <th>项目</th><th>分值</th>
                  <th>项目</th><th>分值</th>
                  <th>项目</th><th>分值</th>
                </tr>
              </thead>
              <tbody>
                <!-- 运营指标行 -->
                <tr>
                  <td rowspan="6" class="td-category td-cat-ops">运营指标</td>
                  <td>耗标煤总量</td><td class="font-bold">30</td>
                  <td>耗标煤总量</td><td class="font-bold">30</td>
                  <td>主城区耗标煤总量</td><td class="font-bold">15</td>
                  <td>耗标煤总量</td><td class="font-bold">30</td>
                  <td>耗标煤总量</td><td class="font-bold">30</td>
                  <td>耗标煤总量</td><td class="font-bold">30</td>
                  <td class="td-highlight">外购热量</td><td class="font-bold td-highlight">30</td>
                </tr>
                <tr>
                  <td>厂内水耗量</td><td class="font-bold">10</td>
                  <td>厂内水耗量</td><td class="font-bold">10</td>
                  <td>供暖热单耗</td><td class="font-bold">15</td>
                  <td>供暖电单耗</td><td class="font-bold">10</td>
                  <td>供暖电单耗</td><td class="font-bold">10</td>
                  <td>供暖电单耗</td><td class="font-bold">10</td>
                  <td>供暖电单耗</td><td class="font-bold">10</td>
                </tr>
                <tr>
                  <td>现货电价</td><td class="font-bold">20</td>
                  <td>现货电价</td><td class="font-bold">20</td>
                  <td>供暖电单耗</td><td class="font-bold">10</td>
                  <td>供暖水单耗</td><td class="font-bold">20</td>
                  <td>供暖水单耗</td><td class="font-bold">20</td>
                  <td>供暖水单耗</td><td class="font-bold">20</td>
                  <td>供暖水单耗</td><td class="font-bold">20</td>
                </tr>
                <tr>
                  <td>全厂热效率</td><td class="font-bold">20</td>
                  <td>全厂热效率</td><td class="font-bold">20</td>
                  <td>供暖水单耗</td><td class="font-bold">20</td>
                  <td>服务投诉率</td><td class="font-bold">20</td>
                  <td>服务投诉率</td><td class="font-bold">20</td>
                  <td>服务投诉率</td><td class="font-bold">20</td>
                  <td>服务投诉率</td><td class="font-bold">20</td>
                </tr>
                <tr>
                  <td>非计划停机停炉</td><td class="font-bold">10</td>
                  <td>非计划停机停炉</td><td class="font-bold">10</td>
                  <td>服务投诉率</td><td class="font-bold">20</td>
                  <td>停供断管率</td><td class="font-bold">10</td>
                  <td>停供断管率</td><td class="font-bold">10</td>
                  <td>停供断管率</td><td class="font-bold">10</td>
                  <td>停供断管率</td><td class="font-bold">10</td>
                </tr>
                <tr>
                  <td class="td-empty" colspan="2">-</td>
                  <td class="td-empty" colspan="2">-</td>
                  <td>停供断管率</td><td class="font-bold">10</td>
                  <td class="td-empty" colspan="2">-</td>
                  <td class="td-empty" colspan="2">-</td>
                  <td class="td-empty" colspan="2">-</td>
                  <td class="td-empty" colspan="2">-</td>
                </tr>
                <!-- 管理指标行 -->
                <tr class="tr-mgmt">
                  <td rowspan="2" class="td-category td-cat-mgmt">管理指标</td>
                  <td>安全文明生产</td><td class="font-bold text-purple">10</td>
                  <td>安全文明生产</td><td class="font-bold text-purple">10</td>
                  <td>安全文明生产</td><td class="font-bold text-purple">10</td>
                  <td>安全文明生产</td><td class="font-bold text-purple">10</td>
                  <td>安全文明生产</td><td class="font-bold text-purple">10</td>
                  <td>安全文明生产</td><td class="font-bold text-purple">10</td>
                  <td>安全文明生产</td><td class="font-bold text-purple">10</td>
                </tr>
                <tr class="tr-mgmt">
                  <td>安全环保事故</td><td class="text-danger font-bold">否决/扣分</td>
                  <td>安全环保事故</td><td class="text-danger font-bold">否决/扣分</td>
                  <td>安全环保事故</td><td class="text-danger font-bold">否决/扣分</td>
                  <td>安全环保事故</td><td class="text-danger font-bold">否决/扣分</td>
                  <td>安全环保事故</td><td class="text-danger font-bold">否决/扣分</td>
                  <td>安全环保事故</td><td class="text-danger font-bold">否决/扣分</td>
                  <td>安全环保事故</td><td class="text-danger font-bold">否决/扣分</td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="tfoot-sum-row">
                  <th class="th-total">满分总计</th>
                  <th colspan="2">100 分</th>
                  <th colspan="2">100 分</th>
                  <th colspan="2">100 分</th>
                  <th colspan="2">100 分</th>
                  <th colspan="2">100 分</th>
                  <th colspan="2">100 分</th>
                  <th colspan="2">100 分</th>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <!-- 详细计分规则清单（三组分类） -->
        <div class="content-block">
          <div class="block-header">
            <div class="bh-left">
              <h4>📖 各指标计分算法与实施细则（9 大核心维度）</h4>
              <span class="bh-sub">依据集团竞赛方案正文公式统一封装</span>
            </div>
          </div>

          <div class="rules-category-section">
            <h5 class="rc-title text-blue">⚡ 一、生产能耗与电力效益指标</h5>
            <div class="rules-detail-grid">
              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-blue">能耗控制</span>
                  <h5>耗标煤总量 / 外购热量 / 供暖热单耗</h5>
                </div>
                <div class="drc-formula">完成率 = 1 + (目标值 - 完成值) / 目标值</div>
                <p class="drc-desc">
                  完成率 100% 得满分。超出或降低 1 个百分点加减 1 分（不足 1% 按比例计算）。不计负分，<strong>得分上限 120%</strong>。<br />
                  <em>* 特别约定：供热公司主城区耗标煤总量、供暖热单耗超出/降低 1 个百分点按 0.5 分加减。</em>
                </p>
              </div>

              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-blue">单耗水耗</span>
                  <h5>厂内水耗量 / 供暖电单耗 / 供暖水单耗</h5>
                </div>
                <div class="drc-formula">得分 = [1 + (目标值 - 完成值) / 目标值] × 权重分</div>
                <p class="drc-desc">
                  与月度生产计划目标比较，按完成率乘对应权重分值得出。不计负分，<strong>得分上限 120%</strong>。
                </p>
              </div>

              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-green">电力效益</span>
                  <h5>现货电价（20分）</h5>
                </div>
                <div class="drc-formula">完成率 = 每月平均现货电价 / (辽宁统一结算点均价 × 1.05)</div>
                <p class="drc-desc">
                  完成率 100% 得 20 分。超出或降低 3 个百分点加减 1 分（不足 3% 按比例加减）。不计负分，<strong>得分上限 120%（24分）</strong>。由售电公司提供基准值。
                </p>
              </div>

              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-green">综合能效</span>
                  <h5>全厂热效率（20分）</h5>
                </div>
                <div class="drc-formula">完成率 = 1 + (完成值 - 目标值) / 目标值</div>
                <p class="drc-desc">
                  完成率 100% 得 20 分。超出或降低 1 个百分点加减 2 分（不足 1% 按比例加减）。不计负分，<strong>得分上限 110%（22分）</strong>。
                </p>
              </div>
            </div>
          </div>

          <div class="rules-category-section">
            <h5 class="rc-title text-orange">🏢 二、供热运营与服务民生指标</h5>
            <div class="rules-detail-grid">
              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-orange">服务民生</span>
                  <h5>服务投诉率（20分）</h5>
                </div>
                <div class="drc-formula">万 m² 省市民心网投诉件数量，横向排名赋分</div>
                <p class="drc-desc">
                  第 1 名得 20 分，排名每下降 1 名扣 2 分。<br />
                  进入周/月红榜<strong>额外加 5 分</strong>；若<strong>进入周/月黑榜，直接取消当月考核资格不予兑现</strong>。
                </p>
              </div>

              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-orange">稽查停供</span>
                  <h5>停供断管率（10分）</h5>
                </div>
                <div class="drc-formula">分户停供断管抽检率 100% 得满分 10 分</div>
                <p class="drc-desc">
                  月度检查断管率，每低 1 个百分点扣 1 分（不足 1% 按比例计分），不计负分。<strong>断管率低于 95% 时，该项直接得 0 分</strong>。
                </p>
              </div>
            </div>
          </div>

          <div class="rules-category-section">
            <h5 class="rc-title text-purple">🛡️ 三、运行安全与现场文明规范</h5>
            <div class="rules-detail-grid">
              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-purple">安全运行</span>
                  <h5>非计划停机停炉（10分）</h5>
                </div>
                <div class="drc-formula">基准目标 0 次/月（得满分 10 分）</div>
                <p class="drc-desc">
                  热源厂主设备发生一次非计划停运扣 5 分，发生两次及以上扣完 10 分为止，不计负分。
                </p>
              </div>

              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-purple">现场规范</span>
                  <h5>安全文明生产（10分 · 实际得分）</h5>
                </div>
                <div class="drc-formula">基准 10 分，实际完成值直接录入现场评定得分（0~10分）</div>
                <p class="drc-desc">
                  定置管理、两票三制、班组台账、“三违行为”等现场检查发现问题逐项扣减，最终录入实际评定得分，计算分即等于实际得分。
                </p>
              </div>

              <div class="detail-rule-card">
                <div class="drc-head">
                  <span class="drc-badge badge-red">安全底线</span>
                  <h5>安全环保事故（扣分 / 一票否决）</h5>
                </div>
                <div class="drc-formula">一般事故扣 10 分；较大及以上事故一票否决</div>
                <p class="drc-desc">
                  发生较大及以上安全环保事故，取消当月奖金兑现资格。当月调查未定性的以认定月份补扣。
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= 标签页 2：评分测算工作台（按默认顺序展示各单位 · 不排名） ================= -->
      <section v-else-if="activeTab === 'calculation'" class="tab-content calculation-section">
        <!-- 统计核心卡片流 KPI -->
        <div class="calc-kpi-grid">
          <div class="calc-kpi-card kpi-month">
            <div class="kpi-icon">📅</div>
            <div class="kpi-content">
              <div class="kpi-label">考核测算月份</div>
              <div class="kpi-val text-brand">{{ selectedMonthLabel }}</div>
              <div class="kpi-sub">供暖期月度经营考评</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-units">
            <div class="kpi-icon">🏢</div>
            <div class="kpi-content">
              <div class="kpi-label">参评单位总数</div>
              <div class="kpi-val font-mono">7 <span class="unit-text">家</span></div>
              <div class="kpi-sub">热电厂 2 家 · 供热/分厂 5 家</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-budget">
            <div class="kpi-icon">💰</div>
            <div class="kpi-content">
              <div class="kpi-label">月度总奖金池基数</div>
              <div class="kpi-val text-blue font-mono">¥280,000</div>
              <div class="kpi-sub">固定专项预算池</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-reward">
            <div class="kpi-icon">🎁</div>
            <div class="kpi-content">
              <div class="kpi-label">当前拟兑现奖金总额</div>
              <div class="kpi-val text-green font-mono">¥{{ Math.round(totalSimulatedReward).toLocaleString() }}</div>
              <div class="kpi-progress-bar">
                <div
                  class="kpi-bar-fill"
                  :style="{ width: `${Math.min(100, (totalSimulatedReward / 280000) * 100)}%` }"
                ></div>
              </div>
              <div class="kpi-sub">
                <template v-if="totalExtraReward !== 0">
                  竞赛 ¥{{ Math.round(totalBaseReward).toLocaleString() }} + 嘉奖 ¥{{ Math.round(totalExtraReward).toLocaleString() }}
                </template>
                <template v-else>
                  全网兑现率 {{ ((totalSimulatedReward / 280000) * 100).toFixed(1) }}%
                </template>
              </div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-status">
            <div class="kpi-icon" :class="disqualifiedCount > 0 ? 'red-icon' : 'green-icon'">
              {{ disqualifiedCount > 0 ? '⚠️' : '🛡️' }}
            </div>
            <div class="kpi-content">
              <div class="kpi-label">红线资格核查</div>
              <div :class="['kpi-val font-mono', disqualifiedCount > 0 ? 'text-red' : 'text-green']">
                {{ disqualifiedCount > 0 ? `${disqualifiedCount} 家取消` : '全员合格' }}
              </div>
              <div class="kpi-sub">{{ disqualifiedCount > 0 ? '末位<85分 / 事故 / 黑榜' : '无一票否决单位' }}</div>
            </div>
          </div>
        </div>

        <!-- 快速跳转锚点导航栏与批量展开收起工具条（按默认顺序展示） -->
        <div class="units-nav-toolbar">
          <div class="unt-left">
            <span class="unt-title">🧭 快速定位单位：</span>
            <div class="unt-pills">
              <button
                v-for="(unit, uIdx) in unitsData"
                :key="`jump-${unit.code}`"
                type="button"
                class="unt-pill-btn"
                @click="scrollToUnit(unit.code)"
              >
                <span class="unt-rank-num">{{ uIdx + 1 }}.</span>
                <span class="unt-name">{{ unit.name }}</span>
              </button>
            </div>
          </div>
          <div class="unt-right">
            <label class="toggle-source-opt" title="显示或隐藏各指标的数据取数来源">
              <input type="checkbox" v-model="showSourceTags" />
              <span>显示取数来源</span>
            </label>
            <button type="button" class="btn-tool-mini" @click="expandAllUnits">全部展开</button>
            <button type="button" class="btn-tool-mini" @click="collapseAllUnits">全部折叠</button>
          </div>
        </div>

        <!-- 7 家参评单位垂直卡片（从上到下按默认顺序逐一分列 · 无排名） -->
        <div class="vertical-units-container">
          <div
            v-for="(unit, unitIdx) in unitsData"
            :key="unit.code"
            :id="`unit-card-${unit.code}`"
            class="unit-vertical-card content-block"
            :class="{ 'card-collapsed': !unitExpandedMap[unit.code], 'card-disqualified': !unit.eligible }"
          >
            <!-- 头部摘要栏（点击可折叠/展开 · 按默认顺序不参与排名） -->
            <div class="uvc-header" @click="toggleUnitExpand(unit.code)">
              <div class="uvc-header-left">
                <span class="uvc-seq-badge">#{{ unitIdx + 1 }}</span>
                <h3 class="uvc-title">{{ unit.name }}</h3>
                <span class="uvc-count-tag">{{ getOperationalIndicators(unit).length + 2 }} 项考评指标</span>
              </div>

              <div class="uvc-header-right" @click.stop>
                <div class="uvc-stat-pill">
                  <span class="usp-label">月度基数</span>
                  <span class="usp-val font-mono">¥{{ (unit.baseAmount ?? 0).toLocaleString() }}</span>
                </div>

                <div class="uvc-stat-pill uvc-score-pill">
                  <span class="usp-label">综合得分</span>
                  <span
                    class="usp-val font-mono font-bold"
                    :class="(unit.score ?? 0) >= 100 ? 'text-green' : (unit.score ?? 0) >= 85 ? 'text-blue' : 'text-red'"
                  >
                    {{ (unit.score ?? 0).toFixed(2) }} 分
                  </span>
                </div>

                <div class="uvc-stat-pill uvc-status-pill">
                  <span v-if="unit.eligible && (unit.pendingCount || 0) === 0" class="status-badge status-ok">✓ 资格有效</span>
                  <span v-else-if="unit.eligible && (unit.pendingCount || 0) > 0" class="status-badge status-pending">
                    ⏳ 待月报({{ unit.pendingCount }}项)
                  </span>
                  <span v-else class="status-badge status-fail" :title="unit.disqualifyReason">
                    ✕ {{ unit.disqualifyReason }}
                  </span>
                </div>

                <div class="uvc-stat-pill uvc-reward-pill">
                  <span class="usp-label">拟兑现奖金</span>
                  <span
                    class="usp-reward-val font-mono font-bold"
                    :class="unit.eligible || (unit.extraRewardTotal || 0) > 0 ? 'text-green' : 'text-muted strike'"
                  >
                    ¥{{ Math.round(unit.calculatedReward || 0).toLocaleString() }}
                  </span>
                  <span v-if="unit.extraRewardTotal" class="usp-extra-hint font-mono">
                    含嘉奖 {{ unit.extraRewardTotal >= 0 ? '+' : '' }}¥{{ Math.round(unit.extraRewardTotal).toLocaleString() }}
                  </span>
                </div>

                <button
                  type="button"
                  class="btn-toggle-expand"
                  :title="unitExpandedMap[unit.code] ? '收起该单位' : '展开该单位'"
                  @click="toggleUnitExpand(unit.code)"
                >
                  <span class="toggle-text">{{ unitExpandedMap[unit.code] ? '收起' : '展开' }}</span>
                  <span class="toggle-arrow" :class="{ rotated: !unitExpandedMap[unit.code] }">▼</span>
                </button>
              </div>
            </div>

            <!-- 卡片主体内容（展开时显示） -->
            <div v-show="unitExpandedMap[unit.code]" class="uvc-body">
              <!-- 1. 运营指标打分表 -->
              <div class="uvc-sub-section">
                <div class="sub-section-title">
                  <div class="sst-left">
                    <span class="sst-icon">⚡</span>
                    <span class="sst-name">生产能耗与运营指标（权重合计 {{ getOperationalIndicators(unit).reduce((s, i) => s + (i.weight || 0), 0) }} 分）</span>
                  </div>
                  <div class="sst-hint-group">
                    <span class="sst-hint">计划值与实际完成值均可微调编辑</span>
                    <span class="sst-manual-legend" title="手动填报或修改的完成值将高亮着色，二次自动取数时自动保留">
                      <span class="manual-swatch"></span>
                      <span>琥珀色着色 = 人工调整/手填完成值</span>
                    </span>
                  </div>
                </div>

                <div class="table-responsive">
                  <table class="unit-ind-table modern-table">
                    <thead>
                      <tr>
                        <th class="th-num">序号</th>
                        <th class="th-ind-name">考核指标</th>
                        <th class="th-weight">权重分</th>
                        <th class="th-target">计划值</th>
                        <th class="th-actual">实际完成值</th>
                        <th class="th-unit">单位</th>
                        <th class="th-rate">达成率</th>
                        <th class="th-rule">计分规则</th>
                        <th class="th-score">测算得分</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="(ind, indIdx) in getOperationalIndicators(unit)"
                        :key="`${unit.code}-ind-${indIdx}`"
                        :class="{ 'row-manual-actual': ind.isManualActual }"
                      >
                        <td class="text-center font-mono">{{ indIdx + 1 }}</td>
                        <td>
                          <div class="ind-name-box">
                            <span class="ind-main-name font-bold">{{ ind.name }}</span>
                            <div class="ind-tag-row" v-if="showSourceTags || ind.isManualActual">
                              <span v-if="showSourceTags" class="ind-source-tag">{{ ind.sourceLabel }}</span>
                              <span
                                v-if="ind.isManualActual"
                                class="ind-manual-tag"
                                :title="getManualTooltip(ind)"
                              >人工调整</span>
                            </div>
                          </div>
                        </td>
                        <td class="text-center font-mono font-bold">{{ ind.weight }} 分</td>
                        <!-- 计划值（支持编辑） -->
                        <td>
                          <div v-if="ind.hasTarget" class="ind-input-cell ind-target-cell">
                            <input
                              type="number"
                              step="any"
                              class="ind-input target-input"
                              v-model.number="ind.targetValue"
                              placeholder="计划值"
                              @input="recalculateAllScores"
                            />
                          </div>
                          <div v-else class="ind-fixed-target-box" :class="{ 'fixed-target-right': ind.calcType === 'shutdown' }">
                            <span class="ind-fixed-val font-mono">{{ ind.calcType === 'shutdown' ? '0' : '-' }}</span>
                            <span v-if="ind.calcType === 'complaint_rank'" class="ind-fixed-tag">横向排名</span>
                          </div>
                        </td>
                        <!-- 实际完成值（支持编辑，手工调整后着色标记） -->
                        <td>
                          <div
                            class="ind-input-cell"
                            :class="{ 'ind-manual-cell': ind.isManualActual }"
                          >
                            <span
                              v-if="ind.isManualActual"
                              class="manual-dot-badge"
                              :title="getManualTooltip(ind)"
                            >手调</span>
                            <input
                              type="number"
                              step="any"
                              class="ind-input"
                              v-model.number="ind.actualValue"
                              placeholder="实际值"
                              @input="onActualValueInput(ind)"
                            />
                            <button
                              v-if="ind.isManualActual"
                              type="button"
                              class="manual-reset-btn"
                              :title="getRestoreTooltip(ind)"
                              @click="restoreSystemActualValue(ind)"
                            >↺</button>
                          </div>
                        </td>
                        <td class="text-center text-muted font-mono">{{ ind.unit }}</td>
                        <td class="text-center font-mono font-bold text-blue">
                          {{ getIndicatorRate(ind) }}
                        </td>
                        <td class="text-muted text-xs">
                          {{ getIndicatorRuleSummary(ind) }}
                        </td>
                        <td class="text-center">
                          <span
                            v-if="ind.score === null || ind.score === undefined"
                            class="ind-score-badge score-pending font-mono"
                            title="实际完成值尚未出数，暂不计分"
                          >
                            待出数
                          </span>
                          <span
                            v-else
                            class="ind-score-badge font-mono"
                            :class="ind.score >= (ind.weight ?? 0) ? 'score-win' : 'score-loss'"
                          >
                            {{ ind.score.toFixed(2) }} 分
                          </span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- 2. 现场管理与红线核查区（双列排布） -->
              <div class="uvc-sub-section mgmt-section">
                <div class="mgmt-grid">
                  <!-- 左侧：安全文明生产评定 -->
                  <div class="mgmt-box civic-box">
                    <div class="mgmt-box-header">
                      <div class="mbh-title">
                        <span class="mbh-badge badge-purple">管理考核</span>
                        <h4>🛡️ 安全文明生产评定（满分 10 分）</h4>
                      </div>
                      <span class="mbh-score font-mono text-purple font-bold">
                        计入得分：{{ (getCivicIndicator(unit).score ?? 10).toFixed(1) }} 分
                      </span>
                    </div>
                    <p class="mgmt-desc">
                      两票三制、定置管理、班组安全台账与现场三违行为评定，<strong>录入值即为实际得分（0~10分）</strong>。
                    </p>
                    <div class="civic-input-row">
                      <span class="cir-label">现场评定实际得分：</span>
                      <div
                        class="cir-input-box"
                        :class="{ 'cir-manual-box': getCivicIndicator(unit).isManualActual }"
                      >
                        <span
                          v-if="getCivicIndicator(unit).isManualActual"
                          class="manual-dot-badge"
                          title="安全文明生产得分已由默认满分 10 分调整"
                        >手调</span>
                        <input
                          type="number"
                          min="0"
                          max="10"
                          step="0.5"
                          class="civic-score-input"
                          v-model.number="getCivicIndicator(unit).actualValue"
                          placeholder="0~10"
                          @input="onActualValueInput(getCivicIndicator(unit))"
                        />
                        <span class="cir-unit">分</span>
                        <button
                          v-if="getCivicIndicator(unit).isManualActual"
                          type="button"
                          class="manual-reset-btn"
                          title="恢复默认满分 10 分"
                          @click="restoreSystemActualValue(getCivicIndicator(unit))"
                        >↺</button>
                      </div>
                      <span class="cir-hint">（支持步进 0.5 分，满分 10 分）</span>
                    </div>
                  </div>

                  <!-- 右侧：安全事故与民生红线 -->
                  <div class="mgmt-box accident-box">
                    <div class="mgmt-box-header">
                      <div class="mbh-title">
                        <span class="mbh-badge badge-red">红线管控</span>
                        <h4>🚨 运行安全与民生一票否决核查</h4>
                      </div>
                    </div>
                    <p class="mgmt-desc">
                      生产中发生事故或民生投诉违规时点击触发对应扣罚与一票否决状态：
                    </p>
                    <div class="redline-action-chips">
                      <button
                        type="button"
                        class="redline-chip"
                        :class="{ active: unit.hasGeneralAccident, 'chip-warn': true }"
                        @click="unit.hasGeneralAccident = !unit.hasGeneralAccident; recalculateAllScores()"
                      >
                        <span class="chip-dot"></span>
                        一般安全事故（-10分）
                      </button>
                      <button
                        type="button"
                        class="redline-chip"
                        :class="{ active: unit.hasMajorAccident, 'chip-danger': true }"
                        @click="unit.hasMajorAccident = !unit.hasMajorAccident; recalculateAllScores()"
                      >
                        <span class="chip-dot"></span>
                        较大及以上事故（一票否决）
                      </button>

                      <template v-if="unit.indicators && unit.indicators.some((i) => i && i.calcType === 'complaint_rank')">
                        <button
                          type="button"
                          class="redline-chip"
                          :class="{ active: unit.isBlackListed, 'chip-danger': true }"
                          @click="unit.isBlackListed = !unit.isBlackListed; recalculateAllScores()"
                        >
                          <span class="chip-dot"></span>
                          民心网投诉黑榜（一票否决）
                        </button>
                        <button
                          type="button"
                          class="redline-chip"
                          :class="{ active: unit.isRedListed, 'chip-success': true }"
                          @click="unit.isRedListed = !unit.isRedListed; recalculateAllScores()"
                        >
                          <span class="chip-dot"></span>
                          民心网投诉红榜（+5分）
                        </button>
                      </template>
                    </div>

                    <!-- 当前状态反馈 -->
                    <div class="redline-status-callout">
                      <div v-if="!unit.hasGeneralAccident && !unit.hasMajorAccident && !unit.isBlackListed && !unit.isRedListed" class="rsc-ok">
                        ✓ 运行安全与服务红线核查通过，无异常扣分
                      </div>
                      <div v-else class="rsc-warn">
                        <span v-if="unit.hasGeneralAccident" class="rsc-item warn">⚠️ 发生一般安全事故：扣减 10 分</span>
                        <span v-if="unit.hasMajorAccident" class="rsc-item danger">🚨 发生较大及以上事故：取消当月奖励资格</span>
                        <span v-if="unit.isBlackListed" class="rsc-item danger">🚨 进入投诉通报黑榜：取消当月奖励资格</span>
                        <span v-if="unit.isRedListed" class="rsc-item success">🎉 进入投诉通报红榜：奖励 +5 分</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= 标签页 3：投诉率排名 ================= -->
      <section v-else-if="activeTab === 'complaints'" class="tab-content complaints-section">
        <!-- 统计核心卡片流 KPI -->
        <div class="calc-kpi-grid">
          <div class="calc-kpi-card kpi-month">
            <div class="kpi-icon">📅</div>
            <div class="kpi-content">
              <div class="kpi-label">考核测算月份</div>
              <div class="kpi-val text-brand">{{ selectedMonthLabel }}</div>
              <div class="kpi-sub">民生供热服务评价</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-units">
            <div class="kpi-icon">🏢</div>
            <div class="kpi-content">
              <div class="kpi-label">参评供热单位</div>
              <div class="kpi-val font-mono">5 <span class="unit-text">家</span></div>
              <div class="kpi-sub">直供管网单位横向比拼</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-budget">
            <div class="kpi-icon">🥇</div>
            <div class="kpi-content">
              <div class="kpi-label">全网最优投诉率</div>
              <div class="kpi-val text-green font-mono">
                {{ complaintRankingList.length > 0 ? complaintRankingList[0].actualValue.toFixed(2) : '0.00' }}
                <span class="unit-text">件/万㎡</span>
              </div>
              <div class="kpi-sub">
                {{ complaintRankingList.length > 0 ? complaintRankingList[0].unitName : '-' }}（当前位列第 1 名）
              </div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-reward">
            <div class="kpi-icon">📊</div>
            <div class="kpi-content">
              <div class="kpi-label">全网平均投诉率</div>
              <div class="kpi-val text-blue font-mono">
                {{ averageComplaintRate }} <span class="unit-text">件/万㎡</span>
              </div>
              <div class="kpi-sub">5 家参评单位算术平均</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-status">
            <div class="kpi-icon" :class="complaintBlackListCount > 0 ? 'red-icon' : 'green-icon'">
              {{ complaintBlackListCount > 0 ? '🚨' : '🛡️' }}
            </div>
            <div class="kpi-content">
              <div class="kpi-label">民心网通报核查</div>
              <div :class="['kpi-val font-mono', complaintBlackListCount > 0 ? 'text-red' : 'text-green']">
                {{ complaintBlackListCount > 0 ? `${complaintBlackListCount} 家黑榜` : '全员合格' }}
              </div>
              <div class="kpi-sub">
                {{ complaintRedListCount > 0 ? `${complaintRedListCount} 家进入红榜(+5分)` : '无一票否决通报' }}
              </div>
            </div>
          </div>
        </div>

        <!-- 投诉率排名主表格卡片 -->
        <div class="content-block complaints-block">
          <div class="block-header table-control-header">
            <div class="tch-left">
              <h4>📢 各单位服务投诉率实际完成值与横向排名对照表</h4>
              <span class="sub-hint">
                * 考评规则：考核万平米民心网有效投诉件数量（件/万㎡），从小到大横向排名，第 1 名得满分 20 分，排名每下降 1 名扣 2 分；可在此直接微调投诉率实际值实时联动测算
              </span>
            </div>
            <div class="tch-right-controls">
              <span class="formula-chip">计分公式：第 1 名得 20 分，每降 1 名扣 2 分</span>
            </div>
          </div>

          <div class="table-responsive">
            <table class="complaints-table modern-table">
              <thead>
                <tr>
                  <th class="th-crank">排名</th>
                  <th class="th-cunit">参评供热单位</th>
                  <th class="th-cactual">投诉率实际完成值</th>
                  <th class="th-cunit-label">计量单位</th>
                  <th class="th-cweight">权重分</th>
                  <th class="th-cscore">排名得分</th>
                  <th class="th-clist">红黑榜通报</th>
                  <th class="th-cfinal">最终计入得分</th>
                  <th class="th-crule">计分明细</th>
                  <th class="th-caction">快速操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in complaintRankingList"
                  :key="`c-rank-${item.unitCode}`"
                  :class="{
                    'tr-gold': item.rank === 1,
                    'tr-blacklisted': item.isBlackListed,
                    'tr-manual-actual': item.rawItem?.isManualActual,
                  }"
                >
                  <!-- 排名 -->
                  <td class="text-center">
                    <span v-if="item.rank === 1" class="rank-badge rank-1">🥇 1</span>
                    <span v-else-if="item.rank === 2" class="rank-badge rank-2">🥈 2</span>
                    <span v-else-if="item.rank === 3" class="rank-badge rank-3">🥉 3</span>
                    <span v-else class="rank-badge rank-normal">{{ item.rank }}</span>
                  </td>

                  <!-- 单位 -->
                  <td>
                    <div class="unit-name-cell">
                      <span class="unc-name font-bold">{{ item.unitName }}</span>
                      <span v-if="item.rank === 1" class="best-badge">全网最优</span>
                      <span
                        v-if="item.rawItem?.isManualActual"
                        class="ind-manual-tag"
                        :title="getManualTooltip(item.rawItem)"
                      >人工调整</span>
                    </div>
                  </td>

                  <!-- 投诉率实际完成值（支持编辑，手工调整着色标记） -->
                  <td>
                    <div
                      class="ind-input-cell c-input-cell"
                      :class="{ 'ind-manual-cell': item.rawItem?.isManualActual }"
                    >
                      <span
                        v-if="item.rawItem?.isManualActual"
                        class="manual-dot-badge"
                        :title="getManualTooltip(item.rawItem)"
                      >手调</span>
                      <input
                        type="number"
                        step="any"
                        min="0"
                        class="ind-input"
                        v-model.number="item.rawItem.actualValue"
                        placeholder="实际投诉率"
                        @input="onActualValueInput(item.rawItem)"
                      />
                      <button
                        v-if="item.rawItem?.isManualActual"
                        type="button"
                        class="manual-reset-btn"
                        :title="getRestoreTooltip(item.rawItem)"
                        @click="restoreSystemActualValue(item.rawItem)"
                      >↺</button>
                    </div>
                  </td>

                  <!-- 计量单位 -->
                  <td class="text-center text-muted font-mono">{{ item.unit }}</td>

                  <!-- 权重 -->
                  <td class="text-center font-mono font-bold">{{ item.weight }} 分</td>

                  <!-- 排名得分 -->
                  <td class="text-center">
                    <span class="score-pill font-mono font-bold text-blue">
                      {{ item.score.toFixed(1) }} 分
                    </span>
                  </td>

                  <!-- 红黑榜通报开关 -->
                  <td class="text-center">
                    <div class="list-toggle-group">
                      <button
                        type="button"
                        class="mini-chip-btn"
                        :class="{ active: item.isRedListed, 'chip-redlist': true }"
                        :title="item.isRedListed ? '已标记为红榜(+5分)' : '点击标记为红榜'"
                        @click="item.rawUnit.isRedListed = !item.rawUnit.isRedListed; recalculateAllScores()"
                      >
                        🌟 红榜 (+5)
                      </button>
                      <button
                        type="button"
                        class="mini-chip-btn"
                        :class="{ active: item.isBlackListed, 'chip-blacklist': true }"
                        :title="item.isBlackListed ? '已标记为黑榜(一票否决)' : '点击标记为黑榜'"
                        @click="item.rawUnit.isBlackListed = !item.rawUnit.isBlackListed; recalculateAllScores()"
                      >
                        🚨 黑榜 (否决)
                      </button>
                    </div>
                  </td>

                  <!-- 最终计入得分 -->
                  <td class="text-center">
                    <span
                      class="ind-score-badge font-mono"
                      :class="item.isBlackListed ? 'score-zero' : item.finalScore >= 20 ? 'score-win' : 'score-loss'"
                    >
                      <template v-if="item.isBlackListed">0.0 分 (否决)</template>
                      <template v-else>{{ item.finalScore.toFixed(1) }} 分</template>
                    </span>
                  </td>

                  <!-- 计分明细 -->
                  <td class="text-xs text-muted">
                    <span v-if="item.isBlackListed" class="text-red font-bold">进入黑榜，一票否决取消当月考评资格</span>
                    <span v-else-if="item.isRedListed" class="text-green font-bold">第 {{ item.rank }} 名基础分 {{ item.score }} 分 + 红榜奖励 5 分 = 25 分</span>
                    <span v-else>第 {{ item.rank }} 名：基础分 {{ item.score }} 分</span>
                  </td>

                  <!-- 操作列 -->
                  <td class="text-center">
                    <button
                      type="button"
                      class="btn-action-goto"
                      @click="goToUnitScoring(item.unitCode)"
                    >
                      详细测算 ✍️
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 可视化横向比拼条形图 -->
        <div class="content-block">
          <div class="block-header">
            <div class="bh-left">
              <h4>📊 5 家参评供热单位投诉率横向对比直方图</h4>
              <span class="bh-sub">投诉率数值越低表示供暖服务质量越优异（单位：件/万㎡）</span>
            </div>
          </div>
          <div class="complaint-bars-container">
            <div
              v-for="item in complaintRankingList"
              :key="`bar-${item.unitCode}`"
              class="complaint-bar-row"
            >
              <div class="cbar-unit-info">
                <span class="cbar-rank font-mono font-bold">#{{ item.rank }}</span>
                <span class="cbar-name">{{ item.unitName }}</span>
              </div>
              <div class="cbar-track-wrap">
                <div
                  class="cbar-fill"
                  :class="item.rank === 1 ? 'bar-gold' : item.rank <= 3 ? 'bar-blue' : 'bar-orange'"
                  :style="{ width: `${Math.min(100, Math.max(15, (item.actualValue / Math.max(0.3, maxComplaintRate)) * 100))}%` }"
                >
                  <span class="cbar-val-text font-mono">{{ Number(item.actualValue || 0).toFixed(4) }} 件/万㎡</span>
                </div>
              </div>
              <div class="cbar-score-pill font-mono">
                得分：<strong :class="item.isBlackListed ? 'text-red' : 'text-blue'">{{ item.isBlackListed ? '0' : item.finalScore }} 分</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= 标签页 3.5：额外嘉奖（按单位手动填报项目与金额） ================= -->
      <section v-else-if="activeTab === 'extra_rewards'" class="tab-content extra-rewards-section">
        <div class="calc-kpi-grid extra-kpi-grid">
          <div class="calc-kpi-card kpi-month">
            <div class="kpi-icon">📅</div>
            <div class="kpi-content">
              <div class="kpi-label">考核测算月份</div>
              <div class="kpi-val text-brand">{{ selectedMonthLabel }}</div>
              <div class="kpi-sub">额外嘉奖与月度绩效联动</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-units">
            <div class="kpi-icon">🏅</div>
            <div class="kpi-content">
              <div class="kpi-label">已申报嘉奖单位 / 项数</div>
              <div class="kpi-val font-mono">
                {{ extraRewardUnitCount }} <span class="unit-text">家 · {{ extraRewardItemCount }} 项</span>
              </div>
              <div class="kpi-sub">支持每家单位配置多项嘉奖</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-budget">
            <div class="kpi-icon">🎁</div>
            <div class="kpi-content">
              <div class="kpi-label">额外嘉奖合计总额</div>
              <div class="kpi-val text-amber font-mono">
                {{ totalExtraReward >= 0 ? '+' : '' }}¥{{ Math.round(totalExtraReward).toLocaleString() }}
              </div>
              <div class="kpi-sub">同步写入“考评兑现汇总”F列（其他嘉奖）</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-reward">
            <div class="kpi-icon">💰</div>
            <div class="kpi-content">
              <div class="kpi-label">全网拟兑现总奖金</div>
              <div class="kpi-val text-green font-mono">¥{{ Math.round(totalSimulatedReward).toLocaleString() }}</div>
              <div class="kpi-sub">
                竞赛 ¥{{ Math.round(totalBaseReward).toLocaleString() }} + 嘉奖 ¥{{ Math.round(totalExtraReward).toLocaleString() }}
              </div>
            </div>
          </div>
        </div>

        <div class="extra-notice-bar">
          <span class="notice-icon">💡</span>
          <span class="notice-text">
            <strong>填写说明：</strong>针对各参评单位在月度常规指标之外的专项表彰（如：创新奖励、应急抢险、专项保供嘉奖等），请在此按单位手动录入<strong>嘉奖项目名称</strong>与<strong>金额（元）</strong>。系统将实时累加至各单位“拟兑现奖金”及“结果总览”，并在保存数据库与导出 Excel 报表（《考评兑现汇总》“其他嘉奖”列及《计算过程明细》附表二）中自动体现。
          </span>
        </div>

        <div class="extra-units-grid">
          <div
            v-for="unit in unitsData"
            :key="`extra-${unit.code}`"
            class="content-block extra-unit-card"
          >
            <div class="extra-unit-head">
              <div class="euh-left">
                <h4 class="euh-name">{{ unit.name }}</h4>
                <span v-if="!unit.eligible" class="status-badge status-fail" :title="unit.disqualifyReason">
                  竞赛奖金否决(¥0)
                </span>
              </div>
              <div class="euh-right">
                <div class="euh-stat">
                  <span class="euh-label">竞赛指标奖金</span>
                  <strong class="font-mono text-blue">¥{{ Math.round(unit.baseReward || 0).toLocaleString() }}</strong>
                </div>
                <div class="euh-stat">
                  <span class="euh-label">额外嘉奖小计</span>
                  <strong class="font-mono text-amber">
                    {{ (unit.extraRewardTotal || 0) >= 0 ? '+' : '' }}¥{{ Math.round(unit.extraRewardTotal || 0).toLocaleString() }}
                  </strong>
                </div>
                <div class="euh-stat euh-stat-total">
                  <span class="euh-label">单位最终奖金</span>
                  <strong class="font-mono text-green">¥{{ Math.round(unit.calculatedReward || 0).toLocaleString() }}</strong>
                </div>
                <button
                  type="button"
                  class="btn-add-extra"
                  @click="addExtraRewardItem(unit)"
                >
                  ＋ 添加嘉奖项目
                </button>
              </div>
            </div>

            <div class="extra-unit-body">
              <div v-if="!unit.extraRewards || unit.extraRewards.length === 0" class="extra-empty-row">
                <span class="extra-empty-text">暂无额外嘉奖项目（默认 ¥0）</span>
                <button
                  type="button"
                  class="btn-add-extra-inline"
                  @click="addExtraRewardItem(unit)"
                >
                  点击录入嘉奖项目与金额
                </button>
              </div>

              <div v-else class="extra-items-table-wrap">
                <table class="extra-items-table">
                  <thead>
                    <tr>
                      <th style="width: 52px;">序号</th>
                      <th style="min-width: 220px;">嘉奖项目名称</th>
                      <th style="width: 170px;">嘉奖金额（元）</th>
                      <th style="min-width: 220px;">备注 / 认定依据（选填）</th>
                      <th style="width: 82px;">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, rIdx) in unit.extraRewards" :key="`${unit.code}-er-${rIdx}`">
                      <td class="text-center font-mono text-muted">{{ rIdx + 1 }}</td>
                      <td>
                        <input
                          v-model.trim="item.title"
                          type="text"
                          class="extra-input"
                          placeholder="例如：寒潮保供专项嘉奖 / 管理创新奖"
                          @input="onExtraRewardChange"
                        />
                      </td>
                      <td>
                        <div class="extra-amount-wrap">
                          <span class="extra-currency">¥</span>
                          <input
                            v-model.number="item.amount"
                            type="number"
                            step="5"
                            class="extra-input extra-input-num font-mono"
                            placeholder="0"
                            @input="onExtraRewardChange"
                          />
                        </div>
                      </td>
                      <td>
                        <input
                          v-model.trim="item.remark"
                          type="text"
                          class="extra-input"
                          placeholder="会议纪要号 / 审批说明"
                          @input="onExtraRewardChange"
                        />
                      </td>
                      <td class="text-center">
                        <button
                          type="button"
                          class="btn-del-extra"
                          title="删除该条嘉奖"
                          @click="removeExtraRewardItem(unit, rIdx)"
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= 标签页 4：结果总览 ================= -->
      <section v-else-if="activeTab === 'overview'" class="tab-content overview-section">
        <!-- 统计核心卡片流 KPI -->
        <div class="calc-kpi-grid">
          <div class="calc-kpi-card kpi-month">
            <div class="kpi-icon">📅</div>
            <div class="kpi-content">
              <div class="kpi-label">考核测算月份</div>
              <div class="kpi-val text-brand">{{ selectedMonthLabel }}</div>
              <div class="kpi-sub">供暖期月度经营考评</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-units">
            <div class="kpi-icon">🏢</div>
            <div class="kpi-content">
              <div class="kpi-label">参评单位总数</div>
              <div class="kpi-val font-mono">7 <span class="unit-text">家</span></div>
              <div class="kpi-sub">热电厂 2 家 · 供热/分厂 5 家</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-budget">
            <div class="kpi-icon">💰</div>
            <div class="kpi-content">
              <div class="kpi-label">月度总奖金池基数</div>
              <div class="kpi-val text-blue font-mono">¥280,000</div>
              <div class="kpi-sub">固定专项预算池</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-reward">
            <div class="kpi-icon">🎁</div>
            <div class="kpi-content">
              <div class="kpi-label">当前拟兑现奖金总额</div>
              <div class="kpi-val text-green font-mono">¥{{ Math.round(totalSimulatedReward).toLocaleString() }}</div>
              <div class="kpi-progress-bar">
                <div
                  class="kpi-bar-fill"
                  :style="{ width: `${Math.min(100, (totalSimulatedReward / 280000) * 100)}%` }"
                ></div>
              </div>
              <div class="kpi-sub">
                <template v-if="totalExtraReward !== 0">
                  竞赛 ¥{{ Math.round(totalBaseReward).toLocaleString() }} + 嘉奖 ¥{{ Math.round(totalExtraReward).toLocaleString() }}
                </template>
                <template v-else>
                  全网兑现率 {{ ((totalSimulatedReward / 280000) * 100).toFixed(1) }}%
                </template>
              </div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-status">
            <div class="kpi-icon" :class="disqualifiedCount > 0 ? 'red-icon' : 'green-icon'">
              {{ disqualifiedCount > 0 ? '⚠️' : '🛡️' }}
            </div>
            <div class="kpi-content">
              <div class="kpi-label">红线资格核查</div>
              <div :class="['kpi-val font-mono', disqualifiedCount > 0 ? 'text-red' : 'text-green']">
                {{ disqualifiedCount > 0 ? `${disqualifiedCount} 家取消` : '全员合格' }}
              </div>
              <div class="kpi-sub">{{ disqualifiedCount > 0 ? '末位<85分 / 事故 / 黑榜' : '无一票否决单位' }}</div>
            </div>
          </div>
        </div>

        <!-- 全网 7 家参评单位综合排名与奖金总览表 -->
        <div class="content-block overview-block">
          <div class="block-header table-control-header">
            <div class="tch-left">
              <h4>🏆 7 家参评单位综合排名与奖金总览表</h4>
              <span class="sub-hint">
                * 综合看板：按月度综合考评得分自动排名，呈现名次梯队、考核得分、兑现资格与测算拟兑现奖金，点击操作列即可跳转至测算台调整数值
              </span>
            </div>
            <div class="tch-right-controls">
              <div class="legend-pills">
                <span class="legend-pill"><span class="dot green"></span>得分达标</span>
                <span class="legend-pill"><span class="dot blue"></span>低于满分</span>
                <span class="legend-pill"><span class="dot red"></span>红线否决(¥0)</span>
              </div>
            </div>
          </div>

          <div class="table-responsive">
            <table class="leaderboard-table modern-table">
              <thead>
                <tr>
                  <th class="th-rank">排名</th>
                  <th class="th-unit-name">参评单位</th>
                  <th class="th-base">奖励基数</th>
                  <th class="th-score-bar">考核综合得分</th>
                  <th class="th-status">兑现资格</th>
                  <th class="th-extra">额外嘉奖</th>
                  <th class="th-reward">测算拟兑现奖金</th>
                  <th class="th-action">快速操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(unit, idx) in leaderboardUnits"
                  :key="`lb-${unit.code}`"
                  :class="{ 'tr-disqualified': !unit.eligible, 'tr-top-1': idx === 0 }"
                >
                  <td class="text-center font-mono">
                    <span
                      class="rank-chip"
                      :class="idx === 0 ? 'rank-1' : idx === 1 ? 'rank-2' : idx === 2 ? 'rank-3' : idx === 6 ? 'rank-last' : 'rank-normal'"
                    >
                      <span class="rank-medal" v-if="idx === 0">🥇</span>
                      <span class="rank-medal" v-else-if="idx === 1">🥈</span>
                      <span class="rank-medal" v-else-if="idx === 2">🥉</span>
                      第 {{ idx + 1 }} 名
                      <span v-if="idx === 6" class="chip-last-tag">末位</span>
                    </span>
                  </td>
                  <td>
                    <div class="lb-unit-box">
                      <strong class="lb-unit-name">{{ unit.name }}</strong>
                    </div>
                  </td>
                  <td class="text-center font-mono font-bold text-blue">
                    ¥{{ (unit.baseAmount ?? 0).toLocaleString() }}
                  </td>
                  <td>
                    <div class="lb-score-cell">
                      <div class="lb-score-num-row">
                        <strong
                          class="font-mono lb-score-val"
                          :class="(unit.score ?? 0) >= 100 ? 'text-green' : (unit.score ?? 0) >= 85 ? 'text-blue' : 'text-red'"
                        >
                          {{ (unit.score ?? 0).toFixed(2) }}
                        </strong>
                        <span class="lb-score-sub text-muted font-mono">/ 100分</span>
                      </div>
                      <div class="lb-progress-wrap">
                        <div
                          class="lb-progress-fill"
                          :class="(unit.score ?? 0) >= 100 ? 'fill-green' : (unit.score ?? 0) >= 85 ? 'fill-blue' : 'fill-red'"
                          :style="{ width: `${Math.min(100, Math.max(0, unit.score ?? 0))}%` }"
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td class="text-center">
                    <span v-if="unit.eligible && (unit.pendingCount || 0) === 0" class="status-badge status-ok">
                      ✓ 正常兑现
                    </span>
                    <span v-else-if="unit.eligible && (unit.pendingCount || 0) > 0" class="status-badge status-pending">
                      ⏳ 待月报({{ unit.pendingCount }}项)
                    </span>
                    <span v-else class="status-badge status-fail" :title="unit.disqualifyReason">
                      ✕ {{ unit.disqualifyReason }}
                    </span>
                  </td>
                  <td class="text-center font-mono">
                    <span :class="(unit.extraRewardTotal || 0) !== 0 ? 'text-amber font-bold' : 'text-muted'">
                      ¥{{ Math.round(unit.extraRewardTotal || 0).toLocaleString() }}
                    </span>
                  </td>
                  <td class="text-center">
                    <div class="calculated-reward-box">
                      <strong
                        class="reward-num font-mono"
                        :class="unit.eligible || (unit.extraRewardTotal || 0) > 0 ? 'text-green' : 'text-muted strike'"
                      >
                        ¥{{ Math.round(unit.calculatedReward || 0).toLocaleString() }}
                      </strong>
                      <span v-if="unit.extraRewardTotal" class="reward-extra-tag font-mono">
                        竞赛 ¥{{ Math.round(unit.baseReward || 0).toLocaleString() }} + 嘉奖 ¥{{ Math.round(unit.extraRewardTotal || 0).toLocaleString() }}
                      </span>
                      <span v-if="!unit.eligible && !unit.extraRewardTotal" class="text-disqualified-hint">取消资格(¥0)</span>
                      <span v-else-if="!unit.eligible && unit.extraRewardTotal" class="text-disqualified-hint">竞赛资格取消(¥0)</span>
                    </div>
                  </td>
                  <td class="text-center">
                    <button
                      type="button"
                      class="btn-lb-jump"
                      @click="goToUnitScoring(unit.code)"
                    >
                      去评分修改 ✍️
                    </button>
                  </td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="lb-tfoot-row">
                  <td colspan="2" class="text-center font-bold">全网 7 家参评单位总计</td>
                  <td class="text-center font-mono font-bold text-blue">¥280,000</td>
                  <td class="text-center text-muted font-mono">
                    全网平均 {{ (leaderboardUnits.reduce((s, u) => s + (u.score || 0), 0) / 7).toFixed(2) }} 分
                  </td>
                  <td class="text-center">
                    <span :class="disqualifiedCount > 0 ? 'text-red font-bold' : 'text-green font-bold'">
                      {{ disqualifiedCount > 0 ? `${disqualifiedCount} 家否决` : '全员合格' }}
                    </span>
                  </td>
                  <td class="text-center font-mono font-bold text-amber">
                    ¥{{ Math.round(totalExtraReward).toLocaleString() }}
                  </td>
                  <td class="text-center font-mono font-bold text-green lb-sum-reward">
                    ¥{{ Math.round(totalSimulatedReward).toLocaleString() }}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <!-- 结果深度分析与红线合规看板 -->
        <div class="overview-analytics-grid">
          <div class="content-block oa-card">
            <div class="oa-header">
              <h4>💰 奖金池分配结构与兑现情况</h4>
              <span class="oa-sub">月度总奖金池基数 280,000 元</span>
            </div>
            <div class="oa-body">
              <div class="oa-stat-row">
                <div class="oa-stat-item">
                  <span class="oa-label">计划预算总额</span>
                  <span class="oa-val font-mono text-blue font-bold">¥280,000</span>
                </div>
                <div class="oa-stat-item">
                  <span class="oa-label">测算拟兑现总额</span>
                  <span class="oa-val font-mono text-green font-bold">¥{{ Math.round(totalSimulatedReward).toLocaleString() }}</span>
                </div>
                <div class="oa-stat-item">
                  <span class="oa-label">全网奖金达成率</span>
                  <span class="oa-val font-mono text-brand font-bold">{{ ((totalSimulatedReward / 280000) * 100).toFixed(1) }}%</span>
                </div>
                <div class="oa-stat-item">
                  <span class="oa-label">结余/沉淀奖金</span>
                  <span class="oa-val font-mono text-muted font-bold">¥{{ Math.max(0, 280000 - Math.round(totalSimulatedReward)).toLocaleString() }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="content-block oa-card">
            <div class="oa-header">
              <h4>🛡️ 竞赛红线与一票否决核验结论</h4>
              <span class="oa-sub">末位且&lt;85分 / 较大及以上事故 / 投诉通报黑榜</span>
            </div>
            <div class="oa-body">
              <div v-if="disqualifiedCount === 0" class="oa-status-clean">
                <span class="oa-clean-icon">✓</span>
                <div class="oa-clean-info">
                  <strong>全网 7 家参评单位均具备奖金兑现资格</strong>
                  <p>未发生末位淘汰（最后一名得分 &ge; 85 分）、较大安全环保事故或民心网黑榜通报事件。</p>
                </div>
              </div>
              <div v-else class="oa-status-issues">
                <div
                  v-for="disUnit in leaderboardUnits.filter((u) => !u.eligible)"
                  :key="`dis-${disUnit.code}`"
                  class="oa-issue-item"
                >
                  <span class="oa-issue-tag">🚨 取消资格</span>
                  <strong class="oa-issue-name">{{ disUnit.name }}</strong>
                  <span class="oa-issue-reason">{{ disUnit.disqualifyReason }}</span>
                  <span class="oa-issue-reward font-mono">拟兑现 ¥{{ Math.round((disUnit.baseAmount ?? 0) * ((disUnit.score ?? 0) / 100)).toLocaleString() }} → ¥0</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ================= 标签页 5：供暖期兑现记录（2026.11 - 2027.03 定稿与发放汇总） ================= -->
      <section v-else-if="activeTab === 'season_records'" class="tab-content season-records-section">
        <div class="calc-kpi-grid extra-kpi-grid">
          <div class="calc-kpi-card kpi-month">
            <div class="kpi-icon">📅</div>
            <div class="kpi-content">
              <div class="kpi-label">供暖期定稿进度（26.11 - 27.03）</div>
              <div class="kpi-val text-brand font-mono">
                {{ seasonFinalSummary.count }} <span class="unit-text">/ 5 个月已定稿</span>
              </div>
              <div class="kpi-sub">另有 {{ seasonSavedPendingCount }} 个月已保存待发布定稿</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-reward">
            <div class="kpi-icon">✅</div>
            <div class="kpi-content">
              <div class="kpi-label">已定稿累计发放总奖金</div>
              <div class="kpi-val text-green font-mono">¥{{ Math.round(seasonFinalSummary.total_reward || 0).toLocaleString() }}</div>
              <div class="kpi-sub">仅计入状态为 FINAL 的正式定稿月份</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-budget">
            <div class="kpi-icon">🏅</div>
            <div class="kpi-content">
              <div class="kpi-label">已定稿构成（竞赛奖 + 嘉奖）</div>
              <div class="kpi-val text-blue font-mono" style="font-size: 1.05rem;">
                ¥{{ Math.round(seasonFinalSummary.base_reward || 0).toLocaleString() }}
                <span class="text-amber">+ ¥{{ Math.round(seasonFinalSummary.extra_reward || 0).toLocaleString() }}</span>
              </div>
              <div class="kpi-sub">指标竞赛奖金 + 额外专项嘉奖</div>
            </div>
          </div>

          <div class="calc-kpi-card kpi-units">
            <div class="kpi-icon">🗂️</div>
            <div class="kpi-content">
              <div class="kpi-label">全口径存档参考（含未定稿）</div>
              <div class="kpi-val font-mono">¥{{ Math.round(seasonAllSavedSummary.total_reward || 0).toLocaleString() }}</div>
              <div class="kpi-sub">共 {{ seasonAllSavedSummary.count }} 个月已在数据库归档</div>
            </div>
          </div>
        </div>

        <!-- 表一：月度定稿与兑现总账 -->
        <div class="content-block">
          <div class="block-header table-control-header">
            <div class="tch-left">
              <h4>📜 2026.11–2027.03 月度指标竞赛定稿与奖金汇总台账</h4>
              <span class="sub-hint">
                * “保存至系统数据库”记录为 <strong>SAVED（暂存）</strong>，“发布结果”记录为 <strong>FINAL（正式定稿）</strong>；点击进入对应月份可继续调整或重新发布定稿
              </span>
            </div>
            <div class="tch-right-controls">
              <button
                type="button"
                class="btn-tool-mini"
                :disabled="isLoadingSeasonRecords"
                @click="loadSeasonRecords"
              >
                {{ isLoadingSeasonRecords ? '刷新中...' : '🔄 刷新台账' }}
              </button>
            </div>
          </div>

          <div class="table-responsive">
            <table class="leaderboard-table modern-table season-table">
              <thead>
                <tr>
                  <th style="width: 140px;">考核月份</th>
                  <th style="width: 165px;">归档定稿状态</th>
                  <th style="width: 150px;">竞赛指标奖金</th>
                  <th style="width: 130px;">额外嘉奖</th>
                  <th style="width: 160px;">当月兑现总额</th>
                  <th style="width: 110px;">否决单位数</th>
                  <th style="width: 185px;">定稿 / 最近更新时间</th>
                  <th style="width: 130px;">快速跳转</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="rec in seasonMonthRecords"
                  :key="`sr-${rec.month}`"
                  :class="{ 'tr-season-final': rec.status === 'final' }"
                >
                  <td class="text-center font-mono font-bold">{{ formatSeasonMonthName(rec.month) }}</td>
                  <td class="text-center">
                    <span v-if="rec.status === 'final'" class="season-status-pill pill-final">
                      ✅ 已发布定稿 (FINAL)
                    </span>
                    <span v-else-if="rec.status === 'saved'" class="season-status-pill pill-saved">
                      💾 已保存暂存 (SAVED)
                    </span>
                    <span v-else class="season-status-pill pill-empty">
                      ⏳ 尚未保存记录
                    </span>
                  </td>
                  <td class="text-center font-mono">
                    {{ rec.exists ? `¥${Math.round(rec.base_reward || 0).toLocaleString()}` : '-' }}
                  </td>
                  <td class="text-center font-mono" :class="rec.exists && (rec.extra_reward || 0) !== 0 ? 'text-amber font-bold' : ''">
                    {{ rec.exists ? `¥${Math.round(rec.extra_reward || 0).toLocaleString()}` : '-' }}
                  </td>
                  <td class="text-center font-mono font-bold" :class="rec.status === 'final' ? 'text-green' : 'text-blue'">
                    {{ rec.exists ? `¥${Math.round(rec.total_reward || 0).toLocaleString()}` : '-' }}
                  </td>
                  <td class="text-center font-mono">
                    <span v-if="!rec.exists">-</span>
                    <span v-else-if="rec.disqualified_count > 0" class="text-red font-bold">{{ rec.disqualified_count }} 家</span>
                    <span v-else class="text-green">0 家</span>
                  </td>
                  <td class="text-center font-mono text-muted" style="font-size: 0.78rem;">
                    <template v-if="rec.status === 'final' && rec.published_at">
                      定稿：{{ formatDateTimeShort(rec.published_at) }}
                    </template>
                    <template v-else-if="rec.updated_at">
                      更新：{{ formatDateTimeShort(rec.updated_at) }}
                    </template>
                    <template v-else>-</template>
                  </td>
                  <td class="text-center">
                    <button
                      type="button"
                      class="btn-lb-jump"
                      @click="jumpToSeasonMonth(rec.month)"
                    >
                      {{ rec.exists ? '查看 / 修改' : '去填报测算' }}
                    </button>
                  </td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="lb-tfoot-row season-tfoot-final">
                  <td colspan="2" class="text-center font-bold">✅ 已定稿（FINAL）累计合计（{{ seasonFinalSummary.count }} 个月）</td>
                  <td class="text-center font-mono font-bold text-blue">¥{{ Math.round(seasonFinalSummary.base_reward || 0).toLocaleString() }}</td>
                  <td class="text-center font-mono font-bold text-amber">¥{{ Math.round(seasonFinalSummary.extra_reward || 0).toLocaleString() }}</td>
                  <td class="text-center font-mono font-bold text-green lb-sum-reward">¥{{ Math.round(seasonFinalSummary.total_reward || 0).toLocaleString() }}</td>
                  <td colspan="3" class="text-center text-muted" style="font-size: 0.8rem;">正式纳入供暖期兑现总账</td>
                </tr>
                <tr class="lb-tfoot-row">
                  <td colspan="2" class="text-center text-muted font-bold">全口径参考合计（含 SAVED 暂存，共 {{ seasonAllSavedSummary.count }} 个月）</td>
                  <td class="text-center font-mono text-muted">¥{{ Math.round(seasonAllSavedSummary.base_reward || 0).toLocaleString() }}</td>
                  <td class="text-center font-mono text-muted">¥{{ Math.round(seasonAllSavedSummary.extra_reward || 0).toLocaleString() }}</td>
                  <td class="text-center font-mono font-bold text-muted">¥{{ Math.round(seasonAllSavedSummary.total_reward || 0).toLocaleString() }}</td>
                  <td colspan="3" class="text-center text-muted" style="font-size: 0.8rem;">包含尚未正式定稿的暂存测算</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        <!-- 表二：7 家参评单位分月兑现矩阵 -->
        <div class="content-block">
          <div class="block-header">
            <div class="bh-left">
              <h4>🏢 7 家参评单位 2026.11–2027.03 分月奖金发放明细（供暖期累计）</h4>
              <span class="bh-sub">绿色加粗表示该月已定稿（FINAL）；灰色标注“(未定稿)”表示已保存（SAVED）但尚未点击“发布结果”</span>
            </div>
          </div>

          <div class="table-responsive">
            <table class="leaderboard-table modern-table season-matrix-table">
              <thead>
                <tr>
                  <th style="width: 130px;">参评单位</th>
                  <th v-for="rec in seasonMonthRecords" :key="`smh-${rec.month}`">
                    {{ rec.month }}
                    <div class="smh-sub">
                      {{ rec.status === 'final' ? '已定稿' : rec.status === 'saved' ? '未定稿' : '未存档' }}
                    </div>
                  </th>
                  <th style="width: 150px;">已定稿累计 (元)</th>
                  <th style="width: 150px;">全口径参考累计</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="uRow in seasonUnitMatrix" :key="`smr-${uRow.code}`">
                  <td class="font-bold text-center">{{ uRow.name }}</td>
                  <td
                    v-for="cell in uRow.cells"
                    :key="`smc-${uRow.code}-${cell.month}`"
                    class="text-center font-mono"
                  >
                    <template v-if="!cell.exists">-</template>
                    <template v-else-if="cell.status === 'final'">
                      <strong class="text-green">¥{{ Math.round(cell.reward).toLocaleString() }}</strong>
                      <div v-if="cell.extraReward" class="smc-sub text-amber">含嘉奖 ¥{{ Math.round(cell.extraReward).toLocaleString() }}</div>
                    </template>
                    <template v-else>
                      <span class="text-muted">¥{{ Math.round(cell.reward).toLocaleString() }}</span>
                      <div class="smc-sub text-muted">(未定稿)</div>
                    </template>
                  </td>
                  <td class="text-center font-mono font-bold text-green">
                    ¥{{ Math.round(uRow.finalTotal).toLocaleString() }}
                  </td>
                  <td class="text-center font-mono text-muted">
                    ¥{{ Math.round(uRow.allSavedTotal).toLocaleString() }}
                  </td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="lb-tfoot-row season-tfoot-final">
                  <td class="text-center font-bold">各月合计</td>
                  <td v-for="rec in seasonMonthRecords" :key="`smf-${rec.month}`" class="text-center font-mono font-bold">
                    <span v-if="!rec.exists">-</span>
                    <span v-else :class="rec.status === 'final' ? 'text-green' : 'text-muted'">
                      ¥{{ Math.round(rec.total_reward || 0).toLocaleString() }}
                    </span>
                  </td>
                  <td class="text-center font-mono font-bold text-green lb-sum-reward">
                    ¥{{ Math.round(seasonFinalSummary.total_reward || 0).toLocaleString() }}
                  </td>
                  <td class="text-center font-mono font-bold text-muted">
                    ¥{{ Math.round(seasonAllSavedSummary.total_reward || 0).toLocaleString() }}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AppHeader from '../../daily_report_25_26/components/AppHeader.vue'
import Breadcrumbs from '../../daily_report_25_26/components/Breadcrumbs.vue'
import {
  exportCompetitionExcel,
  fetchCompetitionAutoData,
  fetchCompetitionSeasonRecords,
  getCompetitionRecord,
  saveCompetitionRecord,
} from '../../daily_report_25_26/services/api.js'

// 1. 面包屑导航配置
const breadcrumbItems = computed(() => [
  { label: '项目选择', to: '/projects' },
  { label: '月报导入与查询', to: '/projects/monthly_data_show/pages' },
  { label: '供暖期指标竞赛专题', to: null },
])

// 2. 标签页控制
const activeTab = ref('rules') // 'rules' | 'calculation'

// 3. 月份选择逻辑：默认为上个月，但不早于 2026-11
function computeDefaultMonth() {
  const now = new Date()
  let y = now.getFullYear()
  let m = now.getMonth() // 0~11 表示 1~12 月，当前月-1 恰好为上个月
  if (m === 0) {
    y -= 1
    m = 12
  }
  const candidate = `${y}-${String(m).padStart(2, '0')}`
  if (candidate < '2026-11') {
    return '2026-11'
  }
  return candidate
}

const selectedMonth = ref(computeDefaultMonth())
const showSourceTags = ref(true)

const availableMonths = [
  { value: '2026-11', label: '2026年11月' },
  { value: '2026-12', label: '2026年12月' },
  { value: '2027-01', label: '2027年01月' },
  { value: '2027-02', label: '2027年02月' },
  { value: '2027-03', label: '2027年03月' },
  { value: '2026-01', label: '2026年01月（历史库验证）' },
  { value: '2026-02', label: '2026年02月（历史库验证）' },
  { value: '2026-03', label: '2026年03月（历史库验证）' },
  { value: '2026-2027', label: '2026-2027供暖期（总评 · 暂未启用）' },
]

const selectedMonthLabel = computed(() => {
  const found = availableMonths.find((m) => m.value === selectedMonth.value)
  return found ? found.label : selectedMonth.value
})

// 4. 7家参评单位基数定义
const unitBaseRewardList = [
  { code: 'BeiHai', name: '北海热电厂', type: '热电厂', baseAmount: 70000 },
  { code: 'XiangHai', name: '香海热电厂', type: '热电厂', baseAmount: 50000 },
  { code: 'GongRe', name: '供热公司', type: '供热管网', baseAmount: 60000 },
  { code: 'JinZhou', name: '金州热电', type: '热电分公司', baseAmount: 50000 },
  { code: 'BeiFang', name: '北方热电', type: '热电分公司', baseAmount: 30000 },
  { code: 'JinPu', name: '金普公司', type: '供热分公司', baseAmount: 10000 },
  { code: 'ZhuangHe', name: '庄河环海', type: '外购热供热', baseAmount: 10000 },
]

function getUnitTypeClass(type) {
  if (type.includes('热电厂')) return 'type-power'
  if (type.includes('管网') || type.includes('供热公司')) return 'type-network'
  if (type.includes('外购')) return 'type-outer'
  return 'type-branch'
}

// 5. 生成各单位默认指标模板工厂函数（系统自动取数项置空，手工认定项预置标准基准）
function buildInitialUnitData() {
  return [
    {
      code: 'BeiHai',
      name: '北海热电厂',
      type: '热电厂',
      baseAmount: 70000,
      score: 0,
      pendingCount: 0,
      eligible: true,
      disqualifyReason: '',
      isBlackListed: false,
      isRedListed: false,
      hasMajorAccident: false,
      hasGeneralAccident: false,
      extraRewards: [],
      indicators: [
        { name: '耗标煤总量', weight: 30, unit: '吨', hasTarget: true, targetValue: null, actualValue: null, calcType: 'energy_saving', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '厂内水耗量', weight: 10, unit: '吨', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '现货电价', weight: 20, unit: '元/MWh', hasTarget: true, targetValue: null, actualValue: null, calcType: 'spot_price', sourceLabel: '电力现货市场', sourceType: 'src-spot' },
        { name: '全厂热效率', weight: 20, unit: '%', hasTarget: true, targetValue: null, actualValue: null, calcType: 'efficiency', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '非计划停炉停机', weight: 10, unit: '次', hasTarget: false, targetValue: 0, actualValue: 0, calcType: 'shutdown', sourceLabel: '手动填报 (默认0次)', sourceType: 'src-manual' },
        null, // 第 6 个插槽留空
        { name: '安全文明生产', weight: 10, unit: '分', hasTarget: false, targetValue: 10, actualValue: 10, calcType: 'civic', sourceLabel: '手动填报 (基准满分10分)', sourceType: 'src-manual' },
      ],
    },
    {
      code: 'XiangHai',
      name: '香海热电厂',
      type: '热电厂',
      baseAmount: 50000,
      score: 0,
      pendingCount: 0,
      eligible: true,
      disqualifyReason: '',
      isBlackListed: false,
      isRedListed: false,
      hasMajorAccident: false,
      hasGeneralAccident: false,
      extraRewards: [],
      indicators: [
        { name: '耗标煤总量', weight: 30, unit: '吨', hasTarget: true, targetValue: null, actualValue: null, calcType: 'energy_saving', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '厂内水耗量', weight: 10, unit: '吨', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '现货电价', weight: 20, unit: '元/MWh', hasTarget: true, targetValue: null, actualValue: null, calcType: 'spot_price', sourceLabel: '电力现货市场', sourceType: 'src-spot' },
        { name: '全厂热效率', weight: 20, unit: '%', hasTarget: true, targetValue: null, actualValue: null, calcType: 'efficiency', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '非计划停炉停机', weight: 10, unit: '次', hasTarget: false, targetValue: 0, actualValue: 0, calcType: 'shutdown', sourceLabel: '手动填报 (默认0次)', sourceType: 'src-manual' },
        null,
        { name: '安全文明生产', weight: 10, unit: '分', hasTarget: false, targetValue: 10, actualValue: 10, calcType: 'civic', sourceLabel: '手动填报 (基准满分10分)', sourceType: 'src-manual' },
      ],
    },
    {
      code: 'GongRe',
      name: '供热公司',
      type: '供热管网',
      baseAmount: 60000,
      score: 0,
      pendingCount: 0,
      eligible: true,
      disqualifyReason: '',
      isBlackListed: false,
      isRedListed: false,
      hasMajorAccident: false,
      hasGeneralAccident: false,
      extraRewards: [],
      indicators: [
        { name: '主城区耗标煤总量', weight: 15, unit: '吨', hasTarget: true, targetValue: null, actualValue: null, calcType: 'energy_saving_half', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖热单耗', weight: 15, unit: 'GJ/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'energy_saving_half', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖电单耗', weight: 10, unit: 'kWh/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖水单耗', weight: 20, unit: 't/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '服务投诉率', weight: 20, unit: '件/万㎡', hasTarget: false, targetValue: 0, actualValue: null, calcType: 'complaint_rank', sourceLabel: '日报表', sourceType: 'src-complaint' },
        { name: '停供断管率', weight: 10, unit: '%', hasTarget: true, targetValue: 100, actualValue: 100, calcType: 'pipe_cutoff', sourceLabel: '手动填报 (默认100%)', sourceType: 'src-manual' },
        { name: '安全文明生产', weight: 10, unit: '分', hasTarget: false, targetValue: 10, actualValue: 10, calcType: 'civic', sourceLabel: '手动填报 (基准满分10分)', sourceType: 'src-manual' },
      ],
    },
    {
      code: 'JinZhou',
      name: '金州热电',
      type: '热电分公司',
      baseAmount: 50000,
      score: 0,
      pendingCount: 0,
      eligible: true,
      disqualifyReason: '',
      isBlackListed: false,
      isRedListed: false,
      hasMajorAccident: false,
      hasGeneralAccident: false,
      extraRewards: [],
      indicators: [
        { name: '耗标煤总量', weight: 30, unit: '吨', hasTarget: true, targetValue: null, actualValue: null, calcType: 'energy_saving', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖电单耗', weight: 10, unit: 'kWh/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖水单耗', weight: 20, unit: 't/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '服务投诉率', weight: 20, unit: '件/万㎡', hasTarget: false, targetValue: 0, actualValue: null, calcType: 'complaint_rank', sourceLabel: '日报表', sourceType: 'src-complaint' },
        { name: '停供断管率', weight: 10, unit: '%', hasTarget: true, targetValue: 100, actualValue: 100, calcType: 'pipe_cutoff', sourceLabel: '手动填报 (默认100%)', sourceType: 'src-manual' },
        null,
        { name: '安全文明生产', weight: 10, unit: '分', hasTarget: false, targetValue: 10, actualValue: 10, calcType: 'civic', sourceLabel: '手动填报 (基准满分10分)', sourceType: 'src-manual' },
      ],
    },
    {
      code: 'BeiFang',
      name: '北方热电',
      type: '热电分公司',
      baseAmount: 30000,
      score: 0,
      pendingCount: 0,
      eligible: true,
      disqualifyReason: '',
      isBlackListed: false,
      isRedListed: false,
      hasMajorAccident: false,
      hasGeneralAccident: false,
      extraRewards: [],
      indicators: [
        { name: '耗标煤总量', weight: 30, unit: '吨', hasTarget: true, targetValue: null, actualValue: null, calcType: 'energy_saving', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖电单耗', weight: 10, unit: 'kWh/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖水单耗', weight: 20, unit: 't/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '服务投诉率', weight: 20, unit: '件/万㎡', hasTarget: false, targetValue: 0, actualValue: null, calcType: 'complaint_rank', sourceLabel: '日报表', sourceType: 'src-complaint' },
        { name: '停供断管率', weight: 10, unit: '%', hasTarget: true, targetValue: 100, actualValue: 100, calcType: 'pipe_cutoff', sourceLabel: '手动填报 (默认100%)', sourceType: 'src-manual' },
        null,
        { name: '安全文明生产', weight: 10, unit: '分', hasTarget: false, targetValue: 10, actualValue: 10, calcType: 'civic', sourceLabel: '手动填报 (基准满分10分)', sourceType: 'src-manual' },
      ],
    },
    {
      code: 'JinPu',
      name: '金普公司',
      type: '供热分公司',
      baseAmount: 10000,
      score: 0,
      pendingCount: 0,
      eligible: true,
      disqualifyReason: '',
      isBlackListed: false,
      isRedListed: false,
      hasMajorAccident: false,
      hasGeneralAccident: false,
      extraRewards: [],
      indicators: [
        { name: '耗标煤总量', weight: 30, unit: '吨', hasTarget: true, targetValue: null, actualValue: null, calcType: 'energy_saving', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖电单耗', weight: 10, unit: 'kWh/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖水单耗', weight: 20, unit: 't/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '服务投诉率', weight: 20, unit: '件/万㎡', hasTarget: false, targetValue: 0, actualValue: null, calcType: 'complaint_rank', sourceLabel: '日报表', sourceType: 'src-complaint' },
        { name: '停供断管率', weight: 10, unit: '%', hasTarget: true, targetValue: 100, actualValue: 100, calcType: 'pipe_cutoff', sourceLabel: '手动填报 (默认100%)', sourceType: 'src-manual' },
        null,
        { name: '安全文明生产', weight: 10, unit: '分', hasTarget: false, targetValue: 10, actualValue: 10, calcType: 'civic', sourceLabel: '手动填报 (基准满分10分)', sourceType: 'src-manual' },
      ],
    },
    {
      code: 'ZhuangHe',
      name: '庄河环海',
      type: '外购热供热',
      baseAmount: 10000,
      score: 0,
      pendingCount: 0,
      eligible: true,
      disqualifyReason: '',
      isBlackListed: false,
      isRedListed: false,
      hasMajorAccident: false,
      hasGeneralAccident: false,
      extraRewards: [],
      indicators: [
        { name: '外购热量', weight: 30, unit: 'GJ', hasTarget: true, targetValue: null, actualValue: null, calcType: 'energy_saving', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖电单耗', weight: 10, unit: 'kWh/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '供暖水单耗', weight: 20, unit: 't/万㎡', hasTarget: true, targetValue: null, actualValue: null, calcType: 'consumption', sourceLabel: '月报表', sourceType: 'src-month' },
        { name: '服务投诉率', weight: 20, unit: '件/万㎡', hasTarget: false, targetValue: 0, actualValue: null, calcType: 'complaint_rank', sourceLabel: '日报表', sourceType: 'src-complaint' },
        { name: '停供断管率', weight: 10, unit: '%', hasTarget: true, targetValue: 100, actualValue: 100, calcType: 'pipe_cutoff', sourceLabel: '手动填报 (默认100%)', sourceType: 'src-manual' },
        null,
        { name: '安全文明生产', weight: 10, unit: '分', hasTarget: false, targetValue: 10, actualValue: 10, calcType: 'civic', sourceLabel: '手动填报 (基准满分10分)', sourceType: 'src-manual' },
      ],
    },
  ]
}

// 6. 核心测算状态
const unitsData = ref(buildInitialUnitData())

// 6.5 安全获取/补充各单位安全文明生产指标（兜底防越界）
function getCivicIndicator(unit) {
  if (!unit) return { actualValue: 10, score: 10, weight: 10 }
  if (!Array.isArray(unit.indicators)) unit.indicators = []
  let civic = unit.indicators.find((i) => i && (i.calcType === 'civic' || i.name === '安全文明生产'))
  if (!civic) {
    civic = {
      name: '安全文明生产',
      weight: 10,
      unit: '分',
      hasTarget: false,
      targetValue: 10,
      actualValue: 10,
      score: 10,
      calcType: 'civic',
      sourceLabel: '检查评定',
      sourceType: 'src-manual'
    }
    unit.indicators[6] = civic
  }
  return civic
}

function isBlankMetric(val) {
  return val === null || val === undefined || val === '' || Number.isNaN(Number(val))
}

const MANUAL_DEFAULT_CALC_TYPES = new Set(['shutdown', 'pipe_cutoff', 'civic'])

function getIndicatorDefaultValue(ind) {
  if (!ind) return null
  if (ind.calcType === 'shutdown') return 0
  if (ind.calcType === 'pipe_cutoff') return 100
  if (ind.calcType === 'civic') return 10
  return null
}

function onActualValueInput(ind) {
  if (!ind) return
  if (MANUAL_DEFAULT_CALC_TYPES.has(ind.calcType)) {
    const defVal = getIndicatorDefaultValue(ind)
    ind.isManualActual = isBlankMetric(ind.actualValue) || Number(ind.actualValue) !== defVal
  } else {
    // 非原生手工项（月报、现货、投诉率）：清空且无系统原值时恢复待出数状态，否则标为人工调整
    if (isBlankMetric(ind.actualValue) && isBlankMetric(ind.autoActualValue)) {
      ind.isManualActual = false
    } else {
      ind.isManualActual = true
    }
  }
  recalculateAllScores()
}

function restoreSystemActualValue(ind) {
  if (!ind) return
  if (MANUAL_DEFAULT_CALC_TYPES.has(ind.calcType)) {
    ind.actualValue = getIndicatorDefaultValue(ind)
  } else {
    ind.actualValue = ind.autoActualValue !== undefined ? ind.autoActualValue : null
  }
  ind.isManualActual = false
  recalculateAllScores()
}

function getManualTooltip(ind) {
  if (!ind) return '已完成人工调整'
  if (MANUAL_DEFAULT_CALC_TYPES.has(ind.calcType)) {
    const defVal = getIndicatorDefaultValue(ind)
    return `人工认定调整（默认基准：${defVal}${ind.unit || ''}）`
  }
  if (!isBlankMetric(ind.autoActualValue)) {
    return `人工调整覆盖（系统取数原值：${ind.autoActualValue}${ind.unit || ''}）`
  }
  return '由人工手工填写实际完成值（系统暂未出数）'
}

function getRestoreTooltip(ind) {
  if (!ind) return '恢复默认/系统值'
  if (MANUAL_DEFAULT_CALC_TYPES.has(ind.calcType)) {
    return `恢复默认基准值（${getIndicatorDefaultValue(ind)}${ind.unit || ''}）`
  }
  if (!isBlankMetric(ind.autoActualValue)) {
    return `还原为系统自动取数原值（${ind.autoActualValue}）`
  }
  return '清除手工填报并恢复待出数状态'
}

// 7. 严格按方案公式计算单个指标得分；实际值（或带目标项的计划值）未出数时返回 null
function calculateSingleIndicatorScore(item) {
  if (!item) return null
  const weight = Number(item.weight)

  if (item.calcType === 'complaint_rank') {
    if (isBlankMetric(item.actualValue)) {
      item.score = null
      return null
    }
    const score = item.score != null ? Number(item.score) : 20.0
    item.score = score
    return score
  }

  if (isBlankMetric(item.actualValue)) {
    item.score = null
    return null
  }

  if (item.hasTarget && (isBlankMetric(item.targetValue) || Number(item.targetValue) <= 0)) {
    item.score = null
    return null
  }

  const target = Number(item.targetValue)
  const actual = Number(item.actualValue)
  let score = 0

  switch (item.calcType) {
    case 'energy_saving': {
      // 完成率 = 1 + (目标值 - 完成值) / 目标值；超出/降低 1 个百分点加减 1 分；上限 120%
      const rate = 1 + (target - actual) / target
      const diffPercent = (rate - 1.0) * 100
      score = Math.max(0, Math.min(weight * 1.2, weight + diffPercent * 1.0))
      break
    }
    case 'energy_saving_half': {
      // 供热公司主城区耗标煤总量、热单耗：完成率超出/降低 1 个百分点按 0.5 分加减；上限 120%
      const rate = 1 + (target - actual) / target
      const diffPercent = (rate - 1.0) * 100
      score = Math.max(0, Math.min(weight * 1.2, weight + diffPercent * 0.5))
      break
    }
    case 'consumption': {
      // 单耗/水耗：得分 = 完成率 × 权重分；完成率 = 1 + (目标 - 完成) / 目标；上限 120%
      const rate = 1 + (target - actual) / target
      score = Math.max(0, Math.min(weight * 1.2, rate * weight))
      break
    }
    case 'spot_price': {
      // 现货电价：完成率 = 现货均价 / (统一结算点 × 1.05)；每超减 3 个百分点加减 1 分；上限 120%
      const rate = actual / target
      const diffPercent = (rate - 1.0) * 100
      score = Math.max(0, Math.min(weight * 1.2, weight + (diffPercent / 3.0) * 1.0))
      break
    }
    case 'efficiency': {
      // 全厂热效率：完成率 = 1 + (完成 - 目标) / 目标；每超减 1 个百分点加减 2 分；上限 110%
      const rate = 1 + (actual - target) / target
      const diffPercent = (rate - 1.0) * 100
      score = Math.max(0, Math.min(weight * 1.1, weight + diffPercent * 2.0))
      break
    }
    case 'shutdown': {
      // 非计划停机停炉：目标 0 次得 10 分，发生 1 次扣 5 分
      const times = Math.max(0, actual)
      score = Math.max(0, weight - times * 5)
      break
    }
    case 'civic': {
      // 安全文明生产：完成值直接为“实际评定得分”，满分 10 分（0~10分）
      score = Math.max(0, Math.min(weight, actual))
      break
    }
    case 'pipe_cutoff': {
      // 停供断管率：计划值（默认100%）得满分，每低 1% 扣 1 分；低于 95% 得 0 分
      const baseTarget = target > 0 ? target : 100.0
      if (actual < 95.0) {
        score = 0
      } else {
        const gap = Math.max(0, baseTarget - actual)
        score = Math.max(0, weight - gap * 1.0)
      }
      break
    }
    default:
      score = weight
  }

  item.score = score
  return score
}

// 8. 重新核算各单位总分与红线资格
function recalculateAllScores() {
  if (!unitsData.value || !Array.isArray(unitsData.value)) return

  // 1) 投诉率动态横向排名赋分：第1名20分，每降1名扣2分
  // 仅针对具备有效投诉率实际值的参评单位排序（排除北海、香海等纯热源电厂）
  const unitsWithComplaints = unitsData.value
    .filter((u) => {
      if (!u || !u.indicators) return false
      const cItem = u.indicators.find((i) => i && i.calcType === 'complaint_rank')
      return cItem && !isBlankMetric(cItem.actualValue)
    })
    .map((u) => {
      const cItem = u.indicators.find((i) => i && i.calcType === 'complaint_rank')
      return { code: u.code, val: Number(cItem.actualValue) }
    })
    .sort((a, b) => a.val - b.val)

  unitsWithComplaints.forEach((item, rIdx) => {
    const u = unitsData.value.find((x) => x.code === item.code)
    if (u && u.indicators) {
      const cItem = u.indicators.find((i) => i && i.calcType === 'complaint_rank')
      if (cItem) {
        cItem.score = Math.max(0, 20.0 - rIdx * 2.0)
      }
    }
  })

  // 2) 逐个单位汇总计算
  unitsData.value.forEach((unit) => {
    let total = 0
    let pendingCount = 0
    if (unit.indicators) {
      unit.indicators.forEach((ind) => {
        if (ind) {
          const indScore = calculateSingleIndicatorScore(ind)
          if (indScore === null) {
            pendingCount += 1
          } else {
            total += indScore
          }
        }
      })
    }

    // 联动同步安全文明生产实际得分
    const civic = getCivicIndicator(unit)
    if (civic) {
      if (isBlankMetric(civic.actualValue)) {
        civic.score = null
      } else {
        const val = Number(civic.actualValue)
        civic.score = Math.max(0, Math.min(10, val))
      }
    }

    // 考虑红榜加分与事故扣分
    if (unit.isRedListed) {
      total += 5.0
    }
    if (unit.hasGeneralAccident) {
      total -= 10.0
    }

    unit.pendingCount = pendingCount
    unit.score = Math.max(0, total)
  })

  // 3) 按照分数进行初步排名；仅当全网所有单位指标均已出数时，才判定“末位且低于85分”淘汰
  const allComplete = unitsData.value.every((u) => (u.pendingCount || 0) === 0)
  const sortedByScore = [...unitsData.value].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
  const lastUnit = sortedByScore[sortedByScore.length - 1]

  unitsData.value.forEach((unit) => {
    let isEligible = true
    let reason = ''

    if (unit.hasMajorAccident) {
      isEligible = false
      reason = '重大事故(一票否决)'
    } else if (unit.isBlackListed) {
      isEligible = false
      reason = '投诉黑榜(取消资格)'
    } else if (allComplete && lastUnit && unit.code === lastUnit.code && (unit.score ?? 0) < 85.0) {
      isEligible = false
      reason = '末位且<85分(淘汰)'
    }

    const baseReward = isEligible
      ? Math.round(((unit.baseAmount ?? 0) * ((unit.score ?? 0) / 100.0)) / 5) * 5
      : 0
    if (!Array.isArray(unit.extraRewards)) {
      unit.extraRewards = []
    }
    const extraRewardTotal = unit.extraRewards.reduce((sum, item) => {
      if (!item || isBlankMetric(item.amount)) return sum
      return sum + Number(item.amount)
    }, 0)

    unit.eligible = isEligible
    unit.disqualifyReason = reason
    unit.baseReward = baseReward
    unit.extraRewardTotal = extraRewardTotal
    unit.calculatedReward = baseReward + extraRewardTotal
  })
}

function normalizeLoadedUnits(list) {
  if (!Array.isArray(list)) return
  list.forEach((u) => {
    if (!u) return
    if (!Array.isArray(u.extraRewards)) {
      u.extraRewards = []
    }
    if (Array.isArray(u.indicators)) {
      u.indicators.forEach((ind) => {
        if (!ind) return
        ind.isManualActual = Boolean(ind.isManualActual)
      })
    }
  })
}

function addExtraRewardItem(unit) {
  if (!unit) return
  if (!Array.isArray(unit.extraRewards)) {
    unit.extraRewards = []
  }
  unit.extraRewards.push({
    title: '',
    amount: null,
    remark: '',
  })
  onExtraRewardChange()
}

function removeExtraRewardItem(unit, idx) {
  if (!unit || !Array.isArray(unit.extraRewards)) return
  unit.extraRewards.splice(idx, 1)
  onExtraRewardChange()
}

function onExtraRewardChange() {
  recalculateAllScores()
  if (/^\d{4}-\d{2}$/.test(String(selectedMonth.value || ''))) {
    try {
      localStorage.setItem(`competition_draft_${selectedMonth.value}`, JSON.stringify(unitsData.value))
      if (recordStatus.value !== 'saved') {
        recordStatus.value = 'draft'
        recordStatusNote.value = '已更新额外嘉奖项目并暂存本地草稿 (请记得点击保存至系统数据库)'
      }
    } catch {
      // ignore localStorage quota error
    }
  }
}

// 9. 获取特定单位当前名次
function getUnitRank(targetUnit) {
  if (!targetUnit || !unitsData.value) return 1
  const sorted = [...unitsData.value].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
  const idx = sorted.findIndex((u) => u.code === targetUnit.code)
  return idx >= 0 ? idx + 1 : 1
}

// 9.1 综合排名排行榜列表
const leaderboardUnits = computed(() => {
  return [...unitsData.value].sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
})

// 9.2 各单位垂直卡片折叠/展开状态管理
const unitExpandedMap = ref({
  BeiHai: true,
  XiangHai: true,
  GongRe: true,
  JinZhou: true,
  BeiFang: true,
  JinPu: true,
  ZhuangHe: true,
})

function toggleUnitExpand(code) {
  unitExpandedMap.value[code] = !unitExpandedMap.value[code]
}

function expandAllUnits() {
  Object.keys(unitExpandedMap.value).forEach((k) => {
    unitExpandedMap.value[k] = true
  })
}

function collapseAllUnits() {
  Object.keys(unitExpandedMap.value).forEach((k) => {
    unitExpandedMap.value[k] = false
  })
}

function scrollToUnit(code) {
  unitExpandedMap.value[code] = true
  const el = document.getElementById(`unit-card-${code}`)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function goToUnitScoring(code) {
  activeTab.value = 'calculation'
  setTimeout(() => {
    scrollToUnit(code)
  }, 100)
}

// 9.3 获取运营指标列表（过滤掉空项与安全文明指标）
function getOperationalIndicators(unit) {
  if (!unit || !Array.isArray(unit.indicators)) return []
  return unit.indicators.filter((ind) => ind && ind.calcType !== 'civic')
}

// 9.4 计算运营指标达成率文本
function getIndicatorRate(item) {
  if (!item || !item.hasTarget || isBlankMetric(item.targetValue) || isBlankMetric(item.actualValue)) return '-'
  const target = Number(item.targetValue)
  const actual = Number(item.actualValue)
  if (target <= 0) return '-'
  if (item.calcType === 'energy_saving' || item.calcType === 'energy_saving_half' || item.calcType === 'consumption') {
    const rate = (1 + (target - actual) / target) * 100
    return `${rate.toFixed(1)}%`
  }
  if (item.calcType === 'spot_price') {
    const rate = (actual / target) * 100
    return `${rate.toFixed(1)}%`
  }
  if (item.calcType === 'efficiency') {
    const rate = (1 + (actual - target) / target) * 100
    return `${rate.toFixed(1)}%`
  }
  if (item.calcType === 'pipe_cutoff') {
    return target > 0 ? `${((actual / target) * 100).toFixed(1)}%` : `${actual.toFixed(1)}%`
  }
  return '-'
}

// 9.5 获取指标计分规则精炼描述
function getIndicatorRuleSummary(item) {
  if (!item) return ''
  switch (item.calcType) {
    case 'energy_saving':
      return '超降1%加减1分，上限120%'
    case 'energy_saving_half':
      return '超降1%加减0.5分，上限120%'
    case 'consumption':
      return '完成率×权重分，上限120%'
    case 'spot_price':
      return '超降3%加减1分，上限120%'
    case 'efficiency':
      return '超降1%加减2分，上限110%'
    case 'shutdown':
      return '基准0次，非停一次扣5分'
    case 'pipe_cutoff':
      return '低1%扣1分，<95%得0分'
    case 'complaint_rank':
      return '横向排名第1名20分，降1名扣2分'
    default:
      return '依方案标准核算'
  }
}

const totalBaseReward = computed(() => {
  return unitsData.value.reduce((acc, u) => acc + (u.baseReward || 0), 0)
})

const totalExtraReward = computed(() => {
  return unitsData.value.reduce((acc, u) => acc + (u.extraRewardTotal || 0), 0)
})

const extraRewardUnitCount = computed(() => {
  return unitsData.value.filter(
    (u) => Array.isArray(u.extraRewards) && u.extraRewards.some((r) => r && ((r.title && r.title.trim()) || !isBlankMetric(r.amount))),
  ).length
})

const extraRewardItemCount = computed(() => {
  return unitsData.value.reduce((acc, u) => acc + (Array.isArray(u.extraRewards) ? u.extraRewards.length : 0), 0)
})

const totalSimulatedReward = computed(() => {
  return unitsData.value.reduce((acc, u) => acc + (u.calculatedReward || 0), 0)
})

const disqualifiedCount = computed(() => {
  return unitsData.value.filter((u) => !u.eligible).length
})

// 投诉率横向排名专用列表（5家参评供热单位）
const complaintRankingList = computed(() => {
  if (!unitsData.value || !Array.isArray(unitsData.value)) return []
  const list = []
  unitsData.value.forEach((unit) => {
    if (unit && unit.indicators) {
      const cItem = unit.indicators.find((i) => i && i.calcType === 'complaint_rank')
      if (cItem) {
        const baseScore = Number(cItem.score || 0)
        const finalScore = unit.isBlackListed ? 0 : unit.isRedListed ? baseScore + 5 : baseScore
        list.push({
          unitCode: unit.code,
          unitName: unit.name,
          unitType: unit.type,
          actualValue: Number(cItem.actualValue || 0),
          unit: cItem.unit || '件/万㎡',
          score: baseScore,
          finalScore: finalScore,
          weight: cItem.weight || 20,
          isBlackListed: !!unit.isBlackListed,
          isRedListed: !!unit.isRedListed,
          eligible: unit.eligible,
          disqualifyReason: unit.disqualifyReason,
          rawItem: cItem,
          rawUnit: unit,
        })
      }
    }
  })
  // 从小到大升序排序（投诉率越低越好）
  list.sort((a, b) => a.actualValue - b.actualValue)
  return list.map((item, idx) => ({
    ...item,
    rank: idx + 1,
  }))
})

const averageComplaintRate = computed(() => {
  if (!complaintRankingList.value || complaintRankingList.value.length === 0) return '0.00'
  const sum = complaintRankingList.value.reduce((acc, i) => acc + (i.actualValue || 0), 0)
  return (sum / complaintRankingList.value.length).toFixed(3)
})

const maxComplaintRate = computed(() => {
  if (!complaintRankingList.value || complaintRankingList.value.length === 0) return 0.3
  return Math.max(...complaintRankingList.value.map((i) => i.actualValue || 0), 0.25)
})

const complaintBlackListCount = computed(() => {
  return complaintRankingList.value.filter((i) => i.isBlackListed).length
})

const complaintRedListCount = computed(() => {
  return complaintRankingList.value.filter((i) => i.isRedListed).length
})

// 10. 操作与持久化（系统数据库直连 + 本地兜底）
const isFetchingAuto = ref(false)
const isSavingRecord = ref(false)
const isPublishingFinal = ref(false)
const isExportingExcel = ref(false)
const isLoadingSeasonRecords = ref(false)
const recordStatus = ref('default') // 'default' | 'fetched' | 'saved' | 'final' | 'draft'
const recordStatusNote = ref('')

const SEASON_MONTHS = ['2026-11', '2026-12', '2027-01', '2027-02', '2027-03']
const seasonRecordsPayload = ref({
  months: SEASON_MONTHS,
  records: SEASON_MONTHS.map((m) => ({
    month: m,
    exists: false,
    status: 'unrecorded',
    base_reward: 0,
    extra_reward: 0,
    total_reward: 0,
    disqualified_count: 0,
    published_at: null,
    updated_at: null,
    units: [],
  })),
  final_summary: { count: 0, base_reward: 0, extra_reward: 0, total_reward: 0 },
  all_saved_summary: { count: 0, base_reward: 0, extra_reward: 0, total_reward: 0 },
})

const recordStatusClass = computed(() => {
  switch (recordStatus.value) {
    case 'final': return 'status-final'
    case 'saved': return 'status-saved'
    case 'fetched': return 'status-fetched'
    case 'draft': return 'status-draft'
    default: return 'status-default'
  }
})

async function applyAutoFetchData(monthVal, showSummaryModal = true) {
  if (!/^\d{4}-\d{2}$/.test(String(monthVal || ''))) {
    if (showSummaryModal) {
      alert('供暖期总评暂未启用，请选择具体考核月份（YYYY-MM）进行取数。')
    }
    return
  }

  isFetchingAuto.value = true
  try {
    const res = await fetchCompetitionAutoData(monthVal)
    if (!res || !res.ok) {
      throw new Error(res?.detail || '取数失败')
    }

    const fetchedUnits = res.units || {}
    let matchedIndicatorCount = 0
    let preservedManualCount = 0

    // 更新 7 家单位的数据
    unitsData.value.forEach((unit) => {
      const uExt = fetchedUnits[unit.code]
      if (!uExt || !Array.isArray(unit.indicators)) return

      unit.indicators.forEach((ind) => {
        if (!ind) return
        let extItem = null

        // 统一按指标名称智能对齐
        if (ind.name.includes('标煤')) extItem = uExt.coal_consumption
        else if (ind.name === '厂内水耗量') extItem = uExt.water_consumption
        else if (ind.name === '现货电价') extItem = uExt.spot_price
        else if (ind.name === '全厂热效率') extItem = uExt.heat_efficiency
        else if (ind.name === '外购热量') extItem = uExt.purchased_heat
        else if (ind.name === '供暖热单耗') extItem = uExt.heat_unit_consumption
        else if (ind.name === '供暖电单耗') extItem = uExt.elec_unit_consumption
        else if (ind.name === '供暖水单耗') extItem = uExt.water_unit_consumption
        else if (ind.name === '服务投诉率') extItem = uExt.service_complaint_rate
        else if (ind.name === '非计划停炉停机') extItem = uExt.unplanned_outage
        else if (ind.name === '停供断管率') extItem = uExt.pipe_break_rate
        else if (ind.name === '安全文明生产') extItem = uExt.safety_production

        if (extItem) {
          if (MANUAL_DEFAULT_CALC_TYPES.has(ind.calcType)) {
            // 手动认定项仅在当前为空时填充默认值，避免覆盖已录入或已归档的事实认定数据
            if (isBlankMetric(ind.actualValue) && !isBlankMetric(extItem.actualValue)) {
              ind.actualValue = extItem.actualValue
              ind.isManualActual = false
            }
          } else {
            if (ind.hasTarget) {
              ind.targetValue = extItem.targetValue ?? null
            }
            ind.autoActualValue = extItem.actualValue ?? null
            // 已标记人工调整的完成值不被二次自动取数覆盖
            if (ind.isManualActual && !isBlankMetric(ind.actualValue)) {
              preservedManualCount++
            } else {
              ind.actualValue = extItem.actualValue ?? null
              ind.isManualActual = false
            }
          }
          if (extItem.source) {
            ind.sourceLabel = extItem.source
          }
          if (extItem.complaintCount !== undefined) {
            ind.complaintCount = extItem.complaintCount
            ind.heatingArea = extItem.heatingArea
          }
          matchedIndicatorCount++
        }
      })
    })

    recalculateAllScores()
    recordStatus.value = 'fetched'

    const spotTip = res.spot_latest_date
      ? `现货基准至 ${res.spot_latest_date}${res.spot_bill_latest_date ? ` / 账单加权至 ${res.spot_bill_latest_date}` : ' / 账单待导入'}`
      : '现货数据暂无'
    const manualTip = preservedManualCount > 0 ? `；已保留 ${preservedManualCount} 项人工调整完成值` : ''

    if (res.is_historical) {
      recordStatusNote.value = `【月报全面对接】：${selectedMonthLabel.value} 月报计划与实际值来自 monthly_data_show；${spotTip}${manualTip}`
    } else {
      recordStatusNote.value = `【实时项已联动 · 月报实际值待出数】：月度计划取自月报表，未结账前月报实际值留空；${spotTip}${manualTip}`
    }

    if (showSummaryModal) {
      // 弹窗提示抽取摘要
      const summaryMsg = [
        `【系统数据自动提取完成】`,
        `考核月份：${selectedMonthLabel.value}`,
        `月报记录匹配：${res.monthly_rows_matched || 0} 条`,
        `电力现货口径：${spotTip}`,
        `供热投诉匹配：${res.complaint_units_matched || 0} 家单位`,
        `指标对照回填：${matchedIndicatorCount} 项`,
        preservedManualCount > 0 ? `人工调整保留：${preservedManualCount} 项（琥珀色着色项未覆盖，如需还原可点单元格内 ↺）` : '',
        ``,
        res.is_historical
          ? `数据口径说明：【已结账月】月报能耗与单耗指标已从 monthly_data_show 提取计划与实际值；现货电价已按电力现货市场口径计算。`
          : `数据口径说明：【进行中当月】月度计划值取自月报表，月报实际完成值在月末出数前保持留空（不以日报累计替代）；北海/香海现货电价及供热投诉率已实时动态更新；手工项保留已有录入不被覆盖。`,
        ``,
        `您可以直接补充或调整数据，随后点击【保存至系统数据库】。`,
      ].filter((line, idx, arr) => line !== '' || arr[idx - 1] !== '').join('\n')
      alert(summaryMsg)
    }
  } catch (err) {
    if (showSummaryModal) {
      alert(`自动取数失败: ${err.message || err}`)
    } else {
      console.warn('静默自动取数异常:', err)
      recordStatus.value = 'default'
      recordStatusNote.value = '当前月份未归档，可点击【⚡ 从系统自动取数】快速提取'
    }
  } finally {
    isFetchingAuto.value = false
  }
}

async function handleAutoFetchData() {
  await applyAutoFetchData(selectedMonth.value, true)
}

async function resetToDefaultData() {
  if (!confirm(`确定重置【${selectedMonthLabel.value}】的手工认定项及红黑榜状态，并重新从系统拉取最新数据吗？`)) {
    return
  }
  localStorage.removeItem(`competition_draft_${selectedMonth.value}`)
  unitsData.value = buildInitialUnitData()
  recalculateAllScores()
  await applyAutoFetchData(selectedMonth.value, false)
}

async function onMonthChange() {
  recordStatus.value = 'default'
  recordStatusNote.value = '正在检索系统已存测算记录...'

  // 先载入基础数据结构
  unitsData.value = buildInitialUnitData()

  if (!/^\d{4}-\d{2}$/.test(String(selectedMonth.value || ''))) {
    recordStatus.value = 'default'
    recordStatusNote.value = '供暖期结束总评暂未启用（涉及其他综合要素，后续另行规划），请选择具体考核月份'
    recalculateAllScores()
    return
  }

  try {
    const res = await getCompetitionRecord(selectedMonth.value)
    if (res && res.ok && res.found && Array.isArray(res.data_payload) && res.data_payload.length === 7) {
      normalizeLoadedUnits(res.data_payload)
      unitsData.value = res.data_payload
      const dbStatus = String(res.status || 'saved').toLowerCase() === 'final' ? 'final' : 'saved'
      recordStatus.value = dbStatus
      const timeStr = dbStatus === 'final'
        ? (res.published_at || res.updated_at || '').slice(0, 19).replace('T', ' ')
        : (res.updated_at || '').slice(0, 19).replace('T', ' ')
      recordStatusNote.value = dbStatus === 'final'
        ? `已加载数据库正式定稿结果 (定稿时间：${timeStr})`
        : `已加载数据库已保存记录 (更新时间：${timeStr}，尚未点击“发布结果”定稿)`
      recalculateAllScores()
      return
    }
  } catch (err) {
    console.warn('获取数据库记录异常，尝试检查本地草稿或自动联动取数', err)
  }

  // 若数据库中无记录，检查本地草稿
  const cached = localStorage.getItem(`competition_draft_${selectedMonth.value}`)
  if (cached) {
    try {
      const parsed = JSON.parse(cached)
      if (
        Array.isArray(parsed) &&
        parsed.length === 7 &&
        parsed.every((u) => u && Array.isArray(u.indicators) && u.indicators.length >= 6)
      ) {
        unitsData.value = parsed
        normalizeLoadedUnits(unitsData.value)
        recordStatus.value = 'draft'
        recordStatusNote.value = '已加载本地暂存草稿 (尚未持久化至系统数据库)'
        recalculateAllScores()
        return
      }
    } catch {
      // ignore
    }
  }

  // 若数据库无归档且无草稿，直接自动从系统真实数据库抽取月报、电力现货与投诉数据！
  await applyAutoFetchData(selectedMonth.value, false)
}

async function persistCompetitionWithStatus(targetStatus) {
  if (!/^\d{4}-\d{2}$/.test(String(selectedMonth.value || ''))) {
    alert('供暖期总评暂未启用，请选择具体考核月份后再操作。')
    return false
  }
  const isFinal = targetStatus === 'final'
  if (isFinal) {
    isPublishingFinal.value = true
  } else {
    isSavingRecord.value = true
  }
  try {
    recalculateAllScores()
    const payload = {
      status: targetStatus,
      baseReward: totalBaseReward.value,
      extraReward: totalExtraReward.value,
      totalReward: totalSimulatedReward.value,
      disqualifiedCount: disqualifiedCount.value,
      dataPayload: unitsData.value,
      summaryPayload: {
        month: selectedMonth.value,
        status: targetStatus,
        savedAt: new Date().toISOString(),
        leaderboard: leaderboardUnits.value.map((u, idx) => ({
          rank: idx + 1,
          code: u.code,
          name: u.name,
          score: u.score,
          pendingCount: u.pendingCount || 0,
          baseReward: u.baseReward || 0,
          extraReward: u.extraRewardTotal || 0,
          reward: u.calculatedReward,
          eligible: u.eligible,
          disqualifyReason: u.disqualifyReason,
        })),
        complaintRanking: complaintRankingList.value.map((c) => ({
          rank: c.rank,
          unitCode: c.unitCode,
          unitName: c.unitName,
          actualValue: c.actualValue,
          score: c.finalScore,
        })),
      },
    }

    const res = await saveCompetitionRecord(selectedMonth.value, payload)
    if (res && res.ok) {
      recordStatus.value = isFinal ? 'final' : 'saved'
      const nowLabel = new Date().toLocaleTimeString()
      recordStatusNote.value = isFinal
        ? `已正式发布结果并标记为定稿 FINAL (${nowLabel})`
        : `已成功保存至系统数据库 SAVED (${nowLabel}，尚未发布定稿)`
      localStorage.setItem(`competition_draft_${selectedMonth.value}`, JSON.stringify(unitsData.value))
      loadSeasonRecords()
      if (isFinal) {
        alert(`【发布定稿成功 (FINAL)】\n当前月份【${selectedMonthLabel.value}】的 7 家单位指标打分、额外嘉奖与兑现奖金已正式定稿入库！\n可在“供暖期兑现记录”标签页查看供暖期累计定稿汇总。`)
      } else {
        alert(`【数据库保存成功 (SAVED)】\n当前月份【${selectedMonthLabel.value}】的 7 家单位指标测算明细、额外嘉奖与综合排名已保存至系统数据库。\n后续确认无误后，可点击【📢 发布结果】正式定稿。`)
      }
      return true
    }
    throw new Error(res?.message || '保存返回异常')
  } catch (err) {
    alert(`${isFinal ? '发布定稿' : '保存至数据库'}失败: ${err.message || err}`)
    return false
  } finally {
    if (isFinal) {
      isPublishingFinal.value = false
    } else {
      isSavingRecord.value = false
    }
  }
}

async function handleSaveRecord() {
  if (recordStatus.value === 'final') {
    const ok = confirm(
      `当前月份【${selectedMonthLabel.value}】已处于【正式定稿 (FINAL)】状态。\n` +
      `点击“保存至系统数据库”将更新数据并把状态改回“已保存暂存 (SAVED)”；若想更新并保持定稿，请改点【📢 发布结果】。\n\n确认按暂存状态 (SAVED) 保存吗？`
    )
    if (!ok) return
  }
  await persistCompetitionWithStatus('saved')
}

async function handlePublishFinal() {
  if (!/^\d{4}-\d{2}$/.test(String(selectedMonth.value || ''))) {
    alert('供暖期总评暂未启用，请选择具体考核月份后再发布。')
    return
  }
  const ok = confirm(
    `确认正式发布【${selectedMonthLabel.value}】考评结果并标记为定稿（FINAL）吗？\n\n` +
    `定稿后将重新保存全套测算与额外嘉奖数据，并正式计入“供暖期兑现记录”已定稿统计（后续仍可修改后重新保存或再次定稿）。`
  )
  if (!ok) return
  await persistCompetitionWithStatus('final')
}

const seasonMonthRecords = computed(() => seasonRecordsPayload.value?.records || [])
const seasonFinalSummary = computed(
  () => seasonRecordsPayload.value?.final_summary || { count: 0, base_reward: 0, extra_reward: 0, total_reward: 0 },
)
const seasonAllSavedSummary = computed(
  () => seasonRecordsPayload.value?.all_saved_summary || { count: 0, base_reward: 0, extra_reward: 0, total_reward: 0 },
)
const seasonSavedPendingCount = computed(() => {
  return seasonMonthRecords.value.filter((r) => r.exists && r.status !== 'final').length
})

const seasonUnitMatrix = computed(() => {
  const recs = seasonMonthRecords.value
  return unitBaseRewardList.map((baseUnit) => {
    let finalTotal = 0
    let allSavedTotal = 0
    const cells = recs.map((rec) => {
      if (!rec.exists) {
        return { month: rec.month, exists: false, status: 'unrecorded', reward: 0, extraReward: 0 }
      }
      const matched = (rec.units || []).find((u) => u.code === baseUnit.code)
      const reward = Number(matched?.reward || 0)
      const extraReward = Number(matched?.extraReward || 0)
      allSavedTotal += reward
      if (rec.status === 'final') {
        finalTotal += reward
      }
      return {
        month: rec.month,
        exists: true,
        status: rec.status,
        reward,
        extraReward,
      }
    })
    return {
      code: baseUnit.code,
      name: baseUnit.name,
      cells,
      finalTotal,
      allSavedTotal,
    }
  })
})

function formatSeasonMonthName(monthStr) {
  const [y, m] = String(monthStr || '').split('-')
  return y && m ? `${y}年${m}月` : monthStr
}

function formatDateTimeShort(isoStr) {
  if (!isoStr) return '-'
  return String(isoStr).slice(0, 16).replace('T', ' ')
}

async function loadSeasonRecords() {
  isLoadingSeasonRecords.value = true
  try {
    const res = await fetchCompetitionSeasonRecords(SEASON_MONTHS)
    if (res && res.ok) {
      seasonRecordsPayload.value = res
    }
  } catch (err) {
    console.warn('加载供暖期兑现记录失败:', err)
  } finally {
    isLoadingSeasonRecords.value = false
  }
}

function openSeasonRecordsTab() {
  activeTab.value = 'season_records'
  loadSeasonRecords()
}

async function jumpToSeasonMonth(monthStr) {
  if (!monthStr) return
  selectedMonth.value = monthStr
  activeTab.value = 'overview'
  await onMonthChange()
}

async function handleExportExcel() {
  if (!/^\d{4}-\d{2}$/.test(String(selectedMonth.value || ''))) {
    alert('供暖期总评暂未启用，请选择具体考核月份后再导出报表。')
    return
  }
  if (!Array.isArray(unitsData.value) || unitsData.value.length === 0) {
    alert('当前没有可导出的竞赛测算数据。')
    return
  }

  recalculateAllScores()
  isExportingExcel.value = true
  let blobUrl = ''
  try {
    const { blob, filename } = await exportCompetitionExcel(selectedMonth.value, {
      monthLabel: selectedMonthLabel.value,
      statusNote: recordStatusNote.value,
      unitsData: unitsData.value,
    })
    blobUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename || `供暖期指标竞赛考评表_${selectedMonth.value}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (err) {
    alert(`导出竞赛报表失败: ${err.message || err}`)
  } finally {
    if (blobUrl) {
      window.URL.revokeObjectURL(blobUrl)
    }
    isExportingExcel.value = false
  }
}

// 页面初始化即刻核算
recalculateAllScores()

// 初始化
onMounted(() => {
  onMonthChange()
})
</script>

<style scoped>
.competition-page {
  min-height: 100vh;
  background-color: #f1f5f9;
  color: #1e293b;
  display: flex;
  flex-direction: column;
}

.competition-main {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 1rem 1.5rem 3rem;
  box-sizing: border-box;
}

/* 顶部 Hero 控制栏 */
.topbar-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
  color: #fff;
  padding: 1.25rem 1.75rem;
  border-radius: 14px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.15), 0 2px 6px rgba(37, 99, 235, 0.2);
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  gap: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.hero-left {
  display: flex;
  align-items: center;
}

.title-with-badge {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.trophy-icon {
  font-size: 2.2rem;
  background: rgba(255, 255, 255, 0.12);
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
}

.title-text-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.title-row h2 {
  margin: 0;
  font-size: 1.45rem;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.02em;
}

.season-badge {
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  font-size: 0.75rem;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  font-weight: 600;
  color: #f8fafc;
}

.stage-tag {
  background: #38bdf8;
  color: #0f172a;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.hero-sub {
  margin: 0;
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.86rem;
}

/* 顶部操作与筛选 */
.hero-right {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.month-selector-card {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(8px);
  padding: 0.4rem 0.85rem;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  transition: all 0.2s ease;
}

.month-selector-card:hover {
  background: rgba(255, 255, 255, 0.2);
}

.calendar-icon {
  font-size: 1.25rem;
}

.month-select-inner {
  display: flex;
  flex-direction: column;
}

.month-label {
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.75);
  font-weight: 500;
  margin-bottom: 2px;
}

.month-select {
  background: #ffffff;
  color: #0f172a;
  border: none;
  border-radius: 6px;
  padding: 0.35rem 0.65rem;
  font-size: 0.86rem;
  font-weight: 700;
  cursor: pointer;
  outline: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.hero-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-hero {
  border: none;
  padding: 0.55rem 0.95rem;
  border-radius: 8px;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.25);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-1px);
}

.btn-primary {
  background: #3b82f6;
  color: #ffffff;
  border: 1px solid #60a5fa;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
}

.btn-primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.45);
}

.btn-hero:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.btn-auto-fetch {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.3) 0%, rgba(217, 119, 6, 0.4) 100%);
  color: #fef3c7;
  border: 1px solid rgba(251, 191, 36, 0.6);
  position: relative;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.25);
}

.btn-auto-fetch:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.45) 0%, rgba(217, 119, 6, 0.55) 100%);
  transform: translateY(-1px);
}

.btn-export {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.28) 0%, rgba(5, 150, 105, 0.42) 100%);
  color: #ecfdf5;
  border: 1px solid rgba(52, 211, 153, 0.55);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
}

.btn-export:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.45) 0%, rgba(5, 150, 105, 0.6) 100%);
  transform: translateY(-1px);
}

.btn-publish {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  color: #ffffff;
  border: 1px solid #34d399;
  box-shadow: 0 2px 10px rgba(5, 150, 105, 0.4);
}

.btn-publish:hover:not(:disabled) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(5, 150, 105, 0.5);
}

.fetch-badge-live {
  font-size: 0.65rem;
  background: #10b981;
  color: #ffffff;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

/* 数据状态条 */
.status-ribbon-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #3b82f6;
  padding: 0.65rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.82rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  flex-wrap: wrap;
  gap: 0.5rem;
}

.status-ribbon-inner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  font-size: 0.75rem;
}

.status-dot.status-final {
  color: #059669;
}

.status-dot.status-saved {
  color: #2563eb;
}

.status-ribbon-bar.is-final {
  border-left-color: #059669;
  background: linear-gradient(90deg, #ecfdf5 0%, #ffffff 30%);
}

.ribbon-state-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.12rem 0.48rem;
  border-radius: 4px;
  letter-spacing: 0.03em;
}

.badge-final {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
}

.badge-saved {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.status-dot.status-fetched {
  color: #f59e0b;
}

.status-dot.status-draft {
  color: #6366f1;
}

.status-dot.status-default {
  color: #94a3b8;
}

.status-text {
  font-weight: 600;
  color: #1e293b;
}

.status-ribbon-tip {
  color: #64748b;
  font-size: 0.76rem;
}

/* 导航 Tabs 现代化重构 */
.competition-tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  background: #ffffff;
  padding: 0.35rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
}

.tab-btn {
  background: transparent;
  border: none;
  padding: 0.65rem 1.25rem;
  font-size: 0.92rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tab-btn:hover {
  color: #1e293b;
  background: #f8fafc;
}

.tab-btn.active {
  background: #eff6ff;
  color: #1d4ed8;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.1);
}

.tab-icon {
  font-size: 1.05rem;
}

.tab-title {
  letter-spacing: -0.01em;
}

.tab-pill {
  background: #dbeafe;
  color: #1e40af;
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-weight: 700;
  pointer-events: none;
}

.tab-amount-chip {
  background: #dcfce7;
  color: #15803d;
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-weight: 700;
  font-family: ui-monospace, monospace;
}

/* 内容板块通用卡片 */
.content-block {
  background: #ffffff;
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  margin-bottom: 1.25rem;
}

.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.15rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.bh-left {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.bh-left h4 {
  margin: 0;
  font-size: 1.05rem;
  color: #0f172a;
  font-weight: 800;
}

.bh-sub {
  font-size: 0.78rem;
  color: #64748b;
}

.calc-formula {
  font-size: 0.8rem;
  color: #1d4ed8;
  font-weight: 700;
  background: #eff6ff;
  padding: 0.3rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
}

.section-hint {
  font-size: 0.78rem;
  color: #64748b;
  margin: 0.85rem 0 0;
  line-height: 1.5;
}

/* 标签页 1：规则卡片流 */
.rules-overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}

.rule-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  position: relative;
}

.rule-card.highlight-card {
  border-top: 4px solid #2563eb;
}

.rule-card.warning-card {
  border-top: 4px solid #ef4444;
  background: linear-gradient(180deg, #fffafa 0%, #ffffff 100%);
}

.card-title-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.card-icon {
  font-size: 1.4rem;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}

.blue-icon { background: #eff6ff; }
.red-icon { background: #fee2e2; }
.green-icon { background: #dcfce7; }

.card-title-wrap {
  display: flex;
  flex-direction: column;
}

.card-title-wrap h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
}

.card-subtitle {
  font-size: 0.75rem;
  color: #64748b;
}

.rule-list {
  margin: 0;
  padding-left: 1.25rem;
  font-size: 0.86rem;
  line-height: 1.7;
  color: #334155;
}

.redline-list {
  list-style: none;
  padding-left: 0;
}

.redline-list li {
  margin-bottom: 0.65rem;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  line-height: 1.6;
}

.tag-red {
  background: #fee2e2;
  color: #b91c1c;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  flex-shrink: 0;
  border: 1px solid #fecaca;
}

.tag-gray {
  background: #f1f5f9;
  color: #475569;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  flex-shrink: 0;
}

/* 7家单位基数卡片网格 */
.base-reward-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.75rem;
}

.base-reward-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.85rem 0.75rem;
  display: flex;
  flex-direction: column;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.base-reward-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  border-color: #cbd5e1;
}

.brc-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
}

.unit-type-tag {
  font-size: 0.68rem;
  padding: 0.08rem 0.35rem;
  border-radius: 4px;
  font-weight: 600;
}

.type-power { background: #dbeafe; color: #1e40af; }
.type-network { background: #ffedd5; color: #9a3412; }
.type-outer { background: #fef3c7; color: #92400e; }
.type-branch { background: #e2e8f0; color: #334155; }

.unit-share-pill {
  font-size: 0.68rem;
  color: #64748b;
  font-family: ui-monospace, monospace;
}

.unit-name {
  font-weight: 800;
  font-size: 0.95rem;
  color: #0f172a;
  margin-bottom: 0.4rem;
}

.reward-amount-box {
  display: flex;
  align-items: baseline;
  gap: 0.15rem;
  margin-bottom: 0.5rem;
}

.currency {
  font-size: 0.85rem;
  color: #1d4ed8;
  font-weight: 700;
}

.reward-amount {
  font-size: 1.25rem;
  font-weight: 800;
  color: #1d4ed8;
  font-family: ui-monospace, monospace;
}

.amount-unit {
  font-size: 0.72rem;
  color: #64748b;
}

.progress-bar-wrap {
  width: 100%;
  height: 4px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: #2563eb;
  border-radius: 999px;
}

/* 规则对照矩阵表 */
.table-responsive {
  width: 100%;
  overflow-x: auto;
}

.modern-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.82rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  overflow: hidden;
}

.modern-table th,
.modern-table td {
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  padding: 0.45rem 0.5rem;
  text-align: center;
}

.modern-table th:last-child,
.modern-table td:last-child {
  border-right: none;
}

.thead-row-1 th {
  background: #f1f5f9;
  color: #0f172a;
  font-weight: 800;
  padding: 0.55rem 0.4rem;
}

.thead-row-2 th {
  background: #f8fafc;
  color: #475569;
  font-size: 0.74rem;
  padding: 0.35rem 0.4rem;
}

.td-cat-ops {
  background: #eff6ff;
  color: #1e40af;
  font-weight: 800;
  writing-mode: vertical-lr;
  letter-spacing: 3px;
}

.td-cat-mgmt {
  background: #faf5ff;
  color: #7e22ce;
  font-weight: 800;
  writing-mode: vertical-lr;
  letter-spacing: 3px;
}

.td-highlight {
  background: #fef3c7;
  color: #92400e;
}

.td-empty {
  color: #cbd5e1;
  background: #f8fafc;
}

.tfoot-sum-row th {
  background: #f1f5f9;
  font-weight: 800;
  color: #0f172a;
  padding: 0.55rem;
}

/* 9大规则卡片分组 */
.rules-category-section {
  margin-bottom: 1.25rem;
}

.rules-category-section:last-child {
  margin-bottom: 0;
}

.rc-title {
  margin: 0 0 0.75rem 0;
  font-size: 0.95rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.rules-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 0.85rem;
}

.detail-rule-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.85rem 1rem;
  display: flex;
  flex-direction: column;
}

.drc-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}

.drc-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
}

.badge-blue { background: #dbeafe; color: #1e40af; }
.badge-green { background: #dcfce7; color: #166534; }
.badge-orange { background: #ffedd5; color: #9a3412; }
.badge-purple { background: #f3e8ff; color: #6b21a8; }
.badge-red { background: #fee2e2; color: #991b1b; }

.drc-head h5 {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: #0f172a;
}

.drc-formula {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  padding: 0.35rem 0.6rem;
  border-radius: 4px;
  font-size: 0.78rem;
  font-family: ui-monospace, monospace;
  color: #1e40af;
  margin: 0.35rem 0 0.5rem;
  line-height: 1.4;
}

.drc-desc {
  margin: 0;
  font-size: 0.8rem;
  color: #475569;
  line-height: 1.55;
}

/* ================= 标签页 2：评分测算工作台样式 ================= */
.calc-kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.calc-kpi-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem 1.15rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
  transition: all 0.2s ease;
}

.calc-kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.kpi-icon {
  font-size: 1.5rem;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: #f1f5f9;
  flex-shrink: 0;
}

.kpi-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.kpi-label {
  font-size: 0.76rem;
  color: #64748b;
  font-weight: 600;
  margin-bottom: 0.2rem;
}

.kpi-val {
  font-size: 1.35rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
  margin-bottom: 0.25rem;
}

.unit-text {
  font-size: 0.82rem;
  font-weight: 500;
  color: #64748b;
}

.kpi-sub {
  font-size: 0.72rem;
  color: #94a3b8;
}

.kpi-progress-bar {
  width: 100%;
  height: 4px;
  background: #e2e8f0;
  border-radius: 999px;
  margin-bottom: 0.25rem;
  overflow: hidden;
}

.kpi-bar-fill {
  height: 100%;
  background: #16a34a;
  border-radius: 999px;
}

.text-brand { color: #2563eb; }
.text-blue { color: #1d4ed8; }
.text-green { color: #16a34a; }
.text-red { color: #dc2626; }
.text-purple { color: #7e22ce; }
.text-orange { color: #ea580c; }
.text-danger { color: #b91c1c; }
.text-muted { color: #94a3b8; }
.font-bold { font-weight: 700; }
.font-mono { font-family: ui-monospace, monospace; }

/* ================= 1. 综合排名与奖金总览大表样式 ================= */
.overview-block {
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.25rem;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.table-control-header {
  align-items: center;
  margin-bottom: 0.85rem;
}

.tch-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.tch-left h4 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
}

.sub-hint {
  font-size: 0.78rem;
  color: #64748b;
  font-weight: 400;
}

.tch-right-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.legend-pills {
  display: flex;
  gap: 0.75rem;
  font-size: 0.74rem;
  color: #475569;
}

.legend-pill {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.green { background: #16a34a; }
.dot.blue { background: #2563eb; }
.dot.red { background: #dc2626; }

.leaderboard-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.84rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  overflow: hidden;
}

.leaderboard-table th {
  background: #f1f5f9;
  color: #334155;
  font-weight: 700;
  padding: 0.65rem 0.5rem;
  border-bottom: 1px solid #cbd5e1;
  border-right: 1px solid #e2e8f0;
  font-size: 0.8rem;
}

.leaderboard-table td {
  padding: 0.6rem 0.5rem;
  border-bottom: 1px solid #e2e8f0;
  border-right: 1px solid #e2e8f0;
  vertical-align: middle;
}

.leaderboard-table th:last-child,
.leaderboard-table td:last-child {
  border-right: none;
}

.leaderboard-table tbody tr:hover td {
  background-color: #f8fafc;
}

.tr-top-1 td {
  background: #fefce8;
}

.tr-disqualified td {
  background: #fff8f8;
}

.lb-unit-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.lb-unit-name {
  font-size: 0.95rem;
  color: #0f172a;
}

.lb-score-cell {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 130px;
}

.lb-score-num-row {
  display: flex;
  align-items: baseline;
  gap: 0.35rem;
}

.lb-score-val {
  font-size: 1.1rem;
}

.lb-score-sub {
  font-size: 0.72rem;
}

.lb-progress-wrap {
  width: 100%;
  height: 5px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.lb-progress-fill {
  height: 100%;
  border-radius: 999px;
}

.fill-green { background: #16a34a; }
.fill-blue { background: #2563eb; }
.fill-red { background: #dc2626; }

.btn-lb-jump {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  font-size: 0.76rem;
  font-weight: 700;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.btn-lb-jump:hover {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
  transform: translateY(-1px);
}

.lb-tfoot-row td {
  background: #f8fafc;
  padding: 0.75rem 0.5rem;
  border-top: 2px solid #cbd5e1;
}

.lb-sum-reward {
  font-size: 1.15rem;
}

/* ================= 2. 快速定位导航条与展开折叠工具栏 ================= */
.units-nav-toolbar {
  position: sticky;
  top: 0.75rem;
  z-index: 10;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 0.65rem 1rem;
  margin-bottom: 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.unt-left {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.unt-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: #334155;
  white-space: nowrap;
}

.unt-pills {
  display: flex;
  gap: 0.35rem;
  flex-wrap: wrap;
}

.unt-pill-btn {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  color: #334155;
  font-size: 0.76rem;
  font-weight: 600;
  padding: 0.25rem 0.55rem;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  transition: all 0.15s ease;
}

.unt-pill-btn:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
  transform: translateY(-1px);
}

.unt-rank-num {
  font-family: ui-monospace, monospace;
  font-weight: 800;
  color: #2563eb;
}

.unt-right {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.toggle-source-opt {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.76rem;
  color: #475569;
  cursor: pointer;
  user-select: none;
  background: #f8fafc;
  padding: 0.25rem 0.55rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  transition: all 0.15s ease;
}

.toggle-source-opt:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.btn-tool-mini {
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 600;
  padding: 0.25rem 0.55rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-tool-mini:hover {
  background: #e2e8f0;
  color: #0f172a;
}

/* ================= 3. 7 家参评单位垂直大卡片（从上到下排布） ================= */
.vertical-units-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.unit-vertical-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.unit-vertical-card:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06);
  border-color: #cbd5e1;
}

.unit-vertical-card.card-disqualified {
  border-left: 4px solid #ef4444;
}

/* 卡片顶部横条 Header */
.uvc-header {
  background: #f8fafc;
  padding: 0.85rem 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  border-bottom: 1px solid #e2e8f0;
  user-select: none;
  flex-wrap: wrap;
  gap: 0.85rem;
  transition: background-color 0.15s ease;
}

.uvc-header:hover {
  background: #f1f5f9;
}

.uvc-header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.uvc-seq-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 800;
  padding: 0.18rem 0.55rem;
  border-radius: 6px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #cbd5e1;
  font-family: ui-monospace, monospace;
}

.uvc-rank-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.84rem;
  font-weight: 800;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
}

.uvc-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
}

.uvc-count-tag {
  font-size: 0.72rem;
  background: #eff6ff;
  color: #2563eb;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-weight: 600;
}

.uvc-header-right {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.uvc-stat-pill {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  background: #ffffff;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.usp-label {
  font-size: 0.65rem;
  color: #64748b;
  font-weight: 500;
}

.usp-val {
  font-size: 0.95rem;
}

.usp-reward-val {
  font-size: 1.1rem;
}

.btn-toggle-expand {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 700;
  padding: 0.35rem 0.65rem;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  transition: all 0.15s ease;
}

.btn-toggle-expand:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}

.toggle-arrow {
  font-size: 0.65rem;
  transition: transform 0.2s ease;
}

.toggle-arrow.rotated {
  transform: rotate(-90deg);
}

/* 卡片主体 Body */
.uvc-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  background: #ffffff;
}

.uvc-sub-section {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.sub-section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid #f1f5f9;
}

.sst-left {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.sst-icon {
  font-size: 1.1rem;
}

.sst-name {
  font-size: 0.92rem;
  font-weight: 700;
  color: #1e293b;
}

.sst-hint-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.sst-hint {
  font-size: 0.74rem;
  color: #94a3b8;
}

.sst-manual-legend {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: #92400e;
  background: #fef3c7;
  border: 1px solid #fcd34d;
  border-radius: 999px;
  padding: 0.1rem 0.55rem;
}

.manual-swatch {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  background: #f59e0b;
  display: inline-block;
}

/* 运营指标打分表 */
.unit-ind-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  font-size: 0.84rem;
}

.unit-ind-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 700;
  padding: 0.55rem 0.65rem;
  border-bottom: 1px solid #e2e8f0;
  border-right: 1px solid #f1f5f9;
  font-size: 0.78rem;
}

.unit-ind-table td {
  padding: 0.55rem 0.65rem;
  border-bottom: 1px solid #f1f5f9;
  border-right: 1px solid #f1f5f9;
  vertical-align: middle;
}

.unit-ind-table th:last-child,
.unit-ind-table td:last-child {
  border-right: none;
}

.unit-ind-table tbody tr:hover td {
  background-color: #fcfdfe;
}

.th-num { width: 45px; }
.th-ind-name { min-width: 140px; }
.th-weight { width: 85px; }
.th-target { width: 145px; }
.th-actual { width: 145px; }
.th-unit { width: 90px; }
.th-rate { width: 85px; }
.th-rule { min-width: 200px; }
.th-score { width: 110px; }

.ind-name-box {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.ind-main-name {
  color: #0f172a;
}

.ind-tag-row {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  flex-wrap: wrap;
}

.ind-source-tag {
  font-size: 0.65rem;
  background: #f1f5f9;
  color: #64748b;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
}

.ind-manual-tag {
  font-size: 0.65rem;
  font-weight: 700;
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
  padding: 0.05rem 0.38rem;
  border-radius: 4px;
}

.row-manual-actual td {
  background-color: #fffbeb !important;
}

.ind-input-cell {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0.2rem 0.5rem;
  transition: all 0.15s ease;
}

.ind-input-cell.ind-manual-cell {
  background: #fef3c7;
  border-color: #f59e0b;
  border-left: 3px solid #d97706;
  padding-left: 0.35rem;
}

.ind-input-cell.ind-manual-cell .ind-input {
  color: #92400e;
}

.ind-input-cell.ind-manual-cell:focus-within {
  background: #fffbeb;
  border-color: #d97706;
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.22);
}

.manual-dot-badge {
  flex-shrink: 0;
  font-size: 0.62rem;
  font-weight: 700;
  line-height: 1.2;
  color: #92400e;
  background: #fde68a;
  border: 1px solid #f59e0b;
  border-radius: 4px;
  padding: 0.08rem 0.28rem;
  white-space: nowrap;
}

.manual-reset-btn {
  flex-shrink: 0;
  border: none;
  background: rgba(217, 119, 6, 0.14);
  color: #92400e;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  padding: 0;
}

.manual-reset-btn:hover {
  background: #f59e0b;
  color: #ffffff;
}

.ind-input-cell:focus-within {
  background: #ffffff;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.ind-target-cell:focus-within {
  border-color: #0284c7;
  box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
}

.target-input {
  color: #0369a1;
}

.ind-fixed-target-box {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.2rem 0.5rem;
  background: #f1f5f9;
  border-radius: 6px;
  border: 1px dashed #cbd5e1;
}

.ind-fixed-target-box.fixed-target-right {
  justify-content: flex-end;
  padding-right: 0.65rem;
}

.ind-fixed-val {
  font-weight: 700;
  color: #475569;
  font-size: 0.82rem;
}

.ind-fixed-tag {
  font-size: 0.68rem;
  color: #64748b;
  background: #e2e8f0;
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
}

.ind-input {
  border: none;
  background: transparent;
  outline: none;
  width: 100%;
  font-family: ui-monospace, monospace;
  font-size: 0.88rem;
  font-weight: 700;
  color: #0f172a;
  text-align: right;
}

.ind-input-unit {
  font-size: 0.72rem;
  color: #94a3b8;
  white-space: nowrap;
}

.ind-score-badge {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  font-size: 0.84rem;
  font-weight: 800;
}

.score-win {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.score-loss {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.score-pending {
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #cbd5e1;
  font-weight: 600;
}

/* ================= 4. 管理指标与安全红线核验区 ================= */
.mgmt-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.mgmt-box {
  border-radius: 10px;
  padding: 1rem 1.15rem;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.civic-box {
  background: #fdfaff;
  border: 1px solid #e9d5ff;
}

.accident-box {
  background: #fff8f8;
  border: 1px solid #fecaca;
}

.mgmt-box-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mbh-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.mbh-title h4 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
}

.mbh-badge {
  font-size: 0.68rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-weight: 700;
}

.badge-purple { background: #f3e8ff; color: #7e22ce; }
.badge-red { background: #fee2e2; color: #b91c1c; }

.mgmt-desc {
  margin: 0;
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.45;
}

.civic-input-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.35rem;
  flex-wrap: wrap;
}

.cir-label {
  font-size: 0.82rem;
  font-weight: 700;
  color: #6b21a8;
}

.cir-input-box {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: #ffffff;
  border: 1px solid #c4b5fd;
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
  transition: all 0.15s ease;
}

.cir-input-box.cir-manual-box {
  background: #fef3c7;
  border-color: #f59e0b;
  border-left: 3px solid #d97706;
}

.cir-input-box.cir-manual-box .civic-score-input,
.cir-input-box.cir-manual-box .cir-unit {
  color: #92400e;
}

.civic-score-input {
  border: none;
  background: transparent;
  outline: none;
  width: 65px;
  font-family: ui-monospace, monospace;
  font-size: 1rem;
  font-weight: 800;
  color: #6b21a8;
  text-align: right;
}

.cir-unit {
  font-size: 0.8rem;
  font-weight: 700;
  color: #6b21a8;
}

.cir-hint {
  font-size: 0.72rem;
  color: #94a3b8;
}

.redline-action-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.35rem;
}

.redline-chip {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 600;
  padding: 0.3rem 0.65rem;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  transition: all 0.15s ease;
}

.redline-chip:hover {
  background: #f8fafc;
  color: #0f172a;
}

.chip-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #94a3b8;
}

.redline-chip.active.chip-warn {
  background: #fef3c7;
  color: #92400e;
  border-color: #f59e0b;
}

.redline-chip.active.chip-warn .chip-dot {
  background: #d97706;
}

.redline-chip.active.chip-danger {
  background: #fee2e2;
  color: #991b1b;
  border-color: #ef4444;
}

.redline-chip.active.chip-danger .chip-dot {
  background: #dc2626;
}

.redline-chip.active.chip-success {
  background: #dcfce7;
  color: #166534;
  border-color: #22c55e;
}

.redline-chip.active.chip-success .chip-dot {
  background: #16a34a;
}

.redline-status-callout {
  margin-top: 0.25rem;
  font-size: 0.76rem;
}

.rsc-ok {
  color: #16a34a;
  font-weight: 700;
}

.rsc-warn {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.rsc-item {
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.rsc-item.warn { background: #fef3c7; color: #92400e; }
.rsc-item.danger { background: #fee2e2; color: #b91c1c; }
.rsc-item.success { background: #dcfce7; color: #166534; }

/* ================= 5. 通用徽章与文字辅助 ================= */
.rank-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 800;
  background: #f1f5f9;
  color: #475569;
}

.rank-chip.rank-1, .uvc-rank-badge.rank-1 {
  background: #fef9c3;
  color: #854d0e;
  border: 1px solid #fde047;
}

.rank-chip.rank-2, .uvc-rank-badge.rank-2 {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
}

.rank-chip.rank-3, .uvc-rank-badge.rank-3 {
  background: #ffedd5;
  color: #9a3412;
  border: 1px solid #fdba74;
}

.rank-chip.rank-last, .uvc-rank-badge.rank-last {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

.chip-last-tag, .uvc-last-tag {
  font-size: 0.65rem;
  background: #ef4444;
  color: #ffffff;
  padding: 0 0.3rem;
  border-radius: 3px;
  margin-left: 2px;
}

.rank-medal {
  font-size: 0.95rem;
}

.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
  font-size: 0.76rem;
  font-weight: 700;
  white-space: nowrap;
}

.status-ok {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.status-fail {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.status-pending {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
}

.calculated-reward-box {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.reward-num {
  font-size: 1.15rem;
  font-weight: 800;
}

.strike {
  text-decoration: line-through;
}

.text-disqualified-hint {
  font-size: 0.7rem;
  color: #dc2626;
  font-weight: 700;
  margin-top: 2px;
}

/* ================= 6. 结果总览深度看板与结构分析 ================= */
.overview-analytics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  margin-top: 1.25rem;
}

.oa-card {
  padding: 1.25rem 1.5rem;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.oa-header {
  margin-bottom: 1rem;
}

.oa-header h4 {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 800;
  color: #0f172a;
}

.oa-sub {
  font-size: 0.78rem;
  color: #64748b;
}

.oa-stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
}

.oa-stat-item {
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.oa-label {
  font-size: 0.72rem;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.oa-val {
  font-size: 1.15rem;
}

.oa-status-clean {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 1rem 1.25rem;
}

.oa-clean-icon {
  font-size: 1.4rem;
  color: #16a34a;
  background: #dcfce7;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.oa-clean-info strong {
  color: #15803d;
  font-size: 0.95rem;
}

.oa-clean-info p {
  margin: 0.25rem 0 0;
  font-size: 0.8rem;
  color: #166534;
}

.oa-status-issues {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.oa-issue-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  font-size: 0.82rem;
  flex-wrap: wrap;
}

.oa-issue-tag {
  background: #ef4444;
  color: #ffffff;
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
}

.oa-issue-name {
  color: #0f172a;
}

.oa-issue-reason {
  color: #dc2626;
  font-weight: 600;
}

.oa-issue-reward {
  margin-left: auto;
  color: #991b1b;
  font-weight: 700;
}

/* ================= 6. 投诉率排名专用样式 ================= */
.pill-complaints {
  background: #ffedd5;
  color: #c2410c;
  border: 1px solid #fed7aa;
}

.th-crank { width: 75px; }
.th-cunit { min-width: 130px; }
.th-ctype { width: 95px; }
.th-cactual { width: 150px; }
.th-cunit-label { width: 90px; }
.th-cweight { width: 85px; }
.th-cscore { width: 95px; }
.th-clist { width: 190px; }
.th-cfinal { width: 120px; }
.th-crule { min-width: 220px; }
.th-caction { width: 110px; }

.c-input-cell {
  width: 135px;
  margin: 0 auto;
}

.best-badge {
  font-size: 0.65rem;
  background: #fef08a;
  color: #854d0e;
  border: 1px solid #facc15;
  font-weight: 700;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
}

.list-toggle-group {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.35rem;
}

.mini-chip-btn {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.2rem 0.45rem;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.mini-chip-btn:hover {
  background: #ffffff;
  color: #1e293b;
}

.mini-chip-btn.chip-redlist.active {
  background: #dcfce7;
  color: #15803d;
  border-color: #86efac;
  font-weight: 700;
}

.mini-chip-btn.chip-blacklist.active {
  background: #fee2e2;
  color: #b91c1c;
  border-color: #fca5a5;
  font-weight: 700;
}

.score-zero {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.tr-blacklisted td {
  background-color: #fff5f5 !important;
}

.tr-manual-actual td {
  background-color: #fffbeb !important;
}

.complaints-notice-bar {
  margin-top: 1rem;
  padding: 0.75rem 1rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 0.8rem;
  color: #166534;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  line-height: 1.5;
}

.complaints-notice-bar .notice-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

/* 投诉率直方对比图 */
.complaint-bars-container {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 0.5rem 0;
}

.complaint-bar-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.cbar-unit-info {
  width: 140px;
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
}

.cbar-rank {
  font-size: 0.82rem;
  color: #64748b;
  width: 24px;
}

.cbar-name {
  font-size: 0.88rem;
  font-weight: 700;
  color: #1e293b;
}

.cbar-track-wrap {
  flex: 1;
  background: #f1f5f9;
  height: 28px;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.cbar-fill {
  height: 100%;
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 0 0.65rem;
  transition: width 0.4s ease;
}

.cbar-fill.bar-gold {
  background: linear-gradient(90deg, #facc15, #eab308);
  color: #713f12;
}

.cbar-fill.bar-blue {
  background: linear-gradient(90deg, #38bdf8, #0284c7);
  color: #ffffff;
}

.cbar-fill.bar-orange {
  background: linear-gradient(90deg, #fb923c, #ea580c);
  color: #ffffff;
}

.cbar-val-text {
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
}

.cbar-score-pill {
  width: 130px;
  text-align: right;
  font-size: 0.84rem;
  color: #64748b;
  flex-shrink: 0;
}

/* 额外嘉奖标签页样式 */
.pill-extra {
  background: #fef3c7;
  color: #b45309;
  font-weight: 700;
}

.usp-extra-hint,
.reward-extra-tag {
  display: inline-block;
  margin-top: 2px;
  font-size: 0.72rem;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
}

.extra-kpi-grid {
  grid-template-columns: repeat(4, 1fr);
}

.text-amber {
  color: #d97706;
}

.extra-notice-bar {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  padding: 0.8rem 1rem;
  border-radius: 10px;
  font-size: 0.84rem;
  line-height: 1.55;
  margin-bottom: 1rem;
}

.extra-units-grid {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.extra-unit-card {
  padding: 0.95rem 1.15rem;
}

.extra-unit-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}

.euh-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.euh-name {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 700;
  color: #0f172a;
}

.euh-right {
  display: flex;
  align-items: center;
  gap: 1.1rem;
  flex-wrap: wrap;
}

.euh-stat {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-size: 0.82rem;
}

.euh-label {
  font-size: 0.72rem;
  color: #64748b;
}

.euh-stat-total {
  padding-left: 0.9rem;
  border-left: 1px solid #e2e8f0;
}

.btn-add-extra {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  padding: 0.42rem 0.8rem;
  border-radius: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-add-extra:hover {
  background: #dbeafe;
  border-color: #93c5fd;
}

.extra-unit-body {
  padding-top: 0.75rem;
}

.extra-empty-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 0.65rem 0.9rem;
  font-size: 0.83rem;
  color: #64748b;
}

.btn-add-extra-inline {
  background: transparent;
  border: none;
  color: #2563eb;
  font-weight: 600;
  font-size: 0.82rem;
  cursor: pointer;
}

.btn-add-extra-inline:hover {
  text-decoration: underline;
}

.extra-items-table-wrap {
  overflow-x: auto;
}

.extra-items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.extra-items-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  text-align: left;
  padding: 0.5rem 0.65rem;
  border-bottom: 1px solid #e2e8f0;
}

.extra-items-table td {
  padding: 0.5rem 0.65rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.extra-input {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0.4rem 0.6rem;
  font-size: 0.85rem;
  color: #0f172a;
  background: #ffffff;
  outline: none;
  box-sizing: border-box;
}

.extra-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.extra-amount-wrap {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.extra-currency {
  color: #64748b;
  font-weight: 600;
}

.extra-input-num {
  text-align: right;
}

.btn-del-extra {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  padding: 0.3rem 0.6rem;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-del-extra:hover {
  background: #fee2e2;
}

/* 供暖期兑现记录标签页样式 */
.season-records-section .season-table th,
.season-records-section .season-matrix-table th {
  text-align: center;
}

.th-extra {
  width: 115px;
  text-align: center;
}

.season-status-pill {
  display: inline-block;
  font-size: 0.76rem;
  font-weight: 700;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
}

.pill-final {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
}

.pill-saved {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.pill-empty {
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #cbd5e1;
}

.tr-season-final {
  background-color: #f0fdf4;
}

.season-tfoot-final td {
  background-color: #ecfdf5 !important;
  border-top: 2px solid #a7f3d0;
}

.smh-sub {
  font-size: 0.68rem;
  font-weight: 500;
  color: #64748b;
  margin-top: 2px;
}

.smc-sub {
  font-size: 0.68rem;
  margin-top: 2px;
}

/* 响应式适配 */
@media (max-width: 1200px) {
  .calc-kpi-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .base-reward-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 900px) {
  .rules-overview-grid {
    grid-template-columns: 1fr;
  }
  .calc-kpi-grid {
    grid-template-columns: 1fr;
  }
  .base-reward-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .topbar-hero {
    flex-direction: column;
    align-items: flex-start;
  }
  .hero-right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
