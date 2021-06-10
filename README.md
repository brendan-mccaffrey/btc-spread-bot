# FTX Algorithmic Trading Client

This is a Python script designed to capture arbitrage opportunity between BTC future and spot prices. It ulitizes the FTX API, to place orders, monitor positions, and exit positions in accordance with the strategy. 

## Functionality

Upon invoking *script.py*, assuming it's configured correctly, the following will happen:

 1. Global variables will be assigned within ftx script, representing the paramaters of the invokation
 2. An FTX client is established
 3. The hourly historical premium values, since Jan 1 2021, are retreived to calculate the value of the 1st, 2nd, and 3rd quartiles of implied annualized return.
 4. The script priodically (every 5 seconds) queries FTX for the current premium, and triggers `enter_position()` if the current implied annualized return is above the 50th percentile (taking into account the possibility of encountering worst-case slippage in order execution).
 5. Orders of the same size (denominated in terms of underlying token) are placed for the spot (buy) and future (sell) markets, confirmation details are printed to the console, and the transactions are logged to *transaction_logs.csv*.
 6. `monitor_position()` is invoked, which periodically (every 5 seconds) queries FTX for the current premium and triggers `exit_position()` if the current implied annualized return is below the 25th percentile (taking into account the possibility of encountering worst-case slippage in order execution).
 7. Orders of the same size (denominated in terms of underlying token) are placed for the spot (sell) and future (buy) markets close out the positions. Again, confirmation details are printed to the console, and the transactions are logged to *transaction_logs.csv*.

## Structure

This trading bot is made up of three main components

 - **Position Entrance**
 - **Position Monitoring**
 - **Position Exit**

### Position Entrance

When the script is executed, an FTX API client is initialized to the user information identified in *ftx.py* The **position entrance** script is triggered, and the bot evaluates the current spread between *BTC-0924* Futures and *BTC* Spot. Once the spread is confirmed, a limit buy order is placed for the spot. Once this order execution is confirmed, the corresponding future sell limit order is placed. Once this limit order is confirmed, the **position monitoring** process begins.

### Position Monitoring

The **position monitoring** script is triggered after the position is entered successfully. The monitoring script queries the API for the status of the positions every 10 seconds. If the spread increases from that at entry, the position is increased to capture opportunity and avoid margin calls. If the price of *BTC-0924* ever dips below the *BTC* spot, the **position exit** script is triggered. Otherwise, the positions are exited upon expiry of the future (September 24).

### Position Exit

The **position exit** script is executed in a similar fashion to the **position entrance** script. First, the API is queried for the current price of the two pairs, and confirms the spread is less than 0.1%. The script then places a limit sell for the *BTC* spot position, and awaits confirmation. A limit buy is then placed on the *BTC-0924* position if the position is not already exited. The resulting P/L from the position is then written to an excel sheet named *results.xslx*

## Logs

All transactions are logged into *transaction_logs.csv* for P/L tracking purposes.

## Testing

*testScript.py* serves as a sandbox, holding a collection of individual test methods. The *run()* function has several, commented, invokations, which can be uncommented to test respective components. 

## Configuration

 1. Create an account on [FTX](ftx.com), and create an API key
 2. In *script.py* assign values to the following variables accordingly:
    - spot_market
    - future_market
    - exp_date
    - myapi_key
    - mysubaccount_name *optional*
 3. Create a file named *tokenfile.token* and paste your api_secret. Note - the *gitignore* file is configured to prohibit any file with the *.token* extension from being pushed to GitHub.
 4. In your terminal / command prompt program, navigate to the project folder, and run `python3 script.py`


## Inquiries

Please contact [Brendan McCaffrey](mailto:brendanchristophermccaffrey.com) with any inquiries.
