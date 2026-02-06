import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from tg_manager.api.app import create_app
from tg_manager.core.config import load_settings


class _FakeTelegram:
    def __init__(self) -> None:
        self.created_topics: list[tuple[str, str]] = []
        self.sent_messages: list[tuple[str, int, str]] = []
        self.closed_topics: list[tuple[str, int]] = []
        self._next_thread_id = 100

    async def create_topic(self, *, chat_id: str, title: str) -> int:
        self.created_topics.append((chat_id, title))
        self._next_thread_id += 1
        return self._next_thread_id

    async def send_message(self, *, chat_id: str, message_thread_id: int, text: str) -> int:
        self.sent_messages.append((chat_id, int(message_thread_id), text))
        return 1

    async def close_topic(self, *, chat_id: str, message_thread_id: int) -> None:
        self.closed_topics.append((chat_id, int(message_thread_id)))

    def close(self) -> None:
        return None


@contextmanager
def _test_client():
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "test.sqlite3")
        token = "secret"
        market_chat_id = "-1001234567890"
        with patch.dict(
            "os.environ",
            {"API_AUTH_TOKEN": token, "SQLITE_PATH": db_path, "MARKET_CHAT_ID": market_chat_id},
            clear=True,
        ):
            settings = load_settings()
        fake_tg = _FakeTelegram()
        app = create_app(settings, telegram_service=fake_tg)  # 注入 mock，避免真实打 Telegram
        with TestClient(app) as client:
            yield client, token, fake_tg


