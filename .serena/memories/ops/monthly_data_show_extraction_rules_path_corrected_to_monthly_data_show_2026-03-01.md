时间：2026-03-01
用户反馈：提取规则配置文件放错目录，应在 backend_data/projects/monthly_data_show。
处理：
1) 文件迁移
- 从 backend_data/projects/monthly_data_pull/mapping_rules/monthly_data_show_extraction_rules.json
- 到 backend_data/projects/monthly_data_show/monthly_data_show_extraction_rules.json
2) 读取路径修正
- 文件：backend/projects/monthly_data_show/services/extractor.py
- 将候选路径统一改为 monthly_data_show 目录（容器 /app/data、/app/backend_data、本地 backend_data）。
3) 文档更新
- configs/progress.md
- backend/README.md
- frontend/README.md
- backend_data/projects/monthly_data_pull/README.md
- backend_data/projects/monthly_data_show/README.md
验证：python -m py_compile backend/projects/monthly_data_show/services/extractor.py 通过。