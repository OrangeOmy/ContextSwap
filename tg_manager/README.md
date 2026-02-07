# tg_manager (Telegram Session Manager / MVP)

This project maps an x402 transaction hash (used as the session ID) to a Telegram Supergroup Forum Topic and provides HTTP APIs to create/query/end sessions.

## 1. Preparation (Telegram)

You need to prepare the following on Telegram:

1. A Supergroup with **Forum Topics** enabled.
2. A dedicated Telegram user account (recommended) for Telethon login (MTProto userbot).
3. Add that user to the supergroup and grant admin privileges with at least **Manage Topics** permission (required for creating/closing topics).
4. Obtain the supergroup `chat_id` (usually like `-100xxxxxxxxxx`).
5. Manually add buyer bot and seller bot to the supergroup (one-time operation). Note: a Topic is just a thread view; members see the same permissions.
6. If buyer/seller bots do not respond in the group, check **Privacy Mode** first:
   - Privacy Mode ON: bots typically only receive mentions or commands.
   - Recommended: turn Privacy Mode OFF in BotFather, or ensure injected messages include `@buyer_bot @seller_bot`.

Important limitation (must understand):
- Telegram Bot API does not deliver messages sent by bots to other bots. Therefore this project uses Telethon (user account) to speak/listen in the Topic and relay messages between buyer/seller bots.

## 2. Configuration (env / .env)

Create a `.env` in the ContextSwap root directory (already in `.gitignore`).

Required:
- `API_AUTH_TOKEN`: static token for HTTP API (caller must send `Authorization: Bearer <token>`)
- `MARKET_CHAT_ID`: the supergroup `chat_id`
- `TELETHON_API_ID`: Telethon API ID (integer)
- `TELETHON_API_HASH`: Telethon API hash
- `TELETHON_SESSION`: Telethon StringSession (must be pre-authorized; server is non-interactive)

Optional:
- `SQLITE_PATH`: SQLite file path (shared default `./db/contextswap.sqlite3`)
- `HOST`: bind address (default `0.0.0.0`)
- `PORT`: listen port (default `8000`)

Example:
```bash
API_AUTH_TOKEN=change_me_to_a_long_random_string
MARKET_CHAT_ID=-1001234567890
TELETHON_API_ID=123456
TELETHON_API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELETHON_SESSION=1AABBB... (long string)
SQLITE_PATH=./db/contextswap.sqlite3
HOST=0.0.0.0
PORT=8000
```

How to generate `TELETHON_SESSION`:
- Fill `TELETHON_API_ID` and `TELETHON_API_HASH` first, leave `TELETHON_SESSION` empty.
- Run:
```bash
set -a && source ../.env && set +a
uv run python scripts/export_telethon_session.py
```
- Copy the long string output into `.env` as `TELETHON_SESSION=...`.

## 3. Start the service (uv)

Load `.env` and start:
```bash
set -a && source ../.env && set +a
uv run main.py
```

Expected:
- uvicorn startup logs
- health check returns 200

```bash
curl -sS http://127.0.0.1:8000/healthz
```

Expected response:
```json
{"status":"ok"}
```

## 4. Create session (Topic + injected prompt)

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/session/create" \
  -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "0xabc123...def",
    "buyer_bot_username": "mybuyer6384_bot",
    "seller_bot_username": "Jack_Hua_bot",
    "initial_prompt": "请 Jack_Hua_bot 使用weather skill 给出2 月 9日 香港的天气。"
  }'
```

Notes:
- `transaction_id` should be the x402 transaction hash (session ID).
- `buyer_bot_username` / `seller_bot_username` can be with or without `@`; the service normalizes and stores without `@`.
- The injected system message always includes `@buyer_bot @seller_bot` to trigger updates under Privacy Mode.
- If the same `transaction_id` already exists, `create` is idempotent: no new topic/injection by default. For troubleshooting, pass `"force_reinject": true`.
- After startup, the service relays bot messages inside the Topic. Only messages containing `[READY_TO_FORWARD]` are forwarded.
- If the seller’s forwarded content contains `[END_OF_REPORT]`, the service closes the Topic and marks the session `ended`.

Expected (HTTP):
- 200 OK
- JSON includes:
  - `transaction_id=0xabc123def456`
  - `status=running`
  - `chat_id` = `MARKET_CHAT_ID`
  - `message_thread_id` = new Topic thread id

Expected (Telegram):
- A new Topic named like `tx:0xabc123def456`
- A system injection message with rules and markers
- Buyer/seller bot messages appear in the same Topic, and userbot relays between them

Idempotency:
- Repeated create for same `transaction_id` returns 200 without duplicating Topic/injection.

## 5. Query session

```bash
curl -sS "http://127.0.0.1:8000/v1/session/0xabc123def456" \
  -H "Authorization: Bearer $API_AUTH_TOKEN"
