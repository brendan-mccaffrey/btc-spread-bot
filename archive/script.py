from module import FtxClient, FtxOtcClient 
import ftx
import testScript
import testFtx
import exampleFtx

from datetime import date

from tabulate import tabulate

from json import loads, dump

from openpyxl import Workbook

from os import error, path

import pandas as pd
import numpy as np

import time

if __name__ == '__main__':

    '''
    --- Configuration ---

     - spot_market
     - future_market
     - exp_date
     - myapi_key
     - mysubaccount_name [optional]
     - api_secret [configure in tokenfile.token]
     - amount

     Call ftx.start() OR testScript.run()

    '''

    # SPOT MARKET
    spot_market = 'AVAX/USD'

    # FUTURE MARKET
    future_market = 'AVAX-0924'

    # JUNE 25
    exp_date = date(2021, 9, 24)

    # Bot Account
    myapi_key = 'H44-vetflB-eLYXoAE4_bHofqxB-x8i6vHSEuCVc'
    mysubaccount_name = 'Bot-Account'

    # Total notional value (USD) of two orders to be placed
    amount = 40

    # result = 
    # result = ftx.start(myapi_key, mysubaccount_name, spot_market, future_market, exp_date, amount)
    result = exampleFtx.start(myapi_key, mysubaccount_name, spot_market, future_market, exp_date, amount)

    # result = testScript.run(myapi_key, mysubaccount_name, spot_market, future_market, exp_date, amount)
    # result = ftx.start(myapi_key, mysubaccount_name, spot_market, future_market, exp_date, amount)


    # # SEPT 24
    # exp_date = date(2021, 9, 24)

    # # Main Account Read-Only
    # myapi_key = 'IaTmKDfD9-sFn7RfDumFuoUudeI_XJ-x6C1EOTL5'
    # mysubaccount_name = None


