"""Excel 当前快照去冗余：在 OOXML 包内局部编辑，保留缓存及未知对象。

不移动单元格，不修改业务条件，不执行公式。无法证明可删/可缩的内容保留。
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from bisect import bisect_left, bisect_right
from copy import deepcopy
from dataclasses import dataclass, field
from io import BytesIO
import posixpath
import re
from time import perf_counter
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED

from lxml import etree as ET
from openpyxl.formula import Tokenizer
from openpyxl.formula.translate import Translator
from openpyxl.utils.cell import range_boundaries, get_column_letter

MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS = {'s': MAIN}
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
SAFE_BLANK = {'SUM', 'COUNT', 'SUMIF', 'SUMIFS', 'COUNTIF', 'COUNTIFS', 'COUNTBLANK'}
CELL = re.compile(r'^\$?([A-Z]{1,3})\$?(\d+)$')
COL_RANGE = re.compile(r'^(\$?[A-Z]{1,3}):(\$?[A-Z]{1,3})$')
GUARD_EQUAL = re.compile(r'^IF\(\s*(\$?[A-Z]{1,3}\$?\d+)\s*=\s*""\s*,\s*""\s*,', re.I)
GUARD_NOT_EQUAL = re.compile(r'^IF\(\s*(\$?[A-Z]{1,3}\$?\d+)\s*<>\s*""\s*,', re.I)


def tag(name):
    return f'{{{MAIN}}}{name}'


def parse(data):
    return ET.fromstring(data, ET.XMLParser(resolve_entities=False, no_network=True))


def serialize(root):
    return ET.tostring(root, encoding='UTF-8', xml_declaration=True, standalone=True)


def split_reference(value, current):
    """只解释明确的内部 A1 引用；名称、外链、三维及结构化引用交给保留策略。"""
    if '!' in value:
        sheet, address = value.rsplit('!', 1)
        sheet = sheet[1:-1].replace("''", "'") if sheet.startswith("'") and sheet.endswith("'") else sheet
    else:
        sheet, address = current, value
    if any(c in sheet for c in '[]:'):
        return None
    try:
        bounds = range_boundaries(address)
        if bounds[0] is None or bounds[2] is None:
            return None
        return sheet, address, (bounds[0], bounds[1] or 1, bounds[2], bounds[3] or 1048576)
    except ValueError:
        return None


def formula_tokens(formula):
    try:
        return Tokenizer('=' + formula).items
    except Exception:
        return None


def token_contexts(tokens):
    """取得每个 token 最近的函数及调用区间，避免改动字符串中的伪引用。"""
    stack, contexts, calls = [], {}, {}
    for i, token in enumerate(tokens):
        if token.subtype == 'OPEN':
            stack.append(i)
        contexts[i] = next((j for j in reversed(stack) if tokens[j].type == 'FUNC'), None)
        if token.subtype == 'CLOSE' and stack:
            start = stack.pop()
            if tokens[start].type == 'FUNC':
                calls[start] = i
    return contexts, calls


def call_arguments(tokens, start, stop):
    depth, args, begin = 0, [], start + 1
    for i in range(start + 1, stop):
        t = tokens[i]
        if t.subtype == 'OPEN':
            depth += 1
        elif t.subtype == 'CLOSE':
            depth -= 1
        elif t.type == 'SEP' and t.subtype == 'ARG' and depth == 0:
            args.append(tokens[begin:i])
            begin = i + 1
    return args + [tokens[begin:stop]]


def safe_sumproducts(tokens, calls):
    """识别由布尔条件组成、且非空分类条件排除空尾部的 SUMPRODUCT。

    不处理除法、自定义函数或任意数值乘积。各数组仍使用完全相同的行边界。
    TEXT 的日期格式限定为样本使用的数值日期格式，避免猜测其他转换语义。
    """
    ref = r"(?:'(?:[^']|'')+'!|[\w.]+!)?\$?[A-Z]{1,3}(?:\$?\d+)?(?::\$?[A-Z]{1,3}(?:\$?\d+)?)?"
    literal = r'"(?:[^"]|"")*"'
    category = re.compile(r'--\((' + ref + r')=("[^"<>=*?~]+")\)', re.I)
    date = re.compile(r'--\(TEXT\(' + ref + r',"yyyy-mm-dd"\)(?:>=|<=|>|<|=)TEXT\(' + ref + r',"yyyy-mm-dd"\)\)', re.I)
    match = re.compile(r'--ISNUMBER\(MATCH\(' + ref + r',\{' + literal + r'(?:,' + literal + r')*\},0\)\)', re.I)
    result = {}
    for start, stop in calls.items():
        if tokens[start].value.upper() != 'SUMPRODUCT(':
            continue
        args = [''.join(t.value for t in arg if t.type != 'WHITE-SPACE') for arg in call_arguments(tokens, start, stop)]
        has_mask = any(category.fullmatch(arg) for arg in args)
        if args and has_mask and all(category.fullmatch(arg) or date.fullmatch(arg) or match.fullmatch(arg) for arg in args):
            result[start] = stop
    return result


def blank_excluded(tokens, start, stop):
    """COUNTIF(S) 至少一项条件必须排除空值，才可缩短参与计数的区域。"""
    args = call_arguments(tokens, start, stop)
    for arg in args[1::2]:
        text = ''.join(t.value for t in arg).strip()
        # 非空精确文本（包括中文分类）不匹配空尾部；不猜测通配符与数值强制转换。
        if len(arg) == 1 and arg[0].subtype == 'TEXT':
            criterion = text[1:-1].replace('""', '"')
            if criterion and not any(c in criterion for c in '<>=*?~'):
                return True
            if criterion == '<>':
                return True
        if re.fullmatch(r'">=?"&\(?TODAY\(\)\)?(?:\+.*)?', text, re.I):
            return True
    return False


@dataclass
class Sheet:
    name: str
    path: str
    root: object
    cells: dict
    formulas: dict
    candidates: set
    protected: list = field(default_factory=list)


def load_sheets(parts):
    book = parse(parts['xl/workbook.xml'])
    rels = parse(parts['xl/_rels/workbook.xml.rels'])
    targets = {r.get('Id'): posixpath.normpath(posixpath.join('xl', r.get('Target'))) if not r.get('Target').startswith('/') else r.get('Target')[1:] for r in rels}
    sheets = {}
    for entry in book.find(tag('sheets')):
        path = targets[entry.get(f'{{{REL}}}id')]
        root = parse(parts[path])
        cells = {c.get('r'): c for c in root.findall('s:sheetData/s:row/s:c', NS)}
        masters = {}
        for address, c in cells.items():
            f = c.find(tag('f'))
            if f is not None and f.get('t') == 'shared' and f.text:
                masters[f.get('si')] = (address, f.text)
        formulas = {}
        for address, c in cells.items():
            f = c.find(tag('f'))
            if f is None:
                continue
            text = f.text
            if not text and f.get('t') == 'shared':
                origin, text = masters[f.get('si')]
                text = Translator('=' + text, origin=origin).translate_formula(address)[1:]
            formulas[address] = text or ''
        sheets[entry.get('name')] = Sheet(entry.get('name'), path, root, cells, formulas, set())
    return book, sheets


def has_content(c):
    if c is None:
        return False
    v = c.find(tag('v'))
    inline = c.find(tag('is'))
    return (v is not None and v.text is not None) or (inline is not None and any(inline.itertext())) or c.find(tag('f')) is not None


def find_candidates(sheet):
    """仅删除重复预填序列中、缓存为空且空值守卫能够证明为空的公式。"""
    guarded = {}
    for address, formula in sheet.formulas.items():
        m = GUARD_EQUAL.match(formula)
        if not m:
            m = GUARD_NOT_EQUAL.match(formula)
            if not m or not re.search(r',\s*""\s*\)$', formula):
                continue
            tokens = formula_tokens(formula)
            depth, separators = 0, []
            for i, t in enumerate(tokens or []):
                if t.subtype == 'OPEN':
                    depth += 1
                elif t.subtype == 'CLOSE':
                    depth -= 1
                elif t.type == 'SEP' and t.subtype == 'ARG' and depth == 1:
                    separators.append(i)
            if len(separators) != 2 or ''.join(t.value for t in tokens[separators[1] + 1:-1]).strip() != '""':
                continue
        guard = m.group(1).replace('$', '')
        col, row, _, _ = range_boundaries(address)
        guard_col, _, _, _ = range_boundaries(guard)
        # 同一记录中已有常量时，即使守卫列为空，也保留该记录的公式。
        if any(has_content(sheet.cells.get(f'{get_column_letter(i)}{row}')) and f'{get_column_letter(i)}{row}' not in sheet.formulas for i in range(min(col, guard_col), max(col, guard_col) + 1)):
            continue
        f = sheet.cells[address].find(tag('f'))
        v = sheet.cells[address].find(tag('v'))
        if f.get('t') in ('array', 'dataTable') or v is None or v.text not in (None, ''):
            continue
        guarded[address] = guard
    counts = Counter(CELL.match(a).group(1) for a in guarded)
    memo = {}

    def proven(address, visiting):
        if address in memo:
            return memo[address]
        if address in visiting or address not in guarded:
            return False
        guard = guarded[address]
        c = sheet.cells.get(guard)
        empty = not has_content(c)
        if guard in guarded:
            empty = proven(guard, visiting | {address})
        memo[address] = empty
        return empty

    sheet.candidates = {a for a in guarded if counts[CELL.match(a).group(1)] >= 16 and proven(a, set())}


def preserve_dependencies(sheets, book, warnings):
    """保留直接引用及对空字符串/空单元格有区别的使用方所需的公式。"""
    dependencies = []
    for sheet in sheets.values():
        for address, formula in sheet.formulas.items():
            tokens = formula_tokens(formula)
            if tokens is None or re.search(r'\b(INDIRECT|OFFSET)\s*\(', formula, re.I):
                warnings.append('存在动态引用或无法解析的公式，预填公式清理已保守停用；其他范围仍可分析。')
                for target in sheets.values():
                    target.candidates.clear()
                return
            contexts, calls = token_contexts(tokens)
            products = safe_sumproducts(tokens, calls)
            for i, token in enumerate(tokens):
                if token.type != 'OPERAND' or token.subtype != 'RANGE':
                    continue
                context = contexts[i]
                function = tokens[context].value[:-1].upper() if context is not None else ''
                if function in SAFE_BLANK:
                    continue
                ref = split_reference(token.value, sheet.name)
                if ref and ref[2][1] != ref[2][3] and any(start < i < stop for start, stop in products.items()):
                    continue
                if ref:
                    dependencies.append((sheet.name, address, ref))
                else:
                    # 不明确的命名/结构化引用可能观察空字符串，不冒险删其来源。
                    warnings.append('存在非聚合用途的名称或结构化引用，预填公式清理已保守停用。')
                    for target in sheets.values():
                        target.candidates.clear()
                    return
    for name in book.findall('s:definedNames/s:definedName', NS):
        if name.get('name', '').startswith('_xlnm.'):
            continue
        ref = split_reference(name.text or '', '')
        if ref:
            dependencies.append((None, None, ref))
    index = {}
    for sheet in sheets.values():
        columns = defaultdict(list)
        for address in sheet.candidates:
            col, row, _, _ = range_boundaries(address)
            columns[col].append((row, address))
        index[sheet.name] = {col: sorted(rows) for col, rows in columns.items()}
    outgoing = defaultdict(list)
    queue = deque()
    for source, address, ref in dependencies:
        outgoing[(source, address)].append(ref)
        if source is None or address not in sheets[source].candidates:
            queue.append((source, address, ref))
    while queue:
        source, address, (target, _, bounds) = queue.popleft()
        if target not in sheets:
            continue
        a, b, c, d = bounds
        pinned = set()
        for col, rows in index[target].items():
            if a <= col <= c:
                begin, end = bisect_left(rows, (b, '')), bisect_right(rows, (d, '\uffff'))
                pinned.update(p for _, p in rows[begin:end] if p in sheets[target].candidates)
        sheets[target].candidates -= pinned
        if pinned and len(sheets[target].protected) < 12:
            sheets[target].protected.append({'source_sheet': source, 'source_cell': address, 'target_range': bounds, 'count': len(pinned)})
        for p in pinned:
            queue.extend((target, p, ref) for ref in outgoing[(target, p)])


def content_limits(sheet):
    limits = defaultdict(int)
    for address, c in sheet.cells.items():
        if address not in sheet.candidates and has_content(c):
            col, row, _, _ = range_boundaries(address)
            limits[col] = max(limits[col], row)
    return limits


def optimize_formula(formula, current, limits):
    tokens = formula_tokens(formula)
    if tokens is None:
        return formula, 0
    contexts, calls = token_contexts(tokens)
    products = safe_sumproducts(tokens, calls)
    groups = defaultdict(list)
    for i, token in enumerate(tokens):
        if token.type != 'OPERAND' or token.subtype != 'RANGE':
            continue
        ref = split_reference(token.value, current)
        call = contexts[i]
        product = next((start for start, stop in products.items() if start < i < stop), None)
        if product is not None and ref and ref[2][1] != ref[2][3]:
            call = product
        if not ref or ref[0] not in limits or call is None:
            continue
        function = tokens[call].value[:-1].upper()
        if function not in {'SUM', 'COUNT', 'SUMIF', 'SUMIFS', 'COUNTIF', 'COUNTIFS'} and call not in products:
            continue
        if function in {'COUNTIF', 'COUNTIFS'} and not blank_excluded(tokens, call, calls[call]):
            continue
        groups[call].append((i, ref))
    changes = 0
    for group in groups.values():
        if len({(bounds[1], bounds[3]) for _, (_, _, bounds) in group}) > 1:
            # SUMIF 等允许不同起点的隐式映射；不擅自改变它的对齐方式。
            continue
        # 所有对应数组使用同一界限；保留首行和原起始行，避免错位及漏计表头。
        end = max((limits[s].get(col, 1) for _, (s, _, (a, _, c, _)) in group for col in range(a, c + 1)), default=1)
        for i, (sheet, address, (a, b, c, d)) in group:
            if d <= end or b > end:
                continue
            # 不缩短任意的有限范围，除非它明显超出当前内容且是单列引用。
            if a != c:
                continue
            prefix = tokens[i].value[:-len(address)]
            col = get_column_letter(a)
            absolute = '$' if address.startswith('$') else ''
            tokens[i].value = f'{prefix}{absolute}{col}${b}:{absolute}{col}${end}'
            changes += 1
    return ''.join(t.value for t in tokens), changes


def clip_ranges(value, limits):
    result = []
    for item in value.split():
        try:
            a, b, c, d = range_boundaries(item)
            a, b, c, d = a or 1, b or 1, c or 16384, d or 1048576
            end = max((limits.get(col, 0) for col in range(a, c + 1)), default=0)
            if end >= b:
                result.append(f'{get_column_letter(a)}{b}:{get_column_letter(c)}{min(d, end)}')
        except ValueError:
            result.append(item)
    return ' '.join(result)


def constant_snapshot(sheets):
    return {(s.name, a): (c.get('t'), c.findtext(tag('v')), ET.tostring(c.find(tag('is'))) if c.find(tag('is')) is not None else None) for s in sheets.values() for a, c in s.cells.items() if a not in s.formulas and has_content(c)}


def optimize_workbook(data: bytes):
    """返回独立的新工作簿与审计报告；原文件不写盘、不覆盖。"""
    started = perf_counter()
    try:
        with ZipFile(BytesIO(data)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 256 * 1024 * 1024:
                raise ValueError('工作簿解压后超过 256 MB，请拆分后处理。')
            parts = {name: archive.read(name) for name in archive.namelist()}
        if any(n.startswith('_xmlsignatures/') for n in parts):
            raise ValueError('此文件带数字签名，清理会使签名失效，请提供未签名的副本。')
        book, sheets = load_sheets(parts)
    except (BadZipFile, KeyError, ET.XMLSyntaxError, ValueError) as exc:
        raise ValueError(f'无法处理此 Excel 工作簿：{exc}') from exc
    # 共享字符串中的纯空格并非业务内容；仅当整行没有其他内容时移除。
    shared = parse(parts['xl/sharedStrings.xml']).findall('s:si', NS) if 'xl/sharedStrings.xml' in parts else []
    whitespace_counts = {}
    whitespace_candidates = {}
    for sheet in sheets.values():
        whitespace = set()
        content_rows = set()
        for address, cell in sheet.cells.items():
            v = cell.find(tag('v'))
            inline = cell.find(tag('is'))
            blank_text = cell.find(tag('f')) is None and (
                (cell.get('t') == 's' and v is not None and v.text is not None and int(v.text) < len(shared) and not ''.join(shared[int(v.text)].itertext()).strip())
                or (cell.get('t') == 'inlineStr' and inline is not None and not ''.join(inline.itertext()).strip())
                or (cell.get('t') == 'str' and v is not None and not (v.text or '').strip())
            )
            if blank_text:
                whitespace.add(address)
            elif has_content(cell) and address not in sheet.formulas:
                content_rows.add(range_boundaries(address)[1])
        whitespace_candidates[sheet.name] = {address for address in whitespace if range_boundaries(address)[1] not in content_rows}
    # 空格与空单元格在部分 Excel 公式中含义不同；被引用时保留原值。
    for sheet in sheets.values():
        for formula in sheet.formulas.values():
            tokens = formula_tokens(formula)
            if tokens is None or re.search(r'\b(INDIRECT|OFFSET)\s*\(', formula, re.I):
                for candidates in whitespace_candidates.values():
                    candidates.clear()
                break
            for token in tokens:
                if token.type != 'OPERAND' or token.subtype != 'RANGE':
                    continue
                ref = split_reference(token.value, sheet.name)
                if not ref or ref[0] not in whitespace_candidates:
                    continue
                a, b, c, d = ref[2]
                whitespace_candidates[ref[0]] = {address for address in whitespace_candidates[ref[0]] if not (a <= range_boundaries(address)[0] <= c and b <= range_boundaries(address)[1] <= d)}
    for name in book.findall('s:definedNames/s:definedName', NS):
        ref = split_reference(name.text or '', '')
        if ref and ref[0] in whitespace_candidates:
            a, b, c, d = ref[2]
            whitespace_candidates[ref[0]] = {address for address in whitespace_candidates[ref[0]] if not (a <= range_boundaries(address)[0] <= c and b <= range_boundaries(address)[1] <= d)}
    for sheet in sheets.values():
        removable = whitespace_candidates[sheet.name]
        for address in removable:
            cell = sheet.cells.pop(address)
            cell.getparent().remove(cell)
        whitespace_counts[sheet.name] = len(removable)
    before_constants = constant_snapshot(sheets)
    warnings = ['统计公式与原有缓存保留；未执行 Excel/WPS 原生重算，不能将缓存一致视为重算结果一致。']
    for sheet in sheets.values():
        find_candidates(sheet)
    preserve_dependencies(sheets, book, warnings)
    limits = {s.name: content_limits(s) for s in sheets.values()}
    report = {'input_bytes': len(data), 'formulas_before': sum(len(s.formulas) for s in sheets.values()), 'sheets': [], 'tables': [], 'warnings': warnings, 'references_optimized': 0}
    expected_formulas = {}
    styles = parse(parts['xl/styles.xml']) if 'xl/styles.xml' in parts else None
    xfs = styles.find(tag('cellXfs')) if styles is not None else None
    borderless_styles = {}
    for sheet in sheets.values():
        actions = []
        removed_blank = 0
        removed_empty_rows = 0
        sheet_limits = limits[sheet.name]
        # 合并区域内的空白单元格承担边框等显示作用，需要保留。
        merged_bounds = [range_boundaries(m.get('ref')) for m in sheet.root.findall('s:mergeCells/s:mergeCell', NS)]
        occupied_rows = {range_boundaries(address)[1] for address, cell in sheet.cells.items() if address not in sheet.candidates and has_content(cell)}
        columns = sheet.root.findall('s:cols/s:col', NS)
        for column in columns:
            style_id = column.get('style')
            if style_id is None or xfs is None or int(style_id) >= len(xfs):
                continue
            old_id = int(style_id)
            original_xf = xfs[old_id]
            if original_xf.get('borderId', '0') == '0':
                continue
            if old_id not in borderless_styles:
                new_xf = deepcopy(original_xf)
                new_xf.set('borderId', '0')
                new_xf.set('applyBorder', '1')
                borderless_styles[old_id] = len(xfs)
                xfs.append(new_xf)
            # 对原本继承列样式的已存在单元格显式赋予旧样式，保留有效区域边框。
            first, last = int(column.get('min')), int(column.get('max'))
            for address, cell in sheet.cells.items():
                col, _, _, _ = range_boundaries(address)
                if first <= col <= last and cell.get('s') is None and address not in sheet.candidates:
                    cell.set('s', style_id)
            column.set('style', str(borderless_styles[old_id]))
        for address, c in list(sheet.cells.items()):
            if address in sheet.candidates:
                c.getparent().remove(c)
                continue
            if address in sheet.formulas:
                f = c.find(tag('f'))
                if f.get('t') == 'shared':
                    for key in ('t', 'si', 'ref'):
                        f.attrib.pop(key, None)
                original = sheet.formulas[address]
                optimized, count = optimize_formula(original, sheet.name, limits)
                f.text = optimized
                expected_formulas[(sheet.name, address)] = optimized
                report['references_optimized'] += count
                if count:
                    actions.append({'cell': address, 'before': original, 'after': optimized, 'references': count})
            elif not has_content(c) and not any(c.find(tag(t)) is not None for t in ('extLst',)):
                col, row, _, _ = range_boundaries(address)
                in_merge = any(a <= col <= c and b <= row <= d for a, b, c, d in merged_bounds)
                if not in_merge and (row not in occupied_rows or row > sheet_limits.get(col, 0)):
                    c.getparent().remove(c)
                    removed_blank += 1
        for row in sheet.root.findall('s:sheetData/s:row', NS):
            row_number = int(row.get('r'))
            if len(row) == 0 and row_number not in occupied_rows and not any(b <= row_number <= d for _, b, _, d in merged_bounds):
                row.getparent().remove(row)
                removed_empty_rows += 1
            else:
                row.attrib.pop('spans', None)
        ranges = []
        for obj in list(sheet.root.iter()):
            if not isinstance(obj.tag, str):
                continue
            local = ET.QName(obj).localname
            attribute = 'sqref' if local in {'conditionalFormatting', 'dataValidation'} else 'ref' if local == 'autoFilter' else None
            if attribute and obj.get(attribute) and obj.getparent() is not None:
                old = obj.get(attribute)
                new = clip_ranges(old, sheet_limits)
                if new != old:
                    ranges.append({'type': local, 'before': old, 'after': new or '移除空区域'})
                    if new:
                        obj.set(attribute, new)
                    else:
                        obj.getparent().remove(obj)
        validations = sheet.root.find(tag('dataValidations'))
        if validations is not None:
            validations.set('count', str(len(validations)))
            if not len(validations):
                sheet.root.remove(validations)
        remaining = sheet.root.findall('s:sheetData/s:row/s:c', NS)
        max_row = max((range_boundaries(c.get('r'))[1] for c in remaining), default=1)
        max_col = max((range_boundaries(c.get('r'))[0] for c in remaining), default=1)
        # 合并区和批注/绘图锚点不移动，避免损伤独立区域的版面与对象。
        for merge in sheet.root.findall('s:mergeCells/s:mergeCell', NS):
            a, b, c, d = range_boundaries(merge.get('ref'))
            max_row, max_col = max(max_row, d), max(max_col, c)
        dimension = sheet.root.find(tag('dimension'))
        old_dimension = dimension.get('ref') if dimension is not None else None
        if dimension is not None:
            dimension.set('ref', f'A1:{get_column_letter(max_col)}{max_row}')
        parts[sheet.path] = serialize(sheet.root)
        report['sheets'].append({'name': sheet.name, 'range_before': old_dimension, 'range_after': f'A1:{get_column_letter(max_col)}{max_row}', 'formulas_removed': len(sheet.candidates), 'blank_cells_removed': removed_blank, 'whitespace_cells_removed': whitespace_counts[sheet.name], 'empty_rows_removed': removed_empty_rows, 'formula_changes': actions, 'range_changes': ranges, 'dependency_preservation': sheet.protected})
        rel_path = posixpath.join(posixpath.dirname(sheet.path), '_rels', posixpath.basename(sheet.path) + '.rels')
        if rel_path in parts:
            for rel in parse(parts[rel_path]):
                if not rel.get('Type', '').endswith('/table'):
                    continue
                path = posixpath.normpath(posixpath.join(posixpath.dirname(sheet.path), rel.get('Target'))).lstrip('/')
                if rel.get('Target').startswith('/'):
                    path = rel.get('Target')[1:]
                table = parse(parts[path])
                old = table.get('ref')
                new = clip_ranges(old, sheet_limits)
                # totalsRow 的位置不能擅自移动。
                if new and table.get('totalsRowCount', '0') == '0' and old != new:
                    table.set('ref', new)
                    af = table.find(tag('autoFilter'))
                    if af is not None:
                        af.set('ref', new)
                    parts[path] = serialize(table)
                    report['tables'].append({'sheet': sheet.name, 'name': table.get('displayName'), 'before': old, 'after': new})
    for name in book.findall('s:definedNames/s:definedName', NS):
        if name.get('name') != '_xlnm._FilterDatabase':
            continue
        ref = split_reference(name.text or '', '')
        if ref and ref[0] in limits:
            new = clip_ranges(ref[1], limits[ref[0]])
            if new:
                name.text = "'" + ref[0].replace("'", "''") + "'!" + new
    parts['xl/workbook.xml'] = serialize(book)
    if borderless_styles:
        xfs.set('count', str(len(xfs)))
        parts['xl/styles.xml'] = serialize(styles)
    # 删除已过时的计算顺序缓存与对应关系；保留原 calcPr（尤其迭代/精度设置）。
    for path in list(parts):
        if path == 'xl/calcChain.xml':
            del parts[path]
        elif path in ('xl/_rels/workbook.xml.rels', '[Content_Types].xml'):
            root = parse(parts[path])
            for item in list(root):
                if item.get('Type', '').endswith('/calcChain') or item.get('PartName') == '/xl/calcChain.xml':
                    root.remove(item)
            parts[path] = serialize(root)
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
        for path, content in parts.items():
            archive.writestr(path, content)
    result = output.getvalue()
    # 在交付前重新读取生成包，逐格校验常量、保留公式、缓存以及工作表顺序。
    with ZipFile(BytesIO(result)) as archive:
        if archive.testzip() is not None:
            raise ValueError('输出文件 ZIP 完整性校验失败。')
        _, checked = load_sheets({p: archive.read(p) for p in archive.namelist()})
    if list(checked) != list(sheets) or constant_snapshot(checked) != before_constants:
        raise ValueError('优化结果未通过原始数据完整性校验，已取消下载。')
    for (name, address), formula in expected_formulas.items():
        original, saved = sheets[name].cells[address], checked[name].cells.get(address)
        if saved is None or checked[name].formulas.get(address) != formula or original.findtext(tag('v')) != saved.findtext(tag('v')) or original.get('t') != saved.get('t'):
            raise ValueError('优化结果未通过公式或缓存一致性校验，已取消下载。')
    report.update(output_bytes=len(result), formulas_after=len(expected_formulas), constants_verified=len(before_constants), cached_results_verified=len(expected_formulas), elapsed_seconds=round(perf_counter() - started, 3), recalculated=False)
    report['warnings'] = list(dict.fromkeys(warnings))
    report['formulas_removed'] = report['formulas_before'] - report['formulas_after']
    return result, report


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description='分析当前 .xlsx 快照并生成去冗余副本及 JSON 报告')
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error('输出路径必须与原文件不同，禁止覆盖原文件。')
    content, summary = optimize_workbook(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(content)
    args.output.with_suffix('.report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in summary.items() if key not in ('sheets',)}, ensure_ascii=True, indent=2))
