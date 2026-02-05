import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient

from contextswap.config import load_env
from contextswap.facilitator.client import DirectFacilitatorClient
from contextswap.facilitator.conflux import ConfluxFacilitator
from contextswap.seller.api import create_seller_app
from contextswap.x402 import b64decode_json, b64encode_json, build_payment


def main() -> None:
    env = load_env()

    facilitator = ConfluxFacilitator(env.rpc_url)
    facilitator_client = DirectFacilitatorClient(facilitator)

    seller_app = create_seller_app(facilitator_client, env.seller_address)
    seller_client = TestClient(seller_app)

    first = seller_client.get("/weather")
    if first.status_code != 402:
        raise RuntimeError(f"Expected 402, got {first.status_code}: {first.text}")

    payment_required = first.headers.get("payment-required")
    if not payment_required:
        raise RuntimeError("Missing PAYMENT-REQUIRED header")

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

    if second.status_code != 200:
        raise RuntimeError(f"Expected 200, got {second.status_code}: {second.text}")

    print("Status:", second.status_code)
    print("Body:", second.text)
    payment_response = second.headers.get("payment-response")
    if payment_response:
        print("Payment response:", b64decode_json(payment_response))


if __name__ == "__main__":
    main()
