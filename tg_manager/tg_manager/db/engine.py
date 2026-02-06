"""
SQLite 数据库引擎与初始化。

约定：
- 使用单文件 SQLite。
- 不实现迁移：当需要改表结构时，通过删除旧数据库文件来重建（MVP 快速迭代策略）。
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """返回 UTC ISO8601 时间字符串（秒级）。"""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect_sqlite(sqlite_path: str) -> sqlite3.Connection:
    """连接 SQLite，并设置常用参数。"""

    if sqlite_path != ":memory:":
        parent = os.path.dirname(os.path.abspath(sqlite_path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(sqlite_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # 常用优化与一致性设置（MVP 单机足够）
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """初始化数据库表（如果不存在则创建）。"""

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          transaction_id TEXT NOT NULL UNIQUE,

          chat_id TEXT,
          message_thread_id INTEGER,

          status TEXT NOT NULL,

          session_start_at TEXT,
          session_end_at TEXT,
          end_reason TEXT,

          message_count INTEGER NOT NULL DEFAULT 0,
          participants_json TEXT NOT NULL DEFAULT '[]',
          metadata_json TEXT NOT NULL DEFAULT '{}',

          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
        """
    )
    conn.commit()

