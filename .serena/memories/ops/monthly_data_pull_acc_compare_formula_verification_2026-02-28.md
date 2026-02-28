时间：2026-02-28
主题：累计一致性核对补强（目标公式参与比对）
触发：用户反馈异常提示未覆盖累计不一致问题。

改动文件：
1) backend/projects/monthly_data_pull/services/engine.py
2) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
3) configs/progress.md
4) backend/README.md
5) frontend/README.md

实现摘要：
- 后端：
  - 目标累计单元格为公式时，提取公式表达式并尝试求值；
  - 与源累计值比对后给出 acc_compare_status：ok / mismatch / formula_not_verifiable；
  - compare_stats 增加 formula_not_verifiable 计数。
- 前端：
  - 异常清单筛选纳入 formula_not_verifiable；
  - 汇总展示“公式未校验”计数；
  - 说明文案补充“累计公式无法校验”提示。

结果：
- 可计算公式可直接检出累计不一致；
- 复杂公式会明确标注未校验，不再被误认为一致。