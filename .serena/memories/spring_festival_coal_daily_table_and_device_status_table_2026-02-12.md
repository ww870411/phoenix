时间：2026-02-12
变更范围：frontend/src/projects/daily_report_spring_festval_2026/pages/SpringFestivalDashboardView.vue；configs/progress.md；frontend/README.md；backend/README.md
实现内容：
1) 在“当日各口径耗原煤量对比”图下新增每日明细表，字段为日期、气温，以及集团汇总/主城区/金州/北方/金普/庄河的本期与同期原煤消耗量。
2) 新增 COAL_SCOPE_CONFIGS、resolveCoalMetricByScope、coalRows、coalVisibleRows，数据源按 byDate 解析，并仅显示到业务日期。
3) 在页面图表底部新增“各单位运行设备数量明细表”（业务日期），口径为北海电厂（含北海水炉）、香海、金州、北方、金普、庄河。
4) 新增 DEVICE_SCOPE_CONFIGS、resolveScopeMetricValuesByConfig、deviceStatusRows；北海按北海热电联产+北海水炉聚合；指标含运行汽炉数/运行汽轮机数/运行水炉数/运行锅炉房锅炉数（本期/同期）。
5) 新增 table-scroll 样式支持宽表横向滚动。
验证：frontend 执行 npm run build 通过。