# 数据填报路径统一 2025-10-22
- 时间：2025-10-22（按当前会话时间记）
- 变更：后端 `daily_report_25_26` API 与前端路由、服务、文档路径从 `/sheets` 统一调整为 `/data_entry/sheets`，同步更新 configs/logs.md 与 progress.md 记录。
- 影响文件：backend/api/v1/daily_report_25_26.py、frontend/src/router/index.js、ProjectSelectView.vue、Breadcrumbs.vue、Sheets.vue、services/api.js、frontend 与 backend README、configs/设定（填表请求）.md 等。
- 工具说明：Serena 对若干 JS/Markdown 文件缺乏符号级编辑能力，本次通过 Codex CLI `apply_patch` 降级完成替换，已在 progress.md 留痕。
- 验证：全局检索旧路径未见残留，等待下一轮联调确认接口通路。