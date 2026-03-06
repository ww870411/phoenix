时间：2026-03-06
主题：项目选择页桌面卡片高度回退

现象：
- 用户反馈 PC 端项目选择页卡片高度异常偏高。

原因：
- ProjectSelectView.vue 中此前增加了桌面端 .card 的 min-height: 136px，导致 PC 端卡片被整体抬高。

修正：
- 删除 frontend/src/pages/ProjectSelectView.vue 中桌面端 .card 的 min-height: 136px。
- 保留手机断点下的单列卡片和紧凑样式，不影响移动端优化。

验证：
- frontend 目录执行 npm run build，2026-03-06 构建通过。

影响范围：
- 仅前端桌面端展示密度修正，无后端改动。