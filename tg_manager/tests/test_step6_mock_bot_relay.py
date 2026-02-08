import json
import os
import tempfile
import unittest
from types import SimpleNamespace

from tg_manager.db.engine import connect_sqlite, init_db
from tg_manager.db.models import create_session
from tg_manager.services.mock_bot_relay import MockBotRelay, parse_mock_bots


class _FakeClient:
    async def get_input_entity(self, peer_id: int) -> int:
        return int(peer_id)


class _FakeRelay:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def relay_as_username(self, session, *, sender_username: str, source_text: str) -> None:
        self.calls.append((session.transaction_id, sender_username, source_text))


class TestMockBotRelay(unittest.IsolatedAsyncioTestCase):
    async def test_parse_mock_bots_defaults(self) -> None:
        parsed = parse_mock_bots(
            enabled=True,
            raw_json=None,
            market_slug="demo-market",
        )
        self.assertIn("polling_data_bot", parsed)
        self.assertIn("official_media_bot", parsed)
        self.assertIn("social_signal_bot", parsed)

    async def test_only_seller_mention_triggers_mock_reply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                create_session(
                    conn,
                    transaction_id="tx_mock",
                    status="running",
                    chat_id="-1001234567890",
                    message_thread_id=900,
                    metadata_json=json.dumps(
                        {
                            "buyer_bot_username": "buyer_bot",
                            "seller_bot_username": "polling_data_bot",
                        },
                        ensure_ascii=False,
                    ),
                )

                relay = _FakeRelay()
                mock = MockBotRelay(
                    client=_FakeClient(),
                    conn=conn,
                    market_chat_id="-1001234567890",
                    relay=relay,
                    responses={"polling_data_bot": "fixed response"},
                    seller_auto_end=True,
                )

                event = SimpleNamespace(
                    message=SimpleNamespace(
                        id=1,
                        raw_text="@polling_data_bot 请给结论",
                        reply_to=SimpleNamespace(reply_to_top_id=900),
                    )
                )
                await mock._on_new_message(event)

                self.assertEqual(len(relay.calls), 1)
                tx, sender, source = relay.calls[0]
                self.assertEqual(tx, "tx_mock")
                self.assertEqual(sender, "polling_data_bot")
                self.assertIn("fixed response", source)
                self.assertIn("[READY_TO_FORWARD]", source)
                self.assertIn("[END_OF_REPORT]", source)
            finally:
                conn.close()

    async def test_seller_auto_end_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.sqlite3")
            conn = connect_sqlite(db_path)
            try:
                init_db(conn)
                create_session(
                    conn,
                    transaction_id="tx_mock_no_end",
                    status="running",
                    chat_id="-1001234567890",
                    message_thread_id=901,
                    metadata_json=json.dumps(
                        {
                            "buyer_bot_username": "buyer_bot",
                            "seller_bot_username": "official_media_bot",
                        },
                        ensure_ascii=False,
                    ),
                )

                relay = _FakeRelay()
                mock = MockBotRelay(
                    client=_FakeClient(),
                    conn=conn,
                    market_chat_id="-1001234567890",
                    relay=relay,
                    responses={"official_media_bot": "stable response"},
                    seller_auto_end=False,
                )

                event = SimpleNamespace(
                    message=SimpleNamespace(
                        id=2,
                        raw_text="@official_media_bot 请补充",
                        reply_to=SimpleNamespace(reply_to_top_id=901),
                    )
                )
                await mock._on_new_message(event)

                self.assertEqual(len(relay.calls), 1)
                source = relay.calls[0][2]
                self.assertIn("[READY_TO_FORWARD]", source)
                self.assertNotIn("[END_OF_REPORT]", source)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
