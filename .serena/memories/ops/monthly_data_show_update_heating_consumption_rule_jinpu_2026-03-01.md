时间：2026-03-01
需求：刷新“10.供暖耗热量”规则，金普口径改为指标值=供热量（单位吉焦）。
实现：
- 文件：backend/projects/monthly_data_show/services/extractor.py
- 规则调整：
  - 金州/北方：供暖耗热量=供热量-高温水销售量（保持）
  - 金普/庄河/研究院/主城区电锅炉：供暖耗热量=供热量
验证：python -m py_compile backend/projects/monthly_data_show/services/extractor.py 通过。
留痕：configs/progress.md、backend/README.md、frontend/README.md 已更新。