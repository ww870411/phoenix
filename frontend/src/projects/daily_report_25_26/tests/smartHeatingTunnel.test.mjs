// 本地执行：node src/projects/daily_report_25_26/tests/smartHeatingTunnel.test.mjs
// 执行真实组件 setup，控制接口和计时器，验证初始化与轮询的请求数量及挂载时机。
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { computed, ref } from 'vue'
import { compileScript, parse } from '@vue/compiler-sfc'

const componentUrl = new URL('../pages/SmartHeatingTunnelView.vue', import.meta.url)
const { descriptor } = parse(await readFile(componentUrl, 'utf8'))
const script = compileScript(descriptor, { id: 'tunnel-behavior-test' }).content
  .replace(/import\s+\{[^}]+\}\s+from 'vue'/, 'const { computed, ref, onMounted, onBeforeUnmount } = harness.vue')
  .replace(/import\s+\{[^}]+\}\s+from 'vue-router'/, 'const { useRoute, useRouter } = harness.router')
  .replace(/import AppHeader from '[^']+'/, 'const AppHeader = {}')
  .replace(/import Breadcrumbs from '[^']+'/, 'const Breadcrumbs = {}')
  .replace(/import\s+\{ useAuthStore \}\s+from '[^']+'/, 'const { useAuthStore } = harness')
  .replace(/import\s+\{[^}]+\}\s+from '\.\.\/services\/api'/, 'const { downloadTunnelClientScript, fetchTunnelConfig, fetchTunnelStatus, getTunnelGatewayUrl, updateTunnelConfig } = harness.api')

function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

const mounted = [], unmounted = [], scheduled = [], statusCalls = [], configCalls = [], cleared = []
const harness = {
  vue: { computed, ref, onMounted: fn => mounted.push(fn), onBeforeUnmount: fn => unmounted.push(fn) },
  router: {
    useRoute: () => ({ params: { projectKey: 'daily_report_25_26' }, query: {} }),
    useRouter: () => ({}),
  },
  useAuthStore: () => ({ isGlobalAdmin: true, token: '' }),
  setTimeout: (fn, delay) => { scheduled.push({ fn, delay }); return scheduled.length },
  clearTimeout: id => cleared.push(id),
  api: {
    fetchTunnelStatus: () => { const call = deferred(); statusCalls.push(call); return call.promise },
    fetchTunnelConfig: () => { const call = deferred(); configCalls.push(call); return call.promise },
    getTunnelGatewayUrl: (project, path) => `/api/${project}/gateway/${path}`,
    downloadTunnelClientScript: () => {}, updateTunnelConfig: () => {},
  },
}
globalThis.__tunnelBehaviorHarness = harness
const prefix = 'const harness = globalThis.__tunnelBehaviorHarness; const { setTimeout, clearTimeout } = harness;\n'
const { default: component } = await import(`data:text/javascript;base64,${Buffer.from(prefix + script).toString('base64')}`)
const state = component.setup({}, { expose() {} })

const initialize = mounted[0]()
assert.equal(statusCalls.length, 1)
assert.equal(configCalls.length, 1, '初始化应立即并行发起两项请求')
statusCalls[0].resolve({ online: true })
await Promise.resolve()
assert.equal(state.isRelayOnline.value, false, '配置未返回前不应挂载默认入口')
configCalls[0].resolve({ portal_path: '/custom/entry/' })
await initialize
assert.equal(state.isRelayOnline.value, true)
assert.equal(state.initializing.value, false)
assert.ok(state.gatewayUrl.value.endsWith('/gateway/custom/entry/'))
assert.equal(scheduled.length, 1)
assert.equal(scheduled[0].delay, 8000)

const poll = scheduled[0].fn()
assert.equal(statusCalls.length, 2)
assert.equal(configCalls.length, 1, '日常轮询不再重复读取配置')
assert.equal(scheduled.length, 1, '慢请求未完成时不安排下一轮')
statusCalls[1].resolve({ online: true })
await poll
assert.equal(scheduled.length, 2)

state.onIframeLoad()
assert.equal(state.refreshing.value, false)
state.portalIframe.value = { src: '' }
state.handleReloadFrame()
assert.equal(state.refreshing.value, true)
assert.ok(state.portalIframe.value.src.includes('_t='))
assert.equal(scheduled.length, 2, '刷新状态不使用固定 600 毫秒假完成计时器')
statusCalls[2].reject(new Error('测试连接错误'))
await new Promise(resolve => setImmediate(resolve))
assert.ok(state.statusError.value.includes('测试连接错误'))
assert.equal(state.isRelayOnline.value, true, '状态探测失败不卸载已打开的内网页面')
state.onIframeLoad()
assert.equal(state.refreshing.value, false)
unmounted[0]()
assert.equal(cleared.length, 1)
delete globalThis.__tunnelBehaviorHarness
console.log('智慧供热组件行为通过：初始化并行、配置完成后挂载、状态单独轮询、无重叠轮询、真实刷新状态与错误反馈。')
