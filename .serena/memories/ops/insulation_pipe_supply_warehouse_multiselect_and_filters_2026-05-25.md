时间：2026-05-25
任务：完善 `insulation_pipe_supply_2026` 的库管员管理页面，补齐单号/车牌号筛选，并将首列“选中”改为真正可用的多选批量库管确认交互。

前置说明：
- 本轮继续在项目 `D:\编程项目\phoenix` 内工作。
- 文本与代码编辑按仓库 AGENTS 允许的降级路径使用 `apply_patch`。
- 本轮未运行自动构建或编译验证；当前环境中的命令执行器此前出现进程启动失败，因此本轮仅完成代码与文档修改。

本轮修改：
1. 后端 `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
- `get_warehouse_management_deliveries()` 新增可选过滤参数：
  - `order_no`
  - `vehicle_plate_no`
- 保持当前过滤口径：
  - `shipment_no` 精确匹配
  - `order_no` 包含匹配
  - `vehicle_plate_no` 包含匹配

2. 前端请求层 `frontend/src/projects/daily_report_25_26/services/api.js`
- `getTubeWarehouseManagementDeliveries()` 新增透传：
  - `orderNo`
  - `vehiclePlateNo`

3. 库管页 `frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`
- 库管台账筛选区新增：
  - 单号
  - 车牌号
- 台账首列从无状态“选中”按钮改为复选框。
- 新增多选状态：`selectedDeliveryIds`
- 支持：
  - 单条勾选/取消
  - 表头一键勾选当前列表中全部 `pending_warehouse` 记录
  - 右侧处置区显示：已选记录数、可批量确认数
- 批量确认逻辑：
  - 对已勾选且状态为 `pending_warehouse` 的记录逐条调用现有单条库管确认接口
  - 不新增后端批量状态推进接口，继续复用既有单条权限与状态校验

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

结论：
- 库管页现在已经具备“按单号/车牌号筛选 + 多选后批量库管确认”的实际可用闭环。
- 首列“选中”不再是无效占位交互。
