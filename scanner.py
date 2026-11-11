#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
 INTRADAY SCANNER v3.3 - ALL THREE SOP STRATEGIES, FULLY AUTOMATED
 (AUTO-POI FOR STRATEGY 3) + 15:10 AUTO SQUARE-OFF + SELF-LEARNING JOURNAL
===============================================================================
Companion tool to the "Top 3 Intraday Strategies & Scanners SOP (Rev 2.x)".

WHAT IT DOES
------------
1. Scans NIFTY 100 stocks every 5 minutes and evaluates ALL THREE SOP
   strategies on closed 5-minute bars:
   S1  Fibonacci Extension Continuation (SOP 3.1, Types 01/02/03):
       A-B-C impulse + pullback structure, activation close beyond Fib
       Extension Level 1, golden-pocket / 0.236 zone watch, 2R+1G (long)
       or 2G+1R (short) trigger, buy/sell stop beyond the green/red candle,
       5-bar trigger expiry, noise filter on the green candle range.
   S2  NSE Momentum + Volume Breakout (SOP 3.2, Table 7, verbatim):
       close beyond prior 3-bar high/low + VWAP side + EMA9/EMA20 + RSI(14)
       55/45 + 1.5x 20-bar volume surge with a 100k-share floor + close in
       the top/bottom 25% of the signal bar + Rs 50-2000 band + minimum
       stop = max(0.30% of entry, 1.5 x ATR14). Entry = signal high/low
       +/- one tick (stop order), SL beyond the signal bar, 1:3 target.
   S3  Five-Timeframe CHoCH (SOP 3.3): H4 POI zones are marked FOR you by
       the AutoPoi engine every morning (supply = swing highs, demand =
       swing lows on H4, fresh-only, near price) - no manual zone entry
       needed. Optional manual overrides in poi_zones.csv are merged in.
       W1/D1 bias computed from daily closes (must agree), H1 confirmation
       (engulfing / pin bar / CHoCH close), M15 close in direction, stop
       one tick beyond the POI extreme, target = nearest opposing POI if
       >= 2R else fixed 3R.
2. Sizes every confirmed signal to the SOP risk model (0.25% capital risk,
   1:3 fixed reward:risk) and enforces SOP 3.4 discipline: max 2 concurrent
   positions, max 10 trades/day (config: max_trades_per_day), one position
   per instrument, and a hard entry cutoff - no signals after 13:30 IST for
   ANY strategy.
3. AUTOMATED SQUARE-OFF: the loop stops scanning at 15:10 IST, every OPEN
   trade in the journal is squared off with the freshest available price,
   day verdicts are refreshed, the final report is printed and the console
   closes. A 15:05 heads-up alert is sent first (Telegram/console).
4. SELF-LEARNING (v3.2): every cycle the scanner studies the last 30 closed
   trades in the journal - win/loss split by strategy (S1/S2/S3), by
   direction (LONG/SHORT), by entry hour and the recent 10-trade trend -
   and BENCHES whatever is statistically losing. A benched strategy or
   direction emits no signals until its form recovers; gates re-compute
   after every closed trade and reset from the fresh journal each morning.
5. ALERTS ONLY. It never places orders. Verify every signal in your broker
   terminal and pass the SOP 12-point checklist before acting.

WHAT IS NEW IN v3.3 (vs v3.2.2)
-------------------------------
* NO MORE AUTO-BLOCKING (study mode): the self-learning engine now runs in
  OBSERVE-ONLY mode by default (self_learning.blocking = false). It still
  studies the journal and reports which families/directions WOULD be
  benched, but it never stops a signal any more - while the system is
  being tested it must keep producing data, not silence.
* CIRCUIT BREAKER NO LONGER STOPS SIGNALS (journal.breaker_blocking =
  false): a tripped breaker still sends the SOP warning and still marks
  the day FAILED in daily_summary.csv, but scanning and alerting continue
  so the day produces a full, studyable sample.
* SHADOW SIGNALS AFTER THE DAILY CAP (shadow_after_cap = true): the
  10-trades/day cap stays exactly as it is - after 10 ALERTED trades the
  scanner stops alerting, but it KEEPS SCANNING and journals every further
  confirmed signal as a SHADOW row (Mode=SHADOW in trade_journal.csv).
  Shadow rows are tracked to their WIN/LOSS outcome like normal trades,
  are excluded from day stats, verdicts and the circuit breaker, and are
  reported separately ("SHADOW STUDY") - pure fuel for improving the
  strategies for the next day.

WHAT IS NEW IN v3.2.2 (vs v3.2.1)
---------------------------------
* CRASH FIX: run_once could die with "TypeError: '<' not supported between
  instances of 'tuple' and 'str'" the moment Strategy 1 put a live A-B-C
  setup on its watch list. The S1 watch set holds (symbol, side) TUPLES
  and was unioned into the symbol set that is sorted() for the bar
  request - a mixed tuple/str sort. The watch list is now projected to
  plain symbols before the union and the bar request sorts a strings-only
  set; a dedicated regression test pins this behaviour.

WHAT IS NEW IN v3.2.1 (vs v3.2)
-------------------------------
* UNIVERSE AUTO-REFRESH: NIFTY 100 members change when NSE re-balances the
  index or a company delists, and the old static universe_nifty100.txt kept
  throwing data errors for dead symbols. The scanner now refreshes its own
  universe at startup at most once every universe_refresh.days (default 7):
    1. official NSE constituents CSV (works from home IPs),
    2. Wikipedia NIFTY 50 + NIFTY Next 50 tables (works from cloud runners),
    3. the existing file (always the last-resort fallback).
  A refreshed list is written back to universe_nifty100.txt + cached in
  universe_cache.json (committed by the GitHub workflow), added/removed
  symbols are printed and Telegram-alerted. Any failure is non-fatal.

WHAT IS NEW IN v3.2 (vs v3.1)
-----------------------------
* SELF-LEARNING ENGINE: the scanner now reads the last 30 closed trades
  from trade_journal.csv and computes overall form, per-strategy form,
  LONG vs SHORT form, entry-hour form and the recent-10 "moving trend".
  From those it builds transparent, rule-based gates:
    - a strategy family (S1/S2/S3) is BENCHED for the day when it has 8+
      closed trades and either win rate < 30% or net R <= -2R (tunable),
      or when its recent form collapses (< 20% WR over 6+ of the last 10
      trades);
    - a direction (LONG/SHORT) is BENCHED when it has 10+ closed trades
      with win rate < 25%.
  Benched = no new signals from that family/direction; open trades are
  still monitored to their normal outcome. Gates refresh after every
  closed trade, so a benched family can earn its way back the same day.
  The snapshot is saved to journal/learning_state.json (committed by the
  GitHub Actions workflow, so learning persists across cloud runs), and a
  SELF-LEARNING REPORT is appended to the EOD output + sent to Telegram
  once a day.
* DAILY TRADE CAP RAISED TO 10 (was 3): after 10 trades in a day the
  scanner stops issuing signals and sends one Telegram notice; open
  trades keep being monitored and squared off at 15:10 as usual.
* ENGINE-WIDE 13:30 CUTOFF: the SOP "no entries after 13:30" rule was
  only enforced inside Strategy 2 - it now filters ALL strategies, so an
  S1/S3 confirmation that lands at 13:35 is dropped.

WHAT IS NEW IN v3.1 (vs v3.0)
-----------------------------
* STRATEGY 3 IS NOW FULLY AUTOMATED: the new AutoPoi engine builds the
  H4 supply/demand zone map itself every morning from Yahoo 1-hour
  history (two H4 candles per NSE session: 09:15-13:15, 13:15-15:30),
  keeps only fresh zones (never closed through), within +/-6% of the
  last close, and writes poi_zones_auto.csv. Zones carry today's date
  and expire at midnight - a brand-new map is generated next session.
  Your manual poi_zones.csv (if you fill it) is merged on top, so you
  can still force a zone the machine did not pick.
* Morning Telegram summary now lists how many auto zones survived the
  W1/D1 bias alignment, so you know Strategy 3's watchlist before 09:30.

WHAT IS NEW IN v3.0 (vs v2.2.1)
-------------------------------
* Strategy 2 rebuilt to match SOP Table 7 exactly (3-bar breakout, EMA9/20,
  RSI gate, 1.5x volume + 100k shares, bar-range close, Rs 2000 cap,
  ATR minimum stop, stop-order entry at signal high/low + 1 tick).
* Strategy 1 (Fibonacci Extension Continuation, Types 01/02/03) implemented.
* Strategy 3 (Five-Timeframe CHoCH) implemented - reads poi_zones.csv,
  computes W1/D1 bias itself, watches H1 + M15 confirmation at your zones.
* 15:10 square-off hardened: history-based finalize + fresh-bar fallback,
  15:05 warning alert, weekend exit, --once EOD guard for cloud runs.

USAGE
-----
  python scanner.py                 continuous 5-minute scanning loop
  python scanner.py --once          run a single scan cycle and exit
  python scanner.py --journal       update journal + print report, no scan
  python scanner.py --selftest      run the built-in test suite
  python journal.py                 standalone journal updater/reporter

