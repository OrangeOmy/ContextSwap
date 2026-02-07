import unittest

from eth_account import Account
from fastapi.testclient import TestClient

from contextswap.facilitator.base import BaseFacilitator
from contextswap.facilitator.client import DirectFacilitatorClient
from contextswap.platform.api.app import create_app
from contextswap.platform.config import Settings
from contextswap.platform.services import transaction_service
from contextswap.x402 import CHAIN_ID, NETWORK_ID, b64decode_json, b64encode_json


class TestFacilitator(BaseFacilitator):
    def __init__(self) -> None:
        super().__init__(CHAIN_ID, NETWORK_ID)

    def send_raw_transaction(self, raw_hex: str) -> str:
        return transaction_service.compute_tx_hash(raw_hex)


class FakeTelegramService:
    def __init__(self) -> None:
        self._next_topic_id = 300
        self.created_topics: list[tuple[str, str]] = []
        self.sent_messages: list[tuple[str, int, str]] = []
        self.closed_topics: list[tuple[str, int]] = []

    async def create_topic(self, *, chat_id: str, title: str) -> int:
        self.created_topics.append((chat_id, title))
        self._next_topic_id += 1
        return self._next_topic_id

    async def send_message(self, *, chat_id: str, message_thread_id: int, text: str) -> int:
        self.sent_messages.append((chat_id, int(message_thread_id), text))
        return 1

    async def close_topic(self, *, chat_id: str, message_thread_id: int) -> None:
        self.closed_topics.append((chat_id, int(message_thread_id)))


def build_payment_payload(requirements: dict, buyer_private_key: bytes) -> dict:
    accepts = requirements["accepts"][0]
    tx = {
        "to": accepts["payTo"],
        "value": int(accepts["amountWei"]),
        "gas": 21000,
        "gasPrice": 1,
        "nonce": 0,
        "chainId": CHAIN_ID,
    }
    signed = Account.sign_transaction(tx, buyer_private_key)
    raw_tx = signed.raw_transaction.hex()
    buyer_address = Account.from_key(buyer_private_key).address
    return {
        "x402Version": requirements["x402Version"],
        "scheme": accepts.get("scheme", "exact"),
        "network": accepts.get("network", NETWORK_ID),
        "from": buyer_address,
        "to": accepts["payTo"],
        "amountWei": str(accepts["amountWei"]),
        "rawTransaction": raw_tx,
    }


