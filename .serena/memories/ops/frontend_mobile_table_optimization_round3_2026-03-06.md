时间：2026-03-06
主题：前端移动端优化第三轮（入口页与文案收敛）

前置说明：
- 延续 apply_patch 降级编辑方式，原因仍为 Vue SFC 结构化编辑支持有限。
- 用户追加要求：不要特意写“手机端已切换为横向滑动查看模式...”这类显式说明文案。

改动摘要：
1. DataEntryView.vue
- 删除 mobile-grid-hint 模板与样式。
- 保留横向滚动容器与 RevoGrid 最小宽度保护，不再使用显式提示文案。

2. LoginView.vue
- 在 <=640px 下收紧视觉区高度与 padding。
- 调整标题、描述、输入框和登录按钮尺寸，使竖屏触控更紧凑。
- 让登录表单卡片在手机下更像底部承接面板。

3. ProjectSelectView.vue
- 为卡片增加基础 hover/过渡。
- 在 <=768px 下切换为单列卡片布局，并压缩卡片高度、间距和文本密度。

4. ProjectEntryView.vue
- 为 entry-loading 增加 padding、行高与手机端字号/高度优化。

验证：
- frontend 目录再次执行 npm run build，2026-03-06 构建通过。
- 浏览器手机视口复测 DataEntryView，DOM 查询结果：hint=false，containsText=false，确认显式提示文案已完全移除。

影响范围：
- 仅前端展示与交互文案层，无后端接口变更。