from time import sleep
from datetime import datetime
from tabulate import tabulate
from openpyxl import Workbook
from os import error, path

from module import FtxClient #, FtxOtcClient    This is commented because the script currently does not use the OtcClient

import pandas as pd


'''
GLOBAL VARIABLES
'''

desired_spread = 0.05
records = pd.DataFrame(columns = ['Timestamp', 'Asset', 'Price', 'Action'])
spot_entry_price = None
spot_pos_size = None
future_entry_price = None
future_pos_size = None


def initialize_client(api_key, subaccount_name):
    '''
    Creates FTX Client
    :param api_key: Api key of Ftx account
    :param subaccount_name: *Optional* Name of Ftx subaccount
    Returns: client
    '''
    # Initialize tokenfile path for secret_key import
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

    # Return client instance
    return FtxClient(str(api_key), str(api_secret), subaccount_name)

def log_transaction(df):
    '''
    Writes transaction information to csv file
    :param df: Pandas DataFrame of transaction information, adhering to { timestamp: , market: , side: , price: , size: } 
    Returns: Nothing
    '''
    filepath = 'transaction-logs.csv'
    df.to_csv(filepath, mode='a', index = False, header=None)

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

def evaluate_spread(spread):
    '''
    Evaluates the current (input) spread
    :param spread: A number representing the current price spread
    Returns: Boolean indicating if given spread is higher than desired
    '''
    global desired_spread
    if spread >= desired_spread:
        return True
    return False

def evaluate_opportunity(client):
    '''
    Retreives prices of BTC-0924 and BTC-USD markets to determine if an arbitrage should be taken
    :param client: Ftx Client
    Returns: Dictionary of prices iff arbitrage is attractive, None otherwise
    '''
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

def get_btc_balance(client):
    '''
    Helper function that returns current BTC balance (in BTC)
    :param client: Ftx client
    Returns: Amount of BTC holdings
    '''
    resp = client.get_balances()
    positions = dict()
    for pos in resp:
        positions[pos['coin']] = pos['total']

    return positions['BTC']

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
    print("You locked in a ", spread, " profit")
    print("")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

def declare_order(order, price, size):
    '''
    Helper function to declare order placement to the console
    :param order: The order being invoked (e.g. SPOT LIMIT BUY)
    :param price: The limit price of the order
    :param size: The size of the order
    Returns: Nothing
    '''
    print('------------------------------------------------------------------')
    print("PLACING ", order, " ORDER")
    print("Price: ", price)
    print("Size: ", size)
    print('------------------------------------------------------------------')

def get_current_prices(client):
    '''
    Helper function to retrieve current (ask) prices of BTC/USD and BTC-0924
    :param client: Ftx client
    Returns: dictionary of { Market : price } pairs
    '''
    prices = dict()
    data = get_last_prices(client, ["BTC/USD", "BTC-0924"])

    for d in data:
        print("Storing ask price for ", d['name'] , ": ", d['ask'])
        prices[d['name']] = d['ask']

    return prices

def calc_current_spread(prices):
    '''
    Helper function to calculate current spread given prices
    :param client: prices (output of get_current_prices)
    Returns: A numerical value representing the price spread
    '''
    return prices['BTC/USD'] / prices['BTC-0924'] - 1

def recordAction(market, action, price, size):
    '''
    Helper function to record transaction information to a csv file
    :param market: Market in which order was placed
    :param action: Buy or sell, depending on side of order
    :param price: Price at which the order was executed
    :param size: Size of the order, in USD terms
    Returns: Nothing
    '''
    transaction = pd.DataFrame({'Timestamp' : datetime.now(), 'Market' : market, 'Action' : action, 'Price' : price, 'Size': size}, index = [0])
    log_transaction(transaction)


def waitForConfirmation(client, id, need_close = False):
    '''
    Queires the status of an order, and returns the response once the requirement is satisfied (filledSize > 0 iff need_close = False, status = closed otherwise)
    :param id: The id of the order to confirm
    :param need_close: *Optional* Boolean; True if you want method to return only when the order of interest if closed (fully executed)
    Returns: Ftx order status response
    '''
    print("Waiting for confirmation..")
    # Store time at the beginning of function execution
    startTime = datetime.now()

    # Provide one second for transaction to settle before query
    sleep(1)

    if need_close:
        while True:
            response = client.get_order_status(id)
            # The order has been closed, we can return the result
            if response['status'] == "closed":
                return response
            # Calculate time elapsed to detect extremely long pending status
            elapsedTime = datetime.now() - startTime
            if elapsedTime.seconds > 20:
                # What to do here? we have waited over 20 seconds for order (either future match of the full/partial of the spot, or the remaining of spot) to be filled
                # TODO
                pass
            # Add one second stall so we don't hit FTX rate limit
            sleep(1)

    else:
        while True:
            response = client.get_order_status(id)
            # If we don't need close, we can return the response to submit a partial matching order
            if response['filledSize'] > 0:
                return response
            # Calculate time elapsed to detect extremely long pending status
            elapsedTime = datetime.now() - startTime
            if elapsedTime.seconds > 20:
                # What to do here? we have waited over 10 seconds for 1st leg to be filled
                # TODO
                pass
            # Add one second stall so we don't hit FTX rate limit
            sleep(1)

