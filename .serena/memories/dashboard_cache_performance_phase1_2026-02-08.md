时间戳：2026-02-08
任务：按用户确认执行数据看板缓存发布性能优化（第一阶段），并保留现有业务口径。

前置说明/偏差记录：
- 用户要求先全面思考后实施，已先完成链路排查与瓶颈定位，再执行改造。
- 文件读写遵循用户约束：未使用 cmd/powershell 脚本写文件，改动通过 apply_patch 完成。

变更文件清单：
1) backend/services/dashboard_expression.py
2) backend/services/dashboard_cache_job.py
3) backend/api/v1/daily_report_25_26.py
4) frontend/src/daily_report_25_26/services/api.js
5) frontend/src/daily_report_25_26/pages/DashBoard.vue
6) configs/progress.md
7) backend/README.md
8) frontend/README.md

实现摘要：
- 发布窗口参数化：后端 /dashboard/cache/publish 新增 days(1..30)，默认7；前端新增“发布天数（1/3/7）”并透传。
- 发布任务级查询缓存：cache_publish_job 在一次任务内构建 shared_metrics_cache，传入 evaluate_dashboard，跨日期复用 groups/sum_basic_data 查询结果。
- 去除人为延时：evaluate_dashboard 的进度回调移除固定 sleep(0.1)。
- 逐小时气温窗口化：从“历史起点全量扫描”改为“回溯窗口（默认7天，可配置回溯天数1..31）+预测天数”。

预期效果：
- 日常场景可用1天发布显著缩短耗时；
- 7天发布时减少重复 Group 查询与无效温度查询，CPU 持续占用时长下降；
- 接口契约向后兼容（days 参数不传仍为7）。

回滚方案：
- 回滚上述8个文件到本次修改前版本；
- 前端若不再暴露窗口控制，可仅保留后端 days 能力并默认7。