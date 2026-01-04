import pandas as pd
import os
from pnl_tracker import save_portfolio_weights, calculate_pnl
from unittest.mock import patch

def test_pnl_flow():
    # 1. Create dummy weights for 2025-01-01
    weights_df = pd.DataFrame({
        'ticker': ['AAPL', 'GOOGL'],
        'weight': [0.5, -0.5]
    })
    save_portfolio_weights('2025-01-01', weights_df)
    
    # 2. Mock avd.get_daily_data to return prices for 2025-01-01 and 2025-01-02
    # AAPL: 100 -> 110 (+10%)
    # GOOGL: 200 -> 190 (-5%)
    
    mock_data_aapl = [
        {'date': '2025-01-01', 'close': 100.0},
        {'date': '2025-01-02', 'close': 110.0}
    ]
    mock_data_googl = [
        {'date': '2025-01-01', 'close': 200.0},
        {'date': '2025-01-02', 'close': 190.0}
    ]
    
    def mock_get_daily_data(ticker, start, end):
        if ticker == 'AAPL': return mock_data_aapl
        if ticker == 'GOOGL': return mock_data_googl
        return []

    with patch('alpha_vantage_downloader.get_daily_data', side_effect=mock_get_daily_data):
        pnl_df = calculate_pnl('2025-01-01', '2025-01-02')
        
    print("\nResulting PnL DataFrame:")
    print(pnl_df)
    
    # Expected PnL:
    # AAPL: 0.5 * 0.10 = 0.05
    # GOOGL: -0.5 * -0.05 = 0.025
    # Total: 0.075
    
    aapl_pnl = pnl_df[pnl_df['ticker'] == 'AAPL']['pnl'].values[0]
    googl_pnl = pnl_df[pnl_df['ticker'] == 'GOOGL']['pnl'].values[0]
    
    print(f"\nAAPL PnL: {aapl_pnl} (Expected 0.05)")
    print(f"GOOGL PnL: {googl_pnl} (Expected 0.025)")
    
    assert abs(aapl_pnl - 0.05) < 1e-6
    assert abs(googl_pnl - 0.025) < 1e-6
    print("\nTest Passed!")

if __name__ == "__main__":
    test_pnl_flow()
