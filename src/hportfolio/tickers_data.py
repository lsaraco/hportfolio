"""For tickets data handling."""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, ClassVar

import yfinance
from pandas import DataFrame
from PyQt5.QtCore import QThread

from hportfolio.workers import FinanceLoadWorker


class TickersData:
    """Class for handling ticker data."""

    data_content: ClassVar[dict] = {}
    historical_price_df: ClassVar[dict] = {}
    used_tickers: ClassVar[Any] = set()
    loaded_data_path:str = ""
    total_invested:int = 0
    current_portfolio: ClassVar[dict] = {}
    current_portfolio_value:int = 0
    pandl:int = 0
    start_date:str = "2023-03-14"
    refresh_callback = None

    # Set-up logger
    logger = logging.getLogger("TickersData")

    def __init__(self, data_file: str, refresh_callback:Callable):
        """Constructor."""
        load_status = self.load_data_file(data_file)
        if load_status:
            self.loaded_data_path = data_file
            self.__class__.logger.info(f"Successfully loaded {self.loaded_data_path} file.")
            self.load_total_investment()
            self.load_current_portfolio(blocking=True,callback=refresh_callback)
            self.refresh_callback = refresh_callback
            self.__class__.logger.info(f"Total invested: {self.total_invested}")
            self.__class__.logger.info(f"Portfolio value: {self.current_portfolio_value}")
            self.__class__.logger.info(f"Current portfolio: {self.current_portfolio}")

    def today_int(self):
        """Gets current date as integer."""
        return int(datetime.strptime(self.today(), "%Y-%m-%d").astimezone().timestamp())

    def today(self):
        """Gets current date."""
        return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

    def yesterday(self):
        """Gets yesterday's date."""
        return (datetime.now(timezone.utc).astimezone() - timedelta(days=1)).strftime("%Y-%m-%d")

    def tomorrow(self):
        """Gets tomorrow's date."""
        return (datetime.now(timezone.utc).astimezone() + timedelta(days=1)).strftime("%Y-%m-%d")

    def start_date_int(self):
        """Gets start date as int."""
        return int(datetime.strptime(self.start_date, "%Y-%m-%d").astimezone().timestamp())

    def get_current_tickers(self):
        """Get tickers as today (excludes liquidity)."""
        return [x for x in self.data_content["status"]["last"]["stocks"] if x != "LIQUIDITY"]

    def get_current_tickers_and_liq(self):
        """Get current position (tickers + liquidity)."""
        return self.data_content["status"]["last"]["stocks"]

    def get_invested_cash(self, date: str) -> float:
        """Gets total invested cash until a certain date.

        Args:
            date: String with format YYYY-MM-DD to get invested cash up to that point.

        Returns:
            Float number with the invested cash up to that date.
        """
        deposits_dict = self.data_content["operations"]["deposit"]
        val = accum = 0
        for deposit_date in deposits_dict:
            if deposit_date > date:
                break
            val = deposits_dict[deposit_date]
            accum += val
        return accum

    def reload_data_file(self):
        """Re-loads data from JSON file and updates internal class dictionary."""
        with Path(self.loaded_data_path).open(encoding="utf8") as input_fh:
            self.data_content = json.load(input_fh)
            return True
        return False

    def load_data_file(self, data_file: str):
        """Loads data from JSON file.

        Args:
            data_file: String with path of JSON file.

        Returns:
            True if file loaded correctly. False otherwise.
        """
        with Path(data_file).open(encoding="utf8") as input_fh:
            self.data_content = json.load(input_fh)
            return True
        return False

    def load_total_investment(self):
        """Load initial investment data."""
        deposits_dict = self.data_content["operations"]["deposit"]
        accum = 0
        for deposit_date in deposits_dict:
            val = deposits_dict[deposit_date]
            accum += val
        self.total_invested = accum
        return self.total_invested

    def load_current_portfolio(self, blocking = True, callback = None):
        """Get total value of current portfolio.

        Args:
            data_file: String with path of JSON file.

        Returns:
            True if file loaded correctly. False otherwise.
        """
        self.current_portfolio = {}
        tickers = self.get_current_tickers()
        if blocking:
            self.get_tickers_value(tickers, force_load=True) #This function queries yFinance and takes some time
            self.reload_current_portfolio_data()
        else:
            self.gen_thread = QThread()
            self.gen_worker = FinanceLoadWorker(self,tickers)
            self.gen_worker.moveToThread(self.gen_thread)
            self.gen_thread.started.connect(self.gen_worker.get_tickers_value)
            self.gen_worker.finished.connect(self.reload_current_portfolio_data)
            if callback:
                self.gen_worker.finished.connect(callback)
            self.gen_worker.finished.connect(self.gen_worker.deleteLater)
            self.gen_worker.finished.connect(self.gen_thread.quit)
            self.gen_thread.start()
        return True

    def reload_current_portfolio_data(self):
        """Update portfolio chart and data."""
        accum = 0
        current_positions_dict = self.data_content["status"]["last"]["stocks"]
        for stock, qty in current_positions_dict.items():
            stock_value = self.get_last_price(stock)
            stock_value_total = stock_value * qty
            self.current_portfolio[stock] = {
                "qty": qty,
                "total": stock_value_total,
            }
            accum += stock_value_total
        self.current_portfolio_value = accum
        return True

    def get_current_portfolio_value(self):
        """Get total value of current portfolio."""
        return self.current_portfolio_value

    def get_current_portfolio_tickers_info(self):
        """Get current position in each ticker."""
        return self.current_portfolio

    def get_tickers_value(self, tickers: list, force_load: bool = False) -> DataFrame:
        """Get the value of the tickers on memory (if loaded) or from Yahoo Finance.

        Args:
            tickers: List containing name of tickers .
            force_load: If True, it will always fetch data from Yahoo Finance. If False, data is reused from a previous fetch (if available).

        Returns:
            A dataframe with historical price for each ticker.
        """
        force_load_ = force_load
        for ticker in tickers:
            if ticker not in self.historical_price_df and ticker != "LIQUIDITY":
                self.used_tickers.add(ticker)
                force_load_ = True
        if force_load_:
            ticker_historic_info = yfinance.Tickers(" ".join(self.used_tickers)).history(interval="1d", start=self.start_date, end=self.tomorrow())
            self.historical_price_df = ticker_historic_info.iloc[:]["Close"]
        return self.historical_price_df

    def get_price(self, ticker: str, date: str):
        """Get close price of a ticker on an specific date.

        Args:
            ticker: String with name of the ticker.
            date: String with the date, in format YYYY-MM-DD.

        Returns:
            A float with the price at that date.
        """
        if ticker == "LIQUIDITY":
            return 1
        if ticker in self.historical_price_df:
            if date in self.historical_price_df[ticker]:
                price = self.historical_price_df[ticker][date]
                return price
            for i in range(1, 5):  # Go up to 5 days before (to avoid weekends and holidays)
                date_ = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
                if date_ in self.historical_price_df[ticker]:
                    price = self.historical_price_df[ticker][date_]
                    return price
        self.__class__.logger.error(f"Cannot get {date} price of {ticker}")
        return 0

    def get_last_price(self, ticker: str):
        """Get close price of a ticker on an specific date.

        Args:
            ticker: String with name of ticker.

        Returns:
            A float with last price (at close or live price if market is open).
        """
        if ticker == "LIQUIDITY":
            return 1
        if ticker in self.historical_price_df:
            return self.historical_price_df[ticker][-1]
        self.__class__.logger.error(f"Cannot get last price of {ticker}")
        return 0

    @property
    def pandl(self):
        """Get P&L."""
        return self.current_portfolio_value - self.total_invested

    @property
    def pandl_percentage(self):
        """Get P&L percentage."""
        return round((self.current_portfolio_value / self.total_invested - 1) * 100, 2)

    @staticmethod
    def get_price_color(price:float):
        """Returns a color based on the price. Green if > 0. Red if < 0, black otherwise."""
        if price > 0:
            return "#0ec43e"
        if price < 0 :
            return "#de0700"
        return "#000000"


