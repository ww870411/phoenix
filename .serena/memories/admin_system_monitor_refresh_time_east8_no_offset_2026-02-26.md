时间：2026-02-26
任务：系统监控“最近刷新”时间改为东八区且不显示 +08:00。
实现：
- 文件：frontend/src/projects/daily_report_25_26/pages/AdminConsoleView.vue
- 新增 formatEast8Time(value)
- 使用 Intl.DateTimeFormat + timeZone=Asia/Shanghai 格式化
- 输出格式：YYYY-MM-DD HH:mm:ss
- 模板中“最近刷新”改为调用该格式化函数
结果：页面显示为东八区纯时间文本，无时区后缀。