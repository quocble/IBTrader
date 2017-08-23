# IBTrader
IBTrader is live trading agent for Interactive Brokers.  IB's API is queue-based asynchronous and is difficult to use for general purpose trading 
algorithm. We provide an easier abstraction that is similar to Quantopian's API.


## API

These functions are implemented for you.  To buy/sell, simply send target %, other types order can be easily implemented based on this api.

```python
# agent/base_algo.py

class BaseAlgorithm:
  def order_target_percent(self, symbol, percent:float, limit):
    pass
  def run_on_trading_day(self, func):
    pass
  def updatePosition(self):
    pass
  def updateAccountSummary(self):
    pass
```

### Example

See agent/rfs_v1.py for real example.


### How to run

Startup your IB Client, and enable API

run
```
python agent/rfs_v1.py
```
