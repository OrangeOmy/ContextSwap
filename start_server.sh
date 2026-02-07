#!/bin/bash
set -euo pipefail

cd /root/ContextSwap
set -a && source .env && set +a

has_conflux=0
has_tron=0

if [ -n "${FACILITATOR_BASE_URL:-}" ] || [ -n "${CONFLUX_TESTNET_ENDPOINT:-}" ]; then
  has_conflux=1
fi

if [ -n "${TRON_NILE_ENDPOINT:-}" ] || [ -n "${TRON_TESTNET_ENDPOINT:-}" ] || [ -n "${TRON_SHASTA_ENDPOINT:-}" ]; then
  has_tron=1
fi

if [ "$has_conflux" -eq 0 ] && [ "$has_tron" -eq 0 ]; then
  echo "错误: 未配置 Conflux 或 Tron RPC，请在 .env 中设置 CONFLUX_TESTNET_ENDPOINT 或 TRON_NILE_ENDPOINT。"
  exit 1
fi

networks=()
if [ "$has_conflux" -eq 1 ]; then
  networks+=("conflux")
fi
if [ "$has_tron" -eq 1 ]; then
  networks+=("tron")
fi

echo "即将启动平台服务，已检测到支付网络: ${networks[*]}"
echo "服务地址: ${HOST:-0.0.0.0}:${PORT:-9000}"

if [ "${START_SERVER_DRY_RUN:-0}" = "1" ]; then
  echo "START_SERVER_DRY_RUN=1，仅执行配置检查，不启动服务。"
  exit 0
fi

uv run python -m contextswap.platform.main
