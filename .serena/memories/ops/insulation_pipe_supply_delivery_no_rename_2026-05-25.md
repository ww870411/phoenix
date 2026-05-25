时间：2026-05-25
任务：根据用户要求，将 `tube.tube_delivery` 新增的发货单号字段命名从 `delivery_code` 统一调整为 `delivery_no`。

前置说明：
- 本轮涉及 SQL 与 Markdown 文本文件编辑，Serena 不适合做该类非符号结构化修改，按仓库 AGENTS 允许的降级路径使用 `apply_patch` 完成编辑。
- 本轮未直接修改数据库实例，仅修改初始化脚本与项目文档。

本轮修改：
1. `backend/sql/tube_schema_init.sql`
- 字段名从 `delivery_code VARCHAR(64)` 调整为 `delivery_no VARCHAR(64)`
- 字段注释同步从 `delivery_code` 改为 `delivery_no`
- 唯一索引名同步从 `uq_tube_delivery_delivery_code` 改为 `uq_tube_delivery_delivery_no`

2. 文档同步：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`

当前口径：
- 单条发货记录的正式落库单号字段统一命名为 `delivery_no`
- 运输分组字段继续命名为 `shipment_no`
