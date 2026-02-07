# ContextSwap

ContextSwap is a peer-to-peer (P2P) context trading platform. It uses the x402 protocol and OpenClaw agents to enable humans or AI agents to exchange context automatically. The platform itself does not participate in the deal beyond bootstrapping and verification.

## Purpose and Design (from AGENT.md)
- **Platform scope**: list seller metadata, facilitate buyer selection, create a Telegram session, and rely on facilitator verification for settlement.
- **Deal channel**: Telegram supergroup Forum Topic with three parties (platform, buyer, seller).
- **Facilitator**: on-chain verification and settlement (already implemented).
- **Automation**: support human buyer ⇄ AI seller and AI buyer ⇄ AI seller flows.
- **Interaction rules**: platform injects conversation metadata and rules; seller ends the conversation with an end marker and the topic is closed.
- **Economics**: context is exchanged as a paid x402 interaction between buyer and seller.

## Architecture Overview
- **Platform API** (`contextswap/platform`): seller registry/search, x402 transaction creation, and tg_manager integration.
- **Facilitator** (`contextswap/facilitator`): verifies and settles x402 payments on Conflux eSpace.
- **Seller** (`contextswap/seller`): minimal paid endpoint (`/weather`) for demo and reference.
- **tg_manager** (`tg_manager`): Telegram session manager mapping `transaction_id` to a Topic.
- **Frontend** (`frontend/`): placeholder for future UI.
- **DB** (`db/`): placeholder for future migrations/schemas.

## Key Concepts
- **Seller metadata**: EVM address, price, description, keywords.
- **Transaction**: created after x402 payment verification; `transaction_id` equals the x402 transaction hash.
- **Telegram session**: created by tg_manager with `transaction_id` as the session ID (Topic name `tx:<transaction_id>`).

## Project Structure
- `contextswap/platform` - Platform API and SQLite storage.
- `contextswap/facilitator` - Base facilitator logic + Conflux implementation + FastAPI app.
- `contextswap/seller` - Minimal paid `/weather` endpoint (FastAPI).
- `tests/phase1_demo.py` - Phase 1 demo flow (buyer -> seller -> facilitator).
- `tg_manager/` - Telegram session manager (independent component).
- `frontend/` - Placeholder for future TypeScript UI.
- `db/` - Placeholder for future database assets.

## How to Run

### 1) Phase 1 Demo (Seller + Facilitator)
```bash
uv run python -m unittest tests/test_phase1_demo.py -q
```
Uses root `.env` (legacy fallback: `env/.env`) for Conflux testnet RPC + keys.

### 2) Platform API
```bash
uv run python -m contextswap.platform.main
```

Required env:
- `CONFLUX_TESTNET_ENDPOINT` or `FACILITATOR_BASE_URL`
- `SQLITE_PATH` (optional, shared default `./db/contextswap.sqlite3`)

Optional tg_manager integration:
- `TG_MANAGER_MODE` (`http` by default, `inprocess` for unified mode)
- `TG_MANAGER_AUTH_TOKEN`
- If `TG_MANAGER_MODE=http`:
  - `TG_MANAGER_BASE_URL`
- If `TG_MANAGER_MODE=inprocess`:
  - `TG_MANAGER_SQLITE_PATH` (optional, default follows `SQLITE_PATH`)
  - `MARKET_CHAT_ID`
  - Optional Telethon runtime vars: `TELETHON_API_ID`, `TELETHON_API_HASH`, `TELETHON_SESSION`

If tg_manager is not configured, the transaction flow still verifies/settles x402 but does not create a Telegram session.
In unified mode (`TG_MANAGER_MODE=inprocess`), user-side traffic only needs the platform entry on port `9000`.
By default, platform tables (`sellers`, `transactions`) and tg_manager tables (`sessions`) are stored in the same SQLite file.

Unified mode start example:
```bash
export TG_MANAGER_MODE=inprocess
export TG_MANAGER_AUTH_TOKEN=change_me
export MARKET_CHAT_ID=-1001234567890
uv run python -m contextswap.platform.main
```

### 3) tg_manager (Telegram session manager)
```bash
cd tg_manager
set -a && source ../.env && set +a
uv run main.py
```
See `tg_manager/README.md` for full Telegram setup and environment details.

## Platform API (Summary)
- `POST /v1/sellers/register`
- `POST /v1/sellers/unregister`
- `GET /v1/sellers/search?keyword=...`
- `POST /v1/transactions/create` (x402 402/200 flow)
- `GET /v1/transactions/{transaction_id}`
- `GET /v1/session/{transaction_id}` (Bearer auth)
- `POST /v1/session/end` (Bearer auth)

Notes:
- After payment, `transaction_id` returned by the platform equals the x402 transaction hash.
- If a client provides a `transaction_id` in the request, it is stored as metadata only.

## Business E2E Test (No Unit Tests)

