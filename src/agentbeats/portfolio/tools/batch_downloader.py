import time
import calendar
import os
import random
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime, timedelta
from .alpha_vantage_downloader import (
    get_daily_data,
    get_options_data,
    get_news_sentiment,
    get_insider_transactions,
)
import json
from .sp500_utils import get_sp500_tickers

# Rate Limiter
class RateLimiter:
    def __init__(self, interval):
        self.interval = interval
        self.lock = Lock()
        self.last_call = 0

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            # Add jitter: random float between 0.01 and 0.05 seconds
            jitter = random.uniform(0.01, 0.05)
            target_interval = self.interval + jitter
            
            if elapsed < target_interval:
                time.sleep(target_interval - elapsed)
            self.last_call = time.time()

def download_all_sp500(start_date, end_date, output_dir, api_key=None):
    """
    Downloads daily data for all S&P 500 tickers and saves them as CSV files.
    Respects the API rate limit of 75 requests per minute.

    Args:
        start_date (str): Start date 'YYYY-MM-DD'.
        end_date (str): End date 'YYYY-MM-DD'.
        output_dir (str): Directory to save CSV files.
        api_key (str, optional): Alpha Vantage API key.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # get_sp500_tickers returns a DataFrame
    df_tickers = get_sp500_tickers()
    
    # Identify the column containing tickers
    if 'Symbol' in df_tickers.columns:
        tickers = df_tickers['Symbol'].tolist()
    elif 'Ticker' in df_tickers.columns:
        tickers = df_tickers['Ticker'].tolist()
    else:
        # Fallback: use the first column
        tickers = df_tickers.iloc[:, 0].tolist()

    print(f"Found {len(tickers)} tickers. Starting download...")

    for i, ticker in enumerate(tickers):
        print(f"Downloading {ticker} ({i+1}/{len(tickers)})...")
        
        try:
            data = get_daily_data(ticker, start_date, end_date, api_key)
            
            if data:
                df = pd.DataFrame(data)
                output_path = os.path.join(output_dir, f"{ticker}.parquet")
                df.to_parquet(output_path)
            else:
                print(f"No data found for {ticker}")
                
        except Exception as e:
            print(f"Failed to download {ticker}: {e}")

        # Rate limiting
        # 75 requests per minute = 1.25 requests per second
        # Sleep 0.85s to be safe (approx 1.17s per cycle including processing time)
        time.sleep(0.85)

    print("Download complete.")

def download_all_sp500_options(date=None, start_date=None, end_date=None, output_dir='options_data', api_key=None, max_workers=5):
    """
    Downloads options data for all S&P 500 tickers and saves them as Parquet files.
    Uses concurrency to maximize throughput while respecting the API rate limit.
    Saves data in 'output_dir/TICKER/YYMMDD.parquet' format.

    Args:
        date (str, optional): Specific date 'YYYY-MM-DD'.
        start_date (str, optional): Start date 'YYYY-MM-DD' for range.
        end_date (str, optional): End date 'YYYY-MM-DD' for range.
        output_dir (str): Directory to save Parquet files.
        api_key (str, optional): Alpha Vantage API key.
        max_workers (int, optional): Number of concurrent threads. Default is 5.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    df_tickers = get_sp500_tickers()
    
    if 'Symbol' in df_tickers.columns:
        tickers = df_tickers['Symbol'].tolist()
    elif 'Ticker' in df_tickers.columns:
        tickers = df_tickers['Ticker'].tolist()
    else:
        tickers = df_tickers.iloc[:, 0].tolist()

    print(f"Found {len(tickers)} tickers. Starting concurrent options download...")

    # Determine date list
    target_dates = []
    if date:
        target_dates.append(date)
    elif start_date and end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        current_dt = start_dt
        while current_dt <= end_dt:
            target_dates.append(current_dt.strftime('%Y-%m-%d'))
            current_dt += timedelta(days=1)
    else:
        print("No date or date range specified.")
        return

    # Increase base interval to 0.8s (approx 75 req/min) + jitter
    rate_limiter = RateLimiter(0.8)

    def process_ticker(ticker):
        ticker_dir = os.path.join(output_dir, ticker)
        os.makedirs(ticker_dir, exist_ok=True)

        for target_date in target_dates:
            # Format filename as YYYYMMDD.parquet
            # Parse YYYY-MM-DD to datetime object then format
            dt_obj = datetime.strptime(target_date, '%Y-%m-%d')
            filename = dt_obj.strftime('%Y%m%d') + ".parquet"
            output_path = os.path.join(ticker_dir, filename)
            
            if os.path.exists(output_path):
                print(f"File {output_path} already exists. Skipping.")
                continue

            # Wait for rate limit slot
            rate_limiter.wait()
            
            print(f"Downloading options for {ticker} on {target_date}...")
            
            try:
                # Fetch data for single date
                data = get_options_data(ticker, date=target_date, api_key=api_key)
                
                if data and isinstance(data, dict) and 'data' in data:
                    df = pd.DataFrame(data['data'])
                    df['date'] = target_date
                    df.to_parquet(output_path)
                else:
                    print(f"No options data found for {ticker} on {target_date}")
                    
            except Exception as e:
                print(f"Failed to download options for {ticker} on {target_date}: {e}")

    # Use ThreadPoolExecutor for concurrency
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_ticker, tickers)

    print("Options download complete.")

