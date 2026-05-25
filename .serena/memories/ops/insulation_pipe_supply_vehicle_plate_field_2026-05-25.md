时间：2026-05-25
任务：在 `insulation_pipe_supply_2026` 中为发货流程新增“车牌号”字段，并贯穿供给页、需求页、库管页展示链路。

前置说明：
- 已在项目 `D:\编程项目\phoenix` 上下文下完成修改。
- 文本与代码编辑按仓库 AGENTS 允许的降级路径使用 `apply_patch`。
- 本轮尝试使用本地命令执行器运行 `py_compile` 做最小语法验证，但执行器进程启动失败（`spawn setup refresh`），因此本轮未完成自动编译验证。

本轮设计：
- 新增字段 `vehicle_plate_no`，中文定义为“车牌号”。
- 字段挂在 `tube.tube_delivery` 表上，不额外新建车次表；但业务语义按“车次级字段”处理。
- 同一 `shipment_no` 下车牌号必须一致。
- 继续已有车次时：
  1. 若该车次已登记车牌号，则自动沿用，不允许改成其他值。
  2. 若该车次尚未登记车牌号，则允许本次补录，并由后端回填整个车次。

后端修改：
- `backend/sql/tube_schema_init.sql`
  - 为 `tube.tube_delivery` 增加 `vehicle_plate_no VARCHAR(32)` 与字段注释。
- `backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py`
  - `create_delivery_record()` 增加 `vehicle_plate_no`
  - `list_delivery_records()` 返回 `vehicle_plate_no`
  - `get_shipment_owner()` 增加返回当前车次已登记的 `vehicle_plate_no`
  - 新增 `sync_shipment_vehicle_plate()`，按 `shipment_no` 回填/同步车牌号
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
  - `SupplyDeliveryCreatePayload` / `SupplyDeliveryBatchCreatePayload` 增加 `vehicle_plate_no`
  - `_resolve_shipment_no_for_create()` 增加车牌号一致性校验与解析
  - `_create_supply_delivery_entry()` 在生成/复用车次后同步车牌号
  - 单条发货与批量发货接口均已透传车牌号

前端修改：
- `SupplyManagementView.vue`
  - 发货表单新增“车牌号（选填）”输入框
  - 继续已有车次时，若已有车牌号则自动带出并锁定；若为空则允许补录
  - 发货记录表新增“车牌号”列
  - 批量提交接口已附带 `vehicle_plate_no`
- `DemandManagementView.vue`
  - 物流确认记录表新增“车牌号”列
- `WarehouseManagementView.vue`
  - 台账表新增“车牌号”列
  - 选中记录摘要新增车牌号展示

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

迁移说明：
- `tube_schema_init.sql` 只覆盖新环境初始化。
- 已存在数据库需要额外执行：
  - `ALTER TABLE tube.tube_delivery ADD COLUMN vehicle_plate_no VARCHAR(32);`

未完成项：
- 暂未把车牌号加入各页面筛选条件。
- 暂未做按车牌号聚合或风险提示。
- 本轮未完成自动编译/构建验证。
