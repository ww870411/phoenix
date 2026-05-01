时间：2026-04-10
问题：monthly_data_show/query-tool 在 company=供热公司、item=蒸汽平均焓 且开启 aggregate_months 时，错误地把多个月份的蒸汽平均焓直接累计，未按供热公司口径先汇总基础指标再求值。
结论：该问题的根因是 indicator_config.json 仅支持 calculated_items，而“蒸汽平均焓”未被配置为聚合期重算项，导致主查询 SQL 在 aggregate_months 场景下把它当普通基础指标 SUM(value)。
本轮改动：
1. backend_data/projects/monthly_data_show/indicator_config.json
- 新增 aggregate_formula_overrides 配置段。
- 新增配置：name=蒸汽平均焓，companies=[供热公司]，formula=({{各热力站耗热量}} - {{低真空供暖耗热量}} - {{高温水供暖耗热量}}) * 1000 / {{供暖耗汽量}}。
2. backend/projects/monthly_data_show/services/indicator_config.py
- 新增 _normalize_aggregate_formula_overrides。
- load_indicator_runtime_config 增加 aggregate_formula_overrides、aggregate_formula_item_set、aggregate_formula_units、aggregate_formula_formulas、aggregate_formula_dependency_map、aggregate_formula_company_map 输出。
3. backend/projects/monthly_data_show/api/workspace.py
- 新增运行时全局：AGGREGATE_FORMULA_ITEM_SET / UNITS / DEPENDENCY_MAP / FORMULAS / COMPANY_MAP。
- _refresh_indicator_runtime 同步刷新上述聚合公式配置。
- _collect_required_base_items 改为支持传入 dependency_map 和 formula_item_set。
- 新增 _compute_aggregate_formula_indicator 与 _build_aggregate_formula_override_rows。
- query_month_data_show 中：
  - aggregate_months 时识别 selected_aggregate_formula_items；
  - 自动补齐聚合公式依赖项进入 query_base_items；
  - 生成 aggregate_formula_rows；
  - 命中聚合公式覆盖的基础行会在最终输出前按 company/item/period/type/date/report_month 键被替换，避免继续返回累计值。
4. 文档同步：
- configs/progress.md
- frontend/README.md
- backend/README.md
验证：
- python -m py_compile backend/projects/monthly_data_show/services/indicator_config.py 通过。
- python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。
说明：
- Serena 已激活且完成 onboarding 检查。
- 本轮文本编辑使用 apply_patch；原因是同时涉及 Python/JSON/Markdown 多文件精确补丁，且仓库规范允许使用原生文本补丁工具。