import unittest

from eth_account import Account
from fastapi import Response
from starlette.requests import Request

from contextswap.facilitator.base import BaseFacilitator
from contextswap.facilitator.client import DirectFacilitatorClient
from contextswap.platform.api.routes.transactions import TransactionCreateRequest, create_transaction
from contextswap.platform.config import Settings
from contextswap.platform.db import models
from contextswap.platform.db.engine import connect_sqlite, init_db
from contextswap.platform.services import seller_service, transaction_service
from contextswap.x402 import CHAIN_ID, NETWORK_ID, b64decode_json, b64encode_json


class TestFacilitator(BaseFacilitator):
    def __init__(self) -> None:
        super().__init__(CHAIN_ID, NETWORK_ID)

    def send_raw_transaction(self, raw_hex: str) -> str:
        return transaction_service.compute_tx_hash(raw_hex)


class FakeTgManagerClient:
    def __init__(self) -> None:
        self.last_payload = None

    def create_session(self, **kwargs):
        self.last_payload = kwargs
        return {
            "transaction_id": kwargs["transaction_id"],
            "status": "running",
            "chat_id": "-100123",
            "message_thread_id": 456,
        }

    def close(self) -> None:
        return None


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


class TransactionFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        settings = Settings(
            sqlite_path=":memory:",
            rpc_url="http://localhost:8545",
            tron_rpc_url=None,
            tron_api_key=None,
            facilitator_base_url=None,
            tg_manager_mode="http",
            tg_manager_base_url=None,
            tg_manager_auth_token=None,
            tg_manager_sqlite_path=":memory:",
            tg_manager_market_chat_id=None,
        )
        self.conn = connect_sqlite(settings.sqlite_path)
        init_db(self.conn)
        self.facilitator = DirectFacilitatorClient(TestFacilitator())
        self.tg_manager = FakeTgManagerClient()

    def tearDown(self) -> None:
        self.conn.close()

    def _make_request(self, payment_header: str | None) -> Request:
        headers = []
        if payment_header:
            headers.append((b"payment-signature", payment_header.encode("ascii")))
        scope = {
            "type": "http",
            "headers": headers,
        }
        return Request(scope)

    def test_payment_flow(self) -> None:
        seller_account = Account.create()
        buyer_account = Account.create()

        seller = seller_service.register_seller(
            self.conn,
            evm_address=seller_account.address,
            price_wei=1000,
            description="seller one",
            keywords=["k1"],
            seller_id=None,
        )

        payload = TransactionCreateRequest(
            seller_id=seller.seller_id,
            buyer_address=buyer_account.address,
            buyer_bot_username="buyer_bot",
            seller_bot_username="seller_bot",
            initial_prompt="test prompt",
        )

        response = Response()
        create_resp = create_transaction(
            payload,
            request=self._make_request(None),
            response=response,
            conn=self.conn,
            facilitator=self.facilitator,
            tg_manager=self.tg_manager,
        )
        self.assertEqual(response.status_code, 402)
        requirements_b64 = response.headers.get("PAYMENT-REQUIRED")
        self.assertTrue(requirements_b64)

        requirements = b64decode_json(requirements_b64)
        payment = build_payment_payload(requirements, buyer_account.key)

        response = Response()
        body = create_transaction(
            payload,
            request=self._make_request(b64encode_json(payment)),
            response=response,
            conn=self.conn,
            facilitator=self.facilitator,
            tg_manager=self.tg_manager,
        )
        self.assertEqual(response.status_code, 200)
        expected_tx_hash = transaction_service.compute_tx_hash(payment["rawTransaction"])
        self.assertEqual(body["transaction_id"], expected_tx_hash)
        self.assertEqual(body["status"], "session_created")
        self.assertIn("session", body)

        self.assertIsNotNone(self.tg_manager.last_payload)
        self.assertEqual(self.tg_manager.last_payload["transaction_id"], expected_tx_hash)

        stored_tx = models.get_transaction_by_id(self.conn, transaction_id=expected_tx_hash)
        self.assertIsNotNone(stored_tx)
        stored = transaction_service.transaction_to_dict(stored_tx)  # type: ignore[arg-type]
        self.assertEqual(stored["status"], "session_created")


if __name__ == "__main__":
    unittest.main()
