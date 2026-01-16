#!/usr/bin/env bash
set -euo pipefail

if [[ -f ".env" ]]; then
  set -a
  . ./.env
  set +a
fi

DATE=""
PNL_DATE=""
TICKERS="subset"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --date)
      DATE="$2"
      shift 2
      ;;
    --pnl-date)
      PNL_DATE="$2"
      shift 2
      ;;
    --tickers)
      TICKERS="$2"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
 done

if [[ -z "$DATE" ]]; then
  echo "Usage: $0 --date YYYY-MM-DD [--pnl-date YYYY-MM-DD] [--tickers subset|all|T1,T2]" >&2
  exit 1
fi

mkdir -p data

DATE="$DATE" TICKERS="$TICKERS" python - <<'PY'
import os
from pathlib import Path

from agent.tools import data_manager as dm
from agent.tools.sp500_utils import get_sp500_tickers

date = os.environ["DATE"]
tickers_arg = os.environ.get("TICKERS", "subset")

if tickers_arg == "all":
    tickers = get_sp500_tickers()
elif tickers_arg == "subset":
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
else:
    tickers = [t.strip() for t in tickers_arg.split(",") if t.strip()]

base_dir = Path(os.environ.get("AGENTBEATS_DATA_DIR", Path.cwd() / "data"))
missing = []
for ticker in tickers:
    market_path = base_dir / date / "market" / f"{ticker}.csv"
    if not market_path.exists():
        missing.append(ticker)

if missing:
    dm.download_all_data(missing, date)
else:
    print(f"Data already present for {len(tickers)} tickers on {date}, skipping download.")
PY

if [[ -n "$PNL_DATE" ]]; then
  DATE="$PNL_DATE" TICKERS="$TICKERS" python - <<'PY'
import os
from pathlib import Path

from agent.tools import data_manager as dm
from agent.tools.sp500_utils import get_sp500_tickers

date = os.environ["DATE"]
tickers_arg = os.environ.get("TICKERS", "subset")

if tickers_arg == "all":
    tickers = get_sp500_tickers()
elif tickers_arg == "subset":
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
else:
    tickers = [t.strip() for t in tickers_arg.split(",") if t.strip()]

base_dir = Path(os.environ.get("AGENTBEATS_DATA_DIR", Path.cwd() / "data"))
missing = []
for ticker in tickers:
    market_path = base_dir / date / "market" / f"{ticker}.csv"
    if not market_path.exists():
        missing.append(ticker)

if missing:
    dm.download_all_data(missing, date)
else:
    print(f"Data already present for {len(tickers)} tickers on {date}, skipping download.")
PY
fi
