"""按业务日期直接统计投诉明细，不执行工作簿公式。"""
from collections import Counter
from datetime import date, datetime
from io import BytesIO
import re
from zipfile import ZipFile

from openpyxl.utils.datetime import from_excel, WINDOWS_EPOCH, MAC_EPOCH
from backend.services.excel_optimizer import load_sheets, parse, tag

CENTERS = ('华乐中心', '东港中心', '春海中心', '中山中心', '北岗中心', '双兴中心', '香炉礁中心', '兴工中心', '大纺中心', '管网中心')
SOURCES = ('直办', '转办', '省办')
METRICS = ('daily_city', 'daily_province', 'daily_total', 'daily_net', 'daily_province_net', 'daily_city_net', 'monthly_net', 'season_net', 'unresolved_complaints')


def normalize(value):
    return re.sub(r'\s+', '', str(value or '')).replace('（', '(').replace('）', ')')


def center_name(value):
    name = normalize(value)
    matches = [center for center in CENTERS if name in (center, center.replace('中心', '服务中心'))]
    return matches[0] if len(matches) == 1 else None


def record_date(value, epoch):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            converted = from_excel(value, epoch)
            return converted.date() if isinstance(converted, datetime) else None
        except (ValueError, OverflowError):
            return None
    if isinstance(value, str):
        text = value.strip().replace('年', '-').replace('月', '-').replace('日', ' ')
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return None
    return None


def metrics(records, day, month, season):
    counts = dict.fromkeys(METRICS, 0)
    for row in records:
        current = date.fromisoformat(row['date'])
        source, done = row['source'], row['status'] == '已办结'
        unresolved = row['status'] == '未办结'
        is_complaint = normalize(row.get('type')) == '投诉'
        is_net = source == '转办' and done and is_complaint
        if current == day:
            counts['daily_city'] += source in ('直办', '转办')
            counts['daily_province'] += source == '省办'
            counts['daily_total'] += 1
            counts['daily_net'] += is_net
            counts['daily_city_net'] += is_net
        if is_net:
            counts['monthly_net'] += month <= current <= day
            counts['season_net'] += season <= current <= day
        if source == '转办' and unresolved:
            counts['unresolved_complaints'] += current <= day
    return counts


def calculate(data, business_date):
    try:
        day = date.fromisoformat(business_date)
    except (TypeError, ValueError) as exc:
        raise ValueError('业务日期无效，请选择日期。') from exc
    month = day.replace(day=1)
    season = date(day.year if day.month >= 11 else day.year - 1, 11, 1)
    try:
        with ZipFile(BytesIO(data)) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
        book, sheets = load_sheets(parts)
        strings = [''.join(item.itertext()) for item in parse(parts['xl/sharedStrings.xml'])] if 'xl/sharedStrings.xml' in parts else []
        properties = book.find(tag('workbookPr'))
        epoch = MAC_EPOCH if properties is not None and properties.get('date1904') in ('1', 'true') else WINDOWS_EPOCH
    except Exception as exc:
        raise ValueError('无法读取工作簿，请上传有效的 .xlsx 文件。') from exc
    try:
        selected = {}
        for source in SOURCES:
            matches = [s for s in sheets.values() if re.search(r'[（(]' + source + r'[）)]', s.name)]
            if len(matches) != 1:
                raise ValueError(f'无法唯一识别“{source}”明细表，请检查工作表名称。')
            selected[source] = matches[0]
        records, issues = [], []
        def cell_value(sheet, address):
            cell = sheet.cells.get(address)
            if cell is None:
                return None
            value = cell.findtext(tag('v'))
            if cell.get('t') == 's' and value is not None:
                return strings[int(value)]
            if cell.get('t') == 'inlineStr':
                inline = cell.find(tag('is'))
                return ''.join(inline.itertext()) if inline is not None else None
            if cell.get('t') in ('str', 'e'):
                return value
            if value is None or value == '':
                return None
            try:
                return float(value)
            except ValueError:
                return value
        for source, sheet in selected.items():
            header_found = False
            rows = sorted({int(re.search(r'\d+$', address).group()) for address in sheet.cells if re.fullmatch(r'[BCD]\d+', address)})
            for row_number in rows:
                values = [cell_value(sheet, f'{chr(col)}{row_number}') for col in range(ord('B'), ord('M') + 1)]
                if not header_found:
                    if normalize(values[0]) == '日期' and normalize(values[1]) in ('受理编号', '诉求编号') and normalize(values[8]) == '服务中心' and normalize(values[11]) == '办理情况':
                        header_found = True
                    continue
                identifier = str(values[1]).strip() if values[1] is not None else ''
                if not identifier:
                    if record_date(values[0], epoch) is not None and (values[2] or values[4]):
                        issues.append({'sheet': sheet.name, 'row': row_number, 'reason': '日期和明细内容存在，但编号缺失，未纳入统计'})
                    continue
                date_value = record_date(values[0], epoch)
                if date_value is None:
                    issues.append({'sheet': sheet.name, 'row': row_number, 'reason': '编号存在，但日期为空、无效或公式没有保存计算结果'})
                    continue
                name = str(values[8] or '').strip()
                records.append({'sheet': sheet.name, 'row': row_number, 'source': source, 'date': date_value.isoformat(), 'identifier': identifier, 'type': str(values[2] or '').strip(), 'category': str(values[7] or '').strip(), 'center_original': name, 'center': center_name(name), 'status': normalize(values[11])})
            if not header_found:
                raise ValueError(f'工作表“{sheet.name}”未找到符合要求的明细表头。')
        grouped = {name: [] for name in CENTERS}
        unmatched = []
        for record in records:
            (grouped[record['center']] if record['center'] else unmatched).append(record)
        return {'business_date': day.isoformat(), 'month_start': month.isoformat(), 'season_start': season.isoformat(), 'group': metrics(records, day, month, season), 'centers': [{'name': name, 'metrics': metrics(grouped[name], day, month, season)} for name in CENTERS], 'unmatched': {'metrics': metrics(unmatched, day, month, season), 'names': dict(Counter(r['center_original'] or '未填写' for r in unmatched)), 'count': len(unmatched)}, 'records': records, 'issues': issues, 'complete': not issues, 'sheets': {key: value.name for key, value in selected.items()}}
    finally:
        pass
