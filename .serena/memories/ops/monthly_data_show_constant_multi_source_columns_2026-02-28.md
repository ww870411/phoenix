时间：2026-02-28
主题：monthly_data_show 常量注入写入口径支持多选

用户反馈：常量指标的源字段应该可以多选。

实现：
1) 后端 extractor
- source_column -> source_columns(list)
- normalize_constant_rules 兼容旧字段并统一为列表
- 注入逻辑按每个 source_column 生成对应 date/period/type 行
2) 前端页面
- 常量设定表的“写入源字段”改为复选组
- 每条常量可独立勾选多个口径
3) 数据传输
- constant_rules_json 现在携带 source_columns 数组

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md