"""
test_price_provider.py — Unit tests for the hybrid PriceProvider module.
Tất cả HTTP calls và yfinance đều được mock. Không gọi API thực tế.
"""

import json
import time
import threading
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from src.price_provider import PriceProvider, PAIR_META, DASHBOARD_PAIRS


# ---------------------------------------------------------------------------
# Helpers — mock API response payload
# ---------------------------------------------------------------------------

def _make_api_response(extra_rates: dict = None) -> dict:
    """Tạo một response JSON giống ExchangeRate-API trả về."""
    base_rates = {
        "EUR": 0.9217,
        "GBP": 0.7874,
        "JPY": 150.00,
        "CHF": 0.9000,
        "CAD": 1.3600,
        "AUD": 1.5385,
        "NZD": 1.6949,
        "SEK": 10.50,
        "NOK": 10.60,
        "DKK": 6.90,
        "SGD": 1.35,
        "HKD": 7.82,
        "ZAR": 18.50,
        "MXN": 17.20,
    }
    if extra_rates:
        base_rates.update(extra_rates)
    return {
        "result": "success",
        "conversion_rates": base_rates,
    }


def _make_mock_response(status_code: int, json_data: dict = None) -> MagicMock:
    """Tạo mock requests.Response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if status_code >= 400:
        from requests.exceptions import HTTPError
        mock_resp.raise_for_status.side_effect = HTTPError(
            f"HTTP {status_code}", response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = json_data or {}
    return mock_resp


# ===========================================================================
# 1. FETCH API — thành công
# ===========================================================================

class TestFetchAPI:
    def test_successful_api_fetch_returns_rates(self):
        """API trả về 200 + valid JSON → rates dict đầy đủ, source = 'ExchangeRate-API'."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            rates, source = provider._fetch_api()

        assert source == "ExchangeRate-API"
        assert "EURUSD" in rates
        assert "USDJPY" in rates
        assert "EURJPY" in rates
        assert rates["USDJPY"] == pytest.approx(150.00)

    def test_eurusd_rate_computed_correctly(self):
        """EUR/USD = 1 / usd_rates['EUR'] = 1 / 0.9217 ≈ 1.0850."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            rates, _ = provider._fetch_api()

        expected = 1.0 / 0.9217
        assert rates["EURUSD"] == pytest.approx(expected, rel=1e-4)

    def test_cross_rate_eurjpy_computed_correctly(self):
        """EUR/JPY = JPY / EUR = 150.0 / 0.9217 ≈ 162.74."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            rates, _ = provider._fetch_api()

        expected = 150.0 / 0.9217
        assert rates["EURJPY"] == pytest.approx(expected, rel=1e-3)

    def test_xauusd_not_in_api_rates(self):
        """XAU/USD và XAG/USD không có trong ExchangeRate-API free tier → không có key."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            rates, _ = provider._fetch_api()

        assert "XAUUSD" not in rates
        assert "XAGUSD" not in rates

    def test_empty_api_key_returns_empty(self):
        """API key rỗng (override trực tiếp _api_key) → không gọi HTTP, trả về ({}, '')."""
        provider = PriceProvider(api_key="dummy")
        provider._api_key = ""  # force empty sau khi constructor chạy
        with patch("src.price_provider.requests.get") as mock_get:
            rates, source = provider._fetch_api()

        mock_get.assert_not_called()
        assert rates == {}
        assert source == ""

    def test_api_result_not_success_returns_empty(self):
        """API trả về result != 'success' → ({}, '')."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, {"result": "error", "error-type": "invalid-key"})

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            rates, source = provider._fetch_api()

        assert rates == {}
        assert source == ""


# ===========================================================================
# 2. FALLBACK — HTTP 403 / 500 → tự động chuyển sang yfinance
# ===========================================================================

