# 保温管全局看板库存为零只读定位

日期：2026-07-31（Asia/Hong_Kong）；未修改源码或业务数据。

## 当前实证
- `tube_config.json` 的 `show_date` 是 2026-07-31。
- 数据库 `tube.tube_delivery` 当前有 1 条记录：`high_lot_1` / `Φ1120×13/Φ1260×16`，状态 `pending_receive`，发货/到货均为 10 米，`arrived_confirm_at` 为 2026-07-31；2026-07-31 前无使用和损耗记录。
- 按 `list_arrival_aggregates` 的 CASE，`pending_receive` 使用 `COALESCE(arrived_qty, shipped_qty)`，这条记录应入账 10 米；汇总库存公式为到货减使用减损耗，因此有权限的汇总 API 应返回 10 米库存。

## 定位
- 前端 KPI 只是对 `summaryRows[*].station_inventory_qty` 求和；不是前端计算或物流状态阻塞。
- 后端汇总在生成 rows 前按 `resolve_accessible_section_1_ids` 过滤。`tube_warehouse_keeper` 不在全局放行角色中，且 `warehouse_keepers` 配置不参与该函数的站点授权推导；以仓管账号访问会得到空 rows，前端自然显示 0。
- 另一确定路径是 `/supply-management/demand-summary` 请求失败或令牌过期：`DashboardView.vue` 仅 console.error，保留空 `summaryRows` 并显示 0；匿名 API 访问实际返回 401。
- 页面无自动刷新汇总数据的机制；若在 10 米到货确认前已打开，看板可一直保持旧的 0，直至手动刷新/重新进入。

## 后续验证
用当前登录账号在浏览器网络面板查看 demand-summary：若 HTTP 200，检查 rows 是否有 `high_lot_1`；若 401/403/500，则该错误正被页面伪装成 0。
