时间：2026-03-03。
需求：AI 报告生成时增加进度展示。
实现：
1) 日报页面 frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue 新增进度区（进度条+百分比+阶段节点），基于现有 status/stage 计算进度；
2) 月报页面 frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue 同步新增进度区；
3) 月报轮询逻辑补充 aiReportStage 状态接收，并对 revision_pending/revision_content 做阶段别名映射。
验证：npm run build（frontend）通过。
文档：configs/progress.md、frontend/README.md、backend/README.md 已同步。