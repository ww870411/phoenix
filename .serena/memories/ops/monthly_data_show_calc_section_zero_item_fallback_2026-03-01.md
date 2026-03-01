时间：2026-03-01
问题：页面显示“计算指标（0项）”。
处理：
- 文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- 默认标题改为“计算指标”
- 标题渲染增加兜底：若配置标题为空或“0项”，按当前列表动态生成“计算指标（N项）”
结论：避免默认态误导；若仍无计算指标，根因通常是后端仍运行旧代码（未返回 indicator_config）。
留痕：已同步更新 configs/progress.md、frontend/README.md、backend/README.md。