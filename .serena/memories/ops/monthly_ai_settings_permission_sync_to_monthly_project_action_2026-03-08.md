时间戳：2026-03-08（Asia/Hong_Kong）
任务：将月报页面“智能体设定”权限从 isGlobalAdmin 同步为 monthly_data_show 的 can_manage_ai_settings。
前置说明：已基于 Serena 检索确认现状（旧逻辑为 isGlobalAdmin），并对齐日报口径。
变更文件：frontend/src/projects/monthly_data_show/pages/MonthlyDataShowQueryToolView.vue。
改动摘要：
1) 模板按钮权限：v-if / disabled 由 isGlobalAdmin 改为 canConfigureAiSettings。
2) AiAgentSettingsDialog 的 :can-manage 由 isGlobalAdmin 改为 canConfigureAiSettings。
3) 新增权限常量与计算：AI_SETTINGS_PROJECT_KEY='monthly_data_show'；canConfigureAiSettings = auth.canManageAiSettingsFor(AI_SETTINGS_PROJECT_KEY)。
4) openAiSettingsDialog 内部拦截改为 canConfigureAiSettings。
验证证据：文件内已无 isGlobalAdmin/normalizedGroup 残留；canConfigureAiSettings 在模板与函数中统一生效。
文档留痕：已追加更新 configs/progress.md、frontend/README.md、backend/README.md。
降级说明：.vue 非符号模板编辑场景，使用 apply_patch 执行精确替换。
回滚方式：恢复该文件中权限判定与变量定义到改动前（isGlobalAdmin 方案）。