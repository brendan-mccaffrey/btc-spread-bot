# FTX Algorithmic Trading Client

## Structure

This trading bot is made up of three components

 - **Position Entrance**
 - **Position Monitoring**
 - **Position Exit**

### Position Entrance

When the script is executed, an FTX API client is initialized to the user information identified in *ftx.py* The **position entrance** script is triggered, and the bot evaluates the current spread between *BTC-0924* Futures and *BTC* Spot. Once the spread is confirmed, a limit buy order is placed for the spot. Once this order execution is confirmed, the corresponding future sell limit order is placed. Once this limit order is confirmed, the **position monitoring** process begins.

### Position Monitoring

The **position monitoring** script is triggered after the position is entered successfully. The monitoring script queries the API for the status of the positions every 10 seconds. If the spread increases from that at entry, the position is increased to capture opportunity and avoid margin calls. If the price of *BTC-0924* ever dips below the *BTC* spot, the **position exit** script is triggered. Otherwise, the positions are exited upon expiry of the future (September 24).

### Position Exit

The **position exit** script is executed in a similar fashion to the **position entrance** script. First, the API is queried for the current price of the two pairs, and confirms the spread is less than 0.1%. The script then places a limit sell for the *BTC* spot position, and awaits confirmation. A limit buy is then placed on the *BTC-0924* position if the position is not already exited. The resulting P/L from the position is then written to an excel sheet named *results.xslx*


## Instructions

 - ftx.py: Enter API Key and Subaccount name