import os
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
import tempfile
import shutil
from ta import add_all_ta_features
from ta.utils import dropna

# Import local modules
from ..tools import data_manager as dm
from ..tools.news_utils import aggregate_news_sentiment
from ..tools.insider_utils import get_rolling_insider_sentiment

def fetch_and_prepare_data(ticker, target_date_str, api_key=None):
    """
    Fetches necessary data (market, news, insider) and prepares it for feature engineering.
    Reads from local storage via data_manager.
    """
    print(f"Fetching data for {ticker} up to {target_date_str} (Local)...")
    
    # 1. Fetch Market Data
    market_data = dm.read_local_market_data(ticker, target_date_str)
    if not market_data:
        raise ValueError(f"Could not fetch market data for {ticker} (Local)")
        
    df_market = pd.DataFrame(market_data)
    df_market['date'] = pd.to_datetime(df_market['date'])
    df_market = df_market.set_index('date').sort_index()
    
    # 2. Fetch News Data
    news_items = dm.read_local_news(ticker, target_date_str)
    
    # 3. Fetch Insider Data
    insider_data = dm.read_local_insider(ticker, target_date_str)
    
    return {
        'market': df_market,
        'news': news_items,
        'insider': insider_data
    }

def build_features(ticker, data_dict, temp_dir):
    """
    Constructs the feature vector X for the model.
    
    Args:
        ticker (str): Stock ticker.
        data_dict (dict): Data fetched from fetch_and_prepare_data.
        temp_dir (str): Path to a temporary directory for intermediate file storage.
        
    Returns:
        pd.DataFrame: DataFrame containing features, indexed by date.
    """
    print("Building features...")
    
    df = data_dict['market'].copy()
    df = dropna(df)
    
    # 1. Technical Indicators
    # Ensure columns are float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
        
    ta_df = add_all_ta_features(
        df, open="open", high="high", low="low", close="close", volume="volume", fillna=True
    )
    
    # 2. News Sentiment
    # Save news to temp dir structure expected by aggregate_news_sentiment
    # Structure: temp_dir/news_data/TICKER/news.json
    news_dir = os.path.join(temp_dir, 'news_data')
    ticker_news_dir = os.path.join(news_dir, ticker)
    os.makedirs(ticker_news_dir, exist_ok=True)
    
    import json
    if data_dict['news']:
        with open(os.path.join(ticker_news_dir, 'news.json'), 'w') as f:
            json.dump(data_dict['news'], f)
            
    news_df = aggregate_news_sentiment(ticker=ticker, data_dir=news_dir, relevance_threshold=0.5)
    
    # 3. Insider Sentiment
    # Save insider data to temp dir structure expected by get_rolling_insider_sentiment
    # Structure: temp_dir/insider_data/TICKER.parquet
    insider_dir = os.path.join(temp_dir, 'insider_data')
    os.makedirs(insider_dir, exist_ok=True)
    
    if data_dict['insider']:
        df_insider = pd.DataFrame(data_dict['insider'])
        # Rename columns to match what insider_utils expects if needed
        # The downloader returns raw API keys, utils might expect specific names
        # Based on insider_utils.py, it handles 'transaction_date' or 'transactionDate'
        # API usually returns 'transaction_date'
        df_insider.to_parquet(os.path.join(insider_dir, f'{ticker}.parquet'))
        
    insider_df = get_rolling_insider_sentiment(ticker=ticker, data_dir=insider_dir, window_days=10)
    insider_df = insider_df.shift(1) # Shift as per training logic
    
    # 4. Merge Features (Logic from technical_indicators.ipynb)
    # ta_df = ta_df.reindex(news_df['sentiment_score'].index) # This line in notebook filters to news dates?
    # Actually, in the notebook:
    # ta_df = ta_df.reindex( news_df['sentiment_score'].index)
    # ta_df['sentiment_score'] = news_df['sentiment_score']
    # This implies we only predict on days we have news? Or is it just aligning?
    # Let's align to the market data index (ta_df) and join others.
    
    # Note: The notebook logic seems to prioritize news index. 
    # "ta_df = ta_df.reindex( news_df['sentiment_score'].index)"
    # If we want to predict for "today", we must ensure "today" is in the index.
    
    # Let's use left join on market data to keep all trading days
    ta_df['sentiment_score'] = news_df['sentiment_score'].reindex(ta_df.index)
    
    # Insider
    ta_df['insider_sentiment'] = insider_df['rolling_sentiment'].reindex(ta_df.index).ffill(limit=20)
    ta_df['insider_sentiment'] = ta_df['insider_sentiment'] / (ta_df['close'] * ta_df['volume'])
    
    # Calculate 'ret' (daily return)
    # Note: df is the original market dataframe with OHLCV
    ret = df['close'].pct_change()
    ta_df['ret'] = ret.reindex(ta_df.index)
    
    # Fill NaNs as per notebook
    # In notebook: regressor.fit(ta_df.fillna(0.0).iloc[:,6:], ...)
    # However, the saved model expects 'volume_adi', which appears to be at index 5.
    # Adjusting to include it.
    
    features = ta_df.iloc[:, 5:].fillna(0.0)
    
    return features

def predict_realtime(ticker, target_date_str, model_dir='/Volumes/ExtremePro/AV_data/models/linear/'):
    """
    Main function to predict for a specific date.
    
    Args:
        ticker (str): Stock ticker.
        target_date_str (str): Date to predict for (YYYY-MM-DD).
        model_dir (str): Directory containing trained models.
        
    Returns:
        float: Predicted return.
    """
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY not set")
        
    # Create temp directory for data processing
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Fetch Data
        data = fetch_and_prepare_data(ticker, target_date_str, api_key)
        
        # 2. Build Features
        X = build_features(ticker, data, temp_dir)
        
        # 3. Load Model
        model_path = os.path.join(model_dir, f'{ticker}.joblib')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")
            
        print(f"Loading model from {model_path}...")
        model = joblib.load(model_path)
        
        # 4. Predict
        # Get the feature vector for the target date
        if target_date_str not in X.index:
            print(f"Warning: Target date {target_date_str} not in feature index. Using latest available date: {X.index[-1]}")
            target_vector = X.iloc[[-1]]
        else:
            target_vector = X.loc[[target_date_str]]
            
        prediction = model.predict(target_vector)
        
        return prediction[0]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Real-time Stock Prediction')
    parser.add_argument('ticker', type=str, help='Stock ticker')
    parser.add_argument('--date', type=str, default=datetime.now().strftime('%Y-%m-%d'), help='Target date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    try:
        pred = predict_realtime(args.ticker, args.date)
        print(f"\nPrediction for {args.ticker} on {args.date}: {pred}")
    except Exception as e:
        print(f"Error: {e}")
