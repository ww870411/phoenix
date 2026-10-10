# 生产日报边际利润与可比煤价边际利润核对
最后验证日期：2026-10-10。
用户要求：查明daily_report_25_26各单位两种利润公式、数据库表/视图、25-26和24-25单价常量，用于另行测算。
来源：本机phoenix_db / phoenix / public实际表与pg_get_viewdef。底表daily_basic_data、常量constant_data，展示sum_basic_data/groups，分析company/groups daily/sum，北海专用beihai_sub daily/sum。
公式：M=直接收入-非煤成本-标煤耗量×price_std_coal/10000；可比M仅改为price_std_coal_comparable。六家煤耗单位两期可比价1000。主城区三家、集团八家利润汇总均加回内购热成本、减内售热收入。
实际煤价25-26/24-25：北海833/1046、香海862.2914/1085.5565、金州825.45/1085、北方879.68/1103、金普885/1000、庄河932/1054。
特殊点：供热公司两项高温水/售汽收入取日报填报金额；暖收入固定156天分摊；外购电单价常量原始单位元/吨误标，实际按万kWh×元/kWh得到万元；庄河24-25外购热价NULL按0，25-26为47.71；研究院/供热及中心未配置煤价，不应称为真实零煤价。
抽样2026-03-01/2025-03-01，独立按日报原始量和常量复算八家+主城区+集团、2指标2期，40项一致，浮点最大绝对差5.684341886080802e-14万元。
制品：configs/2026-10-10_daily_report_25_26_边际利润公式与参数核对.md；daily_report_25_26_margin_constants_2026-10-10.json（222记录）；daily_report_25_26_margin_views_2026-10-10.sql（8份实际定义）；daily_report_25_26_margin_verification_2026-10-10.json。同步configs/progress.md、frontend/README.md、backend/README.md。
执行说明：Serena项目连接正常；非符号Markdown/JSON/SQL制品使用原生apply_patch创建。无业务代码、视图、表数据修改，回滚仅移除本轮制品及文档段。浏览器连接privileged native pipe bridge不可用，页面可见内容未验收。常量是当前行快照，并不能证明历史每一天参数版本。
服务器中途重启，函数存储丢失后重新只读提取原始证据和复算，先确认制品未创建，再生成最终文档。