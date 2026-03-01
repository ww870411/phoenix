时间：2026-03-01
需求：导入页增加按钮，点击弹窗展示每项规则处理细节。
实现：
1) backend/projects/monthly_data_show/services/extractor.py
- _apply_semicalculated_completion_rules 改为返回逐项命中明细 dict。
2) backend/projects/monthly_data_show/api/workspace.py
- extract-csv 新增响应头 X-Monthly-Rule-Details（URL编码JSON）并在 expose headers 中暴露。
3) frontend/src/projects/daily_report_25_26/services/api.js
- 解析 x-monthly-rule-details -> stats.ruleDetails。
4) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- 提取成功后显示“查看规则命中详情”按钮；
- 新增弹窗组件展示明细行：半计算各子规则命中、金普面积扣减、常量注入、提取总行数。
验证：python -m py_compile workspace.py extractor.py 通过。