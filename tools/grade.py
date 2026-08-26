"""Self-grading of resolved calls. BUILD_PROMPT Part 6a.

Runs nightly and on demand::

    python3 tools/grade.py --date 2026-08-22

**The rule that decides whether this whole loop is honest:** if a single bar touched both the
stop and the target, it is recorded as a **loss**. Bar data does not reveal which came first,
and assuming the good fill is exactly how a backtest lies to you. Every ambiguous bar is also
flagged in ``outcomes.csv`` so the size of the assumption stays visible.

**Skips are graded too.** For a NO TRADE, what the trade *would* have done is measured. For a
WAIT, whether the named condition actually occurred is checked. A desk that only grades its own
trades will happily learn to trade less and call that improvement.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, time as dtime
from typing import Optional
from zoneinfo import ZoneInfo

# Running as a script (``python3 tools/grade.py``) puts tools/ on sys.path, not the repo root,
# so the package imports below would fail. Put the root on the path first.
if __package__ in (None, ""):  # pragma: no cover
    import os as _os
    import sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from tools import market, session

ET = ZoneInfo("America/New_York")

SESSION_CLOSE = dtime(16, 0)
FLAT_BY = dtime(15, 30)  # 0DTE hard flat -- grading stops here, per knowledge/04-risk-rules.md


@dataclass
class GradeResult:
    """One resolved call.

    ``outcome`` is one of: ``win``, ``loss``, ``flat_at_close``, ``no_bars``.
    ``r_multiple`` is measured on the **underlying**, not the contract -- contract P&L depends
    on fills this desk never sees.
    """

    call_id: str
    outcome: str
    r_multiple: Optional[float]
    minutes_to_resolution: Optional[float]
    mfe_r: Optional[float]
    mae_r: Optional[float]
    ambiguous_bar: bool
    note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _r(value: float, risk: float) -> float:
    return round(value / risk, 4) if risk else 0.0


def walk_forward(
    bars,
    entry_time: datetime,
    direction: str,
    entry: float,
    stop: float,
    target: float,
    flat_by: dtime = FLAT_BY,
    call_id: str = "",
) -> GradeResult:
    """Walk bars forward from the call to the flat-by time and record what happened **first**.

    Pure: takes bars in, returns a result. No network, no clock, no I/O.
    """
    risk = abs(entry - stop)
    if risk <= 0:
        return GradeResult(call_id, "no_bars", None, None, None, None, False,
                           "zero risk distance -- ungradeable")

    long = direction.lower().startswith("l")
    entry_time = entry_time.astimezone(ET)
    idx = bars.index
    window = bars[(idx > entry_time) & (idx.time < flat_by)]
    if len(window) == 0:
        return GradeResult(call_id, "no_bars", None, None, None, None, False,
                           "no bars after the call timestamp -- not graded")

    mfe = mae = 0.0
    for stamp, row in window.iterrows():
        high, low = float(row["High"]), float(row["Low"])
        fav = (high - entry) if long else (entry - low)
        adv = (entry - low) if long else (high - entry)
        mfe, mae = max(mfe, fav), max(mae, adv)

        hit_target = high >= target if long else low <= target
        hit_stop = low <= stop if long else high >= stop
        minutes = (stamp.to_pydatetime() - entry_time).total_seconds() / 60.0

        if hit_target and hit_stop:
            # Both inside one bar. Order is unknowable from bar data. Record the loss.
            return GradeResult(
                call_id, "loss", -1.0, round(minutes, 1), _r(mfe, risk), _r(mae, risk), True,
                f"stop and target both touched in the {stamp:%H:%M} ET bar; "
                "order unknowable from bars, recorded as a loss",
            )
        if hit_target:
            return GradeResult(call_id, "win", _r(abs(target - entry), risk), round(minutes, 1),
                               _r(mfe, risk), _r(mae, risk), False,
                               f"target {target:.2f} reached at {stamp:%H:%M} ET")
        if hit_stop:
            return GradeResult(call_id, "loss", -1.0, round(minutes, 1),
                               _r(mfe, risk), _r(mae, risk), False,
                               f"stop {stop:.2f} hit at {stamp:%H:%M} ET")

    last = window.iloc[-1]
    close = float(last["Close"])
    move = (close - entry) if long else (entry - close)
    minutes = (window.index[-1].to_pydatetime() - entry_time).total_seconds() / 60.0
    return GradeResult(
        call_id, "flat_at_close", _r(move, risk), round(minutes, 1),
        _r(mfe, risk), _r(mae, risk), False,
        f"neither level reached by {flat_by:%H:%M} ET; flat at {close:.2f}",
    )


def grade_skip(bars, call_time: datetime, direction: str, entry: float, stop_distance: float,
               reward_multiple: float = 2.0, call_id: str = "") -> GradeResult:
    """What a NO TRADE *would* have done, taken in the obvious direction.

    This is how the desk learns whether it is too cautious. Without it, survivorship guarantees
    the loop drifts toward trading less and calling that an improvement.

    The synthetic stop and target are derived, so this is a **counterfactual, not a trade**.
    It never enters P&L -- ``day_state`` only sums real TRADE rows.
    """
    long = direction.lower().startswith("l")
    stop = entry - stop_distance if long else entry + stop_distance
    target = entry + reward_multiple * stop_distance if long else entry - reward_multiple * stop_distance
    result = walk_forward(bars, call_time, direction, entry, stop, target, call_id=call_id)
    result.note = f"counterfactual skip: {result.note}"
    return result


def check_wait_condition(bars, wait_until: datetime, level: float, direction: str,
                         flat_by: dtime = FLAT_BY) -> dict:
    """Did the named WAIT condition actually occur by the stated time?

    ``direction`` is ``above`` or ``below`` -- the condition the WAIT verdict named.
    """
    idx = bars.index
    window = bars[(idx <= wait_until.astimezone(ET)) & (idx.time < flat_by)]
    if len(window) == 0:
        return {"occurred": None, "note": "no bars in the wait window"}
    closes = window["Close"].astype(float)
    occurred = bool((closes > level).any()) if direction == "above" else bool((closes < level).any())
    return {
        "occurred": occurred,
        "note": (
            f"{'a close' if occurred else 'no close'} {direction} {level:.2f} "
            f"by {wait_until:%H:%M} ET"
        ),
    }


def _float(row: dict, key: str) -> Optional[float]:
    try:
        v = row.get(key, "")
        return float(v) if v not in ("", None) else None
    except (TypeError, ValueError):
        return None


def grade_call_row(row: dict, bars) -> Optional[GradeResult]:
    """Grade one ledger row. Returns ``None`` when the row carries nothing gradeable."""
    call_id = row["call_id"]
    try:
        when = datetime.fromisoformat(row["timestamp_et"])
    except (ValueError, KeyError):
        return GradeResult(call_id, "no_bars", None, None, None, None, False,
                           "unparseable timestamp")

    verdict = row.get("verdict", "")
    entry = _float(row, "entry_low") or _float(row, "entry_high")
    stop = _float(row, "stop")
    target = _float(row, "target1")
    direction = row.get("direction", "long") or "long"

    if verdict == "TRADE":
        if entry is None or stop is None or target is None:
            return GradeResult(call_id, "no_bars", None, None, None, None, False,
                               "TRADE row missing entry, stop or target")
        return walk_forward(bars, when, direction, entry, stop, target, call_id=call_id)

    if verdict == "NO TRADE":
        price = entry if entry is not None else _float(row, "target1")
        if price is None:
            sub = bars[bars.index <= when.astimezone(ET)]
            if len(sub) == 0:
                return GradeResult(call_id, "no_bars", None, None, None, None, False,
                                   "no bar at the skip timestamp")
            price = float(sub.iloc[-1]["Close"])
        stop_distance = _float(row, "stop")
        if stop_distance is None or stop_distance <= 0:
            sub = bars[bars.index <= when.astimezone(ET)]
            stop_distance = float(market.atr(sub).iloc[-1]) if len(sub) > 15 else 0.5
        return grade_skip(bars, when, direction, price, abs(stop_distance), call_id=call_id)

    return None  # WAIT rows are checked by condition, not walked forward


def grade_day(day: date, calls_path: str = session.CALLS_CSV,
              outcomes_path: str = session.OUTCOMES_CSV, interval: str = "1m") -> dict:
    """Grade every ungraded call for one day. Pulls 1-minute bars, per BUILD_PROMPT Part 6a."""
    rows = [r for r in session.calls_for_day(day, calls_path) if r.get("graded") != "yes"]
    report = {"day": str(day), "ungraded": len(rows), "graded": 0, "results": [], "errors": []}
    if not rows:
        return report

    bars_by_ticker: dict[str, object] = {}
    graded_ids: set[str] = set()

    for row in rows:
        ticker = row["ticker"]
        if ticker not in bars_by_ticker:
            try:
                bars_by_ticker[ticker] = market.get_bars(ticker, interval, "5d", prepost=False)
            except market.NoDataError as exc:
                report["errors"].append(f"{ticker}: {exc}")
                bars_by_ticker[ticker] = None
        bars = bars_by_ticker[ticker]
        if bars is None:
            continue

        result = grade_call_row(row, bars)
        if result is None or result.outcome == "no_bars":
            if result:
                report["results"].append(result.as_dict())
            continue

        session.append_outcome({
            "call_id": result.call_id,
            "graded_at": datetime.now(ET).isoformat(timespec="seconds"),
            "outcome": result.outcome,
            "r_multiple": result.r_multiple,
            "minutes_to_resolution": result.minutes_to_resolution,
            "mfe_r": result.mfe_r,
            "mae_r": result.mae_r,
            "ambiguous_bar": "yes" if result.ambiguous_bar else "no",
            # "taken, broke rules" is CJ's own flag from 07-journal-protocol.md, and the most
            # diagnostic value in the set. It comes from him, never inferred from price.
            "rule_break": "yes" if "broke rules" in row.get("notes", "").lower() else "",
            "bars_source": f"yfinance {interval}",
            "notes": result.note,
        }, outcomes_path)
        graded_ids.add(result.call_id)
        report["results"].append(result.as_dict())

    session.mark_graded(graded_ids, calls_path)
    report["graded"] = len(graded_ids)
    return report


def summarise_day(report: dict) -> str:
    """The plain-text body for the nightly GitHub issue."""
    results = report["results"]
    wins = sum(1 for r in results if r["outcome"] == "win")
    losses = sum(1 for r in results if r["outcome"] == "loss")
    flat = sum(1 for r in results if r["outcome"] == "flat_at_close")
    ambiguous = sum(1 for r in results if r["ambiguous_bar"])
    total_r = sum(r["r_multiple"] or 0 for r in results)

    lines = [
        f"# Grading — {report['day']}",
        "",
        f"Calls graded: **{report['graded']}** of {report['ungraded']} ungraded",
        f"Win {wins} · Loss {losses} · Flat at close {flat}",
        f"Sum of R (underlying, includes counterfactual skips): **{total_r:+.2f}R**",
    ]
    if ambiguous:
        lines.append(
            f"\n**{ambiguous} ambiguous bar(s)** — stop and target touched inside one bar, "
            "recorded as losses. Bar data cannot reveal the order."
        )
    if report["errors"]:
        lines += ["", "## Errors", *(f"- {e}" for e in report["errors"])]
    if results:
        lines += ["", "## Detail", "", "| call | outcome | R | mins | note |", "|---|---|---|---|---|"]
        for r in results:
            rv = f"{r['r_multiple']:+.2f}" if r["r_multiple"] is not None else "—"
            lines.append(f"| {r['call_id']} | {r['outcome']} | {rv} | "
                         f"{r['minutes_to_resolution'] or '—'} | {r['note']} |")
    lines += ["", "_Paper trading. Underlying R, not contract P&L._"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Grade the day's calls.")
    ap.add_argument("--date", default=str(session.today_et()))
    ap.add_argument("--interval", default="1m")
    ap.add_argument("--summary", action="store_true", help="print the issue body instead of JSON")
    args = ap.parse_args()

    report = grade_day(date.fromisoformat(args.date), interval=args.interval)
    print(summarise_day(report) if args.summary else json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
