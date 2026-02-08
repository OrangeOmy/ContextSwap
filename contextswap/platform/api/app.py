from contextlib import asynccontextmanager

from fastapi import FastAPI
from telethon import TelegramClient
from telethon.sessions import StringSession

from contextswap.facilitator.client import DirectFacilitatorClient, HTTPFacilitatorClient
from contextswap.facilitator.conflux import ConfluxFacilitator
from contextswap.facilitator.tron import TronFacilitator
from contextswap.platform.api.routes.health import router as health_router
from contextswap.platform.api.routes.session import router as session_router
from contextswap.platform.api.routes.sellers import router as sellers_router
from contextswap.platform.api.routes.transactions import router as transactions_router
from contextswap.platform.config import Settings, load_settings
from contextswap.platform.db.engine import connect_sqlite, init_db
from contextswap.platform.services.inprocess_tg_manager_client import InProcessTgManagerClient
from contextswap.platform.services.session_client import SessionManagerClient
from contextswap.platform.services.tg_manager_client import TgManagerClient
from tg_manager.services.mock_bot_relay import MockBotRelay, parse_mock_bots
from tg_manager.services.telethon_relay import TelethonRelay
from tg_manager.services.telethon_service import TelethonService


def create_app(
    settings: Settings,
    *,
    facilitator_client=None,
    tg_manager_client: SessionManagerClient | None = None,
    tg_manager_telegram_service: object | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal facilitator_client
        nonlocal tg_manager_client
        nonlocal tg_manager_telegram_service
        conn = connect_sqlite(settings.sqlite_path)
        init_db(conn)
        app.state.db = conn
        app.state.settings = settings

        relay: TelethonRelay | None = None
        mock_relay: MockBotRelay | None = None
        telethon_client: TelegramClient | None = None

        facilitators: dict[str, object] | None = None
        if isinstance(facilitator_client, dict):
            facilitators = facilitator_client
            facilitator_client = facilitators.get("conflux") or next(iter(facilitators.values()))
        elif facilitator_client is None:
            facilitators = {}
            if settings.facilitator_base_url:
                facilitators["conflux"] = HTTPFacilitatorClient(settings.facilitator_base_url)
            elif settings.rpc_url:
                facilitators["conflux"] = DirectFacilitatorClient(ConfluxFacilitator(settings.rpc_url))

            if settings.tron_rpc_url:
                facilitators["tron"] = DirectFacilitatorClient(
                    TronFacilitator(settings.tron_rpc_url, settings.tron_api_key)
                )

            if not facilitators:
                raise RuntimeError("Missing Conflux or Tron RPC URL")

            facilitator_client = facilitators.get("conflux") or next(iter(facilitators.values()))

        if tg_manager_client is None:
            if settings.tg_manager_mode == "http":
                if settings.tg_manager_base_url:
                    tg_manager_client = TgManagerClient(settings.tg_manager_base_url, settings.tg_manager_auth_token or "")
            elif settings.tg_manager_mode == "inprocess":
                telegram_service = tg_manager_telegram_service
                if telegram_service is None:
                    telethon_api_id = settings.telethon_api_id
                    telethon_api_hash = settings.telethon_api_hash
                    telethon_session = settings.telethon_session
                    if telethon_api_id is not None and telethon_api_hash and telethon_session:
                        telethon_client = TelegramClient(
                            StringSession(telethon_session),
                            telethon_api_id,
                            telethon_api_hash,
                        )
                        await telethon_client.connect()
                        if not await telethon_client.is_user_authorized():
                            raise RuntimeError("Telethon session is not authorized")
                        telegram_service = TelethonService(client=telethon_client)

                tg_manager_client = InProcessTgManagerClient(
                    sqlite_path=settings.tg_manager_sqlite_path,
                    auth_token=settings.tg_manager_auth_token or "",
                    market_chat_id=settings.tg_manager_market_chat_id or "",
                    telegram_service=telegram_service,
                )
                if telethon_client is not None and settings.tg_manager_market_chat_id:
                    relay = TelethonRelay(
                        client=telethon_client,
                        conn=tg_manager_client.conn,  # type: ignore[attr-defined]
                        market_chat_id=settings.tg_manager_market_chat_id,
                    )
                    await relay.start()
                    mock_bots = parse_mock_bots(
                        enabled=settings.mock_bots_enabled,
                        raw_json=settings.mock_bots_json,
                        market_slug=settings.delegation_market_slug,
                    )
                    mock_relay = MockBotRelay(
                        client=telethon_client,
                        conn=tg_manager_client.conn,  # type: ignore[attr-defined]
                        market_chat_id=settings.tg_manager_market_chat_id,
                        relay=relay,
                        responses=mock_bots,
                        seller_auto_end=settings.mock_seller_auto_end,
                    )
                    await mock_relay.start()

        app.state.facilitator = facilitator_client
        app.state.facilitators = facilitators or {"conflux": facilitator_client}
        app.state.tg_manager = tg_manager_client

        try:
            yield
        finally:
            if mock_relay is not None:
                await mock_relay.stop()
            if relay is not None:
                await relay.stop()
            if telethon_client is not None:
                await telethon_client.disconnect()
            if tg_manager_client is not None:
                tg_manager_client.close()
            conn.close()

    app = FastAPI(title="contextswap-platform", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(sellers_router)
    app.include_router(transactions_router)
    app.include_router(session_router)
    return app


def build_app() -> FastAPI:
    settings = load_settings()
    return create_app(settings)
