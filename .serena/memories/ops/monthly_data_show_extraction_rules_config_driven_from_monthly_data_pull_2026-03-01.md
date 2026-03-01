时间：2026-03-01
需求：在 backend_data/projects/monthly_data_pull 生成提取规则配置文件，并让页面执行按配置处理。
实现：
1) 新增配置文件
- backend_data/projects/monthly_data_pull/mapping_rules/monthly_data_show_extraction_rules.json
- 内容：blocked_companies、default_source_columns、item_exclude_set、item_rename_map、default_constant_rules、semi_calculated_rules、enable_jinpu_heating_area_adjustment。
2) 提取服务改造
- 文件：backend/projects/monthly_data_show/services/extractor.py
- 新增配置加载/刷新函数，候选路径优先 /app/data/... 回退 /app/backend_data/... 和本地 backend_data。
- 在 get_company_options/get_default_constant_rules/normalize_constant_rules/extract_rows 执行前刷新配置。
- 半计算补齐改为通用规则引擎（copy/sum/subtract）按 JSON semi_calculated_rules 执行。
3) 文档留痕
- configs/progress.md
- backend/README.md
- frontend/README.md
- backend_data/projects/monthly_data_pull/README.md
验证：python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py 通过。