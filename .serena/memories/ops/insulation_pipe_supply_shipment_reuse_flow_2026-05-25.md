时间：2026-05-25
任务：继续完成 `insulation_pipe_supply_2026` 的 `shipment_no` 复用闭环，确保单条订单号与运输车次号只在一处生成，避免重复逻辑。

前置说明：
- 本轮延续上一轮对 `order_no/shipment_no` 的接入。
- 文本文件修改继续按仓库 AGENTS 允许的降级路径使用 `apply_patch`。
- 后端诊断仍存在环境级 `fastapi/sqlalchemy` 缺失告警；与本轮逻辑无直接关系。

本轮核心设计：
- `order_no`：始终由后端按单条发货记录唯一生成，不允许复用。
- `shipment_no`：只允许两种来源
  1. 后端新建
  2. 复用一个已存在且供给主体一致的 `shipment_no`
- 前端不负责拼号，只负责表达“继续当前车次 / 新开车次”。

本轮修改：
1. 后端 `workspace.py`
- `SupplyDeliveryCreatePayload` 新增可选字段 `shipment_no`
- `create_supply_management_delivery()` 现支持：
  - 未传 `shipment_no` 时自动新建
  - 传入已有 `shipment_no` 时校验存在且供给主体一致后沿用
- 返回值新增 `shipment_reused`

2. 后端 `supply_management_service.py`
- 新增 `get_shipment_owner()`：按 `shipment_no` 查询所属供给主体
- 保留 `update_delivery_identifiers()` 作为插入后统一回写编号的唯一入口

3. 前端 `SupplyManagementView.vue`
- 发货登记区新增只读展示：订单号、运输车次号
- 新增车次控制：
  - `继续当前车次`
  - `新开车次`
- 发货记录表新增列：运输车次号
- 发货记录表新增按钮：`继续此车次`
- 提交时仅在“继续当前车次”模式下回传已有 `shipment_no`
- 提交成功后默认保持当前 `shipment_no`，便于连续录入同车次多条记录
- 继续兼容旧字段 `delivery_code = order_no`

当前结论：
- “同车次多条记录共享 `shipment_no`”的基础闭环已打通。
- 仍未支持一次性批量录入多条明细；目前是通过连续提交、沿用同一 `shipment_no` 完成。
- 用户给出的样例若要求 `shipment_no` 同时包含换热站码，会与“一个车次允许多个换热站”冲突，因此当前落地版本保持 `shipment_no` 不含换热站码。
