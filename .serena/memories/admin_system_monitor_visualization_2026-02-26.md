时间：2026-02-26
任务：将管理后台系统监控改为图形化展示。
实现：
- 文件：frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 新增：metricHistory（cpu/memory/disk/processCpu）与 METRIC_HISTORY_LIMIT=60
- 采样：每次 loadSystemMetrics 成功后追加历史样本并裁剪上限
- 绘图：sparkPoints() 将历史值(0-100)映射为 SVG polyline 坐标
- UI：在系统监控卡片中增加 4 个 sparkline 趋势图
结果：系统监控支持实时短期趋势可视化，无需新增后端历史接口。