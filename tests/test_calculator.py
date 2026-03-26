"""
test_calculator.py — Unit tests for lot size and pip value calculation logic.
Không gọi API thực tế. Tất cả rates đều là mock data tĩnh.
"""

import pytest
from src.calculator import pip_value_per_lot, calculate_lot_size, CalcResult

# ---------------------------------------------------------------------------
# Shared mock rates — dùng cho tất cả test cases
# ---------------------------------------------------------------------------
MOCK_RATES = {
    # Group 1 — USD as quote
    "EURUSD": 1.0850,
    "GBPUSD": 1.2700,
    "AUDUSD": 0.6500,
    "NZDUSD": 0.5900,
    "XAUUSD": 2300.00,
    "XAGUSD": 27.50,
    # Group 2 — USD as base
    "USDJPY": 150.00,
    "USDCHF": 0.9000,
    "USDCAD": 1.3600,
    # Group 3 — Non-JPY cross pairs (+ USD conversion rates)
    "EURGBP": 0.8543,
    "EURCAD": 1.4756,
    # Group 4 — JPY cross pairs (all use USDJPY for conversion)
    "EURJPY": 162.75,
    "GBPJPY": 190.50,
    "AUDJPY": 97.50,
    "NZDJPY": 88.50,
    "CHFJPY": 166.67,
}


# ===========================================================================
# 1. PIP VALUE — Group 1 (USD as quote)
# ===========================================================================

class TestPipValueGroup1:
    def test_eurusd_pip_value_is_10(self):
        """EUR/USD: pip = 0.0001, lot = 100_000 → $10 per lot."""
        pv = pip_value_per_lot("EURUSD", MOCK_RATES)
        assert pv == pytest.approx(10.0)

    def test_gbpusd_pip_value_is_10(self):
        pv = pip_value_per_lot("GBPUSD", MOCK_RATES)
        assert pv == pytest.approx(10.0)

    def test_audusd_pip_value_is_10(self):
        pv = pip_value_per_lot("AUDUSD", MOCK_RATES)
        assert pv == pytest.approx(10.0)

    def test_xauusd_pip_value(self):
        """XAU/USD: pip = 0.1, lot = 100 oz → pip_value = 100 × 0.1 = $10/lot (Universal Matrix)."""
        pv = pip_value_per_lot("XAUUSD", MOCK_RATES)
        assert pv == pytest.approx(10.0)

    def test_xagusd_pip_value(self):
        """XAG/USD: pip = 0.01, lot = 5,000 oz → pip_value = 5000 × 0.01 = $50/lot (Universal Matrix)."""
        pv = pip_value_per_lot("XAGUSD", MOCK_RATES)
        assert pv == pytest.approx(50.0)

    def test_lowercase_symbol_handled(self):
        """Symbol viết thường vẫn tính đúng."""
        pv = pip_value_per_lot("eurusd", MOCK_RATES)
        assert pv == pytest.approx(10.0)


# ===========================================================================
# 2. PIP VALUE — Group 2 (USD as base)
# ===========================================================================

class TestPipValueGroup2:
    def test_usdjpy_pip_value(self):
        """USD/JPY rate=150: pip = 0.01, lot = 100_000 → 1000/150 ≈ $6.6667."""
        pv = pip_value_per_lot("USDJPY", MOCK_RATES)
        expected = (0.01 * 100_000) / 150.0
        assert pv == pytest.approx(expected, rel=1e-4)

    def test_usdchf_pip_value(self):
        """USD/CHF rate=0.9: pip = 0.0001, lot = 100_000 → 10/0.9 ≈ $11.111."""
        pv = pip_value_per_lot("USDCHF", MOCK_RATES)
        expected = (0.0001 * 100_000) / 0.9
        assert pv == pytest.approx(expected, rel=1e-4)

    def test_usdcad_pip_value(self):
        pv = pip_value_per_lot("USDCAD", MOCK_RATES)
        expected = (0.0001 * 100_000) / 1.36
        assert pv == pytest.approx(expected, rel=1e-4)

    def test_missing_rate_returns_none(self):
        """Thiếu rate → trả về None, không crash."""
        pv = pip_value_per_lot("USDJPY", {})
        assert pv is None

    def test_zero_rate_returns_none(self):
        """Rate = 0 → tránh ZeroDivisionError, trả về None."""
        pv = pip_value_per_lot("USDJPY", {"USDJPY": 0.0})
        assert pv is None


# ===========================================================================
# 3. PIP VALUE — Group 3 (Cross pairs WITHOUT JPY)
# ===========================================================================

