时间：2025-10-19
变更文件：
- backend/api/v1/daily_report_25_26.py
- frontend/src/daily_report_25_26/pages/Sheets.vue
- backend/README.md
- frontend/README.md
- configs/progress.md

关键功能：
- 后端模板接口 `GET /api/v1/projects/{project_key}/sheets/{sheet_key}/template` 读取 backend_data 下的 JSON 模板，补齐当前东八区日期与上一年度同日，返回字段 `sheet_key/sheet_name/unit_name/columns/rows`。
- 模板清单接口 `GET /api/v1/projects/{project_key}/sheets` 现同时包含中文键（单位名、表名）与英文键（unit_name、sheet_name）。
- 前端 `Sheets.vue` 使用卡片列表展示表格，去除 0/0 徽标与行分隔线，保留单位卡片框体；支持新返回字段。
- README&进度文档同步更新处理规则。

验证建议：
1. 调用 `GET /api/v1/projects/daily_report_25_26/sheets/JinZhou_Sheet/template`，确认 `columns[2]`、`columns[3]` 分别为今日日期与去年同日。
2. 前端访问 `/projects/daily_report_25_26/sheets`，检查卡片展示与状态条渲染是否正常。
3. 若模板缺少列名/数据，接口返回 422，需要检查 backend_data 中对应条目。