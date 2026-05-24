时间：2026-05-24
主题：根据 `configs/5.24 tube项目审计（agy）.md` 修复第 2/3/4/6/8 项问题，并在审计报告中标注处理结果。

本次处理范围：
- Bug 2：供给侧滚动三日计划量与展示日期 `show_date` 脱节
- Bug 3：库存/缺口计算未按 `show_date - 1` 截断未来到货与未来使用
- Bug 4：库管页保留到货确认、施工接收冗余接口导致越权
- Bug 6：施工接收少于到货时，损耗仍被计入可用库存
- Bug 8：异常挂起态下已确认到货数量可能被错误清零

代码修改：
1. `backend/projects/insulation_pipe_supply_2026/api/workspace.py`
- `get_supply_management_demand_summary` 已改为：
  - 用 `get_configured_show_date(payload)` 作为滚动三日计划汇总窗口起点
  - 调用 `list_arrival_aggregates(show_date.isoformat())`
  - 调用 `list_usage_totals(show_date.isoformat())`
- 删除库管页下两个冗余接口：
  - `/warehouse-management/deliveries/{delivery_id}/arrival`
  - `/warehouse-management/deliveries/{delivery_id}/receipt`

2. `backend/projects/insulation_pipe_supply_2026/services/supply_management_service.py`
- `list_arrival_aggregates(show_date)`：
  - 增加 `arrived_confirm_at < :show_date` 截断
  - 条件改为 `status <> 'cancelled' AND COALESCE(arrived_qty, 0) > 0`
  - 数量口径改为 `COALESCE(received_qty, arrived_qty, shipped_qty)`，优先使用实际接收量
- `list_usage_totals(show_date)`：
  - 增加 `WHERE usage_date < :show_date`

3. `frontend/src/projects/daily_report_25_26/services/api.js`
- 删除库管冗余 API 包装：
  - `confirmTubeWarehouseDeliveryArrival`
  - `confirmTubeWarehouseDeliveryReceipt`

4. `frontend/src/projects/insulation_pipe_supply_2026/pages/WarehouseManagementView.vue`
- 删除库管冗余导入与 dead code：
  - `arrivalForm` / `receiptForm`
  - `submitArrival()` / `submitReceipt()`
  - 对应 API import
- 页面仅保留库管闭环确认逻辑

5. 审计报告同步：
- `configs/5.24 tube项目审计（agy）.md`
  - 已在 Bug 2 / 3 / 4 / 6 / 8 条目下追加“修改情况（2026-05-24）”说明

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`

验证：
- 前端 `npm run build` 通过。
- 后端本轮未执行自动语法编译检查，主要通过定点搜索核对改动结果。