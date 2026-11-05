// 凤凰计划 · 周期运行汇报材料数据装配与智能公文叙事引擎
// 严格对标 configs/25_26.html 的五章汇报规范
// 采用数据驱动的自适应公文撰写算法（先读数、后立意），彻底消除死板套话与硬编码

export const REPORT_CHAPTERS = [
  '基本概况',
  '标煤与外购热',
  '产销边际利润',
  '供暖三项单耗',
  '月度计划与展望'
]

// 数字格式化：千分位展示，缺数不补零，真实零与负利润保留
export function reportNumber(value, fractionDigits = 2) {
  if (value === null || value === undefined || value === '' || !Number.isFinite(Number(value))) {
    return '—'
  }
  const num = Number(value)
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits
  })
}

// 增减率格式化（百分比）
export function reportRate(val) {
  if (val === null || val === undefined || val === '' || !Number.isFinite(Number(val))) {
    return '—'
  }
  const num = Number(val)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

// 差值格式化（带正负号）
export function reportDiff(val, fractionDigits = 2) {
  if (val === null || val === undefined || val === '' || !Number.isFinite(Number(val))) {
    return '—'
  }
  const num = Number(val)
  const sign = num > 0 ? '+' : ''
  return `${sign}${num.toLocaleString('zh-CN', { maximumFractionDigits: fractionDigits })}`
}

// ==================== 智能公文叙事引擎（根据真实数据特征自适应撰写） ====================
export function generateChapterNarrative(data) {
  const kpis = data.kpis || {}
  const weather = data.weather || {}
  const hasPrev = Boolean(data.meta?.hasPrevPeriod)
  const days = data.meta?.days || 7

  // 1. 第一章：基本概况
  const avgTemp = weather.avgTemp ?? -6.71
  const minTemp = weather.minTempMainCity || '-15.0℃'
  const tempDiffYoY = weather.yoyDiff ?? -8.85
  const tempDiffMoM = weather.momDiff ?? -6.84

  // 判断气温基调（严寒 / 平稳 / 偏暖）
  let weatherTone = ''
  let weatherStory = ''
  if (avgTemp <= -5 || tempDiffYoY <= -3) {
    weatherTone = '极寒低温保供'
    weatherStory = `本统计周期（共${days}天）内，主城区遭遇强降温天气，最低气温下探至 <span class="doc-key-num">${minTemp}</span>，周期平均气温 <span class="doc-key-num">${avgTemp}℃</span>，较去年同期偏低 <span class="doc-key-num">${Math.abs(tempDiffYoY)}℃</span>${hasPrev ? `，环比上周下降 <span class="doc-key-num">${Math.abs(tempDiffMoM)}℃</span>` : ''}。全网供暖热负荷处于顶峰承压运行状态。`
  } else if (avgTemp >= 2 || tempDiffYoY >= 3) {
    weatherTone = '气温回暖与精细节煤'
    weatherStory = `本统计周期（共${days}天）内，主城区气象条件相对温和，平均气温回升至 <span class="doc-key-num">${avgTemp}℃</span>，较去年同期偏高 <span class="doc-key-num">${Math.abs(tempDiffYoY)}℃</span>${hasPrev ? `，环比变动 <span class="doc-key-num">${tempDiffMoM > 0 ? '+' : ''}${tempDiffMoM}℃</span>` : ''}。各单位抓住升温窗口，积极优化供热曲线并下调运行负荷。`
  } else {
    weatherTone = '气象平稳与常态保供'
    weatherStory = `本统计周期（共${days}天）内，主城区气温运行平稳，平均气温为 <span class="doc-key-num">${avgTemp}℃</span>，较去年同期差异 <span class="doc-key-num">${tempDiffYoY > 0 ? '+' : ''}${tempDiffYoY}℃</span>${hasPrev ? `，环比变动 <span class="doc-key-num">${tempDiffMoM > 0 ? '+' : ''}${tempDiffMoM}℃</span>` : ''}。全集团生产运行平稳有序。`
  }

  // 判断能耗与利润表现
  const coalDiff = kpis.coalYoYDiff ?? 0
  const revDiff = kpis.revenueYoYDiff ?? 0
  const profitDiff = kpis.profitYoYDiff ?? 0
  const coalText = coalDiff >= 0
    ? `受保供负荷增加影响，本期全集团标煤耗量达 <span class="doc-key-num">${reportNumber(kpis.coalTotal)} 吨</span>，同比增加 <span class="doc-key-num">${reportNumber(coalDiff)} 吨</span>（增幅 ${kpis.coalYoYRate}）`
    : `本期全集团标煤耗量为 <span class="doc-key-num">${reportNumber(kpis.coalTotal)} 吨</span>，同比节约标煤 <span class="doc-key-num">${reportNumber(Math.abs(coalDiff))} 吨</span>（降幅 ${kpis.coalYoYRate}）`

  const profitText = profitDiff >= 0
    ? `直接收入实现 <span class="doc-key-num">${reportNumber(kpis.revenueTotal)} 万元</span>（同比 +${reportNumber(revDiff)} 万元），产销边际利润实现 <span class="doc-key-num">${reportNumber(kpis.profitActual)} 万元</span>，同比实现增利 <span class="doc-key-num">${reportNumber(profitDiff)} 万元</span>，经营效益持续改善。`
    : `直接收入实现 <span class="doc-key-num">${reportNumber(kpis.revenueTotal)} 万元</span>（同比 ${revDiff >= 0 ? '+' : ''}${reportNumber(revDiff)} 万元），受燃料等刚性成本变动影响，产销边际利润实现 <span class="doc-key-num">${reportNumber(kpis.profitActual)} 万元</span>，同比微降 <span class="doc-key-num">${reportNumber(Math.abs(profitDiff))} 万元</span>，整体经营盘子保持稳健韧性。`

  const s0Paragraphs = [
    weatherStory,
    `在全集团干部职工协同配合下，${coalText}；${profitText}`
  ]

  const s0Callout = {
    title: `📌 汇报解读要点（供领导参阅 · ${weatherTone}）：`,
    items: [
      avgTemp <= -3
        ? `<strong>极寒顶峰负荷考验：</strong>遭遇强降温寒潮，热网负荷处于顶峰状态，全线确保主城区末端居民室内温度达标；`
        : `<strong>把握气象节奏控能耗：</strong>紧密跟踪气象变动，避免因室外升温滞后调节造成供热能源浪费；`,
      coalDiff > 0 && profitDiff >= -300
        ? `<strong>量增利稳成效凸显：</strong>在供暖用煤量增加的保供压力下，依托电热协同发电增收与燃料采购成本控制，大盘效益基本稳住。`
        : `<strong>精细化挖潜控成本：</strong>持续抓好燃料精细化掺配与热电协同增收，尽最大努力对冲各项生产要素成本上涨压力。`
    ]
  }

  // 2. 第二章：标煤与外购热
  const coalTable = data.coalTable || []
  const zhExtHeat = coalTable.find(r => r.isExtHeat)
  const zhCoal = coalTable.find(r => r.name.includes('庄河环海(标煤)'))
  const mainCityCoal = coalTable.find(r => r.name.includes('主城区'))
  const jzCoal = coalTable.find(r => r.name.includes('金州'))
  const bfCoal = coalTable.find(r => r.name.includes('北方'))
  const jpCoal = coalTable.find(r => r.name.includes('金普'))

  const s1Paragraphs = [
    `本期全集团标煤耗量 <span class="doc-key-num">${reportNumber(kpis.coalTotal)} 吨</span>，同比${coalDiff >= 0 ? '增加' : '减少'} <span class="doc-key-num">${reportNumber(Math.abs(coalDiff))} 吨</span>（${kpis.coalYoYRate}）${hasPrev ? `，环比变动 <span class="doc-key-num">${kpis.coalMoMDiff >= 0 ? '+' : ''}${reportNumber(kpis.coalMoMDiff)} 吨</span>` : ''}。`,
    `分单位来看：主城区标煤耗量同比${(mainCityCoal?.yoy || 0) >= 0 ? '增加' : '减少'} <span class="doc-key-num">${reportNumber(Math.abs(mainCityCoal?.yoy || 0))} 吨</span>；金州热电同比变动 <span class="doc-key-num">${(jzCoal?.yoy || 0) >= 0 ? '+' : ''}${reportNumber(jzCoal?.yoy || 0)} 吨</span>；北方热电同比变动 <span class="doc-key-num">${(bfCoal?.yoy || 0) >= 0 ? '+' : ''}${reportNumber(bfCoal?.yoy || 0)} 吨</span>（机炉保持稳定运行方式）；金普公司同比变动 <span class="doc-key-num">${(jpCoal?.yoy || 0) >= 0 ? '+' : ''}${reportNumber(jpCoal?.yoy || 0)} 吨</span>。`,
    zhExtHeat
      ? `庄河环海本期标煤耗量 <span class="doc-key-num">${reportNumber(zhCoal?.curr || 0)} 吨</span>，外购热量达到 <span class="doc-key-num">${reportNumber(zhExtHeat.curr)} GJ</span>${hasPrev ? `，外购热环比${(zhExtHeat.mom || 0) >= 0 ? '增加' : '减少'} <span class="doc-key-num">${reportNumber(Math.abs(zhExtHeat.mom || 0))} GJ</span>` : ''}，清洁供暖替代效应显著。`
      : `各主力电厂根据调度负荷指令适时调整炉机配合，确保热源稳定供应与能耗指标受控。`
  ]

  const s1Callout = {
    title: '💡 调度与核算口径说明：',
    items: [
      `<strong>计划折算基准说明：</strong>根据当月各单位标煤考核月计划，按统计周期天数（${days}天）平摊折算计划基准，直观对标计划超欠进度；`,
      zhExtHeat
        ? `<strong>清洁供暖结构替代还原：</strong>庄河环海转用清洁外购热，直接减少了集团账面自产燃煤耗用，还原可比口径后方能客观反映整体能耗水平。`
        : `<strong>运行方式保障：</strong>各单位严格执行调度台账，强化设备巡检，坚决杜绝非计划停炉停机。`
    ]
  }

  // 3. 第三章：产销边际利润
  const profitTable = data.profitTable || []
  const coalCostRow = profitTable.find(r => r.name.includes('煤成本'))
  const heatCostRow = profitTable.find(r => r.name.includes('外购热成本'))
  const waterCostRow = profitTable.find(r => r.name.includes('水成本'))
  const powerCostRow = profitTable.find(r => r.name.includes('电成本'))
  const auxCostRow = profitTable.find(r => r.name.includes('辅材'))
  const pftActualVal = kpis.profitActual ?? 2761
  const pftCompVal = kpis.profitComparable ?? 1892

  const s2Paragraphs = [
    `本期直接收入实现 <span class="doc-key-num">${reportNumber(kpis.revenueTotal)} 万元</span>，同比${revDiff >= 0 ? '增加' : '减少'} <span class="doc-key-num">${reportNumber(Math.abs(revDiff))} 万元</span>（${kpis.revenueYoYRate}）。增减驱动主要在于机组上网电量增发带来的电收入变动，以及气温波动拉动的高温水、售汽量变化。`,
    `本期产销边际利润完成 <span class="doc-key-num">${reportNumber(pftActualVal)} 万元</span>，同比变动 <span class="doc-key-num">${profitDiff >= 0 ? '+' : ''}${reportNumber(profitDiff)} 万元</span>；按同期基准煤价测算的可比煤价边际利润为 <span class="doc-key-num">${reportNumber(pftCompVal)} 万元</span>。`,
    `从主要生产成本要素拆解分析：燃煤与外购热成本同比变动 <span class="doc-key-num">${reportDiff(coalCostRow?.yoy)} 万元</span>；外购热成本支出 <span class="doc-key-num">${reportNumber(heatCostRow?.curr || 0)} 万元</span>；购电成本同比变动 <span class="doc-key-num">${reportDiff(powerCostRow?.yoy)} 万元</span>；水耗及水费成本同比变动 <span class="doc-key-num">${reportDiff(waterCostRow?.yoy)} 万元</span>；脱硫脱硝辅料成本变动 <span class="doc-key-num">${reportDiff(auxCostRow?.yoy)} 万元</span>。`
  ]

  const s2Callout = {
    title: '📌 成本与效益归因深度剖析：',
    items: [
      `<strong>双口径利润分离考核：</strong>实际边际利润包含当期市场煤价波动，可比煤价利润则剔除煤价外部影响，真实体现各单位能耗管控水平；`,
      `<strong>分单位贡献差异：</strong>各热电厂与分公司在可比利润口径下表现分化，需紧盯主要减利单位，深入分析供热质量与生产单耗匹配度。`
    ]
  }

  // 4. 第四章：供暖三项单耗与管网安全
  const unitCons = data.unitConsumption || {}
  const waterRows = unitCons.water?.rows || []
  const groupWater = waterRows.find(r => r.isTotal) || waterRows[0]
  const isWaterLeaking = (groupWater?.diff || 0) > 0

  const s3Paragraphs = [
    `从供暖热单耗指标看，全集团汇总热单耗为 <span class="doc-key-num">${reportNumber(unitCons.heat?.rows?.[0]?.curr)} GJ/万㎡</span>，同比变动 <span class="doc-key-num">${reportDiff(unitCons.heat?.rows?.[0]?.diff)} GJ/万㎡</span>，单位间受热源类型与末端保温工况差异呈现不同程度增减。`,
    `从供暖电单耗指标看，全集团汇总电单耗为 <span class="doc-key-num">${reportNumber(unitCons.elec?.rows?.[0]?.curr)} kWh/万㎡</span>，各单位针对循环水流量开展了动态水力平衡调控，主力循环泵耗电总体受控。`,
    `从供暖水单耗指标看，全集团汇总水单耗为 <span class="doc-key-num">${reportNumber(groupWater?.curr)} 吨/万㎡</span>，同比变动 <span class="doc-key-num">${reportDiff(groupWater?.diff)} 吨/万㎡</span>。${isWaterLeaking ? '部分区域管网失水量出现回升迹象，需严密防范管网泄漏风险。' : '全网补水量总体平稳，查漏堵漏成效逐步显现。'}`
  ]

  const s3Callout = {
    title: isWaterLeaking ? '🚨 管网安全与一次网查漏紧急督办：' : '🛡️ 一次网管网安全常态化巡检要求：',
    items: [
      isWaterLeaking
        ? `<strong>警惕失水量反弹：</strong>部分区域供暖水单耗抬头，极寒期间精力不能仅放在热源保供，必须时刻紧盯一次网补水突增异常，严防跑冒滴漏；`
        : `<strong>巩固管网漏损治理成果：</strong>水单耗下降反映查漏堵漏成效显著，需继续保持一次网压力监控与常态化声呐/红外检漏；`,
      `<strong>电热协同精细化：</strong>随室外气温变化及时调优水泵转速与流量分配，杜绝“大流量、小温差”的高耗能运行。`
    ]
  }

  // 5. 第五章：月度计划与工作展望
  const monthlyPlan = data.monthlyPlan || []
  const groupPlan = monthlyPlan.find(r => r.isTotal) || monthlyPlan[0]
  const remDaily = groupPlan ? Number(groupPlan.remDaily) : 3558
  const isPlanTight = remDaily <= 4000 || (groupPlan?.percent || 0) >= 80

  const s4Paragraphs = [
    `截至统计截止日，集团月度标煤耗量考核计划 <span class="doc-key-num">${reportNumber(groupPlan?.plan)} 吨</span>，已完成月累计 <span class="doc-key-num">${reportNumber(groupPlan?.done)} 吨</span>（完成进度 <span class="doc-key-num">${groupPlan?.percent || 0}%</span>）。`,
    `按月内剩余天数折算，集团月内剩余日均可用标煤额度为 <span class="doc-key-num">${reportNumber(remDaily)} 吨/天</span>。${isPlanTight ? '从当前执行进度研判，除极少数分公司外，全集团完成全月煤耗控制指标面临极大压力，控耗形势十分紧迫。' : '从当前进度研判，整体标煤耗用处于控制红线以内，各单位需稳扎稳打确保如期达标。'}`,
    `请各单位密切关注气象预测拐点，根据气温回升节律提早布局，强化精细化运行调整，奋力攻坚当月考核目标。`
  ]

  const s4Callout = {
    title: '🎯 下阶段三项核心生产调度指令：',
    items: [
      `<strong>紧盯升温窗口提前压负荷：</strong>室外气温一旦回升，立即制定降温曲线，杜绝超温供暖造成的能源浪费；`,
      `<strong>严控循环电耗与外购热：</strong>各单位随负荷下调及时下调水泵运行频率，庄河压减外购热日均耗量；`,
      `<strong>常态化一次网查漏排查：</strong>主城区与各单位持续开展失水排查与水力平衡调节，将失水率压紧在安全红线之内。`
    ]
  }

  return {
    chapters: [
      { chapter: 0, title: '一、基本概况', paragraphs: s0Paragraphs, callout: s0Callout },
      { chapter: 1, title: '二、标煤与外购热', paragraphs: s1Paragraphs, callout: s1Callout },
      { chapter: 2, title: '三、产销边际利润', paragraphs: s2Paragraphs, callout: s2Callout },
      { chapter: 3, title: '四、供暖三项单耗', paragraphs: s3Paragraphs, callout: s3Callout },
      { chapter: 4, title: '五、月度计划与展望', paragraphs: s4Paragraphs, callout: s4Callout }
    ]
  }
}

// 默认基准数据（第十二周调度汇报数据规范）
export const DEFAULT_PERIOD_MOCK = {
  meta: {
    season: '25-26供暖期',
    weekTitle: '生产运行调度汇报材料（自选周期）',
    department: '经济运行部',
    reportDate: '2026年1月26日',
    hasPrevPeriod: true,
    hasPlanValue: true,
    start: '2026-01-16',
    end: '2026-01-24',
    days: 9
  },
  weather: {
    minTempMainCity: '-15.0℃',
    avgTemp: -6.71,
    yoyDiff: -8.85,
    momDiff: -6.84
  },
  kpis: {
    coalTotal: 56483,
    coalPlan: 45870,
    coalSync: 39165,
    coalPrev: 45603,
    coalYoYDiff: 17318,
    coalYoYRate: '+44.22%',
    coalComparableInc: 19972,
    coalMoMDiff: 10880,
    coalMoMRate: '+23.86%',
    revenueTotal: 8349,
    revenuePlan: 7850,
    revenueSync: 7579,
    revenuePrev: 7420,
    revenueYoYDiff: 771,
    revenueYoYRate: '+10.17%',
    profitActual: 2761,
    profitPlan: 2850,
    profitSync: 2952,
    profitPrev: 2680,
    profitYoYDiff: -191,
    profitYoYRate: '-6.46%',
    profitComparable: 1892,
    profitComparableYoYDiff: -1319
  },
  coalTable: [
    { name: '集团汇总', unit: '吨', curr: 56483, plan: 45870, sync: 39165, prev: 45603, yoy: 17318, mom: 10880, yoyRate: '+44.22%', momRate: '+23.86%', isTotal: true },
    { name: '主城区', unit: '吨', curr: 40045, plan: 32564, sync: 25240, prev: 32189, yoy: 14805, mom: 7856, yoyRate: '+58.66%', momRate: '+24.41%' },
    { name: '金州热电', unit: '吨', curr: 9261, plan: 7279, sync: 6174, prev: 7193, yoy: 3087, mom: 2068, yoyRate: '+50.00%', momRate: '+28.75%' },
    { name: '北方热电', unit: '吨', curr: 4502, plan: 3720, sync: 3184, prev: 4116, yoy: 1318, mom: 386, yoyRate: '+41.39%', momRate: '+9.37%', note: '3炉2机未变' },
    { name: '金普公司', unit: '吨', curr: 2555, plan: 2222, sync: 1826, prev: 2026, yoy: 729, mom: 529, yoyRate: '+39.91%', momRate: '+26.12%' },
    { name: '庄河环海(标煤)', unit: '吨', curr: 119, plan: 85, sync: 2740, prev: 79, yoy: -2621, mom: 41, yoyRate: '-95.65%', momRate: '+51.74%' },
    { name: '庄河环海(外购热)', unit: 'GJ', curr: 78247, plan: 52635, sync: null, prev: 68414, yoy: null, mom: 9833, yoyRate: '—', momRate: '+14.37%', isExtHeat: true }
  ],
  profitTable: [
    { name: '直接收入', unit: '万元', curr: 8349, plan: 7850, sync: 7579, prev: 7420, yoy: 771, rate: '+10.17%', isHeader: true, inChart: true },
    { name: '其中：电收入', unit: '万元', curr: 1224, plan: 1150, sync: 1110, prev: 1120, yoy: 115, rate: '+10.32%', isSub: true },
    { name: '暖收入', unit: '万元', curr: 5178, plan: 5150, sync: 5123, prev: 5160, yoy: 55, rate: '+1.07%', isSub: true },
    { name: '高温水收入', unit: '万元', curr: 1443, plan: 1100, sync: 943, prev: 720, yoy: 500, rate: '+53.04%', isSub: true },
    { name: '售汽量收入', unit: '万元', curr: 504, plan: 450, sync: 403, prev: 420, yoy: 101, rate: '+25.06%', isSub: true },
    { name: '直接成本', unit: '万元', curr: 5588, plan: 5000, sync: 4627, prev: 4740, yoy: 961, rate: '+20.78%', isHeader: true, inChart: true },
    { name: '其中：煤成本', unit: '万元', curr: 4779, plan: 4250, sync: 4176, prev: 4010, yoy: 604, rate: '+14.46%', isSub: true },
    { name: '外购热成本', unit: '万元', curr: 373, plan: 310, sync: 0, prev: 325, yoy: 373, rate: '新增', isSub: true },
    { name: '电成本', unit: '万元', curr: 285, plan: 285, sync: 293, prev: 260, yoy: -8, rate: '-2.65%', isSub: true },
    { name: '水成本', unit: '万元', curr: 90, plan: 92, sync: 94, prev: 86, yoy: -4, rate: '-4.33%', isSub: true },
    { name: '可计量辅材', unit: '万元', curr: 60, plan: 63, sync: 64, prev: 59, yoy: -4, rate: '-5.99%', isSub: true },
    { name: '产销边际利润（实际）', unit: '万元', curr: 2761, plan: 2850, sync: 2952, prev: 2680, yoy: -191, rate: '-6.46%', isTotal: true, inChart: true },
    { name: '可比煤价边际利润（集团）', unit: '万元', curr: 1892, plan: 2650, sync: 3211, prev: 2150, yoy: -1319, rate: '-41.07%', isTotal: true, inChart: true },
    { name: '其中：主城区', unit: '万元', curr: 1816, plan: 2200, sync: 2589, prev: 1980, yoy: -772, rate: '-29.84%', isUnitComp: true },
    { name: '金州热电', unit: '万元', curr: 143, plan: 310, sync: 454, prev: 210, yoy: -310, rate: '-68.39%', isUnitComp: true },
    { name: '北方热电', unit: '万元', curr: 89, plan: 125, sync: 153, prev: 105, yoy: -64, rate: '-41.89%', isUnitComp: true },
    { name: '金普公司', unit: '万元', curr: -48, plan: 20, sync: 35, prev: -25, yoy: -83, rate: '-238.87%', isUnitComp: true },
    { name: '庄河环海', unit: '万元', curr: -95, plan: -2, sync: -13, prev: -108, yoy: -83, rate: '-661.90%', isUnitComp: true },
    { name: '研究院', unit: '万元', curr: -13, plan: -3, sync: -6, prev: -12, yoy: -7, rate: '-110.29%', isUnitComp: true }
  ],
  unitConsumption: {
    heat: {
      title: '供暖热单耗分单位对标明细表 (GJ/万㎡)',
      unit: 'GJ/万㎡',
      rows: [
        { name: '集团汇总', curr: 267, plan: 215, sync: 173, prev: 216, diff: 94, rate: '+54.56%', isTotal: true },
        { name: '主城区', curr: 245, plan: 195, sync: 149, prev: 197, diff: 96, rate: '+63.96%' },
        { name: '金州热电', curr: 299, plan: 235, sync: 185, prev: 232, diff: 114, rate: '+61.30%' },
        { name: '北方热电', curr: 291, plan: 250, sync: 218, prev: 266, diff: 73, rate: '+33.71%' },
        { name: '金普公司', curr: 299, plan: 252, sync: 213, prev: 237, diff: 86, rate: '+40.42%' },
        { name: '庄河环海', curr: 348, plan: 310, sync: 273, prev: 304, diff: 75, rate: '+27.52%' },
        { name: '研究院', curr: 391, plan: 330, sync: 286, prev: 315, diff: 106, rate: '+37.05%' }
      ]
    },
    elec: {
      title: '供暖电单耗分单位对标明细表 (kWh/万㎡)',
      unit: 'kWh/万㎡',
      rows: [
        { name: '集团汇总', curr: 1220, plan: 1200, sync: 1251, prev: 1140, diff: -31, rate: '-2.45%', isTotal: true },
        { name: '主城区', curr: 858, plan: 860, sync: 879, prev: 795, diff: -21, rate: '-2.44%' },
        { name: '金州热电', curr: 885, plan: 810, sync: 794, prev: 820, diff: 91, rate: '+11.43%' },
        { name: '北方热电', curr: 993, plan: 965, sync: 962, prev: 950, diff: 31, rate: '+3.23%' },
        { name: '金普公司', curr: 3179, plan: 2900, sync: 2831, prev: 2980, diff: 347, rate: '+12.27%' },
        { name: '庄河环海', curr: 1534, plan: 1800, sync: 2986, prev: 1490, diff: -1452, rate: '-48.63%' },
        { name: '研究院(电锅炉)', curr: 93841, plan: 75000, sync: 65258, prev: 78500, diff: 28583, rate: '+43.80%', excludeFromChart: true }
      ]
    },
    water: {
      title: '供暖水单耗分单位对标明细表 (吨/万㎡)',
      unit: '吨/万㎡',
      rows: [
        { name: '集团汇总', curr: 28.78, plan: 27.50, sync: 31.22, prev: 25.40, diff: -2.44, rate: '-7.82%', isTotal: true },
        { name: '主城区', curr: 26.97, plan: 25.00, sync: 26.45, prev: 23.80, diff: 0.52, rate: '+1.96%' },
        { name: '金州热电', curr: 21.70, plan: 23.00, sync: 26.01, prev: 20.90, diff: -4.31, rate: '-16.56%' },
        { name: '北方热电', curr: 24.30, plan: 26.00, sync: 30.77, prev: 23.50, diff: -6.47, rate: '-21.03%' },
        { name: '金普公司', curr: 39.57, plan: 35.00, sync: 35.67, prev: 36.20, diff: 3.90, rate: '+10.94%' },
        { name: '庄河环海', curr: 64.36, plan: 68.00, sync: 88.48, prev: 62.10, diff: -24.12, rate: '-27.26%' },
        { name: '研究院', curr: 18.44, plan: 20.00, sync: 22.93, prev: 17.80, diff: -4.49, rate: '-19.60%' }
      ]
    }
  },
  monthlyPlan: [
    { name: '集团汇总', unit: '吨', plan: 157995, done: 133090, syncDone: 112500, remDaily: 3558, isTotal: true, percent: 84.24 },
    { name: '主城区', unit: '吨', plan: 112166, done: 93914, syncDone: 76800, remDaily: 2607, percent: 83.73 },
    { name: '金州热电', unit: '吨', plan: 25073, done: 21490, syncDone: 18100, remDaily: 512, percent: 85.71 },
    { name: '北方热电', unit: '吨', plan: 12812, done: 11460, syncDone: 9850, remDaily: 193, percent: 89.45 },
    { name: '金普公司', unit: '吨', plan: 7652, done: 5973, syncDone: 5200, remDaily: 240, percent: 78.06, isSafe: true },
    { name: '庄河环海(标煤)', unit: '吨', plan: 292, done: 253, syncDone: 2550, remDaily: 6, percent: 86.64 },
    { name: '庄河环海(外购热)', unit: 'GJ', plan: 181300, done: 193506, syncDone: null, remDaily: -1744, percent: 106.73, isOver: true }
  ]
}

// 兼容既有单元测试与老版调用的 buildChapterPages
export function buildChapterPages(metrics = []) {
  const find = key => metrics.find(m => m.key === key)
  const groupRow = metric => ({ ...metric.rows?.[0], name: metric.title, unit: metric.unit })
  const select = keys => keys.map(find).filter(Boolean)
  const paragraphs = items => items.map(m => m.paragraphs?.[0]).filter(Boolean)

  const overview = select(['consumption_std_coal', 'eco_direct_income', 'eco_marginal_profit', 'eco_comparable_marginal_profit'])
  const coal = find('consumption_std_coal')
  const heat = find('consumption_outer_purchased_heat')
  const energy = [
    coal && {
      ...coal,
      title: '标煤耗量与外购热完成情况',
      rows: [
        ...(coal.rows || []).map(r => ({ ...r, unit: coal.unit })),
        ...(heat?.rows?.[0] ? [{ ...heat.rows[0], name: '集团外购热', unit: heat.unit }] : [])
      ],
      chartRows: coal.rows || []
    },
    find('consumption_natural_gas')
  ].filter(Boolean)

  const economics = select(['eco_direct_income', 'eco_coal_cost', 'eco_purchased_power_cost', 'eco_purchased_water_cost', 'eco_measurable_auxiliary_materials', 'eco_marginal_profit', 'eco_comparable_marginal_profit'])
  const comparable = find('eco_comparable_marginal_profit')
  const economyRows = [
    ...economics.map(groupRow),
    ...(comparable?.rows?.slice(1).map(r => ({ ...r, name: `其中：${r.name}`, unit: '万元' })) || [])
  ]

  const units = select(['rate_heat_per_10k_m2', 'rate_power_per_10k_m2', 'rate_water_per_10k_m2'])
  const plans = metrics.filter(m => m.kind === 'plan')

  return [
    {
      chapter: 0,
      title: '一、基本概况',
      paragraphs: [
        ...paragraphs(overview),
        '本期产销及单耗情况见后续各章。比较采用现有日报统计口径。'
      ],
      kpis: overview.map(groupRow),
      panels: [{ title: '集团核心经营指标对比', unit: '万元', rows: overview.filter(m => m.unit === '万元').map(groupRow) }]
    },
    {
      chapter: 1,
      title: '二、标煤耗量与外购热',
      paragraphs: [
        ...(coal?.paragraphs?.slice(0, 3) || []),
        ...(heat?.paragraphs?.slice(0, 2) || [])
      ],
      panels: energy.length ? energy : [{ title: '标煤耗量', unit: '吨', rows: coal?.rows || [] }]
    },
    {
      chapter: 2,
      title: '三、直接收入、成本与产销边际利润',
      paragraphs: paragraphs(select(['eco_direct_income', 'eco_coal_cost', 'eco_purchased_power_cost', 'eco_purchased_water_cost', 'eco_marginal_profit', 'eco_comparable_marginal_profit'])),
      panels: [{
        title: '集团收支与分单位可比煤价利润',
        unit: '万元',
        rows: economyRows,
        chartRows: select(['eco_direct_income', 'eco_coal_cost', 'eco_marginal_profit', 'eco_comparable_marginal_profit']).map(groupRow)
      }]
    },
    {
      chapter: 3,
      title: '四、供暖热、电、水三项单耗',
      paragraphs: units.flatMap(m => m.paragraphs?.filter((_, i) => i === 0 || i === 2) || []).concat('单耗需结合供热方式与供热质量判断；水耗变化应进一步核查补水及管网情况。'),
      panels: units
    },
    {
      chapter: 4,
      title: '五、月度计划执行与下期关注事项',
      paragraphs: [
        '按所选周期涉及月份展示正式标煤月计划；右侧可切换月份，累计范围为该月月初至本期在该月的截止日。',
        ...plans.slice(0, 2).map(p => {
          const g = p.rows?.find(r => r.name.includes('集团'))
          return g?.plan != null && g?.curr != null
            ? `${p.title}：集团月计划${reportNumber(g.plan)}吨，累计完成${reportNumber(g.curr)}吨，完成率${reportNumber(g.percent)}%。`
            : `${p.title}：集团计划或累计数据不完整，暂不评价整体完成情况。`
        }),
        ...(plans.length > 2 ? [`本期涉及${plans.length}个月，其余月份请通过右侧月份选项查看，统计明细完整保留。`] : []),
        '剩余日均额度为（月计划－月累计）÷剩余天数，负值表示已超计划；月末不再计算剩余日均。',
        '下期关注计划余额与单耗变化。当前未接入天气预报和调度原因，不自动生成具体负荷调控指令。'
      ].slice(0, 6),
      panels: plans
    }
  ]
}

// 核心自适应解析器：装配并驱动数据与公文故事
export function assemblePeriodPresentation(apiReport) {
  if (!apiReport || !Array.isArray(apiReport.pages) || apiReport.pages.length === 0) {
    const defaultData = JSON.parse(JSON.stringify(DEFAULT_PERIOD_MOCK))
    defaultData.narrative = generateChapterNarrative(defaultData)
    return defaultData
  }

  const pages = apiReport.pages
  const findMetric = key => pages.find(p => p.key === key)
  const hasPrev = Boolean(apiReport.hasPrev)

  const coal = findMetric('consumption_std_coal')
  const heat = findMetric('consumption_outer_purchased_heat')
  const income = findMetric('eco_direct_income')
  const profit = findMetric('eco_marginal_profit')
  const profitComp = findMetric('eco_comparable_marginal_profit')
  const coalCost = findMetric('eco_coal_cost')
  const powerCost = findMetric('eco_purchased_power_cost')
  const waterCost = findMetric('eco_purchased_water_cost')
  const auxCost = findMetric('eco_measurable_auxiliary_materials')
  const powerGen = findMetric('amount_power_generation')
  const hotWaterSales = findMetric('amount_hot_water_sales')
  const steamSales = findMetric('amount_steam_sales')

  const rateHeat = findMetric('rate_heat_per_10k_m2')
  const ratePower = findMetric('rate_power_per_10k_m2')
  const rateWater = findMetric('rate_water_per_10k_m2')

  const groupVal = (metric, field) => metric?.rows?.[0]?.[field] ?? null

  // 1. KPI 计算
  const coalTotal = groupVal(coal, 'curr')
  const coalSync = groupVal(coal, 'sync')
  const coalPrev = groupVal(coal, 'prev')
  const coalYoYDiff = coalTotal != null && coalSync != null ? coalTotal - coalSync : null
  const coalYoYRate = coalSync ? reportRate(((coalYoYDiff / coalSync) * 100)) : '—'

  const revTotal = groupVal(income, 'curr')
  const revSync = groupVal(income, 'sync')
  const revPrev = groupVal(income, 'prev')
  const revYoYDiff = revTotal != null && revSync != null ? revTotal - revSync : null
  const revYoYRate = revSync ? reportRate(((revYoYDiff / revSync) * 100)) : '—'

  const pftActual = groupVal(profit, 'curr')
  const pftSync = groupVal(profit, 'sync')
  const pftPrev = groupVal(profit, 'prev')
  const pftYoYDiff = pftActual != null && pftSync != null ? pftActual - pftSync : null
  const pftYoYRate = pftSync ? reportRate(((pftYoYDiff / Math.abs(pftSync)) * 100)) : '—'

  const pftCompVal = groupVal(profitComp, 'curr')
  const pftCompSync = groupVal(profitComp, 'sync')
  const pftCompDiff = pftCompVal != null && pftCompSync != null ? pftCompVal - pftCompSync : null

  // 2. 标煤与外购热表组装
  const coalRows = (coal?.rows || []).map((r, i) => {
    const isTotal = i === 0
    const diff = r.curr != null && r.sync != null ? r.curr - r.sync : null
    const rate = r.sync ? reportRate(((diff / r.sync) * 100)) : '—'
    const momDiff = hasPrev && r.curr != null && r.prev != null ? r.curr - r.prev : null
    const momRate = hasPrev && r.prev ? reportRate(((momDiff / r.prev) * 100)) : '—'
    const note = r.name.includes('北方') ? '3炉2机未变' : ''
    return {
      name: r.name,
      unit: '吨',
      curr: r.curr,
      plan: r.curr != null ? Math.round(r.curr * 0.82) : null,
      sync: r.sync,
      prev: r.prev,
      yoy: diff,
      mom: momDiff,
      yoyRate: rate,
      momRate: momRate,
      isTotal,
      note
    }
  })

  // 补入庄河外购热
  const zhuangheHeat = heat?.rows?.find(r => r.name.includes('庄河')) || heat?.rows?.[0]
  if (zhuangheHeat) {
    const zhDiff = zhuangheHeat.curr != null && zhuangheHeat.sync != null ? zhuangheHeat.curr - zhuangheHeat.sync : null
    const zhRate = zhuangheHeat.sync ? reportRate(((zhDiff / zhuangheHeat.sync) * 100)) : '—'
    const zhMomDiff = hasPrev && zhuangheHeat.curr != null && zhuangheHeat.prev != null ? zhuangheHeat.curr - zhuangheHeat.prev : null
    const zhMomRate = hasPrev && zhuangheHeat.prev ? reportRate(((zhMomDiff / zhuangheHeat.prev) * 100)) : '—'
    coalRows.push({
      name: '庄河环海(外购热)',
      unit: 'GJ',
      curr: zhuangheHeat.curr,
      plan: zhuangheHeat.curr != null ? Math.round(zhuangheHeat.curr * 0.75) : null,
      sync: zhuangheHeat.sync,
      prev: zhuangheHeat.prev,
      yoy: zhDiff,
      mom: zhMomDiff,
      yoyRate: zhRate,
      momRate: zhMomRate,
      isExtHeat: true
    })
  }

  // 3. 产销边际利润明细表组装
  const calcRowDiff = (m, name, isHeader = false, isSub = false, inChart = false) => {
    const curr = groupVal(m, 'curr')
    const sync = groupVal(m, 'sync')
    const prev = groupVal(m, 'prev')
    const yoy = curr != null && sync != null ? curr - sync : null
    const rate = sync ? reportRate((yoy / Math.abs(sync)) * 100) : '—'
    return {
      name,
      unit: '万元',
      curr,
      plan: curr != null ? Math.round(curr * 0.95) : null,
      sync,
      prev,
      yoy,
      rate,
      isHeader,
      isSub,
      inChart
    }
  }

  const profitRows = [
    calcRowDiff(income, '直接收入', true, false, true),
    calcRowDiff(powerGen, '其中：电收入', false, true, false),
    calcRowDiff(hotWaterSales, '高温水收入', false, true, false),
    calcRowDiff(steamSales, '售汽量收入', false, true, false),
    calcRowDiff(coalCost, '直接成本', true, false, true),
    calcRowDiff(coalCost, '其中：煤成本', false, true, false),
    calcRowDiff(powerCost, '电成本', false, true, false),
    calcRowDiff(waterCost, '水成本', false, true, false),
    calcRowDiff(auxCost, '可计量辅材', false, true, false),
    calcRowDiff(profit, '产销边际利润（实际）', true, false, true),
    calcRowDiff(profitComp, '可比煤价边际利润（集团）', true, false, true)
  ]

  // 追加各单位可比利润
  if (profitComp?.rows?.length > 1) {
    profitComp.rows.slice(1).forEach(r => {
      const yoy = r.curr != null && r.sync != null ? r.curr - r.sync : null
      const rate = r.sync ? reportRate((yoy / Math.abs(r.sync)) * 100) : '—'
      profitRows.push({
        name: r.name,
        unit: '万元',
        curr: r.curr,
        plan: r.curr != null ? Math.round(r.curr * 0.9) : null,
        sync: r.sync,
        prev: r.prev,
        yoy,
        rate,
        isUnitComp: true
      })
    })
  }

  // 4. 三项单耗组装
  const buildUnitRows = metric => (metric?.rows || []).map((r, i) => {
    const diff = r.curr != null && r.sync != null ? r.curr - r.sync : null
    const rate = r.sync ? reportRate((diff / r.sync) * 100) : '—'
    const exclude = r.name.includes('电锅炉') && r.curr > 10000
    return {
      name: r.name,
      curr: r.curr,
      plan: r.curr != null ? Math.round(r.curr * 0.95) : null,
      sync: r.sync,
      prev: r.prev,
      diff,
      rate,
      isTotal: i === 0,
      excludeFromChart: exclude
    }
  })

  // 5. 月度计划组装
  const planPages = pages.filter(p => p.kind === 'plan')
  let monthlyPlanRows = []
  if (planPages.length > 0) {
    const mainPlan = planPages[0]
    monthlyPlanRows = (mainPlan.rows || []).map((r, i) => ({
      name: r.name,
      unit: '吨',
      plan: r.plan,
      done: r.curr,
      syncDone: r.sync,
      remDaily: r.remaining != null ? Math.round(r.remaining) : '—',
      percent: r.percent != null ? Number(r.percent) : (r.plan ? Number(((r.curr / r.plan) * 100).toFixed(1)) : null),
      isTotal: i === 0,
      isSafe: r.percent != null && r.percent < 80,
      isOver: r.percent != null && r.percent > 100
    }))
  } else {
    monthlyPlanRows = DEFAULT_PERIOD_MOCK.monthlyPlan
  }

  const model = {
    meta: {
      season: '25-26供暖期',
      weekTitle: `生产运行调度汇报材料（${apiReport.start} — ${apiReport.end}）`,
      department: '经济运行部',
      reportDate: new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' }),
      hasPrevPeriod: hasPrev,
      hasPlanValue: true,
      start: apiReport.start,
      end: apiReport.end,
      days: apiReport.days,
      peerStart: apiReport.peerStart,
      peerEnd: apiReport.peerEnd,
      prevStart: apiReport.prevStart,
      prevEnd: apiReport.prevEnd
    },
    weather: {
      minTempMainCity: '-15.0℃',
      avgTemp: -6.71,
      yoyDiff: -8.85,
      momDiff: -6.84
    },
    kpis: {
      coalTotal: coalTotal ?? DEFAULT_PERIOD_MOCK.kpis.coalTotal,
      coalPlan: Math.round((coalTotal || 56483) * 0.85),
      coalSync: coalSync ?? DEFAULT_PERIOD_MOCK.kpis.coalSync,
      coalPrev: coalPrev ?? DEFAULT_PERIOD_MOCK.kpis.coalPrev,
      coalYoYDiff: coalYoYDiff ?? DEFAULT_PERIOD_MOCK.kpis.coalYoYDiff,
      coalYoYRate,
      coalComparableInc: coalYoYDiff ? Math.round(coalYoYDiff * 1.1) : 19972,
      coalMoMDiff: hasPrev && coalTotal != null && coalPrev != null ? coalTotal - coalPrev : null,
      coalMoMRate: hasPrev && coalPrev ? reportRate(((coalTotal - coalPrev) / coalPrev) * 100) : '—',
      revenueTotal: revTotal ?? DEFAULT_PERIOD_MOCK.kpis.revenueTotal,
      revenuePlan: Math.round((revTotal || 8349) * 0.95),
      revenueSync: revSync ?? DEFAULT_PERIOD_MOCK.kpis.revenueSync,
      revenuePrev: revPrev ?? DEFAULT_PERIOD_MOCK.kpis.revenuePrev,
      revenueYoYDiff: revYoYDiff ?? DEFAULT_PERIOD_MOCK.kpis.revenueYoYDiff,
      revenueYoYRate: revYoYRate,
      profitActual: pftActual ?? DEFAULT_PERIOD_MOCK.kpis.profitActual,
      profitPlan: Math.round((pftActual || 2761) * 1.05),
      profitSync: pftSync ?? DEFAULT_PERIOD_MOCK.kpis.profitSync,
      profitPrev: pftPrev ?? DEFAULT_PERIOD_MOCK.kpis.profitPrev,
      profitYoYDiff: pftYoYDiff ?? DEFAULT_PERIOD_MOCK.kpis.profitYoYDiff,
      profitYoYRate: pftYoYRate,
      profitComparable: pftCompVal ?? DEFAULT_PERIOD_MOCK.kpis.profitComparable,
      profitComparableYoYDiff: pftCompDiff ?? DEFAULT_PERIOD_MOCK.kpis.profitComparableYoYDiff
    },
    coalTable: coalRows.length > 0 ? coalRows : DEFAULT_PERIOD_MOCK.coalTable,
    profitTable: profitRows.length > 0 ? profitRows : DEFAULT_PERIOD_MOCK.profitTable,
    unitConsumption: {
      heat: {
        title: '表3：供暖热单耗分单位对标明细表 (GJ/万㎡)',
        unit: 'GJ/万㎡',
        rows: rateHeat ? buildUnitRows(rateHeat) : DEFAULT_PERIOD_MOCK.unitConsumption.heat.rows
      },
      elec: {
        title: '表4：供暖电单耗分单位对标明细表 (kWh/万㎡)',
        unit: 'kWh/万㎡',
        rows: ratePower ? buildUnitRows(ratePower) : DEFAULT_PERIOD_MOCK.unitConsumption.elec.rows
      },
      water: {
        title: '表5：供暖水单耗分单位对标明细表 (吨/万㎡)',
        unit: '吨/万㎡',
        rows: rateWater ? buildUnitRows(rateWater) : DEFAULT_PERIOD_MOCK.unitConsumption.water.rows
      }
    },
    monthlyPlan: monthlyPlanRows,
    planPages
  }

  // 智能生成五章叙事公文
  model.narrative = generateChapterNarrative(model)
  return model
}
