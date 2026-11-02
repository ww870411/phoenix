/** 按当前纸张尺寸导出单页长幅报纸，不按 A4 切断正文和双栏。 */
export function newspaperPdfSize(width, height) {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error('简报版面尺寸无效，请等待页面加载完成。')
  }
  // 标准报纸宽度 420mm；极长内容同比缩放，避免超过 PDF 的页面尺寸上限。
  const pageWidth = Math.min(420, 5000 * width / height)
  return { width: pageWidth, height: pageWidth * height / width }
}

export async function exportDailyBriefPdf(sheet, { date, theme, isCurrent = () => true }) {
  const [{ toCanvas }, { jsPDF }] = await Promise.all([
    import('html-to-image'), import('jspdf'),
  ])
  await document.fonts.ready
  const width = Math.ceil(sheet.getBoundingClientRect().width)
  const height = Math.ceil(Math.max(sheet.scrollHeight, sheet.getBoundingClientRect().height))
  const size = newspaperPdfSize(width, height)
  // 使用浏览器自身的 CSS 渲染保留网格、字体和主题；限制像素总量，兼顾清晰度与内存。
  const pixelRatio = Math.min(2, 16000 / Math.max(width, height), Math.sqrt(24000000 / (width * height)))
  let canvas
  try {
    canvas = await toCanvas(sheet, {
      width, height, pixelRatio,
      backgroundColor: getComputedStyle(sheet).backgroundColor,
      filter: node => !node.hasAttribute?.('data-pdf-ignore'),
    })
    if (!isCurrent()) throw new Error('简报日期或内容已变化，请在页面加载完成后重新导出。')
    const pdf = new jsPDF({
      orientation: size.width > size.height ? 'landscape' : 'portrait',
      unit: 'mm', format: [size.width, size.height], compress: true,
    })
    pdf.setProperties({ title: `每日简报 ${date}`, subject: `集团生产经营简报 · ${theme}` })
    pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, size.width, size.height, undefined, 'FAST')
    await pdf.save(`每日简报_${date}_${theme}.pdf`, { returnPromise: true })
  } finally {
    // 及时释放大画布占用，连续导出不同主题时不累积内存。
    if (canvas) { canvas.width = 0; canvas.height = 0 }
  }
}
