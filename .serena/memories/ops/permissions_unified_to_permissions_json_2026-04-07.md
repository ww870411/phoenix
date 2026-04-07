时间：2026-04-07
主题：将用户级权限覆盖从账户信息.json 迁移到 permissions.json

变更摘要：
- backend/services/auth_manager.py：取消从 账户信息.json 解析 project_actions；新增从 permissions.json.user_overrides 加载用户级项目动作覆盖，并让 update_user_project_action_override 直接写回 permissions.json。
- backend_data/shared/auth/账户信息.json：删除 beifang_admin 下的 project_actions 字段。
- backend_data/shared/auth/permissions.json：新增 user_overrides 段，迁移 beifang_admin 对 daily_report_25_26.can_submit=false 的覆盖。
- configs/progress.md、frontend/README.md、backend/README.md 已同步记录。

验证证据：
- python -m py_compile backend/services/auth_manager.py backend/api/v1/admin_console.py 通过。
- frontend 目录 npm run build 通过。
- 账户信息.json 中已无 project_actions；permissions.json 中存在 user_overrides。