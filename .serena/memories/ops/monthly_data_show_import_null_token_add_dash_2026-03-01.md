时间：2026-03-01
需求：CSV 导入时将单个 '-' 也按空值处理。
实现：
- 文件：backend/projects/monthly_data_show/api/workspace.py
- 变更：NULL_VALUE_TOKENS 增加 '-'。
结果：value='-' 时按 NULL 入库并计入 null_value_rows。
验证：python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。
留痕：configs/progress.md、backend/README.md、frontend/README.md 已更新。