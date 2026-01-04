import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import os
import shutil
from batch_downloader import download_all_sp500, download_all_sp500_options, download_all_sp500_insider_transactions

class TestBatchDownloader(unittest.TestCase):

    def setUp(self):
        self.test_dir = 'test_output'
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch('batch_downloader.time.sleep')
    @patch('batch_downloader.get_daily_data')
    @patch('batch_downloader.get_sp500_tickers')
    def test_download_all_sp500(self, mock_get_tickers, mock_get_data, mock_sleep):
        # Mock tickers
        mock_get_tickers.return_value = pd.DataFrame({'Symbol': ['AAA', 'BBB']})
        
        # Mock data
        mock_get_data.side_effect = [
            [{'date': '2023-10-27', 'close': 100}], # Data for AAA
            [] # No data for BBB
        ]

        # Call function
        download_all_sp500('2023-10-26', '2023-10-27', self.test_dir, 'dummy_key')

        # Verify files
        # Verify files
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'AAA.parquet')))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, 'BBB.parquet')))
        
        # Verify sleep called
        self.assertEqual(mock_sleep.call_count, 2)

    @patch('batch_downloader.time.sleep')
    @patch('batch_downloader.get_options_data')
    @patch('batch_downloader.get_sp500_tickers')
    @patch('batch_downloader.random.uniform')
    def test_download_all_sp500_options(self, mock_uniform, mock_get_tickers, mock_get_options, mock_sleep):
        # Mock random jitter
        mock_uniform.return_value = 0.1
        # Mock tickers
        mock_get_tickers.return_value = pd.DataFrame({'Symbol': ['AAA', 'BBB']})
        
        # Mock data
        def get_options_side_effect(ticker, **kwargs):
            if ticker == 'AAA':
                return {'data': [{'contractID': '1', 'strike': '100'}]}
            return None
            
        mock_get_options.side_effect = get_options_side_effect

        # Call function
        download_all_sp500_options(date='2023-10-27', output_dir=self.test_dir, api_key='dummy_key', max_workers=2)

        # Verify files
        # New structure: output_dir/TICKER/YYYYMMDD.parquet
        # 2023-10-27 -> 20231027
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'AAA', '20231027.parquet')))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, 'BBB', '20231027.parquet')))
        
        # Verify sleep called (RateLimiter calls sleep)
        # With 2 items and 0.85s interval, it should sleep at least once or twice depending on timing.
        # We just verify it was called.
        self.assertTrue(mock_sleep.called)

        # Verify sleep called (RateLimiter calls sleep)
        # With 2 items and 0.85s interval, it should sleep at least once or twice depending on timing.
        # We just verify it was called.
        self.assertTrue(mock_sleep.called)

    @patch('batch_downloader.time.sleep')
    @patch('batch_downloader.get_options_data')
    @patch('batch_downloader.get_sp500_tickers')
    @patch('batch_downloader.os.path.exists')
    @patch('batch_downloader.os.makedirs')
    @patch('batch_downloader.random.uniform')
    def test_download_all_sp500_options_skip_existing(self, mock_uniform, mock_makedirs, mock_exists, mock_get_tickers, mock_get_options, mock_sleep):
        # Mock random jitter
        mock_uniform.return_value = 0.1
        # Mock tickers
        mock_get_tickers.return_value = pd.DataFrame({'Symbol': ['AAA', 'BBB']})
        
        # Mock exists logic for new structure: output_dir/TICKER/YYMMDD.parquet
        # Let's say we are downloading for 2023-10-27.
        # AAA/231027.parquet exists.
        # BBB/231027.parquet does not.
        
        def side_effect(path):
            if path == self.test_dir:
                return True
            if path.endswith('AAA'): # Ticker dir
                return True
            if path.endswith('BBB'): # Ticker dir
                return True
            if 'AAA/20231027.parquet' in path:
                return True
            if 'BBB/20231027.parquet' in path:
                return False
            return False
        
        mock_exists.side_effect = side_effect

        # Mock data for BBB
        mock_get_options.return_value = {'data': [{'contractID': '1', 'strike': '100'}]}

        # Call function
        download_all_sp500_options(date='2023-10-27', output_dir=self.test_dir, api_key='dummy_key', max_workers=2)

        # Verify get_options_data called only once (for BBB)
        self.assertEqual(mock_get_options.call_count, 1)
        self.assertEqual(mock_get_options.call_args[0][0], 'BBB')
        
        # Verify makedirs called for ticker dirs (or at least output_dir)
        # Since we mocked exists=True for ticker dirs, it might not be called for them if logic checks first.
        # But let's check if it was called at least once or logic is sound.

    @patch('batch_downloader.time.sleep')
    @patch('batch_downloader.get_insider_transactions')
    @patch('batch_downloader.get_sp500_tickers')
    @patch('batch_downloader.random.uniform')
    def test_download_all_sp500_insider_transactions(self, mock_uniform, mock_get_tickers, mock_get_insider, mock_sleep):
        # Mock random jitter
        mock_uniform.return_value = 0.1
        # Mock tickers
        mock_get_tickers.return_value = pd.DataFrame({'Symbol': ['AAA', 'BBB']})
        
        # Mock data
        def get_insider_side_effect(ticker, **kwargs):
            if ticker == 'AAA':
                return [{'transactionDate': '2023-10-27', 'transactionType': 'P-Purchase'}]
            return None
            
        mock_get_insider.side_effect = get_insider_side_effect

        # Call function
        download_all_sp500_insider_transactions(output_dir=self.test_dir, api_key='dummy_key', max_workers=2)

        # Verify files
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, 'AAA.parquet')))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, 'BBB.parquet')))
        
        # Verify sleep called
        self.assertTrue(mock_sleep.called)

if __name__ == '__main__':
    unittest.main()