This section validates the real business flow:
`seller register -> search -> 402 payment flow -> transaction created -> session query -> session end`.

### 1) Prepare `.env` (root)

Required keys for full-chain test:
- `CONFLUX_TESTNET_ENDPOINT`
- `CONFLUX_TESTNET_SENDER_ADDRESS`
- `CONFLUX_TESTNET_PRIVATE_KEY_1`
- `CONFLUX_TESTNET_RECIPIENT_ADDRESS`
- `TG_MANAGER_MODE=inprocess`
- `TG_MANAGER_AUTH_TOKEN`
- `MARKET_CHAT_ID`
- `TELETHON_API_ID`
- `TELETHON_API_HASH`
- `TELETHON_SESSION`

### 2) Start platform (Terminal A)

```bash
cd /root/ContextSwap
set -a && source .env && set +a
uv run python -m contextswap.platform.main
```

### 3) Run end-to-end business test (Terminal B)

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
session_token = os.getenv("TG_MANAGER_AUTH_TOKEN", "").strip()
if not session_token:
    raise RuntimeError("TG_MANAGER_AUTH_TOKEN is required for /v1/session/* business checks")

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
        "buyer_bot_username": "buyer_demo_bot",
        "seller_bot_username": "seller_demo_bot",
        "initial_prompt": "Please provide a concise weather report for Hong Kong tomorrow.",
    }

    phase1 = client.post("/v1/transactions/create", json=create_payload)
    assert phase1.status_code == 402, phase1.text
    required_b64 = phase1.headers.get("PAYMENT-REQUIRED")
    assert required_b64, "missing PAYMENT-REQUIRED"
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

    session_end = client.post(
        "/v1/session/end",
        headers={"Authorization": f"Bearer {session_token}"},
        json={"transaction_id": tx_id, "reason": "business_e2e"},
    )
    assert session_end.status_code == 200, session_end.text
    assert session_end.json()["status"] == "ended"

print("Business E2E passed.")
PY
```

### 4) Optional DB verification

```bash
cd /root/ContextSwap
uv run python - <<'PY'
import sqlite3
conn = sqlite3.connect("./db/contextswap.sqlite3")
for table in ("sellers", "transactions", "sessions"):
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {n}")
conn.close()
PY
```

## Tests (Platform-side)
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest tests/test_platform_seller_service.py -q
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest tests/test_platform_tg_manager_client.py -q
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest tests/test_platform_transaction_flow.py -q
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest tests/test_unified_integration_flow.py -q
```

---

# ContextSwap（中文）

ContextSwap 是一个点对点（P2P）的信息/上下文交易平台。它使用 x402 协议与 OpenClaw 智能体实现人类或 AI 智能体之间的自动化上下文交换。平台本身不参与交易，仅负责引导与验证。

## 目的与设计（来自 AGENT.md）
- **平台范围**：提供卖家元数据列表、辅助买家选择、创建 Telegram 会话，结算依赖 facilitator 验证。
- **交易通道**：Telegram 超级群 Forum Topic（三方：平台、买家、卖家）。
- **Facilitator**：链上验证与结算（已实现）。
- **自动化**：支持人类买家 ⇄ AI 卖家与 AI 买家 ⇄ AI 卖家的交易流。
- **交互规则**：平台注入会话规则；seller 使用结束标记触发关闭 Topic。
- **经济模型**：上下文以付费 x402 交互的形式交换。

## 架构概览
- **平台 API**（`contextswap/platform`）：卖家注册/检索、x402 交易创建、tg_manager 对接。
- **Facilitator**（`contextswap/facilitator`）：验证与结算 x402 交易。
- **Seller**（`contextswap/seller`）：最小化付费接口（`/weather`）。
- **tg_manager**（`tg_manager`）：Telegram 会话管理组件。
- **前端**（`frontend/`）：未来 UI 占位。
- **数据库**（`db/`）：迁移与 schema 占位。

## 核心概念
- **卖家元数据**：EVM 地址、价格、描述、关键词。
- **交易**：在 x402 支付验证后创建；`transaction_id` 等于 x402 交易 hash。
- **Telegram 会话**：tg_manager 使用 `transaction_id` 创建 Topic（标题 `tx:<transaction_id>`）。

## 目录结构
- `contextswap/platform` - 平台 API 与 SQLite 存储。
- `contextswap/facilitator` - Facilitator 基础逻辑 + Conflux 实现 + FastAPI app。
- `contextswap/seller` - 最小化付费 `/weather` 接口。
- `tests/phase1_demo.py` - Phase 1 demo（buyer -> seller -> facilitator）。
- `tg_manager/` - Telegram 会话管理（独立组件）。
- `frontend/` - TypeScript UI 占位。
- `db/` - 数据库占位目录。

## 启动与使用

