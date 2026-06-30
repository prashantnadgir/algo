"""
╔══════════════════════════════════════════════════════════════╗
║       Nifty 50 — SMC Demand Zone Scanner (Daily Runner)      ║
║  Scans all 50 Nifty stocks for weekly SMC buying zones       ║
║  Logic mirrors LuxAlgo Smart Money Concepts blue band        ║
╠══════════════════════════════════════════════════════════════╣
║  INSTALL (one time):                                         ║
║    pip install yfinance pandas numpy colorama tabulate       ║
║                                                              ║
║  RUN DAILY:                                                  ║
║    python nifty50_smc_scanner.py                             ║
║                                                              ║
║  OPTIONAL — auto-run every morning on Windows:               ║
║    Task Scheduler → run at 9:30 AM on weekdays               ║
║  OPTIONAL — auto-run on Mac/Linux:                           ║
║    crontab: 30 9 * * 1-5 python /path/to/this/script.py      ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import ssl
import urllib3
import requests

# ── SSL bypass for corporate networks with custom CA (e.g. Eurofins proxy) ───
# Set env vars so curl_cffi (used by yfinance) skips certificate verification
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["SSL_CERT_FILE"] = ""

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests.Session (fallback path)
_orig_request = requests.Session.request
def _no_verify_request(self, method, url, **kwargs):
    kwargs.setdefault("verify", False)
    return _orig_request(self, method, url, **kwargs)
requests.Session.request = _no_verify_request

# Patch curl_cffi.requests.Session (primary path used by yfinance ≥ 0.2)
try:
    import curl_cffi.requests as _curl_req
    _orig_curl_request = _curl_req.Session.request
    def _curl_no_verify(self, method, url, **kwargs):
        kwargs.setdefault("verify", False)
        return _orig_curl_request(self, method, url, **kwargs)
    _curl_req.Session.request = _curl_no_verify
except ImportError:
    pass
# ─────────────────────────────────────────────────────────────────────────────

import yfinance as yf
import time
import pandas as pd
import numpy as np
from tabulate import tabulate
from colorama import init, Fore, Back, Style
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

init(autoreset=True)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SWING_LOOKBACK  = 10       # bars each side to confirm a pivot low
ZONE_BUFFER_PCT = 2.0      # % buffer around swing low to define the zone
NEAR_ZONE_PCT   = 3.0      # % above zone top = "Near Zone" warning
TIMEFRAME       = "15m"    # "1wk" = weekly (recommended), "1d" = daily
HISTORY_PERIOD  = "7d"      # Yahoo limits 15m data to last 60 days max; 7d is safe
SAVE_CSV        = True     # save results to CSV file

# BOS + FVG + Liquidity Sweep strategy settings
FVG_RETEST_TOLERANCE_PCT = 0.3   # % tolerance around FVG zone to count as a retest

# ─── FULL NIFTY 500 SYMBOLS (Yahoo Finance format) ────────────────────────────
NIFTY500 = [
    "RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","TCS.NS",
    "BHARTIARTL.NS","SBIN.NS","HINDUNILVR.NS","BAJFINANCE.NS","ITC.NS",
    "KOTAKBANK.NS","LT.NS","HCLTECH.NS","MARUTI.NS","AXISBANK.NS",
    "ASIANPAINT.NS","WIPRO.NS","ULTRACEMCO.NS","TITAN.NS","ONGC.NS",
    "SUNPHARMA.NS","NTPC.NS","TMCV.NS","POWERGRID.NS","TATASTEEL.NS",
    "ADANIENT.NS","BAJAJFINSV.NS","JSWSTEEL.NS","COALINDIA.NS","DRREDDY.NS",
    "CIPLA.NS","HINDALCO.NS","GRASIM.NS","INDUSINDBK.NS","HEROMOTOCO.NS",
    "DIVISLAB.NS","TECHM.NS","BRITANNIA.NS","BPCL.NS","EICHERMOT.NS",
    "APOLLOHOSP.NS","NESTLEIND.NS","TATACONSUM.NS","ADANIPORTS.NS",
    "BAJAJ-AUTO.NS","SHRIRAMFIN.NS","BEL.NS","TRENT.NS","SBILIFE.NS",
    "HDFCLIFE.NS","HAVELLS.NS","DABUR.NS","MARICO.NS","BERGEPAINT.NS",
    "GODREJCP.NS","COLPAL.NS","PIDILITIND.NS","MUTHOOTFIN.NS",
    "HDFCAMC.NS","ICICIPRULI.NS","ICICIGI.NS","SBICARD.NS","CHOLAFIN.NS",
    "M&M.NS","TATAPOWER.NS","NAUKRI.NS","DMART.NS",
    "IRCTC.NS","IRFC.NS","RECLTD.NS","PFC.NS","HUDCO.NS",
    "HAL.NS","BDL.NS","BEML.NS","BHEL.NS","SAIL.NS",
    "NMDC.NS","MOIL.NS","NATIONALUM.NS","VEDL.NS","HINDCOPPER.NS",
    "APLAPOLLO.NS","JINDALSTEL.NS","WELSPUNLIV.NS","TRIDENT.NS","PAGEIND.NS",
    "ABFRL.NS","RADICO.NS","UBL.NS","INDIGO.NS",
    "BLUEDART.NS","CONCOR.NS","DELHIVERY.NS","ZYDUSLIFE.NS","TORNTPHARM.NS",
    "ALKEM.NS","LUPIN.NS","AUROPHARMA.NS","IPCALAB.NS","GLENMARK.NS",
    "NATCOPHARM.NS","LAURUSLABS.NS","GRANULES.NS","ABBOTINDIA.NS","PFIZER.NS",
    "AJANTPHARM.NS","JBCHEPHARM.NS","FORTIS.NS","MAXHEALTH.NS","METROPOLIS.NS",
    "BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","AUBANK.NS",
    "RBLBANK.NS","KARURVYSYA.NS","EQUITASBNK.NS","UJJIVANSFB.NS",
    "CANFINHOME.NS","AAVAS.NS","HOMEFIRST.NS","MANAPPURAM.NS","IIFL.NS",
    "POONAWALLA.NS","CREDITACC.NS","TATAELXSI.NS","PERSISTENT.NS","COFORGE.NS",
    "MPHASIS.NS","LTTS.NS","KPITTECH.NS","CYIENT.NS","BSOFT.NS",
    "SONACOMS.NS","TANLA.NS","INTELLECT.NS","ZENSARTECH.NS","MASTEK.NS",
    "POLYCAB.NS","ATUL.NS","DEEPAKNTR.NS","NAVINFLUOR.NS","TATACHEM.NS","GNFC.NS",
    "COROMANDEL.NS","CHAMBLFERT.NS","SIEMENS.NS","ABB.NS","CGPOWER.NS",
    "INOXWIND.NS","SUZLON.NS","AMBER.NS","BLUESTARCO.NS","VOLTAS.NS",
    "CROMPTON.NS","DIXON.NS","VGUARD.NS","SYMPHONY.NS","TTKPRESTIG.NS",
    "RELAXO.NS","JUSTDIAL.NS","GREENPANEL.NS","CENTURYPLY.NS",
    "TVSMOTOR.NS","TITAGARH.NS","IRCON.NS","RITES.NS","NBCC.NS",
    "NCC.NS","PNCINFRA.NS","KNRCON.NS","CAPACITE.NS","HGINFRA.NS",
    "ADANIPOWER.NS","TORNTPOWER.NS","CESC.NS","TATACOMM.NS","RAILTEL.NS",
    "HFCL.NS","STLTECH.NS","REDINGTON.NS","INDHOTEL.NS","LEMONTREE.NS",
    "CHALET.NS","THOMASCOOK.NS","KALYANKJIL.NS",
    "RAJESHEXPO.NS","SENCO.NS","GOLDIAM.NS","CAMPUS.NS",
    "BATAINDIA.NS","NUVOCO.NS","JKCEMENT.NS","RAMCOCEM.NS","ORIENTCEM.NS",
    "HEIDELBERG.NS","SUNTV.NS","ZEEL.NS","PVRINOX.NS","SAREGAMA.NS",
    "NETWORK18.NS","PCBL.NS","GALAXYSURF.NS","ALKYLAMINE.NS","KRBL.NS",
    "LTFOODS.NS","AVANTIFEED.NS","GRAPHITE.NS","HEG.NS",
    "CAMS.NS","CDSL.NS","BSE.NS","MCX.NS","ANGELONE.NS","MOTILALOFS.NS",
    "KFINTECH.NS","CIEINDIA.NS","SUPRAJIT.NS","CYIENTDLM.NS","IDEAFORGE.NS","DCMSRIND.NS",
    "PIDILITIND.NS","SRF.NS","HSCL.NS","VINATIORGA.NS","VISHNU.NS","BODALCHEM.NS","NEOGEN.NS","CHEMCON.NS",
]

# ─── SMC LOGIC ───────────────────────────────────────────────────────────────

def find_pivot_lows(low_series: pd.Series, n: int) -> pd.Series:
    """
    Returns a Series where non-NaN values are confirmed pivot lows.
    A pivot low at index i means low[i] is the lowest of n bars on each side.
    """
    pivots = pd.Series(np.nan, index=low_series.index)
    lows = low_series.values
    for i in range(n, len(lows) - n):
        window = lows[i - n: i + n + 1]
        if lows[i] == np.min(window):
            pivots.iloc[i] = lows[i]
    return pivots


def get_last_pivot_low(low_series: pd.Series, n: int) -> float:
    """Returns the most recent confirmed pivot low value."""
    pivots = find_pivot_lows(low_series, n)
    valid  = pivots.dropna()
    return float(valid.iloc[-1]) if len(valid) > 0 else np.nan


def is_impulsive_candle(open_val, close_val, high_val, low_val,
                         min_body_ratio=0.6, min_move_pct=0.5) -> bool:
    """
    True if the candle is a strong bullish candle:
    - Body is > 60% of the full range
    - Close is > 0.5% above open
    """
    rng  = high_val - low_val
    body = abs(close_val - open_val)
    if rng == 0:
        return False
    return (close_val > open_val and
            body / rng > min_body_ratio and
            (close_val - open_val) / open_val * 100 > min_move_pct)


def check_bos(close_series: pd.Series, pivot_highs: pd.Series) -> bool:
    """
    Bullish BOS: latest close just crossed above the last confirmed swing high.
    """
    valid_highs = pivot_highs.dropna()
    if len(valid_highs) == 0:
        return False
    last_sh = float(valid_highs.iloc[-1])
    if len(close_series) < 2:
        return False
    return close_series.iloc[-1] > last_sh and close_series.iloc[-2] <= last_sh


def find_pivot_highs(high_series: pd.Series, n: int) -> pd.Series:
    pivots = pd.Series(np.nan, index=high_series.index)
    highs  = high_series.values
    for i in range(n, len(highs) - n):
        window = highs[i - n: i + n + 1]
        if highs[i] == np.max(window):
            pivots.iloc[i] = highs[i]
    return pivots


# ─── BOS + FVG + LIQUIDITY SWEEP STRATEGY ────────────────────────────────────
# Setup flow (per attached strategy image):
#   1. Liquidity Sweep — price wicks below a recent swing low (stop hunt)
#   2. BOS             — price then breaks above the most recent swing high
#   3. FVG             — a bullish Fair Value Gap exists between the sweep
#                        and the BOS leg (3-candle imbalance)
#   4. Entry           — price returns to retest that FVG zone
#   5. Stop Loss        — below the liquidity sweep low
#   6. Take Profit      — next liquidity level / prior highs

def detect_liquidity_sweep(low_series: pd.Series, n: int, lookback: int = 30):
    """
    Detects a liquidity sweep: the most recent low wicks BELOW a prior
    confirmed swing low (stop hunt) and then closes back above it.
    Returns (swept: bool, sweep_low: float, sweep_idx: int or None)
    """
    pivots = find_pivot_lows(low_series, n).dropna()
    if len(pivots) < 2:
        return False, np.nan, None

    # Use the second-to-last pivot as the "prior" liquidity pool
    prior_low_val = float(pivots.iloc[-2])
    prior_low_idx = pivots.index[-2]

    # Look at bars after the prior pivot for a wick below it
    # Use positional location (works for both integer and datetime index)
    search_start_pos = low_series.index.get_loc(prior_low_idx) + 1
    recent_lows = low_series.iloc[search_start_pos:]
    if len(recent_lows) == 0:
        return False, np.nan, None

    min_after = recent_lows.min()
    if min_after < prior_low_val:
        sweep_idx = recent_lows.idxmin()
        return True, float(min_after), sweep_idx

    return False, np.nan, None


def find_bullish_fvg(df: pd.DataFrame, after_idx=None):
    """
    Finds bullish Fair Value Gaps (3-candle imbalance):
    gap exists when low[i] > high[i-2]  (classic ICT/SMC FVG definition)
    If after_idx is given, only looks for FVGs formed at or after that index.
    Returns list of dicts: {gap_top, gap_bot, idx}
    """
    high = df["High"].values
    low  = df["Low"].values
    fvgs = []
    start = 2
    if after_idx is not None:
        try:
            start_pos = df.index.get_loc(after_idx)
            start = max(2, start_pos)
        except Exception:
            pass

    for i in range(start, len(df)):
        if low[i] > high[i - 2]:
            fvgs.append({
                "idx":     df.index[i],
                "gap_bot": float(high[i - 2]),
                "gap_top": float(low[i]),
            })
    return fvgs


def check_fvg_retest(cmp: float, fvgs: list, tolerance_pct: float = 0.3):
    """
    Checks if current price is sitting inside (or just touching) any
    bullish FVG zone — i.e. price has "returned to FVG" per the strategy.
    """
    for gap in fvgs:
        buf = gap["gap_top"] * tolerance_pct / 100
        if (gap["gap_bot"] - buf) <= cmp <= (gap["gap_top"] + buf):
            return True, gap
    return False, None


def analyse_bos_fvg_setup(df: pd.DataFrame, swing_n: int):
    """
    Full BOS + FVG + Liquidity Sweep setup check.
    Returns a dict with each stage's status plus an overall 'setup_ready' flag.
    """
    result = {
        "sweep":       False,
        "sweep_low":   np.nan,
        "bos":         False,
        "bos_level":   np.nan,
        "fvg_found":   False,
        "fvg_retest":  False,
        "fvg_zone":    None,
        "setup_ready": False,
        "stop_loss":   np.nan,
        "take_profit": np.nan,
    }

    close = df["Close"]
    low   = df["Low"]
    high  = df["High"]

    # Step 1: Liquidity sweep
    swept, sweep_low, sweep_idx = detect_liquidity_sweep(low, swing_n)
    result["sweep"]     = swept
    result["sweep_low"] = round(sweep_low, 2) if not np.isnan(sweep_low) else np.nan
    if not swept:
        return result

    # Step 2: BOS after the sweep — break above swing high formed after sweep_idx
    pivot_highs_after = find_pivot_highs(high, swing_n)
    after_mask = pivot_highs_after.index > sweep_idx
    highs_after_sweep = pivot_highs_after[after_mask].dropna()

    if len(highs_after_sweep) == 0:
        return result

    bos_level = float(highs_after_sweep.iloc[0])
    cmp = float(close.iloc[-1])
    bos_confirmed = cmp > bos_level
    result["bos"]       = bos_confirmed
    result["bos_level"] = round(bos_level, 2)
    if not bos_confirmed:
        return result

    # Step 3: Bullish FVG formed between sweep and now
    fvgs = find_bullish_fvg(df, after_idx=sweep_idx)
    result["fvg_found"] = len(fvgs) > 0
    if not fvgs:
        return result

    # Step 4: Price returns to retest the FVG zone
    retest, gap = check_fvg_retest(cmp, fvgs, tolerance_pct=FVG_RETEST_TOLERANCE_PCT)
    result["fvg_retest"] = retest
    result["fvg_zone"]   = gap

    if retest:
        result["setup_ready"] = True
        result["stop_loss"]   = round(sweep_low, 2)
        # Take profit = next liquidity level = most recent swing high before sweep
        pivot_highs_all = find_pivot_highs(high, swing_n).dropna()
        if len(pivot_highs_all) > 0:
            result["take_profit"] = round(float(pivot_highs_all.iloc[-1]) * 1.0, 2)

    return result



def analyse_stock(ticker: str) -> dict:
    """
    Downloads data and runs SMC demand zone analysis.
    Returns a result dict.
    """
    result = {
        "ticker":    ticker.replace(".NS", ""),
        "cmp":       np.nan,
        "zone_low":  np.nan,
        "zone_top":  np.nan,
        "zone_bot":  np.nan,
        "in_zone":   False,
        "near_zone": False,
        "pct_from_zone_top": np.nan,
        "bos":       False,
        "impulsive_base": False,
        "signal":    "—",
        "error":     None,
        # BOS + FVG + Liquidity Sweep strategy fields
        "ls_sweep":       False,
        "ls_bos":         False,
        "ls_fvg_found":   False,
        "ls_fvg_retest":  False,
        "ls_setup_ready": False,
        "ls_stop_loss":   np.nan,
        "ls_take_profit": np.nan,
    }

    try:
        df = None
        for attempt in range(3):
            try:
                df = yf.download(ticker, period=HISTORY_PERIOD, interval=TIMEFRAME,
                                 progress=False, auto_adjust=True)
                if df is not None and len(df) > 0:
                    break
            except Exception as e:
                if "Rate" in str(e) or "Too Many" in str(e):
                    time.sleep(3 * (attempt + 1))
                else:
                    raise

        if df is None or len(df) < SWING_LOOKBACK * 2 + 5:
            result["error"] = "Insufficient data"
            return result

        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df[["Open", "High", "Low", "Close"]].dropna()

        close = df["Close"]
        low   = df["Low"]
        high  = df["High"]
        open_ = df["Open"]

        cmp = float(close.iloc[-1])
        result["cmp"] = round(cmp, 2)

        # Last confirmed swing low
        last_sl = get_last_pivot_low(low, SWING_LOOKBACK)
        if np.isnan(last_sl):
            result["error"] = "No pivot low found"
            return result

        buf      = last_sl * ZONE_BUFFER_PCT / 100
        zone_bot = last_sl - buf
        zone_top = last_sl + buf * 2

        result["zone_low"] = round(last_sl, 2)
        result["zone_bot"] = round(zone_bot, 2)
        result["zone_top"] = round(zone_top, 2)

        # Zone status
        in_zone   = zone_bot <= cmp <= zone_top
        pct_above = round((cmp - zone_top) / zone_top * 100, 1)
        near_zone = not in_zone and 0 < pct_above <= NEAR_ZONE_PCT

        result["in_zone"]            = in_zone
        result["near_zone"]          = near_zone
        result["pct_from_zone_top"]  = pct_above

        # Check if departure from pivot low was impulsive
        pivots = find_pivot_lows(low, SWING_LOOKBACK)
        valid_pivot_idx = pivots.dropna().index
        if len(valid_pivot_idx) > 0:
            last_pivot_pos = df.index.get_loc(valid_pivot_idx[-1])
            dep_pos        = last_pivot_pos + 1
            if dep_pos < len(df):
                result["impulsive_base"] = is_impulsive_candle(
                    float(open_.iloc[dep_pos]),
                    float(close.iloc[dep_pos]),
                    float(high.iloc[dep_pos]),
                    float(low.iloc[dep_pos]),
                )

        # BOS check
        pivot_highs    = find_pivot_highs(high, SWING_LOOKBACK)
        result["bos"]  = check_bos(close, pivot_highs)

        # ── BOS + FVG + Liquidity Sweep strategy ───────────────────────────
        ls = analyse_bos_fvg_setup(df, SWING_LOOKBACK)
        result["ls_sweep"]       = ls["sweep"]
        result["ls_bos"]         = ls["bos"]
        result["ls_fvg_found"]   = ls["fvg_found"]
        result["ls_fvg_retest"]  = ls["fvg_retest"]
        result["ls_setup_ready"] = ls["setup_ready"]
        result["ls_stop_loss"]   = ls["stop_loss"]
        result["ls_take_profit"] = ls["take_profit"]

        # Signal label
        if ls["setup_ready"]:
            result["signal"] = "LS+BOS+FVG ENTRY"
        elif in_zone and result["bos"]:
            result["signal"] = "IN ZONE + BOS"
        elif in_zone and result["impulsive_base"]:
            result["signal"] = "IN ZONE + IMPULSE"
        elif in_zone:
            result["signal"] = "IN ZONE"
        elif near_zone:
            result["signal"] = f"NEAR ({pct_above}%)"
        else:
            result["signal"] = f"{pct_above}% above"

    except Exception as e:
        result["error"] = str(e)[:60]

    return result


# ─── DISPLAY ─────────────────────────────────────────────────────────────────

def color_signal(signal: str) -> str:
    if "LS+BOS+FVG ENTRY" in signal:
        return Back.GREEN + Fore.BLACK + Style.BRIGHT + f" {signal} " + Style.RESET_ALL
    elif "IN ZONE + BOS" in signal or "IN ZONE + IMPULSE" in signal:
        return Back.YELLOW + Fore.BLACK + f" {signal} " + Style.RESET_ALL
    elif "IN ZONE" in signal:
        return Back.BLUE + Fore.WHITE + f" {signal} " + Style.RESET_ALL
    elif "NEAR" in signal:
        return Fore.YELLOW + signal + Style.RESET_ALL
    else:
        return Fore.WHITE + Style.DIM + signal + Style.RESET_ALL


def print_header():
    now = datetime.now().strftime("%d %b %Y  %H:%M")
    print()
    print(Fore.CYAN + Style.BRIGHT + "═" * 72)
    print(Fore.CYAN + Style.BRIGHT +
          f"  Nifty 50 — SMC Demand Zone Scanner   [{now}]")
    print(Fore.CYAN + Style.BRIGHT +
          f"  Timeframe: {TIMEFRAME}  |  Swing: {SWING_LOOKBACK} bars  |  "
          f"Buffer: {ZONE_BUFFER_PCT}%  |  Near threshold: {NEAR_ZONE_PCT}%")
    print(Fore.CYAN + Style.BRIGHT + "═" * 72)
    print()


def print_summary(results: list):
    in_zone   = [r for r in results if r["in_zone"]]
    near_zone = [r for r in results if r["near_zone"]]
    bos_hits  = [r for r in results if r["bos"] and r["in_zone"]]
    ls_ready  = [r for r in results if r["ls_setup_ready"]]
    errors    = [r for r in results if r["error"]]

    print(Fore.GREEN + Style.BRIGHT +
          f"  🎯 LS+BOS+FVG ENTRY : {len(ls_ready):>2} stocks  (full strategy match)")
    print(Fore.GREEN + Style.BRIGHT +
          f"  ✅ IN ZONE          : {len(in_zone):>2} stocks")
    print(Fore.YELLOW + Style.BRIGHT +
          f"  ⚠️  NEAR ZONE        : {len(near_zone):>2} stocks  (within {NEAR_ZONE_PCT}% above zone)")
    print(Fore.MAGENTA + Style.BRIGHT +
          f"  🔥 BOS + ZONE       : {len(bos_hits):>2} stocks  (strongest demand-zone signal)")
    if errors:
        print(Fore.RED + f"  ❌ Errors           : {len(errors):>2} stocks (data unavailable)")
    print()


def print_table(results: list):
    # Sort: full strategy match first, then BOS+zone, impulse, zone, near, rest
    def sort_key(r):
        if r["ls_setup_ready"]:
            return 0
        elif r["in_zone"] and r["bos"]:
            return 1
        elif r["in_zone"] and r["impulsive_base"]:
            return 2
        elif r["in_zone"]:
            return 3
        elif r["near_zone"]:
            return 4
        else:
            return 5

    sorted_r = sorted(results, key=sort_key)

    rows = []
    for r in sorted_r:
        if r["error"]:
            rows.append([
                r["ticker"], "—", "—", "—", "—", "—", f"ERR: {r['error']}"
            ])
            continue

        sl = f"₹{r['ls_stop_loss']:,.1f}"   if not np.isnan(r["ls_stop_loss"])   else "—"
        tp = f"₹{r['ls_take_profit']:,.1f}" if not np.isnan(r["ls_take_profit"]) else "—"

        rows.append([
            r["ticker"],
            f"₹{r['cmp']:,.1f}",
            f"₹{r['zone_bot']:,.1f} – ₹{r['zone_top']:,.1f}",
            sl,
            tp,
            "✅" if r["bos"] else "—",
            color_signal(r["signal"]),
        ])

    headers = ["STOCK", "CMP", "Demand Zone", "SL", "TP", "BOS", "STATUS"]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline",
                   colalign=("left","right","right","right","right","center","left")))
    print()


def save_csv(results: list):
    rows = []
    for r in results:
        rows.append({
            "Date":         datetime.now().strftime("%Y-%m-%d"),
            "Stock":        r["ticker"],
            "CMP":          r["cmp"],
            "Swing Low":    r["zone_low"],
            "Zone Bottom":  r["zone_bot"],
            "Zone Top":     r["zone_top"],
            "In Zone":      r["in_zone"],
            "Near Zone":    r["near_zone"],
            "BOS":          r["bos"],
            "Liquidity Sweep": r["ls_sweep"],
            "LS-BOS":          r["ls_bos"],
            "FVG Found":       r["ls_fvg_found"],
            "FVG Retest":      r["ls_fvg_retest"],
            "Setup Ready":     r["ls_setup_ready"],
            "Stop Loss":       r["ls_stop_loss"],
            "Take Profit":     r["ls_take_profit"],
            "Signal":       r["signal"].replace("\x1b[0m","").strip(),
            "Error":        r["error"] or "",
        })
    fname = f"smc_scan_{datetime.now().strftime('%Y%m%d')}.csv"
    pd.DataFrame(rows).to_csv(fname, index=False)
    print(Fore.CYAN + f"  💾 Results saved to: {fname}")
    print()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print_header()

    print(Fore.WHITE + f"  Scanning {len(NIFTY500)} Nifty 500 stocks on {TIMEFRAME} timeframe...")
    print(Fore.WHITE + "  This takes ~30–60 seconds. Please wait.\n")

    results = []
    for i, ticker in enumerate(NIFTY500):
        symbol = ticker.replace(".NS", "")        
        print(f"  [{i+1:>2}/{len(NIFTY500)}] {symbol:<15}", end="\r", flush=True)
        results.append(analyse_stock(ticker))
        time.sleep(0.3)

    print(" " * 40, end="\r")  # clear progress line

    print_summary(results)
    print_table(results)

    if SAVE_CSV:
        save_csv(results)

    # Final highlight — full strategy entries first, then demand-zone stocks
    ls_entries     = [r["ticker"] for r in results if r["ls_setup_ready"]]
    in_zone_stocks = [r["ticker"] for r in results if r["in_zone"]]

    if ls_entries:
        print(Back.GREEN + Fore.BLACK + Style.BRIGHT +
              "  🎯 LS+BOS+FVG ENTRY SETUPS → " +
              ", ".join(ls_entries) + "  " + Style.RESET_ALL)
        print()

    if in_zone_stocks:
        print(Fore.BLUE + Back.WHITE + Style.BRIGHT +
              "  TODAY'S BUY ZONE STOCKS → " +
              ", ".join(in_zone_stocks) + "  " + Style.RESET_ALL)
        print()

    if not ls_entries and not in_zone_stocks:
        print(Fore.YELLOW +
              "  No stocks in demand zone or LS+BOS+FVG setup today. "
              "Try increasing Zone Buffer % in CONFIG.")
        print()


if __name__ == "__main__":
    main()
