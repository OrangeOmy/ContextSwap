from contextlib import asynccontextmanager

from fastapi import FastAPI

from contextswap.facilitator.client import DirectFacilitatorClient, HTTPFacilitatorClient
from contextswap.facilitator.conflux import ConfluxFacilitator
from contextswap.platform.api.routes.health import router as health_router
from contextswap.platform.api.routes.sellers import router as sellers_router
from contextswap.platform.api.routes.transactions import router as transactions_router
from contextswap.platform.config import Settings, load_settings
from contextswap.platform.db.engine import connect_sqlite, init_db
from contextswap.platform.services.tg_manager_client import TgManagerClient


def create_app(
    settings: Settings,
    *,
    facilitator_client=None,
    tg_manager_client: TgManagerClient | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal facilitator_client
        nonlocal tg_manager_client
        conn = connect_sqlite(settings.sqlite_path)
        init_db(conn)
        app.state.db = conn
        app.state.settings = settings

        if facilitator_client is None:
            if settings.facilitator_base_url:
                facilitator_client = HTTPFacilitatorClient(settings.facilitator_base_url)
            else:
                if not settings.rpc_url:
                    raise RuntimeError("Missing Conflux RPC URL")
                facilitator_client = DirectFacilitatorClient(ConfluxFacilitator(settings.rpc_url))

        if tg_manager_client is None and settings.tg_manager_base_url:
            tg_manager_client = TgManagerClient(settings.tg_manager_base_url, settings.tg_manager_auth_token or "")

        app.state.facilitator = facilitator_client
        app.state.tg_manager = tg_manager_client

        try:
            yield
        finally:
            if tg_manager_client is not None:
                tg_manager_client.close()
            conn.close()

    app = FastAPI(title="contextswap-platform", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(sellers_router)
    app.include_router(transactions_router)
    return app


def build_app() -> FastAPI:
    settings = load_settings()
    return create_app(settings)
