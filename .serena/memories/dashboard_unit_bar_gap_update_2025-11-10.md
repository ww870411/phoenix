# 2025-11-10 供暖单耗柱距优化
- 触发条件：Serena 目前无法对 `.vue` 组件执行符号级写入，调整 `DashBoard.vue` 柱状图参数时降级使用 apply_patch。
- 变更文件：frontend/src/daily_report_25_26/pages/DashBoard.vue。
- 主要改动：`useUnitConsumptionOption` 中将供暖单耗卡片的柱状图 `barGap`=0%、`barCategoryGap`=65%，让本期/同期柱形贴合、单位间距增大；移除同期系列的数值标签（仅保留本期标签），并统一清理页面所有数据标签的白色背景。
- 回滚提示：若需恢复旧样式，把上述两个参数还原为 `20%` 与 `40%`，重新开启同期标签，如需恢复背景可在相关 label 对象重新加上 `backgroundColor`。
- 验证：加载数据看板，检查供暖单耗三张卡片柱形排布是否符合新间距、同期柱体无数值标签且界面整洁；同时确认其它卡片的数值标签均已无白色背景。