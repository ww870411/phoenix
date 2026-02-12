时间：2026-02-12
需求：原煤明细表采用分级表头，口径下分本期/同期子字段。
实现：SpringFestivalDashboardView.vue 将原煤表头改为两行：父级口径（集团汇总、主城区、金州、北方、金普、庄河）+ 子级（本期/同期）；行数据按子列分别展示当前与同期值；删除不再使用的 formatCurrentPrior。
验证：frontend npm run build 通过。
留痕：configs/progress.md、frontend/README.md、backend/README.md 已更新。