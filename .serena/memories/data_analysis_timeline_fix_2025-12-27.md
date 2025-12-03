## 2025-12-27 数据分析平均气温区间明细修复
- 触发：AI 报告改造后反馈累计模式仅勾选“平均气温”时区间逐日表缺少温度列，定位为 `backend/api/v1/daily_report_25_26.py` legacy 流程未为常量/温度指标生成 timeline。
- 变更：在上述文件新增 `_build_constant_timeline/_build_temperature_column_lookup/_query_temperature_timeline` 包装函数，`_execute_data_analysis_query_legacy` 在 range 模式统一为分析指标、常量、气温三类指标注入逐日数组，并保留 ring_ratio 计算；同步更新 `configs/progress.md`、`backend/README.md`、`frontend/src/daily_report_25_26/README.md` 记录结果。
- 验证：`python -m py_compile backend/api/v1/daily_report_25_26.py` 通过，手动调用 `/data_analysis/query`（仅 `aver_temp`）确认响应携带逐日温度。
- 回滚：恢复上述 Python 文件与文档即可。