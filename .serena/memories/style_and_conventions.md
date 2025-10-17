代码与命名约定：
- Python：变量 `snake_case`、常量 `UPPER_SNAKE`、类名 `PascalCase`；类型注解与必要中文注释。
- TypeScript/JavaScript：变量 `camelCase`、类型/类 `PascalCase`；与后端字段命名保持一致。
- 接口字段：小写 + 下划线（与统一规范一致），枚举值 `'num'`、`'text'`。
- 变更流程：Serena 优先；受阻可降级至 apply_patch，并在进度与知识中留痕。
- 文档：中文为主，变更需同步更新 `configs/progress.md` 与各 README 结构说明。