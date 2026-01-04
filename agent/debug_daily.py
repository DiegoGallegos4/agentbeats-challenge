import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
ticker = 'SPY'

url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={api_key}'

print("Waiting 5 seconds...")
time.sleep(5)

print(f"Fetching {url}...")
response = requests.get(url)
print(f"Status Code: {response.status_code}")
try:
    data = response.json()
    if "Time Series (Daily)" in data:
        print(f"Data found. Keys: {list(data['Time Series (Daily)'].keys())[:3]}")
    else:
        print("Full Response:", data)
except Exception as e:
    print(f"Error parsing JSON: {e}")
    print("Raw text:", response.text)
