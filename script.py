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
    myapi_key = 'pAl3A4s5CmsjepUBrgTRW0ifToq5okYP_cn5AL7u'
    mysubaccount_name = None

    ftx.run(mydesired_spread, myapi_key, mysubaccount_name)
