#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CRYPTO INSTITUTIONAL MASTER PRO - LÕI XỬ LÝ (KHÔNG PHỤ THUỘC GIAO DIỆN)
Dùng chung cho bản Kivy/Android (main.py). Chứa: cấu hình bộ lọc, động cơ kỹ thuật,
quản trị rủi ro, theo dõi hiệu suất, bộ quét và các hàm thu thập vĩ mô.
================================================================================
"""

import sys
import os
import math
import time
import json
import ssl
import threading
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error
import urllib.parse
import collections

# ==============================================================================
# I. CẤU HÌNH HỆ THỐNG VÀ BẢNG MÀU
# ==============================================================================
TZ_VN = timezone(timedelta(hours=7))

BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision"
]

STABLECOINS = {
    "USDT", "USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDP", "EUR", "GBP", "TRY", 
    "AEUR", "USDD", "WBTC", "WBETH", "PAXG", "USTC", "EURI", "USD1", "XUSD", "RLUSD",
    "BFUSD", "USDS", "USDE", "U", "USD", "XAUT", "CUSD", "SUSD", "FRAX", "LUSD", "BTTC", 
    "PYUSD", "GUSD", "VAI", "BRL", "BIDR", "IDRT"
}

LEVERAGED_SUFFIXES = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")

COLOR_PALETTE = {
    "bg_main": "#0b0e14",
    "card_bg": "#151922",
    "card_sub": "#1e2430",
    "border": "#283040",
    "accent_blue": "#007acc",
    "accent_cyan": "#00b4d8",
    "bull_green": "#0ecb81",
    "bear_red": "#f6465d",
    "gold": "#f0b90b",
    "dark_gold": "#d4a017",
    "purple": "#9d4edd",
    "orange": "#f77f00",
    "text_main": "#eaecef",
    "text_muted": "#848e9c",
    "tab_inactive": "#12161f",
    "tab_active": "#222a38"
}

try:
    BASE_DIR = os.environ.get("CRYPTO_DATA_DIR") or os.path.dirname(os.path.abspath(__file__))
except Exception:
    BASE_DIR = os.getcwd()
try:
    os.makedirs(BASE_DIR, exist_ok=True)
except Exception:
    pass

PERF_LOG_FILE = os.path.join(BASE_DIR, "Performance_Tracker.txt")
PERF_DATA_FILE = os.path.join(BASE_DIR, "Performance_Data.json")
PORTFOLIO_FILE = os.path.join(BASE_DIR, "Portfolio_Data.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "Settings.json")


FILTER_FILE = os.path.join(BASE_DIR, "Filter_Setting.json")


# ==============================================================================
# I-B. CẤU HÌNH BỘ LỌC TÙY BIẾN (Filter_Setting.json - ĐỌC REAL-TIME THEO mtime)
# ==============================================================================
class FilterConfig:
    # (key, nhãn, min, max, bước, kiểu, mặc định, nhóm, đơn vị)
    SPECS = [
        ("min_quote_volume_24h", "Vol 24h tối thiểu", 1_000_000, 10_000_000, 500_000, "int", 3_000_000, 1, "USDT"),
        ("top_candidates_pool", "Số Altcoin quét sâu", 30, 100, 5, "int", 60, 1, "mã"),
        ("min_range_position", "Vị trí giá trong biên độ ngày", 0.30, 0.60, 0.05, "float", 0.40, 1, ""),

        ("btc_chg_spread", "Chênh %24h so với BTC", -4.0, 1.0, 0.5, "float", -2.0, 2, "%"),
        ("min_composite_rs", "Composite RS tối thiểu", -1.0, 2.0, 0.1, "float", 0.5, 2, "%"),
        ("rs_weight_6h", "Trọng số RS 6H (24H = 1 - 6H)", 0.30, 0.90, 0.05, "float", 0.60, 2, ""),

        ("rsi_overbought_threshold", "RSI quá mua (FOMO)", 75.0, 88.0, 1.0, "float", 85.0, 3, ""),
        ("wick_rejection_ratio", "Râu trên / thân nến (Shooting Star)", 1.8, 2.8, 0.1, "float", 2.2, 3, "x"),
        ("wick_dump_vol_ratio", "Vol xả / SMA20 (Shooting Star)", 1.5, 3.0, 0.1, "float", 2.0, 3, "x"),
        ("bb_bandwidth_max", "Bollinger Bandwidth nén tối đa", 3.0, 8.0, 0.5, "float", 5.0, 3, "%"),
        ("zlema_ribbon_gap_max", "ZLEMA Ribbon nén tối đa", 0.15, 0.60, 0.05, "float", 0.25, 3, "%"),

        ("trigger_vol_ratio_5m", "Vol bùng nổ 5m (Sóng 3)", 1.2, 2.5, 0.1, "float", 1.6, 4, "x"),
        ("pullback_dry_vol_ratio", "Vol cạn kiệt khi thoái lui", 0.70, 1.10, 0.02, "float", 0.92, 4, "x"),

        ("min_score_threshold", "Điểm sàn hiển thị Tab 1", 60, 85, 1, "int", 72, 5, "điểm"),
        ("penalty_btc_red", "Phạt điểm khi BTC Red", 0, 40, 1, "int", 15, 5, "điểm"),
        ("penalty_btc_yellow", "Phạt điểm khi BTC Yellow", 0, 20, 1, "int", 5, 5, "điểm"),
        ("penalty_btc_15m", "Phạt khi BTC lủng EMA20 15m", 0, 30, 1, "int", 10, 5, "điểm"),
    ]
    BOOL_SPECS = [
        ("btc_red_veto", "Veto tuyệt đối: BTC Red thì không xuất tín hiệu", False),
    ]
    GROUP_TITLES = {
        1: "1. LỌC THANH KHOẢN & VŨ TRỤ GIAO DỊCH",
        2: "2. SỨC MẠNH TƯƠNG ĐỐI (RS) SO VỚI BTC",
        3: "3. CHỈ BÁO KỸ THUẬT & CẢNH BÁO BẪY",
        4: "4. KHỐI LƯỢNG VI CẤU TRÚC (15m / 5m)",
        5: "5. THANG ĐIỂM & PHẠT KHI BTC XẤU",
    }
    SCORE_PRESETS = {"Khắt khe (A+)": 80, "Tiêu chuẩn (A)": 70, "Mở rộng (B)": 60}

    def __init__(self, path):
        self.path = path
        self._lock = threading.RLock()
        self._mtime = None
        self._data = self.defaults()
        self._refresh(force=True)

    @classmethod
    def defaults(cls):
        d = {sp[0]: sp[6] for sp in cls.SPECS}
        d["rs_weight_24h"] = round(1.0 - d["rs_weight_6h"], 4)
        for key, _, default in cls.BOOL_SPECS:
            d[key] = default
        return d

    @classmethod
    def spec_of(cls, key):
        for sp in cls.SPECS:
            if sp[0] == key:
                return sp
        return None

    @classmethod
    def sanitize(cls, raw):
        """Ép kiểu + kẹp giá trị vào dải cho phép; khóa thiếu/lỗi lấy mặc định."""
        out = cls.defaults()
        if not isinstance(raw, dict):
            return out
        for key, _, lo, hi, _, typ, default, _, _ in cls.SPECS:
            try:
                v = float(raw.get(key, default))
                if math.isnan(v) or math.isinf(v):
                    v = default
            except Exception:
                v = default
            v = max(lo, min(hi, v))
            out[key] = int(round(v)) if typ == "int" else round(v, 4)
        out["rs_weight_24h"] = round(1.0 - out["rs_weight_6h"], 4)
        for key, _, default in cls.BOOL_SPECS:
            val = raw.get(key, default)
            out[key] = bool(val) if isinstance(val, (bool, int)) else default
        return out

    def _refresh(self, force=False):
        try:
            mt = os.path.getmtime(self.path) if os.path.exists(self.path) else None
        except Exception:
            mt = None
        with self._lock:
            if not force and mt == self._mtime:
                return
            if mt is None:
                self._data = self.defaults()
                self._mtime = None
                self._write(self._data)
                return
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._data = self.sanitize(raw)
            except Exception:
                pass  # file đang ghi dở / hỏng -> giữ giá trị cũ
            self._mtime = mt

    def _write(self, data):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
            self._mtime = os.path.getmtime(self.path)
            return True
        except Exception:
            return False

    def get(self, key):
        self._refresh()
        with self._lock:
            return self._data.get(key, self.defaults().get(key))

    def snapshot(self):
        self._refresh()
        with self._lock:
            return dict(self._data)

    def update(self, changes):
        with self._lock:
            self._refresh()
            merged = dict(self._data)
            merged.update(changes)
            self._data = self.sanitize(merged)
            ok = self._write(self._data)
            return ok

    def reset(self):
        with self._lock:
            self._data = self.defaults()
            return self._write(self._data)


FILTER_CFG = FilterConfig(FILTER_FILE)


def make_ssl_context():
    """Ưu tiên xác thực chứng chỉ bằng certifi; không có certifi thì giữ hành vi cũ (không xác thực)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


def format_price(p):
    if p is None or p <= 0:
        return "0.00"
    if p < 0.0001:
        return f"{p:.8f}"
    elif p < 0.01:
        return f"{p:.6f}"
    elif p < 1.0:
        return f"{p:.5f}"
    elif p < 100.0:
        return f"{p:.4f}"
    else:
        return f"{p:.2f}"


# ==============================================================================
# II. QUẢN LÝ MẠNG VÀ KẾT NỐI BINANCE SPOT REAL-TIME
# ==============================================================================
class BinanceNetworkManager:
    def __init__(self):
        self.mirrors = list(BINANCE_MIRRORS)
        self.current_idx = 0
        self.lock = threading.Lock()
        self.ssl_context = make_ssl_context()
        self.last_ping_ms = 0
        self.active_host = self.mirrors[0]

    def _rotate_mirror(self):
        with self.lock:
            self.current_idx = (self.current_idx + 1) % len(self.mirrors)
            self.active_host = self.mirrors[self.current_idx]
            return self.active_host

    def fetch_json(self, endpoint, params=None, timeout=6):
        query_str = ""
        if params:
            query_str = "?" + "&".join(f"{k}={v}" for k, v in params.items())

        for _ in range(len(self.mirrors)):
            with self.lock:
                base_url = self.active_host
            url = f"{base_url}{endpoint}{query_str}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
            )
            try:
                t0 = time.perf_counter()
                with urllib.request.urlopen(req, context=self.ssl_context, timeout=timeout) as resp:
                    if resp.status == 200:
                        raw = resp.read().decode("utf-8")
                        self.last_ping_ms = int((time.perf_counter() - t0) * 1000)
                        return json.loads(raw)
            except Exception:
                self._rotate_mirror()
                time.sleep(0.08)
        return None

    def get_ping(self):
        res = self.fetch_json("/api/v3/ping", timeout=3)
        return self.last_ping_ms if res is not None else -1

    def get_24h_tickers(self):
        data = self.fetch_json("/api/v3/ticker/24hr", timeout=8)
        return data if isinstance(data, list) else []

    def get_klines(self, symbol, interval="30m", limit=300):
        params = {"symbol": symbol.upper(), "interval": interval, "limit": str(limit)}
        raw = self.fetch_json("/api/v3/klines", params=params, timeout=6)
        if not raw or not isinstance(raw, list):
            return []
        parsed = []
        for k in raw:
            try:
                parsed.append({
                    "open_time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "quote_volume": float(k[7]),
                    "taker_buy_volume": float(k[9]),
                    "taker_buy_quote_volume": float(k[10])
                })
            except (ValueError, IndexError):
                continue
        return parsed


