import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

// 直接运行组件内的导出函数，校验协议和资源清理；真实排版需浏览器验收。
const source = readFileSync(new URL('../src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue', import.meta.url), 'utf8')
function section(start, end) {
  const a = source.indexOf(start)
  const b = source.indexOf(end, a + start.length)
  assert.ok(a >= 0 && b > a, `导出函数边界缺失：${start}`)
  return source.slice(a, b)
}
const code = section('function escapeHtml(', 'function downloadCanvasAsPng(')
  + section('async function captureWorksheetToPng(', 'async function prepareExportWorkbook(')
const XLSX = { utils: {
  decode_range: () => ({ s: { r: 0, c: 0 }, e: { r: 2, c: 3 } }),
  encode_cell: ({ r, c }) => `${String.fromCharCode(65 + c)}${r + 1}`,
} }
const ws = {
  '!ref': 'A1:D3', '!cols': [{ wch: 28 }, { wch: 12 }, { wch: 12 }, { wch: 12 }],
  '!merges': [{ s: { r: 1, c: 0 }, e: { r: 1, c: 1 } }],
  A2: { t: 's', v: '长指标名称\n第二行说明' }, C2: { t: 'n', v: 12345678.9 },
  A3: { t: 's', v: '<经营单位>' },
}
function createExport(document, download, window) {
  return new Function('XLSX', 'document', 'downloadCanvasAsPng', 'window',
    `${code}; return { buildHtmlForWorksheet, captureWorksheetToPng };`)(XLSX, document, download, window)
}

test('截图 HTML 固定 1600px，保留列宽比例、合并和数字格式', () => {
  const { buildHtmlForWorksheet } = createExport({ createElement: () => ({}) }, () => {}, { innerWidth: 375 })
  const html = buildHtmlForWorksheet(ws, '日报', '2026-10-30')
  assert.match(html, /width:1600px;min-width:1600px;max-width:none/)
  assert.match(html, /table-layout:fixed/)
  const widths = [...html.matchAll(/<col style="width:([\d.]+)%;/g)].map(m => Number(m[1]))
  assert.equal(widths.length, 4)
  assert.ok(Math.abs(widths.reduce((a, b) => a + b, 0) - 100) < 0.00001)
  assert.ok(Math.abs(widths[0] / widths[1] - 28 / 12) < 0.00001)
  assert.match(html, /colspan="2"/)
  assert.match(html, /长指标名称<br\/>第二行说明/)
  assert.match(html, /white-space:nowrap;word-break:normal;[^>]*>12,345,678\.90/)
  assert.match(html, /&lt;经营单位&gt;/)
})

test('超长数值和字符串形式的数字会扩宽各自列，截图宽度随之增长', () => {
  const { buildHtmlForWorksheet } = createExport({ createElement: () => ({}) }, () => {}, { innerWidth: 375 })
  const longNumber = '1234567890'.repeat(45)
  const html = buildHtmlForWorksheet({ ...ws, C2: { t: 'n', v: 1, w: longNumber }, D3: { t: 's', v: longNumber } }, '日报', '')
  const cardWidth = Number(html.match(/table-screenshot-card" style="width:(\d+)px/)[1])
  const widths = [...html.matchAll(/<col style="width:([\d.]+)%;/g)].map(m => Number(m[1]))
  assert.ok(cardWidth > 1600)
  for (const column of [2, 3]) assert.ok((cardWidth - 60) * widths[column] / 100 >= longNumber.length * 12 * 0.8 + 21)
})

test('字符串百分比连同空格和全角百分号保持在同一行', () => {
  const { buildHtmlForWorksheet } = createExport({ createElement: () => ({}) }, () => {}, { innerWidth: 375 })
  const html = buildHtmlForWorksheet({ ...ws, C2: { t: 's', v: '-123.45\n%' }, D3: { t: 's', v: '88.12 ％' } }, '第三张表', '')
  assert.match(html, /white-space:nowrap;word-break:normal;[^>]*>-123\.45 %<\/td>/)
  assert.match(html, /white-space:nowrap;word-break:normal;[^>]*>88\.12 ％<\/td>/)
})

for (const viewport of [{ width: 375, height: 812, dpr: 3 }, { width: 1920, height: 1080, dpr: 1 }]) {
  test(`视口 ${viewport.width}px：截图尺寸独立于窗口并等待字体、清理容器`, async () => {
    const children = []
    let fontsReady = false
    const card = { scrollHeight: 1420, getBoundingClientRect: () => ({ width: 1600, height: 1419.5 }) }
    const document = {
      fonts: { ready: Promise.resolve().then(() => { fontsReady = true }) },
      body: {
        appendChild(node) { node.parentNode = this; children.push(node) },
        removeChild(node) { children.splice(children.indexOf(node), 1); node.parentNode = null },
      },
      createElement: () => ({ style: {}, querySelector: () => card }),
    }
    const downloads = []
    const { captureWorksheetToPng } = createExport(document,
      async (canvas, name) => downloads.push({ canvas, name }),
      { innerWidth: viewport.width, innerHeight: viewport.height, devicePixelRatio: viewport.dpr })
    const canvas = { width: 3200, height: 2840 }
    const render = async (element, options) => {
      assert.equal(fontsReady, true)
      assert.equal(element, card)
      assert.equal(children[0].style.width, '1600px')
      assert.deepEqual(
        [options.width, options.height, options.windowWidth, options.windowHeight, options.scale],
        [1600, 1420, 1600, 1420, 2],
      )
      return canvas
    }
    await captureWorksheetToPng(ws, '日报', '2026-10-30', render)
    assert.deepEqual(downloads, [{ canvas, name: '日报_2026-10-30.png' }])
    assert.equal(children.length, 0)
    await assert.rejects(captureWorksheetToPng(ws, '日报', '', async () => { throw new Error('模拟渲染失败') }), /模拟渲染失败/)
    assert.equal(children.length, 0)
  })
}
