# ContextSwap x402 + tg_manager 集成修改纲要（草案）

## 目标与约束
- 目标：在平台侧完成 seller 元数据注册/检索、x402 付款验证的交易创建，并在付款成功后对接 tg_manager 创建 Telegram Topic。
- 约束：tg_manager 作为独立组件，通过 HTTP API 对接；尽量不修改其关键逻辑与中继机制。
- 约束：业务流程模块化，后续可以替换存储或对接其它渠道。

## 现状简述
- x402 逻辑已在 `contextswap/x402.py` 与 `tests/phase1_demo.py` 验证可用。
- tg_manager 已提供会话创建/查询/结束 API 与 Telethon 中继逻辑。
- 平台侧尚缺少 seller 注册、搜索、交易创建与 tg_manager 对接入口。

## 模块划分（建议新增/调整）
- 平台 API 层（FastAPI）
  - seller 注册/取消注册
  - seller 检索（关键词匹配）
  - 交易创建（x402 验证 + 结算 + tg_manager 会话创建）
- 平台服务层
  - SellerService：注册/注销/检索
  - TransactionService：创建交易、x402 校验、持久化
  - TgManagerClient：tg_manager HTTP 封装（可开关/可替换）
- 平台存储层（SQLite MVP）
  - sellers 表：seller_id、evm_address、price_wei、description、keywords、status、created_at、updated_at
  - transactions 表：transaction_id、seller_id、buyer_address、price_wei、status、payment_raw_tx、tx_hash、chat_id、message_thread_id、metadata_json、created_at、updated_at

## 业务流程（端到端）
1) seller 注册
- 请求：evm 地址、收费标准、描述、关键词
- 行为：保存/更新 seller 元数据（按 evm 地址或 seller_id 幂等）
- 响应：seller_id 与元数据

2) seller 取消注册
- 请求：seller_id 或 evm 地址
- 行为：标记为 inactive（不删除）
- 响应：状态更新

3) buyer 检索 seller
- 请求：keyword（简单匹配）
- 行为：keywords / description 进行 LIKE 或分词最小化匹配
- 响应：匹配列表

4) buyer 发起交易（x402 验证）
- 请求：seller_id、buyer_address、buyer_bot_username、seller_bot_username、initial_prompt
- 行为：
  - 构造 x402 requirements（基于 seller 的 price_wei 与 evm 地址）
  - 若无 PAYMENT-SIGNATURE：返回 402 + PAYMENT-REQUIRED
  - 若有 PAYMENT-SIGNATURE：验证 + 结算（参考 `tests/phase1_demo.py`）
  - 交易入库（status=paid/ready），记录 tx_hash 与支付信息

5) 对接 tg_manager（付款成功后）
- 调用 tg_manager `/v1/session/create`
- payload：transaction_id（使用 x402 交易 hash）、buyer_bot_username、seller_bot_username、initial_prompt
- 记录返回的 chat_id 与 message_thread_id
- 交易响应返回 session 信息

## API 草案（平台侧）
- POST `/v1/sellers/register`
- POST `/v1/sellers/unregister`
- GET `/v1/sellers/search?keyword=...`
- POST `/v1/transactions/create`（x402 402/200 二段式）
- GET `/v1/transactions/{transaction_id}`（便于排障/追踪）

## 配置项（建议新增）
- 平台 SQLite 路径（默认 `./db/contextswap.sqlite3`）
- Facilitator 地址（HTTP）或本地 ConfluxFacilitator 选择开关
- tg_manager base_url 与 auth token（可选开关）

## 与 tg_manager 解耦策略
- 平台侧仅通过 HTTP 调用 tg_manager；不直接 import 内部逻辑
- TgManagerClient 允许关闭（例如本地无 Telegram 环境时仍可跑通 x402）
- 交易创建流程中，tg_manager 失败时的策略：
  - MVP：付款成功但会话创建失败 → 返回可重试错误，交易保持 pending
  - 可选：提供补偿接口（重试创建会话）

## 测试与演示
- 单元测试：seller 注册/取消/检索
- 集成测试：交易创建的 402 -> 支付 -> 200 流程（参考 `tests/phase1_demo.py`）
- tg_manager 对接测试：使用 stub/mock 客户端，验证调用参数与状态落库

## 文档更新
- README 增加平台 API 与运行方式
- 增加 `.env` 示例（平台 + tg_manager）

## 待确认问题
- seller_id 的生成规则（UUID / 由地址派生）
- 交易的 transaction_id 是否由平台生成还是由 buyer 提供
- tg_manager 失败后的处理策略（阻断 vs. 允许后续补偿）
