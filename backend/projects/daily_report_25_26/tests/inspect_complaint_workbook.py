"""只输出结构与公式分布，不输出投诉明细个人信息。"""
import collections
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def inspect(path):
    result = []
    with ZipFile(path) as archive:
        book = ET.fromstring(archive.read('xl/workbook.xml'))
        sheets = book.find('s:sheets', NS)
        for index, sheet in enumerate(sheets, 1):
            root = ET.fromstring(archive.read(f'xl/worksheets/sheet{index}.xml'))
            cells = root.findall('.//s:sheetData/s:row/s:c', NS)
            formulas = [c for c in cells if c.find('s:f', NS) is not None]
            constants = [c for c in cells if c.find('s:f', NS) is None and (c.find('s:v', NS) is not None or c.find('s:is', NS) is not None)]
            counts = collections.Counter(''.join(filter(str.isalpha, c.get('r'))) for c in formulas)
            blocks = collections.Counter((int(''.join(filter(str.isdigit,c.get('r'))))-1)//100 for c in constants)
            result.append({'sheet': sheet.get('name'), 'dimension': root.find('s:dimension', NS).get('ref'), 'cells':len(cells), 'formulas':len(formulas), 'formula_columns':dict(counts), 'constant_row_blocks':dict(blocks), 'examples':[{'cell':c.get('r'),'formula':c.find('s:f', NS).text,'attributes':c.find('s:f', NS).attrib,'cached':c.findtext('s:v',namespaces=NS)} for c in formulas[:12]], 'last_formulas':[{'cell':c.get('r'),'formula':c.find('s:f', NS).text,'cached':c.findtext('s:v',namespaces=NS)} for c in formulas[-4:]], 'objects':{tag:[x.attrib for x in root.findall('s:'+tag,NS)][:6] for tag in ['dataValidations','conditionalFormatting','mergeCells','autoFilter']}})
        tables = [{'path':n,'attributes':ET.fromstring(archive.read(n)).attrib} for n in archive.namelist() if n.startswith('xl/tables/') and n.endswith('.xml')]
        return {'bytes':Path(path).stat().st_size,'sheets':result,'tables':tables,'defined_names':[e.text for e in book.findall('s:definedNames/s:definedName',NS)]}

if __name__ == '__main__':
    import sys
    print(json.dumps(inspect(sys.argv[1]),ensure_ascii=True,indent=2))
