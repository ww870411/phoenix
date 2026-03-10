时间：2026-03-10
补充需求：用户要求进一步简化 `item_rename_rules`，去掉 `scope`，仅保留 `companies`；`companies=["all"]` 表示所有允许口径适用，`companies=["北海"]` 表示仅北海适用。
实现：
1) `backend/projects/monthly_data_show/services/extractor.py`
- 默认 `ITEM_RENAME_RULES` 改为逐条：`source/target/companies`。
- `_refresh_extraction_rules()`：
  - 新格式下无 `companies` 时自动补 `['all']`；
  - 兼容旧格式：若存在 `scope=all_allowed_companies`，自动折算为 `companies=['all']`；
  - 仍兼容旧 `rename_map` 组块写法，会展开为逐条规则。
- `_resolve_item_rename_map(company)`：
  - 若规则 `companies` 含 `all`，则全口径生效；
  - 否则仅在当前子工作表标题命中 `companies` 时生效。
2) `backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json`
- 所有 22 条重命名规则已去掉 `scope`，统一改为 `companies=['all']`。
3) 文档同步：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`
验证：
- `python -m py_compile backend/projects/monthly_data_show/services/extractor.py` 通过。
- JSON 已校验：所有 `item_rename_rules` 不含 `scope`，且 `companies` 均为非空列表。
降级说明：
- Serena 不支持直接编辑 JSON/Markdown 与该类跨块改动，因此使用 `apply_patch`。
回滚：
- 恢复 `scope` 解析逻辑与 JSON 中对应字段。