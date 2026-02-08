# Implementation Plan (Delegation Demo)

## Status
- 状态：进行中（Phase 1-3 已落地，Phase 4 联调待执行）
- 日期：2026-02-08
- 目标：打通“主 bot 主动委托子 bot -> 端点检索最合适 bot -> x402 支付拉群 -> 异步落地 md -> 主 bot 回收 md 并给最终答案”的完整 demo。

## End-to-End Flow (Target)
1. 主 bot 在任务中识别“需要外部专家 bot 协助”。
2. 主 bot 使用新 skill 调 `seller search` 端点，筛选候选 bot。
3. 主 bot 选择 bot 后调 `POST /v1/transactions/create`，完成 x402 `402 -> 200`。
4. 支付成功后 tg_manager 创建 Topic 并注入系统消息（含异步 md 规则）。
5. 子 bot 在 Topic 回复，并把结果写入 `~/.openclaw/question/*.md`。
6. 主 bot 在提示词要求下等待 2 分钟后扫描该目录。
7. 主 bot 读取目标 md 文件并合并上下文。
8. 主 bot 输出最终回答。

## Requirement Breakdown

### R1: 新增 OpenClaw Delegation Skill
- 新增 skill 目录（建议）：`skills/openclaw-bot-delegation/`
- skill 内容：
  - 指导主 bot 何时触发“找外援”。
  - 约束调用顺序：检索 bot -> 创建交易 -> 处理 402 -> 进入 Topic。
  - 约束产物：记录 `seller_id`、`transaction_id`、`chat_id`、`message_thread_id`、目标 md 文件名。
  - 约束失败分支：检索为空、支付失败、会话创建失败的回退话术与重试策略。
- 元数据文件：
  - `SKILL.md`
  - `agents/openai.yaml`

### R2: 修改初始提示词（支持异步 md 交互）
- 注入点：`tg_manager/tg_manager/services/session_service.py` 的 `_build_system_message(...)`。
- 新增提示词规则：
  - 子 bot：回答后必须将内容保存为 md 到 `~/.openclaw/question/`。
  - 文件名规范（建议）：`{transaction_id}__{bot_username}__answer.md`。
  - 子 bot 在 Topic 回执写入的文件名，并附带 `[READY_TO_FORWARD]`。
  - 主 bot：在 120 秒后扫描 `~/.openclaw/question/`，读取对应 md，再输出最终答案。
- 兼容当前标记：
  - 保留 `[READY_TO_FORWARD]` 与 `[END_OF_REPORT]` 机制，不改现有中继语义。

### R3: Mock 多 bot（固定回答、可重复）
- 目标：不接入真实 bot，仅通过 @提及触发 mock 回复。
- 行为约束：
  - 监听 Topic 消息，检测 `@bot_username` 是否在 mock 配置中。
  - 若命中，返回固定模板文本（每次相同，不依赖问题内容）。
  - mock 文本末尾自动包含 `[READY_TO_FORWARD]`；若该 bot 是 seller 可按配置追加 `[END_OF_REPORT]`。
- 配置建议：
  - `MOCK_BOTS_ENABLED=true/false`
  - `MOCK_BOTS_JSON`（`{ "weather_bot": "...固定回答...", "law_bot": "...固定回答..." }`）
- 优先级：
  - 开启 mock 时，目标 bot 命中 mock 列表则走 mock，不要求真实 bot 在线。

## File-Level Change Plan

### A. Skill Files (new)
- `skills/openclaw-bot-delegation/SKILL.md`
- `skills/openclaw-bot-delegation/agents/openai.yaml`
- （可选）`skills/openclaw-bot-delegation/references/api-flow.md`

### B. Platform / API
- `contextswap/platform/api/routes/transactions.py`
  - 预留或扩展 metadata 字段，用于会话注入异步规则（如 md 目录、等待秒数、mock 目标 bot）。
