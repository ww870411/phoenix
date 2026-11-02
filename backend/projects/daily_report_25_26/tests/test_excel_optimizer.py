"""覆盖空公式、独立区域、跨表依赖、引用语义和上传下载协议。"""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import base64

from fastapi import FastAPI
from fastapi.testclient import TestClient
from lxml import etree as ET
from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.table import Table
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule
import pytest

from backend.services.excel_optimizer import (
    NS, blank_excluded, clip_ranges, formula_tokens, load_sheets,
    optimize_formula, optimize_workbook, parse, serialize, split_reference, tag,
)
from backend.projects.daily_report_25_26.api.complaint_optimizer import router
from backend.services.auth_manager import get_current_session


def fixture_bytes(extra=None):
    book = Workbook()
    sheet = book.active
    sheet.title = '明细'
    sheet.append(['序号', '日期', '记录'])
    sheet['C2'] = '有效投诉'
    for row in range(2, 42):
        sheet[f'B{row}'] = f'=IF(C{row}<>"",IF(B{row}<>"",B{row},NOW()),"")'
        sheet[f'A{row}'] = f'=IF(B{row}="","",A{row-1}+1)'
    sheet['G1000'] = '独立统计'
    sheet['H1000'] = '=SUM(A2:A41)'
    sheet['G2000'].number_format = '0.00'
    sheet['K1'] = '=COUNTIFS(C:C,"有效投诉")'
    sheet.add_table(Table(displayName='Records', ref='A1:C1047839'))
    validation = DataValidation(type='list', formula1='"已办结,未办结"')
    validation.add('C2:C8000')
    sheet.add_data_validation(validation)
    sheet.conditional_formatting.add('C2:C8000', CellIsRule(operator='equal', formula=['1']))
    sheet.merge_cells('G1000:G1001')
    if extra:
        extra(book)
    out = BytesIO()
    book.save(out)
    with ZipFile(BytesIO(out.getvalue())) as z:
        parts = {p: z.read(p) for p in z.namelist()}
    root = parse(parts['xl/worksheets/sheet1.xml'])
    for c in root.findall('s:sheetData/s:row/s:c', NS):
        if c.find(tag('f')) is not None:
            v = c.find(tag('v'))
            if c.get('r') in ('A2', 'B2'):
                v.text = '1' if c.get('r') == 'A2' else '46000.5'
            else:
                c.set('t', 'str')
    parts['xl/worksheets/sheet1.xml'] = serialize(root)
    # 不认识的扩展对象也必须逐字节保留。
    parts['customXml/item1.xml'] = b'<kept>opaque</kept>'
    out = BytesIO()
    with ZipFile(out, 'w', ZIP_DEFLATED) as z:
        for p, value in parts.items():
            z.writestr(p, value)
    return out.getvalue()


def test_cleanup_preserves_values_formulas_objects_and_cache():
    original = fixture_bytes()
    result, report = optimize_workbook(original)
    book = load_workbook(BytesIO(result))
    sheet = book['明细']
    assert sheet['C2'].value == '有效投诉'
    assert sheet['B2'].value.startswith('=IF(')
    assert sheet['A3'].value is None and sheet['B3'].value is None
    assert sheet['G1000'].value == '独立统计'
    assert sheet['H1000'].value == '=SUM(A$2:A$2)'
    assert sheet['G2000'].has_style is False
    assert 'G1000:G1001' in sheet.merged_cells
    assert sheet.tables['Records'].ref == 'A1:C2'
    assert str(sheet.data_validations.dataValidation[0].sqref) == 'C2'
    assert str(next(iter(sheet.conditional_formatting)).sqref) == 'C2'
    assert load_workbook(BytesIO(result), data_only=True)['明细']['B2'].value == 46000.5
    assert report['formulas_removed'] == 78
    assert report['recalculated'] is False
    with ZipFile(BytesIO(result)) as z:
        assert z.read('customXml/item1.xml') == b'<kept>opaque</kept>'


