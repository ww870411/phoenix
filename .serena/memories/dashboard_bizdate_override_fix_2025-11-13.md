## 2025-11-13
- 任务：排查 DashBoard 日期切换失效。
- 发现：`loadDashboardData` 在每次响应后都会用 `payload.push_date` 重写 `bizDateInput`，导致用户改动被覆盖，界面表现为日期无法切换。
- 处理：仅在无显式 `showDate`（初次加载或没有手动输入）时才同步 `push_date`；保留空值兜底默认日期。修改文件：`frontend/src/daily_report_25_26/pages/DashBoard.vue`。
- 验证：代码级自检，未运行构建/测试。