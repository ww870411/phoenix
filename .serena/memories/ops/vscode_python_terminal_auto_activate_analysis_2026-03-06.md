日期：2026-03-06
任务：解释 VS Code 在 D:\编程项目\phoenix 中打开 .py 文件后，集成终端自动重启并执行 `d:\编程项目\phoenix_project\.venv\Scripts\Activate.ps1` 的原因。

前置说明：Serena 已接入并完成检查。仓库要求优先使用 Serena；本次主要为排查说明，无业务代码变更。文档补记使用了 desktop-commander 追加写入，原因是需要对 Markdown 留痕且未涉及符号级编辑。

证据：
1. 仓库根目录检索未发现 `.vscode/settings.json`、`*.code-workspace`、`launch.json`、`tasks.json`。
2. 仓库内搜索 `python.terminal.activateEnvironment`、`python.defaultInterpreterPath`、`terminal.integrated`、`Activate.ps1`、`.venv`，未发现当前仓库触发该行为的工作区级配置。
3. 用户现象中的命令 `& d:\编程项目\phoenix_project\.venv\Scripts\Activate.ps1` 符合 VS Code Python 扩展在 PowerShell 中自动激活虚拟环境的标准注入形式。
4. 激活路径指向相邻目录 `phoenix_project\.venv`，说明当前 VS Code 选中的 Python 解释器大概率绑定在另一个项目环境，而不是本仓库内配置触发。

结论：
- 该现象本质上不是“你点开 Python 文件导致系统异常”，而是 VS Code Python 扩展在真正识别到 Python 语言上下文后被激活，并对集成终端自动执行所选解释器的激活脚本。
- 之所以是“点开 .py 文件才发生”，是因为 Python 扩展常按语言上下文延迟激活；在未打开 Python 文件前，普通终端保持原样。
- 之所以激活的是 `phoenix_project\.venv`，是因为当前工作区/窗口绑定的解释器选择落在那个虚拟环境上。

影响范围：
- 仅影响本机 VS Code 集成终端的环境状态。
- 不影响仓库代码本身；未改动前后端业务文件。

留痕文件：
- configs/progress.md
- frontend/README.md
- backend/README.md

建议给用户的处理方向：
1. 在 VS Code 中执行 `Python: Select Interpreter`，切换到当前项目应使用的解释器。
2. 若不希望自动激活，在设置中关闭 `Python > Terminal: Activate Environment`。
3. 若怀疑窗口记住了错误解释器，检查是否打开的是多根工作区或历史工作区缓存。