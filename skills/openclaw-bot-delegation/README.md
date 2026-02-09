# OpenClaw Bot Delegation Skill

Buyer-facing guide for configuring and running the delegation workflow skill.

面向买家的技能配置指南：如何配置并执行委托交易工作流。

## 1. Location / 路径

- Local path: `/home/hzli/conflux-hackthon/ContextSwap/skills/openclaw-bot-delegation`
- Skill spec file: `skills/openclaw-bot-delegation/SKILL.md`
- GitHub: `https://github.com/OrangeOmy/ContextSwap/tree/main/skills/openclaw-bot-delegation`

## 2. What This Skill Does / 这个 Skill 做什么

It executes the full delegation transaction loop in order:

1. register seller,
2. search seller,
3. run x402 `402 -> signed retry -> 200`,
4. verify `transaction_id` and `session` fields,
5. optionally restart and health-check platform.

该技能会按固定顺序执行：

1. 注册卖家，
2. 搜索卖家，
3. 执行 x402 两段式（`402 -> 签名重试 -> 200`），
4. 校验 `transaction_id` 与 `session` 字段，
5. 可选执行平台重启与健康检查。

## 3. Buyer Setup / 买家侧配置

Prepare backend env first (`.env` in repo root). At minimum, ensure:

- `PLATFORM_BASE_URL` (default `http://127.0.0.1:9000`)
- chain RPC and key set required by platform (Conflux or Tron)
- `TG_MANAGER_AUTH_TOKEN` if you want session query/end checks

先完成后端 `.env`，至少保证：

- `PLATFORM_BASE_URL`（默认 `http://127.0.0.1:9000`）
- 链上 RPC 与密钥（Conflux 或 Tron）
- 若要校验会话接口，设置 `TG_MANAGER_AUTH_TOKEN`

Optional delegation overrides / 可选委托参数：

- `DELEGATION_SEARCH_KEYWORD`
- `DELEGATION_BUYER_BOT`
- `DELEGATION_SELLER_BOT`
- `DELEGATION_INITIAL_PROMPT`
- `DELEGATION_PAYMENT_NETWORK` (`conflux` / `tron`)

## 4. How Buyer Uses It / 买家如何使用

If your agent runtime supports skill invocation, call this skill by name and ask it to execute the end-to-end delegation flow.

如果你的智能体运行时支持 skill 调用，直接按技能名触发并要求执行端到端委托流程。

Suggested instruction / 建议指令：

```text
Use skill openclaw-bot-delegation to run seller register/search and x402 transaction flow on http://127.0.0.1:9000, then verify transaction/session status.
```

## 5. Success Criteria / 成功标准

- first create call returns `HTTP 402` with `PAYMENT-REQUIRED`
- retry with signature returns `HTTP 200`
- response includes `transaction_id`
- session includes `chat_id` and `message_thread_id` (when tg_manager is configured)

- 第一次创建交易返回 `HTTP 402` 且包含 `PAYMENT-REQUIRED`
- 签名重试返回 `HTTP 200`
- 响应包含 `transaction_id`
- 配置 tg_manager 时，`session` 含 `chat_id` 与 `message_thread_id`

## 6. Related Docs / 关联文档

- Project overview: `README.md`
- Backend technical doc: `contextswap/README.md`
- Telegram setup: `tg_manager/README.md`
- Frontend dashboard: `frontend/README.md`