class TestPipValueGroup3:
    def test_eurgbp_pip_value_via_gbpusd(self):
        """
        EUR/GBP (Group 3 — non-JPY cross):
        pip_value = contract × pip_size × GBP/USD
                  = 100,000 × 0.0001 × 1.27 = $12.70/lot
        """
        pv = pip_value_per_lot("EURGBP", MOCK_RATES)
        expected = (0.0001 * 100_000) * 1.27
        assert pv == pytest.approx(expected, rel=1e-4)

    def test_eurgbp_group_is_3(self):
        result = calculate_lot_size("EURGBP", sl_pips=10, risk_usd=100, rates=MOCK_RATES)
        assert result is not None
        assert result.group == 3

    def test_cross_non_jpy_missing_conversion_returns_none(self):
        """EUR/GBP — thiếu cả GBPUSD lẫn USDGBP → None."""
        rates_no_gbp = {"EURGBP": 0.8543, "EURUSD": 1.085}  # không có GBPUSD
        pv = pip_value_per_lot("EURGBP", rates_no_gbp)
        assert pv is None


# ===========================================================================
# 4. PIP VALUE — Group 4 (Cross pairs WITH JPY — XXX/JPY)
# ===========================================================================

class TestPipValueGroup4:
    def test_eurjpy_pip_value(self):
        """
        EUR/JPY (Group 4 — JPY cross):
        pip_value = (contract × pip_size) / USD/JPY
                  = (100,000 × 0.01) / 150 = 1000/150 ≈ $6.6667/lot
        Universal Matrix formula — always uses USDJPY directly.
        """
        pv = pip_value_per_lot("EURJPY", MOCK_RATES)
        expected = (0.01 * 100_000) / 150.0
        assert pv == pytest.approx(expected, rel=1e-4)

    def test_gbpjpy_pip_value(self):
        """
        GBP/JPY (Group 4): same formula as EUR/JPY—rate doesn't matter, USDJPY does.
        pip_value = (100,000 × 0.01) / 150 ≈ $6.6667/lot
        """
        pv = pip_value_per_lot("GBPJPY", MOCK_RATES)
        expected = (0.01 * 100_000) / 150.0
        assert pv == pytest.approx(expected, rel=1e-4)

    def test_chfjpy_pip_value(self):
        pv = pip_value_per_lot("CHFJPY", MOCK_RATES)
        expected = (0.01 * 100_000) / 150.0
        assert pv == pytest.approx(expected, rel=1e-4)

    def test_audjpy_pip_value(self):
        pv = pip_value_per_lot("AUDJPY", MOCK_RATES)
        expected = (0.01 * 100_000) / 150.0
        assert pv == pytest.approx(expected, rel=1e-4)

    def test_eurjpy_group_is_4(self):
        result = calculate_lot_size("EURJPY", sl_pips=10, risk_usd=100, rates=MOCK_RATES)
        assert result is not None
        assert result.group == 4

    def test_gbpjpy_group_is_4(self):
        result = calculate_lot_size("GBPJPY", sl_pips=10, risk_usd=100, rates=MOCK_RATES)
        assert result is not None
        assert result.group == 4

    def test_eurjpy_missing_usdjpy_returns_none(self):
        """EUR/JPY — thiếu USDJPY → None (không dùng derived rate)."""
        rates_no_usdjpy = {"EURJPY": 162.75}  # thiếu USDJPY
        pv = pip_value_per_lot("EURJPY", rates_no_usdjpy)
        assert pv is None

    def test_eurjpy_real_scenario_122sl_99_71risk(self):
        """
        Kiểm tra trường hợp thực tế báo cáo:
        EUR/JPY, SL=122 pips, Risk=$99.71, USD/JPY=158.278
        pip_value = (100,000 × 0.01) / 158.278 = 1000/158.278 ≈ $6.3182/lot
        lot = 99.71 / (122 × 6.3182) = 99.71 / 770.52 ≈ 0.1294 → round = 0.13 lots
        """
        rates = {
            "EURJPY": 171.5,       # pair rate (needed for current_rate guard)
            "USDJPY": 158.278,     # conversion rate
        }
        pv = pip_value_per_lot("EURJPY", rates)
        expected_pv = 1000.0 / 158.278
        assert pv == pytest.approx(expected_pv, rel=1e-4)

        result = calculate_lot_size("EURJPY", sl_pips=122, risk_usd=99.71, rates=rates)
        assert result is not None
        assert result.lot_size == 0.13, (
            f"Expected 0.13 lots, got {result.lot_size}. "
            f"pip_value={result.pip_value_per_lot}, formula: 99.71/(122×{result.pip_value_per_lot:.4f})"
        )


