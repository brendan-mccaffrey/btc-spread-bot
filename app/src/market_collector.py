from time import sleep
from datetime import datetime, date
from os import error, path
import pandas as pd
import smtplib

from module import FtxClient

spot_markets = dict()
future_markets = dict()
# spread_markets = {
#                   'BTC' {
#                           (future_market, spot_market)
#                         }
#                   }
spread_markets = dict()

def get_spread_markets(client):
    print("-- Collecting Markets --")
    markets = client.get_markets()
    isFuture = False

    # loop through markets
    for market in markets:
        name = market['name']

        # parse name
        pieces = name.split("-")
        if len(pieces) == 1:
            isFuture = False
            pieces = name.split("/")
            if len(pieces) != 2:
                print("Error splitting market!", market)
                continue
        else:
            isFuture = True
        asset = pieces[0]
        suffix = pieces[1]

        # add to respective dict
        if isFuture:
            if suffix != '0924':
                print("Not adding future because it's not september: ", name)
                continue
            future_markets[asset] = market

            spot_equivalent = spot_markets.get(asset, "")
            if spot_equivalent != "":
                spread_markets[asset] = (market, spot_equivalent)
        else:
            if suffix != 'USD':
                print("Not adding spread because it's not denominated in USD: ", name)
                continue
            spot_markets[asset] = market

            future_equivalent = future_markets.get(asset, "")
            if future_equivalent != "":
                spread_markets[asset] = (future_equivalent, market)


    print("---------------")
    print("Future Markets:")
    print(future_markets.keys())
    print("---------------")
    print("Spot Markets:")
    print(spot_markets.keys())
    print("---------------")
    print("Spread Markets:")
    print(spread_markets.keys())

    return spread_markets

