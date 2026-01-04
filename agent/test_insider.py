import os
from dotenv import load_dotenv
from alpha_vantage_downloader import get_insider_transactions
import json

load_dotenv()

def test_insider_transactions():
    ticker = 'IBM'
    print(f"Fetching insider transactions for {ticker}...")
    data = get_insider_transactions(ticker)
    
    if data:
        print(f"Successfully fetched {len(data)} transactions.")
        print("First transaction sample:")
        print(json.dumps(data[0], indent=2))
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    test_insider_transactions()
