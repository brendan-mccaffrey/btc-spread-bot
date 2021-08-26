
from Asset import Asset
import core
import market_collector
import analyzer
import helper
import trader
from datetime import date



if __name__ == '__main__':
    # JUNE 25
    exp_date = date(2021, 9, 24)

    # Bot Account
    myapi_key = 'H44-vetflB-eLYXoAE4_bHofqxB-x8i6vHSEuCVc'
    mysubaccount_name = 'Bot-Account'

    # Create FTX client instance
    client = core.initialize_client(myapi_key, mysubaccount_name)

    spread_markets = helper.load_cache('z_spread_markets')
    quartiles = helper.load_cache('z_quartiles')
    assets = helper.load_cache('z_assets')

    if spread_markets == None:
        spread_markets = market_collector.get_spread_markets(client)
        helper.save_cache(spread_markets, 'z_spread_markets')

    if quartiles == None:
        quartiles = analyzer.calc_quartiles_for_each(client, spread_markets)
        helper.save_cache(quartiles, 'z_quartiles')

    if assets == None:
        assets = dict()
        for pair in spread_markets:
            my_asset = Asset(pair, spread_markets[pair][0], spread_markets[pair][1], quartiles[pair])
            print("Created asset:", my_asset.name)
            assets[pair] = my_asset
        helper.save_cache(assets, 'z_assets')

    trader.runQuartile(client, assets)

    




    