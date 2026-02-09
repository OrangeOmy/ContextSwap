# ContextSwap Backend (`contextswap/`)

Technical backend documentation for platform API, payment flow, and runtime configuration.

本文件是 `contextswap/` 后端技术文档，覆盖平台 API、支付流程与运行配置。

## 1. Modules / 模块说明

- `contextswap/platform`: marketplace API (seller registry, transaction lifecycle, session bridge).
- `contextswap/facilitator`: on-chain payment verify/settle adapters (Conflux / Tron).
- `contextswap/seller`: minimal paid endpoint examples.
- `contextswap/x402.py`, `contextswap/x402_tron.py`: x402 payload encode/decode and helpers.

- `contextswap/platform`：市场平台 API（卖家、交易、会话桥接）。
- `contextswap/facilitator`：链上支付验证与结算（Conflux / Tron）。
- `contextswap/seller`：最小付费接口示例。
- `contextswap/x402.py`、`contextswap/x402_tron.py`：x402 编解码与辅助函数。

## 2. Run Backend / 启动后端

From repo root:

```bash
uv run python -m contextswap.platform.main
```

Health check:

```bash
curl -sS http://127.0.0.1:9000/healthz
```

Expected / 期望: `{"status":"ok"}`

## 3. Core Env Vars / 核心环境变量

At least one payment backend must exist:

- `CONFLUX_TESTNET_ENDPOINT`, or
- `TRON_NILE_ENDPOINT` (or `TRON_TESTNET_ENDPOINT` / `TRON_SHASTA_ENDPOINT`), or
- `FACILITATOR_BASE_URL`.

至少要配置一个支付后端：

- `CONFLUX_TESTNET_ENDPOINT`，或
- `TRON_NILE_ENDPOINT`（或 `TRON_TESTNET_ENDPOINT` / `TRON_SHASTA_ENDPOINT`），或
- `FACILITATOR_BASE_URL`。

Common config / 常用配置：

- `HOST` (default `0.0.0.0`), `PORT` (default `9000`)
- `SQLITE_PATH` (default `./db/contextswap.sqlite3`)
- `TRON_GRID_API_KEY` (optional)

Telegram/session integration:

- `TG_MANAGER_MODE`: `http` or `inprocess`
- `TG_MANAGER_AUTH_TOKEN`: required for session APIs and inprocess mode
- `TG_MANAGER_BASE_URL`: required when `TG_MANAGER_MODE=http`
- `API_AUTH_TOKEN`: required by standalone `tg_manager` service (normally set equal to `TG_MANAGER_AUTH_TOKEN`)
- `MARKET_CHAT_ID`: required when `TG_MANAGER_MODE=inprocess`
- `TELETHON_API_ID`, `TELETHON_API_HASH`, `TELETHON_SESSION`: optional but needed for live Telegram relay in inprocess mode

Telegram / 会话集成：

- `TG_MANAGER_MODE`：`http` 或 `inprocess`
- `TG_MANAGER_AUTH_TOKEN`：会话 API 与 `inprocess` 模式必需
- `TG_MANAGER_BASE_URL`：`http` 模式需要
- `API_AUTH_TOKEN`：独立 `tg_manager` 进程必需（通常与 `TG_MANAGER_AUTH_TOKEN` 保持一致）
- `MARKET_CHAT_ID`：`inprocess` 模式需要
- `TELETHON_API_ID`、`TELETHON_API_HASH`、`TELETHON_SESSION`：`inprocess` 实际 Telegram 中继时需要

OpenClaw delegation related:

- `OPENCLAW_MARKET_SLUG`
- `OPENCLAW_QUESTION_DIR`
- `OPENCLAW_WAIT_SECONDS`
- `MOCK_BOTS_ENABLED`
- `MOCK_BOTS_JSON`
- `MOCK_SELLER_AUTO_END`

## 4. API Summary / API 概览

### Health

- `GET /healthz`

### Seller lifecycle / 卖家生命周期

- `GET /v1/sellers`
- `GET /v1/sellers/{seller_id}`
- `GET /v1/sellers/by-address/{evm_address}`
- `GET /v1/sellers/search?keyword=...`
- `POST /v1/sellers/register`
- `PATCH /v1/sellers/{seller_id}`
- `POST /v1/sellers/unregister`

### Transactions / 交易

- `GET /v1/transactions`
- `GET /v1/transactions/{transaction_id}`
- `POST /v1/transactions/create`

### Session APIs (Bearer required) / 会话 API（需 Bearer）

- `GET /v1/session/{transaction_id}`
- `POST /v1/session/end`

## 5. Seller Registration Example / 卖家注册示例

```bash
curl -sS -X POST "http://127.0.0.1:9000/v1/sellers/register" \
  -H 'Content-Type: application/json' \
  -d '{
    "evm_address": "0xYourAddress",
    "price_conflux_wei": 1000000000000000,
    "price_tron_sun": 1000000,
    "description": "delegation seller",
    "keywords": ["delegation", "analysis", "market"]
  }'
```

Expected key fields / 关键返回字段：

- `seller_id`
- `status=active`

## 6. x402 Two-Step Transaction Flow / x402 两段式交易流程

1. `POST /v1/transactions/create` **without** `PAYMENT-SIGNATURE`.
2. Server returns `HTTP 402` + `PAYMENT-REQUIRED` header.
3. Client signs payment and retries with `PAYMENT-SIGNATURE`.
4. Server verifies/settles and returns `HTTP 200` + `PAYMENT-RESPONSE`.
5. Response includes `transaction_id` and optional `session`.

1. 不带 `PAYMENT-SIGNATURE` 调用 `POST /v1/transactions/create`。
2. 服务端返回 `HTTP 402` + `PAYMENT-REQUIRED`。
3. 客户端签名后携带 `PAYMENT-SIGNATURE` 重试。
4. 服务端验证并结算，返回 `HTTP 200` + `PAYMENT-RESPONSE`。
5. 响应包含 `transaction_id`，有会话时会带 `session`。

## 7. Session Auth / 会话鉴权

`/v1/session/*` requires:

```http
Authorization: Bearer <TG_MANAGER_AUTH_TOKEN>
```

When `TG_MANAGER_MODE=inprocess`, this token is mandatory.

`/v1/session/*` 需要 Bearer 鉴权；`TG_MANAGER_MODE=inprocess` 时该 token 必填。

## 8. Related Docs / 关联文档

- Project entry: `README.md`
- Frontend: `frontend/README.md`
- Telegram manager: `tg_manager/README.md`
- Buyer delegation skill: `skills/openclaw-bot-delegation/README.md`
