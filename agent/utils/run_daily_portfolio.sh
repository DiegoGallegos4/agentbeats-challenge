#!/bin/bash

# Set up environment
export PATH="/opt/homebrew/Caskroom/miniforge/base/bin:$PATH"
export TAVILY_API_KEY="tvly-D8tv44G68H70Xg8541D2515512112" # Hardcoding for cron or source .env
# Better to source .env if possible, but for simplicity in this script:
cd /Users/raghuramkowdeed/Documents/alphavantage

# Source .env to get keys
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Get today's date
TODAY=$(date +%Y-%m-%d)

# Run the portfolio manager
/opt/homebrew/Caskroom/miniforge/base/bin/python portfolio_manager.py --date "$TODAY" --download --tickers subset >> /Users/raghuramkowdeed/Documents/alphavantage/cron_log.txt 2>&1
