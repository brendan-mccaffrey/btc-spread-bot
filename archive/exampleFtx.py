from time import sleep
from datetime import datetime, date
from os import error, path
import pandas as pd
import smtplib

from module import FtxClient #, FtxOtcClient    This is commented because the script currently does not use the OtcClient


'''
________________________________________________________________________________________________________________________________________________
------------------------------------------------------------------------------------------------------------------------------------------------

/////////////////////////////////////////////////////////////////////////
/////////////////////////// GLOBAL VARIABLES ////////////////////////////
/////////////////////////////////////////////////////////////////////////

________________________________________________________________________________________________________________________________________________
------------------------------------------------------------------------------------------------------------------------------------------------
'''
spot_market = None
future_market = None
exp_date = None
quartile1 = None
quartile2 = None
quartile3 = None
margin_buy = 1.002
margin_sell = 0.998

'''
________________________________________________________________________________________________________________________________________________
------------------------------------------------------------------------------------------------------------------------------------------------

/////////////////////////////////////////////////////////////////////////
/////////////////////////// MAIN FUNCTIONS ////////////////////////////
/////////////////////////////////////////////////////////////////////////

________________________________________________________________________________________________________________________________________________
------------------------------------------------------------------------------------------------------------------------------------------------
'''


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


def waitForConfirmation(client, id):
    '''
    Queires the status of an order, and returns the response once the requirement is satisfied (filledSize > 0 iff need_close = False, status = closed otherwise)
    :param id: The id of the order to confirm
    Returns: Ftx order status response
    '''
    # print("Waiting for confirmation..")
    # Store time at the beginning of function execution
    startTime = datetime.now()

    # Provide one second for transaction to settle before query
    # sleep(1)
    flag = True

    while True:
        response = client.get_order_status(id)
        # The order has been closed, we can return the result
        if response['status'] == "closed":
            return response

        # Calculate time elapsed to detect extremely long pending status
        elapsedTime = datetime.now() - startTime
        if elapsedTime.seconds > 60 and flag:
            message = "The FTX spread bot has been waiting on the confirmation of order ", id, " for over 60 seconds. Please manually inspect the FTX account."
            sendNotification(str(message))
            # Change flag so we only send message once
            flag = False

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
    # Print to console that we are entering
    print()
    print("-----------------------------------------------------------------")
    print("-----------------------------------------------------------------")
    print()
    print(" --- Entering position.. ---")
    print()
    

    global spot_market, future_market, margin_buy, margin_sell
    # Initialize variables for order placement
    # Size for asset purchase is in respective asset terms (hence divide by price)
    spot_size = amount / 2 / (spot_price * margin_buy)
    reduce_only = False
    ioc = False
    post_only = False

    # Place spot order
    resp = client.place_order(spot_market, "buy", spot_price * margin_buy, spot_size, "limit", reduce_only, ioc, post_only)
    # Place future order
    resp2 = client.place_order(future_market, "sell", future_price * margin_sell, spot_size, "limit", reduce_only, ioc, post_only)
  
    # Get confirmation (need_close = True)
    print("Confirming spot position entry..")
    conf = waitForConfirmation(client, resp['id'])
    print()
    print("Confirming future position entry..")
    conf2 = waitForConfirmation(client, resp2['id'])

    # Log to console
    print()
    print("--------------------------------------------")
    print()
    print(" --- Position Entries were successful --- ")
    print()
    print("Spot Buy - (Size: ", conf['filledSize'], ") (Market: ", spot_market, ") (Price: ", conf['avgFillPrice'], ")")
    print()
    print("Future Sell - (Size: ", conf2['filledSize'], ") (Market: ", future_market, ") (Price: ", conf2['avgFillPrice'], ")")
    print()
    print("-----------------------------------------------------------------")
    print("-----------------------------------------------------------------")

    # Log transactions to csv
    recordAction(spot_market, 'buy', conf['avgFillPrice'], conf['filledSize'], conf['avgFillPrice'] * conf['filledSize'])
    recordAction(future_market, 'sell', conf2['avgFillPrice'], conf2['filledSize'], conf2['avgFillPrice'] * conf2['filledSize'])

    # Report successful position entrance to console
    # celebrate(conf2['avgFillPrice'] / conf['avgFillPrice'] - 1)

    return monitor_position(client, conf['filledSize'], conf2['filledSize'])