- `contextswap/platform/services/session_client.py`
  - 评估是否扩展 `create_session(...)` 协议参数，以传递 async/mock 元信息。
- `contextswap/platform/services/tg_manager_client.py`
- `contextswap/platform/services/inprocess_tg_manager_client.py`
  - 对齐新增字段透传。

### C. tg_manager
- `tg_manager/tg_manager/services/session_service.py`
  - 改系统注入提示词模板，加入 md 持久化与 2 分钟回收规则。
- `tg_manager/tg_manager/core/config.py`
  - 新增 mock 相关配置解析。
- `tg_manager/tg_manager/api/app.py`
  - 生命周期中挂载/启动 mock 处理器。
- `tg_manager/tg_manager/services/`（new）
  - 新增 mock 引擎（建议 `mock_bot_relay.py`）。
- `tg_manager/tg_manager/services/telethon_relay.py`
  - 与 mock 引擎协同，避免回环/重复转发。

### D. Tests / E2E
- `tg_manager/tests/`：
  - mock bot @提及触发测试
  - 固定回答一致性测试
  - seller mock 自动结束测试
- `tests/`：
  - 402 -> 会话创建 -> 异步提示词注入字段断言
  - 端到端 demo 冒烟（含 md 目录规则）

## Phases

## Phase 0: Requirement Freeze
- [x] 确认 skill 名称、放置路径、触发语句风格（中文/英文）。
- [x] 确认 md 文件命名规范与目录是否固定为 `~/.openclaw/question/`。
- [x] 确认 mock bot 列表输入方式（环境变量）。

Checkpoint:
- 所有“待确认项”落定，避免后续返工。

## Phase 1: Skill Skeleton
- [x] 创建 `openclaw-bot-delegation` skill 目录与元数据。
- [x] 完成 SKILL.md：端点调用顺序、失败回退、输出字段。
- [x] 完成 `agents/openai.yaml`。

Checkpoint:
- skill 可被 OpenClaw 加载并在“需要找外援 bot”时触发。

## Phase 2: Prompt Injection Upgrade
- [x] 改造 `_build_system_message(...)` 注入异步 md 规则。
- [x] 把 async 相关配置（目录、等待秒数、market_slug）写入 metadata 并可追踪。
- [x] 保持既有 `[READY_TO_FORWARD]`/`[END_OF_REPORT]` 协议。

Checkpoint:
- 新建 Topic 的首条系统消息包含完整异步协作说明。

## Phase 3: Mock Bot Runtime
- [x] 增加 mock 配置加载与默认 deterministic 回复。
- [x] 实现“检测 @seller_bot -> 固定回答”处理器并接入 relay。
- [x] 对 seller mock 支持可选自动结束。

Checkpoint:
- 无真实 bot 情况下，Topic 内可稳定得到 deterministic mock 回复。

## Phase 4: E2E Demo Validation (Pending)
- [ ] 联调脚本：主 bot 请求外援 -> 交易 -> Topic -> mock 回答 -> 最终收敛。
- [ ] 验证 md 路径与文件名契约。
- [ ] 回归现有 unified/separate 流程不回退。

Checkpoint:
- 至少 1 条完整演示记录可复现。

## Acceptance Criteria
- [ ] 主 bot 能基于 skill 主动触发外援检索与请求。
- [ ] 子 bot（真实或 mock）都能按照提示词完成 md 交互契约。
- [ ] 主 bot 能在 120 秒后读取 md 并输出最终回答。
- [ ] mock 模式下同一 bot 对同类触发输出完全一致（deterministic）。
- [ ] 现有 x402 + Topic 流程不被破坏。

## Confirmed Decisions
1. skill 名称：`openclaw-bot-delegation`。
2. md 文件名：`{transaction_id}__{bot_username}__answer.md`。
3. 等待策略：可配置，默认 `120s`。
4. mock 配置来源：`MOCK_BOTS_JSON`。
5. mock seller 默认自动追加 `[END_OF_REPORT]`。
