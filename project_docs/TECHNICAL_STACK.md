# TECHNICAL STACK — FX Lot Master

## Environment
- Python: 3.11+
- Packaging: PyInstaller 6.x
- Target OS: macOS 12+ / Windows 10+

## Dependencies
| Package | Version | Purpose |
|---|---|---|
| customtkinter | >=5.2.2 | Modern dark/light UI |
| requests | >=2.31 | ExchangeRate-API HTTP calls |
| yfinance | >=0.2.40 | Fallback price scraping |
| beautifulsoup4 | >=4.12 | HTML parsing (future scraping) |
| lxml | >=5.1 | Fast XML/HTML parser for BS4 |
| Pillow | >=10.0 | CustomTkinter image support |

## API Keys
- ExchangeRate-API: Free tier at https://www.exchangerate-api.com/
  - Set env var: `EXCHANGERATE_API_KEY=your_key_here`
  - Or hardcode fallback key in price_provider.py (rotate if rate-limited)

## Build Commands

### macOS
```bash
source venv/bin/activate
pyinstaller fx_lot_master.spec
# Output: dist/FX Lot Master.app
```

### Windows
```bat
venv\Scripts\activate
pyinstaller fx_lot_master.spec
:: Output: dist\FX Lot Master.exe
```

## PyInstaller Notes
- Use `--windowed` to suppress console on both platforms
- Bundle CustomTkinter themes: add `--collect-data customtkinter`
- Hidden imports needed: `customtkinter`, `yfinance`, `requests`
