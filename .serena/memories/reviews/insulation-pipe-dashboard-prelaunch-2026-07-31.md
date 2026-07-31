# 保温管全局看板上线前只读审查

日期：2026-07-31（Asia/Hong_Kong）
范围：`/projects/insulation_pipe_supply_2026/pages/dashboard`，未修改源码。

## 已验证
- 路由映射至 `DashboardView.vue`；本机页面 URL 返回 HTTP 200。
- 前端生产构建 `npm run build` 通过。
- 匿名请求汇总 API 返回 401，认证拦截生效；未持有业务用户令牌，未进行真实数据交互验证。

## 关键风险
1. `DashboardView.vue` 的汇总/发货/气象请求失败仅 `console.error`，页面依旧用空数组或 0 渲染，可能把数据故障伪装为“供需平稳”。
2. 健康总评及多处指标提示是固定“极佳/成功”文案，和实时 KPI（硬缺口、SSR、OTD 等）脱钩。
3. 首次加载同时请求无 show_date 气象和配置；配置到达后再请求 show_date 气象，旧请求若后返回可覆盖正确日期结果。
4. 后端汇总 API 的 OTD SQL 未按 session 可访问需求主体过滤，但 rows 已过滤，指标与明细授权口径不一致。
5. 前端从后台切回时仅刷新配置摘要，不刷新汇总/发货/气象，所谓实时看板可长期陈旧。

## 主要证据
- `frontend/src/projects/insulation_pipe_supply_2026/pages/DashboardView.vue`：`loadDashboardData`、`fetchWeatherData`、`onMounted`、健康卡片模板。
- `backend/projects/insulation_pipe_supply_2026/api/workspace.py`：`get_supply_management_demand_summary` 及 OTD 查询。
