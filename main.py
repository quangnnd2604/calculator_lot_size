"""
main.py — Entry point for FX Lot Master.
"""

import os
import sys
import logging

# Ensure src/ is importable when run from project root
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

from src.price_provider import PriceProvider
from src.ui import FXLotMasterApp


def main():
    # API key: set EXCHANGERATE_API_KEY in environment, or replace "" with your key.
    api_key = os.environ.get("EXCHANGERATE_API_KEY", "")

    provider = PriceProvider(api_key=api_key)
    provider.start()  # start background 60s refresh thread

    # Kick off an initial fetch before showing window
    import threading
    def _initial_fetch():
        provider.force_refresh()
        rates = provider.get_all_rates()
        source, ts = provider.get_status()
        print(f"\n[STARTUP] Price source: {source}")
        print(f"[STARTUP] Key rates loaded:")
        for pair in ["EURUSD", "USDJPY", "EURJPY", "GBPUSD", "GBPJPY", "XAUUSD"]:
            v = rates.get(pair, "N/A")
            print(f"  {pair:10s} = {v}")
        print()
    threading.Thread(target=_initial_fetch, daemon=True).start()

    app = FXLotMasterApp(provider)
    try:
        app.mainloop()
    finally:
        provider.stop()


if __name__ == "__main__":
    main()
