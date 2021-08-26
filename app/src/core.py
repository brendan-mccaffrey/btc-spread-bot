from os import error, path
from module import FtxClient

def initialize_client(api_key, subaccount_name):
    '''
    Creates FTX Client
    :param api_key: Api key of Ftx account
    :param subaccount_name: *Optional* Name of Ftx subaccount
    Returns: client
    '''
    # Initialize tokenfile path for secret_key import
    tokenfile = '../../tokenfile.token'

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