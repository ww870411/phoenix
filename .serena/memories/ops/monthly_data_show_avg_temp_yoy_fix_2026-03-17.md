时间：2026-03-17
主题：monthly_data_show 查询对比中平均气温缺少同期值修复

前置说明：
- 用户要求本轮修复代码，但暂不更新 configs/progress.md、frontend/README.md、backend/README.md。
- 已执行 serena__activate_project / serena__check_onboarding_performed。
- 原计划使用 apply_patch 修改文件，但连续两次因工具错误失败（windows sandbox setup refresh failed）；按仓库 AGENTS 降级到 desktop-commander edit_block 做最小编辑。

变更文件：
- backend/projects/monthly_data_show/api/workspace.py

问题根因：
- _fetch_compare_map() 对平均气温会单独从 calc_temperature_data 查询均值并写入 result_map。
- 但该分支未把平均气温 key 加入 complete_keys。
- query_month_data_show_comparison() 生成同比值时使用 `if key in yoy_complete_keys else None`，导致平均气温虽已查到同期值，仍被置空。

修复内容：
- 在平均气温 `avg_value is not None` 分支中补充 `complete_keys.add(key)`。

验证结果：
- 本地调用 query_month_data_show_comparison(QueryRequest(date_from=2024-01-01, date_to=2024-01-31, items=[平均气温], ...)) 后：
  - current_value=-2.2646505376344086
  - yoy_value=-2.466532258064516
  - yoy_rate=0.08184840063211807
- 温度专项摘要仍保持：yoy_avg_temp=-2.4665322580645164

影响范围判断：
- 仅修复平均气温在主对比表中的同比可比判定，不影响主查询结果、不影响环比/计划值逻辑、不影响温度专项对比摘要。

回滚思路：
- 删除本次新增的 `complete_keys.add(key)` 一行即可恢复旧行为。