# monthly_data_show 数据目录

本目录用于月报入库工作台（`monthly_data_show`）的运行时文件落点。

- `uploads/`：前端上传原始月报文件（后续阶段可启用持久化）
- `outputs/`：CSV 提取结果文件（后续阶段可启用留存）
- `indicator_config.json`：指标配置文件（基本指标分组/顺序/单位、计算指标顺序/单位/公式）

当前阶段导出 CSV 采用临时文件直传下载，本目录先保留结构位。
