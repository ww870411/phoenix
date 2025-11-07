## 2025-11-15 登录状态不稳定排查
- 现象：用户在网页端频繁被提示重新登录，尤其是多标签页操作、管理员修改权限配置或后端热重启后。
- 根因：
  1. 前端 Pinia `auth` store（frontend/src/daily_report_25_26/store/auth.js）使用 `sessionStorage` 单标签缓存，会导致新标签页没有令牌而触发重新登录。
  2. 后端 `AuthManager.login()`（backend/services/auth_manager.py:272-307）调用 `_invalidate_user_sessions()`（同文件 347-353 行）强制单会话，同一账号再次登录会立即让已有会话失效。
  3. `AuthManager._ensure_loaded()`（同文件 134-164 行）在检测到账户/权限 JSON 被改动时会清空 `_sessions` 与 `_user_tokens`，而生产环境部署曾启用 `uvicorn --reload`（configs/11.5登陆问题.md 日志），文件变更或热重启都会造成所有用户掉线。
- 建议：
  1. 将 token 缓存切换到 `localStorage`，或引入 SharedWorker 广播，避免多标签重复登录。
  2. 调整后端令牌存储策略，允许每个账号保留多个 token（例如限制为 3 个并按 LRU 驱逐），同时保留手动注销能力。
  3. 生产环境关闭 `--reload`，并考虑将 `_sessions` 外置到 Redis/数据库，或者在权限文件更新时只刷新受影响账号的 token。