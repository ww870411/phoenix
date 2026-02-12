时间：2026-02-12
用户诉求：投诉双图中两类投诉量（总/净，本期/同期）也仅显示到业务日期。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- 新增/统一 shouldShowActualByBizDate(dateText)；
- complaintTotalTrendOption：本期/同期柱数据按业务日期后置 null；
- complaintNetTrendOption：本期/同期柱数据按业务日期后置 null；
- 本期气温线使用同一判断函数。

验证：
- frontend 执行 npm run build 成功。

结果：
- 投诉双图中投诉柱与气温线均在业务日期处结束，后续不显示。