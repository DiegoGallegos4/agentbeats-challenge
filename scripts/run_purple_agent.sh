#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: $0 --date YYYY-MM-DD [--tickers subset|all|T1,T2] [--download]"
  exit 1
fi

python -m agent.purple.portfolio_manager "$@"
