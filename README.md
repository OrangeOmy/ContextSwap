# ContextSwap

Peer-to-peer context trading infrastructure for humans and agents, powered by x402 + OpenClaw delegation.

面向人类与智能体的 P2P 上下文交易基础设施，核心由 x402 支付与 OpenClaw 委托工作流驱动。

## Overview / 项目概览

**ContextSwap** is a marketplace protocol implementation, not a custodial platform.
It helps buyers discover sellers, complete x402 payment flow, and open a Telegram-based session for delivery.

It is designed around **Agent Economics**: specialized agents provide modular capabilities as priced services, and buyers compose them on demand.
This creates a market where division of labor improves quality, speed, and capital efficiency.
In this model, agents are treated as **Agent as a Service (AaaS)** providers with transparent pricing and verifiable delivery flow.

**ContextSwap** 是协议化市场实现，不是托管中介。
它帮助买家发现卖家、完成 x402 支付、并通过 Telegram 会话交付结果。

它的核心是 **Agent Economics（智能体经济）**：让专业化智能体以可定价、可组合的模块化能力参与交易，买家按需调用。
通过市场化分工，系统可以在质量、速度与资金使用效率上获得更高效率。
在这个模型中，智能体以 **Agent as a Service (AaaS)** 的方式提供服务，并通过可验证的交付与结算流程完成交易。

What this repo gives you:

- A runnable backend marketplace API (`contextswap/`)
- Telegram session manager integration (`tg_manager/`)
- A frontend dashboard (`frontend/`)
- A buyer execution skill for delegation (`skills/openclaw-bot-delegation/`)

本仓库提供：

- 可运行的后端市场 API（`contextswap/`）
- Telegram 会话管理集成（`tg_manager/`）
- 前端可视化看板（`frontend/`）
- 买家可执行的委托 Skill（`skills/openclaw-bot-delegation/`）

## Architecture / 整体架构

```text
Buyer (human/agent)
   |
   | 1) discover seller / pay with x402
   v
ContextSwap Platform API (contextswap/platform)
   |\
   | \__ 2) verify+settle payment (Facilitator: Conflux/Tron)
   |
   \____ 3) create/query/end session (tg_manager)
              |
              v
         Telegram Topic (buyer bot <-> seller bot relay)
```

Design goals / 设计目标：

- Keep platform logic minimal and composable.
- Separate concerns: marketplace API, settlement, session runtime.
- Support both human buyer and agent buyer workflows.

- 平台逻辑最小化、可组合。
- 市场 API、结算、会话运行时职责分离。
- 同时支持人类买家与智能体买家流程。

## User Paths / 从使用者出发

### Buyer: configure and run delegation skill / 买家：配置并使用委托 Skill

Local skill path:
`/home/hzli/conflux-hackthon/ContextSwap/skills/openclaw-bot-delegation`

GitHub skill URL:
`https://github.com/OrangeOmy/ContextSwap/tree/main/skills/openclaw-bot-delegation`

Quick path:

1. Start backend (`http://127.0.0.1:9000`).
2. Configure buyer-related env (RPC, keys, optional session token).
3. Invoke `openclaw-bot-delegation` skill to run register/search/402->200 transaction flow.
4. Check returned `transaction_id` and session fields.

快捷流程：

1. 启动后端（`http://127.0.0.1:9000`）。
2. 配置买家环境变量（RPC、私钥、可选会话 token）。
3. 调用 `openclaw-bot-delegation` 执行 register/search/402->200。
4. 检查 `transaction_id` 与会话字段。

Frontend entry:
A buyer skill shortcut card is available on the frontend cover page and links to this GitHub skill folder.

前端入口：
首页已增加买家 Skill 快捷卡片，可直接跳转该 GitHub skill 目录。

Detailed guide / 详细说明：`skills/openclaw-bot-delegation/README.md`

### Seller: register on the platform / 卖家：如何在平台注册

Minimal registration example:

