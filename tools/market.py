"""Price data, indicators and levels.

Two halves, deliberately separated:

* **Pure functions** (`ema`, `atr`, `vwap`, `volume_ratio`, `bar_range_stats`, `get_indicators`,
  `opening_range`, `session_levels`) take a DataFrame and compute. No network, no clock, no I/O.
  These are the ones under test.
* **Fetchers** (`get_bars`, `get_levels`, `get_option_chain`) hit yfinance and cache to
  ``.cache/``.

Everything here is free data. No API key, ever (BUILD_PROMPT Part 0, constraint 2).

Timezone: all bar indices are converted to **US/Eastern**. Display in Central is
``fmt_time`` -- see ``_INDEX.md`` contradiction 1.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, date, time as dtime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")

MARKET_OPEN = dtime(9, 30)
MARKET_CLOSE = dtime(16, 0)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
CACHE_TTL_SECONDS = 120

OHLC = ["Open", "High", "Low", "Close", "Volume"]


class NoDataError(RuntimeError):
    """Raised when a fetch returns nothing usable.

    The caller must surface this as ``NO TRADE -- no data``. Never substitute a fabricated
    level (BUILD_PROMPT Part 3, Step 2).
    """


# --------------------------------------------------------------------------------------
# pure: indicators
# --------------------------------------------------------------------------------------

def ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential moving average, recursive form (``adjust=False``).

    This matches how TradingView seeds and updates an EMA, which matters because CJ reads
    these values off his chart and we must reconcile against them.
    """
    return series.astype(float).ewm(span=length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.astype(float).rolling(length).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    high, low = df["High"].astype(float), df["Low"].astype(float)
    prev_close = df["Close"].astype(float).shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    tr = ranges.max(axis=1)
    tr.iloc[0] = high.iloc[0] - low.iloc[0]  # no prior close on the first bar
    return tr


def atr(df: pd.DataFrame, length: int = 14, method: str = "wilder") -> pd.Series:
    """Average true range.

    ``method="wilder"`` is the standard smoothing. ``method="sma"`` is a plain rolling mean --
    used by the fixture test because it is hand-computable.
    """
    tr = true_range(df)
    if method == "sma":
        return tr.rolling(length).mean()
    if method == "wilder":
        return tr.ewm(alpha=1.0 / length, adjust=False).mean()
    raise ValueError(f"unknown atr method: {method!r}")


def vwap(df: pd.DataFrame) -> pd.Series:
    """Session VWAP, reset at each new calendar day in the index timezone.

    Computed, **not visible on CJ's chart** -- his layout has no VWAP (``02-trycon-mas.md``).
    Any response mentioning it must label it computed. See ``_INDEX.md`` contradiction 3.
    """
    typical = (df["High"].astype(float) + df["Low"].astype(float) + df["Close"].astype(float)) / 3.0
    vol = df["Volume"].astype(float)
    days = pd.Series(df.index.date, index=df.index)
    cum_pv = (typical * vol).groupby(days).cumsum()
    cum_v = vol.groupby(days).cumsum()
    return cum_pv / cum_v.replace(0, np.nan)


def volume_ratio(df: pd.DataFrame, lookback: int = 20) -> float:
    """Last bar's volume against the mean of the ``lookback`` bars before it.

    Only meaningful if volume bars are actually enabled on CJ's chart -- ``02-trycon-mas.md``
    forbids claiming a volume spike when volume is not shown. This value is computed data, so
    it may be used in the engine, but the mentor read may not point at it as *visible*.
    """
    vol = df["Volume"].astype(float)
    if len(vol) < 2:
        return float("nan")
    window = vol.iloc[-(lookback + 1):-1]
    baseline = window.mean()
    if not baseline or np.isnan(baseline) or baseline == 0:
        return float("nan")
    return float(vol.iloc[-1] / baseline)


def bar_range_stats(df: pd.DataFrame, lookback: int = 20) -> dict:
    """Mean and sigma of recent bar ranges. Feeds guard 7 (minimum stop distance)."""
    rng = (df["High"].astype(float) - df["Low"].astype(float)).iloc[-lookback:]
    return {
        "mean_range": float(rng.mean()),
        "sigma_range": float(rng.std(ddof=0)),
        "bars": int(len(rng)),
    }


@dataclass
class Indicators:
    """Every value here is **computed from live bars**, never read off a screenshot."""

    last: float
    ema9: float
    ema21: float
    ema50: float
    ema200: float
    sma200: float
    atr: float
    vwap: float
    volume_ratio: float
    mean_bar_range: float
    sigma_bar_range: float
    bars_used: int
    warmup_ok: bool
    source: str = "computed"

    def as_dict(self) -> dict:
        return asdict(self)


def get_indicators(df: pd.DataFrame, atr_length: int = 14, atr_method: str = "wilder") -> Indicators:
    """The five Trycon MAs plus ATR, VWAP, volume ratio and bar-range stats.

    ``warmup_ok`` is False when there are fewer than 200 bars, which means the 200-period lines
    are seeded on partial history and must be reported as approximate rather than quoted as
    levels.
    """
    if df is None or len(df) == 0:
        raise NoDataError("no bars supplied to get_indicators")

    close = df["Close"].astype(float)
    stats = bar_range_stats(df)
    return Indicators(
        last=float(close.iloc[-1]),
        ema9=float(ema(close, 9).iloc[-1]),
        ema21=float(ema(close, 21).iloc[-1]),
        ema50=float(ema(close, 50).iloc[-1]),
        ema200=float(ema(close, 200).iloc[-1]),
        sma200=float(sma(close, 200).iloc[-1]) if len(close) >= 200 else float("nan"),
        atr=float(atr(df, atr_length, atr_method).iloc[-1]),
        vwap=float(vwap(df).iloc[-1]),
        volume_ratio=volume_ratio(df),
        mean_bar_range=stats["mean_range"],
        sigma_bar_range=stats["sigma_range"],
        bars_used=int(len(df)),
        warmup_ok=len(df) >= 200,
    )


# --------------------------------------------------------------------------------------
# pure: levels
# --------------------------------------------------------------------------------------

def _et_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is None:
        df = df.tz_localize("UTC")
    return df.tz_convert(ET)


def regular_session(df: pd.DataFrame, day: Optional[date] = None) -> pd.DataFrame:
    """Bars inside 09:30--16:00 ET for one day."""
    df = _et_index(df)
    if day is not None:
        df = df[pd.Series(df.index.date, index=df.index).values == day]
    mask = (df.index.time >= MARKET_OPEN) & (df.index.time < MARKET_CLOSE)
    return df[mask]


def opening_range(df: pd.DataFrame, minutes: int = 15, day: Optional[date] = None) -> dict:
    """High/low of the first ``minutes`` of the regular session.

    Returns NaNs until the window has actually printed -- an opening range that has not
    completed is not a level.
    """
    sess = regular_session(df, day)
    if len(sess) == 0:
        return {"or_high": float("nan"), "or_low": float("nan"), "complete": False}
    start = sess.index[0]
    window = sess[sess.index < start + timedelta(minutes=minutes)]
    if len(window) == 0:
        return {"or_high": float("nan"), "or_low": float("nan"), "complete": False}
    complete = bool(sess.index[-1] >= start + timedelta(minutes=minutes))
    return {
        "or_high": float(window["High"].max()),
        "or_low": float(window["Low"].min()),
        "complete": complete,
    }


def session_levels(df: pd.DataFrame, day: Optional[date] = None) -> dict:
    sess = regular_session(df, day)
    if len(sess) == 0:
        return {"session_high": float("nan"), "session_low": float("nan")}
    return {"session_high": float(sess["High"].max()), "session_low": float(sess["Low"].min())}


def overnight_levels(df: pd.DataFrame, day: Optional[date] = None) -> dict:
    """Extended-hours high/low between the prior close and this session's open.

    Requires bars fetched with ``prepost=True``. Returns NaNs otherwise, which is the honest
    answer -- not a guess.
    """
    df = _et_index(df)
    if day is None:
        day = df.index[-1].date()
    session_open = datetime.combine(day, MARKET_OPEN, tzinfo=ET)
    prior_close = datetime.combine(day - timedelta(days=1), MARKET_CLOSE, tzinfo=ET)
    window = df[(df.index >= prior_close) & (df.index < session_open)]
    if len(window) == 0:
        return {"overnight_high": float("nan"), "overnight_low": float("nan"), "bars": 0}
    return {
        "overnight_high": float(window["High"].max()),
        "overnight_low": float(window["Low"].min()),
        "bars": int(len(window)),
    }


def prior_day_levels(daily: pd.DataFrame, day: Optional[date] = None) -> dict:
    """Prior day high/low/close from daily bars."""
    if daily is None or len(daily) < 2:
        return {"pdh": float("nan"), "pdl": float("nan"), "pdc": float("nan")}
    d = daily.copy()
    if isinstance(d.index, pd.DatetimeIndex):
        dates = pd.Series(d.index.date, index=d.index)
        if day is not None:
            d = d[dates.values < day]
    if len(d) == 0:
        return {"pdh": float("nan"), "pdl": float("nan"), "pdc": float("nan")}
    row = d.iloc[-1]
    return {"pdh": float(row["High"]), "pdl": float(row["Low"]), "pdc": float(row["Close"])}


# --------------------------------------------------------------------------------------
# clock
# --------------------------------------------------------------------------------------

def now_et() -> datetime:
    return datetime.now(ET)


def fmt_time(dt: datetime) -> str:
    """Central first, Eastern second. ``_INDEX.md`` contradiction 1."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ET)
    return f"{dt.astimezone(CT):%H:%M} CT / {dt.astimezone(ET):%H:%M} ET"


def is_market_open(when: Optional[datetime] = None) -> bool:
    """Weekday regular-session check.

    **Does not know about market holidays** -- there is no holiday calendar in the free stack.
    On a holiday this returns True and the data fetch returns nothing, which lands on
    ``NO TRADE -- no data``. Honest, if blunt.
    """
    when = (when or now_et()).astimezone(ET)
    if when.weekday() >= 5:
        return False
    return MARKET_OPEN <= when.time() < MARKET_CLOSE


def minutes_until_close(when: Optional[datetime] = None) -> float:
    when = (when or now_et()).astimezone(ET)
    close = datetime.combine(when.date(), MARKET_CLOSE, tzinfo=ET)
    return (close - when).total_seconds() / 60.0


def minutes_since_open(when: Optional[datetime] = None) -> float:
    when = (when or now_et()).astimezone(ET)
    open_dt = datetime.combine(when.date(), MARKET_OPEN, tzinfo=ET)
    return (when - open_dt).total_seconds() / 60.0


# --------------------------------------------------------------------------------------
# fetchers
# --------------------------------------------------------------------------------------

def _cache_path(key: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return os.path.join(CACHE_DIR, f"{safe}.pkl")


def _read_cache(key: str, ttl: int = CACHE_TTL_SECONDS) -> Optional[pd.DataFrame]:
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    if time.time() - os.path.getmtime(path) > ttl:
        return None
    try:
        return pd.read_pickle(path)
    except Exception:
        return None


def _write_cache(key: str, df: pd.DataFrame) -> None:
    try:
        df.to_pickle(_cache_path(key))
    except Exception:
        pass  # a cache miss is never worth failing a call over


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance sometimes returns MultiIndex columns for a single ticker. Flatten them."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    keep = [c for c in OHLC if c in df.columns]
    df = df[keep].dropna(how="all")
    return _et_index(df)


def get_bars(
    ticker: str,
    interval: str = "5m",
    lookback: str = "5d",
    prepost: bool = True,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Fetch bars from yfinance, ET-indexed and cached.

    Raises ``NoDataError`` on an empty response -- weekend, outage, or bad ticker. The caller
    turns that into ``NO TRADE -- no data``.
    """
    key = f"{ticker}-{interval}-{lookback}-{int(prepost)}"
    if use_cache:
        cached = _read_cache(key)
        if cached is not None:
            return cached
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover
        raise NoDataError("yfinance is not installed") from exc

    raw = yf.download(
        ticker, period=lookback, interval=interval, prepost=prepost,
        progress=False, auto_adjust=False,
    )
    if raw is None or len(raw) == 0:
        raise NoDataError(
            f"yfinance returned no bars for {ticker} {interval}/{lookback}. "
            "Weekend, holiday, outage or bad ticker."
        )
    df = _normalise(raw)
    if len(df) == 0:
        raise NoDataError(f"yfinance returned unusable bars for {ticker}")
    _write_cache(key, df)
    return df


def get_levels(ticker: str, day: Optional[date] = None, use_cache: bool = True) -> dict:
    """Prior day H/L/C, overnight H/L, opening range, session H/L. All computed."""
    intraday = get_bars(ticker, "5m", "5d", prepost=True, use_cache=use_cache)
    if day is None:
        day = intraday.index[-1].date()
    try:
        daily = get_bars(ticker, "1d", "1mo", prepost=False, use_cache=use_cache)
    except NoDataError:
        daily = None

    levels: dict = {"ticker": ticker, "day": str(day), "source": "computed"}
    levels.update(prior_day_levels(daily, day))
    levels.update(overnight_levels(intraday, day))
    levels.update(opening_range(intraday, 15, day))
    levels.update(session_levels(intraday, day))
    return levels


def get_option_chain(ticker: str, target_strike: Optional[float] = None) -> dict:
    """Best-effort 0DTE chain near the money.

    yfinance option data is unreliable and often stale. On any failure this returns
    ``{"available": False, "reason": ...}`` and the response must then say the contract line is
    an estimate and ask CJ to confirm the real bid/ask off his chain --
    ``02-trycon-mas.md``: *a price chart cannot verify a strike, premium, bid, ask or spread.*
    """
    out: dict = {"ticker": ticker, "available": False, "reason": "", "expiry": None, "strikes": []}
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        expiries = list(tk.options or [])
        if not expiries:
            out["reason"] = "no expiries returned"
            return out
        today = now_et().date().isoformat()
        expiry = today if today in expiries else expiries[0]
        if expiry != today:
            out["reason"] = f"no 0DTE expiry available; nearest is {expiry}"
        chain = tk.option_chain(expiry)
        out["expiry"] = expiry
        rows = []
        for side, frame in (("call", chain.calls), ("put", chain.puts)):
            for _, r in frame.iterrows():
                bid, ask = float(r.get("bid") or 0), float(r.get("ask") or 0)
                mid = (bid + ask) / 2 if (bid and ask) else float(r.get("lastPrice") or 0)
                rows.append({
                    "side": side,
                    "strike": float(r["strike"]),
                    "bid": bid,
                    "ask": ask,
                    "mid": mid,
                    "spread": round(ask - bid, 4) if (bid and ask) else float("nan"),
                    "spread_pct": round((ask - bid) / mid, 4) if (bid and ask and mid) else float("nan"),
                    "volume": float(r.get("volume") or 0),
                    "open_interest": float(r.get("openInterest") or 0),
                })
        if target_strike is not None:
            rows.sort(key=lambda x: abs(x["strike"] - target_strike))
            rows = rows[:20]
        out["strikes"] = rows
        out["available"] = bool(rows) and expiry == today
        if not out["reason"] and not rows:
            out["reason"] = "chain returned no rows"
        return out
    except Exception as exc:
        out["reason"] = f"chain fetch failed: {type(exc).__name__}: {exc}"
        return out


def data_snapshot(ticker: str, interval: str = "5m") -> dict:
    """Everything the decision engine needs, in one call. Raises ``NoDataError`` cleanly."""
    df = get_bars(ticker, interval, "5d", prepost=True)
    ind = get_indicators(df)
    levels = get_levels(ticker)
    return {
        "ticker": ticker,
        "interval": interval,
        "as_of": df.index[-1].isoformat(),
        "as_of_display": fmt_time(df.index[-1].to_pydatetime()),
        "indicators": ind.as_dict(),
        "levels": levels,
        "market_open": is_market_open(),
        "minutes_until_close": round(minutes_until_close(), 1),
    }


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description="Snapshot live data for a ticker.")
    ap.add_argument("ticker", nargs="?", default="SPY")
    ap.add_argument("--interval", default="5m")
    args = ap.parse_args()
    try:
        print(json.dumps(data_snapshot(args.ticker, args.interval), indent=2, default=str))
    except NoDataError as exc:
        print(json.dumps({"verdict": "NO TRADE", "reason": f"no data: {exc}"}, indent=2))
