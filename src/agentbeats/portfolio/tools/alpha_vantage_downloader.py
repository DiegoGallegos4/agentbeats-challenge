import requests
import time
import os
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()


def get_daily_data(ticker, start_date, end_date, api_key=None):
    """
    Downloads daily time series data from Alpha Vantage for a given ticker
    and filters it by a start and end date.

    Args:
        ticker (str): The stock ticker symbol (e.g., 'IBM').
        start_date (str): The start date in 'YYYY-MM-DD' format.
        end_date (str): The end date in 'YYYY-MM-DD' format.
        api_key (str, optional): Alpha Vantage API key. If not provided,
                                 it looks for 'ALPHA_VANTAGE_API_KEY' env var.

    Returns:
        list: A list of dictionaries containing daily data within the date range.
              Each dictionary has keys: 'date', 'open', 'high', 'low', 'close', 'volume'.
              Returns an empty list if no data is found or an error occurs.
    """
    if not api_key:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    
    if not api_key:
        raise ValueError("API key must be provided or set in ALPHA_VANTAGE_API_KEY environment variable.")

    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={api_key}&outputsize=full'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "Time Series (Daily)" not in data:
            print(f"Error fetching data: {data.get('Note', data.get('Information', 'Unknown error'))}")
            return []

        time_series = data["Time Series (Daily)"]
        filtered_data = []
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # Sort dates to ensure chronological order if needed, though API usually returns reverse chronological
        # We'll iterate through all and filter
        
        for date_str, daily_values in time_series.items():
            date_dt = datetime.strptime(date_str, '%Y-%m-%d')
            
            if start_dt <= date_dt <= end_dt:
                filtered_data.append({
                    'date': date_str,
                    'open': float(daily_values['1. open']),
                    'high': float(daily_values['2. high']),
                    'low': float(daily_values['3. low']),
                    'close': float(daily_values['4. close']),
                    'volume': int(daily_values['5. volume'])
                })
        
        # Sort by date ascending
        filtered_data.sort(key=lambda x: x['date'])
        
        return filtered_data

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return []
    except ValueError as e:
        print(f"Value Error: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

def get_analyst_data(ticker, api_key=None):
    """
    Fetches analyst ratings and target price for a given ticker from Alpha Vantage.

    Args:
        ticker (str): The stock ticker symbol.
        api_key (str, optional): Alpha Vantage API key.

    Returns:
        dict: A dictionary containing analyst data.
              Returns None if an error occurs or data is missing.
    """
    if not api_key:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    
    if not api_key:
        raise ValueError("API key must be provided or set in ALPHA_VANTAGE_API_KEY environment variable.")

    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print(f"No data found for {ticker}")
            return None
            
        # Extract relevant fields
        analyst_data = {
            'Symbol': data.get('Symbol'),
            'AnalystTargetPrice': data.get('AnalystTargetPrice'),
            'AnalystRatingStrongBuy': data.get('AnalystRatingStrongBuy'),
            'AnalystRatingBuy': data.get('AnalystRatingBuy'),
            'AnalystRatingHold': data.get('AnalystRatingHold'),
            'AnalystRatingSell': data.get('AnalystRatingSell'),
            'AnalystRatingStrongSell': data.get('AnalystRatingStrongSell'),
        }
        
        return analyst_data

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_earnings_data(ticker, api_key=None):
    """
    Fetches annual and quarterly earnings (EPS) for a given ticker from Alpha Vantage.

    Args:
        ticker (str): The stock ticker symbol.
        api_key (str, optional): Alpha Vantage API key.

    Returns:
        dict: A dictionary containing 'annualEarnings' and 'quarterlyEarnings'.
              Returns None if an error occurs or data is missing.
    """
    if not api_key:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    
    if not api_key:
        raise ValueError("API key must be provided or set in ALPHA_VANTAGE_API_KEY environment variable.")

    url = f'https://www.alphavantage.co/query?function=EARNINGS&symbol={ticker}&apikey={api_key}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if not data or "annualEarnings" not in data:
            print(f"No earnings data found for {ticker}")
            return None
            
        return {
            'symbol': data.get('symbol'),
            'annualEarnings': data.get('annualEarnings', []),
            'quarterlyEarnings': data.get('quarterlyEarnings', [])
        }

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_news_sentiment(ticker=None, api_key=None, limit=50, time_from=None, time_to=None):
    """
    Fetches news and sentiment data from Alpha Vantage.

    Args:
        ticker (str, optional): The stock ticker symbol.
        api_key (str, optional): Alpha Vantage API key.
        limit (int, optional): Number of results to return. Default is 50.
        time_from (str, optional): Start time in 'YYYYMMDDTHHMM' format.
        time_to (str, optional): End time in 'YYYYMMDDTHHMM' format.

    Returns:
        list: A list of dictionaries containing news articles and sentiment data.
              Returns None if an error occurs.
    """
    if not api_key:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    
    if not api_key:
        raise ValueError("API key must be provided or set in ALPHA_VANTAGE_API_KEY environment variable.")

    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&apikey={api_key}&limit={limit}'
    
    if ticker:
        url += f'&tickers={ticker}'
    if time_from:
        url += f'&time_from={time_from}'
    if time_to:
        url += f'&time_to={time_to}'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "feed" not in data:
            print(f"No news data found for {ticker}")
            return None
            
        return data['feed']

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_options_data(ticker, date=None, start_date=None, end_date=None, api_key=None):
    """
    Fetches historical options data for a given ticker from Alpha Vantage.
    Supports fetching for a single date or a range of dates.

    Args:
        ticker (str): The stock ticker symbol.
        date (str, optional): A specific date (YYYY-MM-DD).
        start_date (str, optional): Start date for a range (YYYY-MM-DD).
        end_date (str, optional): End date for a range (YYYY-MM-DD).
        api_key (str, optional): Alpha Vantage API key.

    Returns:
        dict or list: A dictionary if a single date is requested.
                      A list of dictionaries if a date range is requested.
                      Returns None if an error occurs.
    """
    if not api_key:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    
    if not api_key:
        raise ValueError("API key must be provided or set in ALPHA_VANTAGE_API_KEY environment variable.")

    # Helper function to fetch for a single date
    def fetch_single_date(target_date, retries=3):
        url = f'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={ticker}&apikey={api_key}'
        if target_date:
            url += f'&date={target_date}'
        
        for attempt in range(retries):
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                
                # Check for rate limit message
                if "Information" in data:
                    info_msg = data["Information"]
                    if "Minute-level rate limit exceed" in info_msg:
                        print(f"Minute-level rate limit hit for {target_date}. Retrying in 65 seconds... (Attempt {attempt + 1}/{retries})")
                        time.sleep(65)
                        continue
                    if "Burst pattern detected" in info_msg:
                        print(f"Burst rate limit hit for {target_date}. Retrying in 10 seconds... (Attempt {attempt + 1}/{retries})")
                        time.sleep(10)
                        continue

                if "data" not in data:
                    print(f"No options data found for {ticker} on {target_date}. Response: {data}")
                    return None
                return data
            except Exception as e:
                print(f"Error fetching options for {ticker} on {target_date}: {e}")
                return None
        
        print(f"Failed to fetch data for {target_date} after {retries} attempts due to rate limiting.")
        return None

    # Handle date range
    if start_date and end_date:
        results = []
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y-%m-%d')
            print(f"Fetching options data for {date_str}...")
            data = fetch_single_date(date_str)
            if data:
                # Add date to the data for reference if not present
                if 'date' not in data:
                    data['date'] = date_str
                results.append(data)
            current_dt += timedelta(days=1)
            time.sleep(1) # Be nice to the API
        return results

    # Handle single date (explicit or default)
    return fetch_single_date(date)

def get_news_for_date_range(ticker, start_date, end_date, api_key=None, sleep=1):
    """
    Fetches news sentiment data for a given ticker over a date range.
    Iterates day-by-day to maximize data retrieval.

    Args:
        ticker (str): The stock ticker symbol.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        api_key (str, optional): Alpha Vantage API key.

    Returns:
        list: A list of all news items found within the range.
    """
    if not api_key:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    
    if not api_key:
        raise ValueError("API key must be provided or set in ALPHA_VANTAGE_API_KEY environment variable.")

    all_news = []
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    current_dt = start_dt
    while current_dt <= end_dt:
        date_str = current_dt.strftime('%Y%m%d')
        time_from = f"{date_str}T0000"
        time_to = f"{date_str}T2359"
        
        print(f"Fetching news for {ticker} on {current_dt.strftime('%Y-%m-%d')}...")
        
        # Reuse existing get_news_sentiment function
        # Note: get_news_sentiment returns a list of dicts (the 'feed') or None
        try:
            news_items = get_news_sentiment(
                ticker=ticker,
                api_key=api_key,
                time_from=time_from,
                time_to=time_to,
                limit=1000  # Try to get max per day
            )
        except Exception as exc:
            print(f"  News fetch failed for {ticker} on {current_dt.strftime('%Y-%m-%d')}: {exc}")
            news_items = None
        
        if news_items:
            print(f"  Found {len(news_items)} articles.")
            all_news.extend(news_items)
        else:
            print("  No articles found or error.")
            
        current_dt += timedelta(days=1)
        time.sleep(sleep) # Be nice to the API
        
    return all_news

def get_insider_transactions(ticker, api_key=None):
    """
    Fetches insider transaction data for a given ticker from Alpha Vantage.

    Args:
        ticker (str): The stock ticker symbol.
        api_key (str, optional): Alpha Vantage API key.

    Returns:
        list: A list of dictionaries containing insider transaction data.
              Returns None if an error occurs.
    """
    if not api_key:
        api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    
    if not api_key:
        raise ValueError("API key must be provided or set in ALPHA_VANTAGE_API_KEY environment variable.")

    url = f'https://www.alphavantage.co/query?function=INSIDER_TRANSACTIONS&symbol={ticker}&apikey={api_key}'
    
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Check for rate limit message
            if "Information" in data:
                info_msg = data["Information"]
                if "Minute-level rate limit exceed" in info_msg:
                    print(f"Minute-level rate limit hit for {ticker}. Retrying in 65 seconds... (Attempt {attempt + 1}/{retries})")
                    time.sleep(65)
                    continue
                if "Burst pattern detected" in info_msg:
                    print(f"Burst rate limit hit for {ticker}. Retrying in 10 seconds... (Attempt {attempt + 1}/{retries})")
                    time.sleep(10)
                    continue
            
            if "insider_transactions" in data:
                return data['insider_transactions']
            elif "data" in data:
                return data['data']
            
            print(f"No insider transactions found for {ticker}. Response keys: {list(data.keys())}")
            if "Note" in data:
                print(f"API Note: {data['Note']}")
            return None

        except requests.exceptions.RequestException as e:
            print(f"HTTP Request failed: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None
            
    print(f"Failed to fetch insider transactions for {ticker} after {retries} attempts.")
    return None
