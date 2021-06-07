from importlib.util import spec_from_loader
from module import FtxClient, FtxOtcClient 

from tabulate import tabulate

from json import loads, dump

from openpyxl import Workbook

from os import error, path

import pandas as pd
import numpy as np

import time
from time import sleep
from datetime import date, datetime



desired_spread = 0.05
records = pd.DataFrame(columns = ['Timestamp', 'Asset', 'Price', 'Action'])
spot_entry_price = None
spot_pos_size = None
future_entry_price = None
future_pos_size = None

def initialize_client(api_key, subaccount_name):
    tokenfile = 'tokenfile.token'

    # Throw an error if the authorization token file doesn't exist.
    if not path.exists(tokenfile):
        error('Authorization token file can not be found at the following location: {0}'.format(tokenfile))
    
    # Open the authorization token file in text-mode for reading.
    with open(tokenfile, 'r') as tokenfilestream:
        # Read the first line of the authorization token file.
        tokenfiledata = tokenfilestream.readline().rstrip()

    # Configure account information here
    api_secret = tokenfiledata

    return FtxClient(str(api_key), str(api_secret), subaccount_name)

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

def create_excel(dfs, name = 'output.xlsx'):
    wb = Workbook()
    ws = wb.active
    with pd.ExcelWriter(name, options={'strings_to_formulas': False}) as writer:
        writer.book = wb
        writer.sheets = dict((ws.title, ws) for ws in wb.worksheets)

        for key in dfs.keys():
            dfs[key].to_excel(writer, sheet_name=key)

        writer.save()


def generate_logs():
    create_excel(records, 'transaction_logs.xlsx')

def get_last_prices(client, markets):
    data = []

    for d in client.get_markets():
        if d['name'] in markets:
            data.append(d)

    return data

def evaluate_spread(spread):
    global desired_spread

    if spread >= desired_spread:
        return True

    return False

def evaluate_opportunity(client):

    prices = dict()
    data = get_last_prices(client, ["BTC/USD", "BTC-0924"])

    for d in data:
        print("Storing ask price for ", d['name'] , ": ", d['ask'])
        prices[d['name']] = d['ask']

    if prices['BTC/USD'] >= prices['BTC-0924']:
        print("Spot price is currently higher than future.. ")
        print("Not entering position")
        return None
    
    spread = (prices['BTC-0924']/prices['BTC/USD'] - 1) * 100
    print("Future premium is currently ", (prices['BTC-0924']/prices['BTC/USD'] - 1) * 100, "\%")

    if evaluate_spread(spread):
        return prices

    return None

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

def waitForConfirmation(client, id, need_close = False):
    print("Waiting for confirmation..")

    startTime = datetime.now()
    sleep(1)

    if need_close:
        while True:
            response = client.get_order_status(id)
            if response['status'] == "closed":
                return response

            elapsedTime = datetime.now() - startTime
            if elapsedTime.seconds > 10:
                # What to do here? we have waited over 10 seconds for order (either future match of the full/partial of the spot, or the remaining of spot) to be filled
                # TODO
                pass
            # Add one second stall so we don't hit FTX rate limit
            sleep(1)


    else:
        while True:
            response = client.get_order_status(id)

            if response['filledSize'] > 0:
                return response

            elapsedTime = datetime.now() - startTime
            if elapsedTime.seconds > 20:
                # What to do here? we have waited over 10 seconds for 1st leg to be filled
                # TODO
                pass
            # Add one second stall so we don't hit FTX rate limit
            sleep(1)


