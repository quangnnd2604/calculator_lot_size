# DEVELOPMENT LOG — FX Lot Master

## Session 1 — 2026-03-20

### Completed
- [x] Created project_docs: MASTER_STATE.md, DEVELOPMENT_LOG.md, TECHNICAL_STACK.md
- [x] Built `src/price_provider.py`: Hybrid fetcher (ExchangeRate-API → yfinance fallback), 60s auto-refresh
- [x] Built `src/calculator.py`: Pip value logic for Groups 1/2/3, lot size formula
- [x] Built `src/ui.py`: CustomTkinter dark/light UI, left panel inputs, right panel rate dashboard, status bar
- [x] Created `main.py` entry point
- [x] Created `requirements.txt`
- [x] Created `setup.sh` (macOS) and `setup.bat` (Windows)
- [x] Created `fx_lot_master.spec` for PyInstaller

### What to do next (Session 2 → done in same session)
- [x] Install dependencies via setup.sh
- [x] Write Unit Tests

## Session 2 — 2026-03-20

### Completed
- [x] Ran `./setup.sh` → venv created, all dependencies installed successfully
- [x] Inserted ExchangeRate-API key into `price_provider.py`
- [x] Launched app (`python main.py`) — window opens (black screen issue on macOS Python 3.9/Tk 8.5 — pending fix)
- [x] Created `tests/test_calculator.py` — 32 test cases across 7 classes
- [x] Created `tests/test_price_provider.py` — 23 test cases across 5 classes
- [x] Created `conftest.py` and `pytest.ini`
- [x] Added `pytest>=8.0.0` and `pytest-mock>=3.14.0` to `requirements.txt`
- [x] **Result: 55/55 tests PASSED ✅ in 0.32s**

### What to do next (Session 3)
- [ ] Fix black screen: install Python 3.11+ from python.org (system Tk 8.5 on macOS 3.9 incompatible with CustomTkinter)
- [ ] Add keyboard shortcut Enter → Calculate
- [ ] Add "Copy Result" button
- [ ] Test PyInstaller build
- [ ] Code-sign .app for macOS Gatekeeper
