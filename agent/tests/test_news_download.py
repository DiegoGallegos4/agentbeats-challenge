import os
from dotenv import load_dotenv
from agent.tools.alpha_vantage_downloader import get_news_for_date_range

load_dotenv()

def test_news_download():
    ticker = 'AAPL'
    start_date = '2025-12-25'
    end_date = '2025-12-27'
    
    print(f"Testing news download for {ticker} from {start_date} to {end_date}...")
    
    try:
        news = get_news_for_date_range(ticker, start_date, end_date)
        print(f"Total articles found: {len(news)}")
        
        if news:
            print("First article title:", news[0].get('title', 'No title'))
            print("First article time:", news[0].get('time_published', 'No time'))
        
    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    test_news_download()
