from typing import Any, Dict

import requests

from contextswap.facilitator.base import BaseFacilitator


class DirectFacilitatorClient:
    def __init__(self, facilitator: BaseFacilitator) -> None:
        self._facilitator = facilitator

    def verify_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        return self._facilitator.verify_payment(payment, requirements)

    def settle_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> str:
        return self._facilitator.settle_payment(payment, requirements)


class HTTPFacilitatorClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def verify_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}/v2/x402/verify",
            json={"payment": payment, "requirements": requirements},
            timeout=10,
        )
        if resp.status_code != 200:
            raise RuntimeError(resp.text)
        return resp.json()

    def settle_payment(self, payment: Dict[str, Any], requirements: Dict[str, Any]) -> str:
        resp = requests.post(
            f"{self.base_url}/v2/x402/settle",
            json={"payment": payment, "requirements": requirements},
            timeout=10,
        )
        if resp.status_code != 200:
            raise RuntimeError(resp.text)
        data = resp.json()
        return data.get("txHash", "")