def enter_position(client, spot_price, future_price, amount):
    # declare global variables for future monitoring / exiting
    global future_pos_size, spot_pos_size

    # initialize variables for order placement
    allowed_slippage = 1.001    # margin for price movement 0.1%
    order_type = "limit"
    spot_size = amount / 2
    future_size = amount / 2
    reduce_only = False
    ioc = False
    post_only = False

    open = False

    # declare spot order
    print("PLACING SPOT LIMIT BUY ORDER")
    print("price: ", spot_price)
    print("size: ", spot_size)
    print('------------------------------------------------------------------')

    resp = client.place_conditional_order("BTC/USD", "buy", spot_size, order_type, spot_price * allowed_slippage, reduce_only, ioc)
    
    # wait for confirmation of spot order
    while True:
        confirmation = waitForConfirmation(client, resp['id'])

        filled_price = confirmation['avgFillPrice']
        btc = confirmation['filledSize'] / filled_price
        future_size = btc * future_price
        # set global
        spot_pos_size = confirmation['filledSize']

        if confirmation['status'] == "open":
            open = True

        global spot_entry_price 
        # print summary of spot order
        if open:
            print("Spot order partially executed. You bought ", btc, " BTC @ $", filled_price)
            break
        elif confirmation['status'] == "closed":
            spot_entry_price = filled_price
            print("Spot order fully executed. You bought ", btc, " BTC @ $", filled_price)
            recordAction('BTC/USD', filled_price, 'buy')
            break

        # This loop breaks if and only if filledSize > 0

    
    # declare future order matching the filledSize of the spot order
    print('----------------------------------------------------------------')
    print("PLACING BTC-0924 LIMIT SELL ORDER")
    print("price: ", future_price)
    print("size: ", future_size)
    resp2 = client.place_conditional_order("BTC-0924", "sell", future_size, order_type, future_price * allowed_slippage, reduce_only, ioc)

    # this will return the results of get_order_status only when the transaction has been closed (completed)
    confirmation2 = waitForConfirmation(client, resp2['id'], need_close=True)

    filled_price2 = confirmation2['avgFillPrice']
    btc2 = confirmation2['filledSize'] / filled_price2
    # set global
    future_pos_size = confirmation2['filledSize']

    # print summary of future sell order
    print("Future order executed successfully. You sold ", btc2, " BTC worth of futures @ $", filled_price2)
    recordAction('BTC-0924', filled_price2, 'sell')

    global future_entry_price
    future_entry_price = filled_price2

    if not open:
        # if both orders were executed fully, celebrate locked spread and return True
        celebrate(resp2['filledSize'] / resp['filledSize'])
        return True
    
    # this line will complete only when the spot order is closed
    confirmation1 = waitForConfirmation(client, resp['id'], need_close=True)

    filled_price1 = confirmation1['avgFillPrice']
    btc1 = confirmation1['filledSize'] / filled_price1
    future_size1 = btc1 * future_price
    spot_entry_price = filled_price1
    # adjust global
    spot_pos_size = confirmation1['filledSize']

    # print summary of spot order
    print("Spot order was executed fully. You purchased an additional ", confirmation1['filledSize'] / filled_price1 - confirmation['filledSize'] / filled_price, " BTC @ $", filled_price1)
    # record spot buy
    recordAction("BTC/USD", filled_price1, 'buy')
            
    # declare second future order
    print('----------------------------------------------------------------')
    print("PLACING BTC-0924 LIMIT SELL ORDER")
    print("price: ", future_price)
    print("size: ", future_size1)

    resp1 = client.place_conditional_order("BTC-0924", "sell", future_size1, order_type, future_price * allowed_slippage, reduce_only, ioc)
    # this line will complete only when the sell order is closed
    confirmation3 = waitForConfirmation(client, resp1['id'], need_close=True)

    filled_price3 = confirmation3['price']
    btc3 = confirmation3['filledSize'] / filled_price3
    future_entry_price = filled_price2 / confirmation2['filledSize'] + filled_price3 / confirmation3['filledSize']
    # adjust global
    future_pos_size += confirmation3['filledSize']

    # print summary of future sell order
    print("Future order executed successfully. You sold ", btc3, " BTC worth of futures @ $", filled_price3)
    # record transaction
    recordAction("BTC-0924", filled_price3, 'sell')

    return True

def recordAction(asset, price, action):
    global records
    records = records.append({'Timestamp' : datetime.now(), 'Asset' : asset, 'Price' : price, 'Action' : action}, ignore_index=True)


def start_entry(mydesired_spread, myapi_key, mysubaccount_name, amount):

    global desired_spread
    desired_spread = mydesired_spread

    client = initialize_client(myapi_key, mysubaccount_name)

    prices = evaluate_opportunity(client)

    while prices is None:
        sleep(5)
        prices = evaluate_opportunity(client)

    print("Received: ", prices)

    if enter_position(client, prices['BTC/USD'], prices['BTC-0924'], amount):
        return client
    else:
        # the script will never get here because enter_position will only return True, or else it won't return
        return None

    # pretty_print(df)

def get_current_prices(client):
    prices = dict()
    data = get_last_prices(client, ["BTC/USD", "BTC-0924"])

    for d in data:
        print("Storing ask price for ", d['name'] , ": ", d['ask'])
        prices[d['name']] = d['ask']

    return prices

def calc_current_spread(prices):
    return prices['BTC/USD'] / prices['BTC-0924'] - 1

