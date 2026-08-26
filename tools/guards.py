"""The nine hard vetoes. ``knowledge/04-risk-rules.md``, BUILD_PROMPT Part 7.

Every guard is a **pure function**: no clock, no network, no file I/O. Time is always passed in.
That is what makes them testable at both sides of every boundary, and it is why they can be
trusted -- a guard that reads the clock itself is a guard you cannot prove.

Each returns ``(passed: bool, reason: str)``. ``reason`` is non-empty only on a veto, and it is
written to be pasted straight into a response: when a guard vetoes, **CJ is told which guard**.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, time as dtime, timedelta
from typing import Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path) as fh:
        return json.load(fh)


def _both_tz(dt: datetime) -> str:
    return f"{dt.astimezone(CT):%H:%M} CT / {dt.astimezone(ET):%H:%M} ET"


# Boundary tolerance. Prices and thresholds are floats, so a value sitting *exactly* on a
# threshold can land a hair either side of it (1.5 * 0.40 is 0.6000000000000001, not 0.6).
# A guard that flips on float dust is not a guard you can trust, so "exactly at the threshold"
# is always resolved as **passing**, and the veto needs a real margin.
_EPS = 1e-9


def _meaningfully_below(value: float, threshold: float) -> bool:
    """True only when ``value`` is below ``threshold`` by more than float noise."""
    return value < threshold - _EPS


def _meaningfully_above(value: float, threshold: float) -> bool:
    """True only when ``value`` is above ``threshold`` by more than float noise."""
    return value > threshold + _EPS


def _parse_hhmm(value: str) -> dtime:
    hh, mm = value.split(":")
    return dtime(int(hh), int(mm))


# --------------------------------------------------------------------------------------
# 1. time cutoff
# --------------------------------------------------------------------------------------

def guard_time_cutoff(now: datetime, no_entry_after: str = "15:00", hard_flat: str = "15:30"):
    """No new 0DTE entry after 15:00 ET. Theta in the last half hour is a raffle, not a trade."""
    now_et = now.astimezone(ET)
    cutoff = _parse_hhmm(no_entry_after)
    flat = _parse_hhmm(hard_flat)
    if now_et.time() >= flat:
        return False, (
            f"GUARD 1 time cutoff -- {_both_tz(now_et)} is past hard flat "
            f"({flat:%H:%M} ET). Be flat. No new entries."
        )
    if now_et.time() >= cutoff:
        return False, (
            f"GUARD 1 time cutoff -- no new 0DTE entries after {cutoff:%H:%M} ET. "
            f"It is {_both_tz(now_et)}."
        )
    return True, ""


# --------------------------------------------------------------------------------------
# 2. opening lockout
# --------------------------------------------------------------------------------------

def guard_opening_lockout(now: datetime, lockout_minutes: int = 15):
    """No entries in the first 15 minutes. The open is noise.

    Also vetoes premarket outright -- ``02-trycon-mas.md`` treats premarket as no-call.
    """
    now_et = now.astimezone(ET)
    open_dt = datetime.combine(now_et.date(), dtime(9, 30), tzinfo=ET)
    if now_et < open_dt:
        return False, (
            f"GUARD 2 opening lockout -- premarket. Regular session opens 08:30 CT / 09:30 ET. "
            f"It is {_both_tz(now_et)}."
        )
    unlock = open_dt + timedelta(minutes=lockout_minutes)
    if now_et < unlock:
        return False, (
            f"GUARD 2 opening lockout -- first {lockout_minutes} minutes are noise. "
            f"Clear at {_both_tz(unlock)}."
        )
    return True, ""


# --------------------------------------------------------------------------------------
# 3. event lockout
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Event:
    """A scheduled release. ``when`` must be timezone-aware."""
    name: str
    when: datetime


def guard_event_lockout(
    now: datetime,
    events: Sequence[Event] = (),
    before_minutes: int = 15,
    after_minutes: int = 10,
):
    """No entry inside the window around a scheduled release.

    Event proximity is a first-class input. A perfect chart 8 minutes before CPI is a NO TRADE,
    and the response says that is why.
    """
    now_et = now.astimezone(ET)
    for ev in events:
        when = ev.when.astimezone(ET)
        start = when - timedelta(minutes=before_minutes)
        end = when + timedelta(minutes=after_minutes)
        if start <= now_et <= end:
            delta = (when - now_et).total_seconds() / 60.0
            if delta >= 0:
                window = f"{delta:.0f} min before"
            else:
                window = f"{abs(delta):.0f} min after"
            return False, (
                f"GUARD 3 event lockout -- {ev.name} at {_both_tz(when)}, "
                f"{window} it. No entry from {before_minutes} min before to "
                f"{after_minutes} min after."
            )
    return True, ""


# --------------------------------------------------------------------------------------
# 4. daily loss limit
# --------------------------------------------------------------------------------------

def guard_daily_loss_limit(day_pnl_r: float, limit_r: float = -2.0):
    """After -2R on the day the desk stops calling trades. **Not overridable.**"""
    if day_pnl_r <= limit_r:
        return False, (
            f"GUARD 4 daily loss limit -- day is {day_pnl_r:+.2f}R, limit is {limit_r:+.2f}R. "
            f"Desk is closed for today. This one does not get overridden."
        )
    return True, ""


# --------------------------------------------------------------------------------------
# 5. max trades per day
# --------------------------------------------------------------------------------------

def guard_max_trades(trades_today: int, limit: int = 3):
    """Overtrading is the most common way a good method loses money."""
    if trades_today >= limit:
        return False, (
            f"GUARD 5 max trades -- {trades_today} taken today, limit is {limit}. "
            f"Done for the day."
        )
    return True, ""


# --------------------------------------------------------------------------------------
# 6. cooldown
# --------------------------------------------------------------------------------------

def guard_cooldown(minutes_since_last_loss: Optional[float], cooldown_minutes: int = 15):
    """No new call within 15 minutes of a loss. Revenge trading is the second most common way."""
    if minutes_since_last_loss is None:
        return True, ""
    if minutes_since_last_loss < cooldown_minutes:
        remaining = cooldown_minutes - minutes_since_last_loss
        return False, (
            f"GUARD 6 cooldown -- {minutes_since_last_loss:.0f} min since the last loss, "
            f"cooldown is {cooldown_minutes} min. {remaining:.0f} min left."
        )
    return True, ""


# --------------------------------------------------------------------------------------
# 7. minimum stop distance
# --------------------------------------------------------------------------------------

def guard_min_stop_distance(stop_distance: float, mean_bar_range: float, multiple: float = 1.5):
    """A stop inside bar noise is not a stop, it is a random exit.

    It also makes the trade impossible to grade honestly, which is what corrupts the learning
    loop -- so this guard protects the evidence as much as the account.
    """
    if mean_bar_range is None or math.isnan(mean_bar_range) or mean_bar_range <= 0:
        return False, "GUARD 7 minimum stop -- no bar-range data to size the stop against."
    if stop_distance is None or math.isnan(stop_distance) or stop_distance <= 0:
        return False, "GUARD 7 minimum stop -- no stop distance supplied."
    required = multiple * mean_bar_range
    if _meaningfully_below(stop_distance, required):
        return False, (
            f"GUARD 7 minimum stop -- stop is {stop_distance:.2f}, inside bar noise. "
            f"Needs {required:.2f} ({multiple}x the {mean_bar_range:.2f} average 5m bar range)."
        )
    return True, ""


# --------------------------------------------------------------------------------------
# 8. liquidity
# --------------------------------------------------------------------------------------

def guard_liquidity(bid: float, ask: float, max_spread_pct: float = 0.10):
    """Reject a strike whose spread is wide relative to premium.

    A wide spread is a loss taken at entry. Requires a chain -- a price chart cannot show it
    (``02-trycon-mas.md``).
    """
    if not bid or not ask or bid <= 0 or ask <= 0:
        return False, (
            "GUARD 8 liquidity -- no bid/ask available. Check the chain before entering; "
            "a price chart cannot verify a spread."
        )
    if ask < bid:
        return False, f"GUARD 8 liquidity -- crossed quote, bid {bid:.2f} above ask {ask:.2f}."
    mid = (bid + ask) / 2
    spread_pct = (ask - bid) / mid
    if _meaningfully_above(spread_pct, max_spread_pct):
        return False, (
            f"GUARD 8 liquidity -- spread {ask - bid:.2f} on a {mid:.2f} mid is "
            f"{spread_pct:.1%} of premium, over the {max_spread_pct:.0%} limit."
        )
    return True, ""


# --------------------------------------------------------------------------------------
# 9. chop veto
# --------------------------------------------------------------------------------------

def guard_chop(ema9: float, ema21: float, ema50: float, atr_value: float, fraction: float = 0.25):
    """Tangled MAs are the clearest sit-out signal on this chart.

    If the spread across the 9/21/50 is inside ``fraction * ATR``, no trade in either
    direction.
    """
    values = [ema9, ema21, ema50]
    if any(v is None or math.isnan(v) for v in values):
        return False, "GUARD 9 chop -- moving average values unavailable."
    if atr_value is None or math.isnan(atr_value) or atr_value <= 0:
        return False, "GUARD 9 chop -- no ATR to measure the tangle against."
    spread = max(values) - min(values)
    threshold = fraction * atr_value
    if _meaningfully_below(spread, threshold):
        return False, (
            f"GUARD 9 chop -- 9/21/50 EMAs inside {spread:.2f} "
            f"(9 at {ema9:.2f}, 21 at {ema21:.2f}, 50 at {ema50:.2f}). "
            f"Needs {threshold:.2f} ({fraction} x ATR {atr_value:.2f}). That is chop, not a trend."
        )
    return True, ""


# --------------------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------------------

@dataclass
class GuardContext:
    """Everything the nine guards need. Time is always supplied, never read from the clock."""

    now: datetime
    ema9: float = float("nan")
    ema21: float = float("nan")
    ema50: float = float("nan")
    atr: float = float("nan")
    mean_bar_range: float = float("nan")
    stop_distance: float = float("nan")
    bid: float = 0.0
    ask: float = 0.0
    day_pnl_r: float = 0.0
    trades_today: int = 0
    minutes_since_last_loss: Optional[float] = None
    events: Sequence[Event] = field(default_factory=tuple)


@dataclass
class GuardResult:
    number: int
    name: str
    passed: bool
    reason: str


def run_all(ctx: GuardContext, config: Optional[dict] = None) -> list[GuardResult]:
    """Run every guard. Returns all nine results, in order, passed and failed alike.

    Deliberately does **not** short-circuit: CJ should see everything that would have stopped
    the trade, not just the first thing.
    """
    cfg = (config or load_config())["risk"]

    checks = [
        (1, "time cutoff", guard_time_cutoff(ctx.now, cfg["no_entry_after_et"], cfg["hard_flat_et"])),
        (2, "opening lockout", guard_opening_lockout(ctx.now, cfg["opening_lockout_minutes"])),
        (3, "event lockout", guard_event_lockout(
            ctx.now, ctx.events, cfg["event_lockout_before_minutes"], cfg["event_lockout_after_minutes"])),
        (4, "daily loss limit", guard_daily_loss_limit(ctx.day_pnl_r, cfg["daily_loss_limit_r"])),
        (5, "max trades", guard_max_trades(ctx.trades_today, cfg["max_trades_per_day"])),
        (6, "cooldown", guard_cooldown(ctx.minutes_since_last_loss, cfg["cooldown_minutes_after_loss"])),
        (7, "minimum stop", guard_min_stop_distance(
            ctx.stop_distance, ctx.mean_bar_range, cfg["min_stop_bar_range_multiple"])),
        (8, "liquidity", guard_liquidity(ctx.bid, ctx.ask, cfg["max_spread_pct_of_premium"])),
        (9, "chop", guard_chop(ctx.ema9, ctx.ema21, ctx.ema50, ctx.atr, cfg["chop_veto_atr_fraction"])),
    ]
    return [GuardResult(n, name, ok, why) for n, name, (ok, why) in checks]


def vetoes(results: Iterable[GuardResult]) -> list[GuardResult]:
    return [r for r in results if not r.passed]


def summarise(results: Iterable[GuardResult]) -> str:
    """The block that goes into a NO TRADE response when a guard fires."""
    failed = vetoes(results)
    if not failed:
        return "All nine guards clear."
    return "\n".join(f"- {r.reason}" for r in failed)
