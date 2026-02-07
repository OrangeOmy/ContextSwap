import json
import unittest

import httpx

from contextswap.platform.services.tg_manager_client import TgManagerClient


class TgManagerClientTest(unittest.TestCase):
    def test_create_session(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.headers.get("Authorization"), "Bearer token")
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
        tg.close()


if __name__ == "__main__":
    unittest.main()
