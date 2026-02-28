时间：2026-02-28
背景：用户反馈 value 为 none 时 CSV 入库失败。
决策：空值标记按 NULL 入库，不转换为 0。
变更文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowEntryView.vue
3) configs/progress.md
4) backend/README.md
5) frontend/README.md
实现：
- 后端新增 NULL_VALUE_TOKENS："", none, null, nan, --, 无, 空。
- 解析 CSV value 时命中上述标记则置为 None，允许入库。
- import-csv 返回 null_value_rows 统计。
- 前端第4步成功提示展示空值入库条数。
结果：
- value 为 none/null/nan 等时可正常入库，且有明确统计反馈。