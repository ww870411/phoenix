时间：2026-02-12
需求：列出并改造所有逐小时气温业务点，统一改为从 calc_temperature_data 视图读取；期间平均为每日平均再平均。
原逐小时业务点：
1) backend/services/dashboard_expression.py:_fetch_temperature_series（temperature_data 小时查询）
2) backend/services/dashboard_expression.py:_fill_temperature_block（填充24小时数组）
3) backend/services/dashboard_expression.py:evaluate_dashboard 第1节“逐小时气温”调用上述链路（发布缓存也走此路径）
4) frontend/src/projects/daily_report_25_26/pages/DashBoard.vue:calcAverageFromList/temperatureSeries/averageTemp 对小时数组求日均
改造：
1) 后端新增 _fetch_daily_temperature_stats_map，改从 calc_temperature_data 读取 date,max_temp,min_temp,aver_temp。
2) 后端 _fill_temperature_block 改为写入日级对象 {max,min,avg}。
3) 前端 calcAverageFromList 扩展支持对象格式（avg/aver_temp/average/value）与旧数组双兼容。
4) 期间平均口径保留为 _fetch_average_temperature_between: AVG(aver_temp)。
验证：frontend npm run build 通过；python -m py_compile backend/services/dashboard_expression.py 通过。
涉及文件：backend/services/dashboard_expression.py，frontend/src/projects/daily_report_25_26/pages/DashBoard.vue，configs/progress.md，frontend/README.md，backend/README.md。