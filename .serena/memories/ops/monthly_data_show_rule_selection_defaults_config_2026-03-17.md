时间：2026-03-17
主题：monthly_data_show 规则勾选状态写入配置文件并作为下次默认值

前置说明：
- 用户希望在配置文件中开辟一个区域，记录前端上次规则勾选结果，并在下次进入时默认恢复。
- 本轮仍未更新 configs/progress.md、frontend/README.md、backend/README.md。

变更文件：
- backend/projects/monthly_data_show/services/extractor.py
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json

实现内容：
1. 配置文件新增区块
   - 新增 `extraction_rule_selection_defaults`：
     - `selected_rule_ids`: [child_rule_id, ...]
   - 该区块独立于各规则定义，不影响用户手工维护原有规则内容。
2. 后端读写支持
   - extractor.py 新增：
     - `_resolve_extraction_rules_config_path()`
     - `_load_saved_extraction_rule_ids()`
     - `_save_extraction_rule_selection_defaults()`
   - get_extraction_rule_options() 会根据保存的 child rule id 给每个子项填充 `enabled_default`。
   - extract_rows() 在解析本次实际选中的 child rule id 后，会立即把这次选择回写进配置文件。
3. 前端默认勾选恢复
   - inspect 接口返回的每个 child 规则带 `enabled_default`。
   - MonthlyDataShowEntryView.vue 初始化 `selectedExtractionRuleIds` 时不再强制全选，而是按 `enabled_default !== false` 恢复。
4. 与本轮已有父子规则树兼容
   - 记录的是子项 id，不是父项 id。
   - 若传入旧父项 id，后端仍会先展开后执行，但保存时只保存真实子项 id。

补充修复：
- unit_normalize 子项显示 `exact_match` 时，修复了配置加载阶段丢失 exact_match 的问题。
- 修复 `_normalize_unit(unit_rules=[])` 错误回退为全量单位规则的问题。

验证：
- get_extraction_rule_options() 返回的 child 规则已带 `enabled_default`。
- 手动调用 `_save_extraction_rule_selection_defaults(['item_exclude::本月平均气温','unit_normalize::5','semi_rule_12'])` 后，配置文件中的 `extraction_rule_selection_defaults.selected_rule_ids` 正确更新。
- 再次读取 `_load_saved_extraction_rule_ids()` 可还原同一结果。
- Python 语法检查通过。
- 前端 `npm run build` 通过。

说明：
- 当前回归结束时，已将 `selected_rule_ids` 恢复为空列表，避免把临时测试选择残留到后续默认状态。