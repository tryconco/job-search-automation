"""Recording what was read off the screenshot, and reconciling it against live bars.

**The single most important design rule in this build** (BUILD_PROMPT Part 3, Step 2):

    The screenshot answers *what CJ is looking at and when*.
    The data answers *what is actually true*.

So this module never returns a level. It returns **readings** -- each one carrying a confidence
and a note -- and a **reconciliation** saying whether the screenshot and the bars agree.

The split, from ``knowledge/_INDEX.md`` contradiction 2:

* **price now**  -> the screenshot wins (his chart is live, yfinance intraday is delayed)
* **every level** -> live bars win, always. No level ever comes from a pixel.

Structured output, not prose.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")

#: Default agreement tolerance, in dollars, for SPY/QQQ-scale prices. "A tick or two."
PRICE_TOLERANCE = 0.05

#: How far ahead of the last bar a screenshot may be before it is lag rather than staleness.
LAG_GRACE_MINUTES = 20


class Confidence(str, Enum):
    """How sure the read is. ``UNREADABLE`` is a legitimate answer and must be used."""

    CLEAR = "clear"          # printed plainly, no ambiguity
    PROBABLE = "probable"    # legible but small, cropped or partly overlapped
    UNREADABLE = "unreadable"  # blurry, cut off, or not tagged on this screenshot


class Status(str, Enum):
    AGREE = "agree"                # inside tolerance
    DATA_LAG = "data_lag"          # screenshot newer than the last bar -- expected, not an error
    STALE_SCREENSHOT = "stale"     # closed bars disagree -- ask for a fresh chart
    DISAGREE = "disagree"          # same bar, different price, beyond tolerance
    UNVERIFIABLE = "unverifiable"  # nothing to compare against


@dataclass
class Reading:
    """One value taken off the image. Never a level -- only what the pixels said."""

    field: str
    value: Optional[float]
    confidence: Confidence
    note: str = ""
    source: str = "screenshot"

    def as_dict(self) -> dict:
        d = asdict(self)
        d["confidence"] = self.confidence.value
        return d


@dataclass
class ScreenshotRead:
    """Step 1 of the pipeline: everything actually visible on the image.

    ``02-trycon-mas.md`` governs how to read it: five MA lines matched **by colour** off the
    right-edge tags, Central time axis, the countdown under the price box, bell icons as CJ's
    existing alerts, lighter background for premarket and after hours.
    """

    ticker: Optional[str] = None
    timeframe: Optional[str] = None
    chart_time: Optional[datetime] = None
    candle_countdown_seconds: Optional[int] = None
    signal_candle_developing: Optional[bool] = None
    readings: list[Reading] = field(default_factory=list)
    candle_notes: str = ""
    drawings: list[str] = field(default_factory=list)
    alerts: list[float] = field(default_factory=list)
    operator_text: str = ""
    volume_visible: bool = False

    def get(self, name: str) -> Optional[Reading]:
        for r in self.readings:
            if r.field == name:
                return r
        return None

    def value(self, name: str) -> Optional[float]:
        r = self.get(name)
        return r.value if r and r.confidence is not Confidence.UNREADABLE else None

    def unreadable(self) -> list[str]:
        """Fields that could not be read. These must be named in the response, never guessed."""
        return [r.field for r in self.readings if r.confidence is Confidence.UNREADABLE]

    def as_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "timeframe": self.timeframe,
            "chart_time": self.chart_time.isoformat() if self.chart_time else None,
            "candle_countdown_seconds": self.candle_countdown_seconds,
            "signal_candle_developing": self.signal_candle_developing,
            "readings": [r.as_dict() for r in self.readings],
            "candle_notes": self.candle_notes,
            "drawings": self.drawings,
            "alerts": self.alerts,
            "operator_text": self.operator_text,
            "volume_visible": self.volume_visible,
            "unreadable": self.unreadable(),
        }


@dataclass
class FieldCheck:
    field: str
    screenshot_value: Optional[float]
    data_value: Optional[float]
    delta: Optional[float]
    status: Status
    note: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Reconciliation:
    status: Status
    checks: list[FieldCheck]
    screenshot_age_minutes: Optional[float]
    message: str
    trust_screenshot_for: list[str] = field(default_factory=list)
    trust_data_for: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when the screenshot can be trusted to place price on the map."""
        return self.status in (Status.AGREE, Status.DATA_LAG)

    def as_dict(self) -> dict:
        return {
            "status": self.status.value,
            "checks": [c.as_dict() for c in self.checks],
            "screenshot_age_minutes": self.screenshot_age_minutes,
            "message": self.message,
            "trust_screenshot_for": self.trust_screenshot_for,
            "trust_data_for": self.trust_data_for,
        }


def _bar_at(df, when: datetime):
    """The bar whose window contains ``when``. Returns ``(timestamp, row)`` or ``(None, None)``."""
    if df is None or len(df) == 0 or when is None:
        return None, None
    idx = df.index
    when = when.astimezone(idx.tz or ET)
    earlier = idx[idx <= when]
    if len(earlier) == 0:
        return None, None
    stamp = earlier[-1]
    return stamp, df.loc[stamp]


