时间：2026-03-01
需求：新增导入指标名称转换规则“锅炉耗柴油量 -> 耗油量”。
实现：
- 文件：backend/projects/monthly_data_show/services/extractor.py
- 位置：ITEM_RENAME_MAP
- 新增映射："锅炉耗柴油量": "耗油量"
留痕：
- configs/progress.md 已追加记录。
- backend/README.md 与 frontend/README.md 已追加结构同步说明。
结果：月报导入工作台识别到“锅炉耗柴油量”时，统一归并为“耗油量”进入后续处理链路。