# 单耗卡片水平布局试验（2025-11-11）
- 调整：`frontend/src/daily_report_25_26/pages/DashBoard.vue` 的 `useUnitConsumptionOption` 支持 `orientation` 参数，当前三张单耗卡片以水平条形图展示，并将 `.dashboard-grid__item--unit` 栅格跨度改回 `span 4`、图表高度 300px，实现单行并排效果。
- 降级说明：继续使用 `desktop-commander::read_file` + `apply_patch` 进行 `.vue` 编辑；回滚时把 orientation 恢复为纵向并重设栅格跨度即可。
- 验证：刷新仪表盘确认单耗卡片水平展示，标签/tooltip 正常显示，布局未溢出。