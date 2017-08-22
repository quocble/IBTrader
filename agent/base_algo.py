import schedule
import time
from client import IBApp
from threading import Thread

import logging
log = logging.getLogger(__name__)

import pandas as pd

class BaseAlgorithm:
    def __init__(self, broker):
        self.broker = broker
        print("set broker")

    def run_on_trading_day(self, func):
        print("Run function " + func.__name__)
        func()

    def updatePosition(self):
        self.positions = self.broker.retrievePositions()
        self.positions = [pos for pos in self.positions if pos['shares'] != 0]
        self.positionsByStock = dict((v['asset'].symbol, v) for v in self.positions)
        print("positions ", self.positions)
        # print("positionsByStock ", self.positionsByStock)

    def updateAccountSummary(self):
        self.accountSummary = self.broker.retrieveAccountSummary()

    def schedule_function(self, func, time):
        print("Scheduled function " + func.__name__ + " at " + time)
        schedule.every().day.at(time).do(self.run_on_trading_day, func)

    def order_target_percent(self, symbol, percent:float, limit):
        totalPortfolio = float(self.accountSummary['NetLiquidation'])
        totalDollar = percent * totalPortfolio
        share = int(totalDollar / limit)
        currentShares = symbol in self.positionsByStock and self.positionsByStock[symbol]['shares'] or 0
        targetShares = share - currentShares # very important

        action = 'BUY'
        if targetShares < 0:
            action = 'SELL'

        # Currently do not support Long to short without exiting all of it
        if abs(targetShares) > 0:
            self.broker.sendOrder(action, symbol, abs(targetShares), limit)

class TestAlgorithm(BaseAlgorithm):
    def initialize(self):
        print("initialized")
        # self.schedule_function(self.testCSV, "14:08")
        self.updatePosition()
        limitPrice = self.broker.retrievePrice("WFC") * 0.98
        self.order_target_percent('WFC', -0.10, limitPrice)

    def testCSV(self):
        self.data = pd.read_csv("https://dl.dropboxusercontent.com/u/10877172/Trading/rfs_predict.csv")
        print(self.data.tail())
        print("called")


if __name__ == "__main__":

    app = IBApp()
    app.connect("127.0.0.1", 7497, clientId=0)
    print("serverVersion:%s connectionTime:%s" % (app.serverVersion(),
                                                  app.twsConnectionTime()))

    thread = Thread(target = app.run)
    thread.start()

    algo = TestAlgorithm(app)
    algo.initialize()

    while True:
        schedule.run_pending()
        time.sleep(1)
