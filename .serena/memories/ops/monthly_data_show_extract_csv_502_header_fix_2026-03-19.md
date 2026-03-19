时间：2026-03-19
主题：monthly_data_show/import-workspace 生产环境提取 CSV 返回 Cloudflare 502 的根因修复

前置说明：
- 已执行 Serena activate_project/check_onboarding。
- 原计划使用 apply_patch 编辑，但两次均因 Windows sandbox setup refresh failed 无法执行；按仓库 AGENTS 允许的降级矩阵，改用 Desktop Commander edit_block 完成结构化编辑。

问题现象：
- 开发环境上传月报并提取 CSV 正常。
- 生产环境在 `http(s)://platform.smartview.top/.../monthly_data_show/import-workspace` 提取 CSV 时，前端收到 Cloudflare `502 Bad Gateway` HTML 页面。

根因判断：
- 前端 `extractMonthlyDataShowCsv()` 调用 `/api/v1/projects/monthly_data_show/monthly-data-show/extract-csv` 本身无路径问题。
- 后端 `backend/projects/monthly_data_show/api/workspace.py` 的 `extract_monthly_data_show_csv()` 会把完整规则详情 JSON（含 `semi_calculated_details`、`selected_rule_ids` 等）编码后塞进响应头 `X-Monthly-Rule-Details`。
- 开发环境直连/Vite 代理不易暴露该问题；生产环境经过 Nginx/Cloudflare，更容易因 upstream/header 过大返回 502。

代码改动：
1. backend/projects/monthly_data_show/api/workspace.py
- 删除 `X-Monthly-Rule-Details` 大响应头。
- 改为仅返回小型统计头：
  - `X-Monthly-Semi-Calculated-Completed`
  - `X-Monthly-Jinpu-Heating-Area-Adjusted`
  - `X-Monthly-Item-Exclude-Hits`
  - `X-Monthly-Item-Rename-Hits`
  - `X-Monthly-Constants-Injected`
  - `X-Monthly-Extracted-Total-Rows`

2. frontend/src/projects/daily_report_25_26/services/api.js
- 提取 CSV 接口改为读取上述小型统计头。
- 不再解析 `x-monthly-rule-details`。

3. frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
- “规则命中详情”改为使用后端小型统计值 + 前端当前已选规则摘要本地组装。
- 保留核心汇总统计，但不再展示服务端逐项半计算明细。

4. 文档同步
- configs/progress.md
- frontend/README.md
- backend/README.md

验证：
- `python -m py_compile backend/projects/monthly_data_show/api/workspace.py` 通过。
- `frontend npm run build` 通过。

影响与后续建议：
- 生产提取 CSV 的响应头体积显著缩小，规避网关 502 风险。
- 若未来必须展示完整规则命中明细，应新增独立 JSON 接口或改为文件/响应体承载，不能继续塞入响应头。