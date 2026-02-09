---
name: openclaw-bot-delegation
description: 执行 OpenClaw 委托交易全链路操作。用于需要在同一任务中完成卖方注册与激活状态确认、按关键词检索可用卖方、买方发起交易并严格执行 x402 两段式支付（首次请求返回 HTTP 402 且包含 PAYMENT-REQUIRED，签名后重试返回 HTTP 200 且包含 PAYMENT-RESPONSE）、校验 transaction_id 与 session 关键字段、查询交易与会话状态、以及按标准命令重启并验证平台服务健康的场景。
---

# OpenClaw Bot Delegation

按以下顺序执行，不跳步。

- 默认服务地址：`http://127.0.0.1:9000`
- 健康检查接口：`GET /healthz`
- 交易接口：`POST /v1/transactions/create`

## 1. 注册卖方

在服务健康后注册卖方，并记录 `seller_id`。

```bash
cd /root/ContextSwap
set -a && source .env && set +a

BASE_URL="${PLATFORM_BASE_URL:-http://127.0.0.1:9000}"

curl -sS -X POST "$BASE_URL/v1/sellers/register" \
  -H 'Content-Type: application/json' \
  -d '{
    "evm_address": "'"${CONFLUX_TESTNET_RECIPIENT_ADDRESS}"'",
    "price_conflux_wei": 1000000000000000,
    "description": "delegation seller",
    "keywords": ["delegation", "analysis", "market"]
  }'
```

响应要求：

- 返回 `seller_id`
- `status` 为 `active`

## 2. 买方搜索与使用全流程

先检索卖方，再执行两段式支付创建交易，最后查询交易与会话。

```bash
cd /root/ContextSwap
set -a && source .env && set +a

uv run python - <<'PY'
import os
import httpx

from contextswap.config import load_env
from contextswap.facilitator.conflux import ConfluxFacilitator
from contextswap.x402 import b64decode_json, b64encode_json, build_payment

base_url = os.getenv("PLATFORM_BASE_URL", "http://127.0.0.1:9000")
search_keyword = os.getenv("DELEGATION_SEARCH_KEYWORD", "delegation")
session_token = os.getenv("TG_MANAGER_AUTH_TOKEN", "").strip()

env = load_env()
facilitator = ConfluxFacilitator(env.rpc_url)

with httpx.Client(base_url=base_url, timeout=30.0) as client:
    # 1) 搜索卖方
    search = client.get("/v1/sellers/search", params={"keyword": search_keyword})
    assert search.status_code == 200, search.text
    items = search.json().get("items", [])
    assert items, f"no seller found for keyword={search_keyword!r}"

    seller = items[0]
    seller_id = seller["seller_id"]

    # 2) phase-1: 不带 PAYMENT-SIGNATURE，必须返回 402
    create_payload = {
        "seller_id": seller_id,
        "buyer_address": env.buyer_address,
        "buyer_bot_username": os.getenv("DELEGATION_BUYER_BOT", "buyer_bot"),
        "seller_bot_username": os.getenv("DELEGATION_SELLER_BOT", "seller_bot"),
        "initial_prompt": os.getenv(
            "DELEGATION_INITIAL_PROMPT",
            "请给出结构化分析结论，并包含关键依据。",
        ),
        "payment_network": os.getenv("DELEGATION_PAYMENT_NETWORK", "conflux"),
    }

    phase1 = client.post("/v1/transactions/create", json=create_payload)
    assert phase1.status_code == 402, phase1.text
    required_b64 = phase1.headers.get("PAYMENT-REQUIRED")
    assert required_b64, "missing PAYMENT-REQUIRED"

    # 3) 生成 PAYMENT-SIGNATURE，重试 create，必须返回 200
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
    session = body.get("session") or {}
    assert session.get("chat_id") is not None, body
    assert session.get("message_thread_id") is not None, body

    # 4) 查询交易
    tx_query = client.get(f"/v1/transactions/{tx_id}")
    assert tx_query.status_code == 200, tx_query.text

    # 5) 查询会话（需要 TG_MANAGER_AUTH_TOKEN）
    if session_token:
        session_query = client.get(
            f"/v1/session/{tx_id}",
            headers={"Authorization": f"Bearer {session_token}"},
        )
        assert session_query.status_code == 200, session_query.text

    print({
        "seller_id": seller_id,
        "transaction_id": tx_id,
        "chat_id": session.get("chat_id"),
        "message_thread_id": session.get("message_thread_id"),
    })
PY
```

执行要求：

- `phase1` 必须是 `HTTP 402`，并包含 `PAYMENT-REQUIRED`
- `phase2` 必须是 `HTTP 200`
- 成功响应必须包含 `transaction_id`、`session.chat_id`、`session.message_thread_id`

## 3. 重新启动服务的方式

使用以下命令重启平台服务并完成健康检查。

```bash
cd /root/ContextSwap

pkill -f "contextswap.platform.main" || true
sleep 1

nohup ./start_server.sh > logs/backend_manual_restart.log 2>&1 &

sleep 2
curl -sS "${PLATFORM_BASE_URL:-http://127.0.0.1:9000}/healthz"
```

结果要求：

- 健康检查返回 `{"status":"ok"}`
- 若健康检查失败，继续查看日志文件：`logs/backend_manual_restart.log`