DISCLAIMER: educational tooling only, not investment advice. Trading intraday
equities carries a high risk of loss. You are the risk manager; this script
only watches prices and keeps your logbook.
===============================================================================
"""

import os
import io
import sys
import csv
import json
import math
import time
import argparse
import traceback
import urllib.parse
import urllib.request
from collections import namedtuple
from datetime import datetime, timedelta, time as dtime, timezone

VERSION = "3.3.0"

# ---------------------------------------------------------------------------
# Time zone: Indian Standard Time is UTC+05:30 year-round (no DST), so a fixed
# offset is the most portable choice (works on Windows without tzdata).
# ---------------------------------------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist():
    return datetime.now(IST)


def parse_hhmm(s):
    h, m = str(s).strip().split(":")
    return dtime(int(h), int(m))


def fmt2(x):
    try:
        return f"{float(x):.2f}"
    except Exception:
        return str(x)


def _hhmm(dt):
    return dt.strftime("%H:%M")


def round_tick(price, mode="nearest", tick=0.05):
    """Round to the NSE tick size (Rs 0.05)."""
    n = price / tick
    if mode == "down":
        v = math.floor(n + 1e-9)
    elif mode == "up":
        v = math.ceil(n - 1e-9)
    else:
        v = round(n)
    return round(v * tick, 2)


# ---------------------------------------------------------------------------
# Default configuration. Anything the user omits in config.json is merged
# from here, so the journal works out of the box even with an old config.
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "data_mode": "auto",              # auto | nse | yahoo
    "universe_file": "universe_nifty100.txt",
    # ---- v3.2.1 universe auto-refresh (NIFTY 100 re-balance / delisting) ----
    "universe_refresh": {
        "enabled": True,              # weekly auto-update of constituents
        "days": 7,                    # fetch at most once per N days
        "min_symbols": 80,            # sanity guard on any fetched list
        "max_symbols": 120
    },
    "scan_interval_min": 5,
    "rotate_slice": 25,               # NSE mode: bar-check N extra symbols/cycle
    "scan_start": "09:30",            # no signals before this (IST)
    "entry_cutoff": "13:30",          # SOP: no new entries after 13:30
    "squareoff": "15:10",             # SOP: intraday square-off time
    "squareoff_alert": "15:05",       # heads-up alert before square-off
    "exit_after": "15:35",            # hard loop-exit safety net
    "auto_exit_after_close": True,    # close the console after EOD processing
    "capital": 25000,                 # Rs - trading capital
    "risk_pct": 0.25,                 # Phase V risk per trade (% of capital)
    "rr": 3.0,                        # fixed reward:risk (Phase V = 1:3 only)
    "cost_rt": 50.0,                  # SOP App.B: est. round-trip cost (Rs)
    "sl_buffer_pct": 0.10,            # legacy; SOP 1-tick buffer is used now
    "max_stop_pct": 1.5,              # skip setups whose stop is wider (%)
    "min_bars": 15,                   # 5m bars required before any signal
    "min_price": 50,                  # S2 universe band floor (Rs)
    "max_price": 2000,                # S2 universe band cap (Rs)
    "min_turnover": 10000000,         # data-quality: day turnover >= 1 crore
    "min_range_pct": 0.40,            # data-quality: day range >= 0.4%
    # ---- Strategy 2: NSE Momentum + Volume Breakout (SOP 3.2, Table 7) ----
    "breakout_bars": 3,               # close beyond prior N-bar high/low
    "vol_avg_bars": 20,               # volume surge baseline
    "rvol_mult": 1.5,                 # bar vol >= 1.5x 20-bar average
    "min_bar_volume": 100000,         # ...and >= 100k shares
    "ema_fast": 9,                    # EMA9 above (long) / below (short) EMA20
    "ema_slow": 20,
    "rsi_period": 14,
    "rsi_long": 55,                   # RSI(14) > 55 for longs
    "rsi_short": 45,                  # RSI(14) < 45 for shorts
    "close_extreme_pct": 25,          # close in top/bottom 25% of BAR range
    "min_stop_pct": 0.30,             # min stop = max(0.30% of entry, 1.5xATR)
    "atr_stop_mult": 1.5,
    # ---- Strategy 1: Fibonacci Extension Continuation (SOP 3.1) ----
    "s1_enabled": True,
    "impulse_min_pct": 0.5,           # min A->B impulse leg size (% of A)
    "fib_tol_pct": 0.2,               # zone tolerance (% of price)
    "trigger_expiry_bars": 5,         # green-high break window (SOP: 5 bars)
    "green_min_range_pct": 0.30,      # skip noise-dominated green candles
    # ---- Strategy 3: Five-Timeframe CHoCH (SOP 3.3) ----
    "s3_enabled": True,
    "poi_file": "poi_zones.csv",      # OPTIONAL manual zone overrides
    "s3_auto_poi": True,              # auto-mark H4 POI zones each morning
    "poi_auto_file": "poi_zones_auto.csv",
    "s3_poi_hist_period": "60d",      # 1h history window for detection
    "s3_poi_lookback_days": 30,       # scan the last N sessions of H4
    "s3_poi_max_zone_pct": 2.0,       # drop zones taller than this %
    "s3_poi_proximity_pct": 6.0,      # only zones within +/-X% of price
    "s3_poi_max_per_side": 2,         # nearest N fresh zones per side
    # ---- SOP 3.4 / Phase V discipline caps ----
    "max_concurrent_positions": 2,    # never hold more than 2 positions
    "max_trades_per_day": 10,         # v3.2: daily trade cap (was 3)
    "shadow_after_cap": True,         # v3.3: after the cap keep journaling
                                      # signals as SHADOW rows for study
    # ---- v3.2 self-learning: study the last N closed trades and bench
    # ---- whatever is statistically losing (rules documented in README 6)
    "self_learning": {
        "enabled": True,
        "blocking": False,            # v3.3: observe-only - report what
                                      # WOULD be benched, never block
        "lookback_trades": 30,        # study the last 30 closed trades
        "recent_trades": 10,          # "moving trend" tail of that window
        "min_trades_to_gate": 8,      # min sample before a family is benched
        "block_setup_wr_below": 30.0, # bench family: win rate < 30%...
        "block_setup_r_below": -2.0,  # ...or net R <= -2R
        "min_recent_trades": 6,       # recent-form collapse: min sample
        "recent_form_wr_below": 20.0, # ...win rate < 20% of the last 10
        "min_direction_trades": 10,   # min sample for a direction gate
        "block_direction_wr_below": 25.0
    },
    "telegram": {"bot_token": "", "chat_id": ""},
    "journal": {
        "folder": "journal",
        "breaker_blocking": False,    # v3.3: tripped breaker warns + marks
                                      # the day FAILED but keeps signals on
        "daily_loss_limit_R": -2.0,   # circuit breaker: day loss limit (R)
        "daily_loss_limit_amt": 0,    # optional Rs limit (0 = disabled)
        "max_consecutive_losses": 2   # circuit breaker: loss streak
    }
}


def deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


CURRENT_CFG = None  # set by load_config(); used by send_telegram()


def load_config(path="config.json"):
    global CURRENT_CFG
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                user = json.load(f)
            cfg = deep_merge(DEFAULT_CONFIG, user)
        except Exception as e:
            print(f"[CONFIG] could not parse {path} ({e}); using defaults")
    # sanity
    cfg["scan_start_t"] = parse_hhmm(cfg["scan_start"])
    cfg["entry_cutoff_t"] = parse_hhmm(cfg["entry_cutoff"])
    cfg["squareoff_t"] = parse_hhmm(cfg["squareoff"])
    cfg["squareoff_alert_t"] = parse_hhmm(cfg.get("squareoff_alert", "15:05"))
    cfg["exit_after_t"] = parse_hhmm(cfg.get("exit_after", "15:35"))
    if cfg["rr"] <= 0:
        cfg["rr"] = 3.0
    CURRENT_CFG = cfg
    return cfg


def send_telegram(text):
    """Fire-and-forget Telegram message. Never raises."""
    cfg = CURRENT_CFG or {}
    tg = (cfg.get("telegram") or {})
    token, chat = tg.get("bot_token", ""), tg.get("chat_id", "")
    if not token or not chat:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()
        return True
    except Exception as e:
        print(f"[TG] telegram send failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Market data primitives
# ---------------------------------------------------------------------------
Bar = namedtuple("Bar", "ts open high low close volume")


def load_universe(path):
    """One symbol per line, '#' comments allowed. Returns NSE symbols
    (suffix .NS stripped; Yahoo calls re-attach it)."""
    syms = []
    if not os.path.exists(path):
        print(f"[WARN] universe file '{path}' not found")
        return syms
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.split("#")[0].strip().upper()
            if not s:
                continue
            if s.endswith(".NS"):
                s = s[: -len(".NS")]
            if s not in syms:
                syms.append(s)
    return syms


# ---------------------------------------------------------------------------
# v3.2.1 Universe auto-refresh. NIFTY 100 members change whenever NSE
# re-balances the index (semi-annual review + ad-hoc deletions when a
# company delists or is suspended). A stale universe then keeps throwing
# data errors for dead symbols. The scanner therefore refreshes its own
# universe file at startup, at most once per universe_refresh.days (7):
#   1. official NSE constituents CSV (nsearchives / archives hosts) -
#      authoritative, but NSE blocks datacenter IPs so this works from
#      home broadband, not from GitHub Actions;
#   2. Wikipedia NIFTY 50 + NIFTY Next 50 constituents tables - reachable
#      from cloud runners, no API key, updated by editors on re-balance day;
#   3. the existing universe_nifty100.txt - always kept as last resort.
# A success rewrites universe_nifty100.txt and caches the result (date,
# source, symbols) in universe_cache.json; the cloud workflow commits both
# so every later run starts current. Every failure is non-fatal: the old
# file stays in use and the next attempt happens after the next window.
# ---------------------------------------------------------------------------
_UNIV_TIMEOUT = 15
_UNIV_HDRS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/json,text/csv,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}
_NSE_LIST_URLS = (
    "https://nsearchives.nseindia.com/content/indices/"
    "ind_nifty100list.csv",
    "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
)
_WIKI_PAGES = ("https://en.wikipedia.org/wiki/NIFTY_50",
               "https://en.wikipedia.org/wiki/NIFTY_Next_50")


def _fetch_nifty100_nse(timeout=_UNIV_TIMEOUT):
    """Official NSE constituents CSV -> plain NSE symbols. Raises when
    unreachable (the caller falls through to the Wikipedia source)."""
    last = None
    for url in _NSE_LIST_URLS:
        try:
            req = urllib.request.Request(url, headers=_UNIV_HDRS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                text = r.read().decode("utf-8", "replace")
            syms = []
            for row in csv.DictReader(io.StringIO(text)):
                s = (row.get("Symbol") or row.get("SYMBOL") or
                     "").strip().upper()
                if s and s not in syms and not s.startswith("NIFTY"):
                    syms.append(s)
            if syms:
                return syms
        except Exception as e:
            last = e
    raise RuntimeError(f"NSE constituent list unreachable ({last})")


def _parse_wiki_constituents(page):
    """Ticker symbols from a Wikipedia constituents wikitable, pure regex
    (no bs4/lxml dependency): locate the table whose header row has a
    'Symbol' column, then read that column cell by cell. Returns [] when
    nothing matches."""
    import re as _re
    import html as _html
    out = []
    for tbl in _re.findall(r"<table[^>]*wikitable[^>]*>(.*?)</table>",
                           page, _re.S | _re.I):
        heads = [_re.sub(r"<[^>]+>", "", h).strip().upper()
                 for h in _re.findall(r"<th[^>]*>(.*?)</th>",
                                      tbl, _re.S | _re.I)]
        if "SYMBOL" not in heads:
            continue
        col = heads.index("SYMBOL")
        for row in _re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, _re.S | _re.I):
            cells = _re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>",
                                row, _re.S | _re.I)
            if not cells or len(cells) <= col:
                continue
            n_th = len(_re.findall(r"<th[^>]*>", row, _re.I))
            if n_th and n_th == len(cells):
                continue                  # pure header row (thead)
            sym = _html.unescape(_re.sub(r"<[^>]+>", "", cells[col]))
            sym = sym.strip().upper()
            if _re.fullmatch(r"[A-Z0-9&\-\.]{2,20}", sym) and \
                    not sym.startswith("NIFTY") and sym not in out:
                out.append(sym)
    return out


def _fetch_nifty100_wiki(timeout=_UNIV_TIMEOUT):
    """Wikipedia NIFTY 50 + NIFTY Next 50 tables -> ~100 symbols
    (the NIFTY 100 index is exactly those two buckets). Raises when the
    combined result is implausibly small."""
    out = []
    for url in _WIKI_PAGES:
        try:
            req = urllib.request.Request(url, headers=_UNIV_HDRS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                page = r.read().decode("utf-8", "replace")
            for s in _parse_wiki_constituents(page):
                if s not in out:
                    out.append(s)
        except Exception as e:
            print(f"[UNIVERSE] {url.rsplit('/', 1)[-1]}: fetch failed "
                  f"({e})")
    if len(out) < 50:
        raise RuntimeError(f"Wikipedia gave only {len(out)} symbols")
    return out


def _write_universe_file(path, symbols, source, updated):
    """Rewrite the universe file in load_universe() format (SYMBOL.NS per
    line). Atomic via temp-file + os.replace."""
    tmp = path + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(f"# NIFTY 100 constituents - auto-updated {updated} "
                f"(source: {source})\n")
        f.write("# Maintained by the scanner universe auto-refresh "
                "(config: universe_refresh).\n")
        f.write("# Manual edits are overwritten at the next refresh; "
                "set universe_refresh.enabled=false to freeze.\n")
        for s in symbols:
            f.write(s + ".NS\n")
    os.replace(tmp, path)


def refresh_universe(cfg, base_dir=".", notify=None):
    """Weekly auto-update of universe_nifty100.txt (see block comment).
    Returns (symbols, changed): symbols=[] means 'keep the current file'
    (refresh disabled, inside the schedule window, or every source
    failed). Never raises."""
    ru = cfg.get("universe_refresh") or {}
    if not ru.get("enabled", True):
        return [], False
    ufile = os.path.join(base_dir, cfg.get("universe_file",
                                           "universe_nifty100.txt"))
    cpath = os.path.join(base_dir, "universe_cache.json")
    lo, hi = int(ru.get("min_symbols", 80)), int(ru.get("max_symbols", 120))
    days = float(ru.get("days", 7))
    today = now_ist().date()
    cache = {}
    try:
        with open(cpath, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        cache = {}
    last_att = str(cache.get("last_attempt", ""))
    if last_att:
        try:
            gap = (today - datetime.strptime(last_att, "%Y-%m-%d").date()).days
            if gap < days:
                return [], False          # inside the schedule window
        except ValueError:
            pass                          # corrupt date -> try again
    old = load_universe(ufile)
    print(f"[UNIVERSE] refreshing NIFTY 100 constituents (file has "
          f"{len(old)} symbols; last attempt {last_att or 'never'})...")
    syms, source = [], None
    for name, fn in (("NSE", _fetch_nifty100_nse),
                     ("Wikipedia", _fetch_nifty100_wiki)):
        try:
            got = fn()
            if lo <= len(got) <= hi:
                syms, source = got, name
                break
            print(f"[UNIVERSE] {name} list rejected: {len(got)} symbols "
                  f"outside the {lo}-{hi} sanity window")
        except Exception as e:
            print(f"[UNIVERSE] {name} unavailable: {e}")
    snap = {"last_attempt": today.isoformat(),
            "updated": cache.get("updated", ""),
            "source": cache.get("source", "")}
    changed = False
    if source:
        added = [s for s in syms if s not in old]
        removed = [s for s in old if s not in syms]
        try:
            _write_universe_file(ufile, syms, source, today.isoformat())
            changed = True
            snap["updated"] = today.isoformat()
            snap["source"] = source
            snap["symbols"] = syms
            print(f"[UNIVERSE] refreshed from {source}: {len(syms)} symbols "
                  f"(+{len(added)} added, -{len(removed)} removed)")
            if (added or removed) and notify:
                msg = (f"\U0001f4bb Universe auto-refresh from {source}: "
                       f"{len(syms)} symbols (+{len(added)} added, "
                       f"-{len(removed)} removed)")
                if added:
                    msg += "\n+ " + ", ".join(added[:15])
                if removed:
                    msg += "\n- " + ", ".join(removed[:15])
                notify(msg)
        except Exception as e:
            print(f"[UNIVERSE] could not rewrite the universe file ({e}); "
                  f"keeping the old list")
    else:
        print("[UNIVERSE] all sources failed - keeping the current file "
              f"(next attempt in {int(days)} day(s))")
    try:
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(snap, f, indent=1)
    except Exception:
        pass
    return syms, changed


def ema_series(values, period):
    """Recursive EMA (adjust=False style). Always defined from bar 1, which
    keeps the EMA comparisons usable through the morning session."""
    if not values:
        return []
    k = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1.0 - k))
    return out


def vwap_series(bars):
    out, pv, vv = [], 0.0, 0.0
    for b in bars:
        tp = (b.high + b.low + b.close) / 3.0
        v = b.volume or 0
        pv += tp * v
        vv += v
        out.append(pv / vv if vv > 0 else b.close)
    return out


def rsi_series(values, period=14):
    """Wilder's RSI. Entries before the seed window are None."""
    n = len(values)
    if n < period + 1:
        return [None] * n
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = values[i] - values[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    ag, al = gains / period, losses / period
    out = [None] * period
    if al == 0:
        out.append(100.0 if ag > 0 else 50.0)
    else:
        out.append(100.0 - 100.0 / (1.0 + ag / al))
    for i in range(period + 1, n):
        d = values[i] - values[i - 1]
        ag = (ag * (period - 1) + max(d, 0.0)) / period
        al = (al * (period - 1) + max(-d, 0.0)) / period
        if al == 0:
            out.append(100.0 if ag > 0 else 50.0)
        else:
            out.append(100.0 - 100.0 / (1.0 + ag / al))
    return out


def atr_series(bars, period=14):
    """Wilder's ATR. Entries before the seed window are None."""
    n = len(bars)
    if n < 2:
        return [None] * n
    trs = []
    for i, b in enumerate(bars):
        if i == 0:
            trs.append(b.high - b.low)
        else:
            pc = bars[i - 1].close
            trs.append(max(b.high - b.low, abs(b.high - pc), abs(b.low - pc)))
    if n < period + 1:
        return [None] * n
    a = sum(trs[:period]) / period
    out = [None] * (period - 1) + [a]
    for i in range(period, n):
        a = (a * (period - 1) + trs[i]) / period
        out.append(a)
    return out


def pivot_points_on_values(vals, k=2):
    """Fractal pivots on a plain value series: index i is a pivot high if
    vals[i] > the k values to its right (and >= the values to its left),
    so a pivot is confirmed exactly k bars after the extreme. The first
    k bars of the series get edge treatment (partial left window), which
    keeps the day's opening swing detectable. Returns
    ([(idx, val)...], [(idx, val)...])."""
    highs, lows = [], []
    n = len(vals)
    for i in range(n - k):
        right = vals[i + 1:i + k + 1]
        left = vals[max(0, i - k):i]
        if vals[i] > max(right) and (not left or vals[i] >= max(left)):
            highs.append((i, vals[i]))
        if vals[i] < min(right) and (not left or vals[i] <= min(left)):
            lows.append((i, vals[i]))
    return highs, lows


def pivot_points(bars, k=2):
    """Fractal pivots on OHLC bars: (pivot_highs, pivot_lows) as
    ([(idx, high)...], [(idx, low)...])."""
    hh, _ = pivot_points_on_values([b.high for b in bars], k)
    _, ll = pivot_points_on_values([b.low for b in bars], k)
    return hh, ll


# ===========================================================================
# SIGNAL OBJECT + STRATEGY 2 (SOP 3.2 Table 7, verbatim)
# ===========================================================================
class Signal:
    def __init__(self, symbol, direction, date, sig_time, entry, stop, target,
                 qty, risk_ps, risk_amt, reward_amt, note="", setup=None):
        self.symbol = symbol
        self.direction = direction          # LONG | SHORT
        self.setup = setup or ("S2_BREAKOUT" if direction == "LONG"
                               else "S2_BREAKDOWN")
        self.date = date                    # YYYY-MM-DD (IST)
        self.sig_time = sig_time            # HH:MM (IST)
        self.entry = entry
        self.stop = stop
        self.target = target
        self.qty = qty
        self.risk_ps = risk_ps
        self.risk_amt = risk_amt
        self.reward_amt = reward_amt
        self.note = note

    @property
    def trade_id(self):
        return f"{self.date.replace('-', '')}-{self.symbol}-{self.direction}"


def _size_and_check(symbol, direction, entry, stop, bar, cfg, setup, note):
    """Shared sizing + SOP 4.1 guards (all three strategies).
    Returns a Signal or None."""
    risk_ps = (entry - stop) if direction == "LONG" else (stop - entry)
    if risk_ps <= 0 or risk_ps / entry > float(cfg["max_stop_pct"]) / 100.0:
        return None
    risk_amt = float(cfg["capital"]) * float(cfg["risk_pct"]) / 100.0
    qty = int(risk_amt // risk_ps)
    if qty < 1:
        return None
    if direction == "LONG":
        target = round_tick(entry + float(cfg["rr"]) * risk_ps, "nearest")
    else:
        target = round_tick(entry - float(cfg["rr"]) * risk_ps, "nearest")
    reward_amt = abs(target - entry) * qty
    # SOP 4.1 Step 4 - capital-price rejection (qty is never cut to fit):
    if entry * qty > float(cfg["capital"]):
        return None
    # SOP 4.1 Step 5 - cost hurdle: 3R value must beat cost + Rs 50
    if reward_amt < float(cfg.get("cost_rt", 50.0)) + 50.0:
        return None
    return Signal(symbol, direction, bar.ts.date().isoformat(),
                  _hhmm(bar.ts), round(entry, 2), round(stop, 2),
                  round(target, 2), qty, round(risk_ps, 2),
                  round(risk_amt, 2), round(reward_amt, 2), note, setup)


def check_s2(symbol, bars, cfg):
    """Strategy 2 - NSE Momentum plus Volume Breakout (SOP 3.2, Table 7).
    Long form; shorts are a full mirror. Returns a Signal (setup
    S2_BREAKOUT / S2_BREAKDOWN) or None. All gates must pass."""
    n = len(bars)
    va = int(cfg["vol_avg_bars"])
    bb = int(cfg["breakout_bars"])
    rp = int(cfg["rsi_period"])
    need = max(int(cfg["min_bars"]), va + 2, rp + 2, bb + 2)
    if n < need:
        return None
    bar = bars[-1]
    t = bar.ts.time()
    if t < cfg["scan_start_t"] or t > cfg["entry_cutoff_t"]:
        return None
    if not bar.volume or not bar.close or bar.close <= 0 or bar.high <= bar.low:
        return None

    closes = [b.close for b in bars]
    vols = [b.volume or 0 for b in bars]

    # shared data-quality gates (unchanged from v2.2: staleness + turnover)
    day_high = max(b.high for b in bars)
    day_low = min(b.low for b in bars)
    if (day_high - day_low) / bar.close * 100.0 < float(cfg["min_range_pct"]):
        return None
    if bar.close * sum(vols) < float(cfg["min_turnover"]):
        return None

    # Universe filter: Rs 50 - Rs 2,000 (Table 7, row 6)
    if not (float(cfg["min_price"]) <= bar.close <= float(cfg["max_price"])):
        return None

    # Trend: VWAP side + EMA alignment (row 1)
    vwap = vwap_series(bars)[-1]
    e_fast = ema_series(closes, int(cfg["ema_fast"]))[-1]
    e_slow = ema_series(closes, int(cfg["ema_slow"]))[-1]

    # Momentum context: RSI(14) (row 2)
    rsi = rsi_series(closes, rp)[-1]
    if rsi is None:
        return None

    # Breakout: close beyond the prior 3-bar high/low (row 3)
    bh = max(b.high for b in bars[-(bb + 1):-1])
    bl = min(b.low for b in bars[-(bb + 1):-1])

    # Volume surge: 1.5x the 20-bar average AND >= 100k shares (row 4)
    base = sum(vols[-(va + 1):-1]) / va
    rvol = (bar.volume / base) if base > 0 else 0.0

    # Candle quality: bullish/bearish + close in the top/bottom 25% of the
    # signal bar's own high-low range (row 5)
    close_pos = (bar.close - bar.low) / (bar.high - bar.low)

    long_sig = (bar.close > vwap and e_fast > e_slow and rsi > float(cfg["rsi_long"])
                and bar.close > bh and bar.close > bar.open
                and rvol >= float(cfg["rvol_mult"])
                and bar.volume >= int(cfg["min_bar_volume"])
                and close_pos >= 1.0 - float(cfg["close_extreme_pct"]) / 100.0)
    short_sig = (bar.close < vwap and e_fast < e_slow and rsi < float(cfg["rsi_short"])
                 and bar.close < bl and bar.close < bar.open
                 and rvol >= float(cfg["rvol_mult"])
                 and bar.volume >= int(cfg["min_bar_volume"])
                 and close_pos <= float(cfg["close_extreme_pct"]) / 100.0)
    direction = "LONG" if long_sig else ("SHORT" if short_sig else None)
    if direction is None:
        return None

    # Entry/stop as SOP stop orders: signal high + 1 tick (buy stop) or
    # signal low - 1 tick (sell stop); SL one tick beyond the other extreme.
    if direction == "LONG":
        entry = round_tick(bar.high + 0.05, "up")
        stop = round_tick(bar.low - 0.05, "down")
    else:
        entry = round_tick(bar.low - 0.05, "down")
        stop = round_tick(bar.high + 0.05, "up")

    # Minimum stop gate (Table 7, row 7): >= max(0.30% of entry, 1.5xATR14)
    atr = atr_series(bars, rp)[-1]
    if atr is None:
        return None
    floor = max(float(cfg["min_stop_pct"]) / 100.0 * entry,
                float(cfg["atr_stop_mult"]) * atr)
    risk_now = (entry - stop) if direction == "LONG" else (stop - entry)
    if risk_now < floor:
        return None

    setup = "S2_BREAKOUT" if direction == "LONG" else "S2_BREAKDOWN"
    note = f"S2 3bar-brk rvol{rvol:.1f}x rsi{rsi:.0f}"
    return _size_and_check(symbol, direction, entry, stop, bar, cfg, setup, note)


# Back-compat alias (older callers / tests).
check_signal = check_s2


# ===========================================================================
# STRATEGY 1 - FIBONACCI EXTENSION CONTINUATION (SOP 3.1, Types 01/02/03)
# ===========================================================================
class FibEngine:
    """Strategy 1 - Fibonacci Extension Continuation (long form; shorts are
    a full mirror analysed on price-inverted bars).

    Per-side flow (SOP 3.1):
      1. Locate the latest A-B-C structure from 5m fractal pivots:
         A = pivot low, B = pivot high (impulse leg >= impulse_min_pct%),
         C = pullback pivot low.  Fib Extension Level 1 = C + (B - A),
         the 100% projection of A-B measured from C.
      2. ACTIVATION: a 5m CLOSE above Level 1 (wicks do not count), with
         the context gate: close above VWAP and EMA-20 rising.
      3. ZONE:
         Type 01 - first confirmed swing high B2 after the activation;
                   golden pocket = 0.5-0.618 retracement of C->B2.
         Type 02 - if price first extends to the 1.618 projection, the
                   golden pocket of C->extreme instead.
         Type 03 - Mother Fib = day's primary opening impulse (first
                   pivot low -> first pivot high -> first pullback low);
                   arms when price returns directly to the 0.236 level.
      4. TRIGGER: two consecutive red candles that dip into the zone and
         stay inside it, then a green candle closing inside the zone
         (2R+1G). Skip if the green range < 0.30% of its close (noise).
      5. ENTRY: the signal fires when a later bar trades through the buy
         stop = green high + 1 tick (within trigger_expiry_bars, else the
         setup is void). SL = green low - 1 tick; target = 1:3.

    The analysis is a deterministic replay of the full day's bars on every
    cycle (restart-safe, no hidden state). After a zone fails or the
    trigger expires, the side is dead for the day (SOP: wait for a fresh
    activation - conservative, zero-cost missed trades).
    """

    K = 2  # pivot strength (bars each side)

    def __init__(self, cfg):
        self.cfg = cfg
        self.watch = set()   # {(symbol, side)} with a live setup

    def update(self, symbol, bars):
        """Re-analyse the full day's 5m bars. Returns a Signal or None."""
        sig = self._analyze(symbol, bars, "LONG")
        if sig is None:
            sig = self._analyze(symbol, bars, "SHORT")
        return sig

    def _inv(self, bars):
        return [Bar(b.ts, -b.open, -b.high, -b.low, -b.close, b.volume)
                for b in bars]

    def _analyze(self, symbol, bars, side):
        cfg = self.cfg
        key = (symbol, side)
        n = len(bars)
        if n < max(int(cfg["min_bars"]), 10):
            self.watch.discard(key)
            return None
        if side == "SHORT":
            bars = self._inv(bars)
        closes = [b.close for b in bars]
        vols = [b.volume or 0 for b in bars]

        # shared data-quality gates
        day_high = max(b.high for b in bars)
        day_low = min(b.low for b in bars)
        if day_high <= day_low:
            return None
        if (day_high - day_low) / bars[-1].close * 100.0 < float(cfg["min_range_pct"]):
            self.watch.discard(key)
            return None
        if bars[-1].close * sum(vols) < float(cfg["min_turnover"]):
            self.watch.discard(key)
            return None

        ph, pl = pivot_points(bars, self.K)
        e20 = ema_series(closes, 20)
        # ---- 1+2. latest A-B-C whose Level 1 was ACTUALLY closed above ---
        # (newer swing structures without an activation are skipped, so the
        # golden-pocket pullback of a live setup cannot hijack the picker)
        chosen = None
        for bi in range(len(ph) - 1, -1, -1):
            b_i, b_px = ph[bi]
            lows_before = [p for p in pl if p[0] < b_i]
            lows_after = [p for p in pl if p[0] > b_i]
            if not lows_before or not lows_after:
                continue
            a_i, a_px = lows_before[-1]
            c_i, c_px = lows_after[0]
            leg = b_px - a_px
            if a_px <= 0 or leg <= 0:
                continue
            if leg / a_px * 100.0 < float(cfg["impulse_min_pct"]):
                continue
            if c_px <= a_px or b_px <= c_px:
                continue
            L1 = c_px + leg
            act_i = None
            for i in range(c_i + 1, n):
                if bars[i].close > L1:
                    act_i = i
                    break
            if act_i is None:
                continue        # Level 1 never closed above - try older leg
            vwap_act = vwap_series(bars[:act_i + 1])[-1]
            if bars[act_i].close <= vwap_act or \
                    e20[act_i] <= e20[max(0, act_i - 3)]:
                continue        # context gate failed (SOP: stand aside)
            chosen = (c_i, c_px, leg, L1, act_i)
            break
        if chosen is None:
            self.watch.discard(key)
            return None
        c_i, c_px, leg, L1, act_i = chosen
        L1618 = c_px + 1.618 * leg

        # ---- 3. zones -----------------------------------------------------
        zones = []                                   # (type, lo, hi, form_i)
        ext_i = max(range(act_i, n), key=lambda i: bars[i].high)
        ext_px = bars[ext_i].high
        b2 = next(((pi, px) for pi, px in ph if pi > act_i), None)
        if ext_px >= L1618 and ext_px > c_px:
            leg2 = ext_px - c_px
            zones.append(("T02", ext_px - 0.618 * leg2, ext_px - 0.5 * leg2,
                          ext_i))
        elif b2 is not None and b2[1] > L1:
            leg2 = b2[1] - c_px
            if leg2 > 0:
                zones.append(("T01", b2[1] - 0.618 * leg2, b2[1] - 0.5 * leg2,
                              b2[0] + self.K))
        # Type 03: Mother Fib from the day's opening impulse
        if pl and ph:
            a0 = pl[0]
            b0s = [p for p in ph if p[0] > a0[0]]
            c0s = ([p for p in pl if p[0] > b0s[0][0]] if b0s else [])
            if b0s and c0s:
                mleg = b0s[0][1] - a0[1]
                if mleg > 0 and a0[1] > 0 and \
                        mleg / a0[1] * 100.0 >= float(cfg["impulse_min_pct"]):
                    m236 = c0s[0][1] + 0.236 * mleg
                    pad_m = float(cfg["fib_tol_pct"]) / 100.0 * m236
                    zones.append(("T03", m236 - pad_m, m236 + pad_m, act_i))

        for ztype, zl, zh, form_i in zones:
            if zh > zl:
                sig = self._trigger(symbol, bars, side, ztype, zl, zh,
                                    form_i, n)
                if sig:
                    return sig
        self.watch.add(key)      # activation alive - keep polling
        return None

    def _trigger(self, symbol, bars, side, ztype, zl, zh, form_i, n):
        cfg = self.cfg
        key = (symbol, side)
        mid = (zl + zh) / 2.0
        pad = float(cfg["fib_tol_pct"]) / 100.0 * mid
        expiry = int(cfg["trigger_expiry_bars"])

        # latest 2R+1G whose green candle closes inside the zone
        best = None
        for g in range(max(form_i + 2, 2), n):
            r1, r2, gr = bars[g - 2], bars[g - 1], bars[g]
            if not (r1.close < r1.open and r2.close < r2.open
                    and gr.close > gr.open):
                continue
            if not (r1.low <= zh and r2.low <= zh):
                continue                       # reds must reach the zone
            if min(r1.low, r2.low) < zl - pad:
                continue                       # ...and stay inside it
            if not (zl - pad <= gr.close <= zh + pad):
                continue                       # green closes in the zone
            if gr.low < zl - pad:
                continue
            if gr.high - gr.low < float(cfg["green_min_range_pct"]) / 100.0 * gr.close:
                continue                       # noise-dominated green candle
            best = g
        if best is None:
            return None
        # zone must not have failed before the pattern
        for i in range(form_i, best):
            if bars[i].close < zl - pad:
                self.watch.discard(key)
                return None

        gr = bars[best]
        entry = round_tick(gr.high + 0.05, "up")
        stop = round_tick(gr.low - 0.05, "down")
        note = f"S1 {ztype} pocket {zl:.2f}-{zh:.2f} 2R+1G"
        # sizing + SOP 4.1 guards (analysis space; un-inverted on fill)
        sig = _size_and_check(symbol, "LONG", entry, stop, gr, self.cfg,
                              f"S1_FIB_{ztype}", note)
        if sig is None:
            return None

        # trigger: a later bar trades through the buy stop within expiry
        end = min(n, best + 1 + expiry)
        for j in range(best + 1, end):
            if bars[j].close < zl - pad:       # zone failed while waiting
                self.watch.discard(key)
                return None
            if bars[j].high >= entry:
                fill = bars[j]
                sig.date = fill.ts.date().isoformat()
                sig.sig_time = _hhmm(fill.ts)  # stamped on the fill bar
                if side == "SHORT":
                    sig.entry = round(-sig.entry, 2)
                    sig.stop = round(-sig.stop, 2)
                    sig.target = round(-sig.target, 2)
                    sig.direction = "SHORT"
                sig.reward_amt = abs(sig.target - sig.entry) * sig.qty
                return sig
        if n >= best + 1 + expiry:
            self.watch.discard(key)            # trigger expired -> void
        else:
            self.watch.add(key)                # still waiting
        return None


# ===========================================================================
# STRATEGY 3 - FIVE-TIMEFRAME CHOCH EXECUTION (SOP 3.3)
# ===========================================================================
class ChoChEngine:
    """Strategy 3 - Five-Timeframe CHoCH execution.

    * W1/D1 bias is computed from daily closes (structure proxy: the last
      confirmed swing high AND swing low are both higher = BULL, both
      lower = BEAR, anything else = no Strategy 3 that day - SOP Step 2).
    * H4 POI zones are normally produced by the AutoPoi engine every
      morning (poi_zones_auto.csv); zones you mark yourself in
      poi_zones.csv are merged on top and take precedence in spirit -
      both files are tradable. Only marked zones are tradable - floating
      price is never traded (SOP golden rule).
    * Steps 4-7 automated on the live feed: price taps the zone on M15
      data, the last closed H1 bar must confirm (bullish/bearish
      engulfing, rejection pin bar, or a CHoCH close beyond the prior
      three H1 bars), then an M15 candle must close in direction. Entry =
      that M15 close; stop = one tick beyond the POI extreme; target =
      nearest opposing POI if that is >= 2R, else fixed 3R.
    """

    def __init__(self, cfg, base_dir="."):
        self.cfg = cfg
        self.poi_path = os.path.join(base_dir,
                                     cfg.get("poi_file", "poi_zones.csv"))
        self.auto_path = os.path.join(base_dir,
                                      cfg.get("poi_auto_file",
                                              "poi_zones_auto.csv"))
        self._mtime = None
        self.zones = {}
        self.reload_zones()

    # ---------------- POI zone files (Step 3; auto + manual) -------------
    @staticmethod
    def _read_zone_file(path):
        zones = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if not row or row[0].strip().startswith("#"):
                        continue
                    if row[0].strip().lower() == "symbol":
                        continue
                    try:
                        sym = row[0].strip().upper().replace(".NS", "")
                        side = row[1].strip().upper()
                        lo, hi = float(row[2]), float(row[3])
                        date = row[4].strip() if len(row) > 4 else ""
                        if side not in ("LONG", "SHORT") or hi <= lo:
                            continue
                        zones.setdefault(sym, []).append(
                            {"side": side, "low": lo, "high": hi,
                             "date": date})
                    except Exception:
                        continue
        return zones

    def reload_zones(self):
        """Load zones from the manual file AND the AutoPoi-generated file
        (either may be absent). Re-reads whenever any mtime changes."""
        mts = []
        for p in (self.poi_path, self.auto_path):
            try:
                mts.append(os.path.getmtime(p))
            except OSError:
                mts.append(None)
        mts = tuple(mts)
        if mts == self._mtime:
            return
        self._mtime = mts
        zones = {}
        for path in (self.poi_path, self.auto_path):
            for sym, zs in self._read_zone_file(path).items():
                zones.setdefault(sym, []).extend(zs)
        self.zones = zones
        n = sum(len(v) for v in zones.values())
        if n:
            print(f"[S3] {n} POI zone(s) on {len(zones)} symbol(s) loaded")

    # ---------------- W1 / D1 bias (Steps 1-2) ---------------------------
    @staticmethod
    def _structure(closes, k=2):
        if len(closes) < 2 * (k + 1):
            return None
        ph, pl = pivot_points_on_values(closes, k)
        if len(ph) < 2 or len(pl) < 2:
            return None
        if ph[-1][1] > ph[-2][1] and pl[-1][1] > pl[-2][1]:
            return "BULL"
        if ph[-1][1] < ph[-2][1] and pl[-1][1] < pl[-2][1]:
            return "BEAR"
        return None

    def bias_of(self, symbol, daily_bars):
        if not daily_bars or len(daily_bars) < 60:
            return None
        weekly = {}
        for b in daily_bars:
            iso = b.ts.isocalendar()
            weekly[(iso[0], iso[1])] = b.close   # last close of the week
        wc = [weekly[key] for key in sorted(weekly)]
        w = self._structure(wc)
        d = self._structure([b.close for b in daily_bars[-120:]])
        if w == "BULL" and d == "BULL":
            return "BULL"
        if w == "BEAR" and d == "BEAR":
            return "BEAR"
        return None                              # disagreement -> no S3

    # ---------------- execution (Steps 4-7) ------------------------------
    def update(self, symbol, zones_all, bias, m15, h1, now):
        """Evaluate every marked zone of this symbol for today."""
        day = now.date().isoformat()
        out = []
        for side, want in (("LONG", "BULL"), ("SHORT", "BEAR")):
            if bias != want:
                continue
            for z in zones_all:
                if z["side"] != side:
                    continue
                if z.get("date") and z["date"] != day:
                    continue
                sig = self._eval_zone(symbol, z, zones_all, m15, h1, now,
                                      side)
                if sig:
                    out.append(sig)
        return out[0] if out else None

    def _eval_zone(self, symbol, z, zones_all, m15, h1, now, side):
        day = now.date().isoformat()
        zl, zh = z["low"], z["high"]            # REAL price edges
        if side == "SHORT":
            m15 = [Bar(b.ts, -b.open, -b.high, -b.low, -b.close, b.volume)
                   for b in m15]
            h1 = [Bar(b.ts, -b.open, -b.high, -b.low, -b.close, b.volume)
                  for b in h1]
            fz = {"low": -zh, "high": -zl}       # zone in analysis space
        else:
            fz = {"low": zl, "high": zh}
        tod = [b for b in m15 if b.ts.date().isoformat() == day]
        if len(tod) < 2:
            return None

        # Step 4: latest tap of the POI today (never trade floating price)
        tap = None
        for b in tod:
            if b.low <= fz["high"] and b.high >= fz["low"]:
                tap = b
        if tap is None:
            return None

        # Step 5: H1 confirmation at/after the tap (the prior H1 bar is
        # included so engulfing comparisons have a reference candle)
        h1b = [b for b in h1 if b.ts.date().isoformat() == day
               and b.ts + timedelta(minutes=60) >
               tap.ts - timedelta(minutes=60)]
        hb, kind = self._h1_confirm(h1b)
        if hb is None:
            return None

        # Step 6: M15 confirmation candle close in direction
        mc = None
        for i, b in enumerate(tod):
            if b.ts < hb.ts:
                continue
            prev_c = tod[i - 1].close if i > 0 else b.open
            if b.close > b.open and b.close > prev_c and b.close > fz["low"]:
                mc = b
                break
        if mc is None:
            return None

        # Step 7: sizing in REAL space - stop one tick beyond the POI
        # extreme, target = nearest opposing POI if >= 2R, else fixed 3R
        if side == "LONG":
            entry = round(mc.close, 2)
            stop = round_tick(zl - 0.05, "down")
        else:
            entry = round(-mc.close, 2)
            stop = round_tick(zh + 0.05, "up")
        risk = (entry - stop) if side == "LONG" else (stop - entry)
        if risk <= 0 or risk / entry > float(self.cfg["max_stop_pct"]) / 100.0:
            return None
        risk_amt = float(self.cfg["capital"]) * \
            float(self.cfg["risk_pct"]) / 100.0
        qty = int(risk_amt // risk)
        if qty < 1:
            return None
        target = None
        if side == "LONG":
            opps = [o for o in zones_all
                    if o["side"] == "SHORT" and o["low"] > entry]
            if opps:
                nearest = min(opps, key=lambda o: o["low"])
                if nearest["low"] - entry >= 2 * risk:
                    target = round_tick(nearest["low"], "down")
        else:
            opps = [o for o in zones_all
                    if o["side"] == "LONG" and o["high"] < entry]
            if opps:
                nearest = max(opps, key=lambda o: o["high"])
                if entry - nearest["high"] >= 2 * risk:
                    target = round_tick(nearest["high"], "up")
        if target is None:
            target = (round_tick(entry + 3.0 * risk, "nearest")
                      if side == "LONG"
                      else round_tick(entry - 3.0 * risk, "nearest"))
        reward_amt = abs(target - entry) * qty
        # SOP 4.1 capital-price rejection + cost hurdle
        if entry * qty > float(self.cfg["capital"]) or \
                reward_amt < float(self.cfg.get("cost_rt", 50.0)) + 50.0:
            return None
        ztxt = f"{zl:.2f}-{zh:.2f}"
        return Signal(symbol, side, day, _hhmm(mc.ts), entry, stop, target,
                      qty, round(risk, 2), round(risk_amt, 2),
                      round(reward_amt, 2),
                      f"S3 {kind} @ POI {ztxt}", "S3_CHOCH")

    @staticmethod
    def _h1_confirm(h1b):
        """(bar, kind) for the last closed H1 bar: engulfing / pin / CHoCH."""
        if len(h1b) < 2:
            return None, None
        hb, prev = h1b[-1], h1b[-2]
        body = abs(hb.close - hb.open)
        rng = hb.high - hb.low
        # bullish engulfing
        if (hb.close > hb.open and prev.close < prev.open
                and hb.close >= prev.open and hb.open <= prev.close):
            return hb, "engulfing"
        # rejection pin bar: long lower wick, close in the top third
        if rng > 0 and body > 0:
            lower = min(hb.open, hb.close) - hb.low
            if lower >= 2.0 * body and (hb.close - hb.low) / rng >= 0.66:
                return hb, "pin bar"
        # CHoCH proxy: close beyond the highs of the prior three H1 bars
        if len(h1b) >= 4 and hb.close > max(b.high for b in h1b[-4:-1]):
            return hb, "choch"
        return None, None


# ===========================================================================
# AUTO-POI - STRATEGY 3 ZONE MARKER (automates SOP Step 3)
# ===========================================================================
class AutoPoi:
    """Marks the H4 supply/demand zones for Strategy 3 automatically.

    Every morning (first scan cycle of the day) it rebuilds the zone map
    from Yahoo 1-hour history, so the trader never has to enter zones by
    hand. The discipline of the SOP is preserved: zones are derived only
    from data up to the PREVIOUS close, written once, and stay fixed for
    the whole session - floating price is never traded.

    How a zone is found (classic H4 supply / demand):
      1. Closed 1h bars are grouped into two H4 candles per NSE session:
         H4-A = 09:15-13:15 IST, H4-B = 13:15-15:30 IST.
      2. Fractal swing highs (k=2 confirmed) become SUPPLY zones
         (side SHORT): body-top .. high of the pivot candle.
         Fractal swing lows become DEMAND zones (side LONG):
         low .. body-bottom of the pivot candle.
      3. Fresh-only: if any later H4 candle CLOSED through the far edge
         of a zone, the zone is broken and discarded.
      4. Sanity filters: zone height <= s3_poi_max_zone_pct, distance
         from the last close <= s3_poi_proximity_pct, and only the
         nearest s3_poi_max_per_side zones per side are kept.
      5. Zones are written to poi_zones_auto.csv stamped with today's
         date, so they expire automatically at midnight and a fresh map
         is generated next session (idempotent: if the file already
         carries today's marker, nothing is re-fetched).
      6. Optional W1/D1 bias pre-filter: if a bias function is provided,
         only symbols whose bias agrees with the zone side are written
         (BULL -> demand zones, BEAR -> supply zones), which is exactly
         what the SOP Step 2 gate would do intraday anyway.

    Manual zones in poi_zones.csv still work alongside - both files are
    merged by ChoChEngine.reload_zones().
    """

    def __init__(self, cfg, provider, base_dir="."):
        self.cfg = cfg
        self.provider = provider
        self.out_path = os.path.join(base_dir,
                                     cfg.get("poi_auto_file",
                                             "poi_zones_auto.csv"))

    # ---------------- daily idempotence gate -----------------------------
    def _generated_date(self):
        """Date string the auto file was generated for, or None."""
        try:
            with open(self.out_path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if s.startswith("# generated:"):
                        return s.split(":", 1)[1].strip().split()[0]
        except OSError:
            pass
        return None

    def ensure_today(self, universe, now, bias_of=None):
        """Generate today's zone map if not done yet. Returns
        (zone_count, symbol_count) when freshly written, or None when
        the map already exists (skip - nothing is re-fetched)."""
        today = now.date().isoformat()
        if self._generated_date() == today:
            return None
        zones = self.detect(universe, now, bias_of=bias_of)
        n, n_sym = self.write(zones, today)
        print(f"[S3] auto-POI: {n} fresh zone(s) on {n_sym} symbol(s) "
              f"written to {os.path.basename(self.out_path)} for {today}")
        return n, n_sym

    # ---------------- H4 construction -------------------------------------
    @staticmethod
    def _h4_buckets(bars_1h):
        """Group closed 1h bars into two H4 candles per NSE session."""
        groups, order = {}, []
        for b in bars_1h:
            hm = b.ts.hour * 60 + b.ts.minute
            if hm < 9 * 60 + 15:                 # stray pre-open print
                continue
            key = (b.ts.date(), 0 if hm < 13 * 60 + 15 else 1)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(b)
        out = []
        for key in order:
            g = groups[key]
            out.append(Bar(g[0].ts, g[0].open, max(x.high for x in g),
                           min(x.low for x in g), g[-1].close,
                           sum(x.volume for x in g)))
        return out

    # ---------------- zone detection for one symbol -----------------------
    def _zones_from_h4(self, h4):
        lookback = int(self.cfg.get("s3_poi_lookback_days", 30))
        maxz = float(self.cfg.get("s3_poi_max_zone_pct", 2.0)) / 100.0
        prox = float(self.cfg.get("s3_poi_proximity_pct", 6.0)) / 100.0
        cap = int(self.cfg.get("s3_poi_max_per_side", 2))
        h4 = h4[-(lookback * 2):]
        if len(h4) < 12:
            return []
        last = h4[-1].close
        if last <= 0:
            return []
        piv_hi, _ = pivot_points_on_values([b.high for b in h4], 2)
        _, piv_lo = pivot_points_on_values([b.low for b in h4], 2)
        cands = []
        for idx, _v in piv_hi:                   # supply (SHORT side)
            p = h4[idx]
            hi, lo = p.high, max(p.open, p.close)
            if hi - lo < 0.01 * last / 100:      # degenerate flat top
                continue
            if any(b.close > hi for b in h4[idx + 1:]):
                continue                         # closed through -> broken
            cands.append({"side": "SHORT", "low": round(lo, 2),
                          "high": round(hi, 2), "d": abs(
                              (lo + hi) / 2 - last)})
        for idx, _v in piv_lo:                   # demand (LONG side)
            p = h4[idx]
            lo, hi = p.low, min(p.open, p.close)
            if hi - lo < 0.01 * last / 100:
                continue
            if any(b.close < lo for b in h4[idx + 1:]):
                continue
            cands.append({"side": "LONG", "low": round(lo, 2),
                          "high": round(hi, 2), "d": abs(
                              (lo + hi) / 2 - last)})
        keep = [z for z in cands
                if (z["high"] - z["low"]) / ((z["low"] + z["high"]) / 2)
                <= maxz and z["d"] / last <= prox]
        final = []
        for side in ("LONG", "SHORT"):
            sz = sorted((z for z in keep if z["side"] == side),
                        key=lambda z: z["d"])
            final.extend(sz[:cap])
        for z in final:
            z.pop("d", None)
        return final

    # ---------------- full-universe detection ------------------------------
    def detect(self, universe, now, bias_of=None):
        """{sym: [zones]} for the whole universe from 1h history."""
        period = str(self.cfg.get("s3_poi_hist_period", "60d"))
        h1 = self.provider.get_intraday(sorted(universe), "60m", period,
                                        now=now)
        if not h1:
            raise ProviderUnavailable("no 1h history returned for POI "
                                      "detection")
        today = now.date().isoformat()
        bias = {}
        if bias_of is not None:
            try:
                # same period as _scan_s3's bias pass so both gates agree
                daily = self.provider.get_daily(sorted(universe), "1y",
                                                now=now)
                bias = {s: bias_of(s, daily.get(s)) for s in h1}
            except Exception as e:
                print(f"[S3] auto-POI bias pre-filter skipped ({e})")
                bias = {}
        zones = {}
        for s, bars in h1.items():
            if not bars:
                continue
            h4 = [b for b in self._h4_buckets(bars)
                  if b.ts.date().isoformat() < today]
            zs = self._zones_from_h4(h4)
            if not zs:
                continue
            b = bias.get(s)
            if bias:                 # pre-filter ran -> enforce it
                if b == "BULL":      # SOP Step 2: trade demand only
                    zs = [z for z in zs if z["side"] == "LONG"]
                elif b == "BEAR":    # trade supply only
                    zs = [z for z in zs if z["side"] == "SHORT"]
                else:                # None: W1/D1 disagree -> no S3 today
                    continue
            # pre-filter skipped (daily data down) -> keep both sides;
            # the intraday bias gate in _scan_s3 decides later
            if zs:
                zones[s] = zs
        return zones

    # ---------------- CSV output -------------------------------------------
    def write(self, zones, today):
        """Write the map with a generated-marker line; returns
        (zone_count, symbol_count)."""
        with open(self.out_path, "w", newline="", encoding="utf-8") as f:
            f.write("# AUTO-GENERATED by scanner v%s - DO NOT EDIT\n"
                    % VERSION)
            f.write("# generated: %s (rebuilt every morning before the "
                    "first scan)\n" % today)
            f.write("# H4 supply/demand zones for Strategy 3; they expire "
                    "at midnight.\n")
            f.write("# Manual additions go in poi_zones.csv (merged on "
                    "top).\n")
            f.write("symbol,side,zone_low,zone_high,date\n")
            n = 0
            for sym in sorted(zones):
                for z in zones[sym]:
                    f.write("%s,%s,%.2f,%.2f,%s\n"
                            % (sym, z["side"], z["low"], z["high"], today))
                    n += 1
        return n, len(zones)


# ===========================================================================
# DATA PROVIDERS
# ===========================================================================
class ProviderUnavailable(Exception):
    pass


class NseBlockedError(Exception):
    pass


def yf_sym(sym):
    return sym if "." in sym else sym + ".NS"


class NseFast:
    """Fast lane: one HTTP request to NSE returns quotes for the whole
    NIFTY 100 (LTP / day high / day low / volume). Used for tick-level
    candidate detection between bar confirmations. Many cloud/server IPs are
    blocked by NSE (HTTP 403) - home broadband usually works."""
    BASE = "https://www.nseindia.com"
    HDRS = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0 Safari/537.36"),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": BASE + "/market-data/live-equity-market",
    }

    def __init__(self, cfg=None, timeout=10):
        self.timeout = timeout
        self._cookies = None

    def _http(self, url):
        import http.cookiejar
        if self._cookies is None:
            self._cookies = http.cookiejar.CookieJar()
            self._opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self._cookies))
        req = urllib.request.Request(url, headers=self.HDRS)
        with self._opener.open(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    def warmup(self):
        self._http(self.BASE + "/market-data/live-equity-market")

    def get_snapshot(self):
        """{NSE_SYMBOL: {ltp, high, low, vol, prev_close}} for NIFTY 100."""
        try:
            data = self._http(
                self.BASE + "/api/equity-stockIndices?index=" +
                urllib.parse.quote("NIFTY 100"))
        except urllib.error.HTTPError as e:
            raise NseBlockedError(f"NSE returned HTTP {e.code}")
        out = {}
        for row in data.get("data", []):
            sym = row.get("symbol")
            if not sym or sym.startswith("NIFTY"):
                continue
            out[sym] = {
                "ltp": row.get("lastPrice") or 0,
                "high": row.get("dayHigh") or 0,
                "low": row.get("dayLow") or 0,
                "vol": row.get("totalTradedVolume") or 0,
                "prev_close": row.get("previousClose") or 0,
            }
        return out

    def get_quotes(self, symbols):
        try:
            snap = self.get_snapshot()
        except NseBlockedError:
            raise
        except Exception as e:
            print(f"[NSE] snapshot failed: {e}")
            return {}
        return {s: snap[s] for s in symbols if s in snap}


class YahooProvider:
    """Slow lane / fallback: 5-minute OHLCV bars from Yahoo Finance.
    Works from most networks; data can lag a few minutes - which is exactly
    why the SOP forces a broker-terminal verification before any entry."""
    name = "yahoo"

    def __init__(self, cfg=None):
        try:
            import yfinance as yf  # noqa
        except Exception as e:
            raise ProviderUnavailable(
                f"yfinance not available ({e}). Run: pip install yfinance")
        self.yf = yf

    @staticmethod
    def _parse(sub, sym):
        import pandas as pd  # noqa - only for isinstance checks / dropna
        sub = sub.dropna(subset=["Close"])
        bars = []
        for idx, row in sub.iterrows():
            ts = idx.to_pydatetime()
            ts = ts.replace(tzinfo=IST) if ts.tzinfo is None else ts.astimezone(IST)
            try:
                v = int(float(row.get("Volume") or 0))
            except Exception:
                v = 0
            bars.append(Bar(ts, float(row["Open"]), float(row["High"]),
                            float(row["Low"]), float(row["Close"]), v))
        return bars

    @staticmethod
    def _closed_cutoff(now, minutes):
        """Newest CLOSED bar-start timestamp for a `minutes` interval."""
        cutoff = now.replace(second=0, microsecond=0)
        cutoff -= timedelta(minutes=cutoff.minute % minutes)
        return cutoff - timedelta(minutes=minutes)

    def _download(self, symbols, period, interval):
        return self.yf.download([yf_sym(s) for s in symbols], period=period,
                                interval=interval, group_by="ticker",
                                auto_adjust=False, progress=False,
                                threads=True)

    @staticmethod
    def _split(df, symbols):
        multi = hasattr(df.columns, "levels") and \
            getattr(df.columns, "nlevels", 1) > 1
        for s in symbols:
            try:
                sub = df[yf_sym(s)] if multi else df
                if sub is None or len(sub) == 0:
                    continue
                yield s, sub
            except Exception:
                continue

    def get_bars(self, symbols, now=None):
        """Today's 5m bars for a set of NSE symbols. Incomplete (forming)
        bars are dropped so signals are only confirmed on closed bars."""
        out = {}
        if not symbols:
            return out
        try:
            df = self._download(symbols, "1d", "5m")
        except Exception as e:
            print(f"[YF] batch download failed: {e}")
            return out
        if df is None or len(df) == 0:
            return out
        now = now or now_ist()
        cutoff = self._closed_cutoff(now, 5)
        for s, sub in self._split(df, symbols):
            try:
                bars = [b for b in self._parse(sub, s) if b.ts <= cutoff]
                if bars:
                    out[s] = bars
            except Exception:
                continue
        return out

    def get_intraday(self, symbols, interval="15m", period="5d", now=None):
        """{sym: [Bar]} closed bars for a custom intraday interval
        (15m / 60m). Used by Strategy 3 (H1 + M15 confirmation)."""
        out = {}
        if not symbols:
            return out
        mins = int(interval.rstrip("m")) if interval.endswith("m") else 60
        try:
            df = self._download(symbols, period, interval)
        except Exception as e:
            print(f"[YF] {interval} download failed: {e}")
            return out
        if df is None or len(df) == 0:
            return out
        now = now or now_ist()
        cutoff = self._closed_cutoff(now, mins)
        for s, sub in self._split(df, symbols):
            try:
                bars = [b for b in self._parse(sub, s) if b.ts <= cutoff]
                if bars:
                    out[s] = bars
            except Exception:
                continue
        return out

    def get_daily(self, symbols, period="1y", now=None):
        """{sym: [Bar]} daily bars - used for the Strategy 3 W1/D1 bias."""
        out = {}
        if not symbols:
            return out
        try:
            df = self._download(symbols, period, "1d")
        except Exception as e:
            print(f"[YF] daily download failed: {e}")
            return out
        if df is None or len(df) == 0:
            return out
        for s, sub in self._split(df, symbols):
            try:
                bars = self._parse(sub, s)
                if bars:
                    out[s] = bars
            except Exception:
                continue
        return out

    def get_bars_history(self, symbol, date_str, now=None):
        """Historical 5m bars for one trading day (used by the journal to
        back-fill outcomes). Yahoo keeps ~60 days of 5m data."""
        start = datetime.strptime(date_str, "%Y-%m-%d")
        end = start + timedelta(days=1)
        df = self.yf.Ticker(yf_sym(symbol)).history(
            start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
            interval="5m", auto_adjust=False)
        if df is None or len(df) == 0:
            return []
        return self._parse(df, symbol)


def make_bar_provider(cfg):
    mode = str(cfg.get("data_mode", "auto")).lower()
    if mode == "nse":
        # even in NSE mode, bar confirmation comes from Yahoo
        return YahooProvider(cfg)
    return YahooProvider(cfg)


def fast_candidates(quotes):
    """Tick-level candidate detection from NSE quotes: a stock sitting at (or
    within 5 bps of) its day high is a LONG candidate; at its day low, SHORT.
    These are NOT signals - bar confirmation must still pass all gates."""
    cands = set()
    for sym, q in (quotes or {}).items():
        try:
            ltp, high, low = float(q["ltp"]), float(q["high"]), float(q["low"])
        except Exception:
            continue
        if ltp <= 0 or high <= low or high <= 0:
            continue
        if ltp >= high - 0.0005 * high:
            cands.add(sym)
        elif ltp <= low + 0.0005 * low:
            cands.add(sym)
    return cands

# ===========================================================================
# TRADE JOURNAL - self-generating, self-updating logbook with day verdicts
# ===========================================================================
TRADE_COLS = ["TradeID", "Date", "SignalTime", "Symbol", "Direction", "Setup",
              "Entry", "StopLoss", "Target", "Qty", "RiskPerShare", "RiskAmt",
              "RewardAmt", "RR", "Mode", "Status", "ExitPrice", "ExitTime",
              "ExitReason", "Result", "PnL_R", "PnL_Amt", "UpdatedAt", "Notes"]

SUMMARY_COLS = ["Date", "Trades", "Wins", "Losses", "Flats", "Open",
                "WinRatePct", "NetR", "NetPnlAmt", "BreakerTripped",
                "DayVerdict", "Notes"]


class TradeJournal:
    """One class that does everything the journal needs:

      * AUTO-GENERATE  - creates trade_journal.csv / daily_summary.csv /
        journal_state.json on first use (also self-heals a deleted file).
      * RECORD         - every confirmed signal becomes an OPEN trade row.
      * TRACK          - every cycle each OPEN trade is checked against its
        stop and target using closed 5m bars (and, in NSE mode, live quotes);
        outcome is written back: WIN / LOSS / EOD square-off.
      * VERDICT        - daily_summary.csv is rebuilt after every closed
        trade. The DayVerdict answers "did the trades fail today?":
            SUCCESS - day closed with net positive R
            FAILED  - day closed with net negative R, OR a circuit breaker
                      tripped (loss streak / day loss limit)
            FLAT    - net zero
        A trailing '*' marks a verdict that is still live (trades open).
      * SURVIVE        - open trades persist in journal_state.json; on the
        next start (or via journal.py) missed sessions are back-filled from
        price history and the verdicts are refreshed.
    """

    def __init__(self, base_dir=".", cfg=None, notify=None):
        self.cfg = cfg or dict(DEFAULT_CONFIG)
        self.notify = notify if notify is not None else (lambda m: None)
        j = self.cfg.get("journal") or {}
        self.dir = os.path.join(base_dir, j.get("folder", "journal"))
        self.trades_csv = os.path.join(self.dir, "trade_journal.csv")
        self.summary_csv = os.path.join(self.dir, "daily_summary.csv")
        self.state_json = os.path.join(self.dir, "journal_state.json")
        self.state = {"open": [], "day_verdict_sent": {}, "breaker_notified": {}}
        self.ensure_files()

    # ---------------- file management (auto-generation) -------------------
    def ensure_files(self):
        os.makedirs(self.dir, exist_ok=True)
        if not os.path.exists(self.trades_csv):
            self._write_csv(self.trades_csv, TRADE_COLS, [])
            print(f"[JOURNAL] created {self.trades_csv}")
        if not os.path.exists(self.summary_csv):
            self._write_csv(self.summary_csv, SUMMARY_COLS, [])
            print(f"[JOURNAL] created {self.summary_csv}")
        if os.path.exists(self.state_json):
            try:
                with open(self.state_json, "r", encoding="utf-8") as f:
                    self.state = json.load(f)
                self.state.setdefault("open", [])
                self.state.setdefault("day_verdict_sent", {})
                self.state.setdefault("breaker_notified", {})
            except Exception as e:
                print(f"[JOURNAL] state file unreadable ({e}); rebuilding")
                self.state = {"open": [], "day_verdict_sent": {},
                              "breaker_notified": {}}
                self._rebuild_state_from_csv()
        else:
            self._rebuild_state_from_csv()
        self.state.setdefault("squareoff_alert_sent", {})
        self._save_state()

    def _rebuild_state_from_csv(self):
        """CSV is the source of truth: restore open-trade state from it."""
        opens = [r for r in self._read_trades() if r.get("Status") == "OPEN"]
        self.state["open"] = [self._row_to_open(r) for r in opens]
        if opens:
            print(f"[JOURNAL] restored {len(opens)} open trade(s) from CSV")

    @staticmethod
    def _row_to_open(r):
        return {"trade_id": r["TradeID"], "date": r["Date"],
                "signal_time": r["SignalTime"], "symbol": r["Symbol"],
                "direction": r["Direction"], "entry": r["Entry"],
                "stop": r["StopLoss"], "target": r["Target"], "qty": r["Qty"],
                "risk_ps": r["RiskPerShare"],
                "shadow": r.get("Mode", "LIVE") == "SHADOW"}

    @staticmethod
    def _write_csv(path, cols, rows):
        tmp = path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        os.replace(tmp, path)          # atomic write

    @staticmethod
    def _read_csv(path):
        if not os.path.exists(path):
            return []
        with open(path, "r", newline="", encoding="utf-8") as f:
            return [dict(r) for r in csv.DictReader(f)]

    def _read_trades(self):
        rows = self._read_csv(self.trades_csv)
        for r in rows:                    # v3.3: pre-Mode / blank rows = LIVE
            if not r.get("Mode"):
                r["Mode"] = "LIVE"
        return rows

    def _save_state(self):
        tmp = self.state_json + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=1)
        os.replace(tmp, self.state_json)

    # ---------------- recording -------------------------------------------
    def has_trade(self, trade_id):
        if any(o["trade_id"] == trade_id for o in self.state["open"]):
            return True
        return any(r.get("TradeID") == trade_id for r in self._read_trades())

    def record_signal(self, sig):
        """Append a confirmed signal as an OPEN trade. Dedup by TradeID."""
        if self.has_trade(sig.trade_id):
            return None
        row = {
            "TradeID": sig.trade_id, "Date": sig.date,
            "SignalTime": sig.sig_time, "Symbol": sig.symbol,
            "Direction": sig.direction, "Setup": sig.setup,
            "Entry": fmt2(sig.entry), "StopLoss": fmt2(sig.stop),
            "Target": fmt2(sig.target), "Qty": sig.qty,
            "RiskPerShare": fmt2(sig.risk_ps), "RiskAmt": fmt2(sig.risk_amt),
            "RewardAmt": fmt2(sig.reward_amt),
            "RR": f"1:{self.cfg.get('rr', 3.0):g}", "Mode": "LIVE",
            "Status": "OPEN", "ExitPrice": "", "ExitTime": "",
            "ExitReason": "", "Result": "", "PnL_R": "", "PnL_Amt": "",
            "UpdatedAt": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
            "Notes": sig.note,
        }
        rows = self._read_trades()
        rows.append(row)
        self._write_csv(self.trades_csv, TRADE_COLS, rows)
        self.state["open"].append(self._row_to_open(row))
        self._save_state()
        print(f"[JOURNAL] OPEN  {sig.trade_id} entry {sig.entry} "
              f"SL {sig.stop} TGT {sig.target} qty {sig.qty}")
        return sig.trade_id

    def record_shadow(self, sig, reason=""):
        """v3.3 study mode: journal a confirmed signal that was NOT alerted
        (daily cap reached / concurrency cap held) as a SHADOW row. Shadow
        rows are tracked to their outcome like normal trades, but they are
        excluded from day stats, verdicts and the circuit breaker - they
        exist purely to study and improve the strategies. Dedup by TradeID.
        Returns the trade id or None when the signal is already journaled."""
        if self.has_trade(sig.trade_id):
            return None
        row = {
            "TradeID": sig.trade_id, "Date": sig.date,
            "SignalTime": sig.sig_time, "Symbol": sig.symbol,
            "Direction": sig.direction, "Setup": sig.setup,
            "Entry": fmt2(sig.entry), "StopLoss": fmt2(sig.stop),
            "Target": fmt2(sig.target), "Qty": sig.qty,
            "RiskPerShare": fmt2(sig.risk_ps), "RiskAmt": fmt2(sig.risk_amt),
            "RewardAmt": fmt2(sig.reward_amt),
            "RR": f"1:{self.cfg.get('rr', 3.0):g}", "Mode": "SHADOW",
            "Status": "OPEN", "ExitPrice": "", "ExitTime": "",
            "ExitReason": "", "Result": "", "PnL_R": "", "PnL_Amt": "",
            "UpdatedAt": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
            "Notes": ("SHADOW study-only (not alerted): " + reason).strip()
            if reason else "SHADOW study-only (not alerted)",
        }
        rows = self._read_trades()
        rows.append(row)
        self._write_csv(self.trades_csv, TRADE_COLS, rows)
        self.state["open"].append(self._row_to_open(row))
        self._save_state()
        print(f"[JOURNAL] SHADOW {sig.trade_id} entry {sig.entry} "
              f"SL {sig.stop} TGT {sig.target} (study-only, no alert)")
        return sig.trade_id

    # ---------------- outcome tracking -------------------------------------
    def on_quote(self, symbol, quote, now=None):
        """NSE fast-lane check between bar cycles: the last traded price is
        an actual print, so LTP beyond a level means the level traded."""
        now = now or now_ist()
        for t in list(self.state["open"]):
            if t["symbol"] != symbol or t["date"] != now.date().isoformat():
                continue
            try:
                ltp = float(quote.get("ltp") or 0)
                high, low = float(quote.get("high") or 0), float(quote.get("low") or 0)
            except Exception:
                continue
            if ltp <= 0:
                continue
            stop, target = float(t["stop"]), float(t["target"])
            if t["direction"] == "LONG":
                both = high >= target and low <= stop
                hit_stop, hit_tgt = ltp <= stop, ltp >= target
            else:
                both = low <= target and high >= stop
                hit_stop, hit_tgt = ltp >= stop, ltp <= target
            if both:   # cannot tell which came first -> conservative LOSS
                return self.finalize(t, stop, "STOP_HIT", now, "both levels seen; conservative")
            if hit_stop:
                return self.finalize(t, stop, "STOP_HIT", now)
            if hit_tgt:
                return self.finalize(t, target, "TARGET_HIT", now)

    def on_bars(self, symbol, bars, now=None):
        """Bar-precise outcome check for every OPEN trade of this symbol,
        using only bars AFTER the entry bar (the 0.10% stop buffer guarantees
        the signal bar itself cannot trigger anything)."""
        now = now or now_ist()
        sq = cfg_squareoff(self.cfg)
        out = None
        for t in list(self.state["open"]):
            if t["symbol"] != symbol:
                continue
            seq = [b for b in bars
                   if b.ts.date().isoformat() == t["date"]
                   and b.ts.time() > parse_hhmm(t["signal_time"])]
            if not seq:
                continue
            stop, target = float(t["stop"]), float(t["target"])
            long = t["direction"] == "LONG"
            res = None
            for b in seq:
                hit_stop = (b.low <= stop) if long else (b.high >= stop)
                hit_tgt = (b.high >= target) if long else (b.low <= target)
                if hit_stop and hit_tgt:      # ambiguous bar -> LOSS first
                    res = self.finalize(t, stop, "STOP_HIT", b.ts,
                                        "bar touched both levels; conservative")
                    break
                if hit_stop:
                    res = self.finalize(t, stop, "STOP_HIT", b.ts)
                    break
                if hit_tgt:
                    res = self.finalize(t, target, "TARGET_HIT", b.ts)
                    break
            if not res:
                # still open: square off at/after the SOP square-off time
                session_over = (t["date"] < now.date().isoformat() or
                                now.time() >= sq)
                if session_over:
                    res = self.finalize(
                        t, seq[-1].close, "EOD_SQUAREOFF", seq[-1].ts,
                        None if t["date"] == now.date().isoformat()
                        else "auto-finalized after session end")
            out = out or res
        return out

    def finalize(self, t, exit_price, reason, ts, note=None):
        """Write the outcome of one trade, then refresh the day verdict."""
        rows = self._read_trades()
        row = None
        for r in rows:
            if r.get("TradeID") == t["trade_id"] and r.get("Status") == "OPEN":
                row = r
                break
        if row is None:
            return None
        entry = float(row["Entry"])
        risk_ps = float(row["RiskPerShare"]) or 1.0
        qty = int(float(row["Qty"] or 0))
        pnl_ps = (exit_price - entry) if row["Direction"] == "LONG" else (entry - exit_price)
        pnl_r = pnl_ps / risk_ps if risk_ps else 0.0
        pnl_amt = pnl_ps * qty
        result = "WIN" if pnl_r > 0.05 else ("LOSS" if pnl_r < -0.05 else "FLAT")
        row["Status"] = "CLOSED"
        row["ExitPrice"] = fmt2(exit_price)
        row["ExitTime"] = _hhmm(ts)
        row["ExitReason"] = reason
        row["Result"] = result
        row["PnL_R"] = f"{pnl_r:.3f}"
        row["PnL_Amt"] = fmt2(pnl_amt)
        row["UpdatedAt"] = now_ist().strftime("%Y-%m-%d %H:%M:%S")
        if note:
            row["Notes"] = (row.get("Notes", "") + " | " + note).strip(" |")
        self._write_csv(self.trades_csv, TRADE_COLS, rows)
        self.state["open"] = [o for o in self.state["open"]
                              if o["trade_id"] != t["trade_id"]]
        self._save_state()
        emoji = "✅" if result == "WIN" else ("❌" if result == "LOSS" else "➖")
        if t.get("shadow"):
            # v3.3: study-only rows settle silently - no Telegram, console tag
            print(f"[JOURNAL] SHADOW-CLOSE {t['trade_id']} {reason} -> {result} "
                  f"{pnl_r:+.2f}R (study-only, not counted in day stats)")
        else:
            self.notify(f"{emoji} {row['Symbol']} {row['Direction']} -> {reason} "
                        f"-> {result} {pnl_r:+.2f}R (Rs {pnl_amt:+.2f}) @ {fmt2(exit_price)}")
            print(f"[JOURNAL] CLOSE {t['trade_id']} {reason} -> {result} "
                  f"{pnl_r:+.2f}R (Rs {pnl_amt:+.2f})")
        self.recompute_day(row["Date"])
        return result

    # ---------------- day verdict / summary --------------------------------
    def recompute_day(self, date_str, now=None):
        """Rebuild one day's row in daily_summary.csv and return it.
        v3.3: SHADOW rows are study-only - they never enter the day's
        stats, verdict or breaker; the count is noted separately."""
        now = now or now_ist()
        all_rows = [r for r in self._read_trades() if r.get("Date") == date_str]
        rows = [r for r in all_rows if r.get("Mode", "LIVE") != "SHADOW"]
        shadow_n = len(all_rows) - len(rows)
        if not rows:
            return None
        closed = [r for r in rows if r.get("Status") != "OPEN"]
        open_n = len(rows) - len(closed)
        wins = sum(1 for r in closed if r.get("Result") == "WIN")
        losses = sum(1 for r in closed if r.get("Result") == "LOSS")
        flats = len(closed) - wins - losses
        net_r = sum(float(r["PnL_R"] or 0) for r in closed)
        net_amt = sum(float(r["PnL_Amt"] or 0) for r in closed)
        wr = (100.0 * wins / len(closed)) if closed else 0.0

        # circuit breakers (SOP): loss streak and/or day loss limit
        j = self.cfg.get("journal") or {}
        max_streak = int(j.get("max_consecutive_losses", 2) or 0)
        limit_r = float(j.get("daily_loss_limit_R", -2.0) or 0)
        limit_amt = float(j.get("daily_loss_limit_amt", 0) or 0)
        streak = worst = 0
        for r in sorted(closed, key=lambda r: r.get("ExitTime", "")):
            if r.get("Result") == "LOSS":
                streak += 1
                worst = max(worst, streak)
            else:
                streak = 0
        tripped = ((max_streak > 0 and worst >= max_streak) or
                   (limit_r < 0 and net_r <= limit_r) or
                   (limit_amt > 0 and net_amt <= -abs(limit_amt)))

        if not closed and open_n:
            verdict, live = "PENDING", True
        else:
            if tripped:
                verdict = "FAILED"
            elif net_r > 0.05:
                verdict = "SUCCESS"
            elif net_r < -0.05:
                verdict = "FAILED"
            else:
                verdict = "FLAT"
            # a verdict is provisional while trades are open OR while the
            # session is still running (more trades can still happen)
            session_running = (date_str == now.date().isoformat() and
                               now.time() < cfg_squareoff(self.cfg))
            live = open_n > 0 or session_running
        vlabel = verdict + ("*" if live else "")

        notes = []
        if tripped:
            notes.append(f"circuit breaker: {worst}-loss streak / day limit {limit_r:g}R")
        if open_n:
            notes.append("live")
        if shadow_n:
            notes.append(f"{shadow_n} shadow (study-only)")
        new = {
            "Date": date_str, "Trades": len(rows), "Wins": wins,
            "Losses": losses, "Flats": flats, "Open": open_n,
            "WinRatePct": f"{wr:.1f}", "NetR": f"{net_r:+.3f}",
            "NetPnlAmt": fmt2(net_amt), "BreakerTripped": "YES" if tripped else "NO",
            "DayVerdict": vlabel, "Notes": "; ".join(notes),
        }
        summary = [r for r in self._read_csv(self.summary_csv)
                   if r.get("Date") != date_str]
        summary.append(new)
        summary.sort(key=lambda r: r.get("Date", ""))
        self._write_csv(self.summary_csv, SUMMARY_COLS, summary)

        # notify-once guards
        if tripped and date_str == now.date().isoformat() and \
                not self.state["breaker_notified"].get(date_str):
            self.state["breaker_notified"][date_str] = True
            self._save_state()
            self.notify(f"⛔ CIRCUIT BREAKER {date_str}: stop trading for the "
                        f"day (net {net_r:+.2f}R). SOP rule.")
        final_telegram = (open_n == 0 and not live and
                          date_str == now.date().isoformat() and
                          now.time() >= cfg_squareoff(self.cfg) and
                          not self.state["day_verdict_sent"].get(date_str))
        if final_telegram:
            self.state["day_verdict_sent"][date_str] = True
            self._save_state()
            self.notify(f"📊 {date_str} DAY VERDICT: {verdict} | "
                        f"{len(closed)} trades | {wins}W/{losses}L | "
                        f"net {net_r:+.2f}R (Rs {net_amt:+.2f})")
        return new

    def breaker_tripped_today(self, now=None):
        now = now or now_ist()
        for r in self._read_csv(self.summary_csv):
            if r.get("Date") == now.date().isoformat():
                return r.get("BreakerTripped") == "YES"
        return False

    # ---------------- catch-up / reporting ---------------------------------
    def catch_up(self, hist_provider, now=None):
        """Finalize OPEN trades using price history. Runs at every scanner
        start and inside journal.py, so a PC that was switched off still
        gets accurate outcomes and verdicts."""
        now = now or now_ist()
        sq = cfg_squareoff(self.cfg)
        touched = set()
        for t in list(self.state["open"]):
            sym, date = t["symbol"], t["date"]
            session_over = (date < now.date().isoformat() or
                            (date == now.date().isoformat() and now.time() >= sq))
            try:
                bars = hist_provider.get_bars_history(sym, date, now=now)
            except Exception as e:
                print(f"[JOURNAL] history fetch failed for {sym} {date}: {e}")
                continue
            if not bars:
                if session_over:
                    print(f"[JOURNAL] no history data for {sym} {date} "
                          f"(kept OPEN - will retry / mark manually)")
                continue
            res = self.on_bars(sym, bars, now=now)
            if res:
                touched.add(date)
        for d in sorted(touched):
            self.recompute_day(d, now=now)

    def report(self, now=None, last_days=7):
        """Human-readable journal report (console / Telegram digest)."""
        now = now or now_ist()
        today = now.date().isoformat()
        L = []
        L.append("=" * 66)
        L.append(f" TRADE JOURNAL REPORT  -  {now.strftime('%Y-%m-%d %H:%M')} IST")
        L.append("=" * 66)
        opens = self.state["open"]
        if opens:
            live_o = [o for o in opens if not o.get("shadow")]
            shad_o = [o for o in opens if o.get("shadow")]
            L.append(f"OPEN TRADES ({len(live_o)} live, {len(shad_o)} shadow)")
            for o in live_o:
                L.append(f"  {o['symbol']:<12} {o['direction']:<5} entry "
                         f"{o['entry']} SL {o['stop']} TGT {o['target']} "
                         f"qty {o['qty']}  [{o['date']} {o['signal_time']}]")
            for o in shad_o:
                L.append(f"  [SHADOW] {o['symbol']:<6} {o['direction']:<5} entry "
                         f"{o['entry']} SL {o['stop']} TGT {o['target']} "
                         f"[{o['date']} {o['signal_time']}]")
        else:
            L.append("OPEN TRADES: none")
        trades = self._read_trades()
        today_rows = [r for r in trades if r.get("Date") == today]
        if today_rows:
            s = self.recompute_day(today, now=now) or {}
            L.append("")
            L.append(f"TODAY ({today}): {s.get('Trades', 0)} trades | "
                     f"{s.get('Wins', 0)}W/{s.get('Losses', 0)}L | "
                     f"net {s.get('NetR', '0.000')}R "
                     f"(Rs {s.get('NetPnlAmt', '0.00')})  "
                     f"-> VERDICT: {s.get('DayVerdict', 'PENDING')}")
        summary = [r for r in self._read_csv(self.summary_csv)][-last_days:]
        if summary:
            L.append("")
            L.append(f"LAST {len(summary)} DAY(S)")
            L.append(f"  {'Date':<12}{'Tr':>3}{'W':>3}{'L':>3}{'NetR':>9}"
                     f"{'Rs':>10}  Verdict")
            for r in summary:
                L.append(f"  {r['Date']:<12}{r['Trades']:>3}{r['Wins']:>3}"
                         f"{r['Losses']:>3}{r['NetR']:>9}{r['NetPnlAmt']:>10}"
                         f"  {r['DayVerdict']}")
        closed = [r for r in trades if r.get("Status") != "OPEN"
                  and r.get("Mode", "LIVE") != "SHADOW"]
        shad = [r for r in trades if r.get("Mode", "LIVE") == "SHADOW"]
        if closed:
            wr = 100.0 * sum(1 for r in closed if r["Result"] == "WIN") / len(closed)
            tot = sum(float(r["PnL_R"] or 0) for r in closed)
            L.append("")
            L.append(f"OVERALL: {len(closed)} closed trades | win rate "
                     f"{wr:.0f}% | total {tot:+.2f}R | avg {tot/len(closed):+.2f}R/trade")
            L.append(f"(1:3 structure gross breakeven = 25% win rate; SOP net "
                    f"breakeven ~30% incl. costs)")
        if shad:
            sh_closed = [r for r in shad if r.get("Status") != "OPEN"]
            sh_w = sum(1 for r in sh_closed if r.get("Result") == "WIN")
            sh_l = sum(1 for r in sh_closed if r.get("Result") == "LOSS")
            sh_r = sum(float(r["PnL_R"] or 0) for r in sh_closed)
            L.append("")
            L.append(f"SHADOW STUDY (not counted in day stats): "
                     f"{len(shad)} journaled | {len(sh_closed)} settled "
                     f"({sh_w}W/{sh_l}L, {sh_r:+.2f}R) | "
                     f"{len(shad) - len(sh_closed)} still open")
        L.append("")
        L.append(f"files: {self.trades_csv}")
        L.append(f"       {self.summary_csv}")
        return "\n".join(L)

def cfg_squareoff(cfg):
    return parse_hhmm(cfg.get("squareoff", "15:10"))


# ===========================================================================
# SELF-LEARNING ENGINE (v3.2)
# Studies the last N closed trades in the journal and adapts the scanner:
# benched strategies/directions stop emitting signals; healthy ones keep
# firing. Rule-based and fully transparent - every gate carries its reason.
# ===========================================================================
def _fam_of(setup):
    """Setup tag -> strategy family: S1_FIB_T01 -> S1, S2_BREAKOUT -> S2,
    S3_CHOCH -> S3."""
    return (setup or "").split("_")[0].upper() or "?"


def _in_signal_window(sig, cfg):
    """SOP entry window for EVERY strategy: scan_start <= signal time <=
    entry_cutoff (09:30-13:30 by default). Strategy 2 checks this itself;
    this central filter also covers S1/S3 confirmations."""
    try:
        t = parse_hhmm(sig.sig_time)
    except Exception:
        return True
    return cfg["scan_start_t"] <= t <= cfg["entry_cutoff_t"]


class SelfLearner:
    """Learns from the trade journal and adapts the scanner every day.

    Every refresh() it reads the last `lookback_trades` (default 30) CLOSED
    trades from trade_journal.csv and computes:
      * overall form       - wins / losses / win rate / net R / avg R
      * per-setup form     - S1 / S2 / S3 families (Setup column prefix)
      * per-direction form - LONG vs SHORT
      * per-hour form      - entry hour buckets (09..13)
      * recent form        - the last 10 closed trades ("moving trend")
    From those it builds today's GATES (transparent, rule-based):
      * a setup family is BENCHED when it has >= min_trades_to_gate closed
        trades and (win rate < block_setup_wr_below OR net R <=
        block_setup_r_below), or when its recent form collapses (>=
        min_recent_trades of the last recent_trades with win rate <
        recent_form_wr_below);
      * a direction is BENCHED when it has >= min_direction_trades closed
        trades with win rate < block_direction_wr_below.
    Benched = that family/direction emits no new signals; open trades are
    still monitored to their normal outcome. Gates re-compute after every
    closed trade, so a benched family can earn its way back the same day,
    and everything resets next morning from the fresh journal.

    The snapshot is saved to journal/learning_state.json - inside the
    journal folder, so the GitHub Actions workflow commits it and learning
    persists across cloud runs. `report_text()` renders the EOD digest and
    `digest()` Telegrams it once per day.
    """

    def __init__(self, journal, cfg, notify=None):
        self.journal = journal
        self.cfg = cfg
        self.notify = notify if notify is not None else (lambda m: None)
        sl = cfg.get("self_learning") or {}
        self.enabled = bool(sl.get("enabled", True))
        # v3.3: observe-only by default - the gates are still computed and
        # reported ("would-bench") but never enforced, so the system keeps
        # producing signals/data while it is being tested. Set
        # self_learning.blocking=true in config.json to restore v3.2 gating.
        self.blocking = bool(sl.get("blocking", False))
        self.lookback = int(sl.get("lookback_trades", 30) or 30)
        self.recent_n = int(sl.get("recent_trades", 10) or 10)
        self.min_setup_n = int(sl.get("min_trades_to_gate", 8) or 8)
        self.block_setup_wr = float(sl.get("block_setup_wr_below", 30.0))
        self.block_setup_r = float(sl.get("block_setup_r_below", -2.0))
        self.min_recent_n = int(sl.get("min_recent_trades", 6) or 6)
        self.recent_block_wr = float(sl.get("recent_form_wr_below", 20.0))
        self.min_dir_n = int(sl.get("min_direction_trades", 10) or 10)
        self.block_dir_wr = float(sl.get("block_direction_wr_below", 25.0))
        self.path = os.path.join(journal.dir, "learning_state.json")
        self.stats = {}
        self.gates = {"blocked_setups": {}, "blocked_directions": {},
                      "preferred": ""}
        self.prev = {}
        self._load()

    # ---------------- state file -------------------------------------------
    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.prev = json.load(f)
            except Exception as e:
                print(f"[LEARN] state file unreadable ({e}); rebuilding")
                self.prev = {}

    def _save(self, snap):
        if snap == self.prev:            # write only on real change
            return
        self.prev = snap
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=1)
            os.replace(tmp, self.path)   # atomic write
        except Exception as e:
            print(f"[LEARN] could not save state ({e})")

    # ---------------- analysis ----------------------------------------------
    @staticmethod
    def _bucket(rows):
        n = len(rows)
        wins = sum(1 for r in rows if r.get("Result") == "WIN")
        losses = sum(1 for r in rows if r.get("Result") == "LOSS")
        r_sum = sum(float(r.get("PnL_R") or 0) for r in rows)
        return {"n": n, "wins": wins, "losses": losses,
                "wr": round(100.0 * wins / n, 1) if n else 0.0,
                "r": round(r_sum, 2),
                "avg_r": round(r_sum / n, 3) if n else 0.0}

    def refresh(self, now=None):
        """Re-read the journal, rebuild stats + gates. One CSV read - cheap
        enough to run every scan cycle, so gates adapt intraday too."""
        now = now or now_ist()
        self.stats = {}
        self.gates = {"blocked_setups": {}, "blocked_directions": {},
                      "preferred": ""}
        if not self.enabled:
            return self.stats
        closed = [r for r in self.journal._read_trades()
                  if r.get("Status") != "OPEN" and r.get("Result")
                  and r.get("Mode", "LIVE") != "SHADOW"]
        closed.sort(key=lambda r: (r.get("Date", ""), r.get("ExitTime", "")))
        studied = closed[-self.lookback:]
        if not studied:
            self._save(self._snapshot(now))
            return self.stats
        self.stats["overall"] = self._bucket(studied)
        self.stats["recent"] = self._bucket(studied[-self.recent_n:])
        streak = 0                       # current losing streak
        for r in reversed(studied):
            if r.get("Result") == "LOSS":
                streak += 1
            else:
                break
        self.stats["loss_streak"] = streak
        for key, grouper in (
                ("setups", lambda r: _fam_of(r.get("Setup"))),
                ("directions", lambda r: r.get("Direction", "?")),
                ("hours", lambda r: (r.get("SignalTime") or "?")[:2])):
            buckets = {}
            for r in studied:
                buckets.setdefault(grouper(r), []).append(r)
            self.stats[key] = {k: self._bucket(v)
                               for k, v in sorted(buckets.items())}
        # per-family RECENT form: how each family did inside the last
        # recent_n closed trades (the moving trend used by gate rule 2)
        fam_recent = {}
        for r in studied[-self.recent_n:]:
            fam_recent.setdefault(_fam_of(r.get("Setup")), []).append(r)
        self.stats["setup_recent"] = {k: self._bucket(v)
                                      for k, v in sorted(fam_recent.items())}
        self._build_gates()
        self._save(self._snapshot(now))
        return self.stats

    def _build_gates(self):
        s = self.stats
        # 1) benched strategy families - slow form over the studied window
        for fam, b in s.get("setups", {}).items():
            if fam not in ("S1", "S2", "S3") or b["n"] < self.min_setup_n:
                continue
            if (b["wr"] < self.block_setup_wr
                    or b["r"] <= self.block_setup_r):
                self.gates["blocked_setups"][fam] = (
                    f"{b['wr']:.0f}% WR / {b['r']:+.1f}R over last "
                    f"{b['n']} trades (rule: bench below "
                    f"{self.block_setup_wr:g}% WR or {self.block_setup_r:g}R "
                    f"on {self.min_setup_n}+ trades)")
        # 2) recent-form collapse (the moving trend): a family whose last
        #    few trades crumbled is benched even if the 30-trade view still
        #    looks acceptable
        for fam, b in s.get("setup_recent", {}).items():
            if (fam in self.gates["blocked_setups"]
                    or fam not in ("S1", "S2", "S3")):
                continue
            if b["n"] >= self.min_recent_n and b["wr"] < self.recent_block_wr:
                self.gates["blocked_setups"][fam] = (
                    f"recent form {b['wr']:.0f}% WR over last {b['n']} "
                    f"trades (rule: bench below {self.recent_block_wr:g}% "
                    f"on {self.min_recent_n}+)")
        # 3) benched directions
        for d, b in s.get("directions", {}).items():
            if d in ("LONG", "SHORT") and b["n"] >= self.min_dir_n \
                    and b["wr"] < self.block_dir_wr:
                self.gates["blocked_directions"][d] = (
                    f"{b['wr']:.0f}% WR over last {b['n']} trades (rule: "
                    f"bench below {self.block_dir_wr:g}% on "
                    f"{self.min_dir_n}+)")
        # 4) advisory: top performer among the healthy families
        cand = [(b["r"], fam) for fam, b in s.get("setups", {}).items()
                if fam in ("S1", "S2", "S3") and b["n"] >= 3
                and fam not in self.gates["blocked_setups"]]
        if cand:
            self.gates["preferred"] = max(cand)[1]

    def _snapshot(self, now):
        return {"as_of": now.date().isoformat(),
                "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "config": {"lookback_trades": self.lookback,
                           "recent_trades": self.recent_n},
                "stats": self.stats,
                "gates": self.gates,
                "digest_sent": (self.prev.get("digest_sent", {})
                                if isinstance(self.prev, dict) else {})}

    # ---------------- gating -------------------------------------------------
    def allow(self, sig):
        """(ok, reason): is this signal allowed under the learned gates?
        v3.3: in observe-only mode (self_learning.blocking=false, the
        default) every signal passes - the gates are reported, not
        enforced."""
        if not self.enabled or not self.blocking:
            return True, ""
        fam = _fam_of(sig.setup)
        why = self.gates["blocked_setups"].get(fam)
        if why:
            return False, f"{fam} benched by self-learner: {why}"
        why = self.gates["blocked_directions"].get(sig.direction)
        if why:
            return False, f"{sig.direction} benched by self-learner: {why}"
        return True, ""

    # ---------------- reporting ----------------------------------------------
    def status_line(self):
        if not self.enabled:
            return "[LEARN] self-learning disabled (config: self_learning)"
        mode = ("BLOCKING" if self.blocking else "OBSERVE-ONLY (no benching)")
        o = self.stats.get("overall")
        if not o:
            return (f"[LEARN] mode: {mode} | no closed trades to learn "
                    f"from yet - all gates open")
        tag = "benched" if self.blocking else "would-bench"
        benched = ", ".join(sorted(self.gates["blocked_setups"])) or "none"
        dirs = ", ".join(sorted(self.gates["blocked_directions"])) or "none"
        pref = self.gates.get("preferred") or "-"
        return (f"[LEARN] mode: {mode} | last {o['n']} closed: "
                f"{o['wins']}W/{o['losses']}L ({o['wr']:.0f}% WR, {o['r']:+.1f}R) | "
                f"{tag}: {benched} | {tag} directions: {dirs} | "
                f"top performer: {pref}")

    def report_text(self):
        if not self.enabled:
            return ""
        o = self.stats.get("overall")
        if not o:
            return ""    # nothing learned yet - no report, no digest noise
        L = [f"SELF-LEARNING REPORT (studied last {o['n']} closed trades)",
             f"  overall : {o['wins']}W/{o['losses']}L | win rate "
             f"{o['wr']:.0f}% | net {o['r']:+.2f}R | avg "
             f"{o['avg_r']:+.2f}R/trade"]
        rec = self.stats.get("recent")
        if rec and rec["n"]:
            L.append(f"  recent {rec['n']:>2}: {rec['wins']}W/"
                     f"{rec['losses']}L | {rec['wr']:.0f}% WR | "
                     f"{rec['r']:+.2f}R   <- moving trend")
        L.append(f"  losing streak: {self.stats.get('loss_streak', 0)}")
        for fam, b in self.stats.get("setups", {}).items():
            if fam not in ("S1", "S2", "S3"):
                continue
            bench_tag = "BENCHED - no signals" if self.blocking \
                else "WOULD-BENCH - blocking off"
            tag = f"  [{bench_tag}]" if fam in self.gates["blocked_setups"] else ""
            star = "  <- top performer" \
                if fam == self.gates.get("preferred") else ""
            L.append(f"  {fam}: {b['wins']}W/{b['losses']}L | "
                     f"{b['wr']:.0f}% WR | {b['r']:+.2f}R over "
                     f"{b['n']}{tag}{star}")
        for d, b in self.stats.get("directions", {}).items():
            if d not in ("LONG", "SHORT"):
                continue
            tag = f"  [{bench_tag}]" if d in self.gates["blocked_directions"] else ""
            L.append(f"  {d}: {b['wins']}W/{b['losses']}L | "
                     f"{b['wr']:.0f}% WR | {b['r']:+.2f}R over "
                     f"{b['n']}{tag}")
        hrs = self.stats.get("hours", {})
        parts = [f"{h}:xx {b['wr']:.0f}%({b['n']})"
                 for h, b in hrs.items() if b["n"]]
        if parts:
            L.append("  by entry hour: " + " | ".join(parts))
        verb = "benched" if self.blocking else "would-bench"
        for fam, why in self.gates["blocked_setups"].items():
            L.append(f"  gate: {fam} {verb} - {why}")
        for d, why in self.gates["blocked_directions"].items():
            L.append(f"  gate: {d} {verb} - {why}")
        if not self.blocking:
            L.append("  (observe-only mode: self_learning.blocking=false - "
                     "no signal is being stopped)")
        # v3.3: shadow study section - the would-have-been signals that
        # were journaled after the daily cap
        try:
            shad = [r for r in self.journal._read_trades()
                    if r.get("Mode", "LIVE") == "SHADOW"]
        except Exception:
            shad = []
        if shad:
            sh_closed = [r for r in shad if r.get("Status") != "OPEN"]
            sh_w = sum(1 for r in sh_closed if r.get("Result") == "WIN")
            sh_l = sum(1 for r in sh_closed if r.get("Result") == "LOSS")
            sh_r = sum(float(r.get("PnL_R") or 0) for r in sh_closed)
            L.append(f"  shadow study: {len(shad)} journaled, "
                     f"{len(sh_closed)} settled ({sh_w}W/{sh_l}L, "
                     f"{sh_r:+.2f}R), {len(shad) - len(sh_closed)} open")
        return "\n".join(L)

    def digest(self, now=None):
        """Telegram the learning digest once per day (EOD). Returns text."""
        now = now or now_ist()
        txt = self.report_text()
        if not txt:
            return ""
        today = now.date().isoformat()
        sent = (self.prev.get("digest_sent", {})
                if isinstance(self.prev, dict) else {})
        if not sent.get(today):
            self.notify("\U0001f9e0 " + txt)
            sent[today] = True
            snap = self._snapshot(now)
            snap["digest_sent"] = sent
            self._save(snap)
        return txt


