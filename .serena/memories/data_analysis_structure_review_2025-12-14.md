## 2025-12-14 数据分析页面结构梳理

- 操作：阅读 `frontend/src/daily_report_25_26/pages/DataAnalysisView.vue` 结构，无代码改动；仅在文档中登记结构总结。
- 关键流程：
  - 首屏 `getDataAnalysisSchema` 加载单位/指标/分析模式/默认日期，温度指标按关键词自动勾选但不选单位。
  - `runAnalysis` 校验单位与指标后，按所选单位逐一调用 `/data_analysis/query`，缓存 `rows/warnings/timeline/meta`，并支持多单位切换与 Excel 导出（单位独立 Sheet）。
  - 区间模式提供 RevoGrid 逐日表与趋势图（气温固定右轴），数据简报含整体概览/趋势观测/相关矩阵/风险提示，复制支持。
- 变更文件：
  - `configs/progress.md`：新增 2025-12-14 梳理记录（无代码改动）。
  - `frontend/README.md`：新增会话小结，说明 DataAnalysisView 依赖与交互流程。
  - `backend/README.md`：新增会话小结，说明后端接口依赖与无需改动。
- 验证：无功能变更，未运行构建/测试。
- 回滚：如需移除本次文档留痕，可删除上述三处新增小结。