时间：2026-03-10
需求：
1) 删除旧 `item_rename_map`，完全使用 `item_rename_rules`；
2) 单位转换规则移入配置文件；
3) 除指标更名外，常量注入与半计算生成的指标也要在导出 CSV 中留痕；并在最后一列前新增“转换类型”列。
实现：
1) `backend/projects/monthly_data_show/services/extractor.py`
- 移除运行时对 `item_rename_map` 的依赖，默认规则仅保留 `item_rename_rules`。
- 新增 `UNIT_NORMALIZE_RULES` / `UNIT_NORMALIZE_RULES_RUNTIME`，并在 `_refresh_extraction_rules()` 中加载 `unit_normalize_rules`。
- `_normalize_item()` 现在返回 `(item, transform_type, transform_note)`，指标更名时写：
  - type=`指标更名`
  - note=`A→B`
- `_normalize_unit()` 现在返回 `(unit, transform_type, transform_note)`，命中单位规则时写：
  - type=`单位转换`
  - note=`旧单位→新单位`
- `_normalize_value(raw_unit, unit, value)` 根据 `unit_normalize_rules` 中的 `value_divisor` 执行数值换算。
- 新增导出扩展列：
  - `item_transform_type`
  - `item_transform_note`
- `extract_rows()`：原始抽取行会汇总指标更名/单位转换留痕。
- `normalize_constant_rules()`：保留常量规则自身可能触发的指标更名/单位转换留痕。
- 常量注入落行时追加：
  - type=`常量注入`
  - note=`固定值注入`
- 半计算补齐落行时追加：
  - type=`半计算`
  - note=`源表达式→目标指标`
2) `backend/projects/monthly_data_show/api/workspace.py`
- 步骤 3 导出 CSV 时固定追加 `item_transform_type`、`item_transform_note` 两列。
- 步骤 4 入库逻辑保持不变，自动忽略这两列。
3) `frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue`
- 步骤 3.1 标准表对照导出改为四列：`company,item,item_transform_type,item_transform_note`。
- 同一 `company+item` 下会聚合多个转换类型与说明（用 `；` 连接）。
4) `backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json`
- 删除旧 `item_rename_map`。
- 新增 `unit_normalize_rules`，当前包含：米2/米² 归一为平方米，千瓦时→万千瓦时并附 `value_divisor=10000`。
验证：
- `python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py` 通过。
- JSON 校验通过：`item_rename_map` 已不存在，`unit_normalize_rules` 共 5 条。
- `cd frontend && npm run build` 通过。
降级说明：
- Serena 不支持直接编辑 Vue/JSON/Markdown 与该类跨文件调整，按仓库规范使用 `apply_patch`。
回滚：
- 恢复旧 `item_rename_map` 依赖与单列 `item_transform_note` 导出；移除 `unit_normalize_rules` 与 `item_transform_type`。