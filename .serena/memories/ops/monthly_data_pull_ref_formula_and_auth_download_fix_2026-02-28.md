时间：2026-02-28
主题：修复导表三问题（REF 诊断、累计公式保留、结果文件鉴权下载）

用户问题：
1) 香海导出全是 REF，希望有错误日志；
2) 全年累计公式丢失，希望支持公式；
3) 打包下载可用但下方文件链接报“缺少认证信息”。

改动文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) backend/projects/monthly_data_pull/api/workspace.py
3) frontend/src/projects/daily_report_25_26/services/api.js
4) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
5) configs/progress.md
6) backend/README.md
7) frontend/README.md

关键实现：
- REF 相关：源工作簿加载改为 data_only=True，避免把公式文本写入目标。
- 错误日志：执行后输出 execution_log_<timestamp>.json（行级状态、关键字段、错误信息）。
- 公式保留：累计写入时若目标累计单元格已有公式（= 开头）则不覆盖。
- 鉴权下载：结果列表改为走带 Authorization 的 fetch 下载，替代匿名 href。
- 口径统一：后端上传接口强制仅允许 xlsx/xlsm/xltx/xltm。

结果：
- 导表问题可定位；
- 累计公式不再被覆盖；
- 下方结果文件可正常下载，不再缺少认证信息。