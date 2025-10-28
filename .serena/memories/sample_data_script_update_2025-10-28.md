时间：2025-10-28
主题：示例数据脚本适配最新模板与表结构
触发：数据库重建后样例数据缺失，需要重新生成 2025-10-20~2025-10-27 数据
范围：backend/scripts/generate_daily_basic_sample.py；文档 backend/README.md、frontend/README.md；留痕 configs/progress.md
主要变更：
- 模板读取切至 configs/数据结构_基本指标表.json
- 交叉表 GongRe_branches_detail_sheet 扁平化，按中心写入 company/company_cn
- 文本型列（单位为“-”或特定项目）写入 note，value 为 NULL
- 表名修正为 daily_basic_data（小写）
- 固定日期 2025-10-20~2025-10-27（含首尾）
输出：backend/sql/sample_daily_basic_data.csv、backend/sql/sample_daily_basic_data.sql
回滚：将 TEMPLATE_FILE/TABLE_NAME/TARGET_DATES 回改；删除派生 CSV/SQL 重新生成
证据：backend/sql/create_tables.sql；configs/数据结构_基本指标表.json；configs/供热中心字典样例.json；backend/README.md 说明
