日期：2026-03-30
主题：daily_report_25_26 主城区边际利润与可比煤价边际利润口径修正

背景：
- 用户确认主城区口径的边际利润类指标不应继续直接汇总北海、香海、供热三个子单位利润结果，而应按统一公式重算。
- 静态排查确认 `analysis_groups_daily` 与 `analysis_groups_sum` 中主城区原逻辑透传 `base_zc` 的 `eco_marginal_profit` / `eco_comparable_marginal_profit`，同时主城区 `eco_direct_income` 的重算遗漏了内售热收入。

本轮改动：
1. 文件：`backend/sql/analysis.sql`
   - 在 `analysis_groups_daily` 与 `analysis_groups_sum` 的主城区输出段中，将 `eco_marginal_profit`、`eco_comparable_marginal_profit` 从 `base_zc` 透传排除。
   - 主城区 `eco_direct_income` 改为直接汇总子单位 `eco_direct_income`，从而包含内售热收入。
   - 新增主城区 `eco_marginal_profit` 重算公式：
     `直接收入 - 煤成本 - 外购电成本 - 购水成本 - 可计量辅材成本`
   - 新增主城区 `eco_comparable_marginal_profit` 重算公式：
     `直接收入 - 可比煤成本 - 外购电成本 - 购水成本 - 可计量辅材成本`
   - 其中 `可比煤成本 = consumption_std_coal × price_std_coal_comparable / 10000`，可比标煤单价按主城区成员单位在对应期间的常量值求和。
2. 文档同步：
   - `configs/progress.md`
   - `frontend/README.md`
   - `backend/README.md`

验证：
- 本轮未执行数据库重建、SQL 实跑或页面联调。
- 通过静态检索确认两套主城区视图段均已切换到新公式，并保留原接口结构不变。

回滚：
- 恢复 `backend/sql/analysis.sql` 中主城区视图段到原先的 `base_zc` 透传利润逻辑与旧的 `eco_direct_income` 重算方式；同步删除本次文档记录。