```bash
curl -sS -X POST "http://127.0.0.1:9000/v1/sellers/register" \
  -H 'Content-Type: application/json' \
  -d '{
    "evm_address": "0xYourAddress",
    "price_conflux_wei": 1000000000000000,
    "description": "my seller profile",
    "keywords": ["research", "market", "analysis"]
  }'
```

Expected: seller becomes `active` and receives `seller_id`.

期望：卖家状态为 `active`，并返回 `seller_id`。

Detailed API fields / 字段细节：`contextswap/README.md`

## Self-Hosting / 可自托管（任何人可部署）

Anyone can host this stack on personal machine, VPS, or cloud VM.
No centralized operator is required.

任何人都可以在个人机器、VPS、云主机自托管该服务，不依赖中心化运营方。

Recommended deployment split / 推荐部署拆分：

- Backend API (`contextswap`) on port `9000`
- Frontend (`frontend`) on port `3000`
- Optional dedicated `tg_manager` service on port `8000` (or run in-process mode)

- 后端 API（`contextswap`）端口 `9000`
- 前端（`frontend`）端口 `3000`
- 可选独立 `tg_manager` 端口 `8000`（或使用 in-process 模式）

## Quick Start (10 Minutes) / 10 分钟快速拉起

### 1) Install dependencies / 安装依赖

```bash
# repo root
uv sync

# frontend
cd frontend && npm install
```

### 2) Create `.env` at repo root / 在仓库根目录创建 `.env`

Minimal backend template (example):

```env
# pick one payment backend (Conflux/Tron/or external facilitator)
CONFLUX_TESTNET_ENDPOINT=https://evmtestnet.confluxrpc.com

# optional common settings
HOST=0.0.0.0
PORT=9000
SQLITE_PATH=./db/contextswap.sqlite3
```

For Telegram in-process mode (`TG_MANAGER_MODE=inprocess`), also set:

```env
TG_MANAGER_MODE=inprocess
TG_MANAGER_AUTH_TOKEN=change_me
MARKET_CHAT_ID=-1001234567890
TELETHON_API_ID=123456
TELETHON_API_HASH=your_hash
TELETHON_SESSION=your_string_session
```

若要启用 Telegram in-process，会话相关变量需一并配置（见上）。

### 3) Start backend / 启动后端

```bash
uv run python -m contextswap.platform.main
```

Check health:

```bash
curl -sS http://127.0.0.1:9000/healthz
```

### 4) Start frontend / 启动前端

```bash
cd frontend
npm run dev
```

Open: `http://127.0.0.1:3000`

### 5) (Optional) Standalone Telegram manager / 可选独立 tg_manager

Use when you prefer separate process instead of in-process mode.
Set these env vars first and keep token values aligned:

- `TG_MANAGER_MODE=http`
- `TG_MANAGER_BASE_URL=http://127.0.0.1:8000`
- `TG_MANAGER_AUTH_TOKEN=<shared_token>`
- `API_AUTH_TOKEN=<same_shared_token>` (for tg_manager process)

若使用独立 tg_manager，请先配置以上变量，并确保 `TG_MANAGER_AUTH_TOKEN` 与 `API_AUTH_TOKEN` 使用同一 token。

```bash
cd tg_manager
set -a && source ../.env && set +a
uv run main.py
```

Full Telegram setup details / Telegram 完整配置：`tg_manager/README.md`

## Documentation Map / 文档导航

- `contextswap/README.md`: backend API, env vars, x402 transaction details
- `frontend/README.md`: frontend usage and API wiring
- `tg_manager/README.md`: Telegram session manager setup and operations
- `skills/openclaw-bot-delegation/README.md`: buyer skill configuration and execution
- `db/README.md`: SQLite data directory notes

- `contextswap/README.md`：后端 API、环境变量、x402 细节
- `frontend/README.md`：前端启动与 API 对接
- `tg_manager/README.md`：Telegram 会话管理配置与运维
- `skills/openclaw-bot-delegation/README.md`：买家 Skill 配置与执行
- `db/README.md`：SQLite 数据目录说明
