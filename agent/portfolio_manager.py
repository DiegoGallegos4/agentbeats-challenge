import pandas as pd
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from graph import app
from sp500_utils import get_sp500_tickers

import argparse
from pnl_tracker import save_portfolio_weights, calculate_pnl

def analyze_ticker(ticker, date=None):
    """
    Runs the multi-agent graph for a single ticker.
    """
    print(f"Analyzing {ticker} (Date: {date})...")
    initial_state = {
        "ticker": ticker,
        "date": date,
        "scores": {},
        "analyses": {},
        "errors": []
    }
    
    try:
        # Invoke the graph
        final_state = app.invoke(initial_state)
        return final_state
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

import time

def build_portfolio(tickers, date=None):
    """
    Analyzes tickers and assigns weights.
    """
    results = []
    
    for i, ticker in enumerate(tickers):
        state = analyze_ticker(ticker, date)
        if state:
            # Calculate aggregate score
            scores = state['scores']
            if not scores:
                avg_score = 0.0
            else:
                avg_score = np.mean(list(scores.values()))
            
            
            results.append({
                'ticker': ticker,
                'avg_score': avg_score,
                'details': scores,
                'analyses': state['analyses']
            })
        
    if not results:
        return pd.DataFrame()
        
    # Save Traces (Analyses)
    if date:
        import json
        import os
        traces_dir = "pnl_data/traces"
        os.makedirs(traces_dir, exist_ok=True)
        traces_path = os.path.join(traces_dir, f"{date}.json")
        
        # Create a dict keyed by ticker
        traces = {r['ticker']: r['analyses'] for r in results}
        
        with open(traces_path, 'w') as f:
            json.dump(traces, f, indent=2)
        print(f"Saved agent traces to {traces_path}")
        
    df = pd.DataFrame(results)
    
    # Unpack 'details' into separate columns
    # Unpack 'details' into separate columns
    details_df = df['details'].apply(pd.Series)
    # Drop 'details' and 'analyses' (we don't want full text in CSV)
    df = pd.concat([df.drop(['details', 'analyses'], axis=1), details_df], axis=1)
    
    # Weight Optimization
    # Market Neutral: Sum(w) = 0
    # Full Investment: Sum(|w|) = 1
    
    # Formula: w_i = (S_i - Mean(S)) / Sum(|S_j - Mean(S)|)
    
    mean_score = df['avg_score'].mean()
    df['centered_score'] = df['avg_score'] - mean_score
    abs_sum = df['centered_score'].abs().sum()
    
    if abs_sum == 0:
        df['weight'] = 0.0
    else:
        df['weight'] = df['centered_score'] / abs_sum
        
    return df.sort_values('weight', ascending=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='Analysis date (YYYY-MM-DD)')
    parser.add_argument('--pnl_date', type=str, help='PnL calculation date (YYYY-MM-DD)')
    parser.add_argument('--tickers', type=str, default='subset', help='subset or all')
    parser.add_argument('--download', action='store_true', help='Download data before analysis')
    parser.add_argument('--pnl_only', action='store_true', help='Run only PnL calculation (skip analysis)')
    args = parser.parse_args()

    if args.tickers == 'all':
        tickers = get_sp500_tickers()
    elif args.tickers == 'subset':
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    else:
        # Assume comma-separated list
        tickers = [t.strip() for t in args.tickers.split(',')]
    
    analysis_date = args.date
    
    if args.download:
        if not analysis_date:
            print("Error: --date is required for download.")
            exit(1)
        import data_manager as dm
        print(f"Downloading data for {len(tickers)} tickers for {analysis_date}...")
        dm.download_all_data(tickers, analysis_date)
        print("Download complete.")
    
    if args.pnl_only:
        if not analysis_date or not args.pnl_date:
            print("Error: --date and --pnl_date are required for PnL only mode.")
            exit(1)
        calculate_pnl(analysis_date, args.pnl_date)
    elif analysis_date:
        print(f"Running analysis for {analysis_date} (Local Data)...")
        portfolio = build_portfolio(tickers, date=analysis_date)
        
        if not portfolio.empty:
            print("\nGenerated Portfolio:")
            # Print all columns except 'analyses' if it exists (it's not in results currently but just in case)
            cols_to_print = [c for c in portfolio.columns if c not in ['analyses']]
            print(portfolio[cols_to_print].head())
            
            save_portfolio_weights(analysis_date, portfolio)
            
            if args.pnl_date:
                calculate_pnl(analysis_date, args.pnl_date)
    else:
        # Default behavior (today)
        # Note: This will fail if local data isn't present for today.
        # User should run with --download --date TODAY first.
        print("Please provide --date and --download to fetch data first.")
        # portfolio = build_portfolio(tickers)
        # print(portfolio)
