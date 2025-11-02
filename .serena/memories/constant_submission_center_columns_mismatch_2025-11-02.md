时间：2025-11-02
主题：常量表提交 500 错误分析（error: "center_cn"）
触发场景：在页面 ZhuangHe_constant_Sheet 提交数据时，前端调用 /data_entry/sheets/.../submit 返回 500。
核心结论：后端常量表持久化逻辑假定 constant_data 存在列 center/center_cn 且唯一键包含 center，但 ORM 模型 backend/db/database_daily_report_25_26.py::ConstantData 未定义这两个列，导致 SQL 构造引用 stmt.excluded.center_cn 时抛错（KeyError: "center_cn"）。
证据：
- backend/api/v1/daily_report_25_26.py: 1346 左右 _persist_constant_data() 在 upsert set_ 显式引用 center_cn；唯一键注释含 (company, center, sheet_name, item, period)。
- backend/db/database_daily_report_25_26.py: ConstantData 模型缺少 center 与 center_cn 列。
- backend/sql/sample_constant_data.sql: 多处 INSERT INTO constant_data 列清单包含 center, center_cn（为 NULL），表明设计意图是存在这些列且可为空。
- configs/11.2常量提交错误.md 中报错主体：{"ok":false,"message":"处理常量表数据时发生错误","error":"center_cn"}
影响范围：
- 所有常量表提交（含/不含中心维）均可能 500。
- 与常量数据相关的查询/幂等更新策略（ON CONFLICT）基于 center 维度的唯一键不生效。
建议修复：
- 为 ConstantData 增加可空列 center(Text)/center_cn(Text)，并在数据库中添加相同列与唯一约束 (company, center, sheet_name, item, period)。
- 若某些表无中心维度，填充 center=None/center_cn=None，按现有代码逻辑幂等覆盖。
回滚思路：
- 如需回退，移除新增列和唯一约束，恢复原模型；并将 _persist_constant_data 的引用回退（移除 center/center_cn）。
补录：已在本条目记录证据与文件路径，等待后续修复实施与验证结果补充。