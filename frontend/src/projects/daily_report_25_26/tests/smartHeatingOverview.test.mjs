// 本地执行：node src/projects/daily_report_25_26/tests/smartHeatingOverview.test.mjs
// 使用 HAR 样本做服务端渲染验证，不向运行中的平台注入录制数据。
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createSSRApp } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { parse, compileScript } from '@vue/compiler-sfc'
import { OVERVIEW_GROUPS } from '../constants/smartHeatingOverview.js'

const componentUrl = new URL('../components/SmartHeatingOverview.vue', import.meta.url)
const source = await readFile(componentUrl, 'utf8')
const { descriptor } = parse(source)
let compiled = compileScript(descriptor, { id: 'overview-test', inlineTemplate: true }).content
compiled = compiled.replaceAll("from 'vue'", `from '${import.meta.resolve('vue')}'`)
  .replaceAll('from "vue"', `from '${import.meta.resolve('vue')}'`)
  .replace("from '../constants/smartHeatingOverview'", `from '${new URL('../constants/smartHeatingOverview.js', componentUrl).href}'`)
const { default: component } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
const har = JSON.parse(await readFile(new URL('../../../../../configs/192.168.1.206(工况一览).har', import.meta.url), 'utf8'))
const entry = har.log.entries.find(item => item.request.url.endsWith('/gk_get_data/'))
const data = JSON.parse(entry.response.content.text)
const now = Date.now()
const props = { data, collectedEpoch: now / 1000, now, online: true }
assert.deepEqual(OVERVIEW_GROUPS.map(group => group.rows.length), [28, 18, 11, 25])
for (const group of OVERVIEW_GROUPS) {
  for (const row of group.rows) {
    assert.ok(data[row.dictName]?.[row.sourceName], `HAR 中缺少 ${row.sourceName}`)
  }
}
const live = await renderToString(createSSRApp(component, props))
assert.equal((live.match(/<th scope="row">/g) || []).length, 82)
assert.equal((live.match(/class="overview-column"/g) || []).length, 3, '分为左中右三列')
const sections = [...live.matchAll(/<section id="heating-group-(\d)"[^>]*>([\s\S]*?)<\/section>/g)]
assert.deepEqual(sections.map(section => Number(section[1])), [0, 1, 2, 3], '电厂、首站、一网、换热站及商户保持阅读顺序')
const expectedBreaks = [[10, 22, 25], [], [5], [5, 11, 15, 19, 23]]
for (const section of sections) {
  const starts = [...section[2].matchAll(/<tr\b[^>]*class="section-break"[^>]*><td class="row-order">(\d+)<\/td>/g)].map(match => Number(match[1]))
  assert.deepEqual(starts, expectedBreaks[Number(section[1])], `分区 ${section[1]} 的分隔位置`)
}
assert.ok(!live.includes('<details'), '采集信息不折叠')
assert.ok(live.includes('3,196.3'), '独立混水汇总流量必须显示')
assert.ok(live.includes('工况数据已接入'))
assert.equal((live.match(/2026-11-04 10:47:05/g) || []).length, 1, '源采集时间仅统一显示一处，不能使用中继当前时间')
assert.match(live, /<td\b[^>]*>0<\/td>/, '零值必须显示为零')
assert.match(live, /<td\b[^>]*>—<\/td>/, '缺失数值应显示占位符')
const expired = await renderToString(createSSRApp(component, { ...props, collectedEpoch: now / 1000 - 181 }))
assert.ok(expired.includes('采集已超时'))
assert.ok(!expired.includes('3,196.3'), '超时数据必须隐藏')
assert.ok(!expired.includes('2026-11-04 10:47:05'), '超时后不应显示旧的采集时间')
const offline = await renderToString(createSSRApp(component, { ...props, online: false }))
assert.ok(!offline.includes('3,196.3'), '断线数据必须隐藏')
const legacy = await renderToString(createSSRApp(component, { ...props, data: null, collectedEpoch: null }))
assert.ok(legacy.includes('新版客户端'))
console.log('通过：82 项 HAR 测点匹配、四分区渲染、混水汇总、零值/空值、超时/断线隐藏及旧客户端兼容。')
