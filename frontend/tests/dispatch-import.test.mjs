// 从实际页面加载导入逻辑，验证状态确认不能被普通保存或覆盖保存绕过。
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ref, computed } from 'vue'

const source = readFileSync(new URL('../src/projects/daily_report_25_26/pages/DispatchInfoView.vue', import.meta.url), 'utf8')
const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1]
  .replace(/import[\s\S]*?from\s+['"][^'"]+['"]/g, '')

function page(responses = [{ ok: true, inserted: 1, updated: 0 }]) {
  const calls = []
  const deps = {
    ref, computed, onMounted() {},
    useAuthStore: () => ({ user: {}, token: '' }),
    useRoute: () => ({ params: {}, query: {} }),
    getProjectNameById: () => '测试项目',
    alert() {},
    saveDispatchData: async (project, payload) => { calls.push({ project, payload }); return responses.shift() },
    fetchDispatchDates: async () => ({ ok: true, dates: [] }),
    queryDispatchData: async () => ({ items: [] }),
  }
  const factory = new Function('deps', `const { ${Object.keys(deps).join(', ')} } = deps;\n${script}\nreturn { extractSummary, statusResolutions, hasUnresolvedStatusConflicts, triggerSaveToDb, confirmOverwriteSave, showOverwriteModal };`)
  const view = factory(deps)
  view.extractSummary.value = { token: '测试', items: [{ biz_date: '2026-10-30', status_conflicts: [{ id: '设备A' }, { id: '设备B' }] }] }
  return { view, calls }
}

test('逐项选择完成前普通入库和覆盖入库均不发请求', async () => {
  const { view, calls } = page()
  view.statusResolutions.value = { 设备A: 'table' }
  assert.equal(view.hasUnresolvedStatusConflicts.value, true)
  await view.triggerSaveToDb()
  await view.confirmOverwriteSave()
  assert.equal(calls.length, 0)
})

test('每台设备可以独立选择表格或事件口径', async () => {
  const { view, calls } = page()
  view.statusResolutions.value = { 设备A: 'table', 设备B: 'events' }
  assert.equal(view.hasUnresolvedStatusConflicts.value, false)
  await view.triggerSaveToDb()
  assert.deepEqual(calls[0].payload.status_resolutions, { 设备A: 'table', 设备B: 'events' })
  assert.equal(calls[0].payload.overwrite, false)
})

test('已有日期的覆盖确认保留逐设备选择', async () => {
  const { view, calls } = page([{ has_conflict: true, conflict_dates: ['2026-10-30'] }, { ok: true }])
  view.statusResolutions.value = { 设备A: 'events', 设备B: 'table' }
  await view.triggerSaveToDb()
  assert.equal(view.showOverwriteModal.value, true)
  await view.confirmOverwriteSave()
  assert.equal(calls.length, 2)
  assert.equal(calls[1].payload.overwrite, true)
  assert.deepEqual(calls[1].payload.status_resolutions, calls[0].payload.status_resolutions)
})
