时间：2026-02-12
用户反馈：原煤对比图缺少同期值，且单位不需要改变。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- coalScopeRows 增加 prior 字段；
- coalTrendOption 从单序列改为双序列（本期/同期）；
- tooltip 同时展示本期与同期；
- 两个序列都保留数据标签；
- 单位保持吨，不引入单位切换。

验证：
- frontend 执行 npm run build 成功。

结果：
- 煤耗图可直接按业务日期对比各口径本期与同期值。