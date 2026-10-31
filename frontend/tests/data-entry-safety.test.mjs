// 对实际页面函数注入延迟/失败接口，不访问业务服务器或数据库。
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { parse } from '@babel/parser'
import { entryContextKey, requireEntryQuery, requireSubmissionSuccess } from '../src/projects/daily_report_25_26/composables/entrySubmissionGuard.js'

const source = readFileSync(new URL('../src/projects/daily_report_25_26/pages/DataEntryView.vue', import.meta.url), 'utf8').match(/<script setup>([\s\S]*?)<\/script>/)[1]
const ast = parse(source, { sourceType: 'module' })
function snippet(name) {
  const node = ast.program.body.find(node => node.id?.name === name || node.declarations?.some(d => d.id.name === name))
  assert.ok(node, name)
  return source.slice(node.start, node.end)
}
function functions(state, names) {
  return new Function('state', `with(state) { ${names.map(snippet).join(';\n')}; return { ${names.join(',')} }; }`)(state)
}
const ref = value => ({ value })
function deferred() {
  let resolve, reject
  const promise = new Promise((a, b) => { resolve = a; reject = b })
  return { promise, resolve, reject }
}
const tick = () => new Promise(resolve => setImmediate(resolve))

function loadState() {
  const state = {
    projectKey: 'p', loadGeneration: 0, internalDateChange: false,
    activeSheetKey: ref('A'), pageConfig: ref('config'), bizDate: ref('2026-10-30'),
    canonicalBizDate: ref('2026-10-30'), isLoadingTemplate: ref(false),
    loadedEntryContext: ref(null), entryLoadError: ref(''), isDailyPage: ref(true),
    linkageMap: ref(new Map()), baseColumns: ref([]), sheetName: ref(''), unitName: ref(''), unitId: ref(''),
    columns: ref([]), rows: ref([]), templateType: ref('standard'), validationEnabled: ref(true),
    validationExplanationMap: ref(new Map()), templateValidationRaw: ref(null), latestRequestId: ref(''),
    gridColumns: ref([]), gridSource: ref([]), readOnlyThreshold: ref(1), isReadOnlyForDate: ref(false),
    templateDicts: ref({}), clearRefreshCountdown() {}, nextTick: async () => {},
    getTemplate: async () => ({ ok: true, columns: ['项目', '单位', '(本期日)'], rows: [['发电', '度', '']], unit_id: 'U' }),
    queryData: async (_p, _s, payload) => ({ ok: true, columns: ['项目', '单位', payload.biz_date], rows: [['发电', '度', payload.biz_date]] }),
    applyTemplatePlaceholders: template => ({ template }),
    resolveValidationEnabledFlag: () => false, normalizeExplanationMapping: () => new Map(),
    rebuildValidationRulesFromRows() {}, runFullValidation() {}, clearAllValidationIssues() {},
    normalizeDictPayload: value => value, rebuildLinkageMapFromPayload() {}, applyReadonlyToColumns() {},
    newRequestId: () => Math.random().toString(), requireEntryQuery, entryContextKey,
  }
  state.replaceDatePlaceholdersInColumns = columns => columns.map(c => c === '(本期日)' ? state.bizDate.value : c)
  state.setupStandardGrid = state.setupCrosstabGrid = async tpl => { state.gridSource.value = tpl.rows; state.columns.value = tpl.columns }
  state.applyStandardQueryResult = async (q, current) => { if (current()) { state.rows.value = q.rows; state.gridSource.value = q.rows } }
  state.entryDataReady = { get value() { return !state.isLoadingTemplate.value && !state.entryLoadError.value && state.loadedEntryContext.value === entryContextKey(state.activeSheetKey.value, state.bizDate.value, state.pageConfig.value) } }
  state.entryLocked = { get value() { return !state.entryDataReady.value } }
  state.saveCurrentSheetToCache = () => { state.saved = state.bizDate.value }
  state.sheetCache = new Map()
  state.isPreparingSubmission = ref(false)
  state.isSubmitting = ref(false)
  state.watch = (_getter, callback, options) => { state.dateWatcher = callback; state.watchOptions = options; return () => {} }
  const loaded = functions(state, ['loadTemplate', 'stop'])
  state.loadTemplate = loaded.loadTemplate
  return state
}

