from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from contextswap.facilitator.base import BaseFacilitator


class FacilitatorRequest(BaseModel):
    payment: Dict[str, Any]
    requirements: Dict[str, Any]


def create_facilitator_app(facilitator: BaseFacilitator) -> FastAPI:
    app = FastAPI(title="x402 Facilitator")

    @app.post("/v2/x402/verify")
    def verify(payload: FacilitatorRequest) -> Dict[str, Any]:
        try:
            result = facilitator.verify_payment(payload.payment, payload.requirements)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "verified": True, **result}

    @app.post("/v2/x402/settle")
    def settle(payload: FacilitatorRequest) -> Dict[str, Any]:
        try:
            tx_hash = facilitator.settle_payment(payload.payment, payload.requirements)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"ok": True, "txHash": tx_hash}

    return app
