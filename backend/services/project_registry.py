# -*- coding: utf-8 -*-
"""
项目注册表（内置默认项）。

目标：
- 统一维护默认项目 key；
- 统一维护内置项目的目录化迁移文件清单；
- 为后端各模块提供单一读取入口，减少散落硬编码。
"""

from __future__ import annotations

from typing import Dict, List, Tuple


DEFAULT_PROJECT_KEY = "daily_report_25_26"
DEFAULT_PROJECT_CONFIG_FILES: List[str] = [
    "数据结构_基本指标表.json",
    "数据结构_常量指标表.json",
    "数据结构_审批用表.json",
    "数据结构_数据分析表.json",
    "数据结构_数据看板.json",
    "date.json",
    "api_key.json",
]
DEFAULT_PROJECT_RUNTIME_FILES: List[str] = [
    "dashboard_cache.json",
    "test.md",
]


PROJECT_REGISTRY: Dict[str, Dict[str, List[str]]] = {
    "daily_report_25_26": {
        "config_files": list(DEFAULT_PROJECT_CONFIG_FILES),
        "runtime_files": list(DEFAULT_PROJECT_RUNTIME_FILES),
    },
}


def get_default_project_key() -> str:
    return DEFAULT_PROJECT_KEY


def get_project_modularization_files(project_key: str) -> Tuple[List[str], List[str]]:
    cfg = PROJECT_REGISTRY.get(project_key)
    if isinstance(cfg, dict):
        config_files = cfg.get("config_files")
        runtime_files = cfg.get("runtime_files")
        if isinstance(config_files, list) and isinstance(runtime_files, list):
            return list(config_files), list(runtime_files)
    return list(DEFAULT_PROJECT_CONFIG_FILES), list(DEFAULT_PROJECT_RUNTIME_FILES)
