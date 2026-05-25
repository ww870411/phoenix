时间：2026-05-25
任务：按用户要求先修改 `backend/sql/tube_schema_init.sql`，为 `insulation_pipe_supply_2026` 的发货表预埋“运输车次号”字段，并说明后续实现方案。

前置说明：
- 本轮涉及 SQL 文本文件编辑，Serena 不适合做该类非符号结构化修改，按仓库 AGENTS 允许的降级路径使用 `apply_patch` 完成编辑。
- 本轮未直接修改数据库实例，仅修改初始化脚本与项目文档。

本轮修改：
1. `backend/sql/tube_schema_init.sql`
- 在 `tube.tube_delivery` 表中新增字段：`shipment_no VARCHAR(64)`
- 新增字段注释：运输车次号，由系统自动生成，用于同一车次发货记录的筛选与分组展示
- 新增索引：`idx_tube_delivery_shipment_no`

2. 文档同步：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`

当前业务结论：
- `shipment_no` 中文定义统一为“运输车次号”。
- 该字段只用于筛选、分组、只读展示，不作为到货、施工接收、库管确认的唯一标识。
- 同一 `shipment_no` 下供给主体必须唯一；可包含多个换热站；确认动作仍按单条发货记录执行。

后续待落地：
- 自动生成规则
- 创建发货接口回写 `shipment_no`
- 供给页、需求页、库管页只读展示和筛选
- 历史数据兼容策略
