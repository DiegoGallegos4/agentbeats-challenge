import pandas as pd
import os

def aggregate_insider_sentiment(ticker, start_date, end_date, data_dir):
    """
    Aggregates insider sentiment for a given ticker over a specified date range.
    Calculates the net dollar volume (buy - sell).

    Args:
        ticker (str): The stock ticker symbol.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        data_dir (str): Directory containing the parquet files.

    Returns:
        float: Net dollar volume (Buy Volume - Sell Volume).
               Returns 0.0 if no data is found or an error occurs.
    """
    file_path = os.path.join(data_dir, f"{ticker}.parquet")
    
    if not os.path.exists(file_path):
        print(f"No data file found for {ticker} at {file_path}")
        return 0.0

    try:
        df = pd.read_parquet(file_path)
        
        # Ensure date column is datetime
        if 'transaction_date' in df.columns:
            date_col = 'transaction_date'
        elif 'transactionDate' in df.columns:
            date_col = 'transactionDate'
        else:
            print(f"Date column not found in {file_path}")
            return 0.0
            
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Drop rows with invalid dates
        df = df.dropna(subset=[date_col])
        
        # Filter by date range
        mask = (df[date_col] >= start_date) & (df[date_col] <= end_date)
        filtered_df = df.loc[mask].copy()
        
        if filtered_df.empty:
            return 0.0

        # Calculate transaction value
        # Handle potential column name variations
        shares_col = 'shares'
        price_col = 'share_price'
        
        # Convert columns to numeric, coercing errors
        filtered_df[shares_col] = pd.to_numeric(filtered_df[shares_col], errors='coerce').fillna(0)
        filtered_df[price_col] = pd.to_numeric(filtered_df[price_col], errors='coerce').fillna(0)
        
        filtered_df['value'] = filtered_df[shares_col] * filtered_df[price_col]
        
        # Aggregate
        buy_volume = 0.0
        sell_volume = 0.0
        
        # Check for acquisition_or_disposal column
        type_col = 'acquisition_or_disposal'
        if type_col not in filtered_df.columns:
             # Fallback or check other columns if needed
             pass

        if type_col in filtered_df.columns:
            buy_mask = filtered_df[type_col] == 'A'
            sell_mask = filtered_df[type_col] == 'D'
            
            buy_volume = filtered_df.loc[buy_mask, 'value'].sum()
            sell_volume = filtered_df.loc[sell_mask, 'value'].sum()
            
        return buy_volume - sell_volume

    except Exception as e:
        print(f"Error aggregating insider sentiment for {ticker}: {e}")
        return 0.0

def get_rolling_insider_sentiment(ticker, data_dir, window_days=5):
    """
    Calculates the rolling sum of insider sentiment (net dollar volume) for a given ticker.
    
    Args:
        ticker (str): The stock ticker symbol.
        data_dir (str): Directory containing the parquet files.
        window_days (int): The rolling window size in days. Default is 5.

    Returns:
        pd.DataFrame: A DataFrame with 'date' and 'rolling_sentiment'.
                      Returns empty DataFrame if no data is found or an error occurs.
    """
    file_path = os.path.join(data_dir, f"{ticker}.parquet")
    
    if not os.path.exists(file_path):
        print(f"No data file found for {ticker} at {file_path}")
        return pd.DataFrame()

    try:
        df = pd.read_parquet(file_path)
        
        # Ensure date column is datetime
        if 'transaction_date' in df.columns:
            date_col = 'transaction_date'
        elif 'transactionDate' in df.columns:
            date_col = 'transactionDate'
        else:
            print(f"Date column not found in {file_path}")
            return pd.DataFrame()
            
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Drop rows with invalid dates
        df = df.dropna(subset=[date_col])
        
        # Calculate transaction value
        shares_col = 'shares'
        price_col = 'share_price'
        
        # Convert columns to numeric, coercing errors
        df[shares_col] = pd.to_numeric(df[shares_col], errors='coerce').fillna(0)
        df[price_col] = pd.to_numeric(df[price_col], errors='coerce').fillna(0)
        
        df['value'] = df[shares_col] * df[price_col]
        
        # Determine sign based on acquisition or disposal
        type_col = 'acquisition_or_disposal'
        if type_col in df.columns:
            # A = Buy (+), D = Sell (-)
            df['signed_value'] = df.apply(
                lambda row: row['value'] if row[type_col] == 'A' else (-row['value'] if row[type_col] == 'D' else 0), 
                axis=1
            )
        else:
            # Fallback if column missing (shouldn't happen with correct data)
            df['signed_value'] = 0.0

        # Group by date to handle multiple transactions on the same day
        daily_sentiment = df.groupby(date_col)['signed_value'].sum().sort_index()
        
        # Calculate rolling sum over calendar days
        # We need to reindex to ensure all days are covered if we want a true calendar rolling window,
        # but usually rolling on the time series index with 'xD' works if it's a DatetimeIndex.
        rolling_sentiment = daily_sentiment.rolling(f'{window_days}D').sum()
        
        result_df = rolling_sentiment.reset_index()
        result_df.columns = ['date', 'rolling_sentiment']
        result_df = result_df.set_index('date')
        
        return result_df

    except Exception as e:
        print(f"Error calculating rolling insider sentiment for {ticker}: {e}")
        return pd.DataFrame()
