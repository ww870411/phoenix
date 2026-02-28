时间：2026-02-28
变更摘要：
1) 前端 monthly_data_show 查询页将指标分段标题“当前指标（尾部含常量指标）”改为“基本指标”。
2) 前端在“基本指标”尾部追加“平均气温”选项，并在加载 query-options 时做兜底追加。
3) 后端 monthly_data_show 查询筛选项接口兜底返回“平均气温”。
4) 后端查询接口新增派生指标构建：当选中“平均气温”且期间包含 month、类型包含 real 时，从 calc_temperature_data 读取 aver_temp，按月份或区间做算术平均，合并到主查询结果并统一排序分页。
涉及文件：
- backend/projects/monthly_data_show/api/workspace.py
- frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
- configs/progress.md
- backend/README.md
- frontend/README.md
回滚思路：
- 撤销以上文件本次提交块，恢复 query-options 原始 items 返回逻辑与 query 仅 month_data_show 主表查询逻辑。