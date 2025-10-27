时间：2025-10-28
问题：calc_sum_basic_data 的价格项匹配依赖常量表项名精确等值，实际常量数据存在大小写/空格/连字符/轻微拼写差异（如 price power sales、price_alkali vs price_clkali），导致价格 miss。
改动：
1) 新增视图 v_constants_center_first_norm：对 item 进行规范化（trim、转小写、空白/连字符→下划线、合并重复下划线），输出 item_key。
2) calc_sum_basic_data 的常量连接与 CASE 判断改用 item_key；
   - 为已知差异增加容错：price_alkali←→price_clkali；price_ammonia_water←→price_n_ammonia_water；eco_season_heating_income←→season_heating_income。
3) calc_sum_gongre_branches_detail_data 的常量连接同样切换为规范化视图。
影响：常量项微小命名差异不再导致 miss；is_price_power_null 在 trace 中可准确反映价格是否缺失。
验证：
- 在不同写法的 item 存在时，trace 与 calc*_ 视图能成功命中价格；
- 若 item 完全缺失，trace 的 is_price_power_null=true 以便排查。
回滚：如需恢复原精确匹配，可将 join 与 CASE 改回 v_constants_center_first，删除/停用规范化视图。
