时间：2026-03-10
需求：步骤 3 导出的 CSV 末尾增加一个字段，用于记录指标名在抽取规则下是如何形成的；若通过规则将 A 转成 B，则记录为 `A→B`，否则留空。该字段需在步骤 3.1 标准表对照中保留，但步骤 4 入库不写数据库。
实现：
1) `backend/projects/monthly_data_show/services/extractor.py`
- 新增 `EXTRA_EXPORT_FIELDS = ('item_transform_note',)`。
- `_normalize_item(...)` 返回值扩展为 `(normalized, changed, transform_note)`。
- 当命中指标更名规则时，`transform_note` 写为 `原指标→标准指标`；未命中则为空串。
- `extract_rows()` 生成基础抽取行时写入 `item_transform_note`；常量注入行固定写空。
- `filter_fields()` 无论用户字段选择如何，都会把 `item_transform_note` 追加到导出字段末尾。
2) `backend/projects/monthly_data_show/api/workspace.py`
- `extract_monthly_data_show_csv()` 写 CSV 表头时同步追加 `item_transform_note`。
- 步骤 4 入库逻辑无需改表结构，因 `_parse_import_csv_rows()` 只读取既有必填字段，会自动忽略该扩展列。
3) `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
- 步骤 3.1 的标准表对照导出改为三列：`company,item,item_transform_note`。
- 对同一 `company+item` 聚合多个说明时，用 `；` 连接。
4) 文档同步
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`
验证：
- `python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py` 通过。
- `cd frontend && npm run build` 通过。
降级说明：
- Serena 不支持直接编辑 Vue/Markdown 与该类跨文件调整，按仓库规范使用 `apply_patch`。
回滚：
- 删除 `item_transform_note` 扩展字段、恢复 `_normalize_item` 返回结构，并移除 3.1 对该字段的导出处理。