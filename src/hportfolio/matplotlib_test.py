import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor, SpanSelector

# Define the ticker symbol
tickerSymbol = "AAPL"

# Get the data for the ticker
tickerData = yf.Ticker(tickerSymbol)


# Define a function to update the plot based on the selected date range
def update_plot(start_date, end_date):
    # Get the data for the selected date range
    tickerDf = tickerData.history(start=start_date, end=end_date, interval="1d")

    # Plot the closing prices
    plt.plot(tickerDf.index, tickerDf["Close"])
    plt.xlabel("Date")
    plt.ylabel("Closing Price")
    plt.title(f"Historical Price Data for {tickerSymbol}")
    plt.show()


# Define a function to handle the SpanSelector event
def onselect(xmin, xmax):
    start_date = pd.Timestamp(xmin).strftime("%Y-%m-%d")
    end_date = pd.Timestamp(xmax).strftime("%Y-%m-%d")
    update_plot(start_date, end_date)


# Get the full data for the ticker
fullData = tickerData.history()

# Plot the full data
update_plot(fullData.index.min().strftime("%Y-%m-%d"), fullData.index.max().strftime("%Y-%m-%d"))

# Add a SpanSelector to allow the user to select a date range
span = SpanSelector(plt.gca(), onselect, "horizontal", useblit=True)  # rectprops=dict(alpha=0.5, facecolor='blue'))
plt.show()
