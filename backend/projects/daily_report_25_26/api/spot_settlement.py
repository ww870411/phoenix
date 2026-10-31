"""电力日账单上传预览、原始数据入库与查询。"""
from typing import List
from uuid import UUID
from zipfile import BadZipFile

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import BaseModel
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from backend.db.database_daily_report_25_26 import SessionLocal
from backend.services.auth_manager import AuthSession, get_current_session
from ..services import spot_settlement_import as bill_service
from ..services.spot_settlement_import import TABLE, PLANTS, load_batch, parse_bill, persist_upload, stage_uploads

router = APIRouter(prefix='/spot_electricity/bills', tags=['原始电力日账单'])
PROJECT_KEY = 'daily_report_25_26'


def _global_admin(session):
    return str(getattr(session, 'group', '')).strip().lower() == 'global_admin'


def _importer(session: AuthSession = Depends(get_current_session)):
    if not _global_admin(session):
        raise HTTPException(403, '仅 Global_admin 可操作日账单上传入库功能')
    return session


def _allowed(session):
    # 与项目现有语义一致：未指定单位清单表示项目范围；有清单时逐厂限制。
    return None if _global_admin(session) else session.resolve_allowed_units(PROJECT_KEY) or None


@router.post('/preview', summary='上传原始日账单并预览，尚不写入业务表')
async def preview_bills(files: List[UploadFile] = File(...), session=Depends(_importer)):
    if not files:
        raise HTTPException(422, '请至少选择一份xlsx日账单')
    uploaded = []
    for file in files:
        if not (file.filename or '').lower().endswith('.xlsx'):
            raise HTTPException(422, '仅支持xlsx日账单')
        content = await file.read(25 * 1024 * 1024 + 1)
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(422, '单个文件不能超过25MB')
        uploaded.append((file.filename, content))
    try:
        result = await run_in_threadpool(stage_uploads, uploaded, session.username)
        allowed = _allowed(session)
        if allowed is not None and any(unit['plant_key'] not in allowed for item in result['files'] for unit in item['units']):
            raise HTTPException(403, '文件包含无权提交的电厂')
        return result
    except (ValueError, BadZipFile, InvalidFileException) as error:
        raise HTTPException(422, f'账单解析失败：{error}') from error


class ConfirmBills(BaseModel):
    token: UUID
    overwrite: bool = False


@router.post('/confirm', summary='确认后将量价映射写入15分钟数据表')
def confirm_bills(payload: ConfirmBills, session=Depends(_importer)):
    try:
        return persist_upload(payload.token, session.username, _allowed(session), overwrite=payload.overwrite)
    except FileNotFoundError as error:
        raise HTTPException(404, '上传预览不存在，请重新上传') from error
    except PermissionError as error:
        raise HTTPException(403, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.get('/imports', summary='查看当前生效的电厂账单来源')
def list_imports(limit: int = Query(20, ge=1, le=100), session=Depends(_importer)):
    items = {}
    allowed = _allowed(session)
    with SessionLocal() as db:
        for plant, (prefix, units) in PLANTS.items():
            if allowed is not None and plant not in allowed:
                continue
            rows = db.execute(text(f'''SELECT {prefix}_bill_import_id AS import_id, trade_date,
                count(*) AS record_count, max(updated_at) AS imported_at FROM {TABLE}
                WHERE {prefix}_bill_import_id IS NOT NULL GROUP BY {prefix}_bill_import_id,trade_date
                ORDER BY max(updated_at) DESC LIMIT :limit'''), {'limit': limit}).mappings()
            for row in rows:
                identifier = str(row['import_id'])
                metadata = load_batch(identifier)
                key = (identifier, str(row['trade_date']))
                item = items.setdefault(key, {'import_id': identifier, 'settlement_date': str(row['trade_date']),
                    'source_file': metadata.get('source_file', '来源文件缺失：' + identifier),
                    'imported_at': metadata.get('imported_at', str(row['imported_at'])), 'record_count': 0, 'unit_count': 0})
                item['unit_count'] += units
                item['record_count'] = max(item['record_count'], row['record_count'])
    return {'ok': True, 'items': sorted(items.values(), key=lambda i: i['imported_at'], reverse=True)[:limit]}


@router.get('/records', summary='分页查看当前入库量价及源单元格')
def list_records(import_id: UUID,
                 offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), session=Depends(_importer)):
    metadata = load_batch(import_id)
    if not metadata:
        raise HTTPException(404, '来源清单不存在')
    allowed = _allowed(session)
    units = [u for u in metadata['units'] if allowed is None or u['plant_key'] in allowed]
    if not units:
        raise HTTPException(403, '无权查看此电厂账单')
    original = bill_service.IMPORT_ROOT / 'originals' / f'{metadata["file_sha256"]}.xlsx'
    if not original.exists():
        raise HTTPException(404, '归档原件不存在')
    report = parse_bill(original.read_bytes(), metadata['source_file'])
    current = {}
    with SessionLocal() as db:
        for plant in {u['plant_key'] for u in units}:
            prefix = PLANTS[plant][0]
            for row in db.execute(text(f'SELECT * FROM {TABLE} WHERE {prefix}_bill_import_id=:id'), {'id': str(import_id)}).mappings():
                current[(plant, str(row['trade_date']), row['point_index'])] = row
    items = []
    for record in report['records']:
        row = current.get((record['plant_key'], str(record['settlement_date']), record['point_index']))
        if row is None or record['subject_code'] not in ('100401', '100600'):
            continue
        prefix = f"{PLANTS[record['plant_key']][0]}_unit{record['unit_number']}"
        contract = record['subject_code'] == '100401'
        quantity = row[prefix + ('_contract_quantity' if contract else '_sales')]
        price = row[prefix + '_contract_price'] if contract else row['bill_real_time_price']
        items.append({k: record[k] for k in ('settlement_unit_name', 'point_index', 'time_label', 'subject_code', 'subject_name')} |
                     {'id': f'{row["id"]}:{prefix}:{record["subject_code"]}',
                      'quantity': str(quantity) if quantity is not None else None,
                      'price': str(price) if price is not None else None,
                      'source_cells': {k: v for k, v in record['source_cells'].items() if k in ('quantity', 'price')}})
    return {'ok': True, 'total': len(items), 'items': items[offset:offset + limit]}