def enter_position(client, spot_price, future_price, amount):
    '''
    Executes the sequential spot+future orders to enter the spread arbitrage position
    :param client: Ftx client
    :param spot_price: Price of BTC/USD when the arbitrage was declared attractive
    :param future_price: Price of BTC-0924 when the arbitrage was declared attractive
    :param amount: Notional amount of the combined position (100 will imply $50 to spot and $50 to future)
    Returns: Nothing
    '''
    # Initialize variables for order placement
    allowed_slippage = 1.0001    # margin for price movement 0.1%
    order_type = "limit"
    # Size for asset purchase is in respective asset terms (hence divide by price)
    spot_size = amount / 2 / spot_price
    reduce_only = False
    ioc = False
    post_only = False

    # Print order details to console
    declare_order("BTC/USD LIMIT BUY", spot_price * allowed_slippage, spot_size)
    # Place spot order
    resp = client.place_order("BTC/USD", "buy", spot_price * allowed_slippage, spot_size, order_type, reduce_only, ioc, post_only)
    # Get confirmation (need_close = True)
    confirmation = waitForConfirmation(client, resp['id'], need_close=True)

    filled_price = confirmation['avgFillPrice']
    btc = confirmation['filledSize']
    print("Spot order fully executed. You bought ", btc, " BTC @ $", filled_price)
    recordAction('BTC/USD','buy', filled_price, btc * filled_price)
 
    # Declare future order matching the filledSize of the spot order
    declare_order("BTC-0924 LIMIT SELL", future_price, btc * future_price)
    # Place future order
    resp2 = client.place_order("BTC-0924", "sell", future_price * allowed_slippage, btc, order_type, reduce_only, ioc, post_only)
    # Get confirmation (need_close = True)
    confirmation2 = waitForConfirmation(client, resp2['id'], need_close=True)

    filled_price2 = confirmation2['avgFillPrice']
    btc2 = confirmation2['filledSize']
    print("Future order executed successfully. You sold ", btc2, " BTC worth of futures @ $", filled_price2)
    recordAction('BTC-0924', 'sell', filled_price2, btc2 * filled_price2)

    # Report successful position entrance to console
    celebrate(filled_price / filled_price2 - 1)

    return monitor_position(client)


def monitor_position(client):
    '''
    Monitors the status of the position (query every 5 seconds), and triggers exit_position if the spread closes to 0
    :param client: Ftx client
    Returns: Nothing
    '''
    flag = True

    liq_price_estimates = dict()
    positions = dict()

    resp = client.get_positions(True)
    for pos in resp:
        # store liquidation prices for future monitoring purposes
        liq_price_estimates[pos['future']] = pos['estimatedLiquidationPrice']
        positions[pos['future']] = pos['size']

    resp = client.get_balances()
    for pos in resp:
        positions[pos['coin']] = pos['total']

    while True:
        prices = get_current_prices(client)
        curr_spread = calc_current_spread(prices)

        if curr_spread <= 0:
            break
        sleep(5)

        # # TODO: Add action for when current spread has increased
        # if curr_spread >= TODO
    
    return exit_position(client, prices['BTC/USD'], prices['BTC-0924'], positions['BTC'] * prices['BTC/USD'], positions['BTC-0924'] * prices['BTC-0924'])


def exit_position(client, spot_price, future_price, spot_size, future_size):
    '''
    Executes the sequential future+spot orders to ecit the spread arbitrage position
    :param client: Ftx client
    :param spot_price: Price of BTC/USD when the spread was 0
    :param future_price: Price of BTC-0924 when the spread was 0
    :param spot_size: Size of BTC position in USD
    :param future_size: Size of BTC-0924 position in USD
    Returns: Nothing
    '''

    # initialize variables for order placement
    allowed_slippage = 0.9999   # margin for price movement 0.1%
    order_type = "limit"
    # NOTE reduce_only is true as we are trying to exit our positions
    reduce_only = True
    ioc = False
    post_only = False

    # Declare future order
    declare_order("FUTURE LIMIT BUY", future_price, future_size)
    # Place order
    resp = client.place_order("BTC-0924", "buy", future_price * allowed_slippage, future_size, order_type, reduce_only, ioc, post_only)
    # Get confirmation
    confirmation = waitForConfirmation(client, resp['id'], need_close=True)

    filled_price = confirmation['avgFillPrice']
    filled_size = confirmation['filledSize']  
    print("Future order fully executed. You bought ", filled_size, " worth of BTC futures @ $", filled_price)
    recordAction('BTC-0924', 'buy', filled_price, filled_size)

    # declare spot order, matching the filledSize of the future order
    declare_order("BTC LIMIT SELL", spot_price, spot_size)
    # Place order
    resp2 = client.place_order("BTC/USD", "sell", spot_price * allowed_slippage, spot_size, order_type, False, ioc, post_only)
    # Get confirmation
    confirmation2 = waitForConfirmation(client, resp2['id'], need_close=True)

    filled_price2 = confirmation2['avgFillPrice']
    filled_size2 = confirmation2['filledSize']
    print("Spot order executed successfully. You sold ", filled_size2 / filled_price2, " BTC @ $", filled_price2)
    recordAction('BTC/USD', 'sell', filled_price2, filled_size2)

    return True
      

