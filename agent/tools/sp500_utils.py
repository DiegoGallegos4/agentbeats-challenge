
import pandas as pd

def get_sp500_tickers():
    df = pd.read_csv('https://gist.githubusercontent.com/ZeccaLehn/f6a2613b24c393821f81c0c1d23d4192/raw/fe4638cc5561b9b261225fd8d2a9463a04e77d19/SP500.csv')
    return df['Symbol'].tolist()

    