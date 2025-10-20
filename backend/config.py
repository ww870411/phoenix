"""
全局配置常量。

提供统一的数据目录常量，避免在代码中硬编码宿主路径。
"""

import os
from pathlib import Path

# 默认数据目录指向容器内的绑定挂载路径
DEFAULT_DATA_DIRECTORY = Path("/app/data")

# 允许通过环境变量 DATA_DIRECTORY 覆盖，默认仍指向 /app/data
DATA_DIRECTORY = Path(os.environ.get("DATA_DIRECTORY", str(DEFAULT_DATA_DIRECTORY)))
