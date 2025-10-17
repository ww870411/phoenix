2025.10.17
新建目录结构
【初始化项目】
1.前端
在frontend下运行：npm create vue@latest，提示
  Need to install the following packages:
  create-vue@3.18.1
选择y后即开始初始化项目
运行项目
npm run dev

2.后端
pip install "fastapi[standard]"
pip install unvicorn

运行项目
uvicorn main:app --reload

【项目隔离】
项目名称统一为：daily_report_25_26
后端暂未隔离，未来通过api进行隔离，但前端设置严格隔离

codex resume 0199efec-4bae-7030-b3b5-7fb56ec9f7ad

删除冗余内容，确保目录干净。
添加dockerfile及docker-compose.yml，设定为开发环境使用。

codex resume 0199efec-4bae-7030-b3b5-7fb56ec9f7ad
好了，刚才在你的帮助下，我们一同构建了应用框架。backcend是后端目录，frontend是前端目录，并使用docker组织，上面两个目录中的README.md是由你负责维护的  程序结构。D:\编程项目\phoenix\configs\progress.md是每次进行修改后你进行记录的地方。根目录下的AGENTS.md是我对你的要求

codex resume 0199f1ca-fa0c-7023-847f-1b45cc2dfb9f
