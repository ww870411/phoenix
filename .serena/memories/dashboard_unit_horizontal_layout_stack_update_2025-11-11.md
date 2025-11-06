# 单耗水平布局栅格配置（2025-11-11 更新）
- 保持水平条形图三卡片同排展示（`.dashboard-grid__item--unit` = span 4），图表高度 450px。
- 公司顺序调整为“研究院→庄河环海→金普热电→北方热电→金州热电→主城区→集团汇总”；缺项自动跳过。
- 相关文档：frontend/src/daily_report_25_26/README.md 与 configs/progress.md 已更新说明。
- 回滚竖向布局时需要同时恢复 orientation、栅格跨度及排序逻辑。