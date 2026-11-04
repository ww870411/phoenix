<template>
  <section class="point-cards" aria-label="热源信息测点卡片">
    <header class="cards-heading"><h3>实时测点</h3><span>{{ items.length }} 个采集点</span></header>
    <article v-for="(item, index) in items" :key="`${item.level1}-${item.pointName}-${index}`" class="point-card">
      <header class="point-heading">
        <span class="point-order">{{ item.order || index + 1 }}</span>
        <div><p>{{ item.level1 }} · {{ item.level2 }}</p><h4>{{ item.pointName }}</h4></div>
      </header>
      <dl class="point-metrics">
        <div v-for="metric in metrics(item)" :key="metric.label" :class="metric.tone">
          <dt>{{ metric.label }} <small>{{ metric.unit }}</small></dt><dd>{{ metric.value }}</dd>
        </div>
      </dl>
      <footer>采集时间 <time>{{ item.update_time || item.SHIJIAN || '—' }}</time></footer>
    </article>
    <p v-if="!items.length" class="cards-empty">{{ online ? '未检索到符合条件的采集点' : '数据链路未连接，暂无实时数据' }}</p>
  </section>
</template>

<script setup>
defineProps({ items: { type: Array, default: () => [] }, online: { type: Boolean, default: false } })

// 手机卡片沿用桌面各类测点的字段与单位，温压差仅在两个值都有效时计算。
function valid(value) { return value !== null && value !== undefined && String(value).trim() !== '' && Number.isFinite(Number(value)) }
function metric(label, raw, unit, digits = 1, tone = '') {
  return { label, unit, tone, value: valid(raw) ? Number(raw).toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '—' }
}
function difference(first, second) { return valid(first) && valid(second) ? Number(first) - Number(second) : null }
function metrics(item) {
  if (item.level1 === '一次网') return [
    metric('供水温度', item.f3, '℃', 1, 'warm'), metric('回水温度', item.f5, '℃', 1, 'cool'),
    metric('供回温差', difference(item.f3, item.f5), '℃'),
    metric('瞬时流量', item.f2, 'm³/h'),
    metric('供水压力', item.f1, 'MPa', 3), metric('回水压力', item.f4, 'MPa', 3),
    metric('供回压差', difference(item.f1, item.f4), 'MPa', 3), metric('瞬时热量', item.f222, 'GJ/h'),
  ]
  const result = [metric('瞬时温度', item.WENDU, '℃', 1, 'warm'), metric('瞬时压力', item.YALI, 'MPa', 3),
    metric('瞬时流量', item.LIULIANG, item.level1 === '电厂' ? 't/h' : 'm³/h'), metric('瞬时热量', item.RELIANG, 'GJ')]
  if (item.level1 === '首站') result.push(metric('当前负荷', item.FUHE, 'MW'), metric('频率', item.PINLV, 'Hz'))
  return result
}
</script>

<style scoped>
.point-cards { display: none; }
@media (max-width: 640px) {
  .point-cards { display: grid; gap: 12px; min-width: 0; }
  .cards-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 2px; }
  .cards-heading h3 { margin: 0; color: #0f172a; font-size: 16px; }
  .cards-heading span { color: #64748b; font-size: 12px; }
  .point-card { min-width: 0; padding: 16px; border: 1px solid #e2e8f0; border-radius: 14px; background: white; box-shadow: 0 3px 12px #0f172a04; }
  .point-heading { display: flex; gap: 10px; align-items: flex-start; margin-bottom: 14px; }
  .point-heading > div { min-width: 0; }
  .point-order { flex: 0 0 auto; border-radius: 8px; background: #eff6ff; color: #0369a1; padding: 5px 8px; font-size: 12px; font-variant-numeric: tabular-nums; }
  .point-heading p { margin: 0 0 5px; font-size: 11px; color: #64748b; overflow-wrap: anywhere; }
  .point-heading h4 { margin: 0; font-size: 15px; color: #0f172a; line-height: 1.5; overflow-wrap: anywhere; }
  .point-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 0; }
  .point-metrics > div { min-width: 0; background: #f8fafc; border-radius: 8px; padding: 10px; }
  dt { font-size: 11px; color: #64748b; line-height: 1.6; }
  dt small { font-size: 10px; }
  dd { margin: 4px 0 0; font-size: 19px; font-weight: 650; color: #1e293b; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
  .warm dd { color: #c2410c; }
  .cool dd { color: #0369a1; }
  footer { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 4px 12px; padding-top: 12px; margin-top: 12px; border-top: 1px solid #f1f5f9; color: #64748b; font-size: 11px; }
  .cards-empty { padding: 32px 16px; text-align: center; background: white; border-radius: 12px; color: #64748b; font-size: 13px; }
}
</style>
