import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { compileScript, parse } from '@vue/compiler-sfc'
import * as Vue from 'vue'

// 使用真实模板和 Vue 渲染器验证点击后的详情渲染；路由、登录态和网络采用固定夹具。
const filename = new URL('../src/projects/insulation_pipe_supply_2026/pages/JointReviewHallView.vue', import.meta.url)
const { descriptor } = parse(readFileSync(filename, 'utf8'))
const compiled = compileScript(descriptor, {
  id: 'hall-regression', inlineTemplate: true,
  templateOptions: { compilerOptions: { hoistStatic: false } },
}).content
const componentCode = compiled
  .replace(/import\s+([\s\S]*?)\s+from\s+['"]([^'"]+)['"];?/g, (_, bindings, path) => {
    if (bindings.trim().startsWith('{')) {
      return `const ${bindings.replace(/\bas\b/g, ':')} = ${path === 'vue' ? 'Vue' : 'deps'};`
    }
    return `const ${bindings.trim()} = deps.${bindings.trim()};`
  })
  .replace('export default', 'return')
const makeComponent = new Function('Vue', 'deps', componentCode)
// 本回归只检查卡片交互，原生输入框指令需要浏览器 DOM，留给浏览器验收。
const testVue = { ...Vue, vModelText: {}, vModelSelect: {} }

function makeNode(type, text = '') {
  return { type, text, props: {}, children: [], parent: null }
}

const renderer = Vue.createRenderer({
  createElement: type => makeNode(type),
  createText: text => makeNode('#text', text),
  createComment: text => makeNode('#comment', text),
  setText: (node, text) => { node.text = text },
  setElementText: (node, text) => { node.text = text; node.children = [] },
  patchProp: (node, key, previous, value) => { node.props[key] = value },
  insert(node, parent, anchor = null) {
    if (node.parent) this.remove(node)
    const index = anchor ? parent.children.indexOf(anchor) : -1
    parent.children.splice(index < 0 ? parent.children.length : index, 0, node)
    node.parent = parent
  },
  remove(node) {
    if (!node.parent) return
    const index = node.parent.children.indexOf(node)
    if (index >= 0) node.parent.children.splice(index, 1)
    node.parent = null
  },
  parentNode: node => node.parent,
  nextSibling: node => node.parent?.children[node.parent.children.indexOf(node) + 1] || null,
})

function findNodes(node, predicate) {
  return [ ...(predicate(node) ? [node] : []), ...node.children.flatMap(child => findNodes(child, predicate)) ]
}
const hasClass = name => node => String(node.props.class || '').split(' ').includes(name)
const flush = async () => { await new Promise(resolve => setImmediate(resolve)); await Vue.nextTick() }
const nodeText = node => node.text + node.children.map(nodeText).join('')

test('提请弹窗备注更正写入载荷，其他状态明细不能更正，非法数量拒绝提交', async () => {
  const modalFile = new URL('../src/projects/insulation_pipe_supply_2026/components/InitiateJointReviewModal.vue', import.meta.url)
  const { descriptor: modalDescriptor } = parse(readFileSync(modalFile, 'utf8'))
  const code = compileScript(modalDescriptor, { id: 'modal-regression', inlineTemplate: true,
    templateOptions: { compilerOptions: { hoistStatic: false } } }).content
    .replace(/import\s+([\s\S]*?)\s+from\s+['"]([^'"]+)['"];?/g, (_, bindings, path) =>
      `const ${bindings.replace(/\bas\b/g, ':')} = ${path === 'vue' ? 'Vue' : 'deps'};`)
    .replace('export default', 'return')
  const factory = new Function('Vue', 'deps', code)
  const calls = []
  const root = makeNode('root')
  const order = { id: 1, category: 'fitting', status: 'pending_arrival', ship_remark: '原备注',
    items: [{ id: 1, status: 'pending_arrival', fitting_type: '弯头', model_spec: 'DN100', shipped_qty: 10 },
      { id: 2, status: 'completed', fitting_type: '三通', model_spec: 'DN200', shipped_qty: 20 }] }
  const app = renderer.createApp(factory(testVue, { createJointReview: async payload => { calls.push(payload); return { ok: true } } }),
    { visible: true, order })
  app.mount(root)
  try {
    await flush()
    const fields = findNodes(root, node => node.type === 'fieldset')
    assert.equal(fields[0].props.disabled, false)
    assert.equal(fields[1].props.disabled, true)
    const remark = findNodes(root, node => node.type === 'textarea' && node.props.placeholder?.includes('发货备注'))[0]
    remark.props['onUpdate:modelValue']('新备注')
    const reason = findNodes(root, node => node.type === 'textarea' && node.props.placeholder?.includes('实况'))[0]
    reason.props['onUpdate:modelValue']('现场核实更正')
    await flush()
    findNodes(root, hasClass('btn-submit'))[0].props.onClick()
    await flush()
    assert.deepEqual(calls[0].proposed_patch, { ship_remark: '新备注' })
    const quantity = findNodes(fields[0], node => node.type === 'input' && node.props.type === 'number')[0]
    quantity.props['onUpdate:modelValue'](Infinity)
    await flush()
    findNodes(root, hasClass('btn-submit'))[0].props.onClick()
    await flush()
    assert.equal(calls.length, 1)
    assert.ok(nodeText(root).includes('有限正数'))
  } finally { app.unmount() }
})

