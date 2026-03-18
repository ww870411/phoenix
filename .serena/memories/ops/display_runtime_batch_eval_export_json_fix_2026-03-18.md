日期：2026-03-18
主题：daily_report_25_26 数据展示页批量导出 JSON/HTML 解析错误修复

背景：用户在展示页点击导出 Excel 时出现“导出失败: Unexpected token '<', "<!DOCTYPE "... is not valid JSON”。页面首次加载约 31 秒，当前优先先修导出失败。

根因：前端 DisplayRuntimeView.vue 的批量导出逻辑一度尝试直接 fetch `/app/data/数据结构_全口径展示表.json` 并调用 `.json()` 解析；当前环境该路径返回 HTML 页面而不是 JSON，因此触发 HTML/JSON 解析错误。

实施：
1. 前端不再直读配置 JSON；批量导出请求改为传 `config + sheet_key`。
2. 后端 `backend/projects/daily_report_25_26/api/legacy_full.py` 的 `runtime/spec/eval-batch` 支持顶层或 job 级 `config`，当未直接传 `spec` 时，沿用 `_locate_sheet_payload(...)` 根据 `config + sheet_key` 定位模板后再调用 `render_spec(...)`。
3. 文档同步：`configs/progress.md`、`frontend/README.md`、`backend/README.md` 已补充本次修复说明。

验证：
- `python -m py_compile backend/projects/daily_report_25_26/api/legacy_full.py` 通过。
- `frontend` 执行 `npm run build` 通过。

影响边界：
- 不改变页面数据口径，不改变 Excel 表样。
- 仅修复批量导出配置解析链路，使其与页面单次加载共用后端模板定位逻辑。

后续建议：若用户复测后导出恢复正常，但页面首开仍约 31 秒，则下一阶段直接拆解单 sheet `render_spec` 的耗时构成。