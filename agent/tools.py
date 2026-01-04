import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
import requests
from bs4 import BeautifulSoup

# Import local modules
import alpha_vantage_downloader as avd
from realtime_prediction import predict_realtime

import data_manager as dm

@tool
def get_model_prediction(ticker: str, target_date: str = None) -> str:
    """
    Runs the pre-trained Ridge regression model to predict the stock's return for a specific date.
    target_date format: YYYY-MM-DD. Defaults to today if not provided.
    """
    try:
        if not target_date:
            target_date = datetime.now().strftime('%Y-%m-%d')
            
        # Note: predict_realtime still calls API internally. 
        # We need to update it or make it use local data.
        # For now, let's assume predict_realtime is updated or we pass a flag.
        # Actually, let's update predict_realtime separately.
        prediction = predict_realtime(ticker, target_date)
        return f"Predicted Return for {ticker} on {target_date}: {prediction:.6f}"
    except Exception as e:
        return f"Error running prediction for {ticker}: {e}"

@tool
def get_market_data(ticker: str, target_date: str = None) -> str:
    """
    Fetches daily market data (OHLCV) for a given ticker up to a specific date.
    Reads from local storage.
    """
    if not target_date:
        target_date = datetime.now().strftime('%Y-%m-%d')
        
    data = dm.read_local_market_data(ticker, target_date)
    
    if not data:
        return f"No market data found for {ticker} (Local)."
        
    # Return latest 5 days relative to target_date
    # Data is already sorted by date ascending in data_manager (if saved that way)
    # Let's ensure sort
    data.sort(key=lambda x: x['date'])
    latest_data = data[-5:]
    
    summary = f"Market Data for {ticker} (Last 5 days ending {target_date}):\n"
    for day in latest_data:
        summary += f"{day['date']}: Close={day['close']}, Volume={day['volume']}\n"
    
    # Add simple trend
    if len(data) > 0:
        start_price = data[0]['close']
        end_price = data[-1]['close']
        trend = "UP" if end_price > start_price else "DOWN"
        summary += f"Trend ({len(data)} days): {trend} ({start_price} -> {end_price})"
    
    return summary

@tool
def get_options_data(ticker: str, target_date: str = None) -> str:
    """
    Fetches options data for a ticker on a specific date from local storage.
    """
    if not target_date:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    data = dm.read_local_options(ticker, target_date)
        
    if not data:
        return f"No options data found for {ticker} on {target_date} (Local)."
        
    return f"Options data for {ticker} on {target_date}: {str(data)[:500]}..."

@tool
def get_insider_data(ticker: str, target_date: str = None) -> str:
    """
    Fetches insider transactions for a ticker up to a specific date from local storage.
    """
    data = dm.read_local_insider(ticker, target_date)
    if not data:
        return f"No insider data found for {ticker} (Local)."
    
    # Summarize last 5 transactions
    latest = data[:5]
    summary = f"Recent Insider Transactions for {ticker} (up to {target_date}):\n"
    for txn in latest:
        date = txn.get('transaction_date', 'N/A')
        name = txn.get('insider_name', 'N/A')
        shares = txn.get('shares', 0)
        txn_type = txn.get('acquisition_or_disposal', 'N/A')
        summary += f"{date}: {name} {txn_type} {shares} shares\n"
        
    return summary

@tool
def get_news_data(ticker: str, target_date: str = None) -> str:
    """
    Fetches news sentiment for a ticker leading up to a specific date from local storage.
    """
    if not target_date:
        target_date = datetime.now().strftime('%Y-%m-%d')
        
    data = dm.read_local_news(ticker, target_date)
    if not data:
        return f"No news found for {ticker} (Local)."
        
    summary = f"Recent News for {ticker} (around {target_date}):\n"
    for item in data:
        title = item.get('title', 'No Title')
        score = item.get('overall_sentiment_score', 0)
        summary += f"- {title} (Sentiment: {score})\n"
        
    return summary

@tool
def get_analyst_data(ticker: str, target_date: str = None) -> str:
    """
    Fetches analyst ratings from local storage.
    """
    if not target_date:
        target_date = datetime.now().strftime('%Y-%m-%d')
        
    data = dm.read_local_analyst(ticker, target_date)
    if not data:
        return f"No analyst data found for {ticker} (Local)."
        
    return f"Analyst Data for {ticker}: {data}"

from tavily import TavilyClient

@tool
def web_search(query: str) -> str:
    """
    Performs a web search using Tavily.
    """
    try:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return "Error: TAVILY_API_KEY not found in environment variables."
            
        tavily = TavilyClient(api_key=api_key)
        response = tavily.search(query=query, search_depth="advanced", max_results=5)
        
        # Tavily returns a dict with 'results' list
        results = response.get('results', [])
        if not results:
            return "No results found."
        
        summary = ""
        for r in results:
            summary += f"Title: {r['title']}\nLink: {r['url']}\nSnippet: {r['content']}\n\n"
        
        return summary
    except Exception as e:
        return f"Error performing web search: {e}"

@tool
def scrape_website(url: str) -> str:
    """
    Scrapes text content from a website URL.
    Useful for reading company IR pages.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text
        text = soup.get_text(separator=' ', strip=True)
        return text[:2000] + "..." # Truncate to avoid context limit
    except Exception as e:
        return f"Error scraping {url}: {e}"
