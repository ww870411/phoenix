时间：2026-02-28
主题：monthly_data_pull 新增页面异常清单区域
需求：在页面中单独展示导表异常清单。

改动文件：
1) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- 步骤3新增“异常清单”区域；
- 执行完成后自动定位并读取 execution_log_*.json；
- 展示累计对照汇总（rows_total/acc_ok/acc_mismatch/acc_skipped_formula）；
- 表格展示异常项：
  - status 为 error_*；
  - status 为 warn_formula_text_from_source；
  - acc_compare_status 为 mismatch。
- 在清空目录、重新解析映射时自动重置异常面板。

结果：
- 用户无需手工打开日志文件即可在页面查看异常行与说明。