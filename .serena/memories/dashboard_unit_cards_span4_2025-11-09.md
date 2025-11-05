# 供暖单耗卡片宽度统一（2025-11-09）
- 背景：仪表盘中三张“供暖单耗”卡片需要在宽屏模式下保持一致的三列布局。
- 操作：在 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 的 1024px 以上栅格设置里，将 `dashboard-grid__item--unit` 的列跨度改为 4。
- 影响：热、电、水单耗卡片在宽屏下并排显示三列，视觉更整齐；图表和表格数据处理逻辑不变。
- 回滚：恢复 `dashboard-grid__item--unit` 的列跨度到修改前即可撤销。