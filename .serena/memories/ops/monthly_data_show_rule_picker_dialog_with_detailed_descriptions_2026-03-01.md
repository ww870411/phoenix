时间：2026-03-01
需求：规则执行选择模块改为弹窗方式，并列出具体规则说明。
实现：
1) backend/projects/monthly_data_show/services/extractor.py
- get_extraction_rule_options 增强 description：
  - 基础规则（剔除/重命名）给出明确示例；
  - 半计算规则自动描述口径、目标指标、表达式、单位。
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- 规则选择面板改为“打开规则列表”按钮；
- 新增规则弹窗 showRulePickerDialog：
  - 逐条显示规则名+描述+复选框；
  - 支持全选/全不选/完成；
- 主面板显示已选数量和选中规则摘要。
验证：python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py 通过。