```

Expected:
- 200 OK with session fields

## 6. Auto end session (recommended)

Triggers (both required):
- seller’s final message ends with `[READY_TO_FORWARD]` and includes `[END_OF_REPORT]`.

Server behavior (fixed order):
1. Forward the last seller message to buyer.
2. Close the Topic.
3. Update session to `ended` with `end_reason=end_marker`.

## 7. Manual end session (fallback)

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/session/end" \
  -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"0xabc123def456"}'
```

Expected:
- 200 OK, `status=ended`, `end_reason=api`, `session_end_at` not empty

Idempotency:
- Repeated end calls return existing ended session, do not overwrite `end_reason`.

## 8. Common errors

- `401`: missing/invalid `Authorization` header
- `403`: token mismatch
- `500` with Telethon not configured: ensure `TELETHON_API_ID/TELETHON_API_HASH/TELETHON_SESSION` and `MARKET_CHAT_ID` are set
- Telethon session not authorized: generate and set `TELETHON_SESSION`
- Topic not created: userbot lacks **Manage Topics** permission or `MARKET_CHAT_ID` is wrong

## 9. Run tests

```bash
uv run python -m unittest discover -s tests -p "test_*.py" -q
```

---

# tg_manager（Telegram 会话管理中间件 / MVP）

本项目用于把“x402 成功交易的 hash（作为会话 ID）”映射为 Telegram 超级群中的一个 Forum Topic（话题），并通过 HTTP API 创建/查询/结束会话。

## 1. 准备（Telegram）

在 Telegram 侧需要准备：

1. 一个超级群（Supergroup），并开启 **Forum Topics**（话题模式）。
2. 一个专用 Telegram 用户账号（建议单独注册，不要用个人号），用于 Telethon 登录（MTProto userbot）。
3. 将该用户账号拉进该超级群并提升为管理员，至少需要 **管理话题（Manage Topics）** 权限（否则无法创建/关闭 Topic）。
4. 获取该超级群的 `chat_id`（通常形如 `-100xxxxxxxxxx`）。
5. 将 buyer bot、seller bot **人工加入**该超级群（一次性操作）。注意：Telegram 的 Topic 不支持“单独拉人进某个 Topic”，Topic 只是一种线程视图，群成员看到的权限相同。
6. 若 buyer/seller bot 在群内不响应消息，优先检查它们的 **Privacy Mode（隐私模式）**：
   - 如果开启隐私模式：它们通常只会收到「@提及」或「命令」等消息
   - 推荐在 BotFather 里关闭隐私模式（Group Privacy / Privacy Mode），或确保系统注入消息里包含 `@buyer_bot @seller_bot`

重要限制（必须了解）：
- Telegram Bot API 不会把“由 bot 发送的消息”投递给其他 bot，因此本项目使用 Telethon（用户账号）在 Topic 内发言/监听，并在 buyer/seller bot 之间做消息中继。

## 2. 配置（环境变量 / .env）

推荐在 ContextSwap 仓库根目录创建 `.env`（该文件已在 `.gitignore` 中忽略，不会被提交）。

必须配置：

- `API_AUTH_TOKEN`：对外 HTTP API 的静态鉴权 token（调用方需带 `Authorization: Bearer <token>`）
- `MARKET_CHAT_ID`：预置超级群 `chat_id`（开启话题模式的群）
- `TELETHON_API_ID`：Telethon API ID（整数）
- `TELETHON_API_HASH`：Telethon API HASH
- `TELETHON_SESSION`：Telethon StringSession（必须已授权，服务端不做交互登录）

可选配置：

- `SQLITE_PATH`：SQLite 文件路径（统一默认 `./db/contextswap.sqlite3`）
- `HOST`：服务监听地址（默认 `0.0.0.0`）
- `PORT`：服务端口（默认 `8000`）

`.env` 示例：

```bash
API_AUTH_TOKEN=change_me_to_a_long_random_string
MARKET_CHAT_ID=-1001234567890
TELETHON_API_ID=123456
TELETHON_API_HASH=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELETHON_SESSION=1AABBB...（很长的一串）
SQLITE_PATH=./db/contextswap.sqlite3
HOST=0.0.0.0
PORT=8000
```

如何生成 `TELETHON_SESSION`：
- 先在 `.env` 里填好 `TELETHON_API_ID`、`TELETHON_API_HASH`（先不填 `TELETHON_SESSION`）。
- 运行导出脚本（会要求输入手机号、验证码、可选 2FA 密码）：

```bash
set -a && source ../.env && set +a
uv run python scripts/export_telethon_session.py
```

- 把脚本输出的那一长串字符串写回 `.env` 的 `TELETHON_SESSION=...`。

## 3. 启动服务（uv）

加载 `.env` 并启动：

```bash
set -a && source ../.env && set +a
uv run main.py
```

期望结果：

- 终端看到 uvicorn 启动日志
- 访问健康检查返回 200

```bash
curl -sS http://127.0.0.1:8000/healthz
```

期望响应：

```json
{"status":"ok"}
```

