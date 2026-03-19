时间：2026-03-19
主题：monthly_data_show 导入工作台修复“原始单位已是万千瓦时却仍被除以10000”

前置说明：
- 已执行 serena__activate_project / serena__check_onboarding_performed。
- `apply_patch` 在当前 Windows sandbox 下执行失败（setup refresh failed），因此本轮改用 Serena 符号编辑 + desktop-commander 最小替换完成修改。
- 已同步文档：configs/progress.md、frontend/README.md、backend/README.md。

变更文件：
- backend/projects/monthly_data_show/services/extractor.py
- configs/progress.md
- frontend/README.md
- backend/README.md

问题现象：
- 原始单位为 `千瓦时` 的记录会正确转成 `万千瓦时`，数值除以 10000。
- 但原始单位已经是 `万千瓦时` 的记录，单位文本不变，数值仍被错误除以 10000。

根因：
- `_normalize_value()` 旧逻辑只判断“按某条规则推导后的单位名是否等于当前标准化单位”，没有要求这条规则必须真实命中原始单位。
- 对规则 `千瓦时 -> 万千瓦时, exact_match=true, value_divisor=10000` 来说：
  - `raw_unit='万千瓦时'` 时，`normalized_by_rule` 仍等于 `万千瓦时`；
  - 因此会误满足 `normalized_by_rule == unit`，从而错误执行除以 10000。

修复：
1. `_normalize_value()` 新增 `unit_rules` 参数，并引入 `matched` 标志。
2. 只有在规则真实命中原始单位时，才允许执行 `value_divisor` 换算。
3. `extract_rows()` 调用 `_normalize_value()` 时改为传入 `active_unit_rules`，保证单位文本标准化与数值换算共享同一套已选规则。

验证：
- `python -m py_compile backend/projects/monthly_data_show/services/extractor.py` 通过。
- 本地样例：
  - `千瓦时 / 10000 -> 万千瓦时 / 1.0`
  - `万千瓦时 / 10000 -> 万千瓦时 / 10000.0`
  - `千克标煤/米2 / 10000 -> 千克标煤/平方米 / 10000.0`

结果：
- 只有原始单位确实是 `千瓦时` 时，值才会被缩放；
- 原始单位已是 `万千瓦时` 的记录不再误缩放。