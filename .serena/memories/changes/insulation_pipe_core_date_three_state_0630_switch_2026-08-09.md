# 保温管核心日期三态与06:30换日

- 时间：2026-08-09。
- 用户要求：新增“全部是”；“是/否”维持现有语义；“全部是”使 `show_date` 自动等于昨日；日期自动换日点改为北京时间06:30。
- 前端文件：`frontend/src/projects/insulation_pipe_supply_2026/pages/GlobalManagementView.vue`。
- 后端文件：`backend/projects/insulation_pipe_supply_2026/services/config_service.py`、`backend/projects/insulation_pipe_supply_2026/api/workspace.py`。
- 测试文件：`backend/projects/insulation_pipe_supply_2026/tests/test_config_service_dates.py`。
- 配置兼容：继续复用 `auto_update_plan_start_date`，支持 `false`、`true`、`"all"`；已有布尔配置无需迁移。
- 三态语义：`false` 三个日期手动；`true` 自动计划起点和消耗日期但 `show_date` 手动；`"all"` 三个日期均自动。
- 日期口径：北京时间06:30前业务当天为前一自然日，06:30起为当天；计划起点=业务当天，消耗日期=业务当天-1天；全部是时 `show_date=业务当天-1天`。
- 实现方式：按接口请求时动态计算，无后台定时任务、无每日配置写盘、无数据库迁移。
- 前端行为：“是/全部是”禁用计划和消耗日期，“全部是”再禁用展示日期；切换与保存时采用同一06:30规则同步日期。加载/保存回显现会覆盖三个后端动态日期，修复自动模式消耗日期显示旧值。JSON预览补回 `usage_collection_date` 并保留第三态。
- 后端保存校验：分区接口仅接受 `false`、`true` 或 `all`，其他值返回422。
- 验证：4个unittest覆盖06:29:59、06:30:00及否/是/全部是，全部通过；相关Python文件py_compile通过；Vite生产构建通过（149模块）；构建产物包含“全部是”选项；git diff --check无空白错误。
- 浏览器验收：localhost无登录会话，跳转登录页，未完成登录态视觉验证；未改线上配置或数据库。
- 文档同步：已更新 `configs/progress.md`、`frontend/README.md`、`backend/README.md`。
- 最后验证日期：2026-08-09。