def download_all_sp500_news(start_date, end_date, output_dir, api_key=None, max_workers=10):
    """
    Downloads news sentiment data for all S&P 500 tickers and saves them as JSON files.
    Uses concurrency to maximize throughput.
    
    Args:
        start_date (str): Start date 'YYYY-MM-DD'.
        end_date (str): End date 'YYYY-MM-DD'.
        output_dir (str): Directory to save JSON files.
        api_key (str, optional): Alpha Vantage API key.
        max_workers (int, optional): Number of concurrent threads. Default is 10.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    df_tickers = get_sp500_tickers()
    
    if 'Symbol' in df_tickers.columns:
        tickers = df_tickers['Symbol'].tolist()
    elif 'Ticker' in df_tickers.columns:
        tickers = df_tickers['Ticker'].tolist()
    else:
        tickers = df_tickers.iloc[:, 0].tolist()

    print(f"Found {len(tickers)} tickers. Starting concurrent news download...")

    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    # Shared rate limiter
    rate_limiter = RateLimiter(0.8)

    def process_ticker(ticker):
        print(f"Processing {ticker}...")
        
        ticker_dir = os.path.join(output_dir, ticker)
        os.makedirs(ticker_dir, exist_ok=True)
        
        current_dt = start_dt
        while current_dt <= end_dt:
            # Determine end of this month
            last_day = calendar.monthrange(current_dt.year, current_dt.month)[1]
            month_end_dt = current_dt.replace(day=last_day)
            
            # The actual end date for this chunk is the min of month_end and global end_dt
            chunk_end_dt = min(month_end_dt, end_dt)
            
            # Filename: YYYYMM.json
            month_str = current_dt.strftime('%Y%m')
            output_path = os.path.join(ticker_dir, f"{month_str}.json")
            
            if os.path.exists(output_path):
                # Move to next month
                current_dt = month_end_dt + timedelta(days=1)
                continue

            # Format time window
            # Start from 00:00 on current_dt to 23:59 on chunk_end_dt
            time_from = current_dt.strftime('%Y%m%dT%H%M')
            time_to = chunk_end_dt.strftime('%Y%m%dT2359')
            
            # Wait for rate limit slot before making the API call
            rate_limiter.wait()
            
            try:
                # Fetch news for this chunk
                news_items = get_news_sentiment(
                    ticker=ticker, 
                    api_key=api_key, 
                    time_from=time_from, 
                    time_to=time_to,
                    limit=1000
                )
                
                if news_items:
                    with open(output_path, 'w') as f:
                        json.dump(news_items, f, indent=4)
                    print(f"  {ticker} {month_str}: Saved {len(news_items)} articles.")
                else:
                    print(f"  {ticker} {month_str}: No articles found.")
                    
            except Exception as e:
                print(f"  Failed to download news for {ticker} {month_str}: {e}")

            # Move to next month
            current_dt = month_end_dt + timedelta(days=1)

    # Use ThreadPoolExecutor for concurrency
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_ticker, tickers)

    print("News download complete.")

def download_all_sp500_insider_transactions(output_dir, api_key=None, max_workers=5):
    """
    Downloads insider transaction data for all S&P 500 tickers and saves them as Parquet files.
    Uses concurrency to maximize throughput while respecting the API rate limit.
    Saves data in 'output_dir/TICKER.parquet' format.

    Args:
        output_dir (str): Directory to save Parquet files.
        api_key (str, optional): Alpha Vantage API key.
        max_workers (int, optional): Number of concurrent threads. Default is 5.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    df_tickers = get_sp500_tickers()
    
    if 'Symbol' in df_tickers.columns:
        tickers = df_tickers['Symbol'].tolist()
    elif 'Ticker' in df_tickers.columns:
        tickers = df_tickers['Ticker'].tolist()
    else:
        tickers = df_tickers.iloc[:, 0].tolist()

    print(f"Found {len(tickers)} tickers. Starting concurrent insider transactions download...")

    # Increase base interval to 0.8s (approx 75 req/min) + jitter
    rate_limiter = RateLimiter(0.8)

    def process_ticker(ticker):
        output_path = os.path.join(output_dir, f"{ticker}.parquet")
        
        if os.path.exists(output_path):
            print(f"File {output_path} already exists. Skipping.")
            return

        # Wait for rate limit slot
        rate_limiter.wait()
        
        print(f"Downloading insider transactions for {ticker}...")
        
        try:
            data = get_insider_transactions(ticker, api_key=api_key)
            
            if data:
                df = pd.DataFrame(data)
                df.to_parquet(output_path)
            else:
                print(f"No insider transactions found for {ticker}")
                
        except Exception as e:
            print(f"Failed to download insider transactions for {ticker}: {e}")

    # Use ThreadPoolExecutor for concurrency
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(process_ticker, tickers)

    print("Insider transactions download complete.")
