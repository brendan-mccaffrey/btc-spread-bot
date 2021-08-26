import analyzer

from time import sleep


def runQuartile(client, assets):
    print("Running strategy")
    while True:
        analyzer.get_spreads(client, assets)
        print("Analyzing")
        for name in assets:
            asset = assets[name]

            if not asset.open_position:
                if asset.spread >= asset.quartiles['q3'] and asset.spread > .01:
                    print("\nOPEN POSITION:", name)
                    print("Current Spread:", asset.spread, "Q3:", asset.quartiles['q3'])

            else:
                if asset.spread <= .01:
                    print("CLOSE POSITION")

            

        sleep(10)
