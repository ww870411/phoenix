# 保温管需求主体 section_1 命名统一

时间：2026-07-31

- 后端 API 的需求主体选项集合由 `stations` 统一为 `section_1s`；响应包装由 `station` 统一为 `section_1`；库存字段由 `station_inventory_qty` 统一为 `section_1_inventory_qty`。
- 看板 KPI 的需求主体计数键统一为 `submitted_section_1_count`、`active_section_1_count`、`safe_section_1_count`。
- 前端需求、供给、库管、看板、历史查询的局部状态/请求参数已移除 `station`，对外字段保持 `section_1_*`；共享配置的管理模式使用 `section_1`。
- SQL 初始化脚本中的需求主体索引名称由 station 改为 section_1；数据库实际业务列原本已使用 `section_1_id`。
- 验证：`npm run build` 通过；运行中后端需求汇总返回 `section_1_inventory_qty=10.0` 与 `totalInv=10.0`，需求选项返回 `section_1s` 而不返回 `stations`。
- 文档：已同步 configs/progress.md、frontend/README.md、backend/README.md。
