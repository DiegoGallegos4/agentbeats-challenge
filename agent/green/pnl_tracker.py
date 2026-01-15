import pandas as pd
import os
from datetime import datetime
from ..tools import alpha_vantage_downloader as avd

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
    # Save all columns to preserve agent scores
    portfolio_df.to_csv(file_path, index=False)
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
        from ..tools import data_manager as dm
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
    
    # Calculate PnL by Score Type (Agent)
    # Identify agent columns (exclude standard columns)
    excluded_cols = ['ticker', 'weight', 'avg_score', 'centered_score', 'return', 'pnl', 'price_prev', 'price_curr', 'note']
    agent_cols = [c for c in weights_df.columns if c not in excluded_cols and pd.api.types.is_numeric_dtype(weights_df[c])]
    
    agent_pnl_summary = {}
    
    if agent_cols:
        print("\n--- PnL by Agent (Hypothetical) ---")
        for agent in agent_cols:
            # 1. Get scores for this agent
            scores = weights_df.set_index('ticker')[agent]
            
            # 2. Normalize to get weights (Market Neutral, Full Investment)
            # Same logic as portfolio_manager.py
            mean_score = scores.mean()
            centered_scores = scores - mean_score
            abs_sum = centered_scores.abs().sum()
            
            if abs_sum == 0:
                agent_weights = centered_scores * 0
            else:
                agent_weights = centered_scores / abs_sum
            
            # 3. Calculate PnL for this agent
            # Map weights to returns
            # pnl_df has 'ticker' and 'return'
            # We need to align agent_weights with pnl_df returns
            
            agent_pnl = 0.0
            for _, row in pnl_df.iterrows():
                ticker = row['ticker']
                ret = row.get('return', 0.0)
                if ticker in agent_weights:
                    w = agent_weights[ticker]
                    agent_pnl += w * ret
            
            agent_pnl_summary[agent] = agent_pnl
            print(f"{agent}: {agent_pnl:.6f}")
            
            # Add agent pnl contribution to pnl_df for detailed view? 
            # No, strictly speaking 'pnl' column is the actual portfolio pnl.
            # We can add 'agent_weight' columns if needed, but summary is probably enough.

    # Save PnL
    pnl_path = os.path.join(PNL_DIR, f"{current_date_str}.csv")
    pnl_df.to_csv(pnl_path, index=False)
    
    # Print PnL by Ticker
    print("\n--- PnL by Ticker ---")
    print(pnl_df[['ticker', 'weight', 'return', 'pnl']].to_string(index=False, float_format=lambda x: "{:.6f}".format(x)))

    total_pnl = pnl_df['pnl'].sum()
    print(f"-----------------------------------")
    print(f"Total Portfolio PnL: {total_pnl:.6f}")
    print(f"Saved PnL details to {pnl_path}")
    
    return pnl_df
