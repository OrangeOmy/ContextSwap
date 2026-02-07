import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from contextswap.config import load_tron_env
from contextswap.facilitator.client import DirectFacilitatorClient
from contextswap.facilitator.tron import TronFacilitator
from contextswap.seller.tron_api import create_tron_seller_app
from contextswap.x402_tron import b64decode_json, b64encode_json, build_payment


class Phase1DemoTronTest(unittest.TestCase):
    def test_phase1_flow_tron(self) -> None:
        env = load_tron_env()

        facilitator = TronFacilitator(env.rpc_url, env.api_key)
        facilitator_client = DirectFacilitatorClient(facilitator)

        seller_app = create_tron_seller_app(facilitator_client, env.seller_address)
        seller_client = TestClient(seller_app)

        first = seller_client.get("/weather")
        self.assertEqual(first.status_code, 402, msg=first.text)

        payment_required = first.headers.get("PAYMENT-REQUIRED")
        self.assertTrue(payment_required)

        requirements = b64decode_json(payment_required)
        payment = build_payment(
            requirements,
            env.rpc_url,
            env.buyer_address,
            env.buyer_private_key,
            env.api_key,
        )

        second = seller_client.get(
            "/weather",
            headers={"PAYMENT-SIGNATURE": b64encode_json(payment)},
        )
        self.assertEqual(second.status_code, 200, msg=second.text)

        payment_response = second.headers.get("PAYMENT-RESPONSE")
        if payment_response:
            decoded = b64decode_json(payment_response)
            self.assertIn("txHash", decoded)


if __name__ == "__main__":
    unittest.main()
