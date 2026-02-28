时间：2026-02-26
范围：backend/api/v1/admin_console.py；backend/requirements.txt；frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue；frontend/src/projects/daily_report_25_26/services/api.js；configs/progress.md；backend/README.md；frontend/README.md
变更摘要：
1) 服务器管理认证从应用内 super_admin 固定凭据改为 SSH 账号认证；
2) 登录接口接收 host/port/username/password，登录成功后发 token，并在会话中保存 SSH 连接元信息；
3) 命令执行改为 SSH exec_command；文件管理改为 SFTP（list/read/write/mkdir/move/delete/upload）；
4) 后端新增 paramiko 依赖；
5) 前端登录区新增主机/端口输入，登录 API 改对象入参，文案改为服务器管理员；
6) 同步更新 progress 与前后端 README 结构记录。
验证：未执行自动化构建/测试，仅完成代码级联动检查。