# ===========================================================================
# SCANNER LOOP
# ===========================================================================
class Scanner:
    def __init__(self, cfg, base_dir="."):
        self.cfg = cfg
        self.base_dir = base_dir
        # v3.2.1: weekly NIFTY 100 constituent refresh BEFORE the file is
        # read - removes delisted/replaced symbols without manual edits.
        # Never raises: on any failure the shipped file stays in use.
        try:
            refresh_universe(cfg, base_dir=base_dir, notify=send_telegram)
        except Exception as e:
            print(f"[UNIVERSE] refresh skipped ({e})")
        self.universe = load_universe(os.path.join(base_dir, cfg["universe_file"]))
        if not self.universe:
            raise SystemExit("Universe is empty - check universe_nifty100.txt")
        self.fast = None
        mode = str(cfg.get("data_mode", "auto")).lower()
        if mode in ("nse", "auto"):
            try:
                nf = NseFast(cfg)
                nf.warmup()
                nf.get_snapshot()
                self.fast = nf
                print(f"[DATA] NSE fast lane OK ({len(self.universe)} symbols)")
            except Exception as e:
                if mode == "nse":
                    print(f"[DATA] NSE unavailable ({e}); falling back to Yahoo")
                else:
                    print(f"[DATA] NSE blocked/failed ({e}); Yahoo-only mode")
        self.bars = make_bar_provider(cfg)   # raises if yfinance missing
        self.journal = TradeJournal(base_dir=base_dir, cfg=cfg,
                                    notify=send_telegram)
        # v3.2 self-learning: load the journal's history and build today's
        # gates (benched strategies/directions) before any scanning starts
        self.learner = SelfLearner(self.journal, cfg, notify=send_telegram)
        try:
            self.learner.refresh()
        except Exception as e:
            print(f"[LEARN] initial refresh failed ({e}); gates open")
        # strategy engines
        self.fib = FibEngine(cfg)                       # Strategy 1
        self.s3 = (ChoChEngine(cfg, base_dir=base_dir)   # Strategy 3
                   if cfg.get("s3_enabled", True) else None)
        self.auto_poi = (AutoPoi(cfg, self.bars, base_dir=base_dir)
                         if self.s3 is not None
                         and cfg.get("s3_auto_poi", True) else None)
        self._s3_bias = {}
        self._s3_bias_date = None
        self._cycle = 0

    def _open_symbols(self):
        return {o["symbol"] for o in self.journal.state["open"]}

    def _scan_symbols(self, quotes):
        """Symbols that need fresh 5m bars this cycle: NSE fast-lane
        candidates + open trades + Strategy 1 watch symbols + a rotating
        slice of the full universe (so every symbol is bar-checked
        periodically even in NSE fast-lane mode - S1 pullbacks happen
        away from the day high, where candidate detection cannot see
        them).

        v3.2.2: fib.watch holds (symbol, side) TUPLES - it is projected
        to plain symbols before the union and the result is coerced to
        strings only, so sorted() can never mix types again (a mixed
        tuple/str sort crashed live runs the moment an S1 setup went
        live)."""
        watch = {s for (s, _side) in self.fib.watch}
        if quotes:
            need = (fast_candidates(quotes) | self._open_symbols()
                    | watch)
            rs = int(self.cfg.get("rotate_slice", 25) or 0)
            if rs > 0 and self.universe:
                seg = (self._cycle * rs) % len(self.universe)
                need |= set(self.universe[seg:seg + rs])
            self._cycle += 1
        else:
            need = set(self.universe) | self._open_symbols() | watch
        return {str(s) for s in need}

    def _entries_allowed(self, now):
        """SOP 3.4 / Phase V discipline: daily trade cap (10), 2 concurrent
        positions. v3.3: SHADOW rows are study-only and never count."""
        today = now.date().isoformat()
        day_n = sum(1 for r in self.journal._read_trades()
                    if r.get("Date") == today
                    and r.get("Mode", "LIVE") != "SHADOW")
        open_n = sum(1 for o in self.journal.state["open"]
                     if not o.get("shadow"))
        if day_n >= int(self.cfg.get("max_trades_per_day", 10)):
            return False, f"daily entry cap reached ({day_n} trades today)"
        if open_n >= int(self.cfg.get("max_concurrent_positions", 2)):
            return False, f"max concurrent positions held ({open_n})"
        return True, ""

    def _cap_notice(self, now):
        """v3.2: one-time Telegram/console notice when the daily trade cap
        is hit. Open trades keep being monitored to their outcome.
        v3.3: with shadow_after_cap on, further signals keep being journaled
        as SHADOW rows (no alerts) so the day still produces study data."""
        today = now.date().isoformat()
        cap = int(self.cfg.get("max_trades_per_day", 10))
        day_n = sum(1 for r in self.journal._read_trades()
                    if r.get("Date") == today
                    and r.get("Mode", "LIVE") != "SHADOW")
        if day_n < cap or self.journal.state.get("cap_notified", {}).get(today):
            return
        self.journal.state.setdefault("cap_notified", {})[today] = True
        self.journal._save_state()
        if self.cfg.get("shadow_after_cap", True):
            msg = (f"\U0001f6d1 DAILY CAP {today}: {day_n}/{cap} trades taken - "
                   f"no more ALERTS today. The scanner keeps scanning and "
                   f"journals further signals as SHADOW rows for study "
                   f"(not alerted, not counted). Open trades are monitored "
                   f"and squared off at {self.cfg.get('squareoff', '15:10')} "
                   f"IST as usual.")
        else:
            msg = (f"\U0001f6d1 DAILY CAP {today}: {day_n}/{cap} trades taken - "
                   f"no more signals today. Open trades keep being monitored "
                   f"and square off at {self.cfg.get('squareoff', '15:10')} IST "
                   f"as usual.")
        print("\n" + msg + "\n")
        send_telegram(msg)

    def run_once(self, now=None):
        now = now or now_ist()
        if now.weekday() >= 5:
            print(f"[SCAN] {now.strftime('%a %H:%M')} - weekend, market closed")
            return
        quotes = {}
        if self.fast is not None:
            try:
                quotes = self.fast.get_quotes(self.universe)
            except NseBlockedError as e:
                print(f"[DATA] NSE now blocked ({e}); switching to Yahoo-only")
                self.fast = None

        # symbols that need bar data: NSE candidates + open trades + S1
        # watch-list + a rotating slice so every symbol is bar-checked
        # periodically even in NSE fast-lane mode (S1 pullbacks happen away
        # from the day high, where candidate detection cannot see them).
        # v3.2.2: the need set is built by _scan_symbols() and is ALWAYS
        # strings-only - fib.watch holds (symbol, side) tuples and a mixed
        # tuple/str sort here crashed live runs (TypeError: '<' not
        # supported between instances of 'tuple' and 'str').
        bars = self.bars.get_bars(sorted(self._scan_symbols(quotes)),
                                  now=now)

        # 1) journal maintenance on fresh bars (outcomes first, always)
        for sym in sorted(bars):
            self.journal.on_bars(sym, bars[sym], now=now)
        if quotes:
            for sym, q in quotes.items():
                if sym in self._open_symbols():
                    self.journal.on_quote(sym, q, now=now)

        # 2) fresh signals. v3.3: NOTHING stops generation any more while
        #    testing - the learner is observe-only by default and a tripped
        #    circuit breaker only warns (both restore-able via config), so
        #    every day produces a full studyable sample. The 10/day cap is
        #    enforced at ALERT time; once it is hit, further confirmed
        #    signals are journaled as SHADOW rows (no alert) for study.
        self.learner.refresh(now=now)
        fresh = []
        tripped = self.journal.breaker_tripped_today(now=now)
        breaker_blocks = tripped and bool(
            (self.cfg.get("journal") or {}).get("breaker_blocking", False))
        if tripped and not breaker_blocks:
            print("[SOP] circuit breaker tripped today - observe mode: "
                  "signals keep flowing for study "
                  "(journal.breaker_blocking=false)")
        if breaker_blocks:
            print("[SOP] CIRCUIT BREAKER active for today - "
                  "no new entries, open trades still monitored")
        else:
            # Strategy 3 first (own data flow: POI zones, 15m/60m, bias)
            fresh += self._scan_s3(now)
            for sym in sorted(bars):
                b = bars[sym]
                sig = None
                if self.cfg.get("s1_enabled", True):
                    sig = self.fib.update(sym, b)      # Strategy 1
                if sig is None:
                    sig = check_s2(sym, b, self.cfg)   # Strategy 2
                if sig:
                    fresh.append(sig)

        # v3.2 engine-wide entry window: no signals before scan_start or
        # after entry_cutoff (13:30) for ANY strategy (S2 self-gates; this
        # also drops S1/S3 confirmations that land after the cutoff)
        n_all = len(fresh)
        fresh = [s for s in fresh if _in_signal_window(s, self.cfg)]
        if len(fresh) != n_all:
            print(f"[SOP] dropped {n_all - len(fresh)} signal(s) outside the "
                  f"{self.cfg['scan_start']}-{self.cfg['entry_cutoff']} "
                  f"entry window")
        self._cap_notice(now)

        for sig in fresh:
            if sig.symbol in self._open_symbols():
                continue        # SOP 3.4: one position per instrument
            ok, why = self._entries_allowed(now)
            if ok:
                ok2, why2 = self.learner.allow(sig)   # v3.2 self-learning
                if not ok2:
                    print(f"[LEARN] signal suppressed - {why2}")
                    continue
                tid = self.journal.record_signal(sig)
                if tid:
                    self._alert(sig)
            elif self.cfg.get("shadow_after_cap", True):
                # v3.3 study mode: cap/concurrency reached - journal the
                # signal silently as SHADOW (no alert), still tracked to
                # its outcome for next-day strategy improvement
                self.journal.record_shadow(sig, reason=why)

        # 3) status line
        self._status_line(now)

    def _scan_s3(self, now):
        """Strategy 3 data flow: auto-POI zones -> W1/D1 bias -> 15m/60m."""
        if not (self.cfg.get("s3_enabled", True) and self.s3 is not None):
            return []
        # SOP Step 3, automated: build today's H4 zone map if not done yet
        if self.auto_poi is not None:
            try:
                res = self.auto_poi.ensure_today(self.universe, now,
                                                 bias_of=self.s3.bias_of)
                if res is not None:
                    n, n_sym = res
                    send_telegram(
                        f"\U0001f4cd S3 auto-POI for {now.date().isoformat()}: "
                        f"{n} fresh H4 zone(s) on {n_sym} symbol(s) after "
                        f"W1/D1 bias alignment. Strategy 3 watchlist ready.")
            except Exception as e:
                print(f"[S3] auto-POI generation failed ({e}); manual "
                      f"{self.s3.poi_path} still honoured")
        self.s3.reload_zones()
        zones = {s: z for s, z in self.s3.zones.items() if s in self.universe}
        if not zones:
            return []
        syms = sorted(zones)
        today = now.date().isoformat()
        if self._s3_bias_date != today:
            try:
                daily = self.bars.get_daily(syms, now=now)
                self._s3_bias = {s: self.s3.bias_of(s, daily.get(s))
                                 for s in syms}
                self._s3_bias_date = today
                n = sum(1 for v in self._s3_bias.values() if v)
                print(f"[S3] W1/D1 bias: {n}/{len(syms)} zone symbol(s) "
                      f"aligned; the rest are no-trade today (SOP Step 2)")
            except Exception as e:
                print(f"[S3] daily data unavailable ({e}); Strategy 3 paused")
                self._s3_bias, self._s3_bias_date = {}, today
        if not self._s3_bias:
            return []
        try:
            m15 = self.bars.get_intraday(syms, "15m", "2d", now=now)
            h1 = self.bars.get_intraday(syms, "60m", "5d", now=now)
        except Exception as e:
            print(f"[S3] intraday fetch failed: {e}")
            return []
        out = []
        for s in syms:
            sig = self.s3.update(s, zones[s], self._s3_bias.get(s),
                                 m15.get(s, []), h1.get(s, []), now)
            if sig:
                out.append(sig)
        return out

    def _alert(self, sig):
        arrow = "🟢 LONG" if sig.direction == "LONG" else "🔴 SHORT"
        msg = (f"{arrow} CONFIRMED | {sig.symbol} | {sig.date} {sig.sig_time} IST\n"
               f"setup {sig.setup} | entry {sig.entry:.2f} | SL {sig.stop:.2f} | "
               f"TGT {sig.target:.2f} ({self.cfg.get('rr', 3.0):g}R) | "
               f"qty {sig.qty} | risk Rs {sig.risk_amt:.2f}\n"
               f"{sig.note}\n"
               f"VERIFY in broker terminal + SOP 12-point checklist first.")
        print("\n" + "!" * 66)
        print(msg)
        print("!" * 66 + "\n")
        send_telegram(msg)

    def _status_line(self, now):
        all_rows = [r for r in self.journal._read_trades()
                    if r.get("Date") == now.date().isoformat()]
        rows = [r for r in all_rows if r.get("Mode", "LIVE") != "SHADOW"]
        shad_n = len(all_rows) - len(rows)      # v3.3: study-only rows
        open_n = sum(1 for o in self.journal.state["open"]
                     if not o.get("shadow"))
        closed = [r for r in rows if r.get("Status") != "OPEN"]
        net = sum(float(r["PnL_R"] or 0) for r in closed)
        wins = sum(1 for r in closed if r["Result"] == "WIN")
        losses = sum(1 for r in closed if r["Result"] == "LOSS")
        verdict = "PENDING"
        s = self.journal.recompute_day(now.date().isoformat(), now=now)
        if s:
            verdict = s.get("DayVerdict", "PENDING")
        shad_txt = f" (+{shad_n} shadow)" if shad_n else ""
        print(f"[{now.strftime('%H:%M')}] signals today: {len(rows)}{shad_txt} "
              f"({wins}W/{losses}L, {open_n} open) | day: {net:+.2f}R "
              f"| verdict: {verdict}")

    def run(self):
        n_zones = sum(len(v) for v in (self.s3.zones if self.s3 else {}).values())
        print(f"[SCANNER v{VERSION}] {len(self.universe)} symbols | mode="
              f"{('nse+yahoo' if self.fast else 'yahoo')} | journal="
              f"{self.journal.dir}")
        print(f"[SCANNER] strategies: S1 fib="
              f"{'ON' if self.cfg.get('s1_enabled', True) else 'off'} | "
              f"S2 momentum | S3 choch="
              f"{'ON' if self.s3 else 'off'} ({n_zones} POI zones, "
              f"auto-POI={'ON' if self.auto_poi is not None else 'off'})")
        print("[SCANNER] alerts only - it never places orders.")
        print(f"[SCANNER] discipline: max "
              f"{self.cfg.get('max_trades_per_day', 10)} trades/day | max "
              f"{self.cfg.get('max_concurrent_positions', 2)} concurrent | "
              f"entries {self.cfg['scan_start']}-"
              f"{self.cfg['entry_cutoff']} IST")
        if self.cfg.get("shadow_after_cap", True):
            print("[SCANNER] v3.3 study mode: after the daily cap, further "
                  "signals are journaled as SHADOW rows (no alerts)")
        print("[SCANNER] learner " +
              ("BLOCKING signals (self_learning.blocking=true)"
               if getattr(self.learner, "blocking", False)
               else "OBSERVE-ONLY - never blocks signals (v3.3)"))
        try:
            print(self.learner.status_line())
        except Exception:
            pass
        # back-fill anything the last session missed
        try:
            self.journal.catch_up(self.bars)
        except Exception as e:
            print(f"[JOURNAL] catch-up failed: {e}")
        interval = int(self.cfg.get("scan_interval_min", 5))
        sq_time = cfg_squareoff(self.cfg)
        alert_time = self.cfg.get("squareoff_alert_t") or parse_hhmm("15:05")
        exit_time = self.cfg.get("exit_after_t") or parse_hhmm("15:35")

        while True:
            now = now_ist()
            if now.weekday() >= 5:
                print("[SCANNER] weekend - market closed. Exiting; "
                      "journal state saved.")
                break
            # AUTOMATION: stop scanning at/after the square-off time
            if now.time() >= sq_time or now.time() >= exit_time:
                print(f"\n[SOP] Time is {now.strftime('%H:%M')}. Reached "
                      f"square-off time ({sq_time.strftime('%H:%M')}).")
                print("[SOP] Stopping scans to process EOD square-offs.")
                break
            # 15:05 heads-up / square-off directive (once per day)
            today = now.date().isoformat()
            if (alert_time <= now.time() < sq_time
                    and not self.journal.state["squareoff_alert_sent"]
                    .get(today)):
                self.journal.state["squareoff_alert_sent"][today] = True
                self.journal._save_state()
                live_o = [o for o in self.journal.state["open"]
                          if not o.get("shadow")]
                n_open = len(live_o)
                shad_n = len(self.journal.state["open"]) - n_open
                extra = (f" {shad_n} study-only SHADOW row(s) square off in "
                         f"the journal automatically (no action needed)."
                         if shad_n else "")
                send_telegram(
                    f"⏰ {today} {alert_time.strftime('%H:%M')} IST - "
                    f"SQUARE-OFF DIRECTIVE: close all {n_open} open MIS "
                    f"position(s) NOW. Auto square-off at "
                    f"{sq_time.strftime('%H:%M')}; no new entries from "
                    f"here." + extra)
                print("[SOP] square-off directive sent")
            self.run_once(now=now)
            target = now.replace(second=0, microsecond=0)
            target += timedelta(minutes=(interval - target.minute % interval))
            wait = (target - now_ist()).total_seconds() + 5
            print(f"[SCANNER] next scan at {target.strftime('%H:%M')} "
                  f"(sleeping {max(wait, 5):.0f}s)")
            try:
                time.sleep(max(wait, 5))
            except KeyboardInterrupt:
                print("\n[SCANNER] stopped by user. Journal state saved.")
                break

    # ---------------- EOD square-off automation --------------------------
    def run_eod(self):
        """15:10 flow: square off every OPEN trade in the journal, refresh
        the day verdicts, print the final report. Runs after the scan loop
        breaks (local) and after --once when started past the cutoff."""
        now = now_ist()
        print("\n" + "=" * 66)
        print(f"[SOP] automated end-of-session processing at "
              f"{now.strftime('%H:%M')} IST")
        # 1) history-based square-off + verdict refresh
        try:
            self.journal.catch_up(self.bars, now=now)
        except Exception as e:
            print(f"[JOURNAL] catch-up failed ({e})")
            send_telegram(f"⚠️ EOD journal update issue: {e}")
        # 2) belt-and-braces: force square-off anything still OPEN
        try:
            self._force_squareoff(now=now)
        except Exception as e:
            print(f"[JOURNAL] force square-off failed: {e}")
        # 3) final report
        print("\n" + self.journal.report(now=now))
        # 4) v3.2 self-learning digest: re-learn after today's settlements,
        #    print the report and Telegram it (once per day)
        try:
            self.learner.refresh(now=now)
            lr = self.learner.digest(now=now)
            if lr:
                print("\n" + lr)
        except Exception as e:
            print(f"[LEARN] digest failed ({e})")
        print("\n[SOP] EOD square-off + journal update complete.")

    def _force_squareoff(self, now=None):
        """Finalize today's still-OPEN trades at the best known price:
        NSE LTP first (fresh print), then the last closed 5m bar. Trades
        that cannot be priced stay OPEN and are flagged for journal.py."""
        now = now or now_ist()
        opens = list(self.journal.state["open"])
        if not opens:
            return
        syms = sorted({o["symbol"] for o in opens})
        today = now.date().isoformat()
        quotes = {}
        if self.fast is not None:
            try:
                quotes = self.fast.get_quotes(syms)
            except Exception:
                quotes = {}
        try:
            bars = self.bars.get_bars(syms, now=now)
        except Exception as e:
            print(f"[JOURNAL] fresh-bar fetch failed ({e})")
            bars = {}
        left = []
        for o in opens:
            done = False
            if o["date"] == today:
                ltp = float((quotes.get(o["symbol"]) or {}).get("ltp") or 0)
                if ltp > 0:
                    self.journal.finalize(o, ltp, "EOD_SQUAREOFF", now,
                                          "NSE LTP")
                    done = True
            if not done:
                got = bars.get(o["symbol"])
                if got:
                    self.journal.on_bars(o["symbol"], got, now=now)
            if any(x["trade_id"] == o["trade_id"]
                   for x in self.journal.state["open"]):
                left.append(o["trade_id"])
        if left:
            print(f"[JOURNAL] {len(left)} trade(s) could not be priced - "
                  f"kept OPEN: {', '.join(left)}")
            send_telegram("⚠️ EOD square-off: " + ", ".join(left) +
                          " not priced (run UPDATE_JOURNAL / journal.py)")
        self.journal.recompute_day(now.date().isoformat(), now=now)