def test_empty_formatted_rows_are_removed_without_shifting_later_content():
    def extra(book):
        sheet = book.active
        sheet['C500'].number_format = '0.00'
        sheet.row_dimensions[500].height = 25
        sheet['G1500'] = '后方独立内容'
    result, report = optimize_workbook(fixture_bytes(extra))
    with ZipFile(BytesIO(result)) as archive:
        _, sheets = load_sheets({name: archive.read(name) for name in archive.namelist()})
    sheet = sheets['明细']
    assert 'C500' not in sheet.cells
    assert sheet.root.find("s:sheetData/s:row[@r='500']", NS) is None
    assert 'G1500' in sheet.cells
    assert report['sheets'][0]['empty_rows_removed'] > 0


def test_referenced_whitespace_is_preserved():
    def extra(book):
        book.active['C500'] = '  '
        book.active['J1'] = '=C500'
    result, _ = optimize_workbook(fixture_bytes(extra))
    assert load_workbook(BytesIO(result)).active['C500'].value == '  '


@pytest.mark.parametrize('consumer', ['=ISBLANK(B41)', '=COUNTA(B1:B41)', '=B41'])
def test_blank_sensitive_references_protect_formula(consumer):
    result, _ = optimize_workbook(fixture_bytes(lambda b: b.active.__setitem__('L1', consumer)))
    assert load_workbook(BytesIO(result)).active['B41'].value is not None


def test_cross_sheet_reference_and_name_protect_formula():
    def extra(b):
        b.create_sheet('汇总')['A1'] = "='明细'!B41"
    result, _ = optimize_workbook(fixture_bytes(extra))
    assert load_workbook(BytesIO(result))['明细']['B41'].value is not None


@pytest.mark.parametrize('consumer', ['=INDIRECT("B41")', '=OFFSET(B2,39,0)', '=SomeName'])
def test_dynamic_or_unknown_references_keep_candidates(consumer):
    result, report = optimize_workbook(fixture_bytes(lambda b: b.active.__setitem__('L1', consumer)))
    assert report['formulas_removed'] == 0
    assert load_workbook(BytesIO(result)).active['B41'].value is not None


@pytest.mark.parametrize('formula,expected', [
    ('COUNTIFS(B:B,"已办结")', 'COUNTIFS(B$1:B$12,"已办结")'),
    ('COUNTIFS(B:B,"")', 'COUNTIFS(B:B,"")'),
    ('COUNTIFS(B:B,0)', 'COUNTIFS(B:B,0)'),
    ('COUNTIFS(B:B,"<="&NOW())', 'COUNTIFS(B:B,"<="&NOW())'),
    ('COUNTIFS(B:B,">="&TODAY())', 'COUNTIFS(B$1:B$12,">="&TODAY())'),
    ('SUM($B:$B)', 'SUM($B$1:$B$12)'),
    ('SUM(B2:B8000)', 'SUM(B$2:B$12)'),
    ('COUNTA(B:B)', 'COUNTA(B:B)'),
    ('ROW(B:B)', 'ROW(B:B)'),
    ('MATCH(0,B:B,0)', 'MATCH(0,B:B,0)'),
    ('"B:B"', '"B:B"'),
    ('COUNTIFS(B:B,"*",C:C,"已办结")', 'COUNTIFS(B$1:B$12,"*",C$1:C$12,"已办结")'),
])
def test_formula_semantics(formula, expected):
    optimized, _ = optimize_formula(formula, '明细', {'明细': {2: 12, 3: 4}})
    assert optimized == expected