function mountHall(overrides = {}) {
  const emptyComponent = { render: () => null }
  const deps = {
    useRoute: () => ({ query: {}, path: '/hall' }),
    useRouter: () => ({ push() {}, replace() {} }),
    useAuthStore: () => ({ user: { group: 'tube_supplier' } }),
    AppHeader: emptyComponent, Breadcrumbs: emptyComponent,
    listJointReviews: async () => ({ ok: true, total: 0, items: [] }),
    ...overrides,
  }
  const root = makeNode('root')
  const app = renderer.createApp(makeComponent(testVue, deps))
  const errors = []
  app.config.errorHandler = error => errors.push(error)
  app.mount(root)
  return { app, root, errors }
}

test('异议方可以重新表决，裁决通过展示实际票数', async () => {
  const review = {
    id: 1, order_category: 'pipe', review_status: 'voting', can_i_vote: true,
    my_voted: true, my_vote_decision: 'reject', needs_my_vote: false,
    required_entities: [{ entity_type: 'supplier', entity_id: 'SUP' }],
    approved_entities: [], rejected_entities: [], proposed_patch: {},
  }
  const { app, root, errors } = mountHall({
    listJointReviews: async params => ({ ok: true, total: 1, items: params.limit === 1 ? [] : [review] }),
  })
  try {
    await flush()
    findNodes(root, hasClass('btn-fold-toggle'))[0].props.onClick({ stopPropagation() {} })
    await flush()
    assert.equal(findNodes(root, hasClass('btn-approve')).length, 1)
    findNodes(root, hasClass('btn-approve'))[0].props.onClick()
    await flush()
    assert.ok(nodeText(root).includes('同意更正确认'))
    assert.deepEqual(errors, [])
  } finally { app.unmount() }
  const next = mountHall({
    listJointReviews: async params => ({ ok: true, total: 1, items: params.limit === 1 ? [] : [{
      ...review, review_status: 'approved', finalized_by: '管理员', approval_type: 'arbitration',
    }] }),
  })
  try {
    await flush()
    assert.ok(nodeText(next.root).includes('终局裁决通过已生效 (1/2 同意)'))
    assert.ok(!nodeText(next.root).includes('全票通过已生效'))
  } finally { next.app.unmount() }
})

test('隐藏状态筛选不传到其他标签，筛选结果不覆盖个人全局KPI', async () => {
  const calls = []
  const { app, root } = mountHall({
    listJointReviews: async params => {
      calls.push(params)
      return { ok: true, total: params.limit === 1 ? 12 : 2, items: [] }
    },
  })
  try {
    await flush()
    const clickTab = async text => {
      findNodes(root, hasClass('hall-tab-btn')).find(node => nodeText(node).includes(text)).props.onClick()
      await flush()
    }
    await clickTab('全网会审台账')
    const statusSelect = findNodes(root, node => node.type === 'select').find(node => nodeText(node).includes('已通过'))
    statusSelect.props['onUpdate:modelValue']('approved')
    statusSelect.props.onChange()
    await flush()
    await clickTab('待我联审')
    const latest = calls.filter(params => params.limit === 20).at(-1)
    assert.equal(latest.review_status, undefined)
    const pendingCard = findNodes(root, hasClass('kpi-card')).find(node => nodeText(node).includes('待我联审表决'))
    assert.ok(nodeText(pendingCard).includes('12'))
    const search = findNodes(root, node => node.type === 'input' && node.props.placeholder?.includes('搜索会审单号'))[0]
    search.props['onUpdate:modelValue']('关键词')
    findNodes(root, hasClass('btn-query'))[0].props.onClick()
    await flush()
    assert.ok(nodeText(pendingCard).includes('12'))
  } finally { app.unmount() }
})

