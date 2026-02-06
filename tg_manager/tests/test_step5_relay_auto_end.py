import json
import os
import tempfile
import unittest

from tg_manager.db.engine import connect_sqlite, init_db
from tg_manager.db.models import create_session, get_session_by_transaction_id
from tg_manager.services.session_service import RELAY_FLUSH_MARKER, SESSION_END_MARKER
from tg_manager.services.telethon_relay import TelethonRelay


class _FakeClient:
    def __init__(self) -> None:
        self.operations: list[str] = []
        self.sent_messages: list[tuple[int, str, int]] = []
        self.close_requests: list[object] = []

    async def get_input_entity(self, peer_id: int) -> int:
        return int(peer_id)

    async def send_message(self, peer: int, text: str, reply_to: int) -> int:
        self.operations.append("send_message")
        self.sent_messages.append((int(peer), text, int(reply_to)))
        return 1

    async def __call__(self, request: object) -> None:
        self.operations.append("close_topic")
        self.close_requests.append(request)


class TestRelayAutoEnd(unittest.IsolatedAsyncioTestCase):
    async def test_only_flush_marker_will_trigger_batch_forward(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                create_session(
                    conn,
                    transaction_id="tx_buffer",
                    status="running",
                    chat_id="-1001234567890",
                    message_thread_id=777,
                    metadata_json=json.dumps(
                        {
                            "buyer_bot_username": "buyer_bot",
                            "seller_bot_username": "seller_bot",
                        },
                        ensure_ascii=False,
                    ),
                )
                session = get_session_by_transaction_id(conn, "tx_buffer")
                assert session is not None

                fake_client = _FakeClient()
                relay = TelethonRelay(client=fake_client, conn=conn, market_chat_id="-1001234567890")

                await relay._maybe_relay(
                    session,
                    sender_username="seller_bot",
                    source_text="第一段",
                )
                await relay._maybe_relay(
                    session,
                    sender_username="seller_bot",
                    source_text=f"第二段 {RELAY_FLUSH_MARKER}",
                )

                self.assertEqual(fake_client.operations, ["send_message"])
                self.assertEqual(len(fake_client.sent_messages), 1)
                sent_text = fake_client.sent_messages[0][1]
                self.assertIn("第一段", sent_text)
                self.assertIn("第二段", sent_text)
                self.assertNotIn(RELAY_FLUSH_MARKER, sent_text)
                self.assertEqual(fake_client.sent_messages[0][2], 777)
            finally:
                conn.close()

    async def test_seller_final_flush_with_end_marker_forward_then_close(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                create_session(
                    conn,
                    transaction_id="tx_auto_end",
                    status="running",
                    chat_id="-1001234567890",
                    message_thread_id=778,
                    metadata_json=json.dumps(
                        {
                            "buyer_bot_username": "buyer_bot",
                            "seller_bot_username": "seller_bot",
                        },
                        ensure_ascii=False,
                    ),
                )
                session = get_session_by_transaction_id(conn, "tx_auto_end")
                assert session is not None

                fake_client = _FakeClient()
                relay = TelethonRelay(client=fake_client, conn=conn, market_chat_id="-1001234567890")

                await relay._maybe_relay(
                    session,
                    sender_username="seller_bot",
                    source_text="最终报告正文",
                )
                await relay._maybe_relay(
                    session,
                    sender_username="seller_bot",
                    source_text=f"收尾 {SESSION_END_MARKER} {RELAY_FLUSH_MARKER}",
                )

                ended = get_session_by_transaction_id(conn, "tx_auto_end")
                assert ended is not None
                self.assertEqual(ended.status, "ended")
                self.assertEqual(ended.end_reason, "end_marker")
                self.assertEqual(fake_client.operations, ["send_message", "close_topic"])
                sent_text = fake_client.sent_messages[0][1]
                self.assertIn(SESSION_END_MARKER, sent_text)
                self.assertNotIn(RELAY_FLUSH_MARKER, sent_text)
                self.assertEqual(fake_client.sent_messages[0][2], 778)
            finally:
                conn.close()

    async def test_buyer_with_end_marker_will_not_close_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                create_session(
                    conn,
                    transaction_id="tx_buyer",
                    status="running",
                    chat_id="-1001234567890",
                    message_thread_id=779,
                    metadata_json=json.dumps(
                        {
                            "buyer_bot_username": "buyer_bot",
                            "seller_bot_username": "seller_bot",
                        },
                        ensure_ascii=False,
                    ),
                )
                session = get_session_by_transaction_id(conn, "tx_buyer")
                assert session is not None

                fake_client = _FakeClient()
                relay = TelethonRelay(client=fake_client, conn=conn, market_chat_id="-1001234567890")
                await relay._maybe_relay(
                    session,
                    sender_username="buyer_bot",
                    source_text=f"buyer 误发 {SESSION_END_MARKER} {RELAY_FLUSH_MARKER}",
                )

                running = get_session_by_transaction_id(conn, "tx_buyer")
                assert running is not None
                self.assertEqual(running.status, "running")
                self.assertEqual(fake_client.operations, ["send_message"])
                self.assertEqual(len(fake_client.close_requests), 0)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
