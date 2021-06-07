from module import FtxClient, FtxOtcClient 

from tabulate import tabulate

from json import loads, dump

from openpyxl import Workbook

from os import error, path

import pandas as pd
import numpy as np

import time


def initialize_client():
    tokenfile = 'tokenfile.token'

    # Throw an error if the authorization token file doesn't exist.
    if not path.exists(tokenfile):
        error('Authorization token file can not be found at the following location: {0}'.format(tokenfile))
    
    # Open the authorization token file in text-mode for reading.
    with open(tokenfile, 'r') as tokenfilestream:
        # Read the first line of the authorization token file.
        tokenfiledata = tokenfilestream.readline().rstrip()

    api_key = 'pAl3A4s5CmsjepUBrgTRW0ifToq5okYP_cn5AL7u'
    api_secret = tokenfile
    subaccount_name = None  # Optional

    return FtxClient(api_key, api_secret, subaccount_name)

def get_perp_data(client, start_time = None, end_time = None):
    market = "BTC-PERP"
    resolution = 15
    start_time = start_time
    end_time = end_time

    return json_to_pandas(client.get_price_history(market, resolution, start_time, end_time))

def get_future_data(client, start_time = None, end_time = None):
    market = "BTC-0924"
    resolution = 15
    start_time = start_time
    end_time = end_time

    return json_to_pandas(client.get_price_history(market, resolution, start_time, end_time))

def get_spot_data(client, start_time = None, end_time = None):
    market = "BTC/USD"
    resolution = 15
    start_time = start_time
    end_time = end_time

    return json_to_pandas(client.get_price_history(market, resolution, start_time, end_time))

def json_to_pandas(data):
    return pd.DataFrame(data)

def pretty_print(df):
    print(tabulate(df, headers='keys', tablefmt='psql'))

def create_excel(dfs):
    wb = Workbook()
    ws = wb.active
    with pd.ExcelWriter('output.xlsx', options={'strings_to_formulas': False}) as writer:
        writer.book = wb
        writer.sheets = dict((ws.title, ws) for ws in wb.worksheets)

        for key in dfs.keys():
            dfs[key].to_excel(writer, sheet_name=key)

        writer.save()


def generate_excel(market1 = "BTC-0924", market2 = "BTC-USD"):
    jan042021 = 1609791775
    now = int(time.time())

    dataframes["BTC-0924"] = get_future_data(client, jan042021, now)
    dataframes["BTC-USD"] = get_spot_data(client, jan042021, now)

    create_excel(dataframes)

def get_last_prices(client, markets):
    data = []

    for d in client.get_markets():
        if d['name'] in markets:
            data.append(d)

    return data

def evaluate_opportunity(client):

    prices = dict()

    data = get_last_prices(client, ["BTC/USD", "BTC-0924"])

    for d in data:
        prices[d['name']] = d['ask']

    if prices['BTC/USD'] >= prices['BTC-0924']:
        print("Spot price is currently higher than future.. ")
        print("Not entering position")
        return False

    else:
        print("Future premium is currently ", (prices['BTC-0924']/prices['BTC/USD'] - 1) * 100, "\%")
        return prices

def celebrate(spread):
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("")
    print("      Wohoooooo!     ")
    print("")
    print("You locked in a ", spread, " profit")
    print("")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

def enter_position(client, spot_price, future_price, amount):

    allowed_slippage = 1.001    # margin for price movement 0.1%
    price = 
    order_type = "limit"
    spot_size = amount / 2
    reduce_only = False
    ioc = False
    post_only = False

    print("PLACING ORDER")
    print("price: ", price)
    print("size: ", spot_size)

    #   Questions to consider before deployment
    # trigger price same as limit?
    # ioc or post_only?
    # what to do if spot doesn't go through
    # what to do if future order doesn;t go through

    resp = client.place_conditional_order("BTC/USD", "buy", spot_size, order_type, spot_price * allowed_slippage, reduce_only, ioc)

    filled_price = resp['price']
    btc = resp['filledSize'] / filled_price
    future_size = btc * future_price

    if resp['status'] == "closed" and resp['remainingSize'] == 0:
        print("Spot order executed successfully. You bought ", resp['filledSize'] / filled_price, " BTC @ ", filled_price)

        print("PLACING ORDER")
        print("price: ", future_price)
        print("size: ", future_size)
        resp2 = client.place_conditional_order("BTC-0924", "sell", future_size, order_type, future_price * allowed_slippage, reduce_only, ioc)


        filled_price2 = resp2['price']
        btc2 = resp2['filledSize'] / filled_price2
        if resp2['status'] == "closed" and resp2['remainingSize'] == 0:
            print("Future order executed successfully. You sold ", resp2['filledSize'] / filled_price2, " BTC worth of futures @ ", filled_price2)

            celebrate(resp2['filledSize'] / resp['filledSize'])

            return True
        
        else:
            print("Future order failed")
            


    # ensure spot order was executed and filled
    if resp['status'] != "closed":
        # status can be 'new' (accepted but not processed yet) or 'open'
        cancel_orders("BTC/USD")
        
    if resp['remainingSize'] != 0:
        cancel_orders("BTC/USD")



if __name__ == '__main__':

    dataframes = dict()

    client = initialize_client()

    prices = evaluate_opportunity(client)

    if prices:
        if enter_position(client, prices['BTC/USD'], prices['BTC-0924'], 100):
            print('Success')
        else:
            pass
            # cancel_orders("BYC/USD")
            # cancel_orders("BTC-0")
    

    # pretty_print(df)