test('慢旧响应不会覆盖新标签列表或提前结束加载', async () => {
  let finishOld, finishNew
  const { app, root } = mountHall({
    listJointReviews: params => params.limit === 1 ? Promise.resolve({ ok: true, total: 0 })
      : new Promise(resolve => { if (params.tab === 'pending_my_vote') finishOld = resolve; else finishNew = resolve }),
  })
  try {
    await flush()
    findNodes(root, hasClass('hall-tab-btn')).find(node => nodeText(node).includes('全网会审台账')).props.onClick()
    await flush()
    finishOld({ ok: true, total: 100, items: [] })
    await flush()
    assert.equal(findNodes(root, hasClass('loading-state')).length, 1)
    finishNew({ ok: true, total: 1, items: [{ id: 5, order_category: 'pipe', review_status: 'voting', proposed_patch: {} }] })
    await flush()
    assert.ok(nodeText(root).includes('共找到 1 笔'))
  } finally { app.unmount() }
})

test('通知ID直接加载旧议案详情并展开，不依赖首屏或个人待办', async () => {
  const calls = []
  const { app, root, errors } = mountHall({
    useRoute: () => ({ query: { tab: 'pending_my_vote', review_id: '99' }, path: '/hall' }),
    getJointReviewDetail: async id => {
      calls.push(id)
      return { ok: true, data: { id, review_no: 'OLD-99', order_category: 'pipe', review_status: 'approved',
        required_entities: [], proposed_patch: {}, approved_entities: [], finalized_by: 'SYSTEM_CONSENSUS' } }
    },
  })
  try {
    await flush()
    assert.deepEqual(calls, [99])
    assert.equal(findNodes(root, hasClass('expanded-details-body')).length, 1)
    assert.ok(nodeText(root).includes('OLD-99'))
    assert.deepEqual(errors, [])
  } finally { app.unmount() }
})

for (const initialGlobalTotal of [53, 0]) {
  test(`全网总数 ${initialGlobalTotal} 独立于标签、筛选和分页，重新进入页面更新统计`, async () => {
    let globalTotal = initialGlobalTotal
    const calls = []
    const emptyComponent = { render: () => null }
    const deps = {
      useRoute: () => ({ query: {}, path: '/hall' }),
      useRouter: () => ({ push() {}, replace() {} }),
      useAuthStore: () => ({ user: { group: 'tube_construction_unit' } }),
      AppHeader: emptyComponent, Breadcrumbs: emptyComponent,
      listJointReviews: async params => {
        calls.push(params)
        if (params.limit === 1) {
          const total = params.tab === 'all' && !params.review_status ? globalTotal : 1
          return { ok: true, items: [], total }
        }
        return {
          ok: true, total: params.search ? 2 : params.tab === 'my_initiated' ? 7 : 25,
          items: [{ id: 42, order_category: 'pipe', review_status: 'voting', proposed_patch: {} }],
        }
      },
    }
    const root = makeNode('root')
    const errors = []
    let app = renderer.createApp(makeComponent(testVue, deps))
    app.config.errorHandler = error => errors.push(error)
    app.mount(root)
    const globalValue = () => {
      const card = findNodes(root, hasClass('kpi-card')).find(node => nodeText(node).includes('全网会审总单数'))
      return nodeText(findNodes(card, hasClass('kpi-val'))[0]).trim()
    }
    const clickText = async (name, className) => {
      const node = findNodes(root, hasClass(className)).find(node => nodeText(node).includes(name))
      node.props.onClick({ stopPropagation() {} })
      await flush()
    }
    try {
      await flush()
      assert.equal(globalValue(), `${globalTotal} 笔`, '初始个人待办条数不能充当全网总数')
      await clickText('我发起的会审', 'hall-tab-btn')
      assert.equal(globalValue(), `${globalTotal} 笔`)
      assert.equal(nodeText(findNodes(root, hasClass('total-text'))[0]), '共找到 7 笔会审提案')
      await clickText('全网会审台账', 'hall-tab-btn')
      const search = findNodes(root, node => node.type === 'input' && node.props.placeholder?.includes('搜索会审单号'))[0]
      search.props['onUpdate:modelValue']('测试关键词')
      await clickText('筛选', 'btn-query')
      assert.equal(globalValue(), `${globalTotal} 笔`)
      assert.equal(nodeText(findNodes(root, hasClass('total-text'))[0]), '共找到 2 笔会审提案')
      await clickText('重置', 'btn-reset')
      const nextPage = findNodes(root, node => node.type === 'button' && nodeText(node).includes('下一页'))[0]
      nextPage.props.onClick()
      await flush()
      assert.ok(calls.some(params => params.page === 2))
      assert.equal(globalValue(), `${globalTotal} 笔`)
      globalTotal += 1
      app.unmount()
      app = renderer.createApp(makeComponent(testVue, deps))
      app.config.errorHandler = error => errors.push(error)
      app.mount(root)
      await flush()
      assert.equal(globalValue(), `${globalTotal} 笔`, '重新进入页面读取最新全网统计')
      assert.ok(calls.some(params => params.tab === 'all' && params.limit === 1 && !params.search && !params.order_category && !params.review_status))
      assert.deepEqual(errors, [])
    } finally {
      app.unmount()
    }
  })
}

