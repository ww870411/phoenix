时间戳：2026-03-08（Asia/Hong_Kong）
任务：将日报查询页 DataAnalysis 中“智能报告（BETA）”和“智能体设定”按钮移动到“生成智能报告”按钮前。
前置说明：已执行 serena__activate_project 与 serena__check_onboarding_performed；onboarding 已完成。
实施摘要：
1) 调整 frontend/src/projects/daily_report_25_26/pages/DataAnalysisView.vue 模板结构。
2) 将“智能报告（BETA）”与“智能体设定”从查询区上方 controls 迁移到结果区 result-header-actions。
3) 插入顺序为：下载 Excel -> 智能报告（BETA） -> 智能体设定 -> 生成智能报告 -> 下载智能分析报告。
4) 查询区原 ai-report-controls 仅保留未开放账号提示文案。
文档留痕：
- configs/progress.md 追加本轮记录。
- frontend/README.md 追加前端结构变化说明。
- backend/README.md 追加“无后端变更”联动说明。
降级说明：Serena 主要用于定位；由于 .vue 非符号模板结构改动，采用 apply_patch 做精确片段编辑；文档使用 desktop-commander 追加写入。
影响范围：仅前端视图层按钮布局，未改动后端接口与数据结构。
回滚方式：恢复 DataAnalysisView.vue 对应模板片段到改动前版本，并删除三份文档新增记录。