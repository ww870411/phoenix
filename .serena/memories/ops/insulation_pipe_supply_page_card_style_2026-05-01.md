# 2026-05-01 保温管供需管理系统入口卡片样式对齐

## 背景
用户要求保温管供需管理系统的四个页面卡片仿照 `/projects/monthly_data_show/pages` 的卡片设计。

## 变更
- `frontend/src/projects/insulation_pipe_supply/pages/InsulationPipeSupplyEntryView.vue`：入口页改用与通用 `PageSelectView` 一致的结构：`card elevated page-block` 外层、`card-grid` 网格、`card elevated page-card` 卡片、`page-card-title` 与 `page-card-desc` 文案层级。
- 保留 `permissions.projects.insulation_pipe_supply.page_access` 项目级权限判断；未授权提示放入相同外层卡片容器。
- `configs/progress.md`、`frontend/README.md`、`backend/README.md` 已同步；后端无接口变更。

## 验证
- `npm run build` 通过。

## 备注
此前确认 `ww870411` 位于 `backend_data/shared/auth/账户信息.json` 的 `Global_admin` 组；如该账号仍不可见新项目，优先检查登录会话缓存是否刷新，以及后端服务是否已重新读取共享权限配置。