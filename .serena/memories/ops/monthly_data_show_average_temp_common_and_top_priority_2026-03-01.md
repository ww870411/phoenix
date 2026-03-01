时间戳：2026-03-01
任务：将“平均气温”指标口径固定为 common，并在查询结果中置顶显示。

变更文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) configs/progress.md
3) backend/README.md
4) frontend/README.md

实现摘要：
- 新增常量 AVERAGE_TEMPERATURE_COMPANY = "common"。
- 平均气温行生成逻辑调整：
  - _build_average_temperature_rows(...) 仅生成 company=common，不再按所选实际口径复制。
  - _fetch_compare_map(...) 的平均气温对比行键和值均固定为 company=common。
- 排序逻辑调整：
  - _merge_and_sort_rows(...) 新增平均气温优先排序前缀。
  - _sort_comparison_rows(...) 新增平均气温优先排序前缀。

结果：
- 查询页中平均气温展示为 common 口径，且在结果前部优先显示；
- 对比区中平均气温同样保持 common 口径。