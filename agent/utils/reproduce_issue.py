from agent.tools.alpha_vantage_downloader import get_options_data
import os
from dotenv import load_dotenv

load_dotenv()

print("Attempting to download options data for IBM...")
data = get_options_data('IBM', date=None, start_date='2025-12-23', end_date='2025-12-25', api_key=None)

if data:
    print(f"Successfully downloaded {len(data)} records.")
    print(data[0] if len(data) > 0 else "Data is empty list")
else:
    print("Failed to download data.")
