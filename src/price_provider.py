"""
price_provider.py — Hybrid price fetching module
Priority 1: ExchangeRate-API (free tier)
Priority 2: yfinance fallback
Auto-refresh every 60 seconds via background thread.
"""

import os
import time
import threading
import logging
from typing import Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pair metadata: maps canonical symbol → yfinance ticker + pip size
# ---------------------------------------------------------------------------
PAIR_META: Dict[str, dict] = {
    # Group 1 — USD as quote
    "EURUSD": {"yf": "EURUSD=X", "pip": 0.0001, "lot": 100_000},
    "GBPUSD": {"yf": "GBPUSD=X", "pip": 0.0001, "lot": 100_000},
    "AUDUSD": {"yf": "AUDUSD=X", "pip": 0.0001, "lot": 100_000},
    "NZDUSD": {"yf": "NZDUSD=X", "pip": 0.0001, "lot": 100_000},
    "XAUUSD": {"yf": "GC=F",     "pip": 0.1,    "lot": 100},    # 100 oz × 0.1  = $10/lot
    "XAGUSD": {"yf": "SI=F",     "pip": 0.01,   "lot": 5_000}, # 5000 oz × 0.01 = $50/lot
    # Group 2 — USD as base
    "USDJPY": {"yf": "USDJPY=X", "pip": 0.01,   "lot": 100_000},
    "USDCHF": {"yf": "USDCHF=X", "pip": 0.0001, "lot": 100_000},
    "USDCAD": {"yf": "USDCAD=X", "pip": 0.0001, "lot": 100_000},
    "USDSEK": {"yf": "USDSEK=X", "pip": 0.0001, "lot": 100_000},
    "USDNOK": {"yf": "USDNOK=X", "pip": 0.0001, "lot": 100_000},
    "USDDKK": {"yf": "USDDKK=X", "pip": 0.0001, "lot": 100_000},
    "USDSGD": {"yf": "USDSGD=X", "pip": 0.0001, "lot": 100_000},
    "USDHKD": {"yf": "USDHKD=X", "pip": 0.0001, "lot": 100_000},
    "USDZAR": {"yf": "USDZAR=X", "pip": 0.0001, "lot": 100_000},
    "USDMXN": {"yf": "USDMXN=X", "pip": 0.0001, "lot": 100_000},
    # Group 3 — Cross pairs
    "EURJPY": {"yf": "EURJPY=X", "pip": 0.01,   "lot": 100_000},
    "EURGBP": {"yf": "EURGBP=X", "pip": 0.0001, "lot": 100_000},
    "EURCHF": {"yf": "EURCHF=X", "pip": 0.0001, "lot": 100_000},
    "EURCAD": {"yf": "EURCAD=X", "pip": 0.0001, "lot": 100_000},
    "EURAUD": {"yf": "EURAUD=X", "pip": 0.0001, "lot": 100_000},
    "EURNZD": {"yf": "EURNZD=X", "pip": 0.0001, "lot": 100_000},
    "GBPJPY": {"yf": "GBPJPY=X", "pip": 0.01,   "lot": 100_000},
    "GBPCHF": {"yf": "GBPCHF=X", "pip": 0.0001, "lot": 100_000},
    "GBPCAD": {"yf": "GBPCAD=X", "pip": 0.0001, "lot": 100_000},
    "AUDJPY": {"yf": "AUDJPY=X", "pip": 0.01,   "lot": 100_000},
    "NZDJPY": {"yf": "NZDJPY=X", "pip": 0.01,   "lot": 100_000},
    "CHFJPY": {"yf": "CHFJPY=X", "pip": 0.01,   "lot": 100_000},
    "CADJPY": {"yf": "CADJPY=X", "pip": 0.01,   "lot": 100_000},
    "GBPAUD": {"yf": "GBPAUD=X", "pip": 0.0001, "lot": 100_000},
    "GBPNZD": {"yf": "GBPNZD=X", "pip": 0.0001, "lot": 100_000},
    "AUDNZD": {"yf": "AUDNZD=X", "pip": 0.0001, "lot": 100_000},
    "AUDCAD": {"yf": "AUDCAD=X", "pip": 0.0001, "lot": 100_000},
    "AUDCHF": {"yf": "AUDCHF=X", "pip": 0.0001, "lot": 100_000},
    "NZDCAD": {"yf": "NZDCAD=X", "pip": 0.0001, "lot": 100_000},
    "NZDCHF": {"yf": "NZDCHF=X", "pip": 0.0001, "lot": 100_000},
    "CADCHF": {"yf": "CADCHF=X", "pip": 0.0001, "lot": 100_000},
}

