## 2025-12-27 多阶段 AI 报告实现
- 触发：用户要求数据分析 AI 报告拆成多轮大模型调用、逐步思考。
- 变更：`backend/services/data_analysis_ai_report.py` 新增洞察/布局/HTML 三阶段 Prompt、`_call_model/_run_json_stage`、CSS 常量及 job 阶段字段；`configs/progress.md`、`backend/README.md`、`frontend/README.md` 记录流程与状态字段。所有编辑遵循仓库“apply_patch 写入”约束。
- 验证：`python -m py_compile backend/services/data_analysis_ai_report.py` 通过；AI job 状态现支持 stage=insight/layout/render/ready，解析失败会落入 failed 并返回错误信息。
- 回滚：恢复上述文件即可退回单阶段 HTML 生成逻辑。