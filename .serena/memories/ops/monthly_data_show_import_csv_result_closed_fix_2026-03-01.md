时间：2026-03-01
问题：第四步入库报错 This result object does not return rows. It has been closed automatically.
根因：import-csv 中 executemany + RETURNING 在当前驱动下无法直接 fetchall 结果。
修复：
- 文件：backend/projects/monthly_data_show/api/workspace.py
- 方案：改为逐行执行 UPSERT 并读取 scalar_one_or_none() 返回标志，累加 inserted_rows/updated_rows；提交事务。
验证：python -m py_compile backend/projects/monthly_data_show/api/workspace.py 通过。
留痕：configs/progress.md、backend/README.md、frontend/README.md 已更新。