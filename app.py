"""
Divergens Dashboard
===================
Streamlit-app med TradingView-inspirerat interaktivt analysverktyg.

Installation:
    pip install streamlit yfinance pandas numpy ta requests

Kör:
    python -m streamlit run app.py
"""

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json, os, smtplib, requests as req
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit.components.v1 as components

from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from ta.volume import OnBalanceVolumeIndicator

# ─────────────────────────────────────────────
# KONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Divergens Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    .stApp { background-color: #131722; color: #d1d4dc; }
    section[data-testid="stSidebar"] { background-color: #1e222d; border-right: 1px solid #2a2e39; }
    .metric-card {
        background: #1e222d; border: 1px solid #2a2e39;
        border-radius: 8px; padding: 16px; margin-bottom: 10px;
    }
    .metric-value { font-family: 'DM Mono', monospace; font-size: 1.4rem; color: #d1d4dc; }
    .metric-label { font-size: 0.7rem; color: #787b86; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px; }
    .section-header {
        font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.15em;
        color: #787b86; margin: 20px 0 10px 0; padding-bottom: 6px;
        border-bottom: 1px solid #2a2e39;
    }
    .hit-badge { font-family: 'DM Mono', monospace; font-size: 0.75rem; padding: 2px 7px; border-radius: 3px; }
    .hit-strong { background: #0d2d1f; color: #26a69a; }
    .hit-medium { background: #1c1917; color: #f0b429; }
    .hit-weak   { background: #1e222d; color: #787b86; }
    div[data-testid="stMetric"] { background: #1e222d; border: 1px solid #2a2e39; border-radius: 8px; padding: 14px; }
    .stButton button {
        background: #2962ff; color: white; border: none;
        border-radius: 6px; font-family: 'DM Mono', monospace;
        font-size: 0.82rem; padding: 9px 16px; transition: all 0.15s;
    }
    .stButton button:hover { background: #1e53e5; }
    h1, h2, h3 { font-family: 'DM Sans', sans-serif; font-weight: 600; color: #d1d4dc; }
    .stSelectbox label, .stMultiSelect label, .stSlider label,
    .stRadio label, .stCheckbox label, .stTextInput label { color: #787b86 !important; }
    div[data-testid="stDataFrame"] { border: 1px solid #2a2e39; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


INDEX_LISTS = {
    "OMX Stockholm 30": [
        "ABB.ST","ALFA.ST","ASSA-B.ST","AZN.ST","ATCO-A.ST","BOL.ST",
        "CAST.ST","ERIC-B.ST","ESSITY-B.ST","GETI-B.ST","HM-B.ST","HEXA-B.ST",
        "HUSQ-B.ST","INVE-B.ST","KINV-B.ST","NDA-SE.ST","NIBE-B.ST","SAND.ST",
        "SCA-B.ST","SEB-A.ST","SHB-A.ST","SKF-B.ST","SSAB-A.ST","SWED-A.ST",
        "SWMA.ST","TELE2-B.ST","TELIA.ST","VOLV-B.ST","WALL-B.ST","LIFCO-B.ST",
    ],
    "OMX Stockholm Large Cap (urval)": [
        "BALD-B.ST","BEIJ-B.ST","BILI-A.ST","BOOL.ST","CIBUS.ST","ELUX-B.ST",
        "EVO.ST","FABG.ST","HUFV-A.ST","ICA.ST","INDU-A.ST","JM.ST",
        "LATO-B.ST","MIPS.ST","NENT-B.ST","PEAB-B.ST","VIT-B.ST","XVIVO.ST",
    ],
    "OMX Stockholm Mid Cap (urval)": [
        "ADDV-B.ST","BUFAB.ST","CRED-A.ST","DUNI.ST","ENEA.ST",
        "OEM-B.ST","RATO-B.ST","SWEC-A.ST","THULE.ST","VITR.ST",
    ],
    "Nasdaq 100 (urval)": [
        "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO",
        "ADBE","COST","NFLX","AMD","INTC","QCOM","INTU","AMAT",
    ],
    "S&P 500 – Tech (urval)": [
        "AAPL","MSFT","NVDA","GOOGL","META","AVGO","ORCL","CSCO",
        "ACN","IBM","TXN","QCOM","NOW","AMAT","ADI","LRCX",
    ],
    "DAX 40 (urval)": [
        "ADS.DE","AIR.DE","ALV.DE","BAS.DE","BAYN.DE","BMW.DE",
        "DBK.DE","DTE.DE","EOAN.DE","IFX.DE","MRK.DE","SAP.DE","SIE.DE",
    ],
    "Nordiska börser (urval)": [
        "NOVO-B.CO","CARL-B.CO","DSV.CO","MAERSK-B.CO",
        "EQNR.OL","DNB.OL","NHY.OL","NESTE.HE","SAMPO.HE","NOKIA.HE",
    ],
    "Råvaror": [
        "GC=F","SI=F","PL=F","HG=F","CL=F","BZ=F","NG=F",
        "ZW=F","ZC=F","ZS=F","KC=F","CC=F","SB=F","CT=F",
    ],
    "Valutor (Forex)": [
        "EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","USDSEK=X",
        "EURSEK=X","USDNOK=X","AUDUSD=X","NZDUSD=X","USDCAD=X",
    ],
    "Kryptovalutor": [
        "BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD",
        "ADA-USD","AVAX-USD","DOGE-USD","DOT-USD","LINK-USD",
        "MATIC-USD","LTC-USD","ATOM-USD","XLM-USD",
    ],
}

TICKER_NAMES = {
    "GC=F":"Guld","SI=F":"Silver","PL=F":"Platina","HG=F":"Koppar",
    "CL=F":"Råolja (WTI)","BZ=F":"Råolja (Brent)","NG=F":"Naturgas",
    "ZW=F":"Vete","ZC=F":"Majs","ZS=F":"Sojabönor",
    "KC=F":"Kaffe","CC=F":"Kakao","SB=F":"Socker","CT=F":"Bomull",
    "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY",
    "USDCHF=X":"USD/CHF","USDSEK=X":"USD/SEK","EURSEK=X":"EUR/SEK",
    "USDNOK=X":"USD/NOK","AUDUSD=X":"AUD/USD","NZDUSD=X":"NZD/USD","USDCAD=X":"USD/CAD",
    "BTC-USD":"Bitcoin","ETH-USD":"Ethereum","BNB-USD":"BNB",
    "SOL-USD":"Solana","XRP-USD":"Ripple","ADA-USD":"Cardano",
    "AVAX-USD":"Avalanche","DOGE-USD":"Dogecoin","DOT-USD":"Polkadot",
    "LINK-USD":"Chainlink","MATIC-USD":"Polygon","LTC-USD":"Litecoin",
    "ATOM-USD":"Cosmos","XLM-USD":"Stellar",
}

RS_BENCHMARKS = {
    "OMX Stockholm 30": "^OMX", "OMX Stockholm Large Cap (urval)": "^OMX",
    "OMX Stockholm Mid Cap (urval)": "^OMX", "Nasdaq 100 (urval)": "^NDX",
    "S&P 500 – Tech (urval)": "^GSPC", "DAX 40 (urval)": "^GDAXI",
    "Nordiska börser (urval)": "^OMX", "Råvaror": "GC=F",
    "Valutor (Forex)": "EURUSD=X", "Kryptovalutor": "BTC-USD",
    "Bevakningslista": "^OMX",
}

ALERTS_FILE = "alerts_sent.json"
EMAIL_TO    = ""

RSI_PERIOD = 14; MACD_FAST = 12; MACD_SLOW = 26; MACD_SIGNAL_WIN = 9
STOCH_K = 14; STOCH_D = 3; LOOKBACK_BARS = 20; MIN_DISTANCE_BARS = 3


# ─────────────────────────────────────────────
# DIVERGENSLOGIK
# ─────────────────────────────────────────────

def find_local_lows(series, distance=3, n=20):
    s = series.iloc[-n:]
    lows = []
    for i in range(1, len(s) - 1):
        if s.iloc[i] <= s.iloc[i-1] and s.iloc[i] <= s.iloc[i+1]:
            if not lows or (i - lows[-1]) >= distance:
                lows.append(i)
    return lows

def find_local_highs(series, distance=3, n=40):
    s = series.iloc[-n:]
    highs = []
    for i in range(1, len(s) - 1):
        if s.iloc[i] >= s.iloc[i-1] and s.iloc[i] >= s.iloc[i+1]:
            if not highs or (i - highs[-1]) >= distance:
                highs.append(i)
    return highs

def divergence_detail(price_series, indicator_series, lookback=20, distance=3):
    price_lows = find_local_lows(price_series, distance, lookback)
    ind_lows   = find_local_lows(indicator_series, distance, lookback)
    if len(price_lows) < 2 or len(ind_lows) < 2:
        return False, None, None, None, None
    p1, p2 = price_lows[-2], price_lows[-1]
    i1, i2 = ind_lows[-2],   ind_lows[-1]
    base_price = price_series.iloc[-lookback:]
    base_ind   = indicator_series.iloc[-lookback:]
    pv1, pv2 = float(base_price.iloc[p1]), float(base_price.iloc[p2])
    iv1, iv2 = float(base_ind.iloc[i1]),   float(base_ind.iloc[i2])
    return (pv2 < pv1) and (iv2 > iv1), p1, p2, i1, i2

def calc_support_resistance(close, n_bars=60, distance=5):
    lows  = find_local_lows(close,  distance=distance, n=n_bars)
    highs = find_local_highs(close, distance=distance, n=n_bars)
    base  = close.iloc[-n_bars:]
    supports    = sorted({round(float(base.iloc[i]), 2) for i in lows})[-3:]
    resistances = sorted({round(float(base.iloc[i]), 2) for i in highs}, reverse=True)[:3]
    return supports, resistances

def volume_signal(volume, n=20):
    try:
        avg  = float(volume.iloc[-n:-1].mean())
        last = float(volume.iloc[-1])
        if avg == 0: return None, False
        ratio = last / avg
        return ratio, ratio > 1.5
    except Exception:
        return None, False


# ─────────────────────────────────────────────
# DATAHÄMTNING & ANALYS
# ─────────────────────────────────────────────

# Tidsramar: (intervall, period, antal staplar för "1 mån", etikett för senaste stapel, diagramnamn, staplar i diagram)
TIMEFRAMES = {
    "Dag":   {"interval": "1d",  "period": "2y",  "month_bars": 21, "chg_lbl": "1d", "name": "Daggraf",   "n": 120, "start": "6 m."},
    "Vecka": {"interval": "1wk", "period": "5y",  "month_bars": 4,  "chg_lbl": "1v", "name": "Veckograf", "n": 80,  "start": "1 år"},
    "Månad": {"interval": "1mo", "period": "max", "month_bars": 1,  "chg_lbl": "1m", "name": "Månadsgraf","n": 120, "start": "10 år"},
}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_and_analyze(ticker_yf, tf="Vecka", full=False):
    try:
        cfg = TIMEFRAMES[tf]
        df = yf.download(ticker_yf, period="max" if full else cfg["period"], interval=cfg["interval"],
                         progress=False, auto_adjust=True)
        if df is None or len(df) < 40:
            return None
        if isinstance(df.columns, pd.MultiIndex):        # nyare yfinance: (Price, Ticker)
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        close  = df["Close"].squeeze()
        high   = df["High"].squeeze()
        low    = df["Low"].squeeze()
        volume = df["Volume"].squeeze()

        rsi      = RSIIndicator(close=close, window=RSI_PERIOD).rsi()
        macd_obj = MACD(close=close, window_fast=MACD_FAST,
                        window_slow=MACD_SLOW, window_sign=MACD_SIGNAL_WIN)
        macd        = macd_obj.macd()
        macd_signal = macd_obj.macd_signal()
        macd_hist   = macd_obj.macd_diff()
        stoch = StochasticOscillator(high=high, low=low, close=close,
                                     window=STOCH_K, smooth_window=STOCH_D).stoch()
        obv   = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

        dr, rp1, rp2, ri1, ri2 = divergence_detail(close, rsi,   LOOKBACK_BARS, MIN_DISTANCE_BARS)
        dm, mp1, mp2, mi1, mi2 = divergence_detail(close, macd,  LOOKBACK_BARS, MIN_DISTANCE_BARS)
        ds, sp1, sp2, si1, si2 = divergence_detail(close, stoch, LOOKBACK_BARS, MIN_DISTANCE_BARS)
        do, op1, op2, oi1, oi2 = divergence_detail(close, obv,   LOOKBACK_BARS, MIN_DISTANCE_BARS)

        supports, resistances = calc_support_resistance(close)
        vol_ratio, vol_high   = volume_signal(volume)

        ma20  = close.rolling(20).mean()
        ma50  = close.rolling(50).mean()
        ma200 = close.rolling(200).mean()

        return {
            "df": df, "close": close, "volume": volume,
            "rsi": rsi, "macd": macd, "macd_signal": macd_signal,
            "macd_hist": macd_hist, "stoch": stoch, "obv": obv,
            "ma20": ma20, "ma50": ma50, "ma200": ma200,
            "price":      float(close.iloc[-1]),
            "week_chg":   float((close.iloc[-1] / close.iloc[-2] - 1) * 100),
            "month_chg":  float((close.iloc[-1] / close.iloc[-1 - cfg["month_bars"]] - 1) * 100) if len(close) > cfg["month_bars"] else 0.0,
            "tf": tf,
            "rsi_val":    float(rsi.iloc[-1]),
            "hits":       sum([dr, dm, ds, do]),
            "RSI": dr,        "rsi_pts":   (rp1, rp2, ri1, ri2),
            "MACD": dm,       "macd_pts":  (mp1, mp2, mi1, mi2),
            "Stochastic": ds, "stoch_pts": (sp1, sp2, si1, si2),
            "OBV": do,        "obv_pts":   (op1, op2, oi1, oi2),
            "supports": supports, "resistances": resistances,
            "vol_ratio": vol_ratio, "vol_high": vol_high,
        }
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_benchmark(ticker, tf="Vecka"):
    try:
        cfg = TIMEFRAMES[tf]
        df = yf.download(ticker, period=cfg["period"], interval=cfg["interval"], progress=False, auto_adjust=True)
        if df is None or len(df) < 10: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df["Close"].squeeze()
    except Exception:
        return None

def calc_rs(close, benchmark_close, periods=12):
    try:
        aligned = pd.concat([close, benchmark_close], axis=1, join="inner")
        aligned.columns = ["stock", "bench"]
        aligned = aligned.iloc[-periods:]
        rs = (aligned["stock"] / aligned["stock"].iloc[0]) / \
             (aligned["bench"] / aligned["bench"].iloc[0]) * 100 - 100
        return float(rs.iloc[-1])
    except Exception:
        return None


# ─────────────────────────────────────────────
# TRADINGVIEW-INSPIRERAT INTERAKTIVT DIAGRAM
# ─────────────────────────────────────────────

def build_chart_html(result, ticker_name, show_inds, show_support, show_ma,
                     benchmark_close=None, height=700):
    """Bygger ett komplett TradingView-inspirerat diagram med Lightweight Charts."""

    tf_cfg = TIMEFRAMES[result.get("tf", "Vecka")]
    n = len(result["close"])  # hela historiken laddas, periodknapparna styr vad som syns
    df_s   = result["df"].iloc[-n:].copy()
    close  = result["close"].iloc[-n:]
    vol    = result["volume"].iloc[-n:]
    offset = len(result["close"]) - n

    def adj(pts):
        return tuple(max(0, p - offset) if p is not None else None for p in pts)

    rp1, rp2, ri1, ri2 = adj(result["rsi_pts"])
    mp1, mp2, mi1, mi2 = adj(result["macd_pts"])
    sp1, sp2, si1, si2 = adj(result["stoch_pts"])
    op1, op2, oi1, oi2 = adj(result["obv_pts"])

    # ── Konvertera OHLCV till JSON ──
    candle_data = []
    vol_data    = []
    dates_list  = []
    for i, (idx, row) in enumerate(df_s.iterrows()):
        ts = int(pd.Timestamp(idx).timestamp())
        o = round(float(row["Open"]),  4)
        h = round(float(row["High"]),  4)
        l = round(float(row["Low"]),   4)
        c = round(float(row["Close"]), 4)
        v = int(float(row["Volume"]))
        candle_data.append({"time": ts, "open": o, "high": h, "low": l, "close": c})
        vol_data.append({"time": ts, "value": v,
                          "color": "#26a69a" if c >= o else "#ef5350"})
        dates_list.append(ts)

    # ── Periodknappar: avkastning och synligt intervall ──
    last_dt  = pd.Timestamp(close.index[-1])
    first_dt = pd.Timestamp(close.index[0])
    last_px  = float(close.iloc[-1])

    def _base(start):
        s_ = close[close.index <= start]
        return (pd.Timestamp(s_.index[-1]), float(s_.iloc[-1])) if len(s_) else (None, None)

    period_defs = [("1 m.", 1), ("3 m.", 3), ("6 m.", 6), ("i år", "ytd"),
                   ("1 år", 12), ("3 år", 36), ("5 år", 60), ("10 år", 120), ("Max", "max")]
    periods = []
    for lbl, m in period_defs:
        if m == "max":
            b_dt, b_px = first_dt, float(close.iloc[0])
        elif m == "ytd":
            b_dt, b_px = _base(pd.Timestamp(year=last_dt.year, month=1, day=1, tz=last_dt.tz) - pd.Timedelta(days=1))
            if b_dt is None:
                b_dt, b_px = first_dt, float(close.iloc[0])
        else:
            start = last_dt - pd.DateOffset(months=m)
            if start >= first_dt:
                b_dt, b_px = _base(start)
            elif start >= first_dt - pd.Timedelta(days=14):   # några dagars glapp i historiken räcker
                b_dt, b_px = first_dt, float(close.iloc[0])
            else:
                b_dt, b_px = None, None
        if b_dt is None or not b_px:
            periods.append({"lbl": lbl, "pct": None, "from": None})
        else:
            periods.append({"lbl": lbl, "pct": (last_px / b_px - 1) * 100,
                            "from": int(b_dt.timestamp())})

    default_lbl = tf_cfg.get("start", "1 år")
    if not any(p["lbl"] == default_lbl and p["from"] for p in periods):
        default_lbl = "Max"
    default_from = next(p["from"] for p in periods if p["lbl"] == default_lbl)

    period_btns_html = ""
    for p in periods:
        if p["from"] is None:
            period_btns_html += (f'<button class="pbtn" disabled title="För kort historik">'
                                 f'<span class="plbl">{p["lbl"]}</span><span class="ppct">–</span></button>')
        else:
            col = "#26a69a" if p["pct"] >= 0 else "#ef5350"
            act = " active" if p["lbl"] == default_lbl else ""
            pct_txt = f'{p["pct"]:+.2f}%'.replace(".", ",")
            period_btns_html += (f'<button class="pbtn{act}" data-from="{p["from"]}">'
                                 f'<span class="plbl">{p["lbl"]}</span>'
                                 f'<span class="ppct" style="color:{col}">{pct_txt}</span></button>')

    def series_to_json(series, n_bars=None):
        s = series.iloc[-(n_bars or n):]
        out = []
        for idx, val in s.items():
            if pd.isna(val): continue
            ts = int(pd.Timestamp(idx).timestamp())
            out.append({"time": ts, "value": round(float(val), 4)})
        return json.dumps(out)

    def hist_to_json(series):
        s = series.iloc[-n:]
        out = []
        for idx, val in s.items():
            if pd.isna(val): continue
            ts  = int(pd.Timestamp(idx).timestamp())
            col = "#26a69a" if float(val) >= 0 else "#ef5350"
            out.append({"time": ts, "value": round(float(val), 4), "color": col})
        return json.dumps(out)

    # Indikatorer
    rsi_json   = series_to_json(result["rsi"])
    macd_json  = series_to_json(result["macd"])
    sig_json   = series_to_json(result["macd_signal"])
    hist_json  = hist_to_json(result["macd_hist"])
    stoch_json = series_to_json(result["stoch"])
    obv_json   = series_to_json(result["obv"])
    ma20_json  = series_to_json(result["ma20"])
    ma50_json  = series_to_json(result["ma50"])
    ma200_json = series_to_json(result["ma200"])

    # ── Divergenspunkter & zoner ──────────────────────────
    # Markers: pilar + label på candlestick-grafen
    def div_markers(p1, p2, label, color_hex, close_arr):
        markers = []
        if p1 is None: return markers
        try:
            for px in [p1, p2]:
                ts = dates_list[px]
                markers.append({
                    "time": ts,
                    "position": "belowBar",
                    "color": color_hex,
                    "shape": "arrowUp",   # pil uppåt = divergens = potentiell vändning
                    "text": label,
                    "size": 1.2,
                })
        except Exception:
            pass
        return markers

    all_markers = []
    if result["RSI"]:        all_markers += div_markers(rp1, rp2, "RSI",   "#f0b429", close)
    if result["MACD"]:       all_markers += div_markers(mp1, mp2, "MACD",  "#2962ff", close)
    if result["Stochastic"]: all_markers += div_markers(sp1, sp2, "Stoch", "#9c27b0", close)
    if result["OBV"]:        all_markers += div_markers(op1, op2, "OBV",   "#26a69a", close)
    markers_json = json.dumps(sorted(all_markers, key=lambda x: x["time"]))

    # Divergenszon JS: vertikalt streck + skuggat band mellan de två bottnarna
    def div_zone_js(p1, p2, color_hex, label):
        if p1 is None or p2 is None: return ""
        try:
            ts1 = dates_list[p1]; ts2 = dates_list[p2]
            v1  = round(float(close.iloc[p1]), 4)
            v2  = round(float(close.iloc[p2]), 4)
            # Lägsta priset – zonen ritas under bottnarna
            low1 = round(float(result["df"].iloc[-n:]["Low"].iloc[p1]), 4)
            low2 = round(float(result["df"].iloc[-n:]["Low"].iloc[p2]), 4)
            return f"""
        // Divergenszon: {label}
        const divZone_{label} = mainChart.addLineSeries({{
            color: '{color_hex}',
            lineWidth: 2,
            lineStyle: 1,
            lastValueVisible: false,
            priceLineVisible: false,
            crosshairMarkerVisible: false,
            title: '',
        }});
        divZone_{label}.setData([
            {{time: {ts1}, value: {v1}}},
            {{time: {ts2}, value: {v2}}}
        ]);
        // Vertikala streck vid bottnarna
        const divV1_{label} = mainChart.addLineSeries({{
            color: '{color_hex}', lineWidth: 1, lineStyle: 3,
            lastValueVisible: false, priceLineVisible: false,
            crosshairMarkerVisible: false,
        }});
        divV1_{label}.setData([
            {{time: {ts1}, value: {low1 * 0.985}}},
            {{time: {ts1}, value: {v1}}}
        ]);
        const divV2_{label} = mainChart.addLineSeries({{
            color: '{color_hex}', lineWidth: 1, lineStyle: 3,
            lastValueVisible: false, priceLineVisible: false,
            crosshairMarkerVisible: false,
        }});
        divV2_{label}.setData([
            {{time: {ts2}, value: {low2 * 0.985}}},
            {{time: {ts2}, value: {v2}}}
        ]);
"""
        except Exception:
            return ""

    div_zones_js = ""
    if result["RSI"]:        div_zones_js += div_zone_js(rp1, rp2, "#f0b429", "RSI")
    if result["MACD"]:       div_zones_js += div_zone_js(mp1, mp2, "#2962ff", "MACD")
    if result["Stochastic"]: div_zones_js += div_zone_js(sp1, sp2, "#9c27b0", "Stoch")
    if result["OBV"]:        div_zones_js += div_zone_js(op1, op2, "#26a69a", "OBV")

    # Stöd/motstånd
    support_lines_js = ""
    if show_support:
        for lvl in result["supports"]:
            support_lines_js += f"""
            mainChart.addLineSeries({{
                color: '#26a69a', lineWidth: 1, lineStyle: 2, lastValueVisible: true,
                priceLineVisible: false, title: 'S {lvl:.1f}'
            }}).setData([
                {{time: {dates_list[0]}, value: {lvl}}},
                {{time: {dates_list[-1]}, value: {lvl}}}
            ]);"""
        for lvl in result["resistances"]:
            support_lines_js += f"""
            mainChart.addLineSeries({{
                color: '#ef5350', lineWidth: 1, lineStyle: 2, lastValueVisible: true,
                priceLineVisible: false, title: 'R {lvl:.1f}'
            }}).setData([
                {{time: {dates_list[0]}, value: {lvl}}},
                {{time: {dates_list[-1]}, value: {lvl}}}
            ]);"""

    # MA-linjer JS
    ma_js = ""
    if show_ma:
        ma_js = f"""
        const ma20Series = mainChart.addLineSeries({{color:'#f97316', lineWidth:1, lastValueVisible:true, priceLineVisible:false, title:'MA20'}});
        ma20Series.setData({ma20_json});
        const ma50Series = mainChart.addLineSeries({{color:'#9c27b0', lineWidth:1, lastValueVisible:true, priceLineVisible:false, title:'MA50'}});
        ma50Series.setData({ma50_json});
        const ma200Series = mainChart.addLineSeries({{color:'#ef5350', lineWidth:1, lastValueVisible:true, priceLineVisible:false, title:'MA200'}});
        ma200Series.setData({ma200_json});
        """

    # Indikator-panels JS
    ind_panels_js = ""
    sync_panels   = ""
    panel_count   = 1  # main=0, vol=always

    ind_configs = {
        "RSI":        ("RSI (14)", "#2962ff", "rsi"),
        "MACD":       ("MACD (12,26,9)", "#2962ff", "macd"),
        "Stochastic": ("Stoch (14,3)", "#9c27b0", "stoch"),
        "OBV":        ("OBV", "#26a69a", "obv"),
    }

    for ind_name in show_inds:
        pid = f"panel_{ind_name.lower()}"
        panel_count += 1
        ind_panels_js += f"""
        const {pid}El = document.createElement('div');
        {pid}El.style.cssText = 'width:100%;border-top:1px solid #2a2e39;position:relative;';
        container.appendChild({pid}El);
        const {pid}Label = document.createElement('div');
        {pid}Label.style.cssText = 'position:absolute;top:4px;left:8px;z-index:10;font-size:11px;color:#787b86;font-family:monospace;pointer-events:none;';
        {pid}Label.textContent = '{ind_configs[ind_name][0]}';
        {pid}El.appendChild({pid}Label);
        const {pid} = LightweightCharts.createChart({pid}El, {{
            ...chartOptions,
            height: 120,
            timeScale: {{ visible: false, minBarSpacing: 0.001 }},
        }});
        """

        if ind_name == "RSI":
            ind_panels_js += f"""
        const rsiSeries = {pid}.addLineSeries({{color:'#2962ff', lineWidth:1.5, lastValueVisible:true, priceLineVisible:false}});
        rsiSeries.setData({rsi_json});
        {pid}.addLineSeries({{color:'#787b86',lineWidth:1,lineStyle:2,lastValueVisible:false,priceLineVisible:false}})
            .setData([{{time:{dates_list[0]},value:70}},{{time:{dates_list[-1]},value:70}}]);
        {pid}.addLineSeries({{color:'#787b86',lineWidth:1,lineStyle:2,lastValueVisible:false,priceLineVisible:false}})
            .setData([{{time:{dates_list[0]},value:30}},{{time:{dates_list[-1]},value:30}}]);
        """
            if result["RSI"] and ri1 is not None:
                try:
                    t1 = dates_list[ri1]; t2 = dates_list[ri2]
                    v1 = round(float(result["rsi"].iloc[-n:].iloc[ri1]),4)
                    v2 = round(float(result["rsi"].iloc[-n:].iloc[ri2]),4)
                    ind_panels_js += f"""
        const rsiDivSeries = {pid}.addLineSeries({{color:'#f0b429',lineWidth:1.5,lineStyle:1,lastValueVisible:false,priceLineVisible:false}});
        rsiDivSeries.setData([{{time:{t1},value:{v1}}},{{time:{t2},value:{v2}}}]);
        """
                except Exception: pass

        elif ind_name == "MACD":
            ind_panels_js += f"""
        const macdHist = {pid}.addHistogramSeries({{lastValueVisible:false, priceLineVisible:false}});
        macdHist.setData({hist_json});
        const macdLine = {pid}.addLineSeries({{color:'#2962ff',lineWidth:1.5,lastValueVisible:true,priceLineVisible:false}});
        macdLine.setData({macd_json});
        const sigLine = {pid}.addLineSeries({{color:'#f97316',lineWidth:1,lineStyle:0,lastValueVisible:true,priceLineVisible:false}});
        sigLine.setData({sig_json});
        """
            if result["MACD"] and mi1 is not None:
                try:
                    t1 = dates_list[mi1]; t2 = dates_list[mi2]
                    v1 = round(float(result["macd"].iloc[-n:].iloc[mi1]),4)
                    v2 = round(float(result["macd"].iloc[-n:].iloc[mi2]),4)
                    ind_panels_js += f"""
        const macdDivSeries = {pid}.addLineSeries({{color:'#2962ff',lineWidth:1.5,lineStyle:1,lastValueVisible:false,priceLineVisible:false}});
        macdDivSeries.setData([{{time:{t1},value:{v1}}},{{time:{t2},value:{v2}}}]);
        """
                except Exception: pass

        elif ind_name == "Stochastic":
            ind_panels_js += f"""
        const stochSeries = {pid}.addLineSeries({{color:'#9c27b0',lineWidth:1.5,lastValueVisible:true,priceLineVisible:false}});
        stochSeries.setData({stoch_json});
        {pid}.addLineSeries({{color:'#787b86',lineWidth:1,lineStyle:2,lastValueVisible:false,priceLineVisible:false}})
            .setData([{{time:{dates_list[0]},value:80}},{{time:{dates_list[-1]},value:80}}]);
        {pid}.addLineSeries({{color:'#787b86',lineWidth:1,lineStyle:2,lastValueVisible:false,priceLineVisible:false}})
            .setData([{{time:{dates_list[0]},value:20}},{{time:{dates_list[-1]},value:20}}]);
        """
            if result["Stochastic"] and si1 is not None:
                try:
                    t1 = dates_list[si1]; t2 = dates_list[si2]
                    v1 = round(float(result["stoch"].iloc[-n:].iloc[si1]),4)
                    v2 = round(float(result["stoch"].iloc[-n:].iloc[si2]),4)
                    ind_panels_js += f"""
        const stochDivSeries = {pid}.addLineSeries({{color:'#9c27b0',lineWidth:1.5,lineStyle:1,lastValueVisible:false,priceLineVisible:false}});
        stochDivSeries.setData([{{time:{t1},value:{v1}}},{{time:{t2},value:{v2}}}]);
        """
                except Exception: pass

        elif ind_name == "OBV":
            ind_panels_js += f"""
        const obvSeries = {pid}.addAreaSeries({{lineColor:'#26a69a',topColor:'rgba(38,166,154,0.2)',bottomColor:'rgba(38,166,154,0)',lineWidth:1.5,lastValueVisible:true,priceLineVisible:false}});
        obvSeries.setData({obv_json});
        """
            if result["OBV"] and oi1 is not None:
                try:
                    t1 = dates_list[oi1]; t2 = dates_list[oi2]
                    v1 = round(float(result["obv"].iloc[-n:].iloc[oi1]),4)
                    v2 = round(float(result["obv"].iloc[-n:].iloc[oi2]),4)
                    ind_panels_js += f"""
        const obvDivSeries = {pid}.addLineSeries({{color:'#26a69a',lineWidth:1.5,lineStyle:1,lastValueVisible:false,priceLineVisible:false}});
        obvDivSeries.setData([{{time:{t1},value:{v1}}},{{time:{t2},value:{v2}}}]);
        """
                except Exception: pass

        sync_panels += f"{pid},"

    # Nyckeltal
    chg_color = "#26a69a" if result["week_chg"] >= 0 else "#ef5350"
    rsi_color = "#ef5350" if result["rsi_val"] < 30 else ("#f0b429" if result["rsi_val"] < 50 else "#26a69a")
    hits_color= "#26a69a" if result["hits"] >= 3 else "#f0b429" if result["hits"] >= 2 else "#787b86"
    support_txt = "  ".join([f"<span style='color:#26a69a'>S {v:.1f}</span>" for v in result["supports"]])
    resist_txt  = "  ".join([f"<span style='color:#ef5350'>R {v:.1f}</span>" for v in result["resistances"]])
    vol_badge = "🔥" if result["vol_high"] else ""

    # Räkna total panel-höjd
    main_h = 380
    vol_h  = 70
    ind_h  = 120 * len(show_inds)
    total_h = main_h + vol_h + ind_h + 10

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#131722; font-family:'DM Sans',sans-serif; color:#d1d4dc; }}

  .chart-header {{
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 14px 6px; border-bottom:1px solid #2a2e39; background:#1e222d;
  }}
  .chart-title {{ font-size:15px; font-weight:600; color:#d1d4dc; }}
  .chart-price {{ font-size:22px; font-weight:700; color:#d1d4dc; font-family:'DM Mono',monospace; margin-left:14px; }}
  .chart-chg   {{ font-size:13px; margin-left:8px; color:{chg_color}; font-family:'DM Mono',monospace; }}

  .stat-bar {{
    display:flex; gap:20px; padding:6px 14px; background:#1e222d;
    border-bottom:1px solid #2a2e39; flex-wrap:wrap;
  }}
  .stat-item {{ display:flex; flex-direction:column; }}
  .stat-label {{ font-size:9px; color:#787b86; text-transform:uppercase; letter-spacing:.08em; }}
  .stat-value {{ font-size:12px; font-family:'DM Mono',monospace; margin-top:1px; }}

  .div-badges {{
    display:flex; gap:6px; padding:5px 14px; background:#1e222d;
    border-bottom:1px solid #2a2e39; flex-wrap:wrap; align-items:center;
  }}
  .div-badge {{
    font-size:10px; padding:2px 8px; border-radius:3px;
    font-family:'DM Mono',monospace; font-weight:600;
  }}
  .div-rsi   {{ background:rgba(240,180,41,0.15);  color:#f0b429; border:1px solid rgba(240,180,41,0.3); }}
  .div-macd  {{ background:rgba(41,98,255,0.15);   color:#5b9cf6; border:1px solid rgba(41,98,255,0.3); }}
  .div-stoch {{ background:rgba(156,39,176,0.15);  color:#ce93d8; border:1px solid rgba(156,39,176,0.3); }}
  .div-obv   {{ background:rgba(38,166,154,0.15);  color:#26a69a; border:1px solid rgba(38,166,154,0.3); }}
  .no-div    {{ font-size:11px; color:#787b86; }}

  .period-bar {{
    display:flex; background:#1e222d; border-bottom:1px solid #2a2e39; overflow-x:auto;
  }}
  .pbtn {{
    flex:1 0 auto; min-width:64px; background:none; border:none;
    border-bottom:2px solid transparent; color:#d1d4dc; padding:6px 8px 5px;
    cursor:pointer; display:flex; flex-direction:column; align-items:center; gap:1px;
    font-family:'DM Sans',sans-serif;
  }}
  .pbtn:hover:not(:disabled) {{ background:#2a2e39; }}
  .pbtn.active {{ border-bottom-color:#26a69a; }}
  .pbtn.active .plbl {{ font-weight:700; }}
  .pbtn:disabled {{ opacity:.35; cursor:default; }}
  .plbl {{ font-size:12px; }}
  .ppct {{ font-size:11px; font-family:'DM Mono',monospace; }}

  .support-bar {{
    padding:4px 14px; background:#131722; border-bottom:1px solid #2a2e39;
    font-size:11px; font-family:'DM Mono',monospace; display:flex; gap:14px;
  }}

  #container {{ width:100%; background:#131722; }}

  .tv-panel-label {{
    position:absolute; top:4px; left:8px; z-index:10;
    font-size:11px; color:#787b86; font-family:monospace; pointer-events:none;
  }}
</style>
</head>
<body>

<!-- Header -->
<div class="chart-header">
  <div style="display:flex;align-items:baseline;">
    <span class="chart-title">{ticker_name}</span>
    <span class="chart-price">{result["price"]:.2f}</span>
    <span class="chart-chg">{result["week_chg"]:+.2f}%&nbsp;({tf_cfg["chg_lbl"]})</span>
  </div>
  <div style="font-size:11px;color:#787b86;">{tf_cfg["name"]} · Divergensanalys</div>
</div>

<!-- Nyckeltal -->
<div class="stat-bar">
  <div class="stat-item">
    <span class="stat-label">1 mån</span>
    <span class="stat-value" style="color:{'#26a69a' if result['month_chg']>=0 else '#ef5350'}">{result['month_chg']:+.1f}%</span>
  </div>
  <div class="stat-item">
    <span class="stat-label">RSI (14)</span>
    <span class="stat-value" style="color:{rsi_color}">{result['rsi_val']:.1f}</span>
  </div>
  <div class="stat-item">
    <span class="stat-label">Divergenser</span>
    <span class="stat-value" style="color:{hits_color}">{result['hits']}/4</span>
  </div>
  <div class="stat-item">
    <span class="stat-label">Volym</span>
    <span class="stat-value" style="color:{'#f97316' if result['vol_high'] else '#d1d4dc'}">{vol_badge} {f"{result['vol_ratio']:.1f}x" if result['vol_ratio'] else '–'}</span>
  </div>
  <div class="stat-item">
    <span class="stat-label">Stöd</span>
    <span class="stat-value">{support_txt if support_txt else '–'}</span>
  </div>
  <div class="stat-item">
    <span class="stat-label">Motstånd</span>
    <span class="stat-value">{resist_txt if resist_txt else '–'}</span>
  </div>
</div>

<!-- Divergensbadges -->
<div class="div-badges">
  <span style="font-size:10px;color:#787b86;margin-right:4px;">DIVERGENSER:</span>
  {'<span class="div-badge div-rsi">↗ RSI</span>' if result["RSI"] else ''}
  {'<span class="div-badge div-macd">↗ MACD</span>' if result["MACD"] else ''}
  {'<span class="div-badge div-stoch">↗ Stochastic</span>' if result["Stochastic"] else ''}
  {'<span class="div-badge div-obv">↗ OBV</span>' if result["OBV"] else ''}
  {'<span class="no-div">Inga aktiva divergenser</span>' if result["hits"] == 0 else ''}
</div>

<!-- Periodknappar -->
<div class="period-bar">{period_btns_html}</div>

<!-- Diagrammet -->
<div id="container"></div>

<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<script>
const container = document.getElementById('container');

const chartOptions = {{
  layout: {{
    background: {{ color: '#131722' }},
    textColor: '#787b86',
    fontFamily: 'DM Sans, sans-serif',
    fontSize: 11,
  }},
  grid: {{
    vertLines: {{ color: '#1e222d' }},
    horzLines: {{ color: '#1e222d' }},
  }},
  crosshair: {{
    mode: LightweightCharts.CrosshairMode.Normal,
    vertLine: {{ color: '#758696', width: 1, style: 3, labelBackgroundColor: '#2a2e39' }},
    horzLine: {{ color: '#758696', width: 1, style: 3, labelBackgroundColor: '#2a2e39' }},
  }},
  rightPriceScale: {{
    borderColor: '#2a2e39',
    textColor: '#787b86',
  }},
  timeScale: {{
    borderColor: '#2a2e39',
    timeVisible: true,
    secondsVisible: false,
    fixLeftEdge: true,
    minBarSpacing: 0.001,
  }},
  handleScroll: false,
  handleScale:  false,
}};

// ── Huvudpanel: Candlestick ──
const mainEl = document.createElement('div');
mainEl.style.cssText = 'width:100%;position:relative;';
container.appendChild(mainEl);

const mainChart = LightweightCharts.createChart(mainEl, {{
  ...chartOptions,
  height: {main_h},
}});

const candleSeries = mainChart.addCandlestickSeries({{
  upColor: '#26a69a', downColor: '#ef5350',
  borderUpColor: '#26a69a', borderDownColor: '#ef5350',
  wickUpColor: '#26a69a', wickDownColor: '#ef5350',
}});
candleSeries.setData({json.dumps(candle_data)});
candleSeries.setMarkers({markers_json});

{div_zones_js}
{ma_js}
{support_lines_js}

// ── Volympanel ──
const volEl = document.createElement('div');
volEl.style.cssText = 'width:100%;border-top:1px solid #2a2e39;position:relative;';
container.appendChild(volEl);
const volLabel = document.createElement('div');
volLabel.className = 'tv-panel-label';
volLabel.textContent = 'Volym';
volEl.appendChild(volLabel);
const volChart = LightweightCharts.createChart(volEl, {{
  ...chartOptions,
  height: {vol_h},
  timeScale: {{ visible: false, minBarSpacing: 0.001 }},
}});
const volSeries = volChart.addHistogramSeries({{
  priceFormat: {{ type: 'volume' }},
  priceScaleId: '',
  lastValueVisible: false, priceLineVisible: false,
}});
volSeries.priceScale().applyOptions({{ scaleMargins: {{ top: 0.1, bottom: 0 }} }});
volSeries.setData({json.dumps(vol_data)});

// ── Indikatorpaneler ──
{ind_panels_js}

// ── Synkronisera tidsaxlar ──
const allCharts = [mainChart, volChart, {sync_panels}].filter(Boolean);
allCharts.forEach(chart => {{
  chart.timeScale().subscribeVisibleLogicalRangeChange(range => {{
    if (range === null) return;
    allCharts.forEach(other => {{
      if (other !== chart) other.timeScale().setVisibleLogicalRange(range);
    }});
  }});
}});

// ── Periodknappar styr det synliga intervallet ──
const lastTime = {dates_list[-1]};
function showFrom(from) {{
  mainChart.timeScale().setVisibleRange({{ from: from, to: lastTime }});
}}
document.querySelectorAll('.pbtn[data-from]').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.pbtn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    showFrom(parseInt(btn.dataset.from, 10));
  }});
}});
showFrom({default_from});
</script>
</body>
</html>
"""
    return html


# Tyska regionalbörser listar nästan alla stora bolag en gång till – de döljs
# när bolaget har en huvudnotering på annat håll.
SECONDARY_EXCHANGES = {"MUN", "FRA", "DUS", "STU", "BER", "HAM", "HAN", "EBS", "VIE", "IOB", "MEX", "BUE"}
EXCHANGE_NAMES = {
    "STO": "Stockholm", "HEL": "Helsingfors", "CPH": "Köpenhamn", "OSL": "Oslo",
    "NMS": "Nasdaq", "NGM": "Nasdaq", "NCM": "Nasdaq", "NYQ": "NYSE", "ASE": "NYSE American",
    "PCX": "NYSE Arca", "BTS": "Cboe", "LSE": "London", "GER": "Xetra", "PAR": "Paris",
    "AMS": "Amsterdam", "MIL": "Milano", "MCE": "Madrid", "TOR": "Toronto", "CCC": "Krypto",
    "CCY": "Valuta", "NGS": "Nordic Growth Market", "SPT": "Spotlight",
}

def _name_key(namn):
    k = namn.lower()
    for w in ["(publ)", " publ", " ab", " asa", " oyj", " a/s", " inc.", " inc", " plc", " corp.", ",", "."]:
        k = k.replace(w, "")
    return " ".join(k.split())

def search_tickers(query):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=sv-SE&region=SE&quotesCount=15&newsCount=0"
        resp = req.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        raw = []
        for q in resp.json().get("quotes", []):
            if q.get("quoteType") in ("EQUITY", "ETF", "MUTUALFUND", "CRYPTOCURRENCY", "CURRENCY", "FUTURE", "INDEX"):
                raw.append({
                    "namn":   q.get("longname") or q.get("shortname", ""),
                    "ticker": q.get("symbol", ""),
                    "kod":    q.get("exchange", ""),
                })
        # Ett förslag per bolag: huvudnoteringen före tyska regionalbörser
        best = {}
        for r in raw:
            key = _name_key(r["namn"]) or r["ticker"]
            secondary = r["kod"] in SECONDARY_EXCHANGES
            if key not in best or (best[key]["_sec"] and not secondary):
                best[key] = {**r, "_sec": secondary}
        results = []
        for r in best.values():
            results.append({"namn": r["namn"], "ticker": r["ticker"],
                            "börs": EXCHANGE_NAMES.get(r["kod"], r["kod"])})
        return results[:6]
    except Exception:
        return []


# ─────────────────────────────────────────────
# ALERTSYSTEM
# ─────────────────────────────────────────────

def load_sent_alerts():
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE) as f: return json.load(f)
    return {}

def save_sent_alerts(data):
    with open(ALERTS_FILE, "w") as f: json.dump(data, f)

def send_email_alert(subject, body, smtp_user, smtp_pass):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject; msg["From"] = smtp_user; msg["To"] = smtp_user
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, smtp_user, msg.as_string())
        return True
    except Exception as e:
        return str(e)

def check_and_send_alerts(results, smtp_user, smtp_pass, min_hits=2):
    sent  = load_sent_alerts()
    today = datetime.now().strftime("%Y-%m-%d")
    new_alerts = []
    for r in results:
        if r["hits"] < min_hits: continue
        key = f"{r['ticker_yf']}_{today}"
        if key not in sent:
            new_alerts.append(r); sent[key] = True
    if new_alerts:
        rows = "".join([
            f"<tr><td style='padding:8px;color:#5b9cf6;font-family:monospace'>{r['ticker_yf']}</td>"
            f"<td style='padding:8px'>{r.get('name','')}</td>"
            f"<td style='padding:8px;font-family:monospace'>{r['price']:.2f}</td>"
            f"<td style='padding:8px;color:{'#26a69a' if r['week_chg']>=0 else '#ef5350'};font-family:monospace'>{r['week_chg']:+.1f}%</td>"
            f"<td style='padding:8px;color:#26a69a;font-weight:bold'>{r['hits']}/4</td></tr>"
            for r in new_alerts
        ])
        body = f"""<div style='background:#131722;padding:24px;font-family:sans-serif;color:#d1d4dc'>
          <h2 style='color:#5b9cf6'>📈 Divergens Dashboard – Nya signaler {today}</h2>
          <table style='border-collapse:collapse;width:100%;background:#1e222d;margin-top:16px'>
            <thead><tr style='background:#2a2e39'>
              <th style='padding:10px;color:#787b86;text-align:left'>Ticker</th>
              <th style='padding:10px;color:#787b86;text-align:left'>Bolag</th>
              <th style='padding:10px;color:#787b86;text-align:left'>Kurs</th>
              <th style='padding:10px;color:#787b86;text-align:left'>1v %</th>
              <th style='padding:10px;color:#787b86;text-align:left'>Träffar</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
          <p style='color:#787b86;font-size:12px;margin-top:16px'>Divergenser är inte köpsignaler – kombinera med stöd, volym & fundamenta.</p>
        </div>"""
        result = send_email_alert(f"📈 {len(new_alerts)} nya divergenssignaler – {today}", body, smtp_user, smtp_pass)
        save_sent_alerts(sent)
        return new_alerts, result
    return [], None


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📈 Divergens Dashboard")
    st.markdown('<div class="section-header">Diagraminställningar</div>', unsafe_allow_html=True)

    tf              = st.radio("Tidsram", list(TIMEFRAMES.keys()), index=1, horizontal=True)
    show_inds_sel   = st.multiselect("Indikatorer", ["RSI","MACD","Stochastic","OBV"],
                                      default=["RSI","MACD"])
    show_ma         = st.toggle("MA20 / MA50 / MA200", value=True)
    show_support    = st.toggle("Stöd & motstånd", value=True)
    show_rs         = st.toggle("Relativ styrka", value=False)
    chart_height    = st.slider("Diagramhöjd (px)", 500, 1000, 700, step=50)

    st.markdown('<div class="section-header">Screener – Datakälla</div>', unsafe_allow_html=True)
    min_hits = st.slider("Minsta antal indikatorer", 1, 4, 1)
    källa    = st.radio("Analysera", [
        "Börsindex / lista", "Bevakningslista"
    ], index=0)

    custom_tickers = ""; selected_index = None
    if källa == "Börsindex / lista":
        selected_index = st.selectbox("Välj index eller lista", list(INDEX_LISTS.keys()))
        n_idx = len(INDEX_LISTS[selected_index])
        st.markdown(f'<div style="color:#787b86;font-size:0.72rem;">{n_idx} instrument</div>', unsafe_allow_html=True)
    elif källa == "Bevakningslista":
        custom_tickers = st.text_area("Tickers (en per rad)", value="ERIC-B.ST\nVOLV-B.ST\nAAPL", height=110)

    # Webbversionen: e-postalerts är avstängda, så att besökare aldrig skriver in lösenord här
    alerts_on = False; smtp_user = ""; smtp_pass = ""; alert_min = 2

    st.markdown('<div class="section-header">Åtgärder</div>', unsafe_allow_html=True)
    run_btn   = st.button("🔍  Kör screener", use_container_width=True)
    clear_btn = st.button("🗑  Rensa cache",  use_container_width=True)
    if clear_btn:
        st.cache_data.clear(); st.success("Cache rensad!")

    st.markdown("---")
    st.markdown(f'<div style="color:#787b86;font-size:0.68rem;">Uppdaterad: {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>', unsafe_allow_html=True)


# Läge: "search" visar bara det sökta bolaget, "screener" visar screenern
if "mode" not in st.session_state:
    st.session_state["mode"] = "start"
if run_btn:
    st.session_state["mode"] = "screener"
    st.session_state.pop("shown_ticker", None)
    st.session_state["search_box"] = ""

# ─────────────────────────────────────────────
# HUVUDINNEHÅLL
# ─────────────────────────────────────────────

st.markdown("# 📈 Divergens Dashboard")
st.markdown('<div style="color:#787b86;margin-bottom:20px;font-size:0.85rem;">Dag · Vecka · Månad · RSI · MACD · Stochastic · OBV · Stöd/Motstånd · MA · Volym</div>', unsafe_allow_html=True)

# ── Snabbsökning ─────────────────────────────────────────
st.markdown('<div class="section-header">Snabbsökning</div>', unsafe_allow_html=True)

sc1, sc2 = st.columns([4, 1])
with sc1:
    search_input = st.text_input("Sök", placeholder="Bolagsnamn eller ticker – t.ex. 'Volvo', 'Bitcoin', 'H&M', 'AAPL'",
                                  label_visibility="collapsed", key="search_box")
with sc2:
    search_btn = st.button("🔍  Sök", use_container_width=True)

if search_input.strip() and len(search_input.strip()) >= 2:
    sr = search_tickers(search_input.strip())
    if sr:
        options  = [f"{r['namn']}  —  {r['ticker']}  ({r['börs']})" for r in sr]
        opt_map  = {o: r["ticker"] for o, r in zip(options, sr)}
        name_map = {r["ticker"]: r["namn"] for r in sr}
        sel_opt  = st.radio("Sökresultat", options, label_visibility="collapsed", key="sr_radio")
        t_search = opt_map.get(sel_opt, "")

        if st.button(f"📊  Visa diagram  {t_search}", key="analyze_btn"):
            st.session_state["shown_ticker"] = t_search
            st.session_state["mode"] = "search"
        if st.session_state.get("mode") == "search" and st.session_state.get("shown_ticker") == t_search:
            with st.spinner(f"Hämtar {t_search}..."):
                r = fetch_and_analyze(t_search, tf, full=True)
                bench = fetch_benchmark("^OMX", tf) if show_rs else None

            if r is None:
                st.error(f"❌ Kunde inte hämta data för {t_search}")
            else:
                r["ticker_yf"] = t_search
                r["name"]      = name_map.get(t_search, t_search)
                rs_val = calc_rs(r["close"], bench) if bench is not None else None

                html = build_chart_html(r, f"{r['name']} ({t_search})",
                                         show_inds_sel, show_support, show_ma,
                                         benchmark_close=bench if show_rs else None,
                                         height=chart_height)
                components.html(html, height=chart_height + 240, scrolling=False)
                if st.button("✖  Stäng diagram", key="close_search"):
                    st.session_state["mode"] = "start"
                    st.session_state.pop("shown_ticker", None)
                    st.rerun()
    elif search_btn:
        st.warning("Inga bolag hittades.")

st.markdown("---")

# I sökläge visas bara det sökta bolaget – inga andra grafer
if st.session_state.get("mode") != "screener":
    if st.session_state.get("mode") == "start":
        st.info("Sök upp ett bolag ovan, eller klicka **Kör screener** i menyn till vänster för att skanna en hel lista.")
    st.stop()

# ── Divergensanalys / Screener ────────────────────────────
lbl = f"Screener – {selected_index}" if källa == "Börsindex / lista" and selected_index else "Screener"
st.markdown(f'<div class="section-header">{lbl}</div>', unsafe_allow_html=True)

if källa == "Börsindex / lista" and selected_index:
    analyze_list  = [(TICKER_NAMES.get(t, t), t) for t in INDEX_LISTS[selected_index]]
    benchmark_key = selected_index
else:
    lines         = [t.strip() for t in custom_tickers.splitlines() if t.strip() and not t.startswith("#")]
    analyze_list  = [(t, t) for t in lines]
    benchmark_key = "Bevakningslista"

bench_ticker    = RS_BENCHMARKS.get(benchmark_key, "^OMX")
benchmark_close = fetch_benchmark(bench_ticker, tf) if show_rs else None

if run_btn or "analysis_results" not in st.session_state or st.session_state.get("tf_used") != tf:
    st.session_state["tf_used"] = tf
    results = []
    prog = st.progress(0, text="Analyserar...")
    for i, (name, ticker_yf) in enumerate(analyze_list):
        prog.progress((i+1)/len(analyze_list), text=f"Analyserar {name}...")
        r = fetch_and_analyze(ticker_yf, tf)
        if r and r["hits"] >= min_hits:
            r["name"] = name; r["ticker_yf"] = ticker_yf
            r["rs"]   = calc_rs(r["close"], benchmark_close) if benchmark_close is not None else None
            results.append(r)
    prog.empty()
    results.sort(key=lambda x: (-x["hits"], x["rsi_val"]))
    st.session_state["analysis_results"] = results

    if alerts_on and smtp_user and smtp_pass and results:
        new_al, mail_res = check_and_send_alerts(results, smtp_user, smtp_pass, alert_min)
        if new_al and mail_res is True:
            st.toast(f"📧 Alert skickat – {len(new_al)} signaler", icon="✅")
        elif new_al and mail_res is not True:
            st.warning(f"Alert misslyckades: {mail_res}")

results = st.session_state.get("analysis_results", [])

if not results:
    st.info("Inga divergenser hittades. Kör screener eller sänk 'Minsta antal indikatorer'.")
else:
    # Resultatkort
    cols = st.columns(min(len(results), 4))
    for i, r in enumerate(results[:8]):
        with cols[i % 4]:
            hc = "hit-strong" if r["hits"]>=3 else ("hit-medium" if r["hits"]>=2 else "hit-weak")
            wc = "#26a69a" if r["week_chg"]>=0 else "#ef5350"
            rs_str = f"RS {r['rs']:+.1f}%" if r.get("rs") is not None else ""
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">{r['name']}</div>
              <div class="metric-value">{r['price']:.2f}</div>
              <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
                <span class="hit-badge {hc}">{r['hits']}/4</span>
                <span style="color:{wc};font-family:monospace;font-size:0.82rem;">{r['week_chg']:+.1f}%</span>
                <span style="color:#787b86;font-size:0.78rem;">RSI {r['rsi_val']:.0f}</span>
                {'<span style="color:#26a69a;font-size:0.78rem;">🔥</span>' if r['vol_high'] else ''}
              </div>
              <div style="margin-top:6px;font-size:0.7rem;color:#787b86;">
                {'✔ RSI ' if r['RSI'] else ''}{'✔ MACD ' if r['MACD'] else ''}{'✔ Stoch ' if r['Stochastic'] else ''}{'✔ OBV' if r['OBV'] else ''}
              </div>
            </div>""", unsafe_allow_html=True)

    # Välj aktie att visa diagram
    st.markdown('<div class="section-header">Diagram</div>', unsafe_allow_html=True)
    res_names = [r["name"] for r in results]
    sel_name  = st.selectbox("Välj aktie", res_names, key="res_sel")
    sel_r     = next((r for r in results if r["name"] == sel_name), None)

    if sel_r:
        html = build_chart_html(sel_r, f"{sel_name} ({sel_r['ticker_yf']})",
                                 show_inds_sel, show_support, show_ma,
                                 benchmark_close=benchmark_close if show_rs else None,
                                 height=chart_height)
        components.html(html, height=chart_height + 240, scrolling=False)

    # Tabell
    st.markdown('<div class="section-header">Alla träffar</div>', unsafe_allow_html=True)
    rows = [{"Bolag": r["name"], "Ticker": r["ticker_yf"], "Pris": r["price"],
             f"{TIMEFRAMES[tf]['chg_lbl']} %": r["week_chg"], "RSI": r["rsi_val"],
             "Rel styrka": f"{r['rs']:+.1f}%" if r.get("rs") else "–",
             "Volym": "🔥" if r["vol_high"] else "–",
             "RSI div": "✔" if r["RSI"] else "–",
             "MACD div": "✔" if r["MACD"] else "–",
             "Stoch div": "✔" if r["Stochastic"] else "–",
             "OBV div": "✔" if r["OBV"] else "–",
             "Träffar": f"{r['hits']}/4"} for r in results]
    df_res = pd.DataFrame(rows)
    st.dataframe(df_res, use_container_width=True, hide_index=True)
    st.download_button("⬇  Exportera CSV",
                       df_res.to_csv(index=False).encode("utf-8"),
                       "divergenser.csv", "text/csv")