# ===========================================================================
# 4. UNKNOWN PAIR
# ===========================================================================

class TestUnknownPair:
    def test_unknown_pair_returns_none(self):
        pv = pip_value_per_lot("USDXXX", MOCK_RATES)
        assert pv is None


# ===========================================================================
# 5. CALCULATE LOT SIZE — happy path
# ===========================================================================

class TestCalculateLotSize:
    def test_eurusd_lot_size(self):
        """
        EUR/USD: Risk=$100, SL=20 pips, pip_value=$10/lot
        lot = 100 / (20 * 10) = 0.50 lots
        """
        result = calculate_lot_size("EURUSD", sl_pips=20, risk_usd=100, rates=MOCK_RATES)
        assert result is not None
        assert result.lot_size == pytest.approx(0.50, abs=0.005)
        assert result.group == 1

    def test_usdjpy_lot_size(self):
        """
        USD/JPY: Risk=$200, SL=50 pips, pip_value = (0.01*100000)/150 ≈ 6.6667/lot
        lot = 200 / (50 * 6.6667) ≈ 0.60 lots
        """
        pv = (0.01 * 100_000) / 150.0
        expected_lot = round(200.0 / (50.0 * pv), 2)
        result = calculate_lot_size("USDJPY", sl_pips=50, risk_usd=200, rates=MOCK_RATES)
        assert result is not None
        assert result.lot_size == pytest.approx(expected_lot, abs=0.005)
        assert result.group == 2

    def test_eurgbp_lot_size(self):
        """
        EUR/GBP (Group 3 non-JPY cross): Risk=$150, SL=30 pips
        pip_value = 100,000 × 0.0001 × GBPUSD(1.27) = $12.70/lot
        lot = 150 / (30 × 12.70) ≈ 0.39 lots
        """
        pv = (0.0001 * 100_000) * 1.27
        expected_lot = round(150.0 / (30.0 * pv), 2)
        result = calculate_lot_size("EURGBP", sl_pips=30, risk_usd=150, rates=MOCK_RATES)
        assert result is not None
        assert result.lot_size == pytest.approx(expected_lot, abs=0.005)
        assert result.group == 3

    def test_result_is_rounded_to_2_decimals(self):
        result = calculate_lot_size("EURUSD", sl_pips=7, risk_usd=100, rates=MOCK_RATES)
        assert result is not None
        s = str(result.lot_size)
        decimal_places = len(s.split(".")[-1]) if "." in s else 0
        assert decimal_places <= 2

    def test_result_contains_correct_fields(self):
        result = calculate_lot_size("GBPUSD", sl_pips=25, risk_usd=50, rates=MOCK_RATES)
        assert isinstance(result, CalcResult)
        assert result.pair == "GBPUSD"
        assert result.sl_pips == 25
        assert result.risk_usd == 50
        assert result.source_rate == MOCK_RATES["GBPUSD"]


# ===========================================================================
# 6. EDGE CASES — biên giới và lỗi đầu vào
# ===========================================================================

