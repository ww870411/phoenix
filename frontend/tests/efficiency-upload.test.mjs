import assert from 'node:assert/strict'
import test from 'node:test'
import {
  uploadBeihaiEfficiencyReport,
  uploadXianghaiEfficiencyReport,
  uploadGongreEfficiencyReport,
} from '../src/projects/daily_report_25_26/services/api.js'

// 通过公开上传函数验证网关响应、接口路径与 multipart 请求，避免依赖内部辅助函数。
test('能效报表上传响应回归', async t => {
  const originalFetch = globalThis.fetch
  t.after(() => { globalThis.fetch = originalFetch })
  const uploaders = [
    ['beihai', uploadBeihaiEfficiencyReport],
    ['xianghai', uploadXianghaiEfficiencyReport],
    ['gongre', uploadGongreEfficiencyReport],
  ]
  const cases = [
    [413, '<html><h1>413 Request Entity Too Large</h1></html>', /HTTP 413.*client_max_body_size/],
    [502, '<html>Bad Gateway</html>', /服务暂不可用.*HTTP 502/],
    [503, '<html>Service Unavailable</html>', /服务暂不可用.*HTTP 503/],
    [504, '<html>Gateway Timeout</html>', /请求超时.*HTTP 504/],
    [200, '<html>SPA index</html>', /未返回有效 JSON.*HTTP 200/],
    [200, '', /未返回有效 JSON.*HTTP 200/],
    [200, 'null', /未返回有效 JSON.*HTTP 200/],
    [400, JSON.stringify({ ok: false, message: '报表日期不匹配' }), /报表日期不匹配.*HTTP 400/],
    [401, JSON.stringify({ detail: '登录已过期' }), /登录已过期.*HTTP 401/],
    [200, JSON.stringify({ ok: false, message: '未找到日期列' }), /未找到日期列.*HTTP 200/],
  ]
  for (const [unit, upload] of uploaders) {
    await t.test(`${unit}：成功结果与上传字段保持兼容`, async () => {
      const result = { ok: true, data: { cells: [] }, summary: { message: '解析成功' } }
      globalThis.fetch = async (url, options) => {
        assert.equal(url, `/api/v1/projects/daily_report_25_26/data_entry/${unit}/parse_efficiency_report`)
        assert.equal(options.method, 'POST')
        assert.equal(options.body.get('biz_date'), '2026-10-30')
        assert.equal(options.body.get('file').name, '能效.xlsx')
        assert.equal(options.headers['Content-Type'], undefined)
        return Response.json(result)
      }
      assert.deepEqual(await upload('daily_report_25_26', new File(['excel'], '能效.xlsx'), '2026-10-30'), result)
    })
    for (const [status, body, expected] of cases) {
      await t.test(`${unit}：${status} ${body.slice(0, 30)}`, async () => {
        globalThis.fetch = async () => new Response(body, { status })
        await assert.rejects(
          upload('daily_report_25_26', new File(['excel'], '能效.xlsx'), '2026-10-30'),
          expected,
        )
      })
    }
  }
})
