from module import FtxClient, FtxOtcClient 
import ftx
import testScript

from tabulate import tabulate

from json import loads, dump

from openpyxl import Workbook

from os import error, path

import pandas as pd
import numpy as np

import time

if __name__ == '__main__':

    mydesired_spread = 0.10

    # Main Account Read-Only
    # myapi_key = 'IaTmKDfD9-sFn7RfDumFuoUudeI_XJ-x6C1EOTL5'
    # Bot Account
    myapi_key = 'H44-vetflB-eLYXoAE4_bHofqxB-x8i6vHSEuCVc'
    mysubaccount_name = 'Bot-Account'
    # total notional value of two orders to be placed
    amount = 10

    client = testScript.run(myapi_key, mysubaccount_name, amount)
    # client = ftx.start_entry(mydesired_spread, myapi_key, mysubaccount_name, amount)


    # if client is not None:
    #     print("Successfuly entered position. The transaction history was exported into transaction_logs.xlsx")
    #     ftx.monitor_position(client)

    # else:
    #     print("Position was not entered successfully. Please manually check the status of the FTX portfolio")
