# -*- coding: utf-8 -*-
"""
智慧供热旁路精算与质检平台 —— 数据库事实表结构自愈初始化服务。
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from backend.db.database_daily_report_25_26 import engine

logger = logging.getLogger(__name__)

_INIT_LOCK = threading.RLock()
_TABLES_VERIFIED = False

FACT_SQL_FILE = Path(__file__).resolve().parents[3] / "sql" / "smart_heating_platform_fact_init.sql"


def ensure_smart_heating_fact_tables(force: bool = False) -> None:
    """幂等确保 `smart_heating_platform` 全部 9 张事实与运行审计表已创建。"""
    global _TABLES_VERIFIED
    if _TABLES_VERIFIED and not force:
        return
    with _INIT_LOCK:
        if _TABLES_VERIFIED and not force:
            return
        if not FACT_SQL_FILE.exists():
            raise FileNotFoundError(f"未找到事实表 DDL 文件: {FACT_SQL_FILE}")
        ddl_sql = FACT_SQL_FILE.read_text(encoding="utf-8")
        raw_conn = engine.raw_connection()
        try:
            with raw_conn.cursor() as cur:
                cur.execute(ddl_sql)
            raw_conn.commit()
            _TABLES_VERIFIED = True
            logger.info("smart_heating_platform 事实表校验/初始化完成。")
        except Exception:
            raw_conn.rollback()
            raise
        finally:
            raw_conn.close()
