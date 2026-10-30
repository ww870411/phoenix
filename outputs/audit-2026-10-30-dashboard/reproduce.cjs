// 只读审查复现：执行当前看板中的原函数，用可控响应模拟网络时序，不访问或修改数据库。
const fs = require('node:fs')
const assert = require('node:assert/strict')
const path = require('node:path')
const { createRequire } = require('node:module')
const root = path.resolve(__dirname, '../..')
const vue = createRequire(path.join(root, 'frontend/package.json'))('vue')
const frontendRequire = createRequire(path.join(root, 'frontend/package.json'))
const source = fs.readFileSync(path.join(root, 'frontend/src/projects/daily_report_25_26/pages/DashBoard.vue'), 'utf8').replace(/\r\n/g, '\n')
const cut = (start, end) => {
  const first = source.indexOf(start)
  const last = source.indexOf(end, first)
  if (first < 0 || last < 0) throw new Error(`源码边界未匹配：${start}`)
  return source.slice(first, last)
}
const deferred = () => {
  let resolve
  const promise = new Promise(r => { resolve = r })
  return { promise, resolve }
}

async function main() {
  // 整个 setup 与模板首次渲染验收，补足单函数测试无法发现的初始化顺序错误。
  const compiler = frontendRequire('@vue/compiler-sfc')
  const descriptor = compiler.parse(source).descriptor
  const compiled = compiler.compileScript(descriptor, { id: 'dashboard-regression', inlineTemplate: true })
  const js = frontendRequire('esbuild').transformSync(compiled.content, { format: 'cjs', loader: 'js' }).code
  const module = { exports: {} }
  const api = new Proxy({}, { get: () => async () => ({ ok: true }) })
  const requireMock = name => {
    if (name === 'vue') return vue
    if (name === 'pinia') return { storeToRefs: () => ({ canPublish: vue.ref(false) }) }
    if (name === 'vue-router') return { useRouter: () => ({ push() {} }) }
    if (name.endsWith('/store/auth')) return { useAuthStore: () => ({}) }
    if (name.endsWith('.vue')) return { default: { render: () => null } }
    return api
  }
  require('node:vm').runInNewContext(js, { require: requireMock, module, exports: module.exports, console, Date, Map, Set, AbortController, setTimeout, clearTimeout })
  const html = await frontendRequire('@vue/server-renderer').renderToString(vue.createSSRApp(module.exports.default))
  assert.match(html, /业务日期/)
  assert.match(html, /dashboard-skeleton/)
  assert.match(html, /正在加载/)
  assert.doesNotMatch(html, /请选择业务日期/)
  console.log('通过：完整 Vue setup 与初始模板显示加载骨架，无选日提示闪烁或初始化顺序错误')
  const createMain = new Function('V', 'network', `
    const {ref,watch,nextTick}=V;
    let suppressDashboardWatchDepth=0,dashboardAbortController=null,dashboardRequestId=0,dashboardDisposed=false,dashboardLoadTimer=null;
    const bizDateInput=ref('2026-11-01'),isLoading=ref(false),dashboardError=ref(''),dashboardCache=new Map(),projectKey='daily_report_25_26',defaultBizDate='2026-11-01';
    const dashboardData={sections:{},meta:{}};
    const getDashboardCacheKey=v=>v||'__latest__';
    const getDashboardData=network;
    const assignDashboardPayload=p=>dashboardData.sections={date:p.date};
    const scheduled=[];
    const scheduleDashboardLoad=v=>scheduled.push(v);
    ${cut('const acquireWatchSuppress =', 'const fmt =')}
    ${cut('const invalidateDashboardRequest =', 'const DASHBOARD_DEFAULT_CACHE_KEY =')}
    ${cut('async function loadDashboardData(', 'function handleCacheManagerStarted(')}
    ${cut('watch(\n  () => bizDateInput.value,', 'onBeforeUnmount(() => {\n  dashboardDisposed')}
    return {loadDashboardData,bizDateInput,nextTick,scheduled,dashboardCache,dashboardError,isLoading,shown:()=>dashboardData.sections.date};
  `)
  const pending = deferred()
  const calls = []
  const mainState = createMain(vue, (_, params) => { calls.push(params.showDate); return params.showDate === '2026-11-01' ? pending.promise : Promise.resolve({date:'2026-11-02'}) })
  const request = mainState.loadDashboardData('2026-11-01')
  mainState.bizDateInput.value = '2026-11-02'
  await mainState.nextTick()
  pending.resolve({ date: '2026-11-01' })
  await request
  assert.deepEqual(mainState.scheduled, ['2026-11-02'])
  assert.equal(mainState.shown(), undefined)
  await mainState.loadDashboardData('2026-11-02')
  assert.equal(mainState.shown(), '2026-11-02')
  console.log(JSON.stringify({ case: '加载期间切换日期', input: mainState.bizDateInput.value, displayed: mainState.shown(), calls, scheduled: mainState.scheduled }))

  const a = deferred()
  const b = deferred()
  const createSide = new Function('V', 'network', `
    const {ref}=V;
    let dispatchRequestId=0,dashboardDisposed=false;
    const dispatchReport=ref(null),dispatchLoading=ref(false),dispatchError=ref(''),projectKey='daily_report_25_26';
    const queryDispatchData=network;
    ${cut('async function fetchDispatchInfoData(', 'watch(\n  () => effectiveBizDate.value,\n  (newDate) => {\n    fetchSpotElectricityData')}
    return {fetchDispatchInfoData,dispatchReport,dispatchLoading,dispatchError};
  `)
  const side = createSide(vue, (_, p) => p.biz_date === '2026-11-01' ? a.promise : b.promise)
  const ra = side.fetchDispatchInfoData('2026-11-01')
  const rb = side.fetchDispatchInfoData('2026-11-02')
  b.resolve({ items: [{ biz_date: '2026-11-02' }] })
  await rb
  a.resolve({ items: [{ biz_date: '2026-11-01' }] })
  await ra
  assert.equal(side.dispatchReport.value.biz_date, '2026-11-02')
  console.log(JSON.stringify({ case: '调度旧请求后返回', selected: '2026-11-02', displayed: side.dispatchReport.value.biz_date }))

  const old = deferred()
  const cacheState = createMain(vue, () => old.promise)
  cacheState.dashboardCache.set('2026-11-02', { date: '2026-11-02' })
  const oldRequest = cacheState.loadDashboardData('2026-11-01')
  await cacheState.loadDashboardData('2026-11-02')
  old.resolve({ date: '2026-11-01' })
  await oldRequest
  assert.equal(cacheState.shown(), '2026-11-02')
  console.log(JSON.stringify({ case: '切回已缓存日期时旧请求未取消', requested: '2026-11-02', displayed: cacheState.shown() }))

  const createCoal = new Function('V', `
    const {ref,computed}=V;
    const coalStdSection=ref({'本期':{'集团汇总':10},'同期':{'集团汇总':8},'本月累计':{'集团汇总':200},'同期月累计':{'集团汇总':180},'本供暖期累计':{'集团汇总':1000},'同供暖期累计':{'集团汇总':900}});
    const roundOrNull=v=>v??null,normalizeMetricValue=v=>v??null,findPreferredIndex=a=>a.indexOf('集团汇总');
    const buildCumulativeHeadline=(value,peer,options)=>({value,peer,...options});
    const formatHeadlineNumber=v=>String(v);
    const effectiveBizDate=ref('2026-11-02'),bizDateInput=ref('2026-11-02'),DYNAMIC_PLAN_START_DATE='2026-11-01';
    const dashboardData={meta:{pushDate:'2026-11-02'}};
    const coalPlanComparisonData=ref({in_plan_period:true,daily:{plan_value:12,status:'dynamic'}});
    ${cut('const coalStdFallbackCategories =', 'const complaintMetricOrder =')}
    ${cut('const getCoalStdBucket =', 'const coalStdColumns =')}
    ${cut('const primaryCoalHeadline =', '// --- 标煤耗量动态分解计划对比状态与逻辑 ---')}
    ${cut('const dailyCoalPlanSummary =', 'const seasonCoalPlanSummary =')}
    return {coalStdPhaseMode,primaryCoalHeadline,dailyCoalPlanSummary};
  `)
  const coal = createCoal(vue)
  const before = { actual: coal.primaryCoalHeadline.value.value, deviation: coal.dailyCoalPlanSummary.value.diff }
  coal.coalStdPhaseMode.value = 'monthly'
  const after = { actual: coal.primaryCoalHeadline.value.value, deviation: coal.dailyCoalPlanSummary.value.diff }
  assert.deepEqual(after, before)
  assert.equal(after.actual, 10)
  assert.equal(after.deviation, -2)
  console.log(JSON.stringify({ case: '切换标煤图表到本月累计影响当日卡片', dailyPlan: 12, before, after }))
  coal.coalStdPhaseMode.value = 'seasonal'
  assert.equal(coal.primaryCoalHeadline.value.value, 10)

  const toClear = deferred()
  const cleared = createMain(vue, () => toClear.promise)
  const clearing = cleared.loadDashboardData('2026-11-01')
  cleared.bizDateInput.value = ''
  toClear.resolve({date:'2026-11-01'})
  await clearing
  assert.equal(cleared.shown(), undefined)
  assert.equal(cleared.isLoading.value, false)

  const failed = createMain(vue, () => Promise.reject(new Error('注入主请求失败')))
  await failed.loadDashboardData('2026-11-01')
  assert.match(failed.dashboardError.value, /注入主请求失败/)
  assert.equal(failed.shown(), undefined)
  const failedSide = createSide(vue, () => Promise.reject(new Error('注入调度失败')))
  await failedSide.fetchDispatchInfoData('2026-11-01')
  assert.match(failedSide.dispatchError.value, /注入调度失败/)
  console.log('通过：清空日期不回填、主请求与调度失败可见；错误日志为预期注入。')

  const createExtras = new Function('V','network', `
    const {ref}=V;
    let dashboardDisposed=false,spotElecRequestId=0,coalPlanRequestId=0;
    const projectKey='daily_report_25_26',effectiveBizDate=ref(''),DYNAMIC_PLAN_START_DATE='2026-11-01';
    const spotElecSummary=ref(null),spotElecPoints=ref([]),spotElecLoading=ref(false),spotElecError=ref('');
    const coalPlanComparisonData=ref(null),isCoalPlanLoading=ref(false),coalPlanError=ref('');
    const getSpotElectricitySummary=(_,d)=>network(d),getSpotElectricityPoints=()=>Promise.resolve({ok:true,items:[]}),fetchCoalPlanComparison=p=>network(p.bizDate);
    ${cut('async function fetchSpotElectricityData(', 'async function fetchDispatchInfoData(')}
    ${cut('async function loadCoalPlanComparison(', 'watch(\n  () => effectiveBizDate.value,')}
    return {fetchSpotElectricityData,spotElecSummary,spotElecLoading,spotElecError,loadCoalPlanComparison,coalPlanComparisonData,isCoalPlanLoading,coalPlanError};
  `)
  for (const [method,key,loading,error] of [
    ['fetchSpotElectricityData','spotElecSummary','spotElecLoading','spotElecError'],
    ['loadCoalPlanComparison','coalPlanComparisonData','isCoalPlanLoading','coalPlanError'],
  ]) {
    const early=deferred(),late=deferred()
    const extras=createExtras(vue,d=>d==='2026-11-01'?early.promise:late.promise)
    const ra=extras[method]('2026-11-01'),rb=extras[method]('2026-11-02')
    const result=d=>({ok:true,biz_date:d,data:{biz_date:d}})
    early.resolve(result('2026-11-01')); await ra
    assert.equal(extras[loading].value,true)
    late.resolve(result('2026-11-02')); await rb
    assert.equal(extras[key].value.biz_date,'2026-11-02')
    const again=extras[method]('2026-11-01')
    await extras[method](''); await again
    assert.equal(extras[key].value,null)
    const slow=deferred(),fast=deferred()
    const reverse=createExtras(vue,d=>d==='2026-11-01'?slow.promise:fast.promise)
    const ro=reverse[method]('2026-11-01'),rn=reverse[method]('2026-11-02')
    fast.resolve(result('2026-11-02'));await rn
    slow.resolve(result('2026-11-01'));await ro
    assert.equal(reverse[key].value.biz_date,'2026-11-02')
    const broken=createExtras(vue,()=>Promise.reject(new Error('注入扩展请求失败')))
    await broken[method]('2026-11-01')
    assert.match(broken[error].value,/注入扩展请求失败/)
    console.log(`通过：${method} 乱序、loading归属、清空日期与失败提示`)
  }
}
main().catch(err => { console.error(err); process.exitCode = 1 })
