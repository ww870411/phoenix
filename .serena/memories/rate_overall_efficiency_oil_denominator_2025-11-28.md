时间：2025-11-28
场景：用户要求将“全厂热效率”指标的分母从单纯的 consumption_std_coal 调整为包含油耗折算量。
操作：Serena 无法直接编辑 SQL/Markdown，已使用 apply_patch 更新 backend/sql/sum_basic_data.sql 与 backend/sql/groups.sql，将分母统一改为 29.308 * (consumption_std_coal + 1.4571 * consumption_oil)，并同步记录到 backend/README.md、frontend/README.md、configs/progress.md。
验证：更新后需重新执行 SQL 视图脚本（\\i backend/sql/sum_basic_data.sql, \\i backend/sql/groups.sql），查询 rate_overall_efficiency 时即可看到新口径，若单位油耗为 0 则自动回落至旧值。