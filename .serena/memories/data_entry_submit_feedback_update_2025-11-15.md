## 2025-11-15 数据填报成功提示
- 调整 `frontend/src/daily_report_25_26/pages/DataEntryView.vue` 中的成功提示文案，将 `startRefreshCountdown()` 内 `showSubmitFeedback` 的文案改为“提交成功，数据已入库！”。
- 背景：用户希望提示符号为感叹号以匹配现有设计；倒计时与自动刷新逻辑保持不变。
- 影响：仅前端提示文字，后端接口与交互未改动；回滚时恢复该文案即可。