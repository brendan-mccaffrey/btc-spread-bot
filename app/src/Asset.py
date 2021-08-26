

class Asset:

    def __init__(self, name, future_market, spot_market, quartiles):
        self.name = name
        self.future = future_market
        self.spot = spot_market
        self.quartiles = quartiles
        self.spread = 0
        self.open_position = False
