# ContextSwap Unified Service Structure (Planning Draft)

## 1. 目标与边界
- 目标：在联调完成后，对用户侧只暴露一个统一服务入口，完成 seller 注册、检索、x402 交易、Telegram 会话管理全链路。
- 边界：保留 `platform` 与 `tg_manager` 两个业务模块的职责划分，不在规划阶段合并业务代码实现。
- 约束：`transaction_id` 全链路统一为 x402 `tx_hash`，作为交易主键与会话主键。

## 2. 统一后端口图景
| 组件 | 端口 | 对谁开放 | 用途 |
|---|---:|---|---|
| Unified ContextSwap API | 9000 | 用户侧 + 运营侧 | 唯一对外 API 入口 |
| Facilitator API（可选） | 9100 | Unified 服务内部 | x402 verify/settle |
| Telegram Network | N/A | Unified 服务内部 | Telethon Topic 创建/中继/关闭 |

说明：
- 若使用 DirectFacilitator（进程内），可不启用 `9100`。
- 用户侧不需要访问 tg_manager 独立端口。

## 3. 模块职责（统一服务内部）
- `platform` 模块：卖家注册/注销/检索、支付要求生成、支付验证触发、交易落库、交易查询。
- `tg_manager` 模块：会话创建/查询/结束、Topic 注入、Topic 中 buyer/seller bot 消息中继、自动结束会话。
- `facilitator` 模块：x402 `verify` 与 `settle`。
- 统一入口层：路由聚合、依赖装配、生命周期管理、配置统一加载。

## 4. 用户侧 API 全景（统一入口）
### 4.1 交易前阶段
| 阶段 | Method + Path | 核心请求数据 | 核心响应数据 |
|---|---|---|---|
| Seller 注册 | `POST /v1/sellers/register` | `evm_address, price_wei, description, keywords` | `seller_id, status=active` |
| Seller 注销 | `POST /v1/sellers/unregister` | `seller_id` 或 `evm_address` | `seller_id, status=inactive` |
| Seller 检索 | `GET /v1/sellers/search?keyword=...` | `keyword` | `items[]` |

### 4.2 交易阶段（x402 两段式）
| 阶段 | Method + Path | 核心请求数据 | 核心响应数据 |
|---|---|---|---|
| 获取支付要求 | `POST /v1/transactions/create` | Body 含 `seller_id/seller_address, buyer_address, buyer_bot_username, seller_bot_username, initial_prompt`；不带 `PAYMENT-SIGNATURE` | `HTTP 402` + Header `PAYMENT-REQUIRED` |
| 支付后重试 | `POST /v1/transactions/create` | 同上 Body + Header `PAYMENT-SIGNATURE`（base64 json） | `HTTP 200` + Header `PAYMENT-RESPONSE` + `transaction_id + session` |
| 交易查询 | `GET /v1/transactions/{transaction_id}` | `transaction_id` | 交易状态、`chat_id`、`message_thread_id`、错误信息 |

### 4.3 会话管理阶段（运营/系统）
| 阶段 | Method + Path | 核心请求数据 | 核心响应数据 |
|---|---|---|---|
| 会话查询 | `GET /v1/session/{transaction_id}` | `transaction_id` + Bearer 鉴权 | 会话状态、线程标识、时间戳 |
| 手工结束 | `POST /v1/session/end` | `transaction_id, reason?` + Bearer 鉴权 | `status=ended, end_reason` |

## 5. 服务侧调用与数据流
### 5.1 支付确认主链路
1. 用户调用 `POST /v1/transactions/create`（无支付头）  
服务返回 `402 + PAYMENT-REQUIRED`。
2. 用户基于要求构造支付并重试 `POST /v1/transactions/create`（含 `PAYMENT-SIGNATURE`）。
3. Unified 服务调用 Facilitator 进行 `verify/settle`。
4. 支付成功后，Unified 服务创建交易记录（`transaction_id = tx_hash`）。
5. Unified 服务调用会话服务创建 Topic，并写入 `chat_id/message_thread_id`。
6. Unified 返回交易 + 会话信息给用户。

### 5.2 会话运行与结束链路
1. Topic 内 buyer/seller bot 按规则发送消息。
2. 服务仅在检测到 `[READY_TO_FORWARD]` 后转发该 bot 的累积内容。
3. seller 最终内容包含 `[END_OF_REPORT]` 且完成 flush 后：
服务先转发最终消息，再关闭 Topic，再将会话置为 `ended`。

## 6. 数据契约（必须统一）
- `transaction_id`：固定使用 x402 `tx_hash`。
- `PAYMENT-REQUIRED`：base64(json requirements)。
- `PAYMENT-SIGNATURE`：base64(json payment payload)。
- `PAYMENT-RESPONSE`：base64(json with txHash)。
- 会话 metadata：至少包含 `buyer_bot_username, seller_bot_username, initial_prompt`。

## 7. 调试模式规划（需同时可用）
### 7.1 分别调试模式（模块独立）
- Platform 独立启动：`9000`。
- tg_manager 独立启动：`8000`（现状兼容）。
- Platform 通过 HTTP 调 tg_manager。
- 目的：快速定位各模块本地问题。

### 7.2 联合调试模式（统一入口）
- Unified 服务启动：`9000`。
- 用户只调 Unified 入口，不直连 tg_manager。
- 目的：验证真实端到端业务行为和接口一致性。

## 8. 联调验收标准
- 验收 1：Seller 注册/检索/注销可用，返回字段稳定。
- 验收 2：交易创建严格遵循 402 -> 200 两段式，header 契约稳定。
- 验收 3：支付成功后会话必有 `chat_id + message_thread_id`。
- 验收 4：seller 结束标记触发自动关 Topic 并落库 ended。
- 验收 5：分别调试模式与联合调试模式均可运行并通过测试清单。