class UnifiedIntegrationFlowTest(unittest.TestCase):
    def _build_settings(self, *, sqlite_path: str) -> Settings:
        return Settings(
            sqlite_path=sqlite_path,
            rpc_url="http://localhost:8545",
            facilitator_base_url=None,
            tg_manager_mode="inprocess",
            tg_manager_base_url=None,
            tg_manager_auth_token="ops-token",
            tg_manager_sqlite_path=":memory:",
            tg_manager_market_chat_id="-1001234567890",
        )

    def test_unified_payment_and_session_happy_path(self) -> None:
        facilitator = DirectFacilitatorClient(TestFacilitator())
        fake_tg = FakeTelegramService()
        app = create_app(
            self._build_settings(sqlite_path=":memory:"),
            facilitator_client=facilitator,
            tg_manager_telegram_service=fake_tg,
        )
        with TestClient(app) as client:
            seller_account = Account.create()
            buyer_account = Account.create()

            register = client.post(
                "/v1/sellers/register",
                json={
                    "evm_address": seller_account.address,
                    "price_wei": 1000,
                    "description": "seller",
                    "keywords": ["weather"],
                },
            )
            self.assertEqual(register.status_code, 200, register.text)
            seller_id = register.json()["seller_id"]

            search = client.get("/v1/sellers/search", params={"keyword": "weather"})
            self.assertEqual(search.status_code, 200, search.text)
            self.assertEqual(search.json()["items"][0]["seller_id"], seller_id)

            create_payload = {
                "seller_id": seller_id,
                "buyer_address": buyer_account.address,
                "buyer_bot_username": "buyer_bot",
                "seller_bot_username": "seller_bot",
                "initial_prompt": "give me final report",
            }

            phase1 = client.post("/v1/transactions/create", json=create_payload)
            self.assertEqual(phase1.status_code, 402, phase1.text)
            self.assertIn("PAYMENT-REQUIRED", phase1.headers)
            requirements = b64decode_json(phase1.headers["PAYMENT-REQUIRED"])
            payment_payload = build_payment_payload(requirements, buyer_account.key)

            phase2 = client.post(
                "/v1/transactions/create",
                json=create_payload,
                headers={"PAYMENT-SIGNATURE": b64encode_json(payment_payload)},
            )
            self.assertEqual(phase2.status_code, 200, phase2.text)
            body = phase2.json()

            expected_tx_hash = transaction_service.compute_tx_hash(payment_payload["rawTransaction"])
            self.assertEqual(body["transaction_id"], expected_tx_hash)
            self.assertEqual(body["transaction_id"], body["tx_hash"])
            self.assertEqual(body["status"], "session_created")
            self.assertEqual(body["session"]["chat_id"], "-1001234567890")
            self.assertIsInstance(body["session"]["message_thread_id"], int)

            payment_response = b64decode_json(phase2.headers["PAYMENT-RESPONSE"])
            self.assertEqual(payment_response["txHash"], expected_tx_hash)

            tx_detail = client.get(f"/v1/transactions/{expected_tx_hash}")
            self.assertEqual(tx_detail.status_code, 200, tx_detail.text)
            self.assertEqual(tx_detail.json()["message_thread_id"], body["session"]["message_thread_id"])

            no_auth = client.get(f"/v1/session/{expected_tx_hash}")
            self.assertEqual(no_auth.status_code, 401)

            session = client.get(
                f"/v1/session/{expected_tx_hash}",
                headers={"Authorization": "Bearer ops-token"},
            )
            self.assertEqual(session.status_code, 200, session.text)
            self.assertEqual(session.json()["status"], "running")

            ended = client.post(
                "/v1/session/end",
                headers={"Authorization": "Bearer ops-token"},
                json={"transaction_id": expected_tx_hash},
            )
            self.assertEqual(ended.status_code, 200, ended.text)
            self.assertEqual(ended.json()["status"], "ended")
            self.assertEqual(ended.json()["end_reason"], "api")
            self.assertEqual(len(fake_tg.closed_topics), 1)

    def test_unified_create_transaction_fails_when_telethon_not_configured(self) -> None:
        facilitator = DirectFacilitatorClient(TestFacilitator())
        app = create_app(
            self._build_settings(sqlite_path=":memory:"),
            facilitator_client=facilitator,
        )
        with TestClient(app) as client:
            seller_account = Account.create()
            buyer_account = Account.create()

            register = client.post(
                "/v1/sellers/register",
                json={
                    "evm_address": seller_account.address,
                    "price_wei": 1000,
                    "description": "seller",
                    "keywords": ["weather"],
                },
            )
            self.assertEqual(register.status_code, 200, register.text)
            seller_id = register.json()["seller_id"]

            create_payload = {
                "seller_id": seller_id,
                "buyer_address": buyer_account.address,
                "buyer_bot_username": "buyer_bot",
                "seller_bot_username": "seller_bot",
                "initial_prompt": "hello",
            }

            phase1 = client.post("/v1/transactions/create", json=create_payload)
            self.assertEqual(phase1.status_code, 402, phase1.text)
            requirements = b64decode_json(phase1.headers["PAYMENT-REQUIRED"])
            payment_payload = build_payment_payload(requirements, buyer_account.key)
            expected_tx_hash = transaction_service.compute_tx_hash(payment_payload["rawTransaction"])

            phase2 = client.post(
                "/v1/transactions/create",
                json=create_payload,
                headers={"PAYMENT-SIGNATURE": b64encode_json(payment_payload)},
            )
            self.assertEqual(phase2.status_code, 502, phase2.text)

            tx_detail = client.get(f"/v1/transactions/{expected_tx_hash}")
            self.assertEqual(tx_detail.status_code, 200, tx_detail.text)
            detail_body = tx_detail.json()
            self.assertEqual(detail_body["status"], "paid")
            self.assertIn("telethon is not configured", detail_body["error_reason"])


if __name__ == "__main__":
    unittest.main()
