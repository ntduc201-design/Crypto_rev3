#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CRYPTO INSTITUTIONAL MASTER PRO - BẢN KIVY (ANDROID APK)
Giao diện 7 tab chạm cảm ứng. Toàn bộ logic nằm trong core.py (Engine).
================================================================================
"""
import os
import threading
from datetime import datetime

# Thư mục dữ liệu phải được đặt TRƯỚC khi import core (core đọc biến môi trường lúc import)
_private = os.environ.get("ANDROID_PRIVATE")
os.environ.setdefault("CRYPTO_DATA_DIR", _private or os.path.dirname(os.path.abspath(__file__)))

from kivy.config import Config  # noqa: E402
Config.set("graphics", "width", "420")      # chỉ có tác dụng khi chạy thử trên máy tính
Config.set("graphics", "height", "820")
Config.set("input", "mouse", "mouse,multitouch_on_demand")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.clipboard import Clipboard  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.graphics import Color, Rectangle  # noqa: E402
from kivy.metrics import dp, sp  # noqa: E402
from kivy.uix.behaviors import ButtonBehavior  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.checkbox import CheckBox  # noqa: E402
from kivy.uix.gridlayout import GridLayout  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.uix.popup import Popup  # noqa: E402
from kivy.uix.scrollview import ScrollView  # noqa: E402
from kivy.uix.spinner import Spinner  # noqa: E402
from kivy.uix.textinput import TextInput  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402
from kivy.utils import get_color_from_hex  # noqa: E402

import core  # noqa: E402
from core import FILTER_CFG, FilterConfig, format_price, TZ_VN, STABLECOINS  # noqa: E402

# ==============================================================================
# BẢNG MÀU, CỠ CHỮ, TIỆN ÍCH GIAO DIỆN
# ==============================================================================
C = {k: get_color_from_hex(v) for k, v in core.COLOR_PALETTE.items()}
WHITE = (1, 1, 1, 1)
BLACK = (0, 0, 0, 1)
FS = {"xs": sp(11), "s": sp(12), "m": sp(13), "l": sp(15)}


def ui(s):
    """Thay các ký tự mà phông mặc định của Kivy (Roboto) không có, tránh ô vuông lỗi trên Android."""
    return str(s).replace("➔", "→").replace("━", "-").replace("├", "|").replace("└", "|")


class Card(GridLayout):
    """Khung dọc tự co giãn chiều cao theo nội dung, có màu nền."""
    def __init__(self, bg=None, pad=dp(8), spacing=dp(2), **kw):
        super().__init__(cols=1, size_hint_y=None, padding=pad, spacing=spacing, **kw)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            self._bg_color = Color(*(bg or C["card_bg"]))
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

    def _upd_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size


class TapCard(ButtonBehavior, Card):
    pass


def new_grid():
    g = GridLayout(cols=1, size_hint_y=None, spacing=dp(4), padding=[dp(4), dp(2)])
    g.bind(minimum_height=g.setter("height"))
    return g


class WLabel(Label):
    """Nhãn tự xuống dòng theo chiều rộng khung chứa (tên dài hiển thị hết chiều ngang)."""
    def __init__(self, text="", color=None, fs=None, bold=False, halign="left", **kw):
        super().__init__(text=ui(text), color=color or C["text_main"], font_size=fs or FS["s"],
                         bold=bold, halign=halign, valign="top", size_hint_y=None, markup=False, **kw)
        self.bind(width=self._on_w, texture_size=self._on_ts)
        self.text_size = (self.width, None)

    def _on_w(self, *_):
        self.text_size = (self.width, None)

    def _on_ts(self, *_):
        self.height = self.texture_size[1] + dp(3)


def line(parent, text, color=None, fs=None, bold=False, halign="left"):
    lbl = WLabel(text=text, color=color, fs=fs, bold=bold, halign=halign)
    parent.add_widget(lbl)
    return lbl


def hrow(h=dp(32), spacing=dp(4)):
    return BoxLayout(orientation="horizontal", size_hint_y=None, height=h, spacing=spacing)


def kv_row(left, lcol, right="", rcol=None, fs=None, h=dp(22)):
    r = hrow(h)
    pairs = [(left, lcol, "left")]
    if right:
        pairs.append((right, rcol or lcol, "right"))
    for txt, c, ha in pairs:
        lb = Label(text=ui(txt), color=c, font_size=fs or FS["xs"], halign=ha, valign="middle",
                   shorten=True, shorten_from="right")
        lb.bind(size=lambda i, v: setattr(i, "text_size", v))
        r.add_widget(lb)
    return r


def tag(text, color, fs=None, bold=True):
    lb = Label(text=ui(text), color=color, font_size=fs or FS["s"], bold=bold, size_hint_x=None)
    lb.bind(texture_size=lambda i, v: setattr(i, "width", v[0] + dp(6)))
    return lb


def make_btn(text, bg, fg=WHITE, h=dp(40), fs=None, **kw):
    b = Button(text=ui(text), background_normal="", background_down="", background_disabled_normal="",
               background_color=bg, color=fg, font_size=fs or FS["s"], bold=True,
               size_hint_y=None, height=h, halign="center", valign="middle", **kw)
    b.bind(size=lambda i, v: setattr(i, "text_size", (v[0] - dp(6), None)))
    b.bind(state=lambda i, s: setattr(i, "opacity", 0.6 if s == "down" else 1.0))
    return b


def make_input(text="", hint="", h=dp(40), inrow=False, **kw):
    ti = TextInput(text=text, hint_text=hint, multiline=False, font_size=FS["m"],
                   background_normal="", background_active="", background_color=C["card_sub"],
                   foreground_color=WHITE, cursor_color=C["gold"], hint_text_color=C["text_muted"],
                   padding=[dp(8), dp(9), dp(8), dp(9)], write_tab=False,
                   size_hint_y=(1 if inrow else None), **kw)
    if not inrow:
        ti.height = h
    return ti


def num_filter(substring, from_undo):
    """Chỉ cho nhập số, dấu chấm và dấu trừ (bộ lọc 'float' mặc định của Kivy không cho số âm)."""
    return "".join(ch for ch in substring.replace(",", ".") if ch in "0123456789.-")


def side_label(text, **kw):
    lb = Label(text=ui(text), color=C["text_muted"], font_size=FS["s"], bold=True, halign="left", valign="middle", **kw)
    lb.bind(size=lambda i, v: setattr(i, "text_size", v))
    return lb


def make_spinner(text, values, **kw):
    return Spinner(text=text, values=values, background_normal="", background_color=C["card_sub"],
                   color=WHITE, font_size=FS["s"], **kw)


def empty_msg(parent, text):
    lb = Label(text=ui(text), color=C["text_muted"], font_size=FS["m"], halign="center", valign="middle",
               size_hint_y=None, height=dp(140))
    lb.bind(size=lambda i, v: setattr(i, "text_size", (v[0] - dp(16), None)))
    parent.add_widget(lb)


def delete_btn(cb):
    b = make_btn("XÓA", C["card_sub"], fg=C["bear_red"], h=dp(28), fs=FS["xs"], size_hint_x=None, width=dp(52))
    b.bind(on_release=lambda *_: cb())
    return b


# ==============================================================================
# LỚP CƠ SỞ CHO MỖI TAB
# ==============================================================================
class TabBase(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", **kw)
        self.app = app
        self.engine = app.engine
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        self.body = new_grid()
        self.scroll.add_widget(self.body)

    def on_show(self):
        pass


# ==============================================================================
# TAB 1: TÍN HIỆU
# ==============================================================================
SM_NAMES = {
    "WAVE_2": "[SÓNG 2 ELLIOTT]", "WAVE_3": "[SÓNG 3 RETEST]", "BREAKOUT": "[BỨT PHÁ DẢI NÉN]",
    "PULLBACK": "[THOÁI LUI OTE]", "SWEEP": "[QUÉT TK]", "THEO_DÕI": "[THEO DÕI NỀN]",
}
SM_COLORS = {
    "WAVE_2": C["purple"], "WAVE_3": C["orange"], "BREAKOUT": C["gold"],
    "PULLBACK": C["accent_blue"], "SWEEP": C["bull_green"], "THEO_DÕI": C["text_muted"],
}


class TabSignals(TabBase):
    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.add_widget(WLabel(text="TÍN HIỆU SPOT (CHẠM VÀO THẺ ĐỂ CHỌN)", color=C["text_muted"], fs=FS["s"], bold=True,
                               padding=[dp(6), dp(3)]))
        self.add_widget(self.scroll)

    def on_show(self):
        self.render()

    def render(self):
        self.body.clear_widgets()
        results = self.engine.scanned_results
        if not results:
            empty_msg(self.body, "Chưa có tín hiệu nào vượt qua Bộ Lọc Cổng (Gate Filters).\nNhấn 'QUÉT TOÀN BỘ' để kích hoạt.")
            return
        rsi_thr = FILTER_CFG.get("rsi_overbought_threshold")
        for item in results:
            self.body.add_widget(self._make_card(item, rsi_thr))

    def _make_card(self, item, rsi_thr):
        card = TapCard(bg=C["card_bg"])
        score = item["score"]
        rsi_val = item["meta"]["rsi"]
        sm = item["setup_mode"]

        r1 = hrow(dp(26))
        r1.add_widget(tag(item["symbol"], C["text_main"], FS["l"]))
        r1.add_widget(tag(SM_NAMES.get(sm, f"[{sm}]"), SM_COLORS.get(sm, C["text_main"]), FS["s"]))
        r1.add_widget(Widget())
        card.add_widget(r1)

        if rsi_val > rsi_thr:
            badge_bg, badge_fg = C["gold"], BLACK
            badge_txt = f"FOMO QUÁ MUA (RSI > {rsi_thr:g})"
        else:
            badge_bg = C["bull_green"] if score >= 80 else C["accent_cyan"]
            badge_fg = WHITE
            badge_txt = f"Điểm: {score}/100  |  Xếp hạng: [{item['rank_label']}]"
        badge = Card(bg=badge_bg, pad=[dp(6), dp(2)])
        line(badge, badge_txt, color=badge_fg, fs=FS["s"], bold=True)
        card.add_widget(badge)

        card.add_widget(kv_row(f"Giá: {format_price(item['price'])} USDT", C["gold"],
                               f"RS vs BTC: {item['comp_rs']:+.2f}%", C["accent_cyan"], fs=FS["s"], h=dp(24)))
        ote = item["ote"]
        card.add_widget(kv_row(f"Entry: {format_price(ote['entry'])}", C["dark_gold"],
                               f"TP1: {format_price(ote['tp1'])} (+{ote['tp1_pct']}%)", C["bull_green"]))
        card.add_widget(kv_row(f"SL: {format_price(ote['sl'])} (-{ote['risk_pct']}%)", C["bear_red"]))

        desc = Card(bg=C["card_sub"], pad=dp(4))
        line(desc, f"• Đánh giá: {item['position_summary']}", color=C["text_muted"], fs=FS["xs"])
        card.add_widget(desc)

        card.bind(on_release=lambda inst, it=item: self._select(it))
        return card

    def _select(self, item):
        self.engine.selected_coin = item
        self.app.tab_diag.set_symbol(item["symbol"])
        self.engine.add_log(f"Đã chọn mã {item['symbol']} ({item['setup_mode']}) để chẩn đoán.")
        self.app.switch_tab(1)


# ==============================================================================
# TAB 2: CHẨN ĐOÁN
# ==============================================================================
class TabDiagnostics(TabBase):
    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        top = Card(bg=C["card_bg"], pad=dp(6))
        row = hrow(dp(44))
        row.add_widget(tag("MÃ COIN:", C["gold"], FS["s"]))
        self.ent = make_input("BTCUSDT", inrow=True)
        self.ent.bind(on_text_validate=lambda *_: self.on_scan_clicked())
        row.add_widget(self.ent)
        self.btn_scan = make_btn("QUÉT", C["accent_blue"], size_hint_x=None, width=dp(84))
        self.btn_scan.bind(on_release=lambda *_: self.on_scan_clicked())
        row.add_widget(self.btn_scan)
        top.add_widget(row)
        self.add_widget(top)
        self.add_widget(self.scroll)

    def on_show(self):
        self.render()

    def set_symbol(self, sym):
        self.ent.text = sym

    def on_scan_clicked(self):
        raw = self.ent.text.strip().upper()
        if not raw:
            self.app.show_popup("Cảnh báo", "Vui lòng nhập mã coin (Ví dụ: BTC hoặc BTCUSDT).", "warning")
            return
        sym = raw if raw.endswith("USDT") else f"{raw}USDT"
        base = sym[:-4]
        if base in STABLECOINS or base.startswith("USD") or base.endswith("USD") or base in {"U", "USD"}:
            self.app.show_popup("Cảnh báo", f"{sym} thuộc danh mục Stablecoin/neo giá USD, không hỗ trợ phân tích.", "warning")
            return
        self.btn_scan.text = "ĐANG QUÉT..."
        self.btn_scan.disabled = True
        self.engine.custom_scan(sym)

    def on_custom_done(self, symbol="", ok=False, **_):
        self.btn_scan.text = "QUÉT"
        self.btn_scan.disabled = False
        if ok:
            self.render()
            self.app.tab_signals.render()
        else:
            self.app.show_popup("Lỗi", f"Không thể lấy dữ liệu phân tích cho {symbol}.", "error")

    def _block(self, title, color):
        card = Card(bg=C["card_bg"])
        line(card, title, color=color, fs=FS["m"], bold=True)
        self.body.add_widget(card)
        return card

    def render(self):
        self.body.clear_widgets()
        c = self.engine.selected_coin
        if not c:
            empty_msg(self.body, "Vui lòng chọn 1 mã coin từ Tab '1. Tín Hiệu'\nhoặc nhập mã coin ở khung trên rồi nhấn 'QUÉT'.")
            return
        m = c["meta"]
        m15 = m.get("subwave_info", {}).get("m15", {})
        m5 = m.get("subwave_info", {}).get("m5", {})
        price = c["price"]
        rsi_thr = FILTER_CFG.get("rsi_overbought_threshold")

        head = Card(bg=C["card_bg"])
        self.body.add_widget(head)
        line(head, f"{c['symbol']} - BÁO CÁO KỸ THUẬT & ORDERFLOW", color=C["gold"], fs=FS["l"], bold=True)
        rec_text, rec_color = self.engine.get_position_recommendation(c)
        line(head, f"• Đề xuất vị thế: {rec_text}", color=rec_color, fs=FS["s"], bold=True)
        line(head, f"• Thị giá thị trường: {format_price(price)} USDT", color=C["text_main"])
        s1 = m.get("support_1", price * 0.98)
        s2 = m.get("support_2", price * 0.95)
        r1 = m.get("resistance_1", price * 1.02)
        r2 = m.get("resistance_2", price * 1.05)
        pct = lambda a, b: ((a - b) / price * 100.0) if price > 0 else 0.0  # noqa: E731
        line(head, f"• Hỗ trợ: S1={format_price(s1)} (-{pct(price, s1):.2f}%) | S2={format_price(s2)} (-{pct(price, s2):.2f}%)",
             color=C["bull_green"], bold=True)
        line(head, f"• Kháng cự: R1={format_price(r1)} (+{pct(r1, price):.2f}%) | R2={format_price(r2)} (+{pct(r2, price):.2f}%)",
             color=C["bear_red"], bold=True)
        score_col = C["bull_green"] if c["score"] >= 80 else (C["accent_cyan"] if c["score"] >= 65 else C["gold"])
        sb = Card(bg=score_col, pad=[dp(6), dp(2)])
        line(sb, f"Thang điểm hợp lưu: {c['score']}/100  |  Phân loại: [{c['rank_label']}]", color=WHITE, bold=True)
        head.add_widget(sb)

        # 1. EMA & ZLEMA Ribbon
        c1 = self._block("1. HỆ THỐNG XU HƯỚNG EMA & ZLEMA RIBBON [M30 & 4H]", C["accent_blue"])
        z8, z21, gap = m.get("zlema8", 0.0), m.get("zlema21", 0.0), m.get("ribbon_gap", 0.0)
        line(c1, f"• ZLEMA Ribbon: ZLEMA8={format_price(z8)} | ZLEMA21={format_price(z21)} (Độ nén: {gap:.2f}%)", fs=FS["xs"])
        line(c1, f"• Khung M30: EMA20={format_price(m['ema20'])} | EMA50={format_price(m['ema50'])} | EMA200={format_price(m['ema200'])}", fs=FS["xs"])
        line(c1, f"• Khung 4H Vĩ mô: EMA200 4H={format_price(m.get('ema200_4h', 0.0))}", fs=FS["xs"])
        if z8 > z21 and price >= z8:
            rd, rc = "ZLEMA Ribbon bung rộng góc dốc hướng lên (Xung lực tăng cường kích)", C["bull_green"]
        elif gap < FILTER_CFG.get("zlema_ribbon_gap_max"):
            rd, rc = f"ZLEMA Ribbon siêu nén chặt ({gap:.2f}%) - Chuẩn bị bùng nổ xung lực mới", C["gold"]
        else:
            rd, rc = "ZLEMA Ribbon phân kỳ giảm / Đang thoái lui kiểm định", C["bear_red"]
        line(c1, f"• Trạng thái Ribbon: {rd}", color=rc, fs=FS["xs"], bold=True)

        # 2. MACD & RSI
        c2 = self._block("2. ĐỘNG LƯỢNG MACD HISTOGRAM & RSI [Khung M30]", C["accent_cyan"])
        rsi_val = m["rsi"]
        if rsi_val > rsi_thr:
            txt, col = "FOMO QUÁ MUA CỰC ĐỘ - RỦI RO XẢ MẠNH (Hưng phấn quá đà)", C["bear_red"]
        elif rsi_val > 70.0:
            txt, col = "QUÁ MUA NGẮN HẠN (Lực mua mạnh, cần kéo chặt SL)", C["gold"]
        elif rsi_val >= 50.0:
            txt, col = "XUNG LỰC MUA ÁP ĐẢO (Đà tăng mở rộng, phe mua làm chủ)", C["bull_green"]
        elif rsi_val >= 38.0:
            txt, col = "HẠ NHIỆT OTE LÀNH MẠNH (Cân bằng, chuẩn bị chân sóng)", C["accent_cyan"]
        else:
            txt, col = "QUÁ BÁN CẠN CUNG (Lực xả kiệt quệ, dễ bật hồi kỹ thuật)", C["purple"]
        line(c2, f"• RSI M30 (14 nến): {rsi_val:.1f}", color=col, fs=FS["s"], bold=True)
        line(c2, f"  ➔ Đánh giá RSI: {txt}", color=col, fs=FS["xs"], bold=True)
        line(c2, f"• MACD M30: Hist={m['hist']:+.6f} | Delta Hist={m['hist_delta']:+.6f}", fs=FS["xs"])

        # 3. Bollinger & VWAP
        c3 = self._block("3. BIÊN ĐỘ BOLLINGER & VWAP SD BANDS [Phiên GMT+7]", C["purple"])
        vwap_m, vwap_l1 = m.get("session_vwap", 0.0), m.get("vwap_lower1", 0.0)
        line(c3, f"• Session VWAP Phiên: {format_price(vwap_m)} | Vùng OTE (-1SD): {format_price(vwap_l1)}", fs=FS["xs"])
        line(c3, f"• Dải Bollinger M30: Giữa={format_price(m['bb_mid'])} | Độ nén Band: {m['bb_bw']:.2f}%", fs=FS["xs"])
        if price >= vwap_m:
            ct, cc = "Giá TRÊN VWAP phiên - Phe mua làm chủ hoàn toàn", C["bull_green"]
        elif price >= vwap_l1:
            ct, cc = "Vùng kiểm định hấp thụ lành mạnh (Giữa VWAP và -1 SD)", C["accent_cyan"]
        else:
            ct, cc = "Giá DƯỚI dải -1 SD - Áp lực bán mở rộng", C["bear_red"]
        line(c3, f"  ➔ Kiểm soát VWAP: {ct}", color=cc, fs=FS["xs"], bold=True)

        # 4. Orderflow & CVD
        c4 = self._block("4. DÒNG TIỀN ORDERFLOW & PHÂN KỲ CVD [MTF 6H/24H]", C["bull_green"])
        line(c4, f"• POC (120 nến M30 = 60h): {format_price(m['poc'])}", fs=FS["xs"])
        line(c4, f"• Delta CVD (Tích lũy 20 nến): ${m['cvd_usdt']:+,.0f}", fs=FS["xs"])
        line(c4, f"• Kháng giảm khi BTC đỏ: {'XÁC NHẬN HẤP THỤ ĐỠ GIÁ' if m.get('absorption_btc', False) else 'Đồng pha biến động'}", fs=FS["xs"])
        line(c4, f"• Sức mạnh tương đối Composite RS: {c['comp_rs']:+.2f}% (vs BTC)", fs=FS["xs"])
        cvd_div = m.get("cvd_divergence", False)
        cvd_col = C["gold"] if cvd_div else (C["bull_green"] if m["cvd_usdt"] > 0 else C["bear_red"])
        line(c4, f"  ➔ Tín hiệu CVD: {m.get('cvd_desc', '')}", color=cvd_col, fs=FS["xs"], bold=True)

        # 5. Sóng con 15m
        c5 = self._block("5. VI CẤU TRÚC SÓNG CON [Khung 15m Chi Tiết]", C["accent_cyan"])
        if m15:
            p15, z15 = m15.get("price", 0.0), m15.get("zlema20", 0.0)
            line(c5, f"• Thị giá nến 15m: {format_price(p15)} USDT", fs=FS["xs"])
            line(c5, f"  ➔ Vị thế ZLEMA/EMA: {m15.get('pos_ema', '')}", color=C["bull_green"] if p15 >= z15 else C["gold"], fs=FS["xs"], bold=True)
            line(c5, f"• RSI (14) 15m: {m15.get('rsi', 50.0):.1f}", fs=FS["xs"])
            line(c5, f"  ➔ Đánh giá RSI 15m: {m15.get('rsi_eval', '')}", color=C["accent_cyan"], fs=FS["xs"], bold=True)
            line(c5, f"  ➔ Đánh giá MACD 15m: {m15.get('macd_eval', '')}",
                 color=C["bull_green"] if m15.get("hist", 0.0) > 0 else C["bear_red"], fs=FS["xs"], bold=True)
        else:
            line(c5, "• Đang cập nhật nến vi cấu trúc 15m...", color=C["text_muted"], fs=FS["xs"])

        # 6. Kích hoạt 5m
        c6 = self._block("6. ĐIỂM KÍCH HOẠT NHANH MICRO-TRIGGER [Khung 5m Chi Tiết]", C["orange"])
        if m5:
            sub = m.get("subwave_info", {})
            p5, z5 = m5.get("price", 0.0), m5.get("zlema20", 0.0)
            ok = sub.get("confirmed", False)
            tcol = C["bull_green"] if ok else C["gold"]
            line(c6, f"• Thị giá nến 5m: {format_price(p5)} USDT", fs=FS["xs"])
            line(c6, f"  ➔ Vị thế ZLEMA/EMA 5m: {m5.get('pos_ema', '')}", color=C["bull_green"] if p5 >= z5 else C["gold"], fs=FS["xs"], bold=True)
            line(c6, f"  ➔ Trạng thái nến 5m: {m5.get('candle_desc', '')}", fs=FS["xs"], bold=True)
            line(c6, f"  ➔ Đánh giá Trigger: {'ĐỒNG THUẬN KÍCH HOẠT SỚM' if ok else 'ĐANG THEO DÕI NỀN'}", color=tcol, fs=FS["xs"], bold=True)
            line(c6, f"  ➔ Kết luận vi sóng: {sub.get('desc', '')}", color=tcol, fs=FS["xs"], bold=True)
        else:
            line(c6, "• Đang cập nhật nến kích hoạt nhanh 5m...", color=C["text_muted"], fs=FS["xs"])

        go = make_btn(f"THIẾT LẬP KẾ HOẠCH LỆNH SPOT & QUẢN TRỊ NAV ({c['symbol']}) ➔", C["accent_blue"], h=dp(52))
        go.bind(on_release=lambda *_: self.app.switch_tab(2))
        self.body.add_widget(go)
        self.scroll.scroll_y = 1


# ==============================================================================
# TAB 3: LỆNH & NAV
# ==============================================================================
class TabNavOrder(TabBase):
    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.add_widget(self.scroll)
        self.last_qty = 0.0
        self.nav_text = "10000"
        self.risk_text = "1.0%"
        self.loss_text = "0"
        self._for_symbol = None

    def on_show(self):
        self.render()

    def _ote_text(self, sl, r_pct, tp1, tp1p, tp2, tp2p, tp3, tp3p):
        return (f"• Stop-Loss (Đệm 1.5x ATR): {format_price(sl)} USDT (-{r_pct:.2f}%)\n"
                f"• TP1 (Khóa 50% & BE): {format_price(tp1)} USDT (+{tp1p:.2f}%)\n"
                f"• TP2 (Mục tiêu 1.8R): {format_price(tp2)} USDT (+{tp2p:.2f}%)\n"
                f"• TP3 (Mở rộng 2.8R): {format_price(tp3)} USDT (+{tp3p:.2f}%)")

    def render(self):
        self.body.clear_widgets()
        c = self.engine.selected_coin
        if not c:
            empty_msg(self.body, "Vui lòng chọn 1 mã coin từ Tab '1. Tín Hiệu'\nhoặc phân tích một mã từ Tab '2. Chẩn Đoán'.")
            return
        ote = c["ote"]

        card = Card(bg=C["card_bg"])
        self.body.add_widget(card)
        line(card, f"{c['symbol']} - KẾ HOẠCH GIÁ VÀO LỆNH OTE [{c['setup_mode']}]", color=C["gold"], fs=FS["m"], bold=True)
        line(card, f"• Thị giá hiện tại: {format_price(c['price'])} USDT", fs=FS["s"])
        self.lbl_target = line(card, f"• Entry mục tiêu: {format_price(ote['entry'])} USDT", color=C["dark_gold"], fs=FS["s"])
        self.lbl_levels = line(card, self._ote_text(ote["sl"], ote["risk_pct"], ote["tp1"], ote["tp1_pct"],
                                                    ote["tp2"], ote["tp2_pct"], ote["tp3"], ote["tp3_pct"]), fs=FS["s"])

        calc = Card(bg=C["card_bg"], spacing=dp(4))
        self.body.add_widget(calc)
        line(calc, "MÁY TÍNH VỊ THẾ SPOT TIỀN MẶT (KHÔNG MARGIN)", color=C["bull_green"], fs=FS["m"], bold=True)

        line(calc, "Tổng vốn Spot ($) [NAV]:", color=C["text_muted"], bold=True)
        self.ent_nav = make_input(self.nav_text, input_filter=num_filter)
        self.ent_nav.bind(text=lambda i, v: setattr(self, "nav_text", v))
        calc.add_widget(self.ent_nav)

        line(calc, "Giá Entry vào lệnh (USDT):", color=C["text_muted"], bold=True)
        self.ent_entry = make_input(format_price(ote["entry"]), input_filter=num_filter)
        self.ent_entry.foreground_color = C["dark_gold"]
        self.ent_entry.bind(text=lambda i, v: self._on_entry_changed(v))
        calc.add_widget(self.ent_entry)

        r_risk = hrow(dp(40))
        r_risk.add_widget(side_label("Rủi ro chấp nhận (% NAV):"))
        self.sp_risk = make_spinner(self.risk_text, ["0.5%", "1.0%", "1.5%", "2.0%"], size_hint_x=0.4)
        self.sp_risk.bind(text=lambda i, v: setattr(self, "risk_text", v))
        r_risk.add_widget(self.sp_risk)
        calc.add_widget(r_risk)

        r_loss = hrow(dp(40))
        r_loss.add_widget(side_label("Số lệnh thua liên tiếp:"))
        self.sp_loss = make_spinner(self.loss_text, ["0", "1", "2 (Dừng trade)"], size_hint_x=0.4)
        self.sp_loss.bind(text=lambda i, v: setattr(self, "loss_text", v))
        r_loss.add_widget(self.sp_loss)
        calc.add_widget(r_loss)

        b_calc = make_btn("TÍNH TOÁN QUY MÔ VỊ THẾ SPOT", C["accent_blue"])
        b_calc.bind(on_release=lambda *_: self._execute_sizing())
        calc.add_widget(b_calc)

        self.lbl_res = line(calc, "Nhấn 'TÍNH TOÁN QUY MÔ' để xem kết quả phân bổ vốn.", color=C["accent_cyan"], fs=FS["s"])

        b_rec = make_btn("+ GHI NHẬN VÀO GIÁM SÁT 12H (TAB 4)", C["bull_green"], h=dp(46))
        b_rec.bind(on_release=lambda *_: self._record())
        calc.add_widget(b_rec)
        self.scroll.scroll_y = 1

    def _on_entry_changed(self, val):
        try:
            e_val = float(val.replace(",", "").strip())
            if e_val <= 0:
                return
            c = self.engine.selected_coin
            atr_val = c["ote"].get("atr", e_val * 0.02)
            res = core.InstitutionalRiskManager.calculate_levels_from_custom_entry(e_val, atr_val)
            if res:
                self.lbl_target.text = ui(f"• Entry mục tiêu: {format_price(res['entry'])} USDT")
                self.lbl_levels.text = ui(self._ote_text(res["sl"], res["risk_pct"], res["tp1"], res["tp1_pct"],
                                                         res["tp2"], res["tp2_pct"], res["tp3"], res["tp3_pct"]))
        except Exception:
            pass

    def _execute_sizing(self):
        c = self.engine.selected_coin
        if not c:
            return
        try:
            nav = float(self.ent_nav.text.replace(",", "").strip())
            risk_pct = float(self.sp_risk.text.replace("%", "").strip())
            lt = self.sp_loss.text
            losses = 2 if "2" in lt else (1 if "1" in lt else 0)
            entry_val = float(self.ent_entry.text.replace(",", "").strip())
        except ValueError:
            self.app.show_popup("Lỗi", "Vui lòng nhập số vốn NAV và giá Entry hợp lệ.", "error")
            return
        if entry_val <= 0 or nav <= 0:
            self.app.show_popup("Lỗi", "NAV và giá Entry phải lớn hơn 0.", "error")
            return

        ote = c["ote"]
        atr_val = ote.get("atr", entry_val * 0.02)
        calc_res = core.InstitutionalRiskManager.calculate_levels_from_custom_entry(entry_val, atr_val)
        sl_target = calc_res["sl"] if calc_res else ote["sl"]
        if entry_val <= sl_target:
            self.app.show_popup("Lỗi", f"Giá Entry ({format_price(entry_val)}) phải lớn hơn SL ({format_price(sl_target)}).", "error")
            return
        res = core.InstitutionalRiskManager.calculate_position_size(nav, risk_pct, entry_val, sl_target, losses)
        if not res:
            self.app.show_popup("Lỗi", "Không thể tính toán do tham số Entry/SL vi phạm.", "error")
            return

        self.last_qty = res["coin_qty"]
        stop_warn = "\n[CẢNH BÁO KỶ LUẬT]: Đã chạm ngưỡng 2 lệnh thua liên tiếp! Hãy tạm dừng trade hôm nay." if res["stop_trading"] else ""
        cap_warn = (f"\n[KHÓA TRẦN VỊ THẾ]: SL quá gần ({res['sl_pct']:.2f}%), vị thế đã được giới hạn đúng 100% NAV tiền mặt "
                    f"(${res['position_usd']:,.2f}).") if res["is_capped"] else ""
        self.lbl_res.text = ui(
            f"=== BẢNG PHÂN BỔ VỐN SPOT THỰC TẾ ===\n"
            f"• Mã giao dịch: {c['symbol']}\n"
            f"• Thị giá thị trường: {format_price(c['price'])} USDT\n"
            f"• Giá Entry tính toán: {format_price(entry_val)} USDT\n"
            f"• Mức cắt lỗ (SL): {format_price(sl_target)} USDT (-{res['sl_pct']:.2f}%)\n"
            f"• Chốt lời TP1 (50%&BE): {format_price(calc_res['tp1'])} USDT (+{calc_res['tp1_pct']:.2f}%)\n"
            f"• Quy mô tiền mua Spot: ${res['position_usd']:,.2f} ({(res['position_usd'] / nav) * 100:.1f}% NAV)\n"
            f"• Số lượng coin cần đặt: {res['coin_qty']:,.4f} {c['symbol'].replace('USDT', '')}\n"
            f"• Số tiền chịu rủi ro: ${res['actual_risk_usd']:,.2f} ({res['actual_risk_pct']:.2f}% NAV)\n"
            f"• Tiền mặt còn lại: ${res['cash_left']:,.2f} ({(res['cash_left'] / nav) * 100:.1f}% NAV)\n"
            f"• Kỷ luật TP1: Khớp TP1 đóng 50% vị thế, dời SL về Hòa Vốn."
            f"{cap_warn}{stop_warn}")
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.1)

    def _record(self):
        c = self.engine.selected_coin
        if not c:
            self.app.show_popup("Cảnh báo", "Vui lòng chọn 1 coin từ Tab 1 hoặc Tab 2 trước.", "warning")
            return
        try:
            entry_custom = float(self.ent_entry.text.replace(",", "").strip())
        except Exception:
            entry_custom = None
        ok, msg = self.engine.perf_tracker.record_trade(
            c, entry_custom=entry_custom, coin_qty=self.last_qty,
            notify_cb=self.engine.dispatch_monitor_status_webhook)
        if ok:
            self.engine.add_log(f"Giám sát 12H: {msg}")
            self.app.show_popup("Thành công",
                                f"{msg}\nKhi coin khớp giá Entry, hệ thống sẽ TỰ ĐỘNG nạp coin này vào Tab '5. Quản Lý Tài Sản'.",
                                "success")
            self.app.tab_monitor.render()
        else:
            self.app.show_popup("Thông báo", msg, "warning")


# ==============================================================================
# TAB 4: GIÁM SÁT
# ==============================================================================
class TabMonitor(TabBase):
    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        e = self.engine
        self.add_widget(self.scroll)

        # ---- Khung cấu hình webhook (dựng 1 lần, không bị xóa khi làm mới danh sách)
        top = Card(bg=C["card_bg"], spacing=dp(4))
        self.body.add_widget(top)
        line(top, "CẤU HÌNH THÔNG BÁO ĐẨY (TELEGRAM / DISCORD)", color=C["gold"], fs=FS["s"], bold=True)
        self.ent_webhook = make_input(str(e.settings_get("webhook_url", "")),
                                      hint="https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>")
        self.ent_webhook.bind(text=lambda i, v: e.save_setting_key("webhook_url", v.strip()))
        top.add_widget(self.ent_webhook)

        r1 = hrow(dp(40))
        b_paste = make_btn("DÁN URL", C["accent_blue"])
        b_paste.bind(on_release=lambda *_: self._paste())
        r1.add_widget(b_paste)
        b_list = make_btn("GỬI DS GIÁM SÁT", C["accent_cyan"])
        b_list.bind(on_release=lambda *_: self._send_list())
        r1.add_widget(b_list)
        top.add_widget(r1)
        b_port = make_btn("GỬI BÁO CÁO TÀI SẢN", C["bull_green"])
        b_port.bind(on_release=lambda *_: self._send_portfolio())
        top.add_widget(b_port)

        self.btn_auto = make_btn("", C["card_sub"], h=dp(40))
        self.btn_auto.bind(on_release=lambda *_: self._toggle_auto())
        top.add_widget(self.btn_auto)
        self.lbl_auto = line(top, "", fs=FS["xs"])
        self._sync_auto()

        # ---- Khung điều khiển giám sát
        ctrl = Card(bg=C["card_bg"], spacing=dp(4))
        self.body.add_widget(ctrl)
        line(ctrl, "KIỂM ĐỊNH HIỆU SUẤT THỰC TẾ & ĐỐI SOÁT", color=C["gold"], fs=FS["s"], bold=True)
        r2 = hrow(dp(40))
        self.btn_loop = make_btn("", C["card_sub"])
        self.btn_loop.bind(on_release=lambda *_: self._toggle_loop())
        r2.add_widget(self.btn_loop)
        b_clear = make_btn("XÓA TẤT CẢ", C["card_sub"], fg=C["bear_red"])
        b_clear.bind(on_release=lambda *_: self._clear_all())
        r2.add_widget(b_clear)
        ctrl.add_widget(r2)
        self._sync_loop()

        r3 = hrow(dp(40))
        r3.add_widget(tag("Chu kỳ:", C["text_muted"], FS["s"], bold=False))
        self.sp_cycle = make_spinner(e.perf_cycle, ["5m", "15m", "30m"], size_hint_x=0.35)
        self.sp_cycle.bind(text=lambda i, v: self._on_cycle(v))
        r3.add_widget(self.sp_cycle)
        b_now = make_btn("KIỂM TRA NGAY", C["accent_cyan"])
        b_now.bind(on_release=lambda *_: self._audit_now())
        r3.add_widget(b_now)
        ctrl.add_widget(r3)
        self.lbl_status = line(ctrl, "", fs=FS["xs"])
        self.update_countdown(m=e.perf_countdown_sec // 60, s=e.perf_countdown_sec % 60, cycle=e.perf_cycle, active=e.perf_monitor_active)

        # ---- Thống kê
        self.box_stats = Card(bg=C["card_sub"], spacing=dp(2))
        self.body.add_widget(self.box_stats)
        self.lbl_wr = line(self.box_stats, "TỔNG XÁC SUẤT THẮNG: 0.0%", color=C["gold"], fs=FS["l"], bold=True)
        self.lbl_sum = line(self.box_stats, "", fs=FS["xs"], bold=True)
        line(self.box_stats, "• Thống kê theo từng mô hình:", color=C["text_muted"], fs=FS["xs"], bold=True)
        self.lbl_setups = line(self.box_stats, "", fs=FS["xs"])

        self.lbl_title = line(self.body, "DANH SÁCH COIN ĐANG GIÁM SÁT (0):", color=C["text_muted"], fs=FS["s"], bold=True)
        self.list_box = new_grid()
        self.list_box.padding = [0, 0]
        self.body.add_widget(self.list_box)

    def on_show(self):
        self.render()

    # ---- đồng bộ trạng thái nút
    def _sync_auto(self):
        on = self.engine.auto_scan_send_webhook
        self.btn_auto.text = "GỬI BOT: BẬT" if on else "GỬI BOT: TẮT"
        self.btn_auto.background_color = C["bull_green"] if on else C["card_sub"]
        self.btn_auto.color = WHITE if on else C["bear_red"]
        self.lbl_auto.text = ui("Đang bật: Tự động gửi cảnh báo biến động Entry, TP, SL và danh mục Tab 5" if on
                                else "Đang tắt: Không gửi cảnh báo tự động")
        self.lbl_auto.color = C["bull_green"] if on else C["text_muted"]

    def _sync_loop(self):
        on = self.engine.perf_monitor_active
        self.btn_loop.text = f"GIÁM SÁT 12H: {'BẬT' if on else 'TẮT'}"
        self.btn_loop.color = C["bull_green"] if on else C["bear_red"]

    def update_countdown(self, m=0, s=0, cycle="5m", active=True, **_):
        self.lbl_status.text = ui(f"Trạng thái: {'Đang chạy' if active else 'Tạm dừng'} (Chu kỳ: {cycle} | Kế tiếp sau: {m:02d}m{s:02d}s)")
        self.lbl_status.color = C["bull_green"] if active else C["text_muted"]

    # ---- hành động
    def _paste(self):
        try:
            txt = (Clipboard.paste() or "").strip()
            if txt:
                self.ent_webhook.text = txt
                self.engine.add_log(f"Đã dán và lưu Webhook URL: {txt[:35]}...")
        except Exception:
            pass

    def _url(self):
        url = self.ent_webhook.text.strip()
        if not self.engine.webhook_valid(url):
            self.app.show_popup("Cảnh báo", "Vui lòng nhập định dạng Token Bot Telegram hợp lệ.", "warning")
            return None
        return url

    def _send_list(self):
        url = self._url()
        if url:
            self.engine.send_monitor_list_webhook(url)

    def _send_portfolio(self):
        url = self._url()
        if url:
            self.engine.send_portfolio_webhook(url)

    def _toggle_auto(self):
        self.engine.toggle_auto_webhook()
        self._sync_auto()

    def _toggle_loop(self):
        self.engine.toggle_perf_monitor()
        self._sync_loop()

    def _on_cycle(self, val):
        if val != self.engine.perf_cycle:
            self.engine.set_perf_cycle(val)
            sec = self.engine.perf_countdown_sec
            self.update_countdown(sec // 60, sec % 60, val, self.engine.perf_monitor_active)

    def _audit_now(self):
        if self.engine.perf_tracker.get_statistics()["open"] == 0:
            self.engine.add_log("Tab 4: Danh sách giám sát trống (0 coin) -> Dừng kiểm tra.")
            self.app.show_popup("Thông báo", "Danh sách coin cần giám sát đang trống (0 coin).", "info")
            return
        self.engine.audit_now()

    def _delete_one(self, trade_id, symbol):
        def _yes():
            if self.engine.perf_tracker.delete_single_trade(trade_id):
                self.engine.add_log(f"Đã xóa {symbol} khỏi danh sách giám sát.")
                self.render()
        self.app.show_popup("Xác nhận", f"Bạn có chắc muốn xóa mã {symbol} khỏi danh sách giám sát?", "confirm", on_confirm=_yes)

    def _clear_all(self):
        def _yes():
            self.engine.perf_tracker.clear_all()
            self.engine.add_log("Đã xóa sạch dữ liệu giám sát hiệu suất.")
            self.render()
        self.app.show_popup("Xác nhận", "Bạn có chắc muốn xóa toàn bộ danh sách giám sát không?", "confirm", on_confirm=_yes)

    # ---- hiển thị
    def render(self, **_):
        stats = self.engine.perf_tracker.get_statistics()
        wr = stats["win_rate"]
        self.lbl_wr.text = f"TỔNG XÁC SUẤT THẮNG: {wr:.1f}%"
        self.lbl_wr.color = C["bull_green"] if wr >= 65 else (C["gold"] if wr >= 50 else C["bear_red"])
        self.lbl_sum.text = f"Thắng: {stats['wins']} | Thua: {stats['losses']} | Đang chạy 12h: {stats['open']}"
        bs = stats["by_setup"]
        fmt = lambda k, name: f" - [{name}]: {bs[k]['wins']}/{bs[k]['total']} ({bs[k]['win_rate']:.1f}%)"  # noqa: E731
        self.lbl_setups.text = ui("\n".join([fmt("WAVE_2", "Sóng 2"), fmt("WAVE_3", "Sóng 3"), fmt("PULLBACK", "Pullback"),
                                             fmt("BREAKOUT", "Breakout"), fmt("SWEEP", "Quét TK")]))
        self.lbl_title.text = f"DANH SÁCH COIN ĐANG GIÁM SÁT ({len(stats['trades'])}):"

        self.list_box.clear_widgets()
        if not stats["trades"]:
            empty_msg(self.list_box, "Danh sách đang trống.\nSang Tab '3. Lệnh & NAV' và bấm '+ GHI NHẬN VÀO GIÁM SÁT 12H'.")
        for t in stats["trades"]:
            self.list_box.add_widget(self._trade_card(t))
        line(self.list_box, f"• Tệp báo cáo tự động: {core.PERF_LOG_FILE}", color=C["text_muted"], fs=FS["xs"])

    def _trade_card(self, t):
        st = t.get("status", "")
        filled = t.get("is_filled", False) or st in ("OPEN", "WIN_TP1", "WIN_TP2", "WIN_TP3", "WIN_TP1_BE",
                                                     "LOSS_SL", "EXPIRED_WIN", "EXPIRED_LOSS")
        txt, col = "CHƯA KHỚP ORDER", C["text_muted"]
        if not filled and st in ("PENDING", "EXPIRED_CANCEL"):
            txt, col = "CHỜ KHỚP ORDER", C["gold"]
        elif st == "OPEN":
            txt, col = "ĐÃ KHỚP ORDER", C["orange"]
        elif st == "WIN_TP1":
            txt, col = "ĐẠT TP1 (+50% & BE)", C["bull_green"]
        elif st == "WIN_TP2":
            txt, col = "ĐẠT TP2", C["bull_green"]
        elif st == "WIN_TP3":
            txt, col = "ĐẠT TP3 (MAX)", C["bull_green"]
        elif st == "WIN_TP1_BE":
            txt, col = "ĐẠT TP1 & VỀ HÒA VỐN", C["purple"]
        elif st == "LOSS_SL":
            txt, col = "CHẠM CẮT LỖ (SL)", C["bear_red"]
        elif st == "EXPIRED_CANCEL":
            txt, col = "HỦY (CHƯA KHỚP ENTRY)", C["text_muted"]
        elif "EXPIRED" in st:
            txt, col = "HẾT 12H GIÁM SÁT", C["text_muted"]

        card = Card(bg=C["card_bg"], pad=dp(6))
        r1 = hrow(dp(30))
        r1.add_widget(tag(t["symbol"], C["text_main"], FS["m"]))
        r1.add_widget(tag(f"[{t['setup_mode']}]", C["accent_cyan"], FS["xs"]))
        r1.add_widget(Widget())
        r1.add_widget(delete_btn(lambda tid=t["id"], sym=t["symbol"]: self._delete_one(tid, sym)))
        card.add_widget(r1)
        line(card, f"[{txt}]", color=col, fs=FS["xs"], bold=True)

        sv = t.get("start_time_vn", "")
        time_order = sv.split(" ")[1][:5] if " " in sv else sv
        date_order = sv.split(" ")[0][:5] if " " in sv else ""
        fill_val = t.get("fill_time_vn", "") or (sv if filled else "")
        if filled:
            fill_txt = f"Khớp Entry: {fill_val}" if fill_val else "Khớp Entry: [Đã khớp]"
        else:
            fill_txt = "Khớp Entry: [Chờ khớp...]"
        line(card, f"• Đặt Order: {time_order} ({date_order}) | {fill_txt}", color=C["text_muted"], fs=FS["xs"])
        line(card, f"[{st}]", color=C["bull_green"] if "WIN" in st else (C["bear_red"] if "LOSS" in st else C["gold"]),
             fs=FS["xs"], bold=True)

        is_be = st in ("WIN_TP1", "WIN_TP2", "WIN_TP1_BE")
        sl_str = f"SL: {format_price(t['sl'])} (Hòa Vốn - 0.0%)" if is_be else f"SL: {format_price(t['sl'])} (-{t['risk_pct']}%)"
        card.add_widget(kv_row(f"Order E: {format_price(t['entry'])}", C["dark_gold"],
                               f"TP1: {format_price(t['tp1'])} (+{t['tp1_pct']}%)", C["bull_green"]))
        card.add_widget(kv_row(sl_str, C["purple"] if is_be else C["bear_red"]))
        line(card, f"➔ {t['result_desc']}", color=C["text_muted"], fs=FS["xs"])
        return card


# ==============================================================================
# TAB 5: QUẢN LÝ TÀI SẢN
# ==============================================================================
class TabPortfolio(TabBase):
    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.add_widget(self.scroll)

        top = Card(bg=C["card_bg"], spacing=dp(4))
        self.body.add_widget(top)
        line(top, "QUẢN LÝ TÀI SẢN & VỊ THẾ NẮM GIỮ", color=C["bull_green"], fs=FS["m"], bold=True)
        self.btn_refresh = make_btn("KIỂM TRA & CẬP NHẬT", C["accent_blue"])
        self.btn_refresh.bind(on_release=lambda *_: self.on_refresh())
        top.add_widget(self.btn_refresh)
        self.lbl_status = line(top, "Sẵn sàng kiểm tra thị giá", color=C["text_muted"], fs=FS["xs"])

        box = Card(bg=C["card_sub"], pad=dp(6))
        top.add_widget(box)
        self.lbl_total = line(box, "TỔNG TÀI SẢN: $0.00 USDT", color=C["gold"], fs=FS["s"], bold=True)
        self.lbl_pnl = line(box, "LÃI/LỖ RÒNG: +$0.00 (+0.00%)", color=C["bull_green"], fs=FS["xs"], bold=True)

        self.list_box = new_grid()
        self.list_box.padding = [0, 0]
        self.body.add_widget(self.list_box)

    def on_show(self):
        self.render()

    def render(self, **_):
        assets = self.engine.asset_mgr.get_assets()
        total_val = total_cost = 0.0
        for a in assets:
            qty = a.get("quantity", 0.0)
            total_val += a.get("current_price", a.get("entry_price", 0.0)) * qty
            total_cost += a.get("entry_price", 0.0) * qty
        pnl = total_val - total_cost
        pnl_pct = (pnl / total_cost * 100.0) if total_cost > 0 else 0.0
        self.lbl_total.text = f"TỔNG TÀI SẢN: ${total_val:,.2f} USDT (Gốc: ${total_cost:,.2f})"
        self.lbl_pnl.text = f"LÃI/LỖ RÒNG: {pnl:+,.2f} USDT ({pnl_pct:+.2f}%)"
        self.lbl_pnl.color = C["bull_green"] if pnl >= 0 else C["bear_red"]

        self.list_box.clear_widgets()
        hdr = hrow(dp(32))
        hdr.add_widget(side_label(f"DANH SÁCH COIN NẮM GIỮ ({len(assets)}):"))
        if assets:
            b = make_btn("XÓA TẤT CẢ", C["card_sub"], fg=C["bear_red"], h=dp(28), fs=FS["xs"], size_hint_x=None, width=dp(100))
            b.bind(on_release=lambda *_: self._clear_all())
            hdr.add_widget(b)
        self.list_box.add_widget(hdr)

        if not assets:
            empty_msg(self.list_box, "Danh mục tài sản đang trống.\nKhi lệnh ở Tab 4 khớp Entry, coin sẽ tự động được thêm vào đây.")
            return
        for a in assets:
            self.list_box.add_widget(self._asset_card(a))

    def _asset_card(self, a):
        sym = a["symbol"]
        entry_p = a.get("entry_price", 0.0)
        curr_p = a.get("current_price", entry_p)
        qty = a.get("quantity", 0.0)
        diff = a.get("diff_pct", 0.0)
        rec = a.get("recommendation", "TIẾP TỤC THEO DÕI")
        dcol = C["bull_green"] if diff >= 0 else C["bear_red"]

        card = Card(bg=C["card_bg"], pad=dp(6))
        r1 = hrow(dp(30))
        r1.add_widget(tag(sym, C["text_main"], FS["l"]))
        if a.get("setup_mode"):
            r1.add_widget(tag(f"[{a['setup_mode']}]", C["accent_cyan"], FS["xs"]))
        r1.add_widget(Widget())
        r1.add_widget(delete_btn(lambda s=sym: self._delete_one(s)))
        card.add_widget(r1)
        card.add_widget(kv_row(f"Entry: {format_price(entry_p)} | Hiện tại: {format_price(curr_p)}", C["dark_gold"],
                               f"({diff:+.2f}%)", dcol, fs=FS["s"], h=dp(24)))
        line(card, f"Số lượng: {qty:,.4f} | Giá trị: ${curr_p * qty:,.2f} USDT", color=C["text_muted"], fs=FS["xs"])
        rbox = Card(bg=C["card_sub"], pad=dp(4))
        line(rbox, f"Đề xuất vị thế: {rec}", color=C["accent_cyan"] if "GỒNG" in rec else (C["gold"] if "CHỐT" in rec else dcol),
             fs=FS["xs"], bold=True)
        card.add_widget(rbox)
        return card

    def on_refresh(self):
        self.btn_refresh.disabled = True
        self.btn_refresh.text = "ĐANG CẬP NHẬT..."
        self.lbl_status.text = "Đang kết nối Binance lấy giá & chỉ báo..."
        self.engine.refresh_portfolio()

    def on_done(self, count=0, **_):
        self.btn_refresh.disabled = False
        self.btn_refresh.text = "KIỂM TRA & CẬP NHẬT"
        self.lbl_status.text = f"Đã cập nhật {count} coin lúc {datetime.now(TZ_VN).strftime('%H:%M:%S')}"
        self.render()

    def _delete_one(self, symbol):
        def _yes():
            if self.engine.asset_mgr.delete_asset(symbol):
                self.engine.add_log(f"Đã xóa {symbol} khỏi danh mục Quản lý tài sản.")
                self.render()
        self.app.show_popup("Xác nhận", f"Bạn có chắc muốn xóa {symbol} khỏi danh sách Quản lý tài sản?", "confirm", on_confirm=_yes)

    def _clear_all(self):
        def _yes():
            self.engine.asset_mgr.clear_all()
            self.engine.add_log("Đã xóa toàn bộ coin trong danh mục Quản lý tài sản.")
            self.render()
        self.app.show_popup("Xác nhận", "Bạn có chắc muốn xóa toàn bộ danh mục tài sản không?", "confirm", on_confirm=_yes)


# ==============================================================================
# TAB 6: VĨ MÔ & NEWS
# ==============================================================================
class TabMacro(TabBase):
    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.add_widget(self.scroll)
        self._loaded = False
        self._busy = False

        head = Card(bg=C["card_bg"], spacing=dp(4))
        self.body.add_widget(head)
        line(head, "QUANT & MACRO LIVE DASHBOARD", color=C["orange"], fs=FS["m"], bold=True)
        b = make_btn("CẬP NHẬT TIN", C["accent_blue"])
        b.bind(on_release=lambda *_: self.refresh())
        head.add_widget(b)

        self.content = new_grid()
        self.content.padding = [0, 0]
        self.body.add_widget(self.content)

    def on_show(self):
        if not self._loaded:
            self.refresh()

    def refresh(self):
        if self._busy:
            return
        self._busy = True
        self.engine.add_log("Đang cập nhật tin tức vĩ mô & phái sinh...")
        self.content.clear_widgets()
        empty_msg(self.content, "Đang kết nối API vĩ mô (Binance Spot/Futures, Fed St. Louis, Alternative.me)...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            btc_price, change_24h, vol_24h, btc_status = core.fetch_binance_market_data()
            dxy, dxy_chg, dxy_status = core.fetch_binance_dXY_proxy(self.engine.net)
            funding, oi_btc, fut_status = core.fetch_binance_derivatives()
            oi_usd = oi_btc * btc_price if btc_price > 0 else 0.0
            us10y, us10y_date, us10y_status = core.fetch_us10y_treasury_yield()
            btc_dom, total_mcap, cg_status = core.fetch_global_market_metrics()
            fng_val, fng_text, fng_status = core.fetch_fear_and_greed_index()
            bulletins = core.fetch_detailed_bulletins(funding, oi_btc, oi_usd, btc_dom, fng_val, fng_text, dxy, dxy_chg, us10y)
            data = dict(btc_price=btc_price, change_24h=change_24h, vol_24h=vol_24h, btc_status=btc_status,
                        dxy=dxy, dxy_chg=dxy_chg, dxy_status=dxy_status, funding=funding, oi_btc=oi_btc,
                        fut_status=fut_status, oi_usd=oi_usd, us10y=us10y, us10y_date=us10y_date,
                        us10y_status=us10y_status, btc_dom=btc_dom, total_mcap=total_mcap, fng_val=fng_val,
                        fng_text=fng_text, fng_status=fng_status, bulletins=bulletins)
            self.engine.ui_dispatch(lambda: self._build(data))
        except Exception as e:
            self.engine.add_log(f"Lỗi cập nhật Tab 6: {str(e)}")
            self.engine.ui_dispatch(self._fail)

    def _fail(self):
        self._busy = False
        self.content.clear_widgets()
        empty_msg(self.content, "Không tải được dữ liệu vĩ mô. Kiểm tra mạng rồi bấm 'CẬP NHẬT TIN'.")

    def _build(self, d):
        self._busy = False
        self._loaded = True
        self.content.clear_widgets()

        c_api = Card(bg=C["card_bg"])
        self.content.add_widget(c_api)
        line(c_api, "[1] TRẠNG THÁI KẾT NỐI API:", color=C["gold"], fs=FS["s"], bold=True)
        line(c_api, (f"• Binance Spot Feed: {d['btc_status']}\n• Binance Synthetic DXY: {d['dxy_status']}\n"
                     f"• Binance Futures: {d['fut_status']}\n• Fed St. Louis US10Y: {d['us10y_status']}\n"
                     f"• Alternative.me F&G: {d['fng_status']}"), fs=FS["xs"])

        c_mkt = Card(bg=C["card_bg"])
        self.content.add_widget(c_mkt)
        line(c_mkt, "[2] THÔNG SỐ VĨ MÔ & THỊ TRƯỜNG THỰC TẾ:", color=C["bull_green"], fs=FS["s"], bold=True)
        dom = f"{d['btc_dom']:.2f}%" if d["btc_dom"] > 0 else "N/A"
        mcap = f"${d['total_mcap'] / 1e12:.2f}T" if d["total_mcap"] > 0 else "N/A"
        us10 = f"{d['us10y']:.2f}% (Ngày {d['us10y_date']})" if d["us10y"] > 0 else "Chưa có dữ liệu"
        dxy = f"{d['dxy']:.2f} ({d['dxy_chg']:+.2f}%)" if d["dxy"] > 0 else "N/A"
        line(c_mkt, (f"• Giá BTC (Binance): ${d['btc_price']:,.2f} ({d['change_24h']:+.2f}%)\n"
                     f"• Khối lượng 24h BTC: ${d['vol_24h']:,.0f} USDT\n"
                     f"• US10Y (Yield 10Y): {us10}\n• DXY Index (Binance): {dxy}\n"
                     f"• BTC Dominance: {dom} | Vốn hóa TT: {mcap}\n"
                     f"• Fear & Greed: {d['fng_val']}/100 ({d['fng_text']})\n"
                     f"• Funding Rate (8h): {d['funding']:.4f}%\n"
                     f"• Open Interest (OI): {d['oi_btc']:,.0f} BTC (~${d['oi_usd'] / 1e9:.2f}B)"), fs=FS["xs"])

        c_news = Card(bg=C["card_bg"], spacing=dp(4))
        self.content.add_widget(c_news)
        line(c_news, "[3] BẢN TIN PHÂN TÍCH TÁC ĐỘNG VĨ MÔ & CRYPTO:", color=C["accent_cyan"], fs=FS["s"], bold=True)
        oi, chg = d["oi_btc"], d["change_24h"]
        if oi > 350000 and chg > 1.5:
            oi_eval = "Đánh giá Open Interest (OI): Đòn bẩy Long mở rộng mạnh theo đà tăng, lưu ý rủi ro biến động thanh lý hai chiều."
        elif oi > 350000 and chg < -1.5:
            oi_eval = "Đánh giá Open Interest (OI): Vị thế Short tích lũy khối lượng lớn, rủi ro vắt thanh khoản Short (Short Squeeze) khi chạm hỗ trợ cứng."
        elif oi < 150000:
            oi_eval = "Đánh giá Open Interest (OI): Khối lượng phái sinh ở mức thấp, thị trường vận động chủ yếu nhờ giao dịch giao ngay (Spot)."
        else:
            oi_eval = "Đánh giá Open Interest (OI): Cấu trúc vị thế mở ổn định, chưa ghi nhận áp lực nén đòn bẩy cực đoan."
        line(c_news, f"• {oi_eval}", fs=FS["xs"])
        for idx, b in enumerate(d["bulletins"], 1):
            line(c_news, f"({idx}) {b}", fs=FS["xs"])
        self.engine.add_log("Tab 6: Dữ liệu vĩ mô, US10Y & DXY real-time đã cập nhật thành công.")


# ==============================================================================
# TAB 7: CẤU HÌNH BỘ LỌC  (Filter_Setting.json)
# ==============================================================================
class TabConfig(TabBase):
    def __init__(self, app, **kw):
        super().__init__(app, **kw)
        self.add_widget(self.scroll)
        self.inputs = {}
        self.checks = {}
        self._built = False
        self._silent = False

        head = Card(bg=C["card_bg"], spacing=dp(4))
        self.body.add_widget(head)
        line(head, "CẤU HÌNH BỘ LỌC (Filter_Setting.json)", color=C["accent_cyan"], fs=FS["m"], bold=True)
        self.lbl_status = line(head, "Tự động lưu khi chỉnh. Áp dụng ở lần quét kế tiếp.", color=C["text_muted"], fs=FS["xs"])
        r = hrow(dp(38))
        b1 = make_btn("TẢI LẠI FILE", C["accent_blue"])
        b1.bind(on_release=lambda *_: self.reload_file())
        b2 = make_btn("KHÔI PHỤC MẶC ĐỊNH", C["bear_red"])
        b2.bind(on_release=lambda *_: self.reset_defaults())
        r.add_widget(b1)
        r.add_widget(b2)
        head.add_widget(r)

    def on_show(self):
        if not self._built:
            self._build()
        self.refresh_values()

    def _build(self):
        for g in sorted(FilterConfig.GROUP_TITLES):
            card = Card(bg=C["card_bg"], spacing=dp(4))
            self.body.add_widget(card)
            line(card, FilterConfig.GROUP_TITLES[g], color=C["gold"], fs=FS["s"], bold=True)
            if g == 5:
                pr = hrow(dp(36))
                for name, val in FilterConfig.SCORE_PRESETS.items():
                    b = make_btn(name, C["card_sub"], fg=C["text_main"], h=dp(36), fs=FS["xs"])
                    b.bind(on_release=lambda i, v=val: self.commit("min_score_threshold", v))
                    pr.add_widget(b)
                card.add_widget(pr)
            for sp_ in FilterConfig.SPECS:
                if sp_[7] == g:
                    self._add_row(card, sp_)
            if g == 5:
                for key, label, _d in FilterConfig.BOOL_SPECS:
                    row = hrow(dp(52))
                    cb = CheckBox(size_hint_x=None, width=dp(44))
                    cb.bind(active=lambda i, v, k=key: self._on_check(k, v))
                    self.checks[key] = cb
                    lb = Label(text=ui(label), color=C["text_main"], font_size=FS["xs"], halign="left", valign="middle")
                    lb.bind(size=lambda i, v: setattr(i, "text_size", v))
                    row.add_widget(cb)
                    row.add_widget(lb)
                    card.add_widget(row)
        self._built = True

    def _add_row(self, card, sp_):
        key, label, lo, hi, step, typ, default, _g, unit = sp_
        unit_txt = f" ({unit})" if unit else ""
        line(card, f"{label}{unit_txt}", color=C["text_main"], fs=FS["s"])      # nhãn trải hết chiều ngang, tự xuống dòng
        row = hrow(dp(40))
        bm = make_btn("-", C["card_sub"], fg=C["text_main"], fs=FS["l"], size_hint_x=None, width=dp(48))
        bm.bind(on_release=lambda *_: self.nudge(key, -1))
        ti = make_input("", inrow=True, input_filter=num_filter)
        ti.halign = "center"
        ti.foreground_color = C["gold"]
        ti.bind(on_text_validate=lambda *_: self.commit_entry(key))
        ti.bind(focus=lambda i, f: (not f) and self.commit_entry(key))
        bp = make_btn("+", C["card_sub"], fg=C["text_main"], fs=FS["l"], size_hint_x=None, width=dp(48))
        bp.bind(on_release=lambda *_: self.nudge(key, +1))
        row.add_widget(bm)
        row.add_widget(ti)
        row.add_widget(bp)
        card.add_widget(row)
        self.inputs[key] = ti
        lo_s, hi_s = (f"{lo:,}", f"{hi:,}") if typ == "int" else (f"{lo:g}", f"{hi:g}")
        d_s = f"{default:,}" if typ == "int" else f"{default:g}"
        line(card, f"Dải [{lo_s} … {hi_s}]  |  mặc định {d_s}", color=C["text_muted"], fs=FS["xs"])

    # ---- logic
    def _fmt(self, key, val):
        sp_ = FilterConfig.spec_of(key)
        return str(int(val)) if sp_ and sp_[5] == "int" else f"{float(val):g}"

    def refresh_values(self):
        snap = FILTER_CFG.snapshot()
        self._silent = True
        for key, ti in self.inputs.items():
            ti.text = self._fmt(key, snap[key])
        for key, cb in self.checks.items():
            cb.active = bool(snap.get(key, False))
        self._silent = False

    def reload_file(self):
        FILTER_CFG._refresh(force=True)
        self.refresh_values()
        self._status("Đã tải lại từ Filter_Setting.json", C["accent_cyan"])

    def reset_defaults(self):
        ok = FILTER_CFG.reset()
        self.refresh_values()
        self._status("Đã khôi phục mặc định" if ok else "Lỗi ghi file Filter_Setting.json",
                     C["gold"] if ok else C["bear_red"])

    def nudge(self, key, direction):
        sp_ = FilterConfig.spec_of(key)
        try:
            cur = float(self.inputs[key].text.replace(",", "."))
        except Exception:
            cur = FILTER_CFG.get(key)
        self.commit(key, cur + direction * sp_[4])

    def commit_entry(self, key):
        if self._silent:
            return
        try:
            val = float(self.inputs[key].text.replace(",", "."))
        except Exception:
            self.refresh_values()
            self._status(f"Giá trị không hợp lệ: {key}", C["bear_red"])
            return
        if abs(val - float(FILTER_CFG.get(key))) > 1e-9:
            self.commit(key, val)

    def _on_check(self, key, val):
        if not self._silent:
            self.commit(key, bool(val))

    def commit(self, key, value):
        before = FILTER_CFG.snapshot().get(key)
        ok = FILTER_CFG.update({key: value})
        self.refresh_values()
        after = FILTER_CFG.get(key)
        if not ok:
            self._status("Lỗi ghi file Filter_Setting.json", C["bear_red"])
        elif not isinstance(value, bool) and abs(float(value) - float(after)) > 1e-9:
            self._status(f"{key}: giá trị bị kẹp về {after:g} (ngoài dải cho phép)", C["gold"])
        elif before != after:
            self._status(f"Đã lưu {key} = {after}", C["bull_green"])
            self.engine.add_log(f"[CẤU HÌNH] {key}: {before} -> {after}")

    def _status(self, text, color):
        self.lbl_status.text = ui(text)
        self.lbl_status.color = color


# ==============================================================================
# ỨNG DỤNG CHÍNH
# ==============================================================================
TAB_META = [
    ("1. Tín Hiệu", C["gold"]), ("2. Chẩn Đoán", C["accent_cyan"]), ("3. Lệnh & NAV", C["bull_green"]),
    ("4. Giám Sát", C["purple"]), ("5. Quản Lý Tài Sản", C["bull_green"]),
    ("6. Vĩ Mô & News", C["orange"]), ("7. Cấu Hình", C["accent_cyan"]),
]


class CryptoApp(App):
    title = "Crypto Institutional Master Pro"

    def build(self):
        Window.clearcolor = C["bg_main"]
        try:
            Window.softinput_mode = "below_target"   # bàn phím ảo không che ô nhập
        except Exception:
            pass

        self.engine = core.Engine()
        self.engine.ui_dispatch = lambda fn: Clock.schedule_once(lambda dt: fn(), 0)
        self._log_popup = None
        self._log_label = None

        root = BoxLayout(orientation="vertical")
        root.add_widget(self._make_top_bar())
        root.add_widget(self._make_tab_bar())

        self.content = BoxLayout()
        root.add_widget(self.content)
        root.add_widget(self._make_bottom_bar())

        self.tab_signals = TabSignals(self)
        self.tab_diag = TabDiagnostics(self)
        self.tab_nav = TabNavOrder(self)
        self.tab_monitor = TabMonitor(self)
        self.tab_portfolio = TabPortfolio(self)
        self.tab_macro = TabMacro(self)
        self.tab_config = TabConfig(self)
        self.tabs = [self.tab_signals, self.tab_diag, self.tab_nav, self.tab_monitor,
                     self.tab_portfolio, self.tab_macro, self.tab_config]

        e = self.engine
        e.on("btc_status", self._on_btc_status)
        e.on("conn", self._on_conn)
        e.on("scan_start", self._on_scan_start)
        e.on("scan_done", self._on_scan_done)
        e.on("scan_error", self._on_scan_error)
        e.on("custom_scan_done", self.tab_diag.on_custom_done)
        e.on("perf_tick", self.tab_monitor.update_countdown)
        e.on("monitor_refresh", self.tab_monitor.render)
        e.on("portfolio_refresh", self.tab_portfolio.render)
        e.on("portfolio_done", self.tab_portfolio.on_done)
        e.on("portfolio_webhook_sent", lambda **_: self.show_popup("Thành công", "Đã gửi báo cáo danh mục tài sản về Telegram!", "success"))
        e.on("log", self._on_log)

        self.switch_tab(0)
        Clock.schedule_interval(self._tick_clock, 1)
        Clock.schedule_once(lambda dt: e.check_connection(), 0.5)
        e.start_background()
        return root

    # ---- thanh trên / dưới
    def _make_top_bar(self):
        bar = Card(bg=C["card_bg"], pad=[dp(8), dp(4)], spacing=0)
        row = hrow(dp(30))
        self.lbl_conn = Button(text="BINANCE: KẾT NỐI...", color=C["gold"], font_size=FS["xs"], bold=True,
                               background_normal="", background_down="", background_color=(0, 0, 0, 0), halign="left")
        self.lbl_conn.bind(size=lambda i, v: setattr(i, "text_size", v), on_release=lambda *_: self.engine.check_connection())
        self.lbl_btc = Label(text="[BTC: Green]", color=C["bull_green"], font_size=FS["xs"], bold=True, halign="center")
        self.lbl_btc.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.lbl_clock = Label(text="--:--:-- VN", color=C["accent_cyan"], font_size=FS["xs"], bold=True, halign="right")
        self.lbl_clock.bind(size=lambda i, v: setattr(i, "text_size", v))
        row.add_widget(self.lbl_conn)
        row.add_widget(self.lbl_btc)
        row.add_widget(self.lbl_clock)
        bar.add_widget(row)
        return bar

    def _make_tab_bar(self):
        grid = GridLayout(cols=4, rows=2, size_hint_y=None, height=dp(88), spacing=dp(1))
        self.tab_btns = []
        for idx, (title, _col) in enumerate(TAB_META):
            b = make_btn(title, C["tab_inactive"], fg=C["text_muted"], h=dp(44), fs=FS["xs"])
            b.size_hint_y = 1
            b.bind(on_release=lambda i, n=idx: self.switch_tab(n))
            self.tab_btns.append(b)
            grid.add_widget(b)
        b_log = make_btn("Nhật Ký", C["tab_inactive"], fg=C["text_muted"], h=dp(44), fs=FS["xs"])
        b_log.size_hint_y = 1
        b_log.bind(on_release=lambda *_: self.show_log())
        grid.add_widget(b_log)
        return grid

    def _make_bottom_bar(self):
        bar = BoxLayout(size_hint_y=None, height=dp(52), padding=[dp(6), dp(6)], spacing=dp(6))
        with bar.canvas.before:
            Color(*C["card_bg"])
            rect = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda i, v: setattr(rect, "pos", v), size=lambda i, v: setattr(rect, "size", v))
        self.btn_scan = make_btn("QUÉT TOÀN BỘ", C["accent_blue"], size_hint_x=None, width=dp(130))
        self.btn_scan.size_hint_y = 1
        self.btn_scan.bind(on_release=lambda *_: self.engine.start_screener_thread())
        self.lbl_scan = Label(text="Sẵn sàng phân tích (Quant Gating Active)", color=C["text_muted"], font_size=FS["xs"],
                              halign="left", valign="middle")
        self.lbl_scan.bind(size=lambda i, v: setattr(i, "text_size", v))
        bar.add_widget(self.btn_scan)
        bar.add_widget(self.lbl_scan)
        return bar

    # ---- chuyển tab
    def switch_tab(self, idx):
        for i, b in enumerate(self.tab_btns):
            if i == idx:
                b.background_color = C["tab_active"]
                b.color = TAB_META[i][1]
            else:
                b.background_color = C["tab_inactive"]
                b.color = C["text_muted"]
        self.content.clear_widgets()
        self.content.add_widget(self.tabs[idx])
        self.tabs[idx].on_show()

    # ---- sự kiện từ Engine
    def _tick_clock(self, dt):
        self.lbl_clock.text = datetime.now(TZ_VN).strftime("%H:%M:%S VN")

    def _on_btc_status(self, text="", color=None, **_):
        self.lbl_btc.text = ui(text)
        if color:
            self.lbl_btc.color = get_color_from_hex(color) if isinstance(color, str) else color

    def _on_conn(self, state="", ms=0, **_):
        if state == "testing":
            self.lbl_conn.text, self.lbl_conn.color = "BINANCE: ĐANG THỬ...", C["gold"]
        elif state == "live":
            self.lbl_conn.text, self.lbl_conn.color = f"BINANCE: LIVE ({ms}ms)", C["bull_green"]
        else:
            self.lbl_conn.text, self.lbl_conn.color = "BINANCE: MẤT KẾT NỐI", C["bear_red"]

    def _on_scan_start(self, **_):
        self.btn_scan.disabled = True
        self.btn_scan.background_color = C["tab_active"]
        self.lbl_scan.text = "Đang quét Universe (Quant Gate 1/2/3)..."
        self.lbl_scan.color = C["gold"]

    def _on_scan_done(self, count=0, **_):
        self.btn_scan.disabled = False
        self.btn_scan.background_color = C["accent_blue"]
        self.lbl_scan.text = f"Xong: {count} tín hiệu đạt chuẩn"
        self.lbl_scan.color = C["bull_green"]
        self.tab_signals.render()

    def _on_scan_error(self, **_):
        self.btn_scan.disabled = False
        self.btn_scan.background_color = C["accent_blue"]
        self.lbl_scan.text = "Lỗi chu kỳ quét"
        self.lbl_scan.color = C["bear_red"]

    # ---- popup
    def show_popup(self, title, message, kind="info", on_confirm=None):
        accent = {"info": C["accent_cyan"], "success": C["bull_green"], "warning": C["gold"],
                  "error": C["bear_red"], "confirm": C["accent_blue"]}.get(kind, C["accent_cyan"])
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        msg = Label(text=ui(message), color=C["text_main"], font_size=FS["m"], halign="left", valign="top")
        msg.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        box.add_widget(msg)
        row = hrow(dp(44), spacing=dp(8))
        pop = Popup(title=ui(title.upper()), content=box, size_hint=(0.92, None), height=dp(280),
                    auto_dismiss=False, separator_color=accent, title_color=accent, title_size=FS["m"])
        if on_confirm:
            b_no = make_btn("HỦY", C["card_sub"], fg=C["text_muted"])
            b_no.bind(on_release=lambda *_: pop.dismiss())
            b_yes = make_btn("XÁC NHẬN", accent)

            def _yes(*_):
                pop.dismiss()
                on_confirm()
            b_yes.bind(on_release=_yes)
            row.add_widget(b_no)
            row.add_widget(b_yes)
        else:
            b = make_btn("ĐỒNG Ý", accent)
            b.bind(on_release=lambda *_: pop.dismiss())
            row.add_widget(b)
        box.add_widget(row)
        pop.open()

    # ---- nhật ký
    def show_log(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        sv = ScrollView(do_scroll_x=False, bar_width=dp(3))
        lbl = Label(text=ui("\n".join(self.engine.log_lines)), color=C["text_main"], font_size=FS["xs"],
                    halign="left", valign="top", size_hint_y=None)
        lbl.bind(width=lambda i, w: setattr(i, "text_size", (w, None)),
                 texture_size=lambda i, ts: setattr(i, "height", ts[1]))
        sv.add_widget(lbl)
        box.add_widget(sv)
        b = make_btn("ĐÓNG", C["accent_blue"])
        box.add_widget(b)
        pop = Popup(title="NHẬT KÝ HOẠT ĐỘNG", content=box, size_hint=(0.96, 0.85), auto_dismiss=False)
        b.bind(on_release=lambda *_: pop.dismiss())
        self._log_label = lbl
        pop.bind(on_dismiss=lambda *_: setattr(self, "_log_label", None))
        pop.open()
        Clock.schedule_once(lambda dt: setattr(sv, "scroll_y", 0), 0.1)

    def _on_log(self, line="", **_):
        if self._log_label is not None:
            self._log_label.text = ui("\n".join(self.engine.log_lines))

    # ---- vòng đời Android
    def on_pause(self):
        return True     # giữ ứng dụng sống khi chuyển sang app khác

    def on_resume(self):
        pass

    def on_stop(self):
        self.engine.shutdown()


if __name__ == "__main__":
    try:
        CryptoApp().run()
    except Exception:
        import traceback
        err = traceback.format_exc()
        try:
            with open(os.path.join(os.environ["CRYPTO_DATA_DIR"], "crash_log.txt"), "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
        print(err)
