// 上网电量使用独立MWh轴，避免与电价、价差或负电价点数共用刻度。
export function addPlantSalesToOption(option, rows, { enabled, fields, suffix = '', include = () => true }) {
  if (!enabled) return option
  const plants = [
    { name: `北海上网电量${suffix}`, field: fields[0], color: '#0891b2' },
    { name: `香海上网电量${suffix}`, field: fields[1], color: '#8b5cf6' },
  ]
  const hasOtherRightAxis = Boolean(option.yAxis[1]?.show)
  if (hasOtherRightAxis) option.yAxis[1].position = 'right'
  const axisIndex = option.yAxis.length
  option.yAxis.push({
    type: 'value', name: '上网电量 (MWh)', position: 'right',
    offset: hasOtherRightAxis ? 66 : 0,
    nameTextStyle: { color: '#64748b' }, axisLabel: { color: '#64748b' }, splitLine: { show: false },
  })
  option.grid.right = hasOtherRightAxis ? 125 : 65
  option.legend = { show: true, top: 4, type: 'scroll', data: plants.map(p => p.name), textStyle: { color: '#64748b', fontSize: 11 } }
  const added = plants.map(plant => ({
    name: plant.name, type: 'line', yAxisIndex: axisIndex, smooth: false, connectNulls: false,
    showSymbol: false, lineStyle: { width: 2, color: plant.color }, itemStyle: { color: plant.color },
    data: rows.map(row => include(row) ? (row[plant.field] ?? null) : null),
  }))
  option.series.push(...added)
  const originalFormatter = option.tooltip.formatter
  option.tooltip.formatter = params => {
    if (!params?.length) return ''
    const base = params.filter(p => !plants.some(plant => plant.name === p.seriesName))
    let tip = originalFormatter ? originalFormatter(base.length ? base : params) :
      `${params[0].axisValueLabel ?? params[0].name ?? ''}<br/>` + base.map(p => `${p.marker ?? ''}${p.seriesName}: ${p.value ?? '暂无数据'}`).join('<br/>')
    const index = params[0].dataIndex
    for (const series of added) {
      const value = series.data[index]
      if (value != null) tip += `<div style="color:${series.itemStyle.color}">● ${series.name}: ${Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 4 })} MWh</div>`
    }
    return tip
  }
  return option
}
