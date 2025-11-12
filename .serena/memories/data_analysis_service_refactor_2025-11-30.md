# 2025-11-30 数据分析服务抽离
- 将 `/data_analysis/schema` 与 `/data_analysis/query` 的核心代码迁移到 `backend/services/data_analysis.py`，API 端只保留 Pydantic 校验与文件读取逻辑，并通过 service 函数返回统一结果。
- `backend/api/v1/daily_report_25_26.py` 中原有的 `_query_*` 辅助函数保留为 service 别名，并新建 `_execute_data_analysis_query_legacy` 以备调试。
- Serena 无法在 4k+ 行的 API 文件中定位 `_execute_data_analysis_query` 等符号，需要降级使用 `apply_patch` 重写；若后续要回滚，可以直接恢复该文件或调用 legacy 实现。