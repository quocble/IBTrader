import os
import sys
import argparse
import datetime
import collections
import inspect

import logging
import time
import os.path
import threading

from ibapi import wrapper
from ibapi.client import EClient
from ibapi.utils import iswrapper
from ibapi.order import (OrderComboLeg, Order)
from ibapi.account_summary_tags import *
from ibapi.ticktype import *
from ibapi.common import *
from ibapi.order_condition import *
from ibapi.contract import *
from ibapi.order import *
from ibapi.order_state import *

from queue import Queue

from threading import Thread
from time import sleep

class IBWrapper(wrapper.EWrapper):
    # ! [ewrapperimpl]
    def __init__(self):
        wrapper.EWrapper.__init__(self)

class IBClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

class IBApp(IBWrapper, IBClient):
    def __init__(self):
        IBWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)
        self.reqId = 100

    @iswrapper
    # ! [error]
    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        super().error(reqId, errorCode, errorString)
        if errorCode in [2106,2104,2108]:
            return

        print("Error. Id: ", reqId, " Code: ", errorCode, " Msg: ", errorString)
        self.lastTickPrice = None
        self.retrieveEvent.set()

    @iswrapper
    # ! [connectack]
    def connectAck(self):
        if self.async:
            self.startApi()
            self.reqManagedAccts()
            print("Connected")

    @iswrapper
    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        print("Account list: ", accountsList)
        self.account = accountsList

    @iswrapper
    # ! [nextvalidid]
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId

    @staticmethod
    def USStock(symbol):
        #! [stkcontract]
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.currency = "USD"
        contract.exchange = "SMART"
        contract.primaryExchange = "ISLAND"
        # contract.primaryExch = "NYSE"
        #! [stkcontract]
        return contract

    @staticmethod
    def order(action, quantity, limitPrice):
        order = Order()
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = quantity
        order.lmtPrice = limitPrice
        return order

    def nextOrderId(self):
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid

    def retrieveAccountSummary(self):
        self.retrieveEvent = threading.Event()
        self.reqAccountSummary(9001, "All", AccountSummaryTags.AllTags)
        self.accountSummary = {}
        self.retrieveEvent.wait()
        return self.accountSummary

    @iswrapper
    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        # print("Acct Summary. ReqId:", reqId, "Acct:", account, "Tag: ", tag, "Value:", value, "Currency:", currency)
        self.accountSummary[tag] = value

    @iswrapper
    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        self.retrieveEvent.set()

    def retrievePositions(self):
        self.retrieveEvent = threading.Event()
        self.reqPositions()
        self.positions = []
        self.retrieveEvent.wait()
        return self.positions
        # self.reqAccountUpdates(True, self.account)

    @iswrapper
    # ! [position]
    def position(self, account: str, contract: Contract, position: float,
                 avgCost: float):
        super().position(account, contract, position, avgCost)
        # print("Position.", account, "Symbol:", contract.symbol, "SecType:",
        #       contract.secType, "Currency:", contract.currency,
        #       "Position:", position, "Avg cost:", avgCost)
        self.positions.append({ 'asset': contract, 'shares': position, 'cost': avgCost })

    @iswrapper
    # ! [positionend]
    def positionEnd(self):
        super().positionEnd()
        print(str(len(self.positions)))
        self.retrieveEvent.set()

    @iswrapper
    # ! [updateportfolio]
    def updatePortfolio(self, contract: Contract, position: float,
                        marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float,
                        realizedPNL: float, accountName: str):
        super().updatePortfolio(contract, position, marketPrice, marketValue,
                                averageCost, unrealizedPNL, realizedPNL, accountName)
        print("UpdatePortfolio.", contract.symbol, "", contract.secType, "@",
              contract.exchange, "Position:", position, "MarketPrice:", marketPrice,
              "MarketValue:", marketValue, "AverageCost:", averageCost,
              "UnrealizedPNL:", unrealizedPNL, "RealizedPNL:", realizedPNL,
              "AccountName:", accountName)

    def retrievePrice(self, symbol):
        self.reqId += 1
        self.retrieveEvent = threading.Event()
        self.lastTickPriceSum = 0
        self.lastTickPriceCount = 0
        self.reqMktData(self.reqId, IBApp.USStock(symbol), "", True, False, [])
        # self.reqContractDetails(1, IBApp.USStock('WFC'))
        # self.reqRealTimeBars(3101, IBApp.USStock(symbol), 5, "MIDPOINT", True, [])

        self.retrieveEvent.wait()
        return self.lastTickPrice

    @iswrapper
    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)
        print(contractDetails.summary)
        self.retrieveEvent.set()

    @iswrapper
    def contractDetailsEnd(self, reqId: int):
        super().contractDetailsEnd(reqId)

    @iswrapper
    # ! [tickprice]
    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float,
                  attrib: TickAttrib):
        super().tickPrice(reqId, tickType, price, attrib)
        # print("Tick Price. Ticker Id:", reqId, "tickType:", tickType, "Price:",
        #       price, "CanAutoExecute:", attrib.canAutoExecute,
        #       "PastLimit", attrib.pastLimit)
        self.lastTickPriceSum += price
        self.lastTickPriceCount += 1

    @iswrapper
    def tickSize(self, reqId: TickerId, tickType: TickType, size: int):
        super().tickSize(reqId, tickType, size)
        # print("Tick Size. Ticker Id:", reqId, "tickType:", tickType, "Size:", size)

    @iswrapper
    def tickGeneric(self, reqId: TickerId, tickType: TickType, value: float):
        super().tickGeneric(reqId, tickType, value)
        # print("Tick Generic. Ticker Id:", reqId, "tickType:", tickType, "Value:", value)

    @iswrapper
    def tickString(self, reqId: TickerId, tickType: TickType, value: str):
        super().tickString(reqId, tickType, value)
        # print("Tick string. Ticker Id:", reqId, "Type:", tickType, "Value:", value)

    @iswrapper
    def tickSnapshotEnd(self, reqId: int):
        super().tickSnapshotEnd(reqId)
        # print("TickSnapshotEnd:", reqId)
        if self.lastTickPriceCount > 0:
            self.lastTickPrice = self.lastTickPriceSum / self.lastTickPriceCount
        else:
            self.lastTickPrice = None

        self.retrieveEvent.set()

    def sendOrder(self, action, symbol, share, limitPrice):
        print("SendOrder ", action, symbol, share, round(limitPrice,2))
        self.simplePlaceOid = self.nextOrderId()
        self.placeOrder(self.simplePlaceOid, IBApp.USStock(symbol), IBApp.order(action, share, round(limitPrice,2)))

    def run(self):
        try:
            super().run()
        except:
            print ("Exiting.")

def tradingAlgo(client):
    print("tradingAlgo started")
    sleep(5)
    pos = client.retrievePositions()
    print(pos)
    actinfo = client.retrieveAccountSummary()
    print(actinfo)
    print(client.retrievePrice("MSFT"))
    #client.sendOrder()

def main():
    app = IBApp()
    # ! [connect]
    app.connect("127.0.0.1", 7497, clientId=0)
    print("serverVersion:%s connectionTime:%s" % (app.serverVersion(),
                                                  app.twsConnectionTime()))
    # ! [connect]
    thread = Thread(target = tradingAlgo, args = (app,))
    thread.start()

    app.run()



if __name__ == "__main__":
    main()
