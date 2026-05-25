时间：2026-05-25
任务：继续推进 `insulation_pipe_supply_2026`，实现批量发货闭环，并让全局管理页可维护供给主体/换热站 `code`。

前置说明：
- 本轮延续 `order_no/shipment_no` 规则收口工作。
- 文本文件编辑继续按仓库 AGENTS 允许的降级路径使用 `apply_patch`。
- 未运行完整前后端构建；Serena/Pyright 仍报告环境级 `fastapi/sqlalchemy` 缺失告警，以及少量与本轮无关的历史类型告警。

本轮核心设计：
- 单条发货与批量发货统一复用一套后端创建辅助逻辑 `_create_supply_delivery_entry()`。
- `order_no` 始终后端唯一生成；`shipment_no` 只能“新建”或“沿用已有车次”。
- 前端供给页不再通过多次单条提交模拟批量，而是统一走批量接口 `/supply-management/deliveries/batch`。

本轮修改：
1. 后端 `workspace.py`
- 新增 `SupplyDeliveryBatchItemInput` / `SupplyDeliveryBatchCreatePayload`
- 新增 `_resolve_shipment_no_for_create()`：统一处理车次新建/复用
- 新增 `_create_supply_delivery_entry()`：单条与批量共用的发货创建逻辑
- 新增接口：`POST /supply-management/deliveries/batch`
- `_serialize_station_options()`、`_serialize_supply_entity_options()`、`_serialize_all_supply_entity_options()` 统一输出 `code`

2. 后端 `supply_management_service.py`
- 新增 `get_shipment_owner()`：校验 `shipment_no` 所属供给主体
- 保留 `update_delivery_identifiers()` 为唯一编号回写入口

3. 前端 `SupplyManagementView.vue`
- 改用 `createTubeSupplyManagementDeliveryBatch()`
- 发货登记区新增“加入本车次”与“提交当前车次”
- 新增“待提交明细”表格，可先累积多条明细后统一提交
- 继续保留只读车次控制：继续当前车次 / 新开车次 / 继续此车次
- 发货记录表新增“运输车次号”列

4. 前端 `api.js`
- 新增 `createTubeSupplyManagementDeliveryBatch()`

5. 全局管理页 `GlobalManagementView.vue`
- 供给主体区块新增“主体编码”列，对应 `item.code`
- 换热站区块新增“站点编码”列，对应 `item.code`
- `buildSectionPayload()` 与新增行默认值同步包含 `code`

6. 文档同步：
- `configs/progress.md`
- `backend/README.md`
- `frontend/README.md`

当前状态：
- 已具备“一个车次下多条发货明细一次提交、共享同一 `shipment_no`”的主闭环。
- 全局管理页已具备维护 `code` 的能力，避免只靠手改 `tube_config.json`。

剩余未做：
- 需求页 / 库管页尚未增加 `shipment_no` 展示与筛选
- 暂未支持对“待提交明细”做更复杂的编辑排序或整批撤销
