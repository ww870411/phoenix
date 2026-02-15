时间戳：2026-02-15
问题：用户反馈气温图仍空白。

诊断：
- spring 新接口上线后，若后端实例未热重载到新路由，前端主路径会报错（如404），此前未降级处理会导致映射为空。

修复：
- 文件：frontend/src/projects/daily_report_spring_festval_2026/services/api.js
- 函数：getTemperatureTrendByDate
- 策略：
  1) 先调用 spring 路径 /projects/{projectKey}/spring-dashboard/temperature/trend
  2) 捕获异常后回退调用 daily_report_25_26 轻量温度接口 getDashboardTemperatureTrend

结果：
- 在路由切换窗口期（或后端未重载）仍可拿到温度数据，避免曲线空白。