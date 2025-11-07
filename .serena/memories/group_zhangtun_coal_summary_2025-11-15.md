## 2025-11-15
- 更新 `backend/sql/groups.sql`，新增 `group_sum_raw_zhangtun`、`group_sum_std_zhangtun` CTE，输出 `company = 'Group'` 的 `sum_consumption_amount_raw_coal_zhangtun` 与 `sum_consumption_amount_std_coal_zhangtun` 两条指标。
- 计算方式：对 `BeiHai/XiangHai/GongRe/JinZhou/BeiFang/JinPu` 的 `consumption_amount_raw_coal`/`consumption_std_coal` 与 `ZhuangHe` 的 `*_zhangtun` 在日值、7 天、当月、供暖期窗内逐项求和。
- 已在前后端 README、`configs/progress.md` 记录背景和回滚方案，供日后排查。