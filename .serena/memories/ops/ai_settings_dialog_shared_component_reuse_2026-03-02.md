时间：2026-03-02
范围：frontend/src/projects/daily_report_25_26/components/AiAgentSettingsDialog.vue；frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue；frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue；configs/progress.md；frontend/README.md；backend/README.md。
变更摘要：日报与月报页面的“智能体设定”由页面内重复实现改为统一复用 AiAgentSettingsDialog 组件；两页保留各自 API 调用入口（日报 project 级、月报 admin 级）；删除两页重复弹窗模板、状态函数和样式，保证内容与样式一致。
验证证据：在 frontend 目录执行 npm run build 成功，Vite 构建通过。