# ==============================================================================
# III. ĐỘNG CƠ TÍNH TOÁN KỸ THUẬT & ORDERFLOW
# ==============================================================================
class TechnicalEngine:
    @staticmethod
    def calc_ema(values, period):
        if not values or len(values) < period:
            return [0.0] * len(values)
        ema = [0.0] * len(values)
        k = 2.0 / (period + 1)
        sma = sum(values[:period]) / period
        ema[period - 1] = sma
        for i in range(period, len(values)):
            ema[i] = (values[i] * k) + (ema[i - 1] * (1.0 - k))
        for i in range(period - 1):
            ema[i] = ema[period - 1]
        return ema

    @classmethod
    def calc_zlema(cls, values, period):
        if not values or len(values) < period:
            return [0.0] * len(values)
        lag = (period - 1) // 2
        zlema_data = []
        for i in range(len(values)):
            if i < lag:
                zlema_data.append(values[i])
            else:
                zlema_data.append((2.0 * values[i]) - values[i - lag])
        return cls.calc_ema(zlema_data, period)

    @staticmethod
    def calc_rma(values, period):
        if not values or len(values) < period:
            return [0.0] * len(values)
        rma = [0.0] * len(values)
        alpha = 1.0 / period
        rma[period - 1] = sum(values[:period]) / period
        for i in range(period, len(values)):
            rma[i] = (values[i] * alpha) + (rma[i - 1] * (1.0 - alpha))
        for i in range(period - 1):
            rma[i] = rma[period - 1]
        return rma

    @classmethod
    def calc_rsi(cls, closes, period=14):
        if len(closes) <= period:
            return 50.0
        gains, losses = [0.0], [0.0]
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(0.0, diff))
            losses.append(max(0.0, -diff))
        avg_gain = cls.calc_rma(gains, period)
        avg_loss = cls.calc_rma(losses, period)
        curr_loss = avg_loss[-1]
        if curr_loss == 0.0:
            return 100.0 if avg_gain[-1] > 0 else 50.0
        rs = avg_gain[-1] / curr_loss
        return round(100.0 - (100.0 / (1.0 + rs)), 2)

    @classmethod
    def calc_macd(cls, closes, fast=12, slow=26, signal=9):
        if len(closes) < slow + signal:
            return 0.0, 0.0, 0.0, 0.0, False
        ema_f = cls.calc_ema(closes, fast)
        ema_s = cls.calc_ema(closes, slow)
        macd_l = [f - s for f, s in zip(ema_f, ema_s)]
        sig_l = cls.calc_ema(macd_l, signal)
        hist = [m - s for m, s in zip(macd_l, sig_l)]
        hist_delta = hist[-1] - hist[-2] if len(hist) >= 2 else 0.0
        bull_cross = (hist[-2] <= 0.0 and hist[-1] > 0.0) or (macd_l[-2] <= sig_l[-2] and macd_l[-1] > sig_l[-1])
        return round(macd_l[-1], 6), round(sig_l[-1], 6), round(hist[-1], 6), round(hist_delta, 6), bull_cross

    @staticmethod
    def calc_bollinger_bands(closes, period=20, mult=2.0):
        if len(closes) < period:
            return 0.0, 0.0, 0.0, 0.0
        sub = closes[-period:]
        mid = sum(sub) / period
        variance = sum((x - mid) ** 2 for x in sub) / period
        std_dev = math.sqrt(variance)
        upper = mid + (mult * std_dev)
        lower = mid - (mult * std_dev)
        bandwidth = ((upper - lower) / mid * 100.0) if mid > 0 else 0.0
        return round(mid, 6), round(upper, 6), round(lower, 6), round(bandwidth, 2)

    @classmethod
    def calc_atr(cls, klines, period=14):
        if len(klines) < period + 1:
            return 0.0
        tr_list = [klines[0]["high"] - klines[0]["low"]]
        for i in range(1, len(klines)):
            h = klines[i]["high"]
            l = klines[i]["low"]
            pc = klines[i - 1]["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            tr_list.append(tr)
        atr_series = cls.calc_rma(tr_list, period)
        return round(atr_series[-1], 6)

    @staticmethod
    def calc_support_resistance(klines, curr_p):
        if not klines or len(klines) < 10 or curr_p <= 0:
            return round(curr_p * 0.98, 6), round(curr_p * 0.95, 6), round(curr_p * 1.02, 6), round(curr_p * 1.05, 6)

        lookback = min(len(klines), 60)
        recent_k = klines[-lookback:]
        highs = [k["high"] for k in recent_k]
        lows = [k["low"] for k in recent_k]

        resistances = []
        for i in range(2, len(highs) - 2):
            if highs[i] >= highs[i - 1] and highs[i] >= highs[i - 2] and highs[i] >= highs[i + 1] and highs[i] >= highs[i + 2]:
                if highs[i] > curr_p:
                    resistances.append(highs[i])

        supports = []
        for i in range(2, len(lows) - 2):
            if lows[i] <= lows[i - 1] and lows[i] <= lows[i - 2] and lows[i] <= lows[i + 1] and lows[i] <= lows[i + 2]:
                if lows[i] < curr_p:
                    supports.append(lows[i])

        max_high = max(highs)
        min_low = min(lows)

        res_above = [r for r in resistances if r > curr_p * 1.002]
        r1 = min(res_above) if res_above else (max_high if max_high > curr_p * 1.003 else curr_p * 1.025)
        res_higher = [r for r in res_above if r > r1 * 1.005]
        r2 = min(res_higher) if res_higher else (max_high if max_high > r1 * 1.003 else r1 * 1.035)

        sup_below = [s for s in supports if s < curr_p * 0.998]
        s1 = max(sup_below) if sup_below else (min_low if min_low < curr_p * 0.997 else curr_p * 0.975)
        sup_lower = [s for s in sup_below if s < s1 * 0.995]
        s2 = max(sup_lower) if sup_lower else (min_low if min_low < s1 * 0.997 else s1 * 0.97)

        return round(s1, 6), round(s2, 6), round(r1, 6), round(r2, 6)

    @staticmethod
    def calc_session_vwap_bands_vn(klines):
        if not klines:
            return 0.0, 0.0, 0.0, 0.0, 0.0
        last_dt_vn = datetime.fromtimestamp(klines[-1]["open_time"] / 1000.0, tz=TZ_VN)
        if last_dt_vn.hour >= 7:
            session_start = last_dt_vn.replace(hour=7, minute=0, second=0, microsecond=0)
        else:
            session_start = (last_dt_vn - timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
        session_start_ms = int(session_start.timestamp() * 1000)

        cum_tp_vol, cum_vol, cum_tp2_vol = 0.0, 0.0, 0.0
        session_klines = [k for k in klines if k["open_time"] >= session_start_ms]
        if not session_klines:
            session_klines = klines[-24:]

        for k in session_klines:
            tp = (k["high"] + k["low"] + k["close"]) / 3.0
            v = k["volume"]
            cum_tp_vol += tp * v
            cum_tp2_vol += (tp ** 2) * v
            cum_vol += v

        if cum_vol <= 0:
            cp = klines[-1]["close"]
            return cp, cp, cp, cp, cp

        vwap = cum_tp_vol / cum_vol
        var = max(0.0, (cum_tp2_vol / cum_vol) - (vwap ** 2))
        sd = math.sqrt(var)
        return (
            round(vwap, 6),
            round(vwap + sd, 6),
            round(vwap - sd, 6),
            round(vwap + 2.0 * sd, 6),
            round(vwap - 2.0 * sd, 6)
        )

    @staticmethod
    def calc_cvd_series(klines):
        cvd_series = []
        running_cvd = 0.0
        for k in klines:
            tb_q = k.get("taker_buy_quote_volume", 0.0)
            q_vol = k.get("quote_volume", 0.0)
            delta = (2.0 * tb_q) - q_vol
            running_cvd += delta
            cvd_series.append(running_cvd)
        return cvd_series

    @classmethod
    def audit_cvd_divergence(cls, klines, lookback=16):
        if not klines or len(klines) < lookback:
            return False, 0.0, "CVD bình thường"
        sub_k = klines[-lookback:]
        cvds = cls.calc_cvd_series(sub_k)
        closes = [k["close"] for k in sub_k]
        try:
            min_p_idx = closes.index(min(closes))
            if min_p_idx >= len(closes) - 4 and min_p_idx > 2:
                prev_p_idx = closes[:min_p_idx].index(min(closes[:min_p_idx]))
                if closes[min_p_idx] <= closes[prev_p_idx] and cvds[min_p_idx] > cvds[prev_p_idx]:
                    return True, round(cvds[-1] - cvds[0], 2), "Phát hiện Bullish CVD Divergence (Smart Money gom đáy)"
        except Exception:
            pass
        net_cvd = round(cvds[-1] - cvds[0], 2) if cvds else 0.0
        return False, net_cvd, ("Khối lượng mua chủ động dương" if net_cvd > 0 else "Khối lượng bán chủ động")

    @staticmethod
    def calc_cvd_usdt(klines):
        cvd = 0.0
        for k in klines:
            tb_q = k.get("taker_buy_quote_volume", 0.0)
            q_vol = k.get("quote_volume", 0.0)
            cvd += ((2.0 * tb_q) - q_vol)
        return round(cvd, 2)

    @staticmethod
    def calc_volume_profile_poc(klines, bins=35):
        if not klines:
            return 0.0
        min_p = min(k["low"] for k in klines)
        max_p = max(k["high"] for k in klines)
        if max_p <= min_p:
            return min_p
        bin_size = max((max_p - min_p) / bins, 1e-8)
        volume_bins = [0.0] * bins
        for k in klines:
            tp = (k["high"] + k["low"] + k["close"]) / 3.0
            idx = int((tp - min_p) / bin_size)
            idx = max(0, min(bins - 1, idx))
            volume_bins[idx] += k["volume"]
        max_idx = volume_bins.index(max(volume_bins))
        return round(min_p + (max_idx * bin_size) + (bin_size / 2.0), 6)


# ==============================================================================
# IV. ĐỘNG CƠ NHẬN DIỆN MÔ HÌNH VÀ CHIẾN LƯỢC SĂN COIN
# ==============================================================================
class PatternStrategyEngine:
    @staticmethod
    def audit_setup(klines_30m, poc=0.0):
        if len(klines_30m) < 60:
            return None, None

        closes = [k["close"] for k in klines_30m]
        highs = [k["high"] for k in klines_30m]
        lows = [k["low"] for k in klines_30m]
        vols = [k["volume"] for k in klines_30m]
        curr_p = closes[-1]

        lookback = min(len(klines_30m), 90)
        sub_highs = highs[-lookback:]
        sub_lows = lows[-lookback:]
        recent_highs = sub_highs[-50:-4]

        vol_sma20 = sum(vols[-21:-1]) / 20.0 if len(vols) >= 21 else 1.0
        curr_vol = vols[-1]

        cfg = FILTER_CFG.snapshot()
        w3_vol = cfg["trigger_vol_ratio_5m"]
        brk_vol = max(1.0, w3_vol - 0.2)
        dry_vol = cfg["pullback_dry_vol_ratio"]
        bb_max = cfg["bb_bandwidth_max"]

        if recent_highs:
            h1 = max(recent_highs)
            idx_h1 = len(sub_highs) - 1 - sub_highs[::-1].index(h1)
            pre_h1_lows = sub_lows[:idx_h1]
            if pre_h1_lows:
                l0 = min(pre_h1_lows)
                idx_l0 = pre_h1_lows.index(l0)
                w1_amp = h1 - l0
                w1_pct = (w1_amp / l0) * 100.0 if l0 > 0 else 0.0

                if idx_l0 < idx_h1 and w1_pct >= 8.0:
                    post_h1 = klines_30m[-(lookback - idx_h1):]
                    if len(post_h1) >= 4:
                        l2 = min(k["low"] for k in post_h1)
                        retest_ratio = (h1 - curr_p) / w1_amp if w1_amp > 0 else 0.0

                        if (curr_p >= h1 * 0.988) and (curr_vol >= w3_vol * vol_sma20) and (l2 >= l0 + (0.214 * w1_amp)):
                            return "WAVE_3", {"h1": h1, "l0": l0, "l2": l2, "w1_pct": w1_pct, "w1_amp": w1_amp}

                        if (0.382 <= retest_ratio <= 0.786) and (curr_p > l0) and (l2 > l0) and (curr_vol < dry_vol * vol_sma20):
                            return "WAVE_2", {"h1": h1, "l0": l0, "l2": l2, "w1_pct": w1_pct, "w1_amp": w1_amp}

        _, _, _, bb_bw = TechnicalEngine.calc_bollinger_bands(closes, 20)
        swing_h100 = max(highs[-100:])
        swing_l100 = min(lows[-100:])

        if curr_p >= swing_h100 * 0.995 and (curr_vol >= brk_vol * vol_sma20 or bb_bw < bb_max):
            return "BREAKOUT", {"swing_h": swing_h100, "swing_l": swing_l100, "bb_bw": bb_bw}

        diff_range = swing_h100 - swing_l100
        if diff_range > 0:
            fib_500 = swing_h100 - (0.500 * diff_range)
            fib_618 = swing_h100 - (0.618 * diff_range)
            if (fib_618 * 0.99 <= curr_p <= fib_500 * 1.015) and curr_p >= swing_l100:
                return "PULLBACK", {"swing_h": swing_h100, "swing_l": swing_l100, "fib_500": fib_500, "fib_618": fib_618}

        recent_l15 = min(lows[-15:-1]) if len(lows) >= 15 else swing_l100
        if lows[-1] < recent_l15 and closes[-1] > recent_l15:
            return "SWEEP", {"sweep_low": lows[-1], "key_level": recent_l15}

        return None, None

    @staticmethod
    def audit_subwaves_15m_5m(k_15m, k_5m, setup_mode):
        if not k_15m or not k_5m or len(k_15m) < 20 or len(k_5m) < 20:
            return {"confirmed": True, "score_bonus": 0, "desc": "Chưa đủ nến vi cấu trúc 15m/5m", "m15": {}, "m5": {}}

        c_15m = [k["close"] for k in k_15m]
        v_15m = [k["volume"] for k in k_15m]
        curr_p_15m = c_15m[-1]

        rsi_15m = TechnicalEngine.calc_rsi(c_15m, 14)
        ema20_15m = TechnicalEngine.calc_ema(c_15m, 20)[-1]
        zlema20_15m = TechnicalEngine.calc_zlema(c_15m, 20)[-1]
        macd_l15, sig_l15, hist_15m, hist_delta15, _ = TechnicalEngine.calc_macd(c_15m)
        sma_v15m = sum(v_15m[-21:-1]) / 20.0 if len(v_15m) >= 21 else 1.0
        vol_ratio_15m = v_15m[-1] / sma_v15m if sma_v15m > 0 else 1.0

        c_5m = [k["close"] for k in k_5m]
        o_5m = [k["open"] for k in k_5m]
        h_5m = [k["high"] for k in k_5m]
        l_5m = [k["low"] for k in k_5m]
        v_5m = [k["volume"] for k in k_5m]
        curr_p_5m = c_5m[-1]

        rsi_5m = TechnicalEngine.calc_rsi(c_5m, 14)
        ema20_5m = TechnicalEngine.calc_ema(c_5m, 20)[-1]
        zlema20_5m = TechnicalEngine.calc_zlema(c_5m, 20)[-1]
        sma_v5m = sum(v_5m[-21:-1]) / 20.0 if len(v_5m) >= 21 else 1.0
        vol_ratio_5m = v_5m[-1] / sma_v5m if sma_v5m > 0 else 1.0

        candle_5m_green = c_5m[-1] > o_5m[-1]
        candle_5m_pct = ((c_5m[-1] - o_5m[-1]) / o_5m[-1]) * 100.0 if o_5m[-1] > 0 else 0.0
        range_5m = h_5m[-1] - l_5m[-1]
        lower_wick_5m = min(o_5m[-1], c_5m[-1]) - l_5m[-1]
        pinbar_5m = (lower_wick_5m > 0.45 * range_5m) if range_5m > 0 else False

        if rsi_15m < 38:
            rsi_15m_eval = "Quá bán (Cạn kiệt đà rơi)"
        elif 38 <= rsi_15m <= 54:
            rsi_15m_eval = "Hạ nhiệt OTE lành mạnh (Vùng chuẩn Sóng 2)"
        elif 54 < rsi_15m <= 70:
            rsi_15m_eval = "Xung lực tăng mở rộng (Chuẩn đà Sóng 3)"
        else:
            rsi_15m_eval = "Quá mua ngắn hạn (Cần kéo chặt SL)"

        pos_ema_15m = f"TRÊN ZLEMA/EMA20 ({format_price(zlema20_15m)})" if curr_p_15m >= zlema20_15m else f"DƯỚI ZLEMA20 ({format_price(zlema20_15m)})"
        macd_15m_eval = f"Histogram {hist_15m:+.6f} ({'Phe mua áp đảo' if hist_15m > 0 else 'Phe bán suy yếu'})"

        pos_ema_5m = f"TRÊN ZLEMA20 ({format_price(zlema20_5m)})" if curr_p_5m >= zlema20_5m else f"DƯỚI ZLEMA20 ({format_price(zlema20_5m)})"
        candle_5m_desc = f"{'Nến xanh (+{:.2f}%)'.format(candle_5m_pct) if candle_5m_green else 'Nến đỏ ({:.2f}%)'.format(candle_5m_pct)}"
        if pinbar_5m:
            candle_5m_desc += " [Pinbar rút chân]"

        vol_5m_desc = f"{vol_ratio_5m:.2f}x SMA20 ({'Nổ Vol' if vol_ratio_5m >= 1.5 else ('Cạn kiệt' if vol_ratio_5m < 0.85 else 'Bình thường')})"

        confirmed = False
        bonus = 0
        trigger_desc = ""
        _cfg = FILTER_CFG.snapshot()
        _w3_vol = _cfg["trigger_vol_ratio_5m"]
        _brk_vol = max(1.0, _w3_vol - 0.2)

        if setup_mode == "WAVE_2":
            is_15m_cooling = 35 <= rsi_15m <= 54
            is_5m_spring = (candle_5m_green or pinbar_5m) and (vol_ratio_5m < 1.1 or pinbar_5m)
            if is_15m_cooling and is_5m_spring and curr_p_5m >= zlema20_5m:
                confirmed = True
                bonus = 15
                trigger_desc = f"15m cạn cung (RSI {rsi_15m:.1f}) + 5m giữ vững trên ZLEMA20 ({vol_ratio_5m:.2f}x Vol)"
            elif candle_5m_green:
                confirmed = True
                bonus = 6
                trigger_desc = f"5m có nến xanh bật hồi sớm, RSI 15m {rsi_15m:.1f}"
            else:
                trigger_desc = "15m/5m đang điều chỉnh, chưa xuất hiện nến dừng"
        elif setup_mode == "WAVE_3":
            h_prev_5m = max(h_5m[-9:-1]) if len(h_5m) >= 9 else c_5m[-1]
            break_5m = c_5m[-1] >= h_prev_5m * 0.998
            vol_boost_5m = vol_ratio_5m >= _w3_vol
            if break_5m and vol_boost_5m and rsi_15m >= 52 and curr_p_5m >= zlema20_5m:
                confirmed = True
                bonus = 16
                trigger_desc = f"5m nổ xung lực ({vol_ratio_5m:.2f}x) vượt đỉnh & neo trên ZLEMA20"
            elif vol_boost_5m:
                confirmed = True
                bonus = 8
                trigger_desc = f"5m đột biến khối lượng ({vol_ratio_5m:.2f}x SMA20)"
            else:
                trigger_desc = "5m chưa bùng nổ khối lượng vượt đỉnh"
        elif setup_mode == "BREAKOUT":
            if vol_ratio_5m >= _brk_vol and candle_5m_green and curr_p_5m >= zlema20_5m:
                confirmed = True
                bonus = 12
                trigger_desc = f"5m nến xanh bung nén trên ZLEMA20 với Vol x{vol_ratio_5m:.2f}"
            else:
                trigger_desc = f"5m đang giằng co tại kháng cự (Vol x{vol_ratio_5m:.2f})"
        else:
            if (candle_5m_green or pinbar_5m) and curr_p_5m >= zlema20_5m:
                confirmed = True
                bonus = 10
                trigger_desc = f"5m rút chân giữ vững hỗ trợ trên ZLEMA20 (RSI 15m {rsi_15m:.1f})"
            else:
                trigger_desc = "5m chưa có nến phản ứng đảo chiều rõ nét"

        m15_metrics = {
            "price": curr_p_15m, "ema20": ema20_15m, "zlema20": zlema20_15m, "pos_ema": pos_ema_15m,
            "rsi": rsi_15m, "rsi_eval": rsi_15m_eval, "macd_l": macd_l15,
            "sig_l": sig_l15, "hist": hist_15m, "macd_eval": macd_15m_eval,
            "vol_ratio": vol_ratio_15m
        }

        m5_metrics = {
            "price": curr_p_5m, "ema20": ema20_5m, "zlema20": zlema20_5m, "pos_ema": pos_ema_5m,
            "rsi": rsi_5m, "candle_desc": candle_5m_desc,
            "vol_ratio": vol_ratio_5m, "vol_desc": vol_5m_desc
        }

        return {
            "confirmed": confirmed, "score_bonus": bonus, "desc": trigger_desc,
            "m15": m15_metrics, "m5": m5_metrics
        }


# ==============================================================================
# V. QUẢN TRỊ RỦI RO & TÍNH VỊ THẾ SPOT TIỀN MẶT (NAV)
# ==============================================================================
class InstitutionalRiskManager:
    @classmethod
    def calculate_trade_levels(cls, klines_30m, setup_mode, setup_data=None, poc=0.0):
        closes = [k["close"] for k in klines_30m]
        highs = [k["high"] for k in klines_30m]
        lows = [k["low"] for k in klines_30m]
        curr_p = closes[-1]
        atr = TechnicalEngine.calc_atr(klines_30m, 14)
        ema20 = TechnicalEngine.calc_ema(closes, 20)[-1]
        
        setup_data = setup_data or {}

        if setup_mode in ("WAVE_2", "WAVE_3") and "h1" in setup_data and "w1_amp" in setup_data:
            h1 = setup_data["h1"]
            l0 = setup_data.get("l0", min(lows[-60:]))
            l2 = setup_data.get("l2", l0)
            w1_amp = setup_data["w1_amp"]

            if setup_mode == "WAVE_2":
                entry = (h1 - 0.500 * w1_amp + h1 - 0.618 * w1_amp) / 2.0
                sl = (min(l0, poc) if poc > 0 else l0) - (1.2 * atr)
            else:
                entry = h1 * 1.002 if curr_p > h1 else curr_p
                sl = l2 - (1.2 * atr)
        elif setup_mode == "SWEEP" and "sweep_low" in setup_data:
            entry = curr_p
            sl = setup_data["sweep_low"] - (1.2 * atr)
        else:
            swing_h = setup_data.get("swing_h", max(highs[-60:]))
            swing_l = setup_data.get("swing_l", min(lows[-60:]))

            if setup_mode == "BREAKOUT":
                entry = max(curr_p, swing_h)
                sl = entry - (1.8 * atr)
                if ema20 < entry:
                    sl = min(sl, ema20 - (0.8 * atr))
            else:
                fib_500 = swing_h - (0.500 * (swing_h - swing_l))
                fib_618 = swing_h - (0.618 * (swing_h - swing_l))
                entry = (fib_500 + fib_618) / 2.0
                if fib_618 <= ema20 <= fib_500:
                    entry = ema20
                sl = (min(swing_l, poc) if poc > 0 else swing_l) - (1.2 * atr)

        min_sl_dist = entry * 0.025
        if (entry - sl) < min_sl_dist:
            sl = entry - min_sl_dist

        risk = entry - sl
        if risk <= 0:
            risk = 1.5 * atr
            sl = entry - risk

        tp1 = entry + min(risk * 1.0, entry * 0.038)
        tp2 = entry + (1.8 * risk)
        tp3 = entry + (2.8 * risk)

        risk_pct = ((entry - sl) / entry) * 100.0 if entry > 0 else 0.0
        tp1_pct = ((tp1 - entry) / entry) * 100.0 if entry > 0 else 0.0
        tp2_pct = ((tp2 - entry) / entry) * 100.0 if entry > 0 else 0.0
        tp3_pct = ((tp3 - entry) / entry) * 100.0 if entry > 0 else 0.0

        return {
            "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
            "risk_pct": round(risk_pct, 2), "tp1_pct": round(tp1_pct, 2),
            "tp2_pct": round(tp2_pct, 2), "tp3_pct": round(tp3_pct, 2),
            "atr": atr, "poc": poc
        }

    @staticmethod
    def calculate_levels_from_custom_entry(entry_val, atr_val):
        if entry_val <= 0:
            return None
        atr = max(atr_val, entry_val * 0.015)
        sl_dist = max(1.5 * atr, entry_val * 0.025)
        sl = entry_val - sl_dist
        risk = entry_val - sl

        tp1 = entry_val + min(risk * 1.0, entry_val * 0.038)
        tp2 = entry_val + (1.8 * risk)
        tp3 = entry_val + (2.8 * risk)

        risk_pct = ((entry_val - sl) / entry_val) * 100.0
        tp1_pct = ((tp1 - entry_val) / entry_val) * 100.0
        tp2_pct = ((tp2 - entry_val) / entry_val) * 100.0
        tp3_pct = ((tp3 - entry_val) / entry_val) * 100.0

        return {
            "entry": entry_val, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
            "risk_pct": round(risk_pct, 2), "tp1_pct": round(tp1_pct, 2),
            "tp2_pct": round(tp2_pct, 2), "tp3_pct": round(tp3_pct, 2),
            "atr": atr
        }

    @staticmethod
    def calculate_position_size(nav, risk_pct_target, entry, sl, max_losses=0):
        if nav <= 0 or entry <= 0 or sl <= 0 or entry <= sl:
            return None

        target_risk_usd = nav * (risk_pct_target / 100.0)
        sl_pct_raw = (entry - sl) / entry
        raw_position_usd = target_risk_usd / sl_pct_raw

        is_capped = False
        if raw_position_usd > nav:
            position_usd = nav
            actual_risk_usd = position_usd * sl_pct_raw
            actual_risk_pct = (actual_risk_usd / nav) * 100.0
            is_capped = True
        else:
            position_usd = raw_position_usd
            actual_risk_usd = target_risk_usd
            actual_risk_pct = risk_pct_target

        coin_qty = position_usd / entry
        cash_left = max(0.0, nav - position_usd)
        stop_trading = (max_losses >= 2)

        return {
            "position_usd": position_usd, "coin_qty": coin_qty,
            "actual_risk_usd": actual_risk_usd, "actual_risk_pct": actual_risk_pct,
            "sl_pct": sl_pct_raw * 100.0, "cash_left": cash_left,
            "is_capped": is_capped, "stop_trading": stop_trading
        }


# ==============================================================================
# VI. BỘ QUẢN LÝ TÀI SẢN (PORTFOLIO ASSETS)
# ==============================================================================
class AssetManager:
    def __init__(self, net_mgr, log_cb=None):
        self.net = net_mgr
        self.log = log_cb or (lambda m: None)
        self.assets = []
        self.lock = threading.RLock()
        self.load_state()

    def load_state(self):
        with self.lock:
            if os.path.exists(PORTFOLIO_FILE):
                try:
                    with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.assets = data if isinstance(data, list) else []
                except Exception:
                    self.assets = []
            else:
                self.assets = []

    def save_state(self):
        with self.lock:
            try:
                with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.assets, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.log(f"Lỗi lưu file tài sản Portfolio: {e}")

    def add_or_update_asset(self, symbol, entry_price, quantity=0.0, setup_mode="", notes=""):
        with self.lock:
            now_str = datetime.now(TZ_VN).strftime("%d/%m/%Y %H:%M:%S")
            found = False
            for a in self.assets:
                if a["symbol"] == symbol:
                    if quantity > 0:
                        total_qty = a.get("quantity", 0.0) + quantity
                        total_cost = (a.get("entry_price", entry_price) * a.get("quantity", 0.0)) + (entry_price * quantity)
                        a["entry_price"] = total_cost / total_qty if total_qty > 0 else entry_price
                        a["quantity"] = total_qty
                    else:
                        a["entry_price"] = entry_price
                    a["updated_time_vn"] = now_str
                    found = True
                    break

            if not found:
                calc_qty = quantity if quantity > 0 else (100.0 / entry_price if entry_price > 0 else 1.0)
                item = {
                    "symbol": symbol,
                    "entry_price": float(entry_price),
                    "current_price": float(entry_price),
                    "quantity": float(calc_qty),
                    "diff_pct": 0.0,
                    "recommendation": "THEO DÕI NẮM GIỮ (Vừa khớp Entry)",
                    "setup_mode": setup_mode,
                    "added_time_vn": now_str,
                    "updated_time_vn": now_str
                }
                self.assets.insert(0, item)

        self.save_state()

    def delete_asset(self, symbol):
        with self.lock:
            b_len = len(self.assets)
            self.assets = [a for a in self.assets if a.get("symbol") != symbol]
            a_len = len(self.assets)
        self.save_state()
        return (b_len != a_len)

    def clear_all(self):
        with self.lock:
            self.assets = []
        if os.path.exists(PORTFOLIO_FILE):
            try: os.remove(PORTFOLIO_FILE)
            except Exception: pass

    def get_assets(self):
        with self.lock:
            return list(self.assets)

    def evaluate_technical_recommendation(self, symbol, entry_p, curr_p, diff_pct):
        try:
            klines_30m = self.net.get_klines(symbol, interval="30m", limit=80)
            if not klines_30m or len(klines_30m) < 30:
                if diff_pct >= 5.0:
                    return "GỒNG LÃI TỐT / CÂN NHẮC CHỐT TP1 (+5% trở lên)", COLOR_PALETTE["bull_green"]
                elif diff_pct <= -4.0:
                    return "CẢNH BÁO LỖ / XEM XÉT THOÁT PHÒNG THỦ", COLOR_PALETTE["bear_red"]
                return "TIẾP TỤC NẮM GIỮ (Theo dõi biến động)", COLOR_PALETTE["accent_cyan"]

            closes = [k["close"] for k in klines_30m]
            rsi = TechnicalEngine.calc_rsi(closes, 14)
            ema20 = TechnicalEngine.calc_ema(closes, 20)[-1]
            zlema20 = TechnicalEngine.calc_zlema(closes, 20)[-1]
            ema50 = TechnicalEngine.calc_ema(closes, 50)[-1]
            macd_l, sig_l, hist, hist_delta, _ = TechnicalEngine.calc_macd(closes)

            if rsi >= 82.0:
                return f"CHỐT LỜI CHỦ ĐỘNG 50-70% (RSI {rsi:.1f} cực đại, rủi ro điều chỉnh)", COLOR_PALETTE["gold"]

            if diff_pct > 0:
                if curr_p >= zlema20 and hist > 0:
                    if diff_pct >= 6.0:
                        return f"GỒNG TIẾP (Xu hướng khỏe trên ZLEMA, dời SL lên {format_price(entry_p * 1.02)} để khóa lãi)", COLOR_PALETTE["bull_green"]
                    return f"TIẾP TỤC NẮM GIỮ (Đang trên ZLEMA20 & EMA20, MACD dương, Lãi +{diff_pct:.2f}%)", COLOR_PALETTE["bull_green"]
                elif curr_p < zlema20:
                    return f"NÂNG SL HÒA VỐN / KHÓA LÃI 1 PHẦN (Thủng ZLEMA20 phản ứng sớm)", COLOR_PALETTE["orange"]
                else:
                    return f"GỒNG LÃI / THEO DÕI TP MỤC TIÊU (+{diff_pct:.2f}%)", COLOR_PALETTE["accent_cyan"]
            else:
                if diff_pct <= -5.0:
                    return f"CẢNH BÁO RỦI RO: ĐÃ LỖ {diff_pct:.2f}% (Ưu tiên cắt bảo toàn vốn)", COLOR_PALETTE["bear_red"]
                elif curr_p < ema50 and hist < 0:
                    return f"SUY YẾU CẤU TRÚC (Dưới EMA50, giảm tỷ trọng nếu thủng hỗ trợ)", COLOR_PALETTE["bear_red"]
                elif rsi <= 32.0:
                    return f"QUÁ BÁN CỰC ĐỘ (RSI {rsi:.1f} - Chờ nhịp hồi kỹ thuật để cơ cấu)", COLOR_PALETTE["purple"]
                else:
                    return f"TIẾP TỤC NẮM GIỮ / THEO DÕI SL ĐÃ ĐẶT ({diff_pct:.2f}%)", COLOR_PALETTE["text_muted"]

        except Exception:
            return "TIẾP TỤC NẮM GIỮ (Theo dõi)", COLOR_PALETTE["text_muted"]

    def refresh_assets_market(self):
        with self.lock:
            if not self.assets:
                return 0

        updated = 0
        with self.lock:
            symbols = [a["symbol"] for a in self.assets]

        for sym in symbols:
            t_info = self.net.fetch_json("/api/v3/ticker/24hr", params={"symbol": sym})
            if not t_info or not isinstance(t_info, dict):
                continue

            last_p = float(t_info.get("lastPrice", 0.0))
            if last_p <= 0:
                continue

            with self.lock:
                for a in self.assets:
                    if a["symbol"] == sym:
                        a["current_price"] = last_p
                        e_p = a.get("entry_price", last_p)
                        diff = ((last_p - e_p) / e_p * 100.0) if e_p > 0 else 0.0
                        a["diff_pct"] = round(diff, 2)
                        rec_txt, _ = self.evaluate_technical_recommendation(sym, e_p, last_p, diff)
                        a["recommendation"] = rec_txt
                        a["updated_time_vn"] = datetime.now(TZ_VN).strftime("%d/%m/%Y %H:%M:%S")
                        updated += 1
                        break

        self.save_state()
        return updated


# ==============================================================================
# VII. BỘ GHI NHẬN & QUẢN LÝ HIỆU SUẤT THỰC TẾ 12H
# ==============================================================================
class PerformanceTracker:
    def __init__(self, net_mgr, asset_mgr, log_cb=None):
        self.net = net_mgr
        self.asset_mgr = asset_mgr
        self.log = log_cb or (lambda m: None)
        self.trades = []
        self.lock = threading.RLock()
        self.load_state()

    def load_state(self):
        with self.lock:
            if os.path.exists(PERF_DATA_FILE):
                try:
                    with open(PERF_DATA_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        self.trades = data if isinstance(data, list) else []
                        for t in self.trades:
                            st = t.get("status", "PENDING")
                            if st in ("OPEN", "WIN_TP1", "WIN_TP2", "WIN_TP3", "WIN_TP1_BE", "LOSS_SL", "EXPIRED_WIN", "EXPIRED_LOSS"):
                                t["is_filled"] = True
                                if not t.get("fill_time_vn"):
                                    t["fill_time_vn"] = t.get("start_time_vn", "")
                            elif st in ("PENDING", "EXPIRED_CANCEL"):
                                t["is_filled"] = False
                except Exception:
                    self.trades = []
            else:
                self.trades = []

    def save_state(self):
        with self.lock:
            try:
                with open(PERF_DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.trades, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.log(f"Lỗi lưu file JSON hiệu suất: {e}")
        try:
            self.export_text_report()
        except Exception:
            pass

    def record_trade(self, coin, entry_custom=None, coin_qty=0.0, notify_cb=None):
        sym = coin.get("symbol", "")
        ote = coin.get("ote", {})
        sm = coin.get("setup_mode", "THEO_DÕI")
        now_ts = time.time()

        entry_val = float(entry_custom) if (entry_custom and float(entry_custom) > 0) else ote.get("entry", coin.get("price", 0.0))
        atr_val = ote.get("atr", entry_val * 0.02)
        calc_res = InstitutionalRiskManager.calculate_levels_from_custom_entry(entry_val, atr_val)

        sl_val = calc_res["sl"] if calc_res else ote.get("sl", entry_val * 0.97)
        tp1_val = calc_res["tp1"] if calc_res else ote.get("tp1", entry_val * 1.03)
        tp2_val = calc_res["tp2"] if calc_res else ote.get("tp2", entry_val * 1.05)
        tp3_val = calc_res["tp3"] if calc_res else ote.get("tp3", entry_val * 1.08)

        risk_p = calc_res["risk_pct"] if calc_res else round(((entry_val - sl_val) / entry_val) * 100.0, 2)
        tp1_p = calc_res["tp1_pct"] if calc_res else round(((tp1_val - entry_val) / entry_val) * 100.0, 2)
        tp2_p = calc_res["tp2_pct"] if calc_res else round(((tp2_val - entry_val) / entry_val) * 100.0, 2)
        tp3_p = calc_res["tp3_pct"] if calc_res else round(((tp3_val - entry_val) / entry_val) * 100.0, 2)

        with self.lock:
            for t in self.trades:
                if t["symbol"] == sym and t["status"] in ("PENDING", "OPEN", "WIN_TP1", "WIN_TP2") and (now_ts - t["start_ts"] < 900):
                    return False, f"Mã {sym} đang được theo dõi trong vòng 15 phút qua."

        rec = {
            "id": f"{sym}_{int(now_ts)}",
            "symbol": sym,
            "setup_mode": sm,
            "score": coin.get("score", 50),
            "start_ts": now_ts,
            "start_time_vn": datetime.now(TZ_VN).strftime("%d/%m/%Y %H:%M:%S"),
            "fill_time_vn": "",
            "is_filled": False,
            "entry": entry_val,
            "quantity": coin_qty,
            "sl": sl_val,
            "original_sl": sl_val,
            "tp1": tp1_val,
            "tp2": tp2_val,
            "tp3": tp3_val,
            "risk_pct": risk_p,
            "tp1_pct": tp1_p,
            "tp2_pct": tp2_p,
            "tp3_pct": tp3_p,
            "status": "PENDING",
            "end_time_vn": "",
            "result_desc": "Đang chờ khớp Order Entry...",
            "highest_p": entry_val,
            "lowest_p": entry_val
        }

        with self.lock:
            self.trades.insert(0, rec)
        self.save_state()

        if notify_cb:
            notify_cb(rec)

        return True, f"Đã đặt Order {sym} [{sm}] vào danh sách Tab Giám Sát."

    def delete_single_trade(self, trade_id):
        with self.lock:
            before_len = len(self.trades)
            self.trades = [t for t in self.trades if t.get("id") != trade_id]
            after_len = len(self.trades)
        self.save_state()
        return (before_len != after_len)

    def audit_active_trades(self, notify_cb=None, on_entry_filled_cb=None):
        try:
            with self.lock:
                open_indices = [idx for idx, t in enumerate(self.trades) if t["status"] in ("PENDING", "OPEN", "WIN_TP1", "WIN_TP2")]

            if not open_indices:
                return 0

            updated_count = 0
            now_ts = time.time()

            for idx in open_indices:
                with self.lock:
                    if idx >= len(self.trades):
                        continue
                    trade = self.trades[idx]

                sym = trade["symbol"]
                elapsed_sec = now_ts - trade["start_ts"]
                elapsed_hours = elapsed_sec / 3600.0
                h_str = int(elapsed_sec // 3600)
                m_str = int((elapsed_sec % 3600) // 60)

                if elapsed_hours >= 12.0:
                    t_info = self.net.fetch_json("/api/v3/ticker/24hr", params={"symbol": sym})
                    curr_p = float(t_info.get("lastPrice", trade["entry"])) if t_info and isinstance(t_info, dict) else trade["entry"]

                    with self.lock:
                        if not trade.get("is_filled", False):
                            trade["status"] = "EXPIRED_CANCEL"
                            trade["result_desc"] = f"Hết 12h: Chưa khớp Order Entry {format_price(trade['entry'])} (Hủy giám sát)"
                        else:
                            diff_pct = ((curr_p - trade["entry"]) / trade["entry"]) * 100.0 if trade["entry"] > 0 else 0.0
                            if diff_pct >= 0:
                                trade["status"] = "EXPIRED_WIN"
                                trade["result_desc"] = f"Hết 12h: Lãi +{diff_pct:.2f}% (Giá {format_price(curr_p)})"
                            else:
                                trade["status"] = "EXPIRED_LOSS"
                                trade["result_desc"] = f"Hết 12h: Lỗ {diff_pct:.2f}% (Giá {format_price(curr_p)})"
                        trade["end_time_vn"] = datetime.now(TZ_VN).strftime("%d/%m/%Y %H:%M:%S")

                    if notify_cb:
                        notify_cb(trade)
                    updated_count += 1
                    continue

                klines = self.net.get_klines(sym, interval="15m", limit=50)
                if not klines:
                    continue

                valid_k = [k for k in klines if k["open_time"] >= (trade["start_ts"] * 1000 - 60000)]
                if not valid_k:
                    valid_k = [klines[-1]]

                status_changed = False
                for k in valid_k:
                    kh = k["high"]
                    kl = k["low"]
                    k_time_vn = datetime.fromtimestamp(k["open_time"] / 1000.0, tz=TZ_VN).strftime("%d/%m %H:%M")

                    if not trade.get("is_filled", False):
                        if kl <= trade["entry"]:
                            with self.lock:
                                trade["is_filled"] = True
                                trade["status"] = "OPEN"
                                trade["fill_time_vn"] = k_time_vn
                                trade["result_desc"] = f"Đã khớp Entry lúc {k_time_vn} (Giá {format_price(trade['entry'])})"
                            
                            status_changed = True

                            self.asset_mgr.add_or_update_asset(
                                symbol=trade["symbol"],
                                entry_price=trade["entry"],
                                quantity=trade.get("quantity", 0.0),
                                setup_mode=trade.get("setup_mode", "")
                            )
                            self.log(f"[TAB 5 TỰ ĐỘNG NẠP]: {trade['symbol']} đã khớp Entry {format_price(trade['entry'])} -> Thêm vào Quản lý tài sản.")

                            if on_entry_filled_cb:
                                on_entry_filled_cb(trade)

                            if notify_cb:
                                notify_cb(trade)
                        else:
                            continue

                    with self.lock:
                        if kh > trade["highest_p"]: trade["highest_p"] = kh
                        if kl < trade["lowest_p"]: trade["lowest_p"] = kl

                    if kl <= trade["sl"] and kh < trade["tp1"]:
                        with self.lock:
                            if trade["status"] in ("WIN_TP1", "WIN_TP2"):
                                trade["status"] = "WIN_TP1_BE"
                                trade["result_desc"] = f"Sau TP1 đã về Hòa Vốn ({format_price(trade['sl'])}) lúc {k_time_vn}"
                            else:
                                trade["status"] = "LOSS_SL"
                                trade["result_desc"] = f"Chạm SL {format_price(trade['sl'])} lúc {k_time_vn} (-{trade['risk_pct']}%)"
                            trade["end_time_vn"] = datetime.now(TZ_VN).strftime("%d/%m/%Y %H:%M:%S")
                        status_changed = True
                        if notify_cb:
                            notify_cb(trade)
                        break

                    elif kh >= trade["tp3"]:
                        with self.lock:
                            trade["status"] = "WIN_TP3"
                            trade["result_desc"] = f"Chạm TP3 {format_price(trade['tp3'])} lúc {k_time_vn} (+{trade['tp3_pct']}%)"
                            trade["end_time_vn"] = datetime.now(TZ_VN).strftime("%d/%m/%Y %H:%M:%S")
                        status_changed = True
                        if notify_cb:
                            notify_cb(trade)
                        break

                    elif kh >= trade["tp2"] and trade["status"] in ("OPEN", "WIN_TP1"):
                        with self.lock:
                            trade["status"] = "WIN_TP2"
                            trade["sl"] = trade["entry"]
                            trade["result_desc"] = f"Chạm TP2 {format_price(trade['tp2'])} lúc {k_time_vn} (+{trade['tp2_pct']}%) | Đã dời SL hòa vốn"
                        status_changed = True
                        if notify_cb:
                            notify_cb(trade)

                    elif kh >= trade["tp1"] and trade["status"] == "OPEN":
                        with self.lock:
                            trade["status"] = "WIN_TP1"
                            trade["sl"] = trade["entry"]
                            trade["result_desc"] = f"Chạm TP1 {format_price(trade['tp1'])} (+{trade['tp1_pct']}%) lúc {k_time_vn} | Đã dời SL hòa vốn"
                        status_changed = True
                        if notify_cb:
                            notify_cb(trade)

                if status_changed:
                    updated_count += 1
                else:
                    with self.lock:
                        curr_last = valid_k[-1]["close"]
                        if not trade.get("is_filled", False):
                            trade["result_desc"] = f"Đang chờ khớp Order ({h_str:02d}h{m_str:02d}m) | Thị giá {format_price(curr_last)}"
                        else:
                            diff_now = ((curr_last - trade["entry"]) / trade["entry"]) * 100.0 if trade["entry"] > 0 else 0.0
                            sub_tag = f" [{trade['status']}]" if trade["status"] != "OPEN" else ""
                            trade["result_desc"] = f"Đang chạy ({h_str:02d}h{m_str:02d}m){sub_tag} | Thị giá {format_price(curr_last)} ({diff_now:+.2f}%)"

            self.save_state()
            return updated_count
        except Exception:
            return 0

    def get_statistics(self):
        with self.lock:
            trades = list(self.trades)

        total = len(trades)
        completed = [t for t in trades if t["status"] not in ("PENDING", "OPEN", "WIN_TP1", "WIN_TP2")]
        open_trades = [t for t in trades if t["status"] in ("PENDING", "OPEN", "WIN_TP1", "WIN_TP2")]
        wins = [t for t in completed if "WIN" in t["status"] or t["status"] == "EXPIRED_WIN"]
        losses = [t for t in completed if t["status"] in ("LOSS_SL", "EXPIRED_LOSS")]

        win_rate = (len(wins) / len(completed) * 100.0) if completed else 0.0

        setup_stats = {}
        for sm in ("WAVE_3", "WAVE_2", "BREAKOUT", "PULLBACK", "SWEEP", "THEO_DÕI"):
            m_comp = [t for t in completed if t.get("setup_mode") == sm]
            m_win = [t for t in m_comp if "WIN" in t["status"] or t["status"] == "EXPIRED_WIN"]
            m_wr = (len(m_win) / len(m_comp) * 100.0) if m_comp else 0.0
            setup_stats[sm] = {
                "total": len(m_comp),
                "wins": len(m_win),
                "losses": len(m_comp) - len(m_win),
                "win_rate": m_wr
            }

        return {
            "total": total,
            "completed": len(completed),
            "open": len(open_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "by_setup": setup_stats,
            "trades": trades
        }

    def export_text_report(self):
        try:
            stats = self.get_statistics()
            now_str = datetime.now(TZ_VN).strftime("%d/%m/%Y %H:%M:%S (GMT+7)")

            lines = [
                "=" * 85,
                "BÁO CÁO THỰC TẾ & XÁC SUẤT THẮNG LỆNH SPOT (KIỂM ĐỊNH HIỆU SUẤT THỰC TẾ)",
                f"Thời gian cập nhật: {now_str}",
                "=" * 85,
                f"• Tổng số lệnh đã ghi nhận : {stats['total']}",
                f"• Lệnh đã hoàn tất kết quả : {stats['completed']} (Thắng: {stats['wins']} | Thua: {stats['losses']})",
                f"• Lệnh đang trong 12h theo dõi: {stats['open']}",
                f"• TỶ LỆ THẮNG TỔNG THỂ (TP1+): {stats['win_rate']:.2f}%",
                "-" * 85,
                "XÁC SUẤT THẮNG THEO TỪNG MÔ HÌNH SETUP KỸ THUẬT:",
            ]

            names = {
                "WAVE_3": "Sóng 3 Elliott",
                "WAVE_2": "Sóng 2 Elliott",
                "BREAKOUT": "Bứt phá dải nén",
                "PULLBACK": "Thoái lui OTE",
                "SWEEP": "Quét thanh khoản",
                "THEO_DÕI": "Theo dõi nền"
            }

            for sm, s in stats["by_setup"].items():
                lines.append(f"  - [{names.get(sm, sm)}]: {s['wins']}/{s['total']} Thắng ({s['win_rate']:.1f}%) | {s['losses']} Thua")

            lines.extend([
                "-" * 85,
                "NHẬT KÝ CHI TIẾT TỪNG VỊ THẾ ĐÃ GHI NHẬN (MỚI NHẤT LÊN ĐẦU):",
                "-" * 85
            ])

            if not stats["trades"]:
                lines.append("Chưa có lệnh nào được ghi nhận.")
            else:
                for idx, t in enumerate(stats["trades"], 1):
                    end_str = t.get('end_time_vn', '')
                    fill_str = t.get('fill_time_vn', '')
                    time_line = f"Đặt Order: {t['start_time_vn']} | Khớp Entry: {fill_str if fill_str else 'Chờ khớp...'} | Kết thúc: {end_str if end_str else 'Đang chạy...'}"
                    lines.append(f"#{idx:02d} | Mã: {t['symbol']} | Mô hình: [{t['setup_mode']}] | {time_line}")
                    
                    is_be = t.get("status") in ("WIN_TP1", "WIN_TP2", "WIN_TP1_BE")
                    sl_desc = f"{format_price(t['sl'])} (Hòa Vốn - 0.0%)" if is_be else f"{format_price(t['sl'])} (-{t['risk_pct']}%)"
                    lines.append(f"     Order Entry: {format_price(t['entry'])} | SL: {sl_desc} | TP1: {format_price(t['tp1'])} (+{t['tp1_pct']}%)")
                    lines.append(f"     Trạng thái: [{t['status']}] ➔ {t['result_desc']}")
                    lines.append("-" * 40)

            lines.append("")

            with open(PERF_LOG_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass

    def clear_all(self):
        with self.lock:
            self.trades = []
        if os.path.exists(PERF_DATA_FILE):
            try: os.remove(PERF_DATA_FILE)
            except Exception: pass
        self.export_text_report()



# ==============================================================================
# X. ENGINE TRUNG TÂM (THAY CHO CONTROLLER TKINTER) - GIAO TIẾP UI QUA SỰ KIỆN
# ==============================================================================
class Engine:
    """Toàn bộ logic nền. UI đăng ký handler bằng engine.on(tên_sự_kiện, hàm).
    Mọi handler được chạy trên luồng UI thông qua engine.ui_dispatch (do main.py gán)."""

    def __init__(self):
        self.is_running = True
        self.log_lines = collections.deque(maxlen=300)
        self.handlers = {}
        self.ui_dispatch = lambda fn: fn()
        self._settings_lock = threading.RLock()

        self.net = BinanceNetworkManager()
        self.asset_mgr = AssetManager(self.net, self.add_log)
        self.perf_tracker = PerformanceTracker(self.net, self.asset_mgr, self.add_log)

        self.is_scanning = False
        self.scanned_results = []
        self.selected_coin = None

        saved_cfg = self.load_settings()
        self.auto_scan_send_webhook = bool(saved_cfg.get("auto_webhook", False))

        self.perf_monitor_active = True
        self.perf_cycle = "5m"
        self.cached_perf_cycle_sec = 300
        self.perf_countdown_sec = 300

        self.btc_status = {
            "regime": "Green",
            "desc": "Khởi tạo hệ thống...",
            "color": COLOR_PALETTE["bull_green"],
            "micro_trend_15m": True
        }

    # ---------------- sự kiện ----------------
    def on(self, name, fn):
        self.handlers.setdefault(name, []).append(fn)

    def emit(self, name, **kw):
        for h in list(self.handlers.get(name, [])):
            try:
                self.ui_dispatch(lambda h=h: h(**kw))
            except Exception:
                pass

    def run_on_ui(self, fn, *args):
        if self.is_running:
            self.ui_dispatch(lambda: fn(*args))

    def add_log(self, msg):
        ts = datetime.now(TZ_VN).strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        print(line)
        self.emit("log", line=line)

    def shutdown(self):
        self.is_running = False
        self.perf_monitor_active = False

    def settings_get(self, key, default=None):
        return self.load_settings().get(key, default)

    def start_background(self):
        threading.Thread(target=self._perf_monitor_worker, daemon=True).start()

    # ---------------- cài đặt chung ----------------
    def load_settings(self):
        with self._settings_lock:
            return self._load_settings_nolock()

    def _load_settings_nolock(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception:
                return {}
        return {}

    def save_setting_key(self, key, value):
        try:
            with self._settings_lock:
                settings = self._load_settings_nolock()
                settings[key] = value
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.add_log(f"Lỗi lưu cài đặt ({key}): {e}")

    # ---------------- logic đề xuất & webhook ----------------
    def get_position_recommendation(self, coin):
        sm = coin.get("setup_mode", "THEO_DÕI")
        score = coin.get("score", 50)
        btc_reg = self.btc_status.get("regime", "Green")
        btc_15m_ok = self.btc_status.get("micro_trend_15m", True)
        meta = coin.get("meta", {})
        rsi_val = meta.get("rsi", 50.0)

        if meta.get("veto_triggered", False):
            return f"CẢNH BÁO PHỦ QUYẾT: {meta.get('veto_reason', 'Rủi ro bẫy giá')}", COLOR_PALETTE["bear_red"]

        if rsi_val > FILTER_CFG.get("rsi_overbought_threshold"):
            return f"CẢNH BÁO FOMO QUÁ MUA (RSI > {FILTER_CFG.get('rsi_overbought_threshold'):g}) - RỦI RO ĐIỀU CHỈNH CAO", COLOR_PALETTE["gold"]

        if not btc_15m_ok:
            return "TẠM DỪNG MỞ VỊ THẾ (BTC 15m đang dưới EMA20 - Rủi ro xả ngắn hạn)", COLOR_PALETTE["bear_red"]

        if btc_reg == "Red":
            return "MUA PHÒNG THỦ THĂM DÒ / ĐỨNG NGOÀI (Thị trường rủi ro)", COLOR_PALETTE["bear_red"]

        if sm == "WAVE_3":
            return "LONG / ĐẶT LIMIT RETEST ĐỈNH H1 (Kháng cự cũ -> Hỗ trợ mới)", COLOR_PALETTE["orange"]
        elif sm == "WAVE_2":
            return "LONG / ĐẶT LIMIT ĐÓN CHÂN SÓNG (Fib Golden Pocket & CVD Div)", COLOR_PALETTE["purple"]
        elif sm == "BREAKOUT":
            return "LONG / MUA PHÁ VỠ DẢI NÉN (Bollinger & ZLEMA Ribbon Squeeze)", COLOR_PALETTE["gold"]
        elif sm == "PULLBACK":
            return "LONG / ĐẶT LIMIT THOÁI LUI OTE (Hội tụ ZLEMA21 & POC)", COLOR_PALETTE["accent_cyan"]
        elif sm == "SWEEP":
            return "LONG / BẮT PHẢN ỨNG RÚT RÂU ĐẢO CHIỀU (Liquidity Sweep)", COLOR_PALETTE["bull_green"]
        else:
            if score >= 65:
                return "MUA THĂM DÒ TỶ TRỌNG VỪA (Theo dõi nhịp bứt phá)", COLOR_PALETTE["accent_blue"]
            return "QUAN SÁT TÍCH LŨY (Chờ tín hiệu xác nhận dòng tiền)", COLOR_PALETTE["text_muted"]

    # --------------------------------------------------------------------------
    # KHỞI TẠO TOP BAR, NAV TABS VÀ BOTTOM STATUS
    # --------------------------------------------------------------------------

    def dispatch_monitor_status_webhook(self, trade):
        if not self.auto_scan_send_webhook:
            return

        url = str(self.settings_get("webhook_url", "")).strip()
        if not url.startswith("http") or "<TOKEN>" in url:
            return

        status_tag_map = {
            "PENDING": "DA DAT ORDER CHO KHOP",
            "OPEN": "DA KHOP ORDER ENTRY (DA NAP TAB 5)",
            "WIN_TP1": "CHAM TP1 (DA DOI SL VE HOA VON)",
            "WIN_TP2": "CHAM TP2 (+1.8R)",
            "WIN_TP3": "CHAM TP3 (MAX PROFIT)",
            "WIN_TP1_BE": "VE HOA VON (SAU KHI CHAM TP1)",
            "LOSS_SL": "CHAM CAT LO (SL)",
            "EXPIRED_WIN": "HET 12H GIAM SAT (DANG LAI)",
            "EXPIRED_LOSS": "HET 12H GIAM SAT (DANG LO)",
            "EXPIRED_CANCEL": "HET 12H GIAM SAT (HUY VI CHUA KHOP)"
        }

        st = trade.get("status", "OPEN")
        tag_title = status_tag_map.get(st, f"CAP NHAT TRANG THAI [{st}]")
        is_be = st in ("WIN_TP1", "WIN_TP2", "WIN_TP1_BE")
        sl_desc = f"{format_price(trade['sl'])} (Hòa Vốn - 0.0%)" if is_be else f"{format_price(trade['sl'])} (-{trade['risk_pct']}%)"

        html_msg = (
            f"<b>[GIAM SAT VI THE - {tag_title}]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Mã giao dịch</b>: <code>{trade['symbol']}</code> [{trade['setup_mode']}]\n"
            f"• <b>Giá đặt Entry</b>: <code>{format_price(trade['entry'])} USDT</code>\n"
            f"• <b>Cắt lỗ (SL)</b>: <code>{sl_desc}</code>\n"
            f"• <b>Chốt lời TP1</b>: <code>{format_price(trade['tp1'])}</code> (+{trade['tp1_pct']}%)\n"
            f"• <b>Chốt lời TP2</b>: <code>{format_price(trade['tp2'])}</code> (+{trade['tp2_pct']}%)\n"
            f"• <b>Khớp lúc</b>: {trade.get('fill_time_vn') if trade.get('fill_time_vn') else 'Chưa khớp'}\n"
            f"• <b>Chi tiết</b>: <i>{trade['result_desc']}</i>\n"
            f"• <b>Thời gian</b>: {datetime.now(TZ_VN).strftime('%H:%M:%S - %d/%m/%Y')}"
        )
        threading.Thread(target=self.send_raw_webhook, args=(url, html_msg), daemon=True).start()

    def send_raw_webhook(self, url, html_msg):
        try:
            payload = {"text": html_msg, "parse_mode": "HTML"}
            if "api.telegram.org" in url:
                parsed = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed.query)
                if "chat_id" in qs:
                    payload["chat_id"] = qs["chat_id"][0]
            elif "discord.com" in url:
                payload = {"content": html_msg.replace("<b>", "**").replace("</b>", "**").replace("<code>", "`").replace("</code>", "`")}

            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
            ctx = make_ssl_context()
            with urllib.request.urlopen(req, context=ctx, timeout=8) as r:
                self.add_log(f"Đã gửi cảnh báo Webhook: HTTP {r.status}")
        except Exception as e:
            self.add_log(f"Lỗi gửi Webhook: {str(e)}")


    # ---------------- kết nối ----------------
    def check_connection(self):
        def _worker():
            self.emit("conn", state="testing", ms=0)
            p = self.net.get_ping()
            if p >= 0:
                self.emit("conn", state="live", ms=p)
                self.add_log(f"Kiểm tra kết nối thành công. Độ trễ: {p} ms.")
            else:
                self.emit("conn", state="down", ms=-1)
                self.add_log("Lỗi kết nối máy chủ Binance.")
        threading.Thread(target=_worker, daemon=True).start()

    # ---------------- quét ----------------
    def start_screener_thread(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.emit("scan_start")
        self.add_log("=== BẮT ĐẦU CHU KỲ QUÉT TÍN HIỆU ĐỊNH LƯỢNG ===")
        threading.Thread(target=self._screener_worker, daemon=True).start()

    def _scan_failed(self):
        self.is_scanning = False
        self.emit("scan_error")

    def custom_scan(self, sym):
        """Quét sâu 1 mã tùy chọn (Tab 2). Kết quả trả qua sự kiện 'custom_scan_done'."""
        self.add_log(f"Kích hoạt quét phân tích chuyên sâu cho {sym}...")

        def _worker():
            try:
                btc_30m = self.net.get_klines("BTCUSDT", interval="30m", limit=300)
                btc_map = {k["open_time"]: k["close"] for k in btc_30m} if btc_30m else {}

                t_info = self.net.fetch_json("/api/v3/ticker/24hr", params={"symbol": sym})
                quote_vol = 0.0
                if t_info and isinstance(t_info, dict):
                    quote_vol = float(t_info.get("quoteVolume", 0.0))
                elif t_info and isinstance(t_info, list) and len(t_info) > 0:
                    quote_vol = float(t_info[0].get("quoteVolume", 0.0))

                res = self.audit_single_symbol(sym, quote_vol, btc_map, is_custom=True)
                if res:
                    self.selected_coin = res
                    for idx, item in enumerate(self.scanned_results):
                        if item["symbol"] == res["symbol"]:
                            self.scanned_results[idx] = res
                            break
                    else:
                        self.scanned_results.insert(0, res)
                    self.add_log(f"Phân tích hoàn tất: {sym} | Setup: {res['setup_mode']} | Điểm: {res['score']}/100.")
                else:
                    self.add_log(f"Không thể phân tích {sym}: Lỗi xử lý chỉ báo hoặc thiếu nến.")
                self.emit("custom_scan_done", symbol=sym, ok=bool(res))
            except Exception as e:
                self.add_log(f"Lỗi phân tích {sym}: {str(e)}")
                self.emit("custom_scan_done", symbol=sym, ok=False)
        threading.Thread(target=_worker, daemon=True).start()

    # ---------------- giám sát hiệu suất ----------------
    def set_perf_cycle(self, val):
        self.perf_cycle = val
        self.cached_perf_cycle_sec = {"5m": 300, "15m": 900, "30m": 1800}.get(val, 900)
        self.perf_countdown_sec = self.cached_perf_cycle_sec
        self.add_log(f"Đã đổi chu kỳ kiểm tra giám sát thành {val} ({self.cached_perf_cycle_sec}s).")

    def toggle_perf_monitor(self):
        self.perf_monitor_active = not self.perf_monitor_active
        self.add_log(f"Tiến trình giám sát 12H tự động: {'BẬT' if self.perf_monitor_active else 'TẮT'}.")
        return self.perf_monitor_active

    def toggle_auto_webhook(self):
        self.auto_scan_send_webhook = not self.auto_scan_send_webhook
        self.save_setting_key("auto_webhook", self.auto_scan_send_webhook)
        self.add_log("Bật tự động gửi Telegram khi có biến động trạng thái." if self.auto_scan_send_webhook else "Tắt gửi Telegram.")
        return self.auto_scan_send_webhook

    def audit_now(self):
        """Đối soát ngay các lệnh đang giám sát (chạy nền)."""
        self.add_log("Đang kiểm tra nến cập nhật hiệu suất các lệnh...")

        def _worker():
            cnt = self.perf_tracker.audit_active_trades(
                notify_cb=self.dispatch_monitor_status_webhook,
                on_entry_filled_cb=lambda t: self.emit("portfolio_refresh")
            )
            self.add_log(f"Kiểm tra giám sát xong: {cnt} lệnh có thay đổi tiến trình.")
            self.emit("monitor_refresh")
        threading.Thread(target=_worker, daemon=True).start()

    def refresh_portfolio(self):
        def _worker():
            cnt = self.asset_mgr.refresh_assets_market()
            self.add_log(f"Tab 5: Đã cập nhật giá & đề xuất kỹ thuật cho {cnt} coin.")
            self.emit("portfolio_done", count=cnt)
        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def webhook_valid(url):
        return bool(url) and url.startswith("http") and "<TOKEN>" not in url

    def send_monitor_list_webhook(self, url):
        stats = self.perf_tracker.get_statistics()
        trades = stats.get("trades", [])
        if not trades:
            msg = (
                f"<b>[CRYPTO SPOT - DANH SÁCH GIÁM SÁT]</b>\n"
                f"Thời gian: {datetime.now(TZ_VN).strftime('%H:%M:%S (GMT+7)')}\n"
                f"<i>Danh sách giám sát hiện tại đang trống (chưa có lệnh nào được thêm từ Tab 3).</i>"
            )
        else:
            lines = [
                f"<b>[BÁO CÁO DANH SÁCH COIN ĐANG GIÁM SÁT]</b>",
                f"Thời gian: {datetime.now(TZ_VN).strftime('%H:%M:%S %d/%m/%Y')}",
                f"Tổng số: <b>{stats['total']}</b> | Đang chạy 12h: <b>{stats['open']}</b> | Thắng: <b>{stats['wins']}</b> | Thua: <b>{stats['losses']}</b>",
                f"━━━━━━━━━━━━━━━━━━━"
            ]
            for idx, t in enumerate(trades[:8], 1):
                is_be = t.get("status") in ("WIN_TP1", "WIN_TP2", "WIN_TP1_BE")
                sl_str = f"{format_price(t['sl'])} (Hòa Vốn)" if is_be else f"{format_price(t['sl'])}"
                lines.append(
                    f"<b>#{idx:02d} {t['symbol']}</b> [{t['setup_mode']}] - <code>[{t['status']}]</code>\n"
                    f"  ├ Entry: {format_price(t['entry'])} | SL: {sl_str}\n"
                    f"  └ <i>{t['result_desc']}</i>"
                )
            if len(trades) > 8:
                lines.append(f"<i>... và còn {len(trades) - 8} coin khác.</i>")
            msg = "\n".join(lines)
        threading.Thread(target=self.send_raw_webhook, args=(url, msg), daemon=True).start()

    def send_portfolio_webhook(self, url):
        self.add_log("Đang tổng hợp dữ liệu real-time danh mục tài sản để gửi Webhook...")

        def _worker():
            try:
                self.asset_mgr.refresh_assets_market()
                assets = self.asset_mgr.get_assets()
                now_str = datetime.now(TZ_VN).strftime('%H:%M:%S - %d/%m/%Y')
                if not assets:
                    msg = (
                        f"<b>[BAO CAO QUAN LY TAI SAN (TAB 5) - REAL-TIME]</b>\n"
                        f"Thời gian: <code>{now_str}</code>\n"
                        f"<i>Danh mục tài sản hiện tại đang trống (chưa có coin nào khớp Entry).</i>"
                    )
                else:
                    total_val = sum(a.get("current_price", 0.0) * a.get("quantity", 0.0) for a in assets)
                    total_cost = sum(a.get("entry_price", 0.0) * a.get("quantity", 0.0) for a in assets)
                    pnl_usd = total_val - total_cost
                    pnl_pct = (pnl_usd / total_cost * 100.0) if total_cost > 0 else 0.0
                    lines = [
                        f"<b>[BAO CAO QUAN LY TAI SAN (TAB 5) - REAL-TIME]</b>",
                        f"Thời gian: <code>{now_str}</code>",
                        f"• Tổng giá trị: <b>${total_val:,.2f} USDT</b>",
                        f"• Lãi/Lỗ ròng: <b>{pnl_usd:+,.2f} USDT ({pnl_pct:+.2f}%)</b>",
                        f"• Số lượng coin nắm giữ: <b>{len(assets)} mã</b>",
                        f"━━━━━━━━━━━━━━━━━━━"
                    ]
                    for idx, a in enumerate(assets, 1):
                        diff = a.get("diff_pct", 0.0)
                        sign = "+" if diff >= 0 else ""
                        val = a.get("current_price", 0.0) * a.get("quantity", 0.0)
                        lines.append(
                            f"<b>#{idx:02d} {a['symbol']}</b>: {sign}{diff:.2f}%\n"
                            f"  ├ Entry: <code>{format_price(a.get('entry_price', 0.0))}</code> | Hiện tại: <code>{format_price(a.get('current_price', 0.0))}</code>\n"
                            f"  ├ Số lượng: {a.get('quantity', 0.0):,.4f} (~${val:,.2f} USDT)\n"
                            f"  └ <b>Đề xuất</b>: <i>{a.get('recommendation', 'Theo dõi')}</i>"
                        )
                    msg = "\n".join(lines)
                self.send_raw_webhook(url, msg)
                self.emit("portfolio_webhook_sent")
            except Exception as e:
                self.add_log(f"Lỗi gửi báo cáo tài sản: {str(e)}")
        threading.Thread(target=_worker, daemon=True).start()

    def _perf_monitor_worker(self):
        self.perf_countdown_sec = self.cached_perf_cycle_sec
        while self.is_running:
            time.sleep(1)
            if not self.is_running:
                return
            if self.perf_countdown_sec > self.cached_perf_cycle_sec:
                self.perf_countdown_sec = self.cached_perf_cycle_sec

            self.perf_countdown_sec -= 1
            mins = max(0, self.perf_countdown_sec // 60)
            secs = max(0, self.perf_countdown_sec % 60)
            self.emit("perf_tick", m=mins, s=secs, cycle=self.perf_cycle, active=self.perf_monitor_active)

            if self.perf_countdown_sec <= 0:
                self.perf_countdown_sec = self.cached_perf_cycle_sec
                if not self.perf_monitor_active:
                    continue
                try:
                    stats = self.perf_tracker.get_statistics()
                    if stats["open"] == 0:
                        self.add_log(f"Chu kỳ {self.perf_cycle}: Danh sách giám sát trống (0 coin) -> Bỏ qua đối soát.")
                        continue
                    self.add_log(f"Đến chu kỳ {self.perf_cycle}: Bắt đầu đối soát nến các lệnh đang mở...")
                    cnt = self.perf_tracker.audit_active_trades(
                        notify_cb=self.dispatch_monitor_status_webhook,
                        on_entry_filled_cb=lambda t: self.emit("portfolio_refresh")
                    )
                    self.add_log(f"Đối soát xong: {cnt} lệnh có biến động kết quả.")
                    self.emit("monitor_refresh")
                except Exception as e:
                    self.add_log(f"Lỗi đối soát nền: {e}")

    # ---------------- bộ quét ----------------
    def _screener_worker(self):
        try:
            tickers = self.net.get_24h_tickers()
            if not tickers:
                self.add_log("Không lấy được dữ liệu 24h Ticker từ Binance.")
                self._scan_failed()
                return

            btc_chg = 0.0
            for t in tickers:
                if t.get("symbol") == "BTCUSDT":
                    try:
                        btc_chg = float(t.get("priceChangePercent", 0.0))
                    except Exception:
                        pass
                    break

            cfg = FILTER_CFG.snapshot()
            btc_klines_4h = self.net.get_klines("BTCUSDT", interval="4h", limit=300)
            btc_regime = "Green"
            btc_col = COLOR_PALETTE["bull_green"]

            if btc_chg < -2.0:
                btc_regime = "Red"
                btc_col = COLOR_PALETTE["bear_red"]
            elif btc_chg > 3.5:
                btc_regime = "Yellow"
                btc_col = COLOR_PALETTE["gold"]
            elif btc_klines_4h and len(btc_klines_4h) >= 200:
                c_btc = [k["close"] for k in btc_klines_4h]
                ema200_btc = TechnicalEngine.calc_ema(c_btc, 200)[-1]
                if c_btc[-1] < ema200_btc:
                    btc_regime = "Yellow"
                    btc_col = COLOR_PALETTE["gold"]

            if btc_regime == "Red" and cfg["btc_red_veto"]:
                self.add_log("VETO: BTC Red & chế độ Veto tuyệt đối đang BẬT - không xuất tín hiệu.")

            btc_klines_15m = self.net.get_klines("BTCUSDT", interval="15m", limit=60)
            btc_15m_ok = True
            if btc_klines_15m and len(btc_klines_15m) >= 20:
                c_15m_btc = [k["close"] for k in btc_klines_15m]
                ema200_15m_btc = TechnicalEngine.calc_ema(c_15m_btc, 20)[-1]
                if c_15m_btc[-1] < ema200_15m_btc:
                    btc_15m_ok = False
                    self.add_log(f"Cảnh báo: BTC đang DƯỚI EMA20 15m - Tạm thắt chặt bộ lọc.")

            self.btc_status = {
                "regime": btc_regime,
                "color": btc_col,
                "micro_trend_15m": btc_15m_ok
            }
            status_text = f"[BTC: {btc_regime}]" if btc_15m_ok else f"[BTC: {btc_regime} - 15m Retest]"
            self.emit("btc_status", text=status_text, color=btc_col)

            candidates = []
            for t in tickers:
                sym = t.get("symbol", "")
                if not sym.endswith("USDT") or sym == "BTCUSDT" or any(sym.endswith(sfx) for sfx in LEVERAGED_SUFFIXES):
                    continue
                
                base = sym[:-4]
                if base in STABLECOINS or base.startswith("USD") or base.endswith("USD") or base in {"U", "USD"}:
                    continue

                try:
                    vol = float(t.get("quoteVolume", 0.0))
                    chg = float(t.get("priceChangePercent", 0.0))
                    last_p = float(t.get("lastPrice", 0.0))
                    high_p = float(t.get("highPrice", 0.0))
                    low_p = float(t.get("lowPrice", 0.0))
                except Exception:
                    continue

                range_span = high_p - low_p
                range_pos = (last_p - low_p) / range_span if range_span > 0 else 0.5

                if vol >= cfg["min_quote_volume_24h"] and chg > (btc_chg + cfg["btc_chg_spread"]) and range_pos >= cfg["min_range_position"]:
                    candidates.append({"symbol": sym, "quote_vol": vol, "chg": chg, "range_pos": range_pos})

            candidates.sort(key=lambda x: (x["quote_vol"] * 0.5 + x["range_pos"] * 50.0), reverse=True)
            top_pool = candidates[:int(cfg["top_candidates_pool"])]
            self.add_log(f"Bộ lọc chọn ra {len(top_pool)} cặp Altcoin mạnh nhất (Vol >= ${cfg['min_quote_volume_24h'] / 1e6:g}M).")

            btc_30m = self.net.get_klines("BTCUSDT", interval="30m", limit=300)
            btc_map = {k["open_time"]: k["close"] for k in btc_30m} if btc_30m else {}

            passed_results = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self.audit_single_symbol, c["symbol"], c["quote_vol"], btc_map): c["symbol"] for c in top_pool}
                for f in as_completed(futures):
                    try:
                        res = f.result()
                        if res:
                            passed_results.append(res)
                            self.add_log(f"[PHÁT HIỆN] {res['symbol']} | {res['setup_mode']} (Điểm: {res['score']})")
                    except Exception:
                        continue

            passed_results.sort(key=lambda x: x["score"], reverse=True)
            self.scanned_results = passed_results

            self.add_log(f"Chu kỳ hoàn tất: Tìm thấy {len(passed_results)} cơ hội đạt chuẩn.")
            self.is_scanning = False
            self.emit("scan_done", count=len(passed_results))
        except Exception as e:
            self.add_log(f"Lỗi tiến trình quét: {str(e)}")
            self._scan_failed()

    def audit_single_symbol(self, sym, quote_vol, btc_map, is_custom=False):
        try:
            k_30m = self.net.get_klines(sym, interval="30m", limit=300)
            min_required_bars = 40 if is_custom else 80
            if not k_30m or len(k_30m) < min_required_bars:
                return None

            cfg = FILTER_CFG.snapshot()
            if not is_custom and cfg["btc_red_veto"] and self.btc_status.get("regime") == "Red":
                return None

            closes = [k["close"] for k in k_30m]
            highs = [k["high"] for k in k_30m]
            lows = [k["low"] for k in k_30m]
            opens = [k["open"] for k in k_30m]
            vols = [k["volume"] for k in k_30m]
            curr_p = closes[-1]

            # Gate 1: Bẫy xả
            last_body = abs(closes[-1] - opens[-1])
            upper_wick = highs[-1] - max(closes[-1], opens[-1])
            vol_sma20 = sum(vols[-21:-1]) / 20.0 if len(vols) >= 21 else 1.0
            vol_ratio = vols[-1] / vol_sma20 if vol_sma20 > 0 else 1.0

            veto_triggered = False
            veto_reason = ""
            if upper_wick > cfg["wick_rejection_ratio"] * max(last_body, curr_p * 0.003) and vol_ratio >= cfg["wick_dump_vol_ratio"] and closes[-1] < opens[-1]:
                veto_triggered = True
                veto_reason = "Shooting Star xả vol lớn"

            comp_rs = 0.0
            absorption_btc = False
            if btc_map and len(k_30m) >= 48:
                t_curr = k_30m[-1]["open_time"]
                t_6h = k_30m[-12]["open_time"]
                t_24h = k_30m[-48]["open_time"]
                if t_curr in btc_map and t_6h in btc_map and t_24h in btc_map:
                    btc_ret_6h = (btc_map[t_curr] - btc_map[t_6h]) / btc_map[t_6h] if btc_map[t_6h] > 0 else 0.0
                    alt_ret_6h = (closes[-1] - closes[-12]) / closes[-12] if closes[-12] > 0 else 0.0
                    rs_6h = alt_ret_6h - btc_ret_6h

                    btc_ret_24h = (btc_map[t_curr] - btc_map[t_24h]) / btc_map[t_24h] if btc_map[t_24h] > 0 else 0.0
                    alt_ret_24h = (closes[-1] - closes[-48]) / closes[-48] if closes[-48] > 0 else 0.0
                    rs_24h = alt_ret_24h - btc_ret_24h

                    comp_rs = round(((cfg["rs_weight_6h"] * rs_6h) + (cfg["rs_weight_24h"] * rs_24h)) * 100.0, 2)

                    if len(k_30m) >= 2:
                        t_prev = k_30m[-2]["open_time"]
                        if t_prev in btc_map and btc_map[t_prev] > 0 and closes[-2] > 0:
                            btc_drop_1bar = (btc_map[t_curr] - btc_map[t_prev]) / btc_map[t_prev]
                            alt_drop_1bar = (closes[-1] - closes[-2]) / closes[-2]
                            if btc_drop_1bar <= -0.003 and alt_drop_1bar >= 0.0:
                                absorption_btc = True

            if not is_custom and comp_rs < cfg["min_composite_rs"]:
                return None

            k_4h = self.net.get_klines(sym, interval="4h", limit=120)
            ema200_4h = 0.0
            if k_4h and len(k_4h) >= 60:
                c_4h = [k["close"] for k in k_4h]
                ema200_4h = TechnicalEngine.calc_ema(c_4h, min(200, len(c_4h)))[-1]

            # Gate 2: Tính toán ZLEMA & VWAP
            zlema8_series = TechnicalEngine.calc_zlema(closes, 8)
            zlema21_series = TechnicalEngine.calc_zlema(closes, 21)
            zlema8 = zlema8_series[-1] if zlema8_series else curr_p
            zlema21 = zlema21_series[-1] if zlema21_series else curr_p
            ribbon_gap = abs(zlema8 - zlema21) / zlema21 * 100.0 if zlema21 > 0 else 0.0

            session_vwap, vwap_u1, vwap_l1, vwap_u2, vwap_l2 = TechnicalEngine.calc_session_vwap_bands_vn(k_30m)
            cvd_div, net_cvd_val, cvd_desc_str = TechnicalEngine.audit_cvd_divergence(k_30m, lookback=16)

            poc = TechnicalEngine.calc_volume_profile_poc(k_30m, 35)
            ema20_series = TechnicalEngine.calc_ema(closes, 20)
            ema20 = ema20_series[-1] if ema20_series else curr_p
            ema50 = TechnicalEngine.calc_ema(closes, 50)[-1] if len(closes) >= 50 else ema20
            ema200 = TechnicalEngine.calc_ema(closes, 200)[-1] if len(closes) >= 200 else ema50

            rsi = TechnicalEngine.calc_rsi(closes, 14)
            macd_l, sig_l, hist, hist_delta, bull_cross = TechnicalEngine.calc_macd(closes)
            bb_mid, bb_upper, bb_lower, bb_bw = TechnicalEngine.calc_bollinger_bands(closes, 20)
            cvd_usdt = TechnicalEngine.calc_cvd_usdt(k_30m[-20:])

            s1, s2, r1, r2 = TechnicalEngine.calc_support_resistance(k_30m, curr_p)

            setup_mode, setup_data = PatternStrategyEngine.audit_setup(k_30m, poc=poc)
            if not setup_mode:
                if curr_p >= zlema21:
                    setup_mode = "PULLBACK"
                else:
                    setup_mode = "THEO_DÕI"
                setup_data = {"swing_h": max(highs[-50:]), "swing_l": min(lows[-50:])}

            k_15m = self.net.get_klines(sym, interval="15m", limit=30)
            k_5m = self.net.get_klines(sym, interval="5m", limit=30)
            subwave_info = PatternStrategyEngine.audit_subwaves_15m_5m(k_15m, k_5m, setup_mode)

            ote = InstitutionalRiskManager.calculate_trade_levels(k_30m, setup_mode, setup_data, poc=poc)
            if not ote:
                return None

            # Gate 3: Chấm điểm
            score = 30
            if curr_p >= poc: score += 10
            if cvd_usdt > 0: score += 8
            if cvd_div: score += 12
            if absorption_btc: score += 10
            if comp_rs >= 0: score += 10

            if curr_p >= zlema21: score += 12
            if zlema8 >= zlema21: score += 8
            if curr_p >= session_vwap: score += 8
            elif curr_p >= vwap_l1: score += 4

            score += subwave_info.get("score_bonus", 0)

            if setup_mode == "WAVE_3" and vol_ratio >= max(1.0, cfg["trigger_vol_ratio_5m"] - 0.2): score += 10
            elif setup_mode == "WAVE_2" and vol_ratio < cfg["pullback_dry_vol_ratio"] + 0.08: score += 10
            elif setup_mode == "BREAKOUT" and bb_bw < cfg["bb_bandwidth_max"] + 1.0: score += 10

            if rsi > cfg["rsi_overbought_threshold"]: score -= 20
            if self.btc_status.get("regime") == "Red": score -= cfg["penalty_btc_red"]
            elif self.btc_status.get("regime") == "Yellow": score -= cfg["penalty_btc_yellow"]
            if not self.btc_status.get("micro_trend_15m", True): score -= cfg["penalty_btc_15m"]
            if veto_triggered: score -= 25

            score = max(10, min(100, score))
            if not is_custom and score < cfg["min_score_threshold"]:
                return None

            rank_label = "A+" if score >= 85 else ("A" if score >= 72 else ("B" if score >= 60 else "C"))

            mode_desc = {
                "WAVE_2": f"Sóng 2 cạn vol ({vol_ratio:.2f}x SMA20) về Fib OTE. SL đệm {ote['risk_pct']}%.",
                "WAVE_3": f"Sóng 3 bùng nổ xung lực. Đặt LIMIT Retest đỉnh h1={format_price(ote['entry'])}. SL={format_price(ote['sl'])} (-{ote['risk_pct']}%).",
                "BREAKOUT": f"Dải Bollinger & ZLEMA Ribbon nén chặt ({bb_bw:.2f}%) bứt phá với dòng tiền CVD dương.",
                "PULLBACK": f"Thoái lui lành mạnh về vùng hội tụ ZLEMA21 & POC thanh khoản. RSI {rsi:.1f} hạ nhiệt.",
                "SWEEP": "Quét râu rũ bỏ thanh khoản dưới đáy ngắn hạn và rút chân trở lại nền range.",
                "THEO_DÕI": f"Vùng tích lũy giằng co quanh ZLEMA. RSI {rsi:.1f}, Vol M30 {vol_ratio:.2f}x SMA20."
            }.get(setup_mode, "Hội tụ kỹ thuật tối ưu.")

            if absorption_btc:
                mode_desc = f"[HẤP THỤ MUA ĐỠ GIÁ KHI BTC ĐỎ]: {mode_desc}"
            if cvd_div:
                mode_desc = f"[PHÂN KỲ CVD ĐÁY SMART MONEY]: {mode_desc}"

            prev_ema4 = ema20_series[-4] if len(ema20_series) >= 4 else 0.0
            ema_slope_val = ((ema20 - prev_ema4) / prev_ema4 * 100.0) if prev_ema4 > 0 else 0.0

            meta = {
                "ema20": ema20, "ema50": ema50, "ema200": ema200, "ema200_4h": ema200_4h,
                "zlema8": zlema8, "zlema21": zlema21, "ribbon_gap": ribbon_gap,
                "ema_slope": ema_slope_val, "rsi": rsi, "macd_l": macd_l, "sig_l": sig_l,
                "hist": hist, "hist_delta": hist_delta, "bb_mid": bb_mid, "bb_upper": bb_upper,
                "bb_lower": bb_lower, "bb_bw": bb_bw, "session_vwap": session_vwap,
                "vwap_upper1": vwap_u1, "vwap_lower1": vwap_l1, "poc": poc,
                "support_1": s1, "support_2": s2, "resistance_1": r1, "resistance_2": r2,
                "cvd_usdt": cvd_usdt, "cvd_divergence": cvd_div, "cvd_desc": cvd_desc_str,
                "absorption_btc": absorption_btc, "vol_ratio": vol_ratio, "atr": ote["atr"],
                "veto_triggered": veto_triggered, "veto_reason": veto_reason,
                "subwave_info": subwave_info
            }

            return {
                "symbol": sym,
                "price": curr_p,
                "quote_vol": quote_vol,
                "score": score,
                "rank_label": rank_label,
                "setup_mode": setup_mode,
                "comp_rs": comp_rs,
                "position_summary": mode_desc,
                "ote": ote,
                "meta": meta
            }
        except Exception:
            return None



# ==============================================================================
# XI. HÀM BỔ TRỢ THU THẬP VĨ MÔ TỰ DO
# ==============================================================================
def safe_request(url, params=None, timeout=6):
    try:
        ctx = make_ssl_context()

        full_url = url + ("?" + urllib.parse.urlencode(params) if params else "")
        req = urllib.request.Request(
            full_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8")), True
    except Exception:
        pass
    return None, False


def fetch_binance_market_data():
    data, status = safe_request("https://api.binance.com/api/v3/ticker/24hr", params={"symbol": "BTCUSDT"})
    if status and isinstance(data, dict):
        price = float(data.get("lastPrice", 0.0))
        chg_24h = float(data.get("priceChangePercent", 0.0))
        vol_24h_usdt = float(data.get("quoteVolume", 0.0))
        return price, chg_24h, vol_24h_usdt, "ONLINE (Real-time Spot)"
    return 0.0, 0.0, 0.0, "OFFLINE"


def fetch_binance_dXY_proxy(net_mgr):
    try:
        t_eur = net_mgr.fetch_json("/api/v3/ticker/24hr", params={"symbol": "EURUSDT"})
        t_gbp = net_mgr.fetch_json("/api/v3/ticker/24hr", params={"symbol": "GBPUSDT"})

        if t_eur and t_gbp:
            p_eur = float(t_eur.get("lastPrice", 1.085))
            chg_eur = float(t_eur.get("priceChangePercent", 0.0))

            p_gbp = float(t_gbp.get("lastPrice", 1.285))
            chg_gbp = float(t_gbp.get("priceChangePercent", 0.0))

            if p_eur > 0 and p_gbp > 0:
                w_eur = 0.576 / (0.576 + 0.119)
                w_gbp = 0.119 / (0.576 + 0.119)

                dxy_proxy = 102.50 * ((1.085 / p_eur) ** w_eur) * ((1.285 / p_gbp) ** w_gbp)
                dxy_change = - ((w_eur * chg_eur) + (w_gbp * chg_gbp))
                return round(dxy_proxy, 2), round(dxy_change, 2), "ONLINE (Binance FX Proxy)"
    except Exception:
        pass
    return 102.50, 0.00, "OFFLINE / FALLBACK"


def fetch_us10y_treasury_yield():
    try:
        ctx = make_ssl_context()
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            if resp.status == 200:
                lines = resp.read().decode("utf-8").strip().splitlines()
                for line in reversed(lines):
                    parts = line.split(",")
                    if len(parts) >= 2 and parts[0] != "DATE":
                        val_str = parts[1].strip()
                        if val_str and val_str != ".":
                            try:
                                return float(val_str), parts[0].strip(), "ONLINE (Fed St. Louis Live)"
                            except ValueError:
                                continue
    except Exception:
        pass
    return 4.25, "N/A", "OFFLINE / CACHED"


def fetch_binance_derivatives():
    fr_data, fr_status = safe_request("https://fapi.binance.com/fapi/v1/premiumIndex", params={"symbol": "BTCUSDT"})
    funding_rate = float(fr_data["lastFundingRate"]) * 100 if fr_status and fr_data and "lastFundingRate" in fr_data else 0.0

    oi_data, oi_status = safe_request("https://fapi.binance.com/fapi/v1/openInterest", params={"symbol": "BTCUSDT"})
    open_interest_btc = float(oi_data["openInterest"]) if oi_status and oi_data and "openInterest" in oi_data else 0.0

    api_status = "ONLINE (Live)" if (fr_status and oi_status) else "DEGRADED"
    return funding_rate, open_interest_btc, api_status


def fetch_global_market_metrics():
    global_data, g_status = safe_request("https://api.coingecko.com/api/v3/global")
    btc_dominance, total_mcap = 0.0, 0.0
    if g_status and global_data and "data" in global_data:
        btc_dominance = float(global_data["data"].get("market_cap_percentage", {}).get("btc", 0.0))
        total_mcap = float(global_data["data"].get("total_market_cap", {}).get("usd", 0.0))
        return btc_dominance, total_mcap, "ONLINE (Live)"
    return 0.0, 0.0, "OFFLINE / RATE LIMITED"


def fetch_fear_and_greed_index():
    data, status = safe_request("https://api.alternative.me/fng/?limit=1")
    if status and data and "data" in data and len(data["data"]) > 0:
        fng_val = int(data["data"][0].get("value", 50))
        fng_text = data["data"][0].get("value_classification", "Neutral")
        return fng_val, fng_text, "ONLINE (Live)"
    return 50, "Neutral", "OFFLINE"


def fetch_detailed_bulletins(funding_rate, open_interest_btc, oi_usd, btc_dom, fng_val, fng_text, dxy, dxy_chg, us10y):
    bulletins = []
    
    if dxy_chg > 0.35:
        bulletins.append(f"VĨ MÔ (DXY): Chỉ số USD tăng mạnh ({dxy:.2f}, {dxy_chg:+.2f}%). Đồng USD tăng giá đang hút thanh khoản khỏi thị trường tài sản rủi ro, tạo áp lực cản trở đà tăng của BTC và Altcoin.")
    elif dxy_chg < -0.35:
        bulletins.append(f"VĨ MÔ (DXY): Chỉ số USD suy yếu ({dxy:.2f}, {dxy_chg:+.2f}%). Môi trường tiền tệ nới lỏng tạo điều kiện thuận lợi cho dòng tiền đầu cơ kích hoạt làn sóng Risk-On vào Crypto.")
    else:
        bulletins.append(f"VĨ MÔ (DXY): Chỉ số USD đi ngang ổn định quanh mốc {dxy:.2f} ({dxy_chg:+.2f}%), thị trường crypto vận động theo cung cầu nội tại.")

    if us10y >= 4.50:
        bulletins.append(f"LỢI SUẤT (US10Y): Lợi suất TPCP Mỹ 10 năm ở mức cao ({us10y:.2f}%). Lợi suất phi rủi ro hấp dẫn làm tăng chi phí cơ hội nắm giữ Crypto, gây bất lợi cho dòng vốn dài hạn của các tổ chức.")
    elif us10y <= 3.80:
        bulletins.append(f"LỢI SUẤT (US10Y): Lợi suất 10 năm hạ nhiệt ({us10y:.2f}%). Chi phí vốn rẻ thúc đẩy dòng vốn tìm kiếm lợi nhuận cao quay trở lại thị trường tiền mã hóa.")
    else:
        bulletins.append(f"LỢI SUẤT (US10Y): Lợi suất 10 năm dao động ở ngưỡng cân bằng ({us10y:.2f}%), áp lực từ thị trường trái phiếu lên định giá Crypto tạm thời lắng dịu.")

    bulletins.append(f"TÂM LÝ (Alternative.me): Chỉ số Fear & Greed đạt {fng_val}/100 ({fng_text}). Thị trường đang phản ánh tâm lý đầu cơ ngắn hạn.")
    if btc_dom > 0:
        bulletins.append(f"DÒNG TIỀN (Global Dominance): Thị phần vốn hóa Bitcoin (BTC.D) đạt {btc_dom:.2f}%. Dòng tiền đang {'tập trung bảo toàn giá trị ở BTC' if btc_dom > 55 else 'lan tỏa dần sang các cụm Altcoin'}.")

    if funding_rate > 0.01:
        bulletins.append(f"PHÁI SINH (Funding Rate): Dương rất cao ({funding_rate:.4f}%/8h). Phe Long trả phí lớn để giữ vị thế, rủi ro Long Squeeze diện rộng nếu giá xuất hiện nhịp chỉnh bất ngờ.")
    elif funding_rate < -0.005:
        bulletins.append(f"PHÁI SINH (Funding Rate): Âm ({funding_rate:.4f}%/8h). Phe Short đang áp đảo, tiềm năng kích hoạt Short Squeeze nếu xuất hiện lực mua kích thích.")
    else:
        bulletins.append(f"PHÁI SINH (Funding Rate): Cân bằng ({funding_rate:.4f}%/8h), đòn bẩy duy trì trạng thái trung tính, ít rủi ro bão hòa vị thế.")

    return bulletins
