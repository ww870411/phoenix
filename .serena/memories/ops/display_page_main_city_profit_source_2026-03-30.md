时间：2026-03-30
主题：daily_report_25_26 全口径展示页主城区利润指标取数来源
结论：/projects/daily_report_25_26/pages/data_show/sheets 在配置文件 数据结构_全口径展示表.json 下，Group/ZhuChengQu 命中 查询数据源.主表 的 groups 路由，不走 analysis_groups_daily/analysis_groups_sum。
证据链：
1. frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue 通过运行时 evalSpec 取数。
2. backend/services/runtime_expression.py::render_spec 解析 spec['查询数据源']['主表']，若 company 在 groups 列表中则 _per_table='groups'，否则走 default。
3. backend/services/runtime_expression.py::_fetch_metrics_from_view_batch 的 table_whitelist 为 {sum_basic_data, groups}，实际 SQL 为 SELECT ... FROM {target} WHERE company = ANY(:companies)。
4. backend_data/projects/daily_report_25_26/config/数据结构_全口径展示表.json 中三张展示表均配置了 主表:{groups:[Group,ZhuChengQu] 或 [ZhuChengQu], default:sum_basic_data}。
5. backend/sql/groups.sql 中 base_zc 来自 sum_basic_data 对 BeiHai/XiangHai/GongRe 的汇总；主城区直接透传大多数 item，仅排除比率项和 eco_direct_income，因此主城区 eco_marginal_profit / eco_comparable_marginal_profit 在该视图中仍是对子单位利润结果的求和透传。
文档同步：configs/progress.md、frontend/README.md、backend/README.md 已补充此链路说明。