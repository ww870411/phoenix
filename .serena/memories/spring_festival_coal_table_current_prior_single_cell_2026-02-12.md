时间：2026-02-12
需求：原煤对比表不再将本期/同期拆为两列，改为各口径单列且单元格显示本期/同期。
改动：
1) SpringFestivalDashboardView.vue 中原煤表头改为口径单列（集团汇总、主城区、金州、北方、金普、庄河）。
2) 原煤各口径单元格改为 formatCurrentPrior(...) 输出“本期/同期”。
3) 新增 formatCurrentPrior 函数处理空值与精度。
验证：frontend npm run build 通过。
留痕：configs/progress.md、frontend/README.md、backend/README.md 已更新。