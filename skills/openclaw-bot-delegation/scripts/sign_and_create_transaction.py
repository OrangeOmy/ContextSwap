from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import httpx
from dotenv import load_dotenv
from web3 import Web3

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contextswap.x402 import b64decode_json, b64encode_json, build_payment

HARDCODED_CONFLUX_TESTNET_PRIVATE_KEY = "6c6a2f4c7d108c0a1d29eca5633e8700121455587a7142347dbda3d035f1c07c"
CONFLUX_TESTNET_EXPLORER_TX_BASE = "https://evmtestnet.confluxscan.org/tx/"
CONFLUX_MAINNET_EXPLORER_TX_BASE = "https://evm.confluxscan.org/tx/"


def _load_env(env_file: str | None) -> None:
    if env_file:
        load_dotenv(env_file, override=False)
        return

    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        load_dotenv(cwd_env, override=False)


def _read_env(name: str, *, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    if stripped == "":
        return default
    return stripped


def _require(value: str | None, label: str) -> str:
    if value is None:
        raise ValueError(f"Missing required value: {label}")
    return value


def _resolve_wait_seconds(raw: str | None, fallback: int = 120) -> int:
    if raw is None:
        return fallback
    value = int(raw)
    if value <= 0:
        raise ValueError("wait_seconds must be > 0")
    return value


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    buyer_address = _require(args.buyer_address or _read_env("CONFLUX_TESTNET_SENDER_ADDRESS"), "buyer_address")
    buyer_bot = _require(args.buyer_bot_username or _read_env("DEMO_BUYER_BOT_USERNAME"), "buyer_bot_username")
    seller_id = _require(args.seller_id or _read_env("DELEGATION_SELLER_ID"), "seller_id")
    seller_bot = _require(
        args.seller_bot_username or _read_env("DELEGATION_SELLER_BOT_USERNAME"),
        "seller_bot_username",
    )
    initial_prompt = _require(args.initial_prompt or _read_env("DELEGATION_INITIAL_PROMPT"), "initial_prompt")
    market_slug = (
        args.market_slug
        or _read_env("OPENCLAW_MARKET_SLUG")
        or _read_env("DELEGATION_MARKET_SLUG")
        or "will-donald-trump-win-the-2028-us-presidential-election"
    )
    question_dir = args.question_dir or _read_env("OPENCLAW_QUESTION_DIR") or "~/.openclaw/question"
    wait_seconds = _resolve_wait_seconds(
        str(args.wait_seconds) if args.wait_seconds is not None else _read_env("OPENCLAW_WAIT_SECONDS"),
        fallback=120,
    )

    return {
        "seller_id": seller_id,
        "buyer_address": buyer_address,
        "buyer_bot_username": buyer_bot,
        "seller_bot_username": seller_bot,
        "initial_prompt": initial_prompt,
        "market_slug": market_slug,
        "question_dir": question_dir,
        "wait_seconds": wait_seconds,
    }


def _create_payment_signature(
    *,
    requirements_b64: str,
    rpc_url: str,
    buyer_address: str,
    buyer_private_key: str,
) -> str:
    requirements = b64decode_json(requirements_b64)
    private_key = buyer_private_key if buyer_private_key.startswith("0x") else f"0x{buyer_private_key}"
    w3 = Web3(Web3.HTTPProvider(rpc_url))

    payment_payload = build_payment(
        requirements=requirements,
        w3=w3,
        buyer_address=buyer_address,
        buyer_private_key=private_key,
    )
    return b64encode_json(payment_payload)


def _build_explorer_url(*, tx_hash: str, rpc_url: str) -> str:
    override = _read_env("CONFLUX_EXPLORER_TX_BASE_URL")
    if override:
        return f"{override.rstrip('/')}/{tx_hash}"

    if "testnet" in rpc_url.casefold():
        return f"{CONFLUX_TESTNET_EXPLORER_TX_BASE}{tx_hash}"
    return f"{CONFLUX_MAINNET_EXPLORER_TX_BASE}{tx_hash}"


def _wait_for_tx_indexed(
    *,
    rpc_url: str,
    tx_hash: str,
    timeout_seconds: float,
    interval_seconds: float,
) -> bool:
    if timeout_seconds <= 0:
        raise ValueError("rpc_confirm_timeout must be > 0")
    if interval_seconds <= 0:
        raise ValueError("rpc_confirm_interval must be > 0")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    start = time.monotonic()
    while True:
        try:
            tx = w3.eth.get_transaction(tx_hash)
            if tx is not None:
                return True
        except Exception:  # noqa: BLE001
            pass

        if (time.monotonic() - start) >= timeout_seconds:
            return False
        time.sleep(interval_seconds)


def _default_mock_result_markdown(
    *,
    transaction_id: str,
    seller_bot_username: str,
    market_slug: str,
    initial_prompt: str,
) -> str:
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    seller = seller_bot_username.strip().lstrip("@").strip() or "unknown_seller"
    prompt = initial_prompt.strip() or "(empty)"
    return "\n".join(
        [
            "# Delegation Result",
            "",
            f"- transaction_id: `{transaction_id}`",
            f"- seller_bot_username: `{seller}`",
            f"- market_slug: `{market_slug}`",
            f"- as_of: `{as_of}`",
            "",
            "## Initial Prompt",
            prompt,
            "",
            "## Subtopic Output (Mock)",
            "This markdown is mock content generated after a real x402 payment",
            "and a real Telegram topic creation.",
            "",
            "## Forward-Ready Summary",
            "- payment_settled: true",
            "- topic_created: true",
            "- response_type: mock",
        ]
    )


def _read_mock_result_file(path: str) -> str:
    target = Path(path).expanduser()
    if not target.is_file():
        raise ValueError(f"mock result file does not exist: {target}")
    content = target.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"mock result file is empty: {target}")
    return content


