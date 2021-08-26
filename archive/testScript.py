from importlib.metadata import entry_points
from importlib.util import spec_from_loader

from numpy.lib.function_base import _extract_dispatcher
from module import FtxClient, FtxOtcClient 

from tabulate import tabulate
from datetime import date
from json import loads, dump

from openpyxl import Workbook

from os import error, path

import pandas as pd
import numpy as np

import testFtx
from module import FtxClient

import time
from time import sleep
from datetime import date, datetime

'''
DECLARE GLOBAL VARIABLES
'''
spot_market = None
future_market = None
exp_date = None
quartile1 = None
quartile2 = None
quartile3 = None
margin_buy = 1.002
margin_sell = 0.998

def run(myapi_key, mysubaccount_name, my_spot_market, my_future_market, myexp_date, amount):

    # Set global variable
    global spot_market, future_market, exp_date
    spot_market = my_spot_market
    future_market = my_future_market
    exp_date = myexp_date

    client = testFtx.initialize_client(myapi_key, mysubaccount_name)

    testNotification(12345)

    # print(test_exit(client))

    # print(get_curr_ann_return(client))

    # test_calc_quartiles(client)

    # print(get_btc_balance(client))
    
    # test_get_positions(client)
  
    # id = test_place_order(client)
    
    # print(test_confirmation(client, id))

    # id2 = test_monitor(client)

    # get_last_order_id(client)

    # print(get_btc_balance(client))

    # id = test_future_order(client)

    # test_confirmation(client, id, True)

    # test_df_creation()

    # print(get_futures_position(client))

    # test_print()

def get_last_prices(client, markets):
    '''
    Trims the ftx client get_markets() function to return only the markets of interest
    :param markets: List of market names whose prices are to be retreived 
    Returns: List of respective markets' information
    '''
    data = []
    for d in client.get_markets():
        if d['name'] in markets:
            data.append(d)

    return data

def get_current_prices(client):
    '''
    Helper function to retrieve current (ask) prices of BTC/USD and BTC-0924
    :param client: Ftx client
    Returns: dictionary of { Market : price } pairs
    '''
    prices = dict()
    data = get_last_prices(client, [spot_market, future_market])

    for d in data:
        print("Storing ask price for ", d['name'] , ": ", d['ask'])
        prices[d['name']] = d['ask']

    return prices

def test_future_sell(client):
    global margin_buy, margin_sell

    prices = get_current_prices(client)
    future_price = prices['BTC-0625']

    resp2 = client.place_order("BTC-0625", "sell", future_price * margin_sell, 10, "limit", False, False, False)

    return resp2

def get_future_balance(client):
    '''
    Helper function that returns current future balance (in terms of )
    :param client: Ftx client
    Returns: Amount of BTC holdings
    '''
    resp = client.get_positions()
    positions = dict()
    for pos in resp:
        if pos['side'] == 'sell':
            positions[pos['future']] = -1 * pos['size']
        else:
            positions[pos['future']] = pos['size']

    return positions[future_market]

def test_future_buy(client):
    global margin_buy, margin_sell

    balance = get_future_balance(client)

    prices = ftx.get_current_prices(client)
    future_price = prices['BTC-0625']

    resp2 = client.place_order("BTC-0625", "buy", future_price * margin_sell, -1 * balance, "limit", False, False, False)

    return resp2

def get_last_order_id(client):
    resp = client.get_order_history('BTC/USD')

    print(resp)


def get_ann_return(spot, future, day):
    global exp_date

    spread = (future / spot - 1)
    days = (exp_date - day).days
    ann_return = spread / days * 365

    return ann_return


