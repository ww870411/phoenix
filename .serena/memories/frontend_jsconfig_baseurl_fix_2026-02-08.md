# 2026-02-08 前端 jsconfig 报错修复

## 触发
用户反馈 `frontend/jsconfig.json` 报错。

## 排查
- `frontend/jsconfig.json` 存在 `compilerOptions.paths`（`@/* -> ./src/*`）。
- `frontend/vite.config.js` 已存在 `@` 别名配置。
- 问题在于 jsconfig 使用 `paths` 但未设置 `baseUrl`，会触发编辑器/TS Server 配置错误。

## 修复
- 在 `frontend/jsconfig.json` 增加：`"baseUrl": "."`。

## 结果
- jsconfig 路径映射配置完整，`@/*` 别名可正常被编辑器解析；
- 与 Vite 构建别名口径一致，避免“运行可用、编辑器报错”的割裂。