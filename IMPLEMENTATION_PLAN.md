# Implementation Plan (Unified Debug Roadmap)

## Scope
- 目标：实现“模块可分别调试 + 统一入口可联合调试”双模式并存。
- 本计划只定义阶段、检查点与验收，不在本文件中落具体代码实现。

## Phase 0: Baseline Freeze
- [ ] 锁定当前接口与行为基线（platform + tg_manager）。
- [ ] 记录当前端口与环境变量矩阵。
- [ ] 固化现有测试通过结果作为回归基线。

Checkpoint:
- `tests/` 与 `tg_manager/tests/` 全部通过。
- 关键接口路径与请求字段不变更。

## Phase 1: Unified Contract Finalization
- [ ] 确认统一端口策略（Unified:9000, Facilitator:9100 可选）。
- [ ] 确认全链路 `transaction_id = tx_hash` 规则。
- [ ] 确认 402 交互契约：`PAYMENT-REQUIRED / PAYMENT-SIGNATURE / PAYMENT-RESPONSE`。
- [ ] 确认会话 API 是否在统一入口暴露（建议保留 `/v1/session/*`）。

Checkpoint:
- `structure.md` 评审通过。
- 用户侧与服务侧都能基于同一份字段定义对接。

## Phase 2: Dual-Mode Bootstrapping (Separate + Unified)
- [ ] 保持 platform 独立启动路径可用。
- [ ] 保持 tg_manager 独立启动路径可用。
- [ ] 设计 unified 启动路径（单进程聚合路由与生命周期）。
- [ ] 统一配置加载策略，避免冲突变量名与重复初始化。

Checkpoint:
- 分别调试模式启动成功：platform / tg_manager 各自健康检查通过。
- 联合调试模式启动成功：统一入口健康检查通过。

## Phase 3: Internal Integration (Replace Internal HTTP Hop)
- [ ] 在 unified 模式下，交易成功后会话创建改为进程内调用。
- [ ] 保留 separate 模式原有 HTTP 链路，避免回归风险。
- [ ] 统一错误语义：session 创建失败时交易状态与错误字段一致可追踪。
- [ ] 打通交易记录与会话记录的主键关联。

Checkpoint:
- unified 模式下 `POST /v1/transactions/create` 能返回 `session.chat_id/message_thread_id`。
- separate 模式原链路行为不变。

## Phase 4: End-to-End Joint Debug
- [ ] 真实链路验证：seller 注册 -> buyer 检索 -> 402 -> 支付 -> Topic 创建。
- [ ] 验证 Topic 中继：仅含 `[READY_TO_FORWARD]` 时转发。
- [ ] 验证自动结束：seller 最终内容含 `[END_OF_REPORT]` 后关闭 Topic 并落库 ended。
- [ ] 验证手动结束兜底接口。

Checkpoint:
- 提供至少一条完整联调记录（请求样例 + 关键响应字段 + 状态迁移）。
- 数据库中交易与会话状态一致，无孤儿会话。

## Phase 5: Regression and Delivery
- [ ] 补充 unified 场景测试（含 happy path 与关键失败分支）。
- [ ] 回归 separate 场景测试，确保独立调试能力未破坏。
- [ ] 更新 README 与运行说明，明确两种模式的启动命令和端口。
- [ ] 输出上线前检查清单（配置、鉴权、外部依赖、回滚）。

Checkpoint:
- “分别调试”与“联合调试”两套清单全部通过。
- 文档可支持新成员按步骤独立复现。

## Acceptance Criteria
- [ ] 用户侧只需一个统一入口即可完成端到端交易与会话流程。
- [ ] 运营侧仍可查询/结束会话并追踪交易。
- [ ] 任何阶段失败都可通过交易与会话查询接口定位问题。
- [ ] 两个模块可独立排障，也可统一联调。
