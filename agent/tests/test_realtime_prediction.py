import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
import os
import shutil
import tempfile
from datetime import datetime

# Import the module to test
from agent.purple import realtime_prediction

class TestRealtimePrediction(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    @patch('agent.purple.realtime_prediction.avd')
    @patch('agent.purple.realtime_prediction.joblib')
    def test_predict_realtime_flow(self, mock_joblib, mock_avd):
        # Mock Market Data
        dates = pd.date_range(end='2025-01-01', periods=100)
        market_data = []
        for d in dates:
            market_data.append({
                'date': d.strftime('%Y-%m-%d'),
                'open': 100.0,
                'high': 105.0,
                'low': 95.0,
                'close': 102.0,
                'volume': 1000000
            })
        mock_avd.get_daily_data.return_value = market_data
        
        # Mock News Data
        mock_avd.get_news_for_date_range.return_value = [
            {
                'time_published': '20250101T120000',
                'ticker_sentiment': [{'ticker': 'TEST', 'relevance_score': '0.8', 'ticker_sentiment_score': '0.5'}]
            }
        ]
        
        # Mock Insider Data
        mock_avd.get_insider_transactions.return_value = [
            {
                'transaction_date': '2025-01-01',
                'shares': '1000',
                'share_price': '100',
                'acquisition_or_disposal': 'A'
            }
        ]
        
        # Mock Model
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.05])
        mock_joblib.load.return_value = mock_model
        
        # Create Dummy Model File
        model_path = os.path.join(self.test_dir, 'TEST.joblib')
        # We don't need to save a real model, just a file so exists check passes
        # But joblib.load is mocked, so content doesn't matter
        with open(model_path, 'w') as f:
            f.write("dummy model")
            
        # Run Prediction
        prediction = realtime_prediction.predict_realtime('TEST', '2025-01-01', model_dir=self.test_dir)
        
        # Assertions
        self.assertEqual(prediction, 0.05)
        mock_avd.get_daily_data.assert_called_once()
        mock_avd.get_news_for_date_range.assert_called_once()
        mock_avd.get_insider_transactions.assert_called_once()
        mock_joblib.load.assert_called_once()
        mock_model.predict.assert_called_once()

if __name__ == '__main__':
    unittest.main()