# ===========================================================================
# SELF TESTS
# ===========================================================================
def _mk_bars(day, spec, start="09:15"):
    t0 = datetime.strptime(f"{day} {start}", "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    return [Bar(t0 + timedelta(minutes=5 * i), o, h, l, c, v)
            for i, (o, h, l, c, v) in enumerate(spec)]


def _mk_bars_step(day, spec, start="09:15", step=5):
    t0 = datetime.strptime(f"{day} {start}", "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    return [Bar(t0 + timedelta(minutes=step * i), o, h, l, c, v)
            for i, (o, h, l, c, v) in enumerate(spec)]


def _trend_spec(n, start_o=99.0, step=0.02, vol=5000):
    """n gently-rising bars; returns [(o,h,l,c,v)...] with a rising
    structure that alone does NOT trigger (no volume spike)."""
    spec = []
    for i in range(n):
        o = start_o + step * i
        c = o + 0.05
        spec.append((round(o, 2), round(c + 0.10, 2), round(o - 0.10, 2),
                     round(c, 2), vol))
    return spec


SPIKE = (101.90, 103.00, 101.70, 102.90, 150000)   # S2 long signal bar
BASE_BARS = _trend_spec(45) + [SPIKE]


def _test_cfg(tmp, **over):
    cfg = deep_merge(DEFAULT_CONFIG, {"journal": {"folder": "journal"},
                                      "universe_refresh": {"enabled": False}})
    cfg["scan_start_t"] = parse_hhmm(cfg["scan_start"])
    cfg["entry_cutoff_t"] = parse_hhmm(cfg["entry_cutoff"])
    cfg["squareoff_t"] = parse_hhmm(cfg["squareoff"])
    cfg["squareoff_alert_t"] = parse_hhmm(cfg["squareoff_alert"])
    cfg["exit_after_t"] = parse_hhmm(cfg["exit_after"])
    cfg.update(over)
    return cfg


