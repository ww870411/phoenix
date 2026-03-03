时间：2026-03-03
范围：frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue；backend/services/data_analysis_ai_report.py；configs/progress.md；frontend/README.md；backend/README.md。
变更摘要：1) 管理后台“AI 设置”改为复用 AiAgentSettingsDialog（与日报查询/月报查询统一），删除后台旧内嵌表单，统一指向 shared/ai_settings.json。2) 月报报告渲染函数 _generate_monthly_report_html 进一步改为公文简报式排版（标题+元信息+章节正文+附关键同比表+核对结果），弱化日报看板感。
验证：python -m py_compile backend/services/data_analysis_ai_report.py 通过；npm run build(frontend) 通过。