test('统计请求部分失败不影响全网总数，全网请求失败显示横线而非错误数字', async t => {
  t.mock.method(console, 'warn', () => {})
  let globalFailed = false
  let globalTotal = 53
  const emptyComponent = { render: () => null }
  const deps = {
    useRoute: () => ({ query: {}, path: '/hall' }),
    useRouter: () => ({ push() {}, replace() {} }),
    useAuthStore: () => ({ user: { group: 'tube_construction_unit' } }),
    AppHeader: emptyComponent, Breadcrumbs: emptyComponent,
    listJointReviews: async params => {
      if (params.limit === 1 && params.tab === 'pending_my_vote') throw new Error('模拟个人统计失败')
      if (params.limit === 1 && params.tab === 'all' && !params.review_status) {
        if (globalFailed) throw new Error('模拟全网统计失败')
        return { ok: true, total: globalTotal, items: [] }
      }
      return { ok: true, total: 0, items: [] }
    },
  }
  const root = makeNode('root')
  let app = renderer.createApp(makeComponent(testVue, deps))
  app.mount(root)
  const globalText = () => nodeText(findNodes(root, hasClass('kpi-val')).find(hasClass('text-slate'))).trim()
  const refresh = async () => {
    app.unmount()
    app = renderer.createApp(makeComponent(testVue, deps))
    app.mount(root)
    await flush()
  }
  try {
    await flush()
    assert.equal(globalText(), '53 笔')
    globalFailed = true
    await refresh()
    assert.equal(globalText(), '— 笔')
    globalFailed = false
    globalTotal = 0
    await refresh()
    assert.equal(globalText(), '0 笔')
  } finally {
    app.unmount()
  }
})

for (const group of ['tube_construction_unit', 'Global_admin']) {
  test(`${group}：单次展开、收起及批量展开不发生渲染异常`, async () => {
    const review = {
      id: 42, review_no: 'REVIEW-TEST', order_no: 'ORDER-TEST', order_category: 'pipe',
      review_status: 'voting', needs_my_vote: false, initiator_name: '测试提请人',
      proposed_patch: { shipped_qty: 10 }, original_snapshot: { shipped_qty: 8 },
      required_entities: [], approved_entities: [], rejected_entities: [], votes: [],
    }
    const emptyComponent = { render: () => null }
    const deps = {
      useRoute: () => ({ query: {}, path: '/hall' }),
      useRouter: () => ({ push() {}, replace() {} }),
      useAuthStore: () => ({ user: { group }, canAccessAdminConsole: group === 'Global_admin' }),
      AppHeader: emptyComponent, Breadcrumbs: emptyComponent,
      listJointReviews: async () => ({ ok: true, items: [review], total: 1 }),
    }
    const root = makeNode('root')
    const errors = []
    const app = renderer.createApp(makeComponent(testVue, deps))
    app.config.errorHandler = error => errors.push(error)
    app.mount(root)
    try {
      await flush()
      const click = async node => {
        node.props.onClick({ stopPropagation() {} })
        await flush()
        assert.deepEqual(errors.map(error => error.message), [], '点击后不应产生 Vue 运行时错误')
      }
      assert.equal(findNodes(root, hasClass('expanded-details-body')).length, 0)
      await click(findNodes(root, hasClass('btn-fold-toggle'))[0])
      assert.equal(findNodes(root, hasClass('expanded-details-body')).length, 1, '单次点击即展开')
      assert.equal(findNodes(root, hasClass('admin-sign-badge')).length, group === 'Global_admin' ? 1 : 0)
      await click(findNodes(root, hasClass('btn-fold-toggle'))[0])
      assert.equal(findNodes(root, hasClass('expanded-details-body')).length, 0, '单次点击即收起')
      await click(findNodes(root, hasClass('folded-summary-strip'))[0])
      assert.equal(findNodes(root, hasClass('expanded-details-body')).length, 1)
      await click(findNodes(root, hasClass('btn-collapse-bottom'))[0])
      await click(findNodes(root, node => node.type === 'button' && node.text.includes('展开全部'))[0])
      assert.equal(findNodes(root, hasClass('expanded-details-body')).length, 1)
    } finally {
      app.unmount()
    }
  })
}
