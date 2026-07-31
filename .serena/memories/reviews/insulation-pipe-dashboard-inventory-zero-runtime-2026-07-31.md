# 保温管看板库存为零运行态复核

日期：2026-07-31（Asia/Hong_Kong）；只读，无源码或数据改动。

## 关键验证
- 解除权限后的当前 `get_supply_management_demand_summary` 已强制使用所有需求主体；不再依据账号可访问站点过滤。
- 前端 API 客户端当前会将 `show_date` 写入查询参数，后端当前 endpoint 也接收该参数。
- 直接在正在运行的 `phoenix_backend` 容器中调用相同汇总函数：`high_lot_1` 的 `Φ1120×13/Φ1260×16` 行返回 `total_arrived_qty=10.0`、`station_inventory_qty=10.0`，指标 `totalInv=10.0`。
- `phoenix_frontend` 将工作区 `frontend` 挂载到 `/app`；后端启动命令含 `uvicorn ... --reload`。当前代码可被运行环境读取。

## 结论
当前端拿到成功的最新汇总响应时，库存卡必显示 10，不存在剩余的后端业务公式或权限阻塞。仍显示 0 只可能是：浏览器保留了权限调整前加载得到的空 `summaryRows`，或真实浏览器请求得到 401/403/5xx 并被 `DashboardView.vue` 的 catch 静默为 0。点击页面“刷新看板数据”会再次请求；若仍为 0，必须查看该请求的 HTTP 状态和响应 rows。
