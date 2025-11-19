## 2025-12-10 数据分析区间趋势图
- 位置：frontend/src/daily_report_25_26/pages/DataAnalysisView.vue，在“区间明细（逐日）”卡片下方新增 `TrendChart` 面板，基于 `timelineGrid` 与 `previewRows` 的 timeline 数据绘制“本期/同期”双折线，并带 dataZoom。
- 通过 `timelineMetrics` + `activeTimelineMetricKeys` 管理指标芯片，默认选前两项，切换单位会刷新可选指标；Tooltip 显示单位与同比百分比。
- 新建轻量 ECharts 包装组件 `TrendChart`（本文件内定义），README/ progress.md 留痕说明仅前端改动，后端 schema 无需调整。