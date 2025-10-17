"""
daily_report_25_26 项目级路由（v1）

说明：
- 作为项目隔离的路径前缀：`/api/v1/daily_report_25_26`；
- 后续可在此处实现 template/submit/query 等接口，形成与通用路由并存的“项目别名”入口；
- 便于前端以稳定路径访问当前项目，同时保留多项目扩展能力。
"""

from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse
from pathlib import Path as SysPath
from typing import Dict, Any
import json


router = APIRouter()


@router.get("/ping", summary="daily_report_25_26 连通性测试", tags=["daily_report_25_26"])
def ping_daily_report():
    """保留最小可用连通性接口。其他业务接口由后续实现。"""
    return {"ok": True, "project": "daily_report_25_26", "message": "pong"}


# ========== 以下为本项目占位接口（迁移自 projects_daily_report_25_26.py）===========

@router.get("/sheets/{sheet_key}/template", summary="获取模板（占位）")
def get_template_placeholder(
    sheet_key: str = Path(..., description="表键名 sheet_key"),
):
    """占位实现：仅返回占位提示，具体结构待确认后补齐。"""
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": "template endpoint placeholder",
            "sheet_key": sheet_key,
        },
    )


@router.post("/sheets/{sheet_key}/submit", summary="提交数据（占位）")
def submit_placeholder(
    sheet_key: str = Path(..., description="表键名 sheet_key"),
):
    """占位实现：仅返回占位提示，具体结构待确认后补齐。"""
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": "submit endpoint placeholder",
            "sheet_key": sheet_key,
        },
    )


@router.post("/sheets/{sheet_key}/query", summary="查询数据（占位）")
def query_placeholder(
    sheet_key: str = Path(..., description="表键名 sheet_key"),
):
    """占位实现：仅返回占位提示，具体结构待确认后补齐。"""
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "message": "query endpoint placeholder",
            "sheet_key": sheet_key,
        },
    )


@router.get("/sheets", summary="列出可用表（来自挂载目录）")
def list_sheets_placeholder():
    """
    读取 backend_data/数据结构_基本指标表.json 并整理为 {sheet_key: {单位名, 表名}} 结构。

    说明：
    - 为提升健壮性，文件查找按优先级：
      1) 精确名：backend_data/数据结构_基本指标表.json
      2) backend_data 下首个 .json 文件（降级兜底）
    - 字段名容错：优先读取中文键“单位名”“表名”；若文件存在编码差异，尝试常见别名集合。
    """
    # 修正：定位到项目根目录（.../phoenix），而非 backend 目录
    project_root = SysPath(__file__).resolve().parents[3]
    data_dir = project_root / "backend_data"
    preferred = data_dir / "数据结构_基本指标表.json"

    def _read_json(p: SysPath) -> Dict[str, Any]:
        # 依次尝试 utf-8、gbk 读取
        for enc in ("utf-8", "utf-8-sig", "gbk", "gb2312"):
            try:
                with p.open("r", encoding=enc) as f:
                    return json.load(f)
            except Exception:
                continue
        raise FileNotFoundError(f"无法读取 JSON：{p}")

    # 仅精确读取 数据结构_基本指标表.json，不做模糊匹配
    if not preferred.exists():
        return JSONResponse(status_code=404, content={
            "ok": False,
            "message": "未找到文件:backend_data/数据结构_基本指标表.json",
        })
    file_path: SysPath = preferred

    raw = _read_json(file_path)

    # 字段名可能存在编码差异，做容错
    unit_keys = {"单位名", "单位", "单位名称"}
    name_keys = {"表名", "名称", "表名称"}

    result: Dict[str, Dict[str, str]] = {}

    def extract_names(payload: Dict[str, Any]) -> Dict[str, str]:
        unit_name = None
        sheet_name = None
        for k in unit_keys:
            if k in payload and isinstance(payload[k], str) and payload[k].strip():
                unit_name = payload[k].strip()
                break
        for k in name_keys:
            if k in payload and isinstance(payload[k], str) and payload[k].strip():
                sheet_name = payload[k].strip()
                break
        return {
            "unit_name": unit_name or "",
            "sheet_name": sheet_name or "",
        }

    if isinstance(raw, dict):
        for raw_key, payload in raw.items():
            if not isinstance(payload, dict):
                continue
            names = extract_names(payload)
            skey = raw_key  # 保留原键作为 sheet_key
            sheet_name = names["sheet_name"] or skey
            unit_name = names["unit_name"]
            result[skey] = {"单位名": unit_name, "表名": sheet_name}
    elif isinstance(raw, list):
        for idx, payload in enumerate(raw, start=1):
            if not isinstance(payload, dict):
                continue
            names = extract_names(payload)
            sheet_name = names["sheet_name"] or f"表{idx:02d}"
            unit_name = names["unit_name"]
            # 直接使用表名作为 sheet_key（支持中文，前端已使用 encodeURIComponent 处理）
            skey = sheet_name
            result[skey] = {"单位名": unit_name, "表名": sheet_name}
    else:
        # 不支持的结构，返回空
        result = {}

    return JSONResponse(status_code=200, content=result)
