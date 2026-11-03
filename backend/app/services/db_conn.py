import sqlite3

from ..config import DB_PATH


def _connect():
    """创建数据库连接，每次操作独立连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10) #写锁被占用时最多等10秒
    conn.execute("PRAGMA journal_mode = WAL")   #WAL mode：读写不互斥
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn