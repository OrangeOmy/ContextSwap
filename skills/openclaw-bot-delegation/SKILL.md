---
name: openclaw-bot-delegation
description: Delegate tasks to specialist bots with a strict x402 flow. Use when the main OpenClaw agent must detect HTTP 402 payment requirement, create a real on-chain Conflux transaction, open a real Telegram Topic session, and persist deterministic markdown outputs in ~/.openclaw/question for later loading.
---

# OpenClaw Bot Delegation

This skill is intentionally low-freedom so weaker agents can execute it reliably.

## Trigger Conditions (Main Dialog)
Use this skill only when all are true:
1. The main dialog needs external specialist bot delegation.
2. The flow must pass through `POST /v1/transactions/create`.
3. First create call returns `HTTP 402` and includes `PAYMENT-REQUIRED`.

If the first call does not return `402`, stop and report error. Do not simulate payment success.

## Required Runtime
1. Start server from repo root:
- `./start_server.sh`
2. Base URL default:
- `http://127.0.0.1:9000`
3. Health check:
- `GET /healthz` must return `200` and `{\"status\":\"ok\"}`

## APIs Used
- `GET /v1/sellers/search?keyword=<topic>`
- `POST /v1/transactions/create` (must execute two phases: 402 -> 200)
- `GET /v1/transactions/{transaction_id}` (optional post-check)
- `GET /v1/session/{transaction_id}` (optional post-check, needs Bearer token)

## One-Command Transaction + Session + Result
Use bundled script:
- `skills/openclaw-bot-delegation/scripts/sign_and_create_transaction.py`

Run:
```bash
cd /root/ContextSwap
uv run python skills/openclaw-bot-delegation/scripts/sign_and_create_transaction.py \
  --env-file /root/.openclaw/workspace/.env \
  --seller-id "$DEMO_POLLING_SELLER_ID" \
  --seller-bot-username "$DEMO_POLLING_BOT_USERNAME" \
  --initial-prompt "Please provide polling probability breakdown for this market." \
  --write-legacy-filename
```

Optional input for deterministic prewritten markdown:
- `--mock-result-file <path-to-prewritten-md>`

Script contract:
1. Phase-1 calls create without `PAYMENT-SIGNATURE`; expects `HTTP 402` + `PAYMENT-REQUIRED`.
2. Signs Conflux payment locally and retries phase-2 with `PAYMENT-SIGNATURE`; expects `HTTP 200`.
3. Requires `session.chat_id` and `session.message_thread_id` in success response.
4. Polls RPC to check transaction hash is discoverable.
5. Writes deterministic markdown output file for main-agent loading.

## Output Contract (Main Agent Must Read This)
Primary file (always):
- `~/.openclaw/question/<transaction_id>.md`

Optional compatibility file:
- `~/.openclaw/question/<transaction_id>__<seller_bot_username>__answer.md`

Main agent should load only `<transaction_id>.md`.

## Returned JSON Fields
Script stdout returns JSON containing:
- `transaction_id`
- `tx_hash`
- `chat_id`
- `message_thread_id`
- `rpc_confirmed`
- `explorer_url`
- `result_md_path`
- `legacy_result_md_path`
- `payment_response`
- `raw_response`

## Subtopic Response Strategy
Default for demos:
1. Use real Topic creation.
2. Allow mock content for delegated answer text.
3. Keep relay markers compatible with platform rules:
- `[READY_TO_FORWARD]`
- `[END_OF_REPORT]`

Recommended env defaults for stable demos:
- `MOCK_BOTS_ENABLED=true`
- `MOCK_SELLER_AUTO_END=true`

## Case Extension Rules
To add a new case, only change runtime inputs:
1. `seller_id`
2. `seller_bot_username`
3. `initial_prompt`
4. Optional `--mock-result-text` or `--mock-result-file`

Do not fork the script or change the 402/two-phase flow.

## New Demo: Headhunter Agent (Simulated)
Goal:
1. Buyer A (job seeker) submits CV to a headhunter agent.
2. Buyer B (HR) asks the same headhunter agent for best matches.
3. Both rounds must still go through real x402 flow + real Topic creation.
4. Subtopic dialog can stay invisible in demo; final answer is loaded from prewritten markdown in `question_dir`.

