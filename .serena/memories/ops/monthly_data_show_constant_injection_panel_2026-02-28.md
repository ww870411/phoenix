时间：2026-02-28
主题：monthly_data_show 常量注入设定栏

用户需求：
- 增加常量注入设定栏
- 默认采用用户已提供的常量值
- 可手动修改常量值
- 可决定每条常量写入哪个源字段（本年计划/本月计划/本月实际/上年同期）

实现概览：
1) 后端 extractor
- 新增默认常量规则（发电设备容量、锅炉设备容量）
- 新增 normalize_constant_rules
- extract_rows 增加 constants_enabled + constant_rules
- 常量注入时按 (company,item,date,period,type) 覆盖或新增
2) 后端 API
- inspect 返回 constants_enabled_default 和 constant_rules
- extract-csv 支持 constants_enabled、constant_rules_json
3) 前端页面
- 步骤2新增常量注入面板与开关
- 支持逐条编辑 value、source_column
4) 前端 API
- extractMonthlyDataShowCsv 新增 constantsEnabled、constantRules 参数

留痕文件：
- configs/progress.md
- backend/README.md
- frontend/README.md