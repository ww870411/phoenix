# 2025-11-10 供暖单耗柱距优化
- 触发条件：Serena 当前无法对 `.vue` 组件执行符号级写入，调整 `DashBoard.vue` 柱状图参数时降级使用 apply_patch。
- 变更文件：frontend/src/daily_report_25_26/pages/DashBoard.vue。
- 主要改动：供暖单耗、标煤消耗卡片维持 `barGap`=0%、`barCategoryGap`=65%，本期标签双行显示本期/同期；煤炭库存卡片移除合计虚线折线并用 0 半径散点保留合计标签，同时引入 `formatWithThousands`，对煤炭库存图表的标签、坐标轴和表格列统一启用千位分隔显示。
- 回滚提示：若需恢复旧样式，将 `barGap` 与 `barCategoryGap` 恢复到 20%/40%，重新启用同期标签、折线及 `toFixed` 格式化即可。
- 验证：加载数据看板，确认供暖单耗与标煤消耗卡片标签双行显示无重叠，煤炭库存堆叠柱顶部显示加千分位的合计值、表格列也带千分位，图表不再出现虚线折线。