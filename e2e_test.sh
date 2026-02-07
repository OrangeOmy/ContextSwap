#!/bin/bash
set -euo pipefail

cd /root/ContextSwap
set -a && source .env && set +a
uv run python - <<'PY'
import os
import time

import httpx

from contextswap.config import load_env, load_tron_env
from contextswap.facilitator.conflux import ConfluxFacilitator
from contextswap.x402 import b64decode_json, b64encode_json, build_payment as build_conflux_payment
from contextswap.x402_tron import build_payment as build_tron_payment


def _parse_networks(raw: str) -> list[str]:
    got = []
    for item in raw.split(","):
        token = item.strip().lower()
        if not token:
            continue
        if token not in {"conflux", "tron"}:
            raise RuntimeError(f"E2E_NETWORKS 包含不支持的网络: {token!r} (允许: conflux, tron)")
        if token not in got:
            got.append(token)
    if not got:
        raise RuntimeError("E2E_NETWORKS 不能为空")
    return got


def _wait_or_end_session(
    *,
    client: httpx.Client,
    tx_id: str,
    network: str,
    session_token: str,
    poll_interval_seconds: int,
    wait_timeout_seconds: int,
    force_end_on_timeout: bool,
) -> None:
    session_query = client.get(
        f"/v1/session/{tx_id}",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert session_query.status_code == 200, session_query.text
    session_info = session_query.json()

    if str(session_info.get("status", "")).lower() == "ended":
        print(f"[{network}] 会话已结束（首次查询即 ended），本次不再主动结束。")
        return

    deadline = time.monotonic() + wait_timeout_seconds
    ended_by_system = False
    while time.monotonic() < deadline:
        sleep_for = min(poll_interval_seconds, max(0, int(deadline - time.monotonic())))
        if sleep_for > 0:
            time.sleep(sleep_for)
        polled = client.get(
            f"/v1/session/{tx_id}",
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert polled.status_code == 200, polled.text
        polled_info = polled.json()
        status = str(polled_info.get("status", "")).lower()
        print(f"[{network}] 轮询会话状态: {status}")
        if status == "ended":
            ended_by_system = True
            print(f"[{network}] 会话已被系统自动关闭。")
            break

    if not ended_by_system and force_end_on_timeout:
        session_end = client.post(
            "/v1/session/end",
            headers={"Authorization": f"Bearer {session_token}"},
            json={"transaction_id": tx_id, "reason": f"business_e2e_timeout_{network}"},
        )
        assert session_end.status_code == 200, session_end.text
        assert session_end.json()["status"] == "ended"
        print(f"[{network}] 轮询超时后已主动结束会话。")
    elif not ended_by_system:
        raise AssertionError(
            f"[{network}] 轮询超时且未自动关闭会话（E2E_FORCE_END_ON_TIMEOUT=0，脚本不主动关闭）。"
        )


base_url = os.getenv("PLATFORM_BASE_URL", "http://127.0.0.1:9000")
session_token = os.getenv("TG_MANAGER_AUTH_TOKEN", "").strip()
if not session_token:
    raise RuntimeError("业务联调需要 TG_MANAGER_AUTH_TOKEN（用于 /v1/session/*）")

networks = _parse_networks(os.getenv("E2E_NETWORKS", "conflux,tron"))
poll_interval_seconds = int((os.getenv("E2E_POLL_INTERVAL_SECONDS", "30").strip() or "30"))
wait_timeout_seconds = int((os.getenv("E2E_WAIT_TIMEOUT_SECONDS", "300").strip() or "300"))
force_end_on_timeout = os.getenv("E2E_FORCE_END_ON_TIMEOUT", "1").strip().lower() in {"1", "true", "yes", "on"}

if poll_interval_seconds <= 0:
    raise RuntimeError("E2E_POLL_INTERVAL_SECONDS 必须大于 0")
if wait_timeout_seconds <= 0:
    raise RuntimeError("E2E_WAIT_TIMEOUT_SECONDS 必须大于 0")

print(f"开始业务联调，目标网络: {', '.join(networks)}")

with httpx.Client(base_url=base_url, timeout=30.0) as client:
    for network in networks:
        if network == "conflux":
            env = load_env()
            facilitator = ConfluxFacilitator(env.rpc_url)
            price_conflux_wei = int((os.getenv("E2E_CONFLUX_PRICE_WEI", "1000000000000000").strip() or "1000000000000000"))
            register_payload = {
                "evm_address": env.seller_address,
                "price_conflux_wei": price_conflux_wei,
                "description": "business-e2e seller for conflux",
                "keywords": ["business", "e2e", "weather", "conflux"],
            }
            buyer_address = env.buyer_address
            buyer_private_key = env.buyer_private_key
        elif network == "tron":
            env = load_tron_env()
            price_tron_sun = int((os.getenv("E2E_TRON_PRICE_SUN", "1000000").strip() or "1000000"))
            register_payload = {
                "evm_address": env.seller_address,
                "price_tron_sun": price_tron_sun,
                "description": "business-e2e seller for tron",
                "keywords": ["business", "e2e", "weather", "tron"],
            }
            buyer_address = env.buyer_address
            buyer_private_key = env.buyer_private_key
        else:
            raise RuntimeError(f"unsupported network: {network}")

        register = client.post("/v1/sellers/register", json=register_payload)
        assert register.status_code == 200, f"[{network}] {register.text}"
        seller_id = register.json()["seller_id"]

        search = client.get("/v1/sellers/search", params={"keyword": network})
        assert search.status_code == 200, f"[{network}] {search.text}"
        assert len(search.json().get("items", [])) > 0, f"[{network}] search result empty"

        create_payload = {
            "seller_id": seller_id,
            "buyer_address": buyer_address,
            "buyer_bot_username": os.getenv("E2E_BUYER_BOT_USERNAME", "mybuyer6384_bot"),
            "seller_bot_username": os.getenv("E2E_SELLER_BOT_USERNAME", "Jack_Hua_bot"),
            "initial_prompt": "Please provide a concise weather report for Hong Kong tomorrow.",
            "payment_network": network,
        }

        phase1 = client.post("/v1/transactions/create", json=create_payload)
        assert phase1.status_code == 402, f"[{network}] {phase1.text}"
        required_b64 = phase1.headers.get("PAYMENT-REQUIRED")
        assert required_b64, f"[{network}] 缺少 PAYMENT-REQUIRED"
        requirements = b64decode_json(required_b64)

        if network == "conflux":
            payment = build_conflux_payment(
                requirements=requirements,
                w3=facilitator.web3,
                buyer_address=buyer_address,
                buyer_private_key=buyer_private_key,
            )
        else:
            payment = build_tron_payment(
                requirements=requirements,
                rpc_url=env.rpc_url,
                buyer_address=buyer_address,
                buyer_private_key=buyer_private_key,
                api_key=env.api_key,
            )

        phase2 = client.post(
            "/v1/transactions/create",
            json=create_payload,
            headers={"PAYMENT-SIGNATURE": b64encode_json(payment)},
        )
        assert phase2.status_code == 200, f"[{network}] {phase2.text}"
        body = phase2.json()
        tx_id = body["transaction_id"]
        assert body["status"] in {"session_created", "paid"}, f"[{network}] unexpected status: {body}"
        assert body.get("payment_network") == network, f"[{network}] payment_network mismatch: {body}"

        tx_query = client.get(f"/v1/transactions/{tx_id}")
        assert tx_query.status_code == 200, f"[{network}] {tx_query.text}"
        _wait_or_end_session(
            client=client,
            tx_id=tx_id,
            network=network,
            session_token=session_token,
            poll_interval_seconds=poll_interval_seconds,
            wait_timeout_seconds=wait_timeout_seconds,
            force_end_on_timeout=force_end_on_timeout,
        )
        print(f"[{network}] x402 转账与业务会话流程通过，transaction_id={tx_id}")

print("业务联调通过（Conflux/Tron）。")
PY
