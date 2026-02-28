时间：2026-02-28
主题：LibreOffice Headless 作为外部导表程序在线化引擎的可行性调研

结论摘要：
1) 可行：LibreOffice 支持 headless 无界面运行，支持命令行转换与 UNO 受控模式。
2) 公式重算能力存在：UNO 的 XCalculatable 提供 calculate/calculateAll，可用于重算公式。
3) 工程建议：优先持久化服务模式（unoserver）而非每次启动 soffice。
4) 风险：服务端口默认无安全保护，必须仅内网可达并加进程守护与超时重启机制。

关键证据链接：
- LibreOffice 启动参数（--headless / --accept / --convert-to）：https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html
- UNO 计算接口（XCalculatable.calculateAll）：https://api.libreoffice.org/docs/idl/ref/interfacecom_1_1sun_1_1star_1_1sheet_1_1XCalculatable.html
- unoconv 状态（deprecated，推荐 unoserver）：https://github.com/unoconv/unoconv
- unoserver 说明（listener 性能收益、端口安全提示）：https://github.com/unoconv/unoserver

与 Phoenix 的映射建议：
- 保持现有数据填报主链不变；
- 新增“导表执行”模块，采用单实例队列 + UNO 服务（unoserver）+ 超时/重试；
- 首批模板做保真与累计重算回归后再扩大范围。