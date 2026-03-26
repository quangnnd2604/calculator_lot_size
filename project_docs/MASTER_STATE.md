# MASTER STATE — FX Lot Master

_Last updated: 2026-03-20 — Session 3: TP/Profit/R:R feature added._

## Current Status
- **Phase**: Feature complete ✅
- Universal Logic Matrix (4-group) calculator ✅
- Take Profit / Profit target / R:R calculation ✅
- Colour-coded results (Lot=gold, Risk=red, Profit=green, R:R=amber) ✅
- 70 unit tests, all passing ✅
- `.app` bundle built via PyInstaller ✅

## Quick Start
```bash
# macOS
./setup.sh
source venv/bin/activate
python main.py

# Windows
setup.bat
venv\Scripts\activate
python main.py
```

## Project Structure (on disk — verified 2026-03-20)
```
calculator_lot_size/
├── project_docs/
│   ├── MASTER_STATE.md      ← THIS FILE
│   ├── DEVELOPMENT_LOG.md   ← Session log
│   └── TECHNICAL_STACK.md  ← Env, libraries, build commands
├── src/
│   ├── __init__.py
│   ├── price_provider.py    ← Hybrid data (ExchangeRate-API → yfinance), 60s refresh
│   ├── calculator.py        ← Pip value + lot size logic (3 groups)
│   └── ui.py                ← CustomTkinter UI (dark/light, dashboard, status bar)
├── main.py                  ← Entry point
├── requirements.txt         ← Python dependencies
├── setup.sh                 ← macOS venv setup (chmod +x already applied)
├── setup.bat                ← Windows venv setup
├── fx_lot_master.spec       ← PyInstaller (outputs .app on mac, .exe on Windows)
├── conftest.py               ← pytest root path config
├── pytest.ini                ← pytest settings (testpaths, addopts)
└── tests/
    ├── __init__.py
    ├── test_calculator.py    ← 32 tests: pip value Groups 1/2/3, lot size, edge cases, UI format
    └── test_price_provider.py ← 23 tests: API fetch, 403/500 fallback, state, rate building
```

## Supported Currency Pairs (30 total)

### Group 1 — USD Quote (pip value = 10 / 100000 * lot * 100000)
Direct: EUR/USD, GBP/USD, AUD/USD, NZD/USD, XAU/USD, XAG/USD

### Group 2 — USD Base (pip value = (10 / rate) per standard lot)
USD/JPY, USD/CHF, USD/CAD, USD/SEK, USD/NOK, USD/DKK, USD/SGD, USD/HKD, USD/ZAR, USD/MXN

### Group 3 — Cross Pairs (pip value calculated via USD conversion rates)
EUR/JPY, EUR/GBP, EUR/CHF, EUR/CAD, EUR/AUD, EUR/NZD,
GBP/JPY, GBP/CHF, GBP/CAD, AUD/JPY, NZD/JPY, CHF/JPY

## Pip Value Logic

### Standard lot = 100,000 units (metals: 100 oz for XAU, 5000 oz for XAG)

**Group 1 (USD as quote):**
```
pip_value = (pip_size / current_price) * lot_size * current_price
          = pip_size * lot_size
# For most pairs: pip_size=0.0001, XAU pip_size=0.01, XAG pip_size=0.001
pip_value_per_lot = 10 USD  (for standard 4-decimal pairs)
```

**Group 2 (USD as base):**
```
pip_value_per_lot = (pip_size * lot_size) / current_price
# e.g. USD/JPY rate=150: pip_value = (0.01 * 100000) / 150 = $6.67
```

**Group 3 (Cross pairs):**
```
# Convert pip value to USD via the quote currency's rate against USD
pip_value_per_lot = (pip_size * lot_size) * (USD/quote_currency rate)
```

## Lot Size Formula
```
lot_size = risk_usd / (sl_pips * pip_value_per_lot)
lot_size = round(lot_size, 2)
```

## API Key Configuration
- Set env var before running: `export EXCHANGERATE_API_KEY=your_key_here`
- Free key: https://www.exchangerate-api.com/
- Without a key → app silently falls back to yfinance (no crash)

## Test Suite
```bash
# macOS / Linux
source venv/bin/activate
python -m pytest          # run all 55 tests
python -m pytest -v       # verbose output
python -m pytest tests/test_calculator.py    # only calculator tests
python -m pytest tests/test_price_provider.py # only provider tests

# Windows
venv\Scripts\activate
python -m pytest
```

## Next Steps (Session 3)
- [ ] Fix black screen UI on macOS Python 3.9 (install Python 3.11 via python.org)
- [ ] Test build with `pyinstaller fx_lot_master.spec`
- [ ] Add icon (.icns for mac, .ico for Windows) to spec file
- [ ] Add pytest-cov for coverage report
