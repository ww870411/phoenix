时间：2026-02-28
变更主题：monthly_data_pull 映射显示规则修正（去括号并保留实际上传文件名）
触发原因：用户反馈映射规则中的源文件名/底表名仅是参考示例，月份会变化，页面直接显示原始映射名造成误导。
变更文件：
1) frontend/src/projects/monthly_data_pull/pages/MonthlyDataPullEntryView.vue
2) configs/progress.md
3) frontend/README.md
4) backend/README.md
实现摘要：
- 前端新增 normalizeReferenceName(name)：去扩展名，去中英文括号及括号内容（()、（）、[]、【】），压缩空白。
- 源文件与目标底表槽位标题改为显示 normalizeReferenceName(key)。
- 槽位下方文件名继续显示 fileState.*[key]?.name，上传后展示真实文件名。
契约影响：无。后端接口与匹配键值不变，执行链路不变。
回滚方式：将 MonthlyDataPullEntryView.vue 的 slot-title 从 normalizeReferenceName(key) 改回 key，并删除 normalizeReferenceName 函数；文档回退对应新增段落。
验证证据：
- 搜索命中：MonthlyDataPullEntryView.vue 第42/72行已改为 normalizeReferenceName(key)，第176行存在函数定义。