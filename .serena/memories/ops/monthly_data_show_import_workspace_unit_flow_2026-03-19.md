时间：2026-03-19
主题：monthly_data_show/import-workspace 页面“千瓦时 / 万千瓦时”单位转换链路梳理

前置说明：
- 已执行 serena__activate_project / serena__check_onboarding_performed。
- 本轮未修改业务代码，仅补充文档留痕：configs/progress.md、frontend/README.md、backend/README.md。
- 未发生 Serena 降级编辑；文档修改使用 apply_patch。

排查文件：
- frontend/src/router/index.js
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- frontend/src/projects/daily_report_25_26/services/api.js
- backend/projects/monthly_data_show/api/workspace.py
- backend/projects/monthly_data_show/services/extractor.py
- backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json

结论：
1. “千瓦时 -> 万千瓦时”单位转换只发生在步骤 3 `extract-csv` 提取阶段，不发生在步骤 4 `import-csv` 入库阶段。
2. 前端在步骤 1 读取规则后，默认会把全部子规则自动勾选，因此该单位转换规则默认启用。
3. 后端提取时由 `_normalize_unit()` 负责单位文本替换，由 `_normalize_value()` 负责按同一规则对数值做 `value_divisor=10000` 的同步换算。
4. 当前配置中该规则为 `exact_match=true`，因此只有原始单位严格等于 `千瓦时` 才应转换为 `万千瓦时`；若原始单位已是 `万千瓦时`，当前代码不应再命中。
5. `import_monthly_data_show_csv()` 只解析 CSV 并 upsert 入库，采用 CSV 里的最终 `unit/value`，不会再次调用单位标准化逻辑。
6. 因此：
   - 今天新提取的 CSV 若单位异常，问题在提取链路或规则选择；
   - 查询页面若暴露历史 `万万千瓦时`，更可能是旧脏数据仍在数据库中，3 月 16 日修复不会自动清洗历史数据。

补充背景：
- 2026-03-16 已有相关修复：把 `千瓦时 -> 万千瓦时` 改为 `exact_match=true`，用于避免旧逻辑下 `万千瓦时 -> 万万千瓦时` 的重复替换。