from fastapi import Request

from contextswap.facilitator.base import FacilitatorClient
from contextswap.platform.services.session_client import SessionManagerClient


def get_db(request: Request):
    return request.app.state.db


def get_facilitator(request: Request) -> FacilitatorClient | dict[str, FacilitatorClient]:
    facilitators = getattr(request.app.state, "facilitators", None)
    if facilitators:
        return facilitators
    return request.app.state.facilitator


def get_tg_manager(request: Request) -> SessionManagerClient | None:
    return request.app.state.tg_manager
