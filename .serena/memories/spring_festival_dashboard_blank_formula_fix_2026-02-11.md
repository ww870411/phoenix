时间：2026-02-11
问题：mini数据看板出现“有提取JSON但卡片/图表空白”。
证据：configs/2.12 调试信息.md 显示 matched.coal/totalComplaint/netComplaint 已命中，但 payload.current/prior 为 Excel 公式字符串（如 =AE12+AE26+...）。
根因：前端图表需要数值；后端 xlsx_extract 提取时保留了公式文本，未求值。
变更：backend/projects/daily_report_spring_festval_2026/api/xlsx_extract.py
- 新增公式求值能力：单元格引用(A1样式)+四则运算+括号；
- current/prior 改为数字优先，遇公式时求值后输出数值；
- diffCell 保留原值用于追溯。
影响范围：仅春节迷你项目提取接口 /spring-festival/extract-json 与 latest-json 数据内容质量，不影响旧项目接口路径。
回滚思路：回滚 xlsx_extract.py 本次公式解析相关函数与调用点，恢复原始字符串输出策略。