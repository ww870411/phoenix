时间：2026-03-01
需求：导入页可手动勾选执行哪些规则（默认全选），执行后显示实际命中。
实现：
1) backend/projects/monthly_data_show/services/extractor.py
- 新增 get_extraction_rule_options()，输出规则清单（item_exclude、item_rename、semi规则、jinpu_area_adjust）；
- extract_rows 增加 selected_rule_ids 参数，按规则子集执行；
- _normalize_item 支持可选重命名并统计 rename 命中；
- 指标剔除支持可开关并统计 exclude 命中；
- 半计算规则按规则ID执行并汇总命中；
- 统计补充 selected_rule_ids/item_exclude_hits/item_rename_hits。
2) backend/projects/monthly_data_show/api/workspace.py
- inspect 响应新增 extraction_rules；
- extract-csv 新增 Form 参数 extraction_rule_ids 并传入 extract_rows；
- rule_details 增补 selected_rule_ids/item_exclude_hits/item_rename_hits。
3) frontend/src/projects/daily_report_25_26/services/api.js
- extractMonthlyDataShowCsv 新增 extractionRuleIds 参数并传 extraction_rule_ids。
4) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- 新增“规则执行选择”面板（默认全选）；
- 提取按钮未选规则时禁用；
- 详情弹窗显示本次选中规则与实际命中细节。
验证：python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py 通过。