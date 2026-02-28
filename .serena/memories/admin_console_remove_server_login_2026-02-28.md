时间：2026-02-28
主题：服务器管理页面取消页面内登录（改为本地权限执行）

触发：用户明确要求“服务器管理”不需要管理员账号登录，页面已运行在服务器上，权限应由命令行/系统环境控制。

变更文件清单：
1) backend/api/v1/admin_console.py
2) frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
3) frontend/src/projects/daily_report_25_26/services/api.js
4) configs/progress.md
5) backend/README.md
6) frontend/src/projects/daily_report_25_26/README.md

变更摘要：
- 后端移除 super token + SSH/SFTP 登录依赖；/admin/super/login 改为兼容占位；/admin/super/terminal/exec 改为本地 subprocess 执行；/admin/super/files* 改为本地文件系统操作。
- 前端服务器管理页删除登录区与登录态逻辑，去除 superTokenReady 门槛，页面加载时直接初始化目录树/文件列表。
- 前端 API 移除 X-Super-Admin-Token 与 loginSuperAdmin/setSuperAdminToken。
- 文档与进度记录同步更新。

风险与回滚：
- 风险：系统将直接使用后端进程权限执行命令/文件操作，需确保部署账号权限边界符合预期。
- 回滚思路：回退上述三个代码文件到本次变更前版本，可恢复 SSH 登录与 token 二次鉴权链路。