## 4. 创建会话（创建 Topic + 注入 prompt）

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/session/create" \
  -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "0xabc123def456",
    "buyer_bot_username": "mybuyer6384_bot",
    "seller_bot_username": "Jack_Hua_bot",
    "initial_prompt": "请 Jack_Hua_bot 使用weather skill 给出2 月 9日 香港的天气。"
  }'
```

说明：
- `transaction_id` 建议使用 x402 成功交易的 hash（作为会话 ID）。
- `buyer_bot_username` / `seller_bot_username` 支持传 `seller_bot` 或 `@seller_bot`；服务会统一规范化为不带 `@` 的形式落库。
- 服务在系统注入消息里会自动加上 `@buyer_bot @seller_bot`，用于在隐私模式下触发它们收到更新。
- 若你之前用同一个 `transaction_id` 创建过会话：再次 `create` 默认是幂等的，不会重复发送注入消息；排障时可以在请求里加 `"force_reinject": true` 强制再发一次（用于修复旧会话没有 @ 的情况）。
- 服务启动后会开启“Topic 内 bot 消息中继”：buyer/seller bot 的消息只有在包含转发触发标记 `[READY_TO_FORWARD]` 时，才会被服务端批量转发给对方（转发内容为该 bot 自上次转发后累积的全部文本）。
- 当 seller 的已转发文本中包含结束标记 `[END_OF_REPORT]` 时，服务端会在最后一次转发后立即关闭 Topic，并把会话置为 `ended`（`end_reason=end_marker`）。

期望结果（HTTP 返回）：

- 状态码 200
- JSON 中包含：
  - `transaction_id=0xabc123def456`
  - `status=running`
  - `chat_id` 等于你的 `MARKET_CHAT_ID`
  - `message_thread_id` 为新建 Topic 的 thread id

期望结果（Telegram 群内）：

- 超级群中出现一个新 Topic，标题类似 `tx:0xabc123def456`
- Topic 内出现一条“系统注入消息”，包含 `transaction_id`、`initial_prompt`、`[READY_TO_FORWARD]` 与 `[END_OF_REPORT]` 规则
- buyer/seller bot 的回复会在同一 Topic 内出现；同时 userbot 会将双方消息互相转述（新消息 @ 对方，不引用原消息；仅绑定 Topic 根消息以保证落在线程内），让它们“看起来在对话”

幂等行为：

- 重复调用同一个 `transaction_id` 的 create，仍返回 200，但不会重复创建 Topic、不会重复注入消息（返回已有会话）。

## 5. 查询会话

```bash
curl -sS "http://127.0.0.1:8000/v1/session/0xabc123def456" \
  -H "Authorization: Bearer $API_AUTH_TOKEN"
```

期望结果：

- 状态码 200
- 返回与创建时一致的会话字段（包含 `chat_id/message_thread_id/status` 等）

## 6. 自动结束会话（推荐路径）

触发条件（需同时满足）：

- seller 最后一段消息末尾带有 `[READY_TO_FORWARD]`，且该段内容包含 `[END_OF_REPORT]`。

服务端行为（固定顺序）：

1. 先将 seller 最后一条消息转发给 buyer。
2. 再关闭 Topic。
3. 最后将会话状态落库为 `ended`，并写入 `end_reason=end_marker`。

你可以通过查询接口验证：

```bash
curl -sS "http://127.0.0.1:8000/v1/session/0xabc123def456" \
  -H "Authorization: Bearer $API_AUTH_TOKEN"
```

期望结果：

- `status=ended`
- `end_reason=end_marker`
- `session_end_at` 不为空

## 7. 手动结束会话（运维兜底）

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/session/end" \
  -H "Authorization: Bearer $API_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"0xabc123def456"}'
```

期望结果（HTTP 返回）：

- 状态码 200
- `status=ended`
- `end_reason=api`
- `session_end_at` 不为空

期望结果（Telegram 群内）：

- 对应 Topic 被关闭（锁定）/不可继续发言（取决于 Telegram 客户端表现）

幂等行为：

- 重复结束同一 `transaction_id` 会返回已有 ended 会话，不会覆盖 `end_reason`。

## 8. 常见错误与排障

- `401`：缺少或不合法 `Authorization`（需要 `Authorization: Bearer <token>`）
- `403`：token 不匹配（确认调用方 token 与 `.env` 中 `API_AUTH_TOKEN` 一致）
- `500` 且提示未配置 Telethon：确认 `.env` 中 `TELETHON_API_ID/TELETHON_API_HASH/TELETHON_SESSION` 与 `MARKET_CHAT_ID` 已设置
- Telethon session 未授权：需要先生成并填入正确的 `TELETHON_SESSION`（服务端不会弹出交互登录）
- Telegram 侧不创建 Topic：大概率是 userbot 在群内没有 **管理话题（Manage Topics）** 权限，或 `MARKET_CHAT_ID` 不正确

## 9. 运行测试

```bash
uv run python -m unittest discover -s tests -p "test_*.py" -q
```
