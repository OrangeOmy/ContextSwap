from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from contextswap.platform.api.deps import get_tg_manager
from contextswap.platform.services.session_client import SessionClientError, SessionClientNotFound

router = APIRouter(prefix="/v1/session", tags=["session"])


class SessionEndRequest(BaseModel):
    transaction_id: str
    reason: str | None = None


def _parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    raw = authorization.strip()
    prefix = "Bearer "
    if not raw.startswith(prefix):
        return None
    token = raw[len(prefix) :].strip()
    return token or None


def require_session_auth(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    expected = (request.app.state.settings.tg_manager_auth_token or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="session API is disabled (missing TG_MANAGER_AUTH_TOKEN)")
    token = _parse_bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="missing or invalid Authorization header")
    if token != expected:
        raise HTTPException(status_code=403, detail="invalid auth token")


def _get_session_client_or_503(tg_manager):
    if tg_manager is None:
        raise HTTPException(status_code=503, detail="tg_manager is not configured")
    return tg_manager


@router.get("/{transaction_id}", dependencies=[Depends(require_session_auth)])
def get_session(transaction_id: str, tg_manager=Depends(get_tg_manager)) -> dict:
    session_client = _get_session_client_or_503(tg_manager)
    try:
        return session_client.get_session(transaction_id=transaction_id)
    except SessionClientNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SessionClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/end", dependencies=[Depends(require_session_auth)])
def end_session(payload: SessionEndRequest, tg_manager=Depends(get_tg_manager)) -> dict:
    session_client = _get_session_client_or_503(tg_manager)
    try:
        return session_client.end_session(
            transaction_id=payload.transaction_id,
            reason=payload.reason,
        )
    except SessionClientNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SessionClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
