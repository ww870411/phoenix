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


odex resume 0199f1ca-fa0c-7023-847f-1b45cc2dfb9f

————————————————————————————————————————————————————————————————————————————————————————
10.18
  前端页面与路由                                                                                                                                      
  - login: /login → frontend/src/daily_report_25_26/pages/LoginView.                                                                             
  - projects: /projects → frontend/src/daily_report_25_26/pages/ProjectSelectView.vue
      - dashboard: /projects/:projectKey/sheets → frontend/src/daily_report_25_26/pages/DashboardView.                                      
  - data-entry: /projects/:projectKey/sheets/:sheetKey → frontend/src/daily_report_25_26/pages/DataEntryView.                                  
  - 证据文件：frontend/src/router/index.js  


后端 API（统一前缀 /api/v1）
  - 健康检查
      - GET /healthz（应用生存探针） — backend/main.py                                                                                                  
      - GET /ping（系统连通） — backend/api/v1/routes.py                                                                                                
  - 项目级连通                                                                                                                                       
      - GET /projects/daily_report_25_26/ping — backend/api/v1/daily_report_25_26.py                                                                    
  - 表管理与数据填报（当前代码挂载在项目路径下）                                                                                                        
      - 列出表清单：GET /projects/{project_key}/sheets        
      - 获取模板：GET /projects/{project_key}/sheets/{sheet_key}/template                                                                          
      - 提交数据：POST /projects/{project_key}/sheets/{sheet_key}/submit                                                                          
      - 查询数据：POST /projects/{project_key}/sheets/{sheet_key}/query
      - 证据文件：backend/api/v1/projects_daily_report_25_26.py，挂载于 backend/api/v1/routes.py

  前端调用 API（对应 services）                                                                                                                         
                                                                                                                                                        
  - 列表表清单：GET /api/v1/projects/${projectKey}/sheets                                                                                               
  - 获取模板：GET /api/v1/projects/${projectKey}/sheets/${sheetKey}/template                                                                            
  - 提交数据：POST /api/v1/projects/${projectKey}/sheets/${sheetKey}/submit                                                                             
  - 查询数据：POST /api/v1/projects/${projectKey}/sheets/${sheetKey}/query                                                                              
  - 证据文件：frontend/src/daily_report_25_26/services/api.js            
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  发现一个频繁出现的问题，即前后端的项目代号不同，同时后端api文件夹中的项目路由文件也不止一个，需要统一
  已统一

  配置文件的sheet均改为大写的Sheet
  解决前端访问不到后端正确地址的问题。
  去掉每张表上的“刷新状态”按钮，统一在右上方
  统一表格选择页面的路径为/sheets，/dashboard另有他用，对应的vue文件也改名

  列表清单的处理函数为_read_json