# 数据分析页面：后端查询接口 + 前端联动（2025-11-27）

## 后端
- `backend/api/v1/daily_report_25_26.py`
  - `get_data_analysis_schema` 拆出 `_build_data_analysis_schema_payload`，支持“调整指标”分组与 `metric_group_views`，便于区分哪类指标可在哪些视图展示。
  - 新增 `POST /projects/daily_report_25_26/data_analysis/query`：依据 `unit_key/analysis_mode` 自动设置 `SET LOCAL phoenix.biz_date` 或 `phoenix.sum_start_date/end_date`，查询 `company_daily_analysis` 等视图，并补充常量指标（`constant_data`）。
  - 返回 `rows/missing_metrics/warnings/view/start_date/end_date`，前端可直接展示缺失提示与日期范围；若指标与当前视图不符，直接 400 告知具体指标。

## 前端
- `frontend/src/daily_report_25_26/pages/DataAnalysisView.vue`
  - 指标面板读取 `metric_group_views`，自动禁用当前视图不支持的分组（新增“调整指标”标签），按钮/复选框在查询过程中呈禁用态。
  - Run 按钮改为异步调用 `runDataAnalysis`，结果表展示单位、常量/缺失标签及环比色差，并在查询中显示 Loading 与后端 warning。
  - schema 载入及筛选条件变化时统一调用 `clearPreviewState`，避免旧数据干扰。

以上改动记录于 backend/frontend README 与 configs/progress.md。