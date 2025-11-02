时间：2025-11-02
主题：常量提交 500（缺失唯一约束）
现象：移除 center/center_cn 后，再次提交 ZhuangHe_constant_Sheet，后端抛出 `psycopg2.errors.InvalidColumnReference there is no unique or exclusion constraint matching the ON CONFLICT specification`。
证据：configs/11.2常量提交错误.md 最新记录。
原因：数据库表 constant_data 尚未创建唯一约束/索引 (company, sheet_name, item, period)，导致后端 ON CONFLICT 无匹配目标。
处理建议：执行
```
ALTER TABLE constant_data DROP CONSTRAINT IF EXISTS constant_data_unique;
CREATE UNIQUE INDEX IF NOT EXISTS uq_constant_comp_sheet_item_period ON constant_data (company, sheet_name, item, period);
```
如需命名为约束，可使用 `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE (...)`。
影响：约束缺失前，常量数据可能重复；修复后幂等覆盖生效。