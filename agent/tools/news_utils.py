import os
import json
import pandas as pd
from datetime import datetime, timedelta
import glob

def aggregate_news_sentiment(ticker, data_dir, relevance_threshold=0.0):
    """
    Aggregates news sentiment data for a specific ticker.
    
    Filters articles by relevance score and groups them by "Trading Day".
    A Trading Day is defined as the period from the previous day's 16:00:01 
    to the current day's 16:00:00.
    
    Args:
        ticker (str): Ticker symbol.
        data_dir (str): Root directory containing news data (e.g., 'sp500_news').
                        Expects structure: data_dir/TICKER/*.json
        relevance_threshold (float): Minimum relevance score to include an article.
        
    Returns:
        pd.DataFrame: DataFrame indexed by 'date' with columns ['sentiment_score', 'article_count'].
    """
    ticker_dir = os.path.join(data_dir, ticker)
    if not os.path.exists(ticker_dir):
        print(f"Directory not found: {ticker_dir}")
        return pd.DataFrame()
    
    # Find all JSON files for the ticker
    json_files = glob.glob(os.path.join(ticker_dir, "*.json"))
    
    all_articles = []
    
    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_articles.extend(data)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
            
    if not all_articles:
        return pd.DataFrame()
        
    processed_data = []
    
    for article in all_articles:
        # Check relevance for the specific ticker
        ticker_relevance = 0.0
        ticker_sentiment = 0.0
        
        # Parse ticker_sentiment list
        # "ticker_sentiment": [
        #     {"ticker": "AAPL", "relevance_score": "0.1", "ticker_sentiment_score": "0.1", ...}
        # ]
        if 'ticker_sentiment' in article:
            for item in article['ticker_sentiment']:
                if item.get('ticker') == ticker:
                    try:
                        ticker_relevance = float(item.get('relevance_score', 0))
                        ticker_sentiment = float(item.get('ticker_sentiment_score', 0))
                    except ValueError:
                        continue
                    break
        
        # Filter by relevance
        if ticker_relevance < relevance_threshold:
            continue
            
        # Parse time_published
        # Format: "20250102T133000"
        time_str = article.get('time_published')
        if not time_str:
            continue
            
        try:
            dt = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
        except ValueError:
            continue
            
        # Determine Trading Date
        # If time > 16:00:00, it belongs to the NEXT day
        if dt.time() > datetime.strptime("160000", "%H%M%S").time():
            trading_date = (dt + timedelta(days=1)).date()
        else:
            trading_date = dt.date()
            
        processed_data.append({
            'date': trading_date,
            'sentiment_score': ticker_sentiment,
            'relevance_score': ticker_relevance
        })
        
    if not processed_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(processed_data)
    
    # Group by date
    agg_df = df.groupby('date').agg({
        'sentiment_score': 'mean',
        'relevance_score': 'count' # Count of articles
    }).rename(columns={'relevance_score': 'article_count'})
    
    agg_df.index = pd.to_datetime(agg_df.index)
    agg_df = agg_df.sort_index()
    
    return agg_df

