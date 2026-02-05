# ContextSwap

Phase 2 scaffold for x402 on Conflux eSpace.

## Structure
- `contextswap/facilitator` - Base facilitator logic + Conflux implementation + FastAPI app.
- `contextswap/seller` - Minimal paid `/weather` endpoint (FastAPI).
- `tests/phase1_demo.py` - Phase 1 demo flow (buyer -> seller -> facilitator).
- `frontend/` - Placeholder for future TypeScript UI.
- `db/` - Placeholder for future database assets.

## Run demo (Phase 1 logic)
```
uv run python tests/phase1_demo.py
```

This uses `env/.env` for Conflux testnet RPC + keys.
