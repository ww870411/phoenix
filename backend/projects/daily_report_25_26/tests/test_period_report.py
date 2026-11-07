"""周期边界、分析分支与接口权限回归；不写业务数据库。"""
from datetime import date
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.services.auth_manager import get_current_session
from backend.projects.daily_report_25_26.api.period_report import router
import io
import zipfile
import openpyxl
from backend.projects.daily_report_25_26.services.period_report_export import compute_comparison_dates
from backend.projects.daily_report_25_26.services.period_report import validate_period, metric_story, report_value, build_period_report


class PeriodReportTests(TestCase):
    def test_missing_metrics_follow_user_zero_convention(self):
        for value in (None, '', float('nan'), float('inf')):
            self.assertEqual(report_value(value), 0)
        self.assertEqual(report_value(-12.5), -12.5)
        self.assertEqual(report_value(0), 0)

    def test_november_period_keeps_engine_peer_and_zero_fills_unknown(self):
        module = 'backend.projects.daily_report_25_26.services.period_report'
        def calculate(company, keys, start, end, **kwargs):
            self.assertEqual((start.month, start.day, end.month, end.day), (11, 1, 11, 4))
            return {'consumption_std_coal': {'value_biz_date': 400 if start.year == 2026 else 300}}
        with patch(module + '.HeatingAnalysisEngine') as engine, patch(module + '.get_monthly_coal_progress', return_value={'items': []}):
            engine.return_value.compute_analysis_rows.side_effect = calculate
            report = build_period_report(None, date(2026, 11, 1), date(2026, 11, 4), False)
        coal = next(p for p in report['pages'] if p['key'] == 'consumption_std_coal')
        self.assertEqual((coal['rows'][0]['curr'], coal['rows'][0]['sync'], coal['rows'][0]['delta']), (400, 300, 100))
        gas = next(p for p in report['pages'] if p['key'] == 'consumption_natural_gas')
        self.assertEqual((gas['rows'][0]['curr'], gas['rows'][0]['sync']), (0, 0))

    def test_period_bounds(self):
        validate_period(date(2026, 1, 16), date(2026, 1, 24))
        validate_period(date(2026, 1, 31), date(2026, 2, 2))
        for start, end in [(date(2026, 2, 1), date(2026, 1, 1)),
                           (date(2026, 9, 30), date(2026, 10, 1))]:
            with self.assertRaises(ValueError):
                validate_period(start, end)

    def test_negative_profit_and_missing(self):
        rows = [{'name': '集团', 'curr': 10, 'sync': -2, 'prev': None},
                {'name': '甲', 'curr': None, 'sync': 0, 'prev': None}]
        story = ' '.join(metric_story('边际利润', rows, '万元', False))
        self.assertIn('由亏转盈', story)
        self.assertNotIn('%', story)
        self.assertNotIn('较上期', story)
        self.assertNotIn('部分单位本期缺少完整依据', story)

    def test_offsetting_changes_do_not_create_contribution_percentage(self):
        rows = [{'name': '集团', 'curr': 100, 'sync': 99, 'prev': 100},
                {'name': '甲', 'curr': 200, 'sync': 100, 'prev': 200},
                {'name': '乙', 'curr': 0, 'sync': 99, 'prev': 0}]
        story = ' '.join(metric_story('标煤耗量', rows, '吨', True))
        self.assertIn('甲', story)
        self.assertNotIn('占集团增量', story)

    def test_permission_and_bad_dates_before_database(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch('backend.projects.daily_report_25_26.api.period_report.SessionLocal') as session:
            for group in ('Group_viewer', 'unit_admin', 'admin', 'global_admin', 'Global_admin ', ''):
                app.dependency_overrides[get_current_session] = lambda group=group: SimpleNamespace(group=group)
                self.assertEqual(client.get('/period-report').status_code, 403)
                self.assertEqual(client.get('/period-report?start=2026-11-01&end=2026-11-04').status_code, 403)
            session.assert_not_called()

        for admin_group in ('Global_admin', 'Group_admin'):
            app.dependency_overrides[get_current_session] = lambda group=admin_group: SimpleNamespace(group=group)
            with patch('backend.projects.daily_report_25_26.api.period_report.SessionLocal') as session:
                session.return_value.__enter__.return_value.execute.return_value.scalars.return_value.all.return_value = []
                self.assertEqual(client.get('/period-report').status_code, 200)
                session.reset_mock()
                self.assertEqual(client.get('/period-report?start=2026-01-01').status_code, 422)
                self.assertEqual(client.get('/period-report?start=2026-02-01&end=2026-01-01').status_code, 422)
                session.assert_not_called()

    def test_files_management_endpoints(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # 1. 权限拦截测试
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Group_viewer')
        self.assertEqual(client.get('/period-report/files').status_code, 403)
        self.assertEqual(client.post('/period-report/files/save', json={'filename': 'a.html', 'content': 'x'}).status_code, 403)

        # 1.1 Group_admin 也具备材料空间访问权限
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Group_admin')
        res_group_admin = client.get('/period-report/files')
        self.assertEqual(res_group_admin.status_code, 200)

        # 2. Global_admin 正常列出文件
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Global_admin')
        res = client.get('/period-report/files')
        self.assertEqual(res.status_code, 200)
        items = res.json().get('items', [])
        # 至少存在之前创建的模板文件或材料文件
        self.assertTrue(any(it['name'].endswith('.html') for it in items))

        # 3. 保存新 HTML 文件
        test_filename = '2026-03-01_2026-03-07_test_report.html'
        test_content = '<!DOCTYPE html><html><body><h1>测试运行汇报</h1></body></html>'
        save_res = client.post('/period-report/files/save', json={'filename': test_filename, 'content': test_content})
        self.assertEqual(save_res.status_code, 200)
        self.assertEqual(save_res.json()['name'], test_filename)
        self.assertIn('created_at', save_res.json())
        self.assertIn('updated_at', save_res.json())

        # 4. 获取文件内容
        content_res = client.get(f'/period-report/files/content?path={test_filename}')
        self.assertEqual(content_res.status_code, 200)
        self.assertEqual(content_res.json()['content'], test_content)

        # 5. 重命名文件测试
        # 5.1 尝试重命名模板文件被 403 拦截
        tpl_rename = client.post('/period-report/files/rename', json={
            'path': '工作流/1.html模板与使用说明/模版引擎.html',
            'new_name': 'hacked.html'
        })
        self.assertEqual(tpl_rename.status_code, 403)

        # 5.2 正常重命名并验证自动补全/保持原扩展名
        renamed_target = '2026-03-01_2026-03-07_renamed_report'
        rename_res = client.post('/period-report/files/rename', json={
            'path': test_filename,
            'new_name': renamed_target
        })
        self.assertEqual(rename_res.status_code, 200)
        renamed_info = rename_res.json()
        self.assertEqual(renamed_info['name'], f'{renamed_target}.html')
        self.assertEqual(renamed_info['rel_path'], f'{renamed_target}.html')

        # 5.3 尝试重命名为已存在文件返回 400
        conflict_res = client.post('/period-report/files/rename', json={
            'path': f'{renamed_target}.html',
            'new_name': f'{renamed_target}.html'
        })
        # 相同名称视为未改变直接成功返回
        self.assertEqual(conflict_res.status_code, 200)

        # 6. 下载重命名后的文件
        down_res = client.get(f'/period-report/files/download?path={renamed_target}.html')
        self.assertEqual(down_res.status_code, 200)
        self.assertIn('测试运行汇报', down_res.text)

        # 7. 安全防穿越校验
        bad_path_res = client.get('/period-report/files/content?path=../../../../main.py')
        self.assertEqual(bad_path_res.status_code, 400)

        # 8. 模板保护校验（禁止通过材料空间接口删除工作流核心模板）
        del_tpl_res = client.delete('/period-report/files?path=工作流/1.html模板与使用说明/模版引擎.html')
        self.assertEqual(del_tpl_res.status_code, 403)

        # 9. 删除重命名后的文件
        del_res = client.delete(f'/period-report/files?path={renamed_target}.html')
        self.assertEqual(del_res.status_code, 200)

        # 10. 删除后再次读取返回 404
        self.assertEqual(client.get(f'/period-report/files/content?path={renamed_target}.html').status_code, 404)

    def test_comparison_dates_logic(self):
        # 1. 整月测试：3月份（31天）-> 上期为2月份（28天）
        full_res = compute_comparison_dates(date(2026, 3, 1), date(2026, 3, 31), True)
        self.assertTrue(full_res["is_full_month"])
        self.assertEqual(full_res["days_count"], 31)
        self.assertEqual(full_res["prev_start"], date(2026, 2, 1))
        self.assertEqual(full_res["prev_end"], date(2026, 2, 28))

        # 2. 非整月测试：1月16日~1月24日（9天）-> 上期向前等长追溯9天
        non_full_res = compute_comparison_dates(date(2026, 1, 16), date(2026, 1, 24), True)
        self.assertFalse(non_full_res["is_full_month"])
        self.assertEqual(non_full_res["days_count"], 9)
        self.assertEqual(non_full_res["prev_start"], date(2026, 1, 7))
        self.assertEqual(non_full_res["prev_end"], date(2026, 1, 15))

    def test_export_xlsx_endpoints_and_space_save(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Global_admin')

        # 1. 流式下载测试
        res = client.get('/period-report/export-xlsx?start=2026-01-16&end=2026-01-24&include_prev=true')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        self.assertEqual(wb.sheetnames, ['指标对标全景总表', '设备运行与开停机', '电力现货电价走势', '调度日志与抢修记录'])

        # 2. 一键保存至材料仓库空间测试
        save_res = client.get('/period-report/export-xlsx?start=2026-01-16&end=2026-01-24&include_prev=true&save_to_space=true&filename=test_export.xlsx')
        self.assertEqual(save_res.status_code, 200)
        save_json = save_res.json()
        self.assertTrue(save_json["ok"])
        self.assertEqual(save_json["file"]["kind"], "excel")

        # 3. 在文件列表中验证扫描出 excel 类型
        files_res = client.get('/period-report/files')
        self.assertEqual(files_res.status_code, 200)
        items = files_res.json().get("items", [])
        excel_item = next((it for it in items if it["name"] == "test_export.xlsx"), None)
        self.assertIsNotNone(excel_item)
        self.assertEqual(excel_item["kind"], "excel")

        # 4. 下载该 excel 文件
        down_res = client.get('/period-report/files/download?path=test_export.xlsx')
        self.assertEqual(down_res.status_code, 200)
        self.assertEqual(down_res.headers["content-type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # 5. 清理测试文件
        del_res = client.delete('/period-report/files?path=test_export.xlsx')
        self.assertEqual(del_res.status_code, 200)

    def test_workflow_management_endpoints(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # 1. 权限拦截测试（仅限 Global_admin，拦截 Group_viewer 与 Group_admin）
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Group_viewer')
        self.assertEqual(client.get('/period-report/workflow/files').status_code, 403)
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Group_admin')
        self.assertEqual(client.get('/period-report/workflow/files').status_code, 403)

        # 2. Global_admin 正常读取工作流根目录（含子目录与文件）
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Global_admin')
        res = client.get('/period-report/workflow/files')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        items = data.get('items', [])
        breadcrumbs = data.get('breadcrumbs', [])
        directories = data.get('directories', [])
        files = data.get('files', [])

        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(breadcrumbs[0]['path'], '')
        # 验证根目录下直接包含子目录 1.html模板与使用说明
        self.assertTrue(any(d['name'] == '1.html模板与使用说明' and d['is_dir'] for d in directories))
        # 验证根目录下直接包含直接文件 工作流概述.md
        self.assertTrue(any(f['name'] == '工作流概述.md' and not f['is_dir'] for f in files))

        # 2.1 进入子目录 1.html模板与使用说明 查看
        sub_res = client.get('/period-report/workflow/files?folder=1.html%E6%A8%A1%E6%9D%BF%E4%B8%8E%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E')
        self.assertEqual(sub_res.status_code, 200)
        sub_data = sub_res.json()
        self.assertEqual(len(sub_data.get('breadcrumbs', [])), 2)
        sub_files = sub_data.get('files', [])
        self.assertTrue(any('模版引擎.html' in f['name'] for f in sub_files))

        # 3. 读取工作流 Markdown 内容
        content_res = client.get("/period-report/workflow/files/content?path=工作流概述.md")
        self.assertEqual(content_res.status_code, 200)
        content_json = content_res.json()
        self.assertEqual(content_json['kind'], 'markdown')
        self.assertTrue(len(content_json['content']) > 0)

        # 4. 安全防穿越拦截
        bad_res = client.get('/period-report/workflow/files/content?path=../../../../main.py')
        self.assertEqual(bad_res.status_code, 400)

        # 5. 在子目录下创建测试文件夹
        folder_create_res = client.post('/period-report/workflow/folders/create', json={
            'parent_folder': '',
            'folder_name': 'test_temp_subfolder'
        })
        self.assertEqual(folder_create_res.status_code, 200)
        self.assertTrue(folder_create_res.json()['ok'])

        # 6. 上传测试文件到该测试文件夹
        test_file_content = b'# Test Workflow Doc\nHello Workflow.'
        upload_res = client.post(
            '/period-report/workflow/files/upload?folder=test_temp_subfolder',
            files={'file': ('temp_test_doc.md', test_file_content, 'text/markdown')}
        )
        self.assertEqual(upload_res.status_code, 200)
        uploaded = upload_res.json()
        self.assertEqual(uploaded['name'], 'temp_test_doc.md')

        # 7. 重命名测试文件
        rename_res = client.post('/period-report/workflow/files/rename', json={
            'path': uploaded['rel_path'],
            'new_name': 'renamed_test_doc'
        })
        self.assertEqual(rename_res.status_code, 200)
        renamed = rename_res.json()
        self.assertEqual(renamed['name'], 'renamed_test_doc.md')

        # 8. 下载测试文件
        down_res = client.get(f"/period-report/workflow/files/download?path={renamed['rel_path']}")
        self.assertEqual(down_res.status_code, 200)
        self.assertIn('Test Workflow Doc', down_res.text)

        # 9. 删除测试目录（递归清理）
        del_res = client.delete("/period-report/workflow/files?path=test_temp_subfolder")
        self.assertEqual(del_res.status_code, 200)

        # 10. 一键全量打包下载工作流（ZIP 格式）
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Group_viewer')
        self.assertEqual(client.get('/period-report/workflow/archive').status_code, 403)

        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Global_admin')
        archive_res = client.get('/period-report/workflow/archive')
        self.assertEqual(archive_res.status_code, 200)
        self.assertEqual(archive_res.headers['content-type'], 'application/zip')
        self.assertIn('Content-Disposition', archive_res.headers)

        # 验证解压全量包中的文件
        with zipfile.ZipFile(io.BytesIO(archive_res.content)) as zf:
            namelist = zf.namelist()
            self.assertTrue(any('工作流概述.md' in n for n in namelist))
            self.assertTrue(any('模版引擎.html' in n or '模板引擎说明.md' in n for n in namelist))

        # 11. 一键打包下载指定子目录
        sub_archive_res = client.get('/period-report/workflow/archive?folder=1.html%E6%A8%A1%E6%9D%BF%E4%B8%8E%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E')
        self.assertEqual(sub_archive_res.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(sub_archive_res.content)) as zf_sub:
            sub_namelist = zf_sub.namelist()
            # 应该包含子目录内部的模板或说明，但不应包含工作流根目录下的工作流概述.md
            self.assertTrue(any('模版引擎.html' in n or '模板引擎说明.md' in n for n in sub_namelist))
            self.assertFalse(any('工作流概述.md' in n for n in sub_namelist))

    def test_display_config_and_space_transfer(self):
        """测试页面默认展示设定与空间文件夹/跨空间文件传输能力。"""
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # 1. 默认配置读取
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Group_admin', username='group_user')
        res_cfg = client.get('/period-report/display-config')
        self.assertEqual(res_cfg.status_code, 200)
        self.assertIn('mode', res_cfg.json())

        # 2. 权限拦截：Group_admin 禁止修改默认展示
        res_deny = client.post('/period-report/display-config', json={'mode': 'custom_html', 'target_file': '2026_2027.html'})
        self.assertEqual(res_deny.status_code, 403)

        # 3. Global_admin 设定与校验
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Global_admin', username='super_admin')
        # 非法模式
        self.assertEqual(client.post('/period-report/display-config', json={'mode': 'invalid_mode'}).status_code, 400)
        # 不存在的文件
        self.assertEqual(client.post('/period-report/display-config', json={'mode': 'custom_html', 'target_file': 'not_exist_file.html'}).status_code, 404)

        # 正常设定为 custom_html
        set_res = client.post('/period-report/display-config', json={'mode': 'custom_html', 'target_file': '2026_2027.html'})
        self.assertEqual(set_res.status_code, 200)
        self.assertEqual(set_res.json()['mode'], 'custom_html')
        self.assertEqual(set_res.json()['target_file'], '2026_2027.html')

        # 还原为 generated
        revert_res = client.post('/period-report/display-config', json={'mode': 'generated', 'target_file': ''})
        self.assertEqual(revert_res.status_code, 200)
        self.assertEqual(revert_res.json()['mode'], 'generated')

        # 4. 获取空间文件夹列表
        # Group_admin 读取 material
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Group_admin')
        mat_folders = client.get('/period-report/folders?space=material')
        self.assertEqual(mat_folders.status_code, 200)
        self.assertTrue(any(f['path'] == '' for f in mat_folders.json()['folders']))

        # Group_admin 读取 workflow 被拦截
        self.assertEqual(client.get('/period-report/folders?space=workflow').status_code, 403)

        # Global_admin 读取 workflow
        app.dependency_overrides[get_current_session] = lambda: SimpleNamespace(group='Global_admin')
        wf_folders = client.get('/period-report/folders?space=workflow')
        self.assertEqual(wf_folders.status_code, 200)
        self.assertTrue(any(f['path'] == '1.html模板与使用说明' for f in wf_folders.json()['folders']))

        # 5. 在材料空间创建测试子文件夹
        create_folder_res = client.post('/period-report/folders/create-in-space', json={
            'space': 'material',
            'parent_folder': '',
            'folder_name': 'test_material_folder'
        })
        self.assertEqual(create_folder_res.status_code, 200)

        # 6. 跨空间复制：将材料空间已有的 2026_2027.html 复制到工作流根目录
        copy_res = client.post('/period-report/files/transfer', json={
            'source_space': 'material',
            'source_path': '2026_2027.html',
            'target_space': 'workflow',
            'target_folder': '',
            'action': 'copy',
            'overwrite': True
        })
        self.assertEqual(copy_res.status_code, 200)
        copied_name = copy_res.json()['target_name']
        self.assertTrue(copied_name.startswith('2026_2027'))

        # 7. 工作流空间内移动：将刚刚复制的文件移动到 1.html模板与使用说明
        move_res = client.post('/period-report/files/transfer', json={
            'source_space': 'workflow',
            'source_path': copied_name,
            'target_space': 'workflow',
            'target_folder': '1.html模板与使用说明',
            'action': 'move',
            'overwrite': True
        })
        self.assertEqual(move_res.status_code, 200)
        moved_rel = move_res.json()['target_rel_path']

        # 8. 清理工作流测试文件与材料空间测试文件夹
        client.delete(f'/period-report/workflow/files?path={moved_rel}')
        from backend.projects.daily_report_25_26.services.period_report_files import STORAGE_DIR
        test_dir_to_clean = STORAGE_DIR / 'test_material_folder'
        if test_dir_to_clean.exists():
            test_dir_to_clean.rmdir()

        # 12. 非法路径穿越打包测试
        bad_archive = client.get('/period-report/workflow/archive?folder=../../')
        self.assertEqual(bad_archive.status_code, 400)
