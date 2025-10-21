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
      - dashboard: /projects/:projectKey/data_entry/sheets → frontend/src/daily_report_25_26/pages/DashboardView.                                      
  - data-entry: /projects/:projectKey/data_entry/sheets/:sheetKey → frontend/src/daily_report_25_26/pages/DataEntryView.                                  
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

  但是，填表页面无法渲染的问题依然存在，gemini的建议是：
  DataEntryView.vue 的实现方式从原生 <revo-grid> 切换为使用 @revolist/vue3-datagrid Vue 组件。这不仅是更推荐的做法，而且很可能会一并解决 CSS 
  样式不加载的问题。
  我将让codex去看看
  codex称建议很好，目前已经可以渲染！

  不断修复渲染中，codex似乎执着于在返回数据中添加顶端的"ok": true，以及在/sheets页面中添加进度显示

  尝试申请了gpt team会员：linuxdo_126628@pu.edu.kg

  在revogrid中，有诸多api参数，还有很多在columns中设置的内容，比如要将某列数据左侧对齐：
  colDefs.push({
    prop: 'c0',
    name: columns.value[0] ?? '项目',
    readonly: true,
    autoSize: true,
    minSize: 160,
    cellProperties: () => ({
      style: { textAlign: 'left' } // 用函数，这里返回对象
      }),
  });



增加“失焦保存”功能，避免必须enter才能保存数据的问题。

codex编写了一份创建数据库表的脚本，待容器启动后执行docker compose exec db psql -U postgres -d phoenix -f /app/sql/create_tables.sql

修复面包屑导航及前端名称的中文显示

开始构建前端向后端发送的数据包，格式同前端从后端请求到的数据包，并添加提交时间

将字典加入基本指标表，并构建前后端传输携带

修复隐患：确认使用绑定挂载路径；修改基本指标表.json过于绝对的全局变量名，改为BASIC_DATA_FILE

去掉项目选择页面中的导航
增加前端填表页面提交数据时附带的 "status":"submit"以及"unit_name"

进行数据初次转换，待写入数据库。但“数据拆解”过程仍存在，需要去除

在后端建立db文件夹，存放SQLALchemy相关文件，包括session，ORM模型。发现数据库中的表名都是小写，对应设定。
程序只有当 company（单位代号）、sheet_name（模板键）、item（项目键）和 date（列对应的业务日期）都取到了有效值时，才会把该记录加入待写入列表。


*将数据采集的相关页面及API全部加入data_entry前缀：
【前端页面清单】
/login                                              不变
/projects                                           不变
/projects/daily_report_25_26/sheets                 改为/projects/daily_report_25_26/data_entry/sheets 
/projects/daily_report_25_26/sheets/{sheet_key}     改为/projects/daily_report_25_26/data_entry/sheets/{sheet_key} 

【API清单】
GET /sheets                          改为GET /data_entry/sheets                
GET /sheets/{sheet_key}/template     改为GET /data_entry/sheets/{key}/template 
POST /sheets/{sheet_key}/submit      改为POST /data_entry/sheets/{key}/submit  
POST /sheets/{sheet_key}/query       改为POST /data_entry/sheets/{key}/query  

修改完毕

实现空值也写入数据库的可追溯业务逻辑。
因为一些Bug，数据库表名全部都是小写

修复使用后端绑定挂载路径时的写法混乱问题，有些位置使用了固定的绝对路径，而没有使用/app/data，未来是一个隐患。
新增 backend/config.py:1-12 定义全局 DATA_DIRECTORY（默认 /app/data，可用环境变量覆盖），成为后端访问数据卷的唯一入口。
取消使用《常量指标表》的兜底行为。

数据库的数据路径也有问题，而且yml文件中写的各类挂载路径还都设置了一个似乎是冗余的全面路径：
# 源码热更新：将整个项目挂载到容器 /app，便于开发时实时生效
      - ./:/app
也要取消

yml中的路径环境变量有什么用？

修正 煤炭库存表的渲染及数据库写表过程。修改后端响应请求时，发送数据包的添加日期（改为键值对），并且修改前端提交数据带有该日期。
数据库表有无，增加了几个项目。
因为自然键设置缺少storage_type的原因，无法成功写库，修改唯一约束后已经实现煤炭库存表的写库过程。


面包屑导航/幂等/唯一约束/删除的筛选依据

模板增加"解释说明"列，并调整本日/同期日写在它们中间，其内容写在note中



codex resume 0199fefc-c0ae-7810-b4fa-079a4c51da72













天气数据的自动获取:
根据查询资料：在FastAPI生态中，通常使用 apscheduler 这样的库，您可以设置一个定时任务（例如 add_job(run_daily_import, 'cron', hour=3, minute=0)），它就会在指定时间自动执行您的代码。

