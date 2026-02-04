## 2025-12-09（仪表盘运行设备明细展示优化 - 零值隐藏）

- **User Request:** 如果某个指标（本期和同期）都为零，则不显示其标签和数字，而是显示一个中性占位符。
- **Agent Action:**
  1. 修改 `frontend/src/daily_report_25_26/pages/DashBoard.vue` 中的 `renderDeviceCombo` 函数。
  2. 在渲染 `combo-item` 列表之前，先过滤掉那些本期和同期值都为零的 `item`。
  3. 如果过滤后没有剩余的 `item`（即所有指标都为零），则整个单元格显示一个居中的灰色 `—`。
  4. 为 `combo-zero-cell` 添加了 CSS 样式，使其在单元格中居中显示。
- **Result:** 现在，当某个设备的运行指标（例如“汽炉数”）本期和同期都为零时，该指标的标签和数字将不会显示，使得表格更专注于展示有数据的项。如果一个分组内的所有指标都为零，则该分组对应的单元格会显示一个清晰的 `—` 占位符，进一步提升了表格的简洁性和可读性。

## 2026-01-10（数据分析环比数据缩放修正）

- **User Request:** 修正数据分析页面累计模式下，“环比比较”板块中百分比指标（如“全厂热效率”）上期数值显示错误（如 0.85% 而非 85%）的问题。
- **Agent Action:**
  1. 分析 `backend/api/v1/daily_report_25_26.py` 中的 `_execute_data_analysis_query_legacy` 函数。
  2. 发现构造 `prev_totals_map` 时未对百分比类指标应用缩放函数 `_scale_metric_value`。
  3. 修改代码，在计算 `ring_ratio` 之前以及填充 `prev_totals_map` 时，统一对相关数值进行缩放处理。
- **Result:** 现在环比板块的“上期累计”数值量级已与本期、同期保持一致，百分比指标能够正确显示。

## 2026-01-31（SSL 证书过期导致 Cloudflare 526 错误）

- **User Request:** 网站突然无法访问，Cloudflare 显示 526 错误（SSL 无效），仅在 "Full" 模式下可用，"Strict" 模式报错。需要排查原因。
- **Agent Action:**
  1. 检查 `docker-compose.server.yml` 和 `deploy/nginx.prod.conf`。
  2. 发现 `certbot` 容器配置了自动续期命令 (`certbot renew`)，但 `web` (Nginx) 容器缺少对应的重载 (reload) 机制。
  3. Nginx 仅在启动时读取证书，即使 Certbot 更新了证书文件，Nginx 内存中仍运行旧证书，导致过期。
- **Result:** 建议用户在服务器执行 `docker compose -f docker-compose.server.yml restart web` 以重载证书。建议后续增加 Nginx 定时重载机制。