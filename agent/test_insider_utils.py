import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import os
from insider_utils import aggregate_insider_sentiment, get_rolling_insider_sentiment

class TestInsiderUtils(unittest.TestCase):

    @patch('insider_utils.pd.read_parquet')
    @patch('insider_utils.os.path.exists')
    def test_aggregate_insider_sentiment(self, mock_exists, mock_read_parquet):
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock DataFrame
        data = {
            'transaction_date': ['2023-10-25', '2023-10-26', '2023-10-27', '2023-10-28'],
            'acquisition_or_disposal': ['A', 'D', 'A', 'D'],
            'shares': [100, 50, 200, 100],
            'share_price': [10.0, 20.0, 15.0, 10.0]
        }
        df = pd.DataFrame(data)
        mock_read_parquet.return_value = df
        
        # Test case 1: Full range
        # Buy: (100*10) + (200*15) = 1000 + 3000 = 4000
        # Sell: (50*20) + (100*10) = 1000 + 1000 = 2000
        # Net: 4000 - 2000 = 2000
        result = aggregate_insider_sentiment('TEST', '2023-10-25', '2023-10-28', 'dummy_dir')
        self.assertEqual(result, 2000.0)
        
        # Test case 2: Partial range (26th to 27th)
        # Buy: (200*15) = 3000
        # Sell: (50*20) = 1000
        # Net: 3000 - 1000 = 2000
        result = aggregate_insider_sentiment('TEST', '2023-10-26', '2023-10-27', 'dummy_dir')
        self.assertEqual(result, 2000.0)
        
        # Test case 3: No data in range
        result = aggregate_insider_sentiment('TEST', '2023-10-01', '2023-10-02', 'dummy_dir')
        self.assertEqual(result, 0.0)

    @patch('insider_utils.os.path.exists')
    def test_aggregate_insider_sentiment_no_file(self, mock_exists):
        mock_exists.return_value = False
        result = aggregate_insider_sentiment('TEST', '2023-10-25', '2023-10-28', 'dummy_dir')
        self.assertEqual(result, 0.0)

        result = aggregate_insider_sentiment('TEST', '2023-10-25', '2023-10-28', 'dummy_dir')
        self.assertEqual(result, 0.0)

    @patch('insider_utils.pd.read_parquet')
    @patch('insider_utils.os.path.exists')
    def test_get_rolling_insider_sentiment(self, mock_exists, mock_read_parquet):
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock DataFrame
        # Dates: 25th (Buy 1000), 26th (Sell 1000), 28th (Buy 3000)
        data = {
            'transaction_date': ['2023-10-25', '2023-10-26', '2023-10-28'],
            'acquisition_or_disposal': ['A', 'D', 'A'],
            'shares': [100, 50, 200],
            'share_price': [10.0, 20.0, 15.0]
        }
        df = pd.DataFrame(data)
        mock_read_parquet.return_value = df
        
        # Call function with 2-day window
        result_df = get_rolling_insider_sentiment('TEST', 'dummy_dir', window_days=2)
        
        # Expected results:
        # 25th: 1000 (rolling 2d: 24-25) -> 1000
        # 26th: -1000 (rolling 2d: 25-26) -> 1000 + (-1000) = 0
        # 28th: 3000 (rolling 2d: 27-28) -> 0 + 3000 = 3000 (26th is out of window)
        
        self.assertEqual(len(result_df), 3)
        self.assertEqual(result_df.iloc[0]['rolling_sentiment'], 1000.0)
        self.assertEqual(result_df.iloc[1]['rolling_sentiment'], 0.0)
        self.assertEqual(result_df.iloc[2]['rolling_sentiment'], 3000.0)
        
        # Verify dates
        self.assertEqual(result_df.index[0], pd.Timestamp('2023-10-25'))

    @patch('insider_utils.pd.read_parquet')
    @patch('insider_utils.os.path.exists')
    def test_get_rolling_insider_sentiment_corrupted_date(self, mock_exists, mock_read_parquet):
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock DataFrame with one corrupted date
        data = {
            'transaction_date': ['2023-10-25', '2003-11-21</value>...', '2023-10-27'],
            'acquisition_or_disposal': ['A', 'A', 'A'],
            'shares': [100, 100, 100],
            'share_price': [10.0, 10.0, 10.0]
        }
        df = pd.DataFrame(data)
        mock_read_parquet.return_value = df
        
        # Call function
        result_df = get_rolling_insider_sentiment('TEST', 'dummy_dir', window_days=2)
        
        # Should drop the middle row and process the others
        self.assertEqual(len(result_df), 2)
        self.assertEqual(result_df.index[0], pd.Timestamp('2023-10-25'))
        self.assertEqual(result_df.index[1], pd.Timestamp('2023-10-27'))

if __name__ == '__main__':
    unittest.main()
