## 2025-12-27 常量累计与气温环比修复
- 症状：在累计模式下，常量指标在网页/AI 报告中被错误地累加，导致“累计值”与单日值不一致；同时“平均气温”等温度指标在响应 `rows` 中没有 `ring_ratio` 字段，AI 报告也缺少环比信息。
- 处理：
  1. `backend/api/v1/daily_report_25_26.py` 的 legacy 流程中，常量指标的 `total_current/total_peer` 直接等于单值，不再使用逐日和；`ring_ratio` 计算改为根据指标类型分别读取上一窗口值（温度→`prev_temp_rows`，常量→`const_value_map`，其他→`prev_rows_map`），确保气温/常量都能得到环比百分比。
  2. 为 AI 报告生成 `ringCompare` 时，先写入响应再触发 `enqueue_ai_report_job`，保证 AI payload 与前端相同；`backend/services/data_analysis_ai_report.py` 也会在卡片缺少 `ring` 时用 `ringCompare.entries` 回填。
- 验证：`python -m py_compile backend/api/v1/daily_report_25_26.py`；勾选“智能报告生成”后抓包可见平均气温的 `ring_ratio` 与常量 `total_current` 均正确。
- 回滚：恢复上述文件即可。