时间戳：2026-02-15
问题：用户反馈模块化调整后气温曲线持续空白，且调整前可用。

判断：
- 运行环境可能未重载后端新增路由，导致前两个轻量接口不可达。

修复：
- 文件：frontend/src/projects/daily_report_spring_festval_2026/services/api.js
- 函数：getTemperatureTrendByDate
- 回退链路升级为三级：
  1) spring 项目轻量接口
  2) daily_report_25_26 轻量接口
  3) 历史稳定接口 getDashboardData('daily_report_25_26')

结果：
- 不依赖后端重启也可恢复温度数据来源，避免曲线空白。