class TestFallbackBehavior:
    def test_http_403_triggers_yfinance_fallback(self):
        """HTTP 403 từ API → _fetch_yfinance được gọi thay thế."""
        provider = PriceProvider(api_key="test_key")
        mock_403 = _make_mock_response(403)
        fallback_rates = {"EURUSD": 1.085, "USDJPY": 150.0}

        with patch("src.price_provider.requests.get", return_value=mock_403):
            with patch.object(provider, "_fetch_yfinance", return_value=(fallback_rates, "yfinance")) as mock_yf:
                provider._do_refresh()
                mock_yf.assert_called_once()

        assert provider.get_rate("EURUSD") == pytest.approx(1.085)
        source, _ = provider.get_status()
        assert source == "yfinance"

    def test_http_500_triggers_yfinance_fallback(self):
        """HTTP 500 từ API → fallback sang yfinance."""
        provider = PriceProvider(api_key="test_key")
        mock_500 = _make_mock_response(500)
        fallback_rates = {"GBPUSD": 1.27, "USDJPY": 150.0}

        with patch("src.price_provider.requests.get", return_value=mock_500):
            with patch.object(provider, "_fetch_yfinance", return_value=(fallback_rates, "yfinance")) as mock_yf:
                provider._do_refresh()
                mock_yf.assert_called_once()

        source, _ = provider.get_status()
        assert source == "yfinance"

    def test_api_success_does_not_call_yfinance(self):
        """API thành công → yfinance KHÔNG được gọi."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            with patch.object(provider, "_fetch_yfinance") as mock_yf:
                provider._do_refresh()
                mock_yf.assert_not_called()

    def test_both_sources_fail_rates_unchanged(self):
        """Cả API lẫn yfinance đều lỗi → rates không thay đổi, không crash."""
        provider = PriceProvider(api_key="test_key")
        provider._rates = {"EURUSD": 1.08}  # pre-existing stale rate

        with patch.object(provider, "_fetch_api", return_value=({}, "")):
            with patch.object(provider, "_fetch_yfinance", return_value=({}, "ERROR")):
                provider._do_refresh()

        # rates không bị xóa, giữ nguyên giá trị cũ
        assert provider.get_rate("EURUSD") == pytest.approx(1.08)


# ===========================================================================
# 3. THREAD SAFETY & STATE
# ===========================================================================

class TestStateManagement:
    def test_get_rate_returns_none_before_refresh(self):
        """Trước khi refresh, get_rate trả về None."""
        provider = PriceProvider(api_key="")
        assert provider.get_rate("EURUSD") is None

    def test_get_all_rates_returns_copy(self):
        """get_all_rates trả về dict copy, không phải reference trực tiếp."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            provider._do_refresh()

        rates_copy = provider.get_all_rates()
        rates_copy["FAKEPAIR"] = 9999.0
        assert provider.get_rate("FAKEPAIR") is None  # global state không bị ảnh hưởng

    def test_status_updated_after_successful_refresh(self):
        """Sau khi refresh thành công, source và timestamp được cập nhật."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())
        before = time.time()

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            provider._do_refresh()

        source, ts = provider.get_status()
        assert source == "ExchangeRate-API"
        assert ts >= before

    def test_on_update_callback_called(self):
        """Callback đăng ký qua on_update() phải được gọi sau mỗi refresh."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())
        callback = MagicMock()
        provider.on_update(callback)

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            provider._do_refresh()

        callback.assert_called_once()

    def test_callback_exception_does_not_crash_provider(self):
        """Callback raise exception → provider vẫn hoạt động bình thường."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        def bad_callback():
            raise RuntimeError("UI crashed!")

        provider.on_update(bad_callback)

        # Không được raise exception ra ngoài
        with patch("src.price_provider.requests.get", return_value=mock_resp):
            try:
                provider._do_refresh()
            except Exception as e:
                pytest.fail(f"provider._do_refresh() raised unexpectedly: {e}")

    def test_get_rate_case_insensitive(self):
        """get_rate('eurusd') == get_rate('EURUSD')."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            provider._do_refresh()

        rate_upper = provider.get_rate("EURUSD")
        rate_lower = provider.get_rate("eurusd")
        assert rate_upper == rate_lower


# ===========================================================================
# 4. BUILD RATES FROM USD BASE
# ===========================================================================

class TestBuildRatesFromUsdBase:
    def setup_method(self):
        self.provider = PriceProvider(api_key="test_key")
        self.usd_rates = {
            "EUR": 0.9217,
            "GBP": 0.7874,
            "JPY": 150.00,
            "CHF": 0.9000,
            "CAD": 1.3600,
            "AUD": 1.5385,
            "NZD": 1.6949,
        }

    def test_usd_base_pair_direct(self):
        """USDJPY = usd_rates['JPY'] = 150.00."""
        rates = self.provider._build_rates_from_usd_base(self.usd_rates)
        assert rates["USDJPY"] == pytest.approx(150.00)

    def test_usd_quote_pair_inverted(self):
        """EURUSD = 1 / usd_rates['EUR']."""
        rates = self.provider._build_rates_from_usd_base(self.usd_rates)
        assert rates["EURUSD"] == pytest.approx(1.0 / 0.9217, rel=1e-4)

    def test_cross_pair_ratio(self):
        """EURJPY = JPY / EUR = 150.0 / 0.9217."""
        rates = self.provider._build_rates_from_usd_base(self.usd_rates)
        expected = 150.0 / 0.9217
        assert rates["EURJPY"] == pytest.approx(expected, rel=1e-3)

    def test_missing_currency_skipped_gracefully(self):
        """Currency bị thiếu trong usd_rates → pair đó không có trong output, không crash."""
        partial_rates = {"EUR": 0.9217}  # thiếu JPY, GBP, v.v.
        rates = self.provider._build_rates_from_usd_base(partial_rates)
        assert "USDJPY" not in rates
        assert "EURUSD" in rates  # EUR có → EURUSD vẫn tính được

    def test_all_non_metal_pairs_generated(self):
        """Tất cả pair không phải XAU/XAG đều được tạo khi rates đầy đủ."""
        rates = self.provider._build_rates_from_usd_base(self.usd_rates)
        non_metal_pairs = [s for s in PAIR_META if not s.startswith(("XAU", "XAG"))]
        # Chỉ test các pair mà currencies có trong usd_rates
        available_currencies = set(self.usd_rates.keys()) | {"USD"}
        for pair in non_metal_pairs:
            base, quote = pair[:3], pair[3:]
            if base in available_currencies and quote in available_currencies:
                assert pair in rates, f"{pair} should be in rates"


# ===========================================================================
# 5. DASHBOARD PAIRS
# ===========================================================================

class TestDashboardPairs:
    def test_dashboard_pairs_all_supported(self):
        """Tất cả DASHBOARD_PAIRS phải có trong PAIR_META."""
        for pair in DASHBOARD_PAIRS:
            assert pair in PAIR_META, f"{pair} missing from PAIR_META"

    def test_dashboard_rates_available_after_api_fetch(self):
        """Sau khi API fetch thành công, tất cả dashboard pairs có rate (trừ XAU/XAG)."""
        provider = PriceProvider(api_key="test_key")
        mock_resp = _make_mock_response(200, _make_api_response())

        with patch("src.price_provider.requests.get", return_value=mock_resp):
            provider._do_refresh()

        non_metal_dashboard = [p for p in DASHBOARD_PAIRS if not p.startswith("XAU")]
        for pair in non_metal_dashboard:
            assert provider.get_rate(pair) is not None, f"No rate for {pair}"