def test_calc_quartiles(client):
    global spot_market, future_market
    # Get hourly historical data
    spot_resp = client.get_price_history(spot_market, 3600, int(datetime(2021, 1, 1).timestamp()), int(datetime.now().timestamp()))
    future_resp = client.get_price_history(future_market, 3600, int(datetime(2021, 1, 1).timestamp()), int(datetime.now().timestamp()))

    df = pd.DataFrame(columns=["Spot Open", "Future Open", "Annualized Return"])

    for spot, future in zip(spot_resp, future_resp):
        if spot['startTime'] != future['startTime']:
            print("ERROR: calc_quartiles was hindered by unsynced historical price lists")
        else:
            day = datetime.strptime(spot['startTime'][:10], "%Y-%m-%d").date()
            ann_return = get_ann_return(spot['open'], future['open'], day)
            df = df.append({"Spot Open": spot['open'], "Future Open": future['open'], "Annualized Return": ann_return}, ignore_index=True)

    result = df["Annualized Return"].describe()

    quartile1 = result['25%']
    quartile2 = result['50%']
    quartile3 = result['75%']

    print("Calculated current quartiles of:")
    print("Quartile 1 : ", quartile1)
    print("Quartile 2 : ", quartile2)
    print("Quartile 3 : ", quartile3)


def test_get_positions(client):
    print("Testing get_positions")

    print("Prices")
    print(ftx.get_current_prices(client))
    print("Future Positions")
    print(client.get_positions())
    print("Spot Positions")
    print(client.get_balances())

def test_future_order(client):
    print("Testing place_future_order")
    prices = ftx.get_current_prices(client)

    print(prices['BTC-0924'])

    myprice = prices['BTC-0924'] * 1.001

    resp = client.place_order("BTC/USD", "buy", myprice, 10.0 / myprice, "limit")
    print(resp)

    return resp['id']

def test_place_order(client):
    print("Testing place_order")

    prices = get_current_prices(client)

    print(prices['BTC/USD'])

    myprice = prices['BTC/USD'] * 1.002

    resp = client.place_order("BTC/USD", "buy", myprice, 10.0 / myprice, "limit")
    print(resp)

    return resp['id']

def test_confirmation(client, id):

    print("Testing waitForConfirmation")

    return ftx.waitForConfirmation(client, id, need_close=True)


def test_exit(client):
    print("Testing exit_position")

    prices = get_current_prices(client)
    price = prices[spot_market]

    btc_balance = get_btc_balance(client)
    print(btc_balance)

    resp = client.place_order(spot_market, "sell", price, btc_balance, "limit")
    print(resp)

    return resp['id']

def get_days():
    '''
    Helper function that return the number of days between now and the expiration date
    :param client: Ftx client
    Returns: Float representing annualized return
    '''
    global exp_date

    int_diff = (exp_date - date.today()).days

    print("Days: ", int_diff)
    return int_diff

def get_curr_ann_return(client):
    '''
    Calculates the implied annual return from the current spread premium
    :param client: Ftx client
    Returns: Float representing annualized return
    '''
    global exp_date, future_market, spot_market
    prices = dict()
    data = get_last_prices(client, [spot_market, future_market])

    for d in data:
        prices[d['name']] = d['ask']

    print(prices)

    spread = (prices[future_market]/prices[spot_market] - 1)

    ann_return = spread / get_days() * 365

    return ann_return

def get_btc_balance(client):
    resp = client.get_balances()
    positions = dict()
    for pos in resp:
        positions[pos['coin']] = pos['total']

    return positions['BTC']

def get_futures_position(client):
    resp = client.get_positions(True)
    positions = dict()
    for pos in resp:
        positions[pos['future']] = pos['size']

    return positions

def test_df_creation():
    df = pd.DataFrame({'Timestamp' : datetime.now(), 'Market' : 'M', 'Action' : 'A', 'Price' : 'P', 'Size': 'S'}, ignore_index = True)
    print(df)

def testNotification(id):
    message = "The FTX spread bot has been waiting on the confirmation of order ", id, " for over 60 seconds. Please manually inspect the FTX account."
    ftx.sendNotification(str(message))
            

def test_print():
    print("Please refer to \'transaction_logs.csv\' to review the P/L for the trade.")


    



    





