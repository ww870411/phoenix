时间：2026-03-16
主题：monthly_data_show 2024 月报导入后单位异常与设备利用率为 0 的根因定位

前置校验：
- serena__activate_project：已激活 D:\编程项目\phoenix
- serena__check_onboarding_performed：已完成
- 本轮无 Serena 降级编辑受阻；代码未修改，仅更新文档留痕。

排查文件：
- backend/projects/monthly_data_show/services/extractor.py
- backend/projects/monthly_data_show/api/workspace.py
- backend/projects/monthly_data_show/services/indicator_config.py
- backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json
- backend_data/projects/monthly_data_show/indicator_config.json
- configs/progress.md
- frontend/README.md
- backend/README.md

结论：
1. 单位“万万千瓦时”根因：`extractor.py` 中 `_normalize_unit()` 对 `unit_normalize_rules` 做字符串包含替换；配置含 `千瓦时 -> 万千瓦时`。当原始单位已经是 `万千瓦时` 时，会再次把其中的“千瓦时”替换掉，得到“万万千瓦时”。
2. `发电设备利用率`、`供热设备利用率` 为查询时计算指标，不是导入即存储的原始指标。`extract_rows()` 对 `calculated_item_set` 中的指标直接 `continue`，不会入库。
3. 查询阶段 `workspace.py` 依赖 `indicator_config.json` 中公式实时计算利用率；其中分母依赖 `发电设备容量`、`锅炉设备容量` 等基础指标。
4. 当前 `monthly_data_show_extraction_rules.json` 里的容量常量仅对 `source_columns=["本月实际"]` 注入，导致查询其他口径（如本月累计等）时容量缺失，公式按 0 参与运算，利用率返回 0。
5. 历史表即便自带利用率原值，现有设计也不会保留，而是统一在查询时重算，因此 2024 历史数据更容易暴露口径覆盖不足问题。

文档同步：
- configs/progress.md：新增 2026-03-16 排查记录
- frontend/README.md：新增 2026-03-16 排查同步
- backend/README.md：新增 2026-03-16 排查同步

后续修复建议：
- 收紧单位归一规则，避免对已标准单位重复替换。
- 为容量常量补齐所有需要参与利用率计算的口径，或调整利用率计算逻辑统一回落到 `本月实际` 容量基数。