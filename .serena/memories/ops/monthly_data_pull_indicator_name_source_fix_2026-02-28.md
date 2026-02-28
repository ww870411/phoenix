时间：2026-02-28
主题：异常清单指标名称来源修正为“子公司月报表指标名称”
触发：用户反馈新增“指标名称”列仍为空。

改动文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

实现摘要：
- 后端新增 _extract_indicator_name(row)：
  - 首选读取 row['子公司月报表指标名称']；
  - 兜底支持列名空格差异匹配（去空格比对）。
- 行日志 indicator_name 改为统一调用该函数。

结果：
- execution_log 的 indicator_name 与映射字段“子公司月报表指标名称”对齐。
- 需重新执行导表生成新日志后，前端异常清单显示才会更新。