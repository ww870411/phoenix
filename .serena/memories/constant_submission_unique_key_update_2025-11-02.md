时间：2025-11-02
主题：常量数据唯一键改为 (company, item, period)
背景：用户确认不再使用 sheet_name 作为常量数据区分键，并已创建索引 `constant_data_company_idx(company,item,period)`。
代码同步：
- backend/api/v1/daily_report_25_26.py `_persist_constant_data` 的 `ON CONFLICT` 改为引用 `(company, item, period)`。
- 文档更新：`configs/progress.md` 和 `backend/README.md` 均已说明新的幂等键。
影响：
- 同一公司同一指标在不同常量表（如存在）将共享链路；当前业务确认只有一张常量表，故无额外交叉。
- 数据库需保持唯一索引 `(company, item, period)`，否则 upsert 仍无法生效。
回滚：如需恢复 sheet_name 维度，需同步调整数据库唯一约束与代码 `index_elements`。