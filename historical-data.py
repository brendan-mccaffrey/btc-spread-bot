import ftx
from datetime import datetime
import pandas as pd


def log_data(df):
    '''
    Writes transaction information to csv file
    :param df: Pandas DataFrame of transaction information, adhering to { timestamp: , market: , side: , price: , size: } 
    Returns: Nothing
    '''
    filepath = 'eth-data.csv'
    df.to_csv(filepath, mode='a', index = False, header=None)

if __name__ == '__main__':

    myapi_key = 'H44-vetflB-eLYXoAE4_bHofqxB-x8i6vHSEuCVc'
    mysubaccount_name = 'Bot-Account'

    client = ftx.initialize_client(myapi_key, mysubaccount_name)
    results = client.get_price_history("LUSD/USD", 15, int(datetime(2021, 5, 19, 8).timestamp()), int(datetime(2021, 5, 19, 13).timestamp()))

    df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Start Time"])
    for spot in results:
        df = df.append({"Open": spot['open'], "High": spot['high'], "Low": spot['low'], "Close": spot['close'], "Start Time": spot['startTime']}, ignore_index=True)


    log_data(df)