test('切换日期立即使网格与缓存失效，加载成功才解锁', async () => {
  const s = loadState()
  await s.loadTemplate(null, { preserveDate: true })
  assert.equal(s.entryDataReady.value, true)
  const q = deferred()
  s.queryData = () => q.promise
  s.sheetCache.set('old', {})
  s.bizDate.value = '2026-10-31'
  s.dateWatcher()
  assert.equal(s.watchOptions.flush, 'sync')
  assert.equal(s.sheetCache.size, 0)
  assert.equal(s.entryDataReady.value, false)
  await tick()
  q.resolve({ ok: true, columns: [], rows: [['新日期']] })
  await tick()
  assert.equal(s.entryDataReady.value, true)
  assert.equal(s.saved, '2026-10-31')
})

test('读取失败保持锁定并明确报错，重试成功才恢复', async () => {
  const s = loadState()
  s.queryData = async () => { throw Error('网络断开') }
  await assert.rejects(s.loadTemplate(null, { preserveDate: true }), /网络断开/)
  assert.equal(s.entryDataReady.value, false)
  assert.match(s.entryLoadError.value, /网络断开/)
  assert.equal(s.isLoadingTemplate.value, false)
  s.queryData = async () => ({ ok: true, columns: [], rows: [] })
  await s.loadTemplate(null, { preserveDate: true })
  assert.equal(s.entryDataReady.value, true)
})

test('晚到的旧日期查询不能覆盖新日期，旧失败不污染新状态', async () => {
  for (const fail of [false, true]) {
    const s = loadState(), old = deferred()
    s.queryData = async () => old.promise
    const first = s.loadTemplate(null, { preserveDate: true })
    await tick()
    s.bizDate.value = '2026-11-01'
    s.queryData = async () => ({ ok: true, columns: [], rows: [['最新日期']] })
    await s.loadTemplate(null, { preserveDate: true })
    if (fail) old.reject(Error('旧请求失败'))
    else old.resolve({ ok: true, columns: [], rows: [['旧日期']] })
    assert.equal(await first, false)
    assert.deepEqual(s.gridSource.value, [['最新日期']])
    assert.equal(s.entryDataReady.value, true)
  }
})

test('慢模板响应和快速切表都不能回填旧上下文', async () => {
  const s = loadState(), old = deferred(), original = s.getTemplate
  s.getTemplate = () => old.promise
  const first = s.loadTemplate()
  s.activeSheetKey.value = 'B'
  s.getTemplate = original
  await s.loadTemplate('B', { preserveDate: true })
  old.resolve({ columns: ['旧模板'], rows: [['旧表']] })
  assert.equal(await first, false)
  assert.equal(s.loadedEntryContext.value, entryContextKey('B', s.bizDate.value, 'config'))
})

test('内部权威日期赋值不触发第二次查询，用户日期不会被模板改回', async () => {
  const s = loadState()
  s.getTemplate = async () => ({ biz_date: '2026-10-29', columns: ['项目', '单位', '(本期日)'], rows: [] })
  await s.loadTemplate()
  assert.equal(s.bizDate.value, '2026-10-29')
  assert.equal(s.columns.value[2], '2026-10-29')
  s.bizDate.value = '2026-10-31'
  await s.loadTemplate(null, { preserveDate: true })
  assert.equal(s.bizDate.value, '2026-10-31')
  assert.equal(s.columns.value[2], '2026-10-31')
})

test('标准表、交叉表和常量表均验证完整响应，常量不传日期', async () => {
  for (const type of ['standard', 'crosstab', 'constant']) {
    const s = loadState()
    s.getTemplate = async () => ({ template_type: type, columns: ['项目', '单位', '本期'], rows: [] })
    const calls = []
    s.queryData = async (_p, _sheet, payload) => { calls.push(payload); return { ok: true, columns: ['项目'], rows: [] } }
    await s.loadTemplate(null, { preserveDate: true })
    assert.equal(calls.length, 1)
    assert.equal(calls[0].biz_date, type === 'constant' ? undefined : '2026-10-30')
    assert.equal(s.entryDataReady.value, true)
    s.queryData = async () => ({ ok: false, message: '数据异常' })
    await assert.rejects(s.loadTemplate(null, { preserveDate: true }), /数据异常/)
    assert.equal(s.entryDataReady.value, false)
  }
})

