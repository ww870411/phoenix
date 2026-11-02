import test from 'node:test'
import assert from 'node:assert/strict'
import { newspaperPdfSize } from '../src/projects/daily_report_25_26/composables/dailyBriefPdf.js'

test('长幅报纸保持宽高比，正文不被分页裁切', () => {
  const size = newspaperPdfSize(1220, 2800)
  assert.equal(size.width, 420)
  assert.equal(size.height / size.width, 2800 / 1220)
})

test('横版及极长内容均保持比例并符合 PDF 页面尺寸上限', () => {
  for (const [width, height] of [[1220, 800], [400, 20000]]) {
    const size = newspaperPdfSize(width, height)
    assert.ok(size.width <= 5000 && size.height <= 5000)
    assert.ok(Math.abs(size.width / size.height - width / height) < 1e-10)
  }
})

test('加载中或无效尺寸不生成空白 PDF', () => {
  for (const [width, height] of [[0, 800], [1220, 0], [-1, 800], [NaN, 800], [1220, Infinity]]) {
    assert.throws(() => newspaperPdfSize(width, height), /版面尺寸无效/)
  }
})
