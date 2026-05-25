时间：2026-05-25
任务：根据用户要求，在 `backend/sql/tube_schema_init.sql` 中为 `insulation_pipe_supply_2026` 的发货表补齐正式落库的发货单号字段，并保留运输车次号字段。

前置说明：
- 本轮涉及 SQL 文本文件编辑，Serena 不适合做该类非符号结构化修改，按仓库 AGENTS 允许的降级路径使用 `apply_patch` 完成编辑。
- 本轮未直接修改数据库实例，仅修改初始化脚本与项目文档。

本轮修改：
1. `backend/sql/tube_schema_init.sql`
- 在 `tube.tube_delivery` 表中新增字段：`delivery_code VARCHAR(64)`
- 保留上一轮新增字段：`shipment_no VARCHAR(64)`
- 新增字段注释：
  - `delivery_code`：发货单号，由系统生成并落库，用于单条发货记录的展示、检索与统计
  - `shipment_no`：运输车次号，由系统自动生成，用于同一车次发货记录的筛选与分组展示
- 新增索引：
  - `uq_tube_delivery_delivery_code`
  - `idx_tube_delivery_shipment_no`

2. 文档同步：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`

当前业务结论：
- `delivery_code` 与 `shipment_no` 均应落库，均由系统自动生成。
- `delivery_code` 对应单条发货记录；`shipment_no` 对应运输分组维度。
- 确认动作仍按单条发货记录执行，不按 `shipment_no` 统一改状态。
