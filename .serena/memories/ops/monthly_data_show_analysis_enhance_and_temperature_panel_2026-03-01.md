时间戳：2026-03-01
任务：增强“专业分析要点”，新增“平均气温”折叠分析区，并将页面主要数据与分析拆分导出为XLSX多子工作表。

变更文件：
1) backend/projects/monthly_data_show/api/workspace.py
2) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

后端实现：
- QueryComparisonResponse 增加 temperature_comparison。
- 新增温度对比模型：TemperatureDailyComparisonRow / TemperatureComparisonSummary / TemperatureComparisonPayload。
- 新增 _build_temperature_comparison_payload：
  - 查询当前窗口与同比窗口每日气温；
  - 输出逐日同比明细和平均气温同比汇总。

前端实现：
- 专业分析要点改为按 orderFields（数据层次顺序）分组，输出：
  - 同比差值/差异率
  - 环比差值/差异率
  - 计划比差值/差异率
  - Top波动与风险提示
- 新增“平均气温区间分析（默认折叠）”模块：
  - 平均气温同比卡片
  - 每日气温同比表
  - 本期/同期曲线图（SVG）
- XLSX 导出扩展为多工作表，覆盖汇总、查询结果、对比明细、热力图、TopN、专业分析、气温日序与气温汇总（按数据存在性输出）。

结果：
- 分析内容更贴合业务解读；
- 平均气温指标具备独立专题分析和导出能力；
- 导出文件与页面分析结构一致性提升。