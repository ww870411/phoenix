daily_report_25_26 前端模块说明

目标：
- 为项目代号 `daily_report_25_26` 提供隔离的前端实现；
- 目录直接位于 `src/` 下，与未来其他项目并列，不使用 `projects/` 额外层级；
- 通过本目录内的路由、状态、组件与服务实现代码与样式隔离。

子目录：
- `pages/`：业务页面（如仪表盘、表单填报页）。
- `components/`：项目私有组件。
- `store/`：Pinia 状态模块（仅在项目路由加载时使用）。
- `services/`：后端 API 访问封装（不修改 `src/api/` 全局目录）。
- `constants/`：常量（如 `project_key`、路由基路径等）。

注意：
- 后端 `project_key` 统一为 `daily_report_25_26`，与目录名一致；请使用 `constants/` 中的常量保持一致性。
- 不在此阶段修改全局路由；后续可在 `router/index.js` 中按需懒加载本模块的路由。
