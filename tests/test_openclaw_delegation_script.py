from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT_PATH = Path("skills/openclaw-bot-delegation/scripts/sign_and_create_transaction.py").resolve()
SPEC = importlib.util.spec_from_file_location("openclaw_sign_create", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load module spec from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class _FakeResponse:
    def __init__(self, *, status_code: int, headers: dict[str, str] | None = None, text: str = "", body: dict | None = None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text
        self._body = body or {}

    def json(self) -> dict:
        return self._body


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.calls: list[tuple[str, dict, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, *, json: dict, headers: dict | None = None):
        self.calls.append((url, json, headers or {}))
        if not self._responses:
            raise RuntimeError("No fake response left")
        return self._responses.pop(0)


class OpenClawDelegationScriptTests(unittest.TestCase):
    def test_build_explorer_url_testnet(self) -> None:
        tx_hash = "0xabc123"
        url = MODULE._build_explorer_url(tx_hash=tx_hash, rpc_url="https://evmtestnet.confluxrpc.com")
        self.assertEqual(url, f"https://evmtestnet.confluxscan.org/tx/{tx_hash}")

    def test_write_result_files_primary_and_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary, legacy = MODULE._write_result_files(
                result_dir=tmp,
                transaction_id="0xtxid",
                seller_bot_username="polling3738_bot",
                body="# hello",
                write_legacy_filename=True,
            )
            self.assertTrue(Path(primary).exists())
            self.assertTrue(Path(primary).name == "0xtxid.md")
            self.assertIsNotNone(legacy)
            assert legacy is not None
            self.assertTrue(Path(legacy).exists())
            self.assertTrue(Path(legacy).name == "0xtxid__polling3738_bot__answer.md")

    def test_run_success_path(self) -> None:
        phase1 = _FakeResponse(
            status_code=402,
            headers={"PAYMENT-REQUIRED": "required_payload"},
            text="payment required",
        )
        phase2 = _FakeResponse(
            status_code=200,
            headers={"PAYMENT-RESPONSE": "settled_payload"},
            body={
                "transaction_id": "0xtransaction",
                "tx_hash": "0xtransaction",
                "status": "session_created",
                "session": {"chat_id": "-100111", "message_thread_id": 77},
            },
        )

        fake_client = _FakeClient([phase1, phase2])

        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(
                base_url="http://127.0.0.1:9000",
                rpc_url="https://evmtestnet.confluxrpc.com",
                seller_id="seller_id",
                seller_bot_username="polling3738_bot",
                buyer_address="0xE425936Ee4eAC61619db921D1f805B0F910E6F08",
                buyer_bot_username="buyer_bot",
                buyer_private_key="0xabc",
                initial_prompt="Please analyze this market",
                market_slug="demo-market",
                question_dir=tmp,
                result_dir=tmp,
                mock_result_text="# demo result",
                mock_result_file=None,
                write_legacy_filename=False,
                rpc_confirm_timeout=1.0,
                rpc_confirm_interval=0.1,
                wait_seconds=30,
                timeout=10.0,
            )

            with mock.patch.object(MODULE.httpx, "Client", return_value=fake_client):
                with mock.patch.object(MODULE, "_create_payment_signature", return_value="signed_payload"):
                    with mock.patch.object(MODULE, "_wait_for_tx_indexed", return_value=True):
                        result = MODULE.run(args)

            self.assertEqual(result["transaction_id"], "0xtransaction")
            self.assertEqual(result["tx_hash"], "0xtransaction")
            self.assertEqual(result["chat_id"], "-100111")
            self.assertEqual(result["message_thread_id"], 77)
            self.assertTrue(result["rpc_confirmed"])
            self.assertEqual(result["payment_response"], "settled_payload")
            self.assertTrue(Path(result["result_md_path"]).exists())
            self.assertIsNone(result["legacy_result_md_path"])

    def test_run_uses_mock_result_file(self) -> None:
        phase1 = _FakeResponse(
            status_code=402,
            headers={"PAYMENT-REQUIRED": "required_payload"},
            text="payment required",
        )
        phase2 = _FakeResponse(
            status_code=200,
            headers={"PAYMENT-RESPONSE": "settled_payload"},
            body={
                "transaction_id": "0xtransaction2",
                "tx_hash": "0xtransaction2",
                "status": "session_created",
                "session": {"chat_id": "-100111", "message_thread_id": 78},
            },
        )
        fake_client = _FakeClient([phase1, phase2])

        with tempfile.TemporaryDirectory() as tmp:
            result_dir = Path(tmp)
            prepared = result_dir / "prepared.md"
            prepared.write_text("# prewritten headhunter result\ncandidate=alex\n", encoding="utf-8")

            args = argparse.Namespace(
                base_url="http://127.0.0.1:9000",
                rpc_url="https://evmtestnet.confluxrpc.com",
                seller_id="seller_id",
                seller_bot_username="headhunter_agent_bot",
                buyer_address="0xE425936Ee4eAC61619db921D1f805B0F910E6F08",
                buyer_bot_username="hr_agent_bot",
                buyer_private_key="0xabc",
                initial_prompt="Please return top candidates for backend role",
                market_slug="demo-market",
                question_dir=tmp,
                result_dir=tmp,
                mock_result_text=None,
                mock_result_file=str(prepared),
                write_legacy_filename=False,
                rpc_confirm_timeout=1.0,
                rpc_confirm_interval=0.1,
                wait_seconds=30,
                timeout=10.0,
            )

            with mock.patch.object(MODULE.httpx, "Client", return_value=fake_client):
                with mock.patch.object(MODULE, "_create_payment_signature", return_value="signed_payload"):
                    with mock.patch.object(MODULE, "_wait_for_tx_indexed", return_value=True):
                        result = MODULE.run(args)

            body = Path(result["result_md_path"]).read_text(encoding="utf-8")
            self.assertIn("# prewritten headhunter result", body)
            self.assertIn("candidate=alex", body)


if __name__ == "__main__":
    unittest.main()
