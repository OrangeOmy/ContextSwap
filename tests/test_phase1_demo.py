import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from contextswap.config import load_env
from contextswap.facilitator.client import DirectFacilitatorClient
from contextswap.facilitator.conflux import ConfluxFacilitator
from contextswap.seller.api import create_seller_app
from contextswap.x402 import b64decode_json, b64encode_json, build_payment


class Phase1DemoTest(unittest.TestCase):
    def test_phase1_flow(self) -> None:
        env = load_env()

        facilitator = ConfluxFacilitator(env.rpc_url)
        facilitator_client = DirectFacilitatorClient(facilitator)

        seller_app = create_seller_app(facilitator_client, env.seller_address)
        seller_client = TestClient(seller_app)

        first = seller_client.get("/weather")
        self.assertEqual(first.status_code, 402, msg=first.text)

        payment_required = first.headers.get("PAYMENT-REQUIRED")
        self.assertTrue(payment_required)

        requirements = b64decode_json(payment_required)
        payment = build_payment(
            requirements,
            facilitator.web3,
            env.buyer_address,
            env.buyer_private_key,
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
