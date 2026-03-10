时间：2026-03-09
任务：按用户要求在 backend/services 下新增辽宁省发改委现货电价抓取脚本。
新增文件：backend/services/liaoning_spot_price_fetcher.py
功能：独立 CLI，抓取 POST https://fgw.ln.gov.cn/indexview/api/getListData，默认范围为 2026-01-01 到当天；默认过滤全空占位日；支持 --output-json、--output-csv、--include-empty-days、--timeout、--pause-seconds。
实现细节：使用 httpx.Client；按仓库规范实现 429 退避 20 秒重试一次、5xx/超时退避 2 秒重试一次；将 getListData 的 24 行 * 4 组字段展开为 96 个 15 分钟点位。
验证：已执行 `python backend/services/liaoning_spot_price_fetcher.py --start-date 2026-03-08 --end-date 2026-03-09`，输出为“请求 2 天，返回 1 天，有效发布 1 天，全空日 0 天”，说明默认过滤规则已生效，2026-03-09 全空占位日被排除。
留痕文件：configs/progress.md、frontend/README.md、backend/README.md。
回滚方式：删除 backend/services/liaoning_spot_price_fetcher.py，并删除三份文档中 2026-03-09 对应新增小节。