项目：Phoenix 在线数据填报平台
目的：统一在线数据填报、自动校验与汇总、提供分析与趋势图。
技术栈：
- 后端：FastAPI + SQLAlchemy + PostgreSQL（Tall Table：entries）
- 前端：Vue3 + Vite + RevoGrid
- 容器：Docker + Compose
结构：
- backend/（app 入口 main.py，API v1 路由聚合，项目级路由 daily_report_25_26）
- frontend/（Vue3 应用，router、pages、services 分层；daily_report_25_26 子域）
- configs/（基础配置与进度记录）
规范：
- API 前缀 `/api/v1`；核心接口 `/template`、`/submit`、`/query`；字段命名与规范文档一致。
- 项目代号规范值：`25-26daily_report`；当前实现路径：`daily_report_25_26`（存在命名差异，前端以路由参数适配）。
不确定性：
- 运行与测试命令以本地常见方式给出，后续可按实际脚手架调整。