function batchState() {
  const s = {
    canSubmitCurrentProject: ref(true), submitDisabled: ref(false), entryLocked: ref(false),
    activeSheetKey: ref('A'), bizDate: ref('2026-10-30'), pageConfig: ref('config'),
    unitSheets: ref([{ sheet_key: 'A', sheet_name: '甲表' }, { sheet_key: 'B', sheet_name: '乙表' }]),
    unitSheetsReady: ref(true), isPreparingSubmission: ref(false), isSubmitting: ref(false),
    entryDataReady: ref(true), validationEnabled: ref(false), hasBlockingValidation: ref(false),
    sheetCache: new Map(), projectKey: 'p', submitTime: ref(''), messages: [], calls: [],
    dirtySheets: new Set(['A', 'B']),
    clearRefreshCountdown() {}, applyReadonlyToColumns() {}, runFullValidation() {}, entryContextKey, requireSubmissionSuccess,
  }
  s.saveCurrentSheetToCache = key => s.sheetCache.set(key, { isLoaded: true, contextKey: entryContextKey(key, s.bizDate.value, s.pageConfig.value) })
  s.onSwitchSheetTab = async key => { s.activeSheetKey.value = key; s.saveCurrentSheetToCache(key); return true }
  s.buildPayloadForCachedState = () => ({ biz_date: s.bizDate.value })
  s.submitData = async (_p, key, payload) => { s.calls.push({ key, payload }); return { ok: true, inserted: 1 } }
  s.showSubmitFeedback = (type, message) => s.messages.push({ type, message })
  s.startRefreshCountdown = () => { s.refreshed = true }
  s.run = functions(s, ['onSubmitAll']).onSubmitAll
  return s
}

test('任一表加载失败或缺失缓存时，没有任何提交，也不提示成功', async () => {
  for (const mode of ['throw', 'missing', 'stale']) {
    const s = batchState(), original = s.onSwitchSheetTab
    s.onSwitchSheetTab = async key => {
      if (key === 'B') {
        if (mode === 'throw') throw Error('乙表加载失败')
        s.activeSheetKey.value = key
        s.saveCurrentSheetToCache = () => {}
        if (mode === 'stale') s.sheetCache.set(key, { isLoaded: true, contextKey: '旧日期' })
        return true
      }
      return original(key)
    }
    await s.run()
    assert.equal(s.calls.length, 0)
    assert.match(s.messages.at(-1).message, /未提交任何报表/)
    assert.equal(s.isPreparingSubmission.value, false)
  }
})

test('准备阶段日期变化或未加载完整清单时停止所有提交', async () => {
  for (const mode of ['date', 'catalog']) {
    const s = batchState(), original = s.onSwitchSheetTab
    if (mode === 'catalog') s.unitSheetsReady.value = false
    else s.onSwitchSheetTab = async key => { const r = await original(key); s.bizDate.value = '2026-11-01'; return r }
    await s.run()
    assert.equal(s.calls.length, 0)
  }
})

test('逐表校验后才提交，任一校验阻断都不写入', async () => {
  const s = batchState()
  s.validationEnabled.value = true
  s.runFullValidation = () => { s.hasBlockingValidation.value = s.activeSheetKey.value === 'B' }
  await s.run()
  assert.equal(s.calls.length, 0)
  assert.match(s.messages.at(-1).message, /乙表.*校验/)
})

test('部分成功需等待全部请求完成，只更新成功表，不自动刷新', async () => {
  const s = batchState(), last = deferred()
  s.submitData = async (_p, key) => key === 'A' ? { ok: true, inserted: 1 } : last.promise
  const run = s.run()
  await tick()
  assert.equal(s.isSubmitting.value, true)
  last.reject(Error('连接失败'))
  await run
  assert.match(s.messages.at(-1).message, /成功 1\/2.*乙表.*连接失败/)
  assert.ok(s.sheetCache.get('A').submitTime)
  assert.equal(s.sheetCache.get('B').submitTime, undefined)
  assert.deepEqual([...s.dirtySheets], ['B'])
  assert.equal(s.refreshed, undefined)
})

