时间：2026-03-08
问题：生产环境 admin-console 操作日志 IP 显示为 Docker/代理上一跳地址，不是真实用户来源地址。

根因：
- `backend/api/v1/admin_console.py` 的 `collect_audit_events` 仅使用 `request.client.host` 记录 `client_ip`。
- 在反向代理链路下，`request.client.host` 往往是代理地址。

修复：
1) 后端：
- 新增 `_extract_forwarded_client_ip(request)`：优先 `X-Forwarded-For`（取首个），其次 `X-Real-IP`。
- 新增 `_normalize_ip(raw_ip)`：使用 `ipaddress.ip_address` 规范化。
- 新增 `_resolve_client_ip(request)`：优先转发头，回退 `request.client.host`。
- `collect_audit_events` 改为调用 `_resolve_client_ip(request)`。

2) 前端：
- `AdminConsoleView.vue` 审计日志 IP 列兼容显示 `client_ip || ip`，兼容历史日志字段。

验证：
- `python -m py_compile backend/api/v1/admin_console.py` 通过。
- `frontend` 执行 `npm run build` 通过。

文档同步：
- `configs/progress.md`
- `frontend/README.md`
- `backend/README.md`