时间：2026-03-01
任务：将“2.28 月报数据库化配置文件”第四部分未落地的半计算补齐规则写入提取链路。
实现文件：backend/projects/monthly_data_show/services/extractor.py
新增函数：_apply_semicalculated_completion_rules(rows)
接入点：extract_rows（在常量注入前执行），并写入统计字段 semi_calculated_completed。
落地规则：
- 煤折标煤量：金普/庄河 = 耗标煤总量
- 供热耗标煤量：北海水炉/金普/庄河 = 耗标煤总量
- 耗电量：北海/香海=综合厂用电量+外购电量；供热公司/金普/庄河/研究院/主城区电锅炉=外购电量
- 耗水量：北海/北海水炉/香海=电厂耗水量
- 热网耗水量：供热公司/金普/庄河/研究院/主城区电锅炉=耗水量
- 热网耗电量：供热公司/金普/庄河/研究院/主城区电锅炉=外购电量
- 供暖耗热量：供热公司=各热力站耗热量；金州/北方/金普=供热量-高温水销售量；庄河/研究院/主城区电锅炉=供热量
说明：已保留并继续执行规则5（金普期末供暖收费面积扣减）。
留痕：configs/progress.md、backend/README.md、frontend/README.md 已更新。