class TickerObject:
    """Object for each independent ticker."""

    tickers_index: dict = {}
    cost: float = 0
    qty: int = 0
    value: float = 0
    name: str = ""

    # Set-up logger
    logger = logging.getLogger("TickerObject")

    def __init__(self, name: str):
        """Constructor."""
        self.name = name
        if name in TickerObject.tickers_index:
            self.__class__.logger.warning(f"Redefining {name} item.")
        TickerObject.tickers_index[name] = self

    def update_qty(self, new_qty: int, price: float):
        """Updates quantity and cost basis of each ticker.

        Args:
            new_qty: Integer that specifies number of units of the ticker.
            price: Float that specifies the unit price of the ticker.

        Returns:
            True if new quantity is different than previous. False otherwise.
        """
        delta_qty = new_qty - self.qty
        if delta_qty != 0:
            self.cost += delta_qty * price
            self.cost += 1  # Most brokers charge $1 per transaction
        self.qty += delta_qty
        self.value = self.qty * price
        return delta_qty != 0

    def get_pandl(self):
        """Get Profit and Loss of a Ticker."""
        return self.value - self.cost

    def get_pandl_percentage(self):
        """Get Profit and Loss (in percentage) of a Ticker."""
        if self.cost <= 0:
            self.__class__.logger.error(f"Error with Ticker {self.name}. Cost not valid (cost={self.cost})")
            return f"{self.cost}"
        return f"{self.get_pandl()/self.cost*100.0:.2f}"

    @staticmethod
    def get_ticker_object(name: str):
        """Get any ticker object by name. If object is not found, create it.

        Args:
            name: String with name of ticker object.

        Returns:
            A TickerObject related with the specified ticker.
        """
        obj = None
        if name in TickerObject.tickers_index:
            obj = TickerObject.tickers_index[name]
        else:
            obj = TickerObject(name)
            TickerObject.tickers_index[name] = obj
        return obj

    @staticmethod
    def get_tickers():
        """Get name of all the tickers created."""
        return [obj.name for obj in TickerObject.tickers_index]

    @staticmethod
    def get_tickers_iterator():
        """Get tickers iterator."""
        yield from TickerObject.tickers_index.values()

    @staticmethod
    def reset_all():
        """Reset cost,qty,value,etc of each ticker."""
        TickerObject.logger.warning("Resetting all tickers")
        for obj in TickerObject.get_tickers_iterator():
            obj.qty = 0
            obj.cost = 0
            obj.value = 0
