时间：2026-05-25
任务：在 `insulation_pipe_supply_2026` 子项目中梳理发货、到货确认、施工接收、库管确认流程的当前真实状态，并与 v5.2 方案/执行版文档对齐。

前置说明：
- 已激活项目 `D:\编程项目\phoenix` 并读取 Serena 手册 `initial_instructions`。
- 当前会话中未发现可调用的 `check_onboarding_performed` 工具，因此未执行该项检查。
- 本轮未修改前后端业务代码，仅按仓库 AGENTS 要求补充文档留痕：`configs/progress.md`、`frontend/README.md`、`backend/README.md`。

本轮确认的业务与实现现状：
- 供给侧已完成“同一 `shipment_no` 下批量发货”的交互与后端接口闭环。
- 单次批量提交中的多条发货记录共用一个 `shipment_no`，但每条记录仍生成独立 `order_no`。
- 到货确认、施工接收、库管确认三类动作，当前都严格按单条 `delivery_id` 处理，没有按 `shipment_no` 批量确认。
- 当前状态机保持：`pending_arrival -> pending_receive -> pending_warehouse -> completed`，撤销仅允许 `pending_arrival`。

前端对应关系：
- `SupplyManagementView.vue`：批量暂存发货明细、提交当前车次、继续已有车次、撤销发货。
- `DemandManagementView.vue`：物流确认记录查询、到货确认、施工接收；已支持 `order_no` / `shipment_no` / 型号 / 发货日期 / 到货日期筛选。
- `WarehouseManagementView.vue`：仅负责库管确认；已支持 `shipment_no` 展示与筛选，不再提供到货确认或施工接收替代入口。

后端对应关系：
- `api/workspace.py` 暴露主流程接口。
- `services/supply_management_service.py` 控制状态推进与数量校验：
  - 到货数量不能大于发货数量
  - 施工接收数量不能大于到货数量
  - 库管确认仅允许 `pending_warehouse`

当前仍待继续完善的重点：
1. 需求页、库管页虽然已能按 `shipment_no` 检索，但缺少按车次视角的汇总、差异提示与异常辅助信息。
2. 方案中定义的超时提醒、数量差异、风险提示仍未形成正式 dashboard/预警接口闭环。
3. “确认后回退”仍保持第一阶段禁止口径；若未来要开放，需单独扩展状态机与留痕规则。

证据文件：
- `configs/5.24_tube项目建设方案_v5.2_物流链管理版.md`
- `configs/5.24_tube项目完整构建流程计划_v5.2执行版.md`
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
- `backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/SupplyManagementView.vue`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/DemandManagementView.vue`
- `frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`