def test_sumproduct_preserves_strings_and_uniform_bounds():
    formula = 'SUMPRODUCT(--(TEXT(B:B,"yyyy-mm-dd")>=TEXT(P46,"yyyy-mm-dd")),--(J:J="春海服务中心"),--ISNUMBER(MATCH(M:M,{"已办结","撤件"},0)))'
    optimized, count = optimize_formula(formula, '明细', {'明细': {2: 36, 10: 20, 13: 10, 16: 46}})
    assert count == 3
    assert 'B$1:B$36' in optimized and 'J$1:J$36' in optimized and 'M$1:M$36' in optimized
    assert 'P46' in optimized and '"春海服务中心"' in optimized
    unsafe = 'SUMPRODUCT(1/B:B,--(J:J="分类"))'
    assert optimize_formula(unsafe, '明细', {'明细': {2: 36, 10: 20}})[0] == unsafe


def test_repeated_upload_independent_and_idempotent():
    original = fixture_bytes()
    result, report = optimize_workbook(original)
    second, r2 = optimize_workbook(result)
    assert r2['formulas_removed'] == 0
    assert r2['constants_verified'] == report['constants_verified']
    assert load_workbook(BytesIO(second)).active['C2'].value == '有效投诉'


def test_if_guard_does_not_mistake_nested_else_for_blank():
    def extra(b):
        for row in range(2, 42):
            b.active[f'D{row}'] = f'=IF(C{row}<>"",1,IF(E{row}=1,2,""))'
    result, _ = optimize_workbook(fixture_bytes(extra))
    assert load_workbook(BytesIO(result)).active['D41'].value is not None


@pytest.mark.parametrize('value', [b'', b'not an excel file'])
def test_invalid_workbook(value):
    with pytest.raises(ValueError, match='无法处理'):
        optimize_workbook(value)


def test_upload_download_contract_and_authentication():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        assert client.post('/data_entry/complaints/optimize', files={'file': ('a.xlsx', b'bad')}).status_code == 401
        app.dependency_overrides[get_current_session] = lambda: object()
        assert client.post('/data_entry/complaints/optimize', files={'file': ('a.xls', b'bad')}).status_code == 400
        assert client.post('/data_entry/complaints/optimize', files={'file': ('a.xlsx', b'bad')}).status_code == 400
        response = client.post('/data_entry/complaints/optimize', files={'file': ('测试.xlsx', fixture_bytes())})
        assert response.status_code == 200
        payload = response.json()
        assert payload['filename'] == '测试_去冗余.xlsx'
        assert load_workbook(BytesIO(base64.b64decode(payload['file_base64']))).active['C2'].value == '有效投诉'


def test_real_sample():
    sample = Path(__file__).resolve().parents[4] / 'configs/2026-2027年度市12345诉求件统计表.xlsx'
    if not sample.exists():
        pytest.skip('样本由用户本地提供，不随代码提交')
    original = sample.read_bytes()
    optimized, report = optimize_workbook(original)
    assert len(report['sheets']) == 5
    assert report['formulas_removed'] > 47000
    assert report['output_bytes'] < report['input_bytes'] * 0.2
    assert report['references_optimized'] > 500
    with ZipFile(BytesIO(optimized)) as archive:
        _, sheets = load_sheets({name: archive.read(name) for name in archive.namelist()})
        items = list(sheets.values())
        assert 'L8012' not in items[1].cells
        assert items[1].root.find("s:sheetData/s:row[@r='500']", NS) is None
        xfs = parse(archive.read('xl/styles.xml')).find(tag('cellXfs'))
        for sheet in items[1:3]:
            for col in sheet.root.findall('s:cols/s:col', NS):
                if col.get('style') is not None:
                    assert xfs[int(col.get('style'))].get('borderId', '0') == '0'
            for cf in sheet.root.findall('s:conditionalFormatting', NS):
                assert '1048576' not in cf.get('sqref', '')
        assert parse(archive.read('xl/tables/table1.xml')).get('ref') == 'A1:M16'
        assert 'R16' in items[2].formulas
    assert all(s['formulas_removed'] == 0 for s in report['sheets'][3:])
