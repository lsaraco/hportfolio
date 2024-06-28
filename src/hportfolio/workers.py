"""Module for running asynchronous tasks."""
from __future__ import annotations

from typing import TYPE_CHECKING

import yfinance
from pandas import DataFrame
from PyQt5.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from hportfolio.tickers_data import TickersData


class FinanceLoadWorker(QObject):
    """Class to implement working threads for PyQt GUI."""

    # Signals to communicate at different stages of process life
    finished = pyqtSignal(DataFrame)
    progress = pyqtSignal(int)
    progress_message = pyqtSignal(str)

    def __init__(self, tickers_data:TickersData, tickers:list[str]):
        """Worker constructor.

        Args:
            tickers_data (TickersData): Object containing the data of portfolio.
            tickers (list): A list with tickers names.
        """
        QObject.__init__(self)
        self.tickers_data = tickers_data
        self.tickers = tickers

    def get_tickers_value(self) -> DataFrame:
        """Get the value of the tickers on memory (if loaded) or from Yahoo Finance.

        Args:
            None

        Returns:
            A dataframe containing historical price of tickers.
        """
        force_load_ = True
        tickers = self.tickers
        for ticker in tickers:
            if ticker not in self.tickers_data.historical_price_df and ticker != "LIQUIDITY":
                self.tickers_data.used_tickers.add(ticker)
                force_load_ = True
        if force_load_:
            ticker_historic_info = yfinance.Tickers(" ".join(self.tickers_data.used_tickers)).history(interval="1d", start=self.tickers_data.start_date, end=self.tickers_data.tomorrow())
            self.tickers_data.historical_price_df = ticker_historic_info.iloc[:]["Close"]
        self.finished.emit(self.tickers_data.historical_price_df)



