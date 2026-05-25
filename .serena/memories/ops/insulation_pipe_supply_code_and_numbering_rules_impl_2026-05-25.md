时间：2026-05-25
任务：为 `insulation_pipe_supply_2026` 增加供给主体/换热站 `code` 标识，并接入 `order_no` / `shipment_no` 编号规则。

前置说明：
- 本轮涉及 JSON、Markdown 与 Python 文本文件编辑；SQL/配置/文档部分按仓库 AGENTS 允许的降级路径使用 `apply_patch` 完成。
- 已用 Serena 符号与搜索工具确认改动位置；`supply_management_service.py` 符号概览已识别到新函数 `update_delivery_identifiers`、`build_order_no`、`build_shipment_no`。
- 诊断工具中仍存在环境级 `fastapi/sqlalchemy` 缺失告警；另有部分历史类型告警与本轮无关。由于 LSP 缓存/环境原因，`workspace.py` 仍回报新导入符号未知，但文本与符号搜索均已确认函数存在。

本轮修改：
1. `backend_data/projects/insulation_pipe_supply_2026/tube_config.json`
- 供给主体新增 `code`：`supplier_a -> SA`、`supplier_b -> SB`
- 换热站新增 `code`：`station_a -> A`、`station_b -> B`、`station_c -> C`、`station_d -> D`

2. `backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py`
- `list_delivery_records` 增加读取 `order_no`、`shipment_no`
- `create_delivery_record` 增加入库参数 `order_no`、`shipment_no`
- 新增 `update_delivery_identifiers()`：先插入拿到 `id`，再回写两个编号
- 新增 `build_order_no()`：`O{供给主体code}-{换热站code}-{yyMMdd}-{序号}`
- 新增 `build_shipment_no()`：`S{供给主体code}-{yyMMdd}-{序号}`
- 保留 `build_delivery_code()` 兼容旧显示字段

3. `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
- 新增 `_build_station_code_map()`、`_build_supply_entity_code_map()`
- `_decorate_delivery_rows()` 现会补齐 `order_no`、`shipment_no`，并令 `delivery_code = order_no`
- `create_supply_management_delivery()` 现为新记录生成 `order_no/shipment_no`，并通过 `update_delivery_identifiers()` 回写数据库
- 创建接口返回新增：`order_no`、`shipment_no`，同时保留 `delivery_code` 兼容现有前端

4. 文档同步：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`

关键业务判断：
- 用户样例中若让 `shipment_no` 同时带换热站码，会与“同一车次允许覆盖多个换热站”的要求冲突，因此本轮落地规则中 `shipment_no` 不含换热站码。
- 当前已完成的是编号规则与字段回写基础能力；尚未完成真正“同车次多条记录共享同一 `shipment_no`”的批量发货交互闭环，后续仍需补前端或批量接口复用逻辑。
