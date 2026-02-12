时间：2026-02-12
用户反馈：庄河口径同期值应选用“其中：张屯原煤消耗量”。

变更文件：
- frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue
- configs/progress.md
- frontend/README.md
- backend/README.md

实现：
- 庄河分支中 prior 指标匹配从“原煤+剔除”调整为优先匹配“其中：张屯原煤消耗量”；
- 兼容关键词组合回退（其中 + 张屯原煤消耗量），应对文本空格差异。

验证：
- frontend 执行 npm run build 成功。

结果：
- 庄河口径同期值来源已按业务要求切换。