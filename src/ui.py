"""
ui.py — FX Lot Master: CustomTkinter main window.

Layout
──────
┌──────────────────────────┬──────────────────────────┐
│  LEFT PANEL              │  RIGHT PANEL             │
│  • Pair selector         │  • Dashboard (6 majors)  │
│  • SL pips input         │                          │
│  • Risk USD input        │                          │
│  • [Calculate] button    │                          │
│  • Result display        │                          │
└──────────────────────────┴──────────────────────────┘
│  STATUS BAR  (source • last update • auto-refresh)   │
└──────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import time
import tkinter as tk
from datetime import datetime
from typing import Optional

import customtkinter as ctk

from .price_provider import PAIR_META, DASHBOARD_PAIRS, PriceProvider
from .calculator import calculate_lot_size, CalcResult

# ── Appearance ──────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

import platform
_SYS = platform.system()
_FF = "SF Pro Display" if _SYS == "Darwin" else "Segoe UI"

_FONT_TITLE  = (_FF, 22, "bold")
_FONT_LABEL  = (_FF, 13)
_FONT_ENTRY  = (_FF, 13)
_FONT_RESULT = (_FF, 32, "bold")
_FONT_SMALL  = (_FF, 11)
_FONT_STATUS = (_FF, 10)

_ALL_PAIRS = sorted(PAIR_META.keys())


class FXLotMasterApp(ctk.CTk):
    def __init__(self, price_provider: PriceProvider):
        super().__init__()
        self.provider = price_provider
        self.provider.on_update(self._on_prices_updated)

        self.title("FX Lot Master")
        self.geometry("940x720")
        self.minsize(940, 720)
        self.resizable(True, False)
        self._build_ui()
        # Force full render before showing — fixes black screen on macOS Tk 8.5
        self.update()
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.after(100, self._update_dashboard)
        self._start_countdown()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)  # main content row expands

        # ── Title bar ────────────────────────────────────────────────────────
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=(18, 0), sticky="ew")
        ctk.CTkLabel(title_frame, text="FX Lot Master", font=_FONT_TITLE).pack(side="left")
        self._theme_btn = ctk.CTkButton(
            title_frame, text="☀ Light", width=90, height=28,
            font=_FONT_SMALL, command=self._toggle_theme,
        )
        self._theme_btn.pack(side="right")

        # Separator
        ctk.CTkFrame(self, height=1, fg_color=("gray70", "gray30")).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(8, 0)
        )

        # ── Left panel ───────────────────────────────────────────────────────
        left = ctk.CTkFrame(self, corner_radius=12)
        left.grid(row=2, column=0, padx=(20, 10), pady=15, sticky="nsew")
        self._build_left_panel(left)

        # ── Right panel ──────────────────────────────────────────────────────
        right = ctk.CTkFrame(self, corner_radius=12)
        right.grid(row=2, column=1, padx=(10, 20), pady=15, sticky="nsew")
        self._build_right_panel(right)

        # ── Status bar ───────────────────────────────────────────────────────
        status_frame = ctk.CTkFrame(self, height=30, fg_color=("gray85", "gray20"))
        status_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        status_frame.grid_columnconfigure(0, weight=1)
        self._status_var = tk.StringVar(value="Initializing…")
        ctk.CTkLabel(
            status_frame, textvariable=self._status_var,
            font=_FONT_STATUS, anchor="w",
        ).grid(row=0, column=0, padx=14, pady=4, sticky="w")
        self._countdown_var = tk.StringVar(value="")
        ctk.CTkLabel(
            status_frame, textvariable=self._countdown_var,
            font=_FONT_STATUS, anchor="e",
        ).grid(row=0, column=1, padx=14, pady=4, sticky="e")

    def _build_left_panel(self, parent: ctk.CTkFrame):
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text="Calculator", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, padx=20, pady=(16, 10), sticky="w"
        )

        # Pair
        ctk.CTkLabel(parent, text="Currency Pair", font=_FONT_LABEL).grid(
            row=1, column=0, padx=20, pady=(4, 0), sticky="w"
        )
        self._pair_var = tk.StringVar(value="EURUSD")
        self._pair_menu = ctk.CTkOptionMenu(
            parent, variable=self._pair_var, values=_ALL_PAIRS,
            width=220, font=_FONT_ENTRY,
        )
        self._pair_menu.grid(row=2, column=0, padx=20, pady=(4, 10), sticky="ew")

        # SL pips
        ctk.CTkLabel(parent, text="Stop Loss (Pips)", font=_FONT_LABEL).grid(
            row=3, column=0, padx=20, pady=(4, 0), sticky="w"
        )
        self._sl_entry = ctk.CTkEntry(
            parent, placeholder_text="e.g. 20", font=_FONT_ENTRY, width=220
        )
        self._sl_entry.grid(row=4, column=0, padx=20, pady=(4, 10), sticky="ew")

        # TP pips
        ctk.CTkLabel(parent, text="Take Profit (Pips)", font=_FONT_LABEL).grid(
            row=5, column=0, padx=20, pady=(4, 0), sticky="w"
        )
        self._tp_entry = ctk.CTkEntry(
            parent, placeholder_text="e.g. 40  (tuỳ chọn)", font=_FONT_ENTRY, width=220
        )
        self._tp_entry.grid(row=6, column=0, padx=20, pady=(4, 10), sticky="ew")

        # Risk USD
        ctk.CTkLabel(parent, text="Risk Amount (USD)", font=_FONT_LABEL).grid(
            row=7, column=0, padx=20, pady=(4, 0), sticky="w"
        )
        self._risk_entry = ctk.CTkEntry(
            parent, placeholder_text="e.g. 100", font=_FONT_ENTRY, width=220
        )
        self._risk_entry.grid(row=8, column=0, padx=20, pady=(4, 14), sticky="ew")

        # Calculate button
        self._calc_btn = ctk.CTkButton(
            parent, text="Calculate Lot Size", font=("Segoe UI", 14, "bold"),
            height=42, command=self._on_calculate
        )
        self._calc_btn.grid(row=9, column=0, padx=20, pady=(0, 14), sticky="ew")

        # Bind Enter key
        self.bind("<Return>", lambda _: self._on_calculate())

        # Separator
        ctk.CTkFrame(parent, height=1, fg_color=("gray70", "gray30")).grid(
            row=10, column=0, sticky="ew", padx=20, pady=(0, 12)
        )

        # ── Lot Size (highlighted gold/yellow) ─────────────────────────────
        ctk.CTkLabel(parent, text="SỐ LOT CẦN VÀO", font=_FONT_LABEL).grid(
            row=11, column=0, padx=20, pady=(0, 2), sticky="w"
        )
        self._result_var = tk.StringVar(value="—")
        ctk.CTkLabel(
            parent, textvariable=self._result_var,
            font=_FONT_RESULT, text_color=("#d97706", "#fbbf24"),
        ).grid(row=12, column=0, padx=20, pady=(0, 8), sticky="w")

        # ── Risk / Profit / R:R summary row ────────────────────────────────
        summary = ctk.CTkFrame(parent, fg_color="transparent")
        summary.grid(row=13, column=0, padx=20, pady=(0, 4), sticky="ew")
        summary.grid_columnconfigure((0, 1, 2), weight=1)

        # Risk (red)
        risk_col = ctk.CTkFrame(summary, fg_color="transparent")
        risk_col.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(risk_col, text="Số tiền rủi ro", font=_FONT_SMALL,
                     text_color=("gray50", "gray60")).pack(anchor="w")
        self._risk_display_var = tk.StringVar(value="—")
        ctk.CTkLabel(risk_col, textvariable=self._risk_display_var,
                     font=(_FF, 14, "bold"),
                     text_color=("#c62828", "#ef9a9a")).pack(anchor="w")

        # Profit (green)
        profit_col = ctk.CTkFrame(summary, fg_color="transparent")
        profit_col.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(profit_col, text="Mục tiêu lợi nhuận", font=_FONT_SMALL,
                     text_color=("gray50", "gray60")).pack(anchor="w")
        self._profit_var = tk.StringVar(value="—")
        ctk.CTkLabel(profit_col, textvariable=self._profit_var,
                     font=(_FF, 14, "bold"),
                     text_color=("#1b5e20", "#81c784")).pack(anchor="w")

        # R:R (amber)
        rr_col = ctk.CTkFrame(summary, fg_color="transparent")
        rr_col.grid(row=0, column=2, sticky="w")
        ctk.CTkLabel(rr_col, text="Tỷ lệ R:R", font=_FONT_SMALL,
                     text_color=("gray50", "gray60")).pack(anchor="w")
        self._rr_var = tk.StringVar(value="—")
        ctk.CTkLabel(rr_col, textvariable=self._rr_var,
                     font=(_FF, 14, "bold"),
                     text_color=("#92400e", "#fcd34d")).pack(anchor="w")

        # Detail row
        self._detail_var = tk.StringVar(value="")
        ctk.CTkLabel(
            parent, textvariable=self._detail_var,
            font=_FONT_SMALL, text_color=("gray40", "gray65"), wraplength=260,
        ).grid(row=14, column=0, padx=20, pady=(4, 4), sticky="w")

        # Error label
        self._error_var = tk.StringVar(value="")
        self._error_label = ctk.CTkLabel(
            parent, textvariable=self._error_var,
            font=_FONT_SMALL, text_color=("red", "#ff6b6b"),
        )
        self._error_label.grid(row=15, column=0, padx=20, pady=(0, 10), sticky="w")

    def _build_right_panel(self, parent: ctk.CTkFrame):
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text="Market Rates", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, padx=20, pady=(16, 10), sticky="w"
        )
        self._dashboard_labels: dict[str, tk.StringVar] = {}
        for i, pair in enumerate(DASHBOARD_PAIRS):
            row_frame = ctk.CTkFrame(parent, fg_color="transparent")
            row_frame.grid(row=i + 1, column=0, padx=16, pady=4, sticky="ew")
            row_frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row_frame, text=f"{pair[:3]}/{pair[3:]}", font=_FONT_LABEL, width=80, anchor="w").grid(
                row=0, column=0, sticky="w"
            )
            rate_var = tk.StringVar(value="—")
            self._dashboard_labels[pair] = rate_var
            ctk.CTkLabel(
                row_frame, textvariable=rate_var,
                font=("Segoe UI", 13, "bold"), anchor="e",
                text_color=("#1a73e8", "#4da6ff"),
            ).grid(row=0, column=1, sticky="e")

        # Refresh button
        self._refresh_btn = ctk.CTkButton(
            parent, text="⟳  Refresh Now", width=160, height=32,
            font=_FONT_SMALL, command=self._manual_refresh,
        )
        self._refresh_btn.grid(row=len(DASHBOARD_PAIRS) + 1, column=0, padx=20, pady=(16, 16))

    # ── Actions ──────────────────────────────────────────────────────────────

    def _on_calculate(self):
        self._error_var.set("")
        pair = self._pair_var.get().replace("/", "").upper()
        sl_text = self._sl_entry.get().strip()
        risk_text = self._risk_entry.get().strip()
        tp_text = self._tp_entry.get().strip()

        def _reset_results():
            self._result_var.set("—")
            self._detail_var.set("")
            self._risk_display_var.set("—")
            self._profit_var.set("—")
            self._rr_var.set("—")

        # Validate SL and Risk
        try:
            sl = float(sl_text)
            risk = float(risk_text)
        except ValueError:
            self._error_var.set("Invalid input — enter numeric values.")
            _reset_results()
            return

        if sl <= 0 or risk <= 0:
            self._error_var.set("SL and Risk must be greater than zero.")
            _reset_results()
            return

        # Parse TP (optional)
        try:
            tp = float(tp_text) if tp_text else 0.0
        except ValueError:
            tp = 0.0

        rates = self.provider.get_all_rates()
        result: Optional[CalcResult] = calculate_lot_size(pair, sl, risk, rates)

        if result is None:
            self._error_var.set(f"No rate data for {pair}. Refreshing…")
            _reset_results()
            self.provider.force_refresh()
            return

        # Lot size
        self._result_var.set(f"{result.lot_size:.2f} lots")

        # Risk (red)
        self._risk_display_var.set(f"${risk:,.2f}")

        # Profit & R:R
        if tp > 0:
            profit = round(result.lot_size * tp * result.pip_value_per_lot, 2)
            rr = tp / sl
            self._profit_var.set(f"${profit:,.2f}")
            self._rr_var.set(f"1:{rr:.1f}")
        else:
            self._profit_var.set("$0.00")
            self._rr_var.set("—")

        self._detail_var.set(
            f"Pair: {result.pair[:3]}/{result.pair[3:]}  |  "
            f"SL: {result.sl_pips} pips  |  "
            f"Risk: ${result.risk_usd:,.2f}\n"
            f"Pip Value/lot: ${result.pip_value_per_lot:.4f}  |  "
            f"Rate: {result.source_rate:.5f}  |  Group: {result.group}"
        )

    def _manual_refresh(self):
        self._refresh_btn.configure(state="disabled", text="Refreshing…")
        import threading
        def _do():
            self.provider.force_refresh()
            self.after(0, lambda: self._refresh_btn.configure(state="normal", text="⟳  Refresh Now"))
        threading.Thread(target=_do, daemon=True).start()

    def _toggle_theme(self):
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            ctk.set_appearance_mode("light")
            self._theme_btn.configure(text="🌙 Dark")
        else:
            ctk.set_appearance_mode("dark")
            self._theme_btn.configure(text="☀ Light")

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_prices_updated(self):
        """Called from background thread — schedule GUI update on main thread."""
        self.after(0, self._update_dashboard)
        self.after(0, self._update_status)

    def _update_dashboard(self):
        rates = self.provider.get_all_rates()
        for pair, var in self._dashboard_labels.items():
            rate = rates.get(pair)
            if rate is None:
                var.set("—")
            elif pair in ("USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY", "CHFJPY"):
                var.set(f"{rate:.3f}")
            elif pair in ("XAUUSD",):
                var.set(f"{rate:.2f}")
            else:
                var.set(f"{rate:.5f}")

    def _update_status(self):
        source, ts = self.provider.get_status()
        if ts:
            dt = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            self._status_var.set(f"Source: {source}   |   Last update: {dt}")
        else:
            self._status_var.set("Connecting…")

    # ── Countdown timer ──────────────────────────────────────────────────────

    def _start_countdown(self):
        self._tick()

    def _tick(self):
        _, ts = self.provider.get_status()
        if ts:
            elapsed = time.time() - ts
            from .price_provider import REFRESH_INTERVAL
            remaining = max(0, REFRESH_INTERVAL - elapsed)
            self._countdown_var.set(f"Next update in {int(remaining)}s")
        self.after(1000, self._tick)
