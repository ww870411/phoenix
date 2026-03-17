时间：2026-03-17
主题：monthly_data_show 导入工作台规则分组选择 + 半计算公式跨口径引用支持

前置说明：
- 用户要求本轮实现功能，但不更新 configs/progress.md、frontend/README.md、backend/README.md。
- 前端构建初次在沙箱内因 esbuild spawn 限制失败，获批后重新执行 `npm run build` 并通过。

变更文件：
- backend/projects/monthly_data_show/services/extractor.py
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json（本轮保留用户当前已调整的最后一条规则内容，仅在功能验证中按当前配置使用）

实现内容：
1. 规则选择 UI 分组化
   - 后端 get_extraction_rule_options() 继续返回扁平规则列表，但新增 category_id/category_name 元信息：
     - base_cleanup / 基础清洗
     - semi_calculated / 半计算规则
     - special_adjustments / 特殊修正
   - 前端 MonthlyDataShowEntryView.vue 基于 category_id/category_name 做分组渲染。
   - “规则执行选择”弹窗支持：
     - 全选 / 全不选（全局）
     - 本组全选 / 本组全不选（组内子项）
     - 每个子规则单独勾选，默认仍为全勾选
   - 提交仍沿用 selectedExtractionRuleIds 扁平数组，不改接口协议。
2. 半计算公式支持口径标识
   - extractor.py 新增公式令牌解析：若公式中的引用写成 `口径::指标`、`口径:指标` 或 `口径：指标`，则从指定口径读取该窗口下的指标值。
   - 若公式引用未写口径，则默认取当前规则正在生成的目标口径。
   - 支持别名：`当前口径::指标`、`本口径::指标`、`self::指标`、`current::指标`。
   - 公式仍复用 indicator_config.py 的安全求值器 evaluate_formula。

验证结果：
- Python 语法检查：`python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py` 通过。
- 前端构建：`frontend npm run build` 通过。
- 后端最小功能验证：
  - 当前配置中的公式规则（用户已改为“煤折标煤量补齐”）在同口径下可正常生成目标指标。
  - 临时将最后一条规则公式改成 `="全口径::耗标煤总量"-"当前口径::耗油量"*1.4571` 后，跨口径公式可正确生成结果，transform_note 显示为 `{{全口径::耗标煤总量}}-{{当前口径::耗油量}}*1.4571→煤折标煤量`。

当前约定：
- 推荐公式写法：`="全口径::耗标煤总量"-"当前口径::耗油量"*1.4571`
- 不写口径前缀时，默认取当前目标口径同窗口值。

回滚思路：
- 前端：恢复 MonthlyDataShowEntryView.vue 的 extractionRules 扁平列表渲染。
- 后端：恢复 get_extraction_rule_options() 的无分类元信息版本，并撤回 extractor.py 中的跨口径公式解析函数与调用。