def reconcile(
    read: ScreenshotRead,
    df,
    indicators=None,
    tolerance: float = PRICE_TOLERANCE,
    lag_grace_minutes: int = LAG_GRACE_MINUTES,
) -> Reconciliation:
    """Compare the screenshot against live bars and rule on which to trust.

    The comparison is against the bar covering the **screenshot's own timestamp**, not the
    newest bar -- comparing a 10:15 screenshot against an 11:00 bar would flag every chart as
    wrong.

    Outcomes:

    * ``AGREE`` -- inside tolerance. Proceed.
    * ``DATA_LAG`` -- the screenshot is newer than the last bar. Expected: yfinance intraday
      runs behind. Not an error. Use the screenshot price for the trigger, bars for levels.
    * ``STALE_SCREENSHOT`` -- a **closed** bar disagrees beyond tolerance. Say the chart may be
      stale and ask for a fresh one (``02-trycon-mas.md`` freshness rule).
    * ``UNVERIFIABLE`` -- no timestamp or no price was readable.
    """
    checks: list[FieldCheck] = []
    price = read.value("last_price")
    last_bar_time = df.index[-1].to_pydatetime() if (df is not None and len(df)) else None

    age = None
    if read.chart_time and last_bar_time:
        age = (read.chart_time.astimezone(ET) - last_bar_time.astimezone(ET)).total_seconds() / 60.0

    if price is None or read.chart_time is None or last_bar_time is None:
        missing = []
        if price is None:
            missing.append("last price")
        if read.chart_time is None:
            missing.append("chart timestamp")
        if last_bar_time is None:
            missing.append("live bars")
        return Reconciliation(
            status=Status.UNVERIFIABLE,
            checks=checks,
            screenshot_age_minutes=age,
            message=(
                f"Could not reconcile: {', '.join(missing)} unavailable. "
                "Stating no level that did not come from live data."
            ),
            trust_data_for=["every level"],
        )

    stamp, row = _bar_at(df, read.chart_time)
    if row is None:
        return Reconciliation(
            status=Status.UNVERIFIABLE,
            checks=checks,
            screenshot_age_minutes=age,
            message="Screenshot predates the available bar history. Cannot verify.",
            trust_data_for=["every level"],
        )

    bar_close = float(row["Close"])
    bar_high, bar_low = float(row["High"]), float(row["Low"])
    inside_bar = (bar_low - tolerance) <= price <= (bar_high + tolerance)
    delta = price - bar_close

    if age is not None and age > lag_grace_minutes:
        status = Status.DATA_LAG
        note = (
            f"Screenshot is {age:.0f} min ahead of the last bar ({last_bar_time:%H:%M} ET). "
            "That is data lag, not a stale chart."
        )
    elif inside_bar or abs(delta) <= tolerance:
        status = Status.AGREE
        note = f"Screenshot price sits inside the {stamp:%H:%M} ET bar."
    else:
        status = Status.STALE_SCREENSHOT
        note = (
            f"Screenshot reads {price:.2f} but the {stamp:%H:%M} ET bar closed {bar_close:.2f} "
            f"(range {bar_low:.2f}-{bar_high:.2f}). Chart may be stale."
        )

    checks.append(FieldCheck("last_price", price, bar_close, round(delta, 4), status, note))

    # MA readings are checked for *agreement only*. The computed value is the level, always --
    # a matching pixel does not promote a pixel to a level.
    if indicators is not None:
        for name, computed in (
            ("ema9", indicators.ema9), ("ema21", indicators.ema21),
            ("ema50", indicators.ema50), ("ema200", indicators.ema200),
            ("sma200", indicators.sma200),
        ):
            seen = read.value(name)
            if seen is None or computed is None or (isinstance(computed, float) and math.isnan(computed)):
                continue
            d = seen - computed
            agree = abs(d) <= max(tolerance, 0.10)
            checks.append(FieldCheck(
                name, seen, round(float(computed), 4), round(d, 4),
                Status.AGREE if agree else Status.DISAGREE,
                "" if agree else f"chart tag {seen:.2f} vs computed {computed:.2f}; using computed",
            ))

    message = note
    disagreeing = [c.field for c in checks[1:] if c.status is Status.DISAGREE]
    if disagreeing:
        message += (
            f" Chart tags disagree with computed values on: {', '.join(disagreeing)}. "
            "Computed values are authoritative for every level."
        )
    if read.unreadable():
        message += f" Not readable on this image: {', '.join(read.unreadable())}."

    return Reconciliation(
        status=status,
        checks=checks,
        screenshot_age_minutes=age,
        message=message,
        trust_screenshot_for=["current price", "current time", "what CJ drew", "candle shape"],
        trust_data_for=[
            "EMA 9/21/50/200", "SMA 200", "ATR", "VWAP", "prior day H/L/C",
            "overnight H/L", "opening range", "session H/L",
        ],
    )


def developing_candle_block(read: ScreenshotRead) -> Optional[str]:
    """The WAIT reason when the signal candle is still printing.

    ``02-trycon-mas.md``: a candle still counting down can flip its shape before the close. It
    is not a confirmed engulfing, pin bar or inside bar until it closes.
    """
    if not read.signal_candle_developing:
        return None
    if read.candle_countdown_seconds is None:
        return "Signal candle is still printing. Not a confirmed pattern until it closes."
    mins, secs = divmod(int(read.candle_countdown_seconds), 60)
    return (
        f"Signal candle is still printing — {mins}m {secs:02d}s on the countdown. "
        "It can flip its shape before the close. Not a confirmed pattern yet."
    )
