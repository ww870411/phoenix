时间：2026-03-01
需求：将指标计量单位加入配置文件。
实现：
- 文件：backend/projects/monthly_data_show/services/indicator_config.py
  - 支持 basic_groups.items[].unit 字段解析并传递。
- 文件：backend_data/projects/monthly_data_show/indicator_config.json
  - 为基础指标分组项补齐 unit 字段。
验证：
- 容器内加载配置成功，basic_items unit_count=67。
结果：
- 基础指标/计算指标单位均可在配置文件统一维护。