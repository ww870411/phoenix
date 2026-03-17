日期：2026-03-17
任务：按用户要求继续处理中断任务，并完成文档同步。

本轮新增处理：
1. 将 backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json 中 semi_calculated_rules 整段改为“每个规则对象单行”书写，提升人工维护与扫读效率。
2. 按用户最新要求，补写三个记录文件：
- configs/progress.md
- frontend/README.md
- backend/README.md
记录内容覆盖本次会话的主要过程：
- 平均气温查询逻辑核查
- 2024-01 平均气温同比缺失修复
- semi_calculated_rules 公式能力与跨口径引用支持
- import-workspace 步骤二规则选择升级为父项折叠 + 子项逐条勾选
- unit_normalize_rules 纳入选择项并补充 exact_match 展示
- 临时引入再移除的规则勾选记忆能力
- 全部 semi_calculated_rules 统一 allow_missing_subtrahend_as_zero=true
- semi_calculated_rules 单行化维护格式

验证证据：
- JSON 解析通过：monthly_data_show_extraction_rules.json
- python -m py_compile backend/projects/monthly_data_show/services/extractor.py backend/projects/monthly_data_show/api/workspace.py 通过
- frontend npm run build 通过

偏差状态更新：
- 用户已在本轮明确要求保存全部过程到三个记录文件，因此此前“暂不更新三个记录文件”的偏差已结束，记录文件已补齐。