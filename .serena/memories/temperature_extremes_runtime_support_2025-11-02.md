时间：2025-11-02
主题：集团分析简报温度指标接入
背景：Group_analysis_brief_report_Sheet 需要展示“日最高气温/日最低气温”，原先 value_biz_date() 依赖 sum_basic_data 返回 0。
实现：
- 数据层：视图更名为 `calc_temperature_data`，每日输出 `max_temp`、`min_temp`、`aver_temp`。
- 服务层：`runtime_expression.render_spec` 在预取指标时调用 `_fetch_temperature_extremes`，将当日及同期日极值写入 `metrics_by_company['Group']`（amount_temp_highest/lowest 的 value/sum_* 帧）。
- 表达式无需改动，模板保持 `value_biz_date()`/`value_peer_date()`。
注意：当前仅为 `Group` 公司注入温度极值；若后续希望各单位单独展示，需要扩展 `calc_temperature_data` 增加单位维度并在 `_fetch_temperature_extremes` 中按公司填充。