class FakeHist:
    def __init__(self, bars_by_date):
        self.d = bars_by_date

    def get_bars_history(self, symbol, date_str, now=None):
        return self.d.get((symbol, date_str), [])


def _sig_for(cfg, bars, symbol="TEST"):
    return check_signal(symbol, bars, cfg)


def test_config_merge():
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "config.json")
    with open(p, "w") as f:
        json.dump({"capital": 50000, "journal": {"daily_loss_limit_R": -1.0},
                   "squareoff_alert": "15:00"}, f)
    cfg = load_config(p)
    assert cfg["capital"] == 50000
    assert cfg["journal"]["daily_loss_limit_R"] == -1.0
    assert cfg["journal"]["max_consecutive_losses"] == 2      # default merged
    assert cfg["rr"] == 3.0
    assert cfg["max_price"] == 2000 and cfg["min_bar_volume"] == 100000
    assert cfg["squareoff_alert_t"] == parse_hhmm("15:00")    # user override
    assert cfg["exit_after_t"] == parse_hhmm("15:35")         # default


def test_journal_autocreate():
    import tempfile
    d = tempfile.mkdtemp()
    j = TradeJournal(base_dir=d, cfg=_test_cfg(d), notify=None)
    assert os.path.exists(j.trades_csv) and os.path.exists(j.summary_csv)
    assert os.path.exists(j.state_json)
    head = open(j.trades_csv, encoding="utf-8").readline().strip()
    assert head.split(",")[0] == "TradeID" and "Result" in head


