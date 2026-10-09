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
