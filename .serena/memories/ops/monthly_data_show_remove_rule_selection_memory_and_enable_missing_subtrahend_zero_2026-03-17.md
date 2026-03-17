日期：2026-03-17
任务：继续处理中断任务，落实两项调整：1）移除 monthly_data_show 导入页规则勾选记忆；2）将配置文件中所有 semi_calculated_rules 的 allow_missing_subtrahend_as_zero 统一设为 true。

变更摘要：
1. backend/projects/monthly_data_show/services/extractor.py
- 移除 extraction_rule_selection_defaults 的读写与保存逻辑。
- get_extraction_rule_options() 恢复为所有子规则 enabled_default=True。
- extract_rows() 不再回写上次勾选状态。
2. frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- 恢复步骤二规则选择初始化逻辑：默认选中 flattenedExtractionRules 的全部子规则。
- 移除对后端 enabled_default 持久化默认值的依赖。
3. backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json
- 删除顶层 extraction_rule_selection_defaults 配置块。
- 为全部 semi_calculated_rules 项补充 allow_missing_subtrahend_as_zero=true。

验证证据：
- python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py 通过。
- frontend 执行 npm run build 通过。
- 模式搜索确认：
  - 前端已恢复 selectedExtractionRuleIds.value = flattenedExtractionRules.value.map((rule) => rule.id)
  - 配置文件中不再存在 extraction_rule_selection_defaults
  - semi_calculated_rules 全部存在 allow_missing_subtrahend_as_zero=true

偏差说明：
- 根 AGENTS.md 与项目 AGENTS.md 要求每轮同步更新 configs/progress.md、frontend/README.md、backend/README.md。
- 但用户在当前会话中已明确要求：除非其提出，否则不要更新那三个记录文件。
- 本轮遵从用户显式指令，未更新上述三个文件。若后续用户要求统一更新，再集中补录。

回滚思路：
- 若要恢复“记住上次勾选”，可重新引入 extraction_rule_selection_defaults 配置块及 extractor.py / MonthlyDataShowEntryView.vue 中对应读写逻辑。
- 若要恢复半计算减项缺失非零容忍，可在配置中逐条去掉 allow_missing_subtrahend_as_zero 或设回 false。