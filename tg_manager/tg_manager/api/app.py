"""
FastAPI 应用装配。

约定：
- 使用 SQLite 作为最小持久化。
- 采用方案 B（超级群 + Topic）作为会话空间。
- 采用 Telethon（MTProto userbot）读写 Topic，并实现 bot 消息中继。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from telethon import TelegramClient
from telethon.sessions import StringSession

from tg_manager.core.config import Settings, load_settings
from tg_manager.db.engine import connect_sqlite, init_db
from tg_manager.api.routes.health import router as health_router
from tg_manager.api.routes.session import router as session_router
from tg_manager.services.telethon_relay import TelethonRelay
from tg_manager.services.telethon_service import TelethonService


def create_app(settings: Settings, *, telegram_service: object | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        conn = connect_sqlite(settings.sqlite_path)
        init_db(conn)
        app.state.db = conn
        app.state.settings = settings

        # Telethon userbot：若配置齐全则启用；否则保持为空（healthz 仍可启动）
        created_client = False
        relay: TelethonRelay | None = None
        if telegram_service is not None:
            app.state.telegram = telegram_service
            app.state.relay = None
        elif (
            settings.market_chat_id
            and settings.telethon_api_id is not None
            and settings.telethon_api_hash
            and settings.telethon_session
        ):
            client = TelegramClient(
                StringSession(settings.telethon_session),
                settings.telethon_api_id,
                settings.telethon_api_hash,
            )
            await client.connect()
            created_client = True
            authorized = await client.is_user_authorized()
            if not authorized:
                raise RuntimeError("Telethon session 未授权：请先生成 TELETHON_SESSION（StringSession）再启动服务")

            app.state.telegram = TelethonService(client=client)
            relay = TelethonRelay(client=client, conn=conn, market_chat_id=settings.market_chat_id)
            await relay.start()
            app.state.relay = relay
        else:
            app.state.telegram = None
            app.state.relay = None

        try:
            yield
        finally:
            if relay is not None:
                await relay.stop()
            if created_client and app.state.telegram is not None:
                # 仅在我们创建 client 的情况下断开连接；注入场景不干预外部生命周期
                svc = app.state.telegram
                client = getattr(svc, "client", None)
                if isinstance(client, TelegramClient):
                    await client.disconnect()
            conn.close()

    app = FastAPI(title="tg_manager", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(session_router)
    return app


def build_app() -> FastAPI:
    """从环境变量加载配置并构建应用。"""

    settings = load_settings()
    return create_app(settings)
