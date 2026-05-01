时间：2026-04-10
最终方案：不再使用临时 aggregate_formula_overrides，改为将 monthly_data_show 的 calculated_items 正式升级为支持公司口径限制。

问题背景：
- 用户确认“蒸汽平均焓”在单月查询时也可以直接按公式计算，不必引用基础表中的原始值。
- 因此更合理的方案是把“蒸汽平均焓”并入正式 calculated_items，而不是只做多月聚合重算。

本轮最终改动：
1. backend_data/projects/monthly_data_show/indicator_config.json
- 删除临时 aggregate_formula_overrides 配置段。
- 为现有全部 calculated_items 显式补充 companies: ["all"]。
- 在 calculated_items 末尾新增：
  - name: 蒸汽平均焓
  - unit: 千焦/千克
  - formula: ({{各热力站耗热量}} - {{低真空供暖耗热量}} - {{高温水供暖耗热量}}) * 1000 / {{供暖耗汽量}}
  - companies: ["供热公司"]
- calculated_section.title 从 19项 改为 20项。

2. backend/projects/monthly_data_show/services/indicator_config.py
- _normalize_calculated_items 新增 companies 解析；若未配置则默认 ["all"]。
- load_indicator_runtime_config 新增 calculated_item_company_map。
- 前端下发的 calculated_items 载荷现在会包含 companies 字段。

3. backend/projects/monthly_data_show/api/workspace.py
- 新增全局运行时映射 CALCULATED_ITEM_COMPANY_MAP。
- _refresh_indicator_runtime 同步刷新公司范围映射。
- _build_calculated_rows 在生成每条计算指标结果时，按公司范围判断是否生效：
  - 若配置含 all，则对全部公司生效；
  - 否则仅对 companies 命中的公司生效。
- 因为蒸汽平均焓已进入 calculated_items，查询主链路会自动补齐其依赖基础指标，并在单月、逐月、多月聚合时统一走公式计算逻辑。

结果：
- calculated_items 现在支持“按公司控制公式生效范围”。
- 蒸汽平均焓已成为正式计算指标：
  - 对供热公司：单月、逐月、多月聚合都按公式算；
  - 对其他公司：不会误套该公式。

验证：
- 已确认代码中不存在 AGGREGATE_FORMULA / aggregate_formula_overrides 残留引用（rg 搜索为空）。
- python -m py_compile backend/projects/monthly_data_show/services/indicator_config.py 通过。
- python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。

文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md