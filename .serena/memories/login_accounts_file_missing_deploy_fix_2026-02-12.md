时间：2026-02-12
问题：服务器容器部署后登录报错 {"detail":"账户信息文件缺失"}。
定位：backend/services/auth_manager.py::_load_accounts 在 resolve_accounts_path 返回路径不存在时抛错。
修复：
1) backend/services/project_data_paths.py
- resolve_accounts_path 增加候选：
  /app/data/shared/auth/账户信息.json
  /app/data/shared/auth/accounts.json
  /app/data/shared/账户信息.json
  /app/data/auth/账户信息.json
  /app/data/账户信息.json
  /app/data/accounts.json
- resolve_permissions_path 增加候选：
  /app/data/shared/auth/permissions.json
  /app/data/auth/permissions.json
  /app/data/shared/permissions.json
  /app/data/permissions.json
2) backend/services/auth_manager.py
- 账户/权限文件缺失报错包含解析后的绝对路径，便于线上排障。
验证：python -m py_compile backend/services/project_data_paths.py backend/services/auth_manager.py 通过。