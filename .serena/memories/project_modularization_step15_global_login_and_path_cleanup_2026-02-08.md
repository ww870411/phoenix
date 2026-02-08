# 2026-02-08 项目模块化第15步：全局登录页归位与路径口径清理

## 背景
用户确认继续修复“未归位/标准不统一”项中的：
1) 登录页全局化；
2) 注释/README 路径口径统一；
并要求删除历史文件 DashBoard888.vue。

## 本次变更
1. 前端登录页归位到全局壳层
- 文件移动：`frontend/src/daily_report_25_26/pages/LoginView.vue` -> `frontend/src/pages/LoginView.vue`
- 路由更新：`frontend/src/router/index.js` 中 `/login` 改为 `../pages/LoginView.vue`
- 新文件内部依赖修正：
  - `../daily_report_25_26/styles/theme.css`
  - `../daily_report_25_26/store/auth`

2. 清理历史冗余页面
- 删除：`frontend/src/daily_report_25_26/pages/DashBoard888.vue`

3. 后端路径口径统一（仅注释/文档）
- 更新：`backend/services/auth_manager.py`
- 更新：`backend/services/dashboard_cache.py`
- 更新：`backend/services/dashboard_expression.py`
- 更新：`backend/services/data_analysis_ai_report.py`
- 更新：`backend/README.md` 的 AI 设置存储路径说明

4. 文档同步
- 更新：`frontend/README.md`（补充全局壳层页面目录与 Login 归位）
- 更新：`frontend/src/daily_report_25_26/README.md`（移除 DashBoard888 文案）
- 更新：`configs/progress.md`（新增第15步记录）

## 验证结果
- `frontend/src/pages/` 已包含 `LoginView.vue` 与 `ProjectSelectView.vue`
- `frontend/src/daily_report_25_26/pages/` 已不含 `LoginView.vue` 与 `DashBoard888.vue`
- 代码中已无 `DashBoard888` 引用
- `/login` 路由已指向 `../pages/LoginView.vue`

## 风险与回滚
- 风险：登录页移动后若相对路径遗漏可能导致构建失败；本次已修正并核对。
- 回滚：可将 `LoginView.vue` 移回原目录并恢复路由路径；若需要恢复历史页面，可从版本历史还原 `DashBoard888.vue`。