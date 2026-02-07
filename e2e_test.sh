#!/bin/bash
cd /root/ContextSwap
set -a && source .env && set +a
uv run python - <<'PY'
import os
import time
import httpx
from contextswap.config import load_env
from contextswap.facilitator.conflux import ConfluxFacilitator
from contextswap.x402 import b64decode_json, b64encode_json, build_payment

base_url = os.getenv("PLATFORM_BASE_URL", "http://127.0.0.1:9000")
session_token = os.getenv("TG_MANAGER_AUTH_TOKEN", "").strip()
if not session_token:
    raise RuntimeError("业务联调需要 TG_MANAGER_AUTH_TOKEN（用于 /v1/session/*）")
poll_interval_seconds = int((os.getenv("E2E_POLL_INTERVAL_SECONDS", "30").strip() or "30"))
wait_timeout_seconds = int((os.getenv("E2E_WAIT_TIMEOUT_SECONDS", "300").strip() or "300"))
force_end_on_timeout = os.getenv("E2E_FORCE_END_ON_TIMEOUT", "1").strip().lower() in {"1", "true", "yes", "on"}
if poll_interval_seconds <= 0:
    raise RuntimeError("E2E_POLL_INTERVAL_SECONDS 必须大于 0")
if wait_timeout_seconds <= 0:
    raise RuntimeError("E2E_WAIT_TIMEOUT_SECONDS 必须大于 0")

env = load_env()
facilitator = ConfluxFacilitator(env.rpc_url)

seller_payload = {
    "evm_address": env.seller_address,
    "price_wei": 1000000000000000,
    "description": "business-e2e seller",
    "keywords": ["business", "e2e", "weather"],
}

with httpx.Client(base_url=base_url, timeout=30.0) as client:
    register = client.post("/v1/sellers/register", json=seller_payload)
    assert register.status_code == 200, register.text
    seller_id = register.json()["seller_id"]

    search = client.get("/v1/sellers/search", params={"keyword": "e2e"})
    assert search.status_code == 200, search.text
    assert len(search.json().get("items", [])) > 0

    create_payload = {
        "seller_id": seller_id,
        "buyer_address": env.buyer_address,
        "buyer_bot_username": "mybuyer6384_bot",
        "seller_bot_username": "Jack_Hua_bot",
        "initial_prompt": "Please provide a concise weather report for Hong Kong tomorrow.",
    }

    phase1 = client.post("/v1/transactions/create", json=create_payload)
    assert phase1.status_code == 402, phase1.text
    required_b64 = phase1.headers.get("PAYMENT-REQUIRED")
    assert required_b64, "缺少 PAYMENT-REQUIRED"
    requirements = b64decode_json(required_b64)

    payment = build_payment(
        requirements=requirements,
        w3=facilitator.web3,
        buyer_address=env.buyer_address,
        buyer_private_key=env.buyer_private_key,
    )

    phase2 = client.post(
        "/v1/transactions/create",
        json=create_payload,
        headers={"PAYMENT-SIGNATURE": b64encode_json(payment)},
    )
    assert phase2.status_code == 200, phase2.text
    body = phase2.json()
    tx_id = body["transaction_id"]
    assert body["status"] in {"session_created", "paid"}

    tx_query = client.get(f"/v1/transactions/{tx_id}")
    assert tx_query.status_code == 200, tx_query.text

    session_query = client.get(
        f"/v1/session/{tx_id}",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert session_query.status_code == 200, session_query.text
    session_info = session_query.json()
    if str(session_info.get("status", "")).lower() == "ended":
        print("会话已结束（首次查询即 ended），本次不再主动结束。")
    else:
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
            print(f"轮询会话状态: {status}")
            if status == "ended":
                ended_by_system = True
                print("会话已被系统自动关闭，脚本结束。")
                break

        if not ended_by_system and force_end_on_timeout:
            session_end = client.post(
                "/v1/session/end",
                headers={"Authorization": f"Bearer {session_token}"},
                json={"transaction_id": tx_id, "reason": "business_e2e_timeout"},
            )
            assert session_end.status_code == 200, session_end.text
            assert session_end.json()["status"] == "ended"
            print("轮询超时后已主动结束会话。")
        elif not ended_by_system:
            raise AssertionError("轮询超时且未自动关闭会话（E2E_FORCE_END_ON_TIMEOUT=0，脚本不主动关闭）。")

print("业务联调通过。")
PY
