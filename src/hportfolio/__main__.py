#!/bin/env python
"""Module configuration file."""

import logging

from hportfolio import main_window

# Constant definitions
LOGGING_LEVEL = logging.INFO

def configure_loggers(level:int):
    """Configure loggers."""
    # Configure logging module
    logging.basicConfig(
        level=level,
        format="%(name)s - %(levelname)s - %(message)s"
    )
    # We don't want too much messages from yFinance. Put a fixed logging level
    yfinance_logger = logging.getLogger("yfinance")
    yfinance_logger.setLevel(logging.WARNING)

    print("") # Print a newline to make it look prettier on the console.  # noqa: FURB105
    logging.info("Initializing Historic Portfolio Tracker")

def launch_gui():
    """Launches Main GUI."""
    main_window.launch_gui()

if __name__ == "__main__":
    #Configure loggers according to desired level
    configure_loggers(LOGGING_LEVEL)

    #Launch GUI
    launch_gui()
