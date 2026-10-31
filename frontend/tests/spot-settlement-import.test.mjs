import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { computed, ref } from 'vue'
import { previewSpotBills, confirmSpotBills, listSpotBillRecords } from '../src/projects/daily_report_25_26/services/api.js'

test('卡片电费四舍五入为整数并显示千位分隔符，缺失、零和负数正确区分', () => {
  const page = readFileSync(new URL('../src/projects/daily_report_25_26/pages/SpotElectricityView.vue', import.meta.url), 'utf8')
  const helpers = page.match(/const feeNumberFormatter =[\s\S]*?\n}\nfunction formatNum[\s\S]*?\n}/)[0]
  const format = new Function(`${helpers}; return formatPlantMetric`)()
  assert.equal(format(1234567.5, '元'), '1,234,568 元')
  assert.equal(format(-1234.5, '元'), '-1,235 元')
  assert.equal(format(0, '元'), '0 元')
  assert.equal(format(-0.3, '元'), '0 元')
  assert.equal(format(null, '元'), '暂无数据')
  assert.equal(format(123.456, 'MWh'), '123.46 MWh')
  assert.equal(format(123.456, '元/MWh'), '123.46 元/MWh')
})

test('平均现货电价差异率显示正负号和两位小数，零基准保持不可计算', () => {
  const page = readFileSync(new URL('../src/projects/daily_report_25_26/pages/SpotElectricityView.vue', import.meta.url), 'utf8')
  const helpers = page.match(/const spotPriceRateFormatter =[\s\S]*?\n}/)[0]
  const format = new Function(`${helpers}; return formatSpotPriceRate`)()
  assert.equal(format(12.345), '+12.35%')
  assert.equal(format(-3.456), '-3.46%')
  assert.equal(format(-0.001), '0.00%')
  assert.equal(format(null), '—')
})

test('日账单入口仅超级管理员可见，提交权限和管理控制台权限不能替代角色', () => {
  const page = readFileSync(new URL('../src/projects/daily_report_25_26/pages/SpotElectricityView.vue', import.meta.url), 'utf8')
  const declaration = page.match(/^const canImportBills = .*$/m)[0]
  const visible = auth => new Function('computed', 'auth', `${declaration}; return canImportBills.value`)(computed, auth)
  assert.equal(visible({ user: { group: 'Global_admin' } }), true)
  assert.equal(visible({ user: { group: 'unit_admin' }, canSubmitFor: () => true, canAccessAdminConsole: true }), false)
  assert.equal(visible({ user: { group: 'project_admin' }, canSubmitFor: () => true }), false)
  assert.equal(visible({ user: null }), false)
})

test('真实API封装：multipart上传、确认token及原始明细分页参数', async t => {
  const original = globalThis.fetch
  t.after(() => { globalThis.fetch = original })
  const requests = []
  globalThis.fetch = async (url, options) => { requests.push({ url, options }); return Response.json({ ok: true, token: 'preview-token' }) }
  const files = [new File(['a'], '甲.xlsx'), new File(['b'], '乙.xlsx')]
  await previewSpotBills('daily_report_25_26', files)
  assert.equal(requests[0].options.body.getAll('files').length, 2)
  assert.equal(requests[0].options.headers['Content-Type'], undefined)
  assert.match(requests[0].url, /spot_electricity\/bills\/preview$/)
  await confirmSpotBills('daily_report_25_26', 'preview-token')
  assert.deepEqual(JSON.parse(requests[1].options.body), { token: 'preview-token', overwrite: false })
  await listSpotBillRecords('daily_report_25_26', { importId: 'id', recordType: 'daily_total', offset: 100 })
  assert.doesNotMatch(requests[2].url, /record_type=/)
  assert.match(requests[2].url, /offset=100/)
  globalThis.fetch = async () => Response.json({ detail: '时段不完整' }, { status: 422 })
  await assert.rejects(previewSpotBills('daily_report_25_26', files), /时段不完整/)
})

const source = readFileSync(new URL('../src/projects/daily_report_25_26/components/SpotSettlementImport.vue', import.meta.url), 'utf8')
  .match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*$/gm, '')
function component(overrides = {}) {
  const calls = []
  const deps = {
    ref, defineProps: () => ({ projectKey: 'daily_report_25_26' }), defineEmits: () => () => {},
    previewSpotBills: async (_p, files) => { calls.push(['preview', files]); return { ok: true, token: 'token', files: [] } },
    confirmSpotBills: async (_p, token) => { calls.push(['confirm', token]); return { ok: true, inserted: 7469, imported: [{}, {}], skipped: [] } },
    ...overrides,
  }
  const state = new Function('deps', `const { ${Object.keys(deps).join(',')} }=deps; ${source}; return { files, previewData, error, message, busy, chooseFiles, preview, confirm, cellValue };`)(deps)
  return { state, calls }
}

test('先预览再确认，重新选文件会丢弃旧token，成功后清理预览', async () => {
  const { state, calls } = component()
  await state.confirm()
  assert.equal(calls.length, 0)
  state.chooseFiles({ target: { files: ['甲.xlsx', '乙.xlsx'] } })
  await state.preview()
  assert.equal(state.previewData.value.token, 'token')
  state.chooseFiles({ target: { files: ['丙.xlsx'] } })
  assert.equal(state.previewData.value, null)
  await state.preview()
  await state.confirm()
  assert.deepEqual(calls.at(-1), ['confirm', 'token'])
  assert.match(state.message.value, /写入\/更新 7469 个15分钟时点/)
  assert.equal(state.previewData.value, null)
})

test('确认失败保留token供幂等重试，不报告入库成功', async () => {
  const { state } = component({ confirmSpotBills: async () => { throw Error('事务失败') } })
  await state.preview()
  await state.confirm()
  assert.equal(state.previewData.value.token, 'token')
  assert.match(state.error.value, /事务失败/)
  assert.equal(state.message.value, '')
  assert.equal(state.busy.value, false)
})

test('已有数据先展示冲突，第二次明确点击才发送覆盖参数', async () => {
  const sent = []
  const { state } = component({ confirmSpotBills: async (_p, _token, overwrite) => {
    sent.push(overwrite)
    return overwrite ? { ok: true, inserted: 96, imported: [{}], skipped: [] }
      : { ok: false, needs_overwrite: true, conflicts: ['该电厂同日已有数据'] }
  } })
  await state.preview()
  await state.confirm()
  assert.deepEqual(sent, [false])
  assert.match(state.error.value, /同日已有数据/)
  assert.equal(state.message.value, '')
  assert.equal(state.previewData.value.token, 'token')
  await state.confirm()
  assert.deepEqual(sent, [false, true])
  assert.match(state.message.value, /96 个15分钟时点/)
})

test('预览合计的零值和空白保持区分', () => {
  const { state } = component()
  assert.equal(state.cellValue(0), '0')
  assert.equal(state.cellValue(null), '空白')
  assert.equal(state.cellValue(undefined), '空白')
})
