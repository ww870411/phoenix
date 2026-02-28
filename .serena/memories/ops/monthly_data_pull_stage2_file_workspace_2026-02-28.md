时间：2026-02-28
主题：monthly_data_pull 第二阶段 - 文件工作台

本轮目标：让新项目页面具备最小可操作能力（上传与查看四类默认目录文件）。

后端改动：
- 文件：backend/projects/monthly_data_pull/api/workspace.py
- 新增接口：
  1) GET /api/v1/projects/monthly_data_pull/monthly-data-pull/files?bucket=...
  2) POST /api/v1/projects/monthly_data_pull/monthly-data-pull/files/upload?bucket=...
- bucket 支持：mapping_rules/source_reports/target_templates/outputs
- 机制：
  - 非法 bucket 返回 422
  - 上传时文件名安全清洗
  - 重名时自动追加时间戳后缀
  - 列表返回 name/size_bytes/updated_at

前端改动：
- 文件：frontend/src/projects/daily_report_25_26/services/api.js
  - 新增 listMonthlyDataPullFiles / uploadMonthlyDataPullFiles
- 文件：frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
  - 新增“文件工作台”区域
  - 每个目录支持：选择文件、多文件上传、刷新列表、错误提示
  - 展示文件基本元数据

文档留痕：
- configs/progress.md 新增本轮记录
- backend/README.md、frontend/README.md 同步结构状态

结果：
- monthly_data_pull 项目可在线完成每月导表输入文件准备（映射/源表/目标）。
- 下一步可直接进入“映射解析 + 预检 + 执行任务”实现。