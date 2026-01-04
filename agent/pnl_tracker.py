import pandas as pd
import os
from datetime import datetime
import alpha_vantage_downloader as avd

DATA_DIR = "pnl_data"
WEIGHTS_DIR = os.path.join(DATA_DIR, "weights")
PNL_DIR = os.path.join(DATA_DIR, "pnl")

# Ensure directories exist
os.makedirs(WEIGHTS_DIR, exist_ok=True)
os.makedirs(PNL_DIR, exist_ok=True)

def save_portfolio_weights(date_str: str, portfolio_df: pd.DataFrame):
    """
    Saves the portfolio weights for a specific date.
    Expected columns in portfolio_df: ['ticker', 'weight']
    """
    file_path = os.path.join(WEIGHTS_DIR, f"{date_str}.csv")
    portfolio_df[['ticker', 'weight']].to_csv(file_path, index=False)
    print(f"Saved weights for {date_str} to {file_path}")

def calculate_pnl(prev_date_str: str, current_date_str: str):
    """
    Calculates PnL from prev_date to current_date based on weights at prev_date.
    PnL = Weight * Return
    Return = (Price_current - Price_prev) / Price_prev
    """
    weights_path = os.path.join(WEIGHTS_DIR, f"{prev_date_str}.csv")
    if not os.path.exists(weights_path):
        print(f"No weights found for {prev_date_str}")
        return None
        
    weights_df = pd.read_csv(weights_path)
    results = []
    
    print(f"Calculating PnL from {prev_date_str} to {current_date_str}...")
    
    for _, row in weights_df.iterrows():
        ticker = row['ticker']
        weight = row['weight']
        
        if weight == 0:
            results.append({'ticker': ticker, 'weight': 0, 'return': 0, 'pnl': 0})
            continue
            
        # Fetch daily data to get close prices
        # Use local data manager
        import data_manager as dm
        # We need data up to current_date_str
        data = dm.read_local_market_data(ticker, current_date_str)
        
        if not data:
            print(f"Warning: No data for {ticker}")
            results.append({'ticker': ticker, 'weight': weight, 'return': 0, 'pnl': 0, 'note': 'No Data'})
            continue
            
        # Convert to dict for easy lookup
        # data is list of dicts: [{'date': 'YYYY-MM-DD', 'close': 123.45}, ...]
        price_map = {d['date']: d['close'] for d in data}
        
        price_prev = price_map.get(prev_date_str)
        price_curr = price_map.get(current_date_str)
        
        if price_prev is None or price_curr is None:
            print(f"Warning: Missing price for {ticker} (Prev: {price_prev}, Curr: {price_curr})")
            results.append({'ticker': ticker, 'weight': weight, 'return': 0, 'pnl': 0, 'note': 'Missing Price'})
            continue
            
        ret = (price_curr - price_prev) / price_prev
        pnl = weight * ret
        
        results.append({
            'ticker': ticker,
            'weight': weight,
            'return': ret,
            'pnl': pnl,
            'price_prev': price_prev,
            'price_curr': price_curr
        })
        
    pnl_df = pd.DataFrame(results)
    
    # Save PnL
    pnl_path = os.path.join(PNL_DIR, f"{current_date_str}.csv")
    pnl_df.to_csv(pnl_path, index=False)
    
    total_pnl = pnl_df['pnl'].sum()
    print(f"Total PnL for {current_date_str}: {total_pnl:.6f}")
    print(f"Saved PnL details to {pnl_path}")
    
    return pnl_df
