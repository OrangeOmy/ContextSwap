from typing import Any, Dict

from fastapi import FastAPI, Request, Response

from contextswap.facilitator.base import FacilitatorClient
from contextswap.x402_tron import (
    CHAIN_ID,
    DEFAULT_PRICE_SUN,
    NETWORK_ID,
    b64decode_json,
    b64encode_json,
    make_requirements,
)


def create_tron_seller_app(
    facilitator_client: FacilitatorClient,
    seller_address: str,
    price_sun: int | None = None,
) -> FastAPI:
    app = FastAPI(title="x402 Seller (Tron)")
    price = price_sun or DEFAULT_PRICE_SUN

    @app.get("/weather")
    def get_weather(request: Request, response: Response) -> Dict[str, Any]:
        requirements = make_requirements(seller_address, price)
        requirements_b64 = b64encode_json(requirements)
        payment_header = request.headers.get("PAYMENT-SIGNATURE")

        if not payment_header:
            response.status_code = 402
            response.headers["PAYMENT-REQUIRED"] = requirements_b64
            return {"error": "Payment required"}

        try:
            payment_payload = b64decode_json(payment_header)
        except Exception:  # noqa: BLE001
            response.status_code = 402
            response.headers["PAYMENT-REQUIRED"] = requirements_b64
            return {"error": "Invalid payment payload"}

        try:
            verify_resp = facilitator_client.verify_payment(payment_payload, requirements)
            if not verify_resp.get("verified", True):
                raise ValueError("Verification failed")
            tx_hash = facilitator_client.settle_payment(payment_payload, requirements)
        except Exception as exc:  # noqa: BLE001
            response.status_code = 402
            response.headers["PAYMENT-REQUIRED"] = requirements_b64
            return {"error": str(exc)}

        payment_response = {
            "x402Version": 2,
            "scheme": "exact",
            "network": NETWORK_ID,
            "txHash": tx_hash,
        }
        response.headers["PAYMENT-RESPONSE"] = b64encode_json(payment_response)

        return {
            "report": {
                "weather": "sunny",
                "temperature": 70,
                "chainId": CHAIN_ID,
            }
        }

    return app
