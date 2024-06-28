"""Classes related with main graphic interface."""
import logging
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtChart import QChart, QChartView, QDateTimeAxis, QLineSeries, QValueAxis
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QKeyEvent, QPainter
from PyQt5.QtWidgets import QLabel, QSizePolicy, QTableWidget, QTableWidgetItem

from hportfolio.crosshair import Crosshairs
from hportfolio.gui import main_window
from hportfolio.tickers_data import TickerObject, TickersData

# Constants definition
BASEPATH = str(Path(__file__ + "/../").resolve())
RES_PATH = BASEPATH + "/res"
DATA_PATH = BASEPATH + "/data"
ONE_DAY_IN_SECONDS = 86400

class CustomChartView(QChartView):
    """Custom chart view for adding additional features like hotkeys and crosshair."""

    def __init__(self, chart: QChart, tickers_data: TickersData):
        """Constructor."""
        super().__init__(chart)
        self.crosshair = Crosshairs(chart, self.scene(), tickers_data)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        """Mouse move event override."""
        super().mouseMoveEvent(event)
        self.crosshair.update_position(event.pos())

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """Hotkeys implementation."""
        if event.key() == ord("F"):
            self.chart().zoomReset()

        return super().keyPressEvent(event)


class MainWindow(QtWidgets.QMainWindow, main_window.Ui_MainWindow):
    """Main app window class."""

    def __init__(self, *args, **kwargs):
        """Main Window Constructor."""
        QtWidgets.QMainWindow.__init__(self, *args, **kwargs)
        self.setupUi(self)

        # Connections
        self.plot_status_reload_BTN.clicked.connect(self.reload_stock_data)
        self.data_reload_BTN.clicked.connect(self.reload_stock_data)

        # Tickers data
        self.tickers_data = TickersData(DATA_PATH + "/data.json",self.update_gui)

        # Create QChart
        self.plot_chart = QChart()
        # self.plot_chart.setAnimationOptions(QChart.AllAnimations)

        # Create the plot widget and add it to the plot tab
        self.chart_view = CustomChartView(self.plot_chart, self.tickers_data)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.chart_view.setRubberBand(QChartView.RectangleRubberBand)
        self.chart_view.setDragMode(QChartView.RubberBandDrag)

        self.plot_chart_container.addWidget(self.chart_view)
        # self.plot_layout.setDragMode(QChartView.ScrollHandDrag)

        # Create the plot series and add it to the plot widget
        self.series_initial_investment = QLineSeries()
        self.series_initial_investment.setPointLabelsVisible(True)  # noqa: FBT003
        self.series_initial_investment.setPointLabelsFormat("@yPoint")
        self.series_portfolio_total = QLineSeries()
        self.series_portfolio_total.setPointsVisible(True)  # noqa: FBT003
        self.plot_chart.addSeries(self.series_initial_investment)
        self.plot_chart.addSeries(self.series_portfolio_total)

        # X axis configuration
        self.axis_x = QDateTimeAxis()
        self.axis_x.setTickCount(24)
        self.axis_x.setFormat("MM-dd-yyyy")
        my_font = QtGui.QFont()
        my_font.setPointSize(9)
        self.axis_x.setLabelsFont(my_font)
        self.axis_x.setLabelsAngle(-90)
        self.axis_x.setTitleText("Date")
        self.plot_chart.addAxis(self.axis_x, Qt.AlignBottom)

        # Y axis configuration
        self.axis_y = QValueAxis()
        self.axis_y.setTickCount(10)
        self.axis_y.setLabelFormat("%d")
        self.axis_y.setTitleText("Cash")
        self.plot_chart.addAxis(self.axis_y, Qt.AlignLeft)

        # Attach axis to each series
        self.series_portfolio_total.attachAxis(self.axis_x)
        self.series_portfolio_total.attachAxis(self.axis_y)
        self.series_initial_investment.attachAxis(self.axis_x)
        self.series_initial_investment.attachAxis(self.axis_y)

        # Configure name of each series
        self.series_portfolio_total.setName("Portfolio")
        self.series_initial_investment.setName("Investment")

        # Initialize variables used for summary view
        self.stock_labels = []
        self.current_money = 0
        self.initial_investment = 0
        self.pandl = 0
        self.load_line_chart(self.tickers_data)

    def reload_stock_table(self):
        """Reload table on Data tab of GUI."""
        self.data_TABLE.setRowCount(0)
        tickers_data: TickersData = self.tickers_data
        historic_data = tickers_data.data_content["status"]
        stocks_ = historic_data["last"]["stocks"]
        total_sum = total_pandl = total_cost_basis = total_sum_yesterday = 0
        for ticker, qty in stocks_.items():
            if qty<=0:
                continue
            value_ = tickers_data.get_price(ticker, tickers_data.today())
            value_yesterday = tickers_data.get_price(ticker, tickers_data.yesterday())
            daily_pandl = value_*qty-value_yesterday*qty
            ticker_obj = TickerObject.get_ticker_object(ticker)
            row_count = self.data_TABLE.rowCount()
            self.data_TABLE.insertRow(row_count)
            self.data_TABLE.setItem(row_count, 0, QTableWidgetItem(f"{ticker} ({qty})"))
            self.data_TABLE.setItem(row_count, 1, QTableWidgetItem(f"${value_:.2f}"))
            self.data_TABLE.setItem(row_count, 2, QTableWidgetItem(f"${value_*qty:.2f}"))
            self.data_TABLE.setItem(row_count, 3, QTableWidgetItem(f"${ticker_obj.cost}"))
            self.data_TABLE.setItem(row_count, 4, QTableWidgetItem(f"${ticker_obj.cost/ticker_obj.qty:.2f}"))
            self.data_TABLE.setItem(row_count, 5, QTableWidgetItem(f"${ticker_obj.get_pandl():.1f}"))
            self.data_TABLE.setItem(row_count, 6, QTableWidgetItem(f"{ticker_obj.get_pandl_percentage()}%"))
            self.data_TABLE.setItem(row_count, 7, QTableWidgetItem(f"${daily_pandl:.1f}"))
            if ticker=="LIQUIDITY":
                    continue
            total_sum += qty*value_
            total_sum_yesterday += qty*value_yesterday
            total_cost_basis += ticker_obj.cost
            total_pandl += ticker_obj.get_pandl()
            color = TickersData.get_price_color(ticker_obj.get_pandl())
            for column in range(self.data_TABLE.columnCount()-1):
                    self.data_TABLE.item(row_count, column).setBackground(QtGui.QColor(color))
            self.data_TABLE.item(row_count, 7).setBackground(QtGui.QColor(TickersData.get_price_color(daily_pandl)))

        row_count = self.data_TABLE.rowCount()
        self.data_TABLE.insertRow(row_count)
        self.data_TABLE.setItem(row_count, 0, QTableWidgetItem("Total:"))
        self.data_TABLE.setItem(row_count, 1, QTableWidgetItem("-"))
        self.data_TABLE.setItem(row_count, 2, QTableWidgetItem(f"${total_sum:.2f}"))
        self.data_TABLE.setItem(row_count, 3, QTableWidgetItem(f"${total_cost_basis:.2f}"))
        self.data_TABLE.setItem(row_count, 4, QTableWidgetItem("-"))
        self.data_TABLE.setItem(row_count, 5, QTableWidgetItem(f"${total_pandl:.2f}"))
        self.data_TABLE.setItem(row_count, 6, QTableWidgetItem(f"{100*total_pandl/total_cost_basis:.2f}%"))
        self.data_TABLE.setItem(row_count, 7, QTableWidgetItem(f"${total_sum-total_sum_yesterday:.1f}"))
        color = TickersData.get_price_color(total_pandl)
        for column in range(self.data_TABLE.columnCount()-1):
            self.data_TABLE.item(row_count, column).setBackground(QtGui.QColor(color))
        self.data_TABLE.item(row_count, 7).setBackground(QtGui.QColor(TickersData.get_price_color(total_sum-total_sum_yesterday)))

        self.data_TABLE.resizeColumnsToContents()
        self.data_TABLE.setSelectionBehavior(QTableWidget.SelectRows)

    def reload_stock_data(self):
        """Reload stock data in background (not blocking)."""
        self.tickers_data.reload_data_file()
        self.tickers_data.load_current_portfolio(blocking=False,callback=self.update_gui)

    def update_gui(self):
        """Update GUI once all the data was obtained from yFinance and files."""
        TickerObject.reset_all()
        self.plot_historic_portfolio(self.tickers_data)
        self.update_headers_stock_info(self.tickers_data)
        self.reload_stock_table()

    def load_line_chart(self, tickers_data: TickersData):
        """Loads line chart."""
        if tickers_data:
            self.plot_initial_investment(tickers_data.data_content["operations"]["deposit"])
            self.plot_status_iinvest_LBL.setText(f"Initial investment: ${tickers_data.total_invested}")
            self.plot_historic_portfolio(tickers_data)
            self.update_headers_stock_info(tickers_data)

    def update_headers_stock_info(self, tickers_data: TickersData):
        """Loads stock data."""
        current_portfolio = tickers_data.current_portfolio
        for my_lbl in self.stock_labels:
            self.plot_status_stocks_container.removeWidget(my_lbl)
            my_lbl.deleteLater()
            my_lbl = None  # noqa: PLW2901
        self.stock_labels = []

        cnt = 0
        for ticker in current_portfolio:
            lbl = QLabel()
            my_font = QtGui.QFont()
            my_font.setPointSize(8)
            lbl.setFont(my_font)
            lbl.setObjectName(f"plot_stock_lbl_{ticker}")
            self.plot_status_stocks_container.addWidget(lbl, int(cnt / 5), cnt % 5)
            self.stock_labels.append(lbl)
            past_ticker_price = tickers_data.get_price(ticker, tickers_data.yesterday())
            current_ticker_price = tickers_data.get_price(ticker, tickers_data.today())
            ticker_increase_percentage = round(((current_ticker_price - past_ticker_price) / past_ticker_price) * 100, 2)
            if ticker_increase_percentage > 0:
                str_modif = "+"
                color_modif = "0ec43e"
            elif ticker_increase_percentage < 0:
                str_modif = ""
                color_modif = "de0700"
            else:
                str_modif = ""
                color_modif = "000000"
            lbl.setText(f"<p style='color:#{color_modif}'>{ticker}({current_portfolio[ticker]['qty']}): ${round(current_ticker_price,1)} ({str_modif}{ticker_increase_percentage}%)</p>")
            cnt += 1
        self.plot_status_total_LBL.setText(f"Total: ${int(tickers_data.current_portfolio_value)}")
        self.plot_status_pl_LBL.setText(f"P&L: ${int(tickers_data.pandl)} ({tickers_data.pandl_percentage}%)")

    def plot_initial_investment(self, deposits_dict: dict):
        """Load initial investment data."""
        min_ = 1e20
        accum = 0
        for deposit_date in deposits_dict:
            q_date = QtCore.QDate.fromString(deposit_date, "yyyy-MM-dd")
            qdate = QtCore.QDateTime(q_date)
            if qdate.toMSecsSinceEpoch() < min_:
                min_ = qdate.toMSecsSinceEpoch()
                min_date = qdate
            val = deposits_dict[deposit_date]
            self.series_initial_investment.append(qdate.toMSecsSinceEpoch(), accum)
            accum += val
            self.series_initial_investment.append(qdate.toMSecsSinceEpoch(), accum)
        qcurrent_date = QtCore.QDateTime(QtCore.QDate().currentDate())
        self.series_initial_investment.append(qcurrent_date.toMSecsSinceEpoch(), accum)
        self.axis_x.setRange(min_date, qcurrent_date)
        self.axis_y.setRange(0, accum * 1.10)

    def plot_historic_portfolio(self, tickers_data: TickersData):
        """Line plot of historical value of portfolio over time."""
        self.series_portfolio_total.clear()
        historic_data = tickers_data.data_content["status"]
        for date_in_seconds in range(tickers_data.start_date_int(), tickers_data.today_int() + ONE_DAY_IN_SECONDS, ONE_DAY_IN_SECONDS):
            date_ = datetime.fromtimestamp(date_in_seconds).strftime("%Y-%m-%d")
            position_changed = False
            if date_ in historic_data or date_ == tickers_data.today():
                stocks_ = historic_data["last"]["stocks"] if date_ == tickers_data.today() else historic_data[date_]["stocks"]
                position_changed = True
            tickers_data.get_tickers_value(stocks_.keys())
            total_value = 0
            for ticker, qty in stocks_.items():
                value_ = tickers_data.get_price(ticker, date_)
                if position_changed:
                    ticker_obj = TickerObject.get_ticker_object(ticker)
                    ret_stat = ticker_obj.update_qty(qty, value_)  # noqa: F841
                total_value += value_ * qty
            q_date = QtCore.QDate.fromString(date_, "yyyy-MM-dd")
            qdate = QtCore.QDateTime(q_date)
            self.series_portfolio_total.append(qdate.toMSecsSinceEpoch(), total_value)

        if len(tickers_data.data_content["force_cost_basis"]) > 1:
            force_vals = tickers_data.data_content["force_cost_basis"]
            for ticker in historic_data["last"]["stocks"]:
                if ticker == "LIQUIDITY":
                    continue
                ticker_obj = TickerObject.get_ticker_object(ticker)
                if ticker in force_vals:
                    ticker_obj.cost = force_vals[ticker][1]

        for ticker in TickerObject.tickers_index:
            ticker_obj = TickerObject.get_ticker_object(ticker)
            ticker_obj.value = ticker_obj.qty * tickers_data.get_price(ticker, tickers_data.today())
            if ticker_obj.qty > 0:
                logging.info(f"-{ticker_obj.name}({ticker_obj.qty}) cost: {ticker_obj.cost:.2f}, {ticker_obj.value:.2f} (${ticker_obj.get_pandl():.2f} / {ticker_obj.get_pandl_percentage()}%)")

    def launch_worker(self, name: str, worker: Callable, finish_cb: Callable, progress_cb: Callable | None, *args, **kwargs):  # noqa: ANN002, ANN003
        """Generic function to launch a worker."""
        if name not in self.threads_dict or (self.threads_dict[name] and not self.threads_dict[name].isRunning()):
            qthread_ = QThread()
            qworker_ = worker(*args, **kwargs)
            qworker_.moveToThread(qthread_)
            qthread_.started.connect(worker.run_function)
            if progress_cb:
                qworker_.progress.connect(progress_cb)
            qworker_.finished.connect(finish_cb)
            qworker_.finished.connect(qthread_.quit)
            qworker_.finished.connect(qworker_.deleteLater)
            self.threads_dict[name] = qthread_
            self.workers_dict[name] = qworker_
            qthread_.start()


def launch_gui():
    """Launches GUI."""
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()

    # Exit status will depend on app exit status
    sys.exit(app.exec_())