# Pairs needed to convert cross-pair pip values to USD
_USD_CONVERSION_PAIRS = [
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
    "USDJPY", "USDCHF", "USDCAD",
]

DASHBOARD_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD", "USDCHF"]

REFRESH_INTERVAL = 60  # seconds


class PriceProvider:
    """
    Thread-safe hybrid price provider.
    Fetches from ExchangeRate-API first; falls back to yfinance.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("EXCHANGERATE_API_KEY", "26a8636970883b643825cd66")
        self._rates: Dict[str, float] = {}
        self._source: str = "N/A"
        self._last_updated: float = 0.0
        self._lock = threading.RLock()
        self._callbacks = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start background refresh thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background refresh thread."""
        self._stop_event.set()

    def get_rate(self, symbol: str) -> Optional[float]:
        """Return latest rate for *symbol* (e.g. 'EURUSD')."""
        with self._lock:
            return self._rates.get(symbol.upper())

    def get_all_rates(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._rates)

    def get_status(self) -> Tuple[str, float]:
        """Return (source_label, timestamp_of_last_update)."""
        with self._lock:
            return self._source, self._last_updated

    def on_update(self, callback):
        """Register a callable invoked after each successful refresh."""
        self._callbacks.append(callback)

    def force_refresh(self):
        """Trigger an immediate refresh (blocking)."""
        self._do_refresh()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh_loop(self):
        while not self._stop_event.is_set():
            self._do_refresh()
            # Sleep in small increments so stop_event is checked promptly
            for _ in range(REFRESH_INTERVAL * 10):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)

    def _do_refresh(self):
        rates, source = self._fetch_api()
        if not rates:
            rates, source = self._fetch_yfinance()
        if rates:
            with self._lock:
                self._rates.update(rates)
                self._source = source
                self._last_updated = time.time()
            for cb in self._callbacks:
                try:
                    cb()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Fetcher 1 — ExchangeRate-API (free tier: /latest/USD)
    # ------------------------------------------------------------------

    def _fetch_api(self) -> Tuple[Dict[str, float], str]:
        if not self._api_key:
            return {}, ""
        try:
            url = f"https://v6.exchangerate-api.com/v6/{self._api_key}/latest/USD"
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") != "success":
                return {}, ""
            usd_rates: dict = data["conversion_rates"]  # e.g. {"EUR": 0.92, "JPY": 150, ...}
            return self._build_rates_from_usd_base(usd_rates), "ExchangeRate-API"
        except Exception as exc:
            logger.warning("ExchangeRate-API error: %s", exc)
            return {}, ""

    def _build_rates_from_usd_base(self, usd_rates: dict) -> Dict[str, float]:
        """Convert a USD-based rate table into all required pair rates."""
        rates: Dict[str, float] = {}
        for symbol in PAIR_META:
            base = symbol[:3]
            quote = symbol[3:]
            if base == "XAU" or base == "XAG":
                # These are not in ExchangeRate-API free tier; skip
                continue
            try:
                if base == "USD":
                    rates[symbol] = usd_rates[quote]
                elif quote == "USD":
                    rates[symbol] = 1.0 / usd_rates[base]
                else:
                    # Cross: base/quote = (USD/quote) / (USD/base)
                    rates[symbol] = usd_rates[quote] / usd_rates[base]
            except (KeyError, ZeroDivisionError):
                pass
        return rates

    # ------------------------------------------------------------------
    # Fetcher 2 — yfinance fallback
    # ------------------------------------------------------------------

    def _fetch_yfinance(self) -> Tuple[Dict[str, float], str]:
        try:
            import yfinance as yf  # lazy import — not available at package level

            tickers = [meta["yf"] for meta in PAIR_META.values()]
            data = yf.download(
                tickers,
                period="1d",
                interval="1m",
                progress=False,
                auto_adjust=True,
                threads=True,
            )
            rates: Dict[str, float] = {}
            close = data.get("Close") if hasattr(data, "get") else data["Close"]
            for symbol, meta in PAIR_META.items():
                ticker = meta["yf"]
                try:
                    price = float(close[ticker].dropna().iloc[-1])
                    rates[symbol] = price
                except Exception:
                    pass
            return rates, "yfinance"
        except Exception as exc:
            logger.error("yfinance fallback error: %s", exc)
            return {}, "ERROR"
