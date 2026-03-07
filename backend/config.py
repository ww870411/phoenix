"""
全局配置常量。

提供统一的数据目录常量，避免在代码中硬编码宿主路径。
"""

import os
from pathlib import Path

# 默认数据目录：优先尝试容器内的路径，若不存在则回退到本地项目目录下的 backend_data
_container_data = Path("/app/data")
_local_data = Path(__file__).resolve().parents[1] / "backend_data"

if _container_data.exists():
    DEFAULT_DATA_DIRECTORY = _container_data
else:
    DEFAULT_DATA_DIRECTORY = _local_data

# 允许通过环境变量 DATA_DIRECTORY 覆盖
DATA_DIRECTORY = Path(os.environ.get("DATA_DIRECTORY", str(DEFAULT_DATA_DIRECTORY)))
