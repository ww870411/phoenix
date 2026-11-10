// 通过实际 Vue 服务端渲染和页面函数核查导航/状态，不启动浏览器。
import { after, before, test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'
import { createSSRApp, h } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { parse } from '@babel/parser'
import { correctionBreadcrumbs, correctionColumn, correctionValue } from '../src/projects/daily_report_25_26/composables/dataCorrectionPresentation.js'

let server, Breadcrumbs, RecordsView
before(async () => {
  server = await createServer({
    configFile: false, root: fileURLToPath(new URL('..', import.meta.url)),
    optimizeDeps: { noDiscovery: true, include: [] },
    plugins: [vue()], appType: 'custom', server: { middlewareMode: true, hmr: false, watch: null },
  })
  Breadcrumbs = (await server.ssrLoadModule('/src/projects/daily_report_25_26/components/Breadcrumbs.vue')).default
  RecordsView = (await server.ssrLoadModule('/src/projects/daily_report_25_26/pages/DataCorrectionsView.vue')).default
})
after(async () => { await server?.close() })

async function render(component, props = {}) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { render: () => null } }] })
  await router.push('/projects/daily_report_25_26/pages/data_corrections')
  const app = createSSRApp({ render: () => h(component, props) })
  app.use(createPinia()); app.use(router)
  return renderToString(app)
}

test('真实面包屑渲染包含项目选择、具名项目入口和不可点击的当前页', async () => {
  const items = correctionBreadcrumbs('2026-2027供暖期生产日报')
  const html = await render(Breadcrumbs, { items })
  assert.match(html, /aria-label="面包屑导航"/)
  assert.match(html, /href="\/projects"[^>]*>项目选择<\/a>/)
  assert.match(html, /href="\/projects\/daily_report_25_26\/pages"[^>]*>2026-2027供暖期生产日报<\/a>/)
  assert.match(html, /aria-current="page"[^>]*>数据修正申请记录<\/span>/)
  assert.equal((html.match(/aria-hidden="true"/g) || []).length, 2)
  assert.doesNotMatch(html, /href="[^"]*data_corrections"/)
})

test('实际记录页面首屏具备完整导航，读取完成前不会闪现空结果或分页', async () => {
  const html = await render(RecordsView)
  assert.match(html, /2026-2027供暖期生产日报/)
  assert.match(html, /正在读取申请记录/)
  assert.doesNotMatch(html, /暂无修正申请|共 0 条|项目页面/)
})

test('记录页面使用已加载的真实项目名称，不将供暖期名称写死', async () => {
  const { projects } = await server.ssrLoadModule('/src/projects/daily_report_25_26/composables/useProjects.js')
  const original = projects.value
  try {
    projects.value = [{ project_id: 'daily_report_25_26', project_name: '新的供暖期生产日报' }]
    const html = await render(RecordsView)
    assert.match(html, /href="\/projects\/daily_report_25_26\/pages"[^>]*>新的供暖期生产日报<\/a>/)
  } finally { projects.value = original }
})

test('零值、空格和小数的展示不混淆，表头不泄漏占位符', () => {
  assert.equal(correctionValue(0), '0')
  assert.equal(correctionValue('0.0000'), '0.0000')
  for (const value of [null, undefined, '', '  ']) assert.equal(correctionValue(value), '空值')
  assert.equal(correctionValue('-2.5000'), '-2.5000')
  assert.equal(correctionColumn('(本期日)'), '本期值')
  assert.equal(correctionColumn('(同期日)'), '同期值')
  assert.equal(correctionColumn('港口存煤'), '港口存煤')
})

const source = readFileSync(new URL('../src/projects/daily_report_25_26/pages/DataCorrectionsView.vue', import.meta.url), 'utf8').match(/<script setup>([\s\S]*?)<\/script>/)[1]
const ast = parse(source, { sourceType: 'module' })
function functions(state, names) {
  const snippets = names.map(name => {
    const node = ast.program.body.find(n => n.id?.name === name)
    assert.ok(node, name)
    return source.slice(node.start, node.end)
  })
  return new Function('state', `with(state) { ${snippets.join('\n')} return { ${names.join(',')} }; }`)(state)
}
const ref = value => ({ value })
function state() {
  return { loading: ref(false), resolving: ref(false), status: ref('pending'), offset: ref(100),
    records: ref([{ id: '旧记录' }]), total: ref(101), error: ref(''), message: ref('上次提示'),
    selection: ref({ record: { id: 1 }, action: 'approve' }), note: ref('已核实'),
    resolutionError: ref(''), actionLabels: { approve: '确认修正' } }
}

test('待审批记录减少导致末页失效时，重新读取最后有效页', async () => {
  const s = state(), queries = []
  s.dataCorrectionRequest = async query => { queries.push(query); return { records: [{ id: 7 }], total: 51 } }
  await functions(s, ['load']).load()
  assert.equal(s.offset.value, 50)
  assert.equal(queries.length, 2)
  assert.match(queries[1], /offset=50/)
  assert.deepEqual(s.records.value, [{ id: 7 }])
  assert.equal(s.loading.value, false)
})

test('筛选无记录时回到第一页，失败时清除旧成功提示并保留错误状态', async () => {
  const s = state()
  s.dataCorrectionRequest = async () => ({ records: [], total: 0 })
  await functions(s, ['load']).load()
  assert.equal(s.offset.value, 0)
  assert.deepEqual(s.records.value, [])
  s.dataCorrectionRequest = async () => { throw new Error('读取失败') }
  s.message.value = '上次成功'
  await functions(s, ['load']).load()
  assert.equal(s.error.value, '读取失败')
  assert.equal(s.message.value, '')
  assert.equal(s.loading.value, false)
})

test('审批冲突保留弹窗、申请和用户说明，成功后刷新再显示结果', async () => {
  const s = state()
  s.dataCorrectionRequest = async () => { throw new Error('原数据已变化') }
  s.load = async () => {}
  const view = functions(s, ['resolve'])
  await view.resolve()
  assert.equal(s.selection.value.record.id, 1)
  assert.equal(s.note.value, '已核实')
  assert.equal(s.resolutionError.value, '原数据已变化')
  s.dataCorrectionRequest = async () => ({})
  s.load = async () => { assert.equal(s.selection.value, null); s.message.value = '' }
  await view.resolve()
  assert.equal(s.message.value, '确认修正完成。')
  assert.equal(s.resolving.value, false)
})
