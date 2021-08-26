from time import sleep
from datetime import datetime, date
from os import error, path
import pandas as pd
import smtplib
import pickle

import CONSTANTS

from module import FtxClient


'''
________________________________________________________________________________________________________________________________________________
------------------------------------------------------------------------------------------------------------------------------------------------

/////////////////////////////////////////////////////////////////////////
/////////////////////////// HELPER FUNCTIONS ////////////////////////////
/////////////////////////////////////////////////////////////////////////

________________________________________________________________________________________________________________________________________________
------------------------------------------------------------------------------------------------------------------------------------------------
'''

def log_transaction(df):
    '''
    Writes transaction information to csv file
    :param df: Pandas DataFrame of transaction information, adhering to { timestamp: , market: , side: , price: , size: } 
    Returns: Nothing
    '''
    filepath = 'transaction-logs.csv'
    df.to_csv(filepath, mode='a', index = False, header=None)


def sendNotification(message):
	# Initialize sender and receiver addresses
	sender = "daveharrison329@gmail.com"
	# @vtext forwards emails to texts to respective phone numbers
	receivers = ["6313568914@vtext.com"]

	# initialize server
	server = smtplib.SMTP('smtp.gmail.com', 587) #587
	
	# send email
	server.starttls()
	server.login(sender, "032370002")
	print("Login successful")
	server.sendmail(sender, receivers, message)
	print("Message sent")


def get_last_prices(client):
    '''
    Trims the ftx client get_markets() function to return only the markets of interest
    :param markets: List of market names whose prices are to be retreived 
    Returns: List of respective markets' information
    '''
    data = []
    for d in client.get_markets():
        if d['name'] in [ftx.spot_market, ftx.future_market]:
            data.append(d)

    return data


def get_days():
    '''
    Helper function that return the number of days between now and the expiration date
    :param client: Ftx client
    Returns: Float representing annualized return
    '''
    int_diff = (CONSTANTS.exp_date - date.today()).days

    print("Days: ", int_diff)
    return int_diff


def get_curr_ann_return(client, future_market, spot_market):
    '''
    Calculates the implied annual return from the current spread premium
    :param client: Ftx client
    Returns: Float representing annualized return
    '''
    prices = dict()
    data = get_last_prices(client, [spot_market, future_market])

    for d in data:
        prices[d['name']] = d['ask']

    spread = (prices[future_market]/prices[spot_market] - 1)

    ann_return = spread / get_days() * 365

    return ann_return

def get_ann_return(spot, future, day):
    '''
    Calculates the implied annual return from information provided through parameters
    :param spot: Spot price
    :param future: Future price
    :param day: The date of the provided price information
    Returns: Float representing annualized return
    '''

    spread = (future / spot - 1)
    days = (CONSTANTS.exp_date - day).days
    ann_return = spread / days * 365

    return ann_return


# def evaluate_enter_opportunity(client, future_market, spot_market):
#     '''
#     Retreives implied annualized return of premium between future and spot markets to determine if entrance should be taken
#     :param client: Ftx Client
#     Returns: Dictionary of prices iff arbitrage is attractive, None otherwise
#     '''

#     global margin_buy, margin_sell
#     prices = dict()
#     data = get_last_prices(client)

#     for d in data:
#         prices[d['name']] = d['ask']

#     # Calculate the current annualized return, assuming allowed slippage is fully taken
#     curr_return = get_ann_return(prices[spot_market] * margin_buy, prices[future_market] * margin_sell, date.today()) 
#     if curr_return >= quartile2:
#         print("Current annualized return is ", curr_return, ", which is higher than Quartile 2")
#         return prices
#     return None


# def evaluate_exit_opportunity(client, future_market, spot_market):
#     '''
#     Retreives implied annualized return of premium between future and spot markets to determine if exit should be taken
#     :param client: Ftx Client
#     Returns: Dictionary of prices iff exit is attractive, None otherwise
#     '''
#     global margin_buy, margin_sell
#     prices = dict()
#     data = get_last_prices(client)

#     for d in data:
#         prices[d['name']] = d['ask']

#     # Calculate the current annualized return, assuming allowed slippage is fully taken
#     curr_return = get_ann_return(prices[spot_market] * margin_sell, prices[future_market] * margin_buy, date.today()) 
#     if curr_return <= quartile1:
#         print("Current annualized return is ", curr_return, ", which is lower than Quartile 1")
#         return prices
#     return None


def get_spot_balance(client, spot_market):
    '''
    Helper function that returns current spot balance (in terms of spot coin)
    :param client: Ftx client
    Returns: Amount of BTC holdings
    '''
    resp = client.get_balances()
    positions = dict()
    for pos in resp:
        positions[pos['coin']] = pos['total']

    return positions[spot_market[:3]]


def get_future_balance(client, future_market):
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


def celebrate(spread):
    '''
    Helper function to confirm position entrance through the console
    :param spread: The spread between spot and future at entrance
    Returns: Nothing
    '''
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("")
    print("      Wohoooooo!     ")
    print("")
    print(" You locked in a ", spread, " profit")
    print("")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


def get_current_prices(client, future_market, spot_market):
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


def update_spread(asset):
    future_price = asset.future['ask']
    spot_price = asset.spot['ask']
    days = get_days()
    asset.spread = float(future_price / spot_price - 1) / float(days) * 365


def recordAction(market, action, price, size, notional_size):
    '''
    Helper function to record transaction information to a csv file
    :param market: Market in which order was placed
    :param action: Buy or sell, depending on side of order
    :param price: Price at which the order was executed
    :param size: Size of the order, in USD terms
    Returns: Nothing
    '''
    transaction = pd.DataFrame({'Timestamp' : datetime.now(), 'Market' : market, 'Action' : action, 'Price' : price, 'Size': size, 'Notional Size': notional_size}, index = [0])
    log_transaction(transaction)


def calc_quartiles(client, future_market, spot_market):
    '''
    Retrieves historical data at hour intervals, starting on Jan. 1 2021, calculates quartiles (1, 2, 3) of annualized returns 
    implied by the spread, and assigns values to the respective global variables
    :param client: Ftx client
    Returns: Nothing
    '''
    print("Calculating quartiles of annualized returns..")
    # Get hourly historical data from
    spot_resp = client.get_price_history(spot_market, 3600, int(datetime(2021, 3, 1).timestamp()), int(datetime.now().timestamp()))
    future_resp = client.get_price_history(future_market, 3600, int(datetime(2021, 3, 1).timestamp()), int(datetime.now().timestamp()))

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

    print("--------------------------------------------")
    print("           ", spot_market)
    print("Calculated current quartiles of:")
    print()
    print("Quartile 1 : ", quartile1)
    print("Quartile 2 : ", quartile2)
    print("Quartile 3 : ", quartile3)
    print()
    print("-----------------------------------------------------------------")
    print("-----------------------------------------------------------------")

    q_dict = { 'q1': quartile1, 'q2': quartile2, 'q3': quartile3}

    return q_dict

def load_cache(name):
    try:
        return pickle.load( open( name + '.pkl', 'rb' ) )
    except:
        pass
    return None

def save_cache(data, name):
    try:
        pickle.dump(data, open( name + '.pkl', 'wb' ) )
    except:
        pass
    return
