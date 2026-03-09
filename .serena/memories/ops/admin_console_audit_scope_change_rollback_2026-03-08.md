时间：2026-03-08
事件：用户确认未授权修改日志采集范围，仅希望日志相关内容在“操作日志”页面呈现。

处理：
- 回滚此前采集范围改动：
  1) frontend/src/main.js 恢复全局 initAuditTracking(...)。
  2) frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue 删除按页签启停采集逻辑。
- 文档同步：
  - configs/progress.md
  - frontend/README.md
  - backend/README.md
  均补充“更正/回滚”记录。

结果：
- 日志采集行为恢复为变更前口径。
- 操作日志页面的展示与筛选能力保留。