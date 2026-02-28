时间：2026-02-28
主题：异常清单行号 +1 对齐映射文件可见行号
触发：用户反馈异常清单行号比映射文件显示少1。

改动文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

实现摘要：
- 将 execute_mapping 中日志行号枚举起始从 start=1 改为 start=2；
- 使 row_index 与映射文件可见行号一致（首行为表头，数据从第2行）。

结果：
- 异常清单行号与映射文件对齐；
- 需重新执行导表后，新的 execution_log 才体现修正。