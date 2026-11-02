"""可选 Windows Excel 文件 API 验证；只读打开，绝不保存源文件。

需要本机 Excel 与 pywin32，不属于 Linux 服务运行依赖。
只记录验证数量和不一致坐标，不输出投诉文本或个人资料。
"""
import argparse
import json
from pathlib import Path
from time import perf_counter
from zipfile import ZipFile

from backend.services.excel_optimizer import load_sheets


def validate(source, output, recalculate=False):
    import win32com.client
    import win32process

    with ZipFile(output) as z:
        _, sheets = load_sheets({p: z.read(p) for p in z.namelist()})
    app = win32com.client.DispatchEx('Excel.Application')
    _, pid = win32process.GetWindowThreadProcessId(app.Hwnd)
    print(json.dumps({'excel_pid': pid}), flush=True)
    app.Visible = False
    app.DisplayAlerts = False
    app.EnableEvents = False
    app.AutomationSecurity = 3
    books = []
    report = {'engine': 'Microsoft Excel', 'version': app.Version, 'recalculated': recalculate, 'opening_seconds': {}, 'value_differences': [], 'compared_cells': 0, 'source_error_cells': [], 'output_error_cells': []}
    try:
        snapshots = []
        for label, path in [('source', source), ('output', output)]:
            started = perf_counter()
            # Excel 必须先打开工作簿才能设置 Calculation；首本以只读方式打开。
            book = app.Workbooks.Open(str(path.resolve()), UpdateLinks=0, ReadOnly=True, IgnoreReadOnlyRecommended=True)
            books.append(book)
            app.Calculation = -4135
            report['opening_seconds'][label] = round(perf_counter() - started, 3)
            print(json.dumps({'opened': label, 'seconds': report['opening_seconds'][label]}), flush=True)
            if recalculate:
                app.CalculateFullRebuild()
            snapshot = {}
            for sheet in sheets.values():
                ws = book.Worksheets(sheet.name)
                for address in sheet.formulas:
                    cell = ws.Range(address)
                    snapshot[(sheet.name, address)] = cell.Value2
                    if str(cell.Text) in ('#REF!', '#VALUE!', '#DIV/0!', '#NAME?', '#N/A', '#NUM!', '#NULL!'):
                        report[label + '_error_cells'].append([sheet.name, address, str(cell.Text)])
            snapshots.append(snapshot)
        for key, value in snapshots[0].items():
            report['compared_cells'] += 1
            other = snapshots[1][key]
            if isinstance(value, (int, float)) and isinstance(other, (int, float)):
                equal = abs(value - other) <= max(1e-9, abs(value) * 1e-12)
            else:
                equal = value == other
            if not equal:
                report['value_differences'].append(list(key))
        return report
    finally:
        for book in books:
            book.Close(SaveChanges=False)
        app.Quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='只读比较源工作簿与去冗余副本的 Excel 计算值')
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('--recalculate', action='store_true')
    args = parser.parse_args()
    result = validate(args.source, args.output, args.recalculate)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True), flush=True)
