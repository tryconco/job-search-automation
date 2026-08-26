"""Deterministic bar fixtures. No network in any test."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

ET = ZoneInfo("America/New_York")


def make_bars(rows, start="2026-08-24 09:30", freq_minutes=5, tz=ET):
    """rows: list of (open, high, low, close, volume)."""
    begin = datetime.strptime(start, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
    idx = [begin + timedelta(minutes=freq_minutes * i) for i in range(len(rows))]
    return pd.DataFrame(
        rows, columns=["Open", "High", "Low", "Close", "Volume"],
        index=pd.DatetimeIndex(idx, name="Datetime"),
    )


def flat_bars(n=60, price=100.0, rng=0.5, volume=1000.0, start="2026-08-24 09:30"):
    """Bars that barely move -- the chop case."""
    rows = []
    for i in range(n):
        drift = 0.02 * ((i % 3) - 1)
        c = price + drift
        rows.append((c, c + rng / 2, c - rng / 2, c, volume))
    return make_bars(rows, start=start)


def trending_bars(n=260, start_price=100.0, step=0.10, rng=0.4, volume=1000.0,
                  start="2026-08-21 09:30"):
    """A clean uptrend long enough to warm up the 200-period lines."""
    rows = []
    p = start_price
    for _ in range(n):
        o = p
        c = p + step
        rows.append((o, max(o, c) + rng / 2, min(o, c) - rng / 2, c, volume))
        p = c
    return make_bars(rows, start=start)
