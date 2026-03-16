时间：2026-03-16
主题：monthly_data_show 单位规则增加 exact_match 标志，并修复利用率计算中天数被覆盖问题

说明：
- 按用户本轮新约定，未更新 `configs/progress.md`、`frontend/README.md`、`backend/README.md`，留待任务结束前统一更新。
- `apply_patch` 在当前环境连续失败，改用 desktop-commander 精确编辑完成最小改动。

变更文件：
- backend/projects/monthly_data_show/services/extractor.py
- backend/projects/monthly_data_show/api/workspace.py
- backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json

实现：
1. 单位规则增加 `exact_match` 开关。
- 默认内置 `UNIT_NORMALIZE_RULES` 与配置文件中的 5 条现有规则均补上 `exact_match`。
- 面积相关规则保留 `exact_match=false`，允许在复合单位中替换，如 `千克标煤/米2 -> 千克标煤/平方米`。
- `千瓦时 -> 万千瓦时` 改为 `exact_match=true`，避免 `万千瓦时 -> 万万千瓦时`。
2. `_normalize_unit()` 按规则决定走精确匹配还是包含替换，移除之前针对 `千瓦时` 的硬编码特判。
3. `_normalize_value()` 同步按 `exact_match` 推导本条规则是否命中，保证单位换算与单位文本替换保持一致。
4. `_compute_calculated_indicator()` 在构造公式上下文时，跳过依赖遍历对 `天数` 的再次覆盖，修复 `天数` 被写成 0 导致利用率恒为 0 的问题。

验证：
- `python -m py_compile backend\projects\monthly_data_show\services\extractor.py backend\projects\monthly_data_show\api\workspace.py` 通过。
- 单位规则验证：
  - `_normalize_unit('万千瓦时') -> ('万千瓦时', '', '')`
  - `_normalize_unit('千瓦时') -> ('万千瓦时', '单位转换', '千瓦时→万千瓦时')`
  - `_normalize_unit('千克标煤/米2') -> ('千克标煤/平方米', '单位转换', '米2→平方米')`
- 查询验证：`北海 / 2024-01 / month / real` 下
  - `发电设备利用率 = 0.72819355`
  - `供热设备利用率 = 0.6379079`
- 额外确认：数据库中此前已导入的旧 2024 数据仍保留错误单位值，如 `发电量.unit='万万千瓦时'`；本轮修复会影响后续重新提取/导入，不会自动改写历史库中脏数据。

后续建议：
- 若要修复已入库的 2024 错误单位，需要单独做历史数据清洗或重新走步骤 3/4 导入。