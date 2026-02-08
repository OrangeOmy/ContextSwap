"""
基于 platform db 的 FastAPI 接口测试。
使用内存 SQLite 与 mock facilitator / tg_manager，不依赖外部服务。
"""
import unittest
from fastapi.testclient import TestClient

from contextswap.platform.api.app import create_app
from contextswap.platform.config import Settings


class _MockTgManager:
    def close(self) -> None:
        pass


def _test_settings() -> Settings:
    return Settings(
        sqlite_path=":memory:",
        rpc_url="http://localhost:9999",
        tron_rpc_url=None,
        tron_api_key=None,
        facilitator_base_url=None,
        tg_manager_mode="http",
        tg_manager_base_url="",
        tg_manager_auth_token="",
        tg_manager_sqlite_path=":memory:",
        tg_manager_market_chat_id=None,
    )


def _make_app():
    """使用内存 DB 与 mock 依赖的 FastAPI 应用。"""
    settings = _test_settings()
    return create_app(
        settings,
        facilitator_client=object(),
        tg_manager_client=_MockTgManager(),
    )


class PlatformApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = _make_app()
        self._test_client = TestClient(self.app)
        self._test_client.__enter__()
        self.client = self._test_client

    def tearDown(self) -> None:
        self._test_client.__exit__(None, None, None)

    # ---------- health ----------

    def test_healthz(self) -> None:
        r = self.client.get("/healthz")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok"})

    # ---------- dashboard (db 聚合) ----------

    def test_dashboard_stats_empty(self) -> None:
        r = self.client.get("/v1/dashboard/stats")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("sellers", data)
        self.assertEqual(data["sellers"]["total"], 0)
        self.assertEqual(data["sellers"]["active"], 0)
        self.assertIn("transactions", data)
        self.assertEqual(data["transactions"]["total"], 0)
        self.assertIn("keywords_top", data)

    # ---------- sellers (db 读写) ----------

    def test_sellers_register_and_get(self) -> None:
        payload = {
            "evm_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "price_wei": 1000,
            "price_tron_sun": 2000,
            "description": "test seller",
            "keywords": ["alpha", "beta"],
        }
        r = self.client.post("/v1/sellers/register", json=payload)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("id", body)
        self.assertEqual(body["status"], "active")
        self.assertEqual(body["evm_address"], payload["evm_address"])
        seller_id = body["seller_id"]
        self.assertTrue(seller_id)

        r2 = self.client.get(f"/v1/sellers/{seller_id}")
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertEqual(data["seller_id"], seller_id)
        self.assertEqual(data["description"], payload["description"])
        self.assertIn("price_wei", data)
        self.assertIn("price_conflux_wei", data)
        self.assertIn("price_tron_sun", data)
        self.assertIn("keywords", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

    def test_sellers_list_and_by_address(self) -> None:
        self.client.post(
            "/v1/sellers/register",
            json={
                "evm_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                "price_wei": 1000,
                "description": "list me",
                "keywords": "x",
            },
        )
        r = self.client.get("/v1/sellers", params={"limit": 10})
        self.assertEqual(r.status_code, 200)
        items = r.json()["items"]
        self.assertGreaterEqual(len(items), 1)
        self.assertIn("id", items[0])
        self.assertIn("seller_id", items[0])
        addr = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        r2 = self.client.get(f"/v1/sellers/by-address/{addr}")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["evm_address"], addr)

    def test_sellers_patch(self) -> None:
        reg = self.client.post(
            "/v1/sellers/register",
            json={
                "evm_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                "price_wei": 1000,
                "description": "original",
                "keywords": "a",
            },
        )
        seller_id = reg.json()["seller_id"]
        r = self.client.patch(
            f"/v1/sellers/{seller_id}",
            json={"description": "updated", "status": "active"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["description"], "updated")
        self.assertEqual(r.json()["status"], "active")

    def test_sellers_get_not_found(self) -> None:
        r = self.client.get("/v1/sellers/nonexistent_seller_id_123")
        self.assertEqual(r.status_code, 404)
        self.assertIn("not found", r.json().get("detail", "").lower())

    def test_sellers_search(self) -> None:
        payload = {
            "evm_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "price_wei": 1000,
            "description": "searchable text",
            "keywords": "foo,bar",
        }
        self.client.post("/v1/sellers/register", json=payload)

        r = self.client.get("/v1/sellers/search", params={"keyword": "foo"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("items", r.json())
        self.assertEqual(len(r.json()["items"]), 1)
        self.assertIn("foo", (r.json()["items"][0]["keywords"] or ""))

        r2 = self.client.get("/v1/sellers/search", params={"keyword": "nonexistent"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["items"], [])

    def test_sellers_unregister(self) -> None:
        payload = {
            "evm_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "price_wei": 1000,
            "description": "to unregister",
            "keywords": "baz",
        }
        reg = self.client.post("/v1/sellers/register", json=payload)
        self.assertEqual(reg.status_code, 200)
        seller_id = reg.json()["seller_id"]

        r = self.client.post("/v1/sellers/unregister", json={"seller_id": seller_id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "inactive")

        r2 = self.client.get(f"/v1/sellers/{seller_id}")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["status"], "inactive")

    # ---------- transactions (db 读) ----------

    def test_transactions_list_empty(self) -> None:
        r = self.client.get("/v1/transactions")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["items"], [])

    def test_transactions_list_limit_offset(self) -> None:
        r = self.client.get("/v1/transactions", params={"limit": 10, "offset": 0})
        self.assertEqual(r.status_code, 200)
        self.assertIn("items", r.json())

    def test_transactions_get_not_found(self) -> None:
        r = self.client.get("/v1/transactions/tx_nonexistent_id_123")
        self.assertEqual(r.status_code, 404)
        self.assertIn("not found", r.json().get("detail", "").lower())

    def test_transactions_list_returns_full_fields(self) -> None:
        r = self.client.get("/v1/transactions", params={"limit": 5})
        self.assertEqual(r.status_code, 200)
        self.assertIn("items", r.json())
        for item in r.json()["items"]:
            self.assertIn("id", item)
            self.assertIn("transaction_id", item)
            self.assertIn("payment_payload_json", item)
            self.assertIn("requirements_json", item)
            self.assertIn("metadata_json", item)

    # ---------- dashboard 与 db 一致性 ----------

    def test_dashboard_stats_after_seller_register(self) -> None:
        self.client.post(
            "/v1/sellers/register",
            json={
                "evm_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                "price_wei": 1000,
                "description": "d",
                "keywords": "k",
            },
        )
        r = self.client.get("/v1/dashboard/stats")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["sellers"]["total"], 1)
        self.assertEqual(r.json()["sellers"]["active"], 1)


if __name__ == "__main__":
    unittest.main()
