时间：2026-03-18
背景：用户确认 daily_report_25_26 数据展示运行时页面当前数据与导出样式正确，但页面加载和 Excel 导出性能差，先实施第一阶段优化，仅减少重复取数/重复求值，不改口径和表样。
变更文件：
- backend/services/runtime_expression.py
- backend/projects/daily_report_25_26/api/legacy_full.py
- frontend/src/projects/daily_report_25_26/services/api.js
- frontend/src/projects/daily_report_25_26/pages/DisplayRuntimeView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md
实现摘要：
1. render_spec 增加同请求级共享缓存：按 biz_date+table+company 复用指标结果，按 table+company 复用常量结果，并缓存同业务日温度极值结果。
2. 新增 POST /projects/daily_report_25_26/runtime/spec/eval-batch，支持 jobs 数组批量求值多个展示 sheet，并在同一次批量请求中共享上述缓存。
3. DisplayRuntimeView 导出链路改为一次批量调用 evalSpecsBatch，替代原先对 Group_sum_show_Sheet、Group_analysis_brief_report_Sheet、ZhuChengQu_sum_show_Sheet 的 3 次串行 evalSpec。
4. 导出仍沿用原模板 25-26生产日报标准模板.xlsx、原 origin/slicePoint 填充逻辑与原文件名规则，确保表样不变。
验证：
- python -m py_compile backend/services/runtime_expression.py backend/projects/daily_report_25_26/api/legacy_full.py 通过。
- frontend 执行 npm run build 通过。
边界：
- 本轮主要优化导出重算链路；单个展示页首次加载仍沿用单 sheet render_spec，若生产环境仍慢，下一阶段继续拆解单次页面加载耗时并评估多进程/更细粒度并行。