def aggregate_news_sentiment_by_topic(ticker, data_dir, min_topic_relevance=0.5):
    """
    Aggregates news sentiment data by TOPIC for a specific ticker.
    
    Groups by "Trading Day" and "Topic".
    
    Args:
        ticker (str): Ticker symbol.
        data_dir (str): Root directory containing news data.
        min_topic_relevance (float): Minimum relevance score for a topic to be included.
        
    Returns:
        pd.DataFrame: DataFrame indexed by ['date', 'topic'] with columns ['sentiment_score', 'article_count'].
    """
    ticker_dir = os.path.join(data_dir, ticker)
    if not os.path.exists(ticker_dir):
        print(f"Directory not found: {ticker_dir}")
        return pd.DataFrame()
    
    # Find all JSON files for the ticker
    json_files = glob.glob(os.path.join(ticker_dir, "*.json"))
    
    all_articles = []
    
    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_articles.extend(data)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue
            
    if not all_articles:
        return pd.DataFrame()
        
    processed_data = []
    
    for article in all_articles:
        # Parse time_published
        time_str = article.get('time_published')
        if not time_str:
            continue
            
        try:
            dt = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
        except ValueError:
            continue
            
        # Determine Trading Date
        if dt.time() > datetime.strptime("160000", "%H%M%S").time():
            trading_date = (dt + timedelta(days=1)).date()
        else:
            trading_date = dt.date()
            
        # Get ticker sentiment for THIS ticker
        ticker_sentiment = 0.0
        found_ticker = False
        if 'ticker_sentiment' in article:
            for item in article['ticker_sentiment']:
                if item.get('ticker') == ticker:
                    try:
                        ticker_sentiment = float(item.get('ticker_sentiment_score', 0))
                        found_ticker = True
                    except ValueError:
                        continue
                    break
        
        if not found_ticker:
            continue
            
        # Process Topics
        # "topics": [
        #    {"topic": "Earnings", "relevance_score": "0.9"}, ...
        # ]
        if 'topics' in article:
            for topic_item in article['topics']:
                topic_name = topic_item.get('topic')
                try:
                    topic_relevance = float(topic_item.get('relevance_score', 0))
                except ValueError:
                    continue
                    
                if topic_relevance >= min_topic_relevance:
                    processed_data.append({
                        'date': trading_date,
                        'topic': topic_name,
                        'sentiment_score': ticker_sentiment,
                        'count': 1
                    })
        
    if not processed_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(processed_data)
    
    # Group by date and topic
    agg_df = df.groupby(['date', 'topic']).agg({
        'sentiment_score': 'mean',
        'count': 'sum' # Count of articles per topic
    }).rename(columns={'count': 'article_count'})
    
    # Sort index
    agg_df = agg_df.sort_index()
    
    return agg_df

def get_news_features(ticker, data_dir, relevance_threshold=0.0, min_topic_relevance=0.5):
    """
    Generates wide-format news features for a ticker.
    
    Combines overall sentiment and topic-specific sentiment into a single DataFrame.
    
    Columns:
        - all_topic.sentiment_score
        - all_topic.article_count
        - {Topic}.sentiment_score
        - {Topic}.article_count
        
    Args:
        ticker (str): Ticker symbol.
        data_dir (str): Root directory containing news data.
        relevance_threshold (float): Threshold for overall sentiment.
        min_topic_relevance (float): Threshold for topic sentiment.
        
    Returns:
        pd.DataFrame: Wide-format DataFrame indexed by date.
    """
    # 1. Get Overall Sentiment
    df_all = aggregate_news_sentiment(ticker, data_dir, relevance_threshold)
    
    if df_all.empty:
        return pd.DataFrame()
        
    # Rename columns
    df_all = df_all.rename(columns={
        'sentiment_score': 'all_topic.sentiment_score',
        'article_count': 'all_topic.article_count'
    })
    
    # 2. Get Topic Sentiment
    df_topics = aggregate_news_sentiment_by_topic(ticker, data_dir, min_topic_relevance)
    
    if df_topics.empty:
        return df_all
        
    # 3. Pivot Topic Data
    # Reset index to move 'topic' to columns
    df_topics_flat = df_topics.reset_index()
    
    # Pivot
    df_pivot = df_topics_flat.pivot(index='date', columns='topic', values=['sentiment_score', 'article_count'])
    
    # Flatten MultiIndex columns
    # Current columns: ('sentiment_score', 'Earnings'), ('article_count', 'Earnings'), ...
    # Desired: 'Earnings.sentiment_score', 'Earnings.article_count'
    
    new_columns = []
    for col in df_pivot.columns:
        metric, topic = col
        new_columns.append(f"{topic}.{metric}")
        
    df_pivot.columns = new_columns
    
    # 4. Merge
    # Use outer join to keep all dates, though usually they should align if data exists
    final_df = df_all.join(df_pivot, how='outer')
    
    # Fill NaNs?
    # For sentiment_score, NaN means no news for that topic. 
    # Leaving as NaN is probably best for ML models (can be handled or imputed later).
    # For article_count, NaN implies 0.
    
    # Let's fill article_count NaNs with 0
    count_cols = [c for c in final_df.columns if 'article_count' in c]
    final_df[count_cols] = final_df[count_cols].fillna(0)
    
    return final_df
