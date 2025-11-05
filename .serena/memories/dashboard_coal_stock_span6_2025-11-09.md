# 标煤消耗与库存卡片宽度统一（2025-11-09）
- 背景：仪表盘底部“标煤消耗量对比”“煤炭库存”卡片需要在宽屏下并排展示。
- 操作：在 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 的 1024px 以上栅格设置中，将 `dashboard-grid__item--stock` 的列跨度调整为 `span 6`，与 `dashboard-grid__item--coal` 保持一致。
- 影响：底部两张卡片在宽屏模式下各占半行，布局更均衡；图表逻辑不变。
- 回滚：恢复 `dashboard-grid__item--stock` 的列跨度至原值即可。