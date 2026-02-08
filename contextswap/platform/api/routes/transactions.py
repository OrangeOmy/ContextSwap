from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from contextswap.platform.api.deps import get_db, get_facilitator, get_tg_manager
from contextswap.platform.config import DEFAULT_DEMO_MARKET_SLUG
from contextswap.platform.db import models
from eth_utils import to_checksum_address

from contextswap.platform.services import transaction_service
from contextswap.x402 import b64decode_json, b64encode_json

router = APIRouter(prefix="/v1/transactions", tags=["transactions"])


class TransactionCreateRequest(BaseModel):
    transaction_id: str | None = None
    payment_network: str | None = None
    seller_id: str | None = None
    seller_address: str | None = None
    buyer_address: str
    buyer_bot_username: str
    seller_bot_username: str
    initial_prompt: str
    market_slug: str | None = None
    question_dir: str | None = None
    wait_seconds: int | None = None


def _get_seller(conn, *, seller_id: str | None, seller_address: str | None) -> models.Seller:
    if seller_id:
        seller = models.get_seller_by_id(conn, seller_id=seller_id)
    elif seller_address:
        try:
            checksum = to_checksum_address(seller_address)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        seller = models.get_seller_by_address(conn, evm_address=checksum)
    else:
        raise HTTPException(status_code=400, detail="seller_id or seller_address is required")

    if seller is None or seller.status != "active":
        raise HTTPException(status_code=404, detail="seller not found")
    return seller


@router.post("/create")
def create_transaction(
    payload: TransactionCreateRequest,
    request: Request,
    response: Response,
    conn=Depends(get_db),
    facilitator=Depends(get_facilitator),
    tg_manager=Depends(get_tg_manager),
) -> dict:
    try:
        app = request.app
    except Exception:  # noqa: BLE001
        app = None
    app_state = getattr(app, "state", None)
    settings = getattr(app_state, "settings", None)
    default_market_slug = DEFAULT_DEMO_MARKET_SLUG
    default_question_dir = "~/.openclaw/question"
    default_wait_seconds = 120
    if settings is not None:
        default_market_slug = getattr(settings, "delegation_market_slug", default_market_slug)
        default_question_dir = getattr(settings, "delegation_question_dir", default_question_dir)
        default_wait_seconds = getattr(settings, "delegation_wait_seconds", default_wait_seconds)

    seller = _get_seller(conn, seller_id=payload.seller_id, seller_address=payload.seller_address)

    payment_network = (payload.payment_network or "").strip().lower()
    if not payment_network:
        if isinstance(facilitator, dict):
            if "conflux" in facilitator:
                payment_network = "conflux"
            elif "tron" in facilitator:
                payment_network = "tron"
        else:
            payment_network = "conflux"
    if payment_network not in {"conflux", "tron"}:
        raise HTTPException(status_code=400, detail="payment_network must be one of: conflux, tron")

    if isinstance(facilitator, dict):
        facilitator_client = facilitator.get(payment_network)
    else:
        facilitator_client = facilitator if payment_network == "conflux" else None
    if facilitator_client is None:
        raise HTTPException(status_code=400, detail=f"facilitator for {payment_network} is not configured")

    try:
        requirements = transaction_service.build_requirements(seller, network=payment_network)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    requirements_b64 = b64encode_json(requirements)
    price_amount = int(requirements["accepts"][0]["amountWei"])

    payment_header = request.headers.get("PAYMENT-SIGNATURE")
    if not payment_header:
        response.status_code = 402
        response.headers["PAYMENT-REQUIRED"] = requirements_b64
        return {"error": "payment required"}

    try:
        payment_payload = b64decode_json(payment_header)
    except Exception as exc:  # noqa: BLE001
        response.status_code = 402
        response.headers["PAYMENT-REQUIRED"] = requirements_b64
        return {"error": f"invalid payment payload: {exc}"}

    try:
        computed_tx_hash = transaction_service.compute_payment_id(payment_payload, network=payment_network)
    except Exception as exc:  # noqa: BLE001
        response.status_code = 402
        response.headers["PAYMENT-REQUIRED"] = requirements_b64
        return {"error": f"invalid payment payload: {exc}"}

    existing = models.get_transaction_by_id(conn, transaction_id=computed_tx_hash)
    if existing is not None:
        response.headers["PAYMENT-RESPONSE"] = transaction_service.build_payment_response(
            existing.tx_hash or computed_tx_hash,
            network=payment_network,
        )
        return transaction_service.transaction_to_dict(existing)

    try:
        tx_hash = transaction_service.verify_and_settle_payment(
            facilitator_client,
            payment_payload,
            requirements,
        )
    except Exception as exc:  # noqa: BLE001
        response.status_code = 402
        response.headers["PAYMENT-REQUIRED"] = requirements_b64
        return {"error": str(exc)}

    transaction_id = tx_hash
    resolved_wait_seconds = (
        payload.wait_seconds
        if isinstance(payload.wait_seconds, int) and payload.wait_seconds > 0
        else int(default_wait_seconds)
    )
    metadata = {
        "buyer_bot_username": payload.buyer_bot_username,
        "seller_bot_username": payload.seller_bot_username,
        "initial_prompt": payload.initial_prompt,
        "market_slug": (payload.market_slug or default_market_slug).strip(),
        "question_dir": (payload.question_dir or default_question_dir).strip(),
        "wait_seconds": resolved_wait_seconds,
    }
    if payload.transaction_id:
        metadata["client_transaction_id"] = payload.transaction_id

    transaction = transaction_service.create_transaction(
        conn,
        transaction_id=transaction_id,
        seller=seller,
        buyer_address=payload.buyer_address,
        payment_payload=payment_payload,
        requirements=requirements,
        tx_hash=tx_hash,
        price_wei=price_amount,
        metadata=metadata,
    )

    session_info = None
    if tg_manager is not None:
        try:
            session_info = tg_manager.create_session(
                transaction_id=tx_hash,
                buyer_bot_username=payload.buyer_bot_username,
                seller_bot_username=payload.seller_bot_username,
                initial_prompt=payload.initial_prompt,
                market_slug=metadata["market_slug"],
                question_dir=metadata["question_dir"],
                wait_seconds=int(metadata["wait_seconds"]),
            )
            session_chat_id = session_info.get("chat_id")
            session_thread_id = session_info.get("message_thread_id")
            if session_chat_id is None or session_thread_id is None:
                raise RuntimeError("tg_manager response missing chat_id or message_thread_id")
            transaction = transaction_service.attach_session(
                conn,
                transaction_id=transaction_id,
                chat_id=str(session_chat_id),
                message_thread_id=int(session_thread_id),
            )
        except Exception as exc:  # noqa: BLE001
            transaction = transaction_service.record_tg_manager_error(
                conn,
                transaction_id=transaction_id,
                error_reason=str(exc),
            )
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    response.headers["PAYMENT-RESPONSE"] = transaction_service.build_payment_response(tx_hash, network=payment_network)

    result = transaction_service.transaction_to_dict(transaction)
    if session_info is not None:
        result["session"] = {
            "chat_id": session_info.get("chat_id"),
            "message_thread_id": session_info.get("message_thread_id"),
            "status": session_info.get("status"),
        }
    return result


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str, conn=Depends(get_db)) -> dict:
    got = models.get_transaction_by_id(conn, transaction_id=transaction_id)
    if got is None:
        raise HTTPException(status_code=404, detail="transaction not found")
    return transaction_service.transaction_to_dict(got)
