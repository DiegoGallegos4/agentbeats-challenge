import unittest
from unittest.mock import patch, MagicMock
from unittest.mock import patch, MagicMock
from unittest.mock import patch, MagicMock
from unittest.mock import patch, MagicMock
from agent.tools.alpha_vantage_downloader import (
    get_daily_data,
    get_analyst_data,
    get_earnings_data,
    get_news_sentiment,
    get_options_data,
)
import os

class TestAlphaVantageDownloader(unittest.TestCase):

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_daily_data_success(self, mock_get):
        # Mock response data
        mock_response = {
            "Meta Data": {
                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": "IBM",
                "3. Last Refreshed": "2023-10-27",
                "4. Output Size": "Full size",
                "5. Time Zone": "US/Eastern"
            },
            "Time Series (Daily)": {
                "2023-10-27": {
                    "1. open": "140.0",
                    "2. high": "142.0",
                    "3. low": "139.0",
                    "4. close": "141.0",
                    "5. volume": "1000000"
                },
                "2023-10-26": {
                    "1. open": "138.0",
                    "2. high": "140.0",
                    "3. low": "137.0",
                    "4. close": "139.0",
                    "5. volume": "900000"
                },
                "2023-10-25": {
                    "1. open": "135.0",
                    "2. high": "137.0",
                    "3. low": "134.0",
                    "4. close": "136.0",
                    "5. volume": "800000"
                }
            }
        }

        # Configure the mock to return a response with an OK status code and the json data
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_get.return_value = mock_resp_obj

        # Test parameters
        ticker = 'IBM'
        start_date = '2023-10-26'
        end_date = '2023-10-27'
        api_key = 'dummy_key'

        # Call the function
        result = get_daily_data(ticker, start_date, end_date, api_key)

        # Assertions
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['date'], '2023-10-26')
        self.assertEqual(result[1]['date'], '2023-10-27')
        self.assertEqual(result[0]['close'], 139.0)
        self.assertEqual(result[1]['close'], 141.0)

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_daily_data_no_data(self, mock_get):
        # Mock response with error/note
        mock_response = {
            "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute and 500 calls per day."
        }
        
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_get.return_value = mock_resp_obj

        result = get_daily_data('IBM', '2023-10-26', '2023-10-27', 'dummy_key')
        self.assertEqual(result, [])

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_analyst_data(self, mock_get):
        # Mock response
        mock_response = {
            "Symbol": "IBM",
            "AssetType": "Common Stock",
            "Name": "International Business Machines",
            "AnalystTargetPrice": "150.00",
            "AnalystRatingStrongBuy": "2",
            "AnalystRatingBuy": "3",
            "AnalystRatingHold": "5",
            "AnalystRatingSell": "1",
            "AnalystRatingStrongSell": "0"
        }
        
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_get.return_value = mock_resp_obj

        result = get_analyst_data('IBM', 'dummy_key')
        
        self.assertEqual(result['Symbol'], 'IBM')
        self.assertEqual(result['AnalystTargetPrice'], '150.00')
        self.assertEqual(result['AnalystRatingStrongBuy'], '2')

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_earnings_data(self, mock_get):
        # Mock response
        mock_response = {
            "symbol": "IBM",
            "annualEarnings": [
                {"fiscalDateEnding": "2023-09-30", "reportedEPS": "2.2"}
            ],
            "quarterlyEarnings": [
                {"fiscalDateEnding": "2023-09-30", "reportedEPS": "2.2", "estimatedEPS": "2.1"}
            ]
        }
        
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_get.return_value = mock_resp_obj

        result = get_earnings_data('IBM', 'dummy_key')
        
        self.assertEqual(result['symbol'], 'IBM')
        self.assertEqual(len(result['annualEarnings']), 1)
        self.assertEqual(result['quarterlyEarnings'][0]['estimatedEPS'], '2.1')

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_news_sentiment(self, mock_get):
        # Mock response
        mock_response = {
            "items": "50",
            "sentiment_score_definition": "x <= -0.35: Bearish...",
            "relevance_score_definition": "0 < x <= 1: ...",
            "feed": [
                {
                    "title": "IBM Reports Earnings",
                    "url": "https://example.com/ibm-earnings",
                    "time_published": "20231026T120000",
                    "authors": ["John Doe"],
                    "summary": "IBM reported strong earnings...",
                    "overall_sentiment_score": 0.35,
                    "overall_sentiment_label": "Bullish",
                    "ticker_sentiment": [
                        {
                            "ticker": "IBM",
                            "relevance_score": "0.8",
                            "ticker_sentiment_score": "0.4",
                            "ticker_sentiment_label": "Bullish"
                        }
                    ]
                }
            ]
        }
        
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_get.return_value = mock_resp_obj

        result = get_news_sentiment('IBM', 'dummy_key')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], "IBM Reports Earnings")
        self.assertEqual(result[0]['overall_sentiment_label'], "Bullish")

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_news_sentiment_with_time(self, mock_get):
        # Mock response
        mock_response = {"feed": []}
        
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_get.return_value = mock_resp_obj

        get_news_sentiment('IBM', 'dummy_key', time_from='20230101T0000', time_to='20230102T0000')
        
        # Verify URL parameters
        args, _ = mock_get.call_args
        url = args[0]
        self.assertIn('time_from=20230101T0000', url)
        self.assertIn('time_to=20230102T0000', url)

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_news_sentiment_no_ticker(self, mock_get):
        # Mock response
        mock_response = {"feed": []}
        
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_get.return_value = mock_resp_obj

        get_news_sentiment(api_key='dummy_key')
        
        # Verify URL parameters
        args, _ = mock_get.call_args
        url = args[0]
        self.assertNotIn('tickers=', url)

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_options_data(self, mock_get):
        # Mock response
        mock_response = {
            "meta_data": {"1. Information": "Historical Options"},
            "data": [
                {"contractID": "IBM231027C00140000", "type": "call", "strike": "140.00", "implied_volatility": "0.2"}
            ]
        }
        
        mock_resp_obj = MagicMock()
        mock_resp_obj.status_code = 200
        mock_resp_obj.json.return_value = mock_response
        mock_get.return_value = mock_resp_obj

        result = get_options_data('IBM', '2023-10-27', 'dummy_key')
        
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['data'][0]['type'], 'call')
        self.assertEqual(result['data'][0]['implied_volatility'], '0.2')

    @patch('agent.tools.alpha_vantage_downloader.requests.get')
    def test_get_options_data_range(self, mock_get):
        # Mock response for two days
        mock_response_1 = {"data": [{"contractID": "1", "date": "2023-10-26"}]}
        mock_response_2 = {"data": [{"contractID": "2", "date": "2023-10-27"}]}
        
        mock_resp_obj_1 = MagicMock()
        mock_resp_obj_1.status_code = 200
        mock_resp_obj_1.json.return_value = mock_response_1
        
        mock_resp_obj_2 = MagicMock()
        mock_resp_obj_2.status_code = 200
        mock_resp_obj_2.json.return_value = mock_response_2
        
        # Side effect to return different responses
        mock_get.side_effect = [mock_resp_obj_1, mock_resp_obj_2]

        result = get_options_data('IBM', start_date='2023-10-26', end_date='2023-10-27', api_key='dummy_key')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['data'][0]['contractID'], '1')
        self.assertEqual(result[1]['data'][0]['contractID'], '2')
        self.assertEqual(mock_get.call_count, 2)

if __name__ == '__main__':
    unittest.main()
