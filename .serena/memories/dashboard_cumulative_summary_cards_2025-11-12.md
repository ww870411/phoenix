# 2025-11-12 仪表盘累计摘要卡片切换
- 位置：frontend/src/daily_report_25_26/pages/DashBoard.vue
- 后四张 summary-card 改为读取 `/dashboard` 返回的 “9.累计卡片” 数据（供暖期平均气温、可比煤价边际利润、标煤耗量、投诉量），每项展示本期值与括号内的同期增量。
- 新增 `formatHeadlineNumber/formatHeadlineDelta` 与 `cumulativeSection` 相关计算属性，支持千分位格式与差值计算；旧的煤炭库存及单耗摘要逻辑已删除。
- 单位取自配置 `计量单位` 字段，若需回滚请恢复 `DashBoard.vue` 对应段落。