import os
import shutil
from unittest.mock import patch, MagicMock
from agent.tools.batch_downloader import download_all_sp500_news
import pandas as pd

def test_batch_news_download():
    output_dir = 'test_news_data'
    
    # Clean up previous test run
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        
    print("Testing batch news download...")
    
    # Mock get_sp500_tickers to return a small subset
    mock_tickers = pd.DataFrame({'Symbol': ['AAPL', 'MSFT']})
    
    with patch('agent.tools.batch_downloader.get_sp500_tickers', return_value=mock_tickers):
        download_all_sp500_news(
            start_date='2025-12-25',
            end_date='2025-12-26',
            output_dir=output_dir
        )
        
    # Verify files exist
    expected_files = {
        'AAPL': ['202512.json'],
        'MSFT': ['202512.json']
    }
    
    for ticker, filenames in expected_files.items():
        ticker_dir = os.path.join(output_dir, ticker)
        if not os.path.exists(ticker_dir):
            print(f"Error: Directory {ticker_dir} not found.")
            continue
            
        for filename in filenames:
            path = os.path.join(ticker_dir, filename)
            if os.path.exists(path):
                print(f"Verified {ticker}/{filename} exists.")
            else:
                print(f"Error: {ticker}/{filename} not found.")

if __name__ == "__main__":
    test_batch_news_download()
