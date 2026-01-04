import os
import json
import pandas as pd
from datetime import datetime
from news_utils import aggregate_news_sentiment, aggregate_news_sentiment_by_topic, get_news_features

def test_aggregation():
    # Setup dummy data
    ticker = "TEST_TICKER"
    data_dir = "test_news_data"
    ticker_dir = os.path.join(data_dir, ticker)
    os.makedirs(ticker_dir, exist_ok=True)
    
    # Create dummy articles
    # Day 1: 2025-01-01
    # Article 1: 15:00 (Day 1) -> Should be Day 1
    # Article 2: 16:30 (Day 1) -> Should be Day 2
    # Article 3: 09:00 (Day 2) -> Should be Day 2
    
    articles = [
        {
            "time_published": "20250101T150000",
            "ticker_sentiment": [
                {"ticker": ticker, "relevance_score": "0.8", "ticker_sentiment_score": "0.5"}
            ]
        },
        {
            "time_published": "20250101T163000",
            "ticker_sentiment": [
                {"ticker": ticker, "relevance_score": "0.9", "ticker_sentiment_score": "0.8"}
            ]
        },
        {
            "time_published": "20250102T090000",
            "ticker_sentiment": [
                {"ticker": ticker, "relevance_score": "0.7", "ticker_sentiment_score": "-0.2"}
            ]
        },
        {
            "time_published": "20250102T100000",
            "ticker_sentiment": [
                {"ticker": ticker, "relevance_score": "0.1", "ticker_sentiment_score": "0.0"} # Low relevance
            ]
        }
    ]
    
    with open(os.path.join(ticker_dir, "dummy.json"), 'w') as f:
        json.dump(articles, f)
        
    print("Testing aggregation...")
    df = aggregate_news_sentiment(ticker, data_dir, relevance_threshold=0.5)
    
    print(df)
    
    # Verification
    # Day 1 (2025-01-01): Only Article 1 (0.5)
    # Day 2 (2025-01-02): Article 2 (0.8) + Article 3 (-0.2) = 0.6 / 2 = 0.3
    # Article 4 is excluded due to relevance < 0.5
    
    assert len(df) == 2
    assert df.loc['2025-01-01', 'article_count'] == 1
    assert df.loc['2025-01-01', 'sentiment_score'] == 0.5
    
    assert df.loc['2025-01-02', 'article_count'] == 2
    assert abs(df.loc['2025-01-02', 'sentiment_score'] - 0.3) < 0.001
    
    print("Test Passed!")
    
    # Cleanup
    import shutil
    shutil.rmtree(data_dir)

def test_topic_aggregation():
    # Setup dummy data
    ticker = "TEST_TICKER_TOPIC"
    data_dir = "test_news_data_topic"
    ticker_dir = os.path.join(data_dir, ticker)
    os.makedirs(ticker_dir, exist_ok=True)
    
    articles = [
        {
            "time_published": "20250101T150000",
            "ticker_sentiment": [{"ticker": ticker, "ticker_sentiment_score": "0.5"}],
            "topics": [
                {"topic": "Earnings", "relevance_score": "0.9"},
                {"topic": "Technology", "relevance_score": "0.4"} # Should be filtered out
            ]
        },
        {
            "time_published": "20250101T153000",
            "ticker_sentiment": [{"ticker": ticker, "ticker_sentiment_score": "0.7"}],
            "topics": [
                {"topic": "Earnings", "relevance_score": "0.8"}
            ]
        }
    ]
    
    with open(os.path.join(ticker_dir, "dummy.json"), 'w') as f:
        json.dump(articles, f)
        
    print("\nTesting topic aggregation...")
    df = aggregate_news_sentiment_by_topic(ticker, data_dir, min_topic_relevance=0.5)
    
    print(df)
    
    # Verification
    # Date: 2025-01-01
    # Topic: Earnings
    # Article 1 (0.5) + Article 2 (0.7) = 1.2 / 2 = 0.6
    
    # Topic: Technology
    # Filtered out (0.4 < 0.5)
    
    # Check index
    from datetime import date
    assert (date(2025, 1, 1), 'Earnings') in df.index
    assert (date(2025, 1, 1), 'Technology') not in df.index
    
    # Check values
    # Note: date in index is datetime.date object
    from datetime import date
    idx = (date(2025, 1, 1), 'Earnings')
    assert df.loc[idx, 'article_count'] == 2
    assert abs(df.loc[idx, 'sentiment_score'] - 0.6) < 0.001
    
    print("Topic Test Passed!")
    
    import shutil
    shutil.rmtree(data_dir)

def test_wide_format_features():
    # Setup dummy data
    ticker = "TEST_TICKER_WIDE"
    data_dir = "test_news_data_wide"
    ticker_dir = os.path.join(data_dir, ticker)
    os.makedirs(ticker_dir, exist_ok=True)
    
    articles = [
        {
            "time_published": "20250101T150000",
            "ticker_sentiment": [{"ticker": ticker, "ticker_sentiment_score": "0.5"}],
            "topics": [
                {"topic": "Earnings", "relevance_score": "0.9"}
            ]
        }
    ]
    
    with open(os.path.join(ticker_dir, "dummy.json"), 'w') as f:
        json.dump(articles, f)
        
    print("\nTesting wide-format features...")
    df = get_news_features(ticker, data_dir)
    
    print(df)
    print("Columns:", df.columns.tolist())
    
    # Verification
    assert 'all_topic.sentiment_score' in df.columns
    assert 'Earnings.sentiment_score' in df.columns
    assert 'Earnings.article_count' in df.columns
    
    # Check values
    # DataFrame index is likely DatetimeIndex (Timestamp), not date objects
    idx = pd.Timestamp("2025-01-01")
    
    assert df.loc[idx, 'all_topic.sentiment_score'] == 0.5
    assert df.loc[idx, 'Earnings.sentiment_score'] == 0.5
    assert df.loc[idx, 'Earnings.article_count'] == 1.0
    
    print("Wide Format Test Passed!")
    
    import shutil
    shutil.rmtree(data_dir)

if __name__ == "__main__":
    test_aggregation()
    test_topic_aggregation()
    test_wide_format_features()
