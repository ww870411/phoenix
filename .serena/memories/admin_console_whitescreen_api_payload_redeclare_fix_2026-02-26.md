时间：2026-02-26
范围：frontend/src/projects/daily_report_25_26/services/api.js；configs/progress.md；frontend/README.md；backend/README.md
问题：前端白屏，控制台报 SyntaxError: Identifier 'payload' has already been declared（api.js loginSuperAdmin）。
修复：
1) loginSuperAdmin 参数名 payload 改为 loginPayload；
2) response.json() 结果变量改为 data；
3) 消除同一作用域变量重定义。
结果：页面可正常加载。