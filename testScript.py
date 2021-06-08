from importlib.metadata import entry_points
from importlib.util import spec_from_loader
from module import FtxClient, FtxOtcClient 

from tabulate import tabulate

from json import loads, dump

from openpyxl import Workbook

from os import error, path

import pandas as pd
import numpy as np

import ftx
from module import FtxClient

import time
from time import sleep
from datetime import date, datetime

entry_price = 0
entry_size = 0

def run(myapi_key, mysubaccount_name, amount):

    client = ftx.initialize_client(myapi_key, mysubaccount_name)

    # print(get_btc_balance(client))
    
    # test_get_positions(client)
  
    # id = test_place_order(client)
    
    # test_confirmation(client, id)

    # id2 = test_monitor(client)

    # get_last_order_id(client)

    # print(get_btc_balance(client))

    # id = test_future_order(client)

    # test_confirmation(client, id, True)

    # test_df_creation()

    # print(get_futures_position(client))

    test_print()




def get_last_order_id(client):
    resp = client.get_order_history('BTC/USD')

    print(resp)


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

    prices = ftx.get_current_prices(client)

    print(prices['BTC/USD'])

    myprice = prices['BTC/USD'] * 1.001

    resp = client.place_order("BTC/USD", "buy", myprice, 10.0 / myprice, "limit")
    print(resp)

    return resp['id']

def test_confirmation(client, id):
    print("Testing waitForConfirmation")

    global entry_price, entry_size

    confirmation = ftx.waitForConfirmation(client, id)
    

    if confirmation['status'] == "open":
        print("First confirmation")
        print(confirmation)
        print("Confirmation status is open")
        print("Waiting 5 seconds")
        sleep(5)
        confirmation = ftx.waitForConfirmation(client, id)

    print("Second confirmation")
    print(confirmation)

    entry_price = confirmation['avgFillPrice']
    entry_size = confirmation['filledSize']

    print(entry_price)
    print(entry_size)

def test_monitor(client):

    positions = dict()

    resp = client.get_balances()
    for pos in resp:
        positions[pos['coin']] = pos['total']

    while True:
        prices = ftx.get_current_prices(client)

        if prices['BTC/USD'] > entry_price * 1.001:

            test_exit(client, prices['BTC/USD'])
            break

def test_exit(client, price):
    print("Testing exit_position")

    prices = ftx.get_current_prices(client)

    btc_balance = get_btc_balance(client)

    resp = client.place_order("BTC/USD", "sell", price, btc_balance, "limit")
    print(resp)

    return resp['id']

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

def test_print():
    print("Please refer to \'transaction_logs.csv\' to review the P/L for the trade.")


    



    