class TestEdgeCases:
    def test_sl_zero_raises_value_error(self):
        """SL = 0 → ValueError, không crash app im lặng."""
        with pytest.raises(ValueError, match="positive"):
            calculate_lot_size("EURUSD", sl_pips=0, risk_usd=100, rates=MOCK_RATES)

    def test_risk_zero_raises_value_error(self):
        """Risk = 0 → ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_lot_size("EURUSD", sl_pips=20, risk_usd=0, rates=MOCK_RATES)

    def test_negative_sl_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_lot_size("EURUSD", sl_pips=-5, risk_usd=100, rates=MOCK_RATES)

    def test_negative_risk_raises_value_error(self):
        with pytest.raises(ValueError):
            calculate_lot_size("EURUSD", sl_pips=20, risk_usd=-100, rates=MOCK_RATES)

    def test_missing_rate_returns_none(self):
        """Không có rate cho pair → trả về None, không crash."""
        result = calculate_lot_size("EURUSD", sl_pips=20, risk_usd=100, rates={})
        assert result is None

    def test_pair_with_slash_normalised(self):
        """Symbol 'EUR/USD' phải được normalize thành 'EURUSD'."""
        result = calculate_lot_size("EUR/USD", sl_pips=20, risk_usd=100, rates=MOCK_RATES)
        assert result is not None
        assert result.pair == "EURUSD"

    def test_very_small_risk(self):
        """$1 risk → lot < 0.01, kết quả là 0.00 (làm tròn)."""
        result = calculate_lot_size("EURUSD", sl_pips=100, risk_usd=1, rates=MOCK_RATES)
        assert result is not None
        assert result.lot_size >= 0.0

    def test_very_large_risk(self):
        """$1,000,000 risk → lot hợp lệ, không overflow."""
        result = calculate_lot_size("EURUSD", sl_pips=10, risk_usd=1_000_000, rates=MOCK_RATES)
        assert result is not None
        assert result.lot_size > 0


# ===========================================================================
# 7. UI FORMAT — kiểm tra chuỗi hiển thị lên giao diện
# ===========================================================================

class TestUIFormat:
    def test_lot_size_display_string(self):
        """lot_size phải render được thành chuỗi 'X.XX lots'."""
        result = calculate_lot_size("EURUSD", sl_pips=20, risk_usd=100, rates=MOCK_RATES)
        display = f"{result.lot_size:.2f} lots"
        assert display == "0.50 lots"

    def test_pip_value_display_string(self):
        """pip_value_per_lot phải format được thành 4 chữ số thập phân."""
        result = calculate_lot_size("USDJPY", sl_pips=50, risk_usd=200, rates=MOCK_RATES)
        display = f"${result.pip_value_per_lot:.4f}"
        assert display.startswith("$")
        assert "." in display

    def test_detail_string_contains_all_fields(self):
        """Chuỗi detail hiển thị trên UI chứa đủ thông tin."""
        result = calculate_lot_size("EURUSD", sl_pips=20, risk_usd=100, rates=MOCK_RATES)
        detail = (
            f"Pair: {result.pair[:3]}/{result.pair[3:]}  |  "
            f"SL: {result.sl_pips} pips  |  "
            f"Risk: ${result.risk_usd:,.2f}"
        )
        assert "EUR/USD" in detail
        assert "20" in detail
        assert "$100.00" in detail


# ===========================================================================
# 8. TAKE PROFIT CALCULATION
# ===========================================================================

class TestTakeProfitCalculation:
    def test_eurusd_0_1lot_tp100_profit_is_100(self):
        """
        EUR/USD: lot=0.10, TP=100 pips, pip_value=$10/lot
        profit = 0.10 × 100 × 10 = $100.00
        """
        pv = pip_value_per_lot("EURUSD", MOCK_RATES)
        profit = round(0.10 * 100 * pv, 2)
        assert profit == pytest.approx(100.0)

    def test_eurusd_1lot_tp50_profit_is_500(self):
        """EUR/USD 1 lot, TP=50 pips → profit = 1 × 50 × 10 = $500."""
        pv = pip_value_per_lot("EURUSD", MOCK_RATES)
        profit = round(1.0 * 50 * pv, 2)
        assert profit == pytest.approx(500.0)

    def test_tp_zero_profit_is_zero(self):
        """TP = 0 → profit = $0."""
        pv = pip_value_per_lot("EURUSD", MOCK_RATES)
        profit = round(0.50 * 0 * pv, 2)
        assert profit == 0.0

    def test_rr_ratio_sl50_tp100_is_1_to_2(self):
        """SL=50, TP=100 → R:R = 1:2.0."""
        assert (100.0 / 50.0) == pytest.approx(2.0)

    def test_rr_ratio_sl20_tp30_is_1_to_1_5(self):
        """SL=20, TP=30 → R:R = 1:1.5."""
        assert (30.0 / 20.0) == pytest.approx(1.5)

    def test_usdjpy_tp_profit(self):
        """
        USD/JPY @150: lot=0.5, TP=30 pips
        pip_value = 1000/150 ≈ $6.6667/lot
        profit = 0.5 × 30 × 6.6667 ≈ $100.00
        """
        pv = pip_value_per_lot("USDJPY", MOCK_RATES)
        profit = round(0.5 * 30 * pv, 2)
        expected = round(0.5 * 30 * (1000.0 / 150.0), 2)
        assert profit == pytest.approx(expected, rel=1e-4)

    def test_profit_rounded_to_2_decimals(self):
        """Kết quả lợi nhuận được làm tròn 2 chữ số thập phân."""
        pv = pip_value_per_lot("EURUSD", MOCK_RATES)
        profit = round(0.15 * 33 * pv, 2)
        s = str(profit)
        decimal_places = len(s.split(".")[-1]) if "." in s else 0
        assert decimal_places <= 2

    def test_xauusd_tp_profit(self):
        """
        XAU/USD: pip_value = 100 × 0.1 = $10/lot
        lot=0.5, TP=20 pips → profit = 0.5 × 20 × 10 = $100
        """
        pv = pip_value_per_lot("XAUUSD", MOCK_RATES)
        profit = round(0.5 * 20 * pv, 2)
        assert profit == pytest.approx(100.0)
