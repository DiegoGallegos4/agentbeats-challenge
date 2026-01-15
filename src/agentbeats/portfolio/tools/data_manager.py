import os
from pathlib import Path
import json
import pandas as pd
from datetime import datetime, timedelta
from . import alpha_vantage_downloader as avd
import time

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from . import alpha_vantage_downloader as avd
import time

REPO_ROOT = Path(__file__).resolve().parents[4]
BASE_DIR = os.environ.get("AGENTBEATS_DATA_DIR", str(REPO_ROOT / "data"))

def get_dirs(date_str):
    """Returns dictionary of directory paths for a specific date."""
    date_dir = os.path.join(BASE_DIR, date_str)
    return {
        'market': os.path.join(date_dir, "market"),
        'news': os.path.join(date_dir, "news"),
        'insider': os.path.join(date_dir, "insider"),
        'options': os.path.join(date_dir, "options"),
        'analyst': os.path.join(date_dir, "analyst")
    }

def download_all_data(tickers, target_date_str):
    """
    Downloads all data for the given tickers for the target date.
    Saves to BASE_DIR/target_date_str/{data_type}/
    """
    dirs = get_dirs(target_date_str)
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
        
    print(f"Starting batch download for {len(tickers)} tickers for date {target_date_str}...")
    print(f"Saving to {os.path.join(BASE_DIR, target_date_str)}")
    
    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Downloading data for {ticker}...")
        
        # 1. Market Data (Daily)
        end_dt = datetime.strptime(target_date_str, '%Y-%m-%d')
        start_dt = end_dt - timedelta(days=730)
        market_data = avd.get_daily_data(ticker, start_dt.strftime('%Y-%m-%d'), target_date_str)
        if market_data:
            df = pd.DataFrame(market_data)
            csv_path = os.path.join(dirs['market'], f"{ticker}.csv")
            df.to_csv(csv_path, index=False)
        
        # 2. News Data
        # Fetch 7 days of news for context
        news_start = end_dt - timedelta(days=7)
        news_items = avd.get_news_for_date_range(ticker, news_start.strftime('%Y-%m-%d'), target_date_str)
        if news_items:
            json_path = os.path.join(dirs['news'], f"{ticker}.json")
            with open(json_path, 'w') as f:
                json.dump(news_items, f, indent=2)
                
        # 3. Insider Data
        insider_data = avd.get_insider_transactions(ticker)
        if insider_data:
            json_path = os.path.join(dirs['insider'], f"{ticker}.json")
            with open(json_path, 'w') as f:
                json.dump(insider_data, f, indent=2)
                
        # 4. Options Data
        options_data = avd.get_options_data(ticker, date=target_date_str)
        if options_data:
            json_path = os.path.join(dirs['options'], f"{ticker}.json")
            with open(json_path, 'w') as f:
                json.dump(options_data, f, indent=2)
                
        # 5. Analyst Data
        analyst_data = avd.get_analyst_data(ticker)
        if analyst_data:
            json_path = os.path.join(dirs['analyst'], f"{ticker}.json")
            with open(json_path, 'w') as f:
                json.dump(analyst_data, f, indent=2)
                
        # Rate Limit Sleep
        time.sleep(12) 

# --- Read Functions ---

def read_local_market_data(ticker, target_date_str):
    dirs = get_dirs(target_date_str)
    csv_path = os.path.join(dirs['market'], f"{ticker}.csv")
    if not os.path.exists(csv_path):
        return []
    
    df = pd.read_csv(csv_path)
    # Filter if needed, though file should already be scoped to target_date
    if target_date_str:
        df = df[df['date'] <= target_date_str]
        
    return df.to_dict('records')

def read_local_news(ticker, target_date_str):
    dirs = get_dirs(target_date_str)
    json_path = os.path.join(dirs['news'], f"{ticker}.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        if target_date_str:
            # Filter by time_published <= target_date_str (end of day)
            # time_published format: "20251222T153000"
            target_dt_str = target_date_str.replace("-", "") + "T235959"
            data = [item for item in data if item.get('time_published', '99999999T999999') <= target_dt_str]
            
        return data
    return []

def read_local_insider(ticker, target_date_str):
    dirs = get_dirs(target_date_str)
    json_path = os.path.join(dirs['insider'], f"{ticker}.json")
    if not os.path.exists(json_path):
        return []
        
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    if target_date_str:
        data = [d for d in data if d.get('transaction_date', '9999-99-99') <= target_date_str]
        
    return data

def read_local_options(ticker, target_date_str):
    dirs = get_dirs(target_date_str)
    json_path = os.path.join(dirs['options'], f"{ticker}.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            return json.load(f)
    return None

def read_local_analyst(ticker, target_date_str):
    dirs = get_dirs(target_date_str)
    json_path = os.path.join(dirs['analyst'], f"{ticker}.json")
    if os.path.exists(json_path):
        with open(json_path, 'r') as f:
            return json.load(f)
    return None
