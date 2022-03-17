# pylint: disable=import-error
"""
Create a class for vectorized backtesting ofmoving averages,
ADX, and DI Plus using Interactive Brokers API.
"""


import numpy as np
import pandas as pd
import talib
from ib_insync import *
from pylab import plt



class EMA_ADX_VectorBacktester():
    """Class for the vectorized backtesting of EMA/ADX-based trading strategies.

    Attributes
    ==========
    EMA1: int
        time window in days for shorter EMA
    EMA2: int
        time window in days for longer EMA
    end: str
        end date for data retrieval "HH:MM:SS"

    Methods
    =======
    get_data:
        retrieves and prepares the base data set
    set_parameters:
        sets one or two new EMA parameters
    run_strategy:
        runs the backtest for the EMA-based strategy
    plot_results:
        plots the performance of the strategy compared to the symbol
    """


    def __init__(self, EMA1, EMA2, end):
        """Initialize function."""
        self.EMA1 = EMA1
        self.EMA2 = EMA2
        self.end = end
        self.results = None
        self.get_data()
    

    def get_data(self):
        """Retrieve and prepare the data."""
        # make call to API
        ib = IB()
        ib.connect()

        contract = Forex('EURUSD')

        # to change the length of time data is pulled or timeframe update
        #   durationStr and barSizeSetting.
        bars = ib.reqHistoricalData(contract, endDateTime=self.end,
                                durationStr='3 Y', barSizeSetting='1 day',
                                whatToShow='MIDPOINT', useRTH=True, timeout=0)
        # create dataframe from API call
        raw = util.df(bars)

        # select columns that will be used
        raw = raw[["date", "open", "high", "low", "close"]]
        # create new columns
        raw['return'] = np.log(raw["close"] / raw["close"].shift(1))
        raw['EMA1'] = talib.EMA(raw["close"], timeperiod=self.EMA1)
        raw['EMA2'] = talib.EMA(raw["close"], timeperiod=self.EMA2)
        raw['ADX'] = talib.ADX(raw["high"], raw["low"], raw["close"],
                                timeperiod=7) # (timeperiod=n*2) so 7 * 2 = 14
        raw['DI_Plus'] = talib.PLUS_DI(raw["high"], raw["low"],
                                        raw["close"], timeperiod=14)
        self.data = raw


    def set_parameters(self, EMA1=None, EMA2=None):
        """Update EMA parameters and resp. time series."""
        if EMA1 is not None:
            self.EMA1 = EMA1
            self.data['EMA1'] = talib.EMA(self.data["close"], timeperiod=EMA1)
        if EMA2 is not None:
            self.EMA2 = EMA2
            self.data['EMA2'] = talib.EMA(self.data["close"], timeperiod=EMA2)


    def run_strategy(self):
        """Backtest the trading strategy."""
        data = self.data.copy()

        # threshold value for both ADX & DI_Plus
        threshold = 25

        # define entry criteria
        data['position'] = np.where((data['EMA1'] > data['EMA2']) & (data['ADX']
                        >= threshold) & (data['DI_Plus'] >= threshold), 1, -1)

        # create columns to track the effectivness of the strategy
        data['strategy'] = data['position'].shift(1) * data['return']
        data['creturns'] = data['return'].cumsum().apply(np.exp)
        data['cstrategy'] = data['strategy'].cumsum().apply(np.exp)
        self.results = data

        # gross performance of the strategy
        aperf = data['cstrategy'].iloc[-1]
        # out-/underperformance of strategy
        operf = aperf - data['creturns'].iloc[-1]
        print("Gross performance of strategy {}".format(round(aperf, 2)))
        print("\nOut-/underperformance of strategy {}".format(round(operf, 2)))
        return round(aperf, 2), round(operf, 2)


    def plot_results(self):
        """Plot cumulative performance of strategy compared to symbol."""
        if self.results is None:
            print("No results to plot yet. Run a strategy.")

        title = 'EMA1=%d, EMA2=%d' % (self.EMA1, self.EMA2)
        # plot visual representation of Buy & Hold Vs. Strategy
        self.results[['creturns', 'cstrategy']].plot(title=title,
                                                    figsize=(10, 6))
        plt.show()
        self.results[["close", "EMA1", "EMA2"]].plot(figsize=(20, 12))
        plt.show()


if __name__ == '__main__':
    emabt = EMA_ADX_VectorBacktester(5, 20, '20211231 10:00:00')
    print(emabt.run_strategy())
    emabt.plot_results()
