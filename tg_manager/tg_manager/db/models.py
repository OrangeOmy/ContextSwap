"""
数据模型（轻量 CRUD）。

说明：
- MVP 阶段优先“能跑通闭环”，不引入 ORM。
- 使用 sqlite3 + 参数化 SQL，减少依赖与心智负担。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from tg_manager.db.engine import utc_now_iso


class DbError(RuntimeError):
    """数据库操作错误。"""


class AlreadyExistsError(DbError):
    """唯一约束等导致的重复创建。"""


@dataclass(frozen=True)
class Session:
    id: int
    transaction_id: str
    chat_id: str | None
    message_thread_id: int | None
    status: str
    session_start_at: str | None
    session_end_at: str | None
    end_reason: str | None
    message_count: int
    participants_json: str
    metadata_json: str
    created_at: str
    updated_at: str


def _row_to_session(row: sqlite3.Row) -> Session:
    return Session(
        id=int(row["id"]),
        transaction_id=str(row["transaction_id"]),
        chat_id=row["chat_id"],
        message_thread_id=row["message_thread_id"],
        status=str(row["status"]),
        session_start_at=row["session_start_at"],
        session_end_at=row["session_end_at"],
        end_reason=row["end_reason"],
        message_count=int(row["message_count"]),
        participants_json=str(row["participants_json"]),
        metadata_json=str(row["metadata_json"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def create_session(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    status: str = "created",
    chat_id: str | None = None,
    message_thread_id: int | None = None,
    session_start_at: str | None = None,
    metadata_json: str = "{}",
) -> Session:
    """创建会话（transaction_id 唯一）。"""

    now = utc_now_iso()
    start_at = session_start_at or now

    try:
        cur = conn.execute(
            """
            INSERT INTO sessions (
              transaction_id, chat_id, message_thread_id,
              status, session_start_at,
              metadata_json,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                chat_id,
                message_thread_id,
                status,
                start_at,
                metadata_json,
                now,
                now,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise AlreadyExistsError(f"会话已存在：transaction_id={transaction_id}") from exc

    conn.commit()
    session_id = int(cur.lastrowid)
    got = get_session_by_id(conn, session_id)
    if got is None:
        raise DbError("创建会话后无法读取（不应发生）")
    return got


def get_session_by_id(conn: sqlite3.Connection, session_id: int) -> Session | None:
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return _row_to_session(row) if row else None


def get_session_by_transaction_id(conn: sqlite3.Connection, transaction_id: str) -> Session | None:
    row = conn.execute(
        "SELECT * FROM sessions WHERE transaction_id = ?",
        (transaction_id,),
    ).fetchone()
    return _row_to_session(row) if row else None


def get_running_session_by_chat_thread(
    conn: sqlite3.Connection,
    *,
    chat_id: str,
    message_thread_id: int,
) -> Session | None:
    """按 chat_id + message_thread_id 查询 running 会话（用于 Telethon 中继路由）。"""

    row = conn.execute(
        "SELECT * FROM sessions WHERE chat_id = ? AND message_thread_id = ? AND status = 'running' LIMIT 1",
        (str(chat_id), int(message_thread_id)),
    ).fetchone()
    return _row_to_session(row) if row else None


def update_session_fields(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    fields: dict[str, Any],
) -> Session:
    """按 transaction_id 更新字段（仅用于内部受控调用）。"""

    if not fields:
        got = get_session_by_transaction_id(conn, transaction_id)
        if got is None:
            raise DbError(f"会话不存在：transaction_id={transaction_id}")
        return got

    # 防御性：避免更新主键与审计字段
    forbidden = {"id", "transaction_id", "created_at"}
    bad = forbidden.intersection(fields.keys())
    if bad:
        raise ValueError(f"不允许更新字段：{sorted(bad)}")

    fields = dict(fields)
    fields["updated_at"] = utc_now_iso()

    columns = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values())
    values.append(transaction_id)

    cur = conn.execute(
        f"UPDATE sessions SET {columns} WHERE transaction_id = ?",
        values,
    )
    if cur.rowcount != 1:
        raise DbError(f"会话不存在或更新失败：transaction_id={transaction_id}")
    conn.commit()

    got = get_session_by_transaction_id(conn, transaction_id)
    if got is None:
        raise DbError("更新会话后无法读取（不应发生）")
    return got
