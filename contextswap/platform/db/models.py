import sqlite3
from dataclasses import dataclass
from typing import Any

from contextswap.platform.db.engine import utc_now_iso


class DbError(RuntimeError):
    pass


class AlreadyExistsError(DbError):
    pass


@dataclass(frozen=True)
class Seller:
    id: int
    seller_id: str
    evm_address: str
    price_wei: int
    description: str
    keywords: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Transaction:
    id: int
    transaction_id: str
    seller_id: str
    buyer_address: str
    price_wei: int
    status: str
    payment_payload_json: str
    requirements_json: str
    tx_hash: str | None
    chat_id: str | None
    message_thread_id: int | None
    metadata_json: str
    error_reason: str | None
    created_at: str
    updated_at: str


def _row_to_seller(row: sqlite3.Row) -> Seller:
    return Seller(
        id=int(row["id"]),
        seller_id=str(row["seller_id"]),
        evm_address=str(row["evm_address"]),
        price_wei=int(row["price_wei"]),
        description=str(row["description"]),
        keywords=str(row["keywords"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _row_to_transaction(row: sqlite3.Row) -> Transaction:
    return Transaction(
        id=int(row["id"]),
        transaction_id=str(row["transaction_id"]),
        seller_id=str(row["seller_id"]),
        buyer_address=str(row["buyer_address"]),
        price_wei=int(row["price_wei"]),
        status=str(row["status"]),
        payment_payload_json=str(row["payment_payload_json"]),
        requirements_json=str(row["requirements_json"]),
        tx_hash=row["tx_hash"],
        chat_id=row["chat_id"],
        message_thread_id=row["message_thread_id"],
        metadata_json=str(row["metadata_json"]),
        error_reason=row["error_reason"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def create_seller(
    conn: sqlite3.Connection,
    *,
    seller_id: str,
    evm_address: str,
    price_wei: int,
    description: str,
    keywords: str,
    status: str,
) -> Seller:
    now = utc_now_iso()
    try:
        cur = conn.execute(
            """
            INSERT INTO sellers (
              seller_id, evm_address, price_wei,
              description, keywords, status,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                seller_id,
                evm_address,
                int(price_wei),
                description,
                keywords,
                status,
                now,
                now,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise AlreadyExistsError(f"seller already exists: seller_id={seller_id}") from exc

    conn.commit()
    got = get_seller_by_id(conn, seller_id=seller_id)
    if got is None:
        raise DbError("failed to read seller after create")
    return got


def get_seller_by_id(conn: sqlite3.Connection, *, seller_id: str) -> Seller | None:
    row = conn.execute("SELECT * FROM sellers WHERE seller_id = ?", (seller_id,)).fetchone()
    return _row_to_seller(row) if row else None


def get_seller_by_address(conn: sqlite3.Connection, *, evm_address: str) -> Seller | None:
    row = conn.execute("SELECT * FROM sellers WHERE evm_address = ?", (evm_address,)).fetchone()
    return _row_to_seller(row) if row else None


def search_sellers(conn: sqlite3.Connection, *, keyword: str) -> list[Seller]:
    kw = (keyword or "").strip().lower()
    if not kw:
        return []

    like = f"%{kw}%"
    rows = conn.execute(
        """
        SELECT * FROM sellers
        WHERE status = 'active'
          AND (lower(keywords) LIKE ? OR lower(description) LIKE ?)
        ORDER BY updated_at DESC
        """,
        (like, like),
    ).fetchall()
    return [_row_to_seller(row) for row in rows]


def update_seller_fields(
    conn: sqlite3.Connection,
    *,
    seller_id: str,
    fields: dict[str, Any],
) -> Seller:
    if not fields:
        got = get_seller_by_id(conn, seller_id=seller_id)
        if got is None:
            raise DbError(f"seller not found: seller_id={seller_id}")
        return got

    forbidden = {"id", "seller_id", "created_at"}
    bad = forbidden.intersection(fields.keys())
    if bad:
        raise ValueError(f"forbidden fields: {sorted(bad)}")

    fields = dict(fields)
    fields["updated_at"] = utc_now_iso()

    columns = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values())
    values.append(seller_id)

    cur = conn.execute(
        f"UPDATE sellers SET {columns} WHERE seller_id = ?",
        values,
    )
    if cur.rowcount != 1:
        raise DbError(f"seller not found: seller_id={seller_id}")
    conn.commit()

    got = get_seller_by_id(conn, seller_id=seller_id)
    if got is None:
        raise DbError("failed to read seller after update")
    return got


def create_transaction(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    seller_id: str,
    buyer_address: str,
    price_wei: int,
    status: str,
    payment_payload_json: str,
    requirements_json: str,
    tx_hash: str | None,
    chat_id: str | None,
    message_thread_id: int | None,
    metadata_json: str,
    error_reason: str | None = None,
) -> Transaction:
    now = utc_now_iso()
    try:
        cur = conn.execute(
            """
            INSERT INTO transactions (
              transaction_id, seller_id, buyer_address,
              price_wei, status,
              payment_payload_json, requirements_json,
              tx_hash, chat_id, message_thread_id,
              metadata_json, error_reason,
              created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                seller_id,
                buyer_address,
                int(price_wei),
                status,
                payment_payload_json,
                requirements_json,
                tx_hash,
                chat_id,
                message_thread_id,
                metadata_json,
                error_reason,
                now,
                now,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise AlreadyExistsError(f"transaction already exists: {transaction_id}") from exc

    conn.commit()
    tx = get_transaction_by_id(conn, transaction_id=transaction_id)
    if tx is None:
        raise DbError("failed to read transaction after create")
    return tx


def get_transaction_by_id(conn: sqlite3.Connection, *, transaction_id: str) -> Transaction | None:
    row = conn.execute(
        "SELECT * FROM transactions WHERE transaction_id = ?",
        (transaction_id,),
    ).fetchone()
    return _row_to_transaction(row) if row else None


def update_transaction_fields(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    fields: dict[str, Any],
) -> Transaction:
    if not fields:
        got = get_transaction_by_id(conn, transaction_id=transaction_id)
        if got is None:
            raise DbError(f"transaction not found: {transaction_id}")
        return got

    forbidden = {"id", "transaction_id", "created_at"}
    bad = forbidden.intersection(fields.keys())
    if bad:
        raise ValueError(f"forbidden fields: {sorted(bad)}")

    fields = dict(fields)
    fields["updated_at"] = utc_now_iso()

    columns = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values())
    values.append(transaction_id)

    cur = conn.execute(
        f"UPDATE transactions SET {columns} WHERE transaction_id = ?",
        values,
    )
    if cur.rowcount != 1:
        raise DbError(f"transaction not found: {transaction_id}")
    conn.commit()

    got = get_transaction_by_id(conn, transaction_id=transaction_id)
    if got is None:
        raise DbError("failed to read transaction after update")
    return got
