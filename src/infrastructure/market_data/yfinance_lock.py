"""Shared lock for yfinance requests to ensure thread safety."""
import threading

yfinance_lock = threading.Lock()