test('业务失败、零写入和非预期响应不能算成功；全部确认成功才刷新', async () => {
  for (const reply of [{ ok: false, message: '拒绝写入' }, { ok: true, inserted: 0 }, null]) {
    const s = batchState()
    s.submitData = async () => reply
    await s.run()
    assert.match(s.messages.at(-1).message, /成功 0\/2/)
    assert.equal(s.refreshed, undefined)
  }
  const s = batchState()
  await s.run()
  assert.equal(s.calls.length, 2)
  assert.equal(s.refreshed, true)
  assert.equal(s.isSubmitting.value, false)
})

test('未就绪时单表提交也被阻止', async () => {
  const state = { entryLocked: ref(true), showSubmitFeedback: (...args) => { state.feedback = args } }
  await functions(state, ['onSubmit']).onSubmit()
  assert.match(state.feedback[1], /完整加载/)
})

test('切日期前取消确认保留日期和修改，确认后才切换；提交中禁止切换', () => {
  const state = {
    bizDate: ref('2026-10-30'), dirtySheets: new Set(['A']), isPreparingSubmission: ref(false),
    isSubmitting: ref(false), efficiencyUploading: ref(false), window: { confirm: () => false },
  }
  const change = functions(state, ['onBizDateChanged']).onBizDateChanged
  const event = { target: { value: '2026-10-31' } }
  change(event)
  assert.equal(state.bizDate.value, '2026-10-30')
  assert.equal(event.target.value, '2026-10-30')
  assert.equal(state.dirtySheets.size, 1)
  state.window.confirm = () => true
  event.target.value = '2026-10-31'
  change(event)
  assert.equal(state.bizDate.value, '2026-10-31')
  assert.equal(state.dirtySheets.size, 0)
  state.isSubmitting.value = true
  event.target.value = '2026-11-01'
  change(event)
  assert.equal(state.bizDate.value, '2026-10-31')
})

test('提交后的新编辑会取消自动刷新，保留网格内容', () => {
  const state = {
    dirtySheets: new Set(), refreshCountdown: ref(0), refreshCountdownTimer: null,
    clearRefreshCountdown() {}, showSubmitFeedback() {}, reloadTemplate() { state.reloaded = true; return Promise.resolve() },
    window: { setInterval(fn) { state.timer = fn; return 1 } },
  }
  functions(state, ['startRefreshCountdown']).startRefreshCountdown(1)
  state.dirtySheets.add('A')
  state.timer()
  assert.equal(state.reloaded, undefined)
  assert.equal(state.dirtySheets.size, 1)
})

test('实际缓存存取拒绝旧日期和不同配置，合法缓存完整恢复', async () => {
  const s = loadState()
  Object.assign(s, {
    submitTime: ref(''), rowLabelIndex: ref(new Map()), validationRuleMap: ref(new Map()),
    validationDependents: ref(new Map()), cellValidationMap: ref(new Map()), virtualValidationRules: ref([]),
    sheetValidationEnabled: ref(true), sheetAiReportEnabled: ref(false),
  })
  s.currentEntryContext = { get value() { return entryContextKey(s.activeSheetKey.value, s.bizDate.value, s.pageConfig.value) } }
  const cache = functions(s, ['saveCurrentSheetToCache', 'restoreSheetFromCache'])
  await s.loadTemplate()
  cache.saveCurrentSheetToCache()
  const saved = s.sheetCache.get('A')
  s.bizDate.value = '2026-11-01'
  assert.equal(cache.restoreSheetFromCache('A'), false)
  s.bizDate.value = '2026-10-30'
  s.pageConfig.value = 'other-config'
  assert.equal(cache.restoreSheetFromCache('A'), false)
  s.pageConfig.value = 'config'
  assert.equal(cache.restoreSheetFromCache('A'), true)
  assert.equal(s.loadedEntryContext.value, saved.contextKey)
  assert.equal(s.entryDataReady.value, true)
})
