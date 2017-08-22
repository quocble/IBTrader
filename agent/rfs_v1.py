from base_algo import BaseAlgorithm
import schedule
import time
from client import IBApp
from threading import Thread
import pandas as pd
from zipline.utils.tradingcalendar import get_early_closes,trading_day
import datetime

import logging
log = logging.getLogger(__name__)


class RFSAlgo(BaseAlgorithm):
    def execute(self):
        self.before_trading_start()
        time.sleep(5)
        self.sell_all()
        time.sleep(30)
        self.rebalance()
        print ("**** Algo Done! ****")

    # Fetch data and calculate weights
    def before_trading_start(context):
        context.updatePosition()
        context.updateAccountSummary()

        context.data = pd.read_csv("https://dl.dropboxusercontent.com/u/10877172/Trading/rfs_predict.csv", parse_dates=True, index_col=['date'])
        context.data = context.data.tshift(1, freq=trading_day)

        #filter only today
        context.data = context.data[context.data.index == pd.to_datetime(datetime.datetime.now().date())]
        context.long_assets = context.data[context.data.predict > 0].asset.values
        context.short_assets = context.data[context.data.predict < 0].asset.values

        #print data.fetcher_assets
        # print predict.shape
        #print results.index
        print(len(context.long_assets))
        print(context.long_assets)
        print(context.short_assets)
        # print context.short_assets

        context.weights = {}

        lw = 0.0
        sw = 0.0

        if len(context.long_assets) > 0:
            lw = 0.95 / float(len(context.long_assets))

        if len(context.short_assets) > 0:
            sw = -0.95 / float(len(context.short_assets))

        for stock in context.long_assets:
            context.weights[stock] = lw
        for stock in context.short_assets:
            context.weights[stock] = sw

        #print (context.weights)


    def sell_all(context):
        # Close positions which have been held for > Hold Period
        # print(context.positions)
        for positionObj in context.positions:
            position = positionObj['asset'].symbol
            price = context.broker.retrievePrice(position)

            if price == None:
                print("Error fetching price for " + positionObj['asset'].symbol)
                continue

            shares = positionObj['shares']
            portfolio_value = float(context.accountSummary['NetLiquidation'])

            if position not in context.weights.keys():
                cur_weight = (price*shares)/portfolio_value
                limit_price = cur_weight > 0 and (0.975 * price) or (1.025 * price)
                print("SELL => {} ALL".format(position))
                context.order_target_percent(position, 0, limit_price)
            else:
                cur_weight = (price*shares)/portfolio_value
                new_weight = context.weights[position]
                print(cur_weight, new_weight)
                if new_weight != None:
                    if (cur_weight > 0 and cur_weight > new_weight) or \
                        (cur_weight < 0 and cur_weight < new_weight):

                        limit_price = cur_weight > 0 and (0.94 * price) or (1.06 * price)
                        print("SELL => {} cur_weight={} new_weight={}".format(position, cur_weight, new_weight))
                        context.order_target_percent(position,new_weight, limit_price)
                        context.weights[position] = None

    def rebalance(context):
        for equity, weight in iter(context.weights.items()):
            if weight != None:
                price = context.broker.retrievePrice(equity)

                if price == None:
                    print("Error fetching price for " + equity)
                    continue

                limit_price = weight > 0 and price*1.025 or price * 0.975
                print("BUY => {} weight={:.3f}".format(equity, weight))
                context.order_target_percent(equity, weight, limit_price)

if __name__ == "__main__":

    app = IBApp()
    app.connect("127.0.0.1", 7497, clientId=0)
    print("serverVersion:%s connectionTime:%s" % (app.serverVersion(),
                                                  app.twsConnectionTime()))

    thread = Thread(target = app.run)
    thread.start()

    algo = RFSAlgo(app)
    algo.execute()
    app.disconnect()
