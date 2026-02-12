时间：2026-02-12
用户诉求：在mini看板上部增加下载PDF按钮。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- 工具栏新增按钮“下载PDF”；
- 新增 downloadDashboardPdf()，调用 window.print() 进入浏览器另存为PDF流程。

验证：
- frontend 执行 npm run build 成功。

结果：
- 用户可在顶部一键触发PDF导出流程。