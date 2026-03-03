时间：2026-03-03
问题：New API 连通性测试通过，但完整报告阶段持续出现 HTTP 504 Gateway time-out（Cloudflare）。
判断：长上下文+多阶段调用触发上游处理超时，测试请求短小因此可通过。
变更：backend/services/data_analysis_ai_report.py
1) 新增 _is_transient_gateway_error(exc)，识别 500/502/503/504/gateway timeout/timed out。
2) _call_model 增加瞬时网关错误退避重试：2 秒后重试（attempt < retries）。
3) 新增 New API 独立提示词长度上限 PROMPT_DATA_MAX_CHARS_NEWAPI=36000。
4) _resolve_prompt_data_char_limit 按 provider 返回上限；_serialize_prompt_processed_data 改为使用动态上限。
结果：New API 长请求更不易触发超时，且出现瞬时 504 时可自动自恢复一次。