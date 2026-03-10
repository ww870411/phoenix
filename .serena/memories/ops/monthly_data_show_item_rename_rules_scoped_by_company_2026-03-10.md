时间：2026-03-10
需求：扩展 monthly_data_show 抽取规则中的 `item_rename_map`，支持对特定子工作表单独配置指标更名；并将当前既有更名规则明确标记为“适用于全部允许子工作表（排除 blocked_companies）”。
实现：
1) 后端 `backend/projects/monthly_data_show/services/extractor.py`
- 新增 `ITEM_RENAME_RULES` 默认结构：
  - `scope=all_allowed_companies`
  - `companies=[]`
  - `rename_map={...}`
- `_refresh_extraction_rules()` 新增对 `item_rename_rules` 的加载与规范化，支持：
  - `all_allowed_companies`
  - `specific_companies`
- `_resolve_item_rename_map(company)`：按当前子工作表标题合并适用规则。
- `_normalize_item(..., company=...)`：执行更名时按当前子工作表应用映射。
- `extract_rows()` 与 `normalize_constant_rules()` 已传入当前 company，确保同一规则链路下更名一致。
- 兼容性：若配置文件中没有 `item_rename_rules`，仍回退使用旧 `item_rename_map`。
2) 配置 `backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json`
- 新增 `item_rename_rules`。
- 现有全部更名规则已迁移为一条 `scope=all_allowed_companies` 规则。
- 保留 `item_rename_map` 作为兼容旧配置的兜底字段。
3) 文档同步
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`
降级说明：
- Serena 不支持直接编辑 JSON/Markdown 与该类混合改动，因此按仓库规范使用 `apply_patch`。
验证：
- `python -m py_compile backend/projects/monthly_data_show/services/extractor.py` 通过。
- `monthly_data_show_extraction_rules.json` 已用 Python `json.load` 校验可解析。
回滚：
- 删除 `item_rename_rules` 相关加载与匹配逻辑，恢复 `_normalize_item` 直接读取单一 `ITEM_RENAME_MAP`；移除 JSON 中新增的 `item_rename_rules`。