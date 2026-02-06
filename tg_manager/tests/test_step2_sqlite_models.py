import os
import tempfile
import unittest

from tg_manager.db.engine import connect_sqlite, init_db
from tg_manager.db.models import AlreadyExistsError, create_session, get_session_by_transaction_id, update_session_fields


class TestSqliteModels(unittest.TestCase):
    def test_init_db_creates_sessions_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
                ).fetchone()
                self.assertIsNotNone(row)
            finally:
                conn.close()

    def test_create_and_get_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                s1 = create_session(conn, transaction_id="tx_1")
                got = get_session_by_transaction_id(conn, "tx_1")
                self.assertIsNotNone(got)
                assert got is not None
                self.assertEqual(got.id, s1.id)
                self.assertEqual(got.transaction_id, "tx_1")
                self.assertEqual(got.status, "created")
                self.assertEqual(got.message_count, 0)
            finally:
                conn.close()

    def test_transaction_id_unique(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                create_session(conn, transaction_id="tx_1")
                with self.assertRaises(AlreadyExistsError):
                    create_session(conn, transaction_id="tx_1")
            finally:
                conn.close()

    def test_update_session_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                create_session(conn, transaction_id="tx_1")
                updated = update_session_fields(
                    conn,
                    transaction_id="tx_1",
                    fields={"status": "ended", "end_reason": "api", "message_count": 3},
                )
                self.assertEqual(updated.status, "ended")
                self.assertEqual(updated.end_reason, "api")
                self.assertEqual(updated.message_count, 3)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()