def monitor_position(client, spot_size, future_size):
    '''
    Monitors the status of the position (query every 5 seconds), and triggers exit_position if the spread closes to 0
    :param client: Ftx client
    Returns: Nothing
    '''
    print("")
    print(" --- Monitoring position.. ---")

    global spot_market, future_market
    # Initialize variables for monitoring
    flag = True
    liq_price_estimates = dict()
    positions = dict()

    # Store liquidation prices for future monitoring purposes
    # resp = client.get_positions()
    # for pos in resp:
    #     if pos['future'] == future_market:
    #         liq_price_estimates[future_market] = pos['estimatedLiquidationPrice']
    #         print()
    #         print("Estimate liquidation price for ", future_market, " is :", liq_price_estimates[future_market])
    #         print()

    # Periodically query current annualized return until, with worst-case slippage, it's below Quartile 1
    prices = None
    while True:
        print()
        print("Evaluating sell opportunity..")
        prices = evaluate_exit_opportunity(client)
        if prices is not None:
            break
        sleep(5)
    
    # Trigger exit
    return exit_position(client, prices[spot_market], prices[future_market], spot_size, future_size)


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
    # Print to console that we are entering
    print()
    print("-----------------------------------------------------------------")
    print("-----------------------------------------------------------------")
    print()
    print(" --- Exiting position.. ---")
    print()

    spot_size = get_spot_balance(client)
    
    global spot_market, future_market, margin_buy, margin_sell
    # Initialize variables for order placement
    reduce_only = True
    ioc = False
    post_only = False

    # Place future buy order
    # print(future_market, "buy", future_price * margin_buy, "limit", future_size, reduce_only, ioc, post_only)
    # Place spot sell order
    # print(spot_market, "sell", spot_price * margin_sell, "limit", spot_size, False, ioc, post_only)

    # Place future buy order
    resp2 = client.place_order(future_market, "buy", future_price * margin_buy, future_size, "limit", reduce_only, ioc, post_only)
    # Place spot sell order
    resp = client.place_order(spot_market, "sell", spot_price * margin_sell, spot_size, "limit", False, ioc, post_only)

    # Get confirmations (need_close = True)
    print("Confirming future market close..")
    conf2 = waitForConfirmation(client, resp2['id'])
    print()
    print("Confirming spot market close..")
    conf = waitForConfirmation(client, resp['id'])
    print()

    # Log transactions to csv
    recordAction(future_market, 'buy', conf['avgFillPrice'], conf['filledSize'], conf['avgFillPrice'] * conf['filledSize'])
    recordAction(spot_market, 'sell', conf2['avgFillPrice'], conf2['filledSize'], conf2['avgFillPrice'] * conf2['filledSize'])

    # Log to console
    print("--------------------------------------------")
    print()
    print(" --- Position Exits were successful --- ")
    print()
    print("Spot Sell - (Size: ", conf['filledSize'], ") (Market: ", spot_market, ") (Price: ", conf['avgFillPrice'], ")")
    print()
    print("Future Buy - (Size: ", conf2['filledSize'], ") (Market: ", future_market, ") (Price: ", conf2['avgFillPrice'], ")")
    print()
    print("-----------------------------------------------------------------")
    print("-----------------------------------------------------------------")

    return True
      

