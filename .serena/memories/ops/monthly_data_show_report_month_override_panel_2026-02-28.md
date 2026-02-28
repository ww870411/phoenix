时间：2026-02-28
需求：在步骤2最上方增加“报告月份设定”，程序按文件名自动识别年月，但允许用户修改。
变更文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
2) frontend/src/projects/daily_report_25_26/services/api.js
3) backend/projects/monthly_data_show/api/workspace.py
4) backend/projects/monthly_data_show/services/extractor.py
5) configs/progress.md
6) backend/README.md
7) frontend/README.md
实现摘要：
- 前端新增步骤2顶部设定栏（年份/月输入 + YYYY-MM-01 预览），inspect 后自动填入推断值。
- 前端提取时新增 report_year/report_month 参数提交。
- 后端 inspect 返回 inferred_report_year/inferred_report_month/inferred_report_month_date。
- 后端 extract-csv 接收并校验 report_year/report_month。
- extractor 在解析文件名基础上支持覆盖年月，统一作用于 date/period/type 和 report_month 字段。
结果：
- 用户可在提取前明确控制来源月份，满足“自动识别+人工修正”流程。