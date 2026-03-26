"""
calculator.py — Universal Lot Size Calculator

Universal Logic Matrix (USD account base):

  Group 1 — XXX/USD & Metals (USD as quote)
    pip_value = contract_size × pip_size
    Result: always fixed in USD
    • EUR/USD: 100,000 × 0.0001 = $10.00/lot
    • XAU/USD:     100 × 0.1    = $10.00/lot
    • XAG/USD:   5,000 × 0.01   = $50.00/lot

  Group 2 — USD/XXX (USD as base)
    pip_value = (contract_size × pip_size) / pair_rate
    • USD/JPY @150: (100,000 × 0.01) / 150  = $6.67/lot
    • USD/CHF @0.9: (100,000 × 0.0001) / 0.9 = $11.11/lot

  Group 3 — Cross pairs WITHOUT JPY (XXX/YYY)
    pip_value = contract_size × pip_size × YYY/USD_rate
    If only USD/YYY available: contract_size × pip_size / USD/YYY_rate
    • EUR/GBP @0.854, GBP/USD=1.27: 100,000 × 0.0001 × 1.27 = $12.70/lot
    • GBP/CAD @1.72, USD/CAD=1.36:  100,000 × 0.0001 / 1.36 =  $7.35/lot

  Group 4 — Cross pairs WITH JPY (XXX/JPY)
    pip_value = (contract_size × 0.01) / USD/JPY_rate
    • EUR/JPY, USD/JPY=150: (100,000 × 0.01) / 150 = $6.67/lot
    • GBP/JPY, USD/JPY=150: (100,000 × 0.01) / 150 = $6.67/lot
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from .price_provider import PAIR_META


# ---------------------------------------------------------------------------
# Group classification
# ---------------------------------------------------------------------------

def _pair_group(symbol: str) -> int:
    """
    Group 1: XXX/USD & metals      — pip_value = contract × pip_size (fixed USD)
    Group 2: USD/XXX               — pip_value = (contract × pip_size) / pair_rate
    Group 3: Cross, no JPY (XXX/YYY) — pip_value = contract × pip_size × YYY/USD
    Group 4: Cross JPY (XXX/JPY)   — pip_value = (contract × pip_size) / USD/JPY
    """
    base, quote = symbol[:3], symbol[3:]
    if quote == "USD":
        return 1
    if base == "USD":
        return 2
    if quote == "JPY":
        return 4
    return 3


# ---------------------------------------------------------------------------
# Core dataclass
# ---------------------------------------------------------------------------

@dataclass
class CalcResult:
    lot_size: float
    pip_value_per_lot: float  # in USD
    pair: str
    sl_pips: float
    risk_usd: float
    source_rate: float
    group: int


# ---------------------------------------------------------------------------
# Pip value engine
# ---------------------------------------------------------------------------

def pip_value_per_lot(symbol: str, rates: dict, debug: bool = False) -> Optional[float]:
    """
    Return pip value (in USD) for ONE standard lot of *symbol*.
    Returns None if required rates are unavailable.
    """
    symbol = symbol.upper()
    meta = PAIR_META.get(symbol)
    if meta is None:
        return None

    pip_size: float = meta["pip"]
    lot_size: float = meta["lot"]
    group = _pair_group(symbol)

    current_rate = rates.get(symbol)
    if current_rate is None or current_rate == 0:
        if debug:
            print(f"[DEBUG] {symbol}: pair rate missing or zero → None")
        return None

    if debug:
        print(f"\n{'='*60}")
        print(f"[DEBUG] Pip Value Audit: {symbol}")
        print(f"[DEBUG]   Group      : {group}")
        print(f"[DEBUG]   pip_size   : {pip_size}")
        print(f"[DEBUG]   lot_size   : {lot_size:,}")
        print(f"[DEBUG]   pair rate  : {current_rate}")

    # ------------------------------------------------------------------
    # Group 1 — XXX/USD & metals: pip_value = contract × pip_size
    # ------------------------------------------------------------------
    if group == 1:
        pv = pip_size * lot_size
        if debug:
            print(f"[DEBUG]   Formula  : {pip_size} × {lot_size:,} = ${pv:.4f}/lot")
            print(f"{'='*60}")
        return pv

    # ------------------------------------------------------------------
    # Group 2 — USD/XXX: pip_value = (contract × pip_size) / pair_rate
    # ------------------------------------------------------------------
    if group == 2:
        pv = (pip_size * lot_size) / current_rate
        if debug:
            print(f"[DEBUG]   Formula  : ({pip_size} × {lot_size:,}) / {current_rate}")
            print(f"[DEBUG]            = {pip_size * lot_size} / {current_rate}")
            print(f"[DEBUG]            = ${pv:.4f}/lot")
            print(f"{'='*60}")
        return pv

    # ------------------------------------------------------------------
    # Group 3 — Cross pairs WITHOUT JPY (XXX/YYY)
    # pip_value = contract × pip_size × YYY/USD
    # Fallback : contract × pip_size / USD/YYY
    # ------------------------------------------------------------------
    if group == 3:
        quote = symbol[3:]
        quote_usd_sym = f"{quote}USD"    # preferred: GBPUSD, AUDUSD, etc.
        usd_quote_sym = f"USD{quote}"    # fallback:  USDCAD, USDCHF, etc.
        pip_in_quote  = pip_size * lot_size

        if quote_usd_sym in rates and rates[quote_usd_sym]:
            usd_per_quote = rates[quote_usd_sym]
            formula = f"{pip_in_quote} × rates['{quote_usd_sym}']={usd_per_quote:.5f}"
        elif usd_quote_sym in rates and rates[usd_quote_sym]:
            usd_per_quote = 1.0 / rates[usd_quote_sym]
            formula = f"{pip_in_quote} / rates['{usd_quote_sym}']={rates[usd_quote_sym]:.5f}"
        else:
            if debug:
                print(f"[DEBUG]   No {quote}/USD conversion rate available → None")
                print(f"{'='*60}")
            return None

        pv = pip_in_quote * usd_per_quote
        if debug:
            print(f"[DEBUG]   Formula  : {formula}")
            print(f"[DEBUG]            = ${pv:.4f}/lot")
            print(f"{'='*60}")
        return pv

    # ------------------------------------------------------------------
    # Group 4 — Cross pairs WITH JPY (XXX/JPY)
    # pip_value = (contract × pip_size) / USD/JPY_rate
    # USD/JPY rate is ALWAYS fetched directly — never derived
    # ------------------------------------------------------------------
    if group == 4:
        usdjpy_rate = rates.get("USDJPY")
        if not usdjpy_rate or usdjpy_rate == 0:
            if debug:
                print(f"[DEBUG]   USDJPY rate missing → None")
                print(f"{'='*60}")
            return None

        pv = (pip_size * lot_size) / usdjpy_rate
        if debug:
            print(f"[DEBUG]   Formula  : ({pip_size} × {lot_size:,}) / USDJPY={usdjpy_rate}")
            print(f"[DEBUG]            = {pip_size * lot_size} / {usdjpy_rate}")
            print(f"[DEBUG]            = ${pv:.4f}/lot")
            print(f"{'='*60}")
        return pv

    return None


# ---------------------------------------------------------------------------
# Lot size calculator
# ---------------------------------------------------------------------------

def calculate_lot_size(
    symbol: str,
    sl_pips: float,
    risk_usd: float,
    rates: dict,
) -> Optional[CalcResult]:
    """
    Calculate lot size to risk *risk_usd* USD with stop-loss of *sl_pips* pips.
    Uses 1 pip = pip_size (e.g. 20 pips = 20 × 0.0001 for 4-decimal pairs).
    Returns CalcResult or None if rates are missing.
    """
    if sl_pips <= 0 or risk_usd <= 0:
        raise ValueError("SL pips and Risk amount must be positive.")

    symbol = symbol.upper().replace("/", "")
    pv = pip_value_per_lot(symbol, rates, debug=True)

    print(f"[DEBUG] Lot Calculation: {symbol}")
    print(f"[DEBUG]   SL pips        = {sl_pips}")
    print(f"[DEBUG]   Risk USD       = ${risk_usd}")
    print(f"[DEBUG]   Pip value/lot  = ${pv:.4f}" if pv else "[DEBUG]   Pip value/lot  = N/A")
    if pv and pv > 0:
        raw_lot = risk_usd / (sl_pips * pv)
        print(f"[DEBUG]   = ${risk_usd} / ({sl_pips} pips × ${pv:.4f})")
        print(f"[DEBUG]   = ${risk_usd} / ${sl_pips * pv:.4f}")
        print(f"[DEBUG]   = {raw_lot:.6f} lots")
        print(f"[DEBUG]   ⇒ round to 0.01 = {round(raw_lot, 2)} lots\n")

    if pv is None or pv == 0:
        return None

    lot = risk_usd / (sl_pips * pv)
    lot = round(lot, 2)

    return CalcResult(
        lot_size=lot,
        pip_value_per_lot=round(pv, 4),
        pair=symbol,
        sl_pips=sl_pips,
        risk_usd=risk_usd,
        source_rate=rates.get(symbol, 0.0),
        group=_pair_group(symbol),
    )

