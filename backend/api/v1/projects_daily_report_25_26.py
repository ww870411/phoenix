"""
projects/daily_report_25_26 路由（v1）

说明
- 统一后端前缀为 `/api/v1/projects/daily_report_25_26`。
- 仅创建占位接口，暂不实现具体业务逻辑，待数据传递格式确认后补齐。
"""

from fastapi import APIRouter, Path
from fastapi.responses import JSONResponse
from pathlib import Path as SysPath
import json
from typing import Dict, Any


router = APIRouter(tags=["projects/daily_report_25_26"])


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
    """读取 backend_data/数据结构_基本指标表.json 并整理为 {sheet_key: {单位名, 表名}} 结构。

    说明：
    - 为提升健壮性，文件查找按优先级：
      1) 精确名：backend_data/数据结构_基本指标表.json
      2) backend_data 下首个 .json 文件（降级兜底）
    - 键名规范：将以 `_constant_sheet` 结尾的键统一替换为 `_sheet`。
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
            "message": "未找到文件：backend_data/数据结构_基本指标表.json",
        })
    file_path: SysPath = preferred

    raw = _read_json(file_path)

    # 字段名可能存在编码差异，做容错
    unit_keys = {"单位名", "单位", "单位名称"}
    name_keys = {"表名", "名称", "表名称"}

    result: Dict[str, Dict[str, str]] = {}
    for raw_key, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        # 保持 sheet_key 原样返回（不做 _constant_sheet → _sheet 规范化）
        skey = raw_key

        # 提取单位名、表名
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

        # 若缺失则跳过该项
        if not sheet_name:
            # 放行但标注占位，避免整个列表为空
            sheet_name = skey
        if not unit_name:
            unit_name = ""

        result[skey] = {"单位名": unit_name, "表名": sheet_name}

    return JSONResponse(status_code=200, content=result)
