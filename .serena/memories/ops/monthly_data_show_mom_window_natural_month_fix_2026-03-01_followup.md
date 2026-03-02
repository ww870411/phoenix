时间：2026-03-01
主题：monthly_data_show 查询 26.2 无环比值修复（补充留痕）

背景：用户已导入 26.1 与 26.2，查询 26.2 未出现环比值。

根因：query-comparison 的旧环比窗口为“按天数平移”，导致自然月窗口 2026-02-01~2026-02-28 被映射为 2026-01-04~2026-01-31，排除了 2026-01-01 的月报数据。

实现：
1) backend/projects/monthly_data_show/api/workspace.py
- 新增 _resolve_mom_window(current_start, current_end)
- 自然整月时取上月整月；非整月时保留同天数平移
- query_month_data_show_comparison 改为调用该函数生成 mom_start/mom_end

2) 文档留痕
- configs/progress.md：新增“环比窗口修复”与“README 同步”条目
- backend/README.md：新增环比窗口修复说明
- frontend/README.md：新增前端联动说明（重新查询即可命中 26.1 环比）

结果：自然月查询环比正确命中上月整月数据。