import httpx

from contextswap.platform.services.session_client import SessionClientError, SessionClientNotFound


class TgManagerClient:
    def __init__(self, base_url: str, auth_token: str, *, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token.strip()
        if not self.auth_token:
            raise ValueError("tg_manager auth_token is required")
        self._client = client or httpx.Client(timeout=10)

    def create_session(
        self,
        *,
        transaction_id: str,
        buyer_bot_username: str,
        seller_bot_username: str,
        initial_prompt: str,
        force_reinject: bool = False,
    ) -> dict:
        payload = {
            "transaction_id": transaction_id,
            "buyer_bot_username": buyer_bot_username,
            "seller_bot_username": seller_bot_username,
            "initial_prompt": initial_prompt,
            "force_reinject": force_reinject,
        }
        resp = self._client.post(
            f"{self.base_url}/v1/session/create",
            headers={"Authorization": f"Bearer {self.auth_token}"},
            json=payload,
        )
        if resp.status_code != 200:
            raise SessionClientError(resp.text)
        return resp.json()

    def get_session(self, *, transaction_id: str) -> dict:
        resp = self._client.get(
            f"{self.base_url}/v1/session/{transaction_id}",
            headers={"Authorization": f"Bearer {self.auth_token}"},
        )
        if resp.status_code != 200:
            if resp.status_code == 404:
                raise SessionClientNotFound(resp.text)
            raise SessionClientError(resp.text)
        return resp.json()

    def end_session(self, *, transaction_id: str, reason: str | None = None) -> dict:
        payload: dict[str, str] = {"transaction_id": transaction_id}
        if reason:
            payload["reason"] = reason
        resp = self._client.post(
            f"{self.base_url}/v1/session/end",
            headers={"Authorization": f"Bearer {self.auth_token}"},
            json=payload,
        )
        if resp.status_code != 200:
            if resp.status_code == 404:
                raise SessionClientNotFound(resp.text)
            raise SessionClientError(resp.text)
        return resp.json()

    def close(self) -> None:
        self._client.close()