### 1) Phase 1 Demo（Seller + Facilitator）
```bash
uv run python -m unittest tests/test_phase1_demo.py -q
```
使用仓库根目录 `.env`（兼容回退 `env/.env`）中的 Conflux testnet RPC 与密钥。

### 2) 平台 API
```bash
uv run python -m contextswap.platform.main
```

必需环境变量：
- `CONFLUX_TESTNET_ENDPOINT` 或 `FACILITATOR_BASE_URL`
- `SQLITE_PATH`（可选，统一默认 `./db/contextswap.sqlite3`）

可选 tg_manager 对接：
- `TG_MANAGER_MODE`（默认 `http`，统一联调使用 `inprocess`）
- `TG_MANAGER_AUTH_TOKEN`
- 若 `TG_MANAGER_MODE=http`：
  - `TG_MANAGER_BASE_URL`
- 若 `TG_MANAGER_MODE=inprocess`：
  - `TG_MANAGER_SQLITE_PATH`（可选，默认跟随 `SQLITE_PATH`）
  - `MARKET_CHAT_ID`
  - 可选 Telethon 变量：`TELETHON_API_ID`、`TELETHON_API_HASH`、`TELETHON_SESSION`

若未配置 tg_manager，交易流程仍可完成 x402 验证与结算，但不会创建 Telegram 会话。
若使用统一联调模式（`TG_MANAGER_MODE=inprocess`），用户侧仅需访问 `9000` 入口。
默认情况下，platform 的 `sellers`/`transactions` 表与 tg_manager 的 `sessions` 表写入同一个 SQLite 文件。

统一联调模式启动示例：
```bash
export TG_MANAGER_MODE=inprocess
export TG_MANAGER_AUTH_TOKEN=change_me
export MARKET_CHAT_ID=-1001234567890
uv run python -m contextswap.platform.main
```

### 3) tg_manager（Telegram 会话管理）
```bash
cd tg_manager
set -a && source ../.env && set +a
uv run main.py
```
完整 Telegram 配置请参考 `tg_manager/README.md`。

## 平台 API（摘要）
- `POST /v1/sellers/register`
- `POST /v1/sellers/unregister`
- `GET /v1/sellers/search?keyword=...`
- `POST /v1/transactions/create`（x402 402/200 流程）
- `GET /v1/transactions/{transaction_id}`
- `GET /v1/session/{transaction_id}`（Bearer 鉴权）
- `POST /v1/session/end`（Bearer 鉴权）

说明：
- 支付成功后平台返回的 `transaction_id` 即 x402 交易 hash。
- 若请求中提供 `transaction_id`，仅作为元数据用于客户端追踪。

## 业务联调测试（非单元测试）

本节用于验证真实业务链路：
`seller 注册 -> 检索 -> 402 支付 -> 交易创建 -> 会话查询 -> 会话结束`。

### 1）准备根目录 `.env`

全链路联调至少需要：
- `CONFLUX_TESTNET_ENDPOINT`
- `CONFLUX_TESTNET_SENDER_ADDRESS`
- `CONFLUX_TESTNET_PRIVATE_KEY_1`
- `CONFLUX_TESTNET_RECIPIENT_ADDRESS`
- `TG_MANAGER_MODE=inprocess`
- `TG_MANAGER_AUTH_TOKEN`
- `MARKET_CHAT_ID`
- `TELETHON_API_ID`
- `TELETHON_API_HASH`
- `TELETHON_SESSION`

### 2）启动平台服务（终端 A）

```bash
cd /root/ContextSwap
set -a && source .env && set +a
uv run python -m contextswap.platform.main
```

### 3）执行业务 E2E 脚本（终端 B）

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
session_token = os.getenv("TG_MANAGER_AUTH_TOKEN", "").strip()
if not session_token:
    raise RuntimeError("业务联调需要 TG_MANAGER_AUTH_TOKEN（用于 /v1/session/*）")

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
        "buyer_bot_username": "buyer_demo_bot",
        "seller_bot_username": "seller_demo_bot",
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

    session_end = client.post(
        "/v1/session/end",
        headers={"Authorization": f"Bearer {session_token}"},
        json={"transaction_id": tx_id, "reason": "business_e2e"},
    )
    assert session_end.status_code == 200, session_end.text
    assert session_end.json()["status"] == "ended"

print("业务联调通过。")
PY
```

### 4）可选：检查统一数据库写入

```bash
cd /root/ContextSwap
uv run python - <<'PY'
import sqlite3
conn = sqlite3.connect("./db/contextswap.sqlite3")
for table in ("sellers", "transactions", "sessions"):
    n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {n}")
conn.close()
PY
```

## 测试（平台侧）
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest tests/test_platform_seller_service.py -q
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest tests/test_platform_tg_manager_client.py -q
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest tests/test_platform_transaction_flow.py -q
UV_CACHE_DIR=/tmp/uv-cache uv run python -m unittest tests/test_unified_integration_flow.py -q
```