Use these prewritten markdown templates:
- `skills/openclaw-bot-delegation/assets/headhunter/candidate_cv_ingested.md`
- `skills/openclaw-bot-delegation/assets/headhunter/hr_match_report.md`
- `skills/openclaw-bot-delegation/assets/headhunter/candidate_cv_index.md`
- `skills/openclaw-bot-delegation/assets/headhunter/CAND-2026-001.md`
- `skills/openclaw-bot-delegation/assets/headhunter/CAND-2026-014.md`
- `skills/openclaw-bot-delegation/assets/headhunter/CAND-2026-023.md`

### Prepare Question Directory
```bash
mkdir -p ~/.openclaw/question
cp skills/openclaw-bot-delegation/assets/headhunter/candidate_cv_ingested.md ~/.openclaw/question/
cp skills/openclaw-bot-delegation/assets/headhunter/hr_match_report.md ~/.openclaw/question/
cp skills/openclaw-bot-delegation/assets/headhunter/candidate_cv_index.md ~/.openclaw/question/
cp skills/openclaw-bot-delegation/assets/headhunter/CAND-2026-001.md ~/.openclaw/question/
cp skills/openclaw-bot-delegation/assets/headhunter/CAND-2026-014.md ~/.openclaw/question/
cp skills/openclaw-bot-delegation/assets/headhunter/CAND-2026-023.md ~/.openclaw/question/
```

### Round 1: Job Seeker Submits CV (Mock Ingestion)
```bash
cd /root/ContextSwap
uv run python skills/openclaw-bot-delegation/scripts/sign_and_create_transaction.py \
  --env-file /root/.openclaw/workspace/.env \
  --seller-id "$DEMO_HEADHUNTER_SELLER_ID" \
  --seller-bot-username "$DEMO_HEADHUNTER_BOT_USERNAME" \
  --buyer-bot-username "$DEMO_JOBSEEKER_BOT_USERNAME" \
  --initial-prompt "我是求职者，请将我的CV入库，并回复是否已登记。" \
  --mock-result-file ~/.openclaw/question/candidate_cv_ingested.md \
  --write-legacy-filename
```

Expected semantic result in `<transaction_id>.md`:
- "猎头已经读了你的cv，有合适岗位会通知"

### Round 2: HR Asks for Matching Candidates (Mock Retrieval)
```bash
cd /root/ContextSwap
uv run python skills/openclaw-bot-delegation/scripts/sign_and_create_transaction.py \
  --env-file /root/.openclaw/workspace/.env \
  --seller-id "$DEMO_HEADHUNTER_SELLER_ID" \
  --seller-bot-username "$DEMO_HEADHUNTER_BOT_USERNAME" \
  --buyer-bot-username "$DEMO_HR_BOT_USERNAME" \
  --initial-prompt "我是HR，请根据岗位需求返回最匹配的候选人。岗位：高级后端工程师，Python/Go，分布式系统经验。" \
  --mock-result-file ~/.openclaw/question/hr_match_report.md \
  --write-legacy-filename
```

Expected behavior:
1. Script still does 402 -> signed payment -> 200.
2. Session and subtopic are still created.
3. Result markdown is deterministic mock content from prewritten file.
4. Main agent reads `~/.openclaw/question/<transaction_id>.md` and reports who is most suitable.
5. If report only contains `candidate_id`, main agent should map via `~/.openclaw/question/candidate_cv_index.md` then read `~/.openclaw/question/<candidate_id>.md`.

### Demo Scope Guardrails
- Headhunter replies are fully simulated.
- Do not claim real CV parsing or real database retrieval in this demo.
- Do not skip x402 payment flow.

## Failure Handling
- Seller search empty: report no seller and request alternate keyword.
- Phase-1 is not `402`: stop and report mismatch.
- Missing `PAYMENT-REQUIRED`: stop and report protocol failure.
- Phase-2 is not `200`: stop and report response body.
- Missing session fields after paid transaction: treat as failed delegation.
- Result markdown write failure: treat as failed delegation.
