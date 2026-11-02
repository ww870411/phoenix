"""投诉指标口径、跨年日期及异常明细回归测试。"""
from datetime import datetime
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook
import pytest

from backend.projects.daily_report_25_26.services.complaint_statistics import calculate, CENTERS
from backend.projects.daily_report_25_26.api.complaint_optimizer import router
from backend.services.auth_manager import get_current_session


def sample():
    book = Workbook()
    book.remove(book.active)
    sheets = {}
    for source in ('直办', '转办', '省办'):
        sheet = book.create_sheet('明细（' + source + '）')
        sheet.append(['序号', '日期', '受理编号', '分类', '电话', '内容', '回复', '地址', '投诉类别', '服务中心', '所属所', '站', '办理情况'])
        sheets[source] = sheet
    def add(source, date, number, center, status):
        sheets[source].append([None, date, number, '咨询', None, '内容', None, None, '类型', center, None, None, status])
    add('直办', datetime(2027, 2, 10, 23, 59), 'D1', '华乐服务中心', '已办结')
    add('转办', datetime(2027, 2, 10, 8), 'T1', '华乐中心', '已办结')
    add('转办', datetime(2027, 2, 10, 9), 'T2', '其他部门', '撤件')
    add('转办', datetime(2027, 2, 1), 'T3', '东港服务中心', '已办结')
    add('转办', datetime(2026, 11, 1), 'T4', '东港中心', '已办结')
    add('转办', datetime(2026, 10, 31), 'T5', '东港中心', '已办结')
    add('转办', datetime(2027, 2, 11), 'T6', '东港中心', '已办结')
    add('省办', datetime(2027, 2, 10), 'P1', '华乐中心', '已办结')
    data = BytesIO()
    book.save(data)
    return data.getvalue()


def test_metrics_and_reconciliation():
    result = calculate(sample(), '2027-02-10')
    assert result['month_start'] == '2027-02-01'
    assert result['season_start'] == '2026-11-01'
    assert result['group'] == {'daily_city': 3, 'daily_province': 1, 'daily_total': 4, 'daily_net': 1, 'daily_province_net': 0, 'daily_city_net': 1, 'monthly_net': 2, 'season_net': 3}
    assert [c['name'] for c in result['centers']] == list(CENTERS)
    assert result['centers'][0]['metrics']['daily_total'] == 3
    assert result['unmatched']['metrics']['daily_total'] == 1
    for key, value in result['group'].items():
        assert sum(c['metrics'][key] for c in result['centers']) + result['unmatched']['metrics'][key] == value
    assert result['complete']


def test_missing_cached_date_is_reported():
    book = Workbook()
    book.remove(book.active)
    for source in ('直办', '转办', '省办'):
        sheet = book.create_sheet('明细（' + source + '）')
        sheet.append(['序号', '日期', '受理编号', '分类', '电话', '内容', '回复', '地址', '投诉类别', '服务中心', '所属所', '站', '办理情况'])
        if source == '转办':
            sheet.append([1, '=NOW()', 'T1', '投诉', None, '内容', None, None, None, '华乐中心', None, None, '已办结'])
    out = BytesIO()
    book.save(out)
    result = calculate(out.getvalue(), '2026-11-15')
    assert not result['complete'] and result['issues'][0]['row'] == 2
    assert result['group']['daily_total'] == 0


def test_missing_sheet_and_invalid_date():
    with pytest.raises(ValueError):
        calculate(sample(), '2027-02-30')
    book = Workbook()
    output = BytesIO()
    book.save(output)
    with pytest.raises(ValueError, match='无法唯一识别'):
        calculate(output.getvalue(), '2027-02-10')


def test_http_endpoint():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_session] = lambda: object()
    with TestClient(app) as client:
        response = client.post('/data_entry/complaints/statistics', data={'biz_date': '2027-02-10'}, files={'file': ('report.xlsx', sample())})
        assert response.status_code == 200
        assert response.json()['data']['group']['season_net'] == 3
