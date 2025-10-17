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