from module import FtxClient, FtxOtcClient 
import ftx

from tabulate import tabulate

from json import loads, dump

from openpyxl import Workbook

from os import error, path

import pandas as pd
import numpy as np

import time

if __name__ == '__main__':

    mydesired_spread = 0.10
    myapi_key = 'aZYQ8mZy2mMBc-3a017ECpEDFX2AURo3wn1xUQto'
    mysubaccount_name = None
    # total notional value of two orders to be placed
    amount = 100

    client = ftx.start_entry(mydesired_spread, myapi_key, mysubaccount_name, amount)


    if client is not None:
        print("Successfuly entered position. The transaction history was exported into transaction_logs.xlsx")
        ftx.monitor_position(client)

    else:
        print("Position was not entered successfully. Please manually check the status of the FTX portfolio")
