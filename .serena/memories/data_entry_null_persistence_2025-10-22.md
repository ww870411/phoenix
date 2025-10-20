# 数据填报空值落库 2025-10-22
- 时间：2025-10-22
- 变更：_flatten_records 不再忽略 None/空字符串，统一转换为 "0"，由 _persist_daily_basic 删除后重插写入数据库，以保证空值填报也可追溯。
- 影响文件：backend/api/v1/daily_report_25_26.py（_flatten_records），backend/README.md（文档说明）。
- 验证：代码层面确认；待实际填报调试验证数据库 value=0。