# insulation_pipe_supply_2026 当前逻辑审计记录

时间：2026-05-28
范围：tube 子项目后端 API/service、前端 Dashboard/需求/供应/库管页面、项目记录文档。

## 输入来源
- 用户要求对当前 tube 项目做全面细致审计，特别关注多个逻辑作用在同一个业务或功能上造成的隐患。
- 本轮为只读审计为主，除同步审计记录到 `configs/progress.md`、`frontend/README.md`、`backend/README.md` 外，未修改业务代码。

## 主要发现
1. 高风险：`backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py` 的全局管理员编辑入口 `super_update_delivery_record` 可绕过到货、接收、入库状态机校验，直接修改状态、数量、异常标记等字段，可能产生 `received_qty > arrived_qty`、无确认时间戳但状态已推进、非法状态值等不一致数据。
2. 中高风险：库存与缺口口径分散。供应汇总中 `station_inventory_qty = total_arrived_qty - total_usage_qty` 未归零；需求矩阵中相同概念会 `max(..., 0)`；Dashboard 前端又派生硬缺口，存在同一业务不同口径。
3. 中风险：硬缺口和 SSR/KPI 指标主要由 `DashboardView.vue` 前端计算，后端未提供统一业务字段，未来净缺口/在途扣减规则变化时容易漂移。
4. 中风险：物流状态标签、状态样式和动作规则在后端 options、SupplyManagementView、WarehouseManagementView、DemandManagementView 等多处重复维护，已有文案差异，后续可能造成按钮权限或状态展示错配。
5. 中风险：`list_arrival_aggregates` 输出 `total_arrived_qty` 时使用 `COALESCE(received_qty, arrived_qty, shipped_qty)`，字段名像“总到货量”，实际更接近“可用入账量兜底”，会影响库存、UCR 等指标解释。

## 已同步文档
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

## 建议修复顺序
1. 先收口全局管理员物流编辑入口：复用状态机校验或集中状态不变量校验。
2. 再集中库存、净缺口、硬缺口计算：后端统一返回字段，前端仅展示。
3. 最后统一前端物流状态字典/动作元数据，并补充回归用例。