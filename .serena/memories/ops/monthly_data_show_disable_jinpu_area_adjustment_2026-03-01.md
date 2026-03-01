时间：2026-03-01
需求：临时作废规则“金普 期末供暖收费面积 = 期末供暖收费面积 - 高温水面积”。
实现：
- 文件：backend/projects/monthly_data_show/services/extractor.py
- 新增开关 ENABLE_JINPU_HEATING_AREA_ADJUSTMENT = False
- extract_rows 中将 jinpu_heating_area_adjusted 改为按开关执行；当前关闭后不再应用扣减，统计为0。
验证：python -m py_compile backend/projects/monthly_data_show/services/extractor.py 通过。
留痕：configs/progress.md、backend/README.md、frontend/README.md 已更新。