def start_entry(mydesired_spread, myapi_key, mysubaccount_name, amount):
    '''
    This is the main function
    It initializes the client, waits for a market opportunity, and triggers the trade execution when an attractive spread presents itself
    :param mydesired_spread: The spread at or above which we would like to enter the position (e.g. .10)
    :param myapi_key: API Key for Ftx client
    :param subaccount_name: *Optional* The name of the subaccount to which the API Key belongs
    :param amount: Total notional amount willing to be devoted to the trade
    Returns: Nothing
    '''
    # Set global variable
    global desired_spread
    desired_spread = mydesired_spread
    # Create FTX client instance
    client = initialize_client(myapi_key, mysubaccount_name)

    # Query market for prices every 5 seconds until we find an opportunity
    prices = None
    while prices is None:
        prices = evaluate_opportunity(client)
        sleep(5)

    # Print to console the prices at which we are entering
    print("Received: ", prices)
    # Start the trade
    result = enter_position(client, prices['BTC/USD'], prices['BTC-0924'], amount)

    # Print final message once the position is exited
    if result:
        print("-----------------------------------------------------------------")
        print("-----------------------------------------------------------------")
        print("-----------------------------------------------------------------")
        print()
        print(datetime.now())
        print("Congratulations, you successfully executed a spread arbitrage. ")
        print()
        print("Please check \'transaction_logs.csv\' to review the P/L for this trade.")
        print()
        print()
        print("-----------------------------------------------------------------")
        print("-----------------------------------------------------------------")
        print("-----------------------------------------------------------------")





'''
________________________________________________________________________________________________________________________________________________
------------------------------------------------------------------------------------------------------------------------------------------------


/////////////////////////// ARCHIVED FUNCTIONS ////////////////////////////
These are functions that didn't end of getting utilized by the final script.
///////////////////////////////////////////////////////////////////////////


________________________________________________________________________________________________________________________________________________
------------------------------------------------------------------------------------------------------------------------------------------------

def enter_position(client, spot_price, future_price, amount):
    
    Executes the sequential spot+future orders to enter the spread arbitrage position
    :param client: Ftx client
    :param spot_price: Price of BTC/USD when the arbitrage was declared attractive
    :param future_price: Price of BTC-0924 when the arbitrage was declared attractive
    :param amount: Notional amount of the combined position (100 will imply $50 to spot and $50 to future)
    Returns: True when the position is entered
    
    # declare global variables for future monitoring / exiting
    global future_pos_size, spot_pos_size

    # initialize variables for order placement
    allowed_slippage = 1.001    # margin for price movement 0.1%
    order_type = "limit"
    # Size for asset purchase is in respective asset terms (hence divide by price)
    spot_size = amount / 2 / spot_price
    reduce_only = False
    ioc = False
    post_only = False
    # Flag variable to mark order status
    open = False

    # Print order details to console
    declare_order("BTC/USD LIMIT BUY", spot_price * allowed_slippage, spot_size)
    # Place order
    resp = client.place_order("BTC/USD", "buy", spot_price * allowed_slippage, spot_size, order_type, reduce_only, ioc, post_only)
    
    # Wait for confirmation of spot order
    while True:
        confirmation = waitForConfirmation(client, resp['id'])

        filled_price = confirmation['avgFillPrice']
        btc = confirmation['filledSize']
        future_size = btc

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
            recordAction('BTC/USD','buy', filled_price, confirmation['filledSize'] * filled_price)
            break

        # This loop breaks if and only if filledSize > 0

    
    # Declare future order matching the filledSize of the spot order
    declare_order("BTC-0924 LIMIT SELL", future_price, future_size)
    # Place order
    resp2 = client.place_order("BTC-0924", "sell", future_price * allowed_slippage, future_size, order_type, reduce_only, ioc, post_only)

    # Get confirmation (need_close = True)
    confirmation2 = waitForConfirmation(client, resp2['id'], need_close=True)

    filled_price2 = confirmation2['avgFillPrice']
    btc2 = confirmation2['filledSize'] / filled_price2

    # Print summary of future sell order
    print("Future order executed successfully. You sold ", btc2, " BTC worth of futures @ $", filled_price2)
    recordAction('BTC-0924', 'sell', filled_price2, btc * filled_price2)

    if not open:
        # If both orders were executed fully, celebrate locked spread and return True
        celebrate(resp2['filledSize'] / resp['filledSize'])
        return True
    
    # This line will complete only when the spot order is closed
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

    resp1 = client.place_order("BTC-0924", "sell", future_price * allowed_slippage, future_size1, order_type, reduce_only, ioc, post_only)
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

def json_to_pandas(data):
    return pd.DataFrame(data)

def pretty_print(df):
    print(tabulate(df, headers='keys', tablefmt='psql'))

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
------------------------------------------------------------------------------------------------------------------------------------------------

'''