class TestHttpApiStep3(unittest.TestCase):
    def test_healthz_ok(self) -> None:
        with _test_client() as (client, _, _tg):
            resp = client.get("/healthz")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json().get("status"), "ok")

    def test_create_auth_missing(self) -> None:
        with _test_client() as (client, _, _tg):
            resp = client.post(
                "/v1/session/create",
                json={
                    "transaction_id": "tx_1",
                    "buyer_bot_username": "buyer",
                    "seller_bot_username": "seller",
                    "initial_prompt": "hi",
                },
            )
            self.assertEqual(resp.status_code, 401)

    def test_create_auth_wrong_token(self) -> None:
        with _test_client() as (client, _, _tg):
            resp = client.post(
                "/v1/session/create",
                headers={"Authorization": "Bearer wrong"},
                json={
                    "transaction_id": "tx_1",
                    "buyer_bot_username": "buyer",
                    "seller_bot_username": "seller",
                },
            )
            self.assertEqual(resp.status_code, 403)

    def test_create_idempotent_and_get_and_end(self) -> None:
        with _test_client() as (client, token, tg):
            headers = {"Authorization": f"Bearer {token}"}

            resp1 = client.post(
                "/v1/session/create",
                headers=headers,
                json={
                    "transaction_id": "tx_1",
                    "buyer_bot_username": "buyer_bot",
                    "seller_bot_username": "seller_bot",
                    "initial_prompt": "请给出报告",
                },
            )
            self.assertEqual(resp1.status_code, 200)
            data1 = resp1.json()
            self.assertEqual(data1["transaction_id"], "tx_1")
            self.assertEqual(data1["status"], "running")
            self.assertIsInstance(data1["session_id"], int)
            self.assertEqual(data1["chat_id"], "-1001234567890")
            self.assertIsNotNone(data1["message_thread_id"])

            meta1 = json.loads(data1["metadata_json"])
            self.assertEqual(meta1["buyer_bot_username"], "buyer_bot")
            self.assertEqual(meta1["seller_bot_username"], "seller_bot")
            self.assertEqual(meta1["initial_prompt"], "请给出报告")
            self.assertFalse(meta1["telegram_stub"])

            self.assertEqual(len(tg.created_topics), 1)
            self.assertEqual(len(tg.sent_messages), 1)
            sent_text = tg.sent_messages[0][2]
            self.assertIn("@buyer_bot", sent_text)
            self.assertIn("@seller_bot", sent_text)
            self.assertIn("初始指令：", sent_text)
            self.assertIn("请给出报告", sent_text)

            resp2 = client.post(
                "/v1/session/create",
                headers=headers,
                json={
                    "transaction_id": "tx_1",
                    "buyer_bot_username": "buyer_bot",
                    "seller_bot_username": "seller_bot",
                    "initial_prompt": "再次创建（应幂等）",
                },
            )
            self.assertEqual(resp2.status_code, 200)
            data2 = resp2.json()
            self.assertEqual(data2["session_id"], data1["session_id"])
            self.assertEqual(data2["created_at"], data1["created_at"])
            self.assertEqual(data2["metadata_json"], data1["metadata_json"])

            # 幂等：不应再次创建 Topic / 发送注入消息
            self.assertEqual(len(tg.created_topics), 1)
            self.assertEqual(len(tg.sent_messages), 1)

            got = client.get("/v1/session/tx_1", headers=headers)
            self.assertEqual(got.status_code, 200)
            got_data = got.json()
            self.assertEqual(got_data["session_id"], data1["session_id"])
            self.assertEqual(got_data["transaction_id"], "tx_1")

            not_found = client.get("/v1/session/tx_not_exist", headers=headers)
            self.assertEqual(not_found.status_code, 404)

            end1 = client.post("/v1/session/end", headers=headers, json={"transaction_id": "tx_1"})
            self.assertEqual(end1.status_code, 200)
            end_data1 = end1.json()
            self.assertEqual(end_data1["status"], "ended")
            self.assertEqual(end_data1["end_reason"], "api")
            self.assertIsNotNone(end_data1["session_end_at"])
            self.assertEqual(len(tg.closed_topics), 1)

            # 再次结束应幂等：不覆盖 end_reason
            end2 = client.post(
                "/v1/session/end",
                headers=headers,
                json={"transaction_id": "tx_1", "reason": "manual"},
            )
            self.assertEqual(end2.status_code, 200)
            end_data2 = end2.json()
            self.assertEqual(end_data2["status"], "ended")
            self.assertEqual(end_data2["end_reason"], "api")
            self.assertEqual(len(tg.closed_topics), 1)

    def test_create_force_reinject_sends_second_message(self) -> None:
        with _test_client() as (client, token, tg):
            headers = {"Authorization": f"Bearer {token}"}

            resp1 = client.post(
                "/v1/session/create",
                headers=headers,
                json={
                    "transaction_id": "tx_reinject",
                    "buyer_bot_username": "buyer_bot",
                    "seller_bot_username": "seller_bot",
                    "initial_prompt": "第一次",
                },
            )
            self.assertEqual(resp1.status_code, 200)
            self.assertEqual(len(tg.sent_messages), 1)

            resp2 = client.post(
                "/v1/session/create",
                headers=headers,
                json={
                    "transaction_id": "tx_reinject",
                    "buyer_bot_username": "buyer_bot",
                    "seller_bot_username": "seller_bot",
                    "initial_prompt": "第二次（强制重新注入）",
                    "force_reinject": True,
                },
            )
            self.assertEqual(resp2.status_code, 200)
            self.assertEqual(len(tg.sent_messages), 2)
            sent_text = tg.sent_messages[1][2]
            self.assertIn("@buyer_bot", sent_text)
            self.assertIn("@seller_bot", sent_text)
            self.assertIn("第二次（强制重新注入）", sent_text)

    def test_create_accepts_at_prefix_and_normalizes(self) -> None:
        with _test_client() as (client, token, tg):
            headers = {"Authorization": f"Bearer {token}"}

            resp = client.post(
                "/v1/session/create",
                headers=headers,
                json={
                    "transaction_id": "tx_2",
                    "buyer_bot_username": "@buyer_bot",
                    "seller_bot_username": "@seller_bot",
                    "initial_prompt": "请开始对话",
                },
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            meta = json.loads(data["metadata_json"])
            self.assertEqual(meta["buyer_bot_username"], "buyer_bot")
            self.assertEqual(meta["seller_bot_username"], "seller_bot")

            self.assertEqual(len(tg.created_topics), 1)
            self.assertEqual(len(tg.sent_messages), 1)
            sent_text = tg.sent_messages[0][2]
            self.assertIn("@buyer_bot", sent_text)
            self.assertIn("@seller_bot", sent_text)


if __name__ == "__main__":
    unittest.main()