def start(myapi_key, mysubaccount_name, my_spot_market, my_future_market, myexp_date, amount):
    '''
    This is the main function
    It initializes the client, waits for a market opportunity, and triggers the trade execution when an attractive spread presents itself
    :param myapi_key: API Key for Ftx client
    :param subaccount_name: *Optional* The name of the subaccount to which the API Key belongs
    :param my_spot_market: The spot market to be traded
    :param my_future_market: The future market to be traded
    :param amount: Total notional amount willing to be devoted to the trade
    Returns: Nothing
    '''
    # Set global variables
    global spot_market, future_market, exp_date
    spot_market = my_spot_market
    future_market = my_future_market
    exp_date = myexp_date

    # Check for instantiation errors
    if spot_market == None or future_market == None:
        print("ERROR: We were not given spot and future markets")
        print("Aborting execution")
        return False

    # Create FTX client instance
    client = initialize_client(myapi_key, mysubaccount_name)

    # Calculate annualized return quartiles based on historical data and assign globals accordingly
    calc_quartiles(client)

    # Query market for prices every 5 seconds until we find an opportunity
    prices = None
    print()
    while True:
        print("Searching for opportunity to enter position..")
        prices = evaluate_enter_opportunity(client)
        if prices is not None:
            break
        sleep(5)

    # Start the trade
    result = enter_position(client, prices[spot_market], prices[future_market], amount)

    # Print final message once the position is exited
    if result:
        print()
        print("--------------------------------------------------------------------------------")
        print("--------------------------------------------------------------------------------")
        print("--------------------------------------------------------------------------------")
        print()
        print(" --- Timestamp: ", datetime.now(), " --- ")
        print()
        print(" --- Congratulations, arbitrage was successful! ---")
        print()
        print(" --- Please check \'transaction_logs.csv\' to review the P/L for this trade. --- ")
        print()
        print("--------------------------------------------------------------------------------")
        print("--------------------------------------------------------------------------------")
        print("--------------------------------------------------------------------------------")

    return result


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
        if d['name'] in [spot_market, future_market]:
            data.append(d)

    return data


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
    global exp_date

    spread = (future / spot - 1)
    days = (exp_date - day).days
    ann_return = spread / days * 365

    return ann_return


def evaluate_enter_opportunity(client):
    '''
    Retreives implied annualized return of premium between future and spot markets to determine if entrance should be taken
    :param client: Ftx Client
    Returns: Dictionary of prices iff arbitrage is attractive, None otherwise
    '''

    global margin_buy, margin_sell
    prices = dict()
    data = get_last_prices(client)

    for d in data:
        prices[d['name']] = d['ask']

    

    # Calculate the current annualized return, assuming allowed slippage is fully taken
    print(get_ann_return(prices[spot_market] , prices[future_market] , date.today()))

    curr_return = get_ann_return(prices[spot_market] * margin_buy, prices[future_market] * margin_sell, date.today()) 
    if curr_return >= quartile2:
        print("Current annualized return is ", curr_return, ", which is higher than Quartile 2")
        return prices
    print("Current annualized return is ", curr_return)
    return prices
    return None


def evaluate_exit_opportunity(client):
    '''
    Retreives implied annualized return of premium between future and spot markets to determine if exit should be taken
    :param client: Ftx Client
    Returns: Dictionary of prices iff exit is attractive, None otherwise
    '''
    global margin_buy, margin_sell
    prices = dict()
    data = get_last_prices(client)

    


    for d in data:
        prices[d['name']] = d['ask']

    return prices

    # Calculate the current annualized return, assuming allowed slippage is fully taken
    curr_return = get_ann_return(prices[spot_market] * margin_sell, prices[future_market] * margin_buy, date.today()) 
    if curr_return <= quartile1:
        print("Current annualized return is ", curr_return, ", which is lower than Quartile 1")
        return prices
    return None


def get_spot_balance(client):
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


def calc_current_spread(prices):
    '''
    Helper function to calculate current spread given prices
    :param client: prices (output of get_current_prices)
    Returns: A numerical value representing the price spread
    '''
    global spot_market, future_market
    return prices[spot_market] / prices[future_market] - 1


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


def calc_quartiles(client):
    '''
    Retrieves historical data at hour intervals, starting on Jan. 1 2021, calculates quartiles (1, 2, 3) of annualized returns 
    implied by the spread, and assigns values to the respective global variables
    :param client: Ftx client
    Returns: Nothing
    '''
    print()
    print("-----------------------------------------------------------------")
    print()
    print("Calculating quartiles of annualized returns..")
    print()
    global spot_market, future_market, quartile1, quartile2, quartile3
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
    print(result)

    quartile1 = result['25%']
    quartile2 = result['50%']
    quartile3 = result['75%']

    print("--------------------------------------------")
    print()
    print("Calculated current quartiles of:")
    print()
    print("Quartile 1 : ", quartile1)
    print("Quartile 2 : ", quartile2)
    print("Quartile 3 : ", quartile3)
    print()
    print("-----------------------------------------------------------------")
    print("-----------------------------------------------------------------")