def monitor_position(client):
    flag = True

    liq_price_estimates = dict()

    resp = client.get_positions(True)
    for pos in resp:
        # store liquidation prices for future monitoring purposes
        if "market" in pos:
            liq_price_estimates[pos['market']] = pos['estimatedLiquidationPrice']
        elif "future" in pos:
            liq_price_estimates[pos['future']] = pos['estimatedLiquidationPrice']

    while flag:
        prices = get_current_prices(client)
        curr_spread = calc_current_spread(prices)

        if curr_spread <= 0:
            flag = False
            exit_position(client, prices['BTC/USD'], prices['BTC-0924'])

        # # TODO: Add action for when current spread has increased
        # if curr_spread >= TODO

def exit_position(client, spot_price, future_price):
    # declare global variables for use
    global future_pos_size, spot_pos_size

    # initialize variables for order placement
    allowed_slippage = 0.999   # margin for price movement 0.1%
    order_type = "limit"
    # NOTE reduce_only is true as we are trying to exit our positions
    reduce_only = True
    ioc = False
    post_only = False

    open = False

    # declare future order
    print("PLACING FUTURE LIMIT BUY ORDER")
    print("price: ", future_price)
    print("size: ", future_pos_size)
    print('------------------------------------------------------------------')

    resp = client.place_conditional_order("BTC/USD", "buy", future_pos_size, order_type, future_price * allowed_slippage, reduce_only, ioc)

    # wait for confirmation of future order
    while True:
        confirmation = waitForConfirmation(client, resp['id'])

        filled_price = confirmation['avgFillPrice']
        btc = confirmation['filledSize'] / filled_price  

        if confirmation['status'] == "open":
            open = True

        # print summary of future order
        if open:
            print("Future order partially executed. You bought ", btc, " worth of BTC futures @ $", filled_price)
            break
        elif confirmation['status'] == "closed":
            # set global
            future_pos_size -= confirmation['filledSize']
            print("Future order fully executed. You bought ", btc, " worth of BTC futures @ $", filled_price)
            recordAction('BTC-0924', filled_price, 'buy')
            break

        # This loop breaks if and only if filledSize > 0

 
    # declare spot order, matching the filledSize of the future order
    print('----------------------------------------------------------------')
    print("PLACING BTC/USD LIMIT SELL ORDER")
    print("price: ", spot_price)
    print("size: ", spot_pos_size)
    resp2 = client.place_conditional_order("BTC/USD", "sell", spot_pos_size, order_type, spot_price * allowed_slippage, reduce_only, ioc)

    # this will return the results of get_order_status only when the transaction has been closed (completed)
    confirmation2 = waitForConfirmation(client, resp2['id'], need_close=True)

    filled_price2 = confirmation2['avgFillPrice']
    btc2 = confirmation2['filledSize'] / filled_price2
    # set global
    spot_pos_size -= confirmation2['filledSize']

    # print summary of spot sell order
    print("Spot order executed successfully. You sold ", btc2, " BTC @ $", filled_price2)
    recordAction('BTC/USD', filled_price2, 'sell')
 
    if not open:
        # if both orders were executed fully, return True
        return True
    
    # this line will complete only when the future order is closed
    confirmation1 = waitForConfirmation(client, resp['id'], need_close=True)

    filled_price1 = confirmation1['avgFillPrice']
    btc1 = confirmation1['filledSize'] / filled_price1
    spot_size1 = btc1 * spot_price
    # adjust global
    future_pos_size -= confirmation1['filledSize']

    # print summary of spot order
    print("Spot order was executed fully. You purchased an additional ", confirmation1['filledSize'] / filled_price1 - confirmation['filledSize'] / filled_price, " BTC @ $", filled_price1)
    # record future buy
    recordAction("BTC-0924", filled_price1, 'buy')
            
    # declare second spot order
    print('----------------------------------------------------------------')
    print("PLACING BTC/USD LIMIT SELL ORDER")
    print("price: ", spot_price)
    print("size: ", spot_pos_size)

    resp1 = client.place_conditional_order("BTC-0924", "sell", spot_pos_size, order_type, spot_price * allowed_slippage, reduce_only, ioc)
    # this line will complete only when the sell order is closed
    confirmation3 = waitForConfirmation(client, resp1['id'], need_close=True)

    filled_price3 = confirmation3['price']
    btc3 = confirmation3['filledSize'] / filled_price3
    # adjust global
    spot_pos_size -= confirmation3['filledSize']

    # print summary of future sell order
    print("Spot order executed successfully. You sold ", btc3, " BTC @ $", filled_price3)
    # record transaction
    recordAction("BTC/USD", filled_price3, 'sell')

    return True
      

def tester(client):
    print(client.get_positions())