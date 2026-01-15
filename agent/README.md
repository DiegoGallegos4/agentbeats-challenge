# Multi-Agent Stock Analysis & Portfolio Manager

This project implements a multi-agent system for stock analysis and portfolio management using LangGraph, Alpha Vantage data, and local storage. It employs various agents (Market, News, Insider, Options, Analyst, Web, Quantitative) to analyze stocks and generate a balanced portfolio.

## 📂 Data Directory Structure

The system relies on a specific local directory structure to store downloaded data and avoid API rate limits.

**Root Data Directory:** `/Volumes/ExtremePro/AV_data/` (Configurable in `agent/tools/data_manager.py`)

```text
/Volumes/ExtremePro/AV_data/
├── YYYY-MM-DD/              # Dated subdirectories for historical snapshots
│   ├── market/              # Daily OHLCV CSVs ({ticker}.csv)
│   ├── news/                # News sentiment JSONs ({ticker}.json)
│   ├── insider/             # Insider transaction CSVs ({ticker}.csv)
│   ├── options/             # Options chain JSONs ({ticker}.json)
│   └── analyst/             # Analyst ratings CSVs ({ticker}.csv)
└── models/                  # Trained quantitative models
    └── linear/              # Ridge regression models ({ticker}.joblib)
```

**PnL Data Directory:** `./pnl_data/` (Relative to project root)

```text
pnl_data/
├── weights/                 # Generated portfolio weights
│   └── YYYY-MM-DD.csv
└── pnl/                     # Calculated Daily PnL
    └── YYYY-MM-DD.csv
```

## 🚀 Setup

1.  **Environment Variables**: Create a `.env` file in the project root (only required for the tools you use):
    ```env
    ALPHA_VANTAGE_API_KEY=your_av_key
    OPENAI_API_KEY=your_openai_key
    TAVILY_API_KEY=your_tavily_key
    ```
    - `ALPHA_VANTAGE_API_KEY`: required for downloading market/news/options/insider data.
    - `OPENAI_API_KEY`: required for LLM-based agents (ChatOpenAI).
    - `TAVILY_API_KEY`: required for web search tooling.

2.  **Dependencies**:
    ```bash
    pip install pandas numpy langchain langgraph langchain-openai alpha_vantage ta joblib beautifulsoup4 tavily-python python-dotenv
    ```

## 🛠 Usage

### 1. Download Data
Always download data first for the target date to ensure local availability.
```bash
# Download for specific tickers
python -m agent.purple.portfolio_manager --date 2025-12-22 --download --tickers AAPL,MSFT,TSLA

# Download for a predefined subset
python -m agent.purple.portfolio_manager --date 2025-12-22 --download --tickers subset

# Download for all S&P 500 (Warning: Takes time)
python -m agent.purple.portfolio_manager --date 2025-12-22 --download --tickers all
```

### 2. Run Analysis
Runs the multi-agent system on the downloaded data to generate portfolio weights.
```bash
python -m agent.purple.portfolio_manager --date 2025-12-22 --tickers subset
```
*Output:* Saves weights to `pnl_data/weights/2025-12-22.csv`.

### 3. Calculate PnL (Profit and Loss)
To calculate PnL, you need weights from a previous date and market data for the current date.

**Full Run (Analysis + PnL):**
```bash
python -m agent.purple.portfolio_manager --date 2025-12-22 --tickers subset
python -m agent.green.portfolio_evaluator --date 2025-12-22 --pnl_date 2025-12-23
```

**PnL Only (Skip Analysis):**
Useful if you already ran the analysis and just want to compute returns.
*Prerequisite:* Data must be downloaded for **both** dates.
```bash
python -m agent.green.portfolio_evaluator --date 2025-12-22 --pnl_date 2025-12-23
```

### 4. Automated Daily Run (Cron)
Use the provided shell script `agent/utils/run_daily_portfolio.sh` to run the job daily with the current date.

**Crontab Entry (Mon-Fri at 16:00):**
```cron
0 16 * * 1-5 /Users/raghuramkowdeed/Documents/alphavantage/agent/utils/run_daily_portfolio.sh
```

## 🧩 Architecture

*   **`agent/purple/portfolio_manager.py`**: Main entry point. Handles arguments, orchestration, and PnL tracking.
*   **`agent/tools/data_manager.py`**: Centralized handler for reading/writing local data in dated directories.
*   **`agent/purple/graph.py`**: Defines the LangGraph workflow and agent nodes.
*   **`agent/purple/agents.py`**: Defines the system prompts and configuration for each agent.
*   **`agent/tools/tools.py`**: LangChain tools used by agents (Market Data, Tavily Search, Website Scraper, etc.).
*   **`agent/purple/realtime_prediction.py`**: Quantitative agent's logic for feature engineering and model prediction.
*   **`agent/green/pnl_tracker.py`**: Calculates portfolio PnL from saved weights.
*   **`agent/green/portfolio_evaluator.py`**: Minimal CLI wrapper that evaluates PnL from saved weights.
