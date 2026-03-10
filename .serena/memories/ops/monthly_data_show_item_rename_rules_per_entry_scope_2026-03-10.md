时间：2026-03-10
补充需求：用户要求 `item_rename_map` 的作用范围不是规则组级，而是“每一条重命名单独带标志”。
实现调整：
1) `backend/projects/monthly_data_show/services/extractor.py`
- `ITEM_RENAME_RULES` 默认结构从组级 `rename_map` 改为逐条规则：
  - `source`
  - `target`
  - `scope`
  - `companies`
- `_refresh_extraction_rules()`：
  - 优先解析逐条规则格式；
  - 同时兼容旧的组级 `rename_map` 写法，启动时会自动展开为逐条规则；
  - 旧 `item_rename_map` 仍可作为兜底来源。
- `_resolve_item_rename_map(company)` 改为逐条匹配当前子工作表并生成最终映射。
2) `backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json`
- `item_rename_rules` 已改成逐条配置；
- 当前 22 条更名规则均显式写为：`source + target + scope=all_allowed_companies + companies=[]`。
3) 文档同步：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`
验证：
- `python -m py_compile backend/projects/monthly_data_show/services/extractor.py` 通过。
- JSON 已加载校验，`item_rename_rules` 条数为 22。
降级说明：
- Serena 不支持直接编辑 JSON/Markdown 与该类跨块调整，故使用 `apply_patch`。
回滚：
- 恢复 `ITEM_RENAME_RULES` 为组级 `rename_map` 结构，并将 JSON 中 `item_rename_rules` 回退为单个组规则。