def _write_result_files(
    *,
    result_dir: str,
    transaction_id: str,
    seller_bot_username: str,
    body: str,
    write_legacy_filename: bool,
) -> tuple[str, str | None]:
    tx = transaction_id.strip()
    if not tx:
        raise ValueError("Cannot write result markdown without transaction_id")

    output_dir = Path(result_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    primary = output_dir / f"{tx}.md"
    primary.write_text(body.rstrip() + "\n", encoding="utf-8")

    legacy: str | None = None
    if write_legacy_filename:
        seller = seller_bot_username.strip().lstrip("@").strip() or "unknown_seller"
        compat = output_dir / f"{tx}__{seller}__answer.md"
        compat.write_text(body.rstrip() + "\n", encoding="utf-8")
        legacy = str(compat)

    return str(primary), legacy


def run(args: argparse.Namespace) -> dict[str, Any]:
    base_url = _require(args.base_url or _read_env("PLATFORM_BASE_URL") or "http://127.0.0.1:9000", "base_url")
    payload = _build_payload(args)

    rpc_url = _require(args.rpc_url or _read_env("CONFLUX_TESTNET_ENDPOINT"), "CONFLUX_TESTNET_ENDPOINT")
    buyer_private_key = _require(
        args.buyer_private_key or _read_env("CONFLUX_TESTNET_PRIVATE_KEY_1") or HARDCODED_CONFLUX_TESTNET_PRIVATE_KEY,
        "CONFLUX_TESTNET_PRIVATE_KEY_1",
    )

    create_url = f"{base_url.rstrip('/')}/v1/transactions/create"
    with httpx.Client(timeout=args.timeout) as client:
        phase1 = client.post(create_url, json=payload)

        if phase1.status_code != 402:
            raise RuntimeError(f"Expected HTTP 402 on phase-1, got {phase1.status_code}: {phase1.text}")

        required_b64 = phase1.headers.get("PAYMENT-REQUIRED")
        if not required_b64:
            raise RuntimeError("Missing PAYMENT-REQUIRED header in phase-1 response")

        payment_signature = _create_payment_signature(
            requirements_b64=required_b64,
            rpc_url=rpc_url,
            buyer_address=str(payload["buyer_address"]),
            buyer_private_key=buyer_private_key,
        )

        phase2 = client.post(
            create_url,
            json=payload,
            headers={"PAYMENT-SIGNATURE": payment_signature},
        )

        if phase2.status_code != 200:
            raise RuntimeError(f"Expected HTTP 200 on phase-2, got {phase2.status_code}: {phase2.text}")

        body = phase2.json()

    transaction_id = str(body.get("transaction_id") or "").strip()
    tx_hash = str(body.get("tx_hash") or transaction_id).strip()
    if not transaction_id:
        raise RuntimeError("Transaction response missing transaction_id")
    if not tx_hash:
        raise RuntimeError("Transaction response missing tx_hash/transaction_id")

    session = body.get("session") or {}
    chat_id = session.get("chat_id")
    message_thread_id = session.get("message_thread_id")
    if chat_id is None or message_thread_id is None:
        raise RuntimeError("Transaction paid but session was not created (missing chat_id/message_thread_id)")

    rpc_confirmed = _wait_for_tx_indexed(
        rpc_url=rpc_url,
        tx_hash=tx_hash,
        timeout_seconds=float(args.rpc_confirm_timeout),
        interval_seconds=float(args.rpc_confirm_interval),
    )
    explorer_url = _build_explorer_url(tx_hash=tx_hash, rpc_url=rpc_url)
    if not rpc_confirmed:
        raise RuntimeError(
            f"Transaction is not discoverable via RPC within timeout: tx_hash={tx_hash}, explorer={explorer_url}"
        )

    mock_result_file = getattr(args, "mock_result_file", None)
    result_body = (
        args.mock_result_text
        or (_read_mock_result_file(mock_result_file) if mock_result_file else None)
        or _read_env("DELEGATION_MOCK_RESULT_TEXT")
        or _default_mock_result_markdown(
            transaction_id=transaction_id,
            seller_bot_username=str(payload["seller_bot_username"]),
            market_slug=str(payload["market_slug"]),
            initial_prompt=str(payload["initial_prompt"]),
        )
    )
    result_dir = args.result_dir or str(payload["question_dir"])
    result_md_path, legacy_result_md_path = _write_result_files(
        result_dir=result_dir,
        transaction_id=transaction_id,
        seller_bot_username=str(payload["seller_bot_username"]),
        body=result_body,
        write_legacy_filename=bool(args.write_legacy_filename),
    )

    return {
        "transaction_id": transaction_id,
        "tx_hash": tx_hash,
        "status": body.get("status"),
        "chat_id": chat_id,
        "message_thread_id": message_thread_id,
        "rpc_confirmed": rpc_confirmed,
        "explorer_url": explorer_url,
        "payment_response": phase2.headers.get("PAYMENT-RESPONSE"),
        "result_md_path": result_md_path,
        "legacy_result_md_path": legacy_result_md_path,
        "raw_response": body,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sign Conflux x402 payment, create transaction, verify on-chain visibility, and persist result markdown.",
    )
    parser.add_argument("--env-file", default=None, help="Optional env file path to load before reading variables")
    parser.add_argument("--base-url", default=None, help="Platform base URL (default from PLATFORM_BASE_URL)")
    parser.add_argument("--rpc-url", default=None, help="Conflux RPC URL (default from CONFLUX_TESTNET_ENDPOINT)")

    parser.add_argument("--seller-id", default=None, help="Seller ID to buy from")
    parser.add_argument("--seller-bot-username", default=None, help="Seller bot username")
    parser.add_argument("--buyer-address", default=None, help="Buyer wallet address")
    parser.add_argument("--buyer-bot-username", default=None, help="Buyer bot username")
    parser.add_argument("--buyer-private-key", default=None, help="Buyer private key (hex, optional override)")

    parser.add_argument("--initial-prompt", default=None, help="Task prompt to inject into Topic")
    parser.add_argument("--market-slug", default=None, help="Polymarket market slug")
    parser.add_argument("--question-dir", default=None, help="question_dir sent to platform/tg_manager")
    parser.add_argument("--result-dir", default=None, help="Output directory for primary <transaction_id>.md")
    parser.add_argument("--mock-result-text", default=None, help="Optional explicit markdown body for result file")
    parser.add_argument(
        "--mock-result-file",
        default=None,
        help="Optional markdown file path. Script reads this content and writes it to <transaction_id>.md",
    )
    parser.add_argument(
        "--write-legacy-filename",
        action="store_true",
        help="Also write legacy file: <transaction_id>__<seller_bot_username>__answer.md",
    )
    parser.add_argument(
        "--rpc-confirm-timeout",
        type=float,
        default=90.0,
        help="Seconds to wait for tx hash to be discoverable via RPC",
    )
    parser.add_argument(
        "--rpc-confirm-interval",
        type=float,
        default=3.0,
        help="Polling interval in seconds for tx discoverability",
    )
    parser.add_argument("--wait-seconds", type=int, default=None, help="Wait window before main bot collects markdown")
    parser.add_argument("--timeout", type=float, default=40.0, help="HTTP timeout in seconds")
    parser.add_argument("--output", default=None, help="Optional output JSON file path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _load_env(args.env_file)

    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
