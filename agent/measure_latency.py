import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
ticker = 'SPY'
date = '2025-12-23' # Use a recent date, or one likely to have data

url = f'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={ticker}&date={date}&apikey={api_key}'

print(f"Testing latency for {url}...")
start_time = time.time()
try:
    response = requests.get(url)
    end_time = time.time()
    print(f"Status Code: {response.status_code}")
    print(f"Latency: {end_time - start_time:.4f} seconds")
except Exception as e:
    print(f"Error: {e}")
