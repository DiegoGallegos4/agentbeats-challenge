import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
ticker = 'SPY'
date = '2025-12-23'

url = f'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={ticker}&date={date}&apikey={api_key}'

print("Waiting 65 seconds to clear rate limit...")
time.sleep(65)

print(f"Fetching {url}...")
response = requests.get(url)
print(f"Status Code: {response.status_code}")
try:
    data = response.json()
    if "data" in data:
        print(f"Data count: {len(data['data'])}")
        print("First item:", data['data'][0] if data['data'] else "Empty list")
    else:
        print("Full Response:", data)
except Exception as e:
    print(f"Error parsing JSON: {e}")
    print("Raw text:", response.text)
