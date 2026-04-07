时间：2026-04-07
主题：admin-console 日报提交权限面板增加折叠与一键全部开启/关闭

变更文件：
- frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现摘要：
1. 提交权限用户列表默认折叠，新增 submitPermissionCollapsed 状态。
2. 面板头部新增“展开列表/折叠列表”按钮，减少后台页面空间占用。
3. 新增 submitPermissionBulkPending 状态与 setAllSubmitPermissions 方法。
4. 头部新增“全部开启”“全部关闭”按钮。
5. 批量操作未新增后端接口，前端顺序复用现有 setAdminProjectSubmitPermission 单用户接口完成批量切换。

结果：
- 账号较多时页面默认更紧凑。
- 管理员可快速批量开关所有普通账号的日报提交权限。

验证说明：
- 未执行构建；仅做模板片段级修改与结构自检。