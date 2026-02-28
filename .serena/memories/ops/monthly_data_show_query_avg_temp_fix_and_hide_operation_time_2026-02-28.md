时间：2026-02-28
变更摘要：
1) 前端查询结果表移除 operation_time 显示列。
2) 后端修正“平均气温”计算范围：当仅选择单个月份边界时，按该月完整自然月计算平均值。
3) 后端查询将“平均气温”从主表 month_data_show 项中过滤，防止主表同名数据覆盖/干扰；仅选平均气温时跳过主表查询，仅返回 calc_temperature_data 派生结果。
涉及文件：
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- backend/projects/monthly_data_show/api/workspace.py
- configs/progress.md
- backend/README.md
- frontend/README.md
验证要点：
- 查询结果无 operation_time 列
- 单月查询平均气温不再等于首日值，而是月内日均值算术平均