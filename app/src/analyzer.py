import helper

from module import FtxClient

def calc_quartiles_for_each(client, spread_markets):
    quartiles = dict()

    for pair in spread_markets:
        future = spread_markets[pair][0]['name']
        spot = spread_markets[pair][1]['name']

        quartiles[pair] = helper.calc_quartiles(client, future, spot)

    return quartiles

def get_spreads(client, assets):
    isFuture = False
    markets = client.get_markets()
    for market in markets:
        name = market['name']
        if assets.get(name, "") == "":
            continue

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

        if isFuture:
            assets[asset].future = market
        else:
            assets[asset].spot = market

    for name in assets:
        helper.update_spread(assets[name])
        print(name, ":", assets[name].spread)
