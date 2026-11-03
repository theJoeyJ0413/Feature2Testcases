"""
后端全局配置
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 自动加载 backend/.env 中的配置（API Key 等）
load_dotenv()

BACKEND_ROOT = Path(__file__).resolve().parent.parent

# 所有生成文件（需求文档、测试用例）的输出根目录
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", BACKEND_ROOT / "output"))


DB_ROOT =  BACKEND_ROOT / "data"
DB_PATH = DB_ROOT / "management.db"
