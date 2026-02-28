时间：2026-02-28
主题：monthly_data_show/pages 页面卡片字体样式对齐

用户反馈：项目子页面卡片字体与其他项目卡片观感不一致。

实现：
- 文件：frontend/src/projects/daily_report_25_26/pages/PageSelectView.vue
  1) .page-card 增加字体继承：font-family/font-size/line-height: inherit
  2) 增加 appearance: none，消除 button 默认样式差异
  3) 调整标题与描述样式：
     - title: 16px, var(--text)
     - desc: 13px, #666

结果：
- /projects/monthly_data_show/pages 的卡片字体风格与项目列表卡片一致。

留痕：
- configs/progress.md
- backend/README.md
- frontend/README.md