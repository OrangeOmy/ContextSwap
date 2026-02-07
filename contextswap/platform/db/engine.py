import os
import sqlite3
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect_sqlite(sqlite_path: str) -> sqlite3.Connection:
    if sqlite_path != ":memory:":
        parent = os.path.dirname(os.path.abspath(sqlite_path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(sqlite_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sellers (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          seller_id TEXT NOT NULL UNIQUE,
          evm_address TEXT NOT NULL,
          price_wei INTEGER NOT NULL,
          description TEXT NOT NULL,
          keywords TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sellers_status ON sellers(status);
        CREATE INDEX IF NOT EXISTS idx_sellers_keywords ON sellers(keywords);

        CREATE TABLE IF NOT EXISTS transactions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          transaction_id TEXT NOT NULL UNIQUE,
          seller_id TEXT NOT NULL,
          buyer_address TEXT NOT NULL,
          price_wei INTEGER NOT NULL,
          status TEXT NOT NULL,
          payment_payload_json TEXT NOT NULL,
          requirements_json TEXT NOT NULL,
          tx_hash TEXT,
          chat_id TEXT,
          message_thread_id INTEGER,
          metadata_json TEXT NOT NULL,
          error_reason TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        );

        CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
        CREATE INDEX IF NOT EXISTS idx_transactions_seller_id ON transactions(seller_id);
        """
    )
    conn.commit()
