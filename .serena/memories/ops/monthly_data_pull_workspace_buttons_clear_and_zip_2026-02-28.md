时间：2026-02-28
主题：monthly_data_pull 页面新增“清空目录/打包下载”按钮与后端接口
需求：
1) 清空 backend_data/projects/monthly_data_pull 下 mapping_rules/source_reports/target_templates/outputs 文件；
2) 打包下载 outputs 目录文件。

改动文件：
1) backend/projects/monthly_data_pull/api/workspace.py
2) frontend/src/projects/daily_report_25_26/services/api.js
3) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
4) configs/progress.md
5) backend/README.md
6) frontend/README.md

后端实现：
- 新增 POST /monthly-data-pull/clear-workspace
  - 清理四个工作目录中的文件；保留 .gitkeep。
- 新增 GET /monthly-data-pull/download-outputs-zip
  - 将 outputs 文件打包 zip 返回下载；若目录为空返回 404。
  - 使用临时文件并通过 BackgroundTask 响应后删除。

前端实现：
- 页面顶部新增按钮：清空目录、打包下载。
- 新增 API：
  - clearMonthlyDataPullWorkspace(projectKey)
  - downloadMonthlyDataPullOutputsZip(projectKey)
- 清空目录：二次确认后执行，成功后重置页面状态到步骤1。
- 打包下载：鉴权 fetch 获取 blob，触发浏览器下载保存（保存位置由浏览器选择）。

说明：
- 导表执行主链路不变；仅新增目录维护和批量导出能力。