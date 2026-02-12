时间：2026-02-12
问题：用户反馈 mini 看板设备明细表形式不对，不应平铺所有设备字段及本期/同期列。
处理：
1) 在 SpringFestivalDashboardView.vue 中将设备表改为分组列（炉机组态、调峰水炉、燃煤锅炉）。
2) 组内采用标签+本期/同期组合展示（如 炉 3/3、机 3/3），风格对齐 daily_report_25_26 参考表。
3) 对本期与同期均为0的设备项做过滤，组内为空显示“—”。
4) 新增组合单元格样式 device-combo-cell/combo-item/combo-label/combo-value。
验证：frontend npm run build 通过。