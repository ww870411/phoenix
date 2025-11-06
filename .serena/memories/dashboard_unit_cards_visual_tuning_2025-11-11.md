# 数据看板单耗卡片视觉优化（2025-11-11）
- 目的：在单耗卡片改为 12 栅格后增大图表展示面积，并强化本期/同期的颜色对比。
- 实施：`frontend/src/daily_report_25_26/pages/DashBoard.vue` 内将三张单耗对比图的高度调至 360px；`useUnitConsumptionOption` 统一使用蓝色(#2563eb)代表本期、橙色(#f97316)代表同期，并放宽柱宽及网格边距。
- 降级说明：Serena 目前无法精细编辑 `.vue`，本次继续使用 `desktop-commander::read_file` + `apply_patch`；回滚时恢复该文件即还原视觉。
- 验证：刷新仪表盘确认蓝/橙对比与更高图表生效；切换窄屏模式确保响应式布局无回归。