def test_rsi_atr_helpers():
    up = [100.0 + i for i in range(30)]
    assert rsi_series(up, 14)[-1] > 85
    dn = [200.0 - i for i in range(30)]
    assert rsi_series(dn, 14)[-1] < 15
    assert rsi_series([100.0] * 5, 14) == [None] * 5          # too short
    bars = _mk_bars("2026-01-05", [(100.0, 101.0, 99.0, 100.0, 1000)] * 20)
    a = atr_series(bars, 14)
    assert a[-1] is not None and abs(a[-1] - 2.0) < 0.3
    assert atr_series(bars[:5], 14)[-1] is None               # seed window


def test_record_and_dedup():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    bars = _mk_bars("2026-01-05", BASE_BARS)
    sig = _sig_for(cfg, bars)
    assert sig is not None and sig.direction == "LONG", "expected LONG signal"
    assert sig.setup == "S2_BREAKOUT"
    tid = j.record_signal(sig)
    assert tid and j.has_trade(tid)
    assert j.record_signal(sig) is None, "duplicate must be rejected"
    rows = j._read_trades()
    assert len(rows) == 1 and rows[0]["Status"] == "OPEN"
    assert rows[0]["Entry"] == "103.05"          # signal high + 1 tick
    assert abs(sig.stop - 101.65) < 1e-9         # signal low - 1 tick
    assert abs(sig.target - 107.25) < 0.051      # 1:3 from the stop order
    risk_amt = cfg["capital"] * cfg["risk_pct"] / 100.0
    assert sig.qty == int(risk_amt // (103.05 - 101.65))


def test_long_target_win():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    bars = _mk_bars(day, BASE_BARS)
    sig = _sig_for(cfg, bars)
    j.record_signal(sig)
    # next bar rallies through the target
    bars2 = bars + _mk_bars(day, [(102.9, 107.6, 102.6, 107.3, 20000)], start="13:10")
    j.on_bars("TEST", bars2, now=datetime(2026, 1, 5, 13, 20, tzinfo=IST))
    row = j._read_trades()[0]
    assert row["Status"] == "CLOSED" and row["Result"] == "WIN"
    assert row["ExitReason"] == "TARGET_HIT"
    assert abs(float(row["PnL_R"]) - 3.0) < 0.05, row["PnL_R"]
    s = j.recompute_day(day, now=datetime(2026, 1, 5, 15, 20, tzinfo=IST))
    assert s["DayVerdict"] == "SUCCESS" and s["Open"] == 0  # final after squareoff


def test_long_stop_loss():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    bars = _mk_bars(day, BASE_BARS)
    sig = _sig_for(cfg, bars)
    j.record_signal(sig)
    bars2 = bars + _mk_bars(day, [(102.8, 102.9, 101.0, 101.2, 20000)], start="13:10")
    j.on_bars("TEST", bars2, now=datetime(2026, 1, 5, 13, 20, tzinfo=IST))
    row = j._read_trades()[0]
    assert row["Result"] == "LOSS" and row["ExitReason"] == "STOP_HIT"
    assert abs(float(row["PnL_R"]) + 1.0) < 0.02


def test_short_mirror():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    spec = []
    for i in range(45):                      # gentle downtrend
        o = 101.0 - 0.02 * i
        c = o - 0.05
        spec.append((round(o, 2), round(c + 0.10, 2), round(o - 0.10, 2),
                     round(c, 2), 5000))
    bars = _mk_bars(day, spec + [(99.60, 99.75, 98.60, 98.75, 150000)])
    sig = _sig_for(cfg, bars)
    assert sig is not None and sig.direction == "SHORT", "expected SHORT signal"
    assert sig.setup == "S2_BREAKDOWN"
    assert sig.stop > bars[-1].high          # mirrored SL above the bar high
    assert abs(sig.entry - 98.55) < 1e-9     # sell stop: low - 1 tick
    assert abs(sig.target - 94.80) < 0.051   # 1:3 below the sell stop
    j.record_signal(sig)
    bars2 = bars + _mk_bars(day, [(98.7, 98.8, 94.6, 94.7, 20000)], start="13:10")
    j.on_bars("TEST", bars2, now=datetime(2026, 1, 5, 13, 20, tzinfo=IST))
    row = j._read_trades()[0]
    assert row["Result"] == "WIN" and row["ExitReason"] == "TARGET_HIT"


def test_same_bar_conservative_loss():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    bars = _mk_bars(day, BASE_BARS)
    j.record_signal(_sig_for(cfg, bars))
    # one wild bar that touches BOTH stop and target
    bars2 = bars + _mk_bars(day, [(102.9, 108.0, 101.0, 103.0, 90000)], start="13:10")
    j.on_bars("TEST", bars2, now=datetime(2026, 1, 5, 13, 20, tzinfo=IST))
    row = j._read_trades()[0]
    assert row["Result"] == "LOSS" and row["ExitReason"] == "STOP_HIT"
    assert "conservative" in row["Notes"]


def test_eod_squareoff():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    bars = _mk_bars(day, BASE_BARS)
    j.record_signal(_sig_for(cfg, bars))
    # drifts sideways, nothing hit; now=15:12 (past 15:10) -> square off at
    # the last available close (13:15 in this synthetic series)
    bars2 = bars + _mk_bars(day, [(102.95, 103.15, 102.85, 103.05, 900)] * 2,
                            start="13:10")
    j.on_bars("TEST", bars2, now=datetime(2026, 1, 5, 15, 12, tzinfo=IST))
    row = j._read_trades()[0]
    assert row["Status"] == "CLOSED" and row["ExitReason"] == "EOD_SQUAREOFF"
    assert row["ExitTime"] == "13:15"
    assert row["Result"] == "FLAT"        # exit at entry -> zero P&L


def test_catch_up_backfill():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    bars = _mk_bars(day, BASE_BARS)
    j.record_signal(_sig_for(cfg, bars))
    assert len(j.state["open"]) == 1
    # simulate: PC was off; next morning the target had been hit
    hist = FakeHist({("TEST", day): bars +
                     _mk_bars(day, [(102.9, 107.6, 102.6, 107.3, 20000)], start="13:10")})
    j.catch_up(hist, now=datetime(2026, 1, 6, 9, 0, tzinfo=IST))
    row = j._read_trades()[0]
    assert row["Status"] == "CLOSED" and row["Result"] == "WIN"
    assert j.state["open"] == []
    s = [r for r in j._read_csv(j.summary_csv) if r["Date"] == day][0]
    assert s["DayVerdict"] == "SUCCESS"


def test_day_verdicts_and_breaker():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"

    def base_bars():
        return _mk_bars(day, BASE_BARS)

    def loss_bars():
        return base_bars() + _mk_bars(day, [(102.8, 102.9, 101.0, 101.2, 20000)],
                                      start="13:10")

    def win_bars():
        return base_bars() + _mk_bars(day, [(102.9, 107.6, 102.6, 107.3, 20000)],
                                      start="13:10")

    # trade 1: LOSS -> day verdict FAILED while session still running
    j.record_signal(_sig_for(cfg, base_bars()))
    j.on_bars("TEST", loss_bars(), now=datetime(2026, 1, 5, 13, 20, tzinfo=IST))
    s = j.recompute_day(day, now=datetime(2026, 1, 5, 13, 30, tzinfo=IST))
    assert s["DayVerdict"] == "FAILED*", s["DayVerdict"]

    # trade 2: second consecutive LOSS -> 2-loss streak trips the breaker
    sig2 = check_signal("TEST2", base_bars(), cfg)
    j.record_signal(sig2)
    j.on_bars("TEST2", loss_bars(), now=datetime(2026, 1, 5, 13, 40, tzinfo=IST))
    s = j.recompute_day(day, now=datetime(2026, 1, 5, 15, 20, tzinfo=IST))
    assert s["BreakerTripped"] == "YES" and s["DayVerdict"] == "FAILED"
    assert j.breaker_tripped_today(now=datetime(2026, 1, 5, 15, 20, tzinfo=IST))

    # a winning day -> SUCCESS (final, after square-off time)
    d2 = tempfile.mkdtemp()
    j2 = TradeJournal(base_dir=d2, cfg=_test_cfg(d2), notify=None)
    j2.record_signal(_sig_for(cfg, base_bars()))
    j2.on_bars("TEST", win_bars(), now=datetime(2026, 1, 5, 13, 20, tzinfo=IST))
    s2 = j2.recompute_day(day, now=datetime(2026, 1, 5, 15, 20, tzinfo=IST))
    assert s2["DayVerdict"] == "SUCCESS" and s2["Wins"] == 1

    # a breakeven day -> FLAT
    d3 = tempfile.mkdtemp()
    j3 = TradeJournal(base_dir=d3, cfg=_test_cfg(d3), notify=None)
    j3.record_signal(_sig_for(cfg, base_bars()))
    j3.on_bars("TEST", base_bars() + _mk_bars(day, [(103.0, 103.2, 102.9, 103.05, 900)],
                                              start="13:10"),
               now=datetime(2026, 1, 5, 15, 12, tzinfo=IST))
    s3 = j3.recompute_day(day, now=datetime(2026, 1, 5, 15, 20, tzinfo=IST))
    assert s3["DayVerdict"] == "FLAT"


def test_state_rebuild_from_csv():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    bars = _mk_bars(day, BASE_BARS)
    j.record_signal(_sig_for(cfg, bars))
    os.remove(j.state_json)                   # simulate lost state file
    j2 = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    assert len(j2.state["open"]) == 1, "state must rebuild from CSV"


def test_entry_cutoff_and_gates():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    good = _mk_bars("2026-01-05", BASE_BARS)
    assert _sig_for(cfg, good) is not None
    # after 13:30 -> blocked (same breakout bar, timestamped 13:35)
    late = _mk_bars("2026-01-05", _trend_spec(45))
    late.append(Bar(late[-1].ts + timedelta(minutes=5), 101.2, 103.0,
                    101.1, 102.9, 150000))          # ts = 13:35
    assert _sig_for(cfg, late) is None, "entry cutoff must block late signals"
    # low relative volume -> blocked
    quiet = _mk_bars("2026-01-05", _trend_spec(45) +
                     [(101.20, 103.00, 101.10, 102.90, 5500)])
    assert _sig_for(cfg, quiet) is None
    # stale day (tiny range) -> blocked
    stale = _mk_bars("2026-01-05", [(100.0, 100.05, 99.98, 100.02, 5000)] * 46)
    assert _sig_for(cfg, stale) is None


def test_quote_fast_check():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    bars = _mk_bars(day, BASE_BARS)
    j.record_signal(_sig_for(cfg, bars))
    # LTP beyond target is a real print -> WIN without any bar
    q = {"ltp": 109.0, "high": 109.0, "low": 102.0}
    j.on_quote("TEST", q, now=datetime(2026, 1, 5, 12, 0, tzinfo=IST))
    row = j._read_trades()[0]
    assert row["Result"] == "WIN"


def test_s2_min_stop_gate():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    # breakout with a noise-dominated stop (< max(0.30%, 1.5xATR)) -> skip
    tight = _mk_bars("2026-01-05", _trend_spec(45) +
                     [(102.00, 102.20, 102.00, 102.17, 150000)])
    assert _sig_for(cfg, tight) is None, "min-stop gate must reject tight bars"


def _s1_spec():
    """A clean S1 Type-01 day: impulse A(99.80)->B(101.00), pullback C
    (100.15), activation close above Level 1 (101.35), swing high B2
    (102.05), pullback into the golden pocket [100.88, 101.10], 2R+1G."""
    return [
        (100.00, 100.05, 99.95, 100.00, 8000),   # 0-3: A pivot low @ 1
        (99.95, 100.00, 99.80, 99.90, 8000),
        (99.90, 99.98, 99.82, 99.94, 8000),
        (99.95, 100.10, 99.90, 100.05, 8000),
        (100.00, 100.20, 99.95, 100.15, 8000),   # 4-8: impulse to B @ 8
        (100.20, 100.40, 100.15, 100.35, 8000),
        (100.40, 100.60, 100.35, 100.55, 8000),
        (100.60, 100.80, 100.55, 100.75, 8000),
        (100.80, 101.00, 100.75, 100.95, 8000),
        (100.90, 100.95, 100.55, 100.60, 8000),   # 9-11: pullback to C @ 11
        (100.60, 100.65, 100.30, 100.35, 8000),
        (100.35, 100.40, 100.15, 100.20, 8000),
        (100.20, 100.60, 100.20, 100.55, 8000),   # 12-14: recovery
        (100.55, 101.00, 100.50, 100.95, 8000),
        (100.95, 101.40, 100.90, 101.35, 8000),   # touches L1, no close yet
        (101.35, 101.85, 101.30, 101.80, 8000),   # 15: ACTIVATION close
        (101.80, 102.00, 101.75, 101.95, 8000),   # 16-17: swing high B2
        (101.95, 102.05, 101.90, 102.00, 8000),
        (101.95, 102.00, 101.60, 101.65, 8000),   # 18-19: pullback starts
        (101.65, 101.70, 101.25, 101.30, 8000),
        (101.25, 101.30, 100.95, 101.00, 8000),   # 20-21: two reds in pocket
        (101.00, 101.05, 100.80, 100.85, 8000),
        (100.85, 101.20, 100.80, 101.15, 8000),   # 22: green in pocket
    ]


def test_s1_fib_t01():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    fib = FibEngine(cfg)
    day = "2026-01-05"
    bars = _mk_bars(day, _s1_spec())
    assert fib.update("TEST", bars) is None, "no trigger break yet"
    # the next bar trades through the buy stop (green high 101.20 + 1 tick)
    bars2 = bars + _mk_bars(day, [(101.15, 101.35, 101.10, 101.30, 8000)],
                            start="11:10")
    sig = fib.update("TEST", bars2)
    assert sig is not None, "S1 Type-01 signal expected"
    assert sig.setup == "S1_FIB_T01" and sig.direction == "LONG"
    assert abs(sig.entry - 101.25) < 1e-9      # green high + 1 tick
    assert abs(sig.stop - 100.75) < 1e-9       # green low - 1 tick
    assert abs(sig.target - 102.75) < 0.051    # 1:3
    assert sig.qty == int(62.50 // 0.50)
    assert sig.sig_time == "11:10"             # filled on the break bar


def test_s1_trigger_expiry():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    fib = FibEngine(cfg)
    day = "2026-01-05"
    # five quiet bars after the green candle -> SOP 5-bar trigger expiry
    bars = _mk_bars(day, _s1_spec()) + \
        _mk_bars(day, [(101.15, 101.20, 101.00, 101.05, 8000)] * 5,
                 start="11:10")
    assert fib.update("TEST", bars) is None, "expired trigger must be void"


def test_s3_zone_flow():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    eng = ChoChEngine(cfg, base_dir=d)         # empty poi file -> no zones
    assert eng.zones == {}
    eng.zones = {"TEST": [
        {"side": "LONG", "low": 100.20, "high": 102.00, "date": ""},
        {"side": "SHORT", "low": 106.00, "high": 107.00, "date": ""},
    ]}
    day = "2026-01-05"
    m15 = _mk_bars_step(day, [
        (103.00, 103.10, 102.60, 102.70, 1000),
        (102.70, 102.80, 102.20, 102.30, 1000),
        (102.30, 102.40, 101.60, 101.70, 1000),   # first tap of the zone
        (101.70, 101.80, 101.20, 101.30, 1000),   # deeper tap
        (101.45, 101.65, 101.40, 101.60, 1000),   # M15 confirm close
    ], step=15)
    h1 = _mk_bars_step(day, [
        (101.80, 101.90, 101.50, 101.55, 5000),   # small red bar at the zone
        (101.40, 102.30, 101.20, 102.25, 5000),   # bullish engulfing
    ], step=60)
    sig = eng.update("TEST", eng.zones["TEST"], "BULL", m15, h1,
                     datetime(2026, 1, 5, 10, 20, tzinfo=IST))
    assert sig is not None, "S3 signal expected at the demand POI"
    assert sig.setup == "S3_CHOCH" and sig.direction == "LONG"
    assert abs(sig.entry - 101.60) < 1e-9       # the M15 confirm close
    assert abs(sig.stop - 100.15) < 1e-9        # POI extreme - 1 tick
    assert abs(sig.target - 106.00) < 1e-9      # nearest opposing POI (>= 2R)
    assert sig.qty == int(62.50 // 1.45)        # Phase V sizing
    # bearish bias -> demand zone not tradable (SOP Step 2)
    assert eng.update("TEST", eng.zones["TEST"], "BEAR", m15, h1,
                      datetime(2026, 1, 5, 10, 20, tzinfo=IST)) is None


def test_s3_bias_structure():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    eng = ChoChEngine(cfg, base_dir=d)
    day0 = datetime(2025, 10, 6, 9, 15, tzinfo=IST)

    def daily(seq):
        return [Bar(day0 + timedelta(days=i), v, v, v, v, 1000)
                for i, v in enumerate(seq)]

    up = [100.0 + (i % 4) * 0.4 + i * 0.05 for i in range(80)]
    dn = [200.0 - ((i % 4) * 0.4 + i * 0.05) for i in range(80)]
    assert eng.bias_of("T", daily(up)) == "BULL"
    assert eng.bias_of("T", daily(dn)) == "BEAR"
    assert eng.bias_of("T", daily(up[:40])) is None    # too little history


def test_entries_allowed_caps():
    sc = Scanner.__new__(Scanner)          # skip __init__ (no network)
    sc.cfg = _test_cfg(".", max_trades_per_day=2, max_concurrent_positions=1)

    class FakeJ:
        state = {"open": [{"symbol": "X"}]}

        @staticmethod
        def _read_trades():
            return [{"Date": "2026-01-05"}, {"Date": "2026-01-05"}]

    sc.journal = FakeJ()
    now = datetime(2026, 1, 5, 11, 0, tzinfo=IST)
    ok, why = sc._entries_allowed(now)
    assert not ok and "cap" in why         # 3-entry cap (2 reached)
    sc.cfg["max_trades_per_day"] = 5
    ok, why = sc._entries_allowed(now)
    assert not ok and "concurrent" in why  # 2-position cap (1 held)
    sc.cfg["max_concurrent_positions"] = 3
    ok, _ = sc._entries_allowed(now)
    assert ok


# ------------------------- SelfLearner tests (v3.2) -----------------------
def _closed_row(tid, date, sig_time, setup, direction, result, pnl_r,
                exit_time="15:10"):
    """A CLOSED trade row shaped exactly like the journal writes them."""
    return {"TradeID": tid, "Date": date, "SignalTime": sig_time,
            "Symbol": "TST", "Direction": direction, "Setup": setup,
            "Entry": "100.00", "StopLoss": "99.00", "Target": "103.00",
            "Qty": 10, "RiskPerShare": "1.00", "RiskAmt": "10.00",
            "RewardAmt": "30.00", "RR": "1:3", "Status": "CLOSED",
            "ExitPrice": "100.50", "ExitTime": exit_time,
            "ExitReason": "EOD_SQUAREOFF", "Result": result,
            "PnL_R": f"{pnl_r:.3f}", "PnL_Amt": "0", "UpdatedAt": "",
            "Notes": ""}


def _lr_sig(setup, direction="LONG", hhmm="10:05"):
    return Signal("TST", direction, "2026-01-07", hhmm, 100.0,
                  99.0 if direction == "LONG" else 101.0,
                  103.0 if direction == "LONG" else 97.0,
                  10, 1.0, 10.0, 30.0, note="", setup=setup)


def test_learner_gates():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    rows = []
    # 10 losing S3 SHORT trades -> rule 1 (family) + direction gate
    for i in range(10):
        rows.append(_closed_row(f"T3-{i}", "2026-01-05", "09:45", "S3_CHOCH",
                                "SHORT", "LOSS", -1.0,
                                exit_time=f"10:{i:02d}"))
    # S1: 40% WR / +6R over 10 trades -> rule 1 passes...
    for i in range(4):
        rows.append(_closed_row(f"T1W-{i}", "2026-01-06", "10:00",
                                "S1_FIB_T01", "LONG", "WIN", 3.0,
                                exit_time=f"10:{i * 10:02d}"))
    # ...but its 6 most recent trades all lost -> rule 2 (recent collapse)
    for i in range(6):
        rows.append(_closed_row(f"T1L-{i}", "2026-01-06", "11:00",
                                "S1_FIB_T01", "LONG", "LOSS", -1.0,
                                exit_time=f"14:{i * 10:02d}"))
    # S2: 3 healthy wins -> stays open, becomes top performer
    for i in range(3):
        rows.append(_closed_row(f"T2W-{i}", "2026-01-06", "12:00",
                                "S2_BREAKOUT", "LONG", "WIN", 3.0,
                                exit_time=f"12:{i * 10:02d}"))
    j._write_csv(j.trades_csv, TRADE_COLS, rows)

    lr = SelfLearner(j, cfg, notify=None)
    lr.refresh(now=datetime(2026, 1, 7, 9, 0, tzinfo=IST))
    assert lr.stats["overall"]["n"] == 23
    assert lr.gates["blocked_setups"].get("S3"), "S3 (0% WR over 10) benched"
    assert "recent form" in lr.gates["blocked_setups"].get("S1", ""), \
        "S1 benched by recent-form collapse, not by the 30-trade view"
    assert lr.gates["blocked_directions"].get("SHORT"), \
        "SHORT (0% WR over 10) benched"
    assert lr.gates["preferred"] == "S2"
    # v3.3 DEFAULT = observe-only: gates are computed + reported, never enforced
    ok, _ = lr.allow(_lr_sig("S3_CHOCH", "SHORT"))
    assert ok, "observe-only mode (blocking=false) must pass every signal"
    assert "OBSERVE-ONLY" in lr.status_line()
    # restore v3.2 blocking to pin the gate behaviour itself
    lr.blocking = True
    ok, _ = lr.allow(_lr_sig("S2_BREAKOUT", "LONG"))
    assert ok, "healthy family + open direction must pass"
    ok, why = lr.allow(_lr_sig("S3_CHOCH", "SHORT"))
    assert not ok and "S3" in why
    ok, why = lr.allow(_lr_sig("S2_BREAKDOWN", "SHORT"))
    assert not ok and "SHORT" in why, \
        "direction gate fires even for a healthy family"
    # snapshot persisted inside the journal folder
    assert os.path.exists(lr.path)
    with open(lr.path, "r", encoding="utf-8") as f:
        snap = json.load(f)
    assert snap["gates"]["blocked_setups"].get("S1")
    # digest sends once per day only
    sent = []
    lr2 = SelfLearner(j, cfg, notify=sent.append)
    lr2.prev = lr.prev
    lr2.refresh(now=datetime(2026, 1, 7, 15, 15, tzinfo=IST))
    lr2.digest(now=datetime(2026, 1, 7, 15, 15, tzinfo=IST))
    assert len(sent) == 1
    lr2.digest(now=datetime(2026, 1, 7, 15, 20, tzinfo=IST))
    assert len(sent) == 1, "digest is once-per-day"
    # disabled learner never blocks
    cfg_off = _test_cfg(d, self_learning={"enabled": False})
    lr3 = SelfLearner(j, cfg_off, notify=None)
    ok, _ = lr3.allow(_lr_sig("S3_CHOCH", "SHORT"))
    assert ok


def test_learner_ignores_shadow_rows():
    """v3.3: SHADOW rows are study-only - the learner studies LIVE rows."""
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    rows = [_closed_row(f"L-{i}", "2026-01-05", "09:45", "S2_BREAKOUT",
                        "LONG", "LOSS", -1.0, exit_time=f"10:{i:02d}")
            for i in range(10)]
    j._write_csv(j.trades_csv, TRADE_COLS, rows)
    lr = SelfLearner(j, cfg, notify=None)
    lr.refresh(now=datetime(2026, 1, 6, 9, 0, tzinfo=IST))
    assert lr.stats["overall"]["n"] == 10
    # 10 losing S3 SHADOW rows must not enter the study set
    shad = [dict(_closed_row(f"SH-{i}", "2026-01-05", "13:00", "S3_CHOCH",
                             "SHORT", "LOSS", -1.0, exit_time=f"13:{i:02d}"),
                 Mode="SHADOW") for i in range(10)]
    j._write_csv(j.trades_csv, TRADE_COLS, rows + shad)
    lr.refresh(now=datetime(2026, 1, 6, 9, 5, tzinfo=IST))
    assert lr.stats["overall"]["n"] == 10, "shadow rows must not be studied"
    assert "S3" not in lr.stats.get("setups", {})


def test_shadow_flow_after_cap():
    """v3.3: once the daily cap is reached, further signals journal as
    SHADOW rows - tracked to their outcome, but silent (no Telegram) and
    excluded from day stats, the breaker and the cap itself."""
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d, max_trades_per_day=10)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    rows = [_closed_row(f"T-{i}", day, "09:45", "S2_BREAKOUT", "LONG",
                        "LOSS", -1.0, exit_time=f"10:{i:02d}")
            for i in range(10)]
    j._write_csv(j.trades_csv, TRADE_COLS, rows)
    j._rebuild_state_from_csv()
    sc = Scanner.__new__(Scanner)
    sc.cfg = cfg
    sc.journal = j
    now = datetime(2026, 1, 5, 12, 0, tzinfo=IST)
    ok, why = sc._entries_allowed(now)
    assert not ok and "cap" in why, "10 live trades -> cap reached"
    sent = []
    j.notify = sent.append
    sig = Signal("TST", "LONG", day, "12:05", 100.0, 99.0, 103.0,
                 10, 1.0, 10.0, 30.0, note="", setup="S1_FIB_T01")
    tid = j.record_shadow(sig, reason=why)
    assert tid and not sent, "shadow recording must be silent"
    assert j.record_shadow(sig, reason="again") is None, "dedup by TradeID"
    sh = [r for r in j._read_trades() if r.get("Mode") == "SHADOW"]
    assert len(sh) == 1 and sh[0]["Status"] == "OPEN"
    ok, why = sc._entries_allowed(now)
    assert not ok and "cap" in why, "shadow must not raise the live count"
    # settle the shadow via bars: rally past its 103 target after 12:05
    bars = _mk_bars_step(day, _trend_spec(15, start_o=101.0, step=0.30),
                         start="12:10")
    j.on_bars("TST", bars, now=datetime(2026, 1, 5, 13, 0, tzinfo=IST))
    sh = [r for r in j._read_trades() if r.get("Mode") == "SHADOW"]
    assert sh[0]["Status"] == "CLOSED" and sh[0]["Result"] == "WIN"
    assert not sent, "shadow settle must be console-only (no Telegram)"
    # day summary: LIVE stats only - the +3R shadow win is NOT counted
    s = j.recompute_day(day, now=now)
    assert s["Trades"] == 10 and s["Wins"] == 0
    assert abs(float(s["NetR"]) + 10.0) < 1e-6, "shadow PnL excluded from NetR"
    assert "1 shadow" in s["Notes"]
    assert s["BreakerTripped"] == "YES"    # from the 10 live losses
    assert s["DayVerdict"].startswith("FAILED")


def test_breaker_observe_mode():
    """v3.3: a tripped circuit breaker stops signals ONLY when
    journal.breaker_blocking=true; the default observe mode keeps the
    day producing studyable data (verdict still marked FAILED)."""
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _test_cfg(d)
    j = TradeJournal(base_dir=d, cfg=cfg, notify=None)
    day = "2026-01-05"
    rows = [_closed_row(f"T-{i}", day, "09:45", "S2_BREAKOUT", "LONG",
                        "LOSS", -1.0, exit_time=f"10:{i:02d}")
            for i in range(2)]
    j._write_csv(j.trades_csv, TRADE_COLS, rows)
    now = datetime(2026, 1, 5, 11, 0, tzinfo=IST)
    j.recompute_day(day, now=now)
    tripped = j.breaker_tripped_today(now=now)
    assert tripped, "2 consecutive losses trip the streak breaker"
    # observe mode (default): generation continues
    blocks = tripped and bool(
        (cfg.get("journal") or {}).get("breaker_blocking", False))
    assert not blocks
    s = j.recompute_day(day, now=now)
    assert s["DayVerdict"].startswith("FAILED"), "observe mode still marks the day"
    # blocking restored via config
    cfg["journal"]["breaker_blocking"] = True
    blocks = tripped and bool(
        (cfg.get("journal") or {}).get("breaker_blocking", False))
    assert blocks


def test_signal_window_filter():
    cfg = _test_cfg(".")

    def mk(hhmm):
        return _lr_sig("S2_BREAKOUT", "LONG", hhmm)

    assert _in_signal_window(mk("09:30"), cfg)      # window opens
    assert _in_signal_window(mk("11:05"), cfg)
    assert _in_signal_window(mk("13:30"), cfg)      # cutoff inclusive
    assert not _in_signal_window(mk("13:35"), cfg), "no signals after 13:30"
    assert not _in_signal_window(mk("09:00"), cfg), "no signals before 09:30"
    assert DEFAULT_CONFIG["max_trades_per_day"] == 10, "v3.2 daily cap"


# ------------------------- AutoPoi tests ----------------------------------
def _h1_session(day, closes, wick=0.12, vol=5000):
    """Six 1h bars (09:15..15:15 IST) walking through `closes`."""
    times = ["09:15", "10:15", "11:15", "12:15", "13:15", "14:15", "15:15"]
    bars = []
    o = closes[0] - (closes[0] * 0)  # first bar opens at given level
    seq = closes
    for i, c in enumerate(seq):
        t0 = datetime.strptime(f"{day} {times[i]}", "%Y-%m-%d %H:%M")
        bars.append(Bar(t0.replace(tzinfo=IST), o,
                        max(o, c) + wick, min(o, c) - wick, c, vol))
        o = c
    return bars


def _auto_poi_cfg(tmp, **over):
    cfg = _test_cfg(tmp, **over)
    cfg["poi_auto_file"] = "poi_zones_auto.csv"
    cfg["s3_poi_lookback_days"] = 30
    cfg["s3_poi_max_zone_pct"] = 2.0
    cfg["s3_poi_proximity_pct"] = 20.0   # wide for the synthetic series
    cfg["s3_poi_max_per_side"] = 2
    return cfg


class FakeProv:
    """Minimal provider double for AutoPoi tests."""

    def __init__(self, h1_by_sym, daily_by_sym=None):
        self.h1 = h1_by_sym
        self.daily = daily_by_sym or {}
        self.h1_calls = 0

    def get_intraday(self, symbols, interval="15m", period="5d", now=None):
        self.h1_calls += 1
        return {s: list(self.h1.get(s, [])) for s in symbols}

    def get_daily(self, symbols, period="1y", now=None):
        return {s: list(self.daily.get(s, [])) for s in symbols}


def _swing_series(rally_over=False):
    """12 sessions: down into ~399 (swing low), up into ~441 (swing
    high), then mild drift. rally_over=True closes through the high."""
    sessions = ["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06",
                "2026-01-07", "2026-01-08", "2026-01-09", "2026-01-12",
                "2026-01-13", "2026-01-14", "2026-01-15", "2026-01-16"]
    path = []                       # per-session six 1h closes
    px = 430.0
    for i in range(12):
        if i < 3:                   # decline into the swing low (~399)
            step = -3.4
        elif i < 8:                 # rally into the swing high (~441)
            step = +2.78
        else:                       # mild drift under the high
            step = -0.4
        closes = [round(px + step * (j + 1) * 0.5, 2) for j in range(7)]
        closes = [px] + closes[:6]
        px = closes[-1]
        path.append((sessions[i], closes))
    bars = []
    for day, closes in path:
        bars += _h1_session(day, closes)
    if rally_over:
        for k, day in enumerate(["2026-01-19", "2026-01-20"]):
            closes = [442.0 + k, 444.0 + k, 446.0 + k, 448.0 + k,
                      450.0 + k, 452.0 + k, 454.0 + k]
            bars += _h1_session(day, closes)
    return bars


def test_auto_poi_h4_and_zones():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _auto_poi_cfg(d)
    ap = AutoPoi(cfg, FakeProv({"TEST": _swing_series()}), base_dir=d)
    now = datetime(2026, 1, 22, 9, 30, tzinfo=IST)   # a Friday, after data
    h1 = ap.provider.get_intraday(["TEST"], "60m", "60d", now=now)
    h4 = ap._h4_buckets(h1["TEST"])
    assert len(h4) == 24, f"12 sessions -> 24 H4 bars, got {len(h4)}"
    b0 = h4[0]
    assert b0.ts.hour == 9 and b0.ts.minute == 15    # bucket A anchor
    zs = ap._zones_from_h4(h4)
    sides = {z["side"] for z in zs}
    assert "LONG" in sides and "SHORT" in sides, f"zones {zs}"
    for z in zs:
        assert set(z) == {"side", "low", "high"}, f"raw zone keys {z}"
        assert z["high"] > z["low"] > 0
        h = (z["high"] - z["low"]) / ((z["low"] + z["high"]) / 2)
        assert h <= 0.02, f"zone too tall: {z}"
    # the supply zone must sit near the 440 swing high, demand near 400
    sup = [z for z in zs if z["side"] == "SHORT"]
    dem = [z for z in zs if z["side"] == "LONG"]
    assert any(z["high"] >= 438 for z in sup), f"supply {sup}"
    assert any(z["low"] <= 402 for z in dem), f"demand {dem}"


def test_auto_poi_fresh_filter_and_expiry():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _auto_poi_cfg(d)
    now = datetime(2026, 1, 22, 9, 30, tzinfo=IST)
    # 1) broken supply: price later CLOSES above the 440 swing high
    ap = AutoPoi(cfg, FakeProv({"TEST": _swing_series(rally_over=True)}),
                 base_dir=d)
    h1 = ap.provider.get_intraday(["TEST"], "60m", "60d", now=now)
    h4 = ap._h4_buckets(h1["TEST"])
    zs = ap._zones_from_h4(h4)
    assert all(z["side"] != "SHORT" for z in zs), \
        f"closed-through supply must be discarded: {zs}"
    # 2) today's partial session never enters the zone math
    today_bars = _h1_session("2026-01-22",
                             [454.0, 456.0, 458.0, 460.0, 462.0, 464.0,
                              466.0])
    h4b = ap._h4_buckets(h1["TEST"] + today_bars)
    assert all(b.ts.date().isoformat() < "2026-01-22"
               for b in AutoPoi._h4_buckets(h1["TEST"]))   # sanity
    zs2 = ap._zones_from_h4([b for b in h4b
                             if b.ts.date().isoformat() < "2026-01-22"])
    assert zs2 == zs or all(z["side"] != "SHORT" for z in zs2)


def test_auto_poi_file_roundtrip_and_idempotence():
    import tempfile
    d = tempfile.mkdtemp()
    cfg = _auto_poi_cfg(d)
    prov = FakeProv({"TEST": _swing_series()})
    ap = AutoPoi(cfg, prov, base_dir=d)
    now = datetime(2026, 1, 22, 9, 30, tzinfo=IST)
    res = ap.ensure_today(["TEST"], now,
                          bias_of=lambda s, daily: "BULL")
    assert res is not None and res[0] > 0 and res[1] == 1
    # bias BULL -> only demand zones survive the pre-filter
    with open(ap.out_path, "r", encoding="utf-8") as f:
        rows = [ln.strip() for ln in f if ln.strip()
                and not ln.startswith("#")
                and not ln.startswith("symbol")]
    assert rows and all(r.split(",")[1] == "LONG" for r in rows), rows
    assert all(r.split(",")[4] == "2026-01-22" for r in rows)
    # idempotence: a second call the same day must NOT re-fetch
    calls = prov.h1_calls
    assert ap.ensure_today(["TEST"], now) is None
    assert prov.h1_calls == calls, "must skip when today's map exists"
    # the ChoChEngine picks the auto file up
    eng = ChoChEngine(cfg, base_dir=d)
    assert "TEST" in eng.zones and eng.zones["TEST"], eng.zones
    # date gate: an undated zone trades, the SAME zone dated yesterday
    # is loaded but must NOT trade today (zones expire at midnight)
    good = {"side": "LONG", "low": 100.20, "high": 101.00, "date": ""}
    stale = dict(good, date="2026-01-21")
    day = now.date().isoformat()
    m15 = _mk_bars_step(day, [
        (102.00, 102.10, 101.60, 101.70, 1000),
        (101.70, 101.80, 101.20, 101.30, 1000),
        (101.30, 101.40, 100.90, 101.00, 1000),   # tap
        (101.00, 101.10, 100.95, 101.05, 1000),   # deeper tap
        (101.05, 101.65, 101.00, 101.60, 1000),   # 10:15 confirm close
    ], step=15)
    h1 = _mk_bars_step(day, [
        (101.30, 101.40, 100.80, 100.90, 5000),   # red bar at the zone
        (100.90, 101.60, 100.75, 101.55, 5000),   # bullish engulfing
    ], step=60)
    assert eng.update("T2", [good], "BULL", m15, h1, now) is not None, \
        "control: the same zone undated must produce a signal"
    assert eng.update("T2", [stale], "BULL", m15, h1, now) is None, \
        "yesterday's zones must not trade today"


_WIKI_FIXTURE = """<html><body>
<table class="wikitable sortable jquery-tablesorter">
<thead><tr><th>Symbol</th><th>Company Name</th><th>Sector</th></tr></thead>
<tbody>
<tr><td><a href="/wiki/Reliance_Industries" title="Reliance">RELIANCE</a></td>
<td>Reliance Industries</td><td>Energy</td></tr>
<tr><td><a href="/wiki/HDFC_Bank">HDFCBANK</a></td><td>HDFC Bank</td>
<td>Financial Services</td></tr>
<tr><td><a href="/wiki/M%26M">M&amp;M</a></td><td>Mahindra &amp; Mahindra</td>
<td>Automotive</td></tr>
<tr><td>NIFTY 50</td><td>Index itself</td><td>Index</td></tr>
</tbody></table>
<table class="wikitable"><tr><th>Name</th><th>Value</th></tr>
<tr><td>not a constituents table</td><td>1</td></tr></table>
</body></html>"""


def test_universe_refresh_flow():
    import tempfile
    d = tempfile.mkdtemp()
    ufile = os.path.join(d, "universe_nifty100.txt")
    with open(ufile, "w") as f:
        f.write("# stale shipped file\nDELISTED.NS\nRELIANCE.NS\n")
    cfg = deep_merge(DEFAULT_CONFIG, {"journal": {"folder": "journal"},
                                      "universe_refresh": {
        "enabled": True, "days": 7, "min_symbols": 2, "max_symbols": 5}})
    # 1) parser: ordered unique symbols from the 'Symbol' column, index
    #    rows and non-constituent tables dropped
    got = _parse_wiki_constituents(_WIKI_FIXTURE)
    assert got == ["RELIANCE", "HDFCBANK", "M&M"], got
    global _fetch_nifty100_nse, _fetch_nifty100_wiki
    keep = (_fetch_nifty100_nse, _fetch_nifty100_wiki)
    try:
        def _boom(timeout=15):
            raise RuntimeError("blocked")
        # 2) stale universe + NSE blocked -> Wikipedia succeeds, dead
        #    symbol is dropped, new one appears, cache written
        _fetch_nifty100_nse = _boom
        _fetch_nifty100_wiki = lambda timeout=15: \
            _parse_wiki_constituents(_WIKI_FIXTURE) + ["NEWGUY"]
        syms, changed = refresh_universe(cfg, base_dir=d)
        assert syms == ["RELIANCE", "HDFCBANK", "M&M", "NEWGUY"], syms
        on_disk = load_universe(ufile)
        assert on_disk == syms and "DELISTED" not in on_disk
        with open(os.path.join(d, "universe_cache.json")) as f:
            cj = json.load(f)
        assert cj["source"] == "Wikipedia" and cj["symbols"] == syms
        assert cj["last_attempt"] and cj["updated"]
        # 3) inside the schedule window -> zero fetches, file untouched
        calls = {"n": 0}
        def _count(timeout=15):
            calls["n"] += 1
            raise RuntimeError("must not be called")
        _fetch_nifty100_nse = _fetch_nifty100_wiki = _count
        syms2, changed2 = refresh_universe(cfg, base_dir=d)
        assert syms2 == [] and changed2 is False and calls["n"] == 0
        assert load_universe(ufile) == syms
        # 4) window elapsed but every source fails -> old file survives
        with open(os.path.join(d, "universe_cache.json"), "w") as f:
            json.dump({"last_attempt": "2020-01-01"}, f)
        _fetch_nifty100_nse = _fetch_nifty100_wiki = _boom
        syms3, changed3 = refresh_universe(cfg, base_dir=d)
        assert syms3 == [] and changed3 is False
        assert load_universe(ufile) == syms
        # 5) fetched list outside the sanity window is rejected
        with open(os.path.join(d, "universe_cache.json"), "w") as f:
            json.dump({"last_attempt": "2020-01-01"}, f)
        _fetch_nifty100_nse = _boom
        _fetch_nifty100_wiki = lambda timeout=15: ["TOOSMALL"]
        syms4, _ = refresh_universe(cfg, base_dir=d)
        assert syms4 == [] and load_universe(ufile) == syms
        # 6) disabled flag: no fetch, no change
        cfg_off = deep_merge(cfg, {"universe_refresh": {"enabled": False}})
        _fetch_nifty100_wiki = _count
        syms5, changed5 = refresh_universe(cfg_off, base_dir=d)
        assert syms5 == [] and changed5 is False and calls["n"] == 0
    finally:
        _fetch_nifty100_nse, _fetch_nifty100_wiki = keep


def test_scan_symbols_type_safe():
    """v3.2.2 regression: the S1 watch set holds (symbol, side) tuples;
    the bar-request symbol set must stay strings-only so sorted() never
    mixes types (that exact mix crashed live runs on 2026-11-03)."""
    sc = Scanner.__new__(Scanner)          # bypass __init__ (no network)
    sc.cfg = _test_cfg(".")
    sc.universe = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    sc._cycle = 0
    sc.fib = FibEngine(sc.cfg)
    sc.fib.watch = {("AAA", "LONG"), ("BBB", "SHORT")}   # tuples!
    sc.journal = type("J", (), {"state": {"open": [
        {"symbol": "CCC"}]}})()
    # 1) Yahoo-only path (no quotes): tuple symbols projected to strings
    need = sc._scan_symbols({})
    assert need == {"AAA", "BBB", "CCC", "DDD", "EEE"}, need
    assert all(isinstance(s, str) for s in need)
    assert sorted(need) == sorted(["AAA", "BBB", "CCC", "DDD", "EEE"])
    # 2) NSE fast-lane path: candidates + open + watch + rotate slice
    quotes = {"AAA": {"ltp": 100.0, "high": 100.0, "low": 99.0},
              "EEE": {"ltp": 50.0, "high": 51.0, "low": 50.0}}
    sc._cycle = 0
    need2 = sc._scan_symbols(quotes)
    assert all(isinstance(s, str) for s in need2)
    assert {"AAA", "BBB", "CCC", "EEE"} <= need2
    sorted(need2)
    # 3) cycle advanced exactly once for the quotes path
    assert sc._cycle == 1


SELF_TESTS = [test_config_merge, test_journal_autocreate, test_rsi_atr_helpers,
              test_record_and_dedup, test_long_target_win, test_long_stop_loss,
              test_short_mirror, test_same_bar_conservative_loss,
              test_eod_squareoff, test_catch_up_backfill,
              test_day_verdicts_and_breaker, test_state_rebuild_from_csv,
              test_entry_cutoff_and_gates, test_quote_fast_check,
              test_s2_min_stop_gate, test_s1_fib_t01, test_s1_trigger_expiry,
              test_s3_zone_flow, test_s3_bias_structure,
              test_entries_allowed_caps,
              test_learner_gates, test_signal_window_filter,
              test_auto_poi_h4_and_zones, test_auto_poi_fresh_filter_and_expiry,
              test_auto_poi_file_roundtrip_and_idempotence,
              test_universe_refresh_flow, test_scan_symbols_type_safe,
              test_learner_ignores_shadow_rows, test_shadow_flow_after_cap,
              test_breaker_observe_mode]


def run_selftests():
    print(f"SELF-TEST SUITE - scanner v{VERSION}")
    print("-" * 66)
    fails = 0
    for fn in SELF_TESTS:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except Exception as e:
            fails += 1
            print(f"  FAIL  {fn.__name__}: {e}")
            traceback.print_exc(limit=2)
    print("-" * 66)
    print(f"{len(SELF_TESTS) - fails}/{len(SELF_TESTS)} passed")
    return fails == 0


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Intraday scanner v%s - all 3 "
                                 "SOP strategies + self-learning + 15:10 "
                                 "auto square-off" % VERSION)
    ap.add_argument("--once", action="store_true", help="single scan cycle")
    ap.add_argument("--journal", action="store_true",
                    help="update journal + print report (no scanning)")
    ap.add_argument("--selftest", action="store_true", help="run test suite")
    ap.add_argument("--config", default="config.json")
    args = ap.parse_args()

    cfg = load_config(args.config)

    if args.selftest:
        ok = run_selftests()
        sys.exit(0 if ok else 1)

    if args.journal:
        j = TradeJournal(base_dir=".", cfg=cfg, notify=send_telegram)
        try:
            j.catch_up(make_bar_provider(cfg))
        except Exception as e:
            print(f"[JOURNAL] catch-up unavailable ({e}) - report only")
        print(j.report())
        sys.exit(0)

    try:
        sc = Scanner(cfg)
    except ProviderUnavailable as e:
        print(f"[FATAL] {e}")
        sys.exit(2)

    if args.once:
        sc.run_once()
        now = now_ist()
        if now.weekday() < 5 and now.time() >= cfg_squareoff(sc.cfg):
            sc.run_eod()       # cloud / late start: square off + verdict
        else:
            print(sc.journal.report())
    else:
        sc.run()
        if sc.cfg.get("auto_exit_after_close", True):
            sc.run_eod()
            time.sleep(1)
            sys.exit(0)


if __name__ == "__main__":
    main()
