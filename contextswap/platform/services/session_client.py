from __future__ import annotations

from typing import Protocol


class SessionClientError(RuntimeError):
    pass


class SessionClientNotFound(SessionClientError):
    pass


class SessionManagerClient(Protocol):
    def create_session(
        self,
        *,
        transaction_id: str,
        buyer_bot_username: str,
        seller_bot_username: str,
        initial_prompt: str,
        force_reinject: bool = False,
    ) -> dict: ...

    def get_session(self, *, transaction_id: str) -> dict: ...

    def end_session(self, *, transaction_id: str, reason: str | None = None) -> dict: ...

    def close(self) -> None: ...
