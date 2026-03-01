时间：2026-03-01
主题：monthly_data_show 导出列与文件名简化

用户诉求：
1) 导出内容与查询结果保持一致（不显示 report_month）；
2) 文件名从长区间+时间戳简化为 月报查询分析_YYYY-MM.xlsx。

改动文件：
1) frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md

实现摘要：
- downloadXlsx() 的查询结果 sheet 列从
  [company,item,unit,value,date,period,type,report_month]
  调整为
  [company,item,unit,value,date,period,type]
- 新增 resolveExportMonthTag() / formatMonthTag()：
  - 优先使用筛选中的 reportMonthFrom/reportMonthTo 或 dateMonthFrom/dateMonthTo；
  - 次选 comparison 窗口标签；
  - 再回退结果样本日期；
  - 最后回退当前年月。
- 文件名改为 月报查询分析_${monthTag}.xlsx。

结果：
- 导出与页面字段一致；
- 文件名符合“月报查询分析_2026-01.xlsx”样式。