时间：2026-02-12
反馈：春节主题影响阅读，顶部四卡背景与文字对比异常。
修复：
1) SpringFestivalDashboardView.vue 中将春节主题通用卡片样式限定为 .card:not(.summary-card)，避免覆盖四卡。
2) 为 summary-card 在 festival 主题下单独设置高对比渐变与文字阴影，恢复可读性。
3) 增加轻量装饰层 festival-ornaments（左右灯笼+福启新岁），pointer-events:none，避免干扰交互。
4) 增补移动端装饰尺寸与位置适配。
验证：frontend npm run build 通过。
留痕：configs/progress.md、frontend/README.md、backend/README.md 已同步。