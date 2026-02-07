import json
import unittest

import httpx

from contextswap.platform.services.tg_manager_client import TgManagerClient


class TgManagerClientTest(unittest.TestCase):
    def test_create_get_end_session(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers.get("Authorization"), "Bearer token")
            if request.method == "POST" and request.url.path == "/v1/session/create":
                payload = json.loads(request.content.decode("utf-8"))
                self.assertEqual(payload["transaction_id"], "tx_1")
                return httpx.Response(
                    200,
                    json={
                        "transaction_id": "tx_1",
                        "status": "running",
                        "chat_id": "-1001",
                        "message_thread_id": 9,
                    },
                )
            if request.method == "GET" and request.url.path == "/v1/session/tx_1":
                return httpx.Response(
                    200,
                    json={
                        "transaction_id": "tx_1",
                        "status": "running",
                        "chat_id": "-1001",
                        "message_thread_id": 9,
                    },
                )
            if request.method == "POST" and request.url.path == "/v1/session/end":
                payload = json.loads(request.content.decode("utf-8"))
                self.assertEqual(payload["transaction_id"], "tx_1")
                self.assertEqual(payload["reason"], "api")
                return httpx.Response(
                    200,
                    json={
                        "transaction_id": "tx_1",
                        "status": "ended",
                        "end_reason": "api",
                    },
                )
            return httpx.Response(500, json={"detail": "unexpected request"})

        transport = httpx.MockTransport(handler)
        client = httpx.Client(transport=transport)
        tg = TgManagerClient("http://example.com", "token", client=client)

        resp = tg.create_session(
            transaction_id="tx_1",
            buyer_bot_username="buyer",
            seller_bot_username="seller",
            initial_prompt="hi",
        )
        self.assertEqual(resp["message_thread_id"], 9)

        got = tg.get_session(transaction_id="tx_1")
        self.assertEqual(got["status"], "running")

        ended = tg.end_session(transaction_id="tx_1", reason="api")
        self.assertEqual(ended["status"], "ended")
        tg.close()


if __name__ == "__main__":
    unittest.main()
