时间：2026-03-01
问题：用户反馈月报导入提取时，规则“金普 期末供暖收费面积 = 期末供暖收费面积 - 高温水面积”未执行。
定位：backend/projects/monthly_data_show/services/extractor.py 原有逻辑无该专项扣减规则。
改动：
1) 新增函数 _apply_jinpu_heating_area_adjustment(rows)
- 仅针对 company=金普；
- 按 date+period+type+report_month 同窗口匹配“期末供暖收费面积/高温水面积”；
- 计算差值并回写到“期末供暖收费面积”，单位置为平方米。
2) 在 extract_rows 中接入并写入统计字段 jinpu_heating_area_adjusted。
3) 更新留痕文档：configs/progress.md、backend/README.md、frontend/README.md。
结果：导入提取阶段将自动应用该规则，后续入库与查询数据使用扣减后值。