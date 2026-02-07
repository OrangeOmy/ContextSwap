# Implementation Plan

## Phase 1: Platform MVP (x402 + tg_manager integration)
- [x] Add platform SQLite schema for sellers and transactions
- [x] Add seller registration, unregistration, and keyword search services
- [x] Add transaction creation flow with x402 verification/settlement
- [x] Add tg_manager client wrapper and integration hook after payment
- [x] Add FastAPI app with seller/transaction routes
- [x] Add module-level tests for seller service, transaction flow, and tg_manager client

## Notes
- tg_manager remains a separate service and is only accessed via HTTP.
- Transaction creation returns 402 with `PAYMENT-REQUIRED` when payment is missing/invalid.
- After payment settles, tg_manager is invoked to create the Telegram Topic session.
- Session ID equals the x402 transaction hash.

## Documentation
- README files now include English + Chinese sections.
- Root AGENT.md is Chinese-only as required.
