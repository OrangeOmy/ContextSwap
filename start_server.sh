#!/bin/bash
cd /root/ContextSwap
set -a && source .env && set +a
uv run python -m contextswap.platform.main