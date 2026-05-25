时间：2026-05-25
任务：启用 `insulation_pipe_supply_2026` 中的 `abnormal_flag`，用于标识“确认到货量小于发货量”或“施工接收量小于到货量”的数量差异异常。

本轮设计：
- 不新增新的异常字段，继续复用已有 `tube.tube_delivery.abnormal_flag`。
- 状态机和异常标记职责分离：
  - `status` 继续只表达流程阶段
  - `abnormal_flag` 单独表达数量差异异常

后端修改：
- 文件：`backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py`
- `update_delivery_arrival_record()`：
  - 当 `arrived_qty < shipped_qty` 时，写入 `abnormal_flag = true`
- `update_delivery_receipt_record()`：
  - 当 `received_qty < arrived_qty` 时，写入 `abnormal_flag = true`
  - 若到货阶段已经异常，则继续保持异常标记

前端修改：
- `SupplyManagementView.vue`
  - 发货记录表新增：到货量、接收量列
  - 状态旁新增“异常”标识
- `DemandManagementView.vue`
  - 物流确认记录状态旁新增“异常”标识
- `WarehouseManagementView.vue`
  - 台账状态旁新增“异常”标识

当前业务结论：
- 若确认到货量小于发货量：
  - 状态仍推进到 `pending_receive`
  - 但会额外显示“异常”
- 若施工接收量小于到货量：
  - 状态仍推进到 `pending_warehouse